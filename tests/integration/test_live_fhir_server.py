"""The HTTP adapter against a real FHIR server loaded with the personas.

Run: docker compose up -d fhir && uv run pytest -m integration
"""

import os
from collections.abc import AsyncIterator

import pytest
from scripts.load_personas import load

from adhd_mcp.fhir.http_adapter import HttpFhirAdapter
from adhd_mcp.fhir.normalize import normalize_many
from tests.adapters.shared_suite import SharedAdapterSuite
from tests.personas import persona_ids

pytestmark = pytest.mark.integration

FHIR_URL = os.environ.get("ADHD_MCP_TEST_FHIR_URL", "http://localhost:8080/fhir")


@pytest.fixture(scope="session")
def loaded_server() -> str:
    load(FHIR_URL)
    return FHIR_URL


@pytest.fixture
async def adapter(loaded_server: str) -> AsyncIterator[HttpFhirAdapter]:
    async with HttpFhirAdapter(loaded_server, page_size=2) as adapter:
        yield adapter


class TestHttpAdapterAgainstLiveServer(SharedAdapterSuite):
    pass


@pytest.mark.anyio
async def test_live_resources_normalize_like_the_fixtures(adapter: HttpFhirAdapter) -> None:
    for persona_id in persona_ids():
        conditions = await adapter.search("Condition", f"{persona_id}-patient")
        result = normalize_many(conditions)
        assert all(s.reason.value == "excluded_status" for s in result.skipped), persona_id
