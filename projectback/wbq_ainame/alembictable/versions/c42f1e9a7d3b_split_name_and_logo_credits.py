"""split name and logo credits

Revision ID: c42f1e9a7d3b
Revises: b91f2c8a4d10
Create Date: 2026-08-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c42f1e9a7d3b"
down_revision: Union[str, None] = "b91f2c8a4d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LOGO_PACKAGES = (
    ("Logo 入门包", "19.90", 3),
    ("Logo 进阶包", "39.90", 8),
    ("Logo 专业包", "69.90", 15),
)


def upgrade() -> None:
    op.add_column(
        "user_credit",
        sa.Column("logo_balance", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "user_credit",
        sa.Column("logo_total_used", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "user_credit",
        sa.Column("logo_total_recharge", sa.Integer(), server_default="0", nullable=False),
    )

    op.add_column(
        "package",
        sa.Column("credit_type", sa.String(length=20), server_default="name", nullable=False),
    )
    op.add_column(
        "user_order",
        sa.Column("credit_type", sa.String(length=20), server_default="name", nullable=False),
    )
    op.add_column(
        "credit_log",
        sa.Column("credit_type", sa.String(length=20), server_default="name", nullable=False),
    )

    op.create_index(op.f("ix_package_credit_type"), "package", ["credit_type"], unique=False)
    op.create_check_constraint(
        "ck_package_credit_type",
        "package",
        "credit_type IN ('name', 'logo')",
    )
    op.create_check_constraint(
        "ck_user_order_credit_type",
        "user_order",
        "credit_type IN ('name', 'logo')",
    )
    op.create_check_constraint(
        "ck_credit_log_credit_type",
        "credit_log",
        "credit_type IN ('name', 'logo')",
    )

    # MySQL 的条件插入同时支持在线升级和 --sql 离线审查。
    for name, price, credit_count in LOGO_PACKAGES:
        op.execute(
            "INSERT INTO package "
            "(name, price, credit_count, credit_type, is_active, created_at) "
            f"SELECT '{name}', {price}, {credit_count}, 'logo', 1, CURRENT_TIMESTAMP "
            "FROM DUAL "
            f"WHERE NOT EXISTS (SELECT 1 FROM package WHERE name = '{name}')"
        )


def downgrade() -> None:
    # 降级时把 Logo 余额及累计值合并回起名字段，避免次数直接丢失。
    op.execute(
        "UPDATE user_credit SET "
        "balance = balance + logo_balance, "
        "total_used = total_used + logo_total_used, "
        "total_recharge = total_recharge + logo_total_recharge"
    )

    op.drop_constraint("ck_credit_log_credit_type", "credit_log", type_="check")
    op.drop_constraint("ck_user_order_credit_type", "user_order", type_="check")
    op.drop_constraint("ck_package_credit_type", "package", type_="check")
    op.drop_index(op.f("ix_package_credit_type"), table_name="package")

    op.drop_column("credit_log", "credit_type")
    op.drop_column("user_order", "credit_type")
    op.drop_column("package", "credit_type")
    op.drop_column("user_credit", "logo_total_recharge")
    op.drop_column("user_credit", "logo_total_used")
    op.drop_column("user_credit", "logo_balance")
