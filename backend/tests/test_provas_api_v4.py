"""Testes especificos da Wave 2 v4.0 — Componente 06.

Cobertura:
  - Schema Pydantic (`ProvaCreateRequest` + `RotaCriacaoEnum`):
    aceitar 4 rotas v4.0; rejeitar legacy (PADRAO/DIRETA); rejeitar
    rota faltando.
  - State machine cirurgico (`executar_transicao`): preservar rota
    quando ja preenchida (v4.0); derivar via determinar_rota apenas
    em prova legada (rota=NULL).

Os testes de criacao via HTTP estao em `test_provas_api.py` (com
`@pytest.mark.parametrize` no `test_create_prova_happy_path` para
cobrir as 4 rotas).
"""
import uuid
from datetime import datetime, timezone

import pytest

from app.db.models import (
    LocalizacaoEnum,
    ProvaDigital,
    RotaEnum,
    SetorEnum,
    StatusProvaEnum,
)
from app.domain.schemas.prova import ProvaCreateRequest, RotaCriacaoEnum
from app.services.state_machine import executar_transicao
from tests.conftest import make_user

pytestmark = pytest.mark.asyncio


# ─── 1. Schema Pydantic ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "rota_str", ["MATRIZ", "LAM_MATRIZ", "FILIAL", "LAM_FILIAL"]
)
def test_provacreaterequest_aceita_4_rotas_v4(rota_str):
    """Wave 2 v4.0: as 4 rotas v4.0 sao aceitas no schema Pydantic."""
    req = ProvaCreateRequest(
        nome="ok",
        nro_requerimento=f"REQ-{rota_str}",
        cliente="C",
        vendedor_id=uuid.uuid4(),
        rota=rota_str,
        object_key="provas/2026/04/ok/arte.jpg",
    )
    assert req.rota == RotaCriacaoEnum(rota_str)


@pytest.mark.parametrize("rota_legacy", ["PADRAO", "DIRETA"])
def test_provacreaterequest_rejeita_legacy_v3(rota_legacy):
    """Wave 2 v4.0: schema Pydantic da criacao bloqueia legacy v3.0
    (PADRAO/DIRETA) — apenas RotaCriacaoEnum (4 novos valores) e aceita.
    Defesa em profundidade: o trigger PostgreSQL nao bloqueia valor
    legacy entrando como NEW, mas o Pydantic intercepta antes do INSERT.
    """
    with pytest.raises(ValueError):
        ProvaCreateRequest(
            nome="Legacy",
            nro_requerimento="REQ-LEGACY",
            cliente="C",
            vendedor_id=uuid.uuid4(),
            rota=rota_legacy,
            object_key="provas/2026/04/legacy/arte.jpg",
        )


def test_provacreaterequest_rejeita_rota_faltando():
    """Wave 2 v4.0: rota e obrigatoria (RN-007 v4.0)."""
    with pytest.raises(ValueError):
        ProvaCreateRequest(
            nome="Sem Rota",
            nro_requerimento="REQ-SEMROTA",
            cliente="C",
            vendedor_id=uuid.uuid4(),
            object_key="provas/2026/04/sr/arte.jpg",
        )


def test_provacreaterequest_rejeita_rota_invalida_string():
    """Strings fora do enum (ex.: 'foo') sao rejeitadas."""
    with pytest.raises(ValueError):
        ProvaCreateRequest(
            nome="Invalida",
            nro_requerimento="REQ-INV",
            cliente="C",
            vendedor_id=uuid.uuid4(),
            rota="FOO_BAR",
            object_key="provas/2026/04/inv/arte.jpg",
        )


# ─── 2. State machine cirurgico ────────────────────────────────────────────


def _build_prova(*, rota: RotaEnum | None, vendedor_id) -> ProvaDigital:
    now = datetime.now(timezone.utc)
    return ProvaDigital(
        id=uuid.uuid4(),
        nome="Prova",
        nro_requerimento="REQ-SM-V4",
        codigo_publico="PRV-2026-05-SMV401",
        cliente="C",
        vendedor_id=vendedor_id,
        imagem_url="provas/2026/05/x/arte.jpg",
        qr_code_hash="a" * 64,
        status=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        rota=rota,
        ciclo_atual=1,
        motivo_cancelamento=None,
        created_at=now,
        updated_at=now,
    )


async def test_executar_transicao_preserva_rota_v4_na_aprovacao(mock_db):
    """Wave 2 v4.0: prova v4.0 (rota ja persistida) NAO tem rota
    sobrescrita ao aprovar. Sem essa correcao cirurgica, o trigger
    PostgreSQL bloquearia a aprovacao com SQLSTATE 22023.
    """
    vendedor = make_user(
        setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ
    )
    prova = _build_prova(rota=RotaEnum.LAM_MATRIZ, vendedor_id=vendedor.id)

    movimentacao = await executar_transicao(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        usuario=vendedor,
        assinatura_digital=b"\x89PNG\r\n\x1a\n" + b"\x00" * 16,
    )

    # Rota PRESERVADA — nao foi sobrescrita por determinar_rota
    # (que retornaria PADRAO para vendedor MATRIZ na v3.0).
    assert prova.rota == RotaEnum.LAM_MATRIZ
    assert movimentacao.rota_no_momento == RotaEnum.LAM_MATRIZ
    assert prova.status == StatusProvaEnum.APROVADA_PELO_VENDEDOR


async def test_executar_transicao_deriva_rota_em_prova_legada(mock_db):
    """Wave 2 v4.0: prova LEGADA v3.0 (rota=None) ainda tem rota
    derivada pelo `determinar_rota` na aprovacao — comportamento v3.0
    preservado ate a Wave 7 (Componente 21) fazer o backfill final.
    """
    vendedor = make_user(
        setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.FILIAL
    )
    prova = _build_prova(rota=None, vendedor_id=vendedor.id)

    movimentacao = await executar_transicao(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        usuario=vendedor,
        assinatura_digital=b"\x89PNG\r\n\x1a\n" + b"\x00" * 16,
    )

    # Comportamento v3.0: vendedor FILIAL -> rota DIRETA.
    assert prova.rota == RotaEnum.DIRETA
    assert movimentacao.rota_no_momento == RotaEnum.DIRETA


@pytest.mark.parametrize(
    "rota_v4",
    [RotaEnum.MATRIZ, RotaEnum.LAM_MATRIZ, RotaEnum.FILIAL, RotaEnum.LAM_FILIAL],
)
async def test_executar_transicao_preserva_todas_4_rotas_v4(rota_v4, mock_db):
    """Cada uma das 4 rotas v4.0 e preservada pelo executar_transicao
    (parametrizado para cobrir cobertura combinatoria)."""
    # Localizacao do vendedor independe da rota — admin escolheu a rota
    # manualmente (RN-009 v4.0: localizacao informativa).
    vendedor = make_user(
        setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ
    )
    prova = _build_prova(rota=rota_v4, vendedor_id=vendedor.id)

    await executar_transicao(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        usuario=vendedor,
        assinatura_digital=b"\x89PNG\r\n\x1a\n" + b"\x00" * 16,
    )

    assert prova.rota == rota_v4  # imutavel
