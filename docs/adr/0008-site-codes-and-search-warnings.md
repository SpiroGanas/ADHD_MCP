# ADR 0008: Per-site local code mapping, and search warnings from the FHIR port

- **Status:** Accepted
- **Date:** 2026-11-27
- **Decided by:** Project owner (decisions of 2026-11-27, open questions 2, 13 and the local-codes question); written by the Claude Code agent

## Context

Phase 3 tools must recognise things that have no standard code: psychiatric inpatient and residential encounters, high-risk-for-suicide flags, ADHD referrals, evaluations and care plans, and which Questionnaire is which screening instrument. Every health system codes these locally. Separately, a FHIR server can return OperationOutcome issues with a search (truncated, suppressed or withheld results); the port returned only resources, so outputs could not disclose incomplete data (risk C8).

## Decision

1. Local codes live in a per-site data file, `src/adhd_mcp/data/site_codes/<site>.toml`, mapping named concepts to code entries (value-set entry format, strict verification) and questionnaire URLs to instrument items. A concept a site does not map matches nothing, and the dependent check reports "not performed". Only the project's synthetic site is shipped. The server uses it for fixture data; for a FHIR server it uses no mapping unless `ADHD_MCP_SITE_CODES` names one. Outputs report the mapping in `versions.site_codes`.
2. `FhirReadPort.search` returns `SearchResult(resources, warnings)`. Warnings keep only the severity (warning or worse) and the FHIR issue-type token; diagnostic text is dropped. Tools mark the category `incomplete`, and so do resources that could not be read.

## Alternatives considered

| Option | Why not |
|---|---|
| Hard-code local codes in the assemblers | Clinical and site knowledge would live in code; every site would need a code change |
| Standard codes only (no mapping) | No standard exists for these concepts; the discharge and flag checks could never run |
| Default to the synthetic mapping everywhere | Against a real server the checks would silently find nothing instead of reporting "not performed" |
| Keep `search` returning a list and add a second method for warnings | Callers could ignore warnings; one return type makes them hard to miss |

## Consequences

- Onboarding a real site (Phase 8) includes writing and verifying its site code file.
- Every port implementation must return warnings; the shared adapter suite checks it.
- A server that over-reports warnings makes results `clear_limited_data` or `excluded = null` more often; that is the safe direction.
