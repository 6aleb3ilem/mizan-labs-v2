from django.contrib import admin

from mizan.apps.identity.models import ApiKey, Grant, Membership, RefreshToken, Role, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("email", "display_name", "realm", "status", "tenant_id", "is_staff")
    list_filter = ("realm", "status", "is_staff")
    search_fields = ("email", "display_name")
    ordering = ("email",)
    readonly_fields = ("password", "created_at", "updated_at", "last_login")


class GrantInline(admin.TabularInline):  # type: ignore[type-arg]
    model = Grant
    extra = 0


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("code", "status", "is_template", "tenant_id")
    inlines = [GrantInline]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("user", "role", "branch", "department", "account_id", "status")


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("user", "session_id", "issued_at", "expires_at", "used_at", "revoked_at")


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("name", "prefix", "role", "expires_at", "last_used_at")
