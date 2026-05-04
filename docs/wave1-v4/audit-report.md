# Relatório de Auditoria · Wave 1 v4.0 · Componente 05 (atualização v4.0)

**Auditor:** Sessão de auditoria sênior independente (read-only)
**Data:** 2026-04-30
**Branch auditada:** `development` (estado pós Wave 1 v4.0 + Audit Fixes)
**SHAs auditados:** `c1847a8` (RLS+JSON) → `d4f4801` (backend) → `81ec1cc` (frontend) → `e45e17a` (testes+script) → `a094819` (closeout) → `ac3be70` (audit fixes H/M) → `3fb6e93` (apêndice docs)
**Branch da auditoria:** `wave1-v4/audit` (sem merge)
**Veredito final:** **APROVADO COM CORREÇÕES** (3 MEDIUM bloqueantes — todas em documentação/testes/cobertura, não em código de produto).

---

## Sumário Executivo

A Wave 1 v4.0 cumpriu a **espinha dorsal** do prompt: o JSON SSoT vive em `shared/access-matrix.json`, é lido fielmente pelas duas linguagens, e a RLS no banco real referencia helpers em `app_private.*` que produzem comportamento equivalente para os 4 perfis (validado via impersonação SQL sob role `authenticated`). As 12 regras × 4 perfis = 48 células estão cobertas, com paridade de decisão entre Python e o JSON. Os 2 HIGH e 5 MEDIUM identificados pela auditoria interna posterior (commit `ac3be70`) foram efetivamente corrigidos. Refactor coordenado limpou `Depends(get_admin_user)` de 17 endpoints sem regressão (757 → 761 testes passando).

A auditoria sênior confirmou **0 achados CRITICAL** próprios. Identificou **3 achados MEDIUM** novos — todos no perímetro de documentação/teste/cobertura — e mais alguns LOW/INFO. **Nenhum dos achados MEDIUM é regressão funcional**: dois dão risco de re-introdução de bugs já corrigidos (drift de docs e cobertura incompleta de teste), o terceiro é uma ambiguidade semântica na Matriz que pode causar drift no futuro. Não bloqueiam a Wave 2 v4.0 desde que registrados como follow-up obrigatório.

| Severidade | Total | IDs |
|---|---|---|
| CRÍTICO | 0 | — |
| ALTO | 0 | — |
| MÉDIO | 6 | AUD-W1V4-001 .. 006 |
| BAIXO | 7 | AUD-W1V4-101 .. 107 |
| INFO | 4 | AUD-W1V4-201 .. 204 |

**Bloqueio para Wave 2 v4.0:** nenhum. Recomendação: corrigir AUD-W1V4-001/002/003 antes do próximo merge para evitar drift acumulado.

---

## Fase 1 — Verificação de Completude

### 1.1 Artefatos lidos (Seções 2.1 a 2.4 do prompt)

| Tipo | Caminho | Status |
|---|---|---|
| Contexto vivo | `CLAUDE.md` | ✅ Lido integral. Inclui seção "RBAC: como adicionar uma nova página" (linhas 367-431). |
| Contexto vivo | `DECISIONS.md` | ✅ Lido (linhas 4034-4288 — Wave 1 v4.0 + Audit Fixes). 7 ADRs (D-1..D-7). |
| Contexto vivo | `CHANGELOG.md` | ✅ Lido (linhas 7962-8214). 2 seções da wave. Histórico anterior preservado (Waves 0-6 intactos). |
| Contexto vivo | `docs/db/schema.sql` | ✅ Conferido com `pg_policies` ao vivo — 12 policies batem. |
| Contexto vivo | `backend/migrations/rls/{009..012}.sql` | ✅ Lidos integral. |
| Contexto vivo | `docs/wave1-v4/analysis.md` | ✅ Lido integral (1.111 linhas, incluindo seção "Execução" + "Audit Fixes"). |
| Produto v4.0 | `RequisitosProvasDigitais_v4_0.docx` | ⚠️ **Lido por intermediário.** Os extracts em `docs/wave1-v4/_extracted/` foram removidos no closeout do Gate 2. Confiei em (a) citações textuais da Seção 3 do `analysis.md`, (b) estrutura codificada em `tests/access/test_matrix_structure.py::TestMatrixSemanticInvariants`, (c) `_clicheria_divergence_note` no JSON. Registrado como AUD-W1V4-204 INFO. |
| Produto v4.0 | `BACKLOG_RastreioProvasDigitais_v4_0.docx` | ⚠️ Mesma situação. |
| Produto v3.0 | `DAT_RastreioProvasDigitais_v3_0.docx` | ⚠️ Mesma situação. |
| Produto v4.0 | `UML_RastreioProvasDigitais_v4_0.drawio` | ⏭️ Não lido. Conforme analysis Seção 0.2 (item 8), conteúdo de classes/estados não é crítico para a wave de RBAC. Reservado para Waves 2/3 v4.0. |
| Código-fonte | `shared/access-matrix.json` | ✅ |
| Código-fonte | `frontend/src/lib/access-matrix.ts` + `lib/hooks/use-authorization.ts` + `components/Restricted.tsx` + `components/AuthToast.tsx` + `lib/supabase/middleware.ts` + `middleware.ts` + `hooks/useGlobalShortcuts.ts` + `hooks/useCurrentUser.ts` | ✅ Todos lidos integral. |
| Código-fonte | `backend/app/access/{__init__,matrix,enforce,scopes,guards}.py` | ✅ Todos lidos integral. |
| Código-fonte | `backend/migrations/rls/009..012` | ✅ |
| Testes | `backend/tests/access/*.py` (5 arquivos + `__init__.py`) | ✅ Todos lidos integral. |
| Script | `scripts/verify_rbac_equivalence.py` | ✅ Lido integral (309 linhas). |
| Histórico Git | 8 commits (`1e086b3` analysis → `3fb6e93` apêndice docs) | ✅ Inspeção via `git log` + `git show` amostral. |

### 1.2 Critérios de aceitação do Componente 05 (atualização v4.0)

> Os "14 critérios da Seção 5.3 do prompt da execução" não estão materialmente acessíveis nesta sessão (extracts removidos). Substituí por uma checagem de **invariantes da analysis.md Seção 9 + DoD da seção 0.4** + elementos materialmente verificáveis no repo.

| # | Critério (extraído da analysis Seção 9 + 8) | Status | Evidência |
|---|---|---|---|
| 1 | SSoT única para 4 camadas | ✅ | `shared/access-matrix.json` é importado por TS e Python; RLS espelha via `app_private.current_user_*`. |
| 2 | Matriz cobre as 13 linhas da Seção 6 do Requisitos v4.0 | ✅ | 12 keys em `EXPECTED_KEYS` (test_matrix_structure.py:28-41). Visualização+Timeline unificadas em `provas.detail` conforme E.3 da analysis. |
| 3 | 4 perfis com decisão para cada regra | ✅ | `test_every_rule_covers_4_profiles` (test_matrix_structure.py:59) — passa em prod. |
| 4 | Middleware reescrito com gating por perfil | ✅ | `frontend/src/lib/supabase/middleware.ts` lido integral; lookup de perfil + LRU 30s + redirect 302 + cookie. |
| 5 | Hook `useAuthorization` consumível em pages | ✅ | `frontend/src/lib/hooks/use-authorization.ts` lido integral; consumido em 5 pages + 2 componentes. |
| 6 | Refactor coordenado das chamadas ad-hoc | ✅ | `Depends(get_admin_user)` removido de **17 endpoints** (verificado via grep). Substituído por `Depends(access_required("<rule_key>"))`. |
| 7 | Migrations RLS 009-012 idempotentes | ✅ | Todas têm DROP IF EXISTS + CREATE. RLS 010-012 contêm cabeçalho com nota de supersedência. |
| 8 | Testes específicos da camada de acesso | ✅ | `tests/access/`: 40 testes em 5 arquivos (test_matrix_structure 19, test_resolve_profile 7, test_enforce_access_for 6, test_scope_filter_for 7, test_matrix_rls_equivalence 1). |
| 9 | Equivalência entre camadas validada | ⚠️ Parcial | `test_matrix_rls_equivalence.py` valida apenas Python ↔ JSON (1 teste, 48 células). RLS validado via script standalone `scripts/verify_rbac_equivalence.py` (executado contra produção). Cobertura RLS: só `provas_digitais`. **Achado AUD-W1V4-002.** |
| 10 | 0 regressão em testes existentes | ✅ | 757 → 761 testes (+36 novos -3 require_role removidos +4 M-2). 0 regressão declarada no CHANGELOG; tests rodam com mock_db existente sem alteração graças à decisão D-5. |
| 11 | Página inicial por perfil | ✅ | `home_by_profile` em JSON; D-4 documenta. Motorista → `/escanear`; demais → `/dashboard`. |
| 12 | Toast de redirect | ✅ | `AuthToast.tsx` + cookie `auth-toast` setado pelo middleware. role="status", aria-live="polite", auto-dismiss 6s. |
| 13 | Doc operacional (CLAUDE.md "como adicionar página") | ✅ presente, ⚠️ desatualizada | Linhas 367-431; conteúdo prático com 7 passos, mas snippet do passo 4 mostra padrão pre-M-1 (`if (!auth.loading && !auth.hasAccess)`) que reintroduziria flash de UI. **Achado AUD-W1V4-001.** |
| 14 | Decisões registradas em DECISIONS.md | ✅ | 7 ADRs (D-1..D-7) cobrindo SSoT, divergência Clicheria, padrão SQL, redirect, factory, FAIL FAST, trailing slash. |

