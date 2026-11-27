"""Existing care: exclusions (ADHD code, open or recent referral, evaluation or care plan)
and the separate narcolepsy medication finding."""

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest

from adhd_mcp.evidence.existing_care import (
    ExistingCareResult,
    assemble_existing_care,
    load_existing_care_content,
)
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.models.domain import CheckOutcome
from adhd_mcp.terminology.site_codes import SiteCodes, load_site_codes, load_site_codes_file
from tests.helpers.failing_adapter import FailingAdapter
from tests.personas import all_resources
from tests.personas.builder import PersonaBuilder

pytestmark = pytest.mark.anyio

AS_OF = date(2026, 6, 15)
LOCAL = "urn:adhd-mcp:synthetic-local-code"


def ago(days: int) -> str:
    return (AS_OF - timedelta(days=days)).isoformat()


async def care(
    patient_id: str,
    resources: list[dict[str, Any]] | None = None,
    *,
    site: SiteCodes | None = None,
    as_of: date = AS_OF,
) -> ExistingCareResult:
    records = PatientRecords(FixtureFhirAdapter(resources or all_resources()))
    content = load_existing_care_content(site or load_site_codes("synthetic"))
    return await assemble_existing_care(records, patient_id, as_of, content)


def outcomes(result: ExistingCareResult) -> dict[str, CheckOutcome]:
    return {c.check: c.outcome for c in result.exclusions_checked}


def person() -> PersonaBuilder:
    return PersonaBuilder("t20", gender="male", birth_date="1985-01-01")


def request(
    p: PersonaBuilder,
    status: str,
    authored: str,
    *,
    code: str = "adhd-evaluation-referral",
    reason: str = "I10",
) -> str:
    return p.service_request(code, authored, status=status, reason=reason)


def add(p: PersonaBuilder, resource: dict[str, Any]) -> str:
    resource["subject"] = {"reference": f"Patient/{p.patient_id}"}
    p.resources.append(resource)
    return str(resource["id"])


def procedure(p: PersonaBuilder, status: str, performed: str) -> str:
    return add(
        p,
        {
            "resourceType": "Procedure",
            "id": f"t20-proc-{len(p.resources)}",
            "status": status,
            "code": {"coding": [{"system": LOCAL, "code": "adhd-evaluation"}]},
            "performedDateTime": performed,
        },
    )


def care_plan(p: PersonaBuilder, status: str, start: str, end: str | None = None) -> str:
    period = {"start": start} | ({"end": end} if end else {})
    return add(
        p,
        {
            "resourceType": "CarePlan",
            "id": f"t20-cp-{len(p.resources)}",
            "status": status,
            "intent": "plan",
            "category": [{"coding": [{"system": LOCAL, "code": "adhd-care-plan"}]}],
            "period": period,
        },
    )


# --- personas -------------------------------------------------------------------------


async def test_an_adhd_code_excludes_and_cites_condition_and_medication_reason() -> None:
    result = await care("p04-patient")
    assert result.excluded is True
    check = next(c for c in result.exclusions_checked if c.check == "adhd_diagnosis_code")
    assert check.outcome is CheckOutcome.FOUND
    assert [r.id for r in check.references] == ["p04-cond-1", "p04-medreq-1"]


async def test_p09_refuted_code_and_old_revoked_referral_do_not_exclude() -> None:
    result = await care("p09-patient")
    assert result.excluded is False
    assert set(outcomes(result).values()) == {CheckOutcome.NOT_FOUND}
    [item] = result.care_items
    assert (item.kind, item.status, item.excludes) == ("service_request", "revoked", False)
    assert item.references[0].id == "p09-sr-1"


