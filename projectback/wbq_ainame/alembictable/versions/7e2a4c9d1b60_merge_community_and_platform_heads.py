"""merge community and platform migration heads

Revision ID: 7e2a4c9d1b60
Revises: 635d54ccf2af, f31b7c9d2a10
Create Date: 2026-08-11
"""

from typing import Sequence, Union


revision: str = "7e2a4c9d1b60"
down_revision: Union[str, tuple[str, str], None] = (
    "635d54ccf2af",
    "f31b7c9d2a10",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
