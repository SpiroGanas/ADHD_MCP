"""Peer review 01, P1: a signal whose data a withhold policy removed is "not checked", never
"not found", and a rule that could not be evaluated leads to insufficient data (owner
decision 2026-11-28)."""

from datetime import UTC, datetime
from typing import Any, cast

import pytest
from fastmcp import Client

from adhd_mcp.clock import FixedClock
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.privacy import load_privacy_policy
from adhd_mcp.privacy.policy import Action, with_actions
from adhd_mcp.server import create_server
from adhd_mcp.terminology.site_codes import load_site_codes
from adhd_mcp.tools.context import ToolContext
from tests.personas.builder import PersonaBuilder

pytestmark = pytest.mark.anyio

CLOCK = FixedClock(datetime(2026, 6, 15, 12, 0, tzinfo=UTC))
WITHHELD = "Not checked: records it needs were withheld by the privacy policy."
SUBSTANCE_SIGNALS = {"stimulant_related_disorder", "alcohol_involvement", "other_substance_use"}


async def assess(p: PersonaBuilder, action: Action) -> dict[str, Any]:
    context = ToolContext(
        port=FixtureFhirAdapter(p.resources),
        clock=CLOCK,
        site_codes=load_site_codes("synthetic"),
        privacy=with_actions(load_privacy_policy(), {"substance_use": action}),
    )
    async with Client(create_server(context)) as client:
        result = await client.call_tool("assess_referral_need", {"patient_id": p.patient_id})
    assert result.structured_content is not None
    return cast(dict[str, Any], result.structured_content)


def reasons(out: dict[str, Any]) -> dict[str, str]:
    return {s["signal"]: s["reason"] for s in out["signals_checked"]}


def e6() -> PersonaBuilder:
    p = PersonaBuilder("t70", gender="male", birth_date="1985-01-01")
    p.condition("F15.20", "x", recorded="2026-01-10")
    p.condition("F10.20", "x", recorded="2026-01-10")
    p.condition("F32.9", "x", recorded="2026-01-10")
    p.condition("G47.00", "x", recorded="2026-01-10")
    return p


async def test_withheld_signals_are_not_checked_and_the_result_is_insufficient_data() -> None:
    # E6: the result was no_recommendation and each signal read "Not found in the record."
    out = await assess(e6(), "withhold")
    assert out["recommendation"] == "insufficient_data"
    why = reasons(out)
    for signal in SUBSTANCE_SIGNALS:
        assert why[signal] == WITHHELD
    assert why["depression_or_anxiety"].startswith("Counted as current")
    assert {s["signal"] for s in out["signals_checked"] if s["present"]} == {
        "depression_or_anxiety",
        "insomnia",
    }


async def test_without_withheld_records_the_signals_read_as_usual() -> None:
    p = PersonaBuilder("t71", gender="male", birth_date="1985-01-01")
    p.condition("F32.9", "x", recorded="2026-01-10")
    p.condition("I10", "x", recorded="2026-01-10")
    out = await assess(p, "withhold")
    assert out["recommendation"] == "no_recommendation"
    assert reasons(out)["alcohol_involvement"] == "Not found in the record."


async def test_a_rule_that_fires_without_the_withheld_signals_still_recommends() -> None:
    p = e6()
    p.encounter("EMER", "2026-02-01T10:00:00Z", reasons=(("V43.52XA", "driver"),))
    p.encounter("EMER", "2026-03-01T10:00:00Z", reasons=(("S52.501A", "fracture"),))
    p.encounter("EMER", "2026-04-01T10:00:00Z", reasons=(("S62.302A", "fracture"),))
    out = await assess(p, "withhold")
    assert out["recommendation"] == "consider_referral_for_formal_screening"
    assert reasons(out)["alcohol_involvement"] == WITHHELD


async def test_an_encounter_withheld_for_its_reason_leaves_visit_signals_unchecked() -> None:
    p = PersonaBuilder("t72", gender="male", birth_date="1985-01-01")
    p.encounter("EMER", "2026-02-01T10:00:00Z", reasons=(("Y90.4", "blood alcohol"),))
    p.condition("F32.9", "x", recorded="2026-01-10")
    out = await assess(p, "withhold")
    why = reasons(out)
    assert why["crash_as_driver"] == WITHHELD
    assert why["repeated_accidental_injury"] == WITHHELD
    assert out["recommendation"] == "insufficient_data"


async def test_the_cite_policy_is_unchanged() -> None:
    out = await assess(e6(), "cite")
    assert out["recommendation"] == "consider_referral_for_formal_screening"
