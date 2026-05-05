"""Testes integrados do trigger `trg_provas_rota_imutavel` (RN-002 v4.0).

AUD-W2V4-T01 — Wave 2 v4.0 Audit Fixes (2026-05-05).

Estes testes rodam UPDATE/INSERT real contra um banco PostgreSQL com
o trigger ativo (`fn_bloquear_alteracao_rota`). Cobrem 5 cenarios:

1. NULL -> valor permitido (Wave 7 readiness — backfill de provas
   legadas v3.0).
2. valor -> outro_valor bloqueado (RN-002 v4.0 — imutabilidade).
3. valor -> NULL bloqueado (RN-002 v4.0 — imutabilidade).
4. `executar_transicao` aprovacao v4.0 preserva rota via trigger
   (modificacao cirurgica ADR-119).
5. `executar_transicao` reinicio de ciclo v4.0 preserva rota via
   trigger (AUD-W2V4-001 fix — ADR-123).

O teste #5 e o validador AUTOMATIZADO do fix do AUD-W2V4-001. Sem
ele, qualquer regressao futura no `state_machine.executar_transicao`
ramo `reiniciando_ciclo` quebra Wave 7 sem deteccao na CI.

Pre-requisito:
  Variavel de ambiente `INTEGRATION_DATABASE_URL` apontando para um
  banco PostgreSQL com o schema da migration 012 aplicado (trigger
  + funcao `fn_bloquear_alteracao_rota` ativos). Pode ser:
    - Banco local Docker (`docker compose up postgres`).
    - Branch isolada do Supabase (criada via MCP `create_branch`).
    - Banco efemero `pytest-postgresql` (futuro setup).

  Se a variavel nao estiver definida, todos os testes SKIPAM com
  mensagem clara — comportamento alinhado com o resto da suite que
  usa `mock_db` por padrao.

Execucao:
  INTEGRATION_DATABASE_URL=postgresql+asyncpg://... \\
      pytest backend/tests/test_imutabilidade_rota.py -v

Wave 7 (Componente 21) DEVE rodar esta suite com banco real antes
de fazer backfill em producao. O teste #1 valida que `NULL -> valor`
ainda eh permitido pelo trigger; sem ele, o backfill quebra.
"""
from __future__ import annotations

import os
import uuid as _uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.db.models import (
    LocalizacaoEnum,
    ProvaDigital,
    RotaEnum,
    SetorEnum,
    StatusProvaEnum,
    Usuario,
)
from app.services.state_machine import executar_transicao


# ─── Skip global se nao houver banco real disponivel ─────────────────────

_INTEGRATION_DB_URL = os.environ.get("INTEGRATION_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    _INTEGRATION_DB_URL is None,
    reason=(
        "Set INTEGRATION_DATABASE_URL=postgresql+asyncpg://... para rodar "
        "estes testes contra um banco real com o trigger "
        "trg_provas_rota_imutavel ativo. Sem essa variavel, os testes "
        "sao pulados — alinhado com o padrao do resto da suite."
    ),
)


ASSINATURA_FAKE = b"\x89PNG\r\n\x1a\n" + b"x" * 100  # PNG header + payload curto


# ─── Fixtures de banco real ───────────────────────────────────────────────


@pytest.fixture(scope="module")
async def integration_engine():
    """Engine async com `INTEGRATION_DATABASE_URL`. Module-scope reutiliza
    pool entre os 5 testes."""
    engine = create_async_engine(_INTEGRATION_DB_URL, echo=False)  # type: ignore[arg-type]
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(integration_engine):
    """Session que abre uma transacao isolada e da rollback no final.

    Toda mutacao feita no teste e revertida — banco volta ao estado
    original. Permite rodar contra ambiente compartilhado sem efeitos
    colaterais.
    """
    async with integration_engine.connect() as conn:
        trans = await conn.begin()
        async with AsyncSession(bind=conn, expire_on_commit=False) as session:
            yield session
        await trans.rollback()


