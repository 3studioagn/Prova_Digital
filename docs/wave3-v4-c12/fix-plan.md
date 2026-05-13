# Plano de Correção · Wave 3 v4.0 · Componente 12

**Branch de plano:** `wave3-v4-c12/fixes/plan` (saiu de `wave3-v4-c12/audit`
para carregar o `audit-report.md` que ainda não está em `development`).
**Branch de execução (Gate 2):** `wave3-v4-c12/fixes/execution` (sairá da
mesma base de `wave3-v4-c12/audit` pelo mesmo motivo).
**PR final aponta para:** `development`.
**Data:** 2026-05-13.
**Origem:** [docs/wave3-v4-c12/audit-report.md](audit-report.md) (HEAD `2a18794`).
**Veredito da auditoria:** APROVADO COM CORREÇÕES MENORES.
**Achados totais:** 0 CRÍTICO · 0 ALTO · 4 MÉDIO · 5 BAIXO · 4 INFO = **13**.

> Este documento é o plano completo (Gate 1) da sessão de correção. Nenhuma
> linha de código de produção foi tocada na elaboração. A execução só inicia
> após autorização explícita do Mario via string
> `AUTORIZADO GATE 2 — CORREÇÃO C12 v4.0`.

---

## 1. Validação de Pré-Requisitos

### 1.1 Leitura de contexto confirmada

| Artefato | Caminho real | Estado |
|---|---|---|
| Relatório de auditoria | [docs/wave3-v4-c12/audit-report.md](audit-report.md) | ✅ Lido integralmente (970 LOC) |
| Contrato C12 | [docs/wave3-v4-c11/contrato-c12.md](../wave3-v4-c11/contrato-c12.md) | ✅ Presente, completo, intocado pelo C12 (409 LOC) |
| Analysis Gate 1+2 | [docs/wave3-v4-c12/analysis.md](analysis.md) | ✅ Lido integralmente (1478 LOC; inclui §16 decisões aprovadas + §17 apêndice de execução) |
| DECISIONS.md (ADRs 158-161) | [DECISIONS.md](../../DECISIONS.md) | ✅ 4 ADRs do C12 lidos |
| CHANGELOG entrada C12 | [CHANGELOG.md](../../CHANGELOG.md) (linhas 5-150) | ✅ Lido |
| CLAUDE.md tabela waves | [CLAUDE.md](../../CLAUDE.md) | ✅ Linha do C12 verificada |
| Smoke validation | [docs/wave3-v4-c12/smoke-validation.md](smoke-validation.md) | ✅ Presente |
| PR description | [docs/wave3-v4-c12/pr-description.md](pr-description.md) | ✅ Presente (124 LOC) |
| visual-guide.md | **AUSENTE** — gap do C12 (AUD-W3C12-003) | ❌ Será criado neste plano |

### 1.2 Contrato C12 — Resumo (consume, não modifica)

| Seção | Conteúdo | Reuso C12 |
|---|---|---|
| §1.3 | `STATUS_LABELS` / `STATUS_LABELS_SHORT` | ✅ Importado em Timeline.tsx |
| §2.2 | `contexto_motorista` Python | ✅ Espelho TypeScript em `prova.ts:354-362` (8 linhas) |
| §3.1 | Sequências canônicas por rota (MATRIZ=6 / LAM_MATRIZ=11 / FILIAL=4 / LAM_FILIAL=7) | ✅ `ROTA_ETAPAS` em `prova.ts:399-436` |
| §3.2 | Sequências legacy (PADRAO=7 / DIRETA=5) | ✅ `LEGACY_ROTA_PADRAO/DIRETA` em `prova.ts:444-466` |
| §6.1 | `prefers-reduced-motion` | ✅ Dupla defesa JS + CSS |
| §6.3 | ARIA | ✅ region/list/listitem/group/alert + `aria-current="step"` |

`git diff --name-only origin/development..HEAD -- docs/wave3-v4-c11/contrato-c12.md`
= **vazio.** Cláusula pétrea respeitada.

### 1.3 Decisões de design aprovadas em DECISIONS.md

Reproduzidas literalmente de `analysis.md §16` (aprovação do Mario em 2026-05-13)
+ ADRs 158, 159, 160, 161 em `DECISIONS.md`:

| # | Decisão | Opção aprovada | ADR | Implementação verificada |
|---|---|---|---|---|
| 1 | Orientação | (a) Vertical | — | ✅ `.timeline { flex-direction: column }` |
| 2 | Layout 4 rotas | (c) Mesmo layout + badge + bloco laminação | — | ✅ `TimelineHeader` + `RenderNodes` |
| 3 | Destaque laminação | (a) Bloco separado label "Etapa de Laminação" | **ADR-160** | ✅ `.laminationBlock` borda dashed verde `#c0ca33` |
| 4 | Contextos motorista | (c) Badge textual | — | ✅ `CONTEXTO_BADGE_LABEL` literal "→ Laminação"/"Laminação →"/"→ Clicheria" |
| 5 | Múltiplos ciclos | (a) Empilhados + separador | — | ✅ `<li .cycleSeparator>↻ reinício de ciclo</li>` |
| 6 | Indicador atual | (a)+(b)+(c) framer-motion reusado | **ADR-161** | ✅ `motion.span` pulse + `useReducedMotion` + badge "Atual" |
| 7 | Cancelamento | (b)+(c) tachado + cinza + motivo | — | ⚠️ PARCIAL — card vermelho + nó cinza + motivo OK; **tachado não implementado** (AUD-W3C12-006) |
| 8 | Terminal sucesso | (a)+(b) check verde + "Concluída" | — | ✅ `CheckCircleIcon` + `.terminalBadge` + `.headerStatusBadgeOk` |
| 9 | Interatividade | (a) Estática | — | ✅ Sem `tabindex`/`onClick`/`onHover` |
| 10 | Densidade | (c) Densa | — | ✅ label + ator + setor + timestamp + motivo |
| 11.1 | Labels legacy | (α) Global `PADRAO→"Matriz"`, `DIRETA→"Filial"` | **ADR-158** (supersede ADR-126) | ✅ `prova.ts:258-259` |
| 11.2 | Tratamento `rota=NULL` | (b) Heurística via `vendedor_localizacao` | **ADR-159** | ✅ `getRotaEtapas` e `getRotaLabel` |
| 11.3 | Laminação para legacy | Nunca renderizar | — (consequência ADR-160) | ✅ `ESTADOS_LAMINACAO` exclui legacy |

**14/14 decisões registradas.** Apenas Decisão 7 com nuance documentada
como AUD-W3C12-006 (escalação humana antes do Gate 2).

### 1.4 Validação de Infraestrutura (MCP read-only)

**Supabase (`rwxlpwmnkekzuurgthkr` · `ACTIVE_HEALTHY` · sa-east-1):**

| Item | Esperado pós-C11 | Real | Status |
|---|---|---|---|
| `alembic_version` | `013` | `013` | ✅ |
| `status_prova_enum` valores | 17 | 17 | ✅ |
| `rota_enum` valores | 6 | 6 | ✅ |
| Trigger `trg_provas_rota_imutavel` | Preservado | Preservado | ✅ |
| RLS 014/015 | Preservadas | Preservadas | ✅ |
| Schema `app_private` helpers | Preservados | Preservados | ✅ |
| Advisor security | 1 INFO (alembic_version ADR-025) + 1 WARN (auth_leaked_password ADR-027) | **Idêntico** | ✅ |
| Advisor performance | 13 INFO `unused_index` (baseline pré-existente) | **Idêntico** | ✅ |

**Cloudflare R2:** N/A — sessão frontend puro. Sem necessidade de validação.

**Resultado:** zero alteração estrutural pelo C12. Banco em produção
idêntico ao pós-C11. Esperado e confirmado.

