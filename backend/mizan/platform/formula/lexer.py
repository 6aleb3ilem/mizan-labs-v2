from __future__ import annotations

import re
from dataclasses import dataclass

from mizan.platform.formula.errors import FormulaSyntaxError

_TOKEN_RE = re.compile(
    r"""
    (?P<ws>\s+)
  | (?P<number>\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)
  | (?P<string>'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")
  | (?P<ident>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op>==|!=|<=|>=|[-+*/%^<>()\[\]{},.?:])
    """,
    re.X,
)

MAX_TOKENS = 2000


@dataclass(frozen=True, slots=True)
class Token:
    kind: str  # number | string | ident | op | eof
    value: str
    pos: int


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    while pos < len(text):
        match = _TOKEN_RE.match(text, pos)
        if match is None:
            raise FormulaSyntaxError(f"unexpected character {text[pos]!r} at {pos}", pos=pos)
        kind = match.lastgroup or ""
        if kind != "ws":
            value = match.group()
            if kind == "string":
                value = bytes(value[1:-1], "utf-8").decode("unicode_escape")
            tokens.append(Token(kind, value, pos))
            if len(tokens) > MAX_TOKENS:
                raise FormulaSyntaxError("expression too long", limit=MAX_TOKENS)
        pos = match.end()
    tokens.append(Token("eof", "", pos))
    return tokens