### 1.3 Definition of Done global (10 itens do BACKLOG)

> Os 10 itens da DoD literal do BACKLOG não foram acessados textualmente nesta sessão. Substituí por DoD funcional verificável.

| # | DoD | Status | Evidência |
|---|---|---|---|
| 1 | Código revisado e merged em `development` | ✅ | 8 commits em `development` entre `1e086b3` e `3fb6e93`. |
| 2 | Testes passando | ✅ | 761 testes (CHANGELOG line 8183). Não rodei localmente; confiei no relato. |
| 3 | Lint+typecheck limpos | ✅ | CHANGELOG line 8184: `npx tsc --noEmit + next lint + next build` limpos. `ruff check` limpo. |
| 4 | Migrations aplicadas em prod | ✅ | `rls_009..012` no histórico de migrations Supabase (CHANGELOG line 8079-8084 + confirmado via MCP). |
| 5 | Advisor limpo | ✅ | MCP `get_advisors`: 1 INFO `rls_enabled_no_policy` em `alembic_version` (intencional ADR-025) + 1 WARN `auth_leaked_password_protection` (WONTFIX ADR-027). Nenhum advisor novo. |
| 6 | Documentação atualizada (CLAUDE/DECISIONS/CHANGELOG) | ✅ | Verificado item por item. |
| 7 | ADRs novos registrados | ✅ | D-1..D-7 (7 ADRs). |
| 8 | Histórico anterior preservado | ✅ | Verificado: CHANGELOG mantém linhas 1-7961 intactas; DECISIONS mantém ADRs ≤ 4033 intactos; CLAUDE mantém estrutura prévia. |
| 9 | Smoke validação real | ✅ | `verify_rbac_equivalence.py` em prod: SUCESSO (admin 16/16, vendedor 0, motorista 0, clicheria 2). Smoke preview: redirect anônimo OK. |
| 10 | Sem alteração fora do escopo | ✅ | Cloudflare intocado (1 bucket pré-existente, 0 Workers, 0 KV). Schema de `auth.*` Supabase intacto (raw_app_meta_data idêntico ao Gate 1). |

### 1.4 Cobertura da Matriz de Acesso (12 regras × 4 perfis = 48 células)

> A Matriz literal do Requisitos tem 13 linhas; consolidação E.3 unificou Visualização+Timeline em `provas.detail` (semântica idêntica). Cobertura 13/13 mantida.

| # | Linha da Matriz | Key Wave 1 v4.0 | studio_admin | vendedor | motorista | clicheria | Coberto Python | Coberto RLS | Coberto teste |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Login | `login` | ● | ● | ● | ● | ✅ | n/a (rota pública) | ✅ |
| 2 | Dashboard | `dashboard` | ● | ● | ● | ● | ✅ | aplicado via scoping em queries de `provas` | ✅ |
| 3 | Listagem de Provas | `provas.list` | ● | ◐ self | ◐ trânsito | ◐ status_clicheria⚠ | ✅ | ✅ pol_provas_select | ✅ |
| 4 | Visualização de Prova (detalhe) | `provas.detail` (= 5) | ● | ◐ self | ◐ trânsito | ◐ status_clicheria⚠ | ✅ | ✅ pol_provas_select + pol_etiquetas_select + pol_movimentacoes_select | ✅ |
| 5 | Timeline da Prova | (consolidada em `provas.detail`) | — | — | — | — | — | — | ✅ via inheritance |
| 6 | Criar Prova | `provas.create` | ● | ○ | ○ | ○ | ✅ | ✅ pol_provas_insert (admin only) | ✅ |
| 7 | Escanear QR Code | `scanner` | ● | ● | ● | ● | ✅ | n/a (universal) | ✅ |
| 8 | Cadastro de Usuários | `usuarios` | ● | ○ | ○ | ○ | ✅ | ✅ pol_usuarios_{insert,update} | ✅ |
| 9 | Relatórios | `relatorios` | ● | ○ | ○ | ○ | ✅ | ✅ via service_role + enforce | ✅ |
| 10 | Configurações | `configuracoes` | ● | ○ | ○ | ○ | ✅ | ✅ pol_config_{select,update} | ✅ |
| 11 | Log de Auditoria | `auditoria` | ● | ○ | ○ | ○ | ✅ | ✅ pol_audit_select + REVOKE GRANT (RLS 008) | ✅ |
| 12 | Reiniciar Ciclo | `provas.restart` | ● | ○ | ○ | ○ | ✅ | ✅ via pol_provas_update + pol_movimentacoes_insert | ✅ |
| 13 | Cancelar Prova | `provas.cancel` | ● | ○ | ○ | ○ | ✅ | ✅ idem | ✅ |

⚠ **Divergência conhecida e documentada (D-2 + AUD-W1V4-201):** Matriz literal v4.0 Seção 6 diz Clicheria=`●` em #3/#4. Implementação manteve `◐ status_clicheria` (comportamento v3.0). Registrado como follow-up obrigatório.

**Cobertura final: 13/13 linhas mapeadas; 48/48 células decididas; 47/48 alinhadas literalmente com a Matriz** (1 célula divergente assumida deliberadamente).

### 1.5 Documentação atualizada

| Arquivo | Item | Status | Linhas |
|---|---|---|---|
| `CHANGELOG.md` | Seção "v4.0 — Wave 1 — Componente 05" | ✅ | 7962-8104 |
| `CHANGELOG.md` | Seção "Audit Fixes (pos-implementacao)" | ✅ | 8106-8214 |
| `CHANGELOG.md` | Histórico anterior preservado | ✅ | 1-7961 intactas |
| `DECISIONS.md` | D-1 SSoT JSON | ✅ | 4040-4068 |
| `DECISIONS.md` | D-2 Clicheria PARCIAL | ✅ | 4069-4105 |
| `DECISIONS.md` | D-3 EXISTS vs jwt | ✅ | 4106-4143 |
| `DECISIONS.md` | D-4 home_by_profile | ✅ | 4144-4170 |
| `DECISIONS.md` | D-5 access_required factory | ✅ | 4171-4198 |
| `DECISIONS.md` | D-6 FAIL FAST runtime | ✅ | 4200-4245 |
| `DECISIONS.md` | D-7 trailing slash | ✅ | 4247-4288 |
| `CLAUDE.md` | Seção "RBAC: como adicionar uma nova página" | ✅ presente, ⚠ desatualizada | 367-431 (snippet linha 400-403 mostra padrão pre-M-1 — vide AUD-W1V4-001) |
| `CLAUDE.md` | Tabela de waves | ✅ | linhas 25-31 (entradas Wave 1 v4.0 RBAC + Wave 1 v4.0 Audit Fixes) |
| `CLAUDE.md` | Atalhos `g a`/`g r` admin-only | ✅ | linhas 327-347 (atualizado p/ Wave 6 + 1 v4.0) |
| `docs/wave1-v4/analysis.md` | Seção "Execução" anexa | ✅ | 901-1037 (E.1 a E.10) |
| `docs/wave1-v4/analysis.md` | Seção "Auditoria pós-implementação" | ✅ | 1039-1110 (A.1 a A.4) |
| `docs/wave1-v4/_extracted/*.md` | Extracts dos docx | ⚠ removidos pós-Gate 1 | AUD-W1V4-204 |

### 1.6 Migrations RLS versionadas

| Arquivo | Aplicado em prod? | Idempotente? | Estado final atribuível? |
|---|---|---|---|
| `001..008` | sim (preservados) | sim | sim |
| `009_helpers_v4.sql` | sim | sim | superseded por 012 (cabeçalho avisa) |
| `010_rebase_rls_v4.sql` | sim | sim | superseded por 012 |
| `011_etiquetas_select_motorista_clicheria.sql` | sim | sim | superseded por 012 |
| `012_move_helpers_to_app_private.sql` | sim | sim | **estado final** |

**Verificação ao vivo (MCP `pg_policies`):** 12 policies referenciam `app_private.current_user_*`. 0 referências a `public.current_user_*`. ✅

**Verificação `pg_proc` (MCP):** 3 funções `app_private.current_user_{is_admin,setor,id}` presentes; 0 funções homônimas em `public`. ✅

### 1.7 Refactor coordenado completo

Grep de padrões antigos:

| Padrão | Resultado | Comentário |
|---|---|---|
| `Depends(get_admin_user)` | 0 ocorrências em endpoints novos. 1 menção em docstring de `deps.py:14`. 0 endpoint usa em prod. | ✅ |
| `require_role(` | 0 ocorrências (somente comentário em `deps.py:18` documentando remoção). | ✅ |
| `if (!user.is_admin)` ou `user?.is_admin` em `frontend/src/app/**.tsx` | 0 ocorrências em pages/components fora de `useAuthorization`/`useCurrentUser`/`useGlobalShortcuts`. | ✅ |
| `user.setor === "..."` em frontend pages | 0 ocorrências. | ✅ |
| `_scoping_filter` fora de `provas.py` | 0 (só dentro de `provas.py`, e mesmo lá, virou shim que delega). | ⚠ tech debt L-2 já registrado |
| Uso de `get_admin_user` em backend | 1 endpoint legacy (`users.py:GET /{id}` linha 200, invariante "self ou admin"). Documentado no CHANGELOG. | ✅ |

---

## Fase 2 — Auditoria Qualitativa

### 2.1 Achados de Segurança

#### AUD-W1V4-101 [BAIXO] — TRUNCATE permanece concedido a `authenticated`/`anon` em todas as tabelas (incluindo `audit_logs`)

**Evidência:** consulta `information_schema.role_table_grants` retornou TRUNCATE GRANT em `audit_logs`, `usuarios`, `provas_digitais`, `movimentacoes`, `etiquetas`, `configuracoes_sistema`, `alembic_version` para ambos `authenticated` e `anon`. RLS 008 (Wave 6) revogou apenas INSERT/UPDATE/DELETE em `audit_logs`.

**Impacto teórico:** TRUNCATE em PostgreSQL **bypassa RLS**. O trigger `trg_audit_logs_imutavel` é BEFORE UPDATE OR DELETE, não cobre TRUNCATE. Logo, um cliente `authenticated` que conseguir executar `TRUNCATE TABLE public.audit_logs` poderia apagar todos os logs sem deixar trace, violando RNF-005.

**Por que é BAIXO e não HIGH:**
1. **Não é regressão da Wave 1 v4.0** — pré-existe desde Wave 0. RLS 008 (Wave 6) já endereçou o vetor principal (DML).
2. **PostgREST não expõe TRUNCATE** como verbo HTTP. `/rest/v1/<tabela>` aceita GET/POST/PATCH/DELETE; nenhum verbo dispara TRUNCATE.
3. **Conexão direta via psql** com role `authenticated` não é arquitetura de exploração trivial — exigiria a `anon_key` + bypass do PostgREST (não trivial em Supabase managed).

**Recomendação:** registrar como follow-up RNF-005:
```sql
REVOKE TRUNCATE ON public.audit_logs FROM anon, authenticated;
```
**Não bloqueia esta auditoria.** Atribui-se à Wave 6 ou a uma migration de hardening dedicada.

#### AUD-W1V4-102 [BAIXO] — Pass-through defensivo em `getRuleForPath = null`

**Evidência:** `frontend/src/lib/supabase/middleware.ts:208-210`:
```typescript
const rule = getRuleForPath(pathname);
if (rule === null) {
  return supabaseResponse;  // pass-through defensivo
}
```

**Impacto:** Nova rota criada em `app/(dashboard)/<x>/page.tsx` sem entrada na Matriz fica acessível por qualquer usuário autenticado. Documentado no comentário linha 27-29 do mesmo arquivo: "Rule null (path nao mapeado): pass-through (defensivo: novas rotas nao quebram navegacao ate serem adicionadas a Matriz)".

**Trade-off avaliado:** alternativa "deny-by-default" quebraria pages de placeholder e prototipagem. A decisão atual prioriza ergonomia de desenvolvimento sobre defesa em profundidade automática.

**Recomendação:** complementar a documentação no CLAUDE.md (passo 1 da seção RBAC) destacando que **omitir entrada na Matriz = pass-through silencioso** — desenvolvedor precisa SEMPRE adicionar entrada (mesmo que `full` para todos os 4) ao criar rota nova. Considerar regra de CI que falhe se houver rota em `app/(dashboard)/` sem entrada na Matriz.

#### AUD-W1V4-103 [BAIXO] — Cache LRU 30s no middleware atrasa revogação de admin

**Evidência:** `frontend/src/lib/supabase/middleware.ts:54-58`:
```typescript
const PROFILE_CACHE = new Map<string, { profile: ProfileSnapshot | null; expiresAt: number }>();
const PROFILE_TTL_MS = 30_000;
```

**Impacto:** se admin é desativado (ou tem `is_admin` flipado para `false`) durante uma sessão ativa, o middleware continua deixando passar requisições por até 30 segundos. Documentado em DECISIONS D-7 do projeto + analysis Seção 11 (R-7 e R-11).

**Mitigações já presentes:**
- Backend valida `ativo=true` em cada request via `get_current_user` (defesa em profundidade não quebra).
- RLS no banco usa `app_private.current_user_is_admin()` — sempre fresh (não cacheia).
- TTL curto (30s) limita janela.

**Recomendação:** ainda assim documentar explicitamente no CLAUDE.md que **alterar `is_admin`/`setor`/`ativo` em produção tem latência de até 30s no middleware**. Considera adicionar invalidação ativa do cache em PATCH/DELETE de `/users/{id}` (publicar via channel Realtime ou similar).

#### AUD-W1V4-104 [BAIXO] — `useCurrentUser` não valida `setor` em runtime

**Evidência:** `frontend/src/hooks/useCurrentUser.ts:42-43`:
```typescript
const user = await apiFetch<UserInfo>("/api/v1/users/me", { token });
setState({ user, loading: false });
```

`apiFetch<UserInfo>` faz cast TypeScript sem verificação runtime. Se o backend retornar um setor fora do union literal (`"STUDIO"|"VENDEDOR"|"MOTORISTA"|"CLICHERIA"`), o cliente continua e a Matriz `resolveProfile` retorna `null` → "negado em tudo" silencioso. Em desenvolvimento isso é difícil de diagnosticar.

**Recomendação:** adicionar validação runtime simples (zod ou guard manual) em `useCurrentUser`. BAIXO porque o backend é fonte confiável e a falha modal é "deny" (segura).

#### Vazamento de mensagens de erro

`enforce_access_for` retorna detail "Acesso nao autorizado para seu perfil" — não revela qual perfil seria autorizado. ✅
`Restricted` exibe mensagens contextuais por `ruleKey` mas todas dizem "restrito ao perfil 3Studio". Não permite enumeração de qual perfil tem acesso a quê. ✅

#### Race conditions na sessão

Documentadas em DECISIONS D-3/D-7 + analysis R-7/R-11. JWT antigo continua valendo até expirar — comportamento padrão Supabase, aceitável.

#### Defesa em profundidade efetiva

**Cenário 1: middleware desativado.** Backend `enforce_access_for` continua bloqueando 403, e RLS continua filtrando dados. ✅
**Cenário 2: backend bypassed.** Cliente Supabase direto (anon key) cai na RLS — testado por impersonação SQL: vendedor mariosouza vê 14 provas (suas), 0 audit_logs, 0 configurações, 1 usuário (self). ✅
**Cenário 3: RLS desativada.** Backend `enforce_access_for` bloqueia páginas admin-only com 403; backend usa `service_role` + `scope_filter_for` para queries de listagem (defesa SUPERIOR). Em teoria funciona, mas perde a defesa INFERIOR. Backend tem isso documentado.

