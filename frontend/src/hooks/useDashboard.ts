"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import type { DashboardResponse } from "@/lib/types/prova";

interface State {
  loading: boolean;
  error: string | null;
  data: DashboardResponse | null;
}

const INITIAL: State = { loading: true, error: null, data: null };

/**
 * Encapsula GET /api/v1/provas/dashboard (Wave 4, Componente 15).
 *
 * Expoe `refresh()` para que o caller (Realtime ou polling) possa
 * re-buscar os contadores sob demanda.
 *
 * Protecao contra race: `latestReqRef` garante que apenas o resultado
 * do refresh() mais recente atualiza o estado.
 */
export function useDashboard(getToken: () => Promise<string | null>) {
  const [state, setState] = useState<State>(INITIAL);
  const latestReqRef = useRef<number>(0);
  const mountedRef = useRef(true);

  const refresh = useCallback(async (): Promise<void> => {
    const reqId = ++latestReqRef.current;
    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const token = await getToken();
      if (!token) {
        if (mountedRef.current && reqId === latestReqRef.current) {
          setState({ loading: false, error: "Sessao expirada", data: null });
        }
        return;
      }

      const data = await apiFetch<DashboardResponse>(
        "/api/v1/provas/dashboard",
        { token },
      );

      if (mountedRef.current && reqId === latestReqRef.current) {
        setState({ loading: false, error: null, data });
      }
    } catch (err) {
      if (mountedRef.current && reqId === latestReqRef.current) {
        const msg =
          err instanceof ApiError
            ? err.message
            : "Erro ao carregar dashboard";
        setState({ loading: false, error: msg, data: null });
      }
    }
  }, [getToken]);

  useEffect(() => {
    mountedRef.current = true;
    refresh();
    return () => {
      mountedRef.current = false;
    };
  }, [refresh]);

  return { ...state, refresh };
}
