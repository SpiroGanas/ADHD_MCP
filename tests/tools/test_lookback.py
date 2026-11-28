"""Peer review 01, C1 (experiment E1): codes from 2008 to 2010 that are not active
problem-list items no longer count as current, and no reason states a recency that is not
true."""

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


async def assess(p: PersonaBuilder) -> dict[str, Any]:
    context = ToolContext(
        port=FixtureFhirAdapter(p.resources), clock=CLOCK, site_codes=load_site_codes("synthetic")
    )
    async with Client(create_server(context)) as client:
        result = await client.call_tool("assess_referral_need", {"patient_id": p.patient_id})
    assert result.structured_content is not None
    return cast(dict[str, Any], result.structured_content)


def e1(category: str | None = None) -> PersonaBuilder:
    """E1's codes. With no category: problem-list items without a clinical status."""
    p = PersonaBuilder("t90", gender="male", birth_date="1975-01-01")
    for code, when in (("Y90.3", "2010-03-01"), ("F32.9", "2009-06-01"), ("G47.00", "2008-04-01")):
        cid = p.condition(code, "x", recorded=when, category=category or "problem-list-item")
        if category is None:
            del next(r for r in p.resources if r["id"] == cid)["clinicalStatus"]
    return p


async def test_old_codes_without_a_status_do_not_count() -> None:
    out = await assess(e1())
    assert out["recommendation"] == "no_recommendation"
    why = {s["signal"]: s["reason"] for s in out["signals_checked"]}
    assert why["alcohol_involvement"] == "Last recorded 2010-03-01, outside the 1095-day window."


async def test_old_encounter_diagnoses_do_not_count() -> None:
    out = await assess(e1(category="encounter-diagnosis"))
    assert out["recommendation"] == "no_recommendation"


async def test_an_old_blood_alcohol_code_never_counts_even_as_an_active_problem() -> None:
    out = await assess(e1(category="problem-list-item"))
    # Depression and insomnia remain active problems; the 2010 Y90.3 does not count.
    present = {s["signal"] for s in out["signals_checked"] if s["present"]}
    assert present == {"depression_or_anxiety", "insomnia"}
    assert out["recommendation"] == "no_recommendation"
    reasons = [s["reason"] for s in out["signals_checked"] if s["present"]]
    assert all(r.startswith("Counted as current: an active problem-list entry") for r in reasons)
