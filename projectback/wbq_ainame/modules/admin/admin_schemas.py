from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from schemas.user_schemas import RawPasswordStr


UserStatus = Literal["active", "frozen", "deleted"]


class AdminBootstrapStatusOut(BaseModel):
    initialization_required: bool
    bootstrap_enabled: bool


class AdminBootstrapIn(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=8)
    password: RawPasswordStr
    bootstrap_secret: str = Field(..., min_length=1, max_length=512)


class AdminBootstrapOut(BaseModel):
    message: str
    user_id: int
    email: EmailStr
    username: str


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
    total_refund: int = 0
    logo_balance: int = 0
    logo_total_used: int = 0
    logo_total_recharge: int = 0
    logo_total_refund: int = 0
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


class AdminCreditAdjustmentIn(BaseModel):
    credit_type: Literal["name", "logo"]
    change_count: int = Field(..., ge=-2147483647, le=2147483647)
    reason: str = Field(..., min_length=1, max_length=200)

    @field_validator("change_count")
    @classmethod
    def validate_change_count(cls, value: int) -> int:
        if value == 0:
            raise ValueError("调整次数不能为 0")
        return value

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("调整原因不能为空")
        return normalized


class AdminCreditAdjustmentOut(BaseModel):
    message: str
    user: AdminUserOut
    credit_type: Literal["name", "logo"]
    change_count: int
    balance_before: int
    balance_after: int


class AdminPackageOut(BaseModel):
    id: int
    name: str
    price: Decimal
    credit_count: int
    credit_type: Literal["name", "logo"]
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AdminPackageStatusIn(BaseModel):
    is_active: bool


class AdminPackageStatusOut(BaseModel):
    message: str
    package: AdminPackageOut
