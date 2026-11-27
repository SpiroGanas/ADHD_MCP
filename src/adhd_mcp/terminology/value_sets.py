"""Versioned value sets loaded from data files, with ICD-10-CM family matching.

Matching kinds:

* ``exact``: the code equals the entry.
* ``prefix`` (ICD-10-CM only): the code is the entry or a descendant of it. A
  three-character category matches only at the dot boundary, so ``F15`` matches
  ``F15.10`` but not ``F150``.
* ``regex``: the code fully matches a Python regular expression (used where a family is
  defined by a character position, such as the intent character of poisoning codes).

In strict mode a value set with any unverified entry is refused (standing invariant 6).
"""

import datetime as dt
import re
import tomllib
from importlib.resources import files
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from adhd_mcp.fhir.codes import ICD10CM, Coding


class UnverifiedContentError(Exception):
    """Raised when strict loading meets clinical content not yet verified."""


class ValueSetEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    system: str
    match: Literal["exact", "prefix", "regex"]
    code: str = Field(min_length=1)
    display: str | None = None
    verified: bool
    source: str | None = None
    source_version: str | None = None
    checked_on: dt.date | None = None
    checked_by: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.match == "prefix" and self.system != ICD10CM:
            raise ValueError("prefix entries are only defined for ICD-10-CM")
        if self.match == "regex":
            try:
                re.compile(self.code)
            except re.error as exc:
                raise ValueError(f"invalid regex {self.code!r}: {exc}") from exc
        if self.verified and not (self.source and self.source_version and self.checked_on):
            raise ValueError("a verified entry needs source, source_version and checked_on")
        return self

    def matches(self, coding: Coding) -> bool:
        if coding.system != self.system:
            return False
        code = coding.code
        if self.match == "exact":
            return code == self.code
        if self.match == "regex":
            return re.fullmatch(self.code, code) is not None
        if code == self.code:
            return True
        boundary = self.code if "." in self.code else self.code + "."
        return code.startswith(boundary)


class ValueSet(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    version: str
    title: str
    description: str | None = None
    entries: tuple[ValueSetEntry, ...]

    def matches(self, coding: Coding) -> ValueSetEntry | None:
        """The first entry matching ``coding``, or ``None``."""
        return next((e for e in self.entries if e.matches(coding)), None)

    def matching_codings(self, codings: tuple[Coding, ...]) -> tuple[Coding, ...]:
        return tuple(c for c in codings if self.matches(c) is not None)

    def unverified_entries(self) -> tuple[ValueSetEntry, ...]:
        return tuple(e for e in self.entries if not e.verified)


def _check_strict(value_set: ValueSet) -> None:
    unverified = value_set.unverified_entries()
    if unverified:
        codes = ", ".join(e.code for e in unverified)
        raise UnverifiedContentError(f"value set {value_set.id} has unverified entries: {codes}")


def parse_value_set(text: str, *, name: str, strict: bool) -> ValueSet:
    value_set = ValueSet.model_validate(tomllib.loads(text))
    if name != value_set.id:
        raise ValueError(f"file name {name!r} does not match value set id {value_set.id!r}")
    if strict:
        _check_strict(value_set)
    return value_set


def load_value_set_file(path: Path, *, strict: bool) -> ValueSet:
    return parse_value_set(path.read_text(encoding="utf-8"), name=path.stem, strict=strict)


def packaged_value_set_ids() -> list[str]:
    root = files("adhd_mcp.data.value_sets")
    return sorted(p.name.removesuffix(".toml") for p in root.iterdir() if p.name.endswith(".toml"))


def load_value_set(value_set_id: str, *, strict: bool = True) -> ValueSet:
    """Load a packaged value set by id. Strict by default."""
    resource = files("adhd_mcp.data.value_sets").joinpath(f"{value_set_id}.toml")
    if not resource.is_file():
        raise LookupError(f"no packaged value set {value_set_id!r}")
    return parse_value_set(resource.read_text("utf-8"), name=value_set_id, strict=strict)
