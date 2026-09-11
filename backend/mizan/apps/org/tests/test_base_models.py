from __future__ import annotations

import pytest

from mizan.apps.org.models import Branch, Department
from mizan.platform.db.models import ConcurrentUpdate
from mizan.platform.labels import get_labels, labels_for

pytestmark = pytest.mark.django_db


def test_row_version_protects_against_lost_updates(branch: Branch) -> None:
    first = Branch.objects.get(pk=branch.pk)
    second = Branch.objects.get(pk=branch.pk)
    first.legal_name = "First writer"
    first.save()
    assert first.row_version == 2
    second.legal_name = "Second writer"
    with pytest.raises(ConcurrentUpdate):
        second.save()
    assert Branch.objects.get(pk=branch.pk).legal_name == "First writer"


def test_update_fields_are_honoured(branch: Branch) -> None:
    branch.phone = "+222 45 00 00 00"
    branch.legal_name = "not saved"
    branch.save(update_fields=["phone"])
    fresh = Branch.objects.get(pk=branch.pk)
    assert fresh.phone == "+222 45 00 00 00"
    assert fresh.legal_name == "Mizan Labs Nouakchott"
    assert fresh.row_version == 2


def test_soft_delete_hides_rows_from_the_default_manager(branch: Branch) -> None:
    department = Department.objects.create(branch=branch, code="SOILS")
    department.soft_delete("created by mistake")
    assert not Department.objects.filter(pk=department.pk).exists()
    assert Department.all_objects.get(pk=department.pk).deleted_reason == "created by mistake"


def test_labels_are_stored_per_locale_and_batch_loaded(branch: Branch) -> None:
    concrete = Department.objects.create(branch=branch, code="CONCRETE")
    soils = Department.objects.create(branch=branch, code="SOILS")
    concrete.set_labels({"fr": "Béton", "en": "Concrete"})
    soils.set_labels({"fr": "Sols & granulats", "en": "Soils & aggregates"})
    assert get_labels("department", concrete.pk) == {"fr": "Béton", "en": "Concrete"}
    assert Department.objects.get(pk=soils.pk).label("en") == "Soils & aggregates"
    assert Department.objects.get(pk=soils.pk).label("de") == "Sols & granulats"
    found = labels_for("department", [concrete.pk, soils.pk])
    assert found[concrete.pk]["fr"] == "Béton"
    rows = list(Department.objects.all())
    Department.attach_labels(rows)
    assert {r.code: r.labels["en"] for r in rows} == {
        "CONCRETE": "Concrete",
        "SOILS": "Soils & aggregates",
    }
