from django.contrib import admin

from mizan.apps.config import models as m


@admin.register(m.NumberingScheme)
class NumberingSchemeAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = (
        "applies_to",
        "branch",
        "department",
        "pattern",
        "version",
        "status",
        "immutable",
    )


@admin.register(m.VocabularyEntry)
class VocabularyEntryAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("kind", "code", "ord", "active", "branch")
    list_filter = ("kind", "active")


class WorkflowStateInline(admin.TabularInline):  # type: ignore[type-arg]
    model = m.WorkflowState
    extra = 0


class WorkflowTransitionInline(admin.TabularInline):  # type: ignore[type-arg]
    model = m.WorkflowTransition
    extra = 0


@admin.register(m.Workflow)
class WorkflowAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("kind", "version", "status", "branch")
    inlines = [WorkflowStateInline, WorkflowTransitionInline]


@admin.register(m.PaymentTermsTemplate)
class PaymentTermsTemplateAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("code", "branch", "is_default", "active")


@admin.register(m.ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("code", "parent", "department", "ord")


@admin.register(m.Service)
class ServiceAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("code", "kind", "category", "unit_of_sale", "active")


@admin.register(m.TestDefinition)
class TestDefinitionAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("code", "version", "status", "unit_under_test", "locked")


@admin.register(m.SpecimenType)
class SpecimenTypeAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("code", "shape", "dims", "active")


@admin.register(m.SieveSet)
class SieveSetAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("code", "sizes_mm")


@admin.register(m.PriceList)
class PriceListAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("code", "branch", "currency", "valid_from", "valid_to", "status")


@admin.register(m.Price)
class PriceAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("price_list", "service", "specimen_type", "unit_price", "min_qty")


@admin.register(m.TaxRule)
class TaxRuleAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("code", "branch", "rate", "active")
