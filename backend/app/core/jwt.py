"""JWT verification for Supabase Auth tokens.

Supabase projects may use ES256 (ECDSA) or HS256 (HMAC) for signing JWTs.
This module detects the algorithm from the token header and verifies accordingly:
  - ES256: public key fetched from Supabase JWKS endpoint (cached in-memory)
  - HS256: shared secret from SUPABASE_JWT_SECRET env var (legacy projects)

We NEVER emit tokens — only verify.
"""

import logging

import httpx
import jwt
from jwt import PyJWK

from app.core.config import settings

logger = logging.getLogger(__name__)

_jwks_cache: dict[str, PyJWK] | None = None


def _fetch_jwks() -> dict[str, PyJWK]:
    """Fetch JWKS from Supabase and return a {kid: PyJWK} mapping."""
    url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    resp = httpx.get(url, headers={"apikey": settings.supabase_anon_key}, timeout=10)
    resp.raise_for_status()
    keys = resp.json()["keys"]
    logger.info("JWKS fetched: %d key(s)", len(keys))
    return {k["kid"]: PyJWK.from_dict(k) for k in keys}


def _get_signing_key(token: str) -> PyJWK:
    """Resolve the signing key for a token via JWKS (with cache + refresh)."""
    global _jwks_cache
    if _jwks_cache is None:
        _jwks_cache = _fetch_jwks()

    header = jwt.get_unverified_header(token)
    kid = header.get("kid")

    if kid and kid in _jwks_cache:
        return _jwks_cache[kid]

    # Cache miss — refresh (key rotation scenario)
    logger.info("JWKS cache miss for kid=%s, refreshing", kid)
    _jwks_cache = _fetch_jwks()

    if kid and kid in _jwks_cache:
        return _jwks_cache[kid]

    raise jwt.InvalidTokenError(f"Key {kid} not found in JWKS")


def verify_token(token: str) -> dict:
    """Verify and decode a Supabase JWT. Returns the decoded payload.

    Detects ES256 vs HS256 from the token header.
    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.
    """
    header = jwt.get_unverified_header(token)
    alg = header.get("alg")

    if alg == "ES256":
        signing_key = _get_signing_key(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
        )

    # Fallback: HS256 (legacy Supabase projects)
    return jwt.decode(
        token,
        settings.supabase_jwt_secret,
        algorithms=["HS256"],
        audience="authenticated",
    )
