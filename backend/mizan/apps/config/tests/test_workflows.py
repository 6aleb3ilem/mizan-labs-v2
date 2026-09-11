"""SPEC §10.3, §13.3: semantics, validation, permissions, guards, effects, simulator."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

import pytest

from mizan.apps.audit.models import AuditEvent
from mizan.apps.config import workflows
from mizan.apps.config.defaults.numbering import install_default_numbering
from mizan.apps.config.defaults.workflows import DEFAULT_WORKFLOWS, install_default_workflows
from mizan.apps.config.models import Workflow, WorkflowState
from mizan.apps.identity.authz import resolve_permissions
from mizan.platform import context
from mizan.platform.api.errors import Conflict

pytestmark = pytest.mark.django_db


class FakeQuote:
    """Enough of a stateful record for the engine: state, save, identity, branch, number."""

    numbering_kind = "QUOTE"

    class _meta:
        model_name = "quote"

    def __init__(self, state: WorkflowState, branch_id: uuid.UUID) -> None:
        self.state = state
        self.pk = uuid.uuid4()
        self.branch_id = branch_id
        self.department_id = None
        self.number = ""
        self.state_entered_at = None
        self.state_entered_by = None
        self.saves: list[Any] = []

    def save(self, update_fields: Any = None) -> None:
        self.saves.append(list(update_fields or []))


@pytest.fixture
def registries() -> Iterator[None]:
    guards, effects = dict(workflows.GUARDS), dict(workflows.EFFECTS)
    yield
    workflows.GUARDS.clear()
    workflows.GUARDS.update(guards)
    workflows.EFFECTS.clear()
    workflows.EFFECTS.update(effects)


@pytest.fixture
def installed(branch: Any) -> dict[str, Workflow]:
    install_default_numbering(branch)
    return install_default_workflows()


def test_every_default_workflow_is_valid_and_active(installed: dict[str, Workflow]) -> None:
    assert set(installed) == {spec.kind for spec in DEFAULT_WORKFLOWS} == set(workflows.SEMANTICS)
    for workflow in installed.values():
        assert workflows.validate_workflow(workflow) == []
        assert workflow.status == "ACTIVE"
        assert workflows.initial_state(workflow).is_initial
    assert workflows.get_active_workflow("QUOTE").kind == "QUOTE"
    assert workflows.state_for_semantic(installed["QUOTE"], "ACCEPTED").label("fr") == "Accepté"


def test_validation_reports_problems(installed: dict[str, Workflow]) -> None:
    workflow = installed["PROJECT"]
    workflow.states.filter(semantic="CLOSED").update(semantic="DONE")
    transition = workflow.transitions.first()
    assert transition is not None
    transition.guards = ["teleport"]
    transition.effects = ["fly(away)"]
    transition.save()
    keys = {p.message_key for p in workflows.validate_workflow(workflow)}
    assert keys == {
        "workflow.unknown_semantic",
        "workflow.semantic_missing",
        "workflow.unknown_guard",
        "workflow.unknown_effect",
    }


def test_transition_requires_permission_guards_and_runs_effects(
    installed: dict[str, Workflow], make_member: Any, branch: Any, registries: None
) -> None:
    quote_wf = installed["QUOTE"]
    record = FakeQuote(workflows.initial_state(quote_wf), branch.id)
    commercial, _ = make_member("COMMERCIAL")
    technician, _ = make_member("TECHNICIAN")
    commercial_actor = context.Actor(id=commercial.id, type="USER")

    # a technician cannot submit a quote
    with pytest.raises(workflows.TransitionError) as forbidden:
        workflows.perform(
            record,
            to_semantic="SENT",
            actor=context.Actor(id=technician.id),
            permissions=resolve_permissions(technician.id, technician.tenant_id),
        )
    assert forbidden.value.code == "workflow_transition_forbidden"

    # guards from the catalogue that no app implements yet fail closed
    with pytest.raises(workflows.GuardFailed) as closed:
        workflows.perform(
            record,
            to_semantic="SENT",
            actor=commercial_actor,
            permissions=resolve_permissions(commercial.id, commercial.tenant_id),
        )
    assert closed.value.params["guard"] == "has_billable_lines"

    workflows.register_guard("has_billable_lines")(lambda ctx: True)
    workflows.register_guard("totals_computed")(lambda ctx: True)
    workflows.register_guard("discount_within_threshold")(
        lambda ctx: ctx.params.get("discount", 0) <= 10
    )
    workflows.register_effect("freeze_revision")(
        lambda ctx, params: ctx.results.__setitem__("frozen", True)
    )
    workflows.register_effect("issue_document")(
        lambda ctx, params: ctx.results.__setitem__("document", params["arg"])
    )

    ctx = workflows.perform(
        record,
        to_semantic="SENT",
        actor=commercial_actor,
        permissions=resolve_permissions(commercial.id, commercial.tenant_id),
        params={"discount": 5},
    )
    assert record.state.semantic == "SENT"
    assert record.state_entered_by == commercial.id
    assert record.number.startswith("DV-NKC-")  # allocate_number effect used the branch scheme
    assert ctx.results == {
        "frozen": True,
        "number": record.number,
        "document": "QUOTE",
        "notifications": ["client_quote_sent"],
    }
    audit = AuditEvent.objects.get(
        aggregate_type="quote", aggregate_id=record.pk, action="transition"
    )
    assert audit.before["semantic"] == "DRAFT" and audit.after["semantic"] == "SENT"

    # the same submit with a large discount takes the approval branch
    draft = FakeQuote(workflows.initial_state(quote_wf), branch.id)
    ctx = workflows.perform(
        draft,
        to_semantic="PENDING_APPROVAL",
        actor=commercial_actor,
        permissions=resolve_permissions(commercial.id, commercial.tenant_id),
        params={"discount": 25},
    )
    assert draft.state.semantic == "PENDING_APPROVAL"
    # ... and the send branch is refused for it
    with pytest.raises(workflows.GuardFailed):
        workflows.perform(
            FakeQuote(workflows.initial_state(quote_wf), branch.id),
            to_semantic="SENT",
            actor=commercial_actor,
            permissions=resolve_permissions(commercial.id, commercial.tenant_id),
            params={"discount": 25},
        )


def test_wildcard_reason_and_terminal_states(
    installed: dict[str, Workflow], make_member: Any, branch: Any
) -> None:
    quote_wf = installed["QUOTE"]
    record = FakeQuote(workflows.initial_state(quote_wf), branch.id)
    manager, _ = make_member("COMMERCIAL_MANAGER")
    perms = resolve_permissions(manager.id, manager.tenant_id)
    actor = context.Actor(id=manager.id)
    assert {t.to_state.semantic for t in workflows.available_transitions(record)} == {
        "PENDING_APPROVAL",
        "SENT",
        "CANCELLED",
    }
    with pytest.raises(workflows.GuardFailed) as no_reason:
        workflows.perform(record, to_semantic="CANCELLED", actor=actor, permissions=perms)
    assert no_reason.value.params["guard"] == "reason_required"
    with pytest.raises(
        Conflict
    ):  # release_stock effect is owned by the assets app, not implemented yet
        workflows.perform(
            record,
            to_semantic="CANCELLED",
            actor=actor,
            permissions=perms,
            params={"reason": "client withdrew"},
        )
    record.state = workflows.state_for_semantic(quote_wf, "ACCEPTED")
    assert workflows.available_transitions(record) == []
    with pytest.raises(workflows.TransitionError):
        workflows.perform(
            record, to_semantic="CANCELLED", actor=actor, permissions=perms, params={"reason": "x"}
        )


def test_system_transitions_need_the_system_actor(
    installed: dict[str, Workflow], branch: Any, make_member: Any
) -> None:
    order_wf = installed["ORDER"]
    record = FakeQuote(workflows.initial_state(order_wf), branch.id)
    manager, _ = make_member("COMMERCIAL_MANAGER")
    with pytest.raises(workflows.TransitionError):
        workflows.perform(
            record,
            to_semantic="AMENDED",
            actor=context.Actor(id=manager.id),
            permissions=resolve_permissions(manager.id, manager.tenant_id),
        )
    workflows.perform(record, to_semantic="AMENDED", actor=context.Actor.system())
    assert record.state.semantic == "AMENDED"


def test_simulator_walks_the_graph(installed: dict[str, Workflow]) -> None:
    path = workflows.simulate(
        installed["QUOTE"],
        ["quote.submit", "quote.approve", "quote.edit", "quote.cancel", "quote.edit"],
    )
    assert [step.get("state") for step in path] == [
        "DRAFT",
        "PENDING_APPROVAL",
        "SENT",
        "NEGOTIATING",
        "REFUSED",
        None,
    ]
    assert path[-1]["error"] == "workflow.transition_denied"
    assert path[2]["effects"][0] == "freeze_revision"
