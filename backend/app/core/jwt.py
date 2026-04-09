"""JWT verification for Supabase Auth tokens.

Supabase projects may use ES256 (ECDSA) or HS256 (HMAC) for signing JWTs.
This module detects the algorithm from the token header and verifies accordingly:
  - ES256: public key fetched from Supabase JWKS endpoint (cached in-memory, async)
  - HS256: shared secret from SUPABASE_JWT_SECRET env var (legacy projects)

We NEVER emit tokens — only verify.

All HTTP calls use httpx.AsyncClient to avoid blocking the event loop in async
FastAPI handlers (per ADR-008 pattern).
"""

import asyncio
import logging
import time

import httpx
import jwt
from jwt import PyJWK

from app.core.config import settings

logger = logging.getLogger(__name__)

# Algorithms we accept. Anything else is rejected explicitly to avoid
# algorithm-confusion attacks.
ALLOWED_ALGORITHMS = {"ES256", "HS256"}

# JWKS cache TTL — refresh proactively after this many seconds.
# Supabase rotates keys infrequently; 1h balances freshness vs HTTP overhead.
JWKS_CACHE_TTL_SECONDS = 3600

_jwks_cache: dict[str, PyJWK] | None = None
_jwks_cached_at: float = 0.0
_jwks_lock = asyncio.Lock()


async def _fetch_jwks() -> dict[str, PyJWK]:
    """Fetch JWKS from Supabase and return a {kid: PyJWK} mapping.

    Async to avoid blocking the event loop. Called on first verification,
    on cache miss (key rotation), and on TTL expiry.
    """
    url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers={"apikey": settings.supabase_anon_key})
        resp.raise_for_status()
        keys = resp.json()["keys"]
    logger.info("JWKS fetched: %d key(s)", len(keys))
    return {k["kid"]: PyJWK.from_dict(k) for k in keys}


def _cache_is_fresh() -> bool:
    return (
        _jwks_cache is not None
        and (time.monotonic() - _jwks_cached_at) < JWKS_CACHE_TTL_SECONDS
    )


async def _get_signing_key(token: str) -> PyJWK:
    """Resolve the signing key for a token via JWKS (with cache + TTL + refresh).

    Cache rules:
      - First request or expired TTL → fetch fresh JWKS
      - kid not found in cache → refresh (handles key rotation between TTLs)
      - asyncio.Lock prevents thundering herd on first load / refresh
    """
    global _jwks_cache, _jwks_cached_at

    header = jwt.get_unverified_header(token)
    kid = header.get("kid")

    # Fast path: cache fresh AND kid present
    if _cache_is_fresh() and kid and kid in _jwks_cache:  # type: ignore[operator]
        return _jwks_cache[kid]  # type: ignore[index]

    # Slow path: lock + (re)fetch
    async with _jwks_lock:
        # Re-check after acquiring lock (another coroutine may have populated)
        if _cache_is_fresh() and kid and kid in _jwks_cache:  # type: ignore[operator]
            return _jwks_cache[kid]  # type: ignore[index]

        if _jwks_cache is None:
            logger.info("JWKS cache empty, fetching")
        elif not _cache_is_fresh():
            logger.info("JWKS cache TTL expired, refreshing")
        else:
            logger.info("JWKS cache miss for kid=%s, refreshing", kid)

        _jwks_cache = await _fetch_jwks()
        _jwks_cached_at = time.monotonic()

    if kid and kid in _jwks_cache:
        return _jwks_cache[kid]

    raise jwt.InvalidTokenError(f"Key {kid} not found in JWKS")


async def verify_token(token: str) -> dict:
    """Verify and decode a Supabase JWT. Returns the decoded payload.

    Detects ES256 vs HS256 from the token header and rejects any other
    algorithm to prevent algorithm-confusion attacks.

    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.
    """
    header = jwt.get_unverified_header(token)
    alg = header.get("alg")

    if alg not in ALLOWED_ALGORITHMS:
        raise jwt.InvalidTokenError(f"Algorithm not allowed: {alg!r}")

    if alg == "ES256":
        signing_key = await _get_signing_key(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
        )

    # alg == "HS256" — legacy Supabase projects
    return jwt.decode(
        token,
        settings.supabase_jwt_secret,
        algorithms=["HS256"],
        audience="authenticated",
    )
