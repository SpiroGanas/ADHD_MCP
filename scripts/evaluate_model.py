"""Run the model-in-the-loop tasks (tests/evals/model_tasks.toml) with a model driver and
print the per-model summary as JSON (Phase 7, item 4).

Usage: uv run python scripts/evaluate_model.py [--driver careful|careless] [--repeats N]

Only the scripted stand-in drivers exist. A live model driver needs the project owner's
approval of the API budget and of the provider SDK as a dependency (status.md, question 4);
see docs/evaluation/model_in_the_loop.md.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.evals import model_loop as m  # noqa: E402

DRIVERS = {
    "careful": m.ScriptedDriver("scripted-careful", m.careful_policy),
    "careless": m.ScriptedDriver("scripted-careless", m.careless_policy),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--driver", choices=sorted(DRIVERS), default="careful")
    parser.add_argument("--repeats", type=int, default=int(m.PASS_BAR["min_repeats"]))
    args = parser.parse_args()
    summary = asyncio.run(m.evaluate(DRIVERS[args.driver], repeats=args.repeats))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
