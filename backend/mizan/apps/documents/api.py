"""Documents API (SPEC A.2, A.10): templates, print profiles, originals, renditions, public verification."""

import uuid
from typing import Any

from django.http import HttpRequest, HttpResponse
from jinja2 import TemplateError
from ninja import Router, Status
from ninja.throttling import AnonRateThrottle

from mizan.apps.audit import services as audit
from mizan.apps.documents import issuance, keys, transparency, verification
from mizan.apps.documents.models import (
    DocumentTemplate,
    IssuedDocument,
    PrintProfile,
    Rendition,
    TemplateStatus,
)
from mizan.apps.documents.rendering import render_html, render_pdf
from mizan.apps.documents.schemas import (
    DigestIn,
    DocumentOut,
    PreviewIn,
    PrintProfileIn,
    PrintProfileOut,
    RenditionIn,
    RenditionOut,
    SuspiciousIn,
    TemplateIn,
    TemplateOut,
    TemplateSummaryOut,
    TemplateVersionIn,
)
from mizan.apps.identity.authz import authorize, requires
from mizan.platform import context
from mizan.platform.api.errors import Conflict, NotFound, UnprocessableEntity
from mizan.platform.authz.catalog import RESOURCES
from mizan.platform.db.tenancy import platform_scope
from mizan.platform.events import emit
from mizan.platform.middleware import client_ip
from mizan.platform.storage import documents_storage

router = Router(tags=["documents"])
verify_router = Router(tags=["verification"])


def _get[M](model: type[M], pk: uuid.UUID) -> M:
    try:
        row: M = model._default_manager.get(pk=pk)  # type: ignore[attr-defined]
    except model.DoesNotExist as exc:  # type: ignore[attr-defined]
        raise NotFound() from exc
    return row


# --- templates ------------------------------------------------------------------------------------


@router.get("/document-templates", response=list[TemplateSummaryOut])
@requires("document_template", "view")
def list_templates(request: HttpRequest, kind: str | None = None) -> list[DocumentTemplate]:
    qs = DocumentTemplate.objects.all().order_by("kind", "locale", "-version")
    if kind:
        qs = qs.filter(kind=kind)
    return list(qs)


@router.get("/document-templates/{uuid:template_id}", response=TemplateOut)
@requires("document_template", "view")
def get_template(request: HttpRequest, template_id: uuid.UUID) -> DocumentTemplate:
    return _get(DocumentTemplate, template_id)


@router.post(
    "/document-templates",
    response={201: TemplateOut},
    summary="Create a draft template (version 1)",
)
@requires("document_template", "configure")
def create_template(request: HttpRequest, payload: TemplateIn) -> Status[DocumentTemplate]:
    if DocumentTemplate.objects.filter(
        kind=payload.kind, locale=payload.locale, branch_id=payload.branch_id
    ).exists():
        raise Conflict("documents.template.exists", code="template_exists")
    _check_template(payload.html, payload.sample_data)
    template = DocumentTemplate.objects.create(**payload.model_dump(), version=1)
    audit.record(
        "document_template",
        template.id,
        "created",
        after={"kind": template.kind, "locale": template.locale},
    )
    return Status(201, template)


@router.post(
    "/document-templates/{uuid:template_id}/versions",
    response={201: TemplateOut},
    summary="New draft version",
)
@requires("document_template", "configure")
def new_template_version(
    request: HttpRequest, template_id: uuid.UUID, payload: TemplateVersionIn
) -> Status[DocumentTemplate]:
    source = _get(DocumentTemplate, template_id)
    latest = (
        DocumentTemplate.objects.filter(
            kind=source.kind, locale=source.locale, branch_id=source.branch_id
        )
        .order_by("-version")
        .first()
    )
    changes = payload.model_dump(exclude_unset=True)
    template = DocumentTemplate.objects.create(
        branch_id=source.branch_id,
        kind=source.kind,
        locale=source.locale,
        version=(latest.version if latest else source.version) + 1,
        name=changes.get("name", source.name),
        html=changes.get("html", source.html),
        css=changes.get("css", source.css),
        variables=changes.get("variables", source.variables),
        sample_data=changes.get("sample_data", source.sample_data),
    )
    _check_template(template.html, template.sample_data)
    audit.record(
        "document_template",
        template.id,
        "version_created",
        after={"kind": template.kind, "version": template.version},
    )
    return Status(201, template)


