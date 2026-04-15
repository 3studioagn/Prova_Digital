/**
 * Tipos TypeScript para Interface de Log de Auditoria (Wave 6, Componente 18).
 *
 * Espelho fiel de `backend/app/domain/schemas/auditoria.py`. Mantem os
 * snake_case do backend no shape transportado pelo JSON (items,
 * filtros_aplicados, etc) e oferece uma camada camel-case para o hook
 * `useAuditoria` aceitar filtros como objeto TypeScript idiomatico.
 *
 * Ver:
 *  - ADR-099 (projecao de tipo_evento)
 *  - WAVE6_ANALYSIS.md secao 4 (contratos de API)
 */

// =============================================================================
// Constantes — whitelist e labels
// =============================================================================

/** Tipos de evento DERIVADOS pela projecao backend.
 * Espelha `TipoEventoEnum` em `schemas/auditoria.py`. */
export const TIPO_EVENTO_VALUES = [
  "CRIACAO_PROVA",
  "ESCANEAMENTO",
  "CANCELAMENTO",
  "REPROVACAO",
  "TRANSICAO_STATUS",
  "REINICIO_CICLO",
  "ALTERACAO_CONFIG",
] as const;

export type TipoEventoEnum = (typeof TIPO_EVENTO_VALUES)[number];

/** Labels pt-BR por tipo_evento. Espelha `TIPO_EVENTO_LABELS` no backend.
 *
 * Mantido aqui como fonte unica da verdade no frontend — evita hardcode
 * espalhado pelas paginas/componentes.
 */
export const TIPO_EVENTO_LABELS: Record<TipoEventoEnum, string> = {
  CRIACAO_PROVA: "Criacao de prova",
  ESCANEAMENTO: "Escaneamento",
  CANCELAMENTO: "Cancelamento",
  REPROVACAO: "Reprovacao",
  TRANSICAO_STATUS: "Transicao de status",
  REINICIO_CICLO: "Reinicio de ciclo",
  ALTERACAO_CONFIG: "Alteracao de configuracao",
};

/** Whitelist de valores crus de `audit_logs.acao` aceitos pelo backend.
 * Espelha `ACOES_VALIDAS` em `schemas/auditoria.py`. */
export const ACOES_VALIDAS = [
  "criar_prova",
  "escanear_prova",
  "transitar_status",
  "reiniciar_ciclo",
  "atualizar_configuracao",
] as const;

export type AcaoValida = (typeof ACOES_VALIDAS)[number];

/** Teto do campo `total_estimado` — se o valor retornado for >= este cap,
 * a UI deve exibir "100k+" em vez do numero exato. */
export const TOTAL_ESTIMADO_CAP = 100_001;

/** Limite maximo de items por pagina (server-enforced). */
export const LIMIT_MAX = 100;

/** Default de items por pagina quando o caller nao especifica. */
export const LIMIT_DEFAULT = 50;

// =============================================================================
// Response DTOs (snake_case — espelhos do JSON wire format)
// =============================================================================

export interface UsuarioAuditoria {
  id: string;
  nome: string;
  setor: string;
  is_admin: boolean;
}

export interface ProvaAuditoria {
  id: string;
  nro_requerimento: string;
  nome: string;
}

export interface AuditLogItem {
  id: string;
  /** Valor cru de `audit_logs.acao` (um dos 5 em `ACOES_VALIDAS`). */
  acao: string;
  /** Enum derivado pela funcao `projetar_tipo_evento` no backend (ADR-099). */
  tipo_evento: TipoEventoEnum;
  /** Label pt-BR para exibicao direta (de `TIPO_EVENTO_LABELS` do backend). */
  tipo_evento_label: string;
  usuario: UsuarioAuditoria;
  /** Null quando `audit_logs.prova_id` e NULL (ex: `atualizar_configuracao`). */
  prova: ProvaAuditoria | null;
  /** JSONB cru preservado para exibicao no modal de detalhes.
   * A varredura empirica do Bloco 6.0 confirmou ausencia de PII sensivel. */
  detalhes_json: Record<string, unknown> | null;
  /** IP do cliente (ADR F04 — X-Forwarded-For, X-Real-IP, request.client). */
  ip_address: string | null;
  user_agent: string | null;
  /** Timestamp UTC ISO 8601 do evento (imutavel por trigger). */
  created_at: string;
}

export interface FiltrosAplicados {
  data_inicio: string | null;
  data_fim: string | null;
  usuario_id: string | null;
  nro_requerimento: string | null;
  acao: string[] | null;
  tipo_evento: TipoEventoEnum[] | null;
  limit: number;
}

export interface AuditoriaListResponse {
  items: AuditLogItem[];
  /** Base64 opaco para a proxima pagina. Null quando `has_more=false`. */
  next_cursor: string | null;
  has_more: boolean;
  /** `COUNT(*)` filtrado. Cap em `TOTAL_ESTIMADO_CAP` — se retornar esse
   * valor, a UI deve exibir "100k+". */
  total_estimado: number;
  filtros_aplicados: FiltrosAplicados;
}

// =============================================================================
// Hook input — AuditoriaFilters (camelCase idiomatico JS)
// =============================================================================

/** Filtros de entrada para `useAuditoria`.
 *
 * Convencao: camelCase no frontend, traduzido para snake_case na query
 * string pelo hook. O caller passa o objeto diretamente — a estabilidade
 * de identidade e gerenciada pelo hook via `filtersKey` derivada.
 */
export interface AuditoriaFilters {
  /** Data no formato ISO-8601 `YYYY-MM-DD` (BRT). */
  dataInicio?: string | null;
  /** Data no formato ISO-8601 `YYYY-MM-DD` (BRT). */
  dataFim?: string | null;
  /** UUID do usuario autor do evento. */
  usuarioId?: string | null;
  /** Numero de requerimento exato — filtra pela prova correspondente. */
  nroRequerimento?: string | null;
  /** Whitelist de valores crus de `acao`. Mutuamente exclusivo com `tipoEvento`. */
  acao?: readonly string[] | null;
  /** Tipos de evento derivados. Mutuamente exclusivo com `acao`. */
  tipoEvento?: readonly TipoEventoEnum[] | null;
  /** Quantidade de items por pagina (1 a `LIMIT_MAX`, default `LIMIT_DEFAULT`). */
  limit?: number;
}
