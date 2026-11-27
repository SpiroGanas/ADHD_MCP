"""The ``get_utilization_summary`` tool: a thin wrapper over the utilization assembler."""

from fastmcp import FastMCP

from adhd_mcp.evidence.utilization import assemble_utilization, load_utilization_content
from adhd_mcp.models.evidence_outputs import UtilizationOutput
from adhd_mcp.tools.common import READ_ONLY, AsOfArg, PatientIdArg, output_versions, start_request
from adhd_mcp.tools.context import ToolContext
from adhd_mcp.wording import load_wording

DESCRIPTION = (
    "Summarize a patient's health care use: emergency and urgent care visits, accidental "
    "injury visits (one per visit however many injury codes it carries; visits with a "
    "self-harm code are not counted as accidental), motor-vehicle crashes as driver "
    "(passenger codes do not count), and psychiatric inpatient or residential stays. Counts "
    "each in windows of 0-30, 31-180 and 181-730 days before the as-of date, and reports "
    "overall record volume (all encounters and distinct visit days) so frequent attendance "
    "can be told apart from specific events. Missed appointments are not read yet. "
    "Read-only. A visit in the record is not a diagnosis."
)


def register(mcp: FastMCP, context: ToolContext) -> None:
    async def get_utilization_summary(
        patient_id: PatientIdArg, as_of: AsOfArg = None
    ) -> UtilizationOutput:
        request = await start_request(context, patient_id, as_of)
        result = await assemble_utilization(
            request.records,
            request.patient_id,
            request.as_of,
            load_utilization_content(context.site_codes),
        )
        return UtilizationOutput(
            patient_id=request.patient_id,
            as_of=request.as_of,
            notice=load_wording().evidence_notice,
            data_completeness=result.data_completeness,
            versions=output_versions(context),
            events=result.events,
            counts=result.counts,
            visit_days_730=result.visit_days_730,
            missed_appointments="not_read",
            psychiatric_stays_checked=result.psychiatric_stays_checked,
            definition_version=result.definition_version,
        )

    mcp.tool(get_utilization_summary, description=DESCRIPTION, annotations=READ_ONLY)
