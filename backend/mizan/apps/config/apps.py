from django.apps import AppConfig


class ConfigAppConfig(AppConfig):
    name = "mizan.apps.config"
    label = "config"
    verbose_name = "Configuration"

    def ready(self) -> None:
        from mizan.apps.config import (
            guards_effects,  # noqa: F401 - registers built-in guards/effects
        )
