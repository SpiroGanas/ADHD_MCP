from pathlib import Path

import pytest

from adhd_mcp.fhir.codes import LOINC
from adhd_mcp.terminology import UnverifiedContentError
from adhd_mcp.terminology.instruments import (
    Instrument,
    load_instrument,
    load_instrument_file,
    packaged_instrument_ids,
)

PHQ9 = """
id = "phq9"
version = "0.1.0"
title = "PHQ-9"

[[codes]]
role = "item"
item = "9"
system = "http://loinc.org"
code = "44260-8"
verified = false

[[cutoffs]]
id = "item9_positive"
code = "44260-8"
operator = ">="
value = 1
verified = false
"""


def write(tmp_path: Path, text: str, name: str = "phq9") -> Path:
    path = tmp_path / f"{name}.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_unverified_instrument_is_refused_in_strict_mode(tmp_path: Path) -> None:
    with pytest.raises(UnverifiedContentError, match=r"phq9.*44260-8.*item9_positive"):
        load_instrument_file(write(tmp_path, PHQ9), strict=True)


def test_non_strict_loading_exposes_codes_and_cutoffs(tmp_path: Path) -> None:
    instrument = load_instrument_file(write(tmp_path, PHQ9), strict=False)
    assert isinstance(instrument, Instrument)
    assert instrument.code_for("item", item="9") == (LOINC, "44260-8")
    cutoff = instrument.cutoff("item9_positive")
    assert cutoff.is_met(1) is True
    assert cutoff.is_met(0) is False


def test_sex_specific_cutoffs_are_selected_by_sex(tmp_path: Path) -> None:
    text = PHQ9.replace('id = "item9_positive"', 'id = "positive"\nsex = "female"') + (
        '\n[[cutoffs]]\nid = "positive"\nsex = "male"\ncode = "44260-8"\noperator = ">="\n'
        "value = 2\nverified = false\n"
    )
    instrument = load_instrument_file(write(tmp_path, text), strict=False)
    assert instrument.cutoff("positive", sex="female").value == 1
    assert instrument.cutoff("positive", sex="male").value == 2
    with pytest.raises(LookupError):
        instrument.cutoff("positive")


def test_cutoff_must_reference_one_of_the_instrument_codes(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not a code of"):
        load_instrument_file(
            write(tmp_path, PHQ9.replace('code = "44260-8"\nop', 'code = "1-1"\nop')), strict=False
        )


def test_packaged_instruments_load() -> None:
    ids = packaged_instrument_ids()
    assert {"phq9", "phq2", "cssrs_screener", "auditc", "pcptsd5", "asrs5"} <= set(ids)
    for instrument_id in ids:
        assert load_instrument(instrument_id, strict=False).id == instrument_id


def test_unknown_instrument_is_an_error() -> None:
    with pytest.raises(LookupError):
        load_instrument("nope", strict=False)
