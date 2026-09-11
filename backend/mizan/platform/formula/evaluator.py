"""Sandboxed evaluation with step and time limits (SPEC §10.5, Appendix K.4)."""

from __future__ import annotations

import time
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation, Overflow
from functools import lru_cache
from typing import Any

from mizan.platform.formula.errors import (
    DivisionByZero,
    FormulaError,
    FormulaLimitExceeded,
    FormulaTypeError,
    MissingValue,
)
from mizan.platform.formula.functions import FUNCTIONS, LAZY_FUNCTIONS, to_decimal
from mizan.platform.formula.nodes import (
    And,
    Attr,
    Binary,
    Call,
    Compare,
    Dot,
    Index,
    Lambda,
    Name,
    Node,
    Not,
    Num,
    Or,
    Str,
    Ternary,
    Unary,
)
from mizan.platform.formula.parser import parse

MAX_STEPS = 100_000
MAX_SECONDS = 0.05
_MISSING = object()

Env = Mapping[str, Any]


class Evaluator:
    def __init__(
        self, env: Env, *, max_steps: int = MAX_STEPS, max_seconds: float = MAX_SECONDS
    ) -> None:
        self.env = env
        self.max_steps = max_steps
        self.max_seconds = max_seconds
        self.steps = 0
        self.started = time.perf_counter()
        self.element_stack: list[Any] = []

    def run(self, node: Node) -> Any:
        return self.eval(node)

    def _tick(self) -> None:
        self.steps += 1
        if self.steps > self.max_steps:
            raise FormulaLimitExceeded("evaluation exceeded the step budget", limit=self.max_steps)
        if self.steps % 256 == 0 and time.perf_counter() - self.started > self.max_seconds:
            raise FormulaLimitExceeded(
                "evaluation exceeded the time budget", limit_ms=self.max_seconds * 1000
            )

    def eval(self, node: Node) -> Any:
        self._tick()
        if isinstance(node, Num):
            return node.value
        if isinstance(node, Str):
            return node.value
        if isinstance(node, Name):
            return self._resolve(node.parts)
        if isinstance(node, Attr):
            return self._attr(self.eval(node.base), node.name)
        if isinstance(node, Index):
            return self._index(self.eval(node.base), self.eval(node.index))
        if isinstance(node, Dot):
            if not self.element_stack:
                raise FormulaError("'.' is only valid inside a lambda")
            element = self.element_stack[-1]
            return element if node.name is None else self._attr(element, node.name)
        if isinstance(node, Unary):
            return -self._number(self.eval(node.operand), "unary -")
        if isinstance(node, Binary):
            return self._binary(node.op, self.eval(node.left), self.eval(node.right))
        if isinstance(node, Compare):
            left = self.eval(node.operands[0])
            for op, operand in zip(node.ops, node.operands[1:], strict=True):
                right = self.eval(operand)
                if not self._compare(op, left, right):
                    return False
                left = right
            return True
        if isinstance(node, Not):
            return not self._truthy(self.eval(node.operand))
        if isinstance(node, And):
            return self._truthy(self.eval(node.left)) and self._truthy(self.eval(node.right))
        if isinstance(node, Or):
            return self._truthy(self.eval(node.left)) or self._truthy(self.eval(node.right))
        if isinstance(node, Ternary):
            return (
                self.eval(node.if_true)
                if self._truthy(self.eval(node.condition))
                else self.eval(node.if_false)
            )
        if isinstance(node, Call):
            return self._call(node)
        if isinstance(node, Lambda):
            raise FormulaError("a lambda is only valid as an argument of filter or map")
        raise FormulaError(f"unsupported node {type(node).__name__}")

    # --- resolution ------------------------------------------------------------------------

    def _resolve(self, parts: tuple[str, ...]) -> Any:
        head, *rest = parts
        if head not in self.env:
            raise MissingValue(f"unknown name {head!r}", path=".".join(parts))
        value: Any = self.env[head]
        for name in rest:
            value = self._attr(value, name, path=".".join(parts))
        return value

    def _attr(self, base: Any, name: str, path: str | None = None) -> Any:
        where = path or name
        if isinstance(base, Mapping):
            value = base.get(name, _MISSING)
            if value is _MISSING or value is None:
                raise MissingValue(f"missing value {where!r}", path=where)
            return value
        if isinstance(base, list | tuple):
            return [self._attr(item, name, path=where) for item in base]
        raise FormulaTypeError(
            f"{where!r}: cannot read {name!r} from {type(base).__name__}", path=where
        )

    def _index(self, base: Any, index: Any) -> Any:
        if isinstance(base, list | tuple):
            i = int(self._number(index, "index"))
            if i < 0 or i >= len(base):
                raise MissingValue(f"index {i} out of range", index=i)
            return base[i]
        if isinstance(base, Mapping):
            return self._attr(base, str(index))
        raise FormulaTypeError("only vectors and records can be indexed")

    # --- operators -------------------------------------------------------------------------

    @staticmethod
    def _number(value: Any, where: str) -> Decimal:
        if isinstance(value, str):
            raise FormulaTypeError(f"{where} expects a number, got a string", where=where)
        return to_decimal(value, where)

    def _binary(self, op: str, left: Any, right: Any) -> Any:
        a, b = self._number(left, op), self._number(right, op)
        try:
            if op == "+":
                return a + b
            if op == "-":
                return a - b
            if op == "*":
                return a * b
            if op == "/":
                if b == 0:
                    raise DivisionByZero("division by zero")
                return a / b
            if op == "%":
                if b == 0:
                    raise DivisionByZero("modulo by zero")
                return a % b
            if op == "^":
                return a**b
        except (InvalidOperation, Overflow) as exc:
            raise FormulaError(f"invalid arithmetic for {op}") from exc
        raise FormulaError(f"unknown operator {op}")

    @staticmethod
    def _compare(op: str, left: Any, right: Any) -> bool:
        if op == "==":
            return bool(left == right)
        if op == "!=":
            return bool(left != right)
        if isinstance(left, str) or isinstance(right, str):
            raise FormulaTypeError(f"{op} does not apply to strings", op=op)
        a, b = to_decimal(left, op), to_decimal(right, op)
        return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]

    @staticmethod
    def _truthy(value: Any) -> bool:
        if isinstance(value, list | tuple):
            return len(value) > 0
        return bool(value)

    # --- calls -----------------------------------------------------------------------------

    def _call(self, node: Call) -> Any:
        name = node.name
        if name in LAZY_FUNCTIONS:
            return self._lazy(node)
        func = FUNCTIONS.get(name)
        if func is None:
            raise FormulaError(f"unknown function {name!r}", function=name)
        args = [self.eval(arg) for arg in node.args]
        try:
            return func(*args)
        except TypeError as exc:
            raise FormulaTypeError(f"{name}: {exc}", function=name) from exc
        except ValueError as exc:
            raise FormulaError(f"{name}: {exc}", function=name) from exc

    def _lazy(self, node: Call) -> Any:
        if node.name == "coalesce":
            for arg in node.args:
                try:
                    value = self.eval(arg)
                except MissingValue:
                    continue
                if value is not None:
                    return value
            raise MissingValue("coalesce: every value is missing")
        if len(node.args) != 2 or not isinstance(node.args[1], Lambda):
            raise FormulaTypeError(f"{node.name}(vector, {{lambda}}) expected", function=node.name)
        vector = self.eval(node.args[0])
        if not isinstance(vector, list | tuple):
            raise FormulaTypeError(f"{node.name} expects a vector", function=node.name)
        body = node.args[1].body
        results = []
        for element in vector:
            self.element_stack.append(element)
            try:
                value = self.eval(body)
            finally:
                self.element_stack.pop()
            if node.name == "map":
                results.append(value)
            elif self._truthy(value):
                results.append(element)
        return results


class Formula:
    """A compiled expression: parse once, evaluate many times."""

    __slots__ = ("node", "text")

    def __init__(self, text: str) -> None:
        self.text = text
        self.node = parse(text)

    def evaluate(self, env: Env, **limits: Any) -> Any:
        return Evaluator(env, **limits).run(self.node)

    def __repr__(self) -> str:
        return f"Formula({self.text!r})"


@lru_cache(maxsize=4096)
def compile_formula(text: str) -> Formula:
    return Formula(text)


def evaluate(text: str, env: Env, **limits: Any) -> Any:
    return compile_formula(text).evaluate(env, **limits)
