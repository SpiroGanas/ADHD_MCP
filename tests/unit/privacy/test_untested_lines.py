"""Peer review 01, T8: lines a mutation probe could change without any test noticing."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest
from fastmcp import Client

from adhd_mcp.clock import FixedClock
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.privacy import load_privacy_policy
from adhd_mcp.privacy.policy import Action, with_actions
from adhd_mcp.server import create_server
from adhd_mcp.terminology.site_codes import load_site_codes
from adhd_mcp.tools.context import ToolContext
from tests.personas.builder import PersonaBuilder

pytestmark = pytest.mark.anyio

CLOCK = FixedClock(datetime(2026, 6, 15, 12, 0, tzinfo=UTC))
ACT = "http://terminology.hl7.org/CodeSystem/v3-ActCode"
POLICY = load_privacy_policy()


async def call(p: PersonaBuilder, tool: str, action: Action) -> dict[str, Any]:
    context = ToolContext(
        port=FixtureFhirAdapter(p.resources),
        clock=CLOCK,
        site_codes=load_site_codes("synthetic"),
        privacy=with_actions(POLICY, {"substance_use": action}),
    )
    async with Client(create_server(context)) as client:
        result = await client.call_tool(tool, {"patient_id": p.patient_id})
    assert result.structured_content is not None
    return cast(dict[str, Any], result.structured_content)


def person() -> PersonaBuilder:
    return PersonaBuilder("t84", gender="male", birth_date="1980-01-01")


async def test_a_reason_code_alone_puts_a_resource_in_a_protected_category() -> None:
    # privacy/policy.py: reason codes were added to classification without any test.
    p = person()
    p.encounter("EMER", "2026-02-01T10:00:00Z", reasons=(("F10.20", "Alcohol dependence"),))
    out = await call(p, "get_utilization_summary", "withhold")
    assert out["privacy"]["withheld"] == [{"category": "substance_use", "records": 1}]
    assert all(e["kind"] != "acute_care_visit" for e in out["events"])


async def test_a_medication_ingredient_on_a_restricted_record_is_redacted() -> None:
    p = person()
    request = p.medication_request("36437", "sertraline", "2026-03-01")
    dispense = p.medication_dispense(request, "36437", "sertraline", "2026-03-02")
    next(r for r in p.resources if r["id"] == dispense)["meta"] = {
        "security": [{"system": ACT, "code": "ETH"}]
    }
    out = await call(p, "get_medication_timeline", "cite")
    (exposure,) = out["exposures"]
    assert exposure["ingredient"] == {"rxcui": "restricted", "name": "restricted"}


async def test_a_coded_screening_answer_on_a_restricted_record_is_redacted() -> None:
    p = person()
    oid = p.observation(
        "93374-7", "Suicide risk level", "2026-05-20T09:45:00Z", value_code=("LA9194-7", "Low")
    )
    next(r for r in p.resources if r["id"] == oid)["meta"] = {
        "security": [{"system": ACT, "code": "SUD"}]
    }
    out = await call(p, "get_screening_history", "cite")
    (entry,) = out["entries"]
    assert entry["answer"] == {"system": None, "code": "restricted", "display": None}


def test_a_resource_normalization_cannot_read_is_classified_by_its_labels() -> None:
    raw = {
        "resourceType": ["not", "a", "type"],
        "id": "x",
        "meta": {"security": [{"system": ACT, "code": "SUD"}]},
    }
    assert POLICY.classify(raw) == {"substance_use"}


def test_a_site_policy_file_is_loaded(tmp_path: Path) -> None:
    text = (Path("src/adhd_mcp/data/privacy.toml").read_text(encoding="utf-8")).replace(
        'substance_use = "cite"', 'substance_use = "withhold"'
    )
    path = tmp_path / "site_privacy.toml"
    path.write_text(text, encoding="utf-8")
    assert load_privacy_policy(path).action("substance_use") == "withhold"