**As duas camadas (middleware/page-level + RLS) são realmente independentes:** middleware lê `usuarios.{is_admin,setor,ativo}` via createServerClient; RLS lê via `app_private.current_user_*` SECURITY DEFINER. Compartilham apenas a tabela-fonte (`usuarios`), não código.

#### `auth.jwt() ->> 'setor'` ausente

JWT do Supabase não tem `setor`. Decisão D-3 mantém padrão atual (EXISTS contra `usuarios`). ✅

#### `security definer` em funções

3 funções `app_private.current_user_*` são SECURITY DEFINER. Owner é `postgres`. `SET search_path = ''` aplicado (ADR-024). REVOKE FROM PUBLIC + GRANT TO authenticated, service_role. Schema `app_private` não exposto via PostgREST (db-schemas inclui apenas `public`).

**Verificado via MCP:** schema `app_private` não tem GRANT EXECUTE para `anon` (só `authenticated` + `service_role`). ✅

### 2.2 Achados de Correção (Bugs)

#### AUD-W1V4-001 [MEDIUM] — CLAUDE.md (linhas 400-403) documenta padrão pre-M-1 que reintroduziria o bug do flash de UI

**Evidência:** `CLAUDE.md` linhas 398-404:
```tsx
4. **No frontend**, na pagina:
   ```tsx
   const auth = useAuthorization("nova.chave");
   if (!auth.loading && !auth.hasAccess) {
     return <Restricted ruleKey="nova.chave" profile={auth.profile} />;
   }
   ```
```

**Bug:** este snippet é **exatamente o padrão que M-1 (audit fixes) corrigiu** em 5 pages. A correção foi para:
```tsx
if (auth.loading) return null;
if (!auth.hasAccess) return <Restricted ... />;
```

**Impacto:** desenvolvedor que segue o guia oficial reintroduz o bug do flash de UI proibida (~50-200ms de controles admin renderizando antes do guard). Não é regressão atual mas drift de documentação que **garante regressão futura**.

**Recomendação (não-bloqueante mas importante):** atualizar o snippet no CLAUDE.md para o padrão pós-M-1, citando explicitamente o ID M-1 do CHANGELOG.

#### AUD-W1V4-002 [MEDIUM] — Cobertura RLS no script de equivalência limitada a `provas_digitais`

**Evidência:** `scripts/verify_rbac_equivalence.py:128-137`:
```python
async def count_visible_provas(auth_uid: uuid.UUID) -> int:
    ...
    row = await c.fetchrow("SELECT count(*)::int AS n FROM public.provas_digitais")
```

A etapa [3/4] do script só conta `provas_digitais`. As tabelas `movimentacoes`, `etiquetas`, `audit_logs`, `configuracoes_sistema`, `usuarios` não são contadas via SQL impersonado.

**Impacto:** lacuna na validação 3-camadas. RLS 011 (etiquetas para Motorista/Clicheria) é exatamente o tipo de mudança que o script deveria validar — e não valida. Marcado como `M-6` follow-up no CHANGELOG (linha 8195).

**Recomendação:** estender o script para 6 tabelas (1 query por tabela × 4 perfis = 24 counts). Implementação trivial, aumenta significativamente o sinal do script.

**Por que MEDIUM e não BAIXO:** o script é a única validação automatizada da camada RLS contra a Matriz. Ele declara "valida 3 camadas" mas valida 1+1+1 fração. Risco real de drift em RLS 011 não detectado.

#### AUD-W1V4-003 [MEDIUM] — Etapa [4/4] do script de equivalência tem assertions frouxas para FULL/PARCIAL

**Evidência:** `scripts/verify_rbac_equivalence.py:257-264` (após M-5 do audit fixes):
```python
for profile, rls_count in rls_counts_by_profile.items():
    decision = evaluate(rule_provas_list, users_by_profile[profile])
    # Hoje nenhum dos 4 perfis e NEGADO em provas.list. Mas se virar:
    if decision.acesso == Acesso.NEGADO and rls_count != 0:
        failures.append(...)
```

**Bug:** a única branch que produz `failure` é `NEGADO + count > 0`. Cenários de drift que NÃO são detectados:
1. Python diz `FULL` mas RLS retorna 0 (drift!) → não falha (admin com 0 provas é cenário válido).
2. Python diz `PARCIAL self_vendedor` mas RLS retorna fewer linhas que esperado → não falha.
3. Python diz `PARCIAL` mas RLS retorna mais linhas que `count_provas_motorista_expected()` → não falha (script não compara).

A etapa [3/4] (linhas 208-215) tem comparações mais fortes (`admin_seen != admin_total`, etc.), mas a etapa [4/4] (que é o nome explícito "validando equivalencia Matriz <-> Python para 48 celulas") foca apenas no caso negativo.

A linha 269-280 itera 44 outras células e só valida que `decision.acesso ∈ {FULL, PARCIAL, NEGADO}` — isto é tautológico (Acesso é Enum). O comentário linha 226-227 diz "valida apenas que a Matriz Python classifica os 4 perfis (FULL/PARCIAL/NEGADO) sem inconsistencia" — isto é mais fraco que o nome da etapa sugere.

**Impacto:** o script pode reportar SUCESSO mesmo se a Matriz divergir do RLS para `provas.detail`, `movimentacoes`, `etiquetas`, etc. M-5 do audit fixes corrigiu o "teatro" puro; mas a cobertura da camada [4/4] ainda é menor do que o nome promete.

**Recomendação:** combinar AUD-W1V4-002 e -003 em uma extensão única do script: para cada `(rule_key, profile, table)` em uma matriz expandida, validar count RLS == count Python esperado. Aproximadamente 12 regras × 4 perfis × 6 tabelas = 288 cells validáveis (muitas são n/a — só `provas_digitais`/`movimentacoes`/`etiquetas` têm escopo PARCIAL).

#### AUD-W1V4-105 [BAIXO] — Endpoints de detalhe de prova usam `scope_filter_for("provas.list", user)` em vez de `provas.detail`

**Evidência:** `backend/app/api/v1/provas.py:885` (`_carregar_prova_com_scoping`) → chama `_scoping_filter(user)` (linha 661-673) → delega `scope_filter_for("provas.list", user)`.

A Matriz codifica `provas.list` e `provas.detail` como duas regras distintas. Por convenção, endpoints `GET /{id}` deveriam usar `provas.detail`. Hoje a semântica é IDÊNTICA (test_provas_detail_inherits_provas_list_scopes em test_matrix_structure.py), então não há bug funcional, mas:

1. Quando alguém alterar a regra `provas.detail` na Matriz (ex.: para implementar a divergência D-2 só no detalhe e não na lista), o backend não respeitará a mudança.
2. Documentação fica enganosa.

**Recomendação:** trocar para `scope_filter_for("provas.detail", user)` em `_carregar_prova_com_scoping`. Trivial.

#### Outros cenários reproduzidos mentalmente: nenhum bug adicional encontrado

- **Vendedor com 0 provas:** vê `[]`. Frontend não quebra. ✅
- **Página inicial inexistente:** `home_by_profile` cobre os 4 perfis; `homeForProfile(null)` → `/login`. ✅
- **Redirect loop:** se `/dashboard` for negado para um perfil (cenário só possível se a Matriz mudar), o middleware redirecionaria em loop. Hoje os 4 perfis têm `dashboard=full`. INFO AUD-W1V4-201.
- **JWT expirado:** Supabase auto-renew via `updateSession`. Sem token → redirect `/login`. ✅
- **Cookie de sessão ausente em rota pública vs protegida:** `isPublicPath` cobre `/login`, `/_next`, `/favicon.ico`, `/api/health`. ✅
- **Idempotência das migrations RLS:** todas usam `DROP IF EXISTS + CREATE` ou `CREATE OR REPLACE`. RLS 012 inclui `DROP FUNCTION IF EXISTS public.current_user_*` — re-aplicável após cleanup. ✅
- **Comportamento do `useAuthorization` em SSR:** retorna `loading=true` durante o initial render servidor (sem user). Pages com `if (auth.loading) return null;` → renderiza nothing. Sem flash. ✅ (M-1)

### 2.3 Achados de Regressões nas Waves 0–6 da v3.0

Testei mentalmente os fluxos críticos e procurei assinaturas de bugs:

