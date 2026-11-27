"""The rules engine: applies a ruleset to signal findings and explains every rule.

Pure and deterministic: the same findings (in any order) and ruleset always give the same
decision. It knows nothing about any condition.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from adhd_mcp.models.assessment import RuleOutcome, SignalFinding
from adhd_mcp.rules.ruleset import Ruleset


@dataclass(frozen=True)
class Decision:
    recommend: bool
    rules: list[RuleOutcome]


def decide(findings: Sequence[SignalFinding], ruleset: Ruleset) -> Decision:
    present = sorted((f for f in findings if f.present), key=lambda f: f.signal)
    high = [f.signal for f in present if f.weight == "high"]
    modifiers = [f.signal for f in present if f.weight == "modifier"]
    outcomes = []
    for rule in ruleset.rules:
        fired = len(high) >= rule.min_high and len(modifiers) >= rule.min_modifiers
        reason = (
            f"{len(high)} high-weight (needs {rule.min_high}) and {len(modifiers)} "
            f"modifiers (needs {rule.min_modifiers})."
        )
        outcomes.append(
            RuleOutcome(
                rule_id=rule.id,
                description=rule.description,
                fired=fired,
                reason=reason,
                high_signals=high,
                modifier_signals=modifiers,
            )
        )
    return Decision(recommend=any(o.fired for o in outcomes), rules=outcomes)
