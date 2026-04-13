# Wave 3 — Lote B — Closeout

**Escopo:** Componente 12 — Timeline Visual de Estagios.
**Data:** 2026-04-13.
**Status:** COMPLETO — aguardando aprovacao final.

---

## 1. Checklist DoD — Componente 12 (Timeline Visual de Estagios)

| # | Criterio (DoD global) | Status | Evidencia |
|---|---|---|---|
| 1 | Code review | Aguardando | Revisao pelo Mario |
| 2 | Testes unitarios >= 80% cobertura | N/A backend (zero mudanca); frontend validado via tsc+lint+build | 389 testes backend passando |
| 3 | Testes de integracao passando | Regressao zero | 389 passed, 0 failed, 1 warning pre-existente |
| 4 | Migrations aplicadas e versionadas | N/A | Zero migrations (100% frontend) |
| 5 | Validada contra criterios US-011 | Estruturalmente | 5 criterios mapeados na implementacao (ver secao 2) |
| 6 | Sem erros no console/logs | OK | `preview_console_logs`: vazio; `preview_logs`: vazio |
| 7 | Documentacao atualizada | OK | CHANGELOG (1 entrada), DECISIONS (ADR-087, 6 decisoes), CLAUDE.md |
| 8 | Policies RLS versionadas | N/A | Zero mudancas RLS |

---

## 2. Criterios de aceitacao US-011 — mapeamento

| # | Criterio | Como foi atendido |
|---|---|---|
| 1 | A timeline exibe todos os estagios percorridos, incluindo ramificacoes | `buildTimelineNodes` gera um no por movimentacao + no implicito "Criada". Rota padrao (6+ nos) e rota direta (4 nos) produzem sequencias distintas naturalmente |
| 2 | Cada etapa concluida mostra responsavel e data/hora | Cada no exibe `usuario_nome`, `SETOR_LABELS[usuario_setor]` e `formatDateTime(created_at)` com data+hora pt-BR |
| 3 | Reprovacoes sao exibidas com motivo e destaque visual | No com `isReprovacao=true` recebe classe `.nodeReprovacao` (dot + texto em `--color-danger`), callout `.nodeMotivo` com fundo vermelho transparente |
| 4 | A rota seguida (padrao ou direta) e indicada | No APROVADA_PELO_VENDEDOR exibe badge `.rotaBadge` com `ROTA_LABELS[rota_no_momento]` |
| 5 | A etapa atual e destacada visualmente | No com `isCurrent=true` recebe classe `.nodeCurrent` (glow box-shadow), badge "Atual" em `.currentBadge`, e `motion.div` com animacao de pulso infinita |

---

## 3. Cobertura de testes

| Aspecto | Resultado |
|---|---|
| Backend `pytest` | **389 passed**, 1 warning (pre-existente em `test_jwt.py`) |
| `tsc --noEmit` | **Limpo** (0 erros) |
| `next lint` | **Limpo** (0 warnings) |
| `next build` | **OK** |
| Console errors (dev) | **0** |
| Server errors (dev) | **0** |

### Bundle size

| Pagina | Size | First Load JS | Nota |
|---|---|---|---|
| `/provas/[id]` | 46 kB | 204 kB | +framer-motion (~35 kB delta). Aceitavel |
| `/escanear` | 11.4 kB | 161 kB | Inalterado |
| Demais paginas | — | — | Inalteradas |

---

## 4. Arquivos criados

| Arquivo | Linhas | Descricao |
|---|---|---|
| `frontend/src/app/(dashboard)/provas/[id]/Timeline.tsx` | 193 | Componente visual: `buildTimelineNodes` + `groupByCycle` + renderizacao + Framer Motion |
| `frontend/src/app/(dashboard)/provas/[id]/timeline.module.css` | 154 | CSS Module da timeline (nos, conectores, badges, motivo, empty/fallback) |
| `WAVE3_LOTE_B_ANALYSIS.md` | ~280 | Plano do Lote B (11 secoes) |
| `WAVE3_LOTE_B_CLOSEOUT.md` | — | Este arquivo |

---

## 5. Arquivos modificados

| Arquivo | O que mudou |
|---|---|
| `frontend/src/app/(dashboard)/provas/[id]/page.tsx` | Import `Timeline` + `STATUS_LABELS` removido do import (nao mais usado diretamente). Bloco `timelineList` (`<ul>` placeholder, ~30 linhas) substituido por `<Timeline movimentacoes={movimentacoes} prova={prova} />` (1 linha) |
| `frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css` | Removidas 8 classes de timeline do placeholder (~55 linhas): `timelineEmpty`, `timelineHint`, `timelineList`, `timelineItem`, `timelineHeader`, `timelineStatus`, `timelineDate`, `timelineMeta`, `timelineMotivo`. Preservadas: `timelineCard`, `timelineTitle` |
| `frontend/package.json` | +1 dependencia: `framer-motion@^12.38.0` |
| `frontend/package-lock.json` | Atualizado |
| `CHANGELOG.md` | Entrada do Lote B |
| `DECISIONS.md` | ADR-087 (6 decisoes: componente extraido, buildTimelineNodes puro, no implicito Criada, agrupamento por ciclo, Framer Motion stagger, CSS Module separado) |
| `CLAUDE.md` | Wave 3 status "LOTES A+B COMPLETOS", estrutura de pastas (+Timeline.tsx, +timeline.module.css), package.json desc |

