"""Configuration API (SPEC A.2): numbering, vocabularies, workflows, payment terms, catalog, prices."""

import datetime as dt
import uuid
from decimal import Decimal
from typing import Any

from django.http import HttpRequest
from ninja import Router, Status

from mizan.apps.config import numbering, payment_terms, services, vocabularies, workflows
from mizan.apps.config.models import (
    ConfigStatus,
    NumberingScheme,
    PaymentTermsTemplate,
    Price,
    PriceList,
    Service,
    ServiceCategory,
    SieveSet,
    SpecimenType,
    TaxRule,
    TestDefinition,
    VocabularyEntry,
    Workflow,
)
from mizan.apps.config.prices import resolve_price
from mizan.apps.config.schemas import (
    CategoryIn,
    CategoryOut,
    NumberingSchemeIn,
    NumberingSchemeOut,
    NumberingVersionIn,
    PaymentTermsIn,
    PaymentTermsOut,
    PaymentTermsPatch,
    PriceImportIn,
    PriceListIn,
    PriceListOut,
    PriceOut,
    ReservationIn,
    SandboxDataIn,
    SandboxIn,
    ServiceIn,
    ServiceOut,
    ServicePatch,
    SieveSetIn,
    SieveSetOut,
    SimulateIn,
    SpecimenTypeIn,
    SpecimenTypeOut,
    TaxRuleIn,
    TaxRuleOut,
    TaxRulePatch,
    TestDefinitionIn,
    TestDefinitionOut,
    TestDefinitionVersionIn,
    VocabularyEntryIn,
    VocabularyEntryOut,
    VocabularyEntryPatch,
    WorkflowDefinitionIn,
    WorkflowOut,
)
from mizan.apps.identity.authz import requires
from mizan.platform.api.errors import Conflict, UnprocessableEntity
from mizan.platform.formula.engine import RunData, Subject, evaluate_definition

router = Router(tags=["configuration"])


def _labels(payload: Any) -> dict[str, str]:
    return {k: v for k, v in payload.model_dump(exclude_none=True).items() if v} if payload else {}


def _with_labels(row: Any, schema: type[Any], **extra: Any) -> dict[str, Any]:
    data: dict[str, Any] = schema.from_orm(row).model_dump(exclude={"labels", *extra})
    data["labels"] = row.labels
    data.update(extra)
    return data


# --- numbering --------------------------------------------------------------------------------------


def _scheme_out(s: NumberingScheme) -> dict[str, Any]:
    data = NumberingSchemeOut.from_orm(s).model_dump(exclude={"preview"})
    data["preview"] = numbering.preview(s) if s.status == ConfigStatus.ACTIVE else None
    return data


@router.get(
    "/numbering-schemes",
    response=list[NumberingSchemeOut],
    summary="Numbering schemes with the next number preview",
)
@requires("numbering_scheme", "view")
def list_numbering_schemes(
    request: HttpRequest, branch_id: uuid.UUID | None = None, applies_to: str | None = None
) -> list[dict[str, Any]]:
    qs = NumberingScheme.objects.select_related("branch", "department").order_by(
        "applies_to", "-version"
    )
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    if applies_to:
        qs = qs.filter(applies_to=applies_to)
    return [_scheme_out(s) for s in qs]


@router.post(
    "/numbering-schemes", response={201: NumberingSchemeOut}, summary="Create a draft scheme"
)
@requires("numbering_scheme", "configure")
def create_numbering_scheme(
    request: HttpRequest, payload: NumberingSchemeIn
) -> Status[dict[str, Any]]:
    numbering.validate_scheme(payload.pattern, payload.gap_policy, payload.allocation)
    latest = (
        NumberingScheme.objects.filter(
            branch_id=payload.branch_id,
            department_id=payload.department_id,
            applies_to=payload.applies_to,
        )
        .order_by("-version")
        .first()
    )
    scheme = NumberingScheme.objects.create(
        **payload.model_dump(), version=(latest.version + 1 if latest else 1)
    )
    services.changed(
        "numbering_scheme",
        scheme.id,
        "created",
        after={"pattern": scheme.pattern, "version": scheme.version},
        branch_id=scheme.branch_id,
    )
    return Status(201, _scheme_out(scheme))


