"""Peer review 01, C4 and C5 (owner decision 2026-11-28, drafts for the clinical reviewer).

C4 (E4): current exposure to an ADHD medication without a narcolepsy reason and without an
ADHD code makes the exclusion unknown and holds the suggestion, with a note.
C5 (E3): with dispensing data present, an antidepressant ordered but never filled is not an
agent "with exposure".
"""

from datetime import UTC, datetime
from typing import Any, cast

import pytest
from fastmcp import Client

from adhd_mcp.clock import FixedClock
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.server import create_server
from adhd_mcp.terminology.site_codes import load_site_codes
from adhd_mcp.tools.context import ToolContext
from tests.helpers.wording import assert_no_diagnostic_language
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


def e4(dispensed: str = "2026-05-02", reason: tuple[str, str] | None = None) -> PersonaBuilder:
    p = PersonaBuilder("t96", gender="male", birth_date="1985-01-01")
    p.condition("F10.20", "x", recorded="2026-01-10")
    p.condition("F32.9", "x", recorded="2026-01-10")
    p.condition("G47.00", "x", recorded="2026-01-10")
    request = p.medication_request("6901", "methylphenidate", dispensed, reason=reason)
    p.medication_dispense(request, "6901", "methylphenidate", dispensed)
    return p


def check(out: dict[str, Any]) -> dict[str, Any]:
    return next(c for c in out["exclusions_checked"] if c["check"] == "adhd_medication_exposure")


async def test_current_adhd_medication_holds_the_suggestion() -> None:
    out = await call(e4())
    assert out["recommendation"] == "insufficient_data"
    assert out["excluded"] is None
    found = check(out)
    assert found["outcome"] == "found"
    assert [r["resource_type"] for r in found["references"]] == ["MedicationDispense"]
    assert any("ADHD medication" in n for n in out["notes"])
    assert_no_diagnostic_language(out)
    draft = await call(e4(), "draft_referral_proposal")
    assert draft["draft"] is None


@pytest.mark.parametrize(("dispensed", "held"), [("2026-03-01", True), ("2026-01-15", False)])
async def test_only_recent_exposure_counts(dispensed: str, held: bool) -> None:
    # 90 days before 2026-06-15 is 2026-03-17. A 30-day supply from 2026-03-01 reaches past
    # it; one from 2026-01-15 ends in February.
    out = await call(e4(dispensed))
    assert (out["recommendation"] == "insufficient_data") is held
    assert (check(out)["outcome"] == "found") is held


async def test_medication_for_narcolepsy_does_not_hold_the_suggestion() -> None:
    out = await call(e4(reason=("G47.419", "Narcolepsy")))
    assert out["recommendation"] == "consider_referral_for_formal_screening"
    assert check(out)["outcome"] == "not_found"


async def test_an_adhd_code_still_means_already_in_care() -> None:
    p = e4()
    p.condition("F90.0", "x", recorded="2021-09-09")
    out = await call(p)
    assert out["recommendation"] == "already_in_care"
    assert out["excluded"] is True


def e3(*, with_dispense: bool) -> PersonaBuilder:
    p = PersonaBuilder("t97", gender="female", birth_date="1985-01-01")
    p.condition("F10.20", "x", recorded="2026-01-10")
    p.condition("F32.9", "x", recorded="2026-01-10")
    for code, name, when in (
        ("36437", "sertraline", "2025-03-01"),
        ("4493", "fluoxetine", "2025-08-01"),
        ("42347", "bupropion", "2026-01-01"),
    ):
        p.medication_request(code, name, when, status="stopped")
    if with_dispense:
        # One unrelated dispense: the record does hold dispensing data.
        p.medication_dispense(None, "29046", "lisinopril", "2026-02-01")
    return p


async def test_orders_never_filled_are_not_agents_with_exposure() -> None:
    out = await call(e3(with_dispense=True))
    agents = next(s for s in out["signals_checked"] if s["signal"] == "multiple_antidepressants")
    assert (agents["present"], agents["reason"]) == (False, "Not found in the record.")
    assert out["recommendation"] == "no_recommendation"


async def test_without_any_dispensing_data_orders_still_count() -> None:
    out = await call(e3(with_dispense=False))
    agents = next(s for s in out["signals_checked"] if s["signal"] == "multiple_antidepressants")
    assert (agents["present"], agents["count"]) == (True, 3)
