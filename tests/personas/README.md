# Persona catalog

Hand-built synthetic patients that act as the specification for every rule (see the TDD rules in [project_plan.md](../../project_plan.md#test-driven-development-rules)). All data is synthetic: every Patient carries the HL7 `HTEST` tag, a `urn:adhd-mcp:synthetic-id` identifier and the family name `Synthetic`.

| File | Contents |
|---|---|
| `catalog.toml` | Narrative and expected outcomes for each persona; the as-of date (2026-06-15) |
| `definitions.py` | How each persona is built. Edit this, not the JSON |
| `builder.py` | Helpers that produce FHIR R4 resources with unique ids (`p01-cond-1`) |
| `bundles/*.json` | Generated FHIR R4 collection bundles, committed |

The personas specify behaviour one case at a time. For evaluation, a larger labelled cohort (184 patients built from 23 archetypes) is generated in memory by [tests/evals/cohort.py](../evals/cohort.py); see [docs/evaluation/](../../docs/evaluation/README.md).

## Use

Load everything in one step:

```python
from tests.personas import all_resources, load_bundle, load_catalog
```

Regenerate the bundles after editing `definitions.py` (a test fails if they are stale):

```bash
uv run python scripts/build_personas.py
```

Load them into the local FHIR server (see [docs/dev/local_fhir_server.md](../../docs/dev/local_fhir_server.md)):

```bash
uv run python scripts/load_personas.py
```

## Rules for adding personas

- Every new rule gets at least one persona that triggers it, one that narrowly misses, and one that is excluded.
- State the expected outcome in `catalog.toml` before the rule is coded.
- RxNorm and local codes in personas are illustrative test data, not verified value-set content.
