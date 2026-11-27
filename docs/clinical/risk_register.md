# Risk Register

Clinical safety, privacy, security and project risks. Review at the end of every phase and whenever a new risk is found. Add risks; do not delete them. Close them with a note.

**Scales.** Likelihood and impact: Low, Medium, High. Status: Open, Mitigated, Accepted, Closed.

**Last reviewed:** 2026-11-27, end of Phase 6 (with the [threat model](../security/threat_model.md))

## Clinical safety

| ID | Risk | L | I | Mitigation | Phase | Status |
|---|---|---|---|---|---|---|
| C1 | A recommendation is read as a diagnosis by a clinician, an AI assistant or a patient | M | H | Fixed wording; not-a-diagnosis marker in the schema; output wording guard test; intended-use notice in every result; model-in-the-loop evaluation. *Phase 1-2:* `is_diagnosis` is `Literal[False]`; the guard (data in `wording.toml`) covers several conditions and suicide-risk statements and runs on every tool's output and description | 1, 5, 7 | Open |
| C2 | An ADHD referral distracts from or displaces a self-harm concern | M | H | Safety gate always runs and is presented first; ADHD recommendation withheld while the gate is positive. *Phase 3:* `check_safety_gate` built; the model only allows "address safety gate first" with a positive gate (property-tested, invariant 2); the tool description says to call it first | 3, 5 | Open |
| C3 | A "clear" safety gate is read as "no suicide risk" | M | H | Output states the gate reflects recorded signals only; lists what was checked; negative PHQ-9 item 9 never clears alone. *Phase 3:* every check is listed with its outcome; plain "clear" only when every check ran on complete data, otherwise `clear_limited_data`; the evidence notice says results are "not a risk assessment"; guidance text never states a risk level. Today the LOINC checks are not performed, so no gate is plain "clear" | 3 | Open |
| C4 | A rule uses a wrong or outdated code or cutoff | H | M | Verification backlog; strict loader refuses unverified entries; sources cited per value set. *Phase 1-2:* strict loader built and tested; ICD-10-CM checked against the FY2026 tabular (redistributed copy, hash not yet compared with CMS) with a committed, reproducible script; seven research values corrected; LOINC and cutoffs still unverified and refused. *Phase 3:* FY2027 tabular from CDC checked; the CDC FY2026 file gives identical results to the redistributed copy. Residual: the human spot-check of `safety.*` sets is waived until release (Phase 7 blocker); LOINC unverified, so LOINC checks are not performed and no cutoff is applied or shown | 1 to 4 | Open |
| C5 | The heuristic flags too many patients, wasting scarce evaluation capacity | M | M | Negative-case tests; threshold sensitivity analysis; rule card states limits | 5, 7 | Open |
| C6 | Women are under-flagged because key signals skew male | H | M | Measure on the designed cohort; document; bring options to the project owner | 7 | Open |
| C7 | ADHD-like presentations from TBI, PTSD or substance use are flagged without context | M | M | Look-alike personas; TBI overlap note routes to neuropsychological evaluation | 5, 7 | Open |
| C8 | An empty or partial record is treated as a clean record | M | H | Data-completeness note in every output; "insufficient data" outcome; fault-injection tests. *Phase 1-2:* normalization reports every skipped resource, including id-less search results; the model forbids a clean or referral result from an unavailable gate. *Phase 3:* the port returns server warnings (ADR 0008); a category with warnings or unreadable resources is `incomplete`; completeness notes in every tool output; the gate is `clear_limited_data` or `data_unavailable` on partial data; `check_existing_care` returns `excluded = null` unless every check ran on complete data; tools do not use `since`. Residual: a site without a code mapping gets "not performed" checks, which a reader may overlook | 3, 7 | Open |
| C9 | Synthetic evaluation results are presented as evidence of accuracy | M | H | Required limitation text in every report and in the README | 7 | Open |
| C10 | The tool is used with real patients before validation | L | H | Intended-use statement; README notice; deployment guide lists required governance | 7, 8 | Open |

## Privacy

