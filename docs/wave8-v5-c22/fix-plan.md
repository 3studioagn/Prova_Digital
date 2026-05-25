# Plano de Correção Pós-Auditoria — Componente 22 (Wave 8 v5.0)

**Sessão:** Wave 8 v5.0 / C22 / Fixes — Correção dos achados da auditoria sênior independente
**Tipo:** Gate-based two-stage — Gate 1 (este documento, sem código de produção)
**Data:** 2026-05-25
**Branch de plano:** `wave8-v5-c22/fixes/plan` (a partir de `wave8-v5-c22/audit` HEAD `3eb4069`)
**Branch de execução proposto (Gate 2):** `wave8-v5-c22/fixes/execution` (a partir deste)
**Base do PR final:** `development` (v4.0 não mergeada em `main`).
**Persona:** engenheiro de software sênior — correção dirigida por relatório de auditoria.

---

## 0. Sumário executivo

A auditoria sênior independente do C22 produziu **14 achados** em
`docs/wave8-v5-c22/audit-report.md` (HEAD `3eb4069`):

| Severidade | Total | Status |
|---|---|---|
| CRÍTICO | 0 | — |
| ALTO | 1 | Ratificado em ADR-164 (chancela explícita do Mario, Q1) — **NO-OP** |
| MÉDIO | 4 | 2 corrigíveis em código + 2 dependentes do Mario (DEFERRED ao smoke E2E) |
| BAIXO | 5 | Todos corrigíveis (cirúrgicos) |
| INFO | 4 | Todos registro/no-op (1 não atribuído ao C22) |

**Categorias críticas avaliadas — todas NEGATIVAS:**

- (a) Decisão de design ignorada? **NÃO** — auditor confirmou 13/13 decisões conformes a ADR-163/164.
- (b) Cenário obrigatório com bug? **NÃO** — cobertura por leitura de código + 17 testes Vitest dos helpers; smoke E2E manual permanece como gate (AUD-004, depende do Mario).
- (c) Arqueologia ignorada/divergente? **NÃO** — implementação fiel a `arqueologia.md` com 3 adaptações documentadas (labels v4.0, seletor Aprovar/Reprovar, anti-enumeração).
- (d) Modificação não-autorizada do backend de assinatura? **NÃO** — `git diff origin/development..HEAD -- backend/` é **VAZIO** (revalidado nesta sessão).
- (e) Modificação não-autorizada do `contrato-c12.md`? **NÃO** — `git diff origin/development..HEAD -- docs/wave3-v4-c11/contrato-c12.md` é **VAZIO**.
- (f) Modificação não-autorizada de componentes anteriores? **NÃO** — só integração leve declarada no `escanear/page.tsx` (3 imports + 1 state + 1 callback + 1 render condicional) e reativação do `useExecutarTransicao` (órfão desde C10 v4.0 — declarado em ADR-163).
- (g) Anti-enumeração quebrada? **NÃO** — preservada nas 6 dimensões; **AUD-W8C22-003 é defesa em profundidade adicional** (porta aberta para regressão futura — não enumeração real hoje).
- (h) Tratamento errado de provas legacy v3.0? **NÃO** — `AssinaturaModal` agnóstico de rota; backend dispatcha v3/v4 pelo facade.
- (i) Tratamento errado dos 3 contextos do motorista? **NÃO** — `badgeContextoMotorista` espelha `contextoMotorista()` do `prova.ts`.
- (j) Race condition mal-tratada? **NÃO** — `isConflict` → view `"conflito"` → `/provas/[id]` (cenário 9).
- (k) Falha de rede mal-tratada? **NÃO** — D5: canvas preservado, retentável.
- (l) Violação de escopo? **NÃO** — sem implementação de responsividade mobile (escopo C23); sem lib nova; sem modificação de backend.
- (m) Acessibilidade? **NÃO crítico** — apenas AUD-W8C22-006 (id duplicado — HTML inválido se ambos coexistirem; atualmente mutuamente exclusivos via render condicional).
- (n) Performance? **NÃO medido** — sem ambiente acionável; smoke do Mario fechará (cenário 11/RNF-002).

**Recomendação geral:** aplicar **3 correções em código** (AUD-003 + AUD-005 + AUD-006) que cobrem todos os MÉDIOS corrigíveis e o BAIXO de a11y. Os 4 BAIXOS opcionais (AUD-007/008/009/010) são qualidade de código incremental — proponho aplicar AUD-007 (UX clara) e AUD-008 (defesa em profundidade pequena), e deixar AUD-009/AUD-010 documentados como deferrals técnicos (registro em `DECISIONS.md`). Os 2 DEFERRED ao Mario (AUD-002 + AUD-004) e os 4 INFO seguem após o smoke.

---

## 1. Inventário consolidado dos 14 achados

> Convenção: ID · Severidade · Categoria · Onde · Descrição · Recomendação original · Status atual · Flags booleanas.

### AUD-W8C22-001 — Divergência formal RN-014 literal / Cenário 4
- **Severidade:** ALTA (chancelada).
- **Categoria:** Aderência ao especificado.
- **Onde:** `escanear/page.tsx:103-112` (`handleIdentificada`) + `lib/assinatura/helpers.ts:76-78` (`deveAbrirAssinatura`).
- **O quê:** "ator-errado in-scope" navega para `/provas/[id]` em vez de exibir mensagem genérica.
- **Recomendação original:** MANTER (chancela explícita em ADR-164, Q1 do Mario, 2026-05-22).
- **Status atual:** **RATIFICADO — NO-OP.**
- **Flags:**
  - Decisão de design ignorada? NÃO (foi ratificada).
  - Cenário obrigatório com bug? NÃO (cenário reescrito em ADR-164).
  - Arqueologia ignorada? NÃO (3 adaptações documentadas).
  - Mod backend / contrato / componentes anteriores? NÃO.
  - Anti-enumeração? NÃO (defesa via escopo RLS + 404 genérico preservada).
  - Reuso quebrado? NÃO.
  - Tratamento legacy / contexto motorista? NÃO.
  - Race / rede / escopo / a11y / performance? NÃO.
  - Afeta C23? NÃO.

