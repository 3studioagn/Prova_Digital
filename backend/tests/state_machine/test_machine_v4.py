"""Testes da maquina v4.0 — validar_transicao_v4 + executar_transicao_v4.

Wave 3 v4.0 / Componente 11.

Cobertura alvo (DAT §3, §4.2, Backlog C11): >=95% em machine.py.

Estrategia:
  - Funcoes puras (pode_cancelar, transicoes_validas_v4,
    motivo_obrigatorio_em_v4, validar_transicao_v4): testes isolados
    sem banco.
  - executar_transicao_v4: usa fixture `mock_db` do conftest + patch de
    `log_audit` (mesmo padrao do test_state_machine.py v3.0).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.db.models import (
    LocalizacaoEnum,
    Movimentacao,
    ProvaDigital,
    RotaEnum,
    SetorEnum,
    StatusProvaEnum,
)
from app.services.state_machine import (
    AtorNaoAutorizadoError,
    TransicaoInvalidaError,
)
from app.state_machine.v4.machine import (
    executar_transicao_v4,
    motivo_obrigatorio_em_v4,
    pode_cancelar,
    transicoes_validas_v4,
    validar_transicao_v4,
)
from tests.conftest import make_user


ASSINATURA_FAKE = b"\x89PNG\r\n\x1a\nfake-signature-v4"


def make_prova_v4(
    *,
    status: StatusProvaEnum = StatusProvaEnum.CRIADA,
    rota: RotaEnum = RotaEnum.MATRIZ,
    ciclo_atual: int = 1,
    motivo_cancelamento: str | None = None,
) -> ProvaDigital:
    """Prova v4.0 em memoria (sem banco) — rota sempre preenchida com valor v4.0."""
    now = datetime.now(timezone.utc)
    return ProvaDigital(
        id=uuid.uuid4(),
        nome="Prova v4 Teste",
        nro_requerimento="REQ-V4-001",
        codigo_publico="PRV-2026-05-ABCDEF",
        cliente="Cliente Teste v4",
        vendedor_id=uuid.uuid4(),
        imagem_url="provas/v4/test/arte.png",
        qr_code_hash="b" * 64,
        status=status,
        rota=rota,
        ciclo_atual=ciclo_atual,
        motivo_cancelamento=motivo_cancelamento,
        created_at=now,
        updated_at=now,
    )


# ═══════════════════════════════════════════════════════════════════════════
# pode_cancelar
# ═══════════════════════════════════════════════════════════════════════════


def test_pode_cancelar_estados_ativos_v3_e_v4():
    """Os 15 estados ativos (10 v3.0 + 5 v4.0 nao-terminais) podem ser cancelados."""
    ativos = [
        # v3.0
        StatusProvaEnum.CRIADA,
        StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        StatusProvaEnum.DE_VOLTA_3STUDIO,
        StatusProvaEnum.COM_MOTORISTA,
        StatusProvaEnum.ENVIADA_PARA_CLICHERIA,
        StatusProvaEnum.ENCAMINHADA_A_CLICHERIA,
        StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
        # v4.0
        StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO,
        StatusProvaEnum.COM_MOTORISTA_VOLTA_LAMINACAO,
        StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL,
        StatusProvaEnum.ENCAMINHADA_PARA_LAMINACAO,
        StatusProvaEnum.LAMINACAO_CONCLUIDA,
        StatusProvaEnum.DE_VOLTA_3STUDIO_POS_LAMINACAO,
        StatusProvaEnum.ENCAMINHADA_PARA_O_VENDEDOR,
    ]
    for s in ativos:
        assert pode_cancelar(s), f"{s.value} deveria ser cancelavel"


def test_nao_pode_cancelar_recebida_pela_clicheria():
    assert not pode_cancelar(StatusProvaEnum.RECEBIDA_PELA_CLICHERIA)


def test_nao_pode_cancelar_ja_cancelada():
    assert not pode_cancelar(StatusProvaEnum.CANCELADA)


# ═══════════════════════════════════════════════════════════════════════════
# transicoes_validas_v4
# ═══════════════════════════════════════════════════════════════════════════


def test_transicoes_validas_matriz_criada_vendedor():
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    assert transicoes_validas_v4(
        RotaEnum.MATRIZ, StatusProvaEnum.CRIADA, v
    ) == frozenset({StatusProvaEnum.RETIRADA_PELO_VENDEDOR})


def test_transicoes_validas_matriz_retirada_vendedor_inclui_reprovar():
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    assert transicoes_validas_v4(
        RotaEnum.MATRIZ, StatusProvaEnum.RETIRADA_PELO_VENDEDOR, v
    ) == frozenset({
        StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
    })


def test_transicoes_validas_matriz_de_volta_motorista():
    m = make_user(setor=SetorEnum.MOTORISTA, localizacao=None)
    assert transicoes_validas_v4(
        RotaEnum.MATRIZ, StatusProvaEnum.DE_VOLTA_3STUDIO, m
    ) == frozenset({StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL})


def test_transicoes_validas_motorista_recebe_vazio_se_ator_errado():
    """Motorista olhando para CRIADA (estado de vendedor) ve conjunto vazio."""
    m = make_user(setor=SetorEnum.MOTORISTA, localizacao=None)
    assert transicoes_validas_v4(
        RotaEnum.MATRIZ, StatusProvaEnum.CRIADA, m
    ) == frozenset()


def test_transicoes_validas_admin_bypassa_setor():
    """Admin (is_admin=True) ve todas as transicoes possiveis em qualquer estado."""
    a = make_user(setor=SetorEnum.STUDIO, localizacao=None, is_admin=True)
    assert transicoes_validas_v4(
        RotaEnum.MATRIZ, StatusProvaEnum.CRIADA, a
    ) == frozenset({StatusProvaEnum.RETIRADA_PELO_VENDEDOR})


def test_transicoes_validas_estado_terminal_retorna_vazio():
    a = make_user(setor=SetorEnum.STUDIO, localizacao=None, is_admin=True)
    assert transicoes_validas_v4(
        RotaEnum.MATRIZ, StatusProvaEnum.RECEBIDA_PELA_CLICHERIA, a
    ) == frozenset()
    assert transicoes_validas_v4(
        RotaEnum.MATRIZ, StatusProvaEnum.CANCELADA, a
    ) == frozenset()


def test_transicoes_validas_rota_legacy_retorna_vazio():
    """Rotas legacy (PADRAO, DIRETA) nao sao da maquina v4.0."""
    a = make_user(setor=SetorEnum.STUDIO, localizacao=None, is_admin=True)
    assert transicoes_validas_v4(
        RotaEnum.PADRAO, StatusProvaEnum.CRIADA, a
    ) == frozenset()
    assert transicoes_validas_v4(
        RotaEnum.DIRETA, StatusProvaEnum.CRIADA, a
    ) == frozenset()


def test_transicoes_validas_filial_criada_vendedor():
    """Decisao M-1: ator=VENDEDOR para Filial.CRIADA → ENCAMINHADA_PARA_O_VENDEDOR."""
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.FILIAL)
    assert transicoes_validas_v4(
        RotaEnum.FILIAL, StatusProvaEnum.CRIADA, v
    ) == frozenset({StatusProvaEnum.ENCAMINHADA_PARA_O_VENDEDOR})


def test_transicoes_validas_studio_em_criada_filial_vazio():
    """STUDIO nao tem permissao em FILIAL.CRIADA → ENCAMINHADA (que eh do vendedor)."""
    s = make_user(setor=SetorEnum.STUDIO, localizacao=None)
    assert transicoes_validas_v4(
        RotaEnum.FILIAL, StatusProvaEnum.CRIADA, s
    ) == frozenset()


def test_transicoes_validas_studio_em_lam_filial_criada_eh_encaminhada_laminacao():
    """3Studio inicia laminacao em rotas Lam.* — confirma na Lam.Filial."""
    s = make_user(setor=SetorEnum.STUDIO, localizacao=None)
    assert transicoes_validas_v4(
        RotaEnum.LAM_FILIAL, StatusProvaEnum.CRIADA, s
    ) == frozenset({StatusProvaEnum.ENCAMINHADA_PARA_LAMINACAO})


def test_transicoes_validas_clicheria_lam_matriz_motorista_ida():
    """US-007: Clicheria confirma termino da laminacao."""
    c = make_user(setor=SetorEnum.CLICHERIA, localizacao=None)
    assert transicoes_validas_v4(
        RotaEnum.LAM_MATRIZ, StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO, c
    ) == frozenset({StatusProvaEnum.LAMINACAO_CONCLUIDA})


# ═══════════════════════════════════════════════════════════════════════════
# motivo_obrigatorio_em_v4
# ═══════════════════════════════════════════════════════════════════════════


def test_motivo_obrigatorio_apenas_reprovacao():
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    obrig = motivo_obrigatorio_em_v4(
        RotaEnum.MATRIZ, StatusProvaEnum.RETIRADA_PELO_VENDEDOR, v
    )
    assert obrig == frozenset({StatusProvaEnum.REPROVADA_PELO_VENDEDOR})


def test_motivo_obrigatorio_sem_reprovacao_disponivel_eh_vazio():
    """Em CRIADA, vendedor so pode retirar — sem motivo obrigatorio."""
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    assert motivo_obrigatorio_em_v4(
        RotaEnum.MATRIZ, StatusProvaEnum.CRIADA, v
    ) == frozenset()


def test_motivo_obrigatorio_rota_legacy_vazio():
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    assert motivo_obrigatorio_em_v4(
        RotaEnum.PADRAO, StatusProvaEnum.RETIRADA_PELO_VENDEDOR, v
    ) == frozenset()


def test_motivo_obrigatorio_terminal_vazio():
    a = make_user(setor=SetorEnum.STUDIO, is_admin=True, localizacao=None)
    assert motivo_obrigatorio_em_v4(
        RotaEnum.MATRIZ, StatusProvaEnum.RECEBIDA_PELA_CLICHERIA, a
    ) == frozenset()


def test_motivo_obrigatorio_motorista_nao_ve_reprovar():
    """Motorista nunca reprova - reprovacao eh do vendedor."""
    m = make_user(setor=SetorEnum.MOTORISTA, localizacao=None)
    assert motivo_obrigatorio_em_v4(
        RotaEnum.MATRIZ, StatusProvaEnum.RETIRADA_PELO_VENDEDOR, m
    ) == frozenset()


# ═══════════════════════════════════════════════════════════════════════════
# validar_transicao_v4 — happy paths
# ═══════════════════════════════════════════════════════════════════════════


def test_validar_matriz_criada_para_retirada():
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    # Nao levanta
    validar_transicao_v4(
        RotaEnum.MATRIZ,
        StatusProvaEnum.CRIADA,
        StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        v,
    )


def test_validar_lam_matriz_motorista_volta_para_pos_laminacao():
    s = make_user(setor=SetorEnum.STUDIO, localizacao=None)
    validar_transicao_v4(
        RotaEnum.LAM_MATRIZ,
        StatusProvaEnum.COM_MOTORISTA_VOLTA_LAMINACAO,
        StatusProvaEnum.DE_VOLTA_3STUDIO_POS_LAMINACAO,
        s,
    )


def test_validar_filial_criada_para_encaminhada_via_vendedor():
    """Decisao M-1 Opcao A."""
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.FILIAL)
    validar_transicao_v4(
        RotaEnum.FILIAL,
        StatusProvaEnum.CRIADA,
        StatusProvaEnum.ENCAMINHADA_PARA_O_VENDEDOR,
        v,
    )


def test_validar_lam_filial_laminacao_concluida_para_encaminhada_vendedor():
    """Lam. Filial - vendedor pega direto da clicheria (sem motorista de volta)."""
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.FILIAL)
    validar_transicao_v4(
        RotaEnum.LAM_FILIAL,
        StatusProvaEnum.LAMINACAO_CONCLUIDA,
        StatusProvaEnum.ENCAMINHADA_PARA_O_VENDEDOR,
        v,
    )


def test_validar_admin_bypassa_setor():
    """Admin pode executar qualquer transicao valida."""
    a = make_user(setor=SetorEnum.CLICHERIA, localizacao=None, is_admin=True)
    validar_transicao_v4(
        RotaEnum.MATRIZ,
        StatusProvaEnum.CRIADA,
        StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        a,
    )


# ═══════════════════════════════════════════════════════════════════════════
# validar_transicao_v4 — rejeicoes
# ═══════════════════════════════════════════════════════════════════════════


def test_validar_rejeita_transicao_invalida():
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    with pytest.raises(TransicaoInvalidaError, match="rota MATRIZ"):
        validar_transicao_v4(
            RotaEnum.MATRIZ,
            StatusProvaEnum.CRIADA,
            StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,  # pulando o fluxo
            v,
        )


def test_validar_rejeita_ator_errado():
    """Motorista tentando retirar (acao do vendedor) → AtorNaoAutorizadoError."""
    m = make_user(setor=SetorEnum.MOTORISTA, localizacao=None)
    with pytest.raises(AtorNaoAutorizadoError, match="setor"):
        validar_transicao_v4(
            RotaEnum.MATRIZ,
            StatusProvaEnum.CRIADA,
            StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
            m,
        )


def test_validar_rejeita_cancelamento_aqui():
    """Cancelamento eh transversal — endpoint dedicado, nao passa por validar_v4."""
    s = make_user(setor=SetorEnum.STUDIO, localizacao=None)
    with pytest.raises(TransicaoInvalidaError, match="POST /\\{id\\}/cancelar"):
        validar_transicao_v4(
            RotaEnum.MATRIZ,
            StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
            StatusProvaEnum.CANCELADA,
            s,
        )


def test_validar_rejeita_reinicio_ciclo_aqui():
    """Reinicio de ciclo eh transversal — endpoint dedicado."""
    s = make_user(setor=SetorEnum.STUDIO, localizacao=None)
    with pytest.raises(TransicaoInvalidaError, match="POST /\\{id\\}/reiniciar-ciclo"):
        validar_transicao_v4(
            RotaEnum.MATRIZ,
            StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
            StatusProvaEnum.CRIADA,
            s,
        )


def test_validar_rejeita_rota_legacy():
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    with pytest.raises(TransicaoInvalidaError, match="nao eh v4.0"):
        validar_transicao_v4(
            RotaEnum.PADRAO,
            StatusProvaEnum.CRIADA,
            StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
            v,
        )


def test_validar_rejeita_origem_sem_transicoes():
    """Estado terminal nao tem transicoes saindo."""
    a = make_user(setor=SetorEnum.STUDIO, localizacao=None, is_admin=True)
    with pytest.raises(TransicaoInvalidaError, match="nao permite"):
        validar_transicao_v4(
            RotaEnum.MATRIZ,
            StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
            StatusProvaEnum.CRIADA,  # destino arbitrario
            a,
        )


# ═══════════════════════════════════════════════════════════════════════════
# executar_transicao_v4 — happy paths com mock_db
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_log_audit():
    """Patch do log_audit em machine.py — evita chamada real ao banco."""
    with patch(
        "app.state_machine.v4.machine.log_audit",
        new=AsyncMock(),
    ) as m:
        yield m


@pytest.mark.asyncio
async def test_executar_matriz_criada_para_retirada(mock_db, mock_log_audit):
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    prova = make_prova_v4(status=StatusProvaEnum.CRIADA, rota=RotaEnum.MATRIZ)

    mov = await executar_transicao_v4(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        usuario=v,
        assinatura_digital=ASSINATURA_FAKE,
    )

    # Movimentacao foi criada com os campos certos
    assert isinstance(mov, Movimentacao)
    assert mov.status_anterior == StatusProvaEnum.CRIADA
    assert mov.status_novo == StatusProvaEnum.RETIRADA_PELO_VENDEDOR
    assert mov.rota_no_momento == RotaEnum.MATRIZ  # rota imutavel
    assert mov.ciclo == 1
    assert mov.assinatura_digital == ASSINATURA_FAKE
    assert mov.motivo_reprovacao is None

    # Prova foi atualizada
    assert prova.status == StatusProvaEnum.RETIRADA_PELO_VENDEDOR
    assert prova.rota == RotaEnum.MATRIZ  # nao mudou
    assert prova.ciclo_atual == 1  # nao mudou

    # Side effects
    mock_db.add.assert_called_once_with(mov)
    mock_db.flush.assert_awaited_once()
    mock_log_audit.assert_awaited_once()
    audit_call = mock_log_audit.call_args
    assert audit_call.kwargs["acao"] == "transitar_status"
    assert audit_call.kwargs["detalhes"]["de"] == "CRIADA"
    assert audit_call.kwargs["detalhes"]["para"] == "RETIRADA_PELO_VENDEDOR"
    assert audit_call.kwargs["detalhes"]["maquina"] == "v4"
    assert audit_call.kwargs["detalhes"]["rota_antes"] == "MATRIZ"
    assert audit_call.kwargs["detalhes"]["rota_depois"] == "MATRIZ"


@pytest.mark.asyncio
async def test_executar_lam_matriz_ida_laminacao_grava_contexto_motorista(mock_db, mock_log_audit):
    """Decisao M-5: contexto_motorista no audit_log.detalhes_json."""
    m = make_user(setor=SetorEnum.MOTORISTA, localizacao=None)
    prova = make_prova_v4(
        status=StatusProvaEnum.ENCAMINHADA_PARA_LAMINACAO,
        rota=RotaEnum.LAM_MATRIZ,
    )

    await executar_transicao_v4(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO,
        usuario=m,
        assinatura_digital=ASSINATURA_FAKE,
    )

    audit_call = mock_log_audit.call_args
    assert audit_call.kwargs["detalhes"]["contexto_motorista"] == "ida_laminacao"


@pytest.mark.asyncio
async def test_executar_lam_matriz_motorista_volta_grava_contexto(mock_db, mock_log_audit):
    m = make_user(setor=SetorEnum.MOTORISTA, localizacao=None)
    prova = make_prova_v4(
        status=StatusProvaEnum.LAMINACAO_CONCLUIDA,
        rota=RotaEnum.LAM_MATRIZ,
    )
    await executar_transicao_v4(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.COM_MOTORISTA_VOLTA_LAMINACAO,
        usuario=m,
        assinatura_digital=ASSINATURA_FAKE,
    )
    assert mock_log_audit.call_args.kwargs["detalhes"]["contexto_motorista"] == "volta_laminacao"


@pytest.mark.asyncio
async def test_executar_matriz_entrega_final_grava_contexto(mock_db, mock_log_audit):
    m = make_user(setor=SetorEnum.MOTORISTA, localizacao=None)
    prova = make_prova_v4(
        status=StatusProvaEnum.DE_VOLTA_3STUDIO,
        rota=RotaEnum.MATRIZ,
    )
    await executar_transicao_v4(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL,
        usuario=m,
        assinatura_digital=ASSINATURA_FAKE,
    )
    assert mock_log_audit.call_args.kwargs["detalhes"]["contexto_motorista"] == "entrega_final"


@pytest.mark.asyncio
async def test_executar_filial_criada_para_encaminhada(mock_db, mock_log_audit):
    """Decisao M-1: ator=VENDEDOR para FILIAL.CRIADA → ENCAMINHADA."""
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.FILIAL)
    prova = make_prova_v4(status=StatusProvaEnum.CRIADA, rota=RotaEnum.FILIAL)

    mov = await executar_transicao_v4(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.ENCAMINHADA_PARA_O_VENDEDOR,
        usuario=v,
        assinatura_digital=ASSINATURA_FAKE,
    )
    assert prova.status == StatusProvaEnum.ENCAMINHADA_PARA_O_VENDEDOR
    assert mov.rota_no_momento == RotaEnum.FILIAL


# ═══════════════════════════════════════════════════════════════════════════
# executar_transicao_v4 — reprovacao
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_executar_reprovacao_exige_motivo(mock_db, mock_log_audit):
    """RF-007: motivo obrigatorio na reprovacao."""
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    prova = make_prova_v4(
        status=StatusProvaEnum.RETIRADA_PELO_VENDEDOR, rota=RotaEnum.MATRIZ
    )

    with pytest.raises(ValueError, match="Motivo da reprovacao"):
        await executar_transicao_v4(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
            usuario=v,
            assinatura_digital=ASSINATURA_FAKE,
            motivo_reprovacao=None,
        )


@pytest.mark.asyncio
async def test_executar_reprovacao_motivo_whitespace_rejeitado(mock_db, mock_log_audit):
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    prova = make_prova_v4(
        status=StatusProvaEnum.RETIRADA_PELO_VENDEDOR, rota=RotaEnum.MATRIZ
    )
    with pytest.raises(ValueError, match="Motivo da reprovacao"):
        await executar_transicao_v4(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
            usuario=v,
            assinatura_digital=ASSINATURA_FAKE,
            motivo_reprovacao="   ",  # so whitespace
        )


@pytest.mark.asyncio
async def test_executar_reprovacao_com_motivo_persiste(mock_db, mock_log_audit):
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    prova = make_prova_v4(
        status=StatusProvaEnum.RETIRADA_PELO_VENDEDOR, rota=RotaEnum.MATRIZ
    )

    mov = await executar_transicao_v4(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
        usuario=v,
        assinatura_digital=ASSINATURA_FAKE,
        motivo_reprovacao="Cor errada na arte",
    )
    assert mov.motivo_reprovacao == "Cor errada na arte"
    assert mov.status_novo == StatusProvaEnum.REPROVADA_PELO_VENDEDOR
    assert prova.status == StatusProvaEnum.REPROVADA_PELO_VENDEDOR
    audit_call = mock_log_audit.call_args
    assert audit_call.kwargs["detalhes"]["motivo_reprovacao"] == "Cor errada na arte"


# ═══════════════════════════════════════════════════════════════════════════
# executar_transicao_v4 — cancelamento (transversal)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_executar_cancelamento_admin_v4(mock_db, mock_log_audit):
    a = make_user(setor=SetorEnum.STUDIO, localizacao=None, is_admin=True)
    prova = make_prova_v4(
        status=StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO,
        rota=RotaEnum.LAM_MATRIZ,
    )

    mov = await executar_transicao_v4(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.CANCELADA,
        usuario=a,
        assinatura_digital=ASSINATURA_FAKE,
        motivo_cancelamento="Cliente desistiu",
    )
    assert mov.status_novo == StatusProvaEnum.CANCELADA
    assert prova.status == StatusProvaEnum.CANCELADA
    assert prova.motivo_cancelamento == "Cliente desistiu"
    # Rota preservada mesmo em cancelamento (RN-002 v4.0)
    assert mov.rota_no_momento == RotaEnum.LAM_MATRIZ
    assert prova.rota == RotaEnum.LAM_MATRIZ


@pytest.mark.asyncio
async def test_executar_cancelamento_studio_sem_admin(mock_db, mock_log_audit):
    """Usuario setor=STUDIO sem is_admin tambem pode cancelar."""
    s = make_user(setor=SetorEnum.STUDIO, localizacao=None, is_admin=False)
    prova = make_prova_v4(status=StatusProvaEnum.CRIADA, rota=RotaEnum.MATRIZ)
    mov = await executar_transicao_v4(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.CANCELADA,
        usuario=s,
        assinatura_digital=ASSINATURA_FAKE,
        motivo_cancelamento="erro de cadastro",
    )
    assert mov.status_novo == StatusProvaEnum.CANCELADA


@pytest.mark.asyncio
async def test_executar_cancelamento_vendedor_rejeitado(mock_db, mock_log_audit):
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    prova = make_prova_v4(
        status=StatusProvaEnum.RETIRADA_PELO_VENDEDOR, rota=RotaEnum.MATRIZ
    )
    with pytest.raises(AtorNaoAutorizadoError, match="setor"):
        await executar_transicao_v4(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.CANCELADA,
            usuario=v,
            assinatura_digital=ASSINATURA_FAKE,
            motivo_cancelamento="tentativa indevida",
        )


@pytest.mark.asyncio
async def test_executar_cancelamento_exige_motivo(mock_db, mock_log_audit):
    a = make_user(setor=SetorEnum.STUDIO, is_admin=True, localizacao=None)
    prova = make_prova_v4(status=StatusProvaEnum.CRIADA, rota=RotaEnum.MATRIZ)
    with pytest.raises(ValueError, match="Motivo do cancelamento"):
        await executar_transicao_v4(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.CANCELADA,
            usuario=a,
            assinatura_digital=ASSINATURA_FAKE,
            motivo_cancelamento=None,
        )


@pytest.mark.asyncio
async def test_executar_cancelamento_rejeita_terminal(mock_db, mock_log_audit):
    a = make_user(setor=SetorEnum.STUDIO, is_admin=True, localizacao=None)
    prova = make_prova_v4(
        status=StatusProvaEnum.RECEBIDA_PELA_CLICHERIA, rota=RotaEnum.MATRIZ
    )
    with pytest.raises(TransicaoInvalidaError, match="estado final"):
        await executar_transicao_v4(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.CANCELADA,
            usuario=a,
            assinatura_digital=ASSINATURA_FAKE,
            motivo_cancelamento="too late",
        )


# ═══════════════════════════════════════════════════════════════════════════
# executar_transicao_v4 — reinicio de ciclo (RF-009 v4.0)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_executar_reinicio_preserva_rota_e_incrementa_ciclo(mock_db, mock_log_audit):
    """RF-009 v4.0: reinicio preserva rota original + ciclo+1 (ADR-123)."""
    a = make_user(setor=SetorEnum.STUDIO, is_admin=True, localizacao=None)
    prova = make_prova_v4(
        status=StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
        rota=RotaEnum.LAM_MATRIZ,
        ciclo_atual=1,
    )

    mov = await executar_transicao_v4(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.CRIADA,
        usuario=a,
        assinatura_digital=ASSINATURA_FAKE,
    )
    assert mov.status_anterior == StatusProvaEnum.REPROVADA_PELO_VENDEDOR
    assert mov.status_novo == StatusProvaEnum.CRIADA
    assert mov.ciclo == 2
    # Rota preservada (RN-002 v4.0)
    assert mov.rota_no_momento == RotaEnum.LAM_MATRIZ
    assert prova.rota == RotaEnum.LAM_MATRIZ
    assert prova.ciclo_atual == 2

    audit_call = mock_log_audit.call_args
    assert audit_call.kwargs["acao"] == "reiniciar_ciclo"
    assert audit_call.kwargs["detalhes"]["rota_antes"] == "LAM_MATRIZ"
    assert audit_call.kwargs["detalhes"]["rota_depois"] == "LAM_MATRIZ"
    assert audit_call.kwargs["detalhes"]["ciclo"] == 2


@pytest.mark.asyncio
async def test_executar_reinicio_vendedor_rejeitado(mock_db, mock_log_audit):
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    prova = make_prova_v4(
        status=StatusProvaEnum.REPROVADA_PELO_VENDEDOR, rota=RotaEnum.MATRIZ
    )
    with pytest.raises(AtorNaoAutorizadoError):
        await executar_transicao_v4(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.CRIADA,
            usuario=v,
            assinatura_digital=ASSINATURA_FAKE,
        )


# ═══════════════════════════════════════════════════════════════════════════
# executar_transicao_v4 — validacoes defensivas
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_executar_rejeita_assinatura_vazia(mock_db, mock_log_audit):
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    prova = make_prova_v4(status=StatusProvaEnum.CRIADA, rota=RotaEnum.MATRIZ)
    with pytest.raises(ValueError, match="Assinatura digital"):
        await executar_transicao_v4(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
            usuario=v,
            assinatura_digital=b"",
        )


@pytest.mark.asyncio
async def test_executar_rejeita_rota_legacy(mock_db, mock_log_audit):
    """Defesa em profundidade: se o roteador da facade errar, machine_v4 rejeita."""
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    prova = make_prova_v4(status=StatusProvaEnum.CRIADA)
    prova.rota = RotaEnum.PADRAO  # forcando legacy
    with pytest.raises(TransicaoInvalidaError, match="nao deve ser processada pela maquina v4.0"):
        await executar_transicao_v4(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
            usuario=v,
            assinatura_digital=ASSINATURA_FAKE,
        )


@pytest.mark.asyncio
async def test_executar_rejeita_rota_none(mock_db, mock_log_audit):
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    prova = make_prova_v4(status=StatusProvaEnum.CRIADA)
    prova.rota = None  # forcando legacy NULL
    with pytest.raises(TransicaoInvalidaError, match="NULL"):
        await executar_transicao_v4(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
            usuario=v,
            assinatura_digital=ASSINATURA_FAKE,
        )


@pytest.mark.asyncio
async def test_executar_rejeita_transicao_ilegal(mock_db, mock_log_audit):
    """Transicao que nao existe na Matriz."""
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    prova = make_prova_v4(status=StatusProvaEnum.CRIADA, rota=RotaEnum.MATRIZ)
    with pytest.raises(TransicaoInvalidaError):
        await executar_transicao_v4(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.LAMINACAO_CONCLUIDA,  # impossivel da CRIADA na MATRIZ
            usuario=v,
            assinatura_digital=ASSINATURA_FAKE,
        )


@pytest.mark.asyncio
async def test_executar_rejeita_ator_errado(mock_db, mock_log_audit):
    c = make_user(setor=SetorEnum.CLICHERIA, localizacao=None)
    prova = make_prova_v4(status=StatusProvaEnum.CRIADA, rota=RotaEnum.MATRIZ)
    with pytest.raises(AtorNaoAutorizadoError):
        await executar_transicao_v4(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
            usuario=c,
            assinatura_digital=ASSINATURA_FAKE,
        )


# ═══════════════════════════════════════════════════════════════════════════
# Fluxos completos (E2E in-memory) — ciclo inteiro de cada rota
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_fluxo_completo_rota_matriz(mock_db, mock_log_audit):
    """Ciclo completo da rota Matriz: 5 transicoes nao-iniciais."""
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    s = make_user(setor=SetorEnum.STUDIO, localizacao=None)
    m = make_user(setor=SetorEnum.MOTORISTA, localizacao=None)
    c = make_user(setor=SetorEnum.CLICHERIA, localizacao=None)
    prova = make_prova_v4(status=StatusProvaEnum.CRIADA, rota=RotaEnum.MATRIZ)

    # 1. CRIADA → RETIRADA (Vendedor)
    await executar_transicao_v4(mock_db, prova=prova, status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR, usuario=v, assinatura_digital=ASSINATURA_FAKE)
    assert prova.status == StatusProvaEnum.RETIRADA_PELO_VENDEDOR

    # 2. RETIRADA → APROVADA (Vendedor)
    await executar_transicao_v4(mock_db, prova=prova, status_novo=StatusProvaEnum.APROVADA_PELO_VENDEDOR, usuario=v, assinatura_digital=ASSINATURA_FAKE)
    assert prova.status == StatusProvaEnum.APROVADA_PELO_VENDEDOR

    # 3. APROVADA → DE_VOLTA_3STUDIO (Studio)
    await executar_transicao_v4(mock_db, prova=prova, status_novo=StatusProvaEnum.DE_VOLTA_3STUDIO, usuario=s, assinatura_digital=ASSINATURA_FAKE)
    assert prova.status == StatusProvaEnum.DE_VOLTA_3STUDIO

    # 4. DE_VOLTA → COM_MOTORISTA_ENTREGA_FINAL (Motorista)
    await executar_transicao_v4(mock_db, prova=prova, status_novo=StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL, usuario=m, assinatura_digital=ASSINATURA_FAKE)
    assert prova.status == StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL

    # 5. COM_MOTORISTA → RECEBIDA (Clicheria)
    await executar_transicao_v4(mock_db, prova=prova, status_novo=StatusProvaEnum.RECEBIDA_PELA_CLICHERIA, usuario=c, assinatura_digital=ASSINATURA_FAKE)
    assert prova.status == StatusProvaEnum.RECEBIDA_PELA_CLICHERIA
    assert prova.rota == RotaEnum.MATRIZ  # imutavel
    assert prova.ciclo_atual == 1


@pytest.mark.asyncio
async def test_fluxo_completo_rota_filial(mock_db, mock_log_audit):
    """Ciclo completo da rota Filial: 3 transicoes nao-iniciais. Sem motorista."""
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.FILIAL)
    c = make_user(setor=SetorEnum.CLICHERIA, localizacao=None)
    prova = make_prova_v4(status=StatusProvaEnum.CRIADA, rota=RotaEnum.FILIAL)

    await executar_transicao_v4(mock_db, prova=prova, status_novo=StatusProvaEnum.ENCAMINHADA_PARA_O_VENDEDOR, usuario=v, assinatura_digital=ASSINATURA_FAKE)
    await executar_transicao_v4(mock_db, prova=prova, status_novo=StatusProvaEnum.APROVADA_PELO_VENDEDOR, usuario=v, assinatura_digital=ASSINATURA_FAKE)
    await executar_transicao_v4(mock_db, prova=prova, status_novo=StatusProvaEnum.RECEBIDA_PELA_CLICHERIA, usuario=c, assinatura_digital=ASSINATURA_FAKE)
    assert prova.status == StatusProvaEnum.RECEBIDA_PELA_CLICHERIA


@pytest.mark.asyncio
async def test_fluxo_completo_rota_lam_matriz(mock_db, mock_log_audit):
    """Ciclo completo da rota Lam. Matriz: 10 transicoes (3 contextos de motorista)."""
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    s = make_user(setor=SetorEnum.STUDIO, localizacao=None)
    m = make_user(setor=SetorEnum.MOTORISTA, localizacao=None)
    c = make_user(setor=SetorEnum.CLICHERIA, localizacao=None)
    prova = make_prova_v4(status=StatusProvaEnum.CRIADA, rota=RotaEnum.LAM_MATRIZ)

    sequencia = [
        (StatusProvaEnum.ENCAMINHADA_PARA_LAMINACAO, s),
        (StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO, m),
        (StatusProvaEnum.LAMINACAO_CONCLUIDA, c),
        (StatusProvaEnum.COM_MOTORISTA_VOLTA_LAMINACAO, m),
        (StatusProvaEnum.DE_VOLTA_3STUDIO_POS_LAMINACAO, s),
        (StatusProvaEnum.RETIRADA_PELO_VENDEDOR, v),
        (StatusProvaEnum.APROVADA_PELO_VENDEDOR, v),
        (StatusProvaEnum.DE_VOLTA_3STUDIO, s),
        (StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL, m),
        (StatusProvaEnum.RECEBIDA_PELA_CLICHERIA, c),
    ]
    for novo_status, ator in sequencia:
        await executar_transicao_v4(
            mock_db, prova=prova, status_novo=novo_status, usuario=ator,
            assinatura_digital=ASSINATURA_FAKE,
        )
    assert prova.status == StatusProvaEnum.RECEBIDA_PELA_CLICHERIA
    assert prova.rota == RotaEnum.LAM_MATRIZ
    assert prova.ciclo_atual == 1


@pytest.mark.asyncio
async def test_fluxo_completo_rota_lam_filial(mock_db, mock_log_audit):
    """Ciclo completo da rota Lam. Filial: 6 transicoes (motorista so na ida)."""
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.FILIAL)
    s = make_user(setor=SetorEnum.STUDIO, localizacao=None)
    m = make_user(setor=SetorEnum.MOTORISTA, localizacao=None)
    c = make_user(setor=SetorEnum.CLICHERIA, localizacao=None)
    prova = make_prova_v4(status=StatusProvaEnum.CRIADA, rota=RotaEnum.LAM_FILIAL)

    sequencia = [
        (StatusProvaEnum.ENCAMINHADA_PARA_LAMINACAO, s),
        (StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO, m),
        (StatusProvaEnum.LAMINACAO_CONCLUIDA, c),
        (StatusProvaEnum.ENCAMINHADA_PARA_O_VENDEDOR, v),
        (StatusProvaEnum.APROVADA_PELO_VENDEDOR, v),
        (StatusProvaEnum.RECEBIDA_PELA_CLICHERIA, c),
    ]
    for novo_status, ator in sequencia:
        await executar_transicao_v4(
            mock_db, prova=prova, status_novo=novo_status, usuario=ator,
            assinatura_digital=ASSINATURA_FAKE,
        )
    assert prova.status == StatusProvaEnum.RECEBIDA_PELA_CLICHERIA


@pytest.mark.asyncio
async def test_fluxo_reprovacao_e_reinicio_lam_matriz(mock_db, mock_log_audit):
    """Vendedor reprova → 3Studio reinicia → ciclo 2 começa preservando rota."""
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    s = make_user(setor=SetorEnum.STUDIO, is_admin=True, localizacao=None)
    prova = make_prova_v4(
        status=StatusProvaEnum.RETIRADA_PELO_VENDEDOR, rota=RotaEnum.LAM_MATRIZ
    )

    # Reprova
    await executar_transicao_v4(
        mock_db, prova=prova,
        status_novo=StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
        usuario=v, assinatura_digital=ASSINATURA_FAKE,
        motivo_reprovacao="erro na arte",
    )
    assert prova.status == StatusProvaEnum.REPROVADA_PELO_VENDEDOR
    assert prova.ciclo_atual == 1

    # Reinicia ciclo
    await executar_transicao_v4(
        mock_db, prova=prova, status_novo=StatusProvaEnum.CRIADA,
        usuario=s, assinatura_digital=ASSINATURA_FAKE,
    )
    assert prova.status == StatusProvaEnum.CRIADA
    assert prova.ciclo_atual == 2
    assert prova.rota == RotaEnum.LAM_MATRIZ  # rota preservada (RN-002 v4.0)
