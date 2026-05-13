"use client";

/**
 * DonutChart SVG interativo (Wave 5, Componente 16).
 *
 * Renderiza um anel segmentado com:
 *   - Animacao de entrada (Framer Motion stroke-dashoffset 0 -> final).
 *   - **Hover**: segmento expande 4px + tooltip absoluto + outros ficam opacity 0.5.
 *   - **Click**: callback onSegmentClick(value) — caller decide acao
 *     (filtrar relatorio, navegar, etc).
 *   - Centro com total + label opcional.
 *   - Legenda lateral clicavel (mesma callback).
 *   - Acessibilidade: role="img" + aria-label + tabela sob <details>.
 *
 * Implementacao:
 *   - Coordenadas polares: cada segmento e um arco SVG calculado por angulo.
 *   - SVG viewBox 200x200 com circulo centro (100,100), raio externo 90, interno 60.
 *   - Sem libs externas (Recharts foi removido na Wave 4).
 */
import { motion } from "framer-motion";
import { useMemo, useState } from "react";

import styles from "../relatorios.module.css";

export interface DonutChartItem {
  label: string;
  value: number;
  /** Valor unico que sera passado em onSegmentClick (ex: status enum). */
  key: string;
  /** CSS color. Default: paleta interna. */
  color?: string;
}

interface Props {
  data: DonutChartItem[];
  ariaLabel: string;
  /** Texto exibido no centro (default: total formatado). */
  centerLabel?: string;
  /** Subtexto do centro. */
  centerHint?: string;
  /** Callback quando usuario clica num segmento ou item da legenda. */
  onSegmentClick?: (key: string) => void;
  formatValue?: (value: number) => string;
  emptyMessage?: string;
}

const VIEW_SIZE = 200;
const CENTER = VIEW_SIZE / 2;
const OUTER_RADIUS = 90;
const INNER_RADIUS = 60;
const HOVER_EXPAND = 4;

// Paleta default (4 cores complementares + fallback)
const DEFAULT_PALETTE = [
  "var(--color-accent, #ffcb5c)", // amarelo
  "#5cb8ff", // azul
  "#ff8a3d", // laranja
  "#a78bfa", // roxo
  "#34d399", // verde
  "#f87171", // vermelho
  "#fbbf24", // amarelo escuro
  "#60a5fa", // azul claro
  "#fb7185", // rosa
  "#a3a3a3", // cinza
];

function defaultFormatValue(v: number): string {
  return v.toLocaleString("pt-BR");
}

/**
 * Converte angulo (em radianos) + raio para coordenadas SVG.
 * Angulo 0 = topo (12h); cresce no sentido horario.
 */
function polarToCartesian(
  centerX: number,
  centerY: number,
  radius: number,
  angleRad: number,
): { x: number; y: number } {
  return {
    x: centerX + radius * Math.sin(angleRad),
    y: centerY - radius * Math.cos(angleRad),
  };
}

/**
 * Constroi o `d` de um arco SVG entre dois angulos (radianos).
 * arco do raio externo (clockwise), linha radial inner, arco interno (counter-clockwise),
 * fechamento.
 *
 * Caso especial 100% (arco completo, 2π):
 *   startOuter e endOuter coincidem (mesmo ponto no topo); SVG nao renderiza
 *   um arco circular completo num unico <path> — fica visualmente vazio. Para
 *   evitar o donut "sumir" quando ha apenas 1 segmento (ex: apos clicar num
 *   status do donut e filtrar a vista), aplicamos um epsilon minusculo no
 *   endAngle. Diferenca visual: ~0.09px num viewport de 200x200, imperceptivel.
 *   Audit 2026-04-29.
 */
const FULL_CIRCLE_EPSILON = 1e-3;

