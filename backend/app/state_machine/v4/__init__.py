"""Maquina de Estados v4.0 — Wave 3 / Componente 11.

Estrutura prescrita pelo DAT v3.0 §4.1:
  rules.py    — tabela imutavel de transicoes (TRANSITION_RULES)
  machine.py  — funcoes puras de validacao + executar_transicao
  contextos.py — derivacao de contexto do motorista (3 contextos)

Esta pasta NAO eh exportada diretamente — o consumo deve ser via
`app.state_machine.<funcao>` (facade publica com roteamento v3.0/v4.0).

Importacoes diretas aqui dentro sao permitidas porque o modulo eh
auto-contido. Externamente, prefira o facade.
"""
from app.state_machine.v4.contextos import (
    ContextoMotorista,
    contexto_motorista,
)
from app.state_machine.v4.machine import (
    executar_transicao_v4,
    pode_cancelar,
    transicoes_validas_v4,
    validar_transicao_v4,
)
from app.state_machine.v4.rules import (
    ROTAS_V4,
    TERMINAIS_V4,
    TRANSITION_RULES,
    Transition,
    estados_da_rota,
)


__all__ = [
    # rules
    "Transition",
    "TRANSITION_RULES",
    "TERMINAIS_V4",
    "ROTAS_V4",
    "estados_da_rota",
    # contextos
    "ContextoMotorista",
    "contexto_motorista",
    # machine
    "validar_transicao_v4",
    "executar_transicao_v4",
    "transicoes_validas_v4",
    "pode_cancelar",
]
