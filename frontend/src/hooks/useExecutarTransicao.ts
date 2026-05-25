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

export interface ExecutarTransicaoInput {
  provaId: string;
  statusNovo: StatusProva;
  assinaturaBase64: string;
  motivoReprovacao?: string | null;
}

export interface ExecutarTransicaoResult {
  data: TransicaoResponse | null;
  error: string | null;
  isConflict: boolean;
  status: number | null;
}

export interface ExecutarTransicaoParams {
  /** Funcao que devolve o JWT atual. Recebida do chamador para manter
   *  a funcao desacoplada do Supabase client. */
  getToken: () => Promise<string | null>;
}

/**
 * Funcao pura que executa o POST `/api/v1/provas/{prova_id}/transicoes`
 * (Componente 11, sub-bloco A.4) e mapeia erros para mensagens em pt-BR.
 * Extraida do hook `useExecutarTransicao` em 2026-05-25 (AUD-W8C22-005)
 * para permitir teste isolado em `vitest --environment node` (sem JSDOM
 * nem `@testing-library/react`), seguindo o padrao da camada de servico
 * `identificacao-prova.ts` (cultura D-13 do projeto — Vitest minimal).
 *
 * Mapeamento de status HTTP (cf. JSDoc do hook):
 *   - 201: sucesso
 *   - 401: "Sessao expirada. Faca login novamente."
 *   - 404: "Prova nao encontrada."
 *   - 409: "O status da prova mudou. Escaneie novamente." + isConflict=true
 *   - 422: mensagem GENERICA (AUD-W8C22-003 — defesa anti-enumeracao)
 *   - 5xx: "Falha de conexao. Tente novamente em instantes."
 *   - rede caiu (fetch threw / nao-ApiError): mensagem generica + status=null
 *   - getToken null/throw: "Sessao expirada..." + status=401 sem chamar fetch
 *
 * Nao acopla com React/DOM — pura e testavel.
 */
export async function executarTransicaoRequest(
  input: ExecutarTransicaoInput,
  params: ExecutarTransicaoParams,
): Promise<ExecutarTransicaoResult> {
  let token: string | null;
  try {
    token = await params.getToken();
  } catch {
    token = null;
  }
  if (!token) {
    return {
      data: null,
      error: "Sessao expirada. Faca login novamente.",
      isConflict: false,
      status: 401,
    };
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
        // AUD-W8C22-003: defesa em profundidade anti-enumeracao. O
        // backend pode retornar 422 com `AtorNaoAutorizadoError` cujo
        // texto LISTA os setores permitidos. Mesmo o AssinaturaModal
        // hoje desestruturando so `executar`, qualquer consumidor
        // futuro que faca `const { error } = useExecutarTransicao(...)`
        // exporia. Mensagem generica fixa; `status === 422` no retorno
        // permite o chamador decidir o tratamento.
        msg = "Nao foi possivel registrar a movimentacao.";
      } else if (err.status >= 500) {
        msg = "Falha de conexao. Tente novamente em instantes.";
      } else {
        // Demais status (403, etc.) - tambem mensagem generica fixa
        // (AUD-W8C22-003). NUNCA repassar `err.message` cru fora dos
        // casos especificos acima (401/404/409/5xx ja tem texto pt-BR
        // fixo). `status` no retorno preserva a informacao tecnica.
        msg = "Nao foi possivel executar a transicao.";
      }
    }
    return { data: null, error: msg, isConflict, status };
  }
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
 *   - 422: mensagem GENERICA "Nao foi possivel registrar..."
 *          — DEFESA EM PROFUNDIDADE ANTI-ENUMERACAO (AUD-W8C22-003): o
 *          backend pode retornar 422 com `AtorNaoAutorizadoError` cujo
 *          texto LISTA os setores permitidos. Mesmo o modal hoje nao
 *          consumindo `error`, qualquer consumidor futuro que faca
 *          `const { error } = useExecutarTransicao(...)` exporia. O
 *          chamador usa `status === 422` para decidir o tratamento.
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
 *
 * AUD-W8C22-005 (2026-05-25): a logica foi extraida para a funcao pura
 * `executarTransicaoRequest` (exportada deste mesmo modulo) para teste
 * isolado em `vitest --environment node`. Este hook agora e um wrapper
 * trivial que adiciona o `useState` para consumidores que precisem do
 * `loading`/`error`/`result` (atualmente nenhum — o `AssinaturaModal`
 * desestrutura so `executar`).
 */
export function useExecutarTransicao(
  getToken: () => Promise<string | null>,
) {
  const [state, setState] = useState<ExecutarTransicaoState>(INITIAL);

  const reset = useCallback(() => setState(INITIAL), []);

  const executar = useCallback(
    async (
      input: ExecutarTransicaoInput,
    ): Promise<ExecutarTransicaoResult> => {
      setState({ loading: true, error: null, result: null });
      const out = await executarTransicaoRequest(input, { getToken });
      setState({
        loading: false,
        error: out.error,
        result: out.data,
      });
      return out;
    },
    [getToken],
  );

  return { ...state, executar, reset };
}