### AUD-W8C22-002 — `visual-guide.md` é STUB (sem screenshots)
- **Severidade:** MÉDIA.
- **Categoria:** Documentação.
- **Onde:** `docs/wave8-v5-c22/visual-guide.md` (109 LOC com 14 placeholders `![...]()`).
- **O quê:** auto-declarado como STUB; padrão idêntico ao C12/C16 pre-smoke.
- **Recomendação original:** preencher screenshots durante o smoke E2E manual.
- **Status atual:** **DEFERRED ao Mario** (corrigível só após smoke).
- **Flags:**
  - Decisão de design / cenário obrigatório / arqueologia / mod backend / mod contrato / mod componentes / anti-enum / reuso / legacy / contexto motorista / race / rede / escopo / a11y / performance / afeta C23? Todas NÃO.
  - **Por que não é ALTO:** consistente com a Decisão D11 Opção B; auditor classificou MÉDIA e o próprio C22 declarou STUB.

### AUD-W8C22-003 — `useExecutarTransicao.state.error` preserva `err.message` cru para 422
- **Severidade:** MÉDIA (defesa em profundidade — porta aberta para regressão).
- **Categoria:** Anti-enumeração.
- **Onde:** `frontend/src/hooks/useExecutarTransicao.ts:110-116`.
- **O quê:** o backend pode retornar 422 com `AtorNaoAutorizadoError` cujo texto **lista os setores permitidos**. O hook armazena `state.error = err.message` cru. O modal hoje **não consome** `state.error` (desestrutura só `executar`), mas qualquer consumidor futuro que faça `const { error } = useExecutarTransicao(...)` exporia.
- **Recomendação original:** mapear 422 inesperado para mensagem genérica no próprio hook, mantendo `status` no retorno.
- **Status atual:** **PENDENTE — corrigir em código** (1 commit cirúrgico).
- **Flags:**
  - Anti-enumeração? **SIM** — dimensão "logs/UI" (mensagem cru pode vazar setores se algum consumidor futuro consumir `state.error`).
  - Defesa em profundidade? SIM.
  - Decisão de design / cenário / arqueologia / mod backend / mod contrato / mod componentes anteriores? NÃO.
  - Afeta C23? NÃO.

### AUD-W8C22-004 — Smoke E2E manual (10 cenários) pendente
- **Severidade:** MÉDIA (bloqueante para release).
- **Categoria:** Cobertura de Testes.
- **Onde:** `docs/wave8-v5-c22/smoke-validation.md` — checklist não preenchido.
- **O quê:** verificação programática inviável (R-6, D-4) — exige backend local + sessão autenticada + provas-fixture nos estados acionáveis.
- **Recomendação original:** Mario subir backend local + criar provas-fixture + executar 10 cenários + 7 transversais.
- **Status atual:** **DEFERRED ao Mario.**
- **Flags:** todas NÃO. **Por que não é ALTO:** consistente com D11 Opção B (chancelada).

### AUD-W8C22-005 — Sem teste unitário novo para `useExecutarTransicao` (reativação)
- **Severidade:** MÉDIA.
- **Categoria:** Cobertura de Testes.
- **Onde:** `frontend/src/hooks/useExecutarTransicao.ts` — sem `__tests__/`.
- **O quê:** hook reativado + campo `status` novo; mapeamento 201/401/404/409/422/5xx/rede para `{status, isConflict, error}` sem teste isolado. Cobre também a invariante de AUD-003.
- **Recomendação original:** adicionar 5-7 testes em `__tests__/useExecutarTransicao.test.ts` mockando `apiFetch`/`ApiError`, validando:
  - 201 → `{data, isConflict=false, status=201}`.
  - 401 → `{data=null, status=401, error="Sessao expirada..."}`.
  - 409 → `{data=null, isConflict=true, status=409, error="O status..."}`.
  - 422 → `{data=null, status=422}`; **TESTAR que `error` não expõe setores** (cobre AUD-003).
  - 5xx → `{data=null, status=5xx, error="Falha de conexao..."}`.
  - rede caiu (não-`ApiError`) → `{status=null}`.
  - token nulo → `{status=401}` sem chamar `apiFetch`.
- **Status atual:** **PENDENTE — corrigir em código.**
- **Flags:**
  - Cobertura de testes? SIM.
  - Anti-enumeração? SIM (parte das asserções valida AUD-003).
  - Decisão de design / cenário / arqueologia / mod backend / mod contrato / mod componentes? NÃO.
  - Race / rede / legacy / contexto motorista / a11y / performance / escopo? NÃO (porém um dos testes simula 409 e outro simula 5xx, cobrindo essas dimensões em nível unit).
  - Afeta C23? NÃO.

### AUD-W8C22-006 — id `assinatura-titulo` reutilizado em 2 componentes
- **Severidade:** BAIXA.
- **Categoria:** Acessibilidade / Correção (HTML válido).
- **Onde:** `AssinaturaModal.tsx:405` (`CabecalhoContexto`) + `:449` (`ResultadoView`).
- **O quê:** dois `<h2>` com mesmo `id="assinatura-titulo"`; HTML inválido se ambos coexistirem. Atualmente mutuamente exclusivos via render condicional do `view` — frágil para regressão.
- **Recomendação original:** extrair `const TITULO_ID = "assinatura-titulo"` ou usar IDs distintos.
- **Status atual:** **PENDENTE — corrigir em código.**
- **Flags:**
  - Acessibilidade? SIM (BAIXO — HTML válido + `aria-labelledby` único).
  - Decisão de design / cenário / arqueologia / mod backend / mod contrato / mod componentes / anti-enum / reuso / legacy / contexto motorista / race / rede / escopo / performance / afeta C23? NÃO.

