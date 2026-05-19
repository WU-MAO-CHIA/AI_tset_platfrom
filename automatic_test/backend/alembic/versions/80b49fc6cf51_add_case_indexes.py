"""add_case_indexes

Revision ID: 80b49fc6cf51
Revises: 50fdd0a702a9
Create Date: 2026-05-19 22:21:08.949538

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '80b49fc6cf51'
down_revision: Union[str, Sequence[str], None] = '50fdd0a702a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("test_cases") as batch_op:
        batch_op.create_index("ix_test_cases_case_number_active", ["case_number"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("test_cases") as batch_op:
        batch_op.drop_index("ix_test_cases_case_number_active")
