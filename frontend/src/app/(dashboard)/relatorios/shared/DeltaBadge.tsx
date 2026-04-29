"use client";

/**
 * Badge de delta percentual (Wave 5, Componente 16 — refinamento visual).
 *
 * Pill compacta com seta (↗ ou ↘) + percentual. Cor depende do `tone`:
 *   - "positive": verde (ex: total subiu, e bom)
 *   - "negative": rosa/danger (ex: taxa reprovacao subiu, ruim)
 *   - "neutral": cinza (ambiguo / sem direcao implicita)
 *
 * O caller decide o tone — a mesma direcao pode ser positive ou negative
 * dependendo do contexto da metrica.
 */
import type { ReactNode } from "react";

import styles from "../relatorios.module.css";

export type DeltaTone = "positive" | "negative" | "neutral";

interface Props {
  /** Percentual ja em decimal (0.125 = 12.5%) ou em pontos percentuais. */
  value: number;
  /** Como interpretar o sinal — caller controla. */
  tone?: DeltaTone;
  /** Texto auxiliar a direita do badge (ex: "vs. periodo anterior"). */
  suffix?: ReactNode;
  /** Renderizar com fundo branco translucido (uso em card preto). Default: false. */
  onDarkSurface?: boolean;
}

const TONE_CLASS: Record<DeltaTone, string> = {
  positive: "deltaBadgePositive",
  negative: "deltaBadgeNegative",
  neutral: "deltaBadgeNeutral",
};

export function DeltaBadge({
  value,
  tone = "neutral",
  suffix,
  onDarkSurface = false,
}: Props) {
  // Variacao zero: nao renderiza badge (evita "↗ 0.0%" semanticamente confuso).
  // -0 e tratado como 0 via Object.is para evitar arrow ↘ em zero negativo.
  if (value === 0 || Object.is(value, -0)) return null;

  const isUp = value > 0;
  const arrow = isUp ? "↗" : "↘";
  const absPct = Math.abs(value * 100);
  const formatted = absPct.toFixed(1);

  const toneKey = TONE_CLASS[tone] as keyof typeof styles;
  const surfaceClass = onDarkSurface ? styles.deltaBadgeOnDark : "";

  return (
    <span className={styles.deltaWrapper}>
      <span
        className={`${styles.deltaBadge} ${styles[toneKey]} ${surfaceClass}`}
        aria-label={`Variacao ${isUp ? "positiva" : "negativa"} de ${formatted} por cento`}
      >
        <span className={styles.deltaArrow} aria-hidden="true">
          {arrow}
        </span>
        {formatted}%
      </span>
      {suffix && <span className={styles.deltaSuffix}>{suffix}</span>}
    </span>
  );
}
