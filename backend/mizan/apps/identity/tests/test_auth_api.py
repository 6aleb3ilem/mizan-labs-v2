"""Sessions, profile, permissions and user administration through the API."""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client

from mizan.apps.identity.models import RefreshToken, User

pytestmark = pytest.mark.django_db

PASSWORD = "Passw0rd!Passw0rd"


def _login(client: Client, email: str, password: str = PASSWORD) -> Any:
    return client.post(
        "/api/v1/auth/login",
        data={"email": email, "password": password},
        content_type="application/json",
    )


def _bearer(token: str) -> Client:
    return Client(HTTP_AUTHORIZATION=f"Bearer {token}")


def test_login_returns_tokens_and_profile(make_member: Any) -> None:
    user, _membership = make_member("COMMERCIAL")
    response = _login(Client(), user.email)
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == 900
    assert body["user"]["email"] == user.email
    assert body["user"]["memberships"][0]["role_code"] == "COMMERCIAL"
    api = _bearer(body["access_token"])
    me = api.get("/api/v1/me").json()
    assert me["id"] == str(user.id)
    perms = api.get("/api/v1/me/permissions").json()
    assert perms["tenant_id"] == str(user.tenant_id)
    assert {"resource": "quote", "action": "create"}.items() <= {
        k: v
        for g in perms["grants"]
        if g["resource"] == "quote" and g["action"] == "create"
        for k, v in g.items()
    }.items()


def test_wrong_password_is_rejected_without_enumeration(make_member: Any) -> None:
    user, _ = make_member("COMMERCIAL")
    wrong = _login(Client(), user.email, "nope-nope-nope")
    unknown = _login(Client(), "ghost@mizanlabs.dev", "nope-nope-nope")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["code"] == unknown.json()["code"] == "invalid_credentials"


def test_disabled_user_cannot_log_in(make_member: Any) -> None:
    from mizan.apps.identity.services import disable_user

    user, _ = make_member("COMMERCIAL")
    disable_user(user)
    assert _login(Client(), user.email).status_code == 403


def test_refresh_rotation_and_reuse_detection(make_member: Any) -> None:
    user, _ = make_member("COMMERCIAL")
    first = _login(Client(), user.email).json()
    rotated = Client().post(
        "/api/v1/auth/refresh",
        data={"refresh_token": first["refresh_token"]},
        content_type="application/json",
    )
    assert rotated.status_code == 200
    second = rotated.json()
    assert second["refresh_token"] != first["refresh_token"]
    assert _bearer(second["access_token"]).get("/api/v1/me").status_code == 200

    reuse = Client().post(
        "/api/v1/auth/refresh",
        data={"refresh_token": first["refresh_token"]},
        content_type="application/json",
    )
    assert reuse.status_code == 401
    assert reuse.json()["code"] == "refresh_token_reused"
    # the theft signal revoked the whole session, including the freshly rotated token
    again = Client().post(
        "/api/v1/auth/refresh",
        data={"refresh_token": second["refresh_token"]},
        content_type="application/json",
    )
    assert again.status_code == 401


def test_logout_revokes_the_session(make_member: Any) -> None:
    user, _ = make_member("COMMERCIAL")
    tokens = _login(Client(), user.email).json()
    assert (
        Client()
        .post(
            "/api/v1/auth/logout",
            data={"refresh_token": tokens["refresh_token"]},
            content_type="application/json",
        )
        .status_code
        == 200
    )
    assert (
        Client()
        .post(
            "/api/v1/auth/refresh",
            data={"refresh_token": tokens["refresh_token"]},
            content_type="application/json",
        )
        .status_code
        == 401
    )
    assert RefreshToken.objects.filter(user=user, revoked_at__isnull=True).count() == 0


