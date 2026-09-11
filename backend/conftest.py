"""Shared fixtures: tenants, scopes, branches, users and an authenticated API client."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from django.test import Client

from mizan.platform.db.tenancy import platform_scope, tenant_scope


@pytest.fixture
def tenant(db: Any) -> Any:
    from mizan.apps.org.models import Tenant

    with platform_scope():
        return Tenant.objects.create(code="T1", name="Tenant One")


@pytest.fixture
def other_tenant(db: Any) -> Any:
    from mizan.apps.org.models import Tenant

    with platform_scope():
        return Tenant.objects.create(code="T2", name="Tenant Two")


@pytest.fixture
def scoped(tenant: Any) -> Iterator[Any]:
    """The test runs inside ``tenant_scope(tenant.id)``."""
    with tenant_scope(tenant.id):
        yield tenant


@pytest.fixture
def branch(scoped: Any) -> Any:
    from mizan.apps.org.models import Branch

    return Branch.objects.create(
        code="NKC",
        legal_name="Mizan Labs Nouakchott",
        currency="MRU",
        timezone="Africa/Nouakchott",
        locales=["fr", "en"],
        working_days=[1, 2, 3, 4, 5, 6],
    )


@pytest.fixture
def staff_user(scoped: Any) -> Any:
    from mizan.apps.identity.models import User

    return User.objects.create_user(
        "aicha@mizanlabs.test",
        "Passw0rd!Passw0rd",
        tenant_id=scoped.id,
        display_name="Aïcha",
        realm="STAFF",
    )


@pytest.fixture
def access_token(staff_user: Any) -> str:
    from mizan.platform.auth.jwt import issue_access_token

    return issue_access_token(
        user_id=staff_user.id,
        tenant_id=staff_user.tenant_id,
        realm="STAFF",
        session_id=uuid.uuid4(),
    )


@pytest.fixture
def api(access_token: str) -> Client:
    return Client(HTTP_AUTHORIZATION=f"Bearer {access_token}", HTTP_X_MIZAN_APP="back-office")
