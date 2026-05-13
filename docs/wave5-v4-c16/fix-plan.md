# Plano de Correção — Componente 16 · Wave 5 v4.0

**Branch (Gate 1 — plano):** `wave5-v4-c16/fixes/plan` (sai de `wave5-v4-c16/audit` HEAD `57a76d2`, que contém o C16 + audit-report).
**Branch (Gate 2 — execução):** `wave5-v4-c16/fixes/execution` (a criar a partir desta mesma base após autorização).
**PR aponta para:** `development`.
**Data:** 2026-05-13.
**Fonte dirigente:** [`docs/wave5-v4-c16/audit-report.md`](audit-report.md) (Veredito **Aprovado com correções — 17 achados**).
**Persona:** Engenheiro de Software Sênior com 15+ anos.
**Marco:** Última sessão de correção de componente da Wave 5 v4.0. Após ela, sessão de revisão consolidada pré-merge (Wave 3 + Wave 5 juntas) antes de `development → main`.

---

## 0. Nota sobre a base do branch

O prompt diz "sai de `development`". Em sentido estrito, `origin/development` está em `f518a94` (Merge `wave3-v4-c12/fixes/execution`) e **NÃO** contém os 9 commits do C16 nem o `audit-report.md` (o PR do C16 contra `development` ainda não foi mergeado). Por isso, "sai de `development`" é interpretado como **destino do PR final**, e a base prática do trabalho é `wave5-v4-c16/audit` (que tem o C16 entregue + o relatório auditado). O PR de correção será aberto contra `development` — quando mergeado, traz todo o C16 + auditoria + fix-plan + correções + fix-validation em uma única ação.

---

## 1. Confirmação de leitura

### 1.1 Artefatos da Seção 2.1 do prompt

| # | Artefato | Caminho | Status |
|---|---|---|:---:|
| 1 | `docs/wave5-v4-c16/audit-report.md` | repo | ✅ Lido integralmente (668 linhas) |
| 2 | `docs/wave3-v4-c11/contrato-c12.md` | repo (intocado, último commit Wave 3 C11 `f57ba28`) | ✅ Lido (409 linhas) |
| 3 | `docs/wave5-v4-c16/visual-guide.md` | recomendado pelo C12 | ❌ AUSENTE (AUD-W5C16-001) |

### 1.2 Arquivos de contexto vivo (estado pós-C16 em `wave5-v4-c16/audit`)

| # | Arquivo | Status |
|---|---|:---:|
| 1 | `CLAUDE.md` | ✅ Lido via system reminder; seção "Relatórios Gerenciais" pós-C12 + atualização tabela waves C16 |
| 2 | `DECISIONS.md` | ✅ ADR-162 lido linhas 7030-7092 (mapeamento literal das 11 decisões) |
| 3 | `CHANGELOG.md` | ✅ Seção C16 linhas 1-81 lida ("FECHA A WAVE 5 v4.0") |
| 4 | `docs/wave5-v4-c16/analysis.md` | ⚠️ Citado pela auditoria (1155 LOC). Lido via system reminder na auditoria + grep adicional |
| 5 | `docs/wave5-v4-c16/smoke-validation.md` | ✅ Lido integralmente (140 linhas, 20 cenários) |

### 1.3 Documentos de produto v4.0 (Seção 2.3 do prompt)

Já carregados via `CLAUDE.md` (system reminder) — não relidos diretamente nesta sessão, mas os conceitos canônicos são citados pontualmente: RF-013/014, RN-009/013, RNF-001/005/008, US-010 a 013, Componente 16 do Backlog, DAT §2/3/7.

### 1.4 Código-fonte tocado pelos achados

| # | Arquivo | Linhas críticas | Achados que afeta |
|---|---|---|---|
| 1 | `frontend/src/app/(dashboard)/relatorios/shared/DonutChart.tsx` | 320-392 (sr-only + details aria-hidden) | AUD-003 |
| 2 | `backend/app/api/v1/reports.py` | 110-230 (constantes); 1696-1701 (CSV summary) | AUD-004, AUD-009, AUD-011 |
| 3 | `backend/app/state_machine/v4/contextos.py` | 1-58 (canônico contexto_motorista) | AUD-004 (referência) |
| 4 | `frontend/src/hooks/useReportFilters.ts` | 1-196 (parseRota/parseStatus/parseRotaCategoria) | AUD-006 |
| 5 | `frontend/src/hooks/__tests__/useReportFilters.test.ts` | 1-189 (re-implementa parsers) | AUD-006 |
| 6 | `frontend/src/app/(dashboard)/relatorios/perspectivas/ReportGeral.tsx` | 332-358 (card ROTA, `.rotaDotPadrao/Direta`) | AUD-007 |
| 7 | `frontend/src/app/(dashboard)/relatorios/relatorios.module.css` | 1119-1125 (`.rotaDotPadrao/Direta`); arquivo todo (prefers-reduced-motion) | AUD-005, AUD-007, AUD-008 |
| 8 | `backend/tests/test_reports_v4.py` | 365-411 (TestContextoMotoristaParidade); 414-453 (TestCategoriaPredicate) | AUD-004 (teste novo); AUD-010 (teste novo) |

---

## 2. Resumo do veredito de auditoria

| Bloco | Quantidade |
|---|:---:|
| CRÍTICO | **0** |
| ALTO | **3** (AUD-001, AUD-002, AUD-003) |
| MÉDIO | **5** (AUD-004, AUD-005, AUD-006, AUD-007, AUD-008) |
| BAIXO | **5** (AUD-009, AUD-010, AUD-011, AUD-012, AUD-013) |
| INFO | **4** (AUD-014, AUD-015, AUD-016, AUD-017) |
| **TOTAL** | **17** |

**Distribuição por categoria do prompt:**
- Decisão de design ignorada: **0** (todas as 11 decisões registradas em ADR-162).
- Cenário obrigatório com bug visual: **0 bug** (cenários 3 e 4 NÃO entregues por decisão consciente ADR-162; cenários 8/9/10 com gap apenas no smoke-validation — AUD-002).
- Anti-enumeração quebrada: **1** (AUD-017 — INFO, trade-off documentado em ADR-162, sem ação).
- Modificação não-autorizada do `contrato-c12.md`: **0** (git diff vazio).
- Modificação não-autorizada do C15 (Dashboard v3): **0** (git diff vazio).
- Modificação não-autorizada de outras entregas: **0** (git diff vazio em todas).
- Tratamento errado de provas legacy v3.0: **0** (heurística D11.2 do C12 aplicada corretamente).
- Reuso quebrado do contrato: **0** (tipos/labels importados, sem hard-code).
- Reuso interno duplicado: **2** (AUD-004 backend, AUD-006 frontend testes).
- Violação de escopo: **0** (17 arquivos exclusivamente no escopo previsto).
- Acessibilidade: **2** (AUD-003 ALTO, AUD-005 MÉDIO).
- Performance: **0 violado** (não medido em staging — gap herdado).
- CSV: **1 assimetria menor** (AUD-011).
- Regressão SQL do Dashboard: **0** (zero linhas mudadas no escopo do C15).

**Conclusão:** veredito do auditor confirmado — **APROVADO COM CORREÇÕES MENORES**. Nenhum dos 3 ALTOS é bloqueante semântico; são polimento de a11y + documentação.

---

## 3. Validação MCP do banco (Supabase) — read-only

Projeto `rwxlpwmnkekzuurgthkr` (sa-east-1), ACTIVE_HEALTHY, Postgres 17.6.

