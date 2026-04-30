# Rastreio de Provas Digitais

Sistema de rastreamento de provas digitais (artes graficas) para a 3Studio.
Acompanha o ciclo de vida completo: criacao, aprovacao, transporte e entrega a clicheria,
com QR Code, assinatura digital de cada movimentacao e auditoria imutavel.

---

## Progresso das Waves

| Wave | Status | Escopo | Sessoes |
|------|--------|--------|---------|
| **0 — Infra** | ✅ **COMPLETA** | Schema Postgres (6 tabelas de dominio + enums + triggers imutabilidade), RLS inicial, R2 bucket, keep-alive cron, CI/CD | 1 |
| **1 — Auth + RBAC** | ✅ **COMPLETA** (sign-off Sessao 6) | Supabase Auth (ES256 JWKS), CRUD de usuarios com saga auth↔DB, RLS `is_admin=true`, tela `/usuarios` | 1-6 |
| **2 — Nucleo do Dominio** | ✅ **COMPLETA** (sign-off Sessao 22 pos-auditoria externa) | Cadastro de prova + etiqueta + QR Code (C06), Listagem com filtros (C07), Detalhe + modal etiqueta/QR (C08), Configuracoes do sistema (C09) | 7-22 |
| **3 — Scanner + Transicoes** | ✅ **COMPLETA** + Review C11 + Auditoria Senior | Camera HTML5, scanner QR, assinatura digital, maquina de estados, reprovacao, roteamento, timeline visual (C12), cancelamento admin (C13), reinicio de ciclo admin (C14). Review C11: bugs stale error, canvas responsivo, modal fluido, entrada manual de codigo QR. Auditoria: 0 CRITICAL, 3 HIGH corrigidos (scan filter admin, getToken try/catch, focus trap modais) | 23+ |
| **4 — Dashboard + Atrasos** | ✅ **COMPLETA** + Auditoria Senior | Dashboard tempo real (RF-014, US-013) com layout Figma: 5 contadores (criadas hoje, com vendedor, aprovadas, na clicheria, atrasadas c/ breakdown por vendedor) + 2 atalhos rapidos. Query consolidada + cache TTL 5s (ADR-092). Calculo de atraso horas corridas (RN-008). Supabase Realtime (postgres_changes) + fallback polling 10s. Auditoria: 0 CRITICAL, 1 HIGH corrigido (click Na clicheria), 2 MEDIUM corrigidos (breakpoint mobile, GROUP BY), 2 LOW corrigidos (ValueError guard, CHANGELOG). ADR-094 | — |
| **5 — Relatorios + Atalhos** | ✅ **COMPLETA** + Visual Refresh + 2 rounds de Auditoria Senior | Componente 16 (Relatorios) + Componente 17 (Atalhos). Endpoint UNICO discriminado por scope (geral/3studio/vendedores/clicheria) com cache TTL 60s + ETag SHA-256 + Realtime invalidation (4 camadas, ~20x reducao queries) + bypass `?_force=1` (ADR-107). Frontend `/relatorios` com 4 perspectivas alinhadas ao design Mario, graficos SVG inline interativos (DonutChart com toggle ADR-108 + BarChart + TimeSeriesChart + Sparkline + DeltaBadge). 5 filtros UI completos por construcao (RotaFilter + StatusFilter + VendedorFilter + DateRangeFilter + SearchInput — RF-013, ADR-106). CSV streaming UTF-8 BOM com 4 datasets enriquecidos (taxas + tempo medio por vendedor — L-A1 Round 2) + audit `REPORT_EXPORTED`. Atalhos globais por teclado (g+s, g+p, g+r admin, ?) + 3º card "Acessar Relatorios" no dashboard. **Round 2 de auditoria senior** (2026-04-29) corrigiu H-A1 (Q4 do `_aggregate_geral` agora aplica filtros via JOIN + `_aplicar_filtros_provas`), M-A1 (Q5 do `_aggregate_3studio` cancelamentos_top tambem), M-F1 (a11y modal sem `aria-hidden` no overlay), L-A1 (CSV summary expoe taxas) e L-F1 (`useMemo` em visibleShortcuts) — ADR-109. ADRs 095-109 (095-101 closeout + 102-105 visual refresh + 106-108 audit Round 1 + 109 audit Round 2). Migration 010 (recovery) + 011 (clarify descricao). **639 testes** (era 424); 0 regressao. | 5.0-5.6 + Visual Refresh + Audit R1 + Audit R2 |
| **6 — Seguranca e Auditoria** | ✅ **COMPLETA** + UX iteration + Auditoria Senior | Componente 18 (Interface de Log de Auditoria) — RNF-005. 3 endpoints `/api/v1/audit-log` (listagem paginada com filtros, detalhe com `MovimentacaoSnapshot`, by-prova). Frontend `/auditoria` admin-only com filtros (busca, tipo_evento semantico, ator, periodo), drawer lateral com focus trap, atalho `g a`, badges coloridos por categoria (reprovacao/reinicio/cancelamento/criacao). RLS 008 (REVOKE INSERT/UPDATE/DELETE em `audit_logs` para `anon`/`authenticated` — defesa em profundidade RNF-005, terceira camada apos trigger e RLS deny-by-default). UX iteration pos-Gate 2: presets de data (Hoje/7d/30d/90d), tipo_evento (6 categorias semanticas), paginacao numerada com janela inteligente, sticky header, ordenacao clicavel, page size selector (whitelist + tiebreaker por id). Auditoria Senior (2026-04-29): 0 CRITICAL, 2 HIGH (focus trap + F401 unused), 4 MEDIUM (ruff I001 + Pydantic 422 + Pragma legacy + OUTERJOIN condicional), 4 LOW (shadowing id + magic number + label botao + catch silencioso) — todos corrigidos. ADRs 110-114. **724 testes** (era 633); 0 regressao. | — |
| **v4.0 W1 — RBAC Matriz** | ✅ **COMPLETA** | Componente 05 (atualizacao v4.0) — Matriz de Acesso por Perfil em 3 camadas independentes. SSoT em `shared/access-matrix.json` (12 regras x 4 perfis = 48 celulas). Camada Python: `backend/app/access/` (matrix + enforce + scopes + guards) + 36 testes. Camada Frontend: `lib/access-matrix.ts` + `lib/hooks/use-authorization.ts` + `components/Restricted` + `components/AuthToast` + middleware reescrito com lookup de perfil + cache LRU 30s + cookie `auth-toast` em redirect. Camada RLS: 4 migrations (009-012) — helpers SECURITY DEFINER em schema `app_private` (resolve advisor `*_security_definer_function_executable`) + rebase das 12 policies + extensao de `pol_etiquetas_select` para Motorista/Clicheria (lacuna L-RLS-1). Refactor coordenado: substituicao de `Depends(get_admin_user)` por `Depends(access_required(rule_key))` em audit_log/reports/configuracoes/users/provas; `_scoping_filter` delega para `scope_filter_for`; `require_role` removido. Frontend: guards proativos em /auditoria, /relatorios (promovido de reativo), /usuarios, /configuracoes, /nova-prova; layout consulta Matriz para esconder itens; `useGlobalShortcuts` deriva da Matriz. Validado via `scripts/verify_rbac_equivalence.py` em producao (3 camadas batem: admin 16/16, vendedor 0, motorista 0, clicheria 2). **757 testes** (era 724 + 36 novos - 3 removidos). Decisao a confirmar: Clicheria PARCIAL com scope `status_clicheria` mantida (Matriz literal diz FULL — registrado follow-up). | — |

