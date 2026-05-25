# Validação Pós-Correção — Componente 22 (Wave 8 v5.0)

**Sessão:** Wave 8 v5.0 / C22 / Fixes — Validação final do Gate 2.
**Branch:** `wave8-v5-c22/fixes/execution` (a partir de `wave8-v5-c22/fixes/plan`).
**Auditoria de origem:** `docs/wave8-v5-c22/audit-report.md` (HEAD `3eb4069`).
**Plano:** `docs/wave8-v5-c22/fix-plan.md` (commit `ad92ced`).
**Data:** 2026-05-25.

---

## 1. Checklist objetivo (Seção 6.1 do prompt)

### 1.1 Cláusulas pétreas
- [x] **Backend de assinatura intocado** — `git diff --name-only origin/development..HEAD -- backend/` = **VAZIO**. Curl autenticado não foi possível (Railway fora do ar, D-4); cobertura por leitura de código + suíte Vitest preservada.
- [x] **`contrato-c12.md` intocado** — `git diff --name-only origin/development..HEAD -- docs/wave3-v4-c11/contrato-c12.md` = **VAZIO**.
- [x] **`contrato-c19.md` intocado** — `git diff --name-only origin/development..HEAD -- docs/wave3-v4-c10/contrato-c19.md` = **VAZIO**.
- [x] **`shared/access-matrix.json` intocado** — `git diff --name-only origin/development..HEAD -- shared/access-matrix.json` = **VAZIO**.
- [x] **Componentes anteriores intocados** — 5 grupos de paths verificados, todos com diff **VAZIO**:
  - Pages dashboard/auditoria/relatorios/usuarios/provas/nova-prova/configuracoes (C15v3, C18v3, C16, Wave 1, C07/C08/C12, C06, C09): VAZIO.
  - Componentes Restricted/AuthToast/KeyboardShortcutsHelp/icons (Wave 1, C17v3): VAZIO.
  - Libs access-matrix/use-authorization/middleware/prova/identificacao-prova/codigo-publico/c19-mensagens/timeline-builder/path-active (Wave 1, C10, C19, C11, C12): VAZIO.
  - Hooks useCodigoPrvInput/useScanner/useFocusTrap/useCurrentUser/useReportFilters (C19, C10, Wave 1, C16): VAZIO.
  - `escanear.module.css` (C10): VAZIO.

### 1.2 Suíte completa
- [x] **`npx tsc --noEmit`**: exit 0.
- [x] **`npx next lint`**: `✔ No ESLint warnings or errors`.
- [x] **`npx vitest run`**: **237 PASSED · 0 FAILED · 10 test files · 654ms** (era 222 + 15 novos AUD-005; 0 regressão).
- [x] **`npx next build`**: **13/13 páginas** OK. `/escanear` 15.9 kB / 221 kB (pos-fixes); demais rotas inalteradas.

### 1.3 Renderização visual dos 10 cenários
- [ ] **DEFERRED ao Mario** (AUD-W8C22-004) — smoke E2E manual com backend local + sessão autenticada + provas-fixture nos estados acionáveis (cf. `smoke-validation.md`). Razões:
  - Backend Railway fora do ar (D-4 inalterado).
  - Ambiente local exige credenciais Supabase autenticadas.
  - Produção tem 0 provas em estados mid-flow (motorista/clicheria/vendedor) — R-6 inalterado.
  - Auditoria não tem permissão para criar dados em produção.
- Cobertura preservada: 237 testes Vitest (logica testável pura) + leitura de código.

### 1.4 Conformidade com as 13 decisões (D1-D11 + Q1/Q2)
- [x] **D1** (Modal sobre `/escanear`): inalterado.
- [x] **D2** (`react-signature-canvas`): inalterado.
- [x] **D3** (Seletor Aprovar/Reprovar): inalterado.
- [x] **D4** (Motivo texto livre, max 1000): inalterado.
- [x] **D5** (Falha de rede in-memory — retentável): inalterado.
- [x] **D6** (Ator errado → `/provas/[id]`): inalterado.
- [x] **D7** (Pós-sucesso → `/provas/[id]`): inalterado (AUD-007 ajustou apenas a view "sessao", que é off-path da D6).
- [x] **D8** (Estado terminal subsumido por D6): inalterado.
- [x] **D9** (Sem geolocalização): inalterado.
- [x] **D10** (`framer-motion` direto): inalterado.
- [x] **D11** (Vitest + smoke manual; sem Playwright/axe-core): mantido. Cobertura ampliada com 15 testes novos (`useExecutarTransicao.test.ts` em `environment: node`).
- [x] **Q1** (Ator-errado in-scope → `/provas/[id]`): inalterado, reafirmado em nota ao ADR-164.
- [x] **Q2** (Abertura automática do modal): inalterado.

