"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import type { RelatorioResponse } from "@/lib/types/relatorio";

interface State {
  loading: boolean;
  error: string | null;
  data: RelatorioResponse | null;
}

const INITIAL: State = { loading: true, error: null, data: null };

// L-05 (auditoria Wave 5 ronda 2): timeout de 30s em rede lenta para nao
// deixar o usuario pendurado. Relatorios sao admin-only e operacoes
// acessadas esporadicamente — 30s cobre backend com drift de cold-start +
// margem generosa. Se o backend nao respondeu em 30s, provavelmente ja
// deu timeout no lado do servidor, ou ha problema real de rede.
const REQUEST_TIMEOUT_MS = 30_000;

/**
 * Encapsula GET /api/v1/provas/relatorios (Wave 5, Componente 16).
 *
 * Aceita filtro de periodo opcional. Sem periodo, o backend usa default
 * de 30 dias. Race protection via latestReqRef. Cancelamento via
 * AbortController — cada nova chamada de refresh cancela a anterior,
 * e o unmount cancela a em voo. Timeout de 30s (REQUEST_TIMEOUT_MS)
 * aborta requests que nao respondem.
 */
export function useRelatorios(
  getToken: () => Promise<string | null>,
  inicio?: string,
  fim?: string,
) {
  const [state, setState] = useState<State>(INITIAL);
  const latestReqRef = useRef<number>(0);
  const mountedRef = useRef(true);
  const abortRef = useRef<AbortController | null>(null);

  const refresh = useCallback(async (): Promise<void> => {
    // Cancelar request anterior em voo (L-05)
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const timeoutId = setTimeout(
      () => controller.abort(),
      REQUEST_TIMEOUT_MS,
    );

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

      const params = new URLSearchParams();
      if (inicio) params.set("periodo_inicio", inicio);
      if (fim) params.set("periodo_fim", fim);
      const qs = params.toString();
      const path = `/api/v1/provas/relatorios${qs ? `?${qs}` : ""}`;

      const data = await apiFetch<RelatorioResponse>(path, {
        token,
        signal: controller.signal,
      });

      if (mountedRef.current && reqId === latestReqRef.current) {
        setState({ loading: false, error: null, data });
      }
    } catch (err) {
      // Ignorar erros de aborto — sao esperados (usuario trocou periodo,
      // componente desmontou, ou timeout disparou). Nao queremos mostrar
      // "Erro ao carregar" nesses casos.
      if (
        err instanceof DOMException && err.name === "AbortError"
      ) {
        return;
      }
      if (mountedRef.current && reqId === latestReqRef.current) {
        const msg =
          err instanceof ApiError
            ? err.message
            : "Erro ao carregar relatorios";
        setState({ loading: false, error: msg, data: null });
      }
    } finally {
      clearTimeout(timeoutId);
    }
  }, [getToken, inicio, fim]);

  useEffect(() => {
    mountedRef.current = true;
    refresh();
    return () => {
      mountedRef.current = false;
      // Cancelar request em voo no unmount (L-05)
      abortRef.current?.abort();
    };
  }, [refresh]);

  return { ...state, refresh };
}
