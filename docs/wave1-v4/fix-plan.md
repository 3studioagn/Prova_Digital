# Plano de Correção · Wave 1 v4.0 · Componente 05 (Audit Round 2)

**Sessão:** Correção pós-auditoria sênior (commit `09eaf78`)
**Branch do plano:** `wave1-v4/fixes/plan` (sem merge)
**Branch de execução planejada:** `wave1-v4/fixes/execution`
**Data:** 2026-05-04
**Insumo dirigente:** [`docs/wave1-v4/audit-report.md`](audit-report.md) (755 linhas, 17 achados)
**Persona:** engenheiro de software sênior · correção dirigida por relatório · defesa em profundidade · refactor coordenado seguro
**Status:** Gate 1 — aguardando autorização para Gate 2

---

## 0. Resumo executivo

A auditoria sênior identificou **17 achados** distribuídos como **0 CRÍTICO · 0 ALTO · 6 MÉDIO · 7 BAIXO · 4 INFO**, todos no perímetro de documentação, testes, cobertura e melhorias de defesa em profundidade. **Nenhum é regressão funcional**: a auditoria explicitamente declarou veredito "APROVADO COM CORREÇÕES" e validou (a) JSON SSoT espelhado por TS/Python/RLS, (b) 12 policies em produção referenciando `app_private.current_user_*`, (c) impersonação SQL bate com a Matriz para os 4 perfis em 6 tabelas.

Esta sessão corrige todos os 17 achados, sem exceção, em commits atômicos rastreáveis ao ID. Os 6 MEDIUM são bloqueantes para a Wave 2 v4.0 (recomendação do auditor); os BAIXOS e INFOs vão junto para fechar o ciclo desta wave de RBAC.

**Escopo declarado intacto:** continua valendo o que estava no prompt da execução — Matriz RBAC e o que ela exige. Nenhum recurso novo entra. O refactor coordenado autorizado pela Wave 1 v4.0 segue válido apenas para fins de RBAC.

**Caso especial — AUD-W1V4-005 (criar teste do middleware):** o frontend **não tem test runner** (`frontend/package.json` só declara `dev`/`build`/`start`/`lint`). Aplicar o achado exige escolha pelo solicitante entre 3 caminhos (vide §4.2 e §6).

---

## 1. Confirmação de leitura e validação MCP

### 1.1 Artefatos obrigatórios lidos integralmente

| Artefato | Caminho | Lido |
|---|---|---|
| Relatório de auditoria | `docs/wave1-v4/audit-report.md` (755 linhas) | ✅ |
| Análise pré-execução | `docs/wave1-v4/analysis.md` (1.111 linhas — focado em E.1..E.10 + A.1..A.4) | ✅ |
| CHANGELOG (Wave 1 v4.0 + Audit Fixes) | `CHANGELOG.md` linhas 7962-8214 | ✅ |
| DECISIONS (D-1..D-7) | `DECISIONS.md` linhas 4034-4288 | ✅ |
| CLAUDE.md (seção RBAC) | `CLAUDE.md` linhas 367-431 | ✅ |
| SSoT da Matriz | `shared/access-matrix.json` | ✅ |
| Middleware Next | `frontend/src/lib/supabase/middleware.ts` | ✅ |
| Hook current user | `frontend/src/hooks/useCurrentUser.ts` | ✅ |
| Camada Python access | `backend/app/access/scopes.py` | ✅ |
| Endpoints provas | `backend/app/api/v1/provas.py` (foco em `_scoping_filter`/`_carregar_prova_com_scoping`) | ✅ |
| RLS atual | `backend/migrations/rls/008_revoke_audit_logs_mutation.sql` (template para RLS 013) | ✅ |
| Teste de equivalência Python | `backend/tests/access/test_matrix_rls_equivalence.py` | ✅ |
| Script de equivalência 3 camadas | `scripts/verify_rbac_equivalence.py` (309 linhas) | ✅ |
| Lib access matrix TS | `frontend/src/lib/access-matrix.ts` (foco `getRuleForPath` + `buildRules`) | ✅ |

> **Nota sobre disponibilidade do `audit-report.md` no working tree:** o relatório foi commitado em `09eaf78` no branch `wave1-v4/audit` (não merged em `development`). O arquivo foi materializado na working tree desta sessão via `git show wave1-v4/audit:docs/wave1-v4/audit-report.md > docs/wave1-v4/audit-report.md` (read-only — sem alteração ao branch fonte). O commit do plano vai materializar essa cópia em `wave1-v4/fixes/plan` para que a sessão de correção tenha o documento dirigente acessível pela árvore.

### 1.2 Validação MCP Supabase — projeto `rwxlpwmnkekzuurgthkr` (ACTIVE_HEALTHY, sa-east-1, PG 17)

| Check | Resultado | Bate com relatório? |
|---|---|---|
| Policies em `public.*` referenciando `app_private.current_user_*` | **12 policies** confirmadas: `audit_logs`(1), `configuracoes_sistema`(2), `etiquetas`(1), `movimentacoes`(2), `provas_digitais`(3), `usuarios`(3) | ✅ |
| Funções `current_user_*` em `app_private` (SECURITY DEFINER) | **3 funções**: `current_user_id` → uuid, `current_user_is_admin` → boolean, `current_user_setor` → setor_enum. 0 funções homônimas em `public`. | ✅ |
| `audit_logs`: GRANTs por role | `anon`/`authenticated`: SELECT + REFERENCES + TRIGGER + **TRUNCATE**. INSERT/UPDATE/DELETE revogados (RLS 008). `service_role` mantém todos. | ✅ — confirma AUD-W1V4-101 vigente |
| Contagens-âncora | `provas_digitais=16, movimentacoes=16, etiquetas=16, audit_logs=74, configuracoes_sistema=2, usuarios=4` | ✅ |
| Advisor security | 1 INFO `rls_enabled_no_policy` em `alembic_version` (intencional, ADR-025) + 1 WARN `auth_leaked_password_protection` (WONTFIX, ADR-027) | ✅ — sem novos alertas |
| Advisor performance | 12 INFOs `unused_index` (volume baixo — se manterão até uso real) | ✅ — sem novos alertas |

