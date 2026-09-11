"""Organisation API (SPEC A.2): tenant profile, branches, departments, signatories, treasury accounts."""

import uuid
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.http import HttpRequest
from ninja import Router, Status

from mizan.apps.identity.authz import requires
from mizan.apps.org import services
from mizan.apps.org.models import Branch, Department, Signatory, Tenant, TreasuryAccount
from mizan.apps.org.schemas import (
    BranchIn,
    BranchOut,
    BranchPatch,
    DepartmentIn,
    DepartmentOut,
    DepartmentPatch,
    SignatoryIn,
    SignatoryOut,
    SignatoryPatch,
    TenantCreate,
    TenantOut,
    TenantPatch,
    TreasuryAccountIn,
    TreasuryAccountOut,
    TreasuryAccountPatch,
)
from mizan.platform import context
from mizan.platform.api.errors import Forbidden, NotFound
from mizan.platform.api.idempotency import idempotent

router = Router(tags=["organisation"])


def _get[M: models.Model](model: type[M], pk: uuid.UUID) -> M:
    try:
        instance: M = model._default_manager.get(pk=pk)
    except ObjectDoesNotExist as exc:
        raise NotFound() from exc
    return instance


def _department_out(d: Department) -> dict[str, Any]:
    return {
        "id": d.id,
        "branch_id": d.branch_id,
        "code": d.code,
        "labels": d.labels,
        "colour": d.colour,
        "ord": d.ord,
        "active": d.active,
    }


def _signatory_out(s: Signatory) -> dict[str, Any]:
    return {
        "id": s.id,
        "branch_id": s.branch_id,
        "user_id": s.user_id,
        "display_name": s.display_name,
        "title": s.title,
        "document_kinds": s.document_kinds,
        "mode": s.mode,
        "has_signature_image": bool(s.signature_image_key),
        "has_stamp_image": bool(s.stamp_image_key),
        "image_positions": s.image_positions,
        "image_version": s.image_version,
        "certificate_ref": s.certificate_ref,
        "esign_provider_code": s.esign_provider_code,
        "requires_step_up": s.requires_step_up,
        "signing_order": s.signing_order,
        "active": s.active,
    }


# --- tenant ----------------------------------------------------------------------------------


@router.get("/tenant", response=TenantOut, summary="Profile and branding of the caller's tenant")
@requires("tenant", "view")
def get_tenant(request: HttpRequest) -> Tenant:
    return _get(Tenant, context.require_tenant_id())


@router.patch(
    "/tenant", response=TenantOut, summary="Update name and theme (logo, primary colour, texts)"
)
@requires("tenant", "configure")
def patch_tenant(request: HttpRequest, payload: TenantPatch) -> Tenant:
    tenant = _get(Tenant, context.require_tenant_id())
    return services.update_tenant(tenant, payload.model_dump(exclude_unset=True))


@router.post(
    "/platform/tenants",
    response={201: TenantOut},
    summary="Platform operator: create a tenant and its administrator",
)
def create_tenant(request: HttpRequest, payload: TenantCreate) -> Status[Tenant]:
    principal = getattr(request, "principal", None)
    if principal is None or not principal.is_platform_operator:
        raise Forbidden(params={"action": "tenant.create"})
    tenant, _admin = services.create_tenant(**payload.model_dump())
    return Status(201, tenant)


# --- branches --------------------------------------------------------------------------------


@router.get("/branches", response=list[BranchOut], summary="Branches of the tenant")
@requires("branch", "view")
def list_branches(request: HttpRequest) -> list[Branch]:
    return list(request.authz.scope(Branch.objects.all(), fields=_BRANCH_FIELDS).order_by("code"))  # type: ignore[attr-defined]


@router.post("/branches", response={201: BranchOut}, summary="Create a branch")
@requires("branch", "configure")
@idempotent
def create_branch(request: HttpRequest, payload: BranchIn) -> Status[Branch]:
    return Status(201, services.create_branch(payload.model_dump()))


@router.get("/branches/{uuid:branch_id}", response=BranchOut)
@requires("branch", "view")
def get_branch(request: HttpRequest, branch_id: uuid.UUID) -> Branch:
    return services.get_branch(branch_id)


