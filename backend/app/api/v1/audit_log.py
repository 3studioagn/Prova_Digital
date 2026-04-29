"""Router de Interface de Log de Auditoria (Wave 6, Componente 18).

Implementa RNF-005: leitura imutavel do log de auditoria, restrito ao perfil
3Studio (is_admin=true). Tres endpoints:

  - GET /api/v1/audit-log              -> listagem paginada com filtros
  - GET /api/v1/audit-log/{id}         -> detalhe (com enriquecimento opcional
                                          de movimentacao relacionada para
                                          eventos transitar_status/reiniciar_ciclo)
  - GET /api/v1/audit-log/by-prova/{id} -> historico cronologico por prova

RBAC em tres camadas (defesa em profundidade):
  1. Middleware: `Depends(get_admin_user)` em todos os endpoints — 401 sem
     token, 403 sem is_admin=true, antes de qualquer query DB.
  2. RLS pol_audit_select (RLS 005) bloqueia clientes nao-bypassrls.
  3. Frontend guard de menu condicional ao is_admin (defesa de UX).

Sem cache: a UI de auditoria precisa refletir o estado atual em tempo real
(admin pode estar investigando incidente). `Cache-Control: no-store`.

Auditoria do proprio acesso: cada request emite log de aplicacao INFO com
usuario_id e filtros aplicados — para investigar quem leu o que. NAO grava
em audit_logs (evita auto-referencia + spam: leitura nao deveria ser auditada
no mesmo log que ela esta consumindo).
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user
from app.db.models import Usuario
from app.db.session import get_db
from app.domain.schemas.audit_log import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MAX_Q_LENGTH,
    AuditLogDetailResponse,
    AuditLogListQuery,
    AuditLogListResponse,
)
from app.services.audit_log_service import (
    buscar_audit_log_detalhe,
    listar_audit_logs,
    listar_audit_logs_por_prova,
    prova_existe,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Header anti-cache ────────────────────────────────────────────────────


# Audit 2026-04-29 M-03: `Pragma: no-cache` removido — RFC 9111 (HTTP caching)
# deprecia o header em RESPOSTAS. So fazia sentido em request HTTP/1.0.
# `Cache-Control: no-store` ja garante que clientes modernos nao guardem copia.
_NO_STORE_HEADERS = {
    "Cache-Control": "no-store",
}


# ─── Helpers de path ──────────────────────────────────────────────────────


def parse_audit_id(
    audit_log_id: str = Path(
        ..., alias="id", description="UUID do registro de audit_log"
    ),
) -> uuid.UUID:
    """Converte path param para UUID, retornando 404 (consistente com
    parse_prova_id da Wave 2 — qualquer string mal formada ou inexistente
    e tratada uniformemente como 'nao encontrado').

    Uso de `alias="id"` mantem a URL `/audit-log/{id}` (compat) enquanto
    o parametro interno `audit_log_id` evita shadowing do builtin `id()`.
    """
    try:
        return uuid.UUID(audit_log_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro nao encontrado",
        )


def parse_prova_id_path(
    prova_id: str = Path(..., description="UUID da prova"),
) -> uuid.UUID:
    """Mesmo padrao de parse_prova_id da Wave 2. Local para evitar import
    circular com app.api.v1.provas (que tambem importa deps em outras
    direcoes)."""
    try:
        return uuid.UUID(prova_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prova nao encontrada",
        )


# ─── GET /api/v1/audit-log — listagem paginada ────────────────────────────


@router.get("", response_model=AuditLogListResponse)
@router.get("/", response_model=AuditLogListResponse)
async def list_audit_logs(
    response: Response,
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    sort: str = Query("desc", pattern="^(asc|desc)$"),
    order_by: str = Query("created_at"),
    from_dt: str | None = Query(None, alias="from"),
    to_dt: str | None = Query(None, alias="to"),
    prova_id: uuid.UUID | None = Query(None),
    usuario_id: uuid.UUID | None = Query(None),
    acao: str | None = Query(None, max_length=100),
    tipo_evento: str | None = Query(None, max_length=20),
    q: str | None = Query(None, max_length=MAX_Q_LENGTH),
    admin: Usuario = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AuditLogListResponse:
    """Lista registros de audit_logs com filtros + paginacao.

    Parametros recebidos como strings cruas e revalidados via
    AuditLogListQuery (Pydantic v2) para centralizar invariantes
    (intervalo coerente, max 366 dias, sanitizacao de q).

    Query params suportados:
      - page (>=1, default 1)
      - page_size (1-200, default 50)
      - sort ('asc'|'desc', default 'desc')
      - from / to (ISO 8601 — UTC; se naive, normaliza pra UTC)
      - prova_id (UUID)
      - usuario_id (UUID)
      - acao (string <=100)
      - q (string <=200, busca em detalhes_json::text)

    Returns:
        AuditLogListResponse com items + total + page + page_size.

    Raises:
        401 sem token, 403 sem is_admin (via Depends).
        422 se Pydantic falhar na validacao agregada.
        502 se DB indisponivel (erro transitorio).
    """
    # Constroi e valida o query schema de forma centralizada.
    try:
        query_schema = AuditLogListQuery.model_validate(
            {
                "page": page,
                "page_size": page_size,
                "sort": sort,
                "order_by": order_by,
                "from": from_dt,
                "to": to_dt,
                "prova_id": prova_id,
                "usuario_id": usuario_id,
                "acao": acao,
                "tipo_evento": tipo_evento,
                "q": q,
            }
        )
    except ValueError as exc:
        # Pydantic ValidationError ja traz detalhes; FastAPI seria 500 se
        # nao traduzissemos. 422 e o codigo apropriado para validacao.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )

    logger.info(
        "audit_log.list user=%s page=%d size=%d order=%s/%s filters=%s",
        admin.id,
        query_schema.page,
        query_schema.page_size,
        query_schema.order_by,
        query_schema.sort,
        {
            k: str(v) if v is not None else None
            for k, v in {
                "from": query_schema.from_dt,
                "to": query_schema.to_dt,
                "prova_id": query_schema.prova_id,
                "usuario_id": query_schema.usuario_id,
                "acao": query_schema.acao,
                "tipo_evento": query_schema.tipo_evento,
                "q": query_schema.q,
            }.items()
            if v is not None
        },
    )

    try:
        result = await listar_audit_logs(db, query_schema)
    except SQLAlchemyError:
        logger.exception(
            "audit_log.list DB error user=%s", admin.id
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao carregar log de auditoria",
        )

    response.headers.update(_NO_STORE_HEADERS)
    return result


# ─── GET /api/v1/audit-log/by-prova/{prova_id} — historico por prova ─────
#
# IMPORTANTE: este endpoint precisa estar declarado ANTES de
# `GET /{id}` porque FastAPI faz o matching em ordem; senao
# `/by-prova/<uuid>` cairia no handler de detalhe (que esperaria
# `id = "by-prova"` — string nao-UUID — e retornaria 404 generico).


@router.get("/by-prova/{prova_id}", response_model=AuditLogListResponse)
async def list_audit_logs_by_prova(
    response: Response,
    prova_id: uuid.UUID = Depends(parse_prova_id_path),
    sort: str = Query("asc", pattern="^(asc|desc)$"),
    admin: Usuario = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AuditLogListResponse:
    """Lista todos os audit_logs de uma prova especifica, em ordem cronologica.

    Sem paginacao — uma prova com historico longo (5 reinicios + 30
    transicoes) cabe folgadamente em uma resposta. Hard cap defensivo
    em 500 itens (audit_log_service.MAX_BY_PROVA_ITEMS).

    Default sort='asc' (cronologico) — caso de uso primario e ler como
    a prova evoluiu, do inicio ao fim.

    Returns:
        AuditLogListResponse — items, total = len(items), page=1,
        page_size=500.

    Raises:
        401 sem token, 403 sem is_admin (via Depends).
        404 se prova nao existir.
        502 se DB indisponivel.
    """
    logger.info(
        "audit_log.by_prova user=%s prova=%s sort=%s",
        admin.id,
        prova_id,
        sort,
    )

    try:
        # 404 antes de listar — evita resposta vazia confundir com "prova
        # existe mas sem audit_logs" (que tambem e valida — apenas seria
        # items=[]).
        if not await prova_existe(db, prova_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prova nao encontrada",
            )
        result = await listar_audit_logs_por_prova(db, prova_id, sort=sort)
    except HTTPException:
        raise
    except SQLAlchemyError:
        logger.exception(
            "audit_log.by_prova DB error user=%s prova=%s",
            admin.id,
            prova_id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao carregar historico da prova",
        )

    response.headers.update(_NO_STORE_HEADERS)
    return result


# ─── GET /api/v1/audit-log/{id} — detalhe ────────────────────────────────


@router.get("/{id}", response_model=AuditLogDetailResponse)
async def get_audit_log_detail(
    response: Response,
    audit_log_id: uuid.UUID = Depends(parse_audit_id),
    admin: Usuario = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AuditLogDetailResponse:
    """Carrega detalhe de um audit_log, com enriquecimento opcional.

    Quando `acao` e 'transitar_status' ou 'reiniciar_ciclo', tenta encontrar
    a Movimentacao correspondente via matching tripla (prova_id +
    status_novo + ciclo) com janela ±5s — preenche
    `movimentacao_relacionada` se achar exatamente uma.

    Se nao achar (formato antigo de detalhes_json, acao sem movimentacao,
    ou ambiguidade nao resolvida), retorna `movimentacao_relacionada=None`
    silenciosamente — o detalhe ainda e valido sem o enriquecimento.

    Returns:
        AuditLogDetailResponse.

    Raises:
        401, 403, 404, 502 (mesmos do list).
    """
    logger.info("audit_log.detail user=%s id=%s", admin.id, audit_log_id)

    try:
        result = await buscar_audit_log_detalhe(db, audit_log_id)
    except SQLAlchemyError:
        logger.exception(
            "audit_log.detail DB error user=%s id=%s", admin.id, audit_log_id
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao carregar registro",
        )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro nao encontrado",
        )

    response.headers.update(_NO_STORE_HEADERS)
    return result