**Conclusão MCP Supabase:** o estado real do banco em produção bate **exatamente** com o que o relatório descreve. **Nenhum achado bloqueado por divergência.** Nenhuma alteração foi aplicada entre auditoria (2026-04-30) e este plano (2026-05-04).

### 1.3 Validação MCP Cloudflare — account `20ab724c91f6bda669eecfe7c51c9171`

| Check | Resultado |
|---|---|
| Contas ativas | 1 (3studioagn@gmail.com, criada 2026-04-06) |
| R2 buckets | 1 (`rastreio-provas-artes`, criado 2026-04-07) |
| Workers | 0 |

**Conclusão MCP Cloudflare:** intocado desde Wave 0. **Nenhum achado de auditoria exige alteração em Cloudflare** — confirmado.

---

## 2. Inventário consolidado dos 17 achados

> Reproduzido a partir do `audit-report.md` (Seções 2 e §"Achados Consolidados"). Status atual = **pendente** para todos (auditoria fechou em 2026-04-30; nenhum achado foi corrigido entre aquela data e este plano).

### 2.1 CRÍTICOS — 0
_Nenhum._

### 2.2 ALTOS — 0
_Nenhum._

### 2.3 MÉDIOS — 6

| ID | Título | Arquivo:linha | Recomendação | Status |
|---|---|---|---|---|
| **AUD-W1V4-001** | Snippet do `CLAUDE.md` (passo 4) reintroduz o bug do flash de UI corrigido por M-1 | `CLAUDE.md:400-403` | Atualizar snippet para `if (auth.loading) return null; if (!auth.hasAccess) return <Restricted/>` | pendente |
| **AUD-W1V4-002** | Script `verify_rbac_equivalence.py` só valida `provas_digitais` (não 6 tabelas) | `scripts/verify_rbac_equivalence.py:128-215` | Estender para 6 tabelas × 4 perfis. (= M-6 follow-up promovido) | pendente |
| **AUD-W1V4-003** | Etapa [4/4] do script tem assertion frouxa para FULL/PARCIAL — só pega caso NEGADO+count>0 | `scripts/verify_rbac_equivalence.py:257-280` | Adicionar checks por `(rule, profile, table)` triple — comparar count RLS == count esperado | pendente |
| **AUD-W1V4-004** | Nome enganoso `test_matrix_rls_equivalence.py` — só valida Matriz↔Python | `backend/tests/access/test_matrix_rls_equivalence.py` | Renomear para `test_matrix_python_equivalence.py` | pendente |
| **AUD-W1V4-005** | Sem teste do middleware (claim manipulado, JWT malformado, cache LRU, redirect com cookie) | `frontend/src/lib/supabase/middleware.ts` (sem teste) | Criar `__tests__/middleware.test.ts` mockando `createServerClient` | pendente — ⚠ exige escolha de caminho (vide §4.2) |
| **AUD-W1V4-006** | Drift entre snippet do `CLAUDE.md` e padrão pós-M-1 (mesma evidência de 001 — categoria "documentação") | `CLAUDE.md:400-403` | Mesma correção do AUD-001 | pendente — corrigido junto com AUD-001 |

### 2.4 BAIXOS — 7

| ID | Título | Arquivo | Status |
|---|---|---|---|
| **AUD-W1V4-101** | TRUNCATE concedido a `authenticated`/`anon` em `audit_logs` (e demais tabelas — pré-existente, não vetor PostgREST) | n/a (RLS 013 nova) | pendente — confirmado vigente via MCP |
| **AUD-W1V4-102** | Pass-through defensivo em `getRuleForPath = null` permite acesso a rota não mapeada | `frontend/src/lib/supabase/middleware.ts:208-210` | pendente — fix por documentação |
| **AUD-W1V4-103** | Cache LRU 30s no middleware atrasa revogação de admin | `frontend/src/lib/supabase/middleware.ts:54-58` | pendente — fix por documentação |
| **AUD-W1V4-104** | `useCurrentUser` não valida `setor` em runtime | `frontend/src/hooks/useCurrentUser.ts:42-43` | pendente — fix de código |
| **AUD-W1V4-105** | Endpoints de detalhe usam `scope_filter_for("provas.list", ...)` em vez de `provas.detail` | `backend/app/api/v1/provas.py:661-673,885` | pendente — refactor minimal |
| **AUD-W1V4-106** | `_scoping_filter` virou shim — tech debt (= L-2 follow-up aceito) | `backend/app/api/v1/provas.py:661-673` | pendente — registrar status quo formal em DECISIONS |
| **AUD-W1V4-107** | Comentário "M-5: asserça de verdade" no script é otimista para a etapa [4/4] | `scripts/verify_rbac_equivalence.py:217-227` | pendente — atualizado junto com AUD-003 |

### 2.5 INFO — 4

| ID | Título | Onde | Status |
|---|---|---|---|
| **AUD-W1V4-201** | Se Matriz mudar `dashboard` para deny em algum perfil, há risco de redirect loop | `home_by_profile` × `dashboard` rule | pendente — registrar nota informativa |
| **AUD-W1V4-202** | Cenário "registro órfão invisível" não verificado exaustivamente | n/a | pendente — registrar nota informativa |
| **AUD-W1V4-203** | Mudanças de RLS não geram entrada em `audit_logs` | RLS migrations vs `audit_service` | pendente — registrar nota informativa |
| **AUD-W1V4-204** | Extracts dos `.docx` (`docs/wave1-v4/_extracted/*.md`) removidos pós-Gate 1 — perde reprodutibilidade da auditoria | `docs/wave1-v4/_extracted/` (ausente) | pendente — registrar nota informativa |

### 2.6 Achados bloqueados por divergência

**Nenhum.** Confirmado via MCP que o estado descrito pelo relatório é o estado vigente em produção em 2026-05-04.

### 2.7 Achados que se autoclassificariam como expansão de escopo

- **AUD-W1V4-005** — exige decisão de instalar test runner no frontend OU manter como deferred. Vide §4.2.

---

## 3. Plano de correção por achado (estratégia, arquivos, risco, validação, dependências)

> Cada entrada explicita: estratégia, arquivos tocados, tipo de mudança, risco de regressão, teste de validação, dependências de outros achados.

### 3.1 AUD-W1V4-001 + AUD-W1V4-006 — Snippet pre-M-1 no CLAUDE.md (corrigidos juntos)

