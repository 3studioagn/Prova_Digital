/**
 * Tipos do dominio de Audit Log usados pelo frontend (Wave 6, Componente 18).
 * Espelho fiel dos schemas Pydantic em backend/app/domain/schemas/audit_log.py.
 *
 * Acesso restrito ao perfil 3Studio (is_admin=true) — defesa em profundidade
 * via middleware FastAPI + RLS pol_audit_select + guard de menu.
 */

import type { Rota, Setor, StatusProva } from "./prova";

// ─── Acoes conhecidas (universo aberto) ──────────────────────────────────

/**
 * Lista das acoes conhecidas hoje. O backend aceita qualquer string <= 100
 * chars — migrations futuras podem adicionar valores. A UI exibe o valor
 * cru se nao estiver no mapa de labels.
 */
export const ACOES_CONHECIDAS = [
  "criar_prova",
  "escanear_prova",
  "transitar_status",
  "reiniciar_ciclo",
  "atualizar_configuracao",
  "REPORT_EXPORTED",
] as const;

export type AcaoConhecida = (typeof ACOES_CONHECIDAS)[number];

/** Tipo aberto: aceita acoes futuras nao listadas. */
export type Acao = AcaoConhecida | string;

/** Labels pt-BR para acoes conhecidas. UI faz fallback para o valor cru. */
export const ACAO_LABELS: Record<AcaoConhecida, string> = {
  criar_prova: "Criar prova",
  escanear_prova: "Escanear QR Code",
  transitar_status: "Mudar status",
  reiniciar_ciclo: "Reiniciar ciclo",
  atualizar_configuracao: "Atualizar configuracao",
  REPORT_EXPORTED: "Exportar relatorio",
};

/** Helper para formatar a acao para exibicao. */
export function formatAcao(acao: string): string {
  if (acao in ACAO_LABELS) {
    return ACAO_LABELS[acao as AcaoConhecida];
  }
  return acao;
}

// ─── Itens da listagem e detalhe ─────────────────────────────────────────

/** Linha individual da listagem de audit_logs.
 *
 * `assinatura_digital` (BYTEA) NUNCA e exposta — backend impede.
 */
