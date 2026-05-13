# Wave 3 v4.0 · Componente 11 · Plano de Correção Pós-Auditoria (Gate 1)

**Data:** 2026-05-13
**Branch alvo:** `wave3-v4-c11/fixes/plan` (sai de `development`, sem merge) — Gate 1.
**PR de execução:** `wave3-v4-c11/fixes/execution` (Gate 2) → `development`.
**Origem:** [`docs/wave3-v4-c11/audit-report.md`](audit-report.md) — auditoria sênior independente em 2026-05-13 (Claude Opus 4.7).
**Modo:** Read-only nesta fase. Nenhuma linha de código de produção foi tocada.

---

## 0. Sumário (≤ 28 linhas)

Total de achados no `audit-report.md`: **2 CRÍTICOS · 3 ALTOS · 5 MÉDIOS · 6 BAIXOS · 6 INFO = 22 entradas com IDs**. Após consolidar 3 duplicações intencionais declaradas pelo auditor (`AUD-006 ≡ AUD-004`, `AUD-014 ≡ AUD-009`, `AUD-016 ≡ AUD-008`), o número de achados **únicos** cai para **19**.

**Categorias especiais:**
- **Drift na Matriz canônica vs implementação:** ZERO (auditor declarou conformidade par a par).
- **Dessincronia do enum em 3 camadas:** ZERO (auditor validou byte-a-byte).
- **Modificação não-autorizada da máquina v3.0:** ZERO (`git diff` vazio em `backend/app/services/state_machine.py`).
- **Trigger no banco inadequado:** ZERO (Decisão M-4 / ADR-150 respeitada).
- **Coexistência rompida (legacy ↔ v4.0):** ZERO (17 provas em produção, sem cruzamento).
- **Decisão de escalação humana ignorada:** 1 — M-7 implementada sem ADR formal (AUD-009/014).
- **Violação de escopo:** ZERO (sem timeline C12, sem backfill Wave 7, sem dashboard Wave 4).
- **Anti-enumeração quebrada:** ZERO em vazamento; mas **AUD-001/002 criam FALSO NEGATIVO** — motorista e clicheria recebem 404 onde deveriam acessar (Matriz §5 quebrada na primária Python). Não é vazamento; é o oposto, mas funcionalmente bloqueia rotas inteiras.
- **Concorrência:** ZERO (FOR UPDATE + 409 já tratado).
- **Afeta C12:** Nenhum bloqueia C12 começar (timeline visual consome `useScanProva`/`useProvaDetail` que funcionam para vendedor/admin); AUD-001/002 só impactam quando motorista/clicheria visualizar prova v4.0 — corrigir antes do PR final do C12.

**1 ponto de nova escalação humana** (AUD-005, ver §6).

---

## 1. Confirmação de leitura dos artefatos da Seção 2 do prompt

### 1.1 Artefatos centrais

| # | Caminho | Lido | Notas |
|---|---|---|---|
| 1 | [docs/wave3-v4-c11/audit-report.md](audit-report.md) (963 LOC) | ✅ | Documento dirigente desta sessão; 22 entradas com IDs |
| 2 | [docs/wave3-v4-c11/contrato-c12.md](contrato-c12.md) (408 LOC) | ✅ | 11 seções, tipos exportados, helpers documentados |
| 3 | [docs/wave3-v4-c11/analysis.md](analysis.md) (1158 LOC) | ✅ | Gate 1 + Apêndice A Execução |
| 4 | [docs/wave3-v4-c11/_agent_extraction.md](_agent_extraction.md) (633 LOC) | ✅ existência | Extração literal dos 4 documentos canônicos |

### 1.2 Arquivos vivos do repositório (estado pós-C11)

| Arquivo | Lido |
|---|---|
| [CLAUDE.md](../../CLAUDE.md) | ✅ (system prompt) |
| [CHANGELOG.md](../../CHANGELOG.md) | ✅ (seção Wave 3 v4.0 / C11 — linhas 5-185) |
| [DECISIONS.md](../../DECISIONS.md) — ADRs 146-153 | ✅ (linhas 6254-6567) |
| [backend/app/access/scopes.py](../../backend/app/access/scopes.py) (114 LOC) | ✅ integralmente |
| [backend/app/state_machine/v4/rules.py](../../backend/app/state_machine/v4/rules.py) (235 LOC) | ✅ integralmente |
| [backend/app/state_machine/v4/machine.py](../../backend/app/state_machine/v4/machine.py) (cobrindo `pode_cancelar`, `executar_transicao_v4` linha 213-389) | ✅ |
| [backend/migrations/rls/014_expand_visibility_v4_states.sql](../../backend/migrations/rls/014_expand_visibility_v4_states.sql) (179 LOC) | ✅ integralmente |
| [shared/access-matrix.json](../../shared/access-matrix.json) (173 LOC) | ✅ integralmente |
| [frontend/src/lib/types/prova.ts](../../frontend/src/lib/types/prova.ts) (chunk linhas 210-235 — comment outdated) | ✅ |
| [backend/tests/access/test_scope_filter_for.py](../../backend/tests/access/test_scope_filter_for.py) (92 LOC) | ✅ integralmente |
| [backend/tests/test_provas_api.py](../../backend/tests/test_provas_api.py) (linhas 1290-1349) | ✅ chunk relevante |

### 1.3 Confirmação das 6+ decisões de escalação humana em `DECISIONS.md`

