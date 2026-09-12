"""The scheduler process: runs the due periodic jobs (SPEC §27.6, Appendix Q).

``--once`` (Cloud Run job, every five minutes from Cloud Scheduler) or a loop for docker-compose.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from mizan.platform import scheduler

log = logging.getLogger("mizan.scheduler")


class Command(BaseCommand):
    help = "Run the periodic jobs that are due (once, or every --interval seconds)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--once", action="store_true", help="run one tick and exit")
        parser.add_argument("--interval", type=int, default=300, help="seconds between ticks")
        parser.add_argument("--only", action="append", default=[], help="restrict to job names")
        parser.add_argument("--list", action="store_true", help="list registered jobs and exit")

    def handle(self, *args: Any, **options: Any) -> None:
        if options["list"]:
            for job in scheduler.registered_jobs():
                self.stdout.write(f"{job.name}\tevery {job.every}")
            return
        only = set(options["only"]) or None
        while True:
            outcomes = scheduler.tick(only=only)
            summary = ", ".join(f"{name}={outcome}" for name, outcome in outcomes.items())
            self.stdout.write(summary or "no periodic jobs registered")
            if options["once"]:
                return
            time.sleep(max(1, int(options["interval"])))
