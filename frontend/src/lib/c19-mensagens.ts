/**
 * Mensagens customizadas do Componente 19 (Wave 3 v4.0) — Fallback de
 * Digitacao Manual de Identificador.
 *
 * **Anti-enumeracao em camada UI (DAT v3.0 §8.2 — ADR-143).**
 *
 * O `QR_INVALIDO` retornado tanto pela validacao client-side (regex
 * local em `lib/codigo-publico.ts`) quanto pelo backend (422 Pydantic
 * para `codigo` > 32 chars no body do `/api/v1/provas/scan`) e
 * uniformizado com a mensagem de `PROVA_NAO_ENCONTRADA` (404 generico
 * do backend, mesmo texto para "inexistente" / "fora do scope" /
 * "formato invalido").
 *
 * **Sacrificio deliberado:** abrimos mao de feedback de formato no
 * cliente para preservar a anti-enumeracao DAT §8.2 — o atacante nao
 * deve conseguir distinguir "formato errado" de "fora do escopo do
 * usuario autenticado" (vetor de enumeracao por bisseccao).
 *
 * Demais codigos herdam `mensagemPara(codigo)` da camada de servico do
 * C10 (`@/lib/services/identificacao-prova`).
 *
 * **Modulo PURO** — sem React, sem DOM. Testavel em Vitest com
 * `environment: node` (sem JSDOM). Extraido de `page.tsx` em
 * 2026-05-11 pos-auditoria (AUD-W3C19-003) para permitir teste de
 * integracao da uniformizacao byte-a-byte (resolve AUD-W3C19-008
 * automaticamente).
 *
 * Testes em `__tests__/c19-mensagens.test.ts`.
 */
import {
  mensagemPara,
  MENSAGENS_ERRO_PADRAO,
  type CodigoErro,
} from "@/lib/services/identificacao-prova";

/**
 * Override de mensagens em pt-BR para o Componente 19. Somente entradas
 * que diferem do padrao de `MENSAGENS_ERRO_PADRAO` devem aparecer aqui.
 *
 * A unica override atual: `QR_INVALIDO` → texto identico ao
 * `PROVA_NAO_ENCONTRADA` (anti-enumeracao).
 */
export const MENSAGENS_C19: Partial<Record<CodigoErro, string>> = {
  QR_INVALIDO: MENSAGENS_ERRO_PADRAO.PROVA_NAO_ENCONTRADA,
};

/**
 * Retorna a mensagem final em pt-BR para exibicao no banner do
 * `<ManualPanel>`. Aplica override do C19 quando houver; caso
 * contrario, faz fallback para a mensagem padrao do C10.
 *
 * **Invariante critica:** `mensagemFinal("QR_INVALIDO") ===
 * MENSAGENS_ERRO_PADRAO.PROVA_NAO_ENCONTRADA`. Quebrar essa
 * igualdade reintroduz vetor de enumeracao. Teste de paridade
 * byte-a-byte em `__tests__/c19-mensagens.test.ts` blinda.
 */
export function mensagemFinal(codigo: CodigoErro): string {
  return MENSAGENS_C19[codigo] ?? mensagemPara(codigo);
}
