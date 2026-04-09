"""Integration tests for /api/v1/users endpoints."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects import postgresql

from app.api.deps import get_admin_user, get_current_user
from app.db.models import LocalizacaoEnum, SetorEnum
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


# ── GET / list filters & pagination ─────────────────────────────────────────
#
# These tests capture every SQL statement passed to db.execute and compile it
# to a literal SQL string. We then assert the WHERE clause / OFFSET / LIMIT
# reflect the query params we sent. This way we test the actual SQL — not just
# whether the route accepts the params.


def _capture_list_stmts(mock_db, *, total: int = 0, items=None):
    """Wire mock_db so it records every executed stmt and yields count then rows."""
    captured: list = []

    async def _execute(stmt):
        captured.append(stmt)
        if len(captured) == 1:
            return _scalar(total)
        return _scalars(items or [])

    mock_db.execute = AsyncMock(side_effect=_execute)
    return captured


def _compiled_sql(stmt) -> str:
    """Compile to PostgreSQL SQL so ILIKE / boolean / etc render exactly as
    they will at runtime — the default dialect would mangle them (ilike →
    LOWER(...) LIKE LOWER(...))."""
    return str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


async def test_list_users_filter_by_setor(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    captured = _capture_list_stmts(mock_db)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/", params={"setor": "VENDEDOR"})
    assert resp.status_code == 200
    for stmt in captured:
        sql = _compiled_sql(stmt)
        assert "setor" in sql.lower()
        assert "VENDEDOR" in sql


async def test_list_users_filter_by_localizacao(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    captured = _capture_list_stmts(mock_db)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/", params={"localizacao": "FILIAL"})
    assert resp.status_code == 200
    for stmt in captured:
        sql = _compiled_sql(stmt)
        assert "localizacao" in sql.lower()
        assert "FILIAL" in sql


async def test_list_users_filter_by_ativo_true(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    captured = _capture_list_stmts(mock_db)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/", params={"ativo": "true"})
    assert resp.status_code == 200
    for stmt in captured:
        sql = _compiled_sql(stmt).lower()
        assert "ativo" in sql
        assert "true" in sql


async def test_list_users_filter_by_ativo_false(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    captured = _capture_list_stmts(mock_db)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/", params={"ativo": "false"})
    assert resp.status_code == 200
    for stmt in captured:
        sql = _compiled_sql(stmt).lower()
        assert "ativo" in sql
        assert "false" in sql


async def test_list_users_filter_by_busca_searches_nome_and_email(admin_user, mock_db):
    """Search must produce ILIKE on both nome and email columns."""
    _setup(mock_db, admin=admin_user)
    captured = _capture_list_stmts(mock_db)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/", params={"busca": "joao"})
    assert resp.status_code == 200
    for stmt in captured:
        sql = _compiled_sql(stmt).lower()
        assert "ilike" in sql
        assert "%joao%" in sql
        assert "nome" in sql
        assert "email" in sql


async def test_list_users_combined_filters(admin_user, mock_db):
    """All three filters at once must produce one WHERE per filter."""
    _setup(mock_db, admin=admin_user)
    captured = _capture_list_stmts(mock_db)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/", params={
            "setor": "VENDEDOR",
            "localizacao": "MATRIZ",
            "ativo": "true",
            "busca": "ana",
        })
    assert resp.status_code == 200
    select_sql = _compiled_sql(captured[1]).lower()
    assert "setor" in select_sql and "vendedor" in select_sql
    assert "localizacao" in select_sql and "matriz" in select_sql
    assert "ativo" in select_sql and "true" in select_sql
    assert "%ana%" in select_sql


async def test_list_users_pagination_offset_and_limit(admin_user, mock_db):
    """page=3 with page_size=15 must yield OFFSET 30 LIMIT 15."""
    _setup(mock_db, admin=admin_user)
    captured = _capture_list_stmts(mock_db, total=100)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/", params={"page": 3, "page_size": 15})
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 3
    assert data["page_size"] == 15
    assert data["total"] == 100
    assert data["pages"] == 7  # ceil(100/15)
    select_sql = _compiled_sql(captured[1]).lower()
    assert "offset 30" in select_sql
    assert "limit 15" in select_sql


async def test_list_users_invalid_setor_returns_422(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/", params={"setor": "INVALID"})
    assert resp.status_code == 422


async def test_list_users_invalid_localizacao_returns_422(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/", params={"localizacao": "MARS"})
    assert resp.status_code == 422


async def test_list_users_page_must_be_positive(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/", params={"page": 0})
    assert resp.status_code == 422


async def test_list_users_page_size_capped_at_100(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/", params={"page_size": 101})
    assert resp.status_code == 422


async def test_list_users_busca_max_length(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    long_q = "a" * 201
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/", params={"busca": long_q})
    assert resp.status_code == 422


# ── Last-active-admin protection (Bloco 2.4) ─────────────────────────────────
#
# System invariant: there must always be at least one is_admin=true AND
# ativo=true user. PATCH and DELETE both enforce this when the target is
# different from the caller (self-protection blocks the same-user case earlier).


def _bind_last_admin_count(mock_db, target, *, other_admins: int):
    """Wire mock_db so the first execute returns the target user and the
    second returns the count of OTHER active admins. Order matches the route."""
    mock_db.execute.side_effect = [
        _scalar(target),       # SELECT user by id
        _scalar(other_admins), # SELECT count() of other active admins
    ]


async def test_patch_blocks_demoting_last_admin(admin_user, mock_db):
    """PATCH is_admin=false on the only other admin must 409 when no others exist."""
    _setup(mock_db, admin=admin_user)
    target = make_user(nome="Other Admin", email="other@test.com", is_admin=True, ativo=True)
    _bind_last_admin_count(mock_db, target, other_admins=0)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(f"{PREFIX}/{target.id}", json={"is_admin": False})
    assert resp.status_code == 409
    assert "ultimo administrador" in resp.json()["detail"].lower()
    mock_db.commit.assert_not_called()


async def test_patch_allows_demoting_when_other_admins_exist(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    target = make_user(nome="Other Admin", email="other@test.com", is_admin=True, ativo=True)
    _bind_last_admin_count(mock_db, target, other_admins=2)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(f"{PREFIX}/{target.id}", json={"is_admin": False})
    assert resp.status_code == 200
    assert target.is_admin is False
    mock_db.commit.assert_called_once()


async def test_patch_blocks_deactivating_last_admin(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    target = make_user(nome="Other Admin", email="other@test.com", is_admin=True, ativo=True)
    _bind_last_admin_count(mock_db, target, other_admins=0)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(f"{PREFIX}/{target.id}", json={"ativo": False})
    assert resp.status_code == 409
    mock_db.commit.assert_not_called()


async def test_patch_skips_last_admin_check_for_non_admin_target(admin_user, mock_db):
    """Non-admin target — last-admin check must NOT run, only one execute call."""
    _setup(mock_db, admin=admin_user)
    target = make_user(nome="Vendedor", email="v@test.com", is_admin=False, ativo=True,
                       setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    mock_db.execute.return_value = _scalar(target)

    with patch("app.api.v1.users.disable_auth_user", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.patch(f"{PREFIX}/{target.id}", json={"ativo": False})
    assert resp.status_code == 200
    assert target.ativo is False
    # Exactly one DB call: the SELECT user. No count() needed.
    assert mock_db.execute.call_count == 1


async def test_patch_skips_last_admin_check_for_inactive_admin_target(admin_user, mock_db):
    """An already-inactive admin doesn't count as 'active' — no count needed."""
    _setup(mock_db, admin=admin_user)
    target = make_user(nome="Old Admin", email="old@test.com", is_admin=True, ativo=False)
    mock_db.execute.return_value = _scalar(target)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(f"{PREFIX}/{target.id}", json={"is_admin": False})
    assert resp.status_code == 200
    assert mock_db.execute.call_count == 1


