"""Standing invariant 2: no recommendation without a safety gate result, and a positive
safety gate is never lost. Checked over generated records and generated gate results."""

import asyncio
from datetime import date, timedelta

import pytest
from hypothesis import event, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from adhd_mcp.evidence.safety_gate import assess_safety_gate, load_gate_content
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.models.domain import (
    CheckOutcome,
    EvidenceItem,
    Recommendation,
    RecommendationCode,
    ResourceRef,
    SafetyCheck,
    SafetyGateResult,
    SafetyGateStatus,
    Versions,
)
from adhd_mcp.terminology.site_codes import load_site_codes
from tests.personas.builder import PersonaBuilder

AS_OF = date(2026, 6, 15)
CONTENT = load_gate_content(load_site_codes("synthetic"), strict=True)

SELF_HARM_CODES = ["R45.851", "T14.91XA", "X71.0XXA", "T42.4X2A", "T42.4X4A", "R45.88", "Z91.51"]
OTHER_CODES = ["I10", "F43.10", "G47.00", "T14.90XA", "R45.850", "T42.4X1A"]

conditions = st.lists(
    st.tuples(
        st.sampled_from(SELF_HARM_CODES + OTHER_CODES),
        st.one_of(st.none(), st.integers(min_value=-30, max_value=800)),
    ),
    max_size=6,
)


def gate_for(items: list[tuple[str, int | None]]) -> SafetyGateResult:
    p = PersonaBuilder("h01", gender="unknown", birth_date="1980")
    for code, days in items:
        recorded = None if days is None else (AS_OF - timedelta(days=days)).isoformat()
        p.condition(code, "generated", recorded=recorded)
    records = PatientRecords(FixtureFhirAdapter(p.resources))
    result, _ = asyncio.run(assess_safety_gate(records, p.patient_id, AS_OF, CONTENT))
    return result


@settings(max_examples=150, deadline=None)
@given(items=conditions)
def test_a_current_self_harm_code_always_makes_the_gate_positive(
    items: list[tuple[str, int | None]],
) -> None:
    result = gate_for(items)
    event(f"gate: {result.status}")
    current = [
        (code, days)
        for code, days in items
        if code in SELF_HARM_CODES and (days is None or 0 <= days <= 365)
    ]
    assert (result.status is SafetyGateStatus.POSITIVE) == bool(current)
    if current:
        assert result.evidence
        assert result.guidance
        assert all(item.references for item in result.evidence)
    else:
        # The unverified LOINC checks are not performed, so never a plain "clear".
        assert result.status is SafetyGateStatus.CLEAR_LIMITED_DATA


outcomes = st.lists(st.sampled_from(list(CheckOutcome)), min_size=1, max_size=6)
statuses = st.sampled_from(list(SafetyGateStatus))
codes = st.sampled_from(list(RecommendationCode))
REF = ResourceRef(resource_type="Condition", id="h-1")


def build_gate(status: SafetyGateStatus, checks: list[CheckOutcome]) -> SafetyGateResult:
    positive = status is SafetyGateStatus.POSITIVE
    return SafetyGateResult(
        status=status,
        checks=[
            SafetyCheck(id=f"c{i}", description="d", outcome=o, reason="r")
            for i, o in enumerate(checks)
        ],
        evidence=[EvidenceItem(signal="c", references=[REF])] if positive else [],
        guidance="g" if positive else None,
    )


@settings(max_examples=400)
@given(status=statuses, checks=outcomes)
def test_a_gate_result_always_agrees_with_its_checks(
    status: SafetyGateStatus, checks: list[CheckOutcome]
) -> None:
    try:
        gate = build_gate(status, checks)
    except ValidationError:
        event("inconsistent gate rejected")
        return
    event(f"valid gate: {gate.status}")
    found = CheckOutcome.FOUND in checks
    assert (gate.status is SafetyGateStatus.POSITIVE) == found
    if gate.status is SafetyGateStatus.CLEAR:
        assert set(checks) == {CheckOutcome.NOT_FOUND}
    if CheckOutcome.FAILED in checks and not found:
        assert gate.status is SafetyGateStatus.DATA_UNAVAILABLE


@settings(max_examples=400)
@given(status=statuses, checks=outcomes, code=codes)
def test_no_recommendation_hides_a_positive_gate(
    status: SafetyGateStatus, checks: list[CheckOutcome], code: RecommendationCode
) -> None:
    try:
        gate = build_gate(status, checks)
        recommendation = Recommendation(
            safety_gate=gate,
            recommendation=code,
            condition_to_screen="adult ADHD",
            basis=[EvidenceItem(signal="s", references=[REF])],
            versions=Versions(server="0", tool_contract="0"),
        )
    except ValidationError:
        event("rejected")
        return
    event(f"accepted: {status} -> {code}")
    assert recommendation.safety_gate is gate
    if gate.status is SafetyGateStatus.POSITIVE:
        assert recommendation.recommendation is RecommendationCode.ADDRESS_SAFETY_GATE_FIRST


def test_a_recommendation_cannot_be_built_without_a_gate() -> None:
    with pytest.raises(ValidationError, match="safety_gate"):
        Recommendation.model_validate(
            {
                "recommendation": "no_recommendation",
                "condition_to_screen": "adult ADHD",
                "versions": {"server": "0", "tool_contract": "0"},
            }
        )