### AUD-W8C22-007 — View `"sessao"` botão "Fazer login" não navega para `/login`
- **Severidade:** BAIXA.
- **Categoria:** Correção (UX).
- **Onde:** `AssinaturaModal.tsx:252-261`.
- **O quê:** view `"sessao"` chama `onFechar` → `/provas/[id]`, que tem middleware → redireciona ao `/login` indiretamente. Label "Fazer login" cria expectativa de ir direto.
- **Recomendação original:** ou trocar label, ou customizar view para chamar `router.push("/login")` explicitamente.
- **Status atual:** **PENDENTE — corrigir em código** (recomendo: navegar direto para `/login`).
- **Flags:**
  - UX? SIM.
  - Decisão de design / cenário / arqueologia / mod backend / mod contrato / mod componentes / anti-enum / reuso / legacy / contexto motorista / race / rede / escopo / a11y / performance / afeta C23? NÃO.

### AUD-W8C22-008 — View `"sucesso"` confia no `destino` local em vez do `result.data.prova.status`
- **Severidade:** BAIXA.
- **Categoria:** Correção (defesa em profundidade).
- **Onde:** `AssinaturaModal.tsx:228-238` (`STATUS_LABELS[destino]`).
- **O quê:** se o backend transformar destino internamente (hipótese remota — não acontece hoje), a view mostraria valor desatualizado.
- **Recomendação original:** `setStatusAplicado(data.prova.status)` e usar na view.
- **Status atual:** **OPCIONAL — recomendo aplicar** (pequeno, defesa em profundidade).
- **Flags:** todas NÃO; rotulado pela auditoria como "opcional".

### AUD-W8C22-009 — `useEffect([view])` usa `querySelector` em vez de ref
- **Severidade:** BAIXA.
- **Categoria:** Correção (idiomatismo).
- **Onde:** `AssinaturaModal.tsx:123-128`.
- **O quê:** busca DOM por id a cada troca de view; idiomatismo React seria capturar via callback ref.
- **Recomendação original:** opcional; padrão atual funciona.
- **Status atual:** **OPCIONAL — proponho DEFERRED** (registro em DECISIONS.md). Refator de baixo retorno; combina com AUD-006 (id) se aplicarmos juntos no futuro.
- **Flags:** todas NÃO.

### AUD-W8C22-010 — `textarea` com `required` + validação manual cooperam mas redundam
- **Severidade:** BAIXA.
- **Categoria:** Correção (idiomatismo).
- **Onde:** `AssinaturaModal.tsx:337` + `:157-160`.
- **O quê:** HTML5 `required` impede submit nativo; `submeter` faz `if (!motivoLimpo)` adicional. Cooperam, mas intenção seria mais clara com `noValidate` no form ou removendo `required`.
- **Recomendação original:** opcional; funciona.
- **Status atual:** **OPCIONAL — proponho DEFERRED** (registro em DECISIONS.md). Cooperam corretamente; não há regressão.
- **Flags:** todas NÃO.

### AUD-W8C22-101 — 5 arquivos CSS uncommitted no working tree
- **Severidade:** INFO.
- **Categoria:** Aderência (não atribuído).
- **Onde:** working tree do Mario (`layout.module.css`, `nova-prova.module.css`, `provas.module.css`, `globals.css`, `tsconfig.tsbuildinfo`).
- **O quê:** Origem: Wave 2 v4.0 / C06 Visual Refresh (registrado em CLAUDE.md). Não são do C22.
- **Status atual:** **NO-OP — não atribuir ao C22.** Stashado nesta sessão como `wave8-v5-c22/fixes: CSS uncommitted pre-C22 (AUD-W8C22-101 INFO) - preservar para Mario` para impedir contaminação do branch de plano.
- **Flags:** todas NÃO.

### AUD-W8C22-102 — Bundle `/escanear` +7.6 kB Size / +10 kB First Load
- **Severidade:** INFO.
- **Categoria:** Performance (justificada).
- **Onde:** `/escanear` 8.31 → 15.9 kB / 210 → 220 kB First Load.
- **O quê:** entrada do `react-signature-canvas` (era órfão, agora ativo) + código do modal. Declarado em CHANGELOG.
- **Status atual:** **NO-OP** — justificado.
- **Flags:** todas NÃO.

### AUD-W8C22-103 — 11 provas legacy NULL + 5 PADRAO/DIRETA em produção
- **Severidade:** INFO.
- **Categoria:** Provas Legacy (informativo).
- **O quê:** confirma relevância do cenário 7 (coexistência v3/v4) — atendido por design.
- **Status atual:** **NO-OP** — informativo.
- **Flags:** todas NÃO.

### AUD-W8C22-104 — 0 provas em estado de motorista/clicheria/vendedor mid-flow em produção
- **Severidade:** INFO.
- **Categoria:** Cobertura de Testes (informativo).
- **O quê:** confirma R-6 — smoke E2E exige criar provas-fixture. Documentado em `smoke-validation.md` §0.
- **Status atual:** **NO-OP** — informativo.
- **Flags:** todas NÃO.

---

## 2. Plano por achado (corrigíveis)

### 2.1 AUD-W8C22-003 — Defesa em profundidade no hook: 422 sem `err.message` cru

**Estratégia:** no `useExecutarTransicao.ts`, mudar o branch `else if (err.status === 422) { msg = err.message; }` para usar mensagem genérica fixa **mas manter `status=422` no retorno** para o consumidor decidir. Manter `err.message` apenas se o backend retornar 422 sem o padrão de `AtorNaoAutorizadoError` (impossível distinguir pelo hook — adotar a postura segura por padrão: mensagem genérica para todo 422).

**Mensagem genérica recomendada:** `"Nao foi possivel registrar a movimentacao."` (paridade com o texto da view `"erro"` do modal — `AssinaturaModal.tsx:270` "Houve um problema ao registrar a movimentacao. Recarregue a pagina e tente novamente.").

**Tipo de correção:** modificação de lógica (3-5 linhas).

