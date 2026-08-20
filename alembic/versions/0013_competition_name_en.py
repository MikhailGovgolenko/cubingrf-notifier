"""add name_en to competitions

The English competition name is scraped from the competition detail page on
cubingrf.org (the site's second 'text-lg font-bold mb-4' block) and shown to
English-speaking users. NULL means the site does not provide an English name.

Revision ID: 0013_competition_name_en
Revises: 0012_competition_cancelled_at
Create Date: 2026-08-20 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0013_competition_name_en'
down_revision: Union[str, Sequence[str], None] = '0012_competition_cancelled_at'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'competitions',
        sa.Column('name_en', sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('competitions', 'name_en')