"use client";

/**
 * Perspectiva Vendedores (Wave 5, Componente 16) — layout match design Mario.
 *
 * Estrutura:
 *
 *   Linha 1 (2 cards: 1fr 2.2fr):
 *     a) BLACK card "VENDEDORES FILIAL"
 *        - numero grande em amarelo accent (volume processado por filial)
 *        - caption "operando rota direta"
 *        - mini-stats grid 3 col no rodape: MATRIZ / ATIVOS / ATRASADAS
 *     b) WHITE card largo "Ranking por volume"
 *        - subtitle "QUEM MAIS MOVIMENTOU" + counter "N VENDEDORES"
 *        - lista com rank + nome + barra horizontal proporcional + valor
 *          (mesma estrutura .vendorRowItem do Geral)
 *
 *   Linha 2 (full-width):
 *     c) WHITE card "Detalhamento"
 *        - subtitle "APROVACAO · REPROVACAO · TEMPO"
 *        - tabela: VENDEDOR (avatar+nome) | LOCAL (pill) | APROV. (% verde) |
 *          REPROV. (% vermelho) | TEMPO | ATRAS.
 *        - top vendedor (idx=0) tem avatar amarelo, demais cinza
 *
 * Mapeamento de campos da API (`ReportResponseVendedores`):
 *   - "VENDEDORES FILIAL"/14 → distribuicao_localizacao.filial
 *   - "MATRIZ"/0 → distribuicao_localizacao.matriz
 *   - "ATIVOS"/2 → ranking.length
 *   - "ATRASADAS"/0 → soma de atrasadas_em_poder[].qtd_atrasadas
 */
import { motion } from "framer-motion";
import { useMemo } from "react";

import {
  formatHoras,
  formatNum,
  formatPct,
  type ReportResponseVendedores,
} from "@/lib/types/report";

import { EmptyState } from "../shared/EmptyState";
import styles from "../relatorios.module.css";

interface Props {
  data: ReportResponseVendedores;
}

/**
 * Extrai iniciais do nome do vendedor para o avatar do detalhamento.
 * Mantida em cada perspectiva (Geral/Vendedores) ao inves de extrair pra
 * compartilhada — escopo trivial, evita coupling cross-perspectiva.
 */
