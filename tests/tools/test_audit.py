"""Audit: exactly one record per tool call, failures included; trace ids; no clinical
values or free text in any audit record or log line (standing invariant 5)."""

import dataclasses
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client

from adhd_mcp.audit.middleware import output_hash
from adhd_mcp.audit.records import JsonlAuditSink, MemoryAuditSink
from adhd_mcp.clock import FixedClock
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.server import create_server
from adhd_mcp.terminology.site_codes import load_site_codes
from adhd_mcp.tools.context import ToolContext, default_conditions
from tests.personas import all_resources
from tests.personas.builder import PersonaBuilder
from tests.tools.test_shared_tool_behavior import PATIENT_TOOLS

pytestmark = pytest.mark.anyio

CLOCK = FixedClock(datetime(2026, 6, 15, 12, 0, tzinfo=UTC))
ALL_TOOLS = [*PATIENT_TOOLS, "draft_referral_proposal"]

CANARY_TEXT = "CANARY-7f3e-free-text"
CANARY_VALUE = 9876.54321
CANARY_NAME = "Canaryname"


def canary_persona() -> PersonaBuilder:
    """Synthetic patient whose record carries text and values that must never be logged."""
    p = PersonaBuilder("p90", gender="male", birth_date="1990-01-01")
    p.resources[0]["name"] = [{"family": CANARY_NAME, "given": ["Synthetic"]}]
    p.condition("F15.10", CANARY_TEXT, recorded="2025-03-01")
    p.resources[-1]["code"]["text"] = CANARY_TEXT
    p.resources[-1]["note"] = [{"text": CANARY_TEXT}]
    p.observation("44261-6", CANARY_TEXT, "2026-01-01T10:00:00Z", value=1)
    p.resources[-1]["valueQuantity"]["value"] = CANARY_VALUE
    p.encounter("EMER", "2025-11-20T17:00:00Z", reasons=(("V43.52XA", CANARY_TEXT),))
    return p


def context(sink: Any, resources: list[dict[str, Any]] | None = None) -> ToolContext:
    return ToolContext(
        port=FixtureFhirAdapter(resources or all_resources()),
        clock=CLOCK,
        site_codes=load_site_codes("synthetic"),
        audit_sink=sink,
    )


@pytest.mark.parametrize("tool", ALL_TOOLS)
async def test_every_tool_call_writes_exactly_one_record(tool: str) -> None:
    sink = MemoryAuditSink()
    async with Client(create_server(context(sink))) as client:
        result = await client.call_tool(tool, {"patient_id": "p01-patient"})
    (record,) = sink.records
    assert record.tool == tool
    assert record.outcome == "success"
    assert record.caller == "local"
    assert record.patient is not None
    assert record.patient.id == "p01-patient"
    assert record.output_sha256 == output_hash(result.structured_content)
    assert record.time == CLOCK.now()
    assert any(r.resource_type == "Patient" for r in record.resources_read)
    assert len(record.trace_id) == 32


async def test_server_info_is_audited_without_a_patient() -> None:
    sink = MemoryAuditSink()
    async with Client(create_server(context(sink))) as client:
        await client.call_tool("get_server_info", {})
    (record,) = sink.records
    assert (record.tool, record.patient, record.resources_read) == ("get_server_info", None, [])


async def test_an_assessment_records_recommendation_ruleset_and_policy() -> None:
    sink = MemoryAuditSink()
    async with Client(create_server(context(sink))) as client:
        await client.call_tool("assess_referral_need", {"patient_id": "p01-patient"})
    (record,) = sink.records
    assert record.recommendation == "consider_referral_for_formal_screening"
    assert record.ruleset == "adhd 1.0.0 (draft)"
    assert record.scorer == "rules-only 1.0.0"
    assert record.privacy_policy == "privacy 0.2.0"
    assert {r.id for r in record.resources_read} >= {"p01-patient", "p01-cond-8"}


async def test_a_configured_scorer_reaches_the_output_and_the_audit_record() -> None:
    sink = MemoryAuditSink()
    ctx = dataclasses.replace(context(sink), conditions=default_conditions(scorer="dummy"))
    async with Client(create_server(ctx)) as client:
        result = await client.call_tool("assess_referral_need", {"patient_id": "p01-patient"})
    (record,) = sink.records
    assert record.scorer == "dummy-not-a-model 0.0.1"
    out = result.structured_content
    assert out is not None
    assert out["scorer"] == {
        "id": "dummy-not-a-model",
        "version": "0.0.1",
        "score": 0.0,
        "failed": False,
    }
    assert out["recommendation"] == "consider_referral_for_formal_screening"


@pytest.mark.parametrize(
    ("args", "code", "patient"),
    [
        ({"patient_id": "../etc"}, "invalid_input", None),
        ({"patient_id": "p99-patient"}, "patient_not_found", "p99-patient"),
        ({"patient_id": "p01-patient", "as_of": "2030-01-01"}, "invalid_input", "p01-patient"),
    ],
)
async def test_a_failed_call_is_recorded_as_failed(
    args: dict[str, Any], code: str, patient: str | None
) -> None:
    sink = MemoryAuditSink()
    async with Client(create_server(context(sink))) as client:
        result = await client.call_tool("check_safety_gate", args, raise_on_error=False)
    assert result.is_error
    (record,) = sink.records
    assert (record.outcome, record.error_code) == ("error", code)
    assert (record.patient.id if record.patient else None) == patient
    assert record.output_sha256 is None


async def test_the_trace_id_comes_from_the_request_traceparent() -> None:
    sink = MemoryAuditSink()
    parent = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
    async with Client(create_server(context(sink))) as client:
        for traceparent in (parent, "junk"):
            await client.call_tool(
                "check_safety_gate",
                {"patient_id": "p01-patient"},
                meta={"traceparent": traceparent},
            )
    assert sink.records[0].trace_id == "0af7651916cd43dd8448eb211c80319c"
    assert sink.records[1].trace_id != "0af7651916cd43dd8448eb211c80319c"


async def test_the_jsonl_sink_appends(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    path.write_text('{"earlier": true}\n', encoding="utf-8")
    async with Client(create_server(context(JsonlAuditSink(path)))) as client:
        await client.call_tool("get_server_info", {})
        await client.call_tool("check_safety_gate", {"patient_id": "p01-patient"})
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == '{"earlier": true}'
    assert [json.loads(x)["tool"] for x in lines[1:]] == ["get_server_info", "check_safety_gate"]


async def test_canary_clinical_content_never_reaches_audit_or_logs(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    p = canary_persona()
    path = tmp_path / "audit.jsonl"
    caplog.set_level(logging.DEBUG)
    async with Client(create_server(context(JsonlAuditSink(path), p.resources))) as client:
        for tool in ALL_TOOLS:
            await client.call_tool(tool, {"patient_id": p.patient_id})
            future = {"patient_id": p.patient_id, "as_of": "2031-01-01"}
            await client.call_tool(tool, future, raise_on_error=False)
    written = path.read_text(encoding="utf-8") + "\n".join(
        r.getMessage() + repr(r.args) for r in caplog.records
    )
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2 * len(ALL_TOOLS)
    for canary in (CANARY_TEXT, str(CANARY_VALUE), CANARY_NAME, "F15.10", "V43.52XA"):
        assert canary not in written, canary