- **Estratégia.** Trocar o trecho do passo 4 da seção "RBAC: como adicionar uma nova página" no `CLAUDE.md` linhas 400-403 para o padrão pós-M-1. Adicionar comentário curto citando M-1 para evitar drift futuro.
- **Arquivos.** `CLAUDE.md` (modificação).
- **Tipo.** Modificação.
- **Risco de regressão.** Baixíssimo — só documentação consumida por humanos.
- **Validação.** Visual. `git diff CLAUDE.md` mostra exatamente a alteração planejada; `grep -n "auth.loading" CLAUDE.md` retorna a nova guarda.
- **Dependências.** Nenhuma.
- **Justificativa do agrupamento (001+006).** Mesmíssima evidência (linhas 400-403), mesmíssima correção. O auditor classificou nas categorias "Bug" e "Documentação" para registrar a falha em duas ângulos; aqui um único commit resolve as duas entradas, com referência explícita a ambas as IDs no corpo do commit.

### 3.2 AUD-W1V4-002 — Script só valida `provas_digitais`

- **Estratégia.** Estender `scripts/verify_rbac_equivalence.py` para contar 6 tabelas (`provas_digitais`, `movimentacoes`, `etiquetas`, `audit_logs`, `configuracoes_sistema`, `usuarios`) impersonando role `authenticated` para os 4 perfis smoke. Estrutura proposta: dict `RLS_COUNTS = {profile: {table: int}}` populado na etapa [3/4]. Cada `count_visible_*` recebe nome da tabela como parâmetro. Para `usuarios`, o vendedor enxerga 1 (próprio); admin enxerga 4; demais enxergam 0 (nenhum self mapeado). Para `audit_logs` e `configuracoes_sistema`, todos não-admin enxergam 0.
- **Arquivos.** `scripts/verify_rbac_equivalence.py` (modificação).
- **Tipo.** Modificação (script standalone — não impacta CI nem produção).
- **Risco de regressão.** Baixo — script standalone executado manualmente; falha → exit code 1 visível, sem efeito em prod.
- **Validação.**
  1. Rodar o script em produção com `DATABASE_URL` setado (read-only para o smoke; escrita apenas dos 4 usuários temporários + cleanup).
  2. Esperado: SUCESSO, com saída discriminando 6 tabelas × 4 perfis = 24 counts.
  3. Smoke negativo: introduzir uma divergência manual (ex.: trocar setor smoke do "vendedor" por VENDEDOR no dict expected) e confirmar que script falha — depois reverter.
- **Dependências.** Bloqueia AUD-003 (a etapa [4/4] depende dos counts coletados aqui).

### 3.3 AUD-W1V4-003 — Etapa [4/4] frouxa

- **Estratégia.** Reescrever a etapa [4/4] do `verify_rbac_equivalence.py` para iterar `(rule, profile, table)` aplicáveis e comparar `RLS_COUNTS[profile][table]` com count esperado pela Matriz Python. As regras com escopo PARCIAL têm matriz `tabela ↔ scope` previsível:
  - `provas.list` / `provas.detail` afetam `provas_digitais`, `movimentacoes` (via prova), `etiquetas` (via prova).
  - `auditoria` / `relatorios` / `configuracoes` / `usuarios` / `provas.create` / `provas.cancel` / `provas.restart` afetam apenas o que a regra discrimina (admin only) — counts esperados são 0/total/total conforme decision.
  - Para cada `(rule, profile)` com `decision.acesso == NEGADO`, count esperado em `tabela_principal` deve ser 0 (já validado parcialmente em [3/4] do script atual).
  - Para `decision.acesso == FULL`, count esperado = total da tabela (admin smoke).
  - Para `decision.acesso == PARCIAL`, count esperado = count da query equivalente do Python (`scope_filter_for(rule, user)`).
  Uma `EXPECTED_MATRIX = {(rule_key, profile): {table: count_expected}}` consolida o que a [4/4] precisa comparar.
- **Arquivos.** `scripts/verify_rbac_equivalence.py` (modificação).
- **Tipo.** Modificação.
- **Risco de regressão.** **Médio** — é o achado de maior risco. A nova [4/4] pode (a) falsificar SUCESSO se a comparação for mal escrita, (b) falsificar FALHA por incompatibilidade de unidades. Mitigação: introduzir 1 caso de teste dentro do próprio script — uma divergência sintética (ex.: criar uma prova extra como vendedor smoke e validar que count vendedor sobe para 1) — e validar antes do cleanup.
- **Validação.**
  1. Rodar contra prod com Matriz atual: SUCESSO esperado.
  2. Smoke positivo: inserir 1 prova com `vendedor_id = SMOKE_VENDEDOR_ID`; rodar; counts vendedor `provas_digitais`/`movimentacoes`/`etiquetas` devem subir para 1 (vendedor expected = 1); script deve continuar SUCESSO. Reverter.
  3. Smoke negativo: alterar manualmente `SMOKE_USER_IDS[VENDEDOR]` para um id que não existe na seed; rodar; script deve FALHAR no profile mismatch ou divergência de count. Reverter.
- **Dependências.** Requer AUD-002 (counts das 6 tabelas disponíveis). Atende AUD-107 (atualiza implicitamente o comentário "asserça de verdade" para refletir a nova cobertura).

### 3.4 AUD-W1V4-004 — Renomear `test_matrix_rls_equivalence.py`

- **Estratégia.** `git mv backend/tests/access/test_matrix_rls_equivalence.py backend/tests/access/test_matrix_python_equivalence.py`. A classe interna já se chama `TestMatrixPythonEquivalence` (linha 55 do arquivo) — sem ajuste de classe necessário. Atualizar a docstring do módulo para deixar claro que é equivalência **Matriz JSON ↔ Python** (não RLS). Atualizar referências em outros arquivos via `grep -rn "test_matrix_rls_equivalence"` (esperado: zero usos externos).
- **Arquivos.** `backend/tests/access/test_matrix_rls_equivalence.py` → `test_matrix_python_equivalence.py` (rename + edição da docstring).
- **Tipo.** Rename + modificação.
- **Risco de regressão.** Baixo — apenas o nome do arquivo muda; pytest descobre por padrão `test_*.py`.
- **Validação.**
  1. `git status` confirma rename (não apagar/recriar).
  2. `pytest backend/tests/access/ -v` lista o teste novo no nome correto e passa (1 teste, 48 cells).
  3. `grep -rn "test_matrix_rls_equivalence" backend/` retorna 0.
