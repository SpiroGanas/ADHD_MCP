"""Integration fixtures: a local FHIR server loaded once with every persona."""

import os

import pytest
from scripts.load_personas import load

FHIR_URL = os.environ.get("ADHD_MCP_TEST_FHIR_URL", "http://localhost:8080/fhir")


@pytest.fixture(scope="session")
def loaded_server() -> str:
    load(FHIR_URL)
    return FHIR_URL
