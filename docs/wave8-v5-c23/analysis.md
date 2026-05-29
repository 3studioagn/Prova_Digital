# Análise Read-Only + Proposta de Estratégia — Componente 23 (Wave 8 v5.0)

**Componente:** 23 — Responsividade Mobile da Página de Escaneamento (NOVO na v5.0)
**Wave:** 8 · Reativação e Polimento Mobile (v5.0) — 2ª e última entrega da Wave 8 e da v5.0
**Branch desta análise:** `wave8-v5-c23/analysis` (sai de `development`, sem merge)
**Branch base:** `development` (HEAD `6c89c46`)
**Data:** 2026-05-29
**Tipo:** Gate-based two-stage — **Gate 1 (read-only)**. Nenhuma linha de código de produção.
**Prioridade:** Should Have
**Status:** AGUARDANDO DECISÕES HUMANAS (11 decisões na §7). Sem autorização para o Gate 2.

> Este documento é o único artefato escrito do Gate 1. Não toca código de
> produção. Toda decisão de UX mobile, breakpoint, orientação ou ajuste em
> C10/C19/C22 não coberta aqui é escalada ao Mario (cláusula pétrea).

---

## 0. Sumário executivo

O C23 é **polimento mobile frontend-only** sobre a página `/escanear` (Componente
10 v4.0 + Componente 19) e o modal de assinatura (Componente 22 v5.0). O backend,
RLS, migrations, máquina de estados e `contrato-c12.md` permanecem **intocados** —
o C23 adiciona media queries, safe areas, ergonomia one-handed e ajustes não-invasivos
de atributos HTML.

A leitura read-only encontrou **5 divergências entre as premissas do prompt e o
estado real do código** (§5), que precisam ser reconhecidas antes de prosseguir:

1. **C20 (animações) NÃO existe no código.** O prompt o lista como dependência
   reusável (`<MotionModal>`, `<PageTransition>`, sistema de toasts). Na prática,
   o projeto usa `framer-motion` direto + `useReducedMotion` direto. (Já registrado
   pelo C22 — CHANGELOG "C20/C21 pendentes por decisão do Mario".)
2. **Playwright, axe-core, jsdom e testing-library NÃO estão instalados.** O Vitest
   roda em `environment: node` (decisão D-13 da Wave 1 v4.0), só testa lógica pura.
   O "E2E" do projeto sempre foi **smoke manual** (`smoke-validation.md`). Os critérios
   15 (cobertura ≥80%) e 16 (matriz Playwright) do prompt conflitam com essa realidade
   e com a natureza CSS-only da entrega. → **Decisão 11 é crítica.**
3. **Não há `export const viewport` no `layout.tsx`.** O Next.js aplica o default
   (`width=device-width, initial-scale=1`), mas sem `viewport-fit=cover` — pré-requisito
   da Decisão 5 (notch).
4. **O shell do dashboard JÁ é responsivo** (`<768px` vira drawer off-canvas). Isso
   reduz o risco: a `/escanear` já renderiza full-width em mobile. Mas o shell está
   **fora do escopo do C23** (não tocar) e o `mobileHeader` sticky (70px) consome o topo.
5. **A página `/escanear` NÃO usa tokens** — usa hex literais do Figma (`#eaeaea`,
   `#575757`, `#f5c518`…). Já o modal de assinatura (C22) **usa tokens** (`var(--color-…)`).
   A regra "sem hard-code" do Backlog refere-se a NÃO introduzir novos hard-codes; a
   Decisão 6 (contraste) na `/escanear` mexe num CSS já hard-coded por design (fidelidade
   ao Figma). → afeta a estratégia da Decisão 6.

**Confirmações de bloqueio (todas verdes):**
- **C22 consolidado** em `development` (linear, 17 commits `f44bc3f..6c89c46`, sem merge
  commit), **auditado** (veredito **APROVADO COM CORREÇÕES** — 0 críticos) e **corrigido**
  (AUD-003/005/006/007/008 RESOLVIDOS; AUD-001 ratificado no-op; AUD-002/004/009 são
  smoke/screenshots deferidos ao Mario). Vitest 237 passando.
- **`contrato-c12.md`** presente em `docs/wave3-v4-c11/contrato-c12.md`, coerente. C23
  apenas consome (estados → metadata visual); não modifica.
- **Infra MCP** (Supabase): projeto `rwxlpwmnkekzuurgthkr` ACTIVE_HEALTHY; `alembic_version=013`;
  `status_prova_enum=17`; `rota_enum=6`; trigger `trg_provas_rota_imutavel` presente; 12
  policies RLS; 3 helpers `app_private`. Advisors idênticos ao baseline.

**Risco crítico em destaque:** regressão visual no desktop. O CSS de `/escanear` passou
por 9 iterações visuais com o Mario + auditoria do C10. Qualquer mexida precisa preservar
desktop (≥1024px) byte-a-byte. A Decisão 1 (estratégia CSS) governa esse risco.

---

## 1. Confirmação de leitura dos artefatos (Seção 3 do prompt)

