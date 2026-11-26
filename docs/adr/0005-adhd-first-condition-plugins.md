# ADR 0005: ADHD first, conditions as plugins

- **Status:** Accepted
- **Date:** 2026-11-26
- **Decided by:** Project owner

## Context

The research report covers fourteen risk domains. ADHD has the strongest case for a first target: it is common, under-diagnosed, and treatment is associated with lower self-harm. Autism and other conditions share many evidence sources but have thinner evidence.

## Decision

Build ADHD end to end first. Structure the rules engine so that a condition is a plugin supplying its signal catalog, ruleset, exclusions and next-step text. The engine and evidence tools contain nothing specific to ADHD.

## Alternatives considered

| Option | Why not |
|---|---|
| ADHD only, no extensibility | A second condition would need a rewrite of the engine |
| Several conditions at once | Too much for one developer; dilutes testing depth on the first condition |

## Consequences

- A test-only dummy condition proves the plugin interface in Phase 5; a disabled second-condition stub proves it again in Phase 8.
- Tool and repository names keep "ADHD" for now. Renaming is a later decision if a second condition ships.
- Shared evidence tools must stay neutral: they report signals, and only a condition plugin interprets them.
