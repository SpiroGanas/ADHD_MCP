# ADR 0012: Authentication toward MCP clients and toward the FHIR server

- **Status:** Accepted
- **Date:** 2026-11-27
- **Decided by:** project owner (PyJWT and cryptography as direct dependencies, 2026-11-27); design by the Claude Code agent

## Context

Hosted over HTTP the server is an OAuth 2.1 protected resource: it must validate bearer tokens (signature, issuer, audience, expiry), publish protected resource metadata (RFC 9728) and enforce scopes. Toward the FHIR server it must use its own SMART on FHIR backend-services credentials and never forward a caller's token. The MCP authorization specification could not be read directly from this environment; FastMCP 4.2's implementation (which follows it) was read in the installed source instead.

## Decision

- **MCP side**: FastMCP's `RemoteAuthProvider` with a `JWTVerifier` (RS256; a public key file or a JWKS URI; issuer and audience required). It serves `/.well-known/oauth-protected-resource/mcp` and returns 401 with a `WWW-Authenticate` header naming that metadata. Scopes: `adhd.evidence.read` for evidence tools, `adhd.referral.assess` for `assess_referral_need` and `draft_referral_proposal`, enforced per tool with `require_scopes`. Over stdio there is no token and no scope check.
- **FHIR side**: `SmartBackendAuth` signs a client assertion (RS384 or ES384, `kid` header, five-minute lifetime) with PyJWT, posts it to the token URL with the client-credentials grant, caches the token until a minute before expiry and renews once after a 401. This POST to the token endpoint is the only non-GET request in the code base and is allowlisted by name in the read-only guard.
- **Configuration** (`adhd_mcp/config.py`): validated at startup. HTTP requires authentication settings and an audit file, unless explicitly run unauthenticated on 127.0.0.1. Error messages name variables, never values; keys are read from files.

## Alternatives considered

| Option | Why not |
|---|---|
| Token passthrough to the FHIR server | Confused-deputy risk; forbidden by the plan and the MCP specification |
| FastMCP's full OAuth server (`OAuthProvider`) | The server should not issue tokens; the health system's authorization server does |
| Hand-written JWT validation | FastMCP's verifier is maintained and already handles key rotation (JWKS) |

## Consequences

- Deployments must register the server with their authorization server (audience = public MCP URL) and with the FHIR server as a backend service.
- Scope names are part of the tool contract and are listed in the protected resource metadata.
- The read-only guard has one documented exception, which a test keeps from silently growing.
