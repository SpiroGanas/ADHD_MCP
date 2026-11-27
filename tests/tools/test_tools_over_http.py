"""The patient tools give the same answers through the HTTP adapter (against the in-process
fake FHIR server, with small pages) as through the fixture adapter."""

from collections.abc import AsyncIterator

import pytest
from fastmcp import Client

from adhd_mcp.clock import FixedClock
from adhd_mcp.fhir.http_adapter import HttpFhirAdapter
from adhd_mcp.server import create_server
from adhd_mcp.terminology.site_codes import load_site_codes
from adhd_mcp.tools.context import ToolContext
from tests.helpers.fake_fhir_server import BASE, FakeFhirServer
from tests.personas import all_resources, persona_ids
from tests.tools.test_shared_tool_behavior import PATIENT_TOOLS

pytestmark = pytest.mark.anyio


@pytest.fixture
async def http_client(fixed_clock: FixedClock) -> AsyncIterator[Client]:  # type: ignore[type-arg]
    server = FakeFhirServer(list(reversed(all_resources())), page_size=2)
    async with HttpFhirAdapter(BASE, transport=server.transport(), page_size=2) as adapter:
        context = ToolContext(
            port=adapter, clock=fixed_clock, site_codes=load_site_codes("synthetic")
        )
        async with Client(create_server(context)) as client:
            yield client


@pytest.mark.parametrize("tool", PATIENT_TOOLS)
@pytest.mark.parametrize("persona_id", persona_ids())
async def test_http_answers_match_the_fixture_answers(
    http_client: Client,  # type: ignore[type-arg]
    persona_client: Client,  # type: ignore[type-arg]
    tool: str,
    persona_id: str,
) -> None:
    args = {"patient_id": f"{persona_id}-patient"}
    over_http = await http_client.call_tool(tool, args)
    direct = await persona_client.call_tool(tool, args)
    assert over_http.structured_content == direct.structured_content