**Estado atual do banco de producao:**
- `alembic_version = 011` (migration 011 aplicada no closeout da Wave 5, 2026-04-27 — ADR-099 cosmetica). Wave 6 nao criou Alembic. Wave 1 v4.0 nao criou Alembic.
- **6 tabelas de dominio** + `alembic_version` (todas com RLS habilitada)
- **Schema `app_private`** (Wave 1 v4.0, RLS 012): 3 funcoes helper SECURITY DEFINER `current_user_is_admin()` / `current_user_setor()` / `current_user_id()` referenciadas pelas 12 policies. Schema NAO listado em `db-schemas` do PostgREST (nao exposto via REST).
- **12 policies RLS** reescritas na Wave 1 v4.0 usando os helpers. Cobertura semantica preservada vs RLS 005/006; `pol_etiquetas_select` estendida para incluir Motorista (status COM_MOTORISTA) e Clicheria (clicheria-states) — fecha lacuna L-RLS-1.
- **`audit_logs` com 3 camadas de defesa** (RNF-005): trigger `trg_audit_logs_imutavel` (Wave 0) + RLS deny-by-default `pol_audit_select` admin-only (Wave 0/1/2) + REVOKE GRANT-level INSERT/UPDATE/DELETE para `anon`/`authenticated` (Wave 6, RLS 008 — ADR-112). `service_role` mantem GRANT.
- **32 indexes** cobrindo filtros dos Componentes 07 + relatorios da Wave 5 (migration 010: +`idx_provas_vendedor_status` +`idx_movimentacoes_status_novo_created_at` — ADR-095). Wave 6 nao criou indice (4 indices em `audit_logs` ja cobrem; advisor `unused_index` deve cair conforme uso real).
- **3 usuarios ativos**: 2 admins (`admin@3studio.com.br` + `ops@3studio.com.br`) + 1 vendedor FILIAL (`mariosouza@teste.com.br`)
- **Advisor Supabase limpo** exceto: 1 INFO `rls_enabled_no_policy` em `alembic_version` (intencional, ADR-025) + 1 WARN `auth_leaked_password_protection` (WONTFIX plano pago, ADR-027)

