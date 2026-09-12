"""Write services: rule and template changes (audited, config.changed), preferences, inbox."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from django.utils import timezone

from mizan.apps.audit import services as audit
from mizan.apps.notify import cron
from mizan.apps.notify.dispatch import plan_rule
from mizan.apps.notify.models import (
    CHANNEL_CODES,
    ContactChannelPreference,
    Notification,
    NotificationRule,
)
from mizan.apps.notify.recipients import CONTACT_ROLES
from mizan.platform import context
from mizan.platform.api.errors import UnprocessableEntity
from mizan.platform.events import EVENT_CODES, Event, emit
from mizan.platform.ids import uuid7
from mizan.platform.realtime.publish import publish_to_user


def changed(
    section: str, aggregate_id: uuid.UUID, action: str, *, before: Any = None, after: Any = None
) -> None:
    audit.record(section, aggregate_id, action, before=before, after=after)
    emit(
        "config.changed",
        aggregate_type=section,
        aggregate_id=aggregate_id,
        payload={"section": section, "action": action},
    )


def validate_rule(data: dict[str, Any]) -> None:
    details: list[dict[str, Any]] = []
    event_code = str(data.get("event_code") or "")
    digest = data.get("digest") or {}
    if event_code and event_code not in EVENT_CODES:
        details.append({"loc": ["event_code"], "msg": f"unknown event {event_code!r}"})
    if not event_code and not digest.get("cron"):
        details.append({"loc": ["event_code"], "msg": "an event code or a digest cron is required"})
    if digest.get("cron"):
        try:
            cron.validate(str(digest["cron"]))
        except cron.InvalidCron as exc:
            details.append({"loc": ["digest", "cron"], "msg": str(exc)})
    channels = data.get("channels") or []
    unknown = [c for c in channels if c not in CHANNEL_CODES]
    if unknown:
        details.append({"loc": ["channels"], "msg": f"unknown channels {unknown}"})
    if not channels:
        details.append({"loc": ["channels"], "msg": "at least one channel"})
    audience = data.get("audience") or {}
    bad_roles = [r for r in audience.get("contact_roles") or [] if r.upper() not in CONTACT_ROLES]
    if bad_roles:
        details.append({"loc": ["audience", "contact_roles"], "msg": f"unknown {bad_roles}"})
    for key in ("roles", "contact_roles", "user_ids", "payload_user_keys"):
        if key in audience and not isinstance(audience[key], list):
            details.append({"loc": ["audience", key], "msg": "must be a list"})
    throttle = data.get("throttle") or {}
    for key in ("window_seconds", "max"):
        if key in throttle and (not isinstance(throttle[key], int) or throttle[key] < 0):
            details.append({"loc": ["throttle", key], "msg": "must be a non-negative integer"})
    if details:
        raise UnprocessableEntity("notify.rule.invalid", details=details)


def simulate_rule(
    rule: NotificationRule, payload: dict[str, Any], *, branch_id: uuid.UUID | None = None
) -> list[dict[str, Any]]:
    """Dry run: who would receive what, with skip reasons. Nothing is persisted or sent."""
    event = Event(
        id=uuid7(),
        code=rule.event_code or "config.changed",
        tenant_id=context.current_tenant_id.get(),
        branch_id=branch_id or rule.branch_id,
        actor_id=context.actor().id,
        actor_type=context.actor().type,
        at=timezone.now(),
        aggregate_type=str(payload.get("aggregate_type") or rule.event_code.split(".")[0]),
        aggregate_id=None,
        payload=payload,
    )
    return [
        {
            "recipient": item.recipient.as_dict(),
            "channel": item.channel,
            "locale": item.locale,
            "status": item.status,
            "reason": item.reason,
            "scheduled_for": item.scheduled_for,
            "rendered": item.rendered,
        }
        for item in plan_rule(rule, event)
    ]


# --- preferences ----------------------------------------------------------------------------------


def preferences(recipient_type: str, recipient_id: uuid.UUID) -> dict[str, bool]:
    rows = ContactChannelPreference.objects.filter(
        recipient_type=recipient_type, recipient_id=recipient_id
    )
    result = dict.fromkeys(CHANNEL_CODES, True)
    result.update({row.channel: row.enabled for row in rows})
    return result


def set_preferences(
    recipient_type: str, recipient_id: uuid.UUID, values: dict[str, bool]
) -> dict[str, bool]:
    unknown = [c for c in values if c not in CHANNEL_CODES]
    if unknown:
        raise UnprocessableEntity(
            "notify.preference.unknown_channel",
            details=[{"loc": ["channels"], "msg": str(unknown)}],
        )
    before = preferences(recipient_type, recipient_id)
    for channel, enabled in values.items():
        ContactChannelPreference.objects.update_or_create(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            channel=channel,
            defaults={"enabled": bool(enabled)},
        )
    after = preferences(recipient_type, recipient_id)
    audit.record(
        "contact_channel_preference",
        recipient_id,
        "updated",
        before=before,
        after=after,
        extra={"recipient_type": recipient_type},
    )
    return after


# --- inbox ----------------------------------------------------------------------------------------


def unread_count(user_id: uuid.UUID) -> int:
    return int(Notification.objects.filter(user_id=user_id, read_at__isnull=True).count())


def mark_read(user_id: uuid.UUID, notification_ids: list[uuid.UUID]) -> int:
    now = timezone.now()
    updated = Notification.objects.filter(
        user_id=user_id, pk__in=notification_ids, read_at__isnull=True
    ).update(read_at=now, updated_at=now)
    _push_counter(user_id)
    return int(updated)


def mark_all_read(user_id: uuid.UUID, *, before: dt.datetime | None = None) -> int:
    now = timezone.now()
    qs = Notification.objects.filter(user_id=user_id, read_at__isnull=True)
    if before is not None:
        qs = qs.filter(created_at__lte=before)
    updated = qs.update(read_at=now, updated_at=now)
    _push_counter(user_id)
    return int(updated)


def _push_counter(user_id: uuid.UUID) -> None:
    publish_to_user(
        context.current_tenant_id.get(), user_id, "inbox", {"unread": unread_count(user_id)}
    )
