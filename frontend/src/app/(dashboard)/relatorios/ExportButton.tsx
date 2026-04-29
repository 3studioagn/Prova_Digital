"use client";

/**
 * Botao de exportacao CSV (Wave 5, Componente 16).
 *
 * Dropdown com 4 datasets: Resumo, Por vendedor, Atrasadas, Provas.
 * Cada um chama useReportExport.exportCsv com o dataset correspondente.
 * Auditoria server-side: backend loga acao=REPORT_EXPORTED antes do streaming.
 */
import { useCallback, useEffect, useRef, useState } from "react";

import { useFocusTrap } from "@/hooks/useFocusTrap";
import {
  EXPORT_DATASETS,
  EXPORT_DATASET_LABELS,
  type ExportDataset,
  type ReportFilters,
} from "@/lib/types/report";

import styles from "./relatorios.module.css";

function DownloadIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );
}

interface Props {
  filters: ReportFilters;
  queryString: string;
  exporting: boolean;
  error: string | null;
  exportCsv: (
    filters: ReportFilters,
    dataset: ExportDataset,
    queryString: string,
  ) => Promise<void>;
  clearError: () => void;
}

/**
 * NOTA SOBRE DATASETS POR SCOPE:
 * - `summary` funciona para todos os 4 scopes (KPIs do scope ativo).
 * - `by-seller` so faz sentido para scope=vendedores no backend, mas o
 *   backend atende qualquer scope (ele agrega vendedores independente).
 * - `overdue` e `proofs` sao snapshots/listagens — independem do scope.
 *
 * UX: oferecemos os 4 datasets sempre. O backend lida com edge cases.
 */

export function ExportButton({
  filters,
  queryString,
  exporting,
  error,
  exportCsv,
  clearError,
}: Props) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const trapRef = useFocusTrap<HTMLDivElement>(open);

  // Combina containerRef + trapRef no mesmo elemento.
  const setRefs = useCallback(
    (node: HTMLDivElement | null) => {
      containerRef.current = node;
      trapRef(node);
    },
    [trapRef],
  );

  // Click fora fecha o menu.
  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  // Escape fecha
  useEffect(() => {
    if (!open) return;
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open]);

  const handlePick = useCallback(
    async (dataset: ExportDataset) => {
      setOpen(false);
      clearError();
      await exportCsv(filters, dataset, queryString);
    },
    [exportCsv, filters, queryString, clearError],
  );

  return (
    <div className={styles.exportContainer} ref={setRefs}>
      <button
        type="button"
        className={styles.exportButton}
        onClick={() => setOpen((v) => !v)}
        disabled={exporting}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <DownloadIcon />
        {exporting ? "Exportando..." : "Exportar CSV"}
        <span className={styles.exportCaret} aria-hidden="true">
          ▾
        </span>
      </button>

      {open && (
        <div
          className={styles.exportMenu}
          role="menu"
          aria-label="Datasets para exportar"
        >
          {EXPORT_DATASETS.map((dataset) => (
            <button
              key={dataset}
              type="button"
              role="menuitem"
              className={styles.exportMenuItem}
              onClick={() => handlePick(dataset)}
            >
              {EXPORT_DATASET_LABELS[dataset]}
            </button>
          ))}
        </div>
      )}

      {error && (
        <div className={styles.exportError} role="alert">
          {error}
          <button
            type="button"
            className={styles.exportErrorDismiss}
            onClick={clearError}
            aria-label="Fechar mensagem de erro"
          >
            ×
          </button>
        </div>
      )}
    </div>
  );
}
