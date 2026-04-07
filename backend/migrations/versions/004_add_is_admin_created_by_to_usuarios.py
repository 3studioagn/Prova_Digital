"""Add is_admin and created_by columns to usuarios (Wave 1 - RBAC).

Revision ID: 004
Revises: 003
Create Date: 2026-04-07

Wave 1 requires RBAC based on is_admin flag and tracking who created each user.
- is_admin: controls admin access (true for 3Studio administrators)
- created_by: tracks which admin created the user (NULL for seed/initial users)
"""
from typing import Sequence, Union

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    ALTER TABLE usuarios
        ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT false;

    ALTER TABLE usuarios
        ADD COLUMN created_by UUID REFERENCES usuarios(id);
    """)


def downgrade() -> None:
    op.execute("""
    ALTER TABLE usuarios DROP COLUMN IF EXISTS created_by;
    ALTER TABLE usuarios DROP COLUMN IF EXISTS is_admin;
    """)
