"""Reusable assertion: no tool output may state or imply a diagnosis."""

from typing import Any

from adhd_mcp.wording.guard import find_diagnostic_language


def _is_false_marker(item: Any) -> bool:
    """``is_diagnosis`` is false in an output, or a schema property fixed to false."""
    return item is False or (isinstance(item, dict) and item.get("const") is False)


def _walk(value: Any, path: str) -> list[str]:
    problems: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}" if path else str(key)
            problems += [f"{child} (key): {p}" for p in find_diagnostic_language(str(key))]
            if key == "is_diagnosis" and not _is_false_marker(item):
                problems.append(f"{child}: is_diagnosis must be false")
            problems += _walk(item, child)
    elif isinstance(value, list | tuple):
        for index, item in enumerate(value):
            problems += _walk(item, f"{path}[{index}]")
    elif isinstance(value, str):
        problems += [f"{path}: {p}" for p in find_diagnostic_language(value)]
    return problems


def assert_no_diagnostic_language(output: Any) -> None:
    """Fail if any string, key or marker in a JSON-like output implies a diagnosis."""
    problems = _walk(output, "")
    if problems:
        raise AssertionError("Diagnostic language in output:\n" + "\n".join(problems))
