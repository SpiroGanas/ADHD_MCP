"""Phase 7, item 6: fault injection in the FHIR layer, through the whole assessment.

Each fault hits one resource type's searches on an otherwise healthy server (the in-process
fake FHIR server behind the HTTP adapter). Whatever the fault, the server must say so: the
category is reported as failed or incomplete, the safety gate is never plain "clear" (and is
"data_unavailable" when an active gate check needed the category), and a
fault in a source of ADHD signals never yields a confident "no_recommendation".
"""

from collections.abc import Callable
from typing import Any

import httpx2
import pytest
from fastmcp import Client

from adhd_mcp.clock import FixedClock
from adhd_mcp.fhir.http_adapter import HttpFhirAdapter
from adhd_mcp.fhir.search import DATE_SEARCH
from adhd_mcp.server import create_server
from adhd_mcp.terminology.site_codes import load_site_codes
from adhd_mcp.tools.assessment import build_output, run_assessment
from adhd_mcp.tools.context import ToolContext
from tests.helpers.fake_fhir_server import BASE, FakeFhirServer, no_sleep
from tests.personas import all_resources

pytestmark = pytest.mark.anyio

#: Resource types read by the safety gate.
GATE_TYPES = {"Condition", "Observation", "QuestionnaireResponse", "Encounter", "Flag"}
#: Gate types read by checks that are active today (the PHQ-9 and C-SSRS checks, which read
#: Observation and QuestionnaireResponse, are not performed until LOINC is verified).
ACTIVE_GATE_TYPES = {"Condition", "Encounter", "Flag"}
#: Resource types the ADHD signals are read from.
SIGNAL_TYPES = {
    "Condition",
    "Encounter",
    "MedicationRequest",
    "MedicationDispense",
    "MedicationStatement",
}
SEARCHED_TYPES = sorted(DATE_SEARCH)

Fault = Callable[[httpx2.Request, httpx2.Response | None], httpx2.Response]


def _json(body: Any) -> httpx2.Response:
    return httpx2.Response(200, json=body)


def _is_first_page(request: httpx2.Request) -> bool:
    return "_offset" not in request.url.params and "broken-page" not in request.url.path


def timeout(request: httpx2.Request, _: httpx2.Response | None) -> httpx2.Response:
    raise httpx2.ReadTimeout("timed out", request=request)


def connection_refused(request: httpx2.Request, _: httpx2.Response | None) -> httpx2.Response:
    raise httpx2.ConnectError("refused", request=request)


def server_error(_: httpx2.Request, __: httpx2.Response | None) -> httpx2.Response:
    return httpx2.Response(503, text="detail that must not leak")


def forbidden(_: httpx2.Request, __: httpx2.Response | None) -> httpx2.Response:
    return httpx2.Response(403)


def not_json(_: httpx2.Request, __: httpx2.Response | None) -> httpx2.Response:
    return httpx2.Response(200, text="<html>maintenance</html>")


def not_a_bundle(_: httpx2.Request, __: httpx2.Response | None) -> httpx2.Response:
    return _json({"resourceType": "OperationOutcome", "issue": []})


def json_list(_: httpx2.Request, __: httpx2.Response | None) -> httpx2.Response:
    return _json([1, 2, 3])


def _healthy_bundle(response: httpx2.Response | None) -> dict[str, Any]:
    assert response is not None
    bundle: dict[str, Any] = response.json()
    return bundle


def partial_pages(request: httpx2.Request, response: httpx2.Response | None) -> httpx2.Response:
    """The first page arrives with a next link; every later page fails."""
    if not _is_first_page(request):
        return httpx2.Response(500)
    bundle = _healthy_bundle(response)
    kind = request.url.path.rsplit("/", 1)[-1]
    bundle["link"] = [{"relation": "next", "url": f"{BASE}/{kind}/broken-page?page=2"}]
    return _json(bundle)


def page_timeout(request: httpx2.Request, response: httpx2.Response | None) -> httpx2.Response:
    """The first page arrives with a next link; the next page times out."""
    if not _is_first_page(request):
        raise httpx2.ReadTimeout("timed out", request=request)
    return partial_pages(request, response)


