"""The authorization engine: allows, field groups, scope predicates (SPEC §9.4)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from mizan.apps.org.models import Branch, Department
from mizan.platform.authz.catalog import validate_grant
from mizan.platform.authz.permissions import EffectivePermissions, GrantBinding

pytestmark = pytest.mark.django_db


def _perms(user_id: uuid.UUID, *bindings: GrantBinding) -> EffectivePermissions:
    return EffectivePermissions(user_id=user_id, tenant_id=uuid.uuid4(), bindings=list(bindings))


def test_allows_and_field_groups_union() -> None:
    user = uuid.uuid4()
    perms = _perms(
        user,
        GrantBinding(
            "project", "view", "OWN_BRANCH", frozenset({"commercial"}), branch_id=uuid.uuid4()
        ),
        GrantBinding(
            "project", "view", "OWN_BRANCH", frozenset({"financial"}), branch_id=uuid.uuid4()
        ),
    )
    assert perms.allows("project", "view")
    assert not perms.allows("project", "edit")
    assert not perms.allows("quote", "view")
    assert perms.field_groups("project", "view") == {"commercial", "financial"}
    assert perms.field_groups("project", "edit") == frozenset()


def test_allows_respects_the_requested_branch() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    perms = _perms(uuid.uuid4(), GrantBinding("intake", "create", "OWN_BRANCH", branch_id=a))
    assert perms.allows("intake", "create", branch_id=a)
    assert not perms.allows("intake", "create", branch_id=b)
    everywhere = _perms(
        uuid.uuid4(), GrantBinding("intake", "create", "OWN_BRANCH", branch_id=None)
    )
    assert everywhere.allows("intake", "create", branch_id=b)
    assert everywhere.branch_ids("intake", "create") is None


def test_scope_predicates_filter_rows(scoped: Any) -> None:
    branch_a = Branch.objects.create(code="A", legal_name="A", currency="MRU")
    branch_b = Branch.objects.create(code="B", legal_name="B", currency="MRU")
    Department.objects.create(branch=branch_a, code="D_A")
    Department.objects.create(branch=branch_b, code="D_B")
    me = uuid.uuid4()

    own_branch = _perms(me, GrantBinding("department", "view", "OWN_BRANCH", branch_id=branch_a.id))
    codes = set(
        Department.objects.filter(
            own_branch.predicate("department", "view", model=Department)
        ).values_list("code", flat=True)
    )
    assert codes == {"D_A"}

    all_branches = _perms(me, GrantBinding("department", "view", "ALL_BRANCHES"))
    assert (
        Department.objects.filter(
            all_branches.predicate("department", "view", model=Department)
        ).count()
        == 2
    )

    nothing = _perms(me)
    assert (
        Department.objects.filter(nothing.predicate("department", "view", model=Department)).count()
        == 0
    )

    # OWN_DEPARTMENT on a model without a department column falls back to the branch.
    dept_scoped = _perms(
        me,
        GrantBinding(
            "department",
            "view",
            "OWN_DEPARTMENT",
            branch_id=branch_b.id,
            department_id=uuid.uuid4(),
        ),
    )
    codes = set(
        Department.objects.filter(
            dept_scoped.predicate("department", "view", model=Department)
        ).values_list("code", flat=True)
    )
    assert codes == {"D_B"}

    # The X-Branch-Id header narrows an ALL_BRANCHES grant to one branch.
    narrowed = all_branches.predicate("department", "view", model=Department, branch_id=branch_b.id)
    assert set(Department.objects.filter(narrowed).values_list("code", flat=True)) == {"D_B"}


def test_own_records_and_assigned_scopes(scoped: Any) -> None:
    branch = Branch.objects.create(code="A", legal_name="A", currency="MRU")
    mine = Department.objects.create(branch=branch, code="MINE")
    theirs = Department.objects.create(branch=branch, code="THEIRS")
    me = uuid.uuid4()
    Department.all_objects.filter(pk=mine.pk).update(created_by=me)
    Department.all_objects.filter(pk=theirs.pk).update(created_by=uuid.uuid4())
    perms = _perms(me, GrantBinding("department", "view", "OWN_RECORDS", branch_id=branch.id))
    assert list(
        Department.objects.filter(
            perms.predicate("department", "view", model=Department)
        ).values_list("code", flat=True)
    ) == ["MINE"]
    # ASSIGNED_TO_ME on a model without an assignee column falls back to the creator.
    assigned = _perms(me, GrantBinding("department", "view", "ASSIGNED_TO_ME", branch_id=branch.id))
    assert (
        Department.objects.filter(
            assigned.predicate("department", "view", model=Department)
        ).count()
        == 1
    )


def test_own_account_scope_requires_an_account() -> None:
    perms = _perms(uuid.uuid4(), GrantBinding("project", "view", "OWN_ACCOUNT", account_id=None))
    assert str(perms.predicate("project", "view")) == str(
        __import__("django.db.models", fromlist=["Q"]).Q(pk__in=[])
    )


def test_catalogue_validation() -> None:
    validate_grant("quote", "approve", "OWN_BRANCH", [])
    validate_grant("project", "view", "OWN_BRANCH", ["commercial"])
    with pytest.raises(ValueError):
        validate_grant("quote", "fly", "OWN_BRANCH", [])
    with pytest.raises(ValueError):
        validate_grant("quote", "view", "OWN_BRANCH", ["commercial"])  # no such group on quote
    with pytest.raises(ValueError):
        validate_grant("nope", "view", "OWN_BRANCH", [])
