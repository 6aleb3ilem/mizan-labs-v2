from django.apps import AppConfig


class CliConfig(AppConfig):
    """Management commands that need the whole project (API document, scheduler, seeds)."""

    name = "mizan.cli"
    label = "cli"
    verbose_name = "Command line"