| Item | Resultado | Idêntico ao baseline pós-C12? |
|---|---|:---:|
| `alembic_version` | `013` | ✅ |
| `rota_enum` | 6 valores: `PADRAO, DIRETA, MATRIZ, LAM_MATRIZ, FILIAL, LAM_FILIAL` | ✅ |
| `status_prova_enum` | 17 valores (10 v3 + 7 v4 na ordem alfabética de adição) | ✅ |
| Total de provas | 17 | ✅ |
| Distribuição rota | `PADRAO=2 · DIRETA=3 · MATRIZ=1 · NULL=11` | ✅ |
| Distribuição status | `CANCELADA=7 · CRIADA=6 · RECEBIDA=2 · REPROVADA=2` | ✅ |
| Usuários ativos | 4 (2 admins STUDIO + 2 vendedores FILIAL: `mariosouza@teste.com.br`, `andrebento@3studio.com.br`) | ⚠️ era 3, agora 4 (drift baixo — não bloqueia) |
| Heurística C12 D11.2 | **TODAS** as 11 provas NULL têm vendedor FILIAL | ✅ — todas vão para o balde Filial via correlated EXISTS |
| `pol_provas_select` | admin OR vendedor_owner OR motorista (4 estados) OR clicheria (7 estados, incluindo `COM_MOTORISTA_ENTREGA_FINAL`) | ✅ — RLS 015 aplicada (Wave 3 C11 R2) |
| Advisors security | 1 INFO `rls_enabled_no_policy` (alembic, intencional) + 1 WARN `auth_leaked_password_protection` (WONTFIX free tier) | ✅ |
| Advisors performance | 13 INFO `unused_index` (esperado em volume baixo, inclui `idx_provas_rota`) | ✅ |

**Conclusão:** estado real do banco em produção é idêntico ao baseline pós-C16 declarado pelo auditor. Zero divergência estrutural. Zero novo advisor.

### Provas representativas para os 10 cenários da auditoria

| Cenário | Prova / Filtro |
|---|---|
| 1 (Página geral) | Qualquer query 3Studio sem filtro |
| 2 (Distribuição rota) | 11 NULL (heurística) + 1 MATRIZ + 2 PADRAO + 3 DIRETA |
| 3 (Tempo Médio por Etapa) | **NÃO entregue como UI** — ADR-162 |
| 4 (Taxa Reprovação segmentada) | **NÃO entregue como UI** — ADR-162 |
| 5 (Filtros) | `?rota_categoria=matriz&status=CRIADA` deve retornar 1+ |
| 6 (Exportação CSV) | Qualquer dataset |
| 7 (Tabela alt a11y) | DonutChart "Provas Ativas" (CRIADA=6 → 1 segmento ativo) |
| 8 (Estado vazio) | `?vendedor_id=<uuid-fictício>` retorna 0 → EmptyState |
| 9 (Estado de erro) | Network throttle / backend down via DevTools |
| 10 (Acesso negado) | Logar como `mariosouza@teste.com.br` (vendedor FILIAL) |

---

## 4. Verificação de não-modificação (intocados)

`git diff origin/development..HEAD` confirma **VAZIO** em:

| Path | Veredito |
|---|:---:|
| `docs/wave3-v4-c11/contrato-c12.md` | ✅ INTOCADO |
| `frontend/src/app/(dashboard)/dashboard/` | ✅ INTOCADO (Dashboard C15 v3) |
| `backend/app/api/v1/provas.py` | ✅ INTOCADO |
| `backend/app/domain/schemas/dashboard.py` | ✅ INTOCADO |
| `frontend/src/hooks/useDashboard.ts` | ✅ INTOCADO |
| `backend/app/state_machine/`, `backend/app/services/state_machine.py` | ✅ INTOCADOS (máquina C11) |
| `backend/app/api/v1/{users,audit_log,configuracoes}.py` | ✅ INTOCADOS |
| `backend/app/access/`, `shared/`, `backend/migrations/` | ✅ INTOCADOS (RBAC Wave 1, migrations) |
| `frontend/src/middleware.ts` | ✅ INTOCADO |
| `frontend/src/lib/services/identificacao-prova.ts`, `frontend/src/lib/codigo-publico.ts`, `frontend/src/lib/c19-mensagens.ts` | ✅ INTOCADOS (C10 + C19) |
| `frontend/src/app/(dashboard)/{auditoria,escanear,provas,nova-prova,usuarios,configuracoes}/` | ✅ INTOCADOS |

**Conclusão:** zero modificação indevida de entregas anteriores. Confirma o item §1.7/1.8/1.9 do audit-report.

### Smoke programático de anti-enumeração (curl, sem token)

| Endpoint (sem auth) | HTTP | Body | Tempo médio (10 amostras) |
|---|:---:|---|---:|
| `GET /api/v1/reports?scope=geral` | 404 | `{"status":"error","code":404,"message":"Application not found"}` | ~430ms |
| `GET /api/v1/inexistente` | 404 | mesmo body | ~440ms |
| `GET /api/v1/reports/export?scope=geral` | 404 | mesmo body | ~430ms |

**Observação:** o domínio `provadigital-production.up.railway.app` está retornando 404 da **plataforma Railway** ("Application not found"), não do backend FastAPI — o serviço pode estar dormente. Sem token de vendedor live, comparação "vendedor → /reports vs vendedor → /inexistente" é **impossível**. O auditor já registrou este gap em §3.4 do audit-report ("NÃO realizada — ambiente local sem token de autenticação live"). Decisão D11→i (ADR-162) preserva 403 para perfis não-3Studio por coerência com Matriz Wave 1 v4.0 — Mario aprovou explicitamente em ADR-162 §"Mapeamento das 11 decisões" linha D11. Sessão de re-auditoria com token live pode validar byte-a-byte se Mario quiser.

### Comparação SQL pré-C16 vs pós-C16 do Dashboard (C15 v3)

```
$ git diff origin/development..HEAD -- 'frontend/src/app/(dashboard)/dashboard/' \
                                       'backend/app/api/v1/provas.py' \
                                       'backend/app/domain/schemas/dashboard.py' \
                                       'frontend/src/hooks/useDashboard.ts' | wc -l
0
```

**Conclusão:** zero linhas mudadas no escopo do C15 (Dashboard v3). Código que gera as queries SQL do Dashboard é byte-idêntico pré-C16 e pós-C16. Portanto, as queries são byte-idênticas, e os números retornados são byte-idênticos. **CONFORME.** Mario pode abrir `/dashboard` no smoke para confirmação visual final.

---

## 5. Inventário consolidado dos 17 achados

Convenções da tabela:
- **DD ignorada?** = decisão de design ignorada? (sim/não)
- **Cenário?** = é cenário obrigatório com bug visual? (sim/qual número/não)
- **Anti-enum?** = é anti-enumeração? (sim/qual dimensão: status/headers/body/timing/logs/cache/não)
- **Mod. contrato?** = modificação não-autorizada do `contrato-c12.md`?
- **Mod. C15?** = modificação não-autorizada do C15 Dashboard?
- **Mod. outras?** = modificação não-autorizada de outras entregas?
- **Legacy?** = tratamento errado de provas legacy?
- **Reuso?** = reuso quebrado/duplicação?
- **Esc. viol.?** = violação de escopo?
- **A11y?** = problema de acessibilidade?
- **Perf?** = problema de performance?
- **CSV?** = problema de CSV?
- **Reg. SQL Dash?** = regressão SQL do Dashboard?

