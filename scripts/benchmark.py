"""Measure how long a full assessment takes (Phase 7, item 7).

Usage:
  uv run python scripts/benchmark.py                       # in-process fixture data
  uv run python scripts/benchmark.py --url http://localhost:8080/fhir   # a FHIR server
                                                           # loaded with the personas
  uv run python scripts/benchmark.py --large 20000         # one synthetic long-term record
                                                           # (20,000 lab results) behind an
                                                           # in-process HTTP server

Calls ``assess_referral_need`` through an in-memory MCP client for every persona, ``--rounds``
times, and prints the latency percentiles and FHIR requests per assessment. Exits non-zero
when the 95th percentile is over ``--target-ms`` or an assessment needs more FHIR requests than
the budget. Targets: docs/evaluation/performance.md.
"""

import argparse
import asyncio
import json
import math
import sys
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastmcp import Client  # noqa: E402
from tests.helpers.fake_fhir_server import BASE, FakeFhirServer, no_sleep  # noqa: E402
from tests.personas import all_resources, persona_ids  # noqa: E402
from tests.personas.builder import PersonaBuilder  # noqa: E402

from adhd_mcp.clock import FixedClock  # noqa: E402
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter  # noqa: E402
from adhd_mcp.fhir.http_adapter import HttpFhirAdapter  # noqa: E402
from adhd_mcp.fhir.port import SEARCHABLE_TYPES, FhirReadPort, RawResource, SearchResult  # noqa: E402
from adhd_mcp.server import create_server  # noqa: E402
from adhd_mcp.terminology.site_codes import load_site_codes  # noqa: E402
from adhd_mcp.tools.context import ToolContext  # noqa: E402

#: Target for a full assessment against a local FHIR server (95th percentile).
TARGET_P95_MS = 2000.0
#: At most one read of the Patient and one search per resource type per assessment, plus two
#: more Observation searches: Observations are read by instrument code (the safety gate), by
#: category and by the site's military separation codes (peer review 01, D1).
REQUEST_BUDGET = 1 + len(SEARCHABLE_TYPES) + 2


class CountingPort:
    """Counts the requests one assessment sends to the FHIR source."""

    def __init__(self, inner: FhirReadPort) -> None:
        self.inner = inner
        self.requests = 0

    async def read_patient(self, patient_id: str) -> RawResource:
        self.requests += 1
        return await self.inner.read_patient(patient_id)

    async def search(self, resource_type: Any, patient_id: str, **kw: Any) -> SearchResult:
        self.requests += 1
        return await self.inner.search(resource_type, patient_id, **kw)


def percentile(values: Sequence[float], q: float) -> float:
    """Nearest-rank percentile (q in 0..100) of a non-empty sample."""
    if not values:
        raise ValueError("no values")
    ordered = sorted(values)
    rank = max(1, math.ceil(q / 100 * len(ordered)))
    return ordered[rank - 1]


@dataclass(frozen=True)
class Summary:
    source: str
    assessments: int
    p50_ms: float
    p95_ms: float
    max_ms: float
    max_requests: int
    target_p95_ms: float
    request_budget: int

    @property
    def ok(self) -> bool:
        return self.p95_ms <= self.target_p95_ms and self.max_requests <= self.request_budget


def summarize(
    source: str,
    latencies_ms: Sequence[float],
    requests: Sequence[int],
    *,
    target_p95_ms: float = TARGET_P95_MS,
    request_budget: int = REQUEST_BUDGET,
) -> Summary:
    return Summary(
        source=source,
        assessments=len(latencies_ms),
        p50_ms=round(percentile(latencies_ms, 50), 1),
        p95_ms=round(percentile(latencies_ms, 95), 1),
        max_ms=round(max(latencies_ms), 1),
        max_requests=max(requests),
        target_p95_ms=target_p95_ms,
        request_budget=request_budget,
    )


async def measure(port: FhirReadPort, patients: Sequence[str], rounds: int) -> tuple[list[float], list[int]]:  # fmt: skip  # noqa: E501
    latencies: list[float] = []
    requests: list[int] = []
    clock = FixedClock(datetime(2026, 6, 15, 12, tzinfo=UTC))
    for _ in range(rounds):
        for patient in patients:
            counting = CountingPort(port)
            context = ToolContext(
                port=counting, clock=clock, site_codes=load_site_codes("synthetic")
            )
            async with Client(create_server(context)) as client:
                start = time.perf_counter()
                await client.call_tool("assess_referral_need", {"patient_id": patient})
                latencies.append((time.perf_counter() - start) * 1000)
            requests.append(counting.requests)
    return latencies, requests


def large_record(labs: int, visits: int = 200) -> list[RawResource]:
    """One synthetic long-term record: many laboratory results and vital signs (which no tool
    needs), routine visits, and a few coded conditions (peer review 01, D1)."""
    p = PersonaBuilder("b01", gender="female", birth_date="1960-01-01")
    for code in ("F32.9", "G47.00", "F10.10"):
        p.condition(code, "synthetic", recorded="2025-01-01")
    for i in range(labs):
        day = date(2026, 6, 1) - timedelta(days=i % 3650)
        oid = p.observation("2345-7", "Glucose", f"{day.isoformat()}T08:00:00Z", value=90 + i % 40)
        resource = next(r for r in reversed(p.resources) if r["id"] == oid)
        resource["category"][0]["coding"][0]["code"] = "laboratory" if i % 4 else "vital-signs"
    for i in range(visits):
        day = date(2026, 6, 1) - timedelta(days=7 * i)
        p.encounter("AMB", f"{day.isoformat()}T09:00:00Z", f"{day.isoformat()}T09:30:00Z")
    return p.resources


async def run_large(labs: int, rounds: int, target: float) -> Summary:
    server = FakeFhirServer(large_record(labs), page_size=100)
    async with HttpFhirAdapter(BASE, transport=server.transport(), sleep=no_sleep) as adapter:
        latencies, requests = await measure(adapter, ["b01-patient"], rounds)
    return summarize(
        f"large record ({labs} lab results)", latencies, requests, target_p95_ms=target
    )


async def run(url: str | None, rounds: int, target: float, large: int | None = None) -> Summary:
    if large:
        return await run_large(large, rounds, target)
    patients = [f"{p}-patient" for p in persona_ids()]
    if url:
        async with HttpFhirAdapter(url) as adapter:
            await measure(adapter, patients, 1)  # warm the server's caches first
            latencies, requests = await measure(adapter, patients, rounds)
        source = url
    else:
        latencies, requests = await measure(FixtureFhirAdapter(all_resources()), patients, rounds)
        source = "fixture (in process)"
    return summarize(source, latencies, requests, target_p95_ms=target)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="FHIR base URL loaded with the personas")
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--target-ms", type=float, default=TARGET_P95_MS)
    parser.add_argument("--large", type=int, help="lab results in one synthetic long record")
    args = parser.parse_args()
    summary = asyncio.run(run(args.url, args.rounds, args.target_ms, args.large))
    print(json.dumps(asdict(summary) | {"ok": summary.ok}, indent=2))
    if not summary.ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
