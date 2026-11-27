"""Load clinician-facing wording from data."""

import tomllib
from functools import cache
from importlib.resources import files

from pydantic import BaseModel, ConfigDict


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ForbiddenPattern(_Frozen):
    id: str
    pattern: str


class DiagnosticLanguage(_Frozen):
    """Phrasings that state or imply a diagnosis; ``{condition}`` is a placeholder."""

    conditions: list[str]
    patterns: list[ForbiddenPattern]


class Wording(_Frozen):
    """Approved clinician-facing text, loaded from ``data/wording.toml``."""

    version: str
    standard_notice: str
    approved_recommendation: str
    diagnostic_language: DiagnosticLanguage


@cache
def load_wording() -> Wording:
    raw = files("adhd_mcp.data").joinpath("wording.toml").read_text(encoding="utf-8")
    return Wording.model_validate(tomllib.loads(raw))
