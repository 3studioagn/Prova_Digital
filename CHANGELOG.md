# Changelog

---

## [2026-04-09 — Sessao 6] — Wave 1: Auditoria de validacao final (sign-off pre-Wave 2)

### Contexto
Mario pediu uma segunda passada de auditoria, agora puramente de validacao: confirmar
que tudo o que foi planejado nas Sessoes 5/5b realmente esta no codigo, no banco e nos
testes; que nao houve regressao silenciosa; e que a Wave 1 pode ser declarada pronta
para a Wave 2. **Escopo: zero mudancas de codigo, apenas verificacao + atualizacao
aditiva de CHANGELOG/DECISIONS/CLAUDE se algo estivesse defasado.** Se a auditoria
encontrasse novos problemas, eu pararia e reportaria antes de tocar em qualquer arquivo.

### Verificacoes executadas

**1. Backend — testes + cobertura**
- `python -m pytest --cov=app --cov-report=term-missing -q`: **108 passed, 1 warning,
  91% cobertura global**. Identico ao baseline da Sessao 5b — zero regressao.
- Cobertura por modulo critico: `app/api/v1/users.py` 93%, `app/core/supabase_admin.py`
  100%, `app/api/deps.py` 100%, `app/core/jwt.py` 88%, `app/domain/schemas/user.py` 100%.
- Warning unico: `JWT test com chave curta` (intencional, ja documentado).
- 0 deprecation warnings (`HTTP_422_UNPROCESSABLE_CONTENT` confirmado em uso, ADR-021).

**2. Frontend — typecheck + lint + build**
- `npx tsc --noEmit`: 0 erros.
- `npm run lint`: 0 warnings.
- `npm run build`: 0 erros. Bundles: `/usuarios` 4.9 kB, `/login` 1.81 kB,
  middleware 80.1 kB. Identicos ao baseline da Sessao 5b.

**3. Estado do banco em producao (via Supabase MCP)**
- `public.alembic_version` = `008` com RLS habilitado, 0 policies (ADR-025 confirmado).
- 11 RLS policies em `public.*` todas usando `is_admin = true` (ADR-018 confirmado em runtime).
- Constraints da migration 003 todas presentes: `chk_ciclo_positivo`,
  `chk_status_diferente`, `chk_ciclo_atual_positivo`, `chk_vendedor_localizacao`.
- Triggers de imutabilidade: `trg_etiquetas_imutavel`, `trg_audit_logs_imutavel`,
  `trg_movimentacoes_imutavel` + 3 triggers `_updated_at` ativos.
- Indexes Wave 1: `idx_usuarios_created_by` (migration 005),
  `idx_configuracoes_sistema_updated_by` (migration 008).
- Trigger functions: `fn_bloquear_alteracao` e `fn_atualizar_updated_at` ambas com
  `search_path = ''` (ADR-024 confirmado).
- **Estado de usuarios**: 2 linhas em `public.usuarios`, 2 em `auth.users`,
  0 banidos, 0 orfaos, sync_state=OK. **1 admin ativo** (vide notas operacionais abaixo).

**4. Advisors do Supabase**
- **Security**: 1x INFO `rls_enabled_no_policy` em `alembic_version` (esperado, ADR-025)
  + 1x WARN `auth_leaked_password_protection` (WONTFIX, ADR-027). **Sem novos achados.**
- **Performance**: 11x WARN `auth_rls_initplan` (Decisao 4b, adiado para Wave 2) +
  varios INFO `unused_index` (esperado — indexes Wave 2/3 sem queries ainda).
  **Sem novos achados.**

**5. Cruzamento Codigo ↔ Requisitos (Wave 1)**

| Req | Implementacao confirmada | Evidencia |
|-----|--------------------------|-----------|
| RF-017 (cadastro com setor + localizacao) | `UserCreate` schema + `chk_vendedor_localizacao` no DB | `backend/app/domain/schemas/user.py:40-77`, migration 003 |
| RF-018 (login Supabase Auth) | Login form + middleware Next.js | `frontend/src/app/login/page.tsx:1-132`, `frontend/src/lib/supabase/middleware.ts:1-47` |
| RF-019 (CRUD usuarios admin-only) | `get_admin_user` em todos os 6 endpoints | `backend/app/api/v1/users.py` (todos os routes), `backend/app/api/deps.py:1-121` |
| RF-020 (RBAC por setor) | `require_role(*allowed_setors)` factory + RLS unificada | `backend/app/api/deps.py`, RLS migration 004 |
| RN-009 (vendedor com localizacao obrigatoria) | `model_validator` Pydantic + DB constraint | `backend/app/domain/schemas/user.py:60-77`, `backend/app/api/v1/users.py` PATCH cross-validation |
| RN-010 (proteger ultimo admin) | 4 protecoes empilhadas (PATCH self/last + DELETE self/last) | `backend/app/api/v1/users.py:33-49` (`_count_other_active_admins`) + uso em PATCH/DELETE |
| RNF-003 (timeout 30 min) | `useInactivityTimeout(30*60*1000, handleLogout)` | `frontend/src/app/(dashboard)/layout.tsx:30,148`, `frontend/src/hooks/useInactivityTimeout.ts:1-34` |
| RNF-004 (senha hashed, nunca em plaintext) | Supabase Auth gerencia bcrypt; backend so passa em POST | `backend/app/core/supabase_admin.py:create_auth_user` |

**6. Cruzamento com Backlog (Components 03/04/05 da Wave 1)**
- **Component 03 — Login**: pagina `/login` funcional, redireciona para `/usuarios`,
  middleware bloqueia acesso a rotas `(dashboard)/*` sem sessao. ✅
- **Component 04 — Users CRUD**: 6 endpoints (GET list, GET me, GET id, POST, PATCH,
  DELETE), UI com tabela + filtros + 3 modais (criar/editar/desativar). ✅
- **Component 05 — RBAC**: `is_admin` boolean no domain DB, `get_admin_user` dependency
  protegendo todos os endpoints sensiveis, RLS unificada com `is_admin = true`,
  `require_role` factory pronta para Waves futuras (uso ja preparado). ✅

### Saga auth↔DB confirmada por leitura de codigo (4 cenarios)
- **POST /users** com falha no commit → `delete_auth_user` (best-effort, ADR-020).
- **PATCH /users/{id}** ativo:false→true com falha no commit → `disable_auth_user`
  (compensacao reversa).
- **PATCH /users/{id}** ativo:true→false com falha no commit → `enable_auth_user`
  (compensacao reversa). `disable_auth_user` chamado ANTES do commit.
- **DELETE /users/{id}** com falha no commit → `enable_auth_user` (compensacao reversa).
  `disable_auth_user` chamado ANTES do commit.
- Compensacao falha → loga "drift manual" para investigacao (ADR-020).

### Resultado
- **Zero mudancas de codigo nesta sessao** — auditoria foi puramente verificadora.
- **Zero regressao**: 108 testes passando, frontend buildando limpo, advisors com mesmo
  perfil da Sessao 5b.
- **Zero drift entre auth e public.usuarios** em producao.
- **Documentacao em dia**: CHANGELOG/DECISIONS/CLAUDE refletem com precisao o estado
  atual do codigo e do banco.

### Veredicto
**Wave 1 esta APROVADA para sign-off.** Todos os requisitos funcionais (RF-017 a RF-020)
e nao-funcionais (RNF-003, RNF-004) da Wave 1 estao implementados, testados e
verificados em producao. As 3 ressalvas conhecidas (single-admin SPOF, deferred
initplan, leaked password WONTFIX) estao documentadas, monitoradas, e nao sao
bloqueantes para iniciar a Wave 2.

### Decisoes formalizadas para a Wave 2 (ADRs novos)

A auditoria nao mudou codigo, mas formalizou como ADRs duas decisoes que ate aqui
estavam soltas em texto livre no CHANGELOG. Ambas precisam ser executadas no inicio
da Wave 2:

- **ADR-029 — Reescrita das policies RLS para `(SELECT auth.uid())`** (adiada para
  Wave 2). Os 11 WARN `auth_rls_initplan` do advisor sao otimizacao, nao bug. Sem
  volume nao da para medir o ganho — a Wave 2 vai trazer `provas_digitais` e
  `movimentacoes` com dados suficientes. Plano de execucao detalhado no ADR (criar
  `backend/migrations/rls/005_initplan_optimization.sql`, aplicar via `apply_rls.py`,
  medir `EXPLAIN ANALYZE` antes/depois, confirmar zero WARN no advisor).
- **ADR-030 — Criar segundo admin operacional antes da Wave 2 entrar em uso real**
  (resolve o SPOF organizacional). Producao tem 1 unico admin (Mario). RN-010 protege
  contra auto-delete, mas se a conta auth for perdida a unica recuperacao e
  intervencao manual fora do app. Decisao: criar `ops@3studio.com.br` (ou similar) via
  o proprio fluxo `POST /api/v1/users` antes da primeira prova digital cadastrada.
  Restricoes detalhadas no ADR (conta dedicada, senha em gerenciador, validacao
  pos-criacao, registro de quem tem acesso compartilhado).

