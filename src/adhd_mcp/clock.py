"""Injected time. Production code never reads the system clock directly."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """The current instant, timezone-aware."""
        ...

    def today(self) -> date:
        """The current date in UTC."""
        ...


class SystemClock:
    """The only place the real clock is read."""

    def now(self) -> datetime:  # pragma: no cover - reads the real clock
        return datetime.now(UTC)

    def today(self) -> date:  # pragma: no cover - reads the real clock
        return self.now().date()


@dataclass(frozen=True)
class FixedClock:
    """A clock frozen at one instant, for tests and reproducible runs."""

    instant: datetime

    def __post_init__(self) -> None:
        if self.instant.tzinfo is None:
            raise ValueError("FixedClock needs a timezone-aware datetime")

    def now(self) -> datetime:
        return self.instant

    def today(self) -> date:
        return self.instant.astimezone(UTC).date()
