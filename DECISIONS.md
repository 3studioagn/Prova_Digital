# Decisoes Tecnicas (ADR Simplificado)

---

## ADR-001 — PyJWT em vez de python-jose
**Data:** 2026-04-07
**Contexto:** Precisamos verificar JWTs emitidos pelo Supabase Auth no backend.
**Decisao:** Usar PyJWT >= 2.8 com extras `[crypto]`.
**Alternativas:** python-jose (popular mas com CVEs conhecidas e mantenedor inativo).
**Consequencias:** Dependencia mais segura e mantida. Requer `cryptography` como sub-dep.

---

## ADR-002 — Cloudflare R2 em vez de Supabase Storage
**Data:** 2026-04-07
**Contexto:** Armazenamento de imagens de artes (provas digitais) com custo previsivel.
**Decisao:** Cloudflare R2 via boto3 (S3-compatible). Bucket: `rastreio-provas-artes`.
**Alternativas:** Supabase Storage (integrado, mas limites de banda no free tier).
**Consequencias:** Egress gratis no R2. Requer configuracao separada de CORS e API token no dashboard Cloudflare.

---

## ADR-003 — Supabase Auth como fonte de verdade para identidade
**Data:** 2026-04-07
**Contexto:** Autenticacao de usuarios do sistema.
**Decisao:** Supabase Auth gerencia auth.users e emite JWTs. O backend NUNCA emite tokens — apenas verifica com PyJWT. A tabela `public.usuarios` espelha perfil da app (setor, localizacao, ativo) e referencia `auth.users` via `auth_uid` sem FK (Alembic nao toca auth.*).
**Alternativas:** Auth proprio com FastAPI (mais controle, muito mais complexidade).
**Consequencias:** Login/signup delegados ao Supabase. Backend precisa de `supabase_jwt_secret` para verificar tokens.

---

## ADR-004 — Separacao Alembic (dominio) vs Supabase (auth)
**Data:** 2026-04-07
**Contexto:** Migrations precisam coexistir com o schema gerenciado pelo Supabase.
**Decisao:** Alembic gerencia APENAS `public.*` (tabelas de dominio). Tabelas `auth.*` sao intocaveis. RLS policies sao versionadas como `.sql` em `backend/migrations/rls/` e aplicadas separadamente.
**Alternativas:** Usar Supabase migrations (menos controle, lock-in).
**Consequencias:** Dois mecanismos de migration coexistindo. Requer disciplina para nunca referenciar auth.* em Alembic.

---

## ADR-005 — CSS Modules (sem framework CSS externo)
**Data:** 2026-04-07
**Contexto:** Estilizacao do frontend Next.js.
**Decisao:** CSS Modules nativo do Next.js. Sem Tailwind, Bootstrap ou similares.
**Alternativas:** Tailwind CSS (rapido, mas gera classes utilitarias que dificultam leitura).
**Consequencias:** CSS mais verboso, mas colocado e tipado. Sem dependencia externa.

---

## ADR-006 — Keep-alive via GitHub Actions cron
**Data:** 2026-04-07
**Contexto:** Supabase free tier pausa projetos inativos apos 7 dias.
**Decisao:** GitHub Actions cron a cada 6 dias (`0 8 */6 * *`) executa `scripts/keep_alive.py` que faz GET em `/health/db`.
**Alternativas:** APScheduler no backend (requer backend sempre ligado — impossivel no free tier).
**Consequencias:** Depende do GitHub Actions estar disponivel. Margem de 1 dia para falhas.

---

## ADR-007 — Health check /health/db com fallback REST API
**Data:** 2026-04-07 (sessao)
**Contexto:** Pooler do Supabase (Supavisor) retorna "Tenant or user not found" para projetos recem-criados. Delay de provisionamento pode levar horas.
**Decisao:** `/health/db` tenta pooler (SQLAlchemy async) primeiro. Se falhar, tenta Supabase REST API (`GET /rest/v1/` com anon key). Se status < 500, banco esta ativo.
**Alternativas:** Esperar pooler ficar disponivel (inaceitavel para CI).
**Consequencias:** Health check sempre funciona mesmo com pooler indisponivel. Campo `method` na resposta indica qual caminho foi usado.

---

## ADR-008 — R2 client singleton + run_in_executor
**Data:** 2026-04-07 (sessao, auditoria)
**Contexto:** boto3 e sincrono. Em FastAPI async, chamadas bloqueiam o event loop.
**Decisao:** Cliente boto3 como singleton global. Todas as operacoes async (r2_upload, r2_download, r2_delete) usam `asyncio.run_in_executor` para rodar no thread pool.
**Alternativas:** aioboto3 (wrapper async, mas menos estavel e com bugs conhecidos).
**Consequencias:** Thread pool default do asyncio e suficiente para o volume esperado. Se escalar, considerar executor dedicado.

---

## ADR-009 — Trigger de imutabilidade em etiquetas
**Data:** 2026-04-07 (sessao, auditoria)
**Contexto:** Etiquetas sao snapshots para impressao (RF-003). Se alteradas apos geracao, comprometem rastreabilidade.
**Decisao:** Adicionar trigger `trg_etiquetas_imutavel` com a mesma `fn_bloquear_alteracao()` usada em movimentacoes e audit_logs.
**Alternativas:** Confiar na camada de aplicacao (insuficiente — acesso direto ao banco bypassaria).
**Consequencias:** 3 tabelas imutaveis no banco: movimentacoes, audit_logs, etiquetas.