async def test_narcolepsy_medication_is_a_separate_finding_not_an_exclusion() -> None:
    result = await care("p06-patient")
    assert result.excluded is False
    finding = result.narcolepsy
    assert finding is not None
    assert finding.medication_for_narcolepsy is True
    assert [r.id for r in finding.condition_references] == ["p06-cond-1"]
    assert [r.id for r in finding.medication_references] == [
        "p06-medreq-1",
        "p06-medreq-2",
        "p06-medreq-3",
    ]


@pytest.mark.parametrize("persona", ["p01", "p02", "p03", "p05", "p07", "p08", "p10"])
async def test_other_personas_are_not_excluded(persona: str) -> None:
    result = await care(f"{persona}-patient")
    assert result.excluded is False
    assert result.narcolepsy is None


# --- referrals and evaluations ---------------------------------------------------------


@pytest.mark.parametrize("status", ["draft", "active", "on-hold"])
async def test_an_open_referral_excludes(status: str) -> None:
    p = person()
    sid = request(p, status, ago(800))
    result = await care(p.patient_id, p.resources)
    assert result.excluded is True
    [item] = result.care_items
    assert (item.excludes, item.why) == (True, "open")
    assert item.references[0].id == sid


@pytest.mark.parametrize(("days", "excludes"), [(364, True), (365, True), (366, False)])
async def test_a_completed_referral_excludes_for_365_days(days: int, excludes: bool) -> None:
    p = person()
    request(p, "completed", ago(days))
    result = await care(p.patient_id, p.resources)
    assert result.excluded is excludes
    assert result.care_items[0].why == (
        "completed within 365 days" if excludes else "completed more than 365 days ago"
    )


@pytest.mark.parametrize("status", ["revoked", "unknown"])
async def test_other_statuses_are_reported_only(status: str) -> None:
    p = person()
    request(p, status, ago(10))
    result = await care(p.patient_id, p.resources)
    assert result.excluded is False
    assert result.care_items[0].why == f"status {status}"


async def test_an_entered_in_error_referral_is_not_listed() -> None:
    p = person()
    request(p, "entered-in-error", ago(10))
    result = await care(p.patient_id, p.resources)
    assert (result.excluded, result.care_items) == (False, [])


async def test_a_referral_is_recognised_by_an_adhd_or_attention_reason() -> None:
    p = person()
    request(p, "active", ago(10), code="psychology-referral", reason="R41.840")
    assert (await care(p.patient_id, p.resources)).excluded is True


async def test_unrelated_referrals_are_not_listed() -> None:
    p = person()
    request(p, "active", ago(10), code="cardiology-referral", reason="I10")
    result = await care(p.patient_id, p.resources)
    assert (result.excluded, result.care_items) == (False, [])


async def test_a_completed_referral_without_a_date_does_not_exclude() -> None:
    p = person()
    sid = request(p, "completed", ago(10))
    del next(r for r in p.resources if r["id"] == sid)["authoredOn"]
    result = await care(p.patient_id, p.resources)
    assert (result.excluded, result.care_items[0].why) == (False, "completed, date unknown")


@pytest.mark.parametrize(
    ("status", "days", "excludes"),
    [("completed", 100, True), ("completed", 400, False), ("in-progress", 400, True)],
)
async def test_evaluation_procedures(status: str, days: int, excludes: bool) -> None:
    p = person()
    procedure(p, status, ago(days))
    assert (await care(p.patient_id, p.resources)).excluded is excludes


@pytest.mark.parametrize(
    ("status", "days", "excludes"),
    [("active", 800, True), ("completed", 30, True), ("completed", 400, False)],
)
async def test_care_plans(status: str, days: int, excludes: bool) -> None:
    p = person()
    care_plan(p, status, ago(days))
    result = await care(p.patient_id, p.resources)
    assert result.excluded is excludes
    assert result.care_items[0].kind == "care_plan"


async def test_items_dated_after_the_as_of_date_are_ignored() -> None:
    p = person()
    request(p, "active", (AS_OF + timedelta(days=1)).isoformat())
    p.condition("F90.0", "ADHD", recorded=(AS_OF + timedelta(days=1)).isoformat())
    result = await care(p.patient_id, p.resources)
    assert (result.excluded, result.care_items) == (False, [])


