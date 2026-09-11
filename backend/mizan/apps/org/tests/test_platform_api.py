from __future__ import annotations

import json

import pytest
from django.test import Client, RequestFactory

from mizan.apps.org.models import Branch, Department
from mizan.platform.api.errors import Conflict
from mizan.platform.api.idempotency import idempotent
from mizan.platform.api.pagination import CursorParams, paginate

pytestmark = pytest.mark.django_db


def test_root_probes(client: Client) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["database"] is True


def test_api_probes_are_public(client: Client) -> None:
    assert client.get("/api/v1/health").json() == {"status": "ok"}
    assert client.get("/api/v1/ready").json()["status"] == "ready"


def test_openapi_document_is_served(client: Client) -> None:
    doc = client.get("/api/v1/openapi.json").json()
    assert doc["info"]["title"] == "Mizan Labs Platform API"
    assert "/api/v1/me" in doc["paths"]


def test_unauthenticated_call_returns_problem_details(client: Client) -> None:
    response = client.get("/api/v1/me")
    assert response.status_code == 401
    assert response["Content-Type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "unauthorized"
    assert body["message_key"] == "auth.unauthorized"
    assert body["request_id"]
    assert response["X-Request-Id"] == body["request_id"]


def test_me_with_bearer_token(api: Client, staff_user: object) -> None:
    response = api.get("/api/v1/me")
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["email"] == "aicha@mizanlabs.dev"
    assert body["realm"] == "STAFF"
    assert body["tenant_id"] == str(staff_user.tenant_id)  # type: ignore[attr-defined]


def test_request_id_is_echoed_when_provided(client: Client) -> None:
    response = client.get("/health", HTTP_X_REQUEST_ID="req-123")
    assert response["X-Request-Id"] == "req-123"


def test_cursor_pagination_walks_every_row_once(branch: Branch) -> None:
    for i in range(7):
        Department.objects.create(branch=branch, code=f"D{i}")
    seen: list[str] = []
    after: str | None = None
    pages = 0
    while True:
        page = paginate(
            Department.objects.all(), CursorParams(after=after, limit=3), lambda d: d.code
        )
        seen.extend(page["items"])
        pages += 1
        after = page["next"]
        if after is None:
            break
    assert pages == 3
    assert sorted(seen) == [f"D{i}" for i in range(7)]
    assert len(set(seen)) == 7


def test_idempotent_replays_the_stored_response(scoped: object) -> None:
    rf = RequestFactory()
    calls: list[int] = []

    @idempotent
    def create(request: object) -> tuple[int, dict[str, str]]:
        calls.append(1)
        return 201, {"id": "abc"}

    request = rf.post(
        "/api/v1/things", data='{"a":1}', content_type="application/json", HTTP_IDEMPOTENCY_KEY="k1"
    )
    first = create(request)
    assert first == (201, {"id": "abc"})
    replay = create(request)
    assert replay.status_code == 201
    assert replay["Idempotent-Replayed"] == "true"
    assert json.loads(replay.content) == {"id": "abc"}
    assert calls == [1]

    different = rf.post(
        "/api/v1/things", data='{"a":2}', content_type="application/json", HTTP_IDEMPOTENCY_KEY="k1"
    )
    with pytest.raises(Conflict):
        create(different)
