"""013 expand status_prova_enum com 7 valores v4.0

Revision ID: 013
Revises: 012
Create Date: 2026-05-13

Wave 3 v4.0 — Componente 11 (atualizacao v4.0) — Maquina de Estados Expandida.

Mudancas:
  ALTER TYPE status_prova_enum ADD VALUE para os 7 novos rotulos da v4.0
  (ordem alfabetica para previsibilidade no `enumsortorder`):

    - COM_MOTORISTA_ENTREGA_FINAL
    - COM_MOTORISTA_IDA_LAMINACAO
    - COM_MOTORISTA_VOLTA_LAMINACAO
    - DE_VOLTA_3STUDIO_POS_LAMINACAO
    - ENCAMINHADA_PARA_LAMINACAO
    - ENCAMINHADA_PARA_O_VENDEDOR
    - LAMINACAO_CONCLUIDA

Os 10 valores existentes (v3.0) PERMANECEM intocados:
  CRIADA, RETIRADA_PELO_VENDEDOR, APROVADA_PELO_VENDEDOR, DE_VOLTA_3STUDIO,
  COM_MOTORISTA, ENVIADA_PARA_CLICHERIA, ENCAMINHADA_A_CLICHERIA,
  RECEBIDA_PELA_CLICHERIA, REPROVADA_PELO_VENDEDOR, CANCELADA.

Total final: 10 + 7 = 17 valores.

Coexistencia (Decisao M-2b(a) do Gate 1 do C11):
  - Provas legacy v3.0 (rota IS NULL ou rota IN {PADRAO, DIRETA}) continuam
    usando exclusivamente os 10 valores v3.0. O roteador da maquina em
    `backend/app/state_machine/__init__.py` dispatcha para a maquina v3.0.
  - Provas v4.0 (rota IN {MATRIZ, LAM_MATRIZ, FILIAL, LAM_FILIAL}) usam
    os valores v4.0 nas transicoes da nova maquina. `COM_MOTORISTA` v3.0
    NAO eh reutilizado nas rotas v4.0 — o equivalente operacional eh
    `COM_MOTORISTA_ENTREGA_FINAL` (estado distinto no enum).
  - `ENVIADA_PARA_CLICHERIA` e `ENCAMINHADA_A_CLICHERIA` permanecem
    legacy-only — as 4 rotas v4.0 transitam de `Com Motorista (entrega
    final)` ou de `Aprovada pelo Vendedor` (Filial/Lam.Filial) direto
    para `Recebida pela Clicheria`.

NAO inclui:
  - Renomeacao de COM_MOTORISTA (Postgres nao suporta renomeacao de enum
    value em transacao — exigiria DROP + CREATE table inteira).
  - DROP VALUE de qualquer valor (Postgres nao suporta DROP VALUE em
    transacao). Os 7 valores adicionados permanecem para sempre.

IDEMPOTENTE: cada ADD VALUE usa IF NOT EXISTS — re-rodar a migration nao
quebra. Pos-execucao, `SELECT enumlabel FROM pg_enum WHERE typname=
'status_prova_enum'` deve retornar 17 rows.

Reversivel: downgrade documenta a limitacao do Postgres e nao executa
mudanca destrutiva. Os 7 valores adicionados permanecem mesmo apos
`alembic downgrade -1`.

DIVERGENCIA REPO vs PRODUCAO:
  Esta migration eh ATOMIC (uma unica transacao). Diferente da migration
  012, NAO ha UPDATE/SELECT que USE os valores recem-adicionados na
  mesma transacao — apenas DDL pura (ALTER TYPE ADD VALUE). Logo, eh
  seguro rodar tudo numa unica transacao.

  Em producao, sera aplicada via MCP `apply_migration` com nome
  `013_expand_status_prova_enum_v4` (uma unica chamada). O
  `alembic_version='013'` sera setado manualmente apos a aplicacao para
  preservar consistencia com o historico Alembic local.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Ordem alfabetica garante previsibilidade no `enumsortorder` do Postgres,
# que aloca posicoes sequenciais a partir do final do enum existente. Util
# para queries de inventario e testes de drift.
_NOVOS_VALORES_V4 = (
    "COM_MOTORISTA_ENTREGA_FINAL",
    "COM_MOTORISTA_IDA_LAMINACAO",
    "COM_MOTORISTA_VOLTA_LAMINACAO",
    "DE_VOLTA_3STUDIO_POS_LAMINACAO",
    "ENCAMINHADA_PARA_LAMINACAO",
    "ENCAMINHADA_PARA_O_VENDEDOR",
    "LAMINACAO_CONCLUIDA",
)


def upgrade() -> None:
    for valor in _NOVOS_VALORES_V4:
        op.execute(
            f"ALTER TYPE status_prova_enum ADD VALUE IF NOT EXISTS '{valor}'"
        )


def downgrade() -> None:
    # Postgres 17 nao suporta DROP VALUE em ALTER TYPE em transacao. Remover
    # um valor de enum exigiria:
    #   1. Verificar que nenhuma linha de nenhuma tabela usa o valor.
    #   2. CREATE TYPE <novo_enum_sem_o_valor>.
    #   3. ALTER TABLE de cada coluna que referencia o enum para usar o
    #      novo type (com cast).
    #   4. DROP TYPE antigo + ALTER TYPE novo RENAME.
    # Isso eh destrutivo, nao-reversivel e fora do escopo desta migration.
    #
    # Estrategia operacional para reverter: nao reverter. Os 7 valores
    # adicionados sao no-op para provas v3.0 e ficam disponiveis para
    # provas v4.0. Se uma futura wave decidir "deprecar" um valor,
    # implementar isso via state_machine (rules.py) sem tocar no enum
    # do banco.
    pass
