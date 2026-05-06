# Plano de Correção · Wave 2 v4.0 · Componente 08 · Pós-Auditoria

**Sessão:** Correção dos achados da auditoria sênior do Componente 08 (Wave 2 v4.0)
**Engenheiro:** Claude (Opus 4.7 1M) · sessão de correção dirigida por relatório
**Data do plano:** 2026-05-06
**Branch desta fase (Gate 1, somente plano):** `wave2-v4-c08/fixes/plan` — sai de `wave2-v4-c08/audit` (HEAD `d90c672`)
**Branch prevista para Gate 2:** `wave2-v4-c08/fixes/execution` (a ser criada após autorização)
**Base de referência da auditoria:** `wave2-v4-c08/audit` HEAD `d90c672` — que carrega o `docs/wave2-v4-c08/audit-report.md`
**Branch da entrega:** `wave2-v4/componente-08` (HEAD `eb9e46c`)
**Persona:** Engenheiro de Software Sênior · 15+ anos · correção dirigida por relatório de auditoria.

---

## 0. Confirmações de pré-requisitos

### 0.1 Leitura dos artefatos exigidos pelo prompt (Seção 2)

| Artefato | Caminho real | Status leitura |
|---|---|---|
| `audit-report.md` (artefato dirigente) | `docs/wave2-v4-c08/audit-report.md` | ✅ lido integralmente (776 linhas) |
| `figma-reference.png` (especificação visual) | `docs/wave2-v4-c08/figma-reference.png` | ⚠️ **PRESENTE NO WORKING TREE** (untracked); ainda **não commitada** — exatamente o objeto do achado **AUD-W2C08-001 (CRITICAL)**. Visualização possível nesta sessão. |
| `CLAUDE.md` | `CLAUDE.md` | ✅ tabela de Waves cobre o estado atual |
| `DECISIONS.md` (ADRs 125-128) | `DECISIONS.md` linhas 5063-5258 | ✅ ADRs 125, 126, 127, 128 lidos integralmente |
| `CHANGELOG.md` (seção C08 v4.0) | `CHANGELOG.md` linhas 9156-9263 | ✅ lido integralmente |
| `analysis.md` do C08 (Gate 1) | branch `wave2-v4-c08/analysis` (commit `2f721cb`) — **NÃO** existe na branch da entrega `wave2-v4/componente-08` | ✅ extraído via `git show` para `.audit-tmp/analysis.md`; lidas Seções 11.3 (preservar Figma), 12.1 (testes prometidos), 14 (riscos) |
| `schema.sql` | `docs/db/schema.sql` (`alembic_version=012`) | ✅ não tocado pelo C08 (frontend-only) |
| Código-fonte de detalhe | `frontend/src/app/(dashboard)/provas/[id]/{page.tsx,detalhe.module.css,Timeline.tsx,AdminActions.tsx,VisualizarEtiquetaModal.tsx}` + `frontend/src/lib/types/prova.ts` + `frontend/src/app/(dashboard)/layout.tsx` (helper `isPathActive`) | ✅ lidos integralmente |
| Vitest config + suite atual | `frontend/vitest.config.ts` + `frontend/src/lib/supabase/__tests__/middleware.test.ts` | ✅ confirmados (15 testes existentes do middleware Wave 1 v4.0) |
| Documentos canônicos v4.0 | `Desktop/Rastreio Prova Digital/{Requisitos,UML,Backlog,DAT}` | ✅ referenciados via `analysis.md` Seções 3 e 5 |

### 0.2 Imagem do Figma — disponibilidade

A imagem **está presente no working tree** em `docs/wave2-v4-c08/figma-reference.png` (untracked). Foi conferida visualmente nesta sessão e mostra:

- Sidebar preto com `Olá Mônica!` + busca + 5 itens primários + 2 secundários (`Configurações`, `Informações`).
- Botão `← Voltar` (pill, fundo claro) no topo.
- Card branco principal com **arte à esquerda (quadrado cinza médio)** + **bloco info à direita** dividido em:
  - `Requerimento: 123456` (pequeno cinza-escuro).
  - `Mussarela fatiada` (título grande, peso médio).
  - Divisor.
  - **Grid 3×2 estrito**: linha 1 = `Cliente` / `Rota` / `Criada em`; linha 2 = `Vendedor` / `Ciclo Atual` / `Status`. **Sem 7º campo "Codigo"**.
  - Linha de ações com **2 botões side-by-side**: `Visualizar etiqueta` (amarelo) + `Baixar etiqueta` (preto).
- Card preto separado (`Histórico de movimentações`) abaixo do card branco — espelha o que o C08 entregou.

Conclusão: a imagem está disponível para auditoria de fidelidade visual nesta sessão. O CRITICAL **AUD-W2C08-001 é trivial de resolver** (`git add` + commit). Achados de fidelidade visual (F02, F03, F04) podem ser corrigidos com referência pixel-comparada.

### 0.3 Validação MCP — Supabase (read-only, 2026-05-06)

| Verificação | Resultado | Comparação com audit |
|---|---|---|
| `alembic_version` | `012` | ✅ idem |
| Total provas | 17 | ✅ idem |
| Provas legacy (`rota IS NULL`) | 11 (65%) | ✅ idem |
| Provas com rota | 6 (1 MATRIZ v4.0, 2 PADRAO legacy, 3 DIRETA legacy) | ✅ idem |
| Distribuição status | CANCELADA=7, CRIADA=6, RECEBIDA_PELA_CLICHERIA=2, REPROVADA_PELO_VENDEDOR=2 | ✅ idem |
| Provas com `motivo_cancelamento` | 7 (todas as CANCELADAs) | ℹ️ candidatas para teste de banner |
| Provas com 2 ciclos | 1 (`66f36e8b-13ec-45a7-812d-f2111db2a9e9` — CRIADA, ciclo 2) | ✅ identificada para teste de Timeline |
| Provas REPROVADAs (testar Reiniciar) | 2 (`73be85ae`, `bd1d722d`) | ✅ identificadas |
| RLS `pol_provas_select` | usa `app_private.current_user_*()` (admin OR self_vendedor OR motorista_em_transito OR clicheria_states) | ✅ Wave 1 v4.0 (RLS 012) |
| RLS `pol_provas_insert` / `pol_provas_update` | `app_private.current_user_is_admin()` | ✅ |
| RLS `pol_movimentacoes_select` / `_insert` | preservadas | ✅ |
| Advisor security | 1 INFO `rls_enabled_no_policy` (alembic_version, ADR-025) + 1 WARN `auth_leaked_password_protection` (ADR-027) — pré-existentes | ✅ **nenhum novo após C08** |
| Advisor performance | 13 INFO `unused_index` — todos pré-existentes (volume baixo) | ✅ **nenhum novo após C08** |

Estado real **bate com o descrito pelo audit**. Esta sessão corrige sobre estado coerente.

### 0.4 Validação MCP — Cloudflare

Não invocado. C08 é **frontend-only** (já confirmado pelo audit em A.2). Diff direto:

```bash
git diff --stat development..wave2-v4-c08/audit -- backend/ scripts/
# (sem output → nenhum arquivo backend/scripts modificado)
```

Confirmação: nenhum bucket R2, worker ou KV foi tocado pelo C08. Esta sessão **não pretende tocar** Cloudflare.

### 0.5 Estado do working tree na entrada do Gate 1 — ATENÇÃO

O working tree **chega à sessão com mudanças não-commitadas** que precisam de tratamento explícito antes do Gate 2:

| Arquivo | Tipo | Conteúdo da mudança | Risco |
|---|---|---|---|
| `frontend/src/app/globals.css` | modified | `--color-card-bg #eaeaea → #ececec`; `--color-card-surface #d9d9d9 → #e4e4e4`; `--fs-base 1rem → 0.9rem`; `--card-padding clamp(2rem,4vw,4rem) → clamp(1rem,3.5vw,3.5rem)` | **CRÍTICO** — a mudança em `--color-card-surface` agrava AUD-W2C08-004 (artSlot fica AINDA mais invisível contra `.cardInner`). Precisa decisão do Mario antes do Gate 2. |
| `frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css` | modified | reduz pesos (500→400) e tamanhos (1rem→0.9rem) em `requerimentoLabel`, `title`, `metaValue`, `btnPrimary`, `btnSecondary`; troca `gap 0.75rem → 1rem`; `btnDanger` muda de fundo vermelho para transparente com borda preta | **ALTO** — `btnDanger` virou outline preto (não mais "ação destrutiva" visualmente). Deveriam ser commitadas? Ou revertidas? |
| `frontend/src/app/(dashboard)/{auditoria,configuracoes,escanear,nova-prova,provas}/*.module.css` | modified | mudanças menores de spacing/tipografia | Médio (visual cross-page) |
| `frontend/tsconfig.tsbuildinfo` | modified | cache do TS — irrelevante | Baixo |
| `docs/wave2-v4-c08/figma-reference.png` | untracked | imagem do Figma anexada por alguém antes desta sessão | **POSITIVO** — resolve AUD-W2C08-001 ao ser commitada |
| `docs/wave2-v4/audit-report-round2.md` | untracked | relatório de Round 2 do **C06** (não-C08) | Não pertence a esta sessão. Será deixado intocado. |
| `.audit-tmp/`, `.next/` | untracked | dirs de build/scratch | Ignorar. |

**Pergunta crítica para o Mario antes do Gate 2** (resposta orienta o plano):

> *Os ajustes não-commitados em `globals.css` e nos `*.module.css` foram intencionais ou são experimentos a descartar?* Se intencionais, o achado AUD-W2C08-004 fica AGRAVADO (`--color-card-surface=#e4e4e4` é ainda mais próximo de `--color-card-bg=#ececec` que de `#eaeaea`); a correção precisará introduzir token novo `--color-card-art-bg=#d9d9d9` independentemente da decisão. Se experimentos, **propomos REVERTER** essas mudanças no Gate 2 antes de aplicar as correções, voltando ao HEAD `d90c672`. Esta decisão **não bloqueia** o plano — corrigimos AUD-W2C08-004 em ambos os cenários — mas **bloqueia o início do Gate 2** porque o estado de partida dele tem que estar definido.

---

## 1. Inventário consolidado dos achados

| ID | Sev. | Categoria | Descrição resumida | Arquivo+linha (referência) | Status atual | W3? | Legacy? | Visual? |
|---|---|---|---|---|---|---|---|---|
| **AUD-W2C08-001** | CRITICAL | Documentação · Aderência | Imagem do Figma não commitada em `docs/wave2-v4-c08/figma-reference.png` (Seção 6.5 do prompt de execução exigia preservação). | `docs/wave2-v4-c08/figma-reference.png` (untracked no working tree) | pendente — imagem está no working tree mas não commitada | não | não | sim (a imagem **é** a referência) |
| **AUD-W2C08-002** | ALTO | Documentação · Rastreabilidade | `analysis.md` em branch separada (`wave2-v4-c08/analysis`); link em `CHANGELOG.md:9159` quebra na branch da entrega. | `CHANGELOG.md:9159` (link) + commit `2f721cb` em `wave2-v4-c08/analysis` | pendente | não | não | não |
| **AUD-W2C08-003** | ALTO | Cobertura de testes | Zero testes Vitest novos no Gate 2 (analysis Seção 12.1 prometeu ≥ 18). Wave 1 v4.0 Audit Round 2 (AUD-W1V4-005) estabeleceu Vitest como padrão. | `frontend/src/**/*.test.{ts,tsx}` (ausentes) | pendente | não | sim (cobre `formatRota(null)` + `null` em meta grid) | não |
| **AUD-W2C08-004** | ALTO | Manutenibilidade · Fidelidade | Token `--color-card-art-bg` ausente; `.artSlot` usa `--color-card-surface` (atualmente `#d9d9d9` em HEAD; **`#e4e4e4` em working tree** — agrava). Em loading/erro o slot fica quase invisível contra `.cardInner` (`#eaeaea`/`#ececec`). | `frontend/src/app/globals.css` (token ausente) + `frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css:290` | pendente | não | não | sim (Figma mostra slot cinza médio claramente distinto do card branco) |
| **AUD-W2C08-005** | MÉDIO | Aderência · Fidelidade | `.metaGrid` adiciona "Codigo:" como 7º item — fora do plano 3×2 declarado pelo Figma. ADR-127 menciona sem registrar como divergência consciente. | `frontend/src/app/(dashboard)/provas/[id]/page.tsx:242-249` | pendente | não | não | sim |
| **AUD-W2C08-006** | MÉDIO | Aderência · Fidelidade | Layout responsivo `≤1100px` reduz para `repeat(2, 1fr)` → 7 itens criam 4 linhas com "Codigo" sozinho na última. Quebra "blocado" pedido pelo Mario. | `frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css:614-617` | pendente | não | não | sim |
| **AUD-W2C08-007** | MÉDIO | Fidelidade | `.title` font-size colapsa para 16-19px em viewports 768-1100px (`clamp(1rem, 2.5vw, 2.5rem)`). Figma textual sugere ~36-40px. | `frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css:106` | pendente | não | não | sim |
| **AUD-W2C08-008** | MÉDIO | Documentação | Falta seção dedicada em `CLAUDE.md` sobre página de detalhe e extensão para Wave 3 (replicar padrão da seção `rota_enum`). | `CLAUDE.md` (sem seção análoga para `StatusProvaEnum`) | pendente | **sim** — destrava extensão para 14 estados na Wave 3 sem ler todo o código | não | não |
| **AUD-W2C08-009** | BAIXO | Bug menor · Consulta Mario | `.artImg` com `object-fit: cover` corta artes retangulares. | `frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css:298` | pendente | não | parcial (artes legacy podem ser retangulares) | parcial |
| **AUD-W2C08-010** | BAIXO | Manutenibilidade | `formatStatus` é wrapper trivial sem agregar valor. | `frontend/src/app/(dashboard)/provas/[id]/page.tsx:39-41` | pendente | não | não | não |
| **AUD-W2C08-011** | BAIXO | Acessibilidade · Microcopy | `formatRota(null) = "—"` é discreto mas críptico para usuário novo. | `frontend/src/app/(dashboard)/provas/[id]/page.tsx:30-37` | pendente | não | **sim** (65% das provas em produção) | parcial |
| **AUD-W2C08-012** | BAIXO | Cobertura de testes | `isPathActive` sem teste apesar de impactar destaque global do menu. | `frontend/src/app/(dashboard)/layout.tsx:90-94` | pendente — coberto pela ampliação do AUD-W2C08-003 | não | não | não |
| **AUD-W2C08-013** | BAIXO | Aderência · Smoke | Smoke E2E manual obrigatório listado em `CHANGELOG:9210-9231` mas ainda não executado. | `CHANGELOG.md:9210-9231` | pendente — depende do Mario para execução manual | não | sim (item 1) | sim (todos os itens) |
| **AUD-W2C08-014** | INFO | Distribuição em produção | 65% provas legacy, 6% v4.0 nova → tratamento "—" é norma. Nada a fazer. | (observação) | informativo | não | sim | não |
| **AUD-W2C08-015** | INFO | Aderência · Cloudflare | R2 não tocado (positivo). Nada a fazer. | (observação) | informativo | não | não | não |
| **AUD-W2C08-016** | INFO | Saúde de infra | Advisors sem novos alertas após C08 (positivo). Nada a fazer. | (observação) | informativo | não | não | não |