@router.post("/numbering-schemes/{uuid:scheme_id}:activate", response=NumberingSchemeOut)
@requires("numbering_scheme", "configure")
def activate_numbering_scheme(request: HttpRequest, scheme_id: uuid.UUID) -> dict[str, Any]:
    scheme = numbering.activate(services.get_or_404(NumberingScheme, scheme_id))
    services.changed("numbering_scheme", scheme.id, "activated", branch_id=scheme.branch_id)
    return _scheme_out(scheme)


@router.get(
    "/numbering-schemes/{uuid:scheme_id}/preview",
    response=dict[str, str],
    summary="Next number without allocating",
)
@requires("numbering_scheme", "view")
def preview_numbering_scheme(
    request: HttpRequest, scheme_id: uuid.UUID, on: dt.date | None = None
) -> dict[str, str]:
    scheme = services.get_or_404(NumberingScheme, scheme_id)
    return {"next": numbering.preview(scheme, on=on)}


@router.post(
    "/numbering-schemes/{uuid:scheme_id}/reservations",
    response=dict[str, int],
    summary="Reserve numbers used elsewhere",
)
@requires("numbering_scheme", "configure")
def reserve_numbers(
    request: HttpRequest, scheme_id: uuid.UUID, payload: ReservationIn
) -> dict[str, int]:
    scheme = services.get_or_404(NumberingScheme, scheme_id)
    rows = numbering.reserve(scheme, payload.numbers, reason=payload.reason)
    services.changed(
        "numbering_scheme",
        scheme.id,
        "numbers_reserved",
        after={"count": len(rows)},
        branch_id=scheme.branch_id,
    )
    return {"reserved": len(rows)}


@router.post(
    "/numbering-schemes/{uuid:scheme_id}/versions",
    response={201: NumberingSchemeOut},
    summary="New draft version of an immutable scheme",
)
@requires("numbering_scheme", "configure")
def new_numbering_version(
    request: HttpRequest, scheme_id: uuid.UUID, payload: NumberingVersionIn
) -> Status[dict[str, Any]]:
    scheme = numbering.new_version(
        services.get_or_404(NumberingScheme, scheme_id), **payload.model_dump()
    )
    services.changed(
        "numbering_scheme",
        scheme.id,
        "version_created",
        after={"version": scheme.version},
        branch_id=scheme.branch_id,
    )
    return Status(201, _scheme_out(scheme))


# --- vocabularies -----------------------------------------------------------------------------------


@router.get("/vocabularies/kinds", response=list[str], summary="The vocabulary kinds of SPEC §10.2")
@requires("vocabulary", "view")
def vocabulary_kinds(request: HttpRequest) -> list[str]:
    return list(vocabularies.KINDS)


@router.get("/vocabularies/{kind}/entries", response=list[VocabularyEntryOut])
@requires("vocabulary", "view")
def list_vocabulary_entries(
    request: HttpRequest,
    kind: str,
    branch_id: uuid.UUID | None = None,
    include_retired: bool = False,
) -> list[dict[str, Any]]:
    qs = VocabularyEntry.objects.filter(kind=kind)
    if branch_id:
        qs = (
            qs.filter(branch_id__in=[branch_id, None])
            if False
            else qs.filter(branch_id=branch_id)
            | VocabularyEntry.objects.filter(kind=kind, branch__isnull=True)
        )
    if not include_retired:
        qs = qs.filter(active=True)
    rows = list(qs.order_by("ord", "code"))
    VocabularyEntry.attach_labels(rows)
    return [_with_labels(r, VocabularyEntryOut) for r in rows]


@router.post("/vocabularies/{kind}/entries", response={201: VocabularyEntryOut})
@requires("vocabulary", "configure")
def create_vocabulary_entry(
    request: HttpRequest, kind: str, payload: VocabularyEntryIn
) -> Status[dict[str, Any]]:
    if kind not in vocabularies.KINDS:
        raise UnprocessableEntity("config.vocabulary.unknown_kind", params={"kind": kind})
    if VocabularyEntry.objects.filter(
        kind=kind, code=payload.code, branch_id=payload.branch_id
    ).exists():
        raise Conflict("config.vocabulary.code_exists", code="vocabulary_code_exists")
    data = payload.model_dump(exclude={"labels"})
    entry = VocabularyEntry.objects.create(kind=kind, **data)
    entry.set_labels(_labels(payload.labels))
    services.changed(
        "vocabulary",
        entry.id,
        "created",
        after={"kind": kind, "code": entry.code},
        branch_id=entry.branch_id,
    )
    return Status(201, _with_labels(entry, VocabularyEntryOut))


