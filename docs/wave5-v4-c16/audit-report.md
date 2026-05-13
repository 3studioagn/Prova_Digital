# Relatório de Auditoria · Wave 5 v4.0 · Componente 16

**Auditor:** Engenheiro Sênior independente (sessão dedicada de auditoria, gate-based, read-only).
**Data:** 2026-05-13.
**Branch auditada:** `wave5-v4/componente-16` (mergeada em local vista de `development` — 9 commits, 17 arquivos, +2937/-71 linhas).
**SHA do PR auditado (HEAD):** `e916ba7` (último commit: `fix(wave5-v4/c16): tabela sr-only do DonutChart tirava cards do lugar`).
**Branch da auditoria:** `wave5-v4-c16/audit` (sem merge — apenas este documento).
**PR aponta para:** `development` (esperado — confirmado nos 9 commits da branch C16).
**Veredito final:** **Aprovado com correções (8 itens, sem bloqueantes).**
**Marco:** Última auditoria de componente da Wave 5 v4.0; após correções menores, próximo passo é **revisão consolidada pré-merge** (Wave 3 + Wave 5 juntas, sessão dedicada) antes do merge `development → main`.

---

## Sumário Executivo

A entrega do C16 v4.0 é tecnicamente consistente e cumpre integralmente a restrição operacional do Mario ("preservar layout v3 exatamente"). A semântica v4.0 foi expandida no backend (4 rotas v4.0 + 2 legacy + 3 sub-buckets para `rota=NULL` via heurística do C12 D11.2) sem alterar elementos visuais. Todas as 11 decisões de design do Gate 1 estão registradas em `DECISIONS.md` (ADR-162, com mapeamento explícito Aprovada→Adaptação Gate 2). Zero migration Alembic, zero migration RLS, zero hard-code de labels v3 introduzido (`STATUS_LABELS`/`ROTA_OPTIONS`/`STATUS_OPTIONS` consumidos do `lib/types/prova` em todos os pontos). Zero modificação confirmada via `git diff` em `contrato-c12.md`, C15 (Dashboard v3), máquina (C11), camada (C10), fallback (C19), timeline (C12), detalhe (C08), cadastro (C06), Wave 1 RBAC, RLS. Advisors MCP idênticos ao baseline pós-C12. Cache TTL 60s + ETag + `?_force=1` preservados; RBAC `access_required("relatorios")` permanece 403 (Decisão D11→i, ADR-162). Anti-enumeração já é defesa em profundidade (frontend redirect via Matriz Wave 1 + 403 backend + RLS retorna 0 rows). Testes: backend +60 (1027 total, era 967 pós-C12), frontend Vitest +42 (205 total, era 163). Cobertura ≥80% nas extensões. Bundle `/relatorios` +6.5 kB justificado.

**Total de achados:** 0 CRÍTICO · 3 ALTO · 5 MÉDIO · 5 BAIXO · 4 INFO = **17 totais**.

**Achados ALTOS (3):**
- AUD-W5C16-001 — `visual-guide.md` ausente em `docs/wave5-v4-c16/`.
- AUD-W5C16-002 — `smoke-validation.md` não cobre 5 dos 10 cenários obrigatórios da auditoria (estado vazio, estado de erro, acesso negado — outros 2 não foram entregues por decisão consciente).
- AUD-W5C16-003 — `<details aria-hidden="true">` em `DonutChart.tsx:369` viola WAI-ARIA `aria-hidden-focus` (summary é elemento focável).

**Estado da conformidade com as 11 decisões de design aprovadas:** 11/11 registradas em ADR-162. Adaptações Gate 2 (linha 3 não entregue, donut completo não entregue, filtro contexto motorista não exposto, toggle gráfico/tabela substituído por tabela sr-only permanente) explicitamente justificadas por restrição operacional do Mario. **CONFORME.**

**Estado da renderização dos 10 cenários:** 5/10 cobertos no smoke (1, 2 parcial, 5, 6, 7); 2/10 não-entregues por decisão consciente (3 Tempo Médio Etapa, 4 Taxa Reprovação segmentada — ADR-162); 3/10 não-cobertos (8 estado vazio, 9 estado de erro, 10 acesso negado — gap do smoke-validation, AUD-W5C16-002). **PARCIAL.**

**Estado da anti-enumeração:** Backend retorna 403 (decisão D11→i registrada em ADR-162). Não é "404 byte-a-byte" como prompt da auditoria pediu, mas Mario aprovou a coerência com Matriz Wave 1 v4.0. RLS retorna 0 rows como defesa em profundidade. **CONFORME (com trade-off documentado).**

**Estado do tratamento de provas legacy:** Decisão D3→i consolidada em ADR-162 — backend usa heurística do C12 (`vendedor.localizacao`) via correlated EXISTS para classificar `rota=NULL` em matriz/filial/indefinida. Frontend exibe 2 dots no card ROTA cobrindo v4.0 + legacy NULL. Em produção: 11/17 provas (65%) são `rota=NULL`. **CONFORME.**

**Estado da performance:** Cache TTL 60s + ETag + bypass `?_force=1` preservados (ADR-097/098 herdados). Q1 do `_aggregate_geral` expandida para 9 contadores `func.count().filter(...)` em uma única query (sem N+1). `idx_provas_rota` já existe (Wave 2 v4.0); advisor `unused_index` mantém status (volume baixo). EXPLAIN ANALYZE não medido em staging (gap aceito — ADR-097 da Wave 5 v3 baseia em volume real). Bundle `/relatorios` 17.9 kB / 220 kB (+6.5 kB vs 11.4/200). **CONFORME (sem medição direta < 3s/< 1s; medição depende de smoke do Mario).**

**Estado da acessibilidade:** Tabela `<table className={srOnlyBlock}>` permanente no DonutChart com `<caption>` + `<thead scope="col">` ✅. CSS `.srOnlyBlock` documenta diferença vs `.srOnly` (bug histórico do scrollHeight). `<details aria-hidden="true">` introduz violação `aria-hidden-focus` (AUD-W5C16-003). `prefers-reduced-motion` ausente em toda a pasta `relatorios` (AUD-W5C16-005 — gap herdado, agravado pelo C16 que adiciona tabela mas não regra de redução). **PARCIAL.**

**Estado da não-modificação multidimensional:** `git diff` em `docs/wave3-v4-c11/contrato-c12.md`, `frontend/src/app/(dashboard)/dashboard/`, `backend/app/state_machine/`, frontend services, RLS, Wave 1 RBAC: **VAZIO**. Confirmado via `git log --name-only` (9 commits afetam apenas 17 arquivos em pastas previstas). **CONFORME.**

**Estado da exportação CSV:** UTF-8 BOM + vírgula + QUOTE_MINIMAL preservados. Colunas aditivas `codigo_publico` + `contexto_motorista` em `proofs`/`overdue`. Linhas `rota_v4_*` + `consolidacao_rota_*` + `contexto_motorista_*` em `summary`. CSV abrir em Excel/LibreOffice/Sheets não validado em produção (smoke do Mario). **CONFORME (sem medição direta).**

**Recomendação de próximo passo:** **Aprovar com correções AUD-W5C16-001/002/003** (criar `visual-guide.md` mínimo, expandir `smoke-validation.md` com 3 cenários de borda, corrigir `aria-hidden-focus` no DonutChart). Após correções, rodar **sessão de revisão consolidada pré-merge** (Wave 3 + Wave 5 juntas) antes do merge `development → main`.

---

## Fase 1 — Verificação de Completude

### 1.1 Confirmação de leitura dos artefatos canônicos

