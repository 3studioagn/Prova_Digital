# 🌊 Wave 6 — Closeout

**Status:** ✅ **COMPLETA**
**Data de conclusão:** 2026-04-29
**Componente:** 18 (Interface de Log de Auditoria)
**RLS aplicada em produção:** 008 (REVOKE INSERT/UPDATE/DELETE em `audit_logs` para `anon`/`authenticated`)
**Migrations Alembic:** sem mudança (`alembic_version = 011`)

---

## 📊 Definition of Done — check final

### Backlog Wave 6 / DoD Global

| # | Critério | Status | Evidência |
|---|---|:---:|---|
| 1 | Code review por outro membro | ✅ | Auditoria sênior interna no commit `2b1c278` revisou os 11 commits anteriores |
| 2 | Testes unit ≥ 80% | ✅ | **92% TOTAL** nos 3 módulos novos: router 86%, service 88%, schemas 99% |
| 3 | Testes integração em staging | ✅ | 68 testes em `test_audit_log_api.py` (RBAC + validação + endpoints + imutabilidade + service direto) + smoke real via curl no analysis.md §"Validação manual executada" |
| 4 | Migrations versionadas | ✅ | RLS 008 versionada em `backend/migrations/rls/008_revoke_audit_logs_mutation.sql` + aplicada via Supabase MCP |
| 5 | Validação contra critérios de aceitação | ✅ | RNF-005 satisfeito com 3 camadas; RF-007/RF-008/RN-005/RN-006 indiretamente — eventos visíveis no log |
| 6 | Console limpo no browser | ✅ | TypeScript `--noEmit` exit 0; ESLint Wave 6 limpo; preview server sem erros |
| 7 | Documentação interna | ✅ | `docs/wave6/analysis.md` (775 linhas Gate 1 + Execução + UX iteration), CHANGELOG por bloco, 5 ADRs (110-114) |
| 8 | Políticas RLS auditadas | ✅ | Wave 6 não criou nova policy — apenas REVOKE explícito em RLS 008. `pol_audit_select` (admin-only) já cobria desde Wave 0. Validação via `has_table_privilege` documentada no analysis.md §2.1 |

### Critérios de aceite específicos

