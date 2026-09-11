"""Organisation services: tenants (platform operators), branches, departments, signatories, treasury."""

from __future__ import annotations

import uuid
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from pydantic import ValidationError as PydanticValidationError

from mizan.apps.audit import services as audit
from mizan.apps.org.models import (
    Branch,
    Department,
    Signatory,
    SignatureMode,
    Tenant,
    TreasuryAccount,
)
from mizan.apps.org.settings_schema import validate_settings
from mizan.platform.api.errors import Conflict, NotFound, UnprocessableEntity
from mizan.platform.db.models import ConcurrentUpdate
from mizan.platform.db.tenancy import platform_scope, tenant_scope
from mizan.platform.events import emit


def _config_changed(
    section: str, aggregate_id: uuid.UUID, action: str, branch_id: uuid.UUID | None = None
) -> None:
    emit(
        "config.changed",
        aggregate_type=section,
        aggregate_id=aggregate_id,
        branch_id=branch_id,
        payload={"section": section, "action": action},
    )


# --- tenants (platform operators) -------------------------------------------------------


def create_tenant(
    *,
    code: str,
    name: str,
    admin_email: str,
    admin_display_name: str = "",
    admin_temporary_password: str,
) -> tuple[Tenant, Any]:
    """Create a tenant, install the default roles and invite its first administrator."""
    from mizan.apps.identity.models import Role
    from mizan.apps.identity.roles import install_default_roles
    from mizan.apps.identity.services import add_membership, create_user

    with platform_scope(), transaction.atomic():
        if Tenant.objects.filter(code=code).exists():
            raise Conflict("org.tenant.code_exists", code="tenant_code_exists")
        tenant = Tenant.objects.create(code=code, name=name)
        audit.record("tenant", tenant.id, "created", after=audit.snapshot(tenant))
    with tenant_scope(tenant.id):
        install_default_roles()
        admin = create_user(
            email=admin_email,
            display_name=admin_display_name,
            temporary_password=admin_temporary_password,
        )
        add_membership(user=admin, role=Role.objects.get(code="TENANT_ADMIN"))
    return tenant, admin


def update_tenant(tenant: Tenant, data: dict[str, Any]) -> Tenant:
    before = audit.snapshot(tenant)
    for name, value in data.items():
        setattr(tenant, name, value)
    tenant.save()
    audit.record("tenant", tenant.id, "updated", before=before, after=audit.snapshot(tenant))
    _config_changed("tenant", tenant.id, "updated")
    return tenant


# --- branches -----------------------------------------------------------------------------


def create_branch(data: dict[str, Any]) -> Branch:
    if Branch.objects.filter(code=data["code"]).exists():
        raise Conflict("org.branch.code_exists", code="branch_code_exists")
    data["settings"] = _validated_settings(data.get("settings") or {})
    branch: Branch = Branch.objects.create(**data)
    audit.record("branch", branch.id, "created", after=audit.snapshot(branch), branch_id=branch.id)
    _config_changed("branch", branch.id, "created", branch_id=branch.id)
    return branch


def update_branch(branch: Branch, data: dict[str, Any]) -> Branch:
    expected = data.pop("row_version", None)
    if expected is not None and expected != branch.row_version:
        raise ConcurrentUpdate(Branch, branch.pk)
    if "settings" in data and data["settings"] is not None:
        data["settings"] = _validated_settings({**branch.settings, **data["settings"]})
    before = audit.snapshot(branch)
    for name, value in data.items():
        setattr(branch, name, value)
    branch.save()
    audit.record(
        "branch",
        branch.id,
        "updated",
        before=before,
        after=audit.snapshot(branch),
        branch_id=branch.id,
    )
    _config_changed("branch", branch.id, "updated", branch_id=branch.id)
    return branch


def _validated_settings(data: dict[str, Any]) -> dict[str, Any]:
    try:
        return validate_settings(data)
    except PydanticValidationError as exc:
        details = [
            {"loc": ["settings", *[str(x) for x in e["loc"]]], "msg": e["msg"]}
            for e in exc.errors()
        ]
        raise UnprocessableEntity("org.branch.invalid_settings", details=details) from exc


def get_branch(branch_id: uuid.UUID) -> Branch:
    try:
        branch: Branch = Branch.objects.get(pk=branch_id)
    except Branch.DoesNotExist as exc:
        raise NotFound() from exc
    return branch


