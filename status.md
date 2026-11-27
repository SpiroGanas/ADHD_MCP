# Project Status

Read this first. Update it whenever the state of the work changes (rules in [CLAUDE.md](CLAUDE.md#keep-statusmd-current)).

**Last updated:** 2026-11-27
**Current phase:** Phases 4, 5 and 6 in progress on one branch (owner request 2026-11-27: "program phases 4, 5 and 6").
**Branch:** `claude/bold-tesla-bf2rn1`

## Summary

A FastMCP 4.2 server exposes five read-only tools: `get_server_info` and the Phase 3 evidence tools `check_safety_gate`, `get_mh_problem_list`, `get_screening_history` and `check_existing_care` (tool contract 0.2.0). Underneath: a read-only FHIR port (fixture and HTTP adapters; searches return server warnings), normalization, a typed reader, a terminology store (34 ICD-10-CM value sets verified against FY2027; six instruments with unverified LOINC codes and cutoffs), a per-site local code mapping (synthetic site only), and one evidence assembler per tool with clinical definitions in data files. Ten synthetic personas specify expected outcomes. No referral rule exists yet (Phase 5).

## Done

- **Phase 3** (all six work items; [SpiroGanas/ADHD_MCP#4](https://github.com/SpiroGanas/ADHD_MCP/pull/4)): `check_safety_gate` with rule card draft ([rule_card_safety_gate.md](docs/clinical/rule_card_safety_gate.md)); `get_mh_problem_list`; `get_screening_history`; `check_existing_care`; shared tool behavior (context injection, validation, error codes, completeness notes); tool descriptions. Standing invariant 2 as property tests. Safety gate module at 100% branch coverage. Port returns OperationOutcome warnings (open question 13). F1 automated part done (FY2027, CDC download).
- Research report; planning and documentation set ([SpiroGanas/ADHD_MCP#2](https://github.com/SpiroGanas/ADHD_MCP/pull/2)).
- **Phase 1** (all eight work items; [SpiroGanas/ADHD_MCP#3](https://github.com/SpiroGanas/ADHD_MCP/pull/3)): tooling pinned in [ADR 0006](docs/adr/0006-tooling-versions.md); package layout; CI with lint, types, tests, coverage floor 90%, gitleaks and a synthetic-data guard; `get_server_info` walking skeleton; test harness (in-memory MCP client, fixed clock, contract snapshots in `tests/contract/snapshots/`); domain models (`src/adhd_mcp/models/domain.py`); diagnostic-wording guard (`src/adhd_mcp/data/wording.toml`, `tests/helpers/wording.py`); verification sprint part 1. Standing invariants 1, 3, 4 and 6 exist as tests.
- **Phase 2** (all nine work items; [SpiroGanas/ADHD_MCP#3](https://github.com/SpiroGanas/ADHD_MCP/pull/3)): FHIR port and fixture adapter; HTTP adapter (httpx2, GET only, paging, retries, origin-pinned paging); normalization ([ADR 0007](docs/adr/0007-fhir-modeling.md)); terminology store; persona catalog ([tests/personas/](tests/personas/README.md)); bulk generator ([docs/dev/synthetic_population.md](docs/dev/synthetic_population.md)); local HAPI FHIR server and CI integration job ([docs/dev/local_fhir_server.md](docs/dev/local_fhir_server.md)); verification sprint part 2. Also a typed reader (`src/adhd_mcp/fhir/reader.py`) for later phases.
- Verification: every ICD-10-CM item in the backlog is Verified or Corrected against the official FY2027 tabular from CDC (and FY2026); seven research values corrected. See [verification_backlog.md](docs/clinical/verification_backlog.md).

## In progress

- Phase 4 (evidence tools II), then Phase 5 (rules engine) and Phase 6 (audit, privacy, security). One PR for all three, a commit per work item.

## Next steps

1. Phase 4, work item 1, `get_medication_timeline`: write ADR 0009 (curated RxNorm ingredient lists, verified against RxNav), the drug-class data files, then the assembler test-first.

## Open questions for the project owner

| # | Question | Needed by |
|---|---|---|
| 1 | Who reviews and approves clinical content (rule cards, signal catalog)? Is there a clinician adviser? (For now the owner waived the human spot-check until release.) | Phase 7 |
| 4 | Is model API access and budget available for the model-in-the-loop evaluation? | Phase 7 |
| 5 | Will VA Lighthouse sandbox access be requested, and by whom? (Apply during Phase 6.) | Phase 8 |
| 6 | Should a priority tier be part of the 1.0 output? (Proposal: no.) | Phase 5 |
| 9 | PC-PTSD-5 cutoff: 4 (current National Center for PTSD default) or 3 (research value; more sensitive, e.g. for women)? | Before LOINC verification (F2) |
| 12 | How should ASRS results be recognised in FHIR data, given no LOINC score code was found (follow-up F3)? Phase 3 lets a site map its ASRS questionnaire | Phase 5 |
| 14 | Verify LOINC through a LOINC account (fhir.loinc.org) or NLM's redistribution? Until then PHQ-9 item 9 and C-SSRS checks are "not performed" and no screening cutoff is applied | Before release |

## Decisions

Scope decisions made 2026-11-26 are recorded in [project_plan.md](project_plan.md#scope). Architecture decisions are in [docs/adr/](docs/adr/README.md).

Owner decisions 2026-11-26 (start of Phase 1):

- Tooling: Python 3.12, uv, pytest, ruff, mypy strict, FastMCP 4.x pinned (ADR 0006).
- FHIR modeling: narrow internal Pydantic models; `fhir.resources` only in tests to validate persona bundles (ADR 0007).
- Verification sprints: the agent checks codes against authoritative public sources and may mark them Verified, recording source, version and date.
- Phases 1 and 2 ship as one PR with a commit per work item.
- Bulk synthetic data: in-repo seeded generator, built on demand, not committed; Synthea not added (2026-11-26).
- Local FHIR server: HAPI FHIR `v8.12.0-2`, in memory (2026-11-26).

Owner decisions 2026-11-27 (start of Phases 4 to 6):

- Drug classes: hand-curated RxNorm ingredient lists per class, verified against RxNav (rxnav.nlm.nih.gov added to the environment), expanded to product codes by a script and committed as data (ADR 0009).
- ADHD ruleset 1.0 uses the proposed defaults: recommend when at least one high-weight signal occurs with two or more modifiers, or two or more high-weight classes, all within 1095 days of the as-of date. High: stimulant-related disorder, alcohol (F10, Y90.1-Y90.9, R78.0), crash as driver, two or more accidental-injury visits within 730 days. TBI adds a neuropsychological-evaluation note and does not count toward referral. Modifiers: other SUD, PTSD, IED, depression or anxiety, three or more distinct antidepressants, BPD, insomnia, attention-symptom codes, legal, education or occupation, housing, family history. All marked inference in the rule card (open question 6 is still open; no priority tier).
- Sensitive-data default (open question 3): cite existence and date only; rules still use the signal; the output states the category was restricted.
- Signal boundaries (open questions 10, 11): value sets kept as verified (no F13/F16/F18; F15 whole; Y90.0 excluded from the alcohol signal; e-bike drivers counted; F32.81 kept; no G47.09; Z55/Z56 whole; housing = Z59.0 and Z59.81).
- PyJWT and cryptography become direct pinned dependencies for Phase 6 authentication.
- Phases 4 to 6 ship as one PR with a commit per work item.

Owner decisions 2026-11-27 (start of Phase 3):

- A personal cloud environment "ADHD_MCP" allows cdc.gov, cms.gov, ptsd.va.gov, healthquality.va.gov and loinc.org (open question 7). loinc.org still blocks automated access.
- LOINC stays unverified for now (follow-up F2); LOINC-based checks are reported as not performed.
- Human spot-check of `safety.*` value sets (F1) waived for synthetic-only development; a Phase 7 release blocker.
- Safety gate never says plain "clear" unless every check ran: a positive check gives `positive`; otherwise a load failure gives `data_unavailable`; a check not performed or an empty record gives `clear_limited_data`.
- Look-back (open question 2): coded self-harm signals and screens count if dated within 365 days of the as-of date; undated items count; older items are listed as history but do not make the gate positive. Active high-risk flags count while active. Discharge windows 90 days (highest priority) and 365 days.
- Asphyxiation self-harm codes T71.1x2/T71.2x2 count in the gate (open question 8).
- Psychiatric inpatient and residential encounters, high-risk flags and ADHD evaluation requests are recognised through a per-site code mapping data file; only the synthetic code system is mapped now.
- An ADHD referral or evaluation excludes when open (active, on-hold, draft) or completed within 365 days; revoked or older ones are reported only.
- The FHIR port returns OperationOutcome warnings so outputs disclose incomplete data (open question 13).

## Known gaps and cautions

- LOINC codes and all cutoffs are unverified, so strict loading refuses every instrument. ICD-10-CM is verified against FY2027 (2026-11-27); the human spot-check is still owed before release.
- ICD-10-CM codes sent without a dot (for example `F1510`) do not match value sets; recorded in ADR 0007 for Phase 8.
- Persona RxNorm codes are illustrative test data; the drug-class source is decided in Phase 4 (ADR 0009).
- `fhir.resources` validates personas against R4B models (no R4 package exists for version 8); the live HAPI R4 load covers R4 validity.

## Pull requests

| PR | Subject | State |
|---|---|---|
| [SpiroGanas/ADHD_MCP#1](https://github.com/SpiroGanas/ADHD_MCP/pull/1) | Research report | Merged |
| [SpiroGanas/ADHD_MCP#2](https://github.com/SpiroGanas/ADHD_MCP/pull/2) | Project plan, architecture and working documentation | Merged |
| [SpiroGanas/ADHD_MCP#3](https://github.com/SpiroGanas/ADHD_MCP/pull/3) | Phases 1 and 2: walking skeleton, FHIR access layer, terminology and personas | Merged |
| [SpiroGanas/ADHD_MCP#4](https://github.com/SpiroGanas/ADHD_MCP/pull/4) | Phase 3: evidence tools I | Merged |
