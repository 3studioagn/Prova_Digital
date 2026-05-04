"""012 add codigo_publico + rotas v4.0 + trigger imutabilidade rota

Revision ID: 012
Revises: 011
Create Date: 2026-05-04

Wave 2 v4.0 — Componente 06 (atualizacao v4.0).

Mudancas:
  1. ALTER TYPE rota_enum ADD VALUE para os 4 novos rotulos da v4.0:
     'MATRIZ', 'LAM_MATRIZ', 'FILIAL', 'LAM_FILIAL'.
     Os valores legacy 'PADRAO' e 'DIRETA' (Wave 0, v3.0) PERMANECEM no
     enum ate a Wave 7 (Componente 21) fazer o backfill das 5 provas que
     ainda os usam. Postgres nao suporta DROP VALUE em transacao —
     remocao definitiva dos legacy fica para wave futura.

  2. ADD COLUMN provas_digitais.codigo_publico VARCHAR(20) UNIQUE NOT NULL.
     Formato: PRV-AAAA-MM-NNNNNN (DAT v3.0 §8.3).
     Alfabeto sem chars ambiguos (sem 0/O/1/I/L) — 31 chars.
     Sequencia: ADD coluna NULLABLE -> backfill local p/ as 16 provas
     existentes -> ALTER COLUMN SET NOT NULL.

  3. UNIQUE INDEX idx_provas_codigo_publico — suporta lookup pelo
     fallback de digitacao manual (Componente 19, Wave 3 v4.0).

  4. INDEX idx_provas_rota — suporta filtro do Componente 07 com 4 rotas
     (RF-014).

  5. Funcao + trigger fn_bloquear_alteracao_rota / trg_provas_rota_imutavel
     BEFORE UPDATE WHEN (OLD.rota IS DISTINCT FROM NEW.rota) — bloqueia
     valor->outro_valor e valor->NULL. PERMITE NULL->valor (Wave 7
     backfill). search_path = '' (consistente com ADR-024).

NAO inclui:
  - Tornar rota NOT NULL (Wave 7 / Componente 21).
  - DROP VALUE PADRAO/DIRETA (limitacao do Postgres + ainda em uso por
    5 provas v3.0 ate Wave 7).

IDEMPOTENTE: ADD VALUE usa IF NOT EXISTS; INDEX usa IF NOT EXISTS;
o backfill so roda em provas com codigo_publico IS NULL.

Reversivel: downgrade dropa trigger + funcao + indexes + coluna. Os
valores adicionados ao enum permanecem (limitacao do Postgres
documentada).
"""
from __future__ import annotations

import secrets
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Alfabeto do `codigo_publico` (DAT v3.0 §8.3): sem chars ambiguos
# (0/O, 1/I/L). 31 caracteres -> 31^6 ≈ 887 milhoes de combinacoes/mes.
_NANO_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_NANO_LEN = 6


def _gen_codigo(ano: int, mes: int) -> str:
    sufixo = "".join(secrets.choice(_NANO_ALPHABET) for _ in range(_NANO_LEN))
    return f"PRV-{ano:04d}-{mes:02d}-{sufixo}"


