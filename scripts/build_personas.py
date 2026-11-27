"""Write persona bundles from tests/personas/definitions.py to tests/personas/bundles/.

Usage: uv run python scripts/build_personas.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.personas import BUNDLE_DIR  # noqa: E402
from tests.personas.definitions import build_bundles  # noqa: E402


def render(bundle: dict[str, object]) -> str:
    return json.dumps(bundle, indent=2, sort_keys=False) + "\n"


def main() -> None:
    BUNDLE_DIR.mkdir(exist_ok=True)
    for key, bundle in build_bundles().items():
        (BUNDLE_DIR / f"{key}.json").write_text(render(bundle), encoding="utf-8")
        print(f"wrote {key}.json")


if __name__ == "__main__":
    main()
