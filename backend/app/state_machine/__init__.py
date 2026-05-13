"""Maquina de Estados — facade publica com roteamento v3.0 vs v4.0.

Wave 3 v4.0 / Componente 11.

Esta eh a porta de entrada UNICA para qualquer codigo do projeto que
precise transitar uma prova ou consultar transicoes validas. NUNCA
importar diretamente de `app.services.state_machine` (v3.0 legacy) ou
de `app.state_machine.v4.*` — sempre via este modulo.

Roteamento (Decisao M-2 + M-2b(a) do Gate 1):
  - prova.rota IS NULL                              -> maquina v3.0 (legacy)
  - prova.rota IN {PADRAO, DIRETA}                  -> maquina v3.0 (legacy preenchido)
  - prova.rota IN {MATRIZ, LAM_MATRIZ, FILIAL, LAM_FILIAL} -> maquina v4.0

API publica:
  - executar_transicao(db, *, prova, status_novo, usuario, ...): roteador.
  - transicoes_validas(prova, usuario): conjunto de destinos validos
    para o usuario, considerando ator + rota. Espelha o calculo do
    `_computar_transicoes_permitidas` antigo, mas agora ramifica por rota.
  - pode_cancelar(status): True se status nao eh terminal.
  - TransicaoInvalidaError, AtorNaoAutorizadoError, RotaIndeterminavelError:
    excecoes de dominio (reusadas do v3.0 para preservar contratos HTTP
    em `provas.py`).

Wave 7 / Componente 21 vai fazer o backfill de `rota` para as provas
legacy e, eventualmente, remover a maquina v3.0. Ate la, ambas coexistem.
"""
from __future__ import annotations

from app.db.models import ProvaDigital, RotaEnum, StatusProvaEnum, Usuario
from app.services.state_machine import (
    AtorNaoAutorizadoError,
    RotaIndeterminavelError,
    TransicaoInvalidaError,
)
from app.services.state_machine import executar_transicao as _executar_v3
from app.state_machine.v4.machine import executar_transicao_v4
from app.state_machine.v4.machine import pode_cancelar as _pode_cancelar_v4
from app.state_machine.v4.machine import transicoes_validas_v4
from app.state_machine.v4.rules import ROTAS_V4, TERMINAIS_V4


__all__ = [
    "executar_transicao",
    "transicoes_validas",
    "pode_cancelar",
    "is_rota_v4",
    "TransicaoInvalidaError",
    "AtorNaoAutorizadoError",
    "RotaIndeterminavelError",
]


def is_rota_v4(rota: RotaEnum | None) -> bool:
    """True se a rota dispatcha para a maquina v4.0.

    Provas legacy (rota=NULL ou rota IN {PADRAO, DIRETA}) usam a maquina
    v3.0. Apenas as 4 rotas v4.0 (MATRIZ, LAM_MATRIZ, FILIAL, LAM_FILIAL)
    sao roteadas para a maquina nova.
    """
    return rota is not None and rota in ROTAS_V4


async def executar_transicao(
    db,
    *,
    prova: ProvaDigital,
    status_novo: StatusProvaEnum,
    usuario: Usuario,
    assinatura_digital: bytes,
    motivo_reprovacao: str | None = None,
    motivo_cancelamento: str | None = None,
    request=None,
):
    """Executa transicao de estado end-to-end com roteamento v3.0/v4.0.

    Dispatcha automaticamente conforme `prova.rota`:
      - rota IS NULL ou legacy (PADRAO/DIRETA) -> v3.0
      - rota v4.0 (MATRIZ/LAM_MATRIZ/FILIAL/LAM_FILIAL) -> v4.0

    Contrato HTTP do caller (handler em provas.py) eh identico ao v3.0:
    as mesmas excecoes sao levantadas (TransicaoInvalidaError,
    AtorNaoAutorizadoError, RotaIndeterminavelError, ValueError),
    permitindo que o mapeamento HTTP (ADR-084) continue valendo sem
    modificacao.
    """
    if is_rota_v4(prova.rota):
        return await executar_transicao_v4(
            db,
            prova=prova,
            status_novo=status_novo,
            usuario=usuario,
            assinatura_digital=assinatura_digital,
            motivo_reprovacao=motivo_reprovacao,
            motivo_cancelamento=motivo_cancelamento,
            request=request,
        )
    return await _executar_v3(
        db,
        prova=prova,
        status_novo=status_novo,
        usuario=usuario,
        assinatura_digital=assinatura_digital,
        motivo_reprovacao=motivo_reprovacao,
        motivo_cancelamento=motivo_cancelamento,
        request=request,
    )


def transicoes_validas(
    prova: ProvaDigital, usuario: Usuario
) -> frozenset[StatusProvaEnum]:
    """Conjunto de destinos validos a partir do estado atual da prova.

    Filtra por (ator do usuario, rota da prova). Resultado eh subset
    valido — toda transicao retornada passa em `executar_transicao` sem
    erro de ator/rota.

    Para a maquina v4.0, consulta `TRANSITION_RULES` direto. Para a
    v3.0 legacy, retorna conjunto vazio — o caller (scan endpoint)
    continua usando `_computar_transicoes_permitidas` do `provas.py`
    que tem a logica antiga (RF-009 por localizacao). Esse helper sera
    estendido para chamar este facade quando a prova for v4.0.

    Cancelamento (admin-only, transversal) e Reinicio de Ciclo
    (admin-only, REPROVADA -> CRIADA) NAO estao incluidos — sao
    expostos por endpoints dedicados (`POST /{id}/cancelar`,
    `POST /{id}/reiniciar-ciclo`).
    """
    if not is_rota_v4(prova.rota):
        # Maquina v3.0 — caller (provas.py) cuida via funcao legada.
        return frozenset()
    assert prova.rota is not None  # narrowing — is_rota_v4 ja verifica
    return transicoes_validas_v4(prova.rota, prova.status, usuario)


def pode_cancelar(status_atual: StatusProvaEnum) -> bool:
    """RN-005: cancelamento permitido em qualquer estado ativo.

    Estados terminais (RECEBIDA_PELA_CLICHERIA, CANCELADA) nao podem
    ser cancelados. Os outros 15 valores do enum (10 v3.0 + 5 v4.0
    ativos) sao todos candidatos a cancelamento — admin-only via
    endpoint dedicado `POST /{id}/cancelar`.

    Compativel com a maquina v3.0 + v4.0 simultaneamente (TERMINAIS_V4
    espelha exatamente os 2 terminais v3.0).
    """
    return _pode_cancelar_v4(status_atual)


# Re-export TERMINAIS_V4 para introspeccao por callers externos (ex.:
# `_computar_transicoes_permitidas` no scan precisa filtrar terminais).
__all__.append("TERMINAIS_V4")
