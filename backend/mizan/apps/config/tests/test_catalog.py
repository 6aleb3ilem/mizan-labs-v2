"""Vocabularies, price resolution order, tax rules."""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal
from typing import Any

import pytest

from mizan.apps.config import vocabularies
from mizan.apps.config.defaults.vocabularies import (
    DEFAULT_VOCABULARIES,
    install_default_vocabularies,
)
from mizan.apps.config.models import (
    Price,
    PriceList,
    Service,
    ServiceCategory,
    SpecimenType,
    VocabularyEntry,
)
from mizan.apps.config.prices import resolve_price
from mizan.platform.api.errors import NotFound

pytestmark = pytest.mark.django_db


def test_vocabularies_install_resolve_and_retire(scoped: Any, branch: Any) -> None:
    assert set(DEFAULT_VOCABULARIES) <= set(vocabularies.KINDS)
    created = install_default_vocabularies()
    assert created > 40
    assert install_default_vocabularies() == 0
    entry = vocabularies.resolve("sample_nature", "SOIL")
    assert entry.label("fr") == "Sol"
    local = VocabularyEntry.objects.create(branch=branch, kind="curing_location", code="TANK_B")
    assert vocabularies.resolve("curing_location", "TANK_B", branch.id) == local
    with pytest.raises(NotFound):
        vocabularies.resolve("curing_location", "TANK_B")

    @vocabularies.register_usage("sample_nature", "samples")
    def _count(e: VocabularyEntry) -> int:
        return 3

    assert vocabularies.usage_of(entry) == {"samples": 3}
    vocabularies.retire(entry)
    entry.refresh_from_db()
    assert entry.active is False and entry.retired_at is not None


def test_price_resolution_order(scoped: Any, branch: Any) -> None:
    category = ServiceCategory.objects.create(code="TESTS.CONCRETE")
    service = Service.objects.create(
        category=category, code="CONCRETE_COMPRESSION", kind="LAB_TEST", unit_of_sale="PER_SPECIMEN"
    )
    cyl = SpecimenType.objects.create(code="CYL_16x32", shape="CYLINDER", dims={"d": 16})
    tier = VocabularyEntry.objects.create(kind="client_tier", code="KEY_ACCOUNT")
    account_id = uuid.uuid4()
    base = PriceList.objects.create(
        branch=branch, code="BASE", currency="MRU", valid_from=dt.date(2026, 1, 1)
    )
    old = PriceList.objects.create(
        branch=branch,
        code="OLD",
        currency="MRU",
        valid_from=dt.date(2025, 1, 1),
        valid_to=dt.date(2025, 12, 31),
    )
    tiered = PriceList.objects.create(
        branch=branch, code="KEY", currency="MRU", valid_from=dt.date(2026, 1, 1), client_tier=tier
    )
    mine = PriceList.objects.create(
        branch=branch,
        code="SOGECO",
        currency="MRU",
        valid_from=dt.date(2026, 1, 1),
        account_id=account_id,
    )
    Price.objects.create(price_list=old, service=service, unit_price=Decimal("2000"))
    Price.objects.create(price_list=base, service=service, unit_price=Decimal("2500"))
    Price.objects.create(
        price_list=base, service=service, specimen_type=cyl, unit_price=Decimal("2600")
    )
    Price.objects.create(
        price_list=base, service=service, unit_price=Decimal("2300"), min_qty=Decimal(20)
    )
    Price.objects.create(price_list=tiered, service=service, unit_price=Decimal("2200"))
    Price.objects.create(price_list=mine, service=service, unit_price=Decimal("2100"))
    on = dt.date(2026, 9, 11)
    kw = {"service_id": service.id, "branch_id": branch.id, "on": on}
    assert resolve_price(**kw).unit_price == Decimal("2500")  # type: ignore[union-attr]
    assert resolve_price(**kw, specimen_type_id=cyl.id).unit_price == Decimal("2600")  # type: ignore[union-attr]
    assert resolve_price(**kw, quantity=Decimal(25)).unit_price == Decimal("2300")  # type: ignore[union-attr]
    assert resolve_price(**kw, client_tier_id=tier.id).unit_price == Decimal("2200")  # type: ignore[union-attr]
    assert resolve_price(**kw, account_id=account_id, client_tier_id=tier.id).unit_price == Decimal(
        "2100"
    )  # type: ignore[union-attr]
    assert resolve_price(
        service_id=service.id, branch_id=branch.id, on=dt.date(2025, 6, 1)
    ).unit_price == Decimal("2000")  # type: ignore[union-attr]
    assert resolve_price(service_id=uuid.uuid4(), branch_id=branch.id, on=on) is None
