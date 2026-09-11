from django.contrib import admin

from mizan.apps.audit.models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = (
        "at",
        "aggregate_type",
        "aggregate_id",
        "action",
        "actor_type",
        "actor_id",
        "tenant_id",
    )
    list_filter = ("aggregate_type", "action", "actor_type")
    search_fields = ("aggregate_id", "actor_id")
    readonly_fields = [f.name for f in AuditEvent._meta.fields]

    def has_change_permission(self, request, obj=None):  # type: ignore[no-untyped-def]
        return False

    def has_delete_permission(self, request, obj=None):  # type: ignore[no-untyped-def]
        return False
