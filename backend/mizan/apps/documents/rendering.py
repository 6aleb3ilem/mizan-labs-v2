"""HTML rendering in a Jinja sandbox and PDF/A-3b output with WeasyPrint (SPEC §18.1)."""

from __future__ import annotations

import datetime as dt
import logging
from decimal import Decimal
from typing import Any

from jinja2 import ChainableUndefined
from jinja2.sandbox import SandboxedEnvironment

log = logging.getLogger("mizan.documents.rendering")
NARROW_NBSP = chr(0x202F)  # French thousands separator


def fmt_money(value: Any, currency: str = "", locale: str = "fr") -> str:
    if value is None or value == "":
        return ""
    amount = Decimal(str(value))
    whole, _, frac = f"{amount:,.2f}".partition(".")
    if locale.startswith("fr"):
        whole = whole.replace(",", NARROW_NBSP)
        text = f"{whole},{frac}"
    else:
        text = f"{whole}.{frac}"
    return f"{text} {currency}".strip()


def fmt_number(value: Any, digits: int = 1, locale: str = "fr") -> str:
    if value is None or value == "":
        return ""
    text = f"{Decimal(str(value)):,.{digits}f}"
    if locale.startswith("fr"):
        text = text.replace(",", NARROW_NBSP).replace(".", ",")
    return text


def fmt_date(value: Any, locale: str = "fr") -> str:
    if not value:
        return ""
    if isinstance(value, str):
        value = dt.date.fromisoformat(value[:10])
    if isinstance(value, dt.datetime):
        value = value.date()
    return str(value.strftime("%d/%m/%Y") if locale.startswith("fr") else value.isoformat())


def build_environment() -> SandboxedEnvironment:
    env = SandboxedEnvironment(
        autoescape=True, undefined=ChainableUndefined, trim_blocks=True, lstrip_blocks=True
    )
    env.filters.update({"money": fmt_money, "number": fmt_number, "date": fmt_date})
    return env


_ENV = build_environment()


def render_html(source: str, context: dict[str, Any]) -> str:
    template = _ENV.from_string(source)
    return template.render(**context)


def render_pdf(
    html: str, css: str = "", *, base_url: str | None = None, pdf_a: bool = True
) -> bytes:
    from weasyprint import CSS, HTML

    stylesheets = [CSS(string=css)] if css else []
    document = HTML(string=html, base_url=base_url)
    options: dict[str, Any] = {}
    if pdf_a:
        options["pdf_variant"] = "pdf/a-3b"
    result: bytes = document.write_pdf(stylesheets=stylesheets, **options)
    return result
