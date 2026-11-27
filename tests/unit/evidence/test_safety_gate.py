"""The safety gate assembler. Every signal type alone makes the gate positive; boundaries are
tested on the day, one day inside and one day outside; empty and failed data are reported,
never mistaken for a clean record.

Most tests load the gate content non-strictly so the LOINC-based checks can be exercised;
``test_strict_content_*`` show what is active today.
"""

from datetime import date, timedelta
from pathlib import Path

import pytest

from adhd_mcp.evidence.safety_gate import (
    GateContent,
    assess_safety_gate,
    load_gate_content,
    load_gate_definition,
)
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.port import SearchWarning
from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.models.domain import (
    CheckOutcome,
    DataStatus,
    SafetyGateResult,
    SafetyGateStatus,
)
from adhd_mcp.terminology import UnverifiedContentError, ValueSet, load_value_set
from adhd_mcp.terminology.site_codes import load_site_codes, load_site_codes_file
from tests.helpers.failing_adapter import FailingAdapter
from tests.helpers.wording import assert_no_diagnostic_language
from tests.personas.builder import PersonaBuilder
from tests.personas.definitions import PHQ9_QUESTIONNAIRE

pytestmark = pytest.mark.anyio

AS_OF = date(2026, 6, 15)


def ago(days: int) -> str:
    return (AS_OF - timedelta(days=days)).isoformat()


def person() -> PersonaBuilder:
    return PersonaBuilder("t01", gender="female", birth_date="1980-01-01")


def content(*, strict: bool = False, site: str = "synthetic") -> GateContent:
    return load_gate_content(load_site_codes(site), strict=strict)


async def gate(
    p: PersonaBuilder, *, strict: bool = False, gate_content: GateContent | None = None
) -> SafetyGateResult:
    records = PatientRecords(FixtureFhirAdapter(p.resources))
    result, _ = await assess_safety_gate(
        records, p.patient_id, AS_OF, gate_content or content(strict=strict)
    )
    return result


def outcome(result: SafetyGateResult, check_id: str) -> CheckOutcome:
    return next(c.outcome for c in result.checks if c.id == check_id)


def signals(result: SafetyGateResult) -> list[str]:
    return [e.signal for e in result.evidence]


# --- coded signals --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("code", "check_id"),
    [
        ("R45.851", "suicidal_ideation_code"),
        ("T14.91XA", "suicide_attempt_code"),
        ("X78.0XXA", "suicide_attempt_code"),
        ("T42.4X2A", "intentional_self_poisoning_code"),
        ("T42.4X4A", "undetermined_intent_poisoning_code"),
        ("T71.112A", "self_harm_asphyxiation_code"),
        ("R45.88", "nonsuicidal_self_harm_code"),
        ("Z91.51", "self_harm_history_code"),
        ("Z91.52", "self_harm_history_code"),
    ],
)
async def test_each_coded_signal_alone_makes_the_gate_positive(code: str, check_id: str) -> None:
    p = person()
    cid = p.condition(code, "synthetic", recorded=ago(10))
    result = await gate(p)
    assert result.status is SafetyGateStatus.POSITIVE
    assert outcome(result, check_id) is CheckOutcome.FOUND
    [item] = result.evidence
    assert item.signal == check_id
    assert [r.id for r in item.references] == [cid]
    assert item.date == AS_OF - timedelta(days=10)
    assert result.guidance is not None


async def test_unrelated_codes_do_not_trigger() -> None:
    p = person()
    p.condition("T14.90XA", "Injury, unspecified", recorded=ago(10))
    p.condition("R45.850", "Homicidal ideations", recorded=ago(10))
    p.condition("T42.4X1A", "Poisoning by benzodiazepines, accidental", recorded=ago(10))
    assert (await gate(p)).status is SafetyGateStatus.CLEAR


@pytest.mark.parametrize(("days", "found"), [(364, True), (365, True), (366, False)])
async def test_coded_signal_look_back_boundary(days: int, found: bool) -> None:
    p = person()
    cid = p.condition("R45.851", "Suicidal ideations", recorded=ago(days))
    result = await gate(p)
    assert (result.status is SafetyGateStatus.POSITIVE) is found
    if not found:
        assert [h.signal for h in result.history] == ["suicidal_ideation_code"]
        assert result.history[0].references[0].id == cid


