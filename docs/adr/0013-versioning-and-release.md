# ADR 0013: Versioning and release policy

- **Status:** Proposed (the project owner approves it with the first release, 1.0.0)
- **Date:** 2026-11-27
- **Decided by:** Claude Code agent, under the owner's decision of 2026-11-27 to prepare the release but tag 1.0.0 only after the clinical content is reviewed

## Context

Phase 7, work item 9 asks for a versioning policy with three separate version lines (server, tool contracts, rulesets), packaging, a tagged 1.0.0 and a container image if useful. Every output and audit record already reports the three lines (architecture: Versioning). What is missing is when each line changes, what a release must contain, and a check that a release is complete.

## Decision

**Three version lines, all semantic versions:**

| Line | Where | Major | Minor | Patch |
|---|---|---|---|---|
| Server | `pyproject.toml` `version` (reported from package metadata) | Breaking change to how the server is run or configured, or a new tool contract major | New features, new tools, new conditions | Fixes that change no output |
| Tool contract | `TOOL_CONTRACT_VERSION` in `src/adhd_mcp/versions.py`; snapshots in `tests/contract/snapshots/` | A tool removed or renamed, an input removed or tightened, an output field removed or changed in meaning | A tool, input or output field added; descriptions changed | Wording of descriptions without change of meaning |
| Ruleset | `version` and `status` in each `data/<condition>/ruleset.toml` | A changed recommendation for some record (rule, threshold, window, weight, signal definition, value set used by a signal) | Additions that change no recommendation (citations, notes) | Not used |

- The contract is `0.x` until the first release and becomes `1.0.0` with server `1.0.0`.
- A released ruleset is immutable: status `released` plus its sha256 pinned in `data/released_rulesets.toml` (ADR 0010). Any change makes a new ruleset version, with its own rule card, evaluation report and change-log entry. A server release may ship a draft ruleset only as a pre-release.
- Other versioned data (gate, evidence-tool definitions, value sets, drug classes, wording, privacy policy, the evaluation cohort and model task set) keep their own `version` fields and are reported where they are used.

**A release:**

1. Pre-releases (`1.0.0rc1`, PEP 440) and 0.x versions may carry a draft ruleset; a final release of 1.0.0 or later requires every active ruleset to be released.

   **Amended 2026-11-28 (peer review 01, G3; owner decision):** the server was relabelled from 1.0.0rc1 to 0.9.0 and stays at 0.x until three things are true: a clinician has signed the rule cards, the model-in-the-loop evaluation has passed with a real model, and the server has read at least one real sandbox. "Release candidate" overstated readiness.
2. `CHANGELOG.md` has a section for the version.
3. The rule card of each active ruleset names its version and status, and its evaluation report (`docs/evaluation/`) matches the current content and cohort.
4. Contract snapshots and the generated tool reference (`docs/reference/tools.md`) match the server.
5. The README states that the tool is not clinically validated.
6. `uv run python scripts/release_check.py` checks 1 to 5 and must pass; then the owner tags `vX.Y.Z` on `main`.
7. Human prerequisites the script cannot check, for a final release: the clinical reviewer's approval of each rule card and signal catalog (status.md, open question 1), the human spot-check of the `safety.*` value sets (verification backlog, F1), and the owner's decisions on the open questions marked "Before release".

**Packaging:** a wheel and sdist built with `uv build` (hatchling; data files are package data). A container image is built from the `Dockerfile` in CI as a check; nothing is published to a registry until the owner decides where (owner decision 2026-11-27).

## Alternatives considered

| Option | Why not |
|---|---|
| One version for everything | A wording fix would look like a clinical change, and a ruleset change could hide inside a server patch |
| Calendar versions for rulesets | Says when, not whether recommendations changed |
| Publish to PyPI and a container registry now | No owner decision on where or by whom; the clinical content is not yet reviewed |

## Consequences

- A clinician or auditor can tell from any output whether two results were produced by the same rules: every output's `versions` carries `clinical_content`, the sha256 of all packaged clinical content, and every audit record carries it too (peer review 01, X2).
- Releasing takes a deliberate step per line; `scripts/release_check.py` catches the forgotten ones.
- Releasing 1.0.0 still needs the owner's review of the clinical content (status.md, Next steps).
