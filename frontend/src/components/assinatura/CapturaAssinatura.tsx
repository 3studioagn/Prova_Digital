"use client";

/**
 * CapturaAssinatura — Wave 8 v5.0 / Componente 22.
 *
 * Wrapper do `react-signature-canvas` (Decisao D2 — mecanismo original
 * recuperado pela arqueologia; pacote `^1.0.7` ja instalado). Encapsula:
 *   - o canvas de tracado (dedo/mouse);
 *   - o dimensionamento responsivo via `ResizeObserver` (mobile-ready —
 *     o `<canvas>` precisa de `width` em px explicito);
 *   - o botao "Limpar".
 *
 * Expoe via `ref` (imperativo) `{ isEmpty, toBase64, clear }` para o
 * `AssinaturaModal` validar e capturar a assinatura no submit.
 */
import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import type SignatureCanvas from "react-signature-canvas";
import SigCanvas from "react-signature-canvas";
import styles from "./assinatura.module.css";

export interface CapturaAssinaturaHandle {
  /** True se nenhum traco foi desenhado (ou o canvas ainda nao montou). */
  isEmpty: () => boolean;
  /** PNG base64 SEM o prefixo `data:image/png;base64,` — formato esperado
   *  pelo backend em `assinatura_base64`. String vazia se nao montou. */
  toBase64: () => string;
  /** Apaga o tracado do canvas. */
  clear: () => void;
}

interface CapturaAssinaturaProps {
  /** Desabilita o botao "Limpar" durante o envio. */
  disabled?: boolean;
}

export const CapturaAssinatura = forwardRef<
  CapturaAssinaturaHandle,
  CapturaAssinaturaProps
>(function CapturaAssinatura({ disabled = false }, ref) {
  const sigRef = useRef<SignatureCanvas | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [canvasWidth, setCanvasWidth] = useState(0);

  // Dimensiona o canvas pela largura real do container. ResizeObserver
  // cobre rotacao de tela / mudanca de viewport — base da prontidao
  // mobile do C22 (o polimento fino e o C23). O `<canvas>` so renderiza
  // depois de `canvasWidth > 0`, o que tambem evita problema de SSR
  // (o efeito so roda no cliente).
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () => {
      const w = el.clientWidth;
      if (w > 0) setCanvasWidth(w);
    };
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useImperativeHandle(
    ref,
    () => ({
      isEmpty: () => sigRef.current?.isEmpty() ?? true,
      toBase64: () => {
        const canvas = sigRef.current?.getCanvas();
        if (!canvas) return "";
        return canvas.toDataURL("image/png").split(",")[1] ?? "";
      },
      clear: () => sigRef.current?.clear(),
    }),
    [],
  );

  return (
    <div className={styles.capturaWrapper}>
      <div ref={containerRef} className={styles.capturaCanvasSlot}>
        {canvasWidth > 0 && (
          <SigCanvas
            ref={sigRef}
            penColor="#000000"
            backgroundColor="#ffffff"
            canvasProps={{
              className: styles.capturaCanvas,
              width: canvasWidth,
              height: 200,
            }}
          />
        )}
      </div>
      <div className={styles.capturaActions}>
        <span className={styles.capturaHint}>
          Assine com o dedo ou o mouse no quadro acima.
        </span>
        <button
          type="button"
          className={styles.capturaLimpar}
          onClick={() => sigRef.current?.clear()}
          disabled={disabled}
        >
          Limpar
        </button>
      </div>
    </div>
  );
});
