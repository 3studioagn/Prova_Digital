"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import { useListProvas, type ListProvasFilters } from "@/hooks/useListProvas";
// A4 (auditoria Wave 2 — Sessao 19): `loadDebounced` foi removido do hook
// porque a pagina ja faz debounce local via setTimeout em handleBuscaChange
// e handleClienteChange. A destructuring abaixo inclui apenas `load`.
import {
  ROTA_LABELS,
  ROTA_OPTIONS,
  STATUS_LABELS,
  STATUS_LABELS_SHORT,
  STATUS_OPTIONS,
  type Rota,
  type StatusProva,
} from "@/lib/types/prova";
import type {
  MeResponse,
  UsuarioListResponse,
  UsuarioResponse,
} from "@/lib/types/usuario";
import { useAuthorization } from "@/lib/hooks/use-authorization";
import styles from "./provas.module.css";

// C07 B1 (auditoria externa Wave 2): `MeResponse` extraido para
// `lib/types/usuario.ts` como fonte unica de verdade.

const DEFAULT_PAGE_SIZE = 20;

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

function ProvasPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Fonte UNICA de truth para o access token nesta pagina. `useListProvas`
  // e o fetchMe useEffect (abaixo) consomem esse mesmo callback — evita
  // duas chamadas independentes a `getSession()` em paralelo na mesma
  // pagina (mesmo padrao do fix A5 do Componente 06, Sessao 18).
  const getToken = useCallback(async () => {
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  }, []);

  const { loading, error, data, load } = useListProvas(getToken);

  // ── Estado local dos filtros (sincronizado com URL) ─────────────────
  const [me, setMe] = useState<MeResponse | null>(null);
  const [vendedores, setVendedores] = useState<UsuarioResponse[]>([]);

  // Extrai filtros da URL. Essa funcao e usada tanto no mount quanto
  // em cada mudanca de searchParams (back/forward do browser).
  const urlFilters: ListProvasFilters = useMemo(() => {
    const page = Number(searchParams.get("page") ?? "1") || 1;
    const page_size =
      Number(searchParams.get("page_size") ?? String(DEFAULT_PAGE_SIZE)) ||
      DEFAULT_PAGE_SIZE;
    const status = (searchParams.get("status") as StatusProva | null) || null;
    const rota = (searchParams.get("rota") as Rota | null) || null;
    return {
      page,
      page_size,
      status,
      periodo_inicio: searchParams.get("periodo_inicio"),
      periodo_fim: searchParams.get("periodo_fim"),
      vendedor_id: searchParams.get("vendedor_id"),
      cliente: searchParams.get("cliente"),
      rota,
      busca: searchParams.get("busca"),
    };
  }, [searchParams]);

  // Inputs controlados locais — separados do urlFilters para permitir
  // digitacao fluida (sem escrever na URL a cada tecla).
  const [buscaInput, setBuscaInput] = useState(urlFilters.busca ?? "");
  const [clienteInput, setClienteInput] = useState(urlFilters.cliente ?? "");

  // Sincroniza inputs locais quando a URL muda externamente
  // (ex: botao back do browser, Limpar filtros).
  useEffect(() => {
    setBuscaInput(urlFilters.busca ?? "");
    setClienteInput(urlFilters.cliente ?? "");
  }, [urlFilters.busca, urlFilters.cliente]);

  // A1 (auditoria Wave 2 — Sessao 19): fetchMe usa `getToken` em vez de
  // chamar `getSession()` direto. Unifica a fonte de truth do access token
  // na pagina (mesmo padrao do fix A5 do C06, Sessao 18).
  useEffect(() => {
    const controller = new AbortController();
    async function fetchMe() {
      const token = await getToken();
      if (!token || controller.signal.aborted) return;
      try {
        const meData = await apiFetch<MeResponse>("/api/v1/users/me", {
          token,
          signal: controller.signal,
        });
        if (!controller.signal.aborted) setMe(meData);

        // Admin tem acesso ao filtro de vendedor — carrega opcoes.
        if (meData.is_admin && !controller.signal.aborted) {
          try {
            const vs = await apiFetch<UsuarioListResponse>(
              "/api/v1/users/?setor=VENDEDOR&ativo=true&page_size=100",
              { token, signal: controller.signal },
            );
            if (!controller.signal.aborted) setVendedores(vs.items);
          } catch {
            // silent — filtro fica sem opcoes
          }
        }
      } catch {
        // silent
      }
    }
    fetchMe();
    return () => controller.abort();
  }, [getToken]);

  // Dispara load sempre que a URL muda.
  //
  // M1 (auditoria Wave 2 — Sessao 19): `isFirstRenderRef` foi removido
  // — era setado no primeiro render mas nunca lido depois, dead state.
  useEffect(() => {
    load(urlFilters);
  }, [urlFilters, load]);

  // ── Helpers para atualizar a URL ─────────────────────────────────────
  const updateUrl = useCallback(
    (patch: Partial<Record<string, string | null>>) => {
      const next = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(patch)) {
        if (value === null || value === "" || value === undefined) {
          next.delete(key);
        } else {
          next.set(key, value);
        }
      }
      // Reset de pagina quando qualquer filtro muda (exceto o proprio page).
      if (!("page" in patch)) {
        next.delete("page");
      }
      router.replace(`/provas?${next.toString()}`);
    },
    [router, searchParams],
  );

  // Handlers imediatos (selects, dates)
  const handleStatusChange = (v: string) =>
    updateUrl({ status: v || null });
  const handleRotaChange = (v: string) => updateUrl({ rota: v || null });
  const handleVendedorChange = (v: string) =>
    updateUrl({ vendedor_id: v || null });
  const handlePeriodoInicioChange = (v: string) =>
    updateUrl({ periodo_inicio: v || null });
  const handlePeriodoFimChange = (v: string) =>
    updateUrl({ periodo_fim: v || null });

  // Handlers com debounce (texto)
  // Ao digitar, atualizamos o input imediatamente mas damos o reload
  // debounced contra o hook. Ao "pausar" por 300ms, a URL tambem e
  // atualizada (via updateUrl dentro de um setTimeout).
  const buscaTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const clienteTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleBuscaChange = (v: string) => {
    setBuscaInput(v);
    if (buscaTimerRef.current) clearTimeout(buscaTimerRef.current);
    buscaTimerRef.current = setTimeout(() => {
      updateUrl({ busca: v || null });
    }, 350);
  };

  const handleClienteChange = (v: string) => {
    setClienteInput(v);
    if (clienteTimerRef.current) clearTimeout(clienteTimerRef.current);
    clienteTimerRef.current = setTimeout(() => {
      updateUrl({ cliente: v || null });
    }, 350);
  };

  // Cleanup dos timers no unmount
  useEffect(() => {
    return () => {
      if (buscaTimerRef.current) clearTimeout(buscaTimerRef.current);
      if (clienteTimerRef.current) clearTimeout(clienteTimerRef.current);
    };
  }, []);

  const handleLimparFiltros = () => {
    setBuscaInput("");
    setClienteInput("");
    router.replace("/provas");
  };

  const handlePage = (newPage: number) => {
    updateUrl({ page: String(newPage) });
  };

  // ── Render ──────────────────────────────────────────────────────────
  const temFiltrosAtivos =
    !!urlFilters.status ||
    !!urlFilters.rota ||
    !!urlFilters.vendedor_id ||
    !!urlFilters.periodo_inicio ||
    !!urlFilters.periodo_fim ||
    !!urlFilters.cliente ||
    !!urlFilters.busca;

  // Wave 1 v4.0: filtro de vendedor so para perfis com acesso 'full' a
  // /provas (admin). Vendedor/motorista/clicheria sao 'parcial' e ja veem
  // apenas o subconjunto definido pela Matriz — filtrar por vendedor_id
  // alheio nao faz sentido para eles.
  const provasListAuth = useAuthorization("provas.list");
  const showVendedorFilter = provasListAuth.level === "full";

  return (
    <>
      <div className={styles.mobileNotice}>
        <p>Para acessar esse recurso, acesse a versao desktop.</p>
      </div>
      <div className={styles.desktopOnly}>
        <header className={styles.pageHeader}>
          <h1 className={styles.title}>Provas digitais</h1>
        </header>

        {/* ── Filtros (4x2 — bate com Figma) ─────────────────────── */}
        <section className={styles.filters} aria-label="Filtros">
          <div className={styles.filterRow}>
            <div className={styles.field}>
              <label htmlFor="filtro_busca" className={styles.label}>
                Buscar nome ou requerimento:
              </label>
              <input
                id="filtro_busca"
                type="search"
                className={styles.input}
                placeholder="123456"
                value={buscaInput}
                onChange={(e) => handleBuscaChange(e.target.value)}
              />
            </div>

            <div className={styles.field}>
              <label htmlFor="filtro_cliente" className={styles.label}>
                Cliente:
              </label>
              <input
                id="filtro_cliente"
                type="search"
                className={styles.input}
                placeholder="Nome do cliente"
                value={clienteInput}
                onChange={(e) => handleClienteChange(e.target.value)}
              />
            </div>

            <div className={styles.field}>
              <label htmlFor="filtro_status" className={styles.label}>
                Status:
              </label>
              <select
                id="filtro_status"
                className={styles.select}
                value={urlFilters.status ?? ""}
                onChange={(e) => handleStatusChange(e.target.value)}
              >
                <option value="">Todos</option>
                {STATUS_OPTIONS.map((s) => (
                  <option key={s} value={s}>
                    {STATUS_LABELS[s]}
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.field}>
              <label htmlFor="filtro_rota" className={styles.label}>
                Rota:
              </label>
              <select
                id="filtro_rota"
                className={styles.select}
                value={urlFilters.rota ?? ""}
                onChange={(e) => handleRotaChange(e.target.value)}
              >
                <option value="">Todos</option>
                {ROTA_OPTIONS.map((r) => (
                  <option key={r} value={r}>
                    {ROTA_LABELS[r]}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className={styles.filterRow}>
            <div className={styles.field}>
              <label htmlFor="filtro_vendedor" className={styles.label}>
                Vendedor:
              </label>
              <select
                id="filtro_vendedor"
                className={styles.select}
                value={urlFilters.vendedor_id ?? ""}
                onChange={(e) => handleVendedorChange(e.target.value)}
                disabled={!showVendedorFilter}
                aria-disabled={!showVendedorFilter}
              >
                <option value="">Todos</option>
                {vendedores.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.nome}
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.field}>
              <label htmlFor="filtro_inicio" className={styles.label}>
                Criada a partir de:
              </label>
              <input
                id="filtro_inicio"
                type="date"
                className={styles.input}
                placeholder="dd/mm/aaaa"
                value={urlFilters.periodo_inicio ?? ""}
                onChange={(e) => handlePeriodoInicioChange(e.target.value)}
              />
            </div>

            <div className={styles.field}>
              <label htmlFor="filtro_fim" className={styles.label}>
                {/* F10 (auditoria externa Wave 2): antes "Finalizada em",
                    que era enganoso — o filtro e sobre `created_at` da prova,
                    nao sobre qualquer conceito de "finalizacao". Wave 2 nao
                    tem o conceito de prova finalizada (isso existe na Wave 3
                    como RECEBIDA_PELA_CLICHERIA, mas a coluna correspondente
                    seria uma MAX(movimentacao.created_at), nao um campo na
                    tabela provas_digitais). */}
                Criada ate:
              </label>
              <input
                id="filtro_fim"
                type="date"
                className={styles.input}
                placeholder="dd/mm/aaaa"
                value={urlFilters.periodo_fim ?? ""}
                onChange={(e) => handlePeriodoFimChange(e.target.value)}
              />
            </div>

            <div className={styles.clearWrap}>
              <button
                type="button"
                className={styles.btnSecondary}
                onClick={handleLimparFiltros}
                disabled={!temFiltrosAtivos}
              >
                Limpar
              </button>
            </div>
          </div>
        </section>

        {/* ── Tabela ──────────────────────────────────────────────── */}
        <section className={styles.tableWrap}>
          <div className={styles.tableScroll}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Requerimento</th>
                  <th>Nome</th>
                  <th>Cliente</th>
                  <th>Vendedor</th>
                  <th>Status</th>
                  <th>Rota</th>
                  <th>Criada em</th>
                  <th className={styles.thActions} aria-label="Acoes"></th>
                </tr>
              </thead>
              <tbody>
                {loading && (
                  <tr>
                    <td colSpan={8} className={styles.loadingCell}>
                      Carregando...
                    </td>
                  </tr>
                )}
                {!loading && error && (
                  <tr>
                    <td colSpan={8} className={styles.errorCell}>
                      <div>{error}</div>
                      <button
                        type="button"
                        className={styles.retryBtn}
                        onClick={() => load(urlFilters)}
                      >
                        Tentar novamente
                      </button>
                    </td>
                  </tr>
                )}
                {!loading && !error && data && data.items.length === 0 && (
                  <tr>
                    <td colSpan={8} className={styles.emptyCell}>
                      {temFiltrosAtivos
                        ? "Nenhuma prova encontrada com esses filtros."
                        : "Nenhuma prova cadastrada ainda."}
                    </td>
                  </tr>
                )}
                {!loading &&
                  !error &&
                  data &&
                  data.items.map((p) => (
                    <tr key={p.id}>
                      <td className={styles.mono}>{p.nro_requerimento}</td>
                      <td>{p.nome}</td>
                      <td>{p.cliente}</td>
                      <td>{p.vendedor_nome}</td>
                      <td>
                        <span className={styles.statusBadge}>
                          {STATUS_LABELS_SHORT[p.status]}
                        </span>
                      </td>
                      <td>{p.rota ? ROTA_LABELS[p.rota] : "—"}</td>
                      <td>{formatDate(p.created_at)}</td>
                      <td className={styles.actions}>
                        <Link
                          href={`/provas/${p.id}`}
                          className={styles.detailBtn}
                          aria-label={`Ver prova ${p.nro_requerimento}`}
                        >
                          Ver
                        </Link>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── Paginacao ──────────────────────────────────────────── */}
        {!loading && !error && data && data.total > 0 && (
          <footer className={styles.pagination}>
            <span className={styles.pageInfo}>
              Pagina {data.page} de {data.pages} · {data.total}{" "}
              {data.total === 1 ? "resultado" : "resultados"}
            </span>
            <div className={styles.pageButtons}>
              <button
                type="button"
                className={styles.pageBtn}
                onClick={() => handlePage(1)}
                disabled={data.page === 1}
                aria-label="Primeira pagina"
              >
                ‹‹
              </button>
              <button
                type="button"
                className={styles.pageBtn}
                onClick={() => handlePage(data.page - 1)}
                disabled={data.page === 1}
                aria-label="Pagina anterior"
              >
                ‹
              </button>
              <button
                type="button"
                className={styles.pageBtn}
                onClick={() => handlePage(data.page + 1)}
                disabled={data.page >= data.pages}
                aria-label="Proxima pagina"
              >
                ›
              </button>
              <button
                type="button"
                className={styles.pageBtn}
                onClick={() => handlePage(data.pages)}
                disabled={data.page >= data.pages}
                aria-label="Ultima pagina"
              >
                ››
              </button>
            </div>
          </footer>
        )}
      </div>
    </>
  );
}

export default function ProvasPage() {
  // Suspense obrigatorio porque useSearchParams exige durante pre-render.
  return (
    <Suspense fallback={<div className={styles.loadingCell}>Carregando...</div>}>
      <ProvasPageInner />
    </Suspense>
  );
}
