"""The ``get_screening_history`` tool: a thin wrapper over the screening history assembler."""

from fastmcp import FastMCP

from adhd_mcp.evidence.screening import assemble_screening_history, load_screening_content
from adhd_mcp.models.evidence_outputs import ScreeningHistoryOutput
from adhd_mcp.tools.common import READ_ONLY, AsOfArg, PatientIdArg, output_versions, start_request
from adhd_mcp.tools.context import ToolContext
from adhd_mcp.wording import load_wording

DESCRIPTION = (
    "Return a timeline of screening instrument results in a patient's FHIR record (PHQ-9, "
    "PHQ-2, C-SSRS risk level, AUDIT-C, PC-PTSD-5, ASRS-5 where coded), read from "
    "Observation panels, standalone results and QuestionnaireResponses. Each entry gives "
    "the date, score or coded answer, the cutoff that applies (sex-specific where the "
    "instrument has one) and whether it was applied, and the resource it came from. "
    "Unknown survey instruments are listed but not scored. A cutoff is applied only when "
    "its code and value are verified; code_verified and cutoff.status say so. Read-only. "
    "A score meeting a cutoff is a screening result for a clinician to review, not a "
    "diagnosis. No instrument item text is returned."
)


def register(mcp: FastMCP, context: ToolContext) -> None:
    async def get_screening_history(
        patient_id: PatientIdArg, as_of: AsOfArg = None
    ) -> ScreeningHistoryOutput:
        request = await start_request(context, patient_id, as_of)
        result = await assemble_screening_history(
            request.records,
            request.patient,
            request.as_of,
            load_screening_content(context.site_codes),
        )
        return ScreeningHistoryOutput(
            patient_id=request.patient_id,
            as_of=request.as_of,
            notice=load_wording().evidence_notice,
            data_completeness=result.data_completeness,
            versions=output_versions(context),
            entries=result.entries,
            instruments_checked=result.instruments_checked,
        )

    mcp.tool(get_screening_history, description=DESCRIPTION, annotations=READ_ONLY)