@router.patch("/vocabularies/{kind}/entries/{uuid:entry_id}", response=VocabularyEntryOut)
@requires("vocabulary", "configure")
def patch_vocabulary_entry(
    request: HttpRequest, kind: str, entry_id: uuid.UUID, payload: VocabularyEntryPatch
) -> dict[str, Any]:
    entry = services.get_or_404(VocabularyEntry, entry_id)
    data = payload.model_dump(exclude_unset=True)
    labels = data.pop("labels", None)
    for name, value in data.items():
        setattr(entry, name, value)
    entry.save()
    if labels:
        entry.set_labels({k: v for k, v in labels.items() if v})
    services.changed("vocabulary", entry.id, "updated", branch_id=entry.branch_id)
    return _with_labels(entry, VocabularyEntryOut)


@router.post(
    "/vocabularies/{kind}/entries/{uuid:entry_id}:retire",
    response=dict[str, Any],
    summary="Retire an entry; returns where it is used",
)
@requires("vocabulary", "configure")
def retire_vocabulary_entry(request: HttpRequest, kind: str, entry_id: uuid.UUID) -> dict[str, Any]:
    entry = services.get_or_404(VocabularyEntry, entry_id)
    usage = vocabularies.usage_of(entry)
    vocabularies.retire(entry)
    services.changed(
        "vocabulary", entry.id, "retired", after={"usage": usage}, branch_id=entry.branch_id
    )
    return {"id": entry.id, "active": entry.active, "used_by": usage}


# --- workflows --------------------------------------------------------------------------------------


def _workflow_out(w: Workflow) -> dict[str, Any]:
    states = list(w.states.order_by("ord"))
    transitions = list(w.transitions.order_by("ord"))
    type(states[0]).attach_labels(states) if states else None
    type(transitions[0]).attach_labels(transitions) if transitions else None
    return {
        "id": w.id,
        "kind": w.kind,
        "branch_id": w.branch_id,
        "version": w.version,
        "status": w.status,
        "activated_at": w.activated_at,
        "states": [
            {
                "id": s.id,
                "code": s.code,
                "semantic": s.semantic,
                "labels": s.labels,
                "colour": s.colour,
                "is_initial": s.is_initial,
                "is_terminal": s.is_terminal,
                "sla_days": s.sla_days,
                "ord": s.ord,
            }
            for s in states
        ],
        "transitions": [
            {
                "id": t.id,
                "from_state_id": t.from_state_id,
                "to_state_id": t.to_state_id,
                "required_action": t.required_action,
                "guards": t.guards,
                "effects": t.effects,
                "labels": t.labels,
                "ord": t.ord,
            }
            for t in transitions
        ],
    }


@router.get(
    "/workflows/semantics",
    response=dict[str, Any],
    summary="Semantics per kind, guard and effect catalogues (for the editor)",
)
@requires("workflow", "view")
def workflow_catalogue(request: HttpRequest) -> dict[str, Any]:
    return {
        "semantics": {k: list(v) for k, v in workflows.SEMANTICS.items()},
        "guards": sorted(workflows.KNOWN_GUARDS),
        "effects": sorted(workflows.KNOWN_EFFECTS),
    }


@router.get("/workflows", response=list[WorkflowOut])
@requires("workflow", "view")
def list_workflows(
    request: HttpRequest, kind: str | None = None, branch_id: uuid.UUID | None = None
) -> list[dict[str, Any]]:
    qs = Workflow.objects.all().order_by("kind", "-version")
    if kind:
        qs = qs.filter(kind=kind)
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    return [_workflow_out(w) for w in qs]


@router.get("/workflows/{uuid:workflow_id}", response=WorkflowOut)
@requires("workflow", "view")
def get_workflow(request: HttpRequest, workflow_id: uuid.UUID) -> dict[str, Any]:
    return _workflow_out(services.get_or_404(Workflow, workflow_id))


