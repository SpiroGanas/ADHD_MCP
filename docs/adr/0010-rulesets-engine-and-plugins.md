# ADR 0010: Rulesets as data, a condition-independent engine, and condition plugins

- **Status:** Accepted
- **Date:** 2026-11-27
- **Decided by:** project owner (ruleset defaults approved 2026-11-27); format by the Claude Code agent

## Context

Phase 5 needs a ruleset a clinician can check line by line, an engine that knows nothing about ADHD (ADR 0005), a slot for a statistical scorer (ADR 0003), and a guarantee that a released ruleset cannot change silently.

## Decision

- **Signal catalog** (`data/adhd/signal_catalog.toml`): one entry per signal with weight class (`high`, `modifier`, or `note`, which never counts), source kind (`condition`, `psychosocial`, `events`, `distinct_agents`), its definition (value sets, domain, event kind or drug class, minimum count), window in days before the as-of date, supplying tool, protected category and evidence. Strict loading refuses a signal on any unverified code.
- **Ruleset** (`data/adhd/ruleset.toml`): id, version, status (`draft` or `released`), effective date, the catalog id and version it reads, exclusions, citations and rules. A rule is `min_high` distinct high-weight signals and `min_modifiers` distinct modifiers; the ruleset recommends when any rule fires. `validated` is always false. A released ruleset loads only if its sha256 is pinned in `data/released_rulesets.toml`.
- **Evaluation** (`rules/signals.py`): generic per source kind. A condition is current from its first date until its last record if resolved, otherwise open; it counts if that interval overlaps the window. Undated conditions do not count. Events and drug agents count when any part falls in the window.
- **Engine** (`rules/engine.py`): pure and deterministic; returns every rule with the signals it counted.
- **Scorer slot** (`rules/scorer.py`): a `Scorer` protocol; 1.0 ships `RulesOnlyScorer` (no score). A score is reported only and never changes the recommendation in this version.
- **Condition plugins** (`conditions/`): a plugin supplies catalog, ruleset, wording, notes for note signals, exclusions and scorer. The orchestration (`orchestration/assess.py`) runs the safety gate, exclusions and the four signal-supplying assemblers through one request-scoped cached port, then applies a fixed precedence: positive gate, unavailable gate, already in care, rule fired, insufficient data, no recommendation.

## Alternatives considered

| Option | Why not |
|---|---|
| Rules as Python code | Harder for a clinician to review; versioning and immutability would rely on code review alone |
| A general rule language (for example CQL) | Far more than two threshold rules need; adds a dependency and a learning curve |
| Point scores per signal | The research gives a combination heuristic, not weights; scores would imply precision the evidence lacks |

## Consequences

- Changing a threshold or window is a data change with a new version; a test keeps the reported active ruleset equal to the loaded one.
- Signals rest only on what the evidence tools return, so assessment and tools agree by construction.
- Releasing 1.0.0 needs the owner's approval of the rule card, then status `released` and a pinned hash.
