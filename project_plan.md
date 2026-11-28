# Project Plan

A phased plan for building ADHD_MCP: a Python and FastMCP server that reads FHIR data and recommends whether a clinician should consider referring a patient for formal adult ADHD screening.

Each phase is about one month of work for one developer. This document contains no code. It describes what to build, in what order, and which tests come first.

Related documents: [architecture](docs/architecture.md), [decision records](docs/adr/README.md), [clinical documents](docs/clinical/), [research report](research/veteran_self_harm_risk_screening.md), [current status](status.md).

## Scope

Decided with the project owner on 2026-11-26.

| Question | Decision |
|---|---|
| Conditions | ADHD first. The design lets other conditions be added later as plugins; none is built in this plan beyond a proof stub in Phase 8 |
| Decision logic | Deterministic, versioned rules. A scorer interface leaves a slot for a statistical model later; no model is trained in this plan |
| Data | Synthetic FHIR R4 for all development and testing. A FHIR abstraction layer and SMART on FHIR authentication keep VA Lighthouse and Oracle Health connectable in Phase 8 |
| Stack | Python and FastMCP |

**In scope:** the tools in the architecture document (nine planned; ten built, with `get_server_info`), MCP resources and prompts, the rules engine, audit logging, authentication, a synthetic evaluation suite, and release 1.0.

