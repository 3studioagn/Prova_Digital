"""Set immutable search_path on trigger helper functions (Wave 1 audit).

Revision ID: 006
Revises: 005
Create Date: 2026-04-08

Supabase security advisor flagged fn_bloquear_alteracao() and
fn_atualizar_updated_at() as `function_search_path_mutable` (WARN level).
Without an explicit search_path, both functions inherit the caller's session
search_path — which opens the door to search_path hijacking attacks (a
malicious schema injecting overrides for now(), coalesce(), etc).

Fix: pin search_path to empty string. Both functions are PL/pgSQL with no
unqualified identifiers that need resolution, so '' is safe. Schema-qualified
references (e.g. NEW.updated_at = NOW()) keep working because NOW() is a
SQL standard built-in available without any search_path.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    ALTER FUNCTION public.fn_bloquear_alteracao() SET search_path = '';
    ALTER FUNCTION public.fn_atualizar_updated_at() SET search_path = '';
    """)


def downgrade() -> None:
    op.execute("""
    ALTER FUNCTION public.fn_bloquear_alteracao() RESET search_path;
    ALTER FUNCTION public.fn_atualizar_updated_at() RESET search_path;
    """)
