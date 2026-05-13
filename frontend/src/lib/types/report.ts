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

import type { ContextoMotorista, Localizacao, Rota, StatusProva } from "./prova";

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

/** Categoria consolidada de rota (Wave 5 v4.0 — Componente 16).
 *
 * Espelha `RotaCategoria` Python em
 * `backend/app/services/report_filters.py`.
 *
 * - `matriz`: provas com `rota IN {MATRIZ, LAM_MATRIZ, PADRAO}` + provas
 *   legacy `rota=NULL` cujo vendedor esta em `localizacao=MATRIZ`.
 * - `filial`: provas com `rota IN {FILIAL, LAM_FILIAL, DIRETA}` + provas
 *   legacy `rota=NULL` cujo vendedor esta em `localizacao=FILIAL`.
 *
 * Quando enviado via `?rota_categoria=...`, toma precedencia sobre
 * `?rota=...` (mais abrangente). O `RotaFilter` atual (3 botoes:
 * Todas/Matriz/Filial) emite `rota_categoria` para preservar layout
 * v3 cobrindo v4.0.
 */
export type RotaCategoria = "matriz" | "filial";

export interface ReportFilters {
  scope: ReportScope;
  /** ISO-8601 datetime UTC. Se ausente, backend usa default (to - 30d). */
  from?: string | null;
  /** ISO-8601 datetime UTC. Se ausente, backend usa now(). */
  to?: string | null;
  /** Busca textual (max 200 chars). */
  q?: string | null;
  vendedor_id?: string | null;
  /** Filtro por valor exato de rota (6 valores: 4 v4.0 + 2 legacy). */
  rota?: Rota | null;
  /** [Wave 5 v4.0] Categoria consolidada (matriz/filial). Precedencia
   * sobre `rota` se ambos fornecidos. */
  rota_categoria?: RotaCategoria | null;
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

/** Categoria detalhada para `distribuicao_rota_v4` (Wave 5 v4.0). */
export type DistRotaV4Categoria =
  | "v4_matriz"
  | "v4_lam_matriz"
  | "v4_filial"
  | "v4_lam_filial"
  | "legacy_padrao"
  | "legacy_direta"
  | "legacy_null_matriz"
  | "legacy_null_filial"
  | "legacy_null_indefinida";

/** Distribuicao detalhada de provas por rota v4.0 + legacy.
 *
 * Wave 5 v4.0: substitui funcionalmente `DistRotaItem` para clientes que
 * precisam do detalhamento. Frontend atual (preservando layout v3) consome
 * `ConsolidacaoRota` no card ROTA; este detalhamento e exposto no CSV e
 * fica disponivel para downstream sem render visivel. */
export interface DistRotaV4Item {
  categoria: DistRotaV4Categoria;
  /** Rota subjacente (null para legacy NULL inferida via localizacao). */
  rota: Rota | null;
  quantidade: number;
}

/** Consolidacao em 2 categorias (Wave 5 v4.0).
 *
 * Usado pelo card ROTA do `ReportGeral` para preservar layout v3 (2 dots)
 * com semantica v4.0 (cobre 4 rotas v4.0 + 2 legacy + null inferido).
 */
export interface ConsolidacaoRota {
  matriz: number;
  filial: number;
  indefinida: number;
}

/** Distribuicao de provas atualmente com motorista por contexto canonico
 * (Wave 5 v4.0). Snapshot — nao filtrado por periodo. */
export interface DistContextoMotoristaItem {
  contexto: ContextoMotorista;
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
  /** Numero absoluto de aprovacoes do vendedor no periodo. */
  aprovacoes: number;
  /** Numero absoluto de reprovacoes do vendedor no periodo. */
  reprovacoes: number;
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

export interface ProvaAtrasadaItem {
  id: string;
  nome: string;
  nro_requerimento: string;
  cliente: string;
  vendedor_nome: string;
  status: StatusProva;
  /** Horas corridas alem do tempo limite (ADR-099). */
  horas_atrasada: number;
  /** Timestamp ISO-8601 UTC da ultima movimentacao (ou created_at). */
  ultima_movimentacao_at: string;
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
  /** [LEGACY v3] Distribuicao por rota — apenas PADRAO/DIRETA/NULL.
   * Preservada por compat; usar `distribuicao_rota_v4` para detalhamento. */
  distribuicao_rota: DistRotaItem[];
  /** [Wave 5 v4.0] Distribuicao detalhada cobrindo 9 categorias possiveis
   * (4 rotas v4.0 + 2 legacy + 3 sub-buckets para `rota=NULL`). Opcional
   * para compat com payloads antigos cached. */
  distribuicao_rota_v4?: DistRotaV4Item[];
  /** [Wave 5 v4.0] Consolidacao matriz/filial usada pelo card ROTA. */
  consolidacao_rota?: ConsolidacaoRota;
  /** [Wave 5 v4.0] Distribuicao de provas com motorista pelos 3 contextos
   * canonicos. Snapshot — nao filtrado por periodo. */
  contexto_motorista_dist?: DistContextoMotoristaItem[];
  /** Top vendedores por volume no periodo (max 200). */
  ranking: VendedorMetrica[];
  /** Top 20 provas atualmente atrasadas (snapshot). */
  provas_atrasadas: ProvaAtrasadaItem[];
  /** Contagem total de atrasadas (sem cap) — UI mostra "(N)" no header. */
  provas_atrasadas_total: number;
  /** Timestamp UTC do calculo. */
  atualizado_em: string;
}

export interface ReportResponse3Studio {
  scope: "3studio";
  periodo: PeriodoMeta;
  indicadores: Indicadores3Studio;
  cancelamentos_top: CancelamentoTop[];
  /**
   * Provas criadas por dia (00:00 UTC do bucket). Mesma serie que o
   * scope=geral (provas_criadas neste scope agrega o mesmo conjunto
   * de registros). Usado pelo sparkline do card "PROVAS CRIADAS".
   */
  serie_temporal: PontoSerie[];
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