#### Componente 06 (Criar Prova) — Wave 2

`POST /upload-url` e `POST /` agora usam `Depends(access_required("provas.create"))`. Antes eram `Depends(get_admin_user)` — mesma decisão (admin only), mesmo retorno 403. ✅ Sem regressão.

#### Componente 07 (Listagem) — Wave 2

`GET /` ainda usa `Depends(get_current_user)` + `_scoping_filter` que delega `scope_filter_for("provas.list", user)`. Vendedor continua vendo só suas, motorista continua vendo COM_MOTORISTA, clicheria os 3 status. ✅ Sem regressão.

#### Componente 08 (Detalhe + Etiqueta + QR) — Wave 2

`GET /{id}`, `/imagem-url`, `/movimentacoes`, `/etiqueta.pdf`, `/qr-code.png` usam `_carregar_prova_com_scoping` → `_scoping_filter` → `scope_filter_for("provas.list", user)`. Ver AUD-W1V4-105 (uso da chave "errada" semanticamente). Funcionalmente equivalente ao v3.0. ✅

#### Componente 09 (Configurações) — Wave 2

3 endpoints migrados de `Depends(get_admin_user)` para `access_required("configuracoes")`. Mesma semântica. ✅

#### Componentes 10/11 (Scanner + Transições) — Wave 3

`POST /scan` e `POST /{id}/transicoes` continuam com `Depends(get_current_user)` + state machine. State machine intacto (B6/B12 da analysis Seção 8.1: "Manter intacto"). Cancelamento (RN-005) preservado em `state_machine.py`. ✅

#### Componentes 12/13/14 (Timeline + Cancelar + Reiniciar) — Wave 3

- Timeline: render frontend, sem checagem RBAC própria — cobertura via `provas.detail`. ✅
- `POST /{id}/cancelar`: usa `access_required("provas.cancel")`. Antes era `get_admin_user`. ✅
- `POST /{id}/reiniciar-ciclo`: idem com `provas.restart`. ✅

#### Componente 15 (Dashboard) — Wave 4

`GET /dashboard` usa `Depends(get_current_user)` + scoping nos counts. Universal na Matriz. ✅ Sem mudança.

#### Componente 16/17 (Relatórios + Atalhos) — Wave 5

- `GET /reports` e `GET /reports/export`: 2 endpoints migrados para `access_required("relatorios")`. ✅
- `useGlobalShortcuts`: agora deriva da Matriz (`evaluateRule`). `g r`/`g a` continuam admin-only por construção. Atalho `g s`/`g p` universais. ✅
- Frontend `/relatorios`: guard PROMOVIDO de reativo (parsing de erro) para proativo (`useAuthorization`). Behavior mais robusto. ✅

#### Componente 18 (Auditoria) — Wave 6

3 endpoints migrados para `access_required("auditoria")`. Frontend usa `useAuthorization("auditoria")` + `<Restricted />`. Comportamento idêntico ao guard ad-hoc anterior. ✅

#### Cenários potenciais de regressão checados e descartados

- **Regra de negócio disfarçada de RBAC:** B12 da analysis explicitamente preserva RN-010 em `users.py` (admin não pode remover próprio is_admin) — não substituiu por chave da Matriz. ✅
- **State machine vs Matriz:** transições continuam validadas por `validar_transicao()` independente de RBAC. ✅
- **`vendedor` com `localizacao=null`:** modelo permite, e a Matriz não depende de localização — só de setor. ✅
- **Endpoint `/users/{id}`:** mantém check inline `if not is_admin and current_user.id != user.id: 403`. Não é célula da Matriz, é invariante. ✅

**Veredito:** 0 regressão funcional detectada. Os 757 testes Wave 0-6 continuam passando (declarado, não rerun nesta sessão).

### 2.4 Achados de Performance

#### Cache LRU 30s (já discutido em AUD-W1V4-103)

Documentado em DECISIONS R-7. Trade-off explícito.

#### EXISTS contra `usuarios` em todas as policies

Cada policy faz lookup contra `usuarios` por `auth_uid`. Helper `app_private.current_user_*()` é STABLE — Postgres cacheia o resultado por query. `usuarios.auth_uid` é UNIQUE → index hit O(log n). Aceitável para volume atual (4 usuários, 16 provas). Documentado em DECISIONS D-3.

#### Advisor de performance (MCP `get_advisors`)

12 INFOs de `unused_index` (alguns índices novos da Wave 5/6 ainda não exercitados). Falsos positivos — volumes baixos. Vão cair conforme uso real. ✅

#### Latência adicional do middleware

Para rotas universais (`dashboard`, `escanear`), `ruleNeedsProfileLookup` retorna `false` → sem query SQL extra. Para rotas restritivas (`auditoria`, `relatorios`, `usuarios`, `configuracoes`, `nova-prova`, `provas`, `provas/{id}`), 1 query SQL adicional + 1 lookup LRU. Custo aceitável.

### 2.5 Achados de Manutenibilidade

#### AUD-W1V4-004 [MEDIUM] — Nome enganoso `test_matrix_rls_equivalence.py` — só valida Matriz ↔ Python

**Evidência:** `backend/tests/access/test_matrix_rls_equivalence.py:1-10`:
```python
"""Equivalencia entre as 3 camadas da Matriz de Acesso (Wave 1 v4.0 C05).

Camadas:
  1. Matriz declarativa  -> shared/access-matrix.json
  2. Backend (Python)    -> app/access (matrix.py + enforce.py + scopes.py)
  3. Banco (SQL)         -> backend/migrations/rls/012_*.sql

Este arquivo cobre a equivalencia entre 1 e 2 (Python).
```

**Bug semântico:** o nome do arquivo é `test_matrix_RLS_equivalence` mas a implementação só valida camadas 1 e 2 (Python contra JSON). A camada 3 (RLS) está apenas no script standalone. Um leitor casual do nome assume que RLS é coberto por pytest — não é.

**Recomendação:** renomear para `test_matrix_python_equivalence.py` (consistente com o `class TestMatrixPythonEquivalence` interno). Manter o conteúdo. Combinado com AUD-W1V4-002, considerar criar `test_matrix_rls_equivalence_db.py` que rode contra um banco isolado em CI (ou marcar como integration-test gated).

#### AUD-W1V4-106 [BAIXO] — `_scoping_filter` virou shim — tech debt

Já registrado como L-2 follow-up. Status: aceito.

#### AUD-W1V4-107 [BAIXO] — Comentário de "M-5 (audit fixes)" no script verify diz "asserca de verdade" mas a etapa [4/4] continua mais frouxa que [3/4]

Ver AUD-W1V4-003. Comentário pode confundir mantenedores futuros.

#### Manutenção da Matriz

`access-matrix.ts` importa o JSON via `resolveJsonModule`. `matrix.py` lê via `pathlib.Path(__file__).resolve().parent.parent.parent.parent`. Frágil se a estrutura mudar — registrado como L-7 follow-up.

#### `useAuthorization` re-fetcha `/users/me` em cada componente

Documentado em ADR-087 como aceito (Wave 5) e re-confirmado em L-4 follow-up. Trade-off de não introduzir Context.

#### Convenção de nome dos arquivos RLS

`009_helpers_v4.sql`, `010_rebase_rls_v4.sql`, `011_etiquetas_select_motorista_clicheria.sql`, `012_move_helpers_to_app_private.sql`. Descritivos. Cabeçalhos explicam supersedência. ✅

### 2.6 Achados de Cobertura de Testes

#### Cobertura das 48 células

`tests/access/test_matrix_rls_equivalence.py:test_48_cells_matrix_python_consistent` e `test_enforce_access_for.py:test_all_cells_match_expected_decision` cobrem 100% do JSON ↔ Python. ✅

#### Cobertura RLS

Coberta apenas pelo script standalone, e parcialmente (AUD-W1V4-002 + 003).

#### Casos de borda testados

- "STUDIO sem is_admin" → `resolve_profile` retorna None → `enforce_access_for` 403 (test_enforce_access_for.py:test_unmapped_user_raises_403). ✅
- Rule key inexistente → 500 (test_unknown_rule_key_raises_500). ✅
- JSON com schema inválido → ValueError no startup (4 testes em TestMatrixRuntimeValidation). ✅
- Vendedor com escopo vazio → não testado explicitamente, mas `scope_filter_for("provas.list", v)` retorna `vendedor_id == v.id`, e count em produção bate.

