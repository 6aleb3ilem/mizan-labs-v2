"""Default role templates (SPEC §9.3, Appendix T). Data, installed per tenant, editable."""

from __future__ import annotations

from dataclasses import dataclass, field

from mizan.apps.identity.models import Grant, Role
from mizan.platform.authz.catalog import CONFIGURATION_RESOURCES, RESOURCES, validate_grant

ALL_BRANCHES, OWN_BRANCH, OWN_DEPARTMENT, ASSIGNED_TO_ME, OWN_ACCOUNT = (
    "ALL_BRANCHES",
    "OWN_BRANCH",
    "OWN_DEPARTMENT",
    "ASSIGNED_TO_ME",
    "OWN_ACCOUNT",
)
VIEW = ("view",)
VCE = ("view", "create", "edit")
VC = ("view", "create")
ALL_ACTIONS = (
    "view",
    "create",
    "edit",
    "delete",
    "submit",
    "approve",
    "issue",
    "cancel",
    "print",
    "export",
)
ASSET_RESOURCES = (
    "equipment", "stock", "consumable", "rental", "sale", "outing", "transfer", "maintenance", "vehicle", "fleet_document",
)  # fmt: skip
LAB_RESOURCES = (
    "expected_intake",
    "intake",
    "specimen",
    "sample",
    "test_run",
    "measurement",
    "report",
)
COMMERCIAL_GROUPS = ("commercial", "financial", "client_contact")


@dataclass(frozen=True)
class GrantSpec:
    resources: tuple[str, ...]
    actions: tuple[str, ...]
    scope: str
    field_groups: tuple[str, ...] = ()


@dataclass(frozen=True)
class RoleTemplate:
    code: str
    labels: dict[str, str]
    grants: tuple[GrantSpec, ...]
    description: str = ""
    extra: dict[str, object] = field(default_factory=dict)


def _g(
    resources: str | tuple[str, ...],
    actions: str | tuple[str, ...],
    scope: str,
    groups: tuple[str, ...] = (),
) -> GrantSpec:
    res = (resources,) if isinstance(resources, str) else resources
    acts = (actions,) if isinstance(actions, str) else actions
    return GrantSpec(res, acts, scope, groups)


COMMERCIAL_GRANTS: tuple[GrantSpec, ...] = (
    _g("account", VCE, OWN_BRANCH, ("client_contact",)),
    _g("contact", VCE, OWN_BRANCH),
    _g(("project", "task", "work_item"), VCE, OWN_BRANCH, COMMERCIAL_GROUPS),
    _g("quote", ("view", "create", "edit", "submit", "print", "export"), OWN_BRANCH),
    _g("quote_revision", ("view", "create", "edit", "print", "export"), OWN_BRANCH),
    _g("acceptance", "create", OWN_BRANCH),
    _g("contract", VC, OWN_BRANCH),
    _g("order", VIEW, OWN_BRANCH, ("commercial",)),
    _g(("invoice", "expected_intake", "intake", "report", "work_order"), VIEW, OWN_BRANCH),
    _g(("attachment", "comment"), VC, OWN_BRANCH),
    _g("dashboard", VIEW, OWN_BRANCH),
)

CLIENT_USER_GRANTS: tuple[GrantSpec, ...] = (
    _g(
        (
            "account",
            "contact",
            "project",
            "task",
            "work_item",
            "quote",
            "quote_revision",
            "contract",
            "order",
            "expected_intake",
            "intake",
            "specimen",
            "sample",
            "test_run",
            "invoice",
            "credit_note",
            "payment",
            "rental",
            "work_order",
            "comment",
        ),
        VIEW,
        OWN_ACCOUNT,
    ),
    _g("project", VIEW, OWN_ACCOUNT, ("financial",)),
    _g("report", ("view", "print"), OWN_ACCOUNT),
    _g("acceptance", "create", OWN_ACCOUNT),
    _g("attachment", VC, OWN_ACCOUNT),
)