**Out of scope for this plan:** note text extraction (`find_note_evidence`), model training, CDS Hooks, production deployment inside a health system, any clinical validation or trial, and any patient-facing feature. These are listed under [Future work](#future-work).

## Test-driven development rules

These apply to every phase.

**The cycle.** Red, green, refactor. Write one failing test that states a behavior, see it fail for the expected reason, write the least code that passes, then refactor with the tests green. Commit at green.

**Test layers.**

| Layer | What it checks | Rules |
|---|---|---|
| Unit | One module: a normalizer, an evidence assembler, a rule | No network, no real clock, no file system outside fixtures. The bulk of all tests |
| Contract | Each MCP tool's name, description, input schema and output schema | A stored snapshot per tool. A changed snapshot is a deliberate, reviewed act because clients and prompts depend on it |
| Tool | A tool called through FastMCP's in-memory client against fixture data | Proves the wrapper, validation and error handling |
| Integration | The server against a local FHIR server loaded with synthetic bundles | Marked separately; run in CI but not required for a fast local loop |
| Golden | Each synthetic persona's full expected recommendation | The expected output is written by hand from the rule card before the code exists |
| Property | Invariants over generated inputs | For example: a positive safety gate is never absent from an output; an excluded patient never receives a recommendation |
| Evaluation | A language model using the tools on scripted tasks | Phase 7; reported, not gating at first |

**Personas are the specification.** Each rule is first written down as one or more synthetic patients with a stated expected outcome. The persona catalog (Phase 2) grows with every rule. Every rule needs at least one persona that triggers it, one that narrowly misses, and one that is excluded.

**Negative cases carry equal weight.** "No recommendation" outcomes are tested as carefully as recommendations. A false flag costs a clinician's time and a patient's trust.

**Standing invariants.** These are written as tests in the phase where they first apply and must never be removed:

1. No output states or implies a diagnosis.
2. No recommendation is returned without a safety gate result.
3. Every signal in an output cites at least one FHIR resource ID.
4. No tool performs a write against the FHIR server.
5. No log record contains clinical values or free text.
6. An unverified code or cutoff cannot be loaded into an active ruleset.

**Other rules.**

- A bug fix starts with a test that reproduces the bug.
- Tests are never skipped, weakened or deleted to get a green run.
- Coverage target: 90% of lines overall and 100% of branches in the rules and safety gate modules. Coverage is a floor, not the goal.
- Time is always injected. Rules about "within 90 days" are tested at the boundary day, one day inside and one day outside.
- All test data is synthetic and obviously so.

## Definition of done

A work item is done when:

- its tests were written first and now pass, with lint and type checks clean
- contract snapshots are updated deliberately if a tool contract changed
- documentation is updated: architecture, rule card, an ADR if a costly decision was made
- [status.md](status.md) is updated
- a pull request is open, CI is green, and review comments are resolved

A phase is done when its exit criteria are met and status.md says so.

## Phase overview

| Phase | Theme | Main result |
|---|---|---|
| 1 | Foundations and walking skeleton | A FastMCP server with one trivial tool, tested end to end in CI |
| 2 | FHIR access layer and synthetic patients | Normalized, typed access to patient data from fixtures or a FHIR server; a persona catalog |
| 3 | Evidence tools I | `check_safety_gate`, `get_mh_problem_list`, `get_screening_history`, `check_existing_care` |
| 4 | Evidence tools II | `get_medication_timeline`, `get_utilization_summary`, `get_psychosocial_context` |
| 5 | Rules engine and recommendation | `assess_referral_need`, `draft_referral_proposal`, resources, prompts |
| 6 | Audit, privacy and security | Audit trail, sensitive-data filter, OAuth, HTTP transport, threat model |
| 7 | Evaluation, hardening and release | Synthetic evaluation report, model-in-the-loop evaluation, version 1.0 |
| 8 | VA readiness and extensibility | Lighthouse sandbox adapter, second-condition stub, model slot proven |

Phases 3 and 4 can swap order. Phase 6 work on authentication can move earlier if a real FHIR server with authentication is needed sooner.

---

## Phase 1: Foundations and walking skeleton

**Goal.** A developer or agent can clone the repository, run one command, and see tests pass against a real FastMCP server that does almost nothing. Every later phase adds behavior to a working, tested pipeline.

### Work items

1. **Tooling decisions.** Choose and pin the Python version, FastMCP version, package and environment manager, test runner, linter, formatter and type checker. Check current FastMCP and MCP specification documentation before choosing; the research notes that the MCP specification changed substantially in 2026. Record the choices in an ADR and the commands in CLAUDE.md and README.
2. **Repository layout.** Create the package and test layout described in the architecture document. Empty modules are acceptable only where a test already needs them.
3. **Continuous integration.** A GitHub Actions workflow that runs tests, lint, type check and coverage on every pull request. Add a secret scan and a check that blocks files resembling real patient data.
4. **Walking skeleton.** A server exposing a single `get_server_info` tool that returns the server name, version, ruleset version (a placeholder for now) and the intended-use statement.
5. **Test harness.** Shared test fixtures: an in-memory MCP client connected to the server, a fixed clock, and the contract snapshot mechanism.
6. **Domain vocabulary.** Define, as typed models, the shared concepts every later phase uses: an evidence item (signal name, resource references, date, weight class), a safety gate result, a recommendation. Fields only, no logic. Review these against the output example in the research report, Part 3.
7. **Output wording guard.** A reusable test helper that scans any tool output for diagnostic language, driven by a list of forbidden phrasings kept as data.
8. **Verification sprint, part 1.** Work through the highest-priority items in the [verification backlog](docs/clinical/verification_backlog.md): the self-harm ICD-10-CM codes and the LOINC codes for C-SSRS and PHQ-9, which Phase 3 depends on.

### Tests first

- The server lists exactly the expected tools (contract snapshot).
- `get_server_info` through the in-memory client returns a version and the intended-use text.
- The output wording guard fails on a sample diagnostic sentence and passes on the approved recommendation wording.
- Domain models reject an evidence item with no resource reference.

### Exit criteria

- One documented command installs dependencies; one runs the full check suite; both work on a clean clone.
- CI is green on a pull request and is required for merge.
- The server can be started locally and inspected with an MCP client or inspector tool.
- ADRs exist for the tooling choices. Standing invariants 1 and 3 exist as tests.

### Risks and open questions

- FastMCP's current major version and its support for the latest MCP specification must be confirmed, not assumed.
- Decide whether to use an existing FHIR model library or define narrow internal models (decide at the start of Phase 2; record an ADR).

---

## Phase 2: FHIR access layer and synthetic patients

**Goal.** The rest of the system can ask for "this patient's conditions" or "observations with these codes since this date" and receive normalized, typed records, without knowing whether they came from a file or a FHIR server.

### Work items

1. **FHIR port.** Define the interface the application uses to read data: patient, conditions, observations, questionnaire responses, medication requests, dispenses and statements, encounters, procedures, service requests, care plans, flags. Read operations only; the interface has no write method by design.
2. **Fixture adapter.** Reads FHIR bundles from files. Used by nearly all tests.
3. **HTTP adapter.** Reads from a FHIR R4 server: search with paging, `_lastUpdated` and date filters, retries with backoff, timeouts, and clear errors for missing data versus failed requests. Unauthenticated at this stage; authentication arrives in Phase 6.
4. **Normalization.** Convert raw resources to internal records: one code representation across coding systems, one date representation across FHIR's date variants, status filtering (entered-in-error excluded, refuted conditions excluded), and retained resource ID and version for evidence linking.
5. **Terminology store.** Value sets as versioned data files: a named set of codes with system, version, source citation and a verified flag. A loader that refuses unverified entries in strict mode (standing invariant 6). Support ICD-10-CM prefix matching, since many signals are code families.
6. **Persona catalog.** A documented set of synthetic patients, each a hand-built FHIR bundle with a short narrative and expected outcomes filled in as rules arrive. Start with about ten: a clear ADHD-signal case, a female presentation with depression and anxiety history, a safety-gate case, an already-diagnosed case, a TBI look-alike, a narcolepsy stimulant case, an empty record, a sparse record, a record with conflicting data, and a healthy control.
7. **Bulk synthetic data.** Generate a larger population with a synthetic patient generator for integration and performance tests. Document how to regenerate it; decide whether generated data is committed or built on demand.
8. **Local FHIR server.** A documented, containerized FHIR server for integration tests, with a script to load the personas.
9. **Verification sprint, part 2.** Verify the ICD-10-CM families, LOINC codes and cutoffs needed by Phases 3 and 4.

### Tests first

- Normalization: each FHIR date variant; a condition with ICD-10-CM and SNOMED codings; entered-in-error resources dropped; missing optional fields tolerated.
- Terminology: prefix matching hits `F15.8` for an `F15` family and does not hit `F150`-style false matches; an unverified entry is refused in strict mode.
- Fixture and HTTP adapters pass the same shared behavioral test suite, so they are interchangeable.
- HTTP adapter against a stubbed server: paging followed to the end, retry on a transient failure, a clear error on a permanent one, and no write request ever issued (standing invariant 4).
- Each persona bundle is valid FHIR R4 and contains only synthetic identifiers.

### Exit criteria

- Both adapters pass the shared suite. Integration tests run against the local FHIR server in CI.
- The persona catalog is documented and loadable in one step.
- An ADR records the FHIR modeling choice.

### Risks and open questions

- Synthetic generators produce little realistic mental health or screening-instrument data. Hand-built personas carry the clinical meaning; generated data is for volume only.
- Real servers represent screening instruments inconsistently (panel observations, questionnaire responses, or local codes). Design normalization to accept both panel and questionnaire forms now.

---

## Phase 3: Evidence tools I

**Goal.** The four tools that the safety gate and exclusions depend on, each returning structured, evidence-linked output.

Each tool is built the same way: write the persona expectations, then the unit tests for the evidence assembler, then the assembler, then the contract snapshot and tool-level tests, then the thin FastMCP wrapper.

### Work items

1. **`check_safety_gate`.** Detects self-harm signals: suicidal ideation, attempt and self-harm codes including intentional and undetermined poisoning; history of suicidal behavior; PHQ-9 item 9 at or above 1; positive C-SSRS screen or moderate or high risk level; psychiatric inpatient or residential discharge within 90 days (highest priority) or 365 days; existing high-risk flags where present. Returns gate status, the list of checks performed, and evidence. A positive gate carries fixed guidance text directing the clinician to suicide risk evaluation and lethal-means counseling. A negative PHQ-9 item 9 never clears the gate on its own.
2. **`get_mh_problem_list`.** Mental health and related diagnoses with normalized codes, first-recorded dates, clinical status and onset order. Groups codes into the families the rules use.
3. **`get_screening_history`.** A timeline of instrument scores (PHQ-9, PHQ-2, C-SSRS, AUDIT-C, PC-PTSD-5, ASRS where present) with date, score, the cutoff applied and its source. Reads both observation panels and questionnaire responses.
4. **`check_existing_care`.** Exclusions and de-duplication: an existing ADHD diagnosis, an open or recent ADHD referral or evaluation, relevant care plans. Also reports stimulant treatment for narcolepsy as a separate finding, not an exclusion.
5. **Shared tool behavior.** Common input validation (patient identifier, optional as-of date), a consistent error shape, a "data not available" result distinct from "nothing found", and a data-completeness note in every output so a clinician can tell an empty record from a clean one.
6. **Tool descriptions.** Write each tool's description for a language-model reader: when to use it, what it does not do, that it is read-only, and that results are not a diagnosis.

### Tests first

- Safety gate: every signal type alone triggers it; the 90 and 365 day boundaries, tested on the day, one day inside and one day outside; an undetermined-intent poisoning counts; a negative item 9 with a positive C-SSRS is positive; an empty record returns "clear, with limited data", not plain "clear".
- Problem list: onset order with identical dates; a resolved condition is retained and labeled; duplicate codings across encounters collapse to one entry with all evidence references.
- Screening history: panel form and questionnaire form produce the same timeline; sex-specific AUDIT-C cutoffs; an unknown instrument is reported but not scored.
- Existing care: an ADHD code present means excluded; a referral cancelled long ago does not exclude; narcolepsy with a stimulant is flagged separately.
- Contract snapshots for all four tools. Standing invariant 2 is introduced as a property test.

### Exit criteria

- All four tools are callable through an MCP client against the persona catalog and the local FHIR server.
- Safety gate module has full branch coverage.
- A rule card draft (from the [template](docs/clinical/rule_card_template.md)) documents the safety gate signals with sources.

### Risks and open questions

- How long does a positive safety gate remain "current"? Propose look-back windows per signal and confirm with the project owner; record in the rule card.
- Which encounter types count as psychiatric inpatient or residential differs by server. Keep the mapping in data.

---

## Phase 4: Evidence tools II

**Goal.** The remaining three evidence tools, which supply most of the ADHD-specific signals.

### Work items

1. **`get_medication_timeline`.** Drug-class exposure periods from requests, dispenses and statements: stimulants and non-stimulant ADHD medications, antidepressants with a count of distinct agents, sedative-hypnotics, and others the ADHD rules reference. Handles overlapping fills, gaps and missing days-supply. Drug classes are RxNorm value sets in the terminology store.
2. **`get_utilization_summary`.** Emergency and urgent-care visits for accidental injury, motor-vehicle crash codes, psychiatric admissions and discharges, missed appointments where recorded, and counts per time window (0 to 30, 31 to 180, 181 to 730 days). Includes a measure of overall record volume so later rules can avoid simply rewarding frequent attendance.
3. **`get_psychosocial_context`.** Housing, legal, educational and occupational Z-codes, relevant social-history observations, and, where present, military context such as separation date. Reports absent data as absent.
4. **Signal catalog.** A single documented, versioned list of every ADHD referral signal: name, weight class (high or modifier), the value sets and windows that define it, which tool supplies it, and its evidence source in the research report. This catalog is the input contract for Phase 5 and the core of the rule card.
5. **Performance pass.** Tools called together should not repeat FHIR queries. Add per-request caching inside the FHIR access layer and measure against the bulk synthetic population.
6. **Verification sprint, part 3.** Verify the remaining codes and cutoffs the ADHD rules will use. Anything still unverified is excluded from the Phase 5 ruleset and listed in status.md.

### Tests first

- Medications: overlapping fills merge into one exposure; a gap splits it; a request never dispensed is reported as prescribed-not-filled; the distinct antidepressant count ignores dose changes and brand or generic variants of one ingredient.
- Utilization: an injury visit is counted once when coded in several places; window boundaries; a crash as passenger is not counted as a crash as driver.
- Psychosocial: a missing separation date yields "unknown", not a default.
- Signal catalog: every entry references value sets that exist and a tool that supplies it; no entry depends on an unverified code.
- Performance: one full assessment issues no duplicate FHIR queries.

### Exit criteria

- Seven evidence tools pass contract, tool and integration tests.
- The signal catalog is complete, reviewed by the project owner, and each signal has at least one persona.

### Risks and open questions

- Mapping medications to classes needs a maintained source of RxNorm ingredients. Decide between a hand-curated list and a terminology service; record an ADR.
- Injury, crash and legal signals skew male (research report, ADHD section). Record this in the rule card now; Phase 7 measures it.

---

## Phase 5: Rules engine and the referral recommendation

**Goal.** The tool that answers the project's question, with a result a clinician can check line by line.

### Work items

1. **Ruleset format.** Rules as versioned data: identifier, version, effective date, the signals and windows used, weight classes, combination logic, exclusions, and citations. A ruleset is immutable once released; a change makes a new version.
2. **Rules engine.** Takes the assembled evidence and a ruleset and returns a decision with a trace: which rules fired, which did not, and why. Pure and deterministic: the same evidence and ruleset always give the same output.
3. **ADHD ruleset 1.0.** The starting heuristic from the research report: recommend when one high-weight signal occurs with two or more modifiers, or when two or more high-weight signal classes occur within about three years. Exclusions from `check_existing_care`. Special handling: possible TBI overlap adds a note suggesting neuropsychological evaluation; narcolepsy stimulant use does not count as a stimulant signal. The exact windows and weights are confirmed with the project owner before coding.
4. **Scorer interface.** A defined slot through which a statistical model could later contribute a score. Version 1.0 ships a rules-only scorer. The interface carries a model identifier and version into the output and audit record, and the engine works with no scorer present.
5. **Condition plugin interface.** ADHD is registered as the first condition: its ruleset, signal catalog, next-step text and exclusions. The engine itself contains nothing ADHD-specific.
6. **`assess_referral_need`.** Orchestrates safety gate, exclusions, evidence assembly and rules. Output fields: recommendation (one of a fixed set), an explicit "is not a diagnosis" marker, condition to screen for, suggested next step, safety gate result, basis (evidence items), exclusions checked, data-completeness note, and ruleset and server versions. A positive safety gate is always presented first and suppresses the ADHD recommendation until addressed, while still reporting what was found.
7. **`draft_referral_proposal`.** Returns a draft referral shaped as a FHIR service request with proposal intent, populated from an assessment. It is returned to the caller only and stored nowhere.
8. **MCP resources.** Read-only, versioned reference material: the active ruleset, the signal catalog, value sets, instrument metadata (names, scoring, cutoffs, codes; no copyrighted item text), and the intended-use statement.
9. **MCP prompts.** A small set of clinician-facing templates: explain this recommendation from its evidence; summarize what was checked and what data was missing.
10. **Rule card.** Complete the [rule card](docs/clinical/rule_card_template.md) for ADHD ruleset 1.0.

### Tests first

- Golden tests: every persona's expected full output, written by hand before the engine exists.
- Rule boundaries: one high-weight signal with one modifier does not recommend; with two it does; two high-weight classes just inside and just outside the window.
- Determinism: repeated runs and shuffled input order give identical output.
- Property tests for standing invariants 1 to 3, plus: an excluded patient never receives a recommendation; a positive safety gate always appears first.
- Trace: every fired rule in the trace corresponds to evidence in the basis, and the reverse.
- Plugin: a dummy test-only condition can be registered and assessed without changing engine code.
- Draft proposal: intent is always proposal; calling the tool issues no FHIR write.
- Prompts and resources: contract snapshots; resource content matches the loaded ruleset version.

### Exit criteria

- `assess_referral_need` returns correct, evidence-linked output for every persona through an MCP client.
- Rules engine has full branch coverage. The rule card is complete and approved by the project owner.
- A demonstration script (documentation, not code) walks through three personas with an MCP client.

### Risks and open questions

- The heuristic is a starting point from the literature, not a validated rule. The rule card and all outputs must say so.
- Should the output include a priority tier? The research suggests ranking against local capacity, which needs population data. Proposal: omit in 1.0 and revisit in Future work.
- Confirm the recommendation vocabulary and the exact clinician-facing wording with the project owner.

---

## Phase 6: Audit, privacy and security

**Goal.** Every call is traceable, protected data is handled deliberately, and the server can run over HTTP with real authentication.

### Work items

1. **Audit record.** One record per tool call: request and trace identifiers, time, caller identity, tool name, server and ruleset versions, input resource IDs with versions, output identifier and recommendation, and a hash of the output. No clinical values or text (standing invariant 5).
2. **Audit sink.** A pluggable destination: local append-only file for development, with an interface suitable for FHIR AuditEvent and Provenance resources later. Document retention expectations.
3. **Tracing.** Propagate trace context from the MCP request through FHIR calls, following the current MCP specification's approach.
4. **Sensitive-data policy.** A filter between the FHIR access layer and the evidence assemblers that applies a configurable policy to specially protected categories (substance use, and others under 38 U.S.C. 7332 and 42 CFR Part 2): allow, cite existence and date only, or withhold. Driven by security labels where present and by code families otherwise. The output always states when a category was withheld.
5. **Authentication as an MCP server.** OAuth 2.1 resource-server behavior over HTTP as the current MCP specification requires: token validation, audience checks, protected-resource metadata, scopes per tool. Use FastMCP's authentication support; confirm what it provides before designing around it.
6. **Authentication as a FHIR client.** SMART on FHIR backend-services credentials for the HTTP adapter. The server uses its own credentials and never forwards a caller's token.
7. **Transport and configuration.** Streamable HTTP transport alongside local stdio. Configuration through environment variables with validation at startup; secrets never in the repository.
8. **Threat model.** A written review covering prompt injection through FHIR content and tool descriptions, confused-deputy risks, data leakage through errors and logs, and denial of service. Each threat maps to a test or an accepted, recorded risk in the [risk register](docs/clinical/risk_register.md).
9. **Input hardening.** Strict validation of every tool input; free text from FHIR records is never interpolated into instructions and is clearly delimited as data where it is returned.

### Tests first

- Audit: every tool call produces exactly one record; a failed call is recorded as failed; a canary clinical value planted in fixtures never appears in any log or audit record.
- Sensitive data: under a "withhold" policy a substance-use signal is absent from the basis and the output says a category was withheld; under "cite only" the reference and date appear with no detail.
- Authentication: missing, expired, wrong-audience and insufficient-scope tokens are each rejected with the correct response; a caller's token is never sent to the FHIR server.
- Injection: a persona whose record contains instruction-like text produces the same recommendation as its clean twin.
- Configuration: the server refuses to start with missing or malformed settings and does not print secrets.

### Exit criteria

- The server runs over HTTP with authentication against the local FHIR server, end to end, in CI.
- The threat model is written, and each threat has a test or a recorded acceptance.
- The risk register is reviewed and current.

### Risks and open questions

- The exact authorization requirements of the current MCP specification were not read directly during research. Read them first.
- The default sensitive-data policy is a product and legal decision. Proposal for discussion: "cite existence and date only" by default.
- How protected data is labeled in VA FHIR is unknown (research gap). Keep the policy configurable by label and by code.

---

## Phase 7: Evaluation, hardening and release 1.0

**Goal.** Know how the rules behave across a synthetic population and how well a language model uses the tools; then ship a documented 1.0.

### Work items

1. **Labelled synthetic cohort.** Extend the persona catalog to a designed cohort of roughly 100 to 200 synthetic patients with intended outcomes, deliberately balanced by sex and age, including look-alikes (TBI, PTSD, bipolar disorder, substance use without ADHD signals) and sparse records.
2. **Evaluation harness.** Runs the cohort and reports: agreement with intended outcomes, which signals drive recommendations, recommendation rate by sex and age band, and sensitivity to each rule threshold. Output is a versioned report tied to a ruleset version.
3. **Sex-balance review.** The research predicts that injury, crash and legal signals under-flag women. Measure it on the cohort, report it in the rule card, and bring options to the project owner (for example, an adjusted modifier set). Any rule change is a new ruleset version with its own tests.
4. **Model-in-the-loop evaluation.** Scripted tasks where a language model uses the server through an MCP client: Does it call the safety gate? Does it report the recommendation faithfully without turning it into a diagnosis? Does it cite evidence? Does it handle missing data honestly? Reported per model; define a pass bar with the project owner.
5. **Tool description tuning.** Revise tool descriptions and prompts based on that evaluation. Each change updates contract snapshots deliberately.
6. **Robustness.** Fault injection in the FHIR layer: timeouts, partial pages, malformed resources. The server must degrade to "data not available" and never to a confident clean result.
7. **Performance.** Latency targets for a full assessment against the local server; measure and fix regressions.
8. **Documentation.** Installation, configuration, client setup for common MCP clients, a tool reference generated from the contracts, the completed rule card, limitations, and a change log.
9. **Release.** Versioning policy for the server, tool contracts and rulesets as three separate version lines; packaging; a tagged 1.0.0 release; a container image if useful.

### Tests first

- The harness on a tiny fixed cohort reproduces a hand-calculated report.
- Fault injection: each fault type produces an explicit incomplete-data result; none produces a recommendation or a "clear" gate from partial data.
- A release check that fails when the rule card, change log or contract snapshots are out of date for the tagged version.

### Exit criteria

- An evaluation report for ADHD ruleset 1.0 is committed, with the sex-balance findings and stated limitations.
- A new user can install, configure and run the server against the sample data by following the README alone.
- Version 1.0.0 is tagged. The README states plainly that the tool is not clinically validated.

### Risks and open questions

- Results on a designed synthetic cohort show that the code matches the intended rules. They say nothing about real-world accuracy. Every report must say this.
- Model-in-the-loop evaluation needs model API access and a budget. Confirm with the project owner.

---

## Phase 8: VA readiness and extensibility

**Goal.** Show that the abstractions hold: a second FHIR back end, a second condition, and a model in the scorer slot, each added without changing the core.

### Work items

1. **VA Lighthouse sandbox adapter.** Connect to the Lighthouse sandbox FHIR APIs with their OAuth flow and synthetic test patients. Document every difference from the generic adapter: supported searches, scopes, resource coverage, rate limits.
2. **Data-shape findings.** Answer the research report's first integration question: whether screening instruments appear as LOINC-coded observations or need mapping from local codes. Add mappings as data. Record findings in the architecture document.
3. **Oracle Health differences.** A desk review of the Oracle Health FHIR R4 API against the FHIR port, listing gaps. Build an adapter only if sandbox access is available.
4. **Sensitive-data policy against real labels.** Check the Phase 6 filter against whatever labeling the sandbox exposes; update the policy configuration and risk register.
5. **Second-condition stub.** Register a minimal second condition (autism is the natural choice from the research) with a small signal catalog and placeholder ruleset marked experimental and disabled by default. Its purpose is to prove the plugin interface, not to ship a second clinical rule.
6. **Model slot proof.** Plug a trivial, clearly labeled dummy scorer into the scorer interface and confirm that its identifier and version flow into outputs and audit records, and that the system behaves identically with it removed.
7. **Deployment guide.** What a health system would need to run this: boundary and hosting assumptions, authentication setup, audit retention, monitoring, and the governance documents required before any clinical use.
8. **Next-stage plan.** A short proposal for what follows, based on [Future work](#future-work) and what this phase revealed.

### Tests first

- The Lighthouse adapter passes the same shared adapter suite as the fixture and HTTP adapters, using recorded sandbox responses so CI needs no credentials.
- Adding the stub condition requires no change to engine tests, and existing ADHD golden tests are untouched.
- With the dummy scorer present, absent or failing, ADHD recommendations are identical to rules-only output.

### Exit criteria

- An assessment runs end to end against Lighthouse sandbox patients.
- The second-condition stub and the dummy scorer are merged, disabled by default, and documented.
- A deployment guide and next-stage proposal are delivered.

### Risks and open questions

- Lighthouse sandbox access requires registration and may take time to approve. Apply during Phase 6.
- Sandbox data may contain few relevant mental health signals; the adapter may be provable only structurally.

---

## Future work

Not planned in detail. Each needs its own planning round and, for most, clinical and institutional partners.

| Item | Notes |
|---|---|
| Note evidence (`find_note_evidence`) | Concept extraction from clinical notes; must run inside the data boundary with a pinned model and its own annotated test set |
| Statistical referral model | Positive-unlabeled learning on real data, validated against a prospectively screened sample; plugs into the scorer slot |
| Priority tiers | Ranking against local evaluation capacity; needs population-level data |
| CDS Hooks service | The same engine delivering cards in the EHR, with clinician feedback captured |
| FHIR-native audit | AuditEvent and Provenance resources with AI transparency labels |
| Rules in CQL | Publishing rules as CQL libraries and plan definitions for portability |
| Additional conditions | Autism first, then others from the research report |
| Silent-mode pilot and trial | Prospective validation with a health-system partner, under ethics oversight |

## Cross-cutting risks

| Risk | Mitigation |
|---|---|
| Output read as a diagnosis | Standing invariant 1; fixed wording; intended-use statement in every output |
| Rule built on an unverified code or cutoff | Verification backlog; strict loader (invariant 6) |
| Real patient data enters the repository | Synthetic-only rule; CI checks; contributor guide |
| Under-flagging women | Measured in Phase 7; documented in the rule card |
| Specification or framework churn | Pinned versions; ADRs; documentation checked before each phase |
| Scope creep toward diagnosis, writes or patient-facing use | Hard rules in CLAUDE.md; intended-use statement; ask before departing from the plan |
| Schedule slip for a solo developer | Phases have exit criteria, not dates; status.md records carry-over |

## Changing this plan

The plan is expected to change. Propose a change to the project owner, update this file in the same pull request as the first affected work, and note the change in status.md. Decisions that are costly to reverse also get an ADR.
