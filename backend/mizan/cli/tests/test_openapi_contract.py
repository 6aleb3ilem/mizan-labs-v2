"""The OpenAPI document `export_openapi` writes is a contract, and the generated client is only as honest as it is.

Ninja registers response and body schemas in `components/schemas` under the schema class's bare
name. Two apps that each define a `TemplateOut` therefore collide: one silently wins, every
operation referencing the other is documented with the wrong shape, and `openapi-typescript`
hands the front-end a type that type-checks against a lie. That is exactly what happened between
`documents` (document templates) and `notify` (message templates), and it is invisible until a
screen is written against the generated client.

These tests make the collision a build failure instead of a debugging session.
"""

from __future__ import annotations

from typing import Any

import pytest

from mizan.config.api import api


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    return api.get_openapi_schema()


def _schema_names(node: Any) -> set[str]:
    """Every `#/components/schemas/X` reachable from a node."""
    found: set[str] = set()
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            found.add(ref.rsplit("/", 1)[-1])
        for value in node.values():
            found |= _schema_names(value)
    elif isinstance(node, list):
        for value in node:
            found |= _schema_names(value)
    return found


def test_no_operation_references_a_schema_that_does_not_exist(document: dict[str, Any]) -> None:
    defined = set(document["components"]["schemas"])
    referenced = _schema_names(document["paths"])
    assert referenced <= defined, f"dangling refs: {sorted(referenced - defined)}"


def test_every_schema_name_is_defined_by_exactly_one_class() -> None:
    """A duplicate class name is the collision itself, caught before it reaches the document."""
    from ninja import Schema

    def descendants(cls: type[Schema]) -> list[type[Schema]]:
        out: list[type[Schema]] = []
        for subclass in cls.__subclasses__():
            out.append(subclass)
            out.extend(descendants(subclass))
        return out

    by_name: dict[str, set[str]] = {}
    for schema in descendants(Schema):
        by_name.setdefault(schema.__name__, set()).add(schema.__module__)

    clashes = {name: sorted(modules) for name, modules in by_name.items() if len(modules) > 1}
    assert not clashes, (
        "schema class names collide in components/schemas; rename them so each is unique: "
        f"{clashes}"
    )


def test_document_and_message_templates_keep_their_own_shapes(document: dict[str, Any]) -> None:
    """The regression that motivated this file."""
    schemas = document["components"]["schemas"]
    document_template = schemas["DocumentTemplateOut"]["properties"]
    message_template = schemas["TemplateOut"]["properties"]

    # A document template is HTML rendered to a sealed PDF; a message template is a channel body.
    assert {"kind", "html", "css", "sample_data"} <= set(document_template)
    assert {"channel", "subject", "body"} <= set(message_template)
    assert "channel" not in document_template
    assert "css" not in message_template
