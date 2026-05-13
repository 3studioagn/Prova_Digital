# Contrato compartilhado entre Scanner (C10 v4.0) e Digitacao Manual (C19)

**Wave:** 3 v4.0
**Componente entregue:** 10 (atualizacao v4.0)
**Componente consumidor:** 19 (Fallback — Digitacao Manual do Codigo)
**Status do contrato:** ✅ ENTREGUE — pronto para o prompt do C19 referenciar literalmente.
**Documento espelha:** DAT v3.0 §8.1 (Endpoint Unico Idempotente).

---

## 1. Visao geral

A Wave 3 v4.0 introduziu **2 mecanismos** de identificacao de provas:

1. **Camera (C10 v4.0 — entregue agora):** o `html5-qrcode` decodifica
   o QR Code da etiqueta e devolve o **payload completo** (ex.:
   `3SD|PRV-2026-05-K3T9XB|abcd1234567890ef`). Frontend chama
   `identificarProvaPorPayload(payload, ...)`.
2. **Digitacao manual (C19 — proxima entrega da Wave):** o usuario
   digita o **codigo legivel** da etiqueta (ex.: `PRV-2026-05-K3T9XB`)
   e submete. Frontend deve chamar `identificarProvaPorCodigo(codigo, ...)`.

DAT v3.0 §8.1 exige **idempotencia** entre os 2 mecanismos: ambos
resolvem para o **mesmo registro** pelo **mesmo lookup logico**. O
backend ja garante isso atraves de `_carregar_prova_por_codigo_publico_com_scoping`,
chamado pelos dois caminhos.

A camada de servico em `frontend/src/lib/services/identificacao-prova.ts`
e o **ponto unico de integracao**. O C19 NAO precisa criar nada novo
relacionado a transporte HTTP, autenticacao, mapeamento de erros — tudo
ja existe.

---

## 2. API publica da camada de servico

Ver `frontend/src/lib/services/identificacao-prova.ts` (entrega C10).

### 2.1 Tipos

```typescript
/**
 * Codigos de erro tipados retornados ao chamador. Cada um tem mensagem
 * em pt-BR pre-resolvida — o C19 apenas renderiza.
 */
export type CodigoErro =
  | "QR_INVALIDO"           // Backend 422 (formato/hash invalido)
  | "PROVA_NAO_ENCONTRADA"  // Backend 404 (inexistente OU fora do scope)
  | "DISPOSITIVO_SEM_CAMERA" // Setado pelo useScanner em falha de hardware
  | "ERRO_REDE"             // Backend 5xx ou network failure
  | "SESSAO_EXPIRADA";      // Backend 401

/**
 * Resultado da identificacao — tagged union.
 * TypeScript impede esquecer de tratar o erro silenciosamente.
 */
export type ResultadoIdentificacao =
  | { tipo: "sucesso"; prova: ScanResponse }
  | { tipo: "erro"; codigo: CodigoErro; mensagem: string };

/**
 * Record exhaustivo de mensagens padrao em pt-BR — exportado em
 * pos-auditoria 2026-05-11 (AUD-W3C10-020) para C19 customizar.
 * `Record<CodigoErro, string>` forca TypeScript a barrar entrada
 * orfa ou faltante quando a uniao mudar.
 */
export const MENSAGENS_ERRO_PADRAO: Record<CodigoErro, string>;

/** Helper que retorna a mensagem padrao para um codigo. */
export function mensagemPara(codigo: CodigoErro): string;
```

### 2.2 Funcao que o C19 vai consumir

```typescript
export async function identificarProvaPorCodigo(
  codigo: string,                              // ex: "PRV-2026-05-K3T9XB"
  params: { getToken: () => Promise<string | null> },
): Promise<ResultadoIdentificacao>;
```

**Caracteristicas:**

- **Sem mock de hardware**: a camada e testavel em `vitest --environment node`.
  O C19 herda essa propriedade — testes do C19 que usam o servico nao precisam
  configurar JSDOM.
