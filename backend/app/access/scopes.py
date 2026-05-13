"""Filtros de escopo (RBAC partial access) — Wave 1 v4.0, Componente 05.

Substitui `_scoping_filter(user)` em `app/api/v1/provas.py` por um helper
centralizado que le `scope` da Matriz de Acesso e devolve clausula
SQLAlchemy para WHERE.

Uso:

    from app.access import scope_filter_for

    base = select(ProvaDigital)
    scope = scope_filter_for("provas.list", user)
    if scope is not None:
        base = base.where(scope)

Decisao de design (analysis Secao 6.0): backend continua usando
service_role e bypassa RLS — o scoping aqui e a defesa SUPERIOR (na query
do backend). A defesa INFERIOR (RLS) cobre o mesmo caminho via
shared/access-matrix.json -> migrations RLS 012.

Para regras com acesso FULL: retorna None (sem restricao).
Para regras com acesso NEGADO: retorna `false_()` — query retorna 0 linhas
de forma defensiva (nao deveria ser chamado se enforce_access_for ja foi).
Para regras PARCIAL: retorna a clausula correspondente ao scope kind.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import false

from app.access.matrix import (
    Acesso,
    evaluate,
    get_rule_for_key,
    resolve_profile,
)
from app.db.models import ProvaDigital, StatusProvaEnum, Usuario

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

logger = logging.getLogger(__name__)


# Status que motorista visualiza ("Em Transito"). Wave 3 v4.0 / C11
# (AUD-W3C11-001 pos-auditoria): estendido para os 3 contextos v4.0
# derivados da migration 013 + RLS 014. Defesa primaria (Python) agora
# bate com a secundaria (RLS) + Matriz canonica Secao 5 (Lam.Matriz,
# Lam.Filial e Matriz transicoes envolvendo motorista). COM_MOTORISTA
# legacy v3.0 preservado (ADR-148 — provas legacy continuam funcionando).
_MOTORISTA_STATUSES: tuple[StatusProvaEnum, ...] = (
    StatusProvaEnum.COM_MOTORISTA,                  # legacy v3.0
    StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO,    # v4.0 — Lam.Matriz / Lam.Filial
    StatusProvaEnum.COM_MOTORISTA_VOLTA_LAMINACAO,  # v4.0 — Lam.Matriz
    StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL,    # v4.0 — Matriz / Lam.Matriz
)

# Status que clicheria visualiza. Wave 3 v4.0 / C11 (AUD-W3C11-002
# pos-auditoria): estendido para os 4 estados v4.0 onde clicheria atua
# (US-007 v4.0 — laminacao + transicao final Matriz/Lam.Matriz).
# Defesa primaria (Python) + secundaria (RLS 015) batem com a Matriz
# canonica Secao 5 das 4 rotas. COM_MOTORISTA_ENTREGA_FINAL incluido
# para que clicheria possa concluir a ultima transicao de Matriz e
# Lam.Matriz (RECEBIDA_PELA_CLICHERIA).
_CLICHERIA_STATUSES: tuple[StatusProvaEnum, ...] = (
    # Legacy v3.0
    StatusProvaEnum.ENVIADA_PARA_CLICHERIA,
    StatusProvaEnum.ENCAMINHADA_A_CLICHERIA,
    StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
    # v4.0 — etapas de laminacao (US-007)
    StatusProvaEnum.ENCAMINHADA_PARA_LAMINACAO,    # clicheria recebe para laminar
    StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO,   # clicheria ve a caminho — confirma chegada
    StatusProvaEnum.LAMINACAO_CONCLUIDA,           # clicheria preparou — visivel ate retirar
    # v4.0 — entrega final (Matriz, Lam.Matriz — ultima transicao da rota)
    StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL,   # clicheria escaneia para confirmar recebimento
)


def scope_filter_for(rule_key: str, user: Usuario) -> "ColumnElement[bool] | None":
    """Devolve clausula WHERE (ou None) para SELECT em provas/movimentacoes.

    Comportamento:
      - FULL  -> None (sem restricao adicional).
      - PARCIAL -> clausula AND/OR conforme scope kind.
      - NEGADO -> sqlalchemy.false() (query retorna 0; defensivo).

    Hoje a unica entidade com escopo PARCIAL na Matriz e a prova (e
    derivados — movimentacao, etiqueta acessam pela prova). Para queries
    em outras tabelas (audit_logs, configuracoes_sistema, usuarios), use
    apenas enforce_access_for — elas sao sempre FULL ou NEGADO.
    """
    rule = get_rule_for_key(rule_key)
    if rule is None:
        logger.error("scope_filter_for: rule_key '%s' inexistente", rule_key)
        return false()

    decision = evaluate(rule, user)
    if decision.acesso == Acesso.NEGADO:
        return false()
    if decision.acesso == Acesso.FULL:
        return None

    # PARCIAL: dispatch por scope kind.
    scope = decision.scope
    if scope == "self_vendedor":
        return ProvaDigital.vendedor_id == user.id
    if scope == "status_motorista_em_transito":
        return ProvaDigital.status.in_(_MOTORISTA_STATUSES)
    if scope == "status_clicheria":
        return ProvaDigital.status.in_(_CLICHERIA_STATUSES)

    # Scope kind desconhecido — bug de configuracao da Matriz. Defensivo.
    logger.error(
        "scope_filter_for: scope kind '%s' nao implementado para rule_key='%s'",
        scope,
        rule_key,
    )
    return false()


def get_user_profile_label(user: Usuario) -> str:
    """Helper de log: rotulo curto do perfil ('admin', 'vendedor:<id>', etc)."""
    profile = resolve_profile(user)
    if profile is None:
        return f"unmapped:setor={user.setor.value}"
    if profile.value == "studio_admin":
        return "admin"
    return f"{profile.value}:{user.id}"


