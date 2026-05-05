"""Testes unitarios da maquina de estados (ADR-040 + ADR-081).

Cobertura alvo: TRANSICOES, ATORES_POR_TRANSICAO, determinar_rota,
transicao_e_valida, pode_cancelar, atores_permitidos, validar_transicao,
executar_transicao.

Zero dependencia de HTTP e zero banco real. `executar_transicao` usa o
`mock_db` (fixture do conftest) e patcha `log_audit` — o contrato com
AsyncSession + Movimentacao.add() e observavel sem banco.
"""
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
    ATORES_POR_TRANSICAO,
    TRANSICOES,
    AtorNaoAutorizadoError,
    RotaIndeterminavelError,
    TransicaoInvalidaError,
    atores_permitidos,
    determinar_rota,
    executar_transicao,
    pode_cancelar,
    transicao_e_valida,
    validar_transicao,
)
from tests.conftest import make_user


def make_prova(
    *,
    status: StatusProvaEnum = StatusProvaEnum.CRIADA,
    rota: RotaEnum | None = None,
    ciclo_atual: int = 1,
    motivo_cancelamento: str | None = None,
    vendedor_id: uuid.UUID | None = None,
) -> ProvaDigital:
    """Helper para instanciar ProvaDigital em memoria (sem banco).

    Os campos com server_default no ORM precisam ser definidos manualmente
    aqui porque nunca ocorre um INSERT real — ficariam None caso contrario
    e poderiam mascarar bugs em asserts do tipo `prova.ciclo_atual + 1`.
    """
    now = datetime.now(timezone.utc)
    return ProvaDigital(
        id=uuid.uuid4(),
        nome="Prova Teste",
        nro_requerimento="REQ-TEST-001",
        cliente="Cliente Teste",
        vendedor_id=vendedor_id or uuid.uuid4(),
        imagem_url="provas/2026/04/test/arte.png",
        qr_code_hash="a" * 64,
        status=status,
        rota=rota,
        ciclo_atual=ciclo_atual,
        motivo_cancelamento=motivo_cancelamento,
        created_at=now,
        updated_at=now,
    )


ASSINATURA_FAKE = b"\x89PNG\r\n\x1a\nfake-signature-bytes-for-testing"

# ─── determinar_rota ─────────────────────────────────────────────────────


def test_determinar_rota_matriz():
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    assert determinar_rota(v) == RotaEnum.PADRAO


def test_determinar_rota_filial():
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.FILIAL)
    assert determinar_rota(v) == RotaEnum.DIRETA


def test_determinar_rota_rejeita_nao_vendedor():
    u = make_user(setor=SetorEnum.STUDIO, localizacao=None)
    with pytest.raises(RotaIndeterminavelError, match="so se aplica a vendedores"):
        determinar_rota(u)


def test_determinar_rota_rejeita_vendedor_sem_localizacao():
    # Nao e possivel instanciar no banco real (CHECK constraint), mas no ORM
    # em memoria podemos construir o objeto sem localizacao para testar.
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=None)
    with pytest.raises(RotaIndeterminavelError, match="nao tem localizacao"):
        determinar_rota(v)


def test_determinar_rota_rejeita_localizacao_desconhecida():
    """Defensive — cobre o fallback para valor de localizacao fora do enum.

    Em producao isso e impossivel (enum do PG + CHECK constraint), mas a
    guarda existe desde Wave 2 como protecao para futuro valor novo em
    LocalizacaoEnum sem atualizacao do determinar_rota. Usa SimpleNamespace
    para passar duck-typing sem depender do validator do SQLAlchemy.
    """
    from types import SimpleNamespace

    fake_vendedor = SimpleNamespace(
        id=uuid.uuid4(),
        setor=SetorEnum.VENDEDOR,
        localizacao="UNKNOWN_LOCATION",  # nao e MATRIZ nem FILIAL
    )
    with pytest.raises(RotaIndeterminavelError, match="desconhecida"):
        determinar_rota(fake_vendedor)


# ─── transicao_e_valida ──────────────────────────────────────────────────


def test_transicao_criada_para_retirada():
    assert transicao_e_valida(
        StatusProvaEnum.CRIADA, StatusProvaEnum.RETIRADA_PELO_VENDEDOR
    )


def test_transicao_retirada_para_aprovada():
    assert transicao_e_valida(
        StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        StatusProvaEnum.APROVADA_PELO_VENDEDOR,
    )