| ID | ADR | Status | Opção escolhida |
|---|---|---|---|
| M-1 — Ator FILIAL.CRIADA→ENCAMINHADA_PARA_O_VENDEDOR | ADR-146 | ✅ Registrado | **A** — Vendedor (texto literal §5.4 prevalece) |
| M-2 — Estrutura do enum | ADR-147 | ✅ Registrado | **A** — `ALTER TYPE status_prova_enum ADD VALUE` x7 |
| M-2b — `COM_MOTORISTA` legacy vs `_ENTREGA_FINAL` v4.0 | ADR-148 | ✅ Registrado | **(a)** — valores DISTINTOS no enum |
| M-3 — Endpoints da v4.0 | ADR-149 | ✅ Registrado | **A** — reusar `POST /{id}/transicoes` |
| M-4 — Trigger PostgreSQL semântico | ADR-150 | ✅ Registrado | **A** — NÃO criar (invariância no Python) |
| M-5 — Contexto do motorista | ADR-151 | ✅ Registrado | **A+C** — derivado de status + `audit_log.detalhes_json` |
| M-6 — Payload `TransicaoRequest` | ADR-152 | ✅ Registrado | **A** — inalterado |
| **M-7 — Mensagens de erro pt-BR** | **AUSENTE** | ⚠️ Só em `analysis.md §A.1` | **B** — conciso, voz ativa (implementação verificada em `machine.py:186-207`) |
| M-8 — Rate limit | ADR-153 | ✅ Registrado | **A** — sem rate limit (follow-up junto com ADR-145) |

**M-7 implementada conforme a decisão, mas sem ADR dedicado** — finding `AUD-009/014` LOW/MED. Plano §3 cobre criação de ADR-154 post-hoc.

### 1.4 Qualidade do `contrato-c12.md`

408 LOC, 11 seções. Seções de mapeamento reproduzidas literalmente (todas as 17 entradas do `StatusProva` + helper `contextoMotorista` Python+TS + `ROTA_ETAPAS` sugerido + endpoints `GET /provas/{id}` + `GET /provas/{id}/movimentacoes`). **Viável para C12 iniciar em paralelo.** Apenas atualização a fazer: §1.4 paleta cores aceita pelo C12 quando definir sua paleta. Seções §5 (endpoints) e §2 (helpers) não mudam pelo plano de correção.

---

## 2. Validação MCP do estado real do banco (Seção 3 do prompt)

### 2.1 Supabase — Projeto `rwxlpwmnkekzuurgthkr` (sa-east-1)

| Item | Esperado pelo audit-report | Estado real (MCP read-only) | Bate? |
|---|---|---|---|
| `alembic_version` | `'013'` | `'013'` | ✅ |
| `status_prova_enum` — 17 valores | 10 v3.0 + 7 v4.0 | 17 valores idênticos | ✅ |
| Ordem alfabética dos 7 v4.0 (sortorder 11-17) | `COM_MOTORISTA_ENTREGA_FINAL`, `COM_MOTORISTA_IDA_LAMINACAO`, `COM_MOTORISTA_VOLTA_LAMINACAO`, `DE_VOLTA_3STUDIO_POS_LAMINACAO`, `ENCAMINHADA_PARA_LAMINACAO`, `ENCAMINHADA_PARA_O_VENDEDOR`, `LAMINACAO_CONCLUIDA` | Confirmado byte-a-byte | ✅ |
| Triggers ativos em `provas_digitais` | `trg_provas_rota_imutavel` + `trg_provas_updated_at` (sem trigger semântico) | Confirmado — também 7 triggers totais no schema `public.*` (todos preservados) | ✅ |
| RLS policies `pol_provas_select`, `pol_movimentacoes_select`, `pol_etiquetas_select` | Motorista 4 estados + Clicheria 6 estados | Confirmado — `qual` retornado pelo `pg_policies` bate literalmente com `014_expand_visibility_v4_states.sql` | ✅ |
| Distribuição de provas (17 total) | Sem cruzamento legacy↔v4.0 | 5 CRIADA NULL + 2 REPROVADA NULL + 4 CANCELADA NULL + 1 CANCELADA DIRETA + 2 RECEBIDA DIRETA + 2 CANCELADA PADRAO + 1 CRIADA MATRIZ = 17. Sem cruzamento. | ✅ |
| Advisors security | 1 INFO `rls_enabled_no_policy` em `alembic_version` (ADR-025) + 1 WARN `auth_leaked_password_protection` (ADR-027) | Confirmados — sem novos alertas | ✅ |

**Veredito:** Estado real **bate integralmente** com a descrição do `audit-report.md`. Nenhum cruzamento. Nenhuma divergência. Estado é seguro para iniciar correções sem ajuste prévio do banco.

### 2.2 Cloudflare R2

Não exigida modificação pelo `audit-report.md`. Nenhum achado mexe em R2. Considerada saudável.

### 2.3 Bloqueios

Nenhum bloqueio. Estado limpo para Gate 2.

---

## 3. Inventário consolidado dos achados (Seção 4.1 do prompt)

Tabela com **22 entradas** (IDs do relatório) — duplicações declaradas pelo auditor mantidas com referência cruzada.

| ID | Severidade | Categoria | Resumo (1-2 linhas) | Arquivo | Status | Drift Matriz? | Dessinc enum? | Mod v3.0? | Trigger? | Coexist? | Escalação ignorada? | Viol escopo? | Afeta C12? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AUD-001 | CRÍTICO | Correção | `_MOTORISTA_STATUSES` não inclui 3 contextos v4.0; motorista recebe 404 em provas v4.0 | `backend/app/access/scopes.py:50-52` | Pendente | não | não | não | não | não | não | não | parcial — afeta quando motorista visualizar |
| AUD-002 | CRÍTICO | Correção | `_CLICHERIA_STATUSES` não inclui 4 estados v4.0; clicheria não conclui rotas v4.0 + RLS 014 falta `COM_MOTORISTA_ENTREGA_FINAL` para clicheria (paridade) | `backend/app/access/scopes.py:55-59` + `migrations/rls/014_*.sql` | Pendente | não | não | não | parcial (paridade RLS) | não | não | não | parcial |
| AUD-003 | HIGH | Documentação | `shared/access-matrix.json scope_kinds` strings v3.0-only — SSoT inconsistente com Matriz §6 + Backlog NT | `shared/access-matrix.json:19-24` | Pendente | não | não | não | não | não | não | não | não |
| AUD-004 | HIGH | Cobertura | Falta cobertura E2E motorista/clicheria em estados v4.0; bugs como AUD-001/002 não capturados | `backend/tests/test_provas_api.py:1304-1331` | Pendente | não | não | não | não | não | não | não | não |
| AUD-005 | HIGH | Aderência | Critério 15 do prompt (botões inline transição) NÃO entregue; decisão pendente do Mario | `frontend/src/app/(dashboard)/provas/[id]/page.tsx` | **REQUER NOVA ESCALAÇÃO** | não | não | não | não | não | não | não | não |
| AUD-006 | HIGH | Cobertura | **Duplicação intencional de AUD-004** | idem | Pendente — corrigido junto | não | não | não | não | não | não | não | não |
| AUD-007 | MED | Cobertura | Drift Python↔Postgres skipped em CI sem `INTEGRATION_DATABASE_URL` | `backend/tests/test_status_prova_enum_drift.py:78-83` | Pendente | não | não | não | não | não | não | não | não |
| AUD-008 | MED | Performance/Manut. | Inconsistência subquery vs EXISTS nas 3 policies RLS | `backend/migrations/rls/014_*.sql` | Pendente | não | não | não | parcial (refactor cosmético) | não | não | não | não |
| AUD-009 | MED | Documentação | Decisão M-7 sem ADR formal | `DECISIONS.md` | Pendente | não | não | não | não | não | **sim (M-7)** | não | não |
| AUD-010 | MED | Manutenibilidade | Docstring `pode_cancelar` com aritmética errada (10+5 ≠ 8+7) | `backend/app/state_machine/v4/machine.py:71-72` | Pendente | não | não | não | não | não | não | não | não |
| AUD-011 | LOW | Manutenibilidade | Comment "10 estados" outdated em `STATUS_LABELS_SHORT` | `frontend/src/lib/types/prova.ts:215` | Pendente | não | não | não | não | não | não | não | não |
| AUD-012 | LOW | Manutenibilidade | CHANGELOG narrativa "9 v3.0 → 14 v4.0" confusa (real: 17 valores no enum) | `CHANGELOG.md:9-10` | Pendente | não | não | não | não | não | não | não | não |
| AUD-013 | LOW | Manutenibilidade | Test count discrepância 87 funções vs 139 declared | `analysis.md §A.5`, `CHANGELOG.md` | Pendente | não | não | não | não | não | não | não | não |
| AUD-014 | LOW | Documentação | **Duplicação intencional de AUD-009** | idem | Pendente — corrigido junto | não | não | não | não | não | sim | não | não |
| AUD-015 | INFO | Preparação C12 | `contrato-c12.md` adequado | — | Sem ação | não | não | não | não | não | não | não | sim |
| AUD-016 | MED | Performance | **Duplicação intencional de AUD-008** | idem | Pendente — corrigido junto | não | não | não | parcial | não | não | não | não |
| AUD-017 | LOW | Performance | Sem benchmark dedicado de transição | `analysis.md §A.5` | Pendente | não | não | não | não | não | não | não | não |
| AUD-018 | INFO | Segurança | Sem trigger semântico — ADR-150 | — | Sem ação | não | não | não | não | não | não | não | não |
| AUD-019 | INFO | Concorrência | FOR UPDATE + 409 já tratado | — | Sem ação | não | não | não | não | não | não | não | não |
| AUD-020 | INFO | Segurança | Anti-enumeração preservada | — | Sem ação | não | não | não | não | não | não | não | não |
| AUD-021 | INFO | Regressão | Camadas anteriores intocadas (positivo) | — | Sem ação | não | não | não | não | não | não | não | não |
| AUD-022 | INFO | Cobertura | 100% no módulo v4 | — | Sem ação | não | não | não | não | não | não | não | não |
| AUD-024 | LOW | Manutenibilidade | `motivo_cancelamento_norm` setado em prova mesmo se não muda outros campos — comportamento idêntico v3.0; auditor declarou aceitável | `backend/app/state_machine/v4/machine.py:354` | **Sem ação** — registrar no apêndice | não | não | não | não | não | não | não | não |

**Total único após dedup**: 19 achados. **Acionáveis em código:** 14 (CRÍTICO 2 + HIGH 3 + MED 4 + LOW 5; AUD-005 requer decisão humana). **Sem ação:** 6 INFOs + AUD-024 LOW (aceitável conforme auditor).

---

## 4. Plano de correção por achado (Seção 4.2 do prompt)

### 4.1 AUD-W3C11-001 (CRÍTICO) — Atualizar `_MOTORISTA_STATUSES`

- **Tipo:** Adição de lógica primária (RBAC scope).
- **Estratégia:** Estender o tuple `_MOTORISTA_STATUSES` em `backend/app/access/scopes.py:50-52` para incluir os 3 estados v4.0 do motorista (`COM_MOTORISTA_IDA_LAMINACAO`, `COM_MOTORISTA_VOLTA_LAMINACAO`, `COM_MOTORISTA_ENTREGA_FINAL`). Atualizar o comentário das linhas 47-49 removendo o follow-up "Wave 3 v4.0 ampliará" — agora histórico, substituir por descrição do estado final pós-C11.
- **Não modifica:** máquina v3.0; timeline visual (C12); backfill (Wave 7); camada serviço C10; cadastro C06; fallback C19; trigger no banco; nenhum CSS.
- **Arquivos tocados:** `backend/app/access/scopes.py` (apenas). 4 linhas adicionadas + 3 comentário ajustadas.
- **Camadas:** backend RBAC primária.
- **Risco de regressão:** ALTO — afeta todas as queries com scope motorista (`/api/v1/provas/`, `/api/v1/provas/scan`, `/api/v1/provas/{id}/*`).
- **Mitigação:** AUD-004 entrega testes E2E que validam exatamente este caminho. Suite existente `backend/tests/access/test_scope_filter_for.py::test_motorista_provas_list_filters_by_status_em_transito` continua passando (verifica que "COM_MOTORISTA" está no SQL — string é prefixo de todos os v4.0). Testes novos do AUD-004 vão asserir presença de cada um dos 3 v4.0 explicitamente.
- **Teste que valida:** novo teste em `test_scope_filter_for.py::test_motorista_v4_inclui_3_contextos` + smoke MCP simulado.
- **Dependência:** nenhuma. Executar primeiro.