def malformed_resource(
    request: httpx2.Request, response: httpx2.Response | None
) -> httpx2.Response:
    """A resource of the searched type that cannot be read: wrong types everywhere."""
    bundle = _healthy_bundle(response)
    kind = request.url.path.rsplit("/", 1)[-1]
    broken = {
        "resourceType": kind,
        "id": "zz-broken-1",
        "status": 7,
        "subject": "nonsense",
        "code": "not a concept",
        "category": "not a list",
        "clinicalStatus": 5,
        "verificationStatus": 5,
        "class": "not a coding",
        "period": "not a period",
        "recordedDate": "not a date",
        "onsetDateTime": 12,
        "effectiveDateTime": "not a date",
        "authoredOn": "not a date",
        "authored": "not a date",
        "whenHandedOver": "not a date",
        "medicationCodeableConcept": "not a concept",
        "item": "not a list",
    }
    bundle.setdefault("entry", []).append({"resource": broken})
    return _json(bundle)


def garbage_entry(_: httpx2.Request, response: httpx2.Response | None) -> httpx2.Response:
    """An entry that is not an object at all."""
    bundle = _healthy_bundle(response)
    bundle.setdefault("entry", []).append("garbage")
    return _json(bundle)


def garbage_resource(_: httpx2.Request, response: httpx2.Response | None) -> httpx2.Response:
    """An entry whose resource is not an object."""
    bundle = _healthy_bundle(response)
    bundle.setdefault("entry", []).append({"resource": ["not", "a", "resource"]})
    return _json(bundle)


def entry_without_resource(_: httpx2.Request, response: httpx2.Response | None) -> httpx2.Response:
    """An entry with no resource, or a resource with no type: neither may vanish silently."""
    bundle = _healthy_bundle(response)
    bundle.setdefault("entry", []).extend(
        [{"search": {"mode": "match"}}, {"resource": {"id": "z"}}]
    )
    return _json(bundle)


def garbage_entries(_: httpx2.Request, response: httpx2.Response | None) -> httpx2.Response:
    """``entry`` is not a list."""
    bundle = _healthy_bundle(response)
    bundle["entry"] = {"resource": "nope"}
    return _json(bundle)


def garbage_link(_: httpx2.Request, response: httpx2.Response | None) -> httpx2.Response:
    """A link that is not an object."""
    bundle = _healthy_bundle(response)
    bundle["link"] = ["next"]
    return _json(bundle)


def server_warning(_: httpx2.Request, response: httpx2.Response | None) -> httpx2.Response:
    """The server says its answer may be incomplete."""
    bundle = _healthy_bundle(response)
    outcome = {
        "resourceType": "OperationOutcome",
        "issue": [{"severity": "warning", "code": "incomplete"}],
    }
    bundle.setdefault("entry", []).append({"resource": outcome, "search": {"mode": "outcome"}})
    return _json(bundle)


FAULTS: dict[str, Fault] = {
    "timeout": timeout,
    "connection_refused": connection_refused,
    "server_error": server_error,
    "forbidden": forbidden,
    "not_json": not_json,
    "not_a_bundle": not_a_bundle,
    "json_list": json_list,
    "partial_pages": partial_pages,
    "page_timeout": page_timeout,
    "malformed_resource": malformed_resource,
    "garbage_entry": garbage_entry,
    "garbage_resource": garbage_resource,
    "garbage_entries": garbage_entries,
    "entry_without_resource": entry_without_resource,
    "garbage_link": garbage_link,
    "server_warning": server_warning,
}


class FaultyServer(FakeFhirServer):
    """Applies one fault to every search of one resource type."""

    def __init__(self, target: str, fault: Fault) -> None:
        super().__init__(all_resources(), page_size=1000)
        self.target = target
        self.fault = fault
        self.target_requested = False

    async def handle(self, request: httpx2.Request) -> httpx2.Response:
        path = request.url.path.removeprefix(httpx2.URL(BASE).path).strip("/").split("/")
        if path[0] != self.target:
            return await super().handle(request)
        self.target_requested = True
        healthy = None
        if len(path) == 1:
            healthy = await super().handle(request)
        return self.fault(request, healthy)


