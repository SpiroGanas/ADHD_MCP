"""Signal catalogs: the documented, versioned list of a condition's referral signals.

A catalog is data. Loading it strictly checks every value set and drug class it names is
verified (standing invariant 6), so no signal can depend on an unverified code.
"""

import tomllib
from importlib.resources import files
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from adhd_mcp.terminology import load_value_set
from adhd_mcp.terminology.drug_classes import load_drug_class

Weight = Literal["high", "modifier", "note"]
Source = Literal["condition", "psychosocial", "events", "distinct_agents"]


class SignalDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    title: str
    weight: Weight
    source: Source
    tool: str
    window_days: int = Field(ge=1)
    value_sets: tuple[str, ...] = ()
    domain: str | None = None
    event: str | None = None
    drug_class: str | None = None
    min_count: int = Field(default=1, ge=1)
    protected: str | None = None
    evidence: str
    inference: bool

    @model_validator(mode="after")
    def _check(self) -> Self:
        needs = {
            "condition": bool(self.value_sets),
            "psychosocial": self.domain is not None,
            "events": self.event is not None,
            "distinct_agents": self.drug_class is not None,
        }
        if not needs[self.source]:
            raise ValueError(f"signal {self.id}: source {self.source} is missing its definition")
        return self


class SignalCatalog(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    version: str
    condition: str
    reviewed_by_owner: bool
    signals: tuple[SignalDefinition, ...]

    @model_validator(mode="after")
    def _unique(self) -> Self:
        ids = [s.id for s in self.signals]
        if len(ids) != len(set(ids)):
            raise ValueError("signal ids must be unique")
        return self


def parse_catalog(text: str, *, strict: bool = True) -> SignalCatalog:
    catalog = SignalCatalog.model_validate(tomllib.loads(text))
    if strict:
        for s in catalog.signals:
            for value_set in s.value_sets:
                load_value_set(value_set, strict=True)
            if s.drug_class is not None:
                load_drug_class(s.drug_class, strict=True)
    return catalog


def load_catalog(package: str, name: str = "signal_catalog.toml") -> SignalCatalog:
    """Load a packaged catalog strictly, e.g. ``load_catalog("adhd_mcp.data.adhd")``."""
    return parse_catalog(files(package).joinpath(name).read_text(encoding="utf-8"))
