"""Integration tests for /api/v1/users endpoints."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient

from app.api.deps import get_admin_user, get_current_user
from app.db.models import SetorEnum
from app.db.session import get_db
from app.main import app
from tests.conftest import make_user

BASE = "http://test"
PREFIX = "/api/v1/users"


# ── Helpers ──────────────────────────────────────────────────────────────────


def _scalar(val=None):
    r = MagicMock()
    r.scalar_one_or_none.return_value = val
    r.scalar.return_value = val
    return r


def _scalars(items):
    r = MagicMock()
    s = MagicMock()
    s.all.return_value = items
    r.scalars.return_value = s
    return r


def _setup(mock_db, *, admin=None, user=None):
    async def _get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _get_db
    if admin is not None:
        app.dependency_overrides[get_admin_user] = lambda: admin
        app.dependency_overrides[get_current_user] = lambda: admin
    elif user is not None:
        app.dependency_overrides[get_current_user] = lambda: user


async def _refresh_defaults(obj):
    """Simulate DB refresh by populating server-default fields."""
    if obj.id is None:
        obj.id = uuid.uuid4()
    if not hasattr(obj, "ativo") or obj.ativo is None:
        obj.ativo = True
    obj.created_at = datetime.now(timezone.utc)
    obj.updated_at = datetime.now(timezone.utc)


# ── GET /me ──────────────────────────────────────────────────────────────────


async def test_get_me_success(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@test.com"
    assert resp.json()["is_admin"] is True


async def test_get_me_no_auth(mock_db):
    _setup(mock_db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/me")
    assert resp.status_code == 401


# ── POST / ───────────────────────────────────────────────────────────────────


async def test_create_user_success(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.return_value = _scalar(None)  # no duplicate
    mock_db.refresh.side_effect = _refresh_defaults

    with patch("app.api.v1.users.create_auth_user", return_value=str(uuid.uuid4())):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(f"{PREFIX}/", json={
                "nome": "New User", "email": "new@test.com",
                "senha": "Pass1234", "setor": "STUDIO",
            })
    assert resp.status_code == 201
    data = resp.json()
    assert data["nome"] == "New User"
    assert data["email"] == "new@test.com"
    assert data["setor"] == "STUDIO"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


async def test_create_user_duplicate_email(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.return_value = _scalar(make_user(email="dup@test.com"))

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/", json={
            "nome": "Dup", "email": "dup@test.com",
            "senha": "Pass1234", "setor": "STUDIO",
        })
    assert resp.status_code == 409
    assert "Email ja cadastrado" in resp.json()["detail"]


async def test_create_user_not_admin(regular_user, mock_db):
    _setup(mock_db, user=regular_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/", json={
            "nome": "X", "email": "x@test.com",
            "senha": "Pass1234", "setor": "STUDIO",
        })
    assert resp.status_code == 403


async def test_create_user_vendedor_no_loc(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/", json={
            "nome": "V", "email": "v@test.com",
            "senha": "Pass1234", "setor": "VENDEDOR",
        })
    assert resp.status_code == 422


async def test_create_user_supabase_auth_error(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.return_value = _scalar(None)

    with patch("app.api.v1.users.create_auth_user", side_effect=Exception("Auth down")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(f"{PREFIX}/", json={
                "nome": "N", "email": "n@test.com",
                "senha": "Pass1234", "setor": "STUDIO",
            })
    assert resp.status_code == 502


async def test_create_user_db_error_rollbacks_auth(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.return_value = _scalar(None)
    mock_db.commit.side_effect = Exception("DB failure")

    auth_uid = str(uuid.uuid4())
    with (
        patch("app.api.v1.users.create_auth_user", return_value=auth_uid),
        patch("app.api.v1.users.delete_auth_user") as mock_delete,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(f"{PREFIX}/", json={
                "nome": "N", "email": "n@test.com",
                "senha": "Pass1234", "setor": "STUDIO",
            })
    assert resp.status_code == 500
    mock_delete.assert_called_once_with(auth_uid)
    mock_db.rollback.assert_called_once()


# ── GET / (list) ─────────────────────────────────────────────────────────────


async def test_list_users_success(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    u1 = make_user(nome="A", email="a@test.com")
    u2 = make_user(nome="B", email="b@test.com")
    mock_db.execute.side_effect = [_scalar(2), _scalars([u1, u2])]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/", params={"page": 1, "page_size": 20})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["pages"] == 1


async def test_list_users_not_admin(regular_user, mock_db):
    _setup(mock_db, user=regular_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/")
    assert resp.status_code == 403


async def test_list_users_empty(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = [_scalar(0), _scalars([])]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["items"] == []


# ── GET /{id} ────────────────────────────────────────────────────────────────


async def test_get_user_admin_sees_any(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    target = make_user(nome="Target", email="target@test.com")
    mock_db.execute.return_value = _scalar(target)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{target.id}")
    assert resp.status_code == 200
    assert resp.json()["nome"] == "Target"


async def test_get_user_self_access(regular_user, mock_db):
    _setup(mock_db, user=regular_user)
    mock_db.execute.return_value = _scalar(regular_user)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{regular_user.id}")
    assert resp.status_code == 200


async def test_get_user_forbidden_other(regular_user, mock_db):
    _setup(mock_db, user=regular_user)
    other = make_user(nome="Other", email="other@test.com")
    mock_db.execute.return_value = _scalar(other)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{other.id}")
    assert resp.status_code == 403


async def test_get_user_not_found(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.return_value = _scalar(None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── PATCH /{id} ──────────────────────────────────────────────────────────────


async def test_update_user_success(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    target = make_user(nome="Old", email="t@test.com")
    mock_db.execute.return_value = _scalar(target)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(f"{PREFIX}/{target.id}", json={"nome": "New"})
    assert resp.status_code == 200
    assert target.nome == "New"
    mock_db.commit.assert_called_once()


async def test_update_user_rn010_remove_own_admin(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.return_value = _scalar(admin_user)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(f"{PREFIX}/{admin_user.id}", json={"is_admin": False})
    assert resp.status_code == 409
    assert "admin" in resp.json()["detail"].lower()


async def test_update_user_rn010_deactivate_self(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.return_value = _scalar(admin_user)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(f"{PREFIX}/{admin_user.id}", json={"ativo": False})
    assert resp.status_code == 409


async def test_update_user_empty_body(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    target = make_user()
    mock_db.execute.return_value = _scalar(target)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(f"{PREFIX}/{target.id}", json={})
    assert resp.status_code == 422
    assert "Nenhum campo" in resp.json()["detail"]


async def test_update_user_vendedor_needs_loc(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    target = make_user(setor=SetorEnum.STUDIO)
    mock_db.execute.return_value = _scalar(target)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(f"{PREFIX}/{target.id}", json={"setor": "VENDEDOR"})
    assert resp.status_code == 422
    assert "localizacao" in resp.json()["detail"].lower()


async def test_update_user_not_found(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.return_value = _scalar(None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(f"{PREFIX}/{uuid.uuid4()}", json={"nome": "X"})
    assert resp.status_code == 404


# ── DELETE /{id} ─────────────────────────────────────────────────────────────


async def test_deactivate_user_success(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    target = make_user(nome="Target", email="t@test.com", ativo=True)
    mock_db.execute.return_value = _scalar(target)

    with patch("app.api.v1.users.disable_auth_user", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.delete(f"{PREFIX}/{target.id}")
    assert resp.status_code == 204
    assert target.ativo is False
    mock_db.commit.assert_called_once()


async def test_deactivate_user_rn010_self(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.return_value = _scalar(admin_user)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.delete(f"{PREFIX}/{admin_user.id}")
    assert resp.status_code == 409


async def test_deactivate_user_already_inactive(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    target = make_user(ativo=False)
    mock_db.execute.return_value = _scalar(target)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.delete(f"{PREFIX}/{target.id}")
    assert resp.status_code == 409


async def test_deactivate_user_not_found(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.return_value = _scalar(None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.delete(f"{PREFIX}/{uuid.uuid4()}")
    assert resp.status_code == 404
