"""menambah kolom images dan deskripsi

Revision ID: 599309e384ce
Revises: 
Create Date: 2026-02-08 10:13:33.168155

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '599309e384ce'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('jeans', sa.Column('images_minio', sa.dialects.postgresql.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('jeans', 'images_minio')
