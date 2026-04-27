"""Geracao deterministica de ETag para Relatorios (Wave 5, Componente 16).

Camada 1 da estrategia 'minimizar queries' do WAVE5_ANALYSIS §4.4:

  Cliente envia `If-None-Match: <etag>` em refetch.
  Backend compara com o ETag do cache hit.
  Match => `304 Not Modified` com body vazio.
  Resultado: zero serializacao + zero bytes ao cliente alem dos headers.

Por que SHA-256 do JSON canonico (e nao `weak` ETag baseado em timestamp):
  - **Determinismo**: dois workers/replicas calculam o mesmo ETag para o
    mesmo payload. Importante quando o cache nao e compartilhado.
  - **Sensibilidade**: qualquer mudanca em qualquer campo => ETag diferente.
  - **Sem coordenacao**: nao precisa banco/redis para gerar.

ETags retornados sao **strong ETags** (sem prefixo `W/`). RFC 7232 §2.3.

Para validacao em comparacao com `If-None-Match`, sempre usar comparacao
de string exata (incluindo as aspas duplas).
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel

# ─── Helpers internos ─────────────────────────────────────────────────────


def _canonical_json(payload: BaseModel | dict[str, Any]) -> str:
    """Serializa um payload em JSON canonico estavel.

    Estavel = mesma entrada produz mesma string em qualquer execucao,
    independente de versao do Python ou ordem de definicao dos campos.

    Implementacao:
      - `model_dump(mode="json")` se Pydantic: converte UUID/datetime/Enum
        para tipos JSON-nativos.
      - `json.dumps(sort_keys=True, separators=(",", ":"))`: ordem
        lexicografica + sem espacos => bit-estavel.
    """
    if isinstance(payload, BaseModel):
        raw: dict[str, Any] = payload.model_dump(
            mode="json", by_alias=False, exclude_none=False
        )
    elif isinstance(payload, dict):
        raw = payload
    else:
        raise TypeError(
            f"compute_etag aceita BaseModel ou dict, recebeu {type(payload).__name__}"
        )
    return json.dumps(raw, sort_keys=True, separators=(",", ":"))


# ─── API publica ──────────────────────────────────────────────────────────


def compute_etag(payload: BaseModel | dict[str, Any]) -> str:
    """Calcula o ETag (strong) de um payload Pydantic ou dict.

    Args:
        payload: modelo Pydantic ou dict JSON-serializavel.

    Returns:
        String no formato `'"<sha256-hex>"'` (com aspas duplas
        envolvendo o digest, conforme RFC 7232).

    Notes:
        - Output e deterministico: mesmo payload => mesmo ETag em qualquer
          worker/replica.
        - Comparacao com `If-None-Match` deve ser por string exata.
    """
    canonical = _canonical_json(payload)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f'"{digest}"'


def matches_if_none_match(if_none_match_header: str | None, etag: str) -> bool:
    """Verifica se um header `If-None-Match` corresponde ao ETag fornecido.

    Suporta:
      - `If-None-Match: "abc"` => match se `etag == '"abc"'`.
      - `If-None-Match: *` => match qualquer recurso existente (RFC 7232 §3.2).
      - `If-None-Match: "a", "b", "c"` => match se etag estiver na lista.

    NAO suporta (intencional, fora de escopo da Wave 5):
      - Weak ETags (`W/"..."`).
      - Comentarios ou whitespace nao-padrao.

    Args:
        if_none_match_header: valor cru do header HTTP (None se ausente).
        etag: ETag do recurso (resultado de `compute_etag`).

    Returns:
        True se houver match (cliente ja tem o conteudo). False caso contrario.
    """
    if if_none_match_header is None:
        return False

    header = if_none_match_header.strip()
    if not header:
        return False

    # Wildcard match (RFC 7232 §3.2)
    if header == "*":
        return True

    # Suporte a lista comma-separated. Cada token e um ETag entre aspas.
    candidates = [token.strip() for token in header.split(",")]
    return etag in candidates


__all__ = [
    "compute_etag",
    "matches_if_none_match",
]
