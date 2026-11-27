"""SMART backend services: the signed assertion, token caching, and the adapter's headers.
The only POST is the token request, sent to the token URL; a caller's token never leaves."""

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs

import httpx2
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from adhd_mcp.audit.trace import current_trace_id
from adhd_mcp.clock import FixedClock
from adhd_mcp.fhir.errors import FhirRequestError
from adhd_mcp.fhir.http_adapter import HttpFhirAdapter
from adhd_mcp.fhir.smart import ASSERTION_TYPE, SmartBackendAuth
from tests.helpers.fake_fhir_server import BASE, FakeFhirServer, no_sleep
from tests.personas import all_resources

pytestmark = pytest.mark.anyio

TOKEN_URL = "https://auth.example.test/token"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PEM = KEY.private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
).decode()


class Clock(FixedClock):
    def advance(self, seconds: int) -> None:
        object.__setattr__(self, "instant", self.instant + timedelta(seconds=seconds))


class TokenServer:
    def __init__(self, *responses: httpx2.Response) -> None:
        self.requests: list[httpx2.Request] = []
        self.responses = list(responses)
        self.issued = 0

    async def handle(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        if self.responses:
            return self.responses.pop(0)
        self.issued += 1
        token = {"access_token": f"server-token-{self.issued}", "token_type": "bearer"}
        return httpx2.Response(200, json=token | {"expires_in": 300})


def make_auth(server: TokenServer, clock: Clock) -> SmartBackendAuth:
    return SmartBackendAuth(
        token_url=TOKEN_URL,
        client_id="adhd-mcp-test",
        private_key_pem=PEM,
        key_id="test-key-1",
        scope="system/Patient.rs system/Condition.rs",
        clock=clock,
        transport=httpx2.MockTransport(server.handle),
    )


def clock() -> Clock:
    return Clock(datetime(2026, 6, 15, 12, 0, tzinfo=UTC))


async def test_the_token_request_is_a_signed_client_credentials_post_to_the_token_url() -> None:
    server = TokenServer()
    auth = make_auth(server, clock())
    assert await auth.access_token() == "server-token-1"
    (request,) = server.requests
    assert (request.method, str(request.url)) == ("POST", TOKEN_URL)
    form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
    assert form["grant_type"] == "client_credentials"
    assert form["client_assertion_type"] == ASSERTION_TYPE
    header = jwt.get_unverified_header(form["client_assertion"])
    assert (header["alg"], header["kid"]) == ("RS384", "test-key-1")
    claims = jwt.decode(
        form["client_assertion"],
        KEY.public_key(),
        algorithms=["RS384"],
        audience=TOKEN_URL,
        options={"verify_exp": False, "verify_iat": False},
    )
    assert claims["iss"] == claims["sub"] == "adhd-mcp-test"
    assert claims["exp"] - claims["iat"] == 300


async def test_the_token_is_reused_until_shortly_before_it_expires() -> None:
    server = TokenServer()
    c = clock()
    auth = make_auth(server, c)
    assert await auth.access_token() == "server-token-1"
    c.advance(239)
    assert await auth.access_token() == "server-token-1"
    c.advance(1)
    assert await auth.access_token() == "server-token-2"


@pytest.mark.parametrize(
    "response",
    [
        httpx2.Response(401, json={"error": "invalid_client"}),
        httpx2.Response(200, json={"access_token": "x", "token_type": "mac"}),
    ],
)
async def test_a_refused_or_odd_token_response_is_an_error(response: httpx2.Response) -> None:
    with pytest.raises(FhirRequestError):
        await make_auth(TokenServer(response), clock()).access_token()


def test_plain_http_token_urls_are_refused() -> None:
    with pytest.raises(ValueError, match="https"):
        SmartBackendAuth(
            token_url="http://auth.example.test/token",
            client_id="x",
            private_key_pem=PEM,
            key_id="k",
            scope="s",
            clock=clock(),
        )


async def adapter_with(fhir: FakeFhirServer, tokens: TokenServer) -> HttpFhirAdapter:
    return HttpFhirAdapter(
        BASE, transport=fhir.transport(), sleep=no_sleep, auth=make_auth(tokens, clock())
    )


async def test_fhir_requests_carry_only_the_servers_own_token() -> None:
    fhir, tokens = FakeFhirServer(all_resources()), TokenServer()
    adapter = await adapter_with(fhir, tokens)
    await adapter.read_patient("p01-patient")
    await adapter.search("Condition", "p01-patient")
    assert {r.headers["Authorization"] for r in fhir.requests} == {"Bearer server-token-1"}
    assert {r.method for r in fhir.requests} == {"GET"}


async def test_a_401_renews_the_token_once() -> None:
    fhir, tokens = FakeFhirServer(all_resources()), TokenServer()
    fhir.fail_next = [401]
    adapter = await adapter_with(fhir, tokens)
    await adapter.read_patient("p01-patient")
    assert [r.headers["Authorization"] for r in fhir.requests] == [
        "Bearer server-token-1",
        "Bearer server-token-2",
    ]


async def test_requests_in_a_traced_call_carry_the_trace_id() -> None:
    fhir = FakeFhirServer(all_resources())
    adapter = HttpFhirAdapter(BASE, transport=fhir.transport(), sleep=no_sleep)
    await adapter.read_patient("p01-patient")
    assert "traceparent" not in fhir.requests[0].headers
    token = current_trace_id.set("4bf92f3577b34da6a3ce929d0e0e4736")
    try:
        await adapter.search("Condition", "p01-patient")
    finally:
        current_trace_id.reset(token)
    parent: Any = fhir.requests[-1].headers["traceparent"]
    assert parent.startswith("00-4bf92f3577b34da6a3ce929d0e0e4736-")