**Total:** 16 achados acionáveis (1 CRITICAL · 3 ALTOS · 4 MÉDIOS · 5 BAIXOS · 3 INFOs) — todos referenciados nos "Achados Consolidados" da Seção do `audit-report.md`.

Achados positivos da Fase 2 (S01, S02, S03, B01-B07, R01-R05, P01-P03, M02-M06, T02-T03, D04-D05, A01-A03, F01-F06) **estão consolidados** nos 16 acionáveis acima ou são positivos sem ação. Nenhum achado fica fora deste plano.

---

## 2. Plano detalhado por achado (ordenado por severidade)

### 2.1 CRITICAL

#### AUD-W2C08-001 — Imagem do Figma não preservada

- **Estratégia (1 commit, ~1min):** `git add docs/wave2-v4-c08/figma-reference.png` + commit dedicado. A imagem já está no working tree.
- **Arquivos tocados:** `docs/wave2-v4-c08/figma-reference.png` (NOVO — adicionar ao tracking).
- **Tipo de mudança:** novo arquivo (binário PNG).
- **Camada:** documentação.
- **Risco regressão:** zero — arquivo binário em pasta docs/, sem efeito em build/runtime.
- **Risco para Wave 3:** nenhum.
- **Fidelidade visual:** N/A (a imagem **é** a referência canônica).
- **Validação:** `git ls-tree wave2-v4-c08/fixes/execution -- docs/wave2-v4-c08/` retorna `figma-reference.png` ao lado de `audit-report.md` e `analysis.md`. `git log --diff-filter=A -- docs/wave2-v4-c08/figma-reference.png` mostra o commit. Comparação visual: a imagem renderizada no GitHub bate com o que o Mario aprovou no prompt original.
- **Dependências:** nenhuma — pode ser primeiro.
- **Mensagem do commit:** `docs(wave2-v4/c08/AUD-001): preservar figma-reference.png como referencia visual canonica`

#### Sub-pergunta operacional

> **Antes do Gate 2:** confirmar que o PNG no working tree é mesmo o que o Mario anexou ao prompt original (vs. um substituto). A inspeção visual nesta sessão mostra layout coerente com a descrição textual da `analysis.md` Seção 5; aceito como verdadeiro.

---

### 2.2 ALTOS

#### AUD-W2C08-002 — `analysis.md` em branch separada; link CHANGELOG quebra

- **Estratégia (1 commit, ~3min):** cherry-pick do commit `2f721cb` (que contém o `analysis.md`) sobre a branch de execução. Alternativa B: copiar o arquivo via `git show wave2-v4-c08/analysis:docs/wave2-v4-c08/analysis.md > docs/wave2-v4-c08/analysis.md` + commit. **Preferência:** cherry-pick para preservar autoria + mensagem do commit original do Gate 1.
- **Arquivos tocados:** `docs/wave2-v4-c08/analysis.md` (NOVO via cherry-pick).
- **Tipo de mudança:** novo arquivo.
- **Camada:** documentação.
- **Risco regressão:** zero — só doc.
- **Risco para Wave 3:** nenhum.
- **Fidelidade visual:** N/A.
- **Validação:** `git ls-files docs/wave2-v4-c08/analysis.md` retorna `analysis.md`. Em viewer markdown, o link `docs/wave2-v4-c08/analysis.md` em `CHANGELOG.md:9159` resolve corretamente. Conferir hash: `git hash-object docs/wave2-v4-c08/analysis.md` deve dar `bdba764949f74840ba2c7e74fad5f8b13c1e849f` (mesmo blob da branch `wave2-v4-c08/analysis`).
- **Dependências:** nenhuma — pode ser segundo (após 001).
- **Mensagem do commit:** preserva a do `2f721cb` se cherry-pick limpo (`docs(wave2-v4/c08): análise read-only pré-execução`); senão `docs(wave2-v4/c08/AUD-002): incorporar analysis.md na branch de fixes`.

#### AUD-W2C08-003 — Zero testes Vitest novos (≥ 18 prometidos)

- **Estratégia (estimativa ~45min):** adicionar arquivos `*.test.ts` cobrindo:
  - `frontend/src/lib/types/__tests__/prova.test.ts` — testes de `formatRota`-equivalente (encapsular a função fora do component): 7 cenários × `ROTA_LABELS[v]` + null + edge invalid. **Importante:** `formatRota` está hoje INLINE em `page.tsx:30-37` (não é exportada). Para testar sem renderizar componente, **pequeno refactor**: extrair para `frontend/src/lib/types/prova.ts` como `formatRota(rota: Rota | null): string`. Ajustar import em `page.tsx`. Esse refactor é seguro (1 chamador), barato (1 linha movida) e atende à intenção do AUD-W2C08-003 sem expandir Framer Motion ou tocar lógica de UI.
  - `frontend/src/app/(dashboard)/__tests__/layout.test.ts` — testes de `isPathActive(pathname, href)` cobrindo 5 casos: exact, prefix, prefix-with-trailing-slash, false-positive `/provas-other`, undefined href. **Mesma técnica de extração**: extrair `isPathActive` para utilitário em `frontend/src/lib/path-active.ts` ou exportá-lo (de `(dashboard)/layout.tsx` é difícil porque é componente; mover para `lib/`).
  - `frontend/src/app/(dashboard)/provas/[id]/__tests__/detalhe-page.test.tsx` — render smoke da página: 3 testes (full / `rota=null` / `motivo_cancelamento` set). Exige `@testing-library/react` + `jsdom` no Vitest. **Decisão de Gate 2**: para minimizar superfície instalada (alinhado com nota de `vitest.config.ts:11-13`), pode-se diferir o smoke render para futura sessão e cobrir mínimo: 7 (`formatRota`) + 5 (`isPathActive`) = **12 testes** (ainda bem abaixo dos 18 prometidos pelo analysis Seção 12.1, mas dentro do espírito de "≥ 1 teste por unidade não-trivial"). Análise alternativa: adicionar `@testing-library/react` + `jsdom` para chegar aos 15+ smoke tests também é aceitável — decisão depende de quanto o Mario quer expandir devDependencies. **Proposta default:** 7 + 5 = 12 testes sem novas devDependencies; smoke render de página fica como deferred com justificativa em DECISIONS. Ver §4 abaixo para autorização.