| Artefato | Caminho real | Lido |
|---|---|---|
| Contrato C12 | `docs/wave3-v4-c11/contrato-c12.md` | ✅ (consumir, não modificar) |
| C22 análise | `docs/wave8-v5-c22/analysis.md` | ✅ (decisões D1–D11) |
| C22 arqueologia | `docs/wave8-v5-c22/arqueologia.md` | ✅ (existe; UI recuperada do commit `6add246`) |
| C22 visual-guide | `docs/wave8-v5-c22/visual-guide.md` | ✅ — **é STUB** (placeholders; sem screenshots; AUD-009) |
| C22 audit-report | `docs/wave8-v5-c22/audit-report.md` | ✅ (APROVADO COM CORREÇÕES) |
| C22 fix-validation | `docs/wave8-v5-c22/fix-validation.md` | ✅ |
| CLAUDE.md | `CLAUDE.md` | ✅ |
| DECISIONS.md | `DECISIONS.md` | ✅ (ADR-163/164/165 do C22) |
| CHANGELOG.md | `CHANGELOG.md` | ✅ (C22 "INICIA A v5.0"; C20/C21 pendentes) |
| C10 docs | `docs/wave3-v4-c10/*` (analysis, contrato-c19, smoke, audit, fix) | ✅ |
| C19 docs | `docs/wave3-v4-c19/*` (analysis, smoke, audit, fix) | ✅ |
| C20 docs | `docs/wave6-v4-c20/*` | ❌ **NÃO EXISTE** (C20 não foi entregue) |
| Requisitos v5.0 | `RequisitosProvasDigitais_v5_0.docx` | ✅ (RF-028/029, RNF-008/013, US-018/019/020, RN-014) |
| Backlog v5.0 | `BACKLOG_RastreioProvasDigitais_v5_0.docx` | ✅ (Componente 23 + DoD Seção 2) |
| DAT v3.0 | `DAT_RastreioProvasDigitais_v3_0.docx` | ✅ (Seção 3 — Estratégia de Testes) |
| Código C10/C19 | `frontend/src/app/(dashboard)/escanear/{page.tsx,escanear.module.css}` | ✅ |
| Código C22 | `frontend/src/components/assinatura/*` + `frontend/src/lib/assinatura/helpers.ts` | ✅ |
| Tokens | `frontend/src/app/globals.css` | ✅ |
| Layout root | `frontend/src/app/layout.tsx` | ✅ (sem `viewport` export) |
| Shell dashboard | `frontend/src/app/(dashboard)/layout.module.css` | ✅ (responsivo `<768px`) |
| Câmera | `frontend/src/hooks/useScanner.ts` | ✅ (qrbox responsivo — AUD-W3C10-022) |
| Configs | `frontend/package.json`, `vitest.config.ts`, `next.config.js` | ✅ |

---

## 2. Validação MCP (Seção 4)

### 2.1 Supabase (read-only)
- `list_projects`: `rwxlpwmnkekzuurgthkr` — "Rastreio Provas Digitais", sa-east-1,
  **ACTIVE_HEALTHY**, Postgres 17.6.
- Estado preservado pós-C22 (consulta única read-only):
  - `alembic_version = 013` ✅
  - `status_prova_enum = 17 valores` ✅ (10 v3.0 + 7 v4.0)
  - `rota_enum = 6 valores` ✅ (4 v4.0 + 2 legacy)
  - `trg_provas_rota_imutavel` presente ✅
  - 12 policies RLS em `public` ✅
  - 3 helpers `app_private` ✅
- `get_advisors security`: 1 INFO `rls_enabled_no_policy` (alembic_version — intencional,
  ADR-025) + 1 WARN `auth_leaked_password_protection` (WONTFIX, ADR-027). **Idêntico ao baseline.**
- `get_advisors performance`: 13 INFO `unused_index` — todos pré-existentes.
- **Conclusão:** banco intocado, exatamente como documentado. C23 não altera nada disso.

### 2.2 Cloudflare
- **MCP Cloudflare NÃO está conectado** nesta sessão (não consta na lista de servidores
  MCP ativos). R2 não pôde ser validado via MCP. **Não-bloqueante:** o C23 é frontend-only
  e não toca storage. Registrado como observação. Se o Mario quiser a validação de
  saudabilidade do R2, fazer manualmente.

---

## 3. Inventário do estado atual (§5.1)

### 3.1 `/escanear` — C10 (câmera) + C19 (manual)

**`escanear/page.tsx` (820 linhas).** Client component. Estrutura:
`.pageWrapper > .wrapper > (.header + ScannerTabs + .innerCard)`. Dentro do innerCard,
`AnimatePresence` faz crossfade entre `<CameraPanel>` e `<ManualPanel>`. Pós-identificação,
chama `handleIdentificada(scan)` → se `deveAbrirAssinatura` abre `<AssinaturaModal>`, senão
`router.push('/provas/[id]')` (integração C22).
- Controles interativos: 2 tabs (Camera/Manual), CTA da câmera ("Abrir câmera"/"Cancelar"/
  "Tentar novamente"), link "Ir para digitação manual", input do código, CTA "Buscar prova",
  link "Tentar novamente", footer "Ver histórico" (desabilitado).
