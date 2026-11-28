"""What the patient tools need: a FHIR source, a clock and the site's local code mapping.

``context_from_environment`` builds it from environment variables when the server runs as
a process; tests pass a context to ``create_server`` directly.

* ``ADHD_MCP_FHIR_BASE_URL``: a FHIR R4 server (read-only access), described by the profile
  ``ADHD_MCP_FHIR_SERVER_PROFILE`` (``generic`` or ``lighthouse``).
* ``ADHD_MCP_FIXTURE_DIR``: a directory of synthetic FHIR bundles, used if no URL is set.
* ``ADHD_MCP_SITE_CODES``: a site code mapping in ``data/site_codes/``, by name, or
  ``ADHD_MCP_SITE_CODES_FILE``: a site's own mapping file, loaded strictly. Defaults to
  ``synthetic`` for fixture data, and to no mapping at all for a FHIR server, so checks that
  need local codes report "not performed" rather than silently finding nothing.

With neither data source set, patient tools return a ``not_configured`` error.
"""

import dataclasses
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from adhd_mcp.audit.records import AuditSink, JsonlAuditSink
from adhd_mcp.clock import Clock, SystemClock
from adhd_mcp.conditions.adhd import adhd_plugin
from adhd_mcp.conditions.autism import autism_plugin
from adhd_mcp.conditions.base import ConditionRegistry
from adhd_mcp.config import ConfigError, Settings, SmartSettings, load_settings
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.http_adapter import HttpFhirAdapter
from adhd_mcp.fhir.lighthouse import LighthouseCcgAuth
from adhd_mcp.fhir.port import FhirReadPort
from adhd_mcp.fhir.profiles import load_server_profile
from adhd_mcp.fhir.smart import FhirAuth, SmartBackendAuth
from adhd_mcp.privacy import PrivacyPolicy, load_privacy_policy
from adhd_mcp.rules.scorer import SCORERS
from adhd_mcp.terminology.site_codes import SiteCodes, load_site_codes, load_site_codes_file

#: Used for a FHIR server whose local codes have not been mapped.
NO_SITE_CODES = SiteCodes(id="none", version="0", title="No local code mapping")


def default_conditions(
    *, scorer: str = "rules-only", experimental: Sequence[str] = ()
) -> ConditionRegistry:
    """The conditions this server assesses: ADHD, plus any experimental stub named in
    ``experimental`` (none by default; not for clinical use). ``scorer`` names an entry of
    ``SCORERS``; the default leaves the ADHD plugin as it is."""
    registry = ConditionRegistry()
    plugin = adhd_plugin()
    if scorer != "rules-only":
        plugin = dataclasses.replace(plugin, scorer=SCORERS[scorer]())
    registry.register(plugin)
    stubs = {"autism": autism_plugin}
    for condition_id in experimental:
        registry.register(stubs[condition_id]())
    return registry


@dataclass(frozen=True)
class ToolContext:
    port: FhirReadPort | None
    clock: Clock
    site_codes: SiteCodes
    conditions: ConditionRegistry = field(default_factory=default_conditions)
    privacy: PrivacyPolicy = field(default_factory=load_privacy_policy)
    audit_sink: AuditSink | None = None
    #: True when callers authenticate (HTTP): each tool then requires its OAuth scope.
    scopes_required: bool = False


def _smart(settings: SmartSettings | None, clock: Clock, profile: str) -> FhirAuth | None:
    if settings is None:
        return None
    kind = LighthouseCcgAuth if profile == "lighthouse" else SmartBackendAuth
    if kind is LighthouseCcgAuth and settings.audience is None:
        raise ConfigError("the lighthouse profile with credentials needs ADHD_MCP_SMART_AUDIENCE")
    return kind(
        token_url=settings.token_url,
        audience=settings.audience,
        client_id=settings.client_id,
        private_key_pem=settings.private_key_file.read_text(encoding="utf-8"),
        key_id=settings.key_id,
        scope=settings.scope,
        clock=clock,
    )


def _site(settings: Settings, default: SiteCodes) -> SiteCodes:
    try:
        if settings.site_codes_file is not None:
            return load_site_codes_file(settings.site_codes_file, strict=True)
        if settings.site_codes is not None:
            return load_site_codes(settings.site_codes)
    except Exception as exc:  # a malformed or unverified file: never a traceback at start-up
        name = "ADHD_MCP_SITE_CODES_FILE" if settings.site_codes_file else "ADHD_MCP_SITE_CODES"
        raise ConfigError(f"{name} could not be loaded: {type(exc).__name__}") from None
    return default


def context_from_environment(
    env: Mapping[str, str] = os.environ, *, settings: Settings | None = None
) -> ToolContext:
    """Build the context from validated settings (``adhd_mcp.config``), loading them from
    ``env`` unless given; raises ``ConfigError`` on a missing or malformed setting."""
    settings = settings or load_settings(env)
    clock = SystemClock()
    port: FhirReadPort | None = None
    site = load_site_codes("synthetic")
    if settings.fhir_base_url is not None:
        profile = settings.fhir_server_profile
        try:
            port = HttpFhirAdapter(
                settings.fhir_base_url,
                auth=_smart(settings.smart, clock, profile),
                profile=load_server_profile(profile),
            )
        except ValueError as exc:
            raise ConfigError(f"ADHD_MCP_FHIR_BASE_URL is not usable: {exc}") from None
        site = NO_SITE_CODES
    elif fixture_dir := env.get("ADHD_MCP_FIXTURE_DIR"):
        port = FixtureFhirAdapter.from_directory(Path(fixture_dir))
    site = _site(settings, site)
    return ToolContext(
        port=port,
        clock=clock,
        site_codes=site,
        conditions=default_conditions(
            scorer=settings.scorer, experimental=settings.experimental_conditions
        ),
        privacy=load_privacy_policy(settings.privacy_policy),
        audit_sink=JsonlAuditSink(settings.audit_file) if settings.audit_file else None,
        scopes_required=settings.auth is not None,
    )
