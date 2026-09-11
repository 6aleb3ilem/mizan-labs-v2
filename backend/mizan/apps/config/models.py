"""Configuration subsystems (SPEC §10): numbering, vocabularies, workflows, catalog, tests, prices, payment terms."""

from __future__ import annotations

import uuid

from django.db import models

from mizan.platform import context
from mizan.platform.db import CodeField, TenantModel
from mizan.platform.ids import uuid7
from mizan.platform.labels import LabelledModel


def _default_tenant_id() -> uuid.UUID | None:
    return context.current_tenant_id.get()


class ConfigStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    RETIRED = "RETIRED", "Retired"


# --- numbering (§10.1) ----------------------------------------------------------------------


class NumberingKind(models.TextChoices):
    ACCOUNT = "ACCOUNT", "Account"
    PROJECT = "PROJECT", "Project"
    QUOTE = "QUOTE", "Quote"
    ORDER = "ORDER", "Order"
    CONTRACT = "CONTRACT", "Contract"
    INTAKE = "INTAKE", "Intake"
    SAMPLE = "SAMPLE", "Sample"
    SPECIMEN = "SPECIMEN", "Specimen"
    TEST_RUN = "TEST_RUN", "Test run"
    REPORT = "REPORT", "Report"
    INVOICE = "INVOICE", "Invoice"
    CREDIT_NOTE = "CREDIT_NOTE", "Credit note"
    PAYMENT = "PAYMENT", "Payment"
    RENTAL = "RENTAL", "Rental"
    SALE = "SALE", "Sale"
    OUTING = "OUTING", "Outing"
    TRANSFER = "TRANSFER", "Transfer"
    WORK_ORDER = "WORK_ORDER", "Work order"
    EQUIPMENT = "EQUIPMENT", "Equipment"
    MAINTENANCE = "MAINTENANCE", "Maintenance"


class NumberingReset(models.TextChoices):
    NEVER = "NEVER", "Never"
    YEARLY = "YEARLY", "Yearly"
    MONTHLY = "MONTHLY", "Monthly"


class GapPolicy(models.TextChoices):
    GAP_FREE = "GAP_FREE", "Gap-free"
    TOLERANT = "TOLERANT", "Tolerant"


class Allocation(models.TextChoices):
    ON_CREATE = "ON_CREATE", "On create"
    ON_ISSUE = "ON_ISSUE", "On issue"


class NumberingScheme(TenantModel):
    branch = models.ForeignKey(
        "org.Branch", on_delete=models.PROTECT, related_name="numbering_schemes"
    )
    department = models.ForeignKey(
        "org.Department",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="numbering_schemes",
    )
    applies_to = models.CharField(max_length=32, choices=NumberingKind.choices)
    prefix = models.CharField(max_length=16, blank=True, default="")
    pattern = models.CharField(max_length=120)
    reset = models.CharField(
        max_length=16, choices=NumberingReset.choices, default=NumberingReset.YEARLY
    )
    gap_policy = models.CharField(
        max_length=16, choices=GapPolicy.choices, default=GapPolicy.TOLERANT
    )
    allocation = models.CharField(
        max_length=16, choices=Allocation.choices, default=Allocation.ON_CREATE
    )
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=16, choices=ConfigStatus.choices, default=ConfigStatus.DRAFT
    )
    effective_from = models.DateField(null=True, blank=True)
    immutable = models.BooleanField(default=False)  # true once a number has been allocated
    supersedes = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta(TenantModel.Meta):
        db_table = "numbering_scheme"
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "department", "applies_to", "version"],
                name="uq_numbering_scheme_version",
                nulls_distinct=False,
            )
        ]

    def __str__(self) -> str:
        return f"{self.applies_to} v{self.version} {self.pattern}"


class NumberingCounter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant_id = models.UUIDField(default=_default_tenant_id, db_index=True)
    scheme = models.ForeignKey(NumberingScheme, on_delete=models.CASCADE, related_name="counters")
    period_key = models.CharField(max_length=16, default="")
    value = models.BigIntegerField(default=0)

    class Meta:
        db_table = "numbering_counter"
        constraints = [
            models.UniqueConstraint(fields=["scheme", "period_key"], name="uq_numbering_counter")
        ]

    def __str__(self) -> str:
        return f"{self.scheme_id}:{self.period_key}={self.value}"