### 1.5 Validação de Não-Modificação (cláusulas pétreas)

```bash
$ git diff --name-only origin/development..HEAD -- \
    backend/ \
    docs/wave3-v4-c11/contrato-c12.md \
    shared/ \
    frontend/src/middleware.ts \
    frontend/src/lib/services/ \
    frontend/src/lib/codigo-publico.ts \
    frontend/src/lib/c19-mensagens.ts \
    "frontend/src/app/(dashboard)/escanear/" \
    "frontend/src/app/(dashboard)/provas/[id]/AdminActions.tsx" \
    "frontend/src/app/(dashboard)/provas/[id]/page.tsx" \
    "frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css" \
    frontend/src/hooks/useProvaDetail.ts
(vazio)
```

✅ **Backend intocado.**
✅ **`contrato-c12.md` intocado.**
✅ **Outras entregas anteriores intocadas** (C11/C10/C19/C06/C08/Wave 1).

`git diff --stat origin/development..HEAD` traz **13 arquivos** modificados
(12 do C12 entregue + 1 audit-report da branch atual). Todos dentro do
escopo declarado.

### 1.6 LOC reais via `wc -l` (evidência para AUD-W3C12-002)

| Arquivo | Documentado em 4 lugares | Real | Δ |
|---|---|---|---|
| `frontend/src/app/(dashboard)/provas/[id]/Timeline.tsx` | 410 | **563** | +153 |
| `frontend/src/app/(dashboard)/provas/[id]/timeline.module.css` | 372 | **471** | +99 |
| `frontend/src/lib/timeline-builder.ts` | 240 ou 354 (inconsistente) | **354** | +0/+114 |
| `frontend/src/lib/types/prova.ts` | 690 ou 482 | **681** | -9/+199 |

A discrepância em Timeline.tsx (+153) corresponde aproximadamente aos 3
SVG icons inline (`CheckCircleIcon`, `AlertTriangleIcon`, `BanIcon` ~73 LOC)
+ JSDoc do header (~22 LOC) + subcomponentes inline (TimelineHeader,
CancellationCard, TimelineStep, RenderNodes, TimelineCycleItem ~60 LOC).

---

## 2. Inventário Consolidado dos 13 Achados

Tabela exaustiva — uma linha por achado, com todas as categorizações
exigidas pela Seção 4.1 do prompt.

### Legenda de colunas (categorizações booleanas)

- **D** = é decisão de design ignorada?
- **C** = é cenário obrigatório com bug visual?
- **R** = é reuso quebrado do `contrato-c12.md`?
- **M-Ct** = é modificação não-autorizada do `contrato-c12.md`?
- **M-Be** = é modificação não-autorizada do backend?
- **M-Oe** = é modificação não-autorizada de outras entregas?
- **A11y** = é problema de acessibilidade?
- **Perf** = é problema de performance?

### 2.1 MÉDIOS (4 achados)

#### AUD-W3C12-001 — `AnimatePresence` envolve children sem `motion.*` exit/enter

| Campo | Valor |
|---|---|
| **Severidade** | MÉDIO |
| **Categoria** | Manutenibilidade + Performance |
| **Arquivo + linha** | `frontend/src/app/(dashboard)/provas/[id]/Timeline.tsx:540-559` |
| **Descrição** | `<AnimatePresence initial={false}>` envolve `built.cycles.map(...)` que renderiza `<Fragment>` + `<li .cycleSeparator>` + `<TimelineCycleItem>`. Nenhum desses é `motion.*` com `initial/animate/exit`. Wrapper sem efeito visual real — pode confundir leitor futuro. |
| **Recomendação original** | Ou remover `<AnimatePresence>` (caso de uso atual não tem transição de saída de ciclos); ou converter `<TimelineCycleItem>` em `<motion.li>` com `initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}`. |
| **Status atual** | Pendente — corrigível em ~2 LOC |
| D | ❌ Não |
| C | ❌ Não |
| R | ❌ Não |
| M-Ct | ❌ Não |
| M-Be | ❌ Não |
| M-Oe | ❌ Não |
| A11y | ❌ Não |
| Perf | ⚠️ Negligenciável (overhead < 1ms) |

---

#### AUD-W3C12-002 — Discrepância de LOC documentada vs real

| Campo | Valor |
|---|---|
| **Severidade** | MÉDIO (documentação) |
| **Categoria** | Documentação |
| **Arquivo + linha** | `CHANGELOG.md:13` · `CLAUDE.md` (linha do C12 na tabela) · `docs/wave3-v4-c12/pr-description.md:41-42` · `docs/wave3-v4-c12/analysis.md:1444` |
| **Descrição** | 4 documentos afirmam "Timeline.tsx 410 LOC (era 273)" mas `wc -l` confirma **563 LOC** reais (+153 não-documentados). Causa provável: contagem manual sem incluir SVG icons inline (~73 LOC) + JSDoc cabeçalho (~22 LOC) + subcomponentes inline (~60 LOC). |
| **Recomendação original** | Atualizar para "Timeline.tsx 563 LOC" ou esclarecer "410 LOC excluindo SVG icons + cabeçalho + subcomponentes". |
| **Status atual** | Pendente — pura documentação, risco zero |
| D | ❌ Não |
| C | ❌ Não |
| R | ❌ Não |
| M-Ct | ❌ Não |
| M-Be | ❌ Não |
| M-Oe | ❌ Não |
| A11y | ❌ Não |
| Perf | ❌ Não |

---

#### AUD-W3C12-003 — `visual-guide.md` ausente

| Campo | Valor |
|---|---|
| **Severidade** | MÉDIO |
| **Categoria** | Documentação |
| **Arquivo + linha** | `docs/wave3-v4-c12/` (arquivo não existe) |
| **Descrição** | Prompt do C12 + prompt da auditoria recomendam `visual-guide.md` com screenshots dos 8 cenários. C12 substituiu por `smoke-validation.md` (18 cenários textuais), que cobre o roteiro de validação mas não o resultado visual. R-4: cenários 2/3/4 sem fixtures em produção (LAM_MATRIZ / FILIAL / LAM_FILIAL = 0 provas). |
| **Recomendação original** | Criar `visual-guide.md` (pode ser stub pós-smoke do Mario). |
| **Status atual** | Pendente — criar STUB estruturado com 8 cenários, prova representativa de cada um, placeholder para screenshot (Mario preenche pós-smoke E2E manual). Cenários 2/3/4 marcados SKIP explicitamente. |
| D | ❌ Não |
| C | ❌ Não |
| R | ❌ Não |
| M-Ct | ❌ Não |
| M-Be | ❌ Não |
| M-Oe | ❌ Não |
| A11y | ❌ Não |
| Perf | ❌ Não |

---

#### AUD-W3C12-004 — Coverage % não medido formalmente

| Campo | Valor |
|---|---|
| **Severidade** | MÉDIO |
| **Categoria** | Cobertura de testes |
| **Arquivo + linha** | Critério 19 do prompt do C12 (§6.3) + `analysis.md §17.4` |
| **Descrição** | Critério 19 exige ≥ 80% nos componentes novos. Entrega marca como ⚠️ "Não medido (D-13 sem coverage v8); estimativa por inspeção ≥ 95%". Sem evidência formal. D-13 da Wave 1 v4.0 (Vitest minimal sem `@vitest/coverage-v8`) é decisão de projeto válida — instalar permanentemente adiciona ~10MB. |
| **Recomendação original** | Rodar `npx vitest run --coverage` pontualmente (sem instalar dep permanente) OU registrar como exceção formal em D-13. |
| **Status atual** | Pendente — rodar pontualmente com `npm install --save-dev --no-save @vitest/coverage-v8` (não persistir no package.json), capturar snapshot em `docs/wave3-v4-c12/coverage-snapshot.md`, depois `npm uninstall @vitest/coverage-v8`. Plano B se inviável: registrar exceção em DECISIONS.md como nota ao D-13. |
| D | ❌ Não |
| C | ❌ Não |
| R | ❌ Não |
| M-Ct | ❌ Não |
| M-Be | ❌ Não |
| M-Oe | ❌ Não |
| A11y | ❌ Não |
| Perf | ❌ Não |

---

### 2.2 BAIXOS (5 achados)

#### AUD-W3C12-005 — `<aside role="alert">` vs `<div role="alert">` (semântica)

| Campo | Valor |
|---|---|
| **Severidade** | BAIXO |
| **Categoria** | A11y/Semântica HTML |
| **Arquivo + linha** | `frontend/src/app/(dashboard)/provas/[id]/Timeline.tsx:203` |
| **Descrição** | `<aside>` significa "side content" (HTML5). `<div role="alert">` é mais semanticamente adequado para alerta. Leitor de tela anuncia de qualquer forma por causa de `role="alert"`. |
| **Recomendação original** | Trocar `<aside>` por `<div>` (purismo) OU manter (não impacta a11y). |
| **Status atual** | Pendente — 1 LOC, risco zero |
| D | ❌ Não |
| C | ❌ Não |
| R | ❌ Não |
| M-Ct | ❌ Não |
| M-Be | ❌ Não |
| M-Oe | ❌ Não |
| A11y | ⚠️ Benigna — semântica HTML, não funcional |
| Perf | ❌ Não |

---

#### AUD-W3C12-006 — Decisão 7 implementada parcialmente (sem tachado nos passos anteriores)

| Campo | Valor |
|---|---|
| **Severidade** | BAIXO (essência da decisão preservada) |
| **Categoria** | Conformidade Visual + Decisão de design parcial |
| **Arquivo + linha** | `Timeline.tsx` (sem strikethrough no nó imediatamente anterior ao cancelamento) + `DECISIONS.md` (decisão de design aprovada em 2026-05-13) |
| **Descrição** | Decisão 7 aprovada: "(b)+(c) tachado no último ativo + nó 'Cancelada' cinza + motivo destacado". Entrega tem ✅ nó cinza + ✅ motivo + ✅ card vermelho `role="alert"` (mecanismos extras), mas ❌ **tachado/strikethrough no nó imediatamente anterior ao cancelamento NÃO IMPLEMENTADO**. |
| **Recomendação original** | Confirmar com Mario se atende ou se vale adicionar `text-decoration: line-through`. Se Mario aceitar como está, rebaixar para INFO. |
| **Status atual** | **ESCALAÇÃO HUMANA NECESSÁRIA antes do Gate 2** — vide §6 deste plano |
| D | ⚠️ Sim — Decisão 7 parcial. Referência: `DECISIONS.md` linha de "Decisão 7" (analysis §16) + AUD-W3C12-006 |
| C | ⚠️ Sim — Cenário 7 (prova cancelada). Divergência: sem tachado no nó anterior. Card + cinza + motivo já preservam a essência. |
| R | ❌ Não |
| M-Ct | ❌ Não |
| M-Be | ❌ Não |
| M-Oe | ❌ Não |
| A11y | ❌ Não (tachado não afeta leitor de tela; nó cinza + motivo já comunicam) |
| Perf | ❌ Não |

---

#### AUD-W3C12-007 — `<ol role="list">` redundante

| Campo | Valor |
|---|---|
| **Severidade** | BAIXO (a11y benigna) |
| **Categoria** | A11y |
| **Arquivo + linha** | `Timeline.tsx:388, 471, 539` (3 ocorrências: `<ol className={styles.cycles} role="list">` e dois `<ul role="list">`) |
| **Descrição** | `<ol>` e `<ul>` já têm `role="list"` implícito por HTML5. Adicionar explicitamente é redundante mas benigno. Algumas implementações de leitor podem ler 2×. |
| **Recomendação original** | Remover `role="list"` em todos os `<ol>`/`<ul>`. Não afeta comportamento. |
| **Status atual** | Pendente — 3 LOCs, risco zero |
| D | ❌ Não |
| C | ❌ Não |
| R | ❌ Não |
| M-Ct | ❌ Não |
| M-Be | ❌ Não |
| M-Oe | ❌ Não |
| A11y | ⚠️ Benigna — redundância semântica |
| Perf | ❌ Não |

---

#### AUD-W3C12-008 — Critério #15 (performance < 500ms) não medido formalmente

| Campo | Valor |
|---|---|
| **Severidade** | BAIXO |
| **Categoria** | Performance |
| **Arquivo + linha** | `smoke-validation.md` cenário 15 |
| **Descrição** | Critério 15 do prompt (§6.3 "Render < 500ms em 3+ ciclos") não medido pelo auditor (sem acesso E2E browser). Estimativa por inspeção: < 50ms (folga 10×). |
| **Recomendação original** | Mario mede no smoke 15 via DevTools Performance. Documentar resultado em smoke-validation.md ou visual-guide.md. |
| **Status atual** | **DEFERRED para smoke E2E manual** do Mario — sem código. Registrar status em `fix-validation.md`. |
| D | ❌ Não |
| C | ❌ Não |
| R | ❌ Não |
| M-Ct | ❌ Não |
| M-Be | ❌ Não |
| M-Oe | ❌ Não |
| A11y | ❌ Não |
| Perf | ⚠️ Sim (mas estimativa folgada) |

---

#### AUD-W3C12-009 — Critério #16+17 (snapshot tests + E2E) não entregues

| Campo | Valor |
|---|---|
| **Severidade** | BAIXO |
| **Categoria** | Cobertura de testes |
| **Arquivo + linha** | `analysis.md §17.3.1` |
| **Descrição** | Critérios 16+17 substituídos por smoke manual + 20 testes unitários do builder. Justificativa documentada (preservar D-13 da Wave 1 v4.0 com Vitest `environment: node`). Aceitável tecnicamente, mas prompt não pré-aprovou a substituição. |
| **Recomendação original** | Manter como está — smoke manual + testes unitários cobrem camada de dados (≥ 95% por inspeção). Avaliar `@testing-library/react` + `jsdom` na Wave 4. |
| **Status atual** | **ACEITO como tradeoff documentado** — sem código. Registrar status em `fix-validation.md`. |
| D | ❌ Não |
| C | ❌ Não |
| R | ❌ Não |
| M-Ct | ❌ Não |
| M-Be | ❌ Não |
| M-Oe | ❌ Não |
| A11y | ❌ Não |
| Perf | ❌ Não |

---

### 2.3 INFO (4 achados)

#### AUD-W3C12-010 — `aria-label` do rotaBadge redundante com texto visível

| Campo | Valor |
|---|---|
| **Severidade** | INFO |
| **Categoria** | A11y benigna |
| **Arquivo + linha** | `Timeline.tsx:171` — `<span className={styles.rotaBadge} aria-label={\`Rota: ${rotaLabel}\`}>{\`Rota: ${rotaLabel}\`}</span>` |
| **Descrição** | Texto interno e `aria-label` idênticos. Redundância benigna. |
| **Recomendação original** | Remover `aria-label` (leitor já lê texto). |
| **Status atual** | Pendente — 1 LOC, risco zero |
| D | ❌ Não |
| C | ❌ Não |
| R | ❌ Não |
| M-Ct | ❌ Não |
| M-Be | ❌ Não |
| M-Oe | ❌ Não |
| A11y | ⚠️ Benigna |
| Perf | ❌ Não |

---

#### AUD-W3C12-011 — R-12 filtros C07 com duplicação visual

