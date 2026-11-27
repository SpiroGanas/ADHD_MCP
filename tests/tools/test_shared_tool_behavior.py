"""Behaviour every patient tool shares: input validation, one error shape, a completeness
note, versions and the evidence notice. Extend PATIENT_TOOLS as tools are added."""

from typing import Any

import pytest
from fastmcp import Client

from adhd_mcp import versions
from adhd_mcp.clock import FixedClock
from adhd_mcp.fhir.errors import FhirRequestError
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.server import create_server
from adhd_mcp.terminology.site_codes import load_site_codes
from adhd_mcp.tools.context import ToolContext
from adhd_mcp.wording import load_wording
from tests.helpers.wording import assert_no_diagnostic_language
from tests.personas import persona_ids

pytestmark = pytest.mark.anyio

PATIENT_TOOLS = ["check_safety_gate"]


async def call(client: Client, tool: str, args: dict[str, Any]) -> Any:  # type: ignore[type-arg]
    return await client.call_tool(tool, args, raise_on_error=False)


def error_text(result: Any) -> str:
    assert result.is_error is True
    return str(result.content[0].text)


@pytest.mark.parametrize("tool", PATIENT_TOOLS)
@pytest.mark.parametrize("bad_id", ["", "../Patient", "a b", "x" * 65])
async def test_invalid_patient_id_is_an_input_error(
    persona_client: Client,  # type: ignore[type-arg]
    tool: str,
    bad_id: str,
) -> None:
    text = error_text(await call(persona_client, tool, {"patient_id": bad_id}))
    assert text.startswith("invalid_input:")


@pytest.mark.parametrize("tool", PATIENT_TOOLS)
async def test_unknown_patient_is_reported_as_not_found(
    persona_client: Client,  # type: ignore[type-arg]
    tool: str,
) -> None:
    text = error_text(await call(persona_client, tool, {"patient_id": "p99-patient"}))
    assert text.startswith("patient_not_found:")


@pytest.mark.parametrize("tool", PATIENT_TOOLS)
async def test_an_as_of_date_in_the_future_is_rejected(
    persona_client: Client,  # type: ignore[type-arg]
    tool: str,
) -> None:
    args = {"patient_id": "p01-patient", "as_of": "2026-06-16"}
    assert error_text(await call(persona_client, tool, args)).startswith("invalid_input:")


@pytest.mark.parametrize("tool", PATIENT_TOOLS)
async def test_output_carries_the_shared_fields(
    persona_client: Client,  # type: ignore[type-arg]
    tool: str,
) -> None:
    result = await call(persona_client, tool, {"patient_id": "p01-patient"})
    out = result.structured_content
    assert result.is_error is False
    assert out["patient_id"] == "p01-patient"
    assert out["as_of"] == "2026-06-15"
    assert out["is_diagnosis"] is False
    assert out["notice"] == load_wording().evidence_notice
    assert out["data_completeness"]
    assert out["versions"]["tool_contract"] == versions.TOOL_CONTRACT_VERSION


@pytest.mark.parametrize("tool", PATIENT_TOOLS)
async def test_an_explicit_as_of_date_is_used(
    persona_client: Client,  # type: ignore[type-arg]
    tool: str,
) -> None:
    args = {"patient_id": "p01-patient", "as_of": "2025-01-31"}
    assert (await call(persona_client, tool, args)).structured_content["as_of"] == "2025-01-31"


@pytest.mark.parametrize("tool", PATIENT_TOOLS)
async def test_empty_record_is_distinguishable_from_a_clean_one(
    persona_client: Client,  # type: ignore[type-arg]
    tool: str,
) -> None:
    out = (await call(persona_client, tool, {"patient_id": "p07-patient"})).structured_content
    assert {n["status"] for n in out["data_completeness"]} == {"empty"}


class UnreachableAdapter(FixtureFhirAdapter):
    async def read_patient(self, patient_id: str) -> dict[str, Any]:
        raise FhirRequestError("read Patient: gave up", status=503, transient=True)


@pytest.mark.parametrize("tool", PATIENT_TOOLS)
async def test_an_unreachable_server_is_a_distinct_error(
    fixed_clock: FixedClock, tool: str
) -> None:
    context = ToolContext(
        port=UnreachableAdapter([]), clock=fixed_clock, site_codes=load_site_codes("synthetic")
    )
    async with Client(create_server(context)) as client:
        text = error_text(await call(client, tool, {"patient_id": "p01-patient"}))
    assert text.startswith("fhir_unavailable:")


@pytest.mark.parametrize("tool", PATIENT_TOOLS)
async def test_a_server_without_a_fhir_source_says_so(fixed_clock: FixedClock, tool: str) -> None:
    context = ToolContext(port=None, clock=fixed_clock, site_codes=load_site_codes("synthetic"))
    async with Client(create_server(context)) as client:
        text = error_text(await call(client, tool, {"patient_id": "p01-patient"}))
    assert text.startswith("not_configured:")


@pytest.mark.parametrize("tool", PATIENT_TOOLS)
@pytest.mark.parametrize("persona_id", persona_ids())
async def test_no_output_contains_diagnostic_language(
    persona_client: Client,  # type: ignore[type-arg]
    tool: str,
    persona_id: str,
) -> None:
    result = await call(persona_client, tool, {"patient_id": f"{persona_id}-patient"})
    assert result.is_error is False
    assert_no_diagnostic_language(result.structured_content)
    assert_no_diagnostic_language([getattr(c, "text", "") for c in result.content])
