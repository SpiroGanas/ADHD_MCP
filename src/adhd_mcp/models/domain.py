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


class CheckOutcome(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    NOT_PERFORMED = "not_performed"
    FAILED = "failed"


class SafetyCheck(_Frozen):
    """One safety-gate check and what came of it."""

    id: str = Field(min_length=1)
    description: str
    outcome: CheckOutcome
    reason: str | None = Field(
        default=None, description="Why the check was not performed or failed"
    )

    @model_validator(mode="after")
    def _reason_when_not_run(self) -> Self:
        if self.outcome in {CheckOutcome.NOT_PERFORMED, CheckOutcome.FAILED} and not self.reason:
            raise ValueError("a check not performed or failed must give a reason")
        return self


class ExclusionCheck(_Frozen):
    check: str = Field(min_length=1, description="What was looked for")
    description: str | None = None
    outcome: CheckOutcome
    reason: str | None = Field(default=None, description="Why not performed or failed")
    references: list[ResourceRef] = Field(default_factory=list)

    @property
    def found(self) -> bool:
        return self.outcome is CheckOutcome.FOUND

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.found and not self.references:
            raise ValueError("a found exclusion must cite references")
        if self.outcome in {CheckOutcome.NOT_PERFORMED, CheckOutcome.FAILED} and not self.reason:
            raise ValueError("a check not performed or failed must give a reason")
        return self


class SafetyGateResult(_Frozen):
    """The gate's status agrees with its checks (owner decision 2026-11-27):

    * positive if and only if a check found a signal;
    * otherwise data_unavailable if a check failed;
    * otherwise clear only if every check ran; clear_limited_data is used when a check
      was not performed or the record holds too little data.
    """

    status: SafetyGateStatus
    checks: list[SafetyCheck] = Field(min_length=1)
    evidence: list[EvidenceItem] = Field(
        default_factory=list, description="Signals that make the gate positive"
    )
    history: list[EvidenceItem] = Field(
        default_factory=list,
        description="Older self-harm signals, outside the look-back window; listed for the "
        "clinician, they do not make the gate positive",
    )
    guidance: str | None = Field(default=None, description="Fixed guidance text when positive")

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        ids = [c.id for c in self.checks]
        if len(ids) != len(set(ids)):
            raise ValueError("check ids must be unique")
        outcomes = {c.outcome for c in self.checks}
        positive = self.status is SafetyGateStatus.POSITIVE
        if positive != (CheckOutcome.FOUND in outcomes):
            raise ValueError("the gate is positive if and only if a check found a signal")
        if positive and not self.evidence:
            raise ValueError("a positive safety gate must cite evidence")
        if positive != (self.guidance is not None):
            raise ValueError("guidance is given exactly when the gate is positive")
        if not positive:
            failed = CheckOutcome.FAILED in outcomes
            if failed != (self.status is SafetyGateStatus.DATA_UNAVAILABLE):
                raise ValueError("data_unavailable is used exactly when a check failed")
            if self.status is SafetyGateStatus.CLEAR and outcomes != {CheckOutcome.NOT_FOUND}:
                raise ValueError("clear requires every check to have run")
        return self


class RecommendationCode(StrEnum):
    CONSIDER_REFERRAL = "consider_referral_for_formal_screening"
    NO_RECOMMENDATION = "no_recommendation"
    ADDRESS_SAFETY_GATE_FIRST = "address_safety_gate_first"
    ALREADY_IN_CARE = "already_in_care"
    INSUFFICIENT_DATA = "insufficient_data"


class DataStatus(StrEnum):
    AVAILABLE = "available"
    EMPTY = "empty"
    INCOMPLETE = "incomplete"
    WITHHELD = "withheld"
    FAILED = "failed"


class DataCompleteness(_Frozen):
    """Whether one data category could be read, so an empty record is never mistaken
    for a clean one."""

    category: str = Field(min_length=1, description="A FHIR resource type")
    status: DataStatus
    records: int = Field(default=0, description="Records read")
    skipped: int = Field(
        default=0, description="Resources not used: entered in error, refuted or malformed"
    )
    warnings: list[str] = Field(
        default_factory=list, description="Server warning codes, e.g. incomplete, suppressed"
    )


class PrivacyCount(_Frozen):
    category: str = Field(description="Protected category, e.g. substance_use")
    records: int = Field(ge=1)


class PrivacyNote(_Frozen):
    """What the sensitive-data policy did. Always present, so a withheld category is never
    silent."""

    policy: str = Field(description="Policy id and version")
    withheld: list[PrivacyCount] = Field(
        default_factory=list,
        description="Records removed before evidence assembly, by category; they were not "
        "used by any rule",
    )
    restricted: list[PrivacyCount] = Field(
        default_factory=list,
        description="Records used, but shown only as references and dates (codes appear as "
        "'restricted'), by category",
    )


class RuleTraceEntry(_Frozen):
    rule_id: str
    fired: bool
    reason: str


class Versions(_Frozen):
    server: str
    tool_contract: str
    ruleset: str | None = None
    scorer: str | None = None
    site_codes: str | None = Field(
        default=None, description="Local code mapping in use: id and version"
    )


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
