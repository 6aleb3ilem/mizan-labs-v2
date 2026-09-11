"""SPEC §20.1: every write is audited; the log is append-only; the History tab is scoped."""

from __future__ import annotations

from typing import Any

import pytest
from django.db import DatabaseError, transaction
from django.test import Client

from mizan.apps.audit.models import AuditEvent
from mizan.apps.audit.services import diff, record, snapshot
from mizan.apps.identity.models import User
from mizan.apps.identity.services import create_user, disable_user
from mizan.platform import context

pytestmark = pytest.mark.django_db


def test_record_captures_actor_tenant_and_context(scoped: Any) -> None:
    actor = context.Actor(id=scoped.id, type="USER")
    token = context.current_actor.set(actor)
    try:
        event = record(
            "project", scoped.id, "created", after={"title": "AF-2026-0001"}, extra={"note": "x"}
        )
    finally:
        context.current_actor.reset(token)
    assert event.tenant_id == scoped.id
    assert event.actor_id == scoped.id
    assert event.actor_type == "USER"
    assert event.after == {"title": "AF-2026-0001"}
    assert event.context["note"] == "x"
    assert "request_id" in event.context


def test_audit_events_cannot_be_updated_or_deleted(scoped: Any) -> None:
    event = record("project", scoped.id, "created")
    with pytest.raises(DatabaseError), transaction.atomic():
        AuditEvent.objects.filter(pk=event.pk).update(action="tampered")
    with pytest.raises(DatabaseError), transaction.atomic():
        AuditEvent.objects.filter(pk=event.pk).delete()
    assert AuditEvent.objects.get(pk=event.pk).action == "created"


def test_snapshot_excludes_secrets_and_diff_reports_changes(scoped: Any) -> None:
    user = User.objects.create_user("snap@mizanlabs.dev", "Passw0rd!Passw0rd", tenant_id=scoped.id)
    before = snapshot(user)
    assert "password" not in before
    assert before["email"] == "snap@mizanlabs.dev"
    user.display_name = "Snapper"
    after = snapshot(user)
    assert diff(before, after) == {"display_name": ["", "Snapper"]}


def test_identity_services_are_audited(scoped: Any) -> None:
    user = create_user(email="audited@mizanlabs.dev", display_name="Audited")
    disable_user(user)
    actions = list(
        AuditEvent.objects.filter(aggregate_type="user", aggregate_id=user.id)
        .order_by("at")
        .values_list("action", flat=True)
    )
    assert actions == ["created", "disabled"]
    disabled = AuditEvent.objects.get(aggregate_id=user.id, action="disabled")
    assert diff(disabled.before, disabled.after)["status"] == ["ACTIVE", "DISABLED"]


def test_login_attempts_are_audited(make_member: Any) -> None:
    user, _ = make_member("COMMERCIAL")
    Client().post(
        "/api/v1/auth/login",
        data={"email": user.email, "password": "wrong-wrong-wrong"},
        content_type="application/json",
    )
    Client().post(
        "/api/v1/auth/login",
        data={"email": user.email, "password": "Passw0rd!Passw0rd"},
        content_type="application/json",
    )
    actions = list(
        AuditEvent.objects.filter(aggregate_id=user.id)
        .order_by("at")
        .values_list("action", flat=True)
    )
    assert actions[-2:] == ["login_failed", "login"]
    assert AuditEvent.objects.get(aggregate_id=user.id, action="login").tenant_id == user.tenant_id


def test_history_endpoint_requires_view_on_the_resource(make_member: Any) -> None:
    admin, _ = make_member("TENANT_ADMIN", all_branches=True)
    technician, _ = make_member("TECHNICIAN")
    target = create_user(email="target@mizanlabs.dev")

    def api_for(user: User) -> Client:
        token = (
            Client()
            .post(
                "/api/v1/auth/login",
                data={"email": user.email, "password": "Passw0rd!Passw0rd"},
                content_type="application/json",
            )
            .json()["access_token"]
        )
        return Client(HTTP_AUTHORIZATION=f"Bearer {token}")

    history = api_for(admin).get(f"/api/v1/history/user/{target.id}")
    assert history.status_code == 200
    assert [e["action"] for e in history.json()["items"]] == ["created"]
    assert api_for(technician).get(f"/api/v1/history/user/{target.id}").status_code == 403
    assert api_for(technician).get("/api/v1/audit-events").status_code == 403
    listed = (
        api_for(admin).get("/api/v1/audit-events?aggregate_type=user&action=created&limit=1").json()
    )
    assert len(listed["items"]) == 1
