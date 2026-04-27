"use client";

/**
 * Grafico de serie temporal SVG inline (Wave 5, Componente 16).
 *
 * Renderiza barras verticais (em vez de linha) — bar chart por dia funciona
 * melhor para volumes baixos (10-30 pontos) e contagens discretas como
 * "provas criadas por dia". Linha seria adequado para metricas continuas.
 *
 * Animacao: cada barra cresce do bottom (height 0 -> final) com stagger.
 * Acessibilidade: role="img" + aria-label + tabela abaixo (details).
 */
import { motion } from "framer-motion";
import { useMemo } from "react";

import { formatDataBrt } from "@/lib/types/report";
import type { PontoSerie } from "@/lib/types/report";

import styles from "../relatorios.module.css";

interface Props {
  points: PontoSerie[];
  ariaLabel: string;
  emptyMessage?: string;
}

const CHART_HEIGHT = 180;
const PADDING_BOTTOM = 24; // espaco para labels do eixo X
const BAR_MIN_WIDTH = 8;

export function TimeSeriesChart({
  points,
  ariaLabel,
  emptyMessage = "Sem dados no periodo",
}: Props) {
  const maxValue = useMemo(() => {
    if (points.length === 0) return 0;
    return Math.max(...points.map((p) => p.quantidade), 1);
  }, [points]);

  if (points.length === 0) {
    return <div className={styles.chartEmpty}>{emptyMessage}</div>;
  }

  const usableHeight = CHART_HEIGHT - PADDING_BOTTOM;
  const barSlot = 100 / points.length; // % por barra
  const barWidth = Math.max(BAR_MIN_WIDTH, barSlot * 0.7); // 70% do slot

  // Decide quais labels exibir (max 6 para nao poluir)
  const labelStride = Math.max(1, Math.ceil(points.length / 6));

  return (
    <div className={styles.chartContainer}>
      <svg
        className={styles.timeSeriesSvg}
        viewBox={`0 0 100 ${CHART_HEIGHT}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={ariaLabel}
        style={{ height: CHART_HEIGHT }}
      >
        {/* Linha base (eixo X) */}
        <line
          x1={0}
          y1={usableHeight}
          x2={100}
          y2={usableHeight}
          stroke="rgba(0,0,0,0.08)"
          strokeWidth={0.3}
        />

        {points.map((p, index) => {
          const heightPct =
            maxValue > 0 ? (p.quantidade / maxValue) * usableHeight : 0;
          const x = barSlot * index + (barSlot - barWidth) / 2;
          const y = usableHeight - heightPct;
          return (
            <g key={`${p.data}-${index}`}>
              <motion.rect
                x={`${x}%`}
                width={`${barWidth}%`}
                fill="var(--color-accent, #ffcb5c)"
                rx={2}
                initial={{ height: 0, y: usableHeight }}
                animate={{ height: heightPct, y }}
                transition={{
                  duration: 0.35,
                  delay: index * 0.03,
                  ease: "easeOut",
                }}
              />
            </g>
          );
        })}

        {/* Labels do eixo X (texto abaixo das barras) */}
        {points.map((p, index) => {
          if (index % labelStride !== 0) return null;
          const cx = barSlot * index + barSlot / 2;
          return (
            <text
              key={`x-${p.data}-${index}`}
              x={`${cx}%`}
              y={CHART_HEIGHT - 6}
              textAnchor="middle"
              className={styles.chartAxisLabel}
            >
              {formatDataBrt(p.data)}
            </text>
          );
        })}
      </svg>

      {/* Tabela acessivel */}
      <details className={styles.chartDetails}>
        <summary>Ver dados em formato tabular</summary>
        <table className={styles.chartTable}>
          <caption className={styles.srOnly}>{ariaLabel}</caption>
          <thead>
            <tr>
              <th scope="col">Data</th>
              <th scope="col">Quantidade</th>
            </tr>
          </thead>
          <tbody>
            {points.map((p) => (
              <tr key={`tbl-${p.data}`}>
                <td>{formatDataBrt(p.data)}</td>
                <td>{p.quantidade}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}
