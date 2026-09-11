"""Documents and verification (SPEC §18): templates, issued documents, renditions, keys, transparency log."""

from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone

from mizan.platform import context
from mizan.platform.db import CodeField, TenantModel
from mizan.platform.ids import uuid7


def _default_tenant_id() -> uuid.UUID | None:
    return context.current_tenant_id.get()


class TemplateStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    RETIRED = "RETIRED", "Retired"


class DocumentTemplate(TenantModel):
    """HTML/CSS per kind and locale, versioned, approved before use (SPEC §10.7)."""

    branch = models.ForeignKey(
        "org.Branch", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    kind = CodeField()  # QUOTE, PV_CONCRETE, INVOICE, LABEL, ...
    locale = models.CharField(max_length=8, default="fr")
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=16, choices=TemplateStatus.choices, default=TemplateStatus.DRAFT
    )
    name = models.CharField(max_length=200, blank=True, default="")
    html = models.TextField()
    css = models.TextField(blank=True, default="")
    variables = models.JSONField(default=dict, blank=True)  # documented variables for the editor
    sample_data = models.JSONField(default=dict, blank=True)
    approved_by = models.UUIDField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta(TenantModel.Meta):
        db_table = "document_template"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "branch", "kind", "locale", "version"],
                name="uq_document_template_version",
                nulls_distinct=False,
            )
        ]

    def __str__(self) -> str:
        return f"{self.kind}/{self.locale} v{self.version}"


class PrintProfile(TenantModel):
    branch = models.ForeignKey(
        "org.Branch", on_delete=models.PROTECT, related_name="print_profiles"
    )
    kind = CodeField()
    defaults = models.JSONField(
        default=dict
    )  # signature_image, digital_signature, qr, watermark, paper, copies

    class Meta(TenantModel.Meta):
        db_table = "print_profile"
        constraints = [models.UniqueConstraint(fields=["branch", "kind"], name="uq_print_profile")]

    def __str__(self) -> str:
        return f"{self.kind} @ {self.branch_id}"


class KeyPurpose(models.TextChoices):
    QR = "QR", "QR payload signing (Ed25519)"
    PDF = "PDF", "PDF sealing (RSA-3072 / X.509)"


class KeyStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    RETIRED = "RETIRED", "Retired (still valid for verification)"


class SigningKey(TenantModel):
    """Public half and handle of a branch key; private material stays in the KMS (or local files in dev)."""

    branch = models.ForeignKey("org.Branch", on_delete=models.PROTECT, related_name="signing_keys")
    purpose = models.CharField(max_length=8, choices=KeyPurpose.choices)
    kid = models.CharField(max_length=64, unique=True)
    algorithm = models.CharField(max_length=32)  # EdDSA | RS256
    backend = models.CharField(max_length=16, default="local")  # local | kms
    key_ref = models.CharField(max_length=255)  # file path (dev) or KMS resource name
    public_jwk = models.JSONField(default=dict, blank=True)
    certificate_pem = models.TextField(blank=True, default="")
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=KeyStatus.choices, default=KeyStatus.ACTIVE)

    class Meta(TenantModel.Meta):
        db_table = "signing_key"

    def __str__(self) -> str:
        return f"{self.kid} ({self.purpose})"


class DocumentStatus(models.TextChoices):
    CURRENT = "CURRENT", "Current"
    SUPERSEDED = "SUPERSEDED", "Superseded"
    REVOKED = "REVOKED", "Revoked"


