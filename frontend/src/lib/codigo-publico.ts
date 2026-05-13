/**
 * Util de codigo publico — Wave 3 v4.0 / Componente 19.
 *
 * Espelho do backend `backend/app/services/codigo_publico_service.py`:
 *   - Formato: PRV-AAAA-MM-NNNNNN (18 chars total)
 *   - Prefixo fixo: "PRV"
 *   - Ano: 4 digitos
 *   - Mes: 2 digitos (01-12)
 *   - Sufixo: 6 chars do alfabeto sem ambiguos (A-Z + 2-9, sem 0/O/1/I/L)
 *
 * **Decisao chave (ADR registrado):** o alfabeto vale POR POSICAO.
 *   - Posicoes 0-3 (ano) e 4-5 (mes): apenas digitos 0-9.
 *   - Posicoes 6-11 (sufixo): apenas chars do `ALFABETO_SUFIXO`.
 *
 * **Constraint dura:** modulo PURO. Zero acoplamento com DOM, React,
 * `navigator`, `document` ou `window`. Testavel em Vitest com
 * `environment: node` (sem JSDOM) — mesma propriedade da camada de
 * servico do C10. Hook React (`useCodigoPrvInput`) consome estas
 * funcoes mas nao as estende.
 *
 * Testes em `__tests__/codigo-publico.test.ts`.
 */

/** Alfabeto do sufixo NNNNNN — 31 chars sem ambiguos (DAT v3.0 §8.3). */
export const ALFABETO_SUFIXO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";

/** Tamanho fixo do codigo canonico. */
export const CODIGO_PUBLICO_TOTAL_LEN = 18;

/** Tamanho do display sem o prefixo "PRV-" (= 14 chars). */
export const DISPLAY_TOTAL_LEN = 14;

/** Tamanho do sufixo alfanumerico. */
export const SUFIXO_LEN = 6;

/** Regex canonico — equivalente ao backend `validar_formato_codigo_publico`.
 *
 * Exportada para consumidores que precisem `.test()` direto, mas o caminho
 * recomendado e usar `validarFormatoCodigoPublico(codigo)`. */
