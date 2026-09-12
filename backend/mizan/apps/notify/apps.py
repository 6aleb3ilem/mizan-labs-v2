from django.apps import AppConfig


class NotifyConfig(AppConfig):
    name = "mizan.apps.notify"
    label = "notify"
    verbose_name = "Notifications"

    def ready(self) -> None:
        # Register the event handler and the periodic digest job.
        from mizan.apps.notify import digest, dispatch  # noqa: F401
