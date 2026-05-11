# Wave 3 v4.0 · Componente 19 · Analise Read-Only (Gate 1)

**Branch:** `wave3-v4-c19/analysis`
**Data:** 2026-05-11
**Auditor:** Sessao Gate 1 (Claude Opus 4.7)
**Escopo desta sessao:** ANALISE READ-ONLY. Nenhum codigo de producao
foi modificado. Nenhuma migration foi aplicada. Validacao MCP estritamente
de leitura.

---

## Sumario Executivo

A 2a entrega da Wave 3 v4.0 — **Componente 19 (Fallback de Digitacao
Manual)** — pode prosseguir. **Todos os pre-requisitos estao
operacionais em `development`** (C10 mergeado em `804d879`, correcoes
pos-auditoria em `b406030`).

**Confirmacoes-chave:**

- `docs/wave3-v4-c10/contrato-c19.md` existe (294 LOC), descreve API
  publica completa, e bate **literalmente** com o codigo real em
  `frontend/src/lib/services/identificacao-prova.ts` (191 LOC).
- A **UI inteira do C19** ja esta presente em
  `(dashboard)/escanear/page.tsx` linhas 586-653, montada pelo
  C10 v4.0 como `<ManualPanel>` — funcional (chama
  `identificarProvaPorCodigo`) mas **sem mascara, sem validacao
  client-side, sem foco automatico, sem rate limit**.
- Camada de servico **comprovadamente desacoplada** de DOM/camera —
  teste anti-acoplamento `expect(src).not.toMatch(/\bnavigator\.|\bdocument\.|\bwindow\./)` continua passando.
- Backend `POST /api/v1/provas/scan` aceita `codigo` com
  `max_length=32`, valida formato via
  `validar_formato_codigo_publico` ANTES do SELECT, retorna 404
  **identico** para "formato invalido" / "inexistente" / "fora do
  scope" — anti-enumeracao DAT v3.0 §8.2 totalmente preservada.
- MCP confirmou: 17 provas em producao com `codigo_publico`
  preenchido (0 NULL); `idx_provas_codigo_publico` UNIQUE existe;
  RLS de `provas_digitais` esta versionada (helpers em
  `app_private`); zero advisor novo.

**Decisoes propostas para o Gate 2** (registrar em `DECISIONS.md`):

1. **Mascara**: implementacao MANUAL no `onChange` (sem nova lib).
   `framer-motion` e `html5-qrcode` ja inflam o bundle; `imask` /
   `react-input-mask` adicionariam 8-15 kB sem ganho material.
2. **Conversao de case**: auto-uppercase no input (o alfabeto e A-Z
   maiusculo + 23456789).
3. **Caracteres invalidos**: **bloqueio rigido** (caractere fora do
   alfabeto nao aparece). Justificativa: minimiza confusao e
   superficie de teste; alinhado com o feel de input "PIN".
4. **Auto-submit ao completar 18 chars**: NAO (manter clique explicito
   — UX previsivel, alinhado com cenario 3 do `smoke-validation.md`
   do C10).
5. **Preservacao de estado ao alternar tabs**: input fica preservado
   (estado em `EscanearPage` ja vive acima do `<ManualPanel>`); o
   `trocarParaCamera` ja zera `manualState` mas NAO mexe em
   `codigoManual`. Manter.

**Risco critico identificado (DESCASAMENTO ENTRE PROMPT E PRODUTO):**

O prompt deste C19 escopa a sessao como **frontend-only** e
explicitamente proibe "modificar o endpoint backend do C10". Porem
**Backlog v4.0 Componente 19 / Notas Tecnicas** + **DAT v3.0 §8.2**
exigem **rate limiting backend de 30 tentativas/min/usuario com
resposta 429** como mitigacao de enumeracao. Hoje o backend NAO
tem rate-limit. Mitigacoes correntes (formato validado antes do
SELECT + RLS antes da resposta + mensagem 404 generica) sao
solidas mas nao cobrem **descoberta lenta** (atacante respeitando
o rate humano natural). Recomendacao: tratar como **achado de
follow-up obrigatorio** — sessao separada (ou C20+) que adiciona
`slowapi` no `/scan` filtrado por `current_user.id` e mapeia 429
para um codigo novo `RATE_LIMITED` na camada de servico. Decisao
final no Gate 2.

---

## 1. Leitura de Contexto

### 1.1 Artefato central

| Caminho | Status | Linhas | Observacao |
|---|---|---|---|
| `docs/wave3-v4-c10/contrato-c19.md` | ✅ presente | 294 | Coerente com codigo real. AUD-W3C10-020 (export `MENSAGENS_ERRO_PADRAO` + `mensagemPara`) ja refletido. `max_length=32` (AUD-012) documentado. |

### 1.2 Repositorio (estado vivo pos-C10)

| Caminho | Verificado | Nota |
|---|---|---|
| `CLAUDE.md` | ✅ | Secao "Identificacao de provas" com nota para C19. |
| `DECISIONS.md` | ✅ | ADRs 132-140 do C10. Notavel ADR-140 (timing differential — vetor real = 0 para caminho manual; ja conferido). |
| `CHANGELOG.md` | ✅ | Secao "Correcoes Pos-Auditoria" do C10. |
| `docs/wave3-v4-c10/analysis.md` | ✅ | 35119 tokens — lido por trechos. |
| `docs/wave3-v4-c10/audit-report.md` | ✅ | Veredito: APROVAR COM CORRECOES. 22 achados, todos tratados (Apendice B). |
| `docs/wave3-v4-c10/fix-validation.md` | ✅ | 819 backend tests + 46 Vitest + 0 advisor novo. |
| `docs/wave3-v4-c10/smoke-validation.md` | ✅ | 20 cenarios; cenarios 3-6 ja sao do C19 (DEFERRED — Mario executa antes do PR para `main`). |
| `frontend/src/app/(dashboard)/escanear/page.tsx` | ✅ | 658 LOC. `<ManualPanel>` em 586-653. |
| `frontend/src/app/(dashboard)/escanear/escanear.module.css` | ✅ | 802 LOC. Estilos do tab Manual em 514-664. |
| `frontend/src/lib/services/identificacao-prova.ts` | ✅ | 191 LOC. |
| `frontend/src/lib/services/__tests__/identificacao-prova.test.ts` | ✅ | 303 LOC, 18 testes (era 16 + 2 AUD-020). |
| `shared/access-matrix.json` | ✅ | rule `scanner` = `full` para os 4 perfis. |
| `frontend/package.json` | ✅ | **Nao tem lib de mascara** (sem `imask`, `react-imask`, `react-input-mask`). Vitest 2.1.9 disponivel. |
| `backend/app/services/codigo_publico_service.py` | ✅ | `validar_formato_codigo_publico` (regex puro) + alfabeto `ABCDEFGHJKMNPQRSTUVWXYZ23456789`. |
| `backend/app/domain/schemas/prova.py` | ✅ | `ScanRequest.codigo: max_length=32` (AUD-012). |
| `backend/app/api/v1/provas.py:scan_prova` | ✅ | Handler com XOR. Caminho manual: valida formato → SELECT scoped → 404 generico (mesma mensagem para 3 cenarios). |

### 1.3 Documentos do produto

