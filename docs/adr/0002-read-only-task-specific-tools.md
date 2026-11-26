# ADR 0002: Read-only, task-specific tools

- **Status:** Accepted
- **Date:** 2026-11-26
- **Decided by:** Project owner, from the research report

## Context

Benchmarks cited in the research report (Part 3) show language models navigating raw FHIR unreliably: the best model completed about 70% of tasks on a virtual EHR, and errors came mostly from wrong tool arguments and misread results. Generic write tools invite unsafe changes to a record.

## Decision

Expose only purpose-built, read-only tools that return pre-assembled, evidence-linked summaries. The server performs all FHIR queries, joins and rule evaluation. No tool writes to a FHIR server; `draft_referral_proposal` returns a draft and stores nothing.

## Alternatives considered

| Option | Why not |
|---|---|
| Generic FHIR search, read and write tools | The model would decide what to query and how to interpret it; unsafe and not auditable |
| Read-only generic search plus task tools | Generic search still lets the model bypass the safety gate and the privacy filter |

## Consequences

- The FHIR port has no write operation, and a test asserts that no write request is ever issued.
- Each new clinical question needs a new tool or a tool change, reviewed as a contract change.
- Tool descriptions and output schemas are part of the safety design and are covered by contract snapshots.
