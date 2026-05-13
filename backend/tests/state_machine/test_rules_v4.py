"""Testes da matriz canonica TRANSITION_RULES (rules.py).

Wave 3 v4.0 / Componente 11.

Foco: validar que a tabela bate LITERALMENTE com a Matriz §5 dos
Requisitos v4.0 — qualquer drift entre tabela e especificacao eh
detectado aqui.

Para cada uma das 4 rotas v4.0, asserts explicitos sobre os destinos
validos por (rota, estado_atual). Total: 24 entradas, ~80 asserts.
"""
from __future__ import annotations

import pytest

from app.db.models import RotaEnum, SetorEnum, StatusProvaEnum
from app.state_machine.v4.rules import (
    ROTAS_V4,
    TERMINAIS_V4,
    TRANSITION_RULES,
    Transition,
    estados_da_rota,
)


# ───────────────────────────────────────────────────────────────────────────
# Sanidade do shape da tabela
# ───────────────────────────────────────────────────────────────────────────


def test_total_de_entradas_eh_24():
    """Conferencia de contagem (Gate 1 §4.7): 5+10+3+6=24."""
    assert len(TRANSITION_RULES) == 24


def test_total_por_rota():
    contagem: dict[RotaEnum, int] = {r: 0 for r in ROTAS_V4}
    for (rota, _), _ in TRANSITION_RULES.items():
        contagem[rota] += 1
    assert contagem[RotaEnum.MATRIZ] == 5
    assert contagem[RotaEnum.LAM_MATRIZ] == 10
    assert contagem[RotaEnum.FILIAL] == 3
    assert contagem[RotaEnum.LAM_FILIAL] == 6


def test_todas_chaves_usam_rota_v4():
    """Nenhuma chave da tabela referencia rota legacy (PADRAO, DIRETA)."""
    for (rota, _) in TRANSITION_RULES.keys():
        assert rota in ROTAS_V4, f"{rota} eh legacy v3.0 — nao deveria estar"


def test_terminais_nao_aparecem_como_chave():
    """RECEBIDA_PELA_CLICHERIA e CANCELADA nao tem transicoes saindo."""
    for (_, status) in TRANSITION_RULES.keys():
        assert status not in TERMINAIS_V4


def test_transitions_sao_frozenset():
    for transicoes in TRANSITION_RULES.values():
        assert isinstance(transicoes, frozenset)
        assert all(isinstance(t, Transition) for t in transicoes)


def test_rotas_v4_eh_frozenset_imutavel():
    assert isinstance(ROTAS_V4, frozenset)
    assert ROTAS_V4 == frozenset({
        RotaEnum.MATRIZ,
        RotaEnum.LAM_MATRIZ,
        RotaEnum.FILIAL,
        RotaEnum.LAM_FILIAL,
    })


def test_terminais_v4_eh_frozenset_imutavel():
    assert isinstance(TERMINAIS_V4, frozenset)
    assert TERMINAIS_V4 == frozenset({
        StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
        StatusProvaEnum.CANCELADA,
    })


# ───────────────────────────────────────────────────────────────────────────
# ROTA MATRIZ (§5.2) — 5 transicoes nao-iniciais
# ───────────────────────────────────────────────────────────────────────────


def _destinos(rota: RotaEnum, origem: StatusProvaEnum) -> set[StatusProvaEnum]:
    return {t.destino for t in TRANSITION_RULES.get((rota, origem), frozenset())}


def _ator_de(rota: RotaEnum, origem: StatusProvaEnum, destino: StatusProvaEnum) -> SetorEnum:
    for t in TRANSITION_RULES[(rota, origem)]:
        if t.destino == destino:
            return t.ator
    raise AssertionError(f"Transicao ({rota.value}, {origem.value} -> {destino.value}) nao encontrada")


def test_matriz_criada_vai_para_retirada_via_vendedor():
    assert _destinos(RotaEnum.MATRIZ, StatusProvaEnum.CRIADA) == {
        StatusProvaEnum.RETIRADA_PELO_VENDEDOR
    }
    assert _ator_de(
        RotaEnum.MATRIZ,
        StatusProvaEnum.CRIADA,
        StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
    ) == SetorEnum.VENDEDOR


