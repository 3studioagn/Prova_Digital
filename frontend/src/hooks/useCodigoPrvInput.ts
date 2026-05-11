"use client";

/**
 * useCodigoPrvInput — Wave 3 v4.0 / Componente 19.
 *
 * Hook React que encapsula o estado do input do fallback de digitacao
 * manual. Binding minimo sobre as funcoes puras em
 * `frontend/src/lib/codigo-publico.ts` — sem logica nova, apenas conecta
 * `aplicarMascara` ao `onChange` do `<input>` e expoe
 * `codigoCompleto`/`isComplete`/`isFormatValid` derivados.
 *
 * Decisao (D9, registrado em DECISIONS.md / ADR-141): nao temos
 * `@testing-library/react` nem `jsdom` instalados (Wave 1 v4.0 / D-13
 * minimo Vitest). Toda logica testavel vive nas funcoes puras (cobertas
 * por 43 testes Vitest); o hook em si e binding trivial validado por
 * Playwright E2E (smoke `manual_input_mask`).
 */
import { useCallback, useMemo, useState } from "react";

import {
  aplicarMascara,
  isDisplayCompleto,
  montarCodigoCompleto,
  validarFormatoCodigoPublico,
} from "@/lib/codigo-publico";

export interface UseCodigoPrvInputResult {
  /** Valor exibido no `<input>` apos mascara (formato `YYYY-MM-NNNNNN`). */
  display: string;
  /** Codigo canonico completo (`PRV-YYYY-MM-NNNNNN`) ou "" se vazio. */
  codigoCompleto: string;
  /** True quando display tem 14 chars (= codigo cheio com prefixo). */
  isComplete: boolean;
  /** True quando `codigoCompleto` casa o regex canonico. */
  isFormatValid: boolean;
  /** Handler para o `onChange` do `<input>` — aplica mascara. */
  setFromInput: (raw: string) => void;
  /** Reseta o input ao valor vazio. */
  reset: () => void;
}

export function useCodigoPrvInput(): UseCodigoPrvInputResult {
  const [display, setDisplay] = useState("");

  const setFromInput = useCallback((raw: string) => {
    setDisplay(aplicarMascara(raw));
  }, []);

  const reset = useCallback(() => {
    setDisplay("");
  }, []);

  const codigoCompleto = useMemo(() => montarCodigoCompleto(display), [display]);
  const isComplete = useMemo(() => isDisplayCompleto(display), [display]);
  const isFormatValid = useMemo(
    () => validarFormatoCodigoPublico(codigoCompleto),
    [codigoCompleto],
  );

  return {
    display,
    codigoCompleto,
    isComplete,
    isFormatValid,
    setFromInput,
    reset,
  };
}
