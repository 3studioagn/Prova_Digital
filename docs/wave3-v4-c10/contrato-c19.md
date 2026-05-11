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
   manual com `useState` no `onChange`.
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
   client-side).

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
- ⏳ Rate limiting (DAT §8.2): C19 faz.
- ⏳ Mascara de digitacao: C19 faz.
- ⏳ Smoke E2E completo do fluxo manual: C19 faz.
