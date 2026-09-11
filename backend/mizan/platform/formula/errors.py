from __future__ import annotations


class FormulaError(Exception):
    """Base error; ``message_key`` and ``params`` feed the API problem details."""

    message_key = "formula.error"

    def __init__(self, message: str, **params: object) -> None:
        super().__init__(message)
        self.params = params


class FormulaSyntaxError(FormulaError):
    message_key = "formula.syntax_error"


class MissingValue(FormulaError):
    message_key = "formula.missing_value"


class DivisionByZero(FormulaError):
    message_key = "formula.division_by_zero"


class FormulaLimitExceeded(FormulaError):
    message_key = "formula.limit_exceeded"


class FormulaTypeError(FormulaError):
    message_key = "formula.type_error"
