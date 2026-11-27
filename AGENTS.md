# AGENTS.md

Entry point for AI coding agents other than Claude Code. The working rules for this repository are in [CLAUDE.md](CLAUDE.md) and apply to every agent. Read that file in full before doing anything.

The short version:

1. Read [status.md](status.md) first and resume from "Next steps".
2. Ask the project owner whenever a requirement is unclear. Do not guess.
3. Work test-first, following [project_plan.md](project_plan.md#test-driven-development-rules).
4. Keep status.md up to date as work progresses.
5. When the work is done, open a pull request and follow it through CI and review.
6. Respect the hard rules: never diagnose, read-only, safety gate first, evidence for every claim, synthetic data only, no clinical content in logs.

Where things are:

| Need | Document |
|---|---|
| What to build next | [status.md](status.md), [project_plan.md](project_plan.md) |
| How the system fits together | [docs/architecture.md](docs/architecture.md) |
| Why a decision was made | [docs/adr/](docs/adr/README.md) |
| Clinical rules and limits | [docs/clinical/](docs/clinical/) |
| Clinical evidence | [research/](research/) |
| How the rules and the tools were evaluated | [docs/evaluation/](docs/evaluation/README.md) |
| Running and configuring the server | [README.md](README.md), [docs/guide/](docs/guide/configuration.md) |
| Contribution workflow and releases | [CONTRIBUTING.md](CONTRIBUTING.md), [CHANGELOG.md](CHANGELOG.md) |
