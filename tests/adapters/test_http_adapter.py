from collections.abc import AsyncIterator
from datetime import UTC, date, datetime

import httpx2
import pytest

from adhd_mcp.fhir.errors import FhirRequestError, ResourceNotFoundError
from adhd_mcp.fhir.http_adapter import HttpFhirAdapter
from adhd_mcp.fhir.normalize import normalize_many
from adhd_mcp.fhir.port import SEARCHABLE_TYPES, SearchWarning
from adhd_mcp.fhir.records import SkipReason
from tests.adapters.shared_suite import SharedAdapterSuite, bundle_ids
from tests.helpers.fake_fhir_server import BASE, FakeFhirServer
from tests.personas import all_resources

pytestmark = pytest.mark.anyio


class Sleeps:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


@pytest.fixture
def server() -> FakeFhirServer:
    return FakeFhirServer(all_resources(), page_size=2)


@pytest.fixture
def sleeps() -> Sleeps:
    return Sleeps()


@pytest.fixture
async def adapter(server: FakeFhirServer, sleeps: Sleeps) -> AsyncIterator[HttpFhirAdapter]:
    async with HttpFhirAdapter(
        BASE, transport=server.transport(), page_size=2, sleep=sleeps
    ) as adapter:
        yield adapter


class TestHttpAdapterAgainstStub(SharedAdapterSuite):
    async def test_never_issues_anything_but_get(
        self, adapter: HttpFhirAdapter, server: FakeFhirServer
    ) -> None:
        await adapter.read_patient("p01-patient")
        for resource_type in SEARCHABLE_TYPES:
            await adapter.search(resource_type, "p02-patient")
        assert server.requests
        assert {r.method for r in server.requests} == {"GET"}


async def test_follows_paging_to_the_end(adapter: HttpFhirAdapter, server: FakeFhirServer) -> None:
    found = await adapter.search("Condition", "p01-patient")
    assert {r["id"] for r in found.resources} == bundle_ids("p01", "Condition")
    assert len(server.requests) == 5  # 10 conditions, 2 per page


async def test_search_parameters(adapter: HttpFhirAdapter, server: FakeFhirServer) -> None:
    await adapter.search(
        "MedicationDispense",
        "p02-patient",
        since=date(2024, 1, 1),
        updated_since=datetime(2025, 1, 1, tzinfo=UTC),
    )
    params = server.requests[0].url.params
    assert params["patient"] == "p02-patient"
    assert params["whenhandedover"] == "ge2024-01-01"
    assert params["_lastUpdated"] == "ge2025-01-01T00:00:00+00:00"
    assert params["_include"] == "MedicationDispense:medication"
    assert params["_count"] == "2"
    assert server.requests[0].headers["accept"] == "application/fhir+json"


async def test_retries_transient_failures_with_backoff(
    adapter: HttpFhirAdapter, server: FakeFhirServer, sleeps: Sleeps
) -> None:
    server.fail_next = [503, httpx2.ConnectError("refused"), 429]
    patient = await adapter.read_patient("p01-patient")
    assert patient["id"] == "p01-patient"
    assert sleeps.delays == [0.5, 1.0, 2.0]


async def test_honours_a_numeric_retry_after(
    adapter: HttpFhirAdapter, server: FakeFhirServer, sleeps: Sleeps
) -> None:
    server.fail_next = [httpx2.Response(429, headers={"Retry-After": "3"})]
    await adapter.read_patient("p01-patient")
    assert sleeps.delays == [3.0]


async def test_gives_up_after_max_attempts_with_a_transient_error(
    server: FakeFhirServer, sleeps: Sleeps
) -> None:
    server.fail_next = [503, 503, 503, 503]
    async with HttpFhirAdapter(
        BASE, transport=server.transport(), max_attempts=3, sleep=sleeps
    ) as adapter:
        with pytest.raises(FhirRequestError) as raised:
            await adapter.search("Condition", "p01-patient")
    assert raised.value.transient is True
    assert raised.value.status == 503
    assert len(server.requests) == 3


async def test_timeout_is_retried_then_reported(server: FakeFhirServer, sleeps: Sleeps) -> None:
    server.fail_next = [httpx2.ReadTimeout("slow")] * 3
    async with HttpFhirAdapter(
        BASE, transport=server.transport(), max_attempts=3, sleep=sleeps
    ) as adapter:
        with pytest.raises(FhirRequestError) as raised:
            await adapter.read_patient("p01-patient")
    assert raised.value.transient is True
    assert raised.value.status is None


@pytest.mark.parametrize("status", [400, 401, 403, 422])
async def test_permanent_failure_is_not_retried(
    adapter: HttpFhirAdapter, server: FakeFhirServer, sleeps: Sleeps, status: int
) -> None:
    server.fail_next = [status]
    with pytest.raises(FhirRequestError) as raised:
        await adapter.search("Condition", "p01-patient")
    assert raised.value.transient is False
    assert raised.value.status == status
    assert sleeps.delays == []
    assert "must not leak" not in str(raised.value)


async def test_missing_patient_is_not_found_not_a_failure(
    adapter: HttpFhirAdapter, server: FakeFhirServer
) -> None:
    server.fail_next = [410]
    with pytest.raises(ResourceNotFoundError):
        await adapter.read_patient("p01-patient")


