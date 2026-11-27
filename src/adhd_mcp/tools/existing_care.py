"""The ``check_existing_care`` tool: a thin wrapper over the existing care assembler."""

from fastmcp import FastMCP

from adhd_mcp.evidence.existing_care import assemble_existing_care, load_existing_care_content
from adhd_mcp.models.evidence_outputs import ExistingCareOutput
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
    "Check whether a patient is already in ADHD care, so a referral is not duplicated: an "
    "ADHD code (F90) on a Condition or as a medication reason; an ADHD referral, "
    "evaluation or care plan that is open or was completed within 365 days. Older, revoked "
    "or cancelled items are listed but do not count. Medication ordered for narcolepsy is "
    "reported separately and is never an exclusion. Returns excluded (true; false only when "
    "every check ran on complete data; otherwise null, meaning unknown), each check with "
    "its outcome and resources, and the care items found. Read-only. An ADHD code in the "
    "record is a prior entry, not a diagnosis by this tool."
)


def register(mcp: FastMCP, context: ToolContext) -> None:
    async def check_existing_care(
        patient_id: PatientIdArg, as_of: AsOfArg = None
    ) -> ExistingCareOutput:
        request = await start_request(context, patient_id, as_of)
        result = await assemble_existing_care(
            request.records,
            request.patient_id,
            request.as_of,
            load_existing_care_content(context.site_codes),
        )
        output = ExistingCareOutput(
            patient_id=request.patient_id,
            as_of=request.as_of,
            notice=load_wording().evidence_notice,
            data_completeness=result.data_completeness,
            privacy=privacy_note(context, request),
            versions=output_versions(context),
            excluded=result.excluded,
            exclusions_checked=result.exclusions_checked,
            care_items=result.care_items,
            narcolepsy=result.narcolepsy,
            definition_version=result.definition_version,
        )
        return apply_privacy(request, output)

    mcp.tool(
        check_existing_care,
        description=DESCRIPTION,
        annotations=READ_ONLY,
        auth=scope_check(context, EVIDENCE_SCOPE),
    )
