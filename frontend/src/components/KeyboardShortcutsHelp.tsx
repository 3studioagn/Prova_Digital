"use client";

/**
 * Modal com lista de atalhos de teclado (Wave 5, Componente 17).
 *
 * Exibe a lista filtrada por permissao (vendedor/motorista/clicheria nao
 * veem `g r` — esse filtro acontece no `useGlobalShortcuts`).
 *
 * Acessibilidade:
 *   - role="dialog" + aria-modal="true" + aria-labelledby
 *   - Focus trap (reusa `useFocusTrap` da Wave 3)
 *   - Esc fecha — handled by useGlobalShortcuts (handler unico,
 *     auditoria 2026-04-29 / L-04 — eliminacao de listener duplicado)
 */
import { useEffect } from "react";

import { useFocusTrap } from "@/hooks/useFocusTrap";
import type { ShortcutDef } from "@/hooks/useGlobalShortcuts";

import styles from "./KeyboardShortcutsHelp.module.css";

interface Props {
  open: boolean;
  onClose: () => void;
  shortcuts: ShortcutDef[];
}

export function KeyboardShortcutsHelp({ open, onClose, shortcuts }: Props) {
  const trapRef = useFocusTrap<HTMLDivElement>(open);

  // Lock scroll do body quando modal aberto
  useEffect(() => {
    if (!open) return;
    const original = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = original;
    };
  }, [open]);

  if (!open) return null;

  return (
    <div
      className={styles.overlay}
      onClick={onClose}
    >
      {/*
        IMPORTANTE: o overlay NAO pode ter `aria-hidden="true"` — esconderia
        o dialog (descendente) do leitor de tela. WAI-ARIA modal pattern: o
        proprio dialog usa `role="dialog"` + `aria-modal="true"` para
        comunicar o estado modal. Audit 2026-04-29 M-F1.
      */}
      <div
        className={styles.dialog}
        ref={trapRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="shortcuts-help-title"
        onClick={(e) => e.stopPropagation()}
      >
        <header className={styles.header}>
          <h2 id="shortcuts-help-title" className={styles.title}>
            Atalhos de teclado
          </h2>
          <button
            type="button"
            className={styles.closeButton}
            onClick={onClose}
            aria-label="Fechar atalhos de teclado"
          >
            ×
          </button>
        </header>

        <div className={styles.content}>
          <p className={styles.intro}>
            Pressione{" "}
            <kbd className={styles.kbd}>g</kbd> seguido de outra tecla para
            navegar:
          </p>
          <ul className={styles.shortcutList}>
            {shortcuts.map((s) => (
              <li key={s.key} className={styles.shortcutItem}>
                <span className={styles.shortcutKeys}>
                  <kbd className={styles.kbd}>g</kbd>
                  <span className={styles.shortcutThen}>depois</span>
                  <kbd className={styles.kbd}>{s.key}</kbd>
                </span>
                <span className={styles.shortcutLabel}>{s.label}</span>
              </li>
            ))}
            <li className={styles.shortcutItem}>
              <span className={styles.shortcutKeys}>
                <kbd className={styles.kbd}>?</kbd>
              </span>
              <span className={styles.shortcutLabel}>
                Mostrar/ocultar este painel
              </span>
            </li>
            <li className={styles.shortcutItem}>
              <span className={styles.shortcutKeys}>
                <kbd className={styles.kbd}>Esc</kbd>
              </span>
              <span className={styles.shortcutLabel}>
                Fechar este painel ou cancelar atalho
              </span>
            </li>
          </ul>

          <p className={styles.hint}>
            Atalhos sao desativados quando voce esta digitando em campos de
            texto.
          </p>
        </div>
      </div>
    </div>
  );
}