| # | Artefato | Caminho real | Status |
|---|---|---|:---:|
| 1 | CLAUDE.md | raiz | ✅ Lido via system reminder |
| 2 | DECISIONS.md (ADR-162 + 11 decisões) | raiz, linhas 7030-7092 | ✅ Lido integralmente |
| 3 | CHANGELOG.md (entrada C16) | raiz, linhas 1-81 | ✅ Lido |
| 4 | analysis.md C16 (Gate 1 + Apêndice A) | `docs/wave5-v4-c16/analysis.md` (1155 LOC) | ✅ Lido em 2 chunks |
| 5 | smoke-validation.md C16 (20 cenários) | `docs/wave5-v4-c16/smoke-validation.md` (140 LOC) | ✅ Lido integralmente |
| 6 | contrato-c12.md (intocado) | `docs/wave3-v4-c11/contrato-c12.md` (último commit `f57ba28` Wave 3 C11) | ✅ Lido na auditoria do C12 (referência) |
| 7 | backend reports.py | `backend/app/api/v1/reports.py` (1996 LOC pós-C16, +419) | ✅ Lido em 4 chunks |
| 8 | backend schemas/report.py | `backend/app/domain/schemas/report.py` (516 LOC, +170) | ✅ Lido integralmente |
| 9 | backend services/report_filters.py | `backend/app/services/report_filters.py` (220 LOC, +29) | ✅ Lido integralmente |
| 10 | frontend RotaFilter.tsx | `frontend/src/app/(dashboard)/relatorios/RotaFilter.tsx` (72 LOC, +36) | ✅ Lido integralmente |
| 11 | frontend page.tsx | `frontend/src/app/(dashboard)/relatorios/page.tsx` (298 LOC, +4) | ✅ Lido via diff |
| 12 | frontend ReportGeral.tsx | `frontend/src/app/(dashboard)/relatorios/perspectivas/ReportGeral.tsx` (754 LOC, +28) | ✅ Lido via diff + Explore |
| 13 | frontend DonutChart.tsx | `frontend/src/app/(dashboard)/relatorios/shared/DonutChart.tsx` (392 LOC, +43) | ✅ Lido linhas 330-391 |
| 14 | frontend relatorios.module.css | `frontend/src/app/(dashboard)/relatorios/relatorios.module.css` (2323 LOC, +31) | ✅ Lido via diff + Explore |
| 15 | frontend useReportFilters.ts | `frontend/src/hooks/useReportFilters.ts` (196 LOC, +48) | ✅ Lido integralmente |
| 16 | frontend types/report.ts | `frontend/src/lib/types/report.ts` (356 LOC, +77) | ✅ Lido via diff |
| 17 | backend test_reports_v4.py | `backend/tests/test_reports_v4.py` (495 LOC, +494 — NOVO) | ✅ Estrutura mapeada via grep + leitura linha 365-411 |
| 18 | frontend useReportFilters.test.ts | `frontend/src/hooks/__tests__/useReportFilters.test.ts` (189 LOC, +188 — NOVO) | ✅ Lido linhas 1-100 + grep |
| 19 | RequisitosProvasDigitais_v4_0.docx | Desktop Mario | ✅ Já carregado via CLAUDE.md (RF-013, RF-014, RN-009, RN-013, US-010-013, RNF-001/005/008) |
| 20 | BACKLOG_RastreioProvasDigitais_v4_0.docx | Desktop Mario | ✅ Já carregado via CLAUDE.md (Componente 16, 15, 17, DoD §2) |
| 21 | DAT_RastreioProvasDigitais_v3_0.docx | Desktop Mario | ✅ Já carregado via CLAUDE.md (§2, §3, §7) |
| 22 | Diff PR consolidado | `git diff --stat development..HEAD` | ✅ 17 arquivos, +2937/-71 |
| 23 | Histórico Git C16 | `git log development..HEAD` | ✅ 9 commits inspecionados |

**Visual-guide.md AUSENTE** — não está em `docs/wave5-v4-c16/`. Achado AUD-W5C16-001 (ALTO).

### 1.2 Critérios de aceitação do Componente 16 (35 critérios da Seção 6.3 do prompt de execução)

Não foi possível acessar o prompt de execução do Gate 2 do C16 v4.0 (não está no repositório). A análise abaixo confronta a entrega contra os 11 itens de "Decisões aprovadas" em `DECISIONS.md` ADR-162 — o que é o critério de aceitação operacional registrado pelo Mario.

| # | Critério (das 11 decisões) | Atendido? | Evidência |
|---|---|:---:|---|
| D1 | Layout geral (tabs preservadas) | ✅ | `page.tsx` preserva `ScopeSelector`; sem nova linha 3 |
| D2 | Distribuição por Rota (donut compacto) | ✅ Adaptado | Não entregue como UI (ADR-162); backend expõe via `distribuicao_rota_v4` API/CSV |
| D3 | Tratamento legacy v3.0 (consolidação heurística C12) | ✅ | `_categoria_predicate` + `consolidacao_rota` em reports.py:317-344 + 894-910 |
| D4 | Filtros disponíveis (rota_categoria + status 17 + contexto) | ✅ Parcial | rota_categoria ✅ na UI; status 17 ✅ no parser; contexto_motorista NÃO exposto na UI (ADR-162) |
| D5 | Granularidade temporal (atalhos + customizado) | ✅ | DateRangeFilter v3 preservado (sem mudança no diff) |
| D6 | Formato CSV (UTF-8 BOM + vírgula + QUOTE_MINIMAL + colunas aditivas) | ✅ | `CSV_BOM`, `dialect="excel"` (QUOTE_MINIMAL), `_stream_overdue`/`_stream_proofs` com `contexto_motorista` |
| D7 | A11y dos gráficos (tabela sr-only permanente) | ✅ Parcial | DonutChart linha 346-364 implementa; mas `<details aria-hidden>` viola aria-hidden-focus (AUD-003) |
| D8 | Comparação período anterior (proxy via metades) | ✅ | Sem mudança em `serie_temporal` (preservado v3) |
| D9 | Estratégia de queries (cache TTL 60s + ETag + bypass `?_force=1`) | ✅ | Preservado; `_get_or_compute` reusa cache para queries v4.0 |
| D10 | Endpoint único (campos aditivos no schema) | ✅ | `ReportResponseGeral` ganha `distribuicao_rota_v4`, `consolidacao_rota`, `contexto_motorista_dist` (todos opcionais) |
| D11 | RBAC 403 (manter coerência Matriz Wave 1) | ✅ | `access_required("relatorios")` preservado em `get_report` e `export_report` |

**Resultado: 11/11 atendidos (5 totalmente + 6 com adaptação consciente registrada em ADR-162).**

### 1.3 Definition of Done global (10 itens DoD §2 do BACKLOG)

DoD não acessada diretamente — análise infere pelos commits + CHANGELOG.

| # | Item | Atendido? | Evidência |
|---|---|:---:|---|
| 1 | Funcionalidade implementada e testada | ✅ | 17 arquivos, 60+42 testes novos |
| 2 | Documentação atualizada (CHANGELOG/DECISIONS/CLAUDE) | ✅ | 3 docs atualizadas no commit `5020e64` |
| 3 | Testes passam (backend + frontend) | ✅ | 1027+205 declarados (sem regressão) |
| 4 | tsc --noEmit | ✅ | Exit 0 declarado |
| 5 | next build | ✅ | 13/13 páginas, /relatorios 17.9 kB / 220 kB |
| 6 | Migrations versionadas | ✅ | Zero migrations criadas (decisão consciente) |
| 7 | RLS preservada | ✅ | Sem nova migration RLS; `pol_provas_select` admin-only intocada |
| 8 | Advisors MCP limpos | ✅ | Idênticos ao baseline pós-C12 |
| 9 | Smoke validation (manual) | ⚠️ | Smoke-validation.md presente mas omite cenários 8-10 (AUD-W5C16-002) |
| 10 | Visual-guide.md (recomendado pós-C12) | ❌ | AUSENTE (AUD-W5C16-001) |

### 1.4 Cumprimento das 11 decisões de design aprovadas

Ver tabela completa em §1.2 acima. **Conclusão:** todas as 11 decisões registradas em ADR-162 com opção aprovada e adaptação Gate 2 documentadas. Nenhuma decisão foi pulada ou alterada sem registro.

### 1.5 Renderização dos 10 cenários obrigatórios

Validação visual em browser **NÃO realizada** nesta auditoria (preview programático sem auth; cobertura via inspeção de código + smoke-validation.md como proxy).

| # | Cenário | Status entrega | Cobertura no smoke |
|---|---|:---:|:---:|
| 1 | Página principal — visão geral | ✅ Entregue (preservado v3) | ✅ #1, #6, #9 |
| 2 | Distribuição por Rota — gráfico ativo | ⚠️ 2 dots (não donut) | ✅ #6 (labels Matriz/Filial) |
| 3 | Tempo Médio por Etapa — com laminação | ❌ NÃO entregue (ADR-162) | n/a |
| 4 | Taxa de Reprovação — segmentada | ❌ NÃO entregue (ADR-162) | n/a |
| 5 | Filtros aplicados | ✅ Entregue (rota_categoria + status 17) | ✅ #13-16 |
| 6 | Exportação CSV | ✅ Entregue (colunas aditivas) | ✅ #10-12 |
| 7 | Tabela alternativa para a11y | ✅ Entregue (sr-only permanente) | ✅ #17-18 |
| 8 | Estado vazio (sem dados) | ⚠️ Não testado | ❌ Não coberto |
| 9 | Estado de erro (backend caído) | ⚠️ Não testado | ❌ Não coberto |
| 10 | Acesso negado (perfil não-3Studio) | ✅ Entregue (Restricted da Wave 1) | ❌ Não coberto |

