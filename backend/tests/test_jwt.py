"""Tests for app.core.jwt — verify_token and JWKS cache.

We never call the real Supabase JWKS endpoint. Instead we generate our own
ES256 keypair, encode tokens with the private key, and inject a fake
_fetch_jwks coroutine that returns a JWKS dict built from the public key.
The HS256 path uses the shared secret already set in conftest.
"""
import json
import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from jwt import PyJWK
from jwt.algorithms import ECAlgorithm

import app.core.jwt as jwt_mod
from app.core.config import settings

# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_keypair():
    priv = ec.generate_private_key(ec.SECP256R1())
    return priv, priv.public_key()


def _make_jwks_dict(public_key, kid: str) -> dict:
    """Build a Supabase-shaped JWKS entry from a cryptography public key."""
    jwk_str = ECAlgorithm.to_jwk(public_key)
    jwk = json.loads(jwk_str) if isinstance(jwk_str, str) else jwk_str
    jwk["kid"] = kid
    jwk["alg"] = "ES256"
    jwk["use"] = "sig"
    return jwk


def _encode_es256(priv_key, kid: str, *, exp_offset: int = 3600, aud: str = "authenticated") -> str:
    return jwt.encode(
        {"sub": str(uuid.uuid4()), "aud": aud, "exp": int(time.time()) + exp_offset},
        priv_key,
        algorithm="ES256",
        headers={"kid": kid},
    )


def _encode_hs256(*, exp_offset: int = 3600, aud: str = "authenticated") -> str:
    return jwt.encode(
        {"sub": str(uuid.uuid4()), "aud": aud, "exp": int(time.time()) + exp_offset},
        settings.supabase_jwt_secret,
        algorithm="HS256",
    )


@pytest.fixture(autouse=True)
def _reset_jwks_cache():
    """Each test starts with a clean JWKS cache."""
    jwt_mod._jwks_cache = None
    jwt_mod._jwks_cached_at = 0.0
    yield
    jwt_mod._jwks_cache = None
    jwt_mod._jwks_cached_at = 0.0


# ── Algorithm restriction (ADR-014 hardening) ────────────────────────────────


async def test_verify_rejects_unallowed_algorithm():
    """HS384 is not in ALLOWED_ALGORITHMS, must be rejected outright."""
    token = jwt.encode(
        {"sub": "x", "aud": "authenticated", "exp": int(time.time()) + 3600},
        "any-secret",
        algorithm="HS384",
    )
    with pytest.raises(jwt.InvalidTokenError, match="not allowed"):
        await jwt_mod.verify_token(token)


async def test_verify_rejects_none_algorithm():
    """The classic 'alg: none' confusion attack must be blocked."""
    token = jwt.encode(
        {"sub": "x", "aud": "authenticated", "exp": int(time.time()) + 3600},
        key=None,
        algorithm=None,
    )
    with pytest.raises(jwt.InvalidTokenError, match="not allowed"):
        await jwt_mod.verify_token(token)


# ── HS256 path (legacy fallback) ─────────────────────────────────────────────


async def test_verify_hs256_success():
    token = _encode_hs256()
    payload = await jwt_mod.verify_token(token)
    assert payload["aud"] == "authenticated"


async def test_verify_hs256_expired():
    token = _encode_hs256(exp_offset=-100)
    with pytest.raises(jwt.ExpiredSignatureError):
        await jwt_mod.verify_token(token)


async def test_verify_hs256_wrong_audience():
    token = _encode_hs256(aud="other-audience")
    with pytest.raises(jwt.InvalidTokenError):
        await jwt_mod.verify_token(token)


# ── ES256 path (Supabase production) ─────────────────────────────────────────


async def test_verify_es256_success(monkeypatch):
    priv, pub = _make_keypair()
    jwks_entry = _make_jwks_dict(pub, "kid-1")

    async def fake_fetch():
        return {"kid-1": PyJWK.from_dict(jwks_entry)}

    monkeypatch.setattr(jwt_mod, "_fetch_jwks", fake_fetch)

    token = _encode_es256(priv, "kid-1")
    payload = await jwt_mod.verify_token(token)
    assert payload["aud"] == "authenticated"


