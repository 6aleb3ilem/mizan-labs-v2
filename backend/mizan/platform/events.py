"""Domain events (SPEC §19.1, §27.4): emitted inside the business transaction.

- Synchronous handlers run immediately in the same transaction (e.g. provisioning that must
  be atomic with the acceptance).
- Asynchronous handlers become one Procrastinate job each, deferred through the Django
  connection, so the job row commits or rolls back with the business write (the outbox).
  ``queueing_lock = "<event id>:<handler>"`` makes enqueueing idempotent.
- Every event is also published on the ``mizan_events`` PostgreSQL channel for SSE.
"""

from __future__ import annotations

import contextlib
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from django.db import transaction
from django.utils import timezone

from mizan.platform import context
from mizan.platform.ids import uuid7

log = logging.getLogger("mizan.events")

EVENT_CODES: frozenset[str] = frozenset(
    [
        "account.created",
        "contact.created",
        "portal_user.invited",
        "portal_user.first_login",
        "project.created",
        "project.closed",
        "work_item.created",
        "work_item.flagged_variance",
        "work_item.delivered",
        "quote.created",
        "quote.revision_created",
        "quote.approval_requested",
        "quote.approved",
        "quote.sent",
        "quote.negotiating",
        "quote.suspended",
        "quote.refused",
        "quote.expired",
        "quote.accepted",
        "quote.cancelled",
        "contract.generated",
        "contract.sent",
        "contract.signed",
        "order.created",
        "order.amended",
        "order.completed",
        "expected_intake.created",
        "intake.registered",
        "specimen.labelled",
        "sample.registered",
        "stage.changed",
        "test_run.scheduled",
        "test_run.assigned",
        "test_run.due_tomorrow",
        "test_run.overdue",
        "test_run.started",
        "measurement.recorded",
        "test_run.measured",
        "computed_value.overridden",
        "test_run.validated",
        "test_run.cancelled",
        "report.draft_ready",
        "report.issued",
        "report.superseded",
        "report.revoked",
        "document.rendered",
        "document.printed",
        "milestone.instantiated",
        "milestone.invoiceable",
        "invoice.issued",
        "invoice.sent",
        "invoice.due_soon",
        "invoice.overdue",
        "invoice.paid",
        "credit_note.issued",
        "payment.recorded",
        "payment.allocated",
        "payment.reversed",
        "payment_intent.succeeded",
        "stock.reserved",
        "stock.released",
        "stock.moved",
        "stock.below_threshold",
        "rental.started",
        "rental.due_soon",
        "rental.late",
        "rental.returned",
        "transfer.dispatched",
        "transfer.received",
        "maintenance.due",
        "maintenance.done",
        "work_order.created",
        "phase.completed",
        "work_order.late",
        "work_order.completed",
        "verification.suspicious",
        "verification.revoked_lookup",
        "fraud_case.opened",
        "user.invited",
        "user.disabled",
        "role.changed",
        "config.changed",
        "backup.completed",
        "backup.failed",
        "job.failed",
    ]
)


@dataclass(frozen=True, slots=True)
class Event:
    id: uuid.UUID
    code: str
    tenant_id: uuid.UUID | None
    branch_id: uuid.UUID | None
    actor_id: uuid.UUID | None
    actor_type: str
    at: datetime
    aggregate_type: str
    aggregate_id: uuid.UUID | None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "code": self.code,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "branch_id": str(self.branch_id) if self.branch_id else None,
            "actor_id": str(self.actor_id) if self.actor_id else None,
            "actor_type": self.actor_type,
            "at": self.at.isoformat(),
            "aggregate_type": self.aggregate_type,
            "aggregate_id": str(self.aggregate_id) if self.aggregate_id else None,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Event:
        return cls(
            id=uuid.UUID(data["id"]),
            code=data["code"],
            tenant_id=uuid.UUID(data["tenant_id"]) if data.get("tenant_id") else None,
            branch_id=uuid.UUID(data["branch_id"]) if data.get("branch_id") else None,
            actor_id=uuid.UUID(data["actor_id"]) if data.get("actor_id") else None,
            actor_type=data.get("actor_type", "SYSTEM"),
            at=datetime.fromisoformat(data["at"]),
            aggregate_type=data["aggregate_type"],
            aggregate_id=uuid.UUID(data["aggregate_id"]) if data.get("aggregate_id") else None,
            payload=dict(data.get("payload") or {}),
        )


HandlerFunc = Callable[[Event], None]


@dataclass(frozen=True, slots=True)
class Handler:
    name: str
    func: HandlerFunc
    sync: bool
    queue: str


_handlers: dict[str, list[Handler]] = {}
_by_name: dict[str, Handler] = {}
WILDCARD = "*"


def subscribe(
    *codes: str, name: str | None = None, sync: bool = False, queue: str = "events"
) -> Callable[[HandlerFunc], HandlerFunc]:
    """Register a handler for one or more event codes (``"*"`` for every event)."""
    for code in codes:
        if code != WILDCARD and code not in EVENT_CODES:
            raise ValueError(f"unknown event code {code!r}")

    def decorator(func: HandlerFunc) -> HandlerFunc:
        handler_name = name or f"{func.__module__}.{func.__qualname__}"
        handler = Handler(name=handler_name, func=func, sync=sync, queue=queue)
        if handler_name in _by_name and _by_name[handler_name].func is not func:
            raise ValueError(f"handler name {handler_name!r} is already registered")
        _by_name[handler_name] = handler
        for code in codes:
            bucket = _handlers.setdefault(code, [])
            if all(h.name != handler_name for h in bucket):
                bucket.append(handler)
        return func

    return decorator


def handlers_for(code: str) -> list[Handler]:
    return [*_handlers.get(code, []), *_handlers.get(WILDCARD, [])]


def get_handler(name: str) -> Handler:
    try:
        return _by_name[name]
    except KeyError as exc:
        raise LookupError(f"no event handler named {name!r}") from exc


def clear_handlers() -> None:
    """Test helper."""
    _handlers.clear()
    _by_name.clear()


def emit(
    code: str,
    *,
    aggregate_type: str,
    aggregate_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
    branch_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
) -> Event:
    if code not in EVENT_CODES:
        raise ValueError(f"unknown event code {code!r}")
    actor = context.actor()
    event = Event(
        id=uuid7(),
        code=code,
        tenant_id=tenant_id or context.current_tenant_id.get(),
        branch_id=branch_id,
        actor_id=actor.id,
        actor_type=actor.type,
        at=timezone.now(),
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=payload or {},
    )
    handlers = handlers_for(code)
    for handler in handlers:
        if handler.sync:
            handler.func(event)
    for handler in handlers:
        if not handler.sync:
            _defer(event, handler)
    from mizan.platform.realtime.publish import publish

    publish(event)
    log.debug("event %s emitted (%d handlers)", code, len(handlers), extra={"event": code})
    return event


def _defer(event: Event, handler: Handler) -> None:
    from procrastinate.exceptions import AlreadyEnqueued

    from mizan.platform.tasks import dispatch_event

    # A duplicate queueing lock fails the INSERT; the savepoint keeps the business transaction usable.
    with contextlib.suppress(AlreadyEnqueued), transaction.atomic():
        dispatch_event.configure(
            queueing_lock=f"{event.id}:{handler.name}", queue=handler.queue
        ).defer(event=event.to_dict(), handler=handler.name)
