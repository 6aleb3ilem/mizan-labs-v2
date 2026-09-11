"""Issuing a document: render → PDF/A-3b → seal → store → registry → QR → transparency (SPEC §18.1)."""

from __future__ import annotations

import base64
import hashlib
import uuid
from dataclasses import dataclass, field
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from mizan.apps.audit import services as audit
from mizan.apps.documents import qr as qr_module
from mizan.apps.documents.keys import ensure_branch_keys, load_qr_private_key, pdf_signer_for
from mizan.apps.documents.models import (
    DocumentStatus,
    DocumentTemplate,
    IssuedDocument,
    Rendition,
    TemplateStatus,
)
from mizan.apps.documents.rendering import render_html, render_pdf
from mizan.apps.documents.signing import seal_pdf
from mizan.apps.documents.tokens import new_short_code, new_verify_token
from mizan.apps.documents.transparency import append_leaf
from mizan.platform import context
from mizan.platform.api.errors import Conflict, NotFound
from mizan.platform.events import emit
from mizan.platform.storage import documents_storage


@dataclass(slots=True)
class IssueRequest:
    kind: str
    number: str
    branch: Any
    data: dict[str, Any]
    subject: dict[str, Any] = field(
        default_factory=dict
    )  # {"acc": "SOGECO", "prj": "AF-2026-0031"}
    digest: dict[str, Any] = field(default_factory=dict)
    subject_type: str = ""
    subject_id: uuid.UUID | None = None
    template: DocumentTemplate | None = None
    template_kind: str = ""
    locale: str = "fr"
    signatory: Any = None
    issued_by: uuid.UUID | None = None
    options: dict[str, Any] = field(default_factory=dict)


def active_template(kind: str, locale: str, branch_id: Any = None) -> DocumentTemplate:
    qs = DocumentTemplate.objects.filter(kind=kind, status=TemplateStatus.ACTIVE)
    for candidate in (
        qs.filter(branch_id=branch_id, locale=locale),
        qs.filter(branch__isnull=True, locale=locale),
        qs.filter(branch__isnull=True),
    ):
        template: DocumentTemplate | None = candidate.order_by("-version").first()
        if template is not None:
            return template
    raise NotFound("documents.template.none_active", params={"kind": kind, "locale": locale})


def content_hash_for(template: DocumentTemplate, locale: str, data: dict[str, Any]) -> str:
    canonical = qr_module.canonical_json(
        {"template": str(template.id), "version": template.version, "locale": locale, "data": data}
    )
    return hashlib.sha256(canonical).hexdigest()


def _signature_image_data_uri(signatory: Any) -> str:
    key = getattr(signatory, "signature_image_key", "") if signatory else ""
    if not key:
        return ""
    try:
        blob = documents_storage().get(key)
    except Exception:
        return ""
    mime = "image/svg+xml" if key.endswith(".svg") else "image/png"
    return f"data:{mime};base64,{base64.b64encode(blob).decode()}"


def build_context(
    document: IssuedDocument, data: dict[str, Any], options: dict[str, Any]
) -> dict[str, Any]:
    branch = document.branch
    tenant_code = getattr(context, "current_tenant_code", None)
    verify_url = qr_module.qr_url(settings.MIZAN_VERIFY_BASE_URL, document.qr_jws)
    signatory = document.signatory
    return {
        **data,
        "document": {
            "kind": document.kind,
            "number": document.number,
            "issued_at": document.issued_at,
            "locale": document.locale,
            "short_code": document.short_code,
            "verify_url": verify_url,
            "verify_site": settings.MIZAN_VERIFY_BASE_URL,
            "qr_svg": qr_module.qr_svg_data_uri(verify_url) if options.get("qr", True) else "",
            "watermark": options.get("watermark", ""),
            "signature_image": _signature_image_data_uri(signatory)
            if options.get("signature_image", False)
            else "",
            "signatory": {"name": signatory.display_name, "title": signatory.title}
            if signatory
            else None,
            "template_version": document.template_version,
        },
        "branch": {
            "code": branch.code,
            "legal_name": branch.legal_name,
            "trade_name": branch.trade_name,
            "address": branch.address,
            "phone": branch.phone,
            "email": branch.email,
            "identifiers": branch.identifiers,
            "currency": branch.currency,
            "legal_texts": branch.legal_texts,
        },
        "tenant_code": tenant_code,
    }


def _render_sealed_pdf(
    document: IssuedDocument,
    template: DocumentTemplate,
    data: dict[str, Any],
    options: dict[str, Any],
) -> tuple[bytes, str]:
    html = render_html(template.html, build_context(document, data, options))
    pdf = render_pdf(html, template.css, pdf_a=True)
    signer = pdf_signer_for(document.seal_key)  # type: ignore[arg-type]
    branch = document.branch
    return seal_pdf(
        pdf,
        signer,
        reason=f"Sealed by {branch.legal_name}",
        location=str((branch.address or {}).get("city", "")),
        tsa_url=settings.MIZAN_TSA_URL,
    )


