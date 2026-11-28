"""Medication timeline: exposure periods by drug class, fills and distinct agents.

Supply periods come from dispenses (handed-over date plus days supply), statements (their
effective period; an active statement with no end runs to the as-of date) and, only when the
record holds no dispensing data, from requests. Periods of one ingredient merge when the gap
between them is within the allowance. All periods end on or before the as-of date.
"""

import asyncio
import tomllib
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from functools import cache
from importlib.resources import files
from typing import Literal

from pydantic import BaseModel, ConfigDict

from adhd_mcp.evidence.common import completeness, not_after, read_category, usable
from adhd_mcp.fhir.reader import PatientRecords, ReadResult
from adhd_mcp.fhir.records import MedicationRecord
from adhd_mcp.models.domain import DataCompleteness, ResourceRef
from adhd_mcp.models.evidence_outputs import (
    AgentSummary,
    DistinctAgents,
    ExposurePeriod,
    IngredientRef,
    PrescriptionEntry,
)
from adhd_mcp.terminology import ValueSet, load_value_set
from adhd_mcp.terminology.drug_classes import DrugClass, DrugIngredient, load_drug_class

Source = Literal["dispense", "statement", "request"]
FillStatus = Literal["filled", "not_filled", "unknown"]
_CATEGORIES = ("MedicationRequest", "MedicationDispense", "MedicationStatement")


class MedicationDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    version: str
    classes: tuple[str, ...]
    assumed_days_supply: int
    allowed_gap_days: int
    fill_window_days: int
    request_statuses: tuple[str, ...]
    request_intents: tuple[str, ...]
    dispense_statuses: tuple[str, ...]
    statement_statuses: tuple[str, ...]
    narcolepsy_value_set: str


@cache
def _definition() -> MedicationDefinition:
    raw = files("adhd_mcp.data").joinpath("medication_timeline.toml").read_text("utf-8")
    return MedicationDefinition.model_validate(tomllib.loads(raw))


@dataclass(frozen=True)
class MedicationContent:
    definition: MedicationDefinition
    classes: tuple[DrugClass, ...]
    narcolepsy: ValueSet


@cache
def load_medication_content() -> MedicationContent:
    d = _definition()
    return MedicationContent(
        definition=d,
        classes=tuple(load_drug_class(c) for c in d.classes),
        narcolepsy=load_value_set(d.narcolepsy_value_set),
    )


@dataclass(frozen=True)
class MedicationTimelineResult:
    exposures: list[ExposurePeriod]
    prescriptions: list[PrescriptionEntry]
    distinct_agents: list[DistinctAgents]
    unclassified_records: int
    classes_checked: list[str]
    data_completeness: list[DataCompleteness]
    definition_version: str
    drug_class_versions: list[str]


@dataclass(frozen=True)
class _Supply:
    start: date
    end: date
    source: Source
    assumed: bool
    narcolepsy: bool
    ref: ResourceRef


def _records(result: ReadResult[MedicationRecord] | None) -> list[MedicationRecord]:
    return list(result.records) if result is not None else []


def _ingredient(i: DrugIngredient) -> IngredientRef:
    return IngredientRef(rxcui=i.rxcui, name=i.name)


def _refs(refs: list[ResourceRef]) -> list[ResourceRef]:
    return sorted(set(refs), key=lambda r: (r.resource_type, r.id))


def _start(m: MedicationRecord) -> date:
    """The record's start date. Undated records are filtered out before this is used."""
    return (m.date.best_date if m.date else None) or date.min


def _supply_end(start: date, days: float | None, d: MedicationDefinition) -> tuple[date, bool]:
    if days is None or days < 1:
        return start + timedelta(days=d.assumed_days_supply - 1), True
    return start + timedelta(days=int(days) - 1), False


def _merge(supplies: list[_Supply], gap: int) -> list[list[_Supply]]:
    groups: list[list[_Supply]] = []
    end = date.min
    for s in sorted(supplies, key=lambda s: (s.start, s.end, s.ref.id)):
        if groups and (s.start - end).days - 1 <= gap:
            groups[-1].append(s)
            end = max(end, s.end)
        else:
            groups.append([s])
            end = s.end
    return groups


class _Assembler:
    def __init__(self, content: MedicationContent, as_of: date) -> None:
        self.content = content
        self.d = content.definition
        self.as_of = as_of

    def _dated(self, records: list[MedicationRecord]) -> list[MedicationRecord]:
        return [m for m in records if _start(m) != date.min and not_after(m.date, self.as_of)]

    def _is_prescription(self, m: MedicationRecord) -> bool:
        return (m.status or "unknown") in self.d.request_statuses and (
            m.intent in self.d.request_intents
        )

    def _narcolepsy(self, m: MedicationRecord) -> bool:
        return bool(self.content.narcolepsy.matching_codings(m.reason_codes))

    def fill_statuses(
        self,
        requests: list[MedicationRecord],
        dispenses: list[MedicationRecord],
        dispense_status: str,
        drug_class: DrugClass,
    ) -> dict[ResourceRef, FillStatus]:
        linked = {ref.id for m in dispenses for ref in m.prescriptions}
        out: dict[ResourceRef, FillStatus] = {}
        for request in requests:
            authored = _start(request)
            names = {i.rxcui for i in drug_class.ingredients_for(request.medication_codes)}
            nearby = any(
                0 <= (_start(m) - authored).days <= self.d.fill_window_days
                and names & {i.rxcui for i in drug_class.ingredients_for(m.medication_codes)}
                for m in dispenses
                if not m.prescriptions
            )
            if request.ref.id in linked or nearby:
                out[request.ref] = "filled"
            elif dispense_status == "available" and dispenses:
                # Not filled only when the record holds complete dispensing data.
                out[request.ref] = "not_filled"
            else:
                out[request.ref] = "unknown"
        return out

    def supplies(
        self,
        m: MedicationRecord,
        source: Source,
        request_narcolepsy: dict[str, bool],
    ) -> _Supply:
        start = _start(m)
        narcolepsy = self._narcolepsy(m) or any(
            request_narcolepsy.get(r.id, False) for r in m.prescriptions
        )
        if source == "statement":
            end = m.date.end if m.date else None
            if end is None:
                end = self.as_of if m.status == "active" else start
            assumed = False
        else:
            end, assumed = _supply_end(start, m.days_supply, self.d)
        end = min(end, self.as_of)
        return _Supply(start, end, source, assumed, narcolepsy, m.ref)


