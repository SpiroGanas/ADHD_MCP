"""The ruleset evaluation harness (Phase 7, item 2).

Runs every cohort patient through the same code path as ``assess_referral_need`` (the
fixture adapter, the privacy policy, the safety gate, exclusions, evidence and rules) and
computes the report: agreement with the intended outcomes, which signals drive the
suggestions, suggestion rates by sex and age band, how the research-profile groups are
treated, and how the results move when each threshold moves.

Metric functions are pure and work on ``PatientResult`` lists, so a test can check them on
a tiny cohort against numbers worked out by hand.
"""

import dataclasses
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, time
from typing import Any

from adhd_mcp.clock import FixedClock
from adhd_mcp.conditions.adhd import adhd_plugin
from adhd_mcp.conditions.base import ConditionPlugin, ConditionRegistry
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.rules.catalog import SignalDefinition
from adhd_mcp.rules.ruleset import Rule
from adhd_mcp.terminology.site_codes import load_site_codes
from adhd_mcp.tools.assessment import run_assessment
from adhd_mcp.tools.context import ToolContext
from tests.evals.cohort import AS_OF, CONSIDER, CohortPatient, all_resources

FIELDS = ("recommendation", "signals", "rules_fired", "safety_gate")

#: Illustrative presentation mix for the sex-balance reweighting: the share of suggestive
#: presentations of each style, per sex. An assumption for illustration, NOT an estimate: the
#: research report says women are more often first labelled depressed or anxious, and gives
#: no numbers.
MIX: dict[str, dict[str, float]] = {
    "female": {"internalizing": 0.7, "externalizing": 0.3},
    "male": {"internalizing": 0.3, "externalizing": 0.7},
}


@dataclass(frozen=True)
class PatientResult:
    patient: CohortPatient
    recommendation: str
    signals: frozenset[str]
    """Present signals, notes included."""
    counted: frozenset[str]
    """Present high-weight and modifier signals (what the rules count)."""
    rules_fired: tuple[str, ...]
    safety_gate: str

    @property
    def flagged(self) -> bool:
        return self.recommendation == CONSIDER

    def expected(self, name: str) -> Any:
        a = self.patient.archetype
        return {
            "recommendation": a.recommendation,
            "signals": a.signals,
            "rules_fired": a.rules_fired,
            "safety_gate": a.safety_gate,
        }[name]

    def actual(self, name: str) -> Any:
        return getattr(self, name)


# --- running --------------------------------------------------------------------------------


def _context(patients: Sequence[CohortPatient], plugin: ConditionPlugin) -> ToolContext:
    registry = ConditionRegistry()
    registry.register(plugin)
    return ToolContext(
        port=FixtureFhirAdapter(all_resources(list(patients))),
        clock=FixedClock(datetime.combine(AS_OF, time(12), tzinfo=UTC)),
        site_codes=load_site_codes("synthetic"),
        conditions=registry,
    )


async def run_cohort(
    patients: Sequence[CohortPatient], plugin: ConditionPlugin | None = None
) -> list[PatientResult]:
    plugin = plugin or adhd_plugin()
    context = _context(patients, plugin)
    results = []
    for p in patients:
        _, a = await run_assessment(context, p.patient_id, None, plugin.id)
        present = [f for f in a.findings if f.present]
        results.append(
            PatientResult(
                patient=p,
                recommendation=a.recommendation.value,
                signals=frozenset(f.signal for f in present),
                counted=frozenset(f.signal for f in present if f.weight != "note"),
                rules_fired=tuple(r.rule_id for r in a.decision.rules if r.fired),
                safety_gate=a.gate.status.value,
            )
        )
    return results


# --- metrics --------------------------------------------------------------------------------


@dataclass(frozen=True)
class Mismatch:
    patient_id: str
    archetype: str
    field: str
    expected: str
    actual: str


def _show(value: Any) -> str:
    if isinstance(value, frozenset | tuple):
        return ", ".join(sorted(value)) or "(none)"
    return str(value)


def agreement(results: Sequence[PatientResult]) -> dict[str, Any]:
    mismatches = [
        Mismatch(
            r.patient.patient_id,
            r.patient.archetype.id,
            name,
            _show(r.expected(name)),
            _show(r.actual(name)),
        )
        for r in results
        for name in FIELDS
        if (frozenset(r.expected(name)) if name == "rules_fired" else r.expected(name))
        != (frozenset(r.actual(name)) if name == "rules_fired" else r.actual(name))
    ]
    wrong = {m.patient_id for m in mismatches}
    return {
        "patients": len(results),
        "agree": len(results) - len(wrong),
        "by_field": {
            name: sum(1 for r in results if not any(
                m.patient_id == r.patient.patient_id and m.field == name for m in mismatches
            ))
            for name in FIELDS
        },
        "mismatches": [dataclasses.asdict(m) for m in mismatches],
    }  # fmt: skip


def rate(flagged: int, total: int) -> dict[str, Any]:
    return {
        "flagged": flagged,
        "total": total,
        "rate": round(flagged / total, 3) if total else None,
    }


