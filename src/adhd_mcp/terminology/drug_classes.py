"""Versioned RxNorm drug classes (ADR 0009).

A class lists ingredients (RxNorm TTY ``IN``). Each ingredient carries the product concepts
that contain it (``SCD``, ``SBD``, packs, forms, multi-ingredient and precise ingredients),
as expanded from RxNav by ``scripts/build_drug_classes.py``. A medication coding maps to
every class ingredient whose own code or product list contains it, so a combination
product counts once per class ingredient.

In strict mode a class with any unverified ingredient is refused (standing invariant 6).
"""

import datetime as dt
import tomllib
from functools import cached_property
from importlib.resources import files
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from adhd_mcp.fhir.codes import RXNORM, Coding
from adhd_mcp.terminology.value_sets import UnverifiedContentError


class DrugIngredient(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rxcui: str = Field(min_length=1)
    name: str = Field(min_length=1)
    verified: bool
    source: str | None = None
    source_version: str | None = None
    checked_on: dt.date | None = None
    checked_by: str | None = None
    products: tuple[str, ...]

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.verified and not (self.source and self.source_version and self.checked_on):
            raise ValueError("a verified ingredient needs source, source_version and checked_on")
        return self


class DrugClass(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    version: str
    title: str
    description: str | None = None
    ingredients: tuple[DrugIngredient, ...]

    @cached_property
    def _index(self) -> dict[str, tuple[DrugIngredient, ...]]:
        index: dict[str, list[DrugIngredient]] = {}
        for ingredient in self.ingredients:
            for code in (ingredient.rxcui, *ingredient.products):
                bucket = index.setdefault(code, [])
                if ingredient not in bucket:
                    bucket.append(ingredient)
        return {code: tuple(found) for code, found in index.items()}

    def ingredients_for(self, codings: tuple[Coding, ...]) -> tuple[DrugIngredient, ...]:
        """Class ingredients contained in any RxNorm coding, in class order."""
        found: set[str] = set()
        for coding in codings:
            if coding.system == RXNORM:
                found.update(i.rxcui for i in self._index.get(coding.code, ()))
        return tuple(i for i in self.ingredients if i.rxcui in found)

    def unverified_ingredients(self) -> tuple[DrugIngredient, ...]:
        return tuple(i for i in self.ingredients if not i.verified)


def parse_drug_class(text: str, *, name: str, strict: bool) -> DrugClass:
    drug_class = DrugClass.model_validate(tomllib.loads(text))
    if name != drug_class.id:
        raise ValueError(f"file name {name!r} does not match drug class id {drug_class.id!r}")
    if strict and (unverified := drug_class.unverified_ingredients()):
        names = ", ".join(i.name for i in unverified)
        raise UnverifiedContentError(f"drug class {drug_class.id} has unverified entries: {names}")
    return drug_class


def packaged_drug_class_ids() -> list[str]:
    root = files("adhd_mcp.data.drug_classes")
    return sorted(p.name.removesuffix(".toml") for p in root.iterdir() if p.name.endswith(".toml"))


def load_drug_class(class_id: str, *, strict: bool = True) -> DrugClass:
    """Load a packaged drug class by id. Strict by default."""
    resource = files("adhd_mcp.data.drug_classes").joinpath(f"{class_id}.toml")
    if not resource.is_file():
        raise LookupError(f"no packaged drug class {class_id!r}")
    return parse_drug_class(resource.read_text("utf-8"), name=class_id, strict=strict)