@router.post(
    "/workflows/{uuid:workflow_id}/versions",
    response={201: WorkflowOut},
    summary="Clone into a new draft version",
)
@requires("workflow", "configure")
def new_workflow_version(request: HttpRequest, workflow_id: uuid.UUID) -> Status[dict[str, Any]]:
    return Status(
        201,
        _workflow_out(services.clone_workflow_version(services.get_or_404(Workflow, workflow_id))),
    )


@router.put(
    "/workflows/{uuid:workflow_id}/definition",
    response=WorkflowOut,
    summary="Replace states and transitions of a draft",
)
@requires("workflow", "configure")
def put_workflow_definition(
    request: HttpRequest, workflow_id: uuid.UUID, payload: WorkflowDefinitionIn
) -> dict[str, Any]:
    workflow = services.replace_definition(
        services.get_or_404(Workflow, workflow_id),
        [s.model_dump() for s in payload.states],
        [t.model_dump() for t in payload.transitions],
    )
    return _workflow_out(workflow)


@router.post("/workflows/{uuid:workflow_id}:validate", response=list[dict[str, Any]])
@requires("workflow", "view")
def validate_workflow(request: HttpRequest, workflow_id: uuid.UUID) -> list[dict[str, Any]]:
    return [
        {"message_key": p.message_key, "params": p.params}
        for p in workflows.validate_workflow(services.get_or_404(Workflow, workflow_id))
    ]


@router.post("/workflows/{uuid:workflow_id}:activate", response=WorkflowOut)
@requires("workflow", "configure")
def activate_workflow(request: HttpRequest, workflow_id: uuid.UUID) -> dict[str, Any]:
    workflow = workflows.activate(services.get_or_404(Workflow, workflow_id))
    services.changed(
        "workflow",
        workflow.id,
        "activated",
        after={"kind": workflow.kind, "version": workflow.version},
    )
    return _workflow_out(workflow)


@router.post(
    "/workflows/{uuid:workflow_id}:simulate",
    response=list[dict[str, Any]],
    summary="Dry run of a sequence of actions",
)
@requires("workflow", "view")
def simulate_workflow(
    request: HttpRequest, workflow_id: uuid.UUID, payload: SimulateIn
) -> list[dict[str, Any]]:
    return workflows.simulate(services.get_or_404(Workflow, workflow_id), payload.actions)


# --- payment terms ----------------------------------------------------------------------------------


@router.get("/payment-terms-templates", response=list[PaymentTermsOut])
@requires("payment_terms_template", "view")
def list_payment_terms(
    request: HttpRequest, branch_id: uuid.UUID | None = None
) -> list[dict[str, Any]]:
    qs = PaymentTermsTemplate.objects.all()
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    rows = list(qs.order_by("-is_default", "code"))
    PaymentTermsTemplate.attach_labels(rows)
    return [_with_labels(r, PaymentTermsOut) for r in rows]


@router.post("/payment-terms-templates", response={201: PaymentTermsOut})
@requires("payment_terms_template", "configure")
def create_payment_terms(request: HttpRequest, payload: PaymentTermsIn) -> Status[dict[str, Any]]:
    template = services.create_payment_terms(
        branch_id=payload.branch_id,
        code=payload.code,
        labels=_labels(payload.labels),
        is_default=payload.is_default,
        milestones=[m.model_dump(mode="json") for m in payload.milestones],
    )
    return Status(201, _with_labels(template, PaymentTermsOut))


@router.patch("/payment-terms-templates/{uuid:template_id}", response=PaymentTermsOut)
@requires("payment_terms_template", "configure")
def patch_payment_terms(
    request: HttpRequest, template_id: uuid.UUID, payload: PaymentTermsPatch
) -> dict[str, Any]:
    data = payload.model_dump(exclude_unset=True, mode="json")
    template = services.update_payment_terms(
        services.get_or_404(PaymentTermsTemplate, template_id), data
    )
    return _with_labels(template, PaymentTermsOut)


@router.post("/payment-terms-templates/{uuid:template_id}:set-default", response=PaymentTermsOut)
@requires("payment_terms_template", "configure")
def set_default_payment_terms(request: HttpRequest, template_id: uuid.UUID) -> dict[str, Any]:
    return _with_labels(
        services.set_default_payment_terms(services.get_or_404(PaymentTermsTemplate, template_id)),
        PaymentTermsOut,
    )


