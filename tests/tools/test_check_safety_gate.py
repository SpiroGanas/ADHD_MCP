from typing import Any

import pytest
from fastmcp import Client

from adhd_mcp.wording import load_wording

pytestmark = pytest.mark.anyio


async def gate_output(client: Client, args: dict[str, Any]) -> dict[str, Any]:  # type: ignore[type-arg]
    result = await client.call_tool("check_safety_gate", args)
    assert result.structured_content is not None
    return result.structured_content


async def test_positive_gate_with_guidance_and_evidence(persona_client: Client) -> None:  # type: ignore[type-arg]
    gate = (await gate_output(persona_client, {"patient_id": "p03-patient"}))["safety_gate"]
    assert gate["status"] == "positive"
    assert gate["guidance"] == load_wording().safety_gate_guidance
    assert gate["evidence"][0]["signal"] == "psychiatric_discharge_within_90_days"
    assert gate["evidence"][0]["references"] == [
        {"resource_type": "Encounter", "id": "p03-enc-1", "version": None}
    ]


async def test_unverified_checks_are_listed_as_not_performed(persona_client: Client) -> None:  # type: ignore[type-arg]
    gate = (await gate_output(persona_client, {"patient_id": "p01-patient"}))["safety_gate"]
    assert gate["status"] == "clear_limited_data"
    not_performed = {c["id"] for c in gate["checks"] if c["outcome"] == "not_performed"}
    assert not_performed == {"phq9_item9", "cssrs_risk_level"}
    assert gate["guidance"] is None


async def test_as_of_date_moves_the_look_back(persona_client: Client) -> None:  # type: ignore[type-arg]
    args = {"patient_id": "p03-patient", "as_of": "2025-06-01"}
    gate = (await gate_output(persona_client, args))["safety_gate"]
    assert gate["status"] == "clear_limited_data"
    assert gate["evidence"] == []


async def test_reports_the_definition_version(persona_client: Client) -> None:  # type: ignore[type-arg]
    out = await gate_output(persona_client, {"patient_id": "p01-patient"})
    assert out["gate_definition_version"] == "0.1.0"
