"""Audit log API (SPEC A.2): the full log for auditors and the History tab of any record."""

import uuid
from datetime import datetime
from typing import Any

from django.http import HttpRequest
from ninja import Query, Router, Schema

from mizan.apps.audit.models import AuditEvent
from mizan.apps.identity.authz import authorize, requires
from mizan.platform.api.pagination import CursorParams, Page, paginate
from mizan.platform.authz.catalog import RESOURCES

router = Router(tags=["audit"])


class AuditEventOut(Schema):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    branch_id: uuid.UUID | None
    aggregate_type: str
    aggregate_id: uuid.UUID | None
    action: str
    actor_id: uuid.UUID | None
    actor_type: str
    at: datetime
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    context: dict[str, Any]


class AuditFilters(Schema):
    aggregate_type: str | None = None
    aggregate_id: uuid.UUID | None = None
    actor_id: uuid.UUID | None = None
    action: str | None = None
    since: datetime | None = None
    until: datetime | None = None


def _filtered(filters: AuditFilters) -> Any:
    qs = AuditEvent.objects.all()
    if filters.aggregate_type:
        qs = qs.filter(aggregate_type=filters.aggregate_type)
    if filters.aggregate_id:
        qs = qs.filter(aggregate_id=filters.aggregate_id)
    if filters.actor_id:
        qs = qs.filter(actor_id=filters.actor_id)
    if filters.action:
        qs = qs.filter(action=filters.action)
    if filters.since:
        qs = qs.filter(at__gte=filters.since)
    if filters.until:
        qs = qs.filter(at__lt=filters.until)
    return qs


def _out(event: AuditEvent) -> dict[str, Any]:
    return AuditEventOut.from_orm(event).model_dump()


@router.get("/audit-events", response=Page[AuditEventOut], summary="Search the audit log")
@requires("audit_event", "view")
def list_audit_events(
    request: HttpRequest, filters: Query[AuditFilters], params: Query[CursorParams]
) -> dict[str, Any]:
    return paginate(_filtered(filters), params, _out, timestamp_field="at")


@router.get(
    "/history/{aggregate_type}/{uuid:aggregate_id}",
    response=Page[AuditEventOut],
    summary="History tab: audit trail of one record (requires view on that resource)",
)
def history(
    request: HttpRequest, aggregate_type: str, aggregate_id: uuid.UUID, params: Query[CursorParams]
) -> dict[str, Any]:
    authorize(request, aggregate_type if aggregate_type in RESOURCES else "audit_event", "view")
    qs = AuditEvent.objects.filter(aggregate_type=aggregate_type, aggregate_id=aggregate_id)
    return paginate(qs, params, _out, timestamp_field="at")
