"""add_runner_environments

Revision ID: b3f5d7e9a1c2
Revises: e7a1c4d2b9f3
Create Date: 2026-10-25 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3f5d7e9a1c2'
down_revision: Union[str, Sequence[str], None] = 'e7a1c4d2b9f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'runner_environments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('token_encrypted', sa.Text(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    with op.batch_alter_table('test_cases') as batch_op:
        batch_op.add_column(sa.Column('runner_environment_id', sa.String(length=36), server_default='builtin-linux', nullable=True))
    with op.batch_alter_table('case_results') as batch_op:
        batch_op.add_column(sa.Column('runner_environment_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('runner_environment_name', sa.String(length=100), nullable=True))
    with op.batch_alter_table('execution_schedules') as batch_op:
        batch_op.add_column(sa.Column('linux_environment_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('windows_environment_id', sa.String(length=36), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('execution_schedules') as batch_op:
        batch_op.drop_column('windows_environment_id')
        batch_op.drop_column('linux_environment_id')
    with op.batch_alter_table('case_results') as batch_op:
        batch_op.drop_column('runner_environment_name')
        batch_op.drop_column('runner_environment_id')
    with op.batch_alter_table('test_cases') as batch_op:
        batch_op.drop_column('runner_environment_id')
    op.drop_table('runner_environments')