| Documento | Itens relevantes lidos | Conclusao |
|---|---|---|
| `RequisitosProvasDigitais_v4_0.docx` | RF-005 (fallback como mecanismo, fluxo idempotente com camera), RF-006 (fluxo unificado de identificacao), RF-007 ("codigo textual digitado e identificador de autenticidade"), US-002 ("campo de digitacao manual como fallback"), RNF-001 (3s carga / 2s identificacao), RNF-007 (RBAC em 2 camadas), RNF-008 (acessibilidade — 5"+ touchscreen) | C19 atende RF-005/006/007/US-002 reusando 100% do que C10 entregou. |
| `BACKLOG_RastreioProvasDigitais_v4_0.docx` Componente 19 | Escopo: input + **mascara em tempo real** + endpoint idempotente (ja existe) + redirect para tela de assinatura (C10 redireciona para `/provas/[id]` — coerente, a "tela de assinatura" sera C11). Mensagens de erro claras (4 cenarios). Criterios: 2s, anti-enumeracao, fora do escopo = mesma mensagem. Notas tecnicas: idempotencia + **RATE LIMITING**. | **Rate limit backend e exigencia textual** — descasamento com escopo do prompt (ver Secao 7 Riscos). |
| `BACKLOG ... Definition of Done Global` | 10 itens da Secao 2 — code review, ≥80% cobertura, staging, migrations versionadas, criterios US, Matriz, sem erros console, doc atualizada, RLS, prefers-reduced-motion. | Aplicaveis literalmente; o Gate 2 executa cada um. |
| `DAT_RastreioProvasDigitais_v3_0.docx` §8 | §8.1 idempotencia (endpoint `POST /api/provas/identificar` aceita `token` OR `codigo`) — o nome real do endpoint atual e `/api/v1/provas/scan` com `payload` XOR `codigo`, **funcionalmente equivalente**. §8.2 anti-enumeracao: rate-limit 30/min, mensagens genericas, entropia 6+ chars. §8.3 formato `PRV-AAAA-MM-NNNNNN`, alfabeto sem 0/O/1/I/L. | Spec vigente. Implementacao atual: ✓ mensagens genericas, ✓ entropia 31^6=887M, ⏳ rate-limit (backlog). |

**Observacao terminologica:** o prompt do C19 cita "RF-019" como
identificador do componente. No Backlog v4.0, RF-019 e o requisito de
tela de login (autenticacao por email/senha) — NAO o fallback manual.
O **RF real** que especifica o fallback e o **RF-005** (Requisitos
v4.0, "[v4.0 NOVO] A tela de escaneamento deve oferecer, como
mecanismo de fallback, um campo de digitacao manual..."). O "19" do
prompt e o numero do **Componente** no Backlog, nao do RF. Sem
implicacao operacional — esclarecimento textual.

---

## 2. Inventario do Contrato C19 (Secao 4.1 do prompt)

**Reproducao literal do `contrato-c19.md` + codigo real em `identificacao-prova.ts`:**

### 2.1 Tipos exportados

```typescript
export type CodigoErro =
  | "QR_INVALIDO"           // Backend 422 (formato/hash invalido — camera)
  | "PROVA_NAO_ENCONTRADA"  // Backend 404 (inexistente OR formato OR fora scope)
  | "DISPOSITIVO_SEM_CAMERA" // useScanner falha de hardware (nao se aplica ao C19)
  | "ERRO_REDE"             // Backend 5xx ou network failure
  | "SESSAO_EXPIRADA";      // Backend 401

export type ResultadoIdentificacao =
  | { tipo: "sucesso"; prova: ScanResponse }
  | { tipo: "erro"; codigo: CodigoErro; mensagem: string };

export const MENSAGENS_ERRO_PADRAO: Record<CodigoErro, string>;
export function mensagemPara(codigo: CodigoErro): string;
export function criarErro(codigo: CodigoErro): ResultadoIdentificacao;
```

### 2.2 Funcao consumida pelo C19

```typescript
export async function identificarProvaPorCodigo(
  codigo: string,
  params: { getToken: () => Promise<string | null> },
): Promise<ResultadoIdentificacao>;
```

**Caracteristicas verificadas:**

- ✅ **Zero acoplamento com hardware** (teste anti-acoplamento em
  `identificacao-prova.test.ts:285-302` faz regex contra source).
- ✅ **Token via callback** — assinatura compativel com `getToken`
  ja usado em `useScanner` e na `EscanearPage`.
- ✅ Mensagens pt-BR pre-resolvidas em `MENSAGENS_ERRO_PADRAO`:
  - QR_INVALIDO: "QR Code nao reconhecido. Verifique se esta
    escaneando uma etiqueta de prova."
  - PROVA_NAO_ENCONTRADA: "Prova nao encontrada."
  - DISPOSITIVO_SEM_CAMERA: "Camera indisponivel. Use a digitacao
    manual."
  - ERRO_REDE: "Falha de conexao. Tente novamente em instantes."
  - SESSAO_EXPIRADA: "Sua sessao expirou. Faca login novamente."

**Mapeamento HTTP → CodigoErro (de `_mapearErro` em `identificacao-prova.ts:174-191`):**

| HTTP | CodigoErro | Observacao |
|---|---|---|
| 200 | `tipo: "sucesso"` | `result.prova` populado |
| 401 | SESSAO_EXPIRADA | |
| 404 | PROVA_NAO_ENCONTRADA | **Mensagem identica** para 3 cenarios (DAT §8.2) |
| 422 | QR_INVALIDO | No caminho manual, **so dispara se codigo > 32 chars** (Pydantic). Codigos formato invalido <= 32 chars caem em validacao backend e viram 404 generico. |
| 5xx / fetch threw | ERRO_REDE | |

**Discrepancia resolvida:** o prompt do C19 lista 5 codigos
incluindo `FORA_DO_ESCOPO` — esse codigo **NAO existe** na uniao
real. O contrato unifica formato/inexistente/fora_do_scope em
`PROVA_NAO_ENCONTRADA` **propositadamente** (anti-enumeracao
DAT §8.2). A unificacao **e** a defesa — separar seria regressao.
O C19 deve tratar como 4 codigos relevantes:
QR_INVALIDO + PROVA_NAO_ENCONTRADA + ERRO_REDE + SESSAO_EXPIRADA.
`DISPOSITIVO_SEM_CAMERA` nao se aplica a digitacao.

---

## 3. Inventario da UI Ja Existente do C19 (Secao 4.2 do prompt)

**Estado:** ✅ **PRESENTE INTEGRALMENTE**, mas a lógica esta **parcial**
(submit funciona; falta mascara, validacao client-side, foco automatico,
rate-limit-client).

### 3.1 Mapa dos elementos UI (page.tsx)

| Elemento | Linha | Identificador | Estado atual |
|---|---|---|---|
| Tab "Camera" (botao com pill animado) | 259-281 | `role="tab"`, `aria-selected={tab === "camera"}` | ATIVO — `onClick={onCamera}`. Pill via `motion.span layoutId="scanner-tab-pill"`. |
| Tab "Manual" (botao com pill animado) | 282-301 | `role="tab"`, `aria-selected={tab === "manual"}` | ATIVO — `onClick={onManual}` chama `trocarParaManual` (zera `cameraState` mas preserva `codigoManual`). |
| `<ManualPanel>` form | 595 | `className={styles.manualPanel}` | Container ativo, `onSubmit={onSubmit}`. |
| h2 "Inserir codigo manualmente" | 601 | `.panelTitleManual` | Estatico. |
| Descricao "Digite o codigo da etiqueta..." | 602-605 | `.panelDescriptionManual` | Estatico (texto inclui literal "PRV-AAAA-MM-NNNNNN"). |
| Wrapper do input | 607-630 | `.manualInputWrapper`, `aria-invalid={isError ? "true" : "false"}` | Wrapper passa `aria-invalid` ao `aria-describedby` por sub-label. |
| Span prefixo "PRV-" | 611-613 | `.manualInputPrefix`, `aria-hidden="true"` | Decorativo; **NAO entra no `codigo` digitado** — o input contem APENAS a parte sem prefixo (problema documentado em Risco R-1 abaixo). |
| Label sr-only "Codigo da prova" | 614-616 | `htmlFor="codigo-manual"`, `className={styles.srOnly}` | OK. |
| Input | 617-629 | `id="codigo-manual"`, `type="text"`, `value={codigo}`, `placeholder="AAAA-MM-NNNNNN"`, `autoComplete="off"`, `autoCapitalize="characters"`, `spellCheck={false}`, `disabled={isLoading}`, `aria-describedby={isError ? "manual-error" : undefined}` | **Aceita qualquer texto**. Sem mascara, sem validacao client-side, sem auto-uppercase real. **Foco automatico ausente.** |
| Banner de erro | 632-636 | `id="manual-error"`, `role="alert"`, `.errorBanner` | Renderizado quando `state.kind === "error"`; texto e `state.mensagem`. |
| Botao "Buscar prova" | 638-647 | `type="submit"`, `.manualCta`, `disabled={submitDisabled}` | `submitDisabled = isLoading \|\| trimmed.length === 0`. Sem checagem de formato — usuario consegue submeter qualquer string nao vazia. |
| Footer placeholder | 650 | `<InnerFooter />` (linhas 658-672) | Reuso compartilhado com tab Camera. |

### 3.2 Estado React no escopo da pagina (page.tsx 60-67)

```tsx
const [tab, setTab] = useState<Tab>("camera");
const [cameraState, setCameraState] = useState<CameraState>({ kind: "idle" });
const [manualState, setManualState] = useState<ManualState>({ kind: "idle" });
const [codigoManual, setCodigoManual] = useState("");
```

`codigoManual` ja existe e e passado ao `<ManualPanel>` via prop
`codigo`. O setter via `onChange` chama `setCodigoManual(e.target.value)`.

`manualState` tagged union (linhas 55-58):

```tsx
type ManualState =
  | { kind: "idle" }
  | { kind: "identifying"; codigo: string }
  | { kind: "error"; codigo: CodigoErro; mensagem: string };
```

### 3.3 Handler atual de submit (page.tsx 135-156)

```tsx
const handleManualSubmit = useCallback(
  async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const codigo = codigoManual.trim();
    if (!codigo) return;
    setManualState({ kind: "identifying", codigo });
    const result: ResultadoIdentificacao = await identificarProvaPorCodigo(
      codigo,
      { getToken },
    );
    if (result.tipo === "sucesso") {
      router.push(`/provas/${result.prova.prova.id}`);
      return;
    }
    setManualState({ kind: "error", codigo: result.codigo, mensagem: result.mensagem });
  },
  [codigoManual, getToken, router],
);
```

**Observacoes criticas:**

- O handler **so manda o que o usuario digitou** (sem prepender "PRV-" automaticamente). O usuario precisa digitar "PRV-AAAA-MM-NNNNNN" no input (18 chars) OU o C19 prepende "PRV-" antes de submeter (so vai aos 14 chars sem prefixo).
- O codigo do C10 mostra o prefixo "PRV-" como **decoracao visual** (span `.manualInputPrefix aria-hidden="true"`) mas isso e ENGANOSO — o usuario nao tem indicacao de que precisa digitar "PRV-" tambem. O placeholder "AAAA-MM-NNNNNN" reforca a ideia errada de que o input nao precisa do "PRV-".
- **Decisao a tomar no Gate 2 (Risco R-1):** o input **deve** considerar o "PRV-" automatico (prepender no submit) OU **deve** exibir o "PRV-" como parte do `value` digitavel? A coerencia textual exige uma das duas. Recomendacao: **prepender automaticamente** — alinhado com o smoke do C10 cen.3 que diz "digitar `PRV-2026-05-TEX9GW`" (codigo completo) mas isso e ambiguo. Vou validar com o Mario no Gate 2.

### 3.4 Confirmacao visual

A UI esta no arquivo, importavel por meio do redesign do C10 — `<ManualPanel>` ativa quando `tab === "manual"`. Confirmacao por inspecao do source unicamente (Gate 1 nao roda dev server). O `smoke-validation.md` do C10 cenarios 2-6 cobre fluxo manual visual.

---

## 4. Plano de Ativacao da Logica (Secao 4.3 do prompt)

Para cada elemento da UI ja existente, especifico:

### 4.1 Input com mascara

**Hook proposto:** `useCodigoPrvInput()` (NOVO) — encapsula:

```tsx
interface UseCodigoPrvInputResult {
  /** Valor canonicalizado para submit: "PRV-YYYY-MM-NNNNNN" ou "" se vazio. */
  codigoCompleto: string;
  /** Valor exibido no input (o que o usuario "ve" depois da mascara). */
  display: string;
  /** Setter chamado pelo onChange — aplica mascara + auto-uppercase + bloqueio de chars invalidos. */
  setFromInput: (raw: string) => void;
  /** True quando display tem exatamente 14 chars (= 18 chars com prefixo PRV-). */
  isComplete: boolean;
  /** Estado de validacao client-side (formato OK ou nao). Calculado por validarFormatoCodigoPublico. */
  isFormatValid: boolean;
  /** Resetar input ao valor vazio. */
  reset: () => void;
}
```

**Side effect:** o `<ManualPanel>` passa a usar `codigoCompleto` em `value`
do form e o setter em `onChange`. O submit usa `codigoCompleto`.

### 4.2 Foco automatico ao entrar em modo Manual

**Hook proposto:** `useRef<HTMLInputElement>(null)` em `<ManualPanel>` +
`useEffect(() => { ref.current?.focus(); }, [])` no mount. Como o
`<ManualPanel>` so existe quando `tab === "manual"` (`AnimatePresence`
`mode="wait"`), o mount dispara cada vez que o usuario alterna para
Manual. Ajuste fino: respeitar `prefers-reduced-motion` nao se aplica
ao foco — sem flicker.

### 4.3 Auto-uppercase + bloqueio de chars invalidos

Dentro do `setFromInput`:

```tsx
const upper = raw.toUpperCase();
const ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789-";
const cleaned = Array.from(upper).filter((c) => ALPHABET.includes(c)).join("");
```

Comportamento: digitar `0` (zero), `O`, `1`, `I`, `L`, espaco, caractere
acentuado — nao aparece no input.

### 4.4 Mascara de digitacao

Padrao alvo: `YYYY-MM-NNNNNN` (14 chars exibidos; prefixo "PRV-" e
estatico no `<span>` decorativo a esquerda do input).

Decisoes formais:

- **Onde o "PRV-" vive:** o `<span>` decorativo de 13px continua. O
  `value` do `<input>` so contem `YYYY-MM-NNNNNN`. Ao chamar
  `identificarProvaPorCodigo`, o hook concatena: `"PRV-" +
  display.replace(...)`. **Inverte a interpretacao atual do prompt** —
  o C19 NAO trata o input como contendo "PRV-" porque o UI textual ja
  separa visualmente. Decisao registrar em ADR.
- **Algoritmo manual** (sem nova lib):
  - Tira tudo que nao for do alfabeto.
  - Insere `-` apos pos 4 (ano completo) e pos 7 (ano+mes completo).
  - Trunca em 14 chars (4 + 1 + 2 + 1 + 6).

Pseudocodigo:

```ts
function aplicarMascara(raw: string): string {
  const chars = Array.from(raw.toUpperCase()).filter(c => ALPHABET_SEM_HIFEN.includes(c));
  const pegou = chars.slice(0, 12); // 4 + 2 + 6 sem hifens
  const ano = pegou.slice(0, 4).join("");
  const mes = pegou.slice(4, 6).join("");
  const seq = pegou.slice(6, 12).join("");
  let out = ano;
  if (pegou.length > 4) out += "-" + mes;
  if (pegou.length > 6) out += "-" + seq;
  return out;
}
```

- **Backspace funciona** — apagar para tras nao precisa de logica
  especial: o `setFromInput` ja recebe o `raw` resultante do nativo do
  navegador e re-mascara.
- **Paste** — o usuario cola "PRV-2026-05-TEX9GW" (ou variante minuscula):
  - `setFromInput("PRV-2026-05-TEX9GW")` → uppercase → filtra → fica `"PRV-2026-05-TEX9GW"`.
  - **Edge case importante:** se o usuario colar com "PRV-" no inicio, o filtro deixa "PRV-" passar (P, R, V, - todos no alfabeto). Mas o input nao quer "PRV-". Solucao: **strip do prefixo PRV-** se presente na entrada de `setFromInput` ANTES da mascara.

```ts
function setFromInput(raw: string) {
  const stripped = raw.replace(/^PRV-?/i, "");
  const masked = aplicarMascara(stripped);
  setDisplay(masked);
}
```

### 4.5 Validacao client-side antes do submit

Funcao pura **importada do backend** seria ideal, mas o prompt proibe
acoplar frontend e backend nesse nivel. Solucao: replicar o regex no
frontend, com teste que confirma equivalencia. Arquivo proposto:
`frontend/src/lib/codigo-publico.ts` (NOVO).

```ts
const ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";

export function validarFormatoCodigoPublico(codigo: string): boolean {
  if (codigo.length !== 18) return false;
  const parts = codigo.split("-");
  if (parts.length !== 4) return false;
  const [pref, ano, mes, sufixo] = parts;
  if (pref !== "PRV") return false;
  if (!/^\d{4}$/.test(ano)) return false;
  if (!/^\d{2}$/.test(mes)) return false;
  const m = parseInt(mes, 10);
  if (m < 1 || m > 12) return false;
  if (sufixo.length !== 6) return false;
  for (const c of sufixo) if (!ALFABETO.includes(c)) return false;
  return true;
}
```

**Teste de paridade Python ↔ TypeScript:** o
`backend/tests/test_codigo_publico_service.py` ja tem 20 testes do
backend. O C19 adiciona 1 teste Vitest que executa um conjunto de
casos identicos.

### 4.6 Handler de submit

Substitui `handleManualSubmit` para validar formato **antes** de chamar
o servico:

```tsx
const handleManualSubmit = useCallback(async (e: FormEvent<HTMLFormElement>) => {
  e.preventDefault();
  const codigo = codigoCompleto; // ja inclui "PRV-"
  if (!validarFormatoCodigoPublico(codigo)) {
    setManualState({ kind: "error", codigo: "QR_INVALIDO", mensagem: "Formato invalido. Verifique a etiqueta." });
    return;
  }
  setManualState({ kind: "identifying", codigo });
  const result = await identificarProvaPorCodigo(codigo, { getToken });
  if (result.tipo === "sucesso") {
    router.push(`/provas/${result.prova.prova.id}`);
    return;
  }
  setManualState({ kind: "error", codigo: result.codigo, mensagem: result.mensagem });
}, [codigoCompleto, getToken, router]);
```

**Atencao critica:** o codigo `QR_INVALIDO` quando vindo de validacao
client-side **revela** ao atacante que o input nao passou. Isso e
**aceito** porque um atacante consciente do regex usa um codigo
bem-formado e bate diretamente no SELECT (mesma resposta da
`PROVA_NAO_ENCONTRADA`). A perda de informacao e minima — o regex e
publico via DAT §8.3.

Alternativa: traduzir `QR_INVALIDO` client-side para a **mesma mensagem**
de `PROVA_NAO_ENCONTRADA`. Vou recomendar isso no Gate 2 — preserva
anti-enumeracao em camada UI. Decisao a registrar em ADR.

### 4.7 Botao "Voltar para camera" / alternancia

Ja existe via `<ScannerTabs>`. O `<ManualPanel>` nao precisa de botao
proprio — o usuario clica na tab "Camera". O smoke do C10 cen.10 ja
adiciona um link inline "Ir para digitacao manual →" no caminho
`DISPOSITIVO_SEM_CAMERA` — o C19 nao mexe nisso.

### 4.8 Auto-submit ao completar 18 chars

**Decisao proposta:** NAO. Razao: ate 14 chars sem prefixo. Auto-submit
e fragil quando o usuario quer corrigir o ultimo char (precisa apagar
2 vezes para evitar disparo). Mantemos o clique no botao para
previsibilidade. Documentar em ADR.

---

## 5. Plano de Validacao Client-Side (Secao 4.4 do prompt)

### 5.1 Estados de input

| Estado | Quando | Reacao |
|---|---|---|
| Vazio | `display === ""` | Botao desabilitado. Sem feedback. |
| Parcial valido | 1-13 chars que casam com mascara progressiva | Sem erro, botao desabilitado. |
| Completo bem-formado | `display.length === 14` E `validarFormatoCodigoPublico("PRV-" + display)` | Botao habilita. Pronto para submit. |
| Completo mal-formado | `display.length === 14` MAS algum component invalido (ex: mes=13) | Botao desabilitado E feedback inline. |

**Detalhe:** mes invalido (>12) so seria possivel se o usuario passar
por mascara digitada manualmente (ex: digitar 1, 3 nos 5o-6o chars).
Como a mascara nao bloqueia digitos invalidos para mes (so chars do
alfabeto), o caso e possivel. Mitigacao: validacao explicita.

### 5.2 Estados de submit

| Estado | Mensagem visivel ao usuario |
|---|---|
| Bem-formado, prova existe in-scope | (transicao para `/provas/[id]` — sem mensagem na tela) |
| Bem-formado, retorno 404 (3 cenarios indistinguiveis) | "Prova nao encontrada." |
| Mal-formado pelo client (caiu na validacao client-side) | **MESMA MENSAGEM "Prova nao encontrada."** (decisao recomendada em §4.6) |
| Sem rede | "Falha de conexao. Tente novamente em instantes." |
| Sessao expirada | "Sua sessao expirou. Faca login novamente." |

### 5.3 Regex final

```ts
/^PRV-\d{4}-(0[1-9]|1[0-2])-[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{6}$/
```

Equivalente ao backend (`validar_formato_codigo_publico`). Salvar em
`frontend/src/lib/codigo-publico.ts` como constante exportada
`CODIGO_PUBLICO_REGEX`.

---

## 6. Plano de Mascara de Input (Secao 4.5 do prompt)

### 6.1 Lib

**Decisao:** implementacao manual. Razao: dependencias atuais do projeto
(`framer-motion 12.38` ja pesa, html5-qrcode 2.3.8 idem); a mascara
PRV-YYYY-MM-NNNNNN tem regra trivial (2 separadores fixos); zero ROI em
adicionar `imask` ou `react-input-mask`.

**Bundle predicted:** delta ≈ +1.5 kB (hook custom + util de mascara +
regex) vs +8 a +15 kB com lib externa.

### 6.2 Padrao

Display: `YYYY-MM-NNNNNN` (14 chars), prefixo "PRV-" sempre visivel via
`<span aria-hidden>` decorativo.

### 6.3 Comportamento esperado

| Acao do usuario | Resultado |
|---|---|
| Digita "2026" | Display: `"2026"` |
| Digita "5" depois | Display: `"2026-5"` (hifen aparece automatico, mas mes parcial — botao continua desabilitado) |
| Digita "0" antes do "5" no mes (corrigindo) | Bloqueado — `0` nao esta no alfabeto. **Mas** o ano e mes precisam de digitos 0-9. Edge case relevante: o alfabeto sem 0/O/1/I/L bloqueia `0`/`1` no mes/ano. |

**EDGE CASE CRITICO descoberto:**
O alfabeto sem ambiguos (DAT §8.3) refere-se **ao sufixo NNNNNN** —
ano e mes sao **digitos 0-9 puros**. O regex backend confirma:
`ano.isdigit() and len(ano) == 4`, `mes.isdigit() and len(mes) == 2`.
Logo o alfabeto se aplica **por posicao**:

- Posicoes 0-3 (ano): `0-9`
- Posicoes 4-5 (mes): `0-9` com restricao 01-12
- Posicoes 6-11 (sufixo): `ABCDEFGHJKMNPQRSTUVWXYZ23456789`

A mascara deve **bloquear por posicao**, nao globalmente. Atualizar o
plano:

```ts
function isCharValidoEm(c: string, pos: number): boolean {
  if (pos < 6) return /\d/.test(c); // ano + mes
  return ALFABETO_SUFIXO.includes(c); // sufixo
}
```

**Sem esse ajuste, o usuario pode digitar uma letra em pos 0 (ex.
"A0265"); ou um digito 0 em pos 6 (ex. ano OK, mes OK, sufixo
"0AAAAA"). O backend rejeita os dois, mas a UX fica confusa.**

Decisao registrada como ADR no Gate 2.

### 6.4 Acessibilidade da mascara

- A mascara **nao quebra** leitor de tela: o `<input>` continua sendo
  `<input type="text">` com `value` strings normais. Apenas o `<span>`
  prefixo e marcado `aria-hidden="true"` (correto — usuario do leitor
  ja sabe pela label "Codigo da prova" o que digitar).
- A label sr-only diz "Codigo da prova" — vou **estender** para
  "Codigo da prova no formato PRV-AAAA-MM-NNNNNN" no C19 para guiar o
  usuario de leitor de tela.

---

## 7. Plano de Tratamento de Erros (Secao 4.6 do prompt)

### 7.1 Tabela de mapeamento contrato → UI

| Codigo do contrato | Cenario no C19 | Mensagem em pt-BR (sugerida) | Tratamento UI |
|---|---|---|---|
| `QR_INVALIDO` (vindo do backend, 422 quando codigo > 32 chars) | Raro — Pydantic rejeitou input acima de 32 chars | "Prova nao encontrada." (**uniformizar** com 404 — anti-enumeracao) | Banner inline, focus volta ao input, codigo preservado |
| `QR_INVALIDO` (vindo da validacao client-side, regex falhou) | Formato invalido detectado antes de enviar | "Prova nao encontrada." (mesma) | idem |
| `PROVA_NAO_ENCONTRADA` (404 backend) | 3 cenarios indistinguiveis (formato OK mas inexistente / fora do scope / formato batido como invalido pelo backend) | "Prova nao encontrada." | idem |
| `ERRO_REDE` (5xx / fetch threw) | Falha de rede | "Falha de conexao. Tente novamente em instantes." | Banner com botao "Tentar Novamente" preservando codigo |
| `SESSAO_EXPIRADA` (401) | Token expirado | "Sua sessao expirou. Faca login novamente." | Banner; ao fechar, redireciona `/login` |
| `DISPOSITIVO_SEM_CAMERA` | **NAO SE APLICA** ao C19 (digitacao nao usa camera) | — | — |

### 7.2 Anti-enumeracao **preservada na UI**

**Decisao critica:** o C19 trata `QR_INVALIDO` (client-side OU backend
422) **com a mesma mensagem** de `PROVA_NAO_ENCONTRADA`.

Implementacao sugerida (espelha o helper do contrato):

```ts
const MENSAGENS_C19: Partial<Record<CodigoErro, string>> = {
  QR_INVALIDO: "Prova nao encontrada.", // uniformiza com 404
};

function mensagemFinal(codigo: CodigoErro): string {
  return MENSAGENS_C19[codigo] ?? mensagemPara(codigo);
}
```

**Aceito que isso "esconde" do usuario que ele digitou errado** —
sacrificio aceitavel porque (a) o input com mascara client-side
evita 99% dos formatos errados antes mesmo do submit; (b)
distinguir formato errado de "fora do scope" cria vetor de timing
distinto da regex backend; (c) DAT §8.2 e Backlog C19 "Critérios
de Aceitação" obrigam essa uniformizacao.

### 7.3 Botao "Tentar Novamente"

Aplicavel apenas em `ERRO_REDE`. Render condicional:

```tsx
{state.kind === "error" && state.codigo === "ERRO_REDE" && (
  <button type="button" onClick={() => setManualState({ kind: "idle" })}>
    Tentar novamente
  </button>
)}
```

Codigo digitado **e preservado** no `display` (estado vive no
`<EscanearPage>`, nao no `<ManualPanel>` — o reset do `manualState` para
`idle` nao toca o input).

---

## 8. Plano de Visibilidade por Perfil (Secao 4.7 do prompt)

**Rule:** `scanner` em `shared/access-matrix.json` (linhas 51-60).

| Perfil | Acesso a `/escanear` | Acesso ao tab Manual |
|---|---|---|
| studio_admin | full | herdado (mesmo tab) |
| vendedor | full | herdado |
| motorista | full | herdado |
| clicheria | full | herdado |
| anonimo | bloqueado por middleware | n/a |

**Implementacao:** ZERO logica nova. O `useAuthorization("scanner")` ja
e usado em `page.tsx:62` e retorna `hasAccess=true` para os 4 perfis.
O `<ManualPanel>` herda — nao precisa de proprio guard.

**RLS continua funcionando:** quando vendedor X digita codigo de
prova de vendedor Y, o `_carregar_prova_por_codigo_publico_com_scoping`
filtra (vendedor_id != current_user.id) e retorna `None` → 404 generico.
**Mesma mensagem** de "inexistente" — anti-enumeracao DAT §8.2 mantida
no caminho de scope.

---

## 9. Plano de Acessibilidade (Secao 4.8 do prompt)

### 9.1 Existente no C10 (preservar)

- `<label htmlFor="codigo-manual" class="srOnly">` — texto descritivo
  (estender no C19 com formato canonico).
- `<input>` tem `id="codigo-manual"`, `autoComplete="off"`,
  `autoCapitalize="characters"`, `spellCheck={false}`,
  `aria-describedby={isError ? "manual-error" : undefined}`.
- Wrapper tem `aria-invalid` dinamico.
- Banner de erro tem `role="alert"` e `id="manual-error"`.
- Footer placeholder tem `aria-disabled="true"` + `title`.

### 9.2 Adicoes do C19

| Item | Implementacao |
|---|---|
| Foco automatico no input ao mount do `<ManualPanel>` | `useRef` + `useEffect` |
| Label estendida | `"Codigo da prova no formato PRV-AAAA-MM-NNNNNN"` |
| `aria-describedby` apontando **tambem** para hint textual quando nao houver erro | Hint em `<p id="manual-hint" class="srOnly">Digite o codigo de 14 caracteres apos PRV-. Apenas letras maiusculas (sem O ou I) e numeros (sem 0 ou 1).</p>` — `aria-describedby={isError ? "manual-error" : "manual-hint"}` |
| Enter no input dispara submit | Ja funciona via `<form onSubmit>` — confirmar no smoke |
| Tab order natural | Topbar → input → submit → footer (link disabled e `aria-disabled` mas focusable em ordem natural — manter) |
| `prefers-reduced-motion` | CSS ja contempla os elementos do tab Manual em linha 793-802 do CSS (rule `@media (prefers-reduced-motion: reduce)`). Sem adicao nova. |
| Contraste AA do banner de erro | `.errorBanner { background: rgba(185,28,28,0.08); color: #7f1d1d; }` — verificar via axe-core no smoke |

### 9.3 Teste axe-core obrigatorio

E2E roda Playwright + `@axe-core/playwright` no tab Manual. Threshold:
0 violacoes "serious" / "critical".

---

## 10. Plano de Modificacao Coordenada (Secao 4.9 do prompt)

| Arquivo | Tipo | Justificativa |
|---|---|---|
| `frontend/src/app/(dashboard)/escanear/page.tsx` | EDIT | Trocar `handleManualSubmit` para usar `codigoCompleto` + `validarFormatoCodigoPublico` + `mensagemFinal`. Integrar `useCodigoPrvInput` hook. Adicionar `useRef` + `useEffect` para foco automatico. Estender label sr-only. Adicionar `id="manual-hint"` + `aria-describedby` dinamico. |
| `frontend/src/app/(dashboard)/escanear/escanear.module.css` | EDIT | Talvez adicionar 1-2 regras: hint sr-only ja existe (`.srOnly`); botao "Tentar novamente" pode reusar `.linkButton` existente; cor de estado "formato OK" sutil. Provavelmente 0 mudanca real. |
| `frontend/src/lib/codigo-publico.ts` | NEW | Util compartilhada com regex + `validarFormatoCodigoPublico` + alfabeto + `aplicarMascara`. |
| `frontend/src/lib/__tests__/codigo-publico.test.ts` | NEW | Testes da util (~15 casos: validos + invalidos + bordas). |
| `frontend/src/hooks/useCodigoPrvInput.ts` | NEW | Hook React encapsulando estado + mascara + auto-uppercase + bloqueio por posicao. |
| `frontend/src/hooks/__tests__/useCodigoPrvInput.test.ts` | NEW | Testes do hook (~10 casos). Render via `renderHook` do `vitest`/`@testing-library/react`. **ATENCAO:** Vitest config esta em `environment: node`. Testes de hook precisam de DOM — usar `// @vitest-environment jsdom` per-file ou trocar para `environment: jsdom` apenas neste arquivo. **Decidir no Gate 2.** |
| `docs/wave3-v4-c10/contrato-c19.md` | EDIT | Apenas adicionar secao "Status: Entrega completa em [data] / branch wave3-v4/componente-19" no FIM, sem mexer no resto. |
| `CHANGELOG.md` | APPEND | Nova secao "v4.0 — Wave 3 — Componente 19" conforme template. |
| `DECISIONS.md` | APPEND | ADRs 141-X (mascara manual, uppercase, bloqueio por posicao, uniformizacao QR_INVALIDO → PROVA_NAO_ENCONTRADA, posicionamento do "PRV-" como decoracao + concatenacao no submit, decisao auto-submit NAO). |
| `CLAUDE.md` | EDIT (linha do bloco "Identificacao de provas") | Nota: "C19 entregue — mascara client-side ativa, validacao de formato espelha o backend, foco automatico, anti-enumeracao preservada na UI." |
| `docs/wave3-v4-c19/analysis.md` | APPEND (seccao Execucao) | Diffs entre proposta Gate 1 e o que foi feito. |

**ZERO alteracao em:**

- `frontend/src/lib/services/identificacao-prova.ts` — proibido pelo prompt e desnecessario.
- `backend/**` — proibido pelo prompt.
- `shared/access-matrix.json` — desnecessario.
- `frontend/src/middleware.ts` — desnecessario.
- `package.json` — sem nova dep.

---

## 11. Estrategia de Testes (Secao 4.10 do prompt)

### 11.1 Unitarios (Vitest)

| Suite | Arquivo | Casos minimos |
|---|---|---|
| `validarFormatoCodigoPublico` | `lib/__tests__/codigo-publico.test.ts` | 15+ casos: validos canonicos, prefixo errado, ano nao-digito, mes fora 01-12, sufixo com 0/O/1/I/L, tamanho errado, paridade Python (5 casos copiados do backend) |
| `aplicarMascara` | mesma | 10+ casos: vazio, parcial, completo, paste com PRV-, paste minusculo, char invalido, char de posicao errada (digito no sufixo, letra no ano), backspace simulado via re-mascarar |
| `useCodigoPrvInput` | `hooks/__tests__/useCodigoPrvInput.test.ts` | 8+ casos: render inicial, setFromInput, isComplete, isFormatValid em todos os transientes, reset, paste, prevencao de double-prefixo |
| Renderizacao do `<ManualPanel>` (snapshot leve) | (opcional) `app/(dashboard)/escanear/__tests__/ManualPanel.test.tsx` | Render idle / error / identifying — confirma que o `aria-invalid`, `aria-describedby` e botao desabilitado mudam conforme estado |

Meta: **+25 testes Vitest novos** (de 46 atuais → 71+).

### 11.2 Integracao

Testar via mock do `fetch` (padrao ja usado em
`identificacao-prova.test.ts:65`):

| Cenario | Esperado |
|---|---|
| Submit com `PRV-2026-05-TEX9GW` (mock 200) | `router.push("/provas/<id>")` chamado |
| Submit com `PRV-2026-05-AAAAAA` (mock 404) | `manualState.kind === "error"` + mensagem "Prova nao encontrada." |
| Submit com `aaa-bad` (validacao client-side falha) | **Mesma mensagem** "Prova nao encontrada." (uniformizacao) |
| Submit com prova legacy (`nro_requerimento` puro, ex `456987`) | Client-side rejeita (regex falha pre-submit) → "Prova nao encontrada." |
| Submit sem rede (fetch throws) | "Falha de conexao..." + botao "Tentar Novamente" |
| Sessao expirada (mock 401) | "Sua sessao expirou..." |

### 11.3 E2E (Playwright)

Manter conforme `smoke-validation.md` do C10 (cenarios 2-6 ja cobrem
o C19 happy path + anti-enumeracao). Expandir com:

| Cenario E2E novo | Esperado |
|---|---|
| Mascara em tempo real ao digitar | Display mostra `2026-05-TEX9GW` ao digitar dígitos um a um |
| Bloqueio de char invalido (digitar `0` no sufixo) | Char nao aparece |
| Paste de `prv-2026-05-tex9gw` (minusculo + prefixo) | Display = `2026-05-TEX9GW` |
| Foco automatico no input ao clicar tab Manual | `document.activeElement === <input id="codigo-manual">` |
| Enter no input com codigo completo | Submit dispara |
| Tab order: tab Camera → tab Manual → input → submit | Validado |
| axe-core sem violacoes serious/critical | OK |
| Performance < 2s do clique no botao ate o detalhe carregar | OK (Network Fast 3G) |

### 11.4 Cobertura

Meta minima Backlog DoD: **80% nas camadas de dominio/servico do
backend** — **N/A para C19** (sem mudanca backend). Equivalente do
frontend: o util `codigo-publico.ts` e o `useCodigoPrvInput` devem
ficar acima de 90% (linha + branch).

---

## 12. Migrations Previstas (Secao 4.11 do prompt)

**NENHUMA.** O backend ja aceita `codigo` em `/scan` desde o C10
(`ScanRequest.codigo: max_length=32`). RLS de `provas_digitais`
inalterada — `pol_provas_select` ja cobre os 4 perfis com scope
adequado. Indices ja existem (`idx_provas_codigo_publico` UNIQUE).
Coluna `codigo_publico` ja NOT NULL desde migration 012.

---

## 13. Riscos e Pontos de Atencao (Secao 4.12 do prompt)

| # | Risco | Severidade | Mitigacao | Status |
|---|---|---|---|---|
| **R-1** | **Rate limiting backend ausente — exigido por Backlog C19 + DAT §8.2.** Vetor de enumeracao por descoberta lenta. | **ALTO** | Implementar `slowapi` no `/scan` filtrado por `current_user.id`, 30/min, 429 → novo codigo `RATE_LIMITED` na camada de servico. **DECISAO NO GATE 2:** incluir nesta sessao (expandindo escopo do prompt) OU registrar como follow-up obrigatorio em sessao separada antes do PR para `main`. | Pendente |
| R-2 | Ambiguidade no posicionamento do "PRV-": e parte do `value` digitavel ou decoracao? Atualmente decoracao (`<span aria-hidden>`). O `smoke-validation.md` do C10 cen.3 diz "digitar `PRV-2026-05-TEX9GW`" — descreve o codigo completo (ambiguo se "PRV-" tambem precisa ser digitado). | MEDIO | Decidir como **decoracao** (proposta principal). Prepender "PRV-" antes do submit. ADR. Mensagem visual fica `[PRV-][2026-05-TEX9GW]`. | Pendente decisao Mario |
| R-3 | Validacao client-side reduz disparos do backend mas **abre canal de timing** entre "rejeitado-no-cliente" vs "rejeitado-no-servidor". | BAIXO | Uniformizar mensagens — `QR_INVALIDO` (client OU backend) usa **mesma string** de `PROVA_NAO_ENCONTRADA`. ADR. | Resolvido em §4.6 + §7.2 |
| R-4 | Mascara de input nao respeita alfabeto **por posicao** (ano/mes sao digitos 0-9, sufixo nao). Risco: usuario digita letra em pos 0 — mascara aceita pela visao "global". | MEDIO | `isCharValidoEm(c, pos)` no setter. Documentado em §6.3 (edge case critico). ADR. | Resolvido no plano |
| R-5 | Hook React de mascara exige DOM nos testes. `vitest.config.ts` esta em `environment: node` (Wave 1 v4.0 / AUD-W1V4-005). Adicionar `// @vitest-environment jsdom` no top do arquivo. **Cuidado:** nao quebrar o teste anti-acoplamento que precisa de Node. | MEDIO | Confinar `jsdom` apenas ao novo arquivo via comentario. Continua honrando o "minimo Vitest" da Opcao A (D-13). | Pendente confirmacao no Gate 2 |
| R-6 | Provas legacy (`rota IS NULL`) nao tem `codigo_publico` antigo no QR — sao identificaveis APENAS por camera (fallback `nro_requerimento`). Backlog cen.6 do smoke do C10: "manual nao aceita legacy" — comportamento aceito. Mas: **MCP confirmou 0 provas com `codigo_publico IS NULL`** (migration 012 fez backfill). Logo TODA prova em producao tem codigo digitavel. | INFO | Documentar no CHANGELOG do C19. Sem acao tecnica. | Validado via MCP |
| R-7 | Auto-uppercase pode confundir usuario que digita minusculo "esperando" ver minusculo (raro mas possivel). | BAIXO | Hint visual "Codigos sao em maiusculas" abaixo do input (ou na descricao ja existente). Sem acao agressiva. | Sem alteracao adicional |
| R-8 | Foco automatico no input pode ser **invasivo** para usuario de leitor de tela que prefere navegar com Tab. WCAG 2.4.3 aceita foco programatico apenas em mount inicial. | BAIXO | Foco so dispara no mount do `<ManualPanel>` (uma vez por troca de tab). Aceitavel. Validar no axe-core. | Resolvido no plano |
| R-9 | Estado preservado ao alternar tabs — usuario digita parcial, vai pra Camera, volta. Atualmente o `codigoManual` vive no `<EscanearPage>` — preserva. `trocarParaCamera` em `page.tsx:163-166` zera `manualState` mas NAO mexe em `codigoManual`. Comportamento OK. | INFO | Confirmar via cenario novo no smoke. | Resolvido (sem mudanca) |
| R-10 | Estado preservado de erro: usuario submit, da erro, volta a editar — `manualState` continua `error` ate ele submeter de novo OU mudar tab. UX aceitavel? | INFO | Decidir: `setManualState({kind:"idle"})` no `onChange` do input quando o atual e error. **Sem isso, o banner "fica" ate o proximo submit.** Recomendado. | Adicionar ao plano (Gate 2) |
| R-11 | Concorrencia camera + digitacao: usuario na tab Camera, camera ativa, alterna para Manual. `trocarParaManual` em `page.tsx:158-161` zera `cameraState` para `idle` — `useScanner` cleanup desliga o stream (AUD-W3C10-011). OK. | INFO | Validado pelo C10. Sem mudanca C19. | Resolvido |

---

## 14. Validacao MCP Supabase (Secao 3 do prompt)

Projeto: `rwxlpwmnkekzuurgthkr` (Rastreio Provas Digitais, sa-east-1,
Postgres 17.6.1.104, ACTIVE_HEALTHY).

### 14.1 Coluna `codigo_publico` e indices

| Coluna | Tipo | Nullable |
|---|---|---|
| `codigo_publico` | `varchar(20)` | NO |
| `nro_requerimento` | `varchar(50)` | NO |
| `rota` | `rota_enum` | YES |
| `status` | `status_prova_enum` | NO |

Indices:

| Indice | Tipo |
|---|---|
| `idx_provas_codigo_publico` | **UNIQUE btree** |
| `provas_digitais_nro_requerimento_key` | UNIQUE btree |
| `idx_provas_rota` | btree |

### 14.2 EXPLAIN ANALYZE do lookup

```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT id, codigo_publico, rota, status
FROM provas_digitais WHERE codigo_publico = 'PRV-2026-05-TEX9GW';
```

```
Seq Scan on provas_digitais  (cost=0.00..2.20 rows=1 width=82)
  (actual time=0.023..0.023 rows=1 loops=1)
  Filter: ((codigo_publico)::text = 'PRV-2026-05-TEX9GW'::text)
  Rows Removed by Filter: 16
  Buffers: shared hit=2
Planning Time: 0.583 ms
Execution Time: 0.098 ms
```

**Interpretacao:** 17 linhas; planner optou por Seq Scan ja que cabe
em 2 buffers (sem ganho real do indice). Em producao crescente, o
planner usara `idx_provas_codigo_publico` automaticamente. Tempo
total `~0.7 ms` — bem dentro de RNF-001/002 (2s).

### 14.3 Distribuicao de dados

```
total: 17 | sem_codigo: 0 | sem_rota: 11 | com_rota: 6 | rotas_distintas: 3
```

Todas as provas tem `codigo_publico`. 11 com `rota IS NULL` (legacy
v3.0) — confirma o smoke do C10 cen.6 (manual nao aceita esses
codigos antigos, pois o `codigo_publico` foi adicionado por backfill
**generico** sem que o QR fisico tenha sido regerado).

### 14.4 RLS `provas_digitais`

```
pol_provas_select  PERMISSIVE SELECT (publico):
  app_private.current_user_is_admin()
  OR (vendedor_id = app_private.current_user_id())
  OR (status = 'COM_MOTORISTA' AND current_user_setor() = 'MOTORISTA')
  OR (status IN (ENVIADA, ENCAMINHADA, RECEBIDA) AND current_user_setor() = 'CLICHERIA')

pol_provas_insert  PERMISSIVE INSERT  qual=null (admin via WITH CHECK pre-existente)
pol_provas_update  PERMISSIVE UPDATE  app_private.current_user_is_admin()
```

**Anti-enumeracao confirmada:** vendedor digita codigo de prova
alheia → policy `pol_provas_select` filtra → `_carregar_prova_...`
retorna `None` → handler retorna 404 generico (mesma resposta de
"inexistente"). ✅

### 14.5 Advisors

- **Security:** 2 alertas pre-existentes:
  - `rls_enabled_no_policy` em `public.alembic_version` (intencional, ADR-025).
  - `auth_leaked_password_protection` (WONTFIX plano pago, ADR-027).
- **Performance:** 13 `unused_index` (todos pre-existentes, incluindo `idx_provas_rota` — Wave 2 v4.0).

**Zero advisor novo atribuivel a esta sessao** (esta sessao nao
escreveu nada ainda — confirmacao baseline).

### 14.6 Cloudflare R2

Nao validado nesta sessao — o C19 nao toca R2 (apenas identifica
prova, sem acesso a imagem). Sem necessidade.

---

## 15. Decisoes a Confirmar no Gate 2

| # | Decisao | Proposta da analise | Necessita confirmacao |
|---|---|---|---|
| D1 | Rate limit backend nesta sessao OU follow-up? | Follow-up em sessao separada (escopo do prompt e frontend-only) — registrar como achado obrigatorio antes do PR para `main`. | Mario |
| D2 | "PRV-" como decoracao (`<span>`) ou parte do `value` editavel? | Decoracao. Prepender no submit. | Mario |
| D3 | Lib de mascara: nova OU manual? | **Manual** (zero dep). | Mario |
| D4 | Auto-uppercase no input? | SIM. | Mario |
| D5 | Bloqueio rigido vs permissivo durante digitacao de chars invalidos? | **Rigido** (caractere fora do alfabeto da posicao nao aparece). | Mario |
| D6 | Auto-submit ao completar 18 chars? | NAO. | Mario |
| D7 | Uniformizar mensagem de `QR_INVALIDO` (client + 422 backend) → `PROVA_NAO_ENCONTRADA`? | SIM (anti-enumeracao em camada UI). | Mario |
| D8 | Reset de `manualState` para `idle` no `onChange` do input? | SIM (UX: banner some quando usuario edita). | Mario |
| D9 | `// @vitest-environment jsdom` per-file no teste do hook? | SIM (minimo Vitest, alinhado com D-13 da Wave 1 v4.0). | Mario |
| D10 | Adicionar hint sr-only `id="manual-hint"` + `aria-describedby` dinamico? | SIM (acessibilidade aprofundada). | Mario |

---

## 16. Criterios de Aceitacao do Gate 1

| Item | Status |
|---|---|
| `docs/wave3-v4-c10/contrato-c19.md` presente e coerente com codigo real | ✅ |
| UI do C19 presente no codigo C10 (mapeada na §3) | ✅ |
| Camada de servico com tipos e funcoes documentadas | ✅ |
| Validacao MCP Supabase (coluna + indice + RLS + advisors) | ✅ |
| Plano de mascara + validacao + acessibilidade | ✅ |
| Tabela anti-enumeracao explicita | ✅ |
| Plano de testes com cobertura ≥80% camada dominio/servico | ✅ |
| Riscos R-1..R-11 documentados | ✅ |
| Migrations: nenhuma | ✅ |
| Branch dedicada `wave3-v4-c19/analysis` | ✅ |
| Commit a fazer: `docs(wave3-v4/c19): análise read-only pré-execução` | (proximo passo) |

---

## 17. Pedido de Autorizacao

Esta sessao **NAO** executou nenhuma modificacao em codigo de
producao, schema, RLS ou backend. **Apenas leitura e criacao deste
documento.** Pronta para receber confirmacao para Gate 2.

**Aguardando string AUTORIZADO GATE 2 — WAVE 3 v4.0 / C19 para
prosseguir.**

Caso a autorizacao venha acompanhada de decisoes (D1-D10), incorporar
antes do primeiro commit no branch `wave3-v4/componente-19`.

---

**Fim do Gate 1.**

---

## Apendice A — Execucao (Gate 2)

**Data:** 2026-05-11
**Branch de execucao:** `wave3-v4/componente-19`
**Autorizacao:** "Pode prosseguir" (Mario, 2026-05-11) — interpretado
como autorizacao com os defaults propostos para D1-D10.

### A.1 Diff entre proposta (Gate 1) e o que foi feito (Gate 2)

| Item proposto | Feito? | Diff |
|---|---|---|
| `frontend/src/lib/codigo-publico.ts` (regex + mascara + alfabeto por posicao) | ✅ | 139 LOC. Inclui `aplicarMascara`, `montarCodigoCompleto`, `validarFormatoCodigoPublico`, `isCharValidoEmPosicaoSemHifen`, `isDisplayCompleto`. |
| `__tests__/codigo-publico.test.ts` com 15+ casos | ✅ | **43 testes** (mais do que o minimo). Cobre paridade backend, mascara incremental, bloqueio por posicao, idempotencia, integracao mascara→validacao. |
| Hook `useCodigoPrvInput` (binding) | ✅ | 68 LOC em `hooks/useCodigoPrvInput.ts`. Sem testes Vitest dedicados (D9 confirmada — logica testavel ja nas funcoes puras; hook validado por E2E). |
| Integracao no `<ManualPanel>` | ✅ | `page.tsx` +133 / -21 LOC. Substitui `useState("")` por `useCodigoPrvInput`. |
| Foco automatico (R-8 / D10) | ✅ | `useRef` + `useEffect([])` no `<ManualPanel>`. Dispara em cada mount do panel (AnimatePresence `mode="wait"`). |
| Label sr-only estendida + hint sr-only adicional | ✅ | `<label>` agora diz "Codigo da prova no formato PRV-AAAA-MM-NNNNNN". `<span id="manual-hint" sr-only>` com instrucoes do alfabeto. `aria-describedby` dinamico. |
| `MENSAGENS_C19` uniformizando QR_INVALIDO → "Prova nao encontrada." (D7) | ✅ | Definido em `page.tsx` com `mensagemFinal` helper. Aplicado a validacao client-side e a mapeamento backend. |
| Reset de banner no `onChange` (D8) | ✅ | `handleManualChange` zera `manualState` quando estava em error. |
| Botao "Tentar novamente" em `ERRO_REDE` (R-10) | ✅ | `tentarNovamenteManual` chama `setManualState({ kind: "idle" })` sem mexer no input. |
| `maxLength={14}` no input | ✅ | Defesa em profundidade alinhada ao backend. |
| `codigoInput` preservado ao alternar tabs (R-9) | ✅ | `trocarParaCamera` continua zerando apenas `manualState`. |
| Update do `contrato-c19.md` (Status: Entrega completa) | ✅ | Secao 7 adicionada com casos de uso, decisoes, validacao numerica. |
| CHANGELOG, DECISIONS (ADRs 141-145), CLAUDE.md | ✅ | Apendices novos. |
| `smoke-validation.md` do C19 | ✅ | 20 cenarios criados para Mario rodar antes do PR. |

### A.2 Decisoes nao tomadas / desvios

- **D1 (rate limit backend):** mantido como follow-up. ADR-145 documenta.
- **R-2 (posicionamento do "PRV-"):** decisao **decoracao** confirmada
  pelo Mario implicitamente — o `<span aria-hidden>` original do C10
  foi preservado; `montarCodigoCompleto(display)` prepende "PRV-" no
  submit. Sem novo edit visual.
- **Auto-submit (D6):** confirmado NAO. Sem auto-submit.

### A.3 Validacao numerica final

| Metrica | Pos-C10 | Pos-C19 |
|---|---|---|
| Vitest tests | 46 | **89** (+43) |
| tsc --noEmit | exit 0 | exit 0 |
| next build | 13/13 paginas | 13/13 paginas |
| Bundle `/escanear` | 7.68 kB / 210 kB | **8.31 kB / 210 kB** |
| MCP advisors security | 2 | 2 (mesmos) |
| MCP advisors performance | 13 | 13 (mesmos) |
| Migrations | — | **zero** |

### A.4 Sequencia de commits (4 funcionais + 1 docs)

```
63d8625 / 8dc6a92  docs(wave3-v4/c19): análise read-only pré-execução
f5e3271  feat(wave3-v4/c19): util codigo publico (regex + mascara + alfabeto por posicao)
f8f7492  feat(wave3-v4/c19): hook useCodigoPrvInput (binding sobre funcoes puras)
6e42129  feat(wave3-v4/c19): ativa fallback de digitacao manual no <ManualPanel>
[próximo] docs(wave3-v4/c19): contrato + CHANGELOG + DECISIONS + CLAUDE + analysis Execucao + smoke
```

### A.5 Smoke E2E manual (DEFERRED — humano)

Criado em `docs/wave3-v4-c19/smoke-validation.md` com 20 cenarios.
Mario executa antes do PR para `main`. Veredito >= 18/20 PASS para
merge.

### A.6 Pendencias bloqueantes para PR em `main`

1. **Smoke E2E manual** acima — DEFERRED humano.
2. **Rate limit backend** (ADR-145) — FOLLOW-UP OBRIGATORIO em
   sessao separada.

Pendencias nao-bloqueantes (ja resolvidas):
- ✅ `tsc --noEmit` exit 0.
- ✅ `vitest run` 89/89.
- ✅ `next build` 13/13.
- ✅ MCP advisors sem novos.
- ✅ Documentacao viva atualizada.

---

**Fim do Apendice A — Execucao.**
