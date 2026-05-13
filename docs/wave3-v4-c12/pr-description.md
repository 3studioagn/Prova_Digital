# Wave 3 v4.0 / C12 — Timeline Visual com 4 Rotas e Laminacao (FECHA A WAVE 3)

> Conteúdo pronto para colar no corpo do PR.
> URL para abrir: <https://github.com/3studioagn/Prova_Digital/pull/new/wave3-v4/componente-12>
> Base: `development` · Head: `wave3-v4/componente-12`

---

## Resumo

4ª e última entrega da Wave 3 v4.0 (de 4 — C10, C19, C11 já entregues).
Fechando o C12, a Wave 3 inteira fica pronta para merge `development → main`.

**Frontend-only** — zero touch em backend, RLS ou migrations.

- Timeline visual reformulada com suporte completo às 4 rotas v4.0 +
  legacy v3.0 (PADRAO/DIRETA renomeadas para "Matriz"/"Filial" — Decisão
  11.1, supersede ADR-126) + rota=NULL com heurística baseada em
  `vendedor_localizacao` (Decisão 11.2)
- Bloco visual destacado "Etapa de laminação" envolvendo nós adjacentes
- 3 contextos do motorista com badges textuais
- Múltiplos ciclos empilhados + estados pendentes (futuros) renderizados
- Card transversal de cancelamento + badge "Concluída" no terminal
- A11y AA completa + `useReducedMotion` (RNF-010) com dupla defesa

## Decisões de design (Gate 1 — 11 escaladas)

Documento completo em [docs/wave3-v4-c12/analysis.md](docs/wave3-v4-c12/analysis.md).
Mario aprovou 1-10 em bloco; Decisão 11 reformulada em troca de
mensagens (3 sub-itens 11.1/11.2/11.3).

## Mudanças

### Adicionado (código de produção)

- `frontend/src/lib/timeline-builder.ts` (240 LOC) — pipeline puro
  `buildTimeline(prova, movimentacoes) -> BuiltTimeline`
- Helpers em `frontend/src/lib/types/prova.ts` (+208 LOC):
  `ContextoMotorista` type + `contextoMotorista` + `ESTADOS_LAMINACAO` +
  `isInLaminationBlock` + `ROTA_ETAPAS` + `LEGACY_ROTA_PADRAO` +
  `LEGACY_ROTA_DIRETA` + `getRotaEtapas` + `getRotaLabel`
- `Timeline.tsx` refactor (273 → 410 LOC) + `timeline.module.css` (211 →
  372 LOC) com 5 subcomponentes internos + 3 SVG icons inline

### Modificado

- `ROTA_LABELS["PADRAO"]="Matriz"` + `ROTA_LABELS["DIRETA"]="Filial"`
  (Decisão 11.1, ADR-158 — supersede ADR-126). Propaga para detalhe +
  listagem + relatórios + CSV.

### ADRs novos (4)

- **ADR-158** — Renomeação global PADRAO→"Matriz" / DIRETA→"Filial"
- **ADR-159** — Heurística `vendedor_localizacao → rota visual` para
  rota=NULL (client-side, sem backfill)
- **ADR-160** — Bloco visual "Etapa de laminação" agrupa nós adjacentes
- **ADR-161** — Nós pendentes (futuros) renderizados com dot outline
  cinza + conector tracejado

## Validação

- `npx tsc --noEmit` exit 0
- `npx next build` 13/13 páginas; `/provas/[id]` em **16.1 kB / 214 kB**
  (era 11.4/209 — overhead +4.7 kB pelo redesign + framer-motion expandido)
- `npx vitest run` **163 passed** (era 98 + 65 novos):
  - 45 novos em `prova.test.ts` (helpers + Decisões 11)
  - 20 novos em `timeline-builder.test.ts` (4 rotas v4.0 + 5 legacy +
    múltiplos ciclos + cancelamento + 3 contextos + edge cases)
- MCP `get_advisors security` idêntico ao baseline pós-C11
- Smoke programático no preview Next: `/login` renderiza sem erros
  (0 console errors, 0 server errors)

## Definition of Done

- [x] Implementação alinhada com decisões de design aprovadas
- [x] Acessibilidade AA (ARIA + reduced motion)
- [x] Testes unitários cobrindo helpers + builder
- [x] tsc + next build OK; sem regressão Vitest
- [x] Sem mudança em backend / RLS / migrations
- [x] Documentação atualizada (CHANGELOG, DECISIONS, CLAUDE.md)
- [x] Smoke validation criado ([docs/wave3-v4-c12/smoke-validation.md](docs/wave3-v4-c12/smoke-validation.md))
- [ ] Smoke E2E manual pelo Mario (depois do merge — 18 cenários)
- [ ] Validação com leitor de tela (VoiceOver/NVDA)

## Test plan

- [ ] **Cenário 1** — Rota Matriz em andamento: badge "Rota: Matriz",
  current com pulse, pendentes em cinza outline
- [ ] **Cenário 5** — Múltiplos ciclos: Ciclo 1 em tampão + Ciclo 2
  atual com separador "↻ reinício de ciclo"
- [ ] **Cenário 6** — Legacy PADRAO mostra badge "Matriz"; DIRETA mostra
  "Filial" (Decisão 11.1)
- [ ] **Cenário 7** — Rota=NULL + vendedor FILIAL → label "Filial" via
  heurística
- [ ] **Cenário 8** — Cancelada: card vermelho + nó cinza terminal +
  motivo
- [ ] **Cenário 9** — Terminal: badge "Concluída" + check verde
- [ ] **Cenário 11** — Reduced motion: pulse desliga
- [ ] **Cenário 12** — Leitor de tela anuncia label + fase + ator
- [ ] **Cenário 17** — Listagem + relatórios mostram "Matriz"/"Filial"
  para legacy (consistência)

## Pendências para PR `development → main` (Wave 3 inteira)

Herdadas:

1. Rate limit backend `/scan` (ADR-145 do C19)
2. Benchmarks `/transicoes` (ADR-153/157 do C11)
3. CI/CD pós-Wave 3 com `INTEGRATION_DATABASE_URL` (ADR-156)

Específicas do C12:

4. Smoke E2E manual (`smoke-validation.md` — cenários 2/3/4 SKIP em
   produção por falta de fixtures Lam.*)
5. Validação leitor de tela (VoiceOver/NVDA)
6. axe-core manual em browser real
7. Decisão R-12: filtros C07 com duplicação visual (Matriz×2, Filial×2)
   pós-Decisão 11.1

## FECHA A WAVE 3 v4.0

Após merge deste PR, a Wave 3 v4.0 fica completa em `development`.
Próximo passo: revisão de wave (auditoria independente recomendada) +
merge `development → main`.
