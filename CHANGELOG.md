# Change log

All notable changes to this project. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning policy: [ADR 0013](docs/adr/0013-versioning-and-release.md). Three version lines are tracked: the **server** (the headings below), the **tool contract** and each **ruleset**.

The tool is not clinically validated, and no version of it diagnoses.

## [Unreleased]

Phase 8 (VA readiness and extensibility). Tool contract 0.4.0.

### Added

- Data-completeness status `not_supported`: the FHIR server does not offer a resource type at all (for example VA Lighthouse has no Flag, QuestionnaireResponse, ServiceRequest, CarePlan, MedicationDispense or MedicationStatement). A safety gate or exclusion check that needs such a type is "not performed" with the reason, never "not found"; an assessment proceeds without dispenses and statements when medication orders were read. `HttpFhirAdapter(supported_types=...)` refuses other types without a request.

- `DummyScorer` (`ADHD_MCP_SCORER=dummy`), clearly labelled `dummy-not-a-model`: a constant score of 0.0 that proves the scorer slot. Off by default.

- Experimental autism stub (`ADHD_MCP_EXPERIMENTAL_CONDITIONS=autism`; off by default; not for clinical use) proving the condition plugin interface: exclusion on recorded autism codes F84.0, F84.5, F84.8, F84.9 (verified against ICD-10-CM FY2027), three placeholder modifiers, ruleset `autism 0.0.1 (experimental)`. Ruleset status `experimental` added. [Rule card](docs/clinical/rule_card_autism_stub.md).

- VA Lighthouse Patient Health API support (`ADHD_MCP_FHIR_SERVER_PROFILE=lighthouse`), built from the public sandbox CapabilityStatement and OpenAPI: FHIR server profiles (`fhir/profiles.py`, `data/fhir_servers/`); the HTTP adapter searches only offered types, filters `since` itself where the server has no date search, and reads referenced Medication resources by id when `_include` is not offered; `LighthouseCcgAuth` with patient-scoped tokens (`launch`) and a configurable assertion audience (`ADHD_MCP_SMART_AUDIENCE`). Not yet run against the sandbox (no credentials). [Integration notes](docs/integration/lighthouse.md).

### Fixed

- Absolute FHIR references (`https://.../Medication/123`) are now understood; before, their medication codes and encounter links were silently lost.
- An empty record on a server that does not offer some types is `insufficient_data`, not `no_recommendation`.

### Changed

- Tool contract 0.3.0 to 0.4.0: the `status` enum of every `data_completeness` entry gains `not_supported`; the assessment's `scorer` gains `failed`; the `condition` argument's description names experimental stubs.
- A scorer that raises no longer fails the assessment: it gives no score and `failed: true`.

## [1.0.0rc1] - 2026-11-27

Release candidate. Not tagged as a release: ruleset `adhd 1.0.0` is still a draft awaiting the project owner's review of the clinical content (signal catalog, rule card, clinician wording, drug-class curation). Tool contract 0.3.0; ruleset `adhd 1.0.0 (draft)`.

### Added

- **Phase 7, evaluation and hardening.**
  - A labelled synthetic cohort of 184 patients (23 archetypes, both sexes, four age bands, look-alikes and sparse records) and an evaluation harness; the generated report for ruleset 1.0.0 ([docs/evaluation/adhd_ruleset_1.0.0.md](docs/evaluation/adhd_ruleset_1.0.0.md)): 184 of 184 patients match their intended outcome (the rules are applied as written; this is not evidence of accuracy).
  - A sex-balance review with measured options for the owner ([docs/evaluation/sex_balance_review.md](docs/evaluation/sex_balance_review.md)).
  - A model-in-the-loop harness: tasks, runner and grader, tested with scripted stand-in models ([docs/evaluation/model_in_the_loop.md](docs/evaluation/model_in_the_loop.md)).
  - Fault injection through the whole assessment (sixteen fault types on every resource type the assessment searches).
  - Latency targets, a FHIR request budget and `scripts/benchmark.py` ([docs/evaluation/performance.md](docs/evaluation/performance.md)).
  - User documentation: installation, configuration, MCP client setup, a tool reference generated from the contracts, limitations; this change log; versioning policy (ADR 0013); `scripts/release_check.py`; a `Dockerfile` built in CI.
- **Phase 6, audit, privacy and security.** One audit record per call (references and hashes only), W3C trace context passed to the FHIR server, a sensitive-data policy (substance use, HIV, sickle-cell disease), OAuth resource server over streamable HTTP with per-tool scopes, SMART backend services toward FHIR, validated configuration, a threat model.
- **Phase 5, rules engine and recommendation.** `assess_referral_need`, `draft_referral_proposal`, the condition-independent rules engine, ADHD ruleset 1.0.0 (draft) and its rule card, MCP resources and two clinician prompts.
- **Phase 4, evidence tools II.** `get_medication_timeline` (curated RxNorm drug classes), `get_utilization_summary`, `get_psychosocial_context`, the ADHD signal catalog, a per-request FHIR cache.
- **Phase 3, evidence tools I.** `check_safety_gate`, `get_mh_problem_list`, `get_screening_history`, `check_existing_care`.
- **Phases 1 and 2.** FastMCP server with `get_server_info`, the read-only FHIR port with fixture and HTTP adapters, normalization, terminology store, 14 synthetic personas, CI.

### Changed

- **Safety gate:** a check whose data was read only in part (a server warning, or a resource that could not be read) now fails, so the gate is `data_unavailable` and no referral is suggested. Before, the check reported not found, the gate was `clear_limited_data` and a suggestion could still be made (owner decision after the Phase 7 clinical safety review). The gate definition data and the tool contract are unchanged.

### Fixed

- The HTTP FHIR adapter raised an unhandled error on a search Bundle whose entry, resource or link was not an object, and silently dropped entries without a resource or a resource type; such a search now fails cleanly and the category is reported as failed.

### Known limitations

See [docs/limitations.md](docs/limitations.md). In short: not clinically validated; internalizing presentations are under-flagged (the research says women with ADHD are more often first labelled depressed or anxious); LOINC codes and screening cutoffs are unverified, so no screening score is used; coded data only.
