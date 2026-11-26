# Bulk synthetic population

A seeded generator makes a larger synthetic population for volume and performance tests (Phase 2, item 7). It is for volume only: the hand-built [personas](../../tests/personas/README.md) carry the clinical meaning.

## Generate

```bash
uv run python scripts/generate_population.py --count 1000 --seed 2026
```

This writes one FHIR R4 collection bundle per patient to `build/population/` (about 6 MB for 1,000 patients). The same seed always gives the same data.

## Decisions

| Question | Decision |
|---|---|
| Committed or built on demand? | Built on demand. `build/` is git-ignored; the generator is deterministic, so the data can be recreated exactly |
| Which generator? | A small generator in this repository (`scripts/generate_population.py`) that reuses the persona builder. No new dependency |
| Synthea? | Not used for now: it needs Java and a download from outside the package index, and produces little mental health or screening data. It remains an option if realistic general-population volume is needed later; adding it would be a new dependency and needs the project owner's approval |

## What it contains

Every generated patient has the same synthetic markers as the personas (`HTEST` tag, `urn:adhd-mcp:synthetic-id` identifier `SYN-1xxxx`, family name `Synthetic`) and ids prefixed `g00001-`. Each has one to eight primary care encounters, plus random conditions, injury emergency visits, medications with dispenses, and PHQ-2 and AUDIT-C totals drawn from small fixed pools. The codes are illustrative test data, not value-set content.