- `input` do C19: `font-size: 16px` (✅ evita auto-zoom iOS), `maxLength=14`, `inputMode`
  **NÃO definido** (Decisão 9), `autoCapitalize="characters"` (✅), `autoComplete="off"` (✅),
  `spellCheck={false}` (✅).

**`escanear.module.css` (803 linhas).** Layout fiel ao Figma desktop. **Já tem media queries
desktop-first** (`max-width`): `1100px`, `900px`, `540px` + bloco `prefers-reduced-motion`.
- `cameraPanel`: grid 2 colunas → 1 coluna em `≤900px`.
- `qrMockBox`: `clamp(220px, 75%, 300px)` — adapta.
- **Touch targets atuais:**
  - `.tab` height 48px desktop → **42px em `≤540px`** ❌ (< 44px — RNF-013).
  - `.cameraCta` height 50px ✅; `.manualCta` py 14px (~46px) ✅.
  - `.linkButton` padding `0.25rem 0` → altura ~24px ❌ (alvo de toque pequeno).
  - `.innerFooterLinkDisabled` — desabilitado, não conta.
- **Cores:** hex literais do Figma (não tokens). Sem `env()` (safe area). Sem tratamento
  de landscape. `.wrapper { min-height: 720px }` — pode forçar overflow em landscape baixo.

### 3.2 Modal de assinatura — C22

**`AssinaturaModal.tsx` (519 linhas)**, **`CapturaAssinatura.tsx` (113 linhas)**,
**`assinatura.module.css` (358 linhas)**, **`lib/assinatura/helpers.ts` (120 linhas — puro).**
- Modal (D1) sobre `/escanear`. 7 views (`selecionando`/`assinando`/`enviando`/`sucesso`/
  `conflito`/`sessao`/`erro`). `framer-motion` + `useReducedMotion`. `useFocusTrap`. Esc fecha.
- **Já mobile-ready** (C22 entregou o piso; C23 faz o polimento):
  - Botões `min-height: 46px` ✅; `.capturaLimpar` `min-height: 44px` ✅.
  - `@media (max-width: 460px)`: empilha `.rodape` (botões full-width) ✅.
  - `textarea` usa `--fs-base` (16px) ✅ (sem auto-zoom iOS).
  - **Usa tokens** (`var(--color-…)`, `var(--radius-…)`, `var(--fs-…)`).
  - `CapturaAssinatura` redimensiona o canvas via `ResizeObserver` (cobre rotação) ✅.
- **Gaps para o C23:**
  - Sem `env()` (safe area) — o backdrop é `position: fixed; inset: 0`; em notch, o card
    centralizado fica ok, mas botões colados no rodapé (se a Decisão 4 fixar) precisariam de
    `env(safe-area-inset-bottom)`.
  - **Landscape:** `.card { max-height: 90vh; overflow-y: auto }` + canvas `height: 200px`
    fixo → em landscape baixo (360px de altura) o canvas + botões ficam apertados (scroll
    resolve funcionalmente, mas ergonomia ruim). Candidato a canvas mais baixo / layout
    2-col em landscape (Decisão 7).
  - Touch target: botões 46px ok, mas `.capturaLimpar` (44px) está no limite.

### 3.3 Shell do dashboard (contexto — fora do escopo)
`(dashboard)/layout.module.css`: **já responsivo**. `<768px` → sidebar vira drawer
off-canvas (hamburger + backdrop + botão X), `.main` full-width, scroll do browser
(reverte o `overflow:hidden` do desktop; globals.css espelha em `<768px`). Logo: a
`/escanear` já é navegável em mobile no nível do shell. **C23 não toca o shell.** Observação:
`mobileHeader` sticky de 70px consome o topo — relevante para "terço inferior" e landscape.

### 3.4 Tokens (`globals.css`)
Tokens centralizados existem: cores (2 superfícies — escura e clara), `--color-accent #ffcb5c`,
`--color-danger #ff5959`, `--color-overlay`, radius (`--radius-sm/card/card-lg/card-xl/pill`),
tipografia (`--fs-display/title/h2/xl/lg/base/sm/xs`, todas ≥ `--fs-xs 0.8125rem`),
`--font-family`. **Não há tokens mobile** (touch-target-min, safe-area). Há media query
`<768px` que troca `overflow` do html/body para `auto`.

### 3.5 Meta viewport / layout root (`layout.tsx`)
**Não há `export const viewport` nem `<meta name="viewport">` explícito.** Next.js 14 injeta
o default (`width=device-width, initial-scale=1`). **Sem `viewport-fit=cover`** → `env(safe-area-inset-*)`
retornam 0 hoje. Decisão 5 (notch) depende de adicionar `export const viewport = { viewportFit: "cover", ... }`.

### 3.6 Câmera (`useScanner.ts`)
Wrapper `html5-qrcode`. **qrbox já responsivo** (AUD-W3C10-022): função `(vw,vh) => lado =
max(120, min(vw,vh,250)-20)`. `facingMode: "environment"`. **C23 NÃO toca este hook** (é
lógica do C10). O ajuste mobile da câmera é puramente CSS do painel ao redor.

