# ADR 0003: Deterministic rules first, with a scorer slot

- **Status:** Accepted
- **Date:** 2026-11-26
- **Decided by:** Project owner

## Context

A trained model for undiagnosed adult ADHD needs labelled real-world data, chart validation and a screened reference sample, none of which this project has. The research report also recommends that safety gates, exclusions and hard triggers be deterministic and auditable even when a model is present. A clinician must be able to see the basis for every recommendation.

## Decision

Version 1.0 decides with deterministic rules held as versioned data. The rules engine defines a scorer interface so a statistical model can contribute later. No model is trained in the current plan.

## Alternatives considered

| Option | Why not |
|---|---|
| Rules only, no model interface | Adding a model later would require reworking outputs and audit records |
| Train a model now | No suitable data; results would be unvalidated and misleading |
| Let the language model weigh the evidence | Not reproducible, not auditable, and contrary to ADR 0002 |

## Consequences

- The same evidence and ruleset always give the same output, which makes golden tests possible.
- Rulesets are immutable once released; every clinical change is a new version with its own tests and rule card.
- The starting rule is a heuristic from the literature, not a validated rule, and every output and document must say so.
- The scorer interface must be proven with a dummy scorer (Phase 8) so it does not rot unused.
