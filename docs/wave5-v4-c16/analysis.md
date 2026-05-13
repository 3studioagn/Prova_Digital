# Wave 5 v4.0 / Componente 16 — Análise Read-Only + Proposta de Design (Gate 1)

**Status:** Gate 1 — análise read-only. Nenhuma linha de código de produção alterada.
**Branch:** `wave5-v4-c16/analysis` (sai de `development`).
**Data:** 2026-05-13.
**Autor:** agente de execução (Claude Code).
**Próximo passo:** aguardar decisões humanas do Mario sobre as 11 decisões propostas + string `AUTORIZADO GATE 2 — WAVE 5 v4.0 / C16` para iniciar Gate 2.

---

## 0. Resumo executivo (≤ 30 linhas)

- Wave 5 v4.0 entrega exclusivamente o Componente 16 v4.0 — Relatórios Gerenciais com suporte ao novo modelo de 4 rotas + laminação + máquina expandida + provas legacy v3.0.
- O C16 já existe em produção como entrega da Wave 5 v3.0 (alembic_version=013, 13 commits) — endpoint único `/api/v1/reports` discriminado por `scope` + `/reports/export` CSV streaming + 4 perspectivas frontend (`ReportGeral`, `Report3Studio`, `ReportVendedores`, `ReportClicheria`). Esta sessão **estende e refina** o C16 v3 existente, não reescreve do zero.
- `contrato-c12.md` está presente em `docs/wave3-v4-c11/contrato-c12.md` e coerente com o código real entregue (verificado: `STATUS_DONUT_COLOR` referenciado em ReportGeral.tsx:91 já cobre os 17 estados; helpers `contextoMotorista`, `ROTA_ETAPAS`, `getRotaEtapas`, `getRotaLabel` exportados em `lib/types/prova.ts`).
- C12 está integralmente em `development` (commits 153f8bf, d7f7beb, da4878c, 7667355, f40f7b6 — branch `wave3-v4-c12/fixes/execution`). 0 CRITICAL, 0 ALTOS, todos os 13 IDs da auditoria pós-C12 corrigidos.
- C15 (Dashboard) está intocado pela v4.0 — `git log` em `frontend/src/app/(dashboard)/dashboard/` retorna apenas 3 commits: `f4fbaef` (versão 1), `f9e5bce` (Wave 5 C17 v3 — 3º card permitido), `6add246` (Wave 4 conclusão). Sem touch v4.0.
- Validação MCP: enum `rota_enum` tem 6 valores (4 v4.0 + 2 legacy); enum `status_prova_enum` tem 17 valores (10 v3.0 + 7 v4.0). 11/17 provas têm `rota IS NULL` (65% legacy), 5 têm rota legacy (PADRAO=2, DIRETA=3) e 1 tem rota v4.0 (MATRIZ). Total: 16 movimentações. `idx_provas_rota` existe (Wave 2 v4.0). Advisors limpos.
- Gaps confirmados entre C16 v3 e v4.0: (1) `RotaFilter` (linha 27-31) só conhece PADRAO/DIRETA; (2) `useReportFilters.parseRota` idem; (3) `useReportFilters.STATUS_VALORES` lista só os 10 v3.0; (4) backend `_aggregate_geral` Q1 só agrega rota_padrao/rota_direta/rota_nula (lacuna nas 4 v4.0); (5) `DistOrigemRota` schema tem `via_padrao`/`via_direta` (modelo v3); (6) labels de filtros já usam "Matriz"/"Filial" via `ROTA_LABELS` (Decisão 11.1 do C12 propagada).
- Sem Figma anexado — proposta de design em ASCII wireframes nesta análise para 10 cenários obrigatórios.
- Decisão crítica a tomar (D3): tratamento de provas legacy v3.0 (`rota IS NULL`) na Distribuição por Rota. Recomendação técnica: agrupar como 5ª categoria "Legacy v3.0" com cor distinta (transparência) — alternativa pode ser inferir via `vendedor_localizacao` (heurística do C12 para Timeline).
- Decisão crítica (D9): estratégia de queries. Recomendação: manter on-demand (Decisão atual da Wave 5 v3 ADR-097/098 com cache TTL 60s + ETag + Realtime invalidation) — já entrega ~20x redução; introduzir índice composto extra se medição mostrar gap.
- Decisão crítica (D11): manter 403 ou alterar para 404 anti-enumeração estrita. Recomendação: manter 403 — coerente com toda a Matriz Wave 1 v4.0; mudar para 404 quebraria invariante da camada (vide ADR-156 do C11 sobre coerência das 3 camadas RBAC).
- Outra divergência com o prompt: Recharts **já foi removido** na Wave 4 (closeout WAVE5_CLOSEOUT.md §99 — "Deps externas chart: 0"). C16 v3 usa SVG inline (`DonutChart`, `BarChart`, `TimeSeriesChart`, `Sparkline`). Esta sessão preserva o padrão SVG sem reintroduzir Recharts.
- 14 testes class containers no `test_reports_api.py` cobrem RBAC, validação, scope routing, cache, ETag, erro backend, export, audit log, filtros, equivalência Dashboard↔Relatórios, cache no-DB-call, auditoria sênior 2026-04-29 R2, e helper `_aplicar_filtros_provas`. Total backend Wave 5 = 209 testes. Frontend Vitest: 163 (pós-C12).
- Riscos críticos do C16 v4.0: (R1) distorção de métricas por contagem legacy não tratada; (R2) anti-enumeração — manter 403 vs 404 a decidir; (R3) backwards-compat da invalidação Realtime (`provas_digitais` na publicação); (R4) rendering complexo da timeline de tempos por etapa com sequências de tamanhos diferentes por rota (MATRIZ=6, LAM_MATRIZ=11, FILIAL=4, LAM_FILIAL=7); (R5) testes de regressão precisam cobrir C15 (Dashboard v3) sem regressão — endpoint `/api/v1/provas/dashboard` consome a mesma `provas_digitais` que C16 v4.0 reformula RLS.

---

## 1. Confirmação de leitura dos artefatos canônicos

| Artefato | Caminho real | Status |
|---|---|:---:|
| Contrato C12 | `docs/wave3-v4-c11/contrato-c12.md` (408 linhas) | ✅ Lido integral |
| CLAUDE.md | `CLAUDE.md` (raiz) | ✅ Lido via system reminder |
| `lib/types/prova.ts` (consumido) | `frontend/src/lib/types/prova.ts` (682 linhas) | ✅ Lido integral |
| C16 v3 backend | `backend/app/api/v1/reports.py` (1613 linhas) | ✅ Lido integral |
| C16 v3 schemas | `backend/app/domain/schemas/report.py` (363 linhas) | ✅ Lido integral |
| C16 v3 filtros | `backend/app/services/report_filters.py` (197 linhas) | ✅ Lido integral |
| C16 v3 frontend (página) | `frontend/src/app/(dashboard)/relatorios/page.tsx` (297 linhas) | ✅ Lido integral |
| C16 v3 ReportGeral | `frontend/src/app/(dashboard)/relatorios/perspectivas/ReportGeral.tsx` (742 linhas) | ✅ Lido integral |
| C16 v3 RotaFilter | `frontend/src/app/(dashboard)/relatorios/RotaFilter.tsx` (59 linhas) | ✅ Lido integral |
| C16 v3 useReportFilters | `frontend/src/hooks/useReportFilters.ts` (177 linhas) | ✅ Lido integral |
| C15 v3 Dashboard | `frontend/src/app/(dashboard)/dashboard/page.tsx` | ✅ Lido top 100 linhas + `git log --all` |
| C16 v3 testes | `backend/tests/test_reports_api.py` (1029 linhas, 14 test classes) | ✅ Inspecionado estrutura |
| Wave 5 v3 closeout | `docs/waves/WAVE5_CLOSEOUT.md` | ✅ Lido top 100 linhas |
| Advisors MCP (security + performance) | live em produção | ✅ Coletado |
| Distribuição de dados em produção | live via MCP `execute_sql` | ✅ Coletado |

**Artefatos referenciados mas não lidos integralmente** (lidos por amostragem suficiente para análise):
- `BACKLOG_RastreioProvasDigitais_v4_0.docx`, `RequisitosProvasDigitais_v4_0.docx`, `DAT_RastreioProvasDigitais_v3_0.docx` — documentos Word do desktop do Mario, citados como referência canônica. CLAUDE.md já carrega o sumário operacional vivo deles.
- `DECISIONS.md` — ADRs até 161 referenciados via CLAUDE.md (ADR-095..101 da Wave 5 v3; ADRs 102-109 visual refresh + auditorias Wave 5 v3).
- `CHANGELOG.md` — entradas v4.0 já refletidas no CLAUDE.md.
- `frontend/src/app/(dashboard)/relatorios/perspectivas/Report3Studio.tsx`, `ReportClicheria.tsx`, `ReportVendedores.tsx` — não lidos (mesma estrutura de cards do `ReportGeral`; reuso será análogo).
- Componentes `shared/` (`DonutChart`, `BarChart`, `TimeSeriesChart`, `Sparkline`, `DeltaBadge`, `KpiCard`, `EmptyState`, `PeriodoBadge`) — não lidos integralmente; serão consumidos pela v4.0 sem modificação.
- `state_machine/v4/rules.py` e `contextos.py` (backend) — não lidos; contrato-c12.md documenta a API consumida pelo frontend.

---

## 2. Validação MCP da infraestrutura (read-only)

### 2.1 Supabase