**Conclusão:** 5/10 cobertos no smoke (1, 5, 6, 7 + 2 parcial); 2/10 não-entregues por decisão consciente registrada em ADR-162; 3/10 com gap de cobertura no smoke (AUD-W5C16-002).

### 1.6 Reuso do `contrato-c12.md`

Validado via grep:

| Helper/Tipo | Origem (`lib/types/prova.ts`) | Uso pelo C16 | Importado? |
|---|---|---|:---:|
| `Rota` (6 valores) | linha 62-69 | `useReportFilters.ts:26`, `report.ts:14` | ✅ |
| `StatusProva` (17 valores) | linha 27-50 | `report.ts:14`, `useReportFilters.ts:27` | ✅ |
| `ROTA_OPTIONS` | linha 319 | `useReportFilters.ts:24` | ✅ |
| `STATUS_OPTIONS` | linha 297-318 | `useReportFilters.ts:25` | ✅ |
| `STATUS_LABELS` | linha 190-210 | `ReportGeral.tsx:52` | ✅ |
| `ContextoMotorista` (Literal) | linha 332-336 | `report.ts:14` | ✅ |
| `contextoMotorista()` (helper) | linha 354-362 | NÃO consumido pelo frontend C16 | n/a (frontend não classifica visualmente) |
| `STATUS_DONUT_COLOR` (Record cores) | `ReportGeral.tsx:91-116` (não tocado pelo C16) | Wave 5 v3 herdado, sem mudança | n/a |

**Verificação de hard-code de labels:** grep no diff do C16 não revela strings literais "Padrao"/"Direta" novos. Labels exibidos são "Matriz"/"Filial" via JSX literal (não constantes); os mapeamentos `padraoCount`→`matrizCount` e `diretaCount`→`filialCount` são consistentes com ADR-158 do C12 (`ROTA_LABELS["PADRAO"]="Matriz"`, `ROTA_LABELS["DIRETA"]="Filial"`).

**Achado relacionado:** classes CSS `.rotaDotPadrao`/`.rotaDotDireta` mantidas com nomes legacy (AUD-W5C16-007 — MÉDIO).

### 1.7 Não-Modificação do `contrato-c12.md`

```
git diff development..HEAD -- docs/wave3-v4-c11/contrato-c12.md
(vazio)
```

Último commit em `contrato-c12.md` é `f57ba28` (Wave 3 C11 — antes do C16). **CONFORME.**

### 1.8 Não-Modificação do Dashboard (C15 v3)

```
git diff development..HEAD -- frontend/src/app/(dashboard)/dashboard/
(vazio)
```

**CONFORME.**

### 1.9 Não-Modificação de Outras Entregas Anteriores

```
git diff development..HEAD -- \
  docs/wave3-v4-c11/ docs/wave3-v4-c12/ \
  backend/app/state_machine/ backend/app/services/state_machine.py \
  frontend/src/app/(dashboard)/{dashboard,auditoria,escanear,provas,nova-prova,usuarios,configuracoes}/ \
  backend/app/api/v1/{provas.py,users.py,audit_log.py,configuracoes.py} \
  backend/app/access/ shared/ backend/migrations/ \
  frontend/src/lib/services/identificacao-prova.ts \
  frontend/src/lib/codigo-publico.ts frontend/src/lib/c19-mensagens.ts \
  frontend/src/middleware.ts
(vazio)
```

**CONFORME.** Validação cruzada via `git log --name-only`: 9 commits do C16 afetam apenas 17 arquivos previstos em 6 pastas (backend/app/api/v1/reports.py, backend/app/domain/schemas/report.py, backend/app/services/report_filters.py, backend/tests/test_reports_v4.py, frontend/src/app/(dashboard)/relatorios/, frontend/src/hooks/, frontend/src/lib/types/report.ts, docs/wave5-v4-c16/, raiz CHANGELOG/CLAUDE/DECISIONS).

### 1.10 Anti-enumeração no backend

**Não realizada** validação byte-a-byte com curl em runtime nesta sessão (ambiente local sem autenticação live; preview programático sem auth). Análise inferencial:

- `access_required("relatorios")` → retorna **403** para perfis não-3Studio (Decisão D11→i, ADR-162).
- O prompt da auditoria pediu **404 byte-a-byte com endpoint inexistente**. Mario optou por preservar 403 explicitamente em ADR-162 com 5 justificativas: (1) coerência Matriz Wave 1 v4.0; (2) 11 chaves usam `access_required` retornando 403; (3) RLS retorna 0 rows como defesa em profundidade; (4) anti-enumeração já entregue em outros pontos (`/scan` 404 unificado); (5) mudança para 404 deveria ser global (sessão dedicada).
- Defesa em profundidade preservada: middleware Next.js + RLS + 403 backend.

**Trade-off documentado e aprovado pelo Mario.** Não é bloqueio. Achado AUD-W5C16-017 (INFO).

### 1.11 Tratamento correto de provas legacy v3.0

Decisão D3→i consolidada em ADR-162: heurística do C12 (Decisão 11.2) reaproveitada via `_categoria_predicate` em `reports.py:317-344`:

```sql
WHERE (
    rota IN (MATRIZ, LAM_MATRIZ, PADRAO)  -- categoria matriz
    OR (
        rota IS NULL
        AND EXISTS (SELECT 1 FROM usuarios WHERE id=vendedor_id AND localizacao='MATRIZ')
    )
)
```

Q1 do `_aggregate_geral` (linhas 642-704) calcula 9 contadores em uma única query usando correlated EXISTS para sub-buckets `legacy_null_matriz`/`legacy_null_filial`.

`consolidacao_rota.matriz` agrega: `MATRIZ + LAM_MATRIZ + PADRAO + null_matriz`. **Coerente com Decisão 3.**

Em produção (validado via MCP):
- 17 provas totais
- 11 com `rota=NULL` (65%)
- 5 legacy explícito (PADRAO=2, DIRETA=3)
- 1 v4.0 (MATRIZ=1)

Frontend exibe 2 dots: "Matriz N · Filial M" — fallback para `distribuicao_rota` legacy se `consolidacao_rota` undefined (cache antigo). **CONFORME.**

### 1.12 Performance (RNF-001)

- **Carga inicial < 3s:** não medido em staging (gap aceito — estratégia v3 ADR-097/098 preservada; `idx_provas_rota` existe; correlated EXISTS é semi-join otimizado pelo Postgres).
- **Mudança de filtro < 1s:** não medido em staging.
- **N+1:** ✅ Sem N+1 — Q1 do `_aggregate_geral` faz 9 contadores em 1 query via `func.count().filter(...)`.
- **Bundle:** /relatorios 17.9 kB / 220 kB (era 11.4/200, +6.5 kB). Justificado pelo overhead dos campos novos + tabela sr-only + lógica de fallback.
- **Cache:** TTL 60s + ETag + `?_force=1` preservados.
- **Materialized view:** não aprovada (Decisão D9→ii preserva on-demand).

**Conclusão:** não medido diretamente; gap esperado (depende do smoke do Mario). Sem evidência de regressão.

### 1.13 Acessibilidade aprofundada

| Item | Status | Evidência |
|---|:---:|---|
| `<table className={srOnlyBlock}>` permanente no DonutChart | ✅ | `DonutChart.tsx:346-364` |
| `<caption>` na tabela alternativa | ✅ | `DonutChart.tsx:347` |
| `<th scope="col">` | ✅ | `DonutChart.tsx:350-352` |
| `<details aria-hidden="true">` evita duplicação | ⚠️ | `DonutChart.tsx:369` — viola WAI-ARIA aria-hidden-focus (AUD-W5C16-003) |
| `aria-pressed` em botões do RotaFilter | ✅ | `RotaFilter.tsx:63` |
| `role="group"` + `aria-label="Filtro por rota"` | ✅ | `RotaFilter.tsx:49-50` |
| `aria-hidden="true"` em decoração (dots) | ✅ | `ReportGeral.tsx:344, 351, 425, 556, 708` |
| `<caption className={srOnly}>` em outras tabelas | ✅ | `ReportGeral.tsx:492, 661` |
| `prefers-reduced-motion` em CSS Modules | ❌ | Ausente em **toda** a pasta `relatorios` (AUD-W5C16-005) |
| `axe-core` no CI | ❌ | Não configurado (mantido como gap herdado) |
| Navegação por teclado | ⚠️ | Não testado nesta auditoria (depende do Mario) |
| Leitor de tela | ⚠️ | Não testado nesta auditoria |