### 4.2 AUD-W3C11-002 (CRÍTICO) — Atualizar `_CLICHERIA_STATUSES` + RLS 015

- **Tipo:** Adição de lógica primária (RBAC scope) + nova migration RLS (paridade primária↔secundária).
- **Estratégia (parte A — Python):** Estender o tuple `_CLICHERIA_STATUSES` em `backend/app/access/scopes.py:55-59` para incluir os 4 estados v4.0 da clicheria: `ENCAMINHADA_PARA_LAMINACAO`, `COM_MOTORISTA_IDA_LAMINACAO`, `LAMINACAO_CONCLUIDA`, `COM_MOTORISTA_ENTREGA_FINAL`. Atualizar comentário.
- **Estratégia (parte B — RLS 015):** Criar `backend/migrations/rls/015_clicheria_inclui_com_motorista_entrega_final.sql` que DROP+CREATE as 3 policies (`pol_provas_select`, `pol_movimentacoes_select`, `pol_etiquetas_select`) estendendo o ARRAY de clicheria com `COM_MOTORISTA_ENTREGA_FINAL`. Idempotente, aplicada via MCP `apply_migration`. **Não altera motorista (RLS 014 já cobre 4 estados).**
- **Não modifica:** máquina v3.0; máquina v4.0; cadastro C06; camada serviço C10; fallback C19; nenhum trigger; nenhum CSS.
- **Arquivos tocados:** `backend/app/access/scopes.py` (linhas 55-59) + `backend/migrations/rls/015_clicheria_inclui_com_motorista_entrega_final.sql` (novo).
- **Camadas:** backend RBAC primária + RLS secundária.
- **Risco de regressão:** ALTO — afeta todas as queries com scope clicheria + escritas via Supabase client.
- **Mitigação:** AUD-004 entrega testes E2E para clicheria. Smoke MCP `apply_migration` (testar em transação dry-run? Supabase MCP aplica direto; validar pós-aplicação com `SELECT polname FROM pg_policy`).
- **Teste que valida:** novo `test_scope_filter_for.py::test_clicheria_v4_inclui_4_estados` + validação MCP da policy pós-migration.
- **Dependência:** nenhuma. Executar em sequência ao AUD-001.
- **Considerações:** RLS 015 deve ser uniformizada para EXISTS junto com AUD-008/016 — combinar (commit único de migration RLS 015 que já reescreve as 3 policies em estilo EXISTS).

### 4.3 AUD-W3C11-003 (HIGH) — Atualizar SSoT `shared/access-matrix.json scope_kinds`

- **Tipo:** Documentação SSoT.
- **Estratégia:** Editar `shared/access-matrix.json:19-24`:
  - `status_motorista_em_transito`: reescrever para `"status IN (COM_MOTORISTA, COM_MOTORISTA_IDA_LAMINACAO, COM_MOTORISTA_VOLTA_LAMINACAO, COM_MOTORISTA_ENTREGA_FINAL) (motorista vê em trânsito — v3.0 legacy + 3 contextos v4.0)"`.
  - `status_clicheria`: reescrever para `"status IN (ENVIADA_PARA_CLICHERIA, ENCAMINHADA_A_CLICHERIA, RECEBIDA_PELA_CLICHERIA, ENCAMINHADA_PARA_LAMINACAO, COM_MOTORISTA_IDA_LAMINACAO, LAMINACAO_CONCLUIDA, COM_MOTORISTA_ENTREGA_FINAL) (clicheria vê — 3 v3.0 + 4 v4.0 incluindo entrega final)"`.
- **Não modifica:** Python, RLS (estes ficam para AUD-001/002), TS espelho do `access-matrix.ts` se houver — verificar e ajustar comentário equivalente.
- **Arquivos tocados:** `shared/access-matrix.json` (linhas 19-24). Eventualmente espelho TS se descobrir comentário duplicado.
- **Risco de regressão:** BAIXO — apenas strings descritivas.
- **Teste que valida:** validação manual + `test_matrix_structure.py` se existir validação de `scope_kinds` (verificar). Sem novo teste obrigatório.
- **Dependência:** nenhuma. Pode ser feito em paralelo com AUD-001/002.

### 4.4 AUD-W3C11-004 + AUD-W3C11-006 (HIGH) — Testes E2E motorista/clicheria em estados v4.0

- **Tipo:** Adição de cobertura de testes.
- **Estratégia:** Criar testes em 2 níveis:
  1. **Unit (scope filter):** Em `backend/tests/access/test_scope_filter_for.py` — `test_motorista_v4_inclui_3_contextos` e `test_clicheria_v4_inclui_4_estados`, asserindo presença explícita de cada valor v4.0 no SQL renderizado (não apenas substring "COM_MOTORISTA").
  2. **API list (`/provas`):** Em `backend/tests/test_provas_api.py` (ou `test_provas_api_v4.py`) — `test_list_motorista_inclui_v4_3_contextos` e `test_list_clicheria_inclui_v4_4_estados`, asserindo cada string v4.0 no SQL renderizado.
  3. **API scan (`/scan`):** novo `test_scan_motorista_em_estado_v4_passa_scoping` e `test_scan_clicheria_em_lam_concluida_passa_scoping` — mocka `_carregar_prova_por_codigo_publico_com_scoping`, valida que o scope agora aceita os v4.0.
