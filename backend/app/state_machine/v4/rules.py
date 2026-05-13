"""Matriz de Transicoes v4.0 — single source of truth (DAT §4.1, §4.2).

Wave 3 v4.0 / Componente 11.

Esta tabela eh a especificacao canonica das transicoes da maquina de
estados v4.0, espelhando LITERALMENTE a Secao 5 do
RequisitosProvasDigitais_v4_0.docx (5.2 a 5.5).

Principio de invariancia (DAT §4.2): as regras NAO vivem no banco —
vivem em codigo versionado. Bug em transicao eh detectado por teste
antes do deploy (cobertura minima 95%). Rollback de transicao quebrada
= revert de commit, nao migracao de dados.

Total: 24 transicoes rota-especificas distribuidas em 4 rotas:
  Matriz       : 5 transicoes (§5.2)
  Lam. Matriz  : 10 transicoes (§5.3)
  Filial       : 3 transicoes (§5.4 — Decisao M-1 Gate 1: ator=Vendedor)
  Lam. Filial  : 6 transicoes (§5.5)

Transversais (NAO rota-especificas):
  - Reprovacao: REPROVAR transition embutida em cada par
    (rota, RETIRADA/ENCAMINHADA_PARA_O_VENDEDOR) — vendedor pode escolher
    APROVAR ou REPROVAR (Decision §5.6 do Requisitos).
  - Reinicio de Ciclo: REPROVADA -> CRIADA, admin-only, ciclo+1, rota
    preservada (RN-006 v4.0, RF-009 v4.0). Tratado fora desta tabela
    (endpoint dedicado `POST /{id}/reiniciar-ciclo`).
  - Cancelamento: qualquer ativo -> CANCELADA, admin-only. Tratado
    fora desta tabela (endpoint dedicado `POST /{id}/cancelar`).

Decisoes Gate 1 do C11:
  - M-1 Opcao A: ator de (FILIAL, CRIADA -> ENCAMINHADA_PARA_O_VENDEDOR)
    eh VENDEDOR. Texto literal do §5.4 prevalece sobre UML 06.3.
    Interpretacao semantica: vendedor assina ao receber a prova.
  - M-2b(a): COM_MOTORISTA legacy v3.0 e COM_MOTORISTA_ENTREGA_FINAL
    v4.0 sao valores DISTINTOS — esta tabela usa apenas o v4.0.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Mapping

from app.db.models import RotaEnum, SetorEnum, StatusProvaEnum


@dataclass(frozen=True)
class Transition:
    """Uma transicao valida na maquina v4.0.

    Attributes:
      destino: Estado destino apos a transicao bem-sucedida.
      ator: Setor autorizado a executar (RN-004 v4.0).
      motivo_obrigatorio: True apenas para REPROVADA_PELO_VENDEDOR (RF-007).
        Cancelamento tambem exige motivo, mas eh transversal — nao
        listado nesta tabela.
    """

    destino: StatusProvaEnum
    ator: SetorEnum
    motivo_obrigatorio: bool = False


# ── Atalhos de legibilidade ────────────────────────────────────────────────
_VENDEDOR = SetorEnum.VENDEDOR
_STUDIO = SetorEnum.STUDIO
_MOTORISTA = SetorEnum.MOTORISTA
_CLICHERIA = SetorEnum.CLICHERIA

_CRIADA = StatusProvaEnum.CRIADA
_RETIRADA = StatusProvaEnum.RETIRADA_PELO_VENDEDOR
_APROVADA = StatusProvaEnum.APROVADA_PELO_VENDEDOR
_REPROVADA = StatusProvaEnum.REPROVADA_PELO_VENDEDOR
_DE_VOLTA = StatusProvaEnum.DE_VOLTA_3STUDIO
_RECEBIDA = StatusProvaEnum.RECEBIDA_PELA_CLICHERIA

# Estados v4.0 (migration 013)
_ENV_VENDEDOR = StatusProvaEnum.ENCAMINHADA_PARA_O_VENDEDOR
_ENV_LAMINACAO = StatusProvaEnum.ENCAMINHADA_PARA_LAMINACAO
_LAMINACAO_OK = StatusProvaEnum.LAMINACAO_CONCLUIDA
_MOT_IDA = StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO
_MOT_VOLTA = StatusProvaEnum.COM_MOTORISTA_VOLTA_LAMINACAO
_MOT_ENTREGA = StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL
_POS_LAMINACAO = StatusProvaEnum.DE_VOLTA_3STUDIO_POS_LAMINACAO

# Reprovacao eh disponivel sempre que o vendedor recebe a prova.
_REPROVAR_VENDEDOR = Transition(_REPROVADA, _VENDEDOR, motivo_obrigatorio=True)


# ── TABELA CANONICA — espelho LITERAL da Secao 5 do Requisitos v4.0 ────────
TRANSITION_RULES: Mapping[
    tuple[RotaEnum, StatusProvaEnum],
    FrozenSet[Transition],
] = {
    # ─── ROTA MATRIZ (§5.2 — 5 transicoes nao-iniciais) ────────────────────
    # 3Studio cria -> Vendedor retira -> Vendedor aprova -> 3Studio devolve
    # -> Motorista entrega -> Clicheria recebe.
    (RotaEnum.MATRIZ, _CRIADA): frozenset({
        Transition(_RETIRADA, _VENDEDOR),
    }),
    (RotaEnum.MATRIZ, _RETIRADA): frozenset({
        Transition(_APROVADA, _VENDEDOR),
        _REPROVAR_VENDEDOR,
    }),
    (RotaEnum.MATRIZ, _APROVADA): frozenset({
        Transition(_DE_VOLTA, _STUDIO),
    }),
    (RotaEnum.MATRIZ, _DE_VOLTA): frozenset({
        Transition(_MOT_ENTREGA, _MOTORISTA),
    }),
    (RotaEnum.MATRIZ, _MOT_ENTREGA): frozenset({
        Transition(_RECEBIDA, _CLICHERIA),
    }),

    # ─── ROTA LAM_MATRIZ (§5.3 — 10 transicoes nao-iniciais) ───────────────
    # 3Studio cria -> 3Studio encaminha para laminacao -> Motorista ida ->
    # Clicheria conclui laminacao -> Motorista volta -> 3Studio recebe
    # laminada -> Vendedor retira -> Vendedor aprova -> 3Studio devolve
    # -> Motorista entrega -> Clicheria recebe.
    (RotaEnum.LAM_MATRIZ, _CRIADA): frozenset({
        Transition(_ENV_LAMINACAO, _STUDIO),
    }),
    (RotaEnum.LAM_MATRIZ, _ENV_LAMINACAO): frozenset({
        Transition(_MOT_IDA, _MOTORISTA),
    }),
    (RotaEnum.LAM_MATRIZ, _MOT_IDA): frozenset({
        Transition(_LAMINACAO_OK, _CLICHERIA),
    }),
    (RotaEnum.LAM_MATRIZ, _LAMINACAO_OK): frozenset({
        Transition(_MOT_VOLTA, _MOTORISTA),
    }),
    (RotaEnum.LAM_MATRIZ, _MOT_VOLTA): frozenset({
        Transition(_POS_LAMINACAO, _STUDIO),
    }),
    (RotaEnum.LAM_MATRIZ, _POS_LAMINACAO): frozenset({
        Transition(_RETIRADA, _VENDEDOR),
    }),
    (RotaEnum.LAM_MATRIZ, _RETIRADA): frozenset({
        Transition(_APROVADA, _VENDEDOR),
        _REPROVAR_VENDEDOR,
    }),
    (RotaEnum.LAM_MATRIZ, _APROVADA): frozenset({
        Transition(_DE_VOLTA, _STUDIO),
    }),
    (RotaEnum.LAM_MATRIZ, _DE_VOLTA): frozenset({
        Transition(_MOT_ENTREGA, _MOTORISTA),
    }),
    (RotaEnum.LAM_MATRIZ, _MOT_ENTREGA): frozenset({
        Transition(_RECEBIDA, _CLICHERIA),
    }),

    # ─── ROTA FILIAL (§5.4 — 3 transicoes nao-iniciais) ────────────────────
    # 3Studio cria -> Vendedor recebe (ator=VENDEDOR por Decisao M-1 do
    # Gate 1 — texto literal §5.4 prevalece) -> Vendedor aprova ->
    # Clicheria recebe (sem Motorista; vendedor e clicheria ambos na Filial).
    (RotaEnum.FILIAL, _CRIADA): frozenset({
        Transition(_ENV_VENDEDOR, _VENDEDOR),
    }),
    (RotaEnum.FILIAL, _ENV_VENDEDOR): frozenset({
        Transition(_APROVADA, _VENDEDOR),
        _REPROVAR_VENDEDOR,
    }),
    (RotaEnum.FILIAL, _APROVADA): frozenset({
        Transition(_RECEBIDA, _CLICHERIA),
    }),

    # ─── ROTA LAM_FILIAL (§5.5 — 6 transicoes nao-iniciais) ────────────────
    # 3Studio cria -> 3Studio encaminha para laminacao -> Motorista ida
    # -> Clicheria conclui laminacao -> Vendedor recebe -> Vendedor aprova
    # -> Clicheria recebe. Sem Motorista no retorno (vendedor e clicheria
    # ambos na Filial — §5.5 literal).
    (RotaEnum.LAM_FILIAL, _CRIADA): frozenset({
        Transition(_ENV_LAMINACAO, _STUDIO),
    }),
    (RotaEnum.LAM_FILIAL, _ENV_LAMINACAO): frozenset({
        Transition(_MOT_IDA, _MOTORISTA),
    }),
    (RotaEnum.LAM_FILIAL, _MOT_IDA): frozenset({
        Transition(_LAMINACAO_OK, _CLICHERIA),
    }),
    (RotaEnum.LAM_FILIAL, _LAMINACAO_OK): frozenset({
        Transition(_ENV_VENDEDOR, _VENDEDOR),
    }),
    (RotaEnum.LAM_FILIAL, _ENV_VENDEDOR): frozenset({
        Transition(_APROVADA, _VENDEDOR),
        _REPROVAR_VENDEDOR,
    }),
    (RotaEnum.LAM_FILIAL, _APROVADA): frozenset({
        Transition(_RECEBIDA, _CLICHERIA),
    }),
}


# Estados terminais — sem transicoes subsequentes (em qualquer rota).
TERMINAIS_V4: FrozenSet[StatusProvaEnum] = frozenset({
    StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
    StatusProvaEnum.CANCELADA,
})


# Rotas suportadas pela maquina v4.0. PADRAO e DIRETA (legacy v3.0)
# NAO estao aqui — provas com essas rotas roteiam para a maquina v3.0
# legacy. Ver `app.state_machine.is_rota_v4`.
ROTAS_V4: FrozenSet[RotaEnum] = frozenset({
    RotaEnum.MATRIZ,
    RotaEnum.LAM_MATRIZ,
    RotaEnum.FILIAL,
    RotaEnum.LAM_FILIAL,
})


def estados_da_rota(rota: RotaEnum) -> FrozenSet[StatusProvaEnum]:
    """Conjunto de estados visitados pela rota (origem ou destino).

    Util para o contrato com C12 (timeline) — ordena rota inteira na
    UI dinamicamente baseado nesse conjunto.

    Inclui CRIADA (origem inicial) e RECEBIDA_PELA_CLICHERIA (terminal
    de sucesso); NAO inclui REPROVADA_PELO_VENDEDOR nem CANCELADA, pois
    sao transversais — qualquer estado nao-terminal pode levar a um
    desses dois.
    """
    if rota not in ROTAS_V4:
        return frozenset()
    estados: set[StatusProvaEnum] = set()
    for (r, origem), transicoes in TRANSITION_RULES.items():
        if r != rota:
            continue
        estados.add(origem)
        for t in transicoes:
            if t.destino == StatusProvaEnum.REPROVADA_PELO_VENDEDOR:
                # Reprovacao eh transversal — nao faz parte da sequencia
                # "linear" da rota visualizada no C12.
                continue
            estados.add(t.destino)
    return frozenset(estados)
