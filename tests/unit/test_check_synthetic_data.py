"""The repository guard that blocks files resembling real patient data."""

import json
from pathlib import Path
from typing import Any

from scripts.check_synthetic_data import SYNTHETIC_IDENTIFIER_SYSTEM, check_file


def synthetic_patient(**overrides: Any) -> dict[str, Any]:
    patient: dict[str, Any] = {
        "resourceType": "Patient",
        "id": "syn-p00",
        "meta": {
            "tag": [
                {"system": "http://terminology.hl7.org/CodeSystem/v3-ActReason", "code": "HTEST"}
            ]
        },
        "identifier": [{"system": SYNTHETIC_IDENTIFIER_SYSTEM, "value": "SYN-0000"}],
        "name": [{"family": "Synthetic", "given": ["Persona"]}],
    }
    patient.update(overrides)
    return patient


def write_json(tmp_path: Path, content: Any) -> Path:
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(content), encoding="utf-8")
    return path


def bundle(*resources: dict[str, Any]) -> dict[str, Any]:
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [{"resource": r} for r in resources],
    }


def test_synthetic_bundle_passes(tmp_path: Path) -> None:
    assert check_file(write_json(tmp_path, bundle(synthetic_patient()))) == []


def test_patient_without_test_data_tag_fails(tmp_path: Path) -> None:
    path = write_json(tmp_path, bundle(synthetic_patient(meta={})))
    assert any("HTEST" in p for p in check_file(path))


def test_patient_with_non_synthetic_identifier_fails(tmp_path: Path) -> None:
    patient = synthetic_patient(
        identifier=[{"system": "http://hospital.example/mrn", "value": "1"}]
    )
    assert any("identifier" in p for p in check_file(write_json(tmp_path, bundle(patient))))


def test_patient_with_realistic_name_fails(tmp_path: Path) -> None:
    patient = synthetic_patient(name=[{"family": "Smith", "given": ["Jane"]}])
    assert any("name" in p for p in check_file(write_json(tmp_path, bundle(patient))))


def test_bare_patient_resource_is_checked(tmp_path: Path) -> None:
    path = write_json(tmp_path, synthetic_patient(meta={}))
    assert check_file(path) != []


def test_ssn_shaped_number_in_any_text_file_fails(tmp_path: Path) -> None:
    path = tmp_path / "notes.md"
    ssn_shaped = "-".join(["123", "45", "6789"])  # assembled so this file passes the guard
    path.write_text(f"contact {ssn_shaped} later\n", encoding="utf-8")
    assert any("SSN" in p for p in check_file(path))


def test_iso_dates_are_not_mistaken_for_ssns(tmp_path: Path) -> None:
    path = tmp_path / "notes.md"
    path.write_text("seen 2024-01-15 and 2024-01-15T10:00:00Z\n", encoding="utf-8")
    assert check_file(path) == []


def test_non_fhir_json_is_ignored(tmp_path: Path) -> None:
    assert check_file(write_json(tmp_path, {"name": {"family": "Smith"}})) == []


def test_binary_file_is_skipped(tmp_path: Path) -> None:
    path = tmp_path / "image.bin"
    path.write_bytes(b"\xff\xfe\x00\x01")
    assert check_file(path) == []
