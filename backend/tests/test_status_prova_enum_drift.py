"""Testes de drift do enum `status_prova_enum` entre Python, TypeScript e PostgreSQL.

Wave 3 v4.0 / Componente 11.

O enum `status_prova_enum` vive em 3 camadas independentes:

  1. Python `StatusProvaEnum` em `backend/app/db/models.py` (ORM SQLAlchemy).
  2. TypeScript `StatusProva` em
     `frontend/src/lib/types/prova.ts`.
  3. PostgreSQL `pg_enum` em producao (Supabase).

Estes testes confrontam as 3 camadas aos pares e detectam drift
automaticamente. Se algum PR futuro adicionar valor numa so camada, a
CI quebra antes do merge.

O teste #1 (Python <-> PostgreSQL) precisa de banco real — skipif
quando `INTEGRATION_DATABASE_URL` ausente, mesmo padrao do
test_rota_enum_drift.py.

Os testes #2 (TS <-> Python) e #3 (sanity check das constantes) sao
pure-Python — sempre rodam.

Pos-migration 013: 17 valores totais (10 v3.0 + 7 v4.0).
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from app.db.models import StatusProvaEnum


# ─── Constantes ───────────────────────────────────────────────────────────

# Os 10 valores v3.0 (Wave 0 + Wave 3 originais).
STATUS_V3 = frozenset({
    "CRIADA",
    "RETIRADA_PELO_VENDEDOR",
    "APROVADA_PELO_VENDEDOR",
    "DE_VOLTA_3STUDIO",
    "COM_MOTORISTA",
    "ENVIADA_PARA_CLICHERIA",
    "ENCAMINHADA_A_CLICHERIA",
    "RECEBIDA_PELA_CLICHERIA",
    "REPROVADA_PELO_VENDEDOR",
    "CANCELADA",
})

# Os 7 valores v4.0 (migration 013 — Componente 11).
STATUS_V4 = frozenset({
    "COM_MOTORISTA_IDA_LAMINACAO",
    "COM_MOTORISTA_VOLTA_LAMINACAO",
    "COM_MOTORISTA_ENTREGA_FINAL",
    "ENCAMINHADA_PARA_LAMINACAO",
    "LAMINACAO_CONCLUIDA",
    "DE_VOLTA_3STUDIO_POS_LAMINACAO",
    "ENCAMINHADA_PARA_O_VENDEDOR",
})

# Conjunto completo do enum.
STATUS_TODOS = STATUS_V3 | STATUS_V4

# Caminho do arquivo TypeScript com os literais.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_TS_TYPES_PATH = _REPO_ROOT / "frontend" / "src" / "lib" / "types" / "prova.ts"


# ─── Teste #1: Python StatusProvaEnum <-> PostgreSQL pg_enum ──────────────


_INTEGRATION_DB_URL = os.environ.get("INTEGRATION_DATABASE_URL")


@pytest.mark.asyncio
@pytest.mark.skipif(
    _INTEGRATION_DB_URL is None,
    reason=(
        "Set INTEGRATION_DATABASE_URL=postgresql+asyncpg://... para "
        "rodar este teste contra o pg_enum real do Postgres."
    ),
)
async def test_status_prova_enum_drift_python_postgres():
    """Confronta `set(StatusProvaEnum)` Python com `SELECT enumlabel
    FROM pg_enum` PostgreSQL. Falha se algum lado tiver valor que o
    outro nao tem.
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
                        "WHERE enumtypid = 'status_prova_enum'::regtype "
                        "ORDER BY enumsortorder"
                    )
                )
            ).all()
        postgres_set = {row[0] for row in rows}
    finally:
        await engine.dispose()

    python_set = {s.value for s in StatusProvaEnum}
    assert postgres_set == python_set, (
        f"DRIFT detectado: Python {python_set} != PostgreSQL {postgres_set}\n"
        f"Apenas em Python: {python_set - postgres_set}\n"
        f"Apenas em PostgreSQL: {postgres_set - python_set}"
    )


# ─── Teste #2: TypeScript <-> Python StatusProvaEnum ──────────────────────


def _extract_typescript_literals(source: str, type_name: str) -> set[str]:
    """Extrai os literais de uma `export type X = "A" | "B" | ...;`.

    Suporta literais separados por `|` em multiplas linhas com
    comentarios `// ...` inline. Reutilizado de test_rota_enum_drift.py.
    """
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


def test_status_prova_drift_typescript_python():
    """Confronta `StatusProva` TS (17 valores) com `StatusProvaEnum` Python.
    """
    assert _TS_TYPES_PATH.exists(), (
        f"Arquivo TS nao encontrado em {_TS_TYPES_PATH}. "
        "Drift de path entre repo e teste — atualizar o teste."
    )
    source = _TS_TYPES_PATH.read_text(encoding="utf-8")

    ts_set = _extract_typescript_literals(source, "StatusProva")
    python_set = {s.value for s in StatusProvaEnum}

    assert ts_set == python_set, (
        f"DRIFT detectado: TS StatusProva {ts_set} != "
        f"Python StatusProvaEnum {python_set}\n"
        f"Apenas em TS: {ts_set - python_set}\n"
        f"Apenas em Python: {python_set - ts_set}"
    )


# ─── Teste #3: Sanity check das constantes do teste ───────────────────────


def test_constantes_de_drift_sao_consistentes():
    """Sanity check que as constantes locais batem com o esperado pela
    Wave 3 v4.0 / C11 (migration 013).
    """
    # 10 v3.0 + 7 v4.0 = 17 totais.
    assert len(STATUS_V3) == 10
    assert len(STATUS_V4) == 7
    assert len(STATUS_TODOS) == 17
    # Sem sobreposicao.
    assert STATUS_V3.isdisjoint(STATUS_V4)
    # E batem com Python.
    python_set = {s.value for s in StatusProvaEnum}
    assert python_set == STATUS_TODOS, (
        f"DRIFT vs constantes locais: Python {python_set} != "
        f"esperado {STATUS_TODOS}"
    )


def test_status_v4_aparecem_nas_status_labels_typescript():
    """STATUS_LABELS no TS deve ter entrada para cada um dos 17 valores.

    O TS `Record<StatusProva, string>` impoe isso em tempo de compilacao,
    mas validamos via teste tambem para fail-fast em CI sem precisar
    de tsc --noEmit como pre-requisito.
    """
    source = _TS_TYPES_PATH.read_text(encoding="utf-8")
    # Procura "VALOR:" como chave de objeto em STATUS_LABELS / STATUS_LABELS_SHORT
    # Limita a regiao do arquivo a partir de "STATUS_LABELS" ate "ROTA_LABELS"
    inicio = source.find("STATUS_LABELS:")
    if inicio == -1:
        inicio = source.find("STATUS_LABELS =")
    fim = source.find("ROTA_LABELS", inicio) if inicio != -1 else -1
    assert inicio != -1 and fim != -1, "Falha ao localizar bloco STATUS_LABELS no TS"
    bloco = source[inicio:fim]

    for status in STATUS_V4:
        # cada valor deve aparecer como chave no objeto STATUS_LABELS
        assert re.search(rf"\b{re.escape(status)}:", bloco), (
            f"Valor v4.0 {status} nao encontrado em STATUS_LABELS / "
            f"STATUS_LABELS_SHORT do TS."
        )
