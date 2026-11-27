"""Existing care: is the patient already diagnosed, referred or being evaluated for ADHD?

Exclusions: a recorded ADHD code; an ADHD referral, evaluation or care plan that is open or
was completed within the window (dated by authored, performed or period start). Older and
revoked items are reported, not counted. Medication for narcolepsy is a separate finding,
never an exclusion.
"""

import asyncio
import re
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from functools import cache
from importlib.resources import files
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from adhd_mcp.evidence.common import completeness, not_after, read_category
from adhd_mcp.fhir.dates import DateRange
from adhd_mcp.fhir.reader import PatientRecords, ReadResult
from adhd_mcp.fhir.records import (
    CarePlanRecord,
    ConditionRecord,
    MedicationRecord,
    ProcedureRecord,
    ServiceRequestRecord,
)
from adhd_mcp.models.domain import CheckOutcome, DataCompleteness, ExclusionCheck, ResourceRef
from adhd_mcp.models.evidence_outputs import CareItem, NarcolepsyFinding
from adhd_mcp.terminology import ValueSet, load_value_set
from adhd_mcp.terminology.site_codes import SiteCodes

_UNMAPPED = "Not performed: no local codes are mapped for it at this site."
#: FHIR status codes are short lowercase tokens; anything else is not passed through.
_STATUS_CODE = re.compile(r"[a-z][a-z-]{0,31}")


class ExistingCareDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    version: str
    diagnosis_value_set: str
    referral_reason_value_sets: tuple[str, ...]
    open_statuses: tuple[str, ...]
    completed_window_days: int
    narcolepsy_value_set: str


@cache
def _definition() -> ExistingCareDefinition:
    raw = files("adhd_mcp.data").joinpath("existing_care.toml").read_text(encoding="utf-8")
    return ExistingCareDefinition.model_validate(tomllib.loads(raw))


@dataclass(frozen=True)
class ExistingCareContent:
    definition: ExistingCareDefinition
    site: SiteCodes
    diagnosis: ValueSet
    referral_reasons: tuple[ValueSet, ...]
    narcolepsy: ValueSet


def load_existing_care_content(site: SiteCodes) -> ExistingCareContent:
    d = _definition()
    return ExistingCareContent(
        definition=d,
        site=site,
        diagnosis=load_value_set(d.diagnosis_value_set),
        referral_reasons=tuple(load_value_set(v) for v in d.referral_reason_value_sets),
        narcolepsy=load_value_set(d.narcolepsy_value_set),
    )


@dataclass(frozen=True)
class ExistingCareResult:
    excluded: bool | None
    exclusions_checked: list[ExclusionCheck]
    care_items: list[CareItem]
    narcolepsy: NarcolepsyFinding | None
    data_completeness: list[DataCompleteness]
    definition_version: str


def _records[R: BaseModel](result: ReadResult[R] | None) -> tuple[R, ...]:
    return result.records if result is not None else ()


def _day(when: DateRange | None, status: str | None) -> date | None:
    """A completed item is dated by its end (when it was completed), else its start. A
    ServiceRequest has no completion date, so its authored date is used."""
    if when is None:
        return None
    if status == "completed" and when.end is not None:
        return when.end
    return when.start if when.start is not None else when.end


def _status(raw: str | None) -> str | None:
    if raw is None or _STATUS_CODE.fullmatch(raw):
        return raw
    return "unrecognized"


def _assess(
    status: str | None, when: date | None, d: ExistingCareDefinition, as_of: date
) -> tuple[bool, str]:
    """Whether an item excludes, and why."""
    if status in d.open_statuses:
        return True, "open"
    if status == "completed":
        if when is None:
            return False, "completed, date unknown"
        if (as_of - when).days <= d.completed_window_days:
            return True, f"completed within {d.completed_window_days} days"
        return False, f"completed more than {d.completed_window_days} days ago"
    return False, f"status {status}"


def _item(
    kind: Literal["service_request", "procedure", "care_plan"],
    ref: ResourceRef,
    status: str | None,
    when: DateRange | None,
    *,
    content: ExistingCareContent,
    as_of: date,
) -> CareItem:
    status = _status(status)
    day = _day(when, status)
    excludes, why = _assess(status, day, content.definition, as_of)
    return CareItem(
        kind=kind, status=status, date=day, excludes=excludes, why=why, references=[ref]
    )


def _sorted(refs: Sequence[ResourceRef]) -> list[ResourceRef]:
    """Unique references in a stable order, whatever order the server returned them in."""
    return sorted(set(refs), key=lambda r: (r.resource_type, r.id))


def _check(
    check: str,
    description: str,
    refs: Sequence[ResourceRef],
    *,
    failed: list[str],
    not_performed: bool = False,
) -> ExclusionCheck:
    if not_performed:
        return ExclusionCheck(
            check=check,
            description=description,
            outcome=CheckOutcome.NOT_PERFORMED,
            reason=_UNMAPPED,
        )
    if refs:
        return ExclusionCheck(
            check=check,
            description=description,
            outcome=CheckOutcome.FOUND,
            references=_sorted(refs),
        )
    if failed:
        return ExclusionCheck(
            check=check,
            description=description,
            outcome=CheckOutcome.FAILED,
            reason=f"Could not read {', '.join(failed)}",
        )
    return ExclusionCheck(check=check, description=description, outcome=CheckOutcome.NOT_FOUND)


