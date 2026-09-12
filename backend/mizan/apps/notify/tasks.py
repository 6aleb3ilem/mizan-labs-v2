"""Procrastinate tasks of the notify app (auto-discovered)."""

from __future__ import annotations

import logging
import uuid

from procrastinate import RetryStrategy
from procrastinate.contrib.django import app

from mizan.apps.notify import dispatch
from mizan.platform import context

log = logging.getLogger("mizan.notify.tasks")


@app.task(
    name="mizan.notify.deliver",
    queue="notify",
    retry=RetryStrategy(max_attempts=dispatch.MAX_ATTEMPTS, wait=30, exponential_wait=2),
)
def deliver_task(delivery_id: str, tenant_id: str) -> None:
    token = context.current_actor.set(context.Actor.system())
    try:
        dispatch.deliver(uuid.UUID(delivery_id), uuid.UUID(tenant_id))
    finally:
        context.current_actor.reset(token)
