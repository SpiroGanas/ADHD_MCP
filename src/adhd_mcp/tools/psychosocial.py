"""The ``get_psychosocial_context`` tool: a thin wrapper over the psychosocial assembler."""

from fastmcp import FastMCP

from adhd_mcp.evidence.psychosocial import assemble_psychosocial, load_psychosocial_content
from adhd_mcp.models.evidence_outputs import PsychosocialOutput
from adhd_mcp.tools.common import READ_ONLY, AsOfArg, PatientIdArg, output_versions, start_request
from adhd_mcp.tools.context import ToolContext
from adhd_mcp.wording import load_wording

DESCRIPTION = (
    "Report a patient's psychosocial context from coded data: homelessness or housing "
    "instability (Z59.0, Z59.81), legal problems (Z65.0-Z65.3), and education or "
    "employment problems (Z55, Z56), from Condition codes and coded social-history "
    "Observation values; and the date of separation from military service where the site "
    "records it. Each domain is found, not_found, or unknown when data could not be read; "
    "a missing separation date is unknown, never assumed. Coded data under-records these "
    "problems, so not_found is weak evidence of absence. Read-only. Not a diagnosis."
)


def register(mcp: FastMCP, context: ToolContext) -> None:
    async def get_psychosocial_context(
        patient_id: PatientIdArg, as_of: AsOfArg = None
    ) -> PsychosocialOutput:
        request = await start_request(context, patient_id, as_of)
        result = await assemble_psychosocial(
            request.records,
            request.patient_id,
            request.as_of,
            load_psychosocial_content(context.site_codes),
        )
        return PsychosocialOutput(
            patient_id=request.patient_id,
            as_of=request.as_of,
            notice=load_wording().evidence_notice,
            data_completeness=result.data_completeness,
            versions=output_versions(context),
            domains=result.domains,
            military=result.military,
            definition_version=result.definition_version,
        )

    mcp.tool(get_psychosocial_context, description=DESCRIPTION, annotations=READ_ONLY)