def test_matriz_retirada_vai_para_aprovada_ou_reprovada_via_vendedor():
    destinos = _destinos(RotaEnum.MATRIZ, StatusProvaEnum.RETIRADA_PELO_VENDEDOR)
    assert destinos == {
        StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
    }
    for destino in destinos:
        assert _ator_de(RotaEnum.MATRIZ, StatusProvaEnum.RETIRADA_PELO_VENDEDOR, destino) == SetorEnum.VENDEDOR


def test_matriz_aprovada_vai_para_de_volta_via_studio():
    assert _destinos(RotaEnum.MATRIZ, StatusProvaEnum.APROVADA_PELO_VENDEDOR) == {
        StatusProvaEnum.DE_VOLTA_3STUDIO
    }
    assert _ator_de(
        RotaEnum.MATRIZ,
        StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        StatusProvaEnum.DE_VOLTA_3STUDIO,
    ) == SetorEnum.STUDIO


def test_matriz_de_volta_vai_para_motorista_entrega_via_motorista():
    """Decisao M-2b(a): motorista entrega final eh COM_MOTORISTA_ENTREGA_FINAL (NOVO v4.0), nao COM_MOTORISTA (legacy)."""
    assert _destinos(RotaEnum.MATRIZ, StatusProvaEnum.DE_VOLTA_3STUDIO) == {
        StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL
    }
    assert _ator_de(
        RotaEnum.MATRIZ,
        StatusProvaEnum.DE_VOLTA_3STUDIO,
        StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL,
    ) == SetorEnum.MOTORISTA


def test_matriz_motorista_entrega_vai_para_recebida_via_clicheria():
    assert _destinos(
        RotaEnum.MATRIZ, StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL
    ) == {StatusProvaEnum.RECEBIDA_PELA_CLICHERIA}
    assert _ator_de(
        RotaEnum.MATRIZ,
        StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL,
        StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
    ) == SetorEnum.CLICHERIA


def test_matriz_nao_passa_por_estados_de_laminacao():
    """Rota MATRIZ nao tem etapa de laminacao — assert defensivo."""
    estados_matriz = estados_da_rota(RotaEnum.MATRIZ)
    estados_laminacao = {
        StatusProvaEnum.ENCAMINHADA_PARA_LAMINACAO,
        StatusProvaEnum.LAMINACAO_CONCLUIDA,
        StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO,
        StatusProvaEnum.COM_MOTORISTA_VOLTA_LAMINACAO,
        StatusProvaEnum.DE_VOLTA_3STUDIO_POS_LAMINACAO,
    }
    assert estados_matriz.isdisjoint(estados_laminacao)


# ───────────────────────────────────────────────────────────────────────────
# ROTA LAM_MATRIZ (§5.3) — 10 transicoes nao-iniciais
# ───────────────────────────────────────────────────────────────────────────


def test_lam_matriz_criada_vai_para_encaminhada_laminacao_via_studio():
    assert _destinos(RotaEnum.LAM_MATRIZ, StatusProvaEnum.CRIADA) == {
        StatusProvaEnum.ENCAMINHADA_PARA_LAMINACAO
    }
    assert _ator_de(
        RotaEnum.LAM_MATRIZ,
        StatusProvaEnum.CRIADA,
        StatusProvaEnum.ENCAMINHADA_PARA_LAMINACAO,
    ) == SetorEnum.STUDIO


def test_lam_matriz_encaminhada_laminacao_vai_para_motorista_ida():
    assert _destinos(
        RotaEnum.LAM_MATRIZ, StatusProvaEnum.ENCAMINHADA_PARA_LAMINACAO
    ) == {StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO}
    assert _ator_de(
        RotaEnum.LAM_MATRIZ,
        StatusProvaEnum.ENCAMINHADA_PARA_LAMINACAO,
        StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO,
    ) == SetorEnum.MOTORISTA