- **Token via callback**: o C19 passa `getToken` (mesma assinatura usada
  pelo `useScanner` e outros hooks). Erro de autenticacao vira
  `SESSAO_EXPIRADA` — sem flash, sem chamada ao backend.
- **Mensagens em pt-BR ja resolvidas**: o C19 nao precisa duplicar
  copy. Em caso de erro: `result.mensagem` ja vem com o texto pronto.
  Se C19 quiser sobrescrever, basta condicionar pelo `result.codigo`.

### 2.3 Comportamento backend (referencia do contrato)

`POST /api/v1/provas/scan`:

```json
{ "codigo": "PRV-AAAA-MM-NNNNNN" }
```

Resposta 200:
```json
{
  "prova": { "id": "...", "codigo_publico": "...", "rota": "...", ... },
  "transicoes_permitidas": [...],
  "motivo_obrigatorio_em": [...]
}
```

Erros:

| HTTP | Cenario | Codigo retornado |
|---|---|---|
| 200 | Sucesso | `{ tipo: "sucesso", prova: ... }` |
| 401 | Token ausente/invalido | `SESSAO_EXPIRADA` |
| 404 | Codigo formato invalido OR inexistente OR fora do scope | `PROVA_NAO_ENCONTRADA` (mensagem identica para os 3) |
| 502 | DB transitorio | `ERRO_REDE` |

Note que **404 e generico** para 3 cenarios distintos — alinhado a
DAT v3.0 §8.2 (protecao contra enumeracao). C19 nao deve diferenciar
"formato invalido" de "fora do scope" — protege contra timing attack.

---

## 3. Roteiro de implementacao do C19 (sugestao)

### 3.1 UI de digitacao manual (ja parcialmente entregue no C10 v4.0)

O Componente 10 v4.0 entregou o **shell visual** do tab "Manual" em
`(dashboard)/escanear/page.tsx` (componente `<ManualPanel>`):

- Input com placeholder `PRV-AAAA-MM-NNNNNN`.
- Botao "Buscar prova →" que ja chama `identificarProvaPorCodigo`.
- Banner de erro inline.
- `aria-invalid` + `aria-describedby` do banner.

**O que o C19 deve adicionar/refinar:**

1. **Mascara de digitacao em tempo real** — input formata
   automaticamente `PRV-AAAA-MM-NNNNNN`, separadores aparecem
   conforme o usuario digita. Sugestao: lib `imask` ou implementacao
   manual com `useState` no `onChange`. **Limite hard:** `max_length=32`
   no backend (AUD-W3C10-012; era 64) — o C19 deve respeitar esse teto.
   Codigos plausiveis tem 18 chars; folga ate 32 cobre typos sem
   inflar superficie. Acima de 32 chars o backend retorna 422 Pydantic
   (distinguivel de 404 generico — aceito por estar fora da faixa
   plausivel).
2. **Validacao client-side antes do submit** — rejeitar formato
   invalido sem chamar a API. Sugestao: regex igual ao
   `validar_formato_codigo_publico` do backend (alfabeto sem 0/O e
   1/I/L). Mensagem em pt-BR diferenciada do erro do backend.
3. **Auto-uppercase** — converter para maiusculas no input.
4. **Auto-submit ao completar 18 chars** — opcional, melhora UX.
5. **Rate limiting client-side** — opcional defesa em profundidade
   (DAT §8.2 cita rate-limit no backend, nao client). Pode ser
   contador local que bloqueia submit por X segundos apos N tentativas
   sem sucesso.
6. **Mensagens de erro ricas** — alem do `result.mensagem` retornado
   pelo servico, C19 pode condicionar mensagens custom por tipo
   (e.g. "Formato invalido — confira a etiqueta" para erros do regex
   client-side). Para reutilizar a mensagem padrao do C10, importar
   `mensagemPara(codigo)` (AUD-W3C10-020) ou `MENSAGENS_ERRO_PADRAO[codigo]`.

### 3.2 Backend (NADA NOVO necessario)

`POST /api/v1/provas/scan` ja aceita `codigo` desde o C10 v4.0.
O backend faz:
- Valida formato via `validar_formato_codigo_publico`.
- Lookup direto via `_carregar_prova_por_codigo_publico_com_scoping`.
- Audit log com `origem='manual'`.
- Sem hash a validar (digitacao nao tem hash).

