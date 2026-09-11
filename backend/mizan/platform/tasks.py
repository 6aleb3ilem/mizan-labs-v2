"""Procrastinate tasks owned by the platform: event dispatch (auto-discovered)."""

from __future__ import annotations

import logging
from typing import Any

from procrastinate import RetryStrategy
from procrastinate.contrib.django import app

from mizan.platform import context
from mizan.platform.db.tenancy import platform_scope, tenant_scope
from mizan.platform.events import Event, get_handler

log = logging.getLogger("mizan.tasks")


def run_handler(event_data: dict[str, Any], handler_name: str) -> None:
    """Execute one handler for one event under the event's tenant scope, as the system actor."""
    event = Event.from_dict(event_data)
    handler = get_handler(handler_name)
    token = context.current_actor.set(context.Actor.system())
    try:
        if event.tenant_id is not None:
            with tenant_scope(event.tenant_id):
                handler.func(event)
        else:
            with platform_scope():
                handler.func(event)
    finally:
        context.current_actor.reset(token)


@app.task(
    name="mizan.events.dispatch",
    queue="events",
    retry=RetryStrategy(max_attempts=5, wait=5, exponential_wait=2),
)
def dispatch_event(event: dict[str, Any], handler: str) -> None:
    log.info(
        "dispatch %s -> %s", event.get("code"), handler, extra={"task": "mizan.events.dispatch"}
    )
    run_handler(event, handler)
