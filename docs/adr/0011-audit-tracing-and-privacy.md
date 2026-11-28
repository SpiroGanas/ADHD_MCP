# ADR 0011: Audit records, trace context and the sensitive-data policy

- **Status:** Accepted
- **Date:** 2026-11-27
- **Decided by:** project owner (default policy "cite existence and date only", 2026-11-27); design by the Claude Code agent

## Context

Phase 6 requires one audit record per tool call with no clinical values (standing invariant 5), trace context carried from the MCP request to the FHIR server, and a configurable policy for specially protected data (38 U.S.C. 7332, 42 CFR Part 2): allow, cite existence and date only, or withhold, always disclosed in the output.

## Decision

**Audit.** A FastMCP middleware writes exactly one `AuditRecord` per tool call, success or failure: record and trace ids, time from the injected clock, caller (token subject and client id when authenticated, otherwise `local`), tool, server, contract, ruleset and scorer versions, the patient reference, every FHIR resource reference (with version) the call read (above 500 references, their count and a sha256 of the sorted list instead; peer review 01, D1), the recommendation (for an assessment), the error code of a failed call, and the sha256 of the canonical output. Resource references are collected by a port wrapper through a context variable, so tools and assemblers stay unaware of auditing. Sinks implement one method, `write(record)`: an append-only JSON Lines file for development (`ADHD_MCP_AUDIT_FILE`) and an in-memory sink for tests. A FHIR AuditEvent/Provenance sink can implement the same interface later. Retention is the deploying organization's decision; the development file is never rotated or edited by the server.

**Tracing.** The MCP Python SDK carries W3C trace context in a request's `_meta.traceparent`. The audit middleware takes the trace id from a valid `traceparent`, or starts a new one, and the HTTP FHIR adapter sends `traceparent` with that trace id and a new span id on every request. No OpenTelemetry dependency is added; FastMCP's own spans use the same carrier.

**Sensitive data.** `data/privacy.toml` defines protected categories by security label (`meta.security`) and by value set: substance use, HIV, sickle cell disease. A policy maps each category to `allow`, `cite` or `withhold`; the default is `cite` for all three (owner decision). A filtering port applies `withhold` before evidence assembly: withheld resources never reach an assembler, and the output's `privacy` section names the category and the count withheld. Under `cite`, resources still feed the rules, but any coded entry from them is shown as `restricted` with only its references and dates. A site may load its own policy file (`ADHD_MCP_PRIVACY_POLICY`).

Amended after the clinical safety review (2026-11-27):

- **The safety gate reads every record.** It reads through the audited, cached port but not through the privacy filter, so a withhold policy can never hide a self-harm signal (for example a suicidal-ideation code carrying a substance-use security label). The gate's output carries signal names and references only, never codes.
- **Only categories an output can use are named.** A category has a `disclose` flag; HIV and sickle-cell disease are `false` because no output or rule uses them, so naming them (even as a count) would only reveal that such a record exists. A test keeps the flag equal to whether any output family or signal uses the category's value sets.
- **Withheld means withheld.** A resource type that lost records to a withhold policy (in a disclosed category) is reported as `withheld` in data completeness, never as complete.
- **Draft referrals** cite protected signals by reference only; their titles appear in the draft's note only under `allow`.

## Alternatives considered

| Option | Why not |
|---|---|
| Logging calls with Python logging only | Hard to guarantee one record per call and no clinical values; no output hash |
| Redact inside each assembler | Every new assembler would have to remember; a filtering port and one output pass cannot be forgotten |
| Add OpenTelemetry as a direct dependency | Not needed to carry a trace id; avoids a dependency the owner has not approved |

## Consequences

- Every output schema gains a `privacy` section (tool contract change, reviewed snapshots).
- The security label codes used to recognize categories must be verified like any other code before a label-only match is relied on; until then categories are also recognized by verified ICD-10-CM value sets.
- Withholding substance-use data removes two high-weight ADHD signals; the output says so.
