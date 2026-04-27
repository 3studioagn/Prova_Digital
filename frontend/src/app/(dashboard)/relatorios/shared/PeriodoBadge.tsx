"use client";

/**
 * Badge mostrando o periodo aplicado (Wave 5, Componente 16).
 *
 * Datas exibidas em BRT (DD/MM) — UTC -> BRT na borda.
 */
import { formatDataBrt } from "@/lib/types/report";

import styles from "../relatorios.module.css";

interface Props {
  fromIso: string;
  toIso: string;
  totalDias: number;
}

export function PeriodoBadge({ fromIso, toIso, totalDias }: Props) {
  return (
    <span className={styles.periodoBadge} aria-label="Periodo aplicado">
      {formatDataBrt(fromIso)} – {formatDataBrt(toIso)} · {totalDias} dia
      {totalDias !== 1 ? "s" : ""}
    </span>
  );
}
