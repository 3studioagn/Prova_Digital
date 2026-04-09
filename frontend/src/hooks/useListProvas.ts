"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import type { ProvaListResponse, Rota, StatusProva } from "@/lib/types/prova";

export interface ListProvasFilters {
  page: number;
  page_size: number;
  status?: StatusProva | null;
  periodo_inicio?: string | null; // YYYY-MM-DD
  periodo_fim?: string | null;
  vendedor_id?: string | null;
  cliente?: string | null;
  rota?: Rota | null;
  busca?: string | null;
}

interface State {
  loading: boolean;
  error: string | null;
  data: ProvaListResponse | null;
}

const INITIAL: State = { loading: true, error: null, data: null };

/**
 * Encapsula GET /api/v1/provas/ com debounce para campos textuais.
 *
 * O estado local do hook nao lida com a URL — a pagina `/provas` usa
 * `useSearchParams` para sincronizar a URL (ADR-Q07.3) e passa os
 * filtros atuais para `load()` a cada mudanca. Campos textuais (busca,
 * cliente) passam pelo debounce interno de 300ms antes de disparar
 * load — selects/dates disparam imediato.
 */
export function useListProvas(getToken: () => Promise<string | null>) {
  const [state, setState] = useState<State>(INITIAL);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latestReqRef = useRef<number>(0);

  const load = useCallback(
    async (filters: ListProvasFilters): Promise<void> => {
      const reqId = ++latestReqRef.current;
      setState((s) => ({ ...s, loading: true, error: null }));

      let token: string | null;
      try {
        token = await getToken();
      } catch {
        token = null;
      }
      if (!token) {
        setState({
          loading: false,
          error: "Sessao expirada. Faca login novamente.",
          data: null,
        });
        return;
      }

      const qs = new URLSearchParams();
      qs.set("page", String(filters.page));
      qs.set("page_size", String(filters.page_size));
      if (filters.status) qs.set("status", filters.status);
      if (filters.periodo_inicio)
        qs.set("periodo_inicio", filters.periodo_inicio);
      if (filters.periodo_fim) qs.set("periodo_fim", filters.periodo_fim);
      if (filters.vendedor_id) qs.set("vendedor_id", filters.vendedor_id);
      if (filters.cliente) qs.set("cliente", filters.cliente);
      if (filters.rota) qs.set("rota", filters.rota);
      if (filters.busca) qs.set("busca", filters.busca);

      try {
        const data = await apiFetch<ProvaListResponse>(
          `/api/v1/provas/?${qs.toString()}`,
          { token },
        );
        // Se outro load() mais recente comecou antes desse retornar, descarta.
        if (reqId !== latestReqRef.current) return;
        setState({ loading: false, error: null, data });
      } catch (err) {
        if (reqId !== latestReqRef.current) return;
        const msg =
          err instanceof ApiError
            ? err.message
            : "Nao foi possivel carregar provas.";
        setState({ loading: false, error: msg, data: null });
      }
    },
    [getToken],
  );

  /**
   * Variante com debounce de 300ms — usar em campos textuais (busca, cliente).
   * Uma chamada cancela o timer anterior, entao digitos rapidos disparam
   * apenas 1 request no final.
   */
  const loadDebounced = useCallback(
    (filters: ListProvasFilters) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        load(filters);
      }, 300);
    },
    [load],
  );

  // Cleanup do timer quando o componente desmonta.
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  return { ...state, load, loadDebounced };
}
