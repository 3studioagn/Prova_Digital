"use client";

/**
 * Filtro de rota — segmented pill (Wave 5, Componente 16).
 *
 * Wave 5 v4.0 (Componente 16): semantica do filtro foi expandida para
 * cobrir as 6 rotas (`MATRIZ`, `LAM_MATRIZ`, `FILIAL`, `LAM_FILIAL`,
 * `PADRAO`, `DIRETA`) + provas legacy `rota=NULL` (heuristica do C12
 * Decisao 11.2). O visual permanece IDENTICO ao v3: 3 botoes (Todas /
 * Matriz / Filial) — mesma `presetGroup`/`presetButton` da `filtersBar`.
 *
 * Internamente, o componente agora opera sobre `rota_categoria`
 * (matriz/filial) em vez de `rota` (valor exato). Os 3 botoes mapeiam:
 *   - "Todas"  -> rota_categoria=null
 *   - "Matriz" -> rota_categoria="matriz" (cobre MATRIZ + LAM_MATRIZ +
 *      PADRAO + NULL com vendedor MATRIZ)
 *   - "Filial" -> rota_categoria="filial" (cobre FILIAL + LAM_FILIAL +
 *      DIRETA + NULL com vendedor FILIAL)
 *
 * Backend aceita `?rota_categoria=matriz|filial`; ausencia significa
 * "todas". Precedencia sobre `?rota=` exata se ambos fornecidos.
 *
 * Acessibilidade preservada: `role="group"` + `aria-pressed` por botao.
 */
import type { RotaCategoria } from "@/lib/types/report";

import styles from "./relatorios.module.css";

interface Props {
  value: RotaCategoria | null;
  onChange: (categoria: RotaCategoria | null) => void;
}

interface Option {
  label: string;
  value: RotaCategoria | null;
}

const OPTIONS: Option[] = [
  { label: "Todas", value: null },
  { label: "Matriz", value: "matriz" },
  { label: "Filial", value: "filial" },
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