- **Arquivos tocados:**
  - `frontend/src/lib/types/prova.ts` (modificado — adiciona `export function formatRota`).
  - `frontend/src/lib/types/__tests__/prova.test.ts` (NOVO).
  - `frontend/src/lib/path-active.ts` (NOVO — extração de `isPathActive`).
  - `frontend/src/lib/__tests__/path-active.test.ts` (NOVO).
  - `frontend/src/app/(dashboard)/provas/[id]/page.tsx` (modificado — usa `formatRota` importado).
  - `frontend/src/app/(dashboard)/layout.tsx` (modificado — usa `isPathActive` importado).
  - `frontend/vitest.config.ts` (já cobre `src/**/__tests__/*.test.ts`; sem mudança).
- **Tipo:** modificação (`prova.ts`, `page.tsx`, `layout.tsx`) + 4 novos arquivos.
- **Camada:** frontend (testes + utilitário).
- **Risco regressão:** baixo — extração é refactor mecânico de função pura. `npx tsc --noEmit` valida o tipo. `npx next build` confirma o bundle. Nenhuma mudança de comportamento esperada.
- **Risco para Wave 3:** **positivo** — a extração de `formatRota` para `lib/types/prova.ts` consolida a única função pura de formatação de rota num lugar testável e expansível (Wave 7 backfill terá teste de regressão pronto).
- **Fidelidade visual:** N/A.
- **Validação:** `npx vitest run` (ou pacote equivalente) lista 12 + 15 (existentes) = 27 testes passando. `npx tsc --noEmit` exit 0. `npx next build` 13/13 páginas (sem regressão de bundle).
- **Dependências:** depende de NENHUM achado anterior; mas se rodar no commit imediato após 001+002, pode ser considerado o terceiro acionável após CRITICAL/análise.
- **Mensagem dos commits:**
  1. `refactor(wave2-v4/c08/AUD-003): extrair formatRota e isPathActive para lib/ testavel` (refactor não-quebrado).
  2. `test(wave2-v4/c08/AUD-003): vitest formatRota (7) + isPathActive (5)` (testes).

#### AUD-W2C08-004 — Token `--color-card-art-bg` ausente; `.artSlot` invisível

- **Estratégia (1 commit, ~5min):** criar `--color-card-art-bg: #d9d9d9` em `globals.css` (`:root`, ao lado dos outros tokens `--color-card-*`). Atualizar `detalhe.module.css:290` para `background: var(--color-card-art-bg)` (sem fallback, já que o token vai sempre estar definido). Documentar em DECISIONS.md o porquê do token semântico dedicado. **Importante:** considerar o estado de `globals.css` no working tree — se o Mario decidir manter as alterações working tree (`--color-card-bg=#ececec`), o token novo `--color-card-art-bg=#d9d9d9` continua válido (delta `#ececec` vs `#d9d9d9` ≈ 19 RGB units → visível). Se decidir reverter, idem (delta `#eaeaea` vs `#d9d9d9` ≈ 17 RGB units → visível). Em ambos os caminhos a fix funciona.
- **Arquivos tocados:**
  - `frontend/src/app/globals.css` (modificado — adiciona token).
  - `frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css:290` (modificado — usa novo token, remove fallback).
  - `DECISIONS.md` (apêndice ADR-129 documentando o token).
- **Tipo:** modificação.
- **Camada:** frontend (CSS tokens).
- **Risco regressão:** baixíssimo — `--color-card-surface` continua existindo e usado em `qrPayloadInput` etc.; o novo token é só para `.artSlot`. Sem efeito cross-page.
- **Risco para Wave 3:** nenhum.
- **Fidelidade visual:** alta — corrige o slot do Figma (cinza médio claramente distinto do card branco).
- **Validação:** smoke visual com prova legacy (`66f36e8b` ou similar onde a arte pode não carregar do R2) — confirmar que o quadrado cinza é visível no estado loading e error. Comparação contra figma-reference.png pixel-a-pixel no slot da arte.
- **Dependências:** independente.
- **Mensagem do commit:** `style(wave2-v4/c08/AUD-004): novo token --color-card-art-bg (#d9d9d9) para artSlot visivel`

---

### 2.3 MÉDIOS

#### AUD-W2C08-005 — `Codigo:` 7º item fora do grid 3×2 do Figma

- **Estratégia (1 commit, ~10min):** seguir a recomendação **(a)** do auditor — **remover o campo "Codigo" do `metaGrid`** e exibir o `codigo_publico` em **subtítulo do header**, ao lado de `Requerimento: NNN`. Forma proposta: `Requerimento: 123 · PRV-2026-05-XYZAB`. Razão: a imagem do Figma só tem 6 campos no grid; `Requerimento` no header já segue o padrão de "identificador secundário"; juntar `codigo_publico` ao mesmo bloco é semântica análoga e não invade o grid. Resolve **junto** AUD-W2C08-006.
- **Arquivos tocados:**
  - `frontend/src/app/(dashboard)/provas/[id]/page.tsx` (modificado — remove o 7º `metaItem`, adiciona o `codigo_publico` no `requerimentoLabel`).
  - `frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css` (modificado — pode precisar `.requerimentoLabel` ganhar `font-feature` ou um span mono pequeno; valido pixel-a-pixel contra o Figma).
  - `DECISIONS.md` (atualizar ADR-127 — apêndice "Pos-auditoria: Codigo no header em vez do grid"; ou novo ADR-130 dedicado).
- **Tipo:** modificação.
- **Camada:** frontend.
- **Risco regressão:** baixo — só layout do header. `codigo_publico` continua exibido (não some); apenas muda de posição.
- **Risco para Wave 3:** nenhum.
- **Fidelidade visual:** alta — alinhe direto com o Figma (grid 3×2 estrito).
- **Validação:** comparação visual contra figma-reference.png (header + grid). Smoke render: ambas as variações `motivo_cancelamento set/unset`.
- **Dependências:** **bloqueia AUD-W2C08-006** (resolve juntos).
- **Mensagem do commit:** `style(wave2-v4/c08/AUD-005): codigo_publico no header (subtitulo) em vez do grid`