| ID | Sev. | Categoria | Descrição (resumo) | Arquivo / Linha | Status | DD ignorada? | Cenário? | Anti-enum? | Mod. contrato? | Mod. C15? | Mod. outras? | Legacy? | Reuso? | Esc. viol.? | A11y? | Perf? | CSV? | Reg. SQL Dash? |
|---|:---:|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| AUD-W5C16-001 | ALTO | Documentação | `visual-guide.md` ausente em `docs/wave5-v4-c16/` | `docs/wave5-v4-c16/` | pendente | não | não | não | não | não | não | não | não | não | não | não | não | não |
| AUD-W5C16-002 | ALTO | Documentação | `smoke-validation.md` sem cenários 8 (vazio), 9 (erro), 10 (acesso negado) | `docs/wave5-v4-c16/smoke-validation.md` | pendente | não | sim — 8, 9, 10 (gap de smoke, não de implementação) | não | não | não | não | não | não | não | não | não | não | não |
| AUD-W5C16-003 | ALTO | Acessibilidade | `<details aria-hidden="true">` viola WAI-ARIA `aria-hidden-focus` | `DonutChart.tsx:369` | pendente | não | não | não | não | não | não | não | não | não | **sim** | não | não | não |
| AUD-W5C16-004 | MÉDIO | Reuso / Manutenibilidade | `_CONTEXTO_MOTORISTA_STATUSES` redefine `contexto_motorista()` Python sem teste cross-validation | `reports.py:202-209` + `test_reports_v4.py:365-411` | pendente | não | não | não | não | não | não | não | **sim — duplicação backend** | não | não | não | não | não |
| AUD-W5C16-005 | MÉDIO | Acessibilidade | `prefers-reduced-motion` ausente em toda a pasta `relatorios` | `relatorios.module.css` (arquivo todo) + componentes com `motion.*` | pendente | não | não | não | não | não | não | não | não | não | **sim** | não | não | não |
| AUD-W5C16-006 | MÉDIO | Reuso / Manutenibilidade | Testes Vitest re-implementam parsers em vez de importar do hook | `useReportFilters.test.ts:30-49` + `useReportFilters.ts:32-67` | pendente | não | não | não | não | não | não | não | **sim — duplicação frontend testes** | não | não | não | não | não |
| AUD-W5C16-007 | MÉDIO | CSS / Manutenibilidade | Classes CSS `.rotaDotPadrao/Direta` mantém nomes legacy v3 mas labels exibidos são v4 (Matriz/Filial) | `ReportGeral.tsx:343,351` + `relatorios.module.css:1119-1125` | pendente | não | não | não | não | não | não | não | sim — semântica visual confusa | não | não | não | não | não |
| AUD-W5C16-008 | MÉDIO | CSS / Documentação | CSS sem comentário documentando mapeamento v3→v4 das classes | `relatorios.module.css:1119-1125` | pendente | não | não | não | não | não | não | não | não | não | não | não | não | não |
| AUD-W5C16-009 | BAIXO | Backend / Documentação | `_CLICHERIA_EM_TRANSITO` sem `COM_MOTORISTA_IDA/VOLTA_LAMINACAO` (correto, mas vale documentar) | `reports.py:127-134` | pendente (aceitar) | não | não | não | não | não | não | não | não | não | não | não | não | não |
| AUD-W5C16-010 | BAIXO | Testes backend | `legacy_null_indefinida` no schema sem teste explícito | `test_reports_v4.py` (a adicionar) + `schemas/report.py:96-99` | pendente | não | não | não | não | não | não | parcialmente — falta cenário edge `vendedor.localizacao IS NULL` | não | não | não | não | não | não |
| AUD-W5C16-011 | BAIXO | CSV | `consolidacao_rota_indefinida` assimétrico (só emitido se > 0) | `reports.py:1696-1701` | pendente | não | não | não | não | não | não | não | não | não | não | não | **sim** | não |
| AUD-W5C16-012 | BAIXO | Revisão (INFO) | `to_cache_key` inclui `scope` corretamente | `report_filters.py:194` | sem ação | não | não | não | não | não | não | não | não | não | não | não | não | não |
| AUD-W5C16-013 | BAIXO | Revisão (INFO) | `_defaults_and_invariants` usa `object.__setattr__` (padrão Pydantic v2) | `report_filters.py:117-159` | sem ação | não | não | não | não | não | não | não | não | não | não | não | não | não |
| AUD-W5C16-014 | INFO | Cobertura | Vitest cobertura: 42 testes via `it.each` (CHANGELOG correto) | `useReportFilters.test.ts` | sem ação | não | não | não | não | não | não | não | não | não | não | não | não | não |
| AUD-W5C16-015 | INFO | Cobertura | Backend pytest: 1027 + 10 skipped (CHANGELOG correto) | `test_reports_v4.py` | sem ação | não | não | não | não | não | não | não | não | não | não | não | não | não |
| AUD-W5C16-016 | INFO | Cobertura | RBAC herdado de `test_reports_api.py` cobre 5 cenários 403 | `test_reports_api.py:157, 170, 179, 188, 671` | sem ação | não | não | não | não | não | não | não | não | não | não | não | não | não |
| AUD-W5C16-017 | INFO | Anti-enumeração | RBAC retorna 403 (não 404 byte-a-byte) — Decisão D11→i ADR-162 | `reports.py:1413, 1501` (access_required) | sem ação | não | não | sim — status code (decisão consciente Mario) | não | não | não | não | não | não | não | não | não | não |

**Resumo do inventário:**
- **12 achados corrigíveis** (3 ALTOS + 5 MÉDIOS + 4 BAIXOS, dos quais AUD-009/012/013 são ACEITOS sem código tocado).
- **5 achados sem ação direta** (AUD-009 ACEITO + AUD-012/013 ACEITOS + AUD-014/015/016 INFO de cobertura + AUD-017 INFO anti-enumeração — total 7 sem código, mas AUD-009 pode receber expansão de comentário opcional → contam efetivamente como **9 com mudança de código** + **3 INFO puros sem ação** + **5 ACEITOS/documentados**).
- **0 BLOQUEADOS POR DIVERGÊNCIA**.
- **0 DEFERRED por violação de escopo**.
- **0 que requerem nova escalação humana**.

---

## 6. Plano de correção por achado

### AUD-W5C16-001 — Criar `visual-guide.md` mínimo (ALTO)

- **Estratégia:** criar `docs/wave5-v4-c16/visual-guide.md` stub estruturado seguindo padrão da Wave 3 C12 (AUD-W3C12-003). 4 seções principais:
  1. Card ROTA pós-C16 (descrição visual: 2 dots — Matriz preto, Filial amarelo).
  2. RotaFilter (3 botões Todas/Matriz/Filial visualmente idênticos).
  3. 4 perspectivas preservadas (Geral/3Studio/Vendedores/Clicheria).
  4. CSV summary snippet com as novas linhas `rota_v4_*`/`consolidacao_rota_*`/`contexto_motorista_*`.
- **Tipo:** documento novo. Sem touch em código.
- **Confirmações:** ✅ não modifica `contrato-c12.md`. ✅ não modifica C15. ✅ não modifica outras entregas. ✅ sem Framer/lib novo.
- **Arquivos tocados:** `docs/wave5-v4-c16/visual-guide.md` (novo).
- **Camada:** documentação.
- **Risco regressão:** BAIXO.
- **Validação:** revisão visual pelo auditor da próxima rodada + Mario tira screenshots no smoke E2E e preenche.
- **Decisão de design afetada:** nenhuma (documento descritivo).
- **Dependências:** nenhuma. Pode ser feito a qualquer momento.

### AUD-W5C16-002 — Expandir `smoke-validation.md` com 3 cenários de borda (ALTO)

- **Estratégia:** editar `docs/wave5-v4-c16/smoke-validation.md` adicionando 3 cenários no fim (antes da seção "Critério de aprovação"):
  - **#21. [ESTADO VAZIO]** — `?vendedor_id=<uuid-fictício>` → `EmptyState` renderiza sem crash; soma de contadores zero.
  - **#22. [ESTADO DE ERRO]** — DevTools network throttle Offline + reload → banner/retry visível; sem crash.
  - **#23. [ACESSO NEGADO]** — logar como `mariosouza@teste.com.br` (vendedor FILIAL) → redirect para `Restricted` Wave 1; backend retorna 403; middleware filtra antes do backend.