@pytest.fixture
async def admin_persistido(db_session: AsyncSession) -> Usuario:
    """Cria admin temporario na transacao (some no rollback)."""
    admin = Usuario(
        id=_uuid.uuid4(),
        auth_uid=_uuid.uuid4(),
        nome="Admin Integ Test",
        email=f"admin-integ-{_uuid.uuid4().hex[:8]}@test.com",
        setor=SetorEnum.STUDIO,
        localizacao=None,
        is_admin=True,
        ativo=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(admin)
    await db_session.flush()
    return admin


async def _criar_prova(
    db: AsyncSession,
    *,
    vendedor_id: _uuid.UUID,
    rota: RotaEnum | None,
    status: StatusProvaEnum = StatusProvaEnum.CRIADA,
    ciclo_atual: int = 1,
) -> ProvaDigital:
    """Helper — cria prova com codigo_publico unico no schema."""
    prova = ProvaDigital(
        id=_uuid.uuid4(),
        nome="Prova Integ Test",
        nro_requerimento=f"REQ-{_uuid.uuid4().hex[:12]}",
        codigo_publico=f"PRV-2026-05-{_uuid.uuid4().hex[:6].upper()}",
        cliente="Cliente Integ",
        vendedor_id=vendedor_id,
        imagem_url=f"provas/{_uuid.uuid4()}/arte.jpg",
        qr_code_hash=f"{_uuid.uuid4().hex}{_uuid.uuid4().hex}",  # 64 chars
        status=status,
        rota=rota,
        ciclo_atual=ciclo_atual,
    )
    db.add(prova)
    await db.flush()
    return prova


@pytest.fixture
async def vendedor_matriz_persistido(db_session: AsyncSession) -> Usuario:
    """Vendedor MATRIZ temporario (some no rollback)."""
    vendedor = Usuario(
        id=_uuid.uuid4(),
        auth_uid=_uuid.uuid4(),
        nome="Vendedor MATRIZ Integ",
        email=f"vmatriz-integ-{_uuid.uuid4().hex[:8]}@test.com",
        setor=SetorEnum.VENDEDOR,
        localizacao=LocalizacaoEnum.MATRIZ,
        is_admin=False,
        ativo=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(vendedor)
    await db_session.flush()
    return vendedor


# ─── Cenario 1: NULL -> valor permitido (Wave 7 readiness) ────────────────


@pytest.mark.asyncio
async def test_trigger_permite_null_to_valor_v4(
    db_session: AsyncSession, vendedor_matriz_persistido: Usuario
):
    """RN-002 v4.0 + Wave 7 backfill (ADR-117): trigger PERMITE
    `NULL -> valor` para que o Componente 21 da Wave 7 possa preencher
    rota das 11 provas legacy v3.0 com `rota=NULL` em producao.

    Este e o teste cabal de Wave 7 readiness. Se este teste FALHAR, a
    Wave 7 nao consegue rodar.
    """
    prova = await _criar_prova(
        db_session, vendedor_id=vendedor_matriz_persistido.id, rota=None
    )
    # UPDATE direto via SQL (representa o comportamento da Wave 7
    # Componente 21 que vai usar UPDATE em massa via Alembic).
    await db_session.execute(
        text(
            "UPDATE provas_digitais SET rota = 'MATRIZ'::rota_enum "
            "WHERE id = :id"
        ),
        {"id": prova.id},
    )
    await db_session.flush()

    # Re-le do banco e confirma que rota foi setada.
    row = (
        await db_session.execute(
            text("SELECT rota FROM provas_digitais WHERE id = :id"),
            {"id": prova.id},
        )
    ).mappings().first()
    assert row is not None
    assert row["rota"] == "MATRIZ"


# ─── Cenario 2: valor -> outro_valor bloqueado ────────────────────────────


@pytest.mark.asyncio
async def test_trigger_bloqueia_valor_to_outro_valor(
    db_session: AsyncSession, vendedor_matriz_persistido: Usuario
):
    """RN-002 v4.0: rota e imutavel apos definicao. Trigger deve
    levantar SQLSTATE 22023."""
    prova = await _criar_prova(
        db_session,
        vendedor_id=vendedor_matriz_persistido.id,
        rota=RotaEnum.MATRIZ,
    )
    with pytest.raises((IntegrityError, DBAPIError)) as excinfo:
        await db_session.execute(
            text(
                "UPDATE provas_digitais SET rota = 'FILIAL'::rota_enum "
                "WHERE id = :id"
            ),
            {"id": prova.id},
        )
        await db_session.flush()
    assert "22023" in str(excinfo.value) or "imutavel" in str(excinfo.value).lower()


# ─── Cenario 3: valor -> NULL bloqueado ───────────────────────────────────


@pytest.mark.asyncio
async def test_trigger_bloqueia_valor_to_null(
    db_session: AsyncSession, vendedor_matriz_persistido: Usuario
):
    """RN-002 v4.0: trigger bloqueia `valor -> NULL` (que era exatamente
    o bug do AUD-W2V4-001 antes do fix)."""
    prova = await _criar_prova(
        db_session,
        vendedor_id=vendedor_matriz_persistido.id,
        rota=RotaEnum.LAM_FILIAL,
    )
    with pytest.raises((IntegrityError, DBAPIError)) as excinfo:
        await db_session.execute(
            text("UPDATE provas_digitais SET rota = NULL WHERE id = :id"),
            {"id": prova.id},
        )
        await db_session.flush()
    assert "22023" in str(excinfo.value) or "imutavel" in str(excinfo.value).lower()


# ─── Cenario 4: executar_transicao aprovacao v4.0 preserva rota ──────────


@pytest.mark.asyncio
async def test_executar_aprovacao_v4_preserva_rota_via_trigger(
    db_session: AsyncSession,
    vendedor_matriz_persistido: Usuario,
    admin_persistido: Usuario,
):
    """ADR-119 (modificacao cirurgica): aprovacao de prova v4.0 com
    rota=MATRIZ preserva rota — trigger nao dispara porque OLD.rota
    IS NOT DISTINCT FROM NEW.rota.

    Pre-correcao (Wave 3 v3.0): zerava rota via determinar_rota,
    disparava trigger, aprovacao falhava.
    """
    prova = await _criar_prova(
        db_session,
        vendedor_id=vendedor_matriz_persistido.id,
        rota=RotaEnum.MATRIZ,
        status=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
    )
    movimentacao = await executar_transicao(
        db_session,
        prova=prova,
        status_novo=StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        usuario=vendedor_matriz_persistido,
        assinatura_digital=ASSINATURA_FAKE,
    )
    await db_session.flush()

    # Rota preservada (sem trigger disparar).
    assert prova.rota == RotaEnum.MATRIZ
    assert movimentacao.rota_no_momento == RotaEnum.MATRIZ
    assert prova.status == StatusProvaEnum.APROVADA_PELO_VENDEDOR


# ─── Cenario 5: executar_transicao reinicio v4.0 preserva rota ───────────


@pytest.mark.asyncio
async def test_executar_reinicio_v4_preserva_rota_via_trigger(
    db_session: AsyncSession,
    vendedor_matriz_persistido: Usuario,
    admin_persistido: Usuario,
):
    """AUD-W2V4-001 + ADR-123: reinicio de ciclo de prova v4.0 com
    rota=MATRIZ preserva rota — trigger nao dispara.

    Pre-correcao: zerava rota -> trigger bloqueava com SQLSTATE 22023
    -> endpoint retornava 502. Bug critico que tornava reinicio de
    ciclo inutil para qualquer prova v4.0.

    Este e o validador AUTOMATIZADO do fix do AUD-W2V4-001.
    """
    prova = await _criar_prova(
        db_session,
        vendedor_id=vendedor_matriz_persistido.id,
        rota=RotaEnum.LAM_MATRIZ,
        status=StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
        ciclo_atual=1,
    )
    movimentacao = await executar_transicao(
        db_session,
        prova=prova,
        status_novo=StatusProvaEnum.CRIADA,
        usuario=admin_persistido,  # Admin reinicia (RN-006)
        assinatura_digital=ASSINATURA_FAKE,
    )
    await db_session.flush()

    # Rota preservada (sem trigger disparar) — ciclo incrementado.
    assert prova.rota == RotaEnum.LAM_MATRIZ
    assert movimentacao.rota_no_momento == RotaEnum.LAM_MATRIZ
    assert prova.status == StatusProvaEnum.CRIADA
    assert prova.ciclo_atual == 2
    assert movimentacao.ciclo == 2
