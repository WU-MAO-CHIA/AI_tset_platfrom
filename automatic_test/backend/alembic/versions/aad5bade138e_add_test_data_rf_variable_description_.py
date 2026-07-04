"""add_test_data_rf_variable_description_checklist_actual_values

Revision ID: aad5bade138e
Revises: f6030690f5d2
Create Date: 2026-07-04 11:32:55.210184

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aad5bade138e'
down_revision: Union[str, Sequence[str], None] = 'f6030690f5d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Phase 25: ADD COLUMN — backward compatible, nullable columns only."""
    with op.batch_alter_table("test_data") as batch_op:
        batch_op.add_column(sa.Column("rf_variable", sa.String(200), nullable=True))
        batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))

    with op.batch_alter_table("checklist_items") as batch_op:
        batch_op.add_column(sa.Column("actual_values", sa.Text(), nullable=True))


def downgrade() -> None:
    """Phase 25 rollback: DROP the three added columns."""
    with op.batch_alter_table("checklist_items") as batch_op:
        batch_op.drop_column("actual_values")

    with op.batch_alter_table("test_data") as batch_op:
        batch_op.drop_column("description")
        batch_op.drop_column("rf_variable")
