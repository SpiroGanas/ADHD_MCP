"""Contract snapshot mechanism.

Snapshots are canonical JSON files. A mismatch fails with a diff. Set the environment
variable ``UPDATE_SNAPSHOTS=1`` to rewrite them deliberately.
"""

import difflib
import json
import os
from pathlib import Path
from typing import Any

from mcp_types import Tool

SNAPSHOT_ROOT = Path(__file__).parent
TOOL_SNAPSHOT_DIR = SNAPSHOT_ROOT / "tools"


def tool_contract(tool: Tool) -> dict[str, Any]:
    """The parts of a tool definition that clients and prompts depend on."""
    return tool.model_dump(
        mode="json",
        by_alias=True,
        include={"name", "title", "description", "input_schema", "output_schema", "annotations"},
        exclude_none=True,
    )


def _canonical(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def assert_matches_snapshot(path: Path, value: Any) -> None:
    actual = _canonical(value)
    if os.environ.get("UPDATE_SNAPSHOTS") == "1":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8")
        return
    if not path.exists():
        raise AssertionError(
            f"No snapshot at {path}. Review the contract, then run with UPDATE_SNAPSHOTS=1."
        )
    expected = path.read_text(encoding="utf-8")
    if actual != expected:
        diff = "".join(
            difflib.unified_diff(
                expected.splitlines(keepends=True),
                actual.splitlines(keepends=True),
                fromfile=f"{path.name} (stored)",
                tofile=f"{path.name} (current)",
            )
        )
        raise AssertionError(f"Contract changed for {path.name}:\n{diff}")
