"""Typed, normalized access to one patient's data, independent of the data source."""

from datetime import date

import pytest

from adhd_mcp.fhir.codes import ICD10CM, LOINC
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.fhir.records import (
    ConditionRecord,
    EncounterRecord,
    MedicationRecord,
    ObservationRecord,
    SkipReason,
)
from adhd_mcp.terminology import ValueSet, load_value_set
from tests.personas import all_resources

pytestmark = pytest.mark.anyio


@pytest.fixture
def records() -> PatientRecords:
    return PatientRecords(FixtureFhirAdapter(all_resources()))


def loinc_set(*codes: str) -> ValueSet:
    return ValueSet.model_validate(
        {
            "id": "test.loinc",
            "version": "0",
            "title": "test",
            "entries": [
                {"system": LOINC, "match": "exact", "code": c, "verified": False} for c in codes
            ],
        }
    )


async def test_patient(records: PatientRecords) -> None:
    patient = await records.patient("p02-patient")
    assert patient.administrative_gender == "female"


async def test_conditions_filtered_by_value_set(records: PatientRecords) -> None:
    result = await records.conditions("p01-patient", value_set=load_value_set("sud.stimulant"))
    assert [r.ref.id for r in result.records] == ["p01-cond-7"]
    assert all(isinstance(r, ConditionRecord) for r in result.records)


async def test_conditions_since_a_date(records: PatientRecords) -> None:
    result = await records.conditions("p01-patient", since=date(2026, 1, 1))
    assert {r.ref.id for r in result.records} == {"p01-cond-5", "p01-cond-6"}


async def test_excluded_resources_are_reported_not_hidden(records: PatientRecords) -> None:
    result = await records.conditions(
        "p09-patient", value_set=load_value_set("care.adhd_diagnosis")
    )
    assert result.records == ()
    assert {(s.ref.id if s.ref else None, s.reason) for s in result.skipped} == {
        ("p09-cond-3", SkipReason.EXCLUDED_STATUS),
        ("p09-cond-4", SkipReason.EXCLUDED_STATUS),
    }


async def test_observations_with_codes_since_a_date(records: PatientRecords) -> None:
    result = await records.observations(
        "p03-patient", value_set=loinc_set("44260-8"), since=date(2026, 5, 1)
    )
    assert len(result.records) == 1
    record = result.records[0]
    assert isinstance(record, ObservationRecord)
    assert record.value is not None
    assert record.value.number == 2.0


async def test_medication_records_resolve_included_medications(records: PatientRecords) -> None:
    result = await records.medication_dispenses("p02-patient")
    assert len(result.records) == 5
    assert all(isinstance(r, MedicationRecord) and r.medication_codes for r in result.records)


async def test_encounters_match_value_sets_on_reason_codes(records: PatientRecords) -> None:
    result = await records.encounters(
        "p03-patient", value_set=load_value_set("safety.suicidal_ideation")
    )
    assert [r.ref.id for r in result.records] == ["p03-enc-1"]
    assert isinstance(result.records[0], EncounterRecord)


async def test_value_set_from_another_system_matches_nothing(records: PatientRecords) -> None:
    other = ValueSet.model_validate(
        {
            "id": "t",
            "version": "0",
            "title": "t",
            "entries": [
                {"system": ICD10CM, "match": "exact", "code": "44260-8", "verified": False}
            ],
        }
    )
    assert (await records.observations("p03-patient", value_set=other)).records == ()


async def test_every_resource_type_has_a_reader(records: PatientRecords) -> None:
    for method in (
        records.questionnaire_responses,
        records.medication_requests,
        records.medication_statements,
        records.procedures,
        records.service_requests,
        records.care_plans,
        records.flags,
    ):
        result = await method("p07-patient")
        assert result.records == ()
        assert result.skipped == ()