async def test_the_latest_date_of_a_condition_counts() -> None:
    p = person()
    p.condition("Z91.51", "History of suicidal behavior", onset="2010", recorded=ago(30))
    assert (await gate(p)).status is SafetyGateStatus.POSITIVE


async def test_an_undated_signal_counts() -> None:
    p = person()
    p.condition("R45.851", "Suicidal ideations")
    result = await gate(p)
    assert result.status is SafetyGateStatus.POSITIVE
    assert result.evidence[0].date is None


async def test_a_signal_dated_after_the_as_of_date_is_ignored() -> None:
    p = person()
    p.condition("R45.851", "Suicidal ideations", recorded=(AS_OF + timedelta(days=1)).isoformat())
    result = await gate(p)
    assert result.status is SafetyGateStatus.CLEAR
    assert result.history == []


async def test_a_resolved_recent_condition_still_counts() -> None:
    p = person()
    p.condition("R45.851", "Suicidal ideations", recorded=ago(20), clinical="resolved")
    assert (await gate(p)).status is SafetyGateStatus.POSITIVE


async def test_entered_in_error_and_refuted_codes_do_not_count() -> None:
    p = person()
    p.condition("I10", "Essential hypertension", recorded=ago(10))
    p.condition("R45.851", "Suicidal ideations", recorded=ago(5), verification="refuted")
    p.condition(
        "R45.88", "Non-suicidal self-harm", recorded=ago(5), verification="entered-in-error"
    )
    assert (await gate(p)).status is SafetyGateStatus.CLEAR


async def test_an_encounter_reason_code_counts_with_the_condition() -> None:
    p = person()
    eid = p.encounter("EMER", f"{ago(3)}T10:00:00Z", reasons=(("R45.851", "Suicidal ideations"),))
    cid = p.condition("R45.851", "Suicidal ideations", recorded=ago(3))
    result = await gate(p)
    assert {r.id for r in result.evidence[0].references} == {eid, cid}


# --- psychiatric discharge ------------------------------------------------------------


def psych_stay(p: PersonaBuilder, discharged_days_ago: int | None, **kw: object) -> str:
    end = f"{ago(discharged_days_ago)}T11:00:00Z" if discharged_days_ago is not None else None
    start_days = (discharged_days_ago or 0) + 10
    return p.encounter(
        "IMP",
        f"{ago(start_days)}T09:00:00Z",
        end,
        service=str(kw.get("service", "psychiatric-inpatient")),
        status=str(kw.get("status", "finished")),
    )


@pytest.mark.parametrize(
    ("days", "signal"),
    [
        (0, "psychiatric_discharge_within_90_days"),
        (89, "psychiatric_discharge_within_90_days"),
        (90, "psychiatric_discharge_within_90_days"),
        (91, "psychiatric_discharge_within_365_days"),
        (364, "psychiatric_discharge_within_365_days"),
        (365, "psychiatric_discharge_within_365_days"),
    ],
)
async def test_discharge_windows_on_the_boundary_days(days: int, signal: str) -> None:
    p = person()
    eid = psych_stay(p, days)
    result = await gate(p)
    assert result.status is SafetyGateStatus.POSITIVE
    assert signals(result) == [signal]
    assert result.evidence[0].references[0].id == eid
    assert result.evidence[0].date == AS_OF - timedelta(days=days)


async def test_discharge_one_day_outside_the_window_is_history() -> None:
    p = person()
    psych_stay(p, 366)
    result = await gate(p)
    assert result.status is SafetyGateStatus.CLEAR
    assert [h.signal for h in result.history] == ["psychiatric_discharge_over_365_days"]


async def test_residential_stay_counts() -> None:
    p = person()
    psych_stay(p, 30, service="psychiatric-residential")
    assert signals(await gate(p)) == ["psychiatric_discharge_within_90_days"]


async def test_a_stay_without_a_discharge_date_counts_as_current() -> None:
    p = person()
    psych_stay(p, None, status="in-progress")
    result = await gate(p)
    assert signals(result) == ["psychiatric_stay_without_discharge_date"]
    assert result.evidence[0].date is None