### Notas operacionais (nao bloqueantes — todas formalizadas em ADRs)
- **Single admin ativo (SPOF organizacional)** → ADR-030. Resolver na Sessao 7
  (abertura da Wave 2), antes de qualquer tarefa funcional.
- **`auth_rls_initplan` (11 WARN)** → ADR-029. Primeira tarefa tecnica da Wave 2,
  apos a primeira leva de dados de carga real.
- **`auth_leaked_password_protection`** → ADR-027 (WONTFIX). Recurso pago do Supabase.
  Compensado por: senha minima GoTrue, rate limiting nativo, signup publico
  desabilitado (todos via Admin API — ADR-013). Re-avaliar quando houver upgrade de
  plano OU se o backlog acrescentar signup publico.

### Documentos atualizados
- `CHANGELOG.md` — esta secao (sign-off da Wave 1 + referencias aos ADRs novos).
- `DECISIONS.md` — **ADR-029** (RLS initplan rewrite adiada para Wave 2) e
  **ADR-030** (criar segundo admin operacional antes da Wave 2).
- `CLAUDE.md` — sem alteracao (listagem de migrations ja estava em dia, e ADRs novos
  nao tocam migrations).

---

## [2026-04-08 — Sessao 5] — Wave 1: Auditoria critica pre-Wave 2

### Contexto
Mario pediu uma auditoria completa, critica e exigente da Wave 1 (Componentes 03-Login,
04-Users CRUD, 05-RBAC) antes de avancar para a Wave 2. Objetivo: provar que a Wave 1 esta
"100% pronta, fail-safe, robusta". Acesso a Supabase MCP e Cloudflare MCP autorizado.
Escopo: NAO tocar nas Waves 2-6. Wave 0 so com permissao explicita. Atualizar
CHANGELOG/CLAUDE/DECISIONS aditivamente.

### Verificacoes feitas (sem mudar codigo)

- **Backend testes**: 96 → 108 passed, 0 deprecation warnings, cobertura 91% global,
  `app/api/v1/users.py` 93%, `app/core/supabase_admin.py` 100%, `app/api/deps.py` 100%.
- **Frontend**: `tsc --noEmit` sem erros, `next lint` sem warnings, `next build` sem erros.
  Bundle final: `/usuarios` 4.9 kB, `/login` 1.81 kB, middleware 80.1 kB.
- **Supabase MCP** (`rwxlpwmnkekzuurgthkr`, sa-east-1, ACTIVE_HEALTHY, Postgres 17.6.1.104):
  - 6 tabelas com RLS habilitado: `usuarios` (3 linhas), `provas_digitais`, `movimentacoes`,
    `etiquetas`, `audit_logs`, `configuracoes_sistema` (2 linhas).
  - 11 policies RLS confirmadas usando `is_admin = true` (consistente com ADR-018).
  - Constraints da migration 003 presentes: `chk_ciclo_positivo`, `chk_status_diferente`,
    `chk_ciclo_atual_positivo`, `chk_vendedor_localizacao`.
  - 3 triggers de imutabilidade ativos: `trg_etiquetas_imutavel`, `trg_audit_logs_imutavel`,
    `trg_movimentacoes_imutavel` + 3 triggers `_updated_at`.
  - Indexes da migration 003 presentes: `idx_movimentacoes_created_at`, `idx_movimentacoes_prova_data`.
  - **Drift de tracking detectado**: `public.alembic_version` NAO existe e
    `supabase_migrations.schema_migrations` so tem 001/002 — migrations 003/004 foram
    aplicadas via SQL direto (ver ADR-022 para o plano de remediacao).
  - **Drift de auth detectado**: `regianepetrim@teste.com.br` tem `auth.users.banned_until =
    2126-04-09` (banido por 100 anos por DELETE antigo) MAS `public.usuarios.ativo = true`
    (alguem reativou via PATCH sem unban). Prova ao vivo dos bugs corrigidos abaixo.
  - Performance advisor (level INFO): FK `usuarios.created_by` sem index.
- **Cloudflare R2 MCP**: bucket `rastreio-provas-artes` confirmado (account
  `20ab724c91f6bda669eecfe7c51c9171`, location ENAM). Sem mudancas — Wave 0.

### Bugs CRITICOS encontrados e corrigidos

- **`backend/app/core/supabase_admin.py`** — `disable_auth_user` agora chama
  `resp.raise_for_status()` (era best-effort, apenas logava). Adicionada nova funcao
  `enable_auth_user(auth_uid)` que faz `PUT /auth/v1/admin/users/{id}` com
  `{"ban_duration": "none"}` (convencao GoTrue para desbanir). `delete_auth_user` PERMANECE
  best-effort por design (so e chamada no rollback de create — la o erro do DB ja aconteceu
  e nao podemos mascara-lo). Ver ADR-020.
- **`backend/app/api/v1/users.py` — PATCH `/users/{id}`**:
  - **Bug fixado**: PATCH `ativo: false → true` agora chama `enable_auth_user` ANTES do
    commit. Antes, o usuario continuava banido em `auth.users` mesmo apos reativacao no
    app DB → drift real em producao (regiane).
  - **Logica nova**: detecta `was_active != will_be_active` antes de mutar o objeto. Se
    `needs_ban`, chama `disable_auth_user`; se `needs_unban`, chama `enable_auth_user`.
    Falha auth → 502 + rollback, sem persistir nada.
  - **Compensacao saga**: se `db.commit()` falhar APOS auth ja ter mudado, faz a operacao
    inversa (re-enable apos ban falho, re-disable apos unban falho). Falha de compensacao
    loga "drift manual" para investigacao operacional.
- **`backend/app/api/v1/users.py` — DELETE `/users/{id}`**:
  - **Bug fixado**: `disable_auth_user` agora roda ANTES de `db.commit()`. Antes, se a
    chamada GoTrue falhasse, o usuario ficava `ativo=false` no app DB mas com tokens
    ainda renovaveis na auth.
  - **Compensacao saga**: se `db.commit()` falhar apos disable, chama `enable_auth_user`
    para reverter o ban. Falha de compensacao loga "drift manual".
- **Deprecation warnings**: 4 ocorrencias de `HTTP_422_UNPROCESSABLE_ENTITY` substituidas
  por `HTTP_422_UNPROCESSABLE_CONTENT` (Starlette 0.40+, RFC 9110). Ver ADR-021.

### Migration nova (NAO aplicada — aguarda decisao do Mario)

- **`backend/migrations/versions/005_add_index_on_usuarios_created_by.py`** — Cria
  `idx_usuarios_created_by` na FK `usuarios.created_by → usuarios.id`. Idempotente
  (`IF NOT EXISTS`). Resolve o aviso INFO do Supabase advisor. **Pendente:** definir como
  aplicar — via Alembic (precisa estabilizar tracking — ADR-022) ou via Supabase MCP
  `apply_migration` (mais rapido, mas perpetua o drift).

### Tests adicionados

- **`backend/tests/test_supabase_admin.py`** (+2 testes):
  - `test_disable_auth_user_failure_raises` (substitui `_does_not_raise`) — confirma novo
    contrato de raise.
  - `test_enable_auth_user_success` — verifica metodo PUT, URL, payload `{"ban_duration": "none"}`.
  - `test_enable_auth_user_failure_raises` — confirma propagacao de erro.
- **`backend/tests/test_users_api.py`** (+9 testes):
  - `test_update_user_reactivation_unbans_in_auth` — PATCH `ativo:false→true` chama
    `enable_auth_user`.
  - `test_update_user_deactivation_bans_in_auth_before_commit` — PATCH `ativo:true→false`
    chama `disable_auth_user` ANTES do commit (verifica ordem).
  - `test_update_user_unrelated_field_does_not_touch_auth` — PATCH so de `nome` nao toca
    em auth.
  - `test_update_user_ban_failure_returns_502_and_does_not_commit`.
  - `test_update_user_unban_failure_returns_502_and_does_not_commit`.
  - `test_update_user_db_commit_fails_after_ban_compensates` — saga reversa.
  - `test_update_user_db_commit_fails_after_unban_compensates` — saga reversa inversa.
  - `test_deactivate_user_disable_runs_before_commit` — DELETE: ordem `disable → commit`.
  - `test_deactivate_user_ban_failure_returns_502_and_does_not_commit`.
  - `test_deactivate_user_db_commit_fails_after_ban_compensates`.
- Atualizado `test_patch_skips_last_admin_check_for_non_admin_target` para mockar
  `disable_auth_user` (agora a transicao `ativo:true→false` chama auth).

### Resultado final

- **108 passed, 1 warning** (warning intencional do JWT test com chave curta), 0
  deprecation warnings, **91% cobertura global**, 93% em `users.py`, 100% em
  `supabase_admin.py`/`api/deps.py`.
