# Contributing

This guide applies to human developers and AI agents alike. AI agents must also follow [CLAUDE.md](CLAUDE.md).

## Before you start

1. Read [status.md](status.md) to see what is done and what is next.
2. Read the current phase in [project_plan.md](project_plan.md).
3. Skim [docs/architecture.md](docs/architecture.md) and the [decision records](docs/adr/README.md).
4. If anything is unclear, ask the project owner before writing code.

## Ground rules

- **Never commit real patient data**, real identifiers or credentials. All test data is synthetic.
- The software recommends referral for screening. It never diagnoses, and nothing in the code, tests or documents may say otherwise.
- Tools are read-only.
- Clinical content (codes, cutoffs, weights, wording) changes only through a clinical content change issue and with the project owner's approval.

## Workflow

1. **Pick a work item** from the current phase, or open an issue using a template.
2. **Create a branch** from the default branch.
3. **Work test-first.** Write a failing test, make it pass, refactor. See the [TDD rules](project_plan.md#test-driven-development-rules).
4. **Keep changes small.** One work item per pull request where practical.
5. **Run all checks locally** (tests, lint, type check) before pushing. The commands are in CLAUDE.md once Phase 1 defines them.
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

## Decisions

A decision that would be costly to reverse gets an [ADR](docs/adr/README.md) in the same pull request.

## Reporting a security or privacy problem

Do not open a public issue. Contact the repository owner privately through GitHub.
