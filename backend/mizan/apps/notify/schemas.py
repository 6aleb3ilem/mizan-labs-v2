import datetime as dt
import uuid
from typing import Any

from ninja import Schema
from pydantic import Field

CODE = r"^[A-Z0-9_.-]{2,64}$"


class RuleOut(Schema):
    id: uuid.UUID
    branch_id: uuid.UUID | None
    code: str
    event_code: str
    audience: dict[str, Any]
    channels: list[str]
    template_code: str
    throttle: dict[str, Any]
    digest: dict[str, Any]
    respect_quiet_hours: bool
    active: bool
    description: str
    row_version: int


class RuleIn(Schema):
    code: str = Field(pattern=CODE)
    branch_id: uuid.UUID | None = None
    event_code: str = ""
    audience: dict[str, Any] = {}
    channels: list[str]
    template_code: str = Field(pattern=CODE)
    throttle: dict[str, Any] = {}
    digest: dict[str, Any] = {}
    respect_quiet_hours: bool = True
    active: bool = True
    description: str = ""


class RulePatch(Schema):
    event_code: str | None = None
    audience: dict[str, Any] | None = None
    channels: list[str] | None = None
    template_code: str | None = Field(default=None, pattern=CODE)
    throttle: dict[str, Any] | None = None
    digest: dict[str, Any] | None = None
    respect_quiet_hours: bool | None = None
    active: bool | None = None
    description: str | None = None


class SimulateIn(Schema):
    payload: dict[str, Any] = {}
    branch_id: uuid.UUID | None = None


class SimulatedDeliveryOut(Schema):
    recipient: dict[str, Any]
    channel: str
    locale: str
    status: str
    reason: str
    scheduled_for: dt.datetime | None
    rendered: dict[str, str]


class TemplateOut(Schema):
    id: uuid.UUID
    code: str
    locale: str
    channel: str
    subject: str
    body: str
    html: str
    variables: dict[str, Any]
    active: bool
    row_version: int


class TemplateIn(Schema):
    code: str = Field(pattern=CODE)
    locale: str = "fr"
    channel: str
    subject: str = ""
    body: str
    html: str = ""
    variables: dict[str, Any] = {}
    sample: dict[str, Any] = {}


class TemplatePatch(Schema):
    subject: str | None = None
    body: str | None = None
    html: str | None = None
    variables: dict[str, Any] | None = None
    active: bool | None = None
    sample: dict[str, Any] = {}


class TemplatePreviewIn(Schema):
    subject: str = ""
    body: str
    html: str = ""
    channel: str = "email"
    sample: dict[str, Any] = {}


class RenderedOut(Schema):
    subject: str
    body: str
    html: str


class DeliveryOut(Schema):
    id: uuid.UUID
    rule_id: uuid.UUID | None
    branch_id: uuid.UUID | None
    event_id: uuid.UUID | None
    event_code: str
    recipient: dict[str, Any]
    recipient_key: str
    channel: str
    locale: str
    template_code: str
    rendered: dict[str, Any]
    status: str
    attempts: int
    last_error: str
    scheduled_for: dt.datetime | None
    sent_at: dt.datetime | None
    provider_message_id: str
    fallback_of_id: uuid.UUID | None
    created_at: dt.datetime


class DeliveryFilters(Schema):
    rule_id: uuid.UUID | None = None
    event_id: uuid.UUID | None = None
    event_code: str | None = None
    status: str | None = None
    channel: str | None = None
    recipient_key: str | None = None
    since: dt.datetime | None = None


class NotificationOut(Schema):
    id: uuid.UUID
    event_id: uuid.UUID | None
    event_code: str
    title: str
    body: str
    link: str
    data: dict[str, Any]
    read_at: dt.datetime | None
    created_at: dt.datetime


class InboxFilters(Schema):
    unread: bool | None = None


class UnreadOut(Schema):
    unread: int


class MarkReadIn(Schema):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=500)


class MarkedOut(Schema):
    marked: int


class PreferencesOut(Schema):
    email: bool = True
    sms: bool = True
    whatsapp: bool = True
    in_app: bool = True


class PreferencesIn(Schema):
    email: bool | None = None
    sms: bool | None = None
    whatsapp: bool | None = None
    in_app: bool | None = None
