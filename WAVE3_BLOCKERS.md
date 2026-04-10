# Wave 3 — Blockers e Debitos Herdados

Arquivo criado pela Wave 3 Lote A para reportar bugs/debitos encontrados
em Waves anteriores durante a implementacao. Cada item aguarda decisao
explicita do Mario antes de ser endereado (regra inviolavel #3 do plano
da Wave 3).

---

## BLOCKER B-01 — Debito pre-existente: `ruff check .` reporta 6 erros em `backend/migrations/`

**Descoberto:** 2026-04-10, Sessao Wave 3 sub-bloco A.1, apos rodar `ruff check .`
no backend inteiro como validacao final.

**Severidade:** media. Nao bloqueia tecnicamente o Lote A (meus arquivos do A.1
passam no ruff), mas bloqueia o passo `Lint (ruff)` do CI que roda `ruff check .`
conforme `.github/workflows/ci.yml:27`.

**Origem:** pre-existente em `main`. Confirmado via `git stash` + `ruff check .`
no estado limpo de `a8d8f7f` (commit "fix(wave-2): auditoria externa + hardening
final (Sessao 22)"). **Nao e regressao do meu trabalho.**

### Os 6 erros

| # | Arquivo | Linha | Regra | Descricao | Fixable? |
|---|---|---|---|---|---|
| 1 | `migrations/env.py` | 9 | F401 | `asyncio` imported but unused | ✅ auto |
| 2 | `migrations/env.py` | 16 | F401 | `sqlalchemy.ext.asyncio.async_engine_from_config` imported but unused | ✅ auto |
| 3 | `migrations/rls/apply_rls.py` | 44 | F541 | f-string without placeholders (`f"  OK"`) | ✅ auto |
| 4 | `migrations/versions/002_seed_configuracoes_iniciais.py` | 30 | E501 | Line too long (107 > 100) — seed descricao literal PT-BR | manual |
| 5 | `migrations/versions/002_seed_configuracoes_iniciais.py` | 44 | E501 | Line too long (103 > 100) — DELETE WHERE IN (...) inline | manual |
| 6 | `migrations/versions/003_fix_constraints_indexes_trigger.py` | 86 | E501 | Line too long (111 > 100) — `CREATE INDEX IF NOT EXISTS ... ON ...` inline | manual |

### Por que a Sessao 22 declarou "ruff limpo" mesmo com esses erros

Hipotese: a Sessao 22 rodou `ruff check app/ tests/` (que passa limpo — confirmei
aqui), nao `ruff check .` (que falha). O CHANGELOG da Sessao 22 nao especifica
o comando exato, entao a alegacao "ruff limpo" refere-se ao codigo da Wave 2
(`app/` + `tests/`), nao as migrations.

### Impacto no Lote A

- **Meus arquivos** (`app/services/state_machine.py`, `tests/test_state_machine.py`):
  passam em `ruff check` sem erros. ✅
- **Suite de testes**: 332 passed, 0 failed. ✅
- **Cobertura de `state_machine.py`**: 100% (90 stmts, 0 missing). ✅
- **CI atual** (`ruff check .`): vai continuar vermelho no mesmo passo e pelas
  mesmas linhas — nao piora e nao melhora.

### Opcoes de resolucao

**(A) Ignorar o blocker e seguir** — assumir que o CI ja estava vermelho desde
antes do meu trabalho (Sessao 22) e que merge de PRs esta sendo feito mesmo
com `Lint (ruff)` quebrado. Risco: nao descubro se o CI estava realmente verde
por algum fluke (versao de ruff mais antiga instalada no runner, cache, etc).

**(B) Adicionar `exclude = ["migrations/"]` no `pyproject.toml`** — solucao
canonica Python + Alembic. Migrations sao semi-geradas (boilerplate alembic +
SQL puro em `op.execute`) e a maioria dos projetos Python com Alembic excluem
elas do lint. Patch minimo (+2 linhas no `pyproject.toml`), zero mudanca de
comportamento. Preserva o lint rigoroso em `app/` e `tests/`.

**(C) Corrigir os 6 erros cirurgicamente** — 3 auto-fixable via `ruff check
--fix`, 3 manuais (quebrar strings literais em 3 linhas para respeitar 100
chars). Delta: ~15-20 linhas editadas em 4 arquivos. Pros: CI fica 100% limpo
no `.` inteiro. Contras: toca em 3 arquivos de `Wave 0` (migrations 002 e 003
+ `env.py` + `apply_rls.py`), violando a regra "nao tocar em Waves anteriores
sem autorizacao".

### Recomendacao

**(B)** — adicionar exclude em `migrations/`. Eh o padrao da comunidade
Python/Alembic, e uma mudanca de 2 linhas em `pyproject.toml`, e nao toca em
nenhum arquivo de Wave 0/1/2 (so adiciona config). O `pyproject.toml` ja foi
tocado na Sessao 22 pela auditoria externa, entao tocar nele de novo para
housekeeping nao e agressivo.

Se o Mario preferir (C), executo via autorizacao expressa e registro como
"housekeeping autorizado" no CHANGELOG do sub-bloco A.1.

Se o Mario preferir (A), registro apenas que o debito foi observado mas mantido
como estava — fica como debito Wave 6 (auditoria final).

### Decisao

✅ **RESOLVIDO 2026-04-10** — Mario autorizou a opcao **(B)** apos revisao do
sub-bloco A.1.

**Acao aplicada:** adicionado `extend-exclude = ["migrations"]` na secao
`[tool.ruff]` de `backend/pyproject.toml` + comentario explicativo apontando
para este arquivo e para o ADR-081.

**Validacao pos-fix:**
- `ruff check .` dentro de `backend/`: **All checks passed!**
- `pytest`: **332 passed**, 1 warning (InsecureKeyLengthWarning pre-existente
  em `test_jwt.py`, fora de escopo da Wave 2/3).
- Zero arquivo de `migrations/` tocado — a regra "nao tocar em Waves
  anteriores" foi preservada.

**Debito remanescente:** os 6 warnings estilisticos em `migrations/` continuam
existindo no codigo. Nao sao detectados pelo CI daqui em diante, mas podem
ser limpos em uma futura Wave 6 (auditoria final) sem pressa. Registro aqui
para rastreabilidade futura caso o padrao de lint mude.

---

## BLOCKER B-02 — Debito pre-existente: `npm audit` reporta 4 high severity no `next@14.2`

**Descoberto:** 2026-04-10, Sessao Wave 3 sub-bloco A.5, apos rodar
`npm install html5-qrcode react-signature-canvas` no frontend.

**Severidade:** media. As vulnerabilidades existem desde a Wave 1 (quando o
Next.js 14 foi instalado) e nao sao regressao das dependencias que o A.5
adiciona.

**Detalhes (via `npm audit`):**

```
next  9.5.0 - 15.5.14                                       high
- DoS via Image Optimizer remotePatterns configuration
- HTTP request deserialization can lead to DoS
- HTTP request smuggling in rewrites
- Unbounded next/image disk cache growth
- DoS with Server Components
Fix available via: npm audit fix --force
Will install next@16.2.3 (breaking change)
```

**Origem:** pre-existente em `main`. O `package.json` tem `"next": "^14.2"`
desde o commit inicial do frontend na Wave 1 (commit `8ccce2e` —
"feat(wave-1): Auth + Users CRUD + RBAC + Login UI ...").

**Impacto no Lote A:** zero funcional. As libs adicionadas por A.5
(`html5-qrcode`, `react-signature-canvas`, `@types/react-signature-canvas`)
passam no audit limpo. Os 4 highs sao do Next.js framework, nao das libs
novas.

**Risco operacional:**
- A Wave 2 ja rodou em producao com Next.js 14 (Vercel) sem incidentes.
- As DoS sao contra o self-host, relevantes principalmente para Next.js
  em Docker/bare metal. Vercel mitiga as partes de Image Optimizer e
  cache de disco como parte do managed runtime.
- Ainda assim, e debito real e deve ser enderecado.

**Decisao:** **NAO resolver no Lote A.** Justificativa:
- `npm audit fix --force` exige upgrade para Next.js 16, que e um major
  release com breaking changes (App Router semantics, React 19,
  middleware changes, etc). Refatoracao nao trivial.
- O Lote A nao introduz o debito, apenas o observou.
- Wave 6 (auditoria final) ja esta planejada para cobrir
  hardening/dependencias — local natural para esse upgrade.

**Registro formal:** adicionar a lista de debitos Wave 6 no `CHANGELOG.md`
ao final do Lote A (no closeout do sub-bloco A.6). Ate la, o A.5 prossegue
normalmente com `next@14.2`.

### Decisao

✅ **REGISTRADO 2026-04-10** — debito pre-existente aceito como TODO para
Wave 6. Zero acao no Lote A.
