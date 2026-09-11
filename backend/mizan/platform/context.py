"""Request/task context carried in contextvars: tenant, actor, request metadata."""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Literal

ActorType = Literal["USER", "SYSTEM", "CLIENT", "API_KEY"]


@dataclass(frozen=True, slots=True)
class Actor:
    id: uuid.UUID | None
    type: ActorType = "USER"
    display_name: str = ""

    @classmethod
    def system(cls) -> Actor:
        return cls(id=None, type="SYSTEM", display_name="system")


@dataclass(frozen=True, slots=True)
class RequestContext:
    request_id: str = ""
    ip: str | None = None
    user_agent: str = ""
    app: str = ""  # back-office | admin | portal | verify | worker | cli
    extra: dict[str, object] = field(default_factory=dict)

    def as_audit_context(self) -> dict[str, object]:
        data: dict[str, object] = {"request_id": self.request_id, "app": self.app}
        if self.ip:
            data["ip"] = self.ip
        data.update(self.extra)
        return data


current_tenant_id: ContextVar[uuid.UUID | None] = ContextVar("mizan_tenant_id", default=None)
current_actor: ContextVar[Actor | None] = ContextVar("mizan_actor", default=None)
current_request: ContextVar[RequestContext | None] = ContextVar("mizan_request", default=None)

SYSTEM_ACTOR = Actor.system()
NO_REQUEST = RequestContext()


def actor() -> Actor:
    return current_actor.get() or SYSTEM_ACTOR


def request_context() -> RequestContext:
    return current_request.get() or NO_REQUEST


rls_bypass_active: ContextVar[bool] = ContextVar("mizan_rls_bypass", default=False)


def tenant_id_or_none() -> uuid.UUID | None:
    return current_tenant_id.get()


def require_tenant_id() -> uuid.UUID:
    tenant_id = current_tenant_id.get()
    if tenant_id is None:
        raise RuntimeError("No tenant scope is active")
    return tenant_id
