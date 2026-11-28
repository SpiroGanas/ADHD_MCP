"""Shared test fixtures: in-memory MCP client and a fixed clock."""

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from fastmcp import Client

from adhd_mcp.clock import FixedClock
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.server import create_server
from adhd_mcp.terminology.site_codes import load_site_codes
from adhd_mcp.tools.context import ToolContext
from tests.personas import all_resources


@pytest.fixture(autouse=True)
def _no_server_settings_from_the_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests never read the developer's ADHD_MCP_* settings (peer review 01, T10: with
    ADHD_MCP_TRANSPORT=http in the shell the contract tests failed, and with an experimental
    condition switched on UPDATE_SNAPSHOTS=1 would have written the wrong contract)."""
    for name in [n for n in os.environ if n.startswith("ADHD_MCP_")]:
        monkeypatch.delenv(name)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def mcp_client() -> AsyncIterator[Client]:  # type: ignore[type-arg]
    """An MCP client connected in memory to a fresh server instance."""
    async with Client(create_server()) as client:
        yield client


@pytest.fixture
def fixed_clock() -> FixedClock:
    """A clock frozen at 2026-06-15T12:00Z. Tests never read the real clock."""
    return FixedClock(datetime(2026, 6, 15, 12, 0, tzinfo=UTC))


@pytest.fixture
def persona_context(fixed_clock: FixedClock) -> ToolContext:
    """Tools reading the persona catalog through the fixture adapter, at the catalog date."""
    return ToolContext(
        port=FixtureFhirAdapter(all_resources()),
        clock=fixed_clock,
        site_codes=load_site_codes("synthetic"),
    )


@pytest.fixture
async def persona_client(persona_context: ToolContext) -> AsyncIterator[Client]:  # type: ignore[type-arg]
    """An MCP client whose server reads the persona catalog."""
    async with Client(create_server(persona_context)) as client:
        yield client
