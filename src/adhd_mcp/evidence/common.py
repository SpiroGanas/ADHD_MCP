"""Helpers every evidence assembler shares: look-back windows, data completeness and
reading a data category without letting one failed request hide the others."""

from collections.abc import Awaitable
from datetime import date, timedelta

from pydantic import BaseModel

from adhd_mcp.fhir.dates import DateRange
from adhd_mcp.fhir.errors import FhirRequestError
from adhd_mcp.fhir.reader import ReadResult
from adhd_mcp.fhir.records import SkipReason
from adhd_mcp.models.domain import DataCompleteness, DataStatus

#: Completeness warning code for resources that could not be read.
UNREADABLE = "unreadable_resources"


def in_window(when: DateRange | None, as_of: date, days: int) -> bool | None:
    """Whether any part of ``when`` falls within ``days`` days before ``as_of``, inclusive
    at both ends (day ``as_of - days`` counts). ``None`` when the item has no date."""
    if when is None:
        return None
    start = as_of - timedelta(days=days)
    begins_by_as_of = when.start is None or when.start <= as_of
    ends_in_window = when.end is None or when.end >= start
    return begins_by_as_of and ends_in_window


def not_after(when: DateRange | None, as_of: date) -> bool:
    """False only for items that begin after the as-of date. Undated items are kept."""
    return when is None or when.start is None or when.start <= as_of


def latest(*ranges: DateRange | None) -> DateRange | None:
    """The range that ends last; an open end counts as latest."""
    known = [r for r in ranges if r is not None]
    if not known:
        return None
    return max(known, key=lambda r: (r.end is None, r.end or date.min))


def completeness[R: BaseModel](category: str, result: ReadResult[R] | None) -> DataCompleteness:
    """The completeness note for one category; ``None`` means the read failed. Server
    warnings and unreadable resources make it ``incomplete``."""
    if result is None:
        return DataCompleteness(category=category, status=DataStatus.FAILED)
    warnings = [w.code for w in result.warnings]
    # A resource that could not be read (malformed, or no id) may hold a signal: the
    # category is incomplete. Entered-in-error and refuted resources are not data.
    if any(s.reason is not SkipReason.EXCLUDED_STATUS for s in result.skipped):
        warnings.append(UNREADABLE)
    if warnings:
        status = DataStatus.INCOMPLETE
    elif result.records:
        status = DataStatus.AVAILABLE
    else:
        status = DataStatus.EMPTY
    return DataCompleteness(
        category=category,
        status=status,
        records=len(result.records),
        skipped=len(result.skipped),
        warnings=warnings,
    )


async def read_category[R: BaseModel](read: Awaitable[ReadResult[R]]) -> ReadResult[R] | None:
    """Await one category read; a failed request becomes ``None`` (reported as failed)."""
    try:
        return await read
    except FhirRequestError:
        return None
