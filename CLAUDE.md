# Rastreio de Provas Digitais

Sistema de rastreamento de provas digitais (artes graficas) para a 3Studio.
Acompanha o ciclo de vida completo: criacao, aprovacao, transporte e entrega a clicheria,
com QR Code, assinatura digital de cada movimentacao e auditoria imutavel.

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
| Deploy | Railway (backend) + Vercel (frontend) — a configurar na Wave 1 |

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
│   │   │   ├── config.py        # Pydantic Settings (12 env vars)
│   │   │   ├── jwt.py           # JWT ES256 (JWKS) + HS256 fallback (ADR-014)
│   │   │   ├── r2.py            # Cliente R2 async (singleton + run_in_executor)
│   │   │   └── supabase_admin.py # GoTrue Admin API client (ADR-013/015)
│   │   ├── db/
│   │   │   ├── session.py       # SQLAlchemy async engine + session
│   │   │   └── models.py        # Usuario model, SetorEnum, LocalizacaoEnum
│   │   ├── api/
│   │   │   ├── deps.py          # Auth dependencies (get_current_user, get_admin_user, require_role)
│   │   │   └── v1/users.py      # 6 endpoints CRUD usuarios
│   │   └── domain/
│   │       └── schemas/user.py  # Pydantic v2: UserCreate, UserUpdate, UserResponse
│   ├── migrations/
│   │   ├── env.py               # Alembic config (asyncpg→psycopg2)
│   │   ├── versions/
│   │   │   ├── 001_create_enums_tables_triggers_indexes.py
│   │   │   ├── 002_seed_configuracoes_iniciais.py
│   │   │   ├── 003_fix_constraints_indexes_trigger.py
│   │   │   └── 004_add_is_admin_created_by_to_usuarios.py
│   │   └── rls/
│   │       ├── 001_enable_rls.sql
│   │       ├── 002_policies_por_perfil.sql
│   │       ├── 003_policies_wave1_usuarios.sql
│   │       └── apply_rls.py
│   └── tests/
│       ├── conftest.py          # Fixtures: make_user, admin_user, mock_db
│       ├── test_schemas.py      # 13 testes validacao Pydantic
│       └── test_users_api.py    # 25 testes integracao endpoints
├── frontend/
│   ├── package.json             # Next.js 14, @supabase/ssr, @supabase/supabase-js
│   ├── tsconfig.json            # strict, ES2017, path aliases @/*
│   ├── next.config.js
│   ├── public/images/
│   │   ├── logo-3studio.svg     # Logo branco 3STUDIO (Figma asset)
│   │   └── login-bg.png         # Background login (Figma asset)
│   └── src/
│       ├── types/global.d.ts    # Declaracao CSS Modules p/ TypeScript
│       ├── hooks/useInactivityTimeout.ts  # Timer 30min (RNF-003)
│       ├── lib/
│       │   ├── api.ts           # apiFetch wrapper (token injection, ApiError)
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
│               └── usuarios/
│                   ├── page.tsx # Tabela + filtros + modais CRUD
│                   └── usuarios.module.css
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

Consultar tambem: [DECISIONS.md](DECISIONS.md) | [CHANGELOG.md](CHANGELOG.md) | [docs/db/schema.sql](docs/db/schema.sql)

---

## Fluxo de trabalho

1. Ler este CLAUDE.md para contexto rapido
2. Consultar o item do backlog indicado pelo Renan
3. Implementar conforme Requisitos + UML + DAT
4. Ao finalizar: atualizar CHANGELOG.md e DECISIONS.md (se houve decisao nova)
