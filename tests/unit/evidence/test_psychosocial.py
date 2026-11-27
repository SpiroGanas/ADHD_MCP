"""Psychosocial context: Z-code domains, social-history observations and military context."""

from datetime import date
from typing import Any

import pytest

from adhd_mcp.evidence.psychosocial import (
    PsychosocialResult,
    assemble_psychosocial,
    load_psychosocial_content,
)
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.terminology.site_codes import SiteCodes, load_site_codes
from adhd_mcp.tools.context import NO_SITE_CODES
from tests.helpers.failing_adapter import FailingAdapter
from tests.personas import all_resources
from tests.personas.builder import ICD10CM, SYNTHETIC_LOCAL, PersonaBuilder

pytestmark = pytest.mark.anyio

AS_OF = date(2026, 6, 15)


def person() -> PersonaBuilder:
    return PersonaBuilder("t50", gender="male", birth_date="1990-01-01")


async def context(
    p: PersonaBuilder | None = None,
    *,
    patient_id: str | None = None,
    adapter: Any = None,
    site: SiteCodes | None = None,
) -> PsychosocialResult:
    port = adapter or FixtureFhirAdapter(p.resources if p else all_resources())
    content = load_psychosocial_content(site or load_site_codes("synthetic"))
    pid = patient_id or (p.patient_id if p else "")
    return await assemble_psychosocial(PatientRecords(port), pid, AS_OF, content)


def domain(result: PsychosocialResult, name: str) -> Any:
    return next(d for d in result.domains if d.domain == name)


def separation(p: PersonaBuilder, value: str | None) -> None:
    resource: dict[str, Any] = {
        "resourceType": "Observation",
        "id": f"t50-sep-{len(p.resources)}",
        "status": "final",
        "category": [{"coding": [{"code": "social-history"}]}],
        "code": {"coding": [{"system": SYNTHETIC_LOCAL, "code": "military-separation-date"}]},
        "subject": {"reference": f"Patient/{p.patient_id}"},
        "effectiveDateTime": "2025-01-01",
    }
    if value is not None:
        resource["valueDateTime"] = value
    p.resources.append(resource)


async def test_z_codes_are_grouped_into_domains() -> None:
    p = person()
    p.condition("Z59.01", "x", recorded="2025-01-01")
    p.condition("Z65.1", "x", recorded="2024-01-01")
    p.condition("Z56.0", "x", recorded="2025-05-01")
    p.condition("Z56.0", "x", recorded="2026-01-01")
    result = await context(p)
    assert [d.status for d in result.domains] == ["found", "found", "found"]
    (occupation,) = domain(result, "education_occupation").families
    (entry,) = occupation.entries
    assert entry.code.code == "Z56.0"
    assert len(entry.references) == 2


async def test_victim_of_crime_is_not_a_legal_problem() -> None:
    p = person()
    p.condition("Z65.4", "x", recorded="2025-01-01")
    assert domain(await context(p), "legal").status == "not_found"


async def test_inadequate_housing_is_not_counted() -> None:
    p = person()
    p.condition("Z59.10", "x", recorded="2025-01-01")
    assert domain(await context(p), "housing").status == "not_found"


async def test_social_history_observation_with_a_coded_value_counts() -> None:
    p = person()
    p.resources.append(
        {
            "resourceType": "Observation",
            "id": "t50-sdoh-1",
            "status": "final",
            "category": [{"coding": [{"code": "social-history"}]}],
            "code": {"coding": [{"system": SYNTHETIC_LOCAL, "code": "housing-status"}]},
            "subject": {"reference": f"Patient/{p.patient_id}"},
            "effectiveDateTime": "2026-01-01",
            "valueCodeableConcept": {"coding": [{"system": ICD10CM, "code": "Z59.811"}]},
        }
    )
    housing = domain(await context(p), "housing")
    assert housing.status == "found"
    assert [r.id for r in housing.observation_references] == ["t50-sdoh-1"]


async def test_missing_separation_date_is_unknown_not_defaulted() -> None:
    result = await context(person())
    assert result.military.status == "unknown"
    assert result.military.separation_date is None
    assert result.military.reason == "not recorded"


async def test_separation_observation_without_a_value_is_unknown() -> None:
    p = person()
    separation(p, None)
    result = await context(p)
    assert result.military.status == "unknown"
    assert result.military.separation_date is None


async def test_recorded_separation_date_is_reported_with_its_reference() -> None:
    p = person()
    separation(p, "2025-11-30")
    result = await context(p)
    assert result.military.status == "recorded"
    assert result.military.separation_date == date(2025, 11, 30)
    assert len(result.military.references) == 1


async def test_without_a_site_mapping_the_separation_date_is_unknown_and_says_why() -> None:
    p = person()
    separation(p, "2025-11-30")
    result = await context(p, site=NO_SITE_CODES)
    assert result.military.status == "unknown"
    assert result.military.reason == "not mapped at this site"


async def test_a_failed_condition_read_makes_domains_unknown() -> None:
    p = person()
    result = await context(adapter=FailingAdapter(p, {"Condition"}), patient_id=p.patient_id)
    assert {d.status for d in result.domains} == {"unknown"}


async def test_conditions_after_the_as_of_date_are_ignored() -> None:
    p = person()
    p.condition("Z65.1", "x", recorded="2026-07-01")
    assert domain(await context(p), "legal").status == "not_found"


async def test_persona_p01_has_an_occupation_problem() -> None:
    result = await context(patient_id="p01-patient")
    assert domain(result, "education_occupation").status == "found"
    assert domain(result, "housing").status == "not_found"