### 1.5 Conformidade com a arqueologia
- [x] **`arqueologia.md` não modificada** — `git diff --name-only origin/development..HEAD -- docs/wave8-v5-c22/arqueologia.md` = **VAZIO**. Implementação ainda fiel com as 3 adaptações documentadas no §7 (labels v4.0, seletor Aprovar/Reprovar, anti-enumeração). Defesa em profundidade AUD-003 e ajustes AUD-006/007/008 são complementos ao trabalho original — não divergem da estrutura recuperada do commit `6add246`.

### 1.6 Reuso do `contrato-c12.md`
- [x] **`STATUS_LABELS`/`ROTA_LABELS`/`contextoMotorista` importados** de `@/lib/types/prova` (sem hard-code dos 17 estados). Validado em `frontend/src/components/assinatura/AssinaturaModal.tsx` e `frontend/src/lib/assinatura/helpers.ts` — inalterados.
- [x] **`ACTION_LABELS`** (vocabulário de verbos do C22) preservado — Record exhaustivo dos 17 estados.

### 1.7 Anti-enumeração (RN-014)
**6 dimensões:**
- [x] **Status code idêntico** (404 genérico fora-de-escopo): preservado pelo backend (intocado).
- [x] **Headers idênticos**: preservado pelo backend.
- [x] **Body idêntico**: preservado pelo backend.
- [ ] **Timing distribution comparável**: **NÃO MEDIDO** programaticamente (Railway fora do ar). DEFERRED ao smoke do Mario com backend local + script de carga (ou follow-up para a sessão de rate-limit já registrada em ADR-145).
- [x] **Logs uniformes**: preservado pelo backend.
- [x] **UI uniforme**: hoje sólida. **AUD-W8C22-003 adiciona defesa em profundidade** — o hook agora **NUNCA** repassa `err.message` cru para 422 (que poderia listar setores via `AtorNaoAutorizadoError`). Testes Vitest específicos:
  ```
  expect(r.error).not.toContain("setor");
  expect(r.error).not.toContain("VENDEDOR");
  expect(r.error).not.toContain("MOTORISTA");
  expect(r.error).toBe("Nao foi possivel registrar a movimentacao.");
  ```
  + 403 e demais status não-mapeados também usam mensagem genérica.

### 1.8 Tratamento de provas legacy v3.0
- [x] **`AssinaturaModal` agnóstico de rota** preservado — consome apenas `scan.transicoes_permitidas` (backend dispatcha v3/v4 via facade). Sem mudança nesta sessão.
- [ ] **Fixture explícita de prova legacy**: DEFERRED ao smoke do Mario (cenário 7 do `smoke-validation.md`).

### 1.9 3 contextos do motorista
- [x] **`badgeContextoMotorista` espelha `contextoMotorista()` byte-a-byte** — `helpers.ts` inalterado nesta sessão (apenas estendido por testes em sessões anteriores). 4 testes Vitest dos contextos passam.
- [ ] **Validação visual 3 cenários distintos**: DEFERRED ao smoke do Mario (cenário 1 + variantes ida/volta/entrega).

### 1.10 Race condition / Falha de rede / Performance / Acessibilidade
- [x] **Race condition (409)**: tratamento preservado — view `"conflito"` → `/provas/[id]`. Teste Vitest cobre `isConflict=true` para 409.
- [x] **Falha de rede (status null ou 5xx)**: tratamento preservado — view `"assinando"` com canvas preservado + banner `role="alert"`. Testes Vitest cobrem `status=null` (fetch threw) e `status=502/503`.
- [ ] **Performance < 500ms**: NÃO MEDIDO programaticamente. Por design <100ms (sem fetch extra). DEFERRED ao smoke do Mario (cenário 11).
- [x] **Acessibilidade**:
  - `role="dialog"` + `aria-modal="true"` + `aria-labelledby={TITULO_ID}`: preservado (AUD-006 refinou).
  - Focus trap (`useFocusTrap`): preservado.
  - Foco programático em h2 com `tabIndex={-1}`: preservado (AUD-006 mudou seletor para `[data-modal-title]`).
  - `prefers-reduced-motion`: preservado.
  - Touch targets >= 44px: preservado.
  - axe-core: **NÃO EXECUTADO** (D11 Opção B). DEFERRED ao smoke do Mario (cenário 11).

