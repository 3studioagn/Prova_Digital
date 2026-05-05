"""Testes de drift do enum `rota_enum` entre Python, TypeScript e PostgreSQL.

AUD-W2V4-T02 — Wave 2 v4.0 Audit Fixes (2026-05-05).

O enum `rota_enum` vive em 3 camadas independentes:

  1. Python `RotaEnum` em `backend/app/db/models.py` (ORM SQLAlchemy).
  2. Pydantic `RotaCriacaoEnum` em
     `backend/app/domain/schemas/prova.py` (subset de criacao — apenas
     os 4 v4.0; legacy bloqueado).
  3. TypeScript `Rota` + `RotaCriacao` em
     `frontend/src/lib/types/prova.ts`.
  4. PostgreSQL `pg_enum` em producao (Supabase).

Estes testes confrontam as 4 camadas aos pares e detectam drift
automaticamente. Se algum PR futuro adicionar valor numa so camada,
a CI quebra antes do merge.

O teste #1 (Python <-> PostgreSQL) precisa de banco real — skipif
quando `INTEGRATION_DATABASE_URL` ausente, mesmo padrao do
test_imutabilidade_rota.py.

Os testes #2 (TS <-> Python), #3 (Pydantic subset) e #4 (Pydantic
literais) sao pure-Python — sempre rodam.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from app.db.models import RotaEnum
from app.domain.schemas.prova import RotaCriacaoEnum


# ─── Constantes ───────────────────────────────────────────────────────────

# Os 4 valores v4.0 (RotaCriacaoEnum) — admin escolhe na criacao.
ROTAS_V4 = frozenset({"MATRIZ", "LAM_MATRIZ", "FILIAL", "LAM_FILIAL"})

# Os 2 valores legacy v3.0 — Wave 7 fara backfill final.
ROTAS_LEGACY = frozenset({"PADRAO", "DIRETA"})

# Conjunto completo do enum Python (ORM + banco).
ROTAS_TODAS = ROTAS_V4 | ROTAS_LEGACY

# Caminho do arquivo TypeScript com os literais.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_TS_TYPES_PATH = _REPO_ROOT / "frontend" / "src" / "lib" / "types" / "prova.ts"


# ─── Teste #1: Python RotaEnum <-> PostgreSQL pg_enum ─────────────────────


_INTEGRATION_DB_URL = os.environ.get("INTEGRATION_DATABASE_URL")


@pytest.mark.asyncio
@pytest.mark.skipif(
    _INTEGRATION_DB_URL is None,
    reason=(
        "Set INTEGRATION_DATABASE_URL=postgresql+asyncpg://... para "
        "rodar este teste contra o pg_enum real do Postgres."
    ),
)
async def test_rota_enum_drift_python_postgres():
    """Confronta `set(RotaEnum)` Python com `SELECT enumlabel FROM pg_enum`
    PostgreSQL. Falha se algum lado tiver valor que o outro nao tem.
    """
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(_INTEGRATION_DB_URL, echo=False)  # type: ignore[arg-type]
    try:
        async with engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        "SELECT enumlabel FROM pg_enum "
                        "WHERE enumtypid = 'rota_enum'::regtype "
                        "ORDER BY enumsortorder"
                    )
                )
            ).all()
        postgres_set = {row[0] for row in rows}
    finally:
        await engine.dispose()

    python_set = {r.value for r in RotaEnum}
    assert postgres_set == python_set, (
        f"DRIFT detectado: Python {python_set} != PostgreSQL {postgres_set}\n"
        f"Apenas em Python: {python_set - postgres_set}\n"
        f"Apenas em PostgreSQL: {postgres_set - python_set}"
    )


# ─── Teste #2: TypeScript <-> Python RotaEnum ─────────────────────────────


def _extract_typescript_literals(source: str, type_name: str) -> set[str]:
    """Extrai os literais de uma `export type X = "A" | "B" | ...;` simples.

    Suporta literais separados por `|` em multiplas linhas. Remove
    comentarios `// ...`.
    """
    # Captura tudo entre `export type X =` e `;` (multiline).
    pattern = re.compile(
        rf"export type {re.escape(type_name)}\s*=\s*([^;]+);",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(source)
    if not match:
        raise AssertionError(
            f"Tipo `{type_name}` nao encontrado em {_TS_TYPES_PATH}"
        )
    body = match.group(1)
    # Remove comentarios de linha.
    body = re.sub(r"//[^\n]*", "", body)
    # Encontra todos os literais de string.
    literais = set(re.findall(r'"([^"]+)"', body))
    return literais


def test_rota_enum_drift_typescript_python():
    """Confronta `Rota` TS (todos os 6 valores) com `RotaEnum` Python.
    """
    assert _TS_TYPES_PATH.exists(), (
        f"Arquivo TS nao encontrado em {_TS_TYPES_PATH}. "
        "Drift de path entre repo e teste — atualizar o teste."
    )
    source = _TS_TYPES_PATH.read_text(encoding="utf-8")

    ts_rota_set = _extract_typescript_literals(source, "Rota")
    python_set = {r.value for r in RotaEnum}

    assert ts_rota_set == python_set, (
        f"DRIFT detectado: TS Rota {ts_rota_set} != Python RotaEnum {python_set}\n"
        f"Apenas em TS: {ts_rota_set - python_set}\n"
        f"Apenas em Python: {python_set - ts_rota_set}"
    )


def test_rota_criacao_drift_typescript_python():
    """Confronta `RotaCriacao` TS (4 valores v4.0) com `RotaCriacaoEnum`
    Pydantic. Garante que o sub-enum de criacao bate.
    """
    source = _TS_TYPES_PATH.read_text(encoding="utf-8")
    ts_set = _extract_typescript_literals(source, "RotaCriacao")
    python_set = {r.value for r in RotaCriacaoEnum}

    assert ts_set == python_set, (
        f"DRIFT detectado: TS RotaCriacao {ts_set} != "
        f"Python RotaCriacaoEnum {python_set}\n"
        f"Apenas em TS: {ts_set - python_set}\n"
        f"Apenas em Python: {python_set - ts_set}"
    )


# ─── Teste #3: RotaCriacaoEnum e subset de RotaEnum ───────────────────────


def test_rotacriacao_e_subset_de_rotaenum():
    """`RotaCriacaoEnum` deve conter apenas valores que existem em
    `RotaEnum` (subset estrito; legacy bloqueado na criacao)."""
    criacao = {r.value for r in RotaCriacaoEnum}
    todas = {r.value for r in RotaEnum}
    assert criacao.issubset(todas), (
        f"RotaCriacaoEnum tem valores que nao existem em RotaEnum: "
        f"{criacao - todas}"
    )
    # Wave 2 v4.0: criacao tem exatamente os 4 v4.0.
    assert criacao == ROTAS_V4, (
        f"RotaCriacaoEnum deveria ter exatamente {ROTAS_V4}, "
        f"mas tem {criacao}"
    )
    # E NAO deve aceitar legacy.
    assert criacao.isdisjoint(ROTAS_LEGACY), (
        f"RotaCriacaoEnum aceita legacy {criacao & ROTAS_LEGACY} — "
        f"isso quebra o bloqueio do Backlog v4.0 §5 Componente 06."
    )


# ─── Teste #4: Sanity check das constantes do teste ───────────────────────


def test_constantes_de_drift_sao_consistentes():
    """Sanity check que as constantes locais batem com o esperado pela
    Wave 2 v4.0 (audit-report.md secao 'Cobertura dos 4 valores')."""
    # 4 v4.0 + 2 legacy = 6 totais.
    assert len(ROTAS_V4) == 4
    assert len(ROTAS_LEGACY) == 2
    assert len(ROTAS_TODAS) == 6
    # E batem com Python.
    python_set = {r.value for r in RotaEnum}
    assert python_set == ROTAS_TODAS
