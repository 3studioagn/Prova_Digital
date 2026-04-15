"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import type {
  AuditLogItem,
  AuditoriaFilters,
  AuditoriaListResponse,
  FiltrosAplicados,
} from "@/lib/types/auditoria";

/**
 * Hook de listagem paginada do audit log (Wave 6, Componente 18).
 *
 * Encapsula `GET /api/v1/auditoria/` com filtros, keyset pagination via
 * cursor opaco, e gerenciamento de estado (loading/error/items) com
 * race protection + AbortController + timeout (padrao ADR-098, L-05
 * auditoria Wave 5 ronda 2).
 *
 * Caracteristicas:
 *
 *  - **Refresh automatico quando filtros mudam:** monitora `filtersKey`
 *    (derivada de todos os campos) e re-disparar `refresh()` no `useEffect`.
 *    Caller nao precisa memoizar o objeto `filters` — identidade instavel
 *    nao dispara re-fetch, apenas mudanca de VALOR.
 *
 *  - **Load more acumulativo:** `loadMore()` busca a proxima pagina via
 *    `next_cursor` e CONCATENA ao `items` existente (estado unico para a
 *    lista acumulada). `refresh()` zera a lista e recomeca do topo.
 *
 *  - **Race protection:** `latestReqRef` descarta respostas stale (ex:
 *    user troca filtros no meio do fetch). `abortRef` cancela o fetch
 *    em voo. `mountedRef` previne setState apos unmount.
 *
 *  - **Timeout 30 s:** requests que nao respondem em 30 s sao abortados.
 *    Mesmo racional do `useRelatorios` (Wave 5) — cobre cold-start do
 *    backend com margem generosa.
 *
 *  - **AbortError silencioso:** cancelamentos legitimos (navegacao,
 *    timeout, filtro novo) nao aparecem como "Erro ao carregar".
 *
 * @param getToken  Factory assincrona que resolve o token Supabase atual
 *                  (ou null se a sessao expirou).
 * @param filters   Filtros de entrada (camelCase). Valores sao traduzidos
 *                  para snake_case na query string.
 */
