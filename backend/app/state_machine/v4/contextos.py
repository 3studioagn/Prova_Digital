"""Detecao de contexto do Motorista — 3 contextos distintos (US-006 v4.0).

Wave 3 v4.0 / Componente 11. Decisao M-5 do Gate 1: contexto eh derivado
do `status_novo` em runtime (NAO persistido em coluna separada de
`movimentacoes`). O `audit_log.detalhes_json` registra o contexto extra
para investigacoes futuras.

Mapeamento:
  COM_MOTORISTA_IDA_LAMINACAO    -> "ida_laminacao"     (Lam. Matriz, Lam. Filial)
  COM_MOTORISTA_VOLTA_LAMINACAO  -> "volta_laminacao"   (Lam. Matriz apenas)
  COM_MOTORISTA_ENTREGA_FINAL    -> "entrega_final"     (Matriz, Lam. Matriz)
  COM_MOTORISTA (legacy v3.0)    -> "entrega_final"     (compat — provas v3.0
                                                          so tinham este contexto)

A Lam. Filial NAO tem motorista no retorno (vendedor e clicheria ambos
na Filial — §5.5 do Requisitos). So aparece um contexto: ida_laminacao.

Consumido por:
  - `executar_transicao_v4` no audit_log.detalhes_json["contexto_motorista"]
  - C12 (Timeline) via `contrato-c12.md` para renderizar badge contextual
"""
from __future__ import annotations

from typing import Literal

from app.db.models import StatusProvaEnum


ContextoMotorista = Literal["ida_laminacao", "volta_laminacao", "entrega_final"]
"""Tres contextos distintos do Motorista (US-006 v4.0)."""


def contexto_motorista(status: StatusProvaEnum) -> ContextoMotorista | None:
    """Deriva o contexto do motorista a partir do `status_novo` da transicao.

    Retorna None se o status nao representa "prova com motorista".
    Retorna "entrega_final" tanto para COM_MOTORISTA (legacy v3.0) quanto
    para COM_MOTORISTA_ENTREGA_FINAL (v4.0) — sao operacionalmente
    equivalentes (Decisao M-2b(a) do Gate 1: valores distintos no enum,
    semantica unificada na UX/timeline).

    Casos cobertos:
      - 3 estados v4.0 explicitos: cada um mapeia para 1 contexto
      - 1 estado legacy (COM_MOTORISTA): mapeia para "entrega_final"
      - Qualquer outro status: None
    """
    if status == StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO:
        return "ida_laminacao"
    if status == StatusProvaEnum.COM_MOTORISTA_VOLTA_LAMINACAO:
        return "volta_laminacao"
    if status == StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL:
        return "entrega_final"
    if status == StatusProvaEnum.COM_MOTORISTA:
        # Legacy v3.0 — 1 unico contexto operacionalmente equivalente
        # ao COM_MOTORISTA_ENTREGA_FINAL da v4.0. C12 trata os dois como
        # entrega final na timeline visual.
        return "entrega_final"
    return None
