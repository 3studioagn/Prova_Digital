"""Funcoes puras de agregacao para Relatorios (Wave 5, Componente 16).

Todas as funcoes deste modulo sao **deterministicas e sem efeito colateral**
— nao tocam DB, nao leem env vars, nao logam. Recebem dados ja extraidos
e devolvem numeros / listas. Isso permite testes unitarios sem fixtures
de banco e isolamento total da logica.

A SQL que extrai os dados vive em app/api/v1/reports.py (Bloco 5.2). O
contrato deste modulo e: dado X, calcule Y. Nada mais.

Convencoes:
  - Tempos sempre em **horas corridas** (ADR-091, ADR-099 — Wave 5 alinhada
    a Wave 4). Funcoes que recebem deltas em segundos retornam horas float.
  - Taxas sempre 0.0-1.0 (frontend converte para % se necessario).
  - Denominador zero => 0.0 ou None (documentado por funcao).
  - Listas vazias => 0 ou None (documentado por funcao).
"""
from __future__ import annotations

import statistics
from datetime import datetime, timedelta
from typing import Iterable

# ─── Constantes ───────────────────────────────────────────────────────────


SECONDS_PER_HOUR = 3600.0


# ─── Conversao de intervalos ──────────────────────────────────────────────


def horas_corridas(start: datetime, end: datetime) -> float:
    """Diferenca em horas (decimal) entre dois timestamps.

    Assume `end >= start`. Se `end < start`, retorna valor negativo —
    caller e responsavel por validar a ordem se necessario.

    Args:
        start: timestamp inicial (tz-aware preferencialmente).
        end: timestamp final.

    Returns:
        Float = (end - start).total_seconds() / 3600.
    """
    return (end - start).total_seconds() / SECONDS_PER_HOUR


# ─── Estatisticas sobre listas de intervalos ──────────────────────────────


def media_horas(intervalos_segundos: Iterable[float]) -> float | None:
    """Media de uma lista de intervalos em segundos, retornado em horas.

    Args:
        intervalos_segundos: iteravel de floats (cada um = `(end - start).total_seconds()`).

    Returns:
        Media em horas (float). `None` se a lista for vazia.
    """
    valores = list(intervalos_segundos)
    if not valores:
        return None
    return statistics.fmean(valores) / SECONDS_PER_HOUR


def mediana_horas(intervalos_segundos: Iterable[float]) -> float | None:
    """Mediana de uma lista de intervalos em segundos, retornado em horas.

    Args:
        intervalos_segundos: iteravel de floats.

    Returns:
        Mediana em horas (float). `None` se a lista for vazia.
    """
    valores = list(intervalos_segundos)
    if not valores:
        return None
    return statistics.median(valores) / SECONDS_PER_HOUR


# ─── Taxas (proporcoes) ───────────────────────────────────────────────────


def taxa(numerador: int, denominador: int) -> float:
    """Calcula uma taxa proporcional (numerador / denominador) em [0.0, 1.0].

    Por convencao de domain (ADR-101 — taxas sobre ciclos), o caller deve
    passar `numerador <= denominador`. Esta funcao apenas garante:
      - Denominador <= 0 => 0.0 (evita ZeroDivisionError e -1/0 issues).
      - Negativo nao acontece se input respeitar convencao; clampamos para
        [0.0, 1.0] como safety net.

    Args:
        numerador: contagem do evento (ex: reprovacoes).
        denominador: total de eventos (ex: ciclos decididos).

    Returns:
        Float em [0.0, 1.0].
    """
    if denominador <= 0:
        return 0.0
    raw = numerador / denominador
    # Clamp defensivo. Em condicoes normais, o caller respeita a convencao.
    if raw < 0.0:
        return 0.0
    if raw > 1.0:
        return 1.0
    return raw


def media_diaria(quantidade: int, total_dias: int) -> float:
    """Media diaria de uma contagem ao longo de um periodo.

    Usado para `Indicadores3Studio.media_diaria_criacao`.

    Args:
        quantidade: total no periodo (ex: provas criadas).
        total_dias: numero de dias do periodo. Min 1.

    Returns:
        Float arredondado a 2 casas (estetica de UI). 0.0 se `total_dias <= 0`.
    """
    if total_dias <= 0:
        return 0.0
    return round(quantidade / total_dias, 2)


# ─── Limite de "atrasada" (RN-008 com horas corridas — ADR-099) ───────────


def limite_atraso(now_utc: datetime, tempo_atraso_horas: int) -> datetime:
    """Datetime UTC de corte para classificar uma prova como 'Atrasada'.

    Provas cuja `coalesce(max(mov.created_at), prova.created_at)` for menor
    que este limite sao consideradas atrasadas (RN-008 com horas corridas
    — ADR-091 + ADR-099).

    Args:
        now_utc: momento de referencia (em UTC). Em producao = `datetime.now(UTC)`.
        tempo_atraso_horas: parametro `tempo_atraso_horas_uteis` da config
          (mantem nome legacy; calculo e em horas corridas).

    Returns:
        Datetime UTC = now_utc - tempo_atraso_horas.
    """
    if tempo_atraso_horas < 0:
        raise ValueError("tempo_atraso_horas nao pode ser negativo")
    return now_utc - timedelta(hours=tempo_atraso_horas)


# ─── Periodo: numero de dias da janela ────────────────────────────────────


def calcular_total_dias(from_dt: datetime, to_dt: datetime) -> int:
    """Numero de dias da janela [from_dt, to_dt) com round-up.

    Espelha `ReportFilters.total_dias` mas exposto como funcao pura para
    permitir uso fora do contexto Pydantic (ex: agregadores).

    Args:
        from_dt: limite inferior (inclusive).
        to_dt: limite superior (exclusive).

    Returns:
        Inteiro >= 1. 23h59 ainda conta como 1 dia.
    """
    if to_dt <= from_dt:
        return 1
    delta = to_dt - from_dt
    days = delta.total_seconds() / 86400.0
    return max(1, int(days) if days == int(days) else int(days) + 1)


# ─── Conveniencia: arredondamento de horas para UI ────────────────────────


def arredondar_horas(horas: float | None, casas: int = 2) -> float | None:
    """Arredonda valor de horas para `casas` casas decimais.

    Mantem `None` quando input e `None` (nao introduz 0.0 onde a semantica
    e 'nenhum dado').

    Args:
        horas: valor em horas (pode ser None).
        casas: casas decimais. Default 2.

    Returns:
        Float arredondado, ou None.
    """
    if horas is None:
        return None
    return round(horas, casas)


# ─── Validacao de timestamp UTC ───────────────────────────────────────────


def assert_utc(dt: datetime, *, name: str = "datetime") -> None:
    """Garante que um datetime e tz-aware UTC.

    Falha em vez de coercer silenciosamente para evitar bugs sutis de timezone
    (lecao da Wave 2 — F25 da auditoria externa).

    Args:
        dt: datetime a validar.
        name: nome para mensagem de erro (debug-friendly).

    Raises:
        ValueError: se `dt` for naive ou tz != UTC.
    """
    if dt.tzinfo is None:
        raise ValueError(f"{name} deve ser tz-aware (UTC)")
    if dt.utcoffset() != timedelta(0):
        raise ValueError(f"{name} deve estar em UTC, recebido {dt.tzinfo}")


__all__ = [
    "SECONDS_PER_HOUR",
    "horas_corridas",
    "media_horas",
    "mediana_horas",
    "taxa",
    "media_diaria",
    "limite_atraso",
    "calcular_total_dias",
    "arredondar_horas",
    "assert_utc",
]
