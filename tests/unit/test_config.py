"""Startup configuration: missing or malformed settings are refused, and no message ever
contains a setting's value (secrets are never printed)."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from adhd_mcp.audit.records import AuditRecord, JsonlAuditSink
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
        "ADHD_MCP_PRIVACY_POLICY": "packaged",
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
        "ADHD_MCP_PRIVACY_POLICY": "packaged",
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


# --- peer review 01, D4: every start-up error is a configuration error ----------------


@pytest.mark.parametrize("url", ["ftp://x", "not a url", "http://"])
def test_a_bad_fhir_base_url_is_a_configuration_error(url: str) -> None:
    # E11: a ValueError from the adapter escaped as a traceback.
    with pytest.raises(ConfigError, match="ADHD_MCP_FHIR_BASE_URL") as raised:
        context_from_environment({"ADHD_MCP_FHIR_BASE_URL": url})
    assert url not in str(raised.value) or url == "http://"


@pytest.mark.parametrize("name", ["../privacy", "no-such-site", "synthetic.toml", ""])
def test_site_codes_must_name_a_packaged_mapping(name: str) -> None:
    # E12: "../privacy" loaded data/privacy.toml and failed with a validation traceback.
    env = {"ADHD_MCP_FIXTURE_DIR": "tests/personas/bundles", "ADHD_MCP_SITE_CODES": name}
    if not name:
        assert context_from_environment(env).site_codes.id == "synthetic"
        return
    with pytest.raises(ConfigError, match="ADHD_MCP_SITE_CODES"):
        load_settings(env)


def test_a_site_can_supply_its_own_site_codes_file(tmp_path: Path) -> None:
    # Peer review 01, S2: there was no supported way to give a site's own mapping.
    path = tmp_path / "local_site.toml"
    path.write_text('id = "local_site"\nversion = "1"\ntitle = "A site"\n')
    context = context_from_environment(
        {"ADHD_MCP_FIXTURE_DIR": "tests/personas/bundles", "ADHD_MCP_SITE_CODES_FILE": str(path)}
    )
    assert context.site_codes.id == "local_site"


def test_a_site_codes_file_must_exist_and_load_strictly(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="ADHD_MCP_SITE_CODES_FILE"):
        load_settings({"ADHD_MCP_SITE_CODES_FILE": str(tmp_path / "missing.toml")})
    bad = tmp_path / "bad.toml"
    bad.write_text('id = "other"\nversion = "1"\ntitle = "x"\n')
    with pytest.raises(ConfigError, match="ADHD_MCP_SITE_CODES_FILE"):
        context_from_environment({"ADHD_MCP_SITE_CODES_FILE": str(bad)})


def test_site_codes_by_name_and_by_file_are_exclusive(tmp_path: Path) -> None:
    path = tmp_path / "local_site.toml"
    path.write_text('id = "local_site"\nversion = "1"\ntitle = "A site"\n')
    with pytest.raises(ConfigError, match="ADHD_MCP_SITE_CODES"):
        load_settings({"ADHD_MCP_SITE_CODES": "synthetic", "ADHD_MCP_SITE_CODES_FILE": str(path)})


def test_the_context_can_reuse_settings_already_loaded() -> None:
    env = {"ADHD_MCP_FIXTURE_DIR": "tests/personas/bundles", "ADHD_MCP_SCORER": "dummy"}
    settings = load_settings(env)
    plugin = context_from_environment(env, settings=settings).conditions.get("adhd")
    assert plugin.scorer is not None
    assert plugin.scorer.id == "dummy-not-a-model"


# --- peer review 01, P2 and P5: settings for a real FHIR server -------------------------


@pytest.mark.parametrize(
    "url", ["http://ehr.internal.example/fhir", "http://10.0.0.5/fhir", "http://fhir:8080/fhir"]
)
def test_plain_http_to_a_non_local_fhir_server_is_refused(url: str) -> None:
    # E13: accepted silently.
    env = {"ADHD_MCP_FHIR_BASE_URL": url, "ADHD_MCP_PRIVACY_POLICY": "packaged"}
    with pytest.raises(ConfigError, match="ADHD_MCP_FHIR_BASE_URL must use https"):
        load_settings(env)
    allowed = load_settings(env | {"ADHD_MCP_ALLOW_PLAIN_HTTP": "1"})
    assert allowed.fhir_base_url == url


@pytest.mark.parametrize("url", ["http://localhost:8080/fhir", "http://127.0.0.1/fhir"])
def test_plain_http_to_a_local_fhir_server_is_allowed(url: str) -> None:
    assert load_settings({"ADHD_MCP_FHIR_BASE_URL": url}).fhir_base_url == url


def test_plain_http_public_url_is_refused(files: dict[str, str]) -> None:
    env = http_env(files) | {"ADHD_MCP_PUBLIC_URL": "http://adhd-mcp.example.test"}
    with pytest.raises(ConfigError, match="ADHD_MCP_PUBLIC_URL must use https"):
        load_settings(env)
    assert load_settings(env | {"ADHD_MCP_ALLOW_PLAIN_HTTP": "1"}).auth is not None


def test_a_non_local_fhir_server_needs_an_explicit_privacy_policy(tmp_path: Path) -> None:
    # P2: a site that set nothing got the permissive "cite" default.
    env = {"ADHD_MCP_FHIR_BASE_URL": "https://fhir.example.test/r4"}
    with pytest.raises(ConfigError, match="ADHD_MCP_PRIVACY_POLICY"):
        load_settings(env)
    assert load_settings(env | {"ADHD_MCP_PRIVACY_POLICY": "packaged"}).privacy_policy is None
    policy = tmp_path / "site_privacy.toml"
    policy.write_text("x")
    chosen = load_settings(env | {"ADHD_MCP_PRIVACY_POLICY": str(policy)})
    assert chosen.privacy_policy == policy


def test_fixture_data_and_a_local_server_need_no_privacy_policy() -> None:
    assert load_settings({"ADHD_MCP_FIXTURE_DIR": "tests/personas/bundles"}).privacy_policy is None
    assert load_settings({"ADHD_MCP_FHIR_BASE_URL": "http://localhost:8080/fhir"}) is not None


def test_the_audit_file_is_created_readable_by_its_owner_only(tmp_path: Path) -> None:
    # P5: the file links patient ids to outcomes.
    record = AuditRecord(
        record_id="r1",
        trace_id="t1",
        time=datetime(2026, 6, 15, tzinfo=UTC),
        caller="local",
        tool="get_server_info",
        outcome="success",
        server_version="x",
        tool_contract_version="x",
        ruleset=None,
        patient=None,
        resources_read=[],
    )
    path = tmp_path / "audit.jsonl"
    JsonlAuditSink(path).write(record)
    assert path.stat().st_mode & 0o777 == 0o600
