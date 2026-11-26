from pathlib import Path

import pytest
from pydantic import ValidationError

from adhd_mcp.fhir.codes import ICD10CM, LOINC, Coding
from adhd_mcp.terminology import (
    UnverifiedContentError,
    ValueSet,
    load_value_set,
    load_value_set_file,
)

VERIFIED = {
    "verified": True,
    "source": "test source",
    "source_version": "FY2026",
    "checked_on": "2026-11-26",
    "checked_by": "test",
}


def value_set(*entries: dict[str, object]) -> ValueSet:
    return ValueSet.model_validate(
        {"id": "test.set", "version": "1.0.0", "title": "Test", "entries": list(entries)}
    )


def icd(code: str) -> Coding:
    return Coding(system=ICD10CM, code=code)


def test_icd10cm_prefix_matches_codes_in_the_family() -> None:
    vs = value_set({"system": ICD10CM, "match": "prefix", "code": "F15", **VERIFIED})
    assert vs.matches(icd("F15")) is not None
    assert vs.matches(icd("F15.8")) is not None
    assert vs.matches(icd("F15.10")) is not None


def test_icd10cm_prefix_does_not_match_across_the_category_boundary() -> None:
    vs = value_set({"system": ICD10CM, "match": "prefix", "code": "F15", **VERIFIED})
    assert vs.matches(icd("F150")) is None
    assert vs.matches(icd("F1")) is None
    assert vs.matches(icd("F16.10")) is None


def test_dotted_prefix_matches_deeper_codes_only() -> None:
    vs = value_set({"system": ICD10CM, "match": "prefix", "code": "T14.91", **VERIFIED})
    assert vs.matches(icd("T14.91XA")) is not None
    assert vs.matches(icd("T14.90XA")) is None
    assert vs.matches(icd("T14.9")) is None


def test_exact_match_does_not_match_children() -> None:
    vs = value_set({"system": ICD10CM, "match": "exact", "code": "R45.851", **VERIFIED})
    assert vs.matches(icd("R45.851")) is not None
    assert vs.matches(icd("R45.8510")) is None
    assert vs.matches(icd("R45.85")) is None


def test_system_must_match() -> None:
    vs = value_set({"system": LOINC, "match": "exact", "code": "44260-8", **VERIFIED})
    assert vs.matches(Coding(system=LOINC, code="44260-8")) is not None
    assert vs.matches(Coding(system="http://other", code="44260-8")) is None
    assert vs.matches(Coding(system=None, code="44260-8")) is None


def test_regex_entry_uses_a_full_match() -> None:
    vs = value_set({"system": ICD10CM, "match": "regex", "code": r"T36\.0X2[ADS]?", **VERIFIED})
    assert vs.matches(icd("T36.0X2A")) is not None
    assert vs.matches(icd("T36.0X2")) is not None
    assert vs.matches(icd("XT36.0X2A")) is None
    assert vs.matches(icd("T36.0X1A")) is None


def test_matches_any_returns_every_matching_coding() -> None:
    vs = value_set({"system": ICD10CM, "match": "prefix", "code": "F90", **VERIFIED})
    codings = (icd("F90.0"), Coding(system="http://snomed.info/sct", code="1"), icd("F90.9"))
    assert vs.matching_codings(codings) == (icd("F90.0"), icd("F90.9"))


def test_prefix_entries_are_only_allowed_for_icd10cm() -> None:
    with pytest.raises(ValidationError, match="prefix"):
        value_set({"system": LOINC, "match": "prefix", "code": "442", **VERIFIED})


def test_invalid_regex_is_rejected() -> None:
    with pytest.raises(ValidationError, match="regex"):
        value_set({"system": ICD10CM, "match": "regex", "code": "T36(", **VERIFIED})


def test_verified_entry_needs_its_provenance() -> None:
    with pytest.raises(ValidationError, match="source"):
        value_set({"system": ICD10CM, "match": "exact", "code": "R45.851", "verified": True})


def test_strict_mode_refuses_unverified_entries(tmp_path: Path) -> None:
    path = tmp_path / "test.set.toml"
    path.write_text(
        'id = "test.set"\nversion = "1.0.0"\ntitle = "Test"\n'
        '[[entries]]\nsystem = "http://hl7.org/fhir/sid/icd-10-cm"\n'
        'match = "exact"\ncode = "R45.851"\nverified = false\n',
        encoding="utf-8",
    )
    with pytest.raises(UnverifiedContentError, match=r"test\.set.*R45\.851"):
        load_value_set_file(path, strict=True)
    loaded = load_value_set_file(path, strict=False)
    assert loaded.unverified_entries()[0].code == "R45.851"


def test_file_name_must_match_the_id(tmp_path: Path) -> None:
    path = tmp_path / "other.toml"
    path.write_text('id = "test.set"\nversion = "1.0.0"\ntitle = "T"\nentries = []\n')
    with pytest.raises(ValueError, match="file name"):
        load_value_set_file(path, strict=False)


def test_packaged_value_set_is_loaded_by_id() -> None:
    vs = load_value_set("safety.suicidal_ideation", strict=False)
    assert vs.id == "safety.suicidal_ideation"


def test_unknown_value_set_id_is_an_error() -> None:
    with pytest.raises(LookupError, match=r"no\.such"):
        load_value_set("no.such", strict=False)
