"""add username to users

Revision ID: 9abca79e9b82
Revises: 0008_user_events
Create Date: 2026-08-05 21:46:43.196737

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = '9abca79e9b82'
down_revision: Union[str, Sequence[str], None] = '0008_user_events'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass