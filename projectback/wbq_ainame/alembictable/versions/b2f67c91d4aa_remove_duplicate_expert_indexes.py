"""remove duplicate expert unique indexes

Revision ID: b2f67c91d4aa
Revises: a83d9f4e2c11
Create Date: 2026-08-10
"""

from typing import Sequence, Union

from alembic import op


revision: str = "b2f67c91d4aa"
down_revision: Union[str, None] = "a83d9f4e2c11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # mapped_column(unique=True, index=True) 已由 ix_* 唯一索引保证约束。
    op.drop_index("uq_expert_order_order_no", table_name="expert_order")
    op.drop_index("uq_expert_profile_user_id", table_name="expert_profile")


def downgrade() -> None:
    op.create_index(
        "uq_expert_profile_user_id",
        "expert_profile",
        ["user_id"],
        unique=True,
    )
    op.create_index(
        "uq_expert_order_order_no",
        "expert_order",
        ["order_no"],
        unique=True,
    )