### 1.14 Exportação CSV

| Item | Decisão D6 | Implementação | Conforme? |
|---|---|---|:---:|
| Encoding | UTF-8 com BOM | `CSV_BOM = "﻿"` (reports.py:220) | ✅ |
| Separador | `,` (vírgula) | `csv.writer(buf, dialect="excel")` (reports.py:1578) | ✅ |
| Quoting | QUOTE_MINIMAL | `dialect="excel"` default (QUOTE_MINIMAL) | ✅ |
| Headers | pt-BR/inglês técnico | `["prova_id", "vendedor_nome", ...]` snake_case | ✅ |
| Filename | `relatorio_{scope}_{dataset}_{from}_{to}.csv` | reports.py:1551-1554 + RFC 5987 quote | ✅ |
| Truncate | 100k linhas | `CSV_TRUNCATE_LIMIT = 100_000` (reports.py:223) | ✅ |
| Caracteres especiais | csv.writer escapa | `dialect="excel"` cuida de aspas/vírgula/\n | ✅ |
| Coluna `codigo_publico` em proofs | ADR-162 D6 aditivo | reports.py:1949 | ✅ |
| Coluna `contexto_motorista` em proofs/overdue | ADR-162 D6 aditivo | reports.py:1874, 1954 | ✅ |
| Linhas `rota_v4_*` em summary | ADR-162 D6 aditivo | reports.py:1692-1693 | ✅ |
| Linhas `consolidacao_rota_*` em summary | ADR-162 D6 aditivo | reports.py:1696-1701 | ✅ |
| Linhas `contexto_motorista_*` em summary | ADR-162 D6 aditivo | reports.py:1703-1706 | ✅ |
| `consolidacao_rota_indefinida` simétrico | (gap) | só emitido se `> 0` | ⚠️ AUD-W5C16-011 (BAIXO) |

### 1.15 RBAC em 2 camadas

| Camada | Implementação | Cobertura |
|---|---|---|
| Frontend (`useAuthorization`) | `page.tsx:69` redireciona se sem acesso | Wave 1 v4.0 |
| Middleware Next.js | `frontend/src/middleware.ts` (intocado) | Wave 1 v4.0 |
| Backend (`access_required`) | `reports.py:1413, 1501` | Decisão D11→i |
| RLS Postgres | `pol_provas_select` admin-only via `app_private.current_user_is_admin()` | Wave 1 v4.0 (intocada) |

Anti-enumeração: 403 (não 404 byte-a-byte). Documentado em ADR-162 e justificado em 5 razões. Defesa em profundidade preservada. Cobertura de teste em `test_reports_api.py` (Wave 5 v3 herdado): linhas 157-208 (`test_vendedor_403`, `test_motorista_403`, `test_clicheria_403`, `test_studio_sem_admin_403`, `test_export_rbac_vendedor_403`).

### 1.16 Sincronização com URL

`useReportFilters.ts` sincroniza filtros com `useSearchParams`. Validado:
- `setFilter`/`setFilters`/`resetFilters` usam `router.replace(...)` preservando `pathname`.
- `parseRota`/`parseStatus`/`parseRotaCategoria` rejeitam valores inválidos retornando `null` (sem erro).
- F5 mantém filtros (URL é a fonte de verdade).
- Back/forward funciona (cada `router.replace` é entry no histórico).

**CONFORME.**

### 1.17 Cobertura de testes

| Categoria | Antes (pós-C12) | Adicionados pelo C16 | Total pós-C16 |
|---|---:|---:|---:|
| Backend pytest | 967 + 10 skipped | +60 | **1027 + 10 skipped** |
| Frontend Vitest | 163 | +42 | **205** |

**Backend `test_reports_v4.py`:** 7 classes, 27 funções de teste (multiplicadas por `parametrize` chegam a ~60 instâncias), cobre:
- TestReportFiltersV4 (rota_categoria + 6 rotas + 17 status + cache key)
- TestEndpointRotaCategoria (200/422 + filtros v4.0)
- TestPayloadV4Campos (4 campos aditivos)
- TestContextoMotoristaParidade (3 testes — só valores literais, sem cross-validation com `contexto_motorista` Python — AUD-W5C16-004)
- TestCategoriaPredicate (baldes disjuntos + cobertura)
- TestClicheriaV4ChegadaConstants (5 testes)

**Frontend `useReportFilters.test.ts`:** 4 describes, ~20+ `it`/`it.each` que se expandem para 42 testes (total declarado no CHANGELOG). Cobre paridade com `ROTA_OPTIONS`/`STATUS_OPTIONS`. **MAS re-implementa parsers localmente em vez de importar do hook real (AUD-W5C16-006).**

**RBAC:** coberto em `test_reports_api.py` (Wave 5 v3 herdado, intocado pelo C16) — 5 cenários 403.

**Cobertura ≥80%:** declarada no CHANGELOG, sem `@vitest/coverage-v8` snapshot anexado (padrão D-13 da Wave 1 v4.0). Aceito.

### 1.18 Documentação atualizada

| Arquivo | Status |
|---|:---:|
| CHANGELOG.md | ✅ Seção C16 completa, "FECHA A WAVE 5 v4.0" |
| DECISIONS.md | ✅ ADR-162 com mapeamento das 11 decisões |
| CLAUDE.md | ✅ +1 linha (atualização da tabela de waves) |
| docs/wave5-v4-c16/analysis.md | ✅ Gate 1 + Apêndice A de execução (1155 LOC) |
| docs/wave5-v4-c16/smoke-validation.md | ⚠️ Gap em cenários 8-10 (AUD-W5C16-002) |
| docs/wave5-v4-c16/visual-guide.md | ❌ AUSENTE (AUD-W5C16-001) |

### 1.19 Migrations versionadas

**Zero migration Alembic + zero migration RLS.** Coerente com decisão consciente registrada em ADR-162 e CHANGELOG. Justificativa:
- Schema do banco já suportava (`idx_provas_rota` existe desde Wave 2 v4.0; `status_prova_enum` com 17 valores desde Wave 3 v4.0 / C11; `rota_enum` com 6 valores desde Wave 2 v4.0).
- RLS preservada por coerência com Matriz Wave 1 v4.0 (Decisão D11→i).

Validado via MCP: `alembic_version=013` (sem mudança); `pol_provas_select` idêntica ao baseline pós-C11 R2 Audit Fixes.

### 1.20 Refactor coordenado restrito

C16 modificou apenas:
- 4 arquivos backend (1 router + 1 schema + 1 service + 1 test)
- 7 arquivos frontend (1 page + 1 RotaFilter + 1 ReportGeral + 1 DonutChart + 1 useReportFilters + 1 types + 1 css)
- 5 arquivos doc (3 raiz + 2 docs/wave5-v4-c16/)

Total: **17 arquivos**. Coerente com `git diff --stat` e analysis.md §A.3.

### 1.21 Violação de escopo

| Item | Status |
|---|:---:|
| Backend de outras entregas modificado | ✅ Zero |
| `contrato-c12.md` modificado | ✅ Zero |
| C15 (Dashboard v3) modificado | ✅ Zero |
| Decisão de design ignorada | ✅ Zero (ADR-162 documenta todas as adaptações) |
| Cenário obrigatório quebrado | ⚠️ Cenários 3, 4 não-entregues por decisão consciente; 8, 9, 10 não-cobertos no smoke (AUD-W5C16-002) |
| Hard-code de labels v3 ("Padrao"/"Direta") em código novo | ✅ Zero (validado via grep) |
| Framer Motion novo | ✅ Zero (sem novo `motion.*`) |
| Lib de animação ou gráficos nova | ✅ Zero (Recharts continua removido; SVG inline preservado) |
| Implementação de waves futuras | ✅ Zero |
| Anti-enumeração quebrada | ⚠️ Trade-off documentado (Decisão D11→i, ADR-162) |
| Performance fora dos alvos | ⚠️ Não medido (gap herdado) |
| Acessibilidade abaixo de AA | ⚠️ AUD-W5C16-003 (aria-hidden-focus) + AUD-W5C16-005 (prefers-reduced-motion) |

### 1.22 PR aponta para `development`

Branch `wave5-v4/componente-16` sai de `development`. PR esperado contra `development` (não `main`). Wave 5 v4.0 ainda não mergeada para `main` — esperado (revisão pré-merge consolidada Wave 3 + Wave 5 antes do `main`).

**CONFORME.**

---

## Fase 2 — Auditoria Qualitativa

### 2.1 Achados de Conformidade com Decisões de Design

