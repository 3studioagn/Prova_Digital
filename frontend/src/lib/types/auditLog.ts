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

// ─── Filtros (query params) ──────────────────────────────────────────────

/** Filtros aceitos pelo GET /api/v1/audit-log.
 *
 * Espelha AuditLogListQuery do backend. Todos opcionais — se omitidos,
 * o backend usa defaults (page=1, page_size=50, sort=desc, sem filtro).
 */
export interface AuditLogFilters {
  page: number;
  page_size: number;
  sort: "asc" | "desc";
  from_dt: string | null;
  to_dt: string | null;
  prova_id: string | null;
  usuario_id: string | null;
  acao: string | null;
  q: string | null;
}

export const DEFAULT_FILTERS: AuditLogFilters = {
  page: 1,
  page_size: 50,
  sort: "desc",
  from_dt: null,
  to_dt: null,
  prova_id: null,
  usuario_id: null,
  acao: null,
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
  if (filters.q) {
    params.set("q", filters.q);
  }
  const s = params.toString();
  return s ? `?${s}` : "";
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
