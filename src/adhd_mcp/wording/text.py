"""Load clinician-facing wording from data."""

import tomllib
from functools import cache
from importlib.resources import files

from pydantic import BaseModel, ConfigDict


class Wording(BaseModel):
    """Approved clinician-facing text, loaded from ``data/wording.toml``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str
    standard_notice: str
    approved_recommendation: str


@cache
def load_wording() -> Wording:
    raw = files("adhd_mcp.data").joinpath("wording.toml").read_text(encoding="utf-8")
    return Wording.model_validate(tomllib.loads(raw))
