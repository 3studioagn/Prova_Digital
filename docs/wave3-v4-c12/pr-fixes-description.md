# PR Description — C12 Correções Pós-Auditoria

**Para colar no GitHub** ao abrir o PR de `wave3-v4-c12/fixes/execution`
→ `development`.

---

## Título sugerido

```
docs(wave3-v4/c12): correcoes pos-auditoria (13 achados tratados)
```

---

## Corpo

```markdown
## Resumo

Sessão de correção pós-auditoria sênior do Componente 12 da Wave 3 v4.0.
Trata os 13 achados do [audit-report.md](docs/wave3-v4-c12/audit-report.md)
(veredito **APROVADO COM CORREÇÕES MENORES** — 0 CRÍTICO · 0 ALTO ·
4 MÉDIO · 5 BAIXO · 4 INFO).

**Resultado:** 8 RESOLVIDOS · 3 DEFERRED · 2 ACEITOS · Zero não-tratados.

## Achados tratados

### Corrigidos (8)

| ID | Severidade | Tipo | Commit |
|---|---|---|---|
| AUD-W3C12-001 | MÉDIO | Remove `<AnimatePresence>` sem motion children em Timeline.tsx | `d5dc3b7` |
| AUD-W3C12-002 | MÉDIO | Reconcilia LOCs reais em 4 docs (CLAUDE/CHANGELOG/PR/analysis) | `7667355` |
| AUD-W3C12-003 | MÉDIO | Cria `docs/wave3-v4-c12/visual-guide.md` stub estruturado | `f40f7b6` |
| AUD-W3C12-004 | MÉDIO | Captura coverage snapshot pontual (sem persistir dep) | `7c61350` |
| AUD-W3C12-005 | BAIXO | `<aside role="alert">` → `<div role="alert">` no CancellationCard | `07222ba` |
| AUD-W3C12-006 | BAIXO → INFO | Apêndice à Decisão 7 (Opção A — aceitar atual sem tachado) | `27e0b8e` |
| AUD-W3C12-007 | BAIXO | Remove `role="list"` redundante em 3 `<ol>/<ul>` | `c55285a` |
| AUD-W3C12-010 | INFO | Remove `aria-label` redundante do rotaBadge | `f973a0b` |

### Deferred ou Aceitos (5)

| ID | Severidade | Tratamento |
|---|---|---|
| AUD-W3C12-008 | BAIXO | **DEFERRED** — smoke 15 manual Mario (DevTools Performance) |
| AUD-W3C12-009 | BAIXO | **ACEITO** como tradeoff D-13 documentado |
| AUD-W3C12-011 | INFO | **DEFERRED** — decisão R-12 pós-merge (filtros C07) |
| AUD-W3C12-012 | INFO | **ACEITO** — consolidado com AUD-009 |
| AUD-W3C12-013 | INFO | **ACEITO** — subcomponentes inline (analysis §17.3.2) |

## Decisão escalada — AUD-W3C12-006 (Opção A)

A Decisão 7 do C12 (cancelamento) listava 3 mecanismos: card vermelho
+ nó cinza + motivo + **tachado no nó anterior**. A entrega do C12
implementou 3 dos 4 mecanismos (card vermelho `role="alert"` extra
+ nó cinza CANCELADA + motivo destacado), mas o tachado não foi
implementado.

**Mario aprovou Opção A em 2026-05-13**: aceitar como está, rebaixar
para INFO, registrar decisão consciente como apêndice à Decisão 7 em
DECISIONS.md (após ADR-161). Razão principal: tachado significa
"deletado/anulado" — a movimentação anterior aconteceu de fato e está
gravada com trigger de imutabilidade; tachá-la seria factualmente
impreciso. Os 3 mecanismos atuais comunicam o cancelamento sem
ambiguidade.

## Validação

- [x] `npx vitest run`: **163/163** testes passados (sem regressão).
- [x] `npx tsc --noEmit`: exit 0.
- [x] `npx next build`: **13/13** páginas; `/provas/[id]` em **14.4 kB / 212 kB** (Δ -1.7 kB / -2 kB pelo AUD-001).
- [x] Coverage: timeline-builder.ts **99.46%**, prova.ts **94.94%**, global **97.15%** (acima do limiar 80%).
- [x] `git diff origin/development..HEAD --` em paths protegidos: **vazio**.
  - backend/ ✅
  - docs/wave3-v4-c11/contrato-c12.md ✅
  - backend/app/state_machine/ ✅
  - frontend/src/app/(dashboard)/escanear/ ✅
  - frontend/src/app/(dashboard)/provas/[id]/AdminActions.tsx ✅
  - frontend/src/app/(dashboard)/provas/[id]/page.tsx ✅
  - frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css ✅
  - frontend/src/lib/services/ ✅
  - frontend/src/lib/codigo-publico.ts ✅
  - frontend/src/lib/c19-mensagens.ts ✅
  - shared/ ✅
  - frontend/src/middleware.ts ✅
  - frontend/src/hooks/useProvaDetail.ts ✅
- [x] MCP advisors security + performance: **idênticos ao baseline pós-C11** (1 INFO `alembic_version` + 1 WARN `auth_leaked_password` security; 13 INFO `unused_index` performance — todos pré-existentes).

## Documentos

- [docs/wave3-v4-c12/fix-plan.md](docs/wave3-v4-c12/fix-plan.md) — Plano completo (Gate 1) com inventário, estratégia por achado, ordem topológica, análise de risco, plano de validação e seção §10 "Resultado da Execução" preenchida.
- [docs/wave3-v4-c12/fix-validation.md](docs/wave3-v4-c12/fix-validation.md) — Relatório de validação com checklist objetivo, verificação por achado, auto-crítica adversarial (21 perguntas respondidas) e recomendação final.
- [docs/wave3-v4-c12/visual-guide.md](docs/wave3-v4-c12/visual-guide.md) — Guia visual stub com 8 cenários estruturados + roteiro para Mario preencher screenshots pós-smoke.
- [docs/wave3-v4-c12/coverage-snapshot.md](docs/wave3-v4-c12/coverage-snapshot.md) — Snapshot de cobertura.
- [docs/wave3-v4-c12/audit-report.md](docs/wave3-v4-c12/audit-report.md) — Relatório original + **apêndice de status pós-correção** no fim.
- [CHANGELOG.md](CHANGELOG.md) — Nova seção "C12 — Correções Pós-Auditoria" antes da seção do C12 original.
- [DECISIONS.md](DECISIONS.md) — Apêndice à Decisão 7 (após ADR-161) registrando Opção A consciente para AUD-006.

## Pendências para PR para `main` (não bloqueiam merge em `development`)

Herdadas das entregas anteriores da Wave 3 v4.0:

1. **Rate limit backend** (ADR-145 do C19) — `/scan` 30/min/user → 429. Sessão dedicada.
2. **Benchmarks** (ADR-153 + ADR-157 do C11) — latência `/transicoes`. Sessão dedicada.
3. **CI/CD pós-Wave 3** (ADR-156 do C11) — drift Python↔Postgres em CI. Sessão dedicada.

Específicas do C12:

4. **Smoke E2E manual** ([smoke-validation.md](docs/wave3-v4-c12/smoke-validation.md) 18 cenários). Cenários 2/3/4 SKIP em produção (R-4 — sem fixtures Lam.*).
5. **Validação leitor de tela** + **axe-core manual** + **performance medida** (smokes 12/14/15).
6. **Screenshots para visual-guide.md** preenchendo placeholders.
7. **Decisão R-12 do AUD-011** — filtros C07 com duplicação visual.

## MARCO — fim da Wave 3 v4.0

Esta é a **última sessão de correção de componente da Wave 3 v4.0.**
Após esta correção (e eventual re-auditoria independente recomendada),
**sessão de revisão de Wave 3 inteira pré-merge `main`** — sessão
dedicada, fora desta correção — antes do merge `development → main`.

Wave 3 inteira completa em `development`. Próximo passo é revisão
consolidada da wave (C10 + C19 + C11 + C12 + Audit Fixes), não merge
direto.

## Recomendações

1. **Nova rodada de auditoria independente em sessão separada**, usando
   o `PROMPT_Auditoria_PosWave3_C12_v4.md`, para confirmar resolução
   dos 13 achados + ausência de regressão + paridade visual das 14
   decisões + reuso do contrato preservado + acessibilidade validada.
2. **Sessão de revisão de Wave 3 inteira pré-merge `main`**.

## Lista de commits (10 commits)

```
da4878c docs(wave3-v4/c12/fixes): consolida documentacao final pos-correcoes
7667355 docs(wave3-v4/c12/AUD-002): reconcilia LOCs reais em 4 docs
f40f7b6 docs(wave3-v4/c12/AUD-003): cria visual-guide.md stub estruturado
27e0b8e docs(wave3-v4/c12/AUD-006): registra apendice a Decisao 7 (Opcao A)
f973a0b a11y(wave3-v4/c12/AUD-010): remove aria-label redundante do rotaBadge
c55285a a11y(wave3-v4/c12/AUD-007): remove role=list redundante em <ol>/<ul>
07222ba a11y(wave3-v4/c12/AUD-005): <aside role=alert> -> <div role=alert>
d5dc3b7 refactor(wave3-v4/c12/AUD-001): remove AnimatePresence sem motion children
7c61350 test(wave3-v4/c12/AUD-004): coverage snapshot dos componentes novos
aa0199d docs(wave3-v4/c12/fixes): plano de correcao pos-auditoria
```

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

---

## Como abrir o PR sem gh CLI

1. Push da branch: `git push -u origin wave3-v4-c12/fixes/execution`
2. Acessar GitHub na URL impressa pelo `git push` (link "Pull request").
3. Title: copiar de "Título sugerido" acima.
4. Body: copiar tudo de "## Resumo" até a última `` ` `` (fechamento do bloco de commits).
5. **Base branch:** `development` (NÃO `main`).
6. **Head branch:** `wave3-v4-c12/fixes/execution`.
7. Submit.

**Recomendação:** marcar a sessão de revisão de Wave 3 pré-merge `main` como
TODO no projeto antes de fechar este PR.
