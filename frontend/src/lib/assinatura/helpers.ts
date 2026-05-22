/**
 * Helpers puros do fluxo de assinatura — Wave 8 v5.0 / Componente 22
 * (Reativacao da Tela de Assinatura no Fluxo de Escaneamento).
 *
 * Modulo SEM acoplamento com DOM/React/camera — testavel em
 * `vitest --environment node` (mesmo padrao da camada de servico
 * `identificacao-prova.ts`, decisao D-13 da Wave 1 v4.0). A logica de
 * decisao do C22 (abrir assinatura vs ir ao detalhe) e os labels v4.0
 * vivem aqui para serem cobertos por testes unitarios isolados.
 */
import {
  STATUS_LABELS,
  contextoMotorista,
  type ScanResponse,
  type StatusProva,
} from "@/lib/types/prova";

/**
 * Verbos de acao por estado-destino de transicao (pt-BR).
 *
 * Record EXAUSTIVO dos 17 estados (10 v3.0 + 7 v4.0) — TypeScript barra
 * o build se a `StatusProva` ganhar um valor sem verbo aqui. Estende o
 * `ACTION_LABELS` recuperado da arqueologia (vocabulario v3.0, 8 verbos)
 * para cobrir os 7 estados v4.0 (risco R-10 da analysis).
 *
 * `CRIADA` e `CANCELADA` nunca chegam como `status_novo` via
 * `POST /transicoes` (rejeitados pelo `TransicaoRequest`), mas constam
 * para a exaustividade do Record.
 */
export const ACTION_LABELS: Record<StatusProva, string> = {
  // ── Legacy v3.0 ───────────────────────────────────────────────────────
  CRIADA: "Reiniciar ciclo",
  RETIRADA_PELO_VENDEDOR: "Retirar prova",
  APROVADA_PELO_VENDEDOR: "Aprovar",
  REPROVADA_PELO_VENDEDOR: "Reprovar",
  DE_VOLTA_3STUDIO: "Confirmar recebimento na 3Studio",
  COM_MOTORISTA: "Confirmar transporte",
  ENVIADA_PARA_CLICHERIA: "Confirmar envio a clicheria",
  ENCAMINHADA_A_CLICHERIA: "Encaminhar a clicheria",
  RECEBIDA_PELA_CLICHERIA: "Confirmar recebimento final",
  CANCELADA: "Cancelar prova",
  // ── v4.0 (Wave 3 / Componente 11) ─────────────────────────────────────
  COM_MOTORISTA_IDA_LAMINACAO: "Confirmar travessia (ida laminacao)",
  COM_MOTORISTA_VOLTA_LAMINACAO: "Confirmar travessia (volta laminacao)",
  COM_MOTORISTA_ENTREGA_FINAL: "Confirmar entrega final",
  ENCAMINHADA_PARA_LAMINACAO: "Encaminhar para laminacao",
  LAMINACAO_CONCLUIDA: "Confirmar laminacao concluida",
  DE_VOLTA_3STUDIO_POS_LAMINACAO: "Confirmar recebimento (pos-laminacao)",
  ENCAMINHADA_PARA_O_VENDEDOR: "Encaminhar para o vendedor",
};

/** Verbo de acao para uma transicao de destino. */
export function labelParaTransicao(destino: StatusProva): string {
  return ACTION_LABELS[destino];
}

/** True se a transicao escolhida e uma reprovacao (RF-008 — exige motivo). */
export function isReprovacao(destino: StatusProva): boolean {
  return destino === "REPROVADA_PELO_VENDEDOR";
}

/**
 * Decisao central do C22 (regra unica confirmada pelo Mario):
 * dado o resultado do `/scan`, o usuario logado e o proximo ator
 * habilitado?
 *
 * `transicoes_permitidas` ja vem filtrado pelo backend para o usuario
 * corrente (`_computar_transicoes_permitidas` -> maquina v4.0 ou v3.0).
 *   - nao-vazio  => e a vez dele  => abrir a tela de assinatura.
 *   - vazio      => NAO e a vez dele OU prova terminal => abrir
 *                   `/provas/[id]` (Decisao D6 — ator-errado in-scope
 *                   vai ao detalhe, sem mensagem de bloqueio; o
 *                   ator-errado fora-de-escopo ja recebeu 404 antes
 *                   de chegar aqui).
 */
export function deveAbrirAssinatura(scan: ScanResponse): boolean {
  return scan.transicoes_permitidas.length > 0;
}

/**
 * True se a transicao para `destino` exige motivo obrigatorio. Consulta
 * `motivo_obrigatorio_em` do `/scan` — fonte de verdade do backend
 * (Wave 3 Lote A: apenas `REPROVADA_PELO_VENDEDOR`, via RF-007/RF-008).
 */
export function exigeMotivo(scan: ScanResponse, destino: StatusProva): boolean {
  return scan.motivo_obrigatorio_em.includes(destino);
}

/**
 * Texto de contexto da travessia do motorista, derivado do estado-destino
 * da transicao. Espelha `contextoMotorista()` de `prova.ts` (3 contextos
 * — US-006 v4.0). Retorna `null` para transicoes que nao sao de motorista
 * (sem badge de contexto).
 */
export function badgeContextoMotorista(destino: StatusProva): string | null {
  const ctx = contextoMotorista(destino);
  if (ctx === "ida_laminacao") return "Travessia: ida para a laminacao";
  if (ctx === "volta_laminacao") return "Travessia: volta da laminacao";
  if (ctx === "entrega_final") return "Travessia: entrega final a clicheria";
  return null;
}

/** Frase "Estado atual -> Estado destino" para exibir no modal. */
export function descricaoTransicao(
  statusAtual: StatusProva,
  destino: StatusProva,
): string {
  return `${STATUS_LABELS[statusAtual]} → ${STATUS_LABELS[destino]}`;
}

/**
 * Titulo do modal de assinatura para uma transicao escolhida. Tres casos
 * que leem bem como cabecalho — o verbo especifico fica no botao
 * (`labelParaTransicao`) e o detalhe na linha `descricaoTransicao`.
 */
export function tituloAssinatura(destino: StatusProva): string {
  if (destino === "REPROVADA_PELO_VENDEDOR") return "Reprovar prova";
  if (destino === "APROVADA_PELO_VENDEDOR") return "Aprovar prova";
  return "Confirmar movimentacao";
}
