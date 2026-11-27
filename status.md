# Project Status

Read this first. Update it whenever the state of the work changes (rules in [CLAUDE.md](CLAUDE.md#keep-statusmd-current)).

**Last updated:** 2026-11-27
**Current phase:** Phase 8 (VA readiness and extensibility), started 2026-11-27 ahead of the 1.0.0 tag (owner decision). Release candidate 1.0.0rc1; tagging 1.0.0 still waits for the owner's review of the clinical content.
**Branch:** `claude/tender-lamport-y0qpyy`

## Summary

A FastMCP 4.2 server, version 1.0.0rc1, with ten read-only tools (tool contract 0.3.0): `get_server_info`; seven evidence tools (`check_safety_gate`, `get_mh_problem_list`, `get_screening_history`, `check_existing_care`, `get_medication_timeline`, `get_utilization_summary`, `get_psychosocial_context`); `assess_referral_need`, which runs the safety gate first and applies ADHD ruleset 1.0.0 (draft) to an evidence-linked signal catalog; and `draft_referral_proposal` (a ServiceRequest draft, never stored). Also MCP resources and two clinician prompts. Every call is audited (references and hashes only); a sensitive-data policy cites or withholds substance use, HIV and sickle-cell data; stdio or HTTP with OAuth; SMART backend services toward FHIR. Evaluated on 14 personas and a 184-patient labelled cohort (all match their intended outcomes); fault-injected; benchmarked; packaged (wheel, Dockerfile); documented for users ([README](README.md), [docs/guide/](docs/guide/configuration.md), [tool reference](docs/reference/tools.md), [limitations](docs/limitations.md), [change log](CHANGELOG.md)).

## Done

- **Phase 7** (items 1 to 4 and 6 to 9; item 5 waits for a live model run; [SpiroGanas/ADHD_MCP#6](https://github.com/SpiroGanas/ADHD_MCP/pull/6)): fault injection, 16 fault types on every resource type the assessment searches, and fixes for malformed Bundles (item 6); labelled cohort of 184 patients, evaluation harness and generated [report](docs/evaluation/adhd_ruleset_1.0.0.md) (items 1, 2); [sex-balance review](docs/evaluation/sex_balance_review.md) (item 3); [model-in-the-loop harness](docs/evaluation/model_in_the_loop.md) with scripted stand-ins (item 4); latency target and request budget, [performance](docs/evaluation/performance.md) (item 7); README rewritten, configuration and client guides, generated tool reference, limitations, change log, link checker (item 8); versioning policy [ADR 0013](docs/adr/0013-versioning-and-release.md) (proposed), version 1.0.0rc1, `scripts/release_check.py`, Dockerfile built and smoke-tested in CI (item 9). Risk register reviewed.
- PR #5 (Phases 4 to 6) merged into `main`.
- **Phase 6** (all nine work items; [SpiroGanas/ADHD_MCP#5](https://github.com/SpiroGanas/ADHD_MCP/pull/5)): audit, trace context, sensitive-data policy, OAuth resource server, SMART backend services, HTTP transport, threat model ([ADR 0011](docs/adr/0011-audit-tracing-and-privacy.md), [ADR 0012](docs/adr/0012-authentication.md)).
- **Phases 1 to 5** ([#1](https://github.com/SpiroGanas/ADHD_MCP/pull/1) to [#5](https://github.com/SpiroGanas/ADHD_MCP/pull/5)): research and plan; walking skeleton, FHIR layer, terminology, personas; evidence tools; rules engine, ruleset 1.0.0 (draft), `assess_referral_need`, `draft_referral_proposal`, resources, prompts.

## In progress

- **Phase 8**, one PR with a commit per work item. Done: `not_supported` data status (contract 0.4.0); dummy scorer (item 6). Remaining, in order: autism stub (item 5); Lighthouse adapter from public docs with synthetic Lighthouse-shaped responses (item 1); data-shape, Oracle Health and security-label desk reviews (items 2 to 4); deployment guide (item 7); next-stage plan (item 8).

## Next steps

1. Continue Phase 8 from the first unfinished item under "In progress".
2. Project owner decisions before tagging 1.0.0 (open questions 1, 4, 14, 16, 17): review and approve, or change, the signal catalog (`reviewed_by_owner = false`), the [rule card](docs/clinical/rule_card_adhd_1.0.md), the clinician wording in `src/adhd_mcp/data/wording.toml`, the drug-class curation (ADR 0009) and medication parameters; choose a sex-balance option; approve ADR 0013.
3. Then release: ruleset status `released` with its sha256 in `src/adhd_mcp/data/released_rulesets.toml`; rule card status Released; tool contract `1.0.0` (snapshots, tool reference); version `1.0.0` in `pyproject.toml` and `CHANGELOG.md`; regenerate the evaluation report; `uv run python scripts/release_check.py` passes; the owner tags `v1.0.0` on `main`.
4. When the owner approves the budget and SDK: a live model driver, the model-in-the-loop run, then tool description tuning (item 5).

## Open questions for the project owner

| # | Question | Needed by |
|---|---|---|
| 1 | Who reviews and approves clinical content (rule cards, signal catalog)? Is there a clinician adviser? (For now the owner waived the human spot-check until release.) | Before release |
| 4 | Model-in-the-loop live run: approve the budget (about 140 requests per model), the `anthropic` SDK as an optional `eval` dependency group, and the proposed pass bar in [model_in_the_loop.md](docs/evaluation/model_in_the_loop.md) | Before release |
| 5 | Will VA Lighthouse sandbox access be requested, and by whom? (No access as of 2026-11-27; the adapter is built from public docs and the live run waits.) | Phase 8 exit |
| 6 | Should a priority tier be part of the 1.0 output? (Proposal: no; not built.) | Before release |
| 9 | PC-PTSD-5 cutoff: 4 (current National Center for PTSD default) or 3? | Before LOINC verification (F2) |
| 12 | How should ASRS results be recognised in FHIR data (follow-up F3)? | Phase 8 |
| 14 | Verify LOINC through a LOINC account (fhir.loinc.org) or NLM's redistribution? Until then PHQ-9 item 9 and C-SSRS checks are "not performed", no screening cutoff is applied, and no ruleset signal uses a screening score | Before release |
| 15 | Approve the invariant-4 exception: the SMART token request is the one POST in the code (to the OAuth token endpoint, never the FHIR server) | PR review |
| 16 | Sex balance: ruleset 1.0.0 flags 8 of 40 internalizing suggestive presentations against 32 of 32 externalizing ones. Choose an option from the [sex-balance review](docs/evaluation/sex_balance_review.md): A no change (proposed for 1.0.0), B a sex-blind "four or more modifiers" rule as draft ruleset 1.1.0, or another | Before release |
| 17 | Approve [ADR 0013](docs/adr/0013-versioning-and-release.md): three version lines, the tool contract becoming 1.0.0 with server 1.0.0, release steps and the release check | Before release |
| 18 | Publish the package or container image anywhere (PyPI, a container registry)? Proposal: not for 1.0; build in CI only | Before release |

## Decisions

Scope decisions made 2026-11-26 are recorded in [project_plan.md](project_plan.md#scope). Architecture decisions are in [docs/adr/](docs/adr/README.md).

Owner decisions 2026-11-27 (start of Phase 8):

- Start Phase 8 before tagging 1.0.0; one PR with a commit per work item; version stays 1.0.0rc1, changes under "Unreleased" in the change log.
- No Lighthouse sandbox access: build the adapter and its client-credentials auth from the public VA documentation, tested with synthetic Lighthouse-shaped responses; the live end-to-end run stays open.
- A resource type a back end does not support is reported with a new data-completeness status `not_supported`; checks that need it are "not performed" (tool contract 0.3.0 to 0.4.0).
- Autism stub: exclusion on recorded autism codes (F84.0, F84.5, F84.8, F84.9) verified against the FY2027 tabular; placeholder signals reuse verified value sets; ruleset status `experimental`; registered only when enabled by an environment variable. Session moved to the ADHD_MCP environment for ftp.cdc.gov; developer.va.gov, api.va.gov, sandbox-api.va.gov, fhir.cerner.com and docs.oracle.com added to it (owner approved).
- Lighthouse facts so far (public sandbox CapabilityStatement and OpenAPI, fetched 2026-11-27): offers Condition, Observation, Encounter, Procedure, MedicationRequest, Medication, Patient (not QuestionnaireResponse, Flag, ServiceRequest, CarePlan, MedicationDispense, MedicationStatement); no `_include`; MedicationRequest has no date search; absolute references; `_count` max 200; Observation categories laboratory, social-history, vital-signs only; CCG token: `launch` = base64 of {"patient": ICN}, assertion exp at most 300 s after iat, RS256 in the example, token lives 5 minutes. The exact CCG scopes and assertion audience (an Okta URL) were not readable here: configurable and unverified.

Owner decisions 2026-11-27 (start of Phase 7):

- Safety gate on partly read data (former open question 19, found by the Phase 7 clinical safety review): a check whose data was read only in part fails, so the gate is `data_unavailable` and no suggestion is made. Built in this phase.

- Model-in-the-loop evaluation (item 4): build the tasks, harness and grader now, tested with a scripted stand-in model; the live run waits for an API key (open question 4).
- Release (item 9): prepare everything (versioning policy, change log, packaging, release check) as a release candidate; tag 1.0.0 only after the owner reviews the clinical content and the ruleset is released.
- Sex-balance review (item 3): measure and propose options; no ruleset change until the owner chooses.
- Container: a Dockerfile and a CI build check; nothing published to a registry.

Owner decisions 2026-11-27 (start of Phases 4 to 6):

- Drug classes: hand-curated RxNorm ingredient lists per class, verified against RxNav (rxnav.nlm.nih.gov added to the environment), expanded to product codes by a script and committed as data (ADR 0009).
- ADHD ruleset 1.0 uses the proposed defaults: recommend when at least one high-weight signal occurs with two or more modifiers, or two or more high-weight classes, all within 1095 days of the as-of date. High: stimulant-related disorder, alcohol (F10, Y90.1-Y90.9, R78.0), crash as driver, two or more accidental-injury visits within 730 days. TBI adds a neuropsychological-evaluation note and does not count. Modifiers: other SUD, PTSD, IED, depression or anxiety, three or more distinct antidepressants, BPD, insomnia, attention-symptom codes, legal, education or occupation, housing, family history. All marked inference in the rule card.
- Sensitive-data default (open question 3): cite existence and date only; rules still use the signal; the output states the category was restricted.
- Signal boundaries (open questions 10, 11): value sets kept as verified (no F13/F16/F18; F15 whole; Y90.0 excluded; e-bike drivers counted; F32.81 kept; no G47.09; Z55/Z56 whole; housing = Z59.0 and Z59.81).
- PyJWT and cryptography become direct pinned dependencies (Phase 6).
- Phases 4 to 6 ship as one PR with a commit per work item.
- terminology.hl7.org was added to the environment to verify security-label codes.

Earlier decisions (Phases 1 to 3, 2026-11-26 and 2026-11-27): tooling in ADR 0006; FHIR modeling in ADR 0007; site code mapping and search warnings in ADR 0008; safety gate look-back 365 days with undated items counting, discharge windows 90 and 365 days, asphyxiation codes counted, a gate is plain "clear" only when every check ran; LOINC stays unverified (F2); the human spot-check of `safety.*` value sets is waived until release; HAPI FHIR `v8.12.0-2` as the local server.

## Known gaps and cautions

- LOINC codes and all screening cutoffs are unverified, so no screening score is used by the gate or the ruleset. ICD-10-CM is verified against FY2027; the human spot-check is still owed before release.
- Ruleset 1.0.0 is a draft and not clinically validated; internalizing presentations, so likely women, are under-flagged (cohort: 8 of 40 against 32 of 32 externalizing; [sex-balance review](docs/evaluation/sex_balance_review.md)).
- No real language model has used the server yet (model-in-the-loop harness tested with scripted stand-ins only).
- The development container has no Docker daemon: the image and the live latency test run only in CI (both passed on PR #6).
- The full list for users: [docs/limitations.md](docs/limitations.md).
- Retired RxNorm product codes are not matched (ADR 0009). Missed appointments are not read (no Appointment search). Coded social-history observation values are reported but not counted by the ruleset.
- ICD-10-CM codes sent without a dot do not match value sets (ADR 0007, Phase 8).
- The development audit file has no tamper evidence (risk P5, accepted); rate limiting is left to the hosting gateway (risk S6, accepted).

## Pull requests

| PR | Subject | State |
|---|---|---|
| [SpiroGanas/ADHD_MCP#1](https://github.com/SpiroGanas/ADHD_MCP/pull/1) | Research report | Merged |
| [SpiroGanas/ADHD_MCP#2](https://github.com/SpiroGanas/ADHD_MCP/pull/2) | Project plan, architecture and working documentation | Merged |
| [SpiroGanas/ADHD_MCP#3](https://github.com/SpiroGanas/ADHD_MCP/pull/3) | Phases 1 and 2: walking skeleton, FHIR access layer, terminology and personas | Merged |
| [SpiroGanas/ADHD_MCP#4](https://github.com/SpiroGanas/ADHD_MCP/pull/4) | Phase 3: evidence tools I | Merged |
| [SpiroGanas/ADHD_MCP#5](https://github.com/SpiroGanas/ADHD_MCP/pull/5) | Phases 4-6: evidence tools II, rules engine and recommendation, audit, privacy and security | Merged |
| [SpiroGanas/ADHD_MCP#6](https://github.com/SpiroGanas/ADHD_MCP/pull/6) | Phase 7: evaluation, hardening and release candidate 1.0.0rc1 | Open |