def test_transicao_retirada_para_reprovada():
    assert transicao_e_valida(
        StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
    )


def test_transicao_aprovada_para_matriz_path():
    assert transicao_e_valida(
        StatusProvaEnum.APROVADA_PELO_VENDEDOR, StatusProvaEnum.DE_VOLTA_3STUDIO
    )


def test_transicao_aprovada_para_filial_path():
    assert transicao_e_valida(
        StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        StatusProvaEnum.ENCAMINHADA_A_CLICHERIA,
    )


def test_transicao_reprovada_para_criada_reinicio_ciclo():
    assert transicao_e_valida(
        StatusProvaEnum.REPROVADA_PELO_VENDEDOR, StatusProvaEnum.CRIADA
    )


def test_transicao_ilegal_criada_para_recebida():
    """Pular direto para o final e invalido (RN-002)."""
    assert not transicao_e_valida(
        StatusProvaEnum.CRIADA, StatusProvaEnum.RECEBIDA_PELA_CLICHERIA
    )


def test_transicao_ilegal_aprovada_para_retirada():
    """Voltar no fluxo e invalido."""
    assert not transicao_e_valida(
        StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
    )


def test_transicao_estado_terminal_recebida():
    """RECEBIDA_PELA_CLICHERIA e terminal — nenhuma transicao saindo."""
    assert TRANSICOES[StatusProvaEnum.RECEBIDA_PELA_CLICHERIA] == set()


def test_transicao_estado_terminal_cancelada():
    """CANCELADA e terminal."""
    assert TRANSICOES[StatusProvaEnum.CANCELADA] == set()


# ─── pode_cancelar ───────────────────────────────────────────────────────


def test_pode_cancelar_criada():
    assert pode_cancelar(StatusProvaEnum.CRIADA)


def test_pode_cancelar_estados_intermediarios():
    for st in [
        StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        StatusProvaEnum.DE_VOLTA_3STUDIO,
        StatusProvaEnum.COM_MOTORISTA,
        StatusProvaEnum.ENVIADA_PARA_CLICHERIA,
        StatusProvaEnum.ENCAMINHADA_A_CLICHERIA,
        StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
    ]:
        assert pode_cancelar(st), f"{st.value} deveria ser cancelavel"


def test_nao_pode_cancelar_terminal_sucesso():
    assert not pode_cancelar(StatusProvaEnum.RECEBIDA_PELA_CLICHERIA)


def test_nao_pode_cancelar_ja_cancelada():
    assert not pode_cancelar(StatusProvaEnum.CANCELADA)


# ─── atores_permitidos ──────────────────────────────────────────────────


def test_atores_transicao_criada_para_retirada():
    assert atores_permitidos(
        StatusProvaEnum.CRIADA, StatusProvaEnum.RETIRADA_PELO_VENDEDOR
    ) == {SetorEnum.VENDEDOR}


def test_atores_transicao_com_motorista_para_enviada():
    assert atores_permitidos(
        StatusProvaEnum.COM_MOTORISTA, StatusProvaEnum.ENVIADA_PARA_CLICHERIA
    ) == {SetorEnum.MOTORISTA}


def test_atores_transicao_recebimento_clicheria():
    assert atores_permitidos(
        StatusProvaEnum.ENVIADA_PARA_CLICHERIA,
        StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
    ) == {SetorEnum.CLICHERIA}


def test_atores_cancelamento_sempre_studio():
    """Cancelamento vindo de qualquer estado -> so STUDIO (RN-005)."""
    for st in StatusProvaEnum:
        if st not in {StatusProvaEnum.CANCELADA, StatusProvaEnum.RECEBIDA_PELA_CLICHERIA}:
            assert atores_permitidos(st, StatusProvaEnum.CANCELADA) == {
                SetorEnum.STUDIO
            }


# ─── validar_transicao ───────────────────────────────────────────────────


def test_validar_happy_vendedor_retira():
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    # Nao deve levantar
    validar_transicao(
        StatusProvaEnum.CRIADA, StatusProvaEnum.RETIRADA_PELO_VENDEDOR, v
    )


def test_validar_rejeita_transicao_ilegal():
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    with pytest.raises(TransicaoInvalidaError, match="Transicao invalida"):
        validar_transicao(
            StatusProvaEnum.CRIADA, StatusProvaEnum.RECEBIDA_PELA_CLICHERIA, v
        )