- **Não modifica:** código de produção (cobertura).
- **Arquivos tocados:** `backend/tests/access/test_scope_filter_for.py` + `backend/tests/test_provas_api.py` (ou criar `test_provas_api_v4_rbac.py`).
- **Total esperado:** ≥ 6 testes novos.
- **Risco de regressão:** ZERO — só adiciona testes.
- **Teste que valida:** os próprios testes.
- **Dependência:** **executar depois de AUD-001 e AUD-002** — os testes asserem o estado pós-correção.

### 4.5 AUD-W3C11-005 (HIGH) — Critério 15 (botões inline) — **REQUER NOVA ESCALAÇÃO HUMANA**

- **Tipo:** Decisão arquitetural pendente do Mario.
- **Estado:** AUD-005 não pode ser "corrigido" automaticamente. O auditor explicitamente pede decisão entre:
  - **(a)** Aceitar o deferral (scanner em `/escanear` continua canônico). Registrar follow-up técnico em ADR-155 + DEFERRED no `CHANGELOG.md`. PR para `development` segue.
  - **(b)** Pedir nova sessão dedicada que entregue botões "Aprovar/Reprovar/Encaminhar" inline no `/provas/[id]/page.tsx` com signature canvas modal (~150-200 LOC novos). Sessão separada, antes do PR para `main`.
- **Eu (correção automática) não posso decidir.** Listado no Gate 1 como **PRECISA ESCALAR antes do Gate 2** (Seção 6 deste plano).
- **Se decisão (a):** apenas atualizar `CHANGELOG.md` + criar ADR-155 + atualizar status em apêndice do `audit-report.md`. Frontend intocado.
- **Se decisão (b):** **abortar este Gate 2** (escopo desta sessão é só correção da auditoria); abrir nova sessão dedicada.

### 4.6 AUD-W3C11-007 (MED) — Drift Python↔Postgres em CI normal

- **Tipo:** Cobertura de testes em CI.
- **Estratégia:** Documentar em ADR-156 (novo) que o teste `test_status_prova_enum_drift_python_postgres` em `backend/tests/test_status_prova_enum_drift.py` requer `INTEGRATION_DATABASE_URL`. Recomendação técnica: adicionar job CI/CD dedicado em `.github/workflows/` que use `services.postgres` container + roda esse teste. **Decisão técnica:** se complexo, classificar como follow-up DEFERRED com encaminhamento para sessão de CI/CD pós-merge (não é blocker para este Gate 2 fechar).
- **Não modifica:** o teste em si; código de produção.
- **Arquivos tocados:** `DECISIONS.md` (ADR-156); opcionalmente `.github/workflows/ci.yml` se decidirmos implementar agora.
- **Risco de regressão:** ZERO.
- **Teste que valida:** o ADR-156 documenta a decisão.
- **Dependência:** nenhuma.

### 4.7 AUD-W3C11-008 + AUD-W3C11-016 (MED) — Uniformizar policies RLS para EXISTS

- **Tipo:** Refactor cosmético + performance.
- **Estratégia:** A migration RLS 015 (criada para AUD-002) já reescreve as 3 policies — aproveitar para uniformizar tudo para EXISTS em vez de `IN (SELECT ...)`. Padrão: `EXISTS (SELECT 1 FROM provas_digitais pd WHERE pd.id = movimentacoes.prova_id AND ...)`. Termina ao primeiro match.
- **Não modifica:** semântica das policies (mesma cobertura) — apenas reescreve cláusulas.
- **Arquivos tocados:** `backend/migrations/rls/015_*.sql` (já criada para AUD-002).
- **Risco de regressão:** BAIXO — semântica preservada. Mitigação: `EXPLAIN ANALYZE` antes e depois (read-only via MCP) em query representativa.
- **Teste que valida:** smoke MCP — `SELECT polname FROM pg_policies` + tentar acesso como motorista impersonado (limitado: MCP não suporta `SET ROLE authenticated` perfeitamente; validar por inspeção).
- **Dependência:** combinada com AUD-002 (commit único de migration).

### 4.8 AUD-W3C11-009 + AUD-W3C11-014 (MED+LOW) — ADR-154 para M-7

- **Tipo:** Documentação ADR.
- **Estratégia:** Criar ADR-154 em `DECISIONS.md` post-hoc com o formato consistente dos ADRs 146-153. Documentar:
  - Data: 2026-05-13 (Wave 3 v4.0 / C11 — Gate 1 Decisão M-7).
  - Contexto: 5 cenários de mensagens novas (transição inválida, ator errado, terminal, reinício rejeitado, cancelamento em terminal).
  - Decisão: Opção B — voz ativa concisa.
  - Justificativa: melhor UX, menor risco de exposição de detalhes (DAT §8.2).
  - Consequências: implementação em `machine.py:186-207`.
- **Não modifica:** código de produção.
- **Arquivos tocados:** `DECISIONS.md`.
- **Risco de regressão:** ZERO.
- **Teste que valida:** revisão visual.
- **Dependência:** nenhuma.

### 4.9 AUD-W3C11-010 (MED) — Corrigir docstring de `pode_cancelar`

- **Tipo:** Documentação inline.
- **Estratégia:** Em `backend/app/state_machine/v4/machine.py:64-75`, reescrever o trecho:
  ```
  Os outros 15 valores do enum (10 v3.0 + 5 v4.0 ativos) sao todos
  cancelaveis.
  ```
  para:
  ```
  Os outros 15 valores do enum (8 v3.0 ativos + 7 v4.0 ativos) sao
  todos cancelaveis. Total enum = 17 (10 v3.0 + 7 v4.0); subtraindo
  os 2 terminais (RECEBIDA, CANCELADA) = 15 ativos.
  ```
