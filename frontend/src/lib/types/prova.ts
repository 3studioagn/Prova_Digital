/**
 * Tipos compartilhados pelo fluxo de Provas Digitais (Componente 06).
 * Espelho fiel dos schemas Pydantic em backend/app/domain/schemas/prova.py.
 */

export type StatusProva =
  | "CRIADA"
  | "RETIRADA_PELO_VENDEDOR"
  | "APROVADA_PELO_VENDEDOR"
  | "DE_VOLTA_3STUDIO"
  | "COM_MOTORISTA"
  | "ENVIADA_PARA_CLICHERIA"
  | "ENCAMINHADA_A_CLICHERIA"
  | "RECEBIDA_PELA_CLICHERIA"
  | "REPROVADA_PELO_VENDEDOR"
  | "CANCELADA";

export type Rota = "PADRAO" | "DIRETA";

export type Localizacao = "MATRIZ" | "FILIAL";

/** Resposta de POST /api/v1/provas/upload-url */
export interface UploadUrlResponse {
  upload_url: string;
  object_key: string;
  expires_at: string;
  max_bytes: number;
}

/** Payload de POST /api/v1/provas/ */
export interface ProvaCreateRequest {
  nome: string;
  nro_requerimento: string;
  cliente: string;
  vendedor_id: string;
  object_key: string;
}

/** Representacao publica de uma prova digital.
 *
 * `rota_projetada` pode ser `null` quando o vendedor original perde a
 * capacidade de ter rota calculada (ex: desativado, mudou de setor). No
 * POST /provas/ sempre vem populado porque o endpoint valida o vendedor
 * no momento da criacao — a tipagem aceita null para ser consistente com
 * o detail (GET /{id}) e evitar discriminacao entre os dois responses.
 */
export interface ProvaResponse {
  id: string;
  nome: string;
  nro_requerimento: string;
  cliente: string;
  vendedor_id: string;
  vendedor_nome: string;
  vendedor_localizacao: Localizacao | null;
  imagem_url: string;
  qr_code_hash: string;
  status: StatusProva;
  rota: Rota | null;
  rota_projetada: Rota | null;
  ciclo_atual: number;
  motivo_cancelamento: string | null;
  created_at: string;
  updated_at: string;
}

/** Resposta de POST /api/v1/provas/ */
export interface ProvaCreateResponse {
  prova: ProvaResponse;
  etiqueta_pdf_base64: string;
  qr_code_payload: string;
}

/** Arquivos aceitos por RF-001. */
export const ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png"] as const;
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024; // 10 MB

// ─── Listagem (Componente 07) ─────────────────────────────────────────

/** Item slim retornado por GET /api/v1/provas/ — espelho de ProvaListItem. */
export interface ProvaListItem {
  id: string;
  nome: string;
  nro_requerimento: string;
  cliente: string;
  vendedor_id: string;
  vendedor_nome: string;
  status: StatusProva;
  rota: Rota | null;
  ciclo_atual: number;
  created_at: string;
  updated_at: string;
}

/** Resposta paginada de GET /api/v1/provas/. */
export interface ProvaListResponse {
  items: ProvaListItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

/** Labels pt-BR para cada status — reutilizavel no Componente 08. */
export const STATUS_LABELS: Record<StatusProva, string> = {
  CRIADA: "Criada",
  RETIRADA_PELO_VENDEDOR: "Retirada pelo vendedor",
  APROVADA_PELO_VENDEDOR: "Aprovada pelo vendedor",
  DE_VOLTA_3STUDIO: "De volta a 3Studio",
  COM_MOTORISTA: "Com motorista",
  ENVIADA_PARA_CLICHERIA: "Enviada para clicheria",
  ENCAMINHADA_A_CLICHERIA: "Encaminhada a clicheria",
  RECEBIDA_PELA_CLICHERIA: "Recebida pela clicheria",
  REPROVADA_PELO_VENDEDOR: "Reprovada pelo vendedor",
  CANCELADA: "Cancelada",
};

/** Labels pt-BR para as rotas. */
export const ROTA_LABELS: Record<Rota, string> = {
  PADRAO: "Rota padrao",
  DIRETA: "Rota direta",
};

/** Ordem canonica dos status para exibicao em selects. */
export const STATUS_OPTIONS: readonly StatusProva[] = [
  "CRIADA",
  "RETIRADA_PELO_VENDEDOR",
  "APROVADA_PELO_VENDEDOR",
  "DE_VOLTA_3STUDIO",
  "COM_MOTORISTA",
  "ENVIADA_PARA_CLICHERIA",
  "ENCAMINHADA_A_CLICHERIA",
  "RECEBIDA_PELA_CLICHERIA",
  "REPROVADA_PELO_VENDEDOR",
  "CANCELADA",
] as const;

export const ROTA_OPTIONS: readonly Rota[] = ["PADRAO", "DIRETA"] as const;

// ─── Detalhe (Componente 08) ──────────────────────────────────────────

/** Alias de `ProvaResponse` usado semanticamente no fluxo de detalhe.
 *
 * Backend devolve o mesmo schema no POST /provas/ e no GET /{id} —
 * consolidado em um tipo so para evitar divergencia acidental de
 * campos/nullability.
 */
export type ProvaDetailResponse = ProvaResponse;

/** Setor do autor de uma movimentacao (mesmos valores do backend). */
export type Setor = "STUDIO" | "VENDEDOR" | "MOTORISTA" | "CLICHERIA";

/** Item do historico de movimentacoes (Wave 2: sempre vazio).
 *
 * `assinatura_digital` NAO e exposta na API — fica como prova server-side.
 */
export interface MovimentacaoResponse {
  id: string;
  prova_id: string;
  usuario_id: string;
  usuario_nome: string;
  usuario_setor: Setor;
  status_anterior: StatusProva;
  status_novo: StatusProva;
  motivo_reprovacao: string | null;
  ciclo: number;
  rota_no_momento: Rota | null;
  created_at: string;
}

export interface MovimentacaoListResponse {
  items: MovimentacaoResponse[];
  total: number;
}

/** URL assinada GET da arte no R2 (TTL 15min). */
export interface ImagemUrlResponse {
  url: string;
  expires_at: string;
}
