"""Seed document templates (SPEC Appendix D, E): loaded from ``backend/templates/documents``."""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.utils import timezone

from mizan.apps.documents.models import DocumentTemplate, PrintProfile, TemplateStatus

TEMPLATE_DIR = Path(settings.BASE_DIR) / "templates" / "documents"

# kind → (file, name)
DEFAULT_TEMPLATES: dict[str, tuple[str, str]] = {
    "QUOTE": ("quote.html", "Devis / Quote"),
    "PV_CONCRETE": ("pv_concrete.html", "PV écrasement béton / Concrete crushing report"),
    "INVOICE": ("invoice.html", "Facture / Invoice"),
    "GENERIC_REPORT": ("generic_report.html", "Rapport d'essai générique / Generic test report"),
    "LABEL": ("label.html", "Étiquettes / Labels"),
}
DEFAULT_PRINT_PROFILE = {
    "signature_image": True,
    "digital_signature": False,
    "qr": True,
    "watermark": "",
    "paper": "A4",
    "copies": 1,
}


def _read(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


def template_source(kind: str) -> str:
    """The template HTML with the shared frame inlined (Jinja include is resolved at seed time)."""
    file_name, _ = DEFAULT_TEMPLATES[kind]
    return _read(file_name).replace(
        '{% include "_frame_header.html" %}', _read("_frame_header.html")
    )


def install_default_templates(*, approved_by: object = None) -> list[DocumentTemplate]:
    created: list[DocumentTemplate] = []
    css = _read("base.css")
    for kind, (_file, name) in DEFAULT_TEMPLATES.items():
        for locale in ("fr", "en"):
            exists = DocumentTemplate.objects.filter(
                branch__isnull=True, kind=kind, locale=locale
            ).exists()
            if exists:
                continue
            template: DocumentTemplate = DocumentTemplate.objects.create(
                branch=None,
                kind=kind,
                locale=locale,
                version=1,
                status=TemplateStatus.ACTIVE,
                name=name,
                html=template_source(kind),
                css=css,
                approved_at=timezone.now(),
            )
            created.append(template)
    return created


def install_default_print_profiles(branch: object) -> int:
    count = 0
    for kind in DEFAULT_TEMPLATES:
        _, was_created = PrintProfile.objects.get_or_create(
            branch=branch, kind=kind, defaults={"defaults": dict(DEFAULT_PRINT_PROFILE)}
        )
        count += int(was_created)
    return count
