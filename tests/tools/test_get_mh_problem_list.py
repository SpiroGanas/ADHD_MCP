import pytest
from fastmcp import Client

pytestmark = pytest.mark.anyio


async def test_lists_families_with_references(persona_client: Client) -> None:  # type: ignore[type-arg]
    result = await persona_client.call_tool("get_mh_problem_list", {"patient_id": "p09-patient"})
    out = result.structured_content
    assert out is not None
    families = {f["family"]: f["entries"] for f in out["families"]}
    assert set(families) == {"mh.depression", "mh.ptsd"}
    assert [r["id"] for r in families["mh.ptsd"][0]["references"]] == ["p09-cond-1", "p09-cond-2"]
    assert families["mh.depression"][0]["resolved"] is True
