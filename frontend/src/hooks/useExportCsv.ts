"use client";

import { useCallback, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// L-05 (auditoria Wave 5 ronda 2): timeout de 60s para o export de CSV.
// Mais generoso que o /relatorios JSON (30s) porque a query do CSV e
// maior (10k linhas no limite) e a serializacao + write podem demorar.
// Se o CSV nao respondeu em 60s, algo esta errado — admin prefere um
// erro claro a ficar esperando indefinidamente.
const CSV_TIMEOUT_MS = 60_000;

/**
 * Hook para download do CSV de relatorios (Wave 5, Componente 16).
 *
 * Usa fetch direto (nao apiFetch) porque o response e binario (blob),
 * nao JSON. Padrao identico ao usado para /etiqueta.pdf e /qr-code.png
 * (CLAUDE.md: "Binarios no frontend"). Timeout de 60s via AbortController.
 */
export function useExportCsv(getToken: () => Promise<string | null>) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const download = useCallback(
    async (inicio?: string, fim?: string): Promise<void> => {
      setLoading(true);
      setError(null);

      // L-05: AbortController com timeout de 60s.
      const controller = new AbortController();
      const timeoutId = setTimeout(
        () => controller.abort(),
        CSV_TIMEOUT_MS,
      );

      try {
        const token = await getToken();
        if (!token) {
          setError("Sessao expirada");
          setLoading(false);
          return;
        }

        const params = new URLSearchParams();
        if (inicio) params.set("periodo_inicio", inicio);
        if (fim) params.set("periodo_fim", fim);
        const qs = params.toString();
        const url = `${API_URL}/api/v1/provas/relatorios/csv${qs ? `?${qs}` : ""}`;

        const res = await fetch(url, {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        });

        if (!res.ok) {
          const body = await res
            .json()
            .catch(() => ({ detail: "Erro ao exportar planilha" }));
          setError(body.detail || `HTTP ${res.status}`);
          setLoading(false);
          return;
        }

        const blob = await res.blob();
        const blobUrl = URL.createObjectURL(blob);

        const disposition = res.headers.get("content-disposition") || "";
        const filenameMatch = disposition.match(/filename="?([^"]+)"?/);
        const filename = filenameMatch
          ? filenameMatch[1]
          : "relatorio_provas.csv";

        const a = document.createElement("a");
        a.href = blobUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(blobUrl);

        setLoading(false);
      } catch (err) {
        // AbortError = timeout disparou ou usuario navegou. Dar mensagem
        // clara em vez de "Erro generico".
        if (err instanceof DOMException && err.name === "AbortError") {
          setError("Exportacao cancelada (timeout ou navegacao)");
        } else {
          setError("Erro ao exportar planilha");
        }
        setLoading(false);
      } finally {
        clearTimeout(timeoutId);
      }
    },
    [getToken],
  );

  return { download, loading, error };
}
