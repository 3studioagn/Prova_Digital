"""Pydantic v2 schemas para Interface de Log de Auditoria (Wave 6, Componente 18).

Implementa RNF-005: leitura imutavel do log de auditoria, restrito ao perfil
3Studio (is_admin=true). Cobre tres endpoints:
  - GET /api/v1/audit-log              -> listagem paginada com filtros
  - GET /api/v1/audit-log/{id}         -> detalhe de um registro
  - GET /api/v1/audit-log/by-prova/{id} -> historico cronologico por prova

Convencoes:
  - Datas em UTC (timezone-aware). Frontend converte para America/Sao_Paulo.
  - Campos `frozen=True` para evitar mutacao acidental no path de response.
  - `assinatura_digital` (BYTEA) NUNCA e exposta em response — apenas o
    boolean `assinatura_digital_presente` no detalhe.
  - `acao` aceita qualquer string <= 100 chars (sem hardcode dos 6 valores
    conhecidos hoje), porque migrations futuras podem adicionar novos.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.db.models import RotaEnum, SetorEnum, StatusProvaEnum


# ─── Constantes de validacao ───────────────────────────────────────────────


MAX_PAGE_SIZE = 200
"""Maximo de itens por pagina na listagem (consistente com /api/v1/users)."""

DEFAULT_PAGE_SIZE = 50
"""Default razoavel para um log auditoria (mais denso que listagem de provas)."""

MAX_RANGE_DAYS = 366
"""Maximo de dias entre `from_dt` e `to_dt` (consistente com /api/v1/reports)."""

MAX_Q_LENGTH = 200
"""Tamanho maximo da busca textual em `detalhes_json::text`."""

MAX_BY_PROVA_ITEMS = 500
"""Hard cap defensivo no historico por prova (sentinela para investigacao)."""


# ─── Query schema (params da listagem) ─────────────────────────────────────


class AuditLogListQuery(BaseModel):
    """Parametros da query GET /api/v1/audit-log.

    Todos os filtros sao opcionais. Defaults conservadores: pagina 1,
    50 itens, ordem decrescente. Validacao Pydantic gera 422 automatico.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)
    sort: str = Field(default="desc", pattern="^(asc|desc)$")
    """Ordenacao por created_at: 'desc' (mais recente primeiro) ou 'asc'."""

    from_dt: datetime | None = Field(default=None, alias="from")
    """Inicio do intervalo (UTC). Inclusive."""

    to_dt: datetime | None = Field(default=None, alias="to")
    """Fim do intervalo (UTC). Exclusive."""

    prova_id: UUID | None = None
    """Filtra por prova especifica."""

    usuario_id: UUID | None = None
    """Filtra por ator (usuario que executou a acao)."""

    acao: str | None = Field(default=None, max_length=100)
    """Filtra por tipo de evento. Aceita qualquer string <= 100 chars."""

    q: str | None = Field(default=None, max_length=MAX_Q_LENGTH)
    """Busca textual em detalhes_json::text (LIKE case-insensitive)."""

    @model_validator(mode="after")
    def validate_date_range(self) -> "AuditLogListQuery":
        """Valida invariantes do intervalo de datas."""
        if self.from_dt is not None and self.to_dt is not None:
            if self.from_dt >= self.to_dt:
                raise ValueError("'from' deve ser anterior a 'to'")
            if (self.to_dt - self.from_dt) > timedelta(days=MAX_RANGE_DAYS):
                raise ValueError(
                    f"Intervalo maximo permitido: {MAX_RANGE_DAYS} dias"
                )
        # Garante timezone-aware (default UTC se naive). Pydantic v2 aceita
        # naive datetimes; normalizamos para evitar comparacoes ambiguas no SQL.
        if self.from_dt is not None and self.from_dt.tzinfo is None:
            object.__setattr__(
                self, "from_dt", self.from_dt.replace(tzinfo=timezone.utc)
            )
        if self.to_dt is not None and self.to_dt.tzinfo is None:
            object.__setattr__(
                self, "to_dt", self.to_dt.replace(tzinfo=timezone.utc)
            )
        return self

    @model_validator(mode="after")
    def validate_q_no_control_chars(self) -> "AuditLogListQuery":
        """Rejeita caracteres de controle no termo de busca (defensivo)."""
        if self.q is not None:
            cleaned = self.q.strip()
            if any(ord(c) < 32 and c not in ("\t",) for c in cleaned):
                raise ValueError("Busca contem caracteres de controle invalidos")
            if cleaned == "":
                # Trata string vazia como ausencia do filtro.
                object.__setattr__(self, "q", None)
            else:
                object.__setattr__(self, "q", cleaned)
        return self


# ─── Item de listagem ──────────────────────────────────────────────────────


class AuditLogItemResponse(BaseModel):
    """Linha individual da listagem de audit_logs.

    Combina dados de audit_logs + JOINs com usuarios (nome, setor) e
    provas_digitais (nro_requerimento) para exibir labels amigaveis na UI
    sem N+1 queries.
    """

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    acao: str
    prova_id: UUID | None
    prova_nro_requerimento: str | None
    """Nro requerimento da prova relacionada — ausente se acao nao tem prova
    (ex: atualizar_configuracao) ou se a prova foi removida (nao deve ocorrer
    em producao porque provas_digitais e auditada — mas defensivo)."""

    usuario_id: UUID
    usuario_nome: str
    usuario_setor: SetorEnum

    detalhes_json: dict[str, Any] | None
    """Payload estruturado da acao. Pode conter PII (cliente, motivo_reprovacao);
    restrito a admin via RLS pol_audit_select."""

    ip_address: str | None
    user_agent: str | None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    """Response paginado da listagem.

    `total` e count(*) com os mesmos filtros aplicados (1 query extra).
    """

    model_config = ConfigDict(frozen=True)

    items: list[AuditLogItemResponse]
    total: int
    page: int
    page_size: int


# ─── Detalhe (com enriquecimento opcional de movimentacao) ────────────────


class MovimentacaoSnapshot(BaseModel):
    """Resumo da movimentacao relacionada a um audit_log de transitar_status
    ou reiniciar_ciclo.

    SEMPRE omite a `assinatura_digital` (BYTEA) — apenas expoe o boolean
    `assinatura_digital_presente` para confirmar que houve assinatura conforme
    RN-003. Caso de uso: investigador quer saber se a transicao foi assinada,
    nao quer copiar bytes.
    """

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    status_anterior: StatusProvaEnum
    status_novo: StatusProvaEnum
    motivo_reprovacao: str | None
    ciclo: int
    rota_no_momento: RotaEnum | None
    assinatura_digital_presente: bool
    created_at: datetime


class AuditLogDetailResponse(AuditLogItemResponse):
    """Detalhe individual com enriquecimento opcional.

    `movimentacao_relacionada` e populada apenas quando `acao` e
    'transitar_status' ou 'reiniciar_ciclo' E a query de matching
    encontra exatamente uma movimentacao correspondente (ver
    audit_log_service._find_movimentacao_relacionada).
    """

    model_config = ConfigDict(frozen=True)

    movimentacao_relacionada: MovimentacaoSnapshot | None = None
