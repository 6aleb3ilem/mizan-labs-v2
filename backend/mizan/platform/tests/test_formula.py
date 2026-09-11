"""The formula language: grammar, precedence, functions, sandbox limits (Appendix K)."""

from __future__ import annotations

from decimal import Decimal as D

import pytest

from mizan.platform.formula import (
    DivisionByZero,
    FormulaError,
    FormulaLimitExceeded,
    FormulaSyntaxError,
    MissingValue,
    compile_formula,
    evaluate,
)


def test_precedence_and_associativity() -> None:
    assert evaluate("2 + 3 * 4 ^ 2", {}) == 50
    assert evaluate("2 ^ 3 ^ 2", {}) == 512  # right associative
    assert evaluate("-2 ^ 2", {}) == 4  # K.1: unary minus binds tighter than ^
    assert evaluate("-(2 ^ 2)", {}) == -4
    assert evaluate("(2 + 3) * 4", {}) == 20
    assert evaluate("7 % 3", {}) == 1
    assert evaluate("10 / 4", {}) == 2.5


def test_comparisons_booleans_and_ternary() -> None:
    env = {"inputs": {"a": 3, "b": 5}}
    assert evaluate("inputs.a < inputs.b and not inputs.a == inputs.b", env) is True
    assert evaluate("inputs.a > inputs.b or inputs.b >= 5", env) is True
    assert evaluate("1 < inputs.a <= 3", env) is True
    assert evaluate("inputs.a > 2 ? 'big' : 'small'", env) == "big"
    assert evaluate("if(inputs.a > 4, 1, 0)", env) == 0


def test_namespaces_vectors_and_lambdas() -> None:
    env = {
        "specimens": [{"stress_mpa": 22.4}, {"stress_mpa": 16.1}, {"stress_mpa": 23.0}],
        "aggregates": {"mean_mpa": 21.5},
        "params": {"threshold": 5},
        "series": [{"cum_retained": 10}, {"cum_retained": 25}, {"cum_retained": 20}],
    }
    assert evaluate("count(specimens.stress_mpa)", env) == 3
    assert (
        evaluate(
            "count(filter(specimens, {aggregates.mean_mpa - .stress_mpa >= params.threshold}))", env
        )
        == 1
    )
    assert evaluate("argmin(specimens.stress_mpa)", env) == 1
    assert evaluate("map(specimens, {.stress_mpa * 10})", env) == [
        D("224.0"),
        D("161.0"),
        D("230.0"),
    ]
    assert evaluate("filter(specimens.stress_mpa, {. > 20})", env) == [22.4, 23.0]
    assert evaluate("series[1].cum_retained", env) == 25
    assert evaluate("is_monotonic_nondecreasing(series.cum_retained)", env) is False
    assert evaluate("first(series).cum_retained + last(series.cum_retained)", env) == 30


def test_functions() -> None:
    assert evaluate("round(2.5)", {}) == 3
    assert evaluate("round(22.45, 1)", {}) == 22.5  # HALF_UP, not banker's rounding
    assert evaluate("round(pi() * 16 ^ 2 / 4, 2)", {}) == D("201.06")
    assert evaluate("floor(2.7) + ceil(2.1) + abs(-1)", {}) == 6
    assert evaluate("sqrt(16) + pow(2, 3)", {}) == 12
    vectors = {
        "v": {
            "a": [4, 9],
            "b": [1, 2, 3, 6],
            "c": [1, 1],
            "d": [1, 9, 3],
            "e": [2, 4, 4, 4, 5, 5, 7, 9],
        }
    }
    assert evaluate("min(3, 1, 2) + max(v.a)", vectors) == 10
    assert evaluate("avg(v.b) + sum(v.c) + median(v.d)", vectors) == 8
    assert round(float(evaluate("stddev(v.e)", vectors)), 4) == 2.1381
    assert evaluate("days_between('2026-09-10', '2026-10-08')", {}) == 28
    assert evaluate("coalesce(inputs.missing, 7)", {"inputs": {}}) == 7
    assert round(float(evaluate("to(1, 'kgf/cm2', 'MPa')", {})), 5) == 0.09807


def test_errors_are_typed_with_message_keys() -> None:
    with pytest.raises(MissingValue) as missing:
        evaluate("inputs.load_kgf / 2", {"inputs": {}})
    assert missing.value.message_key == "formula.missing_value"
    assert missing.value.params["path"] == "inputs.load_kgf"
    with pytest.raises(DivisionByZero):
        evaluate("1 / (2 - 2)", {})
    with pytest.raises(FormulaSyntaxError):
        compile_formula("1 +")
    with pytest.raises(FormulaSyntaxError):
        compile_formula("inputs.a ==")
    with pytest.raises(FormulaError):
        evaluate("teleport(1)", {})
    with pytest.raises(FormulaError):
        evaluate("'a' + 1", {})
    with pytest.raises(MissingValue):
        evaluate("series[5].x", {"series": []})


def test_sandbox_limits() -> None:
    with pytest.raises(FormulaSyntaxError):
        compile_formula("(" * 70 + "1" + ")" * 70)
    with pytest.raises(FormulaSyntaxError):
        compile_formula("1 + " * 1500 + "1")
    big = {"v": list(range(20_000))}
    with pytest.raises(FormulaLimitExceeded):
        evaluate("count(filter(v, {. > 1}))", big, max_steps=1000)
    # no attribute access into Python internals, no assignment, no loops
    with pytest.raises(FormulaError):
        evaluate("inputs.__class__", {"inputs": {"a": 1}})
    with pytest.raises(FormulaSyntaxError):
        compile_formula("a = 1")


def test_compiled_formulas_are_cached() -> None:
    assert compile_formula("1 + 1") is compile_formula("1 + 1")


def test_arithmetic_is_exact_decimal() -> None:
    assert evaluate("17.4 - 12.4 >= 5", {}) is True
    assert evaluate("0.1 + 0.2 == 0.3", {}) is True
    assert evaluate("round(2.675, 2)", {}) == D("2.68")
    assert evaluate("inputs.a - inputs.b", {"inputs": {"a": 17.4, "b": 12.4}}) == D("5.0")
