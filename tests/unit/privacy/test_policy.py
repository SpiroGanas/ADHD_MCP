"""The sensitive-data policy: classification, withhold, cite (restricted), disclosure."""

from datetime import UTC, datetime
from typing import Any

import pytest
from fastmcp import Client

from adhd_mcp.clock import FixedClock
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.privacy import PrivacyLedger, PrivacyPort, load_privacy_policy
from adhd_mcp.privacy.policy import parse_privacy_policy, redact_output, with_actions
from adhd_mcp.server import create_server
from adhd_mcp.terminology.site_codes import load_site_codes
from adhd_mcp.tools.context import ToolContext
from tests.personas import all_resources
from tests.personas.builder import PersonaBuilder

pytestmark = pytest.mark.anyio

POLICY = load_privacy_policy()
ACT = "http://terminology.hl7.org/CodeSystem/v3-ActCode"


def condition(code: str, labels: tuple[str, ...] = ()) -> dict[str, Any]:
    p = PersonaBuilder("t70", gender="male", birth_date="1990-01-01")
    p.condition(code, "x", recorded="2025-01-01")
    raw = p.resources[-1]
    if labels:
        raw["meta"] = {"security": [{"system": ACT, "code": c} for c in labels]}
    return raw


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (condition("F10.20"), {"substance_use"}),
        (condition("F15.10"), {"substance_use"}),
        (condition("Y90.3"), {"substance_use"}),
        (condition("B20"), {"hiv"}),
        (condition("D57.1"), {"sickle_cell"}),
        (condition("I10", ("ETH",)), {"substance_use"}),
        (condition("I10", ("HIV", "SCA")), {"hiv", "sickle_cell"}),
        (condition("I10"), set()),
        (condition("F43.10", ("PSY",)), set()),
    ],
)
def test_resources_are_classified_by_code_and_by_security_label(
    raw: dict[str, Any], expected: set[str]
) -> None:
    assert POLICY.classify(raw) == expected


def test_the_default_policy_cites_every_category() -> None:
    assert POLICY.actions == {"hiv": "cite", "sickle_cell": "cite", "substance_use": "cite"}


def test_a_policy_naming_an_unknown_category_is_refused() -> None:
    text = 'id = "x"\nversion = "1"\ncategories = []\n[actions]\nmystery = "withhold"\n'
    with pytest.raises(ValueError, match="unknown categories"):
        parse_privacy_policy(text)


async def test_withheld_resources_never_reach_the_caller_and_are_counted() -> None:
    p = PersonaBuilder("t71", gender="male", birth_date="1990-01-01")
    p.condition("F10.20", "x", recorded="2025-01-01")
    p.condition("I10", "x", recorded="2025-01-01")
    ledger = PrivacyLedger()
    port = PrivacyPort(
        FixtureFhirAdapter(p.resources), with_actions(POLICY, {"substance_use": "withhold"}), ledger
    )
    found = await port.search("Condition", p.patient_id)
    await port.search("Condition", p.patient_id)  # read twice, counted once
    assert [r["code"]["coding"][0]["code"] for r in found.resources] == ["I10"]
    assert ledger.note(POLICY).withheld[0].model_dump() == {
        "category": "substance_use",
        "records": 1,
    }
    assert ledger.restricted_refs == set()


def test_redaction_replaces_codes_but_keeps_references_and_dates() -> None:
    out = {
        "entries": [
            {
                "code": {"system": "s", "code": "F10.20", "display": "d"},
                "first_recorded": "2025-01-01",
                "references": [{"resource_type": "Condition", "id": "c1", "version": None}],
            },
            {
                "code": {"system": "s", "code": "I10", "display": None},
                "references": [{"resource_type": "Condition", "id": "c2", "version": None}],
            },
        ]
    }
    redacted = redact_output(out, {("Condition", "c1")})
    first, second = redacted["entries"]
    assert first["code"] == {"system": None, "code": "restricted", "display": None}
    assert first["first_recorded"] == "2025-01-01"
    assert first["references"] == out["entries"][0]["references"]
    assert second == out["entries"][1]


def context(actions: dict[str, Any] | None = None) -> ToolContext:
    return ToolContext(
        port=FixtureFhirAdapter(all_resources()),
        clock=FixedClock(datetime(2026, 6, 15, 12, 0, tzinfo=UTC)),
        site_codes=load_site_codes("synthetic"),
        privacy=with_actions(POLICY, actions or {}),
    )


async def call(ctx: ToolContext, tool: str, pid: str) -> dict[str, Any]:
    async with Client(create_server(ctx)) as client:
        result = await client.call_tool(tool, {"patient_id": pid})
    out: dict[str, Any] | None = result.structured_content
    assert out is not None
    return out


async def test_under_cite_substance_codes_are_restricted_in_the_problem_list() -> None:
    out = await call(context(), "get_mh_problem_list", "p01-patient")
    codes = {e["code"]["code"] for f in out["families"] for e in f["entries"]}
    assert "restricted" in codes
    assert not codes & {"F15.10", "F10.10"}
    assert "G47.00" in codes
    assert {c["category"] for c in out["privacy"]["restricted"]} == {"substance_use"}
    assert out["privacy"]["withheld"] == []


async def test_under_cite_the_assessment_still_uses_substance_signals() -> None:
    out = await call(context(), "assess_referral_need", "p01-patient")
    assert {"alcohol_involvement", "stimulant_related_disorder"} <= {
        b["signal"] for b in out["basis"]
    }
    assert "F15.10" not in str(out)


async def test_under_withhold_substance_signals_are_absent_and_the_output_says_so() -> None:
    out = await call(context({"substance_use": "withhold"}), "assess_referral_need", "p01-patient")
    signals = {b["signal"] for b in out["basis"]}
    assert not signals & {"alcohol_involvement", "stimulant_related_disorder"}
    assert {"crash_as_driver", "repeated_accidental_injury"} <= signals
    assert out["privacy"]["withheld"] == [{"category": "substance_use", "records": 2}]


async def test_under_withhold_p12_loses_its_only_high_weight_signal() -> None:
    out = await call(context({"substance_use": "withhold"}), "assess_referral_need", "p12-patient")
    assert out["recommendation"] == "no_recommendation"
    assert [b["signal"] for b in out["basis"]] == ["ptsd"]
    assert out["privacy"]["withheld"][0]["category"] == "substance_use"


async def test_allow_shows_codes() -> None:
    out = await call(context({"substance_use": "allow"}), "get_mh_problem_list", "p01-patient")
    codes = {e["code"]["code"] for f in out["families"] for e in f["entries"]}
    assert {"F15.10", "F10.10"} <= codes
    assert out["privacy"]["restricted"] == []
