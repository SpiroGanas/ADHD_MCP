"""The three version lines reported in every output (see docs/architecture.md#versioning)."""

from importlib.metadata import version

SERVER_NAME = "adhd-mcp"

#: Changes when a tool's name, inputs or output schema changes.
TOOL_CONTRACT_VERSION = "0.1.0"

#: No ruleset is active until Phase 5; reported as null until then.
ACTIVE_RULESET_VERSION: str | None = None


def server_version() -> str:
    """The installed package version."""
    return version(SERVER_NAME)
