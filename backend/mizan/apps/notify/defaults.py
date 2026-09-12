"""Default message templates (SPEC Appendix P) and rules (SPEC §19.3). Data, editable."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mizan.apps.notify.models import MessageTemplate, NotificationRule


@dataclass(frozen=True)
class TemplateSpec:
    code: str
    channel: str
    fr: str
    en: str
    subject_fr: str = ""
    subject_en: str = ""
    variables: dict[str, str] = field(default_factory=dict)


V_QUOTE = {"quote.number": "quote number", "rev": "revision", "project.title": "project title", "total": "total amount", "currency": "currency", "portal_link": "portal link", "contact.first_name": "contact first name"}  # fmt: skip
V_INTAKE = {"qty": "specimens received", "project.title": "project title", "date": "reception date", "dates": "planned test dates"}  # fmt: skip
V_REPORT = {"report.number": "report number", "test.label": "test label", "age": "age in days", "portal_link": "portal link", "verify_link": "verification link"}  # fmt: skip
V_INVOICE = {"invoice.number": "invoice number", "total": "total", "currency": "currency", "due_date": "due date", "balance": "balance due", "days": "days overdue"}  # fmt: skip
V_DIGEST = {"date": "day", "department": "department", "intakes": "intakes", "done": "runs done", "todo": "runs to do", "overdue": "overdue runs", "tomorrow": "runs tomorrow", "departments": "per-department sections"}  # fmt: skip

DEFAULT_TEMPLATES: tuple[TemplateSpec, ...] = (
    # quote.sent
    TemplateSpec(
        "QUOTE_SENT", "email",
        "Bonjour {{ contact.first_name }},\n\nVotre devis {{ quote.number }} rév. {{ rev }} ({{ total }} {{ currency }}) pour le projet {{ project.title }} est disponible : {{ portal_link }}\n\nCordialement,\n{{ branch.legal_name }}",
        "Hello {{ contact.first_name }},\n\nYour quote {{ quote.number }} rev. {{ rev }} ({{ total }} {{ currency }}) for project {{ project.title }} is available: {{ portal_link }}\n\nKind regards,\n{{ branch.legal_name }}",
        "Devis {{ quote.number }} rév. {{ rev }} — {{ project.title }}",
        "Quote {{ quote.number }} rev. {{ rev }} — {{ project.title }}",
        V_QUOTE,
    ),
    TemplateSpec(
        "QUOTE_SENT", "whatsapp",
        "Bonjour {{ contact.first_name }}, votre devis {{ quote.number }} ({{ total }} {{ currency }}) est disponible : {{ portal_link }}",
        "Hello {{ contact.first_name }}, your quote {{ quote.number }} ({{ total }} {{ currency }}) is available: {{ portal_link }}",
        variables=V_QUOTE,
    ),
    # quote.accepted (staff)
    TemplateSpec(
        "QUOTE_ACCEPTED", "in_app",
        "Devis {{ quote.number }} accepté par {{ account.name }} — {{ project.title }}",
        "Quote {{ quote.number }} accepted by {{ account.name }} — {{ project.title }}",
        "Devis {{ quote.number }} accepté",
        "Quote {{ quote.number }} accepted",
        {**V_QUOTE, "account.name": "client account"},
    ),
    TemplateSpec(
        "QUOTE_ACCEPTED", "email",
        "Le devis {{ quote.number }} ({{ total }} {{ currency }}) de {{ account.name }} pour {{ project.title }} a été accepté. Une commande est créée : {{ app_link }}",
        "Quote {{ quote.number }} ({{ total }} {{ currency }}) from {{ account.name }} for {{ project.title }} has been accepted. An order is created: {{ app_link }}",
        "Devis {{ quote.number }} accepté — {{ project.title }}",
        "Quote {{ quote.number }} accepted — {{ project.title }}",
        {**V_QUOTE, "account.name": "client account", "app_link": "back-office link"},
    ),
    # intake.registered
    TemplateSpec(
        "INTAKE_REGISTERED", "sms",
        "Mizan Labs : {{ qty }} éprouvettes reçues pour {{ project.title }} le {{ date }}. Essais prévus : {{ dates }}.",
        "Mizan Labs: {{ qty }} specimens received for {{ project.title }} on {{ date }}. Tests planned: {{ dates }}.",
        variables=V_INTAKE,
    ),
    TemplateSpec(
        "INTAKE_REGISTERED", "in_app",
        "{{ qty }} éprouvettes reçues pour {{ project.title }} le {{ date }}. Essais prévus : {{ dates }}.",
        "{{ qty }} specimens received for {{ project.title }} on {{ date }}. Tests planned: {{ dates }}.",
        "Réception enregistrée — {{ project.title }}",
        "Intake registered — {{ project.title }}",
        V_INTAKE,
    ),
    # test_run.due_tomorrow
    TemplateSpec(
        "TEST_RUN_DUE_TOMORROW", "in_app",
        "Essai {{ test.label }} prévu demain ({{ due_date }}) — {{ project.title }}, {{ specimens }} éprouvettes.",
        "Test {{ test.label }} due tomorrow ({{ due_date }}) — {{ project.title }}, {{ specimens }} specimens.",
        "Essai prévu demain : {{ test.label }}",
        "Test due tomorrow: {{ test.label }}",
        {"test.label": "test label", "due_date": "due date", "project.title": "project title", "specimens": "specimen count"},
    ),
    # report.issued
    TemplateSpec(
        "REPORT_ISSUED", "email",
        "Votre rapport {{ report.number }} ({{ test.label }}, {{ age }} j) est émis. Télécharger : {{ portal_link }}. Vérifier : {{ verify_link }}",
        "Your report {{ report.number }} ({{ test.label }}, {{ age }} d) is issued. Download: {{ portal_link }}. Verify: {{ verify_link }}",
        "Rapport {{ report.number }} — {{ project.title }}",
        "Report {{ report.number }} — {{ project.title }}",
        V_REPORT,
    ),
    TemplateSpec(
        "REPORT_ISSUED", "sms",
        "Mizan Labs : rapport {{ report.number }} ({{ test.label }}) émis. {{ portal_link }}",
        "Mizan Labs: report {{ report.number }} ({{ test.label }}) issued. {{ portal_link }}",
        variables=V_REPORT,
    ),
    TemplateSpec(
        "REPORT_ISSUED", "in_app",
        "Rapport {{ report.number }} ({{ test.label }}, {{ age }} j) émis pour {{ project.title }}.",
        "Report {{ report.number }} ({{ test.label }}, {{ age }} d) issued for {{ project.title }}.",
        "Rapport {{ report.number }} émis",
        "Report {{ report.number }} issued",
        V_REPORT,
    ),
    # invoice.issued / invoice.overdue
    TemplateSpec(
        "INVOICE_ISSUED", "email",
        "Facture {{ invoice.number }} de {{ total }} {{ currency }}, échéance {{ due_date }}. Consulter : {{ portal_link }}",
        "Invoice {{ invoice.number }} for {{ total }} {{ currency }}, due {{ due_date }}. View: {{ portal_link }}",
        "Facture {{ invoice.number }} — {{ total }} {{ currency }}",
        "Invoice {{ invoice.number }} — {{ total }} {{ currency }}",
        V_INVOICE,
    ),
    TemplateSpec(
        "INVOICE_ISSUED", "whatsapp",
        "Facture {{ invoice.number }} de {{ total }} {{ currency }}, échéance {{ due_date }}. {{ portal_link }}",
        "Invoice {{ invoice.number }} for {{ total }} {{ currency }}, due {{ due_date }}. {{ portal_link }}",
        variables=V_INVOICE,
    ),
    TemplateSpec(
        "INVOICE_OVERDUE", "whatsapp",
        "Rappel : la facture {{ invoice.number }} ({{ balance }} {{ currency }}) est échue depuis {{ days }} jours.",
        "Reminder: invoice {{ invoice.number }} ({{ balance }} {{ currency }}) is {{ days }} days overdue.",
        variables=V_INVOICE,
    ),
    TemplateSpec(
        "INVOICE_OVERDUE", "email",
        "Rappel : la facture {{ invoice.number }} ({{ balance }} {{ currency }}) est échue depuis {{ days }} jours. Consulter : {{ portal_link }}",
        "Reminder: invoice {{ invoice.number }} ({{ balance }} {{ currency }}) is {{ days }} days overdue. View: {{ portal_link }}",
        "Rappel — facture {{ invoice.number }} échue",
        "Reminder — invoice {{ invoice.number }} overdue",
        V_INVOICE,
    ),
    # rental.late
    TemplateSpec(
        "RENTAL_LATE", "in_app",
        "Location {{ rental.number }} en retard : {{ equipment }} attendu le {{ due_date }} ({{ days }} j).",
        "Rental {{ rental.number }} is late: {{ equipment }} was due on {{ due_date }} ({{ days }} d).",
        "Location {{ rental.number }} en retard",
        "Rental {{ rental.number }} late",
        {"rental.number": "rental number", "equipment": "equipment", "due_date": "return date", "days": "days late"},
    ),
    TemplateSpec(
        "RENTAL_LATE", "whatsapp",
        "Mizan Labs : la location {{ rental.number }} ({{ equipment }}) devait être restituée le {{ due_date }}. Merci de nous contacter.",
        "Mizan Labs: rental {{ rental.number }} ({{ equipment }}) was due back on {{ due_date }}. Please contact us.",
        variables={"rental.number": "rental number", "equipment": "equipment", "due_date": "return date"},
    ),
    # verification.suspicious
    TemplateSpec(
        "VERIFICATION_SUSPICIOUS", "in_app",
        "Signalement sur le document {{ document.number }} ({{ document.kind }}) : {{ reason }}.",
        "Report on document {{ document.number }} ({{ document.kind }}): {{ reason }}.",
        "Document suspect signalé",
        "Suspicious document reported",
        {"document.number": "document number", "document.kind": "document kind", "reason": "reason"},
    ),
    TemplateSpec(
        "VERIFICATION_SUSPICIOUS", "email",
        "Un signalement a été déposé sur le document {{ document.number }} ({{ document.kind }}) : {{ reason }}. Dossier : {{ app_link }}",
        "A report was filed on document {{ document.number }} ({{ document.kind }}): {{ reason }}. Case: {{ app_link }}",
        "Document suspect signalé — {{ document.number }}",
        "Suspicious document reported — {{ document.number }}",
        {"document.number": "document number", "document.kind": "document kind", "reason": "reason", "app_link": "case link"},
    ),
    # otp (direct send)
    TemplateSpec(
        "OTP", "sms",
        "Code Mizan Labs : {{ otp }} (valable 10 min). Ne le partagez pas.",
        "Mizan Labs code: {{ otp }} (valid 10 min). Do not share it.",
        variables={"otp": "one-time code"},
    ),
    TemplateSpec(
        "OTP", "email",
        "Code Mizan Labs : {{ otp }} (valable 10 min). Ne le partagez pas.",
        "Mizan Labs code: {{ otp }} (valid 10 min). Do not share it.",
        "Votre code Mizan Labs",
        "Your Mizan Labs code",
        {"otp": "one-time code"},
    ),
    # daily digest
    TemplateSpec(
        "DAILY_DIGEST", "email",
        "{% for d in departments %}Résumé du {{ date }} — {{ d.department }} : {{ d.intakes }} réceptions, {{ d.done }} essais faits, {{ d.todo }} à faire, {{ d.overdue }} en retard, {{ d.tomorrow }} demain.\n{% endfor %}",
        "{% for d in departments %}Digest {{ date }} — {{ d.department }}: {{ d.intakes }} intakes, {{ d.done }} runs done, {{ d.todo }} to do, {{ d.overdue }} overdue, {{ d.tomorrow }} tomorrow.\n{% endfor %}",
        "Résumé du {{ date }} — {{ branch.code }}",
        "Digest {{ date }} — {{ branch.code }}",
        V_DIGEST,
    ),
)  # fmt: skip


@dataclass(frozen=True)
class RuleSpec:
    code: str
    event_code: str
    audience: dict[str, Any]
    channels: tuple[str, ...]
    template_code: str
    description: str = ""
    throttle: dict[str, Any] = field(default_factory=dict)
    digest: dict[str, Any] = field(default_factory=dict)
    respect_quiet_hours: bool = True


DEFAULT_RULES: tuple[RuleSpec, ...] = (
    RuleSpec("QUOTE_SENT", "quote.sent", {"contact_roles": ["SIGNATORY", "COMMERCIAL"]}, ("email", "whatsapp"), "QUOTE_SENT", "Client signatory and commercial contacts"),
    RuleSpec("QUOTE_ACCEPTED", "quote.accepted", {"payload_user_keys": ["owner_id"], "roles": ["LAB_SUPERVISOR", "FINANCE"]}, ("in_app", "email"), "QUOTE_ACCEPTED", "Quote owner, supervisors of the involved departments, finance"),
    RuleSpec("INTAKE_REGISTERED", "intake.registered", {"contact_roles": ["TECHNICAL"]}, ("sms", "whatsapp", "in_app"), "INTAKE_REGISTERED", "Client technical contact (short message and portal)"),
    RuleSpec("TEST_RUN_DUE_TOMORROW", "test_run.due_tomorrow", {"payload_user_keys": ["assignee_id"], "roles": ["LAB_SUPERVISOR"]}, ("in_app",), "TEST_RUN_DUE_TOMORROW", "Assigned technician and supervisor"),
    RuleSpec("REPORT_ISSUED", "report.issued", {"contact_roles": ["TECHNICAL", "COMMERCIAL"]}, ("email", "whatsapp", "sms", "in_app"), "REPORT_ISSUED", "Client technical and commercial contacts"),
    RuleSpec("INVOICE_ISSUED", "invoice.issued", {"contact_roles": ["ACCOUNTING"]}, ("email", "whatsapp"), "INVOICE_ISSUED", "Client accounting contact"),
    RuleSpec("INVOICE_OVERDUE", "invoice.overdue", {"contact_roles": ["ACCOUNTING"]}, ("email", "whatsapp"), "INVOICE_OVERDUE", "Client accounting contact", throttle={"window_seconds": 86400, "max": 1}),
    RuleSpec("RENTAL_LATE", "rental.late", {"roles": ["ASSETS"], "contact_roles": ["COMMERCIAL", "TECHNICAL"]}, ("in_app", "whatsapp"), "RENTAL_LATE", "Assets staff and client contact", throttle={"window_seconds": 86400, "max": 1}),
    RuleSpec("VERIFICATION_SUSPICIOUS", "verification.suspicious", {"roles": ["BRANCH_MANAGER"]}, ("in_app", "email"), "VERIFICATION_SUSPICIOUS", "Branch manager", respect_quiet_hours=False),
    RuleSpec("DAILY_DIGEST", "", {"roles": ["LAB_SUPERVISOR", "BRANCH_MANAGER"]}, ("email",), "DAILY_DIGEST", "Daily supervisor digest at 06:30 branch time", digest={"cron": "30 6 * * *", "query": "daily_supervisor"}),
)  # fmt: skip


def install_default_message_templates() -> int:
    created = 0
    for spec in DEFAULT_TEMPLATES:
        for locale, body, subject in (
            ("fr", spec.fr, spec.subject_fr),
            ("en", spec.en, spec.subject_en),
        ):
            _, was_created = MessageTemplate.objects.get_or_create(
                code=spec.code,
                locale=locale,
                channel=spec.channel,
                defaults={"subject": subject, "body": body, "variables": spec.variables},
            )
            created += int(was_created)
    return created


def install_default_notification_rules() -> int:
    created = 0
    for spec in DEFAULT_RULES:
        _, was_created = NotificationRule.objects.get_or_create(
            branch=None,
            code=spec.code,
            defaults={
                "event_code": spec.event_code,
                "audience": spec.audience,
                "channels": list(spec.channels),
                "template_code": spec.template_code,
                "throttle": spec.throttle,
                "digest": spec.digest,
                "respect_quiet_hours": spec.respect_quiet_hours,
                "description": spec.description,
            },
        )
        created += int(was_created)
    return created


def install_defaults() -> dict[str, int]:
    return {
        "templates": install_default_message_templates(),
        "rules": install_default_notification_rules(),
    }