def test_validar_rejeita_ator_errado():
    """Motorista tentando retirar do status CRIADA → deve ser vendedor."""
    m = make_user(setor=SetorEnum.MOTORISTA, localizacao=None)
    with pytest.raises(AtorNaoAutorizadoError, match="nao autorizado"):
        validar_transicao(
            StatusProvaEnum.CRIADA, StatusProvaEnum.RETIRADA_PELO_VENDEDOR, m
        )


def test_validar_admin_bypassa_setor():
    """Admin (is_admin=true) pode executar qualquer transicao valida."""
    a = make_user(setor=SetorEnum.CLICHERIA, localizacao=None, is_admin=True)
    validar_transicao(
        StatusProvaEnum.CRIADA, StatusProvaEnum.RETIRADA_PELO_VENDEDOR, a
    )


def test_validar_cancelamento_ok_para_studio():
    s = make_user(setor=SetorEnum.STUDIO, localizacao=None)
    validar_transicao(
        StatusProvaEnum.COM_MOTORISTA, StatusProvaEnum.CANCELADA, s
    )


def test_validar_cancelamento_rejeita_terminal():
    s = make_user(setor=SetorEnum.STUDIO, localizacao=None)
    with pytest.raises(TransicaoInvalidaError, match="Nao e possivel cancelar"):
        validar_transicao(
            StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
            StatusProvaEnum.CANCELADA,
            s,
        )


def test_validar_cancelamento_rejeita_nao_studio():
    v = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    with pytest.raises(AtorNaoAutorizadoError, match="Cancelamento restrito"):
        validar_transicao(
            StatusProvaEnum.CRIADA, StatusProvaEnum.CANCELADA, v
        )


# ─── executar_transicao (Wave 3 / ADR-081) ───────────────────────────────
#
# Todos os testes abaixo usam a fixture `mock_db` e patcham
# `app.services.state_machine.log_audit` para observar as chamadas de audit
# sem dependencia real de banco. A funcao e async, entao os testes sao
# async marcados com `pytest.mark.asyncio`.


@pytest.fixture
def mock_log_audit():
    """Patch local em log_audit para observar chamadas de auditoria.

    `log_audit` e chamada pelo executar_transicao apos o flush da
    movimentacao. O patch troca a funcao importada no modulo state_machine
    por um AsyncMock para que os testes possam inspecionar `call_args` sem
    precisar de AuditLog real ou db.flush() dentro do log_audit.
    """
    with patch(
        "app.services.state_machine.log_audit", new_callable=AsyncMock
    ) as mock:
        yield mock


@pytest.mark.asyncio
async def test_executar_happy_criada_para_retirada_vendedor_matriz(
    mock_db, mock_log_audit, vendedor_matriz
):
    """Teste 1 — Happy path CRIADA -> RETIRADA. Sem rota populada (so nas
    aprovacoes). Movimentacao copia ciclo=1 e rota_no_momento=None."""
    prova = make_prova(status=StatusProvaEnum.CRIADA, rota=None, ciclo_atual=1)

    result = await executar_transicao(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        usuario=vendedor_matriz,
        assinatura_digital=ASSINATURA_FAKE,
    )

    assert isinstance(result, Movimentacao)
    assert result.status_anterior == StatusProvaEnum.CRIADA
    assert result.status_novo == StatusProvaEnum.RETIRADA_PELO_VENDEDOR
    assert result.ciclo == 1
    assert result.rota_no_momento is None
    assert result.motivo_reprovacao is None

    # A prova deve ter seu status atualizado em memoria
    assert prova.status == StatusProvaEnum.RETIRADA_PELO_VENDEDOR
    assert prova.rota is None  # Rota so persiste na aprovacao
    assert prova.ciclo_atual == 1

    # db.add foi chamado com a movimentacao
    mock_db.add.assert_called_once_with(result)
    mock_db.flush.assert_awaited_once()

    # Audit log chamado com acao padrao
    mock_log_audit.assert_awaited_once()
    kwargs = mock_log_audit.call_args.kwargs
    assert kwargs["acao"] == "transitar_status"
    assert kwargs["usuario_id"] == vendedor_matriz.id
    assert kwargs["prova_id"] == prova.id
    assert kwargs["detalhes"]["de"] == "CRIADA"
    assert kwargs["detalhes"]["para"] == "RETIRADA_PELO_VENDEDOR"
    assert kwargs["detalhes"]["ciclo"] == 1
    assert kwargs["detalhes"]["rota_antes"] is None
    assert kwargs["detalhes"]["rota_depois"] is None


