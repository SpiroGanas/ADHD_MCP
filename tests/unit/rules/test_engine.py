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


# --- peer review 01, C2: one encounter supplies at most one high-weight signal ---------
# ``units`` maps each present high-weight signal to the visits (or records) it rests on and
# how many distinct ones it needs. Classes count only as far as they can rest on separate
# units (owner decision 2026-11-28, a draft for the clinical reviewer).


def units(**kw: tuple[set[str], int]) -> dict[str, tuple[frozenset[str], int]]:
    return {k: (frozenset(v[0]), v[1]) for k, v in kw.items()}


def test_two_high_signals_from_one_visit_count_once() -> None:
    # E2: a crash visit with a blood alcohol code.
    findings = [finding("crash", "high"), finding("alcohol", "high")]
    decision = decide(findings, RULESET, units(crash=({"e1"}, 1), alcohol=({"e1"}, 1)))
    assert decision.recommend is False
    two = next(r for r in decision.rules if r.rule_id == "two_high_classes")
    assert two.reason == (
        "2 high-weight, 1 resting on separate visits or records (needs 2) and 0 modifiers "
        "(needs 0)."
    )


def test_a_crash_visit_cannot_also_be_one_of_two_injuries() -> None:
    # E2b: two crash visits, each also an injury visit.
    findings = [finding("crash", "high"), finding("injury", "high")]
    decision = decide(findings, RULESET, units(crash=({"e1", "e2"}, 1), injury=({"e1", "e2"}, 2)))
    assert decision.recommend is False


def test_separate_visits_count_separately() -> None:
    # p01: a crash visit and two other injury visits, plus problem-list codes.
    findings = [finding("crash", "high"), finding("injury", "high"), finding("stim", "high")]
    decision = decide(
        findings,
        RULESET,
        units(crash=({"e2"}, 1), injury=({"e1", "e2", "e3"}, 2), stim=({"c1"}, 1)),
    )
    assert fired(findings) == ["two_high_classes"]
    assert decision.recommend is True
    assert decision.rules[1].reason == "3 high-weight (needs 2) and 0 modifiers (needs 0)."


def test_a_signal_with_another_unit_keeps_its_class() -> None:
    findings = [finding("crash", "high"), finding("alcohol", "high")]
    decision = decide(findings, RULESET, units(crash=({"e1"}, 1), alcohol=({"e1", "c9"}, 1)))
    assert decision.recommend is True