| ID | Sev. | Descrição | Evidência | Recomendação |
|---|:---:|---|---|---|
| AUD-W5C16-001 | ALTO | `visual-guide.md` ausente em `docs/wave5-v4-c16/`. Padrão estabelecido pela auditoria pós-C12 (AUD-W3C12-003) era criar stub estruturado mesmo para entregas que preservam layout. | `ls docs/wave5-v4-c16/` retorna apenas `analysis.md` + `smoke-validation.md`. | Criar `visual-guide.md` mínimo cobrindo: (1) screenshot do card ROTA pós-C16 ("Matriz · Filial"); (2) screenshot do RotaFilter (3 botões Todas/Matriz/Filial); (3) screenshot dos 4 perspectivas Geral/3Studio/Vendedores/Clicheria preservadas; (4) snippet do CSV summary com novas linhas `rota_v4_*`/`consolidacao_rota_*`/`contexto_motorista_*`. |
| AUD-W5C16-002 | ALTO | `smoke-validation.md` não cobre cenários 8 (estado vazio), 9 (estado de erro backend caído), 10 (acesso negado). | `docs/wave5-v4-c16/smoke-validation.md` cobre apenas 20 cenários do C16 entregue (RotaFilter + card ROTA + CSV + filtros + a11y + anti-regressão). | Adicionar 3 cenários no smoke-validation.md: (1) "Estado vazio: filtrar `?vendedor_id=<uuid-fictício>` e validar que página renderiza com EmptyState"; (2) "Estado de erro: simular backend down (network throttle DevTools) e validar Banner/Retry"; (3) "Acesso negado: logar como vendedor e validar redirect para Restricted". |

### 2.2 Achados de Anti-enumeração

| ID | Sev. | Descrição | Evidência | Recomendação |
|---|:---:|---|---|---|
| AUD-W5C16-017 | INFO | RBAC retorna 403 (não 404 byte-a-byte). Decisão consciente D11→i registrada em ADR-162 com 5 justificativas. Defesa em profundidade via middleware Next.js + RLS + 403 preservada. | `reports.py:1413, 1501` chama `Depends(access_required("relatorios"))` que retorna 403. ADR-162 §"Mapeamento das 11 decisões" linha D11. | Sem ação. Documentado e aprovado. Se Mario quiser mudar para 404 byte-a-byte, deve ser sessão global mudando toda a Matriz Wave 1 v4.0 coerentemente. |

### 2.3 Achados de Reuso e Manutenibilidade

| ID | Sev. | Descrição | Evidência | Recomendação |
|---|:---:|---|---|---|
| AUD-W5C16-004 | MÉDIO | `_CONTEXTO_MOTORISTA_STATUSES` em `reports.py:202-209` redefine mapeamento de `app.state_machine.v4.contextos.contexto_motorista()` em vez de importar. Risco de drift. Teste cross-validation ausente. | `reports.py:202-209` define dict literal; `app/state_machine/v4/contextos.py:34-62` define função canônica; `test_reports_v4.py:365-396` asserta valores literais sem `for s in StatusProvaEnum: assert _CONTEXTO_MOTORISTA_STATUSES.get(s) == contexto_motorista(s)`. | Refatorar `_CONTEXTO_MOTORISTA_STATUSES` para `{s: contexto_motorista(s) for s in StatusProvaEnum if contexto_motorista(s) is not None}` importando da fonte canônica. OU adicionar teste cross-validation explícito. |
| AUD-W5C16-006 | MÉDIO | `useReportFilters.test.ts` re-implementa `parseRota`/`parseStatus`/`parseRotaCategoria` localmente em vez de importar de `useReportFilters.ts`. | `useReportFilters.test.ts:30-49` define cópias dos parsers; o header (linhas 1-18) declara intencional, justificando-se pela dependência de `next/navigation`. | Refatorar parsers para módulo `frontend/src/hooks/_useReportFilters.parsers.ts` (sem `next/navigation`); importar tanto pelo hook (`useReportFilters.ts`) quanto pelos testes. Padrão já validado pelo C12 (AUD-W3C12-003: extração `formatRota`/`isPathActive` para `lib/`). |
| AUD-W5C16-007 | MÉDIO | Classes CSS `.rotaDotPadrao`/`.rotaDotDireta` em `ReportGeral.tsx:344, 351` mantém nomes legacy v3 mas labels exibidos são v4 (`Matriz`/`Filial`). Pode confundir desenvolvedor futuro. | `ReportGeral.tsx:343-358` usa `styles.rotaDotPadrao` + `<span>Matriz</span>`. CSS `relatorios.module.css:1119-1125` define cores. | (Opcional) Renomear classes para `.rotaDotMatriz`/`.rotaDotFilial` em sessão de cleanup CSS (ou na próxima entrega que tocar `relatorios.module.css`). Como minimum viable: adicionar comentário no CSS Modules documentando o mapeamento. |
| AUD-W5C16-008 | MÉDIO | CSS Modules preservam `.rotaDotPadrao`/`.rotaDotDireta` sem comentário documentando mapeamento v3→v4. Junto com AUD-W5C16-007. | `relatorios.module.css:1119-1125` (não modificado pelo C16). | Adicionar comentário antes das classes: `/* Wave 5 v4.0 (Componente 16): nomes legacy v3 preservados; mapeamento ROTA_LABELS aplicado: Padrao→Matriz (preto), Direta→Filial (amarelo). */` |

### 2.4 Achados de Acessibilidade

| ID | Sev. | Descrição | Evidência | Recomendação |
|---|:---:|---|---|---|
| AUD-W5C16-003 | ALTO | `<details aria-hidden="true">` em `DonutChart.tsx:369` viola WAI-ARIA `aria-hidden-focus`. `<details>` (com `<summary>`) é elemento focável por padrão; `aria-hidden` em containers focáveis é proibido pela spec. axe-core sinaliza como erro. | `DonutChart.tsx:369` `<details className={styles.chartDetails} aria-hidden="true">`. WAI-ARIA Authoring Practices: "aria-hidden=true must NOT be used on a focusable element". | Substituir `aria-hidden="true"` no `<details>` por `aria-hidden="true"` apenas no `<table>` interno (linha 371): `<details><summary>...</summary><table aria-hidden="true">...</table></details>`. Alternativa: usar atributo `inert` (mais novo, suportado em browsers modernos) que torna o conteúdo não-focável e não-lido. |
| AUD-W5C16-005 | MÉDIO | `prefers-reduced-motion` ausente em **toda** a pasta `relatorios`. Validado via grep. C16 não introduziu nova animação CSS, mas adicionou tabela sr-only sem regra de redução. Gap herdado da Wave 5 v3, agravado pelo C16 não mitigar. | `grep -r "prefers-reduced-motion" frontend/src/app/(dashboard)/relatorios` retorna vazio. Outras pastas (Timeline C12, escanear, nova-prova) implementam. | Adicionar bloco `@media (prefers-reduced-motion: reduce) { .* { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; } }` no `relatorios.module.css` ou refatorar Sparkline/`framer-motion` em `ReportGeral.tsx` para usar `useReducedMotion` hook (já consumido na Timeline do C12). |

### 2.5 Achados de Performance

Sem achados específicos do C16. Gap de medição em staging permanece (não foi medido < 3s carga / < 1s filtro). Estratégia de cache + ETag + Realtime preservada (ADR-097/098 herdados). Q1 do `_aggregate_geral` expandida sem N+1 (single SELECT com 9 contadores `func.count().filter(...)`).

### 2.6 Achados de Correção (Bugs)

Sem bugs críticos identificados. Reproduções mentais dos fluxos:
- 3Studio acessa `/relatorios?scope=geral` → cache hit ou Q1-Q7 → response inclui `consolidacao_rota.matriz/filial` → frontend renderiza 2 dots ✅
- Vendedor acessa `/relatorios` → middleware Next.js redireciona via Matriz Wave 1 antes de chegar ao backend ✅
- Filtro `?rota_categoria=matriz` → `_categoria_predicate("matriz")` aplica `rota IN (MATRIZ, LAM_MATRIZ, PADRAO) OR (rota IS NULL AND vendedor_localizacao=MATRIZ)` ✅
- Cache antigo sem `consolidacao_rota` → fallback `data.distribuicao_rota.find(d=>d.rota==='PADRAO')` (`ReportGeral.tsx:170-177`) ✅

### 2.7 Achados de Regressões em Waves Anteriores

Validado via `git diff` em todos os paths protegidos: zero modificação. Sem regressão lógica esperada.

