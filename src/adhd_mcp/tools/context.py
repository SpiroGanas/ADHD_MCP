"""What the patient tools need: a FHIR source, a clock and the site's local code mapping.

``context_from_environment`` builds it from environment variables when the server runs as
a process; tests pass a context to ``create_server`` directly.

* ``ADHD_MCP_FHIR_BASE_URL``: a FHIR R4 server (read-only access).
* ``ADHD_MCP_FIXTURE_DIR``: a directory of synthetic FHIR bundles, used if no URL is set.
* ``ADHD_MCP_SITE_CODES``: the site code mapping in ``data/site_codes/`` (default
  ``synthetic``).

With neither data source set, patient tools return a ``not_configured`` error.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from adhd_mcp.clock import Clock, SystemClock
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.http_adapter import HttpFhirAdapter
from adhd_mcp.fhir.port import FhirReadPort
from adhd_mcp.terminology.site_codes import SiteCodes, load_site_codes


@dataclass(frozen=True)
class ToolContext:
    port: FhirReadPort | None
    clock: Clock
    site_codes: SiteCodes


def context_from_environment(env: Mapping[str, str] = os.environ) -> ToolContext:
    port: FhirReadPort | None = None
    if base_url := env.get("ADHD_MCP_FHIR_BASE_URL"):
        port = HttpFhirAdapter(base_url)
    elif fixture_dir := env.get("ADHD_MCP_FIXTURE_DIR"):
        port = FixtureFhirAdapter.from_directory(Path(fixture_dir))
    site = load_site_codes(env.get("ADHD_MCP_SITE_CODES", "synthetic"))
    return ToolContext(port=port, clock=SystemClock(), site_codes=site)
