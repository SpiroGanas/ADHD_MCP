"""The audit record and its sinks."""

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from adhd_mcp.models.domain import ResourceRef


class AuditRecord(BaseModel):
    """One tool call. References and hashes only: no clinical values, no free text."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    record_id: str
    trace_id: str
    time: datetime
    caller: str = Field(description="Token subject and client id, or 'local' over stdio")
    tool: str
    outcome: Literal["success", "error"]
    error_code: str | None = None
    server_version: str
    tool_contract_version: str
    ruleset: str | None
    scorer: str | None = None
    privacy_policy: str | None = None
    patient: ResourceRef | None
    resources_read: list[ResourceRef] = Field(
        description="Every resource read; empty when there were more than the listing limit"
    )
    resources_read_count: int = Field(default=0, description="How many resources were read")
    resources_read_sha256: str | None = Field(
        default=None,
        description="When the list was too long to keep: sha256 of the sorted references, one "
        "'Type/id/version' per line",
    )
    recommendation: str | None = None
    output_sha256: str | None = None


class AuditSink(Protocol):
    def write(self, record: AuditRecord) -> None: ...


class MemoryAuditSink:
    """Keeps records in memory (tests)."""

    def __init__(self) -> None:
        self.records: list[AuditRecord] = []

    def write(self, record: AuditRecord) -> None:
        self.records.append(record)


class JsonlAuditSink:
    """Appends one JSON line per record to a file. Never rewrites or truncates it."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def write(self, record: AuditRecord) -> None:
        line = json.dumps(record.model_dump(mode="json"), sort_keys=True) + "\n"
        with self._lock:
            # Created readable by its owner only: it links patients to outcomes (peer review
            # 01, P5). An existing file keeps the mode it has.
            fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            with os.fdopen(fd, "a", encoding="utf-8") as f:
                f.write(line)
