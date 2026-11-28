"""One code representation across coding systems and their aliases."""

import re
import tomllib
from collections.abc import Mapping
from functools import cache
from importlib.resources import files
from typing import Any

from pydantic import BaseModel, ConfigDict

ICD10CM = "http://hl7.org/fhir/sid/icd-10-cm"
SNOMED = "http://snomed.info/sct"
LOINC = "http://loinc.org"
RXNORM = "http://www.nlm.nih.gov/research/umls/rxnorm"

#: An ICD-10-CM code sent without its dot: a category (letter, digit, character) followed
#: by one to four more characters. The dot goes after the category.
_UNDOTTED_ICD10CM = re.compile(r"[A-Z][0-9][0-9A-Z][0-9A-Z]{1,4}")


class Coding(BaseModel):
    """A normalized coding. Free text (``CodeableConcept.text``) is never kept."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    system: str | None
    code: str
    display: str | None = None


class _CodeSystem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    uri: str
    name: str
    uppercase_codes: bool
    aliases: list[str]


@cache
def _systems() -> dict[str, _CodeSystem]:
    raw = files("adhd_mcp.data.terminology").joinpath("code_systems.toml").read_text("utf-8")
    systems = [_CodeSystem.model_validate(s) for s in tomllib.loads(raw)["systems"]]
    return {key: s for s in systems for key in (s.uri, *s.aliases)}


def canonical_system(system: str | None) -> str | None:
    if system is None:
        return None
    known = _systems().get(system)
    return known.uri if known else system


def normalize_coding(raw: Mapping[str, Any]) -> Coding | None:
    """Normalize one FHIR Coding; ``None`` if it carries no code."""
    code = (raw.get("code") or "").strip()
    if not code:
        return None
    known = _systems().get(raw.get("system") or "")
    if known is not None and known.uppercase_codes:
        code = code.upper()
    if known is not None and known.uri == ICD10CM and _UNDOTTED_ICD10CM.fullmatch(code):
        code = f"{code[:3]}.{code[3:]}"
    return Coding(
        system=known.uri if known else raw.get("system"),
        code=code,
        display=raw.get("display"),
    )


def normalize_concept(raw: Mapping[str, Any] | None) -> tuple[Coding, ...]:
    """All usable codings of a CodeableConcept, in order."""
    if not raw:
        return ()
    codings = (normalize_coding(c) for c in raw.get("coding") or [])
    return tuple(c for c in codings if c is not None)