def _referral_related(sr: ServiceRequestRecord, content: ExistingCareContent) -> bool:
    if content.site.matches("adhd_evaluation_request", sr.codes):
        return True
    return any(vs.matching_codings(sr.reason_codes) for vs in content.referral_reasons)


async def assemble_existing_care(
    records: PatientRecords, patient_id: str, as_of: date, content: ExistingCareContent
) -> ExistingCareResult:
    reads: tuple[Any, ...] = await asyncio.gather(
        read_category(records.conditions(patient_id)),
        read_category(records.service_requests(patient_id)),
        read_category(records.procedures(patient_id)),
        read_category(records.care_plans(patient_id)),
        read_category(records.medication_requests(patient_id)),
        read_category(records.medication_statements(patient_id)),
    )
    names = (
        "Condition",
        "ServiceRequest",
        "Procedure",
        "CarePlan",
        "MedicationRequest",
        "MedicationStatement",
    )
    notes = [completeness(n, r) for n, r in zip(names, reads, strict=True)]
    failed = {n.category for n in notes if n.status == "failed"}
    conditions: Sequence[ConditionRecord] = [
        c for c in _records(reads[0]) if not_after(c.onset or c.recorded, as_of)
    ]
    requests: Sequence[ServiceRequestRecord] = [
        s for s in _records(reads[1]) if not_after(s.authored, as_of)
    ]
    procedures: Sequence[ProcedureRecord] = [
        p for p in _records(reads[2]) if not_after(p.performed, as_of)
    ]
    plans: Sequence[CarePlanRecord] = [c for c in _records(reads[3]) if not_after(c.period, as_of)]
    medications: Sequence[MedicationRecord] = [
        m for m in (*_records(reads[4]), *_records(reads[5])) if not_after(m.date, as_of)
    ]
    site = content.site

    diagnosis_refs = [c.ref for c in conditions if content.diagnosis.matching_codings(c.codes)]
    diagnosis_refs += [
        m.ref for m in medications if content.diagnosis.matching_codings(m.reason_codes)
    ]

    items = [
        _item("service_request", s.ref, s.status, s.authored, content=content, as_of=as_of)
        for s in requests
        if _referral_related(s, content)
    ]
    items += [
        _item("procedure", p.ref, p.status, p.performed, content=content, as_of=as_of)
        for p in procedures
        if site.matches("adhd_evaluation_procedure", p.codes)
    ]
    items += [
        _item("care_plan", c.ref, c.status, c.period, content=content, as_of=as_of)
        for c in plans
        if site.matches("adhd_care_plan", c.categories)
    ]

    def excluding(kind: str) -> list[ResourceRef]:
        return [r for i in items if i.kind == kind and i.excludes for r in i.references]

    def failures(*categories: str) -> list[str]:
        return [c for c in categories if c in failed]

    days = content.definition.completed_window_days
    checks = [
        _check(
            "adhd_diagnosis_code",
            "ADHD code (F90) on a Condition or as a medication reason",
            diagnosis_refs,
            failed=failures("Condition", "MedicationRequest", "MedicationStatement"),
        ),
        _check(
            "adhd_referral",
            f"ADHD referral or evaluation request, open or completed within {days} days",
            excluding("service_request"),
            failed=failures("ServiceRequest"),
        ),
        _check(
            "adhd_evaluation_procedure",
            f"ADHD evaluation in progress or completed within {days} days",
            excluding("procedure"),
            failed=failures("Procedure"),
            not_performed=not site.maps("adhd_evaluation_procedure"),
        ),
        _check(
            "adhd_care_plan",
            f"ADHD care plan, open or completed within {days} days",
            excluding("care_plan"),
            failed=failures("CarePlan"),
            not_performed=not site.maps("adhd_care_plan"),
        ),
    ]
    outcomes = {c.outcome for c in checks}
    # "Not in care" only when every check ran on complete data; otherwise unknown.
    complete = all(n.status in {"available", "empty"} for n in notes)
    excluded: bool | None = None
    if CheckOutcome.FOUND in outcomes:
        excluded = True
    elif complete and outcomes == {CheckOutcome.NOT_FOUND}:
        excluded = False

    narcolepsy_refs = [c.ref for c in conditions if content.narcolepsy.matching_codings(c.codes)]
    narcolepsy = None
    if narcolepsy_refs:
        medication_refs = [
            m.ref for m in medications if content.narcolepsy.matching_codings(m.reason_codes)
        ]
        narcolepsy = NarcolepsyFinding(
            condition_references=_sorted(narcolepsy_refs),
            medication_for_narcolepsy=bool(medication_refs),
            medication_references=_sorted(medication_refs),
        )
    items.sort(key=lambda i: (i.kind, i.date or date.min, i.references[0].id))
    return ExistingCareResult(
        excluded=excluded,
        exclusions_checked=checks,
        care_items=items,
        narcolepsy=narcolepsy,
        data_completeness=notes,
        definition_version=content.definition.version,
    )
