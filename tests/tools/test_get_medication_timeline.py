from typing import Any

import pytest
from fastmcp import Client

pytestmark = pytest.mark.anyio


async def output(client: Client, patient_id: str) -> dict[str, Any]:  # type: ignore[type-arg]
    result = await client.call_tool("get_medication_timeline", {"patient_id": patient_id})
    assert result.structured_content is not None
    return result.structured_content


async def test_p02_reports_five_distinct_antidepressants(persona_client: Client) -> None:  # type: ignore[type-arg]
    out = await output(persona_client, "p02-patient")
    counts = {d["drug_class"]: d["count"] for d in out["distinct_agents"]}
    assert counts == {
        "med.adhd_stimulant": 0,
        "med.adhd_nonstimulant": 0,
        "med.antidepressant": 5,
        "med.sedative_hypnotic": 0,
    }
    assert out["is_diagnosis"] is False


async def test_p06_stimulant_is_marked_for_narcolepsy(persona_client: Client) -> None:  # type: ignore[type-arg]
    out = await output(persona_client, "p06-patient")
    assert out["exposures"]
    assert all(e["for_narcolepsy"] for e in out["exposures"])


async def test_output_carries_no_record_display_text(persona_client: Client) -> None:  # type: ignore[type-arg]
    out = await output(persona_client, "p02-patient")
    # Persona displays are lowercase ingredient names; names in output come from class data.
    names = {e["ingredient"]["name"] for e in out["exposures"]}
    assert names == {"sertraline", "escitalopram", "bupropion", "venlafaxine", "fluoxetine"}
    assert "display" not in str(out)
