"""Testes unitarios da maquina de estados (ADR-040).

Cobertura alvo: TRANSICOES, ATORES_POR_TRANSICAO, determinar_rota,
transicao_e_valida, pode_cancelar, atores_permitidos, validar_transicao,
executar_transicao (stub).

Zero dependencia de banco ou HTTP.
"""
import pytest

from app.db.models import LocalizacaoEnum, RotaEnum, SetorEnum, StatusProvaEnum
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


# ─── executar_transicao (stub Wave 3) ───────────────────────────────────


def test_executar_transicao_e_stub():
    with pytest.raises(NotImplementedError, match="Wave 3"):
        executar_transicao()


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
