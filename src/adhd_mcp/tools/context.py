"""What the patient tools need: a FHIR source, a clock and the site's local code mapping.

``context_from_environment`` builds it from environment variables when the server runs as
a process; tests pass a context to ``create_server`` directly.

* ``ADHD_MCP_FHIR_BASE_URL``: a FHIR R4 server (read-only access).
* ``ADHD_MCP_FIXTURE_DIR``: a directory of synthetic FHIR bundles, used if no URL is set.
* ``ADHD_MCP_SITE_CODES``: the site code mapping in ``data/site_codes/``. Defaults to
  ``synthetic`` for fixture data, and to no mapping at all for a FHIR server, so checks that
  need local codes report "not performed" rather than silently finding nothing.

With neither data source set, patient tools return a ``not_configured`` error.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from adhd_mcp.audit.records import AuditSink, JsonlAuditSink
from adhd_mcp.clock import Clock, SystemClock
from adhd_mcp.conditions.adhd import adhd_plugin
from adhd_mcp.conditions.base import ConditionRegistry
from adhd_mcp.config import SmartSettings, load_settings
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.http_adapter import HttpFhirAdapter
from adhd_mcp.fhir.port import FhirReadPort
from adhd_mcp.fhir.smart import SmartBackendAuth
from adhd_mcp.privacy import PrivacyPolicy, load_privacy_policy
from adhd_mcp.terminology.site_codes import SiteCodes, load_site_codes

#: Used for a FHIR server whose local codes have not been mapped.
NO_SITE_CODES = SiteCodes(id="none", version="0", title="No local code mapping")


def default_conditions() -> ConditionRegistry:
    """The conditions this server assesses: ADHD only in version 1.0."""
    registry = ConditionRegistry()
    registry.register(adhd_plugin())
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


def _smart(settings: SmartSettings | None, clock: Clock) -> SmartBackendAuth | None:
    if settings is None:
        return None
    return SmartBackendAuth(
        token_url=settings.token_url,
        client_id=settings.client_id,
        private_key_pem=settings.private_key_file.read_text(encoding="utf-8"),
        key_id=settings.key_id,
        scope=settings.scope,
        clock=clock,
    )


def context_from_environment(env: Mapping[str, str] = os.environ) -> ToolContext:
    """Build the context from validated settings (``adhd_mcp.config``); raises
    ``ConfigError`` on a missing or malformed setting."""
    settings = load_settings(env)
    clock = SystemClock()
    port: FhirReadPort | None = None
    site = load_site_codes("synthetic")
    if base_url := env.get("ADHD_MCP_FHIR_BASE_URL"):
        port = HttpFhirAdapter(base_url, auth=_smart(settings.smart, clock))
        site = NO_SITE_CODES
    elif fixture_dir := env.get("ADHD_MCP_FIXTURE_DIR"):
        port = FixtureFhirAdapter.from_directory(Path(fixture_dir))
    if site_id := env.get("ADHD_MCP_SITE_CODES"):
        site = load_site_codes(site_id)
    return ToolContext(
        port=port,
        clock=clock,
        site_codes=site,
        privacy=load_privacy_policy(settings.privacy_policy),
        audit_sink=JsonlAuditSink(settings.audit_file) if settings.audit_file else None,
        scopes_required=settings.auth is not None,
    )