#: Read only while the PHQ-9 item 9 check is active, which needs verified LOINC codes (F2).
NOT_READ_YET = {"QuestionnaireResponse"}


async def assess_with_fault(
    clock: FixedClock, persona_id: str, target: str, fault: Fault
) -> dict[str, Any]:
    server = FaultyServer(target, fault)
    async with HttpFhirAdapter(BASE, transport=server.transport(), sleep=no_sleep) as adapter:
        context = ToolContext(port=adapter, clock=clock, site_codes=load_site_codes("synthetic"))
        # The tool's own functions, without an MCP session per case (the MCP layer is covered
        # by the tool tests; here only the data path matters).
        request, assessment = await run_assessment(context, f"{persona_id}-patient", None, "adhd")
        out = build_output(context, request, "adhd", assessment).model_dump(mode="json")
    assert server.target_requested == (target not in NOT_READ_YET)
    return out


async def test_the_direct_call_matches_the_tool_over_mcp(
    fixed_clock: FixedClock,
    persona_client: Client,  # type: ignore[type-arg]
) -> None:
    direct = await assess_with_fault(fixed_clock, "p01", "Flag", forbidden)
    server = FaultyServer("Flag", forbidden)
    async with HttpFhirAdapter(BASE, transport=server.transport(), sleep=no_sleep) as adapter:
        context = ToolContext(
            port=adapter, clock=fixed_clock, site_codes=load_site_codes("synthetic")
        )
        async with Client(create_server(context)) as client:
            result = await client.call_tool("assess_referral_need", {"patient_id": "p01-patient"})
    assert result.structured_content == direct


def _status(out: dict[str, Any], category: str) -> str | None:
    found = [n["status"] for n in out["data_completeness"] if n["category"] == category]
    return found[0] if found else None


# p01 is a referral suggestion, p10 a healthy control.
PERSONAS = ["p01", "p10"]
READ_TYPES = [t for t in SEARCHED_TYPES if t not in NOT_READ_YET]


@pytest.mark.parametrize("persona_id", PERSONAS)
@pytest.mark.parametrize("target", READ_TYPES)
@pytest.mark.parametrize("fault_name", sorted(FAULTS))
async def test_every_fault_is_reported_and_never_gives_a_confident_clean_result(
    fixed_clock: FixedClock, persona_id: str, target: str, fault_name: str
) -> None:
    out = await assess_with_fault(fixed_clock, persona_id, target, FAULTS[fault_name])

    # The fault is visible in the output, never hidden as an empty category.
    assert _status(out, target) in {"failed", "incomplete"}
    # A gate is plain "clear" only when every check ran on complete data.
    assert out["safety_gate"]["status"] != "clear"
    if target in GATE_TYPES:
        assert out["safety_gate"]["status"] in {"data_unavailable", "clear_limited_data"}
    if target in ACTIVE_GATE_TYPES:
        # Partial data never supports "not found": the gate cannot be evaluated.
        assert out["safety_gate"]["status"] == "data_unavailable"
    if out["safety_gate"]["status"] == "data_unavailable":
        assert out["recommendation"] == "insufficient_data"
    # A fault in a signal source never yields a confident "no_recommendation".
    if target in SIGNAL_TYPES:
        assert out["recommendation"] != "no_recommendation"
    # Nothing the server said leaks into the output.
    assert "detail that must not leak" not in str(out)
    assert "maintenance" not in str(out)


@pytest.mark.parametrize("fault_name", sorted(FAULTS))
async def test_any_flag_fault_fails_the_check_and_withholds_a_suggestion(
    fixed_clock: FixedClock, fault_name: str
) -> None:
    """p01 meets the rules. Flags that could not be read, or were read only in part, fail the
    high-risk flag check: the gate is data_unavailable and no suggestion is made (owner
    decision 2026-11-27, open question 19)."""
    out = await assess_with_fault(fixed_clock, "p01", "Flag", FAULTS[fault_name])
    flag_check = next(c for c in out["safety_gate"]["checks"] if c["id"] == "high_risk_flag")
    assert flag_check["outcome"] == "failed"
    assert flag_check["reason"].startswith("Could not read Flag")
    assert out["safety_gate"]["status"] == "data_unavailable"
    assert out["recommendation"] == "insufficient_data"