- **Dependências.** Nenhuma.

### 3.5 AUD-W1V4-005 — Criar testes do middleware (caso especial: frontend não tem test runner)

**Situação observada via inspeção do `frontend/package.json`:** não há `vitest` / `jest` / `@testing-library/*` instalado; scripts disponíveis: `dev`, `build`, `start`, `lint`. Adicionar suite de teste do middleware exige decisão de infraestrutura.

**Caminhos avaliados:**

| Opção | Prós | Contras | Recomendação |
|---|---|---|---|
| **A. Instalar Vitest (mínimo)** | Padrão moderno; integra Next 14; 1 devDep + 1 config + 1 script `test`. Cobre o achado plenamente. | Mudança de infra dev (não prod). Pequena janela de risco em CI (não há CI ainda — `lint` é o único check). | **PREFERIDA** — escopo limitado a devDependency + arquivo de config; nada de produção tocado. |
| **B. `node:test` (built-in Node 18+)** | Zero deps. Suficiente para funções puras (`getRuleForPath`, `isPublicPath`, `ruleNeedsProfileLookup`). | Pesado para mockar `createServerClient` (precisa stubs de `next/server` + `@supabase/ssr`); cobertura parcial. | Aceita como fallback se A for rejeitada. |
| **C. Manter como deferred (status L-1)** | Zero mudança. | Achado MEDIUM fica em aberto; o auditor explicitamente promoveu de LOW para MEDIUM por ser "camada superior da defesa em profundidade". | Aceita se solicitante priorizar minimizar escopo desta sessão. Documentar formalmente em DECISIONS.md. |

**Plano default (Opção A — Vitest mínimo):**
- **Arquivos novos:** `frontend/vitest.config.ts` (mínimo, ambient `node`), `frontend/src/lib/supabase/__tests__/middleware.test.ts`.
- **Arquivos modificados:** `frontend/package.json` (devDeps `vitest`, `@vitest/coverage-v8` opcional; script `"test": "vitest run"`).
- **Cobertura mínima do test:** (a) `isPublicPath` para 4 prefixos canônicos + 1 não-público; (b) `getRuleForPath` para path com/sem trailing slash; (c) `ruleNeedsProfileLookup` para rota universal vs restritiva; (d) `loadProfile` cache hit/miss + bloqueio em `ativo=false` (mockando `supabase.from(...).select(...).eq(...).maybeSingle()`); (e) decisão FULL/PARCIAL/NEGADO em `updateSession` com mock completo de request/`getUser`/profile (5 cenários: anonimo→login, admin→pass, vendedor em /usuarios→redirect, vendedor em /provas→pass+header `x-rbac-scope`, user com `ativo=false`→`/login` com cookie).
- **Risco de regressão.** **Médio**: instalação de devDep + config impacta `npm install` e dev workflow do frontend. Mitigação: `vitest run` é opt-in (não roda no `next build`); CI atual não roda testes do frontend, então não há quebra de pipeline.
- **Validação.**
  1. `cd frontend && npm install`: sem erros.
  2. `cd frontend && npm run test`: ≥ 5 cenários passando.
  3. `cd frontend && npm run lint && npm run build`: sem regressão.
- **Dependências.** Nenhuma técnica. **Bloqueado por decisão do solicitante** (escolha entre A/B/C). O Gate 2 só executa este achado após instrução explícita.

**Decisão a obter no Gate 2:** "Para AUD-W1V4-005, prossiga com Opção A (Vitest mínimo) | Opção B (node:test, cobertura parcial) | Opção C (deferred com justificativa formal)."

### 3.6 AUD-W1V4-101 — REVOKE TRUNCATE em `audit_logs`

- **Estratégia.** Criar `backend/migrations/rls/013_revoke_truncate_audit_logs.sql` espelhando o template do RLS 008. Conteúdo: `REVOKE TRUNCATE ON public.audit_logs FROM anon, authenticated;` + cabeçalho explicando o porquê (TRUNCATE bypassa RLS e o trigger de imutabilidade não cobre TRUNCATE; vetor exigiria conexão direta via psql, não exposto pelo PostgREST, mas defesa em profundidade RNF-005). Aplicar via MCP `apply_migration` em produção.
- **Arquivos.** `backend/migrations/rls/013_revoke_truncate_audit_logs.sql` (novo).
- **Tipo.** Novo + DDL aplicada em produção.
- **Risco de regressão.** Baixo — `service_role` mantém TRUNCATE; backend não usa TRUNCATE; PostgREST não expõe TRUNCATE.
- **Validação.**
  1. Pre: `SELECT has_table_privilege('authenticated','public.audit_logs','TRUNCATE')` = `true`.
  2. Aplicar migration via `mcp__c7b61d2f-..__apply_migration` (Supabase MCP).
  3. Pos: `SELECT has_table_privilege('authenticated','public.audit_logs','TRUNCATE')` = `false`.
  4. Pos: `SELECT has_table_privilege('service_role','public.audit_logs','TRUNCATE')` = `true` (preservado).
  5. Re-executar advisor security: zero novos alertas.
  6. Idempotência: aplicar 2x sem erro.
- **Dependências.** Nenhuma.

### 3.7 AUD-W1V4-102 — Pass-through `getRuleForPath = null` (documentação)

- **Estratégia.** Adicionar parágrafo no passo 1 da seção "RBAC: como adicionar uma nova página" do `CLAUDE.md` alertando que **omitir entrada na Matriz para rota nova = pass-through silencioso**, então cada rota nova exige entrada (mesmo que `full` para os 4 perfis). Não implementar regra CI nesta sessão — fica como follow-up técnico (relatório §"Recomendados não bloqueantes" item 6).
- **Arquivos.** `CLAUDE.md` (modificação).
- **Tipo.** Modificação.
- **Risco de regressão.** Zero (só docs).
- **Validação.** Visual.
- **Dependências.** Nenhuma. Tocará o mesmo arquivo do AUD-001/006 — para preservar atomicidade, vai em commit separado.

