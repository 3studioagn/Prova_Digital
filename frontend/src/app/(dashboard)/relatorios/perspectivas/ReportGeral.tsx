"use client";

/**
 * Perspectiva Geral (Wave 5, Componente 16) — layout match Figma/Mario.
 *
 * Estrutura:
 *   - Linha 1: 4 KPIs simples (Total geral, Tempo medio aprovacao,
 *     Taxa reprovacao geral, Distribuicao por rota)
 *   - Linha 2: 3 cards de chart
 *       a) Donut "Provas Ativas" — distribuicao por status nao-terminal
 *          (interativo: hover destaca + click filtra status no relatorio)
 *       b) BarChart horizontal "Tempo Medio de Aprovacao" — por vendedor
 *       c) BarChart horizontal "Vendedor com Mais Artes" — ranking volume
 *   - Linha 3: tabela "Metricas por Vendedor" full-width
 *   - Linha 4: lista "Provas Atrasadas (N)" full-width
 *
 * Click em segmento do Donut chama `onStatusClick(status)` — page.tsx
 * faz `setFilter("status", status)` (decisao Mario opcao C: filtra dentro
 * do proprio relatorio, nao navega).
 */
import { motion } from "framer-motion";

import {
  formatHoras,
  formatNum,
  formatPct,
  type ReportResponseGeral,
} from "@/lib/types/report";
import { STATUS_LABELS, type StatusProva } from "@/lib/types/prova";

import { BarChart } from "../shared/BarChart";
import { DonutChart } from "../shared/DonutChart";
import { EmptyState } from "../shared/EmptyState";
import { KpiCard } from "../shared/KpiCard";
import styles from "../relatorios.module.css";

interface Props {
  data: ReportResponseGeral;
  /** Caller filtra o relatorio quando segmento do Donut e clicado. */
  onStatusClick?: (status: StatusProva) => void;
}

// Status que contam como "ativo" (nao-terminal) no donut "Provas Ativas".
// CANCELADA e RECEBIDA_PELA_CLICHERIA sao terminais — fora.
const STATUS_ATIVOS_SET = new Set<StatusProva>([
  "CRIADA",
  "RETIRADA_PELO_VENDEDOR",
  "APROVADA_PELO_VENDEDOR",
  "DE_VOLTA_3STUDIO",
  "COM_MOTORISTA",
  "ENVIADA_PARA_CLICHERIA",
  "ENCAMINHADA_A_CLICHERIA",
  "REPROVADA_PELO_VENDEDOR",
]);

