"use client";

/**
 * Sparkline SVG inline (Wave 5, Componente 16 — refinamento visual).
 *
 * Linha pequena de tendencia, usada em cards "destaque" (TOTAL GERAL,
 * VENDEDOR COM MAIS ARTES) para dar pulso visual sem ocupar muito espaco.
 *
 * - SVG estica horizontalmente (preserveAspectRatio="none") para preencher
 *   o card. Stroke usa `vector-effect="non-scaling-stroke"` para nao
 *   distorcer a espessura.
 * - Dot final renderizado como elemento HTML (span) por cima do SVG, com
 *   `position: absolute` em coords proporcionais — assim o circulo
 *   permanece redondo independente do aspect ratio do container, ao
 *   contrario de um <circle> SVG que ficaria oval com preserveAspectRatio=none.
 * - Fallback: se points.length < 2, retorna placeholder com mesma altura
 *   (mantem layout do card estavel — evita colapso vertical e jump de
 *   renderizacao quando `points` chega vazio antes dos dados carregarem).
 *
 * Decorativo. Nao precisa de aria-label; legendado via aria-hidden=true.
 */
import { useId, useMemo } from "react";

interface Props {
  /** Serie de valores numericos. Renderiza nada se length < 2. */
  points: number[];
  /** Cor da linha (default: --color-accent). */
  stroke?: string;
  /** Altura desejada do SVG em px. Largura usa 100%. */
  height?: number;
  /** Mostra um dot pequeno no ultimo ponto. */
  showLastDot?: boolean;
  /** Diametro do dot em px (HTML element). */
  dotSize?: number;
  /** Preenche levemente abaixo da linha com gradient. */
  showArea?: boolean;
  className?: string;
}

const VIEW_W = 200;
const VIEW_H = 60;
const STROKE_WIDTH = 2;
const PAD_TOP = 4;
const PAD_BOTTOM = 4;

export function Sparkline({
  points,
  stroke = "var(--color-accent, #ffcb5c)",
  height = 56,
  showLastDot = true,
  dotSize = 7,
  showArea = true,
  className,
}: Props) {
  const gradientId = useId();

  const { linePath, areaPath, lastPoint } = useMemo(() => {
    if (points.length < 2) {
      return { linePath: "", areaPath: "", lastPoint: null };
    }
    const min = Math.min(...points);
    const max = Math.max(...points);
    const range = max - min || 1;
    const usableH = VIEW_H - PAD_TOP - PAD_BOTTOM;
    const stepX = VIEW_W / (points.length - 1);

    const coords = points.map((value, i) => {
      const x = i * stepX;
      const y = PAD_TOP + (1 - (value - min) / range) * usableH;
      return { x, y };
    });

    const line = coords
      .map((c, i) => `${i === 0 ? "M" : "L"} ${c.x.toFixed(2)} ${c.y.toFixed(2)}`)
      .join(" ");

    const area = `${line} L ${VIEW_W} ${VIEW_H} L 0 ${VIEW_H} Z`;

    return {
      linePath: line,
      areaPath: area,
      lastPoint: coords[coords.length - 1],
    };
  }, [points]);

  if (points.length < 2) {
    // Placeholder: preserva altura do card mesmo sem dados suficientes.
    // Auditoria 2026-04-29 (L-05) — antes retornava null e gerava colapso
    // vertical do `.metricSparkline` em alguns layouts.
    return (
      <span
        className={className}
        aria-hidden="true"
        style={{
          display: "block",
          width: "100%",
          height: `${height}px`,
        }}
      />
    );
  }

  // Dot HTML posicionado proporcionalmente para nao virar oval com
  // preserveAspectRatio="none" do SVG. Como o ultimo ponto sempre tem x=VIEW_W,
  // colamos no canto direito; vertical proporcional ao y.
  const dotTopPct = lastPoint ? (lastPoint.y / VIEW_H) * 100 : 0;

  return (
    <span
      className={className}
      style={{
        position: "relative",
        display: "block",
        width: "100%",
        height: `${height}px`,
        lineHeight: 0,
      }}
    >
      <svg
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        preserveAspectRatio="none"
        width="100%"
        height={height}
        aria-hidden="true"
        style={{ display: "block", overflow: "visible" }}
      >
        {showArea && (
          <>
            <defs>
              <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor={stroke} stopOpacity="0.32" />
                <stop offset="100%" stopColor={stroke} stopOpacity="0" />
              </linearGradient>
            </defs>
            <path d={areaPath} fill={`url(#${gradientId})`} />
          </>
        )}
        <path
          d={linePath}
          fill="none"
          stroke={stroke}
          strokeWidth={STROKE_WIDTH}
          strokeLinecap="round"
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      {showLastDot && lastPoint && (
        <span
          aria-hidden="true"
          style={{
            position: "absolute",
            right: 0,
            top: `${dotTopPct}%`,
            width: `${dotSize}px`,
            height: `${dotSize}px`,
            borderRadius: "50%",
            background: stroke,
            transform: "translate(50%, -50%)",
            pointerEvents: "none",
          }}
        />
      )}
    </span>
  );
}
