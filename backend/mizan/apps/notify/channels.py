"""Channel backends (SPEC §19.2): e-mail (SMTP), SMS (local aggregator adapter), WhatsApp
Business Cloud API, in-app (inbox row + SSE push). Dev and tests use the log backends."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
import uuid
from email.utils import make_msgid
from typing import Any, Protocol

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from mizan.apps.notify.models import Notification, NotificationDelivery
from mizan.platform.ids import uuid7
from mizan.platform.realtime.publish import publish_to_user

log = logging.getLogger("mizan.notify.channels")


class ChannelError(Exception):
    """A transient failure: the delivery is retried."""


class PermanentChannelError(ChannelError):
    """Not worth retrying (bad address, rejected content, unsupported)."""


class ChannelBackend(Protocol):
    code: str

    def send(self, delivery: NotificationDelivery) -> str:
        """Send and return the provider message id."""
        ...


# Messages sent by the log backends, for the developer console and the tests.
LOG_OUTBOX: list[dict[str, Any]] = []


class LogBackend:
    def __init__(self, code: str) -> None:
        self.code = code

    def send(self, delivery: NotificationDelivery) -> str:
        message_id = f"log:{uuid7()}"
        entry = {
            "id": message_id,
            "channel": self.code,
            "to": delivery.address,
            "subject": delivery.rendered.get("subject", ""),
            "body": delivery.rendered.get("body", ""),
        }
        LOG_OUTBOX.append(entry)
        log.info("%s → %s: %s", self.code, entry["to"], entry["body"][:200])
        return message_id


class EmailBackend:
    code = "email"

    def send(self, delivery: NotificationDelivery) -> str:
        address = delivery.address
        if "@" not in address:
            raise PermanentChannelError(f"invalid e-mail address {address!r}")
        message_id = make_msgid(
            domain=str(settings.MIZAN_NOTIFY.get("email_domain") or "mizanlabs")
        )
        message = EmailMultiAlternatives(
            subject=delivery.rendered.get("subject") or "",
            body=delivery.rendered.get("body") or "",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[address],
            headers={"Message-ID": message_id, "X-Mizan-Delivery": str(delivery.id)},
        )
        html = delivery.rendered.get("html")
        if html:
            message.attach_alternative(html, "text/html")
        try:
            message.send(fail_silently=False)
        except OSError as exc:  # SMTP connection problems are transient
            raise ChannelError(str(exc)) from exc
        return message_id


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:500]
        if 400 <= exc.code < 500 and exc.code != 429:
            raise PermanentChannelError(f"HTTP {exc.code}: {body}") from exc
        raise ChannelError(f"HTTP {exc.code}: {body}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ChannelError(str(exc)) from exc
    try:
        data: dict[str, Any] = json.loads(raw or b"{}")
    except ValueError:
        return {}
    return data


class HttpSmsBackend:
    """Generic adapter for a local SMS aggregator: ``POST {to, text, sender}`` with a bearer token."""

    code = "sms"

    def send(self, delivery: NotificationDelivery) -> str:
        conf = settings.MIZAN_NOTIFY
        url = conf.get("sms_url")
        if not url:
            raise PermanentChannelError("SMS aggregator URL is not configured")
        if not delivery.address.startswith("+"):
            raise PermanentChannelError(f"phone number {delivery.address!r} is not E.164")
        response = _post_json(
            str(url),
            {
                "to": delivery.address,
                "text": delivery.rendered.get("body", ""),
                "sender": conf.get("sms_sender") or "MizanLabs",
                "reference": str(delivery.id),
            },
            {"Authorization": f"Bearer {conf.get('sms_token') or ''}"},
        )
        return str(response.get("id") or response.get("message_id") or f"sms:{delivery.id}")


class WhatsAppCloudBackend:
    """WhatsApp Business Cloud API. Business-initiated messages must use a pre-approved
    template: the template named after the message template code (lower case) with a single
    body parameter ``{{1}}`` carrying the rendered text. Free-form text is sent when the
    configuration says so (inside a 24 h customer-service window)."""

    code = "whatsapp"

    def send(self, delivery: NotificationDelivery) -> str:
        conf = settings.MIZAN_NOTIFY
        phone_number_id = conf.get("whatsapp_phone_number_id")
        token = conf.get("whatsapp_access_token")
        if not phone_number_id or not token:
            raise PermanentChannelError("WhatsApp Cloud API is not configured")
        if not delivery.address.startswith("+"):
            raise PermanentChannelError(f"phone number {delivery.address!r} is not E.164")
        to = delivery.address.lstrip("+")
        body = delivery.rendered.get("body", "")
        payload: dict[str, Any] = {"messaging_product": "whatsapp", "to": to}
        if conf.get("whatsapp_free_text"):
            payload.update({"type": "text", "text": {"preview_url": True, "body": body}})
        else:
            payload.update(
                {
                    "type": "template",
                    "template": {
                        "name": (delivery.template_code or "generic").lower(),
                        "language": {"code": delivery.locale or "fr"},
                        "components": [
                            {"type": "body", "parameters": [{"type": "text", "text": body}]}
                        ],
                    },
                }
            )
        version = conf.get("whatsapp_api_version") or "v20.0"
        response = _post_json(
            f"https://graph.facebook.com/{version}/{phone_number_id}/messages",
            payload,
            {"Authorization": f"Bearer {token}"},
        )
        messages = response.get("messages") or [{}]
        return str(messages[0].get("id") or f"wa:{delivery.id}")


class InAppBackend:
    code = "in_app"

    def send(self, delivery: NotificationDelivery) -> str:
        user_id = delivery.address
        if not user_id:
            raise PermanentChannelError("recipient has no in-app user")
        notification: Notification = Notification.objects.create(
            user_id=uuid.UUID(user_id),
            delivery=delivery,
            event_id=delivery.event_id,
            event_code=delivery.event_code,
            title=delivery.rendered.get("subject") or delivery.rendered.get("body", "")[:300],
            body=delivery.rendered.get("body", ""),
            link=str((delivery.context or {}).get("app_link") or ""),
            data={
                "event_code": delivery.event_code,
                "aggregate_type": (delivery.context or {}).get("aggregate_type"),
                "aggregate_id": (delivery.context or {}).get("aggregate_id"),
            },
        )
        publish_to_user(
            delivery.tenant_id,
            notification.user_id,
            "notification",
            {
                "id": str(notification.id),
                "title": notification.title,
                "body": notification.body[:500],
                "link": notification.link,
                "event_code": notification.event_code,
                "created_at": notification.created_at.isoformat(),
            },
        )
        return f"in_app:{notification.id}"


def backend_for(channel: str) -> ChannelBackend:
    conf = settings.MIZAN_NOTIFY
    if channel == "email":
        return LogBackend("email") if conf.get("email_provider") == "log" else EmailBackend()
    if channel == "sms":
        return HttpSmsBackend() if conf.get("sms_provider") == "http" else LogBackend("sms")
    if channel == "whatsapp":
        if conf.get("whatsapp_provider") == "cloud":
            return WhatsAppCloudBackend()
        return LogBackend("whatsapp")
    if channel == "in_app":
        return InAppBackend()
    raise PermanentChannelError(f"unknown channel {channel!r}")
