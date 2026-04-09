"""Supabase Auth Admin API client.

Uses Service Role Key to manage auth.users via the GoTrue admin endpoints.
NEVER expose Service Role Key to the frontend.
"""
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def _admin_headers() -> dict[str, str]:
    return {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }


async def create_auth_user(email: str, password: str) -> str:
    """Create user in Supabase Auth. Returns the auth user's UUID string.

    Raises httpx.HTTPStatusError on failure.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{settings.supabase_url}/auth/v1/admin/users",
            headers=_admin_headers(),
            json={
                "email": email,
                "password": password,
                "email_confirm": True,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info("Auth user created: %s", data["id"])
        return data["id"]


async def delete_auth_user(auth_uid: str) -> None:
    """Delete user from Supabase Auth (rollback on app DB failure)."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.delete(
            f"{settings.supabase_url}/auth/v1/admin/users/{auth_uid}",
            headers=_admin_headers(),
        )
        if resp.is_success:
            logger.info("Auth user deleted (rollback): %s", auth_uid)
        else:
            logger.warning(
                "Failed to rollback auth user %s: %s", auth_uid, resp.text
            )


async def disable_auth_user(auth_uid: str) -> None:
    """Ban user in Supabase Auth so existing tokens are rejected on refresh.

    Raises httpx.HTTPStatusError on failure so the caller can roll back DB state
    when the auth state must stay in sync (PATCH ativo=false / DELETE soft-delete).
    """
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.put(
            f"{settings.supabase_url}/auth/v1/admin/users/{auth_uid}",
            headers=_admin_headers(),
            json={"ban_duration": "876600h"},  # ~100 years
        )
        resp.raise_for_status()
        logger.info("Auth user disabled: %s", auth_uid)


async def enable_auth_user(auth_uid: str) -> None:
    """Unban user in Supabase Auth so they can sign in again.

    Mirror of disable_auth_user — used when an admin reactivates a previously
    deactivated user via PATCH /users/{id} with ativo=true. Without this call,
    public.usuarios.ativo would say "active" but auth.users.banned_until would
    still block any login attempt, causing real production drift.

    Raises httpx.HTTPStatusError on failure so the caller can roll back DB state.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.put(
            f"{settings.supabase_url}/auth/v1/admin/users/{auth_uid}",
            headers=_admin_headers(),
            json={"ban_duration": "none"},
        )
        resp.raise_for_status()
        logger.info("Auth user enabled (unbanned): %s", auth_uid)
