"""Camada de servico para Interface de Log de Auditoria (Wave 6, Componente 18).

Implementa as queries de leitura sobre `audit_logs` para os endpoints de
listagem (com filtros + paginacao), detalhe (com enriquecimento opcional de
movimentacao relacionada) e historico por prova.

Separado do router para permitir testes unitarios sem HTTP. Todas as funcoes
sao puras (recebem AsyncSession, nao tocam Request/Response).

Sem cache: a UI de auditoria precisa refletir o estado atual da tabela em
tempo real (admin pode estar investigando incidente). Diferente de
report_cache.ReportCache da Wave 5, que cacheia agregacoes idempotentes.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import Text, and_, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AuditLog,
    Movimentacao,
    ProvaDigital,
    Usuario,
)
from app.domain.schemas.audit_log import (
    AuditLogDetailResponse,
    AuditLogItemResponse,
    AuditLogListQuery,
    AuditLogListResponse,
    MAX_BY_PROVA_ITEMS,
    MovimentacaoSnapshot,
)


# ─── Acoes que tem movimentacao espelhada ─────────────────────────────────


_ACOES_COM_MOVIMENTACAO = frozenset({"transitar_status", "reiniciar_ciclo"})
"""Eventos do log que correspondem a 1 linha em `movimentacoes`.

