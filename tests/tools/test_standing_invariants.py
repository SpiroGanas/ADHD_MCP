"""Standing invariant 1 across the whole tool surface: no output or description implies a
diagnosis. Extend NO_ARGUMENT_CALLS / patient calls as tools are added; never remove."""

import pytest
from fastmcp import Client

from tests.helpers.wording import assert_no_diagnostic_language

pytestmark = pytest.mark.anyio

NO_ARGUMENT_TOOLS = ["get_server_info"]


async def test_tool_descriptions_and_schemas_contain_no_diagnostic_language(
    mcp_client: Client,  # type: ignore[type-arg]
) -> None:
    for tool in await mcp_client.list_tools():
        assert_no_diagnostic_language(tool.model_dump(mode="json", by_alias=True))


@pytest.mark.parametrize("tool_name", NO_ARGUMENT_TOOLS)
async def test_tool_output_contains_no_diagnostic_language(
    mcp_client: Client,  # type: ignore[type-arg]
    tool_name: str,
) -> None:
    result = await mcp_client.call_tool(tool_name, {})
    assert_no_diagnostic_language(result.structured_content)
    assert_no_diagnostic_language([getattr(c, "text", "") for c in result.content])
