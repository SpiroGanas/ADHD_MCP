"""``assess_referral_need`` orchestration: safety gate, exclusions, evidence, rules.

Order of precedence for the recommendation:

1. a positive safety gate: address the safety gate first (other findings still reported);
2. a safety gate that could not be evaluated: insufficient data;
3. already in care for the condition: already in care;
4. a rule fired: consider referral for formal screening;
5. an empty record, or a signal source that could not be read completely: insufficient data;
6. otherwise: no recommendation.

Every evidence assembler reads through one request-scoped cached port, so no FHIR query is
issued twice. Nothing here is specific to a condition.
"""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from adhd_mcp.conditions.base import ConditionPlugin, ExclusionResult
from adhd_mcp.evidence.medication_timeline import (
    assemble_medication_timeline,
    load_medication_content,
)
from adhd_mcp.evidence.problem_list import assemble_problem_list, load_problem_list_content
from adhd_mcp.evidence.psychosocial import assemble_psychosocial, load_psychosocial_content
from adhd_mcp.evidence.safety_gate import assess_safety_gate, load_gate_content
from adhd_mcp.evidence.utilization import assemble_utilization, load_utilization_content
from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.models.assessment import ScorerRef, SignalFinding
from adhd_mcp.models.domain import (
    DataCompleteness,
    DataStatus,
    EvidenceItem,
    RecommendationCode,
    SafetyGateResult,
    SafetyGateStatus,
    WeightClass,
)
from adhd_mcp.rules.engine import Decision, decide
from adhd_mcp.rules.scorer import run_scorer
from adhd_mcp.rules.signals import SignalEvidence, evaluate_signals
from adhd_mcp.terminology.site_codes import SiteCodes

_SEVERITY = {
    DataStatus.AVAILABLE: 0,
    DataStatus.EMPTY: 0,
    DataStatus.WITHHELD: 1,
    DataStatus.NOT_SUPPORTED: 2,
    DataStatus.INCOMPLETE: 3,
    DataStatus.FAILED: 4,
}
_READABLE = frozenset({DataStatus.AVAILABLE, DataStatus.EMPTY})


@dataclass(frozen=True)
class Assessment:
    gate: SafetyGateResult
    exclusions: ExclusionResult
    findings: list[SignalFinding]
    decision: Decision
    recommendation: RecommendationCode
    basis: list[EvidenceItem]
    notes: list[str]
    data_completeness: list[DataCompleteness]
    scorer: ScorerRef | None


def merge_completeness(notes: Sequence[DataCompleteness]) -> list[DataCompleteness]:
    """One note per category, the least complete one winning, in first-seen order."""
    merged: dict[str, DataCompleteness] = {}
    for n in notes:
        held = merged.get(n.category)
        if held is None or _SEVERITY[n.status] > _SEVERITY[held.status]:
            merged[n.category] = n
    return list(merged.values())


def _basis(findings: Sequence[SignalFinding]) -> list[EvidenceItem]:
    return [
        EvidenceItem(
            signal=f.signal,
            weight_class=WeightClass(f.weight),
            references=f.references,
            date=f.last_date,
        )
        for f in sorted(findings, key=lambda f: (f.weight != "high", f.signal))
        if f.present and f.weight != "note"
    ]


def _choose(
    gate: SafetyGateResult,
    excluded: bool | None,
    decision: Decision,
    completeness: Sequence[DataCompleteness],
    sources_readable: bool,
) -> RecommendationCode:
    if gate.status is SafetyGateStatus.POSITIVE:
        return RecommendationCode.ADDRESS_SAFETY_GATE_FIRST
    if gate.status is SafetyGateStatus.DATA_UNAVAILABLE:
        return RecommendationCode.INSUFFICIENT_DATA
    if excluded is True:
        return RecommendationCode.ALREADY_IN_CARE
    if decision.recommend:
        return RecommendationCode.CONSIDER_REFERRAL
    # A record with nothing in it: every category empty, or not offered by the server.
    empty = all(n.status in (DataStatus.EMPTY, DataStatus.NOT_SUPPORTED) for n in completeness)
    if empty or not sources_readable:
        return RecommendationCode.INSUFFICIENT_DATA
    return RecommendationCode.NO_RECOMMENDATION


