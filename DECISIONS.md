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
