"""The rules engine: applies a ruleset to signal findings and explains every rule.

Pure and deterministic: the same findings (in any order) and ruleset always give the same
decision. It knows nothing about any condition.

High-weight classes count only as far as they rest on separate units (visits or records):
one visit never supplies two high-weight signals, and a signal that needs several events
needs that many units no other counted class uses (peer review 01, C2; owner decision
2026-11-28, a draft for the clinical reviewer).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations

from adhd_mcp.models.assessment import RuleOutcome, SignalFinding
from adhd_mcp.rules.ruleset import Ruleset


@dataclass(frozen=True)
class Decision:
    recommend: bool
    rules: list[RuleOutcome]


#: Per high-weight signal: the units it rests on and how many distinct ones it needs.
Units = Mapping[str, tuple[frozenset[str], int]]


def _fits(signals: Sequence[str], units: Units, used: frozenset[str]) -> bool:
    """Whether every signal can take its needed units, none shared."""
    if not signals:
        return True
    first, rest = signals[0], signals[1:]
    pool, need = units[first]
    free = pool - used
    others = frozenset().union(*(units[s][0] for s in rest))
    # Units no later signal could use are taken first; only shared ones need a search.
    own = sorted(free - others)[:need]
    shared = sorted(free & others)
    return any(
        _fits(rest, units, used | set(own) | set(pick))
        for pick in combinations(shared, max(need - len(own), 0))
    )


def independent_high(high: Sequence[str], units: Units | None) -> int:
    """The most high-weight classes that can count at once on separate units."""
    if units is None:
        return len(high)
    full = {s: units.get(s, (frozenset({f"signal:{s}"}), 1)) for s in high}
    for size in range(len(high), 0, -1):
        for subset in combinations(sorted(high), size):
            ordered = sorted(subset, key=lambda s: (len(full[s][0]), s))
            if _fits(ordered, full, frozenset()):
                return size
    return 0


def decide(
    findings: Sequence[SignalFinding], ruleset: Ruleset, units: Units | None = None
) -> Decision:
    """``units`` maps present high-weight signals to the visits or records they rest on;
    without it every present class counts."""
    present = sorted((f for f in findings if f.present), key=lambda f: f.signal)
    high = [f.signal for f in present if f.weight == "high"]
    modifiers = [f.signal for f in present if f.weight == "modifier"]
    separate = independent_high(high, units)
    counted = (
        f"{len(high)} high-weight"
        if separate == len(high)
        else f"{len(high)} high-weight, {separate} resting on separate visits or records"
    )
    outcomes = []
    for rule in ruleset.rules:
        fired = separate >= rule.min_high and len(modifiers) >= rule.min_modifiers
        reason = (
            f"{counted} (needs {rule.min_high}) and {len(modifiers)} "
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