async def assemble_medication_timeline(
    records: PatientRecords, patient_id: str, as_of: date, content: MedicationContent
) -> MedicationTimelineResult:
    raw = await asyncio.gather(
        read_category(records.medication_requests(patient_id)),
        read_category(records.medication_dispenses(patient_id)),
        read_category(records.medication_statements(patient_id)),
    )
    notes = [completeness(n, r) for n, r in zip(_CATEGORIES, raw, strict=True)]
    reads = [usable(r) for r in raw]
    a = _Assembler(content, as_of)
    d = content.definition
    requests_all = a._dated(_records(reads[0]))
    dispenses_all = [
        m for m in a._dated(_records(reads[1])) if (m.status or "unknown") in d.dispense_statuses
    ]
    statements_all = [
        m for m in a._dated(_records(reads[2])) if (m.status or "unknown") in d.statement_statuses
    ]
    prescriptions_all = [m for m in requests_all if a._is_prescription(m)]
    request_narcolepsy = {m.ref.id: a._narcolepsy(m) for m in requests_all}
    dispense_status = notes[1].status
    # Requests count as exposure only when the record holds no dispensing data at all.
    use_requests = not dispenses_all

    exposures: list[ExposurePeriod] = []
    prescriptions: list[PrescriptionEntry] = []
    distinct: list[DistinctAgents] = []
    classified: set[ResourceRef] = set()
    for drug_class in content.classes:

        def in_class(
            ms: list[MedicationRecord], dc: DrugClass = drug_class
        ) -> list[MedicationRecord]:
            return [m for m in ms if dc.ingredients_for(m.medication_codes)]

        requests = in_class(prescriptions_all)
        dispenses = in_class(dispenses_all)
        statements = in_class(statements_all)
        classified.update(m.ref for m in (*in_class(requests_all), *dispenses, *statements))
        fills = a.fill_statuses(requests, dispenses_all, dispense_status, drug_class)

        by_ingredient: dict[str, list[_Supply]] = defaultdict(list)
        sources: list[tuple[MedicationRecord, Source]] = [
            *((m, "dispense") for m in dispenses),
            *((m, "statement") for m in statements),
        ]
        if use_requests:
            sources += [(m, "request") for m in requests if fills[m.ref] == "unknown"]
        for m, source in sources:
            supply = a.supplies(m, source, request_narcolepsy)
            for ingredient in drug_class.ingredients_for(m.medication_codes):
                by_ingredient[ingredient.rxcui].append(supply)

        agents: list[AgentSummary] = []
        for ingredient in drug_class.ingredients:
            supplies = by_ingredient.get(ingredient.rxcui, [])
            for group in _merge(supplies, d.allowed_gap_days):
                exposures.append(
                    ExposurePeriod(
                        drug_class=drug_class.id,
                        ingredient=_ingredient(ingredient),
                        start=min(s.start for s in group),
                        end=max(s.end for s in group),
                        sources=sorted({s.source for s in group}),
                        days_supply_assumed=any(s.assumed for s in group),
                        for_narcolepsy=any(s.narcolepsy for s in group),
                        references=_refs([s.ref for s in group]),
                    )
                )
            ingredient_requests = [
                m for m in requests if ingredient in drug_class.ingredients_for(m.medication_codes)
            ]
            for m in ingredient_requests:
                prescriptions.append(
                    PrescriptionEntry(
                        drug_class=drug_class.id,
                        ingredient=_ingredient(ingredient),
                        date=_start(m),
                        fill_status=fills[m.ref],
                        references=[m.ref],
                    )
                )
            # Distinct agents are agents with exposure (peer review 01, C5): orders count only
            # when the record holds no dispensing data at all, and then as supplies above.
            dates = [(s.start, s.end) for s in supplies]
            if dates:
                refs = [s.ref for s in supplies]
                agents.append(
                    AgentSummary(
                        ingredient=_ingredient(ingredient),
                        first_date=min(s for s, _ in dates),
                        last_date=max(e for _, e in dates),
                        references=_refs(refs),
                    )
                )
        distinct.append(
            DistinctAgents(
                drug_class=drug_class.id, title=drug_class.title, count=len(agents), agents=agents
            )
        )

    every = [m for r in reads for m in _records(r) if not_after(m.date, as_of)]
    unclassified = sum(1 for m in every if m.ref not in classified)
    prescriptions.sort(
        key=lambda p: (p.drug_class, p.ingredient.name, p.date or date.min, p.references[0].id)
    )
    return MedicationTimelineResult(
        exposures=exposures,
        prescriptions=prescriptions,
        distinct_agents=distinct,
        unclassified_records=unclassified,
        classes_checked=[c.id for c in content.classes],
        data_completeness=notes,
        definition_version=d.version,
        drug_class_versions=[f"{c.id} {c.version}" for c in content.classes],
    )
