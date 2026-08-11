"""merge admin and payment migration heads

Revision ID: f3c9b7e12a64
Revises: d8f4a1c2b903, e91b7c4a2f60
Create Date: 2026-08-11
"""

from typing import Sequence, Union


revision: str = "f3c9b7e12a64"
down_revision: Union[str, tuple[str, str], None] = (
    "d8f4a1c2b903",
    "e91b7c4a2f60",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
