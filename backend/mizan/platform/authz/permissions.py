"""Effective permissions: grants bound to memberships, turned into query predicates.

A grant is (resource, action, scope, field_groups); a binding is a grant attached to the
branch/department/account of one membership. The union of a user's bindings decides
``allows``; ``predicate`` produces the ``Q`` object injected into repository queries.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field

from django.db.models import Model, Q


@dataclass(frozen=True, slots=True)
class GrantBinding:
    resource: str
    action: str
    scope: str
    field_groups: frozenset[str] = frozenset()
    role_code: str = ""
    membership_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None  # None with OWN_BRANCH means every branch of the tenant
    department_id: uuid.UUID | None = None
    account_id: uuid.UUID | None = None
    project_ids: tuple[uuid.UUID, ...] = ()


@dataclass(frozen=True, slots=True)
class ScopeFields:
    """Field names a scope predicate uses on a given model; absent fields are skipped."""

    branch: str = "branch_id"
    department: str = "department_id"
    assignee: str = "assigned_user_id"
    owner: str = "created_by"
    account: str = "account_id"
    project: str = "project_id"


DEFAULT_SCOPE_FIELDS = ScopeFields()


def _has_field(model: type[Model] | None, name: str) -> bool:
    if model is None:
        return True
    names = set()
    for f in model._meta.get_fields():
        names.add(f.name)
        attname = getattr(f, "attname", None)
        if attname:
            names.add(attname)
    return name in names


@dataclass(slots=True)
class EffectivePermissions:
    user_id: uuid.UUID
    tenant_id: uuid.UUID | None
    bindings: list[GrantBinding] = field(default_factory=list)
    is_platform_operator: bool = False

    def bindings_for(self, resource: str, action: str) -> list[GrantBinding]:
        return [b for b in self.bindings if b.resource == resource and b.action == action]

    def allows(self, resource: str, action: str, *, branch_id: uuid.UUID | None = None) -> bool:
        for binding in self.bindings_for(resource, action):
            if (
                branch_id is None
                or binding.scope == "ALL_BRANCHES"
                or binding.branch_id in (None, branch_id)
            ):
                return True
        return False

    def field_groups(self, resource: str, action: str = "view") -> frozenset[str]:
        groups: set[str] = set()
        for binding in self.bindings_for(resource, action):
            groups |= binding.field_groups
        return frozenset(groups)

    def branch_ids(self, resource: str, action: str) -> set[uuid.UUID] | None:
        """Branches reachable for (resource, action); ``None`` means all branches."""
        result: set[uuid.UUID] = set()
        for binding in self.bindings_for(resource, action):
            if binding.scope == "ALL_BRANCHES" or binding.branch_id is None:
                return None
            result.add(binding.branch_id)
        return result

    def predicate(
        self,
        resource: str,
        action: str,
        *,
        model: type[Model] | None = None,
        fields: ScopeFields = DEFAULT_SCOPE_FIELDS,
        branch_id: uuid.UUID | None = None,
    ) -> Q:
        """The row filter for (resource, action); ``Q(pk__in=[])`` when nothing is allowed."""
        clauses: list[Q] = []
        for binding in self.bindings_for(resource, action):
            clause = self._clause(binding, model, fields)
            if clause is None:
                continue
            clauses.append(clause)
        if not clauses:
            return Q(pk__in=[])
        combined = clauses[0]
        for clause in clauses[1:]:
            combined |= clause
        if branch_id is not None and _has_field(model, fields.branch):
            combined &= Q(**{fields.branch: branch_id})
        return combined

    def _clause(
        self, binding: GrantBinding, model: type[Model] | None, fields: ScopeFields
    ) -> Q | None:
        scope = binding.scope
        branch_clause = Q()
        if binding.branch_id is not None and _has_field(model, fields.branch):
            branch_clause = Q(**{fields.branch: binding.branch_id})
        if scope == "ALL_BRANCHES":
            return Q()
        if scope == "OWN_BRANCH":
            return branch_clause
        if scope == "OWN_DEPARTMENT":
            if binding.department_id is not None and _has_field(model, fields.department):
                return branch_clause & Q(**{fields.department: binding.department_id})
            return branch_clause  # models without a department fall back to the branch
        if scope == "ASSIGNED_TO_ME":
            if _has_field(model, fields.assignee):
                return branch_clause & Q(**{fields.assignee: self.user_id})
            return (
                branch_clause & Q(**{fields.owner: self.user_id})
                if _has_field(model, fields.owner)
                else None
            )
        if scope == "OWN_RECORDS":
            if _has_field(model, fields.owner):
                return branch_clause & Q(**{fields.owner: self.user_id})
            return None
        if scope == "OWN_ACCOUNT":
            if binding.account_id is None or not _has_field(model, fields.account):
                return None
            clause = Q(**{fields.account: binding.account_id})
            if binding.project_ids and _has_field(model, fields.project):
                clause &= Q(**{f"{fields.project}__in": list(binding.project_ids)})
            return clause
        return None

    @classmethod
    def for_platform_operator(cls, user_id: uuid.UUID) -> EffectivePermissions:
        bindings = [
            GrantBinding(
                resource="tenant", action=action, scope="ALL_BRANCHES", role_code="PLATFORM"
            )
            for action in ("view", "create", "edit", "configure")
        ]
        return cls(user_id=user_id, tenant_id=None, bindings=bindings, is_platform_operator=True)

    def summary(self) -> list[dict[str, object]]:
        """Serialisable form for ``GET /me/permissions``."""
        return [
            {
                "resource": b.resource,
                "action": b.action,
                "scope": b.scope,
                "field_groups": sorted(b.field_groups),
                "role": b.role_code,
                "membership_id": b.membership_id,
                "branch_id": b.branch_id,
                "department_id": b.department_id,
                "account_id": b.account_id,
            }
            for b in self.bindings
        ]


def merge(perms: Iterable[EffectivePermissions]) -> list[GrantBinding]:
    result: list[GrantBinding] = []
    for p in perms:
        result.extend(p.bindings)
    return result
