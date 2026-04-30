"""FastAPI auth dependencies for route protection.

Authentication flow:
1. Client sends Authorization: Bearer <jwt> header
2. get_current_user verifies JWT via JWKS (ES256) or shared secret (HS256)
3. Loads user record from DB via auth_uid = JWT sub claim
4. Returns 401 if token invalid/missing, 403 if user deactivated

Role-based access:
- get_admin_user — legacy: somente is_admin=true. Mantido para compat
                    de testes (dependency_overrides[get_admin_user]) e
                    para invariantes de negocio em users.py (RN-010).
                    Para novos endpoints, prefira
                    `app.access.access_required(rule_key)` que consulta
                    a Matriz de Acesso (Wave 1 v4.0).

Removed in Wave 1 v4.0:
- require_role(*roles) — factory nunca usada em producao.
"""
import logging
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt import verify_token
from app.db.models import Usuario
from app.db.session import get_db

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    """Verify JWT and load the authenticated user from DB."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticacao ausente",
        )

    token = credentials.credentials
    try:
        payload = await verify_token(token)
    except jwt.ExpiredSignatureError:
        logger.warning("JWT expirado")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
        )
    except jwt.InvalidTokenError as exc:
        logger.warning("JWT invalido: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
        )

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
        )

    try:
        auth_uid = UUID(sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
        )

    result = await db.execute(
        select(Usuario).where(Usuario.auth_uid == auth_uid)
    )
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning("Usuario nao encontrado para auth_uid=%s", auth_uid)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario nao encontrado",
        )

    if not user.ativo:
        logger.warning("Acesso negado (desativado): user_id=%s", user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desativado",
        )

    logger.info("Autenticado: user_id=%s setor=%s", user.id, user.setor.value)
    return user


async def get_admin_user(
    user: Usuario = Depends(get_current_user),
) -> Usuario:
    """Require is_admin=true.

    Wave 1 v4.0: helper legacy. Endpoints novos devem usar
    `app.access.access_required("<rule_key>")`. Mantido por dois motivos:
      1. Tests existentes ainda fazem dependency_overrides[get_admin_user].
      2. Algumas chamadas em codigo (ex.: invariantes de RN-010 em users.py)
         precisam de "is_admin?" puro, nao ligado a uma celula da Matriz.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores",
        )
    return user
