# Rastreio de Provas Digitais

Sistema de rastreamento de provas digitais da 3Studio. Controla o ciclo de vida
das provas desde a criacao ate o recebimento pela clicheria, com rastreabilidade
completa, assinatura digital e auditoria imutavel.

## Stack

| Camada | Tecnologia |
|---|---|
| Frontend | Next.js 14 (App Router) + TypeScript |
| Backend | FastAPI + Python 3.11+ |
| ORM | SQLAlchemy 2.0 (async) |
| Banco | PostgreSQL via Supabase |
| Auth | Supabase Auth (JWT) + PyJWT (verificacao) |
| Migrations | Alembic (tabelas de dominio) |
| Storage | Cloudflare R2 (artes das provas) |
| CI/CD | GitHub Actions |

## Estrutura do Projeto

```
rastreio-provas-digitais/
├── backend/
│   ├── app/
│   │   ├── core/           # config, JWT, cliente R2
│   │   ├── db/             # engine e session SQLAlchemy
│   │   ├── domain/         # entidades e maquina de estados (Wave 1+)
│   │   ├── api/            # routers FastAPI (Wave 1+)
│   │   └── main.py         # app FastAPI + health checks
│   ├── migrations/
│   │   ├── versions/       # migrations Alembic versionadas
│   │   ├── rls/            # politicas RLS em .sql + script de aplicacao
│   │   ├── env.py          # config do Alembic
│   │   └── script.py.mako  # template de migrations
│   ├── tests/
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── .env.example
├── frontend/               # Next.js (boilerplate nesta wave)
├── scripts/
│   ├── keep_alive.py       # mantém Supabase ativo (free tier)
│   └── smoke_r2.py         # teste de conectividade com R2
├── .github/workflows/
│   ├── ci.yml              # lint + testes a cada push
│   └── keep-alive.yml      # cron a cada 6 dias
├── docs/
│   └── cloudflare_r2_setup.md
└── README.md
```

## Setup Local — Passo a Passo

### Pre-requisitos

