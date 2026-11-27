import pytest
from pydantic import ValidationError

from adhd_mcp.fhir.codes import ICD10CM, RXNORM, Coding
from adhd_mcp.terminology import UnverifiedContentError
from adhd_mcp.terminology.drug_classes import (
    DrugClass,
    load_drug_class,
    packaged_drug_class_ids,
    parse_drug_class,
)

VERIFIED = {
    "verified": True,
    "source": "test source",
    "source_version": "RxNorm test",
    "checked_on": "2026-11-27",
    "checked_by": "test",
}


def drug_class(*ingredients: dict[str, object]) -> DrugClass:
    return DrugClass.model_validate(
        {"id": "med.test", "version": "1.0.0", "title": "Test", "ingredients": list(ingredients)}
    )


def rx(code: str) -> Coding:
    return Coding(system=RXNORM, code=code)


def test_an_ingredient_code_maps_to_its_ingredient() -> None:
    dc = drug_class({"rxcui": "6901", "name": "methylphenidate", "products": [], **VERIFIED})
    assert [i.name for i in dc.ingredients_for((rx("6901"),))] == ["methylphenidate"]


def test_a_product_code_maps_to_every_class_ingredient_it_contains() -> None:
    dc = drug_class(
        {"rxcui": "725", "name": "amphetamine", "products": ["111"], **VERIFIED},
        {"rxcui": "3288", "name": "dextroamphetamine", "products": ["111", "222"], **VERIFIED},
    )
    assert [i.name for i in dc.ingredients_for((rx("111"),))] == [
        "amphetamine",
        "dextroamphetamine",
    ]
    assert [i.name for i in dc.ingredients_for((rx("222"),))] == ["dextroamphetamine"]


def test_other_systems_and_unknown_codes_do_not_match() -> None:
    dc = drug_class({"rxcui": "6901", "name": "methylphenidate", "products": [], **VERIFIED})
    assert dc.ingredients_for((Coding(system=ICD10CM, code="6901"), rx("1"))) == ()


def test_a_verified_ingredient_needs_provenance() -> None:
    with pytest.raises(ValidationError, match="source"):
        drug_class({"rxcui": "1", "name": "x", "products": [], "verified": True})


def test_strict_parsing_refuses_unverified_ingredients() -> None:
    text = """
id = "med.test"
version = "1.0.0"
title = "Test"
[[ingredients]]
rxcui = "1"
name = "x"
verified = false
products = []
"""
    with pytest.raises(UnverifiedContentError, match=r"med\.test"):
        parse_drug_class(text, name="med.test", strict=True)
    assert parse_drug_class(text, name="med.test", strict=False).id == "med.test"


def test_file_name_must_match_the_class_id() -> None:
    text = 'id = "med.other"\nversion = "1"\ntitle = "t"\ningredients = []\n'
    with pytest.raises(ValueError, match=r"does not match"):
        parse_drug_class(text, name="med.test", strict=False)


def test_packaged_classes_load_strictly_and_cover_the_rule_classes() -> None:
    ids = packaged_drug_class_ids()
    assert {
        "med.adhd_stimulant",
        "med.adhd_nonstimulant",
        "med.antidepressant",
        "med.sedative_hypnotic",
    } <= set(ids)
    for class_id in ids:
        assert load_drug_class(class_id).ingredients


def test_persona_ingredient_codes_are_in_the_packaged_classes() -> None:
    stimulants = load_drug_class("med.adhd_stimulant")
    antidepressants = load_drug_class("med.antidepressant")
    assert [i.name for i in stimulants.ingredients_for((rx("6901"),))] == ["methylphenidate"]
    assert [i.name for i in stimulants.ingredients_for((rx("725"),))] == ["amphetamine"]
    for code in ("36437", "321988", "42347", "39786", "4493"):
        assert len(antidepressants.ingredients_for((rx(code),))) == 1


def test_unknown_packaged_class_is_a_lookup_error() -> None:
    with pytest.raises(LookupError):
        load_drug_class("med.nothing")
