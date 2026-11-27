"""assess_referral_need: trace, determinism, query count, plugins and input checks."""

import json
from datetime import UTC, date, datetime
from typing import Any

import pytest
from fastmcp import Client

from adhd_mcp.clock import FixedClock
from adhd_mcp.conditions.base import ConditionPlugin, ConditionRegistry
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.port import SearchResult, SearchType
from adhd_mcp.rules.catalog import parse_catalog
from adhd_mcp.rules.ruleset import parse_ruleset
from adhd_mcp.server import create_server
from adhd_mcp.terminology.site_codes import load_site_codes
from adhd_mcp.tools.context import ToolContext, default_conditions
from tests.personas import all_resources, persona_ids

pytestmark = pytest.mark.anyio

CLOCK = FixedClock(datetime(2026, 6, 15, 12, 0, tzinfo=UTC))


async def assess(client: Client, patient_id: str, **args: Any) -> dict[str, Any]:  # type: ignore[type-arg]
    result = await client.call_tool(
        "assess_referral_need", {"patient_id": patient_id, **args}, raise_on_error=False
    )
    assert result.is_error is False, result.content
    assert result.structured_content is not None
    return result.structured_content


@pytest.mark.parametrize("persona_id", persona_ids())
async def test_trace_and_basis_correspond(persona_client: Client, persona_id: str) -> None:  # type: ignore[type-arg]
    out = await assess(persona_client, f"{persona_id}-patient")
    basis = {b["signal"] for b in out["basis"]}
    counted = {s for t in out["decision_trace"] for s in t["high_signals"] + t["modifier_signals"]}
    assert counted == basis
    for rule in out["decision_trace"]:
        if rule["fired"]:
            assert set(rule["high_signals"] + rule["modifier_signals"]) <= basis


@pytest.mark.parametrize("persona_id", persona_ids())
async def test_safety_gate_is_the_first_field(persona_client: Client, persona_id: str) -> None:  # type: ignore[type-arg]
    out = await assess(persona_client, f"{persona_id}-patient")
    assert next(iter(out)) == "safety_gate"


async def test_repeated_and_shuffled_runs_give_identical_output() -> None:
    resources = all_resources()
    outputs = []
    for order in (resources, list(reversed(resources)), resources[1::2] + resources[0::2]):
        context = ToolContext(
            port=FixtureFhirAdapter(order), clock=CLOCK, site_codes=load_site_codes("synthetic")
        )
        async with Client(create_server(context)) as client:
            for pid in ("p01", "p14"):
                outputs.append(
                    (pid, json.dumps(await assess(client, f"{pid}-patient"), sort_keys=True))
                )
    by_persona: dict[str, set[str]] = {}
    for pid, text in outputs:
        by_persona.setdefault(pid, set()).add(text)
    assert all(len(texts) == 1 for texts in by_persona.values())


class CountingAdapter(FixtureFhirAdapter):
    def __init__(self, resources: list[dict[str, Any]]) -> None:
        super().__init__(resources)
        self.calls: list[tuple[str, str]] = []

    async def read_patient(self, patient_id: str) -> dict[str, Any]:
        self.calls.append(("Patient", patient_id))
        return await super().read_patient(patient_id)

    async def search(self, resource_type: SearchType, patient_id: str, **kw: Any) -> SearchResult:
        self.calls.append((resource_type, repr(sorted(kw.items()))))
        return await super().search(resource_type, patient_id, **kw)


async def test_one_assessment_issues_no_duplicate_fhir_queries() -> None:
    adapter = CountingAdapter(all_resources())
    context = ToolContext(port=adapter, clock=CLOCK, site_codes=load_site_codes("synthetic"))
    async with Client(create_server(context)) as client:
        await assess(client, "p01-patient")
    assert len(adapter.calls) == len(set(adapter.calls))
    assert ("Patient", "p01-patient") in adapter.calls


