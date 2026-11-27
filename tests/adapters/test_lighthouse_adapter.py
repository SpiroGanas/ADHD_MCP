"""The VA Lighthouse adapter (Phase 8, item 1), tested without credentials: the shared
adapter suite against a Lighthouse-shaped fake, the profile against the sandbox's recorded
CapabilityStatement, and Lighthouse's client credentials grant with patient-scoped tokens."""

import base64
import json
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx2
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastmcp import Client

from adhd_mcp.clock import FixedClock
from adhd_mcp.fhir.errors import FhirRequestError, SearchNotSupportedError
from adhd_mcp.fhir.http_adapter import HttpFhirAdapter
from adhd_mcp.fhir.lighthouse import LighthouseCcgAuth, lighthouse_adapter
from adhd_mcp.fhir.normalize import normalize_many
from adhd_mcp.fhir.port import SEARCHABLE_TYPES, SearchWarning
from adhd_mcp.fhir.profiles import ServerProfile, load_server_profile
from adhd_mcp.fhir.records import MedicationRecord
from adhd_mcp.fhir.search import DATE_SEARCH
from adhd_mcp.server import create_server
from adhd_mcp.terminology.site_codes import load_site_codes
from adhd_mcp.tools.context import NO_SITE_CODES, ToolContext
from tests.adapters.shared_suite import SharedAdapterSuite
from tests.helpers.fake_fhir_server import no_sleep
from tests.helpers.fake_lighthouse import (
    LIGHTHOUSE_BASE,
    OFFERED,
    TOKEN_URL,
    FakeLighthouseServer,
    launch_patient,
)
from tests.personas import all_resources
from tests.personas.builder import PersonaBuilder

pytestmark = pytest.mark.anyio

RECORDED = Path(__file__).parent / "recorded" / "lighthouse_sandbox_metadata.json"
PROFILE = load_server_profile("lighthouse")
CLOCK = FixedClock(datetime(2026, 6, 15, 12, 0, tzinfo=UTC))
AUDIENCE = "https://okta.lighthouse.test/oauth2/aus-test/v1/token"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PEM = KEY.private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
).decode()
SCOPE = "launch system/Patient.read system/Condition.read"


@pytest.fixture
def server() -> FakeLighthouseServer:
    return FakeLighthouseServer(all_resources(), page_size=2)


@pytest.fixture
async def adapter(server: FakeLighthouseServer) -> AsyncIterator[HttpFhirAdapter]:
    async with lighthouse_adapter(
        LIGHTHOUSE_BASE, transport=server.transport(), page_size=2, sleep=no_sleep
    ) as adapter:
        yield adapter


class TestLighthouseAdapterAgainstStub(SharedAdapterSuite):
    OFFERED = OFFERED

    async def test_only_gets_and_never_an_unsupported_parameter(
        self, adapter: HttpFhirAdapter, server: FakeLighthouseServer
    ) -> None:
        for resource_type in self.offered():
            await adapter.search(resource_type, "p02-patient", since=date(2020, 1, 1))
        assert {r.method for r in server.requests} == {"GET"}
        assert server.rejected == []


# --- the profile against the sandbox's recorded CapabilityStatement --------------------


def interactions(resource: dict[str, Any]) -> set[str]:
    return {i["code"] for i in resource.get("interaction", [])}


def recorded_resources() -> dict[str, dict[str, Any]]:
    statement = json.loads(RECORDED.read_text(encoding="utf-8"))
    (rest,) = statement["rest"]
    return {r["type"]: r for r in rest["resource"]}


def test_the_profile_offers_exactly_the_searchable_types_the_sandbox_offers() -> None:
    sandbox = {t for t, r in recorded_resources().items() if "search-type" in interactions(r)}
    assert PROFILE.offered == frozenset(SEARCHABLE_TYPES) & sandbox
    assert PROFILE.offered == OFFERED


def test_every_search_parameter_the_profile_sends_is_in_the_capability_statement() -> None:
    resources = recorded_resources()
    for resource_type in PROFILE.offered:
        allowed = {p["name"] for p in resources[resource_type]["searchParam"]}
        assert {"patient", "_lastUpdated"} <= allowed, resource_type
        param = PROFILE.date_param(resource_type)
        assert param is None or param in allowed, resource_type
    assert PROFILE.date_param("MedicationRequest") is None  # no date search: filtered here


def test_the_sandbox_offers_no_include_and_medications_are_read_by_id() -> None:
    resources = recorded_resources()
    assert not any(r.get("searchInclude") for r in resources.values())
    assert "read" in interactions(resources["Medication"])
    assert PROFILE.include_medications is False