DEFAULT_ROLES: tuple[RoleTemplate, ...] = (
    RoleTemplate("COMMERCIAL", {"fr": "Commercial", "en": "Commercial"}, COMMERCIAL_GRANTS),
    RoleTemplate(
        "COMMERCIAL_MANAGER",
        {"fr": "Responsable commercial", "en": "Commercial manager"},
        (
            *COMMERCIAL_GRANTS,
            _g("quote", ("approve", "sign", "cancel"), OWN_BRANCH),
            _g("contract", ("sign", "edit"), OWN_BRANCH),
            _g("order", "edit", OWN_BRANCH, ("commercial",)),
            _g(ASSET_RESOURCES, VIEW, OWN_BRANCH),
        ),
    ),
    RoleTemplate(
        "LAB_RECEPTION",
        {"fr": "Réception laboratoire", "en": "Lab reception"},
        (
            _g(("account", "contact", "project", "order"), VIEW, OWN_BRANCH),
            _g(("task", "work_item"), VC, OWN_BRANCH),
            _g("expected_intake", VIEW, OWN_BRANCH),
            _g("intake", ("view", "create", "edit", "print"), OWN_BRANCH),
            _g(("specimen", "sample"), ("view", "create", "change_stage", "print"), OWN_BRANCH),
            _g(("test_run", "report"), VIEW, OWN_BRANCH),
            _g(("attachment", "comment"), VC, OWN_BRANCH),
        ),
    ),
    RoleTemplate(
        "TECHNICIAN",
        {"fr": "Technicien", "en": "Technician"},
        (
            _g("project", VIEW, OWN_DEPARTMENT),
            _g(("task", "work_item"), VIEW, ASSIGNED_TO_ME),
            _g(("expected_intake", "intake", "report"), VIEW, OWN_DEPARTMENT),
            _g(("specimen", "sample"), ("view", "change_stage"), OWN_DEPARTMENT),
            _g("test_run", ("view", "edit"), ASSIGNED_TO_ME),
            _g("measurement", ("view", "create", "edit"), ASSIGNED_TO_ME),
            _g(("equipment", "stock", "consumable"), VIEW, OWN_DEPARTMENT),
            _g("work_order", VIEW, ASSIGNED_TO_ME),
            _g(("attachment", "comment"), VC, ASSIGNED_TO_ME),
        ),
    ),
    RoleTemplate(
        "LAB_SUPERVISOR",
        {"fr": "Superviseur laboratoire", "en": "Lab supervisor"},
        (
            _g(("account", "contact", "project", "order"), VIEW, OWN_DEPARTMENT),
            _g(("task", "work_item"), VC, OWN_DEPARTMENT),
            _g(("expected_intake", "intake"), ("view", "create", "edit", "print"), OWN_DEPARTMENT),
            _g(
                ("specimen", "sample"),
                ("view", "create", "edit", "change_stage", "print"),
                OWN_DEPARTMENT,
            ),
            _g(
                "test_run",
                (
                    "view",
                    "create",
                    "edit",
                    "assign",
                    "reassign",
                    "cancel",
                    "review_results",
                    "override_computed_value",
                ),
                OWN_DEPARTMENT,
                ("raw_measurements",),
            ),
            _g("measurement", ("view", "create", "edit"), OWN_DEPARTMENT),
            _g(
                "report",
                ("view", "create", "edit", "issue", "print", "export", "cancel"),
                OWN_DEPARTMENT,
                ("raw_measurements",),
            ),
            _g(("equipment", "stock", "consumable"), VIEW, OWN_DEPARTMENT),
            _g("work_order", ("view", "edit"), OWN_DEPARTMENT),
            _g(("attachment", "comment"), VC, OWN_DEPARTMENT),
            _g("dashboard", VIEW, OWN_DEPARTMENT),
        ),
    ),
    RoleTemplate(
        "FINANCE",
        {"fr": "Finance", "en": "Finance"},
        (
            _g("account", VIEW, OWN_BRANCH, ("financial",)),
            _g("contact", VIEW, OWN_BRANCH),
            _g(("project", "task", "work_item"), VIEW, OWN_BRANCH, ("financial",)),
            _g(("quote", "quote_revision", "contract", "order"), VIEW, OWN_BRANCH),
            _g(
                ("invoice", "credit_note"),
                ("view", "create", "edit", "issue", "cancel", "print", "export"),
                OWN_BRANCH,
            ),
            _g("payment", ("view", "create", "allocate_payment", "cancel", "print"), OWN_BRANCH),
            _g(("treasury_account", "treasury_entry"), VCE, OWN_BRANCH),
            _g(ASSET_RESOURCES, VIEW, OWN_BRANCH),
            _g(("attachment", "comment"), VC, OWN_BRANCH),
            _g("dashboard", VIEW, OWN_BRANCH),
        ),
    ),
    RoleTemplate(
        "ASSETS",
        {"fr": "Matériel et stocks", "en": "Assets"},
        (
            _g(("account", "contact", "project", "task", "work_item", "order"), VIEW, OWN_BRANCH),
            _g(ASSET_RESOURCES, ALL_ACTIONS, OWN_BRANCH),
            _g(("attachment", "comment"), VC, OWN_BRANCH),
            _g("dashboard", VIEW, OWN_BRANCH),
        ),
    ),
    RoleTemplate(
        "BRANCH_MANAGER",
        {"fr": "Responsable d'agence", "en": "Branch manager"},
        (
            _g(tuple(sorted(RESOURCES - {"tenant"})), VIEW, OWN_BRANCH),
            _g(("project", "task", "work_item"), VIEW, OWN_BRANCH, COMMERCIAL_GROUPS),
            _g("account", VIEW, OWN_BRANCH, ("financial", "client_contact")),
            _g(("report", "test_run"), VIEW, OWN_BRANCH, ("raw_measurements",)),
            _g("project", "edit", OWN_BRANCH, COMMERCIAL_GROUPS),
            _g(
                ("quote", "contract", "report", "invoice"), ("approve", "sign", "issue"), OWN_BRANCH
            ),
            _g(("rental", "transfer"), "approve", OWN_BRANCH),
            _g("work_order", "edit", OWN_BRANCH),
            _g(("attachment", "comment"), VC, OWN_BRANCH),
            _g("dashboard", VIEW, OWN_BRANCH),
            _g("export", "export", OWN_BRANCH),
        ),
    ),
    RoleTemplate(
        "TENANT_ADMIN",
        {"fr": "Administrateur", "en": "Tenant administrator"},
        (
            _g(
                tuple(sorted(CONFIGURATION_RESOURCES)),
                ("view", "create", "edit", "configure"),
                ALL_BRANCHES,
            ),
            _g(
                "user",
                ("view", "create", "edit", "delete", "configure"),
                ALL_BRANCHES,
                ("security",),
            ),
            _g("role", ("view", "create", "edit", "delete", "configure"), ALL_BRANCHES),
            _g("user", "impersonate_view", ALL_BRANCHES),
            _g("contact", VCE, ALL_BRANCHES),
            _g("audit_event", VIEW, ALL_BRANCHES),
            _g("dashboard", VIEW, ALL_BRANCHES),
            _g("export", "export", ALL_BRANCHES),
        ),
    ),
    RoleTemplate(
        "CLIENT_USER", {"fr": "Utilisateur client", "en": "Client user"}, CLIENT_USER_GRANTS
    ),
    RoleTemplate(
        "CLIENT_ADMIN",
        {"fr": "Administrateur client", "en": "Client admin"},
        (
            *CLIENT_USER_GRANTS,
            _g("contact", ("create", "edit"), OWN_ACCOUNT),
            _g("user", VCE, OWN_ACCOUNT),
        ),
    ),
)


