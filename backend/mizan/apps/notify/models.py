"""Notification rules, message templates, preferences, deliveries and the in-app inbox (SPEC §10.8, §19)."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from mizan.platform.db import CodeField, TenantModel


class Channel(models.TextChoices):
    EMAIL = "email", "E-mail"
    SMS = "sms", "SMS"
    WHATSAPP = "whatsapp", "WhatsApp"
    IN_APP = "in_app", "In-app (SSE + inbox, portal)"


CHANNEL_CODES: tuple[str, ...] = tuple(c.value for c in Channel)


class NotificationRule(TenantModel):
    """``notification_rule(event_code, audience, channels[], template, throttle, digest, active)``.

    ``audience`` is ``{"roles": [...], "contact_roles": [...], "user_ids": [...],
    "payload_user_keys": [...]}``: staff roles of the event's branch (and of the departments named
    by the payload), client contact roles resolved from the payload or a registered resolver,
    explicit users, and payload keys carrying user ids (``owner_id``, ``assignee_id``).
    A digest rule has no ``event_code``; ``digest`` is ``{"cron": "30 6 * * *", "query": "..."}``
    evaluated in the branch timezone.
    """

    branch = models.ForeignKey(
        "org.Branch", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    code = CodeField()
    event_code = models.CharField(max_length=64, blank=True, default="", db_index=True)
    audience = models.JSONField(default=dict, blank=True)
    channels = models.JSONField(default=list, blank=True)
    template_code = CodeField()
    throttle = models.JSONField(default=dict, blank=True)  # {"window_seconds": n, "max": m}
    digest = models.JSONField(default=dict, blank=True)  # {"cron": "...", "query": "..."}
    respect_quiet_hours = models.BooleanField(default=True)
    active = models.BooleanField(default=True)
    description = models.CharField(max_length=200, blank=True, default="")

    class Meta(TenantModel.Meta):
        db_table = "notification_rule"
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "branch", "code"],
                name="uq_notification_rule_code",
                nulls_distinct=False,
            )
        ]

    def __str__(self) -> str:
        return f"{self.code} ({self.event_code or 'digest'})"

    @property
    def is_digest(self) -> bool:
        return bool((self.digest or {}).get("cron"))


class MessageTemplate(TenantModel):
    """``message_template(code, locale, channel, subject, body)``; Jinja in a sandbox."""

    code = CodeField()
    locale = models.CharField(max_length=8, default="fr")
    channel = models.CharField(max_length=16, choices=Channel.choices)
    subject = models.CharField(max_length=300, blank=True, default="")  # e-mail, in-app title
    body = models.TextField()
    html = models.TextField(blank=True, default="")  # optional rich e-mail body
    variables = models.JSONField(default=dict, blank=True)  # documented placeholders
    active = models.BooleanField(default=True)

    class Meta(TenantModel.Meta):
        db_table = "message_template"
        ordering = ["code", "channel", "locale"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "code", "locale", "channel"], name="uq_message_template"
            )
        ]

    def __str__(self) -> str:
        return f"{self.code}/{self.channel}/{self.locale}"


class RecipientType(models.TextChoices):
    USER = "user", "Staff or portal user"
    CONTACT = "contact", "Client contact"


class ContactChannelPreference(TenantModel):
    """``contact_channel_preference(contact_id, channel, enabled)``; also holds users' own choices."""

    recipient_type = models.CharField(
        max_length=16, choices=RecipientType.choices, default=RecipientType.CONTACT
    )
    recipient_id = models.UUIDField(db_index=True)
    channel = models.CharField(max_length=16, choices=Channel.choices)
    enabled = models.BooleanField(default=True)

    class Meta(TenantModel.Meta):
        db_table = "contact_channel_preference"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "recipient_type", "recipient_id", "channel"],
                name="uq_contact_channel_preference",
            )
        ]

    def __str__(self) -> str:
        return f"{self.recipient_type}:{self.recipient_id} {self.channel}={self.enabled}"


class DeliveryStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SCHEDULED = "SCHEDULED", "Scheduled (quiet hours)"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"
    SKIPPED = "SKIPPED", "Skipped"


class NotificationDelivery(TenantModel):
    """``notification_delivery(rule, event, recipient, channel, rendered, status, attempts, last_error)``."""

    rule = models.ForeignKey(
        NotificationRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deliveries",
    )
    branch = models.ForeignKey(
        "org.Branch", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    event_id = models.UUIDField(null=True, blank=True, db_index=True)
    event_code = models.CharField(max_length=64, blank=True, default="", db_index=True)
    recipient = models.JSONField(default=dict)  # {type, id, name, address, locale}
    recipient_key = models.CharField(max_length=120, db_index=True)  # "user:<id>" | "contact:<id>"
    channel = models.CharField(max_length=16, choices=Channel.choices)
    locale = models.CharField(max_length=8, default="fr")
    template_code = models.CharField(max_length=64, blank=True, default="")
    context = models.JSONField(default=dict, blank=True)  # render context, kept for fallbacks
    rendered = models.JSONField(default=dict)  # {subject, body, html}
    status = models.CharField(
        max_length=16, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING
    )
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    provider_message_id = models.CharField(max_length=200, blank=True, default="")
    dedupe_key = models.CharField(max_length=200)
    fallback_of = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="fallbacks"
    )

    class Meta(TenantModel.Meta):
        db_table = "notification_delivery"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "dedupe_key"], name="uq_notification_delivery_dedupe"
            )
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "recipient_key", "created_at"],
                name="idx_notification_delivery_rcpt",
            )
        ]

    def __str__(self) -> str:
        return f"{self.channel} → {self.recipient_key} [{self.status}]"

    @property
    def address(self) -> str:
        return str((self.recipient or {}).get("address") or "")


class Notification(TenantModel):
    """The in-app inbox of a user (SPEC §19.2); pushed live over SSE as ``notification``."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    delivery = models.ForeignKey(
        NotificationDelivery,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    event_id = models.UUIDField(null=True, blank=True)
    event_code = models.CharField(max_length=64, blank=True, default="")
    title = models.CharField(max_length=300)
    body = models.TextField(blank=True, default="")
    link = models.CharField(max_length=500, blank=True, default="")  # in-app path
    data = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta(TenantModel.Meta):
        db_table = "notification"
        indexes = [
            models.Index(
                fields=["user", "read_at", "created_at"], name="idx_notification_user_unread"
            )
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    def mark_read(self) -> None:
        if self.read_at is None:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at"])
