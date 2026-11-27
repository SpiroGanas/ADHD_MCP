"""Autism: an EXPERIMENTAL stub condition (Phase 8, item 5) that proves the plugin interface.

Its catalog holds placeholder signals and its ruleset has status ``experimental``; neither is
clinical content. The condition is registered only when ``ADHD_MCP_EXPERIMENTAL_CONDITIONS``
names it. The one piece of real logic is the exclusion: a recorded autism code (verified
value set ``care.autism_diagnosis``) means the patient is already in care.
"""

import tomllib
from datetime import date
from functools import cache
from importlib.resources import files

from pydantic import BaseModel, ConfigDict

from adhd_mcp.conditions.base import ConditionPlugin, ExclusionResult
from adhd_mcp.evidence.common import (
    completeness,
    not_offered_reason,
    read_category,
    usable,
)
from adhd_mcp.evidence.problem_list import conditions_as_of
from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.models.domain import CheckOutcome, DataStatus, ExclusionCheck
from adhd_mcp.rules.catalog import load_catalog
from adhd_mcp.rules.ruleset import load_ruleset
from adhd_mcp.rules.scorer import RulesOnlyScorer
from adhd_mcp.terminology import load_value_set
from adhd_mcp.terminology.site_codes import SiteCodes

DATA = "adhd_mcp.data.autism"
_CHECK = "autism_diagnosis_code"


class StubWording(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str
    title: str
    next_step: str
    recommendations: dict[str, str]


@cache
def load_stub_wording() -> StubWording:
    raw = files(DATA).joinpath("wording.toml").read_text(encoding="utf-8")
    return StubWording.model_validate(tomllib.loads(raw))


async def autism_exclusions(
    records: PatientRecords, patient_id: str, as_of: date, site: SiteCodes
) -> ExclusionResult:
    raw = await read_category(records.conditions(patient_id))
    note = completeness("Condition", raw)
    read = usable(raw)
    value_set = load_value_set("care.autism_diagnosis", strict=True)
    codes = ", ".join(sorted(e.code for e in value_set.entries))
    description = f"Autism code ({codes}) on a Condition"
    if read is None:
        failed = note.status is DataStatus.FAILED
        check = ExclusionCheck(
            check=_CHECK,
            description=description,
            outcome=CheckOutcome.FAILED if failed else CheckOutcome.NOT_PERFORMED,
            reason="Could not read Condition" if failed else not_offered_reason(["Condition"]),
        )
        return ExclusionResult(excluded=None, checks=[check], data_completeness=[note])
    found = sorted(
        (
            c.ref
            for c in conditions_as_of(read.records, as_of)
            if value_set.matching_codings(c.codes)
        ),
        key=lambda r: r.id,
    )
    if found:
        check = ExclusionCheck(
            check=_CHECK, description=description, outcome=CheckOutcome.FOUND, references=found
        )
        excluded: bool | None = True
    else:
        check = ExclusionCheck(
            check=_CHECK, description=description, outcome=CheckOutcome.NOT_FOUND
        )
        # "Not in care" only on complete data; a partial read leaves it unknown.
        excluded = False if note.status in {DataStatus.AVAILABLE, DataStatus.EMPTY} else None
    return ExclusionResult(excluded=excluded, checks=[check], data_completeness=[note])


@cache
def autism_plugin() -> ConditionPlugin:
    wording = load_stub_wording()
    return ConditionPlugin(
        id="autism",
        title=wording.title,
        catalog=load_catalog(DATA),
        ruleset=load_ruleset(DATA),
        recommendation_texts=wording.recommendations,
        next_step=wording.next_step,
        exclusions=autism_exclusions,
        scorer=RulesOnlyScorer(),
    )
