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

/** Labels pt-BR completos — usados no detalhe da prova (Componente 08). */
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

/** Labels pt-BR curtos — usados na listagem (Componente 07), onde a coluna
 * Status tem espaco limitado e o Figma pede versao abreviada. Preserva a
 * distintividade de todos os 10 estados. */
export const STATUS_LABELS_SHORT: Record<StatusProva, string> = {
  CRIADA: "Criada",
  RETIRADA_PELO_VENDEDOR: "Retirada",
  APROVADA_PELO_VENDEDOR: "Aprovada",
  DE_VOLTA_3STUDIO: "Na 3Studio",
  COM_MOTORISTA: "Com motorista",
  ENVIADA_PARA_CLICHERIA: "Enviada",
  ENCAMINHADA_A_CLICHERIA: "Encaminhada",
  RECEBIDA_PELA_CLICHERIA: "Na clicheria",
  REPROVADA_PELO_VENDEDOR: "Reprovada",
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

// ─── Scan + Transicao (Componentes 10 e 11 — Wave 3 Lote A) ──────────

/** Request de `POST /api/v1/provas/scan` (sub-bloco A.3).
 *
 * Formato esperado do `payload`: "3SD|{nro_requerimento}|{hash_truncado}"
 * (hash truncado = 16 chars hex). O backend valida estrutura + integridade
 * (hash HMAC constant-time) e retorna os dados da prova + as transicoes
 * que o usuario corrente pode executar.
 */
export interface ScanRequest {
  payload: string;
}

/** Response de `POST /api/v1/provas/scan`.
 *
 * `transicoes_permitidas` e a lista de destinos validos para o usuario
 * corrente — a UI renderiza um botao por item. `motivo_obrigatorio_em`
 * e subset de `transicoes_permitidas` onde o usuario deve informar motivo
 * (Wave 3 Lote A: apenas `REPROVADA_PELO_VENDEDOR`, via RF-007).
 *
 * Contrato garantido pelo backend: toda transicao em
 * `transicoes_permitidas` tambem passa no endpoint de transicao para
 * este usuario — nao renderizamos botao que seria rejeitado no submit.
 */
export interface ScanResponse {
  prova: ProvaResponse;
  transicoes_permitidas: StatusProva[];
  motivo_obrigatorio_em: StatusProva[];
}

/** Request de `POST /api/v1/provas/{prova_id}/transicoes` (sub-bloco A.4).
 *
 * - `status_novo` nao pode ser `CANCELADA` (gancho Componente 13) nem
 *   `CRIADA` (gancho Componente 14) — o backend rejeita com 422 via
 *   validator Pydantic.
 * - `assinatura_base64` e o PNG do canvas do `react-signature-canvas`
 *   com o prefixo `data:image/png;base64,` removido (use
 *   `.split(",")[1]`). Max 700_000 chars ≈ 525 KB de PNG decodificado.
 * - `motivo_reprovacao` eh obrigatorio sse `status_novo ===
 *   "REPROVADA_PELO_VENDEDOR"` (RF-007). A validacao cruzada acontece
 *   no handler backend, nao no schema.
 */
export interface TransicaoRequest {
  status_novo: StatusProva;
  assinatura_base64: string;
  motivo_reprovacao?: string | null;
}

/** Response de `POST /api/v1/provas/{prova_id}/transicoes`.
 *
 * Retornado com HTTP 201 apos a transicao ser efetivada. O frontend usa
 * `prova` para atualizar o card exibido e `movimentacao` para exibir
 * sucesso (ou para atualizar a timeline localmente sem refetch).
 */
export interface TransicaoResponse {
  prova: ProvaResponse;
  movimentacao: MovimentacaoResponse;
}

/** Limite canonico de bytes do base64 da assinatura — espelho de
 * `ASSINATURA_BASE64_MAX_BYTES` em schemas/prova.py. */
export const ASSINATURA_BASE64_MAX_BYTES = 700_000;

/** Monta o payload escaneavel do QR Code a partir dos dados da prova.
 *
 * Formato: "3SD|{nro_requerimento}|{hash[:16]}"
 * Espelho de `qrcode_service.gerar_payload_qr` no backend.
 */
export function buildQrPayload(
  nroRequerimento: string,
  qrCodeHash: string,
): string {
  return `3SD|${nroRequerimento}|${qrCodeHash.substring(0, 16)}`;
}
