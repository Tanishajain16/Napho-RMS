from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    avatar_url: str | None = None
    phone: str | None = None
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime
    roles: list[str] = []


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    avatar_url: str | None = None


class UserMeOut(BaseModel):
    """Extended profile for the /me endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    avatar_url: str | None = None
    phone: str | None = None
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime
    roles: list[str] = []
    org_id: str | None = None
    department: str | None = None
    designation: str | None = None
    employee_code: str | None = None
