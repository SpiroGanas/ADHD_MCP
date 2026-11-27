"""The ``assess_referral_need`` tool: a thin wrapper over the orchestration."""

from datetime import date
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from adhd_mcp.models.assessment import AssessmentOutput
from adhd_mcp.models.domain import RecommendationCode
from adhd_mcp.orchestration.assess import Assessment, assess
from adhd_mcp.tools.common import (
    ASSESS_SCOPE,
    READ_ONLY,
    AsOfArg,
    ErrorCode,
    PatientIdArg,
    PatientRequest,
    apply_privacy,
    output_versions,
    privacy_note,
    scope_check,
    start_request,
    tool_error,
)
from adhd_mcp.tools.context import ToolContext
from adhd_mcp.wording import load_wording

DESCRIPTION = (
    "Suggest whether a clinician should consider referring a patient for formal adult ADHD "
    "screening, with the evidence behind it. Runs the safety gate first: if self-harm "
    "signals are found the result is address_safety_gate_first and no screening referral is "
    "suggested. Then checks whether the patient is already in ADHD care, reads diagnoses, "
    "psychosocial codes, visits and medications, and applies the versioned ADHD ruleset "
    "(one high-weight signal with two or more modifiers, or two high-weight signal classes, "
    "within 1095 days). Returns one of consider_referral_for_formal_screening, "
    "no_recommendation, address_safety_gate_first, already_in_care or insufficient_data; the "
    "safety gate; every signal checked with its FHIR resources; each rule and whether it "
    "fired; exclusions; notes; and data completeness. Read-only. The ruleset is a starting "
    "heuristic from published research, not clinically validated. The result is never a "
    "diagnosis; a clinician decides."
)

ConditionArg = Annotated[
    str,
    Field(
        description="Condition to assess: 'adhd'. An experimental stub such as 'autism' only "
        "when the server enables it; stubs are not for clinical use."
    ),
]


def build_output(
    context: ToolContext, request: PatientRequest, condition: str, a: Assessment
) -> AssessmentOutput:
    plugin = context.conditions.get(condition)
    wording = load_wording()
    code = a.recommendation
    notes = list(a.notes)
    next_step = None
    if code is RecommendationCode.CONSIDER_REFERRAL:
        next_step = plugin.next_step
        notes.append(wording.notes["heuristic"])
    elif code is RecommendationCode.ADDRESS_SAFETY_GATE_FIRST:
        next_step = wording.safety_next_step
    versions = output_versions(context).model_copy(
        update={
            "ruleset": plugin.ruleset.label,
            "scorer": f"{a.scorer.id} {a.scorer.version}" if a.scorer else None,
        }
    )
    output = AssessmentOutput(
        safety_gate=a.gate,
        recommendation=code,
        condition_to_screen=plugin.title,
        suggested_next_step=next_step,
        basis=a.basis,
        exclusions_checked=a.exclusions.checks,
        decision_trace=a.decision.rules,
        data_completeness=a.data_completeness,
        versions=versions,
        patient_id=request.patient_id,
        as_of=request.as_of,
        notice=wording.standard_notice,
        recommendation_text=plugin.recommendation_texts[code.value],
        notes=notes,
        excluded=a.exclusions.excluded,
        signals_checked=a.findings,
        ruleset=plugin.ruleset.label,
        privacy=privacy_note(context, request),
        scorer=a.scorer,
    )
    return apply_privacy(request, output)


async def run_assessment(
    context: ToolContext, patient_id: str, as_of: date | None, condition: str
) -> tuple[PatientRequest, Assessment]:
    if condition not in context.conditions.ids():
        raise tool_error(ErrorCode.INVALID_INPUT, f"unknown condition {condition!r}")
    # One request-scoped cache: every assembler reads through it, so no query repeats.
    request = await start_request(context, patient_id, as_of, cached=True)
    plugin = context.conditions.get(condition)
    result = await assess(
        plugin,
        request.records,
        request.gate_records,
        request.patient_id,
        request.as_of,
        site=context.site_codes,
    )
    return request, result


def register(mcp: FastMCP, context: ToolContext) -> None:
    async def assess_referral_need(
        patient_id: PatientIdArg, as_of: AsOfArg = None, condition: ConditionArg = "adhd"
    ) -> AssessmentOutput:
        request, result = await run_assessment(context, patient_id, as_of, condition)
        return build_output(context, request, condition, result)

    mcp.tool(
        assess_referral_need,
        description=DESCRIPTION,
        annotations=READ_ONLY,
        auth=scope_check(context, ASSESS_SCOPE),
    )
