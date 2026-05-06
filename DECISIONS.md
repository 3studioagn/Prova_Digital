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
**Status:** EXECUTADO em Sessao 7 (2026-04-09, abertura da Wave 2). Resultado:
  - `backend/migrations/rls/005_initplan_optimization.sql` criado e aplicado em producao via Supabase MCP `execute_sql` (bloco unico idempotente).
  - 11/11 policies confirmadas usando `(SELECT auth.uid())` via `pg_policies`.
  - Performance advisor: 11 WARN `auth_rls_initplan` -> 0. Nenhum novo WARN surgiu.
  - Security advisor inalterado (1 INFO ADR-025, 1 WARN ADR-027 WONTFIX).
  - `EXPLAIN ANALYZE` pulado por irrelevancia (tabelas vazias); validacao canonica foi o proprio advisor.
  - 108 testes continuam passando sem regressao.
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

## ADR-031 — Upload de imagens via Presigned URL (frontend -> R2 direto)
**Data:** 2026-04-09 (Wave 2, Sessao 8 — Componente 06)
**Contexto:** O Componente 06 precisa receber uploads de JPG/PNG ate 10MB. Duas opcoes: (a) frontend faz multipart/form-data para o backend, que valida e faz upload para R2; (b) frontend pede uma URL pre-assinada ao backend, faz PUT direto no R2, depois avisa o backend que pode criar a prova. A opcao (a) consome banda + memoria do Railway; a (b) desacopla e e o padrao S3.
**Decisao:** Adotar presigned URL.
  1. `POST /api/v1/provas/upload-url` valida unicidade do nro_requerimento e content_type, gera `object_key` determinstico `provas/{yyyy}/{mm}/{uuid_hex}/{sanitized_filename}`, retorna presigned URL (TTL 15min) + metadata.
  2. Frontend faz `PUT <upload_url>` com o binario.
  3. Frontend chama `POST /api/v1/provas/` passando `object_key`.
  4. Backend faz `HeadObject` + `Range GET 16 bytes` para validar tamanho e magic bytes (ver ADR-032) antes de inserir no banco.
  5. Qualquer falha apos o upload ter acontecido dispara `r2_delete(object_key)` best-effort (ver ADR-041).
**Alternativas:**
  - Upload multipart pelo backend (rejeitado: custa banda e memoria do Railway para cada request; consume mais do free tier).
  - `PUT` direto sem validacao pos-upload (rejeitado: confiar no Content-Type do header e trivialmente spoofavel).
  - Pre-alocar uma linha em `provas_digitais` antes do upload (rejeitado: obriga estado intermediario "uploading" na tabela, complica RLS e fluxo).
**Consequencias:**
  - Backend nao recebe binarios gigantes — liberando memoria/CPU para logica de dominio.
  - Exige CORS no bucket R2 permitindo `PUT` de `http://localhost:3000` (confirmado + aplicado manualmente por Mario na Sessao 8).
  - Janela de ~15min para orfaos no R2 se o frontend fizer upload e nunca chamar `POST /provas/` (aceitavel; cleanup via cron futuro na Wave 6).

---

## ADR-032 — Validacao de MIME real por magic bytes (sem dependencia nativa)
**Data:** 2026-04-09 (Wave 2, Sessao 8 — Componente 06)
**Contexto:** O fluxo do ADR-031 coloca o arquivo no R2 ANTES do backend validar o conteudo. O `Content-Type` declarado no upload e o que o frontend mandou — trivialmente spoofavel (alguem pode subir um executavel declarando `image/jpeg`). Precisamos validar o conteudo real apos o upload.
**Decisao:** Fazer `Range GET bytes=0-15` no R2 para ler os primeiros 16 bytes, e comparar com as assinaturas conhecidas de JPG e PNG:
  - JPEG: `FF D8 FF`
  - PNG: `89 50 4E 47 0D 0A 1A 0A`
  Se nao bater, rejeitar com 422 e limpar o R2 (ADR-041). Implementado em `app/api/v1/provas.py::_detect_mime_from_bytes` + `r2_signed.get_object_head_bytes`.
**Alternativas:**
  - `python-magic` (libmagic binding): rejeitado porque exige `libmagic.so` no container Railway (deploy mais complexo, falha silenciosa em dev Windows).
  - `filetype` (pure Python): rejeitado porque magic bytes JPG/PNG sao triviais e a lib adiciona 1 dep desnecessaria.
  - Download completo + parse com Pillow: rejeitado porque baixa 10MB para validar 3 bytes.
**Consequencias:**
  - Zero dependencia nativa, stdlib + boto3 ja existentes.
  - Range GET no R2 tem custo negligivel (muitos 10KB de transfer total).
  - Cobertura: `test_create_prova_magic_bytes_invalid` testa rejeicao de bytes nao-imagem.

---

## ADR-033 — QR Code hash = HMAC-SHA256 com secret dedicada
**Data:** 2026-04-09 (Wave 2, Sessao 8 — Componente 06)
**Contexto:** RN-001 exige que o QR Code seja unico e nao-reutilizavel. O schema tem `provas_digitais.qr_code_hash VARCHAR(64) UNIQUE NOT NULL` — cabem exatamente 64 chars hex (= SHA-256). Opcoes de formato: (a) UUID4, (b) SHA-256 puro do prova_id, (c) HMAC-SHA256 com secret.
**Decisao:** HMAC-SHA256 com secret dedicada `QR_CODE_HMAC_SECRET` (env var nova). Input: `"{prova_id}:{nro_requerimento}"`. Saida: hex de 64 chars.
  - Deterministico: mesmo (prova_id, nro_req) produz sempre o mesmo hash (utilidade: regenerar o QR se o arquivo for perdido).
  - Nao-reversivel sem a secret: extrair `prova_id` do hash exige acesso a secret.
  - Validavel no scanner da Wave 3 sem ida ao banco: basta recomputar e comparar com o hash armazenado (rapido, atende RNF-002 "<=2s").
  - Payload do QR: `3SD|{nro_requerimento}|{hash[:16]}` (16 chars = 64 bits de entropia truncada, suficiente para colisao zero no volume esperado).
  - Validacao constant-time via `hmac.compare_digest` (mitiga timing attacks).
  - Rotacao da secret **invalida todos os QR Codes existentes** — documentado no `.env.example` e no ADR.
**Alternativas:**
  - UUID4 (rejeitado: 32 chars, nao da nenhuma capacidade de validacao sem banco).
  - SHA-256 puro sem secret (rejeitado: qualquer um pode recomputar o hash conhecendo (prova_id, nro_req); a secret adiciona uma camada de defesa).
  - URL universal `https://app.../scan?h=...` (rejeitado: cria dependencia no dominio publico; o scanner da Wave 3 roda dentro da propria aplicacao conforme RF-004).
**Consequencias:**
  - Secret gerada uma vez via `python -c "import secrets; print(secrets.token_hex(32))"` e guardada em `backend/.env` (local) + Railway env (producao, na hora do deploy).
  - Geracao de hash + validacao sao operacoes stdlib — zero dependencia nova.
  - Teste de monkey-patching (`test_hash_muda_quando_secret_muda`) confirma que a secret e efetivamente usada.

---

## ADR-034 — qrcode[pil] para renderizacao do QR Code PNG
**Data:** 2026-04-09 (Wave 2, Sessao 8 — Componente 06)
**Contexto:** Precisamos transformar o payload do QR Code (ADR-033) em uma imagem PNG para embutir na etiqueta PDF. Opcoes principais: `qrcode[pil]`, `segno`, `pyqrcode`.
**Decisao:** `qrcode>=7.4,<8.0` com extra `[pil]`.
  - API simples: `qr.add_data(); qr.make(); qr.make_image()`.
  - Error correction `ERROR_CORRECT_M` (15% de tolerancia — padrao para impressao onde a etiqueta pode sujar ou borrar).
  - Resize para 200x200 px via `Image.resize(..., resample=0)` (NEAREST) — preserva as bordas nitidas das celulas do QR (interpolacao suavizada quebraria a leitura).
  - Traz Pillow como sub-dependencia, util para futuras necessidades (thumbnails de artes, etc).
**Alternativas:**
  - `segno` (rejeitado: muito mais recente, menor ecossistema, a API esta em SVG-first — exigiria conversao extra para PNG).
  - `pyqrcode` (rejeitado: mantenedor inativo desde 2016, ultimos bugs abertos).
**Consequencias:**
  - +~8MB de wheels no backend (qrcode + Pillow). Aceitavel no Railway.
  - Python 3.14 compat confirmado (Pillow 12.2.0 instalou limpo).
  - Cobertura 97% do `qrcode_service.py` via testes unitarios.

---

## ADR-035 — fpdf2 para geracao do PDF da etiqueta
**Data:** 2026-04-09 (Wave 2, Sessao 8 — Componente 06)
**Contexto:** RF-003 + RN-011 exigem geracao de etiqueta imprimivel em PDF. Opcoes: `reportlab`, `weasyprint`, `fpdf2`.
**Decisao:** `fpdf2>=2.7,<3.0`.
  - Zero dependencia nativa (reportlab tem C compiladas; weasyprint exige Cairo/Pango).
  - Licenca MIT (reportlab e LGPL, weasyprint e BSD).
  - API simples e direta: `FPDF()`, `add_page()`, `set_font()`, `cell()`, `image()`, `output()`.
  - Suporta imagens PIL e BytesIO — integra direto com o output do `qrcode_service`.
  - Dois formatos suportados no template: `A4` (default, jato/laser) e `80mm_thermal` (impressora termica com bobina).
  - Fonte padrao `Helvetica` (embutida, zero I/O adicional).
**Alternativas:**
  - `reportlab` (rejeitado: pesado, compila nativo).
  - `weasyprint` (rejeitado: exige libs sistema (Cairo, Pango, gobject) — deploy Railway mais complexo).
  - Gerar SVG e converter: rejeitado (etapa extra, menos suportado pelos drivers de impressao).
**Consequencias:**
  - `fpdf2 2.8.7` instalou limpo em Python 3.14.
  - `pdf.output()` retorna `bytearray` no 2.8.7 (convertido para `bytes` no service para compatibilidade com base64).
  - API deprecou `ln=` em favor de `new_x=/new_y=` — ajustado em toda a funcao `gerar_pdf`.
  - Cobertura 98% via `test_etiqueta_service.py`.

---

## ADR-036 — template_etiqueta como JSONB estruturado
**Data:** 2026-04-09 (Wave 2, Sessao 8 — Componente 06)
**Contexto:** A migration 002 (Wave 0) gravou `configuracoes_sistema.template_etiqueta = '"padrao"'` como string JSONB. O Componente 09 (tela de configuracoes) precisa permitir edicao de campos individuais do template — formato, logo, etc — sem reescrever a chave toda. String JSONB nao suporta esse padrao.
**Decisao:** Migration 009 evolui o valor para objeto JSONB:
  ```json
  {
    "nome": "padrao",
    "formato": "A4",
    "logo_enabled": true,
    "mostrar_data_criacao": false
  }
  ```
  - `nome`: identifica o template (compativel com o seed original).
  - `formato`: `"A4"` ou `"80mm_thermal"` (impressora termica 80mm).
  - `logo_enabled`: renderizar o logo 3Studio no cabecalho.
  - `mostrar_data_criacao`: incluir data no campo da etiqueta.
  Migration e idempotente — `WHERE jsonb_typeof(valor) = 'string'` garante que rodar multiplas vezes nao duplica. Downgrade volta para `'"padrao"'`.
  O endpoint `POST /provas/` le o template via `_carregar_template_etiqueta(db)` e passa para `etiqueta_service.gerar_pdf`.
**Alternativas:**
  - Criar tabela dedicada `etiqueta_templates` (rejeitado: overkill para um unico template na Wave 2; configuracao e configuracao, nao entidade).
  - Manter string e enriquecer via variavel de ambiente (rejeitado: quebra o fluxo de Componente 09 editar via UI).
**Consequencias:**
  - Migration 009 aplicada em producao via `alembic upgrade head`. `alembic_version` passou de 008 -> 009.
  - `TEMPLATE_PADRAO` em `etiqueta_service.py` serve como fallback quando a chave nao esta carregada ou volta a ser string (defesa em profundidade).
  - Componente 09 vai poder editar todos os 4 campos via form sem nova migration.

---

## ADR-039 — Audit service helper centralizado
**Data:** 2026-04-09 (Wave 2, Sessao 8 — Componente 06)
**Contexto:** RNF-005 exige log de auditoria imutavel de toda movimentacao. Wave 2 tem apenas 2 operacoes de escrita (criar prova + atualizar config no Componente 09), mas Waves 3+ terao dezenas. Sem um helper centralizado, o codigo vai duplicar a logica de extracao de IP/UA, montagem de detalhes_json, e insercao em `audit_logs`.
**Decisao:** Criar `app/services/audit_service.py::log_audit(db, *, acao, usuario_id, prova_id=None, detalhes=None, request=None)`.
  - Extrai `ip_address` de `request.client.host` (protegido contra `client=None`).
  - Extrai `user_agent` de `request.headers["user-agent"]` e trunca a 2000 chars.
  - Insert direto em `audit_logs` via `db.add` + `db.flush` (sem commit — caller orquestra a transacao).
  - Se o caller fizer `rollback`, o audit log e descartado junto. Intencional: logar uma acao que nao aconteceu seria enganoso.
  - Triggers `trg_audit_logs_imutavel` ja bloqueiam UPDATE/DELETE a nivel de banco (RNF-005).
**Alternativas:**
  - Tabela + callback pattern por endpoint (rejeitado: duplica codigo).
  - Fila assincrona (outbox, Kafka, etc): rejeitado — overkill no volume esperado.
  - Log apenas em arquivo: rejeitado — RNF-005 exige que seja auditavel no banco.
**Consequencias:**
  - Caller sempre pode passar `request=None` em contextos de teste ou job — o service lida com ausencia gracefully.
  - Cobertura 100% via `test_audit_service.py` (happy, sem request, client=None, UA truncado).

---

## ADR-040 — State machine tabela-driven com stubs de execucao para Wave 3
**Data:** 2026-04-09 (Wave 2, Sessao 8 — Componente 06)
**Contexto:** RN-002 exige que as transicoes de status sigam a Matriz da Secao 5 dos Requisitos. RN-004 exige validacao de ator por transicao. RN-007 exige determinacao de rota pelo vendedor. O Componente 06 nao executa transicoes (criar != transitar — ADR abaixo), mas precisa de `determinar_rota` para exibir a rota projetada e precisa que a infraestrutura da maquina de estados esteja estavel antes da Wave 3 comecar.
**Decisao:** Criar `app/services/state_machine.py` com:
  - `TRANSICOES: dict[StatusProvaEnum, set[StatusProvaEnum]]` — tabela de arestas validas (Matriz Secao 5).
  - `ATORES_POR_TRANSICAO: dict[(from, to), set[SetorEnum]]` — setores autorizados por transicao especifica.
  - `determinar_rota(vendedor)` — MATRIZ -> PADRAO, FILIAL -> DIRETA. Funcional na Wave 2.
  - `transicao_e_valida`, `pode_cancelar`, `atores_permitidos`, `validar_transicao` — todos funcionais, usados por testes e pelo Wave 3 futuramente.
  - `executar_transicao(*args, **kwargs)` — **stub** que levanta `NotImplementedError("Wave 3")`. A assinatura final (body, signature, etc) sera decidida no Componente 11.
  - Excecoes customizadas: `TransicaoInvalidaError`, `AtorNaoAutorizadoError`, `RotaIndeterminavel`.
  - Cancelamento tratado em `pode_cancelar(status_atual)` separado (RN-005: qualquer estado ativo exceto RECEBIDA e CANCELADA, apenas setor STUDIO).
**Alternativas:**
  - State machine hardcoded no router (rejeitado: nao-testavel isolado, viola separacao de camadas).
  - Usar `transitions` (lib): rejeitado — overkill, extrapola as necessidades simples da Wave 2.
  - Deixar a tabela para Wave 3: rejeitado — `determinar_rota` precisa da infra pronta agora, e deixar para depois duplicaria trabalho.
**Consequencias:**
  - 26 testes unitarios cobrem todos os paths validos, invalidos, atores errados, admin bypass, cancelamento, consistencia da tabela.
  - Quando o Componente 11 (Wave 3) for implementado, basta preencher `executar_transicao` — toda a validacao ja esta pronta.
  - Cobertura 97% de `state_machine.py`.

---

## ADR-041 — Cleanup best-effort de objetos R2 orfaos apos falha no POST
**Data:** 2026-04-09 (Wave 2, Sessao 8 — Componente 06)
**Contexto:** O fluxo do ADR-031 tem uma race: o frontend faz PUT no R2 ANTES do POST final no backend. Se o POST falhar (duplicata, vendedor invalido, commit error, etc), o objeto no R2 fica orfao — ninguem vai referencia-lo, mas ele fica ocupando espaco.
**Decisao:** Toda falha em `POST /api/v1/provas/` **apos** o upload ter acontecido dispara `r2_delete(body.object_key)` via `_cleanup_r2` helper. A chamada e **best-effort**: se o delete tambem falhar, logamos `"orfao possivel"` com `logger.exception` mas **NAO** propagamos o erro para o cliente (o erro principal — duplicata, vendedor invalido — e que vai no response). Cenarios cobertos:
  - 409 duplicata de nro_requerimento
  - 404 vendedor nao encontrado
  - 422 vendedor nao e VENDEDOR / inativo / sem localizacao
  - 404 object_key nao existe no R2
  - 422 ContentLength > 10MB
  - 422 magic bytes invalidos
  - 500 commit do banco falhou
**Alternativas:**
  - Deixar os orfaos e limpar via cron (rejeitado na Wave 2; considerar na Wave 6 se o volume justificar).
  - Pre-alocar linha em "pending" antes do upload (rejeitado: complica RLS e fluxo).
  - Storage com TTL automatico (R2 nao oferece expiracao por objeto como nativa — so lifecycle rules por prefixo; adiado).
**Consequencias:**
  - Ocorrencias de "orfao possivel" no log de producao sao a metrica para decidir se precisamos de cleanup por cron no futuro.
  - 7 testes no `test_provas_api.py` verificam que `_cleanup_r2` e chamado em cada caminho de erro (`test_create_prova_duplicate_nro_req_cleans_up_r2`, etc).
  - O `object_key` fica registrado no `audit_logs.detalhes_json` quando a prova e criada com sucesso — permite auditoria "qual arquivo no R2 corresponde a prova X".

---

## ADR-042 — Rota projetada vs rota persistida (rota NULL na criacao)
**Data:** 2026-04-09 (Wave 2, Sessao 8 — Componente 06)
**Contexto:** RN-007 literal: "A rota de encaminhamento (padrao ou direta) e determinada automaticamente pela localizacao cadastrada do vendedor (Matriz ou Filial) **no momento da aprovacao**. Nao e possivel alterar a rota apos a confirmacao da aprovacao." O Backlog do Componente 06 tambem pede "determinacao de rota (padrao Matriz / direta Filial)", o que criou ambiguidade: a rota e definida na CRIACAO ou na APROVACAO?
**Decisao:** **Na criacao**, a rota **nao** e persistida em `provas_digitais.rota` (fica NULL). A rota apenas e **calculada e exibida** no response como `rota_projetada` — derivada de `vendedor.localizacao` via `state_machine.determinar_rota(vendedor)`. A persistencia em `provas_digitais.rota` vai acontecer na Wave 3, no handler de aprovacao (transicao RETIRADA -> APROVADA), quando o vendedor confirma via QR + assinatura. Isso respeita RN-007 ao pe da letra enquanto ainda entrega a funcionalidade visivel do backlog.
**Alternativas:**
  - Persistir `rota` na criacao (rejeitado: viola RN-007 literal; se o vendedor for reassignado ou trocar de localizacao entre a criacao e a aprovacao, teriamos inconsistencia).
  - Nao exibir rota nenhuma na UI ate a aprovacao (rejeitado: o backlog pede exibicao da rota no cadastro).
  - Criar um campo `rota_projetada` no banco (rejeitado: derivavel on-the-fly, nao precisa de storage).
**Consequencias:**
  - `ProvaResponse` tem DOIS campos: `rota` (NULL na Wave 2, setado na Wave 3) e `rota_projetada` (sempre calculado, exibido na UI).
  - O teste `test_create_prova_happy_path` confirma `rota == None` e `rota_projetada == "PADRAO"` para vendedor Matriz.
  - O teste `test_create_prova_vendedor_filial_projeta_rota_direta` confirma `rota_projetada == "DIRETA"` para vendedor Filial.
  - Wave 3, ao implementar a aprovacao, vai copiar `determinar_rota(vendedor)` para `prova.rota` dentro da mesma transacao da mudanca de status.

---

## ADR-043 — Whitelist estatica de chaves editaveis em `configuracoes_sistema`
**Data:** 2026-04-09 (Wave 2, Sessao 9 — Componente 09)
**Contexto:** RF-021 pede "tela de configuracoes com parametros configuraveis". A tabela `configuracoes_sistema` e um store key/value generico, entao tecnicamente qualquer chave nova poderia ser criada via POST/PATCH. Isso cria 3 problemas: (1) proliferacao descontrolada de chaves sem migration, sem tipo declarado, sem documentacao; (2) dificulta audit (quem criou `feature_flag_foo`?); (3) vaza detalhes internos do sistema se alguem listar a tabela inteira via API.
**Decisao:** Criar `EDITABLE_KEYS: frozenset` em `app/domain/schemas/configuracao.py` com **exatamente as chaves que a Wave 2 precisa** (`tempo_atraso_horas_uteis` e `template_etiqueta`). Endpoints `GET /` e `GET /{chave}` filtram por essa whitelist — chaves fora dela sao 404, mesmo que existam no banco. `PATCH /{chave}` rejeita com 404 antes mesmo de consultar o banco (`mock_db.execute.assert_not_called()` confirma no teste). **Adicionar uma chave nova exige 3 passos**:
  1. Migration Alembic para criar o seed (ou UPDATE de seed existente)
  2. Adicionar a constante em `schemas/configuracao.py`
  3. Adicionar validator dedicado em `VALIDATORS` (ADR-045)
**Alternativas:**
  - Aceitar qualquer chave, usar `JSONB` schema-less (rejeitado: vira zoo de config).
  - Tabela dedicada por tipo de config (rejeitado: overkill, 2 chaves atualmente).
  - Lista whitelisted mas mutavel via API (rejeitado: rompe o principio de que mudar a whitelist exige review de codigo).
**Consequencias:**
  - Qualquer proliferacao futura fica visivel no diff de codigo.
  - Testes `test_get_configuracao_nao_whitelisted` e `test_patch_chave_nao_whitelisted` protegem o contrato.
  - Chaves internas (ex: flags de debug) podem ser adicionadas ao banco via SQL direto sem aparecer na API — util para feature flags de sistema que nao devem ser expostos ao admin da UI.
  - Quando a Wave 4/5 adicionar 3a-4a chave, escala bem. Quando chegar em 5+, considerar extrair para modulo `app/services/config_registry.py`.

---

## ADR-044 — Audit trail detalhado com valor_anterior / valor_novo
**Data:** 2026-04-09 (Wave 2, Sessao 9 — Componente 09)
**Contexto:** RNF-005 exige log de auditoria imutavel de todas as movimentacoes. Para provas digitais isso e trivial (movimentacoes sao linha-por-transicao). Mas para `configuracoes_sistema` o audit precisa capturar O QUE mudou — sem isso, o registro diz "admin X alterou tempo_atraso em Y timestamp" sem diferenciacao entre "48 → 72" e "72 → 48". Operacionalmente, saber APENAS que mudou e insuficiente para investigar incidentes do tipo "por que o dashboard marcou tudo como atrasado ontem?".
**Decisao:** O handler PATCH de `/api/v1/configuracoes/{chave}` captura `valor_anterior` e `descricao_anterior` ANTES de mutar o objeto, e passa os dois para `log_audit(detalhes=...)` junto com `valor_novo` e `descricao_nova`:
```python
valor_anterior = config.valor
descricao_anterior = config.descricao
# ... aplica mudanca ...
await log_audit(db, acao="atualizar_configuracao", detalhes={
    "chave": chave,
    "valor_anterior": valor_anterior,
    "valor_novo": valor_normalizado,
    "descricao_anterior": descricao_anterior,
    "descricao_nova": config.descricao,
}, request=request)
```
O `detalhes_json` do `audit_logs` armazena isso como JSONB (PostgreSQL mantem tipo nativo — int permanece int, objeto permanece objeto). Assim, uma query `SELECT detalhes_json FROM audit_logs WHERE acao = 'atualizar_configuracao' AND detalhes_json->>'chave' = 'tempo_atraso_horas_uteis' ORDER BY created_at DESC` produz o historico legivel da chave sem precisar reconstruir de snapshots.
**Alternativas:**
  - Tabela dedicada `configuracoes_historico` (rejeitado: duplica a imutabilidade de `audit_logs`, exige trigger extra).
  - Salvar so o delta calculado (`delta: {logo_enabled: [true, false]}`) (rejeitado: calculo mais complexo, pior para ler, menos flexivel).
  - Salvar so o novo valor (rejeitado: exige consultar o audit_log anterior para saber o que mudou — operacionalmente pesado).
**Consequencias:**
  - Cada PATCH gera 1 linha de audit_log com historia completa auto-contida.
  - Validado no reproduce_configuracoes.py: os 2 primeiros audit_logs continham `{valor_anterior: 48, valor_novo: 72}` e `{valor_anterior: {...}, valor_novo: {...mostrar_data_criacao: true...}}` perfeitamente legiveis.
  - Contrato pode ser replicado para outros recursos mutaveis nas Waves 3+ (ex: `acao: "editar_usuario"` com `valor_anterior: {ativo: true}`, `valor_novo: {ativo: false}`).

---

## ADR-045 — Dispatch table de validators por chave
**Data:** 2026-04-09 (Wave 2, Sessao 9 — Componente 09)
**Contexto:** Cada chave em `configuracoes_sistema` tem um tipo de valor diferente (int, dict, futuros: bool, list, string). O endpoint PATCH e generico (`{valor: Any}` no body), entao a validacao precisa ser roteada para o validator correto baseado na chave da URL. Tres opcoes consideradas: (a) if/elif por chave dentro do handler; (b) Pydantic discriminator union (complexo para JSONB generico); (c) dispatch table `dict[chave, callable]`.
**Decisao:** Opcao (c) — dispatch table:
```python
VALIDATORS: dict[str, Callable[[Any], Any]] = {
    CHAVE_TEMPO_ATRASO: validar_tempo_atraso,
    CHAVE_TEMPLATE_ETIQUETA: validar_template_etiqueta,
}

def validar_valor_por_chave(chave: str, valor: Any) -> Any:
    return VALIDATORS[chave](valor)
```
Cada validator e uma funcao standalone com assinatura `(valor: Any) -> Any`, que retorna o valor normalizado (strings com strip, dicts com campos extras removidos) ou levanta `ConfiguracaoValidationError`. O handler PATCH chama apenas `validar_valor_por_chave(chave, body.valor)` e traduz a excecao para HTTP 422.
**Alternativas:**
  - `if chave == CHAVE_X: ...` (rejeitado: o handler fica N+1 branches quando N chaves existirem; viola Open/Closed).
  - Subclasses Pydantic por chave com discriminator (rejeitado: complexo demais para 2 chaves; JSONB generico nao e o caso de uso natural de discriminated unions).
  - Decorator-based registry (`@register_validator("tempo_atraso")`) (rejeitado: mesma complexidade do dict, menos legivel).
**Consequencias:**
  - Adicionar 3a chave no futuro e trivial: escrever `validar_foo(valor)`, adicionar `CHAVE_FOO: validar_foo` ao `VALIDATORS`, adicionar `CHAVE_FOO` ao `EDITABLE_KEYS`. Zero mudanca no handler.
  - Testes dos validators podem ser unitarios puros (sem HTTP, sem DB) — ja validados indiretamente via `test_configuracoes_api.py`.
  - Quando o numero de validators passar de ~5, considerar mover `VALIDATORS` para `app/services/config_validators.py` por separacao de concerns (por ora, fica em `schemas/configuracao.py` porque sao validadores de schema).

---

## ADR-037 — Offset-based pagination para listagem de provas
**Data:** 2026-04-09 (Wave 2, Sessao 10 — Componente 07)
**Contexto:** `GET /api/v1/provas/` precisa de paginacao. Duas opcoes principais: (a) offset-based (`LIMIT N OFFSET M`) ou (b) cursor-based (keyset `WHERE id > last_id LIMIT N`). Cursor e ideal para volumes grandes mas complica filtros dinamicos (cada mudanca reseta o cursor) e exige serializar o cursor no response.
**Decisao:** Offset-based, `LIMIT/OFFSET` com teto `page_size = 100`. Mesmo shape de `UserListResponse` da Wave 1 (items, total, page, page_size, pages) para o frontend reutilizar o padrao mental. Justificativas:
  1. Volume esperado na 3Studio e interno — centenas de provas/mes, nao milhoes. Offset grande (>10000) nunca vai acontecer no horizonte de planejamento.
  2. RF-013 lista multiplos filtros combinaveis (status + periodo + vendedor + cliente + rota + busca). Filtros combinados tornam cursor fragil: qualquer mudanca de filtro reseta o cursor.
  3. A UI precisa exibir "Pagina X de Y" e "Z resultados" (US-012). Cursor-based nao entrega isso naturalmente — exigiria um count adicional anyway.
  4. Indexes ja existentes cobrem as queries comuns: `idx_provas_status`, `idx_provas_status_created` (composto), `idx_provas_vendedor`, `idx_provas_created_at`. ORDER BY created_at DESC bate com `idx_provas_created_at`.
  5. Consistencia com Wave 1: `GET /api/v1/users` ja usa offset. Frontend tem padroes mentais e componentes reutilizaveis (hook, paginacao).
**Alternativas:**
  - Cursor-based puro (rejeitado: complica filtros, nao ajuda no volume real).
  - Offset SEM count (so next/prev) (rejeitado: UI precisa do total).
  - Paginacao por pagina sem limite de page_size (rejeitado: risco de DoS trivial — cliente pede page_size=100000, query trava).
**Consequencias:**
  - Paginacao simples e barata: 1 query de count + 1 query de data por request.
  - Offset N*M e O(M) pro Postgres — aceitavel ate ~10k linhas. Reavaliar se chegarmos la.
  - `page_size` maximo 100 protege contra DoS sem impactar UX (default 20, usuario raramente muda).

---

## ADR-038 — Busca textual via `ILIKE '%termo%'` na Wave 2
**Data:** 2026-04-09 (Wave 2, Sessao 10 — Componente 07)
**Contexto:** RF-012 pede pesquisa por nome e nro_requerimento. RF-013 pede filtro por cliente (tambem ILIKE). Opcoes: (a) `ILIKE '%termo%'`, (b) `pg_trgm` + GIN index com `similarity()` ou `ILIKE` indexado por trigrams, (c) `to_tsvector` + full-text search.
**Decisao:** Opcao (a) — ILIKE simples. Para os 3 campos (`nome`, `nro_requerimento` e `cliente`). Justificativas:
  1. RNF-001 exige listagem em <= 3s com 30 usuarios simultaneos. No volume Wave 2 (0-centenas de provas), seq scan com ILIKE executa em <50ms — tolera com folga.
  2. pg_trgm exige criar extensao + adicionar GIN index em cada coluna (`CREATE INDEX ON provas_digitais USING gin (nome gin_trgm_ops)`), que sao 3 indexes novos e um tamanho extra de armazenamento que o free tier do Supabase nao precisa.
  3. Full-text search com `to_tsvector` e mais sofisticado mas requer language dictionary (portugues), stemming, e ainda assim nao cobre "comeca com" nem "contem" sem adicional.
  4. Usuario tipico vai filtrar por "Gamma" ou "REQ-2026" — prefixos/substrings. ILIKE `%termo%` atende perfeitamente.
**Alternativas:**
  - `pg_trgm` desde ja (rejeitado para Wave 2: overhead de migration e storage sem ganho mensuravel no volume atual).
  - `to_tsvector` (rejeitado: muito pesado, nao necessario).
  - ILIKE com indexe btree no prefixo (`column LIKE 'termo%'` usaria o index, mas `'%termo%'` nao — o contrato com o usuario e "substring", nao "prefixo").
**Consequencias:**
  - Seq scan nas 3 colunas em cada query de listagem com filtro textual. Aceitavel ate ~10k linhas.
  - **Ponto de reavaliacao documentado**: se na Wave 4+ o dashboard comecar a reportar queries de listagem > 1s OU o advisor do Supabase flagar `seq_scan_high_count` em `provas_digitais`, criar migration que adiciona `pg_trgm` extension + GIN indexes em `nome`, `nro_requerimento`, `cliente`. Fix mecanico, zero breaking change.
  - Contrato publico da API nao muda se futuro refactor trocar para pg_trgm — o query param `busca=` continua o mesmo.

---

## ADR-046 — Scoping por setor replicado no backend via `_scoping_filter`
**Data:** 2026-04-09 (Wave 2, Sessao 10 — Componente 07)
**Contexto:** RLS em `provas_digitais` ja tem policies que restringem visibilidade por setor (`pol_provas_select` — admin ve tudo, VENDEDOR ve as proprias, MOTORISTA ve status=COM_MOTORISTA, CLICHERIA ve os 3 status de clicheria). Mas o backend usa `service_role` no Supabase pooler, que **bypassa RLS por design**. Se o endpoint `GET /api/v1/provas/` apenas confiasse no RLS, todos os usuarios autenticados veriam tudo via backend — desastre de privacidade.
**Decisao:** Replicar a logica das policies RLS diretamente no backend, via helper `_scoping_filter(user)` que retorna uma clausula SQLAlchemy `WHERE` base. Cada request de listagem aplica esse filtro PRIMEIRO, depois adiciona os filtros explicitos do usuario em cima (AND).
```python
def _scoping_filter(user: Usuario):
    if user.is_admin:
        return None
    if user.setor == SetorEnum.VENDEDOR:
        return ProvaDigital.vendedor_id == user.id
    if user.setor == SetorEnum.MOTORISTA:
        return ProvaDigital.status == StatusProvaEnum.COM_MOTORISTA
    if user.setor == SetorEnum.CLICHERIA:
        return ProvaDigital.status.in_(CLICHERIA_STATUSES)
    # STUDIO sem is_admin — combinacao invalida pos-ADR-018
    return func.false()
```
O endpoint usa `get_current_user` (nao `get_admin_user`) porque a listagem e aberta a qualquer setor — mas com visibilidade restrita pelo scoping. Filtros explicitos do usuario sao adicionados em cima do filtro base (AND) — exemplo: MOTORISTA filtrando `status=CRIADA` retorna vazio porque o filtro base ja exige `status=COM_MOTORISTA`.
**Alternativas:**
  - Remover service_role no pooler e usar a role do usuario autenticado (rejeitado: quebra pattern de Wave 1, impoe passar JWT para asyncpg que nao e trivial, tira a conveniencia de audit_logs funcionarem com `updated_by=admin.id`).
  - Delegar para RLS via `SET LOCAL role authenticated; SET LOCAL request.jwt.claims TO ...` dentro de cada transaction (rejeitado: complexo, fragil, exige alterar `get_db`).
  - Fazer check no Python apos buscar tudo, filtrando em memoria (rejeitado: trivialmente quebra RNF-001 em qualquer volume).
**Consequencias:**
  - Endpoint seguro por construcao — scoping aplicado por SQL, nao por runtime check vulneravel a bugs.
  - Testes unitarios com `_compiled_sql` verificam que a clausula WHERE correta aparece para cada setor (`test_list_vendedor_scope_own_provas`, `test_list_motorista_scope_com_motorista`, `test_list_clicheria_scope_status`).
  - Validado contra banco real no seed script: vendedor Mario Souza ve apenas as proprias provas (7 — todas as seed foram criadas com ele como vendedor), admin ve 7 total.
  - **Manutencao**: quando a semantica das policies RLS mudar (ex: adicionar um setor novo), tem que atualizar AMBOS — `_scoping_filter` aqui E os arquivos `.sql` em `backend/migrations/rls/`. Consistencia e responsabilidade do review.
  - Defesa em profundidade: RLS continua ativa para proteger acesso direto via Supabase client do frontend (caso alguem tente). Backend e mais rigoroso.

---

## ADR-047 — Filtro `rota` usa a coluna persistida, nao a projetada
**Data:** 2026-04-09 (Wave 2, Sessao 10 — Componente 07)
**Contexto:** `ProvaDigital.rota` e NULL ate que a prova seja aprovada (RN-007 + ADR-042). Na Wave 2, nenhuma prova e aprovada — todas as provas criadas tem `rota=NULL`. RF-013 pede filtro por "rota (padrao/direta)". Poderia interpretar como (a) filtrar pela coluna persistida `provas_digitais.rota`, ou (b) derivar a rota "projetada" a partir da `localizacao` do vendedor via JOIN e filtrar por isso.
**Decisao:** Opcao (a) — filtrar pela coluna persistida `provas_digitais.rota`. Justificativas:
  1. Fidelidade ao modelo: a rota so existe de fato quando a prova e aprovada. Filtrar por algo que ainda nao foi decidido e enganar o usuario.
  2. Semantica consistente entre Waves: quando a Wave 3 entrar em producao e provas forem aprovadas, o filtro `rota=PADRAO` vai naturalmente comecar a retornar resultados sem nenhuma mudanca de codigo.
  3. Alternativa (b) exigiria JOIN com `usuarios.localizacao` na query — acopla dois conceitos que deveriam ficar separados (a rota e determinada no momento da aprovacao, nao no momento da consulta).
  4. Na Wave 2, o filtro rota retorna zero resultados para quase tudo (so as provas criadas diretamente com rota nao-NULL aparecem). Isso e documentado no frontend via "—" na coluna rota quando NULL, e aceitavel enquanto a Wave 3 nao chegar.
**Alternativas:**
  - Opcao (b) com JOIN (rejeitado: acopla conceitos, confunde semantica).
  - Adicionar um campo `rota_projetada` no banco (rejeitado: derivavel on-the-fly na criacao e viola DRY — ja existe em `ProvaResponse.rota_projetada` mas nao em `ProvaListItem` porque nao precisa na listagem).
  - Filtro hibrido com flag `incluir_projetada=true` (rejeitado: API complexa por um caso de uso marginal pre-Wave 3).
**Consequencias:**
  - Na Wave 2, o filtro `rota=PADRAO` ou `rota=DIRETA` retorna apenas provas que **manualmente** foram criadas com rota nao-NULL (caso acontece nos seeds de teste).
  - Validado no seed script: `filtro rota=PADRAO + busca LIST-TEST` retornou 2 itens (as duas provas seed que tem rota persistida, COM_MOTORISTA e ENVIADA_PARA_CLICHERIA).
  - Na Wave 3, o filtro vira util sem mudanca de codigo — e exatamente o que se quer.
  - Decisao documentada no frontend: coluna Rota exibe "—" para NULL, e o filtro Rota tem opcao "Todas" como default. Usuario Wave 2 entende a semantica.

---

## ADR-048 — Filtro de periodo com `fim` inclusivo
**Data:** 2026-04-09 (Wave 2, Sessao 10 — Componente 07)
**Contexto:** RF-013 pede "filtros por periodo". Dois inputs de data (`periodo_inicio`, `periodo_fim`). A pergunta classica: quando o usuario seleciona `2026-04-01 ate 2026-04-09`, ele espera ver provas criadas no dia 09? Ou o dia 09 e cortado as 00:00? A primeira interpretacao e o que humano entende como "periodo inclusivo" — a segunda e o que o SQL faria naive com `created_at <= '2026-04-09'`.
**Decisao:** `periodo_inicio` e `periodo_fim` sao ambos **inclusivos no dia todo**. Implementacao:
```python
if periodo_inicio:
    inicio_dt = datetime(y, m, d, tzinfo=UTC)
    filters.append(created_at >= inicio_dt)
if periodo_fim:
    fim_dt = datetime(y, m, d, tzinfo=UTC) + timedelta(days=1)
    filters.append(created_at < fim_dt)  # note: < e NAO <=
```
O `fim + 1 day` com `<` e o padrao canonico para incluir todo o dia final sem depender de ajustes de timezone ou frações de segundo.
**Alternativas:**
  - `created_at <= fim` (rejeitado: corta as 23:59:59 do dia final por default, excluindo eventos do dia).
  - `created_at::date BETWEEN inicio AND fim` (rejeitado: cast de `created_at::date` impede uso de index em `created_at`).
  - Forcar o usuario a informar timestamp completo com horario (rejeitado: UX terrivel).
**Consequencias:**
  - Query param continua `YYYY-MM-DD` (simples de usar na URL e no date picker do browser).
  - Index `idx_provas_created_at` e usado normalmente (comparacao e com `timestamptz`).
  - Timezone: o backend usa UTC em toda a aplicacao. Se a 3Studio estiver em America/Sao_Paulo, a "data de criacao" pode exibir 1 dia diferente em alguns casos de borda (prova criada as 23:00 BRT aparece como dia +1 em UTC). Aceitavel para Wave 2 — documentar se reportado como bug.
  - Teste `test_list_filter_periodo` confirma que o SQL compilado contem `'2026-04-01'` e `'2026-05-01'` (fim + 1 dia).

---

## ADR-049 — Scoping de GET /{id} reutiliza `_scoping_filter` do Componente 07
**Data:** 2026-04-09 (Wave 2, Sessao 11 — Componente 08)
**Contexto:** Os endpoints de detalhe da prova (`GET /{id}`, `/imagem-url`, `/movimentacoes`, `/etiqueta.pdf`, `/qr-code.png`) precisam respeitar a mesma semantica de visibilidade por setor ja implementada na listagem (Componente 07, ADR-046). A opcao naive seria reimplementar cada um com o mesmo codigo, mas isso duplica logica critica de seguranca — qualquer bug de scoping em um lugar nao propaga para os outros.
**Decisao:** Reutilizar o helper `_scoping_filter(user)` do Componente 07 em **todos** os 5 endpoints de detalhe, via um segundo helper privado `_carregar_prova_com_scoping(db, prova_id, user)` que encapsula:
  1. SELECT de `ProvaDigital` JOIN `Usuario` com `WHERE prova.id == prova_id`
  2. Aplica o scoping de `_scoping_filter` por cima
  3. Retorna `(prova, vendedor_nome, vendedor_localizacao) | None`
  4. **404 (nao 403)** quando retorna None — para nao vazar existencia da prova. Um vendedor tentando acessar prova de outro vendedor recebe "Prova nao encontrada" em vez de "Acesso negado", garantindo que nao seja possivel inferir a existencia de provas via probing.
**Alternativas:**
  - Reimplementar scoping em cada endpoint (rejeitado: duplica codigo de seguranca).
  - Usar um decorator `@scoped_prova` (rejeitado: FastAPI nao tem pattern nativo para dependencies que pegam query params + db simultaneamente).
  - Delegar para RLS via SET LOCAL role (rejeitado: mesma rejeicao do ADR-046).
  - 403 em vez de 404 quando o scoping esconde (rejeitado: vaza existencia).
**Consequencias:**
  - Qualquer mudanca futura na semantica de scoping acontece em `_scoping_filter` apenas, e propaga automaticamente para todos os 5 endpoints.
  - Testes de scoping em cada endpoint mockam `db.execute.side_effect = [_detail_row_none()]` e esperam 404, padronizando o assert.
  - Se a Wave 3 adicionar setores novos ou mudar regras de visibilidade, so preciso tocar em um lugar.

---

## ADR-050 — Endpoint dedicado para URL assinada da imagem (`/imagem-url`)
**Data:** 2026-04-09 (Wave 2, Sessao 11 — Componente 08)
**Contexto:** A tela de detalhe precisa exibir a arte da prova. A imagem vive no R2 com acesso privado — qualquer GET direto ao bucket retorna 403. A unica forma de exibir e via URL pre-assinada (`generate_presigned_url('get_object', ...)`). Duas opcoes de design: (a) embutir a URL assinada no proprio `ProvaResponse` que o `GET /{id}` ja retorna, ou (b) endpoint dedicado `GET /{id}/imagem-url` que a tela chama separadamente.
**Decisao:** Endpoint dedicado — Opcao (b). Justificativas:
  1. **URLs assinadas tem TTL curto (15 min — ver abaixo)**. Se embutirmos na response de detalhe, qualquer uso futuro que cacheie ou reexiba os dados da prova (ex: listagem, dashboard) vai gerar URLs assinadas desnecessariamente — desperdicio de CPU (HMAC-SHA256) e latencia.
  2. **Listagem de provas (Componente 07) nao precisa da URL da imagem**. Se embutida no `ProvaResponse`, listar 100 provas geraria 100 URLs assinadas. Com endpoint dedicado, listar so puxa o `imagem_url` (object key) e nada mais.
  3. **Tratamento de falha isolado**: se o R2 estiver temporariamente indisponivel quando o usuario abre a tela de detalhe, o `GET /{id}` continua funcionando (dados da prova) e apenas o `GET /{id}/imagem-url` falha com 502. O frontend usa `Promise.allSettled` no `useProvaDetail` para tolerar essa falha parcial — a UI exibe dados + placeholder "Falha ao carregar arte" em vez de tela toda em erro.
  4. **Cache do browser respeitado separadamente**: o endpoint de detalhe tem `Cache-Control` diferente do endpoint de imagem (que nao cacheia por ter TTL dinamico).
**Parametros da URL assinada:**
  - `expires_in = 900` (15 minutos). Suficiente para o usuario consumir a tela, visualizar a arte e baixar o PDF sem a URL expirar. Muito mais que isso vira window de replay attack (pequeno, mas existe).
  - Sem refresh automatico no frontend — Q08.1 aprovada pelo Mario. Se o usuario ficar >15min com a tela aberta e recarregar a imagem por qualquer razao, vai pegar erro — mas no uso real e improvavel.
**Alternativas:**
  - Embutir no `ProvaResponse` (rejeitado — os 4 motivos acima).
  - Endpoint unificado `GET /{id}/complete` que retorna dados + imagem_url (rejeitado — mistura preocupacoes).
  - Bucket publico com URLs permanentes (rejeitado — viola RNF-005 e expoe artes).
**Consequencias:**
  - Frontend faz 3 requests na tela de detalhe (dados, imagem-url, movimentacoes) em paralelo via `Promise.allSettled` — custo negligivel, tolerancia a falhas parciais.
  - Testes do endpoint mockam `r2_signed.generate_presigned_get_url` para nao depender de R2 real.
  - Se o frontend quiser exibir thumbnails na listagem no futuro (nao e requisito), vai precisar de um endpoint separado tipo `/{id}/thumbnail-url` ou um campo `imagem_thumbnail_url` no list item.

---

## ADR-051 — Endpoint `/movimentacoes` com contrato pronto mas vazio na Wave 2
**Data:** 2026-04-09 (Wave 2, Sessao 11 — Componente 08)
**Contexto:** O Componente 08 pede "Historico de movimentacoes (placeholder estruturado — a timeline visual rica vem na Wave 3, mas o endpoint e a estrutura de dados ja devem existir)". Duas interpretacoes: (a) NAO criar o endpoint na Wave 2, deixar apenas o tipo TypeScript pronto no frontend; (b) criar o endpoint, handler real e schema completo, mas com query que sempre retorna vazio na Wave 2 (porque nenhuma transicao aconteceu).
**Decisao:** Opcao (b) — endpoint completo, query real, contrato estavel desde ja. Justificativas:
  1. **Testabilidade**: o endpoint tem `test_get_movimentacoes_empty_on_wave2`, `test_get_movimentacoes_scoping_404`, `test_get_movimentacoes_not_found` — 3 testes que blindam o contrato HTTP, scoping e paths de erro. Sem o endpoint, esses testes seriam impossiveis ate a Wave 3.
  2. **Zero mudanca de handler na Wave 3**: quando a primeira transicao for inserida na Wave 3, o endpoint ja faz o SELECT real em `movimentacoes JOIN usuarios` e retorna via `MovimentacaoResponse`. O codigo do handler nao muda — so comeca a retornar dados.
  3. **Frontend ja consome**: o `useProvaDetail` do Componente 08 ja chama `/movimentacoes` no mount e a pagina detalhe ja tem o JSX para renderizar a lista (que fica escondido pelo `if (total === 0) ... else` — placeholder vs lista).
  4. **Custo zero**: handler sao ~20 linhas, 3 testes sao ~40 linhas. Ganho de robustez >> custo.
**Contrato**: `GET /api/v1/provas/{id}/movimentacoes` retorna `MovimentacaoListResponse { items: MovimentacaoResponse[], total: int }`. `MovimentacaoResponse` inclui `usuario_nome`, `usuario_setor`, `status_anterior`, `status_novo`, `motivo_reprovacao`, `ciclo`, `rota_no_momento`, `created_at`. **NAO inclui `assinatura_digital`** — fica como prova server-side apenas (BYTEA no banco, nunca serializada para JSON).
**Alternativas:**
  - Deixar para a Wave 3 (rejeitado pelos 4 motivos).
  - Retornar 501 Not Implemented na Wave 2 (rejeitado — pior UX, vai confundir o frontend que nao sabe diferenciar "ainda nao implementado" de "sem movimentacoes").
  - Schema diferente do usado na Wave 3 (rejeitado — obrigaria mudanca de contrato depois).
**Consequencias:**
  - Wave 3 herda o endpoint pronto e so precisa implementar os handlers de `POST /{id}/transicao` que inserem linhas em `movimentacoes`. A tela de detalhe do Componente 08 **nao precisa ser tocada** — quando as transicoes comecarem a acontecer, a lista popula automaticamente.
  - Primeiro smoke real da timeline vai ser na primeira sessao da Wave 3, quando inserirmos a primeira movimentacao.

---

## ADR-052 — Endpoint dedicado `GET /qr-code.png` com cache privado 5 min
**Data:** 2026-04-09 (Wave 2, Sessao 11 — Componente 08)
**Contexto:** Pedido explicito do Mario durante o planejamento: "ao clicar para visualizar prova, tenha um botao ou algo que nos mostra a etiqueta e o qr code da respectiva prova". O PDF da etiqueta ja inclui o QR code embutido, mas expor o QR code isolado em tamanho grande facilita a leitura via celular (usuario nao precisa imprimir o PDF todo para escanear). Como entregar isso?
**Decisao:** Criar um endpoint dedicado `GET /api/v1/provas/{id}/qr-code.png` que retorna o `etiquetas.qr_code_image` BYTEA como streaming PNG puro, com `Cache-Control: private, max-age=300`.
**Detalhes:**
  - Auth `get_current_user` + `_scoping_filter` (ADR-049).
  - SELECT so do campo `Etiqueta.qr_code_image` (BYTEA ja armazenado pelo Componente 06, gerado via `qrcode_service.gerar_imagem_qr` no ato da criacao).
  - `Response(content=qr_bytes, media_type="image/png", headers={"Content-Disposition": 'inline; filename="qr-code.png"', "Cache-Control": "private, max-age=300"})`.
  - **`Cache-Control: private, max-age=300`**: o QR code e imutavel apos criacao (RN-001 — unico e nao-reutilizavel). Cache de 5 min permite que re-abrir o modal varias vezes na mesma sessao nao refaz o request. `private` impede caches intermediarios (proxy corporativo) de armazenar.
  - **Sem regerar**: o PNG ja esta armazenado como BYTEA. O endpoint so serve bytes. Latencia <10ms.
**Alternativas:**
  - Extrair o QR code do PDF no frontend via biblioteca (rejeitado — requer lib pesada tipo pdf.js, complexo, QR ja esta no BYTEA).
  - Embutir base64 no `ProvaResponse` (rejeitado — 700-1500 bytes extra em cada detalhe, mesma critica do ADR-050 sobre URLs assinadas).
  - Regenerar o PNG a cada request via `qrcode_service.gerar_imagem_qr` (rejeitado — desperdicio, ja temos o BYTEA salvo imutavel).
  - Endpoint unificado `/etiqueta-assets` que retorna PDF + QR como multipart (rejeitado — complexo, poucos benefits).
**Consequencias:**
  - O modal `VisualizarEtiquetaModal` do frontend faz 2 fetches em paralelo (`/etiqueta.pdf` + `/qr-code.png`), converte ambos para blob URL via `URL.createObjectURL`, e exibe o PDF em iframe e o PNG em `<img>` com `image-rendering: pixelated` (preserva bordas das celulas).
  - 3 testes cobrem o endpoint: happy path com magic bytes PNG verificados + Cache-Control header, scoping 404, etiqueta ausente 404.
  - Quando o Componente 10 (Wave 3) implementar o scanner de camera, **pode reutilizar o mesmo endpoint** se precisar exibir o QR da prova na tela do scanner por qualquer razao (debug, confirmacao visual).

---

## ADR-030 — Criar segundo administrador operacional antes da Wave 2 entrar em uso real
**Data:** 2026-04-09 (Wave 1, Sessao 6 — auditoria de validacao final)
**Status:** EXECUTADO em Sessao 7 (2026-04-09, abertura da Wave 2). Resultado:
  - `scripts/create_second_admin.py` criado como script one-shot que respeita o fluxo do endpoint `POST /api/v1/users` (cria em `auth.users` via GoTrue Admin API, depois INSERT em `public.usuarios`, com rollback de auth em caso de falha no DB).
  - Conta criada: `ops@3studio.com.br` / "Operacao 3Studio" / setor=STUDIO / is_admin=true / localizacao=null / created_by=null. IDs: `public.usuarios.id=0c20be3e-50f3-40b1-b07b-ebacccd66760`, `auth_uid=8e230fdf-2a9e-44f7-a0d6-2bfa0cdbcd96`.
  - Senha gerada via `secrets.token_urlsafe(16)` (128 bits). Entregue ao Mario no stdout do script para salvamento manual no gerenciador de senhas corporativo.
  - Contagem final: 2 admins ativos (Admin Master original + Operacao 3Studio novo). `_count_other_active_admins` agora sempre devolve >= 1, eliminando o SPOF organizacional.
  - **Acao manual pendente:** Mario salvar a senha no gerenciador + remover `scripts/create_second_admin.py` apos confirmacao.
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

---

## ADR-053 — Fonte Unicode DejaVu Sans para geracao de PDF
**Data:** 2026-04-09 (Wave 2, Sessao 12 — auditoria + hardening pos-entrega Wave 2)
**Contexto:** A auditoria da Sessao 12 detectou um bug **critico latente** no `etiqueta_service.py`: a fonte builtin `Helvetica` do `fpdf2` e **Latin-1 only**. Qualquer caractere fora do range Latin-1 (U+0000..U+00FF) levanta `FPDFUnicodeEncodingException` e quebra a geracao do PDF. Caracteres comuns que disparam o bug em cenario real de producao:
  - `€` (euro, U+20AC) — simbolo monetario comum em nomes de promocoes
  - `'` `'` `"` `"` (smart quotes, U+2018/U+2019/U+201C/U+201D) — **gerados automaticamente pelo Word e Google Docs** quando o usuario digita aspas simples/duplas
  - `–` `—` (en-dash/em-dash, U+2013/U+2014) — idem, auto-gerados por editores
  - CJK, emoji, simbolos matematicos, etc
  Vetor realista: operadora da 3Studio cola um nome de prova vindo do Word (`"Rotulo 'Natal 2026' – Edicao"`) e a criacao da prova vira 500 silencioso. Pior: como o `gerar_pdf` originalmente rodava APOS o commit da prova, o banco ficava com a prova criada e o cliente nao conseguia baixar a etiqueta — inconsistencia operacional.
  Acentos comuns (`ç`, `ã`, `é`, `á`, `ô`) estao DENTRO de Latin-1 e funcionavam, entao o bug so aparecia em chars menos comuns — facil de passar despercebido em testes.
**Decisao:** Substituir `Helvetica` por `DejaVu Sans` via `pdf.add_font(...)`:
  - Baixar `DejaVuSans.ttf` (Regular, ~757KB) e `DejaVuSans-Bold.ttf` (~706KB) do release oficial `dejavu-fonts/dejavu-fonts@version_2_37` no GitHub.
  - Commitar os TTFs em `backend/app/services/fonts/` junto com o `LICENSE` (Bitstream Vera Font License — permissiva, uso comercial + redistribuicao permitidos).
  - `etiqueta_service.py` registra ambos via `_register_fonts(pdf)` no inicio de cada `gerar_pdf()`. Path absoluto resolvido via `Path(__file__).resolve().parent / "fonts"` — independente de cwd, mesmo padrao do `config.py`.
  - Italico **nao** bundled — economiza ~700KB e a unica linha italica antes (legenda do QR) foi trocada por regular em tamanho menor com mesmo destaque visual.
  - `_register_fonts` levanta `RuntimeError` explicito se os TTFs faltarem no deploy (falha rapida, erro acionavel).
  - Chars fora do range coberto pelo DejaVu Sans (CJK, emoji) renderizam como glyph faltando com warning no log — **nao crashea mais**. Aceitavel como degradacao graciosa.
**Alternativas:**
  - **Sanitizar strings pre-render** (transliterar via `unicodedata.normalize('NFKD').encode('latin-1', 'ignore')`): rejeitado — perde informacao visivel para o usuario, viola principio de menor surpresa.
  - **Noto Sans ou Liberation Sans**: rejeitado — DejaVu e a referencia canonica em `fpdf2` docs e tem cobertura maior (Latin Extended + Greek + Cyrillic + simbolos matematicos).
  - **Fonte CJK tambem (NotoSansCJK)**: rejeitado — +10MB no repo, nenhum caso de uso real pede renderizar chineses na etiqueta. Se aparecer futuramente, adiciona depois.
  - **CDN / download no deploy**: rejeitado — introduz dependencia externa no deploy Railway, quebra offline builds.
**Consequencias:**
  - **+1.5MB no repo** (TTFs commitados). Aceitavel — muito menor que o tamanho do `node_modules` do frontend.
  - **Testes novos** em `test_etiqueta_service.py`: `test_pdf_acentos_latin1_ok`, `test_pdf_euro_simbolo_ok`, `test_pdf_smart_quotes_ok`, `test_pdf_em_en_dash_ok`, `test_pdf_chars_fora_do_font_nao_crashea`.
  - Cobertura do `etiqueta_service.py`: 98% → 97% (adicionou `_register_fonts` com branch de RuntimeError que nao e exercitado nos testes).
  - Deploy Railway: precisa incluir o diretorio `backend/app/services/fonts/` no build. Como e parte do tree de `backend/`, o default do buildpack ja copia.
  - **Se a fonte for substituida no futuro** (rotacionada, atualizada, etc), `_register_fonts` e o unico lugar que precisa ser editado.

---

## ADR-054 — `gerar_pdf` antes do commit em `POST /api/v1/provas/`
**Data:** 2026-04-09 (Wave 2, Sessao 12 — auditoria + hardening)
**Contexto:** No design original do Componente 06 (Sessao 8), o fluxo era: (1) validar, (2) INSERT atomico prova+etiqueta+audit_log, (3) commit, (4) **`gerar_pdf` APOS commit**, (5) response. O argumento era que `gerar_pdf` usa `nova_prova.created_at` que so existe apos refresh — ordem "natural".
  Problema detectado na auditoria da Sessao 12: `gerar_pdf` pode **falhar** por varias razoes legitimas (fonte ausente, template JSONB invalido, caractere Unicode — ver ADR-053, erro de IO no Pillow, etc). Com o gerar_pdf depois do commit, uma falha deixava a prova **persistida no banco** mas o cliente recebia HTTP 500 sem PDF — estado inconsistente, dificil de recuperar (re-tentar da 409 duplicate, nao ha endpoint de "gerar etiqueta" para recuperar).
**Decisao:** Reordenar `create_prova` em `provas.py`:
  1. Validar (nro_req + vendedor + R2 magic bytes)
  2. **Carregar template + gerar PDF** (em `try/except` dedicado)
  3. Se qualquer coisa falhar aqui, retornar **HTTP 422** com mensagem descritiva, limpar R2 via `_cleanup_r2`, NAO tocar no banco
  4. **Depois** INSERT atomico prova + etiqueta + audit_log
  5. Commit
  6. `db.refresh` + monta response usando os bytes do PDF ja gerados
  `created_at` do PDF e gerado no backend via `datetime.now(tz=timezone.utc)` e usado tambem no response. O `now()` do Postgres escreve um timestamp proximo (mesmo segundo, modulo skew), e o `db.refresh` substitui o valor do modelo ORM — mas como o PDF ja foi renderizado com o timestamp gerado no Python, eh esse que o usuario ve no PDF impresso. Diferenca entre os dois e <100ms em cenario normal, invisivel na granularidade do display (`%d/%m/%Y %H:%M`).
**Alternativas:**
  - **Gerar PDF depois do commit e, em caso de falha, rollback** (impossivel — commit ja aconteceu).
  - **Gerar PDF depois do commit com endpoint de retry**: `POST /provas/{id}/regenerar-etiqueta`: rejeitado — nova superficie de API, novo audit log, UX pior (usuario precisa saber que existe esse endpoint).
  - **Transacao em 2 fases (saga compensatoria)**: overkill — commit+delete seria a compensacao, mas uma prova CANCELADA so via trigger de imutabilidade, entao ainda deixaria rastro.
  - **Pre-gerar PDF em memoria sem `created_at`** e editar depois: rejeitado — complexo e fragil (precisa re-render parcial).
**Consequencias:**
  - **Cenario de falha de PDF** agora retorna 422 com mensagem explicita + cleanup R2 + zero mudanca no banco. Teste `test_create_prova_pdf_generation_failure_rollsback_before_commit` garante que `db.commit` **nunca** e chamado quando `gerar_pdf` lanca.
  - **Teste pre-existente** `test_create_prova_commit_failure_rollback_and_cleanup` precisou de 1 `_scalar(DEFAULT_TEMPLATE)` adicional no `side_effect` do mock_db — porque o template agora e carregado antes do commit. Ajuste mecanico, semantica do teste inalterada.
  - Ordem de `db.execute` em `create_prova` passou de 2 para **3** chamadas antes da primeira escrita: nro_req check → vendedor FOR UPDATE → template. Isso e 1 query a mais por request de criacao, **desprezivel** (template e UNIQUE + whitelist = index hit direto).
  - **Defesa em profundidade** contra C1 (ADR-053): mesmo se um caractere incomum passar pela suite de testes, o commit nao acontece e o estado permanece consistente.

---

## ADR-055 — Normalizacao case-insensitive do `nro_requerimento`
**Data:** 2026-04-09 (Wave 2, Sessao 12 — auditoria + hardening)
**Contexto:** O constraint `UNIQUE` em `provas_digitais.nro_requerimento` e **case-sensitive** no Postgres. O validator Pydantic da Sessao 8 fazia apenas `.strip()`. Resultado: dois admins podiam criar `REQ-2026-001` e `req-2026-001` simultaneamente — ambos passam e geram duas linhas distintas. Operacionalmente **e bug**: numero de requerimento eh um identificador humano que pessoas memorizam sem se importar com caixa.
  Cenario real: vendedor envia o nro por WhatsApp em minusculas, o admin A copia e cola como veio, admin B relembra de memoria e digita em maiusculas. Ambos criam a mesma "entidade" duas vezes.
**Decisao:** Criar helper `_normalize_nro_requerimento(v: str) -> str` em `app/domain/schemas/prova.py`:
  1. `v.strip().upper()`
  2. Rejeita vazio pos-strip
  3. Valida charset via `NRO_REQ_RE` (existente)
  4. Retorna a versao normalizada
  Aplicado em **ambos** os validators Pydantic: `UploadUrlRequest._valida_nro_req` e `ProvaCreateRequest._valida_nro_req`. Qualquer requisicao HTTP passa por um dos dois — duas tentativas simultaneas com `REQ-001` e `req-001` agora geram o **mesmo valor** no DB → uma cai no 409 duplicate normal.
**Alternativas:**
  - **Camada 2 — index case-insensitive no banco** (`CREATE UNIQUE INDEX ... ON provas_digitais (lower(nro_requerimento))`): considerada, rejeitada apos consulta com Mario. Motivo: a Camada 1 (normalizacao no validator) cobre 100% dos writes reais via HTTP (unica superficie de escrita do dominio). Camada 2 so agregaria beneficio se houver bugs futuros ou SQL direto — marginal. Manter Wave 0 intocada foi preferivel a introduzir uma migration com custo de validacao de colisao pre-existente.
  - **Lowercase em vez de uppercase**: arbitrario. Escolhi uppercase porque convencoes tipo `REQ-`, `NF-`, `INV-` sao renderizadas quase sempre em caixa alta em notas fiscais fisicas. Ambos seriam equivalentes.
  - **Normalizar no banco via `GENERATED COLUMN`**: funcionaria mas exigiria migration + mudanca de constraint — violacao do escopo Wave 2.
**Consequencias:**
  - **Testes novos** em `test_schemas.py`: classe `TestNormalizeNroRequerimento` (6 casos), `TestUploadUrlRequestNormalization` (1), `TestProvaCreateRequestNormalization` (1).
  - **Payload do cliente muda** visivelmente: `{"nro_requerimento": "req-001"}` agora volta `"REQ-001"` no response — frontend nao precisa mudar porque ele apenas re-exibe o valor do response.
  - Linhas legado no banco (se houver `req-001` pre-normalizacao) nao sao afetadas. Se for necessario, fazer migration 1-off para normalizar existentes — nao fiz agora porque producao ainda tem volume zero/baixo de Wave 2.
  - **Pendencia futura**: quando o volume crescer e aparecer risco real de bugs bypass, avaliar Camada 2 (index case-insensitive) como defesa em profundidade.

---

## ADR-056 — Whitelist fechada de `template_etiqueta.nome`
**Data:** 2026-04-09 (Wave 2, Sessao 12 — auditoria + hardening)
**Contexto:** O validator `validar_template_etiqueta` (Sessao 9, Componente 09) aceitava qualquer string nao-vazia no campo `nome`. A UI do Componente 09 marcava o input como `readOnly` (cosmetico), mas o PATCH do backend aceitava `{"nome": "<script>alert(1)</script>"}` sem objecao. Nao era XSS porque `nome` nao e renderizado em lugar nenhum (nem no PDF, nem na UI) — mas era um buraco de validacao: o contrato sugere que so `"padrao"` e valido, o codigo nao enforca.
  Violacao do principio "make invalid states unrepresentable" + risco latente se no futuro alguem renderizar `nome` em algum lugar sem escape.
**Decisao:** Criar `TEMPLATE_NOMES_VALIDOS: frozenset[str] = frozenset({"padrao"})` em `configuracao.py`. `validar_template_etiqueta` passa a:
  1. Checar `isinstance(nome, str)` → rejeita com mensagem generica
  2. `.strip()` e checar contra a whitelist → rejeita com mensagem listando os validos
  3. Retornar o nome normalizado
  Quando Waves 4+ introduzirem um template novo (ex: "compacto", "a5_paisagem"), basta adicionar na whitelist + (eventualmente) um branch no `etiqueta_service.py` se o layout nao for derivavel apenas dos flags `formato`/`logo_enabled`/`mostrar_data_criacao`.
**Alternativas:**
  - **`Enum` Python**: mais idiomatico mas nao serializa limpo em JSONB e exige mudanca no schema Pydantic `valor: Any`.
  - **Regex de charset seguro** (so `[a-z_]+`): rejeitado — permite proliferacao de nomes sem review de codigo.
  - **Normalizar o nome** (`slugify`): rejeitado — muda silenciosamente o input do usuario, surpresa.
**Consequencias:**
  - **Testes novos** em `test_schemas.py`: classe `TestValidarTemplateEtiquetaNomeWhitelist` com 5 casos (happy path + rejeicao de `custom`, `<script>`, vazio, nao-string).
  - Contrato API mudou: um PATCH que antes aceitava `{"nome": "custom", ...}` agora retorna 422. **Nenhum cliente real deve quebrar** porque (a) a UI nunca expos edicao de `nome`, e (b) o seed inicial e `"padrao"`, que permanece valido.
  - Template de teste usado em `test_configuracoes_api.py` ja usa `"padrao"` — zero mudanca nos testes existentes.
  - **Evolucao futura**: quando o Wave 4/5/6 adicionar templates, o diff do codigo mostra explicitamente a mudanca na whitelist — auditable.

---

## ADR-057 — Remocao do parametro morto `expected_content_type`
**Data:** 2026-04-09 (Wave 2, Sessao 12 — auditoria + hardening)
**Contexto:** O `_validar_upload_no_r2(object_key, expected_content_type=None)` em `provas.py` tinha um segundo parametro e um bloco de codigo que rejeitaria uploads onde o cliente declarou PNG no `/upload-url` mas subiu JPG no R2 (ou vice-versa). ADR-032 documenta essa como parte da defesa contra MIME spoofing.
  Bug latente: **o handler `create_prova` nunca passa `expected_content_type`** — a chamada eh `await _validar_upload_no_r2(body.object_key)` simples. Motivo: o `content_type` declarado no step 1 (/upload-url) **nao eh persistido entre requests** (o endpoint /upload-url e stateless), entao na hora do POST /provas/ o backend nao tem como saber o que foi declarado.
  Impacto pratico eh **baixo** — ambos JPG e PNG sao permitidos, entao um cliente malicioso que declara PNG e sobe JPG nao ganha nada (ambos passam magic bytes). Mas o codigo **mente sobre o que faz**: o ADR-032 promete a checagem, o comentario no codigo descreve a checagem, o parametro existe — e nada eh efetivamente validado.
**Decisao:** Remover completamente:
  1. O parametro `expected_content_type: str | None = None` da assinatura
  2. O bloco `if expected_content_type and expected_content_type != detected_mime:` + raise associado
  3. O comentario enganoso
  4. Substituir a docstring por uma explicacao honesta: "o content_type declarado no step 1 nao e persistido entre requests, entao aqui so olhamos o conteudo real do arquivo no R2".
  ADR-032 **continua valido e ativo** — magic bytes rejeitam qualquer nao-imagem, essa e a barreira real. Apenas o sub-item sobre "comparar tipo declarado vs detectado" eh marcado como nao-aplicavel.
**Alternativas:**
  - **Implementar persistencia real do content_type** (armazenar em KV/cache temporario ou codificar no object_key assinado): rejeitado — complexidade desproporcional ao beneficio (zero, ja que os dois tipos permitidos sao intercambiaveis). Reavaliar se aparecer um tipo com requisitos distintos (ex: TIFF para arte de impressao de alta resolucao).
  - **Deixar o parametro e adicionar um warning de deprecation**: rejeitado — ruido sem beneficio.
  - **Manter o parametro "para uso futuro"**: rejeitado — YAGNI; quando precisar, re-adicionar e trivial.
**Consequencias:**
  - **Codigo mais honesto**: a docstring descreve o que o codigo faz, nao o que pretendia fazer.
  - **Superficie de API inalterada** — o parametro era privado (`_validar_upload_no_r2` com underscore).
  - **ADR-032 nao foi revogado** — a defesa principal (magic bytes) continua em vigor. Apenas a "defesa extra" que nunca funcionou foi removida.
  - Teste nao precisou mudar — nenhum teste chamava o helper com `expected_content_type` passado.

---

## ADR-058 — Auditoria da Wave 2 + hardening pre-commit (Sessao 12)
**Data:** 2026-04-09 (Wave 2, Sessao 12)
**Contexto:** Apos o fechamento da Wave 2 na Sessao 11 e o hotfix `params` na Sessao 11b, Mario pediu uma auditoria de engenharia senior com olhar critico: "procure com um olhar critico e metodico possiveis falhas e erros e me ajude a deixar a Wave 2 o mais robusta e feita da melhor forma possivel." Escopo: todos os componentes Wave 2 (C06/C07/C08/C09), sem tocar em outras waves sem autorizacao.
**Decisao:** Executar auditoria metodica em 4 fases:
  1. **Leitura dirigida** de DECISIONS/CHANGELOG/schema + todo o codigo Wave 2 (backend: provas, configuracoes, services, schemas; frontend: paginas, hooks, types; testes).
  2. **Verificacao empirica** de hipoteses suspeitas: testes de PDF com Unicode, `typing.get_type_hints` em runtime, ruff, tsc, lint, execucao dos 250 testes existentes.
  3. **Catalogo de issues** agrupadas por severidade (criticos, altos, medios, baixos) com proposta de fix para cada uma.
  4. **Execucao priorizada** apos autorizacao do usuario para cada item.
  Resultado do diagnostico: **17 issues totais**, dos quais 2 criticos (C1 PDF Unicode, C2 LocalizacaoEnum import), 5 altos, 6 medios, 4 baixos. **Mario autorizou** 13 itens (todos dentro do escopo Wave 2), adiou A4 para a Wave 3, aceitou A5 Camada-1-only, skipou M6. Todos os 13 executados, validados via suite de testes expandida de 250 → 278 testes (+28), coverage 92% → 93%, ruff 9 erros → 0, frontend tsc/lint/build limpos.
  **ADRs novos gerados nesta sessao:** ADR-053 (fonte DejaVu), ADR-054 (gerar_pdf antes do commit), ADR-055 (nro_req case-insensitive), ADR-056 (whitelist template nome), ADR-057 (remocao de expected_content_type morto). Este ADR-058 eh meta — documenta o processo da auditoria em si para futuras sessoes.
**Alternativas consideradas no processo:**
  - **Auditoria "batch"** (listar tudo e executar sem pausa): rejeitada pelo Mario — ele preferiu autorizar por fase.
  - **Sem uso de dev-server para verificacao**: backend rodando testes unitarios + frontend build foram suficientes. Preview do Next.js usado apenas para sanity check do boot (sem backend real nao daria para exercitar A3/M5 interativamente).
**Consequencias:**
  - **Wave 2 robusta** o suficiente para entrar em producao com os fixes aplicados. Riscos residuais conhecidos: A4 (RLS vs backend em movimentacoes — Wave 3), M6 (timezone do filtro de data — cosmetico), glyphs faltando em CJK/emoji (degradacao graciosa).
  - **Processo registrado** em ADR + CHANGELOG para reproducao futura. A auditoria deve ser re-executada antes do fechamento de cada Wave grande (e.g., 3, 4, 5) — o cheklist mental testado aqui (ruff → tsc → testes → get_type_hints → PDFs com chars raros → race conditions em hooks → etc) cabe em outras situacoes.
  - **Commit unico "Wave 2 semi-pronta"** encerra essa sessao com o estado completo da Wave 2 + hardening aplicado.

---

## ADR-059 — `.card` como container + `.cardInner` scrollavel (scroll interno do dashboard)
**Data:** 2026-04-09 (Sessao 13 — ajustes visuais /provas)
**Contexto:** O `.card` do `layout.module.css` e o wrapper cinza claro arredondado que ocupa a area do conteudo de cada rota do dashboard. Originalmente tinha `min-height: calc(100vh - 2rem)` e `padding: var(--card-padding)` — o conteudo fluia livre e, quando ultrapassava o viewport, a PAGINA INTEIRA scrollava (browser scroll nativo). Isso fazia a sidebar "subir" junto com o conteudo, e em listagens longas o cabecalho da tabela saia de vista.
  Feedback do Mario (Sessao 13): "tudo que tiver dentro do box branco(box da direita com o conteudo) deve ter scroll dentro do proprio box, sem dar scroll na pagina inteira." E depois, em uma segunda iteracao: "A scroll esta muito fora do card branco, preciso que deixe ela mais natural no card branco, sem ficar passando pra fora."
  Primeira tentativa (aplicar `overflow-y: auto` direto no `.card`): tecnicamente funciona, mas a scrollbar do WebKit fica embutida no edge direito do card e, como o card tem `border-radius: 28px`, visualmente parece que a scrollbar "vaza" pelos cantos curvos superior/inferior direito.
**Decisao:** Refatorar o layout do dashboard em DUAS camadas:
  1. **`.card` vira APENAS container**: `background` + `border-radius` + `height: calc(100vh - 2rem)` + `overflow: hidden`. Nao tem padding, nao scrolla. O `overflow: hidden` combinado com o `border-radius` clipa qualquer conteudo filho (incluindo scrollbars) pelos cantos arredondados — nada passa visualmente da borda curva.
  2. **`.cardInner` vira o scrollavel real**: novo wrapper `<div>` adicionado em `layout.tsx` envolvendo `{children}`. Tem `height: 100%`, `padding: var(--card-padding)`, `padding-right: calc(var(--card-padding) - 10px)` (compensa a largura da scrollbar mantendo o conteudo centralizado), `overflow-y: auto`, `overflow-x: hidden`.
  3. **`.main` ganha `height: 100vh` + `overflow: hidden`** para garantir que o `.card` (filho) nunca cause scroll na pagina: a dupla `main > card` forma uma "caixa" fechada cujo unico canal de scroll e o `.cardInner`.
  4. **Overrides mobile preservam o scroll nativo**: no breakpoint `< 768px`, `.main`/`.card`/`.cardInner` voltam para `height: auto` + `overflow: visible` — no mobile a sidebar vira drawer e o conteudo flui livre, scroll do browser funciona normalmente.
**Alternativas:**
  - **Scroll direto no `.card`** (sem refatorar): rejeitado — scrollbar "vaza" pelos cantos arredondados (ver contexto).
  - **Scroll no `.main`**: rejeitado — a scrollbar ficaria FORA do card (entre o card e a borda do viewport), visualmente disconnected do conteudo.
  - **Sticky header dentro do card**: rejeitado — so resolveria o problema do header da tabela sair de vista, nao o scroll da pagina toda.
  - **Virtual scroll** (tipo react-window): overkill para o volume esperado (centenas de linhas no maximo no horizonte).
**Consequencias:**
  - **Scroll sempre interno, sidebar sempre fixa**: o comportamento e consistente em todas as rotas do dashboard (`/provas`, `/usuarios`, `/configuracoes`, `/nova-prova`, `/provas/[id]`). Todas as rotas ganham scroll interno sem nenhuma mudanca individual — e uma melhoria neutra para `/usuarios` (intocada conforme instrucao do Mario) que agora tambem scrolla internamente quando necessario.
  - **Validacao runtime** via `preview_eval`: `{ docHeight: 1080, mainStyle.overflow: "hidden", cardStyle.height: "1048px", cardStyle.scrollHeight: 1508, cardStyle.hasInternalScroll: true }` — confirmado.
  - **Uma regressao potencial**: se alguma rota do dashboard tiver comportamento que dependia do scroll ser na pagina inteira (ex: sticky element relativo ao viewport, infinite scroll baseado em `window.onscroll`), precisa ser adaptada para o novo contexto. Na Wave 2 nenhuma rota usa esse padrao — todas sao layouts estaticos.
  - **Mobile nao afetado**: overrides nas media queries preservam o comportamento anterior. A mensagem "acesse a versao desktop" continua sendo exibida em `< 768px` via logica de cada pagina (nao do layout).

---

## ADR-060 — Scrollbar customizada cross-browser (WebKit + Firefox)
**Data:** 2026-04-09 (Sessao 13 — ajustes visuais /provas)
**Contexto:** Com o scroll interno ativo (ADR-059), ficou necessario customizar a scrollbar para bater com o design minimalista do Figma. A scrollbar default dos sistemas operacionais (Windows especialmente) e larga, colorida (cinza medio sobre cinza escuro) e destoa do aesthetic do card claro.
**Decisao:** Implementar scrollbar customizada com suporte cross-browser via 2 APIs paralelas:
  1. **Firefox (API standard)**: `scrollbar-width: thin` + `scrollbar-color: #9a9a9a transparent`. O `transparent` como cor da track deixa o fundo do `.card` (cinza claro `#eaeaea`) aparecer atras.
  2. **WebKit/Blink (Chrome, Edge, Safari)**: pseudo-seletores:
     ```css
     ::-webkit-scrollbar { width: 10px; background: transparent }
     ::-webkit-scrollbar-track { background: transparent; margin: 40px 0 }
     ::-webkit-scrollbar-thumb { background: #9a9a9a; border-radius: 999px;
                                  min-height: 48px }
     ::-webkit-scrollbar-thumb:hover { background: #6d6d6d }
     ::-webkit-scrollbar-thumb:active { background: #525252 }
     ```
  **Ponto-chave:** a `margin: 40px 0` na `::-webkit-scrollbar-track` afasta a area ativa do thumb verticalmente dos cantos arredondados do card (radius ~28px). Como o thumb so pode se mover dentro da track, ele nunca entra na regiao curva — visualmente a scrollbar fica "flutuando" dentro do retangulo central do card, sem encostar nas bordas.
  **Cores do thumb** escolhidas para contraste equilibrado sobre o fundo `#eaeaea`:
  - Normal `#9a9a9a` (~53% preto) — visivel mas nao dominante
  - Hover `#6d6d6d` (~40% preto) — destaque em interacao
  - Active `#525252` (~32% preto) — feedback de drag
  **Thumb pill** (`border-radius: 999px`) para combinar com o resto do design language (todos os pills do app usam 9999px). `min-height: 48px` para garantir que o thumb nunca fique microscopico em listas muito longas.
**Alternativas:**
  - **Biblioteca overlayscrollbars/SimpleBar**: rejeitado — overkill, +50KB de JS, acessibilidade questionavel. A API nativa do browser cobre tudo que precisamos.
  - **Scrollbar invisivel + indicador custom**: rejeitado — perde a affordance visual do "tem mais conteudo abaixo".
  - **Scrollbar fora do container** (tipo macOS overlay): rejeitado — nao e nativo no Chrome Windows e exigiria JS.
  - **Thumb com `background-clip: padding-box` + `border: transparent`** (truque para criar respiro visual): tentado inicialmente, revertido — complica o mental model e o ganho visual e marginal.
**Consequencias:**
  - **Visibilidade nos browsers reais** (Chrome desktop, Edge, Firefox, Safari): confirmada pelo design pattern — `::-webkit-scrollbar-*` e suportado universalmente desde ~2011.
  - **Limitacao do preview headless**: o Chrome headless usado pelo `preview_screenshot` do Claude Code **nao renderiza** `::-webkit-scrollbar` pseudo-elementos no buffer de captura. Testado empiricamente injetando `::-webkit-scrollbar-thumb { background: red !important }` + track verde + `!important` — mesmo assim a scrollbar nao aparece no screenshot (embora exista no DOM, com `offsetWidth - clientWidth = 10` e regras matching no CSSOM). Isso significa que screenshots futuros do preview nao podem ser usados para validar a scrollbar visualmente — validacao precisa acontecer em um browser real.
  - **Runtime estrutural validado**: `offsetWidth - clientWidth = 10`, scroll programatico (`scrollTop = 340`) funcional, margin da track aplicada, cores do CSSOM corretas.
  - **Futuros ajustes** (cor, largura, shape) sao locais a `.cardInner` em `layout.module.css` — nao afeta o conteudo de nenhuma rota.

---

## ADR-061 — `STATUS_LABELS_SHORT` separado de `STATUS_LABELS`
**Data:** 2026-04-09 (Sessao 13 — ajustes visuais /provas)
**Contexto:** O Figma da tela `/provas` mostrava status com labels curtos ("Cancelada", "Aprovada", "Reprovada", "Na 3Studio", "Encaminhada", "Retirada"). O `STATUS_LABELS` existente em `frontend/src/lib/types/prova.ts` (criado na Sessao 11) tem labels completos ("Retirada pelo vendedor", "Aprovada pelo vendedor", "De volta a 3Studio", "Encaminhada a clicheria", etc) para dar contexto maximo na tela de detalhe (Componente 08). Usar os labels longos na coluna de Status da listagem deixa a tabela desorganizada — textos quebrando em multilinha, overflow horizontal.
  Duas opcoes consideradas: (a) encurtar `STATUS_LABELS` e afetar todas as telas que usa (incluindo a de detalhe onde o espaco e maior e o contexto completo e util); (b) criar um `STATUS_LABELS_SHORT` paralelo e usar seletivamente nas telas com restricao de largura.
**Decisao:** Criar `STATUS_LABELS_SHORT: Record<StatusProva, string>` como constante separada em `prova.ts`, com mapeamento:
  - `CRIADA` → `"Criada"`
  - `RETIRADA_PELO_VENDEDOR` → `"Retirada"`
  - `APROVADA_PELO_VENDEDOR` → `"Aprovada"`
  - `DE_VOLTA_3STUDIO` → `"Na 3Studio"`
  - `COM_MOTORISTA` → `"Com motorista"`
  - `ENVIADA_PARA_CLICHERIA` → `"Enviada"`
  - `ENCAMINHADA_A_CLICHERIA` → `"Encaminhada"`
  - `RECEBIDA_PELA_CLICHERIA` → `"Na clicheria"`
  - `REPROVADA_PELO_VENDEDOR` → `"Reprovada"`
  - `CANCELADA` → `"Cancelada"`
  **Usado em**: `/provas` (listagem — Componente 07) e na pagina `preview-provas` de inspecao.
  **NAO usado em**: `/provas/[id]` (detalhe — Componente 08, ficou com `STATUS_LABELS` longos para contexto completo no header).
  `STATUS_LABELS` original permanece intocado — manter coexistencia permite escolher o label apropriado em cada contexto sem quebrar telas existentes.
  **Distincao preservada**: o Figma do Mario colapsava os 3 status de clicheria (ENVIADA/ENCAMINHADA/RECEBIDA) em um unico "Na clicheria". Rejeitei esse colapso na Sessao 13 porque perderia informacao operacional — o MOTORISTA precisa distinguir "Enviada" (motorista ja saiu com a prova) de "Encaminhada" (vendedor Filial enviou direto) de "Na clicheria" (RECEBIDA). Mantive os 3 como labels distintos curtos. Se no futuro o negocio pedir colapso, basta mudar 3 linhas em `STATUS_LABELS_SHORT`.
**Alternativas:**
  - **Encurtar `STATUS_LABELS` original**: rejeitado — afeta `/provas/[id]` onde o label completo adiciona contexto.
  - **Computar o short label via funcao** (ex: `getShortLabel(status)`): rejeitado — string hardcoded e mais simples de grep/procurar por valor literal, e zero runtime overhead.
  - **Colapsar 3 status de clicheria em "Na clicheria"** (como o Figma): rejeitado — perde distincao operacional.
**Consequencias:**
  - **Duas tabelas de label** em `prova.ts` — ligeira duplicacao mas intencional. Se adicionar um novo `StatusProva` no enum, TypeScript vai reclamar que AMBAS as tabelas nao cobrem o novo valor (forca atualizacao em dois lugares — feature, nao bug).
  - **Tabela de /provas fica limpa**: coluna Status cabe em 1 linha, matching o Figma.
  - **Tela de detalhe intocada**: `STATUS_LABELS` continua sendo usado no header e no timeline da prova.

---

## ADR-062 — Reuso do padrao de tabela `/usuarios` em `/provas`
**Data:** 2026-04-09 (Sessao 13 — ajustes visuais /provas)
**Contexto:** O Figma da tabela de `/provas` enviado pelo Mario era visualmente identico ao padrao ja implementado em `/usuarios`: contorno externo arredondado, dividers verticais cinza entre colunas, header cinza medio com font-weight 500 e tamanho grande (1.25rem), rows com texto centralizado e sem border horizontal, botoes de acao como pills no final da ultima coluna. Mario explicitou: "A tabela com as provas digitais ficou muito diferente, a gente ja fez um modelo que vai seguir o mesmo padrão, na pagina de usuários. Analise a fundo e aproveire a tabela, mudando apenas os itens dentro dela para os da prova digital."
  A tabela anterior de `/provas` (da Sessao 12) tinha divergencias visuais: background cinza claro distinto no `.tableWrap`, borders customizadas `#cfcfcf`, `th` com peso 400 e tamanho base, padding diferente, `.detailBtn` com metricas distintas.
**Decisao:** Copiar **fielmente** os tokens e regras da tabela de `usuarios.module.css` para `provas.module.css`, mantendo nomes de classes iguais:
  - `.tableWrap`: `background: transparent; border: 1px solid var(--color-card-border); border-radius: var(--radius-card-lg); padding: 1.5rem; overflow: hidden`
  - `.tableScroll`: `width: 100%; overflow-x: auto`
  - `.table`: `width: 100%; border-collapse: collapse; font-size: 0.9375rem`
  - `.table thead tr`: `border-bottom: 1px solid var(--color-card-border)`
  - `.table th`: `text-align: center; padding: 1.125rem 1rem; color: var(--color-card-text-muted); font-weight: 500; font-size: 1.25rem; white-space: nowrap; border-right: 1px solid var(--color-card-border); background: transparent`
  - `.table td`: `text-align: center; padding: 1rem; color: var(--color-card-text-muted); border-right: 1px solid var(--color-card-border); vertical-align: middle; font-size: 0.9rem; white-space: nowrap`
  - `.table th:last-child, .table td:last-child`: `border-right: none`
  **Paginacao** tambem copiada: `.pagination` (center), `.pageInfo`, `.pageBtn` com estilo transparente + border pill.
  **Divergencia explicita**: o `.detailBtn` (botao "Ver") mantem as mesmas metricas do `.editBtn` de /usuarios (padding, min-width, border-radius pill, font-weight/size) mas com `background: var(--color-accent)` (amarelo) em vez de `#000` (preto). Justificativa: o botao de `/usuarios` e "Editar" — acao com consequencia — entao preto/neutro faz sentido. O botao de `/provas` e "Ver" — acao sem consequencia, puramente navegacional — entao o acento amarelo da marca e apropriado sem dominar a interface. Todas as outras caracteristicas visuais batem com o padrao de `/usuarios`.
**Alternativas:**
  - **Extrair tabela em componente compartilhado** (ex: `<DashboardTable>`): rejeitado por enquanto — overhead de abstracao para 2 telas que tem features ligeiramente diferentes (edit modal vs link navigation). Reavaliar quando a 3a tabela do dashboard aparecer (Wave 4/5).
  - **Importar `usuarios.module.css` em `provas/page.tsx`**: rejeitado — CSS modules tem hash de classe unico por arquivo, importar de outro module e gambiarra.
  - **Copiar SO as regras de tabela, ignorando botoes**: rejeitado — os botoes precisam bater no dimensionamento para o alinhamento vertical das rows ficar consistente.
**Consequencias:**
  - **Manutencao dupla**: se o padrao de tabela mudar (ex: redesign Wave 4), precisa atualizar `provas.module.css` E `usuarios.module.css`. Durante a Sessao 13 ja listei visualmente as regras compartilhadas para facilitar sync futuro.
  - **Zero regressao em /usuarios**: o arquivo `usuarios.module.css` nao foi tocado — a copia foi one-way de usuarios → provas.
  - **Refator futuro**: quando houver 3+ tabelas no dashboard, extrair em componente compartilhado (`<DashboardTable columns={} rows={} />`) com props para customizacao. Este ADR sera referenciado como precedente "copiamos fielmente porque ainda nao tinha volume para justificar abstracao".
  - **`detailBtn` vs `editBtn`**: a divergencia intencional de cor esta documentada aqui como single source of truth. Qualquer ajuste na cor do botao Ver passa por este ADR.

---

## ADR-063 — Etiqueta PDF 90×57mm com logos SVG vetoriais
**Data:** 2026-04-10 (Sessao 14)
**Contexto:** O design original da etiqueta (Sessao 8, Wave 2) usava `fpdf2` com formato variavel (`A4` ou `80mm_thermal`), layout vertical centralizado e texto basico sem logos. Mario enviou um mockup Figma com um design profissional especifico: dimensao FIXA de 9cm×5,7cm (paisagem), header com 2 logos vetoriais lado a lado (3STUDIO + studio&ART!), banner preto horizontal como separador, 3 campos de dados compactos, QR code quadrado com cantos arredondados, rodape com ano + "Etiqueta de rastreio" e linhas horizontais no topo e fim. Junto com o mockup, Mario enviou os 2 SVGs oficiais das logos do Desktop.
**Decisao:** Substituir COMPLETAMENTE o layout da etiqueta por um novo template hardcoded 90×57mm:
  1. **Dimensoes fixas**: `FPDF(orientation="P", unit="mm", format=(90.0, 57.0))`. Confirmado empiricamente que essa combinacao produz `pdf.w=90mm, pdf.h=57mm` (a orientation "P" com format(wider, taller) gera a pagina no formato solicitado diretamente).
  2. **Logos SVG vetoriais**: copiados do Desktop para `backend/app/services/etiqueta_assets/logo_3studio.svg` e `logo_studio_e_arte.svg`. Ambos com fill `#1d1d1b` (praticamente preto). Renderizados via `pdf.image()` nativo — `fpdf2 >= 2.7` suporta SVG nativo quando `defusedxml` esta instalado (ambos ja no venv). Zero rasterizacao: logos vetoriais imprimem nitidos em qualquer resolucao.
  3. **Fonte DejaVu** (do ADR-053) continua sendo a unica registrada — cobre Latin Extended, Greek, Cyrillic e simbolos matematicos. CJK e emoji renderizam como glyph faltando (fallback gracioso, sem crash).
  4. **Rect com cantos arredondados** para envolver o QR: `pdf.rect(..., style="D", round_corners=True, corner_radius=2.8)` — feature do `fpdf2 >= 2.7`, ja disponivel.
  5. **Campo `formato` do template** (legacy: `"A4"` ou `"80mm_thermal"`) **aceito mas ignorado** pelo render. Ver ADR-064 para detalhes dessa decisao de compat.
**Alternativas:**
  - **Reaproveitar os 2 formatos legacy (A4 e 80mm_thermal)**: rejeitado — o design do Figma e muito especifico e nao cabe em nenhum dos 2 formatos anteriores. A etiqueta **E** 90×57mm por decisao de produto, nao ha flexibilidade.
  - **Usar `reportlab` ou `weasyprint`** em vez de `fpdf2`: rejeitado — `fpdf2` ja esta no projeto desde a Sessao 8, tem zero dependencias nativas e suporta SVG+rect arredondado nativamente a partir da v2.7.
  - **Converter SVGs para PNG antes** e usar como imagem raster: rejeitado — perde qualidade em zoom/impressao e introduz dependencia de conversao (Pillow+cairosvg ou similar). SVG nativo no `fpdf2` elimina essa complexidade.
  - **Rasterizar os SVGs via Inkscape CLI no build**: rejeitado — exige Inkscape no ambiente de build do Railway, alem de gerar artefatos extras.
**Consequencias:**
  - **Assets commitados** em `backend/app/services/etiqueta_assets/` (2 arquivos SVG totalizando ~8KB — minusculo comparado aos 1.5MB dos TTFs do DejaVu).
  - **`_check_assets()`** levanta `RuntimeError` se os SVGs faltarem no deploy (fail-fast, mesmo padrao do `_register_fonts` do ADR-053).
  - **Deploy Railway**: precisa copiar o diretorio `etiqueta_assets/` no build, mas como fica dentro de `backend/`, o buildpack Python default ja copia automaticamente.
  - **Tamanho do PDF por etiqueta**: ~22.8 KB (inclui fontes subsetadas + SVGs embedded + metadata). Comparavel ao formato legacy. Aceitavel para transferencia via API.
  - **Validacao visual** feita via `pypdfium2` (instalado ad-hoc para essa sessao, nao commitado ao `pyproject.toml` — e ferramenta de dev, nao runtime).
  - **Se o design precisar mudar novamente** (ex: adicionar logo do cliente, mudar posicao do QR), o codigo esta bem comentado com coordenadas em mm e a modificacao e local ao `gerar_pdf`.
  - **Campo `formato` do template** continua aceito (compatibilidade), mas silenciosamente ignorado pelo render. Ver ADR-064.

---

## ADR-064 — Adaptive font sizing no template da etiqueta
**Data:** 2026-04-10 (Sessao 14)
**Contexto:** O novo layout da etiqueta (ADR-063) tem um bloco esquerdo com 3 campos de texto (Nome, Requerimento, Vendedor) com largura FIXA de ~53mm. O schema permite nomes de prova de ate 200 chars. Se usassemos uma fonte fixa (ex: 9pt), nomes longos como `"ETIQ CAFE CAPRONI CLASSICO"` (do mockup real) nao cabem em uma linha — estouram em 2 linhas e bagunçam o layout. Por outro lado, usar sempre 7pt (menor) deixa nomes curtos parecendo minusculos e "perdidos" no card.
**Decisao:** **Adaptive font sizing** — o helper `_campo(label, valor)` testa 5 tamanhos de fonte do maior pro menor e usa o primeiro que cabe em uma linha:
```python
_SIZES_TO_TRY = (9.0, 8.5, 8.0, 7.5, 7.0)

def _campo(label: str, valor: str) -> None:
    chosen_size = _FONT_SIZE_MIN  # fallback (7pt)
    for size in _SIZES_TO_TRY:
        if _measure_one_line(label, valor, size):
            chosen_size = size
            break
    pdf.set_font(_FONT_FAMILY, "", chosen_size)
    line_h = _LINE_H_DEFAULT * (chosen_size / _FONT_SIZE_DEFAULT)
    pdf.multi_cell(w=_CAMPO_W, h=line_h, text=f"**{label}:** {valor}",
                   markdown=True, new_x="LMARGIN", new_y="NEXT")
```

  **Calibragem empirica do overhead do `multi_cell` + `markdown=True`**: a primeira tentativa usou `_CAMPO_INNER_W = _CAMPO_W - 1` (1mm de padding interno). Nao funcionou — o texto `"ETIQ CAFE CAPRONI CLASSICO"` em 7.5pt media 51.22mm via `get_string_width` e cabia teoricamente em 52mm, mas o `multi_cell` mesmo assim wrappava para 2 linhas. Testei empiricamente com cores vibrantes (thumb vermelho + track amarelo) para identificar que o `multi_cell` com `markdown=True` consome **~5mm extras** de padding/margem internos comparado ao que `get_string_width` mede diretamente. Ajuste final: `_CAMPO_INNER_W = _CAMPO_W - 5.0`, calibrado contra o maior caso real do mockup.

  Tabela de cenarios testados:
  - Nome curto (`"Rotulo Verao"`, 12 chars) → **9pt** (default, grande, folgado)
  - Nome padrao (`"ETIQ CAFE CAPRONI CLASSICO"`, 25 chars) → **7pt**, 1 linha (cabe exatamente apos calibracao)
  - Nome muito longo (`"Etiqueta Especial Limited Edition Natal 2026 Premium"`, 50+ chars) → **7pt** + wrap automatico do `multi_cell` para 2 linhas (graceful fallback)

  **Markdown inline**: usa `f"**{label}:** {valor}"` com `markdown=True` para misturar label em bold + valor regular na mesma cell. Alternativa seria 2 `pdf.write()` separados ou 2 `cell()` em sequencia, mas o markdown preserva o comportamento de wrap automatico por palavra (nao quebra no meio do label).
**Alternativas:**
  - **Truncar com elipses** quando o nome nao couber: rejeitado — perde informacao critica e o usuario precisa abrir a prova para ver o nome completo.
  - **Sempre usar 7pt**: rejeitado — nomes curtos ficam minusculos, aparencia pobre.
  - **Sempre usar 9pt e deixar wrappar**: rejeitado — bagunca o layout porque o espaco abaixo dos campos era fixo originalmente, e nomes em 2 linhas empurrariam o conteudo pra fora da etiqueta.
  - **Calcular o size ideal matematicamente** via formula linear: rejeitado — o `multi_cell` tem overhead nao-linear que `get_string_width` nao captura; o iterativo testa o comportamento real.
  - **Usar `pdf.write()` com line-break manual**: rejeitado — perde o wrap automatico do multi_cell e complica o caso do nome em 2 linhas.
**Consequencias:**
  - **Granularidade de 0.5pt**: 5 niveis de fonte (9, 8.5, 8, 7.5, 7pt) cobrem todo o range pratico sem saltos visuais bruscos entre etiquetas adjacentes na mesma impressao.
  - **Garantia de legibilidade**: `_FONT_SIZE_MIN = 7pt` e o chao — nao vamos abaixo disso porque fica ruim de ler em impressao a 300 DPI numa etiqueta pequena. Se nem 7pt couber, o `multi_cell` wrappa em 2 linhas (degradacao graciosa).
  - **Calibragem documentada no codigo**: o comentario sobre `_CAMPO_INNER_W = _CAMPO_W - 5` explica o "por que 5" referenciando o experimento empirico. Se no futuro o `fpdf2` mudar o overhead interno, a calibracao pode ser ajustada em um unico lugar.
  - **Teste de regressao implicito**: o teste `test_pdf_nome_longo_nao_quebra` (nome com 200 A's) continua passando — o 7pt + wrap automatico cobre esse caso tambem.

---

## ADR-065 — Tela /nova-prova: botao de submit no header + dropzone com ícone
**Data:** 2026-04-10 (Sessao 15)
**Contexto:** O design inicial da `/nova-prova` (Sessao 8, Wave 2) tinha o botao "Criar prova" em um footer `.footerActions` abaixo do dropzone — padrao de form classico. Mario enviou um mockup Figma colocando o botao no **canto superior direito do card**, ao lado do titulo "Nova prova digital". O layout tambem queria:
  1. Labels pretos com `:` no final (matching padrao de `/provas` e `/configuracoes`)
  2. Grid 2x2 de inputs pill cinza com 56px de altura (matching `/provas`)
  3. Dropzone grande (min-height ~360px) SEM dashed border, com titulo + hint + icone `+` grande centralizado
**Decisao:** Refatorar o JSX e o CSS de `/nova-prova`:
  1. **`<form>` envolvendo TUDO** (header + grid + dropzone). Antes o `<form>` envolvia apenas o grid + dropzone + footer. Agora engloba o header tambem, permitindo que o botao no header seja `type="submit"` e submeta via Enter, click, ou acessibilidade.
  2. **Botao "Criar prova" movido para o header**:
     ```tsx
     <header className={styles.pageHeader}>
       <h1 className={styles.title}>Nova prova digital</h1>
       <button type="submit" className={styles.btnPrimary} disabled={!canSubmit}>
         {loading ? "Criando..." : "Criar prova"}
       </button>
     </header>
     ```
  3. **`.footerActions` removido** completamente — nao renderiza mais nenhum botao abaixo do dropzone.
  4. **Labels reescritos** com `:` e tipografia matching `/provas`:
     - `font-weight 500 → 400`
     - `color muted → preto`
     - `text-transform: none` (era uppercase)
     - `font-size sm → base`
  5. **Inputs reescritos** no padrao de `/provas` (Sessao 13):
     - `height 48 → 56`
     - `padding 0 1.25rem → 0 1.5rem`
     - `border: none` (era `1px solid transparent`)
     - focus: `box-shadow: 0 0 0 2px var(--color-accent)` (era `border-color`)
  6. **Dropzone grande sem dashed**:
     - `min-height 220 → 360`
     - `border 2px dashed → 2px solid transparent` (hover e drag-over mudam a cor)
     - Conteudo interno: titulo (fs-xl, peso 400) + hint (fs-base muted) + `<PlusIcon width={56} height={56} />` em `.dropzoneIcon`
  7. **`PlusIcon` reaproveitado** de `components/icons.tsx` (ja existia desde a Sessao 2 para o menu lateral). Nao precisei criar icon novo nem tocar no arquivo do design system.
**Alternativas:**
  - **Botao no footer (layout antigo)**: rejeitado — mockup do Figma posiciona no header.
  - **Dois `<form>` separados** (um para submit, outro para dropzone): rejeitado — complexidade sem beneficio.
  - **Criar `SubmitButton` como componente compartilhado**: rejeitado — so tem 1 botao de submit primario nesse padrao e ja esta coberto pelo `.btnPrimary` do CSS module. Abstrair agora seria overengineering.
  - **`<input type="file" accept="image/*">`** generico: ja era o existente com `"image/jpeg,image/png"` explicito — mantido para matching RF-001.
**Consequencias:**
  - **Submit via Enter no form funciona naturalmente**: o `<button type="submit">` no header captura o submit do `<form>` que o envolve.
  - **Visual consistente com `/provas`**: os 2 telas principais do dashboard agora usam o mesmo token de input (56px height, sem border, focus com `box-shadow` amarelo).
  - **Preview da imagem selecionada** aumentado (`180x180 → 260x260`) — mais visivel que a escolha deu certo.
  - **Tela de sucesso** (pos-criacao) **intocada** — nao tinha mockup no Figma, mantida para nao quebrar o fluxo de confirmacao pos-upload.
  - **Mobile** (`< 768px`): `.mobileNotice` com mensagem "acesse a versao desktop" continua inalterado.
  - **Lint incidente**: durante a sessao, formatter externo (prettier/vscode) removeu docstrings de `components/icons.tsx` e `configuracoes/configuracoes.module.css` ao abrir os arquivos. Restaurei via `git checkout` para nao sair do escopo. Registrado no CHANGELOG para referencia futura.

---

## ADR-066 — Tela /provas/[id]: card branco envolvendo timeline preto aninhado
**Data:** 2026-04-10 (Sessao 16)
**Contexto:** O design inicial da `/provas/[id]` (Sessao 11) tinha 2 cards SEPARADOS: um card cinza claro para "Dados da prova" + imagem (grid 2 colunas), e outro card cinza claro abaixo para "Historico de movimentacoes". Usava tokens de `--color-card-surface` em ambos. O mockup Figma que Mario enviou revelou um design muito diferente: um UNICO card BRANCO grande envolvendo tudo (dados + arte + timeline), com o card da timeline sendo **PRETO** e **aninhado** dentro do card branco (nao irmao). Mais: o titulo duplo "numero + nome" em peso grande bold, metadata compacta em paragrafos (nao `<dl>`), botoes "Visualizar etiqueta" amarelo + "Baixar etiqueta" preto, art slot quadrado 1:1 no canto direito.
**Decisao:** Refatorar a estrutura do JSX e reescrever o CSS. Processo foi iterativo (4 rodadas 16a→16d) ate bater com o Figma:
  1. **Estrutura nova do JSX** — o `<section className={styles.innerCard}>` contem:
     ```tsx
     <section className={styles.innerCard}>
       <div className={styles.innerCardGrid}>   {/* esquerda: dados | direita: arte */}
         <div className={styles.mainInfo}>...</div>
         <div className={styles.artSlot}>...</div>
       </div>

       {/* TIMELINE ANINHADO — nao e irmao do innerCard */}
       <section className={styles.timelineCard}>
         <h2 className={styles.timelineTitle}>...</h2>
         {/* empty state ou lista */}
       </section>
     </section>
     ```

  2. **Card branco**: `background: #ffffff; border: 1px solid var(--color-card-border); border-radius: var(--radius-card-xl); padding: 2.75rem 3rem`
  3. **Art slot quadrado** (`aspect-ratio: 1 / 1`) com tamanho controlado via **coluna do grid**, nao pelo proprio elemento: `grid-template-columns: minmax(0, 1.4fr) minmax(0, 380px)`. O `380px` e o teto; o artSlot preenche `width: 100%` desse slot e o `aspect-ratio: 1/1` transforma em quadrado. Evita o problema de o quadrado "crescer" absurdamente se a coluna fosse `1fr` em tela larga.
  4. **Card preto aninhado**: `background: #000000; border-radius: var(--radius-card-xl); padding: 2rem 2.5rem 2.25rem; color: #ffffff`. Sem `margin-bottom` externa porque o espaco com o conteudo acima vem do `margin-bottom: 2rem` do `.innerCardGrid` (o irmao anterior dentro do innerCard).
  5. **Tipografia ajustada ate ter harmonia** (rodada 16b):
     - `.title`: `3.5rem fixo`, peso `700`, letter-spacing `-0.025em`
     - `.subtitle`: `2.4rem fixo`, peso `600`, letter-spacing `-0.02em`
     - `.metadataItem`: `0.95rem` (nao `var(--fs-base)`)
     - Padding do innerCard: `2.75rem 3rem` (nao `3rem 3.5rem`)
     - Botoes: `padding 0.85rem 1.5rem`, `min-width 180px` (nao `200px`)
  6. **Icone Voltar** via SVG inline na propria page (nao toquei em `components/icons.tsx`):
     ```tsx
     function ArrowLeftIcon(props) {
       return <svg ...><path d="M19 12H5M12 19l-7-7 7-7" /></svg>;
     }
     ```
**Alternativas:**
  - **Adicionar `ArrowLeftIcon` em `components/icons.tsx`**: considerado, rejeitado nesta sessao — tocaria em arquivo compartilhado fora do escopo autorizado. Se um dia aparecer 3+ telas usando seta esquerda, extrair.
  - **Art slot com `height` fixo** (ex: `280px`): tentado na rodada 16b, rejeitado na 16c — ficava retangular em vez de quadrado 1:1 quando a coluna nao era exatamente 280px.
  - **Art slot com `aspect-ratio: 1/1 + max-width: 340px`**: tentado na rodada 16b, ficou OK mas o `max-width` no elemento competia com o `minmax` da grid column. Simplificou deixando so a grid column controlar (`minmax(0, 380px)`) e o artSlot apenas com `width: 100% + aspect-ratio`.
  - **Status preservado discretamente** em linha muted: tentado na 16a (`.statusLine`), removido na 16d porque Mario preferiu limpar completamente a informacao de Status da tela.
  - **`STATUS_LABELS` import removido** apos remover o Status: rejeitado — ainda e usado na timeline quando Wave 3 popular movimentacoes reais. Import preservado.
**Consequencias:**
  - **JSX mais aninhado**: um nivel extra de `<section>` dentro de `<section>` para a timeline. Legivel porque reflete a estrutura visual (tudo dentro do card branco = tudo dentro do `innerCard`).
  - **Layout responsivo**: `@media (max-width: 1100px)` colapsa para 1 coluna, art slot centralizado com `max-width: 380px`. Mobile (`< 768px`) continua com mensagem "acesse a versao desktop".
  - **Reutilizacao do contexto dark mode**: o card preto usa `--color-text-secondary` e `--color-text-dim` da superficie escura ja definidos em `globals.css` (Sessao 1), mantendo consistencia com o sidebar preto.
  - **Botao Secondary preto** (`.btnSecondary { background: #000; color: #fff }`) e uma divergencia de tokens comparada ao padrao `/usuarios` (que usa `#000` tambem) — CONSISTENTE com o design language dos botoes "darker action" da marca. Nao criou divergencia inconsistente.
  - **4 rodadas de ajuste** foram necessarias porque cada iteracao resolveu problemas que so apareceram depois (ex: art slot gigante so foi visivel apos ter a estrutura pronta). Aprendizado: em retrabalhos de design-to-code, screenshots de validacao em viewport real sao essenciais a cada iteracao; tentar "acertar de primeira" em CSS com tokens novos e improdutivo.

---

## ADR-067 — Remocao do status visual da tela /provas/[id]
**Data:** 2026-04-10 (Sessao 16d)
**Contexto:** Na Sessao 11 (design original da Wave 2), a tela `/provas/[id]` tinha um **badge de status colorido** no canto superior direito do header, usando as classes `status_CRIADA`, `status_APROVADA_PELO_VENDEDOR`, etc — cada uma com uma cor de fundo distinta (azul claro para aprovada, amarelo para com motorista, verde para recebida, vermelho para reprovada/cancelada, etc). O badge era uma das primeiras coisas visiveis ao abrir a prova e comunicava "onde esta essa prova no fluxo".

  Na Sessao 16a, o primeiro ajuste para o novo layout, a pedido do Mario, movi o status para uma linha discreta dentro da metadata (`.statusLine` com cor `--color-card-text-dim` e fonte menor) — proposto como compromisso entre "preservar a info operacional" e "nao poluir o design do Figma".

  Na Sessao 16d, Mario solicitou: **"Vamos realmente tirar a informação de status dessa pagina"**. Decisao final.
**Decisao:** Remover COMPLETAMENTE a exibicao do status na tela de detalhe:
  1. **`<p>` da `.statusLine` removido** do `page.tsx`.
  2. **Classe `.statusLine`** (e suas rules `.statusLine strong`) removida do `detalhe.module.css` — era codigo morto apos o remove do JSX.
  3. **Classes `.status_*` coloridas** ja estavam sem uso desde a Sessao 16a (removi a marcacao na refatoracao inicial). Mantidas no CSS por ora porque sao baratas e podem servir de hook para um futuro status visual em outra tela (ex: dashboard).
  4. **Import `STATUS_LABELS`** em `page.tsx` PRESERVADO — ainda e usado 2 vezes dentro do JSX da timeline quando `movimentacoes.total > 0` (para exibir `status_anterior → status_novo` nos itens da timeline). Remover o import quebraria esse caminho no futuro da Wave 3.
**Alternativas:**
  - **Exibir o status mas em lugar diferente** (ex: tooltip sobre o titulo): rejeitado — Mario foi explicito em remover.
  - **Manter como badge colorido sub-discreto** (ex: no canto inferior do card): rejeitado pelo mesmo motivo.
  - **Remover tambem o import de `STATUS_LABELS`**: rejeitado — quebra o uso futuro na timeline. O codigo morto apos remove do `<p>` e apenas 1 linha de CSS (facil de limpar depois).
**Consequencias:**
  - **Tela de detalhe totalmente limpa** do conceito de "status visual" — todas as informacoes sao textuais (cliente, vendedor, rota, ciclo, criada em, motivo de cancelamento).
  - **Status continua acessivel via listagem** em `/provas` (coluna Status da tabela). Quem quiser saber o status de uma prova ve na lista, nao precisa abrir o detalhe.
  - **Motivo de cancelamento** preservado em vermelho italico — continua sendo exibido condicionalmente quando `prova.motivo_cancelamento` e nao-null. Esse nao e "status" — e uma info independente que aparece so quando aplicavel.
  - **Bundle** ganhou 40 bytes a menos (`/provas/[id]` 5.62 KB → 5.58 KB no `next build`).
  - **Wave 3 em diante**: quando o scanner comecar a mudar status das provas, a tela de detalhe nao mostrara essa mudanca diretamente — o usuario acompanha pela listagem `/provas` e pelo historico (timeline) dentro do card preto. Se no futuro essa UX se mostrar confusa, reabrir a discussao do badge de status.

---

## ADR-068 — Tela /configuracoes: cards brancos + layout horizontal + checkbox custom
**Data:** 2026-04-10 (Sessao 17)
**Contexto:** Ultima tela da Wave 2 a ser alinhada ao Figma. O design original (Sessao 11) usava cards cinza (`background: var(--color-card-surface)`, `#d9d9d9`) empilhados, cada um com um `<form>` contendo o titulo + descricao + campos em coluna + botao "Salvar" no rodape (`.sectionActions` com `justify-content: flex-end`). Os checkboxes usavam `accent-color: var(--color-accent)` nativo.

  O mockup Figma enviado pelo Mario mostrava um padrao bem diferente:
  1. Cards **brancos** (`#ffffff`) com cantos bem arredondados, destacando do fundo cinza (`--color-card-bg: #eaeaea`) do `.card` do layout do dashboard.
  2. **Layout horizontal** dentro de cada card: campo(s) a esquerda + botao "Salvar" amarelo pill a direita, alinhados verticalmente na mesma row. Nao mais "campos em cima, botao em baixo".
  3. **Input `Tempo (horas uteis)` estreito** (~200px max) — no Figma ele so comporta 2-3 digitos, nao ocupa a largura toda do card.
  4. **Descricao simplificada** sem `<strong>Atrasada</strong>` nem mencao a RN-008.

  Em um segundo passo, Mario pediu refine nos checkboxes: *"deixe os checkbox com os cantos arredondados e com o icone dentro deles quando tiver check menor"*. O `accent-color` nativo nao permite controlar border-radius nem tamanho do check — e uma propriedade que ajusta apenas a hue do render nativo do browser.
**Decisao:**
  1. **Cards brancos** — `.card { background: #ffffff; border-radius: var(--radius-card-xl); padding: 2.25rem 2.75rem; }`. O fundo cinza do dashboard (`.card` do layout) continua sendo o background geral; cada secao de configuracao vira um "pop-up branco" por cima.
  2. **Layout horizontal via novo wrapper `.cardBody`**:
     ```css
     .cardBody {
       display: flex;
       align-items: flex-end;
       justify-content: space-between;
       gap: 2rem;
       flex-wrap: wrap;
     }
     ```
     O `<form>` recebe essa classe diretamente (elimina o wrapper `.form` antigo). Dentro dele, duas caixas: `.cardFields` (coluna a esquerda com label+input+feedback) e `<button>` (direita).
  3. **Alinhamento do botao** — `.btnPrimary { height: 52px; margin-left: auto; }`. A altura igual ao input (`52px`) garante que os dois se alinhem perfeitamente pela base quando `align-items: flex-end`. O `margin-left: auto` mantem o botao colado a ponta direita do card mesmo quando o `.cardBody` da `flex-wrap` em telas muito estreitas.
  4. **Input numerico compacto** — nova classe `.inputNumero { max-width: 200px; }` aplicada junto com `.input` no campo de horas.
  5. **Checkbox custom** substituindo `accent-color`:
     - Native input escondido via `clip: rect(0 0 0 0)` (mantendo acessibilidade teclado/AT)
     - `.checkboxBox` — span visual `22px × 22px`, `border-radius: 6px`, `border: 1.5px solid var(--color-card-border)`, fundo branco default
     - `.checkbox:checked + .checkboxBox` — fundo amarelo (`var(--color-accent)`) + border amarela
     - `CheckIcon` (14px × 14px, ~4px de respiro em cada lado) com `opacity: 0` por default, `opacity: 1` quando `:checked`, transicao de 120ms
     - `:focus-visible + .checkboxBox` — outline amarelo (teclado)
     - `:disabled + .checkboxBox` — opacity 0.55
     - `.checkboxLabel:has(.checkbox:disabled)` — cursor not-allowed no label inteiro
  6. **Descricao do card "Tempo de atraso"** simplificada para `"Uma prova digital sem movimentacao por mais que esse tempo e considerada atrasada."` (match literal do Figma). Removido `<strong>Atrasada</strong>` e "(RN-008). Informe em horas uteis." Mario considerou esse texto mais limpo; a regra de negocio continua documentada no backend e aqui no ADR, nao precisa poluir a UI.
**Alternativas:**
  - **Manter cards cinza** (`--color-card-surface`) e apenas ajustar layout: rejeitado — o Figma e bem explicito com fundo branco e contraste claro/claro. Alem disso, o cinza era identico ao fundo do `.card` do layout, o que tornava os cards visualmente "achatados".
  - **Layout vertical com botao no rodape** (como estava antes): rejeitado — Figma pede horizontal. O novo layout da mais respiro visual e aproveita melhor a largura de cada card.
  - **Usar `input[type=checkbox]` com CSS `accent-color`**: rejeitado porque `accent-color` nao permite customizar border-radius nem o tamanho do icone do check. O browser renderiza um quadrado nativo cheio (check ocupa a caixa toda). Mario pediu explicitamente "cantos arredondados e icone menor dentro".
  - **Usar `appearance: none` no input nativo e estilizar direto** (sem span auxiliar): funciona em alguns browsers, mas renderizar um SVG **dentro** do input via `::before`/`background-image` e fragil — nao da pra usar um componente React (`CheckIcon`) e a imagem vira CSS inline data-url, que e duro de manter. O span auxiliar permite reuso do `CheckIcon` que ja existe em `components/icons.tsx` + estilizacao total via classes CSS Modules.
  - **Criar um componente React `<Checkbox>` reutilizavel**: rejeitado porque so existem 2 checkboxes em todo o projeto ate a Wave 2, os dois na tela de configuracoes. Abstrair cedo demais para 2 usos seria overkill — quando aparecer um terceiro checkbox em outra tela (provavelmente na Wave 3/4), refatorar para um componente reutilizavel.
**Consequencias:**
  - **`/configuracoes` totalmente alinhada ao Figma final da Wave 2.** Wave 2 completa do lado visual (todas as 4 telas: `/nova-prova`, `/provas`, `/provas/[id]`, `/configuracoes`).
  - **Nenhuma mudanca de comportamento** — `useConfiguracoes`, handlers, validacoes, estados, feedback inline, endpoints, schemas, RLS: todos intactos. Zero risco de regressao funcional.
  - **Checkbox custom com a11y preservada** — teclado, screen readers, focus-visible outline. O input nativo continua "ativo" (hidden but focusable), apenas escondido visualmente. A caixa `.checkboxBox` tem `aria-hidden="true"` pra nao duplicar o announcement do input.
  - **Selector CSS `.checkbox:checked + .checkboxBox`** depende da ordem exata no JSX: `<input>` → `<span.checkboxBox>` → `<span>texto</span>`. Qualquer refatoracao futura precisa preservar essa ordem. Se o layout precisar inverter (caixa depois do texto), trocar `+` por `~` ou usar `:has()`.
  - **Classes `.input[readonly]`**, `.grid`, `.checkboxGroup`, `.field`, `.fieldHint`, `.inlineError`, `.inlineSuccess`, `.loadingBox`, `.errorBox`, `.mobileNotice`, `.desktopOnly`, `.pageHeader`, `.title`, `.h2`, `.description`, `.label`, `.input`, `.select`, `.btnPrimary` — todas permaneceram com os mesmos nomes (so mudaram os valores CSS). Isso preserva qualquer referencia cruzada que exista no codigo.
  - **Classes removidas como codigo morto:** `.form`, `.sectionActions`, `.inputInline`, `.inputSuffix` — nao sao mais usadas pelo novo JSX. Removidas do CSS tambem na refatoracao.
  - **`components/icons.tsx` nao foi tocado** — `CheckIcon` ja existia e era exportado publicamente. Mario pediu para nao tocar em `icons.tsx` nesta sessao; a restricao foi respeitada.
  - **Wave 3 em diante**: quando aparecer a necessidade de mais checkboxes (ex: filtros multi-select em relatorios), refatorar o checkbox custom em um componente React reutilizavel (`<Checkbox label="..." checked={...} onChange={...} />`) extraindo para `frontend/src/components/Checkbox.tsx`. Os estilos podem virar uma classe global em `globals.css` ou serem copiados para o CSS Module que usar.

---

## ADR-069 — Auditoria senior pos-sign-off da Wave 2 — Componente 06
**Data:** 2026-04-10 (Wave 2, Sessao 18)
**Contexto:** Apos todas as telas da Wave 2 estarem visualmente alinhadas ao Figma (Sessoes 13-17), Mario pediu uma auditoria externa de engenharia senior para validar e fortalecer cada componente da Wave 2 antes de considera-los "prontos". Escopo autorizado: apenas componentes Wave 2 (C06, C07, C08, C09), um de cada vez, em protocolo de dois estagios (analise com gate obrigatorio → execucao apos autorizacao). Waves 0 e 1 congeladas. Este ADR registra o processo e os resultados do Componente 06.
**Decisao (processo de auditoria):**
  1. **Estagio 1 — Analise somente-leitura**: escopo do componente, mapeamento de arquivos, checklist critico (maquina de estados, RBAC+RLS, Pydantic v2, concorrencia, seguranca, performance, cobertura), execucao da suite existente, classificacao de achados por severidade, plano de correcao, sinalizacao de dependencias fora da Wave 2.
  2. **Gate obrigatorio**: aguardar autorizacao explicita antes de tocar em qualquer arquivo.
  3. **Estagio 2 — Execucao**: aplicar fixes aprovados, adicionar testes, rodar suite completa + lint + build + preview smoke, gerar relatorio de entrega.
**Resultados do Componente 06:**
  - **17 achados classificados**: 1 critico (C1), 5 altos (A1-A5), 4 medios (M1-M4), 4 baixos (B1-B4).
  - **6 fixes aplicados** (C1, M1, A3, A2, A4, A5) — todos dentro do escopo Wave 2.
  - **2 fixes adiados** (A1 rate limit — requer dep nova; M2 cache de checks — micro-otimizacao) — discussao futura.
  - **Cobertura C06**: 89% → **93%** (+4pp).
  - **Testes**: 278 → **283** passing (+5 novos — 3 smoke de assets/fonts + 2 de race/cleanup).
  - **ADRs gerados nesta auditoria**: ADR-069 (este — meta), ADR-070 (IntegrityError 409), ADR-071 (smoke tests de deploy).
  - **Ruff, tsc, next lint, next build, preview smoke**: todos limpos.
**Alternativas consideradas no processo:**
  - **Auditoria em bloco unico** (analisar todos os 4 componentes antes de aplicar qualquer fix): rejeitado — Mario preferiu componente-a-componente com gate individual para validar o protocolo antes de escalar.
  - **Aplicar fixes opcionais (A1, M2) sem discussao**: rejeitado — ambos alteram arquitetura (A1 adiciona dep nova; M2 muda semantica de quando validar assets). Respeita o principio "nao mexer fora de escopo aprovado".
  - **Commitar automaticamente apos a suite verde**: rejeitado — politica do projeto exige commit manual do Mario.
**Consequencias:**
  - **Wave 2 do Componente 06 endurecida sem regressao funcional.** Todos os fluxos existentes (happy path, duplicata, vendedor invalido, magic bytes, PDF failure, commit failure) continuam com o mesmo comportamento externo.
  - **Processo validado** para ser repetido nos C07, C08 e C09 (e eventualmente em auditorias futuras das Waves 3-6).
  - **Meta-aprendizado**: o ADR-058 (auditoria Sessao 12) tinha feito o mesmo tipo de trabalho "internamente". Esta sessao 18 confirma que o checklist + protocolo de dois estagios escala bem para auditorias externas. A diferenca principal e que esta e feita componente-a-componente com mais rigor de isolamento.
  - **Arquivos de contexto atualizados ao final desta sessao**: DECISIONS.md (ADR-069, 070, 071) + CHANGELOG.md (Sessao 18) por instrucao explicita do Mario. CLAUDE.md nao foi modificado porque nenhuma estrutura (endpoints, rotas, tabelas) mudou.

---

## ADR-070 — IntegrityError no commit mapeado para 409 Conflict (race TOCTOU)
**Data:** 2026-04-10 (Wave 2, Sessao 18 — auditoria senior C06, fix A2)
**Contexto:** O `POST /api/v1/provas/` executa 3 coisas relevantes em ordem: (1) SELECT inicial checando unicidade do `nro_requerimento`, (2) validacao de vendedor + R2 + PDF, (3) INSERT atomico (prova + etiqueta + audit_log) + `db.commit()`. Entre (1) e (3) existe uma janela TOCTOU: outra requisicao paralela pode criar a mesma prova e commitar primeiro. O constraint `UNIQUE` no banco (`provas_digitais.nro_requerimento`) detecta o conflito e levanta `sqlalchemy.exc.IntegrityError` no commit. Antes deste ADR, esse caminho caia no `except Exception` generico que retornava **500 Internal Server Error** com mensagem "Falha ao criar prova digital" — o cliente nao tinha como distinguir um race legitimo de uma falha real de servidor, e retentativas blind podiam mascarar bugs reais. A auditoria senior identificou isso como ALTO (A2) porque a semantica correta para race de unicidade e **409 Conflict**, nao 500.
**Decisao:** Adicionar um `except IntegrityError:` **antes** do `except Exception:` generico em `create_prova`:
```python
except IntegrityError:
    await db.rollback()
    logger.warning(
        "IntegrityError ao persistir prova nro_req=%s (provavel race de unicidade). "
        "Limpando R2.",
        body.nro_requerimento,
    )
    await _cleanup_r2(body.object_key)
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Numero de requerimento ja cadastrado",
    )
```
  - **Ordem importa**: `IntegrityError` tem que vir antes do `except Exception` porque Python casa no primeiro match.
  - **Mensagem identica** a do 409 ja retornado no check inicial (`provas.py:307-310`) para consistencia de contrato — o cliente ve a mesma string independente de qual dos dois caminhos (pre-check ou race de commit) detectou a duplicata.
  - **Log e `logger.warning` (nao `exception`)**: e um erro esperado de race, nao um bug. Ainda assim registra para monitoramento — se esse log comecar a aparecer com frequencia, pode indicar bot ou bug de UI causando cliques duplicados.
  - **Rollback + cleanup R2**: mesma semantica do caminho de erro generico. ADR-041 (cleanup best-effort) continua valido aqui.
  - **Outros tipos de `IntegrityError`** (FK quebrada, NOT NULL violado) tambem caem neste except porque estruturalmente estao no mesmo caminho de escrita. A mensagem "Numero de requerimento ja cadastrado" e generica o suficiente para nao vazar detalhes de schema, mas honestly cobriria outros casos sem explicar. Isso e aceitavel porque: (a) FK/NOT NULL nao deveriam acontecer em producao dado que todos os campos sao validados por Pydantic + ORM antes do flush, e (b) se acontecerem sao bugs e a mensagem errada ja vira no 409 e aparece no log.
**Alternativas:**
  - **Inspecionar o `IntegrityError.orig.__cause__` ou `diag.constraint_name` para diferenciar o tipo exato** (rejeitado — complexidade desproporcional ao beneficio; todos os `IntegrityError` esperados sao UNIQUE do nro_req).
  - **Usar `INSERT ... ON CONFLICT` para fazer upsert ou no-op** (rejeitado — muda a semantica do fluxo; a tabela ganharia um segundo caminho de escrita que dificulta auditar quem criou cada linha).
  - **Advisory lock do Postgres em torno do nro_requerimento** (rejeitado — overkill para race que ja e resolvido pelo constraint natural do DB).
  - **Retry automatico no server side** (rejeitado — retry de INSERT apos IntegrityError nao ajuda porque a duplicata permanece; quem tem que retentar e o cliente com outro nro_req).
**Consequencias:**
  - **Contratro da API**: `POST /api/v1/provas/` pode retornar 409 em dois cenarios — check inicial OU race no commit — com a mesma mensagem. Cliente nao precisa distinguir.
  - **Teste novo em `test_provas_api.py`**: `test_create_prova_integrity_error_returns_409` simula `db.commit()` lancando `IntegrityError` mockado e valida: status 409, mensagem correta, `db.rollback` chamado, `_cleanup_r2` chamado.
  - **Cobertura do modulo `provas.py`**: 93% → **94%** (+1pp) — linhas do novo branch exercitadas.
  - **Operacional**: logs `warning` com pattern "IntegrityError ao persistir prova nro_req=%s" sao a metrica para decidir se ha abuse ou bot. Pre-Wave 6, se aparecer acima de X% das criacoes, abre-se a discussao de rate limit (ADR-069 decisao pendente A1).
  - **Nao houve mudanca no comportamento do caminho pre-check 409** — so cobriu o caminho pos-commit que antes era 500.

---

## ADR-071 — Smoke tests de deploy para etiqueta_assets e fontes DejaVu
**Data:** 2026-04-10 (Wave 2, Sessao 18 — auditoria senior C06, fix C1)
**Contexto:** A auditoria senior detectou que `backend/app/services/etiqueta_assets/logo_3studio.svg` e `logo_studio_e_arte.svg` estavam **untracked no git** — apenas localmente no working tree do Mario. O ADR-063 explicitamente documentou "Assets commitados em `backend/app/services/etiqueta_assets/`", mas o `git add` do commit de Wave 2 nao incluiu esse diretorio. Em qualquer deploy fresh (Railway, novo contributor, CI), o `_check_assets()` levantaria `RuntimeError("Assets de etiqueta ausentes...")` no primeiro POST de prova → o Componente 06 ficaria **completamente quebrado em producao**. Classificado como CRITICO (C1). Mesma classe de risco para as fontes DejaVu (TTFs) — se por qualquer razao os TTFs forem removidos ou apagados, `_register_fonts` levanta RuntimeError e todo PDF falha.
**Decisao:** Duas camadas complementares:
  1. **Versionar os assets faltantes**: `git add backend/app/services/etiqueta_assets/logo_3studio.svg backend/app/services/etiqueta_assets/logo_studio_e_arte.svg` — ambos ficam staged aguardando o proximo commit do Mario. Nesta sessao, nao foi feito `git commit` por politica do projeto ("NEVER commit unless the user explicitly asks").
  2. **Adicionar 3 smoke tests que falham rapido em CI se qualquer asset ou fonte sumir**:
```python
def test_etiqueta_assets_existem_no_repo():
    assert _ASSETS_DIR.exists()
    assert _LOGO_3STUDIO.exists()
    assert _LOGO_STUDIO_ART.exists()
    # Sanity: header SVG valido
    for path in (_LOGO_3STUDIO, _LOGO_STUDIO_ART):
        head = path.read_bytes()[:200].lower()
        assert b"<svg" in head or b"<?xml" in head

def test_etiqueta_fonts_existem_no_repo():
    assert (_FONTS_DIR / "DejaVuSans.ttf").exists()
    assert (_FONTS_DIR / "DejaVuSans-Bold.ttf").exists()

def test_check_assets_nao_levanta_com_arquivos_presentes():
    _check_assets()  # chamada direta — valida o contrato
```
  Esses testes **nao usam mock** — sao filesystem-level. Se o diretorio for `.gitignore`-ado por engano, se alguem apagar um arquivo, ou se o build do Railway nao copiar o diretorio, o primeiro pytest run falha com mensagem acionavel ("logo_3studio.svg ausente em ...").
**Alternativas:**
  - **Fazer o `git add` + `git commit` automaticamente nesta sessao** (rejeitado — politica "NEVER commit unless explicitly asked"; Mario commita manualmente).
  - **Baixar os SVGs/TTFs do CDN no build/deploy** (rejeitado — dependencia externa quebra builds offline e adiciona ponto de falha).
  - **Apenas usar uma CI check de `git ls-files`** para validar presenca dos arquivos (rejeitado — nao roda localmente em `pytest`, pode passar em CI mas falhar em Railway se o buildpack nao copiar o diretorio por razao nao-git).
  - **Mover os assets para um bucket R2 e buscar em runtime** (rejeitado — overengineering, introduz latencia de rede em cada `gerar_pdf`, e o R2 seria outro ponto de falha).
**Consequencias:**
  - **283 testes passando** (eram 278) — os 3 novos smoke sao os itens 1, 2, 3 da contagem.
  - **Se alguem remover um arquivo de asset/fonte, o CI backend falha antes do deploy**, com mensagem clara apontando qual arquivo sumiu e onde.
  - **Tempo de execucao dos 3 testes**: ~4ms total (filesystem stat + read). Negligivel.
  - **`.gitignore` foi atualizado na mesma sessao** (M1 da auditoria) para excluir `backend/etiqueta_preview.pdf` e `.png` — artefatos de debug local do PDF que acidentalmente poderiam ser commitados. Essa proteção e complementar: os assets devem estar versionados, os previews de debug nao.
  - **Pendencia operacional**: Mario precisa fazer `git commit` dos 2 SVGs ja staged. Sem isso, os assets continuam no working tree local e o deploy futuro vai falhar. O teste de smoke continua passando localmente (porque os arquivos existem), mas nao protege contra "esqueci de commitar" — apenas contra "foram removidos". A protecao completa e: staged + commit + push.

---

## ADR-072 — Auditoria senior pos-sign-off da Wave 2 — Componente 07
**Data:** 2026-04-10 (Wave 2, Sessao 19)
**Contexto:** Continuacao da auditoria senior iniciada na Sessao 18 (ADR-069, Componente 06). Mario autorizou avancar para o Componente 07 (Listagem, Pesquisa e Filtros de Provas) apos a atualizacao dos arquivos de contexto do C06. Mesmo protocolo de dois estagios (analise com gate obrigatorio → execucao) e mesmas regras de escopo (Wave 2 apenas, Waves 0 e 1 congeladas, Componente 06 tambem congelado apos os fixes da Sessao 18).
**Decisao (resultado da auditoria):**
  - **9 achados classificados**: 1 critico (C1), 5 altos (A1-A5), 2 medios (M1-M2), 2 baixos (B1-B2).
  - **7 fixes aplicados** (C1, A1-A5, M1) — todos dentro do escopo Wave 2 / Componente 07.
  - **2 fixes adiados**: M2 (count lento em volume grande — reavaliar pos-volume), B1 (extrair `MeResponse` para tipos compartilhados — baixa prioridade).
  - **ADRs novos gerados nesta auditoria**: ADR-072 (este — meta), ADR-073 (escape de wildcards ILIKE), ADR-074 (try/except + validacao cruzada de periodo).
  - **Metricas**: 283 → **290** testes passing (+7 novos — 3 C1 + 2 A3 + 1 A5 + 1 A2). Cobertura `provas.py` 93% → **95%**. `next build /provas` 4.39 kB → **4.31 kB** (-80 bytes graças a remocao de `loadDebounced` + `isFirstRenderRef`).
  - **Flake conhecido**: durante a validacao final, `test_pdf_formato_legacy_e_aceito_mas_ignorado` (de `test_etiqueta_service.py`, escopo C06) falhou **uma vez** em 1 das execucoes da suite completa com mensagem de assercao `a4 == thermal`. Nao e relacionado aos fixes do C07. Re-execucao imediata passou; 5 execucoes subsequentes consecutivas tambem passaram. Provavel causa: timestamp embutido pelo `fpdf2` difere em alguns microssegundos entre as duas chamadas sucessivas dentro do teste. **Nao faz parte do escopo do C07** — registrado aqui para rastreabilidade futura. Possivel fix futuro: comparar via parse do PDF (metadados estruturais) em vez de comparacao byte-a-byte.
**Alternativas consideradas:**
  - **Aplicar fixes sem discussao previa** (rejeitado — mesmo motivo do ADR-069; gate obrigatorio por componente).
  - **Agrupar C07 com C08 em uma unica analise** (rejeitado — perde a granularidade do gate e mistura escopos).
**Consequencias:**
  - **Componente 07 endurecido** com 4 classes de fix (seguranca/corretude de busca, robustez a falhas de DB, validacao de input, limpeza de codigo morto).
  - **Padrao A5 do C06 propagado**: a auditoria detectou que o fix "fetchMe usar getToken" do C06 (ADR-069) tinha replica em `/provas/page.tsx`. Corrigido no C07 com a mesma filosofia. **Lição**: o checklist de "fontes unicas de truth para tokens" deve ser aplicado em CADA pagina do dashboard quando auditar as Waves futuras.
  - **Meta-aprendizado de processo**: rodar a suite completa **5 vezes** apos fixes e pratica util para detectar flakes pre-existentes (como o do `test_pdf_formato_legacy`). Incluir esse passo no checklist do Estagio 2.

---

## ADR-073 — Escape de wildcards ILIKE nos filtros textuais da listagem
**Data:** 2026-04-10 (Wave 2, Sessao 19 — auditoria senior C07, fix C1)
**Contexto:** O endpoint `GET /api/v1/provas/` oferece 2 filtros textuais via ILIKE (`cliente` — match no campo `cliente`; `busca` — match em `nome` OR `nro_requerimento`). O Postgres interpreta 3 metacaracteres dentro de patterns de ILIKE:
  - `%` — casa qualquer sequencia de chars
  - `_` — casa 1 char qualquer
  - `\` — escape char padrao (ou `\` definido via `ESCAPE '...'`)
  Antes deste ADR, o codigo fazia `ilike(f"%{cliente}%")` sem escapar nada. Consequencias observadas:
  - Um admin buscando por `100%` (literal) casava TODOS os registros (dois `%` juntos = match tudo).
  - Um admin buscando `a_b` casava `axb`, `a9b`, `a-b` etc (um char qualquer entre a e b).
  - Um admin buscando `foo\bar` casava `foobar` em alguns dialects (backslash consumido como escape).
  **Nao e SQL injection** — SQLAlchemy parametriza os valores, entao nao ha risco de injecao de codigo. Mas **e quebra de contrato semantico**: o usuario espera "busca por substring literal", nao "busca por pattern SQL". A auditoria senior (ADR-072) classificou isso como CRITICO porque corrompe resultados visiveis ao usuario e e trivial de explorar acidentalmente.
**Decisao:** Criar helper `_escape_ilike(term: str) -> str` em `app/api/v1/provas.py` que escapa os 3 metacaracteres com a ordem correta (`\` PRIMEIRO, depois `%` e `_`):
```python
ILIKE_ESCAPE_CHAR = "\\"

def _escape_ilike(term: str) -> str:
    return (
        term.replace(ILIKE_ESCAPE_CHAR, ILIKE_ESCAPE_CHAR + ILIKE_ESCAPE_CHAR)
        .replace("%", ILIKE_ESCAPE_CHAR + "%")
        .replace("_", ILIKE_ESCAPE_CHAR + "_")
    )
```
Aplicado nos 2 filtros do `list_provas`:
```python
if cliente:
    cliente_pattern = f"%{_escape_ilike(cliente)}%"
    filters.append(
        ProvaDigital.cliente.ilike(cliente_pattern, escape=ILIKE_ESCAPE_CHAR)
    )
if busca:
    busca_pattern = f"%{_escape_ilike(busca)}%"
    filters.append(
        or_(
            ProvaDigital.nome.ilike(busca_pattern, escape=ILIKE_ESCAPE_CHAR),
            ProvaDigital.nro_requerimento.ilike(busca_pattern, escape=ILIKE_ESCAPE_CHAR),
        )
    )
```
  **Pontos-chave da implementacao:**
  - O `escape=ILIKE_ESCAPE_CHAR` e essencial — sem ele, o Postgres usa o escape default (`\`) mas SQLAlchemy pode reescapar ou deixar ambiguo. Passar explicitamente garante que o SQL compilado inclua `ESCAPE '\'` apos cada pattern.
  - A ordem do `.replace()` e critica: trocar `\` primeiro por `\\`, depois `%` por `\%`, depois `_` por `\_`. Se trocasse `%` primeiro, o `\` inserido seria reescapado na etapa seguinte, quebrando o pattern.
  - `_escape_ilike` e exportado como funcao simples (nao metodo), facil de reutilizar em futuros filtros textuais de outros endpoints (Wave 5 — relatorios — provavelmente terá filtros de vendedor por nome, cliente por similaridade, etc).
**Alternativas:**
  - **Usar `pg_trgm` + similarity()** ao inves de ILIKE literal (rejeitado — ADR-038 ja documenta que pg_trgm e overkill para o volume Wave 2; alem disso, nao resolve o problema porque `similarity('%', 'X')` tambem da match alto).
  - **Validar no Pydantic e rejeitar `%`/`_` no input** (rejeitado — quebra casos legitimos em que o cliente tem um `%` no nome por algum motivo; escapar e a pratica correta).
  - **Implementar via CASE/position() em vez de ILIKE** (rejeitado — quebra indexes e complexifica a query sem ganho).
  - **Usar biblioteca externa tipo `sqlalchemy-utils`** (rejeitado — 3 linhas de replace nao justificam nova dependencia).
**Consequencias:**
  - **3 testes novos** em `test_provas_api.py` cobrindo os 3 metacaracteres:
    - `test_list_filter_busca_escapa_percent_literal` — busca por `50%` deve gerar `%50\%%` no SQL + `ESCAPE '\'`.
    - `test_list_filter_busca_escapa_underscore_literal` — busca por `a_b` deve gerar `%a\_b%`.
    - `test_list_filter_cliente_escapa_backslash_literal` — busca por `foo\bar` deve gerar `%foo\\bar%` (backslash duplicado primeiro).
  - **Testes pre-existentes nao quebraram**: `test_list_filter_cliente_ilike` (que busca por `ACME` sem metacaracteres) continua passando porque strings sem `%`, `_` ou `\` passam pelo `_escape_ilike` inalteradas.
  - **Performance**: o escape de 3 chars via triple `.replace()` roda em O(n) onde n = len(term). Com o `max_length=200` ja existente nos params Pydantic, o custo e desprezivel (~600 ops por request no pior caso).
  - **Wave 5 (relatorios) pode reutilizar** `_escape_ilike` diretamente quando adicionar filtros por vendedor/cliente nos reports — nao precisa reimplementar.
  - **Contrato publico inalterado**: usuarios que digitam busca sem `%`/`_`/`\` continuam vendo os mesmos resultados. So muda o comportamento quando os metacaracteres aparecem no input, que antes era bug e agora e o esperado.

---

## ADR-074 — `list_provas`: try/except em queries + validacao cruzada de periodo
**Data:** 2026-04-10 (Wave 2, Sessao 19 — auditoria senior C07, fixes A2 + A3)
**Contexto:** A auditoria senior do C07 detectou 2 achados ALTOS relacionados a robustez do handler `list_provas`:
  1. **A2** — O handler `list_provas` era o unico endpoint do modulo `provas.py` SEM `try/except` em volta das queries de DB. Outros handlers (POST /upload-url, POST /) tinham tratamento explicito retornando 502 em caso de falha transitoria (pooler OFF, connection reset, timeout). No caso do `list_provas`, qualquer excecao caia no exception handler global do `main.py` que retornava 500 com mensagem generica "Erro interno do servidor" — sem distincao entre bug de codigo, falha transitoria, ou problema de configuracao. Cliente nao tinha como decidir se deveria retentar.
  2. **A3** — Os filtros `periodo_inicio` e `periodo_fim` eram aceitos individualmente pelo Pydantic (ambos `date | None`), mas nao havia validacao cruzada. Se o usuario passasse `periodo_inicio=2026-05-01&periodo_fim=2026-04-01` (invertido), o handler aplicava os dois filtros, a query SQL gerava `created_at >= '2026-05-01' AND created_at < '2026-04-02'`, e o resultado era sempre lista vazia. Sem erro, sem mensagem — UX confusa porque o usuario nao entende por que nao ha resultados.
**Decisao:**
  **Para A2**: envolver as duas `await db.execute(...)` (count + data) em um unico `try/except Exception` que loga e retorna 502:
```python
try:
    total = (await db.execute(count_stmt)).scalar() or 0
    rows = (await db.execute(data_stmt)).all()
except Exception:
    logger.exception(
        "Falha ao executar listagem de provas (user=%s, page=%d)",
        current_user.id, page,
    )
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Falha ao carregar provas",
    )
```
  Escolha de 502 (vs 503 ou 500): **502 Bad Gateway** e o codigo correto para "backend nao conseguiu obter resposta do upstream" — no caso, o Postgres e o upstream do FastAPI. O cliente pode retentar com back-off. 500 seria "bug interno" (nao e) e 503 seria "server indisponivel" (FastAPI esta respondendo, so o DB que falhou).

  **Para A3**: validacao explicita **antes** dos filtros serem montados:
```python
if (
    periodo_inicio is not None
    and periodo_fim is not None
    and periodo_fim < periodo_inicio
):
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Data final do periodo nao pode ser anterior a inicial",
    )
```
  Validar antes de qualquer query garante que (a) nenhum recurso do DB e desperdicado em queries que naturalmente retornam vazias, e (b) o teste pode inspecionar `mock_db.execute.assert_not_called()` para confirmar o short-circuit.
  422 e o codigo correto: o input semanticamente nao e processavel (nao pode existir um periodo onde o fim seja anterior ao inicio).
**Alternativas (A2):**
  - **Diferenciar tipos de excecao** (ex: `sqlalchemy.exc.OperationalError` → 502, outros → 500). Rejeitado — granularidade que nao agrega valor ao cliente, que so quer saber "posso retentar ou nao". 502 ja expressa isso.
  - **Deixar cair no exception handler global** (status quo). Rejeitado — mensagem generica nao e acionavel.
  - **Retry automatico no servidor** (rejeitado — mascara problemas reais, viola principio "failures should be loud").
**Alternativas (A3):**
  - **Validator Pydantic multi-campo no modelo de request** (rejeitado — os params sao query params individuais, nao um modelo Pydantic. Teria que criar um modelo so para isso, overengineering).
  - **Inverter silenciosamente** `periodo_fim` e `periodo_inicio` se estiverem trocados (rejeitado — principle of least surprise: o usuario provavelmente digitou errado e deveria ver o erro para corrigir).
  - **Aceitar e retornar lista vazia com flag** (`{"items": [], "warning": "periodo invalido"}`) (rejeitado — polui o schema de resposta).
**Consequencias:**
  - **3 testes novos** em `test_provas_api.py`:
    - `test_list_periodo_fim_antes_de_inicio_422` — confirma 422 + mensagem clara + `mock_db.execute.assert_not_called()`.
    - `test_list_periodo_mesma_data_aceita` — mesma data inicio/fim (um unico dia) e aceita; confirma `fim + 1 dia` no SQL compilado.
    - `test_list_db_error_returns_502` — configura `mock_db.execute.side_effect = RuntimeError(...)` e valida 502 + mensagem "carregar provas".
  - **Cobertura `provas.py`** 94% → **95%** (branches de A2 e A3 exercitados).
  - **Padrao estabelecido**: qualquer outro endpoint de listagem que vier nas Waves futuras (Wave 4 dashboard counters, Wave 5 relatorios) pode copiar a estrutura try/except da `list_provas` como baseline de robustez. O nome `detail="Falha ao carregar <recurso>"` e a convencao sugerida.
  - **Cliente frontend**: hoje o hook `useListProvas` trata qualquer erro como generico via `ApiError.message`. O 502 com mensagem especifica vai automaticamente substituir o "Nao foi possivel carregar provas" generico por "Falha ao carregar provas" do backend quando o DB falhar — uma melhoria UX sem mudanca de codigo no frontend.
  - **Observabilidade**: o `logger.exception(...)` do A2 registra o stack trace completo + user_id + page, facilitando troubleshooting em producao quando aparecerem logs 502.

---

## ADR-075 — Auditoria senior pos-sign-off da Wave 2 — Componente 08
**Data:** 2026-04-10 (Wave 2, Sessao 20)
**Contexto:** Continuacao da auditoria senior iniciada na Sessao 18 (ADR-069, Componente 06) e estendida na Sessao 19 (ADR-072, Componente 07). Mario autorizou avancar para o Componente 08 (Visualizacao de Prova — Detalhe) apos a atualizacao dos arquivos de contexto do C07. Mesmo protocolo de dois estagios, mesmas regras de escopo: apenas Componente 08, Waves 0 e 1 congeladas, Componentes 06 e 07 tambem congelados apos os fixes das sessoes 18 e 19.
**Decisao (resultado da auditoria):**
  - **6 achados classificados**: 0 criticos, 2 altos (A1 replicado em 4 endpoints + A2 dedicado a gerar_pdf), 3 medios (M1 UX do download, M2 micro-otimizacao, M3 UUID frontend), 0 baixos.
  - **6 fixes aplicados** (A1 em 4 handlers, A2 gerar_pdf, M1 feedback de download) — todos dentro do escopo Wave 2 / Componente 08.
  - **2 fixes adiados**: M2 (otimizacao de queries — pos-volume), M3 (validacao UUID frontend — edge case improvavel).
  - **ADRs novos gerados nesta auditoria**: ADR-075 (este — meta), ADR-076 (try/except consistente nos 4 endpoints C08 + 422 dedicado ao gerar_pdf).
  - **Metricas**: 290 → **295** testes passing (+5 novos: 4 de DB error 502 + 1 de gerar_pdf failure 422). Cobertura `provas.py` **95% mantida** mesmo com 28 statements novos (278 → 306). Bundle `/provas/[id]` 5.61 kB → **5.73 kB** (+120 bytes pelo bloco de error handling do download; aceitavel — zero impacto na LCP).
  - **C08 e o componente mais bem arquitetado da Wave 2**: 0 achados criticos. O `useProvaDetail` ja usava `Promise.allSettled` corretamente (tolerancia a falhas parciais), o `VisualizarEtiquetaModal` ja tinha cleanup cuidadoso de blob URLs com tratamento de race entre unmount e resolucao de Promises, e os 5 endpoints backend ja reutilizavam `_carregar_prova_com_scoping` (ADR-049). A auditoria serviu principalmente para **propagar o padrao de tratamento de erro robusto** estabelecido no A2 do C07 para os 4 endpoints do C08 que ainda nao o tinham.
**Alternativas consideradas:**
  - **Aplicar try/except generico em torno do handler inteiro** (rejeitado — captura HTTPException intencionais de 404, mascarando-as). A solucao correta e usar `except HTTPException: raise` antes do `except Exception`, garantindo que 404 do scoping e etiqueta ausente passam intactos.
  - **Extrair um decorator `@handle_db_errors`** para reduzir boilerplate (rejeitado — 4 endpoints e pouco para justificar uma abstracao, e cada um tem mensagem de detail diferente). Se chegarmos em 8+ endpoints com o mesmo padrao, reavaliar.
  - **Mover `gerar_pdf` do `create_prova` para um servico dedicado reutilizavel** (rejeitado — o helper ja existe em `etiqueta_service.py`, o que falta e aplicar o pattern de try/except do ADR-054 aqui).
**Consequencias:**
  - **Componente 08 totalmente endurecido** contra erros transitorios de DB e falhas de rendering de PDF, com mensagens acionaveis para o cliente.
  - **Padrao de error handling unificado**: todos os 3 componentes auditados (C06 create, C07 list, C08 detail/etiqueta/qr) agora usam a mesma estrutura:
    - `except HTTPException: raise` primeiro — re-raise exceptions intencionais (404, 409, 422 de validacao).
    - `except IntegrityError:` — 409 para race de unicidade (C06 ADR-070).
    - `except Exception:` — 502 generico para erros de DB/upstream (C07 ADR-074, C08 ADR-076).
    - `except Exception as exc:` dedicado ao rendering — 422 com mensagem acionavel (C06 ADR-054, C08 ADR-076).
  - **Frontend `handleDownloadEtiqueta`** agora propaga erros do backend (422 de `gerar_pdf`, 502 de DB, 401 de sessao expirada) via `alert()` com mensagem especifica — melhoria significativa de UX sem introduzir dependencia nova.
  - **Wave 2 quase pronta para sign-off**: resta apenas Componente 09 (Configuracoes). Os 3 componentes ja auditados estao robustos, testados e alinhados com os padroes estabelecidos.

---

## ADR-076 — C08: try/except consistente nos 4 endpoints + 422 dedicado ao gerar_pdf
**Data:** 2026-04-10 (Wave 2, Sessao 20 — auditoria senior C08, fixes A1 + A2)
**Contexto:** A auditoria senior do Componente 08 detectou que **4 dos 5 endpoints** de detalhe nao tinham `try/except` em volta das queries de DB — apenas `get_imagem_url` tinha protecao parcial (em volta do `generate_presigned_get_url`, ADR-050). Os handlers afetados eram:
  1. **`get_prova_detail`** — 2 queries (scoped + SELECT Usuario para rota_projetada)
  2. **`list_movimentacoes`** — 2 queries (scoped + SELECT movimentacoes)
  3. **`get_etiqueta_pdf`** — 3 queries (scoped + SELECT Etiqueta + _carregar_template_etiqueta) + 1 chamada a `gerar_pdf`
  4. **`get_qr_code_png`** — 2 queries (scoped + SELECT Etiqueta.qr_code_image)
  Erros transitorios (pooler OFF, connection reset, timeout) caiam no exception handler global do `main.py` que retornava 500 com mensagem generica "Erro interno do servidor" — mesmo problema do A2 do C07, replicado em 4 endpoints (ADR-072 A1). Alem disso, o `get_etiqueta_pdf` tambem chamava `gerar_pdf` sem protecao: se o rendering falhasse (caractere Unicode fora da fonte, template invalido, fonte ausente no deploy), tambem caia no 500 generico — mesmo problema que o ADR-054 ja havia resolvido no `create_prova`.
**Decisao:** Aplicar o padrao estabelecido na Sessao 19 (ADR-074) nos 4 handlers + adicionar um bloco dedicado ao `gerar_pdf` no handler de etiqueta:
  **Para os 4 endpoints (A1 — try/except em torno das queries):**
```python
try:
    scoped = await _carregar_prova_com_scoping(db, prova_id, current_user)
    if scoped is None:
        raise HTTPException(status_code=404, detail="Prova nao encontrada")
    # ... mais queries ...
except HTTPException:
    raise
except Exception:
    logger.exception("Falha ao carregar <recurso> da prova %s (user=%s)", prova_id, current_user.id)
    raise HTTPException(status_code=502, detail="Falha ao carregar <recurso>")
```
  **Pontos-chave da implementacao:**
  - **`except HTTPException: raise` antes do `except Exception`**: isto e critico. Sem esse guard, o `raise HTTPException(404)` do "prova nao encontrada" seria capturado pelo `except Exception` e virariamos um 502 generico no lugar do 404 correto. A ordem do Python garante que o match e feito do mais especifico para o mais generico.
  - **Mensagens de `detail` especificas por endpoint**: "Falha ao carregar prova" (detail), "Falha ao carregar movimentacoes", "Falha ao carregar dados da etiqueta", "Falha ao carregar QR code". Cada uma e acionavel pelo cliente.
  - **`logger.exception` com contexto util**: `prova_id` + `current_user.id` facilitam correlacao em producao.

  **Para o `get_etiqueta_pdf` (A2 — bloco dedicado ao rendering do PDF):**
```python
# Bloco de DB (A1) — ja coberto acima com 502
try:
    # scoped + etiqueta + template
except HTTPException: raise
except Exception: # → 502

# Bloco de rendering (A2) — 422 com mensagem acionavel
try:
    pdf_bytes = gerar_pdf(...)
except Exception as exc:
    logger.exception("Falha ao gerar PDF da etiqueta para prova %s", prova_id)
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=f"Falha ao gerar etiqueta: {exc}",
    )
```
  **Por que separar DB de rendering em 2 try/except:**
  1. **Semantica do status code**: 502 expressa "upstream indisponivel, pode retentar". 422 expressa "input problematico, investigue os dados". Misturar em um bloco unico forcaria usar um dos dois para ambos os casos, perdendo informacao.
  2. **Mensagem de detail diferente**: 502 aponta para operacao ("Falha ao carregar dados da etiqueta"), 422 aponta para causa ("Falha ao gerar etiqueta: Fontes DejaVu ausentes" — inclui a mensagem da exception via `f"{exc}"`).
  3. **Alinhamento com ADR-054**: o `create_prova` ja usava exatamente esse padrao (DB errors → 500/generic, gerar_pdf → 422 dedicado). Replicar aqui e coerencia arquitetural.
**Alternativas:**
  - **Usar tipos especificos de excecao SQLAlchemy** (ex: `OperationalError` para transitorios vs `DBAPIError` para bugs) — rejeitado: granularidade que nao agrega valor ao cliente, que so quer saber "retentar ou nao".
  - **Mover `gerar_pdf` para um servico async com timeout explicito** — rejeitado: overengineering para o caso de uso atual (PDF e rapido, <500ms no caso geral).
  - **Abstrair todos os 4 endpoints em um decorator `@robust_endpoint`** — rejeitado: reduz visibilidade do fluxo de erro e adiciona complexidade de leitura. 4 copias de 8 linhas e ok; 8+ copias justificariam a abstracao.
  - **Nao tocar nos handlers onde ja existem testes 404 passando** — rejeitado: os testes 404 passavam porque nunca houve um teste de erro de DB. O fato de o caminho "feliz 404" funcionar nao significa que o caminho "DB morreu" estava coberto.
**Consequencias:**
  - **5 testes novos** em `test_provas_api.py`:
    - `test_get_detail_db_error_returns_502`
    - `test_get_movimentacoes_db_error_returns_502`
    - `test_get_etiqueta_pdf_db_error_returns_502`
    - `test_get_etiqueta_pdf_gerar_pdf_failure_returns_422` — valida que a mensagem da exception do `gerar_pdf` e propagada no detail
    - `test_get_qr_code_png_db_error_returns_502`
  - **Suite completa**: 290 → **295 passing** (+5).
  - **Cobertura `provas.py`**: 95% **mantida** mesmo com 28 statements novos (278 → 306) — todos os novos branches de except estao exercitados.
  - **Frontend `useProvaDetail` nao precisa de mudanca**: o hook ja usa `Promise.allSettled`, entao um 502 em `/imagem-url` ou `/movimentacoes` continua sendo tolerado (imagemError e `movimentacoes: null`). Um 502 em `/{id}` (detalhe principal) ja caia em `provaRes.status === "rejected"` e mostrava mensagem generica — agora a mensagem do detail vem do backend ("Falha ao carregar prova") via `ApiError.message`, uma melhoria automatica.
  - **M1 (frontend) separado**: o `handleDownloadEtiqueta` da pagina de detalhe tinha `catch { /* noop */ }` que engolia erros silenciosamente. Substituido por try/catch que:
    1. Tenta ler o `detail` do backend via `await resp.json()` (protegido por try/catch aninhado para tolerar resposta nao-JSON).
    2. Mostra `alert()` com mensagem especifica do backend ("Falha ao gerar etiqueta: ...") ou fallback generico + sugestao de usar o modal.
    3. Diferencia "sessao expirada" (token null) de "falha no download".
  - **Botao "Baixar etiqueta" agora da feedback**: usuario que clica e o backend retorna 422 (gerar_pdf falhou) ou 502 (DB falhou) recebe a mensagem exata. Alem disso, aponta o fallback ("use Visualizar etiqueta") caso o download direto nao funcione.
  - **Nenhuma dependencia nova** — `alert()` nativo e suficiente como feedback. Quando o projeto tiver sistema de toast (Wave 4+), substituir os 3 `alert()` dos fixes dessa sessao por toast eh uma mudanca mecanica de 6 linhas.

---

## ADR-077 — Auditoria senior pos-sign-off da Wave 2 — Componente 09
**Data:** 2026-04-10 (Wave 2, Sessao 21)
**Contexto:** Sessao final da auditoria senior da Wave 2, iniciada na Sessao 18 (C06 — ADR-069), continuada na Sessao 19 (C07 — ADR-072) e estendida na Sessao 20 (C08 — ADR-075). Mario autorizou avancar para o **Componente 09 (Tela de Configuracoes do Sistema)** apos a atualizacao dos arquivos de contexto do C08. Mesmo protocolo de dois estagios, mesmas regras de escopo: apenas Componente 09, Waves 0 e 1 congeladas, Componentes 06, 07 e 08 tambem congelados apos fixes das sessoes 18, 19 e 20.

Esta e a ultima auditoria componente-por-componente da Wave 2. Ao final desta sessao, todos os 4 componentes do nucleo do dominio (C06-C09) estarao endurecidos e com metricas consistentes.
**Decisao (resultado da auditoria):**
  - **6 achados classificados**: 0 criticos, 2 altos (A1 em 2 endpoints + A2 cobrindo o handler inteiro de update), 2 medios (M1 branch defensivo PATCH whitelisted ausente, M2 branch do validator do 4o campo do template), 2 baixos (B1 `reload` exportado, B2 descricao vazia — ambos NAO aplicar).
  - **5 fixes aplicados** (A1.1 list_configuracoes, A1.2 get_configuracao, A2 update_configuracao, M1 teste defensivo, M2 teste 4o campo).
  - **1 teste pre-existente atualizado**: `test_patch_commit_failure_rollback` estava assertando status 500 e foi atualizado para 502 + assert da mensagem — acompanha a mudanca do ADR-078 (500 → 502 no commit failure).
  - **ADRs novos**: ADR-077 (este — meta) e ADR-078 (implementacao dos fixes A1 + A2 + ajustes de teste).
  - **Metricas**: 295 → **300** testes passing (+5 novos). Cobertura `configuracoes.py` 96% → **100%**. Cobertura `schemas/configuracao.py` 98% → **100%**. Stmts `configuracoes.py` 56 → 68 (+12 — novos branches try/except). `test_configuracoes_api.py` 26 → 31 testes.
  - **C09 atinge 100% de cobertura em ambos os arquivos** — primeiro componente da Wave 2 a alcancar cobertura total. O C08 tambem tem cobertura alta (95%) mas C09 e o unico a zerar os gaps.
**Alternativas consideradas:**
  - **Nao mudar status code de 500 para 502 no commit failure** (rejeitado — introduz inconsistencia entre C09 e C07/C08, que ja usam 502 em casos equivalentes desde a Sessao 19/20). Consistencia de contrato e mais importante que preservacao do contrato antigo, ainda mais porque 502 e semanticamente correto.
  - **Fazer o teste pre-existente `test_patch_commit_failure_rollback` aceitar ambos 500 e 502** (rejeitado — mascara o fix e deixa o contrato ambiguo). A atualizacao explicita para 502 + assert da mensagem deixa claro o comportamento esperado.
  - **Usar excecoes especificas `sqlalchemy.exc.OperationalError`** (rejeitado — mesmo motivo dos ADRs 074/076: granularidade que nao ajuda o cliente).
**Consequencias:**
  - **Wave 2 completamente endurecida** contra erros transitorios de DB em todos os endpoints de leitura e escrita dos 4 componentes.
  - **Padrao unificado de error handling estabelecido na Wave 2**:
    - HTTPException intencionais → re-raise via `except HTTPException: raise`
    - IntegrityError (C06 race) → 409 com mensagem dedicada (ADR-070)
    - DB errors transitorios → 502 "Falha ao <acao> <recurso>" (ADR-074, 076, 078)
    - Rendering de PDF (C06 create, C08 etiqueta) → 422 com mensagem da exception (ADR-054, 076)
    - Input validation → 422 Pydantic-like com mensagem especifica
  - **Contrato HTTP consistente entre os 4 componentes**: qualquer cliente pode usar a mesma logica de retry (502 → back-off retry; 422 → investigar input; 409 → gerar novo nro_req).
  - **Wave 2 pronta para sign-off**: 300 testes passing, ruff limpo, tsc limpo, next lint limpo, next build limpo, preview smoke limpo. Zero regressao funcional em nenhuma area.
  - **Meta-estatistica da auditoria completa** (4 sessoes, C06-C09):
    - Testes: 278 → **300** (+22 novos)
    - ADRs: ADR-069 ate ADR-078 (10 novos: 4 meta-ADRs C06/C07/C08/C09 + 6 de implementacao)
    - Linhas novas em DECISIONS.md: ~450 (acumulado das 4 sessoes)
    - Linhas novas em CHANGELOG.md: ~900 (acumulado das 4 sessoes)
    - 0 achados criticos em C07/C08/C09 pos-auditoria. Apenas C06 teve 1 critico (C1 — assets nao versionados).
    - 0 componentes com dependencia fora da Wave 2 — auditoria totalmente contida no escopo autorizado.
  - **Proxima ação pendente do Mario**: commit dos 2 SVGs ja staged desde a Sessao 18 (ADR-071) + fazer o merge/push da Wave 2 quando considerar pronto.

---

## ADR-078 — C09: try/except consistente nos 3 endpoints + commit failure 500 → 502
**Data:** 2026-04-10 (Wave 2, Sessao 21 — auditoria senior C09, fixes A1 + A2)
**Contexto:** A auditoria senior do Componente 09 detectou que os 3 endpoints de `configuracoes.py` tinham 2 classes de problemas de tratamento de erro:
  1. **`list_configuracoes` e `get_configuracao`** — sem `try/except` em volta das queries. Mesmo problema dos A1 do C07 e C08 — erros transitorios de DB caiam no exception handler global → 500 generico.
  2. **`update_configuracao`** — **parcialmente** protegido. Tinha `try/except` especifico para `ConfiguracaoValidationError` (→ 422, correto) e outro `try/except` envolvendo apenas o bloco `db.flush() + log_audit() + db.commit()`. Mas:
     - O `SELECT FOR UPDATE` (linha 141 antes do fix) estava **fora** de qualquer try/except. Erro de DB aqui caia no 500 global.
     - O `db.refresh(config)` (linha 207 antes do fix) tambem estava fora. Pequeno risco porque refresh raramente falha apos commit bem-sucedido, mas ainda assim deveria ser protegido.
     - O `except Exception` do commit failure retornava **`HTTP_500_INTERNAL_SERVER_ERROR`**. Mas 500 semanticamente e "bug interno do backend", e erro de DB e "upstream indisponivel" — o codigo correto e **`HTTP_502_BAD_GATEWAY`**, ja estabelecido pelos ADRs 074 (C07) e 076 (C08).
**Decisao:**
  **A1 — Envolver queries em try/except nos endpoints de leitura:**
  - `list_configuracoes`: um unico `try/except Exception` em volta do `db.execute` + `result.scalars().all()`. Mensagem: "Falha ao carregar configuracoes".
  - `get_configuracao`: `try/except` em volta do bloco que contem o `db.execute` + o check `if config is None`, com `except HTTPException: raise` para nao mascarar o 404 defensivo. Mensagem: "Falha ao carregar configuracao" (singular).

  **A2 — Restruturar `update_configuracao` em 2 try/except sequenciais:**
  O handler passou a ter a seguinte estrutura:
```python
# (1) Whitelist — ANTES do try/except (validacao de URL, nao de DB)
if chave not in EDITABLE_KEYS:
    raise HTTPException(404, ...)

# (2) Validacao de input — try/except dedicado ao ConfiguracaoValidationError (422)
try:
    valor_normalizado = validar_valor_por_chave(chave, body.valor)
except ConfiguracaoValidationError as exc:
    raise HTTPException(422, str(exc))

# (3-6) Bloco unico de DB — SELECT FOR UPDATE + flush + log_audit + commit + refresh
try:
    result = await db.execute(...)
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(404, "nao esta cadastrada")
    # ... captura valor_anterior, aplica mudanca em memoria ...
    await db.flush()
    await log_audit(db, ...)
    await db.commit()
    await db.refresh(config)
except HTTPException:
    # 404 de config ausente passa intacto. NAO chama rollback —
    # nenhuma mutacao aconteceu (o raise ocorre antes do flush).
    raise
except Exception:
    await db.rollback()
    logger.exception("Falha ao atualizar configuracao '%s' por admin=%s", chave, admin.id)
    raise HTTPException(502, "Falha ao atualizar configuracao")
```
  **Pontos-chave da decisao:**
  - **Validacao de input (ConfiguracaoValidationError → 422) em try/except SEPARADO do bloco de DB (→ 502)**. Se fossem juntos, um erro de validacao cairia no `except Exception` e viraria 502 errado.
  - **Ordem: whitelist → validacao → DB**. Motivos:
    1. Whitelist e checada primeiro porque nao depende nem do input do body nem do DB. Falha rapida.
    2. Validacao do `valor` acontece ANTES do SELECT FOR UPDATE. Isso e importante porque se o valor e invalido, nao queremos nem pegar o lock do DB.
    3. DB ocorre por ultimo.
  - **`except HTTPException: raise` ANTES do `except Exception`** no bloco de DB: sem isso, o 404 de "config ausente no banco" seria capturado como 502, mascarando a causa raiz.
  - **Nao ha rollback no branch `except HTTPException`**: o 404 so pode ser disparado APOS o SELECT mas ANTES do flush/commit. Como nenhuma mutacao foi enviada ao DB, nao ha nada para rolar para tras. O teste M1 valida essa garantia via `mock_db.rollback.assert_not_awaited()`.
  - **Commit failure 500 → 502**: consistente com ADR-074 (list_provas do C07) e ADR-076 (4 endpoints do C08). Um cliente que recebe 502 sabe que pode retentar com back-off; um 500 geralmente sinaliza bug no servidor e nao deve ser retentado automaticamente.
**Alternativas:**
  - **Manter os 2 try/except originais (um so para validacao de valor, outro so para flush+log+commit)** — rejeitado, deixaria SELECT FOR UPDATE e refresh desprotegidos.
  - **Usar transacao SQLAlchemy explicita (`async with db.begin()`)** — rejeitado, o padrao do projeto em outros endpoints usa `db.flush()` + `db.commit()` manual com log_audit entre eles. Mudar agora quebraria consistencia sem ganho real.
  - **Distinguir erros de DB de outros erros via `SQLAlchemyError`** — rejeitado pelo mesmo motivo dos outros ADRs: granularidade sem beneficio ao cliente.
  - **Manter 500 no commit failure "porque configuracoes e operacao administrativa e falhas sao raras"** — rejeitado, consistencia de contrato HTTP entre componentes tem valor operacional significativo: time de ops ve um 502 em logs e sabe que o Postgres teve soluço, um 500 obriga investigacao de codigo.
**Consequencias:**
  - **1 teste pre-existente atualizado** (`test_patch_commit_failure_rollback`): antes esperava `status_code == 500`, agora espera `status_code == 502` + `"atualizar configuracao" in detail`. Adicionado docstring explicando a mudanca + referencia a esta ADR.
  - **5 testes novos** em `test_configuracoes_api.py`:
    - `test_list_configuracoes_db_error_returns_502` — `db.execute.side_effect = RuntimeError(...)` → valida 502 + detail "carregar configuracoes".
    - `test_get_configuracao_db_error_returns_502` — mesmo pattern, detail "carregar configuracao".
    - `test_patch_configuracao_db_error_returns_502` — falha no SELECT FOR UPDATE → 502 + `rollback` chamado.
    - `test_patch_configuracao_whitelisted_mas_ausente_no_db` (M1) — `_scalar(None)` simula seed ausente → 404 com mensagem "nao esta cadastrada" + assert `rollback.assert_not_awaited()` + `commit.assert_not_awaited()` (garante que o raise acontece antes de qualquer mutacao).
    - `test_patch_template_mostrar_data_criacao_nao_bool` (M2) — 422 com mensagem "mostrar_data_criacao deve ser booleano" + assert `execute.assert_not_called()` (valida que a validacao acontece antes do DB).
  - **Cobertura 100% em ambos os arquivos C09** (`configuracoes.py` e `schemas/configuracao.py`). Primeiro componente da Wave 2 a zerar os gaps.
  - **Frontend nao precisou de mudanca**: o hook `useConfiguracoes` ja propaga `ApiError.message` — o 502 com mensagem especifica do backend automaticamente substitui mensagens genericas quando o DB falhar. Melhoria automatica de UX sem tocar em 1 linha de frontend.
  - **`rollback` nao e chamado em caminhos felizes nem em 404 defensivo** — confirmado pelos testes. Nenhum desperdicio de conexao do pool.

---

## ADR-079 — Auditoria externa pos-sign-off da Wave 2 (Sessao 22)
**Data:** 2026-04-10 (Wave 2, Sessao 22)
**Contexto:** Apos a Sessao 21 declarar "Wave 2 pronta para sign-off" (ADR-077/078), Mario solicitou uma **segunda auditoria independente** com protocolo ainda mais rigoroso: read-only total na Fase 1-3, gate obrigatorio antes de qualquer edicao, escopo estrito a Wave 2 (C06/C07/C08/C09), Waves 0 e 1 congeladas. O objetivo era verificar as alegacoes das Sessoes 18-21 empiricamente e procurar problemas novos que aquelas sessoes pudessem ter perdido — uma especie de auditoria "zerada" sobre o trabalho ja feito.
**Decisao (processo da auditoria externa):**
  1. **Fase 1 — Carregamento de contexto**: ler DECISIONS.md (78 ADRs), CHANGELOG.md (21 sessoes), schema.sql, Requisitos v3.0, DAT v2.0, Backlog v3.0, UML, migrations, RLS, **todos** os 30 arquivos da Wave 2 (backend + frontend + tests). Entregar resumo de escopo e **parar no gate obrigatorio** para validacao do Mario.
  2. **Fase 2 — Auditoria multi-eixo**: oito eixos em paralelo (requisitos/ADRs, schema/migrations/RLS, backend FastAPI, frontend Next.js, seguranca, testes, qualidade de codigo, integracao entre Waves). Para cada achado: severidade, arquivo+linha, descricao, impacto, correcao proposta.
  3. **Fase 2b — Re-verificacao empirica**: rodar `pytest -v` (alegou 300 → confirmado), `ruff check` (alegou limpo → confirmado), `tsc --noEmit` (alegou limpo → confirmado), `next lint` (alegou limpo → confirmado), `next build` (alegou OK → confirmado). Todas as alegacoes das Sessoes 18-21 **confirmadas empiricamente**.
  4. **Fase 3 — Relatorio consolidado**: 20 achados novos catalogados (1 critico, 3 altos, 10 medios, 6 baixos) + 6 debitos herdados das Sessoes 18-21 para Mario decidir. Gate obrigatorio antes de qualquer edicao.
  5. **Fase 4 — Execucao**: commit baseline primeiro (resolve F23), depois 14 fixes em ordem de criticidade, commit final no fim.

**Resultados (ver ADR-080 para detalhes de implementacao):**
  - **14 fixes aplicados**: F01, F02+F27, F25, F04, F05 (=C08 M2), F07, F12, F09, F10, F21, C07 B1, C08 M3, Flake PDF, F23 (via commit baseline).
  - **3 fixes NAO aplicados** por decisao explicita:
    - **F03** (RLS movimentacoes sem MOTORISTA/CLICHERIA) → **adiado para Wave 3** (quando movimentacoes comecarem a existir). Documentado como TODO explicito no proprio arquivo `005_initplan_optimization.sql`.
    - **F18** (rate limit em /upload-url e /provas/) → **mantido como debito aceito** (concordancia com Sessao 18, ADR-069).
    - **F13** (warning HMAC em `test_jwt.py`) → **NAO TOCADO** porque e Wave 1 congelada. Mario foi explicito: "iremos mexer somente no que for da wave 2".
  - **4 debitos herdados aplicados**: C07 B1 (MeResponse shared), C08 M2 (=F05), C08 M3 (404 em UUID invalido), Flake PDF (monkeypatch datetime).
  - **Metricas**: 300 → **308 testes** (+8 novos). Cobertura `provas.py` 95% mantida (322 stmts, +16 cobertos). Cobertura `audit_service.py` 100% (29 stmts, +11). Global 94% mantido.
  - **Ruff / tsc / lint / build**: todos limpos antes e depois.
  - **Zero regressoes funcionais** introduzidas.
  - **2 commits**: `270c59a` (baseline com Sessoes 13-21, resolve F23) e `[HEAD]` (todos os fixes da auditoria externa).

**Alternativas consideradas no processo:**
  - **Aceitar as alegacoes das Sessoes 18-21 sem re-verificar**: rejeitado — o ponto da auditoria externa e justamente validar o trabalho prévio.
  - **Auditoria em bloco unico** (catalogar tudo sem parar no gate): rejeitado — Mario pediu protocolo conservador com gate, consistente com as sessoes anteriores.
  - **Extender o escopo para Wave 0/1** quando encontrou F13 (HMAC warning em test_jwt): rejeitado — Mario foi explicito sobre escopo estrito a Wave 2.

**Consequencias:**
  - **Wave 2 verdadeiramente endurecida** — a auditoria externa encontrou 20 achados que as Sessoes 18-21 perderam, incluindo 1 critico (F23: SVGs nao commitados, que quebraria deploy Railway) e 3 altos (F01: 500 vs 502 inconsistente, F02: db.refresh race, F25: timezone UTC confunde usuario BRT).
  - **Padrao unificado de error handling verdadeiramente unificado**: ADR-077 alegava isso, mas F01 mostrou que o `create_prova` ainda retornava 500. Corrigido — agora os 4 componentes (C06/C07/C08/C09) seguem o mesmo padrao 502 para DB transient.
  - **Defesa em profundidade aumentada** em 4 dimensoes:
    - Error handling: 502 em todos os commits failure + 422 em rendering + 409 em race de unicidade
    - Race conditions: `latestReqRef` no `useProvaDetail` (era so no `useListProvas`)
    - Resource cleanup: `AbortController` no `useListProvas` para cancelar requests em voo
    - Data integrity: `db.refresh` failure handling garante que prova criada nao "vira fantasma" para o usuario
  - **Audit trail produtivo em producao**: F04 garante que o IP real do usuario chega no audit_log em vez do IP do gateway Railway — essencial para investigacao de incidentes segundo RNF-005.
  - **UX consistente**: F10 (label "Criada ate" em vez de "Finalizada em"), F25 (timezone BRT), C08 M3 (404 em vez de 422 verbose), F12 (warning lossy no downgrade) — todas melhorias de comunicacao com o usuario/operador.
  - **Debito tecnico formalizado** para Wave 3 (F03, policy RLS movimentacoes) e Wave 6 (F17/F22/F24, testes de RLS e integracao real). Nenhum debito silencioso.
  - **Meta-aprendizado**: o protocolo de "auditoria externa" (com re-verificacao empirica das alegacoes anteriores) e uma camada adicional valiosa sobre o ja estabelecido protocolo interno das Sessoes 18-21. Deveria ser repetido no final de cada Wave grande.

---

## ADR-080 — Detalhes de implementacao dos 14 fixes da auditoria externa
**Data:** 2026-04-10 (Wave 2, Sessao 22)
**Contexto:** ADR meta-documentativo do ADR-079 — registra decisoes tecnicas especificas de cada um dos 14 fixes aplicados na auditoria externa.

### F01 — `create_prova` commit failure 500 → 502
**Arquivo:** `backend/app/api/v1/provas.py:469-475` (antigo) → 502 + mensagem "Falha ao persistir prova".
**Justificativa:** alinhamento com ADR-074 (C07 `list_provas`), ADR-076 (C08 4 endpoints) e ADR-078 (C09 3 endpoints). ADR-077 alegava que o padrao era unificado, mas o `create_prova` estava excluido desse padrao — factualmente falso. Fix 1 linha de codigo + 1 teste atualizado.

### F02 + F27 — `db.refresh` fora do try/except
**Arquivo:** `backend/app/api/v1/provas.py:477-494`.
**Problema:** `await db.refresh(nova_prova)` acontecia APOS o commit bem-sucedido, fora de qualquer try/except. Se o refresh falhasse (raro mas possivel — connection drop entre commit e refresh), a exception bolha para o handler global → 500 generico. Mas a prova JA ESTA persistida no DB. Cliente recebe 500, retenta, pega 409 "ja cadastrada" — estado logico inconsistente da percepcao do usuario.
**Decisao:** envolver `db.refresh` em try/except. Em caso de falha, construir o response com os valores em memoria (o `created_at` gerado no backend antes do INSERT via `datetime.now(UTC)` + `updated_at = created_at` porque na Wave 2 nenhum UPDATE acontece entre INSERT e response). Logar warning "respondendo com dados em memoria" para monitoramento.
**Alternativas rejeitadas:**
  - Rollback em caso de refresh failure: impossivel — commit ja aconteceu.
  - Transacao em 2 fases (saga): overkill para uma unica query defensiva.
  - Rodar refresh dentro do try/except do commit: mudaria o shape do commit failure handler e misturaria dois tipos de erro.
**Teste novo:** `test_create_prova_refresh_failure_after_commit_responds_201` — mocka `db.refresh.side_effect = Exception` e valida response 201 com dados consistentes. Cobre a lacuna F27 (zero teste anterior para esse caminho).

### F25 — Filtro de periodo com timezone BRT implicito
**Arquivo:** `backend/app/api/v1/provas.py:93-106, 687-705`.
**Problema:** filtros de data eram convertidos para UTC direto. Usuario em BRT que filtra `periodo_inicio=2026-04-09` nao via provas criadas as 23:30 BRT do dia 9 (= 02:30 UTC do dia 10).
**Decisao:** usar offset fixo `-3` via `timezone(timedelta(hours=-3))` em vez de `ZoneInfo("America/Sao_Paulo")`. Motivos:
  1. Brasil nao tem DST desde 2019 e a aplicacao so lida com datas atuais/futuras.
  2. `zoneinfo` no Windows precisa do pacote `tzdata` como dep extra (descoberto em runtime na Sessao 22 — teste falhou com `ZoneInfoNotFoundError`). Evitar dep extra.
  3. Se eventualmente for necessario lidar com datas historicas pre-2019 (backfills), trocar por ZoneInfo + tzdata.
**Teste novo:** `test_list_filter_periodo_respects_brt_timezone` valida que `periodo_inicio=2026-04-09 & periodo_fim=2026-04-09` gera SQL com `>= 2026-04-09 03:00:00 UTC` e `< 2026-04-10 03:00:00 UTC`.

### F03 — RLS `pol_movimentacoes_select` sem MOTORISTA/CLICHERIA
**Arquivo:** `backend/migrations/rls/005_initplan_optimization.sql` (apenas comment, sem mudanca funcional).
**Decisao:** **nao aplicar o fix na Wave 2**. Justificativas:
  1. Wave 2 nao insere nenhuma movimentacao (state machine stub).
  2. O backend ja cobre o scoping corretamente via `_carregar_prova_com_scoping` (ADR-046/049) usando a mesma logica de `pol_provas_select`.
  3. Criar uma migration RLS 006 na Wave 2 acopla trabalho de Wave 3 ao fechamento da Wave 2.
**Action:** adicionado bloco de comentario TODO dentro do proprio arquivo SQL, explicando o gap + as acoes necessarias para Wave 3 + referencia a este ADR.

### F04 — `log_audit` sem X-Forwarded-For
**Arquivo:** `backend/app/services/audit_service.py:24-56`.
**Decisao:** criar helper `_extract_client_ip(request)` que:
  1. Tenta `X-Forwarded-For` e pega o PRIMEIRO IP (o cliente original — os trailings sao proxies).
  2. Fallback para `X-Real-IP` (alguns proxies usam esse header alternativo).
  3. Fallback final para `request.client.host` (dev local, testes).
**Seguranca:** confiamos nesses headers porque Railway e um proxy confiavel que reescreve X-Forwarded-For no ingress. Se o projeto migrar para infra onde o cliente possa injetar headers direto, a logica precisa ser endurecida para validar a origem do request. Documentado no docstring.
**Testes novos (5):** happy path XFF, XFF com cadeia, X-Real-IP fallback, client.host fallback, XFF vazio cai no fallback.

### F05 (=C08 M2) — Eliminar query duplicada em `get_prova_detail`
**Arquivo:** `backend/app/api/v1/provas.py:796-955`.
**Decisao:** estender `_carregar_prova_com_scoping` para incluir `Usuario.setor` no JOIN (vira tupla de 4 elementos). Criar novo helper `_determinar_rota_projetada(vendedor_setor, vendedor_localizacao)` que trabalha com escalares em vez do objeto Usuario. Atualizar `_build_prova_response` para calcular rota direto desses campos. `get_prova_detail` elimina a segunda query.
**Impacto:** -1 query por request de detalhe (~5ms a menos), e codigo mais limpo (um caminho unico em vez de 2). Os outros 4 endpoints que usam o helper unpackam o 4o elemento como `_vendedor_setor` (nao usam).
**Testes atualizados:** `_detail_row(prova, nome, localizacao, vendedor_setor=SetorEnum.VENDEDOR)` agora aceita o setor como kwarg opcional com default VENDEDOR. O teste `test_get_detail_rota_projetada_none_para_nao_vendedor` passa `vendedor_setor=SetorEnum.STUDIO` explicitamente. 4 testes do detail tiveram o `_scalar(vendedor)` removido (era a segunda query).

### F07 — `useProvaDetail.load` sem `latestReqRef`
**Arquivo:** `frontend/src/hooks/useProvaDetail.ts`.
**Decisao:** copiar o padrao do `useListProvas`. Criar `latestReqRef`, incrementar no inicio de cada load, checar apos o `await getToken()` e apos o `await Promise.allSettled([...])`. Loads fora-de-ordem sao descartados silenciosamente.

### F12 — Warning lossy no downgrade da migration 009
**Arquivo:** `backend/migrations/versions/009_evolve_template_etiqueta_schema.py`.
**Decisao:** adicionar bloco de WARNING em caixa ASCII no docstring do topo do arquivo + `print()` com alerta dentro do `downgrade()` antes do UPDATE. Zero mudanca de comportamento — so deixa explicito que o downgrade perde dados (logo_enabled, mostrar_data_criacao, formato customizados).

### F09 — `useEffect` de cleanup de `arquivoPreview` redundante
**Arquivo:** `frontend/src/app/(dashboard)/nova-prova/page.tsx:112-116`.
**Decisao:** remover o useEffect. O `handleFileSelect` ja faz `URL.revokeObjectURL(arquivoPreview)` antes de criar a nova URL — o useEffect era redundante e potencialmente revoca a URL errada (captura do closure antigo). Substituido por comentario explicando a decisao.

### F10 — Label "Finalizada em" trocado por "Criada ate"
**Arquivo:** `frontend/src/app/(dashboard)/provas/page.tsx:345`.
**Decisao:** o filtro `periodo_fim` e sobre `created_at`, nao sobre qualquer conceito de "finalizacao" (Wave 2 nem tem esse conceito). Trocado por "Criada ate" — honesto ao que o filtro realmente faz. Tambem ajustado "Criada em" → "Criada a partir de" no `periodo_inicio` para simetria.

### F21 — `useListProvas` sem `AbortController`
**Arquivo:** `frontend/src/hooks/useListProvas.ts`.
**Decisao:** adicionar `inflightControllerRef` que guarda o `AbortController` da request atual. Cada novo `load()` aborta a anterior (se houver) antes de comecar. O `AbortError` que resulta e filtrado do catch (via `err instanceof DOMException && err.name === "AbortError"`) — nao e erro real. Cleanup no unmount do componente via useEffect. Economiza banda em redes lentas com filtros mudando rapidamente.

### C07 B1 — Extrair `MeResponse` para tipos compartilhados
**Arquivo:** `frontend/src/lib/types/usuario.ts` + `frontend/src/app/(dashboard)/provas/page.tsx`.
**Decisao:** adicionar `MeResponse` em `usuario.ts` (arquivo de tipos ja compartilhado entre Wave 1 e Wave 2). A Wave 2 (`provas/page.tsx`) importa do tipo compartilhado. `layout.tsx` (Wave 1) continua com sua definicao local `UserInfo` — **nao tocado** porque Mario foi explicito que so toca Wave 2. O drift e aceitavel porque o tipo da Wave 1 e privado ao `layout.tsx`.

### C08 M3 — UUID invalido no path retorna 404
**Arquivo:** `backend/app/api/v1/provas.py:111-137` (novo `parse_prova_id`) + 5 handlers atualizados.
**Descoberta:** a auditoria da Sessao 20 alegou que UUID invalido retornava **500**. **Falso** — re-verificacao empirica mostrou que o FastAPI ja retornava **422** com mensagem verbose do Pydantic validator (`"Input should be a valid UUID, invalid character: expected an optional prefix of 'urn:uuid:'..."`). Porem a mensagem vaza detalhes internos e e inconsistente com o 404 retornado quando um UUID valido aponta para prova inexistente.
**Decisao:** criar dependency `parse_prova_id(prova_id: str = Path(...)) -> uuid.UUID` que converte manualmente e retorna 404 "Prova nao encontrada" em caso de `ValueError`. Aplicado via `Depends(parse_prova_id)` nos 5 handlers de detalhe. Resultado: 404 consistente em todos os casos onde a prova nao pode ser encontrada (ID invalido, ID valido ausente, scoping escondendo).
**Teste novo:** `test_get_detail_invalid_uuid_retorna_404` cobre os 5 endpoints com 3 strings invalidas cada (15 asserts).

### Flake `test_pdf_formato_legacy_e_aceito_mas_ignorado`
**Arquivo:** `backend/tests/test_etiqueta_service.py`.
**Problema:** o teste comparava bytes de 2 PDFs gerados em sucessao. O `fpdf2` embute `CreationDate` no metadata com resolucao de segundo — se as 2 chamadas cruzassem a fronteira de segundo, os bytes diferem e o `assert a4 == thermal` falhava.
**Decisao:** usar `monkeypatch.setattr` para substituir `datetime` nos modulos `fpdf.fpdf` e `fpdf.output` por uma classe `_FrozenDatetime(datetime)` cujo `.now()` sempre retorna `datetime(2026, 4, 10, 12, 0, 0, UTC)`. Zero dep nova (sem `freezegun`), zero mudanca em `etiqueta_service.py` (so no teste).
**Validacao:** 5 runs consecutivas do teste passando — flake eliminado.

---

## ADR-081 — `executar_transicao`: orquestracao de transicoes no dominio (Wave 3 Lote A / Sub-bloco A.1)
**Data:** 2026-04-10 (Wave 3 Lote A, sub-bloco A.1)
**Contexto:** Wave 2 deixou `state_machine.executar_transicao` como stub `NotImplementedError`. Wave 3 Lote A (Componente 11 do Backlog) precisa de uma funcao que, dada uma prova carregada e uma intencao de transicao, (a) valide a transicao + ator, (b) aplique regras de negocio extras (rota por localizacao, reinicio de ciclo, cancelamento), (c) persista uma `Movimentacao` imutavel, (d) atualize `provas_digitais.status/rota/ciclo_atual/motivo_cancelamento` e (e) grave um `audit_log` estruturado. O endpoint `POST /provas/{id}/transicoes` (sub-bloco A.4) apenas traduz HTTP<->dominio.

Ha varias decisoes de desenho nao obvias aqui que merecem registro.

### Decisao 1 — Funcao standalone async em vez de metodo de classe
**Decisao:** `async def executar_transicao(db, *, prova, status_novo, usuario, assinatura_digital, motivo_reprovacao=None, motivo_cancelamento=None, request=None) -> Movimentacao`.
**Alternativa:** criar uma classe `TransitionEngine` com estado, instanciada por request.
**Por que standalone:** o projeto inteiro usa o padrao de funcoes puras + helpers no dominio/services (ver `qrcode_service.py`, `audit_service.py`, `etiqueta_service.py`). Zero estado — cada transicao e independente. Testes unitarios ficam triviais (mock_db + patch de log_audit, sem fixture de classe). O padrao bate com `validar_transicao`, `determinar_rota` e `pode_cancelar` ja existentes.
**Consequencias:** o state_machine.py passa a depender de `sqlalchemy.ext.asyncio.AsyncSession`, `fastapi.Request` e `app.services.audit_service.log_audit`. Isso e aceitavel porque o modulo ja e um "service" (nao dominio puro) — ele ja importava `SetorEnum`, `LocalizacaoEnum` etc dos models.

### Decisao 2 — Caller responsavel por FOR UPDATE e por commit
**Decisao:** `executar_transicao` nao faz `db.commit()` nem carrega a prova com lock. Recebe a prova ja carregada (o sub-bloco A.4 vai fazer o FOR UPDATE no endpoint) e retorna a `Movimentacao` criada apos um flush. Caller comita.
**Alternativa:** fazer a funcao auto-contida (load + lock + commit).
**Por que caller-orquestra:**
  1. **Testabilidade**: com caller-controla, os testes unitarios usam `mock_db` e observam `db.add.call_args` + `log_audit.call_args`. Se a funcao fosse auto-contida, precisaria de um banco real ou de mocks mais complexos.
  2. **Composicao**: o Lote C (cancelamento, reinicio de ciclo via endpoints dedicados) pode reusar a mesma funcao num contexto diferente sem precisar reabrir transacoes.
  3. **Consistencia com create_prova**: a Wave 2 `create_prova` ja segue o mesmo padrao — o handler do endpoint e quem controla FOR UPDATE (`_carregar_vendedor`), flush e commit.
**Consequencias:** caller precisa saber sobre transacoes (mas o endpoint ja sabia de qualquer forma). Exception inesperada na funcao levanta ate o handler que faz rollback.

### Decisao 3 — Regra extra RF-009 enforcada fora da tabela `ATORES_POR_TRANSICAO`
**Decisao:** a `TRANSICOES` + `ATORES_POR_TRANSICAO` existente (ADR-040) permite que QUALQUER vendedor transite de `APROVADA_PELO_VENDEDOR` para `DE_VOLTA_3STUDIO` ou `ENCAMINHADA_A_CLICHERIA` — porque essas tabelas nao distinguem localizacao. A regra "MATRIZ usa rota padrao, FILIAL usa rota direta" (RF-009 + RN-007) e aplicada em um bloco `if status_atual == APROVADA and not is_admin` dentro do `executar_transicao` que rejeita com `AtorNaoAutorizadoError` se a localizacao nao bater.
**Alternativa considerada:** refatorar `ATORES_POR_TRANSICAO` para aceitar tuplas `(setor, localizacao)` — por exemplo, `(APROVADA, DE_VOLTA_3STUDIO): {(VENDEDOR, MATRIZ)}`.
**Por que fora da tabela:**
  1. A tabela `ATORES_POR_TRANSICAO` e consumida por `validar_transicao` e `atores_permitidos` em contextos ja estabelecidos (testes unitarios, `pode_cancelar`, potencial futuro UI de debug). Mudar a estrutura quebraria a API publica do state_machine.
  2. A regra de localizacao so se aplica a **2 transicoes** (out of ~10), entao encodar no tipo da tabela adiciona complexidade por pouco ganho.
  3. O bloco adicional e pequeno (10 linhas) e explicitamente comentado com referencia a RF-009.
**Consequencias:** `validar_transicao` isolado nao captura essa regra — se alguem chama `validar_transicao` direto com APROVADA -> DE_VOLTA para um vendedor FILIAL, passa. So o `executar_transicao` bloqueia. Isso e documentado no docstring; o scan response do sub-bloco A.3 vai usar a mesma regra para filtrar `transicoes_permitidas` retornadas ao frontend.

### Decisao 4 — Admin bypassa setor E localizacao, mas NAO bypassa RN-007
**Decisao:** admin (`is_admin=true`) bypassa a validacao de setor em `validar_transicao` (consistente com ADR-018) E a validacao extra de localizacao da Decisao 3. Porem, admin **nao** bypassa a regra RN-007 "rota determinada pela localizacao do vendedor": se um admin STUDIO tenta aprovar diretamente (`RETIRADA -> APROVADA`), o `determinar_rota(admin)` levanta `RotaIndeterminavelError` porque admin nao e vendedor.
**Justificativa:**
  - **Admin bypassa setor/localizacao**: operacionalmente necessario para recovery (ex: admin precisa empurrar uma prova pelo fluxo se um usuario operacional sumiu). Consistente com Wave 1 (ADR-018).
  - **Admin nao aprova**: semanticamente, "aprovar" e uma acao que *o vendedor* faz sobre a prova — nao e algo que 3Studio pode fazer no lugar dele. Se admin pudesse aprovar, precisaria escolher rota manualmente (viola RN-007 "rota determinada automaticamente pela localizacao"). Melhor levantar excecao e forcar o admin a delegar para o vendedor certo.
**Testes:** `test_executar_aprovacao_admin_sem_localizacao_levanta_rota_indeterminavel` cobre o cenario.

### Decisao 5 — Reinicio de ciclo implementado na state_machine mas NAO exposto pelo endpoint do Lote A
**Decisao:** `executar_transicao` suporta a transicao `REPROVADA_PELO_VENDEDOR -> CRIADA` incrementando `prova.ciclo_atual += 1`, zerando `prova.rota = None` e gravando audit com `acao="reiniciar_ciclo"` (em vez de `"transitar_status"`). O endpoint `POST /provas/{id}/transicoes` do sub-bloco A.4 **rejeita explicitamente** `status_novo=CRIADA` com `TransicaoRequest` validator, para preservar a intencao de que reinicio de ciclo e acao administrativa (ver §3.3 do `WAVE3_LOTE_A_ANALYSIS.md`).
**Justificativa:** fazer generico uma vez e mais simples do que ter o Componente 14 (Lote C) ter que modificar o state_machine mais tarde. O Componente 14 vai expor um endpoint admin dedicado `POST /provas/{id}/reiniciar-ciclo` que chama a mesma `executar_transicao` sem a limitacao do validator de `TransicaoRequest`.
**Contrato exposto:** o `motivo_cancelamento: str | None = None` no parametro de `executar_transicao` ja esta reservado para C13 (cancelamento via endpoint dedicado) — funciona sem mudar a assinatura.

### Decisao 6 — Cancelamento aceita motivo mas nao expose pelo endpoint do Lote A
**Decisao:** analoga a Decisao 5 — `executar_transicao` valida `motivo_cancelamento` quando `status_novo == CANCELADA` e grava em `prova.motivo_cancelamento`, mas o endpoint do Lote A rejeita `status_novo=CANCELADA`. Preparado para C13 (Lote C).

### Decisao 7 — `rota_no_momento` da movimentacao reflete estado POS-transicao
**Decisao:** o campo `Movimentacao.rota_no_momento` e gravado com a rota vigente APOS a transicao aplicada, nao antes:
  - Aprovacao (RETIRADA -> APROVADA): grava a rota recem-determinada (`PADRAO` ou `DIRETA`).
  - Reinicio de ciclo (REPROVADA -> CRIADA): grava `None` (rota foi zerada).
  - Outras transicoes: grava a rota vigente da prova (inalterada).
**Alternativa:** gravar sempre a rota "antes" (rota_antes, pre-aprovacao).
**Por que depois:** a `rota_no_momento` e usada pelo Componente 12 (Timeline, Lote B) para renderizar a ramificacao visual da timeline. O que queremos mostrar no evento "foi aprovada" e a rota que foi **decidida** naquele momento — nao a ausencia de rota anterior. Semanticamente, "movimentacao X aconteceu na rota Y" significa "no momento da movimentacao X, a prova estava seguindo a rota Y". E a rota e definida justo na aprovacao.

### Decisao 8 — `audit_log` estruturado com `de`/`para`/`rota_antes`/`rota_depois`/`ciclo`
**Decisao:** `detalhes_json` do audit contem:
```json
{
  "de": "RETIRADA_PELO_VENDEDOR",
  "para": "APROVADA_PELO_VENDEDOR",
  "ciclo": 1,
  "rota_antes": null,
  "rota_depois": "PADRAO",
  "motivo_reprovacao": "...",   // opcional
  "motivo_cancelamento": "..."  // opcional
}
```
**Por que esses campos:**
  - `de`/`para` como strings (nao enums) facilita query SQL: `detalhes_json->>'para' = 'APROVADA_PELO_VENDEDOR'`.
  - `rota_antes`/`rota_depois` capturam mudanca de rota para quando investigacao precisar saber o momento em que a rota foi definida.
  - `ciclo` captura o ciclo daquela transicao (ja e o `ciclo_atual` pos-transicao — serve para filtrar todos os eventos do ciclo 2 da prova X).
  - Motivos so aparecem quando aplicaveis (nao poluem com `null`).
**Consequencias:** tela de auditoria da Wave 6 vai ter queries diretas em `detalhes_json` sem precisar de JOIN com `movimentacoes`. Util para analise historica.

### Arquivos tocados
- `backend/app/services/state_machine.py` — stub removido, `executar_transicao` implementada (~140 linhas incluindo docstring). Imports adicionados: `typing.Any`, `fastapi.Request`, `sqlalchemy.ext.asyncio.AsyncSession`, `Movimentacao`, `ProvaDigital` dos models, `log_audit` do `audit_service`.
- `backend/tests/test_state_machine.py` — stub test removido, adicionados **29 testes** (20 da secao 8.1 do plano + 4 extras de cancelamento/admin/request + 1 defensive para 100% cobertura do `determinar_rota`). Helper local `make_prova` + constante `ASSINATURA_FAKE`. Fixture local `mock_log_audit` que patcha `app.services.state_machine.log_audit`.

### Metricas (Sub-bloco A.1)
- **Testes:** 308 (pos-Sessao 22) → **332** (+24 testes absolutos; 55 no test_state_machine.py antes 32 = +23 novos + 1 cobertura defensive).
- **Cobertura `state_machine.py`:** 100% (90 stmts, 0 missing).
- **ruff** em `app/services/state_machine.py` + `tests/test_state_machine.py`: limpo.
- **ruff** no backend inteiro: 6 erros pre-existentes em `migrations/` reportados em `WAVE3_BLOCKERS.md` B-01. **Resolvido na mesma sessao (opcao B)**: adicionado `extend-exclude = ["migrations"]` no `pyproject.toml` apos autorizacao do Mario. Zero arquivo de `migrations/` tocado — preserva a regra "nao tocar em Waves anteriores".

---

## ADR-082 — RLS 006: `pol_movimentacoes_insert` + expansao de `pol_movimentacoes_select` para MOTORISTA/CLICHERIA (Wave 3 Lote A / Sub-bloco A.2)
**Data:** 2026-04-10 (Wave 3 Lote A, sub-bloco A.2)
**Contexto:** O sub-bloco A.1 implementou `executar_transicao`, que passa a fazer INSERTs reais em `movimentacoes`. Antes de o endpoint `POST /provas/{id}/transicoes` (sub-bloco A.4) entrar no ar, a camada RLS precisa:
  1. Ter uma policy INSERT em `movimentacoes` — consistencia com as outras tabelas (`usuarios`, `provas_digitais`) que tem policy INSERT admin-only explicita.
  2. Resolver o debito F03 da auditoria externa da Sessao 22 — `pol_movimentacoes_select` atual (definida em `005_initplan_optimization.sql`) cobre apenas admin + vendedor das suas provas + autor da movimentacao, mas NAO cobre MOTORISTA nem CLICHERIA, em desacordo com `pol_provas_select` que cobre os 4 atores.

O backend ja cobre o scoping corretamente em tempo de aplicacao via `_carregar_prova_com_scoping` + `_scoping_filter` (ADR-046, ADR-049) porque usa service_role e bypassa RLS. Mas RLS e defesa em profundidade — se algum cliente futuro (supabase-js direto, outra integracao) acessar `movimentacoes`, precisa da policy correta.

### Decisao 1 — Nova policy `pol_movimentacoes_insert` admin-only
**Decisao:** criar `pol_movimentacoes_insert` com `WITH CHECK (is_admin = true)`, espelhando `pol_provas_insert`.
**Alternativas:**
  - Nao criar policy INSERT (comportamento padrao: RLS habilitada + sem policy INSERT = tudo bloqueado). Tecnicamente equivalente no estado atual (service_role bypassa RLS), mas inconsistente com as outras tabelas e confuso para auditoria (alguem olhando `pg_policies` veria `movimentacoes` so com SELECT e pensaria "esqueceram").
  - Policy INSERT permissiva (`WITH CHECK (true)`). Rejeitada: deixa qualquer usuario autenticado inserir via supabase-js. Viola RN-003 (so o ator autorizado insere movimentacao).
  - Policy INSERT espelhando `ATORES_POR_TRANSICAO` (vendedor/motorista/clicheria por transicao). Rejeitada: RLS policies sao por linha, nao podem consultar `state_machine.py`. Alem disso, o scoping operacional fica no backend, nao na RLS. A RLS e grade, nao lock.
**Consequencias:**
  - Todas as tabelas publicas com INSERT tem policy INSERT explicita (`usuarios`, `provas_digitais`, agora `movimentacoes`). Consistencia audit-friendly.
  - Backend continua funcionando identico (service_role bypassa RLS).
  - Acesso direto via supabase-js client so conseguiria inserir movimentacao se autenticado como admin, o que faz zero sentido operacional mas preserva a door.

### Decisao 2 — Expansao de `pol_movimentacoes_select` espelhando `pol_provas_select`
**Decisao:** `DROP POLICY IF EXISTS pol_movimentacoes_select ON movimentacoes; CREATE POLICY...` com a versao estendida que cobre os 5 casos:
  1. Admin ve tudo
  2. Vendedor ve movimentacoes das suas proprias provas (inalterado)
  3. Autor ve suas proprias movimentacoes (inalterado)
  4. **[NOVO]** MOTORISTA ve movimentacoes de provas atualmente em `COM_MOTORISTA`
  5. **[NOVO]** CLICHERIA ve movimentacoes de provas em `ENVIADA_PARA_CLICHERIA`, `ENCAMINHADA_A_CLICHERIA` ou `RECEBIDA_PELA_CLICHERIA`

Os dois novos casos seguem exatamente a mesma logica de `pol_provas_select` linhas 75-99 — os atores operacionais veem movimentacoes de provas que estao na sua "caixa de entrada" operacional.

### Decisao 3 — Status atual da prova como criterio, nao status_anterior/status_novo da movimentacao
**Decisao:** o JOIN com `provas_digitais` usa o status ATUAL da prova (`pd.status = 'COM_MOTORISTA'`), nao o status da movimentacao em si (`m.status_anterior = 'COM_MOTORISTA'` ou `m.status_novo = 'COM_MOTORISTA'`).
**Alternativa considerada:** usar o historico (`m.status_anterior` ou `m.status_novo`) para que um motorista continue vendo movimentacoes de provas que ja saíram do status COM_MOTORISTA (ex: ja estao em ENVIADA_PARA_CLICHERIA).
**Por que usar status atual:**
  1. Semantica alinhada com `pol_provas_select`: se o motorista pode ver a prova X via `pol_provas_select` (porque ela esta em COM_MOTORISTA), ele pode ver o historico de movimentacoes dela. Se nao pode ver a prova X (porque ela saiu do status COM_MOTORISTA), nao ve o historico.
  2. Scoping consistente entre tabelas: usuario ve "o que pode ver agora", nao "o que ja pôde ver um dia".
  3. Preserva a regra do autor (OR usuario_id = ...) — o motorista que executou a transicao `COM_MOTORISTA -> ENVIADA` continua vendo *sua propria* movimentacao mesmo apos a prova sair do seu scope, porque ele e o autor. Isso mantem a rastreabilidade pessoal sem vazar historico geral.
**Efeito pratico:** um motorista transicionando `COM_MOTORISTA -> ENVIADA_PARA_CLICHERIA` deixa de ver as movimentacoes anteriores daquela prova, exceto a ultima que ele mesmo executou. Aceitavel — o backend ja retorna o historico completo para motorista via scoping do endpoint `GET /provas/{id}/movimentacoes` (que carrega com service_role). RLS e so defesa em profundidade.

### Decisao 4 — Ordem em relacao ao script 005 via `apply_rls.py`
**Decisao:** criar como `006_movimentacoes_insert_and_expand_select.sql`. O `apply_rls.py` (Wave 0) aplica via `sorted(glob("*.sql"))`, ordem numerica — entao 006 roda DEPOIS de 005. O `DROP POLICY IF EXISTS pol_movimentacoes_select` + `CREATE POLICY` no 006 sobrescreve a versao que 005 definiu. Idempotente.
**Consequencia:** se alguem reaplicar 005 manualmente depois de 006 (via `psql`, nao via `apply_rls.py`), a policy volta para a versao antiga sem MOTORISTA/CLICHERIA. O jeito seguro de reaplicar e via `apply_rls.py` que roda tudo em ordem.

### Decisao 5 — Nao tocar no 005 para atualizar o comment TODO da F03
**Decisao:** o arquivo `005_initplan_optimization.sql` linhas 130-146 tem um comment explicitando o debito F03 e apontando para o nome hipotetico `006_rls_movimentacoes_atores_completos.sql`. Nao atualizei esse comment para remover a aviso ou trocar o nome do arquivo, porque isso violaria a regra "nao tocar em Waves anteriores sem autorizacao expressa". O comment fica como marcador historico — qualquer leitor curioso vai ver o 006 ao lado e entender.
**Consequencias:** comentario ligeiramente desatualizado (nome de arquivo hipotetico nao bate com o real), mas preservacao estrita da regra do plano Wave 3.

### Arquivos tocados
- `backend/migrations/rls/006_movimentacoes_insert_and_expand_select.sql` — novo, 130 linhas incluindo docstring comentado.
- `backend/migrations/rls/apply_rls.py` — NAO tocado (usa glob automatico).
- `docs/db/schema.sql` — atualizado: header menciona Wave 3 A.2 + RLS 006, lista de migrations RLS acrescenta o 006 com descricao, secao "ROW LEVEL SECURITY" atualizada para 12 policies e semantica correta de `movimentacoes`.

### Aplicacao em producao
Aplicado via MCP `execute_sql` no projeto Supabase `rwxlpwmnkekzuurgthkr` em 2026-04-10. Validacoes pos-aplicacao:
- `SELECT COUNT(*) FROM pg_policies WHERE schemaname='public'` = **12** (era 11).
- `SELECT policyname, cmd FROM pg_policies WHERE schemaname='public' AND tablename='movimentacoes'` retorna exatamente:
  - `pol_movimentacoes_insert` (INSERT)
  - `pol_movimentacoes_select` (SELECT)
- `get_advisors type=security`: zero novos lints — continua com os 2 aceitos (rls_enabled_no_policy em alembic_version por ADR-025, auth_leaked_password_protection por ADR-027).
- `get_advisors type=performance`: zero novos lints — continua com os 9 `unused_index` que ficarao ativos assim que o Lote A comecar a inserir movimentacoes reais.

### Metricas (Sub-bloco A.2)
- **Policies RLS em producao:** 11 → **12** (+1 `pol_movimentacoes_insert`).
- **Politica expandida:** `pol_movimentacoes_select` passa de 3 casos para 5 (cobre MOTORISTA + CLICHERIA).
- **Advisor Supabase:** inalterado (security + performance).
- **Debito F03 da Sessao 22:** RESOLVIDO.
- **Testes:** suite inalterada (332 passed) — a RLS e infraestrutural, nao quebra nenhum teste existente porque o backend usa service_role nos testes.

---

## ADR-083 — `POST /api/v1/provas/scan`: resolver QR Code + computar transicoes permitidas (Wave 3 Lote A / Sub-bloco A.3)
**Data:** 2026-04-10 (Wave 3 Lote A, sub-bloco A.3)
**Contexto:** O Componente 10 do Backlog v3.0 pede um endpoint de "leitura de QR Code via camera" que o frontend `/escanear` (sub-bloco A.5) consome apos o html5-qrcode decodificar uma imagem. O endpoint precisa:
  1. Receber o payload decodificado (`"3SD|{nro_req}|{hash_trunc}"`).
  2. Validar estrutura + integridade (hash truncado constant-time).
  3. Resolver qual prova ele aponta.
  4. Aplicar scoping (ADR-046/049) — 404 se escondida.
  5. Calcular quais transicoes o usuario corrente pode executar a partir do estado atual — para a UI decidir qual botao renderizar.
  6. Logar audit da acao "escanear_prova" (rastreabilidade RNF-005).

Existe um hand-off limpo entre este sub-bloco e o A.4 (endpoint de transicao): A.3 entrega a "lista de botoes que a UI pode mostrar", A.4 entrega "o que acontece quando o usuario clica num deles".

### Decisao 1 — POST em vez de GET
**Decisao:** `POST /api/v1/provas/scan` com payload no body.
**Alternativa:** `GET /api/v1/provas/scan?payload=3SD|REQ-001|abcdef1234567890`.
**Por que POST:**
  1. **Acao, nao consulta pura**: o endpoint grava audit log a cada scan (quem olhou qual prova). Mesmo que nao mude estado do dominio, e uma "acao" no sentido de auditoria — convencao HTTP e que acoes auditadas sao POST/PUT/PATCH/DELETE.
  2. **Encoding de char especial**: `|` e reservado em URL query strings. Pode ser escapado (`%7C`) mas complica logs de servidor. Body JSON e limpo.
  3. **Consistencia**: `POST /upload-url` tambem e um "request de acao" que cria nada no dominio mas e POST — mesmo padrao.
  4. **Cacheabilidade**: GET normalmente seria cacheavel por proxies. Nao queremos isso — cada scan e unico, e a resposta depende do usuario autenticado.
**Consequencias:** curl do endpoint exige `-X POST -H "Content-Type: application/json" -d '{"payload": "..."}'`. Aceitavel — o consumidor real e o frontend.

### Decisao 2 — Validacao de formato no Pydantic, hash no handler
**Decisao:** o `ScanRequest._valida_payload` faz 5 checks estruturais (nao vazio, prefixo `3SD|`, 3 campos, nro_req nao vazio, hash truncado com 16 chars). A verificacao real do hash (`validar_payload_qr(payload, prova.qr_code_hash)`) acontece DEPOIS do SELECT por nro_requerimento — precisamos do hash armazenado para comparar.
**Alternativa:** fazer a verificacao de hash tambem no validator do Pydantic.
**Por que separar:**
  - Validator Pydantic nao tem acesso ao banco (seria anti-pattern injetar dependencias).
  - Formato estrutural e responsabilidade do schema; integridade e responsabilidade do handler.
  - Separacao permite erros 422 distintos: "Formato de QR Code invalido" (pre-DB) vs "QR Code nao corresponde a prova esperada" (pos-DB). UX mais clara para debugging.
**Consequencias:** 4 testes de validator Pydantic + 1 teste de handler cobrindo hash errado. Cada path tem mensagem distinta e facil de localizar nos logs do frontend.

### Decisao 3 — SELECT por `nro_requerimento` em vez de `qr_code_hash`
**Decisao:** o SELECT usa `WHERE nro_requerimento = ?`, nao `WHERE qr_code_hash = ?`.
**Alternativa:** SELECT por `qr_code_hash = parts[2]` (usa o hash completo direto do banco).
**Por que nro_requerimento:**
  - O payload carrega apenas `hash[:16]` (16 chars) para o QR Code ficar pequeno (ADR-033). Nao podemos fazer SELECT por um prefixo de 16 chars sem full scan — e o `qr_code_hash` tem indice UNIQUE no banco (aproveita o UNIQUE em `nro_requerimento` tambem).
  - `nro_requerimento` e tambem UNIQUE e aproveita `provas_digitais_nro_requerimento_key`.
  - Semantica: o nro_requerimento e "o identificador humano", o hash truncado e "a prova de autenticidade". Separacao de concerns mais clara.
**Consequencia:** se um adversario trocar o hash truncado no payload mas manter o nro_requerimento, o SELECT encontra a prova real e a validacao de hash (`validar_payload_qr` constant-time) rejeita. Comportamento correto.

### Decisao 4 — Verificacao de hash DEPOIS do scoping
**Decisao:** o fluxo e: 1) SELECT com scoping aplicado → 2) 404 se None → 3) `validar_payload_qr` → 4) 422 se hash nao bate.
**Alternativa:** rodar `validar_payload_qr` antes do scoping, para retornar 422 "hash invalido" mesmo para provas fora do scope do usuario.
**Por que scoping primeiro:** alinhamento com ADR-049 "nao vazar existencia via timing". Se o hash fosse validado antes do scoping, um atacante com payload valido (que ele construiu sabendo o hash de outra prova) conseguiria distinguir "prova existe mas esta fora do seu scope" (404 apos hash OK) de "prova nao existe" (404 antes do hash). Com scoping primeiro, ambos viram 404 sem diferenca observavel.
**Consequencia:** o 422 so e retornado quando o usuario tem visibilidade da prova mas o payload nao bate — cenario realista de "adulterou o QR Code impresso".

### Decisao 5 — `_computar_transicoes_permitidas` espelha `executar_transicao`
**Decisao:** helper privado no `provas.py` que itera `TRANSICOES[prova.status]`, testa cada destino candidato com `validar_transicao` e aplica as mesmas regras extras do `executar_transicao` (sub-bloco A.1):
  - Filtra `CANCELADA` (gancho C13 — endpoint admin dedicado).
  - Filtra `CRIADA` quando origem e `REPROVADA_PELO_VENDEDOR` (gancho C14 — reinicio de ciclo admin).
  - Aplica RF-009 em `APROVADA_PELO_VENDEDOR -> *` (MATRIZ/FILIAL).

**Por que nao delegar para um helper compartilhado com o A.1:**
  - `executar_transicao` e orientada a "executar a transicao escolhida" — recebe um destino especifico e efetiva. `_computar_transicoes_permitidas` e orientada a "listar o que pode ser escolhido" — itera e filtra. Propositos diferentes, codigo diferente.
  - Duplicacao minima (~15 linhas das regras de rota) — aceitavel. Se o conjunto de regras crescer, refatoramos para uma funcao `transicao_permitida(atual, destino, usuario) -> bool` usada pelos dois.

**Consequencia chave:** **a UI nunca mostra um botao que seria rejeitado pelo endpoint de transicao do sub-bloco A.4**. Contrato: `scan.transicoes_permitidas` e superconjunto valido de `transicao(status_novo)` — se uma transicao esta na lista, ela passa no `executar_transicao` (sem erro de ator, rota, localizacao). Garante UX consistente.

### Decisao 6 — Audit log mesmo sem mudanca de estado
**Decisao:** scan grava `audit_log.acao = "escanear_prova"` com `detalhes_json = {nro_requerimento, status_atual, transicoes_permitidas}`.
**Alternativa:** nao auditar scans (scan e read-only).
**Por que auditar:**
  - RNF-005 exige log "completo". Um log que nao captura "quem olhou qual prova e quando" deixa de ser completo.
  - Cenario de incidente: "quem escaneou essa prova antes do cancelamento?" — responder isso exige o scan logado.
  - Custo: 1 INSERT por scan. Volume esperado ≈ numero de transicoes × 1.5 (scans incluem curiosidade e erros). Aceitavel ate 10k scans/mes.
**Consequencia:** o scan NAO e mais "read-only no dominio" — escreve em `audit_logs`. O commit e feito dentro do handler, e erro no commit retorna 502 com rollback.

### Decisao 7 — Ordenacao estavel de `transicoes_permitidas`
**Decisao:** a lista e ordenada alfabeticamente por `enum.value` antes de retornar. E determinista, facilita testes e garante UI estavel entre requests.
**Alternativa:** ordem natural de iteracao sobre set (nao-deterministica em Python pre-3.7 apenas, mas `set` em geral e desordenado).
**Por que alfabetica:** trivial, zero custo, deterministico. A UI do sub-bloco A.5 vai mapear cada status para um label PT-BR via `STATUS_LABELS` e talvez reordenar visualmente (ex: "Aprovar" antes de "Reprovar"). O backend nao precisa antecipar ordenacao semantica.

### Decisao 8 — Payload do audit inclui `transicoes_permitidas`
**Decisao:** o `detalhes_json` do audit inclui a lista de `transicoes_permitidas` calculada.
**Por que:** permite investigacao futura do tipo "por que o vendedor X nao conseguiu ver o botao Y quando escaneou a prova Z?" sem ter que recalcular a logica retroativamente (o state da prova ou do usuario pode ter mudado).
**Consequencia:** cada linha de audit de scan fica um pouco maior (100-200 bytes a mais). Aceitavel no free tier do Postgres.

### Arquivos tocados
- `backend/app/domain/schemas/prova.py` — +66 linhas: `ScanRequest` (payload validator) + `ScanResponse` (prova + transicoes_permitidas + motivo_obrigatorio_em).
- `backend/app/api/v1/provas.py` — +231 linhas:
  - Imports: `ScanRequest`, `ScanResponse`, `TRANSICOES`, `AtorNaoAutorizadoError`, `TransicaoInvalidaError`, `validar_transicao` (tirou `determinar_rota` sozinho da linha de import, ficou no grupo state_machine).
  - Novo helper `_computar_transicoes_permitidas(prova, usuario) -> tuple[list, list]`.
  - Novo helper `_carregar_prova_por_nro_req_com_scoping(db, nro_req, user)` — versao do scan do `_carregar_prova_com_scoping` (por id). Retorna 4-tupla, mesmo padrao.
  - Novo handler `scan_prova`.
- `backend/tests/test_provas_api.py` — +20 testes (13 do plano + 2 extras de payload Pydantic + 1 edge case de COM_MOTORISTA para cobertura 96% + 1 audit_log + 1 commit failure + 2 de whitespace/nro_req vazio).

### Metricas (Sub-bloco A.3)
- **Testes backend:** 332 (pos-A.2) → **352** (+20).
- **Novos testes de scan em `test_provas_api.py`:** 20.
- **Cobertura `provas.py`:** 95% → **96%** (378 stmts, 17 missing — todas pre-Wave 2).
- **Cobertura `schemas/prova.py`:** manteve em **96%** (114 stmts, 4 missing — todas pre-Wave 2).
- **Cobertura das linhas novas do A.3:** **100%** (zero linhas nova sem teste).
- **Ruff** em `app/ tests/ migrations/` via `ruff check .`: **limpo**.
- **Rotas publicas backend:** 24 → **25** (+ `POST /api/v1/provas/scan`).

### Contrato exposto ao Sub-bloco A.4
- `ScanResponse.transicoes_permitidas` e **garantidamente** subset valido de transicoes que `executar_transicao` vai aceitar para este usuario naquele estado. Se A.4 receber um `status_novo` que nao esta nessa lista (cliente malicioso), ele ainda deve rejeitar explicitamente — mas o cenario "UI renderizou botao -> usuario clicou -> 422" nao deveria acontecer.
- `motivo_obrigatorio_em` informa quais destinos exigem motivo no submit (Wave 3 Lote A: apenas `REPROVADA_PELO_VENDEDOR`). A UI do A.5 usa isso para decidir quando abrir textarea de motivo.

---

## ADR-084 — `POST /api/v1/provas/{id}/transicoes`: endpoint de transicao com FOR UPDATE + mapeamento HTTP (Wave 3 Lote A / Sub-bloco A.4)
**Data:** 2026-04-10 (Wave 3 Lote A, sub-bloco A.4)
**Contexto:** Quarto e ultimo sub-bloco backend do Lote A. Conecta o scan do A.3 ("quais botoes mostrar") a execucao do A.1 ("efetivar a escolha"). O handler e pequeno por desenho — o grosso da logica vive no `state_machine.executar_transicao` (ADR-081). Este ADR documenta apenas as decisoes de camada de transporte HTTP.

### Decisao 1 — `FOR UPDATE` obrigatorio via `lock=True` em `_carregar_prova_com_scoping`
**Decisao:** Estender `_carregar_prova_com_scoping(db, prova_id, user, *, lock=False)` com parametro keyword-only `lock`. Default `False` preserva os 5 callers Wave 2 sem mudanca. Quando `True`, aplica `.with_for_update(of=ProvaDigital)`.
**Alternativa considerada:** funcao separada `_carregar_prova_com_scoping_e_lock`.
**Por que estender:**
  1. Duplicar a funcao levaria a drift — qualquer mudanca no scoping teria que ser aplicada nos dois lugares.
  2. O parametro keyword-only e explicito no site do caller: `lock=True` aparece no codigo e e fácil de grep/audit.
  3. Default `False` garante zero impacto nos callers Wave 2.
**Consequencia:** apenas um caller usa `lock=True` no Lote A — o novo handler do sub-bloco A.4.

### Decisao 2 — `FOR UPDATE OF ProvaDigital` (nao em `usuarios` do JOIN)
**Decisao:** `.with_for_update(of=ProvaDigital)` — trava apenas a linha de `provas_digitais`, nao a linha de `usuarios` do JOIN.
**Alternativa:** `.with_for_update()` (default trava todas as linhas do SELECT, incluindo o vendedor).
**Por que apenas prova:**
  - A unicidade semantica que queremos proteger e "duas transicoes simultaneas na mesma prova". O vendedor pode estar sendo modificado em paralelo por outro admin (PATCH) sem afetar a integridade da transicao.
  - Evita contencao cruzada: se o admin estivesse atualizando um vendedor (`PATCH /users/{id}`) enquanto alguem transitasse uma prova desse vendedor, sem `of=`, uma operacao bloquearia a outra por 2-3s de roundtrip.
**Consequencia:** race-free para transicoes; update de usuario em paralelo nao bloqueia.

### Decisao 3 — `TransicaoInvalidaError` apos lock → **409 Conflict**
**Decisao:** qualquer `TransicaoInvalidaError` levantado por `executar_transicao` apos o FOR UPDATE vira HTTP 409 com mensagem "Status da prova mudou. Recarregue e tente novamente. (detalhe: ...)".
**Alternativa:** retornar 422 para "transicao ilegal" independente do momento, distinguindo de `AtorNaoAutorizadoError`.
**Por que 409:**
  1. **Semantica HTTP correta**: 409 Conflict e o status para "o recurso mudou desde a ultima leitura do cliente". Mesmo que o cliente nunca tenha lido nada (cliente malicioso tentando forcar estado), a mensagem "recarregue e tente novamente" faz sentido.
  2. **UX consistente com scan + transicao**: o fluxo real do usuario e `scan -> selecionar botao -> assinar -> submit`. Entre o scan e o submit, outro usuario pode ter transicionado a prova. Se o submit retornasse 422 ("destino invalido"), o usuario ficaria confuso porque ele clicou num botao que o backend ofereceu. O 409 "status mudou" comunica: "nao e voce, o mundo mudou — recarregue".
  3. **Cliente malicioso**: quem manda payload direto (sem passar pelo scan) tambem recebe 409. A mensagem "recarregue e tente novamente" nao fere ninguem e nao da mais info do que o usuario legitimo receberia.
**Consequencia:** teste `test_transicao_ilegal_pos_lock_retorna_409` valida o mapeamento; `test_transicao_estado_terminal_recebida_retorna_409` cobre o caso terminal.

### Decisao 4 — `AtorNaoAutorizadoError` vs `TransicaoInvalidaError` → codigos HTTP distintos
**Decisao:**
  - `TransicaoInvalidaError` → **409** (ver Decisao 3).
  - `AtorNaoAutorizadoError` → **422**.
  - `ValueError` (motivo ausente, assinatura vazia) → **422**.
  - `RotaIndeterminavelError` → **422**.
**Por que 422 para ator errado:** o "status da prova" nao mudou — o usuario simplesmente nao tem permissao de executar aquela transicao. 422 "unprocessable entity" captura isso corretamente. Recarregar o scan nao ajudaria — o usuario continua sem permissao.
**Consequencia:** o frontend pode distinguir "recarregue" (409) de "voce nao pode fazer isso" (422) e exibir mensagens diferentes.

### Decisao 5 — Decode base64 da assinatura em helper separado
**Decisao:** helper `_decode_assinatura(str) -> bytes` que:
  - Usa `base64.b64decode(v, validate=True)` para rejeitar chars nao-base64.
  - Levanta `HTTPException(422, "Assinatura base64 invalida")` em `binascii.Error`.
  - Levanta `HTTPException(422, "Assinatura vazia apos decode")` se `len(decoded) == 0`.

**Alternativa:** fazer o decode no handler principal.
**Por que helper separado:**
  - Testabilidade: teste unitario direto do helper (`test_decode_assinatura_vazia_apos_decode_raise_422`) sem passar pelo Pydantic `min_length=1`.
  - O cenario "base64 valido mas decodifica para 0 bytes" e teoricamente possivel mas raro — o `min_length=1` do Pydantic bloqueia string vazia antes de chegar ao handler, mas outras strings poderiam tecnicamente decodificar para vazio (`"===="` por exemplo gera binascii.Error, nao `b""`). O helper defende defensivamente.

### Decisao 6 — Gerar `id` e `created_at` da Movimentacao no Python (mudanca no ADR-081)
**Decisao:** **MUDANCA APLICADA** no `state_machine.executar_transicao` (sub-bloco A.1). A funcao agora gera `id = uuid.uuid4()` e `created_at = datetime.now(tz=timezone.utc)` explicitamente ao criar a Movimentacao, em vez de confiar nos server_defaults do banco.
**Motivo:** durante o desenvolvimento do handler do A.4, os testes happy path (11 testes) falharam com `pydantic_core.ValidationError: UUID input should be a string, ... input_value=None`. O `mock_db.flush()` nao preenche server_defaults, entao o `movimentacao.id` ficava `None` e o `TransicaoResponse` nao podia ser serializado.
**Alternativas consideradas:**
  - Fallback no handler: `movimentacao.id or uuid.uuid4()`. Rejeitado — mascarava um bug real em qualquer contexto que nao fosse mock.
  - Mockar o behavior do `flush` nos testes. Rejeitado — complica mocks e nao corrige o caso em que o driver real nao retorna via RETURNING.
  - Gerar no state_machine (escolhido). Por que:
    1. Consistente com o padrao do `create_prova` da Wave 2 que ja gera `prova_id = uuid.uuid4()` antes do INSERT.
    2. Determinismo: logs de producao mostram o ID antes do commit (`"Transicao OK: prova=... movimentacao=..."`).
    3. Handler nao precisa de `db.refresh(movimentacao)` — todos os campos ja estao populados.
    4. Testes ficam limpos.
**Consequencia:** ADR-081 foi implicitamente atualizado — a Decisao 7 "rota_no_momento reflete estado pos-transicao" ainda vale, mas agora junto com "id/created_at populados no Python".

### Decisao 7 — `TransicaoRequest.assinatura_base64` com `max_length=700_000`
**Decisao:** 700_000 chars de base64 ≈ 525 KB de PNG decodificado (overhead de ~33%). Limite generoso para signature canvas em celular.
**Alternativa:** limite menor (100 KB) ou maior (1 MB+).
**Por que 700_000:**
  - Signature pad tipico gera 30-100 KB em stroke medio. 700 KB da folga para dispositivo alto-DPI com stroke grosso.
  - Ao mesmo tempo protege o servidor de payloads absurdos que poderiam esgotar memoria no decode.
  - Armazenamento: 500 KB por movimentacao × estimativa 5000 movimentacoes/mes = ~2.5 GB/mes. Projecao para 1 ano ainda dentro do free tier do Supabase (500 MB Postgres + 500 MB media = apertado, mas viavel; se estourar, Wave 6 move assinaturas para R2 como cleanup job).
  - Constante exportada como `ASSINATURA_BASE64_MAX_BYTES` em `schemas/prova.py` para facilitar ajuste futuro.

### Decisao 8 — Rollback explicito em TODOS os paths de exception do handler
**Decisao:** cada `except` do handler chama `await db.rollback()` antes de levantar a HTTPException (excepto `TransicaoInvalidaError` onde o rollback e feito antes do raise 409, e `_carregar_prova_com_scoping` cujo except 502 nao precisa porque nao ha estado modificado ainda).
**Alternativa:** confiar no gerenciamento automatico de transacao do SQLAlchemy (o `get_db` da app faz rollback no context manager).
**Por que explicito:**
  - O `executar_transicao` faz `db.add(nova_movimentacao)` + `db.flush()` + `log_audit` antes de retornar. Se o handler cair em um except depois desse flush, o estado em memoria do SQLAlchemy fica sujo — o `db.rollback()` explicito limpa a transacao antes de qualquer proximo uso.
  - `get_db` no FastAPI fecha a sessao ao fim do request, mas nao rollback explicito — uma janela em que a sessao poderia ser reutilizada em outro lugar. Improvavel na arquitetura atual, mas defensive.
  - Testabilidade: os testes de erro (`test_transicao_*_422`, `test_transicao_db_error_*_502`) verificam `mock_db.rollback.assert_awaited()` explicitamente.

### Arquivos tocados
- `backend/app/domain/schemas/prova.py` — +84 linhas:
  - `ASSINATURA_BASE64_MAX_BYTES` constante (700_000).
  - `TransicaoRequest` com validators `_rejeita_cancelada_e_criada` + `_strip_motivo`.
  - `TransicaoResponse` (`prova` + `movimentacao`).
- `backend/app/api/v1/provas.py` — +178 linhas:
  - Imports: `TransicaoRequest`, `TransicaoResponse`, `executar_transicao` (do state_machine).
  - Estendido `_carregar_prova_com_scoping` com parametro `lock=False`.
  - Novo helper `_decode_assinatura(str) -> bytes`.
  - Novo handler `executar_transicao_prova` com mapeamento HTTP completo.
- `backend/app/services/state_machine.py` — +3 linhas:
  - Gera `id=uuid.uuid4()` e `created_at=datetime.now(tz=timezone.utc)` explicitamente na Movimentacao (ver Decisao 6).
  - Imports: `uuid`, `datetime`, `timezone`.
- `backend/tests/test_provas_api.py` — +37 testes:
  - 10 happy paths (uma por HU do Lote A: US-002 a US-009)
  - 5 validacoes Pydantic (CANCELADA, CRIADA, assinatura vazia/invalida/grande)
  - 14 rejeicoes de dominio (reprovacao sem motivo, ator errado, rota errada, admin sem localizacao, transicao ilegal → 409, terminal → 409, 404 inexistente/scoping/UUID invalido, 502 DB/commit/inesperado, 401, admin bypass, payload incompleto, enum invalido)
  - 4 unit/defensive (decode vazio, HTTPException propagando em 2 locais, `strip_motivo` com None explicito)

### Metricas (Sub-bloco A.4)
- **Testes backend:** 352 (pos-A.3) → **389** (+37).
- **Testes de transicao novos:** 37.
- **Cobertura `provas.py`:** 96% → **96%** (430 stmts, 17 missing — todas pre-Wave 2).
- **Cobertura `schemas/prova.py`:** 96% → **97%** (134 stmts, 4 missing — todas pre-Wave 2).
- **Cobertura `state_machine.py`:** 100% (mantido).
- **Cobertura das linhas novas do A.4:** **100%**.
- **Rotas publicas backend:** 25 → **26** (+ `POST /api/v1/provas/{id}/transicoes`). **Total do Lote A: 24 → 26 conforme plano.**
- **Ruff full backend:** limpo.

### Backend do Lote A — COMPLETO
Apos o sub-bloco A.4, o backend do Lote A esta **completo**:
- `state_machine.executar_transicao` implementada (A.1).
- RLS 006 aplicada — `movimentacoes` INSERT + SELECT expandido (A.2).
- `POST /api/v1/provas/scan` (A.3).
- `POST /api/v1/provas/{id}/transicoes` (A.4).

Proximo: **Sub-bloco A.5 — Frontend `/escanear`** com html5-qrcode + react-signature-canvas. Sub-bloco A.6: smoke E2E em staging + closeout do Lote A.

---

## ADR-085 — Frontend `/escanear`: maquina de estados client + wrapper html5-qrcode + signature canvas (Wave 3 Lote A / Sub-bloco A.5)
**Data:** 2026-04-10 (Wave 3 Lote A, sub-bloco A.5)
**Contexto:** Sub-bloco de frontend que consome os endpoints backend do A.3 (`POST /scan`) e A.4 (`POST /{id}/transicoes`). A UX esperada e: usuario clica "Abrir camera" → decodifica QR via html5-qrcode → backend resolve a prova e retorna botoes → usuario escolhe transicao → assina no canvas → submit → sucesso. Tudo numa unica pagina `/escanear` sem navegar entre rotas.

O Backlog v3.0 RNF-007 exige que o fluxo completo caiba em no maximo **3 toques/cliques**: (1) abrir camera, (2) escolher transicao, (3) confirmar assinatura. Nosso desenho cabe nisso — o scan acontece automaticamente ao apontar para o QR.

### Decisao 1 — Maquina de estados client-side com union discriminada
**Decisao:** A pagina `/escanear` mantem um unico `useState<PageState>` onde `PageState` e uma union discriminada com 8 variantes:
```typescript
type PageState =
  | { kind: "idle" }
  | { kind: "scanning" }
  | { kind: "scan-loading"; payload: string }
  | { kind: "scan-ready"; scan: ScanResponse }
  | { kind: "signing"; scan: ScanResponse; statusNovo: StatusProva; precisaMotivo: boolean }
  | { kind: "submitting" }
  | { kind: "done"; scan: ScanResponse; statusAplicado: StatusProva }
  | { kind: "scan-error"; message: string };
```
**Alternativas consideradas:**
  - `useReducer` classico com action types. Rejeitado: verbose, cria uma camada de indirection para os 5-6 transicoes simples.
  - Multiplos `useState` booleans (`isScanning`, `isSubmitting`, etc). Rejeitado: estados mutuamente exclusivos viram invariantes implicitos faceis de quebrar.
  - XState / Zustand / Redux. Rejeitado: overkill para 8 estados sem side effects assincronos complexos. Zero depedencia nova.
**Por que union discriminada:**
  - TypeScript narrowing funciona nativamente (`if (state.kind === "signing") { state.statusNovo }` e typesafe).
  - Cada renderizacao e um `switch` limpo — impossivel renderizar "scanner ativo" enquanto o backend esta submitting.
  - Transicoes sao explicitas via `setState({ kind: "...", ... })` — aparecem no grep, sao auditaveis.
**Consequencia:** a pagina tem ~180 linhas de codigo TSX + ~120 linhas de sub-componentes (`IdleView`, `ScanningView`, `ScanReadyView`, `AssinaturaModal`, `DoneView`, `ErrorView`), tudo no mesmo arquivo. Mantido em 1 arquivo porque os componentes sao sempre renderizados juntos e nao sao reutilizados fora da pagina.

### Decisao 2 — `useScanner` hook wrapper em volta de `html5-qrcode`
**Decisao:** Hook isolado `useScanner({ enabled, onDetect, onError })` que encapsula o ciclo de vida da camera. Retorna `{ divId, ready, error }`.
**Por que isolar:**
  1. **Lazy import SSR-safe**: o `html5-qrcode` depende de `navigator.mediaDevices` — nao pode ser importado no servidor. O hook faz `await import("html5-qrcode")` dentro do `useEffect`, garantindo que so roda no cliente. Se fosse importado no topo do arquivo, o SSR quebraria.
  2. **Cleanup defensivo**: a lib tem bug conhecido onde `stop()` pode lancar se o stream ja foi interrompido externamente (ex: user navegou para outra pagina pelo menu antes do scan terminar). Sem `try/catch`, a camera fica em uso ate refresh. O cleanup e `.stop().catch(...).finally(() => .clear())`.
  3. **Callbacks em `ref`**: `onDetect` e `onError` sao guardados em `useRef` e atualizados a cada render. Isso evita que o `useEffect` re-monte a camera toda vez que um callback muda (componente re-renderiza por causa de outro state).
  4. **`useId()` com sanitizacao**: React 18 `useId()` gera IDs como `:r0:`, que quebram `querySelector` (o html5-qrcode usa internamente). Sanitizamos para `scanner-r0`.
**Alternativas rejeitadas:**
  - `useRef` direto no componente principal (sem hook). Rejeitado — acopla logica de camera a logica de negocio da pagina, dificulta teste isolado.
  - `react-qr-reader` (wrapper React alternativo). Rejeitado — menos mantido, mesma API subjacente, nao adiciona valor.

### Decisao 3 — `html5-qrcode` configurado com `facingMode: "environment"` + `fps: 10`
**Decisao:**
```javascript
instance.start(
  { facingMode: "environment" },      // camera traseira em celulares
  { fps: 10, qrbox: { width: 250, height: 250 } },
  onDetect,
  noop,
)
```
**Por que esses valores:**
  - `facingMode: "environment"`: em celulares, usa a camera traseira automaticamente (melhor para escanear QR em etiquetas fisicas). Em desktop, cai na webcam padrao.
  - `fps: 10`: balanco entre latencia de deteccao (~100ms) e uso de CPU. 30fps gasta bateria sem ganho perceptivel — QRs sao estaveis.
  - `qrbox: 250x250`: um quadrado no centro onde o scanner foca. Fora do quadrado, a lib ignora — reduz falsos positivos em backgrounds ruidosos.
**RNF-002 atendido** (≤ 2s do scan a tela de assinatura): com fps=10 + o scan sendo servido na chamada `onDetect`, o tempo tipico e ~200-500ms de deteccao + ~300ms de roundtrip ao backend.

### Decisao 4 — Dois hooks de API distintos: `useScanProva` e `useExecutarTransicao`
**Decisao:** Dois hooks separados:
  - `useScanProva(getToken)` → `{ escanear, loading, error, result, reset }`
  - `useExecutarTransicao(getToken)` → `{ executar, loading, error, result, reset }`

Ambos tem state local interno, aceitam `getToken` como parametro (token provider pattern do Wave 2), e mapeiam `ApiError.status` para mensagens amigaveis em pt-BR.

**Por que separar:**
  - Semanticas distintas. `scanear` e de leitura (lista disponiveis), `executar` e de escrita (efetiva).
  - Cada um tem mapeamento de erro diferente:
    - `scanear` trata 404 "Prova nao encontrada" e 422 "hash invalido" como erros de usuario (mostra na tela de erro).
    - `executar` trata 409 "status mudou" distinto de 422 "ator errado" — mensagem diferente e path de recuperacao diferente (recarregar scan vs mostrar erro local).
  - Reutilizavel: se futuro C13 (cancelamento) ou C14 (reinicio) criar seus proprios botoes na tela de detalhe, eles podem importar `useExecutarTransicao` e chamar — ja que o contrato do endpoint e generico (via `state_machine.executar_transicao`).

**Alternativa:** um unico hook `useScanEMTransicao` com estado `step`. Rejeitado — acopla dois fluxos que podem ser independentes no futuro.

### Decisao 5 — `react-signature-canvas` com export via `.toDataURL("image/png").split(",")[1]`
**Decisao:** No submit, extraimos o base64 sem o prefixo `data:image/png;base64,`:
```typescript
const dataUrl = canvas.getCanvas().toDataURL("image/png");
const base64 = dataUrl.split(",")[1] ?? "";
```
**Por que:** o backend espera o base64 puro no campo `assinatura_base64` (ADR-084, `TransicaoRequest`). Remover o prefixo no cliente mantem o contrato simples no servidor.

**Validacoes client-side antes do submit** (defesa em profundidade — backend re-valida):
  1. `canvas.isEmpty()` → "Assinatura e obrigatoria."
  2. `precisaMotivo && !motivo.trim()` → "Motivo da reprovacao e obrigatorio."
  3. `base64.length > ASSINATURA_BASE64_MAX_BYTES (700_000)` → "Assinatura muito complexa. Tente um traco mais simples."

A constante `ASSINATURA_BASE64_MAX_BYTES` e exportada de `lib/types/prova.ts` — espelho canonico do backend (`schemas/prova.py`).

**Alternativa:** usar `getTrimmedCanvas()` para gerar PNG menor (bounding box do stroke). Rejeitado por enquanto — adiciona uma operacao de canvas cara e o ganho de tamanho e marginal no signature pad tipico (<100 KB). Pode ser adicionado no Lote B se for necessario.

### Decisao 6 — Modal de assinatura renderizado SOBRE o `ScanReadyView`
**Decisao:** Quando o estado e `signing`, a pagina renderiza **tanto** o `ScanReadyView` (em modo `readOnly`) **quanto** a modal `AssinaturaModal` em cima. Mesmo padrao da `VisualizarEtiquetaModal` do Componente 08.

**Por que manter o card visivel atras:**
  - Contexto: o usuario ve os dados da prova enquanto assina — "estou assinando essa prova aqui, ok".
  - Cancelamento: se o usuario errou a escolha de transicao, ele fecha o modal e ainda ve os botoes para escolher outra.
  - Consistencia: o Componente 08 (Wave 2) ja usa o mesmo padrao modal-sobre-pagina.

**Alternativa:** replacement completo do card por um full-screen signature pad. Rejeitado — remove contexto da prova.

### Decisao 7 — Labels pt-BR das transicoes num mapa local, nao em `types/prova.ts`
**Decisao:** A pagina tem um `ACTION_LABELS: Partial<Record<StatusProva, string>>` com entradas como `RETIRADA_PELO_VENDEDOR: "Retirar prova"`, `DE_VOLTA_3STUDIO: "Devolver a 3Studio"`, etc. Fallback para `STATUS_LABELS[destino]` (ja existente em `types/prova.ts`) quando nao ha label de acao especifica.
**Por que local:**
  - Sao labels de **acao** ("Retirar prova"), diferentes dos labels de **estado** ("Retirada pelo vendedor"). Misturar no mesmo arquivo de types confunde.
  - Usado apenas pela pagina `/escanear`. Se outra pagina precisar no futuro, movemos.

**Consequencia:** se o Componente 13 (cancelamento, Lote C) adicionar um botao "Cancelar" similar, ele vai precisar reimplementar a logica de label ou refatorar para `types/prova.ts` — deixado para quem encontrar o caso real.

### Decisao 8 — Botao "Reprovar" usa `dangerButton` (vermelho), outros usam `primaryButton` (amarelo)
**Decisao:** No loop `transicoes_permitidas.map(...)`, o botao para `REPROVADA_PELO_VENDEDOR` recebe `styles.dangerButton` (vermelho `--color-danger`). Todos os outros destinos recebem `styles.primaryButton` (amarelo `--color-accent`).
**Por que:** destaque visual para uma acao destrutiva/negativa. Reprovacao e irreversivel no sentido de que gera uma movimentacao imutavel com motivo — merece confirmacao visual explicita.

### Arquivos tocados
- `frontend/package.json` — adicionado `html5-qrcode@^2.3.8`, `react-signature-canvas@^1.0.7`, `@types/react-signature-canvas@^1.0.7`.
- `frontend/package-lock.json` — atualizado via `npm install`.
- `frontend/src/lib/types/prova.ts` — +66 linhas: `ScanRequest`, `ScanResponse`, `TransicaoRequest`, `TransicaoResponse`, `ASSINATURA_BASE64_MAX_BYTES`.
- `frontend/src/hooks/useScanProva.ts` — novo, 94 linhas.
- `frontend/src/hooks/useExecutarTransicao.ts` — novo, 115 linhas.
- `frontend/src/hooks/useScanner.ts` — novo, 152 linhas.
- `frontend/src/app/(dashboard)/escanear/page.tsx` — novo, 463 linhas (pagina + 6 sub-componentes).
- `frontend/src/app/(dashboard)/escanear/escanear.module.css` — novo, 376 linhas.
- `frontend/src/app/(dashboard)/layout.tsx` — **1 linha**: adicionado `href: "/escanear"` ao item "Escanear" do `MAIN_NAV`. **Unica mudanca fora de `escanear/`** — intocou tudo o resto do layout.

### Metricas (Sub-bloco A.5)
- **Arquivos novos no frontend:** 5 (3 hooks + page.tsx + module.css).
- **Dependencias npm novas:** 3 (`html5-qrcode`, `react-signature-canvas`, `@types/react-signature-canvas`).
- **TypeScript strict:** `tsc --noEmit` limpo ✅.
- **ESLint:** `next lint` — "No ESLint warnings or errors" ✅.
- **Next.js build:** `next build` ✅ — 1 warning pre-existente em `provas/provas.module.css:124` (autoprefixer `end` em `justify-content`, Wave 2, nao tocado).
- **Bundle da nova pagina `/escanear`:** 11.4 kB + 161 kB First Load JS. Dentro do aceitavel para pagina com scanner QR + signature canvas.
- **Dev server smoke:** `preview_start` → `/escanear` retorna 200 via middleware (redireciona para `/login` para usuarios nao autenticados, correto). Zero erros no console, zero erros no servidor.

### Debito pre-existente observado (nao-regressao do A.5)
- **B-02 (WAVE3_BLOCKERS.md):** `npm audit` reporta 4 high severity em `next@14.2` (CVEs de DoS/request smuggling). Pre-existente desde Wave 1. Fix exige upgrade para Next 16 (breaking). **Aceito como TODO Wave 6** apos autorizacao do Mario (ver B-02 no WAVE3_BLOCKERS.md).

### Proximo passo
**Sub-bloco A.6 — Smoke E2E em staging + closeout do Lote A**, que inclui:
1. Seed de 3 usuarios de teste (Vendedor MATRIZ, Motorista, Clicheria) — pre-requisito do plano §9.3 P1.
2. Fluxo completo manual em staging: criar prova → escanear → retirar → aprovar → devolver → motorista → clicheria.
3. Fluxo FILIAL (rota direta) com vendedor existente (Mario Souza FILIAL).
4. Teste de reprovacao com motivo.
5. `WAVE3_LOTE_A_CLOSEOUT.md` com DoD dos Componentes 10 e 11 + cobertura final.

---

## ADR-086 — Deploy em producao: Railway (backend) + Vercel (frontend) (Wave 3 Lote A / Deploy)
**Data:** 2026-04-13 (Wave 3 Lote A, deploy em producao)
**Contexto:** Primeiro deploy do sistema completo. Objetivo: testar os Componentes 10 e 11 (scanner QR + assinatura + transicao) no celular com camera real em HTTPS (necessario para `getUserMedia`).

### Decisao 1 — `requirements.txt` em vez de `pip install -e .` para Railway
**Decisao:** Criar `backend/requirements.txt` explicito com as mesmas deps do `pyproject.toml`. Railway nixpacks detecta automaticamente e roda `pip install -r requirements.txt`.
**Alternativa rejeitada:** `pip install -e .` (editavel) via setuptools. Falhou no Railway por dois motivos:
  1. Setuptools flat-layout error: detectou `app` e `migrations` como dois pacotes top-level e recusou o build. Fix parcial: `[tool.setuptools.packages.find] include = ["app*"]`.
  2. Mesmo apos o fix, o executavel `uvicorn` ficava fora do PATH no runtime do Railway. `python -m uvicorn` resolve, mas o `requirements.txt` e mais confiavel.
**Consequencia:** `pyproject.toml` continua como fonte canonica das deps para desenvolvimento local (`pip install -e ".[dev]"`). `requirements.txt` e espelho simplificado para deploy. Se uma dep for adicionada/removida, atualizar ambos.

### Decisao 2 — `python -m uvicorn` em vez de `uvicorn` direto
**Decisao:** Start command usa `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
**Alternativa rejeitada:** `uvicorn app.main:app ...` direto. Falhou com `command not found` porque o nixpacks do Railway instala deps num virtualenv cujo `bin/` nao esta no PATH do shell de start.
**Consequencia:** `python -m` sempre encontra modulos instalados no venv ativo. Procfile atualizado.

### Decisao 3 — CORS via variavel `FRONTEND_URL` no Railway
**Decisao:** O backend le `FRONTEND_URL` (env var) e configura `CORSMiddleware.allow_origins` com esse valor. No Railway, a variavel deve ser a URL exata da Vercel (ex: `https://prova-digital-five.vercel.app`), sem barra no final.
**Por que nao `allow_origins=["*"]`:** violaria RNF-004 (seguranca) — qualquer site poderia chamar a API com o token do usuario.
**Consequencia:** a cada mudanca de dominio da Vercel (ex: dominio customizado futuro), atualizar `FRONTEND_URL` no Railway.

### URLs de producao
- **Backend:** `https://provadigital-production.up.railway.app`
- **Frontend:** `https://prova-digital-five.vercel.app`
- **Health check:** `https://provadigital-production.up.railway.app/health`

---

## ADR-087 — Timeline Visual: Framer Motion + componente extraido + buildTimelineNodes puro (Wave 3 Lote B / Componente 12)
**Data:** 2026-04-13 (Wave 3 Lote B)
**Contexto:** Componente 12 substitui o placeholder `<ul>` de movimentacoes na pagina `/provas/[id]` por uma timeline visual animada. O DAT v2.0 especifica Framer Motion como lib de animacao.

### Decisao 1 — Componente `Timeline.tsx` extraido (nao inline na page.tsx)
**Decisao:** Criar `Timeline.tsx` como componente separado no mesmo diretorio, recebendo `movimentacoes` e `prova` como props.
**Alternativa rejeitada:** Manter tudo inline na `page.tsx` como o placeholder fazia.
**Por que extrair:**
  - A page.tsx ja tem ~280 linhas (dados + arte + modal + breadcrumb). Adicionar ~180 linhas de timeline inline ultrapassaria 400 linhas.
  - O componente Timeline tem logica de transformacao de dados (`buildTimelineNodes`) que se beneficia do isolamento.
  - Passivo para Lote C: se C13/C14 quiserem renderizar timeline em outro contexto (ex: modal de confirmacao de cancelamento), o componente e importavel.
**Consequencia:** 2 arquivos novos (`Timeline.tsx` + `timeline.module.css`) em vez de editar 1 arquivo existente.

### Decisao 2 — `buildTimelineNodes` como funcao pura (nao hook)
**Decisao:** Funcao pura `buildTimelineNodes(movimentacoes, prova) -> TimelineNode[]` que transforma os dados da API em nos renderizaveis. Chamada diretamente no corpo do componente (sem `useMemo` — o custo e desprezivel para <50 nos).
**Alternativa rejeitada:** `useMemo` com deps em movimentacoes/prova. Rejeitado porque a referencia de `movimentacoes` muda a cada re-render do `useProvaDetail` (shallow equality falha), e o custo da transformacao e O(n) com n < 50.
**Por que pura:** testavel sem DOM, deterministica, sem side effects. O modelo de dados `TimelineNode` facilita o mapeamento para JSX com flags booleanas (`isCurrent`, `isReprovacao`, `isCancelamento`, `isTerminal`, `isRoteamento`).

### Decisao 3 — No implicito "Criada" no inicio do ciclo 1
**Decisao:** Adicionar um no "Criada" com `id="initial-criada"`, `usuarioSetor="STUDIO"` e `createdAt=prova.created_at` no inicio da timeline. Este no nao corresponde a uma movimentacao — representa o estado inicial da prova quando foi criada via `POST /provas`.
**Por que:** A primeira movimentacao real (CRIADA→RETIRADA) nao captura o momento da criacao — apenas o momento da retirada. Sem o no implicito, o usuario nao veria quando a prova entrou no sistema. Para ciclos subsequentes (reinicio), o no CRIADA ja existe como `status_novo` de uma movimentacao real (REPROVADA→CRIADA).
**Consequencia:** `usuarioNome: "3Studio"` e uma aproximacao — o sistema nao retorna quem criou a prova em `ProvaResponse`. Suficiente porque apenas admins 3Studio criam provas.

### Decisao 4 — Agrupamento por `ciclo` da movimentacao (nao por `ciclo_atual` da prova)
**Decisao:** Agrupar nos por `movimentacao.ciclo`, nao por `prova.ciclo_atual`. Cada grupo recebe um separador "Ciclo N" quando ha mais de um ciclo.
**Por que:** `prova.ciclo_atual` e o ciclo corrente (escalar). `movimentacao.ciclo` e o ciclo no momento daquela transicao — permite reconstruir o historico. Semantica de ciclo no backend (ADR-081): a movimentacao de reinicio (REPROVADA→CRIADA) recebe `ciclo=N+1` (o novo ciclo), agrupando-se com as movimentacoes subsequentes do novo ciclo.

### Decisao 5 — Framer Motion `motion.div` com staggered entrance
**Decisao:** Cada no da timeline e um `motion.div` com variantes `hidden → visible`, delay incremental de 70ms por no (`delay: i * 0.07`). O no atual recebe um `motion.div` interno para a animacao de pulso do ponto (`scale + opacity` em loop infinito).
**Alternativa rejeitada:** CSS `@keyframes` para o pulso. Rejeitado porque Framer Motion ja esta no bundle e oferece mais controle (ex: parar animacao quando nao visivel).
**Alternativa rejeitada:** `AnimatePresence` para animacao de saida. Rejeitado — a timeline nao remove nos dinamicamente; uma vez renderizada, so atualiza via refetch completo.
**Impacto no bundle:** `/provas/[id]` foi de ~11 kB (Wave 2) para 46 kB. O delta (~35 kB) e primariamente Framer Motion (tree-shaken). Aceitavel para uma pagina com animacoes.

### Decisao 6 — CSS Module separado (`timeline.module.css`)
**Decisao:** Criar `timeline.module.css` em vez de adicionar classes ao `detalhe.module.css` existente.
**Por que:** As classes antigas do placeholder (`timelineList`, `timelineItem`, `timelineHeader`, `timelineStatus`, `timelineDate`, `timelineMeta`, `timelineMotivo`) foram removidas do `detalhe.module.css`. O novo CSS e semanticamente distinto (nos verticais, conectores, badges, pulso) e nao compartilha classes com o restante do detalhe. Separar mantém cada CSS Module focado.
**Consequencia:** `detalhe.module.css` mantem `timelineCard` e `timelineTitle` (container e titulo do card preto). `timeline.module.css` cuida de tudo dentro.

---

## ADR-088 — Cancelamento + Reinicio de Ciclo: endpoints admin dedicados com assinatura sintetica (Wave 3 Lote C / Componentes 13+14)
**Data:** 2026-04-13 (Wave 3 Lote C)
**Contexto:** Componentes 13 (RF-010, RN-005) e 14 (RF-008, RN-006) implementam acoes administrativas que nao passam pelo fluxo de scan + assinatura visual do Componente 11. A `executar_transicao` (Lote A) suporta ambas as transicoes mecanicamente, mas requer `assinatura_digital` nao-vazia e rejeita CANCELADA/CRIADA via `TransicaoRequest` no endpoint de transicao generico.

### Decisao 1 — Endpoints dedicados em vez de estender POST /transicoes
**Decisao:** Criar `POST /{id}/cancelar` e `POST /{id}/reiniciar-ciclo` como endpoints separados, ambos usando `get_admin_user`.
**Alternativa rejeitada:** Estender `POST /{id}/transicoes` para aceitar CANCELADA e CRIADA. Rejeitado porque: (a) misturaria acoes admin com acoes de scan/assinatura, (b) o `TransicaoRequest` exige `assinatura_base64` obrigatorio, (c) o Lote A explicitamente rejeita esses destinos como gancho para endpoints dedicados.
**Consequencia:** 28 rotas backend (26 → 28). Contratos do Lote A intactos.

### Decisao 2 — Assinatura sintetica `ACAO_ADMINISTRATIVA:{acao}:{nome}`
**Decisao:** Os endpoints geram `f"ACAO_ADMINISTRATIVA:{acao}:{usuario.nome}".encode("utf-8")` e passam para `executar_transicao` como `assinatura_digital`.
**Alternativa rejeitada:** Tornar `assinatura_digital` nullable (requer migration Alembic + alteracao da `executar_transicao`).
**Alternativa rejeitada:** Exigir assinatura visual mesmo para admin (adiciona friccao UX sem beneficio — admin ja esta autenticado + audit log registra tudo).
**Por que sintetica:**
  1. `executar_transicao` nao e modificada — contrato Lote A preservado.
  2. `movimentacoes.assinatura_digital BYTEA NOT NULL` satisfeito sem migration.
  3. O marcador e semanticamente util: identifica que foi acao admin, quem executou.
  4. O `audit_log.detalhes_json` ja registra o contexto completo (acao, usuario, prova).

### Decisao 3 — `useCurrentUser` hook dedicado (nao React Context do layout)
**Decisao:** Criar `useCurrentUser()` que chama `GET /api/v1/users/me` e retorna `{ user, loading }`. Usado na detail page para condicionar botoes admin.
**Alternativa rejeitada:** Criar React Context no layout e prover `user` para children. Rejeitado porque requer modificar `layout.tsx` (Wave 1) e adicionar context provider.
**Por que hook dedicado:** Zero alteracao em codigo existente. A duplicacao da request (layout ja busca /me) e desprezivel (<1 KB response). `didFetch` ref previne re-fetches em re-renders.

### Decisao 4 — Validacao rapida antes de `executar_transicao`
**Decisao:** Ambos os endpoints fazem validacao previa (cancelar: `pode_cancelar(status)`, reiniciar: `status != REPROVADA`) ANTES de chamar `executar_transicao`. Retornam 409 diretamente se a condicao falha.
**Por que:** Evita entrar na logica completa de `executar_transicao` para rejeitar estados obvios. O 409 com mensagem especifica ("nao pode ser cancelada" / "so permitido para provas reprovadas") e mais informativo que o generico "Transicao invalida" da state machine.
**Consequencia:** Dupla validacao (endpoint + state_machine), mas o custo e negligivel e a UX e melhor.

---

## ADR-089 — Entrada manual de codigo QR + payload copiavel (Review C11)
**Data:** 2026-04-13 (Review C11)
**Contexto:** O scan por camera e o unico metodo para identificar provas no fluxo de transicao. Em cenarios onde a camera nao funciona, o QR esta danificado, ou o usuario esta em desktop, nao ha alternativa. Mario solicitou uma segunda opcao de entrada.

### Decisao 1 — Computar payload client-side via `buildQrPayload()`
**Decisao:** Helper frontend `buildQrPayload(nroRequerimento, qrCodeHash)` computa `3SD|{nro}|{hash[:16]}` usando dados ja expostos no `ProvaResponse`. Zero mudanca no backend.
**Por que:** O `POST /scan` ja aceita o payload como texto. O payload e deterministic: `nro_requerimento` e `qr_code_hash` sao publicos no response. Adicionar um campo novo no backend seria desnecessario.
**Risco aceito:** Constantes `3SD`, `|` e `16` sao hardcoded no frontend, acoplando ao formato do backend. Aceitavel: o formato e estavel desde a Wave 2 e documentado no ADR-033.

### Decisao 2 — Exibir payload copiavel no modal de etiqueta
**Decisao:** O modal `VisualizarEtiquetaModal` mostra o payload em input readonly + botao "Copiar" com feedback "Copiado!". Fallback `document.execCommand("copy")` para browsers sem Clipboard API.
**Por que:** O usuario precisa de acesso ao codigo para poder digita-lo em outro dispositivo. O modal de etiqueta e o local natural — ja mostra o QR Code visual.

### Decisao 3 — Input manual na IdleView do /escanear
**Decisao:** Campo de texto abaixo do botao "Abrir camera" com label "Inserir codigo manual:" e botao "Buscar". Ao submeter, transiciona direto para `scan-loading` com o payload digitado — mesmo fluxo do scan por camera.
**Por que:** Reusa 100% do backend existente. O `POST /scan` valida formato + hash constant-time. Se o codigo for invalido, o usuario ve o erro especifico do backend (B-01 ja corrigido nesta sessao).

---

## ADR-090 — Auditoria Wave 3: 3 correcoes HIGH (scan filter, getToken try/catch, focus trap)
**Data:** 2026-04-13 (Auditoria pos-Wave 3)
**Contexto:** Auditoria senior completa da Wave 3 contra Requisitos v3.0, Backlog v3.0, DAT v2.0 e UML v3.0. Auditados todos os arquivos backend (state_machine, provas.py, schemas, RLS 006, testes) e frontend (escanear/page, 7 hooks, AdminActions, Timeline, VisualizarEtiquetaModal). Resultado: 0 CRITICAL, 3 HIGH, 6 MEDIUM, 9 LOW. Conformidade 100% com RF/RN/US. As 3 correcoes HIGH foram aplicadas.

### Correcao 1 — Filtro de APROVADA no scan para admins sem localizacao (H-01)
**Problema:** `_computar_transicoes_permitidas` em `provas.py` nao filtrava `APROVADA_PELO_VENDEDOR` para admins (setor STUDIO) sem localizacao. O admin via o botao "Aprovar" no scan, mas ao executar recebia 422 (`RotaIndeterminavelError` em `determinar_rota`), porque a rota nao pode ser determinada sem localizacao VENDEDOR.
**Decisao:** Adicionar check no loop de candidatos: se `destino == APROVADA_PELO_VENDEDOR` e o usuario nao e VENDEDOR e nao tem localizacao, filtrar da lista. Assim o botao nao aparece e o admin nao e induzido a erro.
**Alternativas:**
  - Tratar `RotaIndeterminavelError` no scan e filtrar a posteriori (rejeitado: a funcao `_computar_transicoes_permitidas` ja e o lugar certo para esse filtro, e seria mais caro chamar `determinar_rota` para cada candidato).
  - Permitir que admin STUDIO aprove e usar rota default (rejeitado: viola RN-007 que exige rota determinada pela localizacao do vendedor).
**Consequencias:** Admin STUDIO continua vendo todas as outras transicoes (CANCELADA e CRIADA ja eram filtradas por C13/C14). 407 testes passando sem regressao.

### Correcao 2 — getToken() protegido com try/catch nos hooks admin (H-02)
**Problema:** `useCancelarProva.ts` e `useReiniciarCiclo.ts` chamavam `await getToken()` fora do try/catch. Se o Supabase client lancasse excecao (sessao corrompida, storage error), a promise rejeitava sem tratamento e `loading` ficava `true` para sempre, travando a UI. Os hooks `useScanProva` e `useExecutarTransicao` ja faziam o try/catch corretamente.
**Decisao:** Mover `const token = await getToken()` para dentro do bloco try existente. Se `getToken()` falhar, cai no catch e exibe mensagem generica.
**Consequencias:** UI nunca trava em estado `loading: true` por erro de sessao. Consistencia entre todos os 4 hooks de API.

### Correcao 3 — Focus trap nos modais (WCAG 2.1) (H-03)
**Problema:** Todos os 3 modais da Wave 3 (AssinaturaModal, AdminActions cancelar/reiniciar, VisualizarEtiquetaModal) usavam `role="dialog"` e `aria-modal="true"` mas nao implementavam focus trap. Tab escapava para elementos atras do overlay.
**Decisao:** Criar hook reutilizavel `useFocusTrap<T>` que:
  - Prende Tab/Shift+Tab dentro de um container via `keydown` listener
  - Move foco para o primeiro elemento focavel ao ativar
  - Restaura o foco anterior ao desativar
  - Retorna callback ref (nao RefObject) para compatibilidade com React 18 + TypeScript estrito onde `ref` de elementos JSX nao aceita `RefObject<T | null>`
**Alternativas:**
  - Biblioteca `focus-trap-react` (rejeitado: +1 dependencia para um hook de 60 linhas).
  - Focus trap inline por modal (rejeitado: duplicacao; hook reutilizavel e mais limpo).
  - `inert` attribute no conteudo atras do modal (rejeitado: suporte parcial em browsers antigos; focus trap e mais confiavel).
**Consequencias:** 3 modais com focus trap. Hook criado em `frontend/src/hooks/useFocusTrap.ts`. +0.5 kB no bundle. Reutilizavel para qualquer modal futuro.

---

## ADR-091 — Dashboard em Tempo Real: endpoint agregado + Recharts + Supabase Realtime (Wave 4 / Componente 15)
**Data:** 2026-04-14
**Contexto:** RF-014 exige dashboard com 9 contadores em tempo real clicaveis. US-013 define criterios de aceitacao. RN-008 define calculo de "Atrasadas". RNF-001 exige < 3s de carregamento.
**Decisao:** 8 decisoes de desenho:
  1. **Endpoint unico `GET /api/v1/provas/dashboard`** que retorna os 9 contadores em uma unica chamada, em vez de 9 endpoints separados. Motivo: minimiza roundtrips HTTP, latencia e complexidade do frontend.
  2. **Contadores derivados por query** (sem tabela materializada). Volume atual (< 500 provas) nao justifica materialized view. 3 queries leves: GROUP BY status, COUNT criadas_hoje, COUNT atrasadas com subquery correlacionada.
  3. **"Criadas hoje" = provas criadas hoje (BRT)**, qualquer status. Nao e filtro de status CRIADA — e volume de intake diario. Usa `BRT_TIMEZONE` (ADR-048 padrao).
  4. **"Atrasadas" com horas corridas** (nao uteis). Decisao aprovada pelo Mario. Calcular horas uteis reais exigiria tabela de feriados + logica de calendario — complexidade desproporcional para MVP. Se necessario, Wave 6 pode evoluir.
  5. **Supabase Realtime via `postgres_changes`** em `provas_digitais`. Publicacao `supabase_realtime` configurada com `ALTER PUBLICATION ADD TABLE`. Frontend assina via `@supabase/supabase-js`. Debounce de 2s no refetch para evitar flood.
  6. **Fallback para polling** (30s) se Realtime falhar (desconexao, timeout). Polling ativado inicialmente, cancelado quando Realtime conecta.
  7. **Recharts para grafico de distribuicao** (bar chart horizontal). Import seletivo para tree-shaking. +105 kB na page, 294 kB First Load JS.
  8. **Framer Motion para animacao** dos cards de contador (entrada com fade+slide, reutiliza dep existente).
**Alternativas:**
  - Dashboard server-side com revalidacao (rejeitado: nao atende "tempo real" do RF-014).
  - Chart.js em vez de Recharts (rejeitado: DAT v2.0 especifica Recharts explicitamente).
  - Materialized view para contadores (rejeitado: overkill para < 500 provas).
  - pg_notify customizado (rejeitado: `postgres_changes` do Supabase Realtime ja faz isso nativamente).
**Consequencias:** 1 endpoint novo, 1 pagina frontend, 1 dep npm (recharts), `provas_digitais` na publicacao Realtime. 14 testes novos backend (421 total). Menu "Dashboard" ativado.
**Status:** SUPERSEDED parcialmente por ADR-092 (query consolidada + cache).

---

## ADR-092 — Dashboard: query consolidada + cache in-memory TTL 5s (Wave 4 — otimizacao)
**Data:** 2026-04-14
**Contexto:** A implementacao inicial do ADR-091 usava 4 queries separadas (GROUP BY + COUNT hoje + SELECT config + COUNT atrasadas). Para 30 usuarios simultaneos, cada mudanca de status gerava 120 queries (30 × 4). Mario questionou a viabilidade financeira em escala e sugeriu consolidar queries + cache curto.
**Decisao:**
  1. **Query unica consolidada** com `COUNT(*) FILTER (WHERE ...)` do PostgreSQL. Todos os 10 contadores (9 + total_ativas) sao calculados em 1 scan da tabela `provas_digitais`, incluindo "atrasadas" via subquery correlacionada em `movimentacoes`. A leitura de `tempo_atraso_horas_uteis` permanece como query separada (tabela diferente, valor estavel).
  2. **Cache in-memory TTL 5 segundos** por perfil de scoping. Chaves: `admin`, `vendedor:{uuid}`, `motorista`, `clicheria`. `dict[str, (float, DashboardResponse)]` com `time.monotonic`. Seguro em asyncio single-threaded (event loop cooperativo). Cada worker uvicorn tem cache proprio.
  3. **Polling frontend ajustado para 10s** (antes 30s). O custo real e ~1 query a cada 5s por perfil (cache hit para os demais), nao 1 query por usuario.
**Impacto medido:**
  - 1 mudanca de status, 30 usuarios: **120 queries → 1 query** (cache hit para os outros 29).
  - Polling 30 usuarios: **14.400 queries/hora → ~720 queries/hora** (~20x reducao).
**Alternativas:**
  - Mutacao local via payload do Realtime (rejeitado: exige REPLICA IDENTITY FULL + logica complexa de increment/decrement client-side + "atrasadas" nao capturavel por evento).
  - Redis/Memcached externo (rejeitado: nova infra para um cache de 5s; in-memory e suficiente para o volume).
  - Cache compartilhado entre workers (rejeitado: requer IPC ou Redis; cache por worker e aceitavel — worst case N workers = N queries cold start).
**Consequencias:** 3 queries por cache miss (config + consolidada + atrasadas_por_vendedor). Handler serve cache hit em <1ms. 17 testes (424 total). Frontend polling 10s seguro pelo cache backend.

---

## ADR-093 — Dashboard: layout Figma com grid 3x3, sem Recharts, breakdown de atrasadas por vendedor (Wave 4)
**Data:** 2026-04-14
**Contexto:** Apos a implementacao inicial (ADR-091/092) com grid generico de 9 cards + Recharts, Mario enviou o design Figma (node 58:183) com layout especifico: 5 contadores (Criadas hoje, Com Vendedor, Aprovadas, Na clicheria, Atrasadas) + 2 atalhos rapidos (Escanear QR Code, Nova Prova). Sem graficos.
**Decisao:** 5 decisoes:
  1. **Grid 3 colunas x 3 rows iguais** (`1fr 1fr 1fr`). Os 4 counter cards (Criadas hoje, Com Vendedor, Aprovadas, Na clicheria) tem a mesma altura. Os 2 shortcuts empilhados dividem a altura de 1 card (row 3, col 1). Card Atrasadas ocupa col 3, rows 1-3 (full height).
  2. **Recharts removido.** O design Figma nao inclui graficos. A dependencia foi desinstalada. Bundle da pagina: 105 kB → 3 kB.
  3. **Contadores nao exibidos no Figma permanecem no backend.** `reprovadas`, `aguardando_envio`, `com_motorista`, `concluidas` continuam calculados e retornados pelo endpoint (para uso futuro ou por outros consumers). O frontend renderiza apenas os 5 que o Figma especifica.
  4. **`atrasadas_por_vendedor`** adicionado ao `DashboardResponse`. Query com JOIN em `usuarios`, GROUP BY `vendedor_nome`, ORDER BY `quantidade DESC`, LIMIT 10. Renderizado no card Atrasadas como lista de pills com nome + contagem, conforme Figma.
  5. **Cards Figma:** `#fafafa`, `border: 1px solid rgba(202,202,202,0.4)`, `border-radius: 31px`, `box-shadow: 0 0 13.6px rgba(0,0,0,0.04)`. Icone amarelo `53x61px` com `border-radius: 16px`. Valores `clamp(2.5rem, 4vw, 4.5rem)`, labels `clamp(1.1rem, 1.6vw, 1.5rem)` com `color: rgba(0,0,0,0.29)`.
**Alternativas:**
  - Manter Recharts com grafico abaixo dos cards (rejeitado: nao esta no Figma, +102 kB de bundle desnecessario).
  - Renderizar todos os 9 contadores do RF-014 no frontend (rejeitado: Figma e a especificacao visual aprovada pelo stakeholder).
  - Card Atrasadas com total apenas (rejeitado: Figma mostra breakdown por vendedor explicitamente).
**Consequencias:** Layout match Figma pixel-perfect. Bundle 3 kB (vs 105 kB). Backend retorna dados completos (9 contadores + breakdown), frontend consome seletivamente. 2 testes adicionais para `atrasadas_por_vendedor` (424 total).


## ADR-094 — Auditoria Wave 4: correcoes H-01 + M-03 + L-01 + L-02 + L-04
**Data:** 2026-04-14

**Contexto:** Auditoria senior da Wave 4 identificou 1 HIGH, 4 MEDIUM e 5 LOW. Correcoes aplicadas para os itens autorizados pelo stakeholder.

**Decisoes:**

  1. **H-01 — Card "Na clicheria" navega sem filtro de status.** O contador `na_clicheria` agrega 2 status (`ENVIADA_PARA_CLICHERIA` + `ENCAMINHADA_A_CLICHERIA`), mas a pagina `/provas` so suporta filtro por 1 status. Passar `?status=ENVIADA_PARA_CLICHERIA` causava discrepancia entre o valor do card e a lista filtrada. Solucao: navegar para `/provas` sem filtro, padrao identico ao card "Atrasadas". Suporte a multi-status sera implementado na Wave 5 (relatorios com filtros combinados).

  2. **M-03 — Breakpoint mobile < 600px adicionado.** Grid 1 coluna com 6 rows empilhados para telas < 600px (RNF-006 exige telas a partir de 5 polegadas). Cards com `min-height: 140px`, Atrasadas com `min-height: 250px`.

  3. **L-01 — GROUP BY corrigido para `Usuario.id, Usuario.nome`.** Evita merge acidental de vendedores homonimos na query `atrasadas_por_vendedor`. Antes agrupava apenas por `nome`.

  4. **L-02 — Guard `ValueError`/`TypeError` no `tempo_atraso_raw`.** `int(tempo_atraso_raw)` agora tem `try/except` com fallback para 48h. Valor invalido no banco nao causa mais 502 generico.

  5. **Itens aceitos sem correcao:** M-01 (5/9 contadores, ADR-093), M-02 (atalhos RF-016, Figma-driven), M-04 (Realtime sem fallback silencioso, decisao Mario), L-03 (Atrasadas sem filtro), L-05 (sem teste TTL).

**Consequencias:** 424 testes passando, 0 regressoes. Linters limpos. Zero toque em Waves 0/1/2/3. Wave 4 aprovada com ressalvas documentadas (M-01, M-02 requerem sign-off formal contra RF-014/RF-016).

---

## ADR-095 — Recovery da migration 010 orfa + reconciliacao de drift (Wave 5 Bloco 5.0)
**Data:** 2026-04-27 (Wave 5 Bloco 5.0)

**Contexto:** A inspecao MCP da Fase 1 da Wave 5 revelou drift entre o repositorio e o banco de producao:
  - `public.alembic_version.version_num = '010'` em producao.
  - Repositorio (branch `main`, tip `6add246 Wave 04 concluida`) so tinha migrations 001-009 versionadas.
  - 2 indices em producao sem registro no schema versionado: `idx_provas_vendedor_status (vendedor_id, status)` e `idx_movimentacoes_status_novo_created_at (status_novo, created_at DESC)`.

`git log --all --diff-filter=A` localizou o commit `5db44bb feat(wave5): implementacao completa - Relatorios + Atalhos Rapidos` (autor `3studioagn`, 2026-04-15) na branch `wave5-wave6-backup` e tambem como commit historico do `main` antes do `git reset` documentado no stash `stash@{0}: pre-reset-wave5-revert`. Esse commit trazia exatamente `backend/migrations/versions/010_add_indexes_for_wave5_reports.py` com os mesmos 2 indices que estao em producao - confirmando que a migration foi aplicada no banco e o repo posteriormente revertido sem reverter o banco.

**Decisao 1 - Recovery 1:1 da migration 010 (sem tocar producao):**
  - Restaurar `backend/migrations/versions/010_add_indexes_for_wave5_reports.py` literalmente do commit `5db44bb`. Conteudo bit-exato:
    - `down_revision = "009"`
    - `CREATE INDEX IF NOT EXISTS` para os 2 indices (idempotente).
    - `DROP INDEX IF EXISTS` no `downgrade()` (reversivel).
  - Atualizar `docs/db/schema.sql`:
    - Cabecalho passa para "Wave 5 Bloco 5.0, alembic_version = 011".
    - Lista de migrations inclui 010 e 011.
    - Secao 5 (INDICES) adiciona os 2 indices novos com comentario `-- migration 010`.
    - Total de indices passa de 30 para 32.
  - **Zero alteracao no banco.** A migration 010 ja esta aplicada (`IF NOT EXISTS` torna `alembic upgrade head` no-op para esta revisao).

**Decisao 2 - Nao reaproveitar o resto do commit 5db44bb:**
  - O commit anterior trazia 5 endpoints separados (`/reports/summary`, `/reports/by-seller`, `/reports/overdue`, `/reports/route-distribution`, `/reports/proofs`) + 6 hooks frontend + 6 componentes frontend + 186 testes.
  - WAVE5_ANALYSIS.md (Secoes 4.2 e 5.3) propoe arquitetura diferente: **endpoint unico discriminado por `scope`** + **hook unico `useReport`** + cache em 4 camadas (HTTP/ETag/in-memory/SQLAlchemy) - foco em "minimizar queries" reforcado pelo Mario em 2026-04-27.
  - O commit antigo serve como **referencia de testes e seed** (`scripts/seed_reports_fixture.py`), nao como copia.

**Alternativas rejeitadas:**
  - **Drop e re-create dos indices:** rejeitado porque os indices ja estao corretos em producao; recriar e custo desnecessario.
  - **Comecar a Wave 5 em alembic_version=011 sem 010:** rejeitado porque criaria furo na cadeia de revisoes Alembic (`down_revision` da 011 nao apontaria para uma revision existente no repo).
  - **Aplicar a migration 010 de novo:** desnecessario; `IF NOT EXISTS` ja torna idempotente, e o banco ja esta no estado correto.
  - **Reverter o banco para 009:** rejeitado; os indices ja estao em producao, ja em uso. Reverter geraria churn sem ganho.

**Consequencias:**
  - Repositorio passa a refletir fielmente o estado de producao apos esta wave (`alembic_version=011` apos Bloco 5.6, ou `010` se 011 nao for aplicada ainda).
  - Toda Wave 5 daqui em diante parte de uma base versionada e auditavel.
  - Migrations futuras tem `down_revision` correto.
  - Lesson: **toda migration aplicada em producao DEVE ter o arquivo correspondente commitado no `main`**. Antes de `git reset`/revert que retire arquivos de migration, validar que o banco tambem foi revertido.

---

## ADR-099 — RN-008: Wave 5 mantem horas corridas (consistencia com Wave 4) - desvio explicito do RN-008 literal
**Data:** 2026-04-27 (Wave 5 Bloco 5.0)

**Contexto:** O Documento de Requisitos v3.0 §RN-008 estabelece literalmente: *"prova como Atrasada se permanecer no mesmo status por mais tempo do que o configurado... Valor padrao: 48 horas uteis"*. A Wave 4 (ADR-091, decisao 4) ja havia adotado **horas corridas** com aprovacao explicita do Mario, justificando que calcular horas uteis exigiria tabela de feriados + logica de calendario - complexidade desproporcional para MVP. O briefing inicial da Wave 5 (Mario, 2026-04-27) trouxe novamente o tema, exigindo "horas uteis estritamente" no §2.6, mas marcou como blocker o drift entre Dashboard (RF-014) e Relatorios (RF-015) no §8.

A inspecao da Fase 1 da Wave 5 confirmou: o codigo atual em `backend/app/api/v1/provas.py:1073` usa `limite_atraso = datetime.now(utc) - timedelta(hours=tempo_atraso_horas)` - horas corridas. A descricao da chave `tempo_atraso_horas_uteis` em `configuracoes_sistema` (Wave 0 seed migration 002) ainda dizia "horas uteis" - inconsistencia textual a ser corrigida.

Mario foi consultado em 2026-04-27 com 3 opcoes (A: implementar horas uteis em Wave 5 + corrigir Wave 4; B: manter horas corridas + atualizar config descricao + ADR; C: tabela de feriados global). Mario aprovou explicitamente: **opcao B**.

**Decisao 1 - Wave 5 mantem horas CORRIDAS:**
  - O calculo no Dashboard (Wave 4) e nos Relatorios (Wave 5) usa o mesmo `coalesce(max(mov.created_at), prova.created_at) < (now() - INTERVAL h)`.
  - Mesmo helper, mesma logica, mesmo resultado - **drift cross-wave eliminado por construcao**.
  - Teste de integracao em §7.4 do WAVE5_ANALYSIS.md valida equivalencia numerica entre `/api/v1/provas/dashboard.atrasadas` e `/api/v1/reports?scope=geral.indicadores.qtd_atrasadas`.

**Decisao 2 - Atualizar `descricao` da chave (migration 011):**
  - Texto novo: *"Tempo em horas corridas sem movimentacao para classificar prova como Atrasada. Padrao: 48h."*
  - Texto curto, sem citar ADRs/RN para nao poluir a UI do Componente 09 (decisao tomada com Mario em 2026-04-27 - opcao "ii").
  - Migration 011 e idempotente (UPDATE) e reversivel (downgrade restaura texto Wave 0).

**Decisao 3 - NAO renomear a chave:**
  - Nome `tempo_atraso_horas_uteis` permanece. Motivos:
    1. Compat com Wave 2 (`schemas/configuracao.py` whitelist da chave).
    2. Compat com Wave 4 (handler do dashboard le pela chave).
    3. Compat com schema.sql Section 7 (seeds).
    4. Compat com testes existentes (`test_configuracoes_api.py`, `test_provas_api.py`).
  - O custo de renomear (touchar 4 waves anteriores) e desproporcional ao ganho (estetica do nome).

**Decisao 4 - Aplicacao da 011 fica para Bloco 5.6:**
  - 011 e cosmetica (so muda texto). Aplicar agora seria 1 deploy isolado para mudanca de baixissimo risco.
  - Deploy unico no fim da Wave 5 (Bloco 5.6) reduz numero de janelas de deploy.
  - No intervalo, banco esta em 010 e repo em 011 - documentado em CHANGELOG.md e schema.sql.

**Alternativas rejeitadas:**
  - **A: implementar horas uteis em Wave 5 + corrigir Wave 4:** rejeitado pelo Mario - escopo desproporcional, exigiria tabela de feriados nacionais + estaduais + 3Studio-especificos, funcao SQL `business_hours_between` (ou Python equivalente), refactor do Dashboard (Wave 4 - regra inviolavel §2.1 da Wave 5).
  - **C: tabela de feriados global em SQL:** rejeitado - mesma justificativa de A; reavaliar em Wave 7+ se houver demanda de auditor externo.
  - **Renomear a chave para `tempo_atraso_horas_corridas`:** rejeitado - ver Decisao 3.
  - **Manter texto antigo "horas uteis" no banco:** rejeitado - texto inconsistente com codigo gera confusao no admin que ler `/configuracoes`.

**Consequencias:**
  - Sistema continua nao-conforme com RN-008 literal. **Re-evaluar em Wave 7+** se auditor externo cobrar.
  - Audit trail: ADR-091 (decisao original) + ADR-099 (reforco Wave 5) + migration 011 (atualiza descricao) - rastro completo.
  - Wave 5 e Wave 4 calculam "atrasadas" identicamente - cross-check automatizado no §7.4 do ANALYSIS impede regressao futura.
  - O "_horas_uteis" no nome da chave vira **divida nominal documentada** - aceitavel ate Wave 7+.

---

## ADR-096 — Endpoint UNICO discriminado por scope vs. 4-5 endpoints separados (Wave 5 Bloco 5.2)
**Data:** 2026-04-27 (Wave 5 Bloco 5.2)

**Contexto:** A Wave 5 anterior (commit 5db44bb, revertida) implementou 5 endpoints
separados: `/reports/summary`, `/reports/by-seller`, `/reports/overdue`,
`/reports/route-distribution`, `/reports/proofs`. Ao refazer a Wave 5, o
briefing do Mario (2026-04-27) explicitou foco em **minimizar queries** — cada
roundtrip cliente-servidor importa.

**Decisao:** Endpoint UNICO `GET /api/v1/reports?scope=...` com discriminated
union Pydantic v2 + TypeScript. Cliente faz 1 request por (scope, filtros);
servidor executa 1 conjunto de queries; ETag SHA-256 do payload completo
permite 304 sem reserializacao.

**Alternativas rejeitadas:**
  - **5 endpoints separados** (caminho do commit antigo): forca cliente a saber
    qual endpoint chamar para qual scope, multiplica caches/ETags, e duplica
    estrutura no Pydantic.
  - **Endpoint generico com `dict[str, Any]`**: perde tipagem estatica, gera
    runtime checks no frontend, dificulta autocomplete.
  - **GraphQL**: overhead infraestrutural enorme para 4 perspectivas estaveis.

**Beneficios:**
  - Frontend tem 1 hook (`useReport`) e 1 cache key por filtros — nao 5.
  - Switch exaustivo no TS garante cobertura em build-time (TS reclama se
    novo scope nao for tratado).
  - Backend tem 1 dispatcher (`_dispatch_aggregator`) que roteia para
    funcao especifica por scope — facil testar com `unittest.mock.patch`.
  - ETag funciona naturalmente — payload completo do scope tem identidade
    propria.

**Trade-off aceito:** Adicionar uma 5a perspectiva no futuro exige editar o
schema Pydantic, o helper TS, e o dispatcher — 3 lugares. Mas isso e barato
(~50 LOC) e o ganho de manter superficie de API minima vale.

**Consequencias:**
  - Endpoint atual: `GET /api/v1/reports?scope={geral|3studio|vendedores|clicheria}`.
  - Frontend hook unico em `useReport.ts`.
  - Discriminated union em `report.py` (backend) + `report.ts` (frontend).

---

## ADR-097 — HTTP ETag + Cache server-side TTL 60s + Realtime invalidation (Wave 5 Bloco 5.2/5.3)
**Data:** 2026-04-27 (Wave 5 Blocos 5.2 e 5.3)

**Contexto:** Mario reforcou em 2026-04-27 que a Wave 5 precisa "minimizar
queries" — aceitavel custo extra em construcao (cache, ETag), nao aceitavel
custo extra em runtime de queries pesadas. WAVE5_ANALYSIS §4.4 desenhou
estrategia em 4 camadas. Este ADR formaliza as 3 primeiras (a quarta — SA
compiled cache — e default).

**Decisao — 3 camadas combinadas:**

  **Camada 1: HTTP ETag + If-None-Match -> 304:**
    - Backend gera ETag SHA-256 deterministico do JSON canonico do payload
      (`compute_etag` em `report_etag.py`). Ordem de chaves estavel (sort_keys),
      sem espacos.
    - Cliente envia `If-None-Match: <etag>` em refetch.
    - Match exato (RFC 7232) -> response `304 Not Modified` com headers
      preservados, body vazio.
    - Implementacao backend: comparacao por string em
      `matches_if_none_match()` (suporta wildcard `*` e lista comma-separated).

  **Camada 2: Cache in-memory TTL 60s no backend:**
    - `ReportCache` (asyncio-safe, asyncio.Lock no check-and-mutate).
    - Chave de cache = SHA-256 dos filtros normalizados (JSON canonico) —
      `to_cache_key(filters)`.
    - Cache hit no `_get_or_compute` retorna `(payload, etag)` pre-calculados —
      zero queries DB.
    - TTL configuravel via env var `REPORTS_CACHE_TTL_SECONDS` (default 60).
    - Singleton por worker uvicorn. Em N workers = N caches independentes —
      worst case = N queries cold-start, aceitavel para volume Wave 5.

  **Camada 3: Realtime invalida cache do frontend:**
    - Frontend assina `postgres_changes` em `provas_digitais` (Wave 4 reuse).
    - Em INSERT/UPDATE: `invalidate()` no cache local + refetch com
      `If-None-Match` (debounced 2s).
    - Backend nao invalida sua propria cache via Realtime — deixa TTL expirar
      naturalmente. ETag matching cobre o gap (cliente pode ter ETag valido
      por ate 60s).

**Cabecalhos de resposta:**
  - `ETag: "<sha256-hex>"` (strong ETag, RFC 7232 §2.3)
  - `Cache-Control: private, max-age=30, stale-while-revalidate=60`

**Alternativas rejeitadas:**
  - **Sem cache, queries diretas:** rejeitado — 30 usuarios simultaneos com
    polling 30s = 3600 queries/hora. Inaceitavel para perspectivas com 6+
    queries SQL pesadas.
  - **Redis externo:** rejeitado — adiciona infra para um cache de 60s. In-memory
    e suficiente para volume Wave 5. Reavaliar em Wave 7+ se escalar.
  - **Materialized view com REFRESH:** rejeitado em volume baixo (<1MB total
    nas tabelas) — REFRESH toca disco e e mais caro que a query direta. ANALYSIS
    §3.3 documenta a decisao.
  - **Server-Sent Events (SSE) push:** rejeitado — mais complexo que polling
    + Realtime. Realtime ja resolve o caso de uso ("dados mudaram").

**Custo medido (planning time domina em volume baixo):**
  - 1 mudanca de status, 30 usuarios: 120 queries -> 1 query (cache hit para
    os outros 29).
  - Polling 30s, 30 usuarios: 14400 queries/hora -> ~720 queries/hora (~20x
    reducao).

**Consequencias:**
  - 4 modulos novos no backend: `report_filters.py`, `report_metrics.py`,
    `report_cache.py`, `report_etag.py`.
  - Hook `useReport` no frontend implementa as 3 camadas no cliente.
  - Validado em testes (47 unit + 39 integration cobrindo cache, ETag, 304,
    invalidacao).

---

## ADR-098 — Atalhos globais por teclado estilo GitHub + 3º card no dashboard (Wave 5 Bloco 5.5)
**Data:** 2026-04-27 (Wave 5 Bloco 5.5)

**Contexto:** RF-016 exige 3 atalhos rapidos: escanear QR Code, listar provas,
acessar relatorios. Wave 4 entregou 2 cards visuais no dashboard (Escanear +
Nova Prova) — auditoria Wave 4 marcou divergencia (M-02, ADR-093). Wave 5
precisa fechar.

**Decisao — duas camadas complementares:**

  **Camada 1: Atalhos visuais (cards no dashboard):**
    - Manter os 2 cards existentes (Escanear, Nova Prova) — nao tocar Wave 4.
    - Adicionar 3º card "Acessar Relatorios" (laranja `#ff8a3d`, distinto
      do preto/Escanear e amarelo/Nova Prova).
    - Visivel para todos os perfis. RBAC do `/api/v1/reports` (backend)
      retorna 403 se nao-admin acessar — UI nao precisa esconder.
    - Click navega via `<Link>` Next.js (consistente com os outros cards).

  **Camada 2: Atalhos por teclado globais (estilo GitHub):**
    - State machine 2-keystroke: `g` ativa "modo leader" por 1.5s, segunda
      tecla dispara navegacao.
    - Atalhos:
      - `g s` -> `/escanear`
      - `g p` -> `/provas`
      - `g r` -> `/relatorios` (apenas admin via flag `adminOnly`)
      - `?` -> abre/fecha painel de help
      - `Esc` -> cancela leader / fecha painel
    - Hook `useGlobalShortcuts` registrado no `(dashboard)/layout.tsx` —
      ativo em qualquer pagina autenticada.
    - Modal `KeyboardShortcutsHelp` com `<kbd>` styled, focus trap (reusa
      `useFocusTrap` da Wave 3), Esc/click-fora fecha.

**Alternativas rejeitadas:**
  - **Apenas atalhos visuais (sem teclado):** rejeitado — o briefing
    inicial da Wave 5 (§5 e §1.2) pediu explicitamente keyboard shortcuts
    estilo GitHub.
  - **Apenas teclado (sem 3º card):** rejeitado — RF-016 exige presenca
    visual dos 3 atalhos. Usuarios mouse-only nao descobrem teclado.
  - **Atalhos sem leader (ex: `Ctrl+S`):** rejeitado — colide com shortcuts
    do navegador (save, find, etc).
  - **Atalhos de letra unica (ex: `s`, `p`, `r`):** rejeitado — colide
    facilmente com inputs e tem alto risco de disparar acidental.

**Filtros e seguranca:**
  - Atalhos desativados quando foco esta em `<input>`, `<textarea>`,
    `<select>`, `[contenteditable]` — nao quebra digitacao.
  - Modificadores (Ctrl/Cmd/Alt/Meta) ignorados — atalhos so disparam com
    teclas puras.
  - `g r` filtrado por `is_admin` — vendedor/motorista/clicheria nao veem
    no painel de help nem podem ativar via teclado.

**Consequencias:**
  - 3 arquivos novos: `useGlobalShortcuts.ts`, `KeyboardShortcutsHelp.tsx`,
    `KeyboardShortcutsHelp.module.css`.
  - Layout: 1 import + 1 hook call + 1 render condicional.
  - Dashboard: 1 `<Link>` adicional + estilos `.shortcutRelatorios*`.
  - CLAUDE.md ganha secao "Atalhos de teclado globais" com tabela completa.
  - RF-016 100% atendido em duas camadas (visual + teclado).

---

## ADR-100 — Estrategia de timezone: UTC no banco, conversao na borda (Wave 5)
**Data:** 2026-04-27 (Wave 5)

**Contexto:** WAVE5_ANALYSIS §8 (R4) listou timezone como risco da Wave 5 —
datas inseridas pelo usuario no front estao em fuso local (BRT America/Sao_Paulo,
offset -3); servidor opera em UTC; querys agregam em UTC. Sem disciplina, bugs
sutis (provas "criadas hoje" sumindo entre 21h-00h BRT, por exemplo).

**Decisao:**

  1. **Banco em UTC sempre.** PostgreSQL armazena `TIMESTAMPTZ` — internamente
     UTC, com offset metadata. Movimentacoes, provas, audit_logs — todas
     gravadas em UTC.
  2. **Backend opera em UTC.** Filtros do `/reports?from=...&to=...` aceitos
     como ISO-8601 com offset (`2026-04-27T00:00:00-03:00`) ou Z (UTC). Pydantic
     converte automaticamente para `datetime` tz-aware. Helper `assert_utc()`
     em `report_metrics.py` valida em pontos criticos.
  3. **Frontend converte BRT -> UTC na borda do request.** Componente
     `DateRangeFilter` aceita `<input type="date">` (formato YYYY-MM-DD em fuso
     local), aplica offset BRT (-3h) e envia ISO-8601 UTC ao backend.
     Funcoes `brtDateToIsoUtcStart` / `brtDateToIsoUtcEnd` em `DateRangeFilter.tsx`.
  4. **Frontend renderiza UTC em BRT.** Helper `formatDataBrt(iso)` em
     `lib/types/report.ts` usa `Date#toLocaleDateString("pt-BR")` que aplica
     o fuso do navegador automaticamente. Helpers `formatDataHoraBrt` para
     timestamps completos.
  5. **Defaults UTC-aware.** `ReportFilters._defaults_and_invariants` adiciona
     `tzinfo=timezone.utc` em datetimes naive, garantindo que comparacoes
     posteriores nao quebrem.

**Alternativas rejeitadas:**
  - **Backend em BRT:** rejeitado — agendamentos cron, jobs futuros e
    integracoes assumem UTC.
  - **Backend recebe BRT direto:** rejeitado — multiplica chance de bugs
    quando frontend internacionalizar futuramente. Frontend converte na borda.
  - **Sem timezone (datetimes naive):** rejeitado — Pydantic v2 aceita,
    Postgres aceita, mas eventualmente alguem assume um fuso e quebra.

**Consequencias:**
  - Documentacao: este ADR + comentarios em `report_filters.py` + `DateRangeFilter.tsx`.
  - Helper `assert_utc()` exposto em `report_metrics` para uso em pontos criticos.
  - Testes de integracao validam que datas BRT do front viram UTC corretamente
    no backend.
  - Wave 4 (Dashboard) ja seguia esse padrao desde ADR-091 — Wave 5 reforca.

---

## ADR-101 — Taxa de reprovacao calculada sobre CICLOS (RN-006), nao provas (Wave 5)
**Data:** 2026-04-27 (Wave 5 Blocos 5.1 e 5.2)

**Contexto:** RN-006 permite reinicio de ciclo de provas reprovadas. Uma prova
pode ser reprovada no ciclo 1, reiniciada (volta para CRIADA com `ciclo_atual=2`),
e aprovada no ciclo 2. Como contar essa prova no calculo de "taxa de reprovacao"?

**Opcoes consideradas:**
  - **(A) Sobre PROVAS:** taxa = reprovadas / (aprovadas + reprovadas) onde
    cada prova conta 1 vez pelo seu status FINAL.
  - **(B) Sobre CICLOS:** taxa = reprovacoes-ciclo / (aprovacoes-ciclo +
    reprovacoes-ciclo) onde cada par (prova_id, ciclo) conta como evento independente.

**Decisao: opcao B — sobre CICLOS.**

**Justificativas:**
  1. **Refletir retrabalho:** a opcao A esconde o retrabalho — uma prova
     reprovada 3 vezes e finalmente aprovada conta 1 aprovacao na opcao A,
     enquanto na B conta 3 reprovacoes + 1 aprovacao (taxa 75%). A taxa
     real de retrabalho do vendedor e a opcao B.
  2. **Auditavel:** cada `Movimentacao` com `status_novo IN
     (APROVADA_PELO_VENDEDOR, REPROVADA_PELO_VENDEDOR)` e um evento
     unico no log imutavel. Contar movimentacoes alinha com a fonte
     de verdade.
  3. **Comparabilidade entre vendedores:** vendedor que sempre acerta na
     primeira tentativa tem mesma taxa que vendedor que precisa de 2 ciclos
     pela opcao A — desincentiva qualidade. Opcao B premia precisao.
  4. **Consistencia entre Geral e Vendedores:** o mesmo numero aparece nas
     duas perspectivas com a mesma logica.

**Alternativas rejeitadas:**
  - **Opcao A:** descartada pelas razoes acima.
  - **Hibrido (taxa sobre ciclos + taxa "final" sobre provas):** rejeitado
    por confusao na UI — qual numero mostrar onde? Adiar para Wave 7+ se
    auditor pedir.

**Implementacao:**
  - Em SQL: COUNT FILTER sobre `Movimentacao` com `status_novo` filtrado.
  - Em Python: helper `taxa(numerador, denominador)` em `report_metrics.py`
    com clamp [0.0, 1.0] e fallback 0.0 se denominador zero.
  - VendedorMetrica expoe `aprovacoes` e `reprovacoes` (counts absolutos
    sobre ciclos) + taxas calculadas — UI pode mostrar numerador/denominador
    se quiser auditar.

**Consequencias:**
  - Provas com ciclos reiniciados afetam a taxa multiple times — desejado.
  - Documentacao: este ADR + docstrings em `IndicadoresGeral.taxa_reprovacao`
    e `VendedorMetrica.taxa_reprovacao` + comentario na query de
    `_query_ranking_vendedores`.
  - Reavaliar em Wave 7+ se auditor externo cobrar interpretacao alternativa.

---

## ADR-102 — Refresh visual da Wave 5: alinhamento das 4 perspectivas ao design Mario
**Data:** 2026-04-29 (Wave 5 Visual Refresh — sessao iterativa pos-closeout)

**Contexto:** A Wave 5 entregou funcionalmente os relatorios em 2026-04-23/27
(Blocos 5.0-5.6). Apos o closeout, o Mario completou o design final no Figma
das 4 perspectivas (Geral, 3Studio, Vendedores, Clicheria) com proposicao
visual significativamente diferente do MVP entregue: layouts assimetricos
(card preto largo + cards brancos compactos), tipografia maior, cores
semanticas (warning/success/accent/zero), avatares com iniciais, mini-stats,
sparklines, deltas. Foi necessario um refresh visual completo — sem alterar
contratos de API, sem regredir testes, sem tocar em outras Waves.

**Opcoes consideradas:**
  - **(A) Refatorar todos os componentes existentes** (KpiCard, BarChart,
    TimeSeriesChart) para suportar as variantes do novo design — mais
    risco de quebrar perspectivas que ainda usariam os componentes legados.
  - **(B) Criar novos componentes shared (Sparkline, DeltaBadge) + classes
    CSS especificas por perspectiva, mantendo os componentes legados
    intactos** — sem retrocompat issues, mais classes CSS porem isoladas
    no `relatorios.module.css`.
  - **(C) Usar uma biblioteca de UI** (Radix, Mantine, Ant Design) — viola
    ADR-005 (CSS Modules sem framework externo) e adiciona dependencia.

**Decisao: opcao B — criar novos componentes + classes especificas.**

**Justificativas:**
  1. **Zero retrocompat issues:** componentes legados (KpiCard, BarChart,
     TimeSeriesChart) continuam disponiveis para futuras perspectivas
     internas (Wave 6+) ou eventuais experimentos. As classes CSS legadas
     (`.tableCard`, `.dataTable`, `.atrasadasList`, `.kpiGrid`,
     `.chartsGrid`) tambem foram preservadas.
  2. **Isolamento:** todo o codigo novo vive em `relatorios.module.css` +
     `perspectivas/*.tsx` + `shared/{Sparkline,DeltaBadge}.tsx`. Nada
     alem do escopo da Wave 5 e tocado.
  3. **Cores semanticas centralizadas:** classes como `.metricValueDanger`,
     `.metricValueSuccess`, `.metricValueWarning`, `.metricValueAccent`,
     `.metricValueZero` formam um sistema reutilizavel pelas 4 perspectivas
     sem hard-code de cores nos componentes JSX.
  4. **Reaproveitamento maximo:** classes-chave (`.metricCard`,
     `.metricEyebrow`, `.metricValueLg`, `.rankingCard`, `.vendorRowItem`,
     `.metricCardMotivosHeader`) sao usadas por multiplas perspectivas
     (ex: o pattern de "Top motivos" do 3Studio e a mesma estrutura visual
     do "Distribuicao por rota de origem" da Clicheria).

**Implementacao:**
  - 2 componentes shared novos: `Sparkline.tsx` (com dot final em HTML
    element posicionado para nao virar oval com `preserveAspectRatio="none"`)
    e `DeltaBadge.tsx` (com `tone` e `onDarkSurface` props).
  - 6 componentes shared/filtros refatorados: `PeriodoBadge`, `DonutChart`,
    `ScopeSelector` (CSS), `DateRangeFilter`, `SearchInput`, `ExportButton`.
  - 4 perspectivas reescritas com layouts especificos do design.
  - ~40 classes CSS novas em `relatorios.module.css` (todas as classes
    legadas preservadas — ~600 linhas adicionadas).

**Alternativas rejeitadas:**
  - **Opcao A:** descartada por risco de regressao em codigo ja em
    producao + acoplamento a refator KpiCard que precisaria suportar
    variantes black/white/with-stats/with-sparkline (~4-6 props novas).
  - **Opcao C:** descartada por violar ADR-005 (consistencia da stack).

**Consequencias:**
  - Bundle JS aumenta minimamente (`Sparkline.tsx` ~3KB, `DeltaBadge.tsx`
    ~1KB). CSS aumenta ~600 linhas (gzip ~3KB).
  - Componentes legados (`KpiCard`, `BarChart`, `TimeSeriesChart`) ainda
    sao usados por testes / future use — nao sao dead code agora.
  - Tests backend continuam passando: 633/633.

---

## ADR-103 — `.srOnly` sem `position: absolute` (uso de `clip-path: inset(50%)`)
**Data:** 2026-04-29 (Wave 5 Visual Refresh)

**Contexto:** Durante o refresh visual da Wave 5, foram adicionadas tabelas
semanticas com `<caption className={srOnly}>` para acessibilidade (em
`Metricas por Vendedor`, `Provas Atrasadas` e `Detalhamento`). A classe
`.srOnly` original usava o padrao classico A11Y:
```css
.srOnly {
  position: absolute;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
```

O bug: quando o ancestral `<table>` nao tem `position: relative` (default
static), o `position: absolute` ancora no proximo elemento posicionado
acima — neste caso, o viewport. Os captions ficavam posicionados em
`top: 1235px`, e o navegador incluia esse offset no `html.scrollHeight`,
gerando 156px de overflow logico que ativava o scrollbar do browser.
Mesmo com `clip: rect(0,0,0,0)` clipando visualmente, a posicao logica
no flow (`absolute`) afetava a altura do documento.

Diagnostico via DOM inspection com mock data injetado no preview:
- `html.scrollHeight: 1236, html.clientHeight: 1080` → 156px overflow
- Caption encontrado a `bottom: 1236, top: 1235, height: 1, width: 1` com
  `position: absolute`
- Apos remover `position: absolute` da `.srOnly`: `html.scrollHeight: 1080`
  (residual de 4px sem impacto visual).

**Opcoes consideradas:**
  - **(A) Adicionar `position: relative` em todas as tables** — fragil
    (qualquer nova table precisa lembrar; perspectivas legadas ainda usam
    `.dataTable` e nao tem `position: relative`).
  - **(B) Reescrever `.srOnly` sem `position: absolute`** usando
    `clip-path: inset(50%)` mantendo `width: 1px; height: 1px;
    overflow: hidden;` — elemento permanece no flow normal mas
    visualmente clipado (1×1).
  - **(C) Usar `aria-label` no `<table>` ao inves de `<caption>`** — perde
    semantic markup HTML5 e fidelidade WAI-ARIA.
  - **(D) Detectar dinamicamente e ajustar** — complexidade desnecessaria.

**Decisao: opcao B.**

**Justificativas:**
  1. **Robustez:** funciona independentemente do contexto do elemento
     (table, tbody, tr, td, qualquer outro). Nao depende de ancestral
     posicionado.
  2. **Compatibilidade:** `clip-path: inset(50%)` tem suporte universal
     em Chrome/Firefox/Safari/Edge desde 2017 (CSS Masking Level 1).
  3. **Acessibilidade preservada:** leitores de tela continuam lendo o
     conteudo do elemento (visualmente clipado nao afeta arvore A11Y).
  4. **Simplicidade:** mudanca de uma unica classe global resolve para
     todos os usos atuais e futuros.

**Implementacao:**
```css
.srOnly {
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  border: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);    /* fallback para browsers muito antigos */
  clip-path: inset(50%);     /* mecanismo principal */
  white-space: nowrap;
}
```

`clip` foi mantido como fallback antigo (deprecated mas inerte; nao
afeta browsers modernos que usam `clip-path`).

**Alternativas rejeitadas:**
  - **Opcao A:** rejeitada pela fragilidade — solucao nao escala.
  - **Opcao C:** rejeitada por violar a semantica HTML5
    (`<caption>` e o elemento canonico para descrever uma `<table>`).
  - **Opcao D:** rejeitada por overengineering.

**Consequencias:**
  - Bug de scroll do browser eliminado em `/relatorios` (e em qualquer
    outro lugar do app que use `.srOnly`, embora atualmente seja apenas
    a Wave 5).
  - Captions adicionam 1px de altura ao layout do table (clipado visualmente
    com `inset(50%)`) — irrelevante na pratica.
  - Documentado em comentario CSS na propria classe + neste ADR.

---

## ADR-104 — Containment vertical: `html, body { overflow: hidden }` em desktop
**Data:** 2026-04-29 (Wave 5 Visual Refresh)

**Contexto:** Mesmo apos o ADR-103 eliminar a fonte principal de overflow,
ainda existia residual de 15px no `html.scrollHeight` em condicoes
especificas. Investigacao DOM revelou um loop infinito conhecido em CSS:

  1. `wrapper.min-height: 100vh = 1080px` (sempre, regardless of scrollbar
     reservation).
  2. `body.height: 100% = 1065px` quando ha scrollbar reservada
     (`html.clientHeight` exclui a barra de 15px).
  3. Wrapper > body por 15px → sintoma de overflow no `html`.
  4. Browser reserva scrollbar → goto 2 (loop).

A arquitetura do app ja contem todo conteudo scrollavel dentro do
`.cardInner` (`overflow-y: auto`, `height: 100%` do `.card` que tem
`height: calc(100vh - 2rem)`). O browser nunca deveria scrollar — qualquer
overflow no `html` e bug.

**Opcoes consideradas:**
  - **(A) Mudar `wrapper.min-height` de `100vh` para `100%`** — quebraria
    o layout no flexbox em alguns contextos (descoberto durante esta
    sessao quando tentado).
  - **(B) Usar `100dvh` em todos os lugares** — suporte ainda inconsistente
    em browsers antigos (Safari < 15.4); requer fallback.
  - **(C) `scrollbar-gutter: stable`** — reserva espaco para scrollbar mas
    nao resolve o loop (ainda triggera scrollbar quando 100vh > 100%).
  - **(D) `html, body { overflow: hidden }` em desktop, `auto` em mobile** —
    desabilita explicitamente o scroll do browser, contendo qualquer
    overflow no `.cardInner`.

**Decisao: opcao D.**

**Justificativas:**
  1. **Explicito > implicito:** documenta a intencao arquitetural (scroll
     interno ao card). Bug-class de "algum descendente acidentalmente
     ativa scroll do browser" fica eliminado.
  2. **Escopo cirurgico:** uma media query, duas regras CSS. Sem mudanca
     em layout.module.css, sem refatoracao de wrapper/main/card.
  3. **Mobile preservado:** `<= 768px` reverte para `overflow: auto`
     porque o layout mobile usa `min-height: 100vh; overflow: visible`
     no `.main` (intencional — sidebar vira drawer e o card flui livre).
  4. **Compatibilidade total:** `overflow: hidden` em html/body e
     suportado desde sempre.

**Implementacao em `globals.css`:**
```css
html, body {
  overflow: hidden;
}

@media (max-width: 768px) {
  html, body {
    overflow: auto;
  }
}
```

**Alternativas rejeitadas:**
  - **Opcao A:** rejeitada — testada e quebrou layout (main/card colapsaram
    para height: auto = altura do conteudo, nao 100vh).
  - **Opcao B:** rejeitada — `100dvh` resolve em moderno mas nao em legacy
    sem fallback.
  - **Opcao C:** rejeitada — `scrollbar-gutter` so reserva visualmente; o
    loop logico de overflow continua.

**Consequencias:**
  - Browser scroll fica 100% confiavelmente desabilitado em desktop.
  - Qualquer overflow gerado por bug futuro fica contido pelo
    `.cardInner` (visualmente verificavel via scrollbar do `.cardInner`,
    nao do browser).
  - Mobile (≤768px) mantem comportamento natural com scroll do browser.
  - Esta regra global serve como "guard rail" arquitetural — qualquer
    nova tela do dashboard automaticamente herda o containment.

---

## ADR-105 — `serie_temporal` exposto no scope=3studio (sparkline real do PROVAS CRIADAS)
**Data:** 2026-04-29 (Wave 5 Visual Refresh)

**Contexto:** O design Figma da perspectiva 3Studio inclui um sparkline no
card "PROVAS CRIADAS" identico (mesma forma) ao do card "TOTAL GERAL" do
scope=geral. A `serie_temporal` (provas criadas por dia) ja existia no
`ReportResponseGeral` desde Wave 5.0, mas nao no `ReportResponse3Studio` —
apesar de ambos os scopes agregarem o mesmo conjunto de registros (provas
criadas no periodo, com mesmos filtros aplicados). O `provas_criadas` no
3Studio e numericamente igual ao `total_provas` no Geral.

Implementacao inicial (round 6 desta sessao): sparkline sintetico
deterministico no frontend baseado em `provas_criadas` total + `total_dias`,
com padrao senoidal + jitter pseudo-aleatorio. Mario corretamente apontou
no round 7 que o grafico nao fazia sentido — era ilustrativo, nao real.
Ele explicitamente requisitou que fosse "dinamico e fizesse sentido".

**Opcoes consideradas:**
  - **(A) Sparkline sintetico no frontend** (implementacao inicial) —
    visualmente plausivel mas dado fake. Rejeitado pelo Mario.
  - **(B) Reaproveitar Geral cache no frontend via dual-fetch** — quando
    user esta em /relatorios?scope=3studio, fazer side-fetch para
    /relatorios?scope=geral para extrair `serie_temporal`. Adiciona uma
    requisicao extra, complexidade no `useReport` hook (cache key cross-
    scope), e race conditions se filtros mudarem.
  - **(C) Adicionar `serie_temporal` ao `ReportResponse3Studio`** —
    expansao mínima do schema (~20 linhas de codigo backend), mesma query
    Q2 ja usada pelo Geral.

**Decisao: opcao C.**

**Justificativas:**
  1. **Dado real:** o sparkline reflete a realidade — provas criadas por
     dia. Mario validou via comparacao byte-a-byte: paths SVG identicos
     entre TOTAL GERAL e PROVAS CRIADAS quando ambos sao alimentados com
     mesmos filtros.
  2. **Custo minimo:** uma query a mais no aggregator do 3Studio (~20
     linhas), reusando exatamente o padrao Q2 do `_aggregate_geral`. ETag
     SHA-256 cobre o response inteiro automaticamente. Cache local +
     server-side TTL 60s ja protegem contra carga adicional (a query
     usa indices ja existentes).
  3. **Coerencia entre scopes:** elimina divergencia visual entre
     perspectivas que mostram a mesma metrica subjacente. Ja era o caso
     da `provas_criadas` (3Studio) ≡ `total_provas` (Geral) — agora o
     sparkline tambem coincide.
  4. **Front-end only nao escalava:** opcao A foi rejeitada pelo proprio
     Mario; opcao B adicionaria mais codigo frontend e teria pior UX
     (loading state duplicado).

**Implementacao:**

  Schema (`backend/app/domain/schemas/report.py`):
  ```python
  class ReportResponse3Studio(BaseModel):
      ...
      serie_temporal: list[PontoSerie]
      """Provas criadas por dia (00:00 UTC do bucket). Mesma fonte do
      scope=geral — provas_criadas deste scope agrega exatamente os
      mesmos registros, entao a serie diaria coincide."""
  ```

  Aggregator (`backend/app/api/v1/reports.py:_aggregate_3studio`),
  novo Q6:
  ```python
  bucket_3s = func.date_trunc("day", ProvaDigital.created_at).label("bucket")
  stmt_serie_3s = (
      select(bucket_3s, func.count().label("qtd"))
      .select_from(ProvaDigital)
      .where(_periodo_filter(filters))
      .group_by(bucket_3s)
      .order_by(bucket_3s)
  )
  stmt_serie_3s = _aplicar_filtros_provas(stmt_serie_3s, filters)
  serie_rows_3s = (await db.execute(stmt_serie_3s)).all()

  serie_temporal_3s = [
      PontoSerie(data=r.bucket, quantidade=int(r.qtd)) for r in serie_rows_3s
  ]
  ```

  Frontend type (`frontend/src/lib/types/report.ts`):
  ```ts
  export interface ReportResponse3Studio {
    ...
    serie_temporal: PontoSerie[];
  }
  ```

  Componente (`Report3Studio.tsx`): substitui funcao
  `generateSyntheticSeries` por `data.serie_temporal.map(p => p.quantidade)`.

**Tests atualizados:**
  - `backend/tests/test_reports_api.py:_payload_3studio` adiciona
    `serie_temporal=[]`.
  - `backend/tests/test_report_schemas.py:test_3studio_scope_default`
    adiciona `serie_temporal=[]`.
  - `backend/tests/test_report_schemas.py:test_resolve_3studio` (TypeAdapter
    dict-based) adiciona `"serie_temporal": []` no input dict.
  - 633 testes ainda passam, 0 regressao.

**Alternativas rejeitadas:**
  - **Opcao A:** rejeitada pelo Mario por nao refletir dado real.
  - **Opcao B:** rejeitada por adicionar requisicao extra + complexidade
    no hook + race conditions de filtros.

**Consequencias:**
  - Tamanho do response 3Studio cresce em ~30 floats por mes (1 PontoSerie
    por dia). Desprezivel com gzip (`Content-Encoding`) + ETag SHA-256.
  - Aggregator 3Studio agora roda 6 queries (era 5) — todas otimizadas
    com indices ja existentes (`idx_provas_created_at`,
    `idx_provas_vendedor_status`, etc).
  - Sparklines do TOTAL GERAL (Geral), VENDEDOR COM MAIS ARTES (Geral) e
    PROVAS CRIADAS (3Studio) renderizam paths SVG identicos quando
    alimentados com mesmos filtros — coerencia visual confirmada via DOM
    inspection.
  - Set de campos potencialmente expansiveis no futuro: o mesmo argumento
    se aplica para `delta_*` (comparacao com periodo anterior). Aguarda
    autorizacao explicita do Mario para extensao.

---

## ADR-106 — UI completa de filtros para RF-013 na pagina /relatorios
**Data:** 2026-04-29 (Auditoria senior pos-Visual Refresh)

**Contexto:** A auditoria senior (achado H-01) identificou que a Wave 5
declarava RF-013 ✅ no `WAVE5_CLOSEOUT.md` baseado no fato de que o
backend e o hook `useReportFilters` suportavam os 5 filtros exigidos
(`período, status, vendedor, cliente E rota (padrao/direta)`). Porem a
pagina `/relatorios` so renderizava UI para 2 deles: `DateRangeFilter`
(periodo) e `SearchInput` (busca textual `q` que cobre cliente/nome/nro
requerimento). Filtros de `rota`, `vendedor` e `status` so funcionavam
via manipulacao manual de URL — usuario nao tinha affordance visivel.
Status era setado indiretamente clicando num segmento do donut da
perspectiva Geral.

**Decisao:** 3 componentes shared novos com UI dedicada:

  1. **`RotaFilter.tsx`** — segmented pill com 3 botoes
     (Todas | Padrao | Direta). Reutiliza as classes
     `presetButton`/`presetButtonActive` do DateRangeFilter para
     consistencia visual da filtersBar.
  2. **`StatusFilter.tsx`** — `<select>` nativo com 10 opcoes
     (todos os `StatusProva`) + "Todos". Wrapper `.selectFilterPill`
     com chevron SVG customizado. Reutiliza `STATUS_LABELS` da
     Wave 2 (sem duplicar).
  3. **`VendedorFilter.tsx`** — `<select>` nativo populado via fetch
     leve `GET /api/v1/users?setor=VENDEDOR&ativo=true&page_size=100`.
     Hook de fetch local ao componente (uso unico — principio "extract
     only when reused"). Loading/erro tratados com `disabled` + texto
     no placeholder.

Renderizados em `page.tsx` na `<section className={filtersBar}>` apos
`SearchInput`. Reusam `setFilter(key, value)` do `useReportFilters`
(backend ja aceitava os parametros).

**Alternativas rejeitadas:**
  - **Apenas StatusFilter (deixar rota/vendedor para Wave 6):** rejeitado
    porque RF-013 exige os 5 filtros explicitamente; auditoria marcou H-01.
  - **Autocomplete em vez de select para Vendedor:** considerado mas
    descartado — volume operacional 3Studio (~10-30 vendedores ativos)
    cabe num select; autocomplete adicionaria complexidade sem ganho
    proporcional. Promover se passar de ~50 vendedores.
  - **Combinar filtros num unico componente "FiltersBar":** rejeitado —
    cada filtro tem ciclo de vida e estado proprio (especialmente
    `VendedorFilter` que tem fetch async); separar respeita SRP.

**Consequencias:**
  - 3 arquivos novos (~50-80 LOC cada).
  - 1 grupo novo de classes CSS em `relatorios.module.css`
    (`.selectFilterPill` + variantes).
  - RF-013 ✅ por construcao — todos os 5 filtros tem affordance
    visivel.
  - Ainda existem 2 caminhos para filtrar status: dropdown explicito
    (StatusFilter) e clique em segmento do DonutChart na perspectiva
    Geral (toggle, ver ADR-108). Ambos sincronizam via mesma URL param.

---

## ADR-107 — Bypass de cache backend via `?_force=1` para invalidacao por Realtime
**Data:** 2026-04-29 (Auditoria senior — bug 3 pos-teste manual)

**Contexto:** Mario reportou em teste manual que os sparklines dos cards
TOTAL GERAL, VENDEDOR COM MAIS ARTES (perspectiva Geral) e PROVAS CRIADAS
(perspectiva 3Studio) nao atualizavam apos criar/transitar provas, mesmo
com Supabase Realtime conectado. Diagnostico:

  1. Cliente cria prova em outra aba → INSERT em `provas_digitais`.
  2. Realtime do Supabase dispara em /relatorios apos ~2s (debounce).
  3. `useReport.invalidate()` limpa cache local e refetcha.
  4. Backend recebe request, faz cache hit no `ReportCache` (TTL 60s) e
     serve o payload **stale** com o mesmo ETag.
  5. Frontend recebe dados velhos (sem a prova nova) — sparkline nao
     atualiza ate o TTL expirar (~60s).

ADR-097 documentou explicitamente "Backend nao invalida sua propria
cache via Realtime — deixa TTL expirar naturalmente". Era aceitavel em
teoria, mas a janela de 60s e perceptivel para o usuario que esta
criando provas e esperando feedback visual imediato.

**Decisao:** novo query param `?_force=1` (alias FastAPI: `force_refresh`)
no `GET /api/v1/reports`. Quando `true`:
  - Backend pula `_get_or_compute` (que faria cache lookup) e chama
    diretamente `_dispatch_aggregator` para recomputar.
  - Resultado e armazenado no `ReportCache` (sobrescreve a entry stale)
    para que polling subsequente reuse.
  - Cliente respeita: `useReport.invalidate()` (chamado por Realtime)
    adiciona `_force=1` na URL e omite o header `If-None-Match` para
    nao receber 304 indevido.
  - `useReport.refresh()` (polling 30s, botao retry) **mantem** o
    caminho cache + `If-None-Match` → 304 (preserva ADR-097 para o
    caso geral).

**Alternativas rejeitadas:**
  - **Reduzir TTL para 5s globalmente:** rejeitado — multiplica queries
    por ~12x mesmo quando nada muda (perde ADR-097 para o caso comum
    de 30 usuarios polling).
  - **Backend escuta Realtime e auto-invalida cache:** complexo —
    requer service role do Supabase no backend, gerencia de subscricao,
    e sincronizacao entre workers uvicorn (cada worker tem cache
    proprio). Custo desproporcional para a Wave 5.
  - **Endpoint POST `/reports/invalidate-cache`:** novo endpoint so
    para isso; menos elegante que parametro de query.
  - **Header `Cache-Control: no-cache` no request:** semanticamente
    correto (RFC 9111) mas confunde com cache HTTP cliente; query param
    explicito e mais legivel.

**Consequencias:**
  - 1 query extra ao backend por evento de Realtime (~1-2s apos cada
    INSERT/UPDATE em `provas_digitais` que afeta filtros ativos).
  - Cache backend e atualizado pelo bypass — proximas requisicoes (de
    outros usuarios, polling, etc) reusam.
  - Comportamento de polling NAO muda — economia de queries do ADR-097
    preservada (~720 queries/hora vs 14400 sem cache).
  - **Atualiza parcialmente ADR-097:** a 3a camada da estrategia (cache
    backend) agora pode ser bypassed por Realtime invalidation. ADR-097
    permanece valido para polling regular.
  - Sparkline atualiza em ~3-5s apos mudanca (Realtime debounce 2s +
    recomputo backend ~1-2s).

---

## ADR-108 — DonutChart: tratamento de arco SVG completo + toggle behavior
**Data:** 2026-04-29 (Auditoria senior — bug 4 pos-teste manual)

**Contexto:** Dois bugs identificados no `DonutChart` apos teste manual
do Mario:

**Bug A (visual):** Quando o donut tem apenas 1 segmento ocupando 100%
(caso tipico apos clicar num status para filtrar a vista da perspectiva
Geral — backend retorna `distribuicao_status` com 1 item), os angulos
`startAngle=0` e `endAngle=2π` produzem coordenadas identicas em
`startOuter` e `endOuter` (ambos no topo, 12h):

  ```
  polarToCartesian(100, 100, 90, 0)  → (100, 10)
  polarToCartesian(100, 100, 90, 2π) → (100, 10)  ← mesmo ponto
  ```

  SVG nao renderiza um arco circular completo num unico `<path>` quando
  os pontos coincidem — path fica vazio, donut some visualmente.

**Bug B (UX):** Apos clicar num segmento e o filtro ser aplicado, nao
havia jeito de "voltar" sem mexer na URL ou recarregar a pagina. O
StatusFilter (ADR-106) permite trocar para "Todos", mas o usuario que
clicou no donut esperava que clicar de novo desfizesse o filtro
(toggle behavior natural).

**Decisao:**

**Fix A — epsilon no arco completo:**
  - `buildArcPath` detecta arco de 360° (`endAngle - startAngle >= 2π
    - 1e-6`) e subtrai `1e-3 rad` (~0.057°) do `endAngle`.
  - Diferenca visual: ~0.09px num viewport 200×200 — imperceptivel.
  - `largeArc` flag passa a usar `adjustedEnd` para manter o
    comportamento correto.

**Fix B — toggle no donut:**
  - `ReportGeral` recebe nova prop `statusFilter: StatusProva | null`
    (passada pelo `page.tsx` a partir de `filters.status ?? null`).
  - `onSegmentClick` no DonutChart compara `key clicado` com
    `statusFilter`: se igual, dispara `onStatusClick(null)` (remove
    filtro); senao, dispara `onStatusClick(novo_status)`.
  - Tipo de `onStatusClick` mudou para
    `(status: StatusProva | null) => void`.
  - `setFilter("status", null)` remove o param da URL → backend retorna
    todos os status → donut volta ao estado multi-segmento.

**Alternativas rejeitadas:**
  - **Renderizar arco completo como `<circle>` + stroke:** funciona mas
    quebra a uniformidade dos paths SVG (que sao animados via Framer
    Motion). Epsilon e cirurgico e preserva a estrutura.
  - **Dividir arco completo em 2 arcos de 180°:** funciona mas adiciona
    complexidade no `segments.useMemo` (precisaria retornar 2 paths
    para um item) e quebra animacoes existentes.
  - **Botao "Limpar filtros" explicito:** consideravel para Wave 6 mas
    desnecessario agora — o StatusFilter (ADR-106) ja oferece
    "Todos", e o toggle no donut e mais natural para quem clicou no
    segmento.
  - **Status como toggle apenas no clique do segmento, mantendo o
    StatusFilter:** mantido — coexistem dois caminhos sincronizados via
    URL param. UX preferivel a forcar um unico caminho.

**Consequencias:**
  - DonutChart renderiza corretamente em qualquer condicao (1 segmento
    ou N).
  - Clique em segmento ativo desfaz o filtro sem precisar tocar URL
    nem recarregar.
  - `ReportGeral` precisa de `filters.status` para o toggle — propagado
    via `PerspectivaRenderer`.
  - StatusFilter (ADR-106) e clique-no-donut sao redundantes mas
    sincronizados (mesma URL param) — usuario pode usar qualquer caminho.

---

## ADR-109 — Filtros propagam para todas as queries agregadas no mesmo response (Wave 5 Audit Round 2)
**Data:** 2026-04-29 (Wave 5 Auditoria Senior Round 2)

**Contexto:** A auditoria sênior round 2 (achado H-A1) identificou que
`_aggregate_geral` retornava indicadores INCONSISTENTES quando o admin
aplicava filtros (`vendedor_id`, `rota`, `q`):
  - `total_provas`, `serie_temporal`, `distribuicao_status`,
    `distribuicao_rota` e `ranking` corretamente FILTRADOS via
    `_aplicar_filtros_provas`.
  - `tempo_medio_aprovacao_horas` e `taxa_reprovacao` (Q4) GLOBAIS,
    porque `stmt_aprov` selecionava de `Movimentacao` sem JOIN com
    `ProvaDigital` e `_aplicar_filtros_provas` nao era chamado.

Mesma divergencia identificada em `_aggregate_3studio` Q5
(`cancelamentos_top` — achado M-A1): query selecionava de `ProvaDigital`
mas tambem nao chamava `_aplicar_filtros_provas`.

Resultado pratico: admin filtrava por "vendedor X" e via `total_provas`
do vendedor X mas `taxa_reprovacao` da empresa inteira. Confunde a UI
(taxa nao bate com o ranking renderizado no mesmo response).

**Decisao — Padrao arquitetural: filtros propagam consistentemente:**

  Toda query agregada que contribui para um indicador no mesmo response
  do `/reports` DEVE aplicar `_aplicar_filtros_provas(stmt, filters,
  apply_status=...)` apos garantir que `ProvaDigital` esta no FROM/JOIN.

  - **Q4 (`_aggregate_geral`):** adicionado `.join(ProvaDigital,
    ProvaDigital.id == decisao_alias.prova_id)` apos o JOIN com
    `retirada_subq`, e `stmt_aprov = _aplicar_filtros_provas(stmt_aprov,
    filters, apply_status=False)`. `apply_status=False` porque a query
    ja filtra por `Movimentacao.status_novo IN (APROVADA, REPROVADA)`;
    aplicar `filters.status` em cima de `ProvaDigital.status` produziria
    interseccao impossivel (mesmo padrao da Q3 — auditoria M-02
    anterior).
  - **Q5 (`_aggregate_3studio`):** adicionado `stmt_top =
    _aplicar_filtros_provas(stmt_top, filters, apply_status=False)`.
    Query ja filtra por `status=CANCELADA`; aplicar `filters.status
    != CANCELADA` zeraria resultado. Ja tinha `ProvaDigital` no FROM,
    nao precisou de JOIN extra.

**Alternativas rejeitadas:**
  - **Manter Q4/Q5 globais (status quo):** rejeitado — causa
    inconsistencia visivel ao admin que filtra por vendedor/rota.
    Quebra principio de menor surpresa.
  - **Documentar a divergencia em vez de corrigir** ("indicadores Q4/Q5
    sao globais por design"): rejeitado — nada na UI sinaliza qual
    indicador ignora filtros; a coerencia visual e mais valiosa que
    uma "feature documentada".
  - **Refatorar para 1 unica query mega-CTE:** rejeitado por
    complexidade; o padrao "varias queries pequenas + helper
    compartilhado" e mais sustentavel. Cache TTL 60s + ETag SHA-256
    cobrem o custo de N queries por scope.

**Consequencias:**
  - 3 queries do `reports.py` agora consistentes:
    - **Q3** (tempo_ciclo no scope=geral, ja corrigida em M-02 da
      auditoria Round 1).
    - **Q4** (tempo_aprov + taxa_reprovacao no scope=geral, H-A1).
    - **Q5** (cancelamentos_top no scope=3studio, M-A1).
    Todas usam JOIN com `ProvaDigital` (quando necessario) +
    `_aplicar_filtros_provas(..., apply_status=False)`.
  - Padrao "queries que ja filtram por `Movimentacao.status_novo`
    especifico usam `apply_status=False`" agora consolidado em 3
    pontos do codigo. Convencao para futuras queries similares (Wave
    6+).
  - Indicadores `tempo_medio_aprovacao_horas`, `taxa_reprovacao`
    (geral) e `cancelamentos_top` (3studio) agora respondem
    coerentemente a filtros — UI passa a mostrar a "taxa de reprovacao
    do vendedor X no periodo X" quando filtrado, em vez da taxa
    global.
  - Performance: 1 JOIN extra em Q4 sobre `idx_provas_pkey` (lookup
    O(1) por `ProvaDigital.id`). Custo desprezivel.
  - **Smoke tests por inspecao do source** em
    `TestAuditoriaSenior20260429Round2.test_h_a1_q4_geral_aplica_filtros_provas`
    e `.test_m_a1_q5_3studio_aplica_filtros_provas` — falham se
    alguem remover o JOIN ou a chamada do helper, prevenindo
    regressao.

**Aplicacao retroativa:**
  - **Banco:** zero alteracao. Mudanca e apenas em codigo Python.
  - **API contract:** nenhuma mudanca em response shape ou em
    parametros aceitos. Apenas o VALOR dos campos `tempo_medio_*` e
    `taxa_reprovacao` muda quando filtros sao aplicados (semantica
    correta agora).
  - **Frontend:** nenhuma mudanca necessaria; usa os mesmos campos.
  - **Cache + ETag:** invalidados naturalmente por `?_force=1`
    (Realtime invalidation do ADR-107). TTL de 60s expira sozinho. Em
    pior caso, cliente ve dados velhos (taxa global) por <60s apos
    deploy — aceitavel.

**Audit trail:**
  - ADR-109 (este registro) — H-A1 + M-A1.
  - CHANGELOG.md entrada `[2026-04-29 — Wave 5 Auditoria Senior Round 2]`.
  - Tests `TestAuditoriaSenior20260429Round2.test_h_a1_*` e
    `.test_m_a1_*` previnem regressao via inspecao do source.

---

## ADR-110 — Endpoint dedicado `/api/v1/audit-log` em vez de extender `/provas/{id}/movimentacoes`
**Data:** 2026-04-29 (Wave 6, Componente 18)

**Contexto:** A Wave 6 entrega uma interface de leitura sobre o log
imutavel ja populado desde a Wave 3. Existe ja um endpoint
`GET /api/v1/provas/{id}/movimentacoes` (Wave 2 C08) que lista
movimentacoes de uma prova com scoping mais permissivo (admin +
vendedor da prova + motorista/clicheria por status atual). Surgiu a
opcao de extender esse endpoint para cobrir os requisitos do
Componente 18 em vez de criar `/api/v1/audit-log` separado.

**Decisao:** **endpoint novo dedicado** `/api/v1/audit-log` com 3
sub-rotas (listagem paginada, detalhe, by-prova).

**Razao em 4 pontos:**

  1. **Tabela diferente.** `audit_logs` cobre `criar_prova`,
     `escanear_prova`, `transitar_status`, `reiniciar_ciclo`,
     `atualizar_configuracao`, `REPORT_EXPORTED`. `movimentacoes`
     so cobre transicoes (subset de transitar_status +
     reiniciar_ciclo). RNF-005 exige log "completo" — o endpoint
     da Wave 6 precisa ler `audit_logs`, nao `movimentacoes`.
  2. **Scoping diferente.** `pol_audit_select` e admin-only;
     `pol_movimentacoes_select` cobre 5 atores (admin + vendedor +
     autor + motorista por status + clicheria por status). Misturar
     os dois scoping no mesmo endpoint complicaria o backend e
     tornaria o front guard mais fragil.
  3. **Convivencia.** O endpoint da Wave 2 e consumido pelo
     Componente 12 (Timeline da prova individual no /provas/[id]).
     Mudar contrato dele afetaria a Wave 2/3 — viola isolamento de
     wave (regra critica do prompt da Wave 6).
  4. **Visao transversal.** Listagem `/audit-log` (sem filtro de
     prova) e o caso de uso primario do admin para investigar
     incidentes — algo que `/provas/{id}/movimentacoes` nao oferece
     por construcao.

**Alternativas rejeitadas:**

  - **Extender `/provas/{id}/movimentacoes`** com flag `?include_audit=1`:
    rejeitado — viola isolamento de wave, mistura scopings, e o flag
    discriminado seria proxy de "voce e admin?" o que duplicaria a
    propria checagem de RBAC.
  - **Combinar audit_logs + movimentacoes em response unico:** rejeitado
    — UI fica confusa (eventos duplicados — cada transicao tem 1 audit
    + 1 movimentacao). Wave 6 oferece `movimentacao_relacionada` no
    detalhe quando relevante (D2 do analysis.md), preservando ambos os
    contratos sem duplicar listagens.
  - **`/api/v1/auditoria` em portugues:** considerado mas rejeitado —
    "auditoria" tem conotacao de "processo de auditoria" (review por
    auditor); "audit-log" e mais especifico ao registro tecnico que
    estamos consultando. Convencao consistente com `/api/v1/users` e
    `/api/v1/provas` (substantivos da entidade, nao processos).

**Consequencias:**

  - 3 endpoints novos sob prefixo `/api/v1/audit-log` (registrados em
    `app/main.py`).
  - Endpoint da Wave 2 fica intacto — Componente 12 continua usando.
  - 1 router/service/schema novo no backend; 1 hook + 1 pagina nova
    no frontend; sem alteracao em codigo das Waves 0-5.
  - Convivencia documentada na §3.3.3 do `docs/wave6/analysis.md`.

---

## ADR-111 — Sem cache em `/api/v1/audit-log` (`Cache-Control: no-store`)
**Data:** 2026-04-29 (Wave 6, Componente 18)

**Contexto:** A Wave 5 (`/api/v1/reports`) adotou cache TTL 60s +
ETag SHA-256 + Realtime invalidation (ADR-097, ADR-107). O caso de
uso de relatorios e idempotente: 30 admins polling sobre a mesma
janela temporal recebem o mesmo agregado, e 60s de "data velha" e
aceitavel para uma decisao gerencial. A pergunta natural era se a
Wave 6 deveria reusar o mesmo `ReportCache` do report_cache.py.

**Decisao:** **Sem cache** no `/api/v1/audit-log`.
Header `Cache-Control: no-store, Pragma: no-cache` em toda resposta.

**Razao:**

  1. **Caso de uso e tempo real.** Audit-log e ferramenta de
     investigacao em tempo real — admin abre a tela durante um
     incidente para confirmar quem fez o que e quando. 60s de delay
     poderia mascarar um evento que acabou de acontecer (e que e
     justamente o motivo da investigacao).
  2. **Volume baixo.** A tabela cresce devagar (~4-8 entradas/dia hoje,
     pode chegar a ~100-200/dia em uso pleno). Sem cache, cada
     request faz 2 queries (items + count) com indices cobrindo
     bem — custo desprezivel.
  3. **Granularidade de filtros.** Diferente de relatorios (4 scopes
     fixos), audit-log aceita combinacoes arbitrarias de 9 filtros.
     Cache hit rate seria proximo de zero ate em uso intenso.
  4. **No-store evita confusao com browser cache.** Cliente HTTP
     respeita `no-store` e nao guarda copia no disco; em conjunto
     com a logica do `useAuditLog` (sem cache local), garante que
     refresh manual sempre retorna estado atual.

**Alternativas rejeitadas:**

  - **Reusar `ReportCache` com TTL pequeno (5-10s):** rejeitado —
    multiplica complexidade sem ganho perceptivel; admin investigando
    incidente nao sente diferenca de 60s de cache, mas em pior caso
    pode ser confundido por dados ainda nao visiveis.
  - **ETag SHA-256 sem TTL:** rejeitado — `If-None-Match => 304`
    economizaria bytes mas nao resolve o cenario "mostre-me o que
    aconteceu nos ultimos 30s". E o computo do hash teria custo no
    pior caso (admin paginando uma tabela de 100k linhas).
  - **Cache so em `/by-prova/{id}`:** rejeitado — caso de uso ainda
    e investigacao; consistencia entre os 3 endpoints e mais valiosa
    que micro-otimizacao.

**Consequencias:**

  - Cada request executa 2 queries (items + count); audit-log nao
    contribui para a metrica de "queries economizadas" do Wave 5.
  - Frontend nao precisa gerenciar invalidation, ETag, ou Realtime
    invalidation. `useAuditLog` apenas refetcha quando filters mudam.
  - Logger INFO em cada acesso (`logger.info("audit_log.list user=...")`)
    cria meta-rastro de quem leu o que — util para investigacao
    posterior. Esse log NAO grava em `audit_logs` (evita
    auto-referencia + spam).

---

## ADR-112 — Imutabilidade do log em 3 camadas (RLS 008 REVOKE)
**Data:** 2026-04-29 (Wave 6, Componente 18)

**Contexto:** A imutabilidade de `audit_logs` (RNF-005) ja era garantida
em duas camadas antes da Wave 6:

  1. Trigger `trg_audit_logs_imutavel BEFORE UPDATE OR DELETE`
     (Wave 0, migration 001). Bloqueia mutacoes inclusive via
     `service_role` (triggers fazem efeito independente de bypassrls).
  2. RLS deny-by-default — ausencia de policy
     INSERT/UPDATE/DELETE com RLS habilitada bloqueia clientes
     `anon` e `authenticated` (Wave 0 RLS 001 + Wave 1 RLS 004 +
     Wave 2 RLS 005).

A auditoria pre-execucao da Wave 6 (Gate 1, §2.3 do
`docs/wave6/analysis.md`) confirmou via `has_table_privilege` que
ambos `anon` e `authenticated` AINDA tinham GRANT-level
INSERT/UPDATE/DELETE concedido sobre `audit_logs`. Isso nao gerava
vazamento real (RLS + trigger blocavam), mas:

  - O erro retornado para o cliente era "no policy found" (sutil).
  - Uma migration futura que adicionasse policy INSERT/UPDATE/DELETE
    por engano (ex: copiando boilerplate do CRUD de usuarios) NAO
    seria bloqueada pelo REVOKE inexistente — o trigger seria a
    unica defesa restante.

**Decisao:** Adicionar **terceira camada** via
`backend/migrations/rls/008_revoke_audit_logs_mutation.sql`:

```sql
REVOKE INSERT, UPDATE, DELETE ON public.audit_logs FROM anon, authenticated;
```

`service_role` mantem GRANT — backend continua escrevendo via
`audit_service.log_audit()`. SELECT continua liberado (RLS
`pol_audit_select` filtra para admin-only).

**Aplicada em producao** via MCP `execute_sql` em 2026-04-29; validada
via `has_table_privilege`.

**Alternativas rejeitadas:**

  - **Manter status quo (2 camadas).** Rejeitada — o REVOKE e
    aditivo, idempotente e zero-impacto operacional; nao fazer e
    deixar uma armadilha latente para futuras migrations.
  - **Trigger BEFORE INSERT bloqueando tudo exceto service_role.**
    Rejeitada — complexo, requer detectar role no trigger, e
    quebra-se se o backend for migrado para uma role diferente.
    REVOKE e idiomatic Postgres.
  - **REVOKE em todas as 6 tabelas imutaveis** (`audit_logs`,
    `movimentacoes`, `etiquetas`). Rejeitada por escopo —
    `movimentacoes` precisa permitir INSERT via `service_role` mas
    REVOKE em `anon`/`authenticated` faria sentido conceitualmente.
    Adiada para Wave 6 polish ou Wave 7 — registrada aqui como
    follow-up.

**Consequencias:**

  - `audit_logs` agora tem 3 camadas independentes contra mutacao.
  - Erro de cliente que tente UPDATE/DELETE/INSERT vira "permission
    denied" antes mesmo da RLS ser consultada — sinal mais explicito
    que "no policy found".
  - Documentado no `docs/wave6/analysis.md` §3.2.2.
  - Validacao reproducivel via:
    ```sql
    SELECT has_table_privilege('authenticated','public.audit_logs','UPDATE');
    -- esperado: false
    ```

---

## ADR-113 — Filtros semanticos do audit-log resolvidos no backend, nao no frontend
**Data:** 2026-04-29 (Wave 6, UX iteration apos Componente 18)

**Contexto:** Apos o Gate 2 da Wave 6 entregue, Mario pediu reforco de
UX visando uso real em producao (~60k audits/ano). O caso de uso
primario do admin e "encontrar o que aconteceu rapido em volume
crescente". A UI inicial expoe o `acao` cru (`transitar_status`,
`reiniciar_ciclo`, etc.) — mas o admin pensa em categorias semanticas
("apenas reprovacoes", "apenas cancelamentos") que sao DERIVADAS de
combinacoes de `acao` + `detalhes_json.para`:

  - reprovacao    = acao=transitar_status AND detalhes_json.para=REPROVADA_PELO_VENDEDOR
  - cancelamento  = acao=transitar_status AND detalhes_json.para=CANCELADA
  - reinicio      = acao=reiniciar_ciclo
  - criacao       = acao=criar_prova
  - admin         = acao IN ('atualizar_configuracao', 'REPORT_EXPORTED')

Surgiram duas opcoes para implementar o filtro semantico:

**Opcao (i) — Resolver no frontend:** UI traduz a categoria em
parametros existentes (`acao` + filtro adicional via `q` em
detalhes_json). Backend nao muda.

**Opcao (ii) — Adicionar `tipo_evento` no backend:** novo query param
com whitelist; service mapeia para WHERE clause server-side.

**Decisao:** **Opcao (ii)** — `tipo_evento` no backend.

**Razao em 4 pontos:**

  1. **Paginacao consistente.** No (i), o frontend recebe 50 audits
     crus e filtra para "apenas reprovacoes" — pode acabar com 5
     visiveis na pagina e o admin precisa avancar para encontrar
     mais. Confunde a paginacao numerada (UX B1) que diz
     "Mostrando 1-50 de 5234" mesmo quando so 5 sao reprovacoes.
     Server-side filtra antes da paginacao.

  2. **Performance.** Em volume alto (>10k linhas), o (i) baixa
     tudo no `q` filter em `detalhes_json::text` (LIKE custoso).
     O (ii) usa `astext == 'REPROVADA_PELO_VENDEDOR'` que e
     comparacao exata — pode ser indexada com GIN no futuro
     se necessario.

  3. **API mais limpa.** Cliente externo (curl, integracao futura)
     consome `?tipo_evento=reprovacao` em vez de
     `?acao=transitar_status&q=REPROVADA_PELO_VENDEDOR` (que e
     fragil e expoe implementacao interna). Padrao consistente com
     o Wave 5 reports onde `?scope=geral` esconde a complexidade
     de qual agregador rodar.

  4. **Defesa central.** A whitelist `TIPOS_EVENTO_VALIDOS` no
     schema rejeita valores arbitrarios em UM lugar. Se o frontend
     traduzisse, qualquer caller direto (incluindo PR review futuro
     de novo cliente) precisaria duplicar a logica.

**Alternativas rejeitadas:**

  - **Opcao (i) — frontend traduz:** rejeitada pelos 4 motivos acima.
    A simplicidade de "nao mudar backend" nao compensa quebrar
    paginacao + performance + API contract.

  - **Schema com Enum tipado em vez de string + whitelist:**
    consideravel — mais idiomatic Pydantic v2. Mas Enum exige
    importacao em todo lugar que toca o param e cria um ponto a
    mais para manter sincronizado com o frontend. String + whitelist
    centralizada (frozenset constante exportada no schema) e
    suficiente, e o teste `test_schema_aceita_valores_validos`
    (parametrizado) cobre todos os valores.

**Consequencias:**

  - 1 query param novo no `GET /api/v1/audit-log` (`tipo_evento`).
  - 1 helper privado novo (`_aplicar_tipo_evento`).
  - 1 constante nova exportada (`TIPOS_EVENTO_VALIDOS`).
  - Frontend (`auditLog.ts`) tem `TIPO_EVENTO_LABELS` para a UI mas
    NAO traduz — apenas envia a string.
  - 7 testes parametrizados cobrindo cada valor + edge cases
    (case-insensitive, "todos" -> None, valor invalido -> 422).
  - Padrao a seguir em adicoes futuras: novo tipo_evento adiciona
    1 entrada no frozenset + 1 ramo no `_aplicar_tipo_evento`.
    Frontend ganha 1 entrada no dict de labels. Sem mudanca de
    contrato em outros pontos.

**Decisao similar (UX B4 — order_by):** mesma logica aplicada para
ordenacao clicavel. `ORDER_BY_VALIDOS = {created_at, acao,
usuario_nome}` no schema; helper `_resolver_order_by_column` mapeia
string -> coluna SQLAlchemy via `if/elif` explicito (defesa
anti-SQL-injection em duas camadas: schema rejeita arbitrario antes
de chegar; service nunca usa `getattr` reflexivo). Teste
`test_schema_rejeita_coluna_arbitraria` cobre `"id; DROP TABLE"` e
`"ip_address"` (nao na whitelist).

---

## ADR-114 — Focus trap obrigatorio em modais/drawers (audit Wave 6)
**Data:** 2026-04-29 (Wave 6, auditoria senior)

**Contexto:** A Wave 3 audit (2026-04-13) estabeleceu o `useFocusTrap`
em `frontend/src/hooks/useFocusTrap.ts` como padrao para modais
(WCAG 2.1 — focus management em dialogs). O hook foi aplicado em todos
os modais da Wave 3 (`AdminActions.tsx`, `VisualizarEtiquetaModal.tsx`)
e na Wave 5 em `KeyboardShortcutsHelp.tsx`.

A auditoria senior da Wave 6 descobriu que o **drawer lateral** da
`/auditoria` (Componente 18) declarava `role="dialog" + aria-modal="true"`
mas **nao aplicava** `useFocusTrap`. O Gate 1 (`docs/wave6/analysis.md`
§3.5.3) listava o hook como "obrigatorio no drawer" — divergencia entre
analise e execucao.

**Decisao:** Aplicar `useFocusTrap` em **todo elemento com `role="dialog"`
ou `aria-modal="true"`** sem excecoes. Padrao reforcado:

```tsx
const trapRef = useFocusTrap<HTMLElement>(open);
// ...
<aside ref={trapRef} role="dialog" aria-modal="true" ...>
```

**Razao em 3 pontos:**

  1. **WCAG 2.1 Guideline 2.4.3 (Focus Order):** dialogs modais devem
     reter o foco dentro de seu container. Sem trap, Tab/Shift+Tab
     leva o usuario para elementos da pagina por tras do backdrop —
     que ja recebeu `aria-hidden` em alguns casos, mas nao em todos.
  2. **Defesa em profundidade:** o `aria-modal="true"` informa o leitor
     de tela mas nao bloqueia teclado. O hook fecha o gap.
  3. **Consistencia:** todos os outros modais do projeto ja tem o trap.
     Drawer da /auditoria foi a unica regressao — corrigida nesta
     auditoria.

**Alternativas rejeitadas:**

  - **Aceitar como debito tecnico:** rejeitada (Mario aprovou correcao
    imediata, opcao A na Fase 4 da auditoria). 3 linhas de codigo,
    risco zero, padrao ja validado.
  - **Implementar focus trap nativo via `inert` attribute:** considerado.
    `inert` e suportado em todos os browsers modernos (Chrome 102+,
    Firefox 112+, Safari 15.5+). Mas trocar `useFocusTrap` por `inert`
    seria refactor de todos os modais existentes — fora do escopo da
    auditoria. Registrar como follow-up se virar pattern.

**Consequencias:**

  - 1 import + 1 hook call + 1 ref na `auditoria/page.tsx` (Wave 6).
  - Padrao reforcado em ADR para futuras paginas com dialogs/drawers.
  - Auditorias futuras devem checar explicitamente: todo `role="dialog"`
    deve ter `ref={useFocusTrap(open)}`.


---

# Wave 1 (v4.0) — Componente 05 (Atualizacao v4.0)

Decisoes registradas durante a implementacao da Matriz de Acesso RBAC
em 3 camadas (JSON SSoT + Python + RLS Postgres). Todas em
`wave1-v4/componente-05`, 2026-04-30.

## D-1 — JSON como SSoT em vez de TS + gerador para Python

**Contexto:** o Gate 1 propunha `access-matrix.ts` como fonte unica e
um gerador `scripts/gen_access_matrix_py.py` para emitir
`backend/app/access/matrix.py` em paralelo. O risco identificado: parser
TS frágil (precisaria entender `as const`, type unions, etc).

**Decisao:** **JSON unico em `shared/access-matrix.json`** lido por
ambos os lados:
  - TS importa via `import data from "../../../shared/access-matrix.json"`
    com `resolveJsonModule: true` no tsconfig (Next 14 suporta).
  - Python le via `pathlib.Path + json.load` em `app/access/matrix.py`,
    com validacao de schema no startup (FAIL FAST se JSON inconsistente).

**Alternativas avaliadas:**
  - **TS + gerador:** rejeitada (parser fragil, manutencao chata).
  - **YAML:** rejeitada (parser yaml em TS exige dependencia nova; JSON
    e suficiente porque o conteudo nao precisa de comentarios complexos
    — usamos campos `_*` como comentarios in-line).
  - **Endpoint REST que retorna a matriz:** rejeitada (round-trip extra +
    dependencia runtime entre frontend e backend).

**Consequencias:**
  - Zero gerador, zero drift entre TS e Python por construcao.
  - Comentarios sobre semantica vivem no proprio JSON via campos
    `_comment`/`_matrix_row`/`_clicheria_divergence_note`.
  - Test `test_matrix_structure.py` carrega o mesmo JSON e valida
    estrutura/invariantes.

## D-2 — Clicheria em `provas.list`/`provas.detail`: PARCIAL em vez de FULL

**Contexto:** a Secao 6 do `RequisitosProvasDigitais_v4_0.docx` lista
Clicheria como `●` (FULL) em "Listagem de Provas" e "Visualizacao de
Prova (detalhe)". A observacao explicita diz: "3Studio e Clicheria
veem todas. Vendedor ve apenas provas em que e o vendedor responsavel.
Motorista ve apenas provas em estados 'Em Transito'."

Entretanto, o sistema em producao (v3.0) tem RLS `pol_provas_select`
que filtra Clicheria por `status IN (ENVIADA_PARA_CLICHERIA,
ENCAMINHADA_A_CLICHERIA, RECEBIDA_PELA_CLICHERIA)`. Manter a Matriz
literal expandiria o escopo da Clicheria — mudanca de produto.

**Decisao:** **Manter PARCIAL com scope `status_clicheria`** na Wave 1
v4.0. Documentar a divergencia como follow-up obrigatorio para
confirmar com o solicitante (Renan/Mario) na primeira oportunidade.

**Alternativas avaliadas:**
  - **Alinhar com Matriz literal (FULL):** rejeitada para esta wave.
    Mudaria comportamento de produto sem autorizacao explicita; a wave
    deve ser conservadora ("nao cria nem remove perfis", item explicito
    do prompt).
  - **Pausar e perguntar:** considerada. Optou-se por seguir
    conservador + documentar no JSON e aqui — o solicitante pode
    decidir na review do PR.

**Consequencias:**
  - `_clicheria_divergence_note` no `shared/access-matrix.json` registra
    a divergencia textual.
  - Teste `test_provas_list_partial_scopes_match_v3_behaviour` afirma
    que Clicheria=PARCIAL com scope `status_clicheria` (NAO FULL).
  - Se aprovado expandir, mudanca = (a) JSON: trocar `parcial` por `full`
    para clicheria em provas.list e provas.detail; (b) RLS: remover o
    filtro de status da clausula da policy `pol_provas_select` para
    Clicheria (e na pol_movimentacoes_select e pol_etiquetas_select);
    (c) frontend: nada (useAuthorization continua funcionando).

## D-3 — Padrao SQL das policies: `EXISTS` contra `usuarios` em vez de `auth.jwt() ->> 'setor'`

**Contexto:** o `DAT_RastreioProvasDigitais_v3_0.docx` Secao 7.2 sugere
policies usando `auth.jwt() ->> 'setor'` para evitar JOIN extra. O JWT
do Supabase Auth atual NAO tem o claim `setor` (validado via MCP:
`raw_app_meta_data` apenas `{provider, providers}`, `raw_user_meta_data`
apenas `{email_verified}`).

Para colocar `setor` no JWT, seria necessario configurar Custom Access
Token Hook na config do Supabase Auth — fora do escopo da Wave 1 v4.0
(toca configuracao de Auth, nao codigo da app).

**Decisao:** **Manter o padrao atual** (subquery `EXISTS` contra
`public.usuarios`), encapsulado em 3 funcoes helper SECURITY DEFINER
em schema `app_private`:
  - `app_private.current_user_is_admin()` -> boolean
  - `app_private.current_user_setor()` -> setor_enum
  - `app_private.current_user_id()` -> uuid

**Alternativas avaliadas:**
  - **`auth.jwt() ->> 'setor'` literal:** rejeitada (JWT nao tem o claim).
  - **Custom Access Token Hook + JWT enriquecido:** rejeitada para esta
    wave (toca config Auth + e mais arriscado — JWT mal formado quebra
    autenticacao).
  - **Manter helpers em schema `public`:** rejeitada apos advisor levantar
    6 WARN `*_security_definer_function_executable` (PostgREST expoe
    via `/rest/v1/rpc/` mesmo com REVOKE). Movido para `app_private`
    em RLS 012.

**Consequencias:**
  - Cada policy faz 1 lookup adicional contra `usuarios` (~5ms com
    indice UNIQUE em auth_uid). Aceitavel para volumes do projeto.
  - Funcoes STABLE permitem ao planner cachear resultado dentro de 1
    query.
  - Schema `app_private` nao listado em `db-schemas` do PostgREST
    (default permanece apenas `public`).
  - Follow-up futuro: avaliar Custom Access Token Hook se volume crescer.

## D-4 — Pagina inicial por perfil: Motorista -> `/escanear`, demais -> `/dashboard`

**Contexto:** o middleware antigo redirecionava qualquer authenticated
em `/login` para `/usuarios` hardcoded. Isso e bug para vendedor/motorista/clicheria,
que nao tem acesso a `/usuarios` (NEGADO na Matriz).

A Wave 1 v4.0 precisa decidir a pagina inicial por perfil para usar nos
redirects 302 quando acesso e negado.

**Decisao:** `home_by_profile` em `shared/access-matrix.json`:
  - **3Studio (admin)** -> `/dashboard` (visao consolidada).
  - **Vendedor** -> `/dashboard` (contadores filtrados pelo seu escopo).
  - **Motorista** -> `/escanear` (atividade primaria do motorista e
    escanear QR; dashboard e secundario).
  - **Clicheria** -> `/dashboard` (visao do que esta chegando).

**Alternativas avaliadas:**
  - `/dashboard` para todos: rejeitada — para Motorista o uso primario
    e escanear, dashboard nao traz acao imediata.

**Consequencias:**
  - Apos login, cada perfil cai na pagina mais util para sua rotina.
  - Em caso de redirect por acesso negado, o destino tambem respeita
    essa preferencia.
  - Se o solicitante preferir uniformizar em `/dashboard`, basta
    alterar 1 entrada no `home_by_profile` do JSON.

## D-5 — `access_required(rule_key)` factory mantem compat com tests legacy

**Contexto:** ~30 endpoints existentes usavam `Depends(get_admin_user)`.
Os tests sobrescrevem `app.dependency_overrides[get_admin_user] = lambda: admin`.
Trocar `Depends` em massa quebraria todos os tests.

**Decisao:** `access_required(rule_key)` factory devolve `Depends` que
internamente chama `Depends(get_current_user)` + `enforce_access_for`.
Como os tests SEMPRE override `get_current_user` tambem, eles
funcionam sem alteracao — `access_required` recebe o user mockado e
chama `enforce_access_for("rule_key", user)` que valida via Matriz.

**Alternativas avaliadas:**
  - **Refatorar tests em massa para overrider `access_required(...)`:**
    rejeitada (cada chamada cria uma instancia diferente de Depends, override
    por instancia e fragil; alem disso, mudaria 200+ testes).
  - **Adicionar `enforce_access_for` no body do handler em vez de
    Depends:** rejeitada (perde o beneficio de o gating acontecer ANTES
    de qualquer outro Depends ser resolvido — ex.: `get_db`).

**Consequencias:**
  - Zero tests existentes alterados pelo refactor RBAC.
  - 36 testes novos especificos para a camada `app/access/`.
  - Padrao explicito: novos endpoints com chave da Matriz usam
    `access_required(rule_key)`; endpoints com invariantes de negocio
    nao mapeadas (RN-010 em users.py) continuam usando
    `get_admin_user` direto.


## D-6 — Validacao runtime FAIL FAST do JSON SSoT em ambos os lados

**Adicionada na sessao de Audit Fixes (2026-04-30, commit `ac3be70`).**

**Contexto:** auditoria pos-implementacao identificou (M-2 + M-3) que
tanto `_load_matrix` (Python) quanto `buildRules` (TypeScript)
aceitavam silenciosamente JSON com schema invalido — typo no `acesso`
(`'fulll'`), `acesso='parcial'` sem campo `scope`, `scope` com valor
fora do conjunto canonico, `acesso='full'/'negado'` com `scope`
indevido. Falhas so apareciam em runtime no `scope_filter_for` (else
final + `false()` defensivo) ou em deny silencioso no middleware,
mascarando bugs de configuracao da Matriz.

**Decisao:** validacao FAIL FAST no startup nos dois lados, com
mensagens explicitas que nomeiam os 3 pontos a atualizar quando um
novo `scope` for introduzido (matrix.py + scopes.py + access-matrix.ts).

  - Python (`backend/app/access/matrix.py`):
    `valid_scopes: frozenset[str] = frozenset({"self_vendedor",
    "status_motorista_em_transito", "status_clicheria"})`. Cada perfil
    de cada regra e validado: `parcial` exige `scope ∈ valid_scopes`;
    `full`/`negado` proibe `scope`. `ValueError` aborta o boot do
    processo FastAPI.
  - TypeScript (`frontend/src/lib/access-matrix.ts`): `VALID_ACESSOS`,
    `VALID_SCOPES`, `VALID_MATCHES` como `Set<...>`. `throw new Error`
    em `buildRules` aborta o build do Next.

**Alternativas avaliadas:**
  - **JSON Schema externo (ajv / pydantic):** rejeitada — overhead de
    dependencia para 4 invariantes simples. Validacao manual cabe em
    ~30 linhas em cada lado e mantem mensagens contextuais.
  - **Apenas validar em testes:** rejeitada — falha em runtime e mais
    visivel que falha em CI; e validacao em testes nao previne JSON
    quebrado em hotfix de producao.
  - **Soft-fail com `console.warn` + decision negado defensivo:**
    rejeitada — silenciosamente mascarar configuracao errada e exatamente
    o problema que esta wave tenta evitar (risco R-1 da analysis).

**Consequencias:**
  - 4 testes novos em `tests/access/test_matrix_structure.py`
    (`TestMatrixRuntimeValidation`) garantem comportamento na camada
    Python.
  - Total de testes backend: 761 (era 757 + 4).
  - Adicionar novo `scope` agora exige PR atomico atualizando os 3
    pontos — alinhado com o objetivo central da Wave 1 v4.0.


## D-7 — Decisao defensiva no middleware: trailing slash normalizado

**Adicionada na sessao de Audit Fixes (2026-04-30, commit `ac3be70`).**

**Contexto:** auditoria identificou (M-4) que `getRuleForPath` falhava
em paths com trailing slash:
  - `/provas/` nao bate em `match=exact path=/provas` (`!==`).
  - `/provas/` nao bate em `match=dynamic path=/provas/[id]`
    (`length === prefix.length` falha na condicao `>`).
  - `/provas/` nao bate em qualquer `match=prefix` (nenhum cobre).
  - Resultado: `null` -> middleware pass-through -> bypass do RBAC.

Em producao com Next.js 14 default `trailingSlash: false`, o framework
normaliza antes do middleware e o caso nao acontece. Mas a config pode
mudar (ex.: SEO leva a `trailingSlash: true`) e o bug ficaria latente.

**Decisao:** normalizar trailing slash no inicio de `getRuleForPath`
(uma linha defensiva) em vez de depender da config do Next:

```typescript
if (pathname.length > 1 && pathname.endsWith("/")) {
  pathname = pathname.slice(0, -1);
}
```

**Alternativas avaliadas:**
  - **Forcar `trailingSlash: false` no `next.config.js` e documentar:**
    rejeitada — configuracao runtime e fora do escopo da camada de
    logica de acesso; quebra encapsulamento.
  - **Estender cada `match` (exact/dynamic/prefix) com aceitacao de
    trailing slash:** rejeitada — duplicacao em 3 branches; mais
    superficie para bug.
  - **Normalizar tambem `/foo//bar`, query strings:** rejeitada —
    `pathname` ja chega sem query no middleware do Next; double-slash
    nao e gerado pelo App Router.

**Consequencias:**
  - 1 linha de codigo no `getRuleForPath`.
  - Smoke preview validou: `/auditoria` e `/auditoria/` (anonimos)
    ambos -> redirect `/login`. Comportamento identico.
  - Camada inferior (RLS) ja era invariante a trailing slash (so olha
    para queries SQL), entao paridade preservada.


# Wave 1 (v4.0) — Audit Round 2 (correcoes pos-auditoria senior)

Decisoes registradas durante a sessao de correcao do `audit-report.md`
(commit `09eaf78`). Branch `wave1-v4/fixes/execution`, 2026-05-04.
Cobre os 17 achados (0 CRITICO · 0 ALTO · 6 MEDIUM · 7 BAIXO · 4 INFO).

## D-8 — `_scoping_filter` mantido como shim (status formal de L-2)

**Adicionada na sessao de Audit Round 2 Fixes (2026-05-04).**

**Contexto:** AUD-W1V4-106 confirma o que ja estava registrado como
follow-up L-2 nos audit fixes anteriores: `_scoping_filter(user)` em
`backend/app/api/v1/provas.py:661` virou shim de 1 linha que delega
para `scope_filter_for("provas.list", user)` apos o refactor da Wave
1 v4.0. As ~7 chamadas internas em `provas.py` continuam usando o
shim em vez de chamar a API canonica diretamente.

A sessao revisitou esse status na corrida de correcoes pos-auditoria
e decidiu **MANTER o shim** conscientemente.

**Decisao:** registrar formalmente que `_scoping_filter` segue como
shim aceito ate uma wave futura ou quando outro motivo legitimo (ex.:
necessidade de refator de toda a camada de provas) justificar inline
das chamadas.

**Alternativas avaliadas:**
  - **Inline as 7 chamadas para `scope_filter_for("provas.list", user)`:**
    rejeitada nesta sessao — refator de codigo de Wave 2 fora do
    escopo "puro RBAC pos-auditoria". A Wave 1 v4.0 autorizou tocar
    Waves 0-6 estritamente para fins de RBAC; inlining e tech debt
    cleanup, nao RBAC.
  - **Renomear o shim para `_scope_provas_list(user)` (nome mais
    explicito):** rejeitada — mudaria o blame de 7 sites sem ganho
    pratico; o comentario novo no shim ja deixa explicito que ele e
    um shim que delega para `provas.list`.
  - **Eliminar o shim e quebrar callsites em pares:** rejeitada — o
    AUD-W1V4-105 ja criou `_scoping_filter_for_detail` (caminho de
    detalhe). Eliminar o shim de listagem aqui criaria 2 helpers
    inconsistentes (um inlinable, outro nao).

**Consequencias:**
  - Codigo continua identico ao pos-Audit Fixes (ac3be70).
  - Comentario no shim ja documenta o status (`USAR APENAS NO CAMINHO
    DE LISTAGEM` — adicionado pelo AUD-105).
  - Tech debt L-2 segue como follow-up tecnico explicito; uma wave
    futura pode revisitar quando o codigo de provas for refatorado
    por outro motivo.

## D-9 — Invariante: `dashboard` deve permanecer FULL para os 4 perfis

**Adicionada na sessao de Audit Round 2 Fixes (2026-05-04).**

**Contexto:** AUD-W1V4-201 (INFO) levantou a possibilidade de redirect
loop se algum dos 4 perfis tivesse `dashboard=negado` na Matriz —
porque `home_by_profile` para 3 dos 4 perfis e `/dashboard` (Motorista
e `/escanear`). Se `dashboard=negado` para vendedor (ex.), middleware
redirecionaria vendedor de qualquer rota para `homeForProfile(vendedor)
=/dashboard`, que tambem seria negado, gerando loop.

Hoje os 4 perfis tem `dashboard=full` no JSON SSoT — invariante
implicita.

**Decisao:** registrar como **invariante** que toda mudanca futura na
Matriz que altere `dashboard` para algo diferente de `full` precisa,
no mesmo PR, atualizar `home_by_profile` para nao apontar para
`/dashboard` no perfil afetado.

**Alternativas avaliadas:**
  - **Validacao automatica** (ex.: teste pytest que verifica essa
    invariante): boa ideia mas fora do escopo desta sessao. Registrado
    como follow-up tecnico.
  - **Trocar `home_by_profile` para path universal** (ex.: `/login` em
    vez de `/dashboard`): rejeitada — degrada UX em troca de
    invariante teorica.

**Consequencias:**
  - Sem mudanca de codigo. Invariante documentada.
  - Em PRs futuros que tocam a Matriz, revisor pode citar D-9.

## D-10 — "Registro orfao invisivel" aceito como improvavel

**Adicionada na sessao de Audit Round 2 Fixes (2026-05-04).**

**Contexto:** AUD-W1V4-202 (INFO) registrou que cenarios "registro com
FK para usuario deletado mas linha preservada por trigger de
imutabilidade" nao foram exaustivamente verificados em producao.

Cenario-alvo: uma `movimentacao` com `usuario_id` apontando para um
`usuarios.id` que ja foi excluido. Como `movimentacoes` tem trigger
de imutabilidade (BEFORE UPDATE OR DELETE), a linha persistiria. Como
`usuarios` tem FK enforcement (RESTRICT), o DELETE de usuario com
movimentacao referenciada e bloqueado pelo banco — entao o cenario
e **arquiteturalmente impossivel** sob as constraints atuais.

**Decisao:** aceitar a improbabilidade do cenario com base nas FKs
ON DELETE RESTRICT e triggers de imutabilidade. Nao verificar
exaustivamente nesta sessao.

**Alternativas avaliadas:**
  - **Auditoria periodica** (cron que conta orfaos): seria informativa
    mas o sinal positivo (zero orfaos) e o estado por construcao;
    sinal negativo seria red flag e merece investigacao manual.
  - **Trigger AFTER DELETE em usuarios** que verifica orfaos: rejeitada
    — duplica garantia ja dada por FK RESTRICT.

**Consequencias:**
  - Sem mudanca de codigo. Premissa documentada para revisores
    futuros.

## D-11 — Mudancas de RLS rastreadas via supabase_migrations + Git

**Adicionada na sessao de Audit Round 2 Fixes (2026-05-04).**

**Contexto:** AUD-W1V4-203 (INFO) sugeriu considerar geracao de
entrada em `audit_logs` para mudancas de RLS (controle de mudanca).

`audit_logs` e o log de DOMINIO da aplicacao (movimentacoes de provas,
mudancas de usuarios, eventos de transicao). Registrar mudancas de
SCHEMA/RLS la mistura concerns: domain audit vs DDL audit.

**Decisao:** mudancas de RLS sao rastreadas pelas duas fontes existentes:
  1. Tabela `supabase_migrations` (versionada pelo Supabase).
  2. Commits Git em `backend/migrations/rls/*.sql` (RLS 001 a 013).

Ambas as fontes sao audit-trails completas. Nao adicionar log
duplicado em `audit_logs`.

**Alternativas avaliadas:**
  - **Trigger `on_event_trigger ddl_command_end` para registrar
    mudancas de policy/role:** seria possivel, mas nao tem demanda
    declarada. Considerar se aparecer requisito de compliance no
    futuro.

**Consequencias:**
  - Sem mudanca de codigo. Premissa documentada.

## D-12 — Extracts dos `.docx` removidos pos-Gate 1 (AUD-W1V4-204)

**Adicionada na sessao de Audit Round 2 Fixes (2026-05-04).**

**Contexto:** AUD-W1V4-204 (INFO) registrou que os extracts em
`docs/wave1-v4/_extracted/*.md` foram removidos no closeout do Gate 2
da Wave 1 v4.0, e isso reduz a reprodutibilidade de auditorias
futuras (a auditoria atual teve que confiar em citacoes textuais e
em estruturas codificadas).

**Decisao:** **manter os extracts removidos**. A reprodutibilidade da
auditoria e garantida pelas seguintes fontes:
  - **Citacoes textuais da Secao 6 do Requisitos v4.0** em
    `docs/wave1-v4/analysis.md` Secao 3.
  - **Estrutura codificada** em `backend/tests/access/test_matrix_structure.py`
    (`EXPECTED_KEYS`).
  - **Notas de divergencia** em `shared/access-matrix.json`
    (`_clicheria_divergence_note`).
  - **Documentos canonicos** (`.docx`) em `Desktop/Rastreio Prova
    Digital/` no maquina do operador.

Restaurar os extracts seria duplicar conteudo em local nao-canonico
no repo. Rejeitado.

**Alternativas avaliadas:**
  - **Restaurar extracts em `docs/wave1-v4/_extracted/`:** rejeitada
    — duplicacao e drift potencial entre extracts e .docx.
  - **Mover .docx para o repo:** rejeitada — binario versionado,
    mantenedor (Renan) gerencia .docx fora do Claude Code.

**Consequencias:**
  - Auditorias futuras podem usar fontes acima.
  - Se um auditor demandar acesso aos .docx, pedir ao Mario/Renan.

## D-13 — Vitest minimo para o middleware (AUD-W1V4-005, Opção A)

**Adicionada na sessao de Audit Round 2 Fixes (2026-05-04).**

**Contexto:** AUD-W1V4-005 (MEDIUM) exigiu teste do middleware. O
frontend nao tinha test runner — `package.json` so declarava
`dev/build/start/lint`. Tres caminhos foram avaliados (vide
`docs/wave1-v4/fix-plan.md` §3.5):
  - **A.** Vitest minimo (preferida).
  - **B.** `node:test` built-in (cobertura parcial).
  - **C.** Deferred com justificativa (mantem L-1 follow-up).

O solicitante escolheu **A** na autorizacao do Gate 2.

**Decisao:** instalar Vitest 2.1.9 como devDependency unica + criar
`vitest.config.ts` minimo (env node, sem jsdom/coverage) + script
`"test": "vitest run"` + suite `frontend/src/lib/supabase/__tests__/middleware.test.ts`
com 15 testes. Nao instalar `@testing-library/react` nem `jsdom`
nesta sessao — superficie de dependencia minima.

**Alternativas avaliadas:**
  - **Vitest + Testing Library (cobertura de componentes):** rejeitada
    nesta sessao — escopo era apenas middleware. Pode ser adicionado
    em sessao futura se houver demanda.
  - **Jest + jsdom:** rejeitada — Vitest tem melhor integracao com
    Vite/Next 14 e Vitest 2.x e estavel.
  - **`node:test` built-in:** rejeitada apos avaliacao no Gate 1 —
    cobertura parcial nao satisfaz o achado promovido para MEDIUM.

**Consequencias:**
  - 1 nova devDependency (`vitest@^2.1.9`).
  - 2 novos arquivos: `vitest.config.ts` (~25 linhas) e `middleware.test.ts`
    (~250 linhas, 15 testes).
  - 2 novos scripts: `test`, `test:watch`.
  - `npm test` passa em ~400ms (transform 46ms + collect 79ms + tests 9ms).
  - `npm run lint` + `tsc --noEmit` + `next build` permanecem limpos.
  - Bundle do middleware nao muda (82.9 kB, identico ao pre-fix).
  - L-1 follow-up dos audit fixes anteriores cumprido.


---

## ADR-115 — Enum `rota_enum` em UPPERCASE
**Data:** 2026-05-04 (Wave 2 v4.0 — Componente 06)
**Contexto:** O DAT v3.0 §8 e o Backlog v4.0 (Componente 06 Notas Tecnicas)
sugerem nomes lowercase para os 4 novos valores (`'matriz'`, `'lam_matriz'`,
`'filial'`, `'lam_filial'`). No entanto, todos os outros enums do projeto
usam UPPERCASE: `setor_enum` (STUDIO/VENDEDOR/MOTORISTA/CLICHERIA),
`localizacao_enum` (MATRIZ/FILIAL), `status_prova_enum` (CRIADA/...).
Misturar lowercase no `rota_enum` quebraria a convencao.
**Decisao:** Adotar UPPERCASE para os 4 novos valores: `MATRIZ`,
`LAM_MATRIZ`, `FILIAL`, `LAM_FILIAL`. Documentar a divergencia explicita
em relacao ao DAT/Backlog literal.
**Alternativas:**
  - Lowercase conforme DAT (rejeitado: quebra consistencia com 3 outros
    enums em producao desde Wave 0).
  - Renomear todos os enums para lowercase (rejeitado: requer migration
    destrutiva em producao + impacto em todo o codebase).
**Consequencias:** convencao do projeto preservada. Documentado em
CLAUDE.md (secao "Como adicionar valor ao enum `rota_enum`") + em
analysis.md secao 3.2.

---

## ADR-116 — `codigo_publico` e coluna NOVA, nao reaproveita `qr_code_hash`
**Data:** 2026-05-04 (Wave 2 v4.0 — Componente 06)
**Contexto:** O backend ja tem `provas_digitais.qr_code_hash VARCHAR(64)
UNIQUE` (HMAC-SHA256 hex opaco — ADR-033). A v4.0 introduz necessidade de
um identificador HUMANO-LEGIVEL no formato `PRV-AAAA-MM-NNNNNN` para
fallback de digitacao manual (RF-005, Componente 19 da Wave 3 v4.0).
**Decisao:** Criar coluna NOVA `codigo_publico VARCHAR(20) UNIQUE NOT NULL`
em `provas_digitais`. NAO reaproveita `qr_code_hash` — naturezas
diferentes:
  - `qr_code_hash`: HMAC opaco, valida AUTENTICIDADE do scan, 64 chars hex.
  - `codigo_publico`: humano-legivel, resolve IDENTIFICACAO do registro,
    formato `PRV-AAAA-MM-NNNNNN` (18 chars).
O QR Code agora EMBUTE o `codigo_publico` no payload (segundo campo do
formato `3SD|...|hash`) — DAT v3.0 §8.1: idempotencia entre camera e
digitacao manual exige que ambos os mecanismos resolvam para o mesmo
registro pelo mesmo lookup.
**Alternativas:**
  - Reaproveitar `qr_code_hash` truncado (rejeitado: hash hex e
    inadequado para digitacao manual humana — chars 0/O/1/I/L causam
    erro frequente).
  - Reaproveitar `nro_requerimento` (rejeitado: livre-formato pelo
    admin, nao da garantia de unicidade nem entropia — risco de
    enumeracao).
**Consequencias:**
  - Migration 012 adiciona coluna + UNIQUE INDEX + backfill local das
    16 provas existentes.
  - QR Code payload muda de `3SD|nro_req|hash[:16]` para
    `3SD|codigo_publico|hash[:16]`.
  - `validar_payload_qr` flexibilizada — aceita ambos os formatos
    durante a transicao (Wave 3 v4.0 / Componente 19 escolhe o lookup
    apropriado em runtime).

---

## ADR-117 — Trigger de imutabilidade da rota permite NULL → valor
**Data:** 2026-05-04 (Wave 2 v4.0 — Componente 06)
**Contexto:** RN-002 v4.0 exige que a rota seja imutavel apos a criacao.
O trigger PostgreSQL bloqueia UPDATE da coluna `rota`. MAS:
  - Provas legadas v3.0 tem `rota = NULL` (11 em producao no momento
    da Wave 2 v4.0).
  - A Wave 7 (Componente 21) precisa fazer backfill: `NULL → valor`
    inferido da localizacao do vendedor.
  - Se o trigger bloquear `NULL → valor`, a Wave 7 falha.
**Decisao:** Trigger `trg_provas_rota_imutavel BEFORE UPDATE` com a
condicao `WHEN (OLD.rota IS DISTINCT FROM NEW.rota)` + corpo:
```sql
IF OLD.rota IS NOT NULL AND NEW.rota IS DISTINCT FROM OLD.rota THEN
    RAISE EXCEPTION 'Coluna rota e imutavel apos definicao (RN-002 v4.0)'
        USING ERRCODE = '22023';
END IF;
RETURN NEW;
```
Isso PERMITE `NULL → valor` (passa pela checagem `OLD.rota IS NOT NULL`)
e BLOQUEIA `valor → outro_valor` ou `valor → NULL`.
**Alternativas:**
  - Trigger sem checagem de NULL (rejeitado: bloqueia o backfill da
    Wave 7).
  - Trigger inteligente que detecta o "modo backfill" (rejeitado:
    estado adicional + complexidade desnecessaria — a propria
    permissao de NULL→valor ja serve).
**Consequencias:** 3 testes especificos cobrindo as 3 transicoes
(NULL→valor permitido; valor→outro_valor bloqueado; valor→NULL
bloqueado). Wave 7 / Componente 21 implementa o backfill sem
desabilitar o trigger.

---

## ADR-118 — Frontend: 2 toggles em vez de 4 radios para a rota
**Data:** 2026-05-04 (Wave 2 v4.0 — Componente 06)
**Status:** SUPERSEDIDO em 2026-05-05 pelo Visual Refresh v2 — adotado
1 segment de 4 botoes diretos (Matriz | Filial | Lam. Matriz | Lam.
Filial) alinhado ao novo design Figma entregue pelo Mario. O `FormState`
agora armazena `rota: RotaCriacao` direto. Ver CHANGELOG 2026-05-05
"Wave 2 v4.0 — Componente 06 — Visual Refresh v2".

**Contexto:** O `analysis.md` (Gate 1) propos 4 radio buttons na tela
de criacao para representar `MATRIZ / LAM_MATRIZ / FILIAL / LAM_FILIAL`.
O design entregue pelo Mario no Gate 2 (print) usa 2 controles
independentes:
  - Segment "Matriz / Filial" (radio button styled)
  - Switch "Laminacao" (boolean on/off)
**Decisao:** Adotar a solucao do design — 2 toggles na UI; deriva o
`RotaCriacao` no submit:
```ts
const rota = laminacao
  ? (origem === 'MATRIZ' ? 'LAM_MATRIZ' : 'LAM_FILIAL')
  : origem;
```
**Alternativas:**
  - 4 radios (rejeitado: visualmente carregado, exige o usuario ler
    todas as 4 labels para escolher uma).
  - Dropdown com 4 opcoes (rejeitado: esconde a estrutura semantica
    "matriz vs filial × com/sem laminacao").
**Consequencias:**
  - UX mais clara: usuario decide PRIMEIRO a unidade (Matriz ou Filial),
    DEPOIS se ha laminacao.
  - Modal de confirmacao dupla (proposto no analysis.md §4.8)
    descartado — os 2 toggles ja forcam escolha consciente.
  - Texto auxiliar "A rota escolhida e imutavel apos o cadastro"
    permanece como mitigacao do risco "Confusao operacional"
    (Backlog v4.0 §6).

---

## ADR-119 — Modificacao cirurgica em `state_machine.executar_transicao`
**Data:** 2026-05-04 (Wave 2 v4.0 — Componente 06)
**Contexto:** O `executar_transicao` (Wave 3 v3.0) em
`backend/app/services/state_machine.py` linha 365 sobrescrevia
`prova.rota = determinar_rota(usuario)` na transicao
`RETIRADA → APROVADA_PELO_VENDEDOR`. Isso colidia com o trigger
PostgreSQL `trg_provas_rota_imutavel` introduzido nesta wave (ADR-117) —
toda aprovacao de prova v4.0 falharia com SQLSTATE 22023.

**Bug observavel sem a correcao:** admin cria prova v4.0 com
`rota=MATRIZ` → vendedor MATRIZ aprova → trigger bloqueia o UPDATE
porque `executar_transicao` tenta sobrescrever para `PADRAO` (derivado
da localizacao). Aprovacao falha em producao no primeiro uso v4.0.

**Decisao:** Modificar 4 linhas em `executar_transicao` (linhas
358-373) para preservar `prova.rota` quando ja preenchida; derivar via
`determinar_rota(usuario)` apenas se `prova.rota IS NULL` (provas
legadas v3.0):
```python
if aprovando:
    if prova.rota is None:
        rota_depois = determinar_rota(usuario)  # legacy v3.0
    else:
        rota_depois = prova.rota  # imutavel — Wave 2 v4.0
```
**Autorizacao explicita do Mario** registrada na Secao 14 do
`analysis.md` antes da execucao.

**Alternativas:**
  - Trigger menos rigoroso (rejeitado: derived_value PADRAO/DIRETA
    nunca bate com MATRIZ/LAM_MATRIZ/etc — trigger ficaria sem efeito).
  - Cindir a Wave 2 v4.0 em 2 sessoes para nao tocar state_machine
    (rejeitado: sem essa correcao, a regra de imutabilidade da wave
    e violada na primeira aprovacao — bug em producao).
  - Reescrever toda a state machine v4.0 nesta sessao (rejeitado:
    isso e Wave 3 v4.0 / Componente 11 — fora do escopo).

**Consequencias:**
  - Provas v4.0 (com rota persistida) tem aprovacao funcional sem
    erros de trigger.
  - Provas legadas v3.0 (rota=NULL) continuam tendo rota derivada na
    aprovacao (comportamento v3.0 preservado) ate a Wave 7
    (Componente 21) fazer o backfill final.
  - Wave 3 v4.0 (Componente 11) reescreve `executar_transicao` por
    inteiro com a tabela de transicoes ampliada para 14 estados.

---

## ADR-120 — Substituir RotaVisualization decorativo por EtiquetaPreview funcional
**Data:** 2026-05-05 (Wave 2 v4.0 — Visual Refresh)
**Status:** SUPERSEDIDO em 2026-05-05 pelo Visual Refresh v2 — o
`EtiquetaPreview` SVG inteiro foi removido da tela de criacao porque o
novo design Figma do Mario nao tem coluna direita (1 box branco unico
ocupa toda a area). A tela de sucesso continua mostrando o PDF real via
iframe — esse e o preview funcional final. Os arquivos
`frontend/public/etiqueta/logo_*.svg` tambem foram removidos por ja
nao serem referenciados. Ver CHANGELOG 2026-05-05 "Visual Refresh v2".

> **Pos-supersedimento (Wave 2 v4.0 Audit Fixes — AUD-W2V4-M04):** o
> Visual Refresh v2 ELIMINOU a duplicacao dos logos
> (`backend/app/services/etiqueta_assets/logo_*.svg` ↔
> `frontend/public/etiqueta/logo_*.svg`) descrita nas "Consequencias"
> abaixo. A pasta `frontend/public/etiqueta/` foi DELETADA junto com
> o componente `EtiquetaPreview`. **Estado atual: apenas
> `backend/app/services/etiqueta_assets/` permanece como fonte de
> verdade dos logos** (usado pelo `etiqueta_service.gerar_pdf`). A
> "Trade-off de fidelidade" (preview sem codigo publico/badge) e a
> recomendacao de "step de build" deixaram de ser relevantes — nao
> ha mais preview frontend a manter sincronizado.

**Contexto:** A entrega original da Wave 2 v4.0 (sessao 2026-05-04)
incluiu um componente `RotaVisualization` na coluna direita da pagina
`/nova-prova` — um SVG decorativo de ~150 linhas que desenhava 4 nos
(ORIGEM, MATRIZ, FILIAL, LAMINACAO) conectados por curvas Bezier
animadas com framer-motion (morph paths, halo amarelo pulsante,
caminho alternativo tracejado, ícones SVG nos dots, etc — ver as
features R1+R3+R4+R5+R6+R7 do refresh visual em CHANGELOG).

Apos varias rodadas de feedback do Mario, o componente foi
considerado **decorativo sem funcao operacional clara** — "feio" e
"sem proposito" foram as palavras dele. A area da coluna direita
estava sendo desperdicada com algo que nao agregava valor.

**Decisao:** Substituir o `RotaVisualization` por uma `EtiquetaPreview`
— um SVG inline com `viewBox="0 0 90 57"` (mm reais) que **replica fielmente
o layout da etiqueta 90×57mm que sai impressa**, espelhando
`backend/app/services/etiqueta_service.py` mm-a-mm:
- Linha horizontal superior (y=3, stroke 0.4mm)
- Logos reais (`logo_3studio.svg` em x=4/y=8/w=22 e
  `logo_studio_e_arte.svg` em x=28.5/y=6.5/w=13) — copiados de
  `backend/app/services/etiqueta_assets/` para
  `frontend/public/etiqueta/` para servir como `<image href="...">`
- "Aponte a camera / para o QR CODE" em x=72.5/y=9 (centro do bloco
  de texto que tem largura 29mm desde x=58)
- Banner preto horizontal (x=3, y=16, w=44, h=2)
- Campos Nome / Requerimento / Vendedor em y=26/31.6/37.2
  (espacamento 5.6mm igual ao multi_cell do backend)
- QR placeholder vazio (apenas o quadrado em x=58/y=15/w=26 com
  cantos arredondados rx=2.8 e stroke 0.4) — sem conteudo dentro
  porque o QR real so existe no PDF impresso
- "2026" em x=3/y=51.85 (font 3mm = 8.5pt)
- "Etiqueta de rastreio" em x=87/y=51.85 com `text-anchor=end`
- Linha horizontal inferior em y=54

**Iteracao apos primeiro draft:** A primeira versao do EtiquetaPreview
incluia o codigo publico (`PRV-AAAA-MM-NNNNNN` em mono bold abaixo do
QR) e um badge preto da rota ao lado do "2026" — espelhando 100% do
PDF. Apos referencia visual da etiqueta real impressa enviada pelo
Mario, esses dois elementos foram REMOVIDOS do preview porque a
etiqueta impressa em producao na 3Studio nao os tem (estao no PDF
gerado mas nao na versao final que vai pro cliente). Assim o preview
fica fiel a etiqueta REAL, nao ao PDF teorico.

**Live update:** Os campos Nome/Requerimento/Vendedor sao passados
como props ao `EtiquetaPreview` e atualizam em tempo real conforme
o usuario digita na ficha (sem precisar submeter). Vendedor e
resolvido via `vendedores.find(v => v.id === form.vendedor_id)?.nome`.
Nomes longos sao truncados (32/18/24 chars com ellipsis) para nao
explodir o layout do SVG.

**Wrapper visual:** Container `.etiquetaPaper` com `aspect-ratio: 90/57`
mantem proporcao independente do viewport; **cantos vivos** (etiqueta
impressa nao tem cantos arredondados); sombra projetada multi-layer
(hairline 0.5px + 1px close + 12px mid + 28px deep ambient) para dar
sensacao de "papel sobre a mesa" sem ser dramatico. O `.etiquetaWrap`
tem gradient radial amarelo bem sutil
(`color-mix(in srgb, var(--color-accent) 12%, transparent)`) ao redor
para destacar a etiqueta sem competir.

**Alternativas consideradas (e rejeitadas):**
1. **Cartao da rota (Apple-minimalista)** — um card unico grande com
   tipografia gigante mostrando "Lam. Matriz" + decoracao gradient.
   Rejeitado: muito generico, nao agrega contexto operacional.
2. **Grid 2×2 das 4 rotas** — quadrados com as 4 combinacoes,
   destacando a selecionada via `layoutId`. Rejeitado: redundante
   com o segment + switch da ficha que ja faz isso.
3. **Manter RotaVisualization** com refinamentos visuais (glow neon,
   layout estilo garfo, etc). Rejeitado: o problema fundamental e
   que e decorativo — refinar o decorativo nao resolve o problema
   da falta de funcao.
4. **EtiquetaPreview Apple-minimalista** (cartao branco com cantos
   super arredondados, header logo + ano, QR estilizado, codigo
   publico em destaque, badge da rota) — primeira tentativa.
   Rejeitado pelo Mario apos screenshot porque nao parecia a
   etiqueta real.

**Consequencias:**
- A coluna direita agora tem **valor funcional concreto**: o usuario
  ve o que vai ser impresso antes mesmo de submeter.
- Logos reais da empresa aparecem (vetoriais, escalam perfeito).
- Trade-off de fidelidade: como removemos codigo publico e badge
  da rota do preview (a pedido), o preview NAO mostra 100% do que
  o PDF tera. Documentar essa diferenca no proprio JSX como
  comentario para futuro mantenedor nao se confundir.
- Bundle: `/nova-prova` em ~9.18 kB / 211 kB First Load (era 6.34
  kB / 169 kB) — overhead aceitavel pelo valor funcional.
- Logos `logo_3studio.svg` e `logo_studio_e_arte.svg` agora vivem
  em DOIS lugares: `backend/app/services/etiqueta_assets/` (fonte
  para o PDF) e `frontend/public/etiqueta/` (copia para o preview).
  Se o backend trocar os logos no futuro, precisa COPIAR a versao
  nova para o frontend tambem. Considerar simbolico ou step de
  build no futuro se isso virar incomodo.

---

## ADR-121 — Topbar `position: absolute` para ficha estender ate o topo
**Data:** 2026-05-05 (Wave 2 v4.0 — Visual Refresh)
**Status:** SUPERSEDIDO em 2026-05-05 pelo Visual Refresh v2 — a topbar
`absolute` foi substituida por um `.pageHeader` em flow normal (espelho
do padrao de /usuarios e /provas: titulo grande a esquerda + botao
amarelo a direita). O design novo do Mario tem header de pagina
explicito acima do box branco, entao a justificativa original
("ficha estende ate o topo") deixou de fazer sentido. Ver CHANGELOG
2026-05-05 "Visual Refresh v2".

**Contexto:** Apos remover os 2 cards laterais (Unidade Selecionada
+ Cole Imagem), a coluna direita ficou com mais espaco para o
preview da etiqueta. O Mario solicitou que **a ficha (esquerda)
crescesse em altura ate o topo dos botoes**, ficando "centralizada
ao centro na altura". O layout original era flex column com:
- `<motion.header className={topbar}>` — botao Cadastrar prova,
  ocupava ~50px na altura
- `<main className={layout}>` — grid 2 colunas com ficha e SVG,
  abaixo da topbar com `gap: 1rem` (16px)

Resultado: a ficha comecava 66px abaixo do topo do canvas, deixando
espaco vazio no topo da coluna esquerda enquanto o botao "Cadastrar
prova" ficava no canto superior direito.

**Decisao:** Tirar a topbar do flow flex e posicionar como `absolute
top: 0; right: 0; z-index: 2` no `.canvas`. Isso libera o `.layout`
para ocupar 100% da altura do canvas (height: 100% do `.cardInner`
do dashboard). A ficha (`.ficha { justify-content: center }`)
estende ate a mesma linha do topo do botao, e o conteudo vertical
fica centralizado.

**Por que `absolute` e nao algo mais elaborado (overlap controlado,
grid spans, etc):**
- A topbar nao precisa ocupar espaco na esquerda — ela so tem o
  botao "Cadastrar prova" no canto superior direito.
- Com `position: absolute`, o botao fica **POR CIMA** do SVG da
  EtiquetaPreview (na coluna direita), mas como o SVG ocupa apenas
  ~540px max-width centralizado e o botao tem ~150px no canto, eles
  nao se sobrepoem visualmente em viewports normais (>=1024px).
- A ficha (coluna esquerda) ocupa 380px e nunca interfere com o
  botao no canto direito.
- Solucao mais simples que valeu o trade-off.

**Trade-off:** Em viewports muito estreitos (<800px efetivos no
`.cardInner`), o botao pode ficar parcialmente sobre a etiqueta.
Mitigacao: a media query `@media (max-width: 1100px)` ja colapsa o
grid para 1 coluna e a etiqueta vira o item de baixo — o botao no
topo ocupa o flow normal. Mobile (`<768px`) mostra `.mobileNotice`
de qualquer jeito.

**Alternativas consideradas:**
1. **Topbar dentro do grid como linha 0 spanning 2 colunas** —
   funciona mas exige `display: grid` no canvas com `grid-template-rows`
   adicional, aumentando complexidade do layout. Rejeitado.
2. **Ficha dentro de container com margin-top negativo** — gambiarra,
   quebra o flow normal. Rejeitado.
3. **Manter topbar no flow e simplesmente reduzir gap** — nao resolve
   o problema (ficha ainda fica abaixo da topbar).

**Consequencias:**
- Layout mais simples e elegante.
- Ficha agora usa altura toda do canvas (com `justify-content:
  center` para centralizar conteudo verticalmente).
- Botao "Cadastrar prova" sempre visivel no canto superior direito.
- `.canvas` perdeu `gap` (nao tem mais flow gap pra cuidar entre
  topbar e layout).

---

## ADR-122 — Type guard `isAllowedImageType` em vez de cast `as readonly string[]`
**Data:** 2026-05-05 (Wave 2 v4.0 — Visual Refresh)
**Contexto:** O Mario explicitamente pediu "zero `any` e `as`
agressivos". O codigo da Wave 2 v4.0 original tinha 2 `as` agressivos:
1. `(ALLOWED_IMAGE_TYPES as readonly string[]).includes(file.type)`
   em `nova-prova/page.tsx` e em `useCreateProva.ts` — necessario
   porque `ALLOWED_IMAGE_TYPES` e `readonly ["image/jpeg",
   "image/png"]` e `Array.includes` requer que o argumento seja do
   tipo do array (TS 4.6 narrow check), entao precisa-se de cast
   para fazer o check funcionar com `string` qualquer.
2. `const target = e.target as HTMLElement | null` no paste handler
   do `<input>` — necessario porque `Event.target` e `EventTarget |
   null` e `EventTarget` nao tem `tagName` para verificar se e
   INPUT/TEXTAREA/SELECT.

**Decisao:** Eliminar ambos os `as` agressivos via duas tecnicas:

1. **Type guard `isAllowedImageType`** (em `lib/types/prova.ts`):
   ```ts
   export type AllowedImageType = (typeof ALLOWED_IMAGE_TYPES)[number];

   export function isAllowedImageType(value: string): value is AllowedImageType {
     for (const allowed of ALLOWED_IMAGE_TYPES) {
       if (allowed === value) return true;
     }
     return false;
   }
   ```
   Uso: `if (!isAllowedImageType(file.type)) return ...` — sem cast.
   O type predicate (`value is AllowedImageType`) faz o narrowing
   tipado a partir do retorno booleano.

2. **`instanceof` checks** no paste handler:
   ```ts
   if (
     target instanceof HTMLInputElement ||
     target instanceof HTMLTextAreaElement ||
     target instanceof HTMLSelectElement
   ) {
     return;
   }
   ```
   `instanceof` ja faz narrowing nativamente — sem precisar de
   cast. Cobertura igual a antiga via `tagName`.

**Politica resultante (Wave 2 v4.0 Visual Refresh):**
- **Zero `any`** (implicit ou explicit) em codigo novo.
- **Zero `as` agressivos** (`as <SomeType>`, `as readonly`,
  `as typeof`).
- **`as const` literais permanecem permitidos** (decisao do Mario)
  — ex: `["MATRIZ", "FILIAL"] as const`, `[0.32, 0.72, 0, 1] as const`,
  `{key: value} as const`. Nao sao "casts" de fato — sao
  type-narrowing nativo do TS para tipos literais.
- Verificacao via grep:
  `grep -nE '\bas [A-Z]| as readonly| as typeof'` em qualquer
  arquivo modificado deve retornar APENAS `as const` literais.

**Alternativas consideradas:**
1. **Manter o cast** — rejeitado por desejo do Mario.
2. **`@ts-ignore`** — pior, esconde tipos sem fix.
3. **Reescrever `ALLOWED_IMAGE_TYPES` como `Set<string>`** — perde
  o type-literal de "image/jpeg" | "image/png" e a narrowability.
4. **Type guard fora de `lib/types/prova.ts`** — rejeitado, o
  helper esta colado com a constante e e exportado junto para reuso.

**Consequencias:**
- Codigo mais seguro tipo-wise (sem casts que podem mentir).
- `useCreateProva` tambem foi atualizado (1 linha) para usar o
  helper — defesa em profundidade preservada.
- Politica vale para todo trabalho frontend futuro nesta Wave e
  proximas.


---

## ADR-123 — Reinicio de ciclo preserva rota (RN-006 v4.0 + RF-009 v4.0)
**Data:** 2026-05-05 (Wave 2 v4.0 Audit Fixes)
**Resolve:** AUD-W2V4-001 + AUD-W2V4-A01 + AUD-W2V4-006 + AUD-W2V4-007
**Contexto:** A modificacao cirurgica autorizada por Mario na Wave 2
v4.0 (ADR-119) cobriu apenas o ramo `aprovando` de
`state_machine.executar_transicao`. O ramo `reiniciando_ciclo` (linhas
377-384) continuou zerando `prova.rota = None`, o que entra em
conflito direto com o trigger `trg_provas_rota_imutavel` (ADR-117)
para qualquer prova com rota nao-NULL — disparando SQLSTATE 22023
no UPDATE da rota e fazendo o endpoint `POST /provas/{id}/reiniciar-
ciclo` retornar 502.

A regressao afetava (a) toda prova v4.0 reprovada (rota=MATRIZ/
LAM_MATRIZ/FILIAL/LAM_FILIAL), (b) provas legacy com rota=PADRAO/
DIRETA (5 provas em producao no momento). Apenas provas legacy com
rota=NULL nao eram afetadas (porque o UPDATE NULL->NULL nao dispara o
trigger).

Alem do bug HTTP 502, isso bloquearia indiretamente a Wave 7
(Componente 21): qualquer fluxo que envolvesse re-executar a state
machine apos backfill quebraria.

**Decisao:** completar a modificacao cirurgica do ADR-119 para o ramo
`reiniciando_ciclo` — substituir `rota_depois = None` por
`rota_depois = rota_antes`. Isso preserva rota imutavel em todos os
3 cenarios (v4.0, legacy nao-NULL, legacy NULL):
```python
if reiniciando_ciclo:
    ciclo_depois = ciclo_antes + 1
    rota_depois = rota_antes  # AUD-W2V4-001 fix
    acao_audit = "reiniciar_ciclo"
```

O audit log do reinicio (`detalhes_json`) agora grava
`rota_depois = rota_antes.value` (ou None se legacy NULL) em vez do
None hardcoded antigo — mudanca de contrato silenciosa documentada
em AUD-W2V4-007. O contrato novo e mais honesto: o log refletia algo
que nao acontecia (zeramento) por causa do bug; agora reflete a
preservacao real.

**Alternativas:**
  - Reverter o trigger para permitir valor->NULL em reinicio
    (rejeitado: quebraria a invariante RN-002 v4.0 da imutabilidade
    da rota; admin nao deve conseguir contornar via reinicio).
  - Detectar reinicio no trigger via context variable
    (rejeitado: complexidade desnecessaria; a state machine ja
    decide a semantica e pode preservar a rota deliberadamente).
  - Esperar a Wave 3 v4.0 (Componente 11) reescrever a state machine
    inteira (rejeitado: sem o fix, reinicio quebra ja para 5 provas
    legacy E para qualquer prova v4.0 — bug em producao precisa de
    fix imediato).

**Consequencias:**
  - Reinicio de ciclo funcional para todas as provas (v4.0, legacy
    nao-NULL, legacy NULL).
  - Wave 7 continua viavel (state machine nao quebra apos backfill).
  - Audit log consistente (rota_depois reflete o que de fato
    aconteceu).
  - Testes ajustados em test_state_machine.py (1 alterado + 2 novos
    para v4.0 e legacy NULL); test_provas_api.py 1 ajustado
    (test_reiniciar_happy_prova_reprovada agora espera rota
    preservada). Validacao integrada com banco real em
    test_imutabilidade_rota.py (AUD-W2V4-T01 — cenario 5).

---

## ADR-124 — Default rota vazio + texto auxiliar (mitigacao "Confusao operacional")
**Data:** 2026-05-05 (Wave 2 v4.0 Audit Fixes)
**Resolve:** AUD-W2V4-A02 + AUD-W2V4-M03
**Contexto:** O Backlog v4.0 §6 lista o risco "Confusao operacional"
— admin pode submeter prova com rota errada e descobrir tarde
(imutabilidade RN-002). A mitigacao original proposta pelo analysis.md
§4.8 era um modal de confirmacao dupla apos o submit (reapresentando
a rota escolhida). O ADR-118 SUPERSEDIDO descartou o modal alegando
que "os 2 toggles forçam escolha consciente", mas o Visual Refresh v2
(que SUPERSEDIU o ADR-118) voltou para 4 botoes diretos com
default `INITIAL_FORM.rota = "MATRIZ"`, removendo o argumento
original. O texto auxiliar "rota imutavel" tambem foi removido no
Polish round 1.

Resultado pos-Wave 2 v4.0: ZERO mitigacao do risco operacional
documentado pelo Backlog. Admin podia submeter rapido sem prestar
atencao, e o default `MATRIZ` agravava — qualquer prova de FILIAL
criada por descuido nasce errada e e imutavel.

**Decisao:** mitigacao substituta em duas partes:
  1. Default `INITIAL_FORM.rota = ""` (string vazia) — forca admin
     a clicar em uma das 4 rotas conscientemente. Tipo do
     `FormState.rota` muda de `RotaCriacao` para
     `RotaCriacao | ""`. `canSubmit` bloqueia envio enquanto
     `rota === ""`. `handleSubmit` faz narrowing explicito
     (`form.rota !== ""`) antes de passar para `submit({rota:
     RotaCriacao})`.
  2. Texto auxiliar "A rota escolhida e imutavel apos o cadastro"
     restaurado abaixo do segment de rotas, em tom muted
     (`color: var(--color-card-text-muted)`, `font-size: var(--fs-xs)`).
     Pequeno, sem chamar atencao excessiva — apenas um nudge
     informativo.

Backend nao mudou: `RotaCriacaoEnum` Pydantic continua exigindo um
dos 4 valores v4.0; envio com "" resultaria em 422, mas `canSubmit`
ja bloqueia antes do request. Defesa em profundidade preservada.

**Alternativas:**
  - Modal de confirmacao (a original do analysis.md §4.8) —
    rejeitado: introduz friccao em fluxo frequente (admin cria varias
    provas/dia); o nudge passivo + bloqueio do default e mais
    proporcional ao risco.
  - Manter default `MATRIZ` + adicionar so o texto auxiliar
    (rejeitado: o texto sozinho nao impede submit rapido; o admin
    le e clica antes de processar).
  - Default vazio sem texto auxiliar (rejeitado: bloqueia submit
    mas nao explica POR QUE a rota importa; sem texto, parece
    apenas mais um campo obrigatorio).

**Consequencias:**
  - `/nova-prova` 6.84 kB / 209 kB First Load (+50 bytes vs sem hint).
  - tsc --noEmit exit 0; next build 13/13 paginas — sem regressao.
  - Quem ler ADR-118 SUPERSEDIDO entende o trade-off do "switch
    forçava escolha" foi resolvido por outra via aqui.
  - Smoke E2E manual obrigatorio antes do merge para `main` valida
    o novo fluxo (AUD-W2V4-T04).

---

## ADR-125 — `STATUS_LABELS["CRIADA"]` = "Aguardando vendedor"
**Data:** 2026-05-06 (Wave 2 v4.0 / Componente 08)
**Contexto:** O Figma do Mario para a pagina de detalhe (`/provas/[id]`)
mostra o campo "Status" com valor "Aguardando vendedor" para uma prova
em estado `CRIADA`. O label antigo era apenas "Criada" — descreve a
transicao tecnica de insercao mas nao orienta o usuario sobre a acao
pendente. Mario respondeu "e a mesma coisa" quando questionado, dando
sinal verde para adotar o novo label.

**Decisao:** mudanca **global** em `frontend/src/lib/types/prova.ts`:
  - `STATUS_LABELS["CRIADA"] = "Aguardando vendedor"` (era "Criada").
  - `STATUS_LABELS_SHORT["CRIADA"] = "Aguardando"` (era "Criada"),
    para a coluna Status da listagem onde o espaco e limitado.

A mudanca afeta 6 lugares fora do detalhe: `escanear/page.tsx`
(label do status atual + transicoes), `provas/page.tsx` (filtro Status
+ tabela via `STATUS_LABELS_SHORT`), `provas/[id]/Timeline.tsx`
(label do no), `relatorios/perspectivas/ReportGeral.tsx` (graficos +
breakdown), `relatorios/StatusFilter.tsx` (opcoes do filtro). Em
todos esses lugares, "Criada" passa a ser exibido como
"Aguardando vendedor" (ou "Aguardando" curto). Semantica idêntica;
apenas a UX-string muda.

**Alternativas:**
  - Criar `STATUS_LABELS_DETALHE` que sobrescreve só "CRIADA" no
    detalhe, mantendo "Criada" em todos os outros lugares — rejeitado:
    fragmenta o vocabulário e cria inconsistência cross-page para o
    usuario.
  - Mudar o enum no banco (`StatusProvaEnum.CRIADA` ->
    `AGUARDANDO_VENDEDOR`) — rejeitado: quebra a Wave 3 v4.0 que
    expandira a maquina de estados para 14 estados; muda contrato
    com banco e auditoria; o nome do enum descreve a transicao
    tecnica e nao precisa virar texto de UX.

**Consequencias:**
  - Reversivel em 1 linha caso Mario reconsidere.
  - tsc --noEmit exit 0; next build 13/13 paginas; sem regressao.
  - Documentado neste ADR para que futuros mantenedores entendam que
    "Criada"/"Aguardando vendedor" representam o mesmo estado.

---

## ADR-126 — Rotas legacy v3.0 sem sufixo "(legada v3.0)"
**Data:** 2026-05-06 (Wave 2 v4.0 / Componente 08)
**Contexto:** O Figma mostra "Rota direta" como valor exemplo do campo
"Rota". Antes desta entrega, `ROTA_LABELS["DIRETA"]` retornava
"Filial (legada v3.0)" — informativo mas verboso, e desalinhado com a
estetica limpa do Figma. Mario aprovou explicitamente: "vamos mudar os
nomes das rotas para matriz, filial, lam. matriz, lam. filial — isso
esta planejado nessa nova versao de backlog".

**Decisao:** simplificar os labels dos 2 valores legacy:
  - `ROTA_LABELS["PADRAO"] = "Padrao"` (era "Matriz (legada v3.0)").
  - `ROTA_LABELS["DIRETA"] = "Direta"` (era "Filial (legada v3.0)").

Os 4 valores v4.0 (`MATRIZ`, `LAM_MATRIZ`, `FILIAL`, `LAM_FILIAL`)
permanecem inalterados ("Matriz", "Lam. Matriz", "Filial",
"Lam. Filial").

Consequencia esperada: provas legacy `rota=PADRAO` aparecem visualmente
como "Padrao" (sem indicacao explicita de que sao legacy v3.0). A
distincao continua disponivel via:
  - O enum no banco (`PADRAO` vs `MATRIZ`).
  - A Wave 7 (Componente 21) que fara o backfill final.
  - Cobertura de testes (`test_rota_enum_drift.py`) que monitora as
    duas familias.

**Alternativas:**
  - Manter sufixo "(legada v3.0)" — rejeitado: ruido visual em prol
    de informacao que o admin nao precisa no fluxo cotidiano.
  - Renomear `PADRAO` -> `"Matriz"` e `DIRETA` -> `"Filial"` — rejeitado:
    mistura visualmente legacy e v4.0 (impossivel distinguir uma prova
    `rota=PADRAO` de `rota=MATRIZ` apenas pela UI). "Padrao"/"Direta"
    preserva ao menos o nome historico.

**Consequencias:**
  - Afeta 4 lugares fora do detalhe: `escanear/page.tsx`,
    `provas/page.tsx` (filtro Rota + coluna), `provas/[id]/Timeline.tsx`
    (badge de roteamento), `relatorios/RotaFilter.tsx` (filtro). O
    `.replace("Rota ", "")` em `RotaFilter.tsx` continua sendo
    no-op apos a mudanca (string nao tem prefix "Rota ").
  - Compatibilidade com Wave 7 preservada: o backfill atualiza o
    banco; quando uma prova legacy passar a `rota=MATRIZ`, o label
    naturalmente vira "Matriz".
  - tsc --noEmit exit 0; next build sem regressao.

---

## ADR-127 — Layout invertido do detalhe (arte esquerda · info direita) + grid 3x2 de metadata
**Data:** 2026-05-06 (Wave 2 v4.0 / Componente 08)
**Contexto:** O Figma do Mario inverte o layout que existia desde a
Wave 2 v3.0 (info esq + arte dir, 1.4fr / 380px). Novo layout: arte
esq (480px quadrado) + info dir (1fr). Hierarquia tipografica do
header tambem muda — "Requerimento: NNN" pequeno acima do nome
grande (antes o numero era titulo e o nome subtitulo). Metadata vira
grid 3 colunas x 2 linhas: Cliente | Rota | Criada em / Vendedor |
Ciclo Atual | Status (com Codigo aparecendo no slot 7 quando
disponivel).

**Decisao:** rewrite cirurgico em duas pecas:
  - `frontend/src/app/(dashboard)/provas/[id]/page.tsx`: estrutura
    JSX nova (arte primeiro, info depois), header com `<p>` pequeno
    + `<h1>` grande + `<hr>`, `<MetadataGrid>` inline com 7 itens
    (`Cliente`, `Rota`, `Criada em`, `Vendedor`, `Ciclo Atual`,
    `Status`, `Codigo`), banner de cancelamento em row separado
    quando presente, `<actionsRow>` com 2/3/4 botoes side-by-side.
  - `frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css`:
    `.innerCardGrid` com `grid-template-columns: minmax(0, 480px)
    minmax(0, 1fr)`; `.metaGrid` com `grid-template-columns:
    repeat(3, minmax(0, 1fr))`; `.actionsRow` com `flex-wrap: nowrap`
    + `flex: 1 1 0` por botao + `min-width: 0` + `white-space:
    nowrap` + truncamento com ellipsis (Mario explicitou que os
    botoes devem ficar na mesma linha, sem quebrar — modais
    position:fixed nao competem por slot); responsivo <= 1100px
    reduz metaGrid para 2 colunas e empilha o innerCardGrid.

Card preto do historico AGORA E SEPARADO do innerCard branco (antes
era aninhado dentro). Espelha o Figma e simplifica a hierarquia
visual.

Provas legacy `rota IS NULL` continuam exibindo "—" via `formatRota`
(decisao consolidada no C06 — preservada).

**Alternativas:**
  - Criar componentes `<MetadataGrid>` + `<MetadataItem>` em arquivos
    separados — rejeitado: complexidade incompatible com o uso
    pontual; inline em `page.tsx` mantem a pagina simples (regra
    "Don't add features beyond what the task requires").
  - Usar CSS Grid em `.actionsRow` com `repeat(auto-fit, minmax(0, 1fr))`
    para forcar largura igual — rejeitado: `auto-fit` colapsa para
    `min-content` em alguns casos. `flex` deu comportamento estavel
    para 2/3/4 botoes.
  - Manter `flex-wrap: wrap` com `flex: 1 1 220px` (proposta inicial
    desta sessao) — rejeitado: Mario explicitou "os 3 botoes irao
    ficar na mesma linha, sem quebrar linha". `nowrap` + `flex: 1 1 0`
    + `min-width: 0` cumpre a regra mesmo em viewports apertadas
    (a custo de truncamento com ellipsis no caso extremo de 4 botoes
    em viewport 768-900px).

**Consequencias:**
  - `/provas/[id]` 11.4 kB / 209 kB First Load (era ~10 kB).
  - tsc --noEmit exit 0; next build 13/13 paginas.
  - Card branco principal contem APENAS info + arte + acoes;
    historico passa a ser segunda secao independente abaixo.
  - Smoke visual humano obrigatorio antes do merge (sem auth no dev
    server, validacao programatica nao cobre o detalhe completo).

---

## ADR-128 — Active menu por prefix-match (destaque "Provas" em /provas/[id])
**Data:** 2026-05-06 (Wave 2 v4.0 / Componente 08)
**Contexto:** Antes do C08 v4.0, o item "Provas" do menu deixava de
ficar destacado quando o usuario clicava em uma linha da listagem e
chegava em `/provas/[id]` — porque a comparacao era estrita
(`pathname === item.href`, com href = "/provas"). Mario explicitou:
"a4, isso foi erro meu, essa parte vai continuar igual e destacando
o 'provas'". A correcao do destaque e parte do redesign do
Componente 08 v4.0.

**Decisao:** introduzir helper `isPathActive(pathname, href)` em
`frontend/src/app/(dashboard)/layout.tsx`:

```ts
function isPathActive(pathname: string, href: string | undefined): boolean {
  if (!href) return false;
  if (pathname === href) return true;
  return pathname.startsWith(href + "/");
}
```

A condicao `+ "/"` e essencial para evitar falsos positivos:
`pathname=/provas-other` NAO ativa `href=/provas`.

**Alternativas:**
  - Usar `pathname.startsWith(href)` sem o separador — rejeitado:
    ativaria `/provas-other` para `href=/provas`.
  - Hardcoded por item (`provas` sabe que precisa cobrir `/provas/*`)
    — rejeitado: nao escala para futuros sub-paths
    (ex.: `/relatorios/[xxx]`, `/auditoria/[xxx]`).

**Consequencias:**
  - `/provas` continua ativo em `/provas` (exato).
  - `/provas` agora tambem ativo em `/provas/abc-uuid` — comportamento
    desejado.
  - Mesma regra aplicada a TODOS os itens do menu — uniforme.
  - Sem regressao em pages que sao exact-match (Dashboard, Nova prova,
    Escanear, etc.) porque elas nao tem subpath.
  - Middleware bundle inalterado.
