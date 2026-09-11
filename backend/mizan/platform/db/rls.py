"""Row-level security helpers for migrations.

Policies read the transaction-local settings written by ``tenancy.tenant_scope`` and
``tenancy.platform_scope``. FORCE makes the table owner subject to the policy too.
"""

from __future__ import annotations

from django.db import migrations

POLICY_NAME = "tenant_isolation"


def _predicate(tenant_column: str, *, global_when_null: bool) -> str:
    tenant_match = f"{tenant_column} = nullif(current_setting('app.tenant_id', true), '')::uuid"
    if global_when_null:
        tenant_match = f"({tenant_column} IS NULL OR {tenant_match})"
    return f"(current_setting('app.rls_bypass', true) = 'platform' OR {tenant_match})"


def enable_rls_sql(
    table: str, tenant_column: str = "tenant_id", *, global_when_null: bool = False
) -> str:
    predicate = _predicate(tenant_column, global_when_null=global_when_null)
    return (
        f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY;\n'
        f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY;\n'
        f'CREATE POLICY {POLICY_NAME} ON "{table}" USING {predicate} WITH CHECK {predicate};'
    )


def disable_rls_sql(table: str) -> str:
    return (
        f'DROP POLICY IF EXISTS {POLICY_NAME} ON "{table}";\n'
        f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY;\n'
        f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY;'
    )


def enable_rls(
    table: str, tenant_column: str = "tenant_id", *, global_when_null: bool = False
) -> migrations.RunSQL:
    """A reversible migration operation enabling tenant isolation on ``table``."""
    return migrations.RunSQL(
        sql=enable_rls_sql(table, tenant_column, global_when_null=global_when_null),
        reverse_sql=disable_rls_sql(table),
    )


def enable_rls_for(*tables: str) -> list[migrations.RunSQL]:
    return [enable_rls(table) for table in tables]
