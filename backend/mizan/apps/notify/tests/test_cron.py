"""The five-field cron matcher used by digest rules."""

from __future__ import annotations

import datetime as dt

import pytest

from mizan.apps.notify import cron


def test_parse_lists_ranges_and_steps() -> None:
    minute, hour, dom, month, dow = cron.parse("*/15 6-8,20 1,15 * 1-5")
    assert minute == {0, 15, 30, 45}
    assert hour == {6, 7, 8, 20}
    assert dom == {1, 15}
    assert month == set(range(1, 13))
    assert dow == {1, 2, 3, 4, 5}


def test_sunday_is_zero_and_seven() -> None:
    assert 0 in cron.parse("0 0 * * 7")[4]
    assert 7 in cron.parse("0 0 * * 0")[4]


@pytest.mark.parametrize(
    "bad", ["30 6 * *", "60 6 * * *", "a b c d e", "*/0 * * * *", "5-3 * * * *"]
)
def test_invalid_expressions(bad: str) -> None:
    with pytest.raises(cron.InvalidCron):
        cron.validate(bad)


def test_matches_and_window() -> None:
    at = dt.datetime(2026, 9, 14, 6, 30)  # a Monday
    assert cron.matches("30 6 * * *", at)
    assert cron.matches("30 6 * * 1", at)
    assert not cron.matches("30 6 * * 2", at)
    assert (
        cron.matches_window(
            "30 6 * * *", at - dt.timedelta(minutes=5), at + dt.timedelta(minutes=1)
        )
        == at
    )
    assert (
        cron.matches_window(
            "30 6 * * *", at + dt.timedelta(minutes=1), at + dt.timedelta(minutes=10)
        )
        is None
    )
