from django.contrib import admin

from mizan.apps.documents import models as m


@admin.register(m.DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("kind", "locale", "version", "status", "branch")


@admin.register(m.SigningKey)
class SigningKeyAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("kid", "purpose", "algorithm", "backend", "branch", "status", "valid_from")


@admin.register(m.IssuedDocument)
class IssuedDocumentAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("kind", "number", "status", "issued_at", "branch", "verify_token")
    search_fields = ("number", "verify_token")
    readonly_fields = [f.name for f in m.IssuedDocument._meta.fields]


@admin.register(m.VerificationAttempt)
class VerificationAttemptAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("at", "token", "outcome", "ip_hash")


@admin.register(m.TransparencyHead)
class TransparencyHeadAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("published_at", "tree_size", "root_hash")


@admin.register(m.FraudCase)
class FraudCaseAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("created_at", "token", "state", "reporter_contact")
