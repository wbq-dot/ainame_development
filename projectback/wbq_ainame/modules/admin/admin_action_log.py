from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models import Base


class AdminActionLog(Base):
    __tablename__ = "admin_action_log"
    __table_args__ = (
        CheckConstraint(
            "(target_user_id IS NOT NULL AND target_package_id IS NULL) OR "
            "(target_user_id IS NULL AND target_package_id IS NOT NULL)",
            name="ck_admin_action_log_exactly_one_target",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user.id"),
        nullable=False,
        index=True,
    )
    target_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("user.id"),
        nullable=True,
        index=True,
    )
    target_package_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("package.id"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )
