"""Default workflow templates (SPEC §10.3, §13.3, Appendix C). Installed per tenant; editable."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mizan.apps.config.models import ConfigStatus, Workflow, WorkflowState, WorkflowTransition


@dataclass(frozen=True)
class StateSpec:
    code: str
    semantic: str
    labels: dict[str, str]
    colour: str = "slate"
    initial: bool = False
    terminal: bool = False
    sla_days: int | None = None


@dataclass(frozen=True)
class TransitionSpec:
    from_code: str | None  # None: from any non-terminal state
    to_code: str
    action: str
    guards: tuple[Any, ...] = ()
    effects: tuple[Any, ...] = ()
    labels: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowSpec:
    kind: str
    states: tuple[StateSpec, ...]
    transitions: tuple[TransitionSpec, ...]


def _s(code: str, fr: str, en: str, colour: str = "slate", **kw: Any) -> StateSpec:
    return StateSpec(code, code, {"fr": fr, "en": en}, colour, **kw)


def _t(
    frm: str | None,
    to: str,
    action: str,
    guards: tuple[Any, ...] = (),
    effects: tuple[Any, ...] = (),
    fr: str = "",
    en: str = "",
) -> TransitionSpec:
    return TransitionSpec(frm, to, action, guards, effects, {"fr": fr, "en": en} if fr else {})


QUOTE = WorkflowSpec(
    "QUOTE",
    (
        _s("DRAFT", "Brouillon", "Draft", initial=True),
        _s("PENDING_APPROVAL", "En attente d'approbation", "Pending approval", "amber"),
        _s("SENT", "Envoyé", "Sent", "blue", sla_days=15),
        _s("NEGOTIATING", "En négociation", "Negotiating", "violet"),
        _s("ACCEPTED", "Accepté", "Accepted", "green", terminal=True),
        _s("REFUSED", "Refusé", "Refused", "red", terminal=True),
        _s("SUSPENDED", "Suspendu", "Suspended", "orange"),
        _s("EXPIRED", "Expiré", "Expired", "gray", terminal=True),
        _s("CANCELLED", "Annulé", "Cancelled", "gray", terminal=True),
    ),
    (
        _t(
            "DRAFT",
            "PENDING_APPROVAL",
            "quote.submit",
            ("has_billable_lines", "totals_computed", "not discount_within_threshold"),
            ("notify(approvers)", "emit(quote.approval_requested)"),
            "Soumettre pour approbation",
            "Submit for approval",
        ),
        _t(
            "DRAFT",
            "SENT",
            "quote.submit",
            ("has_billable_lines", "totals_computed", "discount_within_threshold"),
            (
                "freeze_revision",
                "allocate_number",
                "issue_document(QUOTE)",
                "notify(client_quote_sent)",
                "emit(quote.sent)",
            ),
            "Envoyer",
            "Send",
        ),
        _t(
            "PENDING_APPROVAL",
            "SENT",
            "quote.approve",
            ("signatory_authorised",),
            (
                "freeze_revision",
                "allocate_number",
                "issue_document(QUOTE)",
                "notify(client_quote_sent)",
                "emit(quote.approved)",
                "emit(quote.sent)",
            ),
            "Approuver et envoyer",
            "Approve and send",
        ),
        _t("PENDING_APPROVAL", "DRAFT", "quote.edit", (), (), "Reprendre", "Back to draft"),
        _t(
            "SENT",
            "NEGOTIATING",
            "quote.edit",
            (),
            ("emit(quote.negotiating)",),
            "Marquer en négociation",
            "Mark negotiating",
        ),
        _t(
            "SENT",
            "DRAFT",
            "quote.edit",
            (),
            ("create_next_revision_on_edit",),
            "Nouvelle révision",
            "New revision",
        ),
        _t(
            "NEGOTIATING",
            "DRAFT",
            "quote.edit",
            (),
            ("create_next_revision_on_edit",),
            "Nouvelle révision",
            "New revision",
        ),
        _t(
            "SENT",
            "ACCEPTED",
            "quote.approve",
            ("acceptance_evidence_attached",),
            (
                "create_order",
                "provision_work",
                "make_milestone_invoiceable(ON_ACCEPTANCE)",
                "notify(internal_accepted)",
                "emit(quote.accepted)",
            ),
            "Accepter",
            "Accept",
        ),
        _t(
            "NEGOTIATING",
            "ACCEPTED",
            "quote.approve",
            ("acceptance_evidence_attached",),
            (
                "create_order",
                "provision_work",
                "make_milestone_invoiceable(ON_ACCEPTANCE)",
                "notify(internal_accepted)",
                "emit(quote.accepted)",
            ),
            "Accepter",
            "Accept",
        ),
        _t(
            "SENT",
            "REFUSED",
            "quote.cancel",
            ("reason_required",),
            ("notify(internal_refused)", "emit(quote.refused)"),
            "Marquer refusé",
            "Mark refused",
        ),
        _t(
            "NEGOTIATING",
            "REFUSED",
            "quote.cancel",
            ("reason_required",),
            ("notify(internal_refused)", "emit(quote.refused)"),
            "Marquer refusé",
            "Mark refused",
        ),
        _t(
            "SENT",
            "SUSPENDED",
            "quote.edit",
            ("reason_required",),
            ("emit(quote.suspended)",),
            "Suspendre",
            "Suspend",
        ),
        _t(
            "NEGOTIATING",
            "SUSPENDED",
            "quote.edit",
            ("reason_required",),
            ("emit(quote.suspended)",),
            "Suspendre",
            "Suspend",
        ),
        _t(
            "SUSPENDED",
            "NEGOTIATING",
            "quote.edit",
            (),
            (),
            "Reprendre la négociation",
            "Resume negotiation",
        ),
        _t(
            "SENT",
            "EXPIRED",
            "system",
            ("validity_elapsed",),
            ("notify(owner_expired)", "emit(quote.expired)"),
        ),
        _t(
            None,
            "CANCELLED",
            "quote.cancel",
            ("reason_required",),
            ("release_stock", "emit(quote.cancelled)"),
            "Annuler",
            "Cancel",
        ),
    ),
)

TEST_RUN = WorkflowSpec(
    "TEST_RUN",
    (
        _s("SCHEDULED", "Planifié", "Scheduled", initial=True),
        _s("IN_PROGRESS", "En cours", "In progress", "blue"),
        _s("MEASURED", "Mesuré", "Measured", "violet"),
        _s("UNDER_REVIEW", "En revue", "Under review", "amber"),
        _s("VALIDATED", "Validé", "Validated", "green"),
        _s("REPORTED", "Rapporté", "Reported", "green", terminal=True),
        _s("CANCELLED", "Annulé", "Cancelled", "gray", terminal=True),
    ),
    (
        _t(
            "SCHEDULED",
            "IN_PROGRESS",
            "test_run.edit",
            ("assigned_or_can_assign",),
            ("emit(test_run.started)",),
            "Démarrer",
            "Start",
        ),
        _t(
            "IN_PROGRESS",
            "MEASURED",
            "test_run.edit",
            ("all_measurements_present", "no_rule_blocking"),
            ("notify(supervisor_measured)", "emit(test_run.measured)"),
            "Marquer mesuré",
            "Mark measured",
        ),
        _t(
            "MEASURED",
            "UNDER_REVIEW",
            "test_run.review_results",
            ("actor_is_not_entrant",),
            (),
            "Prendre en revue",
            "Review",
        ),
        _t(
            "UNDER_REVIEW",
            "VALIDATED",
            "test_run.review_results",
            (),
            ("emit(test_run.validated)",),
            "Valider",
            "Validate",
        ),
        _t(
            "UNDER_REVIEW",
            "IN_PROGRESS",
            "test_run.review_results",
            ("reason_required",),
            ("notify(technician_returned)",),
            "Renvoyer au technicien",
            "Return to technician",
        ),
        _t(
            "VALIDATED",
            "REPORTED",
            "system",
            (),
            ("increment_delivered", "close_parent_if_complete"),
        ),
        _t(
            None,
            "CANCELLED",
            "test_run.cancel",
            ("reason_required",),
            ("release_specimens", "emit(test_run.cancelled)"),
            "Annuler",
            "Cancel",
        ),
    ),
)

REPORT = WorkflowSpec(
    "REPORT",
    (
        _s("DRAFT", "Brouillon", "Draft", initial=True),
        _s("ISSUED", "Émis", "Issued", "green"),
        _s("SUPERSEDED", "Remplacé", "Superseded", "gray", terminal=True),
        _s("REVOKED", "Révoqué", "Revoked", "red", terminal=True),
    ),
    (
        _t(
            "DRAFT",
            "ISSUED",
            "report.issue",
            ("all_runs_validated", "signatory_authorised"),
            (
                "allocate_number",
                "issue_document(REPORT)",
                "notify(client_report_issued)",
                "make_milestone_invoiceable(ON_REPORT)",
                "emit(report.issued)",
            ),
            "Émettre",
            "Issue",
        ),
        _t(
            "ISSUED",
            "SUPERSEDED",
            "system",
            (),
            (
                "update_document_status(SUPERSEDED)",
                "notify(client_report_superseded)",
                "emit(report.superseded)",
            ),
        ),
        _t(
            "ISSUED",
            "REVOKED",
            "report.cancel",
            ("reason_required",),
            (
                "update_document_status(REVOKED)",
                "notify(client_report_revoked)",
                "decrement_delivered",
                "emit(report.revoked)",
            ),
            "Révoquer",
            "Revoke",
        ),
    ),
)

INVOICE = WorkflowSpec(
    "INVOICE",
    (
        _s("DRAFT", "Brouillon", "Draft", initial=True),
        _s("ISSUED", "Émise", "Issued", "green", terminal=True),
        _s("CANCELLED", "Annulée", "Cancelled", "gray", terminal=True),
    ),
    (
        _t(
            "DRAFT",
            "ISSUED",
            "invoice.issue",
            ("invoice_has_lines",),
            (
                "allocate_number",
                "issue_document(INVOICE)",
                "notify(client_invoice_issued)",
                "emit(invoice.issued)",
            ),
            "Émettre",
            "Issue",
        ),
        _t("DRAFT", "CANCELLED", "invoice.cancel", (), (), "Annuler", "Cancel"),
    ),
)

PROJECT = WorkflowSpec(
    "PROJECT",
    (
        _s("OPEN", "Ouvert", "Open", "blue", initial=True),
        _s("ON_HOLD", "En pause", "On hold", "amber"),
        _s("CLOSED", "Clôturé", "Closed", "green", terminal=True),
        _s("CANCELLED", "Annulé", "Cancelled", "gray", terminal=True),
    ),
    (
        _t(
            "OPEN",
            "ON_HOLD",
            "project.edit",
            ("reason_required",),
            (),
            "Mettre en pause",
            "Put on hold",
        ),
        _t("ON_HOLD", "OPEN", "project.edit", (), (), "Reprendre", "Resume"),
        _t(
            "OPEN",
            "CLOSED",
            "project.edit",
            ("no_open_children",),
            ("emit(project.closed)",),
            "Clôturer",
            "Close",
        ),
        _t(None, "CANCELLED", "project.cancel", ("reason_required",), (), "Annuler", "Cancel"),
    ),
)

ACCOUNT = WorkflowSpec(
    "ACCOUNT",
    (
        _s("ACTIVE", "Actif", "Active", "green", initial=True),
        _s("INACTIVE", "Inactif", "Inactive", "gray"),
        _s("BLOCKED", "Bloqué", "Blocked", "red"),
    ),
    (
        _t("ACTIVE", "INACTIVE", "account.edit", (), (), "Désactiver", "Deactivate"),
        _t("INACTIVE", "ACTIVE", "account.edit", (), (), "Réactiver", "Reactivate"),
        _t("ACTIVE", "BLOCKED", "account.edit", ("reason_required",), (), "Bloquer", "Block"),
        _t("BLOCKED", "ACTIVE", "account.edit", (), (), "Débloquer", "Unblock"),
    ),
)

CONTRACT = WorkflowSpec(
    "CONTRACT",
    (
        _s("DRAFT", "Brouillon", "Draft", initial=True),
        _s("SENT_FOR_SIGNATURE", "Envoyé pour signature", "Sent for signature", "blue"),
        _s("SIGNED", "Signé", "Signed", "green", terminal=True),
        _s("CANCELLED", "Annulé", "Cancelled", "gray", terminal=True),
    ),
    (
        _t(
            "DRAFT",
            "SENT_FOR_SIGNATURE",
            "contract.submit",
            (),
            ("request_signature", "emit(contract.sent)"),
            "Envoyer pour signature",
            "Send for signature",
        ),
        _t(
            "SENT_FOR_SIGNATURE",
            "SIGNED",
            "contract.sign",
            ("acceptance_evidence_attached",),
            ("issue_document(CONTRACT)", "emit(contract.signed)"),
            "Enregistrer la signature",
            "Record signature",
        ),
        _t(None, "CANCELLED", "contract.cancel", ("reason_required",), (), "Annuler", "Cancel"),
    ),
)

ORDER = WorkflowSpec(
    "ORDER",
    (
        _s("OPEN", "Ouverte", "Open", "blue", initial=True),
        _s("AMENDED", "Amendée", "Amended", "violet"),
        _s("COMPLETED", "Terminée", "Completed", "green", terminal=True),
        _s("CANCELLED", "Annulée", "Cancelled", "gray", terminal=True),
    ),
    (
        _t("OPEN", "AMENDED", "system", (), ("emit(order.amended)",)),
        _t("AMENDED", "COMPLETED", "system", ("no_open_children",), ("emit(order.completed)",)),
        _t("OPEN", "COMPLETED", "system", ("no_open_children",), ("emit(order.completed)",)),
        _t(
            None,
            "CANCELLED",
            "order.cancel",
            ("reason_required",),
            ("release_stock",),
            "Annuler",
            "Cancel",
        ),
    ),
)

INTAKE = WorkflowSpec(
    "INTAKE",
    (
        _s("REGISTERED", "Enregistrée", "Registered", "blue", initial=True),
        _s("PARTIALLY_PROCESSED", "Partiellement traitée", "Partially processed", "amber"),
        _s("PROCESSED", "Traitée", "Processed", "green", terminal=True),
        _s("CANCELLED", "Annulée", "Cancelled", "gray", terminal=True),
    ),
    (
        _t("REGISTERED", "PARTIALLY_PROCESSED", "system", (), ()),
        _t("PARTIALLY_PROCESSED", "PROCESSED", "system", ("all_runs_of_intake_reported",), ()),
        _t("REGISTERED", "PROCESSED", "system", ("all_runs_of_intake_reported",), ()),
        _t(
            "REGISTERED",
            "CANCELLED",
            "intake.cancel",
            ("reason_required", "all_measurements_present"),
            (),
            "Annuler",
            "Cancel",
        ),
    ),
)

PAYMENT = WorkflowSpec(
    "PAYMENT",
    (
        _s("RECORDED", "Enregistré", "Recorded", "green", initial=True),
        _s("REVERSED", "Annulé", "Reversed", "red", terminal=True),
    ),
    (
        _t(
            "RECORDED",
            "REVERSED",
            "payment.cancel",
            ("reason_required",),
            ("emit(payment.reversed)",),
            "Annuler le paiement",
            "Reverse",
        ),
    ),
)

RENTAL = WorkflowSpec(
    "RENTAL",
    (
        _s("RESERVED", "Réservée", "Reserved", initial=True),
        _s("ACTIVE", "En cours", "Active", "blue"),
        _s("LATE", "En retard", "Late", "red"),
        _s("RETURNED", "Retournée", "Returned", "amber"),
        _s("CLOSED", "Clôturée", "Closed", "green", terminal=True),
        _s("CANCELLED", "Annulée", "Cancelled", "gray", terminal=True),
    ),
    (
        _t(
            "RESERVED",
            "ACTIVE",
            "rental.edit",
            ("stock_available",),
            ("stock_movement(RENTAL_OUT)", "issue_document(RENTAL_NOTE)", "emit(rental.started)"),
            "Remettre",
            "Hand over",
        ),
        _t("ACTIVE", "LATE", "system", (), ("notify(rental_late)", "emit(rental.late)")),
        _t(
            "ACTIVE",
            "RETURNED",
            "rental.edit",
            ("condition_recorded",),
            ("stock_movement(RENTAL_IN)", "compute_penalty", "emit(rental.returned)"),
            "Retour",
            "Return",
        ),
        _t(
            "LATE",
            "RETURNED",
            "rental.edit",
            ("condition_recorded",),
            ("stock_movement(RENTAL_IN)", "compute_penalty", "emit(rental.returned)"),
            "Retour",
            "Return",
        ),
        _t("RETURNED", "CLOSED", "rental.edit", ("penalties_settled",), (), "Clôturer", "Close"),
        _t(
            "RESERVED",
            "CANCELLED",
            "rental.cancel",
            ("reason_required",),
            ("release_stock",),
            "Annuler",
            "Cancel",
        ),
    ),
)

SALE = WorkflowSpec(
    "SALE",
    (
        _s("RESERVED", "Réservée", "Reserved", initial=True),
        _s("DELIVERED", "Livrée", "Delivered", "green", terminal=True),
        _s("CANCELLED", "Annulée", "Cancelled", "gray", terminal=True),
    ),
    (
        _t(
            "RESERVED",
            "DELIVERED",
            "sale.edit",
            ("stock_available",),
            ("stock_movement(SALE)", "issue_document(SALE_NOTE)"),
            "Livrer",
            "Deliver",
        ),
        _t(
            "RESERVED",
            "CANCELLED",
            "sale.cancel",
            ("reason_required",),
            ("release_stock",),
            "Annuler",
            "Cancel",
        ),
    ),
)

OUTING = WorkflowSpec(
    "OUTING",
    (
        _s("OPEN", "Ouverte", "Open", "blue", initial=True),
        _s("PARTIALLY_RETURNED", "Partiellement retournée", "Partially returned", "amber"),
        _s("CLOSED", "Clôturée", "Closed", "green", terminal=True),
    ),
    (
        _t(
            "OPEN",
            "PARTIALLY_RETURNED",
            "outing.edit",
            (),
            ("stock_movement(OUTING_IN)",),
            "Retour partiel",
            "Partial return",
        ),
        _t(
            "OPEN", "CLOSED", "outing.edit", (), ("stock_movement(OUTING_IN)",), "Clôturer", "Close"
        ),
        _t(
            "PARTIALLY_RETURNED",
            "CLOSED",
            "outing.edit",
            (),
            ("stock_movement(OUTING_IN)",),
            "Clôturer",
            "Close",
        ),
    ),
)

TRANSFER = WorkflowSpec(
    "TRANSFER",
    (
        _s("DRAFT", "Brouillon", "Draft", initial=True),
        _s("VALIDATED", "Validé", "Validated", "blue"),
        _s("IN_TRANSIT", "En transit", "In transit", "violet"),
        _s("RECEIVED", "Reçu", "Received", "green", terminal=True),
        _s("CANCELLED", "Annulé", "Cancelled", "gray", terminal=True),
    ),
    (
        _t(
            "DRAFT",
            "VALIDATED",
            "transfer.approve",
            ("stock_available",),
            (),
            "Valider",
            "Validate",
        ),
        _t(
            "VALIDATED",
            "IN_TRANSIT",
            "transfer.edit",
            (),
            ("stock_movement(TRANSFER_OUT)", "emit(transfer.dispatched)"),
            "Expédier",
            "Dispatch",
        ),
        _t(
            "IN_TRANSIT",
            "RECEIVED",
            "transfer.edit",
            (),
            ("stock_movement(TRANSFER_IN)", "emit(transfer.received)"),
            "Réceptionner",
            "Receive",
        ),
        _t("DRAFT", "CANCELLED", "transfer.cancel", ("reason_required",), (), "Annuler", "Cancel"),
        _t(
            "VALIDATED",
            "CANCELLED",
            "transfer.cancel",
            ("reason_required",),
            (),
            "Annuler",
            "Cancel",
        ),
    ),
)

MAINTENANCE = WorkflowSpec(
    "MAINTENANCE",
    (
        _s("PLANNED", "Planifiée", "Planned", initial=True),
        _s("IN_PROGRESS", "En cours", "In progress", "blue"),
        _s("DONE", "Terminée", "Done", "green", terminal=True),
        _s("CANCELLED", "Annulée", "Cancelled", "gray", terminal=True),
    ),
    (
        _t("PLANNED", "IN_PROGRESS", "maintenance.edit", (), (), "Démarrer", "Start"),
        _t(
            "IN_PROGRESS",
            "DONE",
            "maintenance.edit",
            (),
            ("emit(maintenance.done)",),
            "Clôturer",
            "Close",
        ),
        _t(None, "CANCELLED", "maintenance.cancel", ("reason_required",), (), "Annuler", "Cancel"),
    ),
)

WORK_ORDER = WorkflowSpec(
    "WORK_ORDER",
    (
        _s("PLANNED", "Planifié", "Planned", initial=True),
        _s("IN_PROGRESS", "En cours", "In progress", "blue"),
        _s("LATE", "En retard", "Late", "red"),
        _s("COMPLETED", "Terminé", "Completed", "green", terminal=True),
        _s("CANCELLED", "Annulé", "Cancelled", "gray", terminal=True),
    ),
    (
        _t("PLANNED", "IN_PROGRESS", "system", (), ()),
        _t(
            "IN_PROGRESS",
            "LATE",
            "system",
            (),
            ("notify(work_order_late)", "emit(work_order.late)"),
        ),
        _t(
            "IN_PROGRESS",
            "COMPLETED",
            "system",
            (),
            (
                "increment_delivered",
                "make_milestone_invoiceable(ON_DELIVERY)",
                "emit(work_order.completed)",
            ),
        ),
        _t(
            "LATE",
            "COMPLETED",
            "system",
            (),
            (
                "increment_delivered",
                "make_milestone_invoiceable(ON_DELIVERY)",
                "emit(work_order.completed)",
            ),
        ),
        _t(None, "CANCELLED", "work_order.cancel", ("reason_required",), (), "Annuler", "Cancel"),
    ),
)

PHASE = WorkflowSpec(
    "PHASE",
    (
        _s("PENDING", "À faire", "Pending", initial=True),
        _s("IN_PROGRESS", "En cours", "In progress", "blue"),
        _s("COMPLETED", "Terminée", "Completed", "green", terminal=True),
    ),
    (
        _t("PENDING", "IN_PROGRESS", "work_order.edit", (), (), "Démarrer", "Start"),
        _t(
            "IN_PROGRESS",
            "COMPLETED",
            "work_order.edit",
            (),
            ("emit(phase.completed)",),
            "Terminer",
            "Complete",
        ),
    ),
)

DEFAULT_WORKFLOWS: tuple[WorkflowSpec, ...] = (
    PROJECT, ACCOUNT, QUOTE, CONTRACT, ORDER, INTAKE, TEST_RUN, REPORT, INVOICE, PAYMENT, RENTAL, SALE, OUTING,
    TRANSFER, MAINTENANCE, WORK_ORDER, PHASE,
)  # fmt: skip


def install_workflow(
    spec: WorkflowSpec, *, branch_id: Any = None, activate: bool = True
) -> Workflow:
    """Create version 1 of a default workflow for the active tenant (no-op when it exists)."""
    existing: Workflow | None = (
        Workflow.objects.filter(kind=spec.kind, branch_id=branch_id).order_by("-version").first()
    )
    if existing is not None:
        return existing
    workflow: Workflow = Workflow.objects.create(
        kind=spec.kind, branch_id=branch_id, version=1, status=ConfigStatus.DRAFT
    )
    states: dict[str, WorkflowState] = {}
    for ord_, s in enumerate(spec.states):
        state: WorkflowState = WorkflowState.objects.create(
            workflow=workflow,
            code=s.code,
            semantic=s.semantic,
            colour=s.colour,
            is_initial=s.initial,
            is_terminal=s.terminal,
            sla_days=s.sla_days,
            ord=ord_,
        )
        state.set_labels(s.labels)
        states[s.code] = state
    for ord_, t in enumerate(spec.transitions):
        transition: WorkflowTransition = WorkflowTransition.objects.create(
            workflow=workflow,
            from_state=states[t.from_code] if t.from_code else None,
            to_state=states[t.to_code],
            required_action=t.action,
            guards=list(t.guards),
            effects=list(t.effects),
            ord=ord_,
        )
        if t.labels:
            transition.set_labels(t.labels)
    if activate:
        from mizan.apps.config.workflows import activate as activate_workflow

        activate_workflow(workflow)
    return workflow


def install_default_workflows(*, branch_id: Any = None) -> dict[str, Workflow]:
    return {spec.kind: install_workflow(spec, branch_id=branch_id) for spec in DEFAULT_WORKFLOWS}
