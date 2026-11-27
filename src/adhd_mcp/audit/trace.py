"""W3C trace context, carried from the MCP request (``_meta.traceparent``) to FHIR calls."""

import re
import secrets
from contextvars import ContextVar

_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")

#: The trace id of the tool call being served, if any.
current_trace_id: ContextVar[str | None] = ContextVar("current_trace_id", default=None)


def trace_id_from(traceparent: object) -> str | None:
    """The trace id of a valid ``traceparent``; ``None`` for anything else."""
    if not isinstance(traceparent, str):
        return None
    match = _TRACEPARENT.match(traceparent.strip())
    if match is None or match[1] == "0" * 32 or match[2] == "0" * 16:
        return None
    return match[1]


def new_trace_id() -> str:
    return secrets.token_hex(16)


def outgoing_traceparent() -> str | None:
    """A ``traceparent`` for an outgoing FHIR request: the current trace id with a new
    span id. ``None`` outside a traced call."""
    trace_id = current_trace_id.get()
    if trace_id is None:
        return None
    return f"00-{trace_id}-{secrets.token_hex(8)}-01"
