"""AST nodes (immutable)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class Node:
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class Num(Node):
    value: Decimal


@dataclass(frozen=True, slots=True)
class Str(Node):
    value: str


@dataclass(frozen=True, slots=True)
class Name(Node):
    parts: tuple[str, ...]  # e.g. ("inputs", "load_kgf")


@dataclass(frozen=True, slots=True)
class Attr(Node):
    base: Node
    name: str


@dataclass(frozen=True, slots=True)
class Index(Node):
    base: Node
    index: Node


@dataclass(frozen=True, slots=True)
class Dot(Node):
    """The current element inside a lambda: ``.`` or ``.key``."""

    name: str | None


@dataclass(frozen=True, slots=True)
class Unary(Node):
    op: str
    operand: Node


@dataclass(frozen=True, slots=True)
class Binary(Node):
    op: str
    left: Node
    right: Node


@dataclass(frozen=True, slots=True)
class Compare(Node):
    ops: tuple[str, ...]
    operands: tuple[Node, ...]


@dataclass(frozen=True, slots=True)
class Not(Node):
    operand: Node


@dataclass(frozen=True, slots=True)
class And(Node):
    left: Node
    right: Node


@dataclass(frozen=True, slots=True)
class Or(Node):
    left: Node
    right: Node


@dataclass(frozen=True, slots=True)
class Ternary(Node):
    condition: Node
    if_true: Node
    if_false: Node


@dataclass(frozen=True, slots=True)
class Call(Node):
    name: str
    args: tuple[Node, ...]


@dataclass(frozen=True, slots=True)
class Lambda(Node):
    body: Node
