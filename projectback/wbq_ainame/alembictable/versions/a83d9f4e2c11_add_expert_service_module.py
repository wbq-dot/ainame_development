"""add expert service module

Revision ID: a83d9f4e2c11
Revises: c42f1e9a7d3b
Create Date: 2026-08-10

该迁移仅随代码交付，不由应用启动自动执行。
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a83d9f4e2c11"
down_revision: Union[str, None] = "c42f1e9a7d3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "expert_profile",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("bio", sa.Text(), nullable=False),
        sa.Column("specialties", sa.String(length=500), nullable=False),
        sa.Column("experience_years", sa.Integer(), nullable=False),
        sa.Column("credential_file_key", sa.String(length=120), nullable=True),
        sa.Column("credential_file_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("review_note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_expert_profile_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_expert_profile")),
        sa.UniqueConstraint("user_id", name=op.f("uq_expert_profile_user_id")),
    )
    op.create_index(op.f("ix_expert_profile_user_id"), "expert_profile", ["user_id"], unique=True)
    op.create_index(op.f("ix_expert_profile_status"), "expert_profile", ["status"], unique=False)

    op.create_table(
        "expert_service_package",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("expert_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("deliverables", sa.Text(), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("delivery_days", sa.Integer(), nullable=False),
        sa.Column("revision_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("review_note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("delivery_days BETWEEN 1 AND 7", name=op.f("ck_expert_service_package_expert_package_delivery_days")),
        sa.CheckConstraint("price > 0", name=op.f("ck_expert_service_package_expert_package_price")),
        sa.ForeignKeyConstraint(["expert_id"], ["expert_profile.id"], name=op.f("fk_expert_service_package_expert_id_expert_profile")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_expert_service_package")),
    )
    op.create_index(op.f("ix_expert_service_package_expert_id"), "expert_service_package", ["expert_id"], unique=False)
    op.create_index(op.f("ix_expert_service_package_status"), "expert_service_package", ["status"], unique=False)

    op.create_table(
        "expert_order",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_no", sa.String(length=100), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expert_id", sa.Integer(), nullable=False),
        sa.Column("package_id", sa.Integer(), nullable=False),
        sa.Column("package_name", sa.String(length=100), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("delivery_days", sa.Integer(), nullable=False),
        sa.Column("commission_rate", sa.Numeric(5, 4), nullable=False),
        sa.Column("platform_fee", sa.Numeric(10, 2), nullable=False),
        sa.Column("expert_income", sa.Numeric(10, 2), nullable=False),
        sa.Column("candidate_name", sa.String(length=100), nullable=False),
        sa.Column("naming_type", sa.String(length=20), nullable=False),
        sa.Column("background", sa.Text(), nullable=False),
        sa.Column("focus", sa.String(length=500), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("payment_status", sa.String(length=20), nullable=False),
        sa.Column("service_status", sa.String(length=30), nullable=False),
        sa.Column("settlement_status", sa.String(length=20), nullable=False),
        sa.Column("alipay_trade_no", sa.String(length=100), nullable=True),
        sa.Column("revision_used", sa.Boolean(), nullable=False),
        sa.Column("revision_reason", sa.String(length=1000), nullable=True),
        sa.Column("dispute_reason", sa.String(length=1000), nullable=True),
        sa.Column("admin_note", sa.String(length=500), nullable=True),
        sa.Column("refund_reference", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("accept_deadline", sa.DateTime(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("delivery_deadline", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("confirm_deadline", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("refunded_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["expert_id"], ["expert_profile.id"], name=op.f("fk_expert_order_expert_id_expert_profile")),
        sa.ForeignKeyConstraint(["package_id"], ["expert_service_package.id"], name=op.f("fk_expert_order_package_id_expert_service_package")),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_expert_order_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_expert_order")),
        sa.UniqueConstraint("order_no", name=op.f("uq_expert_order_order_no")),
    )
    for column in ("order_no", "user_id", "expert_id", "package_id", "payment_status", "service_status", "settlement_status"):
        op.create_index(op.f(f"ix_expert_order_{column}"), "expert_order", [column], unique=column == "order_no")

    op.create_table(
        "expert_report",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("conclusion", sa.String(length=1000), nullable=False),
        sa.Column("analysis", sa.Text(), nullable=False),
        sa.Column("suggestions", sa.Text(), nullable=False),
        sa.Column("attachment_key", sa.String(length=120), nullable=True),
        sa.Column("attachment_name", sa.String(length=255), nullable=True),
        sa.Column("attachment_size", sa.Integer(), nullable=True),
        sa.Column("attachment_mime", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["expert_order.id"], name=op.f("fk_expert_report_order_id_expert_order")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_expert_report")),
        sa.UniqueConstraint("order_id", "version", name="uq_expert_report_order_version"),
    )
    op.create_index(op.f("ix_expert_report_order_id"), "expert_report", ["order_id"], unique=False)

    op.create_table(
        "expert_review",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expert_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("content", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name=op.f("ck_expert_review_expert_review_rating")),
        sa.ForeignKeyConstraint(["expert_id"], ["expert_profile.id"], name=op.f("fk_expert_review_expert_id_expert_profile")),
        sa.ForeignKeyConstraint(["order_id"], ["expert_order.id"], name=op.f("fk_expert_review_order_id_expert_order")),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_expert_review_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_expert_review")),
        sa.UniqueConstraint("order_id", name="uq_expert_review_order_id"),
    )
    op.create_index(op.f("ix_expert_review_user_id"), "expert_review", ["user_id"], unique=False)
    op.create_index(op.f("ix_expert_review_expert_id"), "expert_review", ["expert_id"], unique=False)

    op.create_table(
        "expert_settlement_request",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("expert_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("remark", sa.String(length=500), nullable=True),
        sa.Column("payment_reference", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["expert_id"], ["expert_profile.id"], name=op.f("fk_expert_settlement_request_expert_id_expert_profile")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_expert_settlement_request")),
    )
    op.create_index(op.f("ix_expert_settlement_request_expert_id"), "expert_settlement_request", ["expert_id"], unique=False)
    op.create_index(op.f("ix_expert_settlement_request_status"), "expert_settlement_request", ["status"], unique=False)

    op.create_table(
        "expert_income",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("expert_id", sa.Integer(), nullable=False),
        sa.Column("gross_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("platform_fee", sa.Numeric(10, 2), nullable=False),
        sa.Column("net_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("settlement_request_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["expert_id"], ["expert_profile.id"], name=op.f("fk_expert_income_expert_id_expert_profile")),
        sa.ForeignKeyConstraint(["order_id"], ["expert_order.id"], name=op.f("fk_expert_income_order_id_expert_order")),
        sa.ForeignKeyConstraint(["settlement_request_id"], ["expert_settlement_request.id"], name=op.f("fk_expert_income_settlement_request_id_expert_settlement_request")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_expert_income")),
        sa.UniqueConstraint("order_id", name=op.f("uq_expert_income_order_id")),
    )
    op.create_index(op.f("ix_expert_income_expert_id"), "expert_income", ["expert_id"], unique=False)
    op.create_index(op.f("ix_expert_income_status"), "expert_income", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_expert_income_status"), table_name="expert_income")
    op.drop_index(op.f("ix_expert_income_expert_id"), table_name="expert_income")
    op.drop_table("expert_income")
    op.drop_index(op.f("ix_expert_settlement_request_status"), table_name="expert_settlement_request")
    op.drop_index(op.f("ix_expert_settlement_request_expert_id"), table_name="expert_settlement_request")
    op.drop_table("expert_settlement_request")
    op.drop_index(op.f("ix_expert_review_expert_id"), table_name="expert_review")
    op.drop_index(op.f("ix_expert_review_user_id"), table_name="expert_review")
    op.drop_table("expert_review")
    op.drop_index(op.f("ix_expert_report_order_id"), table_name="expert_report")
    op.drop_table("expert_report")
    for column in ("settlement_status", "service_status", "payment_status", "package_id", "expert_id", "user_id", "order_no"):
        op.drop_index(op.f(f"ix_expert_order_{column}"), table_name="expert_order")
    op.drop_table("expert_order")
    op.drop_index(op.f("ix_expert_service_package_status"), table_name="expert_service_package")
    op.drop_index(op.f("ix_expert_service_package_expert_id"), table_name="expert_service_package")
    op.drop_table("expert_service_package")
    op.drop_index(op.f("ix_expert_profile_status"), table_name="expert_profile")
    op.drop_index(op.f("ix_expert_profile_user_id"), table_name="expert_profile")
    op.drop_table("expert_profile")

