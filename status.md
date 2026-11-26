# Project Status

Read this first. Update it whenever the state of the work changes (rules in [CLAUDE.md](CLAUDE.md#keep-statusmd-current)).

**Last updated:** 2026-11-26
**Current phase:** Phase 1 (Foundations and walking skeleton) in progress; Phase 2 follows in the same PR.
**Branch:** `claude/intelligent-sagan-imj1bh`

## Summary

The repository holds research, planning and documentation only. No code, tooling or CI exists yet.

## Done

- Research report and source notes ([research/](research/)), merged earlier.
- Planning and documentation set (2026-11-26, [SpiroGanas/ADHD_MCP#2](https://github.com/SpiroGanas/ADHD_MCP/pull/2)): README, CLAUDE.md, AGENTS.md, CONTRIBUTING.md, project_plan.md, this file, architecture document, ADRs 0001 to 0005, clinical documents, GitHub templates, Claude Code commands and reviewer subagent.

## In progress

- Phase 1 and Phase 2, one PR with a commit per work item (owner decision 2026-11-26). Starting with Phase 1 work item 1 (tooling, ADR 0006).

## Next steps

1. Project owner answers the open questions below (questions 1 and 2 are needed by Phase 3).
2. Begin Phase 1, work item 1: choose and pin tooling (Python version, FastMCP version, package manager, test runner, linter, type checker). Check current FastMCP and MCP specification documentation first. Record the result as ADR 0006 and fill in the "Commands" section of CLAUDE.md.
3. Phase 1, work items 2 to 5: repository layout, CI, the `get_server_info` walking skeleton, and the test harness. First failing test: the server lists exactly one tool, `get_server_info`.

## Open questions for the project owner

| # | Question | Needed by |
|---|---|---|
| 1 | Who reviews and approves clinical content (rule cards, signal catalog)? Is there a clinician adviser? | Phase 3 |
| 2 | Look-back windows for each safety gate signal: how long does a positive stay "current"? | Phase 3 |
| 3 | Default sensitive-data policy for substance-use and other specially protected data (proposal: cite existence and date only) | Phase 6 |
| 4 | Is model API access and budget available for the model-in-the-loop evaluation? | Phase 7 |
| 5 | Will VA Lighthouse sandbox access be requested, and by whom? (Apply during Phase 6.) | Phase 8 |
| 6 | Should a priority tier be part of the 1.0 output? (Proposal: no.) | Phase 5 |

## Decisions

Scope decisions made 2026-11-26 are recorded in [project_plan.md](project_plan.md#scope). Architecture decisions are in [docs/adr/](docs/adr/README.md).

Owner decisions 2026-11-26 (start of Phase 1):

- Tooling: Python 3.12, uv, pytest, ruff, mypy strict, FastMCP 4.x pinned (ADR 0006).
- FHIR modeling: narrow internal Pydantic models; `fhir.resources` only in tests to validate persona bundles (ADR 0007).
- Verification sprints: the agent checks codes against authoritative public sources and may mark them Verified, recording source, version and date.
- Phases 1 and 2 ship as one PR with a commit per work item.

## Known gaps and cautions

- Most codes and cutoffs in the research report are unverified. See [docs/clinical/verification_backlog.md](docs/clinical/verification_backlog.md). None may be used in a rule until verified.
- The MCP specification and FastMCP versions named in the documents come from research notes and must be confirmed at the start of Phase 1.

## Pull requests

| PR | Subject | State |
|---|---|---|
| [SpiroGanas/ADHD_MCP#1](https://github.com/SpiroGanas/ADHD_MCP/pull/1) | Research report | Merged |
| [SpiroGanas/ADHD_MCP#2](https://github.com/SpiroGanas/ADHD_MCP/pull/2) | Project plan, architecture and working documentation | Merged |
