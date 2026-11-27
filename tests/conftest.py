"""Shared test fixtures: in-memory MCP client and a fixed clock."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from fastmcp import Client

from adhd_mcp.clock import FixedClock
from adhd_mcp.server import create_server


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
