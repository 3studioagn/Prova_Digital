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

import { DateRangeFilter } from "./DateRangeFilter";
import { ExportButton } from "./ExportButton";
import { ScopeSelector } from "./ScopeSelector";
import { SearchInput } from "./SearchInput";
import {
  formatHoras,
  formatNum,
  formatPct,
} from "@/lib/types/report";
import type { ReportResponse } from "@/lib/types/report";

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
  const { filters, setFilter, toQueryString } = useReportFilters();
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
            <p className={styles.subtitle}>
              Periodo: {data.periodo.total_dias} dia
              {data.periodo.total_dias !== 1 ? "s" : ""}
              {refreshing && (
                <span className={styles.refreshingBadge}>Atualizando...</span>
              )}
            </p>
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
            setFilter("from", from);
            setFilter("to", to);
          }}
        />
        <SearchInput
          value={filters.q ?? null}
          onChange={(q) => setFilter("q", q)}
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
        <PerspectivaPlaceholder data={data} />
      ) : (
        <div className={styles.emptyState}>Nenhum dado disponivel.</div>
      )}
    </div>
  );
}

// ─── Renderer placeholder (Bloco 5.4 substitui por perspectivas dedicadas) ─

function PerspectivaPlaceholder({ data }: { data: ReportResponse }) {
  // Match exaustivo via discriminated union
  switch (data.scope) {
    case "geral":
      return (
        <section
          className={styles.scopePanel}
          id="report-panel-geral"
          aria-labelledby="report-panel-geral"
        >
          <KpiGrid>
            <KpiCard label="Total de provas" value={formatNum(data.indicadores.total_provas)} />
            <KpiCard
              label="Tempo medio de ciclo"
              value={formatHoras(data.indicadores.tempo_medio_ciclo_horas)}
            />
            <KpiCard
              label="Tempo mediano de ciclo"
              value={formatHoras(data.indicadores.tempo_mediano_ciclo_horas)}
            />
            <KpiCard
              label="Tempo medio de aprovacao"
              value={formatHoras(data.indicadores.tempo_medio_aprovacao_horas)}
            />
            <KpiCard
              label="Taxa de reprovacao"
              value={formatPct(data.indicadores.taxa_reprovacao)}
            />
            <KpiCard
              label="Atrasadas (agora)"
              value={formatNum(data.indicadores.qtd_atrasadas)}
            />
          </KpiGrid>
          <p className={styles.placeholderNote}>
            Graficos detalhados (serie temporal + distribuicoes) chegam no Bloco 5.4.
          </p>
        </section>
      );

    case "3studio":
      return (
        <section
          className={styles.scopePanel}
          id="report-panel-3studio"
        >
          <KpiGrid>
            <KpiCard label="Provas criadas" value={formatNum(data.indicadores.provas_criadas)} />
            <KpiCard
              label="Media diaria"
              value={data.indicadores.media_diaria_criacao.toFixed(2)}
            />
            <KpiCard
              label="Reinicios de ciclo"
              value={formatNum(data.indicadores.reinicios_de_ciclo)}
            />
            <KpiCard
              label="Devolvidas (motorista)"
              value={formatNum(data.indicadores.devolvidas_motorista)}
            />
            <KpiCard
              label="Reprovadas aguardando"
              value={formatNum(data.indicadores.reprovadas_aguardando_acao)}
            />
            <KpiCard
              label="Cancelamentos"
              value={formatNum(data.indicadores.cancelamentos)}
            />
            <KpiCard
              label="Tempo medio ate 1ª mov"
              value={formatHoras(
                data.indicadores.tempo_medio_criacao_ate_primeira_mov_horas,
              )}
            />
          </KpiGrid>
          {data.cancelamentos_top.length > 0 && (
            <div className={styles.simpleList}>
              <h2 className={styles.simpleListTitle}>Top motivos de cancelamento</h2>
              <ul className={styles.simpleListUl}>
                {data.cancelamentos_top.map((c) => (
                  <li key={c.motivo}>
                    <strong>{c.quantidade}×</strong> {c.motivo}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      );

    case "vendedores":
      return (
        <section
          className={styles.scopePanel}
          id="report-panel-vendedores"
        >
          <KpiGrid>
            <KpiCard
              label="Vendedores Matriz"
              value={formatNum(data.distribuicao_localizacao.matriz)}
            />
            <KpiCard
              label="Vendedores Filial"
              value={formatNum(data.distribuicao_localizacao.filial)}
            />
            <KpiCard label="Total no ranking" value={formatNum(data.ranking.length)} />
          </KpiGrid>
          {data.ranking.length > 0 && (
            <div className={styles.simpleList}>
              <h2 className={styles.simpleListTitle}>Ranking por volume</h2>
              <ul className={styles.simpleListUl}>
                {data.ranking.slice(0, 10).map((v) => (
                  <li key={v.vendedor_id}>
                    <strong>{v.vendedor_nome}</strong>
                    {" — "}
                    {formatNum(v.volume)} provas, {formatPct(v.taxa_aprovacao)} aprov.
                    {v.provas_atrasadas_em_poder > 0 && (
                      <span className={styles.warnInline}>
                        {" "}
                        · {v.provas_atrasadas_em_poder} atrasadas
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <p className={styles.placeholderNote}>
            Tabela completa + lista de atrasadas em poder no Bloco 5.4.
          </p>
        </section>
      );

    case "clicheria":
      return (
        <section
          className={styles.scopePanel}
          id="report-panel-clicheria"
        >
          <KpiGrid>
            <KpiCard
              label="Recebidas no periodo"
              value={formatNum(data.indicadores.recebidas_no_periodo)}
            />
            <KpiCard
              label="Tempo medio aguardando"
              value={formatHoras(
                data.indicadores.tempo_medio_aguardando_recebimento_horas,
              )}
            />
            <KpiCard
              label="Em transito agora"
              value={formatNum(data.indicadores.em_transito_atual)}
            />
            <KpiCard
              label="Via PADRAO"
              value={formatNum(data.indicadores.por_origem_rota.via_padrao)}
            />
            <KpiCard
              label="Via DIRETA"
              value={formatNum(data.indicadores.por_origem_rota.via_direta)}
            />
          </KpiGrid>
        </section>
      );
  }
}

function KpiGrid({ children }: { children: React.ReactNode }) {
  return <div className={styles.kpiGrid}>{children}</div>;
}

function KpiCard({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.kpiCard}>
      <span className={styles.kpiLabel}>{label}</span>
      <span className={styles.kpiValue}>{value}</span>
    </div>
  );
}

// ─── Suspense wrapper (necessario para useSearchParams em Next 14) ────

export default function RelatoriosPage() {
  return (
    <Suspense fallback={<div className={styles.loadingState}>Carregando...</div>}>
      <RelatoriosContent />
    </Suspense>
  );
}
