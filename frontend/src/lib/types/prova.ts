/**
 * Tipos compartilhados pelo fluxo de Provas Digitais (Componente 06).
 * Espelho fiel dos schemas Pydantic em backend/app/domain/schemas/prova.py.
 */

/**
 * Status da prova digital — 17 valores (10 v3.0 + 7 v4.0).
 *
 * Wave 3 v4.0 / Componente 11: Maquina de Estados Expandida (migration
 * 013). Os 7 novos valores cobrem as 4 rotas v4.0 (MATRIZ, LAM_MATRIZ,
 * FILIAL, LAM_FILIAL) com 3 contextos distintos do Motorista.
 *
 * Coexistencia v3.0/v4.0:
 *   - Provas legacy (rota=NULL ou PADRAO/DIRETA) usam os 10 valores
 *     v3.0 originais.
 *   - Provas v4.0 (rota IN {MATRIZ,LAM_MATRIZ,FILIAL,LAM_FILIAL}) usam
 *     os valores v4.0 novos.
 *   - `COM_MOTORISTA` (v3.0) e `COM_MOTORISTA_ENTREGA_FINAL` (v4.0)
 *     sao operacionalmente equivalentes mas DISTINTOS no enum (Decisao
 *     M-2b(a) do Gate 1 do C11).
 *
 * Espelha `StatusProvaEnum` em `backend/app/db/models.py` e o tipo
 * Postgres `status_prova_enum`. Toda alteracao exige sincronizacao
 * coordenada nas 3 camadas — ver
 * `backend/tests/test_status_prova_enum_drift.py`.
 */
export type StatusProva =
  // ── Legacy v3.0 (Wave 0 + Wave 3) ─────────────────────────────────────
  | "CRIADA"
  | "RETIRADA_PELO_VENDEDOR"
  | "APROVADA_PELO_VENDEDOR"
  | "DE_VOLTA_3STUDIO"
  | "COM_MOTORISTA"               // legacy v3.0 — 1 unico contexto
  | "ENVIADA_PARA_CLICHERIA"      // legacy v3.0 (rota PADRAO)
  | "ENCAMINHADA_A_CLICHERIA"     // legacy v3.0 (rota DIRETA)
  | "RECEBIDA_PELA_CLICHERIA"     // terminal sucesso (v3.0 + v4.0)
  | "REPROVADA_PELO_VENDEDOR"
  | "CANCELADA"                   // terminal cancelamento (v3.0 + v4.0)
  // ── v4.0 (Wave 3 / Componente 11) ─────────────────────────────────────
  // 3 contextos distintos do Motorista (US-006 v4.0)
  | "COM_MOTORISTA_IDA_LAMINACAO"
  | "COM_MOTORISTA_VOLTA_LAMINACAO"
  | "COM_MOTORISTA_ENTREGA_FINAL"
  // Etapas de laminacao (Lam. Matriz, Lam. Filial - US-005, US-007)
  | "ENCAMINHADA_PARA_LAMINACAO"
  | "LAMINACAO_CONCLUIDA"
  // Estado de retorno apos volta de laminacao (Lam. Matriz apenas)
  | "DE_VOLTA_3STUDIO_POS_LAMINACAO"
  // Vendedor Filial recebe direto (sem retirada) — Filial, Lam. Filial
  | "ENCAMINHADA_PARA_O_VENDEDOR";

/**
 * Rota de encaminhamento (Wave 2 v4.0 — Componente 06).
 *
 * Os 4 valores v4.0 (MATRIZ, LAM_MATRIZ, FILIAL, LAM_FILIAL) sao
 * escolhidos manualmente pelo Administrador na criacao da prova.
 * Os 2 valores legacy (PADRAO, DIRETA) permanecem ate a Wave 7
 * (Componente 21) fazer o backfill final — provas v3.0 ja em producao
 * continuam sendo lidas com esses valores. NUNCA enviar PADRAO/DIRETA
 * em payload de criacao (backend rejeita com 422 via RotaCriacaoEnum).
 */
