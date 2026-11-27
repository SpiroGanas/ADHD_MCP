import pytest
from fastmcp import Client

pytestmark = pytest.mark.anyio


async def test_timeline_with_unapplied_cutoffs(persona_client: Client) -> None:  # type: ignore[type-arg]
    result = await persona_client.call_tool("get_screening_history", {"patient_id": "p02-patient"})
    out = result.structured_content
    assert out is not None
    assert [(e["instrument"], e["measure"], e["score"]) for e in out["entries"]] == [
        ("auditc", "total_score", 3),
        ("phq9", "item", 0),
        ("phq9", "total_score", 13),
    ]
    assert out["entries"][0]["cutoff"]["status"] == "not_applied_unverified"
    assert out["entries"][0]["code_verified"] is False
