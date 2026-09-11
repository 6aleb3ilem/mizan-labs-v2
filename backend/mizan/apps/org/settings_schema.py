"""Typed branch settings (SPEC §10.9, Appendix W). Stored as JSON on the branch; validated here."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class QuietHours(BaseModel):
    start: str = Field(pattern=r"^\d{2}:\d{2}$")
    end: str = Field(pattern=r"^\d{2}:\d{2}$")


class BranchSettings(BaseModel):
    model_config = ConfigDict(extra="allow")

    discount_approval_threshold_percent: Decimal = Field(default=Decimal("10"), ge=0, le=100)
    default_quote_validity_days: int = Field(default=30, ge=1, le=365)
    invoice_due_days: int = Field(default=30, ge=0, le=365)
    dunning_schedule_days: list[int] = Field(default_factory=lambda: [7, 21, 45])
    reviewer_must_differ_from_entrant: bool = True
    cash_close_approval_threshold: Decimal = Field(default=Decimal("0"), ge=0)
    late_rental_penalty_factor: Decimal = Field(default=Decimal("1"), ge=0)
    daily_capacity_per_department: dict[str, int] = Field(default_factory=dict)
    offline_cache_days: int = Field(default=2, ge=1, le=14)
    quiet_hours: QuietHours | None = None
    public_digest_exposure: bool = True
    notification_fallback_channels: list[str] = Field(
        default_factory=lambda: ["whatsapp", "sms", "email"]
    )


def validate_settings(data: dict[str, Any]) -> dict[str, Any]:
    return BranchSettings.model_validate(data).model_dump(mode="json")