- Atualizar contagem total (linha 5: "20 cenários" → "23 cenários") e item de SKIP no fim (cenários que requerem ação humana).
- **Tipo:** documento expandido. Sem touch em código.
- **Confirmações:** ✅ não modifica contrato/C15/outras entregas. ✅ sem lib nova.
- **Arquivos tocados:** `docs/wave5-v4-c16/smoke-validation.md`.
- **Camada:** documentação.
- **Risco regressão:** BAIXO.
- **Validação:** lint do markdown; auditor da próxima rodada confirma cobertura.
- **Cenário obrigatório afetado:** cenários 8, 9, 10 da auditoria — **gap de smoke**, não de implementação (estado vazio já existe via `EmptyState` da Wave 5 v3; erro tem tratamento existente; acesso negado funciona via Matriz Wave 1).

### AUD-W5C16-003 — Corrigir `aria-hidden-focus` no DonutChart (ALTO · a11y)

- **Estratégia:** mover o atributo `aria-hidden="true"` do `<details>` (que contém `<summary>` focável — viola WAI-ARIA) para o `<table>` interno. O `<summary>` continua focável e anuncia o toggle ao leitor de tela quando o usuário cego decidir interagir; a `<table>` interna fica `aria-hidden` para evitar duplicação com a tabela sr-only acima.
  - **Antes:**
    ```jsx
    <details className={styles.chartDetails} aria-hidden="true">
      <summary>Ver dados em formato tabular</summary>
      <table className={styles.chartTable}>...</table>
    </details>
    ```
  - **Depois:**
    ```jsx
    <details className={styles.chartDetails}>
      <summary>Ver dados em formato tabular</summary>
      <table className={styles.chartTable} aria-hidden="true">...</table>
    </details>
    ```
  - **Alternativa rejeitada:** `inert` no `<details>` — desabilitaria o foco no `<summary>`, quebrando o toggle para usuário vidente teclado-only. NÃO usar.
- **Tipo:** correção cirúrgica de 1 atributo (move-se de uma linha para outra).
- **Confirmações:** ✅ não modifica contrato/C15/outras entregas. ✅ sem lib nova.
- **Arquivos tocados:** `frontend/src/app/(dashboard)/relatorios/shared/DonutChart.tsx` (1 hunk).
- **Camada:** frontend a11y.
- **Risco regressão:** BAIXO.
- **Validação:**
  - `npx vitest run` (cobre testes existentes — anti-regressão).
  - `npx tsc --noEmit` (zero erros).
  - `npx next build` (13/13 páginas).
  - Inspeção DOM via DevTools (manual no smoke): `<details>` sem `aria-hidden`, `<table>` com `aria-hidden=true`.
  - axe-core no smoke do Mario: zero violação `aria-hidden-focus`.
- **Dimensão a11y:** WAI-ARIA 1.1 — `aria-hidden=true` proibido em containers com elementos focáveis (4.3.2 do spec).
- **Dependências:** nenhuma.

### AUD-W5C16-004 — `_CONTEXTO_MOTORISTA_STATUSES` derivar da fonte canônica (MÉDIO · backend reuso)

- **Estratégia:**
  1. Em `backend/app/api/v1/reports.py` linhas 202-209, substituir o dict literal por um **dict comprehension** que itera sobre `StatusProvaEnum` chamando o canônico `app.state_machine.v4.contextos.contexto_motorista`:
     ```python
     from app.state_machine.v4.contextos import contexto_motorista as _contexto_motorista_canonical

     _CONTEXTO_MOTORISTA_STATUSES: dict[StatusProvaEnum, "ContextoMotorista"] = {
         s: _contexto_motorista_canonical(s)
         for s in StatusProvaEnum
         if _contexto_motorista_canonical(s) is not None
     }
     ```
     Comentário acima documenta paridade automática.
  2. Em `backend/tests/test_reports_v4.py` adicionar 1 teste cross-validation:
     ```python
     def test_cross_validation_with_canonical_contexto_motorista(self):
         from app.state_machine.v4.contextos import contexto_motorista
         from app.api.v1.reports import _CONTEXTO_MOTORISTA_STATUSES
         for s in StatusProvaEnum:
             expected = contexto_motorista(s)
             if expected is None:
                 assert s not in _CONTEXTO_MOTORISTA_STATUSES, f"{s} foi mapeado mas canonical retorna None"
             else:
                 assert _CONTEXTO_MOTORISTA_STATUSES[s] == expected, f"Drift em {s}: dict={_CONTEXTO_MOTORISTA_STATUSES[s]}, canonical={expected}"
     ```
- **Tipo:** refactor com adição de teste.
- **Confirmações:** ✅ não modifica contrato/C15/outras entregas. ✅ sem lib nova. ✅ não toca a função canônica `contexto_motorista` (intocada — pertence ao C11).
- **Arquivos tocados:**
  - `backend/app/api/v1/reports.py` (~8 LOC editadas).
  - `backend/tests/test_reports_v4.py` (~15 LOC adicionadas — novo teste).
- **Camada:** backend.
- **Risco regressão:** BAIXO. A função canônica já trata todos os 17 status (4 mapeados + 13 None). Comprehension preserva exatamente 4 chaves.
- **Validação:**
  - `pytest backend/tests/test_reports_v4.py -v` — todos os testes da classe `TestContextoMotoristaParidade` continuam passando, mais 1 novo.
  - `pytest backend/tests/` — anti-regressão geral (1027 + 1 = 1028 tests passed).
- **Dependências:** nenhuma.

### AUD-W5C16-005 — `prefers-reduced-motion` em `relatorios.module.css` (MÉDIO · a11y)

- **Estratégia:** adicionar bloco `@media (prefers-reduced-motion: reduce)` no FINAL do arquivo `relatorios.module.css` (após a última regra), aplicando degradação a `animation-duration` e `transition-duration` para os elementos animados da pasta `relatorios/`.
  ```css
  /* Wave 5 v4.0 / C16 fix AUD-005 — RNF-008 + RN-012 v4.0:
     respeita preferência do usuário com motion-sickness. */
  @media (prefers-reduced-motion: reduce) {
    .metricCard,
    .chartsRowGeral > *,
    .barRow,
    .donutSegment,
    .donutContainer * {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
      scroll-behavior: auto !important;
    }
  }
  ```
- **Alternativa considerada (não adotada nesta sessão):** usar `useReducedMotion()` do `framer-motion` nos componentes `ReportGeral.tsx`/`Report3Studio.tsx`/`ReportClicheria.tsx`/`ReportVendedores.tsx` + nos shared `BarChart.tsx`/`DonutChart.tsx`/`KpiCard.tsx`/`TimeSeriesChart.tsx` (8 arquivos) para zerar props `transition.duration`/`initial`/`animate`. Mais robusto, porém invasivo. Trade-off: regra CSS global é defensiva suficiente para AA — Framer Motion respeita `prefers-reduced-motion` por default ao animar `transform` (que é o que ele faz aqui), mas a regra CSS reforça e cobre eventuais transições CSS puras (sparkline, badges, hover). Follow-up registrado em DECISIONS se Mario quiser ir além.
- **Tipo:** adição de regra CSS defensiva.
- **Confirmações:** ✅ não modifica contrato/C15/outras entregas. ✅ sem lib nova. ✅ não toca `framer-motion` imports.
- **Arquivos tocados:** `frontend/src/app/(dashboard)/relatorios/relatorios.module.css` (~12 LOC adicionadas no fim).
- **Camada:** frontend a11y CSS.
- **Risco regressão:** BAIXO. Bloco condicional ao `prefers-reduced-motion: reduce` — sem efeito em usuários comuns.
- **Validação:**
  - DevTools → Rendering → Emulate CSS media feature `prefers-reduced-motion: reduce` → confirmar que animações zeram.
  - axe-core sem novas violações.
  - `npx tsc --noEmit` + `npx next build` (CSS Module isolado, sem efeito em build).
