"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import {
  type ChaveConfiguracao,
  type ConfiguracaoListResponse,
  type ConfiguracaoResponse,
} from "@/lib/types/configuracao";

interface UseConfiguracoesState {
  loading: boolean;
  error: string | null;
  configuracoes: Record<string, ConfiguracaoResponse>;
}

const INITIAL: UseConfiguracoesState = {
  loading: true,
  error: null,
  configuracoes: {},
};

/**
 * Carrega todas as configuracoes whitelisted e expoe um `updateConfiguracao`
 * que faz PATCH individual. O estado e indexado por chave para acesso O(1)
 * pelas seccoes do form.
 */
export function useConfiguracoes(getToken: () => Promise<string | null>) {
  const [state, setState] = useState<UseConfiguracoesState>(INITIAL);

  const load = useCallback(async () => {
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
        configuracoes: {},
      });
      return;
    }

    try {
      const resp = await apiFetch<ConfiguracaoListResponse>(
        "/api/v1/configuracoes/",
        { token },
      );
      const indexed: Record<string, ConfiguracaoResponse> = {};
      for (const item of resp.items) {
        indexed[item.chave] = item;
      }
      setState({ loading: false, error: null, configuracoes: indexed });
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : "Nao foi possivel carregar configuracoes.";
      setState({ loading: false, error: msg, configuracoes: {} });
    }
  }, [getToken]);

  useEffect(() => {
    load();
  }, [load]);

  const updateConfiguracao = useCallback(
    async (
      chave: ChaveConfiguracao,
      valor: unknown,
      descricao?: string,
    ): Promise<{ ok: boolean; error: string | null }> => {
      let token: string | null;
      try {
        token = await getToken();
      } catch {
        token = null;
      }
      if (!token) {
        return { ok: false, error: "Sessao expirada. Faca login novamente." };
      }

      try {
        const payload: Record<string, unknown> = { valor };
        if (descricao !== undefined) payload.descricao = descricao;

        const updated = await apiFetch<ConfiguracaoResponse>(
          `/api/v1/configuracoes/${chave}`,
          {
            method: "PATCH",
            token,
            body: JSON.stringify(payload),
          },
        );

        // Atualiza cache local
        setState((s) => ({
          ...s,
          configuracoes: { ...s.configuracoes, [chave]: updated },
        }));

        return { ok: true, error: null };
      } catch (err) {
        const msg =
          err instanceof ApiError
            ? err.message
            : "Nao foi possivel atualizar a configuracao.";
        return { ok: false, error: msg };
      }
    },
    [getToken],
  );

  return { ...state, reload: load, updateConfiguracao };
}
