"""Condition plugins (ADR 0005). The engine and orchestration contain nothing specific to
any condition; each condition supplies its catalog, ruleset, wording and exclusions."""

from adhd_mcp.conditions.base import ConditionPlugin, ConditionRegistry, ExclusionResult

__all__ = ["ConditionPlugin", "ConditionRegistry", "ExclusionResult"]
