"""merge expert and admin payment heads

Revision ID: 635d54ccf2af
Revises: f3c9b7e12a64, d7e3a15c9b20
Create Date: 2026-08-11 19:04:31.189270

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '635d54ccf2af'
down_revision: Union[str, None] = ('f3c9b7e12a64', 'd7e3a15c9b20')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