### 3.8 AUD-W1V4-103 — Cache LRU 30s — documentar latência

- **Estratégia.** Acrescentar nota explícita na mesma seção do `CLAUDE.md` sobre a **latência de até 30s** ao alterar `is_admin`/`setor`/`ativo` em produção. Texto: "Após PATCH/DELETE em /api/v1/users/{id}, o middleware pode continuar deixando o usuário passar até 30s — defesa em profundidade preservada por backend (`get_current_user`) + RLS (helpers fresh)." Não implementar invalidação ativa nesta sessão — fica como follow-up técnico.
- **Arquivos.** `CLAUDE.md` (modificação).
- **Tipo.** Modificação.
- **Risco de regressão.** Zero (só docs).
- **Validação.** Visual.
- **Dependências.** Nenhuma. Toca o mesmo arquivo de AUD-001/006 e AUD-102; vai em commit separado para atomicidade.

### 3.9 AUD-W1V4-104 — `useCurrentUser` sem validação runtime

- **Estratégia.** Adicionar guard manual em `useCurrentUser.ts` que valida que `user.setor` está em `["STUDIO","VENDEDOR","MOTORISTA","CLICHERIA"]` e `user.is_admin` é boolean. Se inválido, `setState({ user: null, loading: false })` (deny seguro). `console.warn` opcional para logging (não falha silenciosa). Sem nova dependência (zod fora do escopo).
- **Arquivos.** `frontend/src/hooks/useCurrentUser.ts` (modificação).
- **Tipo.** Modificação.
- **Risco de regressão.** Baixo — em produção todos os 4 usuários têm setor válido (`STUDIO` ou `VENDEDOR`); guard só roda no edge case de backend retornando lixo.
- **Validação.**
  1. Smoke preview: login admin → user carregado normalmente.
  2. Smoke preview com mock: simular response inválido (via DevTools) → user=null.
  3. `npm run build` sem erro de typecheck.
- **Dependências.** Nenhuma.

### 3.10 AUD-W1V4-105 — Endpoints detail usam `provas.list` em vez de `provas.detail`

- **Estratégia.** Em `backend/app/api/v1/provas.py`:
  1. Criar nova função interna `_scoping_filter_for_detail(user)` que delega para `scope_filter_for("provas.detail", user)`. Mantém a função `_scoping_filter` atual (delegando para `provas.list`) para os endpoints de listagem.
  2. Em `_carregar_prova_com_scoping` linha 885, trocar `_scoping_filter(user)` por `_scoping_filter_for_detail(user)`.
  3. Adicionar comentário explicando que a Matriz separa `provas.list` (listagem) de `provas.detail` (página de detalhe e endpoints derivados — imagem-url, movimentações, etiqueta, qr-code) — semantica idêntica hoje, mas convencionalmente correto.
- **Arquivos.** `backend/app/api/v1/provas.py` (modificação).
- **Tipo.** Modificação minimal (~5 linhas).
- **Risco de regressão.** Baixo — `test_provas_detail_inherits_provas_list_scopes` garante semântica idêntica entre `provas.list` e `provas.detail` (lê do JSON SSoT). Logo, mudar a chave não muda comportamento.
- **Validação.**
  1. `pytest backend/tests/test_provas_api.py -v` — 59 testes (Wave 2 C06+C07+C08) passam.
  2. `pytest backend/tests/access/test_scope_filter_for.py -v` — 7 testes passam.
  3. Smoke MCP: contar provas vistas pelo vendedor smoke (impersonado) em `/api/v1/provas/{id}` antes vs depois — esperado: idêntico.
- **Dependências.** Nenhuma.

### 3.11 AUD-W1V4-106 — `_scoping_filter` shim (registrar L-2 como status formal)

- **Estratégia.** Registrar em `DECISIONS.md` apêndice "D-8 — `_scoping_filter` mantido como shim (status formal de L-2)" justificando: (a) inline nas ~7 chamadas é refactor de código de Wave 2 fora do escopo desta sessão de RBAC; (b) o shim é trivial e tem 1 linha (`return scope_filter_for("provas.list", user)`), legível; (c) já existe registro na seção de Audit Fixes (CHANGELOG linha 8201). A entrada formaliza que esta sessão revisitou e mantém o status quo conscientemente.
- **Arquivos.** `DECISIONS.md` (modificação — apêndice).
- **Tipo.** Modificação documental (apêndice acumulativo).
- **Risco de regressão.** Zero.
- **Validação.** Visual.
- **Dependências.** Nenhuma.

### 3.12 AUD-W1V4-107 — Comentário "M-5 asserça de verdade"

- **Estratégia.** Atualizar o bloco de comentário no `verify_rbac_equivalence.py` linhas 218-227 para refletir a cobertura **expandida** após AUD-002 + AUD-003: "Confronta a Matriz Python com counts RLS para 6 tabelas × 4 perfis (~24 cells), por (rule, profile, table) onde a regra é aplicável. Para cells com decision==NEGADO valida count==0; para FULL valida count==total; para PARCIAL valida count == count via scope_filter_for + query equivalente." Naturalmente, o comentário pode ser inline ao trabalho de AUD-003 — mas para atomicidade, vai em commit separado posicionado logo após AUD-003.
- **Arquivos.** `scripts/verify_rbac_equivalence.py` (modificação).
- **Tipo.** Modificação documental in-code.
- **Risco de regressão.** Zero.
- **Validação.** Visual + grep "asserça de verdade" retorna 0.
- **Dependências.** Após AUD-003.

### 3.13 AUD-W1V4-201 — Risco de redirect loop se Matriz mudar `dashboard`

- **Estratégia.** Registrar em `DECISIONS.md` apêndice "D-9 — Invariante: `dashboard` deve permanecer FULL para todos os 4 perfis OU `home_by_profile` deve ser revisitado simultaneamente". Justificativa: hoje os 4 perfis têm `dashboard=full`. Se algum mudar para `negado`, o redirect 302 levaria para `home_by_profile` que é `/dashboard` para 3 perfis = loop. Documentar como invariante; futuras edições da Matriz devem validar essa relação. Não implementar verificação automática nesta sessão (seria nova entrada na suite de testes ou no script verify).
- **Arquivos.** `DECISIONS.md` (modificação — apêndice).
- **Tipo.** Modificação documental.
- **Risco de regressão.** Zero.
- **Validação.** Visual.
- **Dependências.** Nenhuma.

