"""add user interface language

Revision ID: 0004_user_language
Revises: 0003_reg_status_disciplines
Create Date: 2026-08-05 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '0004_user_language'
down_revision = '0003_reg_status_disciplines'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'users',
        sa.Column('language', sa.String(length=10), nullable=False, server_default='ru'),
    )


def downgrade():
    op.drop_column('users', 'language')