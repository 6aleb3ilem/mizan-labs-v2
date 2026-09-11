"""Default numbering schemes of a new branch (SPEC Appendix E)."""

from __future__ import annotations

from typing import Any

from mizan.apps.config.models import (
    Allocation,
    ConfigStatus,
    GapPolicy,
    NumberingReset,
    NumberingScheme,
)

# applies_to, pattern, reset, gap_policy, allocation
DEFAULT_SCHEMES: tuple[tuple[str, str, str, str, str], ...] = (
    ("ACCOUNT", "CL-{SEQ:5}", NumberingReset.NEVER, GapPolicy.TOLERANT, Allocation.ON_CREATE),
    (
        "PROJECT",
        "AF-{YYYY}-{SEQ:4}",
        NumberingReset.YEARLY,
        GapPolicy.TOLERANT,
        Allocation.ON_CREATE,
    ),
    (
        "QUOTE",
        "DV-{BRANCH}-{YYYY}-{SEQ:4}",
        NumberingReset.YEARLY,
        GapPolicy.TOLERANT,
        Allocation.ON_ISSUE,
    ),
    ("ORDER", "CM-{YYYY}-{SEQ:4}", NumberingReset.YEARLY, GapPolicy.TOLERANT, Allocation.ON_CREATE),
    (
        "CONTRACT",
        "CT-{YYYY}-{SEQ:3}",
        NumberingReset.YEARLY,
        GapPolicy.TOLERANT,
        Allocation.ON_CREATE,
    ),
    ("INTAKE", "RC-{YY}-{SEQ:4}", NumberingReset.YEARLY, GapPolicy.TOLERANT, Allocation.ON_CREATE),
    ("SAMPLE", "EC-{YY}-{SEQ:5}", NumberingReset.YEARLY, GapPolicy.TOLERANT, Allocation.ON_CREATE),
    (
        "TEST_RUN",
        "ES-{YY}-{SEQ:5}",
        NumberingReset.YEARLY,
        GapPolicy.TOLERANT,
        Allocation.ON_CREATE,
    ),
    (
        "REPORT",
        "PV-{BRANCH}-{YYYY}-{SEQ:4}",
        NumberingReset.YEARLY,
        GapPolicy.TOLERANT,
        Allocation.ON_ISSUE,
    ),
    (
        "INVOICE",
        "FA-{YYYY}-{SEQ:5}",
        NumberingReset.YEARLY,
        GapPolicy.GAP_FREE,
        Allocation.ON_ISSUE,
    ),
    (
        "CREDIT_NOTE",
        "AV-{YYYY}-{SEQ:4}",
        NumberingReset.YEARLY,
        GapPolicy.GAP_FREE,
        Allocation.ON_ISSUE,
    ),
    (
        "PAYMENT",
        "PA-{YYYY}-{SEQ:5}",
        NumberingReset.YEARLY,
        GapPolicy.TOLERANT,
        Allocation.ON_CREATE,
    ),
    ("RENTAL", "LO-{YY}-{SEQ:4}", NumberingReset.YEARLY, GapPolicy.TOLERANT, Allocation.ON_CREATE),
    ("SALE", "VE-{YY}-{SEQ:4}", NumberingReset.YEARLY, GapPolicy.TOLERANT, Allocation.ON_CREATE),
    ("OUTING", "BS-{YY}-{SEQ:4}", NumberingReset.YEARLY, GapPolicy.TOLERANT, Allocation.ON_CREATE),
    (
        "TRANSFER",
        "TR-{YY}-{SEQ:4}",
        NumberingReset.YEARLY,
        GapPolicy.TOLERANT,
        Allocation.ON_CREATE,
    ),
    (
        "WORK_ORDER",
        "OT-{YY}-{SEQ:4}",
        NumberingReset.YEARLY,
        GapPolicy.TOLERANT,
        Allocation.ON_CREATE,
    ),
    ("EQUIPMENT", "EQ-{SEQ:4}", NumberingReset.NEVER, GapPolicy.TOLERANT, Allocation.ON_CREATE),
    (
        "MAINTENANCE",
        "MT-{YY}-{SEQ:4}",
        NumberingReset.YEARLY,
        GapPolicy.TOLERANT,
        Allocation.ON_CREATE,
    ),
)


def install_default_numbering(branch: Any) -> list[NumberingScheme]:
    created: list[NumberingScheme] = []
    for applies_to, pattern, reset, gap_policy, allocation in DEFAULT_SCHEMES:
        scheme, was_created = NumberingScheme.objects.get_or_create(
            branch=branch,
            department=None,
            applies_to=applies_to,
            version=1,
            defaults={
                "pattern": pattern,
                "reset": reset,
                "gap_policy": gap_policy,
                "allocation": allocation,
                "status": ConfigStatus.ACTIVE,
            },
        )
        if was_created:
            created.append(scheme)
    return created