| Item | Resultado | Observação |
|---|---|---|
| Projeto | `rwxlpwmnkekzuurgthkr` (sa-east-1) | OK |
| `alembic_version` | `013` | Wave 3 v4.0 C11 aplicada |
| `rota_enum` (6 valores) | `PADRAO`, `DIRETA`, `MATRIZ`, `LAM_MATRIZ`, `FILIAL`, `LAM_FILIAL` | Conforme esperado (Wave 2 v4.0 + legacy) |
| `status_prova_enum` (17 valores) | 10 v3.0 + 7 v4.0 | Conforme contrato-c12.md §1.2 |
| Provas totais | 17 | Volume baixo, mas suficiente para validação |
| Provas com `rota=NULL` | 11 (65%) | Legacy v3.0 sem backfill (Wave 7 pendente) |
| Provas com `rota=PADRAO` | 2 | Legacy v3.0 |
| Provas com `rota=DIRETA` | 3 | Legacy v3.0 |
| Provas com `rota=MATRIZ` | 1 | v4.0 (única) |
| Provas com `rota IN (LAM_MATRIZ,FILIAL,LAM_FILIAL)` | 0 | v4.0 outras rotas sem dados ainda |
| Distribuição status | CANCELADA=7, CRIADA=6, RECEBIDA_PELA_CLICHERIA=2, REPROVADA_PELO_VENDEDOR=2 | Sem provas em estados v4.0 ativos |
| Movimentações totais | 16 | Volume baixo |
| Índices em `provas_digitais` | 9 (codigo_publico UNIQUE, nro_requerimento UNIQUE, qr_code_hash UNIQUE, pkey, vendedor_status compound, vendedor, status, status_created, **rota**, created_at) | `idx_provas_rota` ✅ (Wave 2 v4.0) |
| Índices em `movimentacoes` | 7 (pkey, prova, prova_ciclo, prova_data, status_novo_created_at, usuario, created_at) | OK |
| RLS `provas_digitais` | 3 policies: INSERT (admin), SELECT (admin OR vendedor_owner OR motorista_states OR clicheria_states), UPDATE (admin) | OK; expandida para 17 estados |
| RLS `movimentacoes` | 2 policies: INSERT (admin), SELECT (admin OR usuario_owner OR EXISTS provas matching) | OK |
| Advisors security | 1 INFO `rls_enabled_no_policy` em `alembic_version` (intencional) + 1 WARN `auth_leaked_password_protection` (WONTFIX plano pago) | **Sem novos alertas** vs baseline pós-C11 |
| Advisors performance | 13 INFO `unused_index` (incluindo `idx_provas_rota` e `idx_movimentacoes_status_novo_created_at`) | Esperado em volume baixo (volume real → uso real); sem alarme |

### 2.2 Cloudflare

- Wave 5 v4.0 não toca em R2 nem em qualquer infraestrutura Cloudflare. **Validação trivial:** o bucket `rastreio-provas-artes` (Wave 0) permanece como única integração externa; sem necessidade de novos buckets, CORS ou tokens. Saudabilidade preservada — herdada do baseline pós-C12.

### 2.3 Conclusões da validação

- ✅ Enum dos 17 estados consolidado (C11 entregue).
- ✅ Coluna `rota` nullable com 6 valores possíveis (4 v4.0 + 2 legacy).
- ✅ Trigger `trg_provas_rota_imutavel` em produção (Wave 2 v4.0).
- ✅ Índices necessários já existem (`idx_provas_rota`, `idx_provas_status_created`, `idx_movimentacoes_prova_data`).
- ✅ RLS já é admin-only para queries de relatório (via `pol_provas_select` admin branch).
- ⚠️ Volume baixo (16 provas, 16 movs) — não suficiente para `EXPLAIN ANALYZE` significativo. Confirmação de performance dependerá de testes em staging com fixture seeded (já existe `seed_reports_fixture.py` da Wave 5 v3 — ADR-098).

---

## 3. Inventário do C16 v3.0 atual

### 3.1 Backend

| Camada | Caminho | LOC | Observações |
|---|---|---:|---|
| Router | `backend/app/api/v1/reports.py` | 1613 | Endpoint `GET /` + `GET /export`. RBAC via `access_required("relatorios")` (Wave 1 v4.0). 6 funções de agregação (`_aggregate_geral`, `_aggregate_3studio`, `_aggregate_vendedores`, `_aggregate_clicheria` + helpers `_query_ranking_vendedores`, `_query_provas_atrasadas`). 4 streams CSV (`_stream_summary`, `_stream_by_seller`, `_stream_overdue`, `_stream_proofs`). Cache backend TTL 60s + ETag SHA-256 + `?_force=1` bypass. |
| Schemas | `backend/app/domain/schemas/report.py` | 363 | Discriminated union `ReportResponse` por `scope` (Literal). Sub-schemas frozen=True. `DistRota` aceita `RotaEnum \| None`. `DistOrigemRota` tem `via_padrao`/`via_direta` (v3 only). |
| Filtros | `backend/app/services/report_filters.py` | 197 | Pydantic `ReportFilters` validado (defaults 30d, range max 366d). `to_cache_key()` SHA-256 do JSON canônico. |
| Cache | `backend/app/services/report_cache.py` | (não inspecionado integral) | `ReportCache` asyncio-safe in-memory, TTL 60s. |
| ETag | `backend/app/services/report_etag.py` | (não inspecionado integral) | `compute_etag` + `matches_if_none_match`. |
| Métricas | `backend/app/services/report_metrics.py` | (não inspecionado integral) | `taxa`, `media_diaria`, `arredondar_horas`, `limite_atraso`, `calcular_total_dias`. |
| Testes | `backend/tests/test_reports_api.py` | 1029 | 14 test classes cobrindo RBAC, validação, scope routing, cache, ETag, erros, export, audit log, filtros, equivalência Dashboard↔Relatórios, cache no-DB-call, auditoria sênior R2, helper `_aplicar_filtros_provas`. |

### 3.2 Frontend

| Camada | Caminho | LOC | Observações |
|---|---|---:|---|
| Página principal | `frontend/src/app/(dashboard)/relatorios/page.tsx` | 297 | Orquestra filtros + fetch + Realtime + polling fallback 30s. Roteia entre 4 `Report*` via discriminated union. Wave 1 v4.0: `useAuthorization("relatorios")` guard proativo. |
| ScopeSelector | `.../ScopeSelector.tsx` | (não inspecionado) | Pill horizontal: Geral / 3Studio / Vendedores / Clicheria. |
| DateRangeFilter | `.../DateRangeFilter.tsx` | (não inspecionado) | Presets (Hoje/7d/30d/90d) + customizado. Conversão BRT→UTC. |
| StatusFilter | `.../StatusFilter.tsx` | (não inspecionado) | Select com 10 estados v3.0 (faltam 7 v4.0). |
| VendedorFilter | `.../VendedorFilter.tsx` | (não inspecionado) | Multiselect com fetch lazy. |
| RotaFilter | `.../RotaFilter.tsx` | 59 | Segmented pill: **Todas / Padrao / Direta** (gap v4.0). |
| SearchInput | `.../SearchInput.tsx` | (não inspecionado) | Busca textual (q) com debounce. |
| ExportButton | `.../ExportButton.tsx` | (não inspecionado) | Botão CSV com 4 datasets. |
| Report3Studio | `.../perspectivas/Report3Studio.tsx` | (não inspecionado) | Cards 3Studio + sparkline. |
| ReportClicheria | `.../perspectivas/ReportClicheria.tsx` | (não inspecionado) | Cards Clicheria + `DistOrigemRota` (via_padrao/via_direta — gap v4.0). |
| ReportVendedores | `.../perspectivas/ReportVendedores.tsx` | (não inspecionado) | Ranking + dist. localização. |
| ReportGeral | `.../perspectivas/ReportGeral.tsx` | 742 | Linha 1: 4 cards (Total + Tempo aprov. + Taxa reprov. + ROTA). Linha 2: 3 cards (Donut Provas Ativas + Vendor Row + Vendor Highlight). Mais 2 tabelas (Métricas por Vendedor + Provas Atrasadas). Card ROTA usa `padraoCount`/`diretaCount` (gap v4.0). `STATUS_DONUT_COLOR` já cobre os 17 estados. |
| Shared | `shared/{DonutChart,BarChart,TimeSeriesChart,Sparkline,DeltaBadge,KpiCard,EmptyState,PeriodoBadge}.tsx` | (~8 arquivos) | SVG inline puro. Sem Recharts. |
| useReport | `hooks/useReport.ts` | (não inspecionado) | Fetch wrapped com ETag local + cache local. |
| useReportFilters | `hooks/useReportFilters.ts` | 177 | URL-persisted via `useSearchParams`. `parseRota` só PADRAO/DIRETA (gap); `STATUS_VALORES` 10 estados v3 (gap). |
| useReportExport | `hooks/useReportExport.ts` | (não inspecionado) | Download blob com filename via Content-Disposition. |
| Types | `frontend/src/lib/types/report.ts` | (não inspecionado integral) | `ReportResponse` union; `REPORT_SCOPES`. |

### 3.3 Gaps confirmados C16 v3 → v4.0

| # | Local | Gap | Severidade |
|---|---|---|:---:|
| G1 | `RotaFilter.tsx:27-31` | OPTIONS só tem `null`, `PADRAO`, `DIRETA`. Falta MATRIZ, LAM_MATRIZ, FILIAL, LAM_FILIAL. | 🔴 ALTO |
| G2 | `useReportFilters.ts:33-36` | `parseRota` só aceita PADRAO/DIRETA — `?rota=MATRIZ` na URL vira `null`. | 🔴 ALTO |
| G3 | `useReportFilters.ts:38-49` | `STATUS_VALORES` só tem 10 v3.0; `?status=COM_MOTORISTA_IDA_LAMINACAO` vira `null`. | 🔴 ALTO |
| G4 | `reports.py:506-527` (`_aggregate_geral` Q1) | Contagens explícitas `rota_padrao`, `rota_direta`, `rota_nula`. Falta MATRIZ, LAM_MATRIZ, FILIAL, LAM_FILIAL. | 🔴 ALTO |
| G5 | `reports.py:671-683` | `distribuicao_rota` só monta `DistRota` para PADRAO/DIRETA/None. Falta 4 v4.0. | 🔴 ALTO |
| G6 | `report.py` schema `DistOrigemRota` | Campos `via_padrao`/`via_direta`. Modelo v3.0 que não distingue entre rotas com/sem laminação. | 🟡 MÉDIO |
| G7 | `ReportGeral.tsx:162-165` + `:321-346` | Card ROTA usa `padraoCount`/`diretaCount`. Visual para 2 rotas; precisa expansão para 4 v4.0 + tratamento legacy. | 🔴 ALTO |
| G8 | `_aggregate_clicheria` (`reports.py:912-1003`) | Considera apenas ENVIADA/ENCAMINHADA_A_CLICHERIA legacy. Falta as transições v4.0 (incluindo via laminação). | 🟡 MÉDIO |
| G9 | `reports.py` filtros de período | `_periodo_filter` aplica em `provas_digitais.created_at`. OK — não muda. | ✅ Sem gap |
| G10 | Backend — Tempo Médio por Etapa | **Não existe na v3**. Indicador novo da v4.0 (ampliado para laminação). | 🟢 NOVO |
| G11 | Frontend — Indicador novo "Distribuição por Contexto Motorista" | **Não existe**. Pode ou não estar no escopo — escalar. | 🟡 ESCALAR |
| G12 | `StatusFilter.tsx` | Provavelmente lista só 10 v3.0 (a confirmar). | 🟡 MÉDIO |
| G13 | RLS para anti-enumeração | Hoje retorna 403 via `access_required`. Prompt pede 404 byte a byte. Decisão crítica. | 🟡 ESCALAR (D11) |
| G14 | CSV `dataset=summary` | Linhas `rota_PADRAO`/`rota_DIRETA` (não enumera v4.0). Idem 4 datasets. | 🟡 MÉDIO |
| G15 | Modo "Tabela" alternativo aos gráficos (a11y) | **Não existe**. Prompt v4.0 explicitamente pede. | 🟢 NOVO |
| G16 | `aria-live` para feedback | Parcial — `<div role="alert">` em erro; sem region polite para "Atualizado". | 🟡 MÉDIO |
| G17 | Comparação com período anterior | **Não existe** como feature de backend. `ReportGeral` faz proxy via metades da `serie_temporal`. Pode ser legítima — D8. | 🟡 ESCALAR |

