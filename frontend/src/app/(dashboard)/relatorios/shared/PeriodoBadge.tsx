"use client";

/**
 * Badge mostrando o periodo aplicado (Wave 5, Componente 16).
 *
 * Datas exibidas em BRT (DD/MM) — UTC -> BRT na borda.
 * Visual: pill com ponto amarelo + icone calendario + intervalo + sufixo "DIAS".
 */
import { formatDataBrt } from "@/lib/types/report";

import styles from "../relatorios.module.css";

interface Props {
  fromIso: string;
  toIso: string;
  totalDias: number;
}

function CalendarIcon() {
  return (
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
    >
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  );
}

export function PeriodoBadge({ fromIso, toIso, totalDias }: Props) {
  return (
    <span className={styles.periodoBadge} aria-label="Periodo aplicado">
      <span className={styles.periodoDot} aria-hidden="true" />
      <CalendarIcon />
      <span className={styles.periodoRange}>
        {formatDataBrt(fromIso)} - {formatDataBrt(toIso)}
      </span>
      <span className={styles.periodoDivider} aria-hidden="true">
        ·
      </span>
      <span className={styles.periodoDias}>
        {totalDias} {totalDias === 1 ? "DIA" : "DIAS"}
      </span>
    </span>
  );
}
