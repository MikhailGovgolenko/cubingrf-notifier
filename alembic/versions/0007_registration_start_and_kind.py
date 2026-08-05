"""add registration_start_at and notification kind

Revision ID: 0007_registration_start_and_kind
Revises: 0006_competition_end_date
Create Date: 2026-08-05 14:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '0007_registration_start_and_kind'
down_revision = '0006_competition_end_date'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'competitions',
        sa.Column('registration_start_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'notifications',
        sa.Column('kind', sa.String(20), nullable=False, server_default='new'),
    )
    op.drop_constraint('uq_notification_user_competition', 'notifications', type_='unique')
    op.create_unique_constraint(
        'uq_notification_user_competition_kind',
        'notifications',
        ['user_id', 'competition_id', 'kind'],
    )


def downgrade():
    op.drop_constraint('uq_notification_user_competition_kind', 'notifications', type_='unique')
    op.create_unique_constraint(
        'uq_notification_user_competition',
        'notifications',
        ['user_id', 'competition_id'],
    )
    op.drop_column('notifications', 'kind')
    op.drop_column('competitions', 'registration_start_at')