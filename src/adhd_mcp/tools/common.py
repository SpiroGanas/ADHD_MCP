"""Behaviour every patient tool shares: arguments, validation and one error shape.

Errors are returned as MCP tool errors whose text starts with a fixed code:

* ``invalid_input``: a malformed patient id, or an as-of date in the future;
* ``patient_not_found``: the FHIR server has no such Patient;
* ``fhir_unavailable``: the FHIR server could not be reached or answered with an error;
* ``not_configured``: the server has no FHIR data source.

A data category that fails to load after the Patient was read is not an error: the output
reports it as ``failed`` in its data-completeness note, distinct from ``empty``.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Annotated, Any

from fastmcp.exceptions import ToolError
from fastmcp.server.auth import AuthCheck, require_scopes
from pydantic import BaseModel, Field

from adhd_mcp import versions
from adhd_mcp.audit.middleware import AuditingPort
from adhd_mcp.fhir.errors import FhirRequestError, ResourceNotFoundError
from adhd_mcp.fhir.port import FhirReadPort, validate_patient_id
from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.fhir.records import PatientRecord
from adhd_mcp.fhir.request_cache import RequestCachedPort
from adhd_mcp.models.domain import PrivacyNote, Versions
from adhd_mcp.privacy import PrivacyLedger, PrivacyPort, redact_output
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

#: Every tool this server registers (a contract test keeps the list in step with the server).
TOOL_NAMES = frozenset(
    {
        "get_server_info",
        "check_safety_gate",
        "get_mh_problem_list",
        "get_screening_history",
        "check_existing_care",
        "get_medication_timeline",
        "get_utilization_summary",
        "get_psychosocial_context",
        "assess_referral_need",
        "draft_referral_proposal",
    }
)

#: OAuth scopes (Phase 6). Evidence tools need the first; tools that produce a recommendation
#: or a draft referral need the second.
EVIDENCE_SCOPE = "adhd.evidence.read"
ASSESS_SCOPE = "adhd.referral.assess"
SCOPES = (EVIDENCE_SCOPE, ASSESS_SCOPE)


def scope_check(context: "ToolContext", scope: str) -> AuthCheck | None:
    """The tool's scope requirement, when callers authenticate; none over stdio."""
    return require_scopes(scope) if context.scopes_required else None


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
    #: Unfiltered reads for the safety gate only (see ``request_ports``).
    gate_records: PatientRecords
    ledger: PrivacyLedger = field(default_factory=PrivacyLedger)


def request_ports(
    context: ToolContext, ledger: PrivacyLedger, *, cached: bool = False
) -> tuple[FhirReadPort, FhirReadPort]:
    """The ports one request reads through: (evidence, safety gate).

    Both start from the source, audited, then (for multi-assembler tools) a request-scoped
    cache, so no query repeats. Evidence then passes through the privacy policy. The safety
    gate does not: a self-harm signal must never be hidden from it by a withhold policy,
    and its output carries only signal names and references, never codes.
    """
    assert context.port is not None  # noqa: S101 - checked by start_request
    base: FhirReadPort = AuditingPort(context.port)
    if cached:
        base = RequestCachedPort(base)
    return PrivacyPort(base, context.privacy, ledger), base


async def start_request(
    context: ToolContext, patient_id: str, as_of: date | None, *, cached: bool = False
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
    ledger = PrivacyLedger()
    evidence_port, gate_port = request_ports(context, ledger, cached=cached)
    records = PatientRecords(evidence_port)
    try:
        patient = await records.patient(patient_id)
    except ResourceNotFoundError as exc:
        raise tool_error(ErrorCode.PATIENT_NOT_FOUND, f"no Patient {patient_id}") from exc
    except FhirRequestError as exc:
        raise tool_error(ErrorCode.FHIR_UNAVAILABLE, "the FHIR server could not be read") from exc
    return PatientRequest(
        patient_id=patient_id,
        as_of=as_of,
        patient=patient,
        records=records,
        gate_records=PatientRecords(gate_port),
        ledger=ledger,
    )


def privacy_note(context: ToolContext, request: PatientRequest) -> PrivacyNote:
    return request.ledger.note(context.privacy)


def apply_privacy[M: BaseModel](request: PatientRequest, output: M) -> M:
    """Replace codes resting on restricted resources (policy "cite") with "restricted"."""
    ledger = request.ledger
    if not ledger.restricted_refs and not ledger.withheld_types:
        return output
    data: Any = redact_output(output.model_dump(mode="json"), ledger.restricted_refs)
    # A category that lost records to a withhold policy is reported as withheld, never as
    # complete (an empty or partial record must not look clean).
    for note in data.get("data_completeness") or []:
        if note["category"] in ledger.withheld_types and note["status"] in {"available", "empty"}:
            note["status"] = "withheld"
    return type(output).model_validate(data)


def output_versions(context: ToolContext) -> Versions:
    return Versions(
        server=versions.server_version(),
        tool_contract=versions.TOOL_CONTRACT_VERSION,
        ruleset=versions.ACTIVE_RULESET_VERSION,
        site_codes=f"{context.site_codes.id} {context.site_codes.version}",
    )
