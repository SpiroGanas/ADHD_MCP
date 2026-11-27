"""Check every ICD-10-CM value set against an ICD-10-CM tabular list XML file.

Usage: uv run python scripts/verify_icd10cm_value_sets.py PATH/TO/icd10c-tabular-*.xml

The file's sha256 must equal EXPECTED_SHA256 (or pass --sha256 for a newer release), so a
tampered or unexpected file is never parsed. The script reports, for each value set, how
many tabular codes it matches, and runs these checks (exit code 1 if any fails):

* every exact or prefix entry names a code that exists in the tabular list;
* the poisoning regexes match exactly the T36-T65 codes whose titles say "intentional
  self-harm" (or "undetermined"), and no header code;
* the motor-vehicle driver set matches only driver codes, never "(driver) (passenger)";
* injury and accidental external-cause sets match no self-harm or assault code.

Run on 2026-11-27 against the FY2027 tabular downloaded from ftp.cdc.gov (the pinned hash
below); the output is recorded in docs/clinical/verification/icd10cm_fy2027_check.md. The
earlier FY2026 run is in docs/clinical/verification/icd10cm_fy2026_check.md.
"""

import argparse
import hashlib
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from adhd_mcp.fhir.codes import ICD10CM, Coding  # noqa: E402
from adhd_mcp.terminology import load_value_set, packaged_value_set_ids  # noqa: E402

POISONING_SETS = {
    "safety.intentional_self_poisoning": "intentional self-harm",
    "safety.undetermined_intent_poisoning": "undetermined",
}
EXPECTED_SHA256 = "d778c97a5bb9da7d71645610e277f8db3bd302befa3b08d71dd5043715a74b2a"


def parse_tabular(path: Path) -> dict[str, dict[str, Any]]:
    root = ET.parse(path).getroot()  # noqa: S314 - hash-pinned file
    codes: dict[str, dict[str, Any]] = {}

    def walk(element: ET.Element, inherited: list[str]) -> None:
        for diag in element.findall("diag"):
            seven = diag.find("sevenChrDef")
            chars = (
                [e.get("char") or "" for e in seven.findall("extension")]
                if seven is not None
                else inherited
            )
            codes[diag.findtext("name") or ""] = {
                "title": diag.findtext("desc") or "",
                "leaf": diag.find("diag") is None,
                "seven": chars,
            }
            walk(diag, chars)

    for chapter in root.iter("chapter"):
        for section in chapter.findall("section"):
            walk(section, [])
    return codes


def full_forms(code: str, info: dict[str, Any]) -> list[str]:
    if not info["seven"]:
        return [code]
    base = code.replace(".", "").ljust(6, "X")
    return [f"{base[:3]}.{base[3:]}{char}" for char in info["seven"]]


def check(codes: dict[str, dict[str, Any]]) -> int:
    leaves = {c: i for c, i in codes.items() if i["leaf"]}
    forms = [(f, c) for c, i in leaves.items() for f in full_forms(c, i)]
    problems = 0
    for value_set_id in packaged_value_set_ids():
        value_set = load_value_set(value_set_id, strict=False)
        if not any(e.system == ICD10CM for e in value_set.entries):
            continue
        for entry in value_set.entries:
            if entry.match != "regex" and entry.code not in codes:
                print(f"  MISSING: {value_set_id} names {entry.code}")
                problems += 1
        hits = {c for f, c in forms if value_set.matches(Coding(system=ICD10CM, code=f))}
        print(f"{value_set_id}: {len(hits)} tabular codes")
        title = {c: leaves[c]["title"].lower() for c in hits}
        word = POISONING_SETS.get(value_set_id)
        if word is not None:
            expected = {
                c
                for c, i in leaves.items()
                if "T36" <= c[:3] <= "T65" and word in i["title"].lower()
            }
            headers = [
                c
                for c, i in codes.items()
                if not i["leaf"] and value_set.matches(Coding(system=ICD10CM, code=c))
            ]
            ok = hits == expected and not headers
            print(f"  matches exactly the {len(expected)} '{word}' codes, no headers: {ok}")
            problems += not ok
        if value_set_id == "injury.motor_vehicle_driver":
            bad = [c for c, t in title.items() if "driver" not in t or "(driver) (passenger)" in t]
            print(f"  non-driver codes matched: {len(bad)}")
            problems += len(bad)
        if value_set_id in {"injury.injury_codes", "injury.accidental_external_cause"}:
            bad = [
                c for c, t in title.items() if "self-harm" in t or "suicide" in t or "assault" in t
            ]
            print(f"  self-harm or assault codes matched: {len(bad)}")
            problems += len(bad)
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tabular_xml", type=Path)
    parser.add_argument("--sha256", default=EXPECTED_SHA256)
    args = parser.parse_args()
    digest = hashlib.sha256(args.tabular_xml.read_bytes()).hexdigest()
    if digest != args.sha256:
        raise SystemExit(f"sha256 {digest} does not match the expected file")
    problems = check(parse_tabular(args.tabular_xml))
    print(f"{problems} problem(s)")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