#### AUD-W2C08-006 — Layout responsivo ≤1100px deixa "Codigo" sozinho

- **Estratégia:** **resolvido por AUD-W2C08-005**. Sem o 7º item, o grid em `repeat(2, 1fr)` produz 6 itens em 3 linhas balanceadas (Cliente/Rota, Criada em/Vendedor, Ciclo Atual/Status) — sem assimetria.
- **Validação:** redimensionar viewport para 768-1100px e confirmar grid 2×3 limpo, sem células órfãs.
- **Mensagem do commit (se separado):** `style(wave2-v4/c08/AUD-006): metaGrid responsivo simetrico apos remover Codigo`. **Default:** consolidado no commit do AUD-005.

#### AUD-W2C08-007 — `.title` font-size colapsa para 16-19px em viewports 768-1100px

- **Estratégia (1 commit, ~2min):** trocar `clamp(1rem, 2.5vw, 2.5rem)` para `clamp(1.5rem, 2.5vw, 2.5rem)` em `detalhe.module.css:106`. Mínimo passa para 24px (em 768px viewport, o `2.5vw=19.2px` ainda é < `1.5rem=24px` então o `clamp` toma o `1.5rem`). Em 1100px, `2.5vw=27.5px > 1.5rem`, então segue o vw → ~27px. Em desktop largo (>1.5*40/2.5 = 100vh suficiente), trava em 40px (2.5rem). Hierarquia preservada vs `.metaValue=16px`.
- **Arquivos tocados:** `frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css:106`.
- **Tipo:** modificação.
- **Camada:** frontend.
- **Risco regressão:** baixíssimo — só CSS.
- **Risco para Wave 3:** nenhum.
- **Fidelidade visual:** alta — alinha com o tamanho da imagem do Figma (~36-40px no desktop).
- **Validação:** redimensionar viewport entre 768px e 1440px e confirmar título sempre maior que `metaValue`. Comparação contra figma-reference.png.
- **Dependências:** independente.
- **Mensagem do commit:** `style(wave2-v4/c08/AUD-007): title clamp(1.5rem, 2.5vw, 2.5rem) — minimo 24px em mobile-tablet`

#### AUD-W2C08-008 — Falta seção em `CLAUDE.md` sobre página de detalhe + extensão Wave 3

- **Estratégia (1 commit, ~20min):** adicionar seção operacional em `CLAUDE.md` (após a seção sobre `rota_enum`, antes da divisória final), espelhando o padrão da existente. Conteúdo:
  - Estrutura de arquivos da `/provas/[id]` (page.tsx + detalhe.module.css + Timeline.tsx + AdminActions.tsx + VisualizarEtiquetaModal.tsx + hooks correlatos).
  - Camadas para sincronizar ao adicionar valor a `StatusProvaEnum`: (i) Python `StatusProvaEnum` em `backend/app/db/models.py`; (ii) PostgreSQL via Alembic (`ALTER TYPE status_prova_enum ADD VALUE`); (iii) `state_machine.TRANSICOES` + `ATORES_POR_TRANSICAO`; (iv) TypeScript `StatusProva` + `STATUS_LABELS` + `STATUS_LABELS_SHORT` + `STATUS_OPTIONS`.
  - Quando expandir as 4 flags em `Timeline.tsx` (`isReprovacao`, `isCancelamento`, `isTerminal`, `isRoteamento`): se o novo estado precisar de cor/badge especial (ex.: `LAMINANDO_*` no Wave 3 v4.0).
  - Como o `formatRota`/`isPathActive` foram refatorados para `lib/` (depende do AUD-W2C08-003).
  - Onde adicionar testes Vitest (mesma estrutura `__tests__/*.test.ts`).
- **Arquivos tocados:** `CLAUDE.md` (apêndice).
- **Tipo:** modificação documental.
- **Camada:** documentação.
- **Risco regressão:** zero.
- **Risco para Wave 3:** **positivo** — destrava a expansão para 14 estados sem ler todo o código fonte.
- **Fidelidade visual:** N/A.
- **Validação:** revisão humana (Mario) — seção é didática, deve ser clara e rastreável.
- **Dependências:** se AUD-W2C08-003 mudar local de `formatRota`/`isPathActive`, atualizar a seção depois desse achado.
- **Mensagem do commit:** `docs(wave2-v4/c08/AUD-008): CLAUDE.md ganha secao "Pagina de detalhe: estrutura e extensao para Wave 3"`

---

### 2.4 BAIXOS

#### AUD-W2C08-009 — `.artImg` `object-fit: cover` corta artes retangulares

- **Estratégia (1 commit, ~2min, condicional):** **NÃO ALTERAR sem confirmação do Mario.** O auditor recomenda *consultar*. Se Mario disser `cover` é intencional (estética + padronização do quadrado), classificar como WONTFIX em DECISIONS.md. Se disser para trocar para `contain` (preserva proporção, deixa "letterbox" cinza), aplicar mudança de 1 linha.
- **Arquivos tocados (caminho A — confirmação):** `DECISIONS.md` (registrar decisão WONTFIX ou alteração).
- **Arquivos tocados (caminho B — alterar):** `frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css:298` + DECISIONS.
- **Tipo:** modificação ou doc.
- **Camada:** frontend (CSS) ou doc.
- **Risco regressão:** baixíssimo (CSS de 1 linha).
- **Risco para Wave 3:** nenhum.
- **Fidelidade visual:** **dependente** — Figma textual não decide entre `cover` e `contain` (a imagem do Figma mostra placeholder cinza, não imagem real).
- **Validação:** comparar render com prova real retangular (e.g., 8.5×11) em ambas as opções. Decidir com Mario.
- **Dependências:** depende de input humano.
- **Mensagem do commit (B):** `style(wave2-v4/c08/AUD-009): object-fit contain para preservar proporcao de artes retangulares`. **Padrão proposto:** caminho A (WONTFIX com nota), porque trocar pode introduzir letterbox feio em arte quadrada (~50% das artes em produção?). Mario decide.

#### AUD-W2C08-010 — `formatStatus` é wrapper trivial sem agregar valor

- **Estratégia (1 commit, ~3min):** remover a função `formatStatus` de `page.tsx:39-41` e substituir o uso em `page.tsx:239` por `STATUS_LABELS[prova.status]` direto. **Importante:** preservar o import de `STATUS_LABELS` que já existe no header.
- **Arquivos tocados:** `frontend/src/app/(dashboard)/provas/[id]/page.tsx`.
- **Tipo:** modificação (refactor minor).
- **Camada:** frontend.
- **Risco regressão:** baixíssimo — função pura sendo substituída pela expressão equivalente.
- **Risco para Wave 3:** nenhum.
- **Fidelidade visual:** N/A (visual idêntico).
- **Validação:** `npx tsc --noEmit` exit 0. Smoke render mostra mesma string.
- **Dependências:** independente.
- **Mensagem do commit:** `refactor(wave2-v4/c08/AUD-010): remover wrapper trivial formatStatus`

