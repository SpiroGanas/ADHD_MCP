"""The safety gate: self-harm signals that must be addressed before any screening referral.

The checks, look-back windows and value sets are data (``data/safety_gate.toml``); local
codes come from the site code mapping. Content that cannot be loaded strictly (unverified
codes or cutoffs, or concepts the site does not map) leaves its check "not performed", and
the gate then never reports a plain "clear" (owner decision 2026-11-27).

This module reports what the record contains. It never assesses suicide risk.
"""

import asyncio
import tomllib
from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date
from functools import cache
from importlib.resources import files
from typing import Any

from pydantic import BaseModel, ConfigDict

from adhd_mcp.evidence.common import completeness, in_window, latest, not_after, read_category
from adhd_mcp.fhir.codes import Coding
from adhd_mcp.fhir.dates import DatePrecision, DateRange
from adhd_mcp.fhir.reader import PatientRecords, ReadResult
from adhd_mcp.fhir.records import (
    ConditionRecord,
    EncounterRecord,
    FlagRecord,
    ObservationRecord,
    QuestionnaireResponseRecord,
    Value,
)
from adhd_mcp.models.domain import (
    CheckOutcome,
    DataCompleteness,
    EvidenceItem,
    ResourceRef,
    SafetyCheck,
    SafetyGateResult,
    SafetyGateStatus,
)
from adhd_mcp.terminology import UnverifiedContentError, ValueSet, load_value_set
from adhd_mcp.terminology.instruments import Instrument, load_instrument
from adhd_mcp.terminology.site_codes import QuestionnaireMapping, SiteCodes
from adhd_mcp.wording import load_wording

#: Encounter statuses that are not a stay that happened.
_NOT_A_STAY = frozenset({"planned", "cancelled", "entered-in-error"})
#: Observation statuses that carry no result.
_NO_RESULT = frozenset({"registered", "cancelled", "entered-in-error"})

# --- definition ----------------------------------------------------------------------


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ConditionCheckDef(_Frozen):
    id: str
    description: str
    value_sets: tuple[str, ...]


class DischargeDef(_Frozen):
    id: str
    description: str
    recent_days: int
    lookback_days: int
    concepts: tuple[str, ...]


class InstrumentItemDef(_Frozen):
    id: str
    description: str
    instrument: str
    item: str
    cutoff: str


class RiskLevelDef(_Frozen):
    id: str
    description: str
    instrument: str


class FlagDef(_Frozen):
    id: str
    description: str
    concept: str


class SafetyGateDefinition(_Frozen):
    id: str
    version: str
    lookback_days: int
    condition_checks: tuple[ConditionCheckDef, ...]
    discharge: DischargeDef
    phq9_item9: InstrumentItemDef
    cssrs: RiskLevelDef
    flag: FlagDef


@cache
def load_gate_definition() -> SafetyGateDefinition:
    raw = files("adhd_mcp.data").joinpath("safety_gate.toml").read_text(encoding="utf-8")
    return SafetyGateDefinition.model_validate(tomllib.loads(raw))


# --- content: definition plus loaded terminology -------------------------------------

_UNVERIFIED = (
    "Not performed: its codes or cutoffs are not verified yet. Any recorded results are "
    "listed by get_screening_history for clinician review."
)
_UNMAPPED = "Not performed: no local codes are mapped for it at this site."


@dataclass(frozen=True)
class GateContent:
    """The definition with its terminology loaded. ``not_performed`` maps a check id to the
    reason it cannot run."""

    definition: SafetyGateDefinition
    site: SiteCodes
    value_sets: dict[str, tuple[ValueSet, ...]] = field(default_factory=dict)
    phq9: Instrument | None = None
    cssrs: Instrument | None = None
    not_performed: dict[str, str] = field(default_factory=dict)


def _instrument(instrument_id: str, strict: bool) -> Instrument | None:
    try:
        return load_instrument(instrument_id, strict=strict)
    except UnverifiedContentError:
        return None


def load_gate_content(site: SiteCodes, *, strict: bool = True) -> GateContent:
    """Load the gate's terminology. ``strict=True`` is the only mode the server uses."""
    definition = load_gate_definition()
    value_sets: dict[str, tuple[ValueSet, ...]] = {}
    not_performed: dict[str, str] = {}
    for check in definition.condition_checks:
        try:
            value_sets[check.id] = tuple(load_value_set(v, strict=strict) for v in check.value_sets)
        except UnverifiedContentError:
            not_performed[check.id] = _UNVERIFIED
    if not any(site.maps(c) for c in definition.discharge.concepts):
        not_performed[definition.discharge.id] = _UNMAPPED
    phq9 = _instrument(definition.phq9_item9.instrument, strict)
    if phq9 is None:
        not_performed[definition.phq9_item9.id] = _UNVERIFIED
    cssrs = _instrument(definition.cssrs.instrument, strict)
    if cssrs is None:
        not_performed[definition.cssrs.id] = _UNVERIFIED
    if not site.maps(definition.flag.concept):
        not_performed[definition.flag.id] = _UNMAPPED
    return GateContent(definition, site, value_sets, phq9, cssrs, not_performed)