Escrita pelo `executar_transicao` na mesma transacao do log. O detalhe
desses eventos pode ser enriquecido com a `MovimentacaoSnapshot` para
exibir status_anterior/status_novo validados pelo DDL e o boolean
`assinatura_digital_presente`.
"""


# ─── Helpers de aplicacao de filtros ──────────────────────────────────────


def _aplicar_filtros(stmt, query: AuditLogListQuery):
    """Aplica filtros do query schema sobre o stmt SELECT de audit_logs.

    Espera que o stmt ja tenha `AuditLog` no FROM. Filtros sao todos AND.
    Retorna o stmt estendido (imutavel — SQLAlchemy retorna nova instancia).
    """
    if query.from_dt is not None:
        stmt = stmt.where(AuditLog.created_at >= query.from_dt)
    if query.to_dt is not None:
        stmt = stmt.where(AuditLog.created_at < query.to_dt)
    if query.prova_id is not None:
        stmt = stmt.where(AuditLog.prova_id == query.prova_id)
    if query.usuario_id is not None:
        stmt = stmt.where(AuditLog.usuario_id == query.usuario_id)
    if query.acao is not None:
        stmt = stmt.where(AuditLog.acao == query.acao)
    if query.q is not None:
        # Busca textual em detalhes_json::text via ILIKE.
        # Postgres permite cast direto: `detalhes_json::text ILIKE pattern`.
        # Sem escape de wildcards (%, _) — admin-only, baixo risco;
        # consistente com Wave 5 reports.py que tambem usa ILIKE.
        pattern = f"%{query.q}%"
        stmt = stmt.where(cast(AuditLog.detalhes_json, Text).ilike(pattern))
    return stmt


# ─── Listagem paginada ────────────────────────────────────────────────────


async def listar_audit_logs(
    db: AsyncSession, query: AuditLogListQuery
) -> AuditLogListResponse:
    """Lista audit_logs com filtros + paginacao + JOINs para enriquecimento.

    Executa 2 queries:
      1. SELECT items com JOIN para usuarios (nome, setor) e
         provas_digitais (nro_requerimento), com filtros + LIMIT/OFFSET.
      2. SELECT count(*) com mesmos filtros (para `total`).

    A query de items inclui ORDER BY created_at conforme `query.sort`.
    A query de count nao precisa de ORDER BY.

    Indice usado pelo planner: `idx_audit_created_at` (created_at) cobre
    ORDER BY DESC + LIMIT. Filtros adicionais reduzem o conjunto antes do
    sort se houver indice especifico (idx_audit_acao, idx_audit_prova,
    idx_audit_usuario).
    """
    # Query principal — items.
    stmt = (
        select(
            AuditLog.id,
            AuditLog.acao,
            AuditLog.prova_id,
            AuditLog.usuario_id,
            AuditLog.detalhes_json,
            AuditLog.ip_address,
            AuditLog.user_agent,
            AuditLog.created_at,
            Usuario.nome.label("usuario_nome"),
            Usuario.setor.label("usuario_setor"),
            ProvaDigital.nro_requerimento.label("prova_nro_requerimento"),
        )
        .join(Usuario, Usuario.id == AuditLog.usuario_id)
        .outerjoin(ProvaDigital, ProvaDigital.id == AuditLog.prova_id)
    )
    stmt = _aplicar_filtros(stmt, query)

    # Ordenacao por created_at — sort='asc' ou 'desc' (validado pelo schema).
    if query.sort == "asc":
        stmt = stmt.order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
    else:
        stmt = stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())

    # Paginacao.
    offset = (query.page - 1) * query.page_size
    stmt = stmt.limit(query.page_size).offset(offset)

    rows = (await db.execute(stmt)).all()

    items = [
        AuditLogItemResponse(
            id=row.id,
            acao=row.acao,
            prova_id=row.prova_id,
            prova_nro_requerimento=row.prova_nro_requerimento,
            usuario_id=row.usuario_id,
            usuario_nome=row.usuario_nome,
            usuario_setor=row.usuario_setor,
            detalhes_json=row.detalhes_json,
            ip_address=str(row.ip_address) if row.ip_address is not None else None,
            user_agent=row.user_agent,
            created_at=row.created_at,
        )
        for row in rows
    ]

    # Query de count — mesmos filtros, sem JOINs nem ORDER BY.
    count_stmt = select(func.count(AuditLog.id))
    count_stmt = _aplicar_filtros(count_stmt, query)
    total = (await db.execute(count_stmt)).scalar_one()

    return AuditLogListResponse(
        items=items,
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


# ─── Detalhe individual ───────────────────────────────────────────────────


async def buscar_audit_log_detalhe(
    db: AsyncSession, audit_log_id: UUID
) -> AuditLogDetailResponse | None:
    """Carrega detalhe de um audit_log pelo id, com enriquecimento opcional
    de movimentacao relacionada quando `acao` for transitar_status ou
    reiniciar_ciclo.

    Retorna None se o id nao existir (caller traduz para 404).
    """
    stmt = (
        select(
            AuditLog.id,
            AuditLog.acao,
            AuditLog.prova_id,
            AuditLog.usuario_id,
            AuditLog.detalhes_json,
            AuditLog.ip_address,
            AuditLog.user_agent,
            AuditLog.created_at,
            Usuario.nome.label("usuario_nome"),
            Usuario.setor.label("usuario_setor"),
            ProvaDigital.nro_requerimento.label("prova_nro_requerimento"),
        )
        .join(Usuario, Usuario.id == AuditLog.usuario_id)
        .outerjoin(ProvaDigital, ProvaDigital.id == AuditLog.prova_id)
        .where(AuditLog.id == audit_log_id)
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        return None

    movimentacao_relacionada = None
    if row.acao in _ACOES_COM_MOVIMENTACAO and row.prova_id is not None:
        movimentacao_relacionada = await _find_movimentacao_relacionada(
            db,
            prova_id=row.prova_id,
            audit_created_at=row.created_at,
            detalhes_json=row.detalhes_json,
        )

    return AuditLogDetailResponse(
        id=row.id,
        acao=row.acao,
        prova_id=row.prova_id,
        prova_nro_requerimento=row.prova_nro_requerimento,
        usuario_id=row.usuario_id,
        usuario_nome=row.usuario_nome,
        usuario_setor=row.usuario_setor,
        detalhes_json=row.detalhes_json,
        ip_address=str(row.ip_address) if row.ip_address is not None else None,
        user_agent=row.user_agent,
        created_at=row.created_at,
        movimentacao_relacionada=movimentacao_relacionada,
    )


async def _find_movimentacao_relacionada(
    db: AsyncSession,
    *,
    prova_id: UUID,
    audit_created_at: Any,
    detalhes_json: dict[str, Any] | None,
) -> MovimentacaoSnapshot | None:
    """Encontra a movimentacao correspondente a um audit_log de transicao.

    Estrategia (D2 do analysis.md — opcao A endurecida):
      Matching tripla: prova_id + status_novo (de detalhes_json.para) +
      ciclo (de detalhes_json.ciclo) com janela de +/- 5s em created_at.

    Por que 3 chaves + janela ±5s:
      - `executar_transicao` insere movimentacoes e audit_log na mesma
        transacao; created_at dos dois nao e identico (1 vem de
        datetime.now(), outro de now()), mas a diferenca e na ordem
        de microssegundos. Janela ±5s e folga generosa.
      - 2 transicoes da mesma prova em <5s sao operacionalmente raras
        (operacoes fisicas levam minutos/horas). Mas se ocorrerem,
        status_novo + ciclo desambiguam (cada transicao tem (status_novo,
        ciclo) unico no curto prazo).

    Se detalhes_json nao tem `para` ou `ciclo` (formatos antigos ou novos
    valores de acao), retorna None silenciosamente — o detalhe ainda e
    valido sem o enriquecimento.
    """
    if not detalhes_json:
        return None
    para_str = detalhes_json.get("para")
    ciclo = detalhes_json.get("ciclo")
    if para_str is None or ciclo is None:
        return None

    janela = timedelta(seconds=5)
    stmt = (
        select(Movimentacao)
        .where(
            and_(
                Movimentacao.prova_id == prova_id,
                Movimentacao.status_novo == para_str,
                Movimentacao.ciclo == ciclo,
                Movimentacao.created_at >= audit_created_at - janela,
                Movimentacao.created_at <= audit_created_at + janela,
            )
        )
        .order_by(
            # Ordem prioriza menor delta de created_at — em caso de
            # multiplos matches (improvavel), escolhe o mais proximo.
            func.abs(
                func.extract("epoch", Movimentacao.created_at - audit_created_at)
            )
        )
        .limit(1)
    )
    mov = (await db.execute(stmt)).scalar_one_or_none()
    if mov is None:
        return None

    return MovimentacaoSnapshot(
        id=mov.id,
        status_anterior=mov.status_anterior,
        status_novo=mov.status_novo,
        motivo_reprovacao=mov.motivo_reprovacao,
        ciclo=mov.ciclo,
        rota_no_momento=mov.rota_no_momento,
        # Garantia de privacidade: BYTEA nunca vai pro response. Apenas
        # confirma que a assinatura existe e e nao-vazia (RN-003).
        assinatura_digital_presente=(
            mov.assinatura_digital is not None and len(mov.assinatura_digital) > 0
        ),
        created_at=mov.created_at,
    )


# ─── Historico por prova ──────────────────────────────────────────────────


async def listar_audit_logs_por_prova(
    db: AsyncSession, prova_id: UUID, sort: str = "asc"
) -> AuditLogListResponse:
    """Carrega todo o historico de audit_logs de uma prova, sem paginacao.

    Hard cap defensivo em MAX_BY_PROVA_ITEMS (500) — sentinela para
    investigacao caso uma prova tenha historico anormalmente grande.

    Sort default 'asc' (cronologico) porque o caso de uso primario e
    "como esta prova evoluiu" — leitura sequencial. Se sort='desc',
    inverte para "ultimo evento primeiro".

    NAO verifica se a prova existe — caller (router) faz essa checagem
    via parse_prova_id ou similar para retornar 404 antes de chegar aqui.
    """
    stmt = (
        select(
            AuditLog.id,
            AuditLog.acao,
            AuditLog.prova_id,
            AuditLog.usuario_id,
            AuditLog.detalhes_json,
            AuditLog.ip_address,
            AuditLog.user_agent,
            AuditLog.created_at,
            Usuario.nome.label("usuario_nome"),
            Usuario.setor.label("usuario_setor"),
            ProvaDigital.nro_requerimento.label("prova_nro_requerimento"),
        )
        .join(Usuario, Usuario.id == AuditLog.usuario_id)
        .outerjoin(ProvaDigital, ProvaDigital.id == AuditLog.prova_id)
        .where(AuditLog.prova_id == prova_id)
    )

    if sort == "desc":
        stmt = stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    else:
        stmt = stmt.order_by(AuditLog.created_at.asc(), AuditLog.id.asc())

    stmt = stmt.limit(MAX_BY_PROVA_ITEMS)

    rows = (await db.execute(stmt)).all()

    items = [
        AuditLogItemResponse(
            id=row.id,
            acao=row.acao,
            prova_id=row.prova_id,
            prova_nro_requerimento=row.prova_nro_requerimento,
            usuario_id=row.usuario_id,
            usuario_nome=row.usuario_nome,
            usuario_setor=row.usuario_setor,
            detalhes_json=row.detalhes_json,
            ip_address=str(row.ip_address) if row.ip_address is not None else None,
            user_agent=row.user_agent,
            created_at=row.created_at,
        )
        for row in rows
    ]

    return AuditLogListResponse(
        items=items,
        total=len(items),
        page=1,
        page_size=MAX_BY_PROVA_ITEMS,
    )


# ─── Existencia da prova ──────────────────────────────────────────────────


async def prova_existe(db: AsyncSession, prova_id: UUID) -> bool:
    """Verifica existencia da prova — usado pelo router para 404 antes de
    listar audit_logs por prova.

    Admin ve todas as provas (sem scoping), entao basta um SELECT 1.
    """
    stmt = select(ProvaDigital.id).where(ProvaDigital.id == prova_id).limit(1)
    return (await db.execute(stmt)).scalar_one_or_none() is not None