- **Não modifica:** lógica.
- **Arquivos tocados:** `backend/app/state_machine/v4/machine.py`.
- **Risco de regressão:** ZERO.
- **Teste que valida:** revisão visual.
- **Dependência:** nenhuma.

### 4.10 AUD-W3C11-011 (LOW) — Comment outdated em `STATUS_LABELS_SHORT`

- **Tipo:** Documentação inline.
- **Estratégia:** Em `frontend/src/lib/types/prova.ts:214`, trocar "todos os 10 estados" por "todos os 17 estados (10 v3.0 + 7 v4.0)".
- **Arquivos tocados:** `frontend/src/lib/types/prova.ts`.
- **Risco de regressão:** ZERO.
- **Dependência:** nenhuma.

### 4.11 AUD-W3C11-012 (LOW) — Reformular narrativa CHANGELOG

- **Tipo:** Documentação.
- **Estratégia:** Em `CHANGELOG.md` linhas 9-10, reformular `"de 9 estados v3.0 para 14 estados v4.0"` → `"10 valores v3.0 -> 17 valores no enum (14 estados canônicos via unificação semântica entre COM_MOTORISTA legacy e COM_MOTORISTA_ENTREGA_FINAL v4.0)"`. Apêndice em "Correções Pós-Auditoria".
- **Arquivos tocados:** `CHANGELOG.md`.
- **Risco de regressão:** ZERO.
- **Dependência:** nenhuma.

### 4.12 AUD-W3C11-013 (LOW) — Esclarecer test count

- **Tipo:** Documentação.
- **Estratégia:** Em `analysis.md §A.5` e `CHANGELOG.md`, adicionar nota: `(139 = 87 funções base + ~52 expansões via @pytest.mark.parametrize)`. Apêndice.
- **Arquivos tocados:** `analysis.md` (Apêndice A.5) + `CHANGELOG.md`.
- **Risco de regressão:** ZERO.
- **Dependência:** nenhuma.

### 4.13 AUD-W3C11-017 (LOW) — Sem benchmark dedicado

- **Tipo:** Cobertura/qualidade.
- **Estratégia:** Documentar em `DECISIONS.md` (apêndice ao ADR-153 ou novo ADR-157) que o benchmark dedicado de `/transicoes` será feito junto com a sessão de rate-limit (ADR-145 + ADR-153). Marcar como WONTFIX-DEFERRED pós-merge para `main`. Sem ação de código nesta sessão.
- **Arquivos tocados:** `DECISIONS.md` (apêndice).
- **Risco de regressão:** ZERO.
- **Dependência:** nenhuma.

### 4.14 AUD-W3C11-024 (LOW) — `motivo_cancelamento_norm` aceitável

- **Tipo:** Sem ação (auditor declarou aceitável).
- **Estratégia:** Registrar em apêndice do `audit-report.md` que o achado é **ACEITO sem mudança de código** — comportamento idêntico ao v3.0 + auditor declara "Aceitável, sem ação".
- **Arquivos tocados:** apêndice do `audit-report.md` apenas.
- **Risco de regressão:** ZERO.
- **Dependência:** nenhuma.

### 4.15 INFOs (AUD-015, 018, 019, 020, 021, 022)

- **Tipo:** Sem ação.
- **Estratégia:** Registrar em apêndice do `audit-report.md` que cada um é **ACEITO sem mudança de código** — auditor declarou "Sem ação".
- **Arquivos tocados:** apêndice do `audit-report.md`.
- **Risco de regressão:** ZERO.

---

## 5. Ordem de execução topológica (Seção 4.3 do prompt)

Respeitando hierarquia: CRÍTICO → ALTO → MED → LOW → INFO. Dentro de cada grupo: dependências + decisão de escalação ignorada + dessincronia enum + drift matriz + coexistência + trigger + anti-enumeração + modificação v3.0 + outros.