---

## ADR-010 — Deploy: Railway (backend) + Vercel (frontend)
**Data:** 2026-04-07 (sessao)
**Contexto:** Escolha de plataforma para deploy do MVP.
**Decisao:** Railway free tier para o backend FastAPI. Vercel free tier para o frontend Next.js.
**Alternativas:** Fly.io (backend), Netlify (frontend).
**Consequencias:** Configuracao de deploy a ser feita na Wave 1. Railway suporta Dockerfile ou buildpack Python.

---

## ADR-011 — ~~JWT HS256 com supabase_jwt_secret (sem JWKS)~~ SUPERSEDED por ADR-014
**Data:** 2026-04-07 (Wave 1)
**Status:** SUPERSEDED — Supabase usa ES256 (ECDSA), nao HS256. Ver ADR-014.
**Contexto:** Verificacao de JWTs no backend. Supabase fornece JWT secret (HS256) e tambem JWKS endpoint (RS256).
**Decisao original:** Usar HS256 com `supabase_jwt_secret` direto.
**Motivo da supersessao:** Descoberto durante testes manuais que o Supabase assina JWTs com ES256 (ECDSA), nao HS256. O `supabase_jwt_secret` funciona apenas para verificacao HS256. Projetos novos do Supabase usam ES256 por padrao.

---

## ADR-012 — Enums compartilhados entre SQLAlchemy e Pydantic
**Data:** 2026-04-07 (Wave 1)
**Contexto:** `SetorEnum` e `LocalizacaoEnum` usados tanto no ORM quanto na validacao de API.
**Decisao:** Definir enums em `app/db/models.py` (junto ao model) e importar em `app/domain/schemas/user.py`. Fonte unica de verdade.
**Alternativas:** Duplicar enums em cada camada (risco de divergencia), ou criar modulo separado `app/core/enums.py`.
**Consequencias:** Schemas dependem de models.py, mas evita qualquer divergencia entre camadas.

---

## ADR-013 — Supabase Auth Admin API para gerenciamento de usuarios
**Data:** 2026-04-07 (Wave 1)
**Contexto:** Criacao/desativacao de usuarios precisa manter auth.users sincronizado com public.usuarios.
**Decisao:** Backend usa Service Role Key via httpx para chamar `/auth/v1/admin/users`. Criacao: 1) Supabase Auth, 2) app DB, rollback Auth se DB falhar. Desativacao: soft delete + ban (876600h).
**Alternativas:** Trigger Supabase (Database Webhooks) ou Edge Function.
**Consequencias:** Rollback atomico no create. Service Role Key fica apenas no backend (nunca frontend). Ban garante que tokens existentes nao sao renovados apos desativacao.

---

## ADR-014 — JWT ES256 via JWKS (substitui ADR-011)
**Data:** 2026-04-07 (Wave 1, Sessao 2)
**Contexto:** Supabase projetos novos usam ES256 (ECDSA) para assinar JWTs, nao HS256 como documentado em algumas fontes. Descoberto via `jwt.get_unverified_header(token)["alg"] == "ES256"` durante debug de 401.
**Decisao:** `app/core/jwt.py` detecta o algoritmo do header do token:
  - **ES256**: busca chave publica via JWKS endpoint (`{supabase_url}/auth/v1/.well-known/jwks.json`), cache in-memory com refresh on miss (suporta rotacao de chave)
  - **HS256**: fallback usando `supabase_jwt_secret` (projetos legacy)
**Alternativas:** Forcar HS256 (impossivel — Supabase nao oferece opcao de escolher algoritmo).
**Consequencias:** Requer `pyjwt[crypto]` (sub-dep `cryptography` para ECDSA). JWKS cache evita chamada HTTP a cada request. Refresh automatico cobre rotacao de chaves.

---

## ADR-015 — Nunca criar auth users via raw SQL
**Data:** 2026-04-07 (Wave 1, Sessao 2)
**Contexto:** Tentativa de criar usuario admin via `INSERT INTO auth.users` + `INSERT INTO auth.identities` resultou em login failure (500). GoTrue exige campos internos (`aud`, `role`, `confirmation_token`, etc) que nao sao documentados para insercao manual.
**Decisao:** Sempre usar GoTrue Admin API (`POST /auth/v1/admin/users` com Service Role Key) para criar usuarios em `auth.*`. Nunca manipular tabelas `auth.*` diretamente via SQL.
**Alternativas:** Descobrir e popular todos os campos internos do GoTrue (fragil, muda entre versoes).
**Consequencias:** Depende da Service Role Key e do endpoint Admin do Supabase. Garante compatibilidade com qualquer versao do GoTrue.

---

