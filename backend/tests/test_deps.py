"""Tests for app.api.deps — auth dependencies.

Every protected endpoint goes through these. The integration tests in
test_users_api.py override the deps via dependency_overrides, so they don't
actually exercise the JWT-decoding path. These tests call the dependency
functions directly with hand-built JWTs and a fake AsyncSession.
"""
import time
import uuid
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps import get_admin_user, get_current_user
from app.core.config import settings
from app.db.models import LocalizacaoEnum, SetorEnum, Usuario
from tests.conftest import make_user

# ── Helpers ──────────────────────────────────────────────────────────────────


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _hs256_token(*, sub: str | None = None, exp_offset: int = 3600) -> str:
    payload: dict = {"aud": "authenticated", "exp": int(time.time()) + exp_offset}
    if sub is not None:
        payload["sub"] = sub
    return jwt.encode(payload, settings.supabase_jwt_secret, algorithm="HS256")


def _fake_db_returning(user: Usuario | None) -> AsyncMock:
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=result)
    return db


# ── get_current_user ─────────────────────────────────────────────────────────


async def test_get_current_user_missing_credentials_raises_401():
    db = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=None, db=db)
    assert exc.value.status_code == 401
    assert "ausente" in exc.value.detail.lower()


async def test_get_current_user_expired_token_raises_401():
    token = _hs256_token(sub=str(uuid.uuid4()), exp_offset=-100)
    db = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=_bearer(token), db=db)
    assert exc.value.status_code == 401
    assert "expirado" in exc.value.detail.lower()


async def test_get_current_user_garbage_token_raises_401():
    db = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=_bearer("not.a.jwt"), db=db)
    assert exc.value.status_code == 401
    assert "invalido" in exc.value.detail.lower()


async def test_get_current_user_token_without_sub_raises_401():
    token = _hs256_token(sub=None)  # no sub in payload
    db = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=_bearer(token), db=db)
    assert exc.value.status_code == 401


async def test_get_current_user_sub_not_uuid_raises_401():
    token = _hs256_token(sub="not-a-uuid")
    db = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=_bearer(token), db=db)
    assert exc.value.status_code == 401


async def test_get_current_user_unknown_user_raises_401():
    """Token is valid but DB has no row for this auth_uid."""
    token = _hs256_token(sub=str(uuid.uuid4()))
    db = _fake_db_returning(None)
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=_bearer(token), db=db)
    assert exc.value.status_code == 401
    assert "encontrado" in exc.value.detail.lower()


async def test_get_current_user_deactivated_raises_403():
    auth_uid = uuid.uuid4()
    inactive_user = make_user(auth_uid=auth_uid, ativo=False)
    token = _hs256_token(sub=str(auth_uid))
    db = _fake_db_returning(inactive_user)

    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=_bearer(token), db=db)
    assert exc.value.status_code == 403
    assert "desativado" in exc.value.detail.lower()


async def test_get_current_user_success_returns_usuario():
    auth_uid = uuid.uuid4()
    active_user = make_user(auth_uid=auth_uid, ativo=True, setor=SetorEnum.STUDIO)
    token = _hs256_token(sub=str(auth_uid))
    db = _fake_db_returning(active_user)

    result = await get_current_user(credentials=_bearer(token), db=db)
    assert result is active_user


# ── get_admin_user ───────────────────────────────────────────────────────────


async def test_get_admin_user_admin_passes_through():
    admin = make_user(is_admin=True)
    result = await get_admin_user(user=admin)
    assert result is admin


async def test_get_admin_user_non_admin_raises_403():
    regular = make_user(is_admin=False, setor=SetorEnum.VENDEDOR,
                        localizacao=LocalizacaoEnum.MATRIZ)
    with pytest.raises(HTTPException) as exc:
        await get_admin_user(user=regular)
    assert exc.value.status_code == 403
    assert "administradores" in exc.value.detail.lower()


# require_role removido na Wave 1 v4.0 — factory nunca usado em producao.
# Endpoints novos usam app.access.access_required(rule_key) que consulta
# a Matriz de Acesso unificada (shared/access-matrix.json).