### 3.7 Infra de testes
- `package.json`: `framer-motion ^12.38`, `html5-qrcode ^2.3.8`, `react-signature-canvas
  ^1.0.7`, `vitest ^2.1.9`. **Sem Playwright, sem @axe-core, sem jsdom, sem testing-library.**
- `vitest.config.ts`: `environment: "node"`, include só `src/**/*.test.ts` (não `.tsx`),
  `globals: false`, sem coverage v8 (D-13 — minimizar superfície instalada).
- 18 arquivos de teste, todos lógica pura (`lib/`, `hooks/`). **Baseline: 237 testes Vitest passando** (pós-C22).
- "E2E" do projeto = **smoke manual** documentado em `smoke-validation.md` por componente.

### 3.8 Bundle baseline (documentado; medir exato no Gate 2)
- `/escanear`: ~15.9 kB Size / ~220 kB First Load (pós-C22 — CLAUDE.md).
- Medição exata `next build` será feita no Gate 2 (antes/depois).

### 3.9 Comportamento mobile atual ("antes do C23" — derivado do CSS)
> Screenshots pixel-exatos exigem sessão autenticada (preview programático não tem auth —
> mesma limitação registrada em C12/C16/C22). No Gate 2, capturo via DevTools device emulator
> logado, ou o Mario captura no smoke. Notas derivadas da leitura do CSS:

- **360px portrait, câmera:** `.cameraPanel` já colapsa para 1 coluna (≤900px); `.tabs`
  com `width: min(513px,100%)` cabe; **mas `.tab` cai para 42px (<44px) em ≤540px** ❌.
  `.wrapper { min-height: 720px }` pode gerar scroll. CTA "Abrir câmera" 50px ✅, mas
  posicionado no meio (não no terço inferior) — não atende US-020.1.
- **360px landscape, câmera:** sem regras de landscape; `min-height: 720px` força scroll
  vertical grande; preview + sidebar empilhados verticalmente (1 col) ficam longos.
- **360px portrait, manual:** input 16px ✅ (sem zoom). `.manualPanel` reset de padding em
  ≤900px ✅. CTA "Buscar prova" ~46px ✅. `inputMode` ausente → teclado padrão (Decisão 9).
- **Modal assinatura mobile portrait:** já empilha botões em ≤460px ✅; canvas full-width via
  ResizeObserver ✅. Sem safe-area.
- **Modal assinatura landscape:** canvas 200px + textarea + botões podem exceder altura;
  scroll interno do `.card` resolve, mas ergonomia ruim.

---

## 4. Reuso e dependências (§5.2)

| Recurso | Estado real | Uso no C23 |
|---|---|---|
| Primitivas C20 (`<MotionModal>`, toasts) | **NÃO EXISTEM** | Não há o que reusar. Usar `framer-motion` direto (padrão atual). |
| `useReducedMotion` (framer-motion) | Em uso direto (C22, C10, C12) | Herdar; toda animação CSS nova com `@media (prefers-reduced-motion)`. |
| `useAuthorization` (Wave 1) | Em uso (`scanner` rule, 4 perfis full) | Não mexer — C23 não altera RBAC. |
| `contrato-c12.md` | Presente | Consumir labels/estados; **não modificar**. |
| Tokens `globals.css` | Centralizados | Estender com tokens mobile se aprovado (Decisão 2/4/5). |
| `framer-motion` | `^12.38` instalado | Reusar para qualquer transição de orientação (se houver). |
| Sistema de toasts | **Não existe** | Se a Decisão 10 pedir feedback de orientação, construir mínimo ou descartar. |

---

## 5. Divergências prompt × realidade (decisões implícitas que viram explícitas)

1. **C20 inexistente** → o prompt assume primitivas/toasts do C20. Proposta: usar
   `framer-motion` direto (já é o padrão pós-C22). Não bloqueia o C23.
2. **Sem Playwright/axe/jsdom** → critérios 15/16 do prompt e a Camada 3 (E2E) do DAT
   pressupõem Playwright. O projeto nunca o instalou (D-13). → **Decisão 11.**
3. **Sem `viewport` export** → pré-requisito da Decisão 5.
4. **Shell já responsivo** → bom; mas shell fora de escopo.
5. **`/escanear` usa hex, não tokens** → afeta Decisão 6 (contraste).

Essas 5 não são "decisões de design" novas além das 11 — são contexto que molda as
respostas das Decisões 1, 5, 6, 10 e 11. Registradas para transparência.

---

## 6. Os 10 cenários obrigatórios (§5.3 / §2.1)

