"""Authorization cases generated from the default permission grid (SPEC Appendix T, §9.3)."""

from __future__ import annotations

from typing import Any

import pytest

from mizan.apps.identity.authz import resolve_permissions
from mizan.apps.identity.roles import DEFAULT_ROLES, expand

pytestmark = pytest.mark.django_db

# (role, resource, action, allowed)
CASES: list[tuple[str, str, str, bool]] = [
    ("COMMERCIAL", "quote", "create", True),
    ("COMMERCIAL", "quote", "approve", False),
    ("COMMERCIAL", "acceptance", "create", True),
    ("COMMERCIAL", "invoice", "view", True),
    ("COMMERCIAL", "invoice", "create", False),
    ("COMMERCIAL", "test_run", "edit", False),
    ("COMMERCIAL_MANAGER", "quote", "approve", True),
    ("COMMERCIAL_MANAGER", "contract", "sign", True),
    ("COMMERCIAL_MANAGER", "report", "issue", False),
    ("LAB_RECEPTION", "intake", "create", True),
    ("LAB_RECEPTION", "specimen", "change_stage", True),
    ("LAB_RECEPTION", "quote", "view", False),
    ("LAB_RECEPTION", "measurement", "create", False),
    ("TECHNICIAN", "test_run", "edit", True),
    ("TECHNICIAN", "measurement", "create", True),
    ("TECHNICIAN", "test_run", "assign", False),
    ("TECHNICIAN", "quote", "view", False),
    ("TECHNICIAN", "invoice", "view", False),
    ("TECHNICIAN", "report", "issue", False),
    ("LAB_SUPERVISOR", "test_run", "review_results", True),
    ("LAB_SUPERVISOR", "test_run", "override_computed_value", True),
    ("LAB_SUPERVISOR", "report", "issue", True),
    ("LAB_SUPERVISOR", "test_run", "cancel", True),
    ("LAB_SUPERVISOR", "quote", "view", False),
    ("LAB_SUPERVISOR", "invoice", "issue", False),
    ("FINANCE", "invoice", "issue", True),
    ("FINANCE", "credit_note", "create", True),
    ("FINANCE", "payment", "allocate_payment", True),
    ("FINANCE", "treasury_entry", "create", True),
    ("FINANCE", "quote", "create", False),
    ("FINANCE", "test_run", "view", False),
    ("ASSETS", "rental", "create", True),
    ("ASSETS", "transfer", "approve", True),
    ("ASSETS", "invoice", "view", False),
    ("BRANCH_MANAGER", "quote", "approve", True),
    ("BRANCH_MANAGER", "report", "issue", True),
    ("BRANCH_MANAGER", "invoice", "issue", True),
    ("BRANCH_MANAGER", "payment", "view", True),
    ("BRANCH_MANAGER", "numbering_scheme", "view", True),
    ("BRANCH_MANAGER", "numbering_scheme", "configure", False),
    ("BRANCH_MANAGER", "invoice", "create", False),
    ("TENANT_ADMIN", "numbering_scheme", "configure", True),
    ("TENANT_ADMIN", "workflow", "configure", True),
    ("TENANT_ADMIN", "role", "configure", True),
    ("TENANT_ADMIN", "user", "impersonate_view", True),
    ("TENANT_ADMIN", "project", "view", False),  # no business data by default
    ("TENANT_ADMIN", "quote", "view", False),
    ("CLIENT_USER", "project", "view", True),
    ("CLIENT_USER", "report", "print", True),
    ("CLIENT_USER", "acceptance", "create", True),
    ("CLIENT_USER", "quote", "create", False),
    ("CLIENT_USER", "contact", "create", False),
    ("CLIENT_ADMIN", "contact", "create", True),
    ("CLIENT_ADMIN", "user", "create", True),
    ("CLIENT_ADMIN", "invoice", "issue", False),
]


@pytest.mark.parametrize(
    ("role", "resource", "action", "allowed"),
    CASES,
    ids=[f"{r}-{res}.{a}" for r, res, a, _ in CASES],
)
def test_default_role_grid(
    make_member: Any, role: str, resource: str, action: str, allowed: bool
) -> None:
    user, _ = make_member(role, account_id=None)
    perms = resolve_permissions(user.id, user.tenant_id)
    assert perms.allows(resource, action) is allowed


FIELD_GROUP_CASES: list[tuple[str, str, set[str]]] = [
    ("COMMERCIAL", "project", {"commercial", "financial", "client_contact"}),
    ("LAB_RECEPTION", "project", set()),
    ("TECHNICIAN", "project", set()),
    ("LAB_SUPERVISOR", "work_item", set()),
    ("FINANCE", "project", {"financial"}),
    ("FINANCE", "account", {"financial"}),
    ("BRANCH_MANAGER", "work_item", {"commercial", "financial", "client_contact"}),
    ("CLIENT_USER", "work_item", set()),
    ("LAB_SUPERVISOR", "test_run", {"raw_measurements"}),
    ("TECHNICIAN", "test_run", set()),
]


@pytest.mark.parametrize(
    ("role", "resource", "groups"),
    FIELD_GROUP_CASES,
    ids=[f"{r}-{res}" for r, res, _ in FIELD_GROUP_CASES],
)
def test_field_groups_per_role(
    make_member: Any, role: str, resource: str, groups: set[str]
) -> None:
    user, _ = make_member(role)
    perms = resolve_permissions(user.id, user.tenant_id)
    assert set(perms.field_groups(resource, "view")) == groups


def test_every_template_grant_is_valid_and_scoped() -> None:
    for template in DEFAULT_ROLES:
        rows = expand(template)
        assert rows, template.code
        scopes = {scope for _, _, scope, _ in rows}
        if template.code.startswith("CLIENT"):
            assert scopes == {"OWN_ACCOUNT"}
        elif template.code == "TENANT_ADMIN":
            assert scopes == {"ALL_BRANCHES"}
        else:
            assert "OWN_ACCOUNT" not in scopes


def test_install_is_idempotent(roles: dict[str, Any]) -> None:
    from mizan.apps.identity.models import Grant, Role
    from mizan.apps.identity.roles import install_default_roles

    before = (Role.objects.count(), Grant.objects.count())
    install_default_roles()
    assert (Role.objects.count(), Grant.objects.count()) == before
    assert Role.objects.get(code="TECHNICIAN").label("en") == "Technician"


def test_memberships_are_unions_and_retired_roles_drop_out(
    make_member: Any, roles: dict[str, Any]
) -> None:
    from mizan.apps.identity.services import add_membership, retire_role

    user, _ = make_member("LAB_RECEPTION")
    assert not resolve_permissions(user.id, user.tenant_id).allows("quote", "create")
    add_membership(user=user, role=roles["COMMERCIAL"])
    assert resolve_permissions(user.id, user.tenant_id).allows("quote", "create")
    retire_role(roles["COMMERCIAL"])
    assert not resolve_permissions(user.id, user.tenant_id).allows("quote", "create")
    assert resolve_permissions(user.id, user.tenant_id).allows("intake", "create")
