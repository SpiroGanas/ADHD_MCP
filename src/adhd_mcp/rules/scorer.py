"""The scorer slot (ADR 0003): where a statistical model could later contribute a score.

Version 1.0 ships ``RulesOnlyScorer``, which gives no score. A scorer's identity and version
flow into outputs (and, in Phase 6, audit records). A score is reported only: in this
version it never changes the recommendation. The engine works with no scorer at all.
"""

from collections.abc import Sequence
from typing import Protocol

from adhd_mcp.models.assessment import SignalFinding


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