export function useAuditoria(
  getToken: () => Promise<string | null>,
  filters: AuditoriaFilters,
): AuditoriaHookResult {
  const [state, setState] = useState<State>(INITIAL);

  const mountedRef = useRef(true);
  const abortRef = useRef<AbortController | null>(null);
  const latestReqRef = useRef(0);
  const stateRef = useRef(state);
  const filtersRef = useRef(filters);

  // Keep refs in sync every render so `loadMore` / `doFetch` sempre
  // leem valores atuais (evita closures stale).
  stateRef.current = state;
  filtersRef.current = filters;

  // Chave estavel derivada dos filtros — usada como dep do useEffect.
  // JSON.stringify resolve o problema de identidade instavel de arrays
  // (ex: `acao: ["criar_prova"]` e um novo array a cada render, mas a
  // stringificacao e determinista).
  const filtersKey = JSON.stringify({
    d: filters.dataInicio ?? null,
    f: filters.dataFim ?? null,
    u: filters.usuarioId ?? null,
    n: filters.nroRequerimento ?? null,
    a: filters.acao ?? null,
    t: filters.tipoEvento ?? null,
    l: filters.limit ?? null,
  });

  const doFetch = useCallback(
    async (cursor: string | null, isLoadMore: boolean): Promise<void> => {
      // Cancelar request anterior em voo (ADR-098 L-05).
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      const timeoutId = setTimeout(
        () => controller.abort(),
        REQUEST_TIMEOUT_MS,
      );

      const reqId = ++latestReqRef.current;
      setState((prev) => ({
        ...prev,
        loading: isLoadMore ? prev.loading : true,
        loadingMore: isLoadMore,
        error: null,
      }));

      try {
        const token = await getToken();
        if (!token) {
          if (mountedRef.current && reqId === latestReqRef.current) {
            setState((prev) => ({
              ...prev,
              loading: false,
              loadingMore: false,
              error: "Sessao expirada",
            }));
          }
          return;
        }

        const qs = buildQueryString(filtersRef.current, cursor);
        const path = `/api/v1/auditoria/${qs ? `?${qs}` : ""}`;

        const resp = await apiFetch<AuditoriaListResponse>(path, {
          token,
          signal: controller.signal,
        });

        if (mountedRef.current && reqId === latestReqRef.current) {
          setState((prev) => ({
            loading: false,
            loadingMore: false,
            error: null,
            items: isLoadMore ? [...prev.items, ...resp.items] : resp.items,
            nextCursor: resp.next_cursor,
            hasMore: resp.has_more,
            totalEstimado: resp.total_estimado,
            filtrosAplicados: resp.filtros_aplicados,
          }));
        }
      } catch (err) {
        // AbortError e esperado quando:
        //   1. Novo refresh cancela o anterior.
        //   2. Timeout de 30 s dispara.
        //   3. Componente desmonta.
        // Nao queremos "Erro ao carregar" para esses casos.
        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }
        if (mountedRef.current && reqId === latestReqRef.current) {
          const msg =
            err instanceof ApiError
              ? err.message
              : "Erro ao carregar log de auditoria";
          setState((prev) => ({
            ...prev,
            loading: false,
            loadingMore: false,
            error: msg,
          }));
        }
      } finally {
        clearTimeout(timeoutId);
      }
    },
    [getToken],
  );

  const refresh = useCallback(async (): Promise<void> => {
    await doFetch(null, false);
  }, [doFetch]);

  const loadMore = useCallback(async (): Promise<void> => {
    const s = stateRef.current;
    // No-op quando nao ha mais paginas ou ja tem um fetch em voo.
    if (!s.nextCursor || !s.hasMore || s.loading || s.loadingMore) {
      return;
    }
    await doFetch(s.nextCursor, true);
  }, [doFetch]);

  // Re-disparar refresh sempre que os filtros mudarem (valor, nao identidade).
  // Propositalmente NAO incluimos `refresh` como dep porque ele ja depende
  // de `getToken` + `filtersKey` transitivamente via `doFetch` + ref.
  useEffect(() => {
    mountedRef.current = true;
    refresh();
    return () => {
      mountedRef.current = false;
      abortRef.current?.abort();
    };
    // filtersKey intentionally in deps — dispara re-fetch quando
    // valores (nao identidade) dos filtros mudam.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtersKey, refresh]);

  return {
    ...state,
    refresh,
    loadMore,
  };
}

// =============================================================================
// Internals
// =============================================================================

// L-05 (auditoria Wave 5 ronda 2): timeout de 30 s em rede lenta para nao
// deixar o usuario pendurado. Audit log e admin-only, acessado
// esporadicamente — 30 s cobre cold-start do backend com margem generosa.
const REQUEST_TIMEOUT_MS = 30_000;

interface State {
  loading: boolean;
  /** True durante `loadMore()` — separado de `loading` para a UI mostrar
   * spinner diferente no botao "Carregar mais" vs. skeleton inicial. */
  loadingMore: boolean;
  error: string | null;
  items: AuditLogItem[];
  nextCursor: string | null;
  hasMore: boolean;
  totalEstimado: number;
  filtrosAplicados: FiltrosAplicados | null;
}

const INITIAL: State = {
  loading: true,
  loadingMore: false,
  error: null,
  items: [],
  nextCursor: null,
  hasMore: false,
  totalEstimado: 0,
  filtrosAplicados: null,
};

export interface AuditoriaHookResult extends State {
  /** Zera a lista e busca a primeira pagina novamente. */
  refresh: () => Promise<void>;
  /** Busca a proxima pagina (via `next_cursor`) e concatena ao `items`.
   * No-op se `hasMore=false` ou ja ha um fetch em voo. */
  loadMore: () => Promise<void>;
}

/** Constroi a query string a partir dos filtros + cursor.
 *
 * Exportada para permitir testes unitarios isolados (Wave 6 Bloco 6.5
 * preview) sem precisar montar o hook inteiro.
 */
export function buildQueryString(
  filters: AuditoriaFilters,
  cursor: string | null,
): string {
  const params = new URLSearchParams();

  if (filters.dataInicio) params.set("data_inicio", filters.dataInicio);
  if (filters.dataFim) params.set("data_fim", filters.dataFim);
  if (filters.usuarioId) params.set("usuario_id", filters.usuarioId);
  if (filters.nroRequerimento) {
    params.set("nro_requerimento", filters.nroRequerimento);
  }

  if (filters.acao && filters.acao.length > 0) {
    for (const a of filters.acao) params.append("acao", a);
  }
  if (filters.tipoEvento && filters.tipoEvento.length > 0) {
    for (const t of filters.tipoEvento) params.append("tipo_evento", t);
  }

  if (typeof filters.limit === "number") {
    params.set("limit", String(filters.limit));
  }
  if (cursor) {
    params.set("cursor", cursor);
  }

  return params.toString();
}
