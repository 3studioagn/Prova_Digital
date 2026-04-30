"use client";

/**
 * Pagina /relatorios (Wave 5, Componente 16).
 *
 * Orquestra:
 *  - useReportFilters: filtros URL-persistidos (deep-link/bookmark/back).
 *  - useReport: fetch do payload com cache local + ETag.
 *  - useReportExport: download CSV.
 *  - Realtime via Supabase: invalida cache local em mudancas em provas_digitais.
 *  - Polling fallback (30s) se Realtime falhar.
 *
 * No Bloco 5.3, perspectivas sao renderizadas como cards "raw" com KPIs
 * basicos. Bloco 5.4 substitui por componentes dedicados (ReportGeral,
 * Report3Studio, ReportVendedores, ReportClicheria) com graficos.
 *
 * Suspense boundary: necessario porque `useSearchParams` so funciona em
 * Client Component dentro de Suspense (Next.js 14 App Router).
 */
import { Suspense, useCallback, useEffect, useRef } from "react";
import { createBrowserClient } from "@supabase/ssr";

import { useReport } from "@/hooks/useReport";
import { useReportExport } from "@/hooks/useReportExport";
import { useReportFilters } from "@/hooks/useReportFilters";
import { useAuthorization } from "@/lib/hooks/use-authorization";
import { Restricted } from "@/components/Restricted";

import { DateRangeFilter } from "./DateRangeFilter";
import { ExportButton } from "./ExportButton";
import { RotaFilter } from "./RotaFilter";
import { ScopeSelector } from "./ScopeSelector";
import { SearchInput } from "./SearchInput";
import { StatusFilter } from "./StatusFilter";
import { VendedorFilter } from "./VendedorFilter";
import { Report3Studio } from "./perspectivas/Report3Studio";
import { ReportClicheria } from "./perspectivas/ReportClicheria";
import { ReportGeral } from "./perspectivas/ReportGeral";
import { ReportVendedores } from "./perspectivas/ReportVendedores";
import { PeriodoBadge } from "./shared/PeriodoBadge";
import type { ReportResponse } from "@/lib/types/report";
import type { StatusProva } from "@/lib/types/prova";

import styles from "./relatorios.module.css";

// ─── Supabase client (singleton no modulo) ─────────────────────────────

const supabase = createBrowserClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
);

async function getToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

const REALTIME_DEBOUNCE_MS = 2_000;
const POLLING_INTERVAL_MS = 30_000;

// ─── Pagina principal ──────────────────────────────────────────────────

