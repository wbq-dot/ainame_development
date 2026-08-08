from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


UserStatus = Literal["active", "frozen", "deleted"]


class AdminActionIn(BaseModel):
    reason: str | None = Field(default=None, max_length=200)


class AdminUserOut(BaseModel):
    id: int
    email: str
    username: str
    role: str
    status: UserStatus
    balance: int = 0
    total_used: int = 0
    total_recharge: int = 0
    logo_balance: int = 0
    logo_total_used: int = 0
    logo_total_recharge: int = 0
    created_at: datetime
    updated_at: datetime
    frozen_at: datetime | None = None
    deleted_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class AdminUserListOut(BaseModel):
    items: list[AdminUserOut]
    total: int
    page: int
    page_size: int


class AdminActionOut(BaseModel):
    message: str
    user: AdminUserOut
