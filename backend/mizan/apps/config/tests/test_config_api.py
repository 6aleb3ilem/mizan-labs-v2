"""Configuration endpoints: the administrator adds a test without a release (SPEC Appendix S)."""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client

from mizan.apps.config.defaults.numbering import install_default_numbering
from mizan.apps.config.defaults.workflows import install_default_workflows

pytestmark = pytest.mark.django_db

PASSWORD = "Passw0rd!Passw0rd"


def _api(user: Any) -> Client:
    token = (
        Client()
        .post(
            "/api/v1/auth/login",
            data={"email": user.email, "password": PASSWORD},
            content_type="application/json",
        )
        .json()["access_token"]
    )
    return Client(HTTP_AUTHORIZATION=f"Bearer {token}")


@pytest.fixture
def admin_api(make_member: Any) -> Client:
    admin, _ = make_member("TENANT_ADMIN", all_branches=True)
    return _api(admin)


def test_numbering_endpoints(admin_api: Client, branch: Any) -> None:
    install_default_numbering(branch)
    listed = admin_api.get(
        f"/api/v1/numbering-schemes?branch_id={branch.id}&applies_to=QUOTE"
    ).json()
    assert listed[0]["preview"].startswith("DV-NKC-")
    scheme_id = listed[0]["id"]
    assert admin_api.post(
        f"/api/v1/numbering-schemes/{scheme_id}/reservations",
        data={"numbers": [listed[0]["preview"]], "reason": "V1"},
        content_type="application/json",
    ).json() == {"reserved": 1}
    assert (
        admin_api.get(f"/api/v1/numbering-schemes/{scheme_id}/preview").json()["next"]
        != listed[0]["preview"]
    )
    bad = admin_api.post(
        "/api/v1/numbering-schemes",
        data={
            "branch_id": str(branch.id),
            "applies_to": "INVOICE",
            "pattern": "FA-{SEQ:5}",
            "gap_policy": "GAP_FREE",
            "allocation": "ON_CREATE",
        },
        content_type="application/json",
    )
    assert bad.status_code == 422
    version = admin_api.post(
        f"/api/v1/numbering-schemes/{scheme_id}/versions",
        data={"pattern": "DEV-{YYYY}-{SEQ:5}"},
        content_type="application/json",
    )
    assert (
        version.status_code == 201
        and version.json()["version"] == 2
        and version.json()["status"] == "DRAFT"
    )
    activated = admin_api.post(f"/api/v1/numbering-schemes/{version.json()['id']}:activate")
    assert activated.json()["status"] == "ACTIVE" and activated.json()["preview"].startswith("DEV-")


def test_vocabulary_and_workflow_endpoints(admin_api: Client, branch: Any) -> None:
    assert "sample_nature" in admin_api.get("/api/v1/vocabularies/kinds").json()
    created = admin_api.post(
        "/api/v1/vocabularies/sample_nature/entries",
        data={
            "code": "LATERITE",
            "labels": {"fr": "Latérite", "en": "Laterite"},
            "colour": "orange",
        },
        content_type="application/json",
    )
    assert created.status_code == 201, created.content
    assert (
        admin_api.get("/api/v1/vocabularies/sample_nature/entries").json()[0]["labels"]["fr"]
        == "Latérite"
    )
    retired = admin_api.post(
        f"/api/v1/vocabularies/sample_nature/entries/{created.json()['id']}:retire"
    ).json()
    assert retired["active"] is False and "used_by" in retired
    assert admin_api.get("/api/v1/vocabularies/sample_nature/entries").json() == []
    assert (
        admin_api.post(
            "/api/v1/vocabularies/nope/entries",
            data={"code": "X1", "labels": {"fr": "x"}},
            content_type="application/json",
        ).status_code
        == 422
    )

    install_default_workflows()
    catalogue = admin_api.get("/api/v1/workflows/semantics").json()
    assert (
        catalogue["semantics"]["QUOTE"][0] == "DRAFT" and "reason_required" in catalogue["guards"]
    )
    quote = admin_api.get("/api/v1/workflows?kind=QUOTE").json()[0]
    assert quote["status"] == "ACTIVE" and len(quote["states"]) == 9
    assert quote["states"][0]["labels"] == {"fr": "Brouillon", "en": "Draft"}
    path = admin_api.post(
        f"/api/v1/workflows/{quote['id']}:simulate",
        data={"actions": ["quote.submit", "quote.approve"]},
        content_type="application/json",
    ).json()
    assert [p.get("state") for p in path] == ["DRAFT", "PENDING_APPROVAL", "SENT"]
    draft = admin_api.post(f"/api/v1/workflows/{quote['id']}/versions").json()
    assert draft["version"] == 2 and draft["status"] == "DRAFT"
    definition = {
        "states": [s | {"labels": s["labels"]} for s in draft["states"]],
        "transitions": [
            {
                "from_code": "DRAFT",
                "to_code": "SENT",
                "required_action": "quote.submit",
                "guards": ["has_billable_lines"],
                "effects": ["emit(quote.sent)"],
                "labels": {"fr": "Envoyer", "en": "Send"},
            }
        ],
    }
    replaced = admin_api.put(
        f"/api/v1/workflows/{draft['id']}/definition",
        data=definition,
        content_type="application/json",
    )
    assert replaced.status_code == 200, replaced.content
    assert len(replaced.json()["transitions"]) == 1
    assert admin_api.post(f"/api/v1/workflows/{draft['id']}:validate").json() == []
    activated = admin_api.post(f"/api/v1/workflows/{draft['id']}:activate").json()
    assert activated["status"] == "ACTIVE"
    assert admin_api.get(f"/api/v1/workflows/{quote['id']}").json()["status"] == "RETIRED"


def test_payment_terms_endpoints(admin_api: Client, branch: Any) -> None:
    bad = admin_api.post(
        "/api/v1/payment-terms-templates",
        data={
            "branch_id": str(branch.id),
            "code": "HALF",
            "labels": {"fr": "x"},
            "milestones": [{"label": {"fr": "A"}, "percent": 60, "trigger": "ON_ACCEPTANCE"}],
        },
        content_type="application/json",
    )
    assert bad.status_code == 422
    ok = admin_api.post(
        "/api/v1/payment-terms-templates",
        data={
            "branch_id": str(branch.id),
            "code": "30_70",
            "labels": {"fr": "30/70", "en": "30/70"},
            "is_default": True,
            "milestones": [
                {"label": {"fr": "A"}, "percent": 30, "trigger": "ON_ACCEPTANCE"},
                {
                    "label": {"fr": "B"},
                    "percent": 70,
                    "trigger": "ON_REPORT",
                    "due_days_after_trigger": 30,
                },
            ],
        },
        content_type="application/json",
    )
    assert ok.status_code == 201, ok.content
    amounts = admin_api.get(
        f"/api/v1/payment-terms-templates/{ok.json()['id']}/amounts?total=60610.00"
    ).json()
    assert amounts == ["18183.00", "42427.00"]


