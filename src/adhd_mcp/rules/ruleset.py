"""Rulesets: versioned combination rules over a signal catalog (ADR 0010).

Status ``experimental`` marks a stub that proves an interface (Phase 8): never released, and
the condition is registered only when a setting names it.

A rule fires when at least ``min_high`` distinct high-weight signals and ``min_modifiers``
distinct modifier signals are present. A ruleset recommends when any rule fires. A released
ruleset loads only if its file hash is pinned in ``data/released_rulesets.toml``.
"""

import datetime as dt
import hashlib
import tomllib
from collections.abc import Sequence
from importlib.resources import files
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Rule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    description: str
    min_high: int = Field(ge=0)
    min_modifiers: int = Field(ge=0)

    @model_validator(mode="after")
    def _can_fire_on_evidence(self) -> Self:
        if self.min_high + self.min_modifiers < 1:
            raise ValueError(f"rule {self.id} must require at least one signal")
        return self


class Ruleset(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    version: str
    status: Literal["draft", "released", "experimental"]
    effective_date: dt.date
    catalog: str
    catalog_version: str
    validated: Literal[False] = Field(
        description="Always false: no ruleset in this project is clinically validated"
    )
    exclusions: tuple[str, ...]
    citations: tuple[str, ...] = Field(min_length=1)
    rules: tuple[Rule, ...] = Field(min_length=1)

    @property
    def label(self) -> str:
        return f"{self.id} {self.version} ({self.status})"


class ReleasedRuleset(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    version: str
    sha256: str


def released_rulesets() -> tuple[ReleasedRuleset, ...]:
    raw = files("adhd_mcp.data").joinpath("released_rulesets.toml").read_text(encoding="utf-8")
    return tuple(ReleasedRuleset.model_validate(r) for r in tomllib.loads(raw)["released"])


def parse_ruleset(text: str, *, released: Sequence[ReleasedRuleset]) -> Ruleset:
    ruleset = Ruleset.model_validate(tomllib.loads(text))
    if ruleset.status == "released":
        pins = [r for r in released if (r.id, r.version) == (ruleset.id, ruleset.version)]
        if not pins:
            raise ValueError(f"ruleset {ruleset.label} is released but not pinned")
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != pins[0].sha256:
            raise ValueError(f"ruleset {ruleset.label} changed since release")
    return ruleset


def load_ruleset(package: str, name: str = "ruleset.toml") -> Ruleset:
    text = files(package).joinpath(name).read_text(encoding="utf-8")
    return parse_ruleset(text, released=released_rulesets())