## ADR-016 — JWKS fetch async + TTL + algoritmo restrito
**Data:** 2026-04-08 (Wave 1, Sessao 3 — estabilizacao)
**Contexto:** A primeira versao do `app/core/jwt.py` (ADR-014) tinha 3 problemas detectados em auditoria:
  1. `_fetch_jwks` usava `httpx.Client` sincrono dentro de funcao chamada via `await` — bloqueava o event loop a cada request frio (quando o cache estava vazio ou kid invalido).
  2. Cache JWKS sem TTL — uma vez populado, so refrescava em cache miss por kid. Em caso de chave revogada (nao apenas rotacionada), o backend continuaria aceitando assinaturas antigas indefinidamente.
  3. `verify_token` aceitava qualquer algoritmo que o PyJWT entendesse (inclusive `none`) — abria espaco para algorithm confusion attacks.
**Decisao:**
  - Reescrever `_fetch_jwks` com `httpx.AsyncClient` (mesmo padrao do `supabase_admin.py`).
  - Adicionar `JWKS_CACHE_TTL_SECONDS = 3600` e `_jwks_cached_at` — refresh proativo a cada hora alem do refresh on-miss.
  - `asyncio.Lock` para evitar thundering herd no primeiro fetch e nos refreshes.
  - `ALLOWED_ALGORITHMS = {"ES256", "HS256"}` — qualquer outro `alg` no header levanta `InvalidTokenError` antes mesmo de tentar verificar.
**Alternativas:**
  - Cache permanente sem TTL (rejeitado: chave revogada continuaria aceita).
  - Fetch sem lock (rejeitado: N coroutines paralelas dispararem N requisicoes na primeira chamada).
  - `aiohttp` para JWKS (rejeitado: ja temos httpx no projeto).
**Consequencias:** O event loop nunca bloqueia em verificacao de JWT. Chaves revogadas sao detectadas em ate 1h. Algoritmo confusion attacks (`alg: none`, `alg: HS256` com chave RSA, etc) sao bloqueados explicitamente.

---

## ADR-017 — Exception handler global para garantir CORS em respostas 500
**Data:** 2026-04-08 (Wave 1, Sessao 3 — estabilizacao)
**Contexto:** Quando uma exception nao tratada subia ate o `ServerErrorMiddleware` default do Starlette, a resposta 500 era construida FORA da pilha de middleware do usuario. Como `CORSMiddleware` esta dentro dessa pilha, os headers `Access-Control-Allow-Origin` nao eram aplicados — e o browser reportava "CORS error" para o que era na verdade um erro de servidor. Mario perdeu varias horas tentando "consertar CORS" quando a causa real era falha de DB ou JWT.
**Decisao:** Registrar `@app.exception_handler(Exception)` em `app/main.py` que retorna `JSONResponse(status_code=500, ...)`. Como esse handler roda DENTRO da stack de middleware, o `CORSMiddleware` consegue anexar os headers na saida. O log original da exception e preservado via `logger.exception(...)`.
**Alternativas:**
  - Mover `CORSMiddleware` para fora do user middleware (impossivel via API publica do FastAPI).
  - Usar middleware customizado em vez de exception handler (mais codigo, mesmo resultado).
**Consequencias:** Erros 500 reais sempre chegam ao browser com headers CORS, expondo a mensagem real (`Erro interno do servidor`) em vez de mascararem como erro de CORS. Stack trace continua nos logs do backend.

---

## ADR-018 — RLS unificada em is_admin (substitui setor = 'STUDIO')
**Data:** 2026-04-08 (Wave 1, Sessao 3 — estabilizacao)
**Contexto:** A migration `003_policies_wave1_usuarios.sql` (Sessao 1 da Wave 1) atualizou apenas as policies da tabela `usuarios` para usar `is_admin = true`, mas as policies das outras 5 tabelas (`provas_digitais`, `movimentacoes`, `etiquetas`, `audit_logs`, `configuracoes_sistema`) ainda checavam `setor = 'STUDIO'`. Isso criava uma divergencia perigosa: um admin com setor != STUDIO conseguiria gerenciar usuarios mas NAO veria todas as provas via RLS — quebrando a semantica de "admin".
**Decisao:** Migration `004_unify_rls_is_admin.sql` substitui TODOS os checks de admin nas policies por `is_admin = true`. Logica de negocio por setor (VENDEDOR ve suas provas, MOTORISTA ve `COM_MOTORISTA`, CLICHERIA ve provas em status de clicheria) PERMANECE usando setor — sao papeis operacionais, nao permissoes admin. A partir desta migration, "admin" e definido exclusivamente pela coluna `is_admin = true`, independente do setor cadastrado.
**Alternativas:**
  - Manter dual: `setor = 'STUDIO' OR is_admin = true` (rejeitado: complica policies, mantem ambiguidade).
  - Forcar todo admin a ter `setor = 'STUDIO'` (rejeitado: acopla papel operacional a permissao).
**Consequencias:** Para tornar alguem admin, basta setar `is_admin = true` — nao precisa mexer em setor. Validado em produção via `pg_policies` (11 policies confirmadas usando `is_admin`).

---