| # | Cenário | Comportamento esperado | Critério de validação |
|---|---|---|---|
| 1 | 360px portrait — câmera ativa | Frame de captura proporcional; tabs ≥44px; CTA no terço inferior; sem overflow-x | Sem scroll horizontal; touch targets ≥44px; CTA alcançável com polegar |
| 2 | 360px landscape — câmera ativa | Frame adaptado; controles reorganizados; sem `min-height` forçando scroll absurdo | Layout não quebra; CTA acessível; preview visível |
| 3 | 360px portrait — manual | `inputMode` apropriado; input 16px (sem zoom); CTA grande; validação visível | Teclado nativo correto; sem auto-zoom; botão ≥44px |
| 4 | 360px landscape — manual | Input + botões reorganizados; sem auto-zoom ao focar | Foco sem zoom; submit acessível |
| 5 | Mobile portrait — assinatura (Motorista) | Modal abre auto; canvas dimensionado; contexto visível; botões one-handed | Canvas usável; "Confirmar" no alcance; ≥44px |
| 6 | Mobile landscape — assinatura (Vendedor reprovar + motivo) | Seletor Aprovar/Reprovar; textarea motivo; canvas; submit acessível em landscape | Sem corte; scroll mínimo; teclado não cobre submit |
| 7 | Notch — safe areas | Nenhum botão/conteúdo essencial sob notch ou home indicator | `env()` aplicado; validar iPhone X+ emulado |
| 8 | One-handed — botões alcançáveis | Botões principais no terço inferior; cabeçalho no topo | Sobreposição com zona do polegar |
| 9 | Contraste sob luz forte (simulação) | Texto/ícones legíveis sob filtro de brilho | Lighthouse/axe contrast; AA mínimo |
| 10 | Transição de orientação portrait↔landscape | Adapta sem flash; estado preservado (input não zera; câmera não reinicia à toa) | Sem layout shift; valor do input mantido |

> Cenários 5/6 dependem da existência de provas com o ator certo em produção; em smoke,
> alguns podem ser SKIP (sem motorista/clicheria reais) — mesma ressalva do C22.

---

## 7. Decisões de design propostas — ESCALAÇÃO HUMANA (11)

> Para cada uma: 2–3 opções + recomendação técnica. Aguardo resposta a TODAS antes do Gate 2.

### Decisão 1 — Estratégia CSS (CRÍTICA — afeta arquitetura e risco de regressão)
- **(i) Mobile-first refactor** dos CSS afetados (base mobile + `min-width` para desktop).
  *Backlog Nota Técnica recomenda esta.* Pró: mais limpo. **Contra: maior risco de regressão
  no desktop já auditado (9 iterações Figma do C10).**
- **(ii) Desktop-first com overrides** (`max-width`), estendendo o que já existe.
  Pró: **menor risco de regressão desktop**; coerente com o CSS atual de `/escanear` (que já
  é desktop-first com `max-width`). Contra: CSS com mais sobrescrita.
- **(iii) Híbrido com arquivos novos** (`*.mobile.module.css`). Pró: isolamento. Contra:
  duplicação parcial; CSS Modules não compõem trivialmente entre arquivos (precisa `composes`
  ou classes extras no JSX → toca o componente).
- **Recomendação técnica: (ii).** O CSS de `/escanear` JÁ é desktop-first com `max-width`
  (1100/900/540). Continuar no mesmo paradigma minimiza regressão e é cirúrgico. **Conflito a
  resolver:** o Backlog pede mobile-first; o prompt recomenda desktop-first. Preciso da sua escolha.

### Decisão 2 — Breakpoints
- Sugestão: **360 / 480 / 768 / 1024** (1024 = desktop intocado). O CSS atual usa 540/900/1100;
  poderíamos alinhar a 480/768/1024 ou manter os atuais e só adicionar 360.
- **(i)** Adotar 360/480/768/1024 (alinha ao prompt; reescreve os pontos atuais).
- **(ii)** Manter os atuais (540/900/1100) e só reforçar ≤480/≤360 (menos churn).
- **Recomendação: (ii)** se Decisão 1 = (ii) — menos reescrita; adiciono ≤480 e ≤360 onde falta.
  Se Decisão 1 = (i) mobile-first, então (i) faz mais sentido. Confirmar.

### Decisão 3 — Estratégia de orientação landscape
- **(i)** Adaptação mínima via flex/grid (reorganização).
- **(ii)** Layout repensado (2 colunas em landscape: câmera/canvas à esquerda, ações à direita).
- **(iii)** Bloqueio de landscape (forçar portrait). *Comum em apps de scanner.*
- **Recomendação: (i)** como base, com **(ii) pontual** no modal de assinatura (canvas + ações
  lado a lado em landscape). (iii) é pragmático mas o RF-029/US-020.3 exigem landscape funcional
  — então **não** bloquear. Confirmar.

### Decisão 4 — Posicionamento one-handed dos botões
- **(i)** Sticky/fixed bottom (rodapé fixo).
- **(ii)** Inline no fim do conteúdo (sem fixar).
- **(iii)** Combinação: principal sticky, secundários inline.
- **Recomendação: (iii).** O CTA principal (Abrir câmera / Buscar prova / Confirmar) ancorado
  no terço inferior; secundários (Cancelar/Ver histórico) inline. **Atenção:** sticky bottom no
  modal C22 + teclado virtual (textarea de motivo) pode cobrir o botão — mitigar com `env()` +
  scroll. Confirmar.

### Decisão 5 — Tratamento de notch
- **(i)** Só `env()` em padding (sem mexer no viewport meta) — **mas hoje `env()`=0 sem
  `viewport-fit=cover`**, então (i) puro não tem efeito.
