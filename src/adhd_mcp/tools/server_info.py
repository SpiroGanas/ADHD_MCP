"""The ``get_server_info`` tool."""

from fastmcp import FastMCP

from adhd_mcp import versions
from adhd_mcp.models.server_info import ServerInfo
from adhd_mcp.wording import load_wording

DESCRIPTION = (
    "Return this server's name, versions (server, tool contract, active referral ruleset) "
    "and its intended-use notice. Reads no patient data. Use it to check which versions "
    "produced a result. This server suggests when a clinician might consider referral for "
    "formal ADHD screening; it never diagnoses."
)


def get_server_info() -> ServerInfo:
    return ServerInfo(
        server_name=versions.SERVER_NAME,
        server_version=versions.server_version(),
        tool_contract_version=versions.TOOL_CONTRACT_VERSION,
        ruleset_version=versions.ACTIVE_RULESET_VERSION,
        intended_use=load_wording().standard_notice,
    )


def register(mcp: FastMCP) -> None:
    mcp.tool(
        get_server_info,
        description=DESCRIPTION,
        annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False},
    )
