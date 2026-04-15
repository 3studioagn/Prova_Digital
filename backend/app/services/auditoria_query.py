"""Query builder para audit log (Wave 6 Bloco 6.2, ADR-099).

Implementa a camada SQL dos endpoints `GET /api/v1/auditoria/` e
`GET /api/v1/auditoria/{id}`. Separada de `api/v1/auditoria.py` para:

  - Permitir testes unitarios do builder sem subir o FastAPI.
  - Manter o handler HTTP magro (apenas parsing + error translation).
  - Colocar a logica de keyset pagination + cursor codec + timezone +
    joins em um unico lugar, testavel em isolamento.

Componentes principais:
  1. **Cursor codec** — `encode_cursor` / `decode_cursor` (base64 urlsafe
     de `{"c": iso_datetime, "i": uuid}`).
  2. **Timezone helpers** — `data_inicio_brt_para_utc` /
     `data_fim_brt_para_utc` convertem `date` BRT em `datetime` UTC
     (RNF implicito: usuario pensa em BRT, banco guarda UTC).
  3. **Filter builder** — `_build_filter_clauses` gera as WHERE clauses
     do SQLAlchemy a partir de `AuditoriaFiltros`.
  4. **TipoEvento clause mapper** — `_tipo_evento_para_clause` espelha
     `auditoria_projection.projetar_tipo_evento` no sentido inverso
     (derivado -> cru + JSONB condition).
  5. **Queries principais** — `listar_audit_logs` (keyset + count capped)
     e `buscar_audit_log_por_id` (enriquecido).

**Zero INSERT/UPDATE/DELETE** em `audit_logs` — garantia de imutabilidade
(RNF-005) por ausencia. Os unicos `select()` aqui sao para leitura.
"""
from __future__ import annotations

import base64
import binascii
import json
import logging
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.db.models import AuditLog, ProvaDigital, Usuario
from app.domain.schemas.auditoria import (
    TOTAL_ESTIMADO_CAP,
    AuditLogItem,
    AuditoriaFiltros,
    AuditoriaListResponse,
    FiltrosAplicados,
    ProvaAuditoria,
    TipoEventoEnum,
    UsuarioAuditoria,
)
from app.services.auditoria_projection import label_tipo_evento, projetar_tipo_evento

logger = logging.getLogger(__name__)


# =============================================================================
# Constantes de timezone
# =============================================================================


BRT = timezone(timedelta(hours=-3))
"""Fuso horario do usuario (America/Sao_Paulo).

Usamos offset FIXO `-03:00` em vez de `ZoneInfo("America/Sao_Paulo")`
porque:
  1. O Brasil nao observa horario de verao desde 2019 (Decreto 9.772/2019)
     — o offset e permanentemente UTC-3.
  2. `ZoneInfo` em Python 3.14 no Windows exige o pacote `tzdata`, que
     adicionaria uma dependencia so por causa disso.
  3. Evita o problema classico de TZ data ficar desatualizada em
     containers/imagens cujo `/usr/share/zoneinfo` nao e atualizado.

Se o Brasil voltar a adotar DST no futuro, este constante vira o
unico ponto a atualizar (trocar para `ZoneInfo("America/Sao_Paulo")` e
adicionar `tzdata` ao `pyproject.toml`).
"""

UTC = timezone.utc
"""Fuso horario do banco — `audit_logs.created_at` e TIMESTAMPTZ armazenado
internamente em UTC."""


# =============================================================================
# Excecoes
# =============================================================================


class CursorInvalidoError(ValueError):
    """Cursor malformado (base64 invalido, JSON corrompido, chaves ausentes,
    UUID invalido, datetime invalido). O handler HTTP traduz para 422."""


class AuditLogSemUsuarioError(RuntimeError):
    """Dado inconsistente: audit_log com `usuario_id` referenciando um
    usuario que nao existe mais. Nao deveria acontecer em producao (usuarios
    nao sao apagados, apenas desativados), mas e defensivo. O handler HTTP
    traduz para 500 com mensagem generica."""


# =============================================================================
# 1. Cursor codec (funcoes puras, testavel sem banco)
# =============================================================================