### 3.14 AUD-W1V4-202 — Cenário órfão não verificado

- **Estratégia.** Registrar em `DECISIONS.md` apêndice "D-10 — Cenário 'registro órfão invisível' aceito como improvável dado FK constraints + triggers de imutabilidade". Mencionar que a verificação exaustiva fica como follow-up técnico fora desta wave.
- **Arquivos.** `DECISIONS.md`.
- **Tipo.** Modificação documental.
- **Risco de regressão.** Zero.
- **Validação.** Visual.
- **Dependências.** Nenhuma.

### 3.15 AUD-W1V4-203 — Mudanças de RLS não geram entradas em `audit_logs`

- **Estratégia.** Registrar em `DECISIONS.md` apêndice "D-11 — Mudanças de RLS são rastreadas via `supabase_migrations` + commits Git, não via `audit_logs`". Justificativa: `audit_logs` é log de domínio (movimentações de provas, mudanças de usuário); mudanças de schema/RLS são DDL versionada com rastreabilidade própria. Adicionar audit_log para DDL seria nova feature, fora do escopo.
- **Arquivos.** `DECISIONS.md`.
- **Tipo.** Modificação documental.
- **Risco de regressão.** Zero.
- **Validação.** Visual.
- **Dependências.** Nenhuma.

### 3.16 AUD-W1V4-204 — Extracts dos `.docx` removidos pós-Gate 1

- **Estratégia.** Registrar em `DECISIONS.md` apêndice "D-12 — Extracts em `docs/wave1-v4/_extracted/` foram removidos no closeout do Gate 2 da Wave 1 v4.0; reprodutibilidade da auditoria garantida por (a) citações textuais em `analysis.md` Seção 3, (b) `EXPECTED_KEYS` em `test_matrix_structure.py`, (c) `_clicheria_divergence_note` em `shared/access-matrix.json`, (d) os `.docx` originais em Desktop/Rastreio Prova Digital/." Não restaurar os extracts nesta sessão (foge do escopo de RBAC). Eventual restauração ficaria como follow-up técnico se novas auditorias precisarem.
- **Arquivos.** `DECISIONS.md`.
- **Tipo.** Modificação documental.
- **Risco de regressão.** Zero.
- **Validação.** Visual.
- **Dependências.** Nenhuma.

> **Agrupamento dos 4 INFOs (201-204).** Como nenhum tem alteração de código, todos vão em **um único commit `docs(wave1-v4/AUD-201..204): registrar INFOs como notas/invariantes em DECISIONS`**, com apêndices D-9..D-12. Justificativa: 4 entradas pequenas no mesmo arquivo, mesma natureza (registro de status/decisão sem ação de código), mesma data.

---

## 4. Ordem de execução (topológica, respeitando severidade e dependências)

### 4.1 Sequência canônica

| Posição | ID(s) | Tipo de commit | Arquivo principal |
|---|---|---|---|
| **1** | AUD-W1V4-001 + AUD-W1V4-006 | `docs(wave1-v4/AUD-001+006)` | `CLAUDE.md` (passo 4) |
| **2** | AUD-W1V4-004 | `refactor(wave1-v4/AUD-004)` | `tests/access/` (rename) |
| **3** | AUD-W1V4-002 | `feat(wave1-v4/AUD-002)` | `scripts/verify_rbac_equivalence.py` (counts 6 tabs) |
| **4** | AUD-W1V4-003 | `feat(wave1-v4/AUD-003)` | `scripts/verify_rbac_equivalence.py` (asserção [4/4]) |
| **5** | AUD-W1V4-005 | `test(wave1-v4/AUD-005)` ou `chore(wave1-v4/AUD-005-deferred)` | (ver §3.5) — exige decisão |
| **6** | AUD-W1V4-101 | `chore(wave1-v4/AUD-101)` | `migrations/rls/013_revoke_truncate_audit_logs.sql` |
| **7** | AUD-W1V4-105 | `refactor(wave1-v4/AUD-105)` | `backend/app/api/v1/provas.py` |
| **8** | AUD-W1V4-104 | `fix(wave1-v4/AUD-104)` | `frontend/src/hooks/useCurrentUser.ts` |
| **9** | AUD-W1V4-102 | `docs(wave1-v4/AUD-102)` | `CLAUDE.md` (rota não mapeada) |
| **10** | AUD-W1V4-103 | `docs(wave1-v4/AUD-103)` | `CLAUDE.md` (latência cache) |
| **11** | AUD-W1V4-107 | `docs(wave1-v4/AUD-107)` | `scripts/verify_rbac_equivalence.py` (comentário) |
| **12** | AUD-W1V4-106 | `docs(wave1-v4/AUD-106)` | `DECISIONS.md` (D-8) |
| **13** | AUD-W1V4-201 + 202 + 203 + 204 | `docs(wave1-v4/AUD-201..204)` | `DECISIONS.md` (D-9..D-12) |

**Total:** 13 commits para 17 achados (2 agrupamentos justificados: 001+006 idênticos; 201..204 INFOs documentais sem ação de código).

### 4.2 Justificativa da ordem

1. **MEDIUMs primeiro, BAIXOs depois, INFOs por último** (regra hierárquica do prompt).
2. Dentro dos MEDIUMs:
   - 001+006 (docs) primeiro: trivial, baixo risco, libera o caminho.
   - 004 antes de 002+003: rename é independente, evita conflito de blame se 002/003 mexem em testes irmãos no futuro.
   - 002 antes de 003: 003 depende dos counts coletados em 002.
   - 005 por último (depende de decisão do solicitante).
3. Dentro dos BAIXOs:
   - 101 (RLS 013) primeiro: aplica DDL em prod, melhor cedo no fluxo para validar advisor pós.
   - 105 (refactor minimal) e 104 (frontend hook) — independentes, ordem indiferente; escolhi 105 antes para fechar backend antes de tocar frontend.
   - 102+103 (docs CLAUDE.md) consecutivos.
   - 107 (comentário script) requer 003 já feito.
   - 106 (DECISIONS) por último entre BAIXOS.
4. INFOs num único commit final.

---

## 5. Análise de risco agregado

