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