def test_lam_matriz_motorista_ida_vai_para_laminacao_concluida_via_clicheria():
    """US-007 v4.0: Clicheria confirma termino da laminacao."""
    assert _destinos(
        RotaEnum.LAM_MATRIZ, StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO
    ) == {StatusProvaEnum.LAMINACAO_CONCLUIDA}
    assert _ator_de(
        RotaEnum.LAM_MATRIZ,
        StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO,
        StatusProvaEnum.LAMINACAO_CONCLUIDA,
    ) == SetorEnum.CLICHERIA


def test_lam_matriz_laminacao_concluida_vai_para_motorista_volta():
    """Apenas Lam. Matriz tem motorista de volta. Lam. Filial vai direto para Vendedor."""
    assert _destinos(
        RotaEnum.LAM_MATRIZ, StatusProvaEnum.LAMINACAO_CONCLUIDA
    ) == {StatusProvaEnum.COM_MOTORISTA_VOLTA_LAMINACAO}
    assert _ator_de(
        RotaEnum.LAM_MATRIZ,
        StatusProvaEnum.LAMINACAO_CONCLUIDA,
        StatusProvaEnum.COM_MOTORISTA_VOLTA_LAMINACAO,
    ) == SetorEnum.MOTORISTA


def test_lam_matriz_motorista_volta_vai_para_pos_laminacao_via_studio():
    assert _destinos(
        RotaEnum.LAM_MATRIZ, StatusProvaEnum.COM_MOTORISTA_VOLTA_LAMINACAO
    ) == {StatusProvaEnum.DE_VOLTA_3STUDIO_POS_LAMINACAO}
    assert _ator_de(
        RotaEnum.LAM_MATRIZ,
        StatusProvaEnum.COM_MOTORISTA_VOLTA_LAMINACAO,
        StatusProvaEnum.DE_VOLTA_3STUDIO_POS_LAMINACAO,
    ) == SetorEnum.STUDIO


def test_lam_matriz_pos_laminacao_vai_para_retirada_via_vendedor():
    """Estado #06 DE_VOLTA_3STUDIO_POS_LAMINACAO eh distinto de #11 DE_VOLTA_3STUDIO."""
    assert _destinos(
        RotaEnum.LAM_MATRIZ, StatusProvaEnum.DE_VOLTA_3STUDIO_POS_LAMINACAO
    ) == {StatusProvaEnum.RETIRADA_PELO_VENDEDOR}
    assert _ator_de(
        RotaEnum.LAM_MATRIZ,
        StatusProvaEnum.DE_VOLTA_3STUDIO_POS_LAMINACAO,
        StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
    ) == SetorEnum.VENDEDOR


def test_lam_matriz_retirada_aprovacao_reprovacao_iguais_matriz():
    destinos = _destinos(RotaEnum.LAM_MATRIZ, StatusProvaEnum.RETIRADA_PELO_VENDEDOR)
    assert destinos == {
        StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
    }


def test_lam_matriz_aprovada_vai_para_de_volta():
    """Estado #11 DE_VOLTA_3STUDIO — distinto de #06 POS_LAMINACAO."""
    assert _destinos(RotaEnum.LAM_MATRIZ, StatusProvaEnum.APROVADA_PELO_VENDEDOR) == {
        StatusProvaEnum.DE_VOLTA_3STUDIO
    }


def test_lam_matriz_de_volta_vai_para_motorista_entrega():
    assert _destinos(RotaEnum.LAM_MATRIZ, StatusProvaEnum.DE_VOLTA_3STUDIO) == {
        StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL
    }


def test_lam_matriz_motorista_entrega_vai_para_recebida():
    assert _destinos(
        RotaEnum.LAM_MATRIZ, StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL
    ) == {StatusProvaEnum.RECEBIDA_PELA_CLICHERIA}


# ───────────────────────────────────────────────────────────────────────────
# ROTA FILIAL (§5.4) — 3 transicoes nao-iniciais (Decisao M-1: ator=VENDEDOR)
# ───────────────────────────────────────────────────────────────────────────