| Campo | Valor |
|---|---|
| **Severidade** | INFO |
| **Categoria** | Follow-up de UI |
| **Arquivo + linha** | `analysis.md §17.3.3 + §16.3` |
| **Descrição** | Após Decisão 11.1 (`PADRAO`→"Matriz", `DIRETA`→"Filial"), filtros de listagem C07 podem mostrar 2× "Matriz" (MATRIZ + PADRAO) e 2× "Filial" (FILIAL + DIRETA). Não-bloqueante para o PR. |
| **Recomendação original** | Decidir pós-merge se vale colapsar opções. |
| **Status atual** | **DEFERRED para pós-merge** (já documentado no analysis e CHANGELOG do C12) — sem código. Registrar status em `fix-validation.md`. |
| D | ❌ Não |
| C | ❌ Não |
| R | ❌ Não |
| M-Ct | ❌ Não |
| M-Be | ❌ Não |
| M-Oe | ❌ Não |
| A11y | ❌ Não |
| Perf | ❌ Não |

---

#### AUD-W3C12-012 — Snapshot tests substituídos por smoke manual + testes unitários

| Campo | Valor |
|---|---|
| **Severidade** | INFO |
| **Categoria** | Cobertura |
| **Arquivo + linha** | `analysis.md §17.3.1` |
| **Descrição** | Decisão consciente registrada — coberto por AUD-W3C12-009. |
| **Recomendação original** | Manter como está. |
| **Status atual** | **ACEITO** — sem ação (consolidado com AUD-W3C12-009). |
| D | ❌ Não |
| C | ❌ Não |
| R | ❌ Não |
| M-Ct | ❌ Não |
| M-Be | ❌ Não |
| M-Oe | ❌ Não |
| A11y | ❌ Não |
| Perf | ❌ Não |

---

#### AUD-W3C12-013 — Subcomponentes inline em Timeline.tsx vs arquivos separados

| Campo | Valor |
|---|---|
| **Severidade** | INFO |
| **Categoria** | Manutenibilidade |
| **Arquivo + linha** | `analysis.md §17.3.2` |
| **Descrição** | Plano do Gate 1 previa 8 subcomponentes em arquivos separados. Entregue: 5 internos a Timeline.tsx. Justificativa: < 50 LOC cada, sem reuso externo. Aceita. |
| **Recomendação original** | Manter como está. |
| **Status atual** | **ACEITO** — sem ação. |
| D | ❌ Não |
| C | ❌ Não |
| R | ❌ Não |
| M-Ct | ❌ Não |
| M-Be | ❌ Não |
| M-Oe | ❌ Não |
| A11y | ❌ Não |
| Perf | ❌ Não |

---

## 3. Plano de Correção por Achado

### 3.1 CORRIGÍVEIS (7 achados + 1 dependente de Mario)

#### AUD-W3C12-001 — Remover `AnimatePresence` sem motion children

- **Estratégia:** Remover `<AnimatePresence initial={false}>` que envolve `built.cycles.map(...)` em `Timeline.tsx:540-559`. O caso de uso atual não tem transição de saída de ciclos (página de detalhe não re-renderiza ciclos individualmente — re-monta a Timeline inteira ao trocar prova). Manter os filhos no mesmo lugar, sem o wrapper. Decisão (a) "remover" preferida sobre (b) "converter para motion.li" porque: (1) não há regressão visual; (2) preserva minimalismo; (3) sem custo de animação de entrada que não é necessária no caso de uso atual.
- **Tipo:** modificação de lógica visual (remoção).
- **Confirmação de cláusulas pétreas:**
  - ❌ Não modifica backend (∅).
  - ❌ Não modifica `contrato-c12.md` (∅).
  - ❌ Não modifica outras entregas (∅).
  - ❌ Não introduz Framer Motion novo (remove um uso existente sem efeito).
- **Arquivos tocados (lista exaustiva):**
  - `frontend/src/app/(dashboard)/provas/[id]/Timeline.tsx` (~2 linhas: remover abertura + fechamento de `<AnimatePresence>`).
- **Camadas afetadas:** Frontend apenas (componente Timeline).
- **Risco de regressão:** BAIXO — `AnimatePresence` sem motion children não produz efeito visual; remoção é equivalente comportamental.
- **Validação:** `npx vitest run` (163 testes preservados) + `npx tsc --noEmit` exit 0 + `npx next build` 13/13 + render visual da Timeline com prova de ciclo múltiplo (R-6) idêntico ao baseline.
- **Dependência:** Independente.

---

#### AUD-W3C12-002 — Atualizar LOC reais em 4 documentos

- **Estratégia:** Atualizar literalmente em cada documento "Timeline.tsx 410 LOC (era 273)" → **"Timeline.tsx 563 LOC (era 273) — inclui 73 LOC de SVG icons inline (CheckCircleIcon/AlertTriangleIcon/BanIcon), 22 LOC de JSDoc cabeçalho e ~60 LOC de subcomponentes inline"**. Aplicar mesma transparência aos demais arquivos onde LOC documentado diverge do real:
  - `timeline.module.css`: 372 → **471** (delta +99 do refactor visual).
  - `timeline-builder.ts`: 240/354 → **354** (esclarecer o valor real).
  - `prova.ts`: 482/690 → **681** (delta +199 vs original 482).
- **Tipo:** documentação (4 arquivos).
- **Confirmação de cláusulas pétreas:**
  - ❌ Não modifica backend (∅).
  - ❌ Não modifica `contrato-c12.md` (∅).
  - ❌ Não modifica outras entregas (∅).
- **Arquivos tocados:**
  - `CHANGELOG.md` (linha que afirma "Timeline.tsx 410 LOC, era 273" — busca por "410 LOC").
  - `CLAUDE.md` (linha do C12 na tabela de waves — busca por "410 LOC" no item "Adicionado").
  - `docs/wave3-v4-c12/pr-description.md` (linha 41-42).
  - `docs/wave3-v4-c12/analysis.md` (§17.5 linha ~1444 — tabela "Resumo de mudanças por arquivo").
- **Camadas afetadas:** Documentação apenas.
- **Risco de regressão:** ZERO — documentação não-executável.
- **Validação:** Após `git commit`, verificar via `Grep "410 LOC"` que retorna 0 matches (todos atualizados).
- **Dependência:** Deve ser **o último commit de código** — para que LOC pós-AUD-001 reflita Timeline.tsx atualizado. Vou medir Timeline.tsx novamente após AUD-001 (estimado 563 - 2 = ~561) e usar esse valor.

---

#### AUD-W3C12-003 — Criar `visual-guide.md` STUB estruturado

- **Estratégia:** Criar `docs/wave3-v4-c12/visual-guide.md` com 8 seções (uma por cenário obrigatório). Cada seção contém:
  - **Descrição** do cenário (1 parágrafo).
  - **Decisão de design relevante** com ID (§16 do analysis ou ADR).
  - **Prova representativa em produção** (do Anexo A.3 do audit-report):
    - Cenário 1 (Matriz em andamento): `PRV-2026-05-TEX9GW`
    - Cenário 2 (Lam.Matriz): ⚠️ SKIP — sem prova em produção (R-4)
    - Cenário 3 (Filial): ⚠️ SKIP — sem prova em produção (R-4)
    - Cenário 4 (Lam.Filial): ⚠️ SKIP — sem prova em produção (R-4)
    - Cenário 5 (multi-ciclos): `PRV-2026-04-B9CZ37`
    - Cenário 6 (legacy DIRETA terminal): `PRV-2026-04-9MGETS`
    - Cenário 7 (cancelada legacy PADRAO): `PRV-2026-04-XPXWKA`
    - Cenário 8 (terminal sucesso): `PRV-2026-04-9MGETS` ou `PRV-2026-04-C67HZS`
  - **Placeholder de screenshot** com instrução para Mario preencher pós-smoke E2E.
  - **Critério de validação visual** (texto referenciando o achado do auditor).
