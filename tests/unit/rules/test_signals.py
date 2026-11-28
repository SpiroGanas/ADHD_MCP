"""Signal evaluation from assembled evidence: windows, counts, unavailable sources."""

from datetime import date, timedelta

import pytest

from adhd_mcp.models.domain import ResourceRef
from adhd_mcp.models.evidence_outputs import (
    AgentSummary,
    CodeRef,
    DistinctAgents,
    IngredientRef,
    ProblemEntry,
    ProblemFamily,
    PsychosocialDomain,
    UtilizationEvent,
)
from adhd_mcp.rules.catalog import SignalDefinition
from adhd_mcp.rules.signals import SignalEvidence, evaluate_signal

AS_OF = date(2026, 6, 15)


def ref(i: str, kind: str = "Condition") -> ResourceRef:
    return ResourceRef(resource_type=kind, id=i)


def ago(days: int) -> date:
    return AS_OF - timedelta(days=days)


def signal(**kw: object) -> SignalDefinition:
    base: dict[str, object] = {
        "id": "s",
        "title": "S",
        "weight": "high",
        "source": "condition",
        "tool": "t",
        "value_sets": ["mh.ptsd"],
        "window_days": 100,
        "evidence": "e",
        "inference": False,
    }
    return SignalDefinition.model_validate(base | kw)


def entry(
    i: str,
    first: date | None,
    last: date | None = None,
    *,
    resolved: bool = False,
    current: bool | None = None,
) -> ProblemEntry:
    """An entry; by default an active problem-list item (current) unless resolved."""
    return ProblemEntry(
        code=CodeRef(system="x", code="F43.10"),
        onset=None,
        first_recorded=first,
        last_recorded=last or first,
        last_date=last or first,
        clinical_status="resolved" if resolved else "active",
        resolved=resolved,
        current=(not resolved) if current is None else current,
        onset_order=None,
        references=[ref(i)],
    )


def families(*entries: ProblemEntry, family: str = "mh.ptsd") -> SignalEvidence:
    return SignalEvidence(
        problem_families=[ProblemFamily(family=family, title="t", entries=list(entries))]
    )


def test_an_active_condition_recorded_long_ago_is_current() -> None:
    found = evaluate_signal(signal(), families(entry("c1", ago(1000))), AS_OF)
    assert found.present is True
    assert found.references == [ref("c1")]
    assert found.first_date == ago(1000)


@pytest.mark.parametrize(("days", "present"), [(99, True), (100, True), (101, False)])
def test_a_resolved_condition_counts_only_if_last_recorded_in_the_window(
    days: int, present: bool
) -> None:
    found = evaluate_signal(
        signal(), families(entry("c1", ago(500), ago(days), resolved=True)), AS_OF
    )
    assert found.present is present
    if not present:
        assert "outside the 100-day window" in found.reason
        assert found.references == []


def test_a_current_entry_says_why_it_counts_and_when_it_was_first_recorded() -> None:
    # Peer review 01, C1 (E1): the reason said "Found within 1095 days." for 16-year-old codes.
    found = evaluate_signal(signal(), families(entry("c1", ago(1000))), AS_OF)
    assert found.reason == (f"Counted as current: an active problem-list entry since {ago(1000)}.")


@pytest.mark.parametrize(("days", "present"), [(99, True), (100, True), (101, False)])
def test_an_entry_that_is_not_current_counts_by_its_last_date(days: int, present: bool) -> None:
    found = evaluate_signal(
        signal(), families(entry("c1", ago(900), ago(days), current=False)), AS_OF
    )
    assert found.present is present
    if present:
        assert found.reason == f"Last recorded {ago(days)}, within the 100-day window."
    else:
        assert found.reason == f"Last recorded {ago(days)}, outside the 100-day window."
        assert found.references == []


def test_dated_and_current_entries_are_both_explained() -> None:
    found = evaluate_signal(
        signal(),
        families(entry("c1", ago(900)), entry("c2", ago(300), ago(20), current=False)),
        AS_OF,
    )
    assert found.reason == (
        f"Last recorded {ago(20)}, within the 100-day window. Also counted as current: an "
        f"active problem-list entry since {ago(900)}."
    )


def test_an_entry_first_known_after_the_as_of_date_is_not_counted() -> None:
    found = evaluate_signal(signal(), families(entry("c1", AS_OF + timedelta(days=3))), AS_OF)
    assert (found.present, found.reason) == (False, "Not found in the record.")


def test_an_undated_condition_does_not_count() -> None:
    found = evaluate_signal(signal(), families(entry("c1", None)), AS_OF)
    assert found.present is False
    assert "undated" in found.reason


