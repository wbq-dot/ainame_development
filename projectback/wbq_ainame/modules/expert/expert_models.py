from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from models import Base


class ExpertProfile(Base):
    __tablename__ = "expert_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id"), unique=True, index=True, nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    bio: Mapped[str] = mapped_column(Text, nullable=False)
    specialties: Mapped[str] = mapped_column(String(500), nullable=False)
    expert_level: Mapped[str] = mapped_column(
        String(20), default="ordinary", index=True, nullable=False
    )
    experience_years: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    credential_file_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    credential_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", index=True, nullable=False
    )
    review_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ExpertServicePackage(Base):
    __tablename__ = "expert_service_package"
    __table_args__ = (
        CheckConstraint("delivery_days BETWEEN 1 AND 7", name="expert_package_delivery_days"),
        CheckConstraint("price > 0", name="expert_package_price"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    expert_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("expert_profile.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    deliverables: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    delivery_days: Mapped[int] = mapped_column(Integer, nullable=False)
    revision_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="draft", index=True, nullable=False
    )
    review_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ExpertOrder(Base):
    __tablename__ = "expert_order"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), index=True, nullable=False)
    expert_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("expert_profile.id"), index=True, nullable=True
    )
    package_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("expert_service_package.id"), index=True, nullable=True
    )
    expert_level: Mapped[str] = mapped_column(
        String(20), default="ordinary", index=True, nullable=False
    )
    package_name: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    delivery_days: Mapped[int] = mapped_column(Integer, nullable=False)
    commission_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0.2000"), nullable=False
    )
    platform_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    expert_income: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    service_mode: Mapped[str] = mapped_column(
        String(20), default="naming", nullable=False
    )
    candidate_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    naming_type: Mapped[str] = mapped_column(String(20), nullable=False)
    surname: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    birth_datetime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    birth_calendar: Mapped[str | None] = mapped_column(String(20), nullable=True)
    birthplace: Mapped[str | None] = mapped_column(String(200), nullable=True)
    five_elements: Mapped[str | None] = mapped_column(String(200), nullable=True)
    generation_character: Mapped[str | None] = mapped_column(String(20), nullable=True)
    avoid_characters: Mapped[str | None] = mapped_column(String(200), nullable=True)
    parent_expectations: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    background: Mapped[str] = mapped_column(Text, nullable=False)
    focus: Mapped[str] = mapped_column(String(500), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_status: Mapped[str] = mapped_column(
        String(20), default="unpaid", index=True, nullable=False
    )
    service_status: Mapped[str] = mapped_column(
        String(30), default="pending_payment", index=True, nullable=False
    )
    settlement_status: Mapped[str] = mapped_column(
        String(20), default="none", index=True, nullable=False
    )
    alipay_trade_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    revision_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revision_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    dispute_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    admin_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    refund_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    accept_deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivery_deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confirm_deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ExpertReport(Base):
    __tablename__ = "expert_report"
    __table_args__ = (
        UniqueConstraint("order_id", "version", name="uq_expert_report_order_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("expert_order.id"), index=True, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    conclusion: Mapped[str] = mapped_column(String(1000), nullable=False)
    analysis: Mapped[str] = mapped_column(Text, nullable=False)
    suggestions: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_names: Mapped[str | None] = mapped_column(Text, nullable=True)
    five_elements_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachment_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    attachment_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attachment_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attachment_mime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class ExpertOrderAttachment(Base):
    __tablename__ = "expert_order_attachment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("expert_order.id"), index=True, nullable=False
    )
    file_key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class ExpertReview(Base):
    __tablename__ = "expert_review"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_expert_review_order_id"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="expert_review_rating"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("expert_order.id"), unique=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), index=True, nullable=False)
    expert_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("expert_profile.id"), index=True, nullable=False
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class ExpertIncome(Base):
    __tablename__ = "expert_income"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("expert_order.id"), unique=True, nullable=False
    )
    expert_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("expert_profile.id"), index=True, nullable=False
    )
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    platform_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="available", index=True, nullable=False
    )
    settlement_request_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("expert_settlement_request.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ExpertSettlementRequest(Base):
    __tablename__ = "expert_settlement_request"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    expert_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("expert_profile.id"), index=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", index=True, nullable=False
    )
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
