"""Packaging stays consistent (ADR 0013): the container uses the uv and Python versions the
project and CI use, and keeps out everything but the package and the sample data."""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")


def test_the_container_uses_the_ci_uv_version() -> None:
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    ci_versions = set(re.findall(r'version: "(\d+\.\d+\.\d+)"', ci))
    assert ci_versions == set(re.findall(r"astral-sh/uv:(\d+\.\d+\.\d+)", DOCKERFILE))


def test_the_container_python_matches_the_project() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["requires-python"] == ">=3.12,<3.13"
    assert set(re.findall(r"FROM python:(\d+\.\d+)", DOCKERFILE)) == {"3.12"}


def test_the_container_runs_as_a_non_root_user_without_dev_dependencies() -> None:
    assert "\nUSER adhd\n" in DOCKERFILE
    assert "--no-dev" in DOCKERFILE
    assert "--locked" in DOCKERFILE


def test_only_the_package_and_sample_data_enter_the_build_context() -> None:
    lines = (ROOT / ".dockerignore").read_text(encoding="utf-8").split()
    assert lines[lines.index("*")] == "*"
    allowed = {line for line in lines if line.startswith("!")}
    assert allowed == {
        "!pyproject.toml", "!uv.lock", "!README.md", "!LICENSE", "!src/",
        "!tests/personas/bundles/",
    }  # fmt: skip


def test_the_source_distribution_carries_only_the_package() -> None:
    hatch = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["hatch"]
    assert set(hatch["build"]["targets"]["sdist"]["include"]) == {
        "/src/adhd_mcp", "/README.md", "/LICENSE", "/CHANGELOG.md", "/pyproject.toml",
    }  # fmt: skip
    assert hatch["build"]["targets"]["wheel"]["packages"] == ["src/adhd_mcp"]