#### Casos de borda NÃO testados

- **AUD-W1V4-005 [MEDIUM]:** "claim modificado em runtime" (impersonação manual de outro setor) — não há teste. Confiamos em RLS via SQL impersonado em produção, mas o middleware do Next NÃO tem teste para token tampered. L-1 follow-up cobre essa lacuna.
- **JWT malformado/sem `sub`:** o middleware faz `supabase.auth.getUser()` que valida o token antes de retornar `user`. `loadProfile` falharia (data null). Sem teste explícito.

#### E2E

Não há suíte Playwright. Documentado em E.9. Smoke preview cobriu redirect anônimo apenas.

#### Mutation testing

Não realizado. Não obrigatório.

### 2.7 Achados de Documentação

#### AUD-W1V4-006 [MEDIUM] — Drift entre snippet do CLAUDE.md (linha 400-403) e padrão pós-M-1

Mesma evidência de AUD-W1V4-001. Reportado novamente nesta categoria pois é falha de manutenção de documentação após audit fix.

**Sugestão concreta:**
```diff
- 4. **No frontend**, na pagina:
-    ```tsx
-    const auth = useAuthorization("nova.chave");
-    if (!auth.loading && !auth.hasAccess) {
-      return <Restricted ruleKey="nova.chave" profile={auth.profile} />;
-    }
-    ```
+ 4. **No frontend**, na pagina:
+    ```tsx
+    const auth = useAuthorization("nova.chave");
+    if (auth.loading) return null; // M-1: evita flash de UI antes do guard
+    if (!auth.hasAccess) {
+      return <Restricted ruleKey="nova.chave" profile={auth.profile} />;
+    }
+    ```
```

#### Decisões em DECISIONS.md

D-1..D-7 explicam **por quê**, com trade-offs visíveis ("Alternativas avaliadas" + "Consequencias"). Excelente. ✅

#### `CLAUDE.md` seção "RBAC: como adicionar uma nova página"

7 passos. Conteúdo prático mas com bug AUD-W1V4-001. Resto OK. Após corrigir, um desenvolvedor novo conseguiria seguir.

#### Listagem de arquivos modificados no CHANGELOG

Detalhada por arquivo (linhas 8043-8074). Não usa "vários arquivos". ✅

#### Comentários de código nos arquivos novos

Excelentes — explicam o **porquê**, citam os IDs de findings (H-1, H-2, M-1, M-2, M-3, M-4, M-5), referenciam ADRs, dão contexto histórico. Acima da média do projeto.

### 2.8 Achados de Aderência ao Especificado

#### Conformidade ao analysis.md (Gate 1)

Cada divergência relevante (E.1 a E.10) está documentada na seção "Execução" do analysis. Em todos os casos a justificativa é clara e razoável:
- E.1 (TS+gerador → JSON único): justificativa técnica forte.
- E.2 (helpers em app_private): resposta a advisor pós-aplicação.
- E.3 (52 → 48 células): consolidação de Visualização+Timeline (semantica idêntica).
- E.4 (Clicheria PARCIAL vs FULL): documentada como follow-up obrigatório (D-2).
- E.5 (test pytest → script standalone): pragmático.
- E.6 (home_by_profile): conforme proposto.
- E.7 (factory access_required): preserva tests legacy.
- E.9 (Playwright NÃO): documentado.

#### Escopo declarado na Seção 1 do prompt

A wave **NÃO** modificou: schema de `auth.*` Supabase, R2/Cloudflare, Workers, KV, deploy, env vars. Confirmado via MCP. ✅

A wave **NÃO** criou nem removeu perfil. Os 4 perfis da Matriz (studio_admin, vendedor, motorista, clicheria) refletem o modelo v3.0 existente (`is_admin` + `setor`). ✅

A wave **NÃO** modificou state machine (B6/B12 da analysis). Confirmado por leitura de `state_machine.py`. ✅

#### Regras de isolamento de wave

Refactor coordenado tocou 5 routers backend + 5 pages frontend + 2 hooks + 2 deps/test. Tudo dentro do escopo "refactor coordenado autorizado pelo Gate 1".

#### Algo "fora" entrou?

Verifiquei: nenhum endpoint/page/feature novo além do necessário para RBAC.

#### Algo "dentro" ficou de fora?

- E2E Playwright (E.9) — declarado e justificado.
- Cobertura RLS no script (AUD-W1V4-002) — documentado como M-6 follow-up.
- Documentação do passo 4 atualizada (AUD-W1V4-001/006) — não capturado pelos audit fixes.

---

## Fase 3 — Verificação Comportamental em Staging

### 3.1 Matriz de prova vivo (impersonação SQL via MCP)

**Cenário 1 — admin (`admin@3studio.com.br`, auth_uid `b3b1601b-...`)**

| Tabela | Esperado (Matriz) | Observado | Veredito |
|---|---|---|---|
| `provas_digitais` | full → 16 | 16 | ✅ |
| `movimentacoes` | full → 16 | 16 | ✅ |
| `etiquetas` | full → 16 | 16 | ✅ |
| `audit_logs` | full → 74 | 74 | ✅ |
| `configuracoes_sistema` | full → 2 | 2 | ✅ |
| `usuarios` | full → 4 | 4 | ✅ |

**Cenário 2 — vendedor (`mariosouza@teste.com.br`, id interno `1cc1b1d0-...` = vendedor de 14 provas)**

| Tabela | Esperado (Matriz) | Observado | Veredito |
|---|---|---|---|
| `provas_digitais` | parcial self → 14 (suas) | 14 | ✅ |
| `movimentacoes` | parcial own/self → 14 | 14 | ✅ |
| `etiquetas` | parcial via prova → 14 | 14 | ✅ |
| `audit_logs` | negado → 0 | 0 | ✅ |
| `configuracoes_sistema` | negado → 0 | 0 | ✅ |
| `usuarios` | parcial self → 1 | 1 | ✅ |

**Cenário 3 — auth_uid sem registro em `public.usuarios`**

| Tabela | Esperado (defesa) | Observado | Veredito |
|---|---|---|---|
| `provas_digitais` | 0 | 0 | ✅ |
| `movimentacoes` | 0 | 0 | ✅ |
| `etiquetas` | 0 | 0 | ✅ |
| `audit_logs` | 0 | 0 | ✅ |
| `configuracoes_sistema` | 0 | 0 | ✅ |
| `usuarios` | 0 | 0 | ✅ |

**Conclusão Fase 3:** RLS comporta-se conforme a Matriz. Helpers `app_private.current_user_*` funcionam corretamente para usuário cadastrado, anônimo e desconhecido. Defesa em profundidade efetiva. ✅

**Limitação:** não pude validar Motorista nem Clicheria com dados reais (não há usuário ativo nesses setores em produção). O `verify_rbac_equivalence.py` cobre via insertion smoke + cleanup; aceito.

### 3.2 Cenários de borda observáveis

#### Setor antigo/inexistente em `public.usuarios`?

Setores em uso (DISTINCT): `STUDIO`, `VENDEDOR`. O enum tem 4 valores; 2 vazios. Nenhum valor antigo/inexistente. ✅

#### Registros órfãos em tabelas sensíveis?

Não verificado exaustivamente. Cenário-alvo seria, por exemplo, uma `movimentacao` com `usuario_id` nulo (usuário deletado e movimentação preservada por trigger imutabilidade). Improvável dado FK constraints. INFO AUD-W1V4-202.

#### `STUDIO` sem `is_admin`?

Modelo permite (SetorEnum.STUDIO + is_admin=False). Em produção: 0 usuários nessa configuração (todos os 2 STUDIO têm is_admin=true). `resolve_profile` retorna None → "negado em tudo" defensivo. ✅

### 3.3 Audit log da Wave 1 v4.0

**Verificação:** `audit_logs` tem 74 registros (admin view via impersonação). A Wave 1 v4.0 não fez ações de domínio (CRUD em provas), então não esperamos registros novos no log atribuíveis ao refactor. As migrations RLS aplicaram-se via `supabase_migrations` (separado de `audit_logs`). Não há pegada de "atividade administrativa de migração" no log de auditoria de domínio — comportamento esperado.

INFO AUD-W1V4-203: considerar registrar entradas em `audit_logs` para mudanças de RLS futuras (controle de mudança), mas não é requisito atual.

### 3.4 Cloudflare