### 5.1 Achados com risco ALTO de regressão

**Nenhum** — após classificar os 17 achados.

### 5.2 Achados com risco MÉDIO de regressão (mitigação dedicada)

- **AUD-W1V4-003** — reescrita da etapa [4/4] do script. Mitigação: rodar smoke positivo (script atual passa) + smoke negativo (introduzir divergência sintética; script falha) antes de declarar resolvido. Reverter divergência ao final.
- **AUD-W1V4-005** — instalação de Vitest no frontend (caminho A). Mitigação: bloqueado por decisão explícita do solicitante; se aprovado, validar que `next build` continua limpo após instalação.

### 5.3 Achados com risco BAIXO

Todos os outros 15 achados.

### 5.4 Achados que tocam código de Waves 0–6 da v3.0

- **AUD-W1V4-105** — toca `backend/app/api/v1/provas.py` (Wave 2 C07/C08). Mudança restrita ao caminho de RBAC (`_scoping_filter_for_detail`); preserva semântica de scoping; coberto pelo refactor coordenado autorizado pela Wave 1 v4.0. Sem expansão de escopo.

### 5.5 Achados que exigem nova migration RLS

- **AUD-W1V4-101** — `backend/migrations/rls/013_revoke_truncate_audit_logs.sql`. Idempotente (REVOKE de privilege ausente é no-op). Aplicado via MCP `apply_migration` em produção. Validação: `has_table_privilege` antes/depois + advisor security pós.

### 5.6 Achados que mexem em testes

- **AUD-W1V4-004** — rename. Não fragiliza; pytest continua descobrindo.
- **AUD-W1V4-005** — adiciona testes novos (não modifica existentes).
- **AUD-W1V4-002 + 003** — modificam o script standalone (não a suíte pytest); script tem comportamento mais estrito após (não menos) — não é teste relaxado.

### 5.7 Achados que potencialmente fragilizam testes existentes

**Nenhum.** Todas as correções somam cobertura ou mantêm; nenhuma relaxa assertion.

---

## 6. Plano de validação interna pós-correção (Seção 6 do prompt)

### 6.1 Critério objetivo de "resolvido" por achado

| ID | Critério |
|---|---|
| AUD-001+006 | `grep -n "if (auth.loading) return null" CLAUDE.md` retorna ≥ 1 hit; `grep -n "!auth.loading && !auth.hasAccess" CLAUDE.md` retorna 0. |
| AUD-002 | Saída do script lista counts para 6 tabelas × 4 perfis = 24 contagens; SUCESSO. |
| AUD-003 | Smoke positivo: 1 prova injetada para vendedor smoke faz count vendedor subir para 1, script ainda SUCESSO. Smoke negativo: divergência sintética faz script FAIL. |
| AUD-004 | `git status` mostra rename; `pytest backend/tests/access/test_matrix_python_equivalence.py` passa; `grep -rn "test_matrix_rls_equivalence" backend/` retorna 0. |
| AUD-005 (caminho A) | `cd frontend && npm run test` passa ≥ 5 cenários do middleware; `npm run build` continua limpo. |
| AUD-005 (caminho C) | Entrada formal em `DECISIONS.md` com justificativa; CHANGELOG marca como **deferred**. |
| AUD-101 | `has_table_privilege('authenticated','public.audit_logs','TRUNCATE')` = false; advisor security sem novos alertas. |
| AUD-102 | `grep -n "rota não mapeada" CLAUDE.md` retorna ≥ 1 hit. |
| AUD-103 | `grep -n "30s" CLAUDE.md` retorna ≥ 1 hit no contexto de revogação de admin. |
| AUD-104 | `grep -n "STUDIO\|VENDEDOR\|MOTORISTA\|CLICHERIA" frontend/src/hooks/useCurrentUser.ts` mostra guard runtime. |
| AUD-105 | `grep -n "scope_filter_for(\"provas.list\"" backend/app/api/v1/provas.py` retorna 1 hit (em `_scoping_filter`, não em `_carregar_prova_com_scoping`); novo `_scoping_filter_for_detail` chama `provas.detail`. |
| AUD-106 | DECISIONS.md tem entry "D-8" referenciando L-2 status quo. |
| AUD-107 | `grep -n "asserça de verdade" scripts/verify_rbac_equivalence.py` retorna 0; comentário menciona "6 tabelas". |
| AUD-201..204 | DECISIONS.md tem entries D-9..D-12. |

### 6.2 Suítes a rodar no fechamento

| Suite | Comando | Critério |
|---|---|---|
| Backend pytest | `cd backend && python -m pytest -q` (a partir do venv `.venv`) | 761+ testes passam (sem regressão; +0 — esta sessão não cria pytest novo no backend). |
| Backend lint | `cd backend && ruff check` | Limpo. |
| Frontend lint | `cd frontend && npm run lint` | Limpo. |
| Frontend typecheck | `cd frontend && npx tsc --noEmit` | Limpo. |
| Frontend build | `cd frontend && npm run build` | Limpo. |
| Frontend test (se Opção A) | `cd frontend && npm run test` | ≥ 5 cenários middleware passando. |
| Script verify (3 camadas) | `DATABASE_URL=... python scripts/verify_rbac_equivalence.py` | SUCESSO; 24 counts (6 tabs × 4 perfis); 48 cells validadas. |
| MCP advisor security | tool call | 1 INFO + 1 WARN históricos; nenhum novo. |
| MCP advisor performance | tool call | 12 INFOs `unused_index` históricos; nenhum novo. |
| MCP `pg_policies` | tool call | 12 policies; todas referenciando `app_private.current_user_*`. |
| `has_table_privilege` audit_logs | MCP `execute_sql` | TRUNCATE=false para anon/authenticated; SELECT=true; service_role=todos. |

### 6.3 Greps finais (anti-drift)

| Padrão | Esperado | Por quê |
|---|---|---|
| `if (!auth.loading && !auth.hasAccess)` em `CLAUDE.md` | 0 | M-1 + AUD-001+006 |
| `Depends(get_admin_user)` em `backend/app/api/v1/{audit_log,configuracoes,reports,users}.py` | 0 (apenas em `users.py:GET /{id}` legacy invariante) | refactor coordenado preservado |
| `require_role(` em código de produção | 0 | já removido na Wave 1 v4.0 |
| `scope_filter_for("provas.list"` no caminho de detalhe | 0 (após AUD-105) | nova chave `provas.detail` |
| `test_matrix_rls_equivalence` (nome do arquivo) | 0 | AUD-004 |
| `asserça de verdade` (comentário antigo) | 0 (após AUD-107) | redação atualizada |

