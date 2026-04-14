"use client";

import { useCallback, useEffect, useRef } from "react";

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Prende o foco dentro de um container enquanto `active` for `true`.
 * Move o foco para o primeiro elemento focavel ao ativar e restaura o
 * foco anterior ao desativar.
 *
 * Retorna uma callback ref compativel com a prop `ref` de elementos JSX.
 */
export function useFocusTrap<T extends HTMLElement>(
  active: boolean,
): (node: T | null) => void {
  const containerRef = useRef<T | null>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  const callbackRef = useCallback((node: T | null) => {
    containerRef.current = node;
  }, []);

  useEffect(() => {
    if (!active || !containerRef.current) return;

    // Salva o elemento que tinha foco antes do trap
    previousFocusRef.current = document.activeElement as HTMLElement | null;

    const container = containerRef.current;

    // Move foco para o primeiro elemento focavel dentro do container
    const focusables = container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
    if (focusables.length > 0) {
      focusables[0].focus();
    }

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key !== "Tab") return;

      const elements = container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
      if (elements.length === 0) return;

      const first = elements[0];
      const last = elements[elements.length - 1];

      if (e.shiftKey) {
        // Shift+Tab: se esta no primeiro, vai pro ultimo
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        // Tab: se esta no ultimo, volta pro primeiro
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      // Restaura o foco anterior
      if (previousFocusRef.current && typeof previousFocusRef.current.focus === "function") {
        previousFocusRef.current.focus();
      }
    };
  }, [active]);

  return callbackRef;
}