- **Tipo:** documentação (novo arquivo).
- **Confirmação de cláusulas pétreas:** ❌ Não modifica nenhum dos itens protegidos.
- **Arquivos tocados:** `docs/wave3-v4-c12/visual-guide.md` (NOVO ~120 LOC).
- **Camadas afetadas:** Documentação.
- **Risco de regressão:** ZERO.
- **Validação:** Arquivo existe; estrutura coerente com 8 cenários.
- **Dependência:** Independente.

---

#### AUD-W3C12-004 — Medir coverage formalmente

- **Estratégia primária:** Instalar `@vitest/coverage-v8` temporariamente sem persistir no `package.json`:
  ```powershell
  cd frontend
  npm install --no-save @vitest/coverage-v8
  npx vitest run --coverage --coverage.reporter=text --coverage.reporter=json-summary
  npm uninstall @vitest/coverage-v8  # garante package.json limpo
  ```
  Capturar output em `docs/wave3-v4-c12/coverage-snapshot.md` com tabela por arquivo (stmts/branches/funcs/lines %).
- **Estratégia secundária (se a instalação temporária quebrar algo):** Registrar exceção em DECISIONS.md como apêndice ao D-13 da Wave 1 v4.0, com argumentação:
  - D-13 mantém Vitest minimal por design.
  - 65 testes Vitest novos (45 prova + 20 builder) cobrem todas as funções públicas com 3+ casos.
  - Inspeção manual confirma ≥ 95% nos arquivos novos.
- **Plano contingência se coverage < 80% em algum módulo:** adicionar testes faltantes para subir > 80%, ou documentar a área não-coberta com justificativa.
- **Tipo:** tooling + documentação.
- **Confirmação de cláusulas pétreas:**
  - ❌ Não modifica backend (∅).
  - ❌ Não modifica `contrato-c12.md` (∅).
  - ❌ Não modifica outras entregas (∅).
  - **Não persiste dependência permanente** (passa `--no-save` e desinstala após).
- **Arquivos tocados:**
  - `docs/wave3-v4-c12/coverage-snapshot.md` (NOVO).
  - Possivelmente `DECISIONS.md` (apêndice se estratégia secundária).
- **Camadas afetadas:** Tooling + documentação.
- **Risco de regressão:** BAIXO — instalação temporária pode falhar por incompatibilidade Node/Windows. Mitigação: estratégia secundária registrada.
- **Validação:** Arquivo `coverage-snapshot.md` existe; coverage formal disponível para auditoria futura.
- **Dependência:** Independente. **Recomendação: rodar PRIMEIRO** entre os MÉDIOS — se revelar < 80% em algum arquivo, abre subitem de correção.

---

#### AUD-W3C12-005 — `<aside>` → `<div>` no CancellationCard

- **Estratégia:** Trocar `<aside className={styles.cancellationCard} role="alert">` por `<div className={styles.cancellationCard} role="alert">` em `Timeline.tsx:203`. Comportamento idêntico para leitor de tela; semântica HTML mais adequada.
- **Tipo:** correção de a11y (semântica).
- **Confirmação de cláusulas pétreas:** ❌ Não modifica nenhum item protegido.
- **Arquivos tocados:** `frontend/src/app/(dashboard)/provas/[id]/Timeline.tsx` (1 linha).
- **Camadas afetadas:** Frontend.
- **Risco de regressão:** ZERO — `role="alert"` é o que dispara o anúncio do leitor; `<div>` vs `<aside>` não muda esse comportamento.
- **Validação:** Vitest 163/163; tsc 0; next build 13/13; visual inalterado (CSS module `.cancellationCard` aplica ambos `<aside>` e `<div>`).
- **Dependência:** Independente.

---

#### AUD-W3C12-006 — Decisão 7 parcial (REQUER RESPOSTA DO MARIO ANTES DO GATE 2)

- **Estratégia condicional dependendo da resposta humana** (vide §6):
  - **(A) Mario aceita o atual:** rebaixar para INFO. Registrar decisão em DECISIONS.md como apêndice à Decisão 7 do C12. **Sem mudança de código.**
  - **(B) Mario pede tachado:** implementar `text-decoration: line-through; opacity: 0.6` no nó imediatamente anterior ao `.nodeCancelamento`. Implementação técnica preferida:
    - No `lib/timeline-builder.ts`: adicionar flag `precedesCancellation: boolean` calculada quando o nó CANCELADA existe; o nó imediatamente anterior (não-cancelado) recebe a flag.
    - Em `Timeline.tsx`: aplicar classe `.nodePrecedesCancellation` (ou prop) quando `node.precedesCancellation === true`.
    - Em `timeline.module.css`: nova regra `.nodePrecedesCancellation .nodeLabel { text-decoration: line-through; opacity: 0.6 }` (cobre apenas o label, não o resto).
    - Adicionar 1 teste Vitest no `timeline-builder.test.ts` cobrindo o cenário "prova cancelada — nó anterior tem flag precedesCancellation=true".
- **Tipo:** dependendo da resposta — modificação visual (B) ou ACEITAR (A).
- **Confirmação de cláusulas pétreas:**
  - ❌ Não modifica backend (∅).
  - ❌ Não modifica `contrato-c12.md` (∅).
  - ❌ Não modifica outras entregas (∅).
  - ❌ Não introduz Framer Motion novo.
- **Arquivos tocados (se B):**
  - `frontend/src/lib/timeline-builder.ts` (~5 linhas — calcular flag).
  - `frontend/src/app/(dashboard)/provas/[id]/Timeline.tsx` (~2 linhas — aplicar classe).
  - `frontend/src/app/(dashboard)/provas/[id]/timeline.module.css` (~3 linhas — nova regra).
  - `frontend/src/lib/__tests__/timeline-builder.test.ts` (1 teste novo).
- **Camadas afetadas:** Frontend.
- **Risco de regressão:** BAIXO — flag opt-in, só afeta cenário cancelado; CSS regra com cascata correta.
- **Validação:** Vitest 164 (era 163 + 1 novo); tsc 0; next build 13/13; verificar visualmente que (i) prova cancelada com mov anterior `RETIRADA` mostra "Retirada pelo vendedor" tachada; (ii) prova cancelada sem mov anterior (cancelada em CRIADA) não quebra.
- **Dependência:** **BLOQUEADO PELA RESPOSTA DO MARIO.**

---

#### AUD-W3C12-007 — Remover `role="list"` redundante de `<ol>`/`<ul>`

- **Estratégia:** Remover `role="list"` de 3 ocorrências em `Timeline.tsx` (linhas 388, 471, 539 — todas em `<ol>` ou `<ul>`). `<ol>` e `<ul>` já têm o role implícito por HTML5. Comportamento idêntico.
- **Tipo:** correção de a11y (limpeza).
- **Confirmação de cláusulas pétreas:** ❌ Não modifica nenhum item protegido.
- **Arquivos tocados:** `Timeline.tsx` (3 LOCs).
- **Camadas afetadas:** Frontend.
- **Risco de regressão:** ZERO — role implícito mantido.
- **Validação:** Vitest 163; tsc 0; next build 13/13; visual idêntico.
- **Dependência:** Independente.

---

#### AUD-W3C12-010 — Remover `aria-label` redundante do rotaBadge

