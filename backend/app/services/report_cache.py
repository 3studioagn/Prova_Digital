"""Cache in-memory para Relatorios (Wave 5, Componente 16).

Coracao da estrategia 'minimizar queries' do WAVE5_ANALYSIS §4.4 (Camada 2).
Combinado com:
  - Camada 1 (HTTP/ETag/304): caller passa o ETag pre-calculado para evitar
    serializacao em cache hit.
  - Camada 3 (Realtime): frontend invalida ETag local ao detectar mudancas.
  - Camada 4 (SQLAlchemy compiled cache): elimina planning time dominante.

Caracteristicas:
  - **Asyncio-safe**: `asyncio.Lock` protege check-and-mutate.
  - **TTL configuravel**: default 60s (env var REPORTS_CACHE_TTL_SECONDS).
  - **Generico**: aceita qualquer Pydantic BaseModel como payload + ETag.
  - **Sem unbounded growth**: cache key e SHA-256 dos filtros (universo finito
    em uso real). Cada worker uvicorn tem seu cache; em volume real (3Studio,
    1-2 workers, 30 usuarios) o tamanho fica em <1000 entradas.

Uso tipico no handler (Bloco 5.2):

    cache = get_default_cache()
    key = to_cache_key(filters)

    entry = await cache.get(key)
    if entry is not None:
        # Cache hit — backend ja tem o ETag pre-calculado
        if request.headers.get("If-None-Match") == entry.etag:
            return Response(status_code=304, headers={"ETag": entry.etag})
        return JSONResponse(content=..., headers={"ETag": entry.etag})

    # Cache miss — executar query, montar payload, calcular ETag, armazenar
    payload = await _aggregate(filters, db)
    etag = compute_etag(payload)
    await cache.set(key, payload, etag)
    return JSONResponse(content=payload, headers={"ETag": etag})

Decisao: cache **por worker** (in-memory, sem Redis). Em escala N workers,
worst-case cold start = N queries; aceitavel para volume Wave 5 e simplifica
infra. Reavaliar em Wave 7+ se houver demanda.
"""
from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass

from pydantic import BaseModel

# ─── Configuracao ─────────────────────────────────────────────────────────


DEFAULT_TTL_SECONDS = 60
"""TTL default. Override via env var REPORTS_CACHE_TTL_SECONDS."""


def _resolve_ttl() -> int:
    """Le TTL da env var REPORTS_CACHE_TTL_SECONDS ou usa default."""
    raw = os.environ.get("REPORTS_CACHE_TTL_SECONDS")
    if raw is None:
        return DEFAULT_TTL_SECONDS
    try:
        value = int(raw)
    except (ValueError, TypeError):
        return DEFAULT_TTL_SECONDS
    return value if value > 0 else DEFAULT_TTL_SECONDS


# ─── Entry imutavel ───────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class CacheEntry:
    """Entrada armazenada no cache.

    Attributes:
        expires_at_monotonic: timestamp de expiracao (segundos do clock
          monotonico do processo). Comparar com `time.monotonic()`.
        payload: resposta Pydantic ja validada.
        etag: ETag pre-calculado (string entre aspas, ex: '"abc123..."').
    """

    expires_at_monotonic: float
    payload: BaseModel
    etag: str


# ─── Cache ────────────────────────────────────────────────────────────────


class ReportCache:
    """Cache TTL in-memory, asyncio-safe.

    Construir via `ReportCache(ttl_seconds=...)`. Para a instancia default
    do processo, usar `get_default_cache()`.

    Threading: protegido por `asyncio.Lock`. Em asyncio single-threaded,
    operacoes em `dict` sao atomicas em si mesmas; o Lock evita race entre
    coroutines durante `check then mutate`.
    """

    def __init__(self, ttl_seconds: int | None = None) -> None:
        self._ttl: int = ttl_seconds if ttl_seconds is not None else _resolve_ttl()
        self._store: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    @property
    def ttl_seconds(self) -> int:
        """TTL ativo do cache (segundos)."""
        return self._ttl

    @property
    def size(self) -> int:
        """Numero de entradas armazenadas (incluindo possivelmente expiradas
        que ainda nao foram limpas)."""
        return len(self._store)

    async def get(self, key: str) -> CacheEntry | None:
        """Retorna a entrada se existir e estiver dentro do TTL, senao None.

        Limpa entrada expirada se encontrada (lazy expiration).
        """
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.expires_at_monotonic <= time.monotonic():
                # Expirou — remove e retorna miss
                del self._store[key]
                return None
            return entry

    async def set(self, key: str, payload: BaseModel, etag: str) -> None:
        """Armazena nova entrada (ou substitui existente).

        Args:
            key: chave deterministica (use `to_cache_key(filters)`).
            payload: modelo Pydantic ja validado.
            etag: ETag pre-calculado (use `compute_etag(payload)`).
        """
        async with self._lock:
            self._store[key] = CacheEntry(
                expires_at_monotonic=time.monotonic() + self._ttl,
                payload=payload,
                etag=etag,
            )

    async def invalidate(self, key: str) -> bool:
        """Remove entrada especifica, se existir.

        Returns:
            True se a chave foi removida; False se nao existia.
        """
        async with self._lock:
            return self._store.pop(key, None) is not None

    async def clear(self) -> None:
        """Limpa todo o cache. Util em testes e em emergencias."""
        async with self._lock:
            self._store.clear()

    async def purge_expired(self) -> int:
        """Remove todas as entradas expiradas (best-effort).

        Em uso normal, `get()` ja faz limpeza lazy. Esta funcao e util em
        cenarios de longo idle (sem requests entrando, entradas acumulam
        ate o TTL). Pode ser chamada periodicamente por um job de housekeeping.

        Returns:
            Numero de entradas removidas.
        """
        async with self._lock:
            now = time.monotonic()
            expired_keys = [
                k for k, v in self._store.items() if v.expires_at_monotonic <= now
            ]
            for k in expired_keys:
                del self._store[k]
            return len(expired_keys)


# ─── Singleton do processo ────────────────────────────────────────────────


_default_cache: ReportCache | None = None
_default_lock = asyncio.Lock()


async def get_default_cache_async() -> ReportCache:
    """Retorna a instancia default (singleton lazy + thread-safe)."""
    global _default_cache
    if _default_cache is not None:
        return _default_cache
    async with _default_lock:
        if _default_cache is None:
            _default_cache = ReportCache()
        return _default_cache


def get_default_cache() -> ReportCache:
    """Retorna a instancia default sem `await` (uso em DI sincrona).

    Em primeira chamada, instancia preguicosamente. Apos isso, retorna
    sempre a mesma instancia. Nao e thread-safe na construcao inicial,
    mas FastAPI roda em event loop unico — ok na pratica.
    """
    global _default_cache
    if _default_cache is None:
        _default_cache = ReportCache()
    return _default_cache


def reset_default_cache(*, new_ttl: int | None = None) -> ReportCache:
    """Reseta o singleton default. **Uso restrito a testes.**

    Args:
        new_ttl: TTL custom da nova instancia. Se None, usa default/env.

    Returns:
        Nova instancia do ReportCache.
    """
    global _default_cache
    _default_cache = ReportCache(ttl_seconds=new_ttl)
    return _default_cache


__all__ = [
    "CacheEntry",
    "ReportCache",
    "DEFAULT_TTL_SECONDS",
    "get_default_cache",
    "get_default_cache_async",
    "reset_default_cache",
]
