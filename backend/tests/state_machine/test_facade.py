"""Testes do facade `app.state_machine.__init__` — roteador v3.0/v4.0.

Wave 3 v4.0 / Componente 11.

Cobertura:
  - is_rota_v4 (3 categorias: NULL, legacy, v4.0)
  - executar_transicao roteia corretamente
  - transicoes_validas roteia corretamente
  - pode_cancelar funciona identicamente para v3.0 e v4.0
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.db.models import (
    LocalizacaoEnum,
    ProvaDigital,
    RotaEnum,
    SetorEnum,
    StatusProvaEnum,
)
from app.state_machine import (
    executar_transicao,
    is_rota_v4,
    pode_cancelar,
    transicoes_validas,
)
from tests.conftest import make_user


def _make_prova(rota: RotaEnum | None, status: StatusProvaEnum = StatusProvaEnum.CRIADA) -> ProvaDigital:
    now = datetime.now(timezone.utc)
    return ProvaDigital(
        id=uuid.uuid4(),
        nome="Test Prova",
        nro_requerimento="REQ-FAC-001",
        codigo_publico="PRV-2026-05-XYZ123",
        cliente="Cliente",
        vendedor_id=uuid.uuid4(),
        imagem_url="img.png",
        qr_code_hash="x" * 64,
        status=status,
        rota=rota,
        ciclo_atual=1,
        motivo_cancelamento=None,
        created_at=now,
        updated_at=now,
    )


# ── is_rota_v4 ─────────────────────────────────────────────────────────────


def test_is_rota_v4_none_eh_false():
    assert is_rota_v4(None) is False


def test_is_rota_v4_legacy_padrao_eh_false():
    assert is_rota_v4(RotaEnum.PADRAO) is False


def test_is_rota_v4_legacy_direta_eh_false():
    assert is_rota_v4(RotaEnum.DIRETA) is False


@pytest.mark.parametrize("rota", [
    RotaEnum.MATRIZ,
    RotaEnum.LAM_MATRIZ,
    RotaEnum.FILIAL,
    RotaEnum.LAM_FILIAL,
])
def test_is_rota_v4_v4_eh_true(rota: RotaEnum):
    assert is_rota_v4(rota) is True


# ── transicoes_validas (roteamento) ─────────────────────────────────────────


def test_transicoes_validas_rota_v4_retorna_destinos():
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    prova = _make_prova(rota=RotaEnum.MATRIZ, status=StatusProvaEnum.CRIADA)
    destinos = transicoes_validas(prova, v)
    assert destinos == frozenset({StatusProvaEnum.RETIRADA_PELO_VENDEDOR})


def test_transicoes_validas_legacy_retorna_vazio():
    """Provas legacy (rota=NULL ou PADRAO/DIRETA) caem no caller v3.0 — facade retorna vazio."""
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)

    prova_null = _make_prova(rota=None, status=StatusProvaEnum.CRIADA)
    assert transicoes_validas(prova_null, v) == frozenset()

    prova_padrao = _make_prova(rota=RotaEnum.PADRAO, status=StatusProvaEnum.CRIADA)
    assert transicoes_validas(prova_padrao, v) == frozenset()

    prova_direta = _make_prova(rota=RotaEnum.DIRETA, status=StatusProvaEnum.CRIADA)
    assert transicoes_validas(prova_direta, v) == frozenset()


# ── pode_cancelar ──────────────────────────────────────────────────────────


def test_pode_cancelar_compat_v3_v4():
    """Os 15 estados ativos (10 v3.0 + 5 v4.0 ativos) sao cancelaveis."""
    ativos = [
        StatusProvaEnum.CRIADA,
        StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        StatusProvaEnum.COM_MOTORISTA,  # legacy
        StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO,  # v4.0
        StatusProvaEnum.LAMINACAO_CONCLUIDA,  # v4.0
    ]
    for s in ativos:
        assert pode_cancelar(s)


def test_pode_cancelar_terminais_falso():
    assert not pode_cancelar(StatusProvaEnum.RECEBIDA_PELA_CLICHERIA)
    assert not pode_cancelar(StatusProvaEnum.CANCELADA)


# ── executar_transicao (roteamento) ────────────────────────────────────────


@pytest.mark.asyncio
async def test_executar_roteia_v4_quando_rota_v4(mock_db):
    """Prova com rota v4.0 vai para executar_transicao_v4."""
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    prova = _make_prova(rota=RotaEnum.MATRIZ, status=StatusProvaEnum.CRIADA)

    with patch(
        "app.state_machine.executar_transicao_v4",
        new=AsyncMock(return_value="MOCK_MOV_V4"),
    ) as mock_v4, patch(
        "app.state_machine._executar_v3",
        new=AsyncMock(return_value="MOCK_MOV_V3"),
    ) as mock_v3:
        result = await executar_transicao(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
            usuario=v,
            assinatura_digital=b"sig",
        )
        assert result == "MOCK_MOV_V4"
        mock_v4.assert_awaited_once()
        mock_v3.assert_not_awaited()


@pytest.mark.asyncio
async def test_executar_roteia_v3_quando_rota_null(mock_db):
    """Prova legacy (rota=NULL) vai para executar_transicao v3.0."""
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    prova = _make_prova(rota=None, status=StatusProvaEnum.CRIADA)

    with patch(
        "app.state_machine.executar_transicao_v4",
        new=AsyncMock(return_value="MOCK_MOV_V4"),
    ) as mock_v4, patch(
        "app.state_machine._executar_v3",
        new=AsyncMock(return_value="MOCK_MOV_V3"),
    ) as mock_v3:
        result = await executar_transicao(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
            usuario=v,
            assinatura_digital=b"sig",
        )
        assert result == "MOCK_MOV_V3"
        mock_v3.assert_awaited_once()
        mock_v4.assert_not_awaited()


@pytest.mark.asyncio
async def test_executar_roteia_v3_quando_rota_legacy_padrao(mock_db):
    """Prova legacy preenchida (rota=PADRAO) vai para v3.0."""
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    prova = _make_prova(rota=RotaEnum.PADRAO, status=StatusProvaEnum.CRIADA)

    with patch(
        "app.state_machine.executar_transicao_v4",
        new=AsyncMock(return_value="MOCK_MOV_V4"),
    ) as mock_v4, patch(
        "app.state_machine._executar_v3",
        new=AsyncMock(return_value="MOCK_MOV_V3"),
    ) as mock_v3:
        await executar_transicao(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
            usuario=v,
            assinatura_digital=b"sig",
        )
        mock_v3.assert_awaited_once()
        mock_v4.assert_not_awaited()


@pytest.mark.asyncio
async def test_executar_passa_kwargs_corretamente(mock_db):
    """Todos os kwargs sao passados sem perda."""
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    prova = _make_prova(rota=RotaEnum.MATRIZ, status=StatusProvaEnum.CRIADA)
    request_sentinel = object()

    with patch(
        "app.state_machine.executar_transicao_v4",
        new=AsyncMock(),
    ) as mock_v4:
        await executar_transicao(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
            usuario=v,
            assinatura_digital=b"sig",
            motivo_reprovacao="motivo X",
            motivo_cancelamento="motivo Y",
            request=request_sentinel,
        )
        call = mock_v4.call_args
        assert call.kwargs["prova"] is prova
        assert call.kwargs["status_novo"] == StatusProvaEnum.RETIRADA_PELO_VENDEDOR
        assert call.kwargs["usuario"] is v
        assert call.kwargs["assinatura_digital"] == b"sig"
        assert call.kwargs["motivo_reprovacao"] == "motivo X"
        assert call.kwargs["motivo_cancelamento"] == "motivo Y"
        assert call.kwargs["request"] is request_sentinel
