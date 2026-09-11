"""Write services of the configuration app: validation, audit and config.changed events."""

from __future__ import annotations

import uuid
from typing import Any

from django.db import transaction
from django.utils import timezone

from mizan.apps.audit import services as audit
from mizan.apps.config import payment_terms as pt
from mizan.apps.config.models import (
    ConfigStatus,
    PaymentTermsTemplate,
    Price,
    PriceList,
    Service,
    SpecimenType,
    TestDefinition,
    Workflow,
    WorkflowState,
    WorkflowTransition,
)
from mizan.apps.config.workflows import SEMANTICS
from mizan.platform.api.errors import Conflict, NotFound, UnprocessableEntity
from mizan.platform.events import emit
from mizan.platform.formula.engine import validate_definition_formulas

LEVELS = ("PER_SPECIMEN", "PER_PORTION", "PER_SERIES", "PER_RUN")
SCHEDULING_TYPES = ("NONE", "AGE", "TURNAROUND")


def changed(
    section: str,
    aggregate_id: uuid.UUID,
    action: str,
    *,
    before: Any = None,
    after: Any = None,
    branch_id: Any = None,
) -> None:
    audit.record(section, aggregate_id, action, before=before, after=after, branch_id=branch_id)
    emit(
        "config.changed",
        aggregate_type=section,
        aggregate_id=aggregate_id,
        branch_id=branch_id,
        payload={"section": section, "action": action},
    )


def get_or_404[M](model: type[M], pk: uuid.UUID) -> M:
    try:
        row: M = model._default_manager.get(pk=pk)  # type: ignore[attr-defined]
    except model.DoesNotExist as exc:  # type: ignore[attr-defined]
        raise NotFound() from exc
    return row


# --- workflows ------------------------------------------------------------------------------------


def clone_workflow_version(source: Workflow) -> Workflow:
    latest = (
        Workflow.objects.filter(kind=source.kind, branch_id=source.branch_id)
        .order_by("-version")
        .first()
    )
    version = (latest.version if latest else source.version) + 1
    with transaction.atomic():
        workflow: Workflow = Workflow.objects.create(
            kind=source.kind, branch_id=source.branch_id, version=version, status=ConfigStatus.DRAFT
        )
        mapping: dict[uuid.UUID, WorkflowState] = {}
        for state in source.states.all():
            copy: WorkflowState = WorkflowState.objects.create(
                workflow=workflow,
                code=state.code,
                semantic=state.semantic,
                colour=state.colour,
                is_initial=state.is_initial,
                is_terminal=state.is_terminal,
                sla_days=state.sla_days,
                ord=state.ord,
            )
            copy.set_labels(state.labels)
            mapping[state.id] = copy
        for t in source.transitions.all():
            copy_t: WorkflowTransition = WorkflowTransition.objects.create(
                workflow=workflow,
                from_state=mapping[t.from_state_id] if t.from_state_id else None,
                to_state=mapping[t.to_state_id],
                required_action=t.required_action,
                guards=list(t.guards or []),
                effects=list(t.effects or []),
                ord=t.ord,
            )
            if t.labels:
                copy_t.set_labels(t.labels)
        changed(
            "workflow",
            workflow.id,
            "version_created",
            after={"kind": workflow.kind, "version": version},
        )
    return workflow


def replace_definition(
    workflow: Workflow, states: list[dict[str, Any]], transitions: list[dict[str, Any]]
) -> Workflow:
    if workflow.status != ConfigStatus.DRAFT:
        raise Conflict("workflow.not_draft", code="workflow_not_draft")
    if workflow.kind not in SEMANTICS:
        raise UnprocessableEntity("workflow.unknown_kind")
    codes = [s["code"] for s in states]
    if len(codes) != len(set(codes)):
        raise UnprocessableEntity("workflow.duplicate_state_code")
    with transaction.atomic():
        WorkflowTransition.delete_labels_of(workflow.transitions.all())
        WorkflowState.delete_labels_of(workflow.states.all())
        workflow.transitions.all().delete()
        workflow.states.all().delete()
        by_code: dict[str, WorkflowState] = {}
        for ord_, s in enumerate(states):
            state: WorkflowState = WorkflowState.objects.create(
                workflow=workflow,
                code=s["code"],
                semantic=s["semantic"],
                colour=s.get("colour", "slate"),
                is_initial=s.get("is_initial", False),
                is_terminal=s.get("is_terminal", False),
                sla_days=s.get("sla_days"),
                ord=ord_,
            )
            state.set_labels({k: v for k, v in (s.get("labels") or {}).items() if v})
            by_code[s["code"]] = state
        for ord_, t in enumerate(transitions):
            if t["to_code"] not in by_code or (
                t.get("from_code") and t["from_code"] not in by_code
            ):
                raise UnprocessableEntity(
                    "workflow.transition_state_unknown", params={"transition": ord_}
                )
            transition_: WorkflowTransition = WorkflowTransition.objects.create(
                workflow=workflow,
                from_state=by_code[t["from_code"]] if t.get("from_code") else None,
                to_state=by_code[t["to_code"]],
                required_action=t["required_action"],
                guards=list(t.get("guards") or []),
                effects=list(t.get("effects") or []),
                ord=ord_,
            )
            labels = {k: v for k, v in (t.get("labels") or {}).items() if v}
            if labels:
                transition_.set_labels(labels)
        changed(
            "workflow",
            workflow.id,
            "definition_replaced",
            after={"states": codes, "transitions": len(transitions)},
        )
    return workflow