| RF/RN/RNF | Onde | Validado |
|---|---|:---:|
| **RNF-005** log auditoria completo e imutável, admin-only | 3 endpoints `/api/v1/audit-log` + `get_admin_user` + `pol_audit_select` + trigger `trg_audit_logs_imutavel` + RLS 008 REVOKE | ✅ |
| **RF-007** reprovação visível na auditoria | Filtro semântico `tipo_evento=reprovacao` mapeia para `acao=transitar_status AND detalhes_json.para=REPROVADA_PELO_VENDEDOR` | ✅ |
| **RF-008** reinício de ciclo visível | Filtro `tipo_evento=reinicio` mapeia para `acao=reiniciar_ciclo` + `MovimentacaoSnapshot` no detalhe | ✅ |
| **RN-005** cancelamento preservado | Filtro `tipo_evento=cancelamento` mapeia para `acao=transitar_status AND detalhes_json.para=CANCELADA` | ✅ |
| **RN-006** preserva histórico em ciclos | `detalhes_json.ciclo` exibido no detalhe (não confunde com `prova.ciclo_atual`) | ✅ |
| **RNF-006** responsivo (≥ 5") | `mobileNotice` + `desktopOnly` + breakpoints 768/960/1280 px | ⚠️ N/A (auditoria é desktop-only por construção — mobile mostra notice) |

---

## 🛡️ Estratégia de defesa em profundidade — RNF-005 em 3 camadas

| Camada | Mecanismo | Origem |
|---|---|---|
| **1. Trigger DB** | `trg_audit_logs_imutavel BEFORE UPDATE OR DELETE` | Wave 0 (migration 001) |
| **2. RLS deny-by-default** | `pol_audit_select` admin-only; sem policy INSERT/UPDATE/DELETE | Wave 0 + 1 + 2 (RLS 001/004/005) |
| **3. GRANT-level REVOKE** | `REVOKE INSERT, UPDATE, DELETE ... FROM anon, authenticated` | **Wave 6 — RLS 008** |

`service_role` mantém GRANT (backend continua escrevendo via `audit_service.log_audit`). Validação reproducível:

```sql
SELECT has_table_privilege('authenticated','public.audit_logs','UPDATE');
-- esperado: false
```

ADR-112 documenta o racional. ADR-110 documenta convivência com `/provas/{id}/movimentacoes` da Wave 2 (timeline visual continua intacta).

---

## 📦 Entregáveis (11 commits Wave 6 + 2 commits Wave 5 R2 misturados)

| # | Commit | Tipo | Foco |
|---|---|---|---|
| 1 | `e816167` | docs | Gate 1 — análise read-only pré-execução |
| 2 | `be63f22` | chore | RLS 008 — REVOKE em `audit_logs` |
| 3 | `a556a4a` | feat | Backend — schemas + service + router |
| 4 | `e6bb772` | test | 63 testes integrados (95% cov inicial) |
| 5 | `8372da6` | fix | (Wave 5 R2 misturado) L-F1 useMemo visibleShortcuts |
| 6 | `eb771b3` | feat | Frontend — `/auditoria` + tipos + hook + atalho `g a` + menu admin-only |
| 7 | `bf4d1f9` | docs | (Wave 5 R2 misturado) ADR-109 + CHANGELOG |
| 8 | `6abc500` | docs | CHANGELOG + DECISIONS (110-112) + analysis.md §Execução |
| 9 | `91704bd` | feat | UX iter backend — `tipo_evento` + `order_by` + busca em `nro_requerimento` |
| 10 | `85b52d1` | feat | UX iter frontend — presets data, filtros semânticos, paginação numerada, sticky header, ordenação clicável |
| 11 | `10ff9c3` | docs | UX iter — CHANGELOG + ADR-113 |
| 12 | `2c431ff` | misc | Save antes da auditoria (misturou Wave 5 R2: H-A1, M-A1, L-A1, M-F1) |
| 13 | `2b1c278` | fix | Auditoria sênior — H-01, H-02, M-01..M-04, L-01..L-04 + ADR-114 |

**Observação de isolamento:** o commit `2c431ff` empacotou bugfixes da Wave 5 R2 (auditoria sênior R2 da Wave 5) junto com Wave 6. CHANGELOG separa as duas seções, mas o **commit** mistura conteúdos. Lição capturada em §Lessons learned.

---

## 📈 Métricas finais

### Backend

| Métrica | Wave 5 baseline | Wave 6 final |
|---|---:|---:|
| Testes pytest | 633 | **724** (+91) |
| Cobertura módulos novos | n/a | **92%** TOTAL (router 86%, service 88%, schemas 99%) |
| Endpoints `/api/v1/*` | 31 | **34** (+3 audit-log) |
| Routers `app/api/v1/` | 4 | **5** (+`audit_log.py`) |
| Schemas Pydantic | (vários) | **+1** módulo (`audit_log.py` 287 linhas) |
| Services | (vários) | **+1** módulo (`audit_log_service.py` 482 linhas) |
| ADRs no DECISIONS.md | 109 | **114** (+5: 110, 111, 112, 113, 114) |
| RLS migrations versionadas | 7 | **8** (+008 REVOKE) |
| `ruff check .` | All checks passed! | **All checks passed!** (mantido) |

### Frontend

| Métrica | Wave 5 baseline | Wave 6 final |
|---|---:|---:|
| Rotas Next.js ativas | 10 | **11** (+`/auditoria`) |
| Hooks customizados | 16 | **17** (+`useAuditLog`/`useAuditLogDetail`) |
| Tipos compartilhados | (vários) | **+1** módulo (`auditLog.ts` 334 linhas) |
| Atalhos globais (`g X`) | 3 | **4** (+`g a` admin-only) |
| Bundle `/auditoria` | n/a | **7.27 kB / 166 kB First Load** |
| Ícones SVG | (vários) | **+1** (`ShieldIcon`) |
| Deps externas | 0 | **0** (sem novas deps) |

### Banco

|  | Wave 5 | Wave 6 |
|---|---|---|
| `alembic_version` em produção | 011 | **011** (sem migration nova) |
| Tabelas com RLS | 6 | 6 (sem alteração) |
| Policies RLS | 12 | 12 (sem alteração — apenas REVOKE GRANT-level) |
| Índices | 32 | 32 (sem alteração — 4 índices `unused_index` já cobrem audit_logs) |
| Realtime tables | 1 (`provas_digitais`) | 1 (sem alteração) |
| Defesa em profundidade `audit_logs` | 2 camadas | **3 camadas** (+REVOKE explícito) |

---

## 🧪 Validações finais

- ✅ `pytest backend/tests/`: **724 passed**, 0 regressão (era 633 antes da Wave 6)
- ✅ `ruff check .`: **All checks passed!**
- ✅ `tsc --noEmit`: limpo (exit 0)
- ✅ `next lint`: 0 warnings, 0 errors nos arquivos Wave 6
- ✅ `next build`: rota `/auditoria` 7.27 kB / 166 kB First Load
- ✅ `preview_start` console: 0 erros JS
- ✅ Smoke curl em produção:
  - `GET /api/v1/audit-log` sem auth → **401**
  - `GET /api/v1/audit-log/abc` (UUID malformado) → **404**
  - `POST/PUT/PATCH/DELETE` em qualquer endpoint → **405** (imutabilidade)
- ✅ Validação Supabase via `has_table_privilege` pós-RLS 008:
  - `authenticated`: SELECT=true, INSERT/UPDATE/DELETE=**false**
  - `anon`: SELECT=true, INSERT/UPDATE/DELETE=**false**
  - `service_role`: INSERT=true, SELECT=true (backend continua escrevendo)

---

## 🔓 Pendências para Wave 7+

### 1. E2E Playwright (`auditoria.spec.ts`)
Playwright ainda não está configurado neste projeto. Cenários candidatos:
- Admin happy path — login admin → `/auditoria` → filtros → drawer → fechar
- Vendedor bloqueado — acesso direto à URL renderiza "Acesso restrito"
- Anônimo bloqueado — middleware redireciona para `/login`

### 2. Achados LOW aceitos como follow-up
- **L-05** matching `(prova_id, status_novo, ciclo)` + janela ±5s em `_find_movimentacao_relacionada` — opção B (mov_id no `detalhes_json`) requer alteração em `state_machine.executar_transicao` (Wave 3) — adiada
- **L-06** endpoint `GET /api/v1/audit-log/by-prova/{id}` implementado e testado mas **sem consumer no frontend** — candidato a um botão "Ver histórico desta prova" no drawer
- **L-07** filtro `q` aplica `ILIKE '%{q}%'` sem escape de wildcards `%`/`_` — admin-only, baixo risco
- **L-08** REVOKE em `movimentacoes` e `etiquetas` (consistência com RLS 008) — registrado em ADR-112 alternativas rejeitadas

### 3. Reuso de filtros shared
Extrair `DateRangeFilter`/`SearchInput`/`StatusFilter`/`VendedorFilter` para `frontend/src/components/filters/` — reusar em `/relatorios` + `/auditoria` + `/provas`. Refator dedicado, depende de extrair também o CSS shared.

### 4. Migration Alembic 012 (índices preemptivos)
Acompanhar Supabase advisor pós-Wave 6 — quando os 4 índices `unused_index` em `audit_logs` deixarem a lista (sinal de uso real), avaliar se filtros compostos justificam novos índices. Default: NÃO criar preemptivamente.

---

## 🎓 Lessons learned

### O que funcionou bem

1. **Gate 1 read-only de 775 linhas** antes de qualquer código — o `analysis.md` validou escopo, RLS, defesa em profundidade e contratos antes do Gate 2. Reduziu retrabalho a praticamente zero.
2. **Auditoria sênior pegou 11 achados pós-execução** (2 HIGH + 4 MEDIUM + 4 LOW + 1 observação de isolamento). Útil para reforçar que entrega "passando suite" não é entrega "auditada".
3. **UX iteration pós-Gate 2 (pacote A+B)** — Mario pediu reforço de UX visando ~60k audits/ano em produção. Filtros semânticos, paginação numerada e ordenação clicável melhoraram drasticamente o caso real, sem breaking changes.
4. **3 camadas de defesa em RNF-005** — RLS 008 REVOKE foi puramente aditivo, idempotente e zero-risco. Documentado em ADR-112.
5. **Reuso completo de `useFocusTrap`** (Wave 3 audit) — quando aplicado no drawer (audit fix H-01), 3 linhas de código suficientes graças ao padrão consolidado.
6. **`tipo_evento` resolvido server-side** (ADR-113) — esconde a complexidade do par `(acao, detalhes_json.para)` do admin e mantém paginação consistente.

### O que poderia ter sido melhor

1. **Commit `2c431ff` misturou Wave 5 R2 com Wave 6** — bugfixes legítimos (H-A1, M-A1, L-A1, M-F1), mas em commit cujo título sugeria apenas Wave 6. CHANGELOG separa, mas o commit não. Lição: criar branch dedicado `wave5/audit-r2` quando bugs de wave passada aparecerem durante outra wave.
2. **Drawer da `/auditoria` esqueceu `useFocusTrap`** — divergência entre Gate 1 (analysis.md §3.5.3 listou como "obrigatorio") e execução. Auditoria sênior pegou (H-01). Lição: criar checklist mecânico de "todo `role=dialog` precisa de focus trap" — agora consolidado em ADR-114.
3. **`F401 RotaEnum` import unused** em `test_audit_log_api.py` — passou no review interno; só pegou no `ruff check` da auditoria. Lição: rodar `ruff check .` antes de cada commit, não apenas no fim.
4. **Cobertura inicial 95% caiu para 92% após UX iteration** — `_aplicar_tipo_evento` tem ramos não cobertos via service direto (testes ficam no nível schema/router). Lição: testes parametrizados por valor seriam úteis.

### Padrões que se consolidaram

- **Whitelist por frozenset** + helper `if/elif` explícito (em vez de `getattr` reflexivo) para colunas/filtros aceitos do schema → service. Defesa anti-SQL-injection em duas camadas. ADR-113.
- **`Cache-Control: no-store`** sem `Pragma` (RFC 9111) — Wave 6 corrigiu o legacy header em ADR sequencial.
- **OUTERJOIN condicional** ao filtro que efetivamente o usa (M-04). Evita plan overhead na maioria dos casos.
- **Logger INFO em router admin-only** loggando `user.id` + filtros aplicados — meta-rastro de quem leu o quê. NÃO grava em `audit_logs` (evita auto-referência + spam).

---

## 📌 Estado pós-Wave 6

**Wave 7+** ainda não definida. Backlog v3.0 só tem componentes de Wave 0–6; novas features virão de versão futura do backlog.

Wave 6 deixa para Wave 7+:
- E2E Playwright para `/auditoria` (e idealmente para outras rotas críticas)
- Reuso de filtros shared entre `/relatorios`, `/auditoria` e `/provas`
- Avaliação de REVOKE em `movimentacoes`/`etiquetas`
- Eventual link "Ver histórico desta prova" no drawer (consumindo `/by-prova/{id}`)

---

**Wave 6 completa. Sistema com cobertura funcional 100% do backlog v3.0 (Componentes 01-18).**
