"""Built-in functions of SPEC Appendix K.3. All pure; numbers are ``Decimal``; vectors are lists."""

from __future__ import annotations

import functools
import itertools
import math
import statistics
from collections.abc import Callable, Sequence
from datetime import date, datetime
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from mizan.platform.formula.errors import FormulaError, FormulaTypeError

PI = Decimal("3.141592653589793238462643383279")


def to_decimal(value: Any, where: str = "number") -> Decimal:
    """Exact decimal from int, float (via repr), Decimal or numeric string."""
    if isinstance(value, bool):
        return Decimal(1) if value else Decimal(0)
    if isinstance(value, Decimal):
        if value.is_nan():
            raise FormulaTypeError(f"{where} received NaN", function=where)
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise FormulaTypeError(f"{where} received a non-finite number", function=where)
        return Decimal(repr(value))
    if isinstance(value, str):
        try:
            return Decimal(value)
        except InvalidOperation as exc:
            raise FormulaTypeError(
                f"{where} expects a number, got {value!r}", function=where
            ) from exc
    raise FormulaTypeError(f"{where} expects a number, got {type(value).__name__}", function=where)


def _num(value: Any, where: str) -> Decimal:
    if isinstance(value, str):
        raise FormulaTypeError(f"{where} expects a number, got a string", function=where)
    return to_decimal(value, where)


def _vec(value: Any, where: str) -> list[Decimal]:
    if not isinstance(value, list | tuple):
        raise FormulaTypeError(f"{where} expects a vector", function=where)
    return [_num(v, where) for v in value]


def _non_empty(vec: Sequence[Decimal], where: str) -> list[Decimal]:
    if not vec:
        raise FormulaError(f"{where} of an empty vector", function=where)
    return list(vec)


def round_half_up(x: Any, n: Any = 0) -> Decimal:
    digits = int(_num(n, "round"))
    quantum = Decimal(1).scaleb(-digits)
    return _num(x, "round").quantize(quantum, rounding=ROUND_HALF_UP)


def _min(*args: Any) -> Decimal:
    values = (
        _vec(args[0], "min")
        if len(args) == 1 and isinstance(args[0], list | tuple)
        else [_num(a, "min") for a in args]
    )
    return min(_non_empty(values, "min"))


def _max(*args: Any) -> Decimal:
    values = (
        _vec(args[0], "max")
        if len(args) == 1 and isinstance(args[0], list | tuple)
        else [_num(a, "max") for a in args]
    )
    return max(_non_empty(values, "max"))


def _avg(vec: Any) -> Decimal:
    values = _non_empty(_vec(vec, "avg"), "avg")
    return sum(values, Decimal(0)) / Decimal(len(values))


def _stddev(vec: Any) -> Decimal:
    values = _vec(vec, "stddev")
    return Decimal(statistics.stdev(values)) if len(values) >= 2 else Decimal(0)


def _median(vec: Any) -> Decimal:
    return Decimal(statistics.median(_non_empty(_vec(vec, "median"), "median")))


def _argmin(vec: Any) -> int:
    values = _non_empty(_vec(vec, "argmin"), "argmin")
    return min(range(len(values)), key=values.__getitem__)


def _argmax(vec: Any) -> int:
    values = _non_empty(_vec(vec, "argmax"), "argmax")
    return max(range(len(values)), key=values.__getitem__)


def _first(vec: Any) -> Any:
    if not isinstance(vec, list | tuple) or not vec:
        raise FormulaError("first of an empty vector", function="first")
    return vec[0]


def _last(vec: Any) -> Any:
    if not isinstance(vec, list | tuple) or not vec:
        raise FormulaError("last of an empty vector", function="last")
    return vec[-1]


def _monotonic(vec: Any) -> bool:
    values = _vec(vec, "is_monotonic_nondecreasing")
    return all(a <= b for a, b in itertools.pairwise(values))


def _parse_date(value: Any, where: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError as exc:
            raise FormulaTypeError(f"{where} expects an ISO date", function=where) from exc
    raise FormulaTypeError(f"{where} expects a date", function=where)


def _days_between(d1: Any, d2: Any) -> Decimal:
    return Decimal((_parse_date(d2, "days_between") - _parse_date(d1, "days_between")).days)


def _sqrt(x: Any) -> Decimal:
    value = _num(x, "sqrt")
    if value < 0:
        raise FormulaError("sqrt of a negative number", function="sqrt")
    return value.sqrt()


def _pow(a: Any, b: Any) -> Decimal:
    try:
        return _num(a, "pow") ** _num(b, "pow")
    except InvalidOperation as exc:
        raise FormulaError("invalid power", function="pow") from exc


def _if(cond: Any, a: Any, b: Any) -> Any:
    return a if cond else b


@functools.cache
def _registry() -> Any:
    import pint

    ureg = pint.UnitRegistry()
    try:
        ureg.Quantity(1, "kgf")
    except Exception:  # pragma: no cover - depends on the pint version
        ureg.define("kilogram_force = kilogram * g_0 = kgf")
    return ureg


_UNIT_ALIASES = {
    "cm2": "cm**2",
    "mm2": "mm**2",
    "m2": "m**2",
    "cm3": "cm**3",
    "m3": "m**3",
    "mm3": "mm**3",
    "l": "liter",
}


def _normalise_unit(unit: str) -> str:
    """Laboratory notation (``kgf/cm2``, ``kg/m3``) to pint notation."""
    parts = []
    for token in unit.replace(" ", "").split("/"):
        parts.append("*".join(_UNIT_ALIASES.get(factor, factor) for factor in token.split("*")))
    return "/".join(parts)


def _to(x: Any, *units: Any) -> Decimal:
    """``to(x, "from", "to")``: convert a plain number between declared units."""
    if len(units) != 2:
        raise FormulaTypeError("to(x, from_unit, to_unit) needs two unit names", function="to")
    ureg = _registry()
    try:
        source, target = _normalise_unit(str(units[0])), _normalise_unit(str(units[1]))
        magnitude = ureg.Quantity(float(_num(x, "to")), source).to(target).magnitude
    except Exception as exc:
        raise FormulaError(f"cannot convert {units[0]} to {units[1]}", function="to") from exc
    return to_decimal(float(magnitude), "to")


FUNCTIONS: dict[str, Callable[..., Any]] = {
    "round": round_half_up,
    "floor": lambda x: _num(x, "floor").to_integral_value(rounding=ROUND_FLOOR),
    "ceil": lambda x: _num(x, "ceil").to_integral_value(rounding=ROUND_CEILING),
    "abs": lambda x: abs(_num(x, "abs")),
    "sqrt": _sqrt,
    "pow": _pow,
    "pi": lambda: PI,
    "min": _min,
    "max": _max,
    "avg": _avg,
    "sum": lambda vec: sum(_vec(vec, "sum"), Decimal(0)),
    "count": lambda vec: Decimal(len(vec)) if isinstance(vec, list | tuple) else Decimal(1),
    "stddev": _stddev,
    "median": _median,
    "argmin": _argmin,
    "argmax": _argmax,
    "first": _first,
    "last": _last,
    "is_monotonic_nondecreasing": _monotonic,
    "to": _to,
    "days_between": _days_between,
    "if": _if,
}
LAZY_FUNCTIONS = frozenset({"filter", "map", "coalesce"})
