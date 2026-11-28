"""The committed evaluation report belongs to the active ruleset and the current cohort.

Re-running the whole evaluation takes minutes, so this checks fingerprints instead: changing
the ruleset, the signal catalog, a value set, a drug class or the cohort without
regenerating the report (``uv run python scripts/evaluate_ruleset.py``) fails here.
"""

import json
from typing import Any

from adhd_mcp.conditions.adhd import adhd_plugin
from tests.evals.cohort import build_cohort
from tests.evals.report import (
    _content_files,
    identity,
    logic_files,
    render_markdown,
    report_paths,
)

JSON_PATH, MD_PATH = report_paths(adhd_plugin().ruleset.version)


def committed() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    return data


def test_a_report_exists_for_the_active_ruleset_version() -> None:
    assert JSON_PATH.exists(), "run: uv run python scripts/evaluate_ruleset.py"
    assert MD_PATH.exists()


def test_the_report_matches_the_current_ruleset_content_and_cohort() -> None:
    assert committed()["identity"] == identity(build_cohort()), (
        "The ruleset, its clinical content, the decision logic or the cohort changed since the "
        "report was made. "
        "Run: uv run python scripts/evaluate_ruleset.py"
    )


def test_the_logic_fingerprint_covers_the_modules_that_decide_outcomes() -> None:
    # Peer review 01, T10: a logic change left the committed report looking current.
    paths = {path for path, _ in logic_files()}
    for module in (
        "rules/engine.py",
        "rules/signals.py",
        "orchestration/assess.py",
        "evidence/safety_gate.py",
        "conditions/adhd.py",
        "fhir/normalize.py",
    ):
        assert module in paths


def test_the_markdown_is_rendered_from_the_json() -> None:
    assert MD_PATH.read_text(encoding="utf-8") == render_markdown(committed())


def test_the_report_says_what_it_cannot_show() -> None:
    text = MD_PATH.read_text(encoding="utf-8")
    assert "say nothing about real-world accuracy" in text
    assert "not clinically validated" in text


def test_every_patient_agreed_when_the_report_was_made() -> None:
    agreement = committed()["agreement"]
    assert agreement["mismatches"] == []
    assert agreement["agree"] == agreement["patients"]


def test_the_fingerprint_covers_every_clinical_data_file() -> None:
    paths = {path for path, _ in _content_files()}
    for expected in (
        "adhd/ruleset.toml",
        "adhd/signal_catalog.toml",
        "medication_timeline.toml",
        "utilization.toml",
        "safety_gate.toml",
        "existing_care.toml",
        "privacy.toml",
        "wording.toml",
        "site_codes/synthetic.toml",
        "value_sets/sud.alcohol.toml",
        "drug_classes/med.antidepressant.toml",
        "instruments/phq9.toml",
    ):
        assert expected in paths