async def test_verify_es256_unknown_kid(monkeypatch):
    """Token signed with kid that JWKS does not contain after refresh."""
    priv_known, pub_known = _make_keypair()
    priv_unknown, _ = _make_keypair()
    jwks_entry = _make_jwks_dict(pub_known, "known-kid")

    async def fake_fetch():
        return {"known-kid": PyJWK.from_dict(jwks_entry)}

    monkeypatch.setattr(jwt_mod, "_fetch_jwks", fake_fetch)

    token = _encode_es256(priv_unknown, "ghost-kid")
    with pytest.raises(jwt.InvalidTokenError, match="ghost-kid"):
        await jwt_mod.verify_token(token)


async def test_verify_es256_expired(monkeypatch):
    priv, pub = _make_keypair()

    async def fake_fetch():
        return {"k": PyJWK.from_dict(_make_jwks_dict(pub, "k"))}

    monkeypatch.setattr(jwt_mod, "_fetch_jwks", fake_fetch)

    token = _encode_es256(priv, "k", exp_offset=-100)
    with pytest.raises(jwt.ExpiredSignatureError):
        await jwt_mod.verify_token(token)


# ── JWKS cache (TTL + miss refresh + dedupe) ─────────────────────────────────


async def test_jwks_cache_reuses_within_ttl(monkeypatch):
    """Two consecutive verifications must hit the network only once."""
    priv, pub = _make_keypair()
    fetch_count = 0

    async def fake_fetch():
        nonlocal fetch_count
        fetch_count += 1
        return {"k": PyJWK.from_dict(_make_jwks_dict(pub, "k"))}

    monkeypatch.setattr(jwt_mod, "_fetch_jwks", fake_fetch)

    token = _encode_es256(priv, "k")
    await jwt_mod.verify_token(token)
    await jwt_mod.verify_token(token)
    await jwt_mod.verify_token(token)
    assert fetch_count == 1


async def test_jwks_cache_refreshes_after_ttl_expiry(monkeypatch):
    priv, pub = _make_keypair()
    fetch_count = 0

    async def fake_fetch():
        nonlocal fetch_count
        fetch_count += 1
        return {"k": PyJWK.from_dict(_make_jwks_dict(pub, "k"))}

    monkeypatch.setattr(jwt_mod, "_fetch_jwks", fake_fetch)

    token = _encode_es256(priv, "k")
    await jwt_mod.verify_token(token)
    assert fetch_count == 1

    # Simulate TTL expiry by rewinding cached_at far into the past.
    jwt_mod._jwks_cached_at = time.monotonic() - (jwt_mod.JWKS_CACHE_TTL_SECONDS + 10)

    await jwt_mod.verify_token(token)
    assert fetch_count == 2


async def test_jwks_cache_refreshes_on_unknown_kid(monkeypatch):
    """Key rotation: a token with a kid not in cache triggers a refresh."""
    priv1, pub1 = _make_keypair()
    priv2, pub2 = _make_keypair()
    fetch_count = 0

    state = {"keys": {"kid-1": PyJWK.from_dict(_make_jwks_dict(pub1, "kid-1"))}}

    async def fake_fetch():
        nonlocal fetch_count
        fetch_count += 1
        return state["keys"]

    monkeypatch.setattr(jwt_mod, "_fetch_jwks", fake_fetch)

    # First token, cache populated with kid-1 only
    await jwt_mod.verify_token(_encode_es256(priv1, "kid-1"))
    assert fetch_count == 1

    # Key rotation happens upstream: now Supabase has both kid-1 and kid-2
    state["keys"] = {
        "kid-1": PyJWK.from_dict(_make_jwks_dict(pub1, "kid-1")),
        "kid-2": PyJWK.from_dict(_make_jwks_dict(pub2, "kid-2")),
    }

    # Token with new kid-2 → cache miss → refresh
    await jwt_mod.verify_token(_encode_es256(priv2, "kid-2"))
    assert fetch_count == 2

    # Subsequent calls with kid-2 reuse the refreshed cache
    await jwt_mod.verify_token(_encode_es256(priv2, "kid-2"))
    assert fetch_count == 2
