"""The three version lines reported in every output (see docs/architecture.md#versioning)."""

import hashlib
from functools import cache
from importlib.metadata import version
from importlib.resources import files
from importlib.resources.abc import Traversable

SERVER_NAME = "adhd-mcp"

#: Changes when a tool's name, inputs or output schema changes.
TOOL_CONTRACT_VERSION = "0.5.0"

#: The active referral ruleset: id, version and status. "draft" until the project owner
#: approves it for release (a test keeps this equal to the loaded ruleset).
ACTIVE_RULESET_VERSION: str | None = "adhd 1.0.0 (draft)"


#: Not clinical content: the release pins themselves (they would make the fingerprint
#: circular).
_NOT_CONTENT = frozenset({"released_rulesets.toml"})


def clinical_content_files() -> list[tuple[str, Traversable]]:
    """Every TOML file under the packaged data, by path: rulesets, catalogs, value sets, drug
    classes, instruments, site codes, safety gate and evidence-tool definitions, server
    profiles, privacy policy and wording. Any of them can change an output."""
    found: list[tuple[str, Traversable]] = []

    def walk(folder: Traversable, prefix: str) -> None:
        for item in folder.iterdir():
            path = f"{prefix}{item.name}"
            if item.is_dir():
                walk(item, f"{path}/")
            elif item.name.endswith(".toml") and path not in _NOT_CONTENT:
                found.append((path, item))

    walk(files("adhd_mcp.data"), "")
    return sorted(found, key=lambda pair: pair[0])


@cache
def clinical_content_sha256() -> str:
    """sha256 over every packaged clinical data file (path and content). Two outputs with the
    same value were produced from the same clinical content (peer review 01, X2)."""
    digest = hashlib.sha256()
    for path, f in clinical_content_files():
        digest.update(path.encode() + b"\0" + f.read_bytes() + b"\0")
    return digest.hexdigest()


def server_version() -> str:
    """The installed package version."""
    return version(SERVER_NAME)
