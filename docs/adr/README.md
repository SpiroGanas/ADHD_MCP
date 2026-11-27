# Architecture Decision Records

A short record of each decision that would be costly to reverse: what was decided, why, and what was given up.

## How to use

- Copy [0000-template.md](0000-template.md) to the next number with a short title.
- Keep it to one page. Write it in the same pull request as the change it explains.
- Never edit the decision of an accepted ADR. Write a new one that supersedes it and update the status of the old one.
- Ask the project owner before accepting an ADR that changes scope, clinical behavior or a tool contract.

## Index

| ADR | Title | Status |
|---|---|---|
| [0001](0001-python-and-fastmcp.md) | Python and FastMCP | Accepted |
| [0002](0002-read-only-task-specific-tools.md) | Read-only, task-specific tools | Accepted |
| [0003](0003-rules-first-with-scorer-slot.md) | Deterministic rules first, with a scorer slot | Accepted |
| [0004](0004-synthetic-first-fhir-abstraction.md) | Synthetic data first behind a FHIR abstraction | Accepted |
| [0005](0005-adhd-first-condition-plugins.md) | ADHD first, conditions as plugins | Accepted |
| [0006](0006-tooling-versions.md) | Tooling and pinned versions | Accepted |
| [0007](0007-fhir-modeling.md) | Narrow internal FHIR models | Accepted |
| [0008](0008-site-codes-and-search-warnings.md) | Per-site local code mapping, and search warnings from the FHIR port | Accepted |
| [0009](0009-rxnorm-drug-classes.md) | Hand-curated RxNorm drug classes, expanded and verified with RxNav | Accepted |
| [0010](0010-rulesets-engine-and-plugins.md) | Rulesets as data, a condition-independent engine, and condition plugins | Accepted |
| [0011](0011-audit-tracing-and-privacy.md) | Audit records, trace context and the sensitive-data policy | Accepted |
| [0012](0012-authentication.md) | Authentication toward MCP clients and toward the FHIR server | Accepted |

Expected next: none planned.
