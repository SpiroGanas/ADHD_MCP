"""Shared evidence helpers: look-back windows, data completeness and safe reads."""

from datetime import date, timedelta

import pytest

from adhd_mcp.evidence.common import completeness, in_window, latest, not_after, read_category
from adhd_mcp.fhir.dates import DatePrecision, DateRange
from adhd_mcp.fhir.errors import FhirRequestError
from adhd_mcp.fhir.port import SearchWarning
from adhd_mcp.fhir.reader import ReadResult
from adhd_mcp.fhir.records import ConditionRecord, Skipped, SkipReason
from adhd_mcp.models.domain import DataStatus, ResourceRef

AS_OF = date(2026, 6, 15)

pytestmark = pytest.mark.anyio


def day(d: date) -> DateRange:
    return DateRange(start=d, end=d, precision=DatePrecision.DAY)


@pytest.mark.parametrize(
    ("days_before", "window", "expected"),
    [(0, 90, True), (89, 90, True), (90, 90, True), (91, 90, False), (365, 365, True)],
)
def test_window_includes_its_boundary_day(days_before: int, window: int, expected: bool) -> None:
    assert in_window(day(AS_OF - timedelta(days=days_before)), AS_OF, window) is expected


def test_window_excludes_dates_after_the_as_of_date() -> None:
    assert in_window(day(AS_OF + timedelta(days=1)), AS_OF, 90) is False


def test_a_partial_date_overlapping_the_window_is_inside() -> None:
    year = DateRange(start=date(2025, 1, 1), end=date(2025, 12, 31), precision=DatePrecision.YEAR)
    assert in_window(year, AS_OF, 365)
    assert not in_window(year, AS_OF, 90)


def test_an_open_ended_range_reaches_the_as_of_date() -> None:
    ongoing = DateRange(start=date(2020, 1, 1), end=None, precision=DatePrecision.PERIOD)
    assert in_window(ongoing, AS_OF, 90)


def test_an_undated_item_is_neither_in_nor_out() -> None:
    assert in_window(None, AS_OF, 90) is None


def test_not_after_the_as_of_date() -> None:
    assert not_after(day(AS_OF), AS_OF)
    assert not not_after(day(AS_OF + timedelta(days=1)), AS_OF)
    assert not_after(None, AS_OF)


def test_latest_prefers_the_latest_end_and_treats_open_ends_as_latest() -> None:
    a, b = day(date(2024, 1, 1)), day(date(2025, 1, 1))
    ongoing = DateRange(start=date(2020, 1, 1), end=None, precision=DatePrecision.PERIOD)
    assert latest(a, None, b) == b
    assert latest(a, ongoing) == ongoing
    assert latest(None, None) is None


def condition(cid: str) -> ConditionRecord:
    return ConditionRecord(
        ref=ResourceRef(resource_type="Condition", id=cid),
        codes=(),
        categories=(),
        clinical_status=None,
        verification_status=None,
        onset=None,
        abatement=None,
        recorded=None,
    )


def test_completeness_reports_each_state() -> None:
    skipped = (Skipped(ref=None, resource_type="Condition", reason=SkipReason.NO_ID),)
    empty = ReadResult[ConditionRecord](records=(), skipped=())
    full = ReadResult[ConditionRecord](records=(condition("c1"),), skipped=skipped)
    warned = ReadResult[ConditionRecord](
        records=(condition("c1"),),
        skipped=(),
        warnings=(SearchWarning(severity="warning", code="suppressed"),),
    )
    assert completeness("Condition", empty).status is DataStatus.EMPTY
    note = completeness("Condition", full)
    assert (note.status, note.records, note.skipped) == (DataStatus.AVAILABLE, 1, 1)
    note = completeness("Condition", warned)
    assert (note.status, note.warnings) == (DataStatus.INCOMPLETE, ["suppressed"])
    assert completeness("Condition", None).status is DataStatus.FAILED


async def test_read_category_turns_a_request_failure_into_none() -> None:
    async def fails() -> ReadResult[ConditionRecord]:
        raise FhirRequestError("search Condition: failed with HTTP 500", status=500, transient=True)

    async def works() -> ReadResult[ConditionRecord]:
        return ReadResult[ConditionRecord](records=(), skipped=())

    assert await read_category(fails()) is None
    assert await read_category(works()) == ReadResult[ConditionRecord](records=(), skipped=())
