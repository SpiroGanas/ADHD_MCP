"""The rules engine: pure, deterministic, condition-independent."""

import random

import pytest

from adhd_mcp.models.assessment import SignalFinding
from adhd_mcp.models.domain import ResourceRef
from adhd_mcp.rules.engine import decide
from adhd_mcp.rules.ruleset import Ruleset, load_ruleset

RULESET = load_ruleset("adhd_mcp.data.adhd")


def finding(i: str, weight: str, *, present: bool = True) -> SignalFinding:
    return SignalFinding(
        signal=i,
        title=i,
        weight=weight,
        present=present,
        reason="r",
        window_days=1095,
        references=[ResourceRef(resource_type="Condition", id=i)] if present else [],
    )


def fired(findings: list[SignalFinding], ruleset: Ruleset = RULESET) -> list[str]:
    return [r.rule_id for r in decide(findings, ruleset).rules if r.fired]


def test_one_high_with_one_modifier_does_not_recommend() -> None:
    decision = decide([finding("h", "high"), finding("m1", "modifier")], RULESET)
    assert decision.recommend is False
    first = decision.rules[0]
    assert first.reason == "1 high-weight (needs 1) and 1 modifiers (needs 2)."


def test_one_high_with_two_modifiers_recommends() -> None:
    findings = [finding("h", "high"), finding("m1", "modifier"), finding("m2", "modifier")]
    assert fired(findings) == ["high_with_modifiers"]
    assert decide(findings, RULESET).recommend is True


def test_two_high_classes_recommend_without_modifiers() -> None:
    assert fired([finding("h1", "high"), finding("h2", "high")]) == ["two_high_classes"]


def test_absent_and_note_signals_never_count() -> None:
    findings = [
        finding("h1", "high"),
        finding("h2", "high", present=False),
        finding("n", "note"),
        finding("m1", "modifier"),
        finding("m2", "modifier", present=False),
    ]
    decision = decide(findings, RULESET)
    assert decision.recommend is False
    assert decision.rules[0].high_signals == ["h1"]
    assert decision.rules[0].modifier_signals == ["m1"]


def test_no_signals_no_rule_fires() -> None:
    decision = decide([], RULESET)
    assert decision.recommend is False
    assert all(not r.fired for r in decision.rules)


def test_fired_rules_name_exactly_the_signals_they_counted() -> None:
    findings = [finding("h1", "high"), finding("h2", "high"), finding("m", "modifier")]
    for rule in decide(findings, RULESET).rules:
        assert rule.high_signals == ["h1", "h2"]
        assert rule.modifier_signals == ["m"]


@pytest.mark.parametrize("seed", range(5))
def test_input_order_does_not_change_the_decision(seed: int) -> None:
    findings = [finding(f"h{i}", "high") for i in range(2)] + [
        finding(f"m{i}", "modifier") for i in range(3)
    ]
    shuffled = findings[:]
    random.Random(seed).shuffle(shuffled)  # noqa: S311 - test data order, not security
    assert decide(findings, RULESET) == decide(shuffled, RULESET)