---

## 6. Evidencias de integracao com Lote A e Waves anteriores

| Aspecto | Impacto | Evidencia |
|---|---|---|
| Schema Alembic | **0 alteracoes** | `alembic_version` permanece `009` |
| Endpoints Wave 2+3 | **0 alteracoes** | 26 endpoints intactos |
| `useProvaDetail` hook (Wave 2 C08) | **0 alteracoes** | Consome `movimentacoes` e `prova` como antes |
| `MovimentacaoResponse` (Wave 2) | **0 alteracoes** | Tipo consumido, nao modificado |
| `STATUS_LABELS`, `ROTA_LABELS` (Wave 2) | **0 alteracoes** | Consumidos pelo Timeline, nao modificados |
| Layout dashboard | **0 alteracoes** | Zero mudancas em `layout.tsx` |
| Pagina detalhe (page.tsx) | **Delta minimo** | Apenas import + 1 linha JSX substituindo ~30 linhas |
| RLS | **0 alteracoes** | 12 policies intactas |
| CSS global | **0 alteracoes** | `globals.css` intocado; design tokens consumidos via var() |

---

## 7. Contratos expostos para o Lote C

| Contrato | Para quem | Descricao |
|---|---|---|
| `<Timeline>` renderiza `CANCELADA` | C13 | No com `isCancelamento=true`: dot cinza, texto cinza. C13 so precisa criar a movimentacao — a timeline renderiza |
| `<Timeline>` renderiza ciclos multiplos | C14 | `groupByCycle()` agrupa por `movimentacao.ciclo`. Separador "Ciclo N" aparece quando ha 2+ ciclos. C14 so precisa incrementar `ciclo_atual` — a timeline renderiza |
| `<Timeline>` aceita null `movimentacoes` | C13/C14 | Fallback gracioso "Nao foi possivel carregar o historico" |
| `useProvaDetail.reload()` | C13/C14 | Apos cancelamento ou reinicio, chamar `reload()` refaz o fetch e a timeline re-renderiza automaticamente |

---

## 8. Riscos residuais e pontos de atencao para o Lote C

| # | Item | Nota |
|---|---|---|
| 1 | **Verificacao visual com dados reais** | A pagina `/provas/[id]` requer autenticacao. A timeline foi validada via build+tsc+lint, mas a verificacao visual com movimentacoes reais depende de smoke test em producao com usuario autenticado |
| 2 | **Bundle size** | `/provas/[id]` subiu para 46 kB / 204 kB FL JS (delta ~35 kB de framer-motion). Aceitavel, mas se Lote C adicionar mais deps ao mesmo route segment, monitorar |
| 3 | **B-02 permanece** | `npm audit` 4 high em `next@14.2` — debito pre-existente, TODO Wave 6 |
| 4 | **No implicito "Criada"** | O no inicial usa `usuarioNome: "3Studio"` (aproximacao, pois `ProvaResponse` nao inclui quem criou). Suficiente para o caso de uso |

---

## 9. Metricas consolidadas

| Aspecto | Pos-Lote A | Pos-Lote B | Delta |
|---|---|---|---|
| **Testes backend** | 389 | **389** | 0 |
| **Rotas backend** | 26 | **26** | 0 |
| **Rotas frontend** | 8 | **8** | 0 |
| **Policies RLS** | 12 | **12** | 0 |
| **alembic_version** | 009 | **009** | 0 |
| **Deps npm (prod)** | 10 | **11** | +1 (framer-motion) |
| **ADRs** | 086 | **087** | +1 |
| **Bundle `/provas/[id]`** | ~11 kB | **46 kB** | +35 kB (framer-motion) |
| **Ruff backend** | limpo | **limpo** | — |
| **tsc --noEmit** | limpo | **limpo** | — |
| **next lint** | limpo | **limpo** | — |
| **next build** | OK | **OK** | — |

---

## 10. Proximo passo — Lote C

O Lote C (Componentes 13 Cancelamento + 14 Reinicio de Ciclo) so sera iniciado
apos o **"GO LOTE C"** explicito do Mario. Ate la, nenhuma analise, planejamento
ou codigo dos C13/C14 sera produzido.
