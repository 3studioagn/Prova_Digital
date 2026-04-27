"use client";

/**
 * Perspectiva Vendedores (Wave 5, Componente 16).
 *
 * Tabela completa de ranking + lista de atrasadas em poder + KPIs de
 * distribuicao por localizacao. Permite acompanhar performance comercial
 * e identificar gargalos por vendedor.
 */
import { motion } from "framer-motion";

import {
  formatHoras,
  formatNum,
  formatPct,
  type ReportResponseVendedores,
} from "@/lib/types/report";

import { EmptyState } from "../shared/EmptyState";
import { KpiCard } from "../shared/KpiCard";
import styles from "../relatorios.module.css";

interface Props {
  data: ReportResponseVendedores;
}

export function ReportVendedores({ data }: Props) {
  const totalVendedoresRanking = data.ranking.length;
  const totalAtrasadas = data.atrasadas_em_poder.reduce(
    (acc, v) => acc + v.qtd_atrasadas,
    0,
  );

  return (
    <section
      className={styles.scopePanel}
      id="report-panel-vendedores"
      role="tabpanel"
      aria-labelledby="report-panel-vendedores"
    >
      <div className={styles.kpiGrid}>
        <KpiCard
          label="Vendedores Matriz"
          value={formatNum(data.distribuicao_localizacao.matriz)}
          hint="provas processadas"
          delayIndex={0}
        />
        <KpiCard
          label="Vendedores Filial"
          value={formatNum(data.distribuicao_localizacao.filial)}
          hint="rota direta"
          delayIndex={1}
        />
        <KpiCard
          label="Vendedores ativos"
          value={formatNum(totalVendedoresRanking)}
          hint="no ranking"
          delayIndex={2}
        />
        <KpiCard
          label="Atrasadas em poder"
          value={formatNum(totalAtrasadas)}
          hint="snapshot atual"
          highlight={totalAtrasadas > 0 ? "warning" : "neutral"}
          delayIndex={3}
        />
      </div>

      <div className={styles.tableCard}>
        <h2 className={styles.chartTitle}>Ranking por volume</h2>
        {data.ranking.length === 0 ? (
          <EmptyState message="Sem vendedores no ranking para o periodo selecionado." />
        ) : (
          <div className={styles.tableWrapper}>
            <table className={styles.dataTable}>
              <caption className={styles.srOnly}>
                Ranking de vendedores ordenado por volume de provas processadas
                no periodo
              </caption>
              <thead>
                <tr>
                  <th scope="col">Vendedor</th>
                  <th scope="col">Local</th>
                  <th scope="col" className={styles.tableNumeric}>Volume</th>
                  <th scope="col" className={styles.tableNumeric}>Aprovacao</th>
                  <th scope="col" className={styles.tableNumeric}>Reprovacao</th>
                  <th scope="col" className={styles.tableNumeric}>Tempo medio</th>
                  <th scope="col" className={styles.tableNumeric}>Atrasadas</th>
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
                    <td className={styles.tableNumeric}>
                      {formatNum(v.volume)}
                    </td>
                    <td className={styles.tableNumeric}>
                      {formatPct(v.taxa_aprovacao)}
                    </td>
                    <td className={styles.tableNumeric}>
                      {formatPct(v.taxa_reprovacao)}
                    </td>
                    <td className={styles.tableNumeric}>
                      {formatHoras(v.tempo_medio_retirada_a_decisao_horas)}
                    </td>
                    <td
                      className={
                        v.provas_atrasadas_em_poder > 0
                          ? `${styles.tableNumeric} ${styles.tableWarn}`
                          : styles.tableNumeric
                      }
                    >
                      {formatNum(v.provas_atrasadas_em_poder)}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className={styles.tableCard}>
        <h2 className={styles.chartTitle}>Atrasadas em poder de vendedores</h2>
        {data.atrasadas_em_poder.length === 0 ? (
          <EmptyState
            message="Nenhum vendedor com provas atrasadas."
            hint="Todas as provas em poder dos vendedores estao dentro do prazo."
          />
        ) : (
          <ul className={styles.atrasadasList}>
            {data.atrasadas_em_poder.map((v) => (
              <li key={v.vendedor_id} className={styles.atrasadasItem}>
                <span className={styles.atrasadasNome}>{v.vendedor_nome}</span>
                <span className={styles.atrasadasMeta}>
                  {v.localizacao === "MATRIZ" ? "Matriz" : "Filial"}
                </span>
                <span className={styles.atrasadasContador}>
                  {v.qtd_atrasadas}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
