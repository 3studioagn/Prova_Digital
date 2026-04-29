"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import {
  type AuditLogDetailResponse,
  type AuditLogFilters,
  type AuditLogListResponse,
  filtersToQueryString,
} from "@/lib/types/auditLog";

interface ListState {
  loading: boolean;
  error: string | null;
  data: AuditLogListResponse | null;
}

const INITIAL_LIST: ListState = { loading: true, error: null, data: null };

/**
 * Encapsula GET /api/v1/audit-log (Wave 6, Componente 18).
 *
 * Re-busca quando os filtros mudam. Protecao contra race: `latestReqRef`
 * garante que apenas o resultado da request mais recente atualiza o estado.
 *
 * Sem cache local — audit log precisa refletir o estado atual a cada
 * carregamento (o backend ja envia Cache-Control: no-store; o browser
 * obedece). `refresh()` exposto para botoes "Tentar novamente" / "Atualizar".
 */
export function useAuditLog(
  getToken: () => Promise<string | null>,
  filters: AuditLogFilters,
) {
  const [state, setState] = useState<ListState>(INITIAL_LIST);
  const latestReqRef = useRef<number>(0);
  const mountedRef = useRef(true);

  const queryString = filtersToQueryString(filters);

  const fetchData = useCallback(async (): Promise<void> => {
    const reqId = ++latestReqRef.current;
    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const token = await getToken();
      if (!token) {
        if (mountedRef.current && reqId === latestReqRef.current) {
          setState({
            loading: false,
            error: "Sessao expirada",
            data: null,
          });
        }
        return;
      }

      const data = await apiFetch<AuditLogListResponse>(
        `/api/v1/audit-log${queryString}`,
        { token },
      );

      if (mountedRef.current && reqId === latestReqRef.current) {
        setState({ loading: false, error: null, data });
      }
    } catch (err) {
      if (mountedRef.current && reqId === latestReqRef.current) {
        let msg: string;
        if (err instanceof ApiError) {
          if (err.status === 403) {
            msg = "Acesso restrito ao perfil 3Studio.";
          } else if (err.status === 401) {
            msg = "Sessao expirada. Faca login novamente.";
          } else {
            msg = err.message;
          }
        } else {
          msg = "Erro ao carregar log de auditoria.";
        }
        setState({ loading: false, error: msg, data: null });
      }
    }
  }, [getToken, queryString]);

  useEffect(() => {
    mountedRef.current = true;
    fetchData();
    return () => {
      mountedRef.current = false;
    };
  }, [fetchData]);

  return { ...state, refresh: fetchData };
}

// ─── Hook do detalhe ──────────────────────────────────────────────────────

interface DetailState {
  loading: boolean;
  error: string | null;
  data: AuditLogDetailResponse | null;
}

const INITIAL_DETAIL: DetailState = { loading: false, error: null, data: null };

/**
 * Encapsula GET /api/v1/audit-log/{id}.
 *
 * Carrega sob demanda — `loadDetail(id)` dispara a request. Util para
 * drawers/modais que abrem em resposta a um clique na tabela. Stop:
 * `clear()` reseta o state quando o drawer fecha.
 */
export function useAuditLogDetail(
  getToken: () => Promise<string | null>,
) {
  const [state, setState] = useState<DetailState>(INITIAL_DETAIL);
  const latestReqRef = useRef<number>(0);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const loadDetail = useCallback(
    async (id: string): Promise<void> => {
      const reqId = ++latestReqRef.current;
      setState({ loading: true, error: null, data: null });

      try {
        const token = await getToken();
        if (!token) {
          if (mountedRef.current && reqId === latestReqRef.current) {
            setState({
              loading: false,
              error: "Sessao expirada",
              data: null,
            });
          }
          return;
        }

        const data = await apiFetch<AuditLogDetailResponse>(
          `/api/v1/audit-log/${id}`,
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
              : "Erro ao carregar detalhe.";
          setState({ loading: false, error: msg, data: null });
        }
      }
    },
    [getToken],
  );

  const clear = useCallback(() => {
    latestReqRef.current++; // invalida pendente
    setState(INITIAL_DETAIL);
  }, []);

  return { ...state, loadDetail, clear };
}