def test_a_condition_in_another_family_is_not_the_signal() -> None:
    found = evaluate_signal(signal(), families(entry("c1", ago(5)), family="mh.depression"), AS_OF)
    assert (found.present, found.reason) == (False, "Not found in the record.")


@pytest.mark.parametrize(
    "kind",
    [
        {},
        {"source": "psychosocial", "value_sets": [], "domain": "legal"},
        {"source": "events", "value_sets": [], "event": "injury_visit"},
        {"source": "distinct_agents", "value_sets": [], "drug_class": "med.antidepressant"},
    ],
)
def test_an_unreadable_source_is_reported_as_such(kind: dict[str, object]) -> None:
    found = evaluate_signal(signal(**kind), SignalEvidence(), AS_OF)
    assert found.present is False
    assert found.reason == "Not checked: the data it needs could not be read."


def psychosocial_signal() -> SignalDefinition:
    return signal(source="psychosocial", value_sets=[], domain="legal", weight="modifier")


def test_psychosocial_signal_uses_its_domain_entries() -> None:
    domain = PsychosocialDomain(
        domain="legal",
        title="t",
        status="found",
        families=[
            ProblemFamily(
                family="psychosocial.legal_problems", title="t", entries=[entry("z", ago(3))]
            )
        ],
        observation_references=[],
    )
    other = domain.model_copy(update={"domain": "housing"})
    found = evaluate_signal(
        psychosocial_signal(), SignalEvidence(psychosocial=[other, domain]), AS_OF
    )
    assert found.present is True
    assert found.references == [ref("z")]


def test_psychosocial_domain_not_found() -> None:
    domain = PsychosocialDomain(
        domain="legal", title="t", status="not_found", families=[], observation_references=[]
    )
    found = evaluate_signal(psychosocial_signal(), SignalEvidence(psychosocial=[domain]), AS_OF)
    assert found.present is False


def events_signal(min_count: int = 2) -> SignalDefinition:
    return signal(source="events", value_sets=[], event="injury_visit", min_count=min_count)


def event(i: str, day: date | None, kind: str = "injury_visit") -> UtilizationEvent:
    return UtilizationEvent(kind=kind, date=day, references=[ref(i, "Encounter")])


def test_events_count_only_inside_the_window() -> None:
    evidence = SignalEvidence(
        utilization_events=[
            event("e1", ago(100)),
            event("e2", ago(101)),
            event("e3", None),
            event("e4", ago(-1)),
            event("e5", ago(5), kind="crash_as_driver"),
        ]
    )
    found = evaluate_signal(events_signal(), evidence, AS_OF)
    assert (found.present, found.count) == (False, 1)
    assert found.reason == "1 found within 100 days; 2 required."
    assert found.references == []


def test_enough_events_make_the_signal_present() -> None:
    evidence = SignalEvidence(utilization_events=[event("e1", ago(1)), event("e2", ago(100))])
    found = evaluate_signal(events_signal(), evidence, AS_OF)
    assert (found.present, found.count) == (True, 2)
    assert (found.first_date, found.last_date) == (ago(100), ago(1))
    assert len(found.references) == 2


def test_no_events_at_all() -> None:
    found = evaluate_signal(events_signal(1), SignalEvidence(utilization_events=[]), AS_OF)
    assert (found.present, found.reason) == (False, "Not found in the record.")


def agents_signal() -> SignalDefinition:
    return signal(
        source="distinct_agents",
        value_sets=[],
        drug_class="med.antidepressant",
        min_count=2,
        weight="modifier",
    )


def agent(name: str, first: date, last: date) -> AgentSummary:
    return AgentSummary(
        ingredient=IngredientRef(rxcui=name, name=name),
        first_date=first,
        last_date=last,
        references=[ref(name, "MedicationDispense")],
    )


def test_distinct_agents_count_those_with_exposure_in_the_window() -> None:
    agents = DistinctAgents(
        drug_class="med.antidepressant",
        title="t",
        count=3,
        agents=[
            agent("a", ago(300), ago(100)),
            agent("b", ago(50), ago(10)),
            agent("c", ago(300), ago(101)),
        ],
    )
    other = DistinctAgents(drug_class="med.other", title="t", count=0, agents=[])
    found = evaluate_signal(agents_signal(), SignalEvidence(distinct_agents=[other, agents]), AS_OF)
    assert (found.present, found.count) == (True, 2)
    assert [r.id for r in found.references] == ["a", "b"]


def test_too_few_distinct_agents() -> None:
    agents = DistinctAgents(
        drug_class="med.antidepressant", title="t", count=1, agents=[agent("a", ago(3), ago(1))]
    )
    found = evaluate_signal(agents_signal(), SignalEvidence(distinct_agents=[agents]), AS_OF)
    assert (found.present, found.count) == (False, 1)
