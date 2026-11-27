from datetime import date

import pytest
from pydantic import ValidationError

from adhd_mcp.models.domain import (
    CheckOutcome,
    DataCompleteness,
    DataStatus,
    EvidenceItem,
    ExclusionCheck,
    Recommendation,
    RecommendationCode,
    ResourceRef,
    SafetyCheck,
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


def check(outcome: CheckOutcome, check_id: str = "suicidal_ideation") -> SafetyCheck:
    reason = None if outcome in {CheckOutcome.FOUND, CheckOutcome.NOT_FOUND} else "why"
    return SafetyCheck(id=check_id, description="d", outcome=outcome, reason=reason)


GATE_CHECKS = {
    SafetyGateStatus.POSITIVE: [check(CheckOutcome.FOUND)],
    SafetyGateStatus.CLEAR: [check(CheckOutcome.NOT_FOUND)],
    SafetyGateStatus.CLEAR_LIMITED_DATA: [check(CheckOutcome.NOT_PERFORMED)],
    SafetyGateStatus.DATA_UNAVAILABLE: [check(CheckOutcome.FAILED)],
}


def clear_gate() -> SafetyGateResult:
    return SafetyGateResult(
        status=SafetyGateStatus.CLEAR, checks=GATE_CHECKS[SafetyGateStatus.CLEAR]
    )


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
        SafetyGateResult(
            status=SafetyGateStatus.POSITIVE,
            checks=GATE_CHECKS[SafetyGateStatus.POSITIVE],
            guidance="g",
        )


def test_positive_safety_gate_with_evidence_is_valid() -> None:
    gate = SafetyGateResult(
        status=SafetyGateStatus.POSITIVE,
        checks=GATE_CHECKS[SafetyGateStatus.POSITIVE],
        evidence=[evidence(signal="suicidal_ideation", weight_class=None)],
        guidance="g",
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
        exclusions_checked=[
            ExclusionCheck(check="adhd_diagnosis_code", outcome=CheckOutcome.NOT_FOUND)
        ],
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
        ExclusionCheck(check="adhd_diagnosis_code", outcome=CheckOutcome.FOUND)


def gate(status: SafetyGateStatus) -> SafetyGateResult:
    evidence_items = [evidence(signal="suicidal_ideation", weight_class=None)]
    positive = status is SafetyGateStatus.POSITIVE
    return SafetyGateResult(
        status=status,
        checks=GATE_CHECKS[status],
        evidence=evidence_items if positive else [],
        guidance="g" if positive else None,
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


@pytest.mark.parametrize(
    ("status", "outcomes", "valid"),
    [
        (SafetyGateStatus.CLEAR, [CheckOutcome.NOT_FOUND, CheckOutcome.NOT_FOUND], True),
        (SafetyGateStatus.CLEAR, [CheckOutcome.NOT_FOUND, CheckOutcome.NOT_PERFORMED], False),
        (SafetyGateStatus.CLEAR, [CheckOutcome.NOT_FOUND, CheckOutcome.FAILED], False),
        (SafetyGateStatus.CLEAR_LIMITED_DATA, [CheckOutcome.NOT_FOUND], True),
        (SafetyGateStatus.CLEAR_LIMITED_DATA, [CheckOutcome.NOT_PERFORMED], True),
        (SafetyGateStatus.CLEAR_LIMITED_DATA, [CheckOutcome.FAILED], False),
        (SafetyGateStatus.CLEAR_LIMITED_DATA, [CheckOutcome.FOUND], False),
        (SafetyGateStatus.DATA_UNAVAILABLE, [CheckOutcome.FAILED, CheckOutcome.NOT_FOUND], True),
        (SafetyGateStatus.DATA_UNAVAILABLE, [CheckOutcome.NOT_FOUND], False),
        (SafetyGateStatus.DATA_UNAVAILABLE, [CheckOutcome.FAILED, CheckOutcome.FOUND], False),
        (SafetyGateStatus.POSITIVE, [CheckOutcome.FOUND, CheckOutcome.FAILED], True),
        (SafetyGateStatus.POSITIVE, [CheckOutcome.NOT_FOUND], False),
    ],
)
def test_gate_status_must_agree_with_check_outcomes(
    status: SafetyGateStatus, outcomes: list[CheckOutcome], valid: bool
) -> None:
    positive = status is SafetyGateStatus.POSITIVE
    fields: dict[str, object] = {
        "status": status,
        "checks": [check(o, f"c{i}") for i, o in enumerate(outcomes)],
        "evidence": [evidence(signal="c0", weight_class=None)] if positive else [],
        "guidance": "g" if positive else None,
    }
    if valid:
        assert SafetyGateResult.model_validate(fields).status is status
    else:
        with pytest.raises(ValidationError):
            SafetyGateResult.model_validate(fields)


def test_gate_needs_at_least_one_check() -> None:
    with pytest.raises(ValidationError):
        SafetyGateResult(status=SafetyGateStatus.CLEAR_LIMITED_DATA, checks=[])


def test_guidance_is_given_exactly_when_positive() -> None:
    with pytest.raises(ValidationError, match="guidance"):
        SafetyGateResult(
            status=SafetyGateStatus.POSITIVE,
            checks=GATE_CHECKS[SafetyGateStatus.POSITIVE],
            evidence=[evidence(signal="suicidal_ideation", weight_class=None)],
        )
    with pytest.raises(ValidationError, match="guidance"):
        SafetyGateResult(
            status=SafetyGateStatus.CLEAR,
            checks=GATE_CHECKS[SafetyGateStatus.CLEAR],
            guidance="g",
        )


def test_a_check_not_performed_or_failed_must_say_why() -> None:
    for outcome in (CheckOutcome.NOT_PERFORMED, CheckOutcome.FAILED):
        with pytest.raises(ValidationError, match="reason"):
            SafetyCheck(id="x", description="d", outcome=outcome)


def test_check_ids_are_unique() -> None:
    with pytest.raises(ValidationError, match="unique"):
        SafetyGateResult(
            status=SafetyGateStatus.CLEAR,
            checks=[check(CheckOutcome.NOT_FOUND), check(CheckOutcome.NOT_FOUND)],
        )


def test_incomplete_data_status_exists() -> None:
    note = DataCompleteness(
        category="Flag", status=DataStatus.INCOMPLETE, records=2, warnings=["suppressed"]
    )
    assert note.status == "incomplete"


def test_exclusion_not_performed_or_failed_must_say_why() -> None:
    for outcome in (CheckOutcome.NOT_PERFORMED, CheckOutcome.FAILED):
        with pytest.raises(ValidationError, match="reason"):
            ExclusionCheck(check="adhd_care_plan", outcome=outcome)
    check = ExclusionCheck(check="adhd_care_plan", outcome=CheckOutcome.FAILED, reason="r")
    assert check.found is False