- **Estratégia:** Remover o `aria-label={\`Rota: ${rotaLabel}\`}` em `Timeline.tsx:171` (texto interno já é lido). 1 LOC.
- **Tipo:** correção de a11y (limpeza).
- **Confirmação de cláusulas pétreas:** ❌ Não modifica nenhum item protegido.
- **Arquivos tocados:** `Timeline.tsx` (1 LOC).
- **Camadas afetadas:** Frontend.
- **Risco de regressão:** ZERO.
- **Validação:** Vitest 163; tsc 0; next build 13/13; visual idêntico; leitor de tela continua lendo "Rota: Matriz" (texto interno).
- **Dependência:** Independente.

---

### 3.2 DEFERRED com registro (4 achados)

#### AUD-W3C12-008 — Performance < 500ms (smoke 15 manual do Mario)

- **Justificativa do deferral:** Cenário 15 do smoke já registra a medição manual via DevTools Performance pelo Mario. Auditor estima < 50ms (folga 10×). Sem código a alterar nesta sessão.
- **Encaminhamento:** Registrar status "DEFERRED — smoke 15 manual" em `fix-validation.md`. Mario executa quando rodar o smoke E2E pré-PR.

#### AUD-W3C12-009 — Snapshot tests + E2E não entregues

- **Justificativa do deferral:** Substituição por smoke manual + 20 testes unitários do builder já documentada e justificada em `analysis.md §17.3.1` (preservar D-13 da Wave 1 v4.0 com Vitest `environment: node`).
- **Encaminhamento:** Registrar status "ACEITO como tradeoff" em `fix-validation.md`. Avaliação futura na Wave 4 (dashboard pode requerer `@testing-library/react`).

#### AUD-W3C12-011 — R-12 filtros C07 com duplicação visual

- **Justificativa do deferral:** Decisão de UI orientada por uso real — pós-merge. Já documentada em `analysis.md §16.3 + §17.3.3`.
- **Encaminhamento:** Registrar status "DEFERRED — decisão pós-merge" em `fix-validation.md`.

#### AUD-W3C12-012 — Snapshot tests substituídos (decisão consciente)

- **Justificativa:** Coberto por AUD-W3C12-009 (mesma decisão).
- **Encaminhamento:** Consolidado com AUD-W3C12-009 no `fix-validation.md`.

#### AUD-W3C12-013 — Subcomponentes inline em Timeline.tsx

- **Justificativa:** Decisão consciente documentada em `analysis.md §17.3.2` (cada subcomponente < 50 LOC, sem reuso externo).
- **Encaminhamento:** Registrar status "ACEITO" em `fix-validation.md`.

---

## 4. Ordem Topológica de Execução (Gate 2)

Construída respeitando as 3 regras hierárquicas do prompt §4.3:
1. Severidade: MÉDIO → BAIXO → INFO.
2. Dentro do grupo: (a) reverter modificações indevidas — N/A aqui, (b) decisão de design ignorada, (c) cenário obrigatório, (d) reuso quebrado, (e) acessibilidade, (f) outros.
3. Dependências antes de dependentes.

### 4.1 Sequência numerada dos CORRIGÍVEIS

```
[1] AUD-W3C12-004  · MÉDIO · Coverage snapshot
                     (FAZER PRIMEIRO — pode revelar novos subitens)

[2] AUD-W3C12-001  · MÉDIO · Remove <AnimatePresence> sem motion children
                     (independente; código curto)

[3] AUD-W3C12-005  · BAIXO · <aside> → <div> CancellationCard
                     (a11y benigna; 1 LOC)

[4] AUD-W3C12-007  · BAIXO · Remove role="list" redundante
                     (a11y benigna; 3 LOCs)

[5] AUD-W3C12-010  · INFO  · Remove aria-label rotaBadge redundante
                     (a11y benigna; 1 LOC)

[6] AUD-W3C12-006  · BAIXO · Decisão 7 tachado
                     (CONDICIONAL — só executa se Mario escolher opção B)

[7] AUD-W3C12-003  · MÉDIO · Cria visual-guide.md
                     (após estabilizar código; pode referenciar correções)

[8] AUD-W3C12-002  · MÉDIO · Atualiza LOC nos 4 documentos
                     (ÚLTIMO — para refletir Timeline.tsx pós-AUD-001/005/007/010)
```

### 4.2 DEFERRED (sem execução; só registro)

```
[D1] AUD-W3C12-008  · BAIXO · Performance — smoke manual Mario
[D2] AUD-W3C12-009  · BAIXO · Snapshot/E2E — aceito como tradeoff
[D3] AUD-W3C12-011  · INFO  · R-12 filtros C07 — decisão pós-merge
[D4] AUD-W3C12-012  · INFO  · Snapshot substituído — consolidado com D2
[D5] AUD-W3C12-013  · INFO  · Subcomponentes inline — aceito
```

### 4.3 Total esperado de commits

- 7 commits de correção (1 por AUD CORRIGÍVEL, ordem acima — assumindo Mario escolher opção A em AUD-006; se opção B, 8 commits).
- 1 commit de documentação consolidada (CHANGELOG + DECISIONS + audit-report apêndice + fix-validation).

---

## 5. Análise de Risco Agregado

### 5.1 Risco ALTO de regressão

**NENHUM.** Todos os achados corrigíveis são localizados, com efeito
visual ou semântico mínimo, validados por suíte Vitest existente.

### 5.2 Decisões de design ignoradas

- **1 achado:** AUD-W3C12-006 (Decisão 7 parcial — sem tachado).
- Referência: `DECISIONS.md` → seção "Decisão 7" via `analysis.md §16`.
- Implementação atual preserva a essência (3 mecanismos: card vermelho
  + nó cinza + motivo destacado) — falta apenas a 4ª camada (tachado).
- **Tratamento:** escalação humana antes do Gate 2 (vide §6).

### 5.3 Cenários obrigatórios com bug visual

- **1 achado:** AUD-W3C12-006 (cenário 7 — prova cancelada).
- **Divergência exata:** sem `text-decoration: line-through` no nó
  imediatamente anterior ao `.nodeCancelamento`.
- **Severidade rebaixada para BAIXO** pelo auditor porque os outros 3
  mecanismos comunicam o cancelamento sem ambiguidade.
- **Tratamento:** se Mario optar B (vide §6), correção mínima ~5 LOCs.

### 5.4 Reuso quebrado do `contrato-c12.md`

**NENHUM.** Auditoria confirma reuso completo (audit-report §1.6).

### 5.5 Modificação não-autorizada do `contrato-c12.md`

**NENHUMA.** `git diff -- docs/wave3-v4-c11/contrato-c12.md` retorna
vazio (validação em §1.5 deste plano).

### 5.6 Modificação não-autorizada do backend

**NENHUMA.** `git diff -- backend/` retorna vazio.

### 5.7 Modificação não-autorizada de outras entregas

**NENHUMA.** `git diff` em paths protegidos (escanear/, AdminActions,
detalhe.module.css, page.tsx do detalhe, services/identificacao-prova,
codigo-publico, c19-mensagens, middleware, access-matrix, useProvaDetail,
state_machine/) retorna vazio.

### 5.8 Acessibilidade

- **3 achados:** AUD-005, AUD-007, AUD-010 — todos benignos (semântica
  HTML, redundância de roles, aria-label duplicado). Nenhum representa
  violação real (axe-core não acusaria).
- **Validação:** smoke 14 do `smoke-validation.md` (Mario com axe-core
  + leitor de tela). Já existe; nada a adicionar.

### 5.9 Performance

- **1 achado:** AUD-008 — render < 500ms não medido formalmente.
- **Estimativa de inspeção:** < 50ms (folga 10×).
- **Tratamento:** DEFERRED ao smoke 15 manual do Mario.

### 5.10 Cobertura de testes

- **2 achados:** AUD-004 (coverage % não medido) + AUD-009 (snapshot/E2E
  ausentes).
- **Tratamento:** AUD-004 corrigido via snapshot pontual (vide §3.1
  estratégia primária); AUD-009 aceito como tradeoff.

