/**
 * Camada de servico de identificacao de provas — Wave 3 v4.0, Componente 10.
 *
 * Contrato compartilhado entre:
 *   - **Camera** (este Componente 10): apos `html5-qrcode` decodificar a
 *     imagem, chama `identificarProvaPorPayload(payload)` com o payload
 *     completo (`3SD|<id>|<hash[:16]>`).
 *   - **Digitacao manual** (Componente 19, Wave 3 v4.0): apos o usuario
 *     digitar o codigo da etiqueta, chama `identificarProvaPorCodigo(codigo)`
 *     com o codigo isolado (`PRV-AAAA-MM-NNNNNN`).
 *
 * **Decisao chave (analysis.md §5.2 + ADR registrado):** o backend
 * `POST /api/v1/provas/scan` ja foi estendido para aceitar `payload`
 * XOR `codigo`. Esta camada apenas escolhe qual campo enviar; o backend
 * faz o lookup polimorfico apropriado e retorna a mesma `ScanResponse`.
 *
 * **Zero acoplamento com hardware** — esta camada e intencionalmente
 * pura quanto a `navigator`/`document`/`window`. Imports de DOM ou de
 * libs de camera (`html5-qrcode`) sao proibidos. Vitest roda este modulo
 * em `environment: node` (sem JSDOM) — qualquer regressao de
 * acoplamento quebra `npx vitest run` imediatamente.
 *
 * Testes em `__tests__/identificacao-prova.test.ts`.
 *
 * Ver tambem:
 *   - `docs/wave3-v4-c10/contrato-c19.md` — guia detalhado para o C19
 *   - DAT v3.0 §8.1 (idempotencia camera ↔ manual)
 *   - DAT v3.0 §8.2 (protecao contra enumeracao)
 */
import { apiFetch, ApiError } from "@/lib/api";
import type { ScanResponse } from "@/lib/types/prova";

/**
 * Codigos de erro tipados retornados ao chamador. Cada um tem mensagem
 * em pt-BR pre-resolvida — chamador apenas renderiza.
 */
export type CodigoErro =
  /** Payload do QR mal formado (estrutura), hash invalido ou body sem
   *  payload nem codigo. Backend retornou 422. */
  | "QR_INVALIDO"
  /** Codigo nao existe OU esta fora do escopo do usuario (RLS filtra).
   *  Mesma mensagem para os 2 casos — DAT §8.2 protecao contra
   *  enumeracao. Backend retornou 404. */
  | "PROVA_NAO_ENCONTRADA"
  /** `getUserMedia` indisponivel OU permissao de camera negada pelo
   *  browser. Setado pelo `useScanner` ao falhar a inicializacao. */
  | "DISPOSITIVO_SEM_CAMERA"
  /** 5xx no backend ou network failure (fetch threw). */
  | "ERRO_REDE"
  /** Token ausente, expirado ou invalido. Backend retornou 401. */
  | "SESSAO_EXPIRADA";

/**
 * Resultado da identificacao — tagged union.
 *
 * Padrao adotado para garantir que TODO call site do servico precisa
 * tratar AMBOS os casos via narrowing (`if result.tipo === 'sucesso'`)
 * — TypeScript impede esquecer de tratar o erro silenciosamente.
 */
export type ResultadoIdentificacao =
  | { tipo: "sucesso"; prova: ScanResponse }
  | { tipo: "erro"; codigo: CodigoErro; mensagem: string };

/** Mensagens em pt-BR mapeadas por codigo de erro. Sao retornadas ao
 *  chamador via `result.mensagem` para renderizacao direta.
 *
 *  **Exportada (AUD-W3C10-020)** para permitir que o Componente 19
 *  (digitacao manual) customize ou reutilize as mensagens. O record e
 *  exhaustivo por construcao (`Record<CodigoErro, string>` — TypeScript
 *  forca uma entrada por codigo; novo codigo na uniao quebra o build se
 *  faltar a entrada correspondente). */
