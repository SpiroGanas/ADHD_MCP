import datetime as dt
import tomllib
from typing import Any

import pytest
from scripts import build_drug_classes as script

from adhd_mcp.terminology.drug_classes import parse_drug_class


def fake_rxnav(responses: dict[str, Any]) -> script.Fetch:
    def fetch(path: str) -> Any:
        key = path.split("?", maxsplit=1)[0] if path.startswith("rxcui/") else path
        return responses[key]

    return fetch


METHYLPHENIDATE = {
    "rxcui.json?name=methylphenidate&search=0": {"idGroup": {"rxnormId": ["6901"]}},
    "rxcui/6901/properties.json": {
        "properties": {"rxcui": "6901", "name": "methylphenidate", "tty": "IN", "suppress": "N"}
    },
    "rxcui/6901/related.json": {
        "relatedGroup": {
            "conceptGroup": [
                {"tty": "SCD", "conceptProperties": [{"rxcui": "1091170"}, {"rxcui": "99"}]},
                {"tty": "BPCK"},
            ]
        }
    },
}


def test_ingredient_returns_its_rxcui_and_sorted_products() -> None:
    assert script.ingredient("methylphenidate", fake_rxnav(METHYLPHENIDATE)) == (
        "6901",
        ["99", "1091170"],
    )


def test_a_name_that_is_not_an_active_ingredient_stops_the_build() -> None:
    responses: dict[str, Any] = dict(METHYLPHENIDATE)
    responses["rxcui/6901/properties.json"] = {
        "properties": {"rxcui": "6901", "name": "methylphenidate", "tty": "PIN", "suppress": "N"}
    }
    with pytest.raises(script.BuildError, match="PIN"):
        script.ingredient("methylphenidate", fake_rxnav(responses))


def test_an_ambiguous_or_unknown_name_stops_the_build() -> None:
    responses: dict[str, Any] = {"rxcui.json?name=nothing&search=0": {"idGroup": {}}}
    with pytest.raises(script.BuildError, match="expected one"):
        script.ingredient("nothing", fake_rxnav(responses))


def test_render_writes_a_verified_strictly_loadable_class() -> None:
    text = script.render(
        {"id": "med.test", "title": "Test", "ingredients": ["methylphenidate"]},
        fake_rxnav(METHYLPHENIDATE),
        "02-Nov-2026",
        dt.date(2026, 11, 27),
    )
    raw = tomllib.loads(text)
    assert raw["ingredients"][0]["source_version"] == "RxNorm 02-Nov-2026"
    loaded = parse_drug_class(text, name="med.test", strict=True)
    assert loaded.ingredients[0].products == ("99", "1091170")