- **1 tabela na publicacao `supabase_realtime`**: `provas_digitais` (INSERT/UPDATE para dashboard tempo real)

**Endpoints publicos em producao (34 rotas):**

| Prefix | Endpoints | Wave |
|---|---|---|
| `/api/v1/users` | `GET /me`, `GET /`, `GET /{id}`, `POST /`, `PATCH /{id}`, `DELETE /{id}` | 1 |
| `/api/v1/provas` | `POST /upload-url`, `POST /`, `GET /`, `GET /{id}`, `GET /{id}/imagem-url`, `GET /{id}/movimentacoes`, `GET /{id}/etiqueta.pdf`, `GET /{id}/qr-code.png` | 2 |
| `/api/v1/provas` | `POST /scan`, `POST /{id}/transicoes`, `POST /{id}/cancelar`, `POST /{id}/reiniciar-ciclo` | 3 |
| `/api/v1/provas` | `GET /dashboard` | 4 |
| `/api/v1/reports` | `GET /` (scope discriminado), `GET /export` (CSV streaming) | 5 |
| `/api/v1/audit-log` | `GET /` (paginada + filtros), `GET /{id}` (detalhe + MovimentacaoSnapshot), `GET /by-prova/{id}` (historico cronologico) | 6 |
| `/api/v1/configuracoes` | `GET /`, `GET /{chave}`, `PATCH /{chave}` | 2 |
| `/health*` | `/health`, `/health/db`, `/health/r2` | 0 |

**Rotas frontend em producao (11 paginas):**
- `/login` — Wave 1
- `/dashboard` — Wave 4 C15 + Wave 5 C17 (3º card Acessar Relatorios)
- `/usuarios` — Wave 1 (CRUD + modais)
- `/nova-prova` — Wave 2 C06 (form + dropzone + preview etiqueta)
- `/provas` — Wave 2 C07 (listagem + filtros URL-persisted + paginacao)
- `/provas/[id]` — Wave 2 C08 (detalhe + modal etiqueta/QR + timeline placeholder)
- `/configuracoes` — Wave 2 C09 (tempo atraso + template etiqueta)
- `/escanear` — Wave 3 C10+C11 (scanner QR + assinatura digital + transicao de status + entrada manual de codigo QR)
- `/relatorios` — Wave 5 C16 (4 perspectivas com gráficos SVG inline interativos: Geral, 3Studio, Vendedores, Clicheria + CSV export streaming + atalhos teclado globais)
- `/auditoria` — Wave 6 C18 (listagem do log imutavel admin-only com filtros semanticos, presets de data, paginacao numerada + sticky header + ordenacao clicavel + drawer lateral com focus trap e MovimentacaoSnapshot)

**Atalhos globais por teclado** (Wave 5 C17 + Wave 6): `g s` → /escanear, `g p` → /provas, `g r` → /relatorios (admin-only), `g a` → /auditoria (admin-only), `?` → painel de ajuda.

**Itens do menu ainda inativos (placeholders para Waves futuras):**
- "Informacoes" — sem wave atribuida

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Frontend | Next.js 14, React 18, TypeScript 5, CSS Modules |
| Backend | FastAPI, SQLAlchemy 2.0 async, Pydantic v2, Alembic |
| Banco | PostgreSQL (Supabase, projeto `rwxlpwmnkekzuurgthkr`, sa-east-1) |
| Auth | Supabase Auth (emite JWT) + PyJWT >=2.8 (verifica, nunca emite) |
| Storage | Cloudflare R2 (bucket `rastreio-provas-artes`, account `20ab724c91f6bda669eecfe7c51c9171`) |
| CI/CD | GitHub Actions (lint, testes, keep-alive cron 6 dias) |
| Deploy | Railway (backend) + Vercel (frontend) — configurado na Wave 3 Lote A |