@pytest.mark.parametrize(("start_days", "current"), [(365, True), (366, False)])
async def test_a_finished_stay_without_a_discharge_date_is_dated_by_its_start(
    start_days: int, current: bool
) -> None:
    p = person()
    p.encounter("IMP", f"{ago(start_days)}T09:00:00Z", service="psychiatric-inpatient")
    result = await gate(p)
    if current:
        assert signals(result) == ["psychiatric_stay_without_discharge_date"]
        assert result.evidence[0].date == AS_OF - timedelta(days=start_days)
    else:
        assert result.status is SafetyGateStatus.CLEAR
        assert [h.signal for h in result.history] == ["psychiatric_discharge_over_365_days"]


async def test_the_not_performed_reason_points_to_the_screening_history() -> None:
    result = await gate(person(), strict=True)
    check = next(c for c in result.checks if c.id == "phq9_item9")
    assert check.reason is not None
    assert "get_screening_history" in check.reason


async def test_a_discharge_after_the_as_of_date_means_the_stay_was_current() -> None:
    p = person()
    p.encounter(
        "IMP",
        f"{ago(5)}T09:00:00Z",
        f"{(AS_OF + timedelta(days=3)).isoformat()}T09:00:00Z",
        service="psychiatric-inpatient",
    )
    assert signals(await gate(p)) == ["psychiatric_stay_without_discharge_date"]


async def test_a_stay_starting_after_the_as_of_date_is_ignored() -> None:
    p = person()
    p.encounter(
        "IMP",
        f"{(AS_OF + timedelta(days=2)).isoformat()}T09:00:00Z",
        service="psychiatric-inpatient",
        status="in-progress",
    )
    assert (await gate(p)).status is SafetyGateStatus.CLEAR


@pytest.mark.parametrize("status", ["planned", "cancelled"])
async def test_planned_or_cancelled_stays_do_not_count(status: str) -> None:
    p = person()
    psych_stay(p, 10, status=status)
    assert (await gate(p)).status is SafetyGateStatus.CLEAR


async def test_a_non_psychiatric_inpatient_stay_does_not_count() -> None:
    p = person()
    p.encounter("IMP", f"{ago(20)}T09:00:00Z", f"{ago(15)}T09:00:00Z")
    assert (await gate(p)).status is SafetyGateStatus.CLEAR


async def test_the_recent_discharge_is_presented_first() -> None:
    p = person()
    p.condition("R45.851", "Suicidal ideations", recorded=ago(40))
    psych_stay(p, 40)
    result = await gate(p)
    assert signals(result) == ["psychiatric_discharge_within_90_days", "suicidal_ideation_code"]


# --- screening instruments ------------------------------------------------------------


def phq9_item9(p: PersonaBuilder, value: int, days: int = 10) -> str:
    return p.observation("44260-8", "PHQ-9 item 9", f"{ago(days)}T09:00:00Z", value=value)


@pytest.mark.parametrize(("value", "found"), [(0, False), (1, True), (3, True)])
async def test_phq9_item9_at_or_above_one(value: int, found: bool) -> None:
    p = person()
    phq9_item9(p, value)
    assert (outcome(await gate(p), "phq9_item9") is CheckOutcome.FOUND) is found


@pytest.mark.parametrize(("days", "found"), [(365, True), (366, False)])
async def test_phq9_item9_look_back(days: int, found: bool) -> None:
    p = person()
    phq9_item9(p, 2, days)
    result = await gate(p)
    assert (result.status is SafetyGateStatus.POSITIVE) is found
    assert bool(result.history) is not found


async def test_phq9_item9_from_a_questionnaire_response() -> None:
    p = person()
    qid = p.questionnaire_response(PHQ9_QUESTIONNAIRE, ago(10), {"9": 1, "total": 12})
    result = await gate(p)
    assert signals(result) == ["phq9_item9"]
    assert result.evidence[0].references[0].id == qid


async def test_a_cancelled_observation_carries_no_result() -> None:
    p = person()
    p.observation("44260-8", "PHQ-9 item 9", f"{ago(3)}T09:00:00Z", value=2, status="cancelled")
    assert outcome(await gate(p), "phq9_item9") is CheckOutcome.NOT_FOUND


async def test_questionnaire_answers_below_the_cutoff_or_unmapped_do_not_count() -> None:
    p = person()
    p.questionnaire_response(PHQ9_QUESTIONNAIRE, ago(10), {"9": 0, "total": 3})
    p.questionnaire_response("urn:adhd-mcp:synthetic-questionnaire:other", ago(10), {"9": 3})
    assert outcome(await gate(p), "phq9_item9") is CheckOutcome.NOT_FOUND


