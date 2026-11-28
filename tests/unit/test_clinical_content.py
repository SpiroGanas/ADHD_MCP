"""Peer review 01, X2: a released ruleset was hash-pinned, but the catalog, value sets, drug
classes, gate and evidence definitions and wording it depends on were not, so two outputs
naming the same ruleset could rest on different content. Every output now reports a
fingerprint of all packaged clinical content, and a released ruleset pins it."""

import hashlib

import pytest

from adhd_mcp import versions
from adhd_mcp.audit.records import AuditRecord
from adhd_mcp.rules.ruleset import ReleasedRuleset, parse_ruleset
from tests.unit.rules.test_ruleset import RULESET


def test_the_fingerprint_covers_every_clinical_data_file() -> None:
    paths = {path for path, _ in versions.clinical_content_files()}
    for expected in (
        "adhd/ruleset.toml",
        "adhd/signal_catalog.toml",
        "value_sets/safety.suicidal_ideation.toml",
        "drug_classes/med.antidepressant.toml",
        "safety_gate.toml",
        "existing_care.toml",
        "wording.toml",
        "privacy.toml",
        "site_codes/synthetic.toml",
        "instruments/phq9.toml",
    ):
        assert expected in paths
    # The pins themselves are not content (they would make the fingerprint circular).
    assert "released_rulesets.toml" not in paths


def test_the_fingerprint_is_a_sha256() -> None:
    digest = versions.clinical_content_sha256()
    assert len(digest) == 64
    int(digest, 16)


def test_a_released_ruleset_pins_the_clinical_content_too() -> None:
    text = RULESET.format(status="released")
    digest = hashlib.sha256(text.encode()).hexdigest()
    content = versions.clinical_content_sha256()
    pinned = (ReleasedRuleset(id="x", version="1.0.0", sha256=digest, content_sha256=content),)
    assert parse_ruleset(text, released=pinned).status == "released"
    stale = (ReleasedRuleset(id="x", version="1.0.0", sha256=digest, content_sha256="0" * 64),)
    with pytest.raises(ValueError, match="clinical content changed since release"):
        parse_ruleset(text, released=stale)


def test_every_audit_record_names_the_clinical_content() -> None:
    assert "clinical_content" in AuditRecord.model_fields
