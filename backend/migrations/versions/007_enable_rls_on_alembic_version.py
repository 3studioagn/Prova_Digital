"""Enable RLS on public.alembic_version (Wave 1 audit follow-up).

Revision ID: 007
Revises: 006
Create Date: 2026-04-08

The `alembic stamp 004` executed during the Wave 1 audit (Sessao 5) created
`public.alembic_version` automatically. Alembic does not enable RLS on its own
tracking table — but our project exposes the entire `public` schema via
PostgREST, so any client with the anon key could read or write the version
number. The Supabase security advisor flagged this as ERROR
(`rls_disabled_in_public`) right after the stamp.

Fix: enable RLS without any policies. Postgres denies all access by default
when RLS is on and no policies match. The `postgres` role used by Alembic
itself bypasses RLS entirely, so future `alembic upgrade head` keeps working.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY;
    """)


def downgrade() -> None:
    op.execute("""
    ALTER TABLE public.alembic_version DISABLE ROW LEVEL SECURITY;
    """)
