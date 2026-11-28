"""Block files that resemble real patient data.

Resource rules. They apply to every FHIR resource found anywhere in a JSON document: bare,
in a ``Bundle``, ``contained``, inside ``Parameters``, an item of a JSON array or any other
nested object. Definitional resources (``CapabilityStatement``, ``ValueSet`` and the other
canonical resources) are exempt: their names are machine names and they describe no person.

* A ``Patient``, ``Practitioner``, ``RelatedPerson`` or ``Person``, and every other resource
  that carries a ``name`` or an ``identifier``, must carry the HL7 ``HTEST`` (test health data)
  tag.
* Every identifier in the resource, wherever it sits (a reference's identifier included), must
  use the project's synthetic identifier system, and its value must not be shaped like a US
  Social Security number, with or without dashes.
* Every human name in the resource (any object under a ``name`` key, ``Patient.contact.name``
  included) must have the family name ``Synthetic``.

File rules. The guard fails closed on what it cannot inspect.

* No text file may contain a dashed US Social Security number pattern.
* A ``.json`` file must parse as JSON, and every line of a ``.ndjson`` or ``.jsonl`` file must
  parse as JSON. A ``.json``, ``.ndjson``, ``.jsonl`` or ``.xml`` file that is not UTF-8 fails,
  and so does any file that cannot be read. Other binary files (images) are skipped.
* JSON is also detected by content: any other file whose first non-blank character is ``{`` or
  ``[`` is checked as one JSON document if it parses, else line by line as JSON Lines; there,
  lines that do not parse are ignored (a TOML file can start with ``[`` too).
* FHIR XML fails: a ``.xml`` file, or a file whose content starts with ``<``, that names the
  ``http://hl7.org/fhir`` namespace or has a ``<Patient`` element. The guard does not read XML,
  so FHIR data in this repository is stored as JSON.

Runs on every tracked and untracked (not ignored) file:
``uv run python scripts/check_synthetic_data.py``. ``scripts/pre-commit`` runs it as a git
pre-commit hook. Exit code 1 if anything is found.
"""

import json
import re
import subprocess
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

SYNTHETIC_IDENTIFIER_SYSTEM = "urn:adhd-mcp:synthetic-id"
SYNTHETIC_FAMILY_NAME = "Synthetic"
TEST_DATA_TAG = ("http://terminology.hl7.org/CodeSystem/v3-ActReason", "HTEST")

# Resources that describe a person need the test-data tag even without a name or identifier.
PERSON_RESOURCE_TYPES = frozenset({"Patient", "Practitioner", "RelatedPerson", "Person"})
# The FHIR R4 canonical resources: their name is a machine name and their identifiers name the
# artifact. Resources nested inside them are still checked.
DEFINITIONAL_RESOURCE_TYPES = frozenset(
    {
        "ActivityDefinition",
        "CapabilityStatement",
        "ChargeItemDefinition",
        "CodeSystem",
        "CompartmentDefinition",
        "ConceptMap",
        "EffectEvidenceSynthesis",
        "EventDefinition",
        "Evidence",
        "EvidenceVariable",
        "ExampleScenario",
        "GraphDefinition",
        "ImplementationGuide",
        "Library",
        "Measure",
        "MessageDefinition",
        "NamingSystem",
        "OperationDefinition",
        "PlanDefinition",
        "Questionnaire",
        "ResearchDefinition",
        "ResearchElementDefinition",
        "RiskEvidenceSynthesis",
        "SearchParameter",
        "StructureDefinition",
        "StructureMap",
        "TerminologyCapabilities",
        "TestScript",
        "ValueSet",
    }
)

JSON_SUFFIXES = frozenset({".json"})
JSON_LINES_SUFFIXES = frozenset({".ndjson", ".jsonl"})
TEXT_ONLY_SUFFIXES = JSON_SUFFIXES | JSON_LINES_SUFFIXES | {".xml"}

_SSN = re.compile(r"(?<![\d-])\d{3}-\d{2}-\d{4}(?![\d-])")
_SSN_SHAPED_VALUE = re.compile(r"\d{3}[- ]?\d{2}[- ]?\d{4}")
_FHIR_XML = re.compile(r"""["']http://hl7\.org/fhir["']|<Patient[\s/>]""")


def _objects(value: Any) -> list[dict[str, Any]]:
    """The objects in a JSON value that holds one object or a list of them."""
    items = value if isinstance(value, list) else [value]
    return [item for item in items if isinstance(item, dict)]


