from typing import Any

import pytest
from fastmcp import Client
from fhir.resources.R4B.servicerequest import ServiceRequest

from tests.personas import load_catalog

pytestmark = pytest.mark.anyio

EXPECTED = {p["id"]: p["recommendation"] for p in load_catalog()["personas"]}


async def draft(client: Client, patient_id: str) -> dict[str, Any]:  # type: ignore[type-arg]
    result = await client.call_tool("draft_referral_proposal", {"patient_id": patient_id})
    assert result.structured_content is not None
    return result.structured_content


@pytest.mark.parametrize("persona_id", sorted(EXPECTED))
async def test_a_draft_exactly_when_referral_is_suggested(
    persona_client: Client,  # type: ignore[type-arg]
    persona_id: str,
) -> None:
    out = await draft(persona_client, f"{persona_id}-patient")
    assert out["stored"] is False
    assert out["is_diagnosis"] is False
    suggested = EXPECTED[persona_id] == "consider_referral_for_formal_screening"
    assert (out["draft"] is not None) == suggested
    assert (out["why_no_draft"] is None) == suggested
    if suggested:
        request = out["draft"]
        assert request["intent"] == "proposal"
        assert request["status"] == "draft"
        assert "id" not in request
        assert request["subject"] == {"reference": f"Patient/{persona_id}-patient"}
        ServiceRequest.model_validate(request)


async def test_draft_cites_the_basis(persona_client: Client) -> None:  # type: ignore[type-arg]
    out = await draft(persona_client, "p01-patient")
    assessment = (
        await persona_client.call_tool("assess_referral_need", {"patient_id": "p01-patient"})
    ).structured_content
    assert assessment is not None
    basis = {
        f"{r['resource_type']}/{r['id']}" for b in assessment["basis"] for r in b["references"]
    }
    cited = {
        r["reference"]
        for r in out["draft"].get("reasonReference", []) + out["draft"].get("supportingInfo", [])
    }
    assert cited == basis
    assert all(
        r.startswith(("Condition/", "Observation/"))
        for r in [x["reference"] for x in out["draft"]["reasonReference"]]
    )
