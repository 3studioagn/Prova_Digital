"""Tests for the /health, /health/db and /health/r2 endpoints in main.py.

The DB and R2 health checks have non-trivial fallback logic — they were
flagged in the audit (Bloco 3.4) for having no test coverage. These tests
mock the SQLAlchemy session, the Supabase REST fallback, and the boto3
client so we never touch external systems.
"""
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "http://test"


# ── /health ──────────────────────────────────────────────────────────────────


async def test_health_returns_ok():
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── /health/db ───────────────────────────────────────────────────────────────


def _mock_async_session_success():
    """Build a context-manager mock that simulates a successful SELECT 1."""
    result = MagicMock()
    result.scalar.return_value = 1
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)

    factory = MagicMock(return_value=cm)
    return factory


def _mock_async_session_failure(exc: Exception):
    """Build a session factory whose context manager raises on enter."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(side_effect=exc)
    cm.__aexit__ = AsyncMock(return_value=None)

    factory = MagicMock(return_value=cm)
    return factory


async def test_health_db_pooler_success():
    factory = _mock_async_session_success()
    with patch("app.main.async_session", factory):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get("/health/db")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"
    assert body["method"] == "pooler"


async def test_health_db_falls_back_to_rest_when_pooler_fails():
    """Pooler down → must try Supabase REST and report method='rest_api'."""
    factory = _mock_async_session_failure(ConnectionError("pooler unreachable"))

    rest_resp = MagicMock()
    rest_resp.status_code = 200

    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=None)
    fake_client.get = AsyncMock(return_value=rest_resp)

    with (
        patch("app.main.async_session", factory),
        patch("app.main.httpx.AsyncClient", return_value=fake_client),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get("/health/db")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["method"] == "rest_api"
    fake_client.get.assert_called_once()


async def test_health_db_returns_error_when_both_fail():
    factory = _mock_async_session_failure(ConnectionError("pooler unreachable"))

    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=None)
    fake_client.get = AsyncMock(side_effect=ConnectionError("rest unreachable"))

    with (
        patch("app.main.async_session", factory),
        patch("app.main.httpx.AsyncClient", return_value=fake_client),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get("/health/db")

    assert resp.status_code == 200  # endpoint always returns 200, status flag carries the verdict
    body = resp.json()
    assert body["status"] == "error"
    assert "pooler unreachable" in body["database"]


async def test_health_db_rest_5xx_falls_through_to_error():
    """If REST returns 5xx, the fallback should NOT claim success."""
    factory = _mock_async_session_failure(ConnectionError("pooler unreachable"))

    rest_resp = MagicMock()
    rest_resp.status_code = 503

    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=None)
    fake_client.get = AsyncMock(return_value=rest_resp)

    with (
        patch("app.main.async_session", factory),
        patch("app.main.httpx.AsyncClient", return_value=fake_client),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get("/health/db")

    body = resp.json()
    assert body["status"] == "error"


# ── /health/r2 ───────────────────────────────────────────────────────────────


async def test_health_r2_success():
    fake_client = MagicMock()
    fake_client.head_bucket = MagicMock(return_value={})

    with patch("app.main.get_r2_client", return_value=fake_client):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get("/health/r2")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["r2"] == "connected"
    assert body["bucket"]
    fake_client.head_bucket.assert_called_once()


async def test_health_r2_failure_returns_error():
    fake_client = MagicMock()
    fake_client.head_bucket = MagicMock(side_effect=Exception("AccessDenied"))

    with patch("app.main.get_r2_client", return_value=fake_client):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get("/health/r2")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "error"
    assert "AccessDenied" in body["r2"]
