from django.contrib import admin

from mizan.apps.org.models import Branch, Department, Signatory, Tenant, TreasuryAccount


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("code", "name", "plan", "status", "created_at")
    search_fields = ("code", "name")


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("code", "legal_name", "currency", "timezone", "active", "tenant_id")
    search_fields = ("code", "legal_name")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("code", "branch", "active", "ord")


@admin.register(Signatory)
class SignatoryAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("display_name", "branch", "mode", "active")


@admin.register(TreasuryAccount)
class TreasuryAccountAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("label", "branch", "type", "currency", "printed_on_invoices", "active")