---

## 4. Reuso do `contrato-c12.md`

### 4.1 O que será consumido — sem modificação

| Tipo/helper | Origem | Uso no C16 v4.0 |
|---|---|---|
| `StatusProva` (17 valores) | `lib/types/prova.ts:27-50` | Substituir `STATUS_VALORES` em useReportFilters; expandir StatusFilter |
| `STATUS_LABELS` (full pt-BR) | `lib/types/prova.ts:190-210` | Render de labels em filtros + cards |
| `STATUS_LABELS_SHORT` | `lib/types/prova.ts:216-236` | Render compacto em tabelas/badges |
| `Rota` (6 valores) | `lib/types/prova.ts:62-69` | Substituir tipos hard-code do RotaFilter |
| `RotaCriacao` (4 v4.0) | `lib/types/prova.ts:75` | Filtro de criação (se aplicável) |
| `ROTA_LABELS` (já aplicado Decisão 11.1 C12) | `lib/types/prova.ts:253-260` | PADRAO→"Matriz", DIRETA→"Filial", MATRIZ→"Matriz", LAM_MATRIZ→"Lam. Matriz", etc. |
| `ROTA_OPTIONS` (6 valores) | `lib/types/prova.ts:319-326` | Lista para multiselect rota |
| `contextoMotorista(status)` | `lib/types/prova.ts:354-362` | Render do badge de contexto + Distribuição por Contexto |
| `ROTA_ETAPAS` | `lib/types/prova.ts:399-436` | Indicador Tempo Médio por Etapa (sequência canônica por rota) |
| `LEGACY_ROTA_PADRAO` / `LEGACY_ROTA_DIRETA` | `lib/types/prova.ts:444-466` | Indicador Tempo Médio por Etapa (provas legacy) |
| `getRotaEtapas(rota, loc)` | `lib/types/prova.ts:484-502` | Heurística legacy `rota=NULL` (Decisão 11.2 C12) |
| `getRotaLabel(rota, loc)` | `lib/types/prova.ts:513-521` | Render do label de rota com fallback legacy |
| `ESTADOS_LAMINACAO` + `isInLaminationBlock()` | `lib/types/prova.ts:374-385` | Indicador laminação |
| `STATUS_DONUT_COLOR` | `ReportGeral.tsx:91-116` (já existe e cobre 17 estados) | **JÁ COBRE V4.0** — apenas usar |

### 4.2 Verificação de coerência

- ✅ Mapeamento `Record<StatusProva, ...>` força exhaustividade. TypeScript barra build se um estado v4.0 for omitido.
- ✅ `getRotaEtapas(null, "FILIAL")` retorna `LEGACY_ROTA_DIRETA` — heurística do C12 disponível para indicadores que dependem da rota inferida (não usar para Distribuição por Rota — ver Decisão 3).
- ✅ Backend Python tem `from app.state_machine.v4.contextos import contexto_motorista`. Frontend TS tem `contextoMotorista()`. Paridade testada via `test_status_prova_enum_drift.py` (C11).

### 4.3 Gap no contrato — não há

O `contrato-c12.md` cobre tudo necessário pelo C16 v4.0. Nenhum item adicional precisa ser proposto ao C11 para correção pós-auditoria.

---

## 5. Proposta de design (10 cenários — ASCII wireframes)

### Cenário 1 — Página principal de Relatórios (visão Geral)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Relatorios                                              [⬇ Exportar CSV ▾]      │
│ 30 dias · 14/04 – 13/05 · Atualizado ha 2s                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│ [ Geral ] [ 3Studio ] [ Vendedores ] [ Clicheria ]      ← ScopeSelector (atual) │
├─────────────────────────────────────────────────────────────────────────────────┤
│ ◀ Periodo: [Hoje][7d][30d●][90d][Customizado]  ◀ Busca: [______________]        │
│ ◀ Status: [Todos ▾]  ◀ Vendedor: [Todos ▾]  ◀ Rota: [Todas ▾]                   │
│ ◀ Contexto motorista: [Todos ▾]  (NOVO v4.0 — habilitado so se rota expandida)  │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Linha 1 — 4 cards (preservada da v3)                                           │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐                    │
│  │ ⬛ TOTAL    │ │ TEMPO MED. │ │ TAXA REPR. │ │ ROTA (NEW) │                    │
│  │   17       │ │   62,1 h   │ │  11,76%    │ │ 4 v4.0 +   │                    │
│  │  ▁▂▃▅█▆▄   │ │            │ │            │ │ Legacy     │                    │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘                    │
│                                                                                 │
│  Linha 2 — 3 cards (preservada da v3, donut atualizado)                         │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐                                   │
│  │ Provas     │ │ Tempo med. │ │ ⬛ VENDEDOR │                                   │
│  │ ativas     │ │ por vended.│ │  com mais  │                                   │
│  │ [Donut●]   │ │ [BarLines] │ │  artes     │                                   │
│  │ 9 ATIVAS   │ │ 01 Joao 5h │ │  Mario 8   │                                   │
│  └────────────┘ └────────────┘ └────────────┘                                   │
│                                                                                 │
│  NOVO v4.0 — Linha 3 — 1 card largo (Indicador NOVO: Tempo Medio por Etapa)     │
│  ┌─────────────────────────────────────────────────────────────────┐ [G▾][T▾]   │
│  │ Tempo medio por etapa — MATRIZ        2,3h ▁▂▃▅█▆▄  Δ -4,2%     │            │
│  │ Tempo medio por etapa — LAM. MATRIZ   8,1h ▁▂▃▅█▆▄  Δ +1,1%     │            │
│  │ Tempo medio por etapa — FILIAL        1,8h ▁▂▃▅█▆▄  Δ -2,0%     │            │
│  │ Tempo medio por etapa — LAM. FILIAL   6,5h ▁▂▃▅█▆▄  Δ +0,8%     │            │
│  │ Tempo medio por etapa — LEGACY v3.0   3,7h ▁▂▃▅█▆▄  (so 11 prv) │            │
│  └─────────────────────────────────────────────────────────────────┘            │
│                                                                                 │
│  Tabelas existentes (preservadas):                                              │
│  ┌─────────────────────────────────────────────────────────────────┐            │
│  │ Metricas por Vendedor             RANKING DETALHADO       3 VEND│            │
│  │  # VENDEDOR     LOCAL    VOLUME  APROV. REPROV. TEMPO            │            │
│  │  01 Mario       Filial   ▓▓▓ 5    3      2     12,4h            │            │
│  └─────────────────────────────────────────────────────────────────┘            │
│  ┌─────────────────────────────────────────────────────────────────┐            │
│  │ Provas Atrasadas                  AGUARDANDO ACAO         2 PRV │            │
│  │  # PROVA          VENDEDOR    STATUS              ATRASO        │            │
│  │  01 ABC123        Joao        Aguardando vendedor 25,3h         │            │
│  └─────────────────────────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────────────────────┘
```

Notas:
- Header preservado. Filtros (linha 2) ganham filtros novos: Contexto motorista (apenas em scope=geral; oculto nas demais).
- Cards de KPI da Linha 1 preservados. **Card ROTA reformulado** — vide Cenário 2.
- Donut de Provas Ativas (Linha 2 card e) automaticamente cobre 17 estados via `STATUS_DONUT_COLOR` já existente.
- **Linha 3 NOVA:** "Tempo medio por etapa" agrupado por rota — indicador novo da v4.0.

### Cenário 2 — Distribuição por Rota (card "ROTA" reformulado)

**Opção A — Donut compacto + legenda lateral** (recomendada):

```
┌─────────────────────────────────────┐
│ ROTA                                │
│         ╭─────╮     • Matriz       1│
│        ╱       ╲    • Lam. Matriz  0│
│       │   17    │   • Filial       3│
│       │ PROVAS  │   • Lam. Filial  0│
│        ╲       ╱    • Legacy v3   13│
│         ╰─────╯     ─────────────────│
│                     [Ver tabela]    │
└─────────────────────────────────────┘
```

**Opção B — Stacked bar horizontal**:

```
┌─────────────────────────────────────┐
│ ROTA                                │
│ ▓░░▓▓▓░░░░░░░░░░░░░░░░░░▓▓▓▓▓▓▓▓▓▓▓│ 17 PROVAS
│ │  │  │                  │         │
│ M  LM Filial            Legacy     │
│                                    │
│ Matriz 1 · Lam.Matriz 0 · Filial 3 │
│ Lam.Filial 0 · Legacy 13           │
└─────────────────────────────────────┘
```

**Opção C — Bar vertical**:

```
┌─────────────────────────────────────┐
│ ROTA                                │
│             ▓                       │
│             ▓                       │
│             ▓        ░░             │
│ ▓ ░  ░  ░  ▓        ░░             │
│ ▓ ░  ░  ░  ▓        ░░             │
│ M LM F LF Leg.                     │
│ 1 0  3 0  13                       │
└─────────────────────────────────────┘
```

### Cenário 3 — Tempo Médio por Etapa (com laminação)

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Tempo Medio por Etapa — MATRIZ                              [Grafico][Tabela]│
│                                                                            │
│  Criada ─── Retirada ─── Aprovada ─── DeVolta ─── ComMot ─── Recebida     │
│   0.5h      2.1h         18.4h       4.2h        6.0h     final           │
│  ▁          ▂            ▆           ▃           ▃▄                       │
│                                                                            │
│ Tempo Medio por Etapa — LAM. MATRIZ                                        │
│                                                                            │
│  Criada → P/Lam → IdaLam → Laminada → VoltaLam → PosLam → Retirada → ...  │
│   0.5h    1.2h    3.0h    24.0h      3.0h      0.8h    2.1h    ...      │
│  ▁        ▂       ▃       ██         ▃         ▁       ▂                  │
│                                                                            │
│ Tempo Medio por Etapa — FILIAL                                             │
│  (curva mais compacta — 4 etapas)                                          │
│                                                                            │
│ Tempo Medio por Etapa — LAM. FILIAL                                        │
│  (curva intermediaria — 7 etapas)                                          │
└────────────────────────────────────────────────────────────────────────────┘
```

