"""Peer review 01, D1: Observation searches ask only for what the tools use. The gate and
the screening history search by the codes the instrument files list; the evidence tools by
category (social history, survey, SDOH). Laboratory results and vital signs are never read.
"""

from datetime import UTC, datetime

import pytest

from adhd_mcp.clock import FixedClock
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.http_adapter import HttpFhirAdapter
from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.fhir.request_cache import RequestCachedPort
from adhd_mcp.terminology.site_codes import load_site_codes
from adhd_mcp.tools.assessment import run_assessment
from adhd_mcp.tools.context import ToolContext
from tests.helpers.fake_fhir_server import BASE, FakeFhirServer, no_sleep
from tests.personas.builder import PersonaBuilder

pytestmark = pytest.mark.anyio

CLOCK = FixedClock(datetime(2026, 6, 15, 12, 0, tzinfo=UTC))
LOINC = "http://loinc.org"


def person() -> PersonaBuilder:
    p = PersonaBuilder("t98", gender="female", birth_date="1980-01-01")
    p.condition("F32.9", "x", recorded="2026-01-10")
    p.observation("44260-8", "PHQ-9 item 9", "2025-01-01T09:00:00Z", value=0)
    lab = p.observation("2345-7", "Glucose", "2026-05-01T09:00:00Z", value=99)
    vital = p.observation("8480-6", "Systolic blood pressure", "2026-05-01T09:00:00Z", value=120)
    for oid, category in ((lab, "laboratory"), (vital, "vital-signs")):
        resource = next(r for r in p.resources if r["id"] == oid)
        resource["category"][0]["coding"][0]["code"] = category
    social = p.observation("88124-3", "Food insecurity", "2026-04-01T09:00:00Z")
    next(r for r in p.resources if r["id"] == social)["category"][0]["coding"][0]["code"] = (
        "social-history"
    )
    return p


async def test_the_fixture_adapter_filters_by_category_and_code() -> None:
    p = person()
    adapter = FixtureFhirAdapter(p.resources)
    by_category = await adapter.search(
        "Observation", p.patient_id, categories=("social-history", "survey")
    )
    assert {r["code"]["coding"][0]["code"] for r in by_category.resources} == {
        "44260-8",
        "88124-3",
    }
    by_code = await adapter.search("Observation", p.patient_id, codes=((LOINC, "44260-8"),))
    assert [r["code"]["coding"][0]["code"] for r in by_code.resources] == ["44260-8"]


async def test_the_http_adapter_sends_the_filters() -> None:
    server = FakeFhirServer(person().resources)
    async with HttpFhirAdapter(BASE, transport=server.transport(), sleep=no_sleep) as adapter:
        await adapter.search(
            "Observation",
            "t98-patient",
            categories=("social-history", "survey"),
            codes=((LOINC, "44260-8"), (LOINC, "93374-7")),
        )
    params = server.requests[-1].url.params
    assert params["category"] == "social-history,survey"
    assert params["code"] == f"{LOINC}|44260-8,{LOINC}|93374-7"


async def test_the_request_cache_keeps_differently_filtered_searches_apart() -> None:
    p = person()
    cached = RequestCachedPort(FixtureFhirAdapter(p.resources))
    labs = await cached.search("Observation", p.patient_id, categories=("laboratory",))
    survey = await cached.search("Observation", p.patient_id, categories=("survey",))
    assert labs.resources != survey.resources


async def test_the_reader_applies_the_filters_even_if_a_server_ignores_them() -> None:
    class IgnoringAdapter(FixtureFhirAdapter):
        async def search(self, resource_type, patient_id, **kw):  # type: ignore[no-untyped-def]
            kw.pop("categories", None)
            kw.pop("codes", None)
            return await super().search(resource_type, patient_id, **kw)

    p = person()
    read = await PatientRecords(IgnoringAdapter(p.resources)).observations(
        p.patient_id, categories=("survey",)
    )
    assert [r.codes[0].code for r in read.records] == ["44260-8"]


async def test_an_assessment_never_reads_laboratory_results_or_vital_signs() -> None:
    # E9: Observation?patient=z&_count=100, unfiltered, read every lab and vital sign.
    server = FakeFhirServer(person().resources)
    async with HttpFhirAdapter(BASE, transport=server.transport(), sleep=no_sleep) as adapter:
        context = ToolContext(port=adapter, clock=CLOCK, site_codes=load_site_codes("synthetic"))
        await run_assessment(context, "t98-patient", None, "adhd")
    observation_requests = [r for r in server.requests if r.url.path.endswith("/Observation")]
    assert observation_requests
    for request in observation_requests:
        assert "category" in request.url.params or "code" in request.url.params
    returned = {
        entry["resource"]["code"]["coding"][0]["code"]
        for response in server.responses
        if response.get("resourceType") == "Bundle"
        for entry in response.get("entry", [])
        if entry["resource"]["resourceType"] == "Observation"
    }
    assert "2345-7" not in returned
    assert "8480-6" not in returned


@pytest.mark.parametrize(
    "broken",
    [
        {"category": "not a list"},
        {"category": ["not a concept"]},
        {"category": [{"coding": "nope"}]},
        {"code": "not a concept"},
        {"code": {"coding": [{"code": 7}]}},
    ],
)
async def test_a_malformed_resource_is_kept_for_normalization_to_report(
    broken: dict[str, object],
) -> None:
    # Filtering must never make an unreadable resource vanish (fail closed).
    p = person()
    p.resources.append(
        {
            "resourceType": "Observation",
            "id": "t98-broken",
            "subject": {"reference": "Patient/t98-patient"},
        }
        | broken
    )
    adapter = FixtureFhirAdapter(p.resources)
    by_category = await adapter.search("Observation", p.patient_id, categories=("survey",))
    by_code = await adapter.search("Observation", p.patient_id, codes=((LOINC, "44260-8"),))
    if "category" in broken:
        assert "t98-broken" in {r["id"] for r in by_category.resources}
    else:
        assert "t98-broken" in {r["id"] for r in by_code.resources}
