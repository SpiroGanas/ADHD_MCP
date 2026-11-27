"""The ``get_mh_problem_list`` tool: a thin wrapper over the problem list assembler."""

from fastmcp import FastMCP

from adhd_mcp.evidence.problem_list import assemble_problem_list, load_problem_list_content
from adhd_mcp.models.evidence_outputs import ProblemListOutput
from adhd_mcp.tools.common import READ_ONLY, AsOfArg, PatientIdArg, output_versions, start_request
from adhd_mcp.tools.context import ToolContext
from adhd_mcp.wording import load_wording

DESCRIPTION = (
    "List the mental health and related codes in a patient's FHIR Condition resources "
    "(ICD-10-CM), grouped into the families the referral rules use: ADHD codes, attention "
    "symptoms, depression, anxiety, PTSD, personality, substance use, sleep, narcolepsy, "
    "head injury, family history, and other chapter 5 codes. Each entry gives the code, "
    "first onset and recorded dates, the clinical status of its latest record (resolved "
    "entries are kept and labelled), an onset order, and every Condition it was found in; "
    "codes repeated across encounters appear once. Read-only. Use it to see what has been "
    "coded and in what order. A code listed here is a record entry, not a diagnosis made "
    "by this tool. Self-harm codes are reported by check_safety_gate."
)


def register(mcp: FastMCP, context: ToolContext) -> None:
    async def get_mh_problem_list(
        patient_id: PatientIdArg, as_of: AsOfArg = None
    ) -> ProblemListOutput:
        request = await start_request(context, patient_id, as_of)
        result = await assemble_problem_list(
            request.records, request.patient_id, request.as_of, load_problem_list_content()
        )
        return ProblemListOutput(
            patient_id=request.patient_id,
            as_of=request.as_of,
            notice=load_wording().evidence_notice,
            data_completeness=result.data_completeness,
            versions=output_versions(context),
            families=result.families,
            families_checked=result.families_checked,
            definition_version=result.definition_version,
        )

    mcp.tool(get_mh_problem_list, description=DESCRIPTION, annotations=READ_ONLY)
