"""Schemas Pydantic v2 para Interface de Log de Auditoria (Wave 6, Componente 18).

Implementa RNF-005 (log imutavel, acesso restrito ao perfil 3Studio) e o
contrato do endpoint GET /api/v1/auditoria/ + GET /api/v1/auditoria/{id}.

A tabela `audit_logs` ja existe desde a Wave 0 (migration 001) e recebe
INSERTs desde a Wave 2 via `audit_service.log_audit()` (ADR-039). Esta Wave
entrega APENAS a camada de LEITURA — zero modificacao na camada de escrita,
zero modificacao no schema, zero migration Alembic, zero nova policy RLS.

Decisoes-chave (ADR-099 — Projecao de `tipo_evento` para audit log):

  1. `TipoEventoEnum` e um campo DERIVADO da tupla `(acao, detalhes_json)`.
     A regra de projecao vive em `app/services/auditoria_projection.py` e
     resolve o gap 1.6 do WAVE6_ANALYSIS.md: cancelamento (C13) e logado
     como `acao="transitar_status"` com `detalhes_json.para="CANCELADA"` em
     vez de ter `acao` propria — a interface precisa separar visualmente
     sem tocar na camada de escrita (regra inviolavel #1, Wave 6).

  2. Filtros: `data_inicio`, `data_fim`, `usuario_id`, `nro_requerimento`,
     `acao` (whitelist de 5 valores), `tipo_evento` (enum de 7 valores),
     `cursor` opaco base64, `limit` 1-100.

  3. Paginacao: keyset pagination por `(created_at DESC, id DESC)` via
     cursor base64. Validado empiricamente no Bloco 6.0 — `idx_audit_created_at`
     + PK `audit_logs_pkey` cobrem a query sem Seq Scan (Execution Time
     < 2 ms para 50 linhas).

  4. `acao` e `tipo_evento` sao MUTUAMENTE EXCLUSIVOS. Usar um OU outro.
     Permitir os dois exigiria resolver a intersecao, o que torna a UI
     ambigua e duplica a logica de filtro.

  5. Fuso horario: `data_inicio`/`data_fim` sao `date` ISO-8601. O
     endpoint (Bloco 6.2) e responsavel por convertar para o intervalo
     `[inicio 00:00, fim+1 00:00)` em `America/Sao_Paulo` e comparar com
     `created_at` (TIMESTAMPTZ UTC). Este schema apenas carrega os dados.

Ver tambem:
  - WAVE6_ANALYSIS.md secoes 1.6, 3.2, 4, 7.1
  - ADR-039 (Wave 2 — audit_service centralizado)
  - ADR-099 (esta Wave — projecao de `tipo_evento`)
"""
from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# =============================================================================
# 1. CONSTANTES — whitelist de `acao` e labels pt-BR
# =============================================================================

ACOES_VALIDAS: frozenset[str] = frozenset(
    {
        "criar_prova",
        "escanear_prova",
        "transitar_status",
        "reiniciar_ciclo",
        "atualizar_configuracao",
    }
)
"""Valores aceitos pela coluna `audit_logs.acao` em producao (Waves 2-5).

Mantem esta lista sincronizada com as chamadas de `log_audit()` no backend:
  - `api/v1/provas.py`         -> `criar_prova`, `escanear_prova`
  - `api/v1/configuracoes.py`  -> `atualizar_configuracao`
  - `services/state_machine.py` -> `transitar_status`, `reiniciar_ciclo`

Novas `acao` adicionadas em Waves futuras DEVEM entrar aqui E em
`app/services/auditoria_projection.py` — caso contrario o filtro
`?acao=<nova>` retorna 422 e a tela nao exibe o tipo_evento correto.
"""


class TipoEventoEnum(StrEnum):
    """Tipos de evento DERIVADOS pela funcao `projetar_tipo_evento`.

    A camada de escrita usa apenas 5 valores crus de `acao`, mas a UI
    precisa distinguir "cancelamento", "reprovacao" e "transicao comum"
    dentro do guarda-chuva `transitar_status`. Esta enum e a fonte unica
    da verdade sobre os tipos exibidos na tela (ADR-099).
    """

    CRIACAO_PROVA = "CRIACAO_PROVA"
    ESCANEAMENTO = "ESCANEAMENTO"
    CANCELAMENTO = "CANCELAMENTO"
    REPROVACAO = "REPROVACAO"
    TRANSICAO_STATUS = "TRANSICAO_STATUS"
    REINICIO_CICLO = "REINICIO_CICLO"
    ALTERACAO_CONFIG = "ALTERACAO_CONFIG"


