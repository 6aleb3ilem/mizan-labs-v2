"""The permission catalogue (SPEC §9.2): resources, actions, scopes, field groups.

These are system semantics (tier 1). Roles and grants are configuration (tier 2).
"""

from __future__ import annotations

RESOURCES: frozenset[str] = frozenset(
    {
        "tenant", "branch", "department", "user", "role", "numbering_scheme", "vocabulary", "workflow",
        "service_category", "service", "test_definition", "specimen_type", "sieve_set", "price_list",
        "tax_rule", "document_template", "notification_rule", "integration", "account", "contact",
        "project", "task", "work_item", "quote", "quote_revision", "acceptance", "contract", "order",
        "expected_intake", "intake", "specimen", "sample", "test_run", "measurement", "report",
        "invoice", "credit_note", "payment", "treasury_account", "treasury_entry", "equipment",
        "stock", "consumable", "rental", "sale", "outing", "transfer", "maintenance", "vehicle",
        "fleet_document", "phase_template", "work_order", "attachment", "comment", "audit_event",
        "dashboard", "export", "payment_terms_template", "signatory",
    }
)  # fmt: skip

ACTIONS: frozenset[str] = frozenset(
    {
        "view", "create", "edit", "delete", "submit", "approve", "issue", "sign", "cancel", "export",
        "print", "configure", "assign", "reassign", "change_stage", "review_results",
        "override_computed_value", "allocate_payment", "unlock_revision", "impersonate_view",
    }
)  # fmt: skip

SCOPES: tuple[str, ...] = (
    "ALL_BRANCHES",
    "OWN_BRANCH",
    "OWN_DEPARTMENT",
    "ASSIGNED_TO_ME",
    "OWN_RECORDS",
    "OWN_ACCOUNT",
)

# Field groups qualify view/edit (SPEC §9.2).
FIELD_GROUPS: dict[str, frozenset[str]] = {
    "project": frozenset({"commercial", "financial", "client_contact"}),
    "work_item": frozenset({"commercial", "financial", "client_contact"}),
    "task": frozenset({"commercial", "financial", "client_contact"}),
    "order": frozenset({"commercial"}),
    "report": frozenset({"raw_measurements"}),
    "test_run": frozenset({"raw_measurements"}),
    "user": frozenset({"security"}),
    "account": frozenset({"financial", "client_contact"}),
}

CONFIGURATION_RESOURCES: frozenset[str] = frozenset(
    {
        "tenant", "branch", "department", "numbering_scheme", "vocabulary", "workflow",
        "service_category", "service", "test_definition", "specimen_type", "sieve_set", "price_list",
        "tax_rule", "document_template", "notification_rule", "integration", "phase_template",
        "treasury_account", "payment_terms_template", "signatory",
    }
)  # fmt: skip

# Actions whose holders must have MFA enrolled (SPEC §28).
STEP_UP_ACTIONS: frozenset[str] = frozenset({"issue", "sign", "configure", "allocate_payment"})


def validate_grant(resource: str, action: str, scope: str, field_groups: list[str]) -> None:
    if resource not in RESOURCES:
        raise ValueError(f"unknown resource {resource!r}")
    if action not in ACTIONS:
        raise ValueError(f"unknown action {action!r}")
    if scope not in SCOPES:
        raise ValueError(f"unknown scope {scope!r}")
    allowed = FIELD_GROUPS.get(resource, frozenset())
    unknown = [g for g in field_groups if g not in allowed]
    if unknown:
        raise ValueError(f"field groups {unknown} are not defined on {resource!r}")
