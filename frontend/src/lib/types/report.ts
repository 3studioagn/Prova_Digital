/**
 * Tipos de Relatorios Gerenciais (Wave 5, Componente 16).
 *
 * Espelho fiel dos schemas Pydantic em
 *   backend/app/domain/schemas/report.py
 *
 * Implementa a discriminated union por `scope` — cada perspectiva tem
 * seu shape proprio, e o narrowing via switch/case e exaustivo.
 *
 * Tempos sao sempre em horas CORRIDAS (ADR-091, ADR-099 — desvio do
 * RN-008 literal, alinhado com Wave 4 Dashboard).
 */

import type { Localizacao, Rota, StatusProva } from "./prova";

// ─── Filtros de query ──────────────────────────────────────────────────

export type ReportScope = "geral" | "3studio" | "vendedores" | "clicheria";

export const REPORT_SCOPES: ReportScope[] = [
  "geral",
  "3studio",
  "vendedores",
  "clicheria",
];

export const REPORT_SCOPE_LABELS: Record<ReportScope, string> = {
  geral: "Geral",
  "3studio": "3Studio",
  vendedores: "Vendedores",
  clicheria: "Clicheria",
};

export interface ReportFilters {
  scope: ReportScope;
  /** ISO-8601 datetime UTC. Se ausente, backend usa default (to - 30d). */
  from?: string | null;
  /** ISO-8601 datetime UTC. Se ausente, backend usa now(). */
  to?: string | null;
  /** Busca textual (max 200 chars). */
  q?: string | null;
  vendedor_id?: string | null;
  rota?: Rota | null;
  status?: StatusProva | null;
}

export const REPORT_DEFAULT_PERIOD_DAYS = 30;
export const REPORT_MAX_PERIOD_DAYS = 366;
export const REPORT_MAX_Q_LENGTH = 200;

// ─── Sub-schemas comuns ───────────────────────────────────────────────

export interface PeriodoMeta {
  /** Limite inferior (inclusive) em UTC, ISO-8601. */
  from: string;
  /** Limite superior (exclusive) em UTC, ISO-8601. */
  to: string;
  total_dias: number;
}

export interface DistStatusItem {
  status: StatusProva;
  quantidade: number;
}

export interface DistRotaItem {
  /** `null` representa provas com rota nao definida (status pre-aprovacao). */
  rota: Rota | null;
  quantidade: number;
}

export interface PontoSerie {
  /** Inicio do bucket (UTC, ISO-8601). */
  data: string;
  quantidade: number;
}

export interface CancelamentoTop {
  motivo: string;
  quantidade: number;
}

export interface DistLocalizacao {
  matriz: number;
  filial: number;
}

export interface DistOrigemRota {
  /** Provas que vieram via COM_MOTORISTA → ENVIADA → RECEBIDA. */
  via_padrao: number;
  /** Provas que vieram via ENCAMINHADA (vendedor Filial). */
  via_direta: number;
}

// ─── Indicadores por scope ────────────────────────────────────────────

export interface IndicadoresGeral {
  total_provas: number;
  /** None se nenhuma prova foi concluida no periodo. */
  tempo_medio_ciclo_horas: number | null;
  tempo_mediano_ciclo_horas: number | null;
  /** None se nenhum ciclo decidiu no periodo. */
  tempo_medio_aprovacao_horas: number | null;
  /** Faixa: 0.0 a 1.0. Frontend converte para % se necessario. */
  taxa_reprovacao: number;
  /** Snapshot — provas atualmente nao-terminais excedendo tempo de atraso. */
  qtd_atrasadas: number;
}

export interface Indicadores3Studio {
  provas_criadas: number;
  media_diaria_criacao: number;
  /** Movimentacoes status_anterior=REPROVADA, status_novo=CRIADA (RN-006). */
  reinicios_de_ciclo: number;
  /** Provas que entraram em COM_MOTORISTA no periodo. */
  devolvidas_motorista: number;
  /** Snapshot atual: status REPROVADA_PELO_VENDEDOR sem reinicio. */
  reprovadas_aguardando_acao: number;
  cancelamentos: number;
  tempo_medio_criacao_ate_primeira_mov_horas: number | null;
}

