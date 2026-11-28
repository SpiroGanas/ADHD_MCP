"""The repository guard that blocks files resembling real patient data."""

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
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


# Review T7: every object is walked, every resource with a name or identifier is checked, and
# a file the guard cannot inspect fails instead of passing silently.

REPOSITORY = Path(__file__).resolve().parents[2]
UNTAGGED = synthetic_patient(meta={})


def write_text(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_json_array_of_patients_is_checked(tmp_path: Path) -> None:
    path = write_json(tmp_path, [synthetic_patient(), UNTAGGED])
    assert any("HTEST" in p for p in check_file(path))


@pytest.mark.parametrize("suffix", [".ndjson", ".jsonl"])
def test_json_lines_files_are_checked(tmp_path: Path, suffix: str) -> None:
    lines = f"{json.dumps(synthetic_patient())}\n\n{json.dumps(UNTAGGED)}\n"
    path = write_text(tmp_path, f"patients{suffix}", lines)
    assert any("HTEST" in p for p in check_file(path))


def test_contained_patient_is_checked(tmp_path: Path) -> None:
    observation = {
        "resourceType": "Observation",
        "id": "syn-o00",
        "contained": [UNTAGGED],
        "subject": {"reference": "#syn-p00"},
    }
    assert any("HTEST" in p for p in check_file(write_json(tmp_path, observation)))


def test_patient_inside_parameters_is_checked(tmp_path: Path) -> None:
    parameters = {
        "resourceType": "Parameters",
        "parameter": [{"name": "patient", "resource": UNTAGGED}],
    }
    assert any("HTEST" in p for p in check_file(write_json(tmp_path, parameters)))


def test_synthetic_patient_inside_parameters_passes(tmp_path: Path) -> None:
    parameters = {
        "resourceType": "Parameters",
        "parameter": [{"name": "patient", "resource": synthetic_patient()}],
    }
    assert check_file(write_json(tmp_path, parameters)) == []


def test_patient_inside_any_nested_object_is_checked(tmp_path: Path) -> None:
    export = {"export": {"results": [{"data": UNTAGGED}]}}
    assert any("HTEST" in p for p in check_file(write_json(tmp_path, export)))


PERSON_TYPES = ["Practitioner", "RelatedPerson", "Person"]


@pytest.mark.parametrize("resource_type", PERSON_TYPES)
def test_synthetic_person_resource_passes(tmp_path: Path, resource_type: str) -> None:
    person = synthetic_patient(resourceType=resource_type)
    assert check_file(write_json(tmp_path, bundle(person))) == []


@pytest.mark.parametrize("resource_type", PERSON_TYPES)
def test_person_resource_with_realistic_name_fails(tmp_path: Path, resource_type: str) -> None:
    person = synthetic_patient(resourceType=resource_type, name=[{"family": "Smith"}])
    problems = check_file(write_json(tmp_path, bundle(person)))
    assert any(resource_type in p and "name" in p for p in problems)


@pytest.mark.parametrize("resource_type", PERSON_TYPES)
def test_person_resource_with_record_number_fails(tmp_path: Path, resource_type: str) -> None:
    person = synthetic_patient(
        resourceType=resource_type,
        identifier=[{"system": "http://hospital.example/mrn", "value": "MRN-1"}],
    )
    problems = check_file(write_json(tmp_path, bundle(person)))
    assert any(resource_type in p and "identifier" in p for p in problems)


@pytest.mark.parametrize("resource_type", PERSON_TYPES)
def test_person_resource_without_test_data_tag_fails(tmp_path: Path, resource_type: str) -> None:
    person = synthetic_patient(resourceType=resource_type, meta={})
    problems = check_file(write_json(tmp_path, bundle(person)))
    assert any(resource_type in p and "HTEST" in p for p in problems)


def test_any_resource_with_an_identifier_is_checked(tmp_path: Path) -> None:
    organization = {
        "resourceType": "Organization",
        "id": "syn-org",
        "identifier": [{"system": "http://hl7.org/fhir/sid/us-npi", "value": "1"}],
        "name": "Example Clinic",
    }
    problems = check_file(write_json(tmp_path, organization))
    assert any("HTEST" in p for p in problems)
    assert any("identifier" in p for p in problems)


def test_tagged_organization_with_a_plain_name_passes(tmp_path: Path) -> None:
    organization = {
        "resourceType": "Organization",
        "id": "syn-org",
        "meta": synthetic_patient()["meta"],
        "name": "Synthetic Test Clinic",
    }
    assert check_file(write_json(tmp_path, organization)) == []


def test_identifier_inside_a_reference_is_checked(tmp_path: Path) -> None:
    observation = {
        "resourceType": "Observation",
        "id": "syn-o00",
        "subject": {"identifier": {"system": "http://hospital.example/mrn", "value": "1"}},
    }
    assert any("identifier" in p for p in check_file(write_json(tmp_path, observation)))


def test_patient_contact_name_is_checked(tmp_path: Path) -> None:
    patient = synthetic_patient(contact=[{"name": {"family": "Smith", "given": ["John"]}}])
    assert any("name" in p for p in check_file(write_json(tmp_path, bundle(patient))))


@pytest.mark.parametrize("value", ["123456789", "123 45 6789", " 123456789 "])
def test_ssn_shaped_identifier_value_fails(tmp_path: Path, value: str) -> None:
    patient = synthetic_patient(
        identifier=[{"system": SYNTHETIC_IDENTIFIER_SYSTEM, "value": value}]
    )
    problems = check_file(write_json(tmp_path, bundle(patient)))
    assert any("SSN" in p for p in problems)


@pytest.mark.parametrize("value", ["SYN-0001", "SYN-10001", "12345678", "1234567890"])
def test_other_identifier_values_are_not_mistaken_for_ssns(tmp_path: Path, value: str) -> None:
    patient = synthetic_patient(
        identifier=[{"system": SYNTHETIC_IDENTIFIER_SYSTEM, "value": value}]
    )
    assert check_file(write_json(tmp_path, bundle(patient))) == []


def test_definitional_resources_are_not_held_to_person_rules(tmp_path: Path) -> None:
    capability = {
        "resourceType": "CapabilityStatement",
        "name": "example-server",
        "identifier": [{"system": "urn:ietf:rfc:3986", "value": "urn:oid:2.16.0"}],
        "contact": [{"name": "API Support"}],
    }
    assert check_file(write_json(tmp_path, capability)) == []


def test_json_file_that_does_not_parse_fails(tmp_path: Path) -> None:
    path = write_text(tmp_path, "bundle.json", '{"resourceType": "Patient",')
    assert any("JSON" in p for p in check_file(path))


@pytest.mark.parametrize("suffix", [".ndjson", ".jsonl"])
def test_json_lines_file_with_a_bad_line_fails(tmp_path: Path, suffix: str) -> None:
    path = write_text(tmp_path, f"patients{suffix}", f"{json.dumps(synthetic_patient())}\n{{\n")
    assert any("line 2" in p for p in check_file(path))


@pytest.mark.parametrize("suffix", [".json", ".ndjson", ".jsonl", ".xml"])
def test_structured_file_that_is_not_utf8_fails(tmp_path: Path, suffix: str) -> None:
    path = tmp_path / f"export{suffix}"
    path.write_bytes(b"\xff\xfe{\x00")
    assert check_file(path) != []


def test_path_that_cannot_be_read_fails(tmp_path: Path) -> None:
    assert check_file(tmp_path) != []


def test_json_with_a_byte_order_mark_is_checked(tmp_path: Path) -> None:
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(UNTAGGED), encoding="utf-8-sig")
    assert any("HTEST" in p for p in check_file(path))


