"""Payment terms templates (SPEC §10.10) and the milestone rounding rule of §13.2."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from mizan.apps.config.models import PaymentTermsTemplate
from mizan.platform.api.errors import UnprocessableEntity

TRIGGERS = ("ON_ACCEPTANCE", "ON_DELIVERY", "ON_REPORT", "ON_DATE", "ON_PHASE", "MANUAL")
CENT = Decimal("0.01")


def validate_milestones(milestones: list[dict[str, Any]]) -> list[dict[str, Any]]:
    problems: list[dict[str, Any]] = []
    if not milestones:
        return [{"loc": ["milestones"], "msg": "at least one milestone"}]
    percents = [m for m in milestones if m.get("percent") is not None]
    amounts = [m for m in milestones if m.get("amount") is not None]
    if percents and amounts:
        problems.append(
            {"loc": ["milestones"], "msg": "percent and amount milestones cannot be mixed"}
        )
    if percents and sum(Decimal(str(m["percent"])) for m in percents) != Decimal(100):
        problems.append({"loc": ["milestones"], "msg": "percents must total 100"})
    for i, m in enumerate(milestones):
        if m.get("trigger") not in TRIGGERS:
            problems.append(
                {
                    "loc": ["milestones", i, "trigger"],
                    "msg": f"trigger must be one of {', '.join(TRIGGERS)}",
                }
            )
        if m.get("percent") is None and m.get("amount") is None:
            problems.append({"loc": ["milestones", i], "msg": "percent or amount required"})
        if not (m.get("label") or {}):
            problems.append({"loc": ["milestones", i, "label"], "msg": "label required"})
    return problems


def compute_amounts(milestones: list[dict[str, Any]], total: Decimal) -> list[Decimal]:
    """Percent milestones: rounded to the cent, the last one absorbs the rounding difference."""
    total = Decimal(total).quantize(CENT, rounding=ROUND_HALF_UP)
    if any(m.get("amount") is not None for m in milestones):
        amounts = [
            Decimal(str(m["amount"])).quantize(CENT, rounding=ROUND_HALF_UP) for m in milestones
        ]
        if sum(amounts, Decimal(0)) != total:
            raise UnprocessableEntity(
                "sales.milestones.amounts_must_equal_total", params={"total": str(total)}
            )
        return amounts
    amounts = [
        (total * Decimal(str(m["percent"])) / Decimal(100)).quantize(CENT, rounding=ROUND_HALF_UP)
        for m in milestones[:-1]
    ]
    amounts.append(total - sum(amounts, Decimal(0)))
    return amounts


def default_template(branch_id: Any) -> PaymentTermsTemplate | None:
    template: PaymentTermsTemplate | None = (
        PaymentTermsTemplate.objects.filter(branch_id=branch_id, active=True)
        .order_by("-is_default", "code")
        .first()
    )
    return template
