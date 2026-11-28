"""Authentication over HTTP (OAuth 2.1 resource server): missing, expired, wrong-audience,
wrong-issuer and insufficient-scope tokens are refused; protected resource metadata is
published; a caller's token is never sent to the FHIR server."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx2
import pytest
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.server.auth.providers.jwt import RSAKeyPair

from adhd_mcp.audit.records import MemoryAuditSink
from adhd_mcp.clock import FixedClock
from adhd_mcp.config import AuthSettings
from adhd_mcp.fhir.http_adapter import HttpFhirAdapter
from adhd_mcp.server import build_auth, create_server
from adhd_mcp.terminology.site_codes import load_site_codes
from adhd_mcp.tools.common import ASSESS_SCOPE, EVIDENCE_SCOPE, TOOL_NAMES
from adhd_mcp.tools.context import ToolContext
from tests.helpers.fake_fhir_server import BASE, FakeFhirServer, no_sleep
from tests.personas import all_resources

pytestmark = pytest.mark.anyio

ISSUER = "https://auth.example.test"
PUBLIC = "https://adhd-mcp.example.test"
AUDIENCE = f"{PUBLIC}/mcp"
KEYS = RSAKeyPair.generate()


def token(**kw: Any) -> str:
    args: dict[str, Any] = {
        "subject": "clinician-1",
        "issuer": ISSUER,
        "audience": AUDIENCE,
        "scopes": [EVIDENCE_SCOPE, ASSESS_SCOPE],
        "additional_claims": {"client_id": "assistant-app"},
    } | kw
    return KEYS.create_token(**args)


class Harness:
    def __init__(self, tmp_path: Path) -> None:
        key = tmp_path / "public.pem"
        key.write_text(KEYS.public_key, encoding="utf-8")
        self.settings = AuthSettings(
            issuer=ISSUER,
            audience=AUDIENCE,
            public_url=PUBLIC,
            jwks_uri=None,
            public_key_file=key,
            authorization_servers=(ISSUER,),
        )
        self.fhir = FakeFhirServer(all_resources())
        self.sink = MemoryAuditSink()
        context = ToolContext(
            port=HttpFhirAdapter(BASE, transport=self.fhir.transport(), sleep=no_sleep),
            clock=FixedClock(datetime(2026, 6, 15, 12, 0, tzinfo=UTC)),
            site_codes=load_site_codes("synthetic"),
            audit_sink=self.sink,
        )
        self.app = create_server(context, auth=build_auth(self.settings)).http_app(path="/mcp")

    @asynccontextmanager
    async def running(self) -> AsyncIterator[None]:
        async with self.app.router.lifespan_context(self.app):
            yield

    def http(self) -> httpx2.AsyncClient:
        return httpx2.AsyncClient(transport=httpx2.ASGITransport(app=self.app), base_url=PUBLIC)

    def client(self, bearer: str) -> Client:  # type: ignore[type-arg]
        def factory(**kw: Any) -> httpx2.AsyncClient:
            # FastMCP passes headers, timeout, auth and redirect settings.
            return httpx2.AsyncClient(transport=httpx2.ASGITransport(app=self.app), **kw)

        transport = StreamableHttpTransport(
            AUDIENCE,
            auth=bearer,
            httpx_client_factory=factory,  # type: ignore[arg-type]  # takes extra kwargs
        )
        return Client(transport)


@pytest.fixture
def harness(tmp_path: Path) -> Harness:
    return Harness(tmp_path)


INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {},
}
HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


@pytest.mark.parametrize(
    "bearer",
    [
        None,
        "not-a-jwt",
        token(expires_in_seconds=-60),
        token(audience="https://elsewhere.example.test/mcp"),
        token(issuer="https://other-issuer.example.test"),
        RSAKeyPair.generate().create_token(issuer=ISSUER, audience=AUDIENCE),
    ],
    ids=["missing", "malformed", "expired", "wrong-audience", "wrong-issuer", "wrong-key"],
)
async def test_bad_tokens_are_rejected_with_401(harness: Harness, bearer: str | None) -> None:
    headers = HEADERS | ({"Authorization": f"Bearer {bearer}"} if bearer else {})
    async with harness.running(), harness.http() as http:
        response = await http.post("/mcp", json=INIT, headers=headers)
    assert response.status_code == 401
    assert "resource_metadata" in response.headers.get("WWW-Authenticate", "")
    assert harness.fhir.requests == []


async def test_protected_resource_metadata_names_the_authorization_server(
    harness: Harness,
) -> None:
    async with harness.running(), harness.http() as http:
        response = await http.get("/.well-known/oauth-protected-resource/mcp")
    assert response.status_code == 200
    body = response.json()
    assert body["authorization_servers"] == [f"{ISSUER}/"]
    assert set(body["scopes_supported"]) == {EVIDENCE_SCOPE, ASSESS_SCOPE}


async def test_a_valid_token_reaches_the_tools_and_is_never_forwarded(harness: Harness) -> None:
    bearer = token()
    async with harness.running(), harness.client(bearer) as client:
        result = await client.call_tool("assess_referral_need", {"patient_id": "p01-patient"})
    assert result.structured_content is not None
    assert result.structured_content["recommendation"] == "consider_referral_for_formal_screening"
    assert harness.fhir.requests
    for request in harness.fhir.requests:
        assert bearer not in str(request.headers)
        assert "Authorization" not in request.headers
    (record,) = harness.sink.records
    assert record.caller == "sub=clinician-1 client=assistant-app"


async def test_insufficient_scope_is_refused(harness: Harness) -> None:
    bearer = token(scopes=[EVIDENCE_SCOPE])
    async with harness.running(), harness.client(bearer) as client:
        evidence = await client.call_tool("check_safety_gate", {"patient_id": "p01-patient"})
        assert evidence.is_error is False
        denied = await client.call_tool(
            "assess_referral_need", {"patient_id": "p01-patient"}, raise_on_error=False
        )
    assert denied.is_error is True


# --- peer review 01, T6 and P4: every tool's scope, and the audit of each refusal -------

#: tool -> the scope it needs (None: any authenticated caller).
SCOPES_NEEDED = {
    "get_server_info": None,
    "check_safety_gate": EVIDENCE_SCOPE,
    "get_mh_problem_list": EVIDENCE_SCOPE,
    "get_screening_history": EVIDENCE_SCOPE,
    "check_existing_care": EVIDENCE_SCOPE,
    "get_medication_timeline": EVIDENCE_SCOPE,
    "get_utilization_summary": EVIDENCE_SCOPE,
    "get_psychosocial_context": EVIDENCE_SCOPE,
    "assess_referral_need": ASSESS_SCOPE,
    "draft_referral_proposal": ASSESS_SCOPE,
}
GRANTS = {"no-scope": [], "evidence": [EVIDENCE_SCOPE], "assess": [ASSESS_SCOPE]}


def test_the_scope_table_names_every_tool() -> None:
    assert set(SCOPES_NEEDED) == set(TOOL_NAMES)


@pytest.mark.parametrize("grant", sorted(GRANTS))
@pytest.mark.parametrize("tool", sorted(SCOPES_NEEDED))
async def test_each_tool_is_allowed_exactly_with_its_scope(
    harness: Harness, tool: str, grant: str
) -> None:
    # A mutation probe removed the scope check from three tools and no test noticed (T6).
    needed = SCOPES_NEEDED[tool]
    allowed = needed is None or needed in GRANTS[grant]
    arguments = {} if tool == "get_server_info" else {"patient_id": "p01-patient"}
    async with harness.running(), harness.client(token(scopes=GRANTS[grant])) as client:
        result = await client.call_tool(tool, arguments, raise_on_error=False)
    assert result.is_error is (not allowed)
    (record,) = harness.sink.records
    if allowed:
        assert record.outcome == "success"
    else:
        # P4 (E16): audited as internal_error, like a crash.
        assert (record.outcome, record.error_code) == ("error", "not_authorized")
        assert harness.fhir.requests == []


async def test_an_unknown_tool_is_audited_as_such(harness: Harness) -> None:
    async with harness.running(), harness.client(token()) as client:
        result = await client.call_tool("no_such_tool", {}, raise_on_error=False)
    assert result.is_error is True
    (record,) = harness.sink.records
    assert (record.outcome, record.error_code) == ("error", "unknown_tool")