async def test_an_unknown_condition_is_an_input_error(persona_client: Client) -> None:  # type: ignore[type-arg]
    result = await persona_client.call_tool(
        "assess_referral_need",
        {"patient_id": "p01-patient", "condition": "autism"},
        raise_on_error=False,
    )
    assert result.is_error is True
    assert result.content[0].text.startswith("invalid_input:")  # type: ignore[union-attr]


async def test_an_earlier_as_of_date_changes_the_window(persona_client: Client) -> None:  # type: ignore[type-arg]
    # On 2024-12-31, p11's stimulant dependence (recorded 2025-02-01) is not yet known.
    out = await assess(persona_client, "p11-patient", as_of="2024-12-31")
    assert out["recommendation"] == "no_recommendation"
    present = [s["signal"] for s in out["signals_checked"] if s["present"]]
    assert present == ["crash_as_driver"]


DUMMY_CATALOG = """
id = "dummy.catalog"
version = "1"
condition = "dummy"
reviewed_by_owner = false
[[signals]]
id = "ptsd_signal"
title = "PTSD code"
weight = "high"
source = "condition"
tool = "get_mh_problem_list"
value_sets = ["mh.ptsd"]
window_days = 3650
evidence = "test only"
inference = true
"""
DUMMY_RULESET = """
id = "dummy"
version = "0.0.1"
status = "draft"
effective_date = "2026-11-27"
catalog = "dummy.catalog"
catalog_version = "1"
validated = false
exclusions = []
citations = ["test only"]
[[rules]]
id = "one_high"
description = "One high-weight signal"
min_high = 1
min_modifiers = 0
"""


async def test_a_test_only_condition_can_be_registered_and_assessed() -> None:
    texts = {
        code: f"dummy {code}"
        for code in (
            "consider_referral_for_formal_screening",
            "no_recommendation",
            "address_safety_gate_first",
            "already_in_care",
            "insufficient_data",
        )
    }
    registry: ConditionRegistry = default_conditions()
    registry.register(
        ConditionPlugin(
            id="dummy",
            title="Dummy condition",
            catalog=parse_catalog(DUMMY_CATALOG),
            ruleset=parse_ruleset(DUMMY_RULESET, released=()),
            recommendation_texts=texts,
            next_step="test only",
        )
    )
    context = ToolContext(
        port=FixtureFhirAdapter(all_resources()),
        clock=CLOCK,
        site_codes=load_site_codes("synthetic"),
        conditions=registry,
    )
    async with Client(create_server(context)) as client:
        out = await assess(client, "p09-patient", condition="dummy")
    assert out["recommendation"] == "consider_referral_for_formal_screening"
    assert out["condition_to_screen"] == "Dummy condition"
    assert out["recommendation_text"] == "dummy consider_referral_for_formal_screening"
    assert out["excluded"] is False
    assert out["scorer"] is None
    assert out["versions"]["ruleset"] == "dummy 0.0.1 (draft)"


def test_a_plugin_whose_ruleset_and_catalog_disagree_is_refused() -> None:
    with pytest.raises(ValueError, match="differ"):
        ConditionPlugin(
            id="dummy",
            title="x",
            catalog=parse_catalog(DUMMY_CATALOG),
            ruleset=parse_ruleset(
                DUMMY_RULESET.replace('catalog_version = "1"', 'catalog_version = "2"'), released=()
            ),
            recommendation_texts={},
            next_step="x",
        )


def test_registering_a_condition_twice_is_refused() -> None:
    registry = default_conditions()
    with pytest.raises(ValueError, match="already registered"):
        registry.register(registry.get("adhd"))
    with pytest.raises(LookupError):
        registry.get("nothing")


async def test_as_of_is_echoed(persona_client: Client) -> None:  # type: ignore[type-arg]
    out = await assess(persona_client, "p01-patient", as_of="2026-01-01")
    assert date.fromisoformat(out["as_of"]) == date(2026, 1, 1)
