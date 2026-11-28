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
    """When the condition was known: from its first date to its last date, or open-ended
    when the entry is current (an active problem-list item; peer review 01, C1)."""
    starts = [d for d in (e.onset, e.first_recorded) if d is not None]
    start = min(starts) if starts else None
    end = None if e.current else (e.last_date or e.last_recorded or start)
    return start, end


def _entries(s: SignalDefinition, entries: Sequence[ProblemEntry], as_of: date) -> SignalFinding:
    """A condition signal. The reason states the dates it rests on, never a recency that is
    not true (peer review 01, C1)."""
    if not entries:
        return _finding(s, False, _NOT_FOUND)
    window_start = as_of - timedelta(days=s.window_days)
    dated: list[tuple[date, date, ProblemEntry]] = []
    open_ended: list[tuple[date, ProblemEntry]] = []
    outside: list[date] = []
    undated = 0
    for e in entries:
        start, end = _entry_interval(e)
        if start is None:
            undated += 1
        elif start > as_of:
            continue
        elif end is None:
            open_ended.append((start, e))
        elif end >= window_start:
            dated.append((start, min(end, as_of), e))
        else:
            outside.append(end)
    if not dated and not open_ended:
        if outside:
            return _finding(
                s,
                False,
                f"Last recorded {max(outside)}, outside the {s.window_days}-day window.",
            )
        if undated:
            return _finding(s, False, "Found, but undated, so not counted.")
        return _finding(s, False, _NOT_FOUND)
    parts = []
    if dated:
        last = max(end for _, end, _ in dated)
        parts.append(f"Last recorded {last}, within the {s.window_days}-day window.")
    if open_ended:
        first = min(start for start, _ in open_ended)
        lead = "Also counted" if dated else "Counted"
        parts.append(f"{lead} as current: an active problem-list entry since {first}.")
    used = [e for _, _, e in dated] + [e for _, e in open_ended]
    starts = [start for start, _, _ in dated] + [start for start, _ in open_ended]
    lasts = [end for _, end, _ in dated] + [
        min(e.last_date or start, as_of) for start, e in open_ended
    ]
    return _finding(
        s,
        True,
        " ".join(parts),
        first_date=min(starts),
        last_date=max(lasts),
        references=_refs([r for e in used for r in e.references]),
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