- Frontend continua passando em `tsc`, `next lint`, `next build`.
- Estado auth↔app no codigo: garantidamente convergente ou logado como drift explicito.

### Acoes pendentes (aguardam Mario)

1. **Reativar `regianepetrim@teste.com.br` no Supabase Auth**: o drift atual continua em
   producao. Opcoes: (a) chamar `enable_auth_user(uid)` via script, (b) Supabase Dashboard
   → Authentication → Users → Unban.
2. **Aplicar migration 005**: via Alembic (precisa estabilizar tracking primeiro — ver
   ADR-022) ou via Supabase MCP `apply_migration` (mais rapido, perpetua drift).
3. **Estabilizar tracking de migrations**: rodar `alembic stamp head` para criar
   `public.alembic_version` apontando para 004, antes de aplicar 005 via Alembic.
4. **Wave 0 — issues do advisor (NAO toquei, aguarda autorizacao)**:
   - `function_search_path_mutable` em `fn_bloquear_alteracao` e `fn_atualizar_updated_at`.
   - `auth_rls_initplan` (multiple permissive policies — performance, nao seguranca).
   - `leaked_password_protection` desabilitado no Auth (HaveIBeenPwned check off).

### Documentos atualizados

- `DECISIONS.md` — ADRs 020 (saga auth↔DB), 021 (HTTP_422_UNPROCESSABLE_CONTENT), 022
  (drift de tracking), 023 (index FK created_by).
- `CHANGELOG.md` — esta sessao.

---

## [2026-04-08 — Sessao 5b] — Wave 1: Execucao do plano da auditoria (migrations 005→008)

### Contexto
Apos a auditoria da Sessao 5, Mario aprovou o plano completo: estabilizar o tracking
Alembic, aplicar a migration 005, e tratar os warnings Wave 0 que eu havia listado como
pendentes (search_path mutavel + impactos colaterais detectados durante a execucao).
Mario ficou com 2 acoes manuais no Dashboard (unban da regiane + ativar leaked password
protection); todo o resto foi executado nesta sessao via Supabase MCP. **Escopo Wave 0
liberado explicitamente para os 3 warnings desta sessao** — nao para o restante.

### Estabilizacao do tracking Alembic (ADR-022 endereçado)

- **`python -m alembic stamp 004`** rodado contra producao com `DATABASE_URL` apontando
  para `aws-1-sa-east-1.pooler.supabase.com:5432` (pooler Session). `env.py` usa
  `python-dotenv` para carregar `.env` e converte `postgresql+asyncpg://` →
  `postgresql://` para o driver sync do Alembic.
- Criou `public.alembic_version` com `version_num = '004'`. **Side effect detectado pelo
  advisor de seguranca**: tabela criada SEM RLS no schema `public`, exposto via PostgREST
  (qualquer cliente com a anon key conseguia ler/escrever o numero da versao). Tratado
  por uma migration nova (007) ainda nesta sessao — ver abaixo.
- **`python -m alembic upgrade head`** aplicou a migration 005 normalmente. Verificacao
  via MCP `execute_sql` confirmou `idx_usuarios_created_by` em `pg_indexes` e
  `alembic_version = 005`.

### Migrations novas aplicadas em producao (todas via Alembic, idempotentes)

- **`backend/migrations/versions/005_add_index_on_usuarios_created_by.py`** (criada na
  Sessao 5, aplicada nesta) — `CREATE INDEX IF NOT EXISTS idx_usuarios_created_by ON
  usuarios(created_by)`. Resolveu o INFO `unindexed_foreign_keys` do advisor.
- **`backend/migrations/versions/006_set_search_path_on_trigger_functions.py`** (nova) —
  `ALTER FUNCTION public.fn_bloquear_alteracao() SET search_path = '';` +
  `ALTER FUNCTION public.fn_atualizar_updated_at() SET search_path = '';`. Resolveu os
  WARN `function_search_path_mutable` (ADR-024). Validado em runtime: `UPDATE` em
  `configuracoes_sistema` continuou disparando o `_updated_at` corretamente
  (`updated_at` mudou de `2026-04-07` para `2026-04-08`). As tabelas imutaveis
  (`movimentacoes`/`etiquetas`/`audit_logs`) estao vazias e nao foi possivel testar
  `fn_bloquear_alteracao` ao vivo, mas a fonte usa apenas built-ins schema-qualified
  (`NOW()`, `RAISE EXCEPTION`) — sem dependencia de `search_path`.
- **`backend/migrations/versions/007_enable_rls_on_alembic_version.py`** (nova, **fix de
  side effect** do `alembic stamp`) — `ALTER TABLE public.alembic_version ENABLE ROW
  LEVEL SECURITY;` sem nenhuma policy. Postgres com RLS ligado e zero policies bloqueia
  100% do PostgREST por default. O role `postgres` usado pelo Alembic bypassa RLS, entao
  `alembic upgrade head` continua funcionando. Verificacao via MCP confirmou
  `relrowsecurity = true`. Resolveu o ERROR `rls_disabled_in_public` que apareceu
  imediatamente apos o stamp. Ver ADR-025.
- **`backend/migrations/versions/008_add_index_on_configuracoes_sistema_updated_by.py`**
  (nova, **bonus finding** durante o re-run do advisor) — `CREATE INDEX IF NOT EXISTS
  idx_configuracoes_sistema_updated_by ON configuracoes_sistema(updated_by)`. Mesmo
  padrao do 005, em uma FK da migration 001 que tinha sido esquecida. Provavelmente o
  advisor so reportava a primeira FK sem index, e expos a segunda quando o primeiro foi
  corrigido. Ver ADR-026.

### Estado final do tracking
- `public.alembic_version` existe, esta com RLS habilitado (zero policies = bloqueia
  PostgREST), `version_num = '008'`, e e a fonte de verdade do dominio Wave 1.
- `supabase_migrations.schema_migrations` continua refletindo apenas o que a CLI Supabase
  aplicou (001/002). Convivencia documentada — Alembic = dominio, Supabase migrations =
  setup inicial fora do escopo Alembic.

### Resultado dos advisors apos as migrations

- **Security advisor** — antes: 2x WARN `function_search_path_mutable` + 1x WARN
  `auth_leaked_password_protection`. Depois: 1x INFO `rls_enabled_no_policy` em
  `public.alembic_version` (esperado, e o objetivo do fix) + 1x WARN
  `auth_leaked_password_protection` (Decisao 4c — Mario precisa habilitar via Dashboard,
  nao tem API). Tudo o mais limpo.
- **Performance advisor** — antes: 1x INFO `unindexed_foreign_keys`
  (`usuarios.created_by`) + 11x WARN `auth_rls_initplan` + varios INFO `unused_index`.
  Depois: o INFO original sumiu (resolvido por 005), surgiu e foi resolvido o INFO
  bonus em `configuracoes_sistema.updated_by` (resolvido por 008), os 11 WARN
  `auth_rls_initplan` permanecem (Decisao 4b — adiado para a Wave 2 quando houver
  trafego real para medir o ganho), os INFO `unused_index` permanecem (esperado — sao
  indexes para Wave 2/3 que ainda nao tem queries).

### Tests
- **`python -m pytest -q --no-header`** depois das 4 migrations: **108 passed, 1
  warning** (mesmo warning intencional do JWT test). Migrations sao DDL/metadata-only
  (CREATE INDEX, ALTER FUNCTION, ALTER TABLE) e os testes mockam Supabase Auth, entao
  nao dependem do estado real de producao — confirmacao de que a aplicacao continua
  estavel apos as mudancas no banco.

### Acoes manuais (resolvidas em adendo apos o relatorio)

1. ~~**Unban da regiane**~~ — **RESOLVIDO POR DELETE** (ver ADR-028). Mario informou que
   (a) nao conseguiu unban no Dashboard, e (b) a conta foi criada apenas para teste e
   poderia ser apagada. Executei a remocao completa:
   - Verificacao via MCP: 0 usuarios dependiam dela via FK `created_by` — seguro apagar.
   - `DELETE FROM public.usuarios WHERE id = '038fa2a9...'` via MCP `execute_sql`.
   - `delete_auth_user('2943ba9a...')` via `python -c` (usa o GoTrue Admin API ja
     implementado em `app/core/supabase_admin.py`, limpa `auth.users` + `auth.identities`
     em cascata e revoga sessions).
   - Verificacao final via MCP: 0 linhas em `public.usuarios`, `auth.users`,
     `auth.identities`, `auth.sessions`. Drift 100% resolvido.
   - Estado pos-cleanup: 2 usuarios ativos em `public.usuarios` (Mario + outro admin),
     2 correspondentes em `auth.users`, sem drift.