@router.post(
    "/document-templates/{uuid:template_id}:approve",
    response=TemplateOut,
    summary="Approve: becomes the active version",
)
@requires("document_template", "configure")
def approve_template(request: HttpRequest, template_id: uuid.UUID) -> DocumentTemplate:
    template = _get(DocumentTemplate, template_id)
    DocumentTemplate.objects.filter(
        kind=template.kind,
        locale=template.locale,
        branch_id=template.branch_id,
        status=TemplateStatus.ACTIVE,
    ).exclude(pk=template.pk).update(status=TemplateStatus.RETIRED)
    template.status = TemplateStatus.ACTIVE
    template.approved_by = context.actor().id
    from django.utils import timezone

    template.approved_at = timezone.now()
    template.save(update_fields=["status", "approved_by", "approved_at"])
    audit.record(
        "document_template",
        template.id,
        "approved",
        after={"kind": template.kind, "version": template.version},
    )
    emit(
        "config.changed",
        aggregate_type="document_template",
        aggregate_id=template.id,
        payload={"section": "document_template", "action": "approved"},
    )
    return template


def _check_template(html: str, sample_data: dict[str, Any]) -> None:
    """Compile and render with sample data so that a broken template never reaches approval."""
    try:
        render_html(html, _sample_context(sample_data))
    except TemplateError as exc:
        raise UnprocessableEntity(
            "documents.template.invalid", details=[{"loc": ["html"], "msg": str(exc)}]
        ) from exc
    except Exception as exc:
        raise UnprocessableEntity(
            "documents.template.render_failed", details=[{"loc": ["html"], "msg": str(exc)[:300]}]
        ) from exc


def _sample_context(sample: dict[str, Any]) -> dict[str, Any]:
    from django.conf import settings
    from django.utils import timezone

    return {
        "document": {
            "kind": "PREVIEW", "number": "PREVIEW-0001", "issued_at": timezone.now(), "locale": sample.get("locale", "fr"),
            "short_code": "PRVW-00", "verify_url": settings.MIZAN_VERIFY_BASE_URL, "verify_site": settings.MIZAN_VERIFY_BASE_URL,
            "qr_svg": "", "watermark": "PREVIEW", "signature_image": "", "signatory": None, "template_version": 0,
        },
        "branch": {"code": "NKC", "legal_name": "Sample branch", "trade_name": "", "address": {}, "phone": "", "email": "", "identifiers": {}, "currency": "MRU", "legal_texts": {}},
        "tenant_code": "sample",
        **sample,
    }  # fmt: skip


@router.post(
    "/document-templates/{uuid:template_id}:preview",
    summary="Render the template with sample data (PDF)",
)
@requires("document_template", "view")
def preview_template(
    request: HttpRequest, template_id: uuid.UUID, payload: PreviewIn
) -> HttpResponse:
    template = _get(DocumentTemplate, template_id)
    data = payload.data if payload.data is not None else template.sample_data
    html = render_html(template.html, _sample_context(data))
    pdf = render_pdf(html, template.css, pdf_a=False)
    return HttpResponse(
        pdf,
        content_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=preview.pdf"},
    )


@router.get("/print-profiles", response=list[PrintProfileOut])
@requires("document_template", "view")
def list_print_profiles(
    request: HttpRequest, branch_id: uuid.UUID | None = None
) -> list[PrintProfile]:
    qs = PrintProfile.objects.all()
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    return list(qs.order_by("kind"))


@router.post(
    "/print-profiles",
    response={201: PrintProfileOut},
    summary="Create or replace the print defaults of a kind",
)
@requires("document_template", "configure")
def upsert_print_profile(request: HttpRequest, payload: PrintProfileIn) -> Status[PrintProfile]:
    profile, _ = PrintProfile.objects.update_or_create(
        branch_id=payload.branch_id, kind=payload.kind, defaults={"defaults": payload.defaults}
    )
    audit.record(
        "print_profile", profile.id, "upserted", after=payload.defaults, branch_id=payload.branch_id
    )
    return Status(201, profile)


# --- issued documents -----------------------------------------------------------------------------


def _authorize_document(request: HttpRequest, document: IssuedDocument, action: str) -> None:
    resource = document.subject_type if document.subject_type in RESOURCES else "report"
    authorize(request, resource, action)


@router.get(
    "/documents/{uuid:document_id}",
    response=DocumentOut,
    summary="Registry entry of an issued document",
)
def get_document(request: HttpRequest, document_id: uuid.UUID) -> IssuedDocument:
    document = _get(IssuedDocument, document_id)
    _authorize_document(request, document, "view")
    return document


@router.get("/documents/{uuid:document_id}/download", summary="The sealed canonical original")
def download_document(request: HttpRequest, document_id: uuid.UUID) -> HttpResponse:
    document = _get(IssuedDocument, document_id)
    _authorize_document(request, document, "view")
    pdf = issuance.original_pdf(document)
    return HttpResponse(
        pdf,
        content_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{document.number}.pdf"'},
    )


