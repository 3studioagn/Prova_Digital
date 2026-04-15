"""Testes unitarios da funcao pura `projetar_tipo_evento` (Wave 6, ADR-099).

Cobre a matriz completa da secao 1.6 do WAVE6_ANALYSIS.md:

  - Cada valor de `acao` mapeia para o `tipo_evento` correto.
  - `transitar_status` + `detalhes_json.para` decide entre CANCELAMENTO,
    REPROVACAO e TRANSICAO_STATUS (gap 1.6 resolvido via projecao).
  - Edge cases: `detalhes_json=None`, dict vazio, `para` nao-string, `para`
    com valor futuro desconhecido.
  - Fallback: `acao` desconhecida cai em TRANSICAO_STATUS + emite warning
    (nao raise — preferimos listar a entrada a quebrar a tela).
  - Cobertura cruzada: toda `TipoEventoEnum` tem uma label em
    `TIPO_EVENTO_LABELS` (dual-check).

Meta de cobertura: 100% em `auditoria_projection.py`.
"""
from __future__ import annotations

import logging

import pytest

from app.domain.schemas.auditoria import TIPO_EVENTO_LABELS, TipoEventoEnum
from app.services.auditoria_projection import (
    label_tipo_evento,
    projetar_tipo_evento,
)

# =============================================================================
# Matriz principal — 1 teste explicito por linha da tabela 1.6
# =============================================================================


def test_projecao_criar_prova():
    """`criar_prova` sempre mapeia para CRIACAO_PROVA, com ou sem
    `detalhes_json`."""
    assert (
        projetar_tipo_evento("criar_prova", None)
        == TipoEventoEnum.CRIACAO_PROVA
    )
    assert (
        projetar_tipo_evento(
            "criar_prova",
            {
                "cliente": "Claudio",
                "nro_requerimento": "000236",
                "vendedor_nome": "Mario Souza",
            },
        )
        == TipoEventoEnum.CRIACAO_PROVA
    )


def test_projecao_escanear_prova():
    """`escanear_prova` mapeia para ESCANEAMENTO."""
    assert (
        projetar_tipo_evento("escanear_prova", None)
        == TipoEventoEnum.ESCANEAMENTO
    )
    assert (
        projetar_tipo_evento(
            "escanear_prova",
            {
                "nro_requerimento": "123856",
                "status_atual": "RETIRADA_PELO_VENDEDOR",
                "transicoes_permitidas": ["REPROVADA_PELO_VENDEDOR"],
            },
        )
        == TipoEventoEnum.ESCANEAMENTO
    )


def test_projecao_transitar_status_generico():
    """`transitar_status` para um status comum (nao-CANCELADA,
    nao-REPROVADA) vira TRANSICAO_STATUS."""
    assert (
        projetar_tipo_evento(
            "transitar_status",
            {
                "de": "CRIADA",
                "para": "RETIRADA_PELO_VENDEDOR",
                "ciclo": 1,
                "rota_antes": None,
                "rota_depois": None,
            },
        )
        == TipoEventoEnum.TRANSICAO_STATUS
    )


def test_projecao_cancelamento_gap_1_6():
    """Gap 1.6 resolvido: cancelamento via C13 e logado como
    `transitar_status` com `detalhes.para='CANCELADA'`. A projecao separa
    visualmente sem tocar na camada de escrita.

    Shape real em producao (confirmado no Bloco 6.0 — 1 linha existente).
    """
    assert (
        projetar_tipo_evento(
            "transitar_status",
            {
                "de": "APROVADA_PELO_VENDEDOR",
                "para": "CANCELADA",
                "motivo_cancelamento": "cliente cancelou pedido",
                "ciclo": 1,
                "rota_antes": "PADRAO",
                "rota_depois": "PADRAO",
            },
        )
        == TipoEventoEnum.CANCELAMENTO
    )


def test_projecao_reprovacao():
    """`transitar_status` + `detalhes.para='REPROVADA_PELO_VENDEDOR'` vira
    REPROVACAO."""
    assert (
        projetar_tipo_evento(
            "transitar_status",
            {
                "de": "RETIRADA_PELO_VENDEDOR",
                "para": "REPROVADA_PELO_VENDEDOR",
                "ciclo": 1,
                "rota_antes": "PADRAO",
                "rota_depois": "PADRAO",
            },
        )
        == TipoEventoEnum.REPROVACAO
    )


