import pytest
from fastmcp import Client

from adhd_mcp.rules.ruleset import load_ruleset
from adhd_mcp.wording import load_wording

pytestmark = pytest.mark.anyio


async def test_returns_versions_and_intended_use(mcp_client: Client) -> None:  # type: ignore[type-arg]
    result = await mcp_client.call_tool("get_server_info", {})

    assert result.is_error is False
    out = result.structured_content
    assert out is not None
    assert out["server_name"] == "adhd-mcp"
    assert out["server_version"] == "0.1.0"
    assert out["tool_contract_version"]
    # Phase 5: the active ruleset is reported and matches the loaded one (draft until approved).
    assert (
        out["ruleset_version"] == load_ruleset("adhd_mcp.data.adhd").label == "adhd 1.0.0 (draft)"
    )
    assert out["intended_use"] == load_wording().standard_notice
    assert "not a diagnosis" in out["intended_use"]


async def test_rejects_unexpected_arguments(mcp_client: Client) -> None:  # type: ignore[type-arg]
    result = await mcp_client.call_tool(
        "get_server_info", {"patient_id": "x"}, raise_on_error=False
    )
    assert result.is_error is True
