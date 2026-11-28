"""The performance benchmark's arithmetic, and the FHIR request budget of one assessment
(Phase 7, item 7). Latency itself is measured by scripts/benchmark.py and, against a live
server, by tests/integration/test_performance_live.py; unit tests read no clock."""

import pytest
from scripts.benchmark import REQUEST_BUDGET, CountingPort, large_record, percentile, summarize

from adhd_mcp.clock import FixedClock
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.http_adapter import HttpFhirAdapter
from adhd_mcp.terminology.site_codes import load_site_codes
from adhd_mcp.tools.assessment import run_assessment
from adhd_mcp.tools.context import ToolContext
from tests.helpers.fake_fhir_server import BASE, FakeFhirServer, no_sleep
from tests.personas import all_resources, persona_ids


def test_percentile_is_nearest_rank() -> None:
    values = [5.0, 1.0, 4.0, 2.0, 3.0, 10.0, 9.0, 8.0, 7.0, 6.0]
    assert percentile(values, 50) == 5.0
    assert percentile(values, 95) == 10.0
    assert percentile(values, 90) == 9.0
    assert percentile([42.0], 95) == 42.0
    with pytest.raises(ValueError, match="no values"):
        percentile([], 50)


def test_summary_meets_or_misses_its_targets() -> None:
    fast = summarize("x", [100.0, 200.0, 300.0], [11, 12, 10], target_p95_ms=300.0)
    assert (fast.p50_ms, fast.p95_ms, fast.max_ms, fast.max_requests) == (200.0, 300.0, 300.0, 12)
    assert fast.ok
    assert not summarize("x", [100.0, 400.0], [11], target_p95_ms=300.0).ok
    assert not summarize("x", [100.0], [REQUEST_BUDGET + 1]).ok


@pytest.mark.anyio
@pytest.mark.parametrize("persona_id", persona_ids())
async def test_an_assessment_stays_within_the_fhir_request_budget(
    fixed_clock: FixedClock, persona_id: str
) -> None:
    port = CountingPort(FixtureFhirAdapter(all_resources()))
    context = ToolContext(port=port, clock=fixed_clock, site_codes=load_site_codes("synthetic"))
    await run_assessment(context, f"{persona_id}-patient", None, "adhd")
    assert 1 < port.requests <= REQUEST_BUDGET


@pytest.mark.anyio
async def test_a_large_record_is_assessed_without_reading_its_laboratory_results(
    fixed_clock: FixedClock,
) -> None:
    # Peer review 01, D1: every search read the whole history, every lab and vital sign.
    server = FakeFhirServer(large_record(2000), page_size=100)
    async with HttpFhirAdapter(BASE, transport=server.transport(), sleep=no_sleep) as adapter:
        port = CountingPort(adapter)
        context = ToolContext(port=port, clock=fixed_clock, site_codes=load_site_codes("synthetic"))
        await run_assessment(context, "b01-patient", None, "adhd")
    assert port.requests <= REQUEST_BUDGET
    observations = [
        e["resource"]
        for r in server.responses
        if isinstance(r, dict) and r.get("resourceType") == "Bundle"
        for e in r.get("entry", [])
        if e["resource"]["resourceType"] == "Observation"
    ]
    assert observations == []
