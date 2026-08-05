"""add competition end_date

Revision ID: 0006_competition_end_date
Revises: 0005_user_regions
Create Date: 2026-08-05 13:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '0006_competition_end_date'
down_revision = '0005_user_regions'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'competitions',
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column('competitions', 'end_date')
