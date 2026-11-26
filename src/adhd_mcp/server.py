"""FastMCP application assembly."""

from fastmcp import FastMCP

from adhd_mcp import versions
from adhd_mcp.tools import server_info

INSTRUCTIONS = (
    "Read-only decision support. Tools read a patient's FHIR record and report evidence "
    "a clinician can check. Results suggest whether to consider referral for formal adult "
    "ADHD screening; they are never a diagnosis."
)


def create_server() -> FastMCP:
    """Build a new server instance with every tool registered."""
    mcp = FastMCP(
        versions.SERVER_NAME,
        instructions=INSTRUCTIONS,
        version=versions.server_version(),
        mask_error_details=True,
    )
    server_info.register(mcp)
    return mcp


def main() -> None:  # pragma: no cover - process entry point
    """Run the server over stdio."""
    create_server().run()