def test_projecao_reiniciar_ciclo():
    """`reiniciar_ciclo` e logado pelo state_machine com `acao` propria
    (linha 374) — projecao direta para REINICIO_CICLO."""
    assert (
        projetar_tipo_evento(
            "reiniciar_ciclo",
            {
                "de": "REPROVADA_PELO_VENDEDOR",
                "para": "CRIADA",
                "ciclo": 2,
                "rota_antes": "PADRAO",
                "rota_depois": None,
            },
        )
        == TipoEventoEnum.REINICIO_CICLO
    )


def test_projecao_atualizar_config():
    """`atualizar_configuracao` vira ALTERACAO_CONFIG. Shape real em
    producao: `chave`, `valor_anterior`, `valor_novo`, `descricao_anterior`,
    `descricao_nova`."""
    assert (
        projetar_tipo_evento(
            "atualizar_configuracao",
            {
                "chave": "tempo_atraso_horas_uteis",
                "valor_anterior": 48,
                "valor_novo": 72,
                "descricao_anterior": "Tempo antigo",
                "descricao_nova": "Tempo ajustado",
            },
        )
        == TipoEventoEnum.ALTERACAO_CONFIG
    )


# =============================================================================
# Edge cases — detalhes_json malformado / ausente
# =============================================================================


def test_projecao_detalhes_json_none_em_transitar_status():
    """`detalhes_json=None` com `acao='transitar_status'` nao deve crashar
    — fallback para TRANSICAO_STATUS generica."""
    assert (
        projetar_tipo_evento("transitar_status", None)
        == TipoEventoEnum.TRANSICAO_STATUS
    )


def test_projecao_detalhes_json_vazio_em_transitar_status():
    """`detalhes_json={}` (sem chave `para`) vira TRANSICAO_STATUS."""
    assert (
        projetar_tipo_evento("transitar_status", {})
        == TipoEventoEnum.TRANSICAO_STATUS
    )


def test_projecao_para_nao_e_string():
    """Se `detalhes_json.para` existe mas nao e string (improvavel em
    producao, mas defensivo), cai em TRANSICAO_STATUS sem crashar."""
    assert (
        projetar_tipo_evento("transitar_status", {"para": 42})
        == TipoEventoEnum.TRANSICAO_STATUS
    )
    assert (
        projetar_tipo_evento("transitar_status", {"para": None})
        == TipoEventoEnum.TRANSICAO_STATUS
    )
    assert (
        projetar_tipo_evento("transitar_status", {"para": ["CANCELADA"]})
        == TipoEventoEnum.TRANSICAO_STATUS
    )


def test_projecao_para_com_valor_desconhecido():
    """Se `para` e string mas nao e um status conhecido (ex: futuro enum),
    vira TRANSICAO_STATUS generica — nao eh CANCELAMENTO nem REPROVACAO."""
    assert (
        projetar_tipo_evento(
            "transitar_status", {"para": "NOVO_STATUS_FUTURO"}
        )
        == TipoEventoEnum.TRANSICAO_STATUS
    )


def test_projecao_criar_prova_com_seed_test():
    """Shape historico de `criar_prova` tem apenas `cliente` +
    `nro_requerimento` + `seed_test` (5 linhas legadas em producao).
    Projecao deve funcionar igual — CRIACAO_PROVA."""
    assert (
        projetar_tipo_evento(
            "criar_prova",
            {
                "cliente": "Cliente Seed",
                "nro_requerimento": "SEED-001",
                "seed_test": True,
            },
        )
        == TipoEventoEnum.CRIACAO_PROVA
    )


# =============================================================================
# Fallback — acao desconhecida
# =============================================================================