@pytest.mark.asyncio
async def test_executar_happy_aprovacao_matriz_persiste_rota_padrao(
    mock_db, mock_log_audit, vendedor_matriz
):
    """Teste 2 — Aprovacao por vendedor MATRIZ persiste rota=PADRAO
    (RN-007 + ADR-042)."""
    prova = make_prova(status=StatusProvaEnum.RETIRADA_PELO_VENDEDOR)

    result = await executar_transicao(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        usuario=vendedor_matriz,
        assinatura_digital=ASSINATURA_FAKE,
    )

    assert result.rota_no_momento == RotaEnum.PADRAO
    assert prova.rota == RotaEnum.PADRAO
    assert prova.status == StatusProvaEnum.APROVADA_PELO_VENDEDOR

    kwargs = mock_log_audit.call_args.kwargs
    assert kwargs["detalhes"]["rota_antes"] is None
    assert kwargs["detalhes"]["rota_depois"] == "PADRAO"


@pytest.mark.asyncio
async def test_executar_happy_aprovacao_filial_persiste_rota_direta(
    mock_db, mock_log_audit, vendedor_filial
):
    """Teste 3 — Aprovacao por vendedor FILIAL persiste rota=DIRETA."""
    prova = make_prova(status=StatusProvaEnum.RETIRADA_PELO_VENDEDOR)

    result = await executar_transicao(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        usuario=vendedor_filial,
        assinatura_digital=ASSINATURA_FAKE,
    )

    assert result.rota_no_momento == RotaEnum.DIRETA
    assert prova.rota == RotaEnum.DIRETA


@pytest.mark.asyncio
async def test_executar_happy_reprovacao_com_motivo(
    mock_db, mock_log_audit, vendedor_matriz
):
    """Teste 4 — Reprovacao armazena motivo normalizado (strip) e propaga
    para o audit log."""
    prova = make_prova(status=StatusProvaEnum.RETIRADA_PELO_VENDEDOR)

    result = await executar_transicao(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
        usuario=vendedor_matriz,
        assinatura_digital=ASSINATURA_FAKE,
        motivo_reprovacao="  Cor do logo errada  ",
    )

    assert result.motivo_reprovacao == "Cor do logo errada"
    assert prova.status == StatusProvaEnum.REPROVADA_PELO_VENDEDOR

    kwargs = mock_log_audit.call_args.kwargs
    assert kwargs["detalhes"]["motivo_reprovacao"] == "Cor do logo errada"


@pytest.mark.asyncio
async def test_executar_reprovacao_sem_motivo_levanta_value_error(
    mock_db, mock_log_audit, vendedor_matriz
):
    """Teste 5 — Reprovacao sem motivo levanta ValueError (RF-007)."""
    prova = make_prova(status=StatusProvaEnum.RETIRADA_PELO_VENDEDOR)

    with pytest.raises(ValueError, match="Motivo da reprovacao e obrigatorio"):
        await executar_transicao(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
            usuario=vendedor_matriz,
            assinatura_digital=ASSINATURA_FAKE,
            motivo_reprovacao=None,
        )

    # Nenhum efeito colateral: prova inalterada, db nao tocado, audit nao chamado
    assert prova.status == StatusProvaEnum.RETIRADA_PELO_VENDEDOR
    mock_db.add.assert_not_called()
    mock_log_audit.assert_not_called()


@pytest.mark.asyncio
async def test_executar_reprovacao_motivo_whitespace_levanta_value_error(
    mock_db, mock_log_audit, vendedor_matriz
):
    """Teste 6 — Reprovacao com motivo so-espacos equivale a sem motivo."""
    prova = make_prova(status=StatusProvaEnum.RETIRADA_PELO_VENDEDOR)

    with pytest.raises(ValueError, match="Motivo da reprovacao e obrigatorio"):
        await executar_transicao(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
            usuario=vendedor_matriz,
            assinatura_digital=ASSINATURA_FAKE,
            motivo_reprovacao="   \t\n  ",
        )


