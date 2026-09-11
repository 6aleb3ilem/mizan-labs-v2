"""Built-in guards and effects that are generic (domain apps register the domain-specific ones)."""

from __future__ import annotations

from typing import Any

from mizan.apps.config.workflows import TransitionContext, register_effect, register_guard
from mizan.platform.events import emit


@register_guard("reason_required")
def reason_required(ctx: TransitionContext) -> bool | str:
    return bool(str(ctx.params.get("reason", "")).strip()) or "workflow.reason_required"


@register_guard("actor_is_not_entrant")
def actor_is_not_entrant(ctx: TransitionContext) -> bool | str:
    """Segregation of duties: the reviewer differs from the person who produced the state."""
    branch = getattr(ctx.record, "branch", None)
    settings = getattr(branch, "settings", {}) or {}
    if settings.get("reviewer_must_differ_from_entrant", True) is False:
        return True
    entrant = getattr(ctx.record, "state_entered_by", None)
    return (entrant is None or entrant != ctx.actor.id) or "workflow.actor_is_entrant"


@register_effect("emit")
def emit_event(ctx: TransitionContext, params: dict[str, Any]) -> None:
    code = str(params.get("arg") or params.get("event") or "")
    emit(
        code,
        aggregate_type=ctx.record._meta.model_name or "",
        aggregate_id=ctx.record.pk,
        branch_id=getattr(ctx.record, "branch_id", None),
        payload={
            "from": ctx.from_state.semantic if ctx.from_state else None,
            "to": ctx.to_state.semantic,
            **{k: v for k, v in ctx.params.items() if not k.startswith("_")},
        },
    )


@register_effect("notify")
def notify(ctx: TransitionContext, params: dict[str, Any]) -> None:
    """Records the requested notification rule; the notify app subscribes to the emitted event."""
    ctx.results.setdefault("notifications", []).append(str(params.get("arg", "")))


@register_effect("allocate_number")
def allocate_number(ctx: TransitionContext, params: dict[str, Any]) -> None:
    from mizan.apps.config.numbering import active_scheme, allocate

    record = ctx.record
    if getattr(record, "number", None):
        return
    kind = params.get("arg") or getattr(record, "numbering_kind", None)
    if not kind:
        return
    scheme = active_scheme(str(kind), record.branch_id, getattr(record, "department_id", None))
    allocated = allocate(scheme)
    record.number = allocated.number
    record.save(update_fields=["number"])
    ctx.results["number"] = allocated.number
