"""Router de Relatorios Gerenciais (Wave 5, Componente 16).

Implementa RF-013, RF-015, US-014 com endpoint UNICO discriminado por
`scope` (geral|3studio|vendedores|clicheria) + endpoint dedicado de
exportacao CSV streaming.

Estrategia 'minimizar queries' (WAVE5_ANALYSIS §4.4):
  - Cache in-memory TTL 60s por hash dos filtros (`ReportCache`).
  - ETag SHA-256 deterministico => `If-None-Match` => 304 sem reserializar.
  - Cache-Control: private, max-age=30, stale-while-revalidate=60.
  - SQLAlchemy compiled cache (gratuito).
  - Realtime invalida cache do front (Wave 4 reuse).

RBAC: todos os endpoints exigem `is_admin=true` (US-014).

Auditoria (RNF-005, ADR-095/099):
  - GET /reports: NAO loga (consulta cacheada e idempotente).
  - GET /reports/export: insere `audit_logs.acao=REPORT_EXPORTED` antes
    do streaming (commit imediato — auditavel mesmo se download abortar).

Tempos calculados em horas CORRIDAS (ADR-091, ADR-099 — desvio explicito
do RN-008 literal, alinhado com Wave 4 Dashboard).
"""
from __future__ import annotations

import csv
import io
import logging
import uuid
from collections.abc import AsyncIterator, Iterable
from datetime import datetime, timezone
from typing import Any, Literal
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import (
    Float,
    and_,
    cast,
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user
from app.db.models import (
    ConfiguracaoSistema,
    LocalizacaoEnum,
    Movimentacao,
    ProvaDigital,
    RotaEnum,
    SetorEnum,
    StatusProvaEnum,
    Usuario,
)
from app.db.session import get_db
from app.domain.schemas.report import (
    CancelamentoTop,
    DistLocalizacao,
    DistOrigemRota,
    DistRota,
    DistStatus,
    Indicadores3Studio,
    IndicadoresClicheria,
    IndicadoresGeral,
    PeriodoMeta,
    PontoSerie,
    ProvaAtrasadaItem,
    ReportResponse3Studio,
    ReportResponseClicheria,
    ReportResponseGeral,
    ReportResponseVendedores,
    VendedorAtrasoAtual,
    VendedorMetrica,
)
from app.services.audit_service import log_audit
from app.services.report_cache import ReportCache, get_default_cache
from app.services.report_etag import compute_etag, matches_if_none_match
from app.services.report_filters import (
    MAX_Q_LENGTH,
    ReportFilters,
    ReportScope,
    to_cache_key,
)
from app.services.report_metrics import (
    arredondar_horas,
    calcular_total_dias,
    limite_atraso,
    media_diaria,
    taxa,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Constantes ────────────────────────────────────────────────────────────


_TERMINAL_STATUSES = (
    StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
    StatusProvaEnum.CANCELADA,
)
"""Status terminais — provas atrasadas excluem essas (RN-008 ADR-099)."""

_CLICHERIA_EM_TRANSITO = (
    StatusProvaEnum.COM_MOTORISTA,
    StatusProvaEnum.ENVIADA_PARA_CLICHERIA,
    StatusProvaEnum.ENCAMINHADA_A_CLICHERIA,
)

_VENDEDOR_EM_PODER = (
    StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
    StatusProvaEnum.APROVADA_PELO_VENDEDOR,
)

ExportDataset = Literal["summary", "by-seller", "overdue", "proofs"]
"""Datasets exportaveis em CSV."""

CSV_BOM = "\ufeff"
"""UTF-8 BOM — Excel abrir acentos sem mojibake."""

CSV_TRUNCATE_LIMIT = 100_000
"""Limite hard de linhas no export para evitar arquivos gigantes."""

CSV_BATCH_SIZE = 500
"""Tamanho do chunk lido pelo cursor server-side em datasets grandes."""

CACHE_CONTROL_HEADER = "private, max-age=30, stale-while-revalidate=60"
"""Cliente pode reusar resposta por 30s sem revalidar; 30s adicionais com
revalidacao em background."""


# ─── Helpers ───────────────────────────────────────────────────────────────


async def _resolve_filters(
    *,
    scope: ReportScope,
    from_dt: datetime | None,
    to_dt: datetime | None,
    q: str | None,
    vendedor_id: uuid.UUID | None,
    rota: RotaEnum | None,
    status_filter: StatusProvaEnum | None,
) -> ReportFilters:
    """Constroi o ReportFilters validado a partir dos query params crus.

    Pydantic faz toda a validacao: defaults (30d), invariantes (from < to,
    range <= 366d, q max 200 chars). Erros viram 422 via FastAPI.
    """
    return ReportFilters.model_validate(
        {
            "scope": scope,
            "from": from_dt,
            "to": to_dt,
            "q": q,
            "vendedor_id": vendedor_id,
            "rota": rota,
            "status": status_filter,
        }
    )


async def _read_tempo_atraso(db: AsyncSession) -> int:
    """Le `tempo_atraso_horas_uteis` da tabela configuracoes_sistema.

    Espelha o helper do dashboard (ADR-099 — horas corridas, mantem nome
    legacy). Fallback 48h se valor invalido/ausente.
    """
    cfg_stmt = select(ConfiguracaoSistema.valor).where(
        ConfiguracaoSistema.chave == "tempo_atraso_horas_uteis"
    )
    raw = (await db.execute(cfg_stmt)).scalar_one_or_none()
    try:
        valor = int(raw) if raw is not None else 48
    except (ValueError, TypeError):
        valor = 48
    return max(1, valor)


def _ultima_mov_subq():
    """Subquery correlacionada: ultima movimentacao por prova.

    Usada para calcular 'atrasadas' (ADR-099). Indexada por
    `idx_movimentacoes_prova_data (prova_id, created_at DESC)`.
    """
    return (
        select(func.max(Movimentacao.created_at))
        .where(Movimentacao.prova_id == ProvaDigital.id)
        .correlate(ProvaDigital)
        .scalar_subquery()
    )


def _periodo_filter(filters: ReportFilters):
    """Clausula WHERE de `created_at` para a tabela `provas_digitais`."""
    return and_(
        ProvaDigital.created_at >= filters.from_,
        ProvaDigital.created_at < filters.to,
    )


def _movimentacao_periodo_filter(filters: ReportFilters):
    """Clausula WHERE de `created_at` para a tabela `movimentacoes`."""
    return and_(
        Movimentacao.created_at >= filters.from_,
        Movimentacao.created_at < filters.to,
    )


def _aplicar_filtros_provas(stmt, filters: ReportFilters):
    """Aplica filtros opcionais (q, vendedor_id, rota, status) sobre provas_digitais."""
    if filters.vendedor_id is not None:
        stmt = stmt.where(ProvaDigital.vendedor_id == filters.vendedor_id)
    if filters.rota is not None:
        stmt = stmt.where(ProvaDigital.rota == filters.rota)
    if filters.status is not None:
        stmt = stmt.where(ProvaDigital.status == filters.status)
    if filters.q:
        # Busca textual em nome/cliente/nro_requerimento (ILIKE).
        # Sem escape de wildcards (admin-only, baixo risco).
        pattern = f"%{filters.q}%"
        stmt = stmt.where(
            or_(
                ProvaDigital.nome.ilike(pattern),
                ProvaDigital.cliente.ilike(pattern),
                ProvaDigital.nro_requerimento.ilike(pattern),
            )
        )
    return stmt


async def _query_ranking_vendedores(
    filters: ReportFilters, db: AsyncSession, cutoff: datetime
) -> tuple[list[VendedorMetrica], int, int]:
    """Calcula ranking de vendedores + totals por localizacao.

    Compartilhado entre `_aggregate_geral` (apenas ranking) e
    `_aggregate_vendedores` (ranking + totais para DistLocalizacao).

    3 subqueries internas:
      a) `volume_subq`: provas criadas no periodo, group by vendedor.
      b) `decisoes_subq`: pares (RETIRADA, DECISAO) por ciclo, group by vendedor —
         retorna aprovacoes, reprovacoes, tempo medio.
      c) `atrasadas_subq`: snapshot de provas em poder do vendedor com
         ultima_mov < cutoff (RN-008/ADR-099).

    Final: JOIN das 3 subqueries com `usuarios` filtrando setor=VENDEDOR e
    ativo=true. Ordenado por volume DESC, nome ASC. Limit 200.

    Returns:
        (ranking, matriz_total, filial_total) onde os totais sao a soma
        do `volume` por localizacao.
    """
    retirada_subq = (
        select(
            Movimentacao.prova_id,
            Movimentacao.ciclo,
            func.min(Movimentacao.created_at).label("retirada_at"),
        )
        .where(Movimentacao.status_novo == StatusProvaEnum.RETIRADA_PELO_VENDEDOR)
        .group_by(Movimentacao.prova_id, Movimentacao.ciclo)
        .subquery()
    )
    delta_dec = func.extract(
        "epoch", Movimentacao.created_at - retirada_subq.c.retirada_at
    )

    decisoes_subq = (
        select(
            ProvaDigital.vendedor_id.label("vid"),
            func.count(Movimentacao.id).label("decisoes"),
            func.count(Movimentacao.id)
            .filter(
                Movimentacao.status_novo == StatusProvaEnum.APROVADA_PELO_VENDEDOR
            )
            .label("aprovacoes"),
            func.count(Movimentacao.id)
            .filter(
                Movimentacao.status_novo == StatusProvaEnum.REPROVADA_PELO_VENDEDOR
            )
            .label("reprovacoes"),
            func.avg(delta_dec).label("media_dec_seg"),
        )
        .select_from(Movimentacao)
        .join(ProvaDigital, ProvaDigital.id == Movimentacao.prova_id)
        .join(
            retirada_subq,
            and_(
                retirada_subq.c.prova_id == Movimentacao.prova_id,
                retirada_subq.c.ciclo == Movimentacao.ciclo,
            ),
        )
        .where(
            Movimentacao.status_novo.in_(
                (
                    StatusProvaEnum.APROVADA_PELO_VENDEDOR,
                    StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
                )
            ),
            Movimentacao.created_at >= filters.from_,
            Movimentacao.created_at < filters.to,
        )
        .group_by(ProvaDigital.vendedor_id)
        .subquery()
    )

    volume_subq = (
        select(
            ProvaDigital.vendedor_id.label("vid"),
            func.count().label("vol"),
        )
        .where(_periodo_filter(filters))
        .group_by(ProvaDigital.vendedor_id)
        .subquery()
    )

    ultima_mov = _ultima_mov_subq()
    atrasadas_subq = (
        select(
            ProvaDigital.vendedor_id.label("vid"),
            func.count().label("qtd_atrasadas"),
        )
        .where(
            ProvaDigital.status.in_(_VENDEDOR_EM_PODER),
            func.coalesce(ultima_mov, ProvaDigital.created_at) < cutoff,
        )
        .group_by(ProvaDigital.vendedor_id)
        .subquery()
    )

    stmt_ranking = (
        select(
            Usuario.id.label("vendedor_id"),
            Usuario.nome,
            Usuario.localizacao,
            func.coalesce(volume_subq.c.vol, 0).label("volume"),
            func.coalesce(decisoes_subq.c.aprovacoes, 0).label("aprovacoes"),
            func.coalesce(decisoes_subq.c.reprovacoes, 0).label("reprovacoes"),
            decisoes_subq.c.media_dec_seg,
            func.coalesce(atrasadas_subq.c.qtd_atrasadas, 0).label("qtd_atrasadas"),
        )
        .select_from(Usuario)
        .outerjoin(volume_subq, volume_subq.c.vid == Usuario.id)
        .outerjoin(decisoes_subq, decisoes_subq.c.vid == Usuario.id)
        .outerjoin(atrasadas_subq, atrasadas_subq.c.vid == Usuario.id)
        .where(Usuario.setor == SetorEnum.VENDEDOR, Usuario.ativo.is_(True))
        .order_by(func.coalesce(volume_subq.c.vol, 0).desc(), Usuario.nome.asc())
        .limit(200)
    )
    if filters.vendedor_id is not None:
        stmt_ranking = stmt_ranking.where(Usuario.id == filters.vendedor_id)
    rows = (await db.execute(stmt_ranking)).all()

    ranking: list[VendedorMetrica] = []
    matriz_total = 0
    filial_total = 0
    for r in rows:
        aprov = int(r.aprovacoes)
        reprov = int(r.reprovacoes)
        decisoes = aprov + reprov
        ranking.append(
            VendedorMetrica(
                vendedor_id=r.vendedor_id,
                vendedor_nome=r.nome,
                localizacao=r.localizacao,
                volume=int(r.volume),
                aprovacoes=aprov,
                reprovacoes=reprov,
                taxa_aprovacao=round(taxa(aprov, decisoes), 4),
                taxa_reprovacao=round(taxa(reprov, decisoes), 4),
                tempo_medio_retirada_a_decisao_horas=arredondar_horas(
                    (float(r.media_dec_seg) / 3600.0)
                    if r.media_dec_seg is not None
                    else None
                ),
                provas_atrasadas_em_poder=int(r.qtd_atrasadas),
            )
        )
        if r.localizacao == LocalizacaoEnum.MATRIZ:
            matriz_total += int(r.volume)
        elif r.localizacao == LocalizacaoEnum.FILIAL:
            filial_total += int(r.volume)

    return ranking, matriz_total, filial_total


async def _query_provas_atrasadas(
    db: AsyncSession, *, cutoff: datetime, now_utc: datetime, limit: int
) -> tuple[list[ProvaAtrasadaItem], int]:
    """Snapshot das provas atualmente atrasadas (RN-008/ADR-099, horas corridas).

    Retorna (lista_top_N, total_sem_cap). Lista ordenada por
    `ultima_movimentacao_at` ASC (mais antigas primeiro). `total_sem_cap`
    permite UI exibir 'Provas Atrasadas (N)' mesmo com lista capada.

    Reusa a SQL do `_stream_overdue` (linha por prova) — mesmas garantias
    de uso de indices (idx_movimentacoes_prova_data, idx_provas_status).
    """
    ultima_mov = _ultima_mov_subq()
    coalesced = func.coalesce(ultima_mov, ProvaDigital.created_at)
    horas_atrasada_expr = cast(
        func.extract("epoch", now_utc - coalesced) / 3600.0, Float
    )

    base_filter = and_(
        ProvaDigital.status.not_in(_TERMINAL_STATUSES),
        coalesced < cutoff,
    )

    # Q1: contagem total (sem limit)
    stmt_total = select(func.count()).select_from(ProvaDigital).where(base_filter)
    total = int((await db.execute(stmt_total)).scalar_one() or 0)

    if total == 0:
        return [], 0

    # Q2: top N detalhada
    stmt_lista = (
        select(
            ProvaDigital.id,
            ProvaDigital.nome,
            ProvaDigital.nro_requerimento,
            ProvaDigital.cliente,
            Usuario.nome.label("vendedor_nome"),
            ProvaDigital.status,
            horas_atrasada_expr.label("horas_atrasada"),
            coalesced.label("ultima_at"),
        )
        .select_from(ProvaDigital)
        .join(Usuario, Usuario.id == ProvaDigital.vendedor_id)
        .where(base_filter)
        .order_by(coalesced.asc())
        .limit(limit)
    )
    rows = (await db.execute(stmt_lista)).all()

    items = [
        ProvaAtrasadaItem(
            id=r.id,
            nome=r.nome,
            nro_requerimento=r.nro_requerimento,
            cliente=r.cliente,
            vendedor_nome=r.vendedor_nome,
            status=r.status,
            horas_atrasada=round(float(r.horas_atrasada), 2),
            ultima_movimentacao_at=r.ultima_at,
        )
        for r in rows
    ]
    return items, total


# ─── Agregadores por scope ────────────────────────────────────────────────


async def _aggregate_geral(
    filters: ReportFilters, db: AsyncSession
) -> ReportResponseGeral:
    """Agrega indicadores da perspectiva 'geral' (visao consolidada).

    Queries:
      Q1: contadores por status + rota (sobre provas no periodo).
      Q2: serie temporal (provas/dia).
      Q3: tempo medio + mediano de ciclo (criacao->conclusao).
      Q4: tempo medio aprovacao (RETIRADA -> APROVADA/REPROVADA por ciclo)
          + taxa de reprovacao sobre ciclos (ADR-101).
      Q5: snapshot atrasadas (sem filtro de periodo).
      Q6: leitura tempo_atraso_horas (config).

    Total: 6 queries leves (vs N+1 que cresceria com indicadores).
    """
    tempo_atraso_horas = await _read_tempo_atraso(db)
    now_utc = datetime.now(timezone.utc)
    cutoff = limite_atraso(now_utc, tempo_atraso_horas)

    # Q1+Q2: contadores e serie temporal — provas no periodo
    stmt_provas = (
        select(
            func.count().label("total"),
            *[
                func.count()
                .filter(ProvaDigital.status == s)
                .label(f"status_{s.value}")
                for s in StatusProvaEnum
            ],
            func.count()
            .filter(ProvaDigital.rota == RotaEnum.PADRAO)
            .label("rota_padrao"),
            func.count()
            .filter(ProvaDigital.rota == RotaEnum.DIRETA)
            .label("rota_direta"),
            func.count()
            .filter(ProvaDigital.rota.is_(None))
            .label("rota_nula"),
        )
        .select_from(ProvaDigital)
        .where(_periodo_filter(filters))
    )
    stmt_provas = _aplicar_filtros_provas(stmt_provas, filters)
    row_provas = (await db.execute(stmt_provas)).one()

    # Q2: serie temporal por dia (UTC)
    bucket = func.date_trunc("day", ProvaDigital.created_at).label("bucket")
    stmt_serie = (
        select(bucket, func.count().label("qtd"))
        .select_from(ProvaDigital)
        .where(_periodo_filter(filters))
        .group_by(bucket)
        .order_by(bucket)
    )
    stmt_serie = _aplicar_filtros_provas(stmt_serie, filters)
    serie_rows = (await db.execute(stmt_serie)).all()

    # Q3: tempo medio + mediano de ciclo
    # Provas concluidas no periodo => par (created_at_prova, mov_recebida.created_at)
    # FILTROS de provas (q, vendedor_id, etc) tambem aplicam aqui via JOIN.
    delta_ciclo = func.extract(
        "epoch", Movimentacao.created_at - ProvaDigital.created_at
    )
    stmt_ciclo = (
        select(
            func.avg(delta_ciclo).label("media_seg"),
            func.percentile_cont(0.5)
            .within_group(delta_ciclo)
            .label("mediana_seg"),
        )
        .select_from(Movimentacao)
        .join(ProvaDigital, ProvaDigital.id == Movimentacao.prova_id)
        .where(
            Movimentacao.status_novo == StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
            Movimentacao.created_at >= filters.from_,
            Movimentacao.created_at < filters.to,
        )
    )
    stmt_ciclo = _aplicar_filtros_provas(stmt_ciclo, filters)
    ciclo_row = (await db.execute(stmt_ciclo)).one_or_none()
    media_ciclo_seg = ciclo_row.media_seg if ciclo_row else None
    mediana_ciclo_seg = ciclo_row.mediana_seg if ciclo_row else None

    # Q4: tempo medio aprovacao + taxa de reprovacao sobre ciclos.
    # Pares (RETIRADA, APROVADA|REPROVADA) por (prova_id, ciclo).
    retirada_subq = (
        select(
            Movimentacao.prova_id,
            Movimentacao.ciclo,
            func.min(Movimentacao.created_at).label("retirada_at"),
        )
        .where(Movimentacao.status_novo == StatusProvaEnum.RETIRADA_PELO_VENDEDOR)
        .group_by(Movimentacao.prova_id, Movimentacao.ciclo)
        .subquery()
    )
    decisao_alias = Movimentacao
    stmt_aprov = (
        select(
            func.avg(
                func.extract(
                    "epoch", decisao_alias.created_at - retirada_subq.c.retirada_at
                )
            ).label("media_seg"),
            func.count()
            .filter(decisao_alias.status_novo == StatusProvaEnum.APROVADA_PELO_VENDEDOR)
            .label("aprovacoes"),
            func.count()
            .filter(decisao_alias.status_novo == StatusProvaEnum.REPROVADA_PELO_VENDEDOR)
            .label("reprovacoes"),
        )
        .select_from(decisao_alias)
        .join(
            retirada_subq,
            and_(
                retirada_subq.c.prova_id == decisao_alias.prova_id,
                retirada_subq.c.ciclo == decisao_alias.ciclo,
            ),
        )
        .where(
            decisao_alias.status_novo.in_(
                (
                    StatusProvaEnum.APROVADA_PELO_VENDEDOR,
                    StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
                )
            ),
            decisao_alias.created_at >= filters.from_,
            decisao_alias.created_at < filters.to,
        )
    )
    aprov_row = (await db.execute(stmt_aprov)).one_or_none()
    media_aprov_seg = aprov_row.media_seg if aprov_row else None
    aprovacoes = aprov_row.aprovacoes if aprov_row else 0
    reprovacoes = aprov_row.reprovacoes if aprov_row else 0
    total_decididos = aprovacoes + reprovacoes
    taxa_reprovacao = taxa(reprovacoes, total_decididos)

    # Q5: snapshot atrasadas (nao filtrado por periodo — momento atual)
    # + lista detalhada top 20 (ProvaAtrasadaItem)
    provas_atrasadas, qtd_atrasadas = await _query_provas_atrasadas(
        db, cutoff=cutoff, now_utc=now_utc, limit=20
    )

    # Q6: ranking de vendedores no periodo (helper compartilhado com scope=vendedores)
    ranking, _matriz_total, _filial_total = await _query_ranking_vendedores(
        filters, db, cutoff=cutoff
    )

    # ── Montar response ──────────────────────────────────────────────────
    indicadores = IndicadoresGeral(
        total_provas=int(row_provas.total),
        tempo_medio_ciclo_horas=arredondar_horas(
            (float(media_ciclo_seg) / 3600.0) if media_ciclo_seg is not None else None
        ),
        tempo_mediano_ciclo_horas=arredondar_horas(
            (float(mediana_ciclo_seg) / 3600.0)
            if mediana_ciclo_seg is not None
            else None
        ),
        tempo_medio_aprovacao_horas=arredondar_horas(
            (float(media_aprov_seg) / 3600.0) if media_aprov_seg is not None else None
        ),
        taxa_reprovacao=round(taxa_reprovacao, 4),
        qtd_atrasadas=qtd_atrasadas,
    )

    distribuicao_status = [
        DistStatus(status=s, quantidade=int(getattr(row_provas, f"status_{s.value}")))
        for s in StatusProvaEnum
        if int(getattr(row_provas, f"status_{s.value}")) > 0
    ]

    distribuicao_rota: list[DistRota] = []
    if int(row_provas.rota_padrao) > 0:
        distribuicao_rota.append(
            DistRota(rota=RotaEnum.PADRAO, quantidade=int(row_provas.rota_padrao))
        )
    if int(row_provas.rota_direta) > 0:
        distribuicao_rota.append(
            DistRota(rota=RotaEnum.DIRETA, quantidade=int(row_provas.rota_direta))
        )
    if int(row_provas.rota_nula) > 0:
        distribuicao_rota.append(
            DistRota(rota=None, quantidade=int(row_provas.rota_nula))
        )

    serie_temporal = [
        PontoSerie(data=r.bucket, quantidade=int(r.qtd)) for r in serie_rows
    ]

    return ReportResponseGeral(
        periodo=PeriodoMeta(
            from_=filters.from_,
            to=filters.to,
            total_dias=calcular_total_dias(filters.from_, filters.to),
        ),
        indicadores=indicadores,
        serie_temporal=serie_temporal,
        distribuicao_status=distribuicao_status,
        distribuicao_rota=distribuicao_rota,
        ranking=ranking,
        provas_atrasadas=provas_atrasadas,
        provas_atrasadas_total=qtd_atrasadas,
        atualizado_em=now_utc,
    )


async def _aggregate_3studio(
    filters: ReportFilters, db: AsyncSession
) -> ReportResponse3Studio:
    """Agrega indicadores da perspectiva '3studio' (operacao interna)."""
    now_utc = datetime.now(timezone.utc)
    total_dias = calcular_total_dias(filters.from_, filters.to)

    # Q1: agregados sobre provas no periodo (criadas)
    stmt_provas = (
        select(func.count().label("provas_criadas"))
        .select_from(ProvaDigital)
        .where(_periodo_filter(filters))
    )
    stmt_provas = _aplicar_filtros_provas(stmt_provas, filters)
    provas_criadas = int((await db.execute(stmt_provas)).scalar_one())

    # Q2: agregados sobre movimentacoes no periodo
    stmt_movs = (
        select(
            func.count()
            .filter(
                and_(
                    Movimentacao.status_anterior
                    == StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
                    Movimentacao.status_novo == StatusProvaEnum.CRIADA,
                )
            )
            .label("reinicios"),
            func.count()
            .filter(Movimentacao.status_novo == StatusProvaEnum.COM_MOTORISTA)
            .label("devolvidas_motorista"),
            func.count()
            .filter(Movimentacao.status_novo == StatusProvaEnum.CANCELADA)
            .label("cancelamentos"),
        )
        .select_from(Movimentacao)
        .where(_movimentacao_periodo_filter(filters))
    )
    movs_row = (await db.execute(stmt_movs)).one()

    # Q3: snapshot — reprovadas aguardando acao (estado atual, nao filtrado por periodo)
    stmt_repr = select(func.count()).where(
        ProvaDigital.status == StatusProvaEnum.REPROVADA_PELO_VENDEDOR
    )
    reprovadas_aguardando = int((await db.execute(stmt_repr)).scalar_one() or 0)

    # Q4: tempo medio criacao -> primeira mov, sobre provas criadas no periodo
    primeira_mov_subq = (
        select(
            Movimentacao.prova_id,
            func.min(Movimentacao.created_at).label("primeira_at"),
        )
        .group_by(Movimentacao.prova_id)
        .subquery()
    )
    delta_first = func.extract(
        "epoch", primeira_mov_subq.c.primeira_at - ProvaDigital.created_at
    )
    stmt_resp = (
        select(func.avg(delta_first).label("media_seg"))
        .select_from(ProvaDigital)
        .join(primeira_mov_subq, primeira_mov_subq.c.prova_id == ProvaDigital.id)
        .where(_periodo_filter(filters))
    )
    stmt_resp = _aplicar_filtros_provas(stmt_resp, filters)
    resp_row = (await db.execute(stmt_resp)).one_or_none()
    media_resp_seg = resp_row.media_seg if resp_row else None

    # Q5: top motivos de cancelamento no periodo
    stmt_top = (
        select(
            ProvaDigital.motivo_cancelamento.label("motivo"),
            func.count().label("qtd"),
        )
        .select_from(ProvaDigital)
        .where(
            ProvaDigital.status == StatusProvaEnum.CANCELADA,
            ProvaDigital.motivo_cancelamento.isnot(None),
            _periodo_filter(filters),
        )
        .group_by(ProvaDigital.motivo_cancelamento)
        .order_by(func.count().desc())
        .limit(10)
    )
    top_rows = (await db.execute(stmt_top)).all()

    indicadores = Indicadores3Studio(
        provas_criadas=provas_criadas,
        media_diaria_criacao=media_diaria(provas_criadas, total_dias),
        reinicios_de_ciclo=int(movs_row.reinicios),
        devolvidas_motorista=int(movs_row.devolvidas_motorista),
        reprovadas_aguardando_acao=reprovadas_aguardando,
        cancelamentos=int(movs_row.cancelamentos),
        tempo_medio_criacao_ate_primeira_mov_horas=arredondar_horas(
            (float(media_resp_seg) / 3600.0) if media_resp_seg is not None else None
        ),
    )

    cancelamentos_top = [
        CancelamentoTop(motivo=r.motivo, quantidade=int(r.qtd)) for r in top_rows
    ]

    return ReportResponse3Studio(
        periodo=PeriodoMeta(
            from_=filters.from_, to=filters.to, total_dias=total_dias
        ),
        indicadores=indicadores,
        cancelamentos_top=cancelamentos_top,
        atualizado_em=now_utc,
    )


async def _aggregate_vendedores(
    filters: ReportFilters, db: AsyncSession
) -> ReportResponseVendedores:
    """Agrega ranking + atrasadas em poder + distribuicao por localizacao."""
    tempo_atraso_horas = await _read_tempo_atraso(db)
    now_utc = datetime.now(timezone.utc)
    cutoff = limite_atraso(now_utc, tempo_atraso_horas)
    total_dias = calcular_total_dias(filters.from_, filters.to)

    # Q1: ranking + totais por localizacao (helper compartilhado com scope=geral)
    ranking, matriz_total, filial_total = await _query_ranking_vendedores(
        filters, db, cutoff=cutoff
    )

    # Q2: lista atrasadas em poder (top 10) — recria subquery (independente do helper)
    ultima_mov = _ultima_mov_subq()
    atrasadas_em_poder_subq = (
        select(
            ProvaDigital.vendedor_id.label("vid"),
            func.count().label("qtd_atrasadas"),
        )
        .where(
            ProvaDigital.status.in_(_VENDEDOR_EM_PODER),
            func.coalesce(ultima_mov, ProvaDigital.created_at) < cutoff,
        )
        .group_by(ProvaDigital.vendedor_id)
        .subquery()
    )
    stmt_atr_top = (
        select(
            Usuario.id,
            Usuario.nome,
            Usuario.localizacao,
            atrasadas_em_poder_subq.c.qtd_atrasadas,
        )
        .select_from(atrasadas_em_poder_subq)
        .join(Usuario, Usuario.id == atrasadas_em_poder_subq.c.vid)
        .order_by(atrasadas_em_poder_subq.c.qtd_atrasadas.desc(), Usuario.nome.asc())
        .limit(10)
    )
    atr_rows = (await db.execute(stmt_atr_top)).all()
    atrasadas_em_poder = [
        VendedorAtrasoAtual(
            vendedor_id=r.id,
            vendedor_nome=r.nome,
            localizacao=r.localizacao,
            qtd_atrasadas=int(r.qtd_atrasadas),
        )
        for r in atr_rows
    ]

    return ReportResponseVendedores(
        periodo=PeriodoMeta(
            from_=filters.from_, to=filters.to, total_dias=total_dias
        ),
        ranking=ranking,
        distribuicao_localizacao=DistLocalizacao(
            matriz=matriz_total, filial=filial_total
        ),
        atrasadas_em_poder=atrasadas_em_poder,
        atualizado_em=now_utc,
    )


async def _aggregate_clicheria(
    filters: ReportFilters, db: AsyncSession
) -> ReportResponseClicheria:
    """Agrega indicadores da perspectiva 'clicheria'."""
    now_utc = datetime.now(timezone.utc)
    total_dias = calcular_total_dias(filters.from_, filters.to)

    # Q1: recebidas no periodo + tempo medio aguardando recebimento + por origem
    # Recebimento e a movimentacao com status_novo = RECEBIDA_PELA_CLICHERIA.
    # Origem = ENVIADA (rota PADRAO via motorista) ou ENCAMINHADA (rota DIRETA).
    chegada_subq = (
        select(
            Movimentacao.prova_id,
            Movimentacao.ciclo,
            func.min(Movimentacao.created_at).label("chegada_at"),
            func.min(Movimentacao.status_novo).label("origem_status"),
        )
        .where(
            Movimentacao.status_novo.in_(
                (
                    StatusProvaEnum.ENVIADA_PARA_CLICHERIA,
                    StatusProvaEnum.ENCAMINHADA_A_CLICHERIA,
                )
            )
        )
        .group_by(Movimentacao.prova_id, Movimentacao.ciclo)
        .subquery()
    )
    delta_recv = func.extract(
        "epoch", Movimentacao.created_at - chegada_subq.c.chegada_at
    )

    stmt_recebidas = (
        select(
            func.count().label("total"),
            func.avg(delta_recv).label("media_seg"),
            func.count()
            .filter(
                chegada_subq.c.origem_status
                == StatusProvaEnum.ENVIADA_PARA_CLICHERIA
            )
            .label("via_padrao"),
            func.count()
            .filter(
                chegada_subq.c.origem_status
                == StatusProvaEnum.ENCAMINHADA_A_CLICHERIA
            )
            .label("via_direta"),
        )
        .select_from(Movimentacao)
        .join(
            chegada_subq,
            and_(
                chegada_subq.c.prova_id == Movimentacao.prova_id,
                chegada_subq.c.ciclo == Movimentacao.ciclo,
            ),
        )
        .where(
            Movimentacao.status_novo == StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
            Movimentacao.created_at >= filters.from_,
            Movimentacao.created_at < filters.to,
        )
    )
    rec_row = (await db.execute(stmt_recebidas)).one()

    # Q2: snapshot em transito (status atual)
    stmt_transito = select(func.count()).where(
        ProvaDigital.status.in_(_CLICHERIA_EM_TRANSITO)
    )
    em_transito = int((await db.execute(stmt_transito)).scalar_one() or 0)

    indicadores = IndicadoresClicheria(
        recebidas_no_periodo=int(rec_row.total),
        tempo_medio_aguardando_recebimento_horas=arredondar_horas(
            (float(rec_row.media_seg) / 3600.0)
            if rec_row.media_seg is not None
            else None
        ),
        em_transito_atual=em_transito,
        por_origem_rota=DistOrigemRota(
            via_padrao=int(rec_row.via_padrao),
            via_direta=int(rec_row.via_direta),
        ),
    )

    return ReportResponseClicheria(
        periodo=PeriodoMeta(
            from_=filters.from_, to=filters.to, total_dias=total_dias
        ),
        indicadores=indicadores,
        atualizado_em=now_utc,
    )


# ─── Orchestrador: cache + ETag ───────────────────────────────────────────


async def _dispatch_aggregator(scope: ReportScope, filters: ReportFilters, db: AsyncSession):
    """Roteia para o agregador certo conforme o `scope`.

    Lookup dinamico (name resolution em runtime) — permite que testes
    patchem `_aggregate_geral` etc. via `unittest.mock.patch`.
    """
    if scope == "geral":
        return await _aggregate_geral(filters, db)
    if scope == "3studio":
        return await _aggregate_3studio(filters, db)
    if scope == "vendedores":
        return await _aggregate_vendedores(filters, db)
    if scope == "clicheria":
        return await _aggregate_clicheria(filters, db)
    raise ValueError(f"scope desconhecido: {scope}")


async def _get_or_compute(
    filters: ReportFilters,
    db: AsyncSession,
    cache: ReportCache,
):
    """Retorna (payload, etag, from_cache) — busca no cache ou agrega.

    Em cache hit, devolve o payload + etag pre-calculados (zero queries).
    Em cache miss, executa o agregador, calcula ETag, armazena, devolve.
    """
    key = to_cache_key(filters)
    entry = await cache.get(key)
    if entry is not None:
        return entry.payload, entry.etag, True

    payload = await _dispatch_aggregator(filters.scope, filters, db)
    etag = compute_etag(payload)
    await cache.set(key, payload, etag)
    return payload, etag, False


# ─── Endpoint principal: GET /reports ─────────────────────────────────────


@router.get("", response_model=None)
async def get_report(
    request: Request,
    response: Response,
    scope: ReportScope = Query(..., description="Perspectiva do relatorio"),
    from_: datetime | None = Query(
        None, alias="from", description="Limite inferior do periodo (UTC ISO-8601)"
    ),
    to: datetime | None = Query(
        None, description="Limite superior do periodo (UTC ISO-8601)"
    ),
    q: str | None = Query(None, max_length=MAX_Q_LENGTH, description="Busca textual"),
    vendedor_id: uuid.UUID | None = Query(None),
    rota: RotaEnum | None = Query(None),
    status_filter: StatusProvaEnum | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_admin_user),
):
    """Retorna o relatorio para o `scope` requisitado (US-014, RBAC admin).

    Defaults: ultimos 30 dias se `from`/`to` ausentes. Range maximo 366 dias.

    Cache layers (WAVE5_ANALYSIS §4.4):
      1. ETag/304: cliente envia `If-None-Match` => 304 sem body se hit.
      2. Cache backend TTL 60s por hash dos filtros.
      3. SQLAlchemy compiled cache (gratuito).

    Headers de resposta:
      - ETag: SHA-256 do JSON canonico do payload.
      - Cache-Control: private, max-age=30, stale-while-revalidate=60.
    """
    try:
        filters = await _resolve_filters(
            scope=scope,
            from_dt=from_,
            to_dt=to,
            q=q,
            vendedor_id=vendedor_id,
            rota=rota,
            status_filter=status_filter,
        )
    except Exception as exc:
        # Pydantic validation errors -> 422
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )

    cache = get_default_cache()

    try:
        payload, etag, _from_cache = await _get_or_compute(filters, db, cache)
    except Exception:
        logger.exception("Erro ao calcular relatorio scope=%s", scope)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Erro ao calcular relatorio",
        )

    # Headers de cache + ETag
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = CACHE_CONTROL_HEADER

    # Conditional request: If-None-Match match => 304
    if matches_if_none_match(request.headers.get("If-None-Match"), etag):
        return Response(
            status_code=status.HTTP_304_NOT_MODIFIED,
            headers={
                "ETag": etag,
                "Cache-Control": CACHE_CONTROL_HEADER,
            },
        )

    return payload


