"""The scorer slot (ADR 0003): where a statistical model could later contribute a score.

Version 1.0 ships ``RulesOnlyScorer``, which gives no score. A scorer's identity and version
flow into outputs and audit records. A score is reported only: in this version it never
changes the recommendation, and a scorer that fails gives no score and is marked failed,
so the assessment is the same as without it. The engine works with no scorer at all.

``DummyScorer`` (Phase 8) proves the slot. It is not a model, is never on by default and is
switched on only by ``ADHD_MCP_SCORER=dummy``.
"""

import logging
from collections.abc import Callable, Mapping, Sequence
from typing import Protocol

from adhd_mcp.models.assessment import ScorerRef, SignalFinding

_log = logging.getLogger(__name__)


class Scorer(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def version(self) -> str: ...

    def score(self, findings: Sequence[SignalFinding]) -> float | None: ...


class RulesOnlyScorer:
    """The 1.0 scorer: the ruleset alone decides; no statistical score is produced."""

    id = "rules-only"
    version = "1.0.0"

    def score(self, findings: Sequence[SignalFinding]) -> float | None:
        return None


class DummyScorer:
    """Not a model. A placeholder that proves the scorer slot: it always gives 0.0, which
    carries no information about the patient. For testing the plumbing only."""

    id = "dummy-not-a-model"
    version = "0.0.1"

    def score(self, findings: Sequence[SignalFinding]) -> float | None:
        return 0.0


#: The scorers ``ADHD_MCP_SCORER`` can name.
SCORERS: Mapping[str, Callable[[], Scorer]] = {
    "rules-only": RulesOnlyScorer,
    "dummy": DummyScorer,
}


def run_scorer(scorer: Scorer, findings: Sequence[SignalFinding]) -> ScorerRef:
    """The scorer's reference with its score; a failure gives no score and ``failed``.
    Only the scorer's identity and the exception type are logged, never the findings."""
    try:
        score = scorer.score(findings)
    except Exception as exc:  # any scorer failure must leave the assessment unchanged
        _log.warning("scorer %s %s failed: %s", scorer.id, scorer.version, type(exc).__name__)
        return ScorerRef(id=scorer.id, version=scorer.version, score=None, failed=True)
    return ScorerRef(id=scorer.id, version=scorer.version, score=score)