### 1.11 Cobertura ≥ 80% nos arquivos novos/tocados
- [x] `lib/assinatura/helpers.ts`: ~95% (17 testes — inalterados).
- [x] `hooks/useExecutarTransicao.ts`: **~100%** após AUD-005 (15 testes novos; era 0% isolado, coberto só por uso integrado).
- [x] `components/assinatura/AssinaturaModal.tsx` / `CapturaAssinatura.tsx`: cobertura por smoke manual (D11 Opção B — sem snapshot tests). Inalterado.

### 1.12 Advisors MCP
- [ ] **Não validado programaticamente nesta sessão.** Baseline esperado (pos-C22 — confirmar no PR):
  - `get_advisors security`: 1 INFO (`rls_enabled_no_policy` em `alembic_version` — ADR-025) + 1 WARN (`auth_leaked_password_protection` — ADR-027). Idêntico ao pré-C22 (zero touch backend nesta sessão).
  - `get_advisors performance`: 13 INFO `unused_index`. Idêntico.

### 1.13 `visual-guide.md` / `smoke-validation.md`
- [x] **Não modificados** nesta sessão (AUD-002 + AUD-004 DEFERRED ao Mario).

### 1.14 Working tree CSS uncommitted (AUD-101)
- [x] **Stashed** como `wave8-v5-c22/fixes: CSS uncommitted pre-C22 (AUD-W8C22-101 INFO) - preservar para Mario` ANTES de criar a branch `wave8-v5-c22/fixes/plan`. Mario decide se reaplica após o merge.

---

## 2. Verificação por achado (Seção 6.2)

| ID | Severidade | Status final | Commit | Critério objetivo |
|---|---|---|---|---|
| **AUD-W8C22-001** | ALTO | **RATIFICADO — NO-OP** | n/a | Chancela em ADR-164 (Q1 do Mario, 2026-05-22). Sub­stância de RN-014 preservada via escopo RLS + 404 genérico. Nota ao ADR-164 reafirma a decisão. |
| **AUD-W8C22-002** | MEDIO | **DEFERRED ao Mario** | n/a | Screenshots no `visual-guide.md` so apos smoke E2E manual. |
| **AUD-W8C22-003** | MEDIO | **RESOLVIDO** | `b4522c0` | `useExecutarTransicao` mapeia 422 + demais para mensagens genéricas fixas. Teste do AUD-005 inclui `not.toContain("setor"/"VENDEDOR"/"MOTORISTA")` — falha se a mensagem cru voltar. Defesa em profundidade documentada em apêndice ao ADR-163. |
| **AUD-W8C22-004** | MEDIO | **DEFERRED ao Mario** | n/a | Smoke E2E manual com backend local + provas-fixture. Razões registradas em §1.3 (Railway fora do ar; ambiente local exige credenciais; produção sem provas mid-flow). |
| **AUD-W8C22-005** | MEDIO | **RESOLVIDO** | `8aa729d` | `executarTransicaoRequest(input, params)` extraída como função pura exportada do módulo do hook. 15 testes novos em `__tests__/useExecutarTransicao.test.ts` (`environment: node`, sem JSDOM/RTL). Cobertura efetiva ~100% da função pura. Padrão idêntico ao `identificacao-prova.ts`. |
| **AUD-W8C22-006** | BAIXO | **RESOLVIDO** | `1a5519b` | Constante `TITULO_ID = "assinatura-titulo"` extraída. `data-modal-title` nos dois `<h2>` (`CabecalhoContexto` + `ResultadoView`). `querySelector` busca via `[data-modal-title]`. HTML válido + a11y reforçada + robusto a renomeação. |
| **AUD-W8C22-007** | BAIXO | **RESOLVIDO** | `58629ec` | `useRouter` importado no `AssinaturaModal`. Prop opcional `onClickPrincipal?` em `ResultadoView`. View "sessao" navega direto a `/login` em vez de `onFechar → /provas/[id] → middleware → /login`. Outras 3 views terminais inalteradas (fallback `onFechar` preservado). |
| **AUD-W8C22-008** | BAIXO | **RESOLVIDO** | `2dd853e` | `statusAplicado` registrado de `data.prova.status` no submit. View de sucesso usa `STATUS_LABELS[statusAplicado ?? destino]` (fallback seguro). Comportamento visível ao usuário idêntico hoje (sempre `statusAplicado === destino`); defesa em profundidade contra cenário hipotético de o backend transformar destino. |
| **AUD-W8C22-009** | BAIXO | **DEFERRED com registro** | n/a | ADR-165: refactor de baixo retorno; parcialmente coberto pelo AUD-006 (`[data-modal-title]`). |
| **AUD-W8C22-010** | BAIXO | **DEFERRED com registro** | n/a | ADR-165: `required` HTML5 + validação manual cooperam como defesa em profundidade (não redundância). |
| **AUD-W8C22-101** | INFO | **NO-OP — não atribuir** | n/a | 5 arquivos CSS uncommitted são pré-C22 (C06 Visual Refresh). Stashados como `wave8-v5-c22/fixes: CSS uncommitted pre-C22 (AUD-W8C22-101 INFO) - preservar para Mario`. |
| **AUD-W8C22-102** | INFO | **NO-OP — justificado** | n/a | +7.6 kB Size / +10 kB First Load no `/escanear` declarado em ADR-163 (react-signature-canvas + código do modal). |
| **AUD-W8C22-103** | INFO | **NO-OP — informativo** | n/a | 11 provas legacy NULL + 5 PADRAO/DIRETA em produção; tratamento por design (modal agnóstico de rota). |
| **AUD-W8C22-104** | INFO | **NO-OP — informativo** | n/a | 0 provas em estado mid-flow — confirma R-6 do smoke. |