def test_filial_criada_vai_para_encaminhada_vendedor_via_vendedor():
    """Decisao M-1 Opcao A: texto literal §5.4 - ator eh VENDEDOR."""
    assert _destinos(RotaEnum.FILIAL, StatusProvaEnum.CRIADA) == {
        StatusProvaEnum.ENCAMINHADA_PARA_O_VENDEDOR
    }
    assert _ator_de(
        RotaEnum.FILIAL,
        StatusProvaEnum.CRIADA,
        StatusProvaEnum.ENCAMINHADA_PARA_O_VENDEDOR,
    ) == SetorEnum.VENDEDOR


def test_filial_encaminhada_vai_para_aprovada_ou_reprovada_via_vendedor():
    destinos = _destinos(
        RotaEnum.FILIAL, StatusProvaEnum.ENCAMINHADA_PARA_O_VENDEDOR
    )
    assert destinos == {
        StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
    }
    for d in destinos:
        assert _ator_de(
            RotaEnum.FILIAL, StatusProvaEnum.ENCAMINHADA_PARA_O_VENDEDOR, d
        ) == SetorEnum.VENDEDOR


def test_filial_aprovada_vai_para_recebida_direto_via_clicheria():
    """Sem motorista — vendedor e clicheria na mesma Filial."""
    assert _destinos(RotaEnum.FILIAL, StatusProvaEnum.APROVADA_PELO_VENDEDOR) == {
        StatusProvaEnum.RECEBIDA_PELA_CLICHERIA
    }
    assert _ator_de(
        RotaEnum.FILIAL,
        StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
    ) == SetorEnum.CLICHERIA


def test_filial_nao_passa_por_motorista_nem_de_volta():
    """Rota Filial nao tem motorista, DE_VOLTA_3STUDIO, ou estados de laminacao."""
    estados_filial = estados_da_rota(RotaEnum.FILIAL)
    proibidos = {
        StatusProvaEnum.DE_VOLTA_3STUDIO,
        StatusProvaEnum.COM_MOTORISTA,
        StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL,
        StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO,
        StatusProvaEnum.COM_MOTORISTA_VOLTA_LAMINACAO,
        StatusProvaEnum.ENCAMINHADA_PARA_LAMINACAO,
        StatusProvaEnum.LAMINACAO_CONCLUIDA,
        StatusProvaEnum.DE_VOLTA_3STUDIO_POS_LAMINACAO,
        StatusProvaEnum.RETIRADA_PELO_VENDEDOR,  # rota Filial usa ENCAMINHADA, nao RETIRADA
    }
    assert estados_filial.isdisjoint(proibidos)


# ───────────────────────────────────────────────────────────────────────────
# ROTA LAM_FILIAL (§5.5) — 6 transicoes nao-iniciais
# ───────────────────────────────────────────────────────────────────────────


def test_lam_filial_criada_vai_para_encaminhada_laminacao_via_studio():
    assert _destinos(RotaEnum.LAM_FILIAL, StatusProvaEnum.CRIADA) == {
        StatusProvaEnum.ENCAMINHADA_PARA_LAMINACAO
    }
    assert _ator_de(
        RotaEnum.LAM_FILIAL,
        StatusProvaEnum.CRIADA,
        StatusProvaEnum.ENCAMINHADA_PARA_LAMINACAO,
    ) == SetorEnum.STUDIO


def test_lam_filial_encaminhada_laminacao_motorista_clicheria():
    """Mesma sequencia de laminacao da Lam. Matriz."""
    assert _destinos(
        RotaEnum.LAM_FILIAL, StatusProvaEnum.ENCAMINHADA_PARA_LAMINACAO
    ) == {StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO}
    assert _destinos(
        RotaEnum.LAM_FILIAL, StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO
    ) == {StatusProvaEnum.LAMINACAO_CONCLUIDA}


