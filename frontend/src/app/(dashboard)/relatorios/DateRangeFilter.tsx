"use client";

/**
 * Filtro de periodo (Wave 5, Componente 16).
 *
 * Inputs `<input type="date">` nativos (mesmo padrao da Wave 2 listagem)
 * + presets rapidos: Hoje, 7d, 30d, 90d.
 *
 * Datas sao tratadas como strings YYYY-MM-DD em fuso BRT, convertidas
 * para ISO-8601 UTC (00:00 BRT do dia => UTC) antes de mandar ao backend.
 * Backend valida em UTC; conversao na borda.
 */
import { useCallback, useMemo } from "react";

import styles from "./relatorios.module.css";

interface Props {
  /** ISO-8601 UTC ou null. */
  fromISO: string | null;
  /** ISO-8601 UTC ou null. */
  toISO: string | null;
  onChange: (next: { from: string | null; to: string | null }) => void;
}

const BRT_OFFSET_HOURS = -3;

/** Converte ISO UTC -> string YYYY-MM-DD (BRT) para o input. */
function isoUtcToBrtDate(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  // Aplica offset BRT para extrair o dia local
  const brt = new Date(date.getTime() + BRT_OFFSET_HOURS * 3600 * 1000);
  return brt.toISOString().slice(0, 10);
}

/** Converte YYYY-MM-DD (BRT) -> ISO UTC inicio do dia (00:00 BRT). */
function brtDateToIsoUtcStart(brtDate: string): string {
  // 2026-04-27 BRT 00:00 == 2026-04-27 03:00 UTC (BRT_OFFSET = -3)
  const [y, m, d] = brtDate.split("-").map(Number);
  const utc = new Date(Date.UTC(y, m - 1, d, -BRT_OFFSET_HOURS, 0, 0));
  return utc.toISOString();
}

/** Converte YYYY-MM-DD (BRT) -> ISO UTC FIM do dia (23:59:59 BRT). */
function brtDateToIsoUtcEnd(brtDate: string): string {
  const [y, m, d] = brtDate.split("-").map(Number);
  // 2026-04-27 BRT 23:59:59.999 == 2026-04-28 02:59:59.999 UTC
  const utc = new Date(
    Date.UTC(y, m - 1, d, -BRT_OFFSET_HOURS + 23, 59, 59, 999),
  );
  return utc.toISOString();
}

interface Preset {
  label: string;
  days: number;
}

const PRESETS: Preset[] = [
  { label: "Hoje", days: 0 },
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
];

export function DateRangeFilter({ fromISO, toISO, onChange }: Props) {
  const fromValue = useMemo(() => isoUtcToBrtDate(fromISO), [fromISO]);
  const toValue = useMemo(() => isoUtcToBrtDate(toISO), [toISO]);

  const handleFromChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const v = event.target.value;
      onChange({
        from: v ? brtDateToIsoUtcStart(v) : null,
        to: toISO,
      });
    },
    [onChange, toISO],
  );

  const handleToChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const v = event.target.value;
      onChange({
        from: fromISO,
        to: v ? brtDateToIsoUtcEnd(v) : null,
      });
    },
    [onChange, fromISO],
  );

  const applyPreset = useCallback(
    (days: number) => {
      const now = new Date();
      const todayBrt = isoUtcToBrtDate(now.toISOString());
      const fromDate = new Date(now.getTime() - days * 24 * 3600 * 1000);
      const fromBrt = isoUtcToBrtDate(fromDate.toISOString());
      onChange({
        from: brtDateToIsoUtcStart(fromBrt),
        to: brtDateToIsoUtcEnd(todayBrt),
      });
    },
    [onChange],
  );

  return (
    <div className={styles.dateFilter}>
      <label className={styles.dateField}>
        <span className={styles.dateLabel}>De:</span>
        <input
          type="date"
          className={styles.dateInput}
          value={fromValue}
          onChange={handleFromChange}
          max={toValue || undefined}
        />
      </label>

      <label className={styles.dateField}>
        <span className={styles.dateLabel}>Ate:</span>
        <input
          type="date"
          className={styles.dateInput}
          value={toValue}
          onChange={handleToChange}
          min={fromValue || undefined}
        />
      </label>

      <div className={styles.presetGroup} role="group" aria-label="Periodos rapidos">
        {PRESETS.map((preset) => (
          <button
            key={preset.label}
            type="button"
            className={styles.presetButton}
            onClick={() => applyPreset(preset.days)}
          >
            {preset.label}
          </button>
        ))}
      </div>
    </div>
  );
}