export const CODIGO_PUBLICO_REGEX =
  /^PRV-\d{4}-(0[1-9]|1[0-2])-[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{6}$/;

/**
 * Valida o formato completo `PRV-AAAA-MM-NNNNNN`.
 *
 * Paridade com `backend/app/services/codigo_publico_service.py:validar_formato_codigo_publico`
 * — qualquer divergencia deve ser flagrada por teste de paridade
 * (`__tests__/codigo-publico.test.ts` rodando 5 casos copiados do backend).
 */
export function validarFormatoCodigoPublico(codigo: string): boolean {
  if (typeof codigo !== "string") return false;
  return CODIGO_PUBLICO_REGEX.test(codigo);
}

/**
 * Decide se um char e valido na posicao do **display** (sem prefixo).
 *
 * Display tem 14 chars com 2 hifens fixos:
 *   posicoes 0-3   → ano (digitos 0-9)
 *   posicao  4     → hifen literal "-"
 *   posicoes 5-6   → mes (digitos 0-9)
 *   posicao  7     → hifen literal "-"
 *   posicoes 8-13  → sufixo (ALFABETO_SUFIXO)
 *
 * Esta funcao opera sobre a versao SEM hifens (apenas chars significativos).
 * O hifen e inserido por `aplicarMascara`.
 */
export function isCharValidoEmPosicaoSemHifen(c: string, pos: number): boolean {
  if (c.length !== 1) return false;
  if (pos < 4) {
    // ano — digitos 0-9
    return c >= "0" && c <= "9";
  }
  if (pos < 6) {
    // mes — digitos 0-9 (validacao de range 01-12 acontece no formato final)
    return c >= "0" && c <= "9";
  }
  if (pos < 12) {
    // sufixo
    return ALFABETO_SUFIXO.includes(c);
  }
  return false;
}

/**
 * Aplica a mascara `YYYY-MM-NNNNNN` em uma entrada crua do usuario.
 *
 * Comportamento:
 *   - Strip do prefixo "PRV-" / "prv-" / "PRV" se presente no inicio (paste-friendly).
 *   - Auto-uppercase.
 *   - Filtra chars por posicao (D5: bloqueio rigido).
 *   - Insere hifens automaticamente apos pos 4 (ano) e pos 7 (ano+mes).
 *   - Trunca em DISPLAY_TOTAL_LEN (14 chars com 2 hifens).
 *
 * @param raw Entrada crua do usuario. Em uso normal, sempre vem de
 *   `e.target.value` de um `<input>` — portanto string. A salvaguarda
 *   `typeof raw !== "string"` cobre apenas chamadas indevidas (testes,
 *   refatoracoes, integracoes externas que possam passar `null`,
 *   `undefined`, `number`, etc.) — nestes casos retorna `""`
 *   **silenciosamente** (AUD-W3C19-006). NAO lanca excecao para evitar
 *   crashar a UI; o input simplesmente fica vazio, o que e detectavel
 *   pelo chamador via `isDisplayCompleto`/`validarFormatoCodigoPublico`.
 *
 * @returns Display formatado `YYYY-MM-NNNNNN` (sem prefixo "PRV-"), ou
 *   `""` quando o input nao produz nenhum char significativo (vazio,
 *   apenas separadores ou apenas chars invalidos) — ou quando `raw`
 *   nao e string.
 *
 * Determinismo: pura, idempotente
 * (`aplicarMascara(aplicarMascara(x)) === aplicarMascara(x)`).
 */
export function aplicarMascara(raw: string): string {
  // AUD-W3C19-006: entrada nao-string retorna "" silenciosamente.
  // Documentado no JSDoc acima — risco real em uso normal e zero
  // (e.target.value e sempre string).
  if (typeof raw !== "string") return "";
  // 1) Strip prefixo PRV-/PRV ao normalizar para upper.
  const upper = raw.toUpperCase();
  const semPrefixo = upper.replace(/^PRV-?/, "");
  // 2) Coleta apenas chars significativos (sem hifens, validos por posicao).
  const semHifens: string[] = [];
  for (const c of semPrefixo) {
    if (c === "-") continue; // descarta hifens do input — vamos re-inserir
    const pos = semHifens.length;
    if (pos >= 12) break; // alcancou tamanho maximo do conteudo
    if (isCharValidoEmPosicaoSemHifen(c, pos)) {
      semHifens.push(c);
    }
    // Char invalido: ignora silenciosamente (D5 bloqueio rigido).
  }
  // 3) Re-monta o display com hifens em pos 4 (ano|mes) e pos 7 (mes|sufixo).
  const ano = semHifens.slice(0, 4).join("");
  const mes = semHifens.slice(4, 6).join("");
  const sufixo = semHifens.slice(6, 12).join("");
  let out = ano;
  if (semHifens.length > 4) out += "-" + mes;
  if (semHifens.length > 6) out += "-" + sufixo;
  return out;
}

/**
 * Concatena o prefixo "PRV-" ao display formatado para produzir o codigo
 * canonico enviado ao backend.
 *
 * `display` deve estar no formato `YYYY-MM-NNNNNN` (saida de `aplicarMascara`).
 * Se display estiver vazio, retorna "" — chamador decide se chama backend.
 */
export function montarCodigoCompleto(display: string): string {
  if (!display) return "";
  return `PRV-${display}`;
}

/**
 * Indica se o display tem o tamanho de um codigo completo (14 chars).
 * NAO valida que os componentes (ano/mes/sufixo) sao individualmente
 * validos — para isso, combinar com `validarFormatoCodigoPublico` no
 * codigo montado.
 */
export function isDisplayCompleto(display: string): boolean {
  return display.length === DISPLAY_TOTAL_LEN;
}