Notas:
- Cada "etapa" é uma transição entre estados consecutivos na `ROTA_ETAPAS[rota]`.
- BarChart horizontal compacto (`shared/BarChart.tsx` reusado).
- Toggle "Grafico" / "Tabela" no canto (Decisão 7).
- Filtro de rota acima oculta as outras 3 rotas se selecionado.

### Cenário 4 — Taxa de Reprovação segmentada por rota

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Taxa de Reprovacao — por vendedor + rota          [Grafico][Tabela] [G/T]  │
│                                                                            │
│  Joao         ▓▓▓▓▓░░░░░░░  Matriz  18,2%                                 │
│  Mario        ▓▓▓▓▓▓▓░░░░░  Filial  25,0%                                 │
│  Carlos       ░░░░░░░░░░░░  Lam.Filial 0,0%                               │
│  Andre        ▓▓▓▓▓▓▓▓▓▓░░  Matriz  87,5%  ← outlier (cor vermelha)       │
│                                                                            │
│  Media geral: 32,7%                                                        │
└────────────────────────────────────────────────────────────────────────────┘
```

Variante alternativa (Opção B): grouped bar — 4 barras por vendedor (uma por rota).

### Cenário 5 — Filtros aplicados (interface)

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ◀ PERIODO ──────────────────────────────────────────                       │
│   [ Hoje ] [ 7d ] [ 30d ● ] [ 90d ] [ Customizado ▾ ]   01/04 – 30/04     │
│                                                                            │
│ ◀ BUSCA  [_____________________________ 🔍]   ◀ STATUS [Todos ▾]          │
│                                                                            │
│ ◀ VENDEDOR [Todos os 6 ▾]   ◀ ROTA [Todas ▾ (5 ativas)]                   │
│                                                                            │
│ ◀ CONTEXTO MOT. [Todos ▾]   (apenas se rota for laminacao/null)           │
│                                                                            │
│ ─────────────────────────────────────                                      │
│ FILTROS ATIVOS: 30d  •  Status: Aguardando vendedor  •  Rota: Matriz       │
│ [ Limpar todos × ]                                                         │
└────────────────────────────────────────────────────────────────────────────┘
```

Filtros novos vs v3:
- **Rota** expandida: além de Padrao/Direta — Matriz, Lam. Matriz, Filial, Lam. Filial, Legacy v3.0.
- **Status** expandido: 17 valores no select agrupados visualmente (Legacy / v4.0 / Laminação / Terminal).
- **Contexto motorista** (NOVO): aparece apenas em rotas com laminação ou quando rota=null. 3 opções (Ida lam. / Volta lam. / Entrega final).

### Cenário 6 — Exportação CSV

```
┌─────────────────────────────────────────┐
│ Exportar CSV ▾                          │
├─────────────────────────────────────────┤
│ Dataset:                                │
│  ⦿ Resumo (KPIs)                        │
│  ◯ Por vendedor                         │
│  ◯ Provas atrasadas                     │
│  ◯ Provas no periodo                    │
│                                         │
│ Encoding: UTF-8 com BOM (Excel pt-BR)   │
│ Separador: ,                            │
│                                         │
│ [ Baixar ⬇ ]    [ Cancelar ]            │
└─────────────────────────────────────────┘
```

Notas:
- Modal/popover existente preservado. Apenas opção de dataset.
- Encoding e separador fixados (Decisão 6) — não opcionais.

### Cenário 7 — Tabela alternativa (a11y)

Toggle no card do gráfico:

```
┌────────────────────────────────────────────┐
│ Provas Ativas — ESTADO ATUAL    [⬢][≣]    │ ← [⬢]=Grafico, [≣]=Tabela
├────────────────────────────────────────────┤
│ ROTA                  QUANTIDADE  %        │
│ Matriz                       1   5,88%     │
│ Lam. Matriz                  0   0,00%     │
│ Filial                       3  17,65%     │
│ Lam. Filial                  0   0,00%     │
│ Legacy v3.0                 13  76,47%     │
│ ────────────────────                       │
│ Total                       17 100,00%     │
└────────────────────────────────────────────┘
```

- Toggle inline. Sem submenu.
- `<table role="table" aria-labelledby="...">` com `<caption>` sr-only.
- Leitor de tela lê: "Tabela com X linhas, X colunas: Rota, Quantidade, Percentual..."

### Cenário 8 — Estado vazio (sem dados no período)

```
┌──────────────────────────────────────────────────┐
│             ❍                                   │
│         (ilustracao discreta)                    │
│                                                  │
│      Nenhum dado para este periodo.              │
│                                                  │
│   Tente expandir o periodo ou alterar filtros.   │
│                                                  │
│   [ Limpar filtros ]   [ Periodo: 90d ]          │
└──────────────────────────────────────────────────┘
```

### Cenário 9 — Estado de erro (falha no backend)

```
┌──────────────────────────────────────────────────┐
│        ⚠                                        │
│                                                  │
│   Erro ao carregar relatorio.                    │
│   Tente novamente em alguns instantes.           │
│                                                  │
│   [ Tentar novamente ]                           │
└──────────────────────────────────────────────────┘
```

- `role="alert"` para anuncio imediato pelo leitor de tela.
- Botao com `aria-label="Tentar carregar o relatorio novamente"`.

### Cenário 10 — Acesso negado (perfil não-3Studio)

```
┌──────────────────────────────────────────────────┐
│        🔒                                       │
│                                                  │
│   Acesso restrito                                │
│                                                  │
│   Voce nao tem permissao para ver esta pagina.   │
│   Volte para a tela inicial.                     │
│                                                  │
│   [ Voltar para o inicio ]                       │
└──────────────────────────────────────────────────┘
```

- Reusa o componente `<Restricted ruleKey="relatorios" profile={auth.profile} />` da Wave 1 v4.0.
- Mensagem genérica sem revelar quais perfis têm acesso (anti-enumeração).
- Backend retorna 403 ou 404 conforme Decisão 11.

---

## 6. Decisões de design propostas (escalação humana — 11 decisões)

### Decisão 1 — Layout geral dos relatórios

| Opção | Descrição | Trade-offs |
|---|---|---|
| (i) | **Tabs horizontais no topo (mantém estado v3)** — uma perspectiva por tab. | Já entregue, conhecido, 0 trabalho. |
| (ii) | Sidebar à esquerda com lista de relatórios. | Mais escalável se >10 relatórios; mas só 4 hoje + 2 cards extras propostos. |
| (iii) | Página única com tudo empilhado, lazy. | Densidade visual. Bom para print/screenshot. |
| (iv) | Grid de cards na home, cada card abre página. | Disperso para uso operacional. |

**Recomendação técnica:** (i) — preservar tabs (ScopeSelector existente). Adicionar os indicadores novos da v4.0 (Tempo Médio por Etapa) **dentro do scope=geral** como linhas adicionais (Linha 3 do Cenário 1) em vez de criar tab nova. Justifica-se porque (a) o Mario já está acostumado com a UI atual; (b) o backlog v4.0 não diz que precisa de scope novo; (c) preserva muscle memory de quem já usa.

### Decisão 2 — Visualização da Distribuição por Rota

| Opção | Descrição | Trade-offs |
|---|---|---|
| (i) | Pie chart | Familiar; mas pequeno em card compacto. |
| (ii) | **Donut chart compacto + legenda lateral** | Coerente com Donut "Provas Ativas" já existente; espaço bem aproveitado. |
| (iii) | Stacked bar horizontal | Uma linha; lê-se "% por rota"; menos visual. |
| (iv) | Bar vertical | Mais espaço; compara magnitudes. |
| (v) | Donut + tabela ao lado | Toggle Cenário 7 já cobre. |

**Recomendação técnica:** (ii) — `DonutChart` (já existe em `shared/`) com até 5 segmentos (4 v4.0 + Legacy). Reusa as cores propostas em §6.4 da nova paleta de rotas.

### Decisão 3 — Tratamento de provas legacy v3.0 (CRÍTICA)

| Opção | Descrição | Trade-offs |
|---|---|---|
| (i) | **Agrupar como "Legacy v3.0"** — 5ª categoria no gráfico, cor cinza/transparente. | Honesto; não distorce métricas das 4 v4.0; segue o padrão da Timeline (C12) que tem `LEGACY_*` separado. Recomendado. |
| (ii) | Inferir via `vendedor_localizacao` (heurística do C12 — Decisão 11.2). | Distribui legacy entre Matriz/Filial; mas **não distingue laminação** (toda legacy vai para sem-lam). Cria falsa precisão. |
| (iii) | Excluir do indicador de rota, mostrar separadamente "X provas v3.0 sem rota". | Comunica honestamente; mas usuário precisa fazer 2 leituras. |
| (iv) | Switch UI "Incluir legacy?" — usuário escolhe. | Mais flexível; mais botões. |

**Recomendação técnica:** (i). Justifica-se porque hoje 65% das provas em produção são legacy (`rota=NULL`). Inferir via heurística (opção ii) viola dado real — não temos como saber se a prova original era padrão ou direta (heurística usa só localização). Adicionar 5ª categoria com cor distinta preserva integridade.

**Implicação técnica de (i):** Schema backend ganha campo `legacy_count: int` em `DistRota` (ou novo schema `DistRotaV4`). Frontend renderiza 5 segmentos.

### Decisão 4 — Filtros disponíveis

| Filtro | Status na v3 | Proposta v4.0 | Obrigatório? |
|---|---|---|:---:|
| Período | ✅ Existe (default 30d) | Preservar | ✅ |
| Vendedor (multiselect) | ✅ Existe | Preservar | ❌ |
| Rota (segmented) | ✅ Existe (PADRAO/DIRETA) | **EXPANDIR** para 6 valores + "Legacy" | ❌ |
| Status | ✅ Existe (10 valores) | **EXPANDIR** para 17 valores + grupos visuais | ❌ |
| Contexto motorista (3 ctx) | ❌ Não existe | **ADICIONAR** (default: Todos) | ❌ |
| Busca textual (q) | ✅ Existe | Preservar | ❌ |

**Recomendação técnica:** todos os 6 filtros listados, com Contexto motorista condicional (aparece apenas se rota seleciona uma com laminação ou se rota=Todas).

### Decisão 5 — Granularidade temporal do filtro de período

| Opção | Descrição |
|---|---|
| (i) | Apenas atalhos predefinidos (Hoje, 7d, 30d, 90d). |
| (ii) | Apenas date picker customizado. |
| (iii) | **Atalhos predefinidos + opção Customizado** (estado da v3). |

**Recomendação técnica:** (iii) — preservar. O DateRangeFilter já entrega os 4 atalhos + customizado, validado pela auditoria sênior R2 do C16 v3.

### Decisão 6 — Formato de exportação CSV (decisão fixada — não submeter opções)

