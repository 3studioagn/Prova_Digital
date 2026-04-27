"use client";

/**
 * Perspectiva Clicheria (Wave 5, Componente 16).
 *
 * Visao produtiva da clicheria: 4 KPIs + grafico de distribuicao por
 * origem de rota (PADRAO via motorista vs DIRETA do vendedor filial).
 */
import {
  formatHoras,
  formatNum,
  type ReportResponseClicheria,
} from "@/lib/types/report";

import { BarChart } from "../shared/BarChart";
import { EmptyState } from "../shared/EmptyState";
import { KpiCard } from "../shared/KpiCard";
import styles from "../relatorios.module.css";

interface Props {
  data: ReportResponseClicheria;
}

export function ReportClicheria({ data }: Props) {
  const ind = data.indicadores;

  const origemBars = [
    {
      label: "Via PADRAO (motorista)",
      value: ind.por_origem_rota.via_padrao,
      color: "var(--color-accent, #ffcb5c)",
    },
    {
      label: "Via DIRETA (filial)",
      value: ind.por_origem_rota.via_direta,
      color: "#5cb8ff",
    },
  ].filter((b) => b.value > 0);

  return (
    <section
      className={styles.scopePanel}
      id="report-panel-clicheria"
      role="tabpanel"
      aria-labelledby="report-panel-clicheria"
    >
      <div className={styles.kpiGrid}>
        <KpiCard
          label="Recebidas no periodo"
          value={formatNum(ind.recebidas_no_periodo)}
          hint="ciclo concluido"
          highlight={ind.recebidas_no_periodo > 0 ? "success" : "neutral"}
          delayIndex={0}
        />
        <KpiCard
          label="Tempo medio aguardando"
          value={formatHoras(ind.tempo_medio_aguardando_recebimento_horas)}
          hint="envio -> recebimento"
          delayIndex={1}
        />
        <KpiCard
          label="Em transito agora"
          value={formatNum(ind.em_transito_atual)}
          hint="motorista + clicheria"
          delayIndex={2}
        />
        <KpiCard
          label="Total origens"
          value={formatNum(
            ind.por_origem_rota.via_padrao + ind.por_origem_rota.via_direta,
          )}
          hint="recebidas no periodo"
          delayIndex={3}
        />
      </div>

      <div className={styles.chartsGrid}>
        <div className={styles.chartCard}>
          <h2 className={styles.chartTitle}>Provas recebidas por rota de origem</h2>
          {origemBars.length > 0 ? (
            <BarChart
              data={origemBars}
              ariaLabel="Provas recebidas pela clicheria agrupadas por rota de origem"
            />
          ) : (
            <EmptyState message="Nenhuma prova recebida no periodo." />
          )}
        </div>
      </div>
    </section>
  );
}