def test_administrator_adds_a_test_without_a_release(admin_api: Client, branch: Any) -> None:
    """Appendix S: create LOS_ANGELES, sandbox it, activate it, create the service, resolve its price."""
    category = admin_api.post(
        "/api/v1/service-categories",
        data={"code": "TESTS.AGGREGATES", "labels": {"fr": "Granulats", "en": "Aggregates"}},
        content_type="application/json",
    )
    assert category.status_code == 201, category.content
    definition = {
        "code": "LOS_ANGELES",
        "labels": {"fr": "Los Angeles", "en": "Los Angeles abrasion"},
        "category_id": category.json()["id"],
        "unit_under_test": "SAMPLE",
        "scheduling": {"type": "TURNAROUND", "business_days": 3},
        "inputs": [
            {
                "key": "mass_initial_g",
                "type": "number",
                "unit": "g",
                "level": "PER_RUN",
                "required": True,
            },
            {
                "key": "mass_retained_g",
                "type": "number",
                "unit": "g",
                "level": "PER_RUN",
                "required": True,
            },
        ],
        "computed": [
            {
                "key": "la_pct",
                "unit": "%",
                "level": "PER_RUN",
                "precision": 1,
                "formula": "(inputs.mass_initial_g - inputs.mass_retained_g) / inputs.mass_initial_g * 100",
            }
        ],
        "rules": [
            {
                "code": "LA_TOO_HIGH",
                "effect": "FLAG",
                "expression": "computed.la_pct > 40",
                "labels": {"fr": "LA élevé", "en": "High LA"},
            }
        ],
        "unit_of_sale": "PER_SAMPLE",
    }
    broken = admin_api.post(
        "/api/v1/test-definitions",
        data={
            **definition,
            "computed": [
                {"key": "la_pct", "level": "PER_RUN", "formula": "inputs.mass_initial_g / "}
            ],
        },
        content_type="application/json",
    )
    assert (
        broken.status_code == 422 and broken.json()["details"][0]["msg"] == "formula.syntax_error"
    )
    sandbox = admin_api.post(
        "/api/v1/test-definitions:sandbox",
        data={
            "definition": definition,
            "data": {"run": {"mass_initial_g": 5000, "mass_retained_g": 2900}},
        },
        content_type="application/json",
    )
    assert sandbox.status_code == 200, sandbox.content
    assert sandbox.json()["run_computed"]["la_pct"] == "42.0" and [
        f["code"] for f in sandbox.json()["flags"]
    ] == ["LA_TOO_HIGH"]
    created = admin_api.post(
        "/api/v1/test-definitions", data=definition, content_type="application/json"
    )
    assert created.status_code == 201, created.content
    definition_id = created.json()["id"]
    assert created.json()["status"] == "DRAFT"
    assert (
        admin_api.post(f"/api/v1/test-definitions/{definition_id}:activate").json()["status"]
        == "ACTIVE"
    )
    v2 = admin_api.post(
        f"/api/v1/test-definitions/{definition_id}/versions",
        data={"rules": []},
        content_type="application/json",
    )
    assert (
        v2.status_code == 201
        and v2.json()["version"] == 2
        and v2.json()["labels"]["en"] == "Los Angeles abrasion"
    )
    assert len(admin_api.get("/api/v1/test-definitions").json()) == 1
    assert len(admin_api.get("/api/v1/test-definitions?all_versions=true").json()) == 2

    service = admin_api.post(
        "/api/v1/services",
        data={
            "category_id": category.json()["id"],
            "code": "LOS_ANGELES",
            "labels": {"fr": "Essai Los Angeles", "en": "Los Angeles test"},
            "kind": "LAB_TEST",
            "unit_of_sale": "PER_SAMPLE",
            "test_definition_code": "LOS_ANGELES",
        },
        content_type="application/json",
    )
    assert service.status_code == 201, service.content
    price_list = admin_api.post(
        "/api/v1/price-lists",
        data={
            "branch_id": str(branch.id),
            "code": "BASE_2026",
            "labels": {"fr": "Tarif 2026"},
            "currency": "MRU",
            "valid_from": "2026-01-01",
        },
        content_type="application/json",
    )
    assert price_list.status_code == 201, price_list.content
    imported = admin_api.post(
        f"/api/v1/price-lists/{price_list.json()['id']}/prices:import",
        data={
            "rows": [
                {"service_code": "LOS_ANGELES", "unit_price": "45000.00"},
                {"service_code": "NOPE", "unit_price": "1"},
            ]
        },
        content_type="application/json",
    ).json()
    assert imported["imported"] == 0 and imported["errors"][0]["row"] == 2  # transactional per file
    imported = admin_api.post(
        f"/api/v1/price-lists/{price_list.json()['id']}/prices:import",
        data={"rows": [{"service_code": "LOS_ANGELES", "unit_price": "45000.00"}]},
        content_type="application/json",
    ).json()
    assert imported == {"imported": 1, "errors": []}
    resolved = admin_api.get(
        f"/api/v1/prices/resolve?service_id={service.json()['id']}&branch_id={branch.id}&on=2026-09-11"
    ).json()
    assert resolved["unit_price"] == "45000.00" and resolved["currency"] == "MRU"
    tax = admin_api.post(
        "/api/v1/tax-rules",
        data={
            "branch_id": str(branch.id),
            "code": "TVA16",
            "labels": {"fr": "TVA 16 %", "en": "VAT 16 %"},
            "rate": "16.00",
            "applies_to_kinds": ["LAB_TEST"],
        },
        content_type="application/json",
    )
    assert tax.status_code == 201, tax.content
    assert admin_api.get(f"/api/v1/tax-rules?branch_id={branch.id}").json()[0]["rate"] == "16.00"


def test_configuration_is_denied_to_business_roles(make_member: Any, branch: Any) -> None:
    technician, _ = make_member("TECHNICIAN")
    api = _api(technician)
    assert api.get("/api/v1/test-definitions").status_code == 403
    assert (
        api.post("/api/v1/tax-rules", data={}, content_type="application/json").status_code == 403
    )
