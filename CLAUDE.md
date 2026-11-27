# CLAUDE.md

Working rules for Claude Code in this repository. Other AI agents should follow the same rules (see [AGENTS.md](AGENTS.md)).

## The project in one paragraph

ADHD_MCP is a Python MCP server built with FastMCP. It reads FHIR R4 data and returns an evidence-linked recommendation on whether a clinician should consider referring a patient for formal adult ADHD screening. It recommends referral; it never diagnoses. The design is rules-first, read-only, and synthetic-data-only during development.

## Start of every session

1. **Read [status.md](status.md) first.** It says what is done, what is in progress, and what to do next. Trust it over your own assumptions and resume from "Next steps".
2. Read the current phase in [project_plan.md](project_plan.md).
3. Read other documents only as the task needs them:
   - [docs/architecture.md](docs/architecture.md) before changing structure or tool contracts
   - [docs/adr/](docs/adr/README.md) before revisiting a settled decision
   - [docs/clinical/](docs/clinical/) before touching rules, codes, cutoffs or output wording
   - [research/](research/) for clinical evidence (large files; search them, do not read them whole)

If status.md disagrees with the repository, say so, fix status.md, then continue.

## Ask when unsure

**Always ask the user when clarification is needed.** Do not guess at requirements. Ask in particular before:

- choosing between designs that are costly to reverse
- changing a tool's name, inputs or output schema
- changing clinical content: codes, value sets, cutoffs, rule weights, recommendation wording
- adding a dependency or an external service
- doing anything the plan does not cover, or that contradicts the plan or an ADR
- acting on a requirement that can be read two ways

Ask focused questions with concrete options and a recommendation. Keep working on anything that does not depend on the answer.

## Keep status.md current

status.md is the project's memory between sessions. Create it if it is missing, and **update it whenever the state of the work changes**, at minimum:

- when a task starts (move it to "In progress")
- when a task finishes (move it to "Done", with the PR link)
- when a decision is made or a question is opened or answered
- before ending any session, even an unfinished one

Keep the existing section layout. Write it so that a new session with no other context can resume in under a minute: say exactly what the next action is, name the files and the failing test if there is one. Keep it short; move history older than the current phase into a one-line summary.

## Test-driven development

Follow the TDD rules in [project_plan.md](project_plan.md#test-driven-development-rules). In brief:

1. Write a failing test that states the behavior. Run it and see it fail for the right reason.
2. Write the least code that passes.
3. Refactor with the tests green.

- No production code without a test that required it.
- Never weaken, skip or delete a test to get a green run. If a test is wrong, say why and fix the test in its own commit.
- Unit tests use no network and no real clock.
- Clinical rules need a test for each branch, including the "do not recommend" cases.
- Run the full check suite (tests, lint, type check) before every commit, once Phase 1 defines the commands. Record those commands in the "Commands" section below.

## When programming is done

When the work for a task is complete and all checks pass:

1. Update status.md.
2. Commit with a clear message and push the branch.
3. **Create a pull request**, using [.github/pull_request_template.md](.github/pull_request_template.md).
4. **Watch the pull request**: subscribe to its activity, fix failing CI, and respond to review comments until it is merged or the user says to stop.
5. Record the PR link in status.md.

Documentation-only or planning-only sessions follow the same steps unless the user says otherwise.

## Hard rules

- **Never diagnose.** No output, prompt, log message or document may state or imply that a patient has ADHD. Use "consider referral for formal screening".
- **Read-only.** No tool writes to a FHIR server. `draft_referral_proposal` returns a draft and stores nothing.
- **Safety gate first.** No code path may return an ADHD recommendation without the safety gate result.
- **Evidence or silence.** Every signal in an output cites the FHIR resource ID it came from.
- **Synthetic data only.** Never commit real patient data, real identifiers or credentials. Fixtures must be obviously synthetic.
- **No clinical content in logs.** Log resource references and hashes, not values or note text.
- **Unverified clinical facts stay marked.** Many codes and cutoffs in the research are flagged unverified. Do not use one in a rule until it is checked off in [docs/clinical/verification_backlog.md](docs/clinical/verification_backlog.md).
- **Do not present the tool as clinically validated** anywhere.

## Conventions

- Python with FastMCP; tooling versions are pinned in Phase 1 and recorded in an ADR.
- MCP tools are thin wrappers. Logic lives in plain, separately testable modules (see the layout in [docs/architecture.md](docs/architecture.md)).
- Clinical knowledge (value sets, cutoffs, rule weights) lives in versioned data files, not in code.
- A decision that is costly to reverse gets an ADR in [docs/adr/](docs/adr/README.md).
- Check FastMCP and MCP specification documentation before relying on memory; both change quickly.
- Small, focused commits and pull requests: one plan work item per PR where practical.

## Commands

Defined in Phase 1 ([ADR 0006](docs/adr/0006-tooling-versions.md)). Requires [uv](https://docs.astral.sh/uv/).

| Purpose | Command |
|---|---|
| Install everything (runtime and dev) | `uv sync` |
| Full check suite (run before every commit) | `./scripts/check` |
| Tests only (unit, contract, tool) | `uv run pytest` |
| Start the local FHIR server | `docker compose up -d fhir` ([docs/dev/local_fhir_server.md](docs/dev/local_fhir_server.md)) |
| Integration tests (need the local FHIR server) | `uv run pytest -m integration` |
| Rebuild persona bundles after editing definitions | `uv run python scripts/build_personas.py` |
| Lint / format / type check | `uv run ruff check .` / `uv run ruff format .` / `uv run mypy` |
| Update contract snapshots (deliberate act) | `UPDATE_SNAPSHOTS=1 uv run pytest tests/contract` |
| Run the server over stdio | `uv run adhd-mcp` |
| Inspect the server | `uv run fastmcp inspect src/adhd_mcp/server.py:create_server` |

## Slash commands and subagents

| Command | Use |
|---|---|
| `/resume` | Read status.md and the current phase, then report where work stands and what is next |
| `/tdd-cycle` | Run one red-green-refactor cycle for a named behavior |
| `/update-status` | Bring status.md in line with the repository |
| `/finish-work` | Final checks, status update, commit, push, create and watch the PR |

The `clinical-safety-reviewer` subagent reviews a change against the hard rules above. Use it before opening a PR that touches rules, outputs or logging.
