"""Unit tests para app/services/report_cache.py (Wave 5, Componente 16).

Cobre:
  - get/set/invalidate/clear basicos.
  - TTL: cache hit antes do expirar, miss depois.
  - Lazy expiration no get().
  - purge_expired().
  - Singleton default + reset (uso em testes).
  - Configuracao via env var REPORTS_CACHE_TTL_SECONDS.

Asyncio_mode = "auto" (configurado em pyproject.toml) — async def's sao
auto-tratados como tests assincronos.
"""
import asyncio
import os
import time

import pytest
from pydantic import BaseModel

from app.services.report_cache import (
    DEFAULT_TTL_SECONDS,
    CacheEntry,
    ReportCache,
    _resolve_ttl,
    get_default_cache,
    get_default_cache_async,
    reset_default_cache,
)

# ─── Helper payload (Pydantic BaseModel arbitrario) ───────────────────────


class _DummyPayload(BaseModel):
    chave: str
    contagem: int


def _make_payload(chave: str = "x", contagem: int = 1) -> _DummyPayload:
    return _DummyPayload(chave=chave, contagem=contagem)


# ─── ReportCache: get/set/invalidate ──────────────────────────────────────


class TestReportCacheBasico:
    async def test_get_em_cache_vazio_retorna_none(self):
        cache = ReportCache(ttl_seconds=60)
        assert await cache.get("nonexistent") is None

    async def test_set_e_get_sucesso(self):
        cache = ReportCache(ttl_seconds=60)
        payload = _make_payload("a", 1)
        await cache.set("k1", payload, '"etag1"')

        entry = await cache.get("k1")
        assert entry is not None
        assert entry.payload == payload
        assert entry.etag == '"etag1"'

    async def test_set_substitui_existente(self):
        cache = ReportCache(ttl_seconds=60)
        await cache.set("k", _make_payload("a", 1), '"etag-a"')
        await cache.set("k", _make_payload("b", 2), '"etag-b"')

        entry = await cache.get("k")
        assert entry.payload.chave == "b"
        assert entry.etag == '"etag-b"'

    async def test_invalidate_remove(self):
        cache = ReportCache(ttl_seconds=60)
        await cache.set("k", _make_payload(), '"e"')

        removed = await cache.invalidate("k")
        assert removed is True
        assert await cache.get("k") is None

    async def test_invalidate_inexistente_retorna_false(self):
        cache = ReportCache(ttl_seconds=60)
        removed = await cache.invalidate("never-existed")
        assert removed is False

    async def test_clear_limpa_tudo(self):
        cache = ReportCache(ttl_seconds=60)
        await cache.set("a", _make_payload(), '"x"')
        await cache.set("b", _make_payload(), '"y"')
        assert cache.size == 2

        await cache.clear()
        assert cache.size == 0
        assert await cache.get("a") is None


# ─── ReportCache: TTL ─────────────────────────────────────────────────────


class TestReportCacheTTL:
    async def test_get_dentro_do_ttl_retorna_entry(self):
        cache = ReportCache(ttl_seconds=60)
        await cache.set("k", _make_payload(), '"e"')
        # imediatamente apos set — dentro do TTL
        entry = await cache.get("k")
        assert entry is not None

    async def test_ttl_zero_expira_imediatamente(self):
        """ReportCache(ttl_seconds=0) — entry expira no mesmo instante."""
        cache = ReportCache(ttl_seconds=0)
        await cache.set("k", _make_payload(), '"e"')
        # `time.monotonic()` apos `set` ja excedeu o TTL=0
        # (expires_at = monotonic_set + 0 == monotonic_set <= monotonic_get)
        entry = await cache.get("k")
        assert entry is None

    async def test_lazy_expiration_no_get(self):
        """Apos TTL expirar, `get()` deve limpar e retornar None."""
        cache = ReportCache(ttl_seconds=0)
        await cache.set("k", _make_payload(), '"e"')
        assert cache.size == 1

        # get() deve detectar expiracao e remover
        await cache.get("k")
        assert cache.size == 0

    async def test_purge_expired_remove_apenas_expirados(self):
        """Mistura: 1 expirado, 1 valido. Purge deve remover so o expirado."""
        cache_short = ReportCache(ttl_seconds=0)
        await cache_short.set("expired", _make_payload(), '"e"')

        # Cache "valido" tem outra instancia. Para misturar no mesmo cache,
        # usamos manipulacao direta:
        cache = ReportCache(ttl_seconds=60)
        await cache.set("valid", _make_payload(), '"v"')
        # Inserir uma entrada expirada manualmente
        cache._store["expired"] = CacheEntry(
            expires_at_monotonic=time.monotonic() - 1,
            payload=_make_payload(),
            etag='"old"',
        )
        assert cache.size == 2

        removed = await cache.purge_expired()
        assert removed == 1
        assert cache.size == 1
        assert await cache.get("valid") is not None
        assert await cache.get("expired") is None

    async def test_size_property(self):
        cache = ReportCache(ttl_seconds=60)
        assert cache.size == 0
        await cache.set("a", _make_payload(), '"e"')
        assert cache.size == 1
        await cache.set("b", _make_payload(), '"f"')
        assert cache.size == 2

    async def test_ttl_seconds_property(self):
        cache = ReportCache(ttl_seconds=120)
        assert cache.ttl_seconds == 120


