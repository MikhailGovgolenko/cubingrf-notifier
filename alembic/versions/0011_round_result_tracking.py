"""round result tracking

Adds the user's RSF ID and the per-type round-result switch to ``users`` and
creates the ``round_result_states`` table that the poller uses to detect new
vs. edited results.

Revision ID: 0011_round_result_tracking
Revises: 0010_reconcile_users_columns
Create Date: 2026-08-11 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0011_round_result_tracking'
down_revision: Union[str, Sequence[str], None] = '0010_reconcile_users_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = {c['name'] for c in insp.get_columns('users')}

    if 'rsf_id' not in existing:
        op.add_column('users', sa.Column('rsf_id', sa.String(length=32), nullable=True))
    if 'result_notifications_enabled' not in existing:
        op.add_column(
            'users',
            sa.Column('result_notifications_enabled', sa.Boolean(), nullable=False, server_default='true'),
        )

    op.create_table(
        'round_result_states',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('competition_id', sa.Integer(), sa.ForeignKey('competitions.id'), nullable=False),
        sa.Column('event_code', sa.String(length=20), nullable=False),
        sa.Column('round_number', sa.Integer(), nullable=False),
        sa.Column('registrant_id', sa.Integer(), nullable=True),
        sa.Column('completed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('result_hash', sa.String(length=64), nullable=True),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            'user_id', 'competition_id', 'event_code', 'round_number',
            name='uq_rrs_user_competition_event_round',
        ),
    )


def downgrade() -> None:
    op.drop_table('round_result_states')
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = {c['name'] for c in insp.get_columns('users')}
    if 'result_notifications_enabled' in existing:
        op.drop_column('users', 'result_notifications_enabled')
    if 'rsf_id' in existing:
        op.drop_column('users', 'rsf_id')