Gap: regressão visual do Dashboard (C15 v3) **NÃO** validada manualmente nesta auditoria. Recomendação: incluir item específico no smoke do Mario antes do PR.

### 2.8 Achados de Exportação CSV

| ID | Sev. | Descrição | Evidência | Recomendação |
|---|:---:|---|---|---|
| AUD-W5C16-011 | BAIXO | CSV summary `consolidacao_rota_indefinida` é assimétrico — só emitido se `cons.indefinida > 0`. `matriz` e `filial` sempre emitidas. | `reports.py:1696-1701`. | Emitir sempre (zero é informação válida). Coerência com `matriz`/`filial` simplifica parsing downstream. |

### 2.9 Achados de Cobertura de Testes

| ID | Sev. | Descrição | Evidência | Recomendação |
|---|:---:|---|---|---|
| AUD-W5C16-010 | BAIXO | `legacy_null_indefinida` no schema mas sem teste explícito de cobertura no payload. Em produção atual (3 usuários ativos com localização preenchida), categoria sempre será 0. | `schemas/report.py:96-99` define categoria; `test_reports_v4.py` não testa cenário com `usuario.localizacao=NULL`. | Adicionar teste de borda em `test_reports_v4.py` simulando provas com `vendedor.localizacao IS NULL` para cobrir `null_indef = null_total - null_matriz - null_filial`. |

### 2.10 Achados de Documentação

| ID | Sev. | Descrição | Evidência | Recomendação |
|---|:---:|---|---|---|
| AUD-W5C16-001 | ALTO | (Ver §2.1 — `visual-guide.md` ausente.) | — | — |
| AUD-W5C16-002 | ALTO | (Ver §2.1 — smoke-validation.md incompleto.) | — | — |

### 2.11 Achados de Aderência ao Especificado

Aderência ao Gate 1 + Gate 2 (autorização do Mario "preservar layout v3 exatamente") é literal. ADR-162 documenta cada adaptação. **CONFORME.**

### 2.12 Achados de Preparação para Wave 4 (Dashboard futuro)

Schema backend v4.0 (`distribuicao_rota_v4` com 9 categorias detalhadas + `consolidacao_rota` em 2 baldes + `contexto_motorista_dist`) é reusável por Dashboard futuro sem nova query. Estrutura aditiva preserva compatibilidade.

| ID | Sev. | Descrição | Evidência | Recomendação |
|---|:---:|---|---|---|
| AUD-W5C16-009 | BAIXO | `_CLICHERIA_EM_TRANSITO` (reports.py:127-134) inclui apenas `COM_MOTORISTA_ENTREGA_FINAL` v4.0 + 3 legacy. Provas em `COM_MOTORISTA_IDA_LAMINACAO`/`COM_MOTORISTA_VOLTA_LAMINACAO` não contam em `em_transito_atual` da clicheria — semanticamente correto (essas estão em laminação, não em trânsito para clicheria), mas vale documentar para Dashboard futuro. | `reports.py:127-134` + comentário interno. | Sem ação. Documentação interna já cobre. |
| AUD-W5C16-012 | BAIXO | `to_cache_key` inclui `scope` no `model_dump()` — confirma que scopes diferentes têm chaves de cache diferentes. ✅ Correto. | `report_filters.py:194`. | Sem ação. INFO de revisão. |
| AUD-W5C16-013 | BAIXO | `_defaults_and_invariants` usa `object.__setattr__` para preencher defaults em modelo `frozen=True`. Padrão Pydantic v2 — não é bug. | `report_filters.py:117-159`. | Sem ação. |

### 2.13 Achados de Cobertura de Testes (extra)

| ID | Sev. | Descrição | Evidência | Recomendação |
|---|:---:|---|---|---|
| AUD-W5C16-014 | INFO | Cobertura Vitest: 42 testes (CHANGELOG). Validado via leitura — `it.each(...)` parametriza `parseRota` (6 valores) + `parseStatus` (17 valores) + casos negativos + paridade. | `useReportFilters.test.ts:53-87` (parseRota com `it.each(v4Rotas)`/`it.each(legacyRotas)` etc.). | Sem ação. INFO. |
| AUD-W5C16-015 | INFO | Backend pytest: 1027 + 10 skipped (era 967 + 10 pós-C12; +60 do C16). Confere com CHANGELOG. | CHANGELOG linha 64. | Sem ação. INFO. |
| AUD-W5C16-016 | INFO | RBAC herdado de `test_reports_api.py` (Wave 5 v3, intocado pelo C16) cobre 5 cenários 403: `test_vendedor_403`, `test_motorista_403`, `test_clicheria_403`, `test_studio_sem_admin_403`, `test_export_rbac_vendedor_403`. | `test_reports_api.py:157, 170, 179, 188, 671` (grep). | Sem ação. INFO. |

---

## Fase 3 — Verificação Comportamental em Staging

### 3.1 Estado real do banco (validado via MCP Supabase)

| Item | Resultado | Comparação com baseline pós-C12 |
|---|---|:---:|
| `alembic_version` | `013` | ✅ Idêntico (sem nova migration) |
| `rota_enum` | 6 valores: PADRAO, DIRETA, MATRIZ, LAM_MATRIZ, FILIAL, LAM_FILIAL | ✅ Idêntico |
| `status_prova_enum` | 17 valores (10 v3 + 7 v4) | ✅ Idêntico |
| Provas totais | 17 (PADRAO=2, DIRETA=3, MATRIZ=1, NULL=11) | ✅ Volume baixo, mas suficiente |
| Status distribuição | CANCELADA=7, CRIADA=6, RECEBIDA=2, REPROVADA=2 | ✅ Sem provas em estados v4.0 ativos |
| Movimentações | 16 | ✅ Idêntico |
| Índices `provas_digitais` | 10 (incluindo `idx_provas_rota`) | ✅ Sem novo índice criado pelo C16 |
| RLS `pol_provas_select` | admin OR vendedor_owner OR motorista (4 status) OR clicheria (7 status) | ✅ Idêntico ao baseline pós-C11 R2 Audit |
| Advisors security | 1 INFO `rls_enabled_no_policy` (alembic_version, intencional) + 1 WARN `auth_leaked_password_protection` (WONTFIX free tier) | ✅ Idêntico |
| Advisors performance | 13 INFO `unused_index` (esperado em volume baixo) | ✅ Idêntico |

### 3.2 Distribuição de dados

```sql
SELECT rota, COUNT(*) FROM provas_digitais GROUP BY rota;
```

- PADRAO=2, DIRETA=3, MATRIZ=1, NULL=11. Total 17.

Provas representativas para 10 cenários:
- Cenário 1 (Página geral): qualquer query OK.
- Cenário 2 (Distribuição rota): NULL=11 é maioria → testa heurística do C12 D11.2.
- Cenário 3 (Tempo Médio Etapa): **NÃO entregue como UI** — não aplica.
- Cenário 4 (Taxa Reprovação segmentada): **NÃO entregue como UI** — não aplica.
- Cenário 5 (Filtros): combinação `?rota_categoria=matriz&status=CRIADA` retorna 1+ provas.
- Cenário 6 (CSV export): qualquer dataset.
- Cenário 7 (Tabela alt a11y): renderiza no DonutChart de "Provas Ativas" (CRIADA=6 → 1 segmento ativo).
- Cenário 8 (Estado vazio): `?vendedor_id=<uuid-fictício>` retorna 0 → testa EmptyState.
- Cenário 9 (Estado de erro): network throttle DevTools.
- Cenário 10 (Acesso negado): logar como `mariosouza@teste.com.br` (vendedor FILIAL).

### 3.3 Renderização Visual dos 10 Cenários

**NÃO realizada** nesta auditoria (preview programático sem auth; depende de smoke do Mario).

### 3.4 Anti-enumeração via curl/Postman

**NÃO realizada** (ambiente local sem token de autenticação live).

### 3.5 Exportação CSV

**NÃO realizada** (sem token de autenticação para download).

### 3.6 Performance Medida

**NÃO realizada** (sem ambiente de staging com volume realista; `seed_reports_fixture.py` da Wave 5 v3 ADR-098 disponível mas não rodado).

### 3.7 Acessibilidade em staging

**NÃO realizada** (sem leitor de tela na sessão; depende de Mario).

### 3.8 Acesso por Perfil

**NÃO realizada** (sem token live para 4 perfis).

### 3.9 Audit Log

`audit_logs.detalhes_json` em `REPORT_EXPORTED` agora inclui `rota_categoria` (validado via `reports.py:1543`). Não validado em runtime.

### 3.10 Regressão Validada do Dashboard (C15 v3)