# ─── Concorrencia (Lock) ──────────────────────────────────────────────────


class TestReportCacheConcorrencia:
    async def test_set_concorrente_nao_corrompe(self):
        """Multiplas coroutines escrevendo a mesma chave terminam consistentes."""
        cache = ReportCache(ttl_seconds=60)

        async def writer(i: int):
            await cache.set("shared", _make_payload(f"v{i}", i), f'"etag{i}"')

        # 50 writers concorrentes
        await asyncio.gather(*[writer(i) for i in range(50)])

        # Estado final deve ser uma das escritas (qualquer i de 0 a 49)
        entry = await cache.get("shared")
        assert entry is not None
        assert cache.size == 1  # so 1 chave, nao 50

    async def test_get_durante_set_nao_intercala(self):
        """get/set sob Lock — nao ve estado intermediario."""
        cache = ReportCache(ttl_seconds=60)
        await cache.set("k", _make_payload("inicial"), '"e1"')

        async def reader_burst():
            for _ in range(20):
                entry = await cache.get("k")
                # Nunca deve ver entry parcialmente populado
                assert entry is not None
                assert entry.payload.chave in ("inicial", "novo")
                assert entry.etag in ('"e1"', '"e2"')

        async def writer():
            await asyncio.sleep(0.001)
            await cache.set("k", _make_payload("novo"), '"e2"')

        await asyncio.gather(reader_burst(), writer())


# ─── Singleton default ────────────────────────────────────────────────────


class TestSingletonDefault:
    def teardown_method(self):
        """Limpa singleton entre testes para evitar vazamento de estado."""
        reset_default_cache()

    def test_get_default_cache_retorna_instancia(self):
        cache = get_default_cache()
        assert isinstance(cache, ReportCache)

    def test_get_default_cache_e_idempotente(self):
        a = get_default_cache()
        b = get_default_cache()
        assert a is b

    async def test_get_default_cache_async_e_thread_safe(self):
        async def fetch():
            return await get_default_cache_async()

        # Multiplas coroutines pegando default em paralelo
        results = await asyncio.gather(*[fetch() for _ in range(20)])

        # Todas devem retornar a mesma instancia
        first = results[0]
        assert all(r is first for r in results)

    def test_reset_default_cache_substitui_instancia(self):
        old = get_default_cache()
        new = reset_default_cache()
        assert old is not new
        assert get_default_cache() is new

    def test_reset_default_cache_com_ttl_custom(self):
        custom = reset_default_cache(new_ttl=15)
        assert custom.ttl_seconds == 15


# ─── Resolucao de TTL via env var ─────────────────────────────────────────


class TestResolveTtl:
    def setup_method(self):
        # Salva env var existente para restaurar depois
        self._saved = os.environ.get("REPORTS_CACHE_TTL_SECONDS")
        os.environ.pop("REPORTS_CACHE_TTL_SECONDS", None)

    def teardown_method(self):
        if self._saved is not None:
            os.environ["REPORTS_CACHE_TTL_SECONDS"] = self._saved
        else:
            os.environ.pop("REPORTS_CACHE_TTL_SECONDS", None)

    def test_default_quando_env_ausente(self):
        assert _resolve_ttl() == DEFAULT_TTL_SECONDS

    def test_le_da_env_var(self):
        os.environ["REPORTS_CACHE_TTL_SECONDS"] = "120"
        assert _resolve_ttl() == 120

    def test_invalido_volta_para_default(self):
        os.environ["REPORTS_CACHE_TTL_SECONDS"] = "not-a-number"
        assert _resolve_ttl() == DEFAULT_TTL_SECONDS

    def test_zero_volta_para_default(self):
        """TTL <= 0 e invalido — volta para default."""
        os.environ["REPORTS_CACHE_TTL_SECONDS"] = "0"
        assert _resolve_ttl() == DEFAULT_TTL_SECONDS

    def test_negativo_volta_para_default(self):
        os.environ["REPORTS_CACHE_TTL_SECONDS"] = "-30"
        assert _resolve_ttl() == DEFAULT_TTL_SECONDS

    def test_ttl_explicit_no_construtor_ignora_env(self):
        os.environ["REPORTS_CACHE_TTL_SECONDS"] = "999"
        cache = ReportCache(ttl_seconds=42)
        assert cache.ttl_seconds == 42


# ─── CacheEntry imutavel ──────────────────────────────────────────────────


class TestCacheEntry:
    def test_frozen_dataclass(self):
        entry = CacheEntry(
            expires_at_monotonic=time.monotonic() + 60,
            payload=_make_payload(),
            etag='"e"',
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            entry.etag = '"other"'  # type: ignore[misc]

    def test_slots(self):
        """slots=True => sem __dict__."""
        entry = CacheEntry(
            expires_at_monotonic=0.0,
            payload=_make_payload(),
            etag='"e"',
        )
        assert not hasattr(entry, "__dict__")
