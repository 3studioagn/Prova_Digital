"""FastAPI dependency factory para gating por chave da Matriz.

Substitui `Depends(get_admin_user)` em endpoints onde a checagem
corresponde a uma celula da Matriz de Acesso (Wave 1 v4.0, Componente 05).

Uso:

    from app.access import access_required

    @router.get("/")
    async def list_audits(
        user: Usuario = Depends(access_required("auditoria")),
    ):
        ...

Comportamento:
  1. Resolve `get_current_user` (rejeita 401 sem token).
  2. Chama `enforce_access_for(rule_key, user)` (rejeita 403 se NEGADO).
  3. Devolve o `Usuario` para uso no handler.

Importante:
  - `enforce_access_for` aceita FULL e PARCIAL silenciosamente. Endpoints
    com escopo PARCIAL precisam combinar com `scope_filter_for(rule_key,
    user)` na clausula WHERE da query (ver app/access/scopes.py).
  - Tests existentes que sobrescrevem `get_current_user` continuam
    funcionando: o factory delega via `Depends(get_current_user)`, e
    eles podem injetar admin/vendedor diretamente.
"""
from __future__ import annotations

from typing import Callable

from fastapi import Depends

from app.access.enforce import enforce_access_for
from app.api.deps import get_current_user
from app.db.models import Usuario


def access_required(rule_key: str) -> Callable[..., Usuario]:
    """Factory que devolve dependency FastAPI para gating por rule_key."""

    async def _dependency(
        user: Usuario = Depends(get_current_user),
    ) -> Usuario:
        enforce_access_for(rule_key, user)
        return user

    # Nome ajuda telemetria/swagger.
    _dependency.__name__ = f"require_access_{rule_key.replace('.', '_')}"
    return _dependency
