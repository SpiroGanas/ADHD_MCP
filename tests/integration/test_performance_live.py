"""Latency of a full assessment against the local FHIR server (Phase 7, item 7).

Target (docs/evaluation/performance.md): 95th percentile at most 2 s per assessment, and at
most one Patient read plus one search per resource type.
"""

import pytest
from scripts.benchmark import TARGET_P95_MS, measure, summarize

from adhd_mcp.fhir.http_adapter import HttpFhirAdapter
from tests.personas import persona_ids

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


async def test_full_assessments_meet_the_latency_target(loaded_server: str) -> None:
    patients = [f"{p}-patient" for p in persona_ids()]
    async with HttpFhirAdapter(loaded_server) as adapter:
        await measure(adapter, patients, 1)  # warm-up
        latencies, requests = await measure(adapter, patients, 3)
    summary = summarize(loaded_server, latencies, requests)
    print(summary)  # noqa: T201 - shown in the CI log
    assert summary.p95_ms <= TARGET_P95_MS, summary
    assert summary.ok, summary
