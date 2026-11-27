"""The persona catalog is the specification: every persona's gate matches its expectation,
both with today's strict content and with every check's content active."""

from datetime import date
from typing import Any

import pytest

from adhd_mcp.evidence.safety_gate import assess_safety_gate, load_gate_content
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.models.domain import CheckOutcome, SafetyGateResult
from adhd_mcp.terminology.site_codes import load_site_codes
from tests.personas import all_resources, load_catalog

pytestmark = pytest.mark.anyio

CATALOG = load_catalog()
AS_OF = date.fromisoformat(CATALOG["as_of"])
PERSONAS = CATALOG["personas"]


async def gate(persona_id: str, *, strict: bool) -> SafetyGateResult:
    records = PatientRecords(FixtureFhirAdapter(all_resources()))
    content = load_gate_content(load_site_codes("synthetic"), strict=strict)
    result, _ = await assess_safety_gate(records, f"{persona_id}-patient", AS_OF, content)
    return result


def found(result: SafetyGateResult) -> list[str]:
    return [c.id for c in result.checks if c.outcome is CheckOutcome.FOUND]


@pytest.mark.parametrize("persona", PERSONAS, ids=lambda p: p["id"])
async def test_gate_with_todays_content(persona: dict[str, Any]) -> None:
    result = await gate(persona["id"], strict=True)
    assert result.status == persona["safety_gate"]
    assert found(result) == persona.get("safety_gate_found", [])


@pytest.mark.parametrize("persona", PERSONAS, ids=lambda p: p["id"])
async def test_gate_with_every_check_active(persona: dict[str, Any]) -> None:
    result = await gate(persona["id"], strict=False)
    assert result.status == persona["safety_gate_all_checks_active"]
    assert found(result) == persona.get("safety_gate_found_all_checks_active", [])


async def test_p03_cites_its_resources_and_presents_the_discharge_first() -> None:
    result = await gate("p03", strict=True)
    assert [e.signal for e in result.evidence] == [
        "psychiatric_discharge_within_90_days",
        "suicidal_ideation_code",
        "high_risk_flag",
    ]
    cited = {r.id for e in result.evidence for r in e.references}
    assert cited == {"p03-enc-1", "p03-cond-1", "p03-flag-1"}