## ADR-019 — Protecao do ultimo admin ativo
**Data:** 2026-04-08 (Wave 1, Sessao 3 — estabilizacao)
**Contexto:** A regra RN-010 protegia apenas o admin contra remover o proprio acesso. Mas nada impedia que o admin A demovesse/desativasse o admin B se B fosse o unico OUTRO admin do sistema, deixando o sistema sem nenhum admin ativo. Cenario realista: admin recem-criado se autodemove → sistema fica sem ninguem que possa criar usuarios ou gerenciar configuracoes.
**Decisao:** Funcao `_count_other_active_admins(db, exclude_id)` em `app/api/v1/users.py`. Tanto PATCH quanto DELETE bloqueiam (409) qualquer operacao que deixaria o count em 0:
  - PATCH: se `target.is_admin AND target.ativo` e o body define `is_admin=False` ou `ativo=False`, count tem que ser >= 1.
  - DELETE: se `target.is_admin AND target.ativo`, count tem que ser >= 1.
  - Self-protection (admin nao pode se demover/desativar) permanece como camada anterior; o check de ultimo admin so roda quando target != caller.
**Alternativas:**
  - Constraint no banco (rejeitado: difícil expressar "pelo menos 1 ativo" sem trigger pesado).
  - Check apenas no DELETE (rejeitado: PATCH com `is_admin=false` chegaria ao mesmo estado).
**Consequencias:** Sistema garantidamente sempre tem >= 1 admin ativo. Coberto por 8 testes em `test_users_api.py` (3 bloqueios + 3 caminhos felizes + 2 short-circuits).

---

## ADR-020 — Sincronizacao auth↔DB com saga compensatoria em PATCH/DELETE
**Data:** 2026-04-08 (Wave 1, Sessao 5 — auditoria pre-Wave 2)
**Contexto:** Auditoria critica de Wave 1 encontrou drift real em producao: o usuario `regianepetrim@teste.com.br` tinha `auth.users.banned_until = 2126-04-09` (banido por 100 anos pelo soft-delete) MAS `public.usuarios.ativo = true` (alguem reativou via PATCH). Causas:
  1. **Bug 1 — PATCH sem unban**: `update_user` nao chamava `enable_auth_user` ao reativar. Estado app dizia "ativo" mas o login continuava bloqueado.
  2. **Bug 2 — DELETE com race**: `deactivate_user` fazia `db.commit()` ANTES de chamar `disable_auth_user`. Se a chamada GoTrue falhasse, app estava inativo mas tokens ainda renovavam.
  3. **Bug 3 — `disable_auth_user` best-effort**: o cliente em `app/core/supabase_admin.py` apenas logava o erro em vez de propagar — qualquer falha do GoTrue passava silenciosa.
**Decisao:**
  - **Contrato novo de `disable_auth_user`/`enable_auth_user`**: ambos chamam `resp.raise_for_status()` e propagam `httpx.HTTPStatusError`. Best-effort permanece apenas em `delete_auth_user` (rollback de create — la o erro de DB ja aconteceu, nao podemos mascarar).
  - **Adicao de `enable_auth_user`**: nova funcao em `app/core/supabase_admin.py` que faz `PUT /admin/users/{id}` com `{"ban_duration": "none"}` (convencao GoTrue para desbanir).
  - **PATCH**: detecta transicao `was_active != will_be_active` ANTES de mutar o objeto. Se `needs_ban`, chama `disable_auth_user`; se `needs_unban`, chama `enable_auth_user`. Falha → 502, `db.rollback()`, sem persistir nada. Sucesso da chamada auth → tenta `db.commit()`. Se commit falhar APOS auth ja ter mudado, **compensacao inversa**: re-enable se foi um ban, re-disable se foi um unban. Falha de compensacao loga "drift manual" (operador precisa investigar).
  - **DELETE**: `disable_auth_user` agora roda ANTES do `db.commit()`. Falha auth → 502 sem tocar DB. Falha de commit apos ban → compensacao com `enable_auth_user`.
**Alternativas:**
  - Outbox pattern com worker (rejeitado: overkill para 2 estados, requer infra extra).
  - Two-phase commit / XA (impossivel: GoTrue nao suporta).
  - Manter best-effort e reconciliar via job (rejeitado: drift detectado a posteriori e ja estava em prod).
**Consequencias:**
  - Estado auth↔app sempre converge para o mesmo valor ou para um log de drift explicito (nunca silenciosamente diferente).
  - 9 testes novos em `test_users_api.py` cobrem ordem de chamadas, falhas de auth, falhas de commit e compensacao inversa.
  - 2 testes novos em `test_supabase_admin.py` cobrem o novo contrato de raise.
  - **Acao manual pendente em producao**: o usuario `regianepetrim@teste.com.br` ainda tem `banned_until=2126-04-09`. Precisa rodar um unban explicito (via Supabase Dashboard ou chamando `enable_auth_user`) para sair do drift atual.

---

