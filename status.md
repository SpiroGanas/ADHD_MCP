# Project Status

Read this first. Update it whenever the state of the work changes (rules in [CLAUDE.md](CLAUDE.md#keep-statusmd-current)).

**Last updated:** 2026-11-27
**Current phase:** Phase 3 (Evidence tools I), in progress.
**Branch:** `ccr-29d767ce-uqk8rh`

## Summary

A FastMCP 4.2 server exposes one read-only tool, `get_server_info`. The FHIR access layer is complete: a read-only port with fixture and HTTP adapters (both pass one shared suite, the HTTP adapter also against a live HAPI FHIR server), normalization to typed records, a typed record reader, and a terminology store with 33 verified ICD-10-CM value sets and six screening instruments (LOINC codes and cutoffs still unverified). Ten synthetic personas specify expected outcomes. No clinical tool or rule exists yet.

## Done

- Phases 1 and 2 merged ([SpiroGanas/ADHD_MCP#3](https://github.com/SpiroGanas/ADHD_MCP/pull/3)).
- Research report; planning and documentation set ([SpiroGanas/ADHD_MCP#2](https://github.com/SpiroGanas/ADHD_MCP/pull/2)).
- **Phase 1** (all eight work items; [SpiroGanas/ADHD_MCP#3](https://github.com/SpiroGanas/ADHD_MCP/pull/3)): tooling pinned in [ADR 0006](docs/adr/0006-tooling-versions.md); package layout; CI with lint, types, tests, coverage floor 90%, gitleaks and a synthetic-data guard; `get_server_info` walking skeleton; test harness (in-memory MCP client, fixed clock, contract snapshots in `tests/contract/snapshots/`); domain models (`src/adhd_mcp/models/domain.py`); diagnostic-wording guard (`src/adhd_mcp/data/wording.toml`, `tests/helpers/wording.py`); verification sprint part 1. Standing invariants 1, 3, 4 and 6 exist as tests.
- **Phase 2** (all nine work items; [SpiroGanas/ADHD_MCP#3](https://github.com/SpiroGanas/ADHD_MCP/pull/3)): FHIR port and fixture adapter; HTTP adapter (httpx2, GET only, paging, retries, origin-pinned paging); normalization ([ADR 0007](docs/adr/0007-fhir-modeling.md)); terminology store; persona catalog ([tests/personas/](tests/personas/README.md)); bulk generator ([docs/dev/synthetic_population.md](docs/dev/synthetic_population.md)); local HAPI FHIR server and CI integration job ([docs/dev/local_fhir_server.md](docs/dev/local_fhir_server.md)); verification sprint part 2. Also a typed reader (`src/adhd_mcp/fhir/reader.py`) for later phases.
- Verification: every ICD-10-CM item in the backlog is Verified or Corrected against the official FY2026 tabular; seven research values corrected. See [verification_backlog.md](docs/clinical/verification_backlog.md).

## In progress

- Phase 3, all six work items, on branch `ccr-29d767ce-uqk8rh` (one PR, a commit per work item).
  - Done on the branch: F1 automated part (FY2027 re-check, CDC download comparison).
  - Next: port returns OperationOutcome warnings (Q13), shared tool behavior and site code mapping, then the four tools in plan order.

## Next steps

1. Continue Phase 3 in this order: port warnings; shared tool behavior (`src/adhd_mcp/evidence/common.py`, `data/site_codes/`); `check_safety_gate`; `get_mh_problem_list`; `get_screening_history`; `check_existing_care`; invariant 2 property test; integration tests; rule card; PR.
2. Project owner: make the CI checks required for merge on `main` (repository settings). Answer open questions 1, 9, 12 below when convenient; none blocks Phase 3 code.

## Open questions for the project owner

| # | Question | Needed by |
|---|---|---|
| 1 | Who reviews and approves clinical content (rule cards, signal catalog)? Is there a clinician adviser? (For now the owner waived the human spot-check until release.) | Phase 7 |
| 3 | Default sensitive-data policy for substance-use and other specially protected data (proposal: cite existence and date only) | Phase 6 |
| 4 | Is model API access and budget available for the model-in-the-loop evaluation? | Phase 7 |
| 5 | Will VA Lighthouse sandbox access be requested, and by whom? (Apply during Phase 6.) | Phase 8 |
| 6 | Should a priority tier be part of the 1.0 output? (Proposal: no.) | Phase 5 |
| 9 | PC-PTSD-5 cutoff: 4 (current National Center for PTSD default) or 3 (research value; more sensitive, e.g. for women)? | Phase 3 |
| 10 | Substance codes: include F13 (sedatives), F16 (hallucinogens), F18 (inhalants)? Count caffeine (F15 includes it)? Exclude Y90.0 (blood alcohol under 20 mg/100 ml)? | Phase 4 |
| 11 | Other signal boundaries: count electric-bicycle drivers in V20-V29? Keep F32.81 (premenstrual dysphoric disorder) inside the depression family? Add G47.09 (other insomnia)? Use an explicit subset of Z55/Z56 rather than whole categories? Which housing codes count: homelessness Z59.0, housing instability Z59.81, inadequate housing Z59.1? | Phase 4 |
| 12 | How should ASRS results be recognised in FHIR data, given no LOINC score code was found (follow-up F3)? | Phase 3 |
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
- Persona RxNorm codes are illustrative test data; the drug-class source is decided in Phase 4 (ADR 0008).
- `fhir.resources` validates personas against R4B models (no R4 package exists for version 8); the live HAPI R4 load covers R4 validity.

## Pull requests

| PR | Subject | State |
|---|---|---|
| [SpiroGanas/ADHD_MCP#1](https://github.com/SpiroGanas/ADHD_MCP/pull/1) | Research report | Merged |
| [SpiroGanas/ADHD_MCP#2](https://github.com/SpiroGanas/ADHD_MCP/pull/2) | Project plan, architecture and working documentation | Merged |
| [SpiroGanas/ADHD_MCP#3](https://github.com/SpiroGanas/ADHD_MCP/pull/3) | Phases 1 and 2: walking skeleton, FHIR access layer, terminology and personas | Merged |