async def test_phq9_item9_as_a_panel_component() -> None:
    p = person()
    p.resources.append(
        {
            "resourceType": "Observation",
            "id": "t01-obs-component",
            "status": "final",
            "code": {"coding": [{"system": "http://loinc.org", "code": "44249-1"}]},
            "subject": {"reference": f"Patient/{p.patient_id}"},
            "effectiveDateTime": ago(4),
            "component": [
                {
                    "code": {"coding": [{"system": "http://loinc.org", "code": "44260-8"}]},
                    "valueInteger": 1,
                }
            ],
        }
    )
    assert signals(await gate(p)) == ["phq9_item9"]


async def test_a_negative_phq9_item9_never_clears_a_positive_cssrs() -> None:
    p = person()
    phq9_item9(p, 0, days=1)
    p.observation(
        "93374-7", "Suicide risk level", f"{ago(2)}T09:00:00Z", value_code=("LA6751-7", "Moderate")
    )
    result = await gate(p)
    assert result.status is SafetyGateStatus.POSITIVE
    assert outcome(result, "phq9_item9") is CheckOutcome.NOT_FOUND
    assert outcome(result, "cssrs_risk_level") is CheckOutcome.FOUND


@pytest.mark.parametrize(
    ("answer", "found"), [("LA9194-7", False), ("LA6751-7", True), ("LA9193-9", True)]
)
async def test_cssrs_moderate_or_high_risk_level(answer: str, found: bool) -> None:
    p = person()
    p.observation("93374-7", "Suicide risk level", f"{ago(5)}T09:00:00Z", value_code=(answer, ""))
    assert (outcome(await gate(p), "cssrs_risk_level") is CheckOutcome.FOUND) is found


async def test_cssrs_older_than_the_look_back_is_history() -> None:
    p = person()
    p.observation(
        "93374-7", "Suicide risk level", f"{ago(400)}T09:00:00Z", value_code=("LA9193-9", "")
    )
    result = await gate(p)
    assert result.status is SafetyGateStatus.CLEAR
    assert [h.signal for h in result.history] == ["cssrs_risk_level"]


# --- flags ----------------------------------------------------------------------------


async def test_an_active_high_risk_flag_counts() -> None:
    p = person()
    fid = p.flag("high-risk-for-suicide", ago(200))
    result = await gate(p)
    assert signals(result) == ["high_risk_flag"]
    assert result.evidence[0].references[0].id == fid


async def test_an_inactive_flag_is_history() -> None:
    p = person()
    p.flag("high-risk-for-suicide", ago(200), status="inactive")
    result = await gate(p)
    assert result.status is SafetyGateStatus.CLEAR
    assert [h.signal for h in result.history] == ["high_risk_flag"]


async def test_a_flag_that_ended_before_the_as_of_date_is_history() -> None:
    p = person()
    fid = p.flag("high-risk-for-suicide", ago(200))
    next(r for r in p.resources if r["id"] == fid)["period"]["end"] = ago(1)
    assert (await gate(p)).status is SafetyGateStatus.CLEAR


async def test_a_flag_starting_after_the_as_of_date_is_ignored() -> None:
    p = person()
    p.flag("high-risk-for-suicide", (AS_OF + timedelta(days=1)).isoformat())
    result = await gate(p)
    assert (result.status, result.history) == (SafetyGateStatus.CLEAR, [])


async def test_other_flags_do_not_count() -> None:
    p = person()
    p.flag("fall-risk", ago(10))
    assert (await gate(p)).status is SafetyGateStatus.CLEAR


# --- status, completeness and content -------------------------------------------------


async def test_an_empty_record_is_clear_with_limited_data() -> None:
    result = await gate(person())
    assert result.status is SafetyGateStatus.CLEAR_LIMITED_DATA
    assert {c.outcome for c in result.checks} == {CheckOutcome.NOT_FOUND}


async def test_a_record_with_data_and_no_signal_is_clear() -> None:
    p = person()
    p.condition("I10", "Essential hypertension", recorded=ago(10))
    assert (await gate(p)).status is SafetyGateStatus.CLEAR


