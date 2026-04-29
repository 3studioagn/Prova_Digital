"use client";

/**
 * Filtro de vendedor (Wave 5, Componente 16 — auditoria H-01 / RF-013).
 *
 * `<select>` nativo populado via GET /api/v1/users?setor=VENDEDOR&ativo=true.
 * Backend ja exige admin; reusa apiFetch + token Supabase (padrao do projeto).
 *
 * Decisoes:
 *  - page_size=100: volume operacional da 3Studio cabe em 1 pagina.
 *  - Hook local (nao em src/hooks/) — uso unico, principio do
 *    "extract only when reused" do projeto. Se aparecer um segundo
 *    consumidor, promover.
 *  - Se fetch falhar, select fica desabilitado com placeholder de erro
 *    sem quebrar o resto da filtersBar.
 */
import { useEffect, useId, useState } from "react";

import { apiFetch } from "@/lib/api";
import type { UsuarioListResponse, UsuarioResponse } from "@/lib/types/usuario";

import styles from "./relatorios.module.css";

interface Props {
  value: string | null;
  onChange: (vendedor_id: string | null) => void;
  getToken: () => Promise<string | null>;
}

interface VendedorOption {
  id: string;
  nome: string;
}

interface FetchState {
  options: VendedorOption[];
  loading: boolean;
  error: string | null;
}

const INITIAL: FetchState = { options: [], loading: true, error: null };

export function VendedorFilter({ value, onChange, getToken }: Props) {
  const id = useId();
  const [state, setState] = useState<FetchState>(INITIAL);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      let token: string | null;
      try {
        token = await getToken();
      } catch {
        token = null;
      }
      if (!token) {
        if (!cancelled)
          setState({ options: [], loading: false, error: "Sem sessao" });
        return;
      }
      try {
        const res = await apiFetch<UsuarioListResponse>(
          "/api/v1/users/?setor=VENDEDOR&ativo=true&page_size=100&page=1",
          { token },
        );
        if (cancelled) return;
        const opts: VendedorOption[] = res.items
          .map((u: UsuarioResponse) => ({ id: u.id, nome: u.nome }))
          .sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
        setState({ options: opts, loading: false, error: null });
      } catch {
        if (!cancelled)
          setState({
            options: [],
            loading: false,
            error: "Falha ao carregar vendedores",
          });
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [getToken]);

  const placeholder = state.loading
    ? "Carregando..."
    : state.error
      ? state.error
      : "Todos";

  return (
    <label className={styles.selectFilterPill} htmlFor={id}>
      <span className={styles.selectFilterPrefix}>Vendedor</span>
      <select
        id={id}
        className={styles.selectFilterInput}
        value={value ?? ""}
        onChange={(e) => {
          const v = e.target.value;
          onChange(v === "" ? null : v);
        }}
        disabled={state.loading || state.error !== null}
        aria-label="Filtrar por vendedor"
      >
        <option value="">{placeholder}</option>
        {state.options.map((v) => (
          <option key={v.id} value={v.id}>
            {v.nome}
          </option>
        ))}
      </select>
      <svg
        width="12"
        height="12"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        className={styles.selectFilterChevron}
      >
        <polyline points="6 9 12 15 18 9" />
      </svg>
    </label>
  );
}
