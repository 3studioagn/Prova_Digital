"use client";

import { useCallback, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import type { TransicaoResponse } from "@/lib/types/prova";

interface State {
  loading: boolean;
  error: string | null;
  result: TransicaoResponse | null;
}

const INITIAL: State = { loading: false, error: null, result: null };

/**
 * Hook para POST /api/v1/provas/{id}/cancelar (Componente 13).
 */
export function useCancelarProva(
  getToken: () => Promise<string | null>,
) {
  const [state, setState] = useState<State>(INITIAL);

  const cancelar = useCallback(
    async (provaId: string, motivoCancelamento: string) => {
      setState({ loading: true, error: null, result: null });
      const token = await getToken();
      if (!token) {
        setState({ loading: false, error: "Sessao expirada.", result: null });
        return null;
      }
      try {
        const data = await apiFetch<TransicaoResponse>(
          `/api/v1/provas/${provaId}/cancelar`,
          {
            token,
            method: "POST",
            body: JSON.stringify({ motivo_cancelamento: motivoCancelamento }),
          },
        );
        setState({ loading: false, error: null, result: data });
        return data;
      } catch (err) {
        const msg =
          err instanceof ApiError
            ? err.status === 409
              ? "Status da prova mudou. Recarregue a pagina."
              : err.status === 403
                ? "Acesso restrito a administradores."
                : err.message
            : "Falha ao cancelar prova.";
        setState({ loading: false, error: msg, result: null });
        return null;
      }
    },
    [getToken],
  );

  const reset = useCallback(() => setState(INITIAL), []);

  return { ...state, cancelar, reset };
}