**Confirmação:** não modifica backend; não modifica `contrato-c12.md`; não modifica componentes anteriores; sem lib nova; sem responsividade mobile.

**Arquivos tocados:**
- `frontend/src/hooks/useExecutarTransicao.ts` (alterar 1 branch + atualizar JSDoc da função para refletir a nova decisão de anti-enumeração).

**Camadas afetadas:** frontend (hook) · documentação inline.

**Risco de regressão:** BAIXO. Não há consumidor de `state.error` para 422 hoje; o modal usa `status`. Tested by AUD-005.

**Teste que valida:** AUD-005 incluirá assertion específica: `expect(result.error).not.toContain("setor")` para resposta 422 simulada com texto que lista setores (`"Apenas usuarios do setor VENDEDOR podem executar..."`).

**Dependência:** nenhum predecessor; é predecessor de AUD-005.

### 2.2 AUD-W8C22-005 — Testes do `useExecutarTransicao`

**Estratégia:** criar `frontend/src/hooks/__tests__/useExecutarTransicao.test.ts` (Vitest, `environment: node`) com 7 testes mockando `apiFetch`/`ApiError`:

1. `executar` com 201 → `{data, isConflict=false, status=201, error=null}`.
2. `executar` com 401 (`ApiError(401)`) → `{data=null, status=401, error="Sessao expirada..."}`.
3. `executar` com 404 (`ApiError(404)`) → `{data=null, status=404, error="Prova nao encontrada."}`.
4. `executar` com 409 (`ApiError(409)`) → `{data=null, isConflict=true, status=409, error="O status..."}`.
5. `executar` com 422 + texto que **lista setores** → `{status=422, error=mensagem-generica}` — **assertion específica `not.toContain("setor")` cobre AUD-003**.
6. `executar` com 502 → `{data=null, status=502, error="Falha de conexao..."}`.
7. `executar` com erro não-`ApiError` (rede caiu) → `{data=null, status=null, error=mensagem-generica}`.
8. (Bônus) `executar` com `getToken` retornando `null` → `{status=401, error="Sessao expirada..."}` sem chamar `apiFetch`.

Mocks via `vi.mock("@/lib/api", ...)` espelhando `identificacao-prova.test.ts`. Testar com `renderHook` do `@testing-library/react`? **NÃO** — para alinhar com D-13 (cultura Vitest minimal), usar apenas `vi.fn()` para `getToken` + verificar chamada/resultado da função `executar` direto, sem render. (Padrão idêntico a `identificacao-prova.test.ts`.)

Como `useState` está em jogo, posso usar `act + renderHook` se necessário — porém o desenho atual do hook permite chamar `executar` fora de render (o `useState` só armazena state derivado; o retorno da função é puro pelo escopo do mock). Vou validar no Gate 2 se preciso de `renderHook`; se sim, instalar `@testing-library/react` **apenas como devDep** seria um custo (R-1 da Wave 1 v4.0 / D-13). **Plano B preferencial:** extrair a função `executar` para um helper puro `executarTransicao(apiFetch, getToken, input)` testável diretamente, e fazer o hook só envolvê-lo. Decidir no Gate 2 — proposta inicial: testar via `renderHook` se já está disponível, ou avaliar a extração.

**Tipo de correção:** adição (teste novo) + possível refactor leve do hook se for necessário extrair a função pura.

**Confirmação:** não modifica backend / contrato / componentes anteriores; sem lib nova **a confirmar no Gate 2** (se for preciso `@testing-library/react`, escalar antes).

**Arquivos tocados:**
- (novo) `frontend/src/hooks/__tests__/useExecutarTransicao.test.ts`.
- (eventual) `frontend/src/hooks/useExecutarTransicao.ts` — extração da função pura se necessário.

**Camadas afetadas:** frontend (testes) · possível refactor leve do hook.

**Risco de regressão:** BAIXO. Testes novos isolados; refactor leve preserva contrato.

**Dependência:** AUD-003 (a mensagem genérica de 422 vem desse fix).

### 2.3 AUD-W8C22-006 — id `assinatura-titulo` duplicado

**Estratégia:** extrair `const TITULO_ID = "assinatura-titulo"` no `AssinaturaModal.tsx` e substituir o literal nos 3 pontos:
- linha 125 (`querySelector("#${TITULO_ID}")` — note que isso também encaminha AUD-009 caso aplicado, mas mantemos o querySelector aqui).
- linha 210 (`aria-labelledby={TITULO_ID}`).
- linhas 405 + 449 (`id={TITULO_ID}` nos dois h2).

**Não basta extrair a constante** — o achado é que dois h2 com mesmo id coexistem fisicamente nunca, mas se houvesse um bug futuro de renderizar dois ao mesmo tempo, o `document.querySelector` retornaria sempre o primeiro. **Decisão recomendada:** extrair `TITULO_ID` (constante única) **+ adicionar comentário documentando** que os dois `<h2>` são mutuamente exclusivos via `view` — quem editar precisa garantir essa exclusividade.

**Alternativa (mais robusta):** dois IDs diferentes — `assinatura-titulo-form` e `assinatura-titulo-resultado` — e o efeito de foco descobre qual está montado por seletor genérico `[data-modal-title]`. **Proposta:** combinar com data attribute para o foco ser robusto à mudança de qual h2 está montado — `<h2 id={TITULO_ID} data-modal-title tabIndex={-1}>` e o querySelector busca `[data-modal-title]` (cobre AUD-009 marginalmente).

**Recomendação final:** extrair `TITULO_ID` + adicionar `data-modal-title` no h2 + atualizar o querySelector para usar o data attribute (`querySelector("[data-modal-title]")`). Isso resolve AUD-006 (id consistente) e parte de AUD-009 (já não depende do id literal).

**Tipo de correção:** refactor cirúrgico (5-7 linhas alteradas).

**Confirmação:** não modifica backend / contrato / componentes anteriores; sem lib nova.

**Arquivos tocados:**
- `frontend/src/components/assinatura/AssinaturaModal.tsx` (extração de constante + data attribute).

