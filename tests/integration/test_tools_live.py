"""Every Phase 3 tool, called through an MCP client, gives the same answer from the local
FHIR server as from the fixture bundles (apart from server-assigned version ids).

Run: docker compose up -d fhir && uv run pytest -m integration
"""

from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastmcp import Client

from adhd_mcp.clock import FixedClock
from adhd_mcp.fhir.http_adapter import HttpFhirAdapter
from adhd_mcp.server import create_server
from adhd_mcp.terminology.site_codes import load_site_codes
from adhd_mcp.tools.context import ToolContext
from tests.personas import persona_ids

pytestmark = [pytest.mark.integration, pytest.mark.anyio]

TOOLS = ["check_safety_gate", "get_mh_problem_list", "get_screening_history", "check_existing_care"]


@pytest.fixture
async def live_client(loaded_server: str, fixed_clock: FixedClock) -> AsyncIterator[Client]:  # type: ignore[type-arg]
    async with HttpFhirAdapter(loaded_server) as adapter:
        context = ToolContext(
            port=adapter, clock=fixed_clock, site_codes=load_site_codes("synthetic")
        )
        async with Client(create_server(context)) as client:
            yield client


def without_versions(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: without_versions(v)
            for k, v in value.items()
            if not (k == "version" and "resource_type" in value)
        }
    if isinstance(value, list):
        return [without_versions(v) for v in value]
    return value


@pytest.mark.parametrize("tool", TOOLS)
@pytest.mark.parametrize("persona_id", persona_ids())
async def test_live_answers_match_the_fixtures(
    live_client: Client,  # type: ignore[type-arg]
    persona_client: Client,  # type: ignore[type-arg]
    tool: str,
    persona_id: str,
) -> None:
    args = {"patient_id": f"{persona_id}-patient"}
    live = await live_client.call_tool(tool, args)
    fixture = await persona_client.call_tool(tool, args)
    assert without_versions(live.structured_content) == without_versions(fixture.structured_content)
