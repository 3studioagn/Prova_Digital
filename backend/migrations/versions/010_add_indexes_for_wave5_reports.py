"""010 add indexes for wave 5 reports

Revision ID: 010
Revises: 009
Create Date: 2026-04-15

Dois indices novos para suportar as agregacoes da Wave 5 (Componente 16).

  1. `idx_movimentacoes_status_novo_created_at (status_novo, created_at DESC)`
     - Usado em: tempo medio de aprovacao (WAVE5_ANALYSIS Secao 4.1),
       taxa de reprovacao (Secao 4.4).
     - Permite Index Scan em janela temporal filtrada por tipo de transicao.
       Sem ele, queries como "todas as APROVADA_PELO_VENDEDOR nos ultimos
       30 dias" viram seq scan em `movimentacoes`, inaceitavel em 100k+
       linhas.

  2. `idx_provas_vendedor_status (vendedor_id, status)`
     - Usado em: provas por vendedor com breakdown por status (Secao 4.2).
     - Permite Index Scan por vendedor com filtro de status embutido.
       Alternativa seria seq scan + COUNT FILTER, aceitavel ate ~50k provas.
       Criando ja para nao precisar refactor quando o volume crescer.

Tamanho estimado em 100k movimentacoes + 100k provas: ~20 MB combinados.
Custo de INSERT: < 1 ms adicional por `movimentacoes` (b-tree b+tree update).

IDEMPOTENTE: usa `CREATE INDEX IF NOT EXISTS` / `DROP INDEX IF EXISTS`.

Reversivel: `downgrade()` dropa os dois indices na ordem inversa da criacao.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_movimentacoes_status_novo_created_at
        ON public.movimentacoes (status_novo, created_at DESC);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_provas_vendedor_status
        ON public.provas_digitais (vendedor_id, status);
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS public.idx_provas_vendedor_status;
    """)
    op.execute("""
        DROP INDEX IF EXISTS public.idx_movimentacoes_status_novo_created_at;
    """)
