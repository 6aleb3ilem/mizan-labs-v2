"""The seed produces a usable tenant (SPEC Appendix R step 14) and is idempotent."""

from __future__ import annotations

from typing import Any

import pytest
from django.core.management import call_command
from django.test import Client

from mizan.platform.db.tenancy import platform_scope, tenant_scope

pytestmark = pytest.mark.django_db


def test_seed_demo_is_complete_and_idempotent() -> None:
    from mizan.apps.config.models import Service, TestDefinition, Workflow
    from mizan.apps.identity.models import Membership, User
    from mizan.apps.notify.models import NotificationRule
    from mizan.apps.org.models import Branch, Signatory, Tenant

    call_command("seed_demo", "--tenant-code", "DEMO", verbosity=0)
    call_command("seed_demo", "--tenant-code", "DEMO", verbosity=0)  # second run: no duplicates
    with platform_scope():
        tenant = Tenant.objects.get(code="DEMO")
        assert Tenant.objects.filter(code="DEMO").count() == 1
    with tenant_scope(tenant.id):
        assert Branch.objects.filter(code="NKC").count() == 1
        assert {d.code for d in TestDefinition.objects.all()} == {
            "CONCRETE_COMPRESSION",
            "BLOCK_COMPRESSION",
            "SIEVE_ANALYSIS",
            "WATER_CONTENT",
        }
        assert TestDefinition.objects.filter(status="ACTIVE").count() == 4
        assert Service.objects.count() == 6
        assert Workflow.objects.filter(status="ACTIVE").count() >= 10
        assert NotificationRule.objects.count() == 10
        assert Signatory.objects.get(
            display_name="Direction du laboratoire"
        ).signature_image_key.endswith("placeholder.png")
        assert User.objects.filter(email="sidi@demo.mizanlabs.dev").count() == 1
        assert Membership.objects.filter(user__email="sidi@demo.mizanlabs.dev").count() == 1

    # the demo administrator can sign in and sees the configuration
    login = Client().post(
        "/api/v1/auth/login",
        data={
            "email": "admin@demo.mizanlabs.dev",
            "password": "Demo-Passw0rd!",
            "tenant_code": "DEMO",
        },
        content_type="application/json",
    )
    assert login.status_code == 200, login.content
    api = Client(HTTP_AUTHORIZATION=f"Bearer {login.json()['access_token']}")
    assert [b["code"] for b in api.get("/api/v1/branches").json()] == ["NKC"]
    definitions: list[dict[str, Any]] = api.get("/api/v1/test-definitions").json()
    assert {d["code"] for d in definitions} == {
        "CONCRETE_COMPRESSION",
        "BLOCK_COMPRESSION",
        "SIEVE_ANALYSIS",
        "WATER_CONTENT",
    }
    assert api.get("/api/v1/notification-rules").status_code == 200


def test_block_compression_definition_evaluates() -> None:
    from decimal import Decimal

    from mizan.apps.config.defaults.test_definitions import BLOCK_COMPRESSION
    from mizan.platform.formula.engine import (
        RunData,
        Subject,
        evaluate_definition,
        validate_definition_formulas,
    )

    assert validate_definition_formulas(BLOCK_COMPRESSION) == []
    hollow = {"shape": "BLOCK", "L": 40, "W": 20, "H": 20, "net_factor": 0.55}
    data = RunData(
        subjects=[
            Subject(
                id=str(i),
                inputs={
                    "weight_kg": 14.2,
                    "load_kgf": load,
                    "gross_area_cm2": 800,
                    "net_area_cm2": 440,
                },
                properties=hollow,
            )
            for i, load in enumerate([26400, 27500, 26000])
        ]
    )
    result = evaluate_definition(BLOCK_COMPRESSION, data)
    assert not result.blocked
    assert data.subjects[0].computed["net_kgcm2"] == 60.0
    assert data.subjects[0].computed["stress_mpa"] == 6.0
    assert result.aggregates["mean_mpa"] == Decimal("6.1")
