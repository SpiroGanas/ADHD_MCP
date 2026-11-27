"""Psychosocial context: housing, legal, education and employment problems from Condition
codes and coded social-history Observation values, and military separation where recorded."""

import asyncio
import tomllib
from dataclasses import dataclass
from datetime import date
from functools import cache
from importlib.resources import files
from typing import Any

from pydantic import BaseModel, ConfigDict

from adhd_mcp.evidence.common import completeness, not_after, read_category
from adhd_mcp.evidence.problem_list import conditions_as_of, group_conditions
from adhd_mcp.fhir.reader import PatientRecords, ReadResult
from adhd_mcp.fhir.records import ConditionRecord, ObservationRecord
from adhd_mcp.models.domain import DataCompleteness
from adhd_mcp.models.evidence_outputs import MilitaryContext, PsychosocialDomain
from adhd_mcp.terminology import ValueSet, load_value_set
from adhd_mcp.terminology.site_codes import SiteCodes

_COMPLETE = frozenset({"available", "empty"})


class DomainDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    title: str
    value_sets: tuple[str, ...]


class PsychosocialDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    version: str
    domains: tuple[DomainDefinition, ...]
    military_separation_concept: str


@cache
def _definition() -> PsychosocialDefinition:
    raw = files("adhd_mcp.data").joinpath("psychosocial.toml").read_text(encoding="utf-8")
    return PsychosocialDefinition.model_validate(tomllib.loads(raw))


@dataclass(frozen=True)
class PsychosocialContent:
    definition: PsychosocialDefinition
    site: SiteCodes
    domains: tuple[tuple[DomainDefinition, tuple[ValueSet, ...]], ...]


def load_psychosocial_content(site: SiteCodes) -> PsychosocialContent:
    d = _definition()
    return PsychosocialContent(
        definition=d,
        site=site,
        domains=tuple((dom, tuple(load_value_set(v) for v in dom.value_sets)) for dom in d.domains),
    )


@dataclass(frozen=True)
class PsychosocialResult:
    domains: list[PsychosocialDomain]
    military: MilitaryContext
    data_completeness: list[DataCompleteness]
    definition_version: str


def _military(
    observations: list[ObservationRecord], content: PsychosocialContent, readable: bool
) -> MilitaryContext:
    concept = content.definition.military_separation_concept
    if not content.site.maps(concept):
        return MilitaryContext(
            separation_date=None, status="unknown", reason="not mapped at this site", references=[]
        )
    found = [o for o in observations if content.site.matches(concept, o.codes)]
    dated = [
        (o.value.date.start, o)
        for o in found
        if o.value is not None and o.value.date is not None and o.value.date.start is not None
    ]
    if dated:
        # The latest recorded separation (a person may serve and separate more than once).
        day, obs = max(dated, key=lambda x: (x[0], x[1].ref.id))
        return MilitaryContext(separation_date=day, status="recorded", references=[obs.ref])
    reason = "not recorded" if readable else "observations could not be read completely"
    return MilitaryContext(
        separation_date=None,
        status="unknown",
        reason=reason,
        references=sorted((o.ref for o in found), key=lambda r: r.id),
    )


async def assemble_psychosocial(
    records: PatientRecords, patient_id: str, as_of: date, content: PsychosocialContent
) -> PsychosocialResult:
    reads: tuple[Any, ...] = await asyncio.gather(
        read_category(records.conditions(patient_id)),
        read_category(records.observations(patient_id)),
    )
    condition_read: ReadResult[ConditionRecord] | None = reads[0]
    observation_read: ReadResult[ObservationRecord] | None = reads[1]
    notes = [
        completeness("Condition", condition_read),
        completeness("Observation", observation_read),
    ]
    complete = all(n.status in _COMPLETE for n in notes)
    conditions = conditions_as_of(condition_read.records if condition_read else (), as_of)
    observations = [
        o
        for o in (observation_read.records if observation_read else ())
        if not_after(o.effective, as_of)
    ]
    domains = []
    for definition, value_sets in content.domains:
        families = group_conditions(conditions, value_sets)
        obs_refs = sorted(
            {
                o.ref
                for o in observations
                if o.value is not None
                and any(vs.matching_codings(o.value.codings) for vs in value_sets)
            },
            key=lambda r: r.id,
        )
        if families or obs_refs:
            status = "found"
        elif complete:
            status = "not_found"
        else:
            status = "unknown"
        domains.append(
            PsychosocialDomain(
                domain=definition.id,
                title=definition.title,
                status=status,
                families=families,
                observation_references=obs_refs,
            )
        )
    return PsychosocialResult(
        domains=domains,
        military=_military(observations, content, notes[1].status in _COMPLETE),
        data_completeness=notes,
        definition_version=content.definition.version,
    )
