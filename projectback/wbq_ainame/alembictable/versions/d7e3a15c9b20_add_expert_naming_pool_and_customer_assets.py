"""add expert naming pool and customer assets

Revision ID: d7e3a15c9b20
Revises: b2f67c91d4aa
Create Date: 2026-08-10

该迁移仅随代码交付，不由应用启动自动执行。
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7e3a15c9b20"
down_revision: Union[str, None] = "b2f67c91d4aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "expert_profile",
        sa.Column(
            "expert_level",
            sa.String(length=20),
            server_default="ordinary",
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_expert_profile_expert_level"),
        "expert_profile",
        ["expert_level"],
        unique=False,
    )

    op.add_column(
        "expert_order",
        sa.Column(
            "expert_level",
            sa.String(length=20),
            server_default="ordinary",
            nullable=False,
        ),
    )
    op.add_column(
        "expert_order",
        sa.Column(
            "service_mode",
            sa.String(length=20),
            server_default="naming",
            nullable=False,
        ),
    )
    for name, column_type in (
        ("surname", sa.String(length=20)),
        ("gender", sa.String(length=20)),
        ("birth_datetime", sa.DateTime()),
        ("birth_calendar", sa.String(length=20)),
        ("birthplace", sa.String(length=200)),
        ("five_elements", sa.String(length=200)),
        ("generation_character", sa.String(length=20)),
        ("avoid_characters", sa.String(length=200)),
        ("parent_expectations", sa.Text()),
        ("submitted_content", sa.Text()),
    ):
        op.add_column("expert_order", sa.Column(name, column_type, nullable=True))
    op.alter_column(
        "expert_order",
        "expert_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "expert_order",
        "package_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "expert_order",
        "candidate_name",
        existing_type=sa.String(length=100),
        nullable=True,
    )
    op.create_index(
        op.f("ix_expert_order_expert_level"),
        "expert_order",
        ["expert_level"],
        unique=False,
    )

    op.add_column("expert_report", sa.Column("recommended_names", sa.Text(), nullable=True))
    op.add_column(
        "expert_report", sa.Column("five_elements_analysis", sa.Text(), nullable=True)
    )
    op.add_column("expert_report", sa.Column("final_reply", sa.Text(), nullable=True))

    op.create_table(
        "expert_order_attachment",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("file_key", sa.String(length=120), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["expert_order.id"],
            name=op.f("fk_expert_order_attachment_order_id_expert_order"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_expert_order_attachment")),
        sa.UniqueConstraint("file_key", name=op.f("uq_expert_order_attachment_file_key")),
    )
    op.create_index(
        op.f("ix_expert_order_attachment_order_id"),
        "expert_order_attachment",
        ["order_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_expert_order_attachment_order_id"),
        table_name="expert_order_attachment",
    )
    op.drop_table("expert_order_attachment")
    for column in ("final_reply", "five_elements_analysis", "recommended_names"):
        op.drop_column("expert_report", column)
    op.drop_index(op.f("ix_expert_order_expert_level"), table_name="expert_order")
    op.alter_column(
        "expert_order",
        "candidate_name",
        existing_type=sa.String(length=100),
        nullable=False,
    )
    op.alter_column(
        "expert_order",
        "package_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "expert_order",
        "expert_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    for column in (
        "submitted_content",
        "parent_expectations",
        "avoid_characters",
        "generation_character",
        "five_elements",
        "birthplace",
        "birth_calendar",
        "birth_datetime",
        "gender",
        "surname",
        "service_mode",
        "expert_level",
    ):
        op.drop_column("expert_order", column)
    op.drop_index(op.f("ix_expert_profile_expert_level"), table_name="expert_profile")
    op.drop_column("expert_profile", "expert_level")
