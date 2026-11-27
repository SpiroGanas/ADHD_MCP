"""The autism stub (Phase 8, item 5): a second condition that proves the plugin interface.
Experimental, disabled by default, with placeholder signals that are not clinical content."""

from datetime import UTC, date, datetime, timedelta

import pytest
from fastmcp import Client

from adhd_mcp.clock import FixedClock
from adhd_mcp.conditions.autism import autism_plugin
from adhd_mcp.config import ConfigError, load_settings
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.models.domain import CheckOutcome
from adhd_mcp.orchestration.assess import assess
from adhd_mcp.server import create_server
from adhd_mcp.terminology import load_value_set
from adhd_mcp.terminology.site_codes import load_site_codes
from adhd_mcp.tools.context import ToolContext, context_from_environment, default_conditions
from tests.helpers.failing_adapter import FailingAdapter, UnsupportingAdapter
from tests.helpers.wording import assert_no_diagnostic_language
from tests.personas.builder import PersonaBuilder

pytestmark = pytest.mark.anyio

AS_OF = date(2026, 6, 15)
SITE = load_site_codes("synthetic")


def person() -> PersonaBuilder:
    return PersonaBuilder("t70", gender="female", birth_date="1985-01-01")


def test_the_stub_is_marked_experimental_and_placeholder() -> None:
    plugin = autism_plugin()
    assert plugin.id == "autism"
    assert plugin.ruleset.status == "experimental"
    assert plugin.ruleset.validated is False
    assert plugin.catalog.reviewed_by_owner is False
    for signal in plugin.catalog.signals:
        assert signal.inference is True
        assert "placeholder" in signal.evidence.lower()
    assert all("experimental" in text.lower() for text in plugin.recommendation_texts.values())
    assert "not for clinical use" in plugin.next_step.lower()


def test_the_autism_exclusion_codes_are_verified() -> None:
    value_set = load_value_set("care.autism_diagnosis", strict=True)
    assert sorted(e.code for e in value_set.entries) == ["F84.0", "F84.5", "F84.8", "F84.9"]


async def exclusion(p: PersonaBuilder, adapter: FixtureFhirAdapter | None = None):  # type: ignore[no-untyped-def]
    plugin = autism_plugin()
    assert plugin.exclusions is not None
    records = PatientRecords(adapter or FixtureFhirAdapter(p.resources))
    return await plugin.exclusions(records, p.patient_id, AS_OF, SITE)


@pytest.mark.parametrize("code", ["F84.0", "F84.5", "F84.8", "F84.9"])
async def test_a_recorded_autism_code_excludes(code: str) -> None:
    p = person()
    p.condition(code, "x", recorded="2020-01-01")
    result = await exclusion(p)
    assert result.excluded is True
    assert result.checks[0].outcome is CheckOutcome.FOUND


@pytest.mark.parametrize("code", ["F84.2", "F84.3", "F90.0"])
async def test_codes_outside_the_value_set_do_not_exclude(code: str) -> None:
    p = person()
    p.condition(code, "x", recorded="2020-01-01")
    result = await exclusion(p)
    assert result.excluded is False
    assert result.checks[0].outcome is CheckOutcome.NOT_FOUND


async def test_a_code_recorded_after_the_as_of_date_does_not_exclude() -> None:
    p = person()
    p.condition("F84.0", "x", recorded="2026-07-01")
    assert (await exclusion(p)).excluded is False


async def test_a_failed_or_unoffered_condition_read_leaves_the_exclusion_unknown() -> None:
    p = person()
    failed = await exclusion(p, FailingAdapter(p, {"Condition"}))
    assert failed.excluded is None
    assert failed.checks[0].outcome is CheckOutcome.FAILED
    unoffered = await exclusion(p, UnsupportingAdapter(p, {"Condition"}))
    assert unoffered.excluded is None
    assert unoffered.checks[0].outcome is CheckOutcome.NOT_PERFORMED


def test_the_stub_is_off_by_default() -> None:
    assert default_conditions().ids() == ["adhd"]
    assert context_from_environment({}).conditions.ids() == ["adhd"]


def test_the_stub_is_switched_on_by_name() -> None:
    env = {"ADHD_MCP_EXPERIMENTAL_CONDITIONS": "autism"}
    assert load_settings(env).experimental_conditions == ("autism",)
    assert context_from_environment(env).conditions.ids() == ["adhd", "autism"]


