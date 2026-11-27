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


def gate(status: SafetyGateStatus) -> SafetyGateResult:
    evidence_items = [evidence(signal="suicidal_ideation", weight_class=None)]
    return SafetyGateResult(
        status=status,
        checks_performed=["self-harm codes"],
        evidence=evidence_items if status is SafetyGateStatus.POSITIVE else [],
    )


def recommendation(
    code: RecommendationCode, gate_status: SafetyGateStatus, **extra: object
) -> Recommendation:
    fields: dict[str, object] = {
        "recommendation": code,
        "condition_to_screen": "adult ADHD",
        "safety_gate": gate(gate_status),
        "basis": [evidence()],
        "versions": {"server": "0.1.0", "tool_contract": "0.1.0"},
    }
    fields.update(extra)
    return Recommendation.model_validate(fields)


@pytest.mark.parametrize(
    "code", [c for c in RecommendationCode if c is not RecommendationCode.ADDRESS_SAFETY_GATE_FIRST]
)
def test_a_positive_gate_allows_only_address_safety_gate_first(code: RecommendationCode) -> None:
    with pytest.raises(ValidationError, match="safety gate"):
        recommendation(code, SafetyGateStatus.POSITIVE)
    assert (
        recommendation(
            RecommendationCode.ADDRESS_SAFETY_GATE_FIRST, SafetyGateStatus.POSITIVE
        ).safety_gate.status
        is SafetyGateStatus.POSITIVE
    )


@pytest.mark.parametrize(
    "code", [RecommendationCode.CONSIDER_REFERRAL, RecommendationCode.NO_RECOMMENDATION]
)
def test_an_unavailable_gate_never_yields_a_clean_or_referral_result(
    code: RecommendationCode,
) -> None:
    with pytest.raises(ValidationError, match="safety gate"):
        recommendation(code, SafetyGateStatus.DATA_UNAVAILABLE)


def test_address_safety_gate_first_needs_a_positive_gate() -> None:
    with pytest.raises(ValidationError, match="safety gate"):
        recommendation(RecommendationCode.ADDRESS_SAFETY_GATE_FIRST, SafetyGateStatus.CLEAR)


def test_a_referral_suggestion_needs_evidence() -> None:
    with pytest.raises(ValidationError, match="basis"):
        recommendation(RecommendationCode.CONSIDER_REFERRAL, SafetyGateStatus.CLEAR, basis=[])


def test_safety_gate_is_serialised_before_the_recommendation() -> None:
    rec = recommendation(RecommendationCode.CONSIDER_REFERRAL, SafetyGateStatus.CLEAR)
    keys = list(rec.model_dump())
    assert keys.index("safety_gate") < keys.index("recommendation")
