"""Router de Configuracoes do Sistema — Componente 09 do Backlog.

Endpoints:
  - GET   /api/v1/configuracoes/          -> ConfiguracaoListResponse
  - GET   /api/v1/configuracoes/{chave}   -> ConfiguracaoResponse
  - PATCH /api/v1/configuracoes/{chave}   -> ConfiguracaoResponse

Autorizacao (Wave 1 v4.0): todos os endpoints exigem
`access_required("configuracoes")` — corresponde a celula da Matriz de
Acesso (Secao 6 do RequisitosProvasDigitais_v4_0.docx, linha
"Configuracoes do Sistema"). 3Studio = full; demais perfis = negado.

RLS ja esta ativa em `public.configuracoes_sistema` com policies
admin-only (pol_config_select, pol_config_update — ver migrations RLS
009/010/012), mas o backend usa service_role e bypassa RLS — a
checagem primaria e via dependency FastAPI.

Chaves editaveis (ADR-043): whitelist estatica em
`app.domain.schemas.configuracao.EDITABLE_KEYS`. Chaves novas precisam de
uma migration Alembic + update da whitelist.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.access import access_required
from app.db.models import ConfiguracaoSistema, Usuario
from app.db.session import get_db
from app.domain.schemas.configuracao import (
    EDITABLE_KEYS,
    ConfiguracaoListResponse,
    ConfiguracaoResponse,
    ConfiguracaoUpdateRequest,
    ConfiguracaoValidationError,
    validar_valor_por_chave,
)
from app.services.audit_service import log_audit

logger = logging.getLogger(__name__)
router = APIRouter()


# ───────────────────────────────────────────────────────────────────────
# GET /api/v1/configuracoes/
# ───────────────────────────────────────────────────────────────────────


@router.get("/", response_model=ConfiguracaoListResponse)
async def list_configuracoes(
    db: AsyncSession = Depends(get_db),
    admin: Usuario = Depends(access_required("configuracoes")),
) -> ConfiguracaoListResponse:
    """Lista todas as configuracoes do sistema (admin-only).

    Retorna apenas as chaves whitelisted (EDITABLE_KEYS). Chaves que
    eventualmente existam no banco mas nao estejam na whitelist sao
    filtradas do response — evita vazamento acidental de config interna.

    A1 (auditoria Wave 2 — Sessao 21): try/except em torno da query
    mapeia erros transitorios de DB para 502 acionavel em vez de 500
    generico do handler global. Mesmo padrao do ADR-074 (C07) e
    ADR-076 (C08).
    """
    try:
        result = await db.execute(
            select(ConfiguracaoSistema)
            .where(ConfiguracaoSistema.chave.in_(EDITABLE_KEYS))
            .order_by(ConfiguracaoSistema.chave)
        )
        rows = result.scalars().all()
    except Exception:
        logger.exception(
            "Falha ao listar configuracoes (admin=%s)", admin.id
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao carregar configuracoes",
        )

    return ConfiguracaoListResponse(
        items=[ConfiguracaoResponse.model_validate(r) for r in rows]
    )


# ───────────────────────────────────────────────────────────────────────
# GET /api/v1/configuracoes/{chave}
# ───────────────────────────────────────────────────────────────────────


@router.get("/{chave}", response_model=ConfiguracaoResponse)
async def get_configuracao(
    chave: str,
    db: AsyncSession = Depends(get_db),
    admin: Usuario = Depends(access_required("configuracoes")),
) -> ConfiguracaoResponse:
    """Retorna uma configuracao especifica (admin-only).

    404 em dois cenarios:
      - chave nao esta na whitelist (EDITABLE_KEYS)
      - chave esta na whitelist mas nao existe no banco (bug — migration
        nao foi aplicada ou o seed foi removido manualmente)

    A1 (auditoria Wave 2 — Sessao 21): try/except em torno da query
    mapeia erros transitorios de DB para 502. HTTPException (404) e
    re-levantada antes do except Exception para nao ser mascarada.
    """
    if chave not in EDITABLE_KEYS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuracao '{chave}' nao existe ou nao e editavel",
        )

    try:
        result = await db.execute(
            select(ConfiguracaoSistema).where(ConfiguracaoSistema.chave == chave)
        )
        config = result.scalar_one_or_none()
        if config is None:
            logger.error(
                "Configuracao whitelisted '%s' nao encontrada no banco. "
                "Migration 002 pode ter sido revertida.",
                chave,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuracao '{chave}' nao esta cadastrada no sistema",
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Falha ao carregar configuracao '%s' (admin=%s)", chave, admin.id
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao carregar configuracao",
        )

    return ConfiguracaoResponse.model_validate(config)


# ───────────────────────────────────────────────────────────────────────
# PATCH /api/v1/configuracoes/{chave}
# ───────────────────────────────────────────────────────────────────────


@router.patch("/{chave}", response_model=ConfiguracaoResponse)
async def update_configuracao(
    chave: str,
    body: ConfiguracaoUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: Usuario = Depends(access_required("configuracoes")),
) -> ConfiguracaoResponse:
    """Atualiza uma configuracao especifica (admin-only).

    Fluxo:
      1. Valida chave ∈ EDITABLE_KEYS (404 caso contrario)
      2. SELECT FOR UPDATE na linha atual (trava race com outro admin)
      3. Valida o `valor` via dispatch table (`validar_valor_por_chave`)
      4. Captura valor_anterior e descricao_anterior para o audit log
      5. Aplica UPDATE em memoria, flush, log_audit, commit
      6. Refresh para retornar os valores server-side

    A2 (auditoria Wave 2 — Sessao 21): try/except em torno de TODAS as
    queries de DB (SELECT FOR UPDATE + flush + log_audit + commit +
    refresh), separado do try/except dedicado a `ConfiguracaoValidationError`
    (422). Commit failure agora retorna 502 (upstream/DB indisponivel),
    nao 500 (bug interno) — consistente com ADR-074 (C07) e ADR-076 (C08).
    HTTPException intencionais (404 whitelist, 404 config ausente, 422
    validation) sao re-levantadas via `except HTTPException: raise`.
    """
    # (1) Whitelist — antes do try/except porque e validacao de URL, nao de DB.
    if chave not in EDITABLE_KEYS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuracao '{chave}' nao existe ou nao e editavel",
        )

    # (2) Validacao do valor — ANTES de qualquer query, em try/except dedicado
    # que mapeia ConfiguracaoValidationError para 422. Separado do bloco de
    # DB porque a classe semantica e diferente (input invalido vs upstream
    # indisponivel).
    try:
        valor_normalizado = validar_valor_por_chave(chave, body.valor)
    except ConfiguracaoValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )

    # (3-6) Bloco unico de queries de DB. Falha transitoria -> 502.
    # HTTPException (404 config ausente) e re-levantada antes do except
    # Exception para nao ser mascarada.
    try:
        # (3) SELECT FOR UPDATE trava a linha contra concorrencia.
        result = await db.execute(
            select(ConfiguracaoSistema)
            .where(ConfiguracaoSistema.chave == chave)
            .with_for_update()
        )
        config = result.scalar_one_or_none()
        if config is None:
            logger.error(
                "PATCH de configuracao whitelisted '%s' mas linha ausente no banco",
                chave,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuracao '{chave}' nao esta cadastrada no sistema",
            )

        # (4) Captura estado anterior para audit log.
        valor_anterior = config.valor
        descricao_anterior = config.descricao

        # (5) Aplica mudanca em memoria.
        config.valor = valor_normalizado
        if body.descricao is not None:
            config.descricao = body.descricao
        config.updated_by = admin.id

        # Flush envia o UPDATE sem commitar; o log_audit tambem.
        await db.flush()

        await log_audit(
            db,
            acao="atualizar_configuracao",
            usuario_id=admin.id,
            prova_id=None,  # configuracoes nao estao ligadas a prova especifica
            detalhes={
                "chave": chave,
                "valor_anterior": valor_anterior,
                "valor_novo": valor_normalizado,
                "descricao_anterior": descricao_anterior,
                "descricao_nova": config.descricao,
            },
            request=request,
        )

        await db.commit()
        await db.refresh(config)
    except HTTPException:
        # Re-raise intencional: 404 de config ausente deve passar intacto.
        # Nao chamamos rollback porque nenhuma mutacao foi aplicada no DB
        # (o SELECT ... FOR UPDATE apenas leu; o raise acontece antes do
        # flush).
        raise
    except Exception:
        await db.rollback()
        logger.exception(
            "Falha ao atualizar configuracao '%s' por admin=%s",
            chave,
            admin.id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao atualizar configuracao",
        )

    logger.info(
        "Configuracao atualizada: chave=%s admin=%s valor_anterior=%r valor_novo=%r",
        chave,
        admin.id,
        valor_anterior,
        valor_normalizado,
    )

    return ConfiguracaoResponse.model_validate(config)
