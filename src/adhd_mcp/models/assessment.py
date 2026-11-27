"""Output schemas of ``assess_referral_need`` and ``draft_referral_proposal``. Fixed by
contract snapshots."""

import datetime as dt
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from adhd_mcp.models.domain import Recommendation, ResourceRef, RuleTraceEntry


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SignalFinding(_Frozen):
    """One catalog signal, present or not, and why."""

    signal: str
    title: str
    weight: Literal["high", "modifier", "note"]
    present: bool
    reason: str = Field(description="Why the signal is or is not present")
    window_days: int = Field(description="Days before the as-of date the signal is looked for")
    count: int | None = Field(default=None, description="Events or agents counted, if counted")
    first_date: dt.date | None = None
    last_date: dt.date | None = None
    references: list[ResourceRef] = Field(
        description="Resources behind the signal within the window; empty when not present"
    )
    protected: str | None = Field(
        default=None, description="Sensitive-data category of the signal, if any"
    )

    @model_validator(mode="after")
    def _evidence_or_silence(self) -> Self:
        if self.present and not self.references:
            raise ValueError("a present signal must cite at least one resource")
        return self


class RuleOutcome(RuleTraceEntry):
    description: str
    high_signals: list[str] = Field(description="High-weight signals counted")
    modifier_signals: list[str] = Field(description="Modifier signals counted")


class ScorerRef(_Frozen):
    id: str
    version: str
    score: float | None = Field(
        description="A statistical score, if the scorer gives one. Reported only; in this "
        "version it never changes the recommendation"
    )


class AssessmentOutput(Recommendation):
    """The answer to: should a referral for formal screening be considered, and on what
    evidence? The safety gate is the first field."""

    patient_id: str
    as_of: dt.date
    notice: str = Field(description="The standard notice: a suggestion, never a diagnosis")
    recommendation_text: str = Field(description="The recommendation in approved wording")
    notes: list[str] = Field(description="Further points for the clinician, e.g. TBI overlap")
    excluded: bool | None = Field(
        description="Already in care for the condition: true, false, or null when unknown"
    )
    signals_checked: list[SignalFinding] = Field(description="Every catalog signal, present or not")
    decision_trace: list[RuleOutcome] = Field(  # type: ignore[assignment]
        description="Each rule, whether it fired, and the signals it counted"
    )
    ruleset: str = Field(description="Ruleset id, version and status; never clinically validated")
    scorer: ScorerRef | None = None

    @model_validator(mode="after")
    def _basis_matches_present_signals(self) -> Self:
        present = {s.signal for s in self.signals_checked if s.present and s.weight != "note"}
        if {b.signal for b in self.basis} != present:
            raise ValueError("the basis lists exactly the present weighted signals")
        return self


class ReferralDraftOutput(_Frozen):
    patient_id: str
    as_of: dt.date
    is_diagnosis: Literal[False] = False
    stored: Literal[False] = Field(
        default=False, description="Always false: the draft is returned only, never stored"
    )
    recommendation: str
    draft: dict[str, Any] | None = Field(
        description="A FHIR R4 ServiceRequest with intent 'proposal' and status 'draft', or "
        "null when the assessment does not suggest a referral"
    )
    why_no_draft: str | None = None
    notice: str
