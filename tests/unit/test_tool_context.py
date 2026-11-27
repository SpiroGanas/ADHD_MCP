"""The server builds its tool context from environment variables."""

from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.http_adapter import HttpFhirAdapter
from adhd_mcp.tools.context import context_from_environment
from tests.personas import BUNDLE_DIR


def test_no_data_source_means_no_port() -> None:
    context = context_from_environment({})
    assert context.port is None
    assert context.site_codes.id == "synthetic"


def test_a_base_url_selects_the_http_adapter() -> None:
    context = context_from_environment(
        {"ADHD_MCP_FHIR_BASE_URL": "http://fhir.test/r4", "ADHD_MCP_FIXTURE_DIR": "ignored"}
    )
    assert isinstance(context.port, HttpFhirAdapter)


def test_a_fixture_directory_selects_the_fixture_adapter() -> None:
    context = context_from_environment({"ADHD_MCP_FIXTURE_DIR": str(BUNDLE_DIR)})
    assert isinstance(context.port, FixtureFhirAdapter)
