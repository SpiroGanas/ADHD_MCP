# ADHD_MCP

An MCP server that reads a patient's FHIR record and tells a clinician whether a referral for formal adult ADHD screening may be worth considering, and why.

> **This tool recommends referral for screening. It never diagnoses.** It is decision support for licensed clinicians, not a patient-facing product, and it is **not clinically validated**: its rules are a starting heuristic from published research, tested only on synthetic data. See the [intended use statement](docs/clinical/intended_use.md) and [limitations](docs/limitations.md).

> **Status: 0.9.0, in development.** The planned features are built and tested on synthetic data only. No clinician has reviewed the rules, no real language model has used the tools, and no real FHIR server has been read. Version 1.0.0 waits for all three ([peer review 01](peer_review_01.md), G3). See [status.md](status.md) and the [change log](CHANGELOG.md).

## What it does

Adult ADHD is thought to be under-diagnosed (no estimate is veteran-specific; see [limitations](docs/limitations.md)), and it is associated with a higher risk of self-harm that treatment appears to reduce. An undiagnosed case rarely shows up as an ADHD code. It may show up instead as problems associated with ADHD, none specific to it: stimulant or alcohol-related diagnoses, repeated accidental injuries, crashes, antidepressant switches, sleep problems.

The server assembles those signals from FHIR data, applies versioned, auditable rules, and returns a structured result:

1. **Safety gate first.** Self-harm signals (suicidal ideation or self-harm codes, a recent psychiatric discharge, a high-risk flag) are reported before anything else and take priority over any ADHD referral.
2. **Exclusions.** Patients who already have an ADHD code, referral, evaluation or care plan are not flagged.
3. **Evidence-linked recommendation.** One of `consider_referral_for_formal_screening`, `no_recommendation`, `address_safety_gate_first`, `already_in_care` or `insufficient_data`, with every signal tied to the FHIR resource it came from and every rule's outcome explained.
4. **Audit record.** Every call is recorded with references, versions and an output hash, never clinical values.

The clinical basis is in [research/veteran_self_harm_risk_screening.md](research/veteran_self_harm_risk_screening.md); the rules are in the [rule card](docs/clinical/rule_card_adhd_1.0.md); how they behave on a labelled synthetic cohort is in the [evaluation report](docs/evaluation/adhd_ruleset_1.0.0.md).

## Quick start with the sample data

