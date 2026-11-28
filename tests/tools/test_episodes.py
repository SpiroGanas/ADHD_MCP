"""Peer review 01, C2 (experiments E2, E2b, E14): related findings are not independent
signals. A follow-up visit is not a new injury, and one visit supplies at most one
high-weight signal (owner decision 2026-11-28, a draft for the clinical reviewer)."""

from datetime import UTC, datetime
from typing import Any, cast

import pytest
from fastmcp import Client

from adhd_mcp.clock import FixedClock
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.server import create_server
from adhd_mcp.terminology.site_codes import load_site_codes
from adhd_mcp.tools.context import ToolContext
from tests.personas.builder import PersonaBuilder

pytestmark = pytest.mark.anyio

CLOCK = FixedClock(datetime(2026, 6, 15, 12, 0, tzinfo=UTC))


async def call(p: PersonaBuilder, tool: str = "assess_referral_need") -> dict[str, Any]:
    context = ToolContext(
        port=FixtureFhirAdapter(p.resources), clock=CLOCK, site_codes=load_site_codes("synthetic")
    )
    async with Client(create_server(context)) as client:
        result = await client.call_tool(tool, {"patient_id": p.patient_id})
    assert result.structured_content is not None
    return cast(dict[str, Any], result.structured_content)


def person() -> PersonaBuilder:
    return PersonaBuilder("t95", gender="male", birth_date="1985-01-01")


def visit(p: PersonaBuilder, day: str, *codes: str) -> str:
    eid = p.encounter("EMER", f"{day}T10:00:00Z", f"{day}T14:00:00Z")
    for code in codes:
        p.condition(code, "x", recorded=day, encounter=eid, category="encounter-diagnosis")
    return eid


def present(out: dict[str, Any]) -> set[str]:
    return {s["signal"] for s in out["signals_checked"] if s["present"]}


async def test_a_crash_visit_with_a_blood_alcohol_code_is_one_signal_class() -> None:
    # E2: two_high_classes fired on this single visit with no modifier.
    p = person()
    visit(p, "2026-01-10", "V43.52XA", "Y90.4", "S06.0X0A")
    out = await call(p)
    assert {"crash_as_driver", "alcohol_involvement"} <= present(out)
    assert not any(r["fired"] for r in out["decision_trace"])
    assert out["recommendation"] == "no_recommendation"


async def test_two_crash_visits_are_not_also_two_injuries() -> None:
    # E2b
    p = person()
    visit(p, "2025-10-10", "V43.52XA", "S13.4XXA")
    visit(p, "2026-02-10", "V43.52XA", "S52.501A")
    out = await call(p)
    assert {"crash_as_driver", "repeated_accidental_injury"} <= present(out)
    assert out["recommendation"] == "no_recommendation"


async def test_a_follow_up_visit_is_not_a_new_injury() -> None:
    # E14: one fracture and its re-check ten days later were "2 found within 730 days".
    p = person()
    visit(p, "2026-01-10", "S52.501A", "W01.0XXA")
    visit(p, "2026-01-20", "S52.501D")
    p.condition("F32.9", "x", recorded="2026-01-10")
    p.condition("G47.00", "x", recorded="2026-01-10")
    out = await call(p)
    injury = next(s for s in out["signals_checked"] if s["signal"] == "repeated_accidental_injury")
    assert (injury["present"], injury["count"]) == (False, 1)
    assert out["recommendation"] == "no_recommendation"
    summary = await call(p, "get_utilization_summary")
    visits = [e for e in summary["events"] if e["kind"] == "injury_visit"]
    assert [e["follow_up"] for e in visits] == [False, True]


@pytest.mark.parametrize("seventh", ["D", "G", "K", "P", "S"])
async def test_subsequent_and_sequela_characters_are_follow_ups(seventh: str) -> None:
    p = person()
    visit(p, "2026-01-10", "S52.501A")
    visit(p, "2026-02-10", f"S52.501{seventh}")
    out = await call(p, "get_utilization_summary")
    visits = [e for e in out["events"] if e["kind"] == "injury_visit"]
    assert [e["follow_up"] for e in visits] == [False, True]


async def test_two_new_injuries_still_count() -> None:
    p = person()
    visit(p, "2026-01-10", "S52.501A")
    visit(p, "2026-03-10", "S62.302B")
    p.condition("F32.9", "x", recorded="2026-01-10")
    p.condition("G47.00", "x", recorded="2026-01-10")
    out = await call(p)
    assert "repeated_accidental_injury" in present(out)
    assert out["recommendation"] == "consider_referral_for_formal_screening"
