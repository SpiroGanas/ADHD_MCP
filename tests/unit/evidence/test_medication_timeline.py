"""Medication timeline: drug-class exposure periods, fills, gaps, distinct agents."""

from datetime import date, timedelta
from typing import Any

import pytest

from adhd_mcp.evidence.medication_timeline import (
    MedicationTimelineResult,
    assemble_medication_timeline,
    load_medication_content,
)
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.reader import PatientRecords
from tests.helpers.failing_adapter import FailingAdapter
from tests.personas import all_resources
from tests.personas.builder import PersonaBuilder

pytestmark = pytest.mark.anyio

AS_OF = date(2026, 6, 15)
SERTRALINE = "36437"
SERTRALINE_25MG_TABLET = "312940"  # SCD: sertraline 25 MG Oral Tablet
FLUOXETINE = "4493"
METHYLPHENIDATE = "6901"
ZOLPIDEM = "39993"
LISINOPRIL = "29046"  # not in any class


def ago(days: int) -> str:
    return (AS_OF - timedelta(days=days)).isoformat()


def person() -> PersonaBuilder:
    return PersonaBuilder("t30", gender="female", birth_date="1990-01-01")


async def timeline(
    p: PersonaBuilder | None = None, *, patient_id: str | None = None, adapter: Any = None
) -> MedicationTimelineResult:
    port = adapter or FixtureFhirAdapter(p.resources if p else all_resources())
    pid = patient_id or (p.patient_id if p else "")
    return await assemble_medication_timeline(
        PatientRecords(port), pid, AS_OF, load_medication_content()
    )


def periods(result: MedicationTimelineResult, name: str) -> list[tuple[date, date]]:
    return [(e.start, e.end) for e in result.exposures if e.ingredient.name == name]


def fill(p: PersonaBuilder, code: str, when: str, days: int | None = 30) -> None:
    request = p.medication_request(code, "x", when, days=days or 30)
    p.medication_dispense(request, code, "x", when, days=days)


async def test_one_fill_is_one_exposure_of_its_days_supply() -> None:
    p = person()
    fill(p, SERTRALINE, ago(100), days=30)
    result = await timeline(p)
    assert periods(result, "sertraline") == [(AS_OF - timedelta(100), AS_OF - timedelta(71))]
    (exposure,) = result.exposures
    assert exposure.drug_class == "med.antidepressant"
    assert exposure.sources == ["dispense"]
    assert exposure.days_supply_assumed is False
    assert len(exposure.references) == 1


async def test_overlapping_fills_merge_into_one_exposure() -> None:
    p = person()
    fill(p, SERTRALINE, ago(200), days=90)
    fill(p, SERTRALINE, ago(150), days=90)
    assert periods(await timeline(p), "sertraline") == [
        (AS_OF - timedelta(200), AS_OF - timedelta(61))
    ]


async def test_a_gap_within_the_allowance_is_bridged() -> None:
    p = person()
    fill(p, SERTRALINE, ago(200), days=30)  # ends ago(171)
    fill(p, SERTRALINE, ago(140), days=30)  # 30-day gap: ago(170)..ago(141)
    assert len(periods(await timeline(p), "sertraline")) == 1


async def test_a_gap_beyond_the_allowance_splits_the_exposure() -> None:
    p = person()
    fill(p, SERTRALINE, ago(200), days=30)  # ends ago(171)
    fill(p, SERTRALINE, ago(139), days=30)  # 31-day gap
    assert len(periods(await timeline(p), "sertraline")) == 2


async def test_missing_days_supply_uses_the_assumed_supply_and_says_so() -> None:
    p = person()
    p.medication_dispense(None, SERTRALINE, "x", ago(100), days=None)
    (exposure,) = (await timeline(p)).exposures
    assert exposure.days_supply_assumed is True
    assert (exposure.start, exposure.end) == (AS_OF - timedelta(100), AS_OF - timedelta(71))


async def test_exposure_is_clipped_at_the_as_of_date_and_later_items_ignored() -> None:
    p = person()
    fill(p, SERTRALINE, ago(10), days=90)
    fill(p, FLUOXETINE, (AS_OF + timedelta(1)).isoformat())
    result = await timeline(p)
    assert periods(result, "sertraline") == [(AS_OF - timedelta(10), AS_OF)]
    assert periods(result, "fluoxetine") == []


async def test_a_product_code_maps_to_its_ingredient() -> None:
    p = person()
    fill(p, SERTRALINE_25MG_TABLET, ago(50))
    (exposure,) = (await timeline(p)).exposures
    assert exposure.ingredient.name == "sertraline"
    assert exposure.ingredient.rxcui == SERTRALINE


async def test_a_request_never_dispensed_is_prescribed_not_filled() -> None:
    p = person()
    fill(p, FLUOXETINE, ago(300))  # the record has dispensing data
    p.medication_request(SERTRALINE, "x", ago(100))
    result = await timeline(p)
    statuses = {(r.ingredient.name, r.fill_status) for r in result.prescriptions}
    assert statuses == {("fluoxetine", "filled"), ("sertraline", "not_filled")}
    assert periods(result, "sertraline") == []


async def test_a_dispense_without_a_link_fills_a_recent_request_of_the_same_ingredient() -> None:
    p = person()
    p.medication_request(SERTRALINE, "x", ago(100))
    p.medication_dispense(None, SERTRALINE, "x", ago(95))
    (prescription,) = (await timeline(p)).prescriptions
    assert prescription.fill_status == "filled"


