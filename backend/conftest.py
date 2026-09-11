"""Shared fixtures: tenants, scopes, branches, users and an authenticated API client."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from django.test import Client

from mizan.apps.identity.models import Membership, Role, User
from mizan.apps.identity.roles import install_default_roles
from mizan.apps.identity.services import add_membership
from mizan.platform.db.tenancy import platform_scope, tenant_scope


@pytest.fixture(autouse=True)
def _isolated_files(settings: Any, tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """Signing keys and object storage live in a temporary directory during tests."""
    from mizan.platform import storage

    root = tmp_path_factory.mktemp("mizan")
    settings.MIZAN_SIGNING_LOCAL_DIR = root / "keys"
    settings.MIZAN_STORAGE_LOCAL_ROOT = root / "storage"
    storage.documents_storage.cache_clear()
    storage.attachments_storage.cache_clear()
    yield
    storage.documents_storage.cache_clear()
    storage.attachments_storage.cache_clear()


@pytest.fixture(autouse=True)
def _clear_cache() -> Iterator[None]:
    """Throttle counters live in the cache; every test starts with a clean slate."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


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
        "aicha@mizanlabs.dev",
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


@pytest.fixture
def roles(branch: Any) -> dict[str, Role]:
    return install_default_roles()


@pytest.fixture
def department(branch: Any) -> Any:
    from mizan.apps.org.models import Department

    return Department.objects.create(branch=branch, code="CONCRETE")


@pytest.fixture
def make_member(
    roles: dict[str, Role], branch: Any, scoped: Any
) -> Callable[..., tuple[User, Membership]]:
    counter = iter(range(1, 10_000))

    def _make(
        role_code: str,
        *,
        branch_id: uuid.UUID | None = None,
        department_id: uuid.UUID | None = None,
        account_id: uuid.UUID | None = None,
        all_branches: bool = False,
        password: str = "Passw0rd!Passw0rd",
    ) -> tuple[User, Membership]:
        n = next(counter)
        realm = "CLIENT" if role_code.startswith("CLIENT") else "STAFF"
        user = User.objects.create_user(
            f"{role_code.lower()}{n}@mizanlabs.dev",
            password,
            tenant_id=scoped.id,
            realm=realm,
            display_name=role_code,
        )
        membership = add_membership(
            user=user,
            role=roles[role_code],
            branch_id=None if all_branches else (branch_id or branch.id),
            department_id=department_id,
            account_id=account_id,
        )
        return user, membership

    return _make
