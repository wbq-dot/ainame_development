"""add account security and content cleanup state

Revision ID: d4a7f8c91e20
Revises: c42f1e9a7d3b
Create Date: 2026-08-11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4a7f8c91e20"
down_revision: Union[str, None] = "c42f1e9a7d3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("auth_version", sa.Integer(), server_default="0", nullable=False),
    )

    op.create_table(
        "naming_session",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id"),
    )
    op.create_index(
        op.f("ix_naming_session_user_id"),
        "naming_session",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "account_deletion_job",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(), nullable=False),
        sa.Column("last_error", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_account_deletion_job_next_retry_at"),
        "account_deletion_job",
        ["next_retry_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_account_deletion_job_status"),
        "account_deletion_job",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_account_deletion_job_user_id"),
        "account_deletion_job",
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_account_deletion_job_user_id"),
        table_name="account_deletion_job",
    )
    op.drop_index(
        op.f("ix_account_deletion_job_status"),
        table_name="account_deletion_job",
    )
    op.drop_index(
        op.f("ix_account_deletion_job_next_retry_at"),
        table_name="account_deletion_job",
    )
    op.drop_table("account_deletion_job")
    op.drop_index(op.f("ix_naming_session_user_id"), table_name="naming_session")
    op.drop_table("naming_session")
    op.drop_column("user", "auth_version")
