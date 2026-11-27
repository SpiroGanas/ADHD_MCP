"""Run the labelled synthetic cohort through the active ADHD ruleset and write the versioned
evaluation report to docs/evaluation/ (Phase 7, item 2).

Usage: uv run python scripts/evaluate_ruleset.py

Deterministic: the cohort, the as-of date and the clock are fixed. Takes a few minutes,
because every threshold variant re-runs the whole cohort.
"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.evals import harness as h  # noqa: E402
from tests.evals.cohort import build_cohort  # noqa: E402
from tests.evals.report import (  # noqa: E402
    build_report,
    render_json,
    render_markdown,
    report_paths,
)

from adhd_mcp.conditions.adhd import adhd_plugin  # noqa: E402


async def evaluate() -> dict[str, object]:
    patients = build_cohort()
    baseline = await h.run_cohort(patients)
    sensitivity = await h.run_variants(patients, baseline, h.SENSITIVITY)
    options = await h.run_variants(patients, baseline, h.OPTIONS)
    return build_report(patients, baseline, sensitivity, options)


def main() -> None:
    report = asyncio.run(evaluate())
    json_path, md_path = report_paths(adhd_plugin().ruleset.version)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(render_json(report), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    agreement = report["agreement"]
    assert isinstance(agreement, dict)
    print(f"{agreement['agree']} of {agreement['patients']} patients agree; wrote {md_path}")


if __name__ == "__main__":
    main()
