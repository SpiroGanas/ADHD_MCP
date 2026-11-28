"""The mental health problem list: coded conditions grouped into the families the rules use.

One entry per code: duplicate codings across encounters collapse into one entry citing every
Condition. Each entry has its first onset and recorded dates, its last date, the clinical
status of its latest record, whether it counts as current, and an onset order (entries with
the same first date share a rank).

An entry is current (open-ended, counted whatever its date) only when its latest record is
an active problem-list item with no abatement on or before the as-of date, and its family is
not a single-day event. Encounter diagnoses, conditions without a status and event codes
count by their last date (peer review 01, C1; owner decision 2026-11-28, a draft for the
clinical reviewer).
"""

import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from functools import cache
from importlib.resources import files

from pydantic import BaseModel, ConfigDict

from adhd_mcp.evidence.common import completeness, read_category, usable
from adhd_mcp.fhir.codes import Coding
from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.fhir.records import ConditionRecord
from adhd_mcp.models.domain import DataCompleteness
from adhd_mcp.models.evidence_outputs import CodeRef, ProblemEntry, ProblemFamily
from adhd_mcp.terminology import ValueSet, load_value_set

_RESOLVED = frozenset({"resolved", "inactive"})
_ACTIVE = frozenset({"active", "recurrence", "relapse"})
_PROBLEM_LIST_ITEM = "problem-list-item"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ProblemListDefinition(_Frozen):
    id: str
    version: str
    families: tuple[str, ...]
    fallback: str


class ProblemListResult(_Frozen):
    families: list[ProblemFamily]
    families_checked: list[str]
    data_completeness: list[DataCompleteness]
    definition_version: str


@cache
def _definition() -> ProblemListDefinition:
    raw = files("adhd_mcp.data").joinpath("problem_list.toml").read_text(encoding="utf-8")
    return ProblemListDefinition.model_validate(tomllib.loads(raw))


@dataclass(frozen=True)
class ProblemListContent:
    definition: ProblemListDefinition
    families: tuple[ValueSet, ...]
    fallback: ValueSet


def load_problem_list_content() -> ProblemListContent:
    """Load every family strictly; an unverified family is a packaging error."""
    d = _definition()
    families = tuple(load_value_set(f) for f in d.families)
    return ProblemListContent(d, families, load_value_set(d.fallback))


def _first_date(c: ConditionRecord) -> date | None:
    starts = [r.start for r in (c.onset, c.recorded) if r is not None and r.start is not None]
    return min(starts) if starts else None


def _min(values: Sequence[date | None]) -> date | None:
    known = [v for v in values if v is not None]
    return min(known) if known else None


def _max(values: Sequence[date | None]) -> date | None:
    known = [v for v in values if v is not None]
    return max(known) if known else None


def _last_date(c: ConditionRecord) -> date | None:
    ends = [r.end or r.start for r in (c.recorded, c.onset, c.abatement) if r is not None]
    known = [d for d in ends if d is not None]
    return max(known) if known else None


def _recency(c: ConditionRecord) -> date:
    """Sort key for "latest record": its recorded date, else its latest known date."""
    if c.recorded is not None and c.recorded.start is not None:
        return c.recorded.start
    return _last_date(c) or date.min


def _current(c: ConditionRecord, as_of: date | None) -> bool:
    """An active problem-list item not abated by the as-of date."""
    abated = c.abatement is not None and (
        as_of is None or c.abatement.start is None or c.abatement.start <= as_of
    )
    return (
        c.clinical_status in _ACTIVE
        and any(k.code == _PROBLEM_LIST_ITEM for k in c.categories)
        and not abated
    )


def _display(coding: Coding, value_sets: tuple[ValueSet, ...]) -> str | None:
    """The value set's own display for an exactly listed code. The record's display is
    free text from the record and is never returned."""
    for vs in value_sets:
        entry = vs.matches(coding)
        if entry is not None and entry.match == "exact" and entry.code == coding.code:
            return entry.display
    return None