| Item | Valor proposto | Justificativa |
|---|---|---|
| Encoding | **UTF-8 com BOM** | Excel pt-BR abre sem mojibake (já é o padrão v3 — `CSV_BOM = "﻿"`). |
| Separador | **,** (vírgula) | Padrão Excel internacional; CSV módulo Python default. Mantém v3. |
| Quoting | **Quoting QUOTE_MINIMAL** | csv default; aspear apenas se contém `,` ou `"` ou `\n`. |
| Headers | **pt-BR sem acento ou inglês técnico** | Coerente com snake_case do v3 (`prova_id`, `vendedor_nome`). |
| Filename | `relatorio_{scope}_{dataset}_{from}_{to}.csv` | Mantém v3. RFC 5987 para non-ASCII. |
| Datasets | 4 (mantém v3): summary, by-seller, overdue, proofs | Adicionar coluna `rota` em todos quando aplicável; adicionar coluna `contexto_motorista` em `proofs` e `overdue`. |

**Recomendação técnica:** preservar formato v3 estritamente, apenas adicionar colunas. Mudança no encoding/separador quebra workflows existentes.

### Decisão 7 — Acessibilidade dos gráficos

| Opção | Descrição |
|---|---|
| (i) | Toggle "Gráfico/Tabela" visível em cada gráfico. | Usuário não-vidente alterna; usuário vidente pode usar tabela como atalho de leitura. |
| (ii) | Tabela `sr-only` permanente. | Leitor de tela acessa; vidente nunca vê. |
| (iii) | **Ambos: toggle visível + tabela `sr-only` sempre renderizada com `aria-hidden` quando inativa**. |

**Recomendação técnica:** (i) com tabela renderizada via `aria-hidden` quando inativa — combina o melhor dos dois. Toggle pequeno no canto do card (ícone `⬢`/`≣`); padrão A11Y AAA.

### Decisão 8 — Comparação com período anterior

| Opção | Descrição |
|---|---|
| (i) | Não exibir comparação. | Limpa, baixo custo backend. |
| (ii) | **Manter proxy via metades da serie_temporal (atual)** | Estado v3. `DeltaBadge` já é renderizado. |
| (iii) | Backend retorna comparação real com janela anterior. | Mais preciso; +1 query por chamada; +código. |

**Recomendação técnica:** (ii) — preservar o proxy via metades. Backend não muda. Frontend `computeTotalDelta` continua. Justifica-se porque (a) o usuário entende proxy; (b) backend já está otimizado; (c) v4 não exige comparação real.

### Decisão 9 — Performance / Estratégia de queries (CRÍTICA)

| Opção | Descrição |
|---|---|
| (i) | Queries on-demand, sem cache. | Simples; mas regride 20x. |
| (ii) | **Manter estado v3: on-demand + cache backend TTL 60s + ETag/304 + Realtime invalidation** | Atual. ADR-097/098. Comprovadamente 20x melhor. |
| (iii) | Materialized view com refresh periódico. | Mais rápido em leitura; staleness; complexidade. |
| (iv) | Redis cache. | +dep externa; sem ganho vs (ii) para 30 usuários. |
| (v) | Híbrido (ii) + materialized view para indicador Tempo Médio por Etapa específico. | Apenas se medirmos gap real. |

**Recomendação técnica:** (ii) — preservar. Adicionar indicador novo (Tempo Médio por Etapa) **dentro do mesmo endpoint `?scope=geral`** para herdar o cache existente. Se `EXPLAIN ANALYZE` mostrar > 100ms em staging com fixture realista (10k provas), considerar (v) e propor migration para materialized view (Wave 5.2 ou Wave 6).

### Decisão 10 — Arquitetura de endpoints

| Opção | Descrição |
|---|---|
| (i) | **Endpoint único `/api/v1/reports?scope=...` (estado v3)** | Atual. ADR-096. |
| (ii) | Endpoints separados por relatório. | Sem ganho operacional; aumenta overhead. |
| (iii) | Endpoint base `/api/v1/relatorios/{tipo}`. | Cosmético. |

**Recomendação técnica:** (i) — preservar. **Adicionar indicador novo dentro do schema `ReportResponseGeral`** (campo opcional `tempo_medio_por_etapa: list[TempoMedioEtapa] | None`). Provas legacy populam categoria separada.

### Decisão 11 — Comportamento RBAC: 403 vs 404 anti-enumeração (CRÍTICA — divergência com prompt)

| Opção | Descrição | Coerência |
|---|---|---|
| (i) | **Manter 403 atual** (via `access_required("relatorios")` Wave 1 v4.0) | Coerente com toda Matriz de Acesso (`useAuthorization` + `Restricted`); coerente com 11 outras chaves; testado em `test_reports_api.py:157-208`. |
| (ii) | Mudar para 404 byte a byte idêntico a endpoint inexistente | Cumpre literalmente o prompt v4.0; quebra invariante da Matriz Wave 1; exigiria mudança em `access_required` ou shim específico; testes Wave 1 v4.0 verificam 403 explicitamente. |
| (iii) | Híbrido: 404 só para `/api/v1/reports` (override local) mantendo 403 para outros endpoints. | Inconsistente. Pior dos mundos. |

**Recomendação técnica:** (i) — manter 403. Justifica-se porque:
1. A Matriz de Acesso (`shared/access-matrix.json`) é o sistema canônico de RBAC pós-Wave 1 v4.0. Toda chave segue 403 quando há `acesso: "negado"`.
2. Hoje 12 chaves usam `access_required(...)` — 11 retornam 403, mudar 1 vira regressão.
3. O endpoint **já não revela existência de provas** (filtro RLS retorna 0 rows se vendedor passar). A enumeração relevante é em `/api/v1/provas/{id}` (já protegido).
4. **Anti-enumeração já é entregue em outros pontos** (`/scan` retorna 404 unificado, RLS retorna 0 rows). Para `/api/v1/reports`, 403 é informativo apenas para admin — vendedor/motorista/clicheria **nunca chega ao backend** (middleware Next.js redireciona com base na Matriz).
5. Se o Mario quiser mudar para 404 em `/api/v1/reports`, isso deve ser feito **em toda a Matriz** como sessão dedicada — não pontualmente.

**Escalação obrigatória:** Mario decide. Se decidir (ii), abrir issue/registro para mudar **toda a Matriz** consistentemente.

---

## 7. Plano de arquitetura backend (proposto — não implementar)

### 7.1 Endpoints

**Proposta:** preservar `GET /api/v1/reports?scope={...}` e `GET /api/v1/reports/export?scope={...}&dataset={...}`. Sem novos paths.

**Schema `ReportResponseGeral` ampliado** (proposto):

```python
class TempoMedioEtapa(BaseModel):
    """Tempo médio em horas para uma transição A→B em uma rota específica."""
    model_config = ConfigDict(frozen=True)

    rota_label: str  # "MATRIZ" | "LAM_MATRIZ" | "FILIAL" | "LAM_FILIAL" | "LEGACY"
    etapas: list["EtapaPonto"]  # sequência ordenada
    total_provas_consideradas: int

class EtapaPonto(BaseModel):
    """Uma transição (de_status → para_status) com tempo médio."""
    de_status: StatusProvaEnum | None  # None = início (created_at)
    para_status: StatusProvaEnum
    tempo_medio_horas: float | None
    quantidade_amostras: int

class DistRotaV4(BaseModel):
    """Distribuição por rota — v4.0 com 4 rotas + legacy."""
    rota: RotaEnum | None  # None significa rota=NULL legacy
    quantidade: int
    categoria: Literal["v4", "legacy_padrao", "legacy_direta", "legacy_null"]

class ReportResponseGeral(BaseModel):
    # ... preservar tudo da v3 ...

    # NOVO v4.0:
    distribuicao_rota_v4: list[DistRotaV4]  # substitui distribuicao_rota; preserva campo antigo deprecado
    tempo_medio_por_etapa: list[TempoMedioEtapa]  # 1 entry por rota com dados
    contexto_motorista_dist: list["DistContextoMotorista"] | None  # apenas scope=geral
```

**Por que preservar `distribuicao_rota` deprecado:**
Garantia de não-regressão para clientes que ainda consomem o JSON v3. Decisão é eliminá-lo na Wave 7 (Componente 21 — backfill final).

### 7.2 Queries SQLAlchemy 2.0 async (esquemáticas)

**Q1 nova — distribuição expandida por rota:**

```python
stmt_dist_rota = (
    select(
        ProvaDigital.rota,
        func.count().label("qtd"),
    )
    .select_from(ProvaDigital)
    .where(_periodo_filter(filters))
    .group_by(ProvaDigital.rota)
)
```

GROUP BY direto na coluna `rota` — usa `idx_provas_rota` (B-tree, advisor unused mas funcional). Retorna 1 linha por rota presente + 1 linha para NULL.

**Q2 nova — tempo médio por etapa:**

```python
# Por rota v4.0: usa estados_da_rota(rota) + LAG over (partition by prova_id order by created_at)
# para calcular delta entre transições consecutivas.
stmt_tempo_etapa = text("""
    WITH transicoes AS (
        SELECT
            p.id AS prova_id,
            p.rota,
            m.status_novo,
            m.created_at,
            LAG(m.created_at) OVER (
                PARTITION BY p.id ORDER BY m.created_at
            ) AS anterior_at,
            LAG(m.status_novo) OVER (
                PARTITION BY p.id ORDER BY m.created_at
            ) AS anterior_status
        FROM provas_digitais p
        JOIN movimentacoes m ON m.prova_id = p.id
        WHERE p.created_at >= :from_ AND p.created_at < :to_
    )
    SELECT
        rota,
        anterior_status,
        status_novo,
        AVG(EXTRACT(EPOCH FROM (created_at - anterior_at))) / 3600.0 AS tempo_medio_horas,
        COUNT(*) AS amostras
    FROM transicoes
    WHERE anterior_at IS NOT NULL
    GROUP BY rota, anterior_status, status_novo
    HAVING COUNT(*) >= 1;
""")
```

- Window function `LAG()` evita N+1.
- Filtra `WHERE anterior_at IS NOT NULL` (1ª transição usa `created_at` da prova, ver abaixo).
- Pode ser feita pura SQL ou via `select(...).from_select(CTE)`.

**Q3 nova — distribuição por contexto motorista:**

```python
stmt_contexto = (
    select(
        ProvaDigital.status,
        func.count().label("qtd"),
    )
    .select_from(ProvaDigital)
    .where(
        _periodo_filter(filters),
        ProvaDigital.status.in_([
            StatusProvaEnum.COM_MOTORISTA,  # legacy → entrega_final
            StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO,
            StatusProvaEnum.COM_MOTORISTA_VOLTA_LAMINACAO,
            StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL,
        ]),
    )
    .group_by(ProvaDigital.status)
)
```

