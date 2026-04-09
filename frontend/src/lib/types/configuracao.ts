/**
 * Tipos compartilhados pelo fluxo de Configuracoes do Sistema (Componente 09).
 * Espelho dos schemas em backend/app/domain/schemas/configuracao.py.
 */

// ─── Chaves whitelisted (sincronizado com backend EDITABLE_KEYS) ──────

export const CHAVE_TEMPO_ATRASO = "tempo_atraso_horas_uteis";
export const CHAVE_TEMPLATE_ETIQUETA = "template_etiqueta";

export type ChaveConfiguracao =
  | typeof CHAVE_TEMPO_ATRASO
  | typeof CHAVE_TEMPLATE_ETIQUETA;

// ─── Limites (sincronizado com backend) ───────────────────────────────

export const TEMPO_ATRASO_MIN_HORAS = 1;
export const TEMPO_ATRASO_MAX_HORAS = 168;

export type FormatoEtiqueta = "A4" | "80mm_thermal";

export const FORMATOS_ETIQUETA: readonly FormatoEtiqueta[] = [
  "A4",
  "80mm_thermal",
] as const;

export const FORMATO_LABELS: Record<FormatoEtiqueta, string> = {
  A4: "A4 (folha inteira)",
  "80mm_thermal": "80mm (impressora termica)",
};

// ─── Tipo do valor de cada chave ──────────────────────────────────────

export interface TemplateEtiquetaValor {
  nome: string;
  formato: FormatoEtiqueta;
  logo_enabled: boolean;
  mostrar_data_criacao: boolean;
}

// ─── Response da API ──────────────────────────────────────────────────

export interface ConfiguracaoResponse {
  id: string;
  chave: string;
  valor: unknown; // Pode ser int, string, bool, dict — discriminado por `chave`
  descricao: string | null;
  updated_by: string | null;
  updated_at: string;
}

export interface ConfiguracaoListResponse {
  items: ConfiguracaoResponse[];
}

// ─── Type guards ──────────────────────────────────────────────────────

export function isTemplateEtiquetaValor(
  v: unknown,
): v is TemplateEtiquetaValor {
  if (typeof v !== "object" || v === null) return false;
  const obj = v as Record<string, unknown>;
  return (
    typeof obj.nome === "string" &&
    typeof obj.formato === "string" &&
    (FORMATOS_ETIQUETA as readonly string[]).includes(obj.formato) &&
    typeof obj.logo_enabled === "boolean" &&
    typeof obj.mostrar_data_criacao === "boolean"
  );
}

export function isTempoAtrasoValor(v: unknown): v is number {
  return (
    typeof v === "number" &&
    Number.isInteger(v) &&
    v >= TEMPO_ATRASO_MIN_HORAS &&
    v <= TEMPO_ATRASO_MAX_HORAS
  );
}
