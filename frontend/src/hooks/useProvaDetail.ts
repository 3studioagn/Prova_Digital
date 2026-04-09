"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import type {
  ImagemUrlResponse,
  MovimentacaoListResponse,
  ProvaDetailResponse,
} from "@/lib/types/prova";

interface State {
  loading: boolean;
  error: string | null;
  prova: ProvaDetailResponse | null;
  imagemUrl: ImagemUrlResponse | null;
  imagemError: string | null;
  movimentacoes: MovimentacaoListResponse | null;
}

const INITIAL: State = {
  loading: true,
  error: null,
  prova: null,
  imagemUrl: null,
  imagemError: null,
  movimentacoes: null,
};

/**
 * Carrega detalhe + imagem-url + movimentacoes em paralelo via Promise.allSettled.
 *
 * Promise.allSettled e usado para que um erro parcial (ex: R2 falhando na
 * URL da imagem das provas LIST-TEST-*) nao derrube a tela toda — o usuario
 * ainda ve os dados e o historico, com uma mensagem especifica na area da
 * arte.
 */
export function useProvaDetail(
  provaId: string | null,
  getToken: () => Promise<string | null>,
) {
  const [state, setState] = useState<State>(INITIAL);

  const load = useCallback(async () => {
    if (!provaId) return;
    setState({ ...INITIAL, loading: true });

    let token: string | null;
    try {
      token = await getToken();
    } catch {
      token = null;
    }
    if (!token) {
      setState({
        ...INITIAL,
        loading: false,
        error: "Sessao expirada. Faca login novamente.",
      });
      return;
    }

    const base = `/api/v1/provas/${provaId}`;

    const [provaRes, imagemRes, movRes] = await Promise.allSettled([
      apiFetch<ProvaDetailResponse>(base, { token }),
      apiFetch<ImagemUrlResponse>(`${base}/imagem-url`, { token }),
      apiFetch<MovimentacaoListResponse>(`${base}/movimentacoes`, { token }),
    ]);

    // Erro na prova em si = erro total — nao tem o que mostrar.
    if (provaRes.status === "rejected") {
      const err = provaRes.reason;
      const msg =
        err instanceof ApiError
          ? err.status === 404
            ? "Prova nao encontrada."
            : err.message
          : "Nao foi possivel carregar a prova.";
      setState({
        ...INITIAL,
        loading: false,
        error: msg,
      });
      return;
    }

    // Erro na imagem-url e tolerado — so marca imagemError.
    let imagemUrl: ImagemUrlResponse | null = null;
    let imagemError: string | null = null;
    if (imagemRes.status === "fulfilled") {
      imagemUrl = imagemRes.value;
    } else {
      const err = imagemRes.reason;
      imagemError =
        err instanceof ApiError
          ? err.message
          : "Nao foi possivel carregar a arte.";
    }

    // Erro em movimentacoes tambem e tolerado — fica null, UI mostra fallback.
    let movimentacoes: MovimentacaoListResponse | null = null;
    if (movRes.status === "fulfilled") {
      movimentacoes = movRes.value;
    }

    setState({
      loading: false,
      error: null,
      prova: provaRes.value,
      imagemUrl,
      imagemError,
      movimentacoes,
    });
  }, [provaId, getToken]);

  useEffect(() => {
    load();
  }, [load]);

  return { ...state, reload: load };
}