## ADR-021 — HTTP_422_UNPROCESSABLE_CONTENT (Starlette 0.40+)
**Data:** 2026-04-08 (Wave 1, Sessao 5 — auditoria)
**Contexto:** Starlette 0.40 adicionou `HTTP_422_UNPROCESSABLE_CONTENT` e marcou `HTTP_422_UNPROCESSABLE_ENTITY` como deprecated. RFC 9110 renomeou o status code para refletir que se aplica a "content" (qualquer payload), nao apenas "entity" (XML legacy). Pytest mostrava `DeprecationWarning` em cada uso.
**Decisao:** Substituir todas as 4 ocorrencias em `app/api/v1/users.py` por `HTTP_422_UNPROCESSABLE_CONTENT`. Status code numerico (422) inalterado — apenas o nome da constante.
**Alternativas:** Suprimir o warning (rejeitado: mascara deprecation real, e a substituicao e trivial).
**Consequencias:** Zero deprecation warnings na suite. Compativel com Starlette atual e futuro.

---

## ADR-022 — Drift entre Alembic e supabase_migrations.schema_migrations
**Data:** 2026-04-08 (Wave 1, Sessao 5 — auditoria)
**Contexto:** Verificacao via Supabase MCP encontrou que as migrations 003 e 004 EXISTEM no diretorio `backend/migrations/versions/` e seus efeitos estao no banco (constraints `chk_*`, colunas `is_admin`/`created_by`, indexes `idx_movimentacoes_*`), MAS:
  - A tabela `public.alembic_version` NAO existe.
  - A tabela `supabase_migrations.schema_migrations` (gerenciada pelo Supabase Dashboard / CLI) tem as migrations 001 e 002 como `name="initial_schema"` e `name="seed_configuracoes"` mas NAO tem 003/004.
  - Provavel causa: migrations 003/004 foram aplicadas via SQL direto durante a estabilizacao da Sessao 3, sem rodar `alembic upgrade head`.
**Decisao (registrada, nao executada):** Antes do primeiro deploy de Wave 2, alinhar os dois sistemas:
  1. Rodar `alembic stamp head` localmente apontando para o banco de producao para criar `public.alembic_version` com a revisao corrente (`004`).
  2. Aplicar migrations futuras (incluindo a 005 desta auditoria) via `alembic upgrade head` daqui em diante.
  3. Documentar no README do backend que `supabase_migrations.schema_migrations` reflete apenas o que foi aplicado pela CLI Supabase — `alembic_version` e a fonte de verdade do dominio.
**Alternativas:**
  - Migrar tudo para Supabase CLI (rejeitado: ADR-004 exige Alembic para o dominio).
  - Recriar todas as migrations no Supabase Dashboard (rejeitado: perderia historico).
**Consequencias:** Migration 005 (auditoria Wave 1) sera o primeiro teste de fogo. Se Mario optar por aplicar via MCP `apply_migration` agora (antes do `stamp`), os dois sistemas continuarao desalinhados — solucao temporaria, nao ideal. **Acao pendente**: Mario decide se aplica 005 via MCP ja ou se primeiro estabiliza o tracking.

---

## ADR-023 — Index na FK usuarios.created_by
**Data:** 2026-04-08 (Wave 1, Sessao 5 — auditoria)
**Contexto:** Supabase performance advisor reportou (level INFO): `usuarios.created_by` referencia `usuarios.id` mas nao tem index. Sem o index, qualquer JOIN ou DELETE de admin que tenha criado outros usuarios faz seq scan na tabela inteira. Nao e bug funcional, mas degrada com volume.
**Decisao:** Migration `005_add_index_on_usuarios_created_by.py` cria `CREATE INDEX IF NOT EXISTS idx_usuarios_created_by ON usuarios(created_by)`. Idempotente, mesmo padrao das migrations 001/003.
**Alternativas:** Ignorar (rejeitado: cheap fix, alta visibilidade do advisor).
**Consequencias:** Plano de execucao usa index scan a partir do `apply`. Nenhuma mudanca de comportamento. **Aplicada na Sessao 5b** via `python -m alembic upgrade head` apos `alembic stamp 004` estabilizar o tracking.

---

## ADR-024 — search_path='' nas funcoes de trigger
**Data:** 2026-04-08 (Wave 1, Sessao 5b — execucao do plano da auditoria)
**Contexto:** Supabase security advisor reportava 2x WARN `function_search_path_mutable` em `public.fn_bloquear_alteracao()` e `public.fn_atualizar_updated_at()`. Sem `search_path` explicito, ambas as funcoes herdam o `search_path` da sessao chamadora — superficie classica de search_path hijacking, em que um schema malicioso injeta overrides para `now()`, `coalesce()` etc. e altera o comportamento da funcao. As duas funcoes sao SECURITY DEFINER por default (rodam como o owner) e disparam em triggers de tabelas criticas (movimentacoes, etiquetas, audit_logs, todas as `_updated_at`), entao a exposicao e maxima.
**Decisao:** Migration `006_set_search_path_on_trigger_functions.py` faz `ALTER FUNCTION ... SET search_path = ''`. As duas funcoes sao PL/pgSQL puro com apenas built-ins schema-qualified (`NOW()`, `NEW.updated_at`, `RAISE EXCEPTION`) — nao precisam resolver nenhum identificador via `search_path`. `''` e o valor mais restritivo possivel sem quebrar nada.
**Alternativas:**
  - `SET search_path = pg_catalog, public` (rejeitado: ainda vulneravel se um schema antes de `public` for injetado).
  - `SET search_path = pg_catalog` (equivalente em seguranca, mas menos auto-explicativo do que `''`).
  - Marcar como `SECURITY INVOKER` (rejeitado: muda quem executa, nao resolve o hijack).
