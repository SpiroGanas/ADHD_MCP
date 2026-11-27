from datetime import UTC, date, datetime

import pytest

from adhd_mcp.clock import Clock, FixedClock


def test_fixed_clock_returns_its_instant_and_date(fixed_clock: FixedClock) -> None:
    assert fixed_clock.now() == datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
    assert fixed_clock.today() == date(2026, 6, 15)


def test_fixed_clock_satisfies_the_clock_protocol(fixed_clock: FixedClock) -> None:
    clock: Clock = fixed_clock
    assert clock.today() == date(2026, 6, 15)


def test_fixed_clock_rejects_naive_datetimes() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        FixedClock(datetime(2026, 1, 1))  # noqa: DTZ001 - the point of the test
