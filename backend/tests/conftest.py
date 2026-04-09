"""Test configuration and shared fixtures."""
import os
import uuid as _uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

# Set test env vars BEFORE any app import
os.environ.update({
    "SUPABASE_URL": "http://localhost:54321",
    "SUPABASE_ANON_KEY": "test-anon-key",
    "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
    "SUPABASE_JWT_SECRET": "super-secret-jwt-testing-key-min-32",
    "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/testdb",
    "R2_ACCOUNT_ID": "test-account",
    "R2_ACCESS_KEY_ID": "test-key",
    "R2_SECRET_ACCESS_KEY": "test-secret",
    "R2_ENDPOINT_URL": "http://localhost:9000",
    "QR_CODE_HMAC_SECRET": "test-hmac-secret-not-for-production-min-32-chars",
    "APP_ENV": "test",
    "APP_DEBUG": "false",
})

import pytest  # noqa: E402

from app.db.models import LocalizacaoEnum, SetorEnum, Usuario  # noqa: E402
from app.main import app  # noqa: E402


def make_user(
    *,
    id=None,
    auth_uid=None,
    nome="Test User",
    email="test@example.com",
    setor=SetorEnum.STUDIO,
    localizacao=None,
    is_admin=False,
    ativo=True,
    created_by=None,
):
    return Usuario(
        id=id or _uuid.uuid4(),
        auth_uid=auth_uid or _uuid.uuid4(),
        nome=nome,
        email=email,
        setor=setor,
        localizacao=localizacao,
        is_admin=is_admin,
        ativo=ativo,
        created_by=created_by,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def admin_user():
    return make_user(nome="Admin", email="admin@test.com", is_admin=True)


@pytest.fixture
def regular_user():
    return make_user(
        nome="Regular",
        email="regular@test.com",
        setor=SetorEnum.VENDEDOR,
        localizacao=LocalizacaoEnum.MATRIZ,
    )


@pytest.fixture
def vendedor_matriz():
    return make_user(
        nome="Vendedor Matriz",
        email="vendedor.matriz@test.com",
        setor=SetorEnum.VENDEDOR,
        localizacao=LocalizacaoEnum.MATRIZ,
    )


@pytest.fixture
def vendedor_filial():
    return make_user(
        nome="Vendedor Filial",
        email="vendedor.filial@test.com",
        setor=SetorEnum.VENDEDOR,
        localizacao=LocalizacaoEnum.FILIAL,
    )


@pytest.fixture
def mock_db():
    """Mock AsyncSession.

    SQLAlchemy's AsyncSession mixes sync methods (``add``, ``add_all``,
    ``expunge``, ``delete``) with async ones (``commit``, ``rollback``,
    ``refresh``, ``execute``). ``AsyncMock`` by itself would return a
    coroutine for every attribute access, including the sync ones — calling
    ``db.add(user)`` would then raise a ``RuntimeWarning: coroutine was never
    awaited``. We override the sync methods with plain ``MagicMock`` so they
    behave exactly like the real AsyncSession.
    """
    db = AsyncMock()
    db.add = MagicMock()
    db.add_all = MagicMock()
    db.expunge = MagicMock()
    db.expunge_all = MagicMock()
    db.delete = MagicMock()
    return db


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()