async def test_every_check_is_listed_with_a_description() -> None:
    result = await gate(person())
    assert [c.id for c in result.checks] == [
        "suicidal_ideation_code",
        "suicide_attempt_code",
        "intentional_self_poisoning_code",
        "undetermined_intent_poisoning_code",
        "self_harm_asphyxiation_code",
        "nonsuicidal_self_harm_code",
        "self_harm_history_code",
        "psychiatric_discharge",
        "phq9_item9",
        "cssrs_risk_level",
        "high_risk_flag",
    ]
    assert all(c.description for c in result.checks)


async def test_strict_content_leaves_the_unverified_loinc_checks_not_performed() -> None:
    p = person()
    p.condition("I10", "Essential hypertension", recorded=ago(10))
    phq9_item9(p, 3)
    result = await gate(p, strict=True)
    assert result.status is SafetyGateStatus.CLEAR_LIMITED_DATA
    for check_id in ("phq9_item9", "cssrs_risk_level"):
        check = next(c for c in result.checks if c.id == check_id)
        assert check.outcome is CheckOutcome.NOT_PERFORMED
        assert check.reason is not None
        assert "not verified" in check.reason


async def test_strict_content_still_finds_verified_signals() -> None:
    p = person()
    p.condition("R45.851", "Suicidal ideations", recorded=ago(10))
    assert (await gate(p, strict=True)).status is SafetyGateStatus.POSITIVE


async def test_unmapped_site_concepts_leave_their_checks_not_performed(tmp_path: Path) -> None:
    path = tmp_path / "bare.toml"
    path.write_text('id = "bare"\nversion = "1"\ntitle = "No local codes"\n')
    site = load_site_codes_file(path, strict=True)
    p = person()
    psych_stay(p, 10)
    p.flag("high-risk-for-suicide", ago(10))
    result = await gate(p, gate_content=load_gate_content(site, strict=False))
    assert result.status is SafetyGateStatus.CLEAR_LIMITED_DATA
    for check_id in ("psychiatric_discharge", "high_risk_flag"):
        assert outcome(result, check_id) is CheckOutcome.NOT_PERFORMED


async def test_value_sets_refused_in_strict_mode_leave_the_check_not_performed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse_asphyxiation(value_set_id: str, *, strict: bool = True) -> ValueSet:
        if value_set_id == "safety.self_harm_asphyxiation" and strict:
            raise UnverifiedContentError("unverified")
        return load_value_set(value_set_id, strict=strict)

    monkeypatch.setattr("adhd_mcp.evidence.safety_gate.load_value_set", refuse_asphyxiation)
    result = await gate(person(), strict=True)
    assert outcome(result, "self_harm_asphyxiation_code") is CheckOutcome.NOT_PERFORMED


async def test_with_no_coded_check_active_conditions_are_not_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse_all(value_set_id: str, *, strict: bool = True) -> ValueSet:
        raise UnverifiedContentError("unverified")

    monkeypatch.setattr("adhd_mcp.evidence.safety_gate.load_value_set", refuse_all)
    records = PatientRecords(FailingAdapter(person(), {"Condition"}))
    result, notes = await assess_safety_gate(records, "t01-patient", AS_OF, content(strict=True))
    assert "Condition" not in [n.category for n in notes]
    assert result.status is SafetyGateStatus.CLEAR_LIMITED_DATA


async def failing_gate(p: PersonaBuilder, failing: set[str]) -> tuple[SafetyGateResult, list]:  # type: ignore[type-arg]
    records = PatientRecords(FailingAdapter(p, failing))
    return await assess_safety_gate(records, p.patient_id, AS_OF, content())


async def test_a_failed_category_makes_the_gate_data_unavailable() -> None:
    result, notes = await failing_gate(person(), {"Flag"})
    assert result.status is SafetyGateStatus.DATA_UNAVAILABLE
    check = next(c for c in result.checks if c.id == "high_risk_flag")
    assert check.outcome is CheckOutcome.FAILED
    assert check.reason == "Could not read Flag"
    assert {n.category: n.status for n in notes}["Flag"] is DataStatus.FAILED


