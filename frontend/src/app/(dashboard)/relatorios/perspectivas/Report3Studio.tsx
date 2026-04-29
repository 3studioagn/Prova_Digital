"use client";

/**
 * Perspectiva 3Studio (Wave 5, Componente 16) — layout match design Mario.
 *
 * Estrutura em duas linhas-grade alinhadas ao design:
 *
 *   Linha 1 (4 cards iguais ao Geral em proporcao 1.5/1/1/0.65):
 *     a) BLACK card "PROVAS CRIADAS"
 *        - numero grande do total criado no periodo
 *        - caption "X.XX media diaria · N dias"
 *        - sparkline com a serie diaria real (mesma do scope=geral)
 *     b) WHITE card "REINICIOS CICLO"
 *        - numero grande, cor warning (vermelha) se > 0
 *     c) WHITE card "DEVOLVIDAS"
 *        - numero grande, cor neutra
 *     d) WHITE card "CANCEL." (mais estreito)
 *        - numero grande, cor warning se > 0
 *
 *   Linha 2 (3 cards: 1fr 1fr 2.4fr):
 *     e) WHITE card "REPROV. AGUARDANDO"
 *        - numero grande warning se > 0
 *     f) WHITE card "TEMPO ATE 1ª MOV."
 *        - numero "X.Xh" (h em sub)
 *        - delta opcional (oculto: sem comparacao historica disponivel)
 *     g) WHITE card "Top motivos de cancelamento" (largo)
 *        - subtitle "DIAGNOSTICO DO PERIODO" + counter "N CASOS" no header
 *        - lista top 5 motivos com barra horizontal proporcional ao top
 *        - top vermelho intenso, demais rosa claro
 *
 * Limitacao honesta:
 *   - Delta no card "TEMPO ATE 1ª MOV." continua oculto — backend ainda
 *     nao retorna comparacao com periodo anterior para esse indicador.
 */
import { motion } from "framer-motion";
import { useMemo } from "react";

import {
  formatHoras,
  formatNum,
  type ReportResponse3Studio,
} from "@/lib/types/report";

import { EmptyState } from "../shared/EmptyState";
import { Sparkline } from "../shared/Sparkline";
import styles from "../relatorios.module.css";

interface Props {
  data: ReportResponse3Studio;
}

/**
 * Formata indicador numerico no padrao "X,Y" + sufixo subscrito.
 * Ex: 53.2 / "h" -> renderiza "53,2" grande + "h" pequeno.
 */
function splitValueAndUnit(formatted: string): { main: string; unit: string } {
  const match = formatted.match(/^([-\d.,]+)\s*(.*)$/);
  if (!match) return { main: formatted, unit: "" };
  return { main: match[1], unit: match[2] };
}


