"""The scorer slot (ADR 0003) with the dummy scorer of Phase 8, item 6: a scorer's identity
reaches the output, its score is reported only, and a failing scorer changes nothing."""

from collections.abc import Sequence

from adhd_mcp.models.assessment import SignalFinding
from adhd_mcp.rules.scorer import SCORERS, DummyScorer, RulesOnlyScorer, run_scorer


class BrokenScorer:
    id = "broken"
    version = "0.0.0"

    def score(self, findings: Sequence[SignalFinding]) -> float | None:
        raise RuntimeError("model unavailable")


def test_the_dummy_scorer_is_labelled_as_not_a_model() -> None:
    dummy = DummyScorer()
    assert dummy.id == "dummy-not-a-model"
    assert dummy.version == "0.0.1"
    assert "not a model" in (DummyScorer.__doc__ or "").lower()


def test_the_dummy_score_is_a_constant_that_carries_no_information() -> None:
    assert DummyScorer().score([]) == 0.0


def test_the_scorers_that_can_be_configured() -> None:
    assert set(SCORERS) == {"rules-only", "dummy"}
    assert isinstance(SCORERS["rules-only"](), RulesOnlyScorer)
    assert isinstance(SCORERS["dummy"](), DummyScorer)


def test_a_scorer_reference_carries_identity_version_and_score() -> None:
    ref = run_scorer(DummyScorer(), [])
    assert (ref.id, ref.version, ref.score, ref.failed) == (
        "dummy-not-a-model",
        "0.0.1",
        0.0,
        False,
    )


def test_a_failing_scorer_gives_no_score_and_says_so() -> None:
    ref = run_scorer(BrokenScorer(), [])
    assert (ref.id, ref.version, ref.score, ref.failed) == ("broken", "0.0.0", None, True)
