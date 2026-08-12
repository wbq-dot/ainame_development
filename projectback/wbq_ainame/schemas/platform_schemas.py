from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from schemas.name_schemas import NameIn, NameSchema


class DeveloperRegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=64)
    confirm_password: str = Field(min_length=8, max_length=64)
    code: str = Field(min_length=4, max_length=4)
    referral_code: str | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("两次密码输入不一致")
        if self.referral_code:
            self.referral_code = self.referral_code.strip().upper()
        return self


class DeveloperLoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=1, max_length=64)


class DeveloperOut(BaseModel):
    id: int
    email: str
    name: str
    status: str
    referral_code: str
    rate_limit_per_minute: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DeveloperLoginOut(BaseModel):
    developer: DeveloperOut
    access_token: str
    refresh_token: str


class DeveloperRefreshOut(BaseModel):
    access_token: str


class DeveloperPasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=64)
    new_password: str = Field(min_length=8, max_length=64)


class ApiKeyCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class ApiKeyRenameIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class ApiKeyOut(BaseModel):
    id: int
    name: str
    key_prefix: str
    status: str
    created_at: datetime
    last_used_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreatedOut(ApiKeyOut):
    api_key: str


class WalletOut(BaseModel):
    balance: int
    reserved: int
    available: int
    promotion_balance: Decimal


class CreditLogOut(BaseModel):
    id: int
    change_count: int
    balance_after: int
    type: str
    reference: str | None
    remark: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ApiPackageIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    credit_count: int = Field(gt=0, le=10_000_000)
    description: str | None = Field(default=None, max_length=300)
    sort_order: int = Field(default=0, ge=-10000, le=10000)
    is_active: bool = False


class ApiPackageOut(ApiPackageIn):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ApiPackageStatusIn(BaseModel):
    is_active: bool
    reason: str | None = Field(default=None, max_length=200)


class ApiOrderCreateIn(BaseModel):
    package_id: int
    use_promotion_balance: bool = True


class ApiOrderOut(BaseModel):
    order_no: str
    package_name: str
    credit_count: int
    total_amount: Decimal
    promotion_amount: Decimal
    cash_amount: Decimal
    status: str
    pay_url: str | None = None
    created_at: datetime
    expires_at: datetime
    paid_at: datetime | None


class ApiRefundIn(BaseModel):
    reason: str = Field(min_length=2, max_length=200)


class ApiRefundReviewIn(BaseModel):
    approve: bool
    note: str | None = Field(default=None, max_length=200)


class BatchCreateIn(BaseModel):
    items: list[NameIn] = Field(min_length=1, max_length=100)


class PublicNameOut(BaseModel):
    request_no: str
    names: list[NameSchema]
    remaining_credits: int


class TaskItemOut(BaseModel):
    item_index: int
    status: str
    input_data: dict | None
    output_data: dict | None
    error: str | None
    attempts: int
    model_config = ConfigDict(from_attributes=True)


class TaskOut(BaseModel):
    task_no: str
    task_type: str
    status: str
    total_count: int
    success_count: int
    failure_count: int
    attempts: int
    max_attempts: int
    last_error: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    items: list[TaskItemOut] = []


class CampaignIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    commission_rate: Decimal = Field(default=Decimal("0.10"), ge=0, le=1)
    inviter_credit: int = Field(default=5, ge=0, le=100000)
    invitee_credit: int = Field(default=5, ge=0, le=100000)
    reward_cap: Decimal | None = Field(default=None, ge=0)
    starts_at: datetime
    ends_at: datetime
    is_active: bool = False

    @model_validator(mode="after")
    def valid_window(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("活动结束时间必须晚于开始时间")
        return self


class CampaignOut(CampaignIn):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AdminDeveloperActionIn(BaseModel):
    reason: str = Field(min_length=2, max_length=200)


class AdminTaskRetryIn(BaseModel):
    reason: str = Field(min_length=2, max_length=200)


class AdminRewardInvalidateIn(BaseModel):
    reason: str = Field(min_length=2, max_length=200)