@pytest.mark.parametrize(
    ("name", "text"),
    [
        ("export.txt", json.dumps([UNTAGGED], indent=2)),
        ("export", f"  {json.dumps(UNTAGGED)}"),
        ("export.log", f"{json.dumps(synthetic_patient())}\n{json.dumps(UNTAGGED)}\n"),
    ],
)
def test_json_is_detected_by_content(tmp_path: Path, name: str, text: str) -> None:
    assert any("HTEST" in p for p in check_file(write_text(tmp_path, name, text)))


def test_toml_is_not_mistaken_for_json(tmp_path: Path) -> None:
    path = write_text(tmp_path, "value_set.toml", '[metadata]\nname = "x"\ncodes = [\n  "a",\n]\n')
    assert check_file(path) == []


FHIR_XML = '<Patient xmlns="http://hl7.org/fhir"><name><family value="X"/></name></Patient>'


@pytest.mark.parametrize(
    ("name", "text"),
    [
        ("patient.xml", FHIR_XML),
        ("patient.xml", "<Patient><id value='p'/></Patient>"),
        ("bundle.xml", "<f:Bundle xmlns:f='http://hl7.org/fhir'/>"),
        ("export.txt", f"<?xml version='1.0'?>\n{FHIR_XML}"),
    ],
)
def test_fhir_xml_fails(tmp_path: Path, name: str, text: str) -> None:
    assert any("XML" in p for p in check_file(write_text(tmp_path, name, text)))


def test_other_xml_passes(tmp_path: Path) -> None:
    path = write_text(tmp_path, "build.xml", "<project><name>adhd-mcp</name></project>")
    assert check_file(path) == []


def test_pre_commit_hook_runs_the_guard_and_stops_the_commit_when_it_fails(
    tmp_path: Path,
) -> None:
    """The hook delegates to the guard through uv; a stub uv stands in for the real one."""
    record = tmp_path / "uv-arguments"
    stub = tmp_path / "bin" / "uv"
    stub.parent.mkdir()
    stub.write_text(f'#!/bin/sh\necho "$@" > "{record}"\nexit 1\n', encoding="utf-8")
    stub.chmod(0o755)
    hook = REPOSITORY / "scripts" / "pre-commit"
    env = {**os.environ, "PATH": f"{stub.parent}{os.pathsep}{os.environ['PATH']}"}
    result = subprocess.run([hook], cwd=REPOSITORY, env=env, check=False)  # noqa: S603
    assert result.returncode != 0
    assert record.read_text(encoding="utf-8").split() == [
        "run",
        "python",
        "scripts/check_synthetic_data.py",
    ]
