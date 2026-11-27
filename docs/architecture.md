# Architecture

How ADHD_MCP is put together. This is a design document that changes as phases complete; costly decisions are recorded in [adr/](adr/README.md).

**Built so far (Phases 1 to 3):** the FastMCP server with `get_server_info` and four evidence tools (`check_safety_gate`, `get_mh_problem_list`, `get_screening_history`, `check_existing_care`); shared domain models; the diagnostic-wording guard; the FHIR access layer (read-only port, fixture and HTTP adapters, normalization, typed record reader); the terminology store with value sets, instrument definitions and per-site local code mapping; the evidence layer; the persona catalog. See [Implemented: FHIR access and terminology](#implemented-fhir-access-and-terminology) and [Implemented: evidence tools](#implemented-evidence-tools).

## Purpose and boundary

The server answers one question for a clinician or a clinician's AI assistant: *given this patient's record, should a referral for formal adult ADHD screening be considered, and on what evidence?*

It does not diagnose, does not write to the health record, does not contact patients, and does not let a language model decide eligibility.

## Context

```
  Clinician's AI assistant (MCP client)        Other MCP clients (review, evaluation)
              |                                             |
              |  MCP: stdio locally, HTTP with OAuth when hosted
              v                                             v
  +--------------------------- ADHD_MCP server ----------------------------+
  |  MCP interface      tools | resources | prompts            (FastMCP)   |
  |  Orchestration      assess_referral_need                               |
  |  Rules engine       versioned rulesets, scorer slot, decision trace    |
  |  Condition plugins  ADHD (first)                                       |
  |  Evidence layer     one assembler per evidence tool                    |
  |  Privacy filter     sensitive-data policy                              |
  |  FHIR access        port + adapters (fixtures, HTTP, later Lighthouse) |
  |  Terminology store  versioned value sets and cutoffs                   |
  |  Audit and tracing  one record per call                                |
  +------------------------------------------------------------------------+
              |  FHIR R4 read-only (SMART backend services when authenticated)
              v
        FHIR server: local synthetic server now; VA Lighthouse / Oracle Health later
```

## Layers

Dependencies point downward only. A layer never imports from one above it.

| Layer | Responsibility | Must not |
|---|---|---|
| MCP interface | Declare tools, resources and prompts; validate inputs; shape outputs | Contain clinical or FHIR logic |
| Orchestration | Run safety gate, exclusions, evidence assembly and rules in order | Skip the safety gate |
| Rules engine | Apply a ruleset to evidence; produce a decision and a trace | Know anything specific to ADHD; read FHIR |
| Condition plugins | Supply a condition's ruleset, signal catalog, exclusions and next-step text | Change engine behavior |
| Evidence layer | Turn normalized records into named signals with resource references | Decide whether to recommend |
| Privacy filter | Apply the sensitive-data policy to records before they become evidence | Silently drop data without saying so in the output |
| FHIR access | Fetch and normalize FHIR resources behind a read-only port | Expose any write operation |
| Terminology store | Load versioned value sets and cutoffs; refuse unverified entries in strict mode | Hold codes in program logic |
| Audit and tracing | Record every call with identifiers, versions and references | Record clinical values or text |

## Repository layout

Packages are created when a test first needs them; those marked *planned* do not exist yet.

```
src/adhd_mcp/
  server.py         FastMCP application assembly
  versions.py       server, tool-contract and ruleset version lines
  clock.py          injected clock (the only place the real clock is read)
  tools/            thin tool wrappers, one per tool; shared context, arguments and errors
  wording/          approved wording and the diagnostic-language guard
  fhir/             port, fixture and HTTP adapters, search semantics, normalization, reader
  terminology/      value set, instrument and site code loading and matching
  evidence/         one assembler per evidence tool, plus shared windows and completeness
  models/           shared typed models and output schemas
  data/             wording, code systems, value sets, instruments, site codes,
                    safety gate, problem list and existing care definitions (rulesets later)
  resources/  prompts/  orchestration/  rules/  conditions/adhd/
  privacy/  audit/                                             planned
tests/
  unit/  contract/  tools/  property/  adapters/  integration/  (unit/evidence: assemblers)
  golden/  evals/                                              planned
  helpers/          wording assertion, fake FHIR server, failing adapter
  personas/         synthetic FHIR bundles, catalog and builder
scripts/            check, synthetic-data guard, persona build and load, population generator
docs/
```

## Implemented: FHIR access and terminology

```
 FhirReadPort (read_patient, search -> SearchResult(resources, warnings))
                                           no write method (standing invariant 4)
   |-- FixtureFhirAdapter                   in-memory resources or bundle files
   |-- HttpFhirAdapter                      GET only; paging, retries, origin-pinned next links
          |
          v  raw FHIR JSON
 normalize_many  ->  typed records + skipped list (entered-in-error, refuted, no id, malformed)
          |
          v
 PatientRecords  ->  ReadResult(records, skipped), optionally filtered by a ValueSet
```

- **Search warnings**: a server's OperationOutcome issues of severity warning or worse come back as `SearchWarning` (severity and issue code only; diagnostic text is dropped). Tools report the category as `incomplete`.
- **Search semantics** (`fhir/search.py`) are shared by every adapter: `since` is FHIR `ge` on each type's clinical date; `updated_since` is `_lastUpdated`; medication searches include referenced `Medication` resources. Both adapters pass one shared behavioural suite (`tests/adapters/shared_suite.py`), and the HTTP adapter also passes it against a live HAPI FHIR server in CI.
- **Normalization** rules are in [ADR 0007](adr/0007-fhir-modeling.md). Records keep the resource id and version for evidence; they keep no names, identifiers or free text.
- **Terminology**: value sets (`data/value_sets/`) and instruments (`data/instruments/`) are TOML with per-entry verification provenance. ICD-10-CM `prefix` entries match at the category boundary (`F15` matches `F15.10`, not `F150`); `regex` entries cover families defined by character position, such as the intent character of poisoning codes. Strict loading refuses anything unverified (standing invariant 6).

## Implemented: evidence tools

```
 tool wrapper (tools/*.py)        validate patient id and as-of date, read the Patient
   |                              errors: invalid_input | patient_not_found | fhir_unavailable | not_configured
   v
 assembler (evidence/*.py)        read only the categories it needs, in parallel;
   |                              a failed category becomes "failed", never an error
   v
 output (models/evidence_outputs.py)
   patient_id, as_of, is_diagnosis=false, notice, data_completeness[], versions, + tool fields
```

- **Context** (`tools/context.py`): the FHIR port, the clock and the site code mapping are injected into `create_server`. As a process the server reads `ADHD_MCP_FHIR_BASE_URL` or `ADHD_MCP_FIXTURE_DIR`, and `ADHD_MCP_SITE_CODES` (default `synthetic`).
- **As-of date**: every tool reads the record as of a date (default today, never the future); items dated later are ignored. Look-back windows are inclusive at both ends.
- **Data completeness**: every category read is reported as `available`, `empty`, `incomplete` (server warnings) or `failed`, with record and skipped counts, so an empty record is never mistaken for a clean one.
- **Site codes** (`data/site_codes/`): local codes with no standard (psychiatric inpatient and residential encounters, high-risk flags, ADHD referrals, evaluations and care plans, screening questionnaires). A concept a site does not map leaves the dependent check "not performed". Only the synthetic site exists.
- **Clinical definitions are data**: `data/safety_gate.toml`, `data/problem_list.toml`, `data/existing_care.toml`, each versioned and reported in outputs.

| Tool | Behaviour |
|---|---|
| `check_safety_gate` | Eleven checks, each found, not found, not performed (with reason) or failed. Status: positive if any check found a current signal; else data_unavailable if one failed; else clear_limited_data if one was not performed, the record is empty or the server warned; else clear. 365-day look-back; undated items count; older items are listed as history. Rule card: [rule_card_safety_gate.md](clinical/rule_card_safety_gate.md) |
| `get_mh_problem_list` | ICD-10-CM codes grouped into families (value sets), one entry per code citing every Condition; first onset and recorded dates; status of the latest record; onset order with shared ranks for equal dates; other chapter 5 codes in a fallback family |
| `get_screening_history` | One timeline from observation panels, components and mapped questionnaire responses. Instruments are recognised by code even while unverified (`code_verified`); a cutoff is applied only when code and cutoff are verified. Unknown survey instruments are listed, not scored. No item text is returned |
| `check_existing_care` | Excluded if an ADHD code is recorded, or an ADHD referral, evaluation or care plan is open or was completed within 365 days; `excluded` is null if a check failed and none was found. Medication for narcolepsy is a separate finding |

## Request flow for `assess_referral_need`

1. Validate input: patient identifier, optional as-of date, optional condition (defaults to ADHD).
2. Start an audit record and trace.
3. Fetch the patient's data through the FHIR port; normalize; apply the privacy filter.
4. Run the **safety gate**. Its result is always part of the output.
5. Run **exclusions** (existing ADHD diagnosis, evaluation in progress).
6. Assemble **evidence**: diagnoses, screening history, medications, utilization, psychosocial context.
7. Apply the active **ruleset** through the rules engine; collect the decision trace.
8. Build the output. If the safety gate is positive, it is presented first and the ADHD recommendation is withheld until the gate is addressed, while findings are still reported.
9. Complete the audit record with input resource references, versions and an output hash.

The other evidence tools run steps 1 to 3, one assembler, and step 9.

## Tools

All tools are read-only and take a patient identifier and an optional as-of date. Every output includes evidence references, a data-completeness note, and server and ruleset versions.

| Tool | FHIR resources read | Output summary |
|---|---|---|
| `get_server_info` | none | Server, contract and ruleset versions; intended-use statement |
| `check_safety_gate` | Condition, Observation, QuestionnaireResponse, Encounter, Flag | Gate status, checks performed, evidence, fixed guidance when positive |
| `get_mh_problem_list` | Condition | Diagnoses grouped by family with first-recorded dates and onset order |
| `get_screening_history` | Observation, QuestionnaireResponse | Instrument score timeline with cutoffs applied |
| `get_medication_timeline` | MedicationRequest, MedicationDispense, MedicationStatement | Exposure periods by drug class; distinct antidepressant count |
| `get_utilization_summary` | Encounter, Condition | Injury visits, crashes, psychiatric discharges, counts per window |
| `get_psychosocial_context` | Condition, Observation, Patient | Housing, legal, occupational, educational and military context |
| `check_existing_care` | Condition, ServiceRequest, CarePlan, Procedure | Exclusions and existing referrals |
| `assess_referral_need` | all of the above | The recommendation (below) |
| `draft_referral_proposal` | none | A draft referral with proposal intent; returned only, never stored |

`find_note_evidence` from the research report is deferred (see Future work in the project plan).

### Recommendation output

Fields of the `assess_referral_need` result. The exact schema is fixed by contract tests in Phase 5.

| Field | Meaning |
|---|---|
| Recommendation | One of a fixed vocabulary, for example: consider referral for formal screening; no recommendation; address safety gate first; already in care; insufficient data |
| Not-a-diagnosis marker | Always present and always asserting that the result is not a diagnosis |
| Condition to screen | ADHD in version 1.0 |
| Suggested next step | For example, an ASRS screen followed by clinician evaluation if positive |
| Safety gate | Status, checks performed, evidence |
| Basis | List of evidence items: signal name, weight class, resource references, dates |
| Exclusions checked | What was looked for and what was found |
| Decision trace | Which rules fired and which did not |
| Data completeness | Which data categories were available, empty, withheld or failed to load |
| Versions | Server, tool contract, ruleset, and scorer if present |

### Resources and prompts

| Kind | Items |
|---|---|
| Resources | Active ruleset; signal catalog; value sets; instrument metadata (no copyrighted item text); intended-use statement |
| Prompts | Explain a recommendation from its evidence; summarize what was checked and what was missing |

## Clinical logic

Details and sources are in the research report, ADHD section. The ruleset is a starting heuristic from the literature, not a validated rule.

- **Safety gate signals:** suicidal ideation, attempt and self-harm codes; history of suicidal behavior; PHQ-9 item 9 at 1 or more; positive C-SSRS; recent psychiatric inpatient or residential discharge; existing high-risk flags.
- **High-weight ADHD signals:** stimulant-related disorder or non-prescribed stimulant evidence; alcohol involvement; motor-vehicle crashes as driver; repeated accidental injuries; TBI with attention complaints (routes to neuropsychological evaluation).
- **Modifiers:** other substance use disorders; PTSD; intermittent explosive disorder; recurrent or treatment-resistant depression or anxiety with many antidepressant switches; borderline personality label; chronic insomnia; attention symptom codes; legal, occupational, educational or housing problems; family history.
- **Starting rule:** one high-weight signal with two or more modifiers, or two or more high-weight signal classes within about three years.
- **Exclusions:** existing ADHD diagnosis; evaluation already in progress. Stimulants for narcolepsy are handled separately.

Every code, window and cutoff lives in versioned data and must be verified before use ([verification backlog](clinical/verification_backlog.md)).

## Versioning

Three independent version lines, all reported in every output and audit record:

| Line | Changes when |
|---|---|
| Server | Any release |
| Tool contract | A tool's name, inputs or output schema changes |
| Ruleset | Any clinical content changes; released rulesets are immutable |

## Extensibility

- **New condition:** add a plugin with its own signal catalog, ruleset and next-step text. The engine and evidence tools are shared.
- **Statistical model:** implement the scorer interface. The engine runs with or without a scorer, and the scorer's identity and version flow into outputs and audit records.
- **New FHIR back end:** implement the FHIR port and pass the shared adapter test suite.

## Security and privacy

Built in Phase 6; summarized here so earlier phases do not design against it.

- The server is an OAuth resource server toward MCP clients and a SMART on FHIR client toward the FHIR server. It never forwards a caller's token.
- Local use over stdio; hosted use over HTTP with authentication.
- Text from FHIR records is data, never instructions. It is delimited where returned and never placed into prompts as instructions.
- Specially protected data (for example substance use under 38 U.S.C. 7332 and 42 CFR Part 2) passes through a configurable policy: allow, cite existence and date only, or withhold.
- Audit records and logs contain references and hashes only.

## Open design questions

Tracked in [status.md](../status.md) and resolved through ADRs: FHIR modeling library; source of RxNorm drug-class membership; default sensitive-data policy; audit storage format.
