from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


CreditType = Literal["name", "logo"]
OrderStatus = Literal["pending", "paid", "closed", "refunding", "refunded"]
RefundStatus = Literal["requested", "rejected", "processing", "succeeded", "failed"]


class CreateOrderIn(BaseModel):
    package_id: int


class CreateOrderOut(BaseModel):
    order_no: str
    amount: Decimal
    credit_count: int
    credit_type: CreditType
    pay_url: str
    status: OrderStatus
    expires_at: datetime


class RefundRequestIn(BaseModel):
    reason: str = Field(..., min_length=1, max_length=200)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("请输入退款原因")
        return value


class RefundReviewIn(BaseModel):
    reason: str | None = Field(default=None, max_length=200)


class RefundRejectIn(BaseModel):
    reason: str = Field(..., min_length=1, max_length=200)


class RefundOut(BaseModel):
    refund_no: str
    order_no: str
    user_id: int
    email: str | None = None
    username: str | None = None
    origin: Literal["user_request", "late_payment"]
    status: RefundStatus
    reason: str
    review_note: str | None = None
    amount: Decimal
    credit_count: int
    credit_type: CreditType
    last_error: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None
    completed_at: datetime | None = None


class OrderOut(BaseModel):
    order_no: str
    amount: Decimal
    credit_count: int
    credit_type: CreditType
    status: OrderStatus
    created_at: datetime
    expires_at: datetime
    paid_at: datetime | None = None
    closed_at: datetime | None = None
    refund_eligible: bool
    refund_deadline: datetime | None = None
    refund_ineligible_reason: str | None = None
    latest_refund: RefundOut | None = None


class OrderListOut(BaseModel):
    items: list[OrderOut]
    total: int
    page: int
    page_size: int


class RefundListOut(BaseModel):
    items: list[RefundOut]
    total: int
    page: int
    page_size: int
