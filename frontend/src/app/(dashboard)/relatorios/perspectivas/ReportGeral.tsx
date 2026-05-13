"use client";

/**
 * Perspectiva Geral (Wave 5, Componente 16) — layout match design Mario.
 *
 * Estrutura em duas linhas-grade alinhadas ao Figma do Mario:
 *
 *   Linha 1 (4 cards iguais):
 *     a) BLACK card "TOTAL GERAL · {N} DIAS"
 *        - numero grande do total de provas
 *        - sparkline amarela (serie_temporal)
 *        - delta opcional (computado das metades da serie_temporal)
 *     b) WHITE card "TEMPO MEDIO APROV."
 *        - numero grande em horas
 *        - delta opcional
 *     c) WHITE card "TAXA REPROVACAO"
 *        - numero grande vermelho
 *        - delta opcional
 *     d) WHITE card "ROTA"
 *        - legenda Padrao (preto) + Direta (amarelo)
 *
 *   Linha 2 (3 cards iguais):
 *     e) WHITE card "Provas ativas" / "ESTADO ATUAL"
 *        - DonutChart compacto + center text "{n} ATIVAS"
 *        - click em segmento filtra status (mantem comportamento Wave 5.4)
 *     f) WHITE card "Tempo medio de aprovacao" / "POR VENDEDOR"
 *        - top 1 vendedor com barra horizontal de tempo
 *     g) BLACK card "VENDEDOR COM MAIS ARTES"
 *        - nome do top vendedor + numero grande + sparkline amarela
 *
 * Mantemos abaixo (fora do print do Mario, mas presentes na funcionalidade
 * atual) a tabela "Metricas por Vendedor" e a lista "Provas Atrasadas" da
 * Wave 5.3/5.4 — nao fazia sentido deletar agora sem confirmacao.
 *
 * Sobre deltas vs periodo anterior:
 * O backend nao retorna ainda comparacao com janela anterior. Computamos
 * uma proxy honesta para o card TOTAL GERAL via metades da `serie_temporal`
 * (1a metade do periodo vs 2a metade). Para tempo_medio e taxa_reprovacao
 * nao ha serie diaria desses indicadores, entao os badges ficam ocultos ate
 * o backend retornar `delta_*` ou um indicador comparativo.
 */
import { motion } from "framer-motion";
import { useMemo } from "react";

import {
  formatHoras,
  formatNum,
  formatPct,
  type PontoSerie,
  type ReportResponseGeral,
} from "@/lib/types/report";
import { STATUS_LABELS, type StatusProva } from "@/lib/types/prova";

import { DeltaBadge } from "../shared/DeltaBadge";
import { DonutChart } from "../shared/DonutChart";
import { EmptyState } from "../shared/EmptyState";
import { Sparkline } from "../shared/Sparkline";
import styles from "../relatorios.module.css";