@pytest.mark.asyncio
async def test_executar_transicao_ilegal_levanta_transicao_invalida(
    mock_db, mock_log_audit, vendedor_matriz
):
    """Teste 7 — Destino fora da matriz levanta TransicaoInvalidaError."""
    prova = make_prova(status=StatusProvaEnum.CRIADA)

    with pytest.raises(TransicaoInvalidaError):
        await executar_transicao(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
            usuario=vendedor_matriz,
            assinatura_digital=ASSINATURA_FAKE,
        )

    assert prova.status == StatusProvaEnum.CRIADA
    mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_executar_ator_errado_levanta_ator_nao_autorizado(
    mock_db, mock_log_audit
):
    """Teste 8 — Ator sem permissao levanta AtorNaoAutorizadoError."""
    motorista = make_user(setor=SetorEnum.MOTORISTA, localizacao=None)
    prova = make_prova(status=StatusProvaEnum.CRIADA)

    with pytest.raises(AtorNaoAutorizadoError):
        await executar_transicao(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
            usuario=motorista,
            assinatura_digital=ASSINATURA_FAKE,
        )

    mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_executar_assinatura_vazia_levanta_value_error(
    mock_db, mock_log_audit, vendedor_matriz
):
    """Teste 9 — Assinatura vazia levanta ValueError (RN-003)."""
    prova = make_prova(status=StatusProvaEnum.CRIADA)

    with pytest.raises(ValueError, match="Assinatura digital e obrigatoria"):
        await executar_transicao(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
            usuario=vendedor_matriz,
            assinatura_digital=b"",
        )

    mock_db.add.assert_not_called()
    mock_log_audit.assert_not_called()


@pytest.mark.asyncio
async def test_executar_aprovada_para_de_volta_3studio_matriz_ok(
    mock_db, mock_log_audit, vendedor_matriz
):
    """Teste 10 — Vendedor MATRIZ pode devolver prova aprovada (rota PADRAO)."""
    prova = make_prova(
        status=StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        rota=RotaEnum.PADRAO,
    )

    await executar_transicao(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.DE_VOLTA_3STUDIO,
        usuario=vendedor_matriz,
        assinatura_digital=ASSINATURA_FAKE,
    )

    assert prova.status == StatusProvaEnum.DE_VOLTA_3STUDIO
    assert prova.rota == RotaEnum.PADRAO  # inalterada


@pytest.mark.asyncio
async def test_executar_aprovada_para_de_volta_3studio_filial_rejeita(
    mock_db, mock_log_audit, vendedor_filial
):
    """Teste 11 — Vendedor FILIAL tentando devolver a 3Studio → AtorNaoAutorizado (RF-009)."""
    prova = make_prova(
        status=StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        rota=RotaEnum.DIRETA,
    )

    with pytest.raises(AtorNaoAutorizadoError, match="vendedor MATRIZ"):
        await executar_transicao(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.DE_VOLTA_3STUDIO,
            usuario=vendedor_filial,
            assinatura_digital=ASSINATURA_FAKE,
        )

    assert prova.status == StatusProvaEnum.APROVADA_PELO_VENDEDOR
    mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_executar_aprovada_para_encaminhada_filial_ok(
    mock_db, mock_log_audit, vendedor_filial
):
    """Teste 12 — Vendedor FILIAL pode encaminhar diretamente a clicheria."""
    prova = make_prova(
        status=StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        rota=RotaEnum.DIRETA,
    )

    await executar_transicao(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.ENCAMINHADA_A_CLICHERIA,
        usuario=vendedor_filial,
        assinatura_digital=ASSINATURA_FAKE,
    )

    assert prova.status == StatusProvaEnum.ENCAMINHADA_A_CLICHERIA


@pytest.mark.asyncio
async def test_executar_aprovada_para_encaminhada_matriz_rejeita(
    mock_db, mock_log_audit, vendedor_matriz
):
    """Teste 13 — Vendedor MATRIZ tentando encaminhar direto → AtorNaoAutorizado."""
    prova = make_prova(
        status=StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        rota=RotaEnum.PADRAO,
    )

    with pytest.raises(AtorNaoAutorizadoError, match="vendedor FILIAL"):
        await executar_transicao(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.ENCAMINHADA_A_CLICHERIA,
            usuario=vendedor_matriz,
            assinatura_digital=ASSINATURA_FAKE,
        )


