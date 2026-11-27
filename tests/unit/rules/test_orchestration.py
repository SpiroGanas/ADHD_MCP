"""Orchestration precedence paths not reached by the persona catalog."""

from datetime import date

import pytest

from adhd_mcp.conditions.adhd import adhd_plugin
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.models.domain import DataCompleteness, DataStatus, RecommendationCode
from adhd_mcp.orchestration.assess import assess, merge_completeness
from adhd_mcp.terminology.site_codes import load_site_codes
from adhd_mcp.tools.context import NO_SITE_CODES
from tests.helpers.failing_adapter import FailingAdapter, UnsupportingAdapter
from tests.personas import all_resources
from tests.personas.builder import PersonaBuilder

pytestmark = pytest.mark.anyio

AS_OF = date(2026, 6, 15)
SITE = load_site_codes("synthetic")


def p01_only() -> PersonaBuilder:
    p = PersonaBuilder("p01", gender="male", birth_date="1992-02-11")
    p.resources = [r for r in all_resources() if r["id"].startswith("p01-")]
    return p


async def test_a_gate_that_cannot_be_evaluated_gives_insufficient_data() -> None:
    p = p01_only()
    records = PatientRecords(FailingAdapter(p, {"Flag"}))
    result = await assess(adhd_plugin(), records, records, "p01-patient", AS_OF, site=SITE)
    assert result.gate.status == "data_unavailable"
    assert result.recommendation is RecommendationCode.INSUFFICIENT_DATA


async def test_an_unreadable_signal_source_without_a_fired_rule_is_insufficient_data() -> None:
    p = PersonaBuilder("t60", gender="female", birth_date="1990-01-01")
    p.condition("I10", "x", recorded="2025-01-01")
    records = PatientRecords(FailingAdapter(p, {"MedicationDispense"}))
    result = await assess(adhd_plugin(), records, records, p.patient_id, AS_OF, site=SITE)
    assert result.decision.recommend is False
    assert result.recommendation is RecommendationCode.INSUFFICIENT_DATA
    agents = next(f for f in result.findings if f.signal == "multiple_antidepressants")
    assert agents.reason.startswith("Not checked")


async def test_a_fired_rule_still_recommends_when_another_source_is_unreadable() -> None:
    records = PatientRecords(FailingAdapter(p01_only(), {"MedicationDispense"}))
    result = await assess(adhd_plugin(), records, records, "p01-patient", AS_OF, site=SITE)
    assert result.recommendation is RecommendationCode.CONSIDER_REFERRAL


async def test_incomplete_exclusion_checks_add_a_note_but_still_recommend() -> None:
    records = PatientRecords(FixtureFhirAdapter(all_resources()))
    result = await assess(adhd_plugin(), records, records, "p01-patient", AS_OF, site=NO_SITE_CODES)
    assert result.exclusions.excluded is None
    assert result.recommendation is RecommendationCode.CONSIDER_REFERRAL
    assert any("existing-care check" in n for n in result.notes)


#: The types VA Lighthouse's Patient Health API does not offer (CapabilityStatement 2026-11-27).
NOT_ON_LIGHTHOUSE = {
    "QuestionnaireResponse",
    "Flag",
    "ServiceRequest",
    "CarePlan",
    "MedicationDispense",
    "MedicationStatement",
}


async def test_types_a_server_does_not_offer_do_not_make_every_assessment_insufficient() -> None:
    p = PersonaBuilder("t61", gender="female", birth_date="1990-01-01")
    p.condition("I10", "x", recorded="2025-01-01")
    records = PatientRecords(UnsupportingAdapter(p, NOT_ON_LIGHTHOUSE))
    result = await assess(adhd_plugin(), records, records, p.patient_id, AS_OF, site=SITE)
    assert result.gate.status == "clear_limited_data"
    assert result.exclusions.excluded is None
    assert result.recommendation is RecommendationCode.NO_RECOMMENDATION
    statuses = {n.category: n.status for n in result.data_completeness}
    # QuestionnaireResponse is not read at all: the PHQ-9 check waits for LOINC verification.
    not_offered = {c for c, s in statuses.items() if s is DataStatus.NOT_SUPPORTED}
    assert not_offered == NOT_ON_LIGHTHOUSE - {"QuestionnaireResponse"}


