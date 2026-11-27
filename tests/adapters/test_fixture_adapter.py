from datetime import UTC, datetime

import pytest

from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.port import SearchWarning
from tests.adapters.shared_suite import SharedAdapterSuite
from tests.personas import BUNDLE_DIR, all_resources


@pytest.fixture
def adapter() -> FixtureFhirAdapter:
    return FixtureFhirAdapter(all_resources(), last_updated=datetime(2026, 1, 1, tzinfo=UTC))


class TestFixtureAdapter(SharedAdapterSuite):
    pass


@pytest.mark.anyio
async def test_loads_bundles_from_a_directory() -> None:
    adapter = FixtureFhirAdapter.from_directory(BUNDLE_DIR)
    patient = await adapter.read_patient("p03-patient")
    assert patient["gender"] == "male"


@pytest.mark.anyio
async def test_returned_resources_are_copies() -> None:
    adapter = FixtureFhirAdapter(all_resources())
    first = await adapter.read_patient("p01-patient")
    first["gender"] = "changed"
    assert (await adapter.read_patient("p01-patient"))["gender"] == "male"


@pytest.mark.anyio
async def test_configured_warnings_are_returned_for_that_type_only() -> None:
    warning = SearchWarning(severity="warning", code="suppressed")
    adapter = FixtureFhirAdapter(all_resources(), warnings={"Condition": [warning]})
    assert (await adapter.search("Condition", "p01-patient")).warnings == (warning,)
    assert (await adapter.search("Observation", "p01-patient")).warnings == ()