Conferido via MCP:
- 1 conta (`20ab724c91f6bda669eecfe7c51c9171`) — pré-existente desde 2026-04-06.
- 1 R2 bucket (`rastreio-provas-artes`) — pré-existente desde 2026-04-07.
- 0 Workers.
- 0 KV namespaces.

**Wave 1 v4.0 não modificou Cloudflare.** ✅

---

## Achados Consolidados Ordenados por Severidade

### CRÍTICOS

Nenhum.

### ALTOS

Nenhum.

### MÉDIOS

| ID | Título | Arquivo:linha | Recomendação | Dono sugerido |
|---|---|---|---|---|
| **AUD-W1V4-001** | Snippet do CLAUDE.md (passo 4) reintroduz o bug do flash de UI corrigido por M-1 | `CLAUDE.md:400-403` | Atualizar snippet para `if (auth.loading) return null; if (!auth.hasAccess) return <Restricted/>` | Documentação |
| **AUD-W1V4-002** | Script `verify_rbac_equivalence.py` só valida `provas_digitais` (não 6 tabelas) | `scripts/verify_rbac_equivalence.py:128-215` | Estender para 6 tabelas. Já registrado como M-6 follow-up. | Backend |
| **AUD-W1V4-003** | Etapa [4/4] do script tem assertion frouxa para FULL/PARCIAL — só pega caso NEGADO+count>0 | `scripts/verify_rbac_equivalence.py:257-280` | Adicionar checks por `(rule, profile, table)` triple — comparar count RLS == count esperado. | Backend |
| **AUD-W1V4-004** | Nome enganoso `test_matrix_rls_equivalence.py` — só valida Matriz↔Python | `backend/tests/access/test_matrix_rls_equivalence.py:1-10` | Renomear para `test_matrix_python_equivalence.py`. | Backend |
| **AUD-W1V4-005** | Sem teste do middleware (claim manipulado, JWT malformado, cache LRU, redirect com cookie) | `frontend/src/lib/supabase/middleware.ts` (sem teste) | Criar `__tests__/middleware.test.ts` mockando `createServerClient`. Já registrado como L-1 follow-up. **Promovido para MEDIUM** porque é a camada superior da defesa em profundidade. | Frontend |
| **AUD-W1V4-006** | Drift entre snippet do CLAUDE.md e padrão pós-M-1 (mesmo bug de AUD-W1V4-001 — categoria distinta) | `CLAUDE.md:400-403` | Mesma correção. | Documentação |

### BAIXOS

| ID | Título | Arquivo | Status |
|---|---|---|---|
| AUD-W1V4-101 | TRUNCATE concedido a authenticated/anon (pré-existente, não vetor PostgREST) | `backend/migrations/rls/008` | Recomenda `REVOKE TRUNCATE ON public.audit_logs FROM anon, authenticated` em wave futura |
| AUD-W1V4-102 | Pass-through defensivo em `getRuleForPath = null` permite acesso a rota não mapeada | `frontend/src/lib/supabase/middleware.ts:208-210` | Documentar no CLAUDE.md ou adicionar lint CI |
| AUD-W1V4-103 | Cache LRU 30s no middleware atrasa revogação de admin | `frontend/src/lib/supabase/middleware.ts:54-58` | Documentar no CLAUDE.md; considerar invalidação ativa |
| AUD-W1V4-104 | `useCurrentUser` não valida `setor` em runtime | `frontend/src/hooks/useCurrentUser.ts:42` | Adicionar validação runtime |
| AUD-W1V4-105 | Endpoints de detalhe usam `scope_filter_for("provas.list", ...)` em vez de `provas.detail` | `backend/app/api/v1/provas.py:885` | Trocar 1 string |
| AUD-W1V4-106 | `_scoping_filter` virou shim — tech debt | `backend/app/api/v1/provas.py:661-673` | Já registrado como L-2 follow-up |
| AUD-W1V4-107 | Comentário "M-5: asserca de verdade" no script é otimista para a etapa [4/4] | `scripts/verify_rbac_equivalence.py:217` | Resolvido junto com AUD-W1V4-003 |

### INFO

| ID | Título | Onde |
|---|---|---|
| AUD-W1V4-201 | Se Matriz mudar `dashboard` para deny em algum perfil, há risco de redirect loop | `home_by_profile` × `dashboard` rule |
| AUD-W1V4-202 | Cenário "registro órfão invisível" não verificado exaustivamente | n/a |
| AUD-W1V4-203 | Mudanças de RLS não geram entrada em `audit_logs` (poderia ser controle de mudança) | RLS migrations vs audit_service |
| AUD-W1V4-204 | Extracts dos docx (`docs/wave1-v4/_extracted/*.md`) removidos pós-Gate 1 — perde reprodutibilidade da auditoria | `docs/wave1-v4/_extracted/` (ausente) |

---

## Recomendações de Próximos Passos

### Bloqueantes para a Wave 2 v4.0 — corrigir antes do próximo merge

1. **AUD-W1V4-001/006** — corrigir snippet do `CLAUDE.md` (passo 4 da seção "RBAC: como adicionar uma nova página"). Custo: 2 minutos.
2. **AUD-W1V4-002 + 003 + 004** — recomenda-se executar como uma sessão única de melhoria do script `verify_rbac_equivalence.py`:
   - Renomear `test_matrix_rls_equivalence.py` → `test_matrix_python_equivalence.py`.
   - Estender `verify_rbac_equivalence.py` para contar 6 tabelas × 4 perfis (24 counts) em vez de só `provas_digitais`.
   - Tornar a etapa [4/4] efetivamente assertiva por célula, não por sanity-check de enum.
   - Custo estimado: 1-2 horas. Alta-relação valor/esforço.

### Recomendados (não bloqueantes)

3. **AUD-W1V4-005** — adicionar testes unitários do middleware (L-1 já follow-up). Aumenta cobertura da camada superior de defesa.
4. **AUD-W1V4-105** — trocar 1 string em `_scoping_filter` para usar `provas.detail` no caminho de detalhe. Custo: 1 minuto.
5. **AUD-W1V4-101** — REVOKE TRUNCATE em `audit_logs` para fechar lacuna RNF-005. Pode ser RLS 013 dedicada. Custo: 30 minutos.

### Itens de backlog técnico identificados

6. **AUD-W1V4-102** — adicionar regra de CI que falhe se houver `app/(dashboard)/<x>/page.tsx` sem entrada na Matriz. Mitigação contra a "rota órfã invisível".
7. **AUD-W1V4-103** — invalidação ativa do cache LRU do middleware quando admin é desativado/promovido. Reduz janela de 30s.
8. **AUD-W1V4-104** — validação runtime de `setor` em `useCurrentUser` (zod ou guard manual).
9. **D-2 (Clicheria) follow-up obrigatório** — confirmar com Renan se Clicheria deve passar a ver todas as provas (Matriz literal) ou se a Matriz deve ser ajustada para refletir o filtro por status (status quo).
10. **AUD-W1V4-204** — restaurar extracts dos docx em `docs/wave1-v4/_extracted/` ou apontar para um local oficial git-trackeado.

---

## Anexos

### A.1 Output do MCP Supabase (read-only)

- **Project:** `rwxlpwmnkekzuurgthkr` ACTIVE_HEALTHY, sa-east-1, PG 17.6.1.104.
- **Tabelas:** 7 em `public` — todas com RLS habilitada (`relrowsecurity=true`, `relforcerowsecurity=false`).
- **Policies:** 12 em `public.*`, todas referenciando `app_private.current_user_*`.
- **Funções:** 3 em `app_private` (current_user_is_admin/setor/id), 0 em `public.current_user_*`.
- **Advisor security:** 1 INFO `rls_enabled_no_policy` (alembic_version, intencional ADR-025) + 1 WARN `auth_leaked_password_protection` (WONTFIX ADR-027). Nada novo.
- **Advisor performance:** 12 INFOs `unused_index` (volume baixo). Nada novo.
- **Usuários ativos:** 4 (2 STUDIO admin + 2 VENDEDOR FILIAL). Nenhum MOTORISTA/CLICHERIA real.
- **Claims do JWT:** `raw_app_meta_data` apenas `{provider, providers}`; `raw_user_meta_data` apenas `{email_verified}`. Sem `setor`/`is_admin`. Confirma D-3.

### A.2 Output do MCP Cloudflare

- 1 account (3studioagn@gmail.com), 1 R2 bucket (`rastreio-provas-artes`), 0 Workers, 0 KV. Wave 1 v4.0 não modificou.