**Camadas afetadas:** frontend (componente).

**Risco de regressão:** BAIXO. Mudança puramente estrutural; comportamento idêntico.

**Teste que valida:** os 17 testes Vitest dos helpers já passam — não há teste de DOM do modal (D11 Opção B), então a validação é **visual via revisão manual** + smoke do Mario (cenário 11 — teclado + foco programático).

**Dependência:** nenhuma.

### 2.4 AUD-W8C22-007 — View `"sessao"`: navegar para `/login` explicitamente

**Estratégia:** `ResultadoView` ganha prop opcional `onClickPrincipal?: () => void` que, se passada, substitui o `onFechar` no botão. Para a view `"sessao"`, passar `() => router.push("/login")` (precisa do `useRouter` no `AssinaturaModal` — hoje quem faz `router.push` é o `escanear/page.tsx` via `onFechar`).

**Alternativa minimalista:** trocar o label "Fazer login" para "Entendi" e manter o `onFechar` → `/provas/[id]` → middleware redireciona ao login indiretamente. Menos UX mas zero refactor.

**Recomendação:** versão completa — adicionar `useRouter` no `AssinaturaModal` para a view `"sessao"` navegar a `/login` direto. O ponto fraco de exigir o cliente importar `useRouter` é mínimo (1 import).

**Tipo de correção:** modificação de lógica (4-6 linhas).

**Confirmação:** não modifica backend / contrato / componentes anteriores; sem lib nova.

**Arquivos tocados:**
- `frontend/src/components/assinatura/AssinaturaModal.tsx` (import `useRouter` + `onClickPrincipal` opcional).

**Camadas afetadas:** frontend (componente) · navegação.

**Risco de regressão:** BAIXO. View `"sessao"` é caminho terminal pouco frequente; comportamento atual (vai a `/provas/[id]` → middleware → `/login`) continua sendo um fallback se o `onFechar` for chamado por outro motivo.

**Dependência:** nenhuma.

### 2.5 AUD-W8C22-008 — `setStatusAplicado(data.prova.status)` na view de sucesso

**Estratégia:** depois do `if (data) { ... }` no `submeter`, antes de `setView("sucesso")`, fazer `setStatusAplicado(data.prova.status)`. Substituir `STATUS_LABELS[destino]` por `STATUS_LABELS[statusAplicado]` na view de sucesso. Manter `destino` como fallback (`statusAplicado ?? destino`) para o caso teórico de o backend não devolver a prova com status atualizado (impossível hoje — `TransicaoResponse` sempre tem `prova` populada).

**Tipo de correção:** modificação de lógica (3-5 linhas + 1 useState novo).

**Confirmação:** não modifica backend / contrato / componentes anteriores; sem lib nova.

**Arquivos tocados:**
- `frontend/src/components/assinatura/AssinaturaModal.tsx` (1 useState + 1 setter na linha 175 + 1 substituição na linha 236).

**Camadas afetadas:** frontend (componente).

**Risco de regressão:** BAIXO. Refinamento de defesa em profundidade — comportamento visível ao usuário é idêntico hoje (porque backend devolve `prova.status === destino` sempre).

**Dependência:** nenhuma.

### 2.6 AUD-W8C22-009 — `useEffect([view])` com ref em vez de querySelector

**Estratégia:** **DEFERRED — registrar em DECISIONS.md.** Combina parcialmente com AUD-006 (que já aplicará `[data-modal-title]` em vez de id literal). Refactor de baixo retorno; o padrão atual funciona. Marcação de "follow-up técnico" para sessão futura.

**Justificativa do deferral:** auditor classificou explicitamente como BAIXO e "opcional"; aplicar callback ref em h2 dinâmico (que monta/desmonta com `view`) é mais complexo do que parece (precisa de `useCallback` + handle de cleanup). Custo > benefício para o objetivo desta sessão.

**Documentação:** apêndice em `DECISIONS.md` registrando o deferral com referência a AUD-009.

### 2.7 AUD-W8C22-010 — `textarea` `required` + validação manual

**Estratégia:** **DEFERRED — registrar em DECISIONS.md.** Cooperam corretamente; o `required` HTML5 também serve a usuários sem JS (defesa adicional). Remover seria piorar a a11y (alguns leitores anunciam `required`). Decisão consciente.

**Justificativa do deferral:** auditor classificou BAIXO e "opcional"; o "duplo" cinto-suspensório é defesa em profundidade — mantém comportamento robusto.

**Documentação:** apêndice em `DECISIONS.md` registrando.

---

## 3. Ordem topológica de execução

Lista numerada dos achados **corrigíveis** em código, na ordem que serão aplicados:

1. **AUD-W8C22-003** (MÉDIO · anti-enum hook) — predecessor de AUD-005.
2. **AUD-W8C22-005** (MÉDIO · testes do hook) — valida AUD-003.
3. **AUD-W8C22-006** (BAIXO · id duplicado + a11y) — independente.
4. **AUD-W8C22-007** (BAIXO · view sessão → /login) — independente.
5. **AUD-W8C22-008** (BAIXO · statusAplicado) — independente.

Achados **DEFERRED com registro em DECISIONS.md** (não aplicar código):

- AUD-W8C22-009 (querySelector vs ref) — opcional; resolvido parcialmente em AUD-006.
- AUD-W8C22-010 (textarea required) — cooperação defensiva consciente.

Achados **DEFERRED ao Mario** (não corrigíveis em código nesta sessão):

- AUD-W8C22-002 (screenshots no visual-guide) — após smoke E2E.
- AUD-W8C22-004 (smoke E2E manual) — sessão dedicada do Mario.

Achados **NO-OP**:

- AUD-W8C22-001 (ratificado em ADR-164).
- AUD-W8C22-101..104 (INFO informativos).

---

## 4. Análise de risco agregado

### 4.1 Achados com risco ALTO de regressão
**Nenhum.** Todos os 5 corrigíveis são cirúrgicos e cobertos por testes (Vitest existentes + 7-8 novos do AUD-005).

