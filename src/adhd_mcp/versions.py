"""The three version lines reported in every output (see docs/architecture.md#versioning)."""

from importlib.metadata import version

SERVER_NAME = "adhd-mcp"

#: Changes when a tool's name, inputs or output schema changes.
TOOL_CONTRACT_VERSION = "0.5.0"

#: The active referral ruleset: id, version and status. "draft" until the project owner
#: approves it for release (a test keeps this equal to the loaded ruleset).
ACTIVE_RULESET_VERSION: str | None = "adhd 1.0.0 (draft)"


def server_version() -> str:
    """The installed package version."""
    return version(SERVER_NAME)