@pytest.mark.asyncio
async def test_executar_com_motorista_para_enviada_happy(mock_db, mock_log_audit):
    """Teste 14 — Motorista confirma transporte COM_MOTORISTA -> ENVIADA."""
    motorista = make_user(setor=SetorEnum.MOTORISTA, localizacao=None)
    prova = make_prova(
        status=StatusProvaEnum.COM_MOTORISTA,
        rota=RotaEnum.PADRAO,
    )

    await executar_transicao(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.ENVIADA_PARA_CLICHERIA,
        usuario=motorista,
        assinatura_digital=ASSINATURA_FAKE,
    )

    assert prova.status == StatusProvaEnum.ENVIADA_PARA_CLICHERIA


@pytest.mark.asyncio
async def test_executar_enviada_para_recebida_clicheria_happy(
    mock_db, mock_log_audit
):
    """Teste 15 — Clicheria recebe pelo fluxo padrao (ENVIADA -> RECEBIDA)."""
    clicheria = make_user(setor=SetorEnum.CLICHERIA, localizacao=None)
    prova = make_prova(
        status=StatusProvaEnum.ENVIADA_PARA_CLICHERIA,
        rota=RotaEnum.PADRAO,
    )

    await executar_transicao(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
        usuario=clicheria,
        assinatura_digital=ASSINATURA_FAKE,
    )

    assert prova.status == StatusProvaEnum.RECEBIDA_PELA_CLICHERIA


@pytest.mark.asyncio
async def test_executar_encaminhada_para_recebida_clicheria_happy(
    mock_db, mock_log_audit
):
    """Teste 16 — Clicheria recebe pelo fluxo direto."""
    clicheria = make_user(setor=SetorEnum.CLICHERIA, localizacao=None)
    prova = make_prova(
        status=StatusProvaEnum.ENCAMINHADA_A_CLICHERIA,
        rota=RotaEnum.DIRETA,
    )

    await executar_transicao(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
        usuario=clicheria,
        assinatura_digital=ASSINATURA_FAKE,
    )

    assert prova.status == StatusProvaEnum.RECEBIDA_PELA_CLICHERIA


@pytest.mark.asyncio
async def test_executar_de_volta_para_com_motorista_studio_happy(
    mock_db, mock_log_audit
):
    """Teste 17 — 3Studio confirma envio ao motorista (DE_VOLTA -> COM_MOTORISTA)."""
    studio = make_user(setor=SetorEnum.STUDIO, localizacao=None)
    prova = make_prova(
        status=StatusProvaEnum.DE_VOLTA_3STUDIO,
        rota=RotaEnum.PADRAO,
    )

    await executar_transicao(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.COM_MOTORISTA,
        usuario=studio,
        assinatura_digital=ASSINATURA_FAKE,
    )

    assert prova.status == StatusProvaEnum.COM_MOTORISTA


@pytest.mark.asyncio
async def test_executar_reinicio_ciclo_reprovada_para_criada_incrementa(
    mock_db, mock_log_audit
):
    """Teste 18 — Reinicio de ciclo por STUDIO: incrementa ciclo_atual,
    PRESERVA rota (RN-006 v4.0 + RF-009 v4.0 — ADR-123 / AUD-W2V4-001) e
    emite audit com acao='reiniciar_ciclo' (gancho C14).

    Nao exposto pelo endpoint do Lote A — mas a state_machine suporta para
    que o endpoint admin dedicado do C14 (Lote C) possa chamar sem refactor.

    Pre-correcao (Wave 3 v3.0): zerava rota -> bug AUD-W2V4-001 disparava
    o trigger trg_provas_rota_imutavel para qualquer prova com rota
    nao-NULL. Pos-correcao Wave 2 v4.0 (commit do fix): preserva rota_antes.
    """
    studio = make_user(setor=SetorEnum.STUDIO, localizacao=None)
    prova = make_prova(
        status=StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
        rota=RotaEnum.PADRAO,  # Ciclo anterior havia sido aprovado
        ciclo_atual=1,
    )

    result = await executar_transicao(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.CRIADA,
        usuario=studio,
        assinatura_digital=ASSINATURA_FAKE,
    )

    assert prova.ciclo_atual == 2
    # AUD-W2V4-001 fix: rota PRESERVADA (era None pre-correcao).
    assert prova.rota == RotaEnum.PADRAO
    assert prova.status == StatusProvaEnum.CRIADA
    assert result.ciclo == 2
    assert result.rota_no_momento == RotaEnum.PADRAO

    # Audit log usa acao especifica "reiniciar_ciclo"
    kwargs = mock_log_audit.call_args.kwargs
    assert kwargs["acao"] == "reiniciar_ciclo"
    assert kwargs["detalhes"]["ciclo"] == 2
    assert kwargs["detalhes"]["rota_antes"] == "PADRAO"
    # AUD-W2V4-007: contrato mudou — rota_depois reflete preservacao.
    assert kwargs["detalhes"]["rota_depois"] == "PADRAO"