### 4.2 Achados de modificação não-autorizada do backend (cláusula pétrea)
**Nenhum.** `git diff origin/development..HEAD -- backend/` é VAZIO (revalidado nesta sessão).

### 4.3 Achados de modificação não-autorizada do contrato-c12.md
**Nenhum.** `git diff origin/development..HEAD -- docs/wave3-v4-c11/contrato-c12.md` é VAZIO.

### 4.4 Achados de modificação não-autorizada de componentes anteriores
**Nenhum.** Integração leve declarada em `escanear/page.tsx` (C10) e reativação de `useExecutarTransicao` (órfão desde C10 v4.0) — ambos conformes ADR-163.

### 4.5 Achados de decisão de design ignorada
**Nenhum.** 13/13 decisões conformes a ADR-163/164.

### 4.6 Achados de arqueologia ignorada
**Nenhum.** Implementação fiel com 3 adaptações documentadas em `arqueologia.md` §7.

### 4.7 Achados de cenário obrigatório com bug
**Nenhum.** Cobertura por leitura de código + 17 testes Vitest. Smoke pendente (AUD-004 DEFERRED ao Mario).

### 4.8 Achados de anti-enumeração
**1 (AUD-003).** Dimensão "logs/UI futura" (defesa em profundidade — não vazamento real hoje). Validar com 1 assertion específica em AUD-005 (`not.toContain("setor")` no `error` do retorno do hook para 422).

### 4.9 Achados de provas legacy
**Nenhum.** AUD-103 é informativo.

### 4.10 Achados de contextos do motorista
**Nenhum.** `badgeContextoMotorista` espelha `contextoMotorista()` byte-a-byte.

### 4.11 Achados de race condition
**Nenhum corrigível.** Cenário 9 do smoke E2E pendente (AUD-004). Cobertura por código OK.

### 4.12 Achados de falha de rede
**Nenhum corrigível.** Cenário 6 do smoke E2E pendente (AUD-004). Cobertura por código OK.

### 4.13 Achados de reuso quebrado
**Nenhum.** Sem duplicação de mapping; `STATUS_LABELS`/`ROTA_LABELS`/`contextoMotorista` importados.

### 4.14 Achados de violação de escopo
**Nenhum.** Sem responsividade mobile (escopo C23); sem lib nova; sem modificação de backend.

### 4.15 Achados de acessibilidade
**1 (AUD-006).** id duplicado — HTML inválido se ambos coexistirem. Correção via extração de constante + data attribute. Validar com smoke (cenário 11 — teclado + foco) + revisão visual.

### 4.16 Achados de performance
**Nenhum.** AUD-102 é informativo e justificado (+7.6 kB Size por causa do `react-signature-canvas` que era órfão).

### 4.17 Achados bloqueados por divergência
**Nenhum.**

### 4.18 Achados que requerem nova escalação humana
**Nenhum.** Todas as decisões cabem no escopo já aprovado (ADR-163/164). Se durante o Gate 2 surgir necessidade de `@testing-library/react` para AUD-005, **escalo antes** de instalar a dep.

---

## 5. Plano de validação interna pós-correção

A validação ao final será registrada em `docs/wave8-v5-c22/fix-validation.md`. Critérios:

### 5.1 Por achado corrigido
- **AUD-003:** `git diff` mostra a alteração; AUD-005 inclui assertion específica que falharia se a mensagem original (cru) voltasse.
- **AUD-005:** 7-8 testes Vitest passando; cobertura efetiva 100% do `useExecutarTransicao.ts`.
- **AUD-006:** `git diff` mostra extração de `TITULO_ID` + `data-modal-title`; `npx tsc --noEmit` exit 0; `npx next lint` 0 warnings; revisão visual confirma h2 ainda recebe foco programático.
- **AUD-007:** `git diff` mostra `useRouter` + `onClickPrincipal`; nenhum teste Vitest novo (componente — D11 Opção B); registro em fix-validation com nota de cenário de smoke (`view sessao → clicar "Fazer login" → cai em /login`).
- **AUD-008:** `git diff` mostra `setStatusAplicado`; nenhum teste Vitest novo (componente).

### 5.2 Suíte completa
- `npx vitest run`: **≥ 229 testes** (222 existentes + 7-8 novos do AUD-005); 0 regressão.
- `npx tsc --noEmit`: exit 0.
- `npx next lint`: 0 warnings, 0 errors.
- `npx next build`: 13/13 páginas; bundle `/escanear` ~ 15.9 kB / 220 kB (sem regressão).

### 5.3 Cláusulas pétreas
- `git diff origin/development..HEAD -- backend/`: VAZIO.
- `git diff origin/development..HEAD -- docs/wave3-v4-c11/contrato-c12.md`: VAZIO.
- `git diff origin/development..HEAD -- docs/wave3-v4-c10/contrato-c19.md`: VAZIO.
- `git diff origin/development..HEAD -- shared/access-matrix.json`: VAZIO.
- `git diff origin/development..HEAD -- frontend/src/app/(dashboard)/dashboard/ frontend/src/app/(dashboard)/auditoria/ frontend/src/app/(dashboard)/relatorios/ frontend/src/app/(dashboard)/usuarios/ frontend/src/app/(dashboard)/provas/ frontend/src/app/(dashboard)/nova-prova/ frontend/src/app/(dashboard)/configuracoes/`: VAZIO.
- `git diff origin/development..HEAD -- frontend/src/components/Restricted/ frontend/src/components/AuthToast/ frontend/src/components/KeyboardShortcutsHelp/`: VAZIO.
- `git diff origin/development..HEAD -- frontend/src/lib/access-matrix.ts frontend/src/lib/hooks/use-authorization.ts frontend/src/middleware.ts frontend/src/lib/types/prova.ts`: VAZIO.
- `git diff origin/development..HEAD -- frontend/src/lib/services/identificacao-prova.ts frontend/src/lib/codigo-publico.ts frontend/src/lib/c19-mensagens.ts frontend/src/hooks/useCodigoPrvInput.ts frontend/src/hooks/useScanner.ts frontend/src/hooks/useFocusTrap.ts frontend/src/hooks/useCurrentUser.ts`: VAZIO.
- `git diff origin/development..HEAD -- backend/app/state_machine/`: VAZIO.
- `git diff origin/development..HEAD -- frontend/src/app/(dashboard)/escanear/escanear.module.css`: VAZIO.

