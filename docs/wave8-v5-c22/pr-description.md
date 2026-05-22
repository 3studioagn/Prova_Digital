# Descrição do PR — Componente 22 (Wave 8 v5.0)

> **Como abrir o PR:** a branch `wave8-v5/componente-22` ja esta publicada
> no GitHub. O `gh` CLI nao esta instalado nesta maquina, entao o PR deve
> ser criado pela web. Abra:
>
> **https://github.com/3studioagn/Prova_Digital/pull/new/wave8-v5/componente-22**
>
> Base: `development` · Compare: `wave8-v5/componente-22`.
> Titulo: `Wave 8 v5.0 · C22 — Reativação da Tela de Assinatura`
> Cole o corpo abaixo.

---

## Resumo

Reativa a tela de assinatura no fluxo de escaneamento (RF-028, RN-014) —
1ª entrega da Wave 8 v5.0 e da v5.0. O frontend de assinatura foi
descontinuado no redesenho do C10 v4.0 (commit `e4d543b`); o backend
permaneceu integralmente operacional. Esta entrega reconstrói a UI
(recuperada via arqueologia de Git, commit-fonte `6add246`) e a religa ao
`/escanear` — **zero alteração em backend, banco, RLS, migrations ou
máquina de estados**.

**Fluxo (regra única — ADR-164):** após identificar uma prova (câmera C10
ou digitação manual C19), se o usuário logado é o próximo ator habilitado
(`transicoes_permitidas` não-vazio), o modal de assinatura abre
automaticamente; senão, navega para `/provas/[id]`.

## Gate 1 / Gate 2

- **Gate 1** (commit `f44bc3f`): arqueologia + análise read-only.
  Descobriu que **C20 (animações) e C21 (migração) não existem no código**
  — Mario decidiu mantê-los pendentes e prosseguir.
- **Gate 2**: 6 commits atômicos (`8d5b611`..`64f82d9`).

## Decisões

- **ADR-163** — 11 decisões de design.
- **ADR-164** — ator-errado in-scope abre `/provas/[id]` (revisão de
  RN-014/RF-006/Cenário 4, escalada e com chancela explícita do Mario).

## Arquivos

**Novos:** `components/assinatura/{AssinaturaModal,CapturaAssinatura}.tsx`
+ `assinatura.module.css`; `lib/assinatura/helpers.ts` +
`__tests__/helpers.test.ts`.
**Modificados:** `escanear/page.tsx` (integração leve — 2 pontos
pós-identificação); `hooks/useExecutarTransicao.ts` (reativado, órfão
desde o C10 v4.0; + campo `status`).
**Sem alteração:** backend, C10/C19/C11/C06/C08/C12/C16,
`contrato-c12.md`, schema/migrations/RLS/enums.

## Validação técnica

- `npx tsc --noEmit`: exit 0
- `npx next build`: 13/13 páginas · `/escanear` 15.9 kB / 220 kB (era
  8.31 / 210 — `react-signature-canvas` entra no bundle)
- `npx next lint`: 0 warnings, 0 errors
- `npx vitest run`: **222 testes** (205 + 17 novos), 0 regressão
- Advisors MCP (security + performance): idênticos ao baseline — o C22
  não toca o banco

## Definition of Done global (Backlog §2)

- [x] 1. Code review — **este PR habilita a revisão** (≥1 revisor humano).
- [x] 2. Testes unitários da lógica de negócio — `helpers.ts` coberto por
  17 testes Vitest (cobertura efetiva 100% do módulo puro). Backend: N/A
  (C22 é frontend-only).
- [ ] 3. Testes de integração em staging — smoke E2E manual
  (`smoke-validation.md`, 10 cenários). **Pendente (Mario).**
- [x] 4. Migrations — N/A (zero migrations; C22 não toca o banco).
- [~] 5. Validado contra as US (US-018, US-019) — código verificado;
  validação funcional via smoke.
- [~] 6. Validado contra a Matriz de Acesso — `/escanear` universal; a
  checagem por prova é via `transicoes_permitidas` (backend). Teste
  manual = smoke cenário 4.
- [~] 7. Sem erros no console — build/lint limpos; checagem completa no
  smoke (item 11).
- [x] 8. Documentação interna atualizada — CHANGELOG, DECISIONS, CLAUDE,
  analysis, visual-guide, smoke-validation.
- [x] 9. RLS verificada/versionada — N/A (C22 não cria/altera RLS);
  advisors confirmam RLS inalterada.
- [~] 10. Animações com prefers-reduced-motion — implementado
  (`useReducedMotion` + `@media`); checagem funcional no smoke (item 11).

Legenda: `[x]` feito · `[~]` código feito, validação funcional via smoke ·
`[ ]` pendente.

## Critérios de aceitação (§6.3)

Os critérios de nível de código (tsc, build, lint, testes, zero backend
touch, advisors, integração C10/C19, ARIA/focus trap) estão
**comprovados** — ver Validação técnica. Os critérios **funcionais**
(modal aparece/não-aparece, anti-enumeração byte-a-byte, race 409, prova
legacy, performance <500ms, axe, navegação por teclado) exigem o app
rodando com backend + sessão autenticada + provas-fixture — cobertos pelo
**smoke E2E manual** (`smoke-validation.md`). Limitação detalhada em
`analysis.md` §A.5.

## Pendências antes do merge

- Smoke E2E manual dos 10 cenários (`docs/wave8-v5-c22/smoke-validation.md`).
- Auditoria sênior independente.
- Screenshots para o `visual-guide.md`.
- Redeploy do backend no Railway (estava fora do ar — "Application not
  found").
- Herança da Wave 3: rate limit C19 (ADR-145), CI/CD pós-Wave 3 (ADR-156).

## Test plan

- [x] `tsc --noEmit` exit 0
- [x] `next build` 13/13 páginas
- [x] `next lint` 0 warnings/errors
- [x] `vitest run` 222 testes, 0 regressão
- [ ] Smoke E2E manual — 10 cenários (`smoke-validation.md`)
- [ ] axe DevTools — sem violações críticas (smoke item 11)
- [ ] Verificação mobile ~360px (smoke item 11)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
