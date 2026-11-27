"""Regression tests for the clinical safety review of Phases 4-6 (2026-11-27)."""

import json
import tomllib
from datetime import UTC, datetime
from importlib.resources import files
from typing import Any

import pytest
from fastmcp import Client

from adhd_mcp.clock import FixedClock
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.http_adapter import HttpFhirAdapter
from adhd_mcp.fhir.smart import SmartBackendAuth
from adhd_mcp.privacy import load_privacy_policy
from adhd_mcp.privacy.policy import with_actions
from adhd_mcp.rules.catalog import load_catalog
from adhd_mcp.server import create_server
from adhd_mcp.terminology.site_codes import load_site_codes
from adhd_mcp.tools.context import ToolContext
from tests.personas import all_resources
from tests.personas.builder import PersonaBuilder
from tests.tools.test_shared_tool_behavior import PATIENT_TOOLS

pytestmark = pytest.mark.anyio

POLICY = load_privacy_policy()
CLOCK = FixedClock(datetime(2026, 6, 15, 12, 0, tzinfo=UTC))
ACT = "http://terminology.hl7.org/CodeSystem/v3-ActCode"
TOOLS = [*PATIENT_TOOLS, "draft_referral_proposal"]


def context(resources: list[dict[str, Any]], actions: dict[str, Any] | None = None) -> ToolContext:
    return ToolContext(
        port=FixtureFhirAdapter(resources),
        clock=CLOCK,
        site_codes=load_site_codes("synthetic"),
        privacy=with_actions(POLICY, actions or {}),
    )


async def run_all(ctx: ToolContext, pid: str) -> dict[str, dict[str, Any]]:
    out = {}
    async with Client(create_server(ctx)) as client:
        for tool in TOOLS:
            result = await client.call_tool(tool, {"patient_id": pid})
            assert result.structured_content is not None
            out[tool] = result.structured_content
    return out


@pytest.mark.parametrize("action", ["cite", "withhold"])
@pytest.mark.parametrize("code", ["B20", "Z21", "D57.1"])
async def test_hiv_and_sickle_cell_status_is_never_revealed(code: str, action: str) -> None:
    """B1: no output or rule uses these categories, so no output may name them."""
    p = PersonaBuilder("t80", gender="male", birth_date="1990-01-01")
    p.condition(code, "x", recorded="2025-01-01")
    p.condition("I10", "x", recorded="2025-01-01")
    actions = {"hiv": action, "sickle_cell": action}
    outputs = await run_all(context(p.resources, actions), p.patient_id)
    for tool, out in outputs.items():
        text = json.dumps(out).lower()
        assert "hiv" not in text, tool
        assert "sickle" not in text, tool
        assert code.lower() not in text, tool
        statuses = {n["status"] for n in out.get("data_completeness", [])}
        assert "withheld" not in statuses, tool


def labelled_self_harm() -> PersonaBuilder:
    """B2: a self-harm code carrying a substance-use security label, plus ADHD signals."""
    p = PersonaBuilder("t81", gender="male", birth_date="1990-01-01")
    p.condition("R45.851", "x", recorded="2026-05-01")
    p.resources[-1]["meta"] = {"security": [{"system": ACT, "code": "SUD"}]}
    for days in ("2025-09-01", "2026-02-01"):
        visit = p.encounter("EMER", f"{days}T10:00:00Z")
        p.condition("S62.302A", "x", recorded=days, encounter=visit)
    visit = p.encounter("EMER", "2025-11-20T10:00:00Z")
    p.condition("V43.52XA", "x", recorded="2025-11-20", encounter=visit)
    return p


@pytest.mark.parametrize("action", ["allow", "cite", "withhold"])
async def test_a_withhold_policy_never_hides_a_self_harm_signal_from_the_gate(action: str) -> None:
    p = labelled_self_harm()
    outputs = await run_all(context(p.resources, {"substance_use": action}), p.patient_id)
    assessment = outputs["assess_referral_need"]
    assert assessment["safety_gate"]["status"] == "positive"
    assert assessment["recommendation"] == "address_safety_gate_first"
    assert outputs["check_safety_gate"]["safety_gate"]["status"] == "positive"
    assert outputs["draft_referral_proposal"]["draft"] is None


async def test_withheld_records_mark_their_category_withheld_not_complete() -> None:
    p = labelled_self_harm()
    out = await run_all(context(p.resources, {"substance_use": "withhold"}), p.patient_id)
    statuses = {n["category"]: n["status"] for n in out["get_mh_problem_list"]["data_completeness"]}
    assert statuses["Condition"] == "withheld"


async def test_the_draft_note_names_protected_signals_only_when_allowed() -> None:
    for action, named in (("cite", False), ("withhold", False), ("allow", True)):
        ctx = context(all_resources(), {"substance_use": action})
        async with Client(create_server(ctx)) as client:
            result = await client.call_tool(
                "draft_referral_proposal", {"patient_id": "p01-patient"}
            )
        assert result.structured_content is not None
        notes = json.dumps(result.structured_content["draft"]["note"])
        assert ("Alcohol involvement" in notes) is named, action
        assert "Crash" in notes or "crash" in notes


def test_disclosure_flags_match_what_outputs_use() -> None:
    """A category may be hidden (disclose = false) only if no output family or signal uses
    any of its value sets."""
    used = set(
        tomllib.loads(files("adhd_mcp.data").joinpath("problem_list.toml").read_text("utf-8"))[
            "families"
        ]
    )
    used |= {v for s in load_catalog("adhd_mcp.data.adhd").signals for v in s.value_sets}
    for category in POLICY.categories:
        overlaps = bool(set(category.value_sets) & used)
        assert category.disclose is overlaps, category.id


def test_an_authenticated_fhir_server_must_use_https() -> None:
    auth = SmartBackendAuth(
        token_url="https://auth.example.test/token",
        client_id="x",
        private_key_pem="unused",
        key_id="k",
        scope="s",
        clock=CLOCK,
    )
    with pytest.raises(ValueError, match="https"):
        HttpFhirAdapter("http://fhir.example.test/r4", auth=auth)
    HttpFhirAdapter("http://localhost:8080/fhir", auth=auth)


async def test_psychosocial_signal_explains_an_observation_only_finding() -> None:
    p = PersonaBuilder("t82", gender="male", birth_date="1990-01-01")
    p.resources.append(
        {
            "resourceType": "Observation",
            "id": "t82-sdoh-1",
            "status": "final",
            "code": {"coding": [{"system": "urn:adhd-mcp:synthetic-local-code", "code": "x"}]},
            "subject": {"reference": f"Patient/{p.patient_id}"},
            "effectiveDateTime": "2026-01-01",
            "valueCodeableConcept": {
                "coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "Z65.1"}]
            },
        }
    )
    out = (await run_all(context(p.resources), p.patient_id))["assess_referral_need"]
    legal = next(s for s in out["signals_checked"] if s["signal"] == "legal_problems")
    assert legal["present"] is False
    assert "social-history observations" in legal["reason"]
