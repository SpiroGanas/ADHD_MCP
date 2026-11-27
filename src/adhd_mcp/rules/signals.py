"""Evaluate catalog signals against assembled evidence, as of a date.

Condition-independent: each signal's source and definition come from the catalog. A signal
is present only when it is found inside its window and cites the resources it rests on.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from adhd_mcp.models.assessment import SignalFinding
from adhd_mcp.models.domain import ResourceRef
from adhd_mcp.models.evidence_outputs import (
    DistinctAgents,
    ProblemEntry,
    ProblemFamily,
    PsychosocialDomain,
    UtilizationEvent,
)
from adhd_mcp.rules.catalog import SignalDefinition

_NOT_FOUND = "Not found in the record."
_UNREADABLE = "Not checked: the data it needs could not be read."
_OBSERVATION_ONLY = (
    "Found only in coded social-history observations, which this ruleset does not count."
)


@dataclass(frozen=True)
class SignalEvidence:
    """Evidence from the tools that supply signals. ``None`` means the source could not be
    read, which is reported, never treated as absence."""

    problem_families: Sequence[ProblemFamily] | None = None
    psychosocial: Sequence[PsychosocialDomain] | None = None
    utilization_events: Sequence[UtilizationEvent] | None = None
    distinct_agents: Sequence[DistinctAgents] | None = None
    #: The server offers no dispenses or statements, so agents come from orders alone; the
    #: reason says so (owner decision 2026-11-27).
    agents_from_orders_only: bool = False


_ORDERS_ONLY = (
    " Counted from medication orders only: the FHIR server does not offer dispenses or statements."
)


def _refs(refs: Sequence[ResourceRef]) -> list[ResourceRef]:
    return sorted(set(refs), key=lambda r: (r.resource_type, r.id))


def _finding(s: SignalDefinition, present: bool, reason: str, **kw: object) -> SignalFinding:
    return SignalFinding.model_validate(
        {
            "signal": s.id,
            "title": s.title,
            "weight": s.weight,
            "present": present,
            "reason": reason,
            "window_days": s.window_days,
            "protected": s.protected,
            "references": [],
        }
        | kw
    )


def _entry_interval(e: ProblemEntry) -> tuple[date | None, date | None]:
    """When the condition was known: from its first date to its last record if resolved,
    otherwise open-ended (still current)."""
    starts = [d for d in (e.onset, e.first_recorded) if d is not None]
    start = min(starts) if starts else None
    end = (e.last_recorded or start) if e.resolved else None
    return start, end


def _entries(s: SignalDefinition, entries: Sequence[ProblemEntry], as_of: date) -> SignalFinding:
    if not entries:
        return _finding(s, False, _NOT_FOUND)
    window_start = as_of - timedelta(days=s.window_days)
    current: list[tuple[date, ProblemEntry]] = []
    undated = 0
    for e in entries:
        start, end = _entry_interval(e)
        if start is None:
            undated += 1
        elif start <= as_of and (end is None or end >= window_start):
            current.append((start, e))
    if not current:
        if undated == len(entries):
            return _finding(s, False, "Found, but undated, so not counted.")
        return _finding(s, False, f"Found, but outside the {s.window_days}-day window.")
    lasts = [e.last_recorded or start for start, e in current]
    return _finding(
        s,
        True,
        f"Found within {s.window_days} days.",
        first_date=min(start for start, _ in current),
        last_date=max(lasts),
        references=_refs([r for _, e in current for r in e.references]),
    )


def _counted(
    s: SignalDefinition,
    items: Sequence[tuple[date, date, list[ResourceRef]]],
    as_of: date,
) -> SignalFinding:
    """Items are (first, last, refs); an item counts if any part is in the window."""
    if not items:
        return _finding(s, False, _NOT_FOUND)
    window_start = as_of - timedelta(days=s.window_days)
    inside = [i for i in items if i[0] <= as_of and i[1] >= window_start]
    count = len(inside)
    if count < s.min_count:
        reason = f"{count} found within {s.window_days} days; {s.min_count} required."
        return _finding(s, False, reason, count=count)
    return _finding(
        s,
        True,
        f"{count} found within {s.window_days} days ({s.min_count} required).",
        count=count,
        first_date=min(i[0] for i in inside),
        last_date=max(i[1] for i in inside),
        references=_refs([r for i in inside for r in i[2]]),
    )


def evaluate_signal(  # noqa: PLR0911 - one return per outcome
    s: SignalDefinition, evidence: SignalEvidence, as_of: date
) -> SignalFinding:
    if s.source in ("condition", "psychosocial"):
        observed = False
        if s.source == "condition":
            readable = evidence.problem_families is not None
            entries = [
                e
                for f in evidence.problem_families or ()
                if f.family in s.value_sets
                for e in f.entries
            ]
        else:
            readable = evidence.psychosocial is not None
            observed = any(
                d.observation_references
                for d in evidence.psychosocial or ()
                if d.domain == s.domain
            )
            entries = [
                e
                for d in evidence.psychosocial or ()
                if d.domain == s.domain
                for f in d.families
                for e in f.entries
            ]
        if not readable:
            return _finding(s, False, _UNREADABLE)
        if s.source == "psychosocial" and not entries and observed:
            return _finding(s, False, _OBSERVATION_ONLY)
        return _entries(s, entries, as_of)
    if s.source == "events":
        if evidence.utilization_events is None:
            return _finding(s, False, _UNREADABLE)
        events = [
            (e.date, e.date, e.references)
            for e in evidence.utilization_events
            if e.kind == s.event and e.date is not None
        ]
        return _counted(s, events, as_of)
    if evidence.distinct_agents is None:
        return _finding(s, False, _UNREADABLE)
    agents = [
        (a.first_date, a.last_date, a.references)
        for d in evidence.distinct_agents
        if d.drug_class == s.drug_class
        for a in d.agents
    ]
    finding = _counted(s, agents, as_of)
    if evidence.agents_from_orders_only:
        finding = finding.model_copy(update={"reason": finding.reason + _ORDERS_ONLY})
    return finding


def evaluate_signals(
    signals: Sequence[SignalDefinition], evidence: SignalEvidence, as_of: date
) -> list[SignalFinding]:
    return [evaluate_signal(s, evidence, as_of) for s in signals]