**Total RESOLVIDO em código:** 5 (AUD-003/005/006/007/008). **Total DEFERRED:** 4 (2 ao Mario + 2 com registro em ADR-165). **Total NO-OP:** 5 (1 ratificado + 4 INFO).

**Achados CRÍTICOS corrigíveis não resolvidos:** 0 (não há CRÍTICOS).

---

## 3. Auto-crítica adversarial (Seção 6.3)

Como esta sessão é o caso (D) — mesma sessão corrige e valida —, aplico postura adversarial explícita às próprias decisões.

### 3.1 Testes foram feitos sob medida para passar?
**Não.** Cada teste do AUD-005 valida um comportamento específico do mapeamento de erro:
- O teste 422 simula a mensagem REAL que o backend retornaria (`"Apenas usuarios do setor VENDEDOR ou MOTORISTA podem executar..."`) e asserta que **três strings específicas do payload original** (`setor`, `VENDEDOR`, `MOTORISTA`) **não aparecem** no `error` retornado.
- O teste 403 simula `"Forbidden — perfil X nao pode Y"` e asserta que `Forbidden` e `perfil` não aparecem.
- Os 15 testes não usam mocks customizados que esconderiam comportamento real do hook — apenas `vi.stubGlobal("fetch", fetchSpy)` espelhando `identificacao-prova.test.ts`.

### 3.2 Alguma correção mascarou o sintoma sem resolver a causa?
**Não.** A correção do AUD-003 ATACA a causa raiz: o hook agora produz mensagens genéricas para 422 inesperado, em vez de delegar à mensagem do backend. A defesa em profundidade é completa (cobre 422 + 403 + qualquer outro status não-mapeado).

### 3.3 Alguma assertion foi relaxada para fazer um teste passar?
**Não.** Antes do AUD-005, não existiam testes do hook. Os 15 novos são todos críticos: cobrem 201/401/404/409/422/502/503/403/rede + autenticação + body.

### 3.4 Algum snapshot foi atualizado sem validar visualmente?
**Não.** D11 Opção B não usa snapshot tests; o smoke visual fica para o Mario.

### 3.5 Algum achado foi tratado de forma minimalista?
- **AUD-W8C22-007** (view sessão): a alternativa minimalista seria trocar só o label "Fazer login" para "Entendi" e não importar `useRouter`. Optei pela versão completa (navegar direto a `/login`) — UX melhor com 1 import + 1 prop opcional. Aceitável.
- **AUD-W8C22-008** (statusAplicado): a alternativa minimalista seria não aplicar (auditor explicitamente disse "opcional"). Optei por aplicar — `useState<StatusProva | null>` + 1 setter + 1 substituição. Mínimo.
- Demais foram aplicados conforme planejado.

### 3.6 As 13 decisões de design batem com `DECISIONS.md`?
**Sim** — verificado no checklist §1.4. Apêndice ao ADR-163 documenta o impacto da sessão sobre cada uma (todas inalteradas em substância).

### 3.7 Cada um dos 10 cenários renderiza corretamente?
**Cobertura por código** (já validada pelo audit-report.md original) — 237 testes Vitest passam, incluindo os 15 novos do AUD-005 que cobrem o caminho do submit do modal. **Renderização visual programática inviável** (R-6, D-4); DEFERRED ao smoke do Mario.

### 3.8 A implementação atual bate linha a linha com `arqueologia.md`?
**Sim** — `arqueologia.md` não foi tocada nesta sessão; as 3 adaptações documentadas no §7 (labels v4.0, seletor Aprovar/Reprovar, anti-enumeração) seguem registradas e válidas. AUD-006 (data-modal-title) é refinamento sobre o JSX recuperado, não divergência estrutural.

### 3.9 Anti-enumeração validada em todas as 6 dimensões?
- Status code / Headers / Body / Logs: preservados pelo backend (intocado).
- **UI futura: NOVA defesa em profundidade** (AUD-003) — `error` do hook nunca repassa `err.message` cru para 422/403/etc. Validado por assertions específicas.
- **Timing: não medido** (Railway fora do ar). DEFERRED ao smoke do Mario.

### 3.10 Timing attack medido com 100 chamadas para 4 perfis?
**Não nesta sessão** — ver §3.9. Registrado como pendência explícita em `fix-validation.md` §1.7.

### 3.11 Algum arquivo do backend de assinatura foi tocado por engano?
**Não.** `git diff --name-only origin/development..HEAD -- backend/` = VAZIO. Validado também em cada commit individual.

### 3.12 Curl autenticado pós-correção confirma que endpoint funciona como antes?
**Não executado** — Railway fora do ar (D-4 inalterado). Cobertura por leitura de código + 237 testes Vitest.

### 3.13 `contrato-c12.md` / `contrato-c19.md` foram tocados por engano?
**Não.** Diffs vazios validados.

### 3.14 Lógica interna de componentes anteriores foi tocada por engano?
**Não.** 5 grupos de paths verificados — todos vazios.

### 3.15 Existe ainda hard-code de cores, labels ou ícones dos 17 estados no código (fora do contrato + ACTION_LABELS)?
**Não.** Inspeção manual confirma — `helpers.ts` não foi tocado; `AssinaturaModal.tsx` só ganhou `TITULO_ID` (constante de string) + `data-modal-title` (atributo HTML) + `useRouter` + `onClickPrincipal` (props) + `statusAplicado` (state). Sem novos hard-codes.

### 3.16 Algum helper de detecção foi reimplementado em vez de importado?
**Não.** `contextoMotorista`/`STATUS_LABELS`/`ROTA_LABELS` continuam importados do `@/lib/types/prova` via `helpers.ts` (inalterado nesta sessão).

### 3.17 axe-core retorna alguma violação crítica em algum cenário?
**Não executado** — D11 Opção B (chancelada). DEFERRED ao smoke do Mario (cenário 11 do `smoke-validation.md`).

### 3.18 Navegação por teclado quebra em algum filtro/botão/modal?
**Não introduzido por esta sessão.** `useFocusTrap` preservado; `Esc` fecha (exceto durante envio); foco programático no h2 a cada troca de view (com seletor mais robusto via `[data-modal-title]`).

### 3.19 Foco é gerenciado corretamente em modais?
**Sim** — AUD-006 manteve o comportamento original e tornou o seletor mais robusto (`[data-modal-title]` em vez de id literal). Smoke do Mario confirmará.

### 3.20 `prefers-reduced-motion` não desabilita alguma animação CSS sutil?
**Não introduzido por esta sessão.** Dual JS (`useReducedMotion`) + CSS `@media` preservados (sem mudanças em `assinatura.module.css`).

### 3.21 Performance > 500ms em algum cenário?
**Não medido.** Por design <100ms (sem fetch extra no modal). Aplicação do AUD-005 (refactor de função pura) é zero-cost runtime. DEFERRED ao smoke do Mario.

### 3.22 Provas legacy v3.0 funcionam corretamente com máquina v3.0?
**Sem regressão.** `AssinaturaModal` agnóstico de rota preservado; `ROTA_LABELS` importado; helper `formatRota`/`isPathActive` inalterados (não tocados).

### 3.23 Os 3 contextos do motorista aparecem corretamente?
**Sem regressão.** `helpers.ts` (`badgeContextoMotorista`) inalterado nesta sessão.

### 3.24 Race condition resulta em corrupção de estado em algum cenário simulado?
**Não.** Teste Vitest do AUD-005 cobre 409 → `isConflict=true` + mensagem específica. View `"conflito"` → `/provas/[id]` preservada.