def encode_cursor(created_at: datetime, log_id: UUID) -> str:
    """Codifica `(created_at, log_id)` em base64 urlsafe opaco.

    Formato interno (chaves curtas para minimizar payload):
        `{"c": "<iso datetime>", "i": "<uuid>"}`

    O cursor e opaco do ponto de vista do cliente — nao ha contrato sobre
    o formato interno. Pode mudar em Waves futuras sem quebrar a API.
    """
    payload = json.dumps(
        {"c": created_at.isoformat(), "i": str(log_id)},
        separators=(",", ":"),
    )
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    """Decodifica um cursor opaco. Levanta `CursorInvalidoError` em qualquer
    problema (base64, JSON, objeto, chaves, UUID, datetime).

    Nao confia no input — valida cada etapa explicitamente para dar
    mensagens de erro claras ao cliente.
    """
    try:
        raw_bytes = base64.urlsafe_b64decode(cursor.encode("ascii"))
        raw = raw_bytes.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise CursorInvalidoError(f"cursor nao e base64 valido: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CursorInvalidoError(f"cursor nao e JSON valido: {exc}") from exc

    if not isinstance(data, dict):
        raise CursorInvalidoError("cursor JSON nao e um objeto")

    if "c" not in data or "i" not in data:
        raise CursorInvalidoError("cursor sem chaves 'c' e 'i'")

    try:
        created_at = datetime.fromisoformat(str(data["c"]))
    except (ValueError, TypeError) as exc:
        raise CursorInvalidoError(f"cursor com datetime invalido: {exc}") from exc

    try:
        log_id = UUID(str(data["i"]))
    except (ValueError, TypeError) as exc:
        raise CursorInvalidoError(f"cursor com UUID invalido: {exc}") from exc

    return created_at, log_id


# =============================================================================
# 2. Timezone helpers (funcoes puras)
# =============================================================================


def data_inicio_brt_para_utc(d: date) -> datetime:
    """Converte `date` BRT em `datetime` UTC no inicio do dia.

    Exemplo: `date(2026, 4, 14)` ->
    `datetime(2026, 4, 14, 3, 0, 0, UTC)` (BRT e UTC-3).

    Usado em `WHERE created_at >= <resultado>` (comparacao inclusiva).
    """
    local = datetime.combine(d, time(0, 0, 0), tzinfo=BRT)
    return local.astimezone(UTC)


def data_fim_brt_para_utc(d: date) -> datetime:
    """Converte `date` BRT em `datetime` UTC no inicio do dia SEGUINTE.

    Exemplo: `date(2026, 4, 14)` ->
    `datetime(2026, 4, 15, 3, 0, 0, UTC)`.

    Usado em `WHERE created_at < <resultado>` (comparacao EXCLUSIVA).
    Logica: "todos os eventos do dia 14 BRT" = "created_at < inicio do
    dia 15 BRT". Evita o classico bug de "filtrar ate 2026-04-14 mas
    perder eventos das 23:59:59.999 desse mesmo dia".
    """
    local = datetime.combine(d + timedelta(days=1), time(0, 0, 0), tzinfo=BRT)
    return local.astimezone(UTC)


# =============================================================================
# 3. Filter clause builder (SQLAlchemy 2.0 core)
# =============================================================================


def _tipo_evento_para_clause(tipo: TipoEventoEnum):
    """Mapeia um `TipoEventoEnum` para uma WHERE clause SQLAlchemy.

    Espelha `auditoria_projection.projetar_tipo_evento` no sentido inverso
    (derivado -> cru + condicao JSONB quando aplicavel). Deve ser
    mantido em sincronia com a funcao de projecao — o teste
    `test_build_filter_clauses_combinado` + o parametrizado cobrem.
    """
    if tipo == TipoEventoEnum.CRIACAO_PROVA:
        return AuditLog.acao == "criar_prova"
    if tipo == TipoEventoEnum.ESCANEAMENTO:
        return AuditLog.acao == "escanear_prova"
    if tipo == TipoEventoEnum.REINICIO_CICLO:
        return AuditLog.acao == "reiniciar_ciclo"
    if tipo == TipoEventoEnum.ALTERACAO_CONFIG:
        return AuditLog.acao == "atualizar_configuracao"
    if tipo == TipoEventoEnum.CANCELAMENTO:
        return and_(
            AuditLog.acao == "transitar_status",
            AuditLog.detalhes_json["para"].astext == "CANCELADA",
        )
    if tipo == TipoEventoEnum.REPROVACAO:
        return and_(
            AuditLog.acao == "transitar_status",
            AuditLog.detalhes_json["para"].astext == "REPROVADA_PELO_VENDEDOR",
        )
    if tipo == TipoEventoEnum.TRANSICAO_STATUS:
        # transitar_status mas NAO cancelamento NEM reprovacao — matches
        # o branch `return TipoEventoEnum.TRANSICAO_STATUS` da projecao.
        return and_(
            AuditLog.acao == "transitar_status",
            or_(
                AuditLog.detalhes_json["para"].astext.is_(None),
                AuditLog.detalhes_json["para"].astext.notin_(
                    ("CANCELADA", "REPROVADA_PELO_VENDEDOR")
                ),
            ),
        )
    # Seguranca: se um novo enum for adicionado sem atualizar este
    # mapeamento, levanta — preferivel a silenciosamente filtrar nada.
    raise ValueError(f"TipoEvento nao mapeado: {tipo}")


def _build_filter_clauses(filtros: AuditoriaFiltros) -> list:
    """Constroi a lista de WHERE clauses a partir de `AuditoriaFiltros`.

    Nao inclui a clause do cursor (paginacao keyset) — essa e aplicada
    separadamente apenas na query de listagem. O `COUNT(*)` usa os MESMOS
    filtros SEM o cursor, porque cursor e estado de paginacao, nao de
    dominio.
    """
    clauses: list = []

    if filtros.data_inicio is not None:
        clauses.append(
            AuditLog.created_at >= data_inicio_brt_para_utc(filtros.data_inicio)
        )

    if filtros.data_fim is not None:
        clauses.append(
            AuditLog.created_at < data_fim_brt_para_utc(filtros.data_fim)
        )

    if filtros.usuario_id is not None:
        clauses.append(AuditLog.usuario_id == filtros.usuario_id)

    if filtros.nro_requerimento is not None:
        # `nro_requerimento` e UNIQUE em `provas_digitais` — subquery
        # escalar retorna NULL se nao existir, e `audit_log.prova_id ==
        # NULL` avalia para FALSE (zero rows) — comportamento correto.
        prova_subq = (
            select(ProvaDigital.id)
            .where(ProvaDigital.nro_requerimento == filtros.nro_requerimento)
            .scalar_subquery()
        )
        clauses.append(AuditLog.prova_id == prova_subq)

    if filtros.acao:
        clauses.append(AuditLog.acao.in_(filtros.acao))
    elif filtros.tipo_evento:
        or_clauses = [_tipo_evento_para_clause(t) for t in filtros.tipo_evento]
        clauses.append(or_(*or_clauses))

    return clauses


# =============================================================================
# 4. Query principal: listar_audit_logs
# =============================================================================


async def listar_audit_logs(
    db: AsyncSession,
    filtros: AuditoriaFiltros,
) -> AuditoriaListResponse:
    """Lista paginada do `audit_logs` com enriquecimento via LEFT JOIN.

    Faz 2 queries:
      1. **Listagem** — `SELECT a, u, p FROM audit_logs a LEFT JOIN
         usuarios u ... LEFT JOIN provas_digitais p ... WHERE <filtros>
         [AND cursor_clause] ORDER BY created_at DESC, id DESC
         LIMIT (limit+1)`. O `+1` e o N+1 pattern para detectar
         `has_more`.
      2. **Count capped** — `SELECT count(*) FROM (SELECT id FROM
         audit_logs WHERE <filtros> LIMIT 100_001) sub`. Cap evita
         COUNT(*) full-scan em tabelas muito grandes no futuro.

    Ordem fixa: `(created_at DESC, id DESC)`. Aproveita
    `idx_audit_created_at` + PK `audit_logs_pkey` (validado no Bloco 6.0
    via EXPLAIN ANALYZE — execution time < 3 ms para 50 linhas).
    """
    usuario_alias = aliased(Usuario)
    prova_alias = aliased(ProvaDigital)

    clauses = _build_filter_clauses(filtros)

    # ---------------------------------------------------------------
    # Query 1 — listagem + joins + cursor + ordem + LIMIT N+1
    # ---------------------------------------------------------------

    stmt = (
        select(AuditLog, usuario_alias, prova_alias)
        .outerjoin(usuario_alias, usuario_alias.id == AuditLog.usuario_id)
        .outerjoin(prova_alias, prova_alias.id == AuditLog.prova_id)
    )

    if clauses:
        stmt = stmt.where(*clauses)

    if filtros.cursor is not None:
        # Pode levantar CursorInvalidoError — propaga para o handler HTTP
        # que converte em 422.
        cursor_ts, cursor_id = decode_cursor(filtros.cursor)
        stmt = stmt.where(
            or_(
                AuditLog.created_at < cursor_ts,
                and_(
                    AuditLog.created_at == cursor_ts,
                    AuditLog.id < cursor_id,
                ),
            )
        )

    stmt = stmt.order_by(
        AuditLog.created_at.desc(),
        AuditLog.id.desc(),
    ).limit(filtros.limit + 1)

    result = await db.execute(stmt)
    rows = list(result.all())

    has_more = len(rows) > filtros.limit
    if has_more:
        rows = rows[: filtros.limit]

    items = [_build_item(log, usuario, prova) for log, usuario, prova in rows]

    next_cursor: str | None = None
    if has_more and rows:
        last_log: AuditLog = rows[-1][0]
        next_cursor = encode_cursor(last_log.created_at, last_log.id)

    # ---------------------------------------------------------------
    # Query 2 — COUNT(*) capped (SEM cursor, COM os demais filtros)
    # ---------------------------------------------------------------

    count_inner = select(AuditLog.id)
    if clauses:
        count_inner = count_inner.where(*clauses)
    count_inner = count_inner.limit(TOTAL_ESTIMADO_CAP)
    count_stmt = select(func.count()).select_from(count_inner.subquery())

    count_result = await db.execute(count_stmt)
    total_estimado = int(count_result.scalar_one())

    # ---------------------------------------------------------------
    # Montagem da resposta
    # ---------------------------------------------------------------

    return AuditoriaListResponse(
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
        total_estimado=total_estimado,
        filtros_aplicados=FiltrosAplicados(
            data_inicio=filtros.data_inicio,
            data_fim=filtros.data_fim,
            usuario_id=filtros.usuario_id,
            nro_requerimento=filtros.nro_requerimento,
            acao=filtros.acao,
            tipo_evento=filtros.tipo_evento,
            limit=filtros.limit,
        ),
    )


# =============================================================================
# 5. Query pontual: buscar_audit_log_por_id
# =============================================================================


async def buscar_audit_log_por_id(
    db: AsyncSession,
    log_id: UUID,
) -> AuditLogItem | None:
    """Busca uma entrada pontual do audit_log com enriquecimento.

    Retorna `None` se nao existir — handler HTTP traduz para 404.
    """
    usuario_alias = aliased(Usuario)
    prova_alias = aliased(ProvaDigital)

    stmt = (
        select(AuditLog, usuario_alias, prova_alias)
        .outerjoin(usuario_alias, usuario_alias.id == AuditLog.usuario_id)
        .outerjoin(prova_alias, prova_alias.id == AuditLog.prova_id)
        .where(AuditLog.id == log_id)
    )

    result = await db.execute(stmt)
    row = result.first()
    if row is None:
        return None

    log, usuario, prova = row
    return _build_item(log, usuario, prova)


# =============================================================================
# 6. Row -> DTO builder
# =============================================================================


def _build_item(
    log: AuditLog,
    usuario: Usuario | None,
    prova: ProvaDigital | None,
) -> AuditLogItem:
    """Constroi um `AuditLogItem` a partir de uma row (log, usuario, prova).

    Chama `projetar_tipo_evento` para derivar o campo `tipo_evento` e
    `label_tipo_evento` para o label pt-BR.

    Levanta `AuditLogSemUsuarioError` se `usuario` for `None` — isso
    indica inconsistencia FK (usuario apagado mas audit_log ainda
    referencia), que nao deveria acontecer em producao (usuarios sao
    desativados via `ativo=false`, nunca apagados).
    """
    if usuario is None:
        logger.error(
            "audit_log %s com usuario_id orfao — dado inconsistente", log.id
        )
        raise AuditLogSemUsuarioError(
            f"audit_log {log.id} com usuario_id orfao"
        )

    tipo_evento = projetar_tipo_evento(log.acao, log.detalhes_json)
    tipo_evento_label = label_tipo_evento(tipo_evento)

    usuario_dto = UsuarioAuditoria(
        id=usuario.id,
        nome=usuario.nome,
        setor=usuario.setor.value,
        is_admin=usuario.is_admin,
    )

    prova_dto: ProvaAuditoria | None = None
    if prova is not None:
        prova_dto = ProvaAuditoria(
            id=prova.id,
            nro_requerimento=prova.nro_requerimento,
            nome=prova.nome,
        )

    return AuditLogItem(
        id=log.id,
        acao=log.acao,
        tipo_evento=tipo_evento,
        tipo_evento_label=tipo_evento_label,
        usuario=usuario_dto,
        prova=prova_dto,
        detalhes_json=log.detalhes_json,
        ip_address=str(log.ip_address) if log.ip_address is not None else None,
        user_agent=log.user_agent,
        created_at=log.created_at,
    )