def test_projecao_acao_desconhecida_fallback(caplog: pytest.LogCaptureFixture):
    """`acao` fora da whitelist vira TRANSICAO_STATUS e emite warning.
    Nao raise — preferimos listar a entrada a quebrar a tela inteira."""
    with caplog.at_level(logging.WARNING, logger="app.services.auditoria_projection"):
        resultado = projetar_tipo_evento("acao_que_nao_existe", None)

    assert resultado == TipoEventoEnum.TRANSICAO_STATUS
    assert any(
        "acao_que_nao_existe" in record.getMessage()
        for record in caplog.records
    )
    # Garante que o warning aponta para o arquivo a ser atualizado
    assert any(
        "auditoria_projection.py" in record.getMessage()
        for record in caplog.records
    )


def test_projecao_acao_string_vazia_fallback(
    caplog: pytest.LogCaptureFixture,
):
    """String vazia tambem cai no fallback (nao eh um dos 5 valores)."""
    with caplog.at_level(logging.WARNING, logger="app.services.auditoria_projection"):
        resultado = projetar_tipo_evento("", None)
    assert resultado == TipoEventoEnum.TRANSICAO_STATUS
    # Warning foi emitido
    assert len(caplog.records) >= 1


def test_projecao_acao_com_case_diferente_nao_bate():
    """Matching e case-sensitive — `Criar_Prova` NAO bate com
    `criar_prova`. Se algum dia o projeto trocar para case-insensitive,
    este teste pega o regresso."""
    resultado = projetar_tipo_evento("Criar_Prova", None)
    assert resultado == TipoEventoEnum.TRANSICAO_STATUS


# =============================================================================
# Labels pt-BR — dual-check de cobertura
# =============================================================================


@pytest.mark.parametrize("tipo", list(TipoEventoEnum))
def test_label_tipo_evento_cobre_todos_os_enums(tipo: TipoEventoEnum):
    """Garante que cada valor de `TipoEventoEnum` tem uma label pt-BR
    associada. Se alguem adicionar um enum novo sem a label, este teste
    captura no CI."""
    label = label_tipo_evento(tipo)
    assert isinstance(label, str)
    assert len(label) > 0
    assert label == TIPO_EVENTO_LABELS[tipo]


def test_tipo_evento_labels_dict_e_exaustivo():
    """Dual-check: o dict `TIPO_EVENTO_LABELS` tem exatamente uma entrada
    por valor do enum. Sem sobras, sem faltas — garante sincronia."""
    enum_values = set(TipoEventoEnum)
    label_keys = set(TIPO_EVENTO_LABELS.keys())
    assert enum_values == label_keys, (
        f"Desync entre TipoEventoEnum e TIPO_EVENTO_LABELS. "
        f"No enum: {enum_values - label_keys}. No dict: {label_keys - enum_values}."
    )


# =============================================================================
# Matriz parametrizada — consolidacao
# =============================================================================


@pytest.mark.parametrize(
    "acao,detalhes,esperado",
    [
        ("criar_prova", None, TipoEventoEnum.CRIACAO_PROVA),
        ("escanear_prova", None, TipoEventoEnum.ESCANEAMENTO),
        (
            "transitar_status",
            {"para": "RETIRADA_PELO_VENDEDOR"},
            TipoEventoEnum.TRANSICAO_STATUS,
        ),
        (
            "transitar_status",
            {"para": "APROVADA_PELO_VENDEDOR"},
            TipoEventoEnum.TRANSICAO_STATUS,
        ),
        (
            "transitar_status",
            {"para": "COM_MOTORISTA"},
            TipoEventoEnum.TRANSICAO_STATUS,
        ),
        (
            "transitar_status",
            {"para": "CANCELADA"},
            TipoEventoEnum.CANCELAMENTO,
        ),
        (
            "transitar_status",
            {"para": "REPROVADA_PELO_VENDEDOR"},
            TipoEventoEnum.REPROVACAO,
        ),
        ("reiniciar_ciclo", None, TipoEventoEnum.REINICIO_CICLO),
        ("atualizar_configuracao", None, TipoEventoEnum.ALTERACAO_CONFIG),
    ],
)
def test_projecao_matriz_parametrizada(
    acao: str,
    detalhes: dict | None,
    esperado: TipoEventoEnum,
):
    """Versao parametrizada da matriz 1.6 para consolidacao e deteccao de
    regresso em um unico teste explicito."""
    assert projetar_tipo_evento(acao, detalhes) == esperado