#### AUD-W2C08-011 — `formatRota(null) = "—"` críptico para usuário novo

- **Estratégia (1 commit, ~3min):** adicionar `<span title="Prova legacy v3.0 — rota será definida pelo backfill da Wave 7">—</span>` em vez de literal `"—"`. Native HTML `title` attribute (sem JS). Decisão de design: tooltip no en-dash. Alternativa: passar opacidade reduzida para indicar "menor importância" (visual hint sem texto). **Default proposto:** apenas o `title` HTML — minimal, acessível, e suficiente.
- **Arquivos tocados:** `frontend/src/app/(dashboard)/provas/[id]/page.tsx:30-37` (alterar return de `formatRota`) — ou, se mantida em `lib/types/prova.ts` (após AUD-W2C08-003), modificar lá. Voltar `formatRota` para retornar JSX (`React.ReactNode`) é overkill; em vez disso, manter `formatRota` como pure string e fazer o JSX `<span title=...>—</span>` inline em `page.tsx:215`. Isso preserva testabilidade pura (Vitest sem DOM).
- **Tipo:** modificação.
- **Camada:** frontend.
- **Risco regressão:** baixíssimo — só renderização condicional.
- **Risco para Wave 3:** **positivo** — torna mais explícito que o em-dash representa "ainda não backfilled".
- **Fidelidade visual:** baixa — Figma usa "Rota direta" (preenchida), não tem caso null. Mas o em-dash em si é convenção.
- **Validação:** smoke render com prova legacy `rota=null` mostra em-dash; hover com mouse mostra tooltip nativo. Vitest da `formatRota(null)` continua passando (a função pura ainda retorna `"—"`).
- **Dependências:** se rodar depois de AUD-W2C08-003 (que possivelmente extrai `formatRota` para `lib/`), tocar lá. Senão, tocar em `page.tsx`.
- **Mensagem do commit:** `a11y(wave2-v4/c08/AUD-011): tooltip explicativo no em-dash de prova legacy`

#### AUD-W2C08-012 — `isPathActive` sem teste

- **Estratégia:** **resolvido por AUD-W2C08-003** (testes Vitest cobrem 5 cenários). Sem commit dedicado.
- **Validação:** suite Vitest mostra 5 testes específicos de `isPathActive`.
- **Mensagem (se separado):** `test(wave2-v4/c08/AUD-012): consolidado com AUD-003`.

#### AUD-W2C08-013 — Smoke E2E manual obrigatório listado mas não executado

- **Estratégia:** **executar antes do PR final**. Criar `docs/wave2-v4-c08/smoke-validation.md` com checklist de 15 itens replicados de `CHANGELOG.md:9210-9231`, e marcar pass/fail/observação para cada um. Mario percorre os perfis. Sessão de correção pode rodar **somente** os itens que não dependem de auth de produção (e.g., ler RLS via MCP, simular perfis no DB) — mas autenticação real precisa do Mario.
- **Arquivos tocados:** `docs/wave2-v4-c08/smoke-validation.md` (NOVO).
- **Tipo:** documentação.
- **Camada:** doc + execução manual.
- **Risco regressão:** zero.
- **Risco para Wave 3:** nenhum.
- **Fidelidade visual:** **alta** (todo o checklist exercita visualmente o detalhe redesenhado).
- **Validação:** os 15 itens marcados PASS antes do PR final.
- **Dependências:** depende de Mario (execução real). O **template** do smoke-validation.md pode ser criado já no Gate 2.
- **Mensagem do commit (template):** `docs(wave2-v4/c08/AUD-013): template smoke-validation.md (15 itens) para execucao Mario`

---

### 2.5 INFOs

#### AUD-W2C08-014 — Distribuição em produção (65% legacy)

- **Estratégia:** **registrar como follow-up em DECISIONS.md** ("Pos-auditoria — observação sobre distribuição"). Sem ação operacional. A informação reforça que o tratamento `"—"` é norma, não exceção.
- **Arquivos tocados:** `DECISIONS.md` (apêndice).
- **Mensagem do commit:** consolidar com outros `docs(...)`.

#### AUD-W2C08-015 — Cloudflare R2 não tocado (positivo)

- **Estratégia:** **registrar em DECISIONS.md** como confirmação. Sem ação operacional.

#### AUD-W2C08-016 — Advisors sem novos alertas (positivo)

- **Estratégia:** **registrar em DECISIONS.md** como saúde de infra preservada. Sem ação operacional.

---

## 3. Ordem de execução (topológica)

Critério rígido: severidade DESC → afeta-Wave-3 → afeta-legacy → segurança → dependências.

| # | ID | Sev. | Por que nessa posição |
|---|---|---|---|
| 1 | **AUD-W2C08-001** | CRITICAL | Bloqueante de tudo no audit; correção trivial; libera comparação visual contra Figma para os achados de fidelidade. |
| 2 | **AUD-W2C08-002** | ALTO | Restaura rastreabilidade (analysis.md acessível na branch da entrega) — necessário para o smoke E2E e para que validação posterior tenha referência canônica disponível. |
| 3 | **AUD-W2C08-003** | ALTO | Refactor `formatRota`/`isPathActive` para `lib/` + 12 testes Vitest. Vem antes dos achados que tocam essas mesmas funções (AUD-W2C08-008, 011, 012) para evitar conflito. |
| 4 | **AUD-W2C08-004** | ALTO | Token `--color-card-art-bg`. Independente; corrige fidelidade visual base. |
| 5 | **AUD-W2C08-005** + **006** (consolidados) | MÉDIO | Remove "Codigo" do grid; resolve AUD-006 automaticamente. Vem antes do AUD-007 porque ambos tocam `detalhe.module.css` e este consolidado é maior. |
| 6 | **AUD-W2C08-007** | MÉDIO | `.title` clamp ajustado. Independente. |
| 7 | **AUD-W2C08-008** | MÉDIO | Seção "Página de detalhe" em CLAUDE.md. Reflete localizações finais de `formatRota`/`isPathActive` — deve vir depois de AUD-003. |
| 8 | **AUD-W2C08-010** | BAIXO | Remoção de `formatStatus`. Independente. |
| 9 | **AUD-W2C08-011** | BAIXO | Tooltip no em-dash. Toca código que pode ter sido movido por AUD-003. |
| 10 | **AUD-W2C08-009** | BAIXO | `object-fit` — **depende de decisão Mario antes do Gate 2**. Se WONTFIX, registra em DECISIONS; se mudar, commit dedicado. |
| 11 | **AUD-W2C08-012** | BAIXO | Já resolvido por AUD-003. Status update apenas. |
| 12 | **AUD-W2C08-013** | BAIXO | Template `smoke-validation.md`; execução real depende de Mario (após PR ou antes do merge). |
| 13 | **AUD-W2C08-014, 015, 016** | INFO | Apêndices em DECISIONS.md. Consolidados em 1 commit `docs(...)`. |
| 14 | (final) | — | Atualizar `audit-report.md` com apêndice "Status por achado" + atualizar `fix-plan.md` com seção "Resultado da Execução" + criar `fix-validation.md`. |

