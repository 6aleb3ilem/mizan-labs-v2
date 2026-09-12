"""Seed the demo tenant (SPEC Appendix R step 14): branch NKC, departments, roles, numbering,
workflows, vocabularies, payment terms, signatory (IMAGE mode with a placeholder), document
templates and print profiles, signing keys, the four test definitions, services and prices,
notification rules and templates, and demo users. Idempotent: re-running updates nothing that
exists and creates what is missing."""

from __future__ import annotations

import base64
import datetime as dt
from decimal import Decimal
from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from mizan.platform import context
from mizan.platform.db.tenancy import platform_scope, tenant_scope

# A 1x1 transparent PNG: the signature placeholder until the real image is approved.
PLACEHOLDER_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)

DEPARTMENTS: tuple[tuple[str, str, str, str], ...] = (
    ("CONCRETE", "Béton", "Concrete", "blue"),
    ("SOILS", "Sols et granulats", "Soils and aggregates", "amber"),
    ("STEEL", "Aciers", "Steel", "slate"),
    ("BITUMEN", "Bitumes et enrobés", "Bitumen and asphalt", "brown"),
)

SERVICES: tuple[dict[str, Any], ...] = (
    {"code": "CONCRETE_COMPRESSION", "category": "TESTS.CONCRETE", "kind": "LAB_TEST", "unit_of_sale": "PER_SPECIMEN", "definition": "CONCRETE_COMPRESSION", "price": "2500.00", "labels": {"fr": "Écrasement d'éprouvettes béton", "en": "Concrete compressive strength"}},
    {"code": "BLOCK_COMPRESSION", "category": "TESTS.BLOCKS", "kind": "LAB_TEST", "unit_of_sale": "PER_SPECIMEN", "definition": "BLOCK_COMPRESSION", "price": "2000.00", "labels": {"fr": "Écrasement de parpaings", "en": "Block compressive strength"}},
    {"code": "SIEVE_ANALYSIS", "category": "TESTS.AGGREGATES", "kind": "LAB_TEST", "unit_of_sale": "PER_SAMPLE", "definition": "SIEVE_ANALYSIS", "price": "8000.00", "labels": {"fr": "Analyse granulométrique", "en": "Sieve analysis"}},
    {"code": "WATER_CONTENT", "category": "TESTS.SOILS", "kind": "LAB_TEST", "unit_of_sale": "PER_SAMPLE", "definition": "WATER_CONTENT", "price": "3000.00", "labels": {"fr": "Teneur en eau", "en": "Water content"}},
    {"code": "FIELD_SAMPLING", "category": "FIELD", "kind": "FIELD_SERVICE", "unit_of_sale": "PER_VISIT", "definition": "", "price": "15000.00", "labels": {"fr": "Prélèvement sur chantier", "en": "Site sampling"}},
    {"code": "GEOTECH_STUDY", "category": "STUDIES", "kind": "STUDY", "unit_of_sale": "UNIT", "definition": "", "price": "450000.00", "labels": {"fr": "Étude géotechnique", "en": "Geotechnical study"}},
)  # fmt: skip

USERS: tuple[dict[str, Any], ...] = (
    {"email": "admin@demo.mizanlabs.dev", "name": "Administrateur", "role": "TENANT_ADMIN", "all_branches": True},
    {"email": "aicha@demo.mizanlabs.dev", "name": "Aïcha", "role": "COMMERCIAL"},
    {"email": "moussa@demo.mizanlabs.dev", "name": "Moussa", "role": "LAB_RECEPTION"},
    {"email": "sidi@demo.mizanlabs.dev", "name": "Sidi", "role": "TECHNICIAN", "department": "CONCRETE"},
    {"email": "fatimetou@demo.mizanlabs.dev", "name": "Fatimetou", "role": "LAB_SUPERVISOR", "department": "CONCRETE"},
    {"email": "mohamed@demo.mizanlabs.dev", "name": "Mohamed", "role": "FINANCE"},
    {"email": "director@demo.mizanlabs.dev", "name": "Direction", "role": "BRANCH_MANAGER"},
    {"email": "assets@demo.mizanlabs.dev", "name": "Matériel", "role": "ASSETS"},
)  # fmt: skip


class Command(BaseCommand):
    help = "Create the demo tenant with a complete configuration and demo users."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--tenant-code", default="DEMO")
        parser.add_argument("--tenant-name", default="Mizan Labs (démo)")
        parser.add_argument("--branch-code", default="NKC")
        parser.add_argument(
            "--password", default="Demo-Passw0rd!", help="password of the demo users"
        )
        parser.add_argument("--no-users", action="store_true")
        parser.add_argument("--operator-email", default="operator@mizan-platform.dev")

    def handle(self, *args: Any, **options: Any) -> None:
        token = context.current_actor.set(context.Actor.system())
        try:
            summary = seed(
                tenant_code=str(options["tenant_code"]).upper(),
                tenant_name=str(options["tenant_name"]),
                branch_code=str(options["branch_code"]).upper(),
                password=str(options["password"]),
                with_users=not options["no_users"],
                operator_email=str(options["operator_email"]),
            )
        finally:
            context.current_actor.reset(token)
        for key, value in summary.items():
            self.stdout.write(f"{key:24} {value}")