export interface AuditLogItemResponse {
  id: string;
  acao: string;
  prova_id: string | null;
  prova_nro_requerimento: string | null;
  usuario_id: string;
  usuario_nome: string;
  usuario_setor: Setor;
  detalhes_json: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

/** Resumo de movimentacao relacionada a um audit_log de transicao.
 *
 * Aparece no detalhe quando acao for transitar_status ou reiniciar_ciclo
 * E o backend conseguir matchear via prova_id + status_novo + ciclo +
 * janela ±5s.
 *
 * `assinatura_digital_presente` e o unico vestigio do BYTEA — confirma
 * que houve assinatura conforme RN-003 sem expor o conteudo.
 */
export interface MovimentacaoSnapshot {
  id: string;
  status_anterior: StatusProva;
  status_novo: StatusProva;
  motivo_reprovacao: string | null;
  ciclo: number;
  rota_no_momento: Rota | null;
  assinatura_digital_presente: boolean;
  created_at: string;
}

/** Detalhe individual com enriquecimento opcional. */
export interface AuditLogDetailResponse extends AuditLogItemResponse {
  movimentacao_relacionada: MovimentacaoSnapshot | null;
}

/** Response paginado da listagem (e do by-prova, que tambem usa esse shape). */
export interface AuditLogListResponse {
  items: AuditLogItemResponse[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Tipo de evento semantico (UX A2) ────────────────────────────────────

/** Categorias semanticas de alto nivel para filtro `tipo_evento`.
 *
 * Mapeia para combinacoes de `acao` + `detalhes_json` no backend.
 * 'todos' (e null) = sem filtro.
 */
export type TipoEvento =
  | "todos"
  | "reprovacao"
  | "reinicio"
  | "cancelamento"
  | "criacao"
  | "admin";

export const TIPO_EVENTO_OPTIONS: readonly TipoEvento[] = [
  "todos",
  "reprovacao",
  "reinicio",
  "cancelamento",
  "criacao",
  "admin",
] as const;

export const TIPO_EVENTO_LABELS: Record<TipoEvento, string> = {
  todos: "Todos os eventos",
  reprovacao: "Apenas reprovacoes",
  reinicio: "Apenas reinicios de ciclo",
  cancelamento: "Apenas cancelamentos",
  criacao: "Apenas criacoes de prova",
  admin: "Mudancas administrativas",
};

// ─── Ordenacao (UX B4) ───────────────────────────────────────────────────

/** Colunas pelas quais a listagem pode ser ordenada (whitelist do backend). */
export type OrderBy = "created_at" | "acao" | "usuario_nome";

export const ORDER_BY_LABELS: Record<OrderBy, string> = {
  created_at: "Data e hora",
  acao: "Acao",
  usuario_nome: "Ator",
};

// ─── Page size (UX B2) ───────────────────────────────────────────────────

export const PAGE_SIZE_OPTIONS: readonly number[] = [25, 50, 100, 200] as const;

// ─── Filtros (query params) ──────────────────────────────────────────────

/** Filtros aceitos pelo GET /api/v1/audit-log.
 *
 * Espelha AuditLogListQuery do backend. Todos opcionais — se omitidos,
 * o backend usa defaults (page=1, page_size=50, sort=desc,
 * order_by=created_at, sem filtros).
 */
export interface AuditLogFilters {
  page: number;
  page_size: number;
  sort: "asc" | "desc";
  order_by: OrderBy;
  from_dt: string | null;
  to_dt: string | null;
  prova_id: string | null;
  usuario_id: string | null;
  acao: string | null;
  /** Filtro semantico de alto nivel (UX A2). */
  tipo_evento: TipoEvento | null;
  q: string | null;
}

export const DEFAULT_FILTERS: AuditLogFilters = {
  page: 1,
  page_size: 50,
  sort: "desc",
  order_by: "created_at",
  from_dt: null,
  to_dt: null,
  prova_id: null,
  usuario_id: null,
  acao: null,
  tipo_evento: null,
  q: null,
};

/** Converte filtros para query string ?key=value&... — pula nulos. */
export function filtersToQueryString(filters: Partial<AuditLogFilters>): string {
  const params = new URLSearchParams();
  if (filters.page !== undefined && filters.page !== null) {
    params.set("page", String(filters.page));
  }
  if (filters.page_size !== undefined && filters.page_size !== null) {
    params.set("page_size", String(filters.page_size));
  }
  if (filters.sort) {
    params.set("sort", filters.sort);
  }
  if (filters.order_by && filters.order_by !== "created_at") {
    // Omite quando default — mantem URL enxuta.
    params.set("order_by", filters.order_by);
  }
  if (filters.from_dt) {
    params.set("from", filters.from_dt);
  }
  if (filters.to_dt) {
    params.set("to", filters.to_dt);
  }
  if (filters.prova_id) {
    params.set("prova_id", filters.prova_id);
  }
  if (filters.usuario_id) {
    params.set("usuario_id", filters.usuario_id);
  }
  if (filters.acao) {
    params.set("acao", filters.acao);
  }
  if (filters.tipo_evento && filters.tipo_evento !== "todos") {
    params.set("tipo_evento", filters.tipo_evento);
  }
  if (filters.q) {
    params.set("q", filters.q);
  }
  const s = params.toString();
  return s ? `?${s}` : "";
}

// ─── Presets de data (UX A1) ─────────────────────────────────────────────

export type DatePresetKey = "hoje" | "7d" | "30d" | "90d" | "personalizado";

export const DATE_PRESET_LABELS: Record<DatePresetKey, string> = {
  hoje: "Hoje",
  "7d": "7 dias",
  "30d": "30 dias",
  "90d": "90 dias",
  personalizado: "Personalizado",
};

/** Calcula intervalo from/to em ISO UTC para um preset, baseado em now().
 *
 * "Hoje" = inicio do dia em America/Sao_Paulo ate agora.
 * "7d/30d/90d" = N dias atras (em horas corridas, do mesmo horario) ate agora.
 * "personalizado" = retorna null/null (caller mantem o que estava na URL).
 */
export function presetToRange(
  key: DatePresetKey,
  now: Date = new Date(),
): { from: string | null; to: string | null } {
  if (key === "personalizado") {
    return { from: null, to: null };
  }

  // BRT offset (-3h sem DST). Brasil aboliu DST em 2019.
  const BRT_OFFSET_MS = 3 * 60 * 60 * 1000;

  if (key === "hoje") {
    // Inicio do dia em BRT = meia-noite BRT = 03:00 UTC do mesmo dia.
    const brtNow = new Date(now.getTime() - BRT_OFFSET_MS);
    const startOfDayBrt = new Date(
      Date.UTC(
        brtNow.getUTCFullYear(),
        brtNow.getUTCMonth(),
        brtNow.getUTCDate(),
        0,
        0,
        0,
      ),
    );
    // Converte de volta para UTC (adiciona offset).
    const fromUtc = new Date(startOfDayBrt.getTime() + BRT_OFFSET_MS);
    return { from: fromUtc.toISOString(), to: now.toISOString() };
  }

  const days = key === "7d" ? 7 : key === "30d" ? 30 : 90;
  const from = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
  return { from: from.toISOString(), to: now.toISOString() };
}

/** Detecta qual preset corresponde ao intervalo atual (para destacar pill ativo).
 *
 * Tolerancia de ±1 minuto no `to` (para acomodar diferenca entre
 * "agora-quando-clicou" e "agora-quando-renderiza").
 */
export function detectPreset(
  fromDt: string | null,
  toDt: string | null,
  now: Date = new Date(),
): DatePresetKey {
  if (!fromDt || !toDt) return "personalizado";

  const tolMs = 60 * 1000;
  const toDelta = Math.abs(new Date(toDt).getTime() - now.getTime());
  if (toDelta > tolMs) return "personalizado";

  for (const key of ["hoje", "7d", "30d", "90d"] as const) {
    const expected = presetToRange(key, now);
    if (
      expected.from &&
      Math.abs(new Date(fromDt).getTime() - new Date(expected.from).getTime()) <
        tolMs
    ) {
      return key;
    }
  }
  return "personalizado";
}

// ─── Indicadores visuais ─────────────────────────────────────────────────

/** Categoriza o evento para badge colorido. Consistente com Timeline (C12). */
export type AcaoCategoria =
  | "neutro"
  | "reprovacao"
  | "reinicio"
  | "cancelamento"
  | "criacao";

/** Determina a categoria de um audit_log para coloracao na UI. */
export function categorizar(item: AuditLogItemResponse): AcaoCategoria {
  if (item.acao === "reiniciar_ciclo") {
    return "reinicio";
  }
  if (item.acao === "criar_prova") {
    return "criacao";
  }
  if (item.acao === "transitar_status" && item.detalhes_json) {
    const para = (item.detalhes_json as { para?: string }).para;
    if (para === "REPROVADA_PELO_VENDEDOR") return "reprovacao";
    if (para === "CANCELADA") return "cancelamento";
  }
  return "neutro";
}