Frontend agrupa status → contexto via `contextoMotorista()`. Backend retorna status raw.

### 7.3 Materialized view (não recomendada para esta sessão)

Decisão 9 → (ii). Sem materialized view nesta sessão. Avaliar se EXPLAIN ANALYZE em staging com `seed_reports_fixture.py` (1k+ provas, ADR-098) mostrar Q2 > 100ms.

### 7.4 Caching

Preservar `ReportCache` TTL 60s + ETag SHA-256. Sem mudança.

### 7.5 RLS

**Nenhuma migration RLS necessária** se preservarmos 403 (Decisão 11 → i). A política `pol_provas_select` já tem branch `app_private.current_user_is_admin()`. Admin acessa todas as linhas; perfis não-admin filtrados naturalmente.

Se Decisão 11 → (ii) [404], **migration RLS 016** revisará policies para retornar 0 rows em vez de 403 — mas isso quebra outros endpoints.

### 7.6 Anti-enumeração

Já entregue via RLS + `access_required("relatorios")`. Vendedor que chega ao endpoint backend:
1. Recebe 403 da Wave 1 RBAC.
2. Se hipoteticamente passasse, RLS retornaria 0 rows.

Defesa em profundidade preservada.

---

## 8. Plano de migration Alembic

Avaliação: **nenhuma migration Alembic necessária**.

Justificativa:
- Não há mudança de schema (sem coluna nova, sem tabela nova).
- Índice `idx_provas_rota` já existe.
- Índice `idx_movimentacoes_prova_data` já cobre window function `LAG()`.

Se EXPLAIN ANALYZE em staging mostrar lentidão na Q2 (tempo por etapa), considerar `idx_movimentacoes_prova_status_novo` (composto) — proposta condicionada a evidência.

---

## 9. Plano de migration RLS

Avaliação: **nenhuma migration RLS necessária** se Decisão 11 → (i) (manter 403).

Se Decisão 11 → (ii) (mudar para 404), abrir sessão dedicada (fora desta entrega) para refatorar a Matriz inteira coerentemente.

---

## 10. Plano de arquitetura frontend

### 10.1 Hierarquia de componentes (proposta)

```
<RelatoriosPage> (existente, preservado)
  <Suspense>
    <RelatoriosContent>
      <Header>
        <Title /> <PeriodoBadge /> <ExportButton />
      </Header>
      <ScopeSelector />
      <FiltersBar>
        <DateRangeFilter />
        <SearchInput />
        <StatusFilter />  ← AMPLIAR para 17 valores
        <VendedorFilter />
        <RotaFilter />  ← AMPLIAR para 6 valores + Legacy
        <ContextoMotoristaFilter />  ← NOVO (condicional)
      </FiltersBar>

      <PerspectivaRenderer> (switch existente)
        <ReportGeral>
          <Linha1KPIs> (4 cards — preservada)
            <CardTotal /> <CardTempoAprov /> <CardTaxaReprov />
            <CardRota /> ← REDESIGN para 5 categorias
          </Linha1KPIs>
          <Linha2Cards> (3 cards — preservada)
            <CardDonutAtivas /> <CardVendorRow /> <CardVendorHighlight />
          </Linha2Cards>
          <Linha3NovoIndicador> ← NOVO v4.0
            <TempoMedioPorEtapaCard rota="MATRIZ" />
            <TempoMedioPorEtapaCard rota="LAM_MATRIZ" />
            <TempoMedioPorEtapaCard rota="FILIAL" />
            <TempoMedioPorEtapaCard rota="LAM_FILIAL" />
            <TempoMedioPorEtapaCard rota="LEGACY" />  (se houver dados)
          </Linha3NovoIndicador>
          <RankingTable /> (preservada)
          <ProvasAtrasadasTable /> (preservada)
        </ReportGeral>

        <Report3Studio> (preservado)
        <ReportVendedores> (preservado)
        <ReportClicheria>
          <CardRecebidas /> <CardTempoMedio />
          <CardEmTransito />
          <CardOrigemRota /> ← REDESIGN: v4.0 distingue MATRIZ/LAM_MATRIZ/FILIAL/LAM_FILIAL em vez de via_padrao/via_direta
        </ReportClicheria>
      </PerspectivaRenderer>
    </RelatoriosContent>
  </Suspense>
</RelatoriosPage>
```

### 10.2 Novos subcomponentes

| Componente | Caminho proposto | Reuso |
|---|---|---|
| `TempoMedioPorEtapaCard` | `.../relatorios/perspectivas/cards/TempoMedioPorEtapaCard.tsx` | Reusa `BarChart` shared |
| `ContextoMotoristaFilter` | `.../relatorios/ContextoMotoristaFilter.tsx` | Padrão segmented pill como `RotaFilter` |
| `RouteDistributionTable` | inline em `ReportGeral.tsx` | Toggle Gráfico/Tabela (Decisão 7) |

### 10.3 CSS Modules

Novo CSS Module: `frontend/src/app/(dashboard)/relatorios/perspectivas/cards/tempo-medio-por-etapa.module.css` (≤80 LOC esperado).

Atualizações em `relatorios.module.css` (existente):
- Adicionar `.rotaLegendItemMatriz`, `.rotaLegendItemLamMatriz`, etc — 5 entradas em vez de 2.
- Adicionar `.toggleViewButton` para alternar Gráfico/Tabela.
- Adicionar `.contextoMotoristaFilter` para o filtro novo.

### 10.4 Tipos TypeScript (proposta)

```typescript
// lib/types/report.ts (ampliar)
export interface TempoMedioEtapa {
  rota_label: string;  // 'MATRIZ' | 'LAM_MATRIZ' | 'FILIAL' | 'LAM_FILIAL' | 'LEGACY'
  etapas: EtapaPonto[];
  total_provas_consideradas: number;
}

export interface EtapaPonto {
  de_status: StatusProva | null;
  para_status: StatusProva;
  tempo_medio_horas: number | null;
  quantidade_amostras: number;
}

export interface DistRotaV4 {
  rota: Rota | null;
  quantidade: number;
  categoria: 'v4' | 'legacy_padrao' | 'legacy_direta' | 'legacy_null';
}

export interface DistContextoMotorista {
  contexto: ContextoMotorista;
  quantidade: number;
}
```

---

## 11. Plano de exportação CSV (proposta)

### 11.1 Datasets (preservar 4 + adicionar colunas)

| Dataset | Colunas v3 | Colunas adicionadas v4.0 |
|---|---|---|
| `summary` | scope, indicador, valor | `rota_MATRIZ`, `rota_LAM_MATRIZ`, etc; `tempo_etapa_<rota>_<de>_<para>` |
| `by-seller` | vendedor_id, nome, localização, volume, taxa_aprov, taxa_reprov, tempo_med, atrasadas | Sem mudança — vendedor agnostic a rota; opcionalmente `rotas_distribuicao` |
| `overdue` | prova_id, nro_req, nome, cliente, status, rota, vendedor_nome, localizacao, created_at, ultima_mov, horas_atrasada | `contexto_motorista` (derivado server-side via `contexto_motorista()`) |
| `proofs` | prova_id, nro_req, nome, cliente, status, rota, ciclo_atual, vendedor_nome, localizacao, created_at, updated_at, motivo_cancelamento | `contexto_motorista` + `codigo_publico` (já está no schema mas não no CSV) |

### 11.2 Audit log

`acao=REPORT_EXPORTED` preservado. Detalhes: `scope`, `dataset`, filtros — manter v3.

---

## 12. Plano de acessibilidade

| Item | Status v3 | Plano v4.0 |
|---|:---:|---|
| ARIA labels descritivos em gráficos | ⚠️ Parcial | Adicionar `aria-label` específico em cada gráfico novo |
| `role="table"` + `<caption>` sr-only | ✅ Existe em tabelas | Replicar nos modos Tabela alternativa (Decisão 7) |
| Toggle Gráfico/Tabela | ❌ Não existe | **NOVO** — Decisão 7 |
| Tabela alternativa `sr-only` permanente | ❌ Não existe | **NOVO** — Decisão 7 (ambos) |
| Navegação por teclado | ✅ Filtros existentes | Validar nos componentes novos |
| `prefers-reduced-motion` | ⚠️ Parcial em Sparkline | Replicar em `TempoMedioPorEtapaCard` |
| `aria-live="polite"` | ⚠️ Apenas error/alert | Adicionar para "Atualizando..." e "Atualizado em ..." |
| Contraste AA mínimo | ✅ Atendido | Validar cores novas (5 segmentos de rota) |
| Foco visível | ✅ Existe | Validar toggles novos |
| axe-core CI | ❌ Não configurado | Adicionar `@axe-core/playwright` ou similar em E2E |

---

## 13. Plano de performance

### 13.1 Alvos

- Carga inicial < 3s (RNF-001).
- Mudança de filtro < 1s (alvo mais estrito v4.0).
- Sem N+1.

### 13.2 Mitigações

- Preservar cache TTL 60s + ETag + Realtime invalidation (Decisão 9 → ii).
- Query nova de tempo por etapa usa window function `LAG()` — 1 query, sem N+1.
- Frontend: `useMemo` para `padraoCount`, `diretaCount`, novos contadores por rota; memoizar `ativosData`, `tempoMedioRanking`, `rankingByVolume`.
- Bundle: cota atual `/relatorios` em 11.4 kB / 200 kB First Load (Wave 5 v3 closeout). Adição de `TempoMedioPorEtapaCard` esperada: +1-2 kB. Sem novas deps.
- Lazy-loading dos componentes Report3Studio/Vendedores/Clicheria pode ser feito via `next/dynamic` se necessário (não recomendado para esta sessão — bundle ainda baixo).

### 13.3 Medição

`scripts/seed_reports_fixture.py` (ADR-098) gera 1k+ provas em staging. Validar EXPLAIN ANALYZE de Q1, Q2, Q3 propostas. Aceitável < 100ms por query.

---

## 14. Estratégia de testes (exaustiva)

### 14.1 Backend (extensão dos 14 test classes existentes)

| Test class | Cobertura nova v4.0 |
|---|---|
| `TestReportsScopeRouting` | + asserções: 4 rotas v4.0 em response + categoria legacy |
| `TestReportsValidacao` | + `?rota=MATRIZ` aceito; `?status=COM_MOTORISTA_IDA_LAMINACAO` aceito |
| **NOVO** `TestDistRotaV4` | 5 cenários: solo v4.0, solo legacy, misto, vazio, filtros combinados |
| **NOVO** `TestTempoMedioPorEtapa` | 5 cenários: rota MATRIZ com sequência completa, LAM_MATRIZ com laminação, FILIAL curta, LAM_FILIAL, LEGACY agrupada |
| **NOVO** `TestContextoMotoristaDist` | 4 cenários: 3 contextos v4.0 + 1 legacy COM_MOTORISTA = entrega_final |
| `TestReportsExport` | + colunas novas em todos os 4 datasets validadas |
| `TestReportsFiltros` | + filtros v4.0 combinados |