export type Rota =
  | "MATRIZ"
  | "LAM_MATRIZ"
  | "FILIAL"
  | "LAM_FILIAL"
  // Legacy v3.0 — backfill na Wave 7
  | "PADRAO"
  | "DIRETA";

/**
 * Sub-tipo aceito apenas no payload de criacao (Wave 2 v4.0). Espelha
 * `RotaCriacaoEnum` do backend. Bloqueia legacy.
 */
export type RotaCriacao = "MATRIZ" | "LAM_MATRIZ" | "FILIAL" | "LAM_FILIAL";

export type Localizacao = "MATRIZ" | "FILIAL";

/** Resposta de POST /api/v1/provas/upload-url */
export interface UploadUrlResponse {
  upload_url: string;
  object_key: string;
  expires_at: string;
  max_bytes: number;
}

/** Payload de POST /api/v1/provas/ (Wave 2 v4.0).
 *
 * `rota` e obrigatorio (RN-007 v4.0) — apenas RotaCriacao (4 valores
 * v4.0) e aceita; legacy (PADRAO/DIRETA) e bloqueado pelo backend.
 */
export interface ProvaCreateRequest {
  nome: string;
  nro_requerimento: string;
  cliente: string;
  vendedor_id: string;
  rota: RotaCriacao;
  object_key: string;
}

/** Representacao publica de uma prova digital.
 *
 * Wave 2 v4.0 (Componente 06):
 *   - `codigo_publico` (NOVO) sempre presente — formato PRV-AAAA-MM-NNNNNN.
 *   - `rota_projetada` REMOVIDO — `rota` ja vem persistido com a escolha
 *     do admin desde a criacao.
 *   - `rota` continua nullable para suportar provas legadas v3.0 com
 *     `rota=NULL` (Wave 7 / Componente 21 fara o backfill).
 */
