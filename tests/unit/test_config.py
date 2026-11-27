"""Startup configuration: missing or malformed settings are refused, and no message ever
contains a setting's value (secrets are never printed)."""

from pathlib import Path

import pytest

from adhd_mcp.config import ConfigError, load_settings
from adhd_mcp.fhir.http_adapter import HttpFhirAdapter
from adhd_mcp.fhir.lighthouse import LighthouseCcgAuth
from adhd_mcp.tools.context import context_from_environment

SECRET = "s3cr3t-value-never-printed"


@pytest.fixture
def files(tmp_path: Path) -> dict[str, str]:
    key = tmp_path / "key.pem"
    key.write_text("-----BEGIN PUBLIC KEY-----\nAAAA\n-----END PUBLIC KEY-----\n")
    return {"key": str(key), "audit": str(tmp_path / "audit.jsonl")}


def http_env(files: dict[str, str]) -> dict[str, str]:
    return {
        "ADHD_MCP_TRANSPORT": "http",
        "ADHD_MCP_PUBLIC_URL": "https://adhd-mcp.example.test",
        "ADHD_MCP_AUTH_ISSUER": "https://auth.example.test",
        "ADHD_MCP_AUTH_AUDIENCE": "https://adhd-mcp.example.test/mcp",
        "ADHD_MCP_AUTH_PUBLIC_KEY_FILE": files["key"],
        "ADHD_MCP_AUDIT_FILE": files["audit"],
    }


def test_defaults_are_stdio_without_auth() -> None:
    settings = load_settings({})
    assert (settings.transport, settings.auth, settings.smart, settings.audit_file) == (
        "stdio",
        None,
        None,
        None,
    )


def test_a_complete_http_configuration_loads(files: dict[str, str]) -> None:
    settings = load_settings(http_env(files))
    assert settings.auth is not None
    assert settings.auth.authorization_servers == ("https://auth.example.test",)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"ADHD_MCP_TRANSPORT": "carrier-pigeon"}, "ADHD_MCP_TRANSPORT"),
        ({"ADHD_MCP_PORT": "eighty"}, "ADHD_MCP_PORT"),
        ({"ADHD_MCP_PORT": "70000"}, "ADHD_MCP_PORT"),
        ({"ADHD_MCP_AUTH_ISSUER": ""}, "ADHD_MCP_AUTH_ISSUER"),
        ({"ADHD_MCP_AUTH_ISSUER": "http://auth.example.test"}, "must use https"),
        ({"ADHD_MCP_AUTH_AUDIENCE": ""}, "ADHD_MCP_AUTH_AUDIENCE"),
        (
            {"ADHD_MCP_AUTH_PUBLIC_KEY_FILE": "/nonexistent/key.pem"},
            "ADHD_MCP_AUTH_PUBLIC_KEY_FILE",
        ),
        ({"ADHD_MCP_AUTH_JWKS_URI": "https://auth.example.test/jwks"}, "exactly one"),
        ({"ADHD_MCP_AUDIT_FILE": ""}, "ADHD_MCP_AUDIT_FILE"),
        ({"ADHD_MCP_AUDIT_FILE": "/nonexistent/dir/audit.jsonl"}, "existing directory"),
        ({"ADHD_MCP_PUBLIC_URL": "not a url"}, "ADHD_MCP_PUBLIC_URL"),
    ],
)
def test_bad_http_settings_are_refused(
    files: dict[str, str], change: dict[str, str], message: str
) -> None:
    with pytest.raises(ConfigError, match=message):
        load_settings(http_env(files) | change)


def test_unauthenticated_http_is_only_for_localhost(files: dict[str, str]) -> None:
    env = {"ADHD_MCP_TRANSPORT": "http", "ADHD_MCP_AUDIT_FILE": files["audit"]}
    env["ADHD_MCP_ALLOW_UNAUTHENTICATED_HTTP"] = "1"
    assert load_settings(env).auth is None
    with pytest.raises(ConfigError, match=r"127\.0\.0\.1"):
        load_settings(env | {"ADHD_MCP_HOST": "0.0.0.0"})  # noqa: S104


def test_incomplete_smart_settings_are_refused_without_printing_values(
    files: dict[str, str],
) -> None:
    env = {
        "ADHD_MCP_FHIR_BASE_URL": "https://fhir.example.test/r4",
        "ADHD_MCP_SMART_CLIENT_ID": SECRET,
        "ADHD_MCP_SMART_SCOPE": SECRET,
    }
    with pytest.raises(ConfigError) as caught:
        load_settings(env)
    assert "ADHD_MCP_SMART_TOKEN_URL" in str(caught.value)
    assert SECRET not in str(caught.value)


