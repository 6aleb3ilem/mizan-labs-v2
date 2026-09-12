"""Message rendering: Jinja templates in a sandbox, text for SMS/WhatsApp, HTML for e-mail."""

from __future__ import annotations

from typing import Any

from jinja2 import ChainableUndefined, TemplateError
from jinja2.sandbox import SandboxedEnvironment

from mizan.apps.documents.rendering import fmt_date, fmt_money, fmt_number
from mizan.platform.api.errors import UnprocessableEntity


class MessageRenderError(Exception):
    pass


def _environment(*, autoescape: bool) -> SandboxedEnvironment:
    env = SandboxedEnvironment(
        autoescape=autoescape,
        undefined=ChainableUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=False,
    )
    env.filters.update({"money": fmt_money, "number": fmt_number, "date": fmt_date})
    return env


_TEXT = _environment(autoescape=False)
_HTML = _environment(autoescape=True)


def render_text(source: str, context: dict[str, Any]) -> str:
    try:
        return _TEXT.from_string(source).render(**context).strip()
    except TemplateError as exc:
        raise MessageRenderError(str(exc)) from exc


def render_html(source: str, context: dict[str, Any]) -> str:
    try:
        return _HTML.from_string(source).render(**context).strip()
    except TemplateError as exc:
        raise MessageRenderError(str(exc)) from exc


def check_template(subject: str, body: str, html: str, sample: dict[str, Any]) -> None:
    """Compile and render the three parts with sample data; 422 with the error otherwise."""
    for field, source, renderer in (
        ("subject", subject, render_text),
        ("body", body, render_text),
        ("html", html, render_html),
    ):
        if not source:
            continue
        try:
            renderer(source, sample)
        except MessageRenderError as exc:
            raise UnprocessableEntity(
                "notify.template.invalid", details=[{"loc": [field], "msg": str(exc)}]
            ) from exc


def render_message(template: Any, context: dict[str, Any], *, channel: str) -> dict[str, str]:
    """``{subject, body, html}`` for one template row and one context."""
    rendered = {
        "subject": render_text(template.subject, context) if template.subject else "",
        "body": render_text(template.body, context),
        "html": "",
    }
    if channel == "email" and template.html:
        rendered["html"] = render_html(template.html, context)
    return rendered
