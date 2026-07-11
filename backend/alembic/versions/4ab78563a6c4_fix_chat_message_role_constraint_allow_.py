"""fix_chat_message_role_constraint_allow_system

Revision ID: 4ab78563a6c4
Revises: 6e42bf6077d7
Create Date: 2026-07-11 16:19:29.199932

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4ab78563a6c4'
down_revision: Union[str, Sequence[str], None] = '6e42bf6077d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('case_chat_messages', schema=None) as batch_op:
        batch_op.drop_constraint('ck_chat_message_role', type_='check')
        batch_op.create_check_constraint(
            'ck_chat_message_role', "role IN ('user', 'assistant', 'system')"
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('case_chat_messages', schema=None) as batch_op:
        batch_op.drop_constraint('ck_chat_message_role', type_='check')
        batch_op.create_check_constraint(
            'ck_chat_message_role', "role IN ('user', 'assistant')"
        )