@router.get(
    "/payment-terms-templates/{uuid:template_id}/amounts",
    response=list[Decimal],
    summary="Milestone amounts for a total",
)
@requires("payment_terms_template", "view")
def payment_terms_amounts(
    request: HttpRequest, template_id: uuid.UUID, total: Decimal
) -> list[Decimal]:
    template = services.get_or_404(PaymentTermsTemplate, template_id)
    return payment_terms.compute_amounts(template.milestones, total)


# --- catalog ----------------------------------------------------------------------------------------


@router.get("/service-categories", response=list[CategoryOut])
@requires("service_category", "view")
def list_categories(request: HttpRequest) -> list[dict[str, Any]]:
    rows = list(ServiceCategory.objects.order_by("ord", "code"))
    ServiceCategory.attach_labels(rows)
    return [_with_labels(r, CategoryOut) for r in rows]


@router.post("/service-categories", response={201: CategoryOut})
@requires("service_category", "configure")
def create_category(request: HttpRequest, payload: CategoryIn) -> Status[dict[str, Any]]:
    if ServiceCategory.objects.filter(code=payload.code).exists():
        raise Conflict("config.service_category.code_exists", code="category_code_exists")
    category = ServiceCategory.objects.create(**payload.model_dump(exclude={"labels"}))
    category.set_labels(_labels(payload.labels))
    services.changed("service_category", category.id, "created", after={"code": category.code})
    return Status(201, _with_labels(category, CategoryOut))


@router.get("/services", response=list[ServiceOut])
@requires("service", "view")
def list_services(
    request: HttpRequest,
    kind: str | None = None,
    category_id: uuid.UUID | None = None,
    include_inactive: bool = False,
) -> list[dict[str, Any]]:
    qs = Service.objects.all()
    if kind:
        qs = qs.filter(kind=kind)
    if category_id:
        qs = qs.filter(category_id=category_id)
    if not include_inactive:
        qs = qs.filter(active=True)
    rows = list(qs.order_by("code"))
    Service.attach_labels(rows)
    return [_with_labels(r, ServiceOut) for r in rows]


@router.post("/services", response={201: ServiceOut})
@requires("service", "configure")
def create_service(request: HttpRequest, payload: ServiceIn) -> Status[dict[str, Any]]:
    if Service.objects.filter(code=payload.code).exists():
        raise Conflict("config.service.code_exists", code="service_code_exists")
    if payload.kind == "LAB_TEST" and not payload.test_definition_code:
        raise UnprocessableEntity(
            "config.service.test_definition_required",
            details=[{"loc": ["test_definition_code"], "msg": "required for LAB_TEST"}],
        )
    service = Service.objects.create(**payload.model_dump(exclude={"labels"}))
    service.set_labels(_labels(payload.labels))
    services.changed(
        "service", service.id, "created", after={"code": service.code, "kind": service.kind}
    )
    return Status(201, _with_labels(service, ServiceOut))


@router.patch("/services/{uuid:service_id}", response=ServiceOut)
@requires("service", "configure")
def patch_service(
    request: HttpRequest, service_id: uuid.UUID, payload: ServicePatch
) -> dict[str, Any]:
    service = services.get_or_404(Service, service_id)
    data = payload.model_dump(exclude_unset=True)
    labels = data.pop("labels", None)
    for name, value in data.items():
        setattr(service, name, value)
    service.save()
    if labels:
        service.set_labels({k: v for k, v in labels.items() if v})
    services.changed("service", service.id, "updated")
    return _with_labels(service, ServiceOut)


@router.post("/services/{uuid:service_id}:retire", response=ServiceOut)
@requires("service", "configure")
def retire_service(request: HttpRequest, service_id: uuid.UUID) -> dict[str, Any]:
    service = services.get_or_404(Service, service_id)
    service.active = False
    service.save(update_fields=["active"])
    services.changed("service", service.id, "retired")
    return _with_labels(service, ServiceOut)


@router.get("/specimen-types", response=list[SpecimenTypeOut])
@requires("specimen_type", "view")
def list_specimen_types(request: HttpRequest) -> list[dict[str, Any]]:
    rows = list(SpecimenType.objects.order_by("code"))
    SpecimenType.attach_labels(rows)
    return [_with_labels(r, SpecimenTypeOut) for r in rows]


@router.post("/specimen-types", response={201: SpecimenTypeOut})
@requires("specimen_type", "configure")
def create_specimen_type(request: HttpRequest, payload: SpecimenTypeIn) -> Status[dict[str, Any]]:
    if payload.shape not in ("CYLINDER", "CUBE", "PRISM", "BLOCK"):
        raise UnprocessableEntity(
            "config.specimen_type.unknown_shape", details=[{"loc": ["shape"], "msg": payload.shape}]
        )
    if SpecimenType.objects.filter(code=payload.code).exists():
        raise Conflict("config.specimen_type.code_exists", code="specimen_type_code_exists")
    row = SpecimenType.objects.create(**payload.model_dump(exclude={"labels"}))
    row.set_labels(_labels(payload.labels))
    services.changed("specimen_type", row.id, "created", after={"code": row.code})
    return Status(201, _with_labels(row, SpecimenTypeOut))


@router.get("/sieve-sets", response=list[SieveSetOut])
@requires("sieve_set", "view")
def list_sieve_sets(request: HttpRequest) -> list[dict[str, Any]]:
    rows = list(SieveSet.objects.order_by("code"))
    SieveSet.attach_labels(rows)
    return [_with_labels(r, SieveSetOut) for r in rows]


@router.post("/sieve-sets", response={201: SieveSetOut})
@requires("sieve_set", "configure")
def create_sieve_set(request: HttpRequest, payload: SieveSetIn) -> Status[dict[str, Any]]:
    if sorted(payload.sizes_mm, reverse=True) != payload.sizes_mm:
        raise UnprocessableEntity(
            "config.sieve_set.sizes_must_descend",
            details=[{"loc": ["sizes_mm"], "msg": "descending order"}],
        )
    if SieveSet.objects.filter(code=payload.code).exists():
        raise Conflict("config.sieve_set.code_exists", code="sieve_set_code_exists")
    row = SieveSet.objects.create(**payload.model_dump(exclude={"labels"}))
    row.set_labels(_labels(payload.labels))
    services.changed("sieve_set", row.id, "created", after={"code": row.code})
    return Status(201, _with_labels(row, SieveSetOut))


# --- test definitions -------------------------------------------------------------------------------


@router.get(
    "/test-definitions",
    response=list[TestDefinitionOut],
    summary="Definitions (latest version per code unless all_versions)",
)
@requires("test_definition", "view")
def list_test_definitions(
    request: HttpRequest, status: str | None = None, all_versions: bool = False
) -> list[dict[str, Any]]:
    qs = TestDefinition.objects.all().order_by("code", "-version")
    if status:
        qs = qs.filter(status=status)
    rows = list(qs)
    if not all_versions:
        seen: set[str] = set()
        latest = []
        for r in rows:
            if r.code not in seen:
                seen.add(r.code)
                latest.append(r)
        rows = latest
    TestDefinition.attach_labels(rows)
    return [_with_labels(r, TestDefinitionOut) for r in rows]


@router.get("/test-definitions/{uuid:definition_id}", response=TestDefinitionOut)
@requires("test_definition", "view")
def get_test_definition(request: HttpRequest, definition_id: uuid.UUID) -> dict[str, Any]:
    return _with_labels(services.get_or_404(TestDefinition, definition_id), TestDefinitionOut)


@router.post(
    "/test-definitions", response={201: TestDefinitionOut}, summary="Create version 1 (draft)"
)
@requires("test_definition", "configure")
def create_test_definition(
    request: HttpRequest, payload: TestDefinitionIn
) -> Status[dict[str, Any]]:
    definition = services.create_definition(
        payload.model_dump(exclude={"labels"}), _labels(payload.labels)
    )
    return Status(201, _with_labels(definition, TestDefinitionOut))


@router.post(
    "/test-definitions/{uuid:definition_id}/versions",
    response={201: TestDefinitionOut},
    summary="New draft version with changes",
)
@requires("test_definition", "configure")
def new_test_definition_version(
    request: HttpRequest, definition_id: uuid.UUID, payload: TestDefinitionVersionIn
) -> Status[dict[str, Any]]:
    changes = payload.model_dump(exclude_unset=True)
    labels = changes.pop("labels", None)
    definition = services.new_definition_version(
        services.get_or_404(TestDefinition, definition_id),
        changes,
        {k: v for k, v in (labels or {}).items() if v} or None,
    )
    return Status(201, _with_labels(definition, TestDefinitionOut))


