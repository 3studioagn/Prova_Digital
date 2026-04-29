"use client";

/**
 * Pagina /auditoria — Wave 6, Componente 18.
 *
 * Listagem do log imutavel de auditoria (RNF-005), restrita ao perfil
 * 3Studio (is_admin=true). Defesa em tres camadas:
 *   1. Backend middleware get_admin_user (401/403 antes de qualquer query)
 *   2. RLS pol_audit_select (admin-only)
 *   3. Frontend: este guard renderiza estado restrito se is_admin=false;
 *      item de menu condicional ja esconde o link.
 *
 * Visual: tabela em card claro (alinhada com /provas), filtros inline em
 * grid 4xN, paginacao, drawer lateral de detalhe. Sem botoes de mutacao
 * por construcao — auditoria e read-only.
 */

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { apiFetch, ApiError } from "@/lib/api";
import { useAuditLog, useAuditLogDetail } from "@/hooks/useAuditLog";
import {
  ACOES_CONHECIDAS,
  type AuditLogFilters,
  type AuditLogItemResponse,
  categorizar,
  DEFAULT_FILTERS,
  formatAcao,
} from "@/lib/types/auditLog";
import type { MeResponse } from "@/lib/types/usuario";
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

/** Converte string YYYY-MM-DD (BRT) para ISO UTC inicio do dia. */
function dateToIsoBrt(dateStr: string, endOfDay: boolean): string | null {
  if (!dateStr) return null;
  const [y, m, d] = dateStr.split("-").map(Number);
  if (!y || !m || !d) return null;
  // Constroi como meia-noite/fim do dia em America/Sao_Paulo (UTC-3 sem DST hoje).
  // Brasil aboliu DST em 2019; assumimos UTC-3. Se reintroduzir, usar Intl como
  // o DateRangeFilter da Wave 5 faz dinamicamente — para Wave 6 fica em offset
  // fixo (admin-tool, baixo risco operacional).
  const hh = endOfDay ? 23 : 0;
  const mm = endOfDay ? 59 : 0;
  const ss = endOfDay ? 59 : 0;
  // Date.UTC retorna ms desde epoch em UTC. Adicionamos 3h para converter BRT->UTC.
  const utcMs = Date.UTC(y, m - 1, d, hh + 3, mm, ss);
  return new Date(utcMs).toISOString();
}

/** Converte ISO UTC para YYYY-MM-DD em BRT (para preencher o input date). */
function isoUtcToDateBrt(iso: string | null): string {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    // Subtrai 3h para BRT (assumindo UTC-3).
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
    return {
      page,
      page_size,
      sort,
      from_dt: searchParams.get("from"),
      to_dt: searchParams.get("to"),
      prova_id: searchParams.get("prova_id"),
      usuario_id: searchParams.get("usuario_id"),
      acao: searchParams.get("acao"),
      q: searchParams.get("q"),
    };
  }, [searchParams]);

  // ── Inputs locais (texto/data com debounce) ─────────────────────────
  const [qInput, setQInput] = useState(filters.q ?? "");
  const [fromInput, setFromInput] = useState(isoUtcToDateBrt(filters.from_dt));
  const [toInput, setToInput] = useState(isoUtcToDateBrt(filters.to_dt));

  useEffect(() => {
    setQInput(filters.q ?? "");
    setFromInput(isoUtcToDateBrt(filters.from_dt));
    setToInput(isoUtcToDateBrt(filters.to_dt));
  }, [filters.q, filters.from_dt, filters.to_dt]);

  // ── Carrega usuario logado para guard de admin ──────────────────────
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

  // ── Hook do listing — dispara automatico em filters change ──────────
  const { loading, error, data, refresh } = useAuditLog(getToken, filters);

  // ── Hook do detalhe (drawer) ────────────────────────────────────────
  const detail = useAuditLogDetail(getToken);
  const [drawerOpen, setDrawerOpen] = useState(false);

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

  // ESC fecha o drawer
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
      // Reset de pagina quando qualquer filtro muda
      if (!("page" in patch)) {
        next.delete("page");
      }
      const qs = next.toString();
      router.replace(qs ? `/auditoria?${qs}` : "/auditoria");
    },
    [router, searchParams],
  );

  // Handlers imediatos
  const handleAcaoChange = (v: string) => updateUrl({ acao: v || null });
  const handleSortChange = (v: string) =>
    updateUrl({ sort: v === "asc" ? "asc" : null });

  // Handler com debounce (q)
  const qTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const handleQChange = (v: string) => {
    setQInput(v);
    if (qTimerRef.current) clearTimeout(qTimerRef.current);
    qTimerRef.current = setTimeout(() => {
      updateUrl({ q: v || null });
    }, 350);
  };

  // Datas — convertem BRT->UTC ao perder foco/onChange
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

  // ── Estado: nao admin ───────────────────────────────────────────────
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

  // ── Render ──────────────────────────────────────────────────────────
  const totalPages = data
    ? Math.max(1, Math.ceil(data.total / data.page_size))
    : 1;
  const showingFrom = data && data.total > 0
    ? (data.page - 1) * data.page_size + 1
    : 0;
  const showingTo = data
    ? Math.min(data.page * data.page_size, data.total)
    : 0;

  const temFiltrosAtivos =
    !!filters.from_dt ||
    !!filters.to_dt ||
    !!filters.acao ||
    !!filters.q ||
    !!filters.prova_id ||
    !!filters.usuario_id ||
    filters.sort !== DEFAULT_FILTERS.sort;

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

        {/* ── Filtros ──────────────────────────────────────────────── */}
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
                placeholder="motivo, cliente..."
                value={qInput}
                onChange={(e) => handleQChange(e.target.value)}
              />
            </div>

            <div className={styles.field}>
              <label htmlFor="filtro_acao" className={styles.label}>
                Acao:
              </label>
              <select
                id="filtro_acao"
                className={styles.select}
                value={filters.acao ?? ""}
                onChange={(e) => handleAcaoChange(e.target.value)}
              >
                <option value="">Todas</option>
                {ACOES_CONHECIDAS.map((a) => (
                  <option key={a} value={a}>
                    {formatAcao(a)}
                  </option>
                ))}
              </select>
            </div>

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
          </div>

          <div className={styles.filterRow}>
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

            <div className={styles.field} style={{ gridColumn: "span 2" }} />

            <div className={styles.field}>
              <button
                type="button"
                className={styles.btnSecondary}
                onClick={handleLimparFiltros}
                disabled={!temFiltrosAtivos}
              >
                Limpar filtros
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
                  <th>Data e hora</th>
                  <th>Acao</th>
                  <th>Ator</th>
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

        {/* ── Paginacao ────────────────────────────────────────────── */}
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
              <button
                type="button"
                className={styles.pageBtn}
                onClick={() => handlePage(filters.page + 1)}
                disabled={filters.page >= totalPages}
              >
                Proxima
              </button>
            </div>
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

export default function AuditoriaPage() {
  return (
    <Suspense fallback={<div>Carregando...</div>}>
      <AuditoriaPageInner />
    </Suspense>
  );
}
