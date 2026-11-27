"""Documentation stays true to the code (Phase 7, item 8): the generated tool reference
matches the contract snapshots, and every relative link in the Markdown resolves."""

import re
from pathlib import Path

import pytest
from scripts.build_tool_reference import OUTPUT, render

ROOT = Path(__file__).resolve().parents[2]
#: The research report is a frozen source document with its own external citations.
SKIP = ("research/", ".venv/", "build/", ".pytest_cache/")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def markdown_files() -> list[Path]:
    return sorted(
        p
        for p in ROOT.rglob("*.md")
        if not str(p.relative_to(ROOT)).startswith(SKIP) and ".git/" not in str(p)
    )


def test_the_tool_reference_is_generated_from_the_current_contract() -> None:
    assert OUTPUT.read_text(encoding="utf-8") == render(), (
        "Run: uv run python scripts/build_tool_reference.py"
    )


@pytest.mark.parametrize("path", markdown_files(), ids=lambda p: str(p.relative_to(ROOT)))
def test_relative_links_resolve(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)  # code blocks are not links
    broken = []
    for target in LINK.findall(text):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        file_part = target.split("#", 1)[0]
        if file_part and not (path.parent / file_part).exists():
            broken.append(target)
    assert broken == []