# --- departments ----------------------------------------------------------------------------


def create_department(
    *, branch: Branch, code: str, labels: dict[str, str], colour: str = "", ord: int = 0
) -> Department:
    if Department.objects.filter(branch=branch, code=code).exists():
        raise Conflict("org.department.code_exists", code="department_code_exists")
    department: Department = Department.objects.create(
        branch=branch, code=code, colour=colour, ord=ord
    )
    department.set_labels(labels)
    audit.record(
        "department",
        department.id,
        "created",
        after={**audit.snapshot(department), "labels": labels},
        branch_id=branch.id,
    )
    _config_changed("department", department.id, "created", branch_id=branch.id)
    return department


def update_department(department: Department, data: dict[str, Any]) -> Department:
    before = {**audit.snapshot(department), "labels": department.labels}
    labels = data.pop("labels", None)
    for name, value in data.items():
        setattr(department, name, value)
    department.save()
    if labels:
        department.set_labels(labels)
    audit.record(
        "department",
        department.id,
        "updated",
        before=before,
        after={**audit.snapshot(department), "labels": department.labels},
        branch_id=department.branch_id,
    )
    _config_changed("department", department.id, "updated", branch_id=department.branch_id)
    return department


# --- signatories -----------------------------------------------------------------------------


def create_signatory(data: dict[str, Any]) -> Signatory:
    _validate_mode(data.get("mode", SignatureMode.IMAGE), data)
    signatory: Signatory = Signatory.objects.create(**data)
    audit.record(
        "signatory",
        signatory.id,
        "created",
        after=audit.snapshot(signatory),
        branch_id=signatory.branch_id,
    )
    _config_changed("signatory", signatory.id, "created", branch_id=signatory.branch_id)
    return signatory


def update_signatory(signatory: Signatory, data: dict[str, Any]) -> Signatory:
    before = audit.snapshot(signatory)
    merged = {**audit.snapshot(signatory), **data}
    _validate_mode(merged.get("mode", signatory.mode), merged)
    for name, value in data.items():
        setattr(signatory, name, value)
    signatory.save()
    audit.record(
        "signatory",
        signatory.id,
        "updated",
        before=before,
        after=audit.snapshot(signatory),
        branch_id=signatory.branch_id,
    )
    _config_changed("signatory", signatory.id, "updated", branch_id=signatory.branch_id)
    return signatory


def _validate_mode(mode: str, data: dict[str, Any]) -> None:
    if mode not in SignatureMode.values:
        raise UnprocessableEntity(
            "org.signatory.unknown_mode", details=[{"loc": ["mode"], "msg": mode}]
        )
    if mode == SignatureMode.DIGITAL_CERTIFICATE and not data.get("certificate_ref"):
        raise UnprocessableEntity(
            "org.signatory.certificate_required",
            details=[{"loc": ["certificate_ref"], "msg": "required"}],
        )
    if mode == SignatureMode.EXTERNAL_ESIGN and not data.get("esign_provider_code"):
        raise UnprocessableEntity(
            "org.signatory.provider_required",
            details=[{"loc": ["esign_provider_code"], "msg": "required"}],
        )


# --- treasury accounts -------------------------------------------------------------------------


def create_treasury_account(data: dict[str, Any]) -> TreasuryAccount:
    account = TreasuryAccount(**data)
    try:
        account.full_clean(exclude=["tenant_id", "created_by", "updated_by"])
    except DjangoValidationError as exc:
        raise UnprocessableEntity(
            "org.treasury_account.invalid", details=[{"msg": m} for m in exc.messages]
        ) from exc
    account.save()
    audit.record(
        "treasury_account",
        account.id,
        "created",
        after=audit.snapshot(account),
        branch_id=account.branch_id,
    )
    _config_changed("treasury_account", account.id, "created", branch_id=account.branch_id)
    return account


def update_treasury_account(account: TreasuryAccount, data: dict[str, Any]) -> TreasuryAccount:
    before = audit.snapshot(account)
    for name, value in data.items():
        setattr(account, name, value)
    account.save()
    audit.record(
        "treasury_account",
        account.id,
        "updated",
        before=before,
        after=audit.snapshot(account),
        branch_id=account.branch_id,
    )
    _config_changed("treasury_account", account.id, "updated", branch_id=account.branch_id)
    return account