function RelatoriosContent() {
  // Wave 1 v4.0 — guard proativo via Matriz de Acesso. Substitui o
  // guard reativo (parsing de "administrad" na mensagem de erro do backend)
  // que existia neste arquivo. Beneficio: nao dispara fetch quando
  // usuario sem acesso entra (ex.: vendedor que digita /relatorios na URL),
  // exibindo mensagem padronizada imediatamente.
  const auth = useAuthorization("relatorios");

  const { filters, setFilter, setFilters, toQueryString } = useReportFilters();
  const queryString = toQueryString();
  const { loading, refreshing, error, data, refresh, invalidate } = useReport(
    filters,
    queryString,
    getToken,
  );
  const exportState = useReportExport(getToken);

  // ─── Realtime + polling fallback ─────────────────────────────────────
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const debouncedInvalidate = useCallback(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      invalidate();
    }, REALTIME_DEBOUNCE_MS);
  }, [invalidate]);

  useEffect(() => {
    const channel = supabase
      .channel("relatorios-provas")
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "provas_digitais" },
        () => {
          debouncedInvalidate();
        },
      )
      .subscribe((status) => {
        if (status === "SUBSCRIBED") {
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
        } else if (status === "CHANNEL_ERROR" || status === "TIMED_OUT") {
          if (!pollingRef.current) {
            pollingRef.current = setInterval(refresh, POLLING_INTERVAL_MS);
          }
        }
      });

    // Polling default ativo ate o Realtime conectar
    pollingRef.current = setInterval(refresh, POLLING_INTERVAL_MS);

    return () => {
      channel.unsubscribe();
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [debouncedInvalidate, refresh]);

  // ─── Render ──────────────────────────────────────────────────────────

  // Wave 1 v4.0: guard proativo. Sem acesso -> Restricted (sem fetch).
  // M-1 (audit fixes): retorna null durante loading evita flash de UI.
  if (auth.loading) return null;
  if (!auth.hasAccess) {
    return (
      <div className={styles.page}>
        <Restricted ruleKey="relatorios" profile={auth.profile} />
      </div>
    );
  }

  // Loading inicial sem dados
  if (loading && !data) {
    return (
      <div className={styles.page}>
        <h1 className={styles.title}>Relatorios</h1>
        <div className={styles.loadingState}>Carregando relatorio...</div>
      </div>
    );
  }

  // Erro tela cheia (sem dados)
  if (error && !data) {
    const isForbidden = error.toLowerCase().includes("administrad");
    return (
      <div className={styles.page}>
        <h1 className={styles.title}>Relatorios</h1>
        <div className={styles.errorState} role="alert">
          <p>{isForbidden ? "Acesso restrito a administradores." : error}</p>
          {!isForbidden && (
            <button
              type="button"
              className={styles.retryButton}
              onClick={refresh}
            >
              Tentar novamente
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Relatorios</h1>
          {data && (
            <div className={styles.subtitle}>
              <PeriodoBadge
                fromIso={data.periodo.from}
                toIso={data.periodo.to}
                totalDias={data.periodo.total_dias}
              />
              {refreshing && (
                <span className={styles.refreshingBadge}>Atualizando...</span>
              )}
            </div>
          )}
        </div>

        <ExportButton
          filters={filters}
          queryString={queryString}
          exporting={exportState.exporting}
          error={exportState.error}
          exportCsv={exportState.exportCsv}
          clearError={exportState.clearError}
        />
      </header>

      <ScopeSelector
        value={filters.scope}
        onChange={(scope) => setFilter("scope", scope)}
      />

      <section className={styles.filtersBar}>
        <DateRangeFilter
          fromISO={filters.from ?? null}
          toISO={filters.to ?? null}
          onChange={({ from, to }) => {
            // Atualiza atomicamente — `setFilter` sequencial perderia o
            // primeiro update (race do searchParams no closure).
            setFilters({ from, to });
          }}
        />
        <SearchInput
          value={filters.q ?? null}
          onChange={(q) => setFilter("q", q)}
        />
        <StatusFilter
          value={filters.status ?? null}
          onChange={(status) => setFilter("status", status)}
        />
        <VendedorFilter
          value={filters.vendedor_id ?? null}
          onChange={(vid) => setFilter("vendedor_id", vid)}
          getToken={getToken}
        />
        <RotaFilter
          value={filters.rota ?? null}
          onChange={(rota) => setFilter("rota", rota)}
        />
      </section>

      {error && data && (
        <div className={styles.errorBanner} role="alert">
          {error} —{" "}
          <button
            type="button"
            className={styles.retryButton}
            onClick={refresh}
          >
            tentar novamente
          </button>
        </div>
      )}

      {data ? (
        <PerspectivaRenderer
          data={data}
          statusFilter={filters.status ?? null}
          onStatusClick={(status) => setFilter("status", status)}
        />
      ) : (
        <div className={styles.emptyState}>Nenhum dado disponivel.</div>
      )}
    </div>
  );
}

/**
 * Roteia para a perspectiva certa via discriminated union.
 * Switch exaustivo — TS reclama se um scope nao for tratado.
 */
function PerspectivaRenderer({
  data,
  statusFilter,
  onStatusClick,
}: {
  data: ReportResponse;
  statusFilter: StatusProva | null;
  onStatusClick: (status: StatusProva | null) => void;
}) {
  switch (data.scope) {
    case "geral":
      return (
        <ReportGeral
          data={data}
          statusFilter={statusFilter}
          onStatusClick={onStatusClick}
        />
      );
    case "3studio":
      return <Report3Studio data={data} />;
    case "vendedores":
      return <ReportVendedores data={data} />;
    case "clicheria":
      return <ReportClicheria data={data} />;
  }
}

// ─── Suspense wrapper (necessario para useSearchParams em Next 14) ────

export default function RelatoriosPage() {
  return (
    <Suspense fallback={<div className={styles.loadingState}>Carregando...</div>}>
      <RelatoriosContent />
    </Suspense>
  );
}
