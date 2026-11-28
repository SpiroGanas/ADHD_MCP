"""Peer review 01, C3: a record outside the intended population (an adult, alive at the as-of
date) gets ``outside_intended_population`` before any rule runs; the safety gate still runs
and a positive gate still comes first (owner decision 2026-11-28)."""

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
OUTSIDE = "outside_intended_population"


def person(birth_date: str, **patient: Any) -> PersonaBuilder:
    """E7's codes: enough for a suggestion in an adult."""
    p = PersonaBuilder("t80", gender="female", birth_date=birth_date)
    p.resources[0].update(patient)
    if not birth_date:
        del p.resources[0]["birthDate"]
    p.condition("F10.20", "x", recorded="2026-01-10")
    p.condition("F32.9", "x", recorded="2026-01-10")
    p.condition("G47.00", "x", recorded="2026-01-10")
    return p


async def call(p: PersonaBuilder, tool: str = "assess_referral_need") -> dict[str, Any]:
    context = ToolContext(
        port=FixtureFhirAdapter(p.resources), clock=CLOCK, site_codes=load_site_codes("synthetic")
    )
    async with Client(create_server(context)) as client:
        result = await client.call_tool(tool, {"patient_id": p.patient_id})
    assert result.structured_content is not None
    return cast(dict[str, Any], result.structured_content)


async def test_a_child_gets_no_adult_screening_suggestion() -> None:
    # E7: a patient born in 2017 got "Offer an adult ADHD screen (for example the ASRS-5)".
    out = await call(person("2017-01-01"))
    assert out["recommendation"] == OUTSIDE
    assert out["suggested_next_step"] is None
    assert out["basis"] == []
    assert out["signals_checked"] == []
    assert out["decision_trace"] == []
    assert out["safety_gate"]["status"] == "clear_limited_data"
    assert any("under 18" in n for n in out["notes"])
    assert_no_diagnostic_language(out)


@pytest.mark.parametrize(
    ("birth_date", "outside"),
    [
        ("2008-06-15", False),  # 18 on the as-of date
        ("2008-06-16", True),  # 18 the day after
        ("2008", True),  # 17 or 18: cannot be ruled out
        ("2008-05", False),  # 18 by the end of May 2026 at the latest
        ("2008-06", True),
        ("1960-01-01", False),
    ],
)
async def test_the_age_boundary(birth_date: str, outside: bool) -> None:
    out = await call(person(birth_date))
    assert (out["recommendation"] == OUTSIDE) is outside


async def test_no_birth_date_is_outside_the_intended_population() -> None:
    out = await call(person(""))
    assert out["recommendation"] == OUTSIDE
    assert any("birth date" in n for n in out["notes"])


@pytest.mark.parametrize(
    ("deceased", "outside"),
    [
        ({"deceasedBoolean": True}, True),
        ({"deceasedBoolean": False}, False),
        ({"deceasedDateTime": "2026-03-01T10:00:00Z"}, True),
        ({"deceasedDateTime": "2026-06-20"}, False),  # after the as-of date
    ],
)
async def test_a_deceased_patient_is_outside_the_intended_population(
    deceased: dict[str, Any], outside: bool
) -> None:
    out = await call(person("1980-01-01", **deceased))
    assert (out["recommendation"] == OUTSIDE) is outside
    if outside:
        assert any("deceased" in n for n in out["notes"])


async def test_a_positive_safety_gate_still_comes_first() -> None:
    p = person("2012-01-01")
    p.condition("R45.851", "x", recorded="2026-05-01")
    out = await call(p)
    assert out["recommendation"] == "address_safety_gate_first"


async def test_no_draft_referral_outside_the_intended_population() -> None:
    out = await call(person("2017-01-01"), "draft_referral_proposal")
    assert out["draft"] is None
    assert out["recommendation"] == OUTSIDE