export function ReportGeral({ data, onStatusClick }: Props) {
  const ind = data.indicadores;

  // Distribuicao por rota como string inline ("Padrao: 2 | Direta: 3")
  const padraoCount =
    data.distribuicao_rota.find((d) => d.rota === "PADRAO")?.quantidade ?? 0;
  const diretaCount =
    data.distribuicao_rota.find((d) => d.rota === "DIRETA")?.quantidade ?? 0;
  const rotaText = `Padrao: ${padraoCount} | Direta: ${diretaCount}`;

  // Donut "Provas Ativas": filtra status nao-terminal
  const ativosData = data.distribuicao_status
    .filter((d) => STATUS_ATIVOS_SET.has(d.status))
    .map((d) => ({
      label: STATUS_LABELS[d.status],
      value: d.quantidade,
      key: d.status,
    }));

  // BarChart "Tempo Medio de Aprovacao" — por vendedor (horas)
  const tempoMedioBars = data.ranking
    .filter((v) => v.tempo_medio_retirada_a_decisao_horas !== null)
    .map((v) => ({
      label: v.vendedor_nome,
      value: v.tempo_medio_retirada_a_decisao_horas as number,
      key: v.vendedor_id,
    }))
    .sort((a, b) => b.value - a.value);

  // BarChart "Vendedor com Mais Artes" — ranking volume
  const volumeBars = data.ranking
    .filter((v) => v.volume > 0)
    .map((v) => ({
      label: v.vendedor_nome,
      value: v.volume,
      key: v.vendedor_id,
      color: "#ff8a3d", // laranja diferente do amarelo do tempo medio
    }));

  return (
    <section
      className={styles.scopePanel}
      id="report-panel-geral"
      role="tabpanel"
      aria-labelledby="report-panel-geral"
    >
      {/* Linha 1: 4 KPIs */}
      <div className={styles.kpiRowGeral}>
        <KpiCard
          label="Total geral"
          value={formatNum(ind.total_provas)}
          delayIndex={0}
        />
        <KpiCard
          label="Tempo medio aprovacao"
          value={formatHoras(ind.tempo_medio_aprovacao_horas)}
          delayIndex={1}
        />
        <KpiCard
          label="Taxa reprovacao geral"
          value={formatPct(ind.taxa_reprovacao)}
          highlight={ind.taxa_reprovacao > 0.2 ? "warning" : "neutral"}
          delayIndex={2}
        />
        <KpiCard
          label="Distribuicao por rota"
          value={rotaText}
          delayIndex={3}
        />
      </div>

      {/* Linha 2: 3 cards de chart */}
      <div className={styles.chartsRowGeral}>
        <div className={styles.chartCard}>
          <h2 className={styles.chartTitle}>Provas Ativas</h2>
          {ativosData.length > 0 ? (
            <DonutChart
              data={ativosData}
              ariaLabel="Distribuicao de provas ativas (nao-terminais) por status"
              onSegmentClick={(key) => onStatusClick?.(key as StatusProva)}
              centerHint="ativas"
            />
          ) : (
            <EmptyState
              message="Nenhuma prova ativa."
              hint="Todas as provas estao em estados terminais."
            />
          )}
        </div>

        <div className={styles.chartCard}>
          <h2 className={styles.chartTitle}>Tempo Medio de Aprovacao</h2>
          {tempoMedioBars.length > 0 ? (
            <BarChart
              data={tempoMedioBars}
              ariaLabel="Tempo medio de aprovacao por vendedor (horas corridas)"
              formatValue={(v) => `${v.toFixed(1)}h`}
            />
          ) : (
            <EmptyState
              message="Sem decisoes no periodo."
              hint="Nenhum vendedor decidiu prova ainda."
            />
          )}
        </div>

        <div className={styles.chartCard}>
          <h2 className={styles.chartTitle}>Vendedor com Mais Artes</h2>
          {volumeBars.length > 0 ? (
            <BarChart
              data={volumeBars}
              ariaLabel="Ranking de vendedores por volume de provas no periodo"
            />
          ) : (
            <EmptyState message="Nenhum vendedor processou provas no periodo." />
          )}
        </div>
      </div>

      {/* Linha 3: Tabela Metricas por Vendedor */}
      <div className={styles.tableCard}>
        <h2 className={styles.chartTitle}>Metricas por Vendedor</h2>
        {data.ranking.length === 0 ? (
          <EmptyState message="Nenhum vendedor no ranking para este periodo." />
        ) : (
          <div className={styles.tableWrapper}>
            <table className={styles.dataTable}>
              <caption className={styles.srOnly}>
                Metricas por vendedor: total, aprovadas, reprovadas, taxa de
                reprovacao e tempo medio.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Vendedor</th>
                  <th scope="col">Localizacao</th>
                  <th scope="col" className={styles.tableNumeric}>Total</th>
                  <th scope="col" className={styles.tableNumeric}>Aprovadas</th>
                  <th scope="col" className={styles.tableNumeric}>Reprovadas</th>
                  <th scope="col" className={styles.tableNumeric}>Taxa Rep. %</th>
                  <th scope="col" className={styles.tableNumeric}>Tempo Medio</th>
                </tr>
              </thead>
              <tbody>
                {data.ranking.map((v, index) => (
                  <motion.tr
                    key={v.vendedor_id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.2, delay: index * 0.02 }}
                  >
                    <td>{v.vendedor_nome}</td>
                    <td>
                      <span
                        className={
                          v.localizacao === "MATRIZ"
                            ? styles.localizacaoBadgeMatriz
                            : styles.localizacaoBadgeFilial
                        }
                      >
                        {v.localizacao === "MATRIZ" ? "Matriz" : "Filial"}
                      </span>
                    </td>
                    <td className={styles.tableNumeric}>{formatNum(v.volume)}</td>
                    <td className={styles.tableNumeric}>{formatNum(v.aprovacoes)}</td>
                    <td className={styles.tableNumeric}>{formatNum(v.reprovacoes)}</td>
                    <td className={styles.tableNumeric}>
                      {formatPct(v.taxa_reprovacao)}
                    </td>
                    <td className={styles.tableNumeric}>
                      {formatHoras(v.tempo_medio_retirada_a_decisao_horas)}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Linha 4: Lista Provas Atrasadas */}
      <div className={styles.tableCard}>
        <h2 className={styles.chartTitle}>
          Provas Atrasadas{" "}
          <span className={styles.atrasadasCount}>
            ({data.provas_atrasadas_total})
          </span>
        </h2>
        {data.provas_atrasadas.length === 0 ? (
          <EmptyState
            message="Nenhuma prova atrasada."
            hint="Todas as provas ativas estao dentro do prazo configurado."
          />
        ) : (
          <ul className={styles.atrasadasProvasList}>
            {data.provas_atrasadas.map((p, index) => (
              <motion.li
                key={p.id}
                className={styles.atrasadasProvaItem}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2, delay: index * 0.02 }}
              >
                <div className={styles.atrasadasProvaInfo}>
                  <span className={styles.atrasadasProvaNome}>{p.nome}</span>
                  <span className={styles.atrasadasProvaMeta}>
                    {p.nro_requerimento} · {p.cliente} · {p.vendedor_nome}
                  </span>
                </div>
                <div className={styles.atrasadasProvaStatus}>
                  {STATUS_LABELS[p.status]}
                </div>
                <div className={styles.atrasadasProvaTempo}>
                  {p.horas_atrasada.toFixed(1)}h
                </div>
              </motion.li>
            ))}
            {data.provas_atrasadas_total > data.provas_atrasadas.length && (
              <li className={styles.atrasadasFooter}>
                + {data.provas_atrasadas_total - data.provas_atrasadas.length}{" "}
                provas atrasadas adicionais. Use a exportacao CSV (dataset
                &quot;overdue&quot;) para a lista completa.
              </li>
            )}
          </ul>
        )}
      </div>
    </section>
  );
}
