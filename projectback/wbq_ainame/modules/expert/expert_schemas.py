from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExpertApplicationIn(BaseModel):
    display_name: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=2, max_length=100)
    bio: str = Field(min_length=20, max_length=3000)
    specialties: str = Field(min_length=2, max_length=500)
    experience_years: int = Field(ge=0, le=80)


class ExpertProfileOut(BaseModel):
    id: int
    user_id: int
    display_name: str
    title: str
    bio: str
    specialties: str
    expert_level: str = "ordinary"
    experience_years: int
    status: str
    review_note: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None
    average_rating: float = 0
    review_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class ExpertApplicationOut(ExpertProfileOut):
    credential_file_name: str | None = None


class ExpertPackageIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=20, max_length=5000)
    deliverables: str = Field(min_length=5, max_length=3000)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    delivery_days: int = Field(ge=1, le=7)


class ExpertPackageOut(BaseModel):
    id: int
    expert_id: int
    name: str
    description: str
    deliverables: str
    price: Decimal
    delivery_days: int
    revision_count: int
    status: str
    review_note: str | None = None
    expert_name: str | None = None
    expert_title: str | None = None
    average_rating: float = 0
    review_count: int = 0
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ExpertOrderCreateIn(BaseModel):
    package_id: int | None = None
    expert_level: Literal["ordinary", "renowned", "top"] = "ordinary"
    service_mode: Literal["naming", "review"] = "naming"
    candidate_name: str | None = Field(default=None, max_length=100)
    naming_type: Literal["person", "company", "pet"]
    surname: str | None = Field(default=None, max_length=20)
    gender: Literal["unspecified", "male", "female"] | None = None
    birth_datetime: datetime | None = None
    birth_calendar: Literal["solar", "lunar"] | None = None
    birthplace: str | None = Field(default=None, max_length=200)
    five_elements: str | None = Field(default=None, max_length=200)
    generation_character: str | None = Field(default=None, max_length=20)
    avoid_characters: str | None = Field(default=None, max_length=200)
    parent_expectations: str | None = Field(default=None, max_length=3000)
    submitted_content: str | None = Field(default=None, max_length=5000)
    background: str = Field(min_length=10, max_length=5000)
    focus: str = Field(min_length=2, max_length=500)
    notes: str | None = Field(default=None, max_length=3000)

    @model_validator(mode="after")
    def validate_naming_request(self):
        self.candidate_name = (self.candidate_name or "").strip() or None
        self.surname = (self.surname or "").strip() or None
        if self.service_mode == "review" and not self.candidate_name:
            raise ValueError("名字精批必须填写待分析的名字")
        if self.service_mode == "naming" and self.naming_type == "person" and not self.surname:
            raise ValueError("人名专家起名必须填写姓氏")
        return self


class ExpertOrderOut(BaseModel):
    id: int
    order_no: str
    user_id: int
    expert_id: int | None = None
    package_id: int | None = None
    expert_level: str
    package_name: str
    amount: Decimal
    delivery_days: int
    commission_rate: Decimal
    platform_fee: Decimal
    expert_income: Decimal
    service_mode: str
    candidate_name: str | None = None
    naming_type: str
    surname: str | None = None
    gender: str | None = None
    birth_datetime: datetime | None = None
    birth_calendar: str | None = None
    birthplace: str | None = None
    five_elements: str | None = None
    generation_character: str | None = None
    avoid_characters: str | None = None
    parent_expectations: str | None = None
    submitted_content: str | None = None
    background: str
    focus: str
    notes: str | None = None
    payment_status: str
    service_status: str
    settlement_status: str
    revision_used: bool
    revision_reason: str | None = None
    dispute_reason: str | None = None
    admin_note: str | None = None
    created_at: datetime
    paid_at: datetime | None = None
    accept_deadline: datetime | None = None
    delivery_deadline: datetime | None = None
    delivered_at: datetime | None = None
    confirm_deadline: datetime | None = None
    completed_at: datetime | None = None
    expert_name: str | None = None
    report_version: int | None = None
    image_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class ExpertOrderCreatedOut(ExpertOrderOut):
    pay_url: str


class TextReasonIn(BaseModel):
    reason: str = Field(min_length=2, max_length=1000)


class ExpertReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    content: str | None = Field(default=None, max_length=1000)


class ExpertReportOut(BaseModel):
    id: int
    order_id: int
    version: int
    conclusion: str
    analysis: str
    suggestions: str
    recommended_names: str | None = None
    five_elements_analysis: str | None = None
    final_reply: str | None = None
    attachment_name: str | None = None
    attachment_size: int | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ExpertReportIn(BaseModel):
    conclusion: str = Field(min_length=10, max_length=1000)
    analysis: str = Field(min_length=30, max_length=10000)
    suggestions: str = Field(min_length=10, max_length=5000)
    recommended_names: str | None = Field(default=None, max_length=5000)
    five_elements_analysis: str | None = Field(default=None, max_length=10000)
    final_reply: str | None = Field(default=None, max_length=10000)


class ExpertOrderAttachmentOut(BaseModel):
    id: int
    order_id: int
    file_name: str
    file_size: int
    content_type: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AdminDecisionIn(BaseModel):
    decision: Literal["approve", "reject", "suspend", "restore", "offline"]
    note: str | None = Field(default=None, max_length=500)
    expert_level: Literal["ordinary", "renowned", "top"] | None = None


class ExpertTierOut(BaseModel):
    code: str
    name: str
    price: Decimal
    delivery_days: int
    description: str


class AdminDisputeIn(BaseModel):
    resolution: Literal["complete", "refund"]
    note: str = Field(min_length=2, max_length=500)
    refund_reference: str | None = Field(default=None, max_length=100)


class SettlementCreateIn(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    remark: str | None = Field(default=None, max_length=500)


class SettlementProcessIn(BaseModel):
    decision: Literal["paid", "reject"]
    note: str | None = Field(default=None, max_length=500)
    payment_reference: str | None = Field(default=None, max_length=100)


class SettlementOut(BaseModel):
    id: int
    expert_id: int
    amount: Decimal
    status: str
    remark: str | None = None
    payment_reference: str | None = None
    created_at: datetime
    processed_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class IncomeSummaryOut(BaseModel):
    available: Decimal
    pending: Decimal
    paid: Decimal
