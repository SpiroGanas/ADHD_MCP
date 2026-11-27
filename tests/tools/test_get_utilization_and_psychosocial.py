from typing import Any

import pytest
from fastmcp import Client

pytestmark = pytest.mark.anyio


async def call(client: Client, tool: str, patient_id: str) -> dict[str, Any]:  # type: ignore[type-arg]
    result = await client.call_tool(tool, {"patient_id": patient_id})
    assert result.structured_content is not None
    return result.structured_content


async def test_p01_utilization_counts(persona_client: Client) -> None:  # type: ignore[type-arg]
    out = await call(persona_client, "get_utilization_summary", "p01-patient")
    counts = {c["measure"]: c["total_730"] for c in out["counts"]}
    assert counts["injury_visit"] == 3
    assert counts["crash_as_driver"] == 1
    assert out["missed_appointments"] == "not_read"
    assert out["is_diagnosis"] is False


async def test_p01_psychosocial_occupation(persona_client: Client) -> None:  # type: ignore[type-arg]
    out = await call(persona_client, "get_psychosocial_context", "p01-patient")
    statuses = {d["domain"]: d["status"] for d in out["domains"]}
    assert statuses == {
        "housing": "not_found",
        "legal": "not_found",
        "education_occupation": "found",
    }
    assert out["military"]["status"] == "unknown"
