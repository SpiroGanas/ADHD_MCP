"""The bulk synthetic population: deterministic, synthetic, valid and loadable."""

import json
from pathlib import Path

import pytest
from fhir.resources.R4B.bundle import Bundle
from scripts.check_synthetic_data import check_file
from scripts.generate_population import generate, write_population

from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.normalize import normalize_many


def test_same_seed_gives_identical_output() -> None:
    assert generate(20, seed=7) == generate(20, seed=7)


def test_different_seed_gives_different_output() -> None:
    assert generate(20, seed=7) != generate(20, seed=8)


def test_generates_the_requested_number_of_patients_with_unique_ids() -> None:
    bundles = generate(50, seed=1)
    assert len(bundles) == 50
    keys = [
        (e["resource"]["resourceType"], e["resource"]["id"]) for b in bundles for e in b["entry"]
    ]
    assert len(keys) == len(set(keys))
    assert all(r_id.startswith("g") for _, r_id in keys)


def test_bundles_are_valid_fhir_and_normalize_cleanly() -> None:
    for bundle in generate(15, seed=3):
        Bundle.model_validate(bundle)
        result = normalize_many([e["resource"] for e in bundle["entry"]])
        assert result.skipped == ()
        assert result.records


def test_written_files_pass_the_synthetic_data_guard(tmp_path: Path) -> None:
    paths = write_population(tmp_path, count=5, seed=2)
    assert len(paths) == 5
    for path in paths:
        assert check_file(path) == []
        json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.anyio
async def test_population_loads_into_the_fixture_adapter(tmp_path: Path) -> None:
    write_population(tmp_path, count=10, seed=4)
    adapter = FixtureFhirAdapter.from_directory(tmp_path)
    patient = await adapter.read_patient("g00001-patient")
    assert patient["resourceType"] == "Patient"
    assert await adapter.search("Encounter", "g00001-patient")
