"use client";

/**
 * Hook unico para GET /api/v1/reports (Wave 5, Componente 16).
 *
 * Estrategia 'minimizar queries' (WAVE5_ANALYSIS §4.4 / §5.3):
 *   - Cache local em useRef<Map<filtersKey, {etag, data}>>.
 *   - Cada fetch envia `If-None-Match: <etag-local>` se houver cache.
 *   - 304 Not Modified => mantem dados existentes (zero bytes ao cliente).
 *   - 200 OK => atualiza cache + ETag.
 *   - Race protection via reqId monotonico.
 *   - AbortController cancela request anterior em refetch.
 *   - `invalidate()` limpa cache e dispara refetch (chamado pelo Realtime).
 *
 * Diferente de outros hooks do projeto (useDashboard, useListProvas), este
 * NAO usa apiFetch — precisa ler `ETag` do response e enviar `If-None-Match`,
 * coisa que apiFetch nao expoe. Usamos fetch nativo aqui.
 */
import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "@/lib/api";
import type { ReportFilters, ReportResponse } from "@/lib/types/report";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface CacheEntry {
  etag: string;
  data: ReportResponse;
}

interface State {
  loading: boolean;
  /** True quando ha fetch em voo mas ja temos `data` exibido (refresh). */
  refreshing: boolean;
  error: string | null;
  data: ReportResponse | null;
}

const INITIAL: State = {
  loading: true,
  refreshing: false,
  error: null,
  data: null,
};

/**
 * Constroi a chave de cache local a partir dos filtros.
 *
 * NAO precisa ser bit-exato com o backend (que usa SHA-256 em SQL):
 * o cliente apenas reusa por equivalencia logica. Mesmo objeto =>
 * mesma chave => evita refetch redundante.
 */
function buildCacheKey(filters: ReportFilters, queryString: string): string {
  // queryString ja vem normalizado de useReportFilters.toQueryString
  return `${filters.scope}|${queryString}`;
}

export interface UseReportResult extends State {
  /** Re-fetch forcado (ignora cache local — usado pelo botao retry e Realtime). */
  refresh: () => Promise<void>;
  /** Limpa cache local e dispara refetch (Realtime invalida). */
  invalidate: () => Promise<void>;
}

/**
 * Hook unico para Relatorios.
 *
 * @param filters Filtros tipados (vindos de useReportFilters.filters).
 * @param queryString Pre-stringificado por useReportFilters.toQueryString.
 * @param getToken Async callback que devolve o JWT (ou null).
 * @returns Estado + helpers.
 */
