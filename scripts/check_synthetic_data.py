"""Block files that resemble real patient data.

Rules:

* Every FHIR ``Patient`` in a JSON file (bare, or inside a ``Bundle``) must carry the HL7
  ``HTEST`` (test health data) tag, use only the project's synthetic identifier system, and
  have the family name ``Synthetic``.
* No text file may contain a US Social Security number pattern.

Runs on every tracked and untracked (not ignored) file:
``uv run python scripts/check_synthetic_data.py``.
Exit code 1 if anything is found.
"""

import json
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

SYNTHETIC_IDENTIFIER_SYSTEM = "urn:adhd-mcp:synthetic-id"
SYNTHETIC_FAMILY_NAME = "Synthetic"
TEST_DATA_TAG = ("http://terminology.hl7.org/CodeSystem/v3-ActReason", "HTEST")

_SSN = re.compile(r"(?<![\d-])\d{3}-\d{2}-\d{4}(?![\d-])")


def _patients(document: Any) -> Iterator[dict[str, Any]]:
    if not isinstance(document, dict):
        return
    if document.get("resourceType") == "Patient":
        yield document
    elif document.get("resourceType") == "Bundle":
        for entry in document.get("entry") or []:
            yield from _patients(entry.get("resource"))


def _patient_problems(patient: dict[str, Any]) -> list[str]:
    pid = patient.get("id", "<no id>")
    problems: list[str] = []
    tags = {(t.get("system"), t.get("code")) for t in (patient.get("meta") or {}).get("tag", [])}
    if TEST_DATA_TAG not in tags:
        problems.append(f"Patient {pid}: missing the HTEST test-data tag")
    for identifier in patient.get("identifier") or []:
        if identifier.get("system") != SYNTHETIC_IDENTIFIER_SYSTEM:
            problems.append(
                f"Patient {pid}: identifier system is not {SYNTHETIC_IDENTIFIER_SYSTEM}"
            )
    for name in patient.get("name") or []:
        if name.get("family") != SYNTHETIC_FAMILY_NAME:
            problems.append(f"Patient {pid}: name family is not '{SYNTHETIC_FAMILY_NAME}'")
    return problems


def check_file(path: Path) -> list[str]:
    """Problems found in one file, each prefixed with nothing; empty if clean."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    problems: list[str] = []
    if _SSN.search(text):
        problems.append("contains an SSN-shaped number")
    if path.suffix in {".json", ".ndjson"}:
        lines = text.splitlines() if path.suffix == ".ndjson" else [text]
        for line in lines:
            try:
                document = json.loads(line)
            except json.JSONDecodeError:
                continue
            for patient in _patients(document):
                problems.extend(_patient_problems(patient))
    return problems


def repository_files(root: Path) -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],  # noqa: S607
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [root / line for line in out.splitlines() if (root / line).is_file()]


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    failures = 0
    for path in repository_files(root):
        for problem in check_file(path):
            failures += 1
            print(f"{path.relative_to(root)}: {problem}")
    if failures:
        print(f"{failures} problem(s): files must contain synthetic data only.")
        return 1
    print("No files resembling real patient data found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
