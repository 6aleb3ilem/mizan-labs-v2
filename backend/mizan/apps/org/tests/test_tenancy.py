"""SPEC §5, §27.6, ADR 0003: cross-tenant reads are impossible; every tenant model has a policy."""

from __future__ import annotations

import uuid

import pytest
from django.apps import apps
from django.db import DatabaseError, connection, transaction

from mizan.apps.org.models import Branch, Department, Tenant
from mizan.platform.db.tenancy import active_tenant_setting, platform_scope, tenant_scope

pytestmark = pytest.mark.django_db


def _tenant_tables() -> list[str]:
    tables = []
    for model in apps.get_models():
        if model._meta.abstract or not model._meta.managed:
            continue
        names = {f.name for f in model._meta.fields} | {f.attname for f in model._meta.fields}
        if "tenant_id" in names and model._meta.db_table != "tenant":
            tables.append(model._meta.db_table)
    return sorted(set(tables))


def test_test_database_role_is_not_a_superuser() -> None:
    """A superuser bypasses RLS, which would make every isolation test vacuous."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
        assert cursor.fetchone() == (False,)


def test_every_tenant_model_has_a_forced_rls_policy() -> None:
    tables = _tenant_tables()
    assert tables, "expected at least one tenant model"
    with connection.cursor() as cursor:
        cursor.execute("SELECT tablename FROM pg_policies WHERE policyname = 'tenant_isolation'")
        with_policy = {row[0] for row in cursor.fetchall()}
        cursor.execute(
            "SELECT relname FROM pg_class WHERE relrowsecurity AND relforcerowsecurity AND relname = ANY(%s)",
            [tables],
        )
        forced = {row[0] for row in cursor.fetchall()}
    missing_policy = [t for t in tables if t not in with_policy]
    missing_force = [t for t in tables if t not in forced]
    assert not missing_policy, f"tables without tenant_isolation policy: {missing_policy}"
    assert not missing_force, f"tables without FORCE ROW LEVEL SECURITY: {missing_force}"


def test_rows_are_invisible_outside_a_tenant_scope(tenant: Tenant) -> None:
    with tenant_scope(tenant.id):
        Branch.objects.create(code="A", legal_name="A", currency="MRU")
        assert Branch.objects.count() == 1
    assert Branch.objects.count() == 0, "no scope means no rows"
    assert active_tenant_setting() == ""


def test_cross_tenant_read_is_impossible(tenant: Tenant, other_tenant: Tenant) -> None:
    with tenant_scope(tenant.id):
        Branch.objects.create(code="A", legal_name="A", currency="MRU")
    with tenant_scope(other_tenant.id):
        assert Branch.objects.count() == 0
        assert not Branch.objects.filter(code="A").exists()
        Branch.objects.create(code="B", legal_name="B", currency="XOF")
        assert list(Branch.objects.values_list("code", flat=True)) == ["B"]
    with tenant_scope(tenant.id):
        assert list(Branch.objects.values_list("code", flat=True)) == ["A"]


def test_inserting_a_row_for_another_tenant_is_rejected(
    tenant: Tenant, other_tenant: Tenant
) -> None:
    with tenant_scope(tenant.id), pytest.raises(DatabaseError), transaction.atomic():
        Branch.objects.create(code="X", legal_name="X", currency="MRU", tenant_id=other_tenant.id)


def test_platform_scope_sees_every_tenant(tenant: Tenant, other_tenant: Tenant) -> None:
    with tenant_scope(tenant.id):
        Branch.objects.create(code="A", legal_name="A", currency="MRU")
    with tenant_scope(other_tenant.id):
        Branch.objects.create(code="B", legal_name="B", currency="XOF")
    with platform_scope():
        assert Branch.objects.count() == 2
    assert Branch.objects.count() == 0


def test_nested_scopes_restore_the_outer_tenant(tenant: Tenant, other_tenant: Tenant) -> None:
    with tenant_scope(tenant.id):
        assert active_tenant_setting() == str(tenant.id)
        with tenant_scope(other_tenant.id):
            assert active_tenant_setting() == str(other_tenant.id)
        assert active_tenant_setting() == str(tenant.id)


def test_tenant_id_defaults_to_the_active_scope(tenant: Tenant) -> None:
    with tenant_scope(tenant.id):
        branch = Branch.objects.create(code="A", legal_name="A", currency="MRU")
        department = Department.objects.create(branch=branch, code="CONCRETE")
    assert branch.tenant_id == tenant.id
    assert department.tenant_id == tenant.id


def test_saving_without_a_scope_fails_loudly(db: object) -> None:
    with pytest.raises(RuntimeError):
        Branch.objects.create(code="A", legal_name="A", currency="MRU")


def test_platform_users_are_visible_everywhere(tenant: Tenant) -> None:
    from mizan.apps.identity.models import User

    with platform_scope():
        operator = User.objects.create_superuser("ops@mizan-platform.dev", "Passw0rd!Passw0rd")
    assert User.objects.filter(pk=operator.pk).exists(), "NULL-tenant rows are global"
    with tenant_scope(tenant.id):
        User.objects.create_user("staff@t1.dev", tenant_id=tenant.id)
        assert User.objects.count() == 2
    with tenant_scope(uuid.uuid4()):
        assert User.objects.count() == 1
