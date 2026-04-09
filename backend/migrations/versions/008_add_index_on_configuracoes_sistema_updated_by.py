"""Add index on configuracoes_sistema.updated_by FK (Wave 1 audit follow-up).

Revision ID: 008
Revises: 007
Create Date: 2026-04-08

Same class of issue the Wave 1 audit found in usuarios.created_by (migration
005), but on configuracoes_sistema. The FK `configuracoes_sistema.updated_by`
references usuarios.id and was created without a covering index in migration
001. The Supabase performance advisor flagged it as INFO right after migration
005 was applied (probably the audit only surfaces the first one until it is
fixed). Cheap, idempotent fix using the same pattern as 005.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_configuracoes_sistema_updated_by
        ON configuracoes_sistema(updated_by);
    """)


def downgrade() -> None:
    op.execute("""
    DROP INDEX IF EXISTS idx_configuracoes_sistema_updated_by;
    """)
