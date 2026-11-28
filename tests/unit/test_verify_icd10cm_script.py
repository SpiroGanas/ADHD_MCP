from pathlib import Path

import pytest
from scripts import verify_icd10cm_value_sets as script
from scripts.verify_icd10cm_value_sets import full_forms, parse_tabular

TABULAR = """<?xml version="1.0"?>
<ICD10CM.tabular><chapter><section>
  <diag><name>T14</name><desc>Injury of unspecified body region</desc>
    <sevenChrDef><extension char="A">initial</extension><extension char="D">subs</extension>
    </sevenChrDef>
    <diag><name>T14.9</name><desc>Injury, unspecified</desc>
      <diag><name>T14.91</name><desc>Suicide attempt</desc></diag>
    </diag>
  </diag>
  <diag><name>R45.851</name><desc>Suicidal ideations</desc></diag>
</section></chapter></ICD10CM.tabular>
"""


def test_parse_tabular_inherits_seventh_characters(tmp_path: Path) -> None:
    path = tmp_path / "t.xml"
    path.write_text(TABULAR, encoding="utf-8")
    codes = parse_tabular(path)
    assert codes["T14.91"] == {"title": "Suicide attempt", "leaf": True, "seven": ["A", "D"]}
    assert codes["T14.9"]["leaf"] is False
    assert full_forms("T14.91", codes["T14.91"]) == ["T14.91XA", "T14.91XD"]
    assert full_forms("R45.851", codes["R45.851"]) == ["R45.851"]


def test_refuses_a_file_with_an_unexpected_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "t.xml"
    path.write_text(TABULAR, encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["verify", str(path)])
    with pytest.raises(SystemExit, match="does not match"):
        script.main()


def test_check_counts_a_value_set_code_the_tabular_lacks(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Peer review 01, T5: check() stands behind every verified ICD-10-CM entry and was untested.
    monkeypatch.setattr(script, "packaged_value_set_ids", lambda: ["safety.suicidal_ideation"])
    present = {"R45.851": {"title": "Suicidal ideations", "leaf": True, "seven": []}}
    assert script.check(present) == 0
    assert script.check({}) == 1
    assert "MISSING: safety.suicidal_ideation names R45.851" in capsys.readouterr().out
