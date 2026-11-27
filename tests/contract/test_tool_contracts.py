"""Contract snapshots: each tool's name, description and schemas are stored and reviewed.

A changed snapshot is a deliberate, reviewed act. Regenerate with
``UPDATE_SNAPSHOTS=1 uv run pytest tests/contract`` and explain the change in the PR.
"""

import pytest
from fastmcp import Client

from tests.contract.snapshots import (
    SNAPSHOT_ROOT,
    TOOL_SNAPSHOT_DIR,
    assert_matches_snapshot,
    tool_contract,
)

pytestmark = pytest.mark.anyio


async def test_tool_list_matches_snapshots(mcp_client: Client) -> None:  # type: ignore[type-arg]
    tools = await mcp_client.list_tools()
    stored = sorted(p.stem for p in TOOL_SNAPSHOT_DIR.glob("*.json"))
    assert sorted(t.name for t in tools) == stored


async def test_each_tool_matches_its_snapshot(mcp_client: Client) -> None:  # type: ignore[type-arg]
    for tool in await mcp_client.list_tools():
        assert_matches_snapshot(TOOL_SNAPSHOT_DIR / f"{tool.name}.json", tool_contract(tool))


async def test_every_tool_is_marked_read_only(mcp_client: Client) -> None:  # type: ignore[type-arg]
    for tool in await mcp_client.list_tools():
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is True, tool.name


async def test_prompts_match_their_snapshots(mcp_client: Client) -> None:  # type: ignore[type-arg]
    prompts = await mcp_client.list_prompts()
    assert sorted(p.name for p in prompts) == ["explain_recommendation", "summarize_checks"]
    for prompt in prompts:
        assert_matches_snapshot(
            SNAPSHOT_ROOT / "prompts" / f"{prompt.name}.json",
            prompt.model_dump(mode="json", by_alias=True, exclude_none=True),
        )


async def test_resources_match_their_snapshot(mcp_client: Client) -> None:  # type: ignore[type-arg]
    listed = [
        r.model_dump(mode="json", by_alias=True, exclude_none=True)
        for r in await mcp_client.list_resources()
    ]
    templates = [
        t.model_dump(mode="json", by_alias=True, exclude_none=True)
        for t in await mcp_client.list_resource_templates()
    ]
    assert_matches_snapshot(
        SNAPSHOT_ROOT / "resources.json",
        {"resources": sorted(listed, key=lambda r: r["uri"]), "templates": templates},
    )
