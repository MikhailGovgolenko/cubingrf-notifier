"""add registration_end_at to competitions

The registration closing moment is scraped from the competition detail page on
cubingrf.org (the "по <date> <time>" part of the registration-window text) and
shown in notifications as a "registration closes in N days" countdown. NULL
means the site gives no closing time.

Revision ID: 0014_registration_end_at
Revises: 0013_competition_name_en
Create Date: 2026-09-02 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0014_registration_end_at'
down_revision: Union[str, Sequence[str], None] = '0013_competition_name_en'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'competitions',
        sa.Column('registration_end_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('competitions', 'registration_end_at')