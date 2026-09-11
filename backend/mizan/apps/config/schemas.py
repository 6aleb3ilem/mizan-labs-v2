import datetime as dt
import uuid
from decimal import Decimal
from typing import Any

from ninja import Schema
from pydantic import Field

from mizan.platform.api.schemas import LabelsSchema

CODE = r"^[A-Z0-9_.-]{2,64}$"


class NumberingSchemeOut(Schema):
    id: uuid.UUID
    branch_id: uuid.UUID
    department_id: uuid.UUID | None
    applies_to: str
    prefix: str
    pattern: str
    reset: str
    gap_policy: str
    allocation: str
    version: int
    status: str
    effective_from: dt.date | None
    immutable: bool
    preview: str | None = None


class NumberingSchemeIn(Schema):
    branch_id: uuid.UUID
    department_id: uuid.UUID | None = None
    applies_to: str
    prefix: str = ""
    pattern: str
    reset: str = "YEARLY"
    gap_policy: str = "TOLERANT"
    allocation: str = "ON_CREATE"


class NumberingVersionIn(Schema):
    prefix: str | None = None
    pattern: str | None = None
    reset: str | None = None
    gap_policy: str | None = None
    allocation: str | None = None


class ReservationIn(Schema):
    numbers: list[str] = Field(min_length=1, max_length=1000)
    reason: str = ""


class VocabularyEntryOut(Schema):
    id: uuid.UUID
    kind: str
    branch_id: uuid.UUID | None
    code: str
    labels: dict[str, str]
    colour: str
    icon: str
    ord: int
    active: bool
    extra: dict[str, Any]


class VocabularyEntryIn(Schema):
    code: str = Field(pattern=CODE)
    labels: LabelsSchema
    branch_id: uuid.UUID | None = None
    colour: str = ""
    icon: str = ""
    ord: int = 0
    extra: dict[str, Any] = {}


class VocabularyEntryPatch(Schema):
    labels: LabelsSchema | None = None
    colour: str | None = None
    icon: str | None = None
    ord: int | None = None
    extra: dict[str, Any] | None = None


class WorkflowStateOut(Schema):
    id: uuid.UUID
    code: str
    semantic: str
    labels: dict[str, str]
    colour: str
    is_initial: bool
    is_terminal: bool
    sla_days: int | None
    ord: int


class WorkflowTransitionOut(Schema):
    id: uuid.UUID
    from_state_id: uuid.UUID | None
    to_state_id: uuid.UUID
    required_action: str
    guards: list[Any]
    effects: list[Any]
    labels: dict[str, str]
    ord: int


class WorkflowOut(Schema):
    id: uuid.UUID
    kind: str
    branch_id: uuid.UUID | None
    version: int
    status: str
    activated_at: dt.datetime | None
    states: list[WorkflowStateOut]
    transitions: list[WorkflowTransitionOut]


class WorkflowStateIn(Schema):
    code: str = Field(pattern=CODE)
    semantic: str
    labels: LabelsSchema
    colour: str = "slate"
    is_initial: bool = False
    is_terminal: bool = False
    sla_days: int | None = None


class WorkflowTransitionIn(Schema):
    from_code: str | None = None
    to_code: str
    required_action: str
    guards: list[Any] = []
    effects: list[Any] = []
    labels: LabelsSchema | None = None


class WorkflowDefinitionIn(Schema):
    states: list[WorkflowStateIn]
    transitions: list[WorkflowTransitionIn]


class SimulateIn(Schema):
    actions: list[str]


class MilestoneIn(Schema):
    order: int = 1
    label: dict[str, str]
    percent: Decimal | None = None
    amount: Decimal | None = None
    trigger: str
    trigger_params: dict[str, Any] = {}
    due_days_after_trigger: int = 0


class PaymentTermsOut(Schema):
    id: uuid.UUID
    branch_id: uuid.UUID
    code: str
    labels: dict[str, str]
    is_default: bool
    active: bool
    milestones: list[dict[str, Any]]


class PaymentTermsIn(Schema):
    branch_id: uuid.UUID
    code: str = Field(pattern=CODE)
    labels: LabelsSchema
    is_default: bool = False
    milestones: list[MilestoneIn]


class PaymentTermsPatch(Schema):
    labels: LabelsSchema | None = None
    active: bool | None = None
    milestones: list[MilestoneIn] | None = None


class CategoryOut(Schema):
    id: uuid.UUID
    parent_id: uuid.UUID | None
    code: str
    labels: dict[str, str]
    department_id: uuid.UUID | None
    ord: int


class CategoryIn(Schema):
    code: str = Field(pattern=CODE)
    labels: LabelsSchema
    parent_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    ord: int = 0


class ServiceOut(Schema):
    id: uuid.UUID
    category_id: uuid.UUID
    code: str
    labels: dict[str, str]
    department_id: uuid.UUID | None
    kind: str
    unit_of_sale: str
    test_definition_code: str
    phase_template_code: str
    equipment_class_code: str
    stock_item_code: str
    active: bool


class ServiceIn(Schema):
    category_id: uuid.UUID
    code: str = Field(pattern=CODE)
    labels: LabelsSchema
    department_id: uuid.UUID | None = None
    kind: str
    unit_of_sale: str = "UNIT"
    test_definition_code: str = ""
    phase_template_code: str = ""
    equipment_class_code: str = ""
    stock_item_code: str = ""