- **Python 3.11+** — [python.org/downloads](https://www.python.org/downloads/)
- **Node.js 18+** — [nodejs.org](https://nodejs.org/) (para o frontend)
- **Git** — [git-scm.com](https://git-scm.com/)

### 1. Clonar o repositorio

```bash
git clone <url-do-repo>
cd rastreio-provas-digitais
```

### 2. Configurar o backend

```bash
cd backend

# Criar ambiente virtual (isola as dependencias do projeto)
python -m venv .venv

# Ativar o ambiente virtual
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Instalar dependencias
pip install -e ".[dev]"
```

### 3. Configurar variaveis de ambiente

```bash
# Copiar o template
cp .env.example .env
```

Abra o arquivo `.env` e preencha os valores. Voce vai precisar de:

**Supabase (Settings > API no dashboard):**
- `SUPABASE_URL` — URL do projeto (ex: `https://xxxx.supabase.co`)
- `SUPABASE_ANON_KEY` — chave publica (anon key)
- `SUPABASE_SERVICE_ROLE_KEY` — chave de servico (NUNCA exponha no frontend)
- `SUPABASE_JWT_SECRET` — segredo JWT (Settings > API > JWT Secret)
- `DATABASE_URL` — connection string do PostgreSQL (Settings > Database > Connection string > URI, modo "Session")
  - Troque `postgresql://` por `postgresql+asyncpg://` no inicio

**Cloudflare R2 (siga `docs/cloudflare_r2_setup.md`):**
- `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`
- `R2_ENDPOINT_URL`, `R2_BUCKET_NAME`

### 4. Aplicar migrations (se rodando contra um banco novo)

```bash
# As migrations criam as tabelas de dominio no PostgreSQL.
# Tabelas de autenticacao (auth.*) sao gerenciadas pelo Supabase — nao tocar.

# Instalar driver sincrono (Alembic nao suporta asyncpg)
pip install psycopg2-binary

# Aplicar
alembic upgrade head
```

> **O que e uma migration?**
> E um script versionado que altera a estrutura do banco (criar tabela,
> adicionar coluna, etc). O Alembic aplica as migrations em ordem e guarda
> qual ja foi executada, evitando duplicacao. O comando `upgrade head`
> aplica todas as pendentes.

### 5. Aplicar politicas RLS

```bash
# RLS (Row Level Security) controla QUEM pode ver QUAIS dados no banco.
# Exemplo: um vendedor so ve as provas dele, nao as de outros vendedores.
# O script abaixo aplica todas as politicas versionadas em migrations/rls/.

python migrations/rls/apply_rls.py
```

> **O que e RLS?**
> Row Level Security e uma funcionalidade do PostgreSQL que filtra registros
> automaticamente com base no usuario que esta acessando. Mesmo que alguem
> consiga fazer uma query direta no banco, so vera os dados que as politicas
> permitem. E uma camada de seguranca ALEM da validacao da aplicacao.

### 6. Rodar o backend

```bash
# Inicia o servidor FastAPI na porta 8000
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Acesse os health checks para validar:
- http://localhost:8000/health — deve retornar `{"status": "ok"}`
- http://localhost:8000/health/db — deve retornar `{"status": "ok", "database": "connected"}`
- http://localhost:8000/health/r2 — deve retornar `{"status": "ok", "r2": "connected"}`

### 7. Rodar o frontend (opcional nesta wave)

```bash
cd ../frontend
npm install
npm run dev
```

Acesse http://localhost:3000.

### 8. Validar conectividade R2 (smoke test)

```bash
cd ..
python scripts/smoke_r2.py
```

Deve imprimir OK nos 4 passos (upload, list, download, delete).

## Comandos Uteis

| Comando | O que faz |
|---|---|
| `uvicorn app.main:app --reload` | Inicia o backend em modo desenvolvimento |
| `alembic upgrade head` | Aplica todas as migrations pendentes |
| `alembic downgrade -1` | Reverte a ultima migration |
| `alembic revision -m "descricao"` | Cria uma nova migration vazia |
| `python migrations/rls/apply_rls.py` | Reaaplica todas as politicas RLS |
| `python scripts/smoke_r2.py` | Testa conectividade com o R2 |
| `python scripts/keep_alive.py URL` | Faz ping no backend (keep-alive manual) |
| `ruff check .` | Roda o linter |
| `pytest tests/ -v` | Roda os testes |

## Arquitetura de Dados — Resumo

```
usuarios ──────────< provas_digitais ──────< movimentacoes
    │                     │                       (imutavel)
    │                     ├──────< etiquetas
    │                     │
    │                     └──────< audit_logs
    │                                (imutavel)
    └──────────────< configuracoes_sistema
```

- **Tabelas de dominio** (acima): gerenciadas via Alembic
- **Tabelas de auth** (`auth.users`, `auth.sessions`): gerenciadas pelo Supabase — nunca alterar via Alembic
- **Politicas RLS**: versionadas em `backend/migrations/rls/` como arquivos `.sql`

## Regras Importantes

1. **Nunca** commitar o arquivo `.env` (contem segredos)
2. **Nunca** criar tabelas pelo painel do Supabase — usar Alembic
3. **Nunca** alterar `auth.*` via migration
4. **Nunca** expor `SUPABASE_SERVICE_ROLE_KEY` no frontend
5. Toda politica RLS deve existir como `.sql` versionado antes de ser aplicada

## Waves de Entrega

| Wave | Escopo | Status |
|---|---|---|
| 0 | Infraestrutura + Keep-alive | Concluida |
| 1 | Autenticacao + RBAC | Proxima |
| 2 | Nucleo do Dominio (CRUD provas) | Pendente |
| 3 | Fluxo de Movimentacao + QR Code | Pendente |
| 4 | Dashboard Realtime | Pendente |
| 5 | Relatorios + UX | Pendente |
| 6 | Interface de Auditoria | Pendente |