def seed(
    *,
    tenant_code: str,
    tenant_name: str,
    branch_code: str,
    password: str,
    with_users: bool,
    operator_email: str,
) -> dict[str, Any]:
    from mizan.apps.identity.models import Realm, User
    from mizan.apps.org.models import Tenant

    summary: dict[str, Any] = {}
    with platform_scope():
        tenant, created = Tenant.objects.get_or_create(
            code=tenant_code,
            defaults={"name": tenant_name, "theme": {"primary": "#FF8A00", "logo_object_key": ""}},
        )
        summary["tenant"] = f"{tenant.code} ({'created' if created else 'exists'})"
        if (
            with_users
            and not User.objects.filter(email__iexact=operator_email, realm=Realm.PLATFORM).exists()
        ):
            User.objects.create_superuser(
                operator_email, password, display_name="Platform operator"
            )
            summary["operator"] = operator_email

    with tenant_scope(tenant.id), transaction.atomic():
        summary.update(
            _seed_tenant(tenant, branch_code=branch_code, password=password, with_users=with_users)
        )
    return summary


def _seed_tenant(
    tenant: Any, *, branch_code: str, password: str, with_users: bool
) -> dict[str, Any]:
    from mizan.apps.config.defaults.numbering import install_default_numbering
    from mizan.apps.config.defaults.payment_terms import install_default_payment_terms
    from mizan.apps.config.defaults.test_definitions import install_default_test_definitions
    from mizan.apps.config.defaults.vocabularies import install_default_vocabularies
    from mizan.apps.config.defaults.workflows import install_default_workflows
    from mizan.apps.config.models import (
        ConfigStatus,
        Price,
        PriceList,
        Service,
        ServiceCategory,
        TaxRule,
    )
    from mizan.apps.documents import keys
    from mizan.apps.documents.defaults import (
        install_default_print_profiles,
        install_default_templates,
    )
    from mizan.apps.identity.models import Realm, User
    from mizan.apps.identity.roles import install_default_roles
    from mizan.apps.identity.services import add_membership
    from mizan.apps.notify.defaults import install_defaults as install_notify_defaults
    from mizan.apps.org.models import Branch, Department, Signatory, SignatureMode, TreasuryAccount
    from mizan.platform.storage import attachments_storage

    summary: dict[str, Any] = {}
    branch, created = Branch.objects.get_or_create(
        code=branch_code,
        defaults={
            "legal_name": "Mizan Labs SARL",
            "trade_name": "Mizan Labs Nouakchott",
            "identifiers": {"nif": "00000000", "rc": "RC-NKC-0000"},
            "address": {"line1": "Tevragh Zeina", "city": "Nouakchott", "country": "MR"},
            "phone": "+22245000000",
            "email": "lab@demo.mizanlabs.dev",
            "currency": "MRU",
            "timezone": "Africa/Nouakchott",
            "locales": ["fr", "en"],
            "default_locale": "fr",
            "working_days": [1, 2, 3, 4, 5, 6],
            "holidays": [],
            "settings": {
                "discount_approval_threshold_percent": "10",
                "default_quote_validity_days": 30,
                "invoice_due_days": 30,
                "dunning_schedule_days": [7, 21, 45],
                "quiet_hours": {"start": "21:00", "end": "07:00"},
                "daily_capacity_per_department": {"CONCRETE": 40, "SOILS": 20},
            },
            "legal_texts": {
                "footer": {
                    "fr": "Mizan Labs SARL — laboratoire d'essais",
                    "en": "Mizan Labs SARL — testing laboratory",
                }
            },
        },
    )
    summary["branch"] = f"{branch.code} ({'created' if created else 'exists'})"

    departments: dict[str, Department] = {}
    for ord_, (code, fr, en, colour) in enumerate(DEPARTMENTS, start=1):
        department, _ = Department.objects.get_or_create(
            branch=branch, code=code, defaults={"colour": colour, "ord": ord_}
        )
        department.set_labels({"fr": fr, "en": en})
        departments[code] = department
    summary["departments"] = len(departments)

    roles = install_default_roles()
    summary["roles"] = len(roles)
    summary["numbering_schemes"] = len(install_default_numbering(branch))
    summary["workflows"] = len(install_default_workflows())
    summary["vocabulary_entries"] = install_default_vocabularies()
    summary["payment_terms"] = len(install_default_payment_terms(branch))

    for kind, defaults in (
        ("BANK", {"label": "Banque principale", "bank_name": "Banque de Mauritanie", "iban": "MR13000000000000000000000", "bic": "BMMRMRMR", "printed_on_invoices": True}),
        ("CASH", {"label": "Caisse Nouakchott"}),
    ):  # fmt: skip
        TreasuryAccount.objects.get_or_create(
            branch=branch,
            type=kind,
            label=str(defaults["label"]),
            defaults={**defaults, "currency": "MRU"},
        )
    summary["treasury_accounts"] = TreasuryAccount.objects.filter(branch=branch).count()

    templates = install_default_templates()
    summary["document_templates"] = f"{len(templates)} created"
    summary["print_profiles"] = install_default_print_profiles(branch)
    qr_key, seal_key = keys.ensure_branch_keys(branch)
    summary["signing_keys"] = f"{qr_key.kid}, {seal_key.kid}"

    definitions = install_default_test_definitions(departments)
    summary["test_definitions"] = ", ".join(d.code for d in definitions)

    categories = {c.code: c for c in ServiceCategory.objects.all()}
    price_list, _ = PriceList.objects.get_or_create(
        branch=branch,
        code="STANDARD",
        defaults={
            "currency": "MRU",
            "valid_from": dt.date(dt.date.today().year, 1, 1),
            "status": ConfigStatus.ACTIVE,
        },
    )
    price_list.set_labels({"fr": "Tarif standard", "en": "Standard price list"})
    for spec in SERVICES:
        service, _ = Service.objects.get_or_create(
            code=spec["code"],
            defaults={
                "category": categories[spec["category"]],
                "department": departments.get("CONCRETE")
                if spec["category"].endswith(("CONCRETE", "BLOCKS"))
                else departments.get("SOILS")
                if spec["category"].startswith("TESTS.")
                else None,
                "kind": spec["kind"],
                "unit_of_sale": spec["unit_of_sale"],
                "test_definition_code": spec["definition"],
            },
        )
        service.set_labels(spec["labels"])
        Price.objects.get_or_create(
            price_list=price_list,
            service=service,
            specimen_type=None,
            defaults={"unit_price": Decimal(spec["price"]), "min_qty": Decimal("1")},
        )
    summary["services"] = Service.objects.count()
    summary["prices"] = Price.objects.filter(price_list=price_list).count()
    tax, _ = TaxRule.objects.get_or_create(
        branch=branch,
        code="VAT_16",
        defaults={
            "rate": Decimal("16.00"),
            "applies_to_kinds": ["LAB_TEST", "FIELD_SERVICE", "STUDY", "RENTAL", "SALE", "FEE"],
        },
    )
    tax.set_labels({"fr": "TVA 16 %", "en": "VAT 16 %"})

    notify = install_notify_defaults()
    summary["notification_rules"] = notify["rules"]
    summary["message_templates"] = notify["templates"]

    users: dict[str, User] = {}
    if with_users:
        for spec in USERS:
            user = User.objects.filter(email__iexact=spec["email"]).first()
            if user is None:
                user = User.objects.create_user(
                    spec["email"],
                    password,
                    tenant_id=tenant.id,
                    display_name=spec["name"],
                    realm=Realm.STAFF,
                )
                department = departments.get(spec.get("department", ""))
                add_membership(
                    user=user,
                    role=roles[spec["role"]],
                    branch_id=None if spec.get("all_branches") else branch.id,
                    department_id=department.id if department else None,
                )
            users[spec["email"]] = user
        summary["users"] = len(users)

    signatory, created = Signatory.objects.get_or_create(
        branch=branch,
        display_name="Direction du laboratoire",
        defaults={
            "user": users.get("director@demo.mizanlabs.dev"),
            "title": "Directeur du laboratoire",
            "document_kinds": ["QUOTE", "CONTRACT", "REPORT", "INVOICE", "CREDIT_NOTE"],
            "mode": SignatureMode.IMAGE,
            "image_positions": {"PV_CONCRETE": {"x": 140, "y": 250}, "QUOTE": {"x": 140, "y": 260}},
            "requires_step_up": True,
            "signing_order": 1,
        },
    )
    if created or not signatory.signature_image_key:
        key = f"signatures/{branch.code.lower()}/{signatory.id}/placeholder.png"
        attachments_storage().put(key, PLACEHOLDER_PNG, "image/png")
        signatory.signature_image_key = key
        signatory.image_version = 1
        signatory.save(update_fields=["signature_image_key", "image_version"])
    summary["signatory"] = f"{signatory.display_name} ({signatory.mode})"
    return summary