# ─── Endpoint de exportacao CSV ───────────────────────────────────────────


@router.get("/export")
async def export_report(
    request: Request,
    scope: ReportScope = Query(...),
    dataset: ExportDataset = Query("summary"),
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = Query(None),
    q: str | None = Query(None, max_length=MAX_Q_LENGTH),
    vendedor_id: uuid.UUID | None = Query(None),
    rota: RotaEnum | None = Query(None),
    status_filter: StatusProvaEnum | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_admin_user),
) -> StreamingResponse:
    """Exporta relatorio em CSV (UTF-8 com BOM, Excel-compatible).

    Datasets disponiveis:
      - `summary`: indicadores chave-valor do scope (1 linha por KPI).
      - `by-seller`: ranking de vendedores (1 linha por vendedor).
      - `overdue`: provas atualmente atrasadas (1 linha por prova).
      - `proofs`: provas no periodo (1 linha por prova, server-side cursor).

    Auditoria: insere `audit_logs.acao='REPORT_EXPORTED'` antes do streaming.
    Linha truncadora `# TRUNCATED` se exceder CSV_TRUNCATE_LIMIT.
    """
    try:
        filters = await _resolve_filters(
            scope=scope,
            from_dt=from_,
            to_dt=to,
            q=q,
            vendedor_id=vendedor_id,
            rota=rota,
            status_filter=status_filter,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        )

    # Audit FIRST: log + commit imediato (auditavel mesmo se download abortar).
    await log_audit(
        db,
        acao="REPORT_EXPORTED",
        usuario_id=current_user.id,
        detalhes={
            "scope": filters.scope,
            "dataset": dataset,
            "from": filters.from_.isoformat(),
            "to": filters.to.isoformat(),
            "q": filters.q,
            "vendedor_id": str(filters.vendedor_id) if filters.vendedor_id else None,
            "rota": filters.rota.value if filters.rota else None,
            "status": filters.status.value if filters.status else None,
        },
        request=request,
    )
    await db.commit()

    # Filename: relatorio_{scope}_{dataset}_{from}_{to}.csv
    filename = (
        f"relatorio_{filters.scope}_{dataset}_"
        f"{filters.from_.date().isoformat()}_{filters.to.date().isoformat()}.csv"
    )
    # RFC 5987 — encoded filename for non-ASCII compat
    filename_q = quote(filename)

    return StreamingResponse(
        _stream_csv(filters, dataset, db),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{filename}\"; "
                f"filename*=UTF-8''{filename_q}"
            ),
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