class IssuedDocument(TenantModel):
    """The registry of every issued PDF (SPEC §18.2)."""

    branch = models.ForeignKey(
        "org.Branch", on_delete=models.PROTECT, related_name="issued_documents"
    )
    kind = CodeField()
    number = models.CharField(max_length=64)
    subject_type = models.CharField(
        max_length=64, blank=True, default=""
    )  # report, invoice, quote ...
    subject_id = models.UUIDField(null=True, blank=True)
    subject = models.JSONField(default=dict, blank=True)  # {account, project, refs}
    digest = models.JSONField(
        default=dict, blank=True
    )  # kind-specific, shown behind the short code
    render_data = models.JSONField(default=dict, blank=True)  # template context, for renditions
    issued_at = models.DateTimeField(default=timezone.now)
    issued_by = models.UUIDField(null=True, blank=True)
    signatory = models.ForeignKey(
        "org.Signatory", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    template = models.ForeignKey(
        DocumentTemplate, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    template_version = models.PositiveIntegerField(default=0)
    locale = models.CharField(max_length=8, default="fr")
    content_hash = models.CharField(max_length=64)  # sha256 hex of the canonical content (ADR 0004)
    pdf_object_key = models.CharField(max_length=255)
    pdf_sha256 = models.CharField(max_length=64)
    pdf_size = models.PositiveIntegerField(default=0)
    seal_level = models.CharField(max_length=16, default="B-B")
    status = models.CharField(
        max_length=16, choices=DocumentStatus.choices, default=DocumentStatus.CURRENT
    )
    superseded_by = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    revoked_reason = models.TextField(blank=True, default="")
    revoked_at = models.DateTimeField(null=True, blank=True)
    verify_token = models.CharField(max_length=32, unique=True)
    short_code = models.CharField(max_length=8)
    qr_jws = models.TextField(blank=True, default="")
    qr_key = models.ForeignKey(
        SigningKey, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    seal_key = models.ForeignKey(
        SigningKey, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    transparency_leaf_index = models.BigIntegerField(null=True, blank=True)

    class Meta(TenantModel.Meta):
        db_table = "issued_document"
        indexes = [
            models.Index(fields=["tenant_id", "kind", "number"], name="idx_issued_document_number"),
            models.Index(fields=["subject_type", "subject_id"], name="idx_issued_document_subject"),
        ]

    def __str__(self) -> str:
        return f"{self.kind} {self.number}"


class Rendition(TenantModel):
    document = models.ForeignKey(
        IssuedDocument, on_delete=models.CASCADE, related_name="renditions"
    )
    options = models.JSONField(default=dict)
    produced_by = models.UUIDField(null=True, blank=True)
    produced_at = models.DateTimeField(default=timezone.now)
    object_key = models.CharField(max_length=255)
    sha256 = models.CharField(max_length=64)
    size = models.PositiveIntegerField(default=0)

    class Meta(TenantModel.Meta):
        db_table = "rendition"

    def __str__(self) -> str:
        return f"rendition of {self.document_id}"


class VerificationOutcome(models.TextChoices):
    FOUND = "FOUND", "Found"
    NOT_FOUND = "NOT_FOUND", "Not found"
    DIGEST_OK = "DIGEST_OK", "Digest returned"
    DIGEST_BAD = "DIGEST_BAD", "Wrong short code"
    REVOKED_LOOKUP = "REVOKED_LOOKUP", "Lookup of a revoked document"
    RATE_LIMITED = "RATE_LIMITED", "Rate limited"


class VerificationAttempt(models.Model):
    """Every public lookup; unknown tokens have no tenant (global rows)."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant_id = models.UUIDField(null=True, blank=True, db_index=True)
    token = models.CharField(max_length=32, db_index=True)
    short_code_given = models.CharField(max_length=8, blank=True, default="")
    ip_hash = models.CharField(max_length=64, db_index=True)
    user_agent = models.CharField(max_length=256, blank=True, default="")
    at = models.DateTimeField(default=timezone.now, db_index=True)
    outcome = models.CharField(max_length=16, choices=VerificationOutcome.choices)

    class Meta:
        db_table = "verification_attempt"

    def __str__(self) -> str:
        return f"{self.token} {self.outcome}"


class TransparencyLeaf(TenantModel):
    """Append-only Merkle log of issued documents (SPEC §18.8), one log per tenant."""

    index = models.BigIntegerField()
    document = models.OneToOneField(
        IssuedDocument, on_delete=models.PROTECT, related_name="transparency_leaf"
    )
    leaf_hash = models.CharField(max_length=64)
    tree_head_hash = models.CharField(max_length=64)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta(TenantModel.Meta):
        db_table = "transparency_leaf"
        ordering = ["index"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "index"], name="uq_transparency_leaf_index"
            )
        ]

    def __str__(self) -> str:
        return f"leaf {self.index}"


class TransparencyHead(TenantModel):
    tree_size = models.BigIntegerField()
    root_hash = models.CharField(max_length=64)
    signature = models.TextField()  # JWS over {size, root, published_at}
    key = models.ForeignKey(SigningKey, on_delete=models.PROTECT, related_name="+")
    published_at = models.DateTimeField(default=timezone.now)

    class Meta(TenantModel.Meta):
        db_table = "transparency_head"

    def __str__(self) -> str:
        return f"head size={self.tree_size}"


class FraudCase(models.Model):
    """Suspicious-document reports (SPEC §18.6); anonymous reports of unknown tokens have no tenant."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant_id = models.UUIDField(null=True, blank=True, db_index=True)
    document = models.ForeignKey(
        IssuedDocument, on_delete=models.PROTECT, null=True, blank=True, related_name="fraud_cases"
    )
    token = models.CharField(max_length=32, blank=True, default="")
    reporter_name = models.CharField(max_length=200, blank=True, default="")
    reporter_contact = models.CharField(max_length=200, blank=True, default="")
    message = models.TextField(blank=True, default="")
    attachment_key = models.CharField(max_length=255, blank=True, default="")
    state = models.CharField(max_length=16, default="OPEN")  # OPEN | CLOSED
    created_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "fraud_case"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"fraud case {self.id}"
