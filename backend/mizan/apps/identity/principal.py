"""The authenticated caller of a request or a task."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from mizan.platform.auth.jwt import Realm


@dataclass(slots=True)
class Principal:
    user_id: uuid.UUID
    tenant_id: uuid.UUID | None
    realm: Realm
    session_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None  # from X-Branch-Id, validated against memberships
    step_up_at: int | None = None
    display_name: str = ""
    locale: str = "fr"
    cache: dict[str, object] = field(default_factory=dict)

    @property
    def is_platform_operator(self) -> bool:
        return self.realm == "PLATFORM"

    @property
    def is_client(self) -> bool:
        return self.realm == "CLIENT"