export function Report3Studio({ data }: Props) {
  const ind = data.indicadores;
  const totalDias = data.periodo.total_dias;

  // Top motivos de cancelamento: ordena desc, limita a 5, calcula
  // proporcao relativa ao top (top = 100%, demais escalam).
  const motivosTop = useMemo(() => {
    if (data.cancelamentos_top.length === 0) {
      return [] as Array<{ motivo: string; quantidade: number; pct: number }>;
    }
    const sorted = [...data.cancelamentos_top].sort(
      (a, b) => b.quantidade - a.quantidade,
    );
    const limited = sorted.slice(0, 5);
    const top = limited[0].quantidade;
    return limited.map((c) => ({
      motivo: c.motivo,
      quantidade: c.quantidade,
      pct: top > 0 ? (c.quantidade / top) * 100 : 0,
    }));
  }, [data.cancelamentos_top]);

  // Total de casos (soma das quantidades de todos os motivos)
  const totalCasos = useMemo(
    () =>
      data.cancelamentos_top.reduce((acc, c) => acc + c.quantidade, 0),
    [data.cancelamentos_top],
  );

  // Tempo ate 1ª mov formatado e separado em main + unit
  const tempoFormatted = formatHoras(
    ind.tempo_medio_criacao_ate_primeira_mov_horas,
  );
  const tempoSplit = splitValueAndUnit(tempoFormatted);

  // Sparkline do card PROVAS CRIADAS — serie real do backend (mesma
  // origem do scope=geral). Garante que dois cards com o mesmo total
  // mostram a mesma forma de grafico.
  const sparklineSerie = useMemo(
    () => data.serie_temporal.map((p) => p.quantidade),
    [data.serie_temporal],
  );

  return (
    <section
      className={styles.scopePanel}
      id="report-panel-3studio"
      role="tabpanel"
      aria-labelledby="report-panel-3studio"
    >
      {/* ─── Linha 1: 4 cards (1 black + 3 white) ───────────────────── */}
      <div className={styles.kpiRow3Studio}>
        {/* a) BLACK card — PROVAS CRIADAS */}
        <motion.div
          className={`${styles.metricCard} ${styles.metricCardDark}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0 }}
        >
          <span className={styles.metricEyebrow}>PROVAS CRIADAS</span>
          <span className={styles.metricValueLg}>
            {formatNum(ind.provas_criadas)}
          </span>
          <span className={styles.metricCardCaption}>
            {ind.media_diaria_criacao.toFixed(2).replace(".", ",")} media
            diaria · {totalDias} {totalDias === 1 ? "dia" : "dias"}
          </span>
          {sparklineSerie.length >= 2 && (
            <div className={styles.metricSparkline}>
              <Sparkline points={sparklineSerie} />
            </div>
          )}
        </motion.div>

        {/* b) WHITE card — REINICIOS CICLO (warning se > 0) */}
        <motion.div
          className={`${styles.metricCard} ${styles.metricCardLight} ${styles.metricCardCompact}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.04 }}
        >
          <span className={styles.metricEyebrow}>REINICIOS CICLO</span>
          <span
            className={`${styles.metricValueLg} ${
              ind.reinicios_de_ciclo > 0 ? styles.metricValueWarning : ""
            }`}
          >
            {formatNum(ind.reinicios_de_ciclo)}
          </span>
        </motion.div>

        {/* c) WHITE card — DEVOLVIDAS (cor neutra) */}
        <motion.div
          className={`${styles.metricCard} ${styles.metricCardLight} ${styles.metricCardCompact}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.08 }}
        >
          <span className={styles.metricEyebrow}>DEVOLVIDAS</span>
          <span className={styles.metricValueLg}>
            {formatNum(ind.devolvidas_motorista)}
          </span>
        </motion.div>

        {/* d) WHITE card — CANCEL. (estreito; warning se > 0) */}
        <motion.div
          className={`${styles.metricCard} ${styles.metricCardLight} ${styles.metricCardCompact}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.12 }}
        >
          <span className={styles.metricEyebrow}>CANCEL.</span>
          <span
            className={`${styles.metricValueLg} ${
              ind.cancelamentos > 0 ? styles.metricValueWarning : ""
            }`}
          >
            {formatNum(ind.cancelamentos)}
          </span>
        </motion.div>
      </div>

      {/* ─── Linha 2: 3 cards (2 simples + Top motivos largo) ───────── */}
      <div className={styles.chartsRow3Studio}>
        {/* e) WHITE card — REPROV. AGUARDANDO */}
        <motion.div
          className={`${styles.metricCard} ${styles.metricCardLight} ${styles.metricCardCompact}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.16 }}
        >
          <span className={styles.metricEyebrow}>REPROV. AGUARDANDO</span>
          <span
            className={`${styles.metricValueLg} ${
              ind.reprovadas_aguardando_acao > 0
                ? styles.metricValueWarning
                : ""
            }`}
          >
            {formatNum(ind.reprovadas_aguardando_acao)}
          </span>
        </motion.div>

        {/* f) WHITE card — TEMPO ATE 1ª MOV. */}
        <motion.div
          className={`${styles.metricCard} ${styles.metricCardLight} ${styles.metricCardCompact}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.2 }}
        >
          <div className={styles.metricHeader}>
            <span className={styles.metricEyebrow}>TEMPO ATE 1ª MOV.</span>
            {/*
             * DeltaBadge ocultado: o backend nao retorna comparacao
             * historica para tempo_medio_criacao_ate_primeira_mov_horas.
             * Estrutura pronta — quando expor delta, adicione aqui:
             *
             *   <DeltaBadge value={delta} tone="negative" />
             */}
          </div>
          <div className={styles.metricValueWithUnit}>
            <span className={styles.metricValueLg}>{tempoSplit.main}</span>
            {tempoSplit.unit && (
              <span className={styles.metricValueUnit}>{tempoSplit.unit}</span>
            )}
          </div>
        </motion.div>

        {/* g) WHITE card largo — Top motivos de cancelamento */}
        <motion.div
          className={`${styles.metricCard} ${styles.metricCardLight} ${styles.metricCardMotivos}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.24 }}
        >
          <header className={styles.metricCardMotivosHeader}>
            <div className={styles.metricCardTitleBlock}>
              <h2 className={styles.metricCardTitle}>
                Top motivos de cancelamento
              </h2>
              <span className={styles.metricCardSubtitle}>
                DIAGNOSTICO DO PERIODO
              </span>
            </div>
            <span className={styles.rankingCounter}>
              {totalCasos} {totalCasos === 1 ? "CASO" : "CASOS"}
            </span>
          </header>

          {motivosTop.length === 0 ? (
            <EmptyState
              message="Sem cancelamentos no periodo."
              hint="Bom indicador — operacao sem retrabalho."
            />
          ) : (
            <ul className={styles.cancelMotivosList}>
              {motivosTop.map((m, idx) => (
                <motion.li
                  key={m.motivo}
                  className={styles.cancelMotivoItem}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.2, delay: idx * 0.04 }}
                >
                  <span className={styles.cancelMotivoLabel}>{m.motivo}</span>
                  <div
                    className={styles.cancelMotivoBarTrack}
                    aria-hidden="true"
                  >
                    <div
                      className={`${styles.cancelMotivoBarFill} ${
                        idx === 0 ? styles.cancelMotivoBarFillTop : ""
                      }`}
                      style={{ width: `${m.pct}%` }}
                    />
                  </div>
                  <span className={styles.cancelMotivoValue}>
                    {formatNum(m.quantidade)}
                  </span>
                </motion.li>
              ))}
            </ul>
          )}
        </motion.div>
      </div>
    </section>
  );
}
