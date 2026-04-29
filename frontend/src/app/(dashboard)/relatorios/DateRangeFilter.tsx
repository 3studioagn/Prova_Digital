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
 *
 * Auditoria 2026-04-29 (M-03): offset BRT calculado dinamicamente via
 * `Intl.DateTimeFormat("America/Sao_Paulo")` — resolve eventual retorno
 * do horario de verao no Brasil (BRT/BRST sao tratados pelo runtime do
 * navegador). Brasil aboliu DST em 2019 mas mantemos a defesa por
 * resiliencia regulatoria.
 *
 * Visual: dois pill inputs com prefixo "De"/"Ate" + icone calendario,
 * mais um grupo separado de pills com presets rapidos. O preset ativo
 * (cujo periodo bate com o intervalo atual) ganha destaque preto.
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

const BRT_TIMEZONE = "America/Sao_Paulo";

/**
 * Retorna o offset (em minutos) do fuso BRT em relacao ao UTC para um
 * dado timestamp. Positivo se BRT esta a frente do UTC, negativo se atras.
 *
 * Resiliente a DST: se o Brasil reintroduzir horario de verao, o runtime
 * do navegador devolve `BRST` (-2) entre out-fev e `BRT` (-3) no resto
 * automaticamente via Intl. Em 2026 (estado atual), retorna sempre -180.
 */
function brtOffsetMinutes(at: Date): number {
  // Truque: formata a hora UTC do `at` como se estivesse em SP, parse de volta.
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone: BRT_TIMEZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
  const parts = fmt.formatToParts(at);
  const get = (type: string) =>
    Number(parts.find((p) => p.type === type)?.value ?? 0);
  // Hour pode vir "24" para meia-noite em alguns engines — normaliza.
  const hour = get("hour") % 24;
  const asUtc = Date.UTC(
    get("year"),
    get("month") - 1,
    get("day"),
    hour,
    get("minute"),
    get("second"),
  );
  // (BRT_local - UTC_real) em minutos
  return Math.round((asUtc - at.getTime()) / 60_000);
}

/** Converte ISO UTC -> string YYYY-MM-DD (BRT) para o input. */
function isoUtcToBrtDate(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  // Aplica offset BRT do momento `date` (resolve DST automaticamente).
  const offsetMs = brtOffsetMinutes(date) * 60_000;
  const brt = new Date(date.getTime() + offsetMs);
  return brt.toISOString().slice(0, 10);
}

/** Converte YYYY-MM-DD (BRT) -> ISO UTC inicio do dia (00:00 BRT). */
function brtDateToIsoUtcStart(brtDate: string): string {
  const [y, m, d] = brtDate.split("-").map(Number);
  // Comeca a partir de uma estimativa em UTC; calcula offset BRT para esse
  // momento; reposiciona. Iteracao unica e suficiente: o offset BRT e
  // estavel em janelas de horas (so muda em transicoes DST).
  const guessUtc = Date.UTC(y, m - 1, d, 3, 0, 0); // BRT~UTC-3 default
  const offsetMin = brtOffsetMinutes(new Date(guessUtc));
  const utc = Date.UTC(y, m - 1, d, 0, 0, 0) - offsetMin * 60_000;
  return new Date(utc).toISOString();
}

/** Converte YYYY-MM-DD (BRT) -> ISO UTC FIM do dia (23:59:59 BRT). */
function brtDateToIsoUtcEnd(brtDate: string): string {
  const [y, m, d] = brtDate.split("-").map(Number);
  const guessUtc = Date.UTC(y, m - 1, d, 23 + 3, 59, 59); // BRT~UTC-3 default
  const offsetMin = brtOffsetMinutes(new Date(guessUtc));
  const utc =
    Date.UTC(y, m - 1, d, 23, 59, 59, 999) - offsetMin * 60_000;
  return new Date(utc).toISOString();
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

function CalendarIconSmall() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={styles.dateInputIcon}
    >
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  );
}

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

  // Detecta qual preset (se algum) corresponde ao intervalo atual,
  // tolerando ate 1h de drift entre clique do preset e armazenamento.
  const activePresetDays = useMemo<number | null>(() => {
    if (!fromISO || !toISO) return null;
    const fromMs = new Date(fromISO).getTime();
    const toMs = new Date(toISO).getTime();
    if (Number.isNaN(fromMs) || Number.isNaN(toMs)) return null;
    const diffDays = Math.round((toMs - fromMs) / (24 * 3600 * 1000));
    const match = PRESETS.find((p) => p.days === diffDays);
    return match ? match.days : null;
  }, [fromISO, toISO]);

  return (
    <div className={styles.dateFilter}>
      <label className={styles.dateInputPill}>
        <span className={styles.dateInputPrefix}>De</span>
        <input
          type="date"
          className={styles.dateInput}
          value={fromValue}
          onChange={handleFromChange}
          max={toValue || undefined}
          aria-label="Data inicial"
        />
        <CalendarIconSmall />
      </label>

      <label className={styles.dateInputPill}>
        <span className={styles.dateInputPrefix}>Ate</span>
        <input
          type="date"
          className={styles.dateInput}
          value={toValue}
          onChange={handleToChange}
          min={fromValue || undefined}
          aria-label="Data final"
        />
        <CalendarIconSmall />
      </label>

      <div
        className={styles.presetGroup}
        role="group"
        aria-label="Periodos rapidos"
      >
        {PRESETS.map((preset) => {
          const isActive = activePresetDays === preset.days;
          return (
            <button
              key={preset.label}
              type="button"
              className={
                isActive ? styles.presetButtonActive : styles.presetButton
              }
              onClick={() => applyPreset(preset.days)}
              aria-pressed={isActive}
            >
              {preset.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
