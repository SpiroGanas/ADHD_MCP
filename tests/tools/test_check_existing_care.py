from typing import Any

import pytest
from fastmcp import Client

from tests.personas import load_catalog

pytestmark = pytest.mark.anyio

EXPECTED = {p["id"]: p["existing_care"] for p in load_catalog()["personas"]}


async def output(client: Client, patient_id: str) -> dict[str, Any]:  # type: ignore[type-arg]
    result = await client.call_tool("check_existing_care", {"patient_id": patient_id})
    assert result.structured_content is not None
    return result.structured_content


@pytest.mark.parametrize("persona_id", sorted(EXPECTED))
async def test_matches_the_catalog(persona_client: Client, persona_id: str) -> None:  # type: ignore[type-arg]
    out = await output(persona_client, f"{persona_id}-patient")
    assert out["excluded"] is (EXPECTED[persona_id] == "excluded_adhd_diagnosis")


async def test_narcolepsy_is_reported_separately(persona_client: Client) -> None:  # type: ignore[type-arg]
    out = await output(persona_client, "p06-patient")
    assert out["excluded"] is False
    assert out["narcolepsy"]["medication_for_narcolepsy"] is True