# --- payment terms --------------------------------------------------------------------------------


def create_payment_terms(
    *,
    branch_id: uuid.UUID,
    code: str,
    labels: dict[str, str],
    is_default: bool,
    milestones: list[dict[str, Any]],
) -> PaymentTermsTemplate:
    problems = pt.validate_milestones(milestones)
    if problems:
        raise UnprocessableEntity("config.payment_terms.invalid", details=problems)
    if PaymentTermsTemplate.objects.filter(branch_id=branch_id, code=code).exists():
        raise Conflict("config.payment_terms.code_exists", code="payment_terms_code_exists")
    with transaction.atomic():
        if is_default:
            PaymentTermsTemplate.objects.filter(branch_id=branch_id, is_default=True).update(
                is_default=False
            )
        template: PaymentTermsTemplate = PaymentTermsTemplate.objects.create(
            branch_id=branch_id, code=code, is_default=is_default, milestones=milestones
        )
        template.set_labels(labels)
        changed(
            "payment_terms_template",
            template.id,
            "created",
            after=audit.snapshot(template),
            branch_id=branch_id,
        )
    return template


def update_payment_terms(
    template: PaymentTermsTemplate, data: dict[str, Any]
) -> PaymentTermsTemplate:
    before = audit.snapshot(template)
    labels = data.pop("labels", None)
    if data.get("milestones") is not None:
        problems = pt.validate_milestones(data["milestones"])
        if problems:
            raise UnprocessableEntity("config.payment_terms.invalid", details=problems)
    for name, value in data.items():
        setattr(template, name, value)
    template.save()
    if labels:
        template.set_labels({k: v for k, v in labels.items() if v})
    changed(
        "payment_terms_template",
        template.id,
        "updated",
        before=before,
        after=audit.snapshot(template),
        branch_id=template.branch_id,
    )
    return template


def set_default_payment_terms(template: PaymentTermsTemplate) -> PaymentTermsTemplate:
    with transaction.atomic():
        PaymentTermsTemplate.objects.filter(branch_id=template.branch_id, is_default=True).update(
            is_default=False
        )
        template.is_default = True
        template.save(update_fields=["is_default"])
        changed("payment_terms_template", template.id, "set_default", branch_id=template.branch_id)
    return template


# --- test definitions -----------------------------------------------------------------------------


def validate_definition(data: dict[str, Any]) -> list[dict[str, Any]]:
    problems: list[dict[str, Any]] = []
    if data.get("unit_under_test") not in ("SPECIMEN", "SAMPLE"):
        problems.append({"loc": ["unit_under_test"], "msg": "SPECIMEN or SAMPLE"})
    scheduling = data.get("scheduling") or {}
    if scheduling.get("type", "NONE") not in SCHEDULING_TYPES:
        problems.append(
            {"loc": ["scheduling", "type"], "msg": f"one of {', '.join(SCHEDULING_TYPES)}"}
        )
    if scheduling.get("type") == "AGE" and not scheduling.get("allowed_ages"):
        problems.append(
            {"loc": ["scheduling", "allowed_ages"], "msg": "required for AGE scheduling"}
        )
    if scheduling.get("type") == "TURNAROUND" and not scheduling.get("business_days"):
        problems.append(
            {"loc": ["scheduling", "business_days"], "msg": "required for TURNAROUND scheduling"}
        )
    seen: set[str] = set()
    for section in ("inputs", "computed", "aggregates"):
        for i, spec in enumerate(data.get(section) or []):
            key = spec.get("key")
            if not key:
                problems.append({"loc": [section, i, "key"], "msg": "key required"})
            elif key in seen:
                problems.append({"loc": [section, i, "key"], "msg": f"duplicate key {key}"})
            seen.add(str(key))
            if section != "aggregates" and spec.get("level", "PER_SPECIMEN") not in LEVELS:
                problems.append(
                    {"loc": [section, i, "level"], "msg": f"one of {', '.join(LEVELS)}"}
                )
            if section != "inputs" and not spec.get("formula"):
                problems.append({"loc": [section, i, "formula"], "msg": "formula required"})
    for i, rule in enumerate(data.get("rules") or []):
        if rule.get("effect") not in ("FLAG", "EXCLUDE_AND_RECOMPUTE", "BLOCK"):
            problems.append(
                {"loc": ["rules", i, "effect"], "msg": "FLAG, EXCLUDE_AND_RECOMPUTE or BLOCK"}
            )
        if rule.get("effect") == "EXCLUDE_AND_RECOMPUTE" and not rule.get("target"):
            problems.append({"loc": ["rules", i, "target"], "msg": "target required"})
        if not rule.get("code"):
            problems.append({"loc": ["rules", i, "code"], "msg": "code required"})
    for problem in validate_definition_formulas(data):
        problems.append({"loc": [problem.where], "msg": problem.message_key, **problem.params})
    return problems


