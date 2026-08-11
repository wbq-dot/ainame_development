from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from . import Base


class OrderRefund(Base):
    __tablename__ = "order_refund"
    __table_args__ = (
        CheckConstraint(
            "credit_type IN ('name', 'logo')",
            name="ck_order_refund_credit_type",
        ),
        CheckConstraint(
            "origin IN ('user_request', 'late_payment')",
            name="ck_order_refund_origin",
        ),
        CheckConstraint(
            "status IN ('requested', 'rejected', 'processing', 'succeeded', 'failed')",
            name="ck_order_refund_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    refund_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_order.id"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id"), index=True, nullable=False
    )
    origin: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="requested", index=True, nullable=False
    )
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    credit_count: Mapped[int] = mapped_column(Integer, nullable=False)
    credit_type: Mapped[str] = mapped_column(String(20), nullable=False)
    reserved_credit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reservation_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=True, index=True
    )
    review_note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    alipay_trade_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider_refund_fee: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )
    last_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