def _status(
    notes: Sequence[DataCompleteness], *categories: str, may_be_absent: Sequence[str] = ()
) -> bool:
    """Whether every category was read completely. A category in ``may_be_absent`` may
    instead be one the server does not offer (a failed or partial read still counts)."""
    return all(
        n.status in _READABLE
        or (n.category in may_be_absent and n.status is DataStatus.NOT_SUPPORTED)
        for n in notes
        if n.category in categories
    )


async def assess(
    plugin: ConditionPlugin,
    records: PatientRecords,
    gate_records: PatientRecords,
    patient_id: str,
    as_of: date,
    *,
    site: SiteCodes,
) -> Assessment:
    async def no_exclusions() -> ExclusionResult:
        return ExclusionResult(excluded=False, checks=[], data_completeness=[])

    exclusions_call = (
        plugin.exclusions(records, patient_id, as_of, site)
        if plugin.exclusions is not None
        else no_exclusions()
    )
    gate_result, exclusions, problems, psychosocial, utilization, medication = await asyncio.gather(
        assess_safety_gate(gate_records, patient_id, as_of, load_gate_content(site)),
        exclusions_call,
        assemble_problem_list(records, patient_id, as_of, load_problem_list_content()),
        assemble_psychosocial(records, patient_id, as_of, load_psychosocial_content(site)),
        assemble_utilization(records, patient_id, as_of, load_utilization_content(site)),
        assemble_medication_timeline(records, patient_id, as_of, load_medication_content()),
    )
    gate, gate_notes = gate_result
    completeness = merge_completeness(
        [
            *gate_notes,
            *exclusions.data_completeness,
            *problems.data_completeness,
            *psychosocial.data_completeness,
            *utilization.data_completeness,
            *medication.data_completeness,
        ]
    )
    conditions_ok = _status(completeness, "Condition")
    evidence = SignalEvidence(
        problem_families=problems.families if conditions_ok else None,
        psychosocial=psychosocial.domains if conditions_ok else None,
        utilization_events=utilization.events
        if _status(completeness, "Encounter", "Condition")
        else None,
        # A server that offers no dispenses or statements leaves orders as the whole
        # medication record (the timeline then uses orders); orders themselves are required.
        distinct_agents=medication.distinct_agents
        if _status(
            completeness,
            "MedicationRequest",
            "MedicationDispense",
            "MedicationStatement",
            may_be_absent=("MedicationDispense", "MedicationStatement"),
        )
        else None,
        agents_from_orders_only=any(
            n.category in ("MedicationDispense", "MedicationStatement")
            and n.status is DataStatus.NOT_SUPPORTED
            for n in completeness
        ),
    )
    findings = evaluate_signals(plugin.catalog.signals, evidence, as_of)
    decision = decide(findings, plugin.ruleset)
    sources_readable = None not in (
        evidence.problem_families,
        evidence.utilization_events,
        evidence.distinct_agents,
    )
    recommendation = _choose(gate, exclusions.excluded, decision, completeness, sources_readable)
    notes = [
        plugin.note_texts[f.signal]
        for f in findings
        if f.present and f.weight == "note" and f.signal in plugin.note_texts
    ]
    notes += exclusions.notes
    scorer = run_scorer(plugin.scorer, findings) if plugin.scorer is not None else None
    return Assessment(
        gate=gate,
        exclusions=exclusions,
        findings=findings,
        decision=decision,
        recommendation=recommendation,
        basis=_basis(findings),
        notes=notes,
        data_completeness=completeness,
        scorer=scorer,
    )
