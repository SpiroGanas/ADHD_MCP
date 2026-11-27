"""What a FHIR server offers, so one HTTP adapter can serve several back ends (ADR 0004).

The ``generic`` profile is a full FHIR R4 server: every searchable type, the date search
parameters in ``fhir/search.py`` and ``_include`` of medications. Other profiles are data in
``data/fhir_servers/`` (``lighthouse``).
"""

import tomllib
from functools import cache
from importlib.resources import files

from pydantic import BaseModel, ConfigDict, Field, field_validator

from adhd_mcp.fhir.port import SEARCHABLE_TYPES
from adhd_mcp.fhir.search import DATE_SEARCH


class ServerProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    title: str
    source: str
    offered: frozenset[str] = frozenset(SEARCHABLE_TYPES)
    no_date_search: frozenset[str] = frozenset()
    include_medications: bool = True
    max_page_size: int = Field(default=1000, ge=1)

    @field_validator("offered", "no_date_search")
    @classmethod
    def _known(cls, value: frozenset[str]) -> frozenset[str]:
        unknown = value - set(SEARCHABLE_TYPES)
        if unknown:
            raise ValueError(f"unknown search types: {', '.join(sorted(unknown))}")
        return value

    @field_validator("offered")
    @classmethod
    def _essential(cls, value: frozenset[str]) -> frozenset[str]:
        # The safety gate's coded checks and every condition signal need these.
        if not {"Condition", "Encounter"} <= value:
            raise ValueError("a server profile must offer Condition and Encounter")
        return value

    def date_param(self, resource_type: str) -> str | None:
        """The server's date search parameter, or ``None`` when it has none."""
        if resource_type in self.no_date_search:
            return None
        return DATE_SEARCH[resource_type][0]


GENERIC = ServerProfile(id="generic", title="FHIR R4 server", source="FHIR R4 specification")


@cache
def load_server_profile(profile_id: str) -> ServerProfile:
    if profile_id == "generic":
        return GENERIC
    try:
        raw = files("adhd_mcp.data.fhir_servers").joinpath(f"{profile_id}.toml")
        text = raw.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise LookupError(f"no FHIR server profile {profile_id!r}") from None
    return ServerProfile.model_validate(tomllib.loads(text))


def profile_ids() -> list[str]:
    names = files("adhd_mcp.data.fhir_servers").iterdir()
    return sorted(["generic", *(p.name[:-5] for p in names if p.name.endswith(".toml"))])
