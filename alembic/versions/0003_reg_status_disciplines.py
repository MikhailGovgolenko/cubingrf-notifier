"""add registration status and user discipline preferences

Revision ID: 0003_reg_status_disciplines
Revises: 0002_user_settings
Create Date: 2026-08-04 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '0003_reg_status_disciplines'
down_revision = '0002_user_settings'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'competitions',
        sa.Column('reg_status', sa.String(length=20), nullable=True),
    )
    op.create_table(
        'user_disciplines',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('discipline_code', sa.String(length=20), nullable=False),
        sa.UniqueConstraint('user_id', 'discipline_code', name='uq_user_discipline'),
    )


def downgrade():
    op.drop_table('user_disciplines')
    op.drop_column('competitions', 'reg_status')