@router.patch(
    "/branches/{uuid:branch_id}",
    response=BranchOut,
    summary="Update identity, calendar or settings of a branch",
)
@requires("branch", "configure")
def patch_branch(request: HttpRequest, branch_id: uuid.UUID, payload: BranchPatch) -> Branch:
    return services.update_branch(
        services.get_branch(branch_id), payload.model_dump(exclude_unset=True)
    )


from mizan.platform.authz.permissions import ScopeFields  # noqa: E402

_BRANCH_FIELDS = ScopeFields(branch="id")


# --- departments -----------------------------------------------------------------------------


@router.get(
    "/departments", response=list[DepartmentOut], summary="Departments (optionally of one branch)"
)
@requires("department", "view")
def list_departments(
    request: HttpRequest, branch_id: uuid.UUID | None = None
) -> list[dict[str, Any]]:
    qs = Department.objects.all()
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    rows = list(qs.order_by("ord", "code"))
    Department.attach_labels(rows)
    return [_department_out(d) for d in rows]


@router.post("/departments", response={201: DepartmentOut})
@requires("department", "configure")
def create_department(request: HttpRequest, payload: DepartmentIn) -> Status[dict[str, Any]]:
    department = services.create_department(
        branch=services.get_branch(payload.branch_id),
        code=payload.code,
        labels=payload.labels.model_dump(exclude_none=True),
        colour=payload.colour,
        ord=payload.ord,
    )
    return Status(201, _department_out(department))


@router.patch("/departments/{uuid:department_id}", response=DepartmentOut)
@requires("department", "configure")
def patch_department(
    request: HttpRequest, department_id: uuid.UUID, payload: DepartmentPatch
) -> dict[str, Any]:
    data = payload.model_dump(exclude_unset=True)
    if data.get("labels"):
        data["labels"] = {k: v for k, v in data["labels"].items() if v}
    return _department_out(services.update_department(_get(Department, department_id), data))


# --- signatories -----------------------------------------------------------------------------


@router.get(
    "/signatories", response=list[SignatoryOut], summary="Signatories and their signature modes"
)
@requires("signatory", "view")
def list_signatories(
    request: HttpRequest, branch_id: uuid.UUID | None = None
) -> list[dict[str, Any]]:
    qs = Signatory.objects.all()
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    return [_signatory_out(s) for s in qs]


@router.post("/signatories", response={201: SignatoryOut})
@requires("signatory", "configure")
def create_signatory(request: HttpRequest, payload: SignatoryIn) -> Status[dict[str, Any]]:
    return Status(201, _signatory_out(services.create_signatory(payload.model_dump())))


@router.patch("/signatories/{uuid:signatory_id}", response=SignatoryOut)
@requires("signatory", "configure")
def patch_signatory(
    request: HttpRequest, signatory_id: uuid.UUID, payload: SignatoryPatch
) -> dict[str, Any]:
    return _signatory_out(
        services.update_signatory(
            _get(Signatory, signatory_id), payload.model_dump(exclude_unset=True)
        )
    )


# --- treasury accounts -------------------------------------------------------------------------


@router.get("/treasury-accounts", response=list[TreasuryAccountOut])
@requires("treasury_account", "view")
def list_treasury_accounts(
    request: HttpRequest, branch_id: uuid.UUID | None = None
) -> list[TreasuryAccount]:
    qs = TreasuryAccount.objects.all()
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    return list(qs)


@router.post("/treasury-accounts", response={201: TreasuryAccountOut})
@requires("treasury_account", "create")
def create_treasury_account(
    request: HttpRequest, payload: TreasuryAccountIn
) -> Status[TreasuryAccount]:
    return Status(201, services.create_treasury_account(payload.model_dump()))


@router.patch("/treasury-accounts/{uuid:account_id}", response=TreasuryAccountOut)
@requires("treasury_account", "edit")
def patch_treasury_account(
    request: HttpRequest, account_id: uuid.UUID, payload: TreasuryAccountPatch
) -> TreasuryAccount:
    return services.update_treasury_account(
        _get(TreasuryAccount, account_id), payload.model_dump(exclude_unset=True)
    )
