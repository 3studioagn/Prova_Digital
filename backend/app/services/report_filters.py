"""Filtros de Relatorios (Wave 5, Componente 16) + chave de cache deterministica.

Modelo Pydantic v2 que valida os query params de GET /api/v1/reports e gera
uma chave de cache estavel a partir de filtros equivalentes.

Estrategia para minimizar queries (WAVE5_ANALYSIS Secao 4.4):
  - Mesmos filtros => mesma chave => mesmo cache hit no `report_cache`.
  - Cache backend devolve o ETag pre-calculado => `If-None-Match` no cliente
    resulta em 304 sem reserializacao do payload.
  - Default de janela 30 dias evita "tudo desde o inicio" acidental.

Decisoes:
  - Datas validadas em UTC. Conversao BRT→UTC e responsabilidade do cliente
    (mesma estrategia da Wave 2 endpoint /provas).
  - Range maximo 366 dias para proteger plano de query.
  - `q` (busca textual) com max 200 chars para evitar payloads abusivos.
  - Modelo `frozen=True` => imutavel apos validacao. Combinado com aliases,
    permite deserialization permissiva e cache key canonico.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.db.models import RotaEnum, StatusProvaEnum

# ─── Tipos publicos ────────────────────────────────────────────────────────


ReportScope = Literal["geral", "3studio", "vendedores", "clicheria"]
"""Perspectivas suportadas em GET /api/v1/reports."""


RotaCategoria = Literal["matriz", "filial"]
"""Categoria consolidada de rota (Wave 5 v4.0 — Componente 16).

- `matriz`: filtra `rota IN {MATRIZ, LAM_MATRIZ, PADRAO}` UNION com
  `rota IS NULL AND vendedor.localizacao = MATRIZ` (heuristica do C12).
- `filial`: filtra `rota IN {FILIAL, LAM_FILIAL, DIRETA}` UNION com
  `rota IS NULL AND vendedor.localizacao = FILIAL`.

