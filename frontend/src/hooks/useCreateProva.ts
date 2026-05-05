"use client";

import { useCallback, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import {
  isAllowedImageType,
  MAX_UPLOAD_BYTES,
  type ProvaCreateResponse,
  type RotaCriacao,
  type UploadUrlResponse,
} from "@/lib/types/prova";

interface CreateProvaInput {
  nome: string;
  nro_requerimento: string;
  cliente: string;
  vendedor_id: string;
  /** Wave 2 v4.0: rota e obrigatoria — escolhida manualmente pelo
   * admin entre as 4 opcoes (RN-007 v4.0). */
  rota: RotaCriacao;
  arquivo: File;
}

interface CreateProvaState {
  loading: boolean;
  error: string | null;
  result: ProvaCreateResponse | null;
}

const INITIAL: CreateProvaState = {
  loading: false,
  error: null,
  result: null,
};

/**
 * Encapsula o fluxo completo de criacao de prova digital (ADR-031):
 *
 *   1. POST /api/v1/provas/upload-url      -> presigned URL + object_key
 *   2. PUT <presigned_url>                 -> binario direto no R2
 *   3. POST /api/v1/provas/                -> persiste prova + retorna etiqueta
 *
 * Passo 2 nao passa pelo backend — economiza banda e memoria do Railway.
 * Erros em qualquer etapa devolvem mensagem amigavel no estado `error`.
 */
export function useCreateProva(getToken: () => Promise<string | null>) {
  const [state, setState] = useState<CreateProvaState>(INITIAL);

  const reset = useCallback(() => setState(INITIAL), []);

  const submit = useCallback(
    async (input: CreateProvaInput): Promise<ProvaCreateResponse | null> => {
      // ── Validacao client-side (defesa em profundidade — backend re-valida).
      if (!isAllowedImageType(input.arquivo.type)) {
        setState({
          loading: false,
          error: "O arquivo deve ser JPG ou PNG.",
          result: null,
        });
        return null;
      }
      if (input.arquivo.size > MAX_UPLOAD_BYTES) {
        setState({
          loading: false,
          error: `O arquivo excede o limite de ${MAX_UPLOAD_BYTES / (1024 * 1024)} MB.`,
          result: null,
        });
        return null;
      }

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

      // ── Step 1: pedir presigned URL.
      let uploadData: UploadUrlResponse;
      try {
        uploadData = await apiFetch<UploadUrlResponse>("/api/v1/provas/upload-url", {
          method: "POST",
          token,
          body: JSON.stringify({
            nro_requerimento: input.nro_requerimento,
            filename: input.arquivo.name,
            content_type: input.arquivo.type,
          }),
        });
      } catch (err) {
        const msg =
          err instanceof ApiError
            ? err.message
            : "Nao foi possivel preparar o upload.";
        setState({ loading: false, error: msg, result: null });
        return null;
      }

      // ── Step 2: PUT direto no R2. Sem token — URL ja assinada.
      try {
        const r2Resp = await fetch(uploadData.upload_url, {
          method: "PUT",
          headers: {
            "Content-Type": input.arquivo.type,
          },
          body: input.arquivo,
        });
        if (!r2Resp.ok) {
          throw new Error(`R2 upload failed: ${r2Resp.status}`);
        }
      } catch {
        setState({
          loading: false,
          error: "Falha ao enviar o arquivo. Verifique sua conexao.",
          result: null,
        });
        return null;
      }

      // ── Step 3: confirmar criacao no backend.
      let result: ProvaCreateResponse;
      try {
        result = await apiFetch<ProvaCreateResponse>("/api/v1/provas/", {
          method: "POST",
          token,
          body: JSON.stringify({
            nome: input.nome,
            nro_requerimento: input.nro_requerimento,
            cliente: input.cliente,
            vendedor_id: input.vendedor_id,
            rota: input.rota,
            object_key: uploadData.object_key,
          }),
        });
      } catch (err) {
        const msg =
          err instanceof ApiError
            ? err.message
            : "Nao foi possivel criar a prova digital.";
        setState({ loading: false, error: msg, result: null });
        return null;
      }

      setState({ loading: false, error: null, result });
      return result;
    },
    [getToken],
  );

  return { ...state, submit, reset };
}