- **Dependências:** nenhuma.

### AUD-W5C16-006 — Extrair parsers de `useReportFilters` para módulo dedicado (MÉDIO · reuso testes)

- **Estratégia:** seguir padrão validado pelo C12 (AUD-W3C12-003: extração `formatRota`/`isPathActive` para `lib/`).
  1. Criar `frontend/src/hooks/_useReportFilters.parsers.ts` (prefixo `_` indica "interno do hook" — convenção do projeto):
     ```typescript
     import type { ReportScope, RotaCategoria } from "@/lib/types/report";
     import { REPORT_SCOPES } from "@/lib/types/report";
     import { ROTA_OPTIONS, STATUS_OPTIONS, type Rota, type StatusProva } from "@/lib/types/prova";

     const SCOPE_SET = new Set(REPORT_SCOPES);

     export function parseScope(value: string | null): ReportScope { ... }
     export function parseRota(value: string | null): Rota | null { ... }
     export function parseStatus(value: string | null): StatusProva | null { ... }
     export function parseRotaCategoria(value: string | null): RotaCategoria | null { ... }
     export function nullableString(value: string | null): string | null { ... }
     ```
     5 funções puras, **sem** `next/navigation`, testáveis em `environment: node`.
  2. Em `frontend/src/hooks/useReportFilters.ts`, **remover** as 5 funções locais e importar do módulo novo. Manter assinatura pública `useReportFilters()` inalterada.
  3. Em `frontend/src/hooks/__tests__/useReportFilters.test.ts`, **remover** as re-implementações (linhas 30-49) e **importar** diretamente do módulo `_useReportFilters.parsers`. Os testes existentes continuam exercendo as funções **reais**.
- **Tipo:** refactor de imports (extração); preserva comportamento.
- **Confirmações:** ✅ não modifica contrato/C15/outras entregas. ✅ sem lib nova. ✅ não muda assinatura pública do hook.
- **Arquivos tocados:**
  - `frontend/src/hooks/_useReportFilters.parsers.ts` (novo, ~80 LOC).
  - `frontend/src/hooks/useReportFilters.ts` (remove ~36 LOC, adiciona 1 import).
  - `frontend/src/hooks/__tests__/useReportFilters.test.ts` (remove ~20 LOC, adiciona 1 import).
- **Camada:** frontend testes + hook.
- **Risco regressão:** MÉDIO-BAIXO. Conflito de nome de módulo `_useReportFilters.parsers` improvável (prefixo `_`). Comportamento idêntico.
- **Validação:**
  - `npx vitest run` — todos os 205 testes passam (42 do C16 continuam, agora exercendo módulo real).
  - `npx tsc --noEmit` — zero erros.
  - `npx next build` — 13/13 páginas.
  - **Verificação anti-regressão de identidade comportamental:** rodar o teste `aceita todos os valores de ROTA_OPTIONS (paridade)` e `aceita todos os 17 valores de STATUS_OPTIONS (paridade)` — passam com módulo extraído.
- **Dependências:** nenhuma.

### AUD-W5C16-007 + AUD-W5C16-008 — Renomear `.rotaDotPadrao/Direta` → `.rotaDotMatriz/Filial` + comentário (MÉDIO · CSS)

- **Estratégia combinada (AUD-007 + AUD-008 são complementares):**
  1. Em `relatorios.module.css`:
     - Renomear `.rotaDotPadrao` → `.rotaDotMatriz` (preto `#000000`).
     - Renomear `.rotaDotDireta` → `.rotaDotFilial` (amarelo `var(--color-accent, #ffcb5c)`).
     - Adicionar bloco de comentário acima das 2 regras explicando:
       ```css
       /* Wave 5 v4.0 / C16 fix AUD-007+008 — paleta da legenda do card ROTA.
        *
        * Anteriormente as classes eram `.rotaDotPadrao` (preto) e
        * `.rotaDotDireta` (amarelo), com labels v3 "Padrao"/"Direta". A
        * Wave 5 v4.0 / C16 troca os labels para v4 "Matriz"/"Filial"
        * mantendo as cores (ADR-158 do C12: PADRAO->Matriz, DIRETA->Filial).
        *
        * Esta renomeação eh puramente cosmetica (CSS Module + 1 consumidor
        * ReportGeral.tsx) e elimina o mismatch v3-CSS / v4-UI que confundia
        * leitores futuros. Funcionalmente identico. */
       ```
  2. Em `ReportGeral.tsx:343,351`:
     - Atualizar `styles.rotaDotPadrao` → `styles.rotaDotMatriz`.
     - Atualizar `styles.rotaDotDireta` → `styles.rotaDotFilial`.
  3. **Validar com grep que não há outros consumidores:**
     ```
     $ grep -r "rotaDotPadrao\|rotaDotDireta" frontend/
     (vazio após renomeação)
     ```
- **Alternativa rejeitada:** apenas adicionar comentário sem renomear (sugerido como "minimum viable" pelo auditor). Rejeitada porque o débito técnico fica para sempre — renomeação é trivial (4 ocorrências em 2 arquivos sob CSS Module local) e elimina permanentemente.
- **Tipo:** refactor cosmético (CSS + 1 consumidor TSX).
- **Confirmações:** ✅ não modifica contrato/C15/outras entregas. ✅ não muda comportamento visual (cores idênticas). ✅ sem lib nova.
- **Arquivos tocados:**
  - `frontend/src/app/(dashboard)/relatorios/relatorios.module.css` (rename + comentário, ~15 LOC).
  - `frontend/src/app/(dashboard)/relatorios/perspectivas/ReportGeral.tsx` (2 substituições).
- **Camada:** CSS + frontend.
- **Risco regressão:** BAIXO. CSS Module escopo local + 1 único consumidor confirmado via grep.
- **Validação:**
  - Grep pós-rename retorna 0 ocorrências de `rotaDotPadrao`/`rotaDotDireta`.
  - `npx tsc --noEmit` + `npx next build` — zero erros.
  - Inspecionar visualmente `/relatorios?scope=geral` (no smoke do Mario): card ROTA com dot preto "Matriz" + dot amarelo "Filial" preservados pixel-perfect.
- **Dependências:** AUD-007 e AUD-008 são combinados em 1 commit (renomeação + comentário juntos).

### AUD-W5C16-009 — Documentar `_CLICHERIA_EM_TRANSITO` (BAIXO · ACEITAR)

- **Estratégia:** o auditor mesmo diz "semanticamente correto, mas vale documentar para Dashboard futuro". A docstring atual já cobre. **Decisão:** **ACEITAR** sem ação de código. Optional polish: expandir docstring para enfatizar Wave 4 Dashboard futuro.
- **Tipo:** ACEITO (sem touch) OU comentário opcional (+3 linhas).
- **Confirmações:** N/A (sem mudança real).
- **Arquivos tocados:** `backend/app/api/v1/reports.py` (3 LOC opcionais, ou 0).
- **Camada:** backend / documentação interna.
- **Risco regressão:** ZERO.
- **Validação:** N/A.
- **Decisão proposta:** **ACEITAR sem polish** (alinhada com auditor). Se Mario quiser polish, +3 LOC de comentário no Gate 2.

### AUD-W5C16-010 — Teste de borda `legacy_null_indefinida` (BAIXO · teste)