interface Props {
  data: ReportResponseGeral;
  /** Status atualmente filtrado (vem da URL). Usado para detectar
   * toggle no donut — clicar no segmento que ja e o filtro ativo
   * remove o filtro (retorna ao estado multi-segmento). */
  statusFilter: StatusProva | null;
  /** Caller filtra/desfiltra. Recebe `null` quando o usuario clica no
   * segmento ja ativo (toggle off). */
  onStatusClick?: (status: StatusProva | null) => void;
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

/**
 * Paleta semantica por status para o donut "Provas Ativas".
 *
 * Status "primarios" (provas em andamento) usam tons amarelo/laranja —
 * variantes do accent — e os "stuck" (REPROVADA aguardando acao) usam
 * cinza claro. Mantém match com o design Mario.
 */
const STATUS_DONUT_COLOR: Record<StatusProva, string> = {
  // ── Legacy v3.0 ────────────────────────────────────────────────────────
  CRIADA: "var(--color-accent, #ffcb5c)",
  RETIRADA_PELO_VENDEDOR: "#ffd97a",
  APROVADA_PELO_VENDEDOR: "#f5b041",
  DE_VOLTA_3STUDIO: "#f1c40f",
  COM_MOTORISTA: "#ff8a3d",
  ENVIADA_PARA_CLICHERIA: "#e67e22",
  ENCAMINHADA_A_CLICHERIA: "#d35400",
  REPROVADA_PELO_VENDEDOR: "#d4d4d4",
  // Terminais (nao usados aqui mas mantemos a cobertura do enum):
  CANCELADA: "#9ca3af",
  RECEBIDA_PELA_CLICHERIA: "#34d399",
  // ── v4.0 (Wave 3 / Componente 11) — tons coerentes com os legacy ───────
  // Laminacao: variantes complementares (verde-amarelo) para distinguir
  // visualmente das etapas tradicionais sem destoar da paleta.
  ENCAMINHADA_PARA_LAMINACAO: "#c0ca33",
  COM_MOTORISTA_IDA_LAMINACAO: "#ffa726",
  LAMINACAO_CONCLUIDA: "#9ccc65",
  COM_MOTORISTA_VOLTA_LAMINACAO: "#ff9800",
  DE_VOLTA_3STUDIO_POS_LAMINACAO: "#fbc02d",
  // Vendedor Filial / Lam. Filial recebe direto
  ENCAMINHADA_PARA_O_VENDEDOR: "#ffe082",
  // Entrega final (motorista v4.0) - tom similar ao COM_MOTORISTA legacy
  COM_MOTORISTA_ENTREGA_FINAL: "#ff7043",
};

/**
 * Computa delta proxy para o TOTAL GERAL: (somaSegundaMetade - somaPrimeiraMetade) / somaPrimeiraMetade.
 * Retorna null se nao ha dados suficientes ou se a primeira metade e zero.
 */
function computeTotalDelta(serie: PontoSerie[]): number | null {
  if (serie.length < 4) return null;
  const half = Math.floor(serie.length / 2);
  const first = serie.slice(0, half).reduce((s, p) => s + p.quantidade, 0);
  const second = serie.slice(half).reduce((s, p) => s + p.quantidade, 0);
  if (first === 0) return null;
  return (second - first) / first;
}

/**
 * Formata indicador numerico no padrao "X,Y" + sufixo subscrito.
 * Ex: 62.1 / "h" -> renderiza "62,1" grande + "h" pequeno.
 */
function splitValueAndUnit(formatted: string): { main: string; unit: string } {
  // Encontra o primeiro caractere nao-digito/vírgula/ponto/sinal apos o numero
  const match = formatted.match(/^([-\d.,]+)\s*(.*)$/);
  if (!match) return { main: formatted, unit: "" };
  return { main: match[1], unit: match[2] };
}

/**
 * Extrai iniciais do nome do vendedor para exibir no avatar.
 * - "Mario Souza" -> "MS"
 * - "Andre" -> "AN"
 * - "" -> "?"
 */
function getVendedorInitials(name: string): string {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function ReportGeral({ data, statusFilter, onStatusClick }: Props) {
  const ind = data.indicadores;
  const totalDias = data.periodo.total_dias;

  // ─── Dados derivados ────────────────────────────────────────────────

  const padraoCount =
    data.distribuicao_rota.find((d) => d.rota === "PADRAO")?.quantidade ?? 0;
  const diretaCount =
    data.distribuicao_rota.find((d) => d.rota === "DIRETA")?.quantidade ?? 0;

  // Donut "Provas Ativas": filtra status nao-terminal e aplica cor por status.
  const ativosData = useMemo(
    () =>
      data.distribuicao_status
        .filter((d) => STATUS_ATIVOS_SET.has(d.status))
        .map((d) => ({
          label: STATUS_LABELS[d.status],
          value: d.quantidade,
          key: d.status,
          color: STATUS_DONUT_COLOR[d.status],
        })),
    [data.distribuicao_status],
  );

  const totalAtivas = useMemo(
    () => ativosData.reduce((acc, d) => acc + d.value, 0),
    [ativosData],
  );

  // Ranking de tempo medio de aprovacao (top 5 por tempo desc).
  // O #1 tem progressbar 100%; os demais sao proporcionais (valor / valor[0]).
  const tempoMedioRanking = useMemo(() => {
    const candidatos = data.ranking
      .filter((v) => v.tempo_medio_retirada_a_decisao_horas !== null)
      .map((v) => ({
        id: v.vendedor_id,
        nome: v.vendedor_nome,
        tempo: v.tempo_medio_retirada_a_decisao_horas as number,
      }))
      .sort((a, b) => b.tempo - a.tempo)
      .slice(0, 5);
    if (candidatos.length === 0) return [] as Array<{
      id: string;
      nome: string;
      tempo: number;
      pct: number;
    }>;
    const top = candidatos[0].tempo;
    return candidatos.map((c) => ({
      ...c,
      pct: top > 0 ? (c.tempo / top) * 100 : 0,
    }));
  }, [data.ranking]);

  // Ranking ordenado por volume desc (top no inicio).
  // Usado tanto pelo card "Vendedor com Mais Artes" quanto pela tabela
  // "Metricas por Vendedor" (que precisa do top para a barra proporcional).
  const rankingByVolume = useMemo(
    () => [...data.ranking].sort((a, b) => b.volume - a.volume),
    [data.ranking],
  );
  const topVolumeVendedor = rankingByVolume[0] ?? null;
  const topVolume = topVolumeVendedor?.volume ?? 0;

  // Sparkline serie - apenas quantidades, nao precisa de data aqui
  const sparklineSerie = useMemo(
    () => data.serie_temporal.map((p) => p.quantidade),
    [data.serie_temporal],
  );

  // Delta TOTAL GERAL (proxy): primeira metade vs segunda metade
  const totalDelta = useMemo(
    () => computeTotalDelta(data.serie_temporal),
    [data.serie_temporal],
  );

  // ─── Helpers de formatacao para os cards ────────────────────────────

  const tempoFormatted = formatHoras(ind.tempo_medio_aprovacao_horas);
  const tempoSplit = splitValueAndUnit(tempoFormatted);

  const taxaFormatted = formatPct(ind.taxa_reprovacao);
  const taxaSplit = splitValueAndUnit(taxaFormatted);

  return (
    <section
      className={styles.scopePanel}
      id="report-panel-geral"
      role="tabpanel"
      aria-labelledby="report-panel-geral"
    >
      {/* ─── Linha 1: 4 cards (1 black + 3 white) ─────────────────────── */}
      <div className={styles.kpiRowGeral}>
        {/* a) BLACK card — TOTAL GERAL · N DIAS */}
        <motion.div
          className={`${styles.metricCard} ${styles.metricCardDark}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0 }}
        >
          <span className={styles.metricEyebrow}>
            TOTAL GERAL · {totalDias} {totalDias === 1 ? "DIA" : "DIAS"}
          </span>
          <span className={styles.metricValueLg}>
            {formatNum(ind.total_provas)}
          </span>
          {totalDelta !== null && (
            <DeltaBadge
              value={totalDelta}
              tone={totalDelta >= 0 ? "positive" : "negative"}
              suffix="vs. periodo anterior"
              onDarkSurface
            />
          )}
          <div className={styles.metricSparkline}>
            <Sparkline points={sparklineSerie} />
          </div>
        </motion.div>

        {/* b) WHITE card — TEMPO MEDIO APROV. */}
        <motion.div
          className={`${styles.metricCard} ${styles.metricCardLight} ${styles.metricCardCompact}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.04 }}
        >
          <div className={styles.metricHeader}>
            <span className={styles.metricEyebrow}>TEMPO MEDIO APROV.</span>
          </div>
          <div className={styles.metricValueWithUnit}>
            <span className={styles.metricValueLg}>{tempoSplit.main}</span>
            {tempoSplit.unit && (
              <span className={styles.metricValueUnit}>{tempoSplit.unit}</span>
            )}
          </div>
        </motion.div>

        {/* c) WHITE card — TAXA REPROVACAO */}
        <motion.div
          className={`${styles.metricCard} ${styles.metricCardLight} ${styles.metricCardCompact}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.08 }}
        >
          <div className={styles.metricHeader}>
            <span className={styles.metricEyebrow}>TAXA REPROVACAO</span>
          </div>
          <div className={styles.metricValueWithUnit}>
            <span
              className={`${styles.metricValueLg} ${styles.metricValueDanger}`}
            >
              {taxaSplit.main}
            </span>
            {taxaSplit.unit && (
              <span
                className={`${styles.metricValueUnit} ${styles.metricValueUnitDanger}`}
              >
                {taxaSplit.unit}
              </span>
            )}
          </div>
        </motion.div>

        {/* d) WHITE card — ROTA */}
        <motion.div
          className={`${styles.metricCard} ${styles.metricCardLight} ${styles.metricCardRota}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.12 }}
        >
          <span className={styles.metricEyebrow}>ROTA</span>
          <ul className={styles.rotaLegend}>
            <li className={styles.rotaLegendItem}>
              <span
                className={`${styles.rotaDot} ${styles.rotaDotPadrao}`}
                aria-hidden="true"
              />
              <span className={styles.rotaLegendLabel}>Padrao</span>
              <span className={styles.rotaLegendValue}>{padraoCount}</span>
            </li>
            <li className={styles.rotaLegendItem}>
              <span
                className={`${styles.rotaDot} ${styles.rotaDotDireta}`}
                aria-hidden="true"
              />
              <span className={styles.rotaLegendLabel}>Direta</span>
              <span className={styles.rotaLegendValue}>{diretaCount}</span>
            </li>
          </ul>
        </motion.div>
      </div>

      {/* ─── Linha 2: 3 cards (donut, vendor row, vendor highlight) ──── */}
      <div className={styles.chartsRowGeral}>
        {/* e) Provas ativas / ESTADO ATUAL */}
        <motion.div
          className={`${styles.metricCard} ${styles.metricCardLight} ${styles.metricCardDonut}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.16 }}
        >
          <div className={styles.metricCardTitleBlock}>
            <h2 className={styles.metricCardTitle}>Provas ativas</h2>
            <span className={styles.metricCardSubtitle}>ESTADO ATUAL</span>
          </div>
          {ativosData.length > 0 ? (
            <DonutChart
              data={ativosData}
              ariaLabel="Distribuicao de provas ativas (nao-terminais) por status"
              onSegmentClick={(key) => {
                // Toggle: clicar no segmento que ja e o filtro ativo
                // remove o filtro (volta ao estado multi-segmento).
                const clicked = key as StatusProva;
                if (statusFilter === clicked) {
                  onStatusClick?.(null);
                } else {
                  onStatusClick?.(clicked);
                }
              }}
              centerLabel={String(totalAtivas)}
              centerHint="ATIVAS"
            />
          ) : (
            <EmptyState
              message="Nenhuma prova ativa."
              hint="Todas as provas estao em estados terminais."
            />
          )}
        </motion.div>

        {/* f) Tempo medio de aprovacao / POR VENDEDOR */}
        <motion.div
          className={`${styles.metricCard} ${styles.metricCardLight} ${styles.metricCardVendorRow}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.2 }}
        >
          <div className={styles.metricCardTitleBlock}>
            <h2 className={styles.metricCardTitle}>
              Tempo medio de aprovacao
            </h2>
            <span className={styles.metricCardSubtitle}>POR VENDEDOR</span>
          </div>
          {tempoMedioRanking.length > 0 ? (
            <ul className={styles.vendorRowList}>
              {tempoMedioRanking.map((v, idx) => (
                <li key={v.id} className={styles.vendorRowItem}>
                  <span className={styles.vendorRowRank}>
                    {String(idx + 1).padStart(2, "0")}
                  </span>
                  <span className={styles.vendorRowName}>{v.nome}</span>
                  <span className={styles.vendorRowValue}>
                    {formatHoras(v.tempo)}
                  </span>
                  <div
                    className={styles.vendorRowBarTrack}
                    aria-hidden="true"
                  >
                    <div
                      className={styles.vendorRowBarFill}
                      style={{ width: `${v.pct}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              message="Sem decisoes no periodo."
              hint="Nenhum vendedor decidiu prova ainda."
            />
          )}
        </motion.div>

        {/* g) BLACK card — VENDEDOR COM MAIS ARTES */}
        <motion.div
          className={`${styles.metricCard} ${styles.metricCardDark} ${styles.metricCardVendorHighlight}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.24 }}
        >
          <span className={styles.metricEyebrow}>VENDEDOR COM MAIS ARTES</span>
          {topVolumeVendedor ? (
            <>
              <span className={styles.metricVendorName}>
                {topVolumeVendedor.vendedor_nome}
              </span>
              <div className={styles.metricValueWithUnit}>
                <span className={styles.metricValueLg}>
                  {formatNum(topVolumeVendedor.volume)}
                </span>
                <span className={styles.metricValueUnit}>artes</span>
              </div>
              <div className={styles.metricSparkline}>
                <Sparkline points={sparklineSerie} />
              </div>
            </>
          ) : (
            <span className={styles.metricVendorNameMuted}>
              Nenhum vendedor no periodo
            </span>
          )}
        </motion.div>
      </div>

      {/* ─── Tabela "Metricas por Vendedor" — design Mario ─────────────── */}
      <div className={styles.rankingCard}>
        <header className={styles.rankingHeader}>
          <div className={styles.rankingHeaderTitleBlock}>
            <h2 className={styles.rankingTitle}>Metricas por Vendedor</h2>
            <span className={styles.rankingSubtitle}>RANKING DETALHADO</span>
          </div>
          <span className={styles.rankingCounter}>
            {rankingByVolume.length}{" "}
            {rankingByVolume.length === 1 ? "VENDEDOR" : "VENDEDORES"}
          </span>
        </header>

        {rankingByVolume.length === 0 ? (
          <EmptyState message="Nenhum vendedor no ranking para este periodo." />
        ) : (
          <div className={styles.rankingTableWrapper}>
            <table className={styles.rankingTable}>
              <caption className={styles.srOnly}>
                Metricas por vendedor: ranking de volume, aprovacoes,
                reprovacoes, taxa de reprovacao e tempo medio.
              </caption>
              <thead>
                <tr>
                  <th scope="col" className={styles.rankingTh}>#</th>
                  <th scope="col" className={styles.rankingTh}>VENDEDOR</th>
                  <th scope="col" className={styles.rankingTh}>LOCAL</th>
                  <th scope="col" className={styles.rankingTh}>VOLUME</th>
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
                </tr>
              </thead>
              <tbody>
                {rankingByVolume.map((v, idx) => {
                  const isTop = idx === 0;
                  const initials = getVendedorInitials(v.vendedor_nome);
                  const volumePct =
                    topVolume > 0 ? (v.volume / topVolume) * 100 : 0;
                  const taxa = v.taxa_reprovacao;

                  return (
                    <motion.tr
                      key={v.vendedor_id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.2, delay: idx * 0.04 }}
                    >
                      <td className={styles.rankingTd}>
                        <span className={styles.rankingRankCell}>
                          {isTop && (
                            <span
                              className={styles.rankingRankDot}
                              aria-hidden="true"
                            />
                          )}
                          <span>{String(idx + 1).padStart(2, "0")}</span>
                        </span>
                      </td>
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
                      <td className={styles.rankingTd}>
                        <div className={styles.rankingVolumeCell}>
                          <div
                            className={styles.rankingVolumeTrack}
                            aria-hidden="true"
                          >
                            <div
                              className={styles.rankingVolumeFill}
                              style={{ width: `${volumePct}%` }}
                            />
                          </div>
                          <span className={styles.rankingVolumeNum}>
                            {formatNum(v.volume)}
                          </span>
                        </div>
                      </td>
                      <td
                        className={`${styles.rankingTd} ${styles.rankingNumericCell}`}
                      >
                        <span
                          className={
                            v.aprovacoes > 0
                              ? styles.rankingAprovActive
                              : styles.rankingZeroValue
                          }
                        >
                          {formatNum(v.aprovacoes)}
                        </span>
                      </td>
                      <td
                        className={`${styles.rankingTd} ${styles.rankingNumericCell}`}
                      >
                        <span
                          className={
                            taxa > 0.2
                              ? styles.rankingReprovHigh
                              : taxa > 0
                                ? styles.rankingReprovLow
                                : styles.rankingZeroValue
                          }
                        >
                          {formatPct(taxa)}
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
                    </motion.tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ─── Lista "Provas Atrasadas" — mesmo estilo do ranking ───────── */}
      <div className={styles.rankingCard}>
        <header className={styles.rankingHeader}>
          <div className={styles.rankingHeaderTitleBlock}>
            <h2 className={styles.rankingTitle}>Provas Atrasadas</h2>
            <span className={styles.rankingSubtitle}>
              AGUARDANDO ACAO
            </span>
          </div>
          <span className={styles.rankingCounter}>
            {data.provas_atrasadas_total}{" "}
            {data.provas_atrasadas_total === 1 ? "PROVA" : "PROVAS"}
          </span>
        </header>

        {data.provas_atrasadas.length === 0 ? (
          <EmptyState
            message="Nenhuma prova atrasada."
            hint="Todas as provas ativas estao dentro do prazo configurado."
          />
        ) : (
          <div className={styles.rankingTableWrapper}>
            <table className={styles.rankingTable}>
              <caption className={styles.srOnly}>
                Provas atualmente atrasadas, com vendedor responsavel, status
                e horas de atraso.
              </caption>
              <thead>
                <tr>
                  <th scope="col" className={styles.rankingTh}>#</th>
                  <th scope="col" className={styles.rankingTh}>PROVA</th>
                  <th scope="col" className={styles.rankingTh}>VENDEDOR</th>
                  <th scope="col" className={styles.rankingTh}>STATUS</th>
                  <th
                    scope="col"
                    className={`${styles.rankingTh} ${styles.rankingThNumeric}`}
                  >
                    ATRASO
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.provas_atrasadas.map((p, idx) => {
                  const initials = getVendedorInitials(p.vendedor_nome);
                  return (
                    <motion.tr
                      key={p.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.2, delay: idx * 0.04 }}
                    >
                      <td className={styles.rankingTd}>
                        <span className={styles.rankingRankCell}>
                          {String(idx + 1).padStart(2, "0")}
                        </span>
                      </td>
                      <td className={styles.rankingTd}>
                        <div className={styles.rankingProva}>
                          <span className={styles.rankingProvaNome}>
                            {p.nome}
                          </span>
                          <span className={styles.rankingProvaMeta}>
                            {p.nro_requerimento} · {p.cliente}
                          </span>
                        </div>
                      </td>
                      <td className={styles.rankingTd}>
                        <div className={styles.rankingVendor}>
                          <span
                            className={styles.rankingAvatar}
                            aria-hidden="true"
                          >
                            {initials}
                          </span>
                          <span className={styles.rankingVendorName}>
                            {p.vendedor_nome}
                          </span>
                        </div>
                      </td>
                      <td className={styles.rankingTd}>
                        <span className={styles.rankingStatusPill}>
                          {STATUS_LABELS[p.status]}
                        </span>
                      </td>
                      <td
                        className={`${styles.rankingTd} ${styles.rankingNumericCell}`}
                      >
                        <span className={styles.rankingAtraso}>
                          {p.horas_atrasada.toFixed(1)}h
                        </span>
                      </td>
                    </motion.tr>
                  );
                })}
                {data.provas_atrasadas_total >
                  data.provas_atrasadas.length && (
                  <tr>
                    <td
                      colSpan={5}
                      className={`${styles.rankingTd} ${styles.rankingFooterCell}`}
                    >
                      +{" "}
                      {data.provas_atrasadas_total -
                        data.provas_atrasadas.length}{" "}
                      provas atrasadas adicionais. Use a exportacao CSV
                      (dataset &quot;overdue&quot;) para a lista completa.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