### 6.4 Auto-crítica explícita (Seção 6.3 do prompt — postura adversarial)

A sessão registrará no `fix-validation.md` final respostas honestas para:

1. **Algum teste foi feito sob medida para passar?** Em particular para AUD-003 (smoke negativo do script): a divergência sintética precisa exercer um cenário plausível, não apenas "qualquer mismatch". Critério: a divergência precisa simular drift real (ex.: vendedor smoke sem provas mas script espera 1).
2. **Alguma correção mascarou sintoma sem resolver causa?** Particularmente para AUD-104 (runtime guard). Critério: a causa raiz é "backend pode retornar setor inválido"; o guard fecha o sintoma (deny seguro), mas não previne backend bugado. Documentar.
3. **Alguma assertion foi relaxada para fazer teste passar?** Não há mudança em testes pytest existentes. Confirmar.
4. **Alguma decisão de design minimizou trabalho em vez de seguir caminho técnico?** Para AUD-005 caminho B (node:test): se aprovado, cobre menos do que o auditor pediu. Se aprovado, registrar formalmente.
5. **Algum INFO foi tratado de forma minimalista?** AUD-201..204 são todos registros documentais. O auditor não pediu ação ativa para nenhum deles. Aceitável.

### 6.5 Recomendação final

O `fix-validation.md` terminará com uma das três recomendações do prompt:

- **PR pronto para merge.** Todas as correções aplicadas e validadas (cenário esperado se nenhum smoke negativo aparecer).
- **PR pronto para merge condicional.** Se AUD-005 ficar deferred (Opção C aprovada), assinalar essa única deferida com justificativa.
- **Sessão precisa ser estendida ou refeita.** Apenas se algum smoke real falhar e exigir reescopo (improvável).

E, **em qualquer caso**, registrará: "Recomenda-se nova rodada de auditoria independente em sessão separada, usando o `PROMPT_Auditoria_PosWave1_v4.md`, para confirmar que (a) achados originais foram resolvidos e (b) correções não introduziram novos problemas."

---

## 7. Plano de atualização de documentação (acumulativo)

| Arquivo | Item a adicionar | Tipo |
|---|---|---|
| `CHANGELOG.md` | Nova subseção **"v4.0 — Wave 1 — Componente 05 — Audit Round 2 Fixes (pos-auditoria sênior)"** com lista por ID + commit SHA + arquivo modificado. Histórico anterior preservado. | Apêndice |
| `DECISIONS.md` | **D-8** (AUD-106 — `_scoping_filter` shim status quo). **D-9** (AUD-201 — invariante dashboard×home_by_profile). **D-10** (AUD-202 — registro órfão aceito como improvável). **D-11** (AUD-203 — mudanças RLS rastreadas via supabase_migrations). **D-12** (AUD-204 — extracts removidos). Se AUD-005 for Opção C: **D-13** (AUD-005 deferred com justificativa). | Apêndice |
| `CLAUDE.md` | Passo 4 da seção RBAC corrigido (M-1+AUD-001+006). Nota nova no passo 1 sobre rota não mapeada (AUD-102). Nota sobre latência cache 30s na seção crítica (AUD-103). | Modificação in-loco + apêndice |
| `docs/wave1-v4/audit-report.md` | **Apêndice "Status final por achado"** mapeando ID → commit SHA → critério verificado. Não editar o corpo original. | Apêndice |
| `docs/wave1-v4/fix-plan.md` (este) | Seção final **"Resultado da Execução"** ao fim do Gate 2, com diff entre planejado e realizado. | Apêndice |
| `docs/wave1-v4/fix-validation.md` | Criado no Gate 2 final. Checklist 100% + auto-crítica + recomendação. | Novo |

---

## 8. Itens explicitamente fora de escopo desta sessão (registrados como follow-up)

Os seguintes itens **não são corrigidos** nesta sessão e ficam como follow-up técnico (registrado no CHANGELOG no closeout):

- **Regra CI** que falhe se houver `app/(dashboard)/<x>/page.tsx` sem entrada na Matriz (recomendação relator §"Itens de backlog técnico" item 6).
- **Invalidação ativa do cache LRU** do middleware quando admin é desativado/promovido (item 7).
- **Confirmação D-2 com Renan** sobre Clicheria FULL vs PARCIAL (item 9).
- **Restauração dos extracts dos `.docx`** em `docs/wave1-v4/_extracted/` (item 10).
- **L-3..L-8** do Audit Fixes anterior (já listados no CHANGELOG linha 8204-8214). Continuam como follow-up.

Esta sessão **não regride** nenhum desses itens; apenas reafirma o status quo.

---

## 9. Pedido explícito de autorização para Gate 2

**Sumário:** plano cobre **17/17 achados** do `audit-report.md` em **13 commits atômicos** (2 agrupamentos justificados). Ordem topológica respeita severidade (MEDIUM → LOW → INFO) e dependências internas (AUD-002 antes de AUD-003; AUD-003 antes de AUD-107). Nenhum achado bloqueado por divergência. Risco médio em 2 achados (AUD-003 e AUD-005) com mitigações dedicadas. Validação cobre 6 suites, 12 greps e 4 checks MCP.

**Decisão pendente para AUD-W1V4-005:**

- **Opção A (PREFERIDA):** instalar Vitest mínimo e criar suíte de testes do middleware com ≥ 5 cenários. Mudança limitada a devDependency + 1 config + 1 script + 1 arquivo de teste. Cobre o achado plenamente.
- **Opção B:** usar `node:test` built-in para testar funções puras do middleware (cobertura parcial; não cobre `updateSession` orquestrador completo).
- **Opção C:** manter como deferred, registrar D-13 em `DECISIONS.md` com justificativa formal.

**Aguardando string `AUTORIZADO GATE 2 — CORREÇÃO WAVE 1 v4.0` para prosseguir** (acompanhada da escolha A/B/C para AUD-W1V4-005).
