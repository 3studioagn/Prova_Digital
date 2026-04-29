"use client";

/**
 * Pagina /auditoria — Wave 6, Componente 18 + UX iteration (pacote A+B).
 *
 * Listagem do log imutavel de auditoria (RNF-005), restrita ao perfil
 * 3Studio (is_admin=true). Defesa em tres camadas:
 *   1. Backend middleware get_admin_user (401/403 antes de qualquer query)
 *   2. RLS pol_audit_select (admin-only)
 *   3. Frontend: este guard renderiza estado restrito se is_admin=false;
 *      item de menu condicional ja esconde o link.
 *
 * UX iteration (Wave 6 pos-Gate 2):
 *   A1 — Presets de data (Hoje/7d/30d/90d/Personalizado), default Hoje
 *   A2 — Filtro semantico tipo_evento (em vez do `acao` cru)
 *   A3 — Filtro de usuario (dropdown populado via /users)
 *   A4 — Busca q expandida para nro_requerimento (placeholder reflete)
 *   B1 — Paginacao numerada (1 ... N) + input "ir para"
 *   B2 — Page size selector (25/50/100/200)
 *   B3 — Sticky header da tabela
 *   B4 — Ordenacao clicavel nas colunas (Data/Acao/Ator)
 *
 * Sem botoes de mutacao por construcao — auditoria e read-only.
 */

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import { useAuditLog, useAuditLogDetail } from "@/hooks/useAuditLog";
import { useFocusTrap } from "@/hooks/useFocusTrap";
import {
  type AuditLogFilters,
  type AuditLogItemResponse,
  type DatePresetKey,
  type OrderBy,
  type TipoEvento,
  categorizar,
  DATE_PRESET_LABELS,
  detectPreset,
  formatAcao,
  PAGE_SIZE_OPTIONS,
  presetToRange,
  TIPO_EVENTO_LABELS,
  TIPO_EVENTO_OPTIONS,
} from "@/lib/types/auditLog";
import type { MeResponse, UsuarioListResponse, UsuarioResponse } from "@/lib/types/usuario";
import styles from "./auditoria.module.css";

const DEFAULT_PAGE_SIZE = 50;

/** Formata ISO datetime UTC para America/Sao_Paulo (dd/mm/aaaa HH:MM:SS). */
function formatDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      timeZone: "America/Sao_Paulo",
    });
  } catch {
    return iso;
  }
}

/** Converte string YYYY-MM-DD (BRT) para ISO UTC inicio/fim do dia. */
function dateToIsoBrt(dateStr: string, endOfDay: boolean): string | null {
  if (!dateStr) return null;
  const [y, m, d] = dateStr.split("-").map(Number);
  if (!y || !m || !d) return null;
  const hh = endOfDay ? 23 : 0;
  const mm = endOfDay ? 59 : 0;
  const ss = endOfDay ? 59 : 0;
  const utcMs = Date.UTC(y, m - 1, d, hh + 3, mm, ss);
  return new Date(utcMs).toISOString();
}

/** Converte ISO UTC para YYYY-MM-DD em BRT. */
function isoUtcToDateBrt(iso: string | null): string {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    const brt = new Date(d.getTime() - 3 * 60 * 60 * 1000);
    return brt.toISOString().split("T")[0];
  } catch {
    return "";
  }
}

function AuditoriaPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const getToken = useCallback(async () => {
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  }, []);

  // ── Filtros derivados da URL ────────────────────────────────────────
  const filters: AuditLogFilters = useMemo(() => {
    const page = Number(searchParams.get("page") ?? "1") || 1;
    const page_size =
      Number(searchParams.get("page_size") ?? String(DEFAULT_PAGE_SIZE)) ||
      DEFAULT_PAGE_SIZE;
    const sortRaw = searchParams.get("sort");
    const sort: "asc" | "desc" = sortRaw === "asc" ? "asc" : "desc";
    const orderByRaw = searchParams.get("order_by");
    const order_by: OrderBy =
      orderByRaw === "acao" || orderByRaw === "usuario_nome"
        ? orderByRaw
        : "created_at";
    const tipoEventoRaw = searchParams.get("tipo_evento");
    const tipo_evento: TipoEvento | null =
      tipoEventoRaw &&
      (TIPO_EVENTO_OPTIONS as readonly string[]).includes(tipoEventoRaw)
        ? (tipoEventoRaw as TipoEvento)
        : null;
    return {
      page,
      page_size,
      sort,
      order_by,
      from_dt: searchParams.get("from"),
      to_dt: searchParams.get("to"),
      prova_id: searchParams.get("prova_id"),
      usuario_id: searchParams.get("usuario_id"),
      acao: searchParams.get("acao"),
      tipo_evento,
      q: searchParams.get("q"),
    };
  }, [searchParams]);

  // ── Default "Hoje" no primeiro acesso (UX A1) ───────────────────────
  // Quando o admin entra em /auditoria sem filtros de data, aplica o
  // preset "Hoje" automaticamente. Reduz o conjunto retornado de "tudo
  // que existe" para "o que aconteceu nas ultimas horas". O admin pode
  // expandir conscientemente trocando o pill.
  const router_replace = router.replace;
  const hasUrlFilters = useMemo(() => {
    return Array.from(searchParams.keys()).length > 0;
  }, [searchParams]);

  useEffect(() => {
    if (hasUrlFilters) return;
    const range = presetToRange("hoje");
    if (!range.from || !range.to) return;
    const next = new URLSearchParams();
    next.set("from", range.from);
    next.set("to", range.to);
    router_replace(`/auditoria?${next.toString()}`);
  }, [hasUrlFilters, router_replace]);

  // ── Inputs locais (texto/data com debounce) ─────────────────────────
  const [qInput, setQInput] = useState(filters.q ?? "");
  const [fromInput, setFromInput] = useState(isoUtcToDateBrt(filters.from_dt));
  const [toInput, setToInput] = useState(isoUtcToDateBrt(filters.to_dt));
  const [pageJumpInput, setPageJumpInput] = useState("");

  useEffect(() => {
    setQInput(filters.q ?? "");
    setFromInput(isoUtcToDateBrt(filters.from_dt));
    setToInput(isoUtcToDateBrt(filters.to_dt));
  }, [filters.q, filters.from_dt, filters.to_dt]);

  // ── Carrega usuario logado ──────────────────────────────────────────
  const [me, setMe] = useState<MeResponse | null>(null);
  const [meLoading, setMeLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    async function fetchMe() {
      const token = await getToken();
      if (!token || controller.signal.aborted) {
        if (!controller.signal.aborted) setMeLoading(false);
        return;
      }
      try {
        const data = await apiFetch<MeResponse>("/api/v1/users/me", {
          token,
          signal: controller.signal,
        });
        if (!controller.signal.aborted) {
          setMe(data);
          setMeLoading(false);
        }
      } catch {
        if (!controller.signal.aborted) setMeLoading(false);
      }
    }
    fetchMe();
    return () => controller.abort();
  }, [getToken]);

  // ── Carrega lista de usuarios (UX A3 — para dropdown de filtro) ────
  const [usuarios, setUsuarios] = useState<UsuarioResponse[]>([]);

  useEffect(() => {
    if (!me?.is_admin) return;
    const controller = new AbortController();
    async function fetchUsuarios() {
      const token = await getToken();
      if (!token || controller.signal.aborted) return;
      try {
        const data = await apiFetch<UsuarioListResponse>(
          "/api/v1/users/?ativo=true&page_size=200",
          { token, signal: controller.signal },
        );
        if (!controller.signal.aborted) setUsuarios(data.items);
      } catch (err) {
        // Audit 2026-04-29 L-04: aborts sao esperados (cleanup); demais
        // falhas (ex: 500 do /users) viraram log warn — antes eram engolidas
        // silenciosamente, deixando o dropdown vazio sem feedback ao admin.
        if (!controller.signal.aborted) {
          console.warn("Falha ao carregar lista de atores:", err);
        }
      }
    }
    fetchUsuarios();
    return () => controller.abort();
  }, [me?.is_admin, getToken]);

  // ── Hook do listing ─────────────────────────────────────────────────
  const { loading, error, data, refresh } = useAuditLog(getToken, filters);

  // ── Hook do detalhe (drawer) ────────────────────────────────────────
  const detail = useAuditLogDetail(getToken);
  const [drawerOpen, setDrawerOpen] = useState(false);
  // Audit 2026-04-29 H-01: focus trap obrigatorio em modais (WCAG 2.1).
  // Mesmo padrao usado em KeyboardShortcutsHelp.tsx (Wave 5).
  const drawerTrapRef = useFocusTrap<HTMLElement>(drawerOpen);

  const openDrawer = useCallback(
    (id: string) => {
      setDrawerOpen(true);
      detail.loadDetail(id);
    },
    [detail],
  );

  const closeDrawer = useCallback(() => {
    setDrawerOpen(false);
    detail.clear();
  }, [detail]);

  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeDrawer();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawerOpen, closeDrawer]);

  // ── Helpers para atualizar URL ──────────────────────────────────────
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
      // Reset de pagina quando qualquer filtro muda (exceto se patch ja
      // declara explicitamente uma nova page).
      if (!("page" in patch)) {
        next.delete("page");
      }
      const qs = next.toString();
      router.replace(qs ? `/auditoria?${qs}` : "/auditoria");
    },
    [router, searchParams],
  );

  // ── Handlers dos filtros ────────────────────────────────────────────

  const handleTipoEventoChange = (v: string) => {
    updateUrl({ tipo_evento: v && v !== "todos" ? v : null });
  };

  const handleUsuarioChange = (v: string) => {
    updateUrl({ usuario_id: v || null });
  };

  const handleSortChange = (v: string) => {
    updateUrl({ sort: v === "asc" ? "asc" : null });
  };

  const handlePageSizeChange = (v: string) => {
    const n = Number(v);
    if (!n || n === DEFAULT_PAGE_SIZE) {
      updateUrl({ page_size: null });
    } else {
      updateUrl({ page_size: String(n) });
    }
  };

  // Presets de data (UX A1)
  const handlePreset = (key: DatePresetKey) => {
    if (key === "personalizado") {
      // mantem from/to como esta — usuario edita os date inputs
      return;
    }
    const range = presetToRange(key);
    updateUrl({ from: range.from, to: range.to });
  };

  // Busca q (UX A4) — debounce
  const qTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const handleQChange = (v: string) => {
    setQInput(v);
    if (qTimerRef.current) clearTimeout(qTimerRef.current);
    qTimerRef.current = setTimeout(() => {
      updateUrl({ q: v || null });
    }, 350);
  };

  // Datas customizadas
  const handleFromChange = (v: string) => {
    setFromInput(v);
    updateUrl({ from: dateToIsoBrt(v, false) });
  };
  const handleToChange = (v: string) => {
    setToInput(v);
    updateUrl({ to: dateToIsoBrt(v, true) });
  };

  useEffect(() => {
    return () => {
      if (qTimerRef.current) clearTimeout(qTimerRef.current);
    };
  }, []);

  const handleLimparFiltros = () => {
    setQInput("");
    setFromInput("");
    setToInput("");
    router.replace("/auditoria");
  };

  const handlePage = (newPage: number) => {
    updateUrl({ page: String(newPage) });
  };

  // Ordenacao clicavel (UX B4) — toggle asc/desc na mesma coluna,
  // ou troca para a coluna nova com sort=desc default.
  const handleHeaderSort = (col: OrderBy) => {
    if (filters.order_by === col) {
      // Mesma coluna — toggle direcao.
      updateUrl({ sort: filters.sort === "asc" ? null : "asc" });
    } else {
      // Coluna nova — vai pro default (desc) explicitando order_by.
      updateUrl({ order_by: col === "created_at" ? null : col, sort: null });
    }
  };

  // Pagination numerada — calcula janela de paginas a exibir.
  const totalPages = data
    ? Math.max(1, Math.ceil(data.total / data.page_size))
    : 1;
  const pageWindow = useMemo(
    () => buildPageWindow(filters.page, totalPages),
    [filters.page, totalPages],
  );

  // Estado: nao admin
  if (!meLoading && me && !me.is_admin) {
    return (
      <div className={styles.restricted}>
        <h1 className={styles.restrictedTitle}>Acesso restrito</h1>
        <p className={styles.restrictedMessage}>
          A interface de auditoria e restrita ao perfil 3Studio (Administrador).
          Caso precise acessar, solicite a um administrador (RNF-005).
        </p>
        <Link href="/dashboard" className={styles.restrictedLink}>
          Voltar ao dashboard
        </Link>
      </div>
    );
  }

  const showingFrom = data && data.total > 0
    ? (data.page - 1) * data.page_size + 1
    : 0;
  const showingTo = data
    ? Math.min(data.page * data.page_size, data.total)
    : 0;

  const presetAtivo: DatePresetKey = detectPreset(filters.from_dt, filters.to_dt);

  const temFiltrosAtivos =
    !!filters.from_dt ||
    !!filters.to_dt ||
    !!filters.acao ||
    !!filters.tipo_evento ||
    !!filters.q ||
    !!filters.prova_id ||
    !!filters.usuario_id ||
    filters.sort !== "desc" ||
    filters.order_by !== "created_at" ||
    filters.page_size !== DEFAULT_PAGE_SIZE;

  const handlePageJumpSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const n = Number(pageJumpInput);
    if (!n || n < 1 || n > totalPages) return;
    handlePage(n);
    setPageJumpInput("");
  };

  return (
    <>
      <div className={styles.mobileNotice}>
        <p>Para acessar esse recurso, acesse a versao desktop.</p>
      </div>
      <div className={styles.desktopOnly}>
        <header className={styles.pageHeader}>
          <h1 className={styles.title}>Auditoria</h1>
          <p className={styles.subtitle}>
            Log imutavel de todas as acoes do sistema (RNF-005). Acesso
            restrito ao perfil 3Studio.
          </p>
        </header>

        {/* ── Presets de data (UX A1) ────────────────────────────── */}
        <section className={styles.presetsBar} aria-label="Periodo">
          <span className={styles.presetsLabel}>Periodo:</span>
          {(["hoje", "7d", "30d", "90d", "personalizado"] as DatePresetKey[]).map(
            (key) => (
              <button
                key={key}
                type="button"
                className={
                  presetAtivo === key
                    ? styles.presetPillActive
                    : styles.presetPill
                }
                onClick={() => handlePreset(key)}
                aria-pressed={presetAtivo === key}
              >
                {DATE_PRESET_LABELS[key]}
              </button>
            ),
          )}
        </section>

        {/* ── Filtros principais ──────────────────────────────────── */}
        <section className={styles.filters} aria-label="Filtros">
          <div className={styles.filterRow}>
            <div className={styles.field}>
              <label htmlFor="filtro_q" className={styles.label}>
                Buscar:
              </label>
              <input
                id="filtro_q"
                type="search"
                className={styles.input}
                placeholder="motivo, cliente ou nro requerimento"
                value={qInput}
                onChange={(e) => handleQChange(e.target.value)}
              />
            </div>

            <div className={styles.field}>
              <label htmlFor="filtro_tipo_evento" className={styles.label}>
                Tipo de evento:
              </label>
              <select
                id="filtro_tipo_evento"
                className={styles.select}
                value={filters.tipo_evento ?? "todos"}
                onChange={(e) => handleTipoEventoChange(e.target.value)}
              >
                {TIPO_EVENTO_OPTIONS.map((t) => (
                  <option key={t} value={t}>
                    {TIPO_EVENTO_LABELS[t]}
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.field}>
              <label htmlFor="filtro_usuario" className={styles.label}>
                Ator:
              </label>
              <select
                id="filtro_usuario"
                className={styles.select}
                value={filters.usuario_id ?? ""}
                onChange={(e) => handleUsuarioChange(e.target.value)}
              >
                <option value="">Todos</option>
                {usuarios.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.nome} ({u.setor})
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.field}>
              <label htmlFor="filtro_sort" className={styles.label}>
                Ordem:
              </label>
              <select
                id="filtro_sort"
                className={styles.select}
                value={filters.sort}
                onChange={(e) => handleSortChange(e.target.value)}
              >
                <option value="desc">Mais recentes primeiro</option>
                <option value="asc">Mais antigos primeiro</option>
              </select>
            </div>
          </div>

          {/* Linha 2: datas custom + page_size + limpar */}
          <div className={styles.filterRow}>
            <div className={styles.field}>
              <label htmlFor="filtro_from" className={styles.label}>
                De:
              </label>
              <input
                id="filtro_from"
                type="date"
                className={styles.input}
                value={fromInput}
                onChange={(e) => handleFromChange(e.target.value)}
              />
            </div>

            <div className={styles.field}>
              <label htmlFor="filtro_to" className={styles.label}>
                Ate:
              </label>
              <input
                id="filtro_to"
                type="date"
                className={styles.input}
                value={toInput}
                onChange={(e) => handleToChange(e.target.value)}
              />
            </div>

            <div className={styles.field}>
              <label htmlFor="filtro_page_size" className={styles.label}>
                Linhas por pagina:
              </label>
              <select
                id="filtro_page_size"
                className={styles.select}
                value={String(filters.page_size)}
                onChange={(e) => handlePageSizeChange(e.target.value)}
              >
                {PAGE_SIZE_OPTIONS.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.field}>
              {/* Audit 2026-04-29 L-03: rotulo "Restaurar padrao" reflete
                  que o useEffect re-aplica preset "Hoje" quando a URL fica
                  vazia — "Limpar filtros" sugeria estado realmente vazio. */}
              <button
                type="button"
                className={styles.btnSecondary}
                onClick={handleLimparFiltros}
                disabled={!temFiltrosAtivos}
              >
                Restaurar padrao
              </button>
            </div>
          </div>
        </section>

        {/* ── Tabela ───────────────────────────────────────────────── */}
        <div className={styles.tableWrap}>
          <div className={styles.tableScroll}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <SortableTh
                    label="Data e hora"
                    column="created_at"
                    activeColumn={filters.order_by}
                    direction={filters.sort}
                    onClick={handleHeaderSort}
                  />
                  <SortableTh
                    label="Acao"
                    column="acao"
                    activeColumn={filters.order_by}
                    direction={filters.sort}
                    onClick={handleHeaderSort}
                  />
                  <SortableTh
                    label="Ator"
                    column="usuario_nome"
                    activeColumn={filters.order_by}
                    direction={filters.sort}
                    onClick={handleHeaderSort}
                  />
                  <th>Setor</th>
                  <th>Prova</th>
                  <th>IP</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={6} className={styles.loadingCell}>
                      Carregando registros...
                    </td>
                  </tr>
                ) : error ? (
                  <tr>
                    <td colSpan={6} className={styles.errorCell}>
                      <div className={styles.errorMessage}>{error}</div>
                      <div>
                        <button
                          type="button"
                          className={styles.retryBtn}
                          onClick={refresh}
                        >
                          Tentar novamente
                        </button>
                      </div>
                    </td>
                  </tr>
                ) : !data || data.items.length === 0 ? (
                  <tr>
                    <td colSpan={6} className={styles.emptyCell}>
                      Nenhum registro encontrado para os filtros aplicados.
                    </td>
                  </tr>
                ) : (
                  data.items.map((item) => (
                    <AuditLogRow
                      key={item.id}
                      item={item}
                      onClick={() => openDrawer(item.id)}
                    />
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── Paginacao numerada (UX B1) ──────────────────────────── */}
        {data && data.total > 0 && (
          <nav className={styles.pagination} aria-label="Paginacao">
            <span className={styles.pageInfo}>
              Mostrando {showingFrom}-{showingTo} de {data.total}
            </span>
            <div className={styles.pageButtons}>
              <button
                type="button"
                className={styles.pageBtn}
                onClick={() => handlePage(filters.page - 1)}
                disabled={filters.page <= 1}
              >
                Anterior
              </button>
              {pageWindow.map((entry, idx) =>
                entry === "..." ? (
                  <span
                    key={`ellipsis-${idx}`}
                    className={styles.pageEllipsis}
                    aria-hidden="true"
                  >
                    ...
                  </span>
                ) : (
                  <button
                    key={entry}
                    type="button"
                    className={
                      entry === filters.page
                        ? styles.pageBtnActive
                        : styles.pageBtn
                    }
                    onClick={() => handlePage(entry)}
                    aria-current={entry === filters.page ? "page" : undefined}
                  >
                    {entry}
                  </button>
                ),
              )}
              <button
                type="button"
                className={styles.pageBtn}
                onClick={() => handlePage(filters.page + 1)}
                disabled={filters.page >= totalPages}
              >
                Proxima
              </button>
            </div>
            {totalPages > 5 && (
              <form
                className={styles.pageJump}
                onSubmit={handlePageJumpSubmit}
                aria-label="Ir para pagina"
              >
                <label htmlFor="page_jump" className={styles.pageJumpLabel}>
                  Ir para:
                </label>
                <input
                  id="page_jump"
                  type="number"
                  min={1}
                  max={totalPages}
                  className={styles.pageJumpInput}
                  value={pageJumpInput}
                  onChange={(e) => setPageJumpInput(e.target.value)}
                  placeholder={String(filters.page)}
                />
                <button type="submit" className={styles.pageJumpBtn}>
                  Ir
                </button>
              </form>
            )}
          </nav>
        )}

        {/* ── Drawer de detalhe ────────────────────────────────────── */}
        {drawerOpen && (
          <>
            <div
              className={styles.drawerBackdrop}
              onClick={closeDrawer}
              aria-hidden="true"
            />
            <aside
              ref={drawerTrapRef}
              className={styles.drawer}
              role="dialog"
              aria-modal="true"
              aria-labelledby="drawer-title"
            >
              <header className={styles.drawerHeader}>
                <h2 id="drawer-title" className={styles.drawerTitle}>
                  Detalhes do registro
                </h2>
                <button
                  type="button"
                  className={styles.drawerCloseBtn}
                  onClick={closeDrawer}
                  aria-label="Fechar painel"
                >
                  &times;
                </button>
              </header>
              <div className={styles.drawerBody}>
                {detail.loading ? (
                  <p>Carregando...</p>
                ) : detail.error ? (
                  <p className={styles.errorMessage}>{detail.error}</p>
                ) : detail.data ? (
                  <>
                    <DrawerSection
                      label="Acao"
                      value={formatAcao(detail.data.acao)}
                    />
                    <DrawerSection
                      label="Quando"
                      value={formatDateTime(detail.data.created_at)}
                    />
                    <DrawerSection
                      label="Ator"
                      value={`${detail.data.usuario_nome} (${detail.data.usuario_setor})`}
                    />
                    {detail.data.prova_nro_requerimento && (
                      <DrawerSection
                        label="Prova"
                        value={`#${detail.data.prova_nro_requerimento}`}
                      />
                    )}
                    {detail.data.ip_address && (
                      <DrawerSection
                        label="IP de origem"
                        value={detail.data.ip_address}
                      />
                    )}
                    {detail.data.user_agent && (
                      <DrawerSection
                        label="User Agent"
                        value={detail.data.user_agent}
                      />
                    )}
                    {detail.data.detalhes_json && (
                      <div className={styles.drawerSection}>
                        <span className={styles.drawerLabel}>
                          Detalhes (JSON)
                        </span>
                        <div className={styles.detalhesBlock}>
                          {JSON.stringify(detail.data.detalhes_json, null, 2)}
                        </div>
                      </div>
                    )}
                    {detail.data.movimentacao_relacionada && (
                      <div className={styles.drawerSection}>
                        <span className={styles.drawerLabel}>
                          Movimentacao relacionada (validada por DDL)
                        </span>
                        <div className={styles.movRelacionada}>
                          <div className={styles.movHeader}>
                            {detail.data.movimentacao_relacionada.status_anterior}
                            {" -> "}
                            {detail.data.movimentacao_relacionada.status_novo}
                          </div>
                          <div className={styles.movRow}>
                            <span>Ciclo</span>
                            <span>
                              {detail.data.movimentacao_relacionada.ciclo}
                            </span>
                          </div>
                          {detail.data.movimentacao_relacionada.rota_no_momento && (
                            <div className={styles.movRow}>
                              <span>Rota no momento</span>
                              <span>
                                {detail.data.movimentacao_relacionada.rota_no_momento}
                              </span>
                            </div>
                          )}
                          <div className={styles.movRow}>
                            <span>Assinatura digital</span>
                            <span
                              className={
                                detail.data.movimentacao_relacionada.assinatura_digital_presente
                                  ? styles.assinaturaOk
                                  : styles.assinaturaFalta
                              }
                            >
                              {detail.data.movimentacao_relacionada.assinatura_digital_presente
                                ? "Presente"
                                : "Ausente"}
                            </span>
                          </div>
                          {detail.data.movimentacao_relacionada.motivo_reprovacao && (
                            <div className={styles.movMotivo}>
                              Motivo:{" "}
                              {detail.data.movimentacao_relacionada.motivo_reprovacao}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </>
                ) : null}
              </div>
            </aside>
          </>
        )}
      </div>
    </>
  );
}

// ─── Helpers de UI ─────────────────────────────────────────────────────

interface SortableThProps {
  label: string;
  column: OrderBy;
  activeColumn: OrderBy;
  direction: "asc" | "desc";
  onClick: (col: OrderBy) => void;
}

function SortableTh({
  label,
  column,
  activeColumn,
  direction,
  onClick,
}: SortableThProps) {
  const isActive = activeColumn === column;
  const ariaSort = isActive
    ? direction === "asc"
      ? "ascending"
      : "descending"
    : "none";
  const arrow = isActive ? (direction === "asc" ? " ↑" : " ↓") : "";
  return (
    <th aria-sort={ariaSort}>
      <button
        type="button"
        className={
          isActive ? styles.sortableHeaderActive : styles.sortableHeader
        }
        onClick={() => onClick(column)}
      >
        {label}
        <span aria-hidden="true">{arrow}</span>
      </button>
    </th>
  );
}

interface RowProps {
  item: AuditLogItemResponse;
  onClick: () => void;
}

function AuditLogRow({ item, onClick }: RowProps) {
  const cat = categorizar(item);
  const badgeClass = [
    styles.acaoBadge,
    cat === "reprovacao" && styles.acaoReprovacao,
    cat === "reinicio" && styles.acaoReinicio,
    cat === "cancelamento" && styles.acaoCancelamento,
    cat === "criacao" && styles.acaoCriacao,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <tr className={styles.clickable} onClick={onClick}>
      <td>{formatDateTime(item.created_at)}</td>
      <td>
        <span className={badgeClass}>{formatAcao(item.acao)}</span>
      </td>
      <td>{item.usuario_nome}</td>
      <td>{item.usuario_setor}</td>
      <td>{item.prova_nro_requerimento ?? "-"}</td>
      <td>{item.ip_address ?? "-"}</td>
    </tr>
  );
}

interface DrawerSectionProps {
  label: string;
  value: string;
}

function DrawerSection({ label, value }: DrawerSectionProps) {
  return (
    <div className={styles.drawerSection}>
      <span className={styles.drawerLabel}>{label}</span>
      <span className={styles.drawerValue}>{value}</span>
    </div>
  );
}

/** Constroi a janela de paginas a renderizar (UX B1).
 *
 * Padrao: sempre mostra 1, current-1, current, current+1, last, com
 * ellipsis (...) entre saltos. Em totalPages <= 7, mostra todos.
 *
 * Exemplos para current=10, total=84:
 *   [1, "...", 9, 10, 11, "...", 84]
 *
 * Exemplos para current=2, total=10:
 *   [1, 2, 3, 4, 5, "...", 10]
 */
function buildPageWindow(
  current: number,
  total: number,
): Array<number | "..."> {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }

  const result: Array<number | "..."> = [1];
  const start = Math.max(2, current - 1);
  const end = Math.min(total - 1, current + 1);

  if (start > 2) result.push("...");
  for (let i = start; i <= end; i++) result.push(i);
  if (end < total - 1) result.push("...");

  result.push(total);
  return result;
}

export default function AuditoriaPage() {
  return (
    <Suspense fallback={<div>Carregando...</div>}>
      <AuditoriaPageInner />
    </Suspense>
  );
}