# ─── CSV streaming helpers ────────────────────────────────────────────────


def _csv_writer() -> tuple[io.StringIO, csv.writer]:
    """Cria StringIO buffer + csv.writer reutilizavel (line-by-line)."""
    buf = io.StringIO()
    writer = csv.writer(buf, dialect="excel")
    return buf, writer


def _flush_buf(buf: io.StringIO) -> str:
    """Lê e zera o buffer de StringIO. Retorna a string acumulada."""
    text = buf.getvalue()
    buf.seek(0)
    buf.truncate(0)
    return text


def _format_horas(v: float | None) -> str:
    return f"{v:.2f}" if v is not None else ""


def _format_taxa(v: float) -> str:
    return f"{v * 100:.2f}%"


async def _stream_csv(
    filters: ReportFilters,
    dataset: ExportDataset,
    db: AsyncSession,
) -> AsyncIterator[str]:
    """Gera o CSV em chunks. BOM UTF-8 inicial + truncagem hard."""
    yield CSV_BOM

    if dataset == "summary":
        async for chunk in _stream_summary(filters, db):
            yield chunk
    elif dataset == "by-seller":
        async for chunk in _stream_by_seller(filters, db):
            yield chunk
    elif dataset == "overdue":
        async for chunk in _stream_overdue(filters, db):
            yield chunk
    elif dataset == "proofs":
        async for chunk in _stream_proofs(filters, db):
            yield chunk
    else:
        # Defesa: Pydantic Literal ja restringe; defesa em runtime.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"dataset invalido: {dataset}",
        )


