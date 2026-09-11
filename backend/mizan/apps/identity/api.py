from __future__ import annotations

import uuid

from django.http import HttpRequest
from ninja import Router, Schema

from mizan.apps.identity.models import User
from mizan.apps.identity.principal import Principal
from mizan.platform.api.errors import Unauthorized

router = Router(tags=["identity"])


class MeOut(Schema):
    id: uuid.UUID
    email: str
    display_name: str
    locale: str
    realm: str
    tenant_id: uuid.UUID | None
    mfa_enrolled: bool
    must_change_password: bool


@router.get("/me", response=MeOut, summary="Profile of the caller")
def me(request: HttpRequest) -> User:
    principal: Principal | None = getattr(request, "principal", None)
    if principal is None:
        raise Unauthorized()
    return User.objects.get(pk=principal.user_id)