async def test_a_signal_found_elsewhere_keeps_the_gate_positive_despite_a_failure() -> None:
    p = person()
    p.condition("R45.851", "Suicidal ideations", recorded=ago(10))
    result, _ = await failing_gate(p, {"Encounter", "Observation"})
    assert result.status is SafetyGateStatus.POSITIVE
    assert outcome(result, "suicidal_ideation_code") is CheckOutcome.FOUND
    assert outcome(result, "psychiatric_discharge") is CheckOutcome.FAILED


# Owner decision 2026-11-27 (open question 19): a check whose data was read only in part
# fails, exactly as if the data could not be read; the gate is then data_unavailable.


async def test_server_warnings_fail_the_checks_that_need_the_category() -> None:
    p = person()
    p.condition("I10", "Essential hypertension", recorded=ago(10))
    adapter = FixtureFhirAdapter(
        p.resources, warnings={"Condition": [SearchWarning(severity="warning", code="suppressed")]}
    )
    result, notes = await assess_safety_gate(
        PatientRecords(adapter), p.patient_id, AS_OF, content()
    )
    assert result.status is SafetyGateStatus.DATA_UNAVAILABLE
    assert {n.category: n.status for n in notes}["Condition"] is DataStatus.INCOMPLETE
    check = next(c for c in result.checks if c.id == "suicidal_ideation_code")
    assert check.outcome is CheckOutcome.FAILED
    assert check.reason == "Could not read Condition completely"
    assert outcome(result, "high_risk_flag") is CheckOutcome.NOT_FOUND


async def test_a_malformed_resource_makes_the_gate_data_unavailable() -> None:
    p = person()
    p.condition("F41.1", "Generalized anxiety disorder", recorded=ago(10))
    cid = p.condition("R45.851", "Suicidal ideations", recorded=ago(10))
    next(r for r in p.resources if r["id"] == cid)["recordedDate"] = "not-a-date"
    result, notes = await assess_safety_gate(
        PatientRecords(FixtureFhirAdapter(p.resources)), p.patient_id, AS_OF, content()
    )
    assert result.status is SafetyGateStatus.DATA_UNAVAILABLE
    assert {n.category: n.status for n in notes}["Condition"] is DataStatus.INCOMPLETE


async def test_a_signal_found_in_partly_read_data_keeps_the_gate_positive() -> None:
    p = person()
    p.condition("R45.851", "Suicidal ideations", recorded=ago(10))
    adapter = FixtureFhirAdapter(
        p.resources, warnings={"Condition": [SearchWarning(severity="warning", code="suppressed")]}
    )
    result, _ = await assess_safety_gate(PatientRecords(adapter), p.patient_id, AS_OF, content())
    assert result.status is SafetyGateStatus.POSITIVE
    assert outcome(result, "suicidal_ideation_code") is CheckOutcome.FOUND


async def test_a_failed_and_a_partly_read_category_are_both_named() -> None:
    p = person()
    adapter = FailingAdapter(p, {"Encounter"})
    adapter._warnings = {"Condition": (SearchWarning(severity="warning", code="suppressed"),)}
    result, _ = await assess_safety_gate(PatientRecords(adapter), p.patient_id, AS_OF, content())
    check = next(c for c in result.checks if c.id == "suicidal_ideation_code")
    assert check.reason == "Could not read Condition completely, Encounter"


async def test_completeness_covers_every_category_read() -> None:
    _, notes = await failing_gate(person(), set())
    assert [n.category for n in notes] == [
        "Condition",
        "Encounter",
        "Observation",
        "QuestionnaireResponse",
        "Flag",
    ]


async def test_strict_content_does_not_read_categories_only_inactive_checks_need() -> None:
    records = PatientRecords(FailingAdapter(person(), {"Observation", "QuestionnaireResponse"}))
    result, notes = await assess_safety_gate(records, "t01-patient", AS_OF, content(strict=True))
    assert result.status is SafetyGateStatus.CLEAR_LIMITED_DATA
    assert "Observation" not in [n.category for n in notes]


async def test_positive_output_wording_is_not_diagnostic() -> None:
    p = person()
    p.condition("R45.851", "Suicidal ideations", recorded=ago(10))
    result = await gate(p)
    assert_no_diagnostic_language(result.model_dump(mode="json"))


def test_definition_names_existing_value_sets_and_instruments() -> None:
    definition = load_gate_definition()
    assert definition.lookback_days == 365
    assert definition.discharge.recent_days == 90
    assert definition.discharge.lookback_days == 365
