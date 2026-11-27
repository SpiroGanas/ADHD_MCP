"""Utilization: acute care and injury visits, crashes as driver, psychiatric stays and the
overall record volume, counted in windows before the as-of date."""

import asyncio
import tomllib
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from functools import cache
from importlib.resources import files
from typing import Literal

from pydantic import BaseModel, ConfigDict

from adhd_mcp.evidence.common import completeness, not_after, read_category, usable
from adhd_mcp.fhir.codes import Coding
from adhd_mcp.fhir.reader import PatientRecords, ReadResult
from adhd_mcp.fhir.records import ConditionRecord, EncounterRecord
from adhd_mcp.models.domain import DataCompleteness, ResourceRef
from adhd_mcp.models.evidence_outputs import UtilizationEvent, WindowCount
from adhd_mcp.terminology import ValueSet, load_value_set
from adhd_mcp.terminology.site_codes import SiteCodes

Kind = Literal["acute_care_visit", "injury_visit", "crash_as_driver", "psychiatric_stay"]
_KIND_ORDER: tuple[Kind, ...] = (
    "acute_care_visit",
    "injury_visit",
    "crash_as_driver",
    "psychiatric_stay",
)


class Window(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: Literal["days_0_30", "days_31_180", "days_181_730"]
    from_days: int
    to_days: int


class UtilizationDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    version: str
    encounter_statuses: tuple[str, ...]
    acute_care_classes: tuple[str, ...]
    acute_care_concepts: tuple[str, ...]
    injury_value_sets: tuple[str, ...]
    self_harm_value_sets: tuple[str, ...]
    driver_value_set: str
    psychiatric_concepts: tuple[str, ...]
    windows: tuple[Window, ...]


@cache
def _definition() -> UtilizationDefinition:
    raw = files("adhd_mcp.data").joinpath("utilization.toml").read_text(encoding="utf-8")
    return UtilizationDefinition.model_validate(tomllib.loads(raw))


@dataclass(frozen=True)
class UtilizationContent:
    definition: UtilizationDefinition
    site: SiteCodes
    injury: tuple[ValueSet, ...]
    self_harm: tuple[ValueSet, ...]
    driver: ValueSet


def load_utilization_content(site: SiteCodes) -> UtilizationContent:
    d = _definition()
    return UtilizationContent(
        definition=d,
        site=site,
        injury=tuple(load_value_set(v) for v in d.injury_value_sets),
        self_harm=tuple(load_value_set(v) for v in d.self_harm_value_sets),
        driver=load_value_set(d.driver_value_set),
    )


@dataclass(frozen=True)
class UtilizationResult:
    events: list[UtilizationEvent]
    counts: list[WindowCount]
    visit_days_730: int
    psychiatric_stays_checked: bool
    data_completeness: list[DataCompleteness]
    definition_version: str


def _any(value_sets: Sequence[ValueSet], codes: tuple[Coding, ...]) -> bool:
    return any(vs.matching_codings(codes) for vs in value_sets)


def _sorted(refs: Sequence[ResourceRef]) -> list[ResourceRef]:
    return sorted(set(refs), key=lambda r: (r.resource_type, r.id))


def _condition_day(c: ConditionRecord) -> date | None:
    when = c.onset or c.recorded
    return when.best_date if when else None


def _start(e: EncounterRecord) -> date | None:
    return e.period.start if e.period else None


def _counts(
    measure: str, days: Sequence[date | None], windows: Sequence[Window], as_of: date
) -> WindowCount:
    ages = [(as_of - d).days for d in days if d is not None]
    per = {w.id: sum(1 for a in ages if w.from_days <= a <= w.to_days) for w in windows}
    return WindowCount.model_validate({"measure": measure, **per, "total_730": sum(per.values())})


def _link(
    conditions: Sequence[ConditionRecord], encounters: Sequence[EncounterRecord]
) -> dict[str, list[ConditionRecord]]:
    """Conditions coding each encounter: Condition.encounter and Encounter.diagnosis."""
    by_id = {c.ref.id: c for c in conditions}
    linked: dict[str, list[ConditionRecord]] = defaultdict(list)
    for c in conditions:
        if c.encounter is not None:
            linked[c.encounter.id].append(c)
    for e in encounters:
        for ref in e.diagnoses:
            found = by_id.get(ref.id)
            if found is not None and found not in linked[e.ref.id]:
                linked[e.ref.id].append(found)

    return linked


def _crashes(
    conditions: Sequence[ConditionRecord],
    encounters: Sequence[EncounterRecord],
    driver: ValueSet,
) -> list[tuple[date | None, list[ResourceRef]]]:
    """Crashes as driver: one per encounter, or per day when no encounter is known."""
    encounter_by_id = {e.ref.id: e for e in encounters}
    crashes: dict[tuple[str, str], list[ResourceRef]] = defaultdict(list)
    crash_days: dict[tuple[str, str], date | None] = {}
    for c in conditions:
        if not driver.matching_codings(c.codes):
            continue
        encounter = encounter_by_id.get(c.encounter.id) if c.encounter else None
        if encounter is not None:
            key = ("encounter", encounter.ref.id)
            crash_days[key] = _start(encounter)
            if not crashes[key]:
                crashes[key].append(encounter.ref)
        else:
            day = _condition_day(c)
            key = ("day", day.isoformat() if day else c.ref.id)
            crash_days[key] = day
        crashes[key].append(c.ref)
    for e in encounters:
        key = ("encounter", e.ref.id)
        if driver.matching_codings(e.reason_codes) and key not in crashes:
            crashes[key] = [e.ref]
            crash_days[key] = _start(e)
    out = []
    for key, refs in crashes.items():
        head = refs[:1] if refs[0].resource_type == "Encounter" else []
        out.append((crash_days[key], head + _sorted(refs[len(head) :])))
    return out


async def assemble_utilization(
    records: PatientRecords, patient_id: str, as_of: date, content: UtilizationContent
) -> UtilizationResult:
    d = content.definition
    raw_encounters, raw_conditions = await asyncio.gather(
        read_category(records.encounters(patient_id)),
        read_category(records.conditions(patient_id)),
    )
    notes = [completeness("Encounter", raw_encounters), completeness("Condition", raw_conditions)]
    encounter_read: ReadResult[EncounterRecord] | None = usable(raw_encounters)
    condition_read: ReadResult[ConditionRecord] | None = usable(raw_conditions)
    encounters = [
        e
        for e in (encounter_read.records if encounter_read else ())
        if (e.status or "unknown") in d.encounter_statuses and not_after(e.period, as_of)
    ]
    conditions = [
        c
        for c in (condition_read.records if condition_read else ())
        if not_after(c.onset or c.recorded, as_of)
    ]
    linked = _link(conditions, encounters)
    site = content.site
    events: list[UtilizationEvent] = []

    def add(kind: Kind, day: date | None, refs: list[ResourceRef], end: date | None = None) -> None:
        events.append(UtilizationEvent(kind=kind, date=day, end=end, references=refs))

    for e in encounters:
        coded = linked[e.ref.id]
        codes = e.reason_codes + tuple(code for c in coded for code in c.codes)
        acute = (
            e.encounter_class is not None and e.encounter_class.code in d.acute_care_classes
        ) or any(site.matches(c, e.types + e.service_type) for c in d.acute_care_concepts)
        if acute:
            add("acute_care_visit", _start(e), [e.ref])
            if _any(content.injury, codes) and not _any(content.self_harm, codes):
                injury_refs = [c.ref for c in coded if _any(content.injury, c.codes)]
                add("injury_visit", _start(e), [e.ref, *_sorted(injury_refs)])
        if any(site.matches(c, e.types + e.service_type) for c in d.psychiatric_concepts):
            add("psychiatric_stay", _start(e), [e.ref], e.period.end if e.period else None)

    for day, refs in _crashes(conditions, encounters, content.driver):
        add("crash_as_driver", day, refs)

    events.sort(
        key=lambda ev: (
            ev.date is None,
            ev.date or date.min,
            _KIND_ORDER.index(ev.kind),
            ev.references[0].id,
        )
    )
    counts = [
        _counts(kind, [ev.date for ev in events if ev.kind == kind], d.windows, as_of)
        for kind in _KIND_ORDER
    ]
    all_days = [_start(e) for e in encounters]
    counts.append(_counts("any_encounter", all_days, d.windows, as_of))
    recent_days = {x for x in all_days if x is not None and 0 <= (as_of - x).days <= 730}
    return UtilizationResult(
        events=events,
        counts=counts,
        visit_days_730=len(recent_days),
        psychiatric_stays_checked=any(site.maps(c) for c in d.psychiatric_concepts),
        data_completeness=notes,
        definition_version=d.version,
    )
