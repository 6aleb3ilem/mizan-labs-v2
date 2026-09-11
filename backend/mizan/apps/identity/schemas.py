from __future__ import annotations

import uuid
from datetime import datetime

from ninja import Schema
from pydantic import EmailStr, Field

from mizan.platform.api.schemas import LabelsSchema


class LoginIn(Schema):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    tenant_code: str | None = Field(
        default=None, description="Required when the e-mail exists in several tenants"
    )


class RefreshIn(Schema):
    refresh_token: str


class ChangePasswordIn(Schema):
    current_password: str
    new_password: str = Field(min_length=10, max_length=256)


class UserOut(Schema):
    id: uuid.UUID
    email: str
    display_name: str
    locale: str
    realm: str
    status: str
    tenant_id: uuid.UUID | None
    mfa_enrolled: bool
    must_change_password: bool
    last_login: datetime | None = None


class MembershipOut(Schema):
    id: uuid.UUID
    user_id: uuid.UUID
    role_id: uuid.UUID
    role_code: str
    branch_id: uuid.UUID | None
    department_id: uuid.UUID | None
    account_id: uuid.UUID | None
    project_ids: list[uuid.UUID]
    status: str


class MeOut(UserOut):
    memberships: list[MembershipOut]


class TokenOut(Schema):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: str
    user: MeOut


class GrantOut(Schema):
    resource: str
    action: str
    scope: str
    field_groups: list[str]
    role: str
    membership_id: uuid.UUID | None
    branch_id: uuid.UUID | None
    department_id: uuid.UUID | None
    account_id: uuid.UUID | None


class PermissionsOut(Schema):
    user_id: uuid.UUID
    tenant_id: uuid.UUID | None
    is_platform_operator: bool
    grants: list[GrantOut]


class UserIn(Schema):
    email: EmailStr
    display_name: str = ""
    locale: str = "fr"
    realm: str = "STAFF"
    temporary_password: str | None = Field(default=None, min_length=10)


class UserPatch(Schema):
    display_name: str | None = None
    locale: str | None = None
    status: str | None = None


class MembershipIn(Schema):
    user_id: uuid.UUID
    role_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    account_id: uuid.UUID | None = None
    project_ids: list[uuid.UUID] = []


class GrantIn(Schema):
    resource: str
    action: str
    scope: str
    field_groups: list[str] = []


class RoleIn(Schema):
    code: str = Field(pattern=r"^[A-Z0-9_.-]{2,64}$")
    labels: LabelsSchema
    description: str = ""
    grants: list[GrantIn] = []


class RolePatch(Schema):
    labels: LabelsSchema | None = None
    description: str | None = None


class RoleOut(Schema):
    id: uuid.UUID
    code: str
    labels: dict[str, str]
    description: str
    is_template: bool
    status: str
    grants: list[GrantIn]
    memberships_count: int = 0
