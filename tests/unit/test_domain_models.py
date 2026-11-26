from datetime import date

import pytest
from pydantic import ValidationError

from adhd_mcp.models.domain import (
    DataCompleteness,
    DataStatus,
    EvidenceItem,
    ExclusionCheck,
    Recommendation,
    RecommendationCode,
    ResourceRef,
    SafetyGateResult,
    SafetyGateStatus,
    Versions,
    WeightClass,
)

REF = ResourceRef(resource_type="Condition", id="syn-c1", version="1")


def evidence(**overrides: object) -> EvidenceItem:
    fields: dict[str, object] = {
        "signal": "stimulant_related_disorder",
        "weight_class": WeightClass.HIGH,
        "references": [REF],
        "date": date(2025, 3, 2),
    }
    fields.update(overrides)
    return EvidenceItem.model_validate(fields)


def clear_gate() -> SafetyGateResult:
    return SafetyGateResult(status=SafetyGateStatus.CLEAR, checks_performed=["self-harm codes"])


def test_evidence_item_with_a_reference_is_valid() -> None:
    item = evidence()
    assert item.references == [REF]


def test_evidence_item_rejects_missing_references() -> None:
    with pytest.raises(ValidationError, match="references"):
        evidence(references=[])


def test_resource_ref_rejects_empty_id() -> None:
    with pytest.raises(ValidationError):
        ResourceRef(resource_type="Condition", id="")


def test_resource_ref_rejects_unknown_resource_type() -> None:
    with pytest.raises(ValidationError):
        ResourceRef(resource_type="NotAResource", id="x")


def test_models_are_immutable() -> None:
    item = evidence()
    with pytest.raises(ValidationError):
        item.signal = "other"  # type: ignore[misc]


def test_positive_safety_gate_requires_evidence() -> None:
    with pytest.raises(ValidationError, match="evidence"):
        SafetyGateResult(status=SafetyGateStatus.POSITIVE, checks_performed=["self-harm codes"])


def test_positive_safety_gate_with_evidence_is_valid() -> None:
    gate = SafetyGateResult(
        status=SafetyGateStatus.POSITIVE,
        checks_performed=["self-harm codes"],
        evidence=[evidence(signal="suicidal_ideation", weight_class=None)],
    )
    assert gate.status is SafetyGateStatus.POSITIVE


def test_recommendation_requires_a_safety_gate_result() -> None:
    with pytest.raises(ValidationError, match="safety_gate"):
        Recommendation.model_validate(
            {
                "recommendation": RecommendationCode.NO_RECOMMENDATION,
                "condition_to_screen": "adult ADHD",
                "versions": {"server": "0.1.0", "tool_contract": "0.1.0"},
            }
        )


def test_recommendation_is_never_a_diagnosis() -> None:
    rec = Recommendation(
        recommendation=RecommendationCode.CONSIDER_REFERRAL,
        condition_to_screen="adult ADHD",
        safety_gate=clear_gate(),
        basis=[evidence()],
        exclusions_checked=[ExclusionCheck(check="existing ADHD diagnosis", found=False)],
        data_completeness=[DataCompleteness(category="Condition", status=DataStatus.AVAILABLE)],
        versions=Versions(server="0.1.0", tool_contract="0.1.0", ruleset="1.0.0"),
    )
    assert rec.is_diagnosis is False
    with pytest.raises(ValidationError):
        Recommendation.model_validate({**rec.model_dump(), "is_diagnosis": True})


def test_recommendation_vocabulary_is_fixed() -> None:
    assert {c.value for c in RecommendationCode} == {
        "consider_referral_for_formal_screening",
        "no_recommendation",
        "address_safety_gate_first",
        "already_in_care",
        "insufficient_data",
    }


def test_exclusion_found_requires_references() -> None:
    with pytest.raises(ValidationError, match="references"):
        ExclusionCheck(check="existing ADHD diagnosis", found=True)