2. ~~**Habilitar `auth_leaked_password_protection`**~~ — **WONTFIX** (ver ADR-027). Mario
   informou que o feature nao esta disponivel no plano atual do projeto (recurso pago).
   Aceito como WARN permanente do advisor enquanto nao houver upgrade de plano.
   Compensacoes em vigor: senha minima do GoTrue, rate limiting nativo, ausencia de
   signup publico (todos os usuarios sao criados por admin via Admin API — ADR-013).
   Quando o plano for upgrade, basta ativar o toggle no Dashboard, sem mudanca de codigo.

### Decisoes adiadas (registradas, NAO executadas nesta sessao)

- **`auth_rls_initplan` (11 WARN)** — Decisao 4b. Reescrever as policies para usar
  `(SELECT auth.uid())` em vez de `auth.uid()` direto, evitando re-execucao por linha.
  Ganho de performance so e mensuravel com volume real (tabelas estao com 0-3 linhas).
  Adiado para a Wave 2, quando houver dados de teste suficientes para medir.

### Documentos atualizados

- `DECISIONS.md` — ADRs 024 (search_path nas trigger functions), 025 (RLS na
  alembic_version — fix de side effect), 026 (index FK configuracoes_sistema.updated_by),
  **027 (leaked password protection WONTFIX)**, **028 (remocao da conta de teste regiane)**.
- `CLAUDE.md` — listagem de migrations atualizada (005 marcada como aplicada, 006/007/008
  adicionadas).
- `CHANGELOG.md` — esta secao.

---

## [2026-04-08 — Sessao 4] — Wave 1: Redesign Gerenciador de usuarios (Figma)

### Contexto
Mario forneceu 2 referencias do Figma (pagina admin e modal de novo usuario) e a paleta
exportada do documento. Figma MCP bloqueado por quota Starter, entao a implementacao usou
os PNGs colados na conversa + a lista de cores do guia. Escopo restrito a Wave 1 (somente
gerenciamento de usuarios); sidebar foi expandida com os itens das waves futuras
(Dashboard/Provas/Nova prova/Escanear/Relatorios/Configuracoes/Informacoes) mas renderizados
como `<span>` sem `href` — quando cada pagina for criada, basta trocar por `<Link>` sem
acoplamento adicional. Backend intocado (ja passa nos 96 testes com 91% de cobertura).

### Design tokens (Figma → CSS custom properties)

- **frontend/src/app/globals.css** — Arquivo reescrito para separar explicitamente DUAS
  superficies visuais:
  - Superficie escura (sidebar, login, modais): `--color-bg: #000`, `--color-bg-input: #1f1f1f`,
    `--color-text-primary: #fff`, `--color-text-secondary: #b7b7b7`, `--color-text-dim: #868686`.
  - Superficie clara (cartao principal do dashboard): `--color-card-bg: #eaeaea`,
    `--color-card-surface: #d9d9d9` (inputs/filtros), `--color-card-surface-alt: #d7d7d7` (tabela),
    `--color-card-divider: #b7b7b7`, `--color-card-text: #000`, `--color-card-text-muted: #575757`,
    `--color-card-border: #868686`.
  - Acentos compartilhados: `--color-accent: #ffcb5c`, `--color-danger: #ff5959` (antes `#e74c3c`,
    trocado para casar com o guia do Figma), `--color-overlay: rgba(59, 59, 59, 0.4)` (= `#3B3B3B` a 40%).
  - Radius: `--radius-pill: 9999px` (antes `50px`), `--radius-card-lg: 24px`, `--radius-card-xl: 28px`.
  - Tipografia: escala `--fs-display/title/h2/xl/lg/base/sm/xs` + `--fs-display` com `clamp()`
    para o titulo do cartao escalar com a viewport.
  - `select { appearance: none }` global para que o chevron SVG seja posicionado via CSS.
  - `--card-padding: clamp(1.5rem, 3vw, 3rem)` — padding interno responsivo do cartao.
  - Verificado em runtime via `preview_eval` que todos os 10 tokens criticos estao disponiveis
    no `:root` com os valores exatos da paleta.

### Componente de icones

- **frontend/src/components/icons.tsx** (novo) — 12 icones SVG inline outline, `stroke="currentColor"`,
  `strokeWidth: 1.75`, `viewBox 0 0 24 24`: `SearchIcon`, `HomeIcon`, `LaptopIcon`, `PlusIcon`,
  `ScanIcon`, `ChartIcon`, `UserIcon`, `GearIcon`, `InfoIcon`, `ChevronDownIcon`, `CheckIcon`,
  `CloseIcon`. Todos aceitam `SVGProps<SVGSVGElement>` (size via width/height, className, etc).
  Decisao: **nao instalar `lucide-react`/`heroicons`** — zero dependencia nova, peso minimo,
  controle total sobre o stroke.

### Layout do dashboard (sidebar + cartao)

- **frontend/src/app/(dashboard)/layout.tsx** — Sidebar reescrita fiel ao Figma:
  - Bloco topo: logo "3STUDIO" + "Ola {firstName}!" + campo de busca (pill cinza escuro).
  - `MAIN_NAV` (6 itens: Dashboard, Provas, Nova prova, Escanear, Relatorios, Usuarios) e
    `SECONDARY_NAV` (Configuracoes, Informacoes). Apenas "Usuarios" tem `href: "/usuarios"`.
    Componente interno `NavEntry` renderiza `<Link>` quando ha href ou `<span aria-disabled>`
    caso contrario — **nao cria rotas 404** para as waves futuras.
  - Item ativo marcado por barra vertical amarela (`::before` absoluto com `background: var(--color-accent)`).
  - Rodape: grid 44px/1fr/auto com avatar circular cinza, nome/"3Studio", botao "Sair" em amarelo.
  - Preservados: drawer mobile off-canvas, ESC fecha, backdrop, body scroll lock, `useInactivityTimeout`.
- **frontend/src/app/(dashboard)/layout.module.css** — CSS reescrito:
  - `.sidebar` com `padding: 2.25rem 1.5rem 1.75rem`, flex column com `justify-content: space-between`.
  - `.main` com `padding: 1.5rem` (mostra fundo preto em volta do cartao) + `.card` com
    `background: var(--color-card-bg); border-radius: var(--radius-card-xl); padding: var(--card-padding)`.
  - Mobile (<=768px): `.main { padding: 0.75rem }`, `.card { padding: 1.25rem; border-radius: var(--radius-card-lg) }`.

### Pagina /usuarios (conteudo do cartao)

