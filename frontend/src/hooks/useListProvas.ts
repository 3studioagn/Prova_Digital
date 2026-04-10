"use client";

import { useCallback, useRef, useState } from "react";
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
 * Encapsula GET /api/v1/provas/.
 *
 * O estado local do hook nao lida com a URL — a pagina `/provas` usa
 * `useSearchParams` para sincronizar a URL e passa os filtros atuais
 * para `load()` a cada mudanca.
 *
 * O debounce para campos textuais (busca, cliente) e feito NA PAGINA
 * via setTimeout local em handleBuscaChange/handleClienteChange que
 * atualizam a URL; o useEffect reage a mudanca da URL e chama `load()`.
 * O hook nao precisa de debounce proprio. (Ate a Sessao 18 este hook
 * exportava um `loadDebounced` que nunca foi chamado pela pagina — dead
 * code removido na auditoria Wave 2 Sessao 19, A4.)
 *
 * Protecao contra race: `latestReqRef` garante que apenas o resultado
 * do load() mais recente atualiza o estado, descartando responses
 * fora-de-ordem se o usuario mudar filtros enquanto uma request esta
 * em voo.
 */
export function useListProvas(getToken: () => Promise<string | null>) {
  const [state, setState] = useState<State>(INITIAL);
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

  return { ...state, load };
}
