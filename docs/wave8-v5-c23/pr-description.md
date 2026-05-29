# PR — wave8-v5/c23: responsividade mobile da página de escaneamento

**Base:** `development` · **Head:** `wave8-v5/componente-23`
**Abrir em:** https://github.com/3studioagn/Prova_Digital/pull/new/wave8-v5/componente-23

---

## Resumo
- Responsividade mobile da página `/escanear` (C10 câmera + C19 manual) e do modal de assinatura (C22) — RF-029, RNF-013, US-020.
- Estratégia **desktop-first com overrides** (ADR-166): o design desktop já aprovado fica **intocado**; todo o mobile vive em `@media`.
- Frontend-only: CSS Modules + tokens + `viewport-fit=cover` + 2 atributos HTML não-invasivos. Zero backend/RLS/migration.

## Mudanças (5 fontes)
- `globals.css`: tokens `--touch-target-min: 44px` + `--safe-*` (env safe-area).
- `layout.tsx`: `export const viewport` com `viewportFit: "cover"` (sem bloquear zoom — WCAG 1.4.4).
- `escanear.module.css` (+103, só @media): touch targets ≥44px (`.tab` 42→44, `.linkButton`), CTAs full-width, contraste AA mobile, landscape de telefone (2 colunas + preview quadrado), safe areas.
- `escanear/page.tsx`: `inputMode="text"` + `enterKeyHint="search"` no input do C19.
- `assinatura.module.css` (+53, só @media): safe areas, `90dvh`, rodapé sticky em landscape (one-handed).

## Sem alteração (diff vazio)
- Lógica de C10/C19/C22, `useScanner`, `helpers.ts`.
- Backend, RLS, migrations, enums, máquina de estados, `contrato-c12.md`.
- Shell do dashboard, C06/C08/C11/C12/C16, Wave 1 (RBAC).
- **Desktop ≥1024px: byte-a-byte preservado.**

## Validação
- `tsc --noEmit` 0 · `next lint` 0 · `vitest run` **237** (0 regressão) · `next build` **13/13**.
- `/escanear`: 16 kB / 221 kB First Load (era ~15.9/220).
- Advisors MCP idênticos ao baseline; `alembic_version=013`, enums 17/6, trigger + 12 RLS preservados.

## Definition of Done (Backlog §2)
- [ ] Code review por ≥1 revisor humano.
- [x] Vitest 237 sem regressão (C23 é CSS/atributos — sem nova lógica TS; meta 80% backend N/A).
- [ ] Smoke E2E manual em dispositivos físicos Android + iOS (`docs/wave8-v5-c23/smoke-validation.md`).
- [x] Validado contra US-018/019/020 + RF-029 + RNF-013 (estático; smoke confirma em campo).
- [x] Matriz de Acesso: escanear = universal, sem mudança RBAC.
- [x] Sem erros no console (build/lint limpos).
- [x] Docs atualizados (CHANGELOG, DECISIONS ADR-166, CLAUDE, analysis, visual-guide, smoke-validation).
- [x] Migrations/RLS: N/A (zero alteração de banco).
- [x] prefers-reduced-motion: animações existentes degradam (nenhuma nova).

## Pendências antes do merge `development → main`
- Smoke E2E manual + screenshots no `visual-guide.md`.
- Auditoria sênior independente do C23.
- Herança Wave 3/C22: rate limit C19 (ADR-145), CI/CD (ADR-156), redeploy Railway.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