async def test_an_empty_record_on_a_server_lacking_types_is_still_insufficient_data() -> None:
    p = PersonaBuilder("t65", gender="female", birth_date="1990-01-01")
    records = PatientRecords(UnsupportingAdapter(p, NOT_ON_LIGHTHOUSE))
    result = await assess(adhd_plugin(), records, records, p.patient_id, AS_OF, site=SITE)
    assert result.recommendation is RecommendationCode.INSUFFICIENT_DATA


async def test_orders_count_antidepressants_when_dispenses_are_not_offered() -> None:
    p = PersonaBuilder("t62", gender="female", birth_date="1990-01-01")
    for rxcui, when in (("36437", "2025-01-01"), ("4493", "2025-03-01"), ("2556", "2025-05-01")):
        p.medication_request(rxcui, "x", when)
    records = PatientRecords(UnsupportingAdapter(p, NOT_ON_LIGHTHOUSE))
    result = await assess(adhd_plugin(), records, records, p.patient_id, AS_OF, site=SITE)
    agents = next(f for f in result.findings if f.signal == "multiple_antidepressants")
    assert agents.present is True


async def test_a_server_without_medication_orders_cannot_clear_the_medication_signal() -> None:
    p = PersonaBuilder("t63", gender="female", birth_date="1990-01-01")
    p.condition("I10", "x", recorded="2025-01-01")
    records = PatientRecords(UnsupportingAdapter(p, NOT_ON_LIGHTHOUSE | {"MedicationRequest"}))
    result = await assess(adhd_plugin(), records, records, p.patient_id, AS_OF, site=SITE)
    assert result.recommendation is RecommendationCode.INSUFFICIENT_DATA


async def test_a_failed_optional_medication_source_is_still_insufficient_data() -> None:
    p = PersonaBuilder("t64", gender="female", birth_date="1990-01-01")
    p.condition("I10", "x", recorded="2025-01-01")
    adapter = UnsupportingAdapter(p, {"MedicationStatement"}, failing={"MedicationDispense"})
    records = PatientRecords(adapter)
    result = await assess(adhd_plugin(), records, records, p.patient_id, AS_OF, site=SITE)
    assert result.recommendation is RecommendationCode.INSUFFICIENT_DATA


async def test_a_lighthouse_shaped_record_that_meets_a_rule_still_recommends() -> None:
    records = PatientRecords(UnsupportingAdapter(p01_only(), NOT_ON_LIGHTHOUSE))
    result = await assess(adhd_plugin(), records, records, "p01-patient", AS_OF, site=SITE)
    assert result.recommendation is RecommendationCode.CONSIDER_REFERRAL


def test_not_supported_ranks_between_withheld_and_incomplete() -> None:
    def merged(*statuses: DataStatus) -> DataStatus:
        notes = [DataCompleteness(category="Flag", status=s) for s in statuses]
        return merge_completeness(notes)[0].status

    assert merged(DataStatus.EMPTY, DataStatus.NOT_SUPPORTED) is DataStatus.NOT_SUPPORTED
    assert merged(DataStatus.WITHHELD, DataStatus.NOT_SUPPORTED) is DataStatus.NOT_SUPPORTED
    assert merged(DataStatus.NOT_SUPPORTED, DataStatus.INCOMPLETE) is DataStatus.INCOMPLETE


def test_merged_completeness_keeps_the_least_complete_note() -> None:
    notes = [
        DataCompleteness(category="Condition", status=DataStatus.AVAILABLE, records=3),
        DataCompleteness(category="Encounter", status=DataStatus.EMPTY),
        DataCompleteness(category="Condition", status=DataStatus.FAILED),
        DataCompleteness(category="Condition", status=DataStatus.INCOMPLETE),
    ]
    merged = merge_completeness(notes)
    assert [(n.category, n.status) for n in merged] == [
        ("Condition", DataStatus.FAILED),
        ("Encounter", DataStatus.EMPTY),
    ]