| # | ID | Severidade | Categoria especial | Depende de | Tipo de commit |
|---|---|---|---|---|---|
| 1 | **AUD-001** | CRÍTICO | Defesa primária quebrada | — | `fix(wave3-v4/c11/AUD-001)` |
| 2 | **AUD-002** | CRÍTICO | Defesa primária + RLS paridade (RLS 015 + uniformizar EXISTS conforme AUD-008/016) | — | `fix(wave3-v4/c11/AUD-002)` (Python + nova migration RLS 015) |
| 3 | **AUD-003** | HIGH | Documentação SSoT | — | `docs(wave3-v4/c11/AUD-003)` |
| 4 | **AUD-004/006** | HIGH | Cobertura de testes — valida AUD-001/002 | AUD-001, AUD-002 | `test(wave3-v4/c11/AUD-004)` |
| 5 | **AUD-005** | HIGH | **REQUER DECISÃO HUMANA — aguardando antes do Gate 2** | — | (depende da decisão: `docs(...AUD-005)` se (a); aborta este Gate 2 se (b)) |
| 6 | **AUD-009/014** | MED + LOW (M-7) | Decisão escalação ignorada — criar ADR-154 | — | `docs(wave3-v4/c11/AUD-009)` |
| 7 | **AUD-010** | MED | Manutenibilidade | — | `docs(wave3-v4/c11/AUD-010)` (docstring inline) |
| 8 | **AUD-008/016** | MED | Refactor RLS — combinado com migration RLS 015 (AUD-002) | AUD-002 | (parte de #2) |
| 9 | **AUD-007** | MED | CI/CD — ADR-156 (decisão técnica) | — | `docs(wave3-v4/c11/AUD-007)` |
| 10 | **AUD-011** | LOW | Comment outdated | — | `docs(wave3-v4/c11/AUD-011)` |
| 11 | **AUD-012** | LOW | CHANGELOG narrativa | — | `docs(wave3-v4/c11/AUD-012)` |
| 12 | **AUD-013** | LOW | Test count esclarecimento | — | `docs(wave3-v4/c11/AUD-013)` |
| 13 | **AUD-017** | LOW | Benchmark — ADR-157 ou apêndice | — | `docs(wave3-v4/c11/AUD-017)` |
| 14 | **AUD-024** | LOW | Sem ação — registrar como aceito | — | `docs(wave3-v4/c11/AUD-024)` |
| 15-20 | **AUD-015/018/019/020/021/022** | INFO | Sem ação — registrar como aceitos | — | `docs(wave3-v4/c11/AUD-INFO)` (commit consolidado) |

**Ordem final de execução:** `[AUD-001, AUD-002, AUD-003, AUD-004, AUD-005 (humano), AUD-009, AUD-010, AUD-007, AUD-011, AUD-012, AUD-013, AUD-017, AUD-024, INFOs]`.

**Após cada CRÍTICO ou ALTO corrigido:** rodar smoke parcial (suite `tests/access/` + `tests/state_machine/` + `tests/test_provas_api.py`).

---

## 6. Análise de risco agregado (Seção 4.4 do prompt)

| Categoria | IDs | Mitigação |
|---|---|---|
| **Risco ALTO de regressão** | AUD-001, AUD-002 | Testes novos do AUD-004 + EXPLAIN ANALYZE MCP + smoke MCP de policies. Validação manual com vendedor matriz/admin para garantir não-afetação. |
| **Drift Matriz canônica** | (nenhum) | — |
| **Dessincronia de enum** | (nenhum) | — |
| **Modificação não-autorizada v3.0** | (nenhum) | — |
| **Trigger no banco** | (nenhum — Decisão M-4 respeitada) | — |
| **Coexistência rompida** | (nenhum — confirmado em produção) | — |
| **Decisão de escalação ignorada** | AUD-009/014 (M-7) | ADR-154 post-hoc resolve sem mudança de código (decisão já implementada). |
| **Violação de escopo** | (nenhum) | — |
| **Anti-enumeração** | AUD-001/002 (falso negativo, não vazamento) | Correção resolve causa raiz — motorista/clicheria passam a ver provas que deveriam ver. Mensagem 404 genérica continua para "fora do scope" verdadeiro. |
| **Concorrência** | (nenhum — FOR UPDATE + 409 já tratado) | — |
| **Afeta C12** | AUD-005 (botões inline) | C12 visual independente; resolver AUD-005 antes do PR final do C12. AUD-001/002 já corrigidos antes do C12 ser merged. |
| **Bloqueados por divergência** | (nenhum) | — |
| **DEFERRED por violação de escopo** | (nenhum) | — |
| **REQUER NOVA ESCALAÇÃO** | AUD-005 | Listado em §10 deste documento — Mario decide entre (a) e (b). |

---

## 7. Plano de validação interna pós-correção (Seção 4.5 do prompt)

Critérios objetivos para cada achado, executados antes do PR.

| # | Validação | Como executar | Critério de "verde" |
|---|---|---|---|
| V1 | Verificação não-mod v3.0 | `git diff development -- backend/app/services/state_machine.py` | Output vazio |
| V2 | Verificação não-mod outras entregas | `git diff development -- backend/app/services/qrcode_service.py frontend/src/lib/services/identificacao-prova.ts frontend/src/lib/codigo-publico.ts frontend/src/app/(dashboard)/escanear/page.tsx frontend/src/app/(dashboard)/nova-prova/page.tsx frontend/src/app/(dashboard)/provas/[id]/page.tsx frontend/src/app/(dashboard)/provas/[id]/Timeline.tsx` | Output vazio |
| V3 | Verificação não-mod visual | `git diff development -- '**/*.css' '**/*.module.css' '**/*.scss'` | Output vazio |
| V4 | Suite Python | `.venv\Scripts\python -m pytest backend/tests/ -q` | 961+ passed (era 961+10 skipped); +≥6 novos (AUD-004); 0 falhas; 0 regressão |
| V5 | Suite v4 state_machine | `.venv\Scripts\python -m pytest backend/tests/state_machine/ -q` | 100% pass; cobertura ≥ 95% mantida |
| V6 | Suite access (RBAC) | `.venv\Scripts\python -m pytest backend/tests/access/ -q` | +2 novos testes (AUD-004 unit); pass 100% |
| V7 | Suite provas_api | `.venv\Scripts\python -m pytest backend/tests/test_provas_api.py backend/tests/test_provas_api_v4.py -q` | +≥4 novos testes (AUD-004 API); pass 100% |
| V8 | Enum 3 camadas equivalente | `.venv\Scripts\python -m pytest backend/tests/test_status_prova_enum_drift.py -q` | 3 pure-Python pass; 1 skipif (sem env) — sem regressão. Validar manualmente via MCP que `SELECT enumlabel` retorna 17. |
| V9 | Matriz canônica par a par | Existente via `test_rules_v4.py::test_total_de_entradas_eh_24` + cada `(rota, origem) → destino + ator` | 43 testes pass |
| V10 | Coexistência v3.0 ↔ v4.0 | MCP `SELECT rota, status, COUNT(*) FROM provas_digitais GROUP BY ...` | Distribuição sem cruzamento — idêntica ao baseline pré-correção |
| V11 | Contexto motorista 3 contextos | `test_contextos_v4.py` (6 testes) | Pass |
| V12 | Cancelamento transversal | `test_executar_cancelamento_*` em `test_machine_v4.py` | Pass |
| V13 | Reinício de ciclo preserva rota | `test_executar_reinicio_preserva_rota_e_incrementa_ciclo` | Pass |
| V14 | Concorrência FOR UPDATE | (existente — coberto pelo ADR-084; não re-rodar) | Aceito por análise estática (AUD-019 INFO) |
| V15 | Anti-enumeração | `validar_transicao_v4` mensagens — checar byte-a-byte | Mantidas conforme ADR-154 post-hoc (Opção B M-7) |
| V16 | RLS aplicada em produção | MCP `apply_migration` 015 + `SELECT polname, qual FROM pg_policies` | 3 policies atualizadas; `qual` contém `COM_MOTORISTA_ENTREGA_FINAL` para clicheria |
| V17 | RLS pós-uniformização EXISTS | MCP query nas policies | Padrão EXISTS em todas as 3 |
| V18 | `alembic upgrade head` clean | (em ambiente local) `alembic upgrade head; alembic downgrade -1` | Sem erro |
| V19 | `get_advisors` security | MCP `get_advisors --type=security` | Apenas os 2 pré-existentes (ADR-025 + ADR-027) |
| V20 | Tempo de transição < 1s (RNF-001) | Inspeção análise estática — `transicoes_validas_v4` O(1) | Mantido conforme análise existente |
| V21 | Frontend tsc + Vitest | `cd frontend; npx tsc --noEmit; npx vitest run` | tsc exit 0; 98+ Vitest pass |
| V22 | Decisões M-1..M-8 respeitadas | Inspeção visual de `DECISIONS.md` + apêndice ADR-154 | 9/9 ADRs presentes pós-correção (146-154) |
| V23 | `contrato-c12.md` viável | Inspeção visual — atualizar §2 se helper TS espelhar mudança no Python (nenhuma neste plano) | Sem mudança esperada — contrato fica intacto |

---

## 8. Plano de atualização de documentação (Seção 4.6 do prompt)

| Arquivo | O que adicionar |
|---|---|
| `CHANGELOG.md` | **Nova seção "v4.0 — Wave 3 — Componente 11 — Correções Pós-Auditoria (2026-05-13)"** antes da seção C11 original. Lista por ID corrigido com arquivo + tipo. Lista separada de DEFERRED com encaminhamento. Apêndice — não substitui a seção original. AUD-012 reformula narrativa "9 v3.0 → 14 v4.0". |
| `DECISIONS.md` | **ADR-154** (M-7 post-hoc) + **ADR-155** (decisão Mario sobre AUD-005, se (a)) + **ADR-156** (drift Python↔Postgres em CI — decisão técnica) + opcional **ADR-157** (benchmark deferred). Cada um no formato consistente dos ADRs 146-153. Apêndice — não substitui. |
| `CLAUDE.md` | Atualizar seção "Como adicionar uma nova página" → "Como adicionar um valor a `status_prova_enum`" se mudar (não muda neste plano — apenas ADR-154 documenta M-7). Adicionar nota curta no bloco "Máquina de Estados: coexistência v3.0 e v4.0" sobre RLS 015 paridade primária↔secundária. |
| `docs/wave3-v4-c11/audit-report.md` | **Apêndice "Status pós-correção"** com cada ID: `RESOLVIDO em <sha>` (corrigíveis) / `DEFERRED — encaminhado para <wave>` (se houver) / `BLOQUEADO POR DIVERGÊNCIA — <motivo>` (nenhum esperado) / `ESCALADO NOVAMENTE — <motivo>` (AUD-005 se decisão (b)). **NÃO editar corpo original.** |
| `docs/wave3-v4-c11/fix-plan.md` | **Seção "Resultado da Execução"** anexada no Gate 2 com diffs entre planejado e realizado. |
| `docs/wave3-v4-c11/contrato-c12.md` | Sem mudança esperada — nenhuma correção afeta o contrato. Se Mario optar (b) para AUD-005, adicionar seção "Botões inline na detail page entregues por sessão dedicada" referenciando. |
| `docs/wave3-v4-c11/fix-validation.md` | **Criar no Gate 2** com checklist (Seção 7 deste plano) + verificação por achado + auto-crítica. |

---

## 9. Pontos de escalação humana antes do Gate 2

### 9.1 AUD-W3C11-005 — Critério 15 do prompt original (botões inline na página de detalhe)

**Estado:** o C11 não entregou; documentação no `analysis.md §A.4` registra a deferral como aberta, aguardando decisão do Mario.

**Pergunta para o Mario:**

| Opção | Estratégia | Impacto desta sessão de correção |
|---|---|---|
| **(a)** Aceitar deferral | Botões inline ficam para "futuro pós-Wave 3" se necessário. Scanner em `/escanear` permanece como caminho canônico (RNF-002 ≤2s captura → assinatura). Criar ADR-155 documentando deferral + entrada no CHANGELOG. | Esta sessão fecha normalmente. C12 pode mergear normalmente após. |
| **(b)** Pedir nova sessão dedicada | Sessão separada entrega o modal com signature canvas (~150-200 LOC novos) + hook `useTransitionFromDetail` + lista dinâmica de transições. Bloqueia PR para `main` até entregar. | Esta sessão fecha com AUD-005 marcado como ESCALADO NOVAMENTE. Mario abre nova sessão. |
| **(c)** Outra alternativa | (qualquer outra interpretação que o Mario queira propor) | A definir conjuntamente. |

**Recomendação técnica:** Opção (a). Scanner já cumpre RNF-002. Botões inline adicionam um caminho UI alternativo, mas a UX canônica é via scanner (consistência com Waves 3 v3.0 + v4.0 C10 + C19). Mario decide.

**Não posso prosseguir para Gate 2 sem essa decisão.**

---

## 10. Entregável do Gate 1

- Branch: `wave3-v4-c11/fixes/plan` (criada a partir de `development` HEAD `4aaf806`).
- Commit pendente: `docs(wave3-v4/c11/fixes): plano de correção pós-auditoria` (será criado após este arquivo + commit dos artefatos do Gate 1).
- Sem mudança em código de produção. Sem migration aplicada.
- PR não aberto — espera-se autorização Gate 2.

---

**Fim do Gate 1.** Aguardando:
1. Resposta humana sobre AUD-W3C11-005 (Opção a/b/c).
2. String `AUTORIZADO GATE 2 — CORREÇÃO C11 v4.0` para iniciar execução.