function getVendedorInitials(name: string): string {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function ReportVendedores({ data }: Props) {
  const totalAtivos = data.ranking.length;
  const totalAtrasadas = data.atrasadas_em_poder.reduce(
    (acc, v) => acc + v.qtd_atrasadas,
    0,
  );

  // Ranking ordenado por volume desc — backend ja retorna ordenado, mas
  // garantimos para nao depender da implementacao do agregador.
  const rankingByVolume = useMemo(
    () => [...data.ranking].sort((a, b) => b.volume - a.volume),
    [data.ranking],
  );
  const topVolume = rankingByVolume[0]?.volume ?? 0;

  return (
    <section
      className={styles.scopePanel}
      id="report-panel-vendedores"
      role="tabpanel"
      aria-labelledby="report-panel-vendedores"
    >
      {/* ─── Linha 1: BLACK card stats + Ranking por volume ───────────── */}
      <div className={styles.kpiRowVendedores}>
        {/* a) BLACK card — VENDEDORES FILIAL com mini-stats */}
        <motion.div
          className={`${styles.metricCard} ${styles.metricCardDark} ${styles.metricCardWithStats}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0 }}
        >
          <span className={styles.metricEyebrow}>VENDEDORES FILIAL</span>
          <span
            className={`${styles.metricValueLg} ${styles.metricValueAccent}`}
          >
            {formatNum(data.distribuicao_localizacao.filial)}
          </span>
          <span className={styles.metricCardCaption}>operando rota direta</span>

          <div className={styles.metricMiniStats}>
            <div className={styles.metricMiniStat}>
              <span className={styles.metricMiniStatLabel}>MATRIZ</span>
              <span className={styles.metricMiniStatValue}>
                {formatNum(data.distribuicao_localizacao.matriz)}
              </span>
            </div>
            <div className={styles.metricMiniStat}>
              <span className={styles.metricMiniStatLabel}>ATIVOS</span>
              <span className={styles.metricMiniStatValue}>
                {formatNum(totalAtivos)}
              </span>
            </div>
            <div className={styles.metricMiniStat}>
              <span className={styles.metricMiniStatLabel}>ATRASADAS</span>
              <span className={styles.metricMiniStatValue}>
                {formatNum(totalAtrasadas)}
              </span>
            </div>
          </div>
        </motion.div>

        {/* b) WHITE card largo — Ranking por volume */}
        <motion.div
          className={styles.rankingCard}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.05 }}
        >
          <header className={styles.rankingHeader}>
            <div className={styles.rankingHeaderTitleBlock}>
              <h2 className={styles.rankingTitle}>Ranking por volume</h2>
              <span className={styles.rankingSubtitle}>
                QUEM MAIS MOVIMENTOU
              </span>
            </div>
            <span className={styles.rankingCounter}>
              {totalAtivos}{" "}
              {totalAtivos === 1 ? "VENDEDOR" : "VENDEDORES"}
            </span>
          </header>

          {rankingByVolume.length === 0 ? (
            <EmptyState
              message="Sem vendedores no periodo."
              hint="Nenhum vendedor processou provas no periodo selecionado."
            />
          ) : (
            <ul className={styles.vendorRowList}>
              {rankingByVolume.map((v, idx) => {
                const pct = topVolume > 0 ? (v.volume / topVolume) * 100 : 0;
                return (
                  <motion.li
                    key={v.vendedor_id}
                    className={styles.vendorRowItem}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.2, delay: idx * 0.04 }}
                  >
                    <span className={styles.vendorRowRank}>
                      {String(idx + 1).padStart(2, "0")}
                    </span>
                    <span className={styles.vendorRowName}>
                      {v.vendedor_nome}
                    </span>
                    <span className={styles.vendorRowValue}>
                      {formatNum(v.volume)}
                    </span>
                    <div
                      className={styles.vendorRowBarTrack}
                      aria-hidden="true"
                    >
                      <div
                        className={styles.vendorRowBarFill}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </motion.li>
                );
              })}
            </ul>
          )}
        </motion.div>
      </div>

      {/* ─── Linha 2: Detalhamento (full-width) ────────────────────────── */}
      <div className={styles.rankingCard}>
        <header className={styles.rankingHeader}>
          <div className={styles.rankingHeaderTitleBlock}>
            <h2 className={styles.rankingTitle}>Detalhamento</h2>
            <span className={styles.rankingSubtitle}>
              APROVACAO · REPROVACAO · TEMPO
            </span>
          </div>
        </header>

        {rankingByVolume.length === 0 ? (
          <EmptyState message="Sem vendedores para detalhar neste periodo." />
        ) : (
          <div className={styles.rankingTableWrapper}>
            <table className={styles.rankingTable}>
              <caption className={styles.srOnly}>
                Detalhamento por vendedor: aprovacao, reprovacao, tempo medio
                e provas atrasadas em poder.
              </caption>
              <thead>
                <tr>
                  <th scope="col" className={styles.rankingTh}>
                    VENDEDOR
                  </th>
                  <th scope="col" className={styles.rankingTh}>
                    LOCAL
                  </th>
                  <th
                    scope="col"
                    className={`${styles.rankingTh} ${styles.rankingThNumeric}`}
                  >
                    APROV.
                  </th>
                  <th
                    scope="col"
                    className={`${styles.rankingTh} ${styles.rankingThNumeric}`}
                  >
                    REPROV.
                  </th>
                  <th
                    scope="col"
                    className={`${styles.rankingTh} ${styles.rankingThNumeric}`}
                  >
                    TEMPO
                  </th>
                  <th
                    scope="col"
                    className={`${styles.rankingTh} ${styles.rankingThNumeric}`}
                  >
                    ATRAS.
                  </th>
                </tr>
              </thead>
              <tbody>
                {rankingByVolume.map((v, idx) => {
                  const isTop = idx === 0;
                  const initials = getVendedorInitials(v.vendedor_nome);
                  const taxaAprov = v.taxa_aprovacao;
                  const taxaReprov = v.taxa_reprovacao;
                  return (
                    <motion.tr
                      key={v.vendedor_id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.2, delay: idx * 0.04 }}
                    >
                      <td className={styles.rankingTd}>
                        <div className={styles.rankingVendor}>
                          <span
                            className={
                              isTop
                                ? styles.rankingAvatarTop
                                : styles.rankingAvatar
                            }
                            aria-hidden="true"
                          >
                            {initials}
                          </span>
                          <span className={styles.rankingVendorName}>
                            {v.vendedor_nome}
                          </span>
                        </div>
                      </td>
                      <td className={styles.rankingTd}>
                        <span className={styles.rankingLocalPill}>
                          {v.localizacao === "MATRIZ" ? "Matriz" : "Filial"}
                        </span>
                      </td>
                      <td
                        className={`${styles.rankingTd} ${styles.rankingNumericCell}`}
                      >
                        <span
                          className={
                            taxaAprov > 0
                              ? styles.rankingAprovPctActive
                              : styles.rankingZeroValue
                          }
                        >
                          {formatPct(taxaAprov)}
                        </span>
                      </td>
                      <td
                        className={`${styles.rankingTd} ${styles.rankingNumericCell}`}
                      >
                        <span
                          className={
                            taxaReprov > 0
                              ? styles.rankingReprovHigh
                              : styles.rankingZeroValue
                          }
                        >
                          {formatPct(taxaReprov)}
                        </span>
                      </td>
                      <td
                        className={`${styles.rankingTd} ${styles.rankingNumericCell}`}
                      >
                        <span
                          className={
                            v.tempo_medio_retirada_a_decisao_horas !== null
                              ? styles.rankingTempoCell
                              : styles.rankingZeroValue
                          }
                        >
                          {formatHoras(
                            v.tempo_medio_retirada_a_decisao_horas,
                          )}
                        </span>
                      </td>
                      <td
                        className={`${styles.rankingTd} ${styles.rankingNumericCell}`}
                      >
                        <span
                          className={
                            v.provas_atrasadas_em_poder > 0
                              ? styles.rankingReprovHigh
                              : styles.rankingZeroValue
                          }
                        >
                          {formatNum(v.provas_atrasadas_em_poder)}
                        </span>
                      </td>
                    </motion.tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