def _is_resource(node: Any) -> bool:
    return isinstance(node, dict) and isinstance(node.get("resourceType"), str)


def _resources(node: Any) -> Iterator[dict[str, Any]]:
    """Every FHIR resource at any depth of a JSON value."""
    if _is_resource(node):
        yield node
    children: Iterable[Any] = (
        node.values() if isinstance(node, dict) else node if isinstance(node, list) else ()
    )
    for child in children:
        yield from _resources(child)


def _own_values(node: Any, key: str) -> Iterator[Any]:
    """Values under ``key`` at any depth of one resource, not inside resources nested in it."""
    if isinstance(node, dict) and key in node:
        yield node[key]
    children: Iterable[Any] = (
        node.values() if isinstance(node, dict) else node if isinstance(node, list) else ()
    )
    for child in children:
        if not _is_resource(child):
            yield from _own_values(child, key)


def _resource_problems(resource: dict[str, Any]) -> list[str]:
    kind = resource["resourceType"]
    if kind in DEFINITIONAL_RESOURCE_TYPES:
        return []
    label = f"{kind} {resource.get('id', '<no id>')}"
    problems: list[str] = []
    meta = resource.get("meta")
    tags = {
        (tag.get("system"), tag.get("code"))
        for tag in _objects(meta.get("tag") if isinstance(meta, dict) else None)
    }
    needs_tag = kind in PERSON_RESOURCE_TYPES or "name" in resource or "identifier" in resource
    if needs_tag and TEST_DATA_TAG not in tags:
        problems.append(f"{label}: missing the HTEST test-data tag")
    for value in _own_values(resource, "identifier"):
        for identifier in _objects(value):
            if identifier.get("system") != SYNTHETIC_IDENTIFIER_SYSTEM:
                problems.append(f"{label}: identifier system is not {SYNTHETIC_IDENTIFIER_SYSTEM}")
            if _SSN_SHAPED_VALUE.fullmatch(str(identifier.get("value", "")).strip()):
                problems.append(f"{label}: identifier value is SSN-shaped")
    for value in _own_values(resource, "name"):
        for name in _objects(value):
            if name.get("family") != SYNTHETIC_FAMILY_NAME:
                problems.append(f"{label}: name family is not '{SYNTHETIC_FAMILY_NAME}'")
    return problems


def _json_lines(text: str) -> tuple[list[Any], list[int]]:
    """The documents of a JSON Lines text, and the numbers of the lines that do not parse."""
    documents: list[Any] = []
    bad_lines: list[int] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            documents.append(json.loads(line))
        except json.JSONDecodeError:
            bad_lines.append(number)
    return documents, bad_lines


def _json_documents(path: Path, text: str) -> tuple[list[Any], list[str]]:
    """The JSON documents in a file, and the problems that stopped the guard reading it."""
    if path.suffix in JSON_LINES_SUFFIXES:
        documents, bad_lines = _json_lines(text)
        return documents, [
            f"line {number} is not valid JSON; the guard cannot inspect it" for number in bad_lines
        ]
    if path.suffix not in JSON_SUFFIXES and text.lstrip()[:1] not in {"{", "["}:
        return [], []
    try:
        return [json.loads(text)], []
    except json.JSONDecodeError as error:
        if path.suffix in JSON_SUFFIXES:
            return [], [f"is not valid JSON (line {error.lineno}); the guard cannot inspect it"]
        return _json_lines(text)[0], []


def _is_fhir_xml(path: Path, text: str) -> bool:
    looks_like_xml = path.suffix == ".xml" or text.lstrip().startswith("<")
    return looks_like_xml and _FHIR_XML.search(text) is not None


def check_file(path: Path) -> list[str]:
    """Problems found in one file; empty if clean."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        if path.suffix in TEXT_ONLY_SUFFIXES:
            return ["is not UTF-8 text; the guard cannot inspect it"]
        return []
    except OSError:
        return ["cannot be read; the guard cannot inspect it"]
    problems: list[str] = []
    if _SSN.search(text):
        problems.append("contains an SSN-shaped number")
    if _is_fhir_xml(path, text):
        problems.append("contains FHIR XML, which the guard cannot inspect; store it as JSON")
    documents, reading_problems = _json_documents(path, text)
    problems.extend(reading_problems)
    for document in documents:
        for resource in _resources(document):
            problems.extend(_resource_problems(resource))
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
