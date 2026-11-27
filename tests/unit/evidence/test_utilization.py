"""Utilization: acute care, injury visits, crashes as driver, psychiatric stays, windows."""

from datetime import date, timedelta
from typing import Any

import pytest

from adhd_mcp.evidence.utilization import (
    UtilizationResult,
    assemble_utilization,
    load_utilization_content,
)
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.terminology.site_codes import SiteCodes, load_site_codes
from adhd_mcp.tools.context import NO_SITE_CODES
from tests.helpers.failing_adapter import FailingAdapter
from tests.personas import all_resources
from tests.personas.builder import PersonaBuilder

pytestmark = pytest.mark.anyio

AS_OF = date(2026, 6, 15)


def ago(days: int) -> str:
    return (AS_OF - timedelta(days=days)).isoformat()


def person() -> PersonaBuilder:
    return PersonaBuilder("t40", gender="male", birth_date="1990-01-01")


async def summary(
    p: PersonaBuilder | None = None,
    *,
    patient_id: str | None = None,
    adapter: Any = None,
    site: SiteCodes | None = None,
) -> UtilizationResult:
    port = adapter or FixtureFhirAdapter(p.resources if p else all_resources())
    content = load_utilization_content(site or load_site_codes("synthetic"))
    pid = patient_id or (p.patient_id if p else "")
    return await assemble_utilization(PatientRecords(port), pid, AS_OF, content)


def count(result: UtilizationResult, measure: str) -> dict[str, int]:
    (c,) = [c for c in result.counts if c.measure == measure]
    return c.model_dump(exclude={"measure"})


def injury_visit(p: PersonaBuilder, days: int, *codes: str, class_code: str = "EMER") -> str:
    encounter = p.encounter(class_code, f"{ago(days)}T10:00:00Z", f"{ago(days)}T14:00:00Z")
    for code in codes:
        p.condition(
            code, "x", recorded=ago(days), encounter=encounter, category="encounter-diagnosis"
        )
    return encounter


async def test_an_injury_coded_several_times_on_one_visit_counts_once() -> None:
    p = person()
    injury_visit(p, 10, "S62.302A", "S61.411A", "W01.0XXA")
    result = await summary(p)
    injuries = [e for e in result.events if e.kind == "injury_visit"]
    assert len(injuries) == 1
    assert injuries[0].references[0].resource_type == "Encounter"
    assert len(injuries[0].references) == 4
    assert count(result, "injury_visit")["total_730"] == 1


async def test_injury_found_through_encounter_reason_code() -> None:
    p = person()
    p.encounter("EMER", f"{ago(5)}T10:00:00Z", reasons=(("S93.401A", "x"),))
    assert count(await summary(p), "injury_visit")["days_0_30"] == 1


async def test_injury_found_through_encounter_diagnosis_reference() -> None:
    p = person()
    condition = p.condition("S93.401A", "x", recorded=ago(5))
    encounter = p.encounter("EMER", f"{ago(5)}T10:00:00Z")
    p.resources[-1]["diagnosis"] = [{"condition": {"reference": f"Condition/{condition}"}}]
    result = await summary(p)
    (event,) = [e for e in result.events if e.kind == "injury_visit"]
    assert [r.id for r in event.references] == [encounter, condition]


async def test_injury_at_an_outpatient_visit_is_not_an_acute_injury_visit() -> None:
    p = person()
    injury_visit(p, 10, "S62.302A", class_code="AMB")
    result = await summary(p)
    assert count(result, "injury_visit")["total_730"] == 0
    assert count(result, "any_encounter")["total_730"] == 1


async def test_urgent_care_mapped_by_the_site_is_acute_care() -> None:
    p = person()
    encounter = injury_visit(p, 10, "S62.302A", class_code="AMB")
    p.resources[-2]["type"] = [
        {"coding": [{"system": "urn:adhd-mcp:synthetic-local-code", "code": "urgent-care"}]}
    ]
    result = await summary(p)
    assert [e.references[0].id for e in result.events if e.kind == "injury_visit"] == [encounter]


async def test_a_self_harm_visit_is_not_an_accidental_injury_visit() -> None:
    p = person()
    injury_visit(p, 10, "S61.411A", "X78.0XXA")
    result = await summary(p)
    assert count(result, "injury_visit")["total_730"] == 0
    assert count(result, "acute_care_visit")["total_730"] == 1