**Consequencias:** Warnings do advisor zerados. Validado em runtime: `UPDATE` em `configuracoes_sistema` continuou disparando `_updated_at` corretamente (`updated_at` mudou de `2026-04-07` para `2026-04-08`). Tabelas imutaveis estao vazias e nao deu para testar `fn_bloquear_alteracao` ao vivo, mas a fonte nao tem dependencia de search_path.

---

## ADR-025 — RLS em public.alembic_version (fix de side effect do alembic stamp)
**Data:** 2026-04-08 (Wave 1, Sessao 5b — execucao do plano da auditoria)
**Contexto:** O `python -m alembic stamp 004` (executado para estabilizar o tracking — ADR-022) cria `public.alembic_version` automaticamente. Alembic nao habilita RLS na propria tabela de tracking — mas o projeto expoe TODO o schema `public` via PostgREST com a anon key. O advisor de seguranca reportou ERROR `rls_disabled_in_public` IMEDIATAMENTE apos o stamp: qualquer cliente com a anon key conseguia ler ou escrever o numero da versao.
**Decisao:** Migration `007_enable_rls_on_alembic_version.py` faz `ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY` SEM nenhuma policy. Postgres com RLS ligado e zero policies bloqueia 100% do trafego que passa por roles nao-bypass (anon, authenticated, service_role respeita RLS, etc). O role `postgres` usado pelo Alembic bypassa RLS por default (`bypassrls = true`), entao `alembic upgrade head` continua funcionando normalmente.
**Alternativas:**
  - Mover `alembic_version` para um schema dedicado fora do `public` (rejeitado: requer recriar a tabela e mexer no `version_table_schema` do `env.py`, e ainda precisa garantir que o novo schema nao seja exposto pelo PostgREST).
  - Criar uma policy explicita `FOR ALL USING (false)` (equivalente em seguranca, mais ruido — RLS sem policy ja faz a mesma coisa).
  - Revogar `SELECT/INSERT/UPDATE/DELETE` da tabela para `anon`/`authenticated` via `REVOKE` (rejeitado: nao protege se uma role nova for adicionada; RLS e o mecanismo correto na arquitetura Supabase).
**Consequencias:** Advisor passa a reportar INFO `rls_enabled_no_policy` em `alembic_version` — esse INFO e exatamente o estado desejado (RLS ligado, sem policy = bloqueio total) e nao um erro a ser corrigido. PostgREST nao consegue mais ler/escrever a tabela. Documentado para que ninguem "corrija" o INFO criando policies.

---

## ADR-026 — Index na FK configuracoes_sistema.updated_by
**Data:** 2026-04-08 (Wave 1, Sessao 5b — execucao do plano da auditoria)
**Contexto:** Re-rodando o performance advisor depois de aplicar a migration 005, surgiu um INFO novo: `unindexed_foreign_keys` em `configuracoes_sistema.updated_by → usuarios.id`. Provavelmente o advisor reporta apenas o primeiro caso ate o usuario corrigir, e expos o segundo apos a 005. Mesmo problema do ADR-023 (FK criada na migration 001 sem index), mesma classe de risco.
**Decisao:** Migration `008_add_index_on_configuracoes_sistema_updated_by.py` cria `CREATE INDEX IF NOT EXISTS idx_configuracoes_sistema_updated_by ON configuracoes_sistema(updated_by)`. Idempotente, mesmo padrao das migrations 001/003/005.
**Alternativas:** Ignorar (rejeitado: ja estavamos limpando o advisor, completar a faxina).
**Consequencias:** Advisor 100% limpo na categoria `unindexed_foreign_keys`. Custo operacional desprezivel (tabela tem 2 linhas).

---

## ADR-027 — auth_leaked_password_protection: WONTFIX (recurso de plano pago)
**Data:** 2026-04-08 (Wave 1, Sessao 5b — pos-execucao)
**Contexto:** O advisor de seguranca do Supabase reporta WARN `auth_leaked_password_protection` quando o toggle "Leaked Password Protection" (HaveIBeenPwned check no signup/reset) esta OFF. A auditoria havia listado o item como Decisao 4c (acao manual no Dashboard). Quando reportado, Mario informou que **o feature nao esta disponivel no plano atual do projeto** — o toggle existe na UI mas o save bloqueia/exige upgrade.
**Decisao:** Aceitar o WARN como WONTFIX enquanto o projeto estiver no plano gratuito. Compensacoes ja em vigor:
  1. Politica de senha minima do Supabase Auth (configurada no Dashboard).
  2. Backend nao emite tokens (ADR-003) — toda autenticacao passa pelo GoTrue, que ja faz rate limiting de tentativas de login.
  3. Wave 2/3 nao introduzem nenhuma nova superficie de signup publico — usuarios sao criados exclusivamente por admin (ADR-013).
**Alternativas:**
  - Implementar verificacao HaveIBeenPwned manualmente no backend (rejeitado: re-implementa o feature pago, mais codigo, mais latencia, e o GoTrue/Supabase faria o mesmo job nativamente quando o plano for upgrade).
  - Forcar upgrade de plano so para o feature (rejeitado: custo nao justificado para um MVP interno, ainda no Wave 1).
