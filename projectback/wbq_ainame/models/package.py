from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from . import Base

# 创建套餐表
class Package(Base):
    __tablename__ = "package"
    __table_args__ = (
        CheckConstraint("credit_type IN ('name', 'logo')", name="ck_package_credit_type"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)
    # 套餐名称
    name: Mapped[str] = mapped_column(String(100),unique=True,nullable=False)
    # 套餐价格   Numeric(10, 2) 和 Decimal  精确的浮点数
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # 套餐包含的对应业务次数
    credit_count: Mapped[int] = mapped_column(Integer, nullable=False)
    # name 为起名套餐，logo 为 Logo 生成套餐
    credit_type: Mapped[str] = mapped_column(String(20), default="name", nullable=False, index=True)
    # 是否上架
    is_active: Mapped[bool] = mapped_column(Boolean, default=True,nullable=False)
    # 创建的时间
    created_at: Mapped[datetime] = mapped_column(DateTime,default=datetime.now,nullable=False)