# --- reporting ------------------------------------------------------------------------


async def test_unmapped_concepts_leave_checks_not_performed(tmp_path: Path) -> None:
    path = tmp_path / "bare.toml"
    path.write_text('id = "bare"\nversion = "1"\ntitle = "No local codes"\n')
    p = person()
    procedure(p, "completed", ago(10))
    result = await care(p.patient_id, p.resources, site=load_site_codes_file(path, strict=True))
    assert outcomes(result)["adhd_evaluation_procedure"] is CheckOutcome.NOT_PERFORMED
    assert outcomes(result)["adhd_care_plan"] is CheckOutcome.NOT_PERFORMED
    assert outcomes(result)["adhd_referral"] is CheckOutcome.NOT_FOUND
    assert result.excluded is None  # a check could not run: not a clean "not in care"


async def test_a_failed_read_leaves_the_answer_unknown() -> None:
    p = person()
    records = PatientRecords(FailingAdapter(p, {"ServiceRequest"}))
    content = load_existing_care_content(load_site_codes("synthetic"))
    result = await assemble_existing_care(records, p.patient_id, AS_OF, content)
    assert result.excluded is None
    assert outcomes(result)["adhd_referral"] is CheckOutcome.FAILED


async def test_a_found_exclusion_stands_despite_a_failure() -> None:
    p = person()
    p.condition("F90.2", "ADHD, combined type", recorded=ago(100))
    records = PatientRecords(FailingAdapter(p, {"CarePlan"}))
    content = load_existing_care_content(load_site_codes("synthetic"))
    result = await assemble_existing_care(records, p.patient_id, AS_OF, content)
    assert result.excluded is True


async def test_narcolepsy_code_without_medication_is_still_reported() -> None:
    p = person()
    p.condition("G47.419", "Narcolepsy without cataplexy", recorded=ago(100))
    finding = (await care(p.patient_id, p.resources)).narcolepsy
    assert finding is not None
    assert (finding.medication_for_narcolepsy, finding.medication_references) == (False, [])


async def test_every_category_read_is_in_the_completeness_note() -> None:
    result = await care("p07-patient")
    assert [n.category for n in result.data_completeness] == [
        "Condition",
        "ServiceRequest",
        "Procedure",
        "CarePlan",
        "MedicationRequest",
        "MedicationStatement",
    ]


@pytest.mark.parametrize(("end_days", "excludes"), [(365, True), (366, False)])
async def test_a_completed_care_plan_is_dated_by_its_end(end_days: int, excludes: bool) -> None:
    p = person()
    care_plan(p, "completed", ago(900), ago(end_days))
    result = await care(p.patient_id, p.resources)
    assert result.excluded is excludes
    assert result.care_items[0].date == AS_OF - timedelta(days=end_days)


async def test_a_completed_evaluation_is_dated_by_the_end_of_its_period() -> None:
    p = person()
    pid = procedure(p, "completed", ago(900))
    resource = next(r for r in p.resources if r["id"] == pid)
    del resource["performedDateTime"]
    resource["performedPeriod"] = {"start": ago(900), "end": ago(30)}
    assert (await care(p.patient_id, p.resources)).excluded is True


async def test_incomplete_data_leaves_the_answer_unknown() -> None:
    p = person()
    sid = request(p, "active", ago(10))
    next(r for r in p.resources if r["id"] == sid)["authoredOn"] = "not-a-date"
    result = await care(p.patient_id, p.resources)
    assert result.excluded is None


async def test_an_unexpected_status_string_is_not_passed_through() -> None:
    p = person()
    request(p, "Patient has ADHD", ago(10))
    [item] = (await care(p.patient_id, p.resources)).care_items
    assert (item.status, item.why) == ("unrecognized", "status unrecognized")