def issue_document(req: IssueRequest) -> IssuedDocument:
    """Create the sealed canonical original and its registry entry, in the caller's transaction."""
    template = req.template or active_template(
        req.template_kind or req.kind, req.locale, req.branch.id
    )
    qr_key, seal_key = ensure_branch_keys(req.branch)
    issued_at = timezone.now()
    token = new_verify_token()
    content_hash = content_hash_for(template, req.locale, req.data)
    tenant_code = _tenant_code()
    payload = qr_module.build_payload(
        issuer=f"{tenant_code}/{req.branch.code}",
        kind=req.kind,
        number=req.number,
        issued_at_epoch=int(issued_at.timestamp()),
        subject=req.subject,
        digest=req.digest,
        content_hash_hex=content_hash,
        verify_token=token,
    )
    jws = qr_module.sign_payload(payload, load_qr_private_key(qr_key), qr_key.kid)
    with transaction.atomic():
        document: IssuedDocument = IssuedDocument.objects.create(
            branch=req.branch,
            kind=req.kind,
            number=req.number,
            subject_type=req.subject_type,
            subject_id=req.subject_id,
            subject=req.subject,
            digest=req.digest,
            render_data=req.data,
            issued_at=issued_at,
            issued_by=req.issued_by or context.actor().id,
            signatory=req.signatory,
            template=template,
            template_version=template.version,
            locale=req.locale,
            content_hash=content_hash,
            pdf_object_key="",
            pdf_sha256="",
            verify_token=token,
            short_code=new_short_code(),
            qr_jws=jws,
            qr_key=qr_key,
            seal_key=seal_key,
        )
        options = {"qr": True, "signature_image": False, "watermark": "", **req.options}
        sealed, level = _render_sealed_pdf(document, template, req.data, options)
        sha = hashlib.sha256(sealed).hexdigest()
        key = f"documents/{document.tenant_id}/{issued_at:%Y}/{sha}.pdf"
        documents_storage().put(key, sealed, "application/pdf")
        IssuedDocument.all_objects.filter(pk=document.pk).update(
            pdf_object_key=key, pdf_sha256=sha, pdf_size=len(sealed), seal_level=level
        )
        document.pdf_object_key, document.pdf_sha256, document.pdf_size, document.seal_level = (
            key,
            sha,
            len(sealed),
            level,
        )
        append_leaf(document)
        audit.record(
            "issued_document",
            document.id,
            "issued",
            after={
                "kind": req.kind,
                "number": req.number,
                "content_hash": content_hash,
                "pdf_sha256": sha,
            },
            branch_id=req.branch.id,
        )
        emit(
            "document.rendered",
            aggregate_type="issued_document",
            aggregate_id=document.id,
            branch_id=req.branch.id,
            payload={
                "kind": req.kind,
                "number": req.number,
                "subject_type": req.subject_type,
                "subject_id": str(req.subject_id) if req.subject_id else None,
            },
        )
    return document


def _tenant_code() -> str:
    from mizan.apps.org.models import Tenant

    tenant_id = context.current_tenant_id.get()
    tenant = Tenant.objects.filter(pk=tenant_id).first() if tenant_id else None
    return str(tenant.code) if tenant else "tenant"


def original_pdf(document: IssuedDocument) -> bytes:
    return documents_storage().get(document.pdf_object_key)


def produce_rendition(
    document: IssuedDocument, options: dict[str, Any], produced_by: uuid.UUID | None = None
) -> Rendition:
    """A printed variant with print options; same number, hash and QR as the original (SPEC §18.3)."""
    if document.template is None:
        raise Conflict("documents.rendition.no_template", code="rendition_no_template")
    merged = {"qr": True, "signature_image": True, "watermark": "", **options}
    sealed, _level = _render_sealed_pdf(document, document.template, document.render_data, merged)
    sha = hashlib.sha256(sealed).hexdigest()
    key = f"renditions/{document.tenant_id}/{document.id}/{sha}.pdf"
    documents_storage().put(key, sealed, "application/pdf")
    rendition: Rendition = Rendition.objects.create(
        document=document,
        options=merged,
        produced_by=produced_by or context.actor().id,
        object_key=key,
        sha256=sha,
        size=len(sealed),
    )
    emit(
        "document.printed",
        aggregate_type="issued_document",
        aggregate_id=document.id,
        branch_id=document.branch_id,
        payload={"rendition_id": str(rendition.id), "options": merged},
    )
    return rendition


def supersede(old: IssuedDocument, new: IssuedDocument, reason: str) -> IssuedDocument:
    if old.status != DocumentStatus.CURRENT:
        raise Conflict("documents.not_current", code="document_not_current")
    old.status = DocumentStatus.SUPERSEDED
    old.superseded_by = new
    old.save(update_fields=["status", "superseded_by"])
    audit.record(
        "issued_document",
        old.id,
        "superseded",
        after={"by": new.number, "reason": reason},
        branch_id=old.branch_id,
    )
    return old


def revoke(document: IssuedDocument, reason: str) -> IssuedDocument:
    if document.status == DocumentStatus.REVOKED:
        return document
    document.status = DocumentStatus.REVOKED
    document.revoked_reason = reason
    document.revoked_at = timezone.now()
    document.save(update_fields=["status", "revoked_reason", "revoked_at"])
    audit.record(
        "issued_document",
        document.id,
        "revoked",
        after={"reason": reason},
        branch_id=document.branch_id,
    )
    return document