async def test_refuses_a_next_link_to_another_origin(
    adapter: HttpFhirAdapter, server: FakeFhirServer
) -> None:
    server.next_link_base = "http://elsewhere.test/r4"
    with pytest.raises(FhirRequestError, match="origin"):
        await adapter.search("Condition", "p01-patient")
    assert all(r.url.host == "fhir.test" for r in server.requests)


async def test_non_bundle_search_response_is_a_failure(
    adapter: HttpFhirAdapter, server: FakeFhirServer
) -> None:
    server.fail_next = [httpx2.Response(200, json={"resourceType": "Patient", "id": "x"})]
    with pytest.raises(FhirRequestError, match="Bundle"):
        await adapter.search("Condition", "p01-patient")


async def test_invalid_json_is_a_failure(adapter: HttpFhirAdapter, server: FakeFhirServer) -> None:
    server.fail_next = [httpx2.Response(200, text="<html>")]
    with pytest.raises(FhirRequestError, match="JSON"):
        await adapter.read_patient("p01-patient")


async def test_operation_outcome_issues_become_warnings_without_their_text(
    adapter: HttpFhirAdapter, server: FakeFhirServer
) -> None:
    outcome = {
        "resourceType": "OperationOutcome",
        "issue": [
            {"severity": "warning", "code": "incomplete", "diagnostics": "synthetic detail text"},
            {"severity": "information", "code": "informational"},
        ],
    }
    bundle = {
        "resourceType": "Bundle",
        "type": "searchset",
        "entry": [
            {"resource": outcome, "search": {"mode": "outcome"}},
            {"resource": {"resourceType": "Condition", "id": "c1"}, "search": {"mode": "match"}},
        ],
    }
    server.fail_next = [httpx2.Response(200, json=bundle)]
    found = await adapter.search("Condition", "p01-patient")
    assert [r["id"] for r in found.resources] == ["c1"]
    assert found.warnings == (SearchWarning(severity="warning", code="incomplete"),)
    assert "synthetic detail" not in repr(found)


async def test_warnings_from_every_page_are_collected(
    adapter: HttpFhirAdapter, server: FakeFhirServer
) -> None:
    def page(issue_code: str, next_url: str | None) -> httpx2.Response:
        return httpx2.Response(
            200,
            json={
                "resourceType": "Bundle",
                "type": "searchset",
                "link": [{"relation": "next", "url": next_url}] if next_url else [],
                "entry": [
                    {
                        "resource": {
                            "resourceType": "OperationOutcome",
                            "issue": [{"severity": "error", "code": issue_code}],
                        }
                    }
                ],
            },
        )

    server.fail_next = [page("too-costly", f"{BASE}/Condition?page=2"), page("suppressed", None)]
    found = await adapter.search("Condition", "p01-patient")
    assert found.resources == []
    assert [w.code for w in found.warnings] == ["too-costly", "suppressed"]


def test_base_url_must_be_http_or_https() -> None:
    with pytest.raises(ValueError, match="base URL"):
        HttpFhirAdapter("ftp://fhir.test/r4")


async def test_resources_without_an_id_are_passed_on_to_be_reported(
    adapter: HttpFhirAdapter, server: FakeFhirServer
) -> None:
    bundle = {
        "resourceType": "Bundle",
        "type": "searchset",
        "entry": [
            {"resource": {"resourceType": "Condition"}},
            {"resource": {"resourceType": "Condition"}},
            {"resource": {"resourceType": "Condition", "id": "c1"}},
        ],
    }
    server.fail_next = [httpx2.Response(200, json=bundle)]
    found = await adapter.search("Condition", "p01-patient")
    assert len(found.resources) == 3
    skipped = normalize_many(found.resources).skipped
    assert [s.reason for s in skipped] == [SkipReason.NO_ID, SkipReason.NO_ID]


async def test_refuses_a_next_link_outside_the_base_path(
    adapter: HttpFhirAdapter, server: FakeFhirServer
) -> None:
    server.next_link_base = "http://fhir.test/r4-other"
    with pytest.raises(FhirRequestError, match="origin"):
        await adapter.search("Condition", "p01-patient")


async def test_stops_a_paging_loop(server: FakeFhirServer, sleeps: Sleeps) -> None:
    loop = {
        "resourceType": "Bundle",
        "type": "searchset",
        "link": [{"relation": "next", "url": f"{BASE}/Condition?patient=p01-patient"}],
        "entry": [],
    }
    server.fail_next = [httpx2.Response(200, json=loop) for _ in range(10)]
    async with HttpFhirAdapter(
        BASE, transport=server.transport(), max_pages=5, sleep=sleeps
    ) as adapter:
        with pytest.raises(FhirRequestError, match="pages"):
            await adapter.search("Condition", "p01-patient")
    assert len(server.requests) == 5


async def test_an_issue_code_that_is_not_a_fhir_token_is_not_passed_through(
    adapter: HttpFhirAdapter, server: FakeFhirServer
) -> None:
    outcome = {
        "resourceType": "OperationOutcome",
        "issue": [{"severity": "warning", "code": "Synthetic free text from a server"}],
    }
    bundle = {"resourceType": "Bundle", "type": "searchset", "entry": [{"resource": outcome}]}
    server.fail_next = [httpx2.Response(200, json=bundle)]
    found = await adapter.search("Condition", "p01-patient")
    assert found.warnings == (SearchWarning(severity="warning", code="unknown"),)
