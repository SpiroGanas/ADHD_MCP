# Evaluation

How the ADHD ruleset and the server are evaluated (Phase 7). Every result here comes from synthetic data. **Nothing here is evidence of clinical accuracy, and the tool is not clinically validated.**

| Document | Contents |
|---|---|
| [adhd_ruleset_1.0.0.md](adhd_ruleset_1.0.0.md) (and `.json`) | Generated report for ruleset 1.0.0 on the labelled cohort: agreement with intended outcomes, outcomes by archetype, rates by sex and age band, signal drivers, threshold sensitivity, sex-balance options |
| [sex_balance_review.md](sex_balance_review.md) | Findings on under-flagging of internalizing presentations and the options for the project owner |

## Ruleset evaluation

| Part | Where |
|---|---|
| Labelled cohort (23 archetypes x 2 sexes x 4 age bands = 184 patients) | `tests/evals/cohort.py` |
| Harness (runs the cohort, computes the metrics, threshold variants and options) | `tests/evals/harness.py` |
| Report builder and renderer | `tests/evals/report.py` |
| Tests: cohort design and agreement, a hand-calculated tiny cohort, report freshness | `tests/evals/test_*.py` |

Regenerate the report after any change to the ruleset, the signal catalog, a value set, a drug class or the cohort:

```bash
uv run python scripts/evaluate_ruleset.py
```

It takes about two minutes. `tests/evals/test_report.py` fails while the committed report's fingerprints do not match the current content and cohort. A new ruleset version gets a new report file next to the old one.
