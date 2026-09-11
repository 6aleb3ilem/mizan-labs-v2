"""Numbering schemes (SPEC §10.1): patterns, periods, atomic allocation, reservations, preview."""

from __future__ import annotations

import datetime as dt
import re
import uuid
from dataclasses import dataclass
from typing import Any

from django.db import connection, transaction
from django.utils import timezone

from mizan.apps.config.models import (
    Allocation,
    ConfigStatus,
    GapPolicy,
    NumberingCounter,
    NumberingReset,
    NumberingScheme,
    NumberReservation,
)
from mizan.platform import context
from mizan.platform.api.errors import Conflict, NotFound, UnprocessableEntity
from mizan.platform.ids import short_id, uuid7

TOKEN_RE = re.compile(r"\{(PREFIX|BRANCH|DEPT|YYYY|YY|MM|SEQ(?::(\d+))?)\}")
MAX_SKIPS = 10_000


class NumberingError(UnprocessableEntity):
    code = "numbering_invalid"
    message_key = "config.numbering.invalid"


@dataclass(frozen=True, slots=True)
class AllocatedNumber:
    number: str
    scheme_id: uuid.UUID
    sequence: int
    period_key: str


def validate_scheme(pattern: str, gap_policy: str, allocation: str) -> None:
    tokens = TOKEN_RE.findall(pattern)
    if not any(t[0].startswith("SEQ") for t in tokens):
        raise NumberingError(
            "config.numbering.pattern_needs_seq",
            details=[{"loc": ["pattern"], "msg": "{SEQ:n} required"}],
        )
    if sum(1 for t in tokens if t[0].startswith("SEQ")) > 1:
        raise NumberingError(
            "config.numbering.pattern_one_seq",
            details=[{"loc": ["pattern"], "msg": "one {SEQ:n} only"}],
        )
    if re.search(r"\{[^}]*\}", TOKEN_RE.sub("", pattern)):
        raise NumberingError(
            "config.numbering.unknown_token", details=[{"loc": ["pattern"], "msg": "unknown token"}]
        )
    if gap_policy == GapPolicy.GAP_FREE and allocation != Allocation.ON_ISSUE:
        raise NumberingError(
            "config.numbering.gap_free_requires_on_issue",
            details=[{"loc": ["allocation"], "msg": "GAP_FREE must allocate ON_ISSUE"}],
        )


def period_key(reset: str, on: dt.date) -> str:
    if reset == NumberingReset.YEARLY:
        return f"{on:%Y}"
    if reset == NumberingReset.MONTHLY:
        return f"{on:%Y-%m}"
    return ""


def format_number(
    pattern: str,
    *,
    prefix: str = "",
    branch_code: str = "",
    department_code: str = "",
    on: dt.date,
    sequence: int,
) -> str:
    def repl(match: re.Match[str]) -> str:
        token, width = match.group(1), match.group(2)
        if token == "PREFIX":
            return prefix
        if token == "BRANCH":
            return branch_code
        if token == "DEPT":
            return department_code
        if token == "YYYY":
            return f"{on:%Y}"
        if token == "YY":
            return f"{on:%y}"
        if token == "MM":
            return f"{on:%m}"
        return str(sequence).zfill(int(width or 1))

    return TOKEN_RE.sub(repl, pattern)


def draft_number(record_id: uuid.UUID) -> str:
    """What a not-yet-numbered record displays (ON_ISSUE schemes)."""
    return f"DRAFT-{short_id(record_id)}"


def _today(scheme: NumberingScheme) -> dt.date:
    return timezone.now().date()


def active_scheme(
    applies_to: str, branch_id: uuid.UUID, department_id: uuid.UUID | None = None
) -> NumberingScheme:
    """Department-specific scheme first, then the branch scheme."""
    qs = NumberingScheme.objects.filter(
        branch_id=branch_id, applies_to=applies_to, status=ConfigStatus.ACTIVE
    )
    if department_id is not None:
        specific: NumberingScheme | None = (
            qs.filter(department_id=department_id).order_by("-version").first()
        )
        if specific is not None:
            return specific
    scheme: NumberingScheme | None = qs.filter(department__isnull=True).order_by("-version").first()
    if scheme is None:
        raise NotFound("config.numbering.no_active_scheme", params={"applies_to": applies_to})
    return scheme


def _format(scheme: NumberingScheme, sequence: int, on: dt.date) -> str:
    return format_number(
        scheme.pattern,
        prefix=scheme.prefix,
        branch_code=scheme.branch.code,
        department_code=scheme.department.code if scheme.department is not None else "",
        on=on,
        sequence=sequence,
    )


