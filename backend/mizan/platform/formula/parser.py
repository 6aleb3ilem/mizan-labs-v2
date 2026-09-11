"""Recursive-descent parser for the grammar of SPEC Appendix K.1."""

from __future__ import annotations

from decimal import Decimal

from mizan.platform.formula.errors import FormulaSyntaxError
from mizan.platform.formula.lexer import Token, tokenize
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

MAX_DEPTH = 64
COMPARISON_OPS = ("==", "!=", "<", "<=", ">", ">=")


class Parser:
    def __init__(self, text: str) -> None:
        self.tokens = tokenize(text)
        self.i = 0
        self.depth = 0

    # --- helpers ---------------------------------------------------------------------------

    @property
    def tok(self) -> Token:
        return self.tokens[self.i]

    def advance(self) -> Token:
        token = self.tokens[self.i]
        self.i += 1
        return token

    def at(self, kind: str, value: str | None = None) -> bool:
        return self.tok.kind == kind and (value is None or self.tok.value == value)

    def expect(self, kind: str, value: str | None = None) -> Token:
        if not self.at(kind, value):
            wanted = value or kind
            raise FormulaSyntaxError(
                f"expected {wanted!r} at {self.tok.pos}", pos=self.tok.pos, expected=wanted
            )
        return self.advance()

    def nest(self) -> None:
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise FormulaSyntaxError("expression nested too deeply", limit=MAX_DEPTH)

    def unnest(self) -> None:
        self.depth -= 1

    # --- grammar ---------------------------------------------------------------------------

    def parse(self) -> Node:
        node = self.expr()
        if not self.at("eof"):
            raise FormulaSyntaxError(
                f"unexpected {self.tok.value!r} at {self.tok.pos}", pos=self.tok.pos
            )
        return node

    def expr(self) -> Node:
        self.nest()
        try:
            return self.ternary()
        finally:
            self.unnest()

    def ternary(self) -> Node:
        condition = self.or_expr()
        if self.at("op", "?"):
            self.advance()
            if_true = self.expr()
            self.expect("op", ":")
            if_false = self.expr()
            return Ternary(condition, if_true, if_false)
        return condition

    def or_expr(self) -> Node:
        node = self.and_expr()
        while self.at("ident", "or"):
            self.advance()
            node = Or(node, self.and_expr())
        return node

    def and_expr(self) -> Node:
        node = self.not_expr()
        while self.at("ident", "and"):
            self.advance()
            node = And(node, self.not_expr())
        return node

    def not_expr(self) -> Node:
        if self.at("ident", "not"):
            self.advance()
            return Not(self.not_expr())
        return self.comparison()

    def comparison(self) -> Node:
        first = self.additive()
        ops: list[str] = []
        operands: list[Node] = [first]
        while self.tok.kind == "op" and self.tok.value in COMPARISON_OPS:
            ops.append(self.advance().value)
            operands.append(self.additive())
        if ops:
            return Compare(tuple(ops), tuple(operands))
        return first

    def additive(self) -> Node:
        node = self.term()
        while self.tok.kind == "op" and self.tok.value in ("+", "-"):
            op = self.advance().value
            node = Binary(op, node, self.term())
        return node

    def term(self) -> Node:
        node = self.power()
        while self.tok.kind == "op" and self.tok.value in ("*", "/", "%"):
            op = self.advance().value
            node = Binary(op, node, self.power())
        return node

    def power(self) -> Node:
        base = self.unary()
        if self.at("op", "^"):
            self.advance()
            self.nest()
            try:
                exponent = self.power()  # right associative
            finally:
                self.unnest()
            return Binary("^", base, exponent)
        return base

    def unary(self) -> Node:
        if self.at("op", "-"):
            self.advance()
            return Unary("-", self.unary())
        return self.primary()

    def primary(self) -> Node:
        token = self.tok
        if token.kind == "number":
            self.advance()
            return Num(Decimal(token.value))
        if token.kind == "string":
            self.advance()
            return Str(token.value)
        if token.kind == "ident":
            self.advance()
            if self.at("op", "("):
                return self.call(token.value)
            return self.postfix(Name((token.value,)))
        if token.kind == "op" and token.value == "(":
            self.advance()
            node = self.expr()
            self.expect("op", ")")
            return self.postfix(node)
        if token.kind == "op" and token.value == "{":
            self.advance()
            body = self.expr()
            self.expect("op", "}")
            return Lambda(body)
        if token.kind == "op" and token.value == ".":
            self.advance()
            if self.at("ident"):
                return self.postfix(Dot(self.advance().value))
            return self.postfix(Dot(None))
        raise FormulaSyntaxError(
            f"unexpected {token.value or 'end of expression'!r} at {token.pos}", pos=token.pos
        )

    def postfix(self, node: Node) -> Node:
        while True:
            if self.at("op", "."):
                self.advance()
                name = self.expect("ident").value
                node = Name((*node.parts, name)) if isinstance(node, Name) else Attr(node, name)
            elif self.at("op", "["):
                self.advance()
                index = self.expr()
                self.expect("op", "]")
                node = Index(node, index)
            else:
                return node

    def call(self, name: str) -> Node:
        self.expect("op", "(")
        args: list[Node] = []
        if not self.at("op", ")"):
            args.append(self.expr())
            while self.at("op", ","):
                self.advance()
                args.append(self.expr())
        self.expect("op", ")")
        return self.postfix(Call(name, tuple(args)))


def parse(text: str) -> Node:
    return Parser(text).parse()
