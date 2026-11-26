"""Detect wording that states or implies a diagnosis (standing invariant 1)."""

import re
from functools import cache

from adhd_mcp.wording.text import load_wording


@cache
def _compiled() -> tuple[tuple[str, re.Pattern[str]], ...]:
    spec = load_wording().diagnostic_language
    conditions = "|".join(spec.conditions)
    return tuple(
        (p.id, re.compile(p.pattern.replace("{condition}", conditions), re.IGNORECASE))
        for p in spec.patterns
    )


def find_diagnostic_language(text: str) -> list[str]:
    """Identifiers of every forbidden pattern found in ``text``; empty if none."""
    return [pattern_id for pattern_id, regex in _compiled() if regex.search(text)]
