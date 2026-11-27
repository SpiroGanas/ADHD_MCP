"""The condition plugin interface and registry."""

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import date

from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.models.domain import DataCompleteness, ExclusionCheck
from adhd_mcp.rules.catalog import SignalCatalog
from adhd_mcp.rules.ruleset import Ruleset
from adhd_mcp.rules.scorer import Scorer
from adhd_mcp.terminology.site_codes import SiteCodes


@dataclass(frozen=True)
class ExclusionResult:
    """Whether the patient is already in care for the condition (null when unknown)."""

    excluded: bool | None
    checks: list[ExclusionCheck]
    data_completeness: list[DataCompleteness]
    notes: list[str] = field(default_factory=list)


ExclusionCheckFn = Callable[[PatientRecords, str, date, SiteCodes], Awaitable[ExclusionResult]]


@dataclass(frozen=True)
class ConditionPlugin:
    id: str
    title: str
    catalog: SignalCatalog
    ruleset: Ruleset
    recommendation_texts: Mapping[str, str]
    next_step: str
    note_texts: Mapping[str, str] = field(default_factory=dict)
    """Text added when a note-weight signal of the same id is present."""
    exclusions: ExclusionCheckFn | None = None
    scorer: Scorer | None = None

    def __post_init__(self) -> None:
        if (self.catalog.id, self.catalog.version) != (
            self.ruleset.catalog,
            self.ruleset.catalog_version,
        ):
            raise ValueError(f"condition {self.id}: ruleset and catalog versions differ")
        if self.ruleset.exclusions and self.exclusions is None:
            raise ValueError(
                f"condition {self.id}: the ruleset names exclusions but none are wired"
            )


class ConditionRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, ConditionPlugin] = {}

    def register(self, plugin: ConditionPlugin) -> None:
        if plugin.id in self._plugins:
            raise ValueError(f"condition {plugin.id} is already registered")
        self._plugins[plugin.id] = plugin

    def get(self, condition_id: str) -> ConditionPlugin:
        try:
            return self._plugins[condition_id]
        except KeyError:
            raise LookupError(f"no condition {condition_id!r}") from None

    def ids(self) -> list[str]:
        return sorted(self._plugins)
