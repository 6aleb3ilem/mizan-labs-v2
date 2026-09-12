"""From an event to deliveries (SPEC §19): rules → audience → preferences, throttle, quiet
hours → rendered messages → one delivery per recipient and channel, sent by a worker task.

The handler subscribes to every event and runs asynchronously (outbox); it is idempotent
because every delivery has a deterministic dedupe key.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import logging
import uuid
from dataclasses import dataclass
from typing import Any
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from mizan.apps.notify import channels
from mizan.apps.notify.models import (
    CHANNEL_CODES,
    ContactChannelPreference,
    DeliveryStatus,
    MessageTemplate,
    NotificationDelivery,
    NotificationRule,
)
from mizan.apps.notify.recipients import Recipient, resolve_audience
from mizan.apps.notify.rendering import MessageRenderError, render_message
from mizan.apps.org.models import Branch
from mizan.platform.db.tenancy import tenant_scope
from mizan.platform.events import Event, subscribe

log = logging.getLogger("mizan.notify")

MAX_ATTEMPTS = 5
QUIET_HOURS_CHANNELS: frozenset[str] = frozenset({"sms", "whatsapp"})
# Channel fallbacks when a rule's template does not exist for a channel.
TEMPLATE_CHANNEL_FALLBACKS: dict[str, tuple[str, ...]] = {
    "email": ("email", "in_app"),
    "sms": ("sms", "whatsapp", "in_app"),
    "whatsapp": ("whatsapp", "sms", "in_app"),
    "in_app": ("in_app", "sms", "whatsapp", "email"),
}


# --- templates and context ------------------------------------------------------------------------


def template_for(code: str, locale: str, channel: str) -> MessageTemplate | None:
    """The best template row: exact channel and locale first, then locale fallbacks, then the
    channel fallbacks (a WhatsApp rule may reuse the short SMS text)."""
    rows: list[MessageTemplate] = list(MessageTemplate.objects.filter(code=code, active=True))
    if not rows:
        return None
    locales = [locale, *[loc for loc in ("fr", "en") if loc != locale]]
    for candidate_channel in TEMPLATE_CHANNEL_FALLBACKS.get(channel, (channel,)):
        for candidate_locale in locales:
            for row in rows:
                if row.channel == candidate_channel and row.locale == candidate_locale:
                    return row
        for row in rows:  # any locale of that channel
            if row.channel == candidate_channel:
                return row
    return None


def build_context(
    event: Event, recipient: Recipient, branch: Branch | None, locale: str
) -> dict[str, Any]:
    """Template variables: the payload as-is plus recipient, branch, links and event metadata."""
    payload = dict(event.payload)
    portal = str(settings.MIZAN_PORTAL_BASE_URL).rstrip("/")
    app = str(settings.MIZAN_APP_BASE_URL).rstrip("/")
    verify = str(settings.MIZAN_VERIFY_BASE_URL).rstrip("/")
    aggregate_path = f"/{event.aggregate_type}s/{event.aggregate_id}" if event.aggregate_id else ""
    context: dict[str, Any] = {
        **payload,
        "event": {
            "id": str(event.id),
            "code": event.code,
            "at": event.at,
            "aggregate_type": event.aggregate_type,
            "aggregate_id": str(event.aggregate_id) if event.aggregate_id else "",
        },
        "aggregate_type": event.aggregate_type,
        "aggregate_id": str(event.aggregate_id) if event.aggregate_id else "",
        "recipient": recipient.as_dict(),
        "contact": {
            "first_name": recipient.extra.get("first_name") or recipient.name.split(" ")[0],
            "last_name": recipient.extra.get("last_name", ""),
            "name": recipient.name,
            "email": recipient.email,
            "phone": recipient.phone,
            **(payload.get("contact") or {}),
        },
        "locale": locale,
        "branch": {
            "code": branch.code if branch else "",
            "legal_name": branch.legal_name if branch else "",
            "trade_name": branch.trade_name if branch else "",
            "phone": branch.phone if branch else "",
            "email": branch.email if branch else "",
            "currency": branch.currency if branch else "",
        },
        "portal_base_url": portal,
        "app_base_url": app,
        "verify_base_url": verify,
    }
    context.setdefault("currency", branch.currency if branch else "")
    context.setdefault("portal_link", f"{portal}{payload.get('portal_path') or aggregate_path}")
    context.setdefault("app_link", f"{app}{payload.get('app_path') or aggregate_path}")
    context.setdefault("verify_link", f"{verify}{payload.get('verify_path') or ''}")
    context.setdefault("date", timezone.localdate().isoformat())
    return context


# --- policies -------------------------------------------------------------------------------------


def preferences_for(recipient: Recipient) -> dict[str, bool]:
    if recipient.id is None:
        return {}
    rows = ContactChannelPreference.objects.filter(
        recipient_type=recipient.type, recipient_id=recipient.id
    )
    prefs = {row.channel: row.enabled for row in rows}
    if recipient.type == "contact" and recipient.user_id is not None:
        for row in ContactChannelPreference.objects.filter(
            recipient_type="user", recipient_id=recipient.user_id
        ):
            prefs.setdefault(row.channel, row.enabled)
    return prefs


def quiet_hours_end(branch: Branch | None, now: dt.datetime) -> dt.datetime | None:
    """When ``now`` falls in the branch quiet hours, the moment they end (UTC); else None."""
    if branch is None:
        return None
    window = (branch.settings or {}).get("quiet_hours") or {}
    start_s, end_s = window.get("start"), window.get("end")
    if not start_s or not end_s:
        return None
    tz = ZoneInfo(branch.timezone or "UTC")
    local = now.astimezone(tz)
    start_h, start_m = (int(p) for p in str(start_s).split(":")[:2])
    end_h, end_m = (int(p) for p in str(end_s).split(":")[:2])
    start = dt.time(start_h, start_m)
    end = dt.time(end_h, end_m)
    today = local.date()
    if start <= end:  # e.g. 12:00-14:00
        if start <= local.time() < end:
            return dt.datetime.combine(today, end, tz).astimezone(dt.UTC)
        return None
    # overnight window, e.g. 21:00-07:00
    if local.time() >= start:
        return dt.datetime.combine(today + dt.timedelta(days=1), end, tz).astimezone(dt.UTC)
    if local.time() < end:
        return dt.datetime.combine(today, end, tz).astimezone(dt.UTC)
    return None


def throttled(rule: NotificationRule, recipient_key: str, now: dt.datetime) -> bool:
    throttle = rule.throttle or {}
    window = int(throttle.get("window_seconds") or 0)
    maximum = int(throttle.get("max") or 0)
    if window <= 0 or maximum <= 0:
        return False
    count = (
        NotificationDelivery.objects.filter(
            rule=rule,
            recipient_key=recipient_key,
            created_at__gte=now - dt.timedelta(seconds=window),
        )
        .exclude(status=DeliveryStatus.SKIPPED)
        .count()
    )
    return int(count) >= maximum


# --- deliveries -----------------------------------------------------------------------------------


@dataclass(slots=True)
class PlannedDelivery:
    recipient: Recipient
    channel: str
    locale: str
    template_code: str
    rendered: dict[str, str]
    status: str
    reason: str = ""
    scheduled_for: dt.datetime | None = None
    context: dict[str, Any] | None = None


def plan_rule(
    rule: NotificationRule, event: Event, *, now: dt.datetime | None = None
) -> list[PlannedDelivery]:
    """Everything the rule would send for the event, with the reason of every skip."""
    now = now or timezone.now()
    branch = Branch.objects.filter(pk=event.branch_id).first() if event.branch_id else rule.branch
    planned: list[PlannedDelivery] = []
    for recipient in resolve_audience(rule.audience or {}, event):
        locale = recipient.locale or (branch.default_locale if branch else "") or "fr"
        prefs = preferences_for(recipient)
        context = build_context(event, recipient, branch, locale)
        for channel in rule.channels or []:
            if channel not in CHANNEL_CODES:
                continue
            item = PlannedDelivery(
                recipient=recipient,
                channel=channel,
                locale=locale,
                template_code=rule.template_code,
                rendered={},
                status=DeliveryStatus.PENDING,
                context=context,
            )
            planned.append(item)
            if not recipient.address_for(channel):
                item.status, item.reason = DeliveryStatus.SKIPPED, "no_address"
                continue
            if prefs.get(channel) is False:
                item.status, item.reason = DeliveryStatus.SKIPPED, "preference"
                continue
            if throttled(rule, recipient.key, now):
                item.status, item.reason = DeliveryStatus.SKIPPED, "throttled"
                continue
            template = template_for(rule.template_code, locale, channel)
            if template is None:
                item.status, item.reason = DeliveryStatus.SKIPPED, "no_template"
                continue
            try:
                item.rendered = render_message(template, context, channel=channel)
            except MessageRenderError as exc:
                item.status, item.reason = DeliveryStatus.SKIPPED, f"render_error: {exc}"[:500]
                continue
            if rule.respect_quiet_hours and channel in QUIET_HOURS_CHANNELS:
                end = quiet_hours_end(branch, now)
                if end is not None:
                    item.status, item.scheduled_for = DeliveryStatus.SCHEDULED, end
    return planned


def _persist(
    rule: NotificationRule | None,
    event: Event | None,
    item: PlannedDelivery,
    *,
    dedupe_key: str,
    branch_id: uuid.UUID | None,
    fallback_of: NotificationDelivery | None = None,
) -> NotificationDelivery:
    recipient = item.recipient.as_dict()
    recipient["address"] = item.recipient.address_for(item.channel)
    context = dict(item.context or {})
    context.pop("event", None)
    delivery: NotificationDelivery
    delivery, _created = NotificationDelivery.objects.get_or_create(
        dedupe_key=dedupe_key,
        defaults={
            "rule": rule,
            "branch_id": branch_id,
            "event_id": event.id if event else None,
            "event_code": event.code if event else "",
            "recipient": recipient,
            "recipient_key": item.recipient.key,
            "channel": item.channel,
            "locale": item.locale,
            "template_code": item.template_code,
            "context": _jsonable(context),
            "rendered": item.rendered,
            "status": item.status,
            "last_error": item.reason,
            "scheduled_for": item.scheduled_for,
            "fallback_of": fallback_of,
        },
    )
    return delivery


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, dt.datetime | dt.date | uuid.UUID):
        return str(value.isoformat() if isinstance(value, dt.datetime | dt.date) else value)
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


def enqueue(delivery: NotificationDelivery) -> None:
    from procrastinate.exceptions import AlreadyEnqueued

    from mizan.apps.notify.tasks import deliver_task

    with contextlib.suppress(AlreadyEnqueued), transaction.atomic():
        deliver_task.configure(
            queueing_lock=f"deliver:{delivery.id}",
            schedule_at=delivery.scheduled_for,
            queue="notify",
        ).defer(delivery_id=str(delivery.id), tenant_id=str(delivery.tenant_id))


def process_rule(
    rule: NotificationRule, event: Event, *, now: dt.datetime | None = None
) -> list[NotificationDelivery]:
    deliveries: list[NotificationDelivery] = []
    branch_id = event.branch_id or rule.branch_id
    for item in plan_rule(rule, event, now=now):
        dedupe = f"{rule.id}:{event.id}:{item.recipient.key}:{item.channel}"
        delivery = _persist(rule, event, item, dedupe_key=dedupe, branch_id=branch_id)
        deliveries.append(delivery)
        if delivery.status in (DeliveryStatus.PENDING, DeliveryStatus.SCHEDULED):
            enqueue(delivery)
    return deliveries


def rules_for(event: Event) -> list[NotificationRule]:
    qs = NotificationRule.objects.filter(active=True, event_code=event.code)
    if event.branch_id is not None:
        qs = qs.filter(Q(branch__isnull=True) | Q(branch_id=event.branch_id))
    else:
        qs = qs.filter(branch__isnull=True)
    return list(qs.select_related("branch").order_by("code"))


@subscribe("*", name="notify.dispatch", queue="notify")
def on_event(event: Event) -> None:
    if event.tenant_id is None:
        return
    for rule in rules_for(event):
        try:
            process_rule(rule, event)
        except Exception:
            log.exception("notification rule %s failed for %s", rule.code, event.code)
            raise


# --- sending --------------------------------------------------------------------------------------


def deliver(delivery_id: uuid.UUID, tenant_id: uuid.UUID) -> NotificationDelivery:
    """Worker side: one attempt; raises for a retry, marks FAILED after the last one and then
    tries the branch's fallback channel."""
    with tenant_scope(tenant_id):
        delivery: NotificationDelivery = NotificationDelivery.objects.select_related(
            "rule", "branch"
        ).get(pk=delivery_id)
        if delivery.status not in (DeliveryStatus.PENDING, DeliveryStatus.SCHEDULED):
            return delivery
        delivery.attempts += 1
        delivery.save(update_fields=["attempts"])
    backend = channels.backend_for(delivery.channel)
    try:
        with tenant_scope(tenant_id):
            provider_id = backend.send(delivery)
    except Exception as exc:
        final = delivery.attempts >= MAX_ATTEMPTS or isinstance(exc, channels.PermanentChannelError)
        with tenant_scope(tenant_id):
            delivery.last_error = f"{type(exc).__name__}: {exc}"[:2000]
            if final:
                delivery.status = DeliveryStatus.FAILED
            delivery.save(update_fields=["last_error", "status"])
            if final:
                log.warning(
                    "delivery %s failed permanently on %s: %s",
                    delivery.id,
                    delivery.channel,
                    delivery.last_error,
                )
                fallback(delivery, same_address=not isinstance(exc, channels.PermanentChannelError))
        if not final:
            raise
        return delivery
    with tenant_scope(tenant_id):
        delivery.status = DeliveryStatus.SENT
        delivery.sent_at = timezone.now()
        delivery.provider_message_id = str(provider_id)[:200]
        delivery.last_error = ""
        delivery.save(update_fields=["status", "sent_at", "provider_message_id", "last_error"])
    return delivery