class NumberReservation(models.Model):
    """Numbers already used elsewhere (e.g. continuing a V1 series); skipped by allocation."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant_id = models.UUIDField(default=_default_tenant_id, db_index=True)
    scheme = models.ForeignKey(
        NumberingScheme, on_delete=models.CASCADE, related_name="reservations"
    )
    number = models.CharField(max_length=64)
    reserved_by = models.UUIDField(null=True, blank=True)
    reason = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        db_table = "number_reservation"
        constraints = [
            models.UniqueConstraint(fields=["scheme", "number"], name="uq_number_reservation")
        ]

    def __str__(self) -> str:
        return self.number


# --- vocabularies (§10.2) ---------------------------------------------------------------------


class VocabularyEntry(TenantModel, LabelledModel):
    label_entity = "vocabulary_entry"

    @property
    def label_scope(self) -> str:
        return f"{self.kind!s}/{self.branch_id or 'tenant'}"

    branch = models.ForeignKey(
        "org.Branch", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    kind = models.CharField(max_length=48, db_index=True)
    code = CodeField()
    colour = models.CharField(max_length=32, blank=True, default="")
    icon = models.CharField(max_length=48, blank=True, default="")
    ord = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    extra = models.JSONField(default=dict, blank=True)
    retired_at = models.DateTimeField(null=True, blank=True)

    class Meta(TenantModel.Meta):
        db_table = "vocabulary_entry"
        ordering = ["kind", "ord", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "branch", "kind", "code"],
                name="uq_vocabulary_entry",
                nulls_distinct=False,
            )
        ]

    def __str__(self) -> str:
        return f"{self.kind}:{self.code}"


# --- workflows (§10.3) -------------------------------------------------------------------------


class Workflow(TenantModel):
    branch = models.ForeignKey(
        "org.Branch", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    kind = models.CharField(max_length=32, db_index=True)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=16, choices=ConfigStatus.choices, default=ConfigStatus.DRAFT
    )
    activated_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta(TenantModel.Meta):
        db_table = "workflow"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "branch", "kind", "version"],
                name="uq_workflow_version",
                nulls_distinct=False,
            )
        ]

    def __str__(self) -> str:
        return f"{self.kind} v{self.version} ({self.status})"


class WorkflowState(TenantModel, LabelledModel):
    label_entity = "workflow_state"

    @property
    def label_scope(self) -> str:
        return str(self.workflow_id)

    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="states")
    code = CodeField()
    semantic = models.CharField(max_length=32)
    colour = models.CharField(max_length=32, default="slate")
    is_initial = models.BooleanField(default=False)
    is_terminal = models.BooleanField(default=False)
    sla_days = models.PositiveIntegerField(null=True, blank=True)
    ord = models.PositiveIntegerField(default=0)

    class Meta(TenantModel.Meta):
        db_table = "workflow_state"
        ordering = ["ord", "code"]
        constraints = [
            models.UniqueConstraint(fields=["workflow", "code"], name="uq_workflow_state_code")
        ]

    def __str__(self) -> str:
        return f"{self.code} ({self.semantic})"


class WorkflowTransition(TenantModel, LabelledModel):
    label_entity = "workflow_transition"

    @property
    def label_scope(self) -> str:
        return f"{self.workflow_id}/{self.id}"

    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="transitions")
    from_state = models.ForeignKey(
        WorkflowState,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="transitions_out",
    )  # null: from any non-terminal state
    to_state = models.ForeignKey(
        WorkflowState, on_delete=models.CASCADE, related_name="transitions_in"
    )
    required_action = models.CharField(max_length=64)  # "quote.submit" or "system"
    guards = models.JSONField(default=list, blank=True)
    effects = models.JSONField(default=list, blank=True)
    ord = models.PositiveIntegerField(default=0)

    class Meta(TenantModel.Meta):
        db_table = "workflow_transition"
        ordering = ["ord"]

    def __str__(self) -> str:
        return f"{self.from_state_id or '*'} -> {self.to_state_id} [{self.required_action}]"


# --- payment terms (§10.10) ------------------------------------------------------------------


class PaymentTermsTemplate(TenantModel, LabelledModel):
    label_entity = "payment_terms_template"

    @property
    def label_scope(self) -> str:
        return str(self.branch_id)

    branch = models.ForeignKey(
        "org.Branch", on_delete=models.PROTECT, related_name="payment_terms_templates"
    )
    code = CodeField()
    is_default = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    milestones = models.JSONField(default=list)

    class Meta(TenantModel.Meta):
        db_table = "payment_terms_template"
        constraints = [
            models.UniqueConstraint(fields=["branch", "code"], name="uq_payment_terms_code")
        ]

    def __str__(self) -> str:
        return str(self.code)


# --- catalog (§10.4) ----------------------------------------------------------------------------


class ServiceKind(models.TextChoices):
    LAB_TEST = "LAB_TEST", "Laboratory test"
    FIELD_SERVICE = "FIELD_SERVICE", "Field service"
    STUDY = "STUDY", "Study"
    RENTAL = "RENTAL", "Rental"
    SALE = "SALE", "Sale"
    FEE = "FEE", "Fee"


class ServiceCategory(TenantModel, LabelledModel):
    label_entity = "service_category"

    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="children"
    )
    code = CodeField()
    department = models.ForeignKey(
        "org.Department", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    ord = models.PositiveIntegerField(default=0)

    class Meta(TenantModel.Meta):
        db_table = "service_category"
        ordering = ["ord", "code"]
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "code"], name="uq_service_category_code")
        ]

    def __str__(self) -> str:
        return str(self.code)


class Service(TenantModel, LabelledModel):
    label_entity = "service"

    category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name="services")
    code = CodeField()
    department = models.ForeignKey(
        "org.Department", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    kind = models.CharField(max_length=16, choices=ServiceKind.choices)
    unit_of_sale = models.CharField(max_length=32, default="UNIT")
    test_definition_code = models.CharField(max_length=64, blank=True, default="")
    phase_template_code = models.CharField(max_length=64, blank=True, default="")
    equipment_class_code = models.CharField(max_length=64, blank=True, default="")
    stock_item_code = models.CharField(max_length=64, blank=True, default="")
    active = models.BooleanField(default=True)

    class Meta(TenantModel.Meta):
        db_table = "service"
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "code"], name="uq_service_code")
        ]

    def __str__(self) -> str:
        return str(self.code)


# --- test definitions (§10.5) ------------------------------------------------------------------


class SpecimenType(TenantModel, LabelledModel):
    label_entity = "specimen_type"

    code = CodeField()
    shape = models.CharField(max_length=16)  # CYLINDER | CUBE | PRISM | BLOCK
    dims = models.JSONField(default=dict)  # {d, side, L, W, H}
    derived = models.JSONField(default=dict, blank=True)  # e.g. gross_area, net_factor
    active = models.BooleanField(default=True)

    class Meta(TenantModel.Meta):
        db_table = "specimen_type"
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "code"], name="uq_specimen_type_code")
        ]

    def __str__(self) -> str:
        return str(self.code)

    def properties(self) -> dict[str, object]:
        return {"shape": self.shape, **self.dims, **self.derived}


class SieveSet(TenantModel, LabelledModel):
    label_entity = "sieve_set"

    code = CodeField()
    sizes_mm = models.JSONField(default=list)  # ordered, descending
    active = models.BooleanField(default=True)

    class Meta(TenantModel.Meta):
        db_table = "sieve_set"
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "code"], name="uq_sieve_set_code")
        ]

    def __str__(self) -> str:
        return str(self.code)


class TestDefinition(TenantModel, LabelledModel):
    label_entity = "test_definition"

    @property
    def label_scope(self) -> str:
        return f"{self.code!s}/v{self.version}"

    code = CodeField()
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=16, choices=ConfigStatus.choices, default=ConfigStatus.DRAFT
    )
    category = models.ForeignKey(
        ServiceCategory, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    department = models.ForeignKey(
        "org.Department", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    method_ref = models.CharField(max_length=120, blank=True, default="")
    unit_under_test = models.CharField(max_length=16)  # SPECIMEN | SAMPLE
    specimen_type_codes = models.JSONField(default=list, blank=True)
    scheduling = models.JSONField(default=dict)
    stages = models.JSONField(default=list)
    intake_fields = models.JSONField(default=list, blank=True)
    inputs = models.JSONField(default=list)
    computed = models.JSONField(default=list)
    aggregates = models.JSONField(default=list, blank=True)
    rules = models.JSONField(default=list, blank=True)
    required_equipment_class_code = models.CharField(max_length=64, blank=True, default="")
    report_template_code = models.CharField(max_length=64, blank=True, default="")
    report_columns = models.JSONField(default=list, blank=True)
    unit_of_sale = models.CharField(max_length=32, default="PER_SPECIMEN")
    locked = models.BooleanField(default=False)  # true once a test run references this version
    activated_at = models.DateTimeField(null=True, blank=True)

    class Meta(TenantModel.Meta):
        db_table = "test_definition"
        ordering = ["code", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "code", "version"], name="uq_test_definition_version"
            )
        ]

    def __str__(self) -> str:
        return f"{self.code} v{self.version}"

    def as_spec(self) -> dict[str, object]:
        return {
            "code": self.code,
            "version": self.version,
            "unit_under_test": self.unit_under_test,
            "scheduling": self.scheduling,
            "stages": self.stages,
            "intake_fields": self.intake_fields,
            "inputs": self.inputs,
            "computed": self.computed,
            "aggregates": self.aggregates,
            "rules": self.rules,
            "report_columns": self.report_columns,
        }


# --- prices and taxes (§10.6) ------------------------------------------------------------------


class PriceList(TenantModel, LabelledModel):
    label_entity = "price_list"

    @property
    def label_scope(self) -> str:
        return str(self.branch_id)

    branch = models.ForeignKey("org.Branch", on_delete=models.PROTECT, related_name="price_lists")
    code = CodeField()
    currency = models.CharField(max_length=3)
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    client_tier = models.ForeignKey(
        VocabularyEntry, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    account_id = models.UUIDField(null=True, blank=True, db_index=True)
    status = models.CharField(
        max_length=16, choices=ConfigStatus.choices, default=ConfigStatus.ACTIVE
    )

    class Meta(TenantModel.Meta):
        db_table = "price_list"
        constraints = [
            models.UniqueConstraint(fields=["branch", "code"], name="uq_price_list_code")
        ]

    def __str__(self) -> str:
        return str(self.code)


class Price(TenantModel):
    price_list = models.ForeignKey(PriceList, on_delete=models.CASCADE, related_name="prices")
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="prices")
    specimen_type = models.ForeignKey(
        SpecimenType, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    unit_price = models.DecimalField(max_digits=18, decimal_places=2)
    min_qty = models.DecimalField(max_digits=12, decimal_places=3, default=1)

    class Meta(TenantModel.Meta):
        db_table = "price"
        constraints = [
            models.UniqueConstraint(
                fields=["price_list", "service", "specimen_type", "min_qty"],
                name="uq_price_row",
                nulls_distinct=False,
            )
        ]

    def __str__(self) -> str:
        return f"{self.service_id} @ {self.unit_price}"


class TaxRule(TenantModel, LabelledModel):
    label_entity = "tax_rule"

    @property
    def label_scope(self) -> str:
        return str(self.branch_id)

    branch = models.ForeignKey("org.Branch", on_delete=models.PROTECT, related_name="tax_rules")
    code = CodeField()
    rate = models.DecimalField(max_digits=5, decimal_places=2)
    applies_to_kinds = models.JSONField(default=list, blank=True)
    active = models.BooleanField(default=True)

    class Meta(TenantModel.Meta):
        db_table = "tax_rule"
        constraints = [models.UniqueConstraint(fields=["branch", "code"], name="uq_tax_rule_code")]

    def __str__(self) -> str:
        return f"{self.code} {self.rate}%"