- **(ii)** `export const viewport = { viewportFit: "cover" }` no `layout.tsx` **+** `env()` nos
  paddings — moderno e adaptativo. (Toca o layout root — mudança não-invasiva, 1 export.)
- **(iii)** Padding fixo conservador (sem `env()`).
- **Recomendação: (ii).** É a única que realmente ativa safe areas. Implica adicionar o
  `viewport` export no `layout.tsx` (root) — fora de `/escanear`/assinatura, mas necessário e
  global. **Preciso de autorização explícita para tocar `layout.tsx`** (não está na lista de
  arquivos do C23, mas é pré-requisito técnico do notch). Confirmar.

### Decisão 6 — Contraste para uso ao ar livre
- **(i)** Aprimorar contraste estático (revisar onde falha AA).
- **(ii)** Detecção de luz ambiente (Ambient Light Sensor) — **suporte ruim, descartar**.
- **(iii)** Toggle manual "modo luz forte".
- **Recomendação: (i).** Auditar contraste; ajustar só onde < AA. **Nuance:** `/escanear` usa
  hex literais do Figma (ex.: descrição `#5a5a5a` sobre branco ≈ 7:1 OK; footer `#7a7a7a` ≈ 4.4:1
  no limite). Ajustes seriam pontuais e **não** mudam identidade. Confirmar se posso escurecer
  textos auxiliares marginais (ex.: `#7a7a7a`→`#6a6a6a`) preservando o visual.

### Decisão 7 — Refinamento do modal de assinatura (C22)
- **(i)** Refactor mínimo (só media queries no CSS existente).
- **(ii)** Re-desenho parcial para mobile (canvas mais baixo em landscape, layout 2-col em landscape).
- **(iii)** Componente condicional por viewport (render mobile separado).
- **Recomendação: (i) + (ii) pontual.** O C22 já é mobile-ready (botões 46px, empilha ≤460px).
  Falta: safe-area, landscape (canvas + ações), e talvez canvas adaptativo. **(iii) está vetado
  pelo escopo** (render condicional = mudar lógica do componente). Confirmar.

### Decisão 8 — Captura por câmera em landscape (C10)
- **(i)** Viewport de captura **quadrada** (independente de orientação) — consistente p/ QR.
- **(ii)** Viewport adaptativa à orientação.
- **(iii)** Forçar portrait.
- **Recomendação: (i).** O `useScanner` já entrega qrbox quadrado responsivo (max 250); o CSS
  do painel só precisa manter o slot quadrado/`aspect-ratio: 1` em ambas orientações. Não tocar
  o hook. Confirmar.

### Decisão 9 — Digitação manual em mobile (C19) — atributos do input
- Proposta concreta (ajuste não-invasivo, só atributos HTML):
  - `inputMode="text"` (o código é alfanumérico `PRV-AAAA-MM-NNNNNN` — letras + dígitos;
    `numeric` excluiria letras; `none` esconde teclado). **Recomendado: `text`.**
  - Manter `autoComplete="off"` ✅ (já está).
  - Manter `autoCapitalize="characters"` ✅ (já está — código é maiúsculo).
  - `font-size` já é 16px ✅ (sem auto-zoom iOS).
  - Opcional: `enterKeyHint="search"` (rótulo "buscar" no teclado).
- **Recomendação:** `inputMode="text"` + `enterKeyHint="search"`. Confirmar (ou prefere `none`
  para evitar teclado e forçar uso do scanner? — não recomendado, quebra o fallback do C19).

### Decisão 10 — Feedback visual durante o scan (mobile)
- **(i)** Animação simples (frame piscando).
- **(ii)** Overlay com instruções (texto + frame).
- **(iii)** Combinação (overlay + animação leve, respeitando `prefers-reduced-motion`).
- **Recomendação: (iii).** Já existe `previewHint` ("Centralize o QR Code no quadro") + beam
  amarelo animado (`qrScanBeam`, com `prefers-reduced-motion`). No mobile, garantir que o hint
  e o beam permaneçam visíveis e proporcionais. Sem toasts (não existem). Confirmar.

### Decisão 11 — Estratégia de testes mobile (CRÍTICA — conflito com a realidade do projeto)
- **Contexto:** o prompt (critérios 15/16) e o DAT (Camada 3) pedem **Playwright** + **axe-core**
  + cobertura ≥80%. **Nada disso está instalado**; o Vitest é `environment: node` (D-13); o "E2E"
  histórico do projeto é **smoke manual** (`smoke-validation.md`). Além disso, **CSS responsivo
  não é unit-testável** por cobertura — a meta de 80% do DAT é explicitamente para **lógica de
  backend** (máquina de estados/RBAC/atraso).
- **(i)** Instalar Playwright + browsers + `@axe-core/playwright` e escrever a matriz E2E.
  Pró: atende o texto do prompt. **Contra:** nova superfície grande (~centenas de MB de browsers),
  contraria D-13, sem CI configurado para isso, e exige config nova (`playwright.config`).