function buildArcPath(
  startAngle: number,
  endAngle: number,
  outerRadius: number,
  innerRadius: number,
): string {
  const isFullCircle = endAngle - startAngle >= Math.PI * 2 - 1e-6;
  const adjustedEnd = isFullCircle ? endAngle - FULL_CIRCLE_EPSILON : endAngle;

  const startOuter = polarToCartesian(CENTER, CENTER, outerRadius, startAngle);
  const endOuter = polarToCartesian(CENTER, CENTER, outerRadius, adjustedEnd);
  const startInner = polarToCartesian(CENTER, CENTER, innerRadius, adjustedEnd);
  const endInner = polarToCartesian(CENTER, CENTER, innerRadius, startAngle);
  const largeArc = adjustedEnd - startAngle > Math.PI ? 1 : 0;

  return [
    `M ${startOuter.x} ${startOuter.y}`,
    `A ${outerRadius} ${outerRadius} 0 ${largeArc} 1 ${endOuter.x} ${endOuter.y}`,
    `L ${startInner.x} ${startInner.y}`,
    `A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${endInner.x} ${endInner.y}`,
    "Z",
  ].join(" ");
}

interface ComputedSegment {
  item: DonutChartItem;
  startAngle: number;
  endAngle: number;
  pathNormal: string;
  pathExpanded: string;
  color: string;
  pct: number;
}

