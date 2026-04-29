"use client";

/**
 * Filtro de status (Wave 5, Componente 16 — auditoria H-01 / RF-013).
 *
 * `<select>` nativo com 10 opcoes (todos os StatusProvaEnum) + "Todos".
 * Visual: pill estilo dos outros filtros, com chevron customizado e
 * `appearance: none` (CSS global ja define).
 *
 * Backend aceita `?status=<enum>`; ausencia significa "todos".
 *
 * Nota UX: na perspectiva Geral, o usuario tambem pode filtrar status
 * clicando num segmento do DonutChart "Provas Ativas" (mantido). Ambos
 * caminhos atualizam o mesmo URL param, entao se mantem em sync.
 */
import { useId } from "react";

import {
  STATUS_LABELS,
  STATUS_OPTIONS,
  type StatusProva,
} from "@/lib/types/prova";

import styles from "./relatorios.module.css";

interface Props {
  value: StatusProva | null;
  onChange: (status: StatusProva | null) => void;
}

export function StatusFilter({ value, onChange }: Props) {
  const id = useId();
  return (
    <label className={styles.selectFilterPill} htmlFor={id}>
      <span className={styles.selectFilterPrefix}>Status</span>
      <select
        id={id}
        className={styles.selectFilterInput}
        value={value ?? ""}
        onChange={(e) => {
          const v = e.target.value;
          onChange(v === "" ? null : (v as StatusProva));
        }}
        aria-label="Filtrar por status"
      >
        <option value="">Todos</option>
        {STATUS_OPTIONS.map((s) => (
          <option key={s} value={s}>
            {STATUS_LABELS[s]}
          </option>
        ))}
      </select>
      <svg
        width="12"
        height="12"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        className={styles.selectFilterChevron}
      >
        <polyline points="6 9 12 15 18 9" />
      </svg>
    </label>
  );
}