def _grouped(
    results: Iterable[PatientResult], key: Callable[[PatientResult], str]
) -> dict[str, list[PatientResult]]:
    groups: dict[str, list[PatientResult]] = {}
    for r in results:
        groups.setdefault(key(r), []).append(r)
    return dict(sorted(groups.items()))


def recommendation_counts(results: Sequence[PatientResult]) -> dict[str, int]:
    return dict(sorted(Counter(r.recommendation for r in results).items()))


def rates_by(
    results: Sequence[PatientResult], key: Callable[[PatientResult], str]
) -> dict[str, dict[str, Any]]:
    return {
        group: rate(sum(r.flagged for r in members), len(members))
        | {"recommendations": recommendation_counts(members)}
        for group, members in _grouped(results, key).items()
    }


def drivers(results: Sequence[PatientResult]) -> dict[str, Any]:
    """Among patients given a referral suggestion: how often each counted signal is present,
    and how often each rule fired."""
    flagged = [r for r in results if r.flagged]
    signals = Counter(s for r in flagged for s in r.counted)
    rules = Counter(rule for r in flagged for rule in r.rules_fired)
    return {
        "flagged": len(flagged),
        "signals": dict(sorted(signals.items(), key=lambda kv: (-kv[1], kv[0]))),
        "rules": dict(sorted(rules.items())),
    }


def by_profile(results: Sequence[PatientResult]) -> dict[str, dict[str, Any]]:
    return rates_by(results, lambda r: r.patient.archetype.profile)


def suggestive_by_style(results: Sequence[PatientResult]) -> dict[str, dict[str, Any]]:
    suggestive = [r for r in results if r.patient.archetype.profile == "suggestive"]
    return rates_by(suggestive, lambda r: r.patient.archetype.style or "none")


def suggestive_by_sex(results: Sequence[PatientResult]) -> dict[str, dict[str, Any]]:
    suggestive = [r for r in results if r.patient.archetype.profile == "suggestive"]
    return rates_by(suggestive, lambda r: r.patient.sex)


def mixed_recall(
    style_rates: Mapping[str, Mapping[str, Any]], mix: Mapping[str, Mapping[str, float]]
) -> dict[str, float | None]:
    """Expected share of suggestive presentations flagged per sex, if each sex's suggestive
    presentations followed ``mix`` (style -> share). A reweighting of the balanced cohort
    under a stated assumption, not a measurement of any population."""
    out: dict[str, float | None] = {}
    for sex, shares in mix.items():
        rates = [style_rates.get(style, {}).get("rate") for style in shares]
        if any(r is None for r in rates):
            out[sex] = None
            continue
        out[sex] = round(
            sum(w * float(r or 0) for w, r in zip(shares.values(), rates, strict=True)), 3
        )
    return out


def archetype_outcomes(results: Sequence[PatientResult]) -> dict[str, dict[str, Any]]:
    return {
        archetype: {
            "title": members[0].patient.archetype.title,
            "profile": members[0].patient.archetype.profile,
            "style": members[0].patient.archetype.style,
            "intended": members[0].patient.archetype.recommendation,
            "recommendations": recommendation_counts(members),
        }
        for archetype, members in _grouped(results, lambda r: r.patient.archetype.id).items()
    }


def changes(baseline: Sequence[PatientResult], variant: Sequence[PatientResult]) -> dict[str, Any]:
    """How a variant's recommendations differ from the baseline's, patient by patient."""
    moved = [
        (b.patient.archetype.id, b.recommendation, v.recommendation)
        for b, v in zip(baseline, variant, strict=True)
        if b.recommendation != v.recommendation
    ]
    profile = by_profile(variant)
    return {
        "flagged": sum(r.flagged for r in variant),
        "suggestive": profile.get("suggestive"),
        "not_suggestive": profile.get("not_suggestive"),
        "mixed_recall": mixed_recall(suggestive_by_style(variant), MIX),
        "changed": len(moved),
        "newly_flagged": dict(sorted(Counter(a for a, _, new in moved if new == CONSIDER).items())),
        "no_longer_flagged": dict(
            sorted(Counter(a for a, old, _ in moved if old == CONSIDER).items())
        ),
    }


# --- variants -------------------------------------------------------------------------------


@dataclass(frozen=True)
class Variant:
    id: str
    description: str
    apply: Callable[[ConditionPlugin], ConditionPlugin]


def with_rule(rule_id: str, **update: int) -> Callable[[ConditionPlugin], ConditionPlugin]:
    def apply(plugin: ConditionPlugin) -> ConditionPlugin:
        rules = tuple(
            r.model_copy(update=update) if r.id == rule_id else r for r in plugin.ruleset.rules
        )
        return dataclasses.replace(
            plugin, ruleset=plugin.ruleset.model_copy(update={"rules": rules})
        )

    return apply