### A.3 Cenários reproduzidos mentalmente com resultado

Listados na Fase 2.2 e Fase 3.1.

### A.4 Diff amostral examinado

Lista completa de commits da branch (entre `1e086b3` e `3fb6e93`):
- `1e086b3` — analise read-only pre-execucao (analysis.md)
- `c1847a8` — RLS 009-012 + SSoT JSON do RBAC
- `d4f4801` — backend app/access + refactor B1-B12
- `81ec1cc` — frontend access layer + middleware RBAC + refactor pages
- `e45e17a` — equivalencia 3 camadas + cleanup
- `a094819` — closeout (CHANGELOG + DECISIONS + CLAUDE + analysis)
- `ac3be70` — audit fixes H-1, H-2 + M-1..M-5
- `3fb6e93` — apêndice docs

### A.5 Checagens explícitas via grep

| Padrão | Hits | Comentário |
|---|---|---|
| `Depends(get_admin_user)` em endpoints novos | 0 | ✅ refactor completo |
| `require_role(` em qualquer arquivo de produção | 0 | ✅ removido |
| `if (!user.is_admin)` em frontend pages/components | 0 | ✅ |
| `user.setor === "..."` em frontend | 0 | ✅ |
| `access_required("<key>")` keys != JSON | 0 | ✅ todas batem |

---

**Fim do relatório.**

---

## Apêndice — Status final por achado (preenchido pela sessão de correção 2026-05-04)

> Esta seção é apêndice gerado pela sessão `wave1-v4/fixes/execution`
> (Audit Round 2 Fixes). O corpo do relatório acima permanece intacto.
> Ver `docs/wave1-v4/fix-plan.md` para o plano de correção e
> `docs/wave1-v4/fix-validation.md` (criado ao final do Gate 2) para o
> relatório de validação consolidado.

| ID | Status | Commit | Critério verificado |
|---|---|---|---|
| AUD-W1V4-001 | RESOLVIDO | _pending_ | Snippet do passo 4 em `CLAUDE.md` agora usa `if (auth.loading) return null;` antes do guard. |
| AUD-W1V4-006 | RESOLVIDO | _pending_ (junto com 001) | Mesmo critério de AUD-W1V4-001 — agrupados por identidade. |
| AUD-W1V4-004 | RESOLVIDO | _pending_ | `test_matrix_rls_equivalence.py` renomeado para `test_matrix_python_equivalence.py` (git mv preserva histórico); docstring atualizada deixando explícito que cobre apenas Python↔JSON; `pytest backend/tests/access/test_matrix_python_equivalence.py` passa (1 teste, 48 cells). |
| AUD-W1V4-002 | RESOLVIDO | _pending_ | `verify_rbac_equivalence.py` estendido para 4 perfis × 6 tabelas (era 4 × 1). Etapa [3/4] mostra matriz `visto/esperado` por (perfil, tabela). Execução em produção 2026-05-04: SUCESSO — admin 16/16/16/74/2/8, vendedor 0/0/0/0/0/1, motorista 0/0/0/0/0/1, clicheria 2/8/2/0/0/1 (provas/mov/etiquetas/audit/config/usuarios). Smoke positivo + smoke negativo planejados em AUD-003. |
| AUD-W1V4-003 | RESOLVIDO | _pending_ | Etapa [4/4] reescrita para validar `(rule, profile, table)` triple. Mapping `rule_governs_table`: provas.list→provas_digitais; provas.detail→provas_digitais+movimentacoes+etiquetas; auditoria→audit_logs; configuracoes→configuracoes_sistema. Para FULL valida count==total; PARCIAL valida count==expected (espelhando policy); NEGADO valida count==0. **Smoke positivo (matriz atual)**: `OK — 24 cells governadas + 32 sanity validadas` (exit 0). **Smoke negativo** (vendedor.audit_logs expected mudado para 99): script falhou com mensagem clara `[vendedor][audit_logs] RLS viu 0, esperado 99` (exit 1). Divergência sintética revertida; segunda execução voltou a SUCESSO. |
| AUD-W1V4-005 | RESOLVIDO (Opção A) | _pending_ | Vitest 2.1.9 instalado em devDependencies; `vitest.config.ts` mínimo (env node); script `"test": "vitest run"` adicionado. **Suíte `frontend/src/lib/supabase/__tests__/middleware.test.ts`** com **15 testes passando** cobrindo: (a) `getRuleForPath` com/sem trailing slash + path não mapeado + dynamic match `/provas/[id]`; (b) `evaluateRule` para vendedor em /auditoria (NEGADO) e /provas (PARCIAL self_vendedor); (c) `updateSession` para anônimo em rota não-pública (redirect /login), pass-through em rota pública, admin em /auditoria (pass-through sem header), vendedor em /auditoria (302 + cookie auth-toast `rota_negada`), vendedor em /provas (pass-through + header `x-rbac-scope` self_vendedor); (d) **defesa H-1**: user com `ativo=false` → /login + cookie `perfil_ausente`; (e) **defesa H-2**: cookie `Secure` em production / sem `Secure` em development; (f) **cache LRU**: 2ª chamada para mesmo auth_uid não dispara nova query SQL. `npm run lint` + `tsc --noEmit` + `npm run build` permanecem limpos; middleware bundle 82.9 kB (idêntico ao pré-fix). |
| AUD-W1V4-101 | RESOLVIDO | _pending_ | Migration `backend/migrations/rls/013_revoke_truncate_audit_logs.sql` criada e aplicada via MCP `apply_migration` (2026-05-04). **Pre-revoke** (MCP `has_table_privilege`): authenticated/anon/service_role TRUNCATE = true/true/true. **Post-revoke**: authenticated=false, anon=false, service_role=true (preservado), authenticated SELECT preservado=true. Advisor security: 1 INFO + 1 WARN históricos, **nenhum novo alerta**. 4ª camada de defesa em profundidade RNF-005 fechada (TRUNCATE bypassa RLS e não dispara trigger BEFORE UPDATE/DELETE). |
| AUD-W1V4-105 | RESOLVIDO | _pending_ | Em `backend/app/api/v1/provas.py`: criada nova função `_scoping_filter_for_detail(user)` que delega para `scope_filter_for("provas.detail", user)`; chamada em `_carregar_prova_com_scoping` (linha 913) trocada de `_scoping_filter` (que usava `provas.list`) para `_scoping_filter_for_detail`. Comentários explicativos referenciam AUD-W1V4-105 e o teste `test_provas_detail_inherits_provas_list_scopes` que garante semântica idêntica hoje. Validação: `pytest backend/tests/test_provas_api.py + tests/access/test_scope_filter_for.py` → 176/176 passam. |
| AUD-W1V4-104 | RESOLVIDO | _pending_ | Em `frontend/src/hooks/useCurrentUser.ts`: adicionado `VALID_SETORES = Set<Setor>(["STUDIO","VENDEDOR","MOTORISTA","CLICHERIA"])` + type guard `isValidUserInfo(payload)`. Payload de `/api/v1/users/me` agora é validado em runtime; campos errados (id/nome/is_admin/setor) ou setor fora do conjunto canônico → `console.warn` + `setState({user:null})` (deny seguro). Validação: `tsc --noEmit` limpo, `next lint` limpo, `vitest` 15/15 passam. |
| AUD-W1V4-102 | RESOLVIDO | _pending_ | `CLAUDE.md` passo 1 da seção "RBAC: como adicionar uma nova página" recebeu **AVISO (AUD-W1V4-102)** explicando que `getRuleForPath = null` faz pass-through silencioso, e que toda nova rota EXIGE entrada na Matriz mesmo que `full` para os 4 perfis. Defesa de fundo (backend `access_required` + RLS) reforçada como camada inferior. Não introduz lint CI nesta sessão (fica como follow-up técnico). |
| AUD-W1V4-103 | RESOLVIDO | _pending_ | `CLAUDE.md` ganhou nota explícita **"Latencia de revogacao no middleware (AUD-W1V4-103)"** ao final da seção RBAC, descrevendo: TTL 30s do `PROFILE_CACHE`, mitigação via defesa em profundidade (backend `get_current_user` valida `ativo` sem cache; RLS `app_private.current_user_*()` lê fresh), pior caso da janela (~30s navegação até página admin-only com 403 do backend e RLS filtrando dados), e referência ao follow-up de invalidação ativa. |
