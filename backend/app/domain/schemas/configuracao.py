"""Schemas Pydantic v2 para o dominio de Configuracoes do Sistema (Componente 09).

Implementa RF-021 + RN-008 + RN-011 com validacao whitelisted por chave.

Regras de negocio (ADR-043, ADR-044, ADR-045):
  - Apenas as chaves listadas em `EDITABLE_KEYS` sao editaveis via API.
  - Chaves novas exigem uma migration Alembic — NAO criar via PATCH.
  - Validacao de `valor` e dispatchada por chave via `VALIDATORS` dict.
  - Cada mudanca gera audit_log com valor_anterior e valor_novo para trilha
    completa (ADR-044).
"""
from datetime import datetime
from typing import Any, Callable
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ─── Whitelist de chaves editaveis (ADR-043) ──────────────────────────────

CHAVE_TEMPO_ATRASO = "tempo_atraso_horas_uteis"
CHAVE_TEMPLATE_ETIQUETA = "template_etiqueta"

EDITABLE_KEYS: frozenset[str] = frozenset({CHAVE_TEMPO_ATRASO, CHAVE_TEMPLATE_ETIQUETA})


# ─── Limites do tempo de atraso (RN-008) ──────────────────────────────────

TEMPO_ATRASO_MIN_HORAS = 1
TEMPO_ATRASO_MAX_HORAS = 168  # 7 dias


# ─── Formatos de etiqueta permitidos (RN-011) ─────────────────────────────

FORMATOS_ETIQUETA_VALIDOS = frozenset({"A4", "80mm_thermal"})


# ─── Nomes de template permitidos ──────────────────────────────────────────
# Whitelist fechada. Quando Waves 4+ introduzirem um template novo, bastara
# adicionar aqui + (eventualmente) um branch no etiqueta_service se o layout
# nao for derivavel apenas dos flags formato/logo_enabled/mostrar_data_criacao.
TEMPLATE_NOMES_VALIDOS = frozenset({"padrao"})


# ─── Excecao dedicada para erros de validacao de configuracao ─────────────


class ConfiguracaoValidationError(ValueError):
    """Raise quando o valor enviado falha na validacao especifica da chave."""


# ─── Validadores por chave ────────────────────────────────────────────────


def validar_tempo_atraso(valor: Any) -> int:
    """Valida o valor de `tempo_atraso_horas_uteis`.

    Deve ser inteiro (nao bool) entre 1 e 168 horas.

    Raises:
        ConfiguracaoValidationError: qualquer violacao de tipo ou range.
    """
    # IMPORTANTE: bool e subclasse de int em Python — checar bool primeiro.
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ConfiguracaoValidationError(
            "Campo 'valor' deve ser um numero inteiro"
        )
    if valor < TEMPO_ATRASO_MIN_HORAS or valor > TEMPO_ATRASO_MAX_HORAS:
        raise ConfiguracaoValidationError(
            f"Tempo de atraso deve estar entre {TEMPO_ATRASO_MIN_HORAS} "
            f"e {TEMPO_ATRASO_MAX_HORAS} horas"
        )
    return valor


def validar_template_etiqueta(valor: Any) -> dict[str, Any]:
    """Valida o valor de `template_etiqueta`.

    Deve ser um objeto JSON com exatamente 4 campos:
      - nome: string nao-vazia (read-only via frontend — SQL direto para editar)
      - formato: "A4" ou "80mm_thermal"
      - logo_enabled: booleano
      - mostrar_data_criacao: booleano

    Campos extras no body sao descartados (retorna apenas os 4 validados).

    Raises:
        ConfiguracaoValidationError: qualquer violacao.
    """
    if not isinstance(valor, dict):
        raise ConfiguracaoValidationError(
            "Campo 'valor' deve ser um objeto JSON"
        )

    # nome: deve estar na whitelist fechada de templates conhecidos.
    nome = valor.get("nome")
    if not isinstance(nome, str):
        raise ConfiguracaoValidationError(
            "Campo 'nome' deve ser uma string"
        )
    nome_normalizado = nome.strip()
    if nome_normalizado not in TEMPLATE_NOMES_VALIDOS:
        raise ConfiguracaoValidationError(
            f"Campo 'nome' deve ser um de: {sorted(TEMPLATE_NOMES_VALIDOS)}"
        )

    # formato: literal
    formato = valor.get("formato")
    if formato not in FORMATOS_ETIQUETA_VALIDOS:
        raise ConfiguracaoValidationError(
            f"Campo 'formato' deve ser um de: {sorted(FORMATOS_ETIQUETA_VALIDOS)}"
        )

    # logo_enabled: bool estrito
    logo_enabled = valor.get("logo_enabled")
    if not isinstance(logo_enabled, bool):
        raise ConfiguracaoValidationError(
            "Campo 'logo_enabled' deve ser booleano"
        )

    # mostrar_data_criacao: bool estrito
    mostrar_data = valor.get("mostrar_data_criacao")
    if not isinstance(mostrar_data, bool):
        raise ConfiguracaoValidationError(
            "Campo 'mostrar_data_criacao' deve ser booleano"
        )

    # Retorna apenas os 4 campos conhecidos (descarta extras).
    return {
        "nome": nome_normalizado,
        "formato": formato,
        "logo_enabled": logo_enabled,
        "mostrar_data_criacao": mostrar_data,
    }


# ─── Dispatch table (ADR-045) ─────────────────────────────────────────────
# Quando aparecer uma 3a chave, continua-se adicionando aqui. Quando chegar
# a 5+ chaves, considerar extrair para um modulo `app/services/config_validators.py`
# ou similar.

VALIDATORS: dict[str, Callable[[Any], Any]] = {
    CHAVE_TEMPO_ATRASO: validar_tempo_atraso,
    CHAVE_TEMPLATE_ETIQUETA: validar_template_etiqueta,
}


def validar_valor_por_chave(chave: str, valor: Any) -> Any:
    """Dispatcha a validacao para o validator especifico da chave.

    Args:
        chave: Chave do `configuracoes_sistema`. Deve estar em `EDITABLE_KEYS`.
        valor: Valor bruto recebido do body do PATCH.

    Returns:
        O valor normalizado (pode diferir do original — strings sao strip()ed,
        dicts tem campos extras removidos).

    Raises:
        ConfiguracaoValidationError: validacao falhou.
        KeyError: chave nao tem validator registrado (bug de programacao).
    """
    validator = VALIDATORS[chave]
    return validator(valor)


# ─── Schemas de response ──────────────────────────────────────────────────


class ConfiguracaoResponse(BaseModel):
    """Representacao publica de uma linha de `configuracoes_sistema`."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chave: str
    valor: Any  # JSONB — pode ser int, str, bool, dict, list
    descricao: str | None
    updated_by: UUID | None
    updated_at: datetime


class ConfiguracaoListResponse(BaseModel):
    """Lista de configuracoes retornada pelo GET /api/v1/configuracoes/."""

    items: list[ConfiguracaoResponse]


# ─── Schema de request ────────────────────────────────────────────────────


class ConfiguracaoUpdateRequest(BaseModel):
    """Body do PATCH /api/v1/configuracoes/{chave}.

    `valor` e `Any` porque cada chave tem um tipo diferente — a validacao
    real acontece via `validar_valor_por_chave` no endpoint, baseado na
    chave da URL.

    `descricao` e opcional: quando None ou ausente, o endpoint mantem a
    descricao atual (nao limpa).
    """

    valor: Any = Field(..., description="Novo valor da configuracao")
    descricao: str | None = Field(
        None, max_length=2000, description="Nova descricao (opcional)"
    )