def _next_counter_value(scheme: NumberingScheme, key: str) -> int:
    """One statement: insert-or-increment the counter row and return the new value."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO numbering_counter (id, tenant_id, scheme_id, period_key, value)
            VALUES (%s, %s, %s, %s, 1)
            ON CONFLICT (scheme_id, period_key)
            DO UPDATE SET value = numbering_counter.value + 1
            RETURNING value
            """,
            [uuid7(), scheme.tenant_id, scheme.id, key],
        )
        row = cursor.fetchone()
    return int(row[0])


def allocate(scheme: NumberingScheme, *, on: dt.date | None = None) -> AllocatedNumber:
    """Allocate the next number inside the caller's transaction; reserved numbers are skipped."""
    if scheme.status != ConfigStatus.ACTIVE:
        raise Conflict("config.numbering.scheme_not_active", code="scheme_not_active")
    on = on or _today(scheme)
    key = period_key(scheme.reset, on)
    reserved = set(NumberReservation.objects.filter(scheme=scheme).values_list("number", flat=True))
    for _ in range(MAX_SKIPS):
        sequence = _next_counter_value(scheme, key)
        number = _format(scheme, sequence, on)
        if number not in reserved:
            break
    else:  # pragma: no cover - pathological reservation table
        raise Conflict("config.numbering.exhausted", code="numbering_exhausted")
    if not scheme.immutable:
        NumberingScheme.all_objects.filter(pk=scheme.pk, immutable=False).update(immutable=True)
        scheme.immutable = True
    return AllocatedNumber(number=number, scheme_id=scheme.id, sequence=sequence, period_key=key)


def preview(scheme: NumberingScheme, *, on: dt.date | None = None) -> str:
    """The number the next allocation would produce (nothing is consumed)."""
    on = on or _today(scheme)
    key = period_key(scheme.reset, on)
    counter = NumberingCounter.objects.filter(scheme=scheme, period_key=key).first()
    sequence = (counter.value if counter else 0) + 1
    reserved = set(NumberReservation.objects.filter(scheme=scheme).values_list("number", flat=True))
    number = _format(scheme, sequence, on)
    while number in reserved:
        sequence += 1
        number = _format(scheme, sequence, on)
    return number


def reserve(
    scheme: NumberingScheme, numbers: list[str], *, reason: str = ""
) -> list[NumberReservation]:
    actor = context.actor()
    rows = [
        NumberReservation(scheme=scheme, number=n, reason=reason, reserved_by=actor.id)
        for n in numbers
        if not NumberReservation.objects.filter(scheme=scheme, number=n).exists()
    ]
    return NumberReservation.objects.bulk_create(rows)


def activate(scheme: NumberingScheme, *, effective_from: dt.date | None = None) -> NumberingScheme:
    """Activate a draft version; the previous active version of the same kind is retired."""
    validate_scheme(scheme.pattern, scheme.gap_policy, scheme.allocation)
    with transaction.atomic():
        NumberingScheme.objects.filter(
            branch_id=scheme.branch_id,
            department_id=scheme.department_id,
            applies_to=scheme.applies_to,
            status=ConfigStatus.ACTIVE,
        ).exclude(pk=scheme.pk).update(status=ConfigStatus.RETIRED)
        scheme.status = ConfigStatus.ACTIVE
        scheme.effective_from = effective_from or timezone.now().date()
        scheme.save(update_fields=["status", "effective_from"])
    return scheme


def new_version(scheme: NumberingScheme, **changes: Any) -> NumberingScheme:
    """A scheme that has allocated is immutable: changes create the next version (DRAFT)."""
    latest = (
        NumberingScheme.objects.filter(
            branch_id=scheme.branch_id,
            department_id=scheme.department_id,
            applies_to=scheme.applies_to,
        )
        .order_by("-version")
        .first()
    )
    version = (latest.version if latest else scheme.version) + 1
    fields = {
        "branch_id": scheme.branch_id,
        "department_id": scheme.department_id,
        "applies_to": scheme.applies_to,
        "prefix": scheme.prefix,
        "pattern": scheme.pattern,
        "reset": scheme.reset,
        "gap_policy": scheme.gap_policy,
        "allocation": scheme.allocation,
    }
    fields.update({k: v for k, v in changes.items() if v is not None})
    validate_scheme(str(fields["pattern"]), str(fields["gap_policy"]), str(fields["allocation"]))
    created: NumberingScheme = NumberingScheme.objects.create(
        version=version, status=ConfigStatus.DRAFT, supersedes=scheme, **fields
    )
    return created