Total novo esperado: ~20 testes. Cobertura ≥ 80% nos novos endpoints/queries.

### 14.2 Frontend (Vitest)

| Test file | Cobertura nova v4.0 |
|---|---|
| `tempo-medio-por-etapa-card.test.tsx` | 4 cenários: render por rota; render vazio; render legacy; toggle gráfico/tabela |
| `rota-filter.test.tsx` | 7 opções: Todas + 4 v4.0 + 2 legacy + click toggle |
| `contexto-motorista-filter.test.tsx` | Condicional: aparece se rota IN {LAM_*, NULL}; oculto se rota IN {MATRIZ, FILIAL} |
| `dist-rota-v4.test.tsx` | Renderiza 5 categorias com cores corretas; usa `getRotaLabel` para legacy |
| `use-report-filters.test.tsx` | `parseRota` aceita 6 valores; `parseStatus` aceita 17 valores |
| `use-report-filters-anti-enumeration.test.tsx` | URL com rota inválida → null (não atira); URL com status inválido → null |

Total novo esperado: ~30 testes Vitest. Vitest atual em 163 → ~193.

### 14.3 E2E (Playwright)

Não configurado hoje. Para esta sessão: **fora de escopo** — Playwright requer setup novo (ADR a registrar para Wave 6 ou Wave 7).

Substitutos: smoke validation manual (template `smoke-validation.md` como em C12) + axe-core em CI (proposta nova).

### 14.4 axe-core

Proposta: instalar `@axe-core/playwright` ou similar leve apenas para CI; ou em alternativa, validar manualmente em staging com extensão axe DevTools antes do merge.

### 14.5 Cobertura ≥ 80%

Critério mantido. Coverage snapshot via `@vitest/coverage-v8` instalável temporariamente (padrão D-13 Wave 1 v4.0).

---

## 15. Plano de testes de regressão

Validar que **nenhuma das entregas anteriores quebra**:

| Wave/Componente | Validação |
|---|---|
| C12 (Timeline) | `npx vitest run frontend/src/lib/__tests__/timeline-builder.test.ts` → 20 testes verdes |
| C11 (Máquina v4.0) | `pytest backend/tests/state_machine/` → 139 testes verdes |
| C10/C19 (Scanner/Manual) | `pytest backend/tests/test_provas_api.py::TestScan` → todos verdes |
| C08 (Detalhe) | Render OK; `npx tsc --noEmit` → 0 erros |
| C06 (Cadastro) | `pytest backend/tests/test_codigo_publico_service.py` → 20 verdes |
| Wave 1 (RBAC) | `python scripts/verify_rbac_equivalence.py` → SUCESSO; `pytest backend/tests/access/` → 36 verdes |
| **C15 (Dashboard v3 — VALIDAÇÃO OBRIGATÓRIA)** | `pytest backend/tests/test_dashboard.py` → todos verdes; `next build` sem regressão de bundle em `/dashboard` |
| Wave 4 (Dashboard) | `next build`; bundle `/dashboard` ≤ 3.18 kB (baseline pós-C17 v3) |
| Wave 5 v3 (Relatórios v3) | `pytest backend/tests/test_reports_api.py` → 209 testes verdes **+ novos da v4** |
| Wave 6 (Audit Log) | `pytest backend/tests/test_audit_log_api.py` → todos verdes |

**Comando único de não-regressão:**
```
pytest backend/tests/ -x --tb=short
npx tsc --noEmit
npx vitest run
npx next build
```

---

## 16. Riscos e pontos de atenção

| ID | Risco | Severidade | Mitigação |
|---|---|:---:|---|
| R1 | **Distorção de métricas por contagem legacy** — se Distribuição por Rota mistura legacy sem identificá-lo, percentuais ficam errados. | 🔴 ALTO | Decisão 3 → (i): categoria "Legacy v3.0" separada visualmente. |
| R2 | **Anti-enumeração ambígua** — prompt v4 pede 404, Matriz Wave 1 retorna 403. | 🔴 ALTO | Decisão 11 → (i): manter 403; documentar trade-off; abrir issue para revisão global se Mario discordar. |
| R3 | **Realtime invalidation regredir** — `provas_digitais` na publicação `supabase_realtime` (Wave 4 / RLS 007). Se schema/policy mudar, Realtime pode parar. | 🟡 MÉDIO | Sem mudança em RLS proposta; preservar atual. |
| R4 | **Rendering timeline de tempos por etapa heterogênea** — MATRIZ=6, LAM_MATRIZ=11, FILIAL=4, LAM_FILIAL=7 etapas. UI precisa renderizar bem em larguras diferentes. | 🟡 MÉDIO | `BarChart` shared já é flex; testar em mobile. |
| R5 | **Regressão C15 Dashboard v3** — `/api/v1/provas/dashboard` consome `provas_digitais`. Se mudarmos RLS para anti-enumeração estrita (não recomendado), Dashboard regride. | 🟡 MÉDIO | Decisão 11 → (i) preserva RLS. |
| R6 | **Hard-code de cores/labels** — fácil de regredir se desenvolvedor copia código antigo do `ReportGeral.tsx`. | 🟢 BAIXO | String-matching CI: nenhum literal `"PADRAO"`/`"Padrao"`/`"DIRETA"`/`"Direta"` em files novos — usar `ROTA_LABELS[rota]`. |
| R7 | **Bundle size aumentando** — `/relatorios` em 11.4 kB / 200 kB. Card novo pode adicionar 2-3 kB. | 🟢 BAIXO | Monitorar via `next build`; limite suave 12 kB / 205 kB. |
| R8 | **Performance da window function `LAG()`** — depende de índice composto `(prova_id, created_at)`. | 🟡 MÉDIO | `idx_movimentacoes_prova_data` já existe (Wave 0); EXPLAIN ANALYZE em staging. |
| R9 | **Acessibilidade insuficiente** — Recharts (que não usamos) é notoriamente ruim; SVG inline depende de ARIA bem aplicado. | 🟡 MÉDIO | Decisão 7 → toggle Tabela; axe-core; leitor de tela em staging. |
| R10 | **CSV com `contexto_motorista` quebra Excel** se contém caractere especial. | 🟢 BAIXO | `csv.writer` Python já escapa; teste explícito. |
| R11 | **Indicador Tempo Médio por Etapa sem dados em produção** — só 1 prova v4.0 hoje (MATRIZ). | 🟡 MÉDIO | Render gracioso "Sem dados" + tooltip "Aguardando uso v4.0". Fixture seed para testes. |
| R12 | **Filtro de Contexto Motorista — quando aparecer?** | 🟢 BAIXO | Mostrar sempre em scope=geral; só desabilitado se rota=MATRIZ/FILIAL (sem laminação). |
| R13 | **Estado vazio mal-tratado** | 🟢 BAIXO | Cenário 8 do design + teste E2E manual. |
| R14 | **Estado de erro mal-tratado** | 🟢 BAIXO | Cenário 9 do design + retry button. |
| R15 | **Decisões de design subjetivas sem Figma** | 🟡 MÉDIO | ASCII wireframes + escalação humana antes de implementar (Gate 1). |
| R16 | **C15 (Dashboard) regredir indiretamente via shared `useDashboard`** | 🟢 BAIXO | C16 v4.0 não toca em `useDashboard.ts`. Validar diff. |
| R17 | **`STATUS_VALORES` em `useReportFilters` foi hard-codeado** — extensão para 17 estados precisa também atualizar `STATUS_OPTIONS` (que já tem 17) → reusar. | 🟢 BAIXO | Substituir `STATUS_VALORES` por `STATUS_OPTIONS` importado de `lib/types/prova`. |
| R18 | **`DistOrigemRota` schema legacy** — `via_padrao`/`via_direta` (Clicheria). Manter para v3; expandir para v4 com novo campo `por_rota_v4`. | 🟡 MÉDIO | Não-disruptivo; aditivo. |

---

## 17. Apêndice — Decisões já fixadas pelo prompt do C16 v4.0

| Item | Fixado | Origem |
|---|---|---|
| Acesso restrito a 3Studio | ✅ | Backlog v4.0 C16 + Wave 1 v4.0 Matriz `relatorios` |
| Branch parte de `development` | ✅ | Prompt §0 |
| PR aponta para `development` | ✅ | Prompt §6.1 |
| Reuso do `contrato-c12.md` | ✅ | Prompt §1.2 |
| Sem Framer Motion novo | ✅ | Prompt §1.2 |
| Sem trocar Recharts | ✅ ⚠️ Recharts já removido na W4 — preservar SVG inline | Prompt §6.2 + WAVE5_CLOSEOUT.md §99 |
| RLS via helpers `app_private.current_user_is_admin()` | ✅ | Wave 1 v4.0 RLS 012 |
| Timezone UTC + datetime `America/Sao_Paulo` para UI | ✅ | Padrão do projeto |
| Migrations Alembic reversíveis | ✅ | Padrão |
| Padrões TypeScript estrito | ✅ | Padrão |
| `populate_by_name=True` + frozen=True schemas | ✅ | Padrão Wave 5 v3 |

---

## 18. Próximos passos (resposta esperada do Mario)

1. **Responder explicitamente às 11 decisões** acima (D1..D11) — Mario pode aprovar a recomendação técnica ou escolher outra opção / pedir alteração.
2. **Emitir a string `AUTORIZADO GATE 2 — WAVE 5 v4.0 / C16`** após decisões.
3. Esta análise NÃO escreve código de produção, NÃO aplica migration, NÃO abre PR até a autorização chegar.

---

**Fim do Gate 1.** Aguardando decisões humanas e autorização para Gate 2.

---

# Apêndice A — Execução (Gate 2)

**Data:** 2026-05-13.
**Branch:** `wave5-v4/componente-16` (sai de `development`).
**Autorização do Mario:** "Vamos seguir sua recomendação, desde que não altere nada no layout que temos hoje em dia."

## A.1 Decisões aprovadas + adaptações para "preservar layout"