class ServicePatch(Schema):
    labels: LabelsSchema | None = None
    category_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    unit_of_sale: str | None = None
    test_definition_code: str | None = None
    active: bool | None = None


class SpecimenTypeOut(Schema):
    id: uuid.UUID
    code: str
    labels: dict[str, str]
    shape: str
    dims: dict[str, Any]
    derived: dict[str, Any]
    active: bool


class SpecimenTypeIn(Schema):
    code: str = Field(pattern=CODE)
    labels: LabelsSchema
    shape: str
    dims: dict[str, Any]
    derived: dict[str, Any] = {}


class SieveSetOut(Schema):
    id: uuid.UUID
    code: str
    labels: dict[str, str]
    sizes_mm: list[float]
    active: bool


class SieveSetIn(Schema):
    code: str = Field(pattern=CODE)
    labels: LabelsSchema
    sizes_mm: list[float] = Field(min_length=1)


class TestDefinitionOut(Schema):
    id: uuid.UUID
    code: str
    version: int
    status: str
    labels: dict[str, str]
    category_id: uuid.UUID | None
    department_id: uuid.UUID | None
    method_ref: str
    unit_under_test: str
    specimen_type_codes: list[str]
    scheduling: dict[str, Any]
    stages: list[dict[str, Any]]
    intake_fields: list[dict[str, Any]]
    inputs: list[dict[str, Any]]
    computed: list[dict[str, Any]]
    aggregates: list[dict[str, Any]]
    rules: list[dict[str, Any]]
    required_equipment_class_code: str
    report_template_code: str
    report_columns: list[str]
    unit_of_sale: str
    locked: bool


class TestDefinitionIn(Schema):
    code: str = Field(pattern=CODE)
    labels: LabelsSchema
    category_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    method_ref: str = ""
    unit_under_test: str
    specimen_type_codes: list[str] = []
    scheduling: dict[str, Any] = {"type": "NONE"}
    stages: list[dict[str, Any]] = []
    intake_fields: list[dict[str, Any]] = []
    inputs: list[dict[str, Any]] = []
    computed: list[dict[str, Any]] = []
    aggregates: list[dict[str, Any]] = []
    rules: list[dict[str, Any]] = []
    required_equipment_class_code: str = ""
    report_template_code: str = ""
    report_columns: list[str] = []
    unit_of_sale: str = "PER_SPECIMEN"


class TestDefinitionVersionIn(Schema):
    labels: LabelsSchema | None = None
    scheduling: dict[str, Any] | None = None
    stages: list[dict[str, Any]] | None = None
    intake_fields: list[dict[str, Any]] | None = None
    inputs: list[dict[str, Any]] | None = None
    computed: list[dict[str, Any]] | None = None
    aggregates: list[dict[str, Any]] | None = None
    rules: list[dict[str, Any]] | None = None
    report_columns: list[str] | None = None
    method_ref: str | None = None
    specimen_type_codes: list[str] | None = None


class SandboxSubjectIn(Schema):
    id: str
    inputs: dict[str, Any]
    specimen_type_code: str | None = None
    properties: dict[str, Any] = {}
    status: str = "OK"


class SandboxDataIn(Schema):
    subjects: list[SandboxSubjectIn] = []
    run: dict[str, Any] = {}
    intake: dict[str, Any] = {}
    series: list[SandboxSubjectIn] = []
    portions: list[SandboxSubjectIn] = []


class SandboxIn(Schema):
    definition: TestDefinitionIn | None = None
    data: SandboxDataIn


class PriceListOut(Schema):
    id: uuid.UUID
    branch_id: uuid.UUID
    code: str
    labels: dict[str, str]
    currency: str
    valid_from: dt.date
    valid_to: dt.date | None
    client_tier_id: uuid.UUID | None
    account_id: uuid.UUID | None
    status: str
    prices_count: int = 0


class PriceListIn(Schema):
    branch_id: uuid.UUID
    code: str = Field(pattern=CODE)
    labels: LabelsSchema
    currency: str = Field(min_length=3, max_length=3)
    valid_from: dt.date
    valid_to: dt.date | None = None
    client_tier_id: uuid.UUID | None = None
    account_id: uuid.UUID | None = None


class PriceRowIn(Schema):
    service_code: str
    specimen_type_code: str | None = None
    unit_price: Decimal
    min_qty: Decimal = Decimal(1)


class PriceImportIn(Schema):
    rows: list[PriceRowIn]


class PriceOut(Schema):
    id: uuid.UUID
    price_list_id: uuid.UUID
    service_id: uuid.UUID
    specimen_type_id: uuid.UUID | None
    unit_price: Decimal
    min_qty: Decimal
    currency: str


class TaxRuleOut(Schema):
    id: uuid.UUID
    branch_id: uuid.UUID
    code: str
    labels: dict[str, str]
    rate: Decimal
    applies_to_kinds: list[str]
    active: bool


class TaxRuleIn(Schema):
    branch_id: uuid.UUID
    code: str = Field(pattern=CODE)
    labels: LabelsSchema
    rate: Decimal = Field(ge=0, le=100)
    applies_to_kinds: list[str] = []


class TaxRulePatch(Schema):
    labels: LabelsSchema | None = None
    rate: Decimal | None = None
    applies_to_kinds: list[str] | None = None
    active: bool | None = None
