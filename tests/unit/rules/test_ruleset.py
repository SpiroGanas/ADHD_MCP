"""Ruleset format: versioned, immutable once released, consistent with its catalog."""

import hashlib

import pytest

from adhd_mcp.rules.catalog import load_catalog
from adhd_mcp.rules.ruleset import ReleasedRuleset, load_ruleset, parse_ruleset

RULESET = """
id = "x"
version = "1.0.0"
status = "{status}"
effective_date = "2026-11-27"
catalog = "x.catalog"
catalog_version = "1"
validated = false
exclusions = []
citations = ["test"]
[[rules]]
id = "r"
description = "test"
min_high = 1
min_modifiers = 2
"""


def test_the_adhd_ruleset_loads_and_matches_its_catalog() -> None:
    ruleset = load_ruleset("adhd_mcp.data.adhd")
    catalog = load_catalog("adhd_mcp.data.adhd")
    assert (ruleset.catalog, ruleset.catalog_version) == (catalog.id, catalog.version)
    assert [(r.id, r.min_high, r.min_modifiers) for r in ruleset.rules] == [
        ("high_with_modifiers", 1, 2),
        ("two_high_classes", 2, 0),
    ]
    assert ruleset.validated is False


def test_a_draft_ruleset_needs_no_release_entry() -> None:
    assert parse_ruleset(RULESET.format(status="draft"), released=()).status == "draft"


def test_a_released_ruleset_must_match_its_pinned_hash() -> None:
    text = RULESET.format(status="released")
    digest = hashlib.sha256(text.encode()).hexdigest()
    pinned = (ReleasedRuleset(id="x", version="1.0.0", sha256=digest),)
    assert parse_ruleset(text, released=pinned).status == "released"
    with pytest.raises(ValueError, match="not pinned"):
        parse_ruleset(text, released=())
    changed = text.replace("min_modifiers = 2", "min_modifiers = 1")
    with pytest.raises(ValueError, match="changed since release"):
        parse_ruleset(changed, released=pinned)


def test_a_rule_that_can_never_fire_is_refused() -> None:
    text = (
        RULESET.format(status="draft")
        .replace("min_high = 1", "min_high = 0")
        .replace("min_modifiers = 2", "min_modifiers = 0")
    )
    with pytest.raises(ValueError, match="at least one signal"):
        parse_ruleset(text, released=())
