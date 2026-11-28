"""FastMCP application assembly."""

import os
import sys
from dataclasses import replace

from fastmcp import FastMCP
from fastmcp.server.auth import AuthProvider, RemoteAuthProvider
from fastmcp.server.auth.providers.jwt import JWTVerifier
from pydantic import AnyHttpUrl

from adhd_mcp import prompts, resources, versions
from adhd_mcp.audit.middleware import AuditMiddleware
from adhd_mcp.config import AuthSettings, ConfigError, load_settings
from adhd_mcp.tools import (
    assessment,
    draft_referral,
    existing_care,
    medication_timeline,
    problem_list,
    psychosocial,
    safety_gate,
    screening,
    server_info,
    utilization,
)
from adhd_mcp.tools.common import SCOPES, TOOL_NAMES
from adhd_mcp.tools.context import ToolContext, context_from_environment

INSTRUCTIONS = (
    "Read-only decision support. Tools read a patient's FHIR record and report evidence "
    "a clinician can check. Results suggest whether to consider referral for formal adult "
    "ADHD screening; they are never a diagnosis."
)


def build_auth(settings: AuthSettings) -> RemoteAuthProvider:
    """OAuth 2.1 resource server: JWT validation (issuer, audience, expiry, signature) and
    protected resource metadata (RFC 9728) naming the authorization servers."""
    verifier = JWTVerifier(
        public_key=settings.public_key_file.read_text(encoding="utf-8")
        if settings.public_key_file
        else None,
        jwks_uri=settings.jwks_uri,
        issuer=settings.issuer,
        audience=settings.audience,
        algorithm="RS256",
    )
    return RemoteAuthProvider(
        token_verifier=verifier,
        authorization_servers=[AnyHttpUrl(a) for a in settings.authorization_servers],
        base_url=settings.public_url,
        scopes_supported=list(SCOPES),
        resource_name=versions.SERVER_NAME,
    )


def create_server(context: ToolContext | None = None, auth: AuthProvider | None = None) -> FastMCP:
    """Build a new server instance with every tool registered.

    ``context`` supplies the FHIR source, clock, site codes, privacy policy and audit sink;
    by default it is read from the environment (see ``adhd_mcp.tools.context``). With
    ``auth`` (HTTP transport) callers must present a valid token and each tool its scope.
    """
    context = context or context_from_environment()
    if auth is not None and not context.scopes_required:
        context = replace(context, scopes_required=True)
    mcp = FastMCP(
        versions.SERVER_NAME,
        instructions=INSTRUCTIONS,
        version=versions.server_version(),
        mask_error_details=True,
        auth=auth,
    )
    if context.audit_sink is not None:
        mcp.add_middleware(AuditMiddleware(context.audit_sink, context.clock, TOOL_NAMES))
    server_info.register(mcp)
    safety_gate.register(mcp, context)
    problem_list.register(mcp, context)
    screening.register(mcp, context)
    existing_care.register(mcp, context)
    medication_timeline.register(mcp, context)
    utilization.register(mcp, context)
    psychosocial.register(mcp, context)
    assessment.register(mcp, context)
    draft_referral.register(mcp, context)
    resources.register(mcp, context)
    prompts.register(mcp)
    return mcp


def main() -> None:  # pragma: no cover - process entry point
    """Run the server over stdio or HTTP, as configured. Refuses to start on bad settings."""
    try:
        settings = load_settings(os.environ)
        context = context_from_environment(os.environ, settings=settings)
    except ConfigError as exc:
        print(f"adhd-mcp: configuration error: {exc}", file=sys.stderr)  # noqa: T201
        raise SystemExit(2) from None
    auth = build_auth(settings.auth) if settings.auth else None
    server = create_server(context, auth=auth)
    if settings.transport == "http":
        server.run(transport="http", host=settings.host, port=settings.port)
    else:
        server.run()