def test_lam_filial_laminacao_concluida_vai_para_vendedor_direto():
    """Decisao §5.5: SEM motorista de volta. Vendedor pega direto da Clicheria."""
    assert _destinos(RotaEnum.LAM_FILIAL, StatusProvaEnum.LAMINACAO_CONCLUIDA) == {
        StatusProvaEnum.ENCAMINHADA_PARA_O_VENDEDOR
    }
    assert _ator_de(
        RotaEnum.LAM_FILIAL,
        StatusProvaEnum.LAMINACAO_CONCLUIDA,
        StatusProvaEnum.ENCAMINHADA_PARA_O_VENDEDOR,
    ) == SetorEnum.VENDEDOR


def test_lam_filial_encaminhada_vendedor_aprovacao_reprovacao():
    destinos = _destinos(
        RotaEnum.LAM_FILIAL, StatusProvaEnum.ENCAMINHADA_PARA_O_VENDEDOR
    )
    assert destinos == {
        StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
    }


def test_lam_filial_aprovada_vai_para_recebida_direto():
    """Sem DE_VOLTA_3STUDIO nem motorista entrega — clicheria recebe direto."""
    assert _destinos(
        RotaEnum.LAM_FILIAL, StatusProvaEnum.APROVADA_PELO_VENDEDOR
    ) == {StatusProvaEnum.RECEBIDA_PELA_CLICHERIA}


def test_lam_filial_nao_tem_motorista_volta_nem_entrega():
    """Lam. Filial so tem 1 contexto de motorista (ida_laminacao)."""
    estados_lam_filial = estados_da_rota(RotaEnum.LAM_FILIAL)
    proibidos = {
        StatusProvaEnum.COM_MOTORISTA,
        StatusProvaEnum.COM_MOTORISTA_VOLTA_LAMINACAO,
        StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL,
        StatusProvaEnum.DE_VOLTA_3STUDIO,
        StatusProvaEnum.DE_VOLTA_3STUDIO_POS_LAMINACAO,
        StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
    }
    assert estados_lam_filial.isdisjoint(proibidos)


# ───────────────────────────────────────────────────────────────────────────
# Reprovacao transversal — disponivel em RETIRADA e ENCAMINHADA_PARA_O_VENDEDOR
# ───────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "rota,origem",
    [
        (RotaEnum.MATRIZ, StatusProvaEnum.RETIRADA_PELO_VENDEDOR),
        (RotaEnum.LAM_MATRIZ, StatusProvaEnum.RETIRADA_PELO_VENDEDOR),
        (RotaEnum.FILIAL, StatusProvaEnum.ENCAMINHADA_PARA_O_VENDEDOR),
        (RotaEnum.LAM_FILIAL, StatusProvaEnum.ENCAMINHADA_PARA_O_VENDEDOR),
    ],
)
def test_reprovar_disponivel_em_estado_de_recebimento_vendedor(
    rota: RotaEnum, origem: StatusProvaEnum
):
    """§5.6: reprovacao disponivel em RETIRADA (Matriz/Lam.Matriz) ou ENCAMINHADA_VENDEDOR (Filial/Lam.Filial)."""
    transicoes = TRANSITION_RULES[(rota, origem)]
    matches = [t for t in transicoes if t.destino == StatusProvaEnum.REPROVADA_PELO_VENDEDOR]
    assert len(matches) == 1
    t = matches[0]
    assert t.ator == SetorEnum.VENDEDOR
    assert t.motivo_obrigatorio is True


@pytest.mark.parametrize(
    "rota,origem",
    [
        # CRIADA nao tem rota para reprovar (ainda nao chegou ao vendedor)
        (RotaEnum.MATRIZ, StatusProvaEnum.CRIADA),
        (RotaEnum.FILIAL, StatusProvaEnum.CRIADA),
        (RotaEnum.LAM_MATRIZ, StatusProvaEnum.CRIADA),
        (RotaEnum.LAM_FILIAL, StatusProvaEnum.CRIADA),
        # APROVADA tampouco reprova de novo
        (RotaEnum.MATRIZ, StatusProvaEnum.APROVADA_PELO_VENDEDOR),
        (RotaEnum.FILIAL, StatusProvaEnum.APROVADA_PELO_VENDEDOR),
    ],
)
def test_reprovar_indisponivel_fora_de_recebimento_vendedor(
    rota: RotaEnum, origem: StatusProvaEnum
):
    transicoes = TRANSITION_RULES.get((rota, origem), frozenset())
    destinos = {t.destino for t in transicoes}
    assert StatusProvaEnum.REPROVADA_PELO_VENDEDOR not in destinos


