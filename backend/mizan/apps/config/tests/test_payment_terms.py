"""SPEC §10.10 and §13.2: templates, validation, rounding absorbed by the last milestone."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mizan.apps.config import payment_terms
from mizan.apps.config.defaults.payment_terms import install_default_payment_terms
from mizan.platform.api.errors import UnprocessableEntity


def test_validation() -> None:
    ok = [
        {"order": 1, "label": {"fr": "A"}, "percent": 30, "trigger": "ON_ACCEPTANCE"},
        {"order": 2, "label": {"fr": "B"}, "percent": 70, "trigger": "ON_REPORT"},
    ]
    assert payment_terms.validate_milestones(ok) == []
    bad = [
        {"order": 1, "label": {}, "percent": 30, "trigger": "ON_MOON"},
        {"order": 2, "label": {"fr": "B"}, "amount": 10, "trigger": "ON_REPORT"},
    ]
    messages = [p["msg"] for p in payment_terms.validate_milestones(bad)]
    assert any("mixed" in m for m in messages)
    assert any("trigger" in m for m in messages)
    assert any("label" in m for m in messages)
    assert payment_terms.validate_milestones([]) != []


def test_spec_example_amounts() -> None:
    milestones = [
        {"percent": 30, "trigger": "ON_ACCEPTANCE", "label": {"fr": "A"}},
        {"percent": 70, "trigger": "ON_REPORT", "label": {"fr": "B"}},
    ]
    assert payment_terms.compute_amounts(milestones, Decimal("60610.00")) == [
        Decimal("18183.00"),
        Decimal("42427.00"),
    ]
    thirds = [
        {"percent": Decimal("33.33")},
        {"percent": Decimal("33.33")},
        {"percent": Decimal("33.34")},
    ]
    amounts = payment_terms.compute_amounts(thirds, Decimal("100.00"))
    assert amounts == [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]
    fixed = [{"amount": "40.00"}, {"amount": "60.00"}]
    assert payment_terms.compute_amounts(fixed, Decimal("100")) == [
        Decimal("40.00"),
        Decimal("60.00"),
    ]
    with pytest.raises(UnprocessableEntity):
        payment_terms.compute_amounts([{"amount": "40.00"}, {"amount": "50.00"}], Decimal("100"))


@settings(max_examples=200, deadline=None)
@given(
    total=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("99999999.99"), places=2),
    splits=st.lists(st.integers(min_value=1, max_value=97), min_size=1, max_size=6),
)
def test_percent_milestones_always_sum_to_the_total(total: Decimal, splits: list[int]) -> None:
    weights = sum(splits)
    percents = [Decimal(s) * 100 / weights for s in splits]
    percents[-1] = Decimal(100) - sum(percents[:-1])
    milestones = [{"percent": p} for p in percents]
    amounts = payment_terms.compute_amounts(milestones, total)
    assert sum(amounts) == total
    assert all(a == a.quantize(Decimal("0.01")) for a in amounts)


@pytest.mark.django_db
def test_default_templates(branch: Any) -> None:
    created = install_default_payment_terms(branch)
    assert {t.code for t in created} == {"FULL_ON_ORDER", "30_70_REPORT", "40_30_30_PHASES"}
    default = payment_terms.default_template(branch.id)
    assert default is not None and default.code == "30_70_REPORT"
    assert default.label("en") == "30 % on acceptance, 70 % on report"
    for template in created:
        assert payment_terms.validate_milestones(template.milestones) == []
    assert install_default_payment_terms(branch) == []  # idempotent
