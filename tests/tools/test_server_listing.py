import pytest
from fastmcp import Client

pytestmark = pytest.mark.anyio


async def test_server_lists_exactly_the_expected_tools(mcp_client: Client) -> None:  # type: ignore[type-arg]
    tools = await mcp_client.list_tools()
    assert sorted(t.name for t in tools) == [
        "check_safety_gate",
        "get_mh_problem_list",
        "get_screening_history",
        "get_server_info",
    ]