**Consequencias:**
  - O WARN vai continuar aparecendo no advisor de seguranca indefinidamente. Documentado aqui para que ninguem perca tempo "consertando" novamente.
  - Quando o projeto migrar para um plano que inclui o feature (Pro+), basta ativar o toggle no Dashboard — sem mudanca de codigo.
  - **Revisar este ADR** se houver mudanca de plano OU se o backlog acrescentar signup publico (entao a defesa em profundidade muda).

---

## ADR-028 — Remocao da conta de teste regianepetrim@teste.com.br
**Data:** 2026-04-08 (Wave 1, Sessao 5b — pos-execucao)
**Contexto:** A auditoria da Sessao 5 detectou drift real em producao para `regianepetrim@teste.com.br`: `auth.users.banned_until = 2126-04-09` mas `public.usuarios.ativo = true`. A acao recomendada era unban (Dashboard ou `enable_auth_user`). Quando reportado, Mario informou que (a) nao conseguiu fazer o unban no Dashboard, e (b) **a conta foi criada apenas para teste e pode ser apagada**.
**Decisao:** Apagar a conta inteira (auth + dominio) em vez de unban:
  1. **Verificacao de seguranca**: `SELECT COUNT(*) FROM public.usuarios WHERE created_by = '038fa2a9...'` retornou 0 — nenhum usuario depende dela via FK.
  2. **DELETE em `public.usuarios`** via Supabase MCP `execute_sql` (uma linha removida, sem cascata).
  3. **DELETE em `auth.users`** via `python -c` chamando `app.core.supabase_admin.delete_auth_user('2943ba9a...')` — usa a Admin API do GoTrue (`DELETE /auth/v1/admin/users/{id}`), que limpa `auth.users` + `auth.identities` + revoga sessions em cascata corretamente.
  4. **Verificacao final**: query MCP confirmou 0 linhas em `public.usuarios`, `auth.users`, `auth.identities`, `auth.sessions` — drift resolvido por remocao.
**Alternativas:**
  - Unban + manter (rejeitado: Mario nao conseguiu unban e a conta nao tem proposito alem de teste).
  - Apagar so de `public.usuarios` (rejeitado: deixaria orfa em `auth.users`, drift inverso).
  - DELETE direto em `auth.users` via SQL (rejeitado: pode deixar lixo se houver triggers do GoTrue ou referencias internas; a Admin API e o caminho oficial e ja existe pronta no codigo).
**Consequencias:**
  - Estado producao pos-Sessao 5b: 2 usuarios ativos em `public.usuarios` (Mario + outro admin), 2 correspondentes em `auth.users`, sem drift.
  - O bug que causou o drift original (PATCH sem unban) ja foi corrigido na Sessao 5 (ADR-020) — mesmo se uma nova conta for criada e desativada/reativada, o codigo agora mantem auth↔DB sincronizado.
  - **Sem necessidade de acao adicional do Mario** — o item "1. Reativar regiane" das Sessoes 5/5b esta resolvido por delete.

---

## ADR-029 — Reescrita das policies RLS para `(SELECT auth.uid())` adiada para a Wave 2
**Data:** 2026-04-09 (Wave 1, Sessao 6 — auditoria de validacao final)
**Contexto:** O performance advisor do Supabase reporta 11x WARN `auth_rls_initplan` em todas as policies que chamam `auth.uid()` diretamente em `USING`/`WITH CHECK`. O Postgres re-avalia a expressao por linha em vez de uma vez por query (initplan). A correcao recomendada e envolver em `(SELECT auth.uid())`, o que faz o planner promover a expressao a um InitPlan executado uma unica vez. As 11 policies afetadas estao em `public.usuarios`, `public.provas_digitais`, `public.movimentacoes`, `public.etiquetas`, `public.audit_logs` e `public.configuracoes_sistema` — todas seguindo o mesmo padrao `is_admin = true OR auth_uid = auth.uid()`. **Decisao 4b** ja registrada nas Sessoes 5/5b adiou o trabalho; este ADR formaliza o porque e quando.
**Decisao:** Adiar a reescrita para o **inicio da Wave 2**, junto com a primeira leva de carga real de dados (provas_digitais + movimentacoes). Justificativa:
  1. O ganho de initplan **so e mensuravel com volume**. As tabelas estao com 0–3 linhas — qualquer micro-benchmark agora seria pintura no ar.
  2. Na Wave 2 entram `provas_digitais` (1 linha por arte) e `movimentacoes` (N linhas por prova), com filtros do tipo `WHERE setor = ... AND ativo = true` que sao exatamente o caso onde o initplan re-avaliado machuca. Vamos ter dados de teste suficientes para medir antes/depois.
  3. A reescrita e mecanica e idempotente (substituir `auth.uid()` por `(SELECT auth.uid())` em 11 lugares), mas precisa de um novo arquivo `.sql` em `backend/migrations/rls/` para preservar versionamento (regra critica de CLAUDE.md). Faze-la agora ocupa um slot de migration sem benefit demonstravel.
  4. Nao e bug funcional nem vulnerabilidade — e otimizacao. O WARN do advisor e benigno enquanto o volume estiver baixo.
