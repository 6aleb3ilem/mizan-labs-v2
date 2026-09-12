"""SPEC §19: rules resolve audiences, respect preferences, throttles and quiet hours; deliveries
are logged per channel with retries and fallbacks; the inbox is pushed live."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

import pytest
from django.core import mail
from django.test import Client
from django.utils import timezone
from freezegun import freeze_time
from procrastinate.contrib.django.models import ProcrastinateJob

from mizan.apps.notify import channels, digest, dispatch, services
from mizan.apps.notify.defaults import install_defaults
from mizan.apps.notify.models import (
    ContactChannelPreference,
    DeliveryStatus,
    MessageTemplate,
    Notification,
    NotificationDelivery,
    NotificationRule,
)
from mizan.apps.notify.recipients import Recipient
from mizan.platform import events
from mizan.platform.tasks import run_handler

pytestmark = pytest.mark.django_db

PASSWORD = "Passw0rd!Passw0rd"
CONTACTS = [
    {"id": str(uuid.uuid4()), "role": "SIGNATORY", "first_name": "Moussa", "last_name": "Ba", "email": "moussa@sogeco.mr", "phone": "+22240000001", "locale": "fr"},
    {"id": str(uuid.uuid4()), "role": "COMMERCIAL", "first_name": "Jane", "last_name": "Doe", "email": "jane@sogeco.mr", "phone": "+22240000002", "locale": "en"},
    {"id": str(uuid.uuid4()), "role": "TECHNICAL", "first_name": "Ahmed", "email": "ahmed@sogeco.mr", "phone": "+22240000003"},
]  # fmt: skip
QUOTE_PAYLOAD: dict[str, Any] = {
    "quote": {"number": "DV-NKC-2026-00042"},
    "rev": 1,
    "project": {"title": "Immeuble R+4"},
    "total": "60610.00",
    "currency": "MRU",
    "portal_path": "/quotes/42",
    "contacts": CONTACTS,
}


@pytest.fixture(autouse=True)
def _log_outbox() -> Any:
    channels.LOG_OUTBOX.clear()
    yield
    channels.LOG_OUTBOX.clear()


@pytest.fixture
def defaults(branch: Any) -> dict[str, int]:
    return install_defaults()


def _run_pending_deliveries() -> list[NotificationDelivery]:
    """Execute the queued delivery jobs the way the worker would."""
    done: list[NotificationDelivery] = []
    for job in ProcrastinateJob.objects.filter(task_name="mizan.notify.deliver").order_by("id"):
        done.append(
            dispatch.deliver(uuid.UUID(job.args["delivery_id"]), uuid.UUID(job.args["tenant_id"]))
        )
    return done


def _emit_and_dispatch(code: str, payload: dict[str, Any], branch: Any, **kw: Any) -> events.Event:
    event = events.emit(
        code, aggregate_type=code.partition(".")[0], aggregate_id=uuid.uuid4(), payload=payload,
        branch_id=branch.id, **kw
    )  # fmt: skip
    run_handler(event.to_dict(), "notify.dispatch")
    return event


# --- rules and channels ----------------------------------------------------------------------------


def test_quote_sent_reaches_client_contacts_by_email_and_whatsapp(
    defaults: Any, branch: Any
) -> None:
    assert defaults == {"templates": 42, "rules": 10}
    event = _emit_and_dispatch("quote.sent", QUOTE_PAYLOAD, branch)
    deliveries = list(
        NotificationDelivery.objects.filter(event_id=event.id).order_by("channel", "recipient_key")
    )
    assert {(d.channel, d.recipient["email"]) for d in deliveries} == {
        ("email", "moussa@sogeco.mr"), ("whatsapp", "moussa@sogeco.mr"),
        ("email", "jane@sogeco.mr"), ("whatsapp", "jane@sogeco.mr"),
    }  # technical contact is not in the audience  # fmt: skip
    assert all(d.status == DeliveryStatus.PENDING for d in deliveries)
    sent = _run_pending_deliveries()
    assert {d.status for d in sent} == {DeliveryStatus.SENT}
    # e-mail went through Django's mail backend, in the recipient's locale
    subjects = sorted(m.subject for m in mail.outbox)
    assert subjects == [
        "Devis DV-NKC-2026-00042 rév. 1 — Immeuble R+4",
        "Quote DV-NKC-2026-00042 rev. 1 — Immeuble R+4",
    ]
    french = next(m for m in mail.outbox if m.subject.startswith("Devis"))
    assert french.to == ["moussa@sogeco.mr"]
    assert "http://localhost:5175/quotes/42" in french.body and "60610.00 MRU" in french.body
    assert french.extra_headers["Message-ID"].endswith("@mizanlabs.local>")
    # WhatsApp went to the log adapter with the short text
    wa = [m for m in channels.LOG_OUTBOX if m["channel"] == "whatsapp"]
    assert {m["to"] for m in wa} == {"+22240000001", "+22240000002"}
    assert any(m["body"].startswith("Bonjour Moussa, votre devis DV-NKC-2026-00042") for m in wa)
    assert any(m["body"].startswith("Hello Jane, your quote") for m in wa)
    # the dispatch is idempotent: running the handler again creates nothing
    run_handler(event.to_dict(), "notify.dispatch")
    assert NotificationDelivery.objects.filter(event_id=event.id).count() == 4


def test_no_rule_no_delivery_and_other_tenants_rules_are_invisible(
    defaults: Any, branch: Any, other_tenant: Any
) -> None:
    event = _emit_and_dispatch("project.closed", {}, branch)
    assert not NotificationDelivery.objects.filter(event_id=event.id).exists()
    from mizan.platform.db.tenancy import tenant_scope

    with tenant_scope(other_tenant.id):
        assert NotificationRule.objects.count() == 0
        assert NotificationDelivery.objects.count() == 0


def test_staff_audience_roles_departments_and_payload_users(
    defaults: Any, branch: Any, department: Any, make_member: Any
) -> None:
    from mizan.apps.org.models import Department

    soils = Department.objects.create(branch=branch, code="SOILS")
    owner, _ = make_member("COMMERCIAL")
    concrete_sup, _ = make_member("LAB_SUPERVISOR", department_id=department.id)
    soils_sup, _ = make_member("LAB_SUPERVISOR", department_id=soils.id)
    branch_sup, _ = make_member("LAB_SUPERVISOR")  # no department: branch-wide
    finance, _ = make_member("FINANCE")
    technician, _ = make_member("TECHNICIAN")
    payload = {
        **QUOTE_PAYLOAD,
        "owner_id": str(owner.id),
        "department_ids": [str(department.id)],
        "account": {"name": "SOGECO"},
        "app_path": "/orders/1",
    }
    event = _emit_and_dispatch("quote.accepted", payload, branch)
    rows = NotificationDelivery.objects.filter(event_id=event.id)
    recipients = {r.recipient_key for r in rows}
    assert recipients == {f"user:{u.id}" for u in (owner, concrete_sup, branch_sup, finance)}
    assert f"user:{soils_sup.id}" not in recipients and f"user:{technician.id}" not in recipients
    assert {r.channel for r in rows} == {"in_app", "email"}
    _run_pending_deliveries()
    inbox = Notification.objects.filter(user=owner)
    assert inbox.count() == 1
    note = inbox.get()
    assert note.title == "Devis DV-NKC-2026-00042 accepté"
    assert note.body == "Devis DV-NKC-2026-00042 accepté par SOGECO — Immeuble R+4"
    assert note.link == "http://localhost:5173/orders/1"
    assert note.read_at is None and note.event_code == "quote.accepted"


def test_channel_preferences_and_no_address_are_recorded_as_skips(
    defaults: Any, branch: Any
) -> None:
    ContactChannelPreference.objects.create(
        recipient_type="contact", recipient_id=uuid.UUID(CONTACTS[0]["id"]), channel="whatsapp", enabled=False
    )  # fmt: skip
    payload = {**QUOTE_PAYLOAD, "contacts": [CONTACTS[0], {**CONTACTS[1], "phone": ""}]}
    event = _emit_and_dispatch("quote.sent", payload, branch)
    by_key = {
        (d.recipient["email"], d.channel): d
        for d in NotificationDelivery.objects.filter(event_id=event.id)
    }
    assert by_key[("moussa@sogeco.mr", "whatsapp")].status == DeliveryStatus.SKIPPED
    assert by_key[("moussa@sogeco.mr", "whatsapp")].last_error == "preference"
    assert by_key[("jane@sogeco.mr", "whatsapp")].last_error == "no_address"
    assert by_key[("jane@sogeco.mr", "email")].status == DeliveryStatus.PENDING
    assert ProcrastinateJob.objects.filter(task_name="mizan.notify.deliver").count() == 2


def test_throttle_limits_repeats_per_recipient(defaults: Any, branch: Any) -> None:
    payload = {
        "invoice": {"number": "FA-1"}, "balance": "1000.00", "currency": "MRU", "days": 12,
        "contacts": [{"id": str(uuid.uuid4()), "role": "ACCOUNTING", "email": "compta@sogeco.mr", "phone": "+22240000009"}],
    }  # fmt: skip
    first = _emit_and_dispatch("invoice.overdue", payload, branch)
    second = _emit_and_dispatch("invoice.overdue", payload, branch)
    assert {d.status for d in NotificationDelivery.objects.filter(event_id=first.id)} == {
        DeliveryStatus.PENDING
    }
    again = NotificationDelivery.objects.filter(event_id=second.id)
    assert {d.status for d in again} == {DeliveryStatus.SKIPPED} and {
        d.last_error for d in again
    } == {"throttled"}
    with freeze_time(timezone.now() + dt.timedelta(days=1, minutes=1)):
        third = _emit_and_dispatch("invoice.overdue", payload, branch)
    assert {d.status for d in NotificationDelivery.objects.filter(event_id=third.id)} == {
        DeliveryStatus.PENDING
    }


def test_quiet_hours_defer_sms_and_whatsapp_but_not_email(defaults: Any, branch: Any) -> None:
    branch.settings = {"quiet_hours": {"start": "21:00", "end": "07:00"}}
    branch.save(update_fields=["settings"])
    payload = {
        "qty": 16,
        "project": {"title": "Pont"},
        "date": "2026-09-11",
        "dates": "09/10, 02/11",
        "contacts": CONTACTS,
    }
    with freeze_time("2026-09-11T23:30:00+00:00"):  # 23:30 in Nouakchott (UTC)
        event = _emit_and_dispatch("intake.registered", payload, branch)
    rows = {d.channel: d for d in NotificationDelivery.objects.filter(event_id=event.id)}
    assert rows["sms"].status == DeliveryStatus.SCHEDULED
    assert rows["sms"].scheduled_for == dt.datetime(2026, 9, 12, 7, 0, tzinfo=dt.UTC)
    assert rows["whatsapp"].status == DeliveryStatus.SCHEDULED
    assert (
        rows["in_app"].status == DeliveryStatus.SKIPPED
        and rows["in_app"].last_error == "no_address"
    )
    job = ProcrastinateJob.objects.get(queueing_lock=f"deliver:{rows['sms'].id}")
    assert job.scheduled_at == rows["sms"].scheduled_for
    with freeze_time("2026-09-11T12:00:00+00:00"):
        daytime = _emit_and_dispatch("intake.registered", payload, branch)
    assert (
        NotificationDelivery.objects.get(event_id=daytime.id, channel="sms").status
        == DeliveryStatus.PENDING
    )


def test_template_channel_fallback_and_locale_fallback(defaults: Any, branch: Any) -> None:
    # REPORT_ISSUED has no whatsapp template: the short SMS text is reused; unknown locale → fr
    payload = {
        "report": {"number": "PV-1"}, "test": {"label": "Compression"}, "age": 28, "project": {"title": "Pont"},
        "verify_path": "/d/abc", "contacts": [{**CONTACTS[2], "locale": "ar"}],
    }  # fmt: skip
    event = _emit_and_dispatch("report.issued", payload, branch)
    rows = {d.channel: d for d in NotificationDelivery.objects.filter(event_id=event.id)}
    assert rows["whatsapp"].rendered[
        "body"
    ] == "Mizan Labs : rapport PV-1 (Compression) émis. http://localhost:5175/reports/" + str(
        event.aggregate_id
    )
    assert rows["email"].rendered["subject"] == "Rapport PV-1 — Pont"
    assert "http://localhost:5176/d/abc" in rows["email"].rendered["body"]
    assert rows["in_app"].last_error == "no_address"  # contact without a portal user


# --- sending, retries, fallbacks --------------------------------------------------------------------


def test_transient_failures_retry_then_fail_and_fall_back(
    defaults: Any, branch: Any, monkeypatch: Any
) -> None:
    class Flaky:
        code = "whatsapp"

        def send(self, delivery: NotificationDelivery) -> str:
            raise channels.ChannelError("aggregator down")

    original = channels.backend_for
    monkeypatch.setattr(
        channels, "backend_for", lambda c: Flaky() if c == "whatsapp" else original(c)
    )
    payload = {**QUOTE_PAYLOAD, "contacts": [CONTACTS[0]]}
    event = _emit_and_dispatch("quote.sent", payload, branch)
    wa = NotificationDelivery.objects.get(event_id=event.id, channel="whatsapp")
    for attempt in range(1, dispatch.MAX_ATTEMPTS):
        with pytest.raises(channels.ChannelError):
            dispatch.deliver(wa.id, wa.tenant_id)
        wa.refresh_from_db()
        assert (wa.attempts, wa.status) == (attempt, DeliveryStatus.PENDING)
        assert "aggregator down" in wa.last_error
    final = dispatch.deliver(wa.id, wa.tenant_id)  # last attempt: no raise, FAILED, fallback
    assert (final.attempts, final.status) == (dispatch.MAX_ATTEMPTS, DeliveryStatus.FAILED)
    fallback = NotificationDelivery.objects.get(fallback_of=wa)
    assert (
        fallback.channel == "sms"
    )  # branch default order whatsapp → sms → email; e-mail already used
    assert fallback.event_id == event.id and fallback.status == DeliveryStatus.PENDING
    assert fallback.rendered["body"].startswith("Bonjour Moussa, votre devis")
    assert dispatch.deliver(fallback.id, fallback.tenant_id).status == DeliveryStatus.SENT
    assert channels.LOG_OUTBOX[-1]["channel"] == "sms"


def test_permanent_failure_does_not_retry(defaults: Any, branch: Any) -> None:
    payload = {**QUOTE_PAYLOAD, "contacts": [{**CONTACTS[0], "phone": "40000001"}]}  # not E.164
    event = _emit_and_dispatch("quote.sent", payload, branch)
    wa = NotificationDelivery.objects.get(event_id=event.id, channel="whatsapp")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            channels,
            "backend_for",
            lambda c: channels.HttpSmsBackend() if c == "whatsapp" else channels.LogBackend(c),
        )
        mp.setitem(dispatch.settings.MIZAN_NOTIFY, "sms_url", "http://aggregator.local/send")
        result = dispatch.deliver(wa.id, wa.tenant_id)
    assert (result.status, result.attempts) == (DeliveryStatus.FAILED, 1)
    assert "E.164" in result.last_error
    assert not NotificationDelivery.objects.filter(
        fallback_of=wa
    ).exists()  # sms has the same number


def test_direct_send_for_one_time_codes(defaults: Any, branch: Any) -> None:
    recipient = Recipient(
        type="contact", id=uuid.uuid4(), name="Moussa Ba", phone="+22240000001", locale="fr"
    )
    delivery = dispatch.send_direct("OTP", "sms", recipient, {"otp": "482913"}, branch=branch)
    assert (
        delivery.rule is None
        and delivery.rendered["body"]
        == "Code Mizan Labs : 482913 (valable 10 min). Ne le partagez pas."
    )
    assert dispatch.deliver(delivery.id, delivery.tenant_id).status == DeliveryStatus.SENT
    assert channels.LOG_OUTBOX[-1] == {
        **channels.LOG_OUTBOX[-1],
        "channel": "sms",
        "to": "+22240000001",
    }


# --- digests ----------------------------------------------------------------------------------------


def test_daily_digest_fires_once_at_branch_time(
    defaults: Any, branch: Any, department: Any, make_member: Any
) -> None:
    supervisor, _ = make_member("LAB_SUPERVISOR", department_id=department.id)
    manager, _ = make_member("BRANCH_MANAGER")

    @digest.register_digest_provider("daily_supervisor")
    def counts(b: Any, d: Any, day: dt.date) -> dict[str, int]:
        return {"intakes": 3, "done": 5, "todo": 2, "overdue": 1, "tomorrow": 4}

    try:
        tick = dt.datetime(2026, 9, 14, 6, 35, tzinfo=dt.UTC)  # 06:35 Nouakchott (UTC)
        produced = digest.run_tenant_digests(tick)
        assert {d.recipient_key for d in produced} == {
            f"user:{supervisor.id}",
            f"user:{manager.id}",
        }
        body = produced[0].rendered["body"]
        assert (
            body
            == "Résumé du 2026-09-14 — Concrete : 3 réceptions, 5 essais faits, 2 à faire, 1 en retard, 4 demain."
            or body.startswith("Résumé du 2026-09-14 — CONCRETE")
        )
        assert produced[0].rendered["subject"] == "Résumé du 2026-09-14 — NKC"
        assert (
            digest.run_tenant_digests(tick + dt.timedelta(minutes=5)) == []
        )  # same firing, no duplicate
        assert digest.run_tenant_digests(dt.datetime(2026, 9, 14, 12, 0, tzinfo=dt.UTC)) == []
        assert len(digest.run_tenant_digests(dt.datetime(2026, 9, 15, 6, 31, tzinfo=dt.UTC))) == 2
    finally:
        digest.register_digest_provider("daily_supervisor")(digest.daily_supervisor)


def test_scheduler_runs_the_digest_job(defaults: Any, branch: Any, make_member: Any) -> None:
    from mizan.platform import scheduler
    from mizan.platform.models import PeriodicJobRun

    make_member("BRANCH_MANAGER")
    at = dt.datetime(2026, 9, 14, 6, 33, tzinfo=dt.UTC)
    assert scheduler.tick(at, only={"notify.digests"}) == {"notify.digests": "ran"}
    assert scheduler.tick(at + dt.timedelta(minutes=1), only={"notify.digests"}) == {
        "notify.digests": "skipped"
    }
    run = PeriodicJobRun.objects.get(name="notify.digests")
    assert run.last_error == "" and run.failures == 0 and run.last_finished_at is not None
    assert NotificationDelivery.objects.filter(template_code="DAILY_DIGEST").count() == 1


# --- API ----------------------------------------------------------------------------------------------


def _api(user: Any) -> Client:
    token = Client().post(
        "/api/v1/auth/login", data={"email": user.email, "password": PASSWORD}, content_type="application/json"
    ).json()["access_token"]  # fmt: skip
    return Client(HTTP_AUTHORIZATION=f"Bearer {token}")


def test_rules_and_templates_api(defaults: Any, branch: Any, make_member: Any) -> None:
    admin, _ = make_member("TENANT_ADMIN", all_branches=True)
    api = _api(admin)
    rules = api.get("/api/v1/notification-rules?event_code=quote.sent").json()
    assert [r["code"] for r in rules] == ["QUOTE_SENT"]
    bad = api.post(
        "/api/v1/notification-rules",
        data={"code": "X_RULE", "event_code": "quote.teleported", "channels": ["fax"], "template_code": "QUOTE_SENT"},
        content_type="application/json",
    )  # fmt: skip
    assert bad.status_code == 422
    assert {d["loc"][0] for d in bad.json()["details"]} == {"event_code", "channels"}
    created = api.post(
        "/api/v1/notification-rules",
        data={
            "code": "QUOTE_SENT_MANAGER", "event_code": "quote.sent", "channels": ["in_app"],
            "audience": {"roles": ["COMMERCIAL_MANAGER"]}, "template_code": "QUOTE_ACCEPTED", "branch_id": str(branch.id),
        },
        content_type="application/json",
    )  # fmt: skip
    assert created.status_code == 201, created.content
    rule_id = created.json()["id"]
    patched = api.patch(
        f"/api/v1/notification-rules/{rule_id}",
        data={"active": False},
        content_type="application/json",
    )
    assert patched.json()["active"] is False
    # simulate: dry run with the sample payload, nothing persisted
    sim = api.post(
        f"/api/v1/notification-rules/{rules[0]['id']}:simulate",
        data={"payload": QUOTE_PAYLOAD, "branch_id": str(branch.id)},
        content_type="application/json",
    )
    assert sim.status_code == 200
    assert {(s["recipient"]["email"], s["channel"], s["status"]) for s in sim.json()} == {
        ("moussa@sogeco.mr", "email", "PENDING"), ("moussa@sogeco.mr", "whatsapp", "PENDING"),
        ("jane@sogeco.mr", "email", "PENDING"), ("jane@sogeco.mr", "whatsapp", "PENDING"),
    }  # fmt: skip
    assert NotificationDelivery.objects.count() == 0
    # templates: invalid Jinja is refused, valid drafts preview
    invalid = api.post(
        "/api/v1/message-templates",
        data={"code": "NEW_T", "channel": "sms", "body": "Hello {{ name "},
        content_type="application/json",
    )
    assert invalid.status_code == 422 and invalid.json()["details"][0]["loc"] == ["body"]
    preview = api.post(
        "/api/v1/message-templates:preview",
        data={"subject": "Hi {{ name }}", "body": "Total {{ total | money('MRU') }}", "sample": {"name": "Jane", "total": "1234.5"}},
        content_type="application/json",
    )  # fmt: skip
    assert preview.json() == {
        "subject": "Hi Jane",
        "body": f"Total 1{chr(0x202F)}234,50 MRU",
        "html": "",
    }
    templates = api.get("/api/v1/message-templates?code=OTP&channel=sms").json()
    assert {t["locale"] for t in templates} == {"fr", "en"}
    edited = api.patch(
        f"/api/v1/message-templates/{templates[0]['id']}",
        data={"body": "Code : {{ otp }}", "sample": {"otp": "1"}},
        content_type="application/json",
    )
    assert (
        edited.status_code == 200
        and MessageTemplate.objects.get(pk=templates[0]["id"]).body == "Code : {{ otp }}"
    )
    # a commercial user may not configure rules
    commercial, _ = make_member("COMMERCIAL")
    assert (
        _api(commercial)
        .post("/api/v1/notification-rules", data={}, content_type="application/json")
        .status_code
        == 403
    )


def test_delivery_log_and_retry_api(defaults: Any, branch: Any, make_member: Any) -> None:
    admin, _ = make_member("TENANT_ADMIN", all_branches=True)
    api = _api(admin)
    payload = {**QUOTE_PAYLOAD, "contacts": [{**CONTACTS[0], "phone": ""}]}
    event = _emit_and_dispatch("quote.sent", payload, branch)
    page = api.get(f"/api/v1/notification-deliveries?event_id={event.id}").json()
    assert {(d["channel"], d["status"]) for d in page["items"]} == {
        ("email", "PENDING"),
        ("whatsapp", "SKIPPED"),
    }
    skipped = next(d for d in page["items"] if d["status"] == "SKIPPED")
    pending = next(d for d in page["items"] if d["status"] == "PENDING")
    assert api.post(f"/api/v1/notification-deliveries/{pending['id']}:retry").status_code == 409
    retried = api.post(f"/api/v1/notification-deliveries/{skipped['id']}:retry")
    assert retried.status_code == 201 and retried.json()["fallback_of_id"] == skipped["id"]
    assert retried.json()["status"] == "PENDING"


def test_inbox_api_and_preferences(
    defaults: Any, branch: Any, make_member: Any, monkeypatch: Any
) -> None:
    pushed: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        channels, "publish_to_user", lambda t, u, name, data: pushed.append((name, data))
    )
    monkeypatch.setattr(
        services, "publish_to_user", lambda t, u, name, data: pushed.append((name, data))
    )
    owner, _ = make_member("COMMERCIAL")
    other, _ = make_member("COMMERCIAL")
    for n in range(3):
        _emit_and_dispatch(
            "quote.accepted",
            {**QUOTE_PAYLOAD, "owner_id": str(owner.id), "quote": {"number": f"DV-{n}"}},
            branch,
        )
    _run_pending_deliveries()
    assert [name for name, _ in pushed] == ["notification"] * 3
    api = _api(owner)
    assert api.get("/api/v1/me/notifications/unread-count").json() == {"unread": 3}
    page = api.get("/api/v1/me/notifications?limit=2").json()
    assert len(page["items"]) == 2 and page["next"]
    rest = api.get(f"/api/v1/me/notifications?limit=2&after={page['next']}").json()
    assert len(rest["items"]) == 1 and rest["next"] is None
    first = page["items"][0]["id"]
    assert api.post(
        "/api/v1/me/notifications:read", data={"ids": [first]}, content_type="application/json"
    ).json() == {"marked": 1}
    assert pushed[-1] == ("inbox", {"unread": 2})
    assert api.get("/api/v1/me/notifications?unread=true").json()["items"].__len__() == 2
    assert api.post("/api/v1/me/notifications:read-all").json() == {"marked": 2}
    assert api.get("/api/v1/me/notifications/unread-count").json() == {"unread": 0}
    # another user sees nothing of this inbox and cannot mark it
    assert _api(other).get("/api/v1/me/notifications").json()["items"] == []
    assert _api(other).post(
        "/api/v1/me/notifications:read", data={"ids": [first]}, content_type="application/json"
    ).json() == {"marked": 0}
    # preferences
    assert api.get("/api/v1/me/notification-preferences").json() == {
        "email": True,
        "sms": True,
        "whatsapp": True,
        "in_app": True,
    }
    assert (
        api.put(
            "/api/v1/me/notification-preferences",
            data={"email": False},
            content_type="application/json",
        ).json()["email"]
        is False
    )
    assert (
        ContactChannelPreference.objects.get(
            recipient_type="user", recipient_id=owner.id, channel="email"
        ).enabled
        is False
    )
    _emit_and_dispatch("quote.accepted", {**QUOTE_PAYLOAD, "owner_id": str(owner.id)}, branch)
    latest = (
        NotificationDelivery.objects.filter(recipient_key=f"user:{owner.id}", channel="email")
        .order_by("-created_at")
        .first()
    )
    assert (
        latest is not None
        and latest.status == DeliveryStatus.SKIPPED
        and latest.last_error == "preference"
    )
    contact_id = uuid.uuid4()
    admin, _ = make_member("TENANT_ADMIN", all_branches=True)
    assert _api(admin).put(
        f"/api/v1/contacts/{contact_id}/notification-preferences", data={"sms": False}, content_type="application/json"
    ).json()["sms"] is False  # fmt: skip
    assert (
        _api(other).get(f"/api/v1/contacts/{contact_id}/notification-preferences").status_code
        == 200
    )  # contact.view