C19 NAO precisa modificar provas.py, schemas, RLS, etc.

### 3.3 Rate limiting backend (opcional para C19)

DAT v3.0 §8.2 cita: **30 tentativas por usuario autenticado por minuto;
excedido retorna 429**. **Esta funcionalidade NAO foi entregue no C10 v4.0**
(escopo).

C19 deve:
- Adicionar middleware de rate-limit (sugestao: `slowapi` ou Redis-based
  in-memory counter no FastAPI) escopado ao endpoint `/scan` filtrado
  por `current_user.id`.
- Mapear 429 para um codigo novo na camada de servico, ex.:
  `RATE_LIMITED` → "Muitas tentativas. Aguarde alguns minutos."
- Nao rodar rate-limit no caminho `payload` (camera) — apenas no
  caminho `codigo` (manual) onde a enumeracao e exploravel.

### 3.4 Testes do C19

A camada de servico ja tem 16 testes em
`src/lib/services/__tests__/identificacao-prova.test.ts`. C19 deve adicionar:

- Testes da mascara de digitacao (formato invalido rejeitado, formato
  valido aceito, separadores aparecem corretamente).
- Testes de UX de erro especifico do C19 (mensagens custom, contador
  de tentativas).
- Smoke E2E manual conforme `smoke-validation.md` (apos C19 integrar
  com o tab Manual).

---

### 3.5 Customizando mensagens no C19 (AUD-W3C10-020 + AUD-W3C19-003)

A camada de servico ja resolve a mensagem em pt-BR via
`result.mensagem`. O C19 pode usar diretamente:

```tsx
const resultado = await identificarProvaPorCodigo(codigo, { getToken });
if (resultado.tipo === "erro") {
  setMensagem(resultado.mensagem); // texto padrao em pt-BR
}
```

**Implementacao real entregue pelo C19** (refatorada pos-auditoria
em 2026-05-11 — AUD-W3C19-003): a override do C19 e
`MENSAGENS_C19` + `mensagemFinal` vivem em modulo standalone
`frontend/src/lib/c19-mensagens.ts` (extraidos de `page.tsx` para
permitir teste de integracao da invariante anti-enumeracao
byte-a-byte). O `page.tsx` apenas importa:

```tsx
// page.tsx
import { mensagemFinal } from "@/lib/c19-mensagens";

// lib/c19-mensagens.ts
import {
  mensagemPara,
  MENSAGENS_ERRO_PADRAO,
  type CodigoErro,
} from "@/lib/services/identificacao-prova";

export const MENSAGENS_C19: Partial<Record<CodigoErro, string>> = {
  // Anti-enumeracao em camada UI — aponta direto para a string
  // padrao do C10 para eliminar drift potencial.
  QR_INVALIDO: MENSAGENS_ERRO_PADRAO.PROVA_NAO_ENCONTRADA,
};

export function mensagemFinal(codigo: CodigoErro): string {
  return MENSAGENS_C19[codigo] ?? mensagemPara(codigo);
}
```

**Invariante critica** (teste em `__tests__/c19-mensagens.test.ts`,
9 testes Vitest):

```
mensagemFinal("QR_INVALIDO") === MENSAGENS_ERRO_PADRAO.PROVA_NAO_ENCONTRADA
```

Quebrar essa igualdade reintroduz vetor de enumeracao DAT §8.2.

**Importante:**

- O C19 NAO precisa modificar `identificacao-prova.ts`. A logica de
  apresentacao fica encapsulada em `c19-mensagens.ts`.
- Manter as **mesmas decisoes de anti-enumeracao** ao sobrescrever:
  `QR_INVALIDO` (client-side OU 422 backend) usa identica mensagem
  do `PROVA_NAO_ENCONTRADA` (404 generico para 3 cenarios distintos:
  inexistente, fora do scope, formato invalido). C19 nao deve
  distinguir esses casos para o usuario.
