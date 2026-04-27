"use client";

/**
 * Download de CSV de relatorios (Wave 5, Componente 16).
 *
 * Endpoint: GET /api/v1/reports/export?scope=...&dataset=...&from=...&to=...
 * Resposta: text/csv; charset=utf-8 (com BOM UTF-8 para Excel).
 *
 * Padrao do projeto (Wave 2 — etiqueta PDF, Wave 3 — QR PNG):
 *   - apiFetch NAO suporta binarios. Fetch direto + response.blob().
 *   - URL.createObjectURL para download via <a download> sintetico.
 *   - revogar object URL no cleanup para nao vazar memoria.
 */
import { useCallback, useState } from "react";

import { ApiError } from "@/lib/api";
import type { ExportDataset, ReportFilters } from "@/lib/types/report";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ExportState {
  exporting: boolean;
  error: string | null;
}

const INITIAL: ExportState = { exporting: false, error: null };

export interface UseReportExportResult extends ExportState {
  /**
   * Inicia o download do CSV. O navegador lida com o salvar; nada e
   * armazenado em estado React (so erro/loading).
   */
  exportCsv: (
    filters: ReportFilters,
    dataset: ExportDataset,
    queryString: string,
  ) => Promise<void>;
  clearError: () => void;
}

/** Extrai filename do header Content-Disposition (RFC 5987 + classic). */
function parseFilename(header: string | null, fallback: string): string {
  if (!header) return fallback;
  // filename*=UTF-8''<encoded> — preferencial
  const star = header.match(/filename\*=UTF-8''([^;]+)/i);
  if (star) {
    try {
      return decodeURIComponent(star[1]);
    } catch {
      // fall-through
    }
  }
  // filename="..."
  const classic = header.match(/filename="([^"]+)"/i);
  if (classic) return classic[1];
  return fallback;
}

export function useReportExport(
  getToken: () => Promise<string | null>,
): UseReportExportResult {
  const [state, setState] = useState<ExportState>(INITIAL);

  const exportCsv = useCallback(
    async (
      filters: ReportFilters,
      dataset: ExportDataset,
      queryString: string,
    ): Promise<void> => {
      setState({ exporting: true, error: null });

      let token: string | null;
      try {
        token = await getToken();
      } catch {
        token = null;
      }
      if (!token) {
        setState({
          exporting: false,
          error: "Sessao expirada. Faca login novamente.",
        });
        return;
      }

      // Anexa `dataset` ao queryString existente (queryString ja tem scope/from/to/...).
      const params = new URLSearchParams(queryString);
      params.set("dataset", dataset);

      const url = `${API_URL}/api/v1/reports/export?${params.toString()}`;
      let blobUrl: string | null = null;

      try {
        const res = await fetch(url, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (!res.ok) {
          let detail = `HTTP ${res.status}`;
          try {
            const body = await res.json();
            detail = body.detail || detail;
          } catch {
            // body nao-JSON
          }
          throw new ApiError(detail, res.status);
        }

        const blob = await res.blob();
        const filename = parseFilename(
          res.headers.get("content-disposition"),
          `relatorio_${filters.scope}_${dataset}.csv`,
        );

        blobUrl = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = blobUrl;
        anchor.download = filename;
        anchor.style.display = "none";
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();

        setState({ exporting: false, error: null });
      } catch (err) {
        const msg =
          err instanceof ApiError
            ? err.message
            : "Erro ao exportar relatorio.";
        setState({ exporting: false, error: msg });
      } finally {
        if (blobUrl) {
          // Browser ja iniciou download — pode revogar.
          URL.revokeObjectURL(blobUrl);
        }
      }
    },
    [getToken],
  );

  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  return { ...state, exportCsv, clearError };
}
