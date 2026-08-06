"""add per-type notification preferences and split Moscow region

Adds the independent announcement / registration switches plus the reminder
interval to ``users``, and splits the combined "Москва" region into two
distinct regions: existing users who selected "Москва" also get
"Московская область" (their previous settings are preserved).

Revision ID: 0009_user_notifications
Revises: c5d1e3f2a0b4
Create Date: 2026-08-06 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '0009_user_notifications'
down_revision = 'c5d1e3f2a0b4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'users',
        sa.Column('announcements_enabled', sa.Boolean(), nullable=False, server_default='true'),
    )
    op.add_column(
        'users',
        sa.Column('registration_notifications_enabled', sa.Boolean(), nullable=False, server_default='true'),
    )
    op.add_column(
        'users',
        sa.Column('reg_reminder_interval', sa.Integer(), nullable=False, server_default='30'),
    )

    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        # Existing users who followed Moscow now follow both Moscow and Moscow
        # Oblast. Do not remove any of their existing settings.
        op.execute(
            "INSERT INTO user_regions (user_id, region_key) "
            "SELECT ur.user_id, 'Московская область' "
            "FROM user_regions ur "
            "WHERE ur.region_key = 'Москва' "
            "AND NOT EXISTS ("
            "  SELECT 1 FROM user_regions x "
            "  WHERE x.user_id = ur.user_id AND x.region_key = 'Московская область'"
            ")"
        )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        # Reverse the region split: drop the auto-added Moscow Oblast rows that
        # were created for users who originally only had Moscow.
        op.execute(
            "DELETE FROM user_regions ur "
            "WHERE ur.region_key = 'Московская область' "
            "AND EXISTS ("
            "  SELECT 1 FROM user_regions m "
            "  WHERE m.user_id = ur.user_id AND m.region_key = 'Москва'"
            ")"
        )
    op.drop_column('users', 'reg_reminder_interval')
    op.drop_column('users', 'registration_notifications_enabled')
    op.drop_column('users', 'announcements_enabled')