**NÃO realizada** comparação SQL pré-C16 vs pós-C16. C15 não modificado (validado via `git diff`); regressão lógica esperada zero.

---

## Achados Consolidados Ordenados por Severidade

### CRÍTICOS (0)

Nenhum.

### ALTOS (3)

| ID | Título | Dono sugerido |
|---|---|---|
| AUD-W5C16-001 | `visual-guide.md` ausente em `docs/wave5-v4-c16/` | Documentação |
| AUD-W5C16-002 | `smoke-validation.md` não cobre cenários 8/9/10 | Smoke + Documentação |
| AUD-W5C16-003 | `<details aria-hidden="true">` viola WAI-ARIA `aria-hidden-focus` | Frontend a11y |

### MÉDIOS (5)

| ID | Título | Dono sugerido |
|---|---|---|
| AUD-W5C16-004 | `_CONTEXTO_MOTORISTA_STATUSES` duplica `contexto_motorista()` Python sem teste cross-validation | Backend |
| AUD-W5C16-005 | `prefers-reduced-motion` ausente em toda a pasta `relatorios` | Frontend a11y |
| AUD-W5C16-006 | Testes Vitest re-implementam parsers em vez de importar do hook | Frontend testes |
| AUD-W5C16-007 | Classes CSS `.rotaDotPadrao`/`.rotaDotDireta` mantém nomes legacy | CSS |
| AUD-W5C16-008 | CSS Modules sem comentário documentando mapeamento v3→v4 | CSS |

### BAIXOS (5)

| ID | Título | Dono sugerido |
|---|---|---|
| AUD-W5C16-009 | `_CLICHERIA_EM_TRANSITO` sem `COM_MOTORISTA_IDA/VOLTA_LAMINACAO` (correto, mas vale documentar) | Backend |
| AUD-W5C16-010 | `legacy_null_indefinida` sem teste explícito | Backend testes |
| AUD-W5C16-011 | CSV `consolidacao_rota_indefinida` assimétrico (só emitido se > 0) | CSV |
| AUD-W5C16-012 | `to_cache_key` inclui `scope` corretamente | INFO de revisão |
| AUD-W5C16-013 | `_defaults_and_invariants` usa `object.__setattr__` (padrão Pydantic v2) | Sem ação |

### INFO (4)

| ID | Título |
|---|---|
| AUD-W5C16-014 | Vitest cobertura: 42 testes via `it.each` (CHANGELOG correto) |
| AUD-W5C16-015 | Backend pytest: 1027 + 10 skipped (CHANGELOG correto) |
| AUD-W5C16-016 | RBAC herdado de `test_reports_api.py` cobre 5 cenários 403 |
| AUD-W5C16-017 | Anti-enumeração 403 (não 404 byte-a-byte) — Decisão D11→i, ADR-162 |

---

## Recomendações de Próximos Passos

### Ações requeridas antes de prosseguir para revisão pré-merge consolidada (ALTOS — 3)

1. **Criar `docs/wave5-v4-c16/visual-guide.md`** — stub mínimo com 4 seções (card ROTA, RotaFilter, 4 perspectivas, CSV summary). Mario tira screenshots no smoke. Estimativa: 30 min de redação + 15 min de smoke. (AUD-W5C16-001)
2. **Expandir `docs/wave5-v4-c16/smoke-validation.md`** com 3 cenários de borda: estado vazio (`?vendedor_id=<uuid-fictício>`), estado de erro (network throttle DevTools), acesso negado (logar como vendedor). Estimativa: 15 min. (AUD-W5C16-002)
3. **Corrigir `aria-hidden-focus` em `DonutChart.tsx:369`** — mover `aria-hidden="true"` do `<details>` para o `<table>` interno OU usar atributo `inert`. Adicionar smoke com axe-core no DonutChart. Estimativa: 20 min + 10 min validação. (AUD-W5C16-003)

### Ações recomendadas mas não bloqueantes (MÉDIOS — 5)

4. **Refatorar `_CONTEXTO_MOTORISTA_STATUSES`** para derivar de `contexto_motorista()` canônico OU adicionar teste cross-validation. (AUD-W5C16-004)
5. **Implementar `prefers-reduced-motion`** em `relatorios.module.css`. (AUD-W5C16-005)
6. **Refatorar parsers** para módulo dedicado importável pelos testes. (AUD-W5C16-006)
7. **Renomear ou comentar** classes CSS legacy. (AUD-W5C16-007 + AUD-W5C16-008)

### Itens de backlog técnico (BAIXOS — 5)

8-12. Endereçar conforme prioridade em sessões de cleanup futuras. Sem urgência.

### Recomendação explícita

Após correção dos 3 ALTOS (estimativa total ~90 min), realizar **sessão de revisão consolidada pré-merge** (Wave 3 + Wave 5 juntas — C10 + C19 + C11 + C12 + C16 + Audit Fixes de cada) antes do merge `development → main`. A revisão pré-merge deve cobrir:
- Smoke E2E manual de todos os componentes da Wave 3 v4.0 (incluindo motorista em 3 contextos v4.0 + clicheria em `COM_MOTORISTA_ENTREGA_FINAL`).
- Smoke do C16 v4.0 (smoke-validation.md expandido).
- Pendências herdadas: rate limit C19 (ADR-145), benchmarks C11 (ADRs 153/157), CI/CD pós-Wave 3 (ADR-156).
- Validação visual do Dashboard (C15 v3) sem regressão.
- Validação de performance em staging com fixture realista (`seed_reports_fixture.py` da Wave 5 v3 ADR-098).

---

## Anexos

### A. Output do MCP Supabase (read-only)

- `list_projects` → projeto `rwxlpwmnkekzuurgthkr` ACTIVE_HEALTHY.
- `execute_sql SELECT version_num FROM alembic_version` → `013`.
- `execute_sql` enums → 6 rotas + 17 status confirmados.
- `execute_sql` distribuição rota → PADRAO=2, DIRETA=3, MATRIZ=1, NULL=11.
- `execute_sql` distribuição status → CANCELADA=7, CRIADA=6, RECEBIDA=2, REPROVADA=2.
- `execute_sql` movimentações → 16.
- `execute_sql` índices `provas_digitais` → 10 (incluindo `idx_provas_rota`).
- `execute_sql pg_policy` → 4 policies em `provas_digitais` + `movimentacoes`, `pol_provas_select` admin OR vendedor OR motorista (4 estados) OR clicheria (7 estados).
- `get_advisors security` → 2 alertas (1 INFO + 1 WARN, idênticos ao baseline pós-C12).
- `get_advisors performance` → 13 INFO `unused_index` (idênticos ao baseline pós-C12).

### B. Screenshots dos 10 cenários em staging

**NÃO COLETADOS** nesta auditoria. Recomendado: Mario coleta no smoke E2E pelos cenários 1-7 + os 3 novos do AUD-W5C16-002.

### C. CSV de cada relatório

**NÃO COLETADOS** nesta auditoria. Validação inferencial via inspeção de código:
- `_stream_summary` emite linhas `rota_v4_*` (9), `consolidacao_rota_*` (2-3), `contexto_motorista_*` (0-3).
- `_stream_overdue` emite coluna `contexto_motorista` na posição 7.
- `_stream_proofs` emite colunas `codigo_publico` (3) + `contexto_motorista` (8).

### D. Diffs amostrais examinados

- `git diff development..HEAD -- docs/wave3-v4-c11/contrato-c12.md`: VAZIO ✅
- `git diff development..HEAD -- frontend/src/app/(dashboard)/dashboard/`: VAZIO ✅
- `git diff development..HEAD -- backend/app/state_machine/ backend/app/services/state_machine.py`: VAZIO ✅
- `git diff development..HEAD -- frontend/src/middleware.ts shared/`: VAZIO ✅
- `git diff development..HEAD -- backend/app/api/v1/{provas,users,audit_log,configuracoes}.py`: VAZIO ✅
- `git diff development..HEAD -- backend/app/access/ backend/migrations/`: VAZIO ✅
- `git diff development..HEAD -- frontend/src/lib/services/identificacao-prova.ts frontend/src/lib/codigo-publico.ts frontend/src/lib/c19-mensagens.ts`: VAZIO ✅

### E. Output de axe-core por cenário

**NÃO RODADO** nesta auditoria. Recomendado: Mario roda no smoke (extensão axe DevTools).

### F. Output de teste de performance

**NÃO RODADO**.

### G. Output de teste de anti-enumeração

**NÃO RODADO** byte-a-byte. Decisão D11→i (ADR-162) preserva 403 — discrepância vs prompt da auditoria documentada e justificada.

