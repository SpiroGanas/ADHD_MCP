# Project Status

Read this first. Update it whenever the state of the work changes (rules in [CLAUDE.md](CLAUDE.md#keep-statusmd-current)).

**Last updated:** 2026-11-27
**Current phase:** Phase 7 (evaluation, hardening, release preparation) in progress (owner request 2026-11-27: "program phase 7").
**Branch:** `ccr-5c748898-yqc67t`

## Summary

A FastMCP 4.2 server with ten read-only tools (tool contract 0.3.0): `get_server_info`; seven evidence tools (`check_safety_gate`, `get_mh_problem_list`, `get_screening_history`, `check_existing_care`, `get_medication_timeline`, `get_utilization_summary`, `get_psychosocial_context`); `assess_referral_need`, which runs the safety gate first and applies ADHD ruleset 1.0.0 (draft) to an evidence-linked signal catalog; and `draft_referral_proposal` (a ServiceRequest draft, never stored). Also MCP resources (ruleset, catalog, value sets, drug classes, instruments, intended use) and two clinician prompts. Every call is audited (references and hashes only); a sensitive-data policy cites or withholds substance use, HIV and sickle-cell data; the server runs over stdio or over HTTP as an OAuth resource server, and reads FHIR with SMART backend-services credentials. 14 synthetic personas specify expected outcomes; all match.

## Done

- PR #5 (Phases 4 to 6) merged into `main`.
- **Phase 6** (all nine work items; [SpiroGanas/ADHD_MCP#5](https://github.com/SpiroGanas/ADHD_MCP/pull/5)): audit record and JSON Lines sink, one record per call including failures ([ADR 0011](docs/adr/0011-audit-tracing-and-privacy.md)); trace id from `_meta.traceparent`, sent to FHIR as `traceparent`; sensitive-data policy (`data/privacy.toml`, default cite, HL7 labels verified); OAuth resource server with per-tool scopes and RFC 9728 metadata; SMART backend services ([ADR 0012](docs/adr/0012-authentication.md)); streamable HTTP transport and validated configuration (`src/adhd_mcp/config.py`); [threat model](docs/security/threat_model.md) and risk register review; injection twin test. Standing invariant 5 (canary test) added. PyJWT and cryptography pinned (ADR 0006).
- **Phase 5** (all ten work items; [SpiroGanas/ADHD_MCP#5](https://github.com/SpiroGanas/ADHD_MCP/pull/5)): ruleset format and engine ([ADR 0010](docs/adr/0010-rulesets-engine-and-plugins.md)); ADHD ruleset 1.0.0 (draft); scorer slot (rules-only); condition plugins; `assess_referral_need`; `draft_referral_proposal`; resources; prompts; [rule card](docs/clinical/rule_card_adhd_1.0.md); [walkthrough](docs/demo/assessment_walkthrough.md). Golden tests and snapshots for 14 personas; rules, orchestration and conditions at 100% branch coverage.
- **Phase 4** (all six work items; [SpiroGanas/ADHD_MCP#5](https://github.com/SpiroGanas/ADHD_MCP/pull/5)): `get_medication_timeline` with RxNorm classes curated and verified against RxNav 02-Nov-2026 ([ADR 0009](docs/adr/0009-rxnorm-drug-classes.md)); `get_utilization_summary`; `get_psychosocial_context`; [signal catalog](src/adhd_mcp/data/adhd/signal_catalog.toml); per-request FHIR cache; verification sprint 3.
- **Phases 1 to 3** ([SpiroGanas/ADHD_MCP#3](https://github.com/SpiroGanas/ADHD_MCP/pull/3), [SpiroGanas/ADHD_MCP#4](https://github.com/SpiroGanas/ADHD_MCP/pull/4)): walking skeleton, FHIR access layer, terminology, personas, the four Phase 3 evidence tools. Research and planning in [SpiroGanas/ADHD_MCP#1](https://github.com/SpiroGanas/ADHD_MCP/pull/1) and [SpiroGanas/ADHD_MCP#2](https://github.com/SpiroGanas/ADHD_MCP/pull/2).

## In progress

- Phase 7 on branch `ccr-5c748898-yqc67t`. Done on the branch: item 6 (fault injection; the HTTP adapter now fails a search on a malformed Bundle instead of crashing), items 1 to 3 (labelled cohort of 184 patients in `tests/evals/cohort.py`, harness, generated report [docs/evaluation/adhd_ruleset_1.0.0.md](docs/evaluation/adhd_ruleset_1.0.0.md), [sex-balance review](docs/evaluation/sex_balance_review.md)). Next: item 4 (model-in-the-loop harness, scripted stand-in model), item 7 (performance), items 8 and 9 (documentation, release preparation).

## Next steps

1. Continue Phase 7 on the branch (see In progress).
2. Project owner reviews, then approves or changes: the signal catalog (`reviewed_by_owner = false`), the rule card, the drafted clinician wording in `src/adhd_mcp/data/wording.toml` (`[recommendations]`, `[notes]`, next steps), the drug-class curation choices (ADR 0009), and the medication parameters (30-day supply, gap and fill window). Releasing ruleset 1.0.0 then means status `released` plus a pinned hash in `data/released_rulesets.toml`.

## Open questions for the project owner

| # | Question | Needed by |
|---|---|---|
| 1 | Who reviews and approves clinical content (rule cards, signal catalog)? Is there a clinician adviser? (For now the owner waived the human spot-check until release.) | Phase 7 |
| 4 | Is model API access and budget available for the model-in-the-loop evaluation? | Phase 7 |
| 5 | Will VA Lighthouse sandbox access be requested, and by whom? | Phase 8 |
| 6 | Should a priority tier be part of the 1.0 output? (Proposal: no; not built.) | Phase 7 |
| 9 | PC-PTSD-5 cutoff: 4 (current National Center for PTSD default) or 3? | Before LOINC verification (F2) |
| 12 | How should ASRS results be recognised in FHIR data (follow-up F3)? | Phase 7 |
| 14 | Verify LOINC through a LOINC account (fhir.loinc.org) or NLM's redistribution? Until then PHQ-9 item 9 and C-SSRS checks are "not performed", no screening cutoff is applied, and no ruleset signal uses a screening score | Before release |
| 15 | Approve the invariant-4 exception: the SMART token request is the one POST in the code (to the OAuth token endpoint, never the FHIR server) | PR review |
| 16 | Sex balance: ruleset 1.0.0 flags 8 of 40 internalizing suggestive presentations against 32 of 32 externalizing ones. Choose an option from the [sex-balance review](docs/evaluation/sex_balance_review.md): A no change (proposed for 1.0.0), B a sex-blind "four or more modifiers" rule as draft ruleset 1.1.0, or another | Before release |

## Decisions

Scope decisions made 2026-11-26 are recorded in [project_plan.md](project_plan.md#scope). Architecture decisions are in [docs/adr/](docs/adr/README.md).

Owner decisions 2026-11-27 (start of Phase 7):

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
- Ruleset 1.0.0 is a draft and not clinically validated; women are likely under-flagged (p02).
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
