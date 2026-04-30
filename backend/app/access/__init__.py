"""Camada RBAC do backend — Wave 1 v4.0, Componente 05.

Le shared/access-matrix.json (fonte unica) e expoe:
  - enforce_access_for(rule_key, user) — guard primario para endpoints
  - scope_filter_for(rule_key, user)   — clausula WHERE para SELECTs
                                          com escopo PARCIAL
  - get_matrix() / get_rule_for_key()  — leitura crua da matriz
  - resolve_profile(user)              — mapeia Usuario -> Profile

Espelhada por:
  - frontend/src/lib/access-matrix.ts
  - frontend/src/lib/hooks/use-authorization.ts
  - frontend/src/middleware.ts
  - backend/migrations/rls/012_move_helpers_to_app_private.sql
"""
from app.access.enforce import enforce_access_for
from app.access.guards import access_required
from app.access.matrix import (
    AccessRule,
    Acesso,
    PerfilDecision,
    Profile,
    evaluate,
    get_matrix,
    get_rule_for_key,
    home_for_profile,
    resolve_profile,
)
from app.access.scopes import scope_filter_for

__all__ = [
    "Acesso",
    "AccessRule",
    "PerfilDecision",
    "Profile",
    "access_required",
    "enforce_access_for",
    "evaluate",
    "get_matrix",
    "get_rule_for_key",
    "home_for_profile",
    "resolve_profile",
    "scope_filter_for",
]
