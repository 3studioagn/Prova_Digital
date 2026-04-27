"use client";

/**
 * BarChart SVG inline animado e interativo (Wave 5, Componente 16).
 *
 * Bar chart horizontal com:
 *   - Animacao de entrada (Framer Motion) — width 0 → final, stagger 40ms.
 *   - Hover: barra realca (outras opacity 0.5) + tooltip flutuante.
 *   - Click opcional via `onItemClick(key)` — caller decide acao.
 *   - Acessibilidade: role="img" + aria-label + tabela de dados sob <details>.
 *
 * Sem dependencia externa de chart lib (Recharts foi removido na Wave 4).
 */
import { motion } from "framer-motion";
import { useMemo, useState } from "react";

import styles from "../relatorios.module.css";

export interface BarChartItem {
  label: string;
  value: number;
  /** CSS color. Default: --color-accent. */
  color?: string;
  /** Identificador opcional passado em onItemClick. Default: label. */
  key?: string;
}

interface Props {
  data: BarChartItem[];
  ariaLabel: string;
  /** Callback ao clicar numa barra. Caller decide a acao. */
  onItemClick?: (key: string) => void;
  /** Formatador opcional do valor exibido na barra. Default: toLocaleString. */
  formatValue?: (value: number) => string;
  /** Texto exibido quando data esta vazio. */
  emptyMessage?: string;
}

const DEFAULT_COLOR = "var(--color-accent, #ffcb5c)";
const BAR_HEIGHT = 32;
const BAR_GAP = 8;
const LABEL_WIDTH = 120;
const VALUE_PADDING = 8;

function defaultFormatValue(v: number): string {
  return v.toLocaleString("pt-BR");
}

export function BarChart({
  data,
  ariaLabel,
  onItemClick,
  formatValue = defaultFormatValue,
  emptyMessage = "Sem dados para exibir",
}: Props) {
  const [hoveredKey, setHoveredKey] = useState<string | null>(null);
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number } | null>(
    null,
  );

  const maxValue = useMemo(() => {
    if (data.length === 0) return 0;
    return Math.max(...data.map((d) => d.value), 1);
  }, [data]);

  if (data.length === 0) {
    return <div className={styles.chartEmpty}>{emptyMessage}</div>;
  }

  const totalHeight = data.length * (BAR_HEIGHT + BAR_GAP);
  const interactive = onItemClick !== undefined;

  const handleMouseMove = (event: React.MouseEvent) => {
    const rect = (
      event.currentTarget as HTMLElement
    ).getBoundingClientRect();
    setTooltipPos({
      x: event.clientX - rect.left + 12,
      y: event.clientY - rect.top + 12,
    });
  };

  const hoveredItem = data.find(
    (item) => (item.key ?? item.label) === hoveredKey,
  );

  return (
    <div
      className={styles.chartContainer}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => {
        setHoveredKey(null);
        setTooltipPos(null);
      }}
    >
      <svg
        className={styles.barChartSvg}
        viewBox={`0 0 100 ${totalHeight}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={ariaLabel}
        style={{ height: totalHeight }}
      >
        {data.map((item, index) => {
          const widthPct = (item.value / maxValue) * 100;
          const y = index * (BAR_HEIGHT + BAR_GAP);
          const itemKey = item.key ?? item.label;
          const isHovered = itemKey === hoveredKey;
          const isOtherHovered = hoveredKey !== null && !isHovered;
          return (
            <motion.rect
              key={`${itemKey}-${index}`}
              x={0}
              y={y}
              height={BAR_HEIGHT}
              fill={item.color ?? DEFAULT_COLOR}
              rx={6}
              initial={{ width: 0, opacity: 0 }}
              animate={{
                width: `${widthPct}%`,
                opacity: isOtherHovered ? 0.4 : 1,
              }}
              transition={{
                width: {
                  duration: 0.4,
                  delay: index * 0.04,
                  ease: "easeOut",
                },
                opacity: { duration: 0.15 },
              }}
              style={{
                cursor: interactive ? "pointer" : "default",
              }}
              onMouseEnter={() => setHoveredKey(itemKey)}
              onClick={() => {
                if (interactive) onItemClick(itemKey);
              }}
            />
          );
        })}
      </svg>

      {/* Labels + valores absolutos como overlay (em cima do SVG) */}
      <div
        className={styles.barChartLabels}
        style={{ height: totalHeight }}
        aria-hidden="true"
      >
        {data.map((item, index) => (
          <div
            key={`${item.key ?? item.label}-label-${index}`}
            className={styles.barChartRow}
            style={{ height: BAR_HEIGHT, marginBottom: BAR_GAP }}
          >
            <span
              className={styles.barChartLabel}
              style={{ width: LABEL_WIDTH, paddingLeft: VALUE_PADDING }}
            >
              {item.label}
            </span>
            <span className={styles.barChartValue}>
              {formatValue(item.value)}
            </span>
          </div>
        ))}
      </div>

      {/* Tooltip flutuante */}
      {hoveredItem && tooltipPos && (
        <div
          className={styles.chartTooltip}
          style={{
            left: tooltipPos.x,
            top: tooltipPos.y,
          }}
          role="tooltip"
        >
          <div className={styles.chartTooltipLabel}>{hoveredItem.label}</div>
          <div className={styles.chartTooltipValue}>
            {formatValue(hoveredItem.value)}
          </div>
        </div>
      )}

      {/* Tabela de dados acessivel */}
      <details className={styles.chartDetails}>
        <summary>Ver dados em formato tabular</summary>
        <table className={styles.chartTable}>
          <caption className={styles.srOnly}>{ariaLabel}</caption>
          <thead>
            <tr>
              <th scope="col">Categoria</th>
              <th scope="col">Quantidade</th>
            </tr>
          </thead>
          <tbody>
            {data.map((item, index) => (
              <tr key={`tbl-${item.key ?? item.label}-${index}`}>
                <td>{item.label}</td>
                <td>{formatValue(item.value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}