- **Estratégia:** adicionar teste em `test_reports_v4.py` (classe nova `TestLegacyNullIndefinida`) simulando provas com `vendedor.localizacao IS NULL`:
  ```python
  class TestLegacyNullIndefinida:
      """Cobre cenário edge: provas legacy (rota=NULL) cujo vendedor
      NÃO tem localizacao preenchida — caem no balde 'indefinida'.

      Em produção atual (admin@3studio, ops@3studio têm localizacao=NULL
      mas são is_admin=true) este cenário pode ocorrer se admin for
      vendedor de prova legacy criada antes da Wave 1 v4.0."""

      async def test_payload_inclui_legacy_null_indefinida(self):
          # Fixture: criar prova com rota=NULL e vendedor.localizacao=NULL.
          # Validar que aggregate retorna legacy_null_indefinida=1.
          ...
  ```
- **Tipo:** adição de teste (cobertura).
- **Confirmações:** ✅ não modifica contrato/C15/outras entregas. ✅ usa fixtures existentes do test_reports_v4.py.
- **Arquivos tocados:** `backend/tests/test_reports_v4.py` (~25 LOC adicionadas — 1 classe + 1 teste).
- **Camada:** backend testes.
- **Risco regressão:** ZERO (apenas adição).
- **Validação:**
  - `pytest backend/tests/test_reports_v4.py::TestLegacyNullIndefinida -v` — passa.
  - `pytest backend/tests/` — anti-regressão (≥ 1028 testes passando após AUD-004 + AUD-010 = 1029).
- **Dependências:** ordem após AUD-004 (que também adiciona teste em test_reports_v4.py — evitar conflito de merge).

### AUD-W5C16-011 — CSV emitir `consolidacao_rota_indefinida` sempre (BAIXO · CSV)

- **Estratégia:** em `reports.py:1696-1701`, remover o guard `if cons.indefinida > 0` e emitir sempre:
  - **Antes:**
    ```python
    rows.append([scope, "consolidacao_rota_matriz", str(cons.matriz)])
    rows.append([scope, "consolidacao_rota_filial", str(cons.filial)])
    if cons.indefinida > 0:
        rows.append([scope, "consolidacao_rota_indefinida", str(cons.indefinida)])
    ```
  - **Depois:**
    ```python
    rows.append([scope, "consolidacao_rota_matriz", str(cons.matriz)])
    rows.append([scope, "consolidacao_rota_filial", str(cons.filial)])
    rows.append([scope, "consolidacao_rota_indefinida", str(cons.indefinida)])
    ```
  - Adicionar teste em `test_reports_v4.py` que valida 3 linhas SEMPRE no CSV summary (mesmo quando `indefinida=0`).
- **Tipo:** correção de assimetria.
- **Confirmações:** ✅ não modifica contrato/C15/outras entregas. ✅ aditivo no parsing downstream (parsers que ignoram zero continuam funcionando).
- **Arquivos tocados:**
  - `backend/app/api/v1/reports.py` (3 LOC alteradas).
  - `backend/tests/test_reports_v4.py` (~10 LOC — teste novo).
- **Camada:** backend CSV.
- **Risco regressão:** MUITO BAIXO. Não quebra parsers que filtram zeros; harmoniza com `matriz`/`filial`.
- **Validação:**
  - Inspecionar manualmente uma resposta `/api/v1/reports/export?scope=geral&dataset=summary` no smoke do Mario — confirmar 3 linhas `consolidacao_rota_*` sempre.
  - Teste novo passa.
- **Dependências:** nenhuma.

### AUD-W5C16-012/013 — INFO de revisão (sem ação)

- **AUD-012** (`to_cache_key` inclui `scope` corretamente) — sem ação.
- **AUD-013** (`_defaults_and_invariants` usa `object.__setattr__` Pydantic v2) — sem ação.
- **Registro:** sem mudança de código. ACEITOS no apêndice do `audit-report.md`.

### AUD-W5C16-014/015/016 — INFO de cobertura (sem ação)

- **AUD-014** (Vitest 42 testes via `it.each`) — confirmação CHANGELOG. Sem ação.
- **AUD-015** (Backend pytest 1027 + 10 skipped) — confirmação CHANGELOG. Sem ação. Após Gate 2 vai a 1029+ com AUD-004/010/011.
- **AUD-016** (RBAC herdado de `test_reports_api.py` cobre 5 cenários 403) — confirmação. Sem ação.
- **Registro:** ACEITOS no apêndice do `audit-report.md`.

### AUD-W5C16-017 — Anti-enumeração 403 (não 404 byte-a-byte) (INFO — ACEITAR)

- **Estratégia:** sem ação. Decisão consciente D11→i registrada em ADR-162 com 5 justificativas. Defesa em profundidade preservada (middleware Next.js + 403 backend + RLS 0 rows).
- **Confirmações:** ✅ não modifica contrato/C15/outras entregas. ✅ não muda comportamento.
- **Arquivos tocados:** nenhum.
- **Camada:** N/A.
- **Risco regressão:** ZERO.
- **Validação:** apêndice do `audit-report.md` documenta ACEITO.
- **Registro extra no `DECISIONS.md`:** adicionar 1 entrada de apêndice ao ADR-162 reafirmando a decisão como pós-auditoria validada (manter coerência com Matriz Wave 1 v4.0).
- **Follow-up para Wave 6+:** se Mario quiser migrar a Matriz inteira para 404 byte-a-byte, sessão dedicada (afeta 11 chaves de RBAC, não apenas `relatorios`). NÃO escopo desta sessão.

---

## 7. Ordem de execução topológica

Regra: severidade primeiro; dentro da severidade, prioridade (a) reuso quebrado (cascata para outros) → (b) a11y crítico → (c) refactor que afeta testes → (d) CSS/cosmético → (e) documentação. Achados em arquivo comum agrupados para evitar conflito.

| # | ID | Sev. | Tipo | Arquivo principal |
|---:|---|:---:|---|---|
| 1 | **AUD-W5C16-003** | ALTO | a11y cirúrgico | `DonutChart.tsx` (frontend) |
| 2 | **AUD-W5C16-004** | MÉDIO | reuso backend + teste | `reports.py` + `test_reports_v4.py` |
| 3 | **AUD-W5C16-006** | MÉDIO | reuso frontend testes | `useReportFilters.ts` + parsers.ts (novo) + test |
| 4 | **AUD-W5C16-007 + AUD-W5C16-008** | MÉDIO | CSS rename + comentário | `relatorios.module.css` + `ReportGeral.tsx` |
| 5 | **AUD-W5C16-005** | MÉDIO | a11y CSS | `relatorios.module.css` |
| 6 | **AUD-W5C16-010** | BAIXO | teste backend | `test_reports_v4.py` |
| 7 | **AUD-W5C16-011** | BAIXO | CSV backend + teste | `reports.py` + `test_reports_v4.py` |
| 8 | **AUD-W5C16-009** | BAIXO | aceitar (sem código) ou polish docstring | `reports.py` (opcional) |
| 9 | **AUD-W5C16-001** | ALTO | doc nova | `docs/wave5-v4-c16/visual-guide.md` (novo) |
| 10 | **AUD-W5C16-002** | ALTO | doc expandida | `docs/wave5-v4-c16/smoke-validation.md` |
| 11 | **AUD-W5C16-012/013/014/015/016/017** | INFO/BAIXO | apêndice no audit-report + DECISIONS | `audit-report.md` + `DECISIONS.md` |

