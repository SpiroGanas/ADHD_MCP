"""One date representation across FHIR's date, dateTime, instant and Period variants."""

from datetime import date

import pytest

from adhd_mcp.fhir.dates import DatePrecision, DateRange, parse_fhir_date, parse_period


@pytest.mark.parametrize(
    ("raw", "start", "end", "precision"),
    [
        ("2024", date(2024, 1, 1), date(2024, 12, 31), DatePrecision.YEAR),
        ("2024-02", date(2024, 2, 1), date(2024, 2, 29), DatePrecision.MONTH),
        ("2023-02", date(2023, 2, 1), date(2023, 2, 28), DatePrecision.MONTH),
        ("2024-03-05", date(2024, 3, 5), date(2024, 3, 5), DatePrecision.DAY),
        ("2024-03-05T10:15:00Z", date(2024, 3, 5), date(2024, 3, 5), DatePrecision.DAY),
        ("2024-03-05T23:30:00-05:00", date(2024, 3, 5), date(2024, 3, 5), DatePrecision.DAY),
        ("2024-03-05T00:30:00.123+09:00", date(2024, 3, 5), date(2024, 3, 5), DatePrecision.DAY),
        # Peer review 01, D3 (E10): FHIR requires an offset with a time, but real feeds often
        # omit it. Only the calendar date is used, so the date as written is kept.
        ("2024-03-05T10:15:00", date(2024, 3, 5), date(2024, 3, 5), DatePrecision.DAY),
        ("2024-03-05T10:15", date(2024, 3, 5), date(2024, 3, 5), DatePrecision.DAY),
        ("2024-03-05T10:15:00.5", date(2024, 3, 5), date(2024, 3, 5), DatePrecision.DAY),
    ],
)
def test_each_fhir_date_variant(raw: str, start: date, end: date, precision: DatePrecision) -> None:
    assert parse_fhir_date(raw) == DateRange(start=start, end=end, precision=precision)


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "24-01-01",
        "2024-13",
        "2024-02-30",
        "yesterday",
        "2024-1-5",
        "2024-03-05T10",
        "2024-03-05T",
        "2024-03-05 10:15:00",
        "2024-03-05T10:15:00+5",
    ],
)
def test_malformed_dates_are_rejected(raw: str) -> None:
    with pytest.raises(ValueError, match="FHIR date"):
        parse_fhir_date(raw)


def test_period_with_both_ends() -> None:
    period = parse_period({"start": "2024-01-02T08:00:00Z", "end": "2024-01-05"})
    assert period == DateRange(
        start=date(2024, 1, 2), end=date(2024, 1, 5), precision=DatePrecision.PERIOD
    )


def test_open_ended_period_has_no_end() -> None:
    period = parse_period({"start": "2024-01"})
    assert period == DateRange(start=date(2024, 1, 1), end=None, precision=DatePrecision.PERIOD)


def test_period_with_only_an_end() -> None:
    period = parse_period({"end": "2024"})
    assert period == DateRange(start=None, end=date(2024, 12, 31), precision=DatePrecision.PERIOD)


def test_empty_period_is_none() -> None:
    assert parse_period({}) is None


def test_date_range_ends_on_or_after() -> None:
    year = parse_fhir_date("2023")
    assert year.ends_on_or_after(date(2023, 12, 31))
    assert not year.ends_on_or_after(date(2024, 1, 1))
    open_period = parse_period({"start": "2020-01-01"})
    assert open_period is not None
    assert open_period.ends_on_or_after(date(2099, 1, 1))


def test_best_date_prefers_start_then_end() -> None:
    assert parse_fhir_date("2024-03").best_date == date(2024, 3, 1)
    only_end = parse_period({"end": "2024-05-06"})
    assert only_end is not None
    assert only_end.best_date == date(2024, 5, 6)