### H. Comparação SQL pré-C16 vs pós-C16 do Dashboard

**NÃO RODADA**. C15 não modificado (validado via `git diff`); regressão lógica esperada zero.

---

**Fim do relatório de auditoria.**

**Próxima sessão:** Mario decide entre:
- (a) **Aprovar com correções:** abrir sessão dedicada para corrigir AUD-W5C16-001/002/003 (3 ALTOS, ~90 min). Após, prosseguir para revisão pré-merge consolidada Wave 3 + Wave 5.
- (b) **Aprovar sem correções:** mergeáveis em `development`; correções endereçadas em sessões posteriores como follow-up. Ainda assim recomendado a revisão pré-merge consolidada antes do merge para `main`.
- (c) **Reprovar e refazer:** caso queira incluir Linha 3 (Tempo Médio por Etapa), Donut completo de 5 segmentos, ou filtro Contexto Motorista visível — extensão de escopo que reverte a restrição "preservar layout v3 exatamente". Não recomendado pelo auditor (ADR-162 documenta a decisão consciente).

A recomendação do auditor é **(a) — Aprovar com correções**.

---

## Apêndice — Status pós-correção (Wave 5 v4.0 / C16 Audit Fixes)

**Sessão:** 2026-05-13 (branch `wave5-v4-c16/fixes/execution`, base `wave5-v4-c16/audit` `57a76d2`).
**Decisão do Mario:** Opção (a) — Aprovar com correções (escolhida pós-leitura do `fix-plan.md`).
**Escopo da correção:** TODOS os 17 achados (não apenas os 3 ALTOS sugeridos pelo auditor).
**Resultado:** 12 RESOLVIDOS · 5 ACEITOS (sem código). 0 DEFERRED · 0 BLOQUEADOS · 0 escalações novas.

| ID | Sev. | Status final | Commit SHA | Critério objetivo da resolução |
|---|:---:|:---:|:---:|---|
| AUD-W5C16-001 | ALTO | ✅ RESOLVIDO | `5315edf` | `docs/wave5-v4-c16/visual-guide.md` criado com 7 seções estruturadas (227 LOC). Mario preenche screenshots no smoke. |
| AUD-W5C16-002 | ALTO | ✅ RESOLVIDO | `d3d9599` | `smoke-validation.md` expandido de 20 → 23 cenários (+ #21 estado vazio + #22 estado de erro + #23 acesso negado). |
| AUD-W5C16-003 | ALTO | ✅ RESOLVIDO | `605939a` | `<details aria-hidden="true">` → `<details>` + `<table aria-hidden="true">` interna. WAI-ARIA 1.1 §4.3.2 conforme. Vitest 205/205 + tsc 0. |
| AUD-W5C16-004 | MÉDIO | ✅ RESOLVIDO | `cbe51d5` | `_CONTEXTO_MOTORISTA_STATUSES` derivado por comprehension de `contexto_motorista()` canônica. Novo teste `test_cross_validation_with_canonical_contexto_motorista` itera sobre os 17 valores de `StatusProvaEnum` validando paridade. |
| AUD-W5C16-005 | MÉDIO | ✅ RESOLVIDO | `fb469b0` | Bloco `@media (prefers-reduced-motion: reduce)` adicionado no final de `relatorios.module.css` cobrindo 8 seletores (cards, donut, bar row, sparkline, presets, scope). Padrão da Wave 3 C12. |
| AUD-W5C16-006 | MÉDIO | ✅ RESOLVIDO | `44aaa4c` | Parsers extraídos para `frontend/src/hooks/_useReportFilters.parsers.ts` (módulo puro). Hook importa do módulo; testes Vitest importam diretamente do módulo (sem re-implementação). 42/42 passam. |
| AUD-W5C16-007 | MÉDIO | ✅ RESOLVIDO | `36269f3` | Classes CSS renomeadas: `.rotaDotPadrao` → `.rotaDotMatriz`, `.rotaDotDireta` → `.rotaDotFilial`. Grep pós-rename: 0 ocorrências dos nomes legacy fora do comentário. |
| AUD-W5C16-008 | MÉDIO | ✅ RESOLVIDO | `36269f3` (combinado com AUD-007) | Bloco de comentário Wave 5 v4.0 / C16 fix AUD-W5C16-007+008 acima das classes em `relatorios.module.css` documenta mapeamento histórico v3→v4 e cita ADR-158. |
| AUD-W5C16-009 | BAIXO | ✅ ACEITO (sem código) | n/a | Auditor explicitamente declarou "semanticamente correto, mas vale documentar para Dashboard futuro". A docstring atual de `_CLICHERIA_EM_TRANSITO` (reports.py:127-139) já cobre. Sem código tocado. |
| AUD-W5C16-010 | BAIXO | ✅ RESOLVIDO | `f3afc43` | Classe `TestLegacyNullIndefinida` em `test_reports_v4.py` com 4 testes cobrindo `null_indef = null_total - null_matriz - null_filial`, schema `ConsolidacaoRota.indefinida >= 0`, e `DistRotaV4.categoria='legacy_null_indefinida'`. |
| AUD-W5C16-011 | BAIXO | ✅ RESOLVIDO | `43dee6c` | Guard `if cons.indefinida > 0` removido em `_summary_rows`; linha `consolidacao_rota_indefinida` agora sempre emitida (simetria com `_matriz`/`_filial`). Classe `TestCsvSummaryConsolidacaoIndefinida` com 3 testes. |
| AUD-W5C16-012 | BAIXO | ✅ ACEITO (INFO de revisão) | n/a | `to_cache_key` inclui `scope` corretamente — auditor declarou sem ação. Confirmado. |
| AUD-W5C16-013 | BAIXO | ✅ ACEITO (padrão Pydantic v2) | n/a | `_defaults_and_invariants` usa `object.__setattr__` — padrão para `frozen=True` Pydantic v2. Confirmado. |
| AUD-W5C16-014 | INFO | ✅ ACEITO | n/a | Vitest cobertura: 42 testes via `it.each` — CHANGELOG correto. Confirmado. Após AUD-006, módulo `_useReportFilters.parsers.ts` testado diretamente — mesma cobertura efetiva. |
| AUD-W5C16-015 | INFO | ✅ ACEITO + atualizado | n/a | Backend pytest: 1027 + 10 skipped pós-C16 originalmente. Pós-Audit Fixes: **1035 + 10 skipped** (era 1027 + 8 novos: 1 AUD-004 + 4 AUD-010 + 3 AUD-011). Vide validação na §"Rodar validation". |
| AUD-W5C16-016 | INFO | ✅ ACEITO | n/a | RBAC herdado de `test_reports_api.py` (Wave 5 v3, intocado): 5 cenários 403 cobertos. Confirmado. |
| AUD-W5C16-017 | INFO | ✅ ACEITO (apêndice em ADR-162) | n/a (registro em DECISIONS.md) | Anti-enumeração 403 (não 404 byte-a-byte) é decisão consciente D11→i registrada em ADR-162. Mario aprovou explicitamente em 5 razões. Apêndice pós-auditoria adicionado ao ADR-162 reafirma posição. Sem código tocado. Follow-up para Wave 6+ se Mario quiser migrar Matriz inteira para 404 byte-a-byte (afeta 11 chaves de RBAC, não apenas `relatorios`). |

**Resumo final:**
- **12 ALTOs+MÉDIOs+BAIXOs corrigíveis:** todos RESOLVIDOS.
- **5 BAIXOs/INFOs sem ação:** todos ACEITOS (com justificativa por achado).
- **DEFERRED:** 0.
- **BLOQUEADOS por divergência:** 0.
- **Novas escalações humanas:** 0.

**Validação interna pós-correção:** ver [docs/wave5-v4-c16/fix-validation.md](fix-validation.md) com checklist completo, evidências por achado e auto-crítica adversarial.

**Próximo passo recomendado:** sessão de **auditoria sênior independente** dedicada a validar (a) que cada achado original foi resolvido sem introduzir regressão; (b) que as 11 decisões de ADR-162 permanecem implementadas conforme registrado; (c) que `contrato-c12.md`, C15 (Dashboard v3) e outras entregas continuam intocados; (d) que os 23 cenários do smoke renderizam corretamente; (e) que `prefers-reduced-motion` zera animações em DevTools emulation; (f) que `aria-hidden-focus` não é mais flagrado pelo axe-core; (g) que CSV summary emite `consolidacao_rota_indefinida` sempre. Após re-auditoria, **sessão de revisão consolidada pré-merge** (Wave 3 + Wave 5 juntas) antes do merge `development → main`.
