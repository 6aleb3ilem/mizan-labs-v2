"""Digests (SPEC §19.2): a rule with ``digest.cron`` evaluated in each branch's timezone by the
periodic scheduler; the content comes from a registered provider (the laboratory app supplies
the real counts, the default provider ships the shape)."""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Callable
from typing import Any
from zoneinfo import ZoneInfo

from django.db.models import Q
from django.utils import timezone

from mizan.apps.notify import cron
from mizan.apps.notify.dispatch import PlannedDelivery, _persist, enqueue, template_for
from mizan.apps.notify.models import DeliveryStatus, NotificationDelivery, NotificationRule
from mizan.apps.notify.recipients import staff_by_roles, users_by_ids
from mizan.apps.notify.rendering import MessageRenderError, render_message
from mizan.apps.org.models import Branch, Department, Tenant, TenantStatus
from mizan.platform.db.tenancy import tenant_scope
from mizan.platform.scheduler import periodic

log = logging.getLogger("mizan.notify.digest")

DigestProvider = Callable[[Branch, Department | None, dt.date], dict[str, Any]]
_providers: dict[str, DigestProvider] = {}
WINDOW = dt.timedelta(minutes=15)


def register_digest_provider(name: str) -> Callable[[DigestProvider], DigestProvider]:
    def decorator(func: DigestProvider) -> DigestProvider:
        _providers[name] = func  # a later registration (the lab app) replaces the placeholder
        return func

    return decorator


@register_digest_provider("daily_supervisor")
def daily_supervisor(branch: Branch, department: Department | None, day: dt.date) -> dict[str, Any]:
    """Counts of the supervisor digest; the laboratory app overrides this with real figures."""
    return {"intakes": 0, "done": 0, "todo": 0, "overdue": 0, "tomorrow": 0}


def digest_context(rule: NotificationRule, branch: Branch, day: dt.date) -> dict[str, Any]:
    provider = _providers.get(str((rule.digest or {}).get("query") or "daily_supervisor"))
    if provider is None:
        raise LookupError("unknown digest provider")
    departments = list(Department.objects.filter(branch=branch, active=True))
    sections: list[dict[str, Any]] = []
    totals = {"intakes": 0, "done": 0, "todo": 0, "overdue": 0, "tomorrow": 0}
    for department in departments or [None]:
        counts = provider(branch, department, day)
        for key in totals:
            totals[key] += int(counts.get(key, 0))
        sections.append(
            {
                "department": (department.label() or department.code)
                if department
                else branch.code,
                **counts,
            }
        )
    return {
        "date": day.isoformat(),
        "branch": {"code": branch.code, "legal_name": branch.legal_name},
        "departments": sections,
        "department": ", ".join(s["department"] for s in sections),
        **totals,
    }


def run_branch_digest(
    rule: NotificationRule, branch: Branch, now: dt.datetime, *, window: dt.timedelta = WINDOW
) -> list[NotificationDelivery]:
    expression = str((rule.digest or {}).get("cron") or "")
    if not expression:
        return []
    tz = ZoneInfo(branch.timezone or "UTC")
    local_now = now.astimezone(tz).replace(tzinfo=None)
    fired_at = cron.matches_window(expression, local_now - window, local_now)
    if fired_at is None:
        return []
    stamp = fired_at.strftime("%Y-%m-%dT%H:%M")
    if NotificationDelivery.objects.filter(
        dedupe_key__startswith=f"digest:{rule.id}:{branch.id}:{stamp}:"
    ).exists():
        return []
    audience = rule.audience or {}
    recipients = staff_by_roles(audience.get("roles") or [], branch_id=branch.id)
    recipients += users_by_ids([r for r in (audience.get("user_ids") or []) if r])
    context = digest_context(rule, branch, fired_at.date())
    deliveries: list[NotificationDelivery] = []
    seen: set[str] = set()
    for recipient in recipients:
        if recipient.key in seen:
            continue
        seen.add(recipient.key)
        locale = recipient.locale or branch.default_locale or "fr"
        for channel in rule.channels or ["email"]:
            item = PlannedDelivery(
                recipient=recipient,
                channel=channel,
                locale=locale,
                template_code=rule.template_code,
                rendered={},
                status=DeliveryStatus.PENDING,
                context={**context, "recipient": recipient.as_dict(), "locale": locale},
            )
            template = template_for(rule.template_code, locale, channel)
            if not recipient.address_for(channel):
                item.status, item.reason = DeliveryStatus.SKIPPED, "no_address"
            elif template is None:
                item.status, item.reason = DeliveryStatus.SKIPPED, "no_template"
            else:
                try:
                    item.rendered = render_message(template, item.context or {}, channel=channel)
                except MessageRenderError as exc:
                    item.status, item.reason = DeliveryStatus.SKIPPED, f"render_error: {exc}"
            delivery = _persist(
                rule,
                None,
                item,
                dedupe_key=f"digest:{rule.id}:{branch.id}:{stamp}:{recipient.key}:{channel}",
                branch_id=branch.id,
            )
            deliveries.append(delivery)
            if delivery.status == DeliveryStatus.PENDING:
                enqueue(delivery)
    return deliveries


def run_tenant_digests(now: dt.datetime | None = None) -> list[NotificationDelivery]:
    now = now or timezone.now()
    produced: list[NotificationDelivery] = []
    rules = NotificationRule.objects.filter(active=True, event_code="").exclude(
        Q(digest={}) | Q(digest__cron__isnull=True)
    )
    for rule in rules.select_related("branch"):
        branches = [rule.branch] if rule.branch else list(Branch.objects.filter(active=True))
        for branch in branches:
            if branch is not None:
                produced.extend(run_branch_digest(rule, branch, now))
    return produced


@periodic("notify.digests", every=dt.timedelta(minutes=5))
def run_digests(now: dt.datetime) -> None:
    for tenant in Tenant.objects.filter(status=TenantStatus.ACTIVE):
        with tenant_scope(tenant.id):
            produced = run_tenant_digests(now)
            if produced:
                log.info("tenant %s: %d digest deliveries", tenant.code, len(produced))
