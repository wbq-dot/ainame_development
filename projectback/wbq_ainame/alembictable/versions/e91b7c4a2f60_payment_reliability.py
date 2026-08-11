"""add payment reliability and refunds

Revision ID: e91b7c4a2f60
Revises: d4a7f8c91e20
Create Date: 2026-08-11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e91b7c4a2f60"
down_revision: Union[str, None] = "d4a7f8c91e20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not op.get_context().as_sql:
        bind = op.get_bind()
        duplicate_trade_no = bind.execute(
            sa.text(
                "SELECT alipay_trade_no FROM user_order "
                "WHERE alipay_trade_no IS NOT NULL "
                "GROUP BY alipay_trade_no HAVING COUNT(*) > 1 LIMIT 1"
            )
        ).scalar()
        if duplicate_trade_no:
            raise RuntimeError("检测到重复支付宝交易号，请人工核对后重新执行迁移")

    op.add_column("user_order", sa.Column("expires_at", sa.DateTime(), nullable=True))
    op.add_column("user_order", sa.Column("closed_at", sa.DateTime(), nullable=True))
    op.add_column(
        "user_order", sa.Column("next_reconcile_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "user_order",
        sa.Column("reconcile_attempts", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "user_order", sa.Column("last_reconcile_error", sa.String(1000), nullable=True)
    )
    op.execute(
        "UPDATE user_order SET expires_at = DATE_ADD(created_at, INTERVAL 1 HOUR) "
        "WHERE expires_at IS NULL"
    )
    op.alter_column("user_order", "expires_at", existing_type=sa.DateTime(), nullable=False)
    op.create_index(
        op.f("ix_user_order_expires_at"), "user_order", ["expires_at"], unique=False
    )
    op.create_index(
        op.f("ix_user_order_next_reconcile_at"),
        "user_order",
        ["next_reconcile_at"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_user_order_alipay_trade_no", "user_order", ["alipay_trade_no"]
    )
    op.create_check_constraint(
        "ck_user_order_status",
        "user_order",
        "status IN ('pending', 'paid', 'closed', 'refunding', 'refunded')",
    )

    op.add_column(
        "user_credit",
        sa.Column("total_refund", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "user_credit",
        sa.Column("logo_total_refund", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("credit_log", sa.Column("source_type", sa.String(40), nullable=True))
    op.add_column("credit_log", sa.Column("source_id", sa.String(100), nullable=True))
    op.create_unique_constraint(
        "uq_credit_log_source_type_source_id",
        "credit_log",
        ["source_type", "source_id"],
    )

    op.create_table(
        "order_refund",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("refund_no", sa.String(64), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("origin", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(200), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("credit_count", sa.Integer(), nullable=False),
        sa.Column("credit_type", sa.String(20), nullable=False),
        sa.Column("reserved_credit_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reservation_key", sa.String(120), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("review_note", sa.String(200), nullable=True),
        sa.Column("alipay_trade_no", sa.String(100), nullable=True),
        sa.Column("provider_refund_fee", sa.Numeric(10, 2), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "credit_type IN ('name', 'logo')", name="ck_order_refund_credit_type"
        ),
        sa.CheckConstraint(
            "origin IN ('user_request', 'late_payment')", name="ck_order_refund_origin"
        ),
        sa.CheckConstraint(
            "status IN ('requested', 'rejected', 'processing', 'succeeded', 'failed')",
            name="ck_order_refund_status",
        ),
        sa.ForeignKeyConstraint(["order_id"], ["user_order.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("refund_no"),
    )
    for column in ("order_id", "user_id", "status", "reviewed_by", "next_retry_at"):
        op.create_index(op.f(f"ix_order_refund_{column}"), "order_refund", [column], unique=False)


def downgrade() -> None:
    for column in ("next_retry_at", "reviewed_by", "status", "user_id", "order_id"):
        op.drop_index(op.f(f"ix_order_refund_{column}"), table_name="order_refund")
    op.drop_table("order_refund")
    op.drop_constraint("uq_credit_log_source_type_source_id", "credit_log", type_="unique")
    op.drop_column("credit_log", "source_id")
    op.drop_column("credit_log", "source_type")
    op.drop_column("user_credit", "logo_total_refund")
    op.drop_column("user_credit", "total_refund")
    op.drop_constraint("ck_user_order_status", "user_order", type_="check")
    op.drop_constraint("uq_user_order_alipay_trade_no", "user_order", type_="unique")
    op.drop_index(op.f("ix_user_order_next_reconcile_at"), table_name="user_order")
    op.drop_index(op.f("ix_user_order_expires_at"), table_name="user_order")
    op.drop_column("user_order", "last_reconcile_error")
    op.drop_column("user_order", "reconcile_attempts")
    op.drop_column("user_order", "next_reconcile_at")
    op.drop_column("user_order", "closed_at")
    op.drop_column("user_order", "expires_at")
