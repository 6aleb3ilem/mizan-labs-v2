"""Workflow engine (SPEC §10.3): admin-defined states with system semantics, guards, effects.

Code evaluates ``state.semantic``, never codes or labels. Guards and effects are looked up
by code in registries that the owning apps populate; unknown codes fail validation, and a
known-but-unimplemented code fails closed at transition time.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from django.db import models, transaction
from django.utils import timezone

from mizan.apps.audit import services as audit
from mizan.apps.config.models import ConfigStatus, Workflow, WorkflowState, WorkflowTransition
from mizan.platform import context
from mizan.platform.api.errors import ApiError, Conflict, NotFound, UnprocessableEntity
from mizan.platform.authz.permissions import EffectivePermissions

SEMANTICS: dict[str, tuple[str, ...]] = {
    "PROJECT": ("OPEN", "ON_HOLD", "CLOSED", "CANCELLED"),
    "ACCOUNT": ("ACTIVE", "INACTIVE", "BLOCKED"),
    "QUOTE": ("DRAFT", "PENDING_APPROVAL", "SENT", "NEGOTIATING", "ACCEPTED", "REFUSED", "SUSPENDED", "EXPIRED", "CANCELLED"),
    "CONTRACT": ("DRAFT", "SENT_FOR_SIGNATURE", "SIGNED", "CANCELLED"),
    "ORDER": ("OPEN", "AMENDED", "COMPLETED", "CANCELLED"),
    "INTAKE": ("REGISTERED", "PARTIALLY_PROCESSED", "PROCESSED", "CANCELLED"),
    "TEST_RUN": ("SCHEDULED", "IN_PROGRESS", "MEASURED", "UNDER_REVIEW", "VALIDATED", "REPORTED", "CANCELLED"),
    "REPORT": ("DRAFT", "ISSUED", "SUPERSEDED", "REVOKED"),
    "INVOICE": ("DRAFT", "ISSUED", "CANCELLED"),
    "PAYMENT": ("RECORDED", "REVERSED"),
    "RENTAL": ("RESERVED", "ACTIVE", "RETURNED", "LATE", "CLOSED", "CANCELLED"),
    "SALE": ("RESERVED", "DELIVERED", "CANCELLED"),
    "OUTING": ("OPEN", "PARTIALLY_RETURNED", "CLOSED"),
    "TRANSFER": ("DRAFT", "VALIDATED", "IN_TRANSIT", "RECEIVED", "CANCELLED"),
    "MAINTENANCE": ("PLANNED", "IN_PROGRESS", "DONE", "CANCELLED"),
    "WORK_ORDER": ("PLANNED", "IN_PROGRESS", "LATE", "COMPLETED", "CANCELLED"),
    "PHASE": ("PENDING", "IN_PROGRESS", "COMPLETED"),
}  # fmt: skip

KNOWN_GUARDS: frozenset[str] = frozenset(
    {
        "has_billable_lines", "totals_computed", "discount_within_threshold", "acceptance_evidence_attached",
        "actor_is_not_entrant", "all_runs_of_intake_reported", "all_measurements_present", "no_rule_blocking",
        "stock_available", "no_open_children", "signatory_authorised", "invoice_has_lines", "payment_fully_allocated",
        "reason_required", "all_runs_validated", "validity_elapsed", "condition_recorded", "penalties_settled",
        "assigned_or_can_assign",
    }
)  # fmt: skip
KNOWN_EFFECTS: frozenset[str] = frozenset(
    {
        "freeze_revision", "create_next_revision_on_edit", "create_order", "provision_work", "notify",
        "make_milestone_invoiceable", "reserve_stock", "release_stock", "request_signature", "issue_document",
        "increment_delivered", "decrement_delivered", "close_parent_if_complete", "allocate_number", "emit",
        "release_specimens", "stock_movement", "compute_penalty", "update_document_status",
    }
)  # fmt: skip

SYSTEM_ACTION = "system"
EFFECT_RE = re.compile(r"^([a-z_]+)(?:\((.*)\))?$")


class TransitionError(ApiError):
    status = 409
    code = "workflow_transition_denied"
    message_key = "workflow.transition_denied"


class GuardFailed(ApiError):
    status = 409
    code = "workflow_guard_failed"
    message_key = "workflow.guard_failed"


@dataclass(slots=True)
class TransitionContext:
    record: Any
    workflow: Workflow
    transition: WorkflowTransition
    from_state: WorkflowState | None
    to_state: WorkflowState
    actor: context.Actor
    params: dict[str, Any] = field(default_factory=dict)
    permissions: EffectivePermissions | None = None
    results: dict[str, Any] = field(default_factory=dict)


GuardFunc = Callable[[TransitionContext], bool | str]
EffectFunc = Callable[[TransitionContext, dict[str, Any]], None]
GUARDS: dict[str, GuardFunc] = {}
EFFECTS: dict[str, EffectFunc] = {}


def register_guard(code: str) -> Callable[[GuardFunc], GuardFunc]:
    def decorator(func: GuardFunc) -> GuardFunc:
        GUARDS[code] = func
        return func

    return decorator


def register_effect(code: str) -> Callable[[EffectFunc], EffectFunc]:
    def decorator(func: EffectFunc) -> EffectFunc:
        EFFECTS[code] = func
        return func

    return decorator


def parse_spec(spec: Any) -> tuple[str, dict[str, Any]]:
    """``"notify(client_quote_sent)"`` → ``("notify", {"arg": "client_quote_sent"})``; dicts pass through."""
    if isinstance(spec, dict):
        return str(spec.get("code", "")), dict(spec.get("params") or {})
    match = EFFECT_RE.match(str(spec).strip())
    if not match:
        return str(spec), {}
    code, arg = match.group(1), match.group(2)
    return code, ({"arg": arg.strip().strip("'\"")} if arg else {})


class StatefulModel(models.Model):
    """Mixin for lifecycle records: the admin-defined state plus who entered it and when."""

    workflow_kind: str = ""

    state = models.ForeignKey(WorkflowState, on_delete=models.PROTECT, related_name="+")
    state_entered_at = models.DateTimeField(default=timezone.now)
    state_entered_by = models.UUIDField(null=True, blank=True)

    class Meta:
        abstract = True

    @property
    def semantic(self) -> str:
        return str(self.state.semantic)


# --- lookup --------------------------------------------------------------------------------------


def get_active_workflow(kind: str, branch_id: uuid.UUID | None = None) -> Workflow:
    qs = Workflow.objects.filter(kind=kind, status=ConfigStatus.ACTIVE)
    if branch_id is not None:
        specific: Workflow | None = qs.filter(branch_id=branch_id).order_by("-version").first()
        if specific is not None:
            return specific
    workflow: Workflow | None = qs.filter(branch__isnull=True).order_by("-version").first()
    if workflow is None:
        raise NotFound("workflow.no_active_workflow", params={"kind": kind})
    return workflow


def initial_state(workflow: Workflow) -> WorkflowState:
    state = workflow.states.filter(is_initial=True).order_by("ord").first()
    if state is None:
        raise Conflict("workflow.no_initial_state", code="workflow_no_initial_state")
    return state


def state_for_semantic(workflow: Workflow, semantic: str) -> WorkflowState:
    state = workflow.states.filter(semantic=semantic).order_by("ord").first()
    if state is None:
        raise NotFound("workflow.semantic_missing", params={"semantic": semantic})
    return state


def available_transitions(record: StatefulModel) -> list[WorkflowTransition]:
    current = record.state
    if current.is_terminal:
        return []
    return list(
        WorkflowTransition.objects.filter(workflow_id=current.workflow_id)
        .filter(models.Q(from_state=current) | models.Q(from_state__isnull=True))
        .exclude(to_state=current)
        .select_related("to_state", "from_state")
        .order_by("ord")
    )


# --- validation ----------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Problem:
    message_key: str
    params: dict[str, Any]


def validate_workflow(workflow: Workflow) -> list[Problem]:
    problems: list[Problem] = []
    semantics = SEMANTICS.get(workflow.kind)
    if semantics is None:
        return [Problem("workflow.unknown_kind", {"kind": workflow.kind})]
    states = list(workflow.states.all())
    seen: set[str] = set()
    for state in states:
        if state.semantic not in semantics:
            problems.append(
                Problem(
                    "workflow.unknown_semantic", {"state": state.code, "semantic": state.semantic}
                )
            )
        seen.add(state.semantic)
    for semantic in semantics:
        if semantic not in seen:
            problems.append(Problem("workflow.semantic_missing", {"semantic": semantic}))
    initial = [s for s in states if s.is_initial]
    if len(initial) != 1:
        problems.append(Problem("workflow.one_initial_state_required", {"count": len(initial)}))
    state_ids = {s.id for s in states}
    for transition in workflow.transitions.all():
        if transition.to_state_id not in state_ids or (
            transition.from_state_id is not None and transition.from_state_id not in state_ids
        ):
            problems.append(
                Problem("workflow.transition_state_unknown", {"transition": str(transition.id)})
            )
        for guard in transition.guards or []:
            code, _ = parse_spec(guard)
            if code.removeprefix("not ") not in KNOWN_GUARDS:
                problems.append(Problem("workflow.unknown_guard", {"guard": code}))
        for effect in transition.effects or []:
            code, _ = parse_spec(effect)
            if code not in KNOWN_EFFECTS:
                problems.append(Problem("workflow.unknown_effect", {"effect": code}))
    return problems


def activate(workflow: Workflow) -> Workflow:
    problems = validate_workflow(workflow)
    if problems:
        raise UnprocessableEntity(
            "workflow.invalid", details=[{"msg": p.message_key, **p.params} for p in problems]
        )
    with transaction.atomic():
        Workflow.objects.filter(
            kind=workflow.kind, branch_id=workflow.branch_id, status=ConfigStatus.ACTIVE
        ).exclude(pk=workflow.pk).update(status=ConfigStatus.RETIRED)
        workflow.status = ConfigStatus.ACTIVE
        workflow.activated_at = timezone.now()
        workflow.save(update_fields=["status", "activated_at"])
    return workflow


# --- transitions ---------------------------------------------------------------------------------


def _permitted(
    transition: WorkflowTransition,
    actor: context.Actor,
    permissions: EffectivePermissions | None,
    branch_id: Any,
) -> bool:
    if transition.required_action == SYSTEM_ACTION:
        return actor.type == "SYSTEM"
    if permissions is None:
        return False
    resource, _, action = transition.required_action.partition(".")
    return permissions.allows(resource, action, branch_id=branch_id)


def _run_guards(ctx: TransitionContext) -> None:
    for spec in ctx.transition.guards or []:
        code, params = parse_spec(spec)
        negate = code.startswith("not ")
        code = code.removeprefix("not ")
        guard = GUARDS.get(code)
        if guard is None:
            raise GuardFailed(params={"guard": code, "reason": "not implemented"})
        ctx.params.setdefault("_guard_params", {})[code] = params
        outcome = guard(ctx)
        ok = outcome is True or (isinstance(outcome, str) and outcome == "")
        if negate:
            ok = not ok
        if not ok:
            reason = outcome if isinstance(outcome, str) and outcome else code
            raise GuardFailed(params={"guard": code, "reason": reason})


def _run_effects(ctx: TransitionContext) -> None:
    for spec in ctx.transition.effects or []:
        code, params = parse_spec(spec)
        effect = EFFECTS.get(code)
        if effect is None:
            raise Conflict(
                "workflow.effect_not_implemented",
                code="workflow_effect_missing",
                params={"effect": code},
            )
        effect(ctx, params)


def perform(
    record: StatefulModel,
    *,
    to_semantic: str,
    actor: context.Actor | None = None,
    permissions: EffectivePermissions | None = None,
    action: str | None = None,
    params: dict[str, Any] | None = None,
    save_fields: list[str] | None = None,
) -> TransitionContext:
    """Move ``record`` to a state with the given semantic, enforcing permission, guards and effects."""
    actor = actor or context.actor()
    current: WorkflowState = record.state
    workflow: Workflow = current.workflow
    candidates = [
        t
        for t in available_transitions(record)
        if t.to_state.semantic == to_semantic and (action is None or t.required_action == action)
    ]
    if not candidates:
        raise TransitionError(params={"from": current.semantic, "to": to_semantic})
    branch_id = getattr(record, "branch_id", None)
    permitted = [t for t in candidates if _permitted(t, actor, permissions, branch_id)]
    if not permitted:
        raise TransitionError(
            "workflow.transition_forbidden",
            code="workflow_transition_forbidden",
            params={
                "from": current.semantic,
                "to": to_semantic,
                "action": candidates[0].required_action,
            },
        )
    transition_ = permitted[0]
    ctx = TransitionContext(
        record=record,
        workflow=workflow,
        transition=transition_,
        from_state=current,
        to_state=transition_.to_state,
        actor=actor,
        params=dict(params or {}),
        permissions=permissions,
    )
    with transaction.atomic():
        _run_guards(ctx)
        record.state = transition_.to_state
        record.state_entered_at = timezone.now()
        record.state_entered_by = actor.id
        fields = ["state", "state_entered_at", "state_entered_by", *(save_fields or [])]
        record.save(update_fields=fields)
        audit.record(
            record._meta.model_name or "",
            record.pk,
            "transition",
            before={"state": current.code, "semantic": current.semantic},
            after={"state": transition_.to_state.code, "semantic": transition_.to_state.semantic},
            branch_id=branch_id,
            extra={
                "transition_id": transition_.id,
                "action": transition_.required_action,
                "reason": ctx.params.get("reason"),
            },
        )
        _run_effects(ctx)
    return ctx


# --- simulator -----------------------------------------------------------------------------------


def simulate(workflow: Workflow, actions: list[str]) -> list[dict[str, Any]]:
    """Walk the state graph applying actions (guards and effects ignored): the admin's dry run."""
    states = {s.id: s for s in workflow.states.all()}
    transitions = list(workflow.transitions.select_related("to_state").order_by("ord"))
    current = initial_state(workflow)
    path: list[dict[str, Any]] = [{"state": current.code, "semantic": current.semantic}]
    for action in actions:
        match = next(
            (
                t
                for t in transitions
                if t.required_action == action
                and (t.from_state_id is None or t.from_state_id == current.id)
            ),
            None,
        )
        if match is None or current.is_terminal:
            path.append(
                {"action": action, "error": "workflow.transition_denied", "from": current.code}
            )
            break
        current = states[match.to_state_id]
        path.append(
            {
                "action": action,
                "state": current.code,
                "semantic": current.semantic,
                "guards": match.guards,
                "effects": match.effects,
            }
        )
    return path
