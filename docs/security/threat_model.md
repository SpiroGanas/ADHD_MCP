# Threat Model

Phase 6 review of ADHD_MCP version 0.1.0 (tool contract 0.3.0), 2026-11-27, by the Claude Code agent. Every threat maps to a test or to a recorded acceptance in the [risk register](../clinical/risk_register.md). Review again before release (Phase 7) and before any real deployment (Phase 8).

## System and trust boundaries

```
 MCP client (clinician's AI assistant)            untrusted input: tool arguments, _meta
        |  stdio (local, same user)  or  HTTPS + OAuth bearer token
        v
 ADHD_MCP server  -- audit sink (append-only file) --  logs (no clinical content)
        |  GET only; SMART backend-services token of the server itself
        v
 FHIR server                                       untrusted input: every resource's content
```

Assets: patient data read from FHIR (including specially protected categories); the server's SMART private key; callers' tokens; the integrity of recommendations (a wrong or manipulated result could misdirect care); the audit trail.

## Threats

| # | Threat | Mitigation | Evidence |
|---|---|---|---|
| T1 | **Prompt injection through FHIR content**: text in a record (display, `code.text`, notes, narrative, names) instructs the assistant | Normalization keeps no free text; outputs carry labels only from value sets and instrument data; prompts carry only a validated patient id | `tests/tools/test_injection.py` (poisoned twin gives identical output; text never appears); `tests/unit/fhir/test_normalize.py` |
| T2 | **Prompt injection through tool descriptions or prompts** | Descriptions, prompts and resources are fixed text pinned by contract snapshots and scanned for diagnostic language | `tests/contract/`, `tests/tools/test_standing_invariants.py`, `tests/tools/test_resources_and_prompts.py` |
| T3 | **Malicious tool arguments** (path traversal in patient id, future dates, unknown condition, injected text in prompt arguments) | Patient id must match the FHIR id pattern before it reaches a URL, a prompt or the audit trail; dates validated; condition must be registered | `tests/tools/test_shared_tool_behavior.py`, `test_assess_referral_need.py`, `test_resources_and_prompts.py`, `test_audit.py` |
| T4 | **Confused deputy**: a caller's token is forwarded to the FHIR server, or the server acts with the caller's identity | The FHIR adapter has no access to the caller's token; it sends only the server's own SMART token | `tests/tools/test_http_auth.py::test_a_valid_token_reaches_the_tools_and_is_never_forwarded`, `tests/unit/fhir/test_smart.py` |
| T5 | **Unauthenticated or over-scoped access** over HTTP | OAuth 2.1 resource server: signature, issuer, audience and expiry checked; per-tool scopes; HTTP refuses to start without auth unless bound to 127.0.0.1 | `tests/tools/test_http_auth.py`, `tests/unit/test_config.py` |
| T6 | **Token audience confusion** (a token for another service replayed here) | Audience must equal this server's resource URL | `test_http_auth.py` (wrong-audience) |
| T7 | **Writes to the record** | Port has no write method; only GET to FHIR; the one POST (SMART token request) is allowlisted and goes to the token URL only | `tests/unit/fhir/test_read_only.py`, adapter shared suite, `test_smart.py` |
| T8 | **Leakage through logs, audit records or errors** | Audit stores references, hashes and codes of outcome only; tool errors carry fixed codes and no server bodies; FastMCP masks internal errors | `tests/tools/test_audit.py::test_canary_clinical_content_never_reaches_audit_or_logs`, `tests/adapters` (no response bodies in errors) |
| T9 | **Disclosure of specially protected data** | Sensitive-data policy (default cite: codes shown as `restricted`); withhold option; every output discloses what was withheld or restricted | `tests/unit/privacy/test_policy.py` |
| T10 | **Secrets exposure** (SMART key, configuration) | Keys read from files named by variables; configuration errors name variables, never values; gitleaks in CI | `tests/unit/test_config.py` |
| T11 | **Malicious or compromised FHIR server** (huge or endless pages, redirects elsewhere, malformed resources) | Paging capped and pinned to the configured origin; redirects not followed; malformed resources reported as skipped, never fatal | `tests/adapters/test_http_adapter.py`, `tests/unit/fhir/test_normalize.py` |
| T12 | **Denial of service** (many expensive assessments) | One cached port per assessment (no repeated queries); request timeouts and bounded retries; paging cap. Rate limiting is left to the hosting gateway | `test_assess_referral_need.py::test_one_assessment_issues_no_duplicate_fhir_queries`; **accepted** for 1.0 (risk S6) |
| T13 | **Tampering with the audit trail** | The server only appends; it never rewrites or truncates. Tamper evidence (hash chaining, write-once storage) belongs to the deploying site's audit store | `test_audit.py::test_the_jsonl_sink_appends`; **accepted** for development (risk P5) |
| T14 | **Manipulated clinical content** (ruleset or value set changed silently) | Rulesets and catalogs are versioned data; released rulesets are hash-pinned; strict loading refuses unverified codes | `tests/unit/rules/test_ruleset.py`, `test_signal_catalog.py` |
| T15 | **Trace context abuse** (a forged `traceparent`) | Only a well-formed W3C value is accepted, and only its trace id is used, as a correlation id; it grants nothing | `test_audit.py::test_the_trace_id_comes_from_the_request_traceparent` |

## Out of scope here

Network transport security (TLS termination) and rate limiting belong to the hosting environment; the deployment guide (Phase 8) must require them. Model-side risks (an assistant paraphrasing a suggestion as a diagnosis) are covered by the wording guard and the Phase 7 model-in-the-loop evaluation.