async def test_without_any_dispensing_data_requests_count_as_exposure_with_unknown_fill() -> None:
    p = person()
    p.medication_request(SERTRALINE, "x", ago(100), days=60)
    result = await timeline(p)
    (prescription,) = result.prescriptions
    assert prescription.fill_status == "unknown"
    (exposure,) = result.exposures
    assert exposure.sources == ["request"]
    assert (exposure.start, exposure.end) == (AS_OF - timedelta(100), AS_OF - timedelta(41))


async def test_failed_dispense_read_makes_fill_status_unknown() -> None:
    p = person()
    p.medication_request(SERTRALINE, "x", ago(100))
    result = await timeline(
        adapter=FailingAdapter(p, {"MedicationDispense"}), patient_id=p.patient_id
    )
    assert [r.fill_status for r in result.prescriptions] == ["unknown"]
    statuses = {n.category: n.status for n in result.data_completeness}
    assert statuses["MedicationDispense"] == "failed"


async def test_cancelled_and_proposed_requests_are_not_prescriptions() -> None:
    p = person()
    p.medication_request(SERTRALINE, "x", ago(100), status="cancelled")
    p.resources.append(
        {
            "resourceType": "MedicationRequest",
            "id": "t30-proposal",
            "status": "active",
            "intent": "proposal",
            "medicationCodeableConcept": {
                "coding": [
                    {"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": FLUOXETINE}
                ]
            },
            "subject": {"reference": f"Patient/{p.patient_id}"},
            "authoredOn": ago(90),
        }
    )
    result = await timeline(p)
    assert result.prescriptions == []
    assert result.exposures == []


async def test_an_active_statement_with_no_end_runs_to_the_as_of_date() -> None:
    p = person()
    p.medication_statement(ZOLPIDEM, "x", ago(40))
    (exposure,) = (await timeline(p)).exposures
    assert exposure.drug_class == "med.sedative_hypnotic"
    assert (exposure.start, exposure.end, exposure.sources) == (
        AS_OF - timedelta(40),
        AS_OF,
        ["statement"],
    )


async def test_a_completed_statement_uses_its_period_and_not_taken_is_ignored() -> None:
    p = person()
    p.medication_statement(ZOLPIDEM, "x", ago(400), ago(300), status="completed")
    p.medication_statement(SERTRALINE, "x", ago(40), status="not-taken")
    result = await timeline(p)
    assert periods(result, "zolpidem") == [(AS_OF - timedelta(400), AS_OF - timedelta(300))]
    assert periods(result, "sertraline") == []


async def test_distinct_agents_ignore_dose_and_product_variants() -> None:
    p = person()
    fill(p, SERTRALINE, ago(900))
    fill(p, SERTRALINE_25MG_TABLET, ago(500))
    fill(p, FLUOXETINE, ago(100))
    result = await timeline(p)
    (antidepressants,) = [d for d in result.distinct_agents if d.drug_class == "med.antidepressant"]
    assert antidepressants.count == 2
    sertraline = next(a for a in antidepressants.agents if a.ingredient.name == "sertraline")
    assert sertraline.first_date == AS_OF - timedelta(900)
    assert sertraline.last_date == AS_OF - timedelta(471)
    # The exposure records only (peer review 01, C5): the two dispenses, not their orders.
    assert [r.resource_type for r in sertraline.references] == ["MedicationDispense"] * 2


async def test_unclassified_medications_are_counted_not_named() -> None:
    p = person()
    fill(p, LISINOPRIL, ago(30))
    result = await timeline(p)
    assert result.exposures == []
    assert result.unclassified_records == 2


async def test_stimulant_for_narcolepsy_is_marked() -> None:
    result = await timeline(patient_id="p06-patient")
    assert result.exposures
    assert all(e.drug_class == "med.adhd_stimulant" for e in result.exposures)
    assert all(e.for_narcolepsy for e in result.exposures)


async def test_stimulant_for_adhd_is_not_marked_for_narcolepsy() -> None:
    result = await timeline(patient_id="p04-patient")
    (exposure,) = result.exposures
    assert exposure.ingredient.name == "methylphenidate"
    assert exposure.for_narcolepsy is False


async def test_persona_p02_has_five_distinct_antidepressants() -> None:
    result = await timeline(patient_id="p02-patient")
    (antidepressants,) = [d for d in result.distinct_agents if d.drug_class == "med.antidepressant"]
    assert antidepressants.count == 5
    assert len(result.exposures) == 5


async def test_empty_record_reports_empty_categories() -> None:
    result = await timeline(patient_id="p07-patient")
    assert result.exposures == []
    assert {n.status for n in result.data_completeness} == {"empty"}
    assert [n.category for n in result.data_completeness] == [
        "MedicationRequest",
        "MedicationDispense",
        "MedicationStatement",
    ]


async def test_output_order_does_not_depend_on_server_order() -> None:
    p = person()
    fill(p, SERTRALINE, ago(300))
    fill(p, FLUOXETINE, ago(200))
    fill(p, METHYLPHENIDATE, ago(100))
    forward = await timeline(p)
    p.resources[1:] = list(reversed(p.resources[1:]))
    backward = await timeline(p)
    assert forward == backward
