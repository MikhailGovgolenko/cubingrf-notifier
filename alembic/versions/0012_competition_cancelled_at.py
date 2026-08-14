"""add cancelled_at to competitions

Tracks when the scraper first observed a competition as cancelled, so it can
be kept visible for a 24-hour grace window and then hidden. The timestamp is
set exactly once (never reset on repeated scraper runs).

Revision ID: 0012_competition_cancelled_at
Revises: 0011_round_result_tracking
Create Date: 2026-08-14 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0012_competition_cancelled_at'
down_revision: Union[str, Sequence[str], None] = '0011_round_result_tracking'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'competitions',
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('competitions', 'cancelled_at')