# --- evaluation ----------------------------------------------------------------------


@dataclass
class _Hits:
    """References found by one check, split by whether they count now."""

    current: list[tuple[str, ResourceRef, DateRange | None]] = field(default_factory=list)
    history: list[tuple[str, ResourceRef, DateRange | None]] = field(default_factory=list)


def _date_of(when: DateRange | None) -> date | None:
    if when is None:
        return None
    return when.end if when.end is not None else when.start


def _items(hits: Iterable[tuple[str, ResourceRef, DateRange | None]]) -> list[EvidenceItem]:
    """One evidence item per signal, citing every reference, dated by the latest one."""
    grouped: dict[str, list[tuple[ResourceRef, DateRange | None]]] = {}
    for signal, ref, when in hits:
        grouped.setdefault(signal, []).append((ref, when))
    items = []
    for signal, found in grouped.items():
        refs = sorted({ref for ref, _ in found}, key=lambda r: (r.resource_type, r.id))
        dates = [w for _, w in found]
        when = None if any(w is None for w in dates) else latest(*dates)
        items.append(EvidenceItem(signal=signal, references=refs, date=_date_of(when)))
    return items


def _sort_by_window(
    hits: _Hits, signal: str, ref: ResourceRef, when: DateRange | None, *, as_of: date, days: int
) -> None:
    if not not_after(when, as_of):
        return
    inside = in_window(when, as_of=as_of, days=days)
    (hits.history if inside is False else hits.current).append((signal, ref, when))


def _matches(value_sets: Sequence[ValueSet], codings: tuple[Coding, ...]) -> bool:
    return any(vs.matching_codings(codings) for vs in value_sets)


def _condition_hits(
    check: ConditionCheckDef,
    value_sets: Sequence[ValueSet],
    *,
    conditions: Sequence[ConditionRecord],
    encounters: Sequence[EncounterRecord],
    as_of: date,
    days: int,
) -> _Hits:
    hits = _Hits()
    for c in conditions:
        if _matches(value_sets, c.codes):
            _sort_by_window(
                hits, check.id, c.ref, latest(c.recorded, c.onset), as_of=as_of, days=days
            )
    for e in encounters:
        if _matches(value_sets, e.reason_codes):
            _sort_by_window(hits, check.id, e.ref, e.period, as_of=as_of, days=days)
    return hits


def _discharge_hits(
    definition: DischargeDef, site: SiteCodes, encounters: Sequence[EncounterRecord], as_of: date
) -> _Hits:
    hits = _Hits()
    for e in encounters:
        codings = e.types + e.service_type
        if e.status in _NOT_A_STAY or not any(
            site.matches(c, codings) for c in definition.concepts
        ):
            continue
        started = e.period.start if e.period is not None else None
        if started is not None and started > as_of:
            continue
        discharged = e.period.end if e.period is not None else None
        older = f"psychiatric_discharge_over_{definition.lookback_days}_days"
        if discharged is None or discharged > as_of:
            # No discharge as of this date. A finished stay with no end date is dated by
            # its start, so an old record does not count as current forever.
            if e.status == "finished" and started is not None and discharged is None:
                when = DateRange(start=started, end=started, precision=DatePrecision.DAY)
                current = (as_of - started).days <= definition.lookback_days
                target = hits.current if current else hits.history
                name = "psychiatric_stay_without_discharge_date" if current else older
                target.append((name, e.ref, when))
            else:
                hits.current.append(("psychiatric_stay_without_discharge_date", e.ref, None))
            continue
        when = DateRange(start=discharged, end=discharged, precision=DatePrecision.DAY)
        days_ago = (as_of - discharged).days
        if days_ago <= definition.recent_days:
            name = f"psychiatric_discharge_within_{definition.recent_days}_days"
            hits.current.append((name, e.ref, when))
        elif days_ago <= definition.lookback_days:
            name = f"psychiatric_discharge_within_{definition.lookback_days}_days"
            hits.current.append((name, e.ref, when))
        else:
            hits.history.append((older, e.ref, when))
    return hits


def _observation_values(record: ObservationRecord, system: str, code: str) -> list[Value]:
    """Values recorded under ``code``, on the observation itself or in its components."""
    if record.status in _NO_RESULT:
        return []
    values = []
    if any(c.system == system and c.code == code for c in record.codes) and record.value:
        values.append(record.value)
    for comp in record.components:
        if any(c.system == system and c.code == code for c in comp.codes) and comp.value:
            values.append(comp.value)
    return values


def _phq9_hits(
    definition: InstrumentItemDef,
    phq9: Instrument,
    site: SiteCodes,
    *,
    observations: Sequence[ObservationRecord],
    responses: Sequence[QuestionnaireResponseRecord],
    as_of: date,
    days: int,
) -> _Hits:
    system, code = phq9.code_for("item", definition.item)
    cutoff = phq9.cutoff(definition.cutoff)
    hits = _Hits()

    def positive(values: Iterable[Value]) -> bool:
        return any(v.number is not None and cutoff.is_met(v.number) for v in values)

    for o in observations:
        if positive(_observation_values(o, system, code)):
            _sort_by_window(hits, definition.id, o.ref, o.effective, as_of=as_of, days=days)
    for r in responses:
        mapping: QuestionnaireMapping | None = site.questionnaire(r.questionnaire)
        if mapping is None or mapping.instrument != phq9.id:
            continue
        link_id = mapping.items.get(definition.item)
        answers = [a for i in r.items if i.link_id == link_id for a in i.answers]
        if positive(answers):
            _sort_by_window(hits, definition.id, r.ref, r.authored, as_of=as_of, days=days)
    return hits


def _cssrs_hits(
    definition: RiskLevelDef,
    cssrs: Instrument,
    *,
    observations: Sequence[ObservationRecord],
    as_of: date,
    days: int,
) -> _Hits:
    system, code = cssrs.code_for("risk_level")
    positive = {(a.system, a.code) for a in cssrs.answers if a.for_code == code and a.positive}
    hits = _Hits()
    for o in observations:
        values = _observation_values(o, system, code)
        if any((c.system, c.code) in positive for v in values for c in v.codings):
            _sort_by_window(hits, definition.id, o.ref, o.effective, as_of=as_of, days=days)
    return hits


def _flag_hits(
    definition: FlagDef, site: SiteCodes, flags: Sequence[FlagRecord], as_of: date
) -> _Hits:
    hits = _Hits()
    for f in flags:
        if not site.matches(definition.concept, f.codes) or not not_after(f.period, as_of):
            continue
        ended = f.period is not None and f.period.end is not None and f.period.end < as_of
        target = hits.current if f.status == "active" and not ended else hits.history
        target.append((definition.id, f.ref, f.period))
    return hits


# --- assembly ------------------------------------------------------------------------

_CATEGORY_ORDER = ("Condition", "Encounter", "Observation", "QuestionnaireResponse", "Flag")


def _needed_categories(content: GateContent) -> set[str]:
    d, skip = content.definition, content.not_performed
    needed: set[str] = set()
    if any(c.id not in skip for c in d.condition_checks):
        needed |= {"Condition", "Encounter"}
    if d.discharge.id not in skip:
        needed.add("Encounter")
    if d.phq9_item9.id not in skip:
        needed |= {"Observation", "QuestionnaireResponse"}
    if d.cssrs.id not in skip:
        needed.add("Observation")
    if d.flag.id not in skip:
        needed.add("Flag")
    return needed


async def _maybe[R: BaseModel](
    wanted: bool, read: Callable[[], Awaitable[ReadResult[R]]]
) -> ReadResult[R] | None:
    return await read_category(read()) if wanted else None


def _records[R: BaseModel](result: ReadResult[R] | None) -> tuple[R, ...]:
    return result.records if result is not None else ()


def _check(
    check_id: str,
    description: str,
    content: GateContent,
    hits: _Hits | None,
    failed: list[str],
) -> SafetyCheck:
    if check_id in content.not_performed:
        outcome, reason = CheckOutcome.NOT_PERFORMED, content.not_performed[check_id]
    elif hits is not None and hits.current:
        outcome, reason = CheckOutcome.FOUND, None
    elif failed:
        outcome, reason = CheckOutcome.FAILED, f"Could not read {', '.join(failed)}"
    else:
        outcome, reason = CheckOutcome.NOT_FOUND, None
    return SafetyCheck(id=check_id, description=description, outcome=outcome, reason=reason)