**Notas sobre a ordem:**
- **(1)** AUD-003 primeiro porque é a11y crítico em arquivo isolado (DonutChart.tsx) — zero conflito com demais.
- **(2)/(3)** Refactors de reuso antes que outras correções toquem os mesmos arquivos para minimizar conflito.
- **(4)/(5)** Ambos tocam `relatorios.module.css` mas em seções diferentes (linhas 1119-1125 vs final do arquivo) — commits sequenciais sem conflito.
- **(6)/(7)** Tocam `test_reports_v4.py` após AUD-004 (sequencial, evita conflito).
- **(9)/(10)** Documentação ao FINAL para refletir o estado pós-correções (rename de classes CSS, comportamento ajustado etc.).
- **(11)** Apêndice administrativo, último.

**Achados DEFERRED (violação de escopo):** NENHUM.
**Achados BLOQUEADOS por divergência:** NENHUM.

---

## 8. Análise de risco agregado

### Risco ALTO de regressão
**Nenhum.** Todos os 12 corrigíveis são cirúrgicos com testes anti-regressão imediatos.

### Risco MÉDIO de regressão
- **AUD-006** (extração de parsers): muda import path em `useReportFilters.ts` (consumido por `relatorios/page.tsx` e `FiltersBar.tsx` indiretamente via hook). **Mitigação:** assinatura pública `useReportFilters()` inalterada — só muda implementação interna. `tsc --noEmit` + Vitest pegam qualquer regressão.

### Risco BAIXO de regressão
- **AUD-003** (mover `aria-hidden`): testes Vitest + tsc + next build cobrem build; smoke do Mario valida visual.
- **AUD-004** (refactor `_CONTEXTO_MOTORISTA_STATUSES`): teste cross-validation já valida paridade automática.
- **AUD-007+008** (rename CSS): 4 ocorrências em 2 arquivos sob CSS Module local — grep pós-rename confirma zero resíduo.
- **AUD-005** (CSS media query): bloco condicional, sem efeito em usuários comuns.
- **AUD-010** (teste novo): aditivo.
- **AUD-011** (CSV indefinida sempre): apenas remove guard; harmoniza com `matriz`/`filial`.

### Achados de decisão de design ignorada
**Nenhum.** ADR-162 documenta todas as 11 decisões com adaptação Gate 2. Nenhuma divergência.

### Achados de cenário obrigatório com bug visual
**Nenhum bug de implementação.** Cenários 8/9/10 têm gap apenas no `smoke-validation.md` (AUD-002, ALTO de documentação, não de código).

### Achados de anti-enumeração
**1 (AUD-017 INFO).** Trade-off documentado em ADR-162 e aceito pelo Mario. Sessão de re-auditoria com token live pode validar byte-a-byte se Mario quiser.

### Achados de modificação não-autorizada do `contrato-c12.md`
**0.** `git diff` vazio.

### Achados de modificação não-autorizada do C15 (Dashboard v3)
**0.** `git diff` vazio. SQL pré/pós-C16 idêntico por byte-equality do código.

### Achados de modificação não-autorizada de outras entregas
**0.** `git diff` vazio em todas (C10, C11, C12, C19, C06, C08, Wave 1 RBAC, máquina v4, RLS, migrations).

### Achados de tratamento errado de provas legacy v3.0
**0.** Heurística D11.2 do C12 aplicada corretamente em `_categoria_predicate` (correlated EXISTS). Em produção: 11 NULL todas com vendedor FILIAL → todas para Filial. Coerente.

### Achados de reuso quebrado do contrato
**0.** `STATUS_OPTIONS`/`ROTA_OPTIONS`/`STATUS_LABELS` etc. todos importados via `lib/types/prova` (validado por grep). Hard-code dos 14 estados ou 4 rotas inexistente.

### Achados de violação de escopo
**0.** 18 arquivos modificados exclusivamente nos paths previstos (4 backend + 7 frontend + 5 docs + raiz CHANGELOG/CLAUDE/DECISIONS + audit-report da auditoria).

### Achados de acessibilidade
**2:** AUD-003 (ALTO — `aria-hidden-focus`) e AUD-005 (MÉDIO — `prefers-reduced-motion`). Ambos com mitigação clara (movimentação de atributo + bloco CSS defensivo). Validação via axe-core no smoke + emulação DevTools.

### Achados de performance
**0 violado.** Cache TTL 60s + ETag + bypass `?_force=1` preservados. Q1 do `_aggregate_geral` em 1 SELECT com 9 contadores via `func.count().filter(...)` — sem N+1. Gap herdado: não medido em staging com volume realista (auditor explicitamente em §1.12 — "depende do smoke do Mario"). Não bloqueante.

### Achados de CSV
**1:** AUD-011 (`consolidacao_rota_indefinida` assimétrico). Correção de 1 LOC.

### Achados de regressão SQL do Dashboard
**0.** Código byte-idêntico.

---

## 9. Plano de validação interna pós-correção

Critérios objetivos da Seção 6.1 do prompt:

| # | Item de validação | Como executar | Quem decide pass/fail |
|---|---|---|:---:|
| 1 | `contrato-c12.md` intocado | `git diff <hash inicial> -- 'docs/wave3-v4-c11/contrato-c12.md'` retorna vazio | Eu |
| 2 | C15 (Dashboard v3) intocado | `git diff <hash inicial> -- 'frontend/src/app/(dashboard)/dashboard/' 'backend/app/api/v1/provas.py' 'backend/app/domain/schemas/dashboard.py' 'frontend/src/hooks/useDashboard.ts'` retorna vazio | Eu |
| 3 | Regressão SQL Dashboard | item 2 já garante; smoke visual no `/dashboard` pelo Mario confirma | Mario |
| 4 | Outras entregas intocadas | `git diff` nos paths listados em §4 do plano retorna vazio | Eu |
| 5 | pytest passa | `pytest backend/tests/` ≥ 1029 tests passed | Eu |
| 6 | Vitest passa | `npx vitest run` ≥ 205 tests passed | Eu |
| 7 | tsc sem erros | `npx tsc --noEmit` exit 0 | Eu |
| 8 | next build | 13/13 páginas | Eu |
| 9 | Bundle `/relatorios` | mantém ~17.9 kB / 220 kB (±0.5 kB tolerância) | Eu |
| 10 | Renderização dos 10 cenários | screenshots no `fix-validation.md` | Mario no smoke |
| 11 | Conformidade com 11 decisões ADR-162 | inspeção visual + grep nos arquivos | Eu + Mario |
| 12 | Reuso do `contrato-c12.md` | grep no diff total: zero hard-code de 14 estados ou 4 rotas | Eu |
| 13 | Anti-enumeração (6 dimensões) | gap registrado (sem token live); ADR-162 D11→i preserva 403 | Mario / re-auditoria |
| 14 | Tratamento provas legacy | fixture explícita no teste novo (AUD-010) + verificação em produção (11 NULL→filial) | Eu |
| 15 | Performance < 3s carga + < 1s filtro | gap herdado; medição depende do Mario no smoke (DevTools Performance) | Mario |
| 16 | Acessibilidade axe-core | rodar extensão axe DevTools no `/relatorios?scope=geral`; confirmar zero violação `aria-hidden-focus` | Mario no smoke |
| 17 | Acessibilidade teclado | Tab + Shift+Tab pelos filtros + `<summary>` do DonutChart + botões — todos focáveis | Mario no smoke |
| 18 | `prefers-reduced-motion` respeitado | DevTools → Rendering → Emulate `prefers-reduced-motion: reduce` → animações zeradas | Eu (rendering) + Mario |
| 19 | Leitor de tela | NVDA/VoiceOver lê tabela sr-only do DonutChart sem duplicação | Mario (se possível) |
| 20 | CSV em Excel pt-BR | abrir export summary; confirmar acentos e 3 linhas `consolidacao_rota_*` | Mario |
| 21 | CSV em LibreOffice Calc | idem | Mario (se possível) |
| 22 | CSV em Google Sheets via import | idem | Mario (se possível) |
| 23 | CSV em editor de texto | abrir em VSCode; encoding UTF-8 BOM detectado | Mario (se possível) |
| 24 | Sincronização com URL | F5 mantém filtros; back/forward navega | Mario no smoke |
| 25 | Cobertura ≥ 80% | declarada no CHANGELOG; D-13 da Wave 1 v4.0 evita persistir `@vitest/coverage-v8` | Eu (declarado) |
| 26 | Migrations | nenhuma criada nesta sessão; estado banco preservado | Eu |
| 27 | Advisors MCP | `get_advisors` idêntico ao baseline | Eu |
| 28 | Console limpo | sem erros/warnings críticos no DevTools | Mario no smoke |
| 29 | `visual-guide.md` atualizado | criado por AUD-001 + screenshots do Mario | Eu (criar) + Mario (preencher) |
| 30 | Apêndice no `audit-report.md` | cada um dos 17 IDs com status final + SHA | Eu |

