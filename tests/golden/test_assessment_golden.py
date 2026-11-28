"""Golden tests: every persona's assessment against the expectations written by hand in
tests/personas/catalog.toml before the engine existed, plus a stored full-output snapshot
per persona (update deliberately with UPDATE_SNAPSHOTS=1 and review the diff)."""

from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client

from adhd_mcp.rules.catalog import load_catalog
from tests.contract.snapshots import assert_matches_snapshot
from tests.personas import load_catalog as load_personas

pytestmark = pytest.mark.anyio

PERSONAS = {p["id"]: p for p in load_personas()["personas"]}
SNAPSHOTS = Path(__file__).parent / "snapshots"


async def assess(client: Client, persona_id: str) -> dict[str, Any]:  # type: ignore[type-arg]
    result = await client.call_tool("assess_referral_need", {"patient_id": f"{persona_id}-patient"})
    assert result.structured_content is not None
    return result.structured_content


@pytest.mark.parametrize("persona_id", sorted(PERSONAS))
async def test_assessment_matches_the_hand_written_expectation(
    persona_client: Client,  # type: ignore[type-arg]
    persona_id: str,
) -> None:
    expected = PERSONAS[persona_id]
    out = await assess(persona_client, persona_id)
    assert out["recommendation"] == expected["recommendation"]
    present = sorted(s["signal"] for s in out["signals_checked"] if s["present"])
    assert present == sorted(expected["signals"])
    fired = [t["rule_id"] for t in out["decision_trace"] if t["fired"]]
    assert fired == expected["rules_fired"]
    assert out["safety_gate"]["status"] == expected["safety_gate"]


@pytest.mark.parametrize("persona_id", sorted(PERSONAS))
async def test_full_output_matches_its_snapshot(
    persona_client: Client,  # type: ignore[type-arg]
    persona_id: str,
) -> None:
    out = await assess(persona_client, persona_id)
    out["versions"].pop("server")  # changes with every release
    # Changes with every data edit; checked by tests/tools/test_shared_tool_behavior.py.
    out["versions"].pop("clinical_content")
    assert_matches_snapshot(SNAPSHOTS / f"{persona_id}.json", out)


def test_every_catalog_signal_is_presented_by_at_least_one_persona() -> None:
    presented = {s for p in PERSONAS.values() for s in p["signals"]}
    missing = {s.id for s in load_catalog("adhd_mcp.data.adhd").signals} - presented
    assert missing == set()


def test_every_recommendation_has_a_persona() -> None:
    assert {p["recommendation"] for p in PERSONAS.values()} == {
        "consider_referral_for_formal_screening",
        "no_recommendation",
        "address_safety_gate_first",
        "already_in_care",
        "insufficient_data",
        "outside_intended_population",
    }
