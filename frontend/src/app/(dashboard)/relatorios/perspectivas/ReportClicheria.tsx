"use client";

/**
 * Perspectiva Clicheria (Wave 5, Componente 16) — layout match design Mario.
 *
 * Estrutura:
 *
 *   Linha 1 (4 cards: 1.5fr 1fr 1fr 1fr):
 *     a) BLACK card "TEMPO MEDIO AGUARDANDO"
 *        - numero "X.Yh" (h em sub)
 *        - caption "envio → recebimento"
 *        - delta opcional "↘ X.X%" rosa + caption "melhor que o periodo
 *          anterior" — oculto enquanto backend nao retornar comparacao
 *     b) WHITE card "RECEBIDAS NO PERIODO"
 *        - numero grande em VERDE (success) se > 0; cinza opaco se 0
 *        - delta opcional "↗ X.X%" verde — oculto pelo mesmo motivo
 *     c) WHITE card "EM TRANSITO AGORA"
 *        - numero grande neutro
 *     d) WHITE card "ORIGENS"
 *        - numero grande (soma via_padrao + via_direta)
 *
 *   Linha 2 (2 cards: 1.8fr 1fr):
 *     e) WHITE card "Provas recebidas por rota de origem"
 *        - subtitle "DISTRIBUICAO" + counter "N PROVAS"
 *        - lista com label + barra horizontal azul + valor
 *     f) WHITE card "Fluxo de ciclo"
 *        - subtitle "ESTADO ATUAL"
 *        - lista 3 itens com bullets (preto solido se > 0, outline cinza
 *          se 0): Recebidas, Em transito, Total origens
 *
 * Limitacao honesta: deltas vs periodo anterior continuam ocultos pelo
 * mesmo motivo do scope=geral — backend nao retorna `delta_*`. Estrutura
 * pronta para receber quando os campos forem expostos.
 */
import { motion } from "framer-motion";
import { useMemo } from "react";

import {
  formatHoras,
  formatNum,
  type ReportResponseClicheria,
} from "@/lib/types/report";

import { EmptyState } from "../shared/EmptyState";
import styles from "../relatorios.module.css";

interface Props {
  data: ReportResponseClicheria;
}

/**
 * Formata indicador numerico no padrao "X,Y" + sufixo subscrito.
 * Ex: 155.3 / "h" -> renderiza "155,3" grande + "h" pequeno.
 */
function splitValueAndUnit(formatted: string): { main: string; unit: string } {
  const match = formatted.match(/^([-\d.,]+)\s*(.*)$/);
  if (!match) return { main: formatted, unit: "" };
  return { main: match[1], unit: match[2] };
}

