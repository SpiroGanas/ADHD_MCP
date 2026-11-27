"""The ADHD signal catalog: complete, consistent with the evidence tools, verified only."""

import tomllib
from importlib.resources import files
from typing import Any

import pytest
from fastmcp import Client

from adhd_mcp.rules.catalog import load_catalog, parse_catalog

pytestmark = pytest.mark.anyio

CATALOG = load_catalog("adhd_mcp.data.adhd")


def data(name: str) -> dict[str, Any]:
    return tomllib.loads(files("adhd_mcp.data").joinpath(name).read_text(encoding="utf-8"))


def test_the_catalog_has_the_owner_approved_signals_and_weights() -> None:
    weights = {s.id: s.weight for s in CATALOG.signals}
    assert {k for k, v in weights.items() if v == "high"} == {
        "stimulant_related_disorder",
        "alcohol_involvement",
        "crash_as_driver",
        "repeated_accidental_injury",
    }
    assert {k for k, v in weights.items() if v == "note"} == {"tbi_overlap"}
    assert len([v for v in weights.values() if v == "modifier"]) == 12


def test_condition_signals_use_problem_list_families() -> None:
    families = set(data("problem_list.toml")["families"])
    for s in CATALOG.signals:
        if s.source == "condition":
            assert set(s.value_sets) <= families, s.id


def test_psychosocial_signals_name_a_domain_of_the_tool() -> None:
    domains = {d["id"] for d in data("psychosocial.toml")["domains"]}
    for s in CATALOG.signals:
        if s.source == "psychosocial":
            assert s.domain in domains, s.id


def test_medication_signals_name_a_class_of_the_tool() -> None:
    classes = set(data("medication_timeline.toml")["classes"])
    for s in CATALOG.signals:
        if s.source == "distinct_agents":
            assert s.drug_class in classes, s.id


def test_event_signals_name_an_event_kind_the_tool_counts() -> None:
    for s in CATALOG.signals:
        if s.source == "events":
            assert s.event in {"injury_visit", "crash_as_driver", "psychiatric_stay"}, s.id
            assert s.window_days <= 730 or s.event == "crash_as_driver"


async def test_every_signal_names_a_registered_tool(mcp_client: Client) -> None:  # type: ignore[type-arg]
    tools = {t.name for t in await mcp_client.list_tools()}
    for s in CATALOG.signals:
        assert s.tool in tools, s.id


def test_substance_use_signals_are_marked_protected() -> None:
    for s in CATALOG.signals:
        if any(v.startswith("sud.") for v in s.value_sets):
            assert s.protected == "substance_use", s.id


def test_a_signal_on_an_unknown_value_set_is_refused() -> None:
    text = """
id = "x"
version = "1"
condition = "x"
reviewed_by_owner = false
[[signals]]
id = "s"
title = "s"
weight = "high"
source = "condition"
tool = "get_mh_problem_list"
value_sets = ["unknown.test"]
window_days = 10
evidence = "test"
inference = true
"""
    with pytest.raises(LookupError):
        parse_catalog(text)
    assert parse_catalog(text, strict=False).signals[0].id == "s"


def test_a_signal_missing_its_definition_is_refused() -> None:
    text = """
id = "x"
version = "1"
condition = "x"
reviewed_by_owner = false
[[signals]]
id = "s"
title = "s"
weight = "modifier"
source = "events"
tool = "t"
window_days = 10
evidence = "test"
inference = true
"""
    with pytest.raises(ValueError, match="missing its definition"):
        parse_catalog(text, strict=False)


def test_duplicate_signal_ids_are_refused() -> None:
    entry = """
[[signals]]
id = "s"
title = "s"
weight = "note"
source = "condition"
tool = "t"
value_sets = ["mh.ptsd"]
window_days = 10
evidence = "test"
inference = true
"""
    text = 'id = "x"\nversion = "1"\ncondition = "x"\nreviewed_by_owner = false\n' + entry * 2
    with pytest.raises(ValueError, match="unique"):
        parse_catalog(text, strict=False)
