"""Output schema of ``get_server_info``."""

from pydantic import BaseModel, ConfigDict, Field


class ServerInfo(BaseModel):
    """Identity, versions and intended use of this server."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    server_name: str
    server_version: str
    tool_contract_version: str
    ruleset_version: str | None = Field(
        description="Active referral ruleset: id, version and status (draft until the project "
        "owner approves it). No ruleset is clinically validated."
    )
    intended_use: str = Field(description="The standard intended-use notice.")