**Total estimado de commits no Gate 2:** ~12 (alguns achados consolidados em commits únicos).

---

## 4. Análise de risco agregado

### 4.1 Achados com risco ALTO de regressão

Nenhum. Todos os achados são frontend-only ou doc-only. Sem migrations Alembic ou RLS novas.

### 4.2 Achados com risco para a Wave 3

- **AUD-W2C08-008** (positivo) — destrava a Wave 3 ao documentar como adicionar valor a `StatusProvaEnum`.
- **AUD-W2C08-003** (positivo) — extração de `formatRota` consolida a função pura num lugar testável (Wave 7 backfill terá teste de regressão pronto).

Mitigação: validação manual de extensibilidade da Timeline — adicionar **valor temporário** a `StatusProva` (e.g., `"_TEST_LAMINANDO_MATRIZ"`) + entrada em `STATUS_LABELS` + commitar branch local. Confirmar render sem reescrever `Timeline.tsx`. **Reverter antes de commitar.**

### 4.3 Achados que afetam provas legacy (`rota IS NULL`)

- **AUD-W2C08-003** (positivo) — testes incluem cenário `formatRota(null)`.
- **AUD-W2C08-011** — torna explícito o significado do em-dash para legacy.
- **AUD-W2C08-013** — item 1 do smoke valida visualmente prova legacy.

Mitigação: smoke check explícito após cada um — abrir `/provas/<id>` de prova com `rota IS NULL` (e.g., `66f36e8b`) e validar:
1. Em-dash renderizado.
2. Tooltip presente (após AUD-011).
3. Sem erros no console.
4. Métagrid 3×2 limpo (após AUD-005+006).

### 4.4 Achados de fidelidade visual contra Figma

- **AUD-W2C08-001** (CRITICAL) — sem ela, fidelidade não é auditável.
- **AUD-W2C08-004** — `.artSlot` cinza visível.
- **AUD-W2C08-005** + **006** — grid 3×2 estrito (sem 7º Codigo).
- **AUD-W2C08-007** — `.title` mínimo 24px.
- **AUD-W2C08-013** — smoke E2E manual cobre todos os elementos visuais.

Mitigação: cada um dos 4 achados (4, 5, 7) ganha screenshot pós-correção anexado ao commit ou ao `fix-plan.md` na seção "Resultado da Execução". Comparação elemento-por-elemento contra `figma-reference.png`.

### 4.5 Achados que tocam código de Waves anteriores

- **AUD-W2C08-003** — extrai `isPathActive` de `(dashboard)/layout.tsx` (Wave 1 v4.0). Refactor de 5 linhas para mover função pura para `lib/`. Sem mudança de comportamento. Cobre Wave 1 v4.0 indiretamente — adiciona teste que **não existia** na Wave 1 v4.0 / Audit Round 2 (a suite middleware testou só `getRuleForPath`, não `isPathActive`). **Risco para Wave 1 v4.0:** baixo (só extração).
- Demais: tocam exclusivamente código do C08 v4.0.

Mitigação: rodar suite Vitest atual (15 testes do middleware) após cada commit que toque `layout.tsx`, garantindo zero regressão.

### 4.6 Achados que exigem nova migration Alembic ou RLS

**NENHUM.** Confirmado via análise dos 16 achados. Esta sessão não toca:
- `backend/migrations/versions/*.py`
- `backend/migrations/rls/*.sql`
- Schema do banco em produção

`alembic_version=012` permanece. Cloudflare permanece intocado.

### 4.7 Achados de acessibilidade

- **AUD-W2C08-011** — tooltip nativo HTML `title`.

Validação: smoke manual com hover do mouse + screen reader (NVDA/VoiceOver). Critério: o atributo `title` é lido. Se Mario quiser ARIA mais elaborada (`aria-describedby`), expandir em sessão futura.

### 4.8 Achados de performance

- Nenhum entre os 16 acionáveis. AUD-W2C08-014/015/016 confirmam saúde mantida.

### 4.9 Bloqueios potenciais para o Gate 2

| Bloqueio | Causa | Resolução |
|---|---|---|
| **B1** — Estado do working tree na entrada do Gate 2 | CSS modificado não-commitado (ver §0.5) — agrava AUD-W2C08-004, muda `.btnDanger` para outline preto, reduz fontes. | Pergunta para Mario (§0.5). Se intencionais, manter; se experimentos, reverter via `git checkout HEAD -- frontend/src/app/globals.css frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css …`. |
| **B2** — Decisão sobre `object-fit` (AUD-W2C08-009) | Auditor recomenda consultar Mario. | Pergunta para Mario antes do Gate 2. Default proposto: WONTFIX. |
| **B3** — Default sobre `@testing-library/react` para smoke render (AUD-W2C08-003) | Decisão sobre expandir devDependencies. | Pergunta para Mario. Default proposto: NÃO expandir; entregar 12 testes (formatRota×7 + isPathActive×5). |
| **B4** — `figma-reference.png` é mesmo o anexado ao prompt original? | Imagem chegou ao working tree fora desta sessão (untracked). | Confirmação visual nesta sessão sugere que sim (alinhamento com descrição textual da analysis Seção 5). Aceito tacitamente. Mario pode validar visualmente antes de Gate 2. |
| **B5** — `audit-report-round2.md` (untracked, do C06) | Não pertence ao C08. | Será **deixado intocado** — não é objeto desta sessão. |

---

## 5. Plano de validação interna pós-correção (Gate 2 + smoke check)

### 5.1 Para cada achado: critério objetivo

| ID | Critério "resolvido" |
|---|---|
| 001 | `git ls-tree wave2-v4-c08/fixes/execution -- docs/wave2-v4-c08/figma-reference.png` retorna o blob. Hash do PNG = hash do arquivo no working tree. |
| 002 | `docs/wave2-v4-c08/analysis.md` existe na branch de execução. Hash bate com `bdba7649…` (blob do `wave2-v4-c08/analysis`). Link em `CHANGELOG.md:9159` resolve. |
| 003 | `npx vitest run` mostra 12 novos testes passando (7 `formatRota` + 5 `isPathActive`); 15 existentes continuam passando; total ≥ 27. `npx tsc --noEmit` exit 0. |
| 004 | `globals.css` contém `--color-card-art-bg: #d9d9d9;`; `detalhe.module.css:290` usa `var(--color-card-art-bg)`. Smoke visual com prova `66f36e8b` mostra cinza médio claramente distinto do card branco. |
| 005+006 | `page.tsx` não tem mais o 7º `metaItem`; `requerimentoLabel` exibe `Requerimento: NNN · PRV-YYYY-MM-XXXXXX`. Em viewport 768px e 1100px, grid 3×2 desktop / 2×3 mobile-tablet sem células órfãs. |
| 007 | `.title` em viewport 768px renderiza no mínimo 24px (medido via DevTools). |
| 008 | Seção "Página de detalhe: estrutura e extensão para Wave 3" presente em `CLAUDE.md` e cobre as 4 camadas + flags Timeline + localização final de `formatRota`/`isPathActive`. |
| 010 | `formatStatus` removida; `STATUS_LABELS[prova.status]` direto. `npx tsc --noEmit` exit 0. |
| 011 | Hover do mouse em `—` mostra tooltip nativo; Vitest da `formatRota(null)` continua passando. |
| 009 | DECISIONS atualizado com decisão (WONTFIX ou troca para `contain`); se troca, smoke visual com prova retangular real mostra letterbox cinza. |
| 012 | Coberto por 003. |
| 013 | `smoke-validation.md` existe com 15 itens listados. Mario marca pass/fail antes do PR final. |
| 014/015/016 | DECISIONS atualizado com nota informativa correspondente. |

