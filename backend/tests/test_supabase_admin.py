"""Tests for app.core.supabase_admin — GoTrue Admin API client.

We replace httpx.AsyncClient with a fake context manager that records the
request and returns a controlled response. We never hit the network.
"""
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.core.config import settings
from app.core.supabase_admin import (
    _admin_headers,
    create_auth_user,
    delete_auth_user,
    disable_auth_user,
    enable_auth_user,
)

# ── Helpers ──────────────────────────────────────────────────────────────────


class _FakeAsyncClient:
    """Minimal stand-in for httpx.AsyncClient used in tests.

    Acts as an async context manager. Records every request so the test can
    assert on it. Returns a pre-built response from each verb.
    """

    def __init__(self, response):
        self._response = response
        self.calls: list[tuple[str, str, dict]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return self._response

    async def delete(self, url, **kwargs):
        self.calls.append(("DELETE", url, kwargs))
        return self._response

    async def put(self, url, **kwargs):
        self.calls.append(("PUT", url, kwargs))
        return self._response


def _make_response(
    *,
    status_code: int = 200,
    json_data: dict | None = None,
    text: str = "",
) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.is_success = 200 <= status_code < 300
    resp.text = text
    resp.json = MagicMock(return_value=json_data or {})
    if resp.is_success:
        resp.raise_for_status = MagicMock()
    else:
        request = MagicMock()
        resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("HTTP error", request=request, response=resp)
        )
    return resp


# ── _admin_headers ───────────────────────────────────────────────────────────


def test_admin_headers_uses_service_role_key():
    headers = _admin_headers()
    assert headers["apikey"] == settings.supabase_service_role_key
    assert headers["Authorization"] == f"Bearer {settings.supabase_service_role_key}"
    assert headers["Content-Type"] == "application/json"


# ── create_auth_user ─────────────────────────────────────────────────────────


async def test_create_auth_user_success():
    fake_uid = "11111111-2222-3333-4444-555555555555"
    fake_client = _FakeAsyncClient(_make_response(json_data={"id": fake_uid}))

    with patch("app.core.supabase_admin.httpx.AsyncClient", return_value=fake_client):
        uid = await create_auth_user("user@example.com", "SuperSecret1!")

    assert uid == fake_uid
    assert len(fake_client.calls) == 1
    method, url, kwargs = fake_client.calls[0]
    assert method == "POST"
    assert url.endswith("/auth/v1/admin/users")
    assert kwargs["json"] == {
        "email": "user@example.com",
        "password": "SuperSecret1!",
        "email_confirm": True,
    }
    assert kwargs["headers"]["apikey"] == settings.supabase_service_role_key


async def test_create_auth_user_http_error_propagates():
    """A 4xx/5xx from Supabase must propagate to the caller (so the route can 502)."""
    fake_client = _FakeAsyncClient(
        _make_response(status_code=422, json_data={"error": "invalid email"}, text="invalid email")
    )

    with patch("app.core.supabase_admin.httpx.AsyncClient", return_value=fake_client):
        with pytest.raises(httpx.HTTPStatusError):
            await create_auth_user("bad", "pwd")


# ── delete_auth_user ─────────────────────────────────────────────────────────


async def test_delete_auth_user_success():
    fake_client = _FakeAsyncClient(_make_response(status_code=200))
    uid = "delete-me"

    with patch("app.core.supabase_admin.httpx.AsyncClient", return_value=fake_client):
        await delete_auth_user(uid)

    method, url, _ = fake_client.calls[0]
    assert method == "DELETE"
    assert url.endswith(f"/auth/v1/admin/users/{uid}")


async def test_delete_auth_user_failure_does_not_raise(caplog):
    """Best-effort rollback: a failure must NOT raise — it only logs.

    Why: this function runs as part of a fallback path after a DB error has
    already been raised. Throwing here would mask the original failure.
    """
    fake_client = _FakeAsyncClient(_make_response(status_code=500, text="boom"))

    with patch("app.core.supabase_admin.httpx.AsyncClient", return_value=fake_client):
        await delete_auth_user("ghost-uid")  # must not raise

    assert any("Failed to rollback" in rec.message for rec in caplog.records)


# ── disable_auth_user ────────────────────────────────────────────────────────


async def test_disable_auth_user_success():
    fake_client = _FakeAsyncClient(_make_response(status_code=200))
    uid = "to-disable"

    with patch("app.core.supabase_admin.httpx.AsyncClient", return_value=fake_client):
        await disable_auth_user(uid)

    method, url, kwargs = fake_client.calls[0]
    assert method == "PUT"
    assert url.endswith(f"/auth/v1/admin/users/{uid}")
    # Long ban duration so existing tokens are rejected on refresh
    assert kwargs["json"] == {"ban_duration": "876600h"}


async def test_disable_auth_user_failure_raises():
    """Failure must propagate so the calling route can 502 and abort the request.

    Contract changed in Wave 1 audit (ADR-019/020): disable_auth_user is now
    called BEFORE the DB commit in PATCH/DELETE so a failure must abort the
    transaction. The previous best-effort behaviour caused real production
    drift (auth banned but app DB still ativo=true).
    """
    fake_client = _FakeAsyncClient(_make_response(status_code=503, text="upstream"))

    with patch("app.core.supabase_admin.httpx.AsyncClient", return_value=fake_client):
        with pytest.raises(httpx.HTTPStatusError):
            await disable_auth_user("ghost-uid")


# ── enable_auth_user ─────────────────────────────────────────────────────────


async def test_enable_auth_user_success():
    fake_client = _FakeAsyncClient(_make_response(status_code=200))
    uid = "to-enable"

    with patch("app.core.supabase_admin.httpx.AsyncClient", return_value=fake_client):
        await enable_auth_user(uid)

    method, url, kwargs = fake_client.calls[0]
    assert method == "PUT"
    assert url.endswith(f"/auth/v1/admin/users/{uid}")
    # ban_duration: "none" is the GoTrue convention to UNBAN a user.
    assert kwargs["json"] == {"ban_duration": "none"}


async def test_enable_auth_user_failure_raises():
    """Mirror of disable: failure must propagate so the route can 502 and roll back DB."""
    fake_client = _FakeAsyncClient(_make_response(status_code=500, text="boom"))

    with patch("app.core.supabase_admin.httpx.AsyncClient", return_value=fake_client):
        with pytest.raises(httpx.HTTPStatusError):
            await enable_auth_user("ghost-uid")
