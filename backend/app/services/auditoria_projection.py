"""Projecao de `tipo_evento` derivado para o audit log (Wave 6, ADR-099).

A camada de escrita do audit log (ADR-039, `state_machine.py`,
`api/v1/provas.py`, `api/v1/configuracoes.py`) usa apenas 5 valores crus
de `acao`:

  1. `criar_prova`            — Componente 6, Wave 2
  2. `escanear_prova`         — Componente 10, Wave 3
  3. `transitar_status`       — Componente 11 + Componente 13 (cancelamento!)
  4. `reiniciar_ciclo`        — Componente 14, Wave 3
  5. `atualizar_configuracao` — Componente 9, Wave 2

Mas a interface de Wave 6 (Componente 18) precisa distinguir visualmente
entre sub-eventos dentro de `transitar_status`:

  - Cancelamento    (`acao=transitar_status` + `detalhes_json.para=CANCELADA`)
  - Reprovacao      (`acao=transitar_status` + `detalhes_json.para=REPROVADA_PELO_VENDEDOR`)
  - Transicao comum (`acao=transitar_status` + outro valor de `para`)

A regra de derivacao fica NESTA funcao — nao na query SQL (ficaria poluida
com CASE WHEN + extracao JSONB) e nao no frontend (regra duplicada em 2
linguagens vira drift na hora de adicionar um novo sub-evento). Assim
temos um **unico ponto de verdade**, testavel em isolamento e coberto por
testes unitarios 100% (ver `tests/test_auditoria_projection.py`).

Decisao de design (ADR-099):
  O gap de granularidade da camada de escrita (cancelamento logado como
  `transitar_status`) nao sera corrigido na Wave 3 — regra inviolavel #1
  da Wave 6 proibe modificar waves anteriores. A projecao backend e a
  solucao canonica.

Ver tambem:
  - WAVE6_ANALYSIS.md secao 1.6 (matriz completa)
  - DECISIONS.md ADR-099
  - app/domain/schemas/auditoria.py (`TipoEventoEnum`, `TIPO_EVENTO_LABELS`)
"""
from __future__ import annotations

import logging
from typing import Any

from app.domain.schemas.auditoria import TIPO_EVENTO_LABELS, TipoEventoEnum

logger = logging.getLogger(__name__)


def projetar_tipo_evento(
    acao: str,
    detalhes_json: dict[str, Any] | None,
) -> TipoEventoEnum:
    """Computa `tipo_evento` a partir de `(acao, detalhes_json)`.

    Args:
        acao: Valor cru de `audit_logs.acao`. Deve ser um dos 5 valores
            listados em `ACOES_VALIDAS` (whitelist de produces Waves 2-5).
        detalhes_json: Valor cru de `audit_logs.detalhes_json`. Pode ser
            `None` ou um `dict` JSONB. Apenas relevante quando
            `acao=='transitar_status'`.

    Returns:
        O valor do enum `TipoEventoEnum` correspondente.

    Fallback (acao desconhecida):
        Se `acao` nao bate com nenhum caso conhecido (ex: Wave futura
        introduziu valor novo sem atualizar esta funcao), retornamos
        `TRANSICAO_STATUS` e emitimos `logger.warning`. Escolha
        DELIBERADA: preferimos listar a entrada como "transicao comum"
        a levantar excecao — excecao aqui quebraria a listagem inteira
        da tela de auditoria, transformando um descuido de manutencao em
        um bug P0 visivel para o admin. Ver ADR-099 para o racional.
    """
    if acao == "criar_prova":
        return TipoEventoEnum.CRIACAO_PROVA

    if acao == "escanear_prova":
        return TipoEventoEnum.ESCANEAMENTO

    if acao == "reiniciar_ciclo":
        return TipoEventoEnum.REINICIO_CICLO

    if acao == "atualizar_configuracao":
        return TipoEventoEnum.ALTERACAO_CONFIG

    if acao == "transitar_status":
        # Sub-tipos dependem de detalhes_json.para. Extrai defensivamente —
        # detalhes_json pode ser None (edge case) ou nao ser dict (defesa
        # contra corrupcao historica improvavel mas possivel).
        para: str | None = None
        if isinstance(detalhes_json, dict):
            raw = detalhes_json.get("para")
            if isinstance(raw, str):
                para = raw

        if para == "CANCELADA":
            return TipoEventoEnum.CANCELAMENTO
        if para == "REPROVADA_PELO_VENDEDOR":
            return TipoEventoEnum.REPROVACAO
        return TipoEventoEnum.TRANSICAO_STATUS

    # Fallback — acao desconhecida. Ver docstring para o racional.
    logger.warning(
        "projetar_tipo_evento: acao desconhecida '%s' — fallback TRANSICAO_STATUS. "
        "Atualize auditoria_projection.py (+ testes) se uma nova acao foi adicionada "
        "em Wave posterior.",
        acao,
    )
    return TipoEventoEnum.TRANSICAO_STATUS


def label_tipo_evento(tipo: TipoEventoEnum) -> str:
    """Retorna a label pt-BR de um `TipoEventoEnum`.

    Helper trivial para evitar que call sites importem o dict
    `TIPO_EVENTO_LABELS` diretamente — e mantem o ponto unico de
    reverse-lookup caso a politica de labels mude.

    Args:
        tipo: Valor do enum.

    Returns:
        Label legivel em portugues.
    """
    return TIPO_EVENTO_LABELS[tipo]