### 5.2 Suítes de teste

- **Vitest (frontend):** 15 (existentes) + 12 (novos) = 27 testes passando. Comando: `cd frontend && npx vitest run`.
- **pytest (backend):** preservado intacto (não tocamos backend). Espera-se 805 passed + 9 skipped (Wave 2 v4.0 C06 Audit Fixes) — confirmar com `cd backend && python -m pytest`.
- **Cobertura ≥ 80%:** preservada (sem mudança backend).
- **`alembic upgrade head` / `downgrade -1`:** N/A (sem migration nova).

### 5.3 Smoke E2E manual (template a criar pelo Gate 2)

`docs/wave2-v4-c08/smoke-validation.md` com 15 itens copiados de `CHANGELOG.md:9210-9231`. Mario percorre. Critério de aceite: 15/15 PASS.

### 5.4 Validação MCP pós-correção

- **`get_advisors security` + `get_advisors performance`:** mesma quantidade de alerts pré-correção (1 INFO + 1 WARN security + 13 INFO performance). Zero novos.
- **`list_tables('public')`:** estrutura inalterada.
- **Distribuição de provas:** inalterada (não tocamos dados).

### 5.5 Validação de extensibilidade da Timeline para Wave 3

Procedimento manual no Gate 2 (não commitar):
1. Adicionar temporariamente em `StatusProva`: `| "_TEST_LAMINANDO_MATRIZ"`.
2. Adicionar em `STATUS_LABELS`: `_TEST_LAMINANDO_MATRIZ: "Laminando (matriz)"`.
3. Hardcode num teste local de Timeline (não commitar) com nó usando `_TEST_LAMINANDO_MATRIZ`.
4. Confirmar render sem reescrever `Timeline.tsx`.
5. **Reverter** todas as mudanças temporárias antes de prosseguir.

### 5.6 Validação de fidelidade visual contra Figma

Para cada achado de fidelidade visual (4, 5, 6, 7, 13):
- Screenshot do estado pós-correção em viewport 1440×900.
- Comparação manual com `figma-reference.png` no mesmo elemento.
- Anexar screenshot ao `fix-plan.md` (seção Resultado da Execução).

### 5.7 Validação de RNF-001 (< 3s)

EXPLAIN ANALYZE da query mais quente já é 0.121ms. Nenhuma mudança esperada. Em runtime, render React inalterado significativamente. Lighthouse audit do `/provas/[id]` opcional — não bloqueante.

### 5.8 Validação de acessibilidade

- **Contraste:** `--color-card-text-muted=#575757` sobre `--color-card-art-bg=#d9d9d9` ≈ 5.4:1 → passa AA (4.5:1).
- **ARIA modais:** preservado (não tocamos).
- **Focus trap:** preservado.
- **Tooltip nativo (AUD-011):** lido por screen readers.
- **axe-core:** opcional (não há infra para rodar automatizado nesta sessão; Lighthouse cobre o essencial).

---

## 6. Plano de atualização documental (acumulativo)

| Arquivo | O que adicionar | Tipo |
|---|---|---|
| `CHANGELOG.md` | Nova seção `## v4.0 — Wave 2 — Componente 08 — Correções Pós-Auditoria` com lista dos 16 achados, status (RESOLVIDO/DEFERIDO/INFO), commit SHA. **Apêndice**, não substituição. | apêndice |
| `DECISIONS.md` | ADR-129 (token `--color-card-art-bg`); apêndice no ADR-127 (sobre `Codigo` no header em vez do grid); apêndices informativos para AUD-014/015/016. | apêndice |
| `CLAUDE.md` | Seção "Página de detalhe de prova: estrutura e extensão para Wave 3" (AUD-W2C08-008). | apêndice |
| `docs/wave2-v4-c08/audit-report.md` | Apêndice "Status final por achado" — para cada um dos 16, marcar `RESOLVIDO em commit <sha>` ou `DEFERIDO — justificativa`. **Não editar o corpo original.** | apêndice |
| `docs/wave2-v4-c08/fix-plan.md` (este arquivo) | Seção 7 "Resultado da Execução" — diffs entre planejado e realizado. | apêndice |
| `docs/wave2-v4-c08/fix-validation.md` (NOVO no Gate 2) | Checklist completo + auto-crítica adversarial + recomendação final. | novo |
| `docs/wave2-v4-c08/smoke-validation.md` (NOVO no Gate 2) | Template do smoke E2E manual (15 itens). | novo |

---

## 7. Resultado da Execução (a preencher no Gate 2)

> Esta seção fica **vazia** até o Gate 2 começar. Será preenchida durante a execução com os diffs entre o planejado nesta seção 2 e o efetivamente realizado, commit por commit.

```
Commit 1: <sha> — fix(wave2-v4/c08/AUD-001): ...
   Diff vs plano: <descrição>
Commit 2: <sha> — docs(wave2-v4/c08/AUD-002): ...
   Diff vs plano: <descrição>
...
```

---

## Notas finais sobre limites de escopo (re-confirmação)

- **Não toca** backend (endpoints, schemas, migrations, RLS, scripts).
- **Não toca** Cloudflare R2.
- **Não toca** state_machine.py (Wave 3 cuida da expansão para 14 estados).
- **Não toca** access-matrix.json (Wave 1 v4.0 cuida do RBAC).
- **Não introduz** Framer Motion novo (Wave 6 cuida das animações sofisticadas).
- **Não modifica** endpoints C13 (Cancelamento) ou C14 (Reinício) — apenas integra via contrato existente.
- **Não cria** migration Alembic ou RLS nova.
- **Não modifica** o cadastro (C06) nem o RBAC (Wave 1).
- **Não reclassifica** severidade dos achados unilateralmente.
- **Não corrige** achados fora do `audit-report.md` sem autorização explícita.
- **Preserva** o tratamento de provas legacy (`rota IS NULL`).
- **Preserva** a viabilidade da Wave 3 (Timeline orientada a dados; mapeamentos em `STATUS_LABELS` extensíveis).

**FIM do plano.**
