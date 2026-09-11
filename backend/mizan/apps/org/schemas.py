import uuid
from typing import Any

from ninja import Schema
from pydantic import Field

from mizan.platform.api.schemas import LabelsSchema

CODE_PATTERN = r"^[A-Z0-9_.-]{2,64}$"


class TenantOut(Schema):
    id: uuid.UUID
    code: str
    name: str
    theme: dict[str, Any]
    plan: str
    status: str


class TenantPatch(Schema):
    name: str | None = None
    theme: dict[str, Any] | None = None


class TenantCreate(Schema):
    code: str = Field(pattern=CODE_PATTERN)
    name: str
    admin_email: str
    admin_display_name: str = ""
    admin_temporary_password: str = Field(min_length=10)


class BranchOut(Schema):
    id: uuid.UUID
    code: str
    legal_name: str
    trade_name: str
    identifiers: dict[str, Any]
    address: dict[str, Any]
    phone: str
    email: str
    currency: str
    timezone: str
    locales: list[str]
    default_locale: str
    rounding: str
    working_days: list[int]
    holidays: list[str]
    settings: dict[str, Any]
    legal_texts: dict[str, Any]
    active: bool
    row_version: int


class BranchIn(Schema):
    code: str = Field(pattern=CODE_PATTERN)
    legal_name: str
    trade_name: str = ""
    identifiers: dict[str, Any] = {}
    address: dict[str, Any] = {}
    phone: str = ""
    email: str = ""
    currency: str = Field(min_length=3, max_length=3)
    timezone: str = "Africa/Nouakchott"
    locales: list[str] = ["fr", "en"]
    default_locale: str = "fr"
    rounding: str = "HALF_UP_2"
    working_days: list[int] = [1, 2, 3, 4, 5, 6]
    holidays: list[str] = []
    settings: dict[str, Any] = {}
    legal_texts: dict[str, Any] = {}


class BranchPatch(Schema):
    legal_name: str | None = None
    trade_name: str | None = None
    identifiers: dict[str, Any] | None = None
    address: dict[str, Any] | None = None
    phone: str | None = None
    email: str | None = None
    timezone: str | None = None
    locales: list[str] | None = None
    default_locale: str | None = None
    rounding: str | None = None
    working_days: list[int] | None = None
    holidays: list[str] | None = None
    settings: dict[str, Any] | None = None
    legal_texts: dict[str, Any] | None = None
    active: bool | None = None
    row_version: int | None = Field(
        default=None, description="Optimistic lock: the version last read"
    )


class DepartmentOut(Schema):
    id: uuid.UUID
    branch_id: uuid.UUID
    code: str
    labels: dict[str, str]
    colour: str
    ord: int
    active: bool


class DepartmentIn(Schema):
    branch_id: uuid.UUID
    code: str = Field(pattern=CODE_PATTERN)
    labels: LabelsSchema
    colour: str = ""
    ord: int = 0


class DepartmentPatch(Schema):
    labels: LabelsSchema | None = None
    colour: str | None = None
    ord: int | None = None
    active: bool | None = None


class SignatoryOut(Schema):
    id: uuid.UUID
    branch_id: uuid.UUID
    user_id: uuid.UUID | None
    display_name: str
    title: str
    document_kinds: list[str]
    mode: str
    has_signature_image: bool
    has_stamp_image: bool
    image_positions: dict[str, Any]
    image_version: int
    certificate_ref: str
    esign_provider_code: str
    requires_step_up: bool
    signing_order: int
    active: bool


class SignatoryIn(Schema):
    branch_id: uuid.UUID
    user_id: uuid.UUID | None = None
    display_name: str
    title: str = ""
    document_kinds: list[str] = []
    mode: str = "IMAGE"
    image_positions: dict[str, Any] = {}
    certificate_ref: str = ""
    esign_provider_code: str = ""
    requires_step_up: bool = True
    signing_order: int = 1


class SignatoryPatch(Schema):
    user_id: uuid.UUID | None = None
    display_name: str | None = None
    title: str | None = None
    document_kinds: list[str] | None = None
    mode: str | None = None
    image_positions: dict[str, Any] | None = None
    certificate_ref: str | None = None
    esign_provider_code: str | None = None
    requires_step_up: bool | None = None
    signing_order: int | None = None
    active: bool | None = None


class TreasuryAccountOut(Schema):
    id: uuid.UUID
    branch_id: uuid.UUID
    type: str
    label: str
    bank_name: str
    iban: str
    bic: str
    currency: str
    printed_on_invoices: bool
    active: bool


class TreasuryAccountIn(Schema):
    branch_id: uuid.UUID
    type: str
    label: str
    bank_name: str = ""
    iban: str = ""
    bic: str = ""
    currency: str = Field(min_length=3, max_length=3)
    printed_on_invoices: bool = False


class TreasuryAccountPatch(Schema):
    label: str | None = None
    bank_name: str | None = None
    iban: str | None = None
    bic: str | None = None
    printed_on_invoices: bool | None = None
    active: bool | None = None
