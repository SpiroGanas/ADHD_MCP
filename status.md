# Project Status

Read this first. Update it whenever the state of the work changes (rules in [CLAUDE.md](CLAUDE.md#keep-statusmd-current)).

**Last updated:** 2026-11-28
**Current phase:** Hand-off to human developers and clinicians. Peer review 01 fixes are merged ([SpiroGanas/ADHD_MCP#9](https://github.com/SpiroGanas/ADHD_MCP/pull/9), with no recorded review). Hand-off documents (review checklist, user guide, clinician quick start) are in review on branch `claude/production-handoff-docs-aozfkw`. Version 0.9.0; no release is tagged. 1.0.0 waits for a clinician's sign-off, a real model run and a real sandbox read (G3).
**Branch:** `claude/production-handoff-docs-aozfkw` (hand-off documents in `docs/handoff/`)

## Summary

A FastMCP 4.2 server, version 0.9.0, with ten read-only tools (tool contract 0.5.0): `get_server_info`; seven evidence tools (`check_safety_gate`, `get_mh_problem_list`, `get_screening_history`, `check_existing_care`, `get_medication_timeline`, `get_utilization_summary`, `get_psychosocial_context`); `assess_referral_need`, which runs the safety gate first and applies ADHD ruleset 1.0.0 (draft) to an evidence-linked signal catalog; and `draft_referral_proposal` (a ServiceRequest draft, never stored). Also MCP resources and two clinician prompts. Every call is audited (references and hashes only); a sensitive-data policy cites or withholds substance use, HIV and sickle-cell data; stdio or HTTP with OAuth; SMART backend services toward FHIR. Tested on 16 personas and a 184-patient labelled cohort (all match their intended outcomes, which shows the rules are applied as written, not that they are accurate); fault-injected; benchmarked; packaged (wheel, Dockerfile); documented for users ([README](README.md), [docs/guide/](docs/guide/configuration.md), [tool reference](docs/reference/tools.md), [limitations](docs/limitations.md), [change log](CHANGELOG.md)).

## Done

- **Peer review 01 fixes** (2026-11-28, [SpiroGanas/ADHD_MCP#9](https://github.com/SpiroGanas/ADHD_MCP/pull/9), merged with no recorded review or comment, so open questions 21 and 22 still have no recorded answer; one commit per finding; owner decisions below). Safety gate: SNOMED-only or text-only conditions fail closed and dotless ICD-10-CM is repaired (S1); a result under an unverified PHQ-9 item 9 or C-SSRS code stops the gate (S2; persona p15). Clinical logic, drafts for the reviewer: `outside_intended_population` for under-18, no birth date or deceased (C3; persona p16); only active problem-list items are open-ended and reasons give dates (C1); one visit supplies at most one high-weight signal and follow-up visits are not new injuries (C2); current ADHD medication holds the suggestion (C4); unfilled orders are not exposure (C5). Privacy and security: withheld signals are "not checked" (P1); explicit policy for remote servers (P2); refusals audited (P4); https and 0600 audit file (P5). Data access: 404 on search, timestamps without offsets, start-up errors (D2-D4); filtered Observation searches, large-record benchmark, audit cap (D1). Versions: content fingerprint in outputs and release pins (X2); version 0.9.0 (G3). Tests and CI (T2, T3, T5-T8, T10) and documents (X1, X3-X7, P3). A clinical safety review of the branch before the pull request found two blocking defects in these fixes, both fixed: the gate's code-filtered Observation read missed a PHQ-9 item 9 recorded as a component of a local panel (B1), and the C4 medication check failed open on unreadable data (B2); five smaller points were fixed or documented. Full check: 2,720 tests, 100% branch coverage of rules, gate, orchestration and privacy.
- **Peer review 01** (2026-11-27, `main` at `9e14e02`): [peer_review_01.md](peer_review_01.md). All of `src/` read, the check suite run (2,300 passed, coverage 98.65%), 17 read-only experiments on synthetic data. No code, test or data file changed. Findings are listed under "Next steps" and in the report.
- **Phase 8** (items 1 to 8 except the live Lighthouse run; [SpiroGanas/ADHD_MCP#7](https://github.com/SpiroGanas/ADHD_MCP/pull/7), merged): `not_supported` data status (contract 0.4.0), dummy scorer, autism stub, Lighthouse adapter from public documentation, Oracle Health desk review, deployment guide, next-stage proposal, ADR 0014 (proposed).
- **Phase 7** (items 1 to 4 and 6 to 9; item 5 waits for a live model run; [SpiroGanas/ADHD_MCP#6](https://github.com/SpiroGanas/ADHD_MCP/pull/6)): fault injection, 16 fault types on every resource type the assessment searches, and fixes for malformed Bundles (item 6); labelled cohort of 184 patients, evaluation harness and generated [report](docs/evaluation/adhd_ruleset_1.0.0.md) (items 1, 2); [sex-balance review](docs/evaluation/sex_balance_review.md) (item 3); [model-in-the-loop harness](docs/evaluation/model_in_the_loop.md) with scripted stand-ins (item 4); latency target and request budget, [performance](docs/evaluation/performance.md) (item 7); README rewritten, configuration and client guides, generated tool reference, limitations, change log, link checker (item 8); versioning policy [ADR 0013](docs/adr/0013-versioning-and-release.md) (proposed), version 1.0.0rc1, `scripts/release_check.py`, Dockerfile built and smoke-tested in CI (item 9). Risk register reviewed.
- PR #5 (Phases 4 to 6) merged into `main`.
- **Phase 6** (all nine work items; [SpiroGanas/ADHD_MCP#5](https://github.com/SpiroGanas/ADHD_MCP/pull/5)): audit, trace context, sensitive-data policy, OAuth resource server, SMART backend services, HTTP transport, threat model ([ADR 0011](docs/adr/0011-audit-tracing-and-privacy.md), [ADR 0012](docs/adr/0012-authentication.md)).
- **Phases 1 to 5** ([#1](https://github.com/SpiroGanas/ADHD_MCP/pull/1) to [#5](https://github.com/SpiroGanas/ADHD_MCP/pull/5)): research and plan; walking skeleton, FHIR layer, terminology, personas; evidence tools; rules engine, ruleset 1.0.0 (draft), `assess_referral_need`, `draft_referral_proposal`, resources, prompts.

## In progress

- **Hand-off documents** (branch `claude/production-handoff-docs-aozfkw`; documentation only, no code, test or data change): three Word documents in [docs/handoff/](docs/handoff/README.md). A **Human Review Checklist** of about 130 items grouped by reviewer role (owner, physician, suicide prevention lead, psychologist, nurse, pharmacist, coder, informaticist, software and security engineers, privacy, counsel, data scientist, operations), each with where to look and when it is needed; a **User Guide** (30 pages); a three-page **Clinician Quick Start Guide**. The worked examples were produced by running 0.9.0 on the synthetic personas. In review: [SpiroGanas/ADHD_MCP#10](https://github.com/SpiroGanas/ADHD_MCP/pull/10).

## Next steps

1. **Human reviewers: work through the [Human Review Checklist](docs/handoff/ADHD_MCP_Human_Review_Checklist.docx)**, starting with its "ten items that block everything else". It folds in every step below that needs a person. PR #9 merged without a recorded review, so the owner still has to answer open questions 21 (drafted wording in `src/adhd_mcp/data/wording.toml`) and 22 (`insufficient_data` for a held suggestion, C4); checklist items PO-03 and PO-04.
2. **LOINC verification is now a blocker** (open question 14): until PHQ-9 item 9 and C-SSRS codes are verified, any patient with such a result in the past year gets `insufficient_data` (S2).
3. Owner actions the code cannot do (G1, G2): protect `main` with a required human review; name a clinical reviewer (open question 1); have someone with security experience review the threat model and ADR 0012; do the waived `safety.*` spot-check (20 entries).
4. Clinical reviewer: confirm or reverse the drafts C1 to C5, and answer the questions in the [rule card](docs/clinical/rule_card_adhd_1.0.md#open-questions-for-the-clinical-reviewer-peer-review-01) (flag rate and nicotine dependence C6; driver, anxiety and unconfirmed-diagnosis scope C7; exclusion scope X5; equity, falls, history-of codes, differential notes, annual code updates X7); decide SNOMED CT value sets or a terminology service for the safety concepts (S1 step 3).
5. Follow-ups not built in this change: read `/metadata` at start-up for the `generic` profile to learn the offered types (D2); report skip rates by reason in the evaluation (D3); estimate the flag rate (C6); pin Docker base images by digest (T5); a dependency audit job (owner: not now); split `verified` into `exists_in_source` and `reviewed_by` (G2; owner: not now).
6. Earlier owner decisions still open before 1.0.0 (open questions 1, 4, 14, 16, 17, 19): the signal catalog (`reviewed_by_owner = false`), the rule card, the wording, drug-class curation, a sex-balance option, ADR 0013 and ADR 0014. Phases 4 and 5 are marked done, but their exit criteria (an owner-reviewed catalog and an approved rule card) are not met.
7. Then release as ADR 0013 says: ruleset status `released` with its sha256 and `content_sha256` in `src/adhd_mcp/data/released_rulesets.toml`; tool contract `1.0.0`; version `1.0.0`; regenerate the evaluation report; `uv run python scripts/release_check.py` passes; the owner tags `v1.0.0` on `main`.
8. The Lighthouse live run waits for sandbox credentials (open question 5); the model-in-the-loop run waits for the budget and SDK decision (open question 4).

## Open questions for the project owner

| # | Question | Needed by |
|---|---|---|
| 1 | Who reviews and approves clinical content (rule cards, signal catalog)? Is there a clinician adviser? (For now the owner waived the human spot-check until release.) | Before release |
| 4 | Model-in-the-loop live run: approve the budget (about 140 requests per model), the `anthropic` SDK as an optional `eval` dependency group, and the proposed pass bar in [model_in_the_loop.md](docs/evaluation/model_in_the_loop.md) | Before release |
| 5 | Will VA Lighthouse sandbox access be requested, and by whom? (No access as of 2026-11-27; the adapter is built from public docs and the live run waits.) | Phase 8 exit |
| 6 | Should a priority tier be part of the 1.0 output? (Proposal: no; not built.) | Before release |
| 9 | PC-PTSD-5 cutoff: 4 (current National Center for PTSD default) or 3? | Before LOINC verification (F2) |
| 12 | How should ASRS results be recognised in FHIR data (follow-up F3)? | Phase 8 |
| 14 | Verify LOINC through a LOINC account (fhir.loinc.org) or NLM's redistribution? Until then no screening cutoff is applied, no ruleset signal uses a screening score, and (since peer review 01, S2) any PHQ-9 item 9 or C-SSRS result in the past year stops the gate, so such patients are `insufficient_data` | Now: a blocker |
| 15 | Approve the invariant-4 exception: the SMART token request is the one POST in the code (to the OAuth token endpoint, never the FHIR server) | PR review |
| 16 | Sex balance: ruleset 1.0.0 flags 8 of 40 internalizing suggestive presentations against 32 of 32 externalizing ones. Choose an option from the [sex-balance review](docs/evaluation/sex_balance_review.md): A no change (proposed for 1.0.0), B a sex-blind "four or more modifiers" rule as draft ruleset 1.1.0, or another | Before release |
| 17 | Approve [ADR 0013](docs/adr/0013-versioning-and-release.md): three version lines, the tool contract becoming 1.0.0 with server 1.0.0, release steps and the release check | Before release |
| 19 | Accept [ADR 0014](docs/adr/0014-server-profiles-and-unoffered-data.md) (server profiles, `not_supported`, patient-scoped tokens); still "Proposed" after PR #7 merged | Before release |
| 18 | Publish the package or container image anywhere (PyPI, a container registry)? Proposal: not for 1.0; build in CI only | Before release |
| 21 | Approve the wording drafted for peer review 01 in `wording.toml`: the `outside_intended_population` recommendation text, the notes `population_under_age`, `population_no_birth_date`, `population_deceased` and `adhd_medication_without_code` | PR review |
| 22 | C4: a suggestion held for current ADHD medication without an ADHD code is reported as `insufficient_data` with a note (no new code). Keep, or add a dedicated code such as `possibly_in_care` (a contract change)? | PR review |
| 23 | T9: commit a failing test separately from the code that passes it (so the red step can be audited), which conflicts with "run the full check before every commit"? This change kept each commit green and named the tests it changed | Before the next clinical change |

## Decisions

Scope decisions made 2026-11-26 are recorded in [project_plan.md](project_plan.md#scope). Architecture decisions are in [docs/adr/](docs/adr/README.md).

Owner decisions 2026-11-28 (peer review 01, former open question 20). The clinical-logic changes are built as drafts for the clinical reviewer to confirm or reverse:

- S1: a Condition with no coding in a system the value sets cover makes the Condition category `incomplete` (warning `unrecognized_coding`), so the gate fails closed. Dotless ICD-10-CM codes are normalized.
- S2: a result under a code the instrument file lists for a gate check, verified or not, stops the gate (`data_unavailable`); the unverified code is used only to stop, never to score.
- C3: new recommendation `outside_intended_population` (under 18 at the as-of date, no birth date, or deceased); tool contract 0.5.0.
- C1: encounter diagnoses and event codes count by their latest date; only an active problem-list item is open-ended; abatement is used; the reason gives the dates.
- C2: injury episodes, not visits (seventh character D or S is not a new injury); one encounter supplies at most one high-weight signal.
- C4: current exposure to an ADHD medication without a narcolepsy reason makes `excluded` unknown, with a note.
- C5: with complete dispensing data, only antidepressants with exposure count.
- P1: a signal whose category had records withheld for this patient reads "Not checked: withheld by the privacy policy"; with no rule fired the result is `insufficient_data`.
- D1: filtered searches now, with a large-record benchmark and a capped audit reference list.
- P2: a non-local FHIR server needs an explicit privacy policy. P5: plain http to a non-local host is refused unless explicitly allowed; the audit file is 0600.
- G3: server version 0.9.0 until the release conditions in the review are met. X2: a fingerprint of all clinical content in every output's `versions`.
- Not now: splitting the `verified` flag (G2), a dependency audit job in CI.

Owner decisions 2026-11-27 (start of Phase 8):

- Start Phase 8 before tagging 1.0.0; one PR with a commit per work item; version stays 1.0.0rc1, changes under "Unreleased" in the change log.
- No Lighthouse sandbox access: build the adapter and its client-credentials auth from the public VA documentation, tested with synthetic Lighthouse-shaped responses; the live end-to-end run stays open.
- A resource type a back end does not support is reported with a new data-completeness status `not_supported`; checks that need it are "not performed" (tool contract 0.3.0 to 0.4.0).
- Antidepressant count on a server without dispenses or statements (safety review finding B1): keep counting from orders and disclose it in the signal's reason, not insufficient data.
- Autism stub: exclusion on recorded autism codes (F84.0, F84.5, F84.8, F84.9) verified against the FY2027 tabular; placeholder signals reuse verified value sets; ruleset status `experimental`; registered only when enabled by an environment variable. Session moved to the ADHD_MCP environment for ftp.cdc.gov; developer.va.gov, api.va.gov, sandbox-api.va.gov, fhir.cerner.com and docs.oracle.com added to it (owner approved).
- Lighthouse facts so far (public sandbox CapabilityStatement and OpenAPI, fetched 2026-11-27): offers Condition, Observation, Encounter, Procedure, MedicationRequest, Medication, Patient (not QuestionnaireResponse, Flag, ServiceRequest, CarePlan, MedicationDispense, MedicationStatement); no `_include`; MedicationRequest has no date search; absolute references; `_count` max 200; Observation categories laboratory, social-history, vital-signs only; CCG token: `launch` = base64 of {"patient": ICN}, assertion exp at most 300 s after iat, RS256 in the example, token lives 5 minutes. The exact CCG scopes and assertion audience (an Okta URL) were not readable here: configurable and unverified.

Owner decisions 2026-11-27 (start of Phase 7):

- Safety gate on partly read data (found by the Phase 7 clinical safety review; the "open question 19" of that time, not today's): a check whose data was read only in part fails, so the gate is `data_unavailable` and no suggestion is made. Built in this phase.

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

- Peer review 01's confirmed defects are fixed on the branch, and the safety review of those fixes found two more, also fixed; its process findings (G1, G2) and the clinical questions are not, and need people. Residuals documented in the limitations: withholding by an undisclosed security label can hide a signal silently (by design); an Encounter reason coded only in SNOMED CT is not recognized by the gate. Read [peer_review_01.md](peer_review_01.md).
- One AI author wrote the rules, value sets, tests, evaluation, threat model and safety reviews; no human has reviewed a pull request (G1). "Verified" means checked by that author (G2).
- LOINC codes and all screening cutoffs are unverified, so no screening score is used by the gate or the ruleset, and a recent PHQ-9 item 9 or C-SSRS result makes a patient `insufficient_data`. ICD-10-CM is verified against FY2027; the human spot-check is still owed before release.
- Conditions coded only in SNOMED CT make a patient `insufficient_data` (fail closed) until SNOMED CT value sets or a terminology service exist.
- Ruleset 1.0.0 is a draft and not clinically validated; internalizing presentations, so likely women, are under-flagged (cohort: 8 of 40 against 32 of 32 externalizing; [sex-balance review](docs/evaluation/sex_balance_review.md)).
- No real language model has used the server yet (model-in-the-loop harness tested with scripted stand-ins only).
- The development container has no Docker daemon: the image and the live latency test run only in CI (both passed on PR #6).
- The full list for users: [docs/limitations.md](docs/limitations.md).
- Retired RxNorm product codes are not matched (ADR 0009). Missed appointments are not read (no Appointment search). Coded social-history observation values are reported but not counted by the ruleset.
- The development audit file has no tamper evidence (risk P5, accepted); rate limiting is left to the hosting gateway (risk S6, accepted).

## Pull requests

| PR | Subject | State |
|---|---|---|
| [SpiroGanas/ADHD_MCP#1](https://github.com/SpiroGanas/ADHD_MCP/pull/1) | Research report | Merged |
| [SpiroGanas/ADHD_MCP#2](https://github.com/SpiroGanas/ADHD_MCP/pull/2) | Project plan, architecture and working documentation | Merged |
| [SpiroGanas/ADHD_MCP#3](https://github.com/SpiroGanas/ADHD_MCP/pull/3) | Phases 1 and 2: walking skeleton, FHIR access layer, terminology and personas | Merged |
| [SpiroGanas/ADHD_MCP#4](https://github.com/SpiroGanas/ADHD_MCP/pull/4) | Phase 3: evidence tools I | Merged |
| [SpiroGanas/ADHD_MCP#5](https://github.com/SpiroGanas/ADHD_MCP/pull/5) | Phases 4-6: evidence tools II, rules engine and recommendation, audit, privacy and security | Merged |
| [SpiroGanas/ADHD_MCP#6](https://github.com/SpiroGanas/ADHD_MCP/pull/6) | Phase 7: evaluation, hardening and release candidate 1.0.0rc1 (relabelled 0.9.0 by peer review 01) | Merged |
| [SpiroGanas/ADHD_MCP#7](https://github.com/SpiroGanas/ADHD_MCP/pull/7) | Phase 8: VA readiness and extensibility | Merged |
| [SpiroGanas/ADHD_MCP#8](https://github.com/SpiroGanas/ADHD_MCP/pull/8) | Peer review 01: findings only, no code changes | Merged |
| [SpiroGanas/ADHD_MCP#9](https://github.com/SpiroGanas/ADHD_MCP/pull/9) | Peer review 01 fixes | Merged (no recorded review) |
| [SpiroGanas/ADHD_MCP#10](https://github.com/SpiroGanas/ADHD_MCP/pull/10) | Hand-off documents: review checklist, user guide, clinician quick start | Open |
