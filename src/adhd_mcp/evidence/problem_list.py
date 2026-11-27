"""The mental health problem list: coded conditions grouped into the families the rules use.

One entry per code: duplicate codings across encounters collapse into one entry citing every
Condition. Each entry has its first onset and recorded dates, the clinical status of its
latest record, and an onset order (entries with the same first date share a rank).
"""

import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from functools import cache
from importlib.resources import files

from pydantic import BaseModel, ConfigDict

from adhd_mcp.evidence.common import completeness, read_category
from adhd_mcp.fhir.codes import Coding
from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.fhir.records import ConditionRecord
from adhd_mcp.models.domain import DataCompleteness
from adhd_mcp.models.evidence_outputs import CodeRef, ProblemEntry, ProblemFamily
from adhd_mcp.terminology import ValueSet, load_value_set

_RESOLVED = frozenset({"resolved", "inactive"})


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


def _recency(c: ConditionRecord) -> date:
    """Sort key for "latest record": its recorded date, else its first known date."""
    if c.recorded is not None and c.recorded.start is not None:
        return c.recorded.start
    return _first_date(c) or date.min


def _entry(coding: Coding, conditions: list[ConditionRecord]) -> ProblemEntry:
    recorded = [c.recorded.start if c.recorded else None for c in conditions]
    status = max(conditions, key=_recency).clinical_status
    return ProblemEntry(
        code=CodeRef(system=coding.system, code=coding.code, display=coding.display),
        onset=_min([c.onset.start if c.onset else None for c in conditions]),
        first_recorded=_min(recorded),
        last_recorded=_max(recorded),
        clinical_status=status,
        resolved=status in _RESOLVED,
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


async def assemble_problem_list(
    records: PatientRecords, patient_id: str, as_of: date, content: ProblemListContent
) -> ProblemListResult:
    read = await read_category(records.conditions(patient_id))
    notes = [completeness("Condition", read)]
    # A condition first known after the as-of date did not exist yet.
    conditions = [
        c for c in (read.records if read else ()) if (d := _first_date(c)) is None or d <= as_of
    ]

    # code -> (coding, conditions); a family keeps the codes it matches
    by_code: dict[tuple[str | None, str], tuple[Coding, list[ConditionRecord]]] = {}
    family_codes: dict[str, list[tuple[str | None, str]]] = {}
    for c in conditions:
        for coding in c.codes:
            matched = [vs.id for vs in content.families if vs.matches(coding)]
            if not matched and content.fallback.matches(coding):
                matched = [content.fallback.id]
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
    families = []
    for vs in (*content.families, content.fallback):
        keys = family_codes.get(vs.id)
        if not keys:
            continue
        entries = _with_order([_entry(*by_code[k]) for k in keys], firsts)
        entries.sort(key=lambda e: (e.onset_order is None, e.onset_order or 0, e.code.code))
        families.append(ProblemFamily(family=vs.id, title=vs.title, entries=entries))
    return ProblemListResult(
        families=families,
        families_checked=[vs.id for vs in (*content.families, content.fallback)],
        data_completeness=notes,
        definition_version=content.definition.version,
    )
