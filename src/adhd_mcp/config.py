"""Server settings from environment variables, validated at startup.

The server refuses to start on missing or malformed settings. Error messages name the
variables involved, never their values, so secrets are never printed. Private keys are read
from files named by a variable, never from the variable itself.

| Variable | Meaning |
|---|---|
| ``ADHD_MCP_TRANSPORT`` | ``stdio`` (default) or ``http`` |
| ``ADHD_MCP_HOST``, ``ADHD_MCP_PORT`` | HTTP bind address (default 127.0.0.1:8000) |
| ``ADHD_MCP_PUBLIC_URL`` | Public base URL of this server (HTTP; for OAuth metadata) |
| ``ADHD_MCP_AUTH_ISSUER`` | Expected token issuer (HTTP) |
| ``ADHD_MCP_AUTH_AUDIENCE`` | Expected token audience: this server's resource URL (HTTP) |
| ``ADHD_MCP_AUTH_JWKS_URI`` or ``ADHD_MCP_AUTH_PUBLIC_KEY_FILE`` | Token signing keys (HTTP) |
| ``ADHD_MCP_AUTH_SERVERS`` | Comma-separated authorization server URLs (default: the issuer) |
| ``ADHD_MCP_ALLOW_UNAUTHENTICATED_HTTP`` | ``1``: HTTP without auth, 127.0.0.1 only |
| ``ADHD_MCP_FHIR_BASE_URL`` / ``ADHD_MCP_FIXTURE_DIR`` | Data source (see ``tools/context.py``) |
| ``ADHD_MCP_FHIR_SERVER_PROFILE`` | ``generic`` (default) or ``lighthouse`` (VA Lighthouse) |
| ``ADHD_MCP_SMART_*`` (``TOKEN_URL``, ``CLIENT_ID``, ``KEY_ID``, ``SCOPE``, |  |
| ``PRIVATE_KEY_FILE``) | SMART backend services toward the FHIR server; all or none |
| ``ADHD_MCP_SMART_AUDIENCE`` | The client assertion's audience (default: the token URL; |
|  | required for ``lighthouse``) |
| ``ADHD_MCP_AUDIT_FILE`` | Append-only JSON Lines audit file; required for HTTP |
| ``ADHD_MCP_PRIVACY_POLICY`` | A site's privacy policy file, or ``packaged`` for the packaged |
|  | policy. Required with a FHIR server that is not on this machine |
| ``ADHD_MCP_ALLOW_PLAIN_HTTP`` | ``1``: allow http (not https) to a FHIR server or public URL |
|  | that is not on this machine, for a private network the site trusts |
| ``ADHD_MCP_SITE_CODES`` | A packaged site code mapping, by name (``synthetic``) |
| ``ADHD_MCP_SITE_CODES_FILE`` | A site's own code mapping file (loaded strictly); not with |
|  | ``ADHD_MCP_SITE_CODES`` |
| ``ADHD_MCP_SCORER`` | ``rules-only`` (default) or ``dummy`` (Phase 8 proof; not a model) |
| ``ADHD_MCP_EXPERIMENTAL_CONDITIONS`` | Experimental stubs to register, comma-separated |
|  | (``autism``); none by default. Not for clinical use |
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import httpx2

from adhd_mcp.fhir.profiles import profile_ids
from adhd_mcp.rules.scorer import SCORERS
from adhd_mcp.terminology.site_codes import packaged_site_code_ids

#: Experimental stub conditions that ``ADHD_MCP_EXPERIMENTAL_CONDITIONS`` can switch on.
EXPERIMENTAL_CONDITIONS = frozenset({"autism"})


class ConfigError(Exception):
    """A setting is missing or malformed. The message names variables, never values."""


@dataclass(frozen=True)
class AuthSettings:
    issuer: str
    audience: str
    public_url: str
    jwks_uri: str | None
    public_key_file: Path | None
    authorization_servers: tuple[str, ...]


@dataclass(frozen=True)
class SmartSettings:
    token_url: str
    client_id: str
    key_id: str
    scope: str
    private_key_file: Path
    audience: str | None = None


@dataclass(frozen=True)
class Settings:
    transport: Literal["stdio", "http"]
    host: str
    port: int
    auth: AuthSettings | None
    smart: SmartSettings | None
    audit_file: Path | None
    privacy_policy: Path | None
    scorer: str = "rules-only"
    fhir_server_profile: str = "generic"
    experimental_conditions: tuple[str, ...] = ()
    fhir_base_url: str | None = None
    site_codes: str | None = None
    site_codes_file: Path | None = None


_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def _host(value: str) -> str | None:
    try:
        return httpx2.URL(value).host or None
    except Exception:
        return None


def is_local(value: str) -> bool:
    """Whether a URL names this machine."""
    return _host(value) in _LOCAL_HOSTS


def _url(env: Mapping[str, str], name: str, *, https: bool = False) -> str:
    value = env.get(name, "")
    try:
        url = httpx2.URL(value)
    except Exception as exc:
        raise ConfigError(f"{name} is not a valid URL") from exc
    if url.scheme not in {"http", "https"} or not url.host:
        raise ConfigError(f"{name} must be an absolute http(s) URL")
    if https and url.scheme != "https" and url.host not in _LOCAL_HOSTS:
        raise ConfigError(f"{name} must use https")
    return value


def _plain_http_allowed(env: Mapping[str, str]) -> bool:
    return env.get("ADHD_MCP_ALLOW_PLAIN_HTTP") == "1"


def _privacy_policy(env: Mapping[str, str], base_url: str | None) -> Path | None:
    """A site's policy file, or None for the packaged one. A FHIR server that is not on this
    machine needs an explicit choice (peer review 01, P2: "cite" names the protected
    category beside each reference, which may not be what a site wants)."""
    value = env.get("ADHD_MCP_PRIVACY_POLICY", "")
    if value == "packaged":
        return None
    if value:
        return _file(env, "ADHD_MCP_PRIVACY_POLICY")
    if base_url is not None and not is_local(base_url):
        raise ConfigError(
            "a FHIR server that is not on this machine needs ADHD_MCP_PRIVACY_POLICY: a site "
            "policy file, or 'packaged' to accept the packaged policy (see the configuration "
            "guide for what it does and does not hide)"
        )
    return None


def _file(env: Mapping[str, str], name: str) -> Path:
    path = Path(env[name])
    if not path.is_file():
        raise ConfigError(f"{name} does not name a readable file")
    return path


def _auth(env: Mapping[str, str]) -> AuthSettings:
    missing = [
        n
        for n in ("ADHD_MCP_PUBLIC_URL", "ADHD_MCP_AUTH_ISSUER", "ADHD_MCP_AUTH_AUDIENCE")
        if not env.get(n)
    ]
    if missing:
        raise ConfigError(f"HTTP transport needs authentication settings: {', '.join(missing)}")
    has_jwks = bool(env.get("ADHD_MCP_AUTH_JWKS_URI"))
    has_key = bool(env.get("ADHD_MCP_AUTH_PUBLIC_KEY_FILE"))
    if has_jwks == has_key:
        raise ConfigError(
            "set exactly one of ADHD_MCP_AUTH_JWKS_URI and ADHD_MCP_AUTH_PUBLIC_KEY_FILE"
        )
    issuer = _url(env, "ADHD_MCP_AUTH_ISSUER", https=True)
    servers = tuple(
        s.strip() for s in env.get("ADHD_MCP_AUTH_SERVERS", issuer).split(",") if s.strip()
    )
    for server in servers:
        _url({"ADHD_MCP_AUTH_SERVERS": server}, "ADHD_MCP_AUTH_SERVERS", https=True)
    return AuthSettings(
        issuer=issuer,
        audience=env["ADHD_MCP_AUTH_AUDIENCE"],
        public_url=_url(env, "ADHD_MCP_PUBLIC_URL", https=not _plain_http_allowed(env)),
        jwks_uri=_url(env, "ADHD_MCP_AUTH_JWKS_URI", https=True) if has_jwks else None,
        public_key_file=_file(env, "ADHD_MCP_AUTH_PUBLIC_KEY_FILE") if has_key else None,
        authorization_servers=servers,
    )


_SMART = (
    "ADHD_MCP_SMART_TOKEN_URL",
    "ADHD_MCP_SMART_CLIENT_ID",
    "ADHD_MCP_SMART_KEY_ID",
    "ADHD_MCP_SMART_SCOPE",
    "ADHD_MCP_SMART_PRIVATE_KEY_FILE",
)


def _smart(env: Mapping[str, str]) -> SmartSettings | None:
    present = [n for n in _SMART if env.get(n)]
    if not present:
        return None
    if len(present) != len(_SMART):
        missing = [n for n in _SMART if n not in present]
        raise ConfigError(f"SMART backend settings are incomplete: {', '.join(missing)}")
    if not env.get("ADHD_MCP_FHIR_BASE_URL"):
        raise ConfigError("SMART settings need ADHD_MCP_FHIR_BASE_URL")
    return SmartSettings(
        token_url=_url(env, "ADHD_MCP_SMART_TOKEN_URL", https=True),
        client_id=env["ADHD_MCP_SMART_CLIENT_ID"],
        key_id=env["ADHD_MCP_SMART_KEY_ID"],
        scope=env["ADHD_MCP_SMART_SCOPE"],
        private_key_file=_file(env, "ADHD_MCP_SMART_PRIVATE_KEY_FILE"),
        audience=_url(env, "ADHD_MCP_SMART_AUDIENCE", https=True)
        if env.get("ADHD_MCP_SMART_AUDIENCE")
        else None,
    )


def _profile(env: Mapping[str, str], smart: SmartSettings | None) -> str:
    profile = env.get("ADHD_MCP_FHIR_SERVER_PROFILE", "generic")
    if profile not in profile_ids():
        raise ConfigError(
            f"ADHD_MCP_FHIR_SERVER_PROFILE must be one of: {', '.join(profile_ids())}"
        )
    if profile != "generic" and not env.get("ADHD_MCP_FHIR_BASE_URL"):
        raise ConfigError("ADHD_MCP_FHIR_SERVER_PROFILE needs ADHD_MCP_FHIR_BASE_URL")
    if profile == "lighthouse" and smart is not None and smart.audience is None:
        raise ConfigError("the lighthouse profile with credentials needs ADHD_MCP_SMART_AUDIENCE")
    return profile


def _site_codes(env: Mapping[str, str]) -> tuple[str | None, Path | None]:
    name = env.get("ADHD_MCP_SITE_CODES") or None
    path = _file(env, "ADHD_MCP_SITE_CODES_FILE") if env.get("ADHD_MCP_SITE_CODES_FILE") else None
    if name is not None and path is not None:
        raise ConfigError("set at most one of ADHD_MCP_SITE_CODES and ADHD_MCP_SITE_CODES_FILE")
    if name is not None and name not in packaged_site_code_ids():
        raise ConfigError(
            "ADHD_MCP_SITE_CODES must name a packaged site code mapping: "
            + ", ".join(packaged_site_code_ids())
            + " (use ADHD_MCP_SITE_CODES_FILE for a site's own file)"
        )
    return name, path


def load_settings(env: Mapping[str, str]) -> Settings:
    transport = env.get("ADHD_MCP_TRANSPORT", "stdio")
    if transport not in {"stdio", "http"}:
        raise ConfigError("ADHD_MCP_TRANSPORT must be stdio or http")
    host = env.get("ADHD_MCP_HOST", "127.0.0.1")
    try:
        port = int(env.get("ADHD_MCP_PORT", "8000"))
    except ValueError as exc:
        raise ConfigError("ADHD_MCP_PORT must be a number") from exc
    if not 1 <= port <= 65535:
        raise ConfigError("ADHD_MCP_PORT must be between 1 and 65535")
    auth = None
    audit = Path(env["ADHD_MCP_AUDIT_FILE"]) if env.get("ADHD_MCP_AUDIT_FILE") else None
    if audit is not None and not audit.parent.is_dir():
        raise ConfigError("ADHD_MCP_AUDIT_FILE must be in an existing directory")
    if transport == "http":
        unauthenticated = env.get("ADHD_MCP_ALLOW_UNAUTHENTICATED_HTTP") == "1"
        if unauthenticated:
            if host != "127.0.0.1":
                raise ConfigError(
                    "ADHD_MCP_ALLOW_UNAUTHENTICATED_HTTP needs ADHD_MCP_HOST=127.0.0.1"
                )
        else:
            auth = _auth(env)
        if audit is None:
            raise ConfigError("HTTP transport needs ADHD_MCP_AUDIT_FILE")
    scorer = env.get("ADHD_MCP_SCORER", "rules-only")
    if scorer not in SCORERS:
        raise ConfigError(f"ADHD_MCP_SCORER must be one of: {', '.join(SCORERS)}")
    experimental = tuple(
        c.strip() for c in env.get("ADHD_MCP_EXPERIMENTAL_CONDITIONS", "").split(",") if c.strip()
    )
    if not set(experimental) <= EXPERIMENTAL_CONDITIONS:
        raise ConfigError(
            "ADHD_MCP_EXPERIMENTAL_CONDITIONS may name only: "
            + ", ".join(sorted(EXPERIMENTAL_CONDITIONS))
        )
    smart = _smart(env)
    base_url = (
        _url(env, "ADHD_MCP_FHIR_BASE_URL", https=not _plain_http_allowed(env))
        if env.get("ADHD_MCP_FHIR_BASE_URL")
        else None
    )
    policy = _privacy_policy(env, base_url)
    site_codes, site_codes_file = _site_codes(env)
    return Settings(
        transport=transport,  # type: ignore[arg-type]
        host=host,
        port=port,
        auth=auth,
        smart=smart,
        fhir_server_profile=_profile(env, smart),
        audit_file=audit,
        privacy_policy=policy,
        scorer=scorer,
        experimental_conditions=experimental,
        fhir_base_url=base_url,
        site_codes=site_codes,
        site_codes_file=site_codes_file,
    )