# ───────────────────────────────────────────────────────────────────────────
# estados_da_rota helper
# ───────────────────────────────────────────────────────────────────────────


def test_estados_da_rota_matriz_eh_correto():
    estados = estados_da_rota(RotaEnum.MATRIZ)
    assert estados == frozenset({
        StatusProvaEnum.CRIADA,
        StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        StatusProvaEnum.DE_VOLTA_3STUDIO,
        StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL,
        StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
    })


def test_estados_da_rota_lam_matriz_eh_completo():
    estados = estados_da_rota(RotaEnum.LAM_MATRIZ)
    assert StatusProvaEnum.ENCAMINHADA_PARA_LAMINACAO in estados
    assert StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO in estados
    assert StatusProvaEnum.LAMINACAO_CONCLUIDA in estados
    assert StatusProvaEnum.COM_MOTORISTA_VOLTA_LAMINACAO in estados
    assert StatusProvaEnum.DE_VOLTA_3STUDIO_POS_LAMINACAO in estados
    assert StatusProvaEnum.RETIRADA_PELO_VENDEDOR in estados
    assert StatusProvaEnum.APROVADA_PELO_VENDEDOR in estados
    assert StatusProvaEnum.DE_VOLTA_3STUDIO in estados
    assert StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL in estados
    assert StatusProvaEnum.RECEBIDA_PELA_CLICHERIA in estados
    assert StatusProvaEnum.CRIADA in estados
    # REPROVADA_PELO_VENDEDOR eh transversal — NAO eh listado
    assert StatusProvaEnum.REPROVADA_PELO_VENDEDOR not in estados


def test_estados_da_rota_filial_eh_minimo():
    estados = estados_da_rota(RotaEnum.FILIAL)
    assert estados == frozenset({
        StatusProvaEnum.CRIADA,
        StatusProvaEnum.ENCAMINHADA_PARA_O_VENDEDOR,
        StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
    })


def test_estados_da_rota_legacy_retorna_vazio():
    """Rotas legacy (PADRAO, DIRETA) NAO sao suportadas pela v4.0."""
    assert estados_da_rota(RotaEnum.PADRAO) == frozenset()
    assert estados_da_rota(RotaEnum.DIRETA) == frozenset()


def test_estados_da_rota_exclui_reprovacao():
    """REPROVADA_PELO_VENDEDOR eh transversal — nao eh listado em nenhuma rota."""
    for rota in ROTAS_V4:
        estados = estados_da_rota(rota)
        assert StatusProvaEnum.REPROVADA_PELO_VENDEDOR not in estados


# ───────────────────────────────────────────────────────────────────────────
# Transition dataclass — imutabilidade + igualdade
# ───────────────────────────────────────────────────────────────────────────


def test_transition_eh_imutavel():
    t = Transition(StatusProvaEnum.CRIADA, SetorEnum.VENDEDOR)
    with pytest.raises(AttributeError):
        t.destino = StatusProvaEnum.CANCELADA  # type: ignore[misc]


def test_transition_eh_hashable():
    t1 = Transition(StatusProvaEnum.CRIADA, SetorEnum.VENDEDOR)
    t2 = Transition(StatusProvaEnum.CRIADA, SetorEnum.VENDEDOR)
    assert hash(t1) == hash(t2)
    assert {t1, t2} == {t1}


def test_transition_motivo_obrigatorio_default_false():
    t = Transition(StatusProvaEnum.CRIADA, SetorEnum.VENDEDOR)
    assert t.motivo_obrigatorio is False