export interface VendedorMetrica {
  vendedor_id: string;
  vendedor_nome: string;
  localizacao: Localizacao;
  volume: number;
  taxa_aprovacao: number;
  taxa_reprovacao: number;
  tempo_medio_retirada_a_decisao_horas: number | null;
  provas_atrasadas_em_poder: number;
}

export interface VendedorAtrasoAtual {
  vendedor_id: string;
  vendedor_nome: string;
  localizacao: Localizacao;
  qtd_atrasadas: number;
}

export interface IndicadoresClicheria {
  recebidas_no_periodo: number;
  tempo_medio_aguardando_recebimento_horas: number | null;
  /** Snapshot: COM_MOTORISTA + ENVIADA_PARA_CLICHERIA + ENCAMINHADA. */
  em_transito_atual: number;
  por_origem_rota: DistOrigemRota;
}

// ─── Respostas tipadas (discriminated union) ──────────────────────────

export interface ReportResponseGeral {
  scope: "geral";
  periodo: PeriodoMeta;
  indicadores: IndicadoresGeral;
  serie_temporal: PontoSerie[];
  distribuicao_status: DistStatusItem[];
  distribuicao_rota: DistRotaItem[];
  /** Timestamp UTC do calculo. */
  atualizado_em: string;
}

export interface ReportResponse3Studio {
  scope: "3studio";
  periodo: PeriodoMeta;
  indicadores: Indicadores3Studio;
  cancelamentos_top: CancelamentoTop[];
  atualizado_em: string;
}

export interface ReportResponseVendedores {
  scope: "vendedores";
  periodo: PeriodoMeta;
  ranking: VendedorMetrica[];
  distribuicao_localizacao: DistLocalizacao;
  atrasadas_em_poder: VendedorAtrasoAtual[];
  atualizado_em: string;
}

export interface ReportResponseClicheria {
  scope: "clicheria";
  periodo: PeriodoMeta;
  indicadores: IndicadoresClicheria;
  atualizado_em: string;
}

/**
 * Discriminated union — Pydantic resolve via `scope` no backend.
 * No TypeScript, narrowing exaustivo via switch/case sobre `data.scope`.
 */
export type ReportResponse =
  | ReportResponseGeral
  | ReportResponse3Studio
  | ReportResponseVendedores
  | ReportResponseClicheria;

// ─── Datasets de export CSV ───────────────────────────────────────────

export type ExportDataset = "summary" | "by-seller" | "overdue" | "proofs";

export const EXPORT_DATASETS: ExportDataset[] = [
  "summary",
  "by-seller",
  "overdue",
  "proofs",
];

export const EXPORT_DATASET_LABELS: Record<ExportDataset, string> = {
  summary: "Resumo",
  "by-seller": "Por vendedor",
  overdue: "Atrasadas",
  proofs: "Provas",
};

// ─── Helpers de formatacao (compartilhados pelas perspectivas) ────────

/** Formata percentual a partir de taxa 0.0-1.0. */
export function formatPct(taxa: number): string {
  return `${(taxa * 100).toFixed(1)}%`;
}

/** Formata horas com sufixo. `null` => "—". */
export function formatHoras(horas: number | null): string {
  if (horas === null) return "—";
  return `${horas.toFixed(1)}h`;
}

/** Formata numero inteiro com separador de milhar. */
export function formatNum(n: number): string {
  return n.toLocaleString("pt-BR");
}

/** Formata data ISO em formato BRT (DD/MM). */
export function formatDataBrt(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
  });
}

/** Formata data+hora ISO em BRT. */
export function formatDataHoraBrt(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
