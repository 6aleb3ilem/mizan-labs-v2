"""Notifications API (SPEC A.2): rules, message templates, delivery log, inbox, preferences."""

import uuid
from typing import Any

from django.http import HttpRequest
from ninja import Query, Router, Status

from mizan.apps.identity.authz import requires
from mizan.apps.notify import dispatch, services
from mizan.apps.notify.models import (
    CHANNEL_CODES,
    DeliveryStatus,
    MessageTemplate,
    Notification,
    NotificationDelivery,
    NotificationRule,
)
from mizan.apps.notify.rendering import check_template, render_html, render_text
from mizan.apps.notify.schemas import (
    DeliveryFilters,
    DeliveryOut,
    InboxFilters,
    MarkedOut,
    MarkReadIn,
    NotificationOut,
    PreferencesIn,
    PreferencesOut,
    RenderedOut,
    RuleIn,
    RuleOut,
    RulePatch,
    SimulatedDeliveryOut,
    SimulateIn,
    TemplateIn,
    TemplateOut,
    TemplatePatch,
    TemplatePreviewIn,
    UnreadOut,
)
from mizan.platform.api.errors import Conflict, NotFound, Unauthorized, UnprocessableEntity
from mizan.platform.api.pagination import CursorParams, Page, paginate

router = Router(tags=["notifications"])


def _get[M](model: type[M], pk: uuid.UUID) -> M:
    try:
        row: M = model._default_manager.get(pk=pk)  # type: ignore[attr-defined]
    except model.DoesNotExist as exc:  # type: ignore[attr-defined]
        raise NotFound() from exc
    return row


def _principal(request: HttpRequest) -> Any:
    principal = getattr(request, "principal", None)
    if principal is None:
        raise Unauthorized()
    return principal


# --- rules ----------------------------------------------------------------------------------------


@router.get("/notification-rules", response=list[RuleOut], summary="Notification rules")
@requires("notification_rule", "view")
def list_rules(
    request: HttpRequest, event_code: str | None = None, branch_id: uuid.UUID | None = None
) -> list[NotificationRule]:
    qs = NotificationRule.objects.all()
    if event_code:
        qs = qs.filter(event_code=event_code)
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    return list(qs)


@router.post("/notification-rules", response={201: RuleOut}, summary="Create a rule")
@requires("notification_rule", "configure")
def create_rule(request: HttpRequest, payload: RuleIn) -> Status[NotificationRule]:
    data = payload.model_dump()
    services.validate_rule(data)
    if NotificationRule.objects.filter(branch_id=payload.branch_id, code=payload.code).exists():
        raise Conflict("notify.rule.exists", code="rule_exists")
    rule = NotificationRule.objects.create(**data)
    services.changed("notification_rule", rule.id, "created", after=payload.model_dump(mode="json"))
    return Status(201, rule)


@router.get("/notification-rules/{uuid:rule_id}", response=RuleOut)
@requires("notification_rule", "view")
def get_rule(request: HttpRequest, rule_id: uuid.UUID) -> NotificationRule:
    return _get(NotificationRule, rule_id)


@router.patch("/notification-rules/{uuid:rule_id}", response=RuleOut, summary="Edit a rule")
@requires("notification_rule", "configure")
def patch_rule(request: HttpRequest, rule_id: uuid.UUID, payload: RulePatch) -> NotificationRule:
    rule = _get(NotificationRule, rule_id)
    changes = payload.model_dump(exclude_unset=True)
    before = {k: getattr(rule, k) for k in changes}
    merged = {
        "event_code": rule.event_code,
        "digest": rule.digest,
        "channels": rule.channels,
        "audience": rule.audience,
        "throttle": rule.throttle,
        **changes,
    }
    services.validate_rule(merged)
    for key, value in changes.items():
        setattr(rule, key, value)
    rule.save(update_fields=list(changes))
    services.changed("notification_rule", rule.id, "updated", before=before, after=changes)
    return rule


@router.post(
    "/notification-rules/{uuid:rule_id}:simulate",
    response=list[SimulatedDeliveryOut],
    summary="Dry run: recipients and rendered messages for a sample payload",
)
@requires("notification_rule", "view")
def simulate_rule(
    request: HttpRequest, rule_id: uuid.UUID, payload: SimulateIn
) -> list[dict[str, Any]]:
    rule = _get(NotificationRule, rule_id)
    return services.simulate_rule(rule, payload.payload, branch_id=payload.branch_id)


# --- templates ------------------------------------------------------------------------------------


@router.get("/message-templates", response=list[TemplateOut], summary="Message templates")
@requires("notification_rule", "view")
def list_templates(
    request: HttpRequest, code: str | None = None, channel: str | None = None
) -> list[MessageTemplate]:
    qs = MessageTemplate.objects.all()
    if code:
        qs = qs.filter(code=code)
    if channel:
        qs = qs.filter(channel=channel)
    return list(qs)


@router.post("/message-templates", response={201: TemplateOut}, summary="Create a template")
@requires("notification_rule", "configure")
def create_template(request: HttpRequest, payload: TemplateIn) -> Status[MessageTemplate]:
    if payload.channel not in CHANNEL_CODES:
        raise UnprocessableEntity(
            "notify.template.unknown_channel",
            details=[{"loc": ["channel"], "msg": payload.channel}],
        )
    if MessageTemplate.objects.filter(
        code=payload.code, locale=payload.locale, channel=payload.channel
    ).exists():
        raise Conflict("notify.template.exists", code="template_exists")
    check_template(payload.subject, payload.body, payload.html, payload.sample)
    data = payload.model_dump(exclude={"sample"})
    template = MessageTemplate.objects.create(**data)
    services.changed("message_template", template.id, "created", after=data)
    return Status(201, template)