**Deploy em producao (configurado 2026-04-13):**
- **Backend (Railway):** `https://provadigital-production.up.railway.app`
  - Root Directory: `backend`
  - Start Command: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
  - Variavel `FRONTEND_URL` deve apontar para a URL da Vercel (CORS)
  - Todas as env vars do `backend/.env.example` configuradas no painel Variables
  - Procfile presente em `backend/Procfile`
  - `requirements.txt` presente em `backend/requirements.txt` (Railway detecta automaticamente)
  - `pyproject.toml` tem `[tool.setuptools.packages.find] include = ["app*"]` para evitar flat-layout error
- **Frontend (Vercel):** `https://prova-digital-five.vercel.app`
  - Root Directory: `frontend`
  - Framework: Next.js (auto-detectado)
  - 3 env vars: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL`
  - `NEXT_PUBLIC_API_URL` deve apontar para a URL do Railway (sem `/` no final)
- **Fluxo:** Celular → Vercel (frontend) → Railway (backend) → Supabase (DB) + R2 (imagens)
- **CORS:** `FRONTEND_URL` no Railway = URL da Vercel. Sem isso, o browser bloqueia as chamadas.
- **Redeploy automatico:** ambos redeployam quando ha push na `main` do GitHub

---

## Regras criticas

1. **Separacao Alembic / Supabase**: Alembic gerencia APENAS tabelas de dominio (`public.*`).
   Nunca tocar em `auth.*` via Alembic — Supabase gerencia auth.
2. **RLS sempre versionado**: toda policy deve existir como `.sql` em `backend/migrations/rls/`
   ANTES de ser aplicada ao banco. Scripts sao idempotentes (DROP IF EXISTS + CREATE).
3. **PyJWT >= 2.8**: nunca usar python-jose. O backend apenas verifica tokens, nunca emite.
4. **SERVICE_ROLE_KEY**: nunca expor ao frontend. Apenas o backend FastAPI usa.
5. **CSS Modules**: sem framework CSS externo (Tailwind, Bootstrap, etc).
6. **TypeScript estrito**: `strict: true` no tsconfig.

---

## Estrutura de pastas

```
provaDigital/
├── .claude/launch.json          # Dev servers (backend :8000, frontend :3000)
├── .github/workflows/
│   ├── ci.yml                   # Lint (ruff) + testes + deploy staging
│   └── keep-alive.yml           # Cron cada 6 dias para evitar pausa Supabase
├── backend/
│   ├── alembic.ini
│   ├── pyproject.toml           # Dependencias pinadas
│   ├── .env / .env.example
│   ├── app/
│   │   ├── main.py              # FastAPI + 3 health checks + CORS + users router
│   │   ├── core/
│   │   │   ├── config.py        # Pydantic Settings (13 env vars — +QR_CODE_HMAC_SECRET)
│   │   │   ├── jwt.py           # JWT ES256 (JWKS) + HS256 fallback (ADR-014)
│   │   │   ├── r2.py            # Cliente R2 async (singleton + run_in_executor)
│   │   │   └── supabase_admin.py # GoTrue Admin API client (ADR-013/015)
│   │   ├── db/
│   │   │   ├── session.py       # SQLAlchemy async engine + session
│   │   │   └── models.py        # Usuario + ProvaDigital + Movimentacao + Etiqueta + AuditLog + ConfiguracaoSistema + enums (Setor, Localizacao, StatusProva, Rota)
│   │   ├── api/
│   │   │   ├── deps.py          # Auth dependencies (get_current_user, get_admin_user, require_role)
│   │   │   ├── v1/users.py      # 6 endpoints CRUD usuarios
│   │   │   ├── v1/provas.py     # 10 endpoints Wave 2+3: C06-C08 (8) + POST /scan (C10) + POST /{id}/transicoes (C11)
│   │   │   └── v1/configuracoes.py # 3 endpoints Wave 2 C09: GET/, GET/{chave}, PATCH/{chave}
│   │   ├── domain/
│   │   │   └── schemas/
│   │   │       ├── user.py      # Pydantic v2: UserCreate, UserUpdate, UserResponse
│   │   │       ├── prova.py     # Pydantic v2 Wave 2: Upload/ProvaCreate/ProvaResponse + sanitize_filename
│   │   │       ├── configuracao.py # Pydantic v2 Wave 2 C09: whitelist + validators por chave
│   │   │       └── dashboard.py   # Pydantic v2 Wave 4 C15: DashboardContadores + DashboardResponse
│   │   └── services/            # Wave 2 (ADR-040) + Wave 3 (ADR-081)
│   │       ├── state_machine.py # Transicoes + atores + determinar_rota + executar_transicao (Wave 3 A.1)
│   │       ├── qrcode_service.py # HMAC-SHA256 hash + PNG via qrcode[pil] (ADR-033/034)
│   │       ├── etiqueta_service.py # PDF via fpdf2, templates A4/80mm (ADR-035)
│   │       ├── audit_service.py # log_audit helper (ADR-039)
│   │       └── r2_signed.py     # presigned URL + HeadObject + Range GET (ADR-031)
│   ├── migrations/
│   │   ├── env.py               # Alembic config (asyncpg→psycopg2)
│   │   ├── versions/
│   │   │   ├── 001_create_enums_tables_triggers_indexes.py
│   │   │   ├── 002_seed_configuracoes_iniciais.py
│   │   │   ├── 003_fix_constraints_indexes_trigger.py
│   │   │   ├── 004_add_is_admin_created_by_to_usuarios.py
│   │   │   ├── 005_add_index_on_usuarios_created_by.py  # auditoria Wave 1 — index FK created_by
│   │   │   ├── 006_set_search_path_on_trigger_functions.py  # ADR-024 — search_path='' nas funcoes
│   │   │   ├── 007_enable_rls_on_alembic_version.py  # ADR-025 — fix side effect do alembic stamp
│   │   │   ├── 008_add_index_on_configuracoes_sistema_updated_by.py  # ADR-026 — index FK
│   │   │   └── 009_evolve_template_etiqueta_schema.py  # ADR-036 — JSONB estruturado
│   │   └── rls/
│   │       ├── 001_enable_rls.sql
│   │       ├── 002_policies_por_perfil.sql
│   │       ├── 003_policies_wave1_usuarios.sql
│   │       ├── 004_unify_rls_is_admin.sql  # ADR-018
│   │       ├── 005_initplan_optimization.sql  # ADR-029 — (SELECT auth.uid()) em 11 policies
│   │       ├── 006_movimentacoes_insert_and_expand_select.sql  # ADR-082 — INSERT admin + SELECT c/ MOTORISTA/CLICHERIA
│   │       ├── 007_enable_realtime_provas.sql                 # Wave 4 — provas_digitais na publicacao supabase_realtime
│   │       └── apply_rls.py
│   └── tests/
│       ├── conftest.py          # Fixtures: make_user, admin_user, mock_db, vendedor_matriz/filial
│       ├── test_schemas.py      # 13 testes validacao Pydantic
│       ├── test_users_api.py    # Testes integracao endpoints usuarios
│       ├── test_state_machine.py # 26 testes Wave 2 — maquina de estados
│       ├── test_qrcode_service.py # 13 testes Wave 2 — hash + PNG
│       ├── test_etiqueta_service.py # 7 testes Wave 2 — PDF etiqueta
│       ├── test_audit_service.py # 4 testes Wave 2 — audit helper
│       ├── test_provas_api.py   # 59 testes Wave 2 C06+C07+C08 (15+23+21)
│       └── test_configuracoes_api.py # 26 testes Wave 2 C09 — endpoints configuracoes
├── frontend/
│   ├── package.json             # Next.js 14, @supabase/ssr, @supabase/supabase-js, framer-motion
│   ├── tsconfig.json            # strict, ES2017, path aliases @/*
│   ├── next.config.js
│   ├── public/images/
│   │   ├── logo-3studio.svg     # Logo branco 3STUDIO (Figma asset)
│   │   └── login-bg.png         # Background login (Figma asset)
│   └── src/
│       ├── types/global.d.ts    # Declaracao CSS Modules p/ TypeScript
│       ├── hooks/
│       │   ├── useInactivityTimeout.ts  # Timer 30min (RNF-003)
│       │   ├── useCreateProva.ts        # Wave 2 C06 — fluxo upload-url -> PUT R2 -> POST /provas
│       │   ├── useListProvas.ts         # Wave 2 C07 — GET /provas com filtros + debounce
│       │   ├── useProvaDetail.ts        # Wave 2 C08 — GET detail + imagem-url + movimentacoes
│       │   ├── useConfiguracoes.ts      # Wave 2 C09 — GET list + PATCH por chave
│       │   ├── useFocusTrap.ts           # Wave 3 Auditoria — focus trap reutilizavel para modais (WCAG 2.1)
│       │   ├── useScanner.ts            # Wave 3 C10 — wrapper html5-qrcode (SSR-safe + cleanup)
│       │   ├── useScanProva.ts          # Wave 3 C10 — POST /scan wrapper (retorna {data,error})
│       │   ├── useExecutarTransicao.ts  # Wave 3 C11 — POST /{id}/transicoes wrapper (retorna {data,error,isConflict})
│       │   ├── useCurrentUser.ts        # Wave 3 C13 — GET /users/me para detectar admin
│       │   ├── useCancelarProva.ts      # Wave 3 C13 — POST /{id}/cancelar wrapper
│       │   ├── useReiniciarCiclo.ts     # Wave 3 C14 — POST /{id}/reiniciar-ciclo wrapper
│       │   └── useDashboard.ts          # Wave 4 C15 — GET /dashboard wrapper
│       ├── lib/
│       │   ├── api.ts           # apiFetch wrapper (token injection, ApiError). Nao usar p/ binarios
│       │   ├── types/
│       │   │   ├── prova.ts     # Wave 2 C06-C08 — tipos completos + STATUS_LABELS + ROTA_LABELS
│       │   │   ├── usuario.ts   # Wave 2 — tipos TS espelho de schemas/user.py
│       │   │   └── configuracao.ts # Wave 2 C09 — tipos + type guards
│       │   └── supabase/
│       │       ├── client.ts    # Browser client (@supabase/ssr)
│       │       ├── server.ts    # Server client + cookies()
│       │       └── middleware.ts # Session refresh + redirect
│       ├── middleware.ts        # Next.js middleware (auth redirect)
│       └── app/
│           ├── layout.tsx       # Inter font (next/font/google) + globals.css
│           ├── globals.css      # CSS custom properties (cores, radius)
│           ├── login/
│           │   ├── page.tsx     # Login form + SVG clip-path (Figma match)
│           │   └── login.module.css
│           └── (dashboard)/
│               ├── layout.tsx   # Sidebar + user info + logout + inactivity
│               ├── layout.module.css
│               ├── usuarios/
│               │   ├── page.tsx # Tabela + filtros + modais CRUD
│               │   └── usuarios.module.css
│               ├── nova-prova/  # Wave 2 (Componente 06)
│               │   ├── page.tsx # Form + dropzone + preview PDF da etiqueta
│               │   └── nova-prova.module.css
│               ├── provas/      # Wave 2 (Componentes 07 + 08)
│               │   ├── page.tsx # C07: listagem + filtros URL-persisted + paginacao
│               │   ├── provas.module.css
│               │   └── [id]/    # C08: detalhe + C12: timeline + C13/C14: admin actions
│               │       ├── page.tsx                     # dados + arte + timeline + admin actions
│               │       ├── Timeline.tsx                 # C12: timeline visual com Framer Motion
│               │       ├── timeline.module.css          # C12: estilos da timeline
│               │       ├── AdminActions.tsx             # C13/C14: botoes cancelar + reiniciar + modais
│               │       ├── VisualizarEtiquetaModal.tsx  # modal PDF + QR code
│               │       └── detalhe.module.css
│               ├── escanear/     # Wave 3 (Componentes 10 + 11)
│               │   ├── page.tsx                     # scanner QR + assinatura + state machine
│               │   └── escanear.module.css
│               ├── dashboard/    # Wave 4 (Componente 15)
│               │   ├── page.tsx                     # contadores + Recharts + Realtime
│               │   └── dashboard.module.css
│               └── configuracoes/ # Wave 2 (Componente 09)
│                   ├── page.tsx # Tempo atraso + template etiqueta
│                   └── configuracoes.module.css
├── scripts/
│   ├── smoke_r2.py              # Teste ciclo R2: upload→list→download→delete
│   └── keep_alive.py            # GET /health/db com log
├── docs/
│   ├── cloudflare_r2_setup.md   # Guia manual CORS + API token
│   └── db/schema.sql            # Snapshot do schema atual
├── CLAUDE.md                    # Este arquivo
├── DECISIONS.md                 # Registro de decisoes tecnicas (ADR)
└── CHANGELOG.md                 # Historico por sessao
```

---

## Documentos de referencia

| Documento | Local | Nota |
|-----------|-------|------|
| Requisitos v3.0 | Desktop/Rastreio Prova Digital/ | Requisitos funcionais e regras de negocio |
| UML v3.0 | Desktop/Rastreio Prova Digital/ | Modelagem (diagramas de estado, classes, etc) |
| DAT v2.0 | Desktop/Rastreio Prova Digital/ | Arquitetura tecnica detalhada |
| Backlog v3.0 | Desktop/Rastreio Prova Digital/ | NAO editar — gerenciado pelo Renan fora do Claude Code |

Consultar tambem: [DECISIONS.md](DECISIONS.md) | [CHANGELOG.md](CHANGELOG.md) | [docs/db/schema.sql](docs/db/schema.sql) | [docs/waves/](docs/waves/) (closeouts por wave)

---

## Fluxo de trabalho

1. Ler este CLAUDE.md para contexto rapido
2. Consultar o item do backlog indicado pelo Renan
3. Implementar conforme Requisitos + UML + DAT
4. Ao finalizar: atualizar CHANGELOG.md e DECISIONS.md (se houve decisao nova)

---

## Regras operacionais aprendidas ao longo das Waves

**Sempre usar o `.venv/` do projeto para pip/pytest/uvicorn** (Sessao 8b, 10b, 11b):
- **Windows cmd.exe usa `\` (backslash)**, PowerShell aceita `\` ou `/`, Git Bash usa `/`:
  - cmd:       `.venv\Scripts\python -m pytest`
  - PowerShell: `.venv\Scripts\python -m pytest` ou `.venv/Scripts/python -m pytest`
  - Git Bash:  `.venv/Scripts/python -m pytest`
- **Alternativa confortavel**: ativar o venv primeiro com `.venv\Scripts\activate` (ou `source .venv/Scripts/activate` no Git Bash). Depois de ativado, pode rodar `python`, `pip`, `pytest` direto sem prefixo.
- Para **subir o backend do repo root**: `.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload`
- Qualquer comando sem prefixar o venv (ou sem ativar ele antes) e bug em potencial — pode pegar Python global.

**Paths relativos no codigo** (Sessao 10b):
- `config.py` usa `Path(__file__).resolve().parent.parent.parent / ".env"` para resolver o `.env` independente do cwd
- Qualquer novo path relativo no backend deve seguir o mesmo padrao — nunca depender do cwd

**Mocks de SQLAlchemy NAO testam ordem de INSERTs** (Sessao 8c):
- Fluxos com multiplos INSERTs encadeados por FK precisam de `await db.flush()` explicito entre cada `db.add()`
- Sem relationship declarada, o SQLAlchemy nao detecta a dependencia FK automaticamente
- Rodar `scripts/reproduce_*.py` contra banco real antes de declarar Done — regra desde a Sessao 8c

**Binarios no frontend**:
- `apiFetch<T>()` serializa como JSON — **nao usar** para `/etiqueta.pdf`, `/qr-code.png` ou outros endpoints binarios
- Fazer `fetch` direto com header Authorization manual + `response.blob()` → `URL.createObjectURL(blob)`
- Sempre revogar object URLs no cleanup do `useEffect` para nao vazar memoria

**Scripts one-shot temporarios**:
- Colocar em `scripts/reproduce_*.py` ou `scripts/seed_*.py`
- Ter um modo `--cleanup` que funciona como **primeiro** check do `main()`, nao no final
- Remover do repo apos validacao — nao deixar codigo morto

**Registros imutaveis**:
- `audit_logs`, `movimentacoes` e `etiquetas` tem triggers de imutabilidade
- Nunca esperar conseguir apagar essas linhas — para "limpar" provas de teste, marcar como `CANCELADA` via UPDATE em `provas_digitais`
- O objeto R2 correspondente pode ser deletado via boto3, mas e best-effort (nao atomic com a transacao do banco)

---

## Atalhos de teclado globais (Wave 5 Componente 17 — RF-016, expandido na Wave 6)

Disponiveis em qualquer pagina autenticada, registrados via
`useGlobalShortcuts` em `(dashboard)/layout.tsx`. Padrao 2-keystroke
estilo GitHub: pressionar `g` ativa "modo leader" por 1.5s, depois a
segunda tecla dispara a acao.

| Atalho | Acao |
|--------|------|
| `g` `s` | Ir para `/escanear` |
| `g` `p` | Ir para `/provas` |
| `g` `r` | Ir para `/relatorios` (apenas admin — vendedor/motorista/clicheria nao veem) |
| `g` `a` | Ir para `/auditoria` (apenas admin — Wave 6 C18, RNF-005) |
| `?` | Abrir/fechar painel de ajuda dos atalhos (`<KeyboardShortcutsHelp />`) |
| `Esc` | Fechar painel de ajuda ou cancelar leader |

**Comportamento:**
- Atalhos sao **desativados** quando o foco esta em `<input>`, `<textarea>`,
  `<select>` ou elemento `[contenteditable]` — nao quebra digitacao em
  formularios e buscas.
- Modificadores (Ctrl/Cmd/Alt/Meta) sao ignorados — atalhos so disparam
  com a tecla pura. Evita conflito com shortcuts do navegador.
- `g r` e `g a` aparecem no painel de ajuda **apenas para `is_admin = true`**;
  vendedores/motoristas/clicheria nao veem os atalhos na lista nem podem
  ativar via teclado. Defesa adicional: backend dos `/api/v1/reports` e
  `/api/v1/audit-log` retornam 403 se acesso direto.

**Implementacao:**
- Hook: `frontend/src/hooks/useGlobalShortcuts.ts`
- Modal: `frontend/src/components/KeyboardShortcutsHelp.tsx`
- Estilos: `frontend/src/components/KeyboardShortcutsHelp.module.css`
- Registro no layout: `frontend/src/app/(dashboard)/layout.tsx`
  (1 import + 1 hook call + 1 render condicional)

**Atalhos visuais (3 cards no `/dashboard`)** complementam os de teclado
para usuarios mouse-only:
- "Escanear QR Code" (preto) -> `/escanear`
- "Nova Prova" (amarelo) -> `/nova-prova`
- "Acessar Relatorios" (laranja) -> `/relatorios`

Esses 3 cards estao no `shortcutsCell` (col 1, row 3 do grid Figma do
Dashboard — Wave 4 ADR-093 expandido pelo Componente 17 da Wave 5).

---

## RBAC: como adicionar uma nova pagina (Wave 1 v4.0 — Componente 05)

A Matriz de Acesso vive em **`shared/access-matrix.json`** — fonte unica
de verdade espelhada por TS/Python/RLS. Para adicionar uma nova pagina:

1. **Editar `shared/access-matrix.json`** acrescentando 1 entrada em
   `rules`. Campos obrigatorios:
   - `key`: nome curto kebab-case (ex.: `relatorios.export-mensal`).
   - `path`: caminho real do App Router (ex.: `/relatorios/exportacao`).
   - `match`: `"exact"` | `"prefix"` | `"dynamic"` | `"action"`.
   - `perfis`: objeto com decisao para os 4 perfis
     (`studio_admin`, `vendedor`, `motorista`, `clicheria`). Cada
     decisao tem `acesso` (`"full"`/`"parcial"`/`"negado"`) e, se
     parcial, `scope` (um dos 3 kinds em `scope_kinds`).

2. **Atualizar `EXPECTED_KEYS` em `backend/tests/access/test_matrix_structure.py`**
   para incluir a nova chave. Se for chave cuja regra nao se encaixa nas
   semanticas existentes (ex.: novo scope kind), atualizar tambem
   `VALID_SCOPES` + adicionar branch no `scope_filter_for` em
   `backend/app/access/scopes.py`.

3. **No backend**, no endpoint correspondente:
   ```python
   from app.access import access_required, scope_filter_for

   @router.get("/")
   async def listar(user: Usuario = Depends(access_required("nova.chave"))):
       scope = scope_filter_for("nova.chave", user)  # so para parcial
       ...
   ```

4. **No frontend**, na pagina:
   ```tsx
   const auth = useAuthorization("nova.chave");
   if (!auth.loading && !auth.hasAccess) {
     return <Restricted ruleKey="nova.chave" profile={auth.profile} />;
   }
   ```

5. **Se a pagina deve aparecer no menu** (`(dashboard)/layout.tsx`),
   adicionar entrada em `MAIN_NAV` ou `SECONDARY_NAV` com o campo
   `ruleKey` apontando para a nova chave. A filtragem
   `isNavItemVisible` cuidara da visibilidade.

6. **Se a tabela do banco precisa de proteção nova ou diferente**, criar
   migration RLS em `backend/migrations/rls/` referenciando os helpers
   `app_private.current_user_is_admin()` / `_setor()` / `_id()`. PR deve
   incluir as 3 camadas no mesmo commit (regra do projeto — risco R-1
   da analysis).

7. **Validar via `scripts/verify_rbac_equivalence.py`** com
   `DATABASE_URL` setado: o script insere 4 usuarios smoke, impersona
   role authenticated via `set_config request.jwt.claims`, conta linhas
   visiveis por perfil em `provas_digitais` e compara com o esperado da
   Matriz. Cleanup automatico no final.

**Importante:**
- NUNCA criar `if user.is_admin` ou `Depends(get_admin_user)` em
  endpoints novos. Use `access_required(rule_key)`.
- NUNCA escrever filtragem por `setor` direto em queries SQLAlchemy.
  Use `scope_filter_for(rule_key, user)`.
- `get_admin_user` continua existindo mas e legacy — apenas para
  invariantes de negocio que NAO sao celula da Matriz (ex.: RN-010 em
  `users.py`).
