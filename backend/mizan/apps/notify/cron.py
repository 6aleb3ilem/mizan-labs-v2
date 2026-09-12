"""A small five-field cron matcher (minute hour day-of-month month day-of-week), no dependency.

Supports ``*``, lists ``1,15``, ranges ``1-5``, steps ``*/5`` and ``1-30/10``; day-of-week
0-7 (0 and 7 are Sunday). A digest rule fires when one minute of the scheduler's window matches.
"""

from __future__ import annotations

from datetime import datetime, timedelta

FIELD_RANGES: tuple[tuple[int, int], ...] = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 7))


class InvalidCron(ValueError):
    pass


def _parse_field(text: str, low: int, high: int) -> set[int]:
    values: set[int] = set()
    for part in text.split(","):
        part = part.strip()
        if not part:
            raise InvalidCron(f"empty element in {text!r}")
        step = 1
        if "/" in part:
            part, step_s = part.split("/", 1)
            if not step_s.isdigit() or int(step_s) < 1:
                raise InvalidCron(f"bad step in {text!r}")
            step = int(step_s)
        if part == "*":
            start, end = low, high
        elif "-" in part:
            a, b = part.split("-", 1)
            if not (a.isdigit() and b.isdigit()):
                raise InvalidCron(f"bad range in {text!r}")
            start, end = int(a), int(b)
        else:
            if not part.isdigit():
                raise InvalidCron(f"bad value in {text!r}")
            start = end = int(part)
            if step != 1:
                end = high
        if start < low or end > high or start > end:
            raise InvalidCron(f"{text!r} out of range {low}-{high}")
        values.update(range(start, end + 1, step))
    return values


def parse(expression: str) -> tuple[set[int], ...]:
    fields = expression.split()
    if len(fields) != len(FIELD_RANGES):
        raise InvalidCron("a cron expression has five fields")
    parsed = tuple(
        _parse_field(field, low, high)
        for field, (low, high) in zip(fields, FIELD_RANGES, strict=True)
    )
    dow = set(parsed[4])
    if 7 in dow:
        dow.add(0)
    if 0 in dow:
        dow.add(7)
    return (*parsed[:4], dow)


def validate(expression: str) -> None:
    parse(expression)


def matches(expression: str, moment: datetime) -> bool:
    minute, hour, dom, month, dow = parse(expression)
    return (
        moment.minute in minute
        and moment.hour in hour
        and moment.day in dom
        and moment.month in month
        and (moment.isoweekday() % 7) in dow
    )


def matches_window(expression: str, start: datetime, end: datetime) -> datetime | None:
    """The first minute in ``[start, end)`` matching ``expression`` (local wall-clock times)."""
    parsed_minute, parsed_hour, dom, month, dow = parse(expression)
    moment = start.replace(second=0, microsecond=0)
    while moment < end:
        if (
            moment.minute in parsed_minute
            and moment.hour in parsed_hour
            and moment.day in dom
            and moment.month in month
            and (moment.isoweekday() % 7) in dow
        ):
            return moment
        moment += timedelta(minutes=1)
    return None
