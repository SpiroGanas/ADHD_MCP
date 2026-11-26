"""The persona catalog is valid synthetic FHIR R4 and matches its builder."""

from typing import Any

import pytest
from fhir.resources.R4B.bundle import Bundle
from scripts.build_personas import render
from scripts.check_synthetic_data import check_file

from adhd_mcp.fhir.normalize import normalize_many
from adhd_mcp.fhir.records import SkipReason
from tests.personas import BUNDLE_DIR, load_bundle, load_catalog, persona_ids
from tests.personas.definitions import PERSONAS, build_bundles


def test_catalog_lists_every_defined_persona() -> None:
    assert persona_ids() == list(PERSONAS)
    assert len(persona_ids()) >= 10
    assert load_catalog()["as_of"] == "2026-06-15"


@pytest.mark.parametrize("persona_id", list(PERSONAS))
def test_committed_bundle_matches_the_builder(persona_id: str) -> None:
    committed = (BUNDLE_DIR / f"{persona_id}.json").read_text(encoding="utf-8")
    assert committed == render(build_bundles()[persona_id]), (
        "Bundle out of date: run `uv run python scripts/build_personas.py`"
    )


@pytest.mark.parametrize("persona_id", list(PERSONAS))
def test_bundle_is_valid_fhir(persona_id: str) -> None:
    Bundle.model_validate(load_bundle(persona_id))


@pytest.mark.parametrize("persona_id", list(PERSONAS))
def test_bundle_contains_only_synthetic_identifiers(persona_id: str) -> None:
    assert check_file(BUNDLE_DIR / f"{persona_id}.json") == []


def test_resource_ids_are_unique_across_all_personas() -> None:
    keys = [
        (e["resource"]["resourceType"], e["resource"]["id"])
        for pid in persona_ids()
        for e in load_bundle(pid)["entry"]
    ]
    assert len(keys) == len(set(keys))


def _references(value: Any) -> list[str]:
    if isinstance(value, dict):
        found = [value["reference"]] if isinstance(value.get("reference"), str) else []
        return found + [r for v in value.values() for r in _references(v)]
    if isinstance(value, list):
        return [r for v in value for r in _references(v)]
    return []


@pytest.mark.parametrize("persona_id", list(PERSONAS))
def test_every_reference_resolves_within_the_bundle(persona_id: str) -> None:
    resources = [e["resource"] for e in load_bundle(persona_id)["entry"]]
    present = {f"{r['resourceType']}/{r['id']}" for r in resources}
    for reference in _references(resources):
        assert reference in present, reference


@pytest.mark.parametrize("persona_id", list(PERSONAS))
def test_every_resource_belongs_to_the_persona(persona_id: str) -> None:
    for entry in load_bundle(persona_id)["entry"]:
        resource = entry["resource"]
        assert resource["id"].startswith(f"{persona_id}-")
        subject = resource.get("subject", {}).get("reference")
        assert subject in (None, f"Patient/{persona_id}-patient")


def test_personas_normalize_with_only_deliberate_skips() -> None:
    for persona_id in persona_ids():
        result = normalize_many([e["resource"] for e in load_bundle(persona_id)["entry"]])
        skipped = {(s.ref.id if s.ref else None, s.reason) for s in result.skipped}
        if persona_id == "p09":
            assert skipped == {
                ("p09-cond-3", SkipReason.EXCLUDED_STATUS),
                ("p09-cond-4", SkipReason.EXCLUDED_STATUS),
                ("p09-obs-1", SkipReason.EXCLUDED_STATUS),
            }
        else:
            assert skipped == set(), persona_id