def test_an_unknown_experimental_condition_is_refused() -> None:
    with pytest.raises(ConfigError, match="ADHD_MCP_EXPERIMENTAL_CONDITIONS"):
        load_settings({"ADHD_MCP_EXPERIMENTAL_CONDITIONS": "autism,bipolar"})


async def test_an_enabled_stub_is_assessed_through_the_same_tool() -> None:
    p = person()
    p.condition("F43.10", "x", recorded="2025-01-01")
    p.condition("F33.1", "x", recorded="2025-02-01")
    p.condition("F60.3", "x", recorded="2025-03-01")
    context = ToolContext(
        port=FixtureFhirAdapter(p.resources),
        clock=FixedClock(datetime(2026, 6, 15, 12, 0, tzinfo=UTC)),
        site_codes=SITE,
        conditions=default_conditions(experimental=("autism",)),
    )
    async with Client(create_server(context)) as client:
        result = await client.call_tool(
            "assess_referral_need", {"patient_id": p.patient_id, "condition": "autism"}
        )
    out = result.structured_content
    assert out is not None
    assert out["recommendation"] == "consider_referral_for_formal_screening"
    assert out["condition_to_screen"] == "Autism (experimental stub)"
    assert out["ruleset"] == "autism 0.0.1 (experimental)"
    assert "experimental" in out["recommendation_text"].lower()
    assert_no_diagnostic_language(out)


async def test_an_autism_code_makes_the_stub_already_in_care() -> None:
    p = person()
    for code in ("F43.10", "F33.1", "F60.3", "F84.0"):
        p.condition(code, "x", recorded="2025-01-01")
    plugin = autism_plugin()
    records = PatientRecords(FixtureFhirAdapter(p.resources))
    result = await assess(plugin, records, records, p.patient_id, AS_OF, site=SITE)
    assert result.recommendation == "already_in_care"
    assert plugin.ruleset.exclusions == ("existing_autism_code",)


def test_no_stub_text_implies_a_diagnosis() -> None:
    plugin = autism_plugin()
    assert_no_diagnostic_language(dict(plugin.recommendation_texts))
    assert_no_diagnostic_language({"next_step": plugin.next_step, "title": plugin.title})


async def test_the_stub_never_produces_a_referral_draft() -> None:
    p = person()
    for code in ("F43.10", "F33.1", "F60.3"):
        p.condition(code, "x", recorded="2025-01-01")
    context = ToolContext(
        port=FixtureFhirAdapter(p.resources),
        clock=FixedClock(datetime(2026, 6, 15, 12, 0, tzinfo=UTC)),
        site_codes=SITE,
        conditions=default_conditions(experimental=("autism",)),
    )
    async with Client(create_server(context)) as client:
        result = await client.call_tool(
            "draft_referral_proposal", {"patient_id": p.patient_id, "condition": "autism"}
        )
    out = result.structured_content
    assert out is not None
    assert out["recommendation"] == "consider_referral_for_formal_screening"
    assert out["draft"] is None
    assert "experimental" in out["why_no_draft"]
    assert_no_diagnostic_language(out)


async def test_two_of_the_three_placeholder_modifiers_do_not_fire() -> None:
    p = person()
    p.condition("F43.10", "x", recorded="2025-01-01")
    p.condition("F33.1", "x", recorded="2025-02-01")
    records = PatientRecords(FixtureFhirAdapter(p.resources))
    result = await assess(autism_plugin(), records, records, p.patient_id, AS_OF, site=SITE)
    assert result.recommendation == "no_recommendation"


@pytest.mark.parametrize(("days", "fires"), [(1095, True), (1096, False)])
async def test_the_placeholder_window_boundary(days: int, fires: bool) -> None:
    p = person()
    when = (AS_OF - timedelta(days=days)).isoformat()
    p.condition("F43.10", "x", recorded="2025-01-01")
    p.condition("F33.1", "x", recorded="2025-02-01")
    p.condition("F60.3", "x", recorded=when, onset=when, clinical="resolved")
    records = PatientRecords(FixtureFhirAdapter(p.resources))
    result = await assess(autism_plugin(), records, records, p.patient_id, AS_OF, site=SITE)
    assert result.decision.recommend is fires