Coexiste com `rota` (filtro exato por valor v4.0+legacy). Se ambos
fornecidos, `rota_categoria` toma precedencia (matriz/filial e
mais abrangente que um valor especifico).
"""


# ─── Limites e defaults ────────────────────────────────────────────────────


DEFAULT_PERIOD_DAYS = 30
"""Janela padrao quando `from`/`to` ausentes — evita 'tudo desde o inicio'."""

MAX_PERIOD_DAYS = 366
"""Limite hard para proteger plano de query."""

MAX_Q_LENGTH = 200
"""Limite hard do parametro `q` (busca textual)."""


# ─── Modelo de filtros ─────────────────────────────────────────────────────


class ReportFilters(BaseModel):
    """Filtros de GET /api/v1/reports.

    `from_` e `to` sao validados como UTC. Ambos sao opcionais; quando
    ausentes, default e 'ultimos 30 dias' (DEFAULT_PERIOD_DAYS).

    Range maximo 366 dias (MAX_PERIOD_DAYS). Tamanho maximo de `q` =
    MAX_Q_LENGTH (200) chars.

    Modelo `frozen=True` para imutabilidade pos-validacao — protege contra
    mutacao acidental quando reutilizado entre cache hits.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
    )

    scope: ReportScope
    """Perspectiva tipada — discriminated union do response."""

    from_: datetime | None = Field(default=None, alias="from")
    """Limite inferior (inclusive) do periodo, em UTC. Default: to - 30d."""

    to: datetime | None = None
    """Limite superior (exclusive) do periodo, em UTC. Default: now()."""

    q: str | None = Field(default=None, max_length=MAX_Q_LENGTH)
    """Busca textual em nome/cliente/nro_requerimento (ILIKE). Opcional."""

    vendedor_id: UUID | None = None
    """Filtro por vendedor especifico. Opcional."""

    rota: RotaEnum | None = None
    """Filtro por rota exata. Opcional. Provas com `rota=NULL` sao
    excluidas se este filtro for especificado. Wave 5 v4.0: aceita
    todos os 6 valores de `RotaEnum` (4 v4.0 + 2 legacy)."""

    rota_categoria: RotaCategoria | None = None
    """[Wave 5 v4.0] Filtro consolidado por categoria (matriz/filial).
    Inclui provas v4.0 + legacy explicito + legacy NULL inferido via
    `vendedor.localizacao`. Toma precedencia sobre `rota` se ambos
    fornecidos."""

    status: StatusProvaEnum | None = None
    """Filtro por status especifico. Opcional. Wave 5 v4.0: aceita
    todos os 17 valores (10 v3.0 + 7 v4.0 da Wave 3 v4.0 / C11)."""

    @model_validator(mode="after")
    def _defaults_and_invariants(self) -> "ReportFilters":
        """Preenche defaults e valida invariantes do periodo.

        Roda apos parse de campos individuais. `frozen=True` exige
        `object.__setattr__` para mutar self (padrao Pydantic v2).
        """
        # Default: to = now (UTC)
        if self.to is None:
            object.__setattr__(self, "to", datetime.now(timezone.utc))

        # Default: from = to - DEFAULT_PERIOD_DAYS
        if self.from_ is None:
            object.__setattr__(
                self, "from_", self.to - timedelta(days=DEFAULT_PERIOD_DAYS)
            )

        # Garantir tz-aware (qualquer datetime sem tz e tratado como UTC)
        if self.from_.tzinfo is None:
            object.__setattr__(
                self, "from_", self.from_.replace(tzinfo=timezone.utc)
            )
        if self.to.tzinfo is None:
            object.__setattr__(
                self, "to", self.to.replace(tzinfo=timezone.utc)
            )

        # Invariante 1: from < to
        if self.from_ >= self.to:
            raise ValueError("'from' deve ser anterior a 'to'")

        # Invariante 2: range <= MAX_PERIOD_DAYS
        if (self.to - self.from_) > timedelta(days=MAX_PERIOD_DAYS):
            raise ValueError(
                f"Periodo nao pode exceder {MAX_PERIOD_DAYS} dias"
            )

        # Normalizar q: strip + remover string vazia
        if self.q is not None:
            stripped = self.q.strip()
            object.__setattr__(self, "q", stripped if stripped else None)

        return self

    @property
    def total_dias(self) -> int:
        """Numero de dias na janela (round up). Min 1."""
        delta = self.to - self.from_  # type: ignore[operator]
        # ceil para nao subestimar janelas curtas (ex: 23h59 == 1 dia)
        days = delta.total_seconds() / 86400.0
        return max(1, int(days) if days == int(days) else int(days) + 1)


# ─── Chave de cache canonica ───────────────────────────────────────────────


def to_cache_key(filters: ReportFilters) -> str:
    """Gera chave de cache deterministica para um conjunto de filtros.

    Filtros equivalentes (mesmas datas, mesmos opcionais) produzem chave
    bit-identica — base do compartilhamento de cache entre requests
    concorrentes (estrategia 'minimizar queries' do WAVE5_ANALYSIS §4.4).

    Implementacao:
      1. `model_dump(mode="json")` converte UUID → str e datetime → ISO.
      2. `json.dumps(..., sort_keys=True, separators=(",", ":"))` gera
         JSON canonico (ordem lexicografica de chaves, sem espacos).
      3. SHA-256 do utf-8 da string canonica → hex digest.

    Por que SHA-256 e nao hash():
      - `hash()` do Python e nao-deterministico entre processos (PYTHONHASHSEED).
      - Sha-256 sempre da o mesmo digest, em qualquer worker uvicorn.
      - 256 bits = colisao desprezivel para o universo de filtros possiveis.

    Returns:
        Hex string de 64 chars (SHA-256 digest).
    """
    payload = filters.model_dump(mode="json", by_alias=False, exclude_none=False)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ─── Helper de comparacao para tests ───────────────────────────────────────


def filters_equivalent(a: ReportFilters, b: ReportFilters) -> bool:
    """Dois ReportFilters sao equivalentes sse to_cache_key(a) == to_cache_key(b).

    Helper de uso primariamente em testes. Em producao, comparar diretamente
    as chaves (mais rapido).
    """
    return to_cache_key(a) == to_cache_key(b)


__all__ = [
    "ReportScope",
    "RotaCategoria",
    "ReportFilters",
    "to_cache_key",
    "filters_equivalent",
    "DEFAULT_PERIOD_DAYS",
    "MAX_PERIOD_DAYS",
    "MAX_Q_LENGTH",
]
