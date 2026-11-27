"""The ``get_medication_timeline`` tool: a thin wrapper over the medication assembler."""

from fastmcp import FastMCP

from adhd_mcp.evidence.medication_timeline import (
    assemble_medication_timeline,
    load_medication_content,
)
from adhd_mcp.models.evidence_outputs import MedicationTimelineOutput
from adhd_mcp.tools.common import READ_ONLY, AsOfArg, PatientIdArg, output_versions, start_request
from adhd_mcp.tools.context import ToolContext
from adhd_mcp.wording import load_wording

DESCRIPTION = (
    "Summarize a patient's exposure to the drug classes the referral rules use: stimulant "
    "and non-stimulant ADHD medications, antidepressants and sedative-hypnotics (RxNorm "
    "ingredient classes). Builds exposure periods from dispenses and medication statements "
    "(and from orders only when the record has no dispensing data), merging overlapping "
    "fills and splitting at gaps longer than 30 days; a missing days supply is assumed to be "
    "30 days and flagged. Lists each order with its fill status (filled, not filled, "
    "unknown), the count of distinct agents per class (dose and brand variants count once), "
    "and marks medication ordered for narcolepsy. Medications in no class are counted, not "
    "named. Read-only. A medication in the record is not a diagnosis."
)


def register(mcp: FastMCP, context: ToolContext) -> None:
    async def get_medication_timeline(
        patient_id: PatientIdArg, as_of: AsOfArg = None
    ) -> MedicationTimelineOutput:
        request = await start_request(context, patient_id, as_of)
        result = await assemble_medication_timeline(
            request.records, request.patient_id, request.as_of, load_medication_content()
        )
        return MedicationTimelineOutput(
            patient_id=request.patient_id,
            as_of=request.as_of,
            notice=load_wording().evidence_notice,
            data_completeness=result.data_completeness,
            versions=output_versions(context),
            exposures=result.exposures,
            prescriptions=result.prescriptions,
            distinct_agents=result.distinct_agents,
            unclassified_records=result.unclassified_records,
            classes_checked=result.classes_checked,
            definition_version=result.definition_version,
            drug_class_versions=result.drug_class_versions,
        )

    mcp.tool(get_medication_timeline, description=DESCRIPTION, annotations=READ_ONLY)
