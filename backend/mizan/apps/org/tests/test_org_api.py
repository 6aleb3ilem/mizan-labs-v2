"""Organisation endpoints: permissions, settings validation, optimistic locking, audit."""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client

from mizan.apps.audit.models import AuditEvent
from mizan.apps.org.models import Branch

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


def test_branch_lifecycle_with_settings_validation_and_audit(
    make_member: Any, branch: Branch
) -> None:
    admin, _ = make_member("TENANT_ADMIN", all_branches=True)
    api = _api(admin)
    created = api.post(
        "/api/v1/branches",
        data={
            "code": "NDB",
            "legal_name": "Mizan Labs Nouadhibou",
            "currency": "MRU",
            "settings": {"invoice_due_days": 45},
        },
        content_type="application/json",
    )
    assert created.status_code == 201, created.content
    body = created.json()
    assert body["settings"]["invoice_due_days"] == 45
    assert body["settings"]["dunning_schedule_days"] == [7, 21, 45]  # defaults materialised
    assert {b["code"] for b in api.get("/api/v1/branches").json()} == {"NKC", "NDB"}

    invalid = api.patch(
        f"/api/v1/branches/{body['id']}",
        data={"settings": {"invoice_due_days": -1}},
        content_type="application/json",
    )
    assert invalid.status_code == 422
    assert invalid.json()["details"][0]["loc"] == ["settings", "invoice_due_days"]

    stale = api.patch(
        f"/api/v1/branches/{body['id']}",
        data={"phone": "+222", "row_version": 99},
        content_type="application/json",
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "concurrent_update"

    ok = api.patch(
        f"/api/v1/branches/{body['id']}",
        data={"phone": "+222 45 25 00 00", "row_version": 1},
        content_type="application/json",
    )
    assert ok.status_code == 200
    assert ok.json()["row_version"] == 2
    actions = list(
        AuditEvent.objects.filter(aggregate_type="branch", aggregate_id=body["id"])
        .order_by("at")
        .values_list("action", flat=True)
    )
    assert actions == ["created", "updated"]


def test_branch_configuration_is_denied_to_business_roles(make_member: Any) -> None:
    commercial, _ = make_member("COMMERCIAL")
    api = _api(commercial)
    assert api.get("/api/v1/branches").status_code == 403
    assert (
        api.post(
            "/api/v1/branches",
            data={"code": "X", "legal_name": "X", "currency": "MRU"},
            content_type="application/json",
        ).status_code
        == 403
    )


def test_branch_manager_sees_only_own_branch(make_member: Any, branch: Branch) -> None:
    other = Branch.objects.create(code="NDB", legal_name="Other", currency="MRU")
    manager, _ = make_member("BRANCH_MANAGER", branch_id=branch.id)
    api = _api(manager)
    listed = api.get("/api/v1/branches").json()
    assert [b["code"] for b in listed] == ["NKC"]
    assert other.code == "NDB"


def test_departments_signatories_and_treasury(make_member: Any, branch: Branch) -> None:
    admin, _ = make_member("TENANT_ADMIN", all_branches=True)
    api = _api(admin)
    dep = api.post(
        "/api/v1/departments",
        data={
            "branch_id": str(branch.id),
            "code": "CONCRETE",
            "labels": {"fr": "Béton", "en": "Concrete"},
            "colour": "blue",
        },
        content_type="application/json",
    )
    assert dep.status_code == 201, dep.content
    assert dep.json()["labels"] == {"fr": "Béton", "en": "Concrete"}
    dup = api.post(
        "/api/v1/departments",
        data={"branch_id": str(branch.id), "code": "CONCRETE", "labels": {"fr": "x"}},
        content_type="application/json",
    )
    assert dup.status_code == 409
    renamed = api.patch(
        f"/api/v1/departments/{dep.json()['id']}",
        data={"labels": {"en": "Concrete lab"}},
        content_type="application/json",
    )
    assert renamed.json()["labels"]["en"] == "Concrete lab"
    assert renamed.json()["labels"]["fr"] == "Béton"

    bad_sig = api.post(
        "/api/v1/signatories",
        data={
            "branch_id": str(branch.id),
            "display_name": "Directeur",
            "mode": "DIGITAL_CERTIFICATE",
            "document_kinds": ["REPORT"],
        },
        content_type="application/json",
    )
    assert bad_sig.status_code == 422
    sig = api.post(
        "/api/v1/signatories",
        data={
            "branch_id": str(branch.id),
            "display_name": "Directeur",
            "title": "Directeur général",
            "mode": "IMAGE",
            "document_kinds": ["REPORT", "QUOTE"],
        },
        content_type="application/json",
    )
    assert sig.status_code == 201, sig.content
    assert sig.json()["has_signature_image"] is False
    assert (
        api.get(f"/api/v1/signatories?branch_id={branch.id}").json()[0]["display_name"]
        == "Directeur"
    )

    finance, _ = make_member("FINANCE", branch_id=branch.id)
    fin = _api(finance)
    acc = fin.post(
        "/api/v1/treasury-accounts",
        data={
            "branch_id": str(branch.id),
            "type": "BANK",
            "label": "BMCI courant",
            "iban": "MR13...",
            "currency": "MRU",
            "printed_on_invoices": True,
        },
        content_type="application/json",
    )
    assert acc.status_code == 201, acc.content
    invalid = fin.post(
        "/api/v1/treasury-accounts",
        data={"branch_id": str(branch.id), "type": "WALLET", "label": "x", "currency": "MRU"},
        content_type="application/json",
    )
    assert invalid.status_code == 422
    assert (
        fin.patch(
            f"/api/v1/treasury-accounts/{acc.json()['id']}",
            data={"active": False},
            content_type="application/json",
        ).json()["active"]
        is False
    )
    assert api.get("/api/v1/tenant").json()["code"] == "T1"


def test_platform_operator_creates_a_tenant_with_its_administrator(db: Any) -> None:
    from mizan.apps.identity.models import Membership, User
    from mizan.platform.db.tenancy import platform_scope, tenant_scope

    with platform_scope():
        operator = User.objects.create_superuser("ops@mizan-platform.dev", PASSWORD)
    api = _api(operator)
    created = api.post(
        "/api/v1/platform/tenants",
        data={
            "code": "ACME",
            "name": "Acme Labs",
            "admin_email": "admin@acme-labs.dev",
            "admin_temporary_password": "Temporary-Pass-123",
        },
        content_type="application/json",
    )
    assert created.status_code == 201, created.content
    tenant_id = created.json()["id"]
    with tenant_scope(tenant_id):
        admin = User.objects.get(email="admin@acme-labs.dev")
        assert admin.must_change_password is True
        assert Membership.objects.get(user=admin).role.code == "TENANT_ADMIN"
    assert (
        api.post(
            "/api/v1/platform/tenants",
            data={
                "code": "ACME",
                "name": "Dup",
                "admin_email": "x@acme-labs.dev",
                "admin_temporary_password": "Temporary-Pass-123",
            },
            content_type="application/json",
        ).status_code
        == 409
    )
