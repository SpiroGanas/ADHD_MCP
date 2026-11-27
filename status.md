# Project Status

Read this first. Update it whenever the state of the work changes (rules in [CLAUDE.md](CLAUDE.md#keep-statusmd-current)).

**Last updated:** 2026-11-26
**Current phase:** Phases 1 and 2 code complete, in one pull request awaiting CI and review. Phase 3 (Evidence tools I) is next.
**Branch:** `claude/intelligent-sagan-imj1bh`

## Summary

A FastMCP 4.2 server exposes one read-only tool, `get_server_info`. The FHIR access layer is complete: a read-only port with fixture and HTTP adapters (both pass one shared suite, the HTTP adapter also against a live HAPI FHIR server), normalization to typed records, a typed record reader, and a terminology store with 33 verified ICD-10-CM value sets and six screening instruments (LOINC codes and cutoffs still unverified). Ten synthetic personas specify expected outcomes. No clinical tool or rule exists yet.

## Done

- Research report; planning and documentation set ([SpiroGanas/ADHD_MCP#2](https://github.com/SpiroGanas/ADHD_MCP/pull/2)).
- **Phase 1** (all eight work items; [SpiroGanas/ADHD_MCP#3](https://github.com/SpiroGanas/ADHD_MCP/pull/3)): tooling pinned in [ADR 0006](docs/adr/0006-tooling-versions.md); package layout; CI with lint, types, tests, coverage floor 90%, gitleaks and a synthetic-data guard; `get_server_info` walking skeleton; test harness (in-memory MCP client, fixed clock, contract snapshots in `tests/contract/snapshots/`); domain models (`src/adhd_mcp/models/domain.py`); diagnostic-wording guard (`src/adhd_mcp/data/wording.toml`, `tests/helpers/wording.py`); verification sprint part 1. Standing invariants 1, 3, 4 and 6 exist as tests.
- **Phase 2** (all nine work items; [SpiroGanas/ADHD_MCP#3](https://github.com/SpiroGanas/ADHD_MCP/pull/3)): FHIR port and fixture adapter; HTTP adapter (httpx2, GET only, paging, retries, origin-pinned paging); normalization ([ADR 0007](docs/adr/0007-fhir-modeling.md)); terminology store; persona catalog ([tests/personas/](tests/personas/README.md)); bulk generator ([docs/dev/synthetic_population.md](docs/dev/synthetic_population.md)); local HAPI FHIR server and CI integration job ([docs/dev/local_fhir_server.md](docs/dev/local_fhir_server.md)); verification sprint part 2. Also a typed reader (`src/adhd_mcp/fhir/reader.py`) for later phases.
- Verification: every ICD-10-CM item in the backlog is Verified or Corrected against the official FY2026 tabular; seven research values corrected. See [verification_backlog.md](docs/clinical/verification_backlog.md).

## In progress

- Phases 1 and 2 pull request [SpiroGanas/ADHD_MCP#3](https://github.com/SpiroGanas/ADHD_MCP/pull/3): waiting for CI (first run of the CI and integration workflows) and review. The clinical safety review is done; its two blocking findings and most minor ones are fixed (see the PR description).

## Next steps

1. Watch the PR through CI and review; fix anything that fails.
2. Project owner: make the CI checks required for merge on `main` (repository settings; Phase 1 exit criterion the agent cannot set). Answer open questions 1, 2 and 7 to 12 below.
3. Phase 3, work item 1, `check_safety_gate`. First write the persona expectations (p03 positive; p07 and p08 `clear_limited_data`; others clear) and a rule card draft, then the first failing test: an evidence assembler returns a positive gate citing `p03-cond-1` for R45.851, using `PatientRecords.conditions(..., value_set=load_value_set("safety.suicidal_ideation"))`. LOINC-based checks (PHQ-9 item 9, C-SSRS) cannot be active until follow-up F2 verifies those codes, and no `safety.*` value set may be used in an active check until follow-up F1 (FY2027, hash comparison, human spot-check) is done. Do not use `since` on safety-gate Condition searches: it drops conditions without a recordedDate.

## Open questions for the project owner

| # | Question | Needed by |
|---|---|---|
| 1 | Who reviews and approves clinical content (rule cards, signal catalog)? Is there a clinician adviser? | Phase 3 |
| 2 | Look-back windows for each safety gate signal: how long does a positive stay "current"? | Phase 3 |
| 3 | Default sensitive-data policy for substance-use and other specially protected data (proposal: cite existence and date only) | Phase 6 |
| 4 | Is model API access and budget available for the model-in-the-loop evaluation? | Phase 7 |
| 5 | Will VA Lighthouse sandbox access be requested, and by whom? (Apply during Phase 6.) | Phase 8 |
| 6 | Should a priority tier be part of the 1.0 output? (Proposal: no.) | Phase 5 |
| 7 | Allow network access to loinc.org, cdc.gov (incl. ftp.cdc.gov) and cms.gov, so LOINC codes can be verified directly and ICD-10-CM re-checked against FY2027 (follow-ups F1, F2)? Without it, no LOINC-based safety check can be active | Phase 3 |
| 8 | Should the safety gate also use the intentional self-harm asphyxiation codes T71.1x2/T71.2x2 found during verification (`safety.self_harm_asphyxiation`)? Proposal: yes | Phase 3 |
| 9 | PC-PTSD-5 cutoff: 4 (current National Center for PTSD default) or 3 (research value; more sensitive, e.g. for women)? | Phase 3 |
| 10 | Substance codes: include F13 (sedatives), F16 (hallucinogens), F18 (inhalants)? Count caffeine (F15 includes it)? Exclude Y90.0 (blood alcohol under 20 mg/100 ml)? | Phase 4 |
| 11 | Other signal boundaries: count electric-bicycle drivers in V20-V29? Keep F32.81 (premenstrual dysphoric disorder) inside the depression family? Add G47.09 (other insomnia)? Use an explicit subset of Z55/Z56 rather than whole categories? Which housing codes count: homelessness Z59.0, housing instability Z59.81, inadequate housing Z59.1? | Phase 4 |
| 12 | How should ASRS results be recognised in FHIR data, given no LOINC score code was found (follow-up F3)? | Phase 3 |
| 13 | FHIR servers can return OperationOutcome warnings in a search (for example truncated or withheld results). Today the port returns only a list and drops them. Change the port to return them so outputs can disclose incomplete data? Proposal: yes, before the Phase 3 data-completeness note. This changes the port interface | Phase 3 |

## Decisions

Scope decisions made 2026-11-26 are recorded in [project_plan.md](project_plan.md#scope). Architecture decisions are in [docs/adr/](docs/adr/README.md).

Owner decisions 2026-11-26 (start of Phase 1):

- Tooling: Python 3.12, uv, pytest, ruff, mypy strict, FastMCP 4.x pinned (ADR 0006).
- FHIR modeling: narrow internal Pydantic models; `fhir.resources` only in tests to validate persona bundles (ADR 0007).
- Verification sprints: the agent checks codes against authoritative public sources and may mark them Verified, recording source, version and date.
- Phases 1 and 2 ship as one PR with a commit per work item.
- Bulk synthetic data: in-repo seeded generator, built on demand, not committed; Synthea not added (2026-11-26).
- Local FHIR server: HAPI FHIR `v8.12.0-2`, in memory (2026-11-26).

## Known gaps and cautions

- LOINC codes and all cutoffs are unverified (only search summaries were reachable), so strict loading refuses every instrument. ICD-10-CM was verified against FY2026, not FY2027 (follow-up F1).
- ICD-10-CM codes sent without a dot (for example `F1510`) do not match value sets; recorded in ADR 0007 for Phase 8.
- Persona RxNorm codes are illustrative test data; the drug-class source is decided in Phase 4 (ADR 0008).
- `fhir.resources` validates personas against R4B models (no R4 package exists for version 8); the live HAPI R4 load covers R4 validity.

## Pull requests

| PR | Subject | State |
|---|---|---|
| [SpiroGanas/ADHD_MCP#1](https://github.com/SpiroGanas/ADHD_MCP/pull/1) | Research report | Merged |
| [SpiroGanas/ADHD_MCP#2](https://github.com/SpiroGanas/ADHD_MCP/pull/2) | Project plan, architecture and working documentation | Merged |
| [SpiroGanas/ADHD_MCP#3](https://github.com/SpiroGanas/ADHD_MCP/pull/3) | Phases 1 and 2: walking skeleton, FHIR access layer, terminology and personas | Open |
