# Contributing

This guide applies to human developers and AI agents alike. AI agents must also follow [CLAUDE.md](CLAUDE.md).

## Before you start

1. Read [status.md](status.md) to see what is done and what is next.
2. Read the current phase in [project_plan.md](project_plan.md).
3. Skim [docs/architecture.md](docs/architecture.md) and the [decision records](docs/adr/README.md).
4. If anything is unclear, ask the project owner before writing code.

## Ground rules

- **Never commit real patient data**, real identifiers or credentials. All test data is synthetic. The synthetic-data guard (`scripts/check_synthetic_data.py`; its rules are in the file's docstring) requires every FHIR resource in JSON that describes a person or carries a name or identifier to have the `HTEST` tag, the `urn:adhd-mcp:synthetic-id` identifier system and the family name `Synthetic`, and it fails on SSN-shaped numbers, JSON it cannot parse and any FHIR XML (store FHIR data as JSON). To run it before every commit, install the pre-commit hook once from the root of your clone: `ln -s ../../scripts/pre-commit .git/hooks/pre-commit`.
- The software recommends referral for screening. It never diagnoses, and nothing in the code, tests or documents may say otherwise.
- Tools are read-only.
- Clinical content (codes, cutoffs, weights, wording) changes only through a clinical content change issue and with the project owner's approval.

## Workflow

1. **Pick a work item** from the current phase, or open an issue using a template.
2. **Create a branch** from the default branch.
3. **Work test-first.** Write a failing test, make it pass, refactor. See the [TDD rules](project_plan.md#test-driven-development-rules).
4. **Keep changes small.** One work item per pull request where practical.
5. **Run all checks locally** with `./scripts/check` (lint, format, types, synthetic-data guard, tests) before pushing. Every command is listed in [CLAUDE.md](CLAUDE.md#commands).
6. **Update documentation** in the same pull request: [status.md](status.md) always; architecture, rule card or an ADR when relevant.
7. **Open a pull request** using the template and complete its checklist.
8. **Follow it through.** Fix CI failures and respond to review until it is merged.

## Commits

- Write the subject in the imperative: "Add safety gate boundary tests".
- Explain why in the body when the reason is not obvious.
- Keep a test fix that corrects a wrong test in its own commit, with the reason.

## Tests

- Every behavior has a test that was written first.
- Do not skip, weaken or delete a test to get a green run.
- Changing a contract snapshot is a deliberate act; say why in the pull request.
- New rules need personas: one that triggers, one that narrowly misses, one that is excluded.
- A change to a ruleset, the signal catalog, a value set, a drug class or the evaluation cohort needs a regenerated evaluation report (`uv run python scripts/evaluate_ruleset.py`); a test fails until it is.
- A change to a tool contract needs regenerated snapshots and tool reference (`UPDATE_SNAPSHOTS=1 uv run pytest tests/contract`, then `uv run python scripts/build_tool_reference.py`).

## Releases

Versioning and the release steps are in [ADR 0013](docs/adr/0013-versioning-and-release.md). Add each change to the `Unreleased` section of [CHANGELOG.md](CHANGELOG.md). Before a tag, `uv run python scripts/release_check.py` must pass; only the project owner tags a release.

## Decisions

A decision that would be costly to reverse gets an [ADR](docs/adr/README.md) in the same pull request.

## Reporting a security or privacy problem

Do not open a public issue. Contact the repository owner privately through GitHub.