- Se C19 adicionar codigo novo (ex.: `RATE_LIMITED`), estender
  `CodigoErro` na camada de servico (PR no `identificacao-prova.ts`)
  + adicionar entrada em `MENSAGENS_ERRO_PADRAO` (TypeScript barra
  build se faltar) + atualizar este documento.

---

## 4. Arquivos relacionados (entrega C10 v4.0)

| Arquivo | Descricao |
|---|---|
| `frontend/src/lib/services/identificacao-prova.ts` | Camada de servico (entrega C10) |
| `frontend/src/lib/services/__tests__/identificacao-prova.test.ts` | 16 testes Vitest |
| `frontend/src/app/(dashboard)/escanear/page.tsx` | `<ManualPanel>` shell visual + chamada do servico |
| `frontend/src/app/(dashboard)/escanear/escanear.module.css` | CSS do tab Manual |
| `backend/app/api/v1/provas.py:scan_prova` | Handler com XOR + lookup polimorfico |
| `backend/app/domain/schemas/prova.py:ScanRequest` | model_validator XOR |
| `backend/app/services/codigo_publico_service.py:validar_formato_codigo_publico` | Regex `PRV-AAAA-MM-NNNNNN` |

---

## 5. Caso o C19 precise de algo novo na camada de servico

Se C19 identificar gap (ex.: novo codigo de erro, parametro novo do
servico), o pull request do C19 deve:

1. **Estender** os tipos em `identificacao-prova.ts` sem quebrar o que
   ja existe (versao 1 do contrato e estavel).
2. **Adicionar testes Vitest** novos cobrindo o caso novo.
3. **Atualizar este documento** (`contrato-c19.md`) com o novo
   contrato/sub-secao.
4. **NAO** mover a logica para um novo modulo paralelo — o ponto e
   ter UM lugar onde a identificacao acontece.

---

## 6. Pontos de atencao para revisao da Wave 3 v4.0

- ✅ Idempotencia camera ↔ manual: ambos chamam o mesmo backend,
  resolvem para o mesmo `provas_digitais` row pelo mesmo
  `codigo_publico`.
- ✅ Mensagens 404 genericas (DAT §8.2).
- ✅ Camada de servico desacoplada: testavel em Node (sem JSDOM).
- ⏳ Rate limiting backend (DAT §8.2): **FOLLOW-UP OBRIGATORIO** — registrado
  na entrega do C19 como achado para sessao separada antes do PR para `main`.
- ✅ Mascara de digitacao: entregue pelo C19 (`lib/codigo-publico.ts` +
  `useCodigoPrvInput`).
- ⏳ Smoke E2E completo do fluxo manual: DEFERRED conforme padrao do C10
  (Mario executa em producao antes do PR final).

---

## 7. Status: Entrega Completa

**Data:** 2026-05-11
**Branch:** `wave3-v4/componente-19`
**Componente:** 19 (Fallback de Digitacao Manual)

### Casos de uso consumidos pelo C19

O Componente 19 chamou `identificarProvaPorCodigo(codigo, { getToken })`
exatamente como o contrato previa. Zero modificacao na camada de
servico (`identificacao-prova.ts`), zero modificacao no endpoint
backend (`POST /api/v1/provas/scan`). Casos:

1. **Submit com codigo formato OK** — chama o servico, recebe 200
   `{ tipo: "sucesso", prova: ... }`, navega para `/provas/[id]`.
2. **Submit com codigo formato OK mas inexistente** — recebe 404
   `{ tipo: "erro", codigo: "PROVA_NAO_ENCONTRADA", mensagem: "Prova nao encontrada." }`,
   renderiza banner.
3. **Submit com codigo formato OK mas prova fora do scope (RLS)** —
   mesma resposta 404 + mesma mensagem (anti-enumeracao DAT §8.2).
4. **Submit com codigo formato invalido (regex client falhou)** —
   NAO chama o servico; renderiza banner com **mensagem identica** ao
   404 generico via `mensagemFinal("QR_INVALIDO")` → "Prova nao
   encontrada." Anti-enumeracao preservada em camada UI.
