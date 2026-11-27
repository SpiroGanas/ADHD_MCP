"""The per-request cache: one FHIR query per distinct search, failures not cached."""

import asyncio
from typing import Any

import pytest

from adhd_mcp.fhir.errors import FhirRequestError
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.port import SearchResult, SearchType
from adhd_mcp.fhir.request_cache import RequestCachedPort
from tests.personas import all_resources

pytestmark = pytest.mark.anyio


class CountingAdapter(FixtureFhirAdapter):
    def __init__(self, resources: list[dict[str, Any]], *, fail_first: bool = False) -> None:
        super().__init__(resources)
        self.calls: list[tuple[str, ...]] = []
        self.fail_first = fail_first

    async def read_patient(self, patient_id: str) -> dict[str, Any]:
        self.calls.append(("Patient", patient_id))
        return await super().read_patient(patient_id)

    async def search(self, resource_type: SearchType, patient_id: str, **kw: Any) -> SearchResult:
        self.calls.append((resource_type, patient_id, repr(sorted(kw.items()))))
        await asyncio.sleep(0)
        if self.fail_first and len(self.calls) == 1:
            raise FhirRequestError("down", status=503, transient=True)
        return await super().search(resource_type, patient_id, **kw)


async def test_repeated_and_concurrent_searches_hit_the_server_once() -> None:
    inner = CountingAdapter(all_resources())
    port = RequestCachedPort(inner)
    results = await asyncio.gather(
        port.search("Condition", "p01-patient"),
        port.search("Condition", "p01-patient"),
        port.search("Condition", "p01-patient"),
    )
    assert results[0] == results[1] == results[2]
    await port.read_patient("p01-patient")
    await port.read_patient("p01-patient")
    assert len(inner.calls) == 2


async def test_different_parameters_are_different_queries() -> None:
    inner = CountingAdapter(all_resources())
    port = RequestCachedPort(inner)
    await port.search("Condition", "p01-patient")
    await port.search("Condition", "p02-patient")
    await port.search("Encounter", "p01-patient")
    assert len(inner.calls) == 3


async def test_a_failed_search_is_not_cached() -> None:
    inner = CountingAdapter(all_resources(), fail_first=True)
    port = RequestCachedPort(inner)
    with pytest.raises(FhirRequestError):
        await port.search("Condition", "p01-patient")
    found = await port.search("Condition", "p01-patient")
    assert found.resources
    assert len(inner.calls) == 2


async def test_cached_results_cannot_be_mutated_through_the_cache() -> None:
    port = RequestCachedPort(CountingAdapter(all_resources()))
    first = await port.search("Condition", "p01-patient")
    first.resources.clear()
    assert (await port.search("Condition", "p01-patient")).resources