def with_added_rule(rule: Rule) -> Callable[[ConditionPlugin], ConditionPlugin]:
    def apply(plugin: ConditionPlugin) -> ConditionPlugin:
        rules = (*plugin.ruleset.rules, rule)
        return dataclasses.replace(
            plugin, ruleset=plugin.ruleset.model_copy(update={"rules": rules})
        )

    return apply


def with_signals(
    change: Callable[[SignalDefinition], dict[str, Any] | None],
) -> Callable[[ConditionPlugin], ConditionPlugin]:
    """``change`` returns the fields to update for a signal, or None to leave it."""

    def apply(plugin: ConditionPlugin) -> ConditionPlugin:
        signals = tuple(
            s.model_copy(update=update) if (update := change(s)) else s
            for s in plugin.catalog.signals
        )
        catalog = plugin.catalog.model_copy(update={"signals": signals})
        return dataclasses.replace(plugin, catalog=catalog)

    return apply


def _signal(signal_id: str, **update: int) -> Callable[[SignalDefinition], dict[str, Any] | None]:
    return lambda s: update if s.id == signal_id else None


def _windows(old: int, new: int) -> Callable[[SignalDefinition], dict[str, Any] | None]:
    return lambda s: {"window_days": new} if s.window_days == old else None


SENSITIVITY: tuple[Variant, ...] = (
    Variant("hwm_min_high_0", "high_with_modifiers: 0 high-weight signals (2 modifiers alone)",
            with_rule("high_with_modifiers", min_high=0)),
    Variant("hwm_min_high_2", "high_with_modifiers: 2 high-weight signals",
            with_rule("high_with_modifiers", min_high=2)),
    Variant("hwm_min_modifiers_1", "high_with_modifiers: 1 modifier",
            with_rule("high_with_modifiers", min_modifiers=1)),
    Variant("hwm_min_modifiers_3", "high_with_modifiers: 3 modifiers",
            with_rule("high_with_modifiers", min_modifiers=3)),
    Variant("thc_min_high_1", "two_high_classes: 1 high-weight signal",
            with_rule("two_high_classes", min_high=1)),
    Variant("thc_min_high_3", "two_high_classes: 3 high-weight signals",
            with_rule("two_high_classes", min_high=3)),
    Variant("thc_min_modifiers_1", "two_high_classes: also 1 modifier",
            with_rule("two_high_classes", min_modifiers=1)),
    Variant("injuries_1", "repeated_accidental_injury: 1 visit",
            with_signals(_signal("repeated_accidental_injury", min_count=1))),
    Variant("injuries_3", "repeated_accidental_injury: 3 visits",
            with_signals(_signal("repeated_accidental_injury", min_count=3))),
    Variant("injury_window_365", "repeated_accidental_injury: 365-day window",
            with_signals(_signal("repeated_accidental_injury", window_days=365))),
    Variant("injury_window_1095", "repeated_accidental_injury: 1095-day window",
            with_signals(_signal("repeated_accidental_injury", window_days=1095))),
    Variant("crashes_2", "crash_as_driver: 2 crashes",
            with_signals(_signal("crash_as_driver", min_count=2))),
    Variant("antidepressants_2", "multiple_antidepressants: 2 agents",
            with_signals(_signal("multiple_antidepressants", min_count=2))),
    Variant("antidepressants_4", "multiple_antidepressants: 4 agents",
            with_signals(_signal("multiple_antidepressants", min_count=4))),
    Variant("windows_730", "every 1095-day window shortened to 730 days",
            with_signals(_windows(1095, 730))),
    Variant("windows_1460", "every 1095-day window lengthened to 1460 days",
            with_signals(_windows(1095, 1460))),
)  # fmt: skip

#: Options for the sex-balance review (item 3): measured, not adopted. Any adoption is a new
#: ruleset version chosen by the project owner.
OPTIONS: tuple[Variant, ...] = (
    Variant("add_four_modifiers", "Add a rule: four or more distinct modifiers, no high-weight "
            "signal needed", with_added_rule(Rule(id="four_modifiers",
            description="Four or more modifiers", min_high=0, min_modifiers=4))),
    Variant("add_three_modifiers", "Add a rule: three or more distinct modifiers, no "
            "high-weight signal needed", with_added_rule(Rule(id="three_modifiers",
            description="Three or more modifiers", min_high=0, min_modifiers=3))),
    Variant("antidepressants_2", "Count two distinct antidepressants as the modifier "
            "(instead of three)", with_signals(_signal("multiple_antidepressants",
            min_count=2))),
    Variant("hwm_min_modifiers_1", "One high-weight signal with one modifier",
            with_rule("high_with_modifiers", min_modifiers=1)),
)  # fmt: skip


async def run_variants(
    patients: Sequence[CohortPatient],
    baseline: Sequence[PatientResult],
    variants: Sequence[Variant],
) -> dict[str, dict[str, Any]]:
    out = {}
    for v in variants:
        results = await run_cohort(patients, v.apply(adhd_plugin()))
        out[v.id] = {"description": v.description} | changes(baseline, results)
    return out
