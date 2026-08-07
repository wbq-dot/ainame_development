"""add admin user management

Revision ID: b91f2c8a4d10
Revises: 6a618da337cc
Create Date: 2026-08-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b91f2c8a4d10"
down_revision: Union[str, None] = "6a618da337cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("role", sa.String(length=20), server_default="user", nullable=False),
    )
    op.add_column(
        "user",
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
    )
    op.add_column(
        "user",
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.add_column(
        "user",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.add_column("user", sa.Column("frozen_at", sa.DateTime(), nullable=True))
    op.add_column("user", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_index(op.f("ix_user_role"), "user", ["role"], unique=False)
    op.create_index(op.f("ix_user_status"), "user", ["status"], unique=False)

    op.create_table(
        "admin_action_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("admin_user_id", sa.Integer(), nullable=False),
        sa.Column("target_user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["admin_user_id"],
            ["user.id"],
            name=op.f("fk_admin_action_log_admin_user_id_user"),
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["user.id"],
            name=op.f("fk_admin_action_log_target_user_id_user"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admin_action_log")),
    )
    op.create_index(
        op.f("ix_admin_action_log_admin_user_id"),
        "admin_action_log",
        ["admin_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admin_action_log_target_user_id"),
        "admin_action_log",
        ["target_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admin_action_log_action"),
        "admin_action_log",
        ["action"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_admin_action_log_action"), table_name="admin_action_log")
    op.drop_index(op.f("ix_admin_action_log_target_user_id"), table_name="admin_action_log")
    op.drop_index(op.f("ix_admin_action_log_admin_user_id"), table_name="admin_action_log")
    op.drop_table("admin_action_log")
    op.drop_index(op.f("ix_user_status"), table_name="user")
    op.drop_index(op.f("ix_user_role"), table_name="user")
    op.drop_column("user", "deleted_at")
    op.drop_column("user", "frozen_at")
    op.drop_column("user", "updated_at")
    op.drop_column("user", "created_at")
    op.drop_column("user", "status")
    op.drop_column("user", "role")
