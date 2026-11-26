"""Synthetic persona catalog: load bundles and expectations in one step.

from tests.personas import load_catalog, load_bundle, all_resources
"""

import json
import tomllib
from functools import cache
from pathlib import Path
from typing import Any

PERSONA_DIR = Path(__file__).parent
BUNDLE_DIR = PERSONA_DIR / "bundles"


@cache
def load_catalog() -> dict[str, Any]:
    return tomllib.loads((PERSONA_DIR / "catalog.toml").read_text(encoding="utf-8"))


def persona_ids() -> list[str]:
    return [p["id"] for p in load_catalog()["personas"]]


def load_bundle(persona_id: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((BUNDLE_DIR / f"{persona_id}.json").read_text("utf-8"))
    return data


def all_resources() -> list[dict[str, Any]]:
    """Every resource of every persona, for loading an adapter in one step."""
    return [e["resource"] for pid in persona_ids() for e in load_bundle(pid)["entry"]]
