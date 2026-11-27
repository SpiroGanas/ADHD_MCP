from adhd_mcp.fhir.codes import (
    ICD10CM,
    LOINC,
    RXNORM,
    SNOMED,
    Coding,
    normalize_coding,
    normalize_concept,
)


def test_condition_with_icd10cm_and_snomed_codings_keeps_both() -> None:
    concept = {
        "coding": [
            {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "f15.10", "display": "x"},
            {"system": "http://snomed.info/sct", "code": "  191939002 "},
        ],
        "text": "free text is not kept",
    }
    assert normalize_concept(concept) == (
        Coding(system=ICD10CM, code="F15.10", display="x"),
        Coding(system=SNOMED, code="191939002"),
    )


def test_oid_systems_map_to_canonical_uris() -> None:
    assert normalize_coding({"system": "urn:oid:2.16.840.1.113883.6.90", "code": "R45.851"}) == (
        Coding(system=ICD10CM, code="R45.851")
    )
    assert normalize_coding({"system": "urn:oid:2.16.840.1.113883.6.1", "code": "44260-8"}) == (
        Coding(system=LOINC, code="44260-8")
    )
    assert normalize_coding({"system": "urn:oid:2.16.840.1.113883.6.88", "code": "1"}) == (
        Coding(system=RXNORM, code="1")
    )


def test_unknown_system_is_kept_as_written() -> None:
    coding = normalize_coding({"system": "http://va.example/local", "code": "ABC"})
    assert coding == Coding(system="http://va.example/local", code="ABC")


def test_coding_without_a_code_is_dropped() -> None:
    assert normalize_coding({"system": ICD10CM, "display": "x"}) is None
    assert normalize_coding({"system": ICD10CM, "code": "   "}) is None


def test_coding_without_a_system_is_kept_with_none() -> None:
    assert normalize_coding({"code": "X"}) == Coding(system=None, code="X")


def test_missing_concept_is_empty() -> None:
    assert normalize_concept(None) == ()
    assert normalize_concept({"text": "only text"}) == ()
