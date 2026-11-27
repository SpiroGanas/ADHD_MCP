"""Output schemas of the evidence tools. Fixed by contract snapshots."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from adhd_mcp.models.domain import DataCompleteness, SafetyGateResult, Versions


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