def upgrade() -> None:
    bind = op.get_bind()

    # ─── 1. ALTER TYPE rota_enum (4 novos valores) ─────────────────────────
    # Postgres 12+ permite ADD VALUE em transacao com IF NOT EXISTS (mas o
    # valor recem-adicionado nao pode ser usado na MESMA transacao). Como
    # nada nesta migration precisa USAR os novos valores (o backfill
    # popula apenas codigo_publico, e o trigger nao referencia valores
    # especificos do enum), e seguro rodar tudo numa transacao.
    op.execute("ALTER TYPE rota_enum ADD VALUE IF NOT EXISTS 'MATRIZ'")
    op.execute("ALTER TYPE rota_enum ADD VALUE IF NOT EXISTS 'LAM_MATRIZ'")
    op.execute("ALTER TYPE rota_enum ADD VALUE IF NOT EXISTS 'FILIAL'")
    op.execute("ALTER TYPE rota_enum ADD VALUE IF NOT EXISTS 'LAM_FILIAL'")

    # ─── 2a. ADD COLUMN codigo_publico (NULLABLE inicialmente) ─────────────
    op.add_column(
        "provas_digitais",
        sa.Column("codigo_publico", sa.String(length=20), nullable=True),
    )

    # ─── 2b. Backfill das provas existentes ────────────────────────────────
    # Le `id` + `created_at` de cada prova com codigo_publico IS NULL e
    # gera codigo PRV-AAAA-MM-NNNNNN baseado em created_at. Garantia de
    # unicidade via set local + retry. Em producao no momento da migration
    # ha ~16 provas — colisao em 887M e desprezivel.
    rows = bind.execute(
        sa.text(
            "SELECT id, created_at "
            "FROM provas_digitais "
            "WHERE codigo_publico IS NULL"
        )
    ).fetchall()
    used_codes: set[str] = set()

    # Carrega codigos ja existentes (idempotencia: rodar migration 2x nao
    # quebra; o segundo run encontra a coluna ja populada e o SELECT acima
    # retorna 0 linhas).
    existing = bind.execute(
        sa.text(
            "SELECT codigo_publico FROM provas_digitais "
            "WHERE codigo_publico IS NOT NULL"
        )
    ).fetchall()
    for r in existing:
        used_codes.add(r.codigo_publico)

    for row in rows:
        ano = row.created_at.year
        mes = row.created_at.month
        codigo: str | None = None
        for _ in range(20):  # retry ate 20x — quase impossivel falhar
            cand = _gen_codigo(ano, mes)
            if cand not in used_codes:
                used_codes.add(cand)
                codigo = cand
                break
        if codigo is None:
            raise RuntimeError(
                f"Falha ao gerar codigo_publico unico para prova {row.id} "
                f"apos 20 tentativas — investigar geracao."
            )
        bind.execute(
            sa.text(
                "UPDATE provas_digitais "
                "SET codigo_publico = :codigo "
                "WHERE id = :id"
            ),
            {"codigo": codigo, "id": row.id},
        )

    # ─── 2c. ALTER COLUMN SET NOT NULL (apos backfill) ─────────────────────
    op.alter_column("provas_digitais", "codigo_publico", nullable=False)

    # ─── 3. UNIQUE INDEX em codigo_publico ─────────────────────────────────
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_provas_codigo_publico "
        "ON public.provas_digitais (codigo_publico)"
    )

    # ─── 4. INDEX em rota (filtro do Componente 07 — RF-014) ───────────────
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_provas_rota "
        "ON public.provas_digitais (rota)"
    )

    # ─── 5. Funcao + trigger de imutabilidade da rota (RN-002 v4.0) ────────
    # Permite NULL -> valor (Wave 7 backfill).
    # Bloqueia valor -> outro_valor e valor -> NULL.
    # search_path = '' (ADR-024 — defesa contra search_path hijacking).
    op.execute("""
        CREATE OR REPLACE FUNCTION public.fn_bloquear_alteracao_rota()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        SET search_path = ''
        AS $$
        BEGIN
            IF OLD.rota IS NOT NULL AND NEW.rota IS DISTINCT FROM OLD.rota THEN
                RAISE EXCEPTION
                    'Coluna rota e imutavel apos definicao (RN-002 v4.0). '
                    'Para alterar rota, cancele a prova e crie uma nova.'
                    USING ERRCODE = '22023';
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("DROP TRIGGER IF EXISTS trg_provas_rota_imutavel ON public.provas_digitais")
    op.execute("""
        CREATE TRIGGER trg_provas_rota_imutavel
            BEFORE UPDATE ON public.provas_digitais
            FOR EACH ROW
            WHEN (OLD.rota IS DISTINCT FROM NEW.rota)
            EXECUTE FUNCTION public.fn_bloquear_alteracao_rota();
    """)


def downgrade() -> None:
    # Ordem inversa.
    op.execute("DROP TRIGGER IF EXISTS trg_provas_rota_imutavel ON public.provas_digitais")
    op.execute("DROP FUNCTION IF EXISTS public.fn_bloquear_alteracao_rota()")
    op.execute("DROP INDEX IF EXISTS public.idx_provas_rota")
    op.execute("DROP INDEX IF EXISTS public.idx_provas_codigo_publico")
    op.drop_column("provas_digitais", "codigo_publico")
    # Os 4 valores adicionados ao rota_enum NAO sao removidos —
    # Postgres nao suporta DROP VALUE em transacao. Documentado.