def test_no_error_message_contains_a_setting_value(files: dict[str, str]) -> None:
    bad = {
        "ADHD_MCP_AUTH_ISSUER": f"http://{SECRET}.example.test",
        "ADHD_MCP_PUBLIC_URL": f"not a url {SECRET}",
    }
    for name, value in bad.items():
        with pytest.raises(ConfigError) as caught:
            load_settings(http_env(files) | {name: value})
        assert SECRET not in str(caught.value)


def test_smart_settings_build_an_authenticated_fhir_adapter(tmp_path: Path) -> None:
    key = tmp_path / "smart.pem"
    key.write_text("unused until a token is requested")
    env = {
        "ADHD_MCP_FHIR_BASE_URL": "https://fhir.example.test/r4",
        "ADHD_MCP_SMART_TOKEN_URL": "https://auth.example.test/token",
        "ADHD_MCP_SMART_CLIENT_ID": "adhd-mcp",
        "ADHD_MCP_SMART_KEY_ID": "k1",
        "ADHD_MCP_SMART_SCOPE": "system/*.rs",
        "ADHD_MCP_SMART_PRIVATE_KEY_FILE": str(key),
    }
    context = context_from_environment(env)
    assert context.port is not None
    assert context.port._auth is not None  # type: ignore[attr-defined]


def test_the_scorer_defaults_to_rules_only() -> None:
    assert load_settings({}).scorer == "rules-only"
    assert load_settings({"ADHD_MCP_SCORER": "dummy"}).scorer == "dummy"


def test_an_unknown_scorer_is_refused_without_echoing_it() -> None:
    with pytest.raises(ConfigError, match="ADHD_MCP_SCORER") as raised:
        load_settings({"ADHD_MCP_SCORER": SECRET})
    assert SECRET not in str(raised.value)


def lighthouse_env(key: Path) -> dict[str, str]:
    key.write_text("unused until a token is requested")
    return {
        "ADHD_MCP_FHIR_BASE_URL": "https://sandbox.lighthouse.test/services/fhir/v0/r4",
        "ADHD_MCP_FHIR_SERVER_PROFILE": "lighthouse",
        "ADHD_MCP_SMART_TOKEN_URL": "https://sandbox.lighthouse.test/oauth2/health/system/v1/token",
        "ADHD_MCP_SMART_AUDIENCE": "https://okta.lighthouse.test/oauth2/aus-test/v1/token",
        "ADHD_MCP_SMART_CLIENT_ID": "adhd-mcp",
        "ADHD_MCP_SMART_KEY_ID": "k1",
        "ADHD_MCP_SMART_SCOPE": "launch system/Patient.read",
        "ADHD_MCP_SMART_PRIVATE_KEY_FILE": str(key),
    }


def test_the_server_profile_defaults_to_generic() -> None:
    assert load_settings({}).fhir_server_profile == "generic"


def test_the_lighthouse_profile_builds_the_lighthouse_adapter_and_grant(tmp_path: Path) -> None:
    env = lighthouse_env(tmp_path / "key.pem")
    settings = load_settings(env)
    assert settings.fhir_server_profile == "lighthouse"
    assert settings.smart is not None
    assert settings.smart.audience == env["ADHD_MCP_SMART_AUDIENCE"]
    context = context_from_environment(env)
    assert isinstance(context.port, HttpFhirAdapter)
    assert context.port._profile.id == "lighthouse"
    assert isinstance(context.port._auth, LighthouseCcgAuth)
    assert context.site_codes.id == "none"


def test_lighthouse_with_credentials_needs_the_assertion_audience(tmp_path: Path) -> None:
    env = lighthouse_env(tmp_path / "key.pem")
    del env["ADHD_MCP_SMART_AUDIENCE"]
    with pytest.raises(ConfigError, match="ADHD_MCP_SMART_AUDIENCE"):
        load_settings(env)


@pytest.mark.parametrize(
    "env",
    [
        {"ADHD_MCP_FHIR_SERVER_PROFILE": SECRET},
        {"ADHD_MCP_FHIR_SERVER_PROFILE": "lighthouse"},
    ],
)
def test_a_bad_server_profile_is_refused_without_echoing_it(env: dict[str, str]) -> None:
    with pytest.raises(ConfigError, match="ADHD_MCP_FHIR_SERVER_PROFILE") as raised:
        load_settings(env)
    assert SECRET not in str(raised.value)
