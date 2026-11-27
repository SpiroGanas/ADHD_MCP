"""End to end over HTTP with authentication (Phase 6 exit criterion): an MCP client with a
valid bearer token calls the server's streamable HTTP endpoint, which reads the local FHIR
server; audit records are written; the caller's token never reaches the FHIR server.

Run: docker compose up -d fhir && uv run pytest -m integration
"""

from pathlib import Path

import pytest

from adhd_mcp.audit.records import JsonlAuditSink
from adhd_mcp.clock import FixedClock
from adhd_mcp.fhir.http_adapter import HttpFhirAdapter
from adhd_mcp.server import build_auth, create_server
from adhd_mcp.terminology.site_codes import load_site_codes
from adhd_mcp.tools.context import ToolContext
from tests.tools.test_http_auth import AUDIENCE, Harness, token

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


async def test_authenticated_http_assessment_against_the_live_fhir_server(
    loaded_server: str, fixed_clock: FixedClock, tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    audit = tmp_path / "audit.jsonl"
    async with HttpFhirAdapter(loaded_server) as adapter:
        context = ToolContext(
            port=adapter,
            clock=fixed_clock,
            site_codes=load_site_codes("synthetic"),
            audit_sink=JsonlAuditSink(audit),
        )
        harness.app = create_server(context, auth=build_auth(harness.settings)).http_app(
            path="/mcp"
        )
        bearer = token()
        async with harness.running(), harness.client(bearer) as client:
            result = await client.call_tool("assess_referral_need", {"patient_id": "p01-patient"})
    assert result.structured_content is not None
    assert result.structured_content["recommendation"] == "consider_referral_for_formal_screening"
    assert AUDIENCE.endswith("/mcp")
    text = audit.read_text(encoding="utf-8")
    assert '"tool": "assess_referral_need"' in text
    assert bearer not in text