def test_change_password_enforces_policy_and_revokes_sessions(make_member: Any) -> None:
    user, _ = make_member("COMMERCIAL")
    tokens = _login(Client(), user.email).json()
    api = _bearer(tokens["access_token"])
    weak = api.post(
        "/api/v1/auth/change-password",
        data={"current_password": PASSWORD, "new_password": "1234567890"},
        content_type="application/json",
    )
    assert weak.status_code == 422
    ok = api.post(
        "/api/v1/auth/change-password",
        data={"current_password": PASSWORD, "new_password": "Correct-Horse-Battery-9"},
        content_type="application/json",
    )
    assert ok.status_code == 200
    assert _login(Client(), user.email, "Correct-Horse-Battery-9").status_code == 200
    assert (
        Client()
        .post(
            "/api/v1/auth/refresh",
            data={"refresh_token": tokens["refresh_token"]},
            content_type="application/json",
        )
        .status_code
        == 401
    )


def test_user_administration_requires_the_grant(make_member: Any) -> None:
    admin, _ = make_member("TENANT_ADMIN", all_branches=True)
    technician, _ = make_member("TECHNICIAN")
    admin_api = _bearer(_login(Client(), admin.email).json()["access_token"])
    tech_api = _bearer(_login(Client(), technician.email).json()["access_token"])

    payload = {
        "email": "new.user@mizanlabs.dev",
        "display_name": "New User",
        "temporary_password": "Temp-Password-123",
    }
    denied = tech_api.post("/api/v1/users", data=payload, content_type="application/json")
    assert denied.status_code == 403
    assert denied.json()["message_key"] == "authz.forbidden"
    assert denied.json()["params"] == {"action": "user.create"}

    created = admin_api.post(
        "/api/v1/users", data=payload, content_type="application/json", HTTP_IDEMPOTENCY_KEY="u-1"
    )
    assert created.status_code == 201, created.content
    assert created.json()["must_change_password"] is True
    replay = admin_api.post(
        "/api/v1/users", data=payload, content_type="application/json", HTTP_IDEMPOTENCY_KEY="u-1"
    )
    assert replay.status_code == 201
    assert replay["Idempotent-Replayed"] == "true"
    assert User.objects.filter(email="new.user@mizanlabs.dev").count() == 1

    listed = admin_api.get("/api/v1/users?limit=2").json()
    assert len(listed["items"]) == 2
    assert listed["next"]

    roles = admin_api.get("/api/v1/roles").json()
    assert {r["code"] for r in roles} >= {"TECHNICIAN", "TENANT_ADMIN"}
    view_as = admin_api.get(f"/api/v1/users/{technician.id}/effective-permissions").json()
    assert any(g["resource"] == "test_run" and g["action"] == "edit" for g in view_as["grants"])


def test_role_lifecycle_through_the_api(make_member: Any) -> None:
    admin, _ = make_member("TENANT_ADMIN", all_branches=True)
    api = _bearer(_login(Client(), admin.email).json()["access_token"])
    created = api.post(
        "/api/v1/roles",
        data={
            "code": "QUALITY_LEAD",
            "labels": {"fr": "Responsable qualité", "en": "Quality lead"},
            "grants": [
                {"resource": "test_definition", "action": "configure", "scope": "ALL_BRANCHES"}
            ],
        },
        content_type="application/json",
    )
    assert created.status_code == 201, created.content
    role_id = created.json()["id"]
    bad = api.put(
        f"/api/v1/roles/{role_id}/grants",
        data=[{"resource": "quote", "action": "teleport", "scope": "OWN_BRANCH"}],
        content_type="application/json",
    )
    assert bad.status_code == 422
    replaced = api.put(
        f"/api/v1/roles/{role_id}/grants",
        data=[{"resource": "quote", "action": "view", "scope": "OWN_BRANCH"}],
        content_type="application/json",
    )
    assert [g["action"] for g in replaced.json()["grants"]] == ["view"]
    retired = api.post(f"/api/v1/roles/{role_id}:retire")
    assert retired.json()["status"] == "RETIRED"