export interface ProvaResponse {
  id: string;
  nome: string;
  nro_requerimento: string;
  codigo_publico: string;
  cliente: string;
  vendedor_id: string;
  vendedor_nome: string;
  vendedor_localizacao: Localizacao | null;
  imagem_url: string;
  qr_code_hash: string;
  status: StatusProva;
  rota: Rota | null;
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

/** Type literal derivado do array — usado em narrowing sem cast. */
export type AllowedImageType = (typeof ALLOWED_IMAGE_TYPES)[number];

/** Type guard para validar `file.type` contra os MIME types permitidos
 * sem precisar de `as readonly string[]` ou `as AllowedImageType`. Sempre
 * que precisar narrowing, use este helper. */
export function isAllowedImageType(value: string): value is AllowedImageType {
  for (const allowed of ALLOWED_IMAGE_TYPES) {
    if (allowed === value) return true;
  }
  return false;
}

// ─── Listagem (Componente 07) ─────────────────────────────────────────

/** Item slim retornado por GET /api/v1/provas/ — espelho de ProvaListItem.
 *
 * Wave 2 v4.0 (Componente 06): incluiu `codigo_publico` para permitir
 * busca/exibicao direto na listagem.
 */
export interface ProvaListItem {
  id: string;
  nome: string;
  nro_requerimento: string;
  codigo_publico: string;
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

/** Labels pt-BR completos — usados no detalhe da prova (Componente 08).
 *
 * Wave 2 v4.0 / Componente 08: `CRIADA` virou "Aguardando vendedor" — o
 * label antigo "Criada" descreve apenas a transicao tecnica de insercao;
 * "Aguardando vendedor" e mais claro para o usuario sobre a acao
 * pendente. Decisao do Mario (ADR-125). */
export const STATUS_LABELS: Record<StatusProva, string> = {
  // ── Legacy v3.0 ────────────────────────────────────────────────────────
  CRIADA: "Aguardando vendedor",
  RETIRADA_PELO_VENDEDOR: "Retirada pelo vendedor",
  APROVADA_PELO_VENDEDOR: "Aprovada pelo vendedor",
  DE_VOLTA_3STUDIO: "De volta a 3Studio",
  COM_MOTORISTA: "Com motorista",
  ENVIADA_PARA_CLICHERIA: "Enviada para clicheria",
  ENCAMINHADA_A_CLICHERIA: "Encaminhada a clicheria",
  RECEBIDA_PELA_CLICHERIA: "Recebida pela clicheria",
  REPROVADA_PELO_VENDEDOR: "Reprovada pelo vendedor",
  CANCELADA: "Cancelada",
  // ── v4.0 (Wave 3 / Componente 11) ──────────────────────────────────────
  COM_MOTORISTA_IDA_LAMINACAO: "Com motorista (ida laminacao)",
  COM_MOTORISTA_VOLTA_LAMINACAO: "Com motorista (volta laminacao)",
  COM_MOTORISTA_ENTREGA_FINAL: "Com motorista (entrega final)",
  ENCAMINHADA_PARA_LAMINACAO: "Encaminhada para laminacao",
  LAMINACAO_CONCLUIDA: "Laminacao concluida",
  DE_VOLTA_3STUDIO_POS_LAMINACAO: "De volta a 3Studio (pos-laminacao)",
  ENCAMINHADA_PARA_O_VENDEDOR: "Encaminhada para o vendedor",
};

/** Labels pt-BR curtos — usados na listagem (Componente 07), onde a coluna
 * Status tem espaco limitado e o Figma pede versao abreviada. Preserva a
 * distintividade de todos os 17 estados (10 v3.0 + 7 v4.0 — Wave 3 v4.0
 * C11 migration 013). */
export const STATUS_LABELS_SHORT: Record<StatusProva, string> = {
  // ── Legacy v3.0 ────────────────────────────────────────────────────────
  CRIADA: "Aguardando",
  RETIRADA_PELO_VENDEDOR: "Retirada",
  APROVADA_PELO_VENDEDOR: "Aprovada",
  DE_VOLTA_3STUDIO: "Na 3Studio",
  COM_MOTORISTA: "Com motorista",
  ENVIADA_PARA_CLICHERIA: "Enviada",
  ENCAMINHADA_A_CLICHERIA: "Encaminhada",
  RECEBIDA_PELA_CLICHERIA: "Na clicheria",
  REPROVADA_PELO_VENDEDOR: "Reprovada",
  CANCELADA: "Cancelada",
  // ── v4.0 (Wave 3 / Componente 11) — versoes abreviadas para listagem ───
  COM_MOTORISTA_IDA_LAMINACAO: "Ida laminacao",
  COM_MOTORISTA_VOLTA_LAMINACAO: "Volta laminacao",
  COM_MOTORISTA_ENTREGA_FINAL: "Entrega final",
  ENCAMINHADA_PARA_LAMINACAO: "P/ laminar",
  LAMINACAO_CONCLUIDA: "Laminada",
  DE_VOLTA_3STUDIO_POS_LAMINACAO: "Pos-laminacao",
  ENCAMINHADA_PARA_O_VENDEDOR: "P/ vendedor",
};

/** Labels pt-BR para as rotas (Wave 2 v4.0 + atualizacao Wave 3 v4.0 / C12).
 *
 * Wave 2 v4.0 / Componente 08 (ADR-126): o sufixo "(legada v3.0)" foi
 * removido dos labels de PADRAO/DIRETA.
 *
 * Wave 3 v4.0 / Componente 12 (Decisao 11.1 do Gate 1 — supersede o
 * ADR-126): os labels legacy `PADRAO`/`DIRETA` viram `"Matriz"`/`"Filial"`
 * — alinhamento operacional com a nomenclatura v4.0. Conceitualmente
 * `PADRAO` (v3.0) e `MATRIZ` (v4.0) sao a mesma "Matriz sem laminacao"
 * para o vendedor; idem `DIRETA` e `FILIAL` ("Filial sem laminacao").
 * A distincao tecnica (sequencia de estados na timeline, ausencia de
 * laminacao) continua preservada via `LEGACY_ROTA_PADRAO`/`_DIRETA` no
 * builder da Timeline. O enum Postgres NAO eh tocado (Wave 7 fara o
 * backfill final).
 */
export const ROTA_LABELS: Record<Rota, string> = {
  MATRIZ: "Matriz",
  LAM_MATRIZ: "Lam. Matriz",
  FILIAL: "Filial",
  LAM_FILIAL: "Lam. Filial",
  PADRAO: "Matriz",
  DIRETA: "Filial",
};

/** Formata uma rota (ou ausencia dela) para exibicao na pagina de detalhe.
 *
 * Wave 2 v4.0 / C08 (Componente 06 ja consolidou a estrutura):
 * `rota_projetada` foi removido — `prova.rota` ja vem persistido com a
 * escolha do admin desde a criacao. Provas legadas v3.0 com `rota=NULL`
 * exibem "—" ate a Wave 7 (Componente 21) fazer o backfill final.
 *
 * Extraido de `(dashboard)/provas/[id]/page.tsx` na sessao pos-auditoria
 * (AUD-W2C08-003) para permitir teste unitario isolado via Vitest.
 */
export function formatRota(rota: Rota | null): string {
  if (rota) return ROTA_LABELS[rota];
  return "—";
}

/** Apenas as 4 rotas v4.0, na ordem do design (Mario): linha 1 = Matriz/Filial,
 * linha 2 = Lam. Matriz / Lam. Filial. */
export const ROTA_CRIACAO_OPTIONS: readonly RotaCriacao[] = [
  "MATRIZ",
  "FILIAL",
  "LAM_MATRIZ",
  "LAM_FILIAL",
] as const;

/** Ordem canonica dos status para exibicao em selects.
 *
 * Ordem segue a sequencia tipica de fluxo: inicio → vendedor → 3Studio
 * → laminacao (v4.0) → motorista (3 contextos v4.0 + 1 legacy) →
 * clicheria → terminais → transversais.
 *
 * Wave 3 v4.0: 17 valores totais (10 v3.0 + 7 v4.0).
 */
export const STATUS_OPTIONS: readonly StatusProva[] = [
  "CRIADA",
  "ENCAMINHADA_PARA_LAMINACAO",       // v4.0
  "COM_MOTORISTA_IDA_LAMINACAO",       // v4.0
  "LAMINACAO_CONCLUIDA",               // v4.0
  "COM_MOTORISTA_VOLTA_LAMINACAO",     // v4.0
  "DE_VOLTA_3STUDIO_POS_LAMINACAO",    // v4.0
  "ENCAMINHADA_PARA_O_VENDEDOR",       // v4.0
  "RETIRADA_PELO_VENDEDOR",
  "APROVADA_PELO_VENDEDOR",
  "DE_VOLTA_3STUDIO",
  "COM_MOTORISTA",                     // legacy v3.0
  "COM_MOTORISTA_ENTREGA_FINAL",       // v4.0
  "ENVIADA_PARA_CLICHERIA",            // legacy v3.0
  "ENCAMINHADA_A_CLICHERIA",           // legacy v3.0
  "RECEBIDA_PELA_CLICHERIA",
  "REPROVADA_PELO_VENDEDOR",
  "CANCELADA",
] as const;

/** Opcoes do filtro de rota na listagem (Componente 07).
 *
 * Wave 2 v4.0: 4 rotas novas + 2 legacy (Componente 07 continua
 * filtrando provas v3.0 ainda nao backfilled — Wave 7).
 */
export const ROTA_OPTIONS: readonly Rota[] = [
  "MATRIZ",
  "LAM_MATRIZ",
  "FILIAL",
  "LAM_FILIAL",
  "PADRAO",
  "DIRETA",
] as const;

// ─── Timeline visual (Componente 12 — Wave 3 v4.0) ────────────────────

/**
 * Tres contextos distintos do Motorista (US-006 v4.0). Espelho TS do
 * `ContextoMotorista` Python em
 * `backend/app/state_machine/v4/contextos.py`. Usado pela Timeline (C12)
 * para renderizar o badge contextual em cada nó de motorista.
 */
export type ContextoMotorista =
  | "ida_laminacao"
  | "volta_laminacao"
  | "entrega_final";

/**
 * Deriva o contexto do motorista a partir do `status_novo` da transicao.
 * Espelho do helper Python `contexto_motorista(status)` — DAT v3.0 §8.1
 * exige idempotencia entre as duas camadas. Retorna `null` se o status
 * nao representa "prova com motorista".
 *
 * Mapeamento (Decisao M-5 do Gate 1 do C11 — ADR-151):
 *   - COM_MOTORISTA_IDA_LAMINACAO    -> "ida_laminacao"
 *   - COM_MOTORISTA_VOLTA_LAMINACAO  -> "volta_laminacao"
 *   - COM_MOTORISTA_ENTREGA_FINAL    -> "entrega_final"
 *   - COM_MOTORISTA (legacy v3.0)    -> "entrega_final" (compat)
 *   - Qualquer outro                 -> null
 */
export function contextoMotorista(
  status: StatusProva,
): ContextoMotorista | null {
  if (status === "COM_MOTORISTA_IDA_LAMINACAO") return "ida_laminacao";
  if (status === "COM_MOTORISTA_VOLTA_LAMINACAO") return "volta_laminacao";
  if (status === "COM_MOTORISTA_ENTREGA_FINAL") return "entrega_final";
  if (status === "COM_MOTORISTA") return "entrega_final"; // legacy v3.0
  return null;
}

/**
 * Conjunto dos estados que compoem a "Etapa de Laminacao" no fluxo v4.0.
 * Sequencia adjacente de nos com `isInLaminationBlock(node.status) ===
 * true` forma o bloco visual destacado pelo C12 (Decisao 3 do Gate 1
 * do C12 — opcao A: bloco visualmente separado).
 *
 * Cobre Lam. Matriz (5 estados) e Lam. Filial (3 estados — sem
 * volta_laminacao nem pos_laminacao, pois vendedor+clicheria estao
 * ambos na Filial).
 */
export const ESTADOS_LAMINACAO: readonly StatusProva[] = [
  "ENCAMINHADA_PARA_LAMINACAO",
  "COM_MOTORISTA_IDA_LAMINACAO",
  "LAMINACAO_CONCLUIDA",
  "COM_MOTORISTA_VOLTA_LAMINACAO", // so Lam. Matriz
  "DE_VOLTA_3STUDIO_POS_LAMINACAO", // so Lam. Matriz
] as const;

/** True se o status pertence ao bloco visual de laminacao. */
export function isInLaminationBlock(status: StatusProva): boolean {
  return (ESTADOS_LAMINACAO as readonly string[]).includes(status);
}

/**
 * Sequencia canonica de estados por rota v4.0 — espelha
 * `estados_da_rota(rota)` do backend, mas com ORDEM (o backend devolve
 * `frozenset`). Ordem derivada literalmente da Secao 5 do Requisitos
 * v4.0 + UML 06.x.
 *
 * Inclui CRIADA (origem) e RECEBIDA_PELA_CLICHERIA (terminal sucesso);
 * NAO inclui REPROVADA_PELO_VENDEDOR nem CANCELADA — sao transversais
 * (Decisao 7 do Gate 1 do C12: renderizadas como ramificacoes visuais).
 *
 * Tamanhos: MATRIZ=6 · LAM_MATRIZ=11 · FILIAL=4 · LAM_FILIAL=7.
 */
export const ROTA_ETAPAS: Record<RotaCriacao, readonly StatusProva[]> = {
  MATRIZ: [
    "CRIADA",
    "RETIRADA_PELO_VENDEDOR",
    "APROVADA_PELO_VENDEDOR",
    "DE_VOLTA_3STUDIO",
    "COM_MOTORISTA_ENTREGA_FINAL",
    "RECEBIDA_PELA_CLICHERIA",
  ],
  LAM_MATRIZ: [
    "CRIADA",
    "ENCAMINHADA_PARA_LAMINACAO",
    "COM_MOTORISTA_IDA_LAMINACAO",
    "LAMINACAO_CONCLUIDA",
    "COM_MOTORISTA_VOLTA_LAMINACAO",
    "DE_VOLTA_3STUDIO_POS_LAMINACAO",
    "RETIRADA_PELO_VENDEDOR",
    "APROVADA_PELO_VENDEDOR",
    "DE_VOLTA_3STUDIO",
    "COM_MOTORISTA_ENTREGA_FINAL",
    "RECEBIDA_PELA_CLICHERIA",
  ],
  FILIAL: [
    "CRIADA",
    "ENCAMINHADA_PARA_O_VENDEDOR",
    "APROVADA_PELO_VENDEDOR",
    "RECEBIDA_PELA_CLICHERIA",
  ],
  LAM_FILIAL: [
    "CRIADA",
    "ENCAMINHADA_PARA_LAMINACAO",
    "COM_MOTORISTA_IDA_LAMINACAO",
    "LAMINACAO_CONCLUIDA",
    "ENCAMINHADA_PARA_O_VENDEDOR",
    "APROVADA_PELO_VENDEDOR",
    "RECEBIDA_PELA_CLICHERIA",
  ],
} as const;

/**
 * Sequencia legacy v3.0 — rota PADRAO. Cobre 7 estados (com `COM_MOTORISTA`
 * legacy + `ENVIADA_PARA_CLICHERIA`, que NAO existem nas rotas v4.0).
 * Conceitualmente equivalente a `MATRIZ` v4.0 mas com 1 etapa extra
 * (`ENVIADA_PARA_CLICHERIA`).
 */
export const LEGACY_ROTA_PADRAO: readonly StatusProva[] = [
  "CRIADA",
  "RETIRADA_PELO_VENDEDOR",
  "APROVADA_PELO_VENDEDOR",
  "DE_VOLTA_3STUDIO",
  "COM_MOTORISTA",
  "ENVIADA_PARA_CLICHERIA",
  "RECEBIDA_PELA_CLICHERIA",
] as const;

/**
 * Sequencia legacy v3.0 — rota DIRETA. Cobre 5 estados (com
 * `ENCAMINHADA_A_CLICHERIA`, que NAO existe nas rotas v4.0).
 * Conceitualmente equivalente a `FILIAL` v4.0 mas com `RETIRADA` em vez
 * de `ENCAMINHADA_PARA_O_VENDEDOR`.
 */
export const LEGACY_ROTA_DIRETA: readonly StatusProva[] = [
  "CRIADA",
  "RETIRADA_PELO_VENDEDOR",
  "APROVADA_PELO_VENDEDOR",
  "ENCAMINHADA_A_CLICHERIA",
  "RECEBIDA_PELA_CLICHERIA",
] as const;

/**
 * Resolve a sequencia canonica que a Timeline (C12) deve renderizar.
 *
 * Wave 3 v4.0 / C12 — Decisao 11.2 do Gate 1: provas com `rota=NULL`
 * usam heuristica baseada em `vendedor_localizacao` para inferir a
 * sequencia legacy compativel. Em producao (validado via MCP) as 11
 * provas com `rota=NULL` tem todas `vendedor_localizacao=FILIAL`,
 * logo recebem `LEGACY_ROTA_DIRETA`.
 *
 * - rota v4.0 (MATRIZ/LAM_MATRIZ/FILIAL/LAM_FILIAL) -> ROTA_ETAPAS[rota]
 * - rota legacy PADRAO -> LEGACY_ROTA_PADRAO
 * - rota legacy DIRETA -> LEGACY_ROTA_DIRETA
 * - rota=NULL + vendedor MATRIZ -> LEGACY_ROTA_PADRAO
 * - rota=NULL + vendedor FILIAL -> LEGACY_ROTA_DIRETA
 * - rota=NULL + vendedor=NULL  -> [] (fallback: so historico real)
 */
export function getRotaEtapas(
  rota: Rota | null,
  vendedorLocalizacao: Localizacao | null,
): readonly StatusProva[] {
  if (
    rota === "MATRIZ" ||
    rota === "LAM_MATRIZ" ||
    rota === "FILIAL" ||
    rota === "LAM_FILIAL"
  ) {
    return ROTA_ETAPAS[rota];
  }
  if (rota === "PADRAO") return LEGACY_ROTA_PADRAO;
  if (rota === "DIRETA") return LEGACY_ROTA_DIRETA;
  // rota IS NULL — heuristica via Decisao 11.2 do C12
  if (vendedorLocalizacao === "MATRIZ") return LEGACY_ROTA_PADRAO;
  if (vendedorLocalizacao === "FILIAL") return LEGACY_ROTA_DIRETA;
  return [];
}

/**
 * Resolve o label de rota a exibir no header da Timeline.
 *
 * Wave 3 v4.0 / C12 — Decisoes 11.1 e 11.2 do Gate 1:
 * - Rotas v4.0 e legacy nao-nulas: usa `ROTA_LABELS` (PADRAO/DIRETA ja
 *   renomeadas para "Matriz"/"Filial" — supersede ADR-126).
 * - rota=NULL: heuristica via `vendedor_localizacao` para devolver
 *   "Matriz" ou "Filial". Fallback "—" se nao houver localizacao.
 */
export function getRotaLabel(
  rota: Rota | null,
  vendedorLocalizacao: Localizacao | null,
): string {
  if (rota) return ROTA_LABELS[rota];
  if (vendedorLocalizacao === "MATRIZ") return "Matriz";
  if (vendedorLocalizacao === "FILIAL") return "Filial";
  return "—";
}

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

/** Request de `POST /api/v1/provas/scan`.
 *
 * Wave 3 v4.0 (Componente 10): aceita XOR entre `payload` (caminho
 * camera) e `codigo` (caminho digitacao manual — Componente 19). O
 * backend valida via `model_validator` que exatamente um dos dois esta
 * presente.
 *
 * - `payload`: "3SD|<id>|<hash[:16]>". O segundo campo pode ser:
 *     · `codigo_publico` (PRV-AAAA-MM-NNNNNN) — provas v4.0+
 *     · `nro_requerimento` (string livre) — provas legacy v3.0
 *   Backend detecta pelo formato e usa o lookup apropriado.
 * - `codigo`: codigo publico legivel `PRV-AAAA-MM-NNNNNN`. Caminho
 *   canonico do C19. Resolve direto pela coluna `codigo_publico`.
 */
export interface ScanRequest {
  payload?: string;
  codigo?: string;
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

// ─── Dashboard (Componente 15 — Wave 4) ─────────────────────────────────

/** Contadores agregados do dashboard (RF-014). */
export interface DashboardContadores {
  criadas_hoje: number;
  com_vendedor: number;
  aprovadas: number;
  reprovadas: number;
  aguardando_envio: number;
  com_motorista: number;
  na_clicheria: number;
  concluidas: number;
  atrasadas: number;
}

/** Item do breakdown de atrasadas por vendedor. */
export interface AtrasadaPorVendedor {
  vendedor_nome: string;
  quantidade: number;
}

/** Resposta de GET /api/v1/provas/dashboard. */
export interface DashboardResponse {
  contadores: DashboardContadores;
  total_ativas: number;
  tempo_atraso_horas: number;
  atrasadas_por_vendedor: AtrasadaPorVendedor[];
  atualizado_em: string;
}


/** Monta o payload escaneavel do QR Code a partir dos dados da prova.
 *
 * Wave 2 v4.0: o segundo campo passa a ser `codigo_publico`
 * (PRV-AAAA-MM-NNNNNN) em vez de `nro_requerimento` — DAT v3.0 §8.1
 * exige idempotencia entre camera e digitacao manual (Componente 19,
 * Wave 3 v4.0). Formato: "3SD|{codigo_publico}|{hash[:16]}".
 *
 * Espelho de `qrcode_service.gerar_payload_qr` no backend.
 */
export function buildQrPayload(
  identificador: string,
  qrCodeHash: string,
): string {
  return `3SD|${identificador}|${qrCodeHash.substring(0, 16)}`;
}
