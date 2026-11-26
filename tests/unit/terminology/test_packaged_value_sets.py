"""The packaged value sets: all load, and representative codes match as verified."""

import pytest

from adhd_mcp.fhir.codes import ICD10CM, Coding
from adhd_mcp.terminology import load_value_set, packaged_value_set_ids


def test_every_packaged_value_set_loads_and_strict_mode_follows_verification() -> None:
    ids = packaged_value_set_ids()
    assert len(ids) >= 30
    for value_set_id in ids:
        value_set = load_value_set(value_set_id, strict=False)
        assert value_set.entries, value_set_id
        if not value_set.unverified_entries():
            load_value_set(value_set_id, strict=True)


@pytest.mark.parametrize(
    ("value_set_id", "matching", "not_matching"),
    [
        ("safety.suicidal_ideation", ["R45.851"], ["R45.850", "R45.85"]),
        ("safety.suicide_attempt", ["T14.91XA", "T14.91XD", "T14.91XS"], ["T14.90XA"]),
        (
            "safety.intentional_self_poisoning",
            ["T36.0X2A", "T40.602A", "T36.92XA", "T50.A12A", "T65.822S", "T36.0X2"],
            ["T36.0X1A", "T36.0X4A", "T43.62", "T35.0X2A", "T66.XXXA", "T36.92A"],
        ),
        (
            "safety.undetermined_intent_poisoning",
            ["T36.0X4A", "T42.74XA", "T51.0X4D"],
            ["T36.0X2A", "T43.64"],
        ),
        ("safety.intentional_self_harm_external_cause", ["X71.0XXA", "X83.8XXA"], ["X70", "X84"]),
        ("safety.history_suicidal_behavior", ["Z91.51"], ["Z91.52", "Z91.5"]),
        ("care.adhd_diagnosis", ["F90.0", "F90.9"], ["F91.0", "F900"]),
        ("sud.stimulant", ["F15.10", "F15.20", "F15.90"], ["F14.10", "F150"]),
        (
            "injury.motor_vehicle_driver",
            ["V43.52XA", "V40.0XXA", "V49.40XA", "V23.49XA", "V29.0XXA"],
            ["V43.62XA", "V49.3XXA", "V49.9XXA", "V29.3XXA", "V43.1XXA"],
        ),
        ("injury.injury_codes", ["S06.0X0A", "T14.90XA", "T34.0XXA"], ["T14.91XA", "T36.0X1A"]),
        ("injury.accidental_external_cause", ["W01.0XXA", "X58.XXXA", "X50.0XXA"], ["X71.0XXA"]),
        ("psychosocial.housing_instability", ["Z59.811"], ["Z59.00", "Z59.10"]),
        ("psychosocial.legal_problems", ["Z65.0", "Z65.3"], ["Z65.4"]),
        ("family.mental_behavioral_history", ["Z81.8"], ["Z82.0", "Z81.1"]),
    ],
)
def test_representative_codes(
    value_set_id: str, matching: list[str], not_matching: list[str]
) -> None:
    value_set = load_value_set(value_set_id)
    for code in matching:
        assert value_set.matches(Coding(system=ICD10CM, code=code)), code
    for code in not_matching:
        assert value_set.matches(Coding(system=ICD10CM, code=code)) is None, code