export const MENSAGENS_ERRO_PADRAO: Record<CodigoErro, string> = {
  QR_INVALIDO:
    "QR Code nao reconhecido. Verifique se esta escaneando uma etiqueta de prova.",
  PROVA_NAO_ENCONTRADA: "Prova nao encontrada.",
  DISPOSITIVO_SEM_CAMERA: "Camera indisponivel. Use a digitacao manual.",
  ERRO_REDE: "Falha de conexao. Tente novamente em instantes.",
  SESSAO_EXPIRADA: "Sua sessao expirou. Faca login novamente.",
};

/** Helper para consumidores externos (Componente 19) que querem
 *  reutilizar a mensagem padrao de um codigo de erro sem importar o
 *  record inteiro. Util para condicionar exibicao por `result.codigo`. */
export function mensagemPara(codigo: CodigoErro): string {
  return MENSAGENS_ERRO_PADRAO[codigo];
}

/** Cria um erro tipado com mensagem padrao. Usar no lugar de literais. */
export function criarErro(codigo: CodigoErro): ResultadoIdentificacao {
  return { tipo: "erro", codigo, mensagem: MENSAGENS_ERRO_PADRAO[codigo] };
}

interface IdentificarParams {
  /** Funcao que devolve o token JWT atual. Recebida do chamador para
   *  manter o servico desacoplado do Supabase client. */
  getToken: () => Promise<string | null>;
}

/**
 * Identifica uma prova pelo **payload completo do QR Code** lido pela
 * camera (caminho do Componente 10).
 *
 * O segundo campo do payload pode ser:
 *   - `codigo_publico` (PRV-AAAA-MM-NNNNNN) — provas v4.0+ (caminho
 *     canonico).
 *   - `nro_requerimento` (string livre) — provas legacy v3.0 cujo QR
 *     foi gerado antes da migration 012.
 *
 * O backend (`POST /api/v1/provas/scan`) detecta o formato e usa o
 * lookup apropriado. Esta camada apenas envia.
 */
export async function identificarProvaPorPayload(
  payload: string,
  params: IdentificarParams,
): Promise<ResultadoIdentificacao> {
  return _identificar({ payload }, params);
}

/**
 * Identifica uma prova pelo **codigo publico legivel** digitado
 * manualmente (caminho do Componente 19, contrato pronto).
 *
 * Formato esperado: `PRV-AAAA-MM-NNNNNN`. O backend valida o formato e
 * retorna 404 generico (mesma mensagem de "fora do scope") em caso de
 * formato invalido, alinhado a DAT §8.2.
 *
 * O C19 pode adicionar mascara de digitacao em tempo real e validacao
 * client-side por cima desta camada — mas a chamada ao backend
 * continua sendo via esta funcao.
 */
export async function identificarProvaPorCodigo(
  codigo: string,
  params: IdentificarParams,
): Promise<ResultadoIdentificacao> {
  return _identificar({ codigo }, params);
}

// ── Implementacao compartilhada ───────────────────────────────────────

interface ScanBody {
  payload?: string;
  codigo?: string;
}

async function _identificar(
  body: ScanBody,
  params: IdentificarParams,
): Promise<ResultadoIdentificacao> {
  // 1) Resolve o token de autenticacao.
  let token: string | null;
  try {
    token = await params.getToken();
  } catch {
    return criarErro("SESSAO_EXPIRADA");
  }
  if (!token) {
    return criarErro("SESSAO_EXPIRADA");
  }

  // 2) Faz a chamada via apiFetch (padrao do projeto).
  try {
    const result = await apiFetch<ScanResponse>("/api/v1/provas/scan", {
      method: "POST",
      token,
      body: JSON.stringify(body),
    });
    return { tipo: "sucesso", prova: result };
  } catch (err) {
    return _mapearErro(err);
  }
}

/** Traduz erro do `apiFetch` em codigo tipado pt-BR. */
function _mapearErro(err: unknown): ResultadoIdentificacao {
  if (err instanceof ApiError) {
    if (err.status === 401) {
      return criarErro("SESSAO_EXPIRADA");
    }
    if (err.status === 404) {
      return criarErro("PROVA_NAO_ENCONTRADA");
    }
    if (err.status === 422) {
      return criarErro("QR_INVALIDO");
    }
    if (err.status >= 500) {
      return criarErro("ERRO_REDE");
    }
  }
  // Fetch threw (network down, etc.) ou status nao mapeado: trata como rede.
  return criarErro("ERRO_REDE");
}
