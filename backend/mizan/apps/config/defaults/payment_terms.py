"""Default payment terms templates of a new branch (SPEC §10.10 examples)."""

from __future__ import annotations

from typing import Any

from mizan.apps.config.models import PaymentTermsTemplate

DEFAULT_PAYMENT_TERMS: tuple[dict[str, Any], ...] = (
    {
        "code": "FULL_ON_ORDER",
        "labels": {"fr": "100 % à la commande", "en": "100 % on order"},
        "is_default": False,
        "milestones": [
            {"order": 1, "label": {"fr": "À la commande", "en": "On order"}, "percent": 100, "trigger": "ON_ACCEPTANCE", "due_days_after_trigger": 0}
        ],
    },
    {
        "code": "30_70_REPORT",
        "labels": {"fr": "30 % à l'acceptation, 70 % à la remise du rapport", "en": "30 % on acceptance, 70 % on report"},
        "is_default": True,
        "milestones": [
            {"order": 1, "label": {"fr": "Acompte à l'acceptation", "en": "Deposit on acceptance"}, "percent": 30, "trigger": "ON_ACCEPTANCE", "due_days_after_trigger": 0},
            {"order": 2, "label": {"fr": "Solde à la remise du rapport", "en": "Balance on report"}, "percent": 70, "trigger": "ON_REPORT", "due_days_after_trigger": 30},
        ],
    },
    {
        "code": "40_30_30_PHASES",
        "labels": {"fr": "40 % / 30 % / 30 % par phase", "en": "40 % / 30 % / 30 % per phase"},
        "is_default": False,
        "milestones": [
            {"order": 1, "label": {"fr": "Démarrage", "en": "Kick-off"}, "percent": 40, "trigger": "ON_ACCEPTANCE", "due_days_after_trigger": 0},
            {"order": 2, "label": {"fr": "Phase intermédiaire", "en": "Intermediate phase"}, "percent": 30, "trigger": "ON_PHASE", "trigger_params": {"phase": 2}, "due_days_after_trigger": 30},
            {"order": 3, "label": {"fr": "Remise finale", "en": "Final delivery"}, "percent": 30, "trigger": "ON_DELIVERY", "due_days_after_trigger": 30},
        ],
    },
)  # fmt: skip


def install_default_payment_terms(branch: Any) -> list[PaymentTermsTemplate]:
    created: list[PaymentTermsTemplate] = []
    for spec in DEFAULT_PAYMENT_TERMS:
        template, was_created = PaymentTermsTemplate.objects.get_or_create(
            branch=branch,
            code=spec["code"],
            defaults={"is_default": spec["is_default"], "milestones": spec["milestones"]},
        )
        template.set_labels(spec["labels"])
        if was_created:
            created.append(template)
    return created
