"""FastMCP application assembly."""

from fastmcp import FastMCP

from adhd_mcp import versions
from adhd_mcp.tools import problem_list, safety_gate, screening, server_info
from adhd_mcp.tools.context import ToolContext, context_from_environment

INSTRUCTIONS = (
    "Read-only decision support. Tools read a patient's FHIR record and report evidence "
    "a clinician can check. Results suggest whether to consider referral for formal adult "
    "ADHD screening; they are never a diagnosis."
)


def create_server(context: ToolContext | None = None) -> FastMCP:
    """Build a new server instance with every tool registered.

    ``context`` supplies the FHIR source, clock and site codes; by default it is read from
    the environment (see ``adhd_mcp.tools.context``).
    """
    context = context or context_from_environment()
    mcp = FastMCP(
        versions.SERVER_NAME,
        instructions=INSTRUCTIONS,
        version=versions.server_version(),
        mask_error_details=True,
    )
    server_info.register(mcp)
    safety_gate.register(mcp, context)
    problem_list.register(mcp, context)
    screening.register(mcp, context)
    return mcp


def main() -> None:  # pragma: no cover - process entry point
    """Run the server over stdio."""
    create_server().run()