Requires [uv](https://docs.astral.sh/uv/) (it installs Python 3.12 if needed) and git.

```bash
git clone https://github.com/SpiroGanas/ADHD_MCP.git
cd ADHD_MCP
uv sync
```

See what the server offers, without a client:

```bash
uv run fastmcp inspect src/adhd_mcp/server.py:create_server
```

Run it over stdio against the 14 synthetic personas in `tests/personas/bundles/`:

```bash
ADHD_MCP_FIXTURE_DIR=tests/personas/bundles uv run adhd-mcp
```

The server now waits for an MCP client on standard input; stop it with Ctrl+C. To use it, register it with a client instead (below), then ask, for example: *"Should I consider an ADHD screening referral for patient p01-patient?"* Patient ids are `p01-patient` to `p14-patient`; each persona is described in [tests/personas/catalog.toml](tests/personas/catalog.toml). The sample data are dated around 2026-06-15, so ask with `as_of` 2026-06-15 to see the documented outcomes.

### Connect an MCP client

Most desktop MCP clients take a JSON entry like this (use absolute paths):

```json
{
  "mcpServers": {
    "adhd-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/ADHD_MCP", "adhd-mcp"],
      "env": { "ADHD_MCP_FIXTURE_DIR": "/absolute/path/to/ADHD_MCP/tests/personas/bundles" }
    }
  }
}
```

With Claude Code:

```bash
claude mcp add adhd-mcp \
  --env ADHD_MCP_FIXTURE_DIR="$PWD/tests/personas/bundles" \
  -- uv run --directory "$PWD" adhd-mcp
```

Client-specific steps, the MCP Inspector and a container: [docs/guide/clients.md](docs/guide/clients.md).

## Configuration

Everything is set with environment variables, validated at start-up; the server refuses to start on a missing or malformed setting.

| Variable | Use |
|---|---|
| `ADHD_MCP_FIXTURE_DIR` | Directory of synthetic FHIR bundles (development and demos) |
| `ADHD_MCP_FHIR_BASE_URL` | A FHIR R4 server to read instead (read-only) |
| `ADHD_MCP_TRANSPORT` | `stdio` (default) or `http` (needs OAuth settings and an audit file) |
| `ADHD_MCP_AUDIT_FILE` | Append-only JSON Lines audit file |

The full list (HTTP and OAuth, SMART backend services, privacy policy, site code mapping) and a local FHIR server setup: [docs/guide/configuration.md](docs/guide/configuration.md).

## Tools

All tools are read-only and take a patient id and an optional as-of date. Full inputs and outputs: [docs/reference/tools.md](docs/reference/tools.md) (generated from the tool contracts).

| Tool | Purpose |
|---|---|
| `get_server_info` | Server, tool contract and ruleset versions; intended use |
| `check_safety_gate` | Self-harm signals in the record, checked before any referral is considered |
| `get_mh_problem_list` | Mental health diagnoses grouped by family, with onset order |
| `get_screening_history` | Screening instrument scores over time (cutoffs only where verified) |
| `get_medication_timeline` | Exposure periods by drug class; distinct antidepressants |
| `get_utilization_summary` | Acute care and injury visits, crashes as driver, psychiatric stays |
| `get_psychosocial_context` | Housing, legal, education and employment, military separation |
| `check_existing_care` | Existing ADHD code, referral, evaluation or care plan |
| `assess_referral_need` | The recommendation, with the safety gate, evidence and decision trace |
| `draft_referral_proposal` | A draft referral (FHIR ServiceRequest, status draft) for the clinician; never stored |

The server also offers MCP resources (the ruleset, signal catalog, value sets, drug classes, instrument metadata, intended use) and two prompts (`explain_recommendation`, `summarize_checks`).

## Design principles

| Principle | What it means |
|---|---|
| Recommend, never diagnose | Enforced in output schemas, wording, and tests |
| Deterministic rules first | The language model never navigates raw FHIR or decides eligibility; the server does the joins and rule evaluation |
| Read-only | Tools only read FHIR. `draft_referral_proposal` returns a draft and stores nothing |
| Evidence or silence | Every signal cites a resource id; nothing is asserted without a source |
| Safety gate before referral | Self-harm signals always take priority |
| Honest about missing data | Every output says which data were available, empty, incomplete or failed; an empty record is never a clean one |
| Privacy by default | Synthetic data only in this repository; logs hold references and hashes, not clinical content |
| Test-driven | Every behavior starts as a failing test |

## Development

```bash
./scripts/check            # lint, format, types, synthetic-data guard, tests with coverage
```

All commands are listed in [CLAUDE.md](CLAUDE.md#commands). To contribute, read [CONTRIBUTING.md](CONTRIBUTING.md), then [status.md](status.md) for what is next.

## Repository guide

| Path | Contents |
|---|---|
| [status.md](status.md) | Work done and next steps; updated every session |
| [project_plan.md](project_plan.md) | Phased, test-driven plan |
| [CHANGELOG.md](CHANGELOG.md) | Changes by version |
| [docs/guide/](docs/guide/) | Configuration, client setup and the [deployment guide](docs/guide/deployment.md) |
| [docs/integration/](docs/integration/) | VA Lighthouse adapter notes and the Oracle Health desk review |
| [docs/reference/tools.md](docs/reference/tools.md) | Tool reference |
| [docs/limitations.md](docs/limitations.md) | What the tool cannot do |
| [docs/architecture.md](docs/architecture.md) | Components, data flow, tool contracts |
| [docs/adr/](docs/adr/README.md) | Architecture decision records |
| [docs/handoff/](docs/handoff/README.md) | Hand-off documents (Word): human review checklist by reviewer role, user guide, clinician quick start |
| [docs/clinical/](docs/clinical/) | Intended use, rule cards, risk register, glossary, verification backlog |
| [docs/evaluation/](docs/evaluation/README.md) | Cohort evaluation, sex-balance review, model-in-the-loop and performance |
| [docs/security/threat_model.md](docs/security/threat_model.md) | Threat model |
| [research/](research/) | Evidence report and source notes |
| [CLAUDE.md](CLAUDE.md), [AGENTS.md](AGENTS.md), [CONTRIBUTING.md](CONTRIBUTING.md) | Working rules for AI and human contributors |

## Technology

Python 3.12, [FastMCP](https://gofastmcp.com) 4.2, HL7 FHIR R4, ICD-10-CM, RxNorm, LOINC (codes still unverified, so unused by the rules), uv, pytest, ruff and mypy. Exact versions are pinned in [ADR 0006](docs/adr/0006-tooling-versions.md).

## Data and privacy

Never commit real patient data, credentials, or anything derived from a real health record. All fixtures are synthetic. See the [intended use statement](docs/clinical/intended_use.md) and [risk register](docs/clinical/risk_register.md).

## License

[MIT](LICENSE)