5. **Submit com falha de rede (`fetch` throws OR backend 5xx)** —
   recebe `ERRO_REDE`, renderiza banner com botao "Tentar Novamente"
   (preserva codigo digitado).
6. **Submit com sessao expirada (401)** — recebe `SESSAO_EXPIRADA`,
   renderiza banner padrao.

### Helpers utilizados (AUD-W3C10-020)

- `mensagemPara("PROVA_NAO_ENCONTRADA")` — usado no fallback do
  `mensagemFinal` para 4 dos 5 codigos.
- `MENSAGENS_C19: Partial<Record<CodigoErro, string>>` — override
  local **apenas** para `QR_INVALIDO` (mapeia para "Prova nao
  encontrada." em vez do texto padrao "QR Code nao reconhecido...").

### Decisoes de produto (D1-D10 registradas em DECISIONS.md / ADR-141 a ADR-145)

- **D1 — Rate limiting backend:** NAO incluido nesta sessao (prompt
  explicitamente escopa C19 como frontend-only). Registrado em
  `analysis.md §13 R-1` como **FOLLOW-UP OBRIGATORIO** antes do PR
  para `main`. Defesa em profundidade atual mantida: validar formato
  no client + ANTES do SELECT no backend + RLS antes da resposta +
  404 generico unificado.
- **D2 — "PRV-" como decoracao** (span aria-hidden), nao parte do
  input. Funcao `montarCodigoCompleto` prepende ao submit.
- **D3 — Mascara manual** (sem nova dep). Funcao pura `aplicarMascara`
  em `lib/codigo-publico.ts`.
- **D4 — Auto-uppercase** dentro de `aplicarMascara`.
- **D5 — Bloqueio rigido por posicao**: ano/mes = digitos 0-9; sufixo
  = alfabeto sem ambiguos. Chars fora do alfabeto da posicao **nao
  aparecem** no input.
- **D6 — Auto-submit ao completar:** NAO. Manter clique explicito.
- **D7 — Uniformizacao `QR_INVALIDO` → "Prova nao encontrada."** em
  camada UI (anti-enumeracao).
- **D8 — Reset de banner de erro no `onChange`** do input.
- **D9 — Sem `@testing-library/react` / `jsdom`:** logica testavel
  vive em funcoes puras (43 testes Vitest); hook e binding trivial
  validado por E2E.
- **D10 — `aria-describedby` dinamico** apontando para `#manual-error`
  (estado erro) OU `#manual-hint` (estado normal). Label sr-only
  estendida.

### Validacao numerica

| Metrica | Antes do C19 (pos-AUD C10) | Apos C19 |
|---|---|---|
| Vitest tests | 46 | **89** (+43 novos do codigo-publico) |
| tsc --noEmit | exit 0 | exit 0 |
| next build | 13/13 paginas | 13/13 paginas |
| Bundle `/escanear` | 7.68 kB / 210 kB | **8.31 kB / 210 kB** (+0.63 kB) |
| Advisors security | 2 (pre-existentes) | 2 (mesmos) |
| Advisors performance | 13 (pre-existentes) | 13 (mesmos) |
| Migrations | — | — (zero migration nesta sessao) |

### Arquivos tocados

**Novos:**
- `frontend/src/lib/codigo-publico.ts` (139 LOC).
- `frontend/src/lib/__tests__/codigo-publico.test.ts` (300 LOC).
- `frontend/src/hooks/useCodigoPrvInput.ts` (68 LOC).

**Modificados:**
- `frontend/src/app/(dashboard)/escanear/page.tsx` (+133 / -21 LOC).
- `docs/wave3-v4-c10/contrato-c19.md` (este apendice).
- `CHANGELOG.md`, `DECISIONS.md`, `CLAUDE.md`.
- `docs/wave3-v4-c19/analysis.md` (apendice Execucao).

**Inalterados (proibidos pelo prompt):**
- `frontend/src/lib/services/identificacao-prova.ts` — contrato preservado.
- `backend/**` — zero touch.
- `shared/access-matrix.json` — `scanner` rule inalterada (full × 4 perfis).