@router.patch(
    "/message-templates/{uuid:template_id}", response=TemplateOut, summary="Edit a template"
)
@requires("notification_rule", "configure")
def patch_template(
    request: HttpRequest, template_id: uuid.UUID, payload: TemplatePatch
) -> MessageTemplate:
    template = _get(MessageTemplate, template_id)
    changes = payload.model_dump(exclude_unset=True, exclude={"sample"})
    before = {k: getattr(template, k) for k in changes}
    check_template(
        changes.get("subject", template.subject),
        changes.get("body", template.body),
        changes.get("html", template.html),
        payload.sample,
    )
    for key, value in changes.items():
        setattr(template, key, value)
    template.save(update_fields=list(changes))
    services.changed("message_template", template.id, "updated", before=before, after=changes)
    return template


@router.post(
    "/message-templates:preview",
    response=RenderedOut,
    summary="Render a draft template with sample data",
)
@requires("notification_rule", "view")
def preview_template(request: HttpRequest, payload: TemplatePreviewIn) -> dict[str, str]:
    check_template(payload.subject, payload.body, payload.html, payload.sample)
    return {
        "subject": render_text(payload.subject, payload.sample) if payload.subject else "",
        "body": render_text(payload.body, payload.sample),
        "html": render_html(payload.html, payload.sample)
        if payload.html and payload.channel == "email"
        else "",
    }


# --- delivery log ---------------------------------------------------------------------------------


def _delivery_out(row: NotificationDelivery) -> dict[str, Any]:
    return DeliveryOut.from_orm(row).model_dump()


@router.get(
    "/notification-deliveries", response=Page[DeliveryOut], summary="Delivery log (every channel)"
)
@requires("notification_rule", "view")
def list_deliveries(
    request: HttpRequest, filters: Query[DeliveryFilters], params: Query[CursorParams]
) -> dict[str, Any]:
    qs = NotificationDelivery.objects.all()
    if filters.rule_id:
        qs = qs.filter(rule_id=filters.rule_id)
    if filters.event_id:
        qs = qs.filter(event_id=filters.event_id)
    if filters.event_code:
        qs = qs.filter(event_code=filters.event_code)
    if filters.status:
        qs = qs.filter(status=filters.status)
    if filters.channel:
        qs = qs.filter(channel=filters.channel)
    if filters.recipient_key:
        qs = qs.filter(recipient_key=filters.recipient_key)
    if filters.since:
        qs = qs.filter(created_at__gte=filters.since)
    return paginate(qs, params, _delivery_out)


@router.post(
    "/notification-deliveries/{uuid:delivery_id}:retry",
    response={201: DeliveryOut},
    summary="Re-queue a failed or skipped delivery",
)
@requires("notification_rule", "configure")
def retry_delivery(request: HttpRequest, delivery_id: uuid.UUID) -> Status[NotificationDelivery]:
    delivery = _get(NotificationDelivery, delivery_id)
    if delivery.status not in (DeliveryStatus.FAILED, DeliveryStatus.SKIPPED):
        raise Conflict("notify.delivery.not_retryable", code="delivery_not_retryable")
    return Status(201, dispatch.retry(delivery))


# --- inbox (every authenticated user) -------------------------------------------------------------


def _notification_out(row: Notification) -> dict[str, Any]:
    return NotificationOut.from_orm(row).model_dump()


@router.get("/me/notifications", response=Page[NotificationOut], summary="My inbox")
def my_notifications(
    request: HttpRequest, filters: Query[InboxFilters], params: Query[CursorParams]
) -> dict[str, Any]:
    principal = _principal(request)
    qs = Notification.objects.filter(user_id=principal.user_id)
    if filters.unread is True:
        qs = qs.filter(read_at__isnull=True)
    elif filters.unread is False:
        qs = qs.filter(read_at__isnull=False)
    return paginate(qs, params, _notification_out)


@router.get("/me/notifications/unread-count", response=UnreadOut)
def my_unread_count(request: HttpRequest) -> dict[str, int]:
    return {"unread": services.unread_count(_principal(request).user_id)}


@router.post("/me/notifications:read", response=MarkedOut, summary="Mark some as read")
def mark_read(request: HttpRequest, payload: MarkReadIn) -> dict[str, int]:
    return {"marked": services.mark_read(_principal(request).user_id, payload.ids)}


@router.post("/me/notifications:read-all", response=MarkedOut, summary="Mark everything as read")
def mark_all_read(request: HttpRequest) -> dict[str, int]:
    return {"marked": services.mark_all_read(_principal(request).user_id)}


@router.get("/me/notification-preferences", response=PreferencesOut)
def my_preferences(request: HttpRequest) -> dict[str, bool]:
    return services.preferences("user", _principal(request).user_id)


@router.put("/me/notification-preferences", response=PreferencesOut)
def set_my_preferences(request: HttpRequest, payload: PreferencesIn) -> dict[str, bool]:
    values = payload.model_dump(exclude_unset=True, exclude_none=True)
    return services.set_preferences("user", _principal(request).user_id, values)


@router.get(
    "/contacts/{uuid:contact_id}/notification-preferences",
    response=PreferencesOut,
    summary="Channel preferences of a client contact",
)
@requires("contact", "view")
def contact_preferences(request: HttpRequest, contact_id: uuid.UUID) -> dict[str, bool]:
    return services.preferences("contact", contact_id)


@router.put("/contacts/{uuid:contact_id}/notification-preferences", response=PreferencesOut)
@requires("contact", "edit")
def set_contact_preferences(
    request: HttpRequest, contact_id: uuid.UUID, payload: PreferencesIn
) -> dict[str, bool]:
    values = payload.model_dump(exclude_unset=True, exclude_none=True)
    return services.set_preferences("contact", contact_id, values)
