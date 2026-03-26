"""baseline

Revision ID: b6e9096dd9c5
Revises: 
Create Date: 2026-03-27 00:39:06.357790

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6e9096dd9c5'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('audit_logs', sa.Column('new_field', sa.String(), nullable=True))

def downgrade():
    op.drop_column('audit_logs', 'new_field')