- **(ii)** Seguir o precedente do projeto: **smoke manual** (`smoke-validation.md` com os 10
  cenários) + **DevTools device emulator** + **axe DevTools (extensão do browser, manual)** +
  **Vitest pure-logic** apenas para novos hooks (se Decisão de arquitetura criar `useOrientation`/
  `useViewportSize`). Pró: coerente com D-13/C10/C12/C16/C22; zero nova dependência pesada.
  Contra: não há matriz Playwright automatizada (mas nunca houve).
- **(iii)** Combinação enxuta: (ii) + Playwright **mínimo** somente se o Mario aceitar a nova
  dependência (subset: 360/768 portrait/landscape smoke).
- **Recomendação: (ii)**, e **reinterpretar os critérios 15/16** para uma entrega CSS-only:
  "cobertura ≥80%" aplica-se só a eventual lógica TS nova (hooks); "matriz E2E" = matriz de smoke
  manual + emulator. **Preciso da sua decisão explícita** — se exigir Playwright real (i/iii),
  isso é nova dependência que contraria D-13 e precisa de aprovação formal + provavelmente uma
  sessão de CI.

---

## 8. Plano de arquitetura (§5.5) — condicional às decisões

### 8.1 Estrutura de arquivos (depende da Decisão 1)
- **Se (ii) desktop-first (recomendado):** adicionar/estender media queries em
  `escanear.module.css` e `assinatura.module.css`. **Zero arquivo novo de CSS.**
- **Se (iii) híbrido:** criar `escanear.mobile.module.css` + `assinatura.mobile.module.css`
  (e tocar os componentes para aplicar as classes — sai do "não-invasivo").
- **Tokens mobile (se aprovado — Decisão 2/4/5):** adicionar em `globals.css` (ou
  `tokens-mobile.css` importado): `--touch-target-min: 44px`, `--safe-top/right/bottom/left:
  env(safe-area-inset-*)`.
- **Hooks utilitários:** provavelmente **desnecessários** — orientação/viewport tratáveis 100%
  por CSS media queries (`@media (orientation: landscape)`, `(max-width: …)`). Só criaria
  `useOrientation`/`useViewportSize` se algum comportamento de **estado React** exigir (ex.:
  reset condicional). Default: **não criar** (evita JS desnecessário; preserva estado na rotação
  via CSS puro). Confirmar no Gate 2 conforme necessidade.

### 8.2 Pontos de integração (atributos HTML não-invasivos)
- `escanear/page.tsx`: adicionar `inputMode`/`enterKeyHint` ao `<input>` do C19 (Decisão 9);
  eventuais `aria-label` que mudem entre breakpoints. **Sem tocar handlers/estado/props.**
- `layout.tsx` (root): adicionar `export const viewport` se Decisão 5 = (ii). **Requer
  autorização** (arquivo fora da lista do C23).
- `AssinaturaModal.tsx` / `CapturaAssinatura.tsx`: idealmente **zero mudança de TS**; só CSS.
  Se landscape exigir altura de canvas diferente, avaliar passar isso por CSS (preferível) e
  não por prop (que seria mudança de lógica → escalar).

### 8.3 Detecção de orientação/viewport
- **CSS-first:** `@media (orientation: landscape)` + `@media (max-width/min-width)`. Preferido
  (sem JS, sem layout shift, sem perda de estado na rotação).

---

## 9. Plano de testes (§5.6) + regressão (§5.7) — condicional à Decisão 11

### 9.1 Plano de testes (recomendação = Decisão 11.ii)
- **Smoke manual** `docs/wave8-v5-c23/smoke-validation.md`: matriz viewport × orientação ×
  cenário (360/480/768 + 1024 sanity; portrait+landscape) cobrindo os 10 cenários.
- **DevTools device emulator**: iPhone SE (360), iPhone 12/13 (notch), Pixel, iPad.
- **axe DevTools (manual)** nos viewports mobile — sem violações críticas.
- **Vitest** (`environment: node`): só se criarmos hook puro novo (improvável).
- **Lighthouse** contrast check para Decisão 6.

### 9.2 Regressão
- **Desktop ≥1024px:** screenshots antes/depois de `/escanear` (câmera + manual) e do modal —
  **zero mudança visual** (critério 18). Este é o guard-rail do risco crítico.
- C10 (scanner): escaneia em desktop e mobile.
- C19 (manual): aceita digitação em desktop e mobile; máscara/validação inalteradas.
- C22 (assinatura): funciona desktop + mobile; 7 views intactas.
- C11/C06/C08/C12/C16: `git diff` vazio nesses paths.
- Shell/Dashboard/Atalhos/Log: `git diff` vazio (exceto, se Decisão 5=ii, `layout.tsx` +1 export).
- `tsc --noEmit` exit 0; `next build` 13/13 páginas; `next lint` 0 warnings.

---

## 10. Riscos e pontos de atenção (§5.8)

| Risco | Mitigação |
|---|---|
| **Regressão visual desktop** (CSS de `/escanear` auditado em 9 iterações) | Decisão 1 = (ii) desktop-first; screenshots antes/depois ≥1024px; `git diff` revisado |
| Auto-zoom iOS (input < 16px) | input já 16px; auditar todos os inputs/textarea ≥16px |
| Câmera em landscape (orientação do feed) | Decisão 8.i (slot quadrado); não tocar `useScanner` |
| Layout shift entre orientações | CSS-first; preservar estado em React (não DOM); testar rotação |
| Notch sem `env()` | Decisão 5.ii (`viewport-fit=cover` no root) — autorização p/ tocar `layout.tsx` |
| Touch targets sobrepostos | espaçamento mínimo; `.tab` 42px→≥44px; `.linkButton` aumentar área |
| **Playwright/axe ausentes** (critérios 15/16) | Decisão 11 — reinterpretar p/ smoke manual + emulator, OU aprovar nova dep |
| Bundle size | medir `next build` antes/depois; CSS puro tende a +<1 kB |
| Tocar `/escanear` mexe em hex hard-coded | Decisão 6 — ajustes pontuais, sem mudar identidade |
| Sticky bottom + teclado virtual cobre submit (modal) | `env()` + scroll; testar com teclado aberto |
| Inconsistência cross-browser (Safari iOS `env()`, `dvh`) | testar Chrome+Safari iOS; usar `dvh`/`svh` com fallback |
| Dispositivos físicos indisponíveis | DevTools emulator + (se houver) dispositivo do Mario; documentar |
| C20 inexistente (premissa do prompt) | usar `framer-motion` direto; sem toasts |

---

## 11. Pendência — aguardando decisões

Este Gate 1 não avança para o Gate 2 sem:
1. Respostas explícitas às **11 decisões** da §7 (com destaque para as **CRÍTICAS 1 e 11**, e a
   autorização da §7 Decisão 5 para tocar `layout.tsx`).
2. A string exata: **`AUTORIZADO GATE 2 — WAVE 8 v5.0 / C23`**.

Nenhuma linha de código de produção foi escrita. Nenhum PR aberto.

---

## 12. Apêndice — Execução (Gate 2)

Autorizado pelo Mario em 2026-05-29 ("AUTORIZADO GATE 2 — WAVE 8 v5.0 / C23"), com
a restrição: **o design desktop já aprovado não muda**. Decisões consolidadas no
ADR-166.

### Decisões aplicadas
1=(ii) desktop-first overrides · 2=manter+reforçar (≤480/≤360) · 3=(i)+(ii) modal ·
4=(iii) inline lower-third (sticky só no modal landscape) · 5=(ii) viewport-fit+env ·
6=(i) mobile-scoped · 7=(i)+(ii) · 8=(i) quadrado · 9=inputMode/enterKeyHint ·
10=(iii) hint+beam · 11=(ii) smoke manual (sem Playwright).

### Arquivos tocados (5 fonte + docs)
- `frontend/src/app/globals.css` (+5 tokens mobile).
- `frontend/src/app/layout.tsx` (+`viewport` export).
- `frontend/src/app/(dashboard)/escanear/escanear.module.css` (+103 linhas, só @media).
- `frontend/src/app/(dashboard)/escanear/page.tsx` (+inputMode/enterKeyHint).
- `frontend/src/components/assinatura/assinatura.module.css` (+53 linhas, só @media).
- Docs: este `analysis.md`, `CHANGELOG.md`, `DECISIONS.md` (ADR-166), `CLAUDE.md`,
  `visual-guide.md`, `smoke-validation.md`.

### Diferenças vs o proposto no Gate 1
- **Hooks `useOrientation`/`useViewportSize`: NÃO criados** — detecção 100% via CSS
  media queries (sem JS, sem perda de estado na rotação). Confirma a previsão §8.1.
- **One-handed (Decisão 4): sticky-bottom NÃO aplicado em `/escanear`** (risco de
  sobreposição com footer/teclado, não verificável sem auth nesta sessão). CTAs
  full-width na metade inferior do fluxo; sticky usado apenas no rodapé do modal em
  landscape curto. Conforto one-handed a validar no smoke do Mario.
- **Contraste (Decisão 6): aplicado apenas no mobile** (`≤540px`) para não alterar o
  desktop congelado.

### Validação técnica
- `tsc --noEmit` 0 · `next lint` 0 · `vitest run` **237** (0 regressão) · `next build`
  **13/13**.
- `/escanear`: **16 kB / 221 kB** First Load (era ~15.9 / 220).
- `git status`: 5 fontes + `tsbuildinfo`. **Zero toque** em backend/RLS/migrations/
  enums/máquina/`contrato-c12`/shell/C06/C08/C11/C12/C16.
- Advisors MCP idênticos ao baseline; `alembic_version=013`, enums 17/6, trigger +
  12 RLS preservados.
- Aviso de build `PackFileCacheStrategy` (`provas.module.css`): pré-existente, alheio
  ao C23.

### Pendente (smoke manual do Mario — `smoke-validation.md`)
- 10 cenários em dispositivos físicos (Android + iOS) + DevTools emulator.
- Screenshots antes/depois (desktop = diff zero; mobile = novos layouts).
- axe DevTools nos viewports mobile.
- Smoke programático do `/login` NÃO executado: sem `frontend/.env` local, o dev
  server erraria por env Supabase ausente (sinal enganoso). O build cobre a
  compilação das 13 páginas; a validação de runtime fica no smoke em staging.
