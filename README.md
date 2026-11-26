# ADHD_MCP

An MCP server that reads a patient's FHIR record and tells a clinician whether a formal adult ADHD screening should be considered, and why.

> **Status: planning.** No server code exists yet. This repository currently holds the research, architecture, and project plan that future developers and AI agents will build from. See [status.md](status.md) for the current state.

> **This tool recommends referral for screening. It never diagnoses.** It is decision support for clinicians, not a patient-facing product, and it is not validated for clinical use.

## What it does

Adult ADHD is under-diagnosed, especially in veterans, and it is associated with a higher risk of self-harm that treatment appears to reduce. An undiagnosed case rarely shows up as an ADHD code. It shows up as its consequences: stimulant or alcohol-related diagnoses, repeated accidental injuries, crashes, antidepressant switches, sleep problems.

The server assembles those signals from FHIR data, applies versioned and auditable rules, and returns a structured recommendation:

1. **Safety gate first.** Any self-harm signal (suicidal ideation codes, a positive C-SSRS, a recent psychiatric discharge) is surfaced before anything else and takes priority over an ADHD referral.
2. **Exclusions.** Patients who already have an ADHD diagnosis or an evaluation in progress are not flagged.
3. **Evidence-linked recommendation.** "Consider referral for formal ADHD screening" or "no recommendation", with every supporting signal tied to the FHIR resource it came from.
4. **Audit record.** Every call is logged with its inputs, rule version and output, so recommendations can be evaluated later.

The clinical basis is in [research/veteran_self_harm_risk_screening.md](research/veteran_self_harm_risk_screening.md).

## Design principles

| Principle | What it means |
|---|---|
| Recommend, never diagnose | Enforced in output schemas, wording, and tests |
| Deterministic rules first | The language model never navigates raw FHIR or decides eligibility; the server does the joins and rule evaluation |
| Read-only | Tools only read FHIR. The one exception drafts a referral proposal that is returned to the clinician and never written to the record |
| Evidence or silence | Every claim in an output cites a resource ID; nothing is asserted without a source |
| Safety gate before referral | Self-harm signals always take priority |
| Privacy by default | Synthetic data only in this repository; logs hold references and hashes, not clinical content |
| Test-driven | Every behavior starts as a failing test |

## Technology

- **Language:** Python
- **MCP framework:** [FastMCP](https://gofastmcp.com)
- **Data:** HL7 FHIR R4 (US Core profiles), synthetic data for all development and testing
- **Terminologies:** ICD-10-CM, LOINC, RxNorm, SNOMED CT

Exact versions and supporting libraries are chosen in Phase 1 and recorded as [architecture decision records](docs/adr/README.md).

## Planned MCP tools

| Tool | Purpose |
|---|---|
| `check_safety_gate` | Detect self-harm signals before any referral is considered |
| `get_screening_history` | Scores over time for PHQ-9, C-SSRS, AUDIT-C, PC-PTSD-5, ASRS |
| `get_mh_problem_list` | Mental health diagnoses with onset order |
| `get_medication_timeline` | Stimulant fills, antidepressant switches, sedative-hypnotics |
| `get_utilization_summary` | Emergency injury visits, discharges, no-shows |
| `get_psychosocial_context` | Housing, legal, occupational and military context |
| `check_existing_care` | Existing ADHD diagnosis, referrals, evaluations in progress |
| `assess_referral_need` | Run the rules and return the recommendation with its evidence |
| `draft_referral_proposal` | Draft a referral for clinician review; never written to the record |

Details are in [docs/architecture.md](docs/architecture.md).

## Roadmap

Eight phases of about one month each for a single developer. Full detail is in [project_plan.md](project_plan.md).

| Phase | Theme |
|---|---|
| 1 | Foundations and walking skeleton |
| 2 | FHIR access layer and synthetic patients |
| 3 | Evidence tools I: safety gate, diagnoses, screening history, existing care |
| 4 | Evidence tools II: medications, utilization, psychosocial context |
| 5 | Rules engine and the referral recommendation |
| 6 | Audit, privacy and security |
| 7 | Evaluation, hardening and release 1.0 |
| 8 | VA readiness and extensibility to other conditions |

## Repository guide

| Path | Contents |
|---|---|
| [project_plan.md](project_plan.md) | Phased, test-driven plan |
| [status.md](status.md) | Work done and next steps; updated every session |
| [CLAUDE.md](CLAUDE.md) | Working rules for Claude Code |
| [AGENTS.md](AGENTS.md) | Entry point for other AI coding agents |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Workflow for human and AI contributors |
| [docs/architecture.md](docs/architecture.md) | Components, data flow, tool contracts |
| [docs/adr/](docs/adr/README.md) | Architecture decision records |
| [docs/clinical/](docs/clinical/) | Intended use, risk register, rule card template, glossary, verification backlog |
| [research/](research/) | Evidence report and source notes |

## Getting started

There is nothing to install or run yet. Setup and run instructions will be added here when Phase 1 delivers the walking skeleton.

To contribute, read [CONTRIBUTING.md](CONTRIBUTING.md), then [status.md](status.md) for what is next.

## Data and privacy

Never commit real patient data, credentials, or anything derived from a real health record. All fixtures are synthetic. See the [intended use statement](docs/clinical/intended_use.md) and [risk register](docs/clinical/risk_register.md).

## License

[MIT](LICENSE)
