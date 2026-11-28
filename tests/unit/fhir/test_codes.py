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


def test_icd10cm_code_without_the_dot_gets_the_dot_after_the_category() -> None:
    # Peer review 01, S1 (E8b): "R45851" must match the value set entry "R45.851".
    assert normalize_coding({"system": ICD10CM, "code": "R45851"}) == Coding(
        system=ICD10CM, code="R45.851"
    )
    assert normalize_coding({"system": ICD10CM, "code": "t1491xa"}) == Coding(
        system=ICD10CM, code="T14.91XA"
    )
    assert normalize_coding({"system": ICD10CM, "code": "F3290"}) == Coding(
        system=ICD10CM, code="F32.90"
    )


def test_icd10cm_category_and_dotted_codes_are_unchanged() -> None:
    assert normalize_coding({"system": ICD10CM, "code": "F32"}) == Coding(
        system=ICD10CM, code="F32"
    )
    assert normalize_coding({"system": ICD10CM, "code": "F32.9"}) == Coding(
        system=ICD10CM, code="F32.9"
    )


def test_a_code_that_is_not_icd10cm_shaped_is_not_repaired() -> None:
    # Too long, or not a letter and two characters: kept as sent, so it matches nothing.
    assert normalize_coding({"system": ICD10CM, "code": "R458511X"}).code == "R458511X"  # type: ignore[union-attr]
    assert normalize_coding({"system": ICD10CM, "code": "1234"}).code == "1234"  # type: ignore[union-attr]
    # Other systems are never given a dot.
    assert normalize_coding({"system": SNOMED, "code": "6471006"}).code == "6471006"  # type: ignore[union-attr]
