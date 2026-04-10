"use client";

import { useCallback, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import type { ScanResponse } from "@/lib/types/prova";

interface ScanState {
  loading: boolean;
  error: string | null;
  result: ScanResponse | null;
}

const INITIAL: ScanState = {
  loading: false,
  error: null,
  result: null,
};

/**
 * Hook que encapsula o POST `/api/v1/provas/scan` (Componente 10, sub-bloco A.3).
 *
 * Fluxo:
 *   1. Recebe um `payload` ja decodificado pelo html5-qrcode (string "3SD|...").
 *   2. Faz POST com Bearer token, aguarda 200.
 *   3. Retorna `ScanResponse` com `prova` + `transicoes_permitidas` +
 *      `motivo_obrigatorio_em`.
 *
 * Erros mapeados em mensagens amigaveis:
 *   - 404: "Prova nao encontrada."
 *   - 422: mensagem do backend (formato invalido, hash nao bate)
 *   - 401: "Sessao expirada. Faca login novamente."
 *   - 502: "Falha de conexao. Tente novamente em instantes."
 *
 * Nao mantem cache — cada invocacao de `escanear` e uma chamada nova.
 * O componente chamador controla quando chamar e guarda o resultado.
 */
export function useScanProva(getToken: () => Promise<string | null>) {
  const [state, setState] = useState<ScanState>(INITIAL);

  const reset = useCallback(() => setState(INITIAL), []);

  const escanear = useCallback(
    async (payload: string): Promise<ScanResponse | null> => {
      setState({ loading: true, error: null, result: null });

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
          result: null,
        });
        return null;
      }

      try {
        const result = await apiFetch<ScanResponse>("/api/v1/provas/scan", {
          method: "POST",
          token,
          body: JSON.stringify({ payload }),
        });
        setState({ loading: false, error: null, result });
        return result;
      } catch (err) {
        let msg = "Nao foi possivel resolver o QR Code.";
        if (err instanceof ApiError) {
          if (err.status === 401) {
            msg = "Sessao expirada. Faca login novamente.";
          } else if (err.status === 404) {
            msg = "Prova nao encontrada.";
          } else if (err.status === 422) {
            msg = err.message;
          } else if (err.status >= 500) {
            msg = "Falha de conexao. Tente novamente em instantes.";
          } else {
            msg = err.message;
          }
        }
        setState({ loading: false, error: msg, result: null });
        return null;
      }
    },
    [getToken],
  );

  return { ...state, escanear, reset };
}
