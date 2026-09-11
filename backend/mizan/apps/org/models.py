"""Tenant, branch, department, signatory, treasury account (SPEC §5, §10.9, §10.11, §15.1)."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from mizan.platform.db import BaseModel, CodeField, TenantModel
from mizan.platform.labels import LabelledModel


class TenantStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"


class Tenant(BaseModel):
    """A company or laboratory group: the isolation boundary. Not itself tenant-scoped."""

    code = CodeField(unique=True)
    name = models.CharField(max_length=200)
    theme = models.JSONField(default=dict, blank=True)  # logo, primary colour, header/footer texts
    plan = models.CharField(max_length=32, default="standard")
    status = models.CharField(
        max_length=16, choices=TenantStatus.choices, default=TenantStatus.ACTIVE
    )
    settings = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "tenant"

    def __str__(self) -> str:
        return self.name


class Branch(TenantModel):
    """A laboratory in a city or country: legal identity, currency, tax, timezone, numbering."""

    code = CodeField()
    legal_name = models.CharField(max_length=200)
    trade_name = models.CharField(max_length=200, blank=True, default="")
    identifiers = models.JSONField(default=dict, blank=True)  # registration numbers, tax id
    address = models.JSONField(default=dict, blank=True)
    phone = models.CharField(max_length=64, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    currency = models.CharField(max_length=3)
    timezone = models.CharField(max_length=64, default="Africa/Nouakchott")
    locales = models.JSONField(default=list, blank=True)  # ["fr", "en"]
    default_locale = models.CharField(max_length=8, default="fr")
    rounding = models.CharField(max_length=16, default="HALF_UP_2")
    working_days = models.JSONField(default=list, blank=True)  # ISO weekdays 1..7
    holidays = models.JSONField(default=list, blank=True)  # ISO dates
    settings = models.JSONField(default=dict, blank=True)  # typed by BranchSettings
    legal_texts = models.JSONField(default=dict, blank=True)
    logo_object_key = models.CharField(max_length=255, blank=True, default="")
    active = models.BooleanField(default=True)

    class Meta(TenantModel.Meta):
        db_table = "branch"
        constraints = [models.UniqueConstraint(fields=["tenant_id", "code"], name="uq_branch_code")]

    def __str__(self) -> str:
        return f"{self.code} — {self.legal_name}"


class Department(TenantModel, LabelledModel):
    label_entity = "department"

    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="departments")
    code = CodeField()
    colour = models.CharField(max_length=32, blank=True, default="")
    ord = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta(TenantModel.Meta):
        db_table = "department"
        ordering = ["ord", "code"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "code"], name="uq_department_code")
        ]

    def __str__(self) -> str:
        return f"{self.branch.code}/{self.code}"


class SignatureMode(models.TextChoices):
    IMAGE = "IMAGE", "Signature image"
    DRAWN = "DRAWN", "Drawn on device"
    DIGITAL_CERTIFICATE = "DIGITAL_CERTIFICATE", "Personal digital certificate"
    EXTERNAL_ESIGN = "EXTERNAL_ESIGN", "External e-signature provider"


class Signatory(TenantModel):
    """A person authorised to sign given document kinds for a branch (SPEC §10.11)."""

    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="signatories")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="signatories",
    )
    display_name = models.CharField(max_length=200)
    title = models.CharField(max_length=200, blank=True, default="")
    document_kinds = models.JSONField(default=list, blank=True)  # ["REPORT", "QUOTE", ...]
    mode = models.CharField(
        max_length=32, choices=SignatureMode.choices, default=SignatureMode.IMAGE
    )
    signature_image_key = models.CharField(max_length=255, blank=True, default="")
    stamp_image_key = models.CharField(max_length=255, blank=True, default="")
    image_positions = models.JSONField(default=dict, blank=True)  # per template kind
    image_version = models.PositiveIntegerField(default=0)
    image_approved_by = models.UUIDField(null=True, blank=True)
    image_approved_at = models.DateTimeField(null=True, blank=True)
    certificate_ref = models.CharField(max_length=255, blank=True, default="")  # KMS key / cert id
    esign_provider_code = models.CharField(max_length=64, blank=True, default="")
    requires_step_up = models.BooleanField(default=True)
    signing_order = models.PositiveIntegerField(default=1)
    active = models.BooleanField(default=True)

    class Meta(TenantModel.Meta):
        db_table = "signatory"
        ordering = ["signing_order", "display_name"]

    def __str__(self) -> str:
        return self.display_name

    def signs(self, document_kind: str) -> bool:
        return self.active and document_kind in (self.document_kinds or [])


class TreasuryAccountType(models.TextChoices):
    BANK = "BANK", "Bank"
    CASH = "CASH", "Cash"


class TreasuryAccount(TenantModel):
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="treasury_accounts")
    type = models.CharField(max_length=8, choices=TreasuryAccountType.choices)
    label = models.CharField(max_length=200)
    bank_name = models.CharField(max_length=200, blank=True, default="")
    iban = models.CharField(max_length=64, blank=True, default="")
    bic = models.CharField(max_length=16, blank=True, default="")
    currency = models.CharField(max_length=3)
    printed_on_invoices = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    class Meta(TenantModel.Meta):
        db_table = "treasury_account"
        ordering = ["type", "label"]

    def __str__(self) -> str:
        return f"{self.label} ({self.currency})"
