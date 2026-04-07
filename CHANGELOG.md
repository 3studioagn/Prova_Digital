# Changelog

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