@router.post("/test-definitions/{uuid:definition_id}:activate", response=TestDefinitionOut)
@requires("test_definition", "configure")
def activate_test_definition(request: HttpRequest, definition_id: uuid.UUID) -> dict[str, Any]:
    return _with_labels(
        services.activate_definition(services.get_or_404(TestDefinition, definition_id)),
        TestDefinitionOut,
    )


def _run_sandbox(spec: dict[str, Any], data: SandboxDataIn) -> dict[str, Any]:
    def subjects(rows: list[Any]) -> list[Subject]:
        return [
            Subject(
                id=r.id,
                inputs=dict(r.inputs),
                properties=services.specimen_properties(r.specimen_type_code, dict(r.properties)),
                status=r.status,
            )
            for r in rows
        ]

    run = RunData(
        subjects=subjects(data.subjects),
        run=dict(data.run),
        intake=dict(data.intake),
        series=subjects(data.series),
        portions=subjects(data.portions),
    )
    result = evaluate_definition(spec, run)
    return {
        "subjects": [
            {
                "id": s.id,
                "computed": s.computed,
                "excluded": s.excluded,
                "exclusion_reason": s.exclusion_reason,
                "status": s.status,
            }
            for s in run.subjects
        ],
        "series": [{"id": s.id, "computed": s.computed} for s in run.series],
        "portions": [{"id": s.id, "computed": s.computed} for s in run.portions],
        "run_computed": result.run_computed,
        "aggregates": result.aggregates,
        "flags": [
            {"code": f.code, "labels": f.labels, "target": f.target_subject_id}
            for f in result.flags
        ],
        "blocks": [{"code": b.code, "labels": b.labels} for b in result.blocks],
        "exclusions": [{"code": e.code, "target": e.target_subject_id} for e in result.exclusions],
        "problems": [
            {"message_key": p.message_key, "params": p.params, "where": p.where}
            for p in result.problems
        ],
        "blocked": result.blocked,
    }


@router.post(
    "/test-definitions/{uuid:definition_id}:sandbox",
    response=dict[str, Any],
    summary="Evaluate a stored definition on sample data",
)
@requires("test_definition", "configure")
def sandbox_test_definition(
    request: HttpRequest, definition_id: uuid.UUID, payload: SandboxDataIn
) -> dict[str, Any]:
    definition = services.get_or_404(TestDefinition, definition_id)
    return _run_sandbox(definition.as_spec(), payload)


@router.post(
    "/test-definitions:sandbox",
    response=dict[str, Any],
    summary="Evaluate an unsaved definition on sample data",
)
@requires("test_definition", "configure")
def sandbox_definition(request: HttpRequest, payload: SandboxIn) -> dict[str, Any]:
    if payload.definition is None:
        raise UnprocessableEntity("config.test_definition.required")
    spec = payload.definition.model_dump(exclude={"labels"})
    problems = services.validate_definition(spec)
    if problems:
        raise UnprocessableEntity("config.test_definition.invalid", details=problems)
    return _run_sandbox(spec, payload.data)


# --- prices and taxes -------------------------------------------------------------------------------


def _price_out(price: Price, currency: str) -> dict[str, Any]:
    return {
        "id": price.id,
        "price_list_id": price.price_list_id,
        "service_id": price.service_id,
        "specimen_type_id": price.specimen_type_id,
        "unit_price": price.unit_price,
        "min_qty": price.min_qty,
        "currency": currency,
    }


@router.get("/price-lists", response=list[PriceListOut])
@requires("price_list", "view")
def list_price_lists(
    request: HttpRequest, branch_id: uuid.UUID | None = None
) -> list[dict[str, Any]]:
    qs = PriceList.objects.all()
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    rows = list(qs.order_by("code"))
    PriceList.attach_labels(rows)
    return [_with_labels(r, PriceListOut, prices_count=r.prices.count()) for r in rows]