async def assess_safety_gate(
    records: PatientRecords, patient_id: str, as_of: date, content: GateContent
) -> tuple[SafetyGateResult, list[DataCompleteness]]:
    """Run every check against the patient's record as of ``as_of``.

    Returns the gate result and a completeness note for each category read.
    """
    d, site = content.definition, content.site
    needed = _needed_categories(content)
    conditions, encounters, observations, responses, flags = await asyncio.gather(
        _maybe("Condition" in needed, lambda: records.conditions(patient_id)),
        _maybe("Encounter" in needed, lambda: records.encounters(patient_id)),
        _maybe("Observation" in needed, lambda: records.observations(patient_id)),
        _maybe(
            "QuestionnaireResponse" in needed,
            lambda: records.questionnaire_responses(patient_id),
        ),
        _maybe("Flag" in needed, lambda: records.flags(patient_id)),
    )
    read: dict[str, ReadResult[Any] | None] = {
        "Condition": conditions,
        "Encounter": encounters,
        "Observation": observations,
        "QuestionnaireResponse": responses,
        "Flag": flags,
    }
    notes = [completeness(c, read[c]) for c in _CATEGORY_ORDER if c in needed]
    # A check whose data was read only in part fails, exactly like one whose data could not
    # be read: partial data never supports "not found" (owner decision 2026-11-27).
    unreadable = {
        n.category: ("" if n.status == "failed" else " completely")
        for n in notes
        if n.status in ("failed", "incomplete")
    }

    def failures(*categories: str) -> list[str]:
        return [f"{c}{unreadable[c]}" for c in categories if c in unreadable]

    checks: list[SafetyCheck] = []
    all_hits: list[_Hits] = []

    def record(check_id: str, description: str, hits: _Hits | None, *categories: str) -> None:
        checks.append(_check(check_id, description, content, hits, failures(*categories)))
        if hits is not None:
            all_hits.append(hits)

    discharge_hits = None
    if d.discharge.id not in content.not_performed:
        discharge_hits = _discharge_hits(d.discharge, site, _records(encounters), as_of)

    for cc in d.condition_checks:
        hits = None
        if cc.id not in content.not_performed:
            hits = _condition_hits(
                cc,
                content.value_sets[cc.id],
                conditions=_records(conditions),
                encounters=_records(encounters),
                as_of=as_of,
                days=d.lookback_days,
            )
        record(cc.id, cc.description, hits, "Condition", "Encounter")
    record(d.discharge.id, d.discharge.description, discharge_hits, "Encounter")

    phq9_hits = None
    if content.phq9 is not None:
        phq9_hits = _phq9_hits(
            d.phq9_item9,
            content.phq9,
            site,
            observations=_records(observations),
            responses=_records(responses),
            as_of=as_of,
            days=d.lookback_days,
        )
    record(
        d.phq9_item9.id,
        d.phq9_item9.description,
        phq9_hits,
        "Observation",
        "QuestionnaireResponse",
    )

    cssrs_hits = None
    if content.cssrs is not None:
        cssrs_hits = _cssrs_hits(
            d.cssrs,
            content.cssrs,
            observations=_records(observations),
            as_of=as_of,
            days=d.lookback_days,
        )
    record(d.cssrs.id, d.cssrs.description, cssrs_hits, "Observation")

    flag_hits = None
    if d.flag.id not in content.not_performed:
        flag_hits = _flag_hits(d.flag, site, _records(flags), as_of)
    record(d.flag.id, d.flag.description, flag_hits, "Flag")

    # The most recent discharge is the highest-priority signal, so it is presented first.
    ordered = ([discharge_hits] if discharge_hits else []) + [
        h for h in all_hits if h is not discharge_hits
    ]
    evidence = _items(hit for h in ordered for hit in h.current)
    history = _items(hit for h in ordered for hit in h.history)
    return _result(checks, evidence, history, notes), notes


def _result(
    checks: list[SafetyCheck],
    evidence: list[EvidenceItem],
    history: list[EvidenceItem],
    notes: list[DataCompleteness],
) -> SafetyGateResult:
    outcomes = {c.outcome for c in checks}
    guidance = None
    if CheckOutcome.FOUND in outcomes:
        status = SafetyGateStatus.POSITIVE
        guidance = load_wording().safety_gate_guidance
    elif CheckOutcome.FAILED in outcomes:
        status = SafetyGateStatus.DATA_UNAVAILABLE
    elif (
        CheckOutcome.NOT_PERFORMED in outcomes
        or all(n.records == 0 for n in notes)
        or any(n.status == "incomplete" for n in notes)
    ):
        status = SafetyGateStatus.CLEAR_LIMITED_DATA
    else:
        status = SafetyGateStatus.CLEAR
    return SafetyGateResult(
        status=status, checks=checks, evidence=evidence, history=history, guidance=guidance
    )
