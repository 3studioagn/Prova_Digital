"use client";

import { useCallback, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import type {
  StatusProva,
  TransicaoResponse,
} from "@/lib/types/prova";

interface ExecutarTransicaoState {
  loading: boolean;
  error: string | null;
  result: TransicaoResponse | null;
}

const INITIAL: ExecutarTransicaoState = {
  loading: false,
  error: null,
  result: null,
};

interface ExecutarTransicaoInput {
  provaId: string;
  statusNovo: StatusProva;
  assinaturaBase64: string;
  motivoReprovacao?: string | null;
}

/**
 * Hook que encapsula o POST `/api/v1/provas/{prova_id}/transicoes`
 * (Componente 11, sub-bloco A.4).
 *
 * Mapeamento de status HTTP em mensagens amigaveis:
 *   - 201: sucesso (result populado com prova + movimentacao)
 *   - 401: "Sessao expirada. Faca login novamente."
 *   - 404: "Prova nao encontrada."
 *   - 409: "O status da prova mudou. Escaneie novamente." (race condition)
 *   - 422: mensagem do backend (motivo, rota, enum, etc)
 *   - 502: "Falha de conexao. Tente novamente em instantes."
 *
 * Nao e um hook com state compartilhado — cada invocacao de `executar`
 * faz uma chamada isolada. O componente chamador e responsavel por
 * guardar o resultado e decidir o proximo passo (voltar para idle,
 * recarregar scan, etc).
 *
 * Wave 8 v5.0 / Componente 22: hook reativado (estava orfao desde o
 * redesenho do C10 v4.0). Adicionado o campo `status` ao retorno de
 * `executar` para o chamador mapear erros com seguranca — distingue 409
 * (race), 401 (sessao), 5xx (rede retentavel) de 422/404 (terminal
 * generico), sem depender de string-matching da mensagem (anti-enumeracao).
 */
export function useExecutarTransicao(
  getToken: () => Promise<string | null>,
) {
  const [state, setState] = useState<ExecutarTransicaoState>(INITIAL);

  const reset = useCallback(() => setState(INITIAL), []);

  const executar = useCallback(
    async (
      input: ExecutarTransicaoInput,
    ): Promise<{
      data: TransicaoResponse | null;
      error: string | null;
      isConflict: boolean;
      status: number | null;
    }> => {
      setState({ loading: true, error: null, result: null });

      let token: string | null;
      try {
        token = await getToken();
      } catch {
        token = null;
      }
      if (!token) {
        const error = "Sessao expirada. Faca login novamente.";
        setState({ loading: false, error, result: null });
        return { data: null, error, isConflict: false, status: 401 };
      }

      try {
        const result = await apiFetch<TransicaoResponse>(
          `/api/v1/provas/${input.provaId}/transicoes`,
          {
            method: "POST",
            token,
            body: JSON.stringify({
              status_novo: input.statusNovo,
              assinatura_base64: input.assinaturaBase64,
              motivo_reprovacao: input.motivoReprovacao ?? null,
            }),
          },
        );
        setState({ loading: false, error: null, result });
        return { data: result, error: null, isConflict: false, status: 201 };
      } catch (err) {
        let msg = "Nao foi possivel executar a transicao.";
        let isConflict = false;
        let status: number | null = null;
        if (err instanceof ApiError) {
          status = err.status;
          if (err.status === 401) {
            msg = "Sessao expirada. Faca login novamente.";
          } else if (err.status === 404) {
            msg = "Prova nao encontrada.";
          } else if (err.status === 409) {
            msg = "O status da prova mudou. Escaneie novamente.";
            isConflict = true;
          } else if (err.status === 422) {
            msg = err.message;
          } else if (err.status >= 500) {
            msg = "Falha de conexao. Tente novamente em instantes.";
          } else {
            msg = err.message;
          }
        }
        setState({ loading: false, error: msg, result: null });
        return { data: null, error: msg, isConflict, status };
      }
    },
    [getToken],
  );

  return { ...state, executar, reset };
}
