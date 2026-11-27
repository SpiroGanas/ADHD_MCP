"""Behaviour every FHIR adapter must share, so adapters are interchangeable (ADR 0004).

Subclass ``SharedAdapterSuite`` and provide an ``adapter`` fixture whose data source holds
every persona in ``tests/personas``.
"""

from datetime import UTC, date, datetime

import pytest

from adhd_mcp.fhir.errors import ResourceNotFoundError
from adhd_mcp.fhir.port import SEARCHABLE_TYPES, FhirReadPort, SearchResult, SearchType
from tests.personas import load_bundle, persona_ids


def bundle_ids(persona_id: str, resource_type: str) -> set[str]:
    return {
        e["resource"]["id"]
        for e in load_bundle(persona_id)["entry"]
        if e["resource"]["resourceType"] == resource_type
    }


def ids(result: SearchResult, resource_type: str | None = None) -> set[str]:
    return {
        r["id"]
        for r in result.resources
        if resource_type is None or r["resourceType"] == resource_type
    }


@pytest.mark.anyio
class SharedAdapterSuite:
    async def test_reads_a_patient(self, adapter: FhirReadPort) -> None:
        patient = await adapter.read_patient("p01-patient")
        assert patient["resourceType"] == "Patient"
        assert patient["id"] == "p01-patient"

    async def test_unknown_patient_is_not_found(self, adapter: FhirReadPort) -> None:
        with pytest.raises(ResourceNotFoundError):
            await adapter.read_patient("p99-does-not-exist")

    @pytest.mark.parametrize("bad_id", ["", "../Patient", "a b", "x" * 65, "p01?x=1"])
    async def test_invalid_patient_id_is_rejected_before_any_request(
        self, adapter: FhirReadPort, bad_id: str
    ) -> None:
        with pytest.raises(ValueError, match="patient id"):
            await adapter.read_patient(bad_id)
        with pytest.raises(ValueError, match="patient id"):
            await adapter.search("Condition", bad_id)

    @pytest.mark.parametrize("persona_id", persona_ids())
    @pytest.mark.parametrize("resource_type", SEARCHABLE_TYPES)
    async def test_search_returns_exactly_the_patients_resources(
        self, adapter: FhirReadPort, persona_id: str, resource_type: SearchType
    ) -> None:
        found = await adapter.search(resource_type, f"{persona_id}-patient")
        assert ids(found, resource_type) == bundle_ids(persona_id, resource_type)

    async def test_medication_searches_include_referenced_medications(
        self, adapter: FhirReadPort
    ) -> None:
        found = await adapter.search("MedicationDispense", "p02-patient")
        assert ids(found, "MedicationDispense") == bundle_ids("p02", "MedicationDispense")
        assert ids(found, "Medication") == bundle_ids("p02", "Medication")

    async def test_non_medication_search_returns_only_that_type(
        self, adapter: FhirReadPort
    ) -> None:
        found = await adapter.search("Condition", "p02-patient")
        assert {r["resourceType"] for r in found.resources} == {"Condition"}

    async def test_since_filters_on_the_clinical_date_inclusive(
        self, adapter: FhirReadPort
    ) -> None:
        found = await adapter.search("Condition", "p01-patient", since=date(2025, 6, 1))
        assert ids(found) == {f"p01-cond-{n}" for n in (3, 4, 5, 6, 9, 10)}

    async def test_since_one_day_later_excludes_the_boundary_day(
        self, adapter: FhirReadPort
    ) -> None:
        found = await adapter.search("Condition", "p01-patient", since=date(2025, 6, 2))
        assert ids(found) == {f"p01-cond-{n}" for n in (3, 4, 5, 6, 10)}

    async def test_since_on_encounter_periods(self, adapter: FhirReadPort) -> None:
        found = await adapter.search("Encounter", "p01-patient", since=date(2025, 1, 1))
        assert ids(found) == {"p01-enc-2", "p01-enc-3"}

    async def test_since_on_observations(self, adapter: FhirReadPort) -> None:
        found = await adapter.search("Observation", "p10-patient", since=date(2026, 1, 1))
        assert ids(found) == {"p10-obs-1", "p10-obs-2"}
        assert (
            await adapter.search("Observation", "p10-patient", since=date(2026, 5, 1))
        ).resources == []

    async def test_since_on_medication_dispenses_keeps_medications(
        self, adapter: FhirReadPort
    ) -> None:
        found = await adapter.search("MedicationDispense", "p02-patient", since=date(2024, 1, 1))
        assert ids(found, "MedicationDispense") == {"p02-meddisp-5"}
        assert ids(found, "Medication") == {"p02-med-5"}

    async def test_updated_since(self, adapter: FhirReadPort) -> None:
        past = datetime(2000, 1, 1, tzinfo=UTC)
        future = datetime(2100, 1, 1, tzinfo=UTC)
        assert ids(await adapter.search("Condition", "p01-patient", updated_since=past)) == (
            bundle_ids("p01", "Condition")
        )
        assert (
            await adapter.search("Condition", "p01-patient", updated_since=future)
        ).resources == []

    async def test_empty_record_returns_nothing(self, adapter: FhirReadPort) -> None:
        for resource_type in SEARCHABLE_TYPES:
            assert await adapter.search(resource_type, "p07-patient") == SearchResult(resources=[])

    async def test_persona_searches_carry_no_warnings(self, adapter: FhirReadPort) -> None:
        for resource_type in SEARCHABLE_TYPES:
            assert (await adapter.search(resource_type, "p01-patient")).warnings == ()
