"""Endpoints REST para Interface de Log de Auditoria (Wave 6, Componente 18).

Implementa RNF-005 (log imutavel e completo, acesso restrito ao perfil
3Studio) via dois endpoints de LEITURA:

  - `GET /api/v1/auditoria/`     — listagem paginada keyset (admin only)
  - `GET /api/v1/auditoria/{id}` — detalhe pontual (admin only)

**Nao ha POST/PUT/PATCH/DELETE** por design. O audit_log e imutavel via:
  1. Trigger `trg_audit_logs_imutavel` (Wave 0, migration 001) — bloqueia
     UPDATE/DELETE no nivel do banco.
  2. `audit_service.log_audit()` (ADR-039, Wave 2) — unica via de INSERT,
     chamada pelos outros endpoints.
  3. Ausencia de rotas de escrita aqui — FastAPI retorna 405 Method Not
     Allowed automaticamente.

Gate RBAC: `Depends(get_admin_user)` (ADR-018, Wave 1) — `is_admin=true`
obrigatorio. Qualquer `is_admin=false` (incluindo vendedor, motorista,
clicheria) recebe 403.

Ver tambem:
  - WAVE6_ANALYSIS.md secoes 4 (contratos) e 7 (testes)
  - ADR-099 (projecao de `tipo_evento`)
  - app/services/auditoria_query.py (camada SQL)
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user
from app.db.models import Usuario
from app.db.session import get_db
from app.domain.schemas.auditoria import (
    LIMIT_DEFAULT,
    LIMIT_MAX,
    AuditLogItem,
    AuditoriaFiltros,
    AuditoriaListResponse,
    TipoEventoEnum,
)
from app.services.auditoria_query import (
    AuditLogSemUsuarioError,
    CursorInvalidoError,
    buscar_audit_log_por_id,
    listar_audit_logs,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _format_validation_error(exc: ValidationError) -> str:
    """Formata `ValidationError` em mensagem pt-BR amigavel.

    Remove o prefixo `"Value error, "` que o Pydantic v2 adiciona
    automaticamente em mensagens de `field_validator`/`model_validator`,
    e retorna apenas a primeira mensagem de erro (geralmente suficiente
    para o usuario).
    """
    errors = exc.errors()
    if not errors:
        return "parametros invalidos"
    first = errors[0]
    msg = str(first.get("msg", "parametros invalidos"))
    prefix = "Value error, "
    if msg.startswith(prefix):
        msg = msg[len(prefix) :]
    return msg


@router.get(
    "/",
    response_model=AuditoriaListResponse,
    summary="Listar logs de auditoria (Componente 18)",
    description=(
        "Lista paginada do log de auditoria imutavel. Suporta filtros por "
        "periodo, autor, prova, tipo de evento e acao crua. Paginacao "
        "keyset via cursor opaco. Restrito ao perfil 3Studio "
        "(`is_admin=true`) — RNF-005."
    ),
)
async def listar_auditoria(
    data_inicio: Annotated[date | None, Query()] = None,
    data_fim: Annotated[date | None, Query()] = None,
    usuario_id: Annotated[UUID | None, Query()] = None,
    nro_requerimento: Annotated[str | None, Query(max_length=50)] = None,
    acao: Annotated[list[str] | None, Query()] = None,
    tipo_evento: Annotated[list[TipoEventoEnum] | None, Query()] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=LIMIT_MAX)] = LIMIT_DEFAULT,
    _admin: Usuario = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AuditoriaListResponse:
    """RNF-005 — lista o audit_log com filtros e paginacao, admin only."""
    # Construcao do modelo Pydantic dispara os `model_validator`/
    # `field_validator`/`@field_validator` que validam mutualmente-
    # exclusivo, whitelist de `acao`, data range, etc.
    try:
        filtros = AuditoriaFiltros(
            data_inicio=data_inicio,
            data_fim=data_fim,
            usuario_id=usuario_id,
            nro_requerimento=nro_requerimento,
            acao=acao,
            tipo_evento=tipo_evento,
            cursor=cursor,
            limit=limit,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=_format_validation_error(exc),
        ) from exc

    try:
        return await listar_audit_logs(db, filtros)
    except CursorInvalidoError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"cursor invalido: {exc}",
        ) from exc
    except AuditLogSemUsuarioError as exc:
        logger.error("Inconsistencia em listagem de audit_log: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Log de auditoria com dado inconsistente",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Falha inesperada em listar_auditoria")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao consultar log de auditoria",
        ) from exc


@router.get(
    "/{log_id}",
    response_model=AuditLogItem,
    summary="Detalhe de um log de auditoria (Componente 18)",
    description=(
        "Retorna uma entrada pontual do log de auditoria, enriquecida com "
        "dados do autor e da prova relacionada. Restrito ao perfil 3Studio "
        "(`is_admin=true`) — RNF-005."
    ),
)
async def detalhar_auditoria(
    log_id: UUID,
    _admin: Usuario = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AuditLogItem:
    """RNF-005 — detalhe pontual de um audit_log, admin only."""
    try:
        item = await buscar_audit_log_por_id(db, log_id)
    except AuditLogSemUsuarioError as exc:
        logger.error("Inconsistencia em audit_log %s: %s", log_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Log de auditoria com dado inconsistente",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "Falha inesperada em detalhar_auditoria log_id=%s", log_id
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao consultar log de auditoria",
        ) from exc

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log de auditoria nao encontrado",
        )
    return item