def _entry(
    coding: Coding,
    conditions: list[ConditionRecord],
    value_sets: tuple[ValueSet, ...],
    *,
    point_in_time: bool,
    as_of: date | None,
) -> ProblemEntry:
    recorded = [c.recorded.start if c.recorded else None for c in conditions]
    latest_record = max(conditions, key=_recency)
    status = latest_record.clinical_status
    return ProblemEntry(
        code=CodeRef(system=coding.system, code=coding.code, display=_display(coding, value_sets)),
        onset=_min([c.onset.start if c.onset else None for c in conditions]),
        first_recorded=_min(recorded),
        last_recorded=_max(recorded),
        last_date=_max([_last_date(c) for c in conditions]),
        clinical_status=status,
        resolved=status in _RESOLVED,
        current=not point_in_time and _current(latest_record, as_of),
        onset_order=None,
        references=sorted({c.ref for c in conditions}, key=lambda r: r.id),
    )


def _rank(ranks: dict[date, int], first: date | None) -> int | None:
    return ranks[first] if first is not None else None


def _with_order(entries: list[ProblemEntry], firsts: dict[str, date | None]) -> list[ProblemEntry]:
    ranks = {d: i + 1 for i, d in enumerate(sorted({d for d in firsts.values() if d}))}
    return [
        e.model_copy(update={"onset_order": _rank(ranks, firsts[e.code.code])}) for e in entries
    ]


def conditions_as_of(conditions: Sequence[ConditionRecord], as_of: date) -> list[ConditionRecord]:
    """Conditions first known on or before the as-of date (undated ones are kept)."""
    return [c for c in conditions if (d := _first_date(c)) is None or d <= as_of]


def group_conditions(
    conditions: Sequence[ConditionRecord],
    families: tuple[ValueSet, ...],
    fallback: ValueSet | None = None,
    *,
    as_of: date | None = None,
) -> list[ProblemFamily]:
    """Group conditions into families: one entry per code citing every Condition, families
    in the given order, entries by onset order. The fallback family takes codes it matches
    that no other family matches. ``as_of`` decides whether an abatement has happened yet
    (any abatement counts when it is not given)."""
    every = (*families, fallback) if fallback is not None else families
    # code -> (coding, conditions); a family keeps the codes it matches
    by_code: dict[tuple[str | None, str], tuple[Coding, list[ConditionRecord]]] = {}
    family_codes: dict[str, list[tuple[str | None, str]]] = {}
    for c in conditions:
        for coding in c.codes:
            matched = [vs.id for vs in families if vs.matches(coding)]
            if not matched and fallback is not None and fallback.matches(coding):
                matched = [fallback.id]
            if not matched:
                continue
            key = (coding.system, coding.code)
            by_code.setdefault(key, (coding, []))[1].append(c)
            for family in matched:
                if key not in family_codes.setdefault(family, []):
                    family_codes[family].append(key)

    firsts = {
        code: _min([_first_date(c) for c in found]) for (_, code), (_, found) in by_code.items()
    }
    grouped = []
    for vs in every:
        keys = family_codes.get(vs.id)
        if not keys:
            continue
        entries = _with_order(
            [_entry(*by_code[k], every, point_in_time=vs.point_in_time, as_of=as_of) for k in keys],
            firsts,
        )
        entries.sort(key=lambda e: (e.onset_order is None, e.onset_order or 0, e.code.code))
        grouped.append(ProblemFamily(family=vs.id, title=vs.title, entries=entries))
    return grouped


async def assemble_problem_list(
    records: PatientRecords, patient_id: str, as_of: date, content: ProblemListContent
) -> ProblemListResult:
    raw = await read_category(records.conditions(patient_id))
    notes = [completeness("Condition", raw)]
    read = usable(raw)
    # A condition first known after the as-of date did not exist yet.
    conditions = conditions_as_of(read.records if read else (), as_of)
    return ProblemListResult(
        families=group_conditions(conditions, content.families, content.fallback, as_of=as_of),
        families_checked=[vs.id for vs in (*content.families, content.fallback)],
        data_completeness=notes,
        definition_version=content.definition.version,
    )