---

## 6. Pontos de Escalação Humana ANTES do Gate 2

### 6.1 AUD-W3C12-006 — Decisão 7 parcial

**Contexto:** A Decisão 7 aprovada pelo Mario em 2026-05-13 foi:
> "(b)+(c) tachado no último ativo + nó 'Cancelada' cinza + motivo destacado"

A entrega tem 3 dos 4 mecanismos (card vermelho `role="alert"` extra
+ nó cinza + motivo destacado). Falta o **tachado/strikethrough** no
nó imediatamente anterior ao cancelamento.

**Duas opções:**

#### Opção A — ACEITAR o atual (rebaixar para INFO)

Justificativa: os 3 mecanismos sobrepostos (card vermelho que dispara
`role="alert"` no leitor de tela + nó cinza `CANCELADA` terminal +
motivo destacado em vermelho) comunicam o cancelamento sem ambiguidade.
O tachado seria uma 4ª camada que adiciona ruído visual sobre algo já
saturado de sinalização.

**Ação no Gate 2:** rebaixar AUD-006 para INFO; registrar decisão como
apêndice à Decisão 7 no DECISIONS.md (estilo análogo ao ADR-130 do
C08 v4.0 — "WONTFIX com justificativa").

**Impacto:** zero LOC de código; 1 apêndice em DECISIONS.

#### Opção B — IMPLEMENTAR o tachado conforme decisão literal

Justificativa: a Decisão 7 foi aprovada com 3 mecanismos explícitos
(tachado + nó cinza + motivo); cumprir literalmente o que foi
aprovado.

**Ação no Gate 2:**
- `lib/timeline-builder.ts`: adicionar flag `precedesCancellation: boolean`
  no `TimelineNode`; calcular no pipeline quando o último nó do ciclo
  for `CANCELADA`, marcar o penúltimo nó com a flag.
- `Timeline.tsx`: aplicar classe `.nodePrecedesCancellation` no `<li>`
  do nó.
- `timeline.module.css`: regra `.nodePrecedesCancellation .nodeLabel {
  text-decoration: line-through; opacity: 0.6 }` (cobre só o label, não
  o resto do nó).
- `timeline-builder.test.ts`: 1 teste novo cobrindo o cenário.

**Impacto:** ~10 LOCs entre TS + CSS + 1 teste Vitest.

---

> **Mario:** por favor escolha entre **Opção A (aceitar — sem tachado)** e
> **Opção B (implementar tachado)** antes da autorização do Gate 2.

---

## 7. Plano de Validação Interna Pós-Correção (Seção 4.5)

Critérios objetivos a serem cumpridos antes do PR. Cada um vai virar
checkbox em `fix-validation.md`.

### 7.1 Verificações de não-modificação (cláusulas pétreas)

- [ ] `git diff origin/development..HEAD -- backend/` retorna vazio.
- [ ] `git diff origin/development..HEAD -- docs/wave3-v4-c11/contrato-c12.md` retorna vazio.
- [ ] `git diff origin/development..HEAD -- backend/app/state_machine/` retorna vazio.
- [ ] `git diff origin/development..HEAD -- "frontend/src/app/(dashboard)/escanear/"` retorna vazio.
- [ ] `git diff origin/development..HEAD -- "frontend/src/app/(dashboard)/provas/[id]/AdminActions.tsx"` retorna vazio.
- [ ] `git diff origin/development..HEAD -- frontend/src/lib/services/` retorna vazio.
- [ ] `git diff origin/development..HEAD -- frontend/src/lib/codigo-publico.ts frontend/src/lib/c19-mensagens.ts` retorna vazio.
- [ ] `git diff origin/development..HEAD -- shared/ frontend/src/middleware.ts` retorna vazio.

### 7.2 Suíte de testes

- [ ] `cd frontend && npx vitest run` → ≥ 163 passed (164 se AUD-006 opção B).
- [ ] `cd frontend && npx tsc --noEmit` → exit 0.
- [ ] `cd frontend && npx next build` → 13/13 páginas.

### 7.3 Reuso do contrato preservado

- [ ] Grep por hexadecimais de cores dos 17 estados em Timeline.tsx → apenas em consumo via `var(--color-*)` ou nos imports do contrato. Sem hardcode novo.
- [ ] `STATUS_LABELS` ainda consumido via import do `prova.ts`.
- [ ] `ROTA_ETAPAS` e `LEGACY_ROTA_*` ainda exportados do `prova.ts` sem duplicação.

### 7.4 Acessibilidade

- [ ] axe-core no browser real (Mario rodar smoke 14 do `smoke-validation.md`) — sem violações críticas em cada cenário.
- [ ] Navegação por teclado: Decisão 9 (estática) — sem `tabindex` na Timeline; foco continua passando para `actionsRow` da página de detalhe.
- [ ] `prefers-reduced-motion: reduce` no DevTools desabilita o pulse (cenário 13 do smoke).
- [ ] Leitor de tela (Mario rodar smoke 12 com VoiceOver/NVDA) — Timeline anunciada corretamente.

### 7.5 Performance

- [ ] Smoke 15 do `smoke-validation.md`: Mario mede via DevTools Performance — render < 500ms em prova com 3+ ciclos. Documentar em `fix-validation.md` ou anexar ao `visual-guide.md`.

### 7.6 Coverage

- [ ] `coverage-snapshot.md` criado com tabela por arquivo. Se < 80% em algum módulo dos arquivos novos, testes adicionais incluídos no commit.

### 7.7 Banco e advisors

- [ ] `alembic_version = 013` (igual ao pós-C11).
- [ ] `get_advisors security` idêntico ao baseline (1 INFO + 1 WARN, ambos pré-existentes).
- [ ] `get_advisors performance` idêntico ao baseline (13 INFO `unused_index`).
- [ ] Nenhum advisor crítico novo.

### 7.8 Renderização visual

- [ ] `visual-guide.md` criado com 8 seções estruturadas + provas representativas.
- [ ] Smoke E2E manual do Mario (`smoke-validation.md` 18 cenários) — pelo menos cenários disponíveis em produção (1, 5, 6, 7, 8); cenários 2/3/4 SKIP ou seed.
- [ ] Captura de screenshots por Mario (pós-smoke) para preencher `visual-guide.md`.

### 7.9 Conformidade com decisões de design

- [ ] 14/14 decisões implementadas (já verificado pelo auditor). Apenas AUD-006 com nuance — resolvida pela escolha do Mario.

### 7.10 Documentação atualizada

- [ ] CHANGELOG.md com nova seção "C12 — Correções Pós-Auditoria" listando 7 corrigidos + 4 deferred + 1 escalado.
- [ ] DECISIONS.md com apêndice à Decisão 7 (se opção A) OU sem mudança (se opção B implementa).
- [ ] `audit-report.md` com apêndice de status por achado.
- [ ] `fix-plan.md` com seção "Resultado da Execução" preenchida (commits SHAs).
- [ ] `fix-validation.md` criado com checklist completo + verificação por achado + auto-crítica.
- [ ] `CLAUDE.md` atualizado se algum procedimento mudou (provavelmente não).

---

## 8. Plano de Atualização de Documentação (Seção 4.6)

### 8.1 `CHANGELOG.md`

Nova seção (apêndice — não substitui a do C12):

