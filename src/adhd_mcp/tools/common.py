"""Behaviour every patient tool shares: arguments, validation and one error shape.

Errors are returned as MCP tool errors whose text starts with a fixed code:

* ``invalid_input``: a malformed patient id, or an as-of date in the future;
* ``patient_not_found``: the FHIR server has no such Patient;
* ``fhir_unavailable``: the FHIR server could not be reached or answered with an error;
* ``not_configured``: the server has no FHIR data source.

A data category that fails to load after the Patient was read is not an error: the output
reports it as ``failed`` in its data-completeness note, distinct from ``empty``.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Annotated

from fastmcp.exceptions import ToolError
from pydantic import Field

from adhd_mcp import versions
from adhd_mcp.fhir.errors import FhirRequestError, ResourceNotFoundError
from adhd_mcp.fhir.port import validate_patient_id
from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.fhir.records import PatientRecord
from adhd_mcp.models.domain import Versions
from adhd_mcp.tools.context import ToolContext

PatientIdArg = Annotated[
    str,
    Field(description="FHIR id of the Patient resource: 1 to 64 letters, digits, '-' or '.'"),
]
AsOfArg = Annotated[
    date | None,
    Field(
        description="Read the record as of this date (YYYY-MM-DD); data dated later is "
        "ignored. Defaults to today. Must not be in the future."
    ),
]

#: Tool annotations shared by every tool: read-only, idempotent, reads a closed source.
READ_ONLY = {"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False}


class ErrorCode(StrEnum):
    INVALID_INPUT = "invalid_input"
    PATIENT_NOT_FOUND = "patient_not_found"
    FHIR_UNAVAILABLE = "fhir_unavailable"
    NOT_CONFIGURED = "not_configured"


def tool_error(code: ErrorCode, message: str) -> ToolError:
    return ToolError(f"{code}: {message}")


@dataclass(frozen=True)
class PatientRequest:
    patient_id: str
    as_of: date
    patient: PatientRecord
    records: PatientRecords


async def start_request(
    context: ToolContext, patient_id: str, as_of: date | None
) -> PatientRequest:
    """Validate the arguments and read the Patient, or raise a tool error."""
    if context.port is None:
        raise tool_error(ErrorCode.NOT_CONFIGURED, "this server has no FHIR data source")
    try:
        validate_patient_id(patient_id)
    except ValueError as exc:
        raise tool_error(ErrorCode.INVALID_INPUT, str(exc)) from exc
    today = context.clock.today()
    as_of = as_of or today
    if as_of > today:
        raise tool_error(ErrorCode.INVALID_INPUT, "as_of must not be in the future")
    records = PatientRecords(context.port)
    try:
        patient = await records.patient(patient_id)
    except ResourceNotFoundError as exc:
        raise tool_error(ErrorCode.PATIENT_NOT_FOUND, f"no Patient {patient_id}") from exc
    except FhirRequestError as exc:
        raise tool_error(ErrorCode.FHIR_UNAVAILABLE, "the FHIR server could not be read") from exc
    return PatientRequest(patient_id=patient_id, as_of=as_of, patient=patient, records=records)


def output_versions() -> Versions:
    return Versions(
        server=versions.server_version(),
        tool_contract=versions.TOOL_CONTRACT_VERSION,
        ruleset=versions.ACTIVE_RULESET_VERSION,
    )
