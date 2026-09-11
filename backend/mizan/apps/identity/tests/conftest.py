from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import pytest

from mizan.apps.identity.models import Membership, Role, User
from mizan.apps.identity.roles import install_default_roles
from mizan.apps.identity.services import add_membership


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
