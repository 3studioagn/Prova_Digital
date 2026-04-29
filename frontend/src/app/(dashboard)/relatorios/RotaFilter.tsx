"use client";

/**
 * Filtro de rota (Wave 5, Componente 16 — auditoria H-01 / RF-013).
 *
 * Segmented pill: Padrao | Direta | Todas. Visual identico ao grupo de
 * presets do DateRangeFilter (`presetButton` / `presetButtonActive`),
 * para preservar consistencia da `filtersBar`.
 *
 * Backend aceita `?rota=PADRAO` ou `?rota=DIRETA`; ausencia significa
 * "todas". O componente refletira esse contrato.
 */
import { ROTA_LABELS, type Rota } from "@/lib/types/prova";

import styles from "./relatorios.module.css";

interface Props {
  value: Rota | null;
  onChange: (rota: Rota | null) => void;
}

interface Option {
  label: string;
  value: Rota | null;
}

const OPTIONS: Option[] = [
  { label: "Todas", value: null },
  { label: ROTA_LABELS.PADRAO.replace("Rota ", ""), value: "PADRAO" },
  { label: ROTA_LABELS.DIRETA.replace("Rota ", ""), value: "DIRETA" },
];

export function RotaFilter({ value, onChange }: Props) {
  return (
    <div
      className={styles.presetGroup}
      role="group"
      aria-label="Filtro por rota"
    >
      {OPTIONS.map((opt) => {
        const isActive = value === opt.value;
        const key = opt.value ?? "todas";
        return (
          <button
            key={key}
            type="button"
            className={
              isActive ? styles.presetButtonActive : styles.presetButton
            }
            onClick={() => onChange(opt.value)}
            aria-pressed={isActive}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