@pytest.mark.asyncio
async def test_executar_reinicio_ciclo_v4_preserva_rota_matriz(
    mock_db, mock_log_audit
):
    """Teste 18b — AUD-W2V4-001 cobertura v4.0 (mock_db): reinicio de
    ciclo de prova v4.0 com rota=MATRIZ deve PRESERVAR rota.

    Validacao integrada (banco real + trigger ativo) em
    test_imutabilidade_rota.py (AUD-W2V4-T01).
    """
    studio = make_user(setor=SetorEnum.STUDIO, localizacao=None)
    prova = make_prova(
        status=StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
        rota=RotaEnum.MATRIZ,  # Prova v4.0 com rota imutavel persistida
        ciclo_atual=2,
    )

    result = await executar_transicao(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.CRIADA,
        usuario=studio,
        assinatura_digital=ASSINATURA_FAKE,
    )

    # Rota MATRIZ preservada — sem trigger seria disparado em banco real.
    assert prova.rota == RotaEnum.MATRIZ
    assert result.rota_no_momento == RotaEnum.MATRIZ
    assert prova.ciclo_atual == 3
    assert result.ciclo == 3

    kwargs = mock_log_audit.call_args.kwargs
    assert kwargs["detalhes"]["rota_antes"] == "MATRIZ"
    assert kwargs["detalhes"]["rota_depois"] == "MATRIZ"


@pytest.mark.asyncio
async def test_executar_reinicio_ciclo_legacy_null_mantem_null(
    mock_db, mock_log_audit
):
    """Teste 18c — AUD-W2V4-001: prova legacy v3.0 com rota=NULL no
    reinicio mantem NULL (sem regressao do caminho legacy)."""
    studio = make_user(setor=SetorEnum.STUDIO, localizacao=None)
    prova = make_prova(
        status=StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
        rota=None,  # Prova legada v3.0 sem rota persistida
        ciclo_atual=1,
    )

    result = await executar_transicao(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.CRIADA,
        usuario=studio,
        assinatura_digital=ASSINATURA_FAKE,
    )

    assert prova.rota is None
    assert result.rota_no_momento is None
    assert prova.ciclo_atual == 2

    kwargs = mock_log_audit.call_args.kwargs
    assert kwargs["detalhes"]["rota_antes"] is None
    assert kwargs["detalhes"]["rota_depois"] is None


@pytest.mark.asyncio
async def test_executar_admin_bypassa_setor_em_transicao_valida(
    mock_db, mock_log_audit
):
    """Teste 19 — Admin (is_admin=true) pode executar qualquer transicao
    valida, mesmo sem ser do setor esperado. Mesmo padrao do validar_transicao."""
    admin = make_user(
        setor=SetorEnum.CLICHERIA,  # Setor operacional nao importa
        localizacao=None,
        is_admin=True,
    )
    prova = make_prova(status=StatusProvaEnum.CRIADA)

    await executar_transicao(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        usuario=admin,
        assinatura_digital=ASSINATURA_FAKE,
    )

    assert prova.status == StatusProvaEnum.RETIRADA_PELO_VENDEDOR


@pytest.mark.asyncio
async def test_executar_movimentacao_copia_ciclo_pre_setado(
    mock_db, mock_log_audit, vendedor_matriz
):
    """Teste 20 — Movimentacao captura o ciclo_atual vigente no momento.

    Cenario: prova ja passou por um ciclo de reprovacao (ciclo_atual=2).
    Ao retirar de novo, a movimentacao registra ciclo=2.
    """
    prova = make_prova(status=StatusProvaEnum.CRIADA, ciclo_atual=2)

    result = await executar_transicao(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        usuario=vendedor_matriz,
        assinatura_digital=ASSINATURA_FAKE,
    )

    assert result.ciclo == 2
    assert prova.ciclo_atual == 2  # nao mexe fora do reinicio


