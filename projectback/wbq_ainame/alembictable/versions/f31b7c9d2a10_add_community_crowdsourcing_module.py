"""add community crowdsourcing module

Revision ID: f31b7c9d2a10
Revises: d7e3a15c9b20
Create Date: 2026-08-11

该迁移仅随代码交付，不由应用启动自动执行。
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f31b7c9d2a10"
down_revision: Union[str, None] = "d7e3a15c9b20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "community_topic",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="open", nullable=False),
        sa.Column("is_featured", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("featured_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_community_topic_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_community_topic")),
    )
    for column in ("user_id", "status", "is_featured", "created_at"):
        op.create_index(op.f(f"ix_community_topic_{column}"), "community_topic", [column])

    op.create_table(
        "community_candidate",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("meaning", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="visible", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["community_topic.id"], ondelete="CASCADE", name=op.f("fk_community_candidate_topic_id_community_topic")),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_community_candidate_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_community_candidate")),
        sa.UniqueConstraint("topic_id", "name", name="uq_community_candidate_topic_name"),
    )
    op.create_index(op.f("ix_community_candidate_topic_id"), "community_candidate", ["topic_id"])
    op.create_index(op.f("ix_community_candidate_user_id"), "community_candidate", ["user_id"])
    op.create_index(op.f("ix_community_candidate_status"), "community_candidate", ["status"])

    op.create_table(
        "community_vote",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["community_topic.id"], ondelete="CASCADE", name=op.f("fk_community_vote_topic_id_community_topic")),
        sa.ForeignKeyConstraint(["candidate_id"], ["community_candidate.id"], ondelete="CASCADE", name=op.f("fk_community_vote_candidate_id_community_candidate")),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_community_vote_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_community_vote")),
        sa.UniqueConstraint("topic_id", "user_id", name="uq_community_vote_topic_user"),
    )
    for column in ("topic_id", "candidate_id", "user_id"):
        op.create_index(op.f(f"ix_community_vote_{column}"), "community_vote", [column])

    op.create_table(
        "community_comment",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="visible", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["community_topic.id"], ondelete="CASCADE", name=op.f("fk_community_comment_topic_id_community_topic")),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_community_comment_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_community_comment")),
    )
    for column in ("topic_id", "user_id", "status", "created_at"):
        op.create_index(op.f(f"ix_community_comment_{column}"), "community_comment", [column])

    op.create_table(
        "community_report",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("reporter_user_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=20), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=30), nullable=False),
        sa.Column("detail", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("resolution", sa.String(length=500), nullable=True),
        sa.Column("resolved_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["user.id"], name=op.f("fk_community_report_reporter_user_id_user")),
        sa.ForeignKeyConstraint(["resolved_by"], ["user.id"], name=op.f("fk_community_report_resolved_by_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_community_report")),
        sa.UniqueConstraint("reporter_user_id", "target_type", "target_id", name="uq_community_report_user_target"),
    )
    for column in ("reporter_user_id", "target_type", "target_id", "status", "created_at"):
        op.create_index(op.f(f"ix_community_report_{column}"), "community_report", [column])


def downgrade() -> None:
    for table in (
        "community_report",
        "community_comment",
        "community_vote",
        "community_candidate",
        "community_topic",
    ):
        op.drop_table(table)
