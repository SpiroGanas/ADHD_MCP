"""Writes exactly one audit record per tool call, successful or not."""

import hashlib
import json
import re
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, get_args

from fastmcp.exceptions import NotFoundError
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools import ToolResult
from mcp_types import CallToolRequestParams

from adhd_mcp import versions
from adhd_mcp.audit.records import AuditRecord, AuditSink
from adhd_mcp.audit.trace import current_trace_id, new_trace_id, trace_id_from
from adhd_mcp.clock import Clock
from adhd_mcp.fhir.port import (
    FhirReadPort,
    RawResource,
    SearchResult,
    SearchType,
    validate_patient_id,
)
from adhd_mcp.fhir.search import Codes
from adhd_mcp.models.domain import ResourceRef, ResourceType

_KNOWN_TYPES = frozenset(get_args(ResourceType))
_ERROR_CODE = re.compile(r"^([a-z_]{3,40}):")


#: Above this many resources an audit record holds their count and a hash, not the list
#: (peer review 01, D1: one long record can mean tens of thousands of references).
MAX_LISTED_RESOURCES = 500


@dataclass
class CallAudit:
    """Resources read during one tool call, collected by ``AuditingPort``."""

    refs: dict[tuple[str, str], str | None] = field(default_factory=dict)

    def add(self, raw: RawResource) -> None:
        kind, rid = raw.get("resourceType"), raw.get("id")
        if isinstance(kind, str) and kind in _KNOWN_TYPES and isinstance(rid, str) and rid:
            version = (raw.get("meta") or {}).get("versionId")
            self.refs[(kind, rid)] = version if isinstance(version, str) else None

    def resources(self) -> list[ResourceRef]:
        return [
            ResourceRef(resource_type=k, id=i, version=v) for (k, i), v in sorted(self.refs.items())
        ]

    def resource_summary(self) -> tuple[list[ResourceRef], int, str | None]:
        """(the list, its count, None), or for a long list ([], its count, the sha256 of the
        sorted references, one ``Type/id/version`` per line)."""
        refs = self.resources()
        if len(refs) <= MAX_LISTED_RESOURCES:
            return refs, len(refs), None
        lines = "\n".join(f"{r.resource_type}/{r.id}/{r.version or ''}" for r in refs)
        return [], len(refs), hashlib.sha256(lines.encode("utf-8")).hexdigest()

    def record_fields(self) -> dict[str, Any]:
        listed, count, digest = self.resource_summary()
        return {
            "resources_read": listed,
            "resources_read_count": count,
            "resources_read_sha256": digest,
        }


current_audit: ContextVar[CallAudit | None] = ContextVar("current_audit", default=None)


class AuditingPort:
    """Notes every resource the FHIR source returns into the current call's audit."""

    def __init__(self, inner: FhirReadPort) -> None:
        self._inner = inner

    async def read_patient(self, patient_id: str) -> RawResource:
        raw = await self._inner.read_patient(patient_id)
        if (audit := current_audit.get()) is not None:
            audit.add(raw)
        return raw

    async def search(
        self,
        resource_type: SearchType,
        patient_id: str,
        *,
        since: date | None = None,
        updated_since: datetime | None = None,
        categories: tuple[str, ...] = (),
        codes: Codes = (),
    ) -> SearchResult:
        found = await self._inner.search(
            resource_type,
            patient_id,
            since=since,
            updated_since=updated_since,
            categories=categories,
            codes=codes,
        )
        if (audit := current_audit.get()) is not None:
            for raw in found.resources:
                audit.add(raw)
        return found


def _caller() -> str:
    token = get_access_token()
    if token is None:
        return "local"
    sub = token.claims.get("sub") if token.claims else None
    return f"sub={sub} client={token.client_id}"


def _traceparent(context: MiddlewareContext[CallToolRequestParams]) -> object:
    """The request's ``_meta.traceparent`` (the MCP SDK carries W3C trace context there)."""
    meta: Any = context.message.meta
    if meta is None and context.fastmcp_context is not None:
        request = context.fastmcp_context.request_context
        meta = getattr(request, "meta", None) if request is not None else None
    return meta.get("traceparent") if isinstance(meta, dict) else None


def _patient(arguments: dict[str, Any] | None) -> ResourceRef | None:
    pid = (arguments or {}).get("patient_id")
    try:
        validate_patient_id(pid)  # type: ignore[arg-type]
    except ValueError:
        return None  # an invalid id is never written to the audit trail
    return ResourceRef(resource_type="Patient", id=pid)


def output_hash(structured: Any) -> str:
    canonical = json.dumps(structured, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _error_code(exc: Exception, tool: str, known_tools: frozenset[str]) -> str:
    """The audited error code. FastMCP answers "Unknown tool" both for a tool that does not
    exist and for one the caller's token lacks the scope for; the two are told apart here
    (peer review 01, P4: a refusal was audited as an internal error)."""
    if isinstance(exc, NotFoundError):
        return "not_authorized" if tool in known_tools else "unknown_tool"
    match = _ERROR_CODE.match(str(exc))
    return match[1] if match else "internal_error"


class AuditMiddleware(Middleware):
    def __init__(
        self, sink: AuditSink, clock: Clock, known_tools: frozenset[str] = frozenset()
    ) -> None:
        self.sink = sink
        self.clock = clock
        self.known_tools = known_tools

    async def on_call_tool(
        self,
        context: MiddlewareContext[CallToolRequestParams],
        call_next: CallNext[CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        params = context.message
        trace_id = trace_id_from(_traceparent(context)) or new_trace_id()
        audit = CallAudit()
        audit_token = current_audit.set(audit)
        trace_token = current_trace_id.set(trace_id)
        base: dict[str, Any] = {
            "record_id": str(uuid.uuid4()),
            "trace_id": trace_id,
            "time": self.clock.now(),
            "caller": _caller(),
            "tool": params.name,
            "server_version": versions.server_version(),
            "tool_contract_version": versions.TOOL_CONTRACT_VERSION,
            "ruleset": versions.ACTIVE_RULESET_VERSION,
            "patient": _patient(params.arguments),
        }
        try:
            result = await call_next(context)
        except Exception as exc:
            self.sink.write(
                AuditRecord(
                    **base,
                    outcome="error",
                    error_code=_error_code(exc, params.name, self.known_tools),
                    **audit.record_fields(),
                )
            )
            raise
        finally:
            current_audit.reset(audit_token)
            current_trace_id.reset(trace_token)
        structured = result.structured_content or {}
        found_versions = structured.get("versions") or {}
        privacy = structured.get("privacy") or {}
        self.sink.write(
            AuditRecord(
                **base | {"ruleset": found_versions.get("ruleset", base["ruleset"])},
                outcome="success",
                scorer=found_versions.get("scorer"),
                privacy_policy=privacy.get("policy"),
                **audit.record_fields(),
                recommendation=structured.get("recommendation"),
                output_sha256=output_hash(structured),
            )
        )
        return result
