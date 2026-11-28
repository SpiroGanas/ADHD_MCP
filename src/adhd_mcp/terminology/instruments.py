"""Screening instrument definitions: codes and cutoffs, with verification status.

No copyrighted item text is stored. In strict mode an instrument with any unverified code
or cutoff is refused (standing invariant 6).
"""

import datetime as dt
import tomllib
from functools import cache
from importlib.resources import files
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from adhd_mcp.terminology.value_sets import UnverifiedContentError


class _Verifiable(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    verified: bool
    source: str | None = None
    source_version: str | None = None
    checked_on: dt.date | None = None
    checked_by: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _provenance(self) -> Self:
        if self.verified and not (self.source and self.source_version and self.checked_on):
            raise ValueError("verified content needs source, source_version and checked_on")
        return self


class InstrumentCode(_Verifiable):
    role: Literal["panel", "total_score", "item", "risk_level"]
    item: str | None = None
    system: str
    code: str = Field(min_length=1)
    display: str | None = None


class InstrumentAnswer(_Verifiable):
    """A coded answer to one of the instrument's codes, e.g. a C-SSRS risk level."""

    for_code: str = Field(description="The instrument code this answers")
    system: str
    code: str = Field(min_length=1)
    display: str | None = None
    positive: bool = Field(description="Whether this answer counts as a positive screen")


class Cutoff(_Verifiable):
    id: str
    code: str = Field(description="The instrument code the cutoff applies to")
    operator: Literal[">=", ">"]
    value: float
    sex: Literal["any", "male", "female"] = "any"

    def is_met(self, score: float) -> bool:
        return score >= self.value if self.operator == ">=" else score > self.value


class Instrument(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    version: str
    title: str
    licensing_note: str | None = None
    codes: tuple[InstrumentCode, ...] = ()
    cutoffs: tuple[Cutoff, ...] = ()
    answers: tuple[InstrumentAnswer, ...] = ()

    @model_validator(mode="after")
    def _cutoffs_reference_codes(self) -> Self:
        known = {c.code for c in self.codes}
        for cutoff in self.cutoffs:
            if known and cutoff.code not in known:
                raise ValueError(f"cutoff {cutoff.id}: {cutoff.code} is not a code of {self.id}")
        for answer in self.answers:
            if answer.for_code not in known:
                raise ValueError(
                    f"answer {answer.code}: {answer.for_code} is not a code of {self.id}"
                )
        return self

    def code_for(self, role: str, item: str | None = None) -> tuple[str, str]:
        for c in self.codes:
            if c.role == role and c.item == item:
                return c.system, c.code
        raise LookupError(f"{self.id} has no code with role {role!r} item {item!r}")

    def cutoff(self, cutoff_id: str, sex: str = "any") -> Cutoff:
        for c in self.cutoffs:
            if c.id == cutoff_id and c.sex == sex:
                return c
        raise LookupError(f"{self.id} has no cutoff {cutoff_id!r} for sex {sex!r}")

    def unverified(self) -> list[str]:
        return (
            [c.code for c in self.codes if not c.verified]
            + [c.id for c in self.cutoffs if not c.verified]
            + [a.code for a in self.answers if not a.verified]
        )


def _parse(text: str, *, name: str, strict: bool) -> Instrument:
    instrument = Instrument.model_validate(tomllib.loads(text))
    if instrument.id != name:
        raise ValueError(f"file name {name!r} does not match instrument id {instrument.id!r}")
    if strict and (unverified := instrument.unverified()):
        raise UnverifiedContentError(
            f"instrument {instrument.id} has unverified content: {', '.join(unverified)}"
        )
    return instrument


def load_instrument_file(path: Path, *, strict: bool) -> Instrument:
    return _parse(path.read_text(encoding="utf-8"), name=path.stem, strict=strict)


def packaged_instrument_ids() -> list[str]:
    root = files("adhd_mcp.data.instruments")
    return sorted(p.name.removesuffix(".toml") for p in root.iterdir() if p.name.endswith(".toml"))


@cache
def instrument_codes() -> tuple[tuple[str, str], ...]:
    """Every (system, code) any packaged instrument file lists, verified or not: what the
    gate and the screening history search Observations by (peer review 01, D1)."""
    return tuple(
        sorted(
            {
                (c.system, c.code)
                for i in packaged_instrument_ids()
                for c in load_instrument(i, strict=False).codes
            }
        )
    )


def load_instrument(instrument_id: str, *, strict: bool = True) -> Instrument:
    resource = files("adhd_mcp.data.instruments").joinpath(f"{instrument_id}.toml")
    if not resource.is_file():
        raise LookupError(f"no packaged instrument {instrument_id!r}")
    return _parse(resource.read_text("utf-8"), name=instrument_id, strict=strict)