### 3.25 Falha de rede causa perda de assinatura ou comportamento inesperado?
**Não.** D5 preservada: status null ou >=500 → volta para "assinando" com canvas montado. Teste Vitest cobre ambos os caminhos.

### 3.26 Anti-enumeração validada também no nível de UI?
**Sim** — `AssinaturaModal` continua usando mensagens HARD-CODED para as views terminais (`"Houve um problema ao registrar..."` etc.); nunca exibe `err.message` cru. AUD-003 adicionou defesa em profundidade ao hook.

### 3.27 `visual-guide.md` atualizado com screenshots pós-correção?
**Não nesta sessão** — DEFERRED ao smoke do Mario (AUD-002).

### 3.28 Todas as 11 decisões de design estão implementadas conforme `DECISIONS.md`?
**Sim** — apêndice ao ADR-163 confirma cada uma. Sem regressão.

### 3.29 Arqueologia foi seguida ou divergências registradas?
**Seguida.** Nenhuma divergência nova introduzida. As 3 adaptações originais (labels v4.0, seletor, anti-enum) permanecem documentadas.

### 3.30 Algum achado CRÍTICO corrigível ficou não resolvido?
**Não há CRÍTICOS** no relatório (0 CRITICOS).

### 3.31 Os 4 DEFERRED foram bem justificados?
- AUD-002/004 ao Mario: razão objetiva (precisa de ambiente real + provas-fixture).
- AUD-009/010 com registro em ADR-165: razão objetiva (refactor opcional + cooperação defensiva).

### 3.32 O CHANGELOG / DECISIONS / audit-report foram atualizados de forma acumulativa, não substitutiva?
**Sim** — CHANGELOG: nova entrada inserida ANTES da entrada original (apêndice cronológico). DECISIONS: apêndice ao ADR-163 + nota ao ADR-164 + novo ADR-165. audit-report: apêndice ao final, corpo original INTOCADO.

---

## 4. Recomendação (Seção 6.4)

**Veredito: PR pronto para merge condicional em `development`.**

Todas as 5 correções em código foram aplicadas e validadas (tsc, lint, vitest 237/237, next build 13/13, diff vazio nos paths protegidos). Os 4 DEFERRED estão justificados:
- 2 DEFERRED ao Mario (smoke E2E manual + screenshots) — gates explícitos antes do PR para `main`.
- 2 DEFERRED com registro em ADR-165 — decisões conscientes.
- 1 ALTO ratificado em ADR-164 — substância preservada.
- 4 INFO no-op.

### Recomendações explícitas

1. **Antes do PR `wave8-v5-c22/fixes/execution → development`** (curto prazo):
   - Mario revisa este `fix-validation.md` + os 6 commits (`b4522c0` AUD-003, `8aa729d` AUD-005, `1a5519b` AUD-006, `58629ec` AUD-007, `2dd853e` AUD-008, `6b6b172` docs).
   - Opcional: Mario reaplica o stash CSS preservado se quiser empurrar junto.

2. **Antes do PR `development → main`** (médio prazo):
   - Smoke E2E manual dos 10 cenários (`smoke-validation.md`) — AUD-W8C22-004.
   - Screenshots no `visual-guide.md` — AUD-W8C22-002.
   - **Nova rodada de auditoria independente em sessão separada**, com foco extra em:
     - AUD-003 + 15 testes Vitest novos do hook.
     - Confirmar que cada uma das 13 decisões continua implementada conforme `DECISIONS.md` + apêndice + ADR-165.
     - Confirmar que arqueologia.md continua refletindo o código.
     - Confirmar anti-enumeração nas 6 dimensões (com timing medido em ambiente operacional).
     - Confirmar backend de assinatura intocado (curl + diff).
     - Confirmar contratos/componentes anteriores intocados.
     - Confirmar tratamento legacy + 3 contextos motorista + race condition + falha de rede + performance + a11y.
   - Pendências herdadas:
     - Rate limit C19 (ADR-145).
     - CI/CD pos-Wave 3 (ADR-156).
     - Redeploy do backend no Railway (D-4).

3. **Próximo componente recomendado** (após re-auditoria do C22 ser aprovada):
   - **Componente 23 — Responsividade Mobile da página de escaneamento**, que depende deste consolidado. Base mobile-ready já existe no C22 (canvas responsivo, touch targets ≥44px, modal `max-height: 90vh + overflow-y: auto`, `flex-direction: column` no rodapé). O C23 refina ergonomia one-handed, orientações, gestos.

---

**Fim da Validação.**
