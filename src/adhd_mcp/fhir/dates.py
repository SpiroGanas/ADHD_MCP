"""Normalize FHIR date, dateTime, instant and Period values to one representation.

A dateTime or instant keeps the calendar date as written in its own offset; times and
time zones are not used by any rule. A time written without an offset, which FHIR forbids
but real feeds send, is accepted for the same reason: its calendar date is kept (peer
review 01, D3). Partial dates become ranges: ``2024`` covers the whole year and ``2024-02``
the whole month.
"""

import calendar
import re
from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

_DATE = re.compile(
    r"^(?P<y>\d{4})(?:-(?P<m>\d{2})(?:-(?P<d>\d{2})"
    r"(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?)?)?)?$"
)


class DatePrecision(StrEnum):
    YEAR = "year"
    MONTH = "month"
    DAY = "day"
    PERIOD = "period"


class DateRange(BaseModel):
    """Inclusive range of calendar dates. ``None`` means unbounded on that side."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    start: date | None
    end: date | None
    precision: DatePrecision

    def ends_on_or_after(self, day: date) -> bool:
        """FHIR ``ge`` search semantics: true if any part of the range is on or after ``day``."""
        return self.end is None or self.end >= day

    @property
    def best_date(self) -> date | None:
        """A single representative date: the start if known, otherwise the end."""
        return self.start if self.start is not None else self.end


def parse_fhir_date(raw: str) -> DateRange:
    """Parse a FHIR date, dateTime or instant."""
    match = _DATE.match(raw)
    if match is None:
        raise ValueError(f"not a FHIR date: {raw!r}")
    year = int(match["y"])
    try:
        if match["m"] is None:
            return DateRange(
                start=date(year, 1, 1), end=date(year, 12, 31), precision=DatePrecision.YEAR
            )
        month = int(match["m"])
        if match["d"] is None:
            last = calendar.monthrange(year, month)[1]
            return DateRange(
                start=date(year, month, 1),
                end=date(year, month, last),
                precision=DatePrecision.MONTH,
            )
        day = date(year, month, int(match["d"]))
    except (ValueError, calendar.IllegalMonthError) as exc:
        raise ValueError(f"not a FHIR date: {raw!r}") from exc
    return DateRange(start=day, end=day, precision=DatePrecision.DAY)


def parse_period(raw: dict[str, Any]) -> DateRange | None:
    """Parse a FHIR Period. Returns ``None`` if it has neither start nor end."""
    start = parse_fhir_date(raw["start"]).start if raw.get("start") else None
    end = parse_fhir_date(raw["end"]).end if raw.get("end") else None
    if start is None and end is None:
        return None
    return DateRange(start=start, end=end, precision=DatePrecision.PERIOD)