TIPO_EVENTO_LABELS: dict[TipoEventoEnum, str] = {
    TipoEventoEnum.CRIACAO_PROVA: "Criacao de prova",
    TipoEventoEnum.ESCANEAMENTO: "Escaneamento",
    TipoEventoEnum.CANCELAMENTO: "Cancelamento",
    TipoEventoEnum.REPROVACAO: "Reprovacao",
    TipoEventoEnum.TRANSICAO_STATUS: "Transicao de status",
    TipoEventoEnum.REINICIO_CICLO: "Reinicio de ciclo",
    TipoEventoEnum.ALTERACAO_CONFIG: "Alteracao de configuracao",
}
"""Labels pt-BR para exibicao na tela. Sem acentos por consistencia com o
padrao do projeto (os demais schemas usam strings ASCII para evitar
problemas de encoding em headers HTTP e exports CSV)."""


# =============================================================================
# 2. FILTROS DE REQUEST — query params de GET /api/v1/auditoria/
# =============================================================================

LIMIT_DEFAULT: int = 50
"""Quantidade padrao de items retornados quando `limit` nao e informado."""

LIMIT_MAX: int = 100
"""Teto maximo de `limit` — protege contra abuso e mantem o response curto."""


class AuditoriaFiltros(BaseModel):
    """Query params para `GET /api/v1/auditoria/`.

    Todos os campos sao opcionais. O comportamento default retorna os 50
    eventos mais recentes ordenados por `(created_at DESC, id DESC)`.

    Regras cruzadas (validadas em `_validar_filtros`):
      - `acao` e `tipo_evento` sao MUTUAMENTE EXCLUSIVOS.
      - `data_inicio` deve ser <= `data_fim` quando ambos presentes.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    data_inicio: date | None = None
    """Data ISO-8601 no fuso `America/Sao_Paulo`. Convertida para
    `created_at >= inicio 00:00:00 BRT` pelo endpoint."""

    data_fim: date | None = None
    """Data ISO-8601 no fuso `America/Sao_Paulo`. Convertida para
    `created_at < (fim + 1 dia) 00:00:00 BRT` (intervalo inclusivo do
    dia inteiro)."""

    usuario_id: UUID | None = None
    """UUID do usuario autor do log (`audit_logs.usuario_id`)."""

    nro_requerimento: str | None = Field(default=None, max_length=50)
    """Filtra por prova cujo `nro_requerimento` bate exato. Resolve em
    subquery para `prova_id`. Retorna lista vazia (nao 404) se o
    `nro_requerimento` nao existe — o log e uma consulta, nao um CRUD."""

    acao: list[str] | None = None
    """Filtro por valores crus de `acao`. Whitelist em `ACOES_VALIDAS`.
    Mutuamente exclusivo com `tipo_evento`."""

    tipo_evento: list[TipoEventoEnum] | None = None
    """Filtro pelos tipos DERIVADOS (7 valores). O endpoint mapeia de volta
    para `acao` + condicoes JSONB antes de executar. Mutuamente exclusivo
    com `acao`."""

    cursor: str | None = None
    """Cursor opaco base64 para keyset pagination. Codifica
    `{"created_at": "...", "id": "..."}` — o endpoint decodifica em
    `auditoria_query` (Bloco 6.2). Nao interpretado aqui."""

    limit: int = Field(default=LIMIT_DEFAULT, ge=1, le=LIMIT_MAX)
    """Quantidade de items por pagina. Default 50, maximo 100."""

    @field_validator("acao")
    @classmethod
    def _validar_acao_whitelist(cls, v: list[str] | None) -> list[str] | None:
        """Rejeita valores fora de `ACOES_VALIDAS` e dedupe preservando ordem."""
        if v is None:
            return None
        invalidos = [a for a in v if a not in ACOES_VALIDAS]
        if invalidos:
            raise ValueError(
                f"Acoes invalidas: {invalidos}. "
                f"Valores aceitos: {sorted(ACOES_VALIDAS)}"
            )
        # Dedupe preservando ordem de primeira aparicao.
        vistos: set[str] = set()
        deduped: list[str] = []
        for acao in v:
            if acao not in vistos:
                vistos.add(acao)
                deduped.append(acao)
        return deduped

    @field_validator("tipo_evento")
    @classmethod
    def _dedupe_tipo_evento(
        cls, v: list[TipoEventoEnum] | None
    ) -> list[TipoEventoEnum] | None:
        """Dedupe preservando ordem — a enum ja valida os valores."""
        if v is None:
            return None
        vistos: set[TipoEventoEnum] = set()
        deduped: list[TipoEventoEnum] = []
        for tipo in v:
            if tipo not in vistos:
                vistos.add(tipo)
                deduped.append(tipo)
        return deduped

    @model_validator(mode="after")
    def _validar_filtros(self) -> AuditoriaFiltros:
        """Validacoes cruzadas entre campos."""
        if self.acao and self.tipo_evento:
            raise ValueError(
                "Filtros 'acao' e 'tipo_evento' sao mutuamente exclusivos. "
                "Use um OU outro — nao ambos."
            )
        if (
            self.data_inicio is not None
            and self.data_fim is not None
            and self.data_inicio > self.data_fim
        ):
            raise ValueError(
                "data_inicio nao pode ser posterior a data_fim."
            )
        return self


# =============================================================================
# 3. RESPONSE DTOs — items, paginacao, filtros aplicados
# =============================================================================


class UsuarioAuditoria(BaseModel):
    """Usuario autor do log, enriquecido via LEFT JOIN com `usuarios`.

    Campos minimos suficientes para a UI exibir "quem fez o evento" sem
    exigir uma segunda chamada ao endpoint de usuarios.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID
    nome: str
    setor: str
    is_admin: bool


