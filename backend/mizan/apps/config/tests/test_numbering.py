"""SPEC §10.1: patterns, resets, previews, atomic gap-free allocation, reservations, versions."""

from __future__ import annotations

import datetime as dt
import threading
from typing import Any

import pytest
from django.db import connection

from mizan.apps.config import numbering
from mizan.apps.config.defaults.numbering import install_default_numbering
from mizan.apps.config.models import ConfigStatus, NumberingScheme
from mizan.platform.api.errors import Conflict, NotFound, UnprocessableEntity
from mizan.platform.db.tenancy import tenant_scope

pytestmark = pytest.mark.django_db


def test_format_and_period_keys() -> None:
    on = dt.date(2026, 9, 11)
    assert (
        numbering.format_number(
            "DV-{BRANCH}-{YYYY}-{SEQ:4}", branch_code="NKC", on=on, sequence=187
        )
        == "DV-NKC-2026-0187"
    )
    assert (
        numbering.format_number("{PREFIX}{SEQ:4}-{YY}", prefix="F", on=on, sequence=12)
        == "F0012-26"
    )
    assert (
        numbering.format_number("{DEPT}/{MM}/{SEQ}", department_code="BET", on=on, sequence=7)
        == "BET/09/7"
    )
    assert numbering.period_key("NEVER", on) == ""
    assert numbering.period_key("YEARLY", on) == "2026"
    assert numbering.period_key("MONTHLY", on) == "2026-09"


def test_pattern_validation() -> None:
    numbering.validate_scheme("DV-{SEQ:4}", "TOLERANT", "ON_CREATE")
    with pytest.raises(UnprocessableEntity):
        numbering.validate_scheme("DV-2026", "TOLERANT", "ON_CREATE")  # no sequence
    with pytest.raises(UnprocessableEntity):
        numbering.validate_scheme("{SEQ:4}-{SEQ:2}", "TOLERANT", "ON_CREATE")
    with pytest.raises(UnprocessableEntity):
        numbering.validate_scheme("{BRANCH}-{WEEK}-{SEQ:4}", "TOLERANT", "ON_CREATE")
    with pytest.raises(UnprocessableEntity):
        numbering.validate_scheme(
            "FA-{SEQ:5}", "GAP_FREE", "ON_CREATE"
        )  # gap-free must allocate on issue


def test_allocation_preview_reset_and_reservations(branch: Any) -> None:
    install_default_numbering(branch)
    scheme = numbering.active_scheme("QUOTE", branch.id)
    assert numbering.preview(scheme, on=dt.date(2026, 9, 11)) == "DV-NKC-2026-0001"
    first = numbering.allocate(scheme, on=dt.date(2026, 9, 11))
    assert first.number == "DV-NKC-2026-0001"
    assert numbering.preview(scheme, on=dt.date(2026, 9, 11)) == "DV-NKC-2026-0002"
    numbering.reserve(scheme, ["DV-NKC-2026-0002", "DV-NKC-2026-0003"], reason="V1 series")
    assert numbering.preview(scheme, on=dt.date(2026, 9, 11)) == "DV-NKC-2026-0004"
    assert numbering.allocate(scheme, on=dt.date(2026, 9, 11)).number == "DV-NKC-2026-0004"
    # yearly reset: a new year starts at 1 again
    assert numbering.allocate(scheme, on=dt.date(2027, 1, 4)).number == "DV-NKC-2027-0001"
    scheme.refresh_from_db()
    assert scheme.immutable is True


def test_department_specific_scheme_wins(branch: Any, department: Any) -> None:
    install_default_numbering(branch)
    specific = NumberingScheme.objects.create(
        branch=branch,
        department=department,
        applies_to="TEST_RUN",
        pattern="{DEPT}-{YY}-{SEQ:3}",
        status=ConfigStatus.ACTIVE,
    )
    assert numbering.active_scheme("TEST_RUN", branch.id, department.id) == specific
    assert numbering.active_scheme("TEST_RUN", branch.id).department_id is None
    assert numbering.allocate(specific, on=dt.date(2026, 9, 11)).number == "CONCRETE-26-001"
    with pytest.raises(NotFound):
        numbering.active_scheme("EQUIPMENT", branch.id) if False else numbering.active_scheme(
            "NOPE", branch.id
        )


def test_versions_activation_and_immutability(branch: Any) -> None:
    install_default_numbering(branch)
    scheme = numbering.active_scheme("INVOICE", branch.id)
    numbering.allocate(scheme, on=dt.date(2026, 9, 11))
    draft = numbering.new_version(scheme, pattern="FA-{BRANCH}-{YYYY}-{SEQ:5}")
    assert draft.version == 2 and draft.status == "DRAFT" and draft.supersedes == scheme
    with pytest.raises(Conflict):
        numbering.allocate(draft)  # drafts never allocate
    numbering.activate(draft)
    scheme.refresh_from_db()
    assert scheme.status == "RETIRED"
    assert numbering.active_scheme("INVOICE", branch.id) == draft
    assert numbering.preview(draft, on=dt.date(2026, 9, 11)) == "FA-NKC-2026-00001"
    assert numbering.draft_number(draft.id).startswith("DRAFT-")


@pytest.mark.django_db(transaction=True)
def test_concurrent_allocation_is_gap_free_and_unique(db: Any) -> None:
    from mizan.apps.org.models import Branch, Tenant
    from mizan.platform.db.tenancy import platform_scope

    with platform_scope():
        tenant = Tenant.objects.create(code="CONC", name="Concurrency")
    with tenant_scope(tenant.id):
        branch = Branch.objects.create(code="NKC", legal_name="NKC", currency="MRU")
        install_default_numbering(branch)
        scheme_id = numbering.active_scheme("INVOICE", branch.id).id
    results: list[str] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def worker() -> None:
        try:
            with tenant_scope(tenant.id):
                scheme = NumberingScheme.objects.get(pk=scheme_id)
                mine = [
                    numbering.allocate(scheme, on=dt.date(2026, 9, 11)).number for _ in range(20)
                ]
            with lock:
                results.extend(mine)
        except BaseException as exc:
            errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, errors
    assert len(results) == 160
    assert len(set(results)) == 160
    assert sorted(results) == [f"FA-2026-{i:05d}" for i in range(1, 161)]