async def _stream_summary(
    filters: ReportFilters, db: AsyncSession
) -> AsyncIterator[str]:
    """CSV: 1 linha por KPI (chave/valor). Reutiliza o agregador do scope."""
    payload = await _dispatch_aggregator(filters.scope, filters, db)

    buf, writer = _csv_writer()
    writer.writerow(["scope", "indicador", "valor"])

    for row in _summary_rows(payload):
        writer.writerow(row)

    yield _flush_buf(buf)


def _summary_rows(payload: Any) -> Iterable[list[str]]:
    """Achata os indicadores do payload em linhas (scope, indicador, valor)."""
    scope = payload.scope
    rows: list[list[str]] = []

    p = payload.periodo
    rows.append([scope, "periodo_from", p.from_.isoformat()])
    rows.append([scope, "periodo_to", p.to.isoformat()])
    rows.append([scope, "periodo_total_dias", str(p.total_dias)])

    if scope == "geral":
        ind = payload.indicadores
        rows.append([scope, "total_provas", str(ind.total_provas)])
        rows.append(
            [scope, "tempo_medio_ciclo_horas", _format_horas(ind.tempo_medio_ciclo_horas)]
        )
        rows.append(
            [
                scope,
                "tempo_mediano_ciclo_horas",
                _format_horas(ind.tempo_mediano_ciclo_horas),
            ]
        )
        rows.append(
            [
                scope,
                "tempo_medio_aprovacao_horas",
                _format_horas(ind.tempo_medio_aprovacao_horas),
            ]
        )
        rows.append([scope, "taxa_reprovacao", _format_taxa(ind.taxa_reprovacao)])
        rows.append([scope, "qtd_atrasadas", str(ind.qtd_atrasadas)])
        for d in payload.distribuicao_status:
            rows.append([scope, f"status_{d.status.value}", str(d.quantidade)])
        for d in payload.distribuicao_rota:
            label = d.rota.value if d.rota is not None else "NAO_DEFINIDA"
            rows.append([scope, f"rota_{label}", str(d.quantidade)])
    elif scope == "3studio":
        ind = payload.indicadores
        rows.append([scope, "provas_criadas", str(ind.provas_criadas)])
        rows.append(
            [scope, "media_diaria_criacao", f"{ind.media_diaria_criacao:.2f}"]
        )
        rows.append([scope, "reinicios_de_ciclo", str(ind.reinicios_de_ciclo)])
        rows.append([scope, "devolvidas_motorista", str(ind.devolvidas_motorista)])
        rows.append(
            [
                scope,
                "reprovadas_aguardando_acao",
                str(ind.reprovadas_aguardando_acao),
            ]
        )
        rows.append([scope, "cancelamentos", str(ind.cancelamentos)])
        rows.append(
            [
                scope,
                "tempo_medio_criacao_ate_primeira_mov_horas",
                _format_horas(ind.tempo_medio_criacao_ate_primeira_mov_horas),
            ]
        )
        for c in payload.cancelamentos_top:
            rows.append([scope, f"cancelamento:{c.motivo}", str(c.quantidade)])
    elif scope == "vendedores":
        rows.append(
            [scope, "vendedores_matriz", str(payload.distribuicao_localizacao.matriz)]
        )
        rows.append(
            [scope, "vendedores_filial", str(payload.distribuicao_localizacao.filial)]
        )
        rows.append([scope, "ranking_size", str(len(payload.ranking))])
        for v in payload.ranking:
            rows.append(
                [
                    scope,
                    f"vendedor:{v.vendedor_nome}:volume",
                    str(v.volume),
                ]
            )
    else:  # clicheria
        ind = payload.indicadores
        rows.append([scope, "recebidas_no_periodo", str(ind.recebidas_no_periodo)])
        rows.append(
            [
                scope,
                "tempo_medio_aguardando_recebimento_horas",
                _format_horas(ind.tempo_medio_aguardando_recebimento_horas),
            ]
        )
        rows.append([scope, "em_transito_atual", str(ind.em_transito_atual)])
        rows.append(
            [scope, "via_padrao", str(ind.por_origem_rota.via_padrao)]
        )
        rows.append(
            [scope, "via_direta", str(ind.por_origem_rota.via_direta)]
        )

    return rows


