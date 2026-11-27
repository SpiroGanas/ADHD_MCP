"""Per-site mapping of local codes to the concepts the tools use.

Some things the tools look for have no standard code: which encounters are psychiatric
inpatient or residential stays, which Flags are high-risk-for-suicide flags, which
ServiceRequests are ADHD evaluation referrals, and which questionnaires are which screening
instruments. Each site states these in a data file under ``data/site_codes/``. Only the
project's own synthetic site is shipped; a real site supplies its own file (Phase 8).

A concept a site does not map matches nothing, and tools report the dependent check as not
performed. In strict mode a file with any unverified entry is refused (standing invariant 6).
"""

import tomllib
from collections.abc import Mapping
from importlib.resources import files
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from adhd_mcp.fhir.codes import Coding
from adhd_mcp.terminology.value_sets import UnverifiedContentError, ValueSetEntry

#: Concept name -> what it identifies. A site may map any subset.
SITE_CONCEPTS: Mapping[str, str] = {
    "psychiatric_inpatient_encounter": "Encounter type or service type of a psychiatric "
    "inpatient stay",
    "psychiatric_residential_encounter": "Encounter type or service type of a psychiatric "
    "or substance use residential stay",
    "high_risk_flag": "Flag code of a high-risk-for-suicide flag",
    "adhd_evaluation_request": "ServiceRequest code of a referral for ADHD evaluation",
    "adhd_evaluation_procedure": "Procedure code of an ADHD evaluation",
    "adhd_care_plan": "CarePlan category of an ADHD care plan",
}


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SiteConcept(_Frozen):
    title: str
    entries: tuple[ValueSetEntry, ...] = ()

    def matches(self, codings: tuple[Coding, ...]) -> bool:
        return any(e.matches(c) for e in self.entries for c in codings)


class QuestionnaireMapping(_Frozen):
    """Where a screening instrument's answers are in a site's questionnaire."""

    url: str = Field(description="Canonical URL of the Questionnaire, without version")
    instrument: str = Field(description="Instrument id in data/instruments/")
    total: str | None = Field(default=None, description="linkId of the total score item")
    items: dict[str, str] = Field(
        default_factory=dict, description="Instrument item number -> linkId"
    )
    verified: bool
    source: str | None = None
    note: str | None = None


class SiteCodes(_Frozen):
    id: str
    version: str
    title: str
    description: str | None = None
    concepts: dict[str, SiteConcept] = Field(default_factory=dict)
    questionnaires: tuple[QuestionnaireMapping, ...] = ()

    @model_validator(mode="after")
    def _known_concepts(self) -> Self:
        unknown = sorted(set(self.concepts) - set(SITE_CONCEPTS))
        if unknown:
            raise ValueError(f"unknown site concepts: {', '.join(unknown)}")
        return self

    def maps(self, concept: str) -> bool:
        return bool(self.concepts.get(concept, SiteConcept(title="")).entries)

    def matches(self, concept: str, codings: tuple[Coding, ...]) -> bool:
        mapped = self.concepts.get(concept)
        return mapped is not None and mapped.matches(codings)

    def questionnaire(self, url: str | None) -> QuestionnaireMapping | None:
        canonical = (url or "").partition("|")[0]
        return next((q for q in self.questionnaires if q.url == canonical), None)

    def unverified(self) -> list[str]:
        return [
            f"{name}:{e.code}"
            for name, concept in self.concepts.items()
            for e in concept.entries
            if not e.verified
        ] + [q.url for q in self.questionnaires if not q.verified]


def _parse(text: str, *, name: str, strict: bool) -> SiteCodes:
    site = SiteCodes.model_validate(tomllib.loads(text))
    if site.id != name:
        raise ValueError(f"file name {name!r} does not match site id {site.id!r}")
    if strict and (unverified := site.unverified()):
        raise UnverifiedContentError(
            f"site codes {site.id} have unverified entries: {', '.join(unverified)}"
        )
    return site


def load_site_codes_file(path: Path, *, strict: bool) -> SiteCodes:
    return _parse(path.read_text(encoding="utf-8"), name=path.stem, strict=strict)


def load_site_codes(site_id: str, *, strict: bool = True) -> SiteCodes:
    resource = files("adhd_mcp.data.site_codes").joinpath(f"{site_id}.toml")
    if not resource.is_file():
        raise LookupError(f"no packaged site codes {site_id!r}")
    return _parse(resource.read_text("utf-8"), name=site_id, strict=strict)
