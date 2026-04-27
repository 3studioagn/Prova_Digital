"use client";

/**
 * Campo de busca textual (Wave 5, Componente 16).
 *
 * Debounce 300ms (padrao do projeto na listagem de provas — Wave 2).
 * Backend faz ILIKE em nome/cliente/nro_requerimento (admin-only).
 */
import { useCallback, useEffect, useRef, useState } from "react";

import { REPORT_MAX_Q_LENGTH } from "@/lib/types/report";

import styles from "./relatorios.module.css";

interface Props {
  value: string | null;
  onChange: (value: string | null) => void;
  /** ms — default 300. */
  debounceMs?: number;
}

export function SearchInput({ value, onChange, debounceMs = 300 }: Props) {
  // Estado local para refletir digitacao instantanea — sincronizado com `value`
  // quando externo (URL) muda.
  const [local, setLocal] = useState<string>(value ?? "");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setLocal(value ?? "");
  }, [value]);

  const handleChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const next = event.target.value;
      setLocal(next);

      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        const trimmed = next.trim();
        onChange(trimmed === "" ? null : trimmed);
      }, debounceMs);
    },
    [onChange, debounceMs],
  );

  // Cleanup no unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  return (
    <input
      type="search"
      className={styles.searchInput}
      placeholder="Buscar por nome, cliente ou nº requerimento"
      value={local}
      onChange={handleChange}
      maxLength={REPORT_MAX_Q_LENGTH}
      aria-label="Busca textual nos relatorios"
    />
  );
}
