"""add user subscription flag and unique notifications

Revision ID: 0002_user_settings
Revises: 0001_initial_database_models
Create Date: 2026-08-04 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '0002_user_settings'
down_revision = '0001_initial_database_models'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'users',
        sa.Column('notifications_enabled', sa.Boolean(), nullable=False, server_default='true'),
    )
    op.create_unique_constraint(
        'uq_notification_user_competition',
        'notifications',
        ['user_id', 'competition_id'],
    )


def downgrade():
    op.drop_constraint('uq_notification_user_competition', 'notifications', type_='unique')
    op.drop_column('users', 'notifications_enabled')