@router.post(
    "/documents/{uuid:document_id}/renditions",
    response={201: RenditionOut},
    summary="Produce a printed variant with options",
)
def create_rendition(
    request: HttpRequest, document_id: uuid.UUID, payload: RenditionIn
) -> Status[Rendition]:
    document = _get(IssuedDocument, document_id)
    _authorize_document(request, document, "print")
    return Status(201, issuance.produce_rendition(document, payload.model_dump(exclude_none=True)))


@router.get(
    "/documents/{uuid:document_id}/renditions/{uuid:rendition_id}", summary="Download a rendition"
)
def download_rendition(
    request: HttpRequest, document_id: uuid.UUID, rendition_id: uuid.UUID
) -> HttpResponse:
    document = _get(IssuedDocument, document_id)
    _authorize_document(request, document, "print")
    rendition = Rendition.objects.filter(pk=rendition_id, document=document).first()
    if rendition is None:
        raise NotFound()
    pdf = documents_storage().get(rendition.object_key)
    return HttpResponse(
        pdf,
        content_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{document.number}.pdf"'},
    )


# --- public verification (no tenant scope: documents are looked up by token) ----------------------


@verify_router.get(
    "/verify/keys", auth=None, response=dict[str, Any], summary="JWKS of QR signing keys"
)
def verify_keys(request: HttpRequest) -> dict[str, Any]:
    with platform_scope():
        return keys.public_jwks()


@verify_router.get(
    "/verify/transparency/head",
    auth=None,
    response=dict[str, Any] | None,
    summary="Latest signed tree head",
)
def transparency_head(
    request: HttpRequest, tenant_code: str | None = None
) -> dict[str, Any] | None:
    from mizan.apps.documents.models import TransparencyHead

    with platform_scope():
        qs = TransparencyHead.objects.select_related("key").order_by("-published_at")
        if tenant_code:
            from mizan.apps.org.models import Tenant

            tenant = Tenant.objects.filter(code=tenant_code).first()
            qs = qs.filter(tenant_id=tenant.id) if tenant else qs.none()
        head = qs.first()
        return transparency.head_payload(head) if head else None


@verify_router.get(
    "/verify/transparency/proof/{token}",
    auth=None,
    response=dict[str, Any],
    summary="Inclusion proof of a document",
)
def transparency_proof(request: HttpRequest, token: str) -> dict[str, Any]:
    with platform_scope():
        document = IssuedDocument.objects.filter(verify_token=token).first()
        if document is None or document.transparency_leaf_index is None:
            raise NotFound("verify.not_found", code="verify_not_found")
    from mizan.platform.db.tenancy import tenant_scope

    with tenant_scope(document.tenant_id):
        return transparency.proof_for(document.transparency_leaf_index)


@verify_router.get(
    "/verify/{token}",
    auth=None,
    response=dict[str, Any],
    throttle=[AnonRateThrottle("60/m")],
    summary="Step 1: registry status of a document",
)
def verify_lookup(request: HttpRequest, token: str) -> dict[str, Any]:
    return verification.lookup(
        token, ip=client_ip(request), user_agent=request.headers.get("User-Agent", "")
    )


@verify_router.post(
    "/verify/{token}/digest",
    auth=None,
    response=dict[str, Any],
    summary="Step 2: digest behind the short code (5/min/IP)",
)
def verify_digest(request: HttpRequest, token: str, payload: DigestIn) -> dict[str, Any]:
    return verification.digest(
        token,
        payload.short_code,
        ip=client_ip(request),
        user_agent=request.headers.get("User-Agent", ""),
    )


@verify_router.post(
    "/verify/{token}/report-suspicious",
    auth=None,
    response={201: dict[str, Any]},
    throttle=[AnonRateThrottle("10/m")],
    summary="Open a fraud case",
)
def verify_report_suspicious(
    request: HttpRequest, token: str, payload: SuspiciousIn
) -> Status[dict[str, Any]]:
    case = verification.report_suspicious(
        token,
        reporter_name=payload.reporter_name,
        reporter_contact=payload.reporter_contact,
        message=payload.message,
        ip=client_ip(request),
    )
    return Status(201, {"case_id": case.id, "state": case.state})


@verify_router.get("/verify/{token}/original", summary="Authenticated: download the canonical PDF")
def verify_original(request: HttpRequest, token: str) -> HttpResponse:
    with platform_scope():
        document = IssuedDocument.objects.filter(verify_token=token).first()
    if document is None:
        raise NotFound("verify.not_found", code="verify_not_found")
    principal = getattr(request, "principal", None)
    if principal is None or principal.tenant_id != document.tenant_id:
        raise NotFound("verify.not_found", code="verify_not_found")
    _authorize_document(request, document, "view")
    return HttpResponse(issuance.original_pdf(document), content_type="application/pdf")
