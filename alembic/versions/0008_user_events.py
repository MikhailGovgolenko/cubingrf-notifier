"""rename user_disciplines table and columns to events

Revision ID: 0008_user_events
Revises: 0007_registration_start_and_kind
Create Date: 2026-08-05 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '0008_user_events'
down_revision = '0007_registration_start_and_kind'
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table('user_disciplines', 'user_events')
    op.alter_column(
        'user_events',
        'discipline_code',
        new_column_name='event_code',
    )
    # The unique constraint keeps its auto-generated name on a table/column
    # rename in PostgreSQL, so rename it explicitly for consistency.
    if op.get_bind().dialect.name == 'postgresql':
        op.execute(
            'ALTER TABLE user_events '
            'RENAME CONSTRAINT uq_user_discipline TO uq_user_event'
        )


def downgrade():
    if op.get_bind().dialect.name == 'postgresql':
        op.execute(
            'ALTER TABLE user_events '
            'RENAME CONSTRAINT uq_user_event TO uq_user_discipline'
        )
    op.alter_column(
        'user_events',
        'event_code',
        new_column_name='discipline_code',
    )
    op.rename_table('user_events', 'user_disciplines')