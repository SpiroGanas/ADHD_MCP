"""Generate docs/reference/tools.md from the contract snapshots (Phase 7, item 8).

Usage: uv run python scripts/build_tool_reference.py

The snapshots in tests/contract/snapshots/ are the tool contract; this renders them for
people. tests/unit/test_tool_reference.py fails while the committed page differs from what
this script would write, so the page cannot drift from the contract.
"""

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from adhd_mcp.versions import TOOL_CONTRACT_VERSION  # noqa: E402

SNAPSHOTS = ROOT / "tests" / "contract" / "snapshots"
OUTPUT = ROOT / "docs" / "reference" / "tools.md"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _type(schema: dict[str, Any]) -> str:  # noqa: PLR0911 - one return per schema form
    if "$ref" in schema:
        return str(schema["$ref"]).rsplit("/", 1)[-1]
    if "const" in schema:
        return f"`{json.dumps(schema['const'])}`"
    if "enum" in schema:
        return " \\| ".join(f"`{v}`" for v in schema["enum"])
    if "anyOf" in schema:
        return " or ".join(_type(s) for s in schema["anyOf"])
    kind = schema.get("type", "object")
    if kind == "array":
        return f"list of {_type(schema.get('items', {}))}"
    if fmt := schema.get("format"):
        return f"{kind} ({fmt})"
    return str(kind)


def _cell(text: str) -> str:
    return " ".join(text.split()).replace("|", "\\|")


def _fields(schema: dict[str, Any]) -> list[str]:
    required = set(schema.get("required", []))
    rows = ["| Field | Type | Required | Description |", "|---|---|---|---|"]
    for name, prop in schema.get("properties", {}).items():
        rows.append(
            f"| `{name}` | {_type(prop)} | {'yes' if name in required else 'no'} | "
            f"{_cell(prop.get('description', ''))} |"
        )
    return rows


def render() -> str:
    tools = [_load(p) for p in sorted((SNAPSHOTS / "tools").glob("*.json"))]
    out = [
        "# Tool reference",
        "",
        "Generated from the contract snapshots in `tests/contract/snapshots/` by "
        "`uv run python scripts/build_tool_reference.py`; do not edit by hand. "
        f"Tool contract version **{TOOL_CONTRACT_VERSION}**.",
        "",
        "Every tool is read-only. No result is a diagnosis: every patient tool returns "
        "`is_diagnosis: false` and a notice. The tool is not clinically validated.",
        "",
        "| Tool | Title | Read-only |",
        "|---|---|---|",
    ]
    out += [
        f"| [`{t['name']}`](#{t['name']}) | {t.get('title', '')} | "
        f"{'yes' if t.get('annotations', {}).get('readOnlyHint') else 'no'} |"
        for t in tools
    ]
    out.append("")
    for t in tools:
        out += [f"## {t['name']}", "", _cell(t.get("description", "")), "", "**Inputs**", ""]
        out += _fields(t["inputSchema"]) if t["inputSchema"].get("properties") else ["None."]
        out += ["", "**Output** (top-level fields)", ""]
        out += _fields(t.get("outputSchema", {}))
        out.append("")
    resources = _load(SNAPSHOTS / "resources.json")
    out += ["## Resources", "", "| URI | Title | Description |", "|---|---|---|"]
    for r in resources.get("resources", []) + resources.get("templates", []):
        uri = r.get("uri") or r.get("uriTemplate", "")
        out.append(f"| `{uri}` | {r.get('title', '')} | {_cell(r.get('description', ''))} |")
    out += ["", "## Prompts", "", "| Prompt | Arguments | Description |", "|---|---|---|"]
    for p in sorted((SNAPSHOTS / "prompts").glob("*.json")):
        prompt = _load(p)
        args = ", ".join(f"`{a['name']}`" for a in prompt.get("arguments", []))
        out.append(f"| `{prompt['name']}` | {args} | {_cell(prompt.get('description', ''))} |")
    return "\n".join(out) + "\n"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(), encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
