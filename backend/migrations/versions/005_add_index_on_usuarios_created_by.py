"""Add index on usuarios.created_by FK (Wave 1 audit).

Revision ID: 005
Revises: 004
Create Date: 2026-04-08

Supabase performance advisor flagged the FK usuarios.created_by → usuarios.id
as unindexed (level: INFO). Without an index, deactivating an admin requires a
sequential scan of usuarios to find anyone they created — fine on 3 rows, but
will degrade as the user table grows. Cheap to fix and idempotent.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_usuarios_created_by
        ON usuarios(created_by);
    """)


def downgrade() -> None:
    op.execute("""
    DROP INDEX IF EXISTS idx_usuarios_created_by;
    """)
