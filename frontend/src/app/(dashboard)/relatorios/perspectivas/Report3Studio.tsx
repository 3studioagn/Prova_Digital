"use client";

/**
 * Perspectiva 3Studio (Wave 5, Componente 16).
 *
 * Visao interna da operacao com 7 KPIs + lista de top motivos de cancelamento.
 * Foco em retrabalho (reinicios), responsabilidade (resposta) e
 * cancelamentos (volume + razoes).
 */
import {
  formatHoras,
  formatNum,
  type ReportResponse3Studio,
} from "@/lib/types/report";

import { BarChart } from "../shared/BarChart";
import { EmptyState } from "../shared/EmptyState";
import { KpiCard } from "../shared/KpiCard";
import styles from "../relatorios.module.css";

interface Props {
  data: ReportResponse3Studio;
}

export function Report3Studio({ data }: Props) {
  const ind = data.indicadores;

  const cancelamentosBars = data.cancelamentos_top.map((c) => ({
    label: c.motivo.length > 40 ? `${c.motivo.slice(0, 37)}...` : c.motivo,
    value: c.quantidade,
    color: "var(--color-danger, #ff5959)",
  }));

  return (
    <section
      className={styles.scopePanel}
      id="report-panel-3studio"
      role="tabpanel"
      aria-labelledby="report-panel-3studio"
    >
      <div className={styles.kpiGrid}>
        <KpiCard
          label="Provas criadas"
          value={formatNum(ind.provas_criadas)}
          hint="no periodo"
          delayIndex={0}
        />
        <KpiCard
          label="Media diaria"
          value={ind.media_diaria_criacao.toFixed(2)}
          hint="provas/dia"
          delayIndex={1}
        />
        <KpiCard
          label="Reinicios de ciclo"
          value={formatNum(ind.reinicios_de_ciclo)}
          hint="indica retrabalho (RN-006)"
          highlight={ind.reinicios_de_ciclo > 0 ? "warning" : "neutral"}
          delayIndex={2}
        />
        <KpiCard
          label="Devolvidas (motorista)"
          value={formatNum(ind.devolvidas_motorista)}
          hint="rota PADRAO"
          delayIndex={3}
        />
        <KpiCard
          label="Reprovadas aguardando"
          value={formatNum(ind.reprovadas_aguardando_acao)}
          hint="snapshot atual"
          highlight={ind.reprovadas_aguardando_acao > 0 ? "warning" : "neutral"}
          delayIndex={4}
        />
        <KpiCard
          label="Cancelamentos"
          value={formatNum(ind.cancelamentos)}
          hint="no periodo"
          delayIndex={5}
        />
        <KpiCard
          label="Tempo ate 1ª mov"
          value={formatHoras(ind.tempo_medio_criacao_ate_primeira_mov_horas)}
          hint="responsividade do vendedor"
          delayIndex={6}
        />
      </div>

      <div className={styles.chartsGrid}>
        <div className={styles.chartCard}>
          <h2 className={styles.chartTitle}>Top motivos de cancelamento</h2>
          {cancelamentosBars.length > 0 ? (
            <BarChart
              data={cancelamentosBars}
              ariaLabel="Top motivos de cancelamento ordenados por quantidade"
            />
          ) : (
            <EmptyState
              message="Sem cancelamentos no periodo."
              hint="Bom indicador — operacao sem retrabalho."
            />
          )}
        </div>
      </div>
    </section>
  );
}
