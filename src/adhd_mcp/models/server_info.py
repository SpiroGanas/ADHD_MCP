"""Output schema of ``get_server_info``."""

from pydantic import BaseModel, ConfigDict, Field


class ServerInfo(BaseModel):
    """Identity, versions and intended use of this server."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    server_name: str
    server_version: str
    tool_contract_version: str
    ruleset_version: str | None = Field(
        description="Version of the active referral ruleset; null until a ruleset is released."
    )
    intended_use: str = Field(description="The standard intended-use notice.")