def fallback(
    failed: NotificationDelivery, *, same_address: bool = True
) -> NotificationDelivery | None:
    """Next channel of the branch fallback order the recipient can receive and that was not
    already used for the same rule, event and recipient. After a permanent failure (bad address)
    a channel reusing the same address is skipped."""
    branch = failed.branch
    order = list(
        ((branch.settings if branch else {}) or {}).get("notification_fallback_channels")
        or ["whatsapp", "sms", "email"]
    )
    recipient = Recipient.from_dict(failed.recipient)
    prefs = preferences_for(recipient)
    used = set(
        NotificationDelivery.objects.filter(
            rule=failed.rule, event_id=failed.event_id, recipient_key=failed.recipient_key
        )
        .exclude(status=DeliveryStatus.SKIPPED)
        .values_list("channel", flat=True)
    )
    for channel in order:
        if channel in used or channel == failed.channel or channel not in CHANNEL_CODES:
            continue
        address = recipient.address_for(channel)
        if not address or prefs.get(channel) is False:
            continue
        if not same_address and address == failed.address:
            continue
        template = template_for(failed.template_code, failed.locale, channel)
        if template is None:
            continue
        try:
            rendered = render_message(template, failed.context or {}, channel=channel)
        except MessageRenderError:
            continue
        item = PlannedDelivery(
            recipient=recipient,
            channel=channel,
            locale=failed.locale,
            template_code=failed.template_code,
            rendered=rendered,
            status=DeliveryStatus.PENDING,
            context=failed.context,
        )
        delivery = _persist(
            failed.rule,
            None,
            item,
            dedupe_key=f"fallback:{failed.id}:{channel}",
            branch_id=failed.branch_id,
            fallback_of=failed,
        )
        delivery.event_id = failed.event_id
        delivery.event_code = failed.event_code
        delivery.save(update_fields=["event_id", "event_code"])
        enqueue(delivery)
        return delivery
    return None


