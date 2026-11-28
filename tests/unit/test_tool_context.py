"""The server builds its tool context from environment variables."""

from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.http_adapter import HttpFhirAdapter
from adhd_mcp.tools.context import context_from_environment
from tests.personas import BUNDLE_DIR


def test_no_data_source_means_no_port() -> None:
    context = context_from_environment({})
    assert context.port is None
    assert context.site_codes.id == "synthetic"


def test_a_base_url_selects_the_http_adapter_with_no_local_codes_by_default() -> None:
    context = context_from_environment(
        {
            "ADHD_MCP_FHIR_BASE_URL": "https://fhir.test/r4",
            "ADHD_MCP_PRIVACY_POLICY": "packaged",
            "ADHD_MCP_FIXTURE_DIR": "ignored",
        }
    )
    assert isinstance(context.port, HttpFhirAdapter)
    assert context.site_codes.id == "none"
    assert not context.site_codes.maps("high_risk_flag")


def test_a_site_mapping_can_be_named_for_a_server() -> None:
    context = context_from_environment(
        {
            "ADHD_MCP_FHIR_BASE_URL": "https://fhir.test/r4",
            "ADHD_MCP_PRIVACY_POLICY": "packaged",
            "ADHD_MCP_SITE_CODES": "synthetic",
        }
    )
    assert context.site_codes.id == "synthetic"


def test_a_fixture_directory_selects_the_fixture_adapter() -> None:
    context = context_from_environment({"ADHD_MCP_FIXTURE_DIR": str(BUNDLE_DIR)})
    assert isinstance(context.port, FixtureFhirAdapter)
    assert context.site_codes.id == "synthetic"


def test_the_rules_only_scorer_is_the_default() -> None:
    plugin = context_from_environment({}).conditions.get("adhd")
    assert plugin.scorer is not None
    assert plugin.scorer.id == "rules-only"


def test_the_dummy_scorer_can_be_switched_on() -> None:
    plugin = context_from_environment({"ADHD_MCP_SCORER": "dummy"}).conditions.get("adhd")
    assert plugin.scorer is not None
    assert plugin.scorer.id == "dummy-not-a-model"
