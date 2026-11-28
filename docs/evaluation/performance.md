# Performance

Phase 7, work item 7: latency targets for a full assessment, and how they are measured.

## Targets

| Measure | Target | Checked by |
|---|---|---|
| `assess_referral_need`, 95th percentile, against a local FHIR server (HAPI FHIR in Docker, personas loaded, after one warm-up round) | At most 2 s | `tests/integration/test_performance_live.py` (CI integration job); `scripts/benchmark.py --url ...` |
| FHIR requests per assessment | At most one Patient read, one search per resource type, and two more Observation searches (14): Observations are read by instrument code, by category and by the site's military separation codes, never whole (peer review 01, D1); no query repeated | `tests/unit/test_benchmark.py`; `tests/tools/test_assess_referral_need.py` |
| `assess_referral_need` in process (fixture data) | Not a target; a baseline for spotting regressions | `scripts/benchmark.py` |

The request budget is the deterministic guard: latency against a real server is dominated by the number of round trips, and every assessment reads through one request-scoped cache (`fhir/request_cache.py`). The 2 s target is a proposal; the project owner may set a different one for hosted use.

## Measuring

```bash
uv run python scripts/benchmark.py                                    # in process
docker compose up -d fhir && uv run python scripts/load_personas.py   # then:
uv run python scripts/benchmark.py --url http://localhost:8080/fhir
uv run python scripts/benchmark.py --large 20000                      # one long record
```

`--large N` builds one synthetic long-term record (N laboratory results and vital signs, 200 routine visits, a few coded conditions) behind an in-process HTTP server and assesses it. It shows the effect of filtered searches (peer review 01, D1): no laboratory result or vital sign is transferred. A unit test checks the same on 2,000 results. On 2026-11-28 in the development container, 5,000 results gave a p95 of 279 ms with 14 requests.

The script runs every persona through `assess_referral_need` over an in-memory MCP client, five rounds by default, and prints the 50th and 95th percentiles, the maximum, and the most FHIR requests any assessment needed. It exits non-zero when a target is missed.

## Baseline (2026-11-27)

| Source | Assessments | p50 | p95 | Max | Most FHIR requests |
|---|---|---|---|---|---|
| Fixture data, in process (development container) | 70 | 103 ms | 172 ms | 215 ms | 11 |
| Local HAPI FHIR (CI integration job, 2026-11-27, PR #6) | 14 personas × 3 rounds after a warm-up | | Within the 2 s target (the test passed; figures are printed only on failure) | | Within the budget of 12 |

About 60% of the in-process time is the MCP client validating the large output against its schema; the assessment itself takes about 35 ms (184 cohort patients in about 6 s through the harness). No regression to fix was found.