def expand(template: RoleTemplate) -> list[tuple[str, str, str, list[str]]]:
    """Flatten a template into unique (resource, action, scope, field_groups) rows."""
    rows: dict[tuple[str, str, str], set[str]] = {}
    for spec in template.grants:
        for resource in spec.resources:
            for action in spec.actions:
                validate_grant(resource, action, spec.scope, list(spec.field_groups))
                rows.setdefault((resource, action, spec.scope), set()).update(spec.field_groups)
    return [(r, a, s, sorted(g)) for (r, a, s), g in sorted(rows.items())]


def install_default_roles() -> dict[str, Role]:
    """Create (or refresh) the template roles of the active tenant. Idempotent."""
    roles: dict[str, Role] = {}
    for template in DEFAULT_ROLES:
        role, _ = Role.objects.get_or_create(
            code=template.code, defaults={"is_template": True, "description": template.description}
        )
        role.set_labels(template.labels)
        existing = {(g.resource, g.action, g.scope): g for g in role.grants.all()}
        wanted = expand(template)
        for resource, action, scope, groups in wanted:
            grant = existing.pop((resource, action, scope), None)
            if grant is None:
                Grant.objects.create(
                    role=role, resource=resource, action=action, scope=scope, field_groups=groups
                )
            elif sorted(grant.field_groups or []) != groups:
                grant.field_groups = groups
                grant.save(update_fields=["field_groups"])
        for stale in existing.values():
            stale.delete()
        roles[template.code] = role
    return roles
