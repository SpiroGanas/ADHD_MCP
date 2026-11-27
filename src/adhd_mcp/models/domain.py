"""Shared domain vocabulary used by every later phase.

Fields only. The few validators here protect output invariants that must hold for any
producer: every evidence item cites a FHIR resource (standing invariant 3), a recommendation
always carries a safety gate result (invariant 2) and is never a diagnosis (invariant 1).
"""

import datetime as dt
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

#: FHIR R4 resource types this server reads. There is no write path.
ResourceType = Literal[
    "Patient",
    "Condition",
    "Observation",
    "QuestionnaireResponse",
    "MedicationRequest",
    "MedicationDispense",
    "MedicationStatement",
    "Medication",
    "Encounter",
    "Procedure",
    "ServiceRequest",
    "CarePlan",
    "Flag",
]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ResourceRef(_Frozen):
    """A pointer to the FHIR resource a fact came from."""

    resource_type: ResourceType
    id: str = Field(min_length=1)
    version: str | None = Field(default=None, description="meta.versionId when the server has one")


class WeightClass(StrEnum):
    HIGH = "high"
    MODIFIER = "modifier"


class EvidenceItem(_Frozen):
    """One named signal and the FHIR resources it was found in."""

    signal: str = Field(min_length=1, description="Signal name from the signal catalog")
    weight_class: WeightClass | None = Field(
        default=None, description="Rule weight; null for safety-gate and context items"
    )
    references: list[ResourceRef] = Field(min_length=1)
    date: dt.date | None = Field(default=None, description="Clinically relevant date, if known")


class SafetyGateStatus(StrEnum):
    POSITIVE = "positive"
    CLEAR = "clear"
    CLEAR_LIMITED_DATA = "clear_limited_data"
    DATA_UNAVAILABLE = "data_unavailable"


class SafetyGateResult(_Frozen):
    status: SafetyGateStatus
    checks_performed: list[str] = Field(min_length=1)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    guidance: str | None = Field(default=None, description="Fixed guidance text when positive")

    @model_validator(mode="after")
    def _positive_needs_evidence(self) -> Self:
        if self.status is SafetyGateStatus.POSITIVE and not self.evidence:
            raise ValueError("a positive safety gate must cite evidence")
        return self


class RecommendationCode(StrEnum):
    CONSIDER_REFERRAL = "consider_referral_for_formal_screening"
    NO_RECOMMENDATION = "no_recommendation"
    ADDRESS_SAFETY_GATE_FIRST = "address_safety_gate_first"
    ALREADY_IN_CARE = "already_in_care"
    INSUFFICIENT_DATA = "insufficient_data"


class ExclusionCheck(_Frozen):
    check: str = Field(min_length=1, description="What was looked for")
    found: bool
    references: list[ResourceRef] = Field(default_factory=list)

    @model_validator(mode="after")
    def _found_needs_references(self) -> Self:
        if self.found and not self.references:
            raise ValueError("a found exclusion must cite references")
        return self


class DataStatus(StrEnum):
    AVAILABLE = "available"
    EMPTY = "empty"
    WITHHELD = "withheld"
    FAILED = "failed"


class DataCompleteness(_Frozen):
    category: str = Field(min_length=1)
    status: DataStatus


class RuleTraceEntry(_Frozen):
    rule_id: str
    fired: bool
    reason: str


class Versions(_Frozen):
    server: str
    tool_contract: str
    ruleset: str | None = None
    scorer: str | None = None


class Recommendation(_Frozen):
    """Result of an assessment. The schema is fixed by contract tests in Phase 5.

    The safety gate is the first field, so it is presented first. Validators keep the
    recommendation consistent with the gate: a positive gate allows only
    "address safety gate first"; an unavailable gate never yields a clean or referral result;
    a referral suggestion must cite evidence.
    """

    safety_gate: SafetyGateResult
    recommendation: RecommendationCode
    is_diagnosis: Literal[False] = False
    condition_to_screen: str
    suggested_next_step: str | None = None
    basis: list[EvidenceItem] = Field(default_factory=list)
    exclusions_checked: list[ExclusionCheck] = Field(default_factory=list)
    decision_trace: list[RuleTraceEntry] = Field(default_factory=list)
    data_completeness: list[DataCompleteness] = Field(default_factory=list)
    versions: Versions

    @model_validator(mode="after")
    def _consistent_with_gate(self) -> Self:
        gate = self.safety_gate.status
        code = self.recommendation
        if (gate is SafetyGateStatus.POSITIVE) != (
            code is RecommendationCode.ADDRESS_SAFETY_GATE_FIRST
        ):
            raise ValueError(
                "a positive safety gate requires, and only it allows, address_safety_gate_first"
            )
        if gate is SafetyGateStatus.DATA_UNAVAILABLE and code in {
            RecommendationCode.CONSIDER_REFERRAL,
            RecommendationCode.NO_RECOMMENDATION,
        }:
            raise ValueError("an unavailable safety gate cannot yield a clean or referral result")
        if code is RecommendationCode.CONSIDER_REFERRAL and not self.basis:
            raise ValueError("a referral suggestion must cite evidence in its basis")
        return self