async def _stream_by_seller(
    filters: ReportFilters, db: AsyncSession
) -> AsyncIterator[str]:
    """CSV: 1 linha por vendedor com metricas. Reutiliza o agregador `vendedores`."""
    payload = await _aggregate_vendedores(filters, db)

    buf, writer = _csv_writer()
    writer.writerow(
        [
            "vendedor_id",
            "vendedor_nome",
            "localizacao",
            "volume",
            "taxa_aprovacao_pct",
            "taxa_reprovacao_pct",
            "tempo_medio_retirada_a_decisao_horas",
            "provas_atrasadas_em_poder",
        ]
    )
    for v in payload.ranking:
        writer.writerow(
            [
                str(v.vendedor_id),
                v.vendedor_nome,
                v.localizacao.value,
                str(v.volume),
                _format_taxa(v.taxa_aprovacao),
                _format_taxa(v.taxa_reprovacao),
                _format_horas(v.tempo_medio_retirada_a_decisao_horas),
                str(v.provas_atrasadas_em_poder),
            ]
        )
    yield _flush_buf(buf)


async def _stream_overdue(
    filters: ReportFilters, db: AsyncSession
) -> AsyncIterator[str]:
    """CSV: 1 linha por prova atrasada (snapshot atual, server-side cursor)."""
    tempo_atraso_horas = await _read_tempo_atraso(db)
    now_utc = datetime.now(timezone.utc)
    cutoff = limite_atraso(now_utc, tempo_atraso_horas)
    ultima_mov = _ultima_mov_subq()

    stmt = (
        select(
            ProvaDigital.id,
            ProvaDigital.nro_requerimento,
            ProvaDigital.nome,
            ProvaDigital.cliente,
            ProvaDigital.status,
            ProvaDigital.rota,
            Usuario.nome.label("vendedor_nome"),
            Usuario.localizacao,
            ProvaDigital.created_at,
            func.coalesce(ultima_mov, ProvaDigital.created_at).label("ultima_at"),
            cast(
                func.extract(
                    "epoch",
                    now_utc - func.coalesce(ultima_mov, ProvaDigital.created_at),
                )
                / 3600.0,
                Float,
            ).label("horas_atrasada"),
        )
        .select_from(ProvaDigital)
        .join(Usuario, Usuario.id == ProvaDigital.vendedor_id)
        .where(
            ProvaDigital.status.not_in(_TERMINAL_STATUSES),
            func.coalesce(ultima_mov, ProvaDigital.created_at) < cutoff,
        )
        .order_by(func.coalesce(ultima_mov, ProvaDigital.created_at).asc())
    )

    buf, writer = _csv_writer()
    writer.writerow(
        [
            "prova_id",
            "nro_requerimento",
            "nome",
            "cliente",
            "status",
            "rota",
            "vendedor_nome",
            "localizacao",
            "created_at",
            "ultima_movimentacao_at",
            "horas_atrasada",
        ]
    )
    yield _flush_buf(buf)

    count = 0
    result = await db.stream(stmt, execution_options={"yield_per": CSV_BATCH_SIZE})
    async for row in result:
        if count >= CSV_TRUNCATE_LIMIT:
            yield "# TRUNCATED\n"
            break
        writer.writerow(
            [
                str(row.id),
                row.nro_requerimento,
                row.nome,
                row.cliente,
                row.status.value,
                row.rota.value if row.rota else "",
                row.vendedor_nome,
                row.localizacao.value if row.localizacao else "",
                row.created_at.isoformat(),
                row.ultima_at.isoformat(),
                f"{float(row.horas_atrasada):.2f}",
            ]
        )
        count += 1
        if count % CSV_BATCH_SIZE == 0:
            yield _flush_buf(buf)
    if buf.tell() > 0:
        yield _flush_buf(buf)


