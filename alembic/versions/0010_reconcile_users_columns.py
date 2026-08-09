"""reconcile users columns missing from earlier migrations

An earlier revision (9abca79e9b82 "add username to users") was recorded in
alembic_version but had an empty body, so on already-migrated databases the
``username`` column was never actually created. Later revisions (blocked_at,
last_seen_at, per-type notification preferences) did create their columns, but
this corrective migration makes the reconciliation robust: it verifies every
``users`` column that the SQLAlchemy ``User`` model expects and adds any that
are missing (with the same definitions / defaults as the model), skipping the
ones that already exist.

It never drops or alters existing columns, so no user data is touched.

Revision ID: 0010_reconcile_users_columns
Revises: 0009_user_notifications
Create Date: 2026-08-09 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0010_reconcile_users_columns'
down_revision: Union[str, Sequence[str], None] = '0009_user_notifications'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The exact set of columns the User model declares, with their definitions so a
# missing one is recreated identically. (id / telegram_id / created_at are
# always present from 0001; this reconciles the rest.)
_EXPECTED = [
    sa.Column('username', sa.String(length=64), nullable=True),
    sa.Column('notifications_enabled', sa.Boolean(), nullable=False, server_default='true'),
    sa.Column('announcements_enabled', sa.Boolean(), nullable=False, server_default='true'),
    sa.Column('registration_notifications_enabled', sa.Boolean(), nullable=False, server_default='true'),
    sa.Column('reg_reminder_interval', sa.Integer(), nullable=False, server_default='30'),
    sa.Column('language', sa.String(length=10), nullable=False, server_default='ru'),
    sa.Column('blocked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
]


def _existing_columns(bind) -> set:
    insp = sa.inspect(bind)
    return {c['name'] for c in insp.get_columns('users')}


def upgrade() -> None:
    bind = op.get_bind()
    existing = _existing_columns(bind)
    for column in _EXPECTED:
        if column.name not in existing:
            op.add_column('users', column)


def downgrade() -> None:
    # Corrective/reconciliation migration. It only adds missing columns and
    # never tracks which ones pre-existed, so a downgrade could not restore
    # the exact prior state without risking data loss (e.g. dropping a column
    # that legitimately already existed before this migration ran). Making the
    # downgrade a no-op is the safe, non-destructive choice.
    pass