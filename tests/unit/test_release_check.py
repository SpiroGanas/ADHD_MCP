"""The release check (ADR 0013): it fails when the change log, a rule card, the evaluation
report, the contract snapshots or the tool reference are out of date for the version."""

from typing import Any

import pytest
from scripts import release_check as rc

from adhd_mcp.conditions.adhd import adhd_plugin

RULESET = adhd_plugin().ruleset
RELEASED = RULESET.model_copy(update={"status": "released"})
CARD = "| Ruleset identifier and version | `adhd` 1.0.0 (...) |\n| Status | **Draft.** Windows |\n"


@pytest.mark.parametrize(
    ("version", "pre"),
    [("1.0.0rc1", True), ("1.0.0a2", True), ("1.0.0b1", True), ("1.0.0.dev3", True),
     ("1.0.0", False), ("2.3.4", False)],
)  # fmt: skip
def test_pre_releases_are_recognised(version: str, pre: bool) -> None:
    assert rc.is_pre_release(version) is pre


def test_the_change_log_needs_a_section_for_the_version() -> None:
    assert rc.check_changelog("1.0.0", "## [1.0.0] - 2026-12-01\n") == []
    assert rc.check_changelog("1.0.0", "## [1.0.0rc1] - 2026-11-27\n") != []


def test_the_rule_card_must_name_the_ruleset_version_and_status() -> None:
    assert rc.check_rule_card(RULESET, CARD) == []
    assert rc.check_rule_card(RULESET, None) != []
    assert rc.check_rule_card(RULESET, CARD.replace("1.0.0", "0.9.0")) != []
    assert rc.check_rule_card(RELEASED, CARD) == ["rule card status does not say 'released'"]


def test_the_rule_card_file_is_named_by_major_and_minor_version() -> None:
    assert rc.rule_card_path(RULESET).name == "rule_card_adhd_1.0.md"
    assert rc.rule_card_path(RULESET).exists()


def test_a_final_release_needs_released_rulesets_and_a_1_x_contract() -> None:
    assert rc.check_final_release("1.0.0rc1", [RULESET], "0.3.0") == []
    problems = rc.check_final_release("1.0.0", [RULESET], "0.3.0")
    assert len(problems) == 2
    assert rc.check_final_release("1.0.0", [RELEASED], "1.0.0") == []


def test_the_readme_must_say_the_tool_is_not_clinically_validated() -> None:
    assert rc.check_readme("It is NOT clinically validated.") == []
    assert rc.check_readme("It is validated.") != []


def test_a_changed_tool_contract_is_caught() -> None:
    current: dict[str, Any] = {"tools": {}, "prompts": {}}
    assert "the tool list differs from the contract snapshots" in rc.check_contracts(current)


@pytest.mark.anyio
async def test_a_changed_description_is_caught() -> None:
    current = await rc.current_contracts()
    current["tools"]["get_server_info"] = current["tools"]["get_server_info"] | {
        "description": "changed"
    }
    assert rc.check_contracts(current) == [
        "tool get_server_info differs from its contract snapshot"
    ]


def test_a_missing_report_for_a_new_ruleset_version_is_caught() -> None:
    newer = RULESET.model_copy(update={"version": "9.9.9"})
    assert rc.check_evaluation_report(newer) == [f"no evaluation report for ruleset {newer.label}"]


def test_the_repository_passes_its_release_check_as_a_pre_release() -> None:
    assert rc.is_pre_release(rc.project_version())
    assert rc.run_checks() == []