async def _stream_proofs(
    filters: ReportFilters, db: AsyncSession
) -> AsyncIterator[str]:
    """CSV: 1 linha por prova no periodo (server-side cursor)."""
    stmt = (
        select(
            ProvaDigital.id,
            ProvaDigital.nro_requerimento,
            ProvaDigital.nome,
            ProvaDigital.cliente,
            ProvaDigital.status,
            ProvaDigital.rota,
            ProvaDigital.ciclo_atual,
            Usuario.nome.label("vendedor_nome"),
            Usuario.localizacao,
            ProvaDigital.created_at,
            ProvaDigital.updated_at,
            ProvaDigital.motivo_cancelamento,
        )
        .select_from(ProvaDigital)
        .join(Usuario, Usuario.id == ProvaDigital.vendedor_id)
        .where(_periodo_filter(filters))
        .order_by(ProvaDigital.created_at.asc())
    )
    stmt = _aplicar_filtros_provas(stmt, filters)

    buf, writer = _csv_writer()
    writer.writerow(
        [
            "prova_id",
            "nro_requerimento",
            "nome",
            "cliente",
            "status",
            "rota",
            "ciclo_atual",
            "vendedor_nome",
            "localizacao",
            "created_at",
            "updated_at",
            "motivo_cancelamento",
        ]
    )
    yield _flush_buf(buf)

    count = 0
    result = await db.stream(stmt, execution_options={"yield_per": CSV_BATCH_SIZE})
    async for row in result:
        if count >= CSV_TRUNCATE_LIMIT:
            yield "# TRUNCATED\n"
            break
        writer.writerow(
            [
                str(row.id),
                row.nro_requerimento,
                row.nome,
                row.cliente,
                row.status.value,
                row.rota.value if row.rota else "",
                str(row.ciclo_atual),
                row.vendedor_nome,
                row.localizacao.value if row.localizacao else "",
                row.created_at.isoformat(),
                row.updated_at.isoformat(),
                row.motivo_cancelamento or "",
            ]
        )
        count += 1
        if count % CSV_BATCH_SIZE == 0:
            yield _flush_buf(buf)
    if buf.tell() > 0:
        yield _flush_buf(buf)


__all__ = ["router"]
