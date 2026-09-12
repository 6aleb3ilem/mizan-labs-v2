from django.contrib import admin

from mizan.apps.notify.models import (
    ContactChannelPreference,
    MessageTemplate,
    Notification,
    NotificationDelivery,
    NotificationRule,
)


@admin.register(NotificationRule)
class NotificationRuleAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("code", "event_code", "channels", "template_code", "active", "tenant_id")
    list_filter = ("active", "event_code")
    search_fields = ("code", "event_code")


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("code", "channel", "locale", "active", "tenant_id")
    list_filter = ("channel", "locale", "active")
    search_fields = ("code", "subject", "body")


@admin.register(ContactChannelPreference)
class ContactChannelPreferenceAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("recipient_type", "recipient_id", "channel", "enabled", "tenant_id")


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("created_at", "event_code", "channel", "recipient_key", "status", "attempts")
    list_filter = ("status", "channel", "event_code")
    search_fields = ("recipient_key", "event_code", "last_error")
    readonly_fields = ("rendered", "context", "recipient")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("created_at", "user", "event_code", "title", "read_at")
    list_filter = ("event_code",)
    search_fields = ("title", "body")
