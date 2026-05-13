"use client";

/**
 * Hook que sincroniza ReportFilters com a URL (Wave 5, Componente 16).
 *
 * Filtros vivem em `useSearchParams` para deep-link/bookmark/back-button.
 * O hook expoe `filters` (derivado da URL) + `setFilter(key, value)` que
 * faz `router.replace(...)` mantendo o histórico limpo.
 *
 * Convertores: campos `from`/`to` sao tratados como strings ISO-8601 para
 * passar direto ao backend; o componente DateRangeFilter cuida da conversao
 * BRT/UI -> UTC/ISO.
 */
import { useCallback, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import type {
  ReportFilters,
  ReportScope,
  RotaCategoria,
} from "@/lib/types/report";
import { REPORT_SCOPES } from "@/lib/types/report";
import {
  ROTA_OPTIONS,
  STATUS_OPTIONS,
  type Rota,
  type StatusProva,
} from "@/lib/types/prova";

const SCOPE_SET = new Set(REPORT_SCOPES);

function parseScope(value: string | null): ReportScope {
  if (value && (SCOPE_SET as Set<string>).has(value)) {
    return value as ReportScope;
  }
  return "geral";
}

/** Wave 5 v4.0: aceita os 6 valores de `Rota` (4 v4.0 + 2 legacy).
 *
 * Fonte: `ROTA_OPTIONS` em `@/lib/types/prova` — TypeScript barra a build
 * se algum valor de `Rota` for esquecido aqui. URL com valor invalido
 * retorna `null` (filtro desativado, sem erro). */
function parseRota(value: string | null): Rota | null {
  if (value && (ROTA_OPTIONS as ReadonlyArray<string>).includes(value)) {
    return value as Rota;
  }
  return null;
}

/** Wave 5 v4.0: aceita `matriz` ou `filial` como categoria consolidada. */
function parseRotaCategoria(value: string | null): RotaCategoria | null {
  if (value === "matriz" || value === "filial") return value;
  return null;
}

/** Wave 5 v4.0: aceita os 17 valores de `StatusProva` (10 v3.0 + 7 v4.0).
 *
 * Fonte: `STATUS_OPTIONS` em `@/lib/types/prova`. Antes da Wave 5 v4.0,
 * o array era hard-codeado com os 10 valores v3.0 — filtros v4.0 na
 * URL (`?status=COM_MOTORISTA_IDA_LAMINACAO`) zeravam silenciosamente. */
function parseStatus(value: string | null): StatusProva | null {
  if (value && (STATUS_OPTIONS as ReadonlyArray<string>).includes(value)) {
    return value as StatusProva;
  }
  return null;
}

/** Retorna `null` para vazio/null/undefined; trim em strings. */
function nullableString(value: string | null): string | null {
  if (value === null) return null;
  const t = value.trim();
  return t === "" ? null : t;
}

/**
 * Le os filtros atuais da URL e expoe setters que atualizam a URL.
 *
 * O retorno e estavel entre re-renders quando a URL nao muda
 * (graças ao useMemo + useSearchParams).
 */
export function useReportFilters() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const filters: ReportFilters = useMemo(
    () => ({
      scope: parseScope(searchParams.get("scope")),
      from: nullableString(searchParams.get("from")),
      to: nullableString(searchParams.get("to")),
      q: nullableString(searchParams.get("q")),
      vendedor_id: nullableString(searchParams.get("vendedor_id")),
      rota: parseRota(searchParams.get("rota")),
      rota_categoria: parseRotaCategoria(searchParams.get("rota_categoria")),
      status: parseStatus(searchParams.get("status")),
    }),
    [searchParams],
  );

  /**
   * Atualiza um campo dos filtros e reescreve a URL.
   *
   * Passar `null` ou string vazia remove o parametro da URL.
   * Mudar `scope` preserva os outros filtros (decisao UX: trocar de
   * perspectiva nao deve resetar o periodo).
   *
   * IMPORTANTE: chamadas SEQUENCIAS de `setFilter` no mesmo render
   * (ex: `setFilter("from", x); setFilter("to", y);`) sobrescrevem-se
   * mutuamente porque cada uma le o `searchParams` do closure (que so
   * atualiza no proximo render). Para atualizar multiplos campos
   * atomicamente, use `setFilters` (plural) abaixo.
   */
  const setFilter = useCallback(
    <K extends keyof ReportFilters>(
      key: K,
      value: ReportFilters[K] | null,
    ) => {
      const params = new URLSearchParams(searchParams.toString());
      const stringValue =
        value === null || value === undefined || value === ""
          ? null
          : String(value);
      if (stringValue === null) {
        params.delete(key);
      } else {
        params.set(key, stringValue);
      }
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  /**
   * Atualiza MULTIPLOS campos dos filtros em uma unica reescrita de URL.
   *
   * Use quando precisar atualizar 2+ filtros juntos (ex: from+to do
   * DateRangeFilter, presets de periodo). Chamar `setFilter` em sequencia
   * causa race onde a 2a chamada sobrescreve a 1a (audit 2026-04-29).
   *
   * Passar `null`/`undefined`/string vazia em qualquer campo remove o
   * parametro da URL. Campos ausentes do objeto sao mantidos.
   */
  const setFilters = useCallback(
    (updates: Partial<Record<keyof ReportFilters, ReportFilters[keyof ReportFilters] | null>>) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(updates) as Array<
        [keyof ReportFilters, ReportFilters[keyof ReportFilters] | null]
      >) {
        const stringValue =
          value === null || value === undefined || value === ""
            ? null
            : String(value);
        if (stringValue === null) {
          params.delete(key);
        } else {
          params.set(key, stringValue);
        }
      }
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  /** Reset completo — preserva apenas o scope. */
  const resetFilters = useCallback(() => {
    const params = new URLSearchParams();
    params.set("scope", filters.scope);
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  }, [filters.scope, pathname, router]);

  /**
   * Stringifica os filtros como query params para chamada da API.
   * Omite campos null/undefined.
   *
   * Wave 5 v4.0: emite `rota_categoria` quando setado (precedencia sobre
   * `rota` exata no backend — ver `_aplicar_filtros_provas`).
   */
  const toQueryString = useCallback((): string => {
    const params = new URLSearchParams();
    params.set("scope", filters.scope);
    if (filters.from) params.set("from", filters.from);
    if (filters.to) params.set("to", filters.to);
    if (filters.q) params.set("q", filters.q);
    if (filters.vendedor_id) params.set("vendedor_id", filters.vendedor_id);
    if (filters.rota) params.set("rota", filters.rota);
    if (filters.rota_categoria) {
      params.set("rota_categoria", filters.rota_categoria);
    }
    if (filters.status) params.set("status", filters.status);
    return params.toString();
  }, [filters]);

  return { filters, setFilter, setFilters, resetFilters, toQueryString };
}