@router.post("/price-lists", response={201: PriceListOut})
@requires("price_list", "configure")
def create_price_list(request: HttpRequest, payload: PriceListIn) -> Status[dict[str, Any]]:
    if PriceList.objects.filter(branch_id=payload.branch_id, code=payload.code).exists():
        raise Conflict("config.price_list.code_exists", code="price_list_code_exists")
    row = PriceList.objects.create(**payload.model_dump(exclude={"labels"}))
    row.set_labels(_labels(payload.labels))
    services.changed(
        "price_list", row.id, "created", after={"code": row.code}, branch_id=row.branch_id
    )
    return Status(201, _with_labels(row, PriceListOut, prices_count=0))


@router.post(
    "/price-lists/{uuid:price_list_id}/prices:import",
    response=dict[str, Any],
    summary="Import price rows (transactional per file)",
)
@requires("price_list", "configure")
def import_prices(
    request: HttpRequest, price_list_id: uuid.UUID, payload: PriceImportIn
) -> dict[str, Any]:
    price_list = services.get_or_404(PriceList, price_list_id)
    imported, errors = services.import_prices(price_list, [r.model_dump() for r in payload.rows])
    return {"imported": imported, "errors": errors}


@router.get("/price-lists/{uuid:price_list_id}/prices", response=list[PriceOut])
@requires("price_list", "view")
def list_prices(request: HttpRequest, price_list_id: uuid.UUID) -> list[dict[str, Any]]:
    price_list = services.get_or_404(PriceList, price_list_id)
    return [_price_out(p, price_list.currency) for p in Price.objects.filter(price_list=price_list)]


@router.get(
    "/prices/resolve",
    response=PriceOut | None,
    summary="Applicable unit price (account → tier → branch default)",
)
@requires("price_list", "view")
def resolve_price_endpoint(
    request: HttpRequest,
    service_id: uuid.UUID,
    branch_id: uuid.UUID,
    on: dt.date | None = None,
    account_id: uuid.UUID | None = None,
    client_tier_id: uuid.UUID | None = None,
    specimen_type_id: uuid.UUID | None = None,
    quantity: Decimal = Decimal(1),
) -> dict[str, Any] | None:
    price = resolve_price(
        service_id=service_id,
        branch_id=branch_id,
        on=on or dt.date.today(),
        account_id=account_id,
        client_tier_id=client_tier_id,
        specimen_type_id=specimen_type_id,
        quantity=quantity,
    )
    if price is None:
        return None
    return _price_out(price, price.price_list.currency)


@router.get("/tax-rules", response=list[TaxRuleOut])
@requires("tax_rule", "view")
def list_tax_rules(
    request: HttpRequest, branch_id: uuid.UUID | None = None
) -> list[dict[str, Any]]:
    qs = TaxRule.objects.all()
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    rows = list(qs.order_by("code"))
    TaxRule.attach_labels(rows)
    return [_with_labels(r, TaxRuleOut) for r in rows]


@router.post("/tax-rules", response={201: TaxRuleOut})
@requires("tax_rule", "configure")
def create_tax_rule(request: HttpRequest, payload: TaxRuleIn) -> Status[dict[str, Any]]:
    if TaxRule.objects.filter(branch_id=payload.branch_id, code=payload.code).exists():
        raise Conflict("config.tax_rule.code_exists", code="tax_rule_code_exists")
    row = TaxRule.objects.create(**payload.model_dump(exclude={"labels"}))
    row.set_labels(_labels(payload.labels))
    services.changed(
        "tax_rule",
        row.id,
        "created",
        after={"code": row.code, "rate": str(row.rate)},
        branch_id=row.branch_id,
    )
    return Status(201, _with_labels(row, TaxRuleOut))


@router.patch("/tax-rules/{uuid:rule_id}", response=TaxRuleOut)
@requires("tax_rule", "configure")
def patch_tax_rule(
    request: HttpRequest, rule_id: uuid.UUID, payload: TaxRulePatch
) -> dict[str, Any]:
    rule = services.get_or_404(TaxRule, rule_id)
    data = payload.model_dump(exclude_unset=True)
    labels = data.pop("labels", None)
    for name, value in data.items():
        setattr(rule, name, value)
    rule.save()
    if labels:
        rule.set_labels({k: v for k, v in labels.items() if v})
    services.changed("tax_rule", rule.id, "updated", branch_id=rule.branch_id)
    return _with_labels(rule, TaxRuleOut)
