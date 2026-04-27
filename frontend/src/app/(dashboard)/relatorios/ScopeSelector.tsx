"use client";

/**
 * Tabs/segmented control com 4 perspectivas (Wave 5, Componente 16).
 *
 * Acessibilidade: usa `role="tablist"` + `role="tab"` + `aria-selected`.
 * Setas esquerda/direita movem entre tabs (WAI-ARIA Authoring Practices).
 */
import { useCallback, useRef } from "react";

import {
  REPORT_SCOPES,
  REPORT_SCOPE_LABELS,
  type ReportScope,
} from "@/lib/types/report";

import styles from "./relatorios.module.css";

interface Props {
  value: ReportScope;
  onChange: (scope: ReportScope) => void;
}

export function ScopeSelector({ value, onChange }: Props) {
  const buttonsRef = useRef<Array<HTMLButtonElement | null>>([]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLButtonElement>, currentIndex: number) => {
      if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
      event.preventDefault();
      const dir = event.key === "ArrowRight" ? 1 : -1;
      const next = (currentIndex + dir + REPORT_SCOPES.length) % REPORT_SCOPES.length;
      buttonsRef.current[next]?.focus();
      onChange(REPORT_SCOPES[next]);
    },
    [onChange],
  );

  return (
    <div className={styles.scopeSelector} role="tablist" aria-label="Perspectiva do relatorio">
      {REPORT_SCOPES.map((scope, index) => {
        const isActive = scope === value;
        return (
          <button
            key={scope}
            ref={(el) => {
              buttonsRef.current[index] = el;
            }}
            type="button"
            role="tab"
            aria-selected={isActive}
            aria-controls={`report-panel-${scope}`}
            tabIndex={isActive ? 0 : -1}
            className={isActive ? styles.scopeTabActive : styles.scopeTab}
            onClick={() => onChange(scope)}
            onKeyDown={(e) => handleKeyDown(e, index)}
          >
            {REPORT_SCOPE_LABELS[scope]}
          </button>
        );
      })}
    </div>
  );
}
