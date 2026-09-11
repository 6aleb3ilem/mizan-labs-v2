from django.contrib import admin

from mizan.apps.identity.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("email", "display_name", "realm", "status", "tenant_id", "is_staff")
    list_filter = ("realm", "status", "is_staff")
    search_fields = ("email", "display_name")
    ordering = ("email",)
    readonly_fields = ("password", "created_at", "updated_at", "last_login")