async def test_delete_blocks_last_admin(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    target = make_user(nome="Other Admin", email="other@test.com", is_admin=True, ativo=True)
    _bind_last_admin_count(mock_db, target, other_admins=0)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.delete(f"{PREFIX}/{target.id}")
    assert resp.status_code == 409
    assert "ultimo administrador" in resp.json()["detail"].lower()
    assert target.ativo is True  # not flipped
    mock_db.commit.assert_not_called()


async def test_delete_allows_admin_when_others_exist(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    target = make_user(nome="Other Admin", email="other@test.com", is_admin=True, ativo=True)
    _bind_last_admin_count(mock_db, target, other_admins=1)

    with patch("app.api.v1.users.disable_auth_user", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.delete(f"{PREFIX}/{target.id}")
    assert resp.status_code == 204
    assert target.ativo is False
    mock_db.commit.assert_called_once()


async def test_delete_skips_last_admin_check_for_non_admin(admin_user, mock_db):
    """Non-admin target — exactly one DB call (the SELECT)."""
    _setup(mock_db, admin=admin_user)
    target = make_user(nome="Vendedor", email="v@test.com", is_admin=False, ativo=True,
                       setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    mock_db.execute.return_value = _scalar(target)

    with patch("app.api.v1.users.disable_auth_user", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.delete(f"{PREFIX}/{target.id}")
    assert resp.status_code == 204
    assert mock_db.execute.call_count == 1


# ── Auth sync on PATCH/DELETE (Wave 1 audit) ─────────────────────────────────
#
# Bug fixed in Wave 1 audit: PATCH used to ignore Supabase Auth state. A user
# whose ativo flipped false→true in app DB would still be banned in auth.users
# and unable to login (real production drift, see ADR-019). DELETE committed
# the soft-delete BEFORE banning, so a flaky auth call left the inverse drift.
#
# Contract now:
#   - PATCH/DELETE call disable/enable_auth_user BEFORE db.commit
#   - If the auth call fails → 502, no DB change
#   - If db.commit fails AFTER auth changed → compensate inversely


async def test_update_user_reactivation_unbans_in_auth(admin_user, mock_db):
    """PATCH ativo:false→true must call enable_auth_user before commit."""
    _setup(mock_db, admin=admin_user)
    target = make_user(nome="Reborn", email="r@test.com", ativo=False)
    mock_db.execute.return_value = _scalar(target)

    with patch("app.api.v1.users.enable_auth_user", new_callable=AsyncMock) as mock_enable:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.patch(f"{PREFIX}/{target.id}", json={"ativo": True})
    assert resp.status_code == 200
    assert target.ativo is True
    mock_enable.assert_awaited_once_with(str(target.auth_uid))
    mock_db.commit.assert_called_once()


async def test_update_user_deactivation_bans_in_auth_before_commit(admin_user, mock_db):
    """PATCH ativo:true→false must call disable_auth_user BEFORE commit."""
    _setup(mock_db, admin=admin_user)
    target = make_user(nome="Bye", email="bye@test.com", ativo=True, is_admin=False)
    mock_db.execute.return_value = _scalar(target)

    call_order: list[str] = []
    mock_disable = AsyncMock(side_effect=lambda _uid: call_order.append("disable"))
    original_commit = mock_db.commit
    async def _tracked_commit():
        call_order.append("commit")
        return await original_commit()
    mock_db.commit = _tracked_commit

    with patch("app.api.v1.users.disable_auth_user", mock_disable):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.patch(f"{PREFIX}/{target.id}", json={"ativo": False})
    assert resp.status_code == 200
    assert target.ativo is False
    mock_disable.assert_awaited_once_with(str(target.auth_uid))
    assert call_order == ["disable", "commit"], (
        "disable_auth_user must run BEFORE db.commit, otherwise we re-introduce "
        "the production drift the audit found"
    )


async def test_update_user_unrelated_field_does_not_touch_auth(admin_user, mock_db):
    """Updating only nome must not call enable/disable — auth stays untouched."""
    _setup(mock_db, admin=admin_user)
    target = make_user(nome="Old", email="x@test.com", ativo=True)
    mock_db.execute.return_value = _scalar(target)

    with (
        patch("app.api.v1.users.disable_auth_user", new_callable=AsyncMock) as mock_disable,
        patch("app.api.v1.users.enable_auth_user", new_callable=AsyncMock) as mock_enable,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.patch(f"{PREFIX}/{target.id}", json={"nome": "New"})
    assert resp.status_code == 200
    mock_disable.assert_not_awaited()
    mock_enable.assert_not_awaited()


async def test_update_user_ban_failure_returns_502_and_does_not_commit(admin_user, mock_db):
    """If disable_auth_user fails on deactivation, return 502 and roll back."""
    _setup(mock_db, admin=admin_user)
    target = make_user(nome="X", email="x@test.com", ativo=True, is_admin=False)
    mock_db.execute.return_value = _scalar(target)

    with patch(
        "app.api.v1.users.disable_auth_user",
        new_callable=AsyncMock,
        side_effect=Exception("Auth down"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.patch(f"{PREFIX}/{target.id}", json={"ativo": False})
    assert resp.status_code == 502
    mock_db.commit.assert_not_called()
    mock_db.rollback.assert_called()


async def test_update_user_unban_failure_returns_502_and_does_not_commit(admin_user, mock_db):
    """If enable_auth_user fails on reactivation, return 502 and roll back."""
    _setup(mock_db, admin=admin_user)
    target = make_user(nome="X", email="x@test.com", ativo=False)
    mock_db.execute.return_value = _scalar(target)

    with patch(
        "app.api.v1.users.enable_auth_user",
        new_callable=AsyncMock,
        side_effect=Exception("Auth down"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.patch(f"{PREFIX}/{target.id}", json={"ativo": True})
    assert resp.status_code == 502
    mock_db.commit.assert_not_called()
    mock_db.rollback.assert_called()


async def test_update_user_db_commit_fails_after_ban_compensates(admin_user, mock_db):
    """If commit fails AFTER disable_auth_user succeeded, we must call enable to compensate."""
    _setup(mock_db, admin=admin_user)
    target = make_user(nome="X", email="x@test.com", ativo=True, is_admin=False)
    mock_db.execute.return_value = _scalar(target)
    mock_db.commit.side_effect = Exception("DB down")

    with (
        patch("app.api.v1.users.disable_auth_user", new_callable=AsyncMock) as mock_disable,
        patch("app.api.v1.users.enable_auth_user", new_callable=AsyncMock) as mock_enable,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.patch(f"{PREFIX}/{target.id}", json={"ativo": False})
    assert resp.status_code == 500
    mock_disable.assert_awaited_once_with(str(target.auth_uid))
    mock_enable.assert_awaited_once_with(str(target.auth_uid))


async def test_update_user_db_commit_fails_after_unban_compensates(admin_user, mock_db):
    """If commit fails AFTER enable_auth_user succeeded, we must call disable to compensate."""
    _setup(mock_db, admin=admin_user)
    target = make_user(nome="X", email="x@test.com", ativo=False)
    mock_db.execute.return_value = _scalar(target)
    mock_db.commit.side_effect = Exception("DB down")

    with (
        patch("app.api.v1.users.enable_auth_user", new_callable=AsyncMock) as mock_enable,
        patch("app.api.v1.users.disable_auth_user", new_callable=AsyncMock) as mock_disable,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.patch(f"{PREFIX}/{target.id}", json={"ativo": True})
    assert resp.status_code == 500
    mock_enable.assert_awaited_once_with(str(target.auth_uid))
    mock_disable.assert_awaited_once_with(str(target.auth_uid))


async def test_deactivate_user_disable_runs_before_commit(admin_user, mock_db):
    """DELETE: disable_auth_user must execute BEFORE db.commit (audit fix)."""
    _setup(mock_db, admin=admin_user)
    target = make_user(nome="X", email="x@test.com", ativo=True, is_admin=False)
    mock_db.execute.return_value = _scalar(target)

    call_order: list[str] = []
    mock_disable = AsyncMock(side_effect=lambda _uid: call_order.append("disable"))
    original_commit = mock_db.commit
    async def _tracked_commit():
        call_order.append("commit")
        return await original_commit()
    mock_db.commit = _tracked_commit

    with patch("app.api.v1.users.disable_auth_user", mock_disable):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.delete(f"{PREFIX}/{target.id}")
    assert resp.status_code == 204
    assert call_order == ["disable", "commit"]


async def test_deactivate_user_ban_failure_returns_502_and_does_not_commit(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    target = make_user(nome="X", email="x@test.com", ativo=True, is_admin=False)
    mock_db.execute.return_value = _scalar(target)

    with patch(
        "app.api.v1.users.disable_auth_user",
        new_callable=AsyncMock,
        side_effect=Exception("Auth down"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.delete(f"{PREFIX}/{target.id}")
    assert resp.status_code == 502
    assert target.ativo is True  # not flipped
    mock_db.commit.assert_not_called()


async def test_deactivate_user_db_commit_fails_after_ban_compensates(admin_user, mock_db):
    """DELETE: if commit fails after disable succeeded, enable must compensate."""
    _setup(mock_db, admin=admin_user)
    target = make_user(nome="X", email="x@test.com", ativo=True, is_admin=False)
    mock_db.execute.return_value = _scalar(target)
    mock_db.commit.side_effect = Exception("DB down")

    with (
        patch("app.api.v1.users.disable_auth_user", new_callable=AsyncMock) as mock_disable,
        patch("app.api.v1.users.enable_auth_user", new_callable=AsyncMock) as mock_enable,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.delete(f"{PREFIX}/{target.id}")
    assert resp.status_code == 500
    mock_disable.assert_awaited_once_with(str(target.auth_uid))
    mock_enable.assert_awaited_once_with(str(target.auth_uid))