| ID | Risk | L | I | Mitigation | Phase | Status |
|---|---|---|---|---|---|---|
| P1 | Real patient data is committed to the repository | L | H | Synthetic-only rule; contributor guide; CI checks. *Phase 1-2:* CI guard requires the HTEST tag, synthetic identifiers and family name on every Patient and blocks SSN-shaped numbers; the persona loader writes only to loopback hosts | 1 | Mitigated |
| P2 | Clinical content leaks into logs, audit records or error messages | M | H | References and hashes only; canary-value test. *Phase 6:* audit records hold references, versions, outcome codes and an output hash; a canary persona (free text, values, name, codes) is run through every tool, successful and failed, and never appears in the audit file or in any log record (threat T8) | 6 | Mitigated |
| P3 | Specially protected data (substance use and similar) is disclosed beyond what is permitted | M | H | Configurable sensitive-data policy; disclosure of withheld categories; legal review before real use. *Phase 6:* substance use, HIV and sickle-cell categories by verified ICD-10-CM value sets and HL7 security labels; default "cite" shows references, dates and the signal or family a record belongs to, never its code; "withhold" removes records before evidence assembly (never from the safety gate) and marks the category `withheld`; HIV and sickle-cell categories are never named, as no output uses them; every output has a `privacy` section (ADR 0011, amended after the safety review). Residual: legal review of the default and of label usage at a real site (Phase 8) | 6, 8 | Open |
| P5 | The development audit file can be edited or deleted by anyone with file access | M | M | The server only appends; tamper evidence and retention belong to the site's audit store (FHIR AuditEvent sink, Phase 8). Accepted for synthetic development | 6, 8 | Accepted |
| P4 | Clinical content is sent to a language model outside the authorized boundary | M | H | Deployment guide; the server itself calls no external model in version 1.0 | 6, 8 | Open |

## Security

| ID | Risk | L | I | Mitigation | Phase | Status |
|---|---|---|---|---|---|---|
| S1 | Prompt injection through text in FHIR records or tool descriptions | M | H | Record text treated as data and delimited; injection twin-persona test; contract snapshots pin descriptions. *Phase 6:* a poisoned twin of three personas (text in every free-text field) gives byte-identical output from every tool; prompts carry only a validated patient id. *Phase 2:* records drop free text, but coding `display` strings from the record are kept and must be treated as untrusted and never logged. *Phase 3:* no tool output carries a record's display text: problem list labels come from value sets, screening answer labels from instrument data, instrument code labels are omitted; record status and server issue codes are restricted to token patterns | 5, 6 | Open |
| S2 | A caller's token is forwarded to the FHIR server (confused deputy) | L | H | Server uses its own credentials; test asserts no passthrough. *Phase 6:* SMART backend services with the server's own key; an HTTP test checks the caller's token never appears in FHIR requests (ADR 0012) | 6 | Mitigated |
| S3 | An unauthenticated or over-scoped caller reads patient data | M | H | OAuth with audience checks and per-tool scopes; rejection tests. *Phase 6:* missing, malformed, expired, wrong-audience, wrong-issuer and wrong-key tokens get 401; insufficient scope is refused; HTTP will not start without auth except on 127.0.0.1 | 6 | Mitigated |
| S4 | A tool is changed to write to the record | L | H | Port has no write operation; test asserts no write requests; ADR 0002. *Phase 2:* port has only `read_patient` and `search`; every request in the shared suite is a GET; structural tests block write methods and HTTP write calls in `src/`; next links are pinned to the configured origin and base path | 2 | Mitigated |
| S5 | Secrets committed or printed | L | H | Secret scanning in CI; configuration validation that never echoes secrets. *Phase 1:* gitleaks runs on every pull request. *Phase 6:* configuration errors name variables only (tested); keys are read from files | 1, 6 | Mitigated |
| S6 | Denial of service through many expensive calls | M | M | Per-request cache, timeouts, bounded retries and paging; rate limiting left to the hosting gateway (threat T12). Accepted for 1.0 | 6, 8 | Accepted |

## Project

| ID | Risk | L | I | Mitigation | Phase | Status |
|---|---|---|---|---|---|---|
| J1 | MCP specification or FastMCP changes break the design | M | M | Pinned versions; ADRs; check documentation at the start of each phase | all | Open |
| J2 | No clinician is available to review clinical content | M | H | Open question 1 in status.md; rule cards mark review status | 3 | Open |
| J3 | An AI agent loses context between sessions and repeats or contradicts earlier work | M | M | status.md kept current; ADRs; `/resume` command | all | Open |
| J4 | Scope grows toward diagnosis, writes or patient-facing features | M | H | Hard rules in CLAUDE.md; ask before departing from the plan | all | Open |
| J5 | Lighthouse sandbox access is delayed or its data is too thin | M | L | Apply during Phase 6; recorded responses for tests | 8 | Open |
