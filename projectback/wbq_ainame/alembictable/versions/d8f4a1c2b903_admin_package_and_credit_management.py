"""add admin package and credit management audit targets

Revision ID: d8f4a1c2b903
Revises: c42f1e9a7d3b
Create Date: 2026-08-11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d8f4a1c2b903"
down_revision: Union[str, None] = "c42f1e9a7d3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "admin_action_log",
        "target_user_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.add_column(
        "admin_action_log",
        sa.Column("target_package_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_admin_action_log_target_package_id"),
        "admin_action_log",
        ["target_package_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_admin_action_log_target_package_id_package"),
        "admin_action_log",
        "package",
        ["target_package_id"],
        ["id"],
    )
    op.create_check_constraint(
        "ck_admin_action_log_exactly_one_target",
        "admin_action_log",
        "(target_user_id IS NOT NULL AND target_package_id IS NULL) OR "
        "(target_user_id IS NULL AND target_package_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_admin_action_log_exactly_one_target",
        "admin_action_log",
        type_="check",
    )
    op.drop_constraint(
        op.f("fk_admin_action_log_target_package_id_package"),
        "admin_action_log",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_admin_action_log_target_package_id"),
        table_name="admin_action_log",
    )
    # 旧结构只能表达用户目标；套餐审计行无法无损映射，降级时仅移除这些新记录。
    op.execute("DELETE FROM admin_action_log WHERE target_user_id IS NULL")
    op.drop_column("admin_action_log", "target_package_id")
    op.alter_column(
        "admin_action_log",
        "target_user_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
