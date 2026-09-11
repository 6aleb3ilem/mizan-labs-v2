"""Price resolution (SPEC §10.6): account-specific → tier → branch default, most recent valid."""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

from django.db.models import Q

from mizan.apps.config.models import ConfigStatus, Price


def resolve_price(
    *,
    service_id: uuid.UUID,
    branch_id: uuid.UUID,
    on: dt.date,
    account_id: uuid.UUID | None = None,
    client_tier_id: uuid.UUID | None = None,
    specimen_type_id: uuid.UUID | None = None,
    quantity: Decimal = Decimal(1),
) -> Price | None:
    base = (
        Price.objects.select_related("price_list")
        .filter(
            service_id=service_id,
            price_list__branch_id=branch_id,
            price_list__status=ConfigStatus.ACTIVE,
            price_list__valid_from__lte=on,
            min_qty__lte=quantity,
        )
        .filter(Q(price_list__valid_to__isnull=True) | Q(price_list__valid_to__gte=on))
        .filter(Q(specimen_type_id=specimen_type_id) | Q(specimen_type__isnull=True))
        .order_by("-price_list__valid_from", "-min_qty", "specimen_type_id")
    )
    if account_id is not None:
        specific: Price | None = base.filter(price_list__account_id=account_id).first()
        if specific is not None:
            return specific
    if client_tier_id is not None:
        tiered: Price | None = base.filter(
            price_list__account_id__isnull=True, price_list__client_tier_id=client_tier_id
        ).first()
        if tiered is not None:
            return tiered
    default: Price | None = base.filter(
        price_list__account_id__isnull=True, price_list__client_tier__isnull=True
    ).first()
    return default