export function ReportClicheria({ data }: Props) {
  const ind = data.indicadores;

  // Total de origens (soma das 2 rotas) — usado no card 4 e no fluxo
  const totalOrigens =
    ind.por_origem_rota.via_padrao + ind.por_origem_rota.via_direta;

  // Distribuicao por rota de origem — filtra zeros, calcula proporcao
  // relativa ao top (top = 100%, demais escalam).
  const rotasOrigem = useMemo(() => {
    const entries: Array<{ key: string; label: string; value: number }> = [
      {
        key: "padrao",
        label: "Via PADRAO (motorista)",
        value: ind.por_origem_rota.via_padrao,
      },
      {
        key: "direta",
        label: "Via DIRETA (filial)",
        value: ind.por_origem_rota.via_direta,
      },
    ];
    const filtered = entries.filter((e) => e.value > 0);
    if (filtered.length === 0) {
      return [] as Array<{
        key: string;
        label: string;
        value: number;
        pct: number;
      }>;
    }
    const top = Math.max(...filtered.map((e) => e.value));
    return filtered.map((e) => ({
      ...e,
      pct: top > 0 ? (e.value / top) * 100 : 0,
    }));
  }, [ind.por_origem_rota]);

  // Tempo medio aguardando: separa main + unit (h em subscrito)
  const tempoFormatted = formatHoras(
    ind.tempo_medio_aguardando_recebimento_horas,
  );
  const tempoSplit = splitValueAndUnit(tempoFormatted);

  // Items do "Fluxo de ciclo" (ordem fixa: Recebidas → Em transito → Total)
  const fluxoItems = [
    { label: "Recebidas", value: ind.recebidas_no_periodo },
    { label: "Em transito", value: ind.em_transito_atual },
    { label: "Total origens", value: totalOrigens },
  ];

  return (
    <section
      className={styles.scopePanel}
      id="report-panel-clicheria"
      role="tabpanel"
      aria-labelledby="report-panel-clicheria"
    >
      {/* ─── Linha 1: 4 cards (1 black + 3 white) ─────────────────────── */}
      <div className={styles.kpiRowClicheria}>
        {/* a) BLACK card — TEMPO MEDIO AGUARDANDO */}
        <motion.div
          className={`${styles.metricCard} ${styles.metricCardDark}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0 }}
        >
          <span className={styles.metricEyebrow}>TEMPO MEDIO AGUARDANDO</span>
          <div className={styles.metricValueWithUnit}>
            <span className={styles.metricValueLg}>{tempoSplit.main}</span>
            {tempoSplit.unit && (
              <span className={styles.metricValueUnit}>{tempoSplit.unit}</span>
            )}
          </div>
          <span className={styles.metricCardCaption}>envio → recebimento</span>
          {/*
           * DeltaBadge oculto: backend nao retorna comparacao com periodo
           * anterior para tempo_medio_aguardando_recebimento_horas. Quando
           * exposto, posicionar aqui:
           *
           *   <DeltaBadge value={delta} tone="negative" onDarkSurface
           *     suffix="melhor que o periodo anterior" />
           */}
        </motion.div>

        {/* b) WHITE card — RECEBIDAS NO PERIODO (verde se > 0) */}
        <motion.div
          className={`${styles.metricCard} ${styles.metricCardLight} ${styles.metricCardCompact}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.04 }}
        >
          <div className={styles.metricHeader}>
            <span className={styles.metricEyebrow}>RECEBIDAS NO PERIODO</span>
            {/*
             * DeltaBadge oculto: backend nao retorna delta_recebidas.
             * Quando exposto: <DeltaBadge value={delta} tone="positive" />.
             */}
          </div>
          <span
            className={`${styles.metricValueLg} ${
              ind.recebidas_no_periodo > 0
                ? styles.metricValueSuccess
                : styles.metricValueZero
            }`}
          >
            {formatNum(ind.recebidas_no_periodo)}
          </span>
        </motion.div>

        {/* c) WHITE card — EM TRANSITO AGORA */}
        <motion.div
          className={`${styles.metricCard} ${styles.metricCardLight} ${styles.metricCardCompact}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.08 }}
        >
          <span className={styles.metricEyebrow}>EM TRANSITO AGORA</span>
          <span className={styles.metricValueLg}>
            {formatNum(ind.em_transito_atual)}
          </span>
        </motion.div>

        {/* d) WHITE card — ORIGENS */}
        <motion.div
          className={`${styles.metricCard} ${styles.metricCardLight} ${styles.metricCardCompact}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.12 }}
        >
          <span className={styles.metricEyebrow}>ORIGENS</span>
          <span className={styles.metricValueLg}>
            {formatNum(totalOrigens)}
          </span>
        </motion.div>
      </div>

      {/* ─── Linha 2: 2 cards (distribuicao + fluxo) ────────────────── */}
      <div className={styles.chartsRowClicheria}>
        {/* e) WHITE card — Provas recebidas por rota de origem */}
        <motion.div
          className={`${styles.metricCard} ${styles.metricCardLight} ${styles.metricCardMotivos}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.16 }}
        >
          <header className={styles.metricCardMotivosHeader}>
            <div className={styles.metricCardTitleBlock}>
              <h2 className={styles.metricCardTitle}>
                Provas recebidas por rota de origem
              </h2>
              <span className={styles.metricCardSubtitle}>DISTRIBUICAO</span>
            </div>
            <span className={styles.rankingCounter}>
              {totalOrigens} {totalOrigens === 1 ? "PROVA" : "PROVAS"}
            </span>
          </header>

          {rotasOrigem.length === 0 ? (
            <EmptyState
              message="Nenhuma prova recebida no periodo."
              hint="Sem dados para distribuir entre as rotas."
            />
          ) : (
            <ul className={styles.distRotaList}>
              {rotasOrigem.map((r, idx) => (
                <motion.li
                  key={r.key}
                  className={styles.distRotaItem}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.2, delay: idx * 0.04 }}
                >
                  <span className={styles.distRotaLabel}>{r.label}</span>
                  <div
                    className={styles.distRotaBarTrack}
                    aria-hidden="true"
                  >
                    <div
                      className={styles.distRotaBarFill}
                      style={{ width: `${r.pct}%` }}
                    />
                  </div>
                  <span className={styles.distRotaValue}>
                    {formatNum(r.value)}
                  </span>
                </motion.li>
              ))}
            </ul>
          )}
        </motion.div>

        {/* f) WHITE card — Fluxo de ciclo */}
        <motion.div
          className={`${styles.metricCard} ${styles.metricCardLight} ${styles.metricCardFluxo}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.2 }}
        >
          <header className={styles.metricCardMotivosHeader}>
            <div className={styles.metricCardTitleBlock}>
              <h2 className={styles.metricCardTitle}>Fluxo de ciclo</h2>
              <span className={styles.metricCardSubtitle}>ESTADO ATUAL</span>
            </div>
          </header>

          <ul className={styles.fluxoCicloList}>
            {fluxoItems.map((item, idx) => (
              <motion.li
                key={item.label}
                className={
                  item.value > 0
                    ? styles.fluxoCicloItemActive
                    : styles.fluxoCicloItemMuted
                }
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.2, delay: idx * 0.04 }}
              >
                <span className={styles.fluxoCicloDot} aria-hidden="true" />
                <span className={styles.fluxoCicloLabel}>{item.label}</span>
                <span className={styles.fluxoCicloValue}>
                  {formatNum(item.value)}
                </span>
              </motion.li>
            ))}
          </ul>
        </motion.div>
      </div>
    </section>
  );
}