def create_definition(data: dict[str, Any], labels: dict[str, str]) -> TestDefinition:
    problems = validate_definition(data)
    if problems:
        raise UnprocessableEntity("config.test_definition.invalid", details=problems)
    if TestDefinition.objects.filter(code=data["code"]).exists():
        raise Conflict("config.test_definition.code_exists", code="test_definition_code_exists")
    definition: TestDefinition = TestDefinition.objects.create(
        version=1, status=ConfigStatus.DRAFT, **data
    )
    definition.set_labels(labels)
    changed(
        "test_definition", definition.id, "created", after={"code": definition.code, "version": 1}
    )
    return definition


def new_definition_version(
    source: TestDefinition, changes: dict[str, Any], labels: dict[str, str] | None
) -> TestDefinition:
    """Any change to inputs/computed/aggregates/rules is a new version; a locked version never changes."""
    latest = TestDefinition.objects.filter(code=source.code).order_by("-version").first()
    version = (latest.version if latest else source.version) + 1
    data = {
        f: getattr(source, f)
        for f in (
            "code", "category_id", "department_id", "method_ref", "unit_under_test", "specimen_type_codes", "scheduling",
            "stages", "intake_fields", "inputs", "computed", "aggregates", "rules", "required_equipment_class_code",
            "report_template_code", "report_columns", "unit_of_sale",
        )
    }  # fmt: skip
    data.update({k: v for k, v in changes.items() if v is not None})
    problems = validate_definition(data)
    if problems:
        raise UnprocessableEntity("config.test_definition.invalid", details=problems)
    definition: TestDefinition = TestDefinition.objects.create(
        version=version, status=ConfigStatus.DRAFT, **data
    )
    definition.set_labels(labels or source.labels)
    changed(
        "test_definition",
        definition.id,
        "version_created",
        after={"code": definition.code, "version": version},
    )
    return definition


def activate_definition(definition: TestDefinition) -> TestDefinition:
    problems = validate_definition(
        definition.as_spec() | {"unit_under_test": definition.unit_under_test}
    )
    if problems:
        raise UnprocessableEntity("config.test_definition.invalid", details=problems)
    with transaction.atomic():
        TestDefinition.objects.filter(code=definition.code, status=ConfigStatus.ACTIVE).exclude(
            pk=definition.pk
        ).update(status=ConfigStatus.RETIRED)
        definition.status = ConfigStatus.ACTIVE
        definition.activated_at = timezone.now()
        definition.save(update_fields=["status", "activated_at"])
        changed(
            "test_definition",
            definition.id,
            "activated",
            after={"code": definition.code, "version": definition.version},
        )
    return definition


def specimen_properties(code: str | None, explicit: dict[str, Any]) -> dict[str, Any]:
    if not code:
        return explicit
    specimen_type = SpecimenType.objects.filter(code=code).first()
    if specimen_type is None:
        raise UnprocessableEntity("config.specimen_type.unknown", params={"code": code})
    return {**specimen_type.properties(), **explicit}


# --- prices -----------------------------------------------------------------------------------------


def import_prices(
    price_list: PriceList, rows: list[dict[str, Any]]
) -> tuple[int, list[dict[str, Any]]]:
    services = {
        s.code: s for s in Service.objects.filter(code__in={r["service_code"] for r in rows})
    }
    types = {
        t.code: t
        for t in SpecimenType.objects.filter(
            code__in={r["specimen_type_code"] for r in rows if r.get("specimen_type_code")}
        )
    }
    errors: list[dict[str, Any]] = []
    imported = 0
    with transaction.atomic():
        for i, row in enumerate(rows, start=1):
            service = services.get(row["service_code"])
            if service is None:
                errors.append(
                    {
                        "row": i,
                        "column": "service_code",
                        "message_key": "config.price.unknown_service",
                    }
                )
                continue
            specimen_type = None
            if row.get("specimen_type_code"):
                specimen_type = types.get(row["specimen_type_code"])
                if specimen_type is None:
                    errors.append(
                        {
                            "row": i,
                            "column": "specimen_type_code",
                            "message_key": "config.price.unknown_specimen_type",
                        }
                    )
                    continue
            Price.objects.update_or_create(
                price_list=price_list,
                service=service,
                specimen_type=specimen_type,
                min_qty=row.get("min_qty", 1),
                defaults={"unit_price": row["unit_price"]},
            )
            imported += 1
        if errors:
            transaction.set_rollback(True)
            return 0, errors
        changed(
            "price_list",
            price_list.id,
            "prices_imported",
            after={"rows": imported},
            branch_id=price_list.branch_id,
        )
    return imported, errors