def test_the_page_size_stays_within_the_sandbox_maximum() -> None:
    assert PROFILE.max_page_size == 200
    with pytest.raises(ValueError, match="page size"):
        lighthouse_adapter(LIGHTHOUSE_BASE, page_size=201)


def test_the_generic_profile_is_unchanged() -> None:
    generic = load_server_profile("generic")
    assert generic.offered == frozenset(SEARCHABLE_TYPES)
    assert generic.include_medications is True
    assert all(generic.date_param(t) == DATE_SEARCH[t][0] for t in SEARCHABLE_TYPES)


# --- medications ------------------------------------------------------------------------


def medication_persona() -> PersonaBuilder:
    p = PersonaBuilder("t80", gender="male", birth_date="1980-01-01")
    p.resources.append(
        {
            "resourceType": "Medication",
            "id": "t80-med-1",
            "code": {
                "coding": [
                    {"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "36437"}
                ]
            },
        }
    )
    for n, med in ((1, "t80-med-1"), (2, "t80-med-1"), (3, "t80-med-missing")):
        p.resources.append(
            {
                "resourceType": "MedicationRequest",
                "id": f"t80-medreq-{n}",
                "status": "active",
                "intent": "order",
                "subject": {"reference": "Patient/t80-patient"},
                "medicationReference": {"reference": f"Medication/{med}"},
                "authoredOn": f"202{n}-01-01",
            }
        )
    return p


async def test_referenced_medications_are_read_once_each_and_resolve_codes() -> None:
    p = medication_persona()
    p.resources = [r for r in p.resources if r["id"] != "t80-medreq-3"]
    server = FakeLighthouseServer(p.resources)
    async with lighthouse_adapter(LIGHTHOUSE_BASE, transport=server.transport()) as adapter:
        found = await adapter.search("MedicationRequest", p.patient_id)
    reads = [r for r in server.requests if "/Medication/" in r.url.path]
    assert [r.url.path.rsplit("/", 1)[1] for r in reads] == ["t80-med-1"]
    assert found.warnings == ()
    records = normalize_many(found.resources).records
    codes = {c.code for r in records if isinstance(r, MedicationRecord) for c in r.medication_codes}
    assert codes == {"36437"}


async def test_a_missing_medication_makes_the_search_incomplete_not_silent() -> None:
    p = medication_persona()
    server = FakeLighthouseServer(p.resources)
    async with lighthouse_adapter(LIGHTHOUSE_BASE, transport=server.transport()) as adapter:
        found = await adapter.search("MedicationRequest", p.patient_id)
    assert SearchWarning(severity="warning", code="not-found") in found.warnings


async def test_a_medication_on_another_origin_is_not_fetched() -> None:
    p = medication_persona()
    p.resources = [r for r in p.resources if r["id"] != "t80-medreq-3"]
    p.resources[-1]["medicationReference"]["reference"] = (
        "https://elsewhere.test/r4/Medication/t80-med-1"
    )
    server = FakeLighthouseServer(p.resources)
    async with lighthouse_adapter(LIGHTHOUSE_BASE, transport=server.transport()) as adapter:
        found = await adapter.search("MedicationRequest", p.patient_id)
    assert all("elsewhere" not in str(r.url) for r in server.requests)
    assert SearchWarning(severity="warning", code="not-found") in found.warnings


@pytest.mark.parametrize("bad_id", ["x?_format=xml", "x%2F..", "a" * 65])
async def test_a_medication_id_that_is_not_a_fhir_id_is_never_requested(bad_id: str) -> None:
    p = medication_persona()
    p.resources = [r for r in p.resources if r["id"] != "t80-medreq-3"]
    p.resources[-1]["medicationReference"]["reference"] = f"Medication/{bad_id}"
    server = FakeLighthouseServer(p.resources)
    async with lighthouse_adapter(LIGHTHOUSE_BASE, transport=server.transport()) as adapter:
        found = await adapter.search("MedicationRequest", p.patient_id)
    assert all(bad_id not in str(r.url) for r in server.requests)
    assert SearchWarning(severity="warning", code="not-found") in found.warnings


async def test_contained_and_coded_medications_need_no_read() -> None:
    p = medication_persona()
    p.resources = [r for r in p.resources if r["id"] not in {"t80-medreq-2", "t80-medreq-3"}]
    p.resources[-1]["medicationReference"]["reference"] = "#med"
    p.resources[-1]["contained"] = [{"resourceType": "Medication", "id": "med"}]
    p.medication_request("36437", "x", "2025-01-01")
    server = FakeLighthouseServer(p.resources)
    async with lighthouse_adapter(LIGHTHOUSE_BASE, transport=server.transport()) as adapter:
        found = await adapter.search("MedicationRequest", p.patient_id)
    assert not [r for r in server.requests if "/Medication/" in r.url.path]
    assert found.warnings == ()


async def test_a_response_that_is_not_a_medication_fails_the_search() -> None:
    p = medication_persona()
    server = FakeLighthouseServer(p.resources)
    real = server.route

    async def route(request: httpx2.Request) -> httpx2.Response:
        if "/Medication/" in request.url.path:
            return httpx2.Response(200, json={"resourceType": "Patient", "id": "x"})
        return await real(request)

    transport = httpx2.MockTransport(route)
    async with lighthouse_adapter(LIGHTHOUSE_BASE, transport=transport) as adapter:
        with pytest.raises(FhirRequestError, match="not a Medication"):
            await adapter.search("MedicationRequest", p.patient_id)


async def test_a_failed_medication_read_fails_the_search() -> None:
    p = medication_persona()
    server = FakeLighthouseServer(p.resources)
    real = server.route

    async def route(request: httpx2.Request) -> httpx2.Response:
        if "/Medication/" in request.url.path:
            return httpx2.Response(403)
        return await real(request)

    transport = httpx2.MockTransport(route)
    async with lighthouse_adapter(LIGHTHOUSE_BASE, transport=transport) as adapter:
        with pytest.raises(FhirRequestError):
            await adapter.search("MedicationRequest", p.patient_id)


async def test_unoffered_types_are_refused_before_any_request(
    adapter: HttpFhirAdapter, server: FakeLighthouseServer
) -> None:
    for resource_type in set(SEARCHABLE_TYPES) - OFFERED:
        with pytest.raises(SearchNotSupportedError):
            await adapter.search(resource_type, "p01-patient")
    assert server.requests == []


async def test_page_token_links_are_followed(
    adapter: HttpFhirAdapter, server: FakeLighthouseServer
) -> None:
    await adapter.search("Condition", "p01-patient")
    assert any("-pageToken" in str(r.url) for r in server.requests)


# --- client credentials grant -------------------------------------------------------------


def make_auth(server: FakeLighthouseServer, scope: str = SCOPE) -> LighthouseCcgAuth:
    return LighthouseCcgAuth(
        token_url=TOKEN_URL,
        audience=AUDIENCE,
        client_id="adhd-mcp-test",
        private_key_pem=PEM,
        key_id="test-key-1",
        scope=scope,
        clock=CLOCK,
        transport=server.transport(),
    )


async def test_the_token_request_names_the_patient_in_the_launch_parameter() -> None:
    # An obviously synthetic id in the ICN format (ten digits, V, six digits).
    server = FakeLighthouseServer([])
    auth = make_auth(server)
    await auth.access_token("9000000000V000000")
    (form,) = server.tokens
    assert launch_patient(form) == "9000000000V000000"
    assert base64.b64decode(form["launch"]) == b'{"patient":"9000000000V000000"}'
    assert form["scope"] == SCOPE
    claims = jwt.decode(
        form["client_assertion"],
        KEY.public_key(),
        algorithms=["RS256"],
        audience=AUDIENCE,
        options={"verify_exp": False, "verify_iat": False},
    )
    assert claims["iss"] == claims["sub"] == "adhd-mcp-test"
    assert claims["exp"] - claims["iat"] <= 300


async def test_tokens_are_kept_per_patient() -> None:
    server = FakeLighthouseServer([])
    auth = make_auth(server)
    first = await auth.access_token("p01-patient")
    assert await auth.access_token("p01-patient") == first
    assert await auth.access_token("p02-patient") != first
    assert [launch_patient(f) for f in server.tokens] == ["p01-patient", "p02-patient"]


async def test_a_scope_without_launch_sends_no_launch_parameter() -> None:
    server = FakeLighthouseServer([])
    auth = make_auth(server, scope="system/Appointment.read")
    await auth.access_token("p01-patient")
    assert "launch" not in server.tokens[0]


async def test_a_patient_scoped_token_needs_a_patient() -> None:
    auth = make_auth(FakeLighthouseServer([]))
    with pytest.raises(FhirRequestError, match="patient"):
        await auth.access_token(None)


async def test_the_per_patient_token_cache_is_bounded() -> None:
    server = FakeLighthouseServer([])
    auth = make_auth(server)
    for n in range(auth.max_cached + 5):
        await auth.access_token(f"p{n}")
    assert len(auth._tokens) == auth.max_cached


async def test_every_request_for_a_patient_carries_that_patients_token() -> None:
    server = FakeLighthouseServer(all_resources())
    auth = make_auth(server)
    async with lighthouse_adapter(
        LIGHTHOUSE_BASE, transport=server.transport(), auth=auth, sleep=no_sleep
    ) as adapter:
        await adapter.read_patient("p02-patient")
        await adapter.search("MedicationRequest", "p02-patient")
        await adapter.read_patient("p01-patient")
    tokens = {r.headers["Authorization"] for r in server.requests if "p02" in str(r.url)}
    assert tokens == {"Bearer token-1"}
    assert server.requests[-1].headers["Authorization"] == "Bearer token-2"


async def test_a_401_renews_that_patients_token_once() -> None:
    server = FakeLighthouseServer(all_resources())
    auth = make_auth(server)
    server.required_token = "token-2"
    async with lighthouse_adapter(
        LIGHTHOUSE_BASE, transport=server.transport(), auth=auth, sleep=no_sleep
    ) as adapter:
        patient = await adapter.read_patient("p01-patient")
    assert patient["id"] == "p01-patient"
    assert [launch_patient(f) for f in server.tokens] == ["p01-patient", "p01-patient"]


async def test_a_system_level_scope_shares_one_token_and_invalidates_it() -> None:
    server = FakeLighthouseServer([])
    auth = make_auth(server, scope="system/Appointment.read")
    first = await auth.access_token("p01-patient")
    assert await auth.access_token("p02-patient") == first
    auth.invalidate("p01-patient")
    assert await auth.access_token("p02-patient") != first


def test_the_lighthouse_grant_needs_an_audience() -> None:
    with pytest.raises(ValueError, match="audience"):
        LighthouseCcgAuth(
            token_url=TOKEN_URL,
            audience=None,
            client_id="x",
            private_key_pem=PEM,
            key_id="k",
            scope=SCOPE,
            clock=CLOCK,
        )


def test_unknown_profiles_and_types_are_refused() -> None:
    with pytest.raises(LookupError, match="no FHIR server profile"):
        load_server_profile("oracle-health")
    with pytest.raises(ValueError, match="unknown search types"):
        ServerProfile(id="x", title="x", source="x", offered=frozenset({"Appointment"}))


@pytest.mark.parametrize("missing", ["Condition", "Encounter"])
def test_every_profile_must_offer_conditions_and_encounters(missing: str) -> None:
    offered = OFFERED - {missing}
    with pytest.raises(ValueError, match="must offer Condition and Encounter"):
        ServerProfile(id="x", title="x", source="x", offered=offered)


def test_the_lighthouse_grant_refuses_a_plain_http_token_url() -> None:
    with pytest.raises(ValueError, match="https"):
        LighthouseCcgAuth(
            token_url="http://sandbox.lighthouse.test/token",
            audience=AUDIENCE,
            client_id="x",
            private_key_pem=PEM,
            key_id="k",
            scope=SCOPE,
            clock=CLOCK,
        )


# --- end to end ---------------------------------------------------------------------------


async def test_an_assessment_runs_end_to_end_against_lighthouse_shaped_data() -> None:
    server = FakeLighthouseServer(all_resources())
    port = lighthouse_adapter(LIGHTHOUSE_BASE, transport=server.transport(), sleep=no_sleep)
    context = ToolContext(port=port, clock=CLOCK, site_codes=load_site_codes("synthetic"))
    async with Client(create_server(context)) as client:
        result = await client.call_tool("assess_referral_need", {"patient_id": "p01-patient"})
    out = result.structured_content
    assert out is not None
    assert out["recommendation"] == "consider_referral_for_formal_screening"
    statuses = {n["category"]: n["status"] for n in out["data_completeness"]}
    assert statuses["Flag"] == "not_supported"
    assert statuses["ServiceRequest"] == "not_supported"
    assert statuses["Condition"] == "available"
    gate_checks = {c["id"]: c for c in out["safety_gate"]["checks"]}
    assert gate_checks["high_risk_flag"]["outcome"] == "not_performed"
    assert out["safety_gate"]["status"] == "clear_limited_data"
    # No security labels on Lighthouse data: the policy classifies by code alone.
    assert out["privacy"]["restricted"] == [{"category": "substance_use", "records": 2}]


async def test_an_empty_lighthouse_record_is_insufficient_data_not_clear() -> None:
    server = FakeLighthouseServer(all_resources())
    port = lighthouse_adapter(LIGHTHOUSE_BASE, transport=server.transport(), sleep=no_sleep)
    context = ToolContext(port=port, clock=CLOCK, site_codes=NO_SITE_CODES)
    async with Client(create_server(context)) as client:
        result = await client.call_tool("assess_referral_need", {"patient_id": "p07-patient"})
    out = result.structured_content
    assert out is not None
    assert out["recommendation"] == "insufficient_data"
