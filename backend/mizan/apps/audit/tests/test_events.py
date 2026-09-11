"""SPEC §27.4: events in the business transaction; asynchronous handlers via the outbox."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from django.db import transaction
from procrastinate.contrib.django.models import ProcrastinateJob

from mizan.platform import context, events
from mizan.platform.tasks import run_handler

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _isolated_registry() -> Any:
    saved_handlers = dict(events._handlers)
    saved_names = dict(events._by_name)
    events.clear_handlers()
    yield
    events._handlers.clear()
    events._handlers.update(saved_handlers)
    events._by_name.clear()
    events._by_name.update(saved_names)


def test_unknown_event_codes_are_rejected(scoped: Any) -> None:
    with pytest.raises(ValueError):
        events.emit("quote.teleported", aggregate_type="quote")
    with pytest.raises(ValueError):
        events.subscribe("quote.teleported")(lambda e: None)


def test_sync_handlers_run_in_the_transaction_and_async_ones_are_enqueued(scoped: Any) -> None:
    seen: list[str] = []

    @events.subscribe("quote.sent", name="test.sync", sync=True)
    def on_sent(event: events.Event) -> None:
        seen.append(event.code)

    @events.subscribe("quote.sent", name="test.async")
    def later(event: events.Event) -> None:  # pragma: no cover - executed by the worker
        seen.append("never")

    @events.subscribe("*", name="test.everything")
    def everything(event: events.Event) -> None:  # pragma: no cover
        pass

    quote_id = uuid.uuid4()
    event = events.emit(
        "quote.sent", aggregate_type="quote", aggregate_id=quote_id, payload={"number": "DV-1"}
    )
    assert seen == ["quote.sent"]
    assert event.tenant_id == scoped.id
    jobs = ProcrastinateJob.objects.filter(task_name="mizan.events.dispatch").order_by("id")
    assert [j.queueing_lock for j in jobs] == [
        f"{event.id}:test.async",
        f"{event.id}:test.everything",
    ]
    assert jobs[0].args["event"]["payload"] == {"number": "DV-1"}
    assert jobs[0].queue_name == "events"
    # emitting again with the same handler for the same event id would be a no-op (idempotent enqueue)
    events._defer(event, events.get_handler("test.async"))
    assert ProcrastinateJob.objects.filter(queueing_lock=f"{event.id}:test.async").count() == 1


def test_outbox_rolls_back_with_the_business_transaction(scoped: Any) -> None:
    @events.subscribe("project.created", name="test.async2")
    def later(event: events.Event) -> None:  # pragma: no cover
        pass

    class Boom(Exception):
        pass

    with pytest.raises(Boom), transaction.atomic():
        events.emit("project.created", aggregate_type="project", aggregate_id=uuid.uuid4())
        raise Boom()
    assert not ProcrastinateJob.objects.filter(task_name="mizan.events.dispatch").exists()


def test_dispatch_runs_the_handler_under_the_tenant_scope_as_system(scoped: Any) -> None:
    observed: dict[str, Any] = {}

    @events.subscribe("report.issued", name="test.observer")
    def observe(event: events.Event) -> None:
        from mizan.platform.db.tenancy import active_tenant_setting

        observed["tenant_setting"] = active_tenant_setting()
        observed["actor"] = context.actor().type
        observed["aggregate_id"] = event.aggregate_id

    report_id = uuid.uuid4()
    event = events.emit("report.issued", aggregate_type="report", aggregate_id=report_id)
    run_handler(event.to_dict(), "test.observer")
    assert observed == {
        "tenant_setting": str(scoped.id),
        "actor": "SYSTEM",
        "aggregate_id": report_id,
    }


def test_event_round_trips_through_json(scoped: Any) -> None:
    event = events.emit(
        "intake.registered", aggregate_type="intake", aggregate_id=uuid.uuid4(), payload={"qty": 16}
    )
    assert events.Event.from_dict(event.to_dict()) == event
