"""Check that the repository is ready to tag its current version (ADR 0013).

Usage: uv run python scripts/release_check.py

Fails, listing every problem, when for the version in pyproject.toml:
* CHANGELOG.md has no section for it;
* an active ruleset has no rule card naming its version and status, or its evaluation report
  is missing or stale;
* the tool contract snapshots or the generated tool reference differ from the server;
* the README does not state that the tool is not clinically validated;
* the version is a final release (1.0.0 or later, not a pre-release) while a ruleset is still
  a draft, or the tool contract is still 0.x. A 0.x version, like a pre-release, may carry
  draft rulesets (peer review 01, G3).
"""

import asyncio
import json
import re
import sys
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastmcp import Client  # noqa: E402
from tests.contract.snapshots import SNAPSHOT_ROOT, TOOL_SNAPSHOT_DIR, tool_contract  # noqa: E402
from tests.evals.cohort import build_cohort  # noqa: E402
from tests.evals.report import identity, report_paths  # noqa: E402

from adhd_mcp.rules.ruleset import Ruleset  # noqa: E402
from adhd_mcp.server import create_server  # noqa: E402
from adhd_mcp.tools.context import default_conditions  # noqa: E402
from adhd_mcp.versions import TOOL_CONTRACT_VERSION  # noqa: E402
from scripts.build_tool_reference import OUTPUT as TOOL_REFERENCE  # noqa: E402
from scripts.build_tool_reference import render as render_tool_reference  # noqa: E402

PRE_RELEASE = re.compile(r"(a|b|rc|\.dev)\d*$")
NOT_VALIDATED = "not clinically validated"


def project_version(root: Path = ROOT) -> str:
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def is_pre_release(version: str) -> bool:
    return bool(PRE_RELEASE.search(version))


def check_changelog(version: str, changelog: str) -> list[str]:
    if f"## [{version}]" not in changelog:
        return [f"CHANGELOG.md has no '## [{version}]' section"]
    return []


def rule_card_path(ruleset: Ruleset, root: Path = ROOT) -> Path:
    major, minor = ruleset.version.split(".")[:2]
    return root / "docs" / "clinical" / f"rule_card_{ruleset.id}_{major}.{minor}.md"


def check_rule_card(ruleset: Ruleset, card: str | None) -> list[str]:
    if card is None:
        return [f"no rule card for ruleset {ruleset.label}"]
    problems = []
    if f"`{ruleset.id}` {ruleset.version}" not in card:
        return [f"rule card does not name ruleset `{ruleset.id}` {ruleset.version}"]
    status = re.search(r"^\| Status \| \*\*(\w+)", card, flags=re.MULTILINE)
    if status is None or status.group(1).lower() != ruleset.status:
        problems.append(f"rule card status does not say {ruleset.status!r}")
    return problems


def needs_released_content(version: str) -> bool:
    """A final release of 1.0.0 or later. 0.x versions and pre-releases may ship drafts."""
    return not is_pre_release(version) and int(version.split(".", maxsplit=1)[0]) >= 1


def check_final_release(version: str, rulesets: Sequence[Ruleset], contract: str) -> list[str]:
    if not needs_released_content(version):
        return []
    problems = [
        f"ruleset {r.label} is not released; a final release needs released rulesets"
        for r in rulesets
        if r.status != "released"
    ]
    if contract.startswith("0."):
        problems.append(f"tool contract {contract} is still 0.x; a final release needs 1.0.0+")
    return problems


def check_readme(readme: str) -> list[str]:
    return [] if NOT_VALIDATED in readme.lower() else [f"README does not say '{NOT_VALIDATED}'"]


def check_evaluation_report(ruleset: Ruleset) -> list[str]:
    json_path, md_path = report_paths(ruleset.version)
    if not (json_path.exists() and md_path.exists()):
        return [f"no evaluation report for ruleset {ruleset.label}"]
    stored = json.loads(json_path.read_text(encoding="utf-8"))["identity"]
    if stored != identity(build_cohort()):
        return [f"evaluation report for {ruleset.label} is stale; run scripts/evaluate_ruleset.py"]
    return []


async def current_contracts() -> dict[str, Any]:
    async with Client(create_server()) as client:
        tools = {t.name: tool_contract(t) for t in await client.list_tools()}
        prompts = {
            p.name: p.model_dump(mode="json", by_alias=True, exclude_none=True)
            for p in await client.list_prompts()
        }
    return {"tools": tools, "prompts": prompts}


def _stored(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def check_contracts(current: dict[str, Any]) -> list[str]:
    problems = []
    stored_tools = {p.stem: _stored(p) for p in TOOL_SNAPSHOT_DIR.glob("*.json")}
    if set(stored_tools) != set(current["tools"]):
        problems.append("the tool list differs from the contract snapshots")
    problems += [
        f"tool {name} differs from its contract snapshot"
        for name, contract in current["tools"].items()
        if stored_tools.get(name) != contract
    ]
    problems += [
        f"prompt {name} differs from its contract snapshot"
        for name, prompt in current["prompts"].items()
        if (SNAPSHOT_ROOT / "prompts" / f"{name}.json").exists()
        and _stored(SNAPSHOT_ROOT / "prompts" / f"{name}.json") != prompt
    ]
    if TOOL_REFERENCE.read_text(encoding="utf-8") != render_tool_reference():
        problems.append("docs/reference/tools.md is stale; run scripts/build_tool_reference.py")
    return problems


def run_checks(root: Path = ROOT) -> list[str]:
    version = project_version(root)
    rulesets = [default_conditions().get(c).ruleset for c in default_conditions().ids()]
    problems = check_changelog(version, (root / "CHANGELOG.md").read_text(encoding="utf-8"))
    problems += check_readme((root / "README.md").read_text(encoding="utf-8"))
    for ruleset in rulesets:
        card = rule_card_path(ruleset, root)
        problems += check_rule_card(ruleset, card.read_text("utf-8") if card.exists() else None)
        problems += check_evaluation_report(ruleset)
    problems += check_final_release(version, rulesets, TOOL_CONTRACT_VERSION)
    problems += check_contracts(asyncio.run(current_contracts()))
    return problems


def main() -> None:
    version = project_version()
    problems = run_checks()
    if is_pre_release(version):
        kind = "pre-release"
    elif not needs_released_content(version):
        kind = "0.x development release"
    else:
        kind = "release"
    if problems:
        print(f"{version} ({kind}) is not ready:")
        for p in problems:
            print(f"  - {p}")
        raise SystemExit(1)
    print(f"{version} ({kind}) passes the release check.")


if __name__ == "__main__":
    main()