@pytest.mark.parametrize(
    ("days", "window"),
    [
        (0, "days_0_30"),
        (30, "days_0_30"),
        (31, "days_31_180"),
        (180, "days_31_180"),
        (181, "days_181_730"),
        (730, "days_181_730"),
    ],
)
async def test_window_boundaries(days: int, window: str) -> None:
    p = person()
    injury_visit(p, days, "S62.302A")
    counts = count(await summary(p), "injury_visit")
    assert counts[window] == 1
    assert counts["total_730"] == 1


async def test_a_visit_older_than_730_days_is_listed_but_not_counted() -> None:
    p = person()
    injury_visit(p, 731, "S62.302A")
    result = await summary(p)
    assert [e.kind for e in result.events] == ["acute_care_visit", "injury_visit"]
    assert count(result, "injury_visit")["total_730"] == 0


async def test_a_crash_as_driver_counts_once_per_encounter() -> None:
    p = person()
    injury_visit(p, 20, "V43.52XA", "S13.4XXA", "V43.52XD")
    result = await summary(p)
    crashes = [e for e in result.events if e.kind == "crash_as_driver"]
    assert len(crashes) == 1
    assert count(result, "crash_as_driver")["days_0_30"] == 1


async def test_a_crash_as_passenger_is_not_a_crash_as_driver() -> None:
    p = person()
    injury_visit(p, 20, "V43.62XA", "S13.4XXA")
    result = await summary(p)
    assert count(result, "crash_as_driver")["total_730"] == 0
    assert count(result, "injury_visit")["total_730"] == 1


async def test_a_crash_without_an_encounter_counts_once_per_day() -> None:
    p = person()
    p.condition("V43.52XA", "x", recorded=ago(40))
    p.condition("V43.52XA", "x", recorded=ago(40))
    p.condition("V43.52XA", "x", recorded=ago(400))
    assert count(await summary(p), "crash_as_driver")["total_730"] == 2


async def test_psychiatric_stay_reports_admission_and_discharge() -> None:
    result = await summary(patient_id="p03-patient")
    (stay,) = [e for e in result.events if e.kind == "psychiatric_stay"]
    assert (stay.date, stay.end) == (date(2026, 3, 30), date(2026, 4, 10))
    assert count(result, "psychiatric_stay")["days_31_180"] == 1
    assert result.psychiatric_stays_checked is True


async def test_without_a_site_mapping_psychiatric_stays_are_not_checked() -> None:
    result = await summary(patient_id="p03-patient", site=NO_SITE_CODES)
    assert result.psychiatric_stays_checked is False
    assert [e for e in result.events if e.kind == "psychiatric_stay"] == []


async def test_cancelled_encounters_do_not_count() -> None:
    p = person()
    p.encounter("EMER", f"{ago(5)}T10:00:00Z", status="cancelled")
    result = await summary(p)
    assert count(result, "any_encounter")["total_730"] == 0


async def test_record_volume_counts_distinct_visit_days() -> None:
    p = person()
    p.encounter("AMB", f"{ago(5)}T09:00:00Z")
    p.encounter("AMB", f"{ago(5)}T15:00:00Z")
    p.encounter("AMB", f"{ago(100)}T09:00:00Z")
    result = await summary(p)
    assert count(result, "any_encounter")["total_730"] == 3
    assert result.visit_days_730 == 2


async def test_persona_p01_has_three_injury_visits_and_one_crash_as_driver() -> None:
    result = await summary(patient_id="p01-patient")
    assert count(result, "injury_visit")["total_730"] == 3
    assert count(result, "crash_as_driver")["total_730"] == 1


async def test_failed_condition_read_is_reported_and_encounters_still_counted() -> None:
    p = person()
    injury_visit(p, 10, "S62.302A")
    result = await summary(adapter=FailingAdapter(p, {"Condition"}), patient_id=p.patient_id)
    assert {n.category: n.status for n in result.data_completeness}["Condition"] == "failed"
    assert count(result, "acute_care_visit")["total_730"] == 1


async def test_items_after_the_as_of_date_are_ignored() -> None:
    p = person()
    injury_visit(p, -1, "S62.302A")
    result = await summary(p)
    assert result.events == []