export function useReport(
  filters: ReportFilters,
  queryString: string,
  getToken: () => Promise<string | null>,
): UseReportResult {
  const [state, setState] = useState<State>(INITIAL);

  // Cache local — sobrevive a re-renders mas nao a navegacao entre paginas.
  const cacheRef = useRef<Map<string, CacheEntry>>(new Map());
  const latestReqRef = useRef<number>(0);
  const inflightControllerRef = useRef<AbortController | null>(null);
  const mountedRef = useRef(true);

  /**
   * Fetcher central. `force=true` ignora cache local mas ainda envia ETag
   * para permitir 304 (revalidacao). `bypassBackendCache=true` adiciona
   * `?_force=1` na URL para forcar o backend a recomputar (uso: invalidacao
   * via Realtime quando ha dado novo no banco que o cache backend ainda
   * nao refletiu — TTL 60s vs frescor desejado).
   */
  const fetchReport = useCallback(
    async (
      force: boolean,
      bypassBackendCache: boolean = false,
    ): Promise<void> => {
      const cacheKey = buildCacheKey(filters, queryString);
      const cached = cacheRef.current.get(cacheKey);

      // Cache hit nao-forcado => retornar imediatamente sem rede.
      if (!force && cached) {
        if (mountedRef.current) {
          setState({
            loading: false,
            refreshing: false,
            error: null,
            data: cached.data,
          });
        }
        return;
      }

      // Aborta request anterior — economiza banda em filtros mudando rapido.
      if (inflightControllerRef.current) {
        inflightControllerRef.current.abort();
      }
      const controller = new AbortController();
      inflightControllerRef.current = controller;
      const reqId = ++latestReqRef.current;

      // Refresh visual: se ja temos dados, vira `refreshing`; senao `loading`.
      setState((prev) => ({
        ...prev,
        loading: prev.data === null,
        refreshing: prev.data !== null,
        error: null,
      }));

      let token: string | null;
      try {
        token = await getToken();
      } catch {
        token = null;
      }
      if (reqId !== latestReqRef.current) return;
      if (!token) {
        if (mountedRef.current) {
          setState({
            loading: false,
            refreshing: false,
            error: "Sessao expirada. Faca login novamente.",
            data: null,
          });
        }
        return;
      }

      const headers: Record<string, string> = {
        Authorization: `Bearer ${token}`,
      };
      // ETag para revalidacao 304. Em bypass do backend cache, pular —
      // backend ignoraria o cache de qualquer forma e recomputaria sempre.
      if (cached && !bypassBackendCache) {
        headers["If-None-Match"] = cached.etag;
      }

      // Compoe URL com `?_force=1` quando pedimos refresh sem cache.
      const url = bypassBackendCache
        ? `${API_URL}/api/v1/reports?${queryString}&_force=1`
        : `${API_URL}/api/v1/reports?${queryString}`;

      try {
        const res = await fetch(url, {
          headers,
          signal: controller.signal,
        });

        if (reqId !== latestReqRef.current) return;

        // 304 Not Modified — mantem dados em cache, atualiza estado para success.
        if (res.status === 304) {
          if (cached && mountedRef.current) {
            setState({
              loading: false,
              refreshing: false,
              error: null,
              data: cached.data,
            });
          }
          return;
        }

        if (!res.ok) {
          let detail = `HTTP ${res.status}`;
          try {
            const body = await res.json();
            detail = body.detail || detail;
          } catch {
            // body nao-JSON
          }
          throw new ApiError(detail, res.status);
        }

        const newEtag = res.headers.get("etag") || "";
        const data = (await res.json()) as ReportResponse;

        if (newEtag) {
          cacheRef.current.set(cacheKey, { etag: newEtag, data });
        }

        if (mountedRef.current) {
          setState({
            loading: false,
            refreshing: false,
            error: null,
            data,
          });
        }
      } catch (err) {
        if (reqId !== latestReqRef.current) return;
        // Request abortada — outra ja assumiu, nao sobrescrever estado.
        if (err instanceof DOMException && err.name === "AbortError") return;
        if (!mountedRef.current) return;

        const msg =
          err instanceof ApiError
            ? err.message
            : "Erro ao carregar relatorio.";
        // Mantem `data` se ja tinha (retry tela cheia ou pequeno banner).
        setState((prev) => ({
          loading: false,
          refreshing: false,
          error: msg,
          data: prev.data,
        }));
      }
    },
    [filters, queryString, getToken],
  );

  /** Refresh sob demanda. Sem bypass do backend cache — polling regular
   * envia If-None-Match e tira proveito de 304. Botao "Tentar novamente"
   * tambem cai aqui (e geralmente quer-se cache hit se houver). */
  const refresh = useCallback(async () => {
    await fetchReport(true);
  }, [fetchReport]);

  /** Invalidacao via Realtime: limpa cache local + bypass cache backend.
   * Audit 2026-04-29: bypass garante que mudancas em provas (criadas/
   * transitadas/canceladas) reflitam imediatamente nos sparklines do
   * card TOTAL GERAL, VENDEDOR COM MAIS ARTES e PROVAS CRIADAS. Sem o
   * bypass, backend serviria o cache TTL 60s anterior com ETag stale. */
  const invalidate = useCallback(async () => {
    cacheRef.current.clear();
    await fetchReport(true, true);
  }, [fetchReport]);

  // Refetch a cada mudanca de filtros/queryString.
  useEffect(() => {
    fetchReport(false);
  }, [fetchReport]);

  // Cleanup no unmount: aborta request em voo.
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (inflightControllerRef.current) {
        inflightControllerRef.current.abort();
      }
    };
  }, []);

  return { ...state, refresh, invalidate };
}
