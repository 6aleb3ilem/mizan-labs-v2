"""Periodic jobs (SPEC §27.6): a registry ticked every five minutes by the scheduler process.

Apps register a job with ``@periodic("name", every=timedelta(...))``; ``tick()`` runs the jobs
whose interval has elapsed since their last successful start, one after the other, under the
platform bypass (a job iterates over tenants itself). The last run of every job is persisted so
that a restarted scheduler does not re-run everything at once and so that operators can see
failures (``/health/ready`` and the admin).
"""

from __future__ import annotations

import logging
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from mizan.platform import context
from mizan.platform.db.tenancy import platform_scope

log = logging.getLogger("mizan.scheduler")

JobFunc = Callable[[datetime], None]


@dataclass(frozen=True, slots=True)
class PeriodicJob:
    name: str
    every: timedelta
    func: JobFunc


_jobs: dict[str, PeriodicJob] = {}


def periodic(name: str, *, every: timedelta) -> Callable[[JobFunc], JobFunc]:
    """Register ``func(now)`` to run every ``every`` (at least five minutes of granularity)."""

    def decorator(func: JobFunc) -> JobFunc:
        existing = _jobs.get(name)
        if existing is not None and existing.func is not func:
            raise ValueError(f"periodic job {name!r} is already registered")
        _jobs[name] = PeriodicJob(name=name, every=every, func=func)
        return func

    return decorator


def registered_jobs() -> list[PeriodicJob]:
    return sorted(_jobs.values(), key=lambda job: job.name)


def clear_jobs() -> None:
    """Test helper."""
    _jobs.clear()


def is_due(job: PeriodicJob, last_started_at: datetime | None, now: datetime) -> bool:
    if last_started_at is None:
        return True
    return now - last_started_at >= job.every - timedelta(seconds=30)


def tick(now: datetime | None = None, *, only: set[str] | None = None) -> dict[str, str]:
    """Run every due job once. Returns ``{job name: "ran" | "skipped" | "failed"}``."""
    from mizan.platform.models import PeriodicJobRun

    now = now or timezone.now()
    outcomes: dict[str, str] = {}
    token = context.current_actor.set(context.Actor.system())
    try:
        for job in registered_jobs():
            if only is not None and job.name not in only:
                continue
            with platform_scope():
                run, _ = PeriodicJobRun.objects.select_for_update().get_or_create(name=job.name)
                if not is_due(job, run.last_started_at, now):
                    outcomes[job.name] = "skipped"
                    continue
                run.last_started_at = now
                run.save(update_fields=["last_started_at"])
            outcomes[job.name] = _run(job, run, now)
    finally:
        context.current_actor.reset(token)
    return outcomes


def _run(job: PeriodicJob, run: object, now: datetime) -> str:
    from mizan.platform.models import PeriodicJobRun

    assert isinstance(run, PeriodicJobRun)
    try:
        with platform_scope():
            job.func(now)
    except Exception as exc:
        log.exception("periodic job %s failed", job.name)
        with platform_scope(), transaction.atomic():
            PeriodicJobRun.objects.filter(pk=run.pk).update(
                last_finished_at=timezone.now(),
                last_error=f"{exc!r}\n{traceback.format_exc()[-2000:]}",
                failures=run.failures + 1,
            )
        return "failed"
    with platform_scope():
        PeriodicJobRun.objects.filter(pk=run.pk).update(
            last_finished_at=timezone.now(), last_error="", failures=0
        )
    return "ran"