### 5.4 Reuso preservado do `contrato-c12.md`
- `grep -r "STATUS_LABELS\b" frontend/src/components/assinatura/ frontend/src/lib/assinatura/` — sem hardcode literal dos 17 estados além do `ACTION_LABELS` (que é o vocabulário de **verbos** do C22, complementar ao `STATUS_LABELS` do contrato).
- `grep -r "contextoMotorista\b" frontend/src/components/assinatura/ frontend/src/lib/assinatura/` — apenas via import de `@/lib/types/prova`.

### 5.5 Anti-enumeração (6 dimensões + 100 chamadas)
Conforme `audit-report.md` §5.4: **NÃO executável programaticamente nesta sessão** (backend Railway fora do ar — D-4 inalterado).

Validação documental:
- Assertion específica do AUD-005 cobre dimensão "UI" (mensagem do hook não vaza setores).
- Defesa em camadas preservada (backend 404 genérico + `/scan` filtra `transicoes_permitidas` + frontend hard-coda mensagens nas views terminais).
- 100 chamadas + medição de timing: **DEFERRED ao smoke do Mario** (`smoke-validation.md` §11 — performance) — registrar nota explícita em `fix-validation.md` que essa dimensão exige backend operacional + script de carga (fora do escopo desta sessão).

### 5.6 Tratamento de provas legacy v3.0
- Sem mudança nesta sessão; cobertura por código preservada (`AssinaturaModal` agnóstico de rota; backend dispatcha v3/v4).
- Cenário 7 do smoke do Mario remanesce.

### 5.7 3 contextos do motorista
- Sem mudança nesta sessão; cobertura pelos 4 testes do `helpers.test.ts` preservada.

### 5.8 Race condition / Falha de rede / Performance / Acessibilidade
- Sem mudança no caminho desses cenários; cobertura por código preservada.
- Validação por smoke do Mario (cenários 6 / 9 / 11) — DEFERRED.

### 5.9 Cobertura ≥ 80% nos arquivos novos/tocados
- `helpers.ts`: ≥ 95% (mantido — 17 testes existentes).
- `useExecutarTransicao.ts`: ≥ 95% após AUD-005 (era 0% isolado, coberto só por uso integrado).
- `AssinaturaModal.tsx` / `CapturaAssinatura.tsx`: cobertura por smoke manual (D11 Opção B — sem snapshot tests). Inalterado.

### 5.10 Advisors MCP
- `get_advisors security` + `get_advisors performance`: idênticos ao baseline pós-C22 (1 INFO + 1 WARN security; 13 INFO performance). Validar via MCP no Gate 2 antes do PR (read-only).

### 5.11 visual-guide.md / smoke-validation.md
- `visual-guide.md`: STUB permanece (AUD-002 DEFERRED ao smoke do Mario).
- `smoke-validation.md`: checklist permanece (AUD-004 DEFERRED ao smoke do Mario).

---

## 6. Plano de atualização de documentação

### 6.1 Acumulativo (entre os commits da execução)
- `CHANGELOG.md` — nova entrada **"C22 — Correções Pós-Auditoria"** apêndice à entrada existente do C22 (linha 5). Conteúdo:
  - Lista dos 5 achados corrigidos (AUD-003/005/006/007/008) com tipo de mudança.
  - Lista dos 2 achados DEFERRED com registro em DECISIONS (AUD-009/010).
  - Lista dos 2 achados DEFERRED ao Mario (AUD-002/004).
  - Lista dos 4 INFO + 1 ALTO ratificado (NO-OP).
- `DECISIONS.md` — apêndice ao ADR-163 (ou novo ADR-165 conforme padrão das outras correções) com:
  - AUD-009 — deferral consciente (refactor de baixo retorno).
  - AUD-010 — deferral consciente (cooperação defensiva).
  - Confirmação do trade-off "mensagem genérica em 422" (AUD-003) — defesa em profundidade anti-enumeração.
- `docs/wave8-v5-c22/audit-report.md` — apêndice ao final ("Apêndice de Status Pós-Correção"):
  - Para cada AUD-NNN: status final + commit SHA + critério objetivo. Não editar o corpo do relatório.
- `docs/wave8-v5-c22/fix-plan.md` (este) — seção "Resultado da Execução" anexada ao final com diffs entre planejado e realizado.
- `docs/wave8-v5-c22/fix-validation.md` (novo) — checklist final + auto-crítica adversarial.
- `CLAUDE.md` — sem alterações esperadas (a seção "Tela de Assinatura: fluxo, integração e RBAC" continua válida; nenhum procedimento muda).
- `docs/wave8-v5-c22/visual-guide.md` — sem alteração nesta sessão (AUD-002 DEFERRED).
- `docs/wave8-v5-c22/arqueologia.md` — sem alteração (zero divergência do trabalho original).

### 6.2 Notas de processo
- Stash `wave8-v5-c22/fixes: CSS uncommitted pre-C22 (AUD-W8C22-101 INFO) - preservar para Mario` será **mantido intocado**. Mario decide se reaplica após o merge.

---

## 7. Entregável do Gate 1

- Arquivo: `docs/wave8-v5-c22/fix-plan.md` (este documento).
- Branch: `wave8-v5-c22/fixes/plan` (criada a partir de `wave8-v5-c22/audit` HEAD `3eb4069`).
- Próximo commit: `docs(wave8-v5/c22/fixes): plano de correção pós-auditoria`.
- Aguardando: string `AUTORIZADO GATE 2 — CORREÇÃO C22 v5.0`.