class ProvaAuditoria(BaseModel):
    """Prova relacionada ao log, enriquecida via LEFT JOIN com `provas_digitais`.

    Null quando `audit_logs.prova_id` e NULL — caso tipico de
    `atualizar_configuracao`, que nao esta vinculada a uma prova especifica.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID
    nro_requerimento: str
    nome: str


class AuditLogItem(BaseModel):
    """Uma entrada de audit log enriquecida e projetada.

    Campos projetados pela Wave 6:
      - `tipo_evento`       — enum derivado (regra em `auditoria_projection`)
      - `tipo_evento_label` — label pt-BR para exibicao direta

    Campos originais (`acao`, `detalhes_json`, `ip_address`, `user_agent`,
    `created_at`) sao preservados AS-IS. `detalhes_json` nao e sanitizado —
    a varredura empirica do Bloco 6.0 confirmou que nao contem PII sensivel
    (zero ocorrencias de `password`/`token`/`secret`/`api_key`), e o acesso
    e restrito a admin via `pol_audit_select` + `get_admin_user`.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID
    acao: str
    """Valor cru de `audit_logs.acao` (um dos 5 em `ACOES_VALIDAS`)."""

    tipo_evento: TipoEventoEnum
    """Enum derivado pela funcao `projetar_tipo_evento(acao, detalhes_json)`."""

    tipo_evento_label: str
    """Label pt-BR para exibicao direta na tela (de `TIPO_EVENTO_LABELS`)."""

    usuario: UsuarioAuditoria

    prova: ProvaAuditoria | None
    """Null quando `audit_logs.prova_id` e NULL (ex: alteracao de config)."""

    detalhes_json: dict[str, Any] | None
    """JSONB cru preservado para exibicao no modal de detalhes. Ver seccao
    6.0.2 do WAVE6_ANALYSIS.md para inventario completo das chaves por
    `acao`."""

    ip_address: str | None
    """IP do cliente (ADR F04, Wave 2 auditoria externa). Populado a partir
    de `X-Forwarded-For` > `X-Real-IP` > `request.client.host`."""

    user_agent: str | None
    """User-Agent HTTP, truncado em 2000 chars pela camada de escrita."""

    created_at: datetime
    """Timestamp UTC do momento do evento (`audit_logs.created_at`,
    preenchido por `DEFAULT now()`). Imutavel por trigger."""


class FiltrosAplicados(BaseModel):
    """Echo dos filtros efetivamente aplicados na query.

    Usado pela UI para renderizar os "chips" de filtro ativo no topo da
    tabela (padrao de UX inspirado em `/provas` da Wave 2) e por testes de
    integracao para verificar que os parametros chegaram ao endpoint como
    esperado.
    """

    model_config = ConfigDict(frozen=True)

    data_inicio: date | None
    data_fim: date | None
    usuario_id: UUID | None
    nro_requerimento: str | None
    acao: list[str] | None
    tipo_evento: list[TipoEventoEnum] | None
    limit: int


# Cap do COUNT(*) filtrado — 100_001 sinaliza "mais de 100k" para a UI.
# Mantido aqui (e nao no endpoint) para que testes unitarios possam verificar
# o comportamento sem subir FastAPI.
TOTAL_ESTIMADO_CAP: int = 100_001
"""Teto do COUNT(*) filtrado. Se a query interna retornar >= este valor,
expomos exatamente este valor e a UI exibe '100k+'. Mantem o response
previsivel sem precisar de estimativas via `pg_class.reltuples`."""


class AuditoriaListResponse(BaseModel):
    """Resposta de `GET /api/v1/auditoria/` — pagina de audit logs.

    A estrutura segue o padrao keyset pagination:
      - `items`: lista ordenada por `(created_at DESC, id DESC)`.
      - `next_cursor`: opaco; None quando nao ha mais paginas.
      - `has_more`: True quando a query interna retornou N+1 items.
      - `total_estimado`: COUNT(*) filtrado, capped em `TOTAL_ESTIMADO_CAP`.
      - `filtros_aplicados`: echo dos filtros para debug e UI.
    """

    model_config = ConfigDict(frozen=True)

    items: list[AuditLogItem]

    next_cursor: str | None
    """Base64 opaco para a proxima pagina. None quando `has_more=False`."""

    has_more: bool
    """True se ha mais items apos esta pagina."""

    total_estimado: int
    """COUNT(*) filtrado com os mesmos filtros (exceto `cursor` e `limit`).
    Capped em `TOTAL_ESTIMADO_CAP` — se retornar esse valor, a UI exibe
    '100k+' em vez do numero exato."""

    filtros_aplicados: FiltrosAplicados
