"""Helpers every evidence assembler shares: look-back windows, data completeness and
reading a data category without letting one failed request hide the others.

A category read gives a ``ReadResult``, ``None`` (the read failed) or ``NOT_SUPPORTED`` (the
server does not offer the type). Logic uses ``usable``, which treats both of the latter as
unknown, so a type that is not offered can never pass for "searched and found nothing".
"""

from collections.abc import Awaitable
from dataclasses import dataclass
from datetime import date, timedelta

from pydantic import BaseModel

from adhd_mcp.fhir.dates import DateRange
from adhd_mcp.fhir.errors import FhirRequestError, SearchNotSupportedError
from adhd_mcp.fhir.reader import ReadResult
from adhd_mcp.fhir.records import SkipReason
from adhd_mcp.models.domain import DataCompleteness, DataStatus

#: Completeness warning code for resources that could not be read.
UNREADABLE = "unreadable_resources"


@dataclass(frozen=True)
class NotSupported:
    """The FHIR server does not offer this resource type."""


NOT_SUPPORTED = NotSupported()

type Read[R: BaseModel] = ReadResult[R] | NotSupported | None


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


def completeness[R: BaseModel](category: str, result: Read[R]) -> DataCompleteness:
    """The completeness note for one category; ``None`` means the read failed. Server
    warnings and unreadable resources make it ``incomplete``."""
    if result is None:
        return DataCompleteness(category=category, status=DataStatus.FAILED)
    if isinstance(result, NotSupported):
        return DataCompleteness(category=category, status=DataStatus.NOT_SUPPORTED)
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


async def read_category[R: BaseModel](read: Awaitable[ReadResult[R]]) -> Read[R]:
    """Await one category read; a failed request becomes ``None`` (reported as failed) and a
    type the server does not offer becomes ``NOT_SUPPORTED``."""
    try:
        return await read
    except FhirRequestError:
        return None
    except SearchNotSupportedError:
        return NOT_SUPPORTED


def not_offered_reason(categories: list[str]) -> str:
    """The reason given for a check that needs a type the server does not offer."""
    return f"Not performed: the FHIR server does not offer {', '.join(categories)}."


def usable[R: BaseModel](result: Read[R]) -> ReadResult[R] | None:
    """The read data, or ``None`` when it is unknown (failed or not offered)."""
    return result if isinstance(result, ReadResult) else None