**Plano de execucao na Wave 2:**
  - Criar `backend/migrations/rls/005_initplan_optimization.sql` com `DROP POLICY IF EXISTS` + `CREATE POLICY` para as 11 policies, mantendo a logica identica (so trocando `auth.uid()` por `(SELECT auth.uid())`).
  - Aplicar via `apply_rls.py` apos as primeiras inserts de carga real.
  - Medir `EXPLAIN ANALYZE` antes/depois em 1-2 queries representativas (`SELECT * FROM provas_digitais WHERE ativo = true LIMIT 50` com authenticated role).
  - Confirmar no advisor que os 11 WARN sumiram.
**Alternativas:**
  - Fazer agora junto com o sign-off da Wave 1 (rejeitado: sem volume nao da para validar o ganho, e o trabalho ja esta planejado).
  - Ignorar permanentemente (rejeitado: 11 WARN persistentes poluem o advisor e mascaram problemas reais futuros).
  - Reescrever apenas algumas policies (rejeitado: inconsistente, mais dificil de auditar — ou todas ou nenhuma).
**Consequencias:**
  - Wave 1 sai com 11 WARN `auth_rls_initplan` no advisor — **esperado e documentado**.
  - Primeira tarefa tecnica da Wave 2 (antes de implementar a primeira movimentacao real) sera aplicar a reescrita e medir.
  - Risco de "esquecer": baixo — esta listado neste ADR + na Sessao 6 do CHANGELOG + no veredicto da auditoria. Recomendado criar item explicito no backlog da Wave 2.

---

## ADR-030 — Criar segundo administrador operacional antes da Wave 2 entrar em uso real
**Data:** 2026-04-09 (Wave 1, Sessao 6 — auditoria de validacao final)
**Contexto:** A auditoria final encontrou um SPOF organizacional, nao tecnico: producao tem **1 unico admin ativo** (Mario). A protecao RN-010 funciona corretamente (4 protecoes empilhadas em `_count_other_active_admins` impedem auto-rebaixamento, auto-delete e remocao do ultimo admin), mas isso e exatamente o problema — se a conta auth do unico admin for perdida (esquecimento de senha sem email recovery configurado, comprometimento, etc), a unica recuperacao e via Supabase Dashboard (intervencao manual fora da aplicacao) ou re-promovendo via SQL direto. Nenhum dos dois caminhos e parte do fluxo normal da aplicacao. Wave 1 e o ultimo momento "barato" para resolver isso — na Wave 2 ja havera dados reais de provas e movimentacoes, e o impacto de uma perda de acesso administrativo cresce muito.
**Decisao:** Antes da Wave 2 entrar em uso real (primeira prova digital cadastrada), criar um **segundo admin operacional** via o proprio fluxo da aplicacao (`POST /api/v1/users` com `is_admin=true`, autenticado como Mario). Restricoes:
  1. **Conta dedicada de operacao** — nao deve ser uma conta pessoal de outro funcionario que tambem e usada no dia-a-dia. Email tipo `ops@3studio.com.br` ou similar, com acesso compartilhado e seguro entre Mario e 1 backup confiavel.
  2. **Senha gerada aleatoriamente** e armazenada em gerenciador de senhas (1Password, Bitwarden, etc), nao em texto plano, nao em chat, nao em arquivo do projeto.
  3. **Setor STUDIO + is_admin=true** — sem `localizacao` (admin nao precisa).
  4. **Validacao pos-criacao**: confirmar via `SELECT COUNT(*) FROM public.usuarios WHERE is_admin = true AND ativo = true` que retorna 2, e que o segundo admin consegue logar e listar usuarios.
  5. **Documentar no CHANGELOG da Sessao em que for criado** (provavelmente Sessao 7, abertura da Wave 2).
**Alternativas:**
  - Manter single admin com email recovery configurado (rejeitado: ainda fica vulneravel a perda do email, comprometimento da unica conta, ferias do Mario, etc — single point of failure permanece).
  - Promover uma conta existente a admin (rejeitado: producao so tem o Mario; nao ha conta existente para promover sem criar primeiro).
  - Adiar para "quando fizer sentido" (rejeitado: e exatamente o tipo de tarefa que se adia indefinidamente ate ser tarde demais; o custo de criar agora e ~5 minutos).
  - Implementar self-service password reset via Supabase Auth (valido, mas nao substitui ter um segundo admin — sao defesas complementares; o reset depende de email funcionando).
**Consequencias:**
  - Apos a criacao, RN-010 vai proteger AMBOS os admins (nenhum dos dois consegue se auto-deletar nem deletar o outro se isso deixar zero admins ativos — mas como sao dois, sempre da para remover um).
  - Recuperacao de acesso passa a ser parte do fluxo da aplicacao (admin B consegue redefinir/desativar admin A se necessario).
  - **Acao explicita pendente para Mario** antes da primeira tarefa funcional da Wave 2.
  - Se for criada a conta `ops@3studio.com.br`, importante registrar no gerenciador de senhas da empresa quem mais tem acesso — sao zero auditoria de quem usou se a senha for compartilhada sem rastreio.