def retry(delivery: NotificationDelivery) -> NotificationDelivery:
    """Operator action: re-queue a failed or skipped delivery (a new dedupe key, same content)."""
    copy: NotificationDelivery = NotificationDelivery.objects.create(
        rule=delivery.rule,
        branch_id=delivery.branch_id,
        event_id=delivery.event_id,
        event_code=delivery.event_code,
        recipient=delivery.recipient,
        recipient_key=delivery.recipient_key,
        channel=delivery.channel,
        locale=delivery.locale,
        template_code=delivery.template_code,
        context=delivery.context,
        rendered=delivery.rendered,
        status=DeliveryStatus.PENDING,
        dedupe_key=f"retry:{delivery.id}:{uuid.uuid4().hex[:8]}",
        fallback_of=delivery,
    )
    if not copy.rendered:
        template = template_for(copy.template_code, copy.locale, copy.channel)
        if template is not None:
            copy.rendered = render_message(template, copy.context or {}, channel=copy.channel)
            copy.save(update_fields=["rendered"])
    enqueue(copy)
    return copy


def send_direct(
    template_code: str,
    channel: str,
    recipient: Recipient,
    context: dict[str, Any],
    *,
    branch: Branch | None = None,
    locale: str | None = None,
) -> NotificationDelivery:
    """A message outside any rule (one-time codes, invitations)."""
    locale = locale or recipient.locale or (branch.default_locale if branch else "") or "fr"
    template = template_for(template_code, locale, channel)
    if template is None:
        raise LookupError(f"no message template {template_code!r} for {channel}")
    full_context = {"recipient": recipient.as_dict(), "locale": locale, **context}
    item = PlannedDelivery(
        recipient=recipient,
        channel=channel,
        locale=locale,
        template_code=template_code,
        rendered=render_message(template, full_context, channel=channel),
        status=DeliveryStatus.PENDING,
        context=full_context,
    )
    if not recipient.address_for(channel):
        item.status, item.reason = DeliveryStatus.SKIPPED, "no_address"
    delivery = _persist(
        None,
        None,
        item,
        dedupe_key=f"direct:{uuid.uuid4()}",
        branch_id=branch.id if branch else None,
    )
    if delivery.status == DeliveryStatus.PENDING:
        enqueue(delivery)
    return delivery