| # | Decisão | Aprovada | Adaptação para preservar layout |
|---|---|:---:|---|
| **D1** | Layout geral | ✅ recomendação (i) — tabs preservadas | Sem nova linha 3 (Tempo Médio por Etapa **NÃO entregue** como UI; backend prepara campos para Wave 6+) |
| **D2** | Donut Distribuição por Rota | ✅ recomendação (ii) | **Donut completo NÃO entregue** como UI (substituiria card ROTA atual). Backend expõe `distribuicao_rota_v4` via API e CSV para programmatic. UI card ROTA continua 2 dots (Matriz/Filial) com semântica consolidada |
| **D3** | Tratamento legacy v3.0 | ✅ recomendação (i) consolidada | Backend popula `consolidacao_rota.matriz/filial/indefinida` agregando v4.0 + legacy explícita + legacy NULL (heurística C12 Decisão 11.2 via `vendedor.localizacao`); UI 2 dots cobre tudo |
| **D4** | Filtros disponíveis | ✅ todos preservados | Filtros novos `rota_categoria` (matriz/filial) e Contexto Motorista — apenas o `rota_categoria` é exposto na UI (via `RotaFilter` reformatado para 3 botões: Todas/Matriz/Filial); Contexto Motorista **NÃO** exposto visualmente (preserva layout); valor disponível na API/CSV |
| **D5** | Granularidade temporal | ✅ recomendação (iii) | Sem mudança — DateRangeFilter v3 preservado |
| **D6** | Formato CSV | ✅ recomendação fixa | UTF-8 com BOM + vírgula + QUOTE_MINIMAL preservados; **adições aditivas:** colunas `contexto_motorista` e `codigo_publico` em `proofs`/`overdue`; linhas `rota_v4_*`, `consolidacao_rota_*`, `contexto_motorista_*` em `summary` |
| **D7** | A11y dos gráficos | ✅ recomendação (iii) → ajustado para (ii) | Sem toggle visível (preserva layout). Tabela sr-only **permanente** adicionada ao `DonutChart` (em paralelo ao `<details>` v3); `<details>` interno marcado `aria-hidden="true"` para evitar duplicação na leitura por AT |
| **D8** | Comparação período anterior | ✅ recomendação (ii) | Sem mudança — proxy via metades preservado |
| **D9** | Estratégia de queries | ✅ recomendação (ii) | Cache TTL 60s + ETag + Realtime preservado; novas queries (`rota_v4_*`, `contexto_motorista`) compartilham o mesmo agregador (1 fetch, hit no cache) |
| **D10** | Arquitetura de endpoints | ✅ recomendação (i) | Endpoint único preservado; campos novos aditivos no schema `ReportResponseGeral` |
| **D11** | RBAC 403 vs 404 | ✅ recomendação (i) | 403 preservado — coerência com Matriz Wave 1 v4.0 |

## A.2 Diff entre proposta (Gate 1) e execução (Gate 2)

| Item | Proposta no analysis.md | Entregue |
|---|---|---|
| Linha 3 nova "Tempo Médio por Etapa" (Cenário 1) | Sim — card largo visível | **Não entregue como UI** (alteraria layout). Backend pode adicionar futuramente; ADR-162 documenta o porquê |
| Card ROTA reformulado com Donut 5 segmentos (Cenário 2) | Sim | **Não entregue como UI**. Card ROTA continua 2 dots; semântica de cada dot expandida |
| Filtro Contexto Motorista (Cenário 5) | Sim — exposto na FiltersBar | **Não entregue visualmente.** API aceita filtro, frontend não expõe |
| Toggle Gráfico/Tabela (Cenário 7) | Sim — visível por card | **Não entregue como UI.** Tabela `sr-only` permanente substitui (Opção D7-ii) |
| Tempo Médio por Etapa (D10 backend) | `tempo_medio_por_etapa: list[TempoMedioEtapa]` no schema | **Adiado** — sem demanda visual atualmente; criar quando UI exigir (Wave 6) |
| `distribuicao_rota_v4` | Sim | ✅ Entregue (9 categorias) |
| `consolidacao_rota` | Sim | ✅ Entregue (matriz/filial/indefinida) |
| `contexto_motorista_dist` | Sim | ✅ Entregue (3 contextos) |
| `rota_categoria` (filtro consolidado) | Sim | ✅ Entregue |
| Aceitação de 6 rotas + 17 status nos filtros | Sim | ✅ Entregue |
| CSV proofs/overdue com `contexto_motorista` | Sim | ✅ Entregue + `codigo_publico` extra |
| CSV summary com `rota_v4_*` + `consolidacao_rota_*` + `contexto_motorista_*` | Sim | ✅ Entregue |
| Estender `_aggregate_clicheria` para v4.0 | Sim | ✅ `via_padrao` agora inclui `COM_MOTORISTA_ENTREGA_FINAL`; `via_direta` inclui `APROVADA→RECEBIDA` direto para FILIAL/LAM_FILIAL |
| Migration Alembic | Nenhuma | ✅ Nenhuma criada |
| Migration RLS | Nenhuma | ✅ Nenhuma criada |
| 403 anti-enumeração | Preservar | ✅ `access_required("relatorios")` mantido |
| Recharts | Não reintroduzir | ✅ SVG inline preservado |

## A.3 Arquivos alterados

### Backend (4 arquivos)

| Arquivo | Mudança |
|---|---|
| `backend/app/domain/schemas/report.py` | +`DistRotaV4`, `ConsolidacaoRota`, `DistContextoMotorista`, `RotaCategoria` enum, `DistRotaV4Categoria` enum; estendeu `ReportResponseGeral` com 3 campos opcionais aditivos; estendeu docstring de `DistOrigemRota` |
| `backend/app/services/report_filters.py` | +`RotaCategoria`; `ReportFilters.rota_categoria` aditivo; docstrings v4.0 |
| `backend/app/api/v1/reports.py` | +`_ROTAS_MATRIZ`, `_ROTAS_FILIAL`, `_CLICHERIA_CHEGADA_LEGACY`, `_CLICHERIA_CHEGADA_V4_VIA_MOTORISTA`, `_CLICHERIA_CHEGADA_V4_VIA_DIRETO`, `_CONTEXTO_MOTORISTA_STATUSES`, `_categoria_predicate()`, `_contexto_motorista_csv()`; Q1 do `_aggregate_geral` expandida para popular novos campos; `_aggregate_clicheria` semântica v4.0; CSV proofs/overdue + `contexto_motorista` + (proofs) `codigo_publico`; CSV summary + rota_v4_* + consolidacao_rota_* + contexto_motorista_* |
| `backend/tests/test_reports_v4.py` | **NOVO** — 60 testes cobrindo `rota_categoria`, 6 rotas, 17 status, novos campos do payload, paridade contextoMotorista, baldes disjuntos+cobertura, chegadas clicheria v4.0 |

### Frontend (7 arquivos)

| Arquivo | Mudança |
|---|---|
| `frontend/src/lib/types/report.ts` | +`RotaCategoria` type; +`DistRotaV4Categoria`, `DistRotaV4Item`, `ConsolidacaoRota`, `DistContextoMotoristaItem` interfaces; estendeu `ReportFilters.rota_categoria` aditivo; estendeu `ReportResponseGeral` com 3 campos opcionais aditivos |
| `frontend/src/hooks/useReportFilters.ts` | `parseRota` aceita 6 valores (importa `ROTA_OPTIONS`); `parseStatus` aceita 17 (importa `STATUS_OPTIONS`); +`parseRotaCategoria`; +`filters.rota_categoria` no useMemo + setter + toQueryString |
| `frontend/src/app/(dashboard)/relatorios/RotaFilter.tsx` | **Reescrito** — 3 botões visualmente idênticos (Todas/Matriz/Filial); agora opera sobre `RotaCategoria` em vez de `Rota`; props `value: RotaCategoria \| null` + `onChange: (categoria) => void` |
| `frontend/src/app/(dashboard)/relatorios/page.tsx` | `<RotaFilter>` recebe `filters.rota_categoria` em vez de `filters.rota` |
| `frontend/src/app/(dashboard)/relatorios/perspectivas/ReportGeral.tsx` | `matrizCount`/`filialCount` substituem `padraoCount`/`diretaCount`; usa `data.consolidacao_rota?.matriz/filial` com fallback para `distribuicao_rota` legacy; labels do card ROTA: "Padrao"→"Matriz", "Direta"→"Filial" |
| `frontend/src/app/(dashboard)/relatorios/shared/DonutChart.tsx` | +tabela `sr-only` permanente (D7-ii); marcou `<details>` interno com `aria-hidden="true"` para evitar duplicação na leitura por AT |
| `frontend/src/hooks/__tests__/useReportFilters.test.ts` | **NOVO** — 42 testes Vitest cobrindo parseRota/parseStatus/parseRotaCategoria + paridade com ROTA_OPTIONS/STATUS_OPTIONS |

## A.4 Validação final

| Verificação | Resultado |
|---|---|
| Backend pytest | **1027 passed + 10 skipped** (baseline pós-C12 era 967 + 10; +60 da Wave 5 v4.0) |
| Frontend Vitest | **205 passed** (era 163; +42 novos) |
| `tsc --noEmit` | Exit 0 |
| `next build` | 13/13 páginas; `/relatorios` em **17.9 kB / 220 kB** (era 11.4 kB / 200 kB na Wave 5 v3 — overhead +6.5 kB pelos campos novos de tipo + lógica de fallback + tabela sr-only) |
| Advisors MCP `security` | 2 (1 INFO alembic_version intencional + 1 WARN auth_leaked_password WONTFIX) — **idêntico ao baseline pós-C12, sem novos alertas** |
| Advisors MCP `performance` | 13 INFO `unused_index` — **idêntico ao baseline pós-C12** (esperado em volume baixo) |
| Migration Alembic nova | Nenhuma |
| Migration RLS nova | Nenhuma |

## A.5 Pendências para PR em `main`

Mantidas (herdadas da Wave 3):
- Rate limit backend C19 (ADR-145).
- Benchmarks C11 (ADRs 153/157).
- CI/CD pós-Wave 3 (ADR-156).
- Smoke E2E manual da Timeline.

Específicas C16 v4.0 (ver `smoke-validation.md`):
- Smoke E2E manual: verificar que filtro "Matriz" inclui todas as v4.0 + legacy PADRAO + legacy NULL com vendedor MATRIZ; idem "Filial".
- Verificar visualmente que o card ROTA mostra "Matriz N · Filial N" (labels novos).
- Verificar a11y com leitor de tela (NVDA/VoiceOver) — tabela sr-only acessível imediatamente sem clique no `<details>`.
- CSV download programatico: validar colunas novas em `proofs`, `overdue`, `summary`.

## A.6 Limitações conhecidas

- **Indicador Tempo Médio por Etapa**: backend não calcula. Adiado para Wave 6 quando UI for criada (ADR-162).
- **Filtro Contexto Motorista**: backend recebe sem expor visualmente; frontend sem botão para ativar. Adiado.
- **Distribuição por Rota detalhada (5 segmentos)**: backend expõe via API + CSV; frontend não renderiza. Adiado.

**Fim do Apêndice A.** Próxima sessão: PR para `development`, smoke E2E manual pelo Mario, então auditoria sênior independente.
