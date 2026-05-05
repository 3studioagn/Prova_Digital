"""Testes de upgrade/downgrade/idempotencia da migration 012.

AUD-W2V4-T03 — Wave 2 v4.0 Audit Fixes (2026-05-05).

Migration 012 (`012_add_codigo_publico_and_rotas_v4_to_provas.py`)
introduziu na Wave 2 v4.0:
  - 4 novos valores em `rota_enum` (MATRIZ, LAM_MATRIZ, FILIAL,
    LAM_FILIAL).
  - Coluna `codigo_publico VARCHAR(20) UNIQUE NOT NULL` com backfill
    local das provas existentes.
  - Indexes `idx_provas_codigo_publico` UNIQUE + `idx_provas_rota`.
  - Trigger `trg_provas_rota_imutavel` + funcao
    `fn_bloquear_alteracao_rota`.

Em PRODUCAO foi aplicada via MCP em 3 chunks (`012a`, `012b`, `012c`)
para contornar limitacao do Postgres `ALTER TYPE ADD VALUE` em
transacao. Mas a migration Alembic do REPO e atomic. Esta suite valida
que o fluxo Alembic atomic do repo:
  1. Aplica sem erro em ambiente fresh (upgrade head).
  2. Reverte coluna + trigger + indexes em downgrade -1 (sem reverter
     ENUM ADD VALUE — limitacao Postgres documentada na docstring da
     migration).
  3. E IDEMPOTENTE — aplicar 2x consecutivas nao quebra (backfill com
     `WHERE codigo_publico IS NULL` retorna 0 linhas no segundo run;
     trigger usa CREATE OR REPLACE; ALTER TYPE ADD VALUE usa IF NOT
     EXISTS).

Como o teste exige criar/destruir banco PostgreSQL, usa
INTEGRATION_DATABASE_URL com schema dedicado (cria, dropa) — skipif
quando ausente, mesmo padrao de test_imutabilidade_rota.py.

Wave 7 (Componente 21) DEVE rodar esta suite contra branch fresh
do Supabase antes de criar nova migration 013+; sem ela nao ha
garantia de coexistencia.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


# ─── Skip global ──────────────────────────────────────────────────────────

_INTEGRATION_DB_URL = os.environ.get("INTEGRATION_DATABASE_URL")

# Para o teste de migration, precisamos da URL SINCRONA (psycopg2) — Alembic
# usa SQLAlchemy sync. Convertemos asyncpg -> psycopg2 se necessario.
def _to_sync_url(url: str | None) -> str | None:
    if url is None:
        return None
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )


_SYNC_DB_URL = _to_sync_url(_INTEGRATION_DB_URL)


pytestmark = pytest.mark.skipif(
    _INTEGRATION_DB_URL is None,
    reason=(
        "Set INTEGRATION_DATABASE_URL=postgresql+asyncpg://... para "
        "rodar testes de migration. Recomenda-se branch isolada do "
        "Supabase ou docker postgres dedicado — esta suite cria/dropa "
        "schema temporario."
    ),
)


# ─── Helpers ──────────────────────────────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ALEMBIC_INI = _REPO_ROOT / "backend" / "alembic.ini"


def _alembic_config(db_url: str) -> Config:
    """Constroi Config do Alembic apontando para `db_url`."""
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", db_url)
    cfg.set_main_option(
        "script_location",
        str(_REPO_ROOT / "backend" / "migrations"),
    )
    return cfg


@pytest.fixture
def fresh_schema():
    """Cria schema temporario unique-per-test, retorna URL apontando
    para ele via `search_path`. Drop no fim.

    Postgres nao permite DROP TYPE em transacao se o tipo for usado;
    como toda migration cria tudo dentro do schema, droppar o schema
    inteiro com CASCADE limpa tudo.
    """
    if _SYNC_DB_URL is None:
        pytest.skip("INTEGRATION_DATABASE_URL ausente")
    schema_name = f"test_mig_{os.getpid()}_{os.urandom(4).hex()}"
    base_engine = create_engine(_SYNC_DB_URL, isolation_level="AUTOCOMMIT")
    with base_engine.connect() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema_name}"'))

    # URL com search_path injetado.
    sep = "&" if "?" in _SYNC_DB_URL else "?"
    schema_url = f"{_SYNC_DB_URL}{sep}options=-csearch_path={schema_name}"

    try:
        yield schema_url, schema_name
    finally:
        with base_engine.connect() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        base_engine.dispose()


# ─── Teste #1: alembic upgrade head em ambiente fresh ────────────────────


def test_migration_012_upgrade_aplica_em_ambiente_fresh(fresh_schema):
    """`alembic upgrade head` em schema vazio aplica todas as migrations
    incluindo 012 sem erro. Backfill e no-op (zero provas existentes).
    """
    schema_url, schema_name = fresh_schema
    cfg = _alembic_config(schema_url)
    command.upgrade(cfg, "head")

    # Confirma que coluna codigo_publico existe e e NOT NULL.
    engine = create_engine(schema_url)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                f"SELECT column_name, is_nullable FROM information_schema.columns "
                f"WHERE table_schema = :schema AND table_name = 'provas_digitais' "
                f"AND column_name = 'codigo_publico'"
            ),
            {"schema": schema_name},
        ).all()
        assert len(rows) == 1
        assert rows[0][1] == "NO"  # NOT NULL

        # Confirma que trigger existe.
        trigger_count = conn.execute(
            text(
                "SELECT COUNT(*) FROM pg_trigger "
                "WHERE tgname = 'trg_provas_rota_imutavel'"
            )
        ).scalar()
        assert trigger_count == 1

        # Confirma que indexes existem.
        idx_rows = conn.execute(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE schemaname = :schema "
                "AND indexname IN ('idx_provas_codigo_publico', 'idx_provas_rota')"
            ),
            {"schema": schema_name},
        ).all()
        assert len(idx_rows) == 2
    engine.dispose()


# ─── Teste #2: alembic downgrade -1 reverte estruturas novas ──────────────


def test_migration_012_downgrade_reverte_coluna_trigger_indexes(fresh_schema):
    """`alembic downgrade -1` apos `upgrade head` reverte coluna +
    trigger + indexes da migration 012. Os 4 valores ADD VALUE no enum
    NAO sao revertidos (limitacao Postgres documentada).
    """
    schema_url, schema_name = fresh_schema
    cfg = _alembic_config(schema_url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "-1")

    engine = create_engine(schema_url)
    with engine.connect() as conn:
        # Coluna codigo_publico nao existe mais.
        col_count = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = :schema AND table_name = 'provas_digitais' "
                "AND column_name = 'codigo_publico'"
            ),
            {"schema": schema_name},
        ).scalar()
        assert col_count == 0

        # Trigger nao existe mais.
        trigger_count = conn.execute(
            text(
                "SELECT COUNT(*) FROM pg_trigger "
                "WHERE tgname = 'trg_provas_rota_imutavel'"
            )
        ).scalar()
        assert trigger_count == 0

        # Indexes nao existem mais.
        idx_count = conn.execute(
            text(
                "SELECT COUNT(*) FROM pg_indexes "
                "WHERE schemaname = :schema "
                "AND indexname IN ('idx_provas_codigo_publico', 'idx_provas_rota')"
            ),
            {"schema": schema_name},
        ).scalar()
        assert idx_count == 0

        # ENUM continua com 6 valores (limitacao Postgres — documentado).
        enum_count = conn.execute(
            text(
                "SELECT COUNT(*) FROM pg_enum "
                "WHERE enumtypid = 'rota_enum'::regtype"
            )
        ).scalar()
        assert enum_count == 6
    engine.dispose()


# ─── Teste #3: idempotencia (aplicar 2x consecutivas) ─────────────────────


def test_migration_012_idempotente(fresh_schema):
    """Aplicar `alembic upgrade head` 2x consecutivas nao quebra nada.

    Migration 012 usa:
      - ALTER TYPE ADD VALUE IF NOT EXISTS (idempotente)
      - ADD COLUMN IF NOT EXISTS (idempotente)
      - Backfill com WHERE codigo_publico IS NULL (no-op no segundo run)
      - CREATE UNIQUE INDEX IF NOT EXISTS (idempotente)
      - CREATE OR REPLACE FUNCTION (idempotente)
      - DROP TRIGGER IF EXISTS + CREATE TRIGGER (idempotente)

    Mas Alembic em si nao re-aplica uma migration ja registrada em
    alembic_version. Para testar idempotencia REAL, descemos -1 e
    subimos head novamente.
    """
    schema_url, schema_name = fresh_schema
    cfg = _alembic_config(schema_url)

    # Primeira aplicacao.
    command.upgrade(cfg, "head")

    # Down-up para forcar re-aplicacao da 012.
    command.downgrade(cfg, "-1")
    command.upgrade(cfg, "head")

    # Estado final identico ao do teste #1.
    engine = create_engine(schema_url)
    with engine.connect() as conn:
        # Codigo publico volta a existir.
        col = conn.execute(
            text(
                "SELECT is_nullable FROM information_schema.columns "
                "WHERE table_schema = :schema AND table_name = 'provas_digitais' "
                "AND column_name = 'codigo_publico'"
            ),
            {"schema": schema_name},
        ).scalar_one_or_none()
        assert col == "NO"
        # Trigger volta a existir.
        trigger_count = conn.execute(
            text(
                "SELECT COUNT(*) FROM pg_trigger "
                "WHERE tgname = 'trg_provas_rota_imutavel'"
            )
        ).scalar()
        assert trigger_count == 1
    engine.dispose()