---

## 10. Plano de atualização de documentação

| Arquivo | Mudança | Tipo |
|---|---|---|
| `CHANGELOG.md` | Nova seção "v4.0 — Wave 5 — Componente 16 — Correções Pós-Auditoria (2026-05-14)" no topo. Lista de achados resolvidos por ID + DEFERRED (nenhum) + ACEITOS. Apêndice. | acumulativo |
| `DECISIONS.md` | Apêndice ao **ADR-162** confirmando aceitação pós-auditoria das decisões D11→i (403) + 5 INFO. Possivelmente 1 ADR novo (ADR-163) registrando "Wave 5 v4.0 C16 — Correções Pós-Auditoria: extração de parsers + rename classes CSS + reuso canônico backend" se Mario quiser visibilidade. | acumulativo |
| `CLAUDE.md` | 1 linha na tabela de waves: "Wave 5 v4.0 C16 Audit Fixes — ✅ COMPLETO (aguarda smoke E2E + PR)" com sumário. | acumulativo |
| `docs/wave5-v4-c16/audit-report.md` | Apêndice "Status pós-correção" no fim, com tabela de 17 linhas: ID · Status final (RESOLVIDO/DEFERRED/ACEITO) · Commit SHA · Critério de resolução. Corpo original NÃO editado. | apêndice |
| `docs/wave5-v4-c16/fix-plan.md` | Seção "Resultado da Execução" anexada no fim do Gate 2, com diffs entre planejado e realizado. | apêndice |
| `docs/wave5-v4-c16/fix-validation.md` | Criar no Gate 2 com checklist da §9, evidências por achado, auto-crítica adversarial. | novo |
| `docs/wave5-v4-c16/visual-guide.md` | Criar no Gate 2 com 4 seções estruturadas (AUD-001). Screenshots ficam para Mario preencher no smoke. | novo |
| `docs/wave5-v4-c16/smoke-validation.md` | Adicionar 3 cenários (#21, #22, #23) no fim antes de "Critério de aprovação"; atualizar contagem total 20 → 23. | expansão |

---

## 11. Achados que requerem nova escalação humana

**NENHUM.** Todos os 17 achados podem ser tratados com as estratégias propostas:
- Os 12 corrigíveis seguem estratégias técnicas convencionais sem nova decisão arquitetural.
- Os 5 sem-ação são ACEITOS conforme ADR-162 / declaração do auditor.
- Não houve decisão de design ignorada que demandasse re-escalação.
- Não houve modificação não-autorizada que exigisse decisão sobre reverter vs encaminhar.

---

## 12. Estimativas

| Bloco | Estimativa |
|---|---:|
| AUD-003 (mover aria-hidden) | ~10 min |
| AUD-004 (refactor + teste) | ~30 min |
| AUD-006 (extração parsers + ajuste hook + ajuste teste) | ~45 min |
| AUD-007+008 (rename + comentário) | ~20 min |
| AUD-005 (CSS media query) | ~15 min |
| AUD-010 (teste novo) | ~30 min |
| AUD-011 (CSV indefinida + teste) | ~15 min |
| AUD-009 (aceitar) | ~5 min |
| AUD-001 (visual-guide.md stub) | ~45 min |
| AUD-002 (smoke-validation +3 cenários) | ~20 min |
| AUD-012-017 (apêndices) | ~15 min |
| Validação completa (pytest + vitest + tsc + build + grep + git diff) | ~30 min |
| Atualização CHANGELOG + DECISIONS + CLAUDE + audit-report apêndice | ~30 min |
| Escrever `fix-validation.md` + auto-crítica | ~45 min |
| **TOTAL estimado** | **~5h30min** |

Auditor estimou **~90 min** para os 3 ALTOS sozinhos; estimativa total inclui MÉDIOS, BAIXOS, validação e documentação.

---

## 13. Plano de validação por achado (resumo)

| ID | Critério objetivo de "RESOLVIDO" |
|---|---|
| AUD-001 | `docs/wave5-v4-c16/visual-guide.md` existe; 4 seções presentes. |
| AUD-002 | `smoke-validation.md` tem 23 cenários; cobre estados vazio/erro/acesso negado. |
| AUD-003 | `DonutChart.tsx:369` SEM `aria-hidden`; `<table>` interna COM `aria-hidden="true"`. axe-core: sem violação `aria-hidden-focus`. |
| AUD-004 | `_CONTEXTO_MOTORISTA_STATUSES` derivado de `contexto_motorista()` canônico via comprehension. Teste cross-validation passa. |
| AUD-005 | `relatorios.module.css` tem bloco `@media (prefers-reduced-motion: reduce)`. DevTools emulation zera animações. |
| AUD-006 | `_useReportFilters.parsers.ts` existe; `useReportFilters.ts` e `useReportFilters.test.ts` importam dele. Zero re-implementação local nos testes. |
| AUD-007 | Grep `rotaDotPadrao\|rotaDotDireta` retorna 0 ocorrências em `frontend/`. `rotaDotMatriz`/`rotaDotFilial` presentes. Visual idêntico. |
| AUD-008 | Comentário Wave 5 v4.0 / C16 fix AUD-007+008 presente acima das classes em `relatorios.module.css`. |
| AUD-009 | Marcado ACEITO no apêndice (docstring atual já cobre). |
| AUD-010 | Classe `TestLegacyNullIndefinida` em `test_reports_v4.py` passa com fixture `vendedor.localizacao=NULL`. |
| AUD-011 | `consolidacao_rota_indefinida` aparece SEMPRE no CSV summary (mesmo com indefinida=0). Teste novo passa. |
| AUD-012 | Marcado ACEITO no apêndice (revisão correta). |
| AUD-013 | Marcado ACEITO no apêndice (padrão Pydantic v2). |
| AUD-014 | Marcado ACEITO no apêndice (CHANGELOG já correto). |
| AUD-015 | Marcado ACEITO no apêndice (após Gate 2 vira "1029 + 10 skipped"). |
| AUD-016 | Marcado ACEITO no apêndice (cobertura herdada). |
| AUD-017 | Marcado ACEITO no apêndice; apêndice no ADR-162 reafirma decisão D11→i pós-auditoria. |

---

## 14. Resultado da Execução (placeholder para Gate 2)

> Esta seção será preenchida no Gate 2 com:
> - Lista linear de commits criados (SHA · título · ID do achado).
> - Diffs entre planejado e realizado (mudanças de estratégia em vôo, justificadas).
> - Itens da validação interna (§9) com status final.
> - Achados que se revelaram não-corrigíveis durante a execução (espera-se: nenhum).

---

**Fim do `fix-plan.md`.** Aguardando autorização Gate 2 para iniciar execução.
