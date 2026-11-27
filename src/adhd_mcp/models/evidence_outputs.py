"""Output schemas of the evidence tools. Fixed by contract snapshots."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from adhd_mcp.models.domain import DataCompleteness, ResourceRef, SafetyGateResult, Versions


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CodeRef(_Frozen):
    system: str | None
    code: str
    display: str | None = None


class ProblemEntry(_Frozen):
    code: CodeRef
    onset: date | None = Field(description="Earliest onset date recorded, if any")
    first_recorded: date | None = Field(description="Earliest recorded date, if any")
    last_recorded: date | None = Field(description="Latest recorded date, if any")
    clinical_status: str | None = Field(description="Clinical status of the latest record")
    resolved: bool = Field(description="True when the latest record is resolved or inactive")
    onset_order: int | None = Field(
        description="Rank by first known date (onset or recorded), 1 = earliest; equal dates "
        "share a rank; null when undated"
    )
    references: list[ResourceRef] = Field(min_length=1)


class ProblemFamily(_Frozen):
    family: str = Field(description="Value set id of the family")
    title: str
    entries: list[ProblemEntry]


class EvidenceOutput(BaseModel):
    """Fields every evidence tool returns."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    patient_id: str
    as_of: date = Field(description="The date the record was read as of")
    is_diagnosis: Literal[False] = Field(
        default=False, description="Always false: these results are never a diagnosis"
    )
    notice: str = Field(description="Standard notice on how to read these results")
    data_completeness: list[DataCompleteness] = Field(
        description="Each data category read: available, empty, incomplete or failed. An "
        "empty record is not a clean record."
    )
    versions: Versions


class SafetyGateOutput(EvidenceOutput):
    safety_gate: SafetyGateResult
    gate_definition_version: str = Field(description="Version of the safety gate definition")


class ProblemListOutput(EvidenceOutput):
    families: list[ProblemFamily] = Field(
        description="Families with at least one coded condition, in a fixed order"
    )
    families_checked: list[str] = Field(description="Every family looked for")
    definition_version: str


class CutoffResult(_Frozen):
    """The cutoff for one score and whether it was applied."""

    id: str
    operator: str
    value: float
    sex: str = Field(description="any, male or female")
    status: Literal["applied", "not_applied_unverified", "not_applied_sex_unknown"]
    met: bool | None = Field(description="Whether the score meets the cutoff; null if not applied")
    note: str | None = Field(default=None, description="Where the cutoff comes from")


class ScreeningEntry(_Frozen):
    instrument: str | None = Field(description="Instrument id; null for an unknown instrument")
    instrument_title: str | None
    measure: Literal["total_score", "item", "risk_level", "unknown"]
    item: str | None = Field(default=None, description="Item number for an item score")
    date: date | None
    score: float | None
    answer: CodeRef | None = Field(default=None, description="A coded answer, e.g. a risk level")
    code: CodeRef | None = Field(description="The instrument code of this measure")
    code_verified: bool = Field(description="Whether that code is verified in the terminology")
    form: Literal["observation", "questionnaire_response"]
    questionnaire: str | None = Field(default=None, description="Questionnaire URL, if any")
    cutoff: CutoffResult | None = Field(description="Null when the measure has no cutoff")
    references: list[ResourceRef] = Field(min_length=1)


class ScreeningHistoryOutput(EvidenceOutput):
    entries: list[ScreeningEntry] = Field(description="Timeline, oldest first; undated last")
    instruments_checked: list[str]
