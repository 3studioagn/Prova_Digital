"use client";

import { useEffect, useRef, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import type { AuditLogItem } from "@/lib/types/auditoria";

/**
 * Hook de detalhe pontual do audit log (Wave 6, Componente 18).
 *
 * Encapsula `GET /api/v1/auditoria/{log_id}` para carregar uma entrada
 * especifica — tipicamente usado pelo modal de detalhes que abre quando
 * o admin clica numa linha da listagem.
 *
 * Design:
 *
 *  - **`logId=null` = estado inativo:** quando o modal nao esta aberto,
 *    o caller passa `logId=null` e o hook retorna estado vazio sem fazer
 *    fetch. Trocar para um UUID dispara o fetch automatico.
 *
 *  - **AbortController + timeout 30 s:** mesmo padrao do `useAuditoria`
 *    (ADR-098, L-05).
 *
 *  - **AbortError silencioso:** cancelamentos legitimos (trocar de log,
 *    fechar modal, timeout) nao viram "Erro ao carregar".
 *
 *  - **404 tratado:** o backend retorna 404 para log inexistente; o
 *    `ApiError.status === 404` e convertido em mensagem amigavel pt-BR.
 *
 * @param getToken  Factory assincrona que resolve o token Supabase atual.
 * @param logId     UUID do log a buscar, ou `null` para nao fazer fetch.
 */
export function useAuditoriaDetail(
  getToken: () => Promise<string | null>,
  logId: string | null,
): State {
  const [state, setState] = useState<State>(INITIAL);
  const mountedRef = useRef(true);
  const abortRef = useRef<AbortController | null>(null);

  // Montagem/desmontagem: limpa abort pendente + seta mountedRef.
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      abortRef.current?.abort();
    };
  }, []);

  // Busca quando `logId` muda (incluindo de `null` -> uuid ou vice-versa).
  useEffect(() => {
    // Estado inativo: sem log selecionado.
    if (!logId) {
      setState(INITIAL);
      return;
    }

    // Cancelar fetch anterior em voo (L-05) e armar novo.
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const timeoutId = setTimeout(
      () => controller.abort(),
      REQUEST_TIMEOUT_MS,
    );

    setState({ loading: true, error: null, data: null });

    (async () => {
      try {
        const token = await getToken();
        if (!token) {
          if (mountedRef.current) {
            setState({
              loading: false,
              error: "Sessao expirada",
              data: null,
            });
          }
          return;
        }

        const data = await apiFetch<AuditLogItem>(
          `/api/v1/auditoria/${logId}`,
          {
            token,
            signal: controller.signal,
          },
        );

        if (mountedRef.current) {
          setState({ loading: false, error: null, data });
        }
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }
        if (mountedRef.current) {
          const msg =
            err instanceof ApiError
              ? err.status === 404
                ? "Log de auditoria nao encontrado"
                : err.message
              : "Erro ao carregar log de auditoria";
          setState({ loading: false, error: msg, data: null });
        }
      } finally {
        clearTimeout(timeoutId);
      }
    })();

    // Cleanup de efeito (alem do unmount): aborta fetch quando `logId`
    // muda no meio de um fetch anterior.
    return () => {
      controller.abort();
      clearTimeout(timeoutId);
    };
  }, [logId, getToken]);

  return state;
}

// =============================================================================
// Internals
// =============================================================================

// Mesmo timeout do useAuditoria — mantido separado para permitir tuning
// independente no futuro se precisar.
const REQUEST_TIMEOUT_MS = 30_000;

interface State {
  loading: boolean;
  error: string | null;
  data: AuditLogItem | null;
}

const INITIAL: State = {
  loading: false,
  error: null,
  data: null,
};
