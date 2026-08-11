from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import CheckConstraint, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from . import Base
class UserOrder(Base):
    __tablename__ = "user_order"
    __table_args__ = (
        CheckConstraint("credit_type IN ('name', 'logo')", name="ck_user_order_credit_type"),
        CheckConstraint(
            "status IN ('pending', 'paid', 'closed', 'refunding', 'refunded')",
            name="ck_user_order_status",
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)
    # 系统内部订单号   字符串类型可以任意的长度，不限制字符类型
    order_no: Mapped[str] = mapped_column(String(100),unique=True,index=True,nullable=False)
    # 用户 id
    user_id: Mapped[int] = mapped_column(Integer,ForeignKey("user.id"),index=True,nullable=False)
    # 套餐 id
    package_id: Mapped[int] = mapped_column(Integer,ForeignKey("package.id"),nullable=False)
    # 支付金额
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # 购买次数
    credit_count: Mapped[int] = mapped_column(Integer, nullable=False)
    # 下单时保存套餐类型快照，避免套餐后续修改影响到账类型
    credit_type: Mapped[str] = mapped_column(String(20), default="name", nullable=False)
    # 订单状态：pending 待支付，paid 已支付，closed 已关闭
    status: Mapped[str] = mapped_column(String(20), default="pending",nullable=False)
    # 支付宝交易号 只有付款才有交易号
    alipay_trade_no: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True
    )
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime,default=datetime.now,nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now() + timedelta(hours=1),
        nullable=False,
        index=True,
    )
    # 支付时间 可以为空  只有付款才有付款时间
    paid_at: Mapped[datetime | None] = mapped_column(DateTime,nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_reconcile_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )
    reconcile_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_reconcile_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
