"""The ``check_safety_gate`` tool: a thin wrapper over the safety gate assembler."""

from fastmcp import FastMCP

from adhd_mcp.evidence.safety_gate import assess_safety_gate, load_gate_content
from adhd_mcp.models.evidence_outputs import SafetyGateOutput
from adhd_mcp.tools.common import (
    EVIDENCE_SCOPE,
    READ_ONLY,
    AsOfArg,
    PatientIdArg,
    apply_privacy,
    output_versions,
    privacy_note,
    scope_check,
    start_request,
)
from adhd_mcp.tools.context import ToolContext
from adhd_mcp.wording import load_wording

DESCRIPTION = (
    "Check a patient's FHIR record for self-harm signals that must be addressed before any "
    "screening referral: suicidal ideation, suicide attempt and self-harm codes (including "
    "intentional and undetermined-intent poisoning), history of suicidal behavior, PHQ-9 "
    "item 9, C-SSRS risk level, psychiatric inpatient or residential discharge within 365 "
    "days (90 days is highest priority) and active high-risk flags. Call it first, before "
    "any other assessment. Returns positive, clear, clear_limited_data or data_unavailable, "
    "every check with its outcome (found, not found, not performed, failed), and the FHIR "
    "resources behind each signal. A positive result carries fixed guidance on suicide "
    "risk evaluation and lethal-means counseling. Read-only. It reports what the record "
    "contains; it does not assess suicide risk and is not a diagnosis. clear_limited_data "
    "means some checks could not run or the record is empty, so absence of signals is not "
    "reassurance."
)


def register(mcp: FastMCP, context: ToolContext) -> None:
    async def check_safety_gate(
        patient_id: PatientIdArg, as_of: AsOfArg = None
    ) -> SafetyGateOutput:
        request = await start_request(context, patient_id, as_of)
        content = load_gate_content(context.site_codes, strict=True)
        gate, notes = await assess_safety_gate(
            request.gate_records, request.patient_id, request.as_of, content
        )
        output = SafetyGateOutput(
            patient_id=request.patient_id,
            as_of=request.as_of,
            notice=load_wording().evidence_notice,
            data_completeness=notes,
            privacy=privacy_note(context, request),
            versions=output_versions(context),
            safety_gate=gate,
            gate_definition_version=content.definition.version,
        )
        return apply_privacy(request, output)

    mcp.tool(
        check_safety_gate,
        description=DESCRIPTION,
        annotations=READ_ONLY,
        auth=scope_check(context, EVIDENCE_SCOPE),
    )
