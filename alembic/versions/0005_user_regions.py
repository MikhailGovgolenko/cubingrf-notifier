"""add user regions

Revision ID: 0005_user_regions
Revises: 0004_user_language
Create Date: 2026-08-05 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '0005_user_regions'
down_revision = '0004_user_language'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_regions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('region_key', sa.String(length=128), nullable=False),
        sa.UniqueConstraint('user_id', 'region_key', name='uq_user_region'),
    )


def downgrade():
    op.drop_table('user_regions')