export function DonutChart({
  data,
  ariaLabel,
  centerLabel,
  centerHint,
  onSegmentClick,
  formatValue = defaultFormatValue,
  emptyMessage = "Sem dados para exibir",
}: Props) {
  const [hoveredKey, setHoveredKey] = useState<string | null>(null);
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number } | null>(
    null,
  );

  const total = useMemo(
    () => data.reduce((acc, d) => acc + d.value, 0),
    [data],
  );

  const segments = useMemo<ComputedSegment[]>(() => {
    if (total === 0) return [];
    let acc = 0;
    return data
      .filter((d) => d.value > 0)
      .map((item, idx) => {
        const pct = item.value / total;
        const startAngle = (acc / total) * 2 * Math.PI;
        const endAngle = ((acc + item.value) / total) * 2 * Math.PI;
        acc += item.value;
        const color =
          item.color ?? DEFAULT_PALETTE[idx % DEFAULT_PALETTE.length];
        return {
          item,
          startAngle,
          endAngle,
          pathNormal: buildArcPath(
            startAngle,
            endAngle,
            OUTER_RADIUS,
            INNER_RADIUS,
          ),
          pathExpanded: buildArcPath(
            startAngle,
            endAngle,
            OUTER_RADIUS + HOVER_EXPAND,
            INNER_RADIUS,
          ),
          color,
          pct,
        };
      });
  }, [data, total]);

  if (segments.length === 0) {
    return <div className={styles.chartEmpty}>{emptyMessage}</div>;
  }

  const handleMouseMove = (event: React.MouseEvent) => {
    const rect = (
      event.currentTarget as HTMLElement
    ).getBoundingClientRect();
    setTooltipPos({
      x: event.clientX - rect.left + 12,
      y: event.clientY - rect.top + 12,
    });
  };

  const hoveredSegment = segments.find((s) => s.item.key === hoveredKey);
  const interactive = onSegmentClick !== undefined;

  return (
    <div
      className={styles.donutContainer}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => {
        setHoveredKey(null);
        setTooltipPos(null);
      }}
    >
      <svg
        className={styles.donutSvg}
        viewBox={`0 0 ${VIEW_SIZE} ${VIEW_SIZE}`}
        role="img"
        aria-label={ariaLabel}
      >
        {segments.map((seg, idx) => {
          const isHovered = seg.item.key === hoveredKey;
          const isOtherHovered = hoveredKey !== null && !isHovered;
          return (
            <motion.path
              key={seg.item.key}
              d={isHovered ? seg.pathExpanded : seg.pathNormal}
              fill={seg.color}
              opacity={isOtherHovered ? 0.4 : 1}
              initial={{ opacity: 0, scale: 0.85 }}
              animate={{
                opacity: isOtherHovered ? 0.4 : 1,
                scale: 1,
              }}
              transition={{
                duration: 0.4,
                delay: idx * 0.05,
                ease: "easeOut",
              }}
              style={{
                cursor: interactive ? "pointer" : "default",
                transformOrigin: `${CENTER}px ${CENTER}px`,
                transition: "d 0.15s ease, opacity 0.15s ease",
              }}
              onMouseEnter={() => setHoveredKey(seg.item.key)}
              onClick={() => {
                if (interactive) {
                  onSegmentClick(seg.item.key);
                }
              }}
            />
          );
        })}

        {/* Centro: total + label */}
        <text
          x={CENTER}
          y={CENTER - 6}
          textAnchor="middle"
          dominantBaseline="middle"
          className={styles.donutCenterValue}
        >
          {centerLabel ?? formatValue(total)}
        </text>
        {centerHint && (
          <text
            x={CENTER}
            y={CENTER + 14}
            textAnchor="middle"
            dominantBaseline="middle"
            className={styles.donutCenterHint}
          >
            {centerHint}
          </text>
        )}
      </svg>

      {/* Legenda lateral — dot + label + valor numerico (match design Mario) */}
      <ul className={styles.donutLegend}>
        {segments.map((seg) => {
          const isHovered = seg.item.key === hoveredKey;
          return (
            <li key={`legend-${seg.item.key}`}>
              <button
                type="button"
                className={
                  isHovered ? styles.donutLegendItemActive : styles.donutLegendItem
                }
                onMouseEnter={() => setHoveredKey(seg.item.key)}
                onMouseLeave={() => setHoveredKey(null)}
                onClick={() => {
                  if (interactive) onSegmentClick(seg.item.key);
                }}
                disabled={!interactive}
                aria-label={`${seg.item.label}: ${formatValue(seg.item.value)}`}
              >
                <span
                  className={styles.donutLegendDot}
                  style={{ background: seg.color }}
                  aria-hidden="true"
                />
                <span className={styles.donutLegendLabel}>{seg.item.label}</span>
                <span className={styles.donutLegendValue}>
                  {formatValue(seg.item.value)}
                </span>
              </button>
            </li>
          );
        })}
      </ul>

      {/* Tooltip flutuante */}
      {hoveredSegment && tooltipPos && (
        <div
          className={styles.chartTooltip}
          style={{
            left: tooltipPos.x,
            top: tooltipPos.y,
          }}
          role="tooltip"
        >
          <div className={styles.chartTooltipLabel}>{hoveredSegment.item.label}</div>
          <div className={styles.chartTooltipValue}>
            {formatValue(hoveredSegment.item.value)} ·{" "}
            {(hoveredSegment.pct * 100).toFixed(1)}%
          </div>
        </div>
      )}

      {/* Tabela acessivel — permanente sr-only (Wave 5 v4.0 / D7→Opcao (iii)).
       *
       * Leitor de tela acessa imediatamente sem precisar interagir com o
       * <details>. Layout v3 visualmente preservado (zero pixels novos).
       *
       * O <details> abaixo permanece como toggle visivel ao usuario vidente
       * (estado v3); seu conteudo interno e marcado `aria-hidden="true"`
       * para evitar duplicacao na leitura por AT (NVDA/JAWS/VoiceOver). */}
      <table className={styles.srOnly} aria-label={ariaLabel}>
        <caption>{ariaLabel}</caption>
        <thead>
          <tr>
            <th scope="col">Categoria</th>
            <th scope="col">Quantidade</th>
            <th scope="col">Percentual</th>
          </tr>
        </thead>
        <tbody>
          {segments.map((seg) => (
            <tr key={`sr-${seg.item.key}`}>
              <td>{seg.item.label}</td>
              <td>{formatValue(seg.item.value)}</td>
              <td>{(seg.pct * 100).toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Tabela visivel sob <details> — preservada da v3 para usuario
       * vidente que queira inspecionar valores exatos sem hover. Marcada
       * aria-hidden="true" para nao duplicar com a tabela sr-only acima. */}
      <details className={styles.chartDetails} aria-hidden="true">
        <summary>Ver dados em formato tabular</summary>
        <table className={styles.chartTable}>
          <thead>
            <tr>
              <th scope="col">Categoria</th>
              <th scope="col">Quantidade</th>
              <th scope="col">%</th>
            </tr>
          </thead>
          <tbody>
            {segments.map((seg) => (
              <tr key={`tbl-${seg.item.key}`}>
                <td>{seg.item.label}</td>
                <td>{formatValue(seg.item.value)}</td>
                <td>{(seg.pct * 100).toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}
