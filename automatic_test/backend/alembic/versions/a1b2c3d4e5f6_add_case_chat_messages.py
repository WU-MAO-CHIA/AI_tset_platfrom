"""add_case_chat_messages

Revision ID: a1b2c3d4e5f6
Revises: ceb55f87f651
Create Date: 2026-06-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'ceb55f87f651'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'case_chat_messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('case_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['case_id'], ['test_cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("role IN ('user', 'assistant')", name='ck_chat_message_role'),
    )
    op.create_index('ix_case_chat_messages_case_id', 'case_chat_messages', ['case_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_case_chat_messages_case_id', table_name='case_chat_messages')
    op.drop_table('case_chat_messages')
