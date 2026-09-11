import datetime as dt
import uuid
from typing import Any

from ninja import Schema
from pydantic import Field


class TemplateOut(Schema):
    id: uuid.UUID
    branch_id: uuid.UUID | None
    kind: str
    locale: str
    version: int
    status: str
    name: str
    html: str
    css: str
    variables: dict[str, Any]
    sample_data: dict[str, Any]
    approved_at: dt.datetime | None


class TemplateSummaryOut(Schema):
    id: uuid.UUID
    branch_id: uuid.UUID | None
    kind: str
    locale: str
    version: int
    status: str
    name: str
    approved_at: dt.datetime | None


class TemplateIn(Schema):
    kind: str = Field(pattern=r"^[A-Z0-9_.-]{2,64}$")
    locale: str = "fr"
    branch_id: uuid.UUID | None = None
    name: str = ""
    html: str
    css: str = ""
    variables: dict[str, Any] = {}
    sample_data: dict[str, Any] = {}


class TemplateVersionIn(Schema):
    name: str | None = None
    html: str | None = None
    css: str | None = None
    variables: dict[str, Any] | None = None
    sample_data: dict[str, Any] | None = None


class PreviewIn(Schema):
    data: dict[str, Any] | None = None
    locale: str | None = None


class PrintProfileOut(Schema):
    id: uuid.UUID
    branch_id: uuid.UUID
    kind: str
    defaults: dict[str, Any]


class PrintProfileIn(Schema):
    branch_id: uuid.UUID
    kind: str = Field(pattern=r"^[A-Z0-9_.-]{2,64}$")
    defaults: dict[str, Any]


class DocumentOut(Schema):
    id: uuid.UUID
    branch_id: uuid.UUID
    kind: str
    number: str
    subject_type: str
    subject_id: uuid.UUID | None
    subject: dict[str, Any]
    digest: dict[str, Any]
    issued_at: dt.datetime
    issued_by: uuid.UUID | None
    signatory_id: uuid.UUID | None
    template_version: int
    locale: str
    content_hash: str
    pdf_sha256: str
    pdf_size: int
    seal_level: str
    status: str
    superseded_by_id: uuid.UUID | None
    revoked_reason: str
    verify_token: str
    short_code: str
    transparency_leaf_index: int | None


class RenditionIn(Schema):
    signature_image: bool = True
    digital_signature: bool = True
    qr: bool = True
    watermark: str = Field(default="", max_length=32)
    locale: str | None = None


class RenditionOut(Schema):
    id: uuid.UUID
    document_id: uuid.UUID
    options: dict[str, Any]
    produced_at: dt.datetime
    sha256: str
    size: int


class DigestIn(Schema):
    short_code: str = Field(min_length=6, max_length=8)


class SuspiciousIn(Schema):
    reporter_name: str = ""
    reporter_contact: str = ""
    message: str = Field(default="", max_length=4000)