**Nenhuma decisão pendente que exija nova escalação humana** — todas as decisões do plano cabem no escopo já aprovado (ADR-163/164). Se durante o Gate 2 surgir necessidade de instalar `@testing-library/react` para AUD-005 (caso a função `executar` não seja testável sem `renderHook`), **escalarei antes** com 2 opções (instalar a dep vs extrair a função pura).

**Fim do Gate 1.**

---

## 8. Resultado da Execução (Gate 2 — anexado em 2026-05-25)

> Esta seção foi anexada ao final do plano original após a conclusão
> do Gate 2 (autorização: `AUTORIZADO GATE 2 — CORREÇÃO C22 v5.0`).
> O corpo do plano acima (§0-§7) **não foi editado**.

### 8.1 Diffs entre planejado e realizado

| Item | Planejado no Gate 1 | Realizado no Gate 2 | Observação |
|---|---|---|---|
| AUD-W8C22-003 | Mudar 1 branch `else if (err.status === 422)` no hook + atualizar JSDoc | ✅ Realizado. Também ampliado para o branch "else" (403 e demais) — mesma defesa em profundidade contra `err.message` cru. | Cobertura ampliada além do mínimo. |
| AUD-W8C22-005 | 7-8 testes Vitest cobrindo 201/401/404/409/422/5xx/rede + autenticação | ✅ **15 testes** entregues (mais granular: separei 502/503; adicionei 403; separei testes de body em 3 — `motivo_reprovacao` string, null e URL do endpoint). | Cobertura efetiva ~100% da função pura. |
| AUD-W8C22-005 — refator | Avaliar `@testing-library/react` (renderHook) vs extrair função pura | ✅ **Extraída função pura** `executarTransicaoRequest` exportada do mesmo módulo. Padrão idêntico ao `identificacao-prova.ts`. Hook continua wrapper trivial. Sem instalar nenhuma dep nova. | Decisão B (Plano B preferencial) aplicada — não precisei escalar. |
| AUD-W8C22-006 | Extrair `TITULO_ID` + adicionar `data-modal-title` + atualizar `querySelector` | ✅ Realizado. 3 substituições conforme planejado. | Sem desvio. |
| AUD-W8C22-007 | `useRouter` + `onClickPrincipal` opcional em `ResultadoView` | ✅ Realizado. 4 outras views terminais inalteradas (fallback `onFechar` preservado). | Sem desvio. |
| AUD-W8C22-008 | `setStatusAplicado(data.prova.status)` + `STATUS_LABELS[statusAplicado ?? destino]` | ✅ Realizado com fallback seguro para `destino`. | Sem desvio. |
| AUD-W8C22-009 / -010 | DEFERRED com registro em DECISIONS.md | ✅ ADR-165 criado com justificativas explícitas. | Sem desvio. |
| Documentação | CHANGELOG (apêndice) + DECISIONS (apêndice ADR-163 + nota ADR-164) + audit-report (apêndice de status) + fix-validation.md novo | ✅ Realizado. **+ ADR-165 novo** (deferrals AUD-009/010 — não previsto explicitamente como "novo ADR", mas o plano §6 mencionava "deferrals AUD-009/AUD-010 em DECISIONS"; criar ADR é o padrão estabelecido no projeto e mantém o registro estruturado). | Pequeno desvio cosmético — ganhou ADR próprio em vez de apêndice. |
| Stash do CSS uncommitted (AUD-101) | Preservar com nome explícito | ✅ Stash `wave8-v5-c22/fixes: CSS uncommitted pre-C22 (AUD-W8C22-101 INFO) - preservar para Mario` criado antes da branch `wave8-v5-c22/fixes/plan`. | Sem desvio. |

### 8.2 Commits da execução

| # | SHA | Tipo | Achado | Descrição curta |
|---|---|---|---|---|
| 1 | `b4522c0` | fix | AUD-003 | hook mapeia 422 e demais para mensagem generica |
| 2 | `8aa729d` | test | AUD-005 | testes Vitest do useExecutarTransicao (+ extração função pura) |
| 3 | `1a5519b` | a11y | AUD-006 | TITULO_ID + data-modal-title no AssinaturaModal |
| 4 | `58629ec` | fix | AUD-007 | view sessao navega direto a /login |
| 5 | `2dd853e` | fix | AUD-008 | statusAplicado da resposta do backend na view sucesso |
| 6 | `6b6b172` | docs | (geral) | CHANGELOG + DECISIONS (apêndice ADR-163 + ADR-165) + audit-report (apêndice) |

(Este apêndice é o 7º commit — `docs: anexar Resultado da Execução ao fix-plan + fix-validation.md`.)

### 8.3 Métrica final
- **Testes:** 237 PASSED (era 222 + 15 novos · 0 regressão).
- **tsc / lint / build:** todos OK; build 13/13 páginas.
- **Bundle `/escanear`:** 15.9 kB / 221 kB (era 15.9 / 220 — +1 kB First Load aceitável pela adição do `useRouter`).
- **Cláusulas pétreas:** 6/6 diffs vazios (backend, contratos, matriz RBAC, pages anteriores, libs anteriores, hooks anteriores, escanear.module.css).
- **Achados resolvidos:** 5 em código + 4 DEFERRED (2 ao Mario + 2 com ADR-165) + 5 NO-OP (1 ALTO ratificado + 4 INFO) = 14/14 tratados.

### 8.4 Itens deferred + pendências para o PR `development → main`
- AUD-W8C22-002 (visual-guide screenshots) — após smoke do Mario.
- AUD-W8C22-004 (smoke E2E manual) — sessão dedicada do Mario.
- **Nova rodada de auditoria independente** em sessão separada (recomendação explícita do `fix-validation.md` §4).
- Pendências herdadas: rate limit C19 (ADR-145) + CI/CD pos-Wave 3 (ADR-156) + redeploy Railway.

**Fim do Resultado da Execução.**
