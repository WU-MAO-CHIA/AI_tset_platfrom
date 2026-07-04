"""add_robot_scripts_table

Revision ID: d1e2f3a4b5c6
Revises: c8e876fb44a5
Create Date: 2026-06-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'c8e876fb44a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'robot_scripts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('test_case_id', sa.String(36), sa.ForeignKey('test_cases.id'), nullable=False),
        sa.Column('rf_code', sa.Text(), nullable=False),
        sa.Column('saved_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('test_case_id', name='uq_robot_script_test_case'),
    )
    op.create_index('ix_robot_scripts_test_case_id', 'robot_scripts', ['test_case_id'])


def downgrade() -> None:
    op.drop_index('ix_robot_scripts_test_case_id', table_name='robot_scripts')
    op.drop_table('robot_scripts')
