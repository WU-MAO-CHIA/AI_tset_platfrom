"""add_execution_schedules

Revision ID: 7c3e9a1f2b40
Revises: 61b1dcb1da0f
Create Date: 2026-10-25 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c3e9a1f2b40'
down_revision: Union[str, Sequence[str], None] = '61b1dcb1da0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('execution_schedules',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('checklist_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('frequency', sa.String(length=20), nullable=False),
    sa.Column('time_of_day', sa.String(length=5), nullable=True),
    sa.Column('weekdays', sa.JSON(), nullable=True),
    sa.Column('interval_minutes', sa.Integer(), nullable=True),
    sa.Column('parallel_mode', sa.Boolean(), nullable=False),
    sa.Column('max_workers', sa.Integer(), nullable=False),
    sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_execution_id', sa.String(length=36), nullable=True),
    sa.Column('last_skip_reason', sa.String(length=100), nullable=True),
    sa.Column('created_by', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['checklist_id'], ['test_checklists.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('execution_schedules', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_execution_schedules_checklist_id'), ['checklist_id'], unique=False)
        batch_op.create_index('ix_execution_schedules_due', ['enabled', 'next_run_at'], unique=False)

    with op.batch_alter_table('execution_records', schema=None) as batch_op:
        batch_op.add_column(sa.Column('schedule_id', sa.String(length=36), nullable=True))
        batch_op.create_index(batch_op.f('ix_execution_records_schedule_id'), ['schedule_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('execution_records', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_execution_records_schedule_id'))
        batch_op.drop_column('schedule_id')

    with op.batch_alter_table('execution_schedules', schema=None) as batch_op:
        batch_op.drop_index('ix_execution_schedules_due')
        batch_op.drop_index(batch_op.f('ix_execution_schedules_checklist_id'))

    op.drop_table('execution_schedules')
