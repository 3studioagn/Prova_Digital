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
| **3 — Scanner + Transicoes** | 🔜 Proxima | Camera HTML5, scanner QR, assinatura digital, maquina de estados (executar_transicao), reprovacao, cancelamento, reiniciar ciclo | — |
| **4 — Dashboard + Atrasos** | ⏳ | Dashboard tempo real, contadores, calculo de atraso (RN-008), Realtime via Supabase | — |
| **5 — Relatorios + Export** | ⏳ | CSV export, metricas por vendedor, dashboards gerenciais | — |
| **6 — Auditoria + Polish** | ⏳ | Tela de audit_log, cleanup de orfaos R2, rotacao de secrets, hardening final | — |

**Estado atual do banco de producao:**
- `alembic_version = 009`
- **6 tabelas de dominio** + `alembic_version` (todas com RLS habilitada)
- **11 policies RLS** otimizadas com `(SELECT auth.uid())` (ADR-029)
- **30 indexes** cobrindo filtros dos Componentes 07 e futuros
- **2 admins ativos** (`admin@3studio.com.br` + `ops@3studio.com.br` — ADR-030 executado)
- **Advisor Supabase limpo** exceto: 1 INFO `rls_enabled_no_policy` em `alembic_version` (intencional, ADR-025) + 1 WARN `auth_leaked_password_protection` (WONTFIX plano pago, ADR-027)

**Endpoints publicos em producao (24 rotas):**

| Prefix | Endpoints | Wave |
|---|---|---|
| `/api/v1/users` | `GET /me`, `GET /`, `GET /{id}`, `POST /`, `PATCH /{id}`, `DELETE /{id}` | 1 |
| `/api/v1/provas` | `POST /upload-url`, `POST /`, `GET /`, `GET /{id}`, `GET /{id}/imagem-url`, `GET /{id}/movimentacoes`, `GET /{id}/etiqueta.pdf`, `GET /{id}/qr-code.png` | 2 |
| `/api/v1/configuracoes` | `GET /`, `GET /{chave}`, `PATCH /{chave}` | 2 |
| `/health*` | `/health`, `/health/db`, `/health/r2` | 0 |

**Rotas frontend em producao (7 paginas):**
- `/login` — Wave 1
- `/usuarios` — Wave 1 (CRUD + modais)
- `/nova-prova` — Wave 2 C06 (form + dropzone + preview etiqueta)
- `/provas` — Wave 2 C07 (listagem + filtros URL-persisted + paginacao)
- `/provas/[id]` — Wave 2 C08 (detalhe + modal etiqueta/QR + timeline placeholder)
- `/configuracoes` — Wave 2 C09 (tempo atraso + template etiqueta)

**Itens do menu ainda inativos (placeholders para Waves futuras):**
- "Dashboard" — Wave 4
- "Escanear" — Wave 3
- "Relatorios" — Wave 5
- "Informacoes" — possivel Wave 6

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
│   │   │   ├── v1/provas.py     # 8 endpoints Wave 2 C06+C07+C08: upload-url, POST, GET list, GET {id}, imagem-url, movimentacoes, etiqueta.pdf, qr-code.png
│   │   │   └── v1/configuracoes.py # 3 endpoints Wave 2 C09: GET/, GET/{chave}, PATCH/{chave}
│   │   ├── domain/
│   │   │   └── schemas/
│   │   │       ├── user.py      # Pydantic v2: UserCreate, UserUpdate, UserResponse
│   │   │       ├── prova.py     # Pydantic v2 Wave 2: Upload/ProvaCreate/ProvaResponse + sanitize_filename
│   │   │       └── configuracao.py # Pydantic v2 Wave 2 C09: whitelist + validators por chave
│   │   └── services/            # Wave 2 (ADR-040)
│   │       ├── state_machine.py # Transicoes + atores + determinar_rota + executar_transicao stub
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
│   ├── package.json             # Next.js 14, @supabase/ssr, @supabase/supabase-js
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
│       │   └── useConfiguracoes.ts      # Wave 2 C09 — GET list + PATCH por chave
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
│               │   └── [id]/    # C08: detalhe
│               │       ├── page.tsx                     # dados + arte + timeline placeholder
│               │       ├── VisualizarEtiquetaModal.tsx  # modal PDF + QR code
│               │       └── detalhe.module.css
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

Consultar tambem: [DECISIONS.md](DECISIONS.md) | [CHANGELOG.md](CHANGELOG.md) | [docs/db/schema.sql](docs/db/schema.sql)

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
