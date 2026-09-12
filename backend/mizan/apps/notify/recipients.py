"""Audience resolution (SPEC §10.8): roles, explicit users, payload users and client contacts."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from django.db.models import Q

from mizan.apps.identity.models import Membership, MembershipStatus, Realm, User, UserStatus
from mizan.platform.events import Event

CONTACT_ROLES: tuple[str, ...] = ("SIGNATORY", "COMMERCIAL", "TECHNICAL", "ACCOUNTING")


@dataclass(slots=True)
class Recipient:
    type: str  # "user" | "contact"
    id: uuid.UUID | None
    name: str = ""
    email: str = ""
    phone: str = ""  # E.164, used by SMS and WhatsApp
    locale: str = ""
    user_id: uuid.UUID | None = None  # in-app target: the user itself or a contact's portal user
    role: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        if self.id is not None:
            return f"{self.type}:{self.id}"
        if self.email:
            return f"email:{self.email.lower()}"
        return f"phone:{self.phone}"

    def address_for(self, channel: str) -> str:
        if channel == "email":
            return self.email
        if channel in ("sms", "whatsapp"):
            return self.phone
        if channel == "in_app":
            return str(self.user_id) if self.user_id else ""
        return ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "id": str(self.id) if self.id else None,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "locale": self.locale,
            "user_id": str(self.user_id) if self.user_id else None,
            "role": self.role,
            **({"extra": self.extra} if self.extra else {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Recipient:
        return cls(
            type=str(data.get("type") or "contact"),
            id=uuid.UUID(str(data["id"])) if data.get("id") else None,
            name=str(data.get("name") or ""),
            email=str(data.get("email") or ""),
            phone=str(data.get("phone") or ""),
            locale=str(data.get("locale") or ""),
            user_id=uuid.UUID(str(data["user_id"])) if data.get("user_id") else None,
            role=str(data.get("role") or ""),
            extra=dict(data.get("extra") or {}),
        )

    @classmethod
    def from_user(cls, user: User, role: str = "") -> Recipient:
        return cls(
            type="user",
            id=user.id,
            name=user.display_name or user.email,
            email=user.email,
            phone=str(getattr(user, "phone", "") or ""),
            locale=user.locale,
            user_id=user.id,
            role=role,
        )


ContactResolver = Callable[[Event, list[str]], list[Recipient]]
_contact_resolvers: list[ContactResolver] = []


def register_contact_resolver(func: ContactResolver) -> ContactResolver:
    """The CRM app registers how client contacts are loaded for an event (account, roles)."""
    if func not in _contact_resolvers:
        _contact_resolvers.append(func)
    return func


def payload_contacts(event: Event, roles: list[str]) -> list[Recipient]:
    """Default resolver: contacts carried by the payload as ``contacts: [{role, email, ...}]``."""
    wanted = {r.upper() for r in roles}
    found: list[Recipient] = []
    for raw in event.payload.get("contacts") or []:
        if not isinstance(raw, dict):
            continue
        contact_roles = raw.get("roles") or ([raw["role"]] if raw.get("role") else [])
        if not wanted.intersection(str(r).upper() for r in contact_roles):
            continue
        first = str(raw.get("first_name") or "")
        last = str(raw.get("last_name") or "")
        recipient = Recipient.from_dict(
            {
                **raw,
                "type": "contact",
                "name": raw.get("name") or f"{first} {last}".strip(),
                "role": ",".join(sorted(str(r).upper() for r in contact_roles)),
            }
        )
        recipient.extra = {"first_name": first, "last_name": last}
        found.append(recipient)
    return found


register_contact_resolver(payload_contacts)


def _uuid_list(value: Any) -> list[uuid.UUID]:
    if value is None:
        return []
    items = value if isinstance(value, list | tuple | set) else [value]
    result: list[uuid.UUID] = []
    for item in items:
        try:
            result.append(uuid.UUID(str(item)))
        except ValueError:
            continue
    return result


def department_ids_of(payload: dict[str, Any]) -> list[uuid.UUID]:
    return [*_uuid_list(payload.get("department_id")), *_uuid_list(payload.get("department_ids"))]


def staff_by_roles(
    roles: Iterable[str],
    *,
    branch_id: uuid.UUID | None,
    department_ids: Iterable[uuid.UUID] = (),
) -> list[Recipient]:
    """Active staff holding one of ``roles`` in the branch (or in every branch), narrowed to the
    departments when the event names some (members without a department are branch-wide)."""
    role_codes = [r.upper() for r in roles]
    if not role_codes:
        return []
    qs = Membership.objects.filter(
        status=MembershipStatus.ACTIVE,
        role__code__in=role_codes,
        role__status="ACTIVE",
        user__status=UserStatus.ACTIVE,
        user__realm=Realm.STAFF,
    ).select_related("user", "role")
    if branch_id is not None:
        qs = qs.filter(Q(branch_id__isnull=True) | Q(branch_id=branch_id))
    departments = list(department_ids)
    if departments:
        qs = qs.filter(Q(department_id__isnull=True) | Q(department_id__in=departments))
    seen: dict[uuid.UUID, Recipient] = {}
    for membership in qs.order_by("created_at"):
        if membership.user_id not in seen:
            seen[membership.user_id] = Recipient.from_user(membership.user, membership.role.code)
    return list(seen.values())


def users_by_ids(ids: Iterable[uuid.UUID]) -> list[Recipient]:
    wanted = list(ids)
    if not wanted:
        return []
    return [
        Recipient.from_user(user)
        for user in User.objects.filter(pk__in=wanted, status=UserStatus.ACTIVE).order_by(
            "created_at"
        )
    ]


def contacts_by_roles(event: Event, roles: list[str]) -> list[Recipient]:
    if not roles:
        return []
    found: dict[str, Recipient] = {}
    for resolver in _contact_resolvers:
        for recipient in resolver(event, roles):
            found.setdefault(recipient.key, recipient)
    return list(found.values())


def resolve_audience(audience: dict[str, Any], event: Event) -> list[Recipient]:
    """Union of every audience part, deduplicated by recipient key (first occurrence wins)."""
    found: dict[str, Recipient] = {}

    def add_all(recipients: Iterable[Recipient]) -> None:
        for recipient in recipients:
            found.setdefault(recipient.key, recipient)

    add_all(
        staff_by_roles(
            audience.get("roles") or [],
            branch_id=event.branch_id,
            department_ids=department_ids_of(event.payload),
        )
    )
    user_ids = _uuid_list(audience.get("user_ids") or [])
    for key in audience.get("payload_user_keys") or []:
        user_ids.extend(_uuid_list(event.payload.get(str(key))))
    add_all(users_by_ids(user_ids))
    add_all(contacts_by_roles(event, [str(r) for r in audience.get("contact_roles") or []]))
    return list(found.values())