# ─── Testes extras (cancelamento + cobertura 100%) ───────────────────────


@pytest.mark.asyncio
async def test_executar_cancelamento_sem_motivo_levanta_value_error(
    mock_db, mock_log_audit
):
    """Cancelamento sem motivo → ValueError. Gancho para C13: o endpoint
    do Lote A rejeita CANCELADA antes de chegar aqui, mas a state_machine
    enforça a regra RN-005."""
    studio = make_user(setor=SetorEnum.STUDIO, localizacao=None)
    prova = make_prova(status=StatusProvaEnum.COM_MOTORISTA, rota=RotaEnum.PADRAO)

    with pytest.raises(ValueError, match="Motivo do cancelamento e obrigatorio"):
        await executar_transicao(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.CANCELADA,
            usuario=studio,
            assinatura_digital=ASSINATURA_FAKE,
            motivo_cancelamento=None,
        )

    mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_executar_cancelamento_com_motivo_persiste_no_prova(
    mock_db, mock_log_audit
):
    """Cancelamento com motivo grava em prova.motivo_cancelamento + audit."""
    studio = make_user(setor=SetorEnum.STUDIO, localizacao=None)
    prova = make_prova(status=StatusProvaEnum.COM_MOTORISTA, rota=RotaEnum.PADRAO)

    await executar_transicao(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.CANCELADA,
        usuario=studio,
        assinatura_digital=ASSINATURA_FAKE,
        motivo_cancelamento="  Cliente cancelou o pedido  ",
    )

    assert prova.status == StatusProvaEnum.CANCELADA
    assert prova.motivo_cancelamento == "Cliente cancelou o pedido"

    kwargs = mock_log_audit.call_args.kwargs
    assert kwargs["detalhes"]["motivo_cancelamento"] == "Cliente cancelou o pedido"


@pytest.mark.asyncio
async def test_executar_aprovacao_admin_sem_localizacao_levanta_rota_indeterminavel(
    mock_db, mock_log_audit
):
    """Admin STUDIO tentando aprovar uma prova direto → RotaIndeterminavelError
    porque nao ha localizacao para derivar a rota. Admin pode bypassar setor
    (validar_transicao) mas nao pode bypassar RN-007 (rota derivada da
    localizacao do vendedor).
    """
    admin_studio = make_user(
        setor=SetorEnum.STUDIO, localizacao=None, is_admin=True
    )
    prova = make_prova(status=StatusProvaEnum.RETIRADA_PELO_VENDEDOR)

    with pytest.raises(RotaIndeterminavelError):
        await executar_transicao(
            mock_db,
            prova=prova,
            status_novo=StatusProvaEnum.APROVADA_PELO_VENDEDOR,
            usuario=admin_studio,
            assinatura_digital=ASSINATURA_FAKE,
        )

    mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_executar_request_passado_para_audit_log(
    mock_db, mock_log_audit, vendedor_matriz
):
    """O parametro `request` e forwarded para log_audit (para popular
    IP/user-agent via X-Forwarded-For — ADR F04 da Sessao 22)."""
    prova = make_prova(status=StatusProvaEnum.CRIADA)
    fake_request = object()  # qualquer objeto — log_audit esta patchado

    await executar_transicao(
        mock_db,
        prova=prova,
        status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        usuario=vendedor_matriz,
        assinatura_digital=ASSINATURA_FAKE,
        request=fake_request,
    )

    kwargs = mock_log_audit.call_args.kwargs
    assert kwargs["request"] is fake_request


# ─── consistencia estrutural da tabela ─────────────────────────────────


def test_toda_transicao_tem_atores_definidos():
    """Toda aresta em TRANSICOES (exceto cancelamento) deve ter ator definido."""
    for origem, destinos in TRANSICOES.items():
        for destino in destinos:
            if destino == StatusProvaEnum.CANCELADA:
                continue  # tratado separadamente
            assert (origem, destino) in ATORES_POR_TRANSICAO, (
                f"Transicao {origem.value} -> {destino.value} sem ator definido"
            )


def test_todos_estados_aparecem_em_transicoes():
    """Todo StatusProvaEnum deve ter entrada em TRANSICOES (mesmo que vazio)."""
    for st in StatusProvaEnum:
        assert st in TRANSICOES, f"Estado {st.value} faltando em TRANSICOES"
