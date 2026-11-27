"""The ``draft_referral_proposal`` tool: a draft referral, returned only and stored nowhere.

The draft is a FHIR R4 ServiceRequest with status ``draft`` and intent ``proposal``. It has
no id and is never sent to a FHIR server: a clinician reviews it and places any real order
in their own system.
"""

from typing import Any

from fastmcp import FastMCP

from adhd_mcp.models.assessment import ReferralDraftOutput
from adhd_mcp.models.domain import RecommendationCode, ResourceRef
from adhd_mcp.orchestration.assess import Assessment
from adhd_mcp.privacy import PrivacyPolicy
from adhd_mcp.tools.assessment import ConditionArg, run_assessment
from adhd_mcp.tools.common import (
    ASSESS_SCOPE,
    READ_ONLY,
    AsOfArg,
    PatientIdArg,
    privacy_note,
    scope_check,
)
from adhd_mcp.tools.context import ToolContext
from adhd_mcp.wording import load_wording

DESCRIPTION = (
    "Draft a referral for formal adult ADHD screening from an assessment, for a clinician "
    "to review. Runs assess_referral_need; only when it suggests a referral, returns a FHIR "
    "R4 ServiceRequest with status 'draft' and intent 'proposal' that cites the evidence "
    "(reasonReference for conditions and observations, supportingInfo for visits and "
    "medications). Otherwise the draft is null and the reason is given. The draft is "
    "returned only: it has no id, is never stored and is never sent to the health record. "
    "Not a diagnosis and not an order."
)

#: ServiceRequest.reasonReference may point only to these resource types (FHIR R4).
_REASON_TYPES = frozenset({"Condition", "Observation"})
DRAFT_TAG = {"system": "urn:adhd-mcp:draft", "code": "unsaved-draft"}


def _reference(ref: ResourceRef) -> dict[str, str]:
    return {"reference": f"{ref.resource_type}/{ref.id}"}


def build_draft(
    patient_id: str,
    condition_title: str,
    ruleset: str,
    a: Assessment,
    policy: PrivacyPolicy,
) -> dict[str, Any]:
    refs = sorted(
        {r for item in a.basis for r in item.references}, key=lambda r: (r.resource_type, r.id)
    )
    present = [f for f in a.findings if f.present and f.weight != "note"]
    # Signals from a protected category are cited by reference only: their titles would
    # name the category in free text a clinician may paste into an order.
    shown = [
        f.title for f in present if f.protected is None or policy.action(f.protected) == "allow"
    ]
    hidden = len(present) - len(shown)
    titles = ", ".join(shown) if shown else "protected signals only"
    if shown and hidden:
        titles += f"; and {hidden} protected signal(s) cited by reference only"
    draft: dict[str, Any] = {
        "resourceType": "ServiceRequest",
        "meta": {"tag": [DRAFT_TAG]},
        "status": "draft",
        "intent": "proposal",
        "code": {"text": f"Referral for formal adult {condition_title} screening"},
        "subject": {"reference": f"Patient/{patient_id}"},
        "note": [
            {"text": load_wording().standard_notice},
            {"text": f"Suggested by ruleset {ruleset} from: {titles}."},
        ],
    }
    reasons = [_reference(r) for r in refs if r.resource_type in _REASON_TYPES]
    supporting = [_reference(r) for r in refs if r.resource_type not in _REASON_TYPES]
    if reasons:
        draft["reasonReference"] = reasons
    if supporting:
        draft["supportingInfo"] = supporting
    return draft


def register(mcp: FastMCP, context: ToolContext) -> None:
    async def draft_referral_proposal(
        patient_id: PatientIdArg, as_of: AsOfArg = None, condition: ConditionArg = "adhd"
    ) -> ReferralDraftOutput:
        request, result = await run_assessment(context, patient_id, as_of, condition)
        plugin = context.conditions.get(condition)
        wording = load_wording()
        draft = None
        why = None
        if result.recommendation is RecommendationCode.CONSIDER_REFERRAL:
            draft = build_draft(
                request.patient_id, plugin.title, plugin.ruleset.label, result, context.privacy
            )
        else:
            why = (
                f"The assessment result is {result.recommendation.value}: "
                f"{plugin.recommendation_texts[result.recommendation.value]}"
            )
        return ReferralDraftOutput(
            patient_id=request.patient_id,
            as_of=request.as_of,
            recommendation=result.recommendation.value,
            draft=draft,
            why_no_draft=why,
            privacy=privacy_note(context, request),
            notice=wording.standard_notice,
        )

    mcp.tool(
        draft_referral_proposal,
        description=DESCRIPTION,
        annotations=READ_ONLY,
        auth=scope_check(context, ASSESS_SCOPE),
    )