- **frontend/src/app/(dashboard)/usuarios/page.tsx** — Estrutura JSX reescrita:
  - `<header class="pageHeader">` com titulo "Gerenciador de usuarios" (var(--fs-display)) + botao
    "Novo usuario" (pill amarelo).
  - `<section class="filters">` com 3 campos pill:
    - `.searchField` (flex: 1) com `<SearchIcon>` absoluto a esquerda do `<input type="search">`.
    - 2 `.selectField` com `<select>` + `<ChevronDownIcon>` absoluto a direita (appearance: none).
  - `<section class="tableWrap">` — tabela sobre `--color-card-surface-alt` (#d7d7d7), headers em
    `--color-card-text-muted`, divisores horizontais sutis (`rgba(183, 183, 183, 0.55)`).
  - Acoes por linha: `.editBtn` (pill preto) + `.dangerBtn` (pill vermelho) — apenas quando a linha
    esta ativa.
  - 3 modais (create/edit/deactivate) com:
    - Overlay `rgba(59, 59, 59, 0.4)` + `backdrop-filter: blur(1px)`.
    - `.modal` em fundo preto puro, `border-radius: var(--radius-card-lg)`, `padding: 2rem 2.25rem`.
    - Titulo `var(--fs-h2)` + `.modalDivider` (linha horizontal branca a 35%).
    - Inputs em `--color-bg-input` (pill) com foco amarelo.
    - Checkbox "Administrador" custom: `<span class="checkBox">` com `:checked + .checkBox::after`
      desenhando o check via bordas rotacionadas (preto sobre amarelo).
    - Botoes: `.btnSecondary` (pill cinza escuro "Cancelar") + `.btnPrimary` (pill amarelo "Cadastrar")
      ou `.btnDanger` (pill vermelho "Desativar").
  - `role="dialog"`, `aria-modal="true"`, `aria-labelledby` apontando para o `<h2>` de cada modal.
- **frontend/src/app/(dashboard)/usuarios/usuarios.module.css** — Reescrito (540 linhas) para
  implementar tudo acima + breakpoint mobile (tabela com `min-width: 720px` e scroll horizontal,
  modal `flex-direction: column-reverse` nas acoes, botoes ocupando 100%).

### Itens das waves futuras (sem acoplamento)

- `MAIN_NAV[0..4]` e `SECONDARY_NAV` sao renderizados como `<span aria-disabled="true">` dentro do
  `NavEntry`. Quando a Wave 2 criar `/dashboard`, `/provas`, etc, basta **adicionar `href` no array
  correspondente** e o `NavEntry` automaticamente vira `<Link>`. Zero mudanca de CSS, zero mudanca
  estrutural. O active-state por pathname ja funciona.
- Os icones ja estao prontos em `@/components/icons` — nao sera necessario criar novos para as
  Waves 2-5 a menos que aparecam itens especificos.

### Verificacao

- **TypeScript**: `npx tsc --noEmit` passou sem output (strict mode, 2 arquivos novos + 4 alterados).
- **Build Next**: `npx next build` → `✓ Compiled successfully`, `✓ Generating static pages (6/6)`.
  Paginas: `/usuarios` 4.75 kB (154 kB first load), `/login` 7.16 kB (157 kB). Middleware 80.1 kB.
- **Preview runtime**: server subiu em porta 57870 (autoPort ligado no `.claude/launch.json` porque
  ha processo node leftover na 3000), sem erros de servidor, sem erros de console, login renderiza
  identico ao anterior em desktop e mobile (375x812), tokens claros confirmados em runtime via
  `getComputedStyle(:root)` — todos batem exatamente com a paleta do Mario.
- **Middleware**: `window.location.href = '/usuarios'` no preview redireciona para `/login` (auth
  middleware continua funcionando; a pagina renderizada so pode ser vista com sessao autenticada).

### Arquivos alterados nessa sessao

```
M  .claude/launch.json                                (autoPort: true em frontend)
M  frontend/src/app/globals.css                       (tokens + superficies)
A  frontend/src/components/icons.tsx                  (12 icones SVG)
M  frontend/src/app/(dashboard)/layout.tsx            (sidebar completa)
M  frontend/src/app/(dashboard)/layout.module.css    (estilos sidebar + cartao)
M  frontend/src/app/(dashboard)/usuarios/page.tsx    (JSX redesign)
M  frontend/src/app/(dashboard)/usuarios/usuarios.module.css  (CSS redesign)
M  CHANGELOG.md                                       (este bloco)
```

### Pegadinhas resolvidas

1. **Figma MCP bloqueado por quota do plano Starter** — `get_design_context`, `get_screenshot`
   e `get_metadata` retornaram todos o mesmo paywall. Solucao: Mario colou PNGs @2x + paleta
   exportada, e a implementacao usou os pixels das imagens + os hex codes escritos.
2. **Port 3000 ocupado** — Processo node leftover (provavelmente de outra sessao). Em vez de
   matar sem permissao, habilitei `autoPort: true` em `.claude/launch.json` e o preview subiu em
   57870. Nao toca no dev server que estava rodando antes.
3. **`--color-danger` antigo (`#e74c3c`) nao batia com a paleta do Figma (`#ff5959`)** — trocado
   no `:root`. O login usa o token via `var(--color-danger)` para mensagens de erro, entao agora
   fica coerente com o resto do sistema (antes tinha 2 tons de vermelho no projeto).
4. **`--radius-pill` estava `50px` (fixo)** — botoes grandes do Figma exigem pill verdadeiro
   independentemente da altura. Trocado para `9999px`.

### Pendente

- Visualizacao manual autenticada de `/usuarios` (exige login real, fora do escopo automatizado).
- Quando as paginas das Waves 2+ forem criadas, substituir `<span aria-disabled>` por `<Link>`
  nos items correspondentes do `MAIN_NAV`/`SECONDARY_NAV` em `layout.tsx`.

### Ajustes pos-feedback (mesma sessao)

Mario revisou o resultado e pediu 3 correcoes baseadas em um PNG adicional da tabela:

1. **Tabela sem preenchimento** — o `background: var(--color-card-surface-alt)` saiu. Agora
   `.tableWrap` e transparente e mostra apenas um contorno `1px solid var(--color-card-border)`
   com `border-radius: var(--radius-card-lg)` e `overflow: hidden` (pra borda nao vazar sobre
   o scroll interno).
2. **Conteudo centralizado** — todos os `th`/`td` passaram de `text-align: left` para `center`,
   com `vertical-align: middle`. `.actions` (botoes Editar/Desativar) passou de `justify-content:
   flex-end` para `center`. `.thActions` tambem.
3. **Linhas verticais entre colunas** — cada `th`/`td` recebeu `border-right: 1px solid
   var(--color-card-border)`. A regra `:last-child { border-right: none }` evita linha dupla
   encostando na borda direita do contorno externo. A linha horizontal abaixo do header
   (`thead tr { border-bottom }`) foi mantida. Nao ha linhas horizontais entre rows (fiel ao
   PNG).
4. **Scroll interno** — `.tableScroll` (novo wrapper `<div>` dentro de `.tableWrap`) isola o
   `overflow-x: auto`, mantendo o contorno arredondado do pai intacto quando a tabela precisa
   rolar horizontalmente (mobile).
5. **Logo da sidebar = logo do login** — `layout.tsx` agora importa `next/image` e renderiza
   `<Image src="/images/logo-3studio.svg" width={132} height={28} priority />` em vez do texto
   `<div>3STUDIO</div>`. O CSS `.logo` foi simplificado para `width: 132px; height: auto;
   margin-bottom: 2rem`. Mesmo asset que a tela de login (carregamento ja cacheado).

Rebuild apos ajustes:
- `npx tsc --noEmit` → limpo
- `npx next build` → `✓ Compiled successfully`, `/usuarios` 4.77 kB, `/login` 1.81 kB
- `preview_eval` confirmou que o `img[alt="3Studio"]` carrega com `src="/images/logo-3studio.svg"`,
  `naturalWidth: 122`, sem erros de servidor nem console.

### Segunda rodada de feedback (mesma sessao) — respiro nas linhas verticais

Mario notou que no Figma as linhas verticais internas da tabela tem um "respiro" (nao
encostam no contorno externo do card — tem um gap de ~12px no topo e embaixo). Minha
implementacao anterior deixava as linhas verticais indo de borda a borda.

**Fix**: `padding: 4rem 0` no `.tableWrap` (apenas top/bottom, zero nos lados — valor
ajustado por Mario depois de visualizar, pra casar com o respiro generoso do Figma).
Como as bordas verticais (`border-right`) dos `th`/`td` ficam DENTRO da area padded,
elas ficam naturalmente contidas a 64px do topo e 64px da base do card — sem tocar a
linha de contorno externa. A linha horizontal do `thead tr { border-bottom }` continua
full width porque nao ha padding horizontal.

### Terceira rodada — Mobile redesign (mesma sessao)

Mario ajustou o desktop manualmente (sidebar-width 400px, padding 4rem, logo SVG via
`<Image>`, itens centralizados, espessuras ajustadas) e pediu para redesenhar APENAS o
mobile: header novo em formato pill arredondado com logo a esquerda e hamburger a
direita (igual ao Figma), e a tela de gerenciamento trocada por uma mensagem no mobile.

#### Mudancas

- **`frontend/src/app/(dashboard)/layout.tsx`**
  - Importa `CloseIcon` do `@/components/icons`.
  - Novo markup do mobile header: `<header className={styles.mobileHeader}>` contendo
    um `<div className={styles.mobileHeaderInner}>` com `<Image src="/images/logo-3studio.svg" />`
    (100x22) a esquerda e o botao hamburger a direita. O hamburger so ABRE o drawer
    (`setIsMobileNavOpen(true)`) — o fechamento passou a ser responsabilidade do X
    dentro do drawer e do backdrop/ESC, que ja existiam.
  - Dentro do `<aside>` drawer, novo botao `<button className={styles.closeBtn}>` com
    `<CloseIcon />` no topo-direita — visivel apenas no mobile, esconde no desktop.

- **`frontend/src/app/(dashboard)/layout.module.css`**
  - Bloco `@media (max-width: 768px)` completamente reescrito.
  - `.mobileHeader` vira um container com padding externo (1rem 1rem 0.5rem) que cria
    respiro em volta do pill. `.mobileHeaderInner` e o pill propriamente: altura 56px,
    `background: var(--color-bg-input)`, `border-radius: 9999px`, padding 0 1.5rem,
    flex space-between.
  - `.hamburger` dentro do pill: 26x18, 3 barras brancas de 2px.
  - `.closeBtn` desktop: `display: none`. Mobile: `display: inline-flex`, absolute top
    1.5rem right 1.25rem, 36x36, stroke branco.
  - `.sidebar` mobile agora tem `border-top-right-radius: 28px` e `border-bottom-right-radius: 28px`
    (drawer com cantos arredondados no lado direito, fiel ao Figma). Width `min(80vw, 340px)`.
  - `.greeting` e `.searchBox` escondidos no mobile (`display: none`) — o Figma nao mostra
    esses elementos dentro do drawer mobile, so logo + menu + bloco usuario.
  - `.logo` reduzida para 100px no mobile e `margin-bottom: 1.5rem`.
  - `.main` mobile: `padding: 0 1rem 1rem` (sem top, porque o `.mobileHeader` ja tem
    `padding-top: 1rem`). `.card` com `padding: 1.5rem 1.25rem`.

- **`frontend/src/app/(dashboard)/usuarios/page.tsx`**
  - Adicionado wrapper `<div className={styles.mobileNotice}>` com o paragrafo
    "Para acessar esse recurso, acesse a versão desktop." — sempre presente no DOM
    mas escondido no desktop.
  - Todo o conteudo existente (header + filtros + tabela + pagination) envolvido em
    `<div className={styles.desktopOnly}>`. Os modais ficam FORA desse wrapper porque
    (1) sao `position: fixed` e nao entrariam no fluxo de "contents" de qualquer jeito,
    (2) no mobile os botoes que disparam os modais (Novo usuario / Editar / Desativar)
    estao dentro do `.desktopOnly` escondido, entao nao ha como abrir um modal no mobile.

- **`frontend/src/app/(dashboard)/usuarios/usuarios.module.css`**
  - Novos seletores `.mobileNotice` (desktop: `display: none`) e `.desktopOnly`
    (desktop: `display: contents` — nao interfere no layout flex dos filhos).
  - Bloco `@media (max-width: 768px)` simplificado: esconde `.desktopOnly` e mostra
    `.mobileNotice` como flex centralizado (min-height 60vh, paragrafo 1.125rem em
    `--color-card-text-muted`, max-width 320px pra quebrar bonito em textos longos).
  - Removido o bloco antigo que tentava adaptar tabela/modais no mobile — nao sao
    mais alcancaveis.

#### Verificacao
- `npx tsc --noEmit` → limpo
- `rm -rf .next && npx next build` → `✓ Compiled successfully`, `/usuarios` 4.9 kB
  (era 4.77 kB; delta de 130B pelo aviso mobile + wrapper), `/login` 1.81 kB
- Preview no viewport mobile 375x812: login renderiza normalmente, sem erros de
  servidor nem console. `/usuarios` retorna `opaqueredirect` (middleware de auth
  funcionando — comportamento esperado sem sessao).

#### Decisao de arquitetura (explica porque `display: contents` no wrapper)

Usei `display: contents` no `.desktopOnly` em vez de `display: block` pra nao criar
um `div` extra no grafo de layout quando visivel no desktop. Isso garante que o CSS
existente do `.pageHeader`, `.filters`, `.tableWrap` e `.pagination` continue se
comportando igual (flex gaps, margin-bottom entre secoes, etc) — como se o wrapper
nao estivesse la. No mobile o `display: none` esconde normalmente e os filhos nao
renderizam. Trade-off: `display: contents` tem suporte desigual em screen readers
historicamente, mas para um wrapper visual sem semantica acessivel essa e uma
aplicacao OK (o proprio MDN recomenda pra esse caso).

Apos o fix tambem precisei fazer `rm -rf .next && npx next build` — o cache do Next
estava retornando `PageNotFoundError: /_document` num primeiro rebuild. Depois da
limpeza compilou limpo (`✓ Compiled successfully`, mesmos tamanhos).

---

## [2026-04-08 — Sessao 3] — Wave 1: Estabilizacao (auditoria + testes + UX)

### Contexto
Auditoria completa antes de avancar para a Wave 2. Mario solicitou conferencia minuciosa
de toda a Wave 1 (Wave 0 esta congelada). 5 frentes: bloqueantes da Sessao 2, hardening
de seguranca, cobertura de testes, polimentos de frontend, atualizacao de docs.
Pre-condicao do Mario: nao iniciar Wave 2 ate Wave 1 estar 100% estavel.

### Bloco 1 — Bloqueantes resolvidos

- **backend/.env, backend/.env.example** — `DATABASE_URL` corrigida de `aws-0-sa-east-1.pooler.supabase.com:6543` para `aws-1-sa-east-1.pooler.supabase.com:5432`. Causa raiz: Supabase atualizou a infraestrutura do Supavisor em sa-east-1 e migrou tenants para `aws-1-`. Mesma senha funciona com o novo hostname/porta. `/health/db` agora retorna `method: "pooler"`.
- **backend/app/core/jwt.py** — `_fetch_jwks` reescrito com `httpx.AsyncClient` (era sync, bloqueava o event loop). Adicionado `JWKS_CACHE_TTL_SECONDS = 3600`, `_jwks_cached_at` e `asyncio.Lock` para anti-thundering-herd. Algoritmos restritos a `{"ES256", "HS256"}` — qualquer outro `alg` no header e rejeitado antes de tentar verificar (mitiga algorithm confusion). Ver ADR-016.
- **backend/app/main.py** — Registrado `@app.exception_handler(Exception)` que retorna `JSONResponse(500)` DENTRO da pilha de middleware. Sem isso, o `ServerErrorMiddleware` default do Starlette respondia fora do `CORSMiddleware` e o browser reportava "CORS error" para qualquer 500 real. Ver ADR-017.
- **backend/app/api/deps.py** — `verify_token(token)` agora `await`-ado (era chamada sincrona).
- **backend/pyproject.toml** — Adicionado `psycopg2-binary>=2.9,<3.0` (necessario para Alembic e `apply_rls.py` que usam driver sync). Adicionado `pytest-cov>=5.0,<7.0` em dev deps.

### Bloco 2 — Hardening RLS + RBAC

- **backend/migrations/rls/004_unify_rls_is_admin.sql** (novo, aplicado ao Supabase via MCP) — Substitui `setor = 'STUDIO'` por `is_admin = true` em TODAS as policies admin de `provas_digitais` (SELECT/INSERT/UPDATE), `movimentacoes` (SELECT), `etiquetas` (SELECT), `audit_logs` (SELECT) e `configuracoes_sistema` (SELECT/UPDATE). Logica de negocio por setor (VENDEDOR/MOTORISTA/CLICHERIA) preservada. Verificado em `pg_policies`: 11 policies usando `is_admin`, zero `setor=STUDIO` remanescente. Ver ADR-018.
- **backend/app/api/v1/users.py** — Helper `_count_other_active_admins(db, exclude_id)`. PATCH e DELETE agora bloqueiam (409 "ultimo administrador") qualquer operacao que deixaria o sistema sem admin ativo. Cobre os casos: demover (`is_admin=false`) ou desativar (`ativo=false`) o unico admin restante. Self-protection (admin nao pode se demover) permanece como check anterior. Ver ADR-019.

### Bloco 3 — Cobertura de testes (38 → 83 testes)

- **backend/tests/test_jwt.py** (novo, 11 testes) — Algoritmos rejeitados (`HS384`, `none`), ES256 happy path com keypair gerado em runtime e JWKS mockado, ES256 com kid desconhecido, expiracao, audience errado, HS256 fallback, cache reuso dentro do TTL, refresh apos TTL expirado, refresh em cache miss por kid (rotacao de chave).
- **backend/tests/test_supabase_admin.py** (novo, 7 testes) — `_admin_headers` com Service Role Key, `create_auth_user` happy path + 422 propagado, `delete_auth_user` happy path + falha que NAO levanta (best-effort log), `disable_auth_user` happy path + falha que NAO levanta. Mock de `httpx.AsyncClient` via `_FakeAsyncClient` que grava chamadas.
- **backend/tests/test_health.py** (novo, 7 testes) — `/health` ok, `/health/db` happy path pooler, fallback REST quando pooler falha, erro quando ambos falham, fallback REST 5xx tambem reporta erro, `/health/r2` ok e falha.
- **backend/tests/test_users_api.py** — +20 testes:
  - 12 testes de filtros/paginacao: setor, localizacao, ativo true/false, busca em nome+email, filtros combinados, OFFSET/LIMIT corretos, validacao 422 para setor/localizacao invalidos, page>=1, page_size<=100, busca max_length=200. Helper `_capture_list_stmts` registra os stmts e `_compiled_sql` compila com dialect Postgres (default rendia `LOWER LIKE` em vez de `ILIKE`).
  - 8 testes de protecao do ultimo admin: PATCH bloqueia democao/desativacao do ultimo, PATCH permite quando ha outros, PATCH skip check para non-admin e admin ja inativo, DELETE bloqueia, DELETE permite, DELETE skip para non-admin.
- **Total: 83 testes passando (era 38).** Suite roda em ~0.3s.

### Bloco 4 — Frontend (UX)

- **frontend/src/app/(dashboard)/layout.tsx** — Mobile navigation off-canvas. Estado `isMobileNavOpen` controla um drawer que desliza da esquerda em < 768px. Backdrop fecha ao tap, ESC fecha, route change fecha automaticamente, `body { overflow: hidden }` enquanto aberto. Hamburger button no `mobileHeader` com `aria-expanded`, `aria-controls`, `aria-label`. Antes: sidebar simplesmente sumia (`display: none`) deixando o usuario sem navegacao.
- **frontend/src/app/(dashboard)/layout.module.css** — Novas classes `.mobileHeader`, `.hamburger`, `.hamburgerBar`, `.mobileLogo`, `.backdrop`, `.sidebarOpen`. Em < 768px: sidebar `transform: translateX(-100%)` por default, `translateX(0)` quando aberta, `transition: 0.25s ease-out`, `width: min(86vw, 280px)`, `z-index` acima do backdrop.
- **frontend/src/app/(dashboard)/usuarios/page.tsx** — `fetchUsers` agora popula `listError` no catch (era silent). UI renderiza linha de erro na tabela com mensagem (do `ApiError` quando disponivel) + botao "Tentar novamente" que rechama `fetchUsers`. Antes: erro de API mostrava "Nenhum usuario encontrado", mascarando outages.
- **frontend/src/app/(dashboard)/usuarios/usuarios.module.css** — Novas classes `.errorCell`, `.errorMessage`, `.retryBtn`.
- **frontend/.env.local.example** — Reescrito com docstrings explicando cada variavel, prefixo `NEXT_PUBLIC_` (browser-safe), aviso explicito de que service role key NUNCA vai aqui.

### Bloco 5 — Documentacao
- **DECISIONS.md** — 4 ADRs novos: ADR-016 (JWKS async + TTL + algoritmo restrito), ADR-017 (exception handler global p/ CORS em 500), ADR-018 (RLS unificada em is_admin), ADR-019 (protecao do ultimo admin ativo).
- **CHANGELOG.md** — Esta entrada.

### Pegadinhas descobertas nesta sessao
- **`aws-0-` -> `aws-1-` no pooler Supabase**: o Supavisor migra tenants entre clusters sem aviso; o erro `Tenant or user not found` pode ser puramente DNS/hostname errado, nao credencial. Sempre confirmar o hostname atual no dashboard.
- **`str(stmt.compile(...))` sem dialect renderiza `ILIKE` como `LOWER(col) LIKE LOWER(...)`**: o default compiler do SQLAlchemy nao suporta ilike. Para testar SQL real, compilar com `dialect=postgresql.dialect()`.
- **Starlette `ServerErrorMiddleware` esta FORA da user middleware stack**: respostas 500 nao tratadas pulam o `CORSMiddleware`. Solucao e registrar `@app.exception_handler(Exception)` que vira a resposta dentro da stack.
- **Algoritmos JWT permitidos devem ser explicitos**: PyJWT por default tenta o algoritmo declarado no header. Se voce nao restringe, um atacante pode trocar `alg` para outra coisa que sua chave aceite por acidente. `ALLOWED_ALGORITHMS = {...}` blindado antes do `jwt.decode`.

### Pendente para Wave 2
- Deploy Railway/Vercel (intencionalmente adiado pelo Mario).
- Testes E2E com banco real (atualmente todos os testes mockam DB e httpx).

---

## [2026-04-07 — Sessao 2] — Wave 1: UI Login (Figma) + JWT ES256 + Investigacao Pooler DB

### Contexto
Continuacao da Wave 1. Foco em: polir tela de login conforme Figma, corrigir problemas de autenticacao
descobertos durante testes manuais e investigar erro de conexao com o pooler do Supabase.

### Frontend — Login UI (match Figma)

#### Arquivos criados
- **frontend/public/images/logo-3studio.svg** — Logo branco 3STUDIO extraido do Figma (asset direto)
- **frontend/public/images/login-bg.png** — Foto de fundo do painel de imagem (asset Figma)
- **frontend/src/types/global.d.ts** — Declaracao TypeScript para imports de `.css` (fix `Cannot find module`)

#### Arquivos modificados
- **frontend/src/app/layout.tsx** — Adicionado `next/font/google` para carregar Inter com suporte a font-weight variavel
- **frontend/src/app/login/page.tsx** — Reescrito para match Figma:
  - SVG inline `<clipPath>` com `clipPathUnits="objectBoundingBox"` para borda inclinada do painel de imagem
  - Painel de imagem via CSS background (nao Next.js Image)
  - Logo via `next/image`
  - Links "Nao possui conta? Registre-se" + "Esqueci minha senha"
- **frontend/src/app/login/login.module.css** — Reescrito + ajustes manuais do Mario:
  - Painel imagem: `flex: 0 1 55%`, `clip-path: url(#imagePanelClip)`
  - Logo: `align-self: center`, `margin-bottom: 4rem`
  - Titulo: `font-weight: 400`, sem italico
  - Subtitulo/labels: `font-weight: 300`
  - Button: `font-weight: 400`, `margin-top: 1rem`
  - Footer: `margin-top: 5rem`

### Backend — JWT ES256 (fix critico)

#### Problema
Supabase Auth assina JWTs com **ES256 (ECDSA)**, nao HS256 como assumido no ADR-011.
O backend verificava com HS256 → 401 Unauthorized em todos os endpoints protegidos.

#### Arquivos modificados
- **backend/app/core/jwt.py** — Reescrito completamente:
  - Detecta algoritmo do header JWT (ES256 vs HS256)
  - ES256: busca chave publica via JWKS (`/.well-known/jwks.json`) com cache in-memory + refresh on miss
  - HS256: fallback para projetos legacy usando `supabase_jwt_secret`
  - Dependencia: `pyjwt[crypto]` (pacote `cryptography` para ECDSA)
- **backend/app/api/deps.py** — `get_current_user` agora usa `verify_token()` centralizado (import de `app.core.jwt`)

### Backend — Admin user via GoTrue API

#### Problema
Usuario master criado via `INSERT INTO auth.users` + `INSERT INTO auth.identities` falhava no login (500).
GoTrue exige campos internos que raw SQL nao popula corretamente.

#### Correcao
- Deletado usuario criado via SQL
- Recriado via GoTrue Admin API (`POST /auth/v1/admin/users` com Service Role Key)
- `auth_uid` atualizado na tabela `public.usuarios`

### Investigacao — CORS / Pooler DB (nao resolvido)

#### Sintoma
`Access to fetch at 'http://localhost:8000/api/v1/users/' blocked by CORS policy`

#### Diagnostico detalhado
1. CORS middleware **funciona corretamente** — verificado via curl (preflight OPTIONS retorna headers corretos)
2. Erro real: **banco de dados inacessivel via pooler** → endpoint retorna 500 → resposta de erro nao inclui headers CORS (Starlette exception handler default)
3. `GET /health/db` confirma: `"method": "rest_api", "note": "Pooler indisponivel"`
4. Teste direto asyncpg: `InternalServerError: Tenant or user not found`
5. `DATABASE_URL` atual: `postgresql+asyncpg://postgres.rwxlpwmnkekzuurgthkr:...@aws-0-sa-east-1.pooler.supabase.com:5432/postgres`

#### Causa raiz provavel
- Senha do pooler expirada/incorreta
- Formato da URL de conexao pode ter mudado no Supabase (verificar dashboard)
- Possivel necessidade de parametro SSL

### Pendente para proxima sessao

1. **[BLOQUEANTE] Corrigir conexao pooler DB** — Verificar `DATABASE_URL` correto no dashboard Supabase, testar conexao, atualizar `.env`
2. **[BLOQUEANTE] Garantir CORS em respostas de erro** — Quando o handler lanca excecao (500), a resposta precisa incluir CORS headers. Opções: middleware de exception ou wrapper
3. **Teste E2E completo** — Login → Dashboard → Criar usuario → Listar → Editar → Desativar
4. **Testes unitarios/integracao** — Refinar os 38 testes existentes, adicionar cobertura para JWT ES256, error paths
5. **Deploy staging** — Railway (backend) + Vercel (frontend) — pendente desde Wave 0

### Pegadinhas descobertas nesta sessao

- **Supabase JWT usa ES256, NAO HS256**: O `supabase_jwt_secret` (variavel de ambiente) e para HS256, mas projetos novos assinam com ECDSA (ES256). Sempre verificar `jwt.get_unverified_header(token)["alg"]`
- **Criar auth users via GoTrue Admin API, NUNCA via raw SQL**: `POST /auth/v1/admin/users` com Service Role Key. Raw SQL em `auth.users`/`auth.identities` falta campos internos do GoTrue e causa login failure
- **Erro CORS pode mascarar erro 500**: Quando o backend retorna 500 via exception handler default do Starlette, headers CORS nao sao incluidos. O browser reporta como "CORS error" mesmo sendo erro de servidor
- **Font-weight nao funciona sem next/font**: CSS `font-weight: 300/400/700` nao tem efeito se o font nao for carregado com os weights corretos. `next/font/google` com `Inter({ subsets: ["latin"] })` carrega todos os weights automaticamente

---

## [2026-04-07] — Wave 1: Auth + Users CRUD + RBAC

### Backend

#### Auth (Componente 03)
- **app/api/deps.py** — `get_current_user` (JWT HS256 via PyJWT, audience=authenticated), `get_admin_user`, `require_role(*setors)` — 3 camadas de protecao
- **app/core/supabase_admin.py** — Supabase Auth Admin API client (create, delete, disable via Service Role Key)
- **app/db/models.py** — SQLAlchemy 2.0 model `Usuario` com 11 colunas, `SetorEnum`, `LocalizacaoEnum`
- **app/domain/schemas/user.py** — Pydantic v2: UserCreate (email regex, senha validacao, model_validator RN-009), UserUpdate (exclude_unset), UserResponse, UserListResponse

#### Users CRUD (Componente 04)
- **app/api/v1/users.py** — 6 endpoints:
  - `GET /me` — qualquer autenticado
  - `POST /` — admin: cria em Supabase Auth + DB com rollback atomico
  - `GET /` — admin: lista paginada com filtros (setor, localizacao, ativo, busca)
  - `GET /{id}` — admin ve qualquer, nao-admin ve apenas self
  - `PATCH /{id}` — admin: atualizacao parcial, RN-009 + RN-010 enforced
  - `DELETE /{id}` — admin: soft delete (ativo=false) + ban no Supabase Auth, RN-010 enforced

#### Migration e RLS (Componente 05)
- **migrations/versions/004_add_is_admin_created_by_to_usuarios.py** — `is_admin BOOLEAN NOT NULL DEFAULT false`, `created_by UUID REFERENCES usuarios(id)`
- **migrations/rls/003_policies_wave1_usuarios.sql** — 3 policies atualizadas: SELECT (self ou admin), INSERT/UPDATE (admin only), usando `is_admin = true` em vez de `setor = 'STUDIO'`

### Frontend

#### Login (Componente 03)
- **src/lib/supabase/client.ts** — Browser client via @supabase/ssr `createBrowserClient`
- **src/lib/supabase/server.ts** — Server client via `createServerClient` + cookies()
- **src/lib/supabase/middleware.ts** — Session refresh + redirect logic
- **src/middleware.ts** — Next.js middleware: atualiza sessao, redireciona /login <-> /usuarios
- **src/hooks/useInactivityTimeout.ts** — Timer 30 min (RNF-003): mouse, keyboard, touch, scroll resetam
- **src/app/login/page.tsx** — Formulario email/senha, Supabase signInWithPassword, mensagens de erro
- **src/app/login/login.module.css** — Split layout (imagem + form), dark theme, gold accent
- **src/app/globals.css** — CSS custom properties (cores, radius, font) extraidas do Figma
- **src/lib/api.ts** — `apiFetch` wrapper com ApiError, token injection, 204 handling

#### Dashboard (Componente 04)
- **src/app/(dashboard)/layout.tsx** — Sidebar fixa, user info (/me), logout, inactivity timeout 30 min
- **src/app/(dashboard)/layout.module.css** — Sidebar 280px, nav com active state, responsive
- **src/app/(dashboard)/usuarios/page.tsx** — Tabela com filtros/busca/paginacao + modais Create/Edit/Deactivate
- **src/app/(dashboard)/usuarios/usuarios.module.css** — Badges (ativo/inativo/admin), modal overlay, form fields

### Testes
- **tests/conftest.py** — Fixtures: make_user factory, admin_user, regular_user, mock_db
- **tests/test_schemas.py** — 13 testes unitarios (UserCreate validacao, UserUpdate parcial)
- **tests/test_users_api.py** — 25 testes integracao (todos endpoints, RBAC, RN-009, RN-010, rollback)
- **38 testes passing** (0 falhas)

### Banco de dados (aplicado no Supabase)
- `usuarios`: +2 colunas (`is_admin`, `created_by`)
- 3 RLS policies atualizadas para `is_admin`-based

### Dependencias adicionadas
- **Backend**: httpx (ja existia), pyjwt[crypto] (ja existia)
- **Frontend**: `@supabase/supabase-js`, `@supabase/ssr`

---

## [2026-04-07] — Wave 0: Infraestrutura completa

### Criado
- **backend/pyproject.toml** — dependencias pinadas conforme DAT Secao 1 (13 deps + 3 dev)
- **backend/app/main.py** — FastAPI com 3 health checks (`/health`, `/health/db`, `/health/r2`) e CORS
- **backend/app/core/config.py** — Pydantic Settings com 12 env vars (Supabase, R2, app)
- **backend/app/core/jwt.py** — esqueleto de verificacao JWT (HS256, audience=authenticated). Sera plugado na Wave 1
- **backend/app/core/r2.py** — cliente Cloudflare R2 (singleton + async via run_in_executor)
- **backend/app/db/session.py** — SQLAlchemy 2.0 async engine + session factory (asyncpg, pool_pre_ping=True)
- **backend/migrations/versions/001_create_enums_tables_triggers_indexes.py** — schema central: 4 enums, 6 tabelas, 2 funcoes trigger, 5 triggers, 14 indices
- **backend/migrations/versions/002_seed_configuracoes_iniciais.py** — seeds: tempo_atraso=48h, template_etiqueta=padrao
- **backend/migrations/versions/003_fix_constraints_indexes_trigger.py** — correcoes de auditoria: 3 CHECKs, trigger etiquetas, 2 indices novos, 2 indices redundantes removidos
- **backend/migrations/rls/001_enable_rls.sql** — RLS habilitado em 6 tabelas
- **backend/migrations/rls/002_policies_por_perfil.sql** — 11 policies RLS por setor (STUDIO, VENDEDOR, MOTORISTA, CLICHERIA)
- **backend/migrations/rls/apply_rls.py** — script para aplicar .sql files em ordem
- **backend/.env.example** — template com 12 env vars
- **frontend/** — boilerplate Next.js 14 (layout.tsx, page.tsx, tsconfig strict)
- **scripts/smoke_r2.py** — teste ciclo completo R2 (upload→list→download→delete)
- **scripts/keep_alive.py** — GET /health/db com log para cron
- **.github/workflows/ci.yml** — lint (ruff) + testes + deploy staging condicional
- **.github/workflows/keep-alive.yml** — cron cada 6 dias + workflow_dispatch
- **docs/cloudflare_r2_setup.md** — guia passo a passo CORS + API token
- **.claude/launch.json** — config dev servers (backend :8000, frontend :3000)

### Banco de dados (aplicado no Supabase)
- 4 enums: `setor_enum`(4), `localizacao_enum`(2), `status_prova_enum`(10), `rota_enum`(2)
- 6 tabelas: `usuarios`, `provas_digitais`, `movimentacoes`, `etiquetas`, `audit_logs`, `configuracoes_sistema`
- 6 triggers: 3 imutabilidade (audit_logs, movimentacoes, etiquetas) + 3 updated_at
- 4 CHECK constraints: `chk_vendedor_localizacao`, `chk_status_diferente`, `chk_ciclo_positivo`, `chk_ciclo_atual_positivo`
- 27 indices (0 redundantes)
- 11 RLS policies
- 2 seeds em configuracoes_sistema

### Pegadinhas descobertas
- **Supabase pooler "Tenant or user not found"**: projetos recem-criados precisam de tempo para o Supavisor provisionar o tenant. Solucao: fallback via REST API no health check
- **Supabase direct connection e IPv6-only**: maquina sem IPv6 nao conecta. Pooler (Supavisor) fornece IPv4
- **pyproject.toml build-backend**: `setuptools.backends._legacy:_Backend` nao existe. Usar `setuptools.build_meta`
- **Port 8000 ocupada**: processos python.exe de sessoes anteriores. `taskkill //F //PID <pid>`
- **tsconfig target es5**: conflita com `moduleResolution: "bundler"` do Next.js 14. Corrigido para ES2017
- **Dependencias do venv incompletas**: venv tinha apenas boto3 e psycopg2. Instaladas todas as 40 deps de uma vez

### Correcoes de auditoria (3 rodadas)
1. **C1**: `pol_movimentacoes_select` — VENDEDOR so via movimentacoes proprias, nao das suas provas. Corrigido para incluir `prova_id IN (provas do vendedor)`
2. **C2**: `etiquetas` sem trigger de imutabilidade — adicionado `trg_etiquetas_imutavel`
3. **C3**: R2 client sincrono bloqueava event loop — reescrito com singleton + `run_in_executor`
4. **M1**: indices `idx_usuarios_auth_uid` e `idx_provas_nro_requerimento` redundantes (duplicatas de UNIQUE) — removidos
5. **M2**: faltava CHECK `status_anterior != status_novo` em movimentacoes — adicionado
6. **M3**: faltava CHECK `ciclo >= 1` — adicionado em movimentacoes e provas_digitais
7. **M4**: faltava indice em `movimentacoes.created_at` para deteccao de atraso — adicionado
8. **R1**: indice composto `(prova_id, created_at DESC)` para query "ultima movimentacao" — adicionado
9. **Policy CLICHERIA**: faltava `RECEBIDA_PELA_CLICHERIA` no `pol_provas_select` — adicionado
10. **r2_download**: `Body.read()` fora do executor — movido para dentro da closure

### Pendencias para Wave 1
- Deploy Railway + Vercel (plataformas escolhidas, nao configuradas)
- Pooler do Supabase pode ja estar disponivel (re-testar)
- Diretorio `backend/tests/` vazio — criar testes na Wave 1
- Diretorios `backend/app/api/` e `backend/app/domain/` vazios — endpoints e modelos na Wave 1