```
## v4.0 — Wave 3 — Componente 12 — Correções Pós-Auditoria (2026-05-13)

**Branch:** `wave3-v4-c12/fixes/execution` → PR contra `development`.
**Origem:** [audit-report.md](docs/wave3-v4-c12/audit-report.md).
**Veredito da auditoria:** APROVADO COM CORREÇÕES MENORES.
**Resultado:** 7 corrigidos · 4 deferred · 1 escalado e resolvido (opção <A|B>).

### Corrigido

- **AUD-W3C12-001** — Remove `<AnimatePresence>` sem motion children
  em Timeline.tsx (wrapper sem efeito visual).
- **AUD-W3C12-002** — Atualiza LOC reais em CHANGELOG/CLAUDE/pr-description/analysis.
- **AUD-W3C12-003** — Cria `docs/wave3-v4-c12/visual-guide.md` stub
  estruturado com 8 cenários.
- **AUD-W3C12-004** — Captura coverage snapshot em
  `docs/wave3-v4-c12/coverage-snapshot.md` (sem persistir
  `@vitest/coverage-v8` no package.json).
- **AUD-W3C12-005** — `<aside role="alert">` → `<div role="alert">` no
  CancellationCard (purismo semântico).
- **AUD-W3C12-007** — Remove `role="list"` redundante de 3 `<ol>/<ul>`.
- **AUD-W3C12-010** — Remove `aria-label` redundante do rotaBadge.
- *(condicional)* **AUD-W3C12-006** — Tachado no nó anterior ao
  cancelamento (se Mario optar B).

### Deferred (sem código nesta sessão)

- **AUD-W3C12-008** — Performance < 500ms — Mario mede no smoke 15.
- **AUD-W3C12-009** — Snapshot/E2E aceito como tradeoff (D-13 da Wave 1 v4.0).
- **AUD-W3C12-011** — R-12 filtros C07 — decisão pós-merge.
- **AUD-W3C12-012** — Consolidado com AUD-009.
- **AUD-W3C12-013** — Subcomponentes inline — aceito.

### Validação

- `npx vitest run` 163/163 (164 se opção B) sem regressão.
- `npx tsc --noEmit` exit 0.
- `npx next build` 13/13.
- MCP advisors security + performance idênticos ao baseline pós-C11.
- `git diff` em paths protegidos (backend, contrato-c12.md, outras
  entregas) retorna vazio.
```

### 8.2 `DECISIONS.md`

- **Se opção A:** Apêndice à Decisão 7 (entrada nova em estilo "PostScript"
  do ADR-160 ou similar) registrando que o tachado foi **explicitamente
  dispensado** após análise pós-auditoria: "os 3 mecanismos sobrepostos
  (card vermelho `role="alert"` + nó cinza terminal + motivo destacado)
  comunicam o cancelamento sem ambiguidade; o tachado adicionaria ruído
  visual sobre algo já saturado de sinalização".

- **Se opção B:** Sem mudança em DECISIONS.md (a decisão original é
  cumprida).

- **AUD-004:** apêndice ao D-13 da Wave 1 v4.0 com nota: "Coverage
  pontual via instalação temporária de `@vitest/coverage-v8` com
  `--no-save` + `npm uninstall` após uso — preserva D-13 sem persistir
  dependência."

### 8.3 `CLAUDE.md`

Verificar se algum procedimento da seção "Página de detalhe da prova"
mudou pela correção. **Estimativa: nenhuma mudança** — todas as
correções são localizadas, sem impacto procedural.

### 8.4 `docs/wave3-v4-c12/audit-report.md` — apêndice de status

Adicionar, no fim do arquivo (sem editar o corpo original), nova
seção:

```
---

## Apêndice — Status Pós-Correção (preenchido em 2026-05-XX)

| ID | Status final | Commit | Critério de prova |
|---|---|---|---|
| AUD-W3C12-001 | RESOLVIDO em commit `<sha>` | <sha> | Diff em Timeline.tsx remove `<AnimatePresence>` + suite Vitest 163/163 |
| AUD-W3C12-002 | RESOLVIDO em commit `<sha>` | <sha> | grep "410 LOC" retorna 0 matches |
| AUD-W3C12-003 | RESOLVIDO em commit `<sha>` | <sha> | `docs/wave3-v4-c12/visual-guide.md` existe |
| AUD-W3C12-004 | RESOLVIDO em commit `<sha>` | <sha> | `coverage-snapshot.md` com tabela |
| AUD-W3C12-005 | RESOLVIDO em commit `<sha>` | <sha> | Diff em Timeline.tsx troca `<aside>` por `<div>` |
| AUD-W3C12-006 | RESOLVIDO (opção <A|B>) | <sha ou N/A> | <screenshot ou nota> |
| AUD-W3C12-007 | RESOLVIDO em commit `<sha>` | <sha> | grep `role="list"` retorna 0 matches em Timeline.tsx |
| AUD-W3C12-008 | DEFERRED — smoke 15 manual | N/A | Mario executa pré-PR |
| AUD-W3C12-009 | ACEITO como tradeoff (D-13) | N/A | analysis §17.3.1 |
| AUD-W3C12-010 | RESOLVIDO em commit `<sha>` | <sha> | Diff em Timeline.tsx remove aria-label |
| AUD-W3C12-011 | DEFERRED — pós-merge | N/A | analysis §17.3.3 |
| AUD-W3C12-012 | ACEITO — consolidado com AUD-009 | N/A | — |
| AUD-W3C12-013 | ACEITO — analysis §17.3.2 | N/A | — |
```

### 8.5 `docs/wave3-v4-c12/fix-plan.md` (este arquivo)

Anexar, no fim, seção "Resultado da Execução" comparando planejado vs
realizado (commits, divergências, retiros, additions).

### 8.6 `docs/wave3-v4-c12/fix-validation.md` (NOVO)

Criar com:
- Checklist objetivo da Seção 7 deste plano (com checkboxes preenchidos).
- Verificação por achado (uma linha por AUD com status final, commit
  SHA, critério de prova, evidência).
- Auto-crítica adversarial (Seção 6.3 do prompt).
- Recomendação final (PR pronto para merge `development` /
  pronto-com-deferred / sessão precisa estender).

### 8.7 `docs/wave3-v4-c12/visual-guide.md` (NOVO — AUD-W3C12-003)

Criar com 8 seções (uma por cenário) + STUBs para screenshots do Mario
pós-smoke. Detalhamento técnico em §3.1.

### 8.8 `docs/wave3-v4-c12/coverage-snapshot.md` (NOVO — AUD-W3C12-004)

Capturar output de `npx vitest run --coverage` em tabela por arquivo
(stmts/branches/funcs/lines %). Foco nos arquivos novos: `prova.ts`,
`timeline-builder.ts`, `Timeline.tsx`.

---

## 9. Critérios de Saída da Sessão de Correção

Checklist final (espelho da Seção 8 do prompt):

- [ ] PR aberto contra `development` com descrição completa por achado.
- [ ] `fix-plan.md` com seção "Resultado da Execução" preenchida.
- [ ] `fix-validation.md` com checklist + verificação + auto-crítica.
- [ ] `audit-report.md` com apêndice de status por achado.
- [ ] `CHANGELOG.md` + `DECISIONS.md` atualizados acumulativamente.
- [ ] `CLAUDE.md` atualizado se necessário (provavelmente não).
- [ ] Smoke check 100% verde (suíte Vitest, tsc, next build, MCP advisors).
- [ ] `visual-guide.md` criado (mesmo que STUB pendente smoke do Mario).
- [ ] Reuso do contrato preservado (validado por grep).
- [ ] Performance: smoke 15 do Mario (DEFERRED registrado).
- [ ] Recomendação explícita de nova auditoria independente pós-correção.
- [ ] Reconhecimento de que merge `main` requer sessão de revisão de Wave 3.

---

## 10. Resultado da Execução (placeholder — Gate 2)

> Esta seção será preenchida ao final do Gate 2 com diffs entre planejado
> e realizado.

```
(vazio — a preencher no Gate 2)
```

---

**Fim do Plano de Correção · Gate 1 · 2026-05-13.**
