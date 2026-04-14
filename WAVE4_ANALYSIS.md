# WAVE4_ANALYSIS.md — Dashboard e Visibilidade Operacional

**Wave:** 4
**Componente:** 15 — Dashboard em Tempo Real
**Prioridade:** Must Have
**Dependencia:** Componente 11 (Wave 3) — concluido
**Data:** 2026-04-14

---

## 1. Escopo Exato (extraido do Backlog v3.0)

### Componente 15 — Dashboard em Tempo Real

**Descricao:** Recharts + Supabase Realtime (WebSocket) + contadores clicaveis. Inclui contadores de Reprovadas e Com Motorista.

**Requisitos vinculados:**

| Req | Descricao | Prioridade |
|-----|-----------|------------|
| RF-014 | Dashboard com contadores em tempo real: Criadas hoje, Com vendedor, Aprovadas, Reprovadas, Aguardando envio, Com motorista, Na clicheria, Concluidas, Atrasadas. Contadores clicaveis. | Must |
| US-013 | "Como usuario da 3Studio, eu quero acessar o dashboard com os contadores de status para ter uma visao geral imediata da operacao." | — |
| RN-008 | Prova "Atrasada" = mesma status por mais tempo que o configurado (padrao 48h uteis). | Must |
| RNF-001 | Dashboard carrega em < 3 segundos com ate 30 usuarios simultaneos. | Must |
| RNF-008 | Disponibilidade continua em horario comercial (seg-sex 07-18h). Sem Realtime = refresh manual = violacao. | Must |

### Criterios de Aceitacao (US-013)

1. Os contadores refletem dados em tempo real.
2. O dashboard exibe: **Criadas hoje**, **Com vendedor**, **Aprovadas**, **Reprovadas**, **Aguardando envio**, **Com motorista**, **Na clicheria**, **Concluidas**, **Atrasadas**.
3. E possivel clicar em cada contador para ver as provas daquele status.

### Definition of Done (DoD Global do Backlog)

1. Code review.
2. Testes unitarios >= 80% em logica de negocio.
3. Testes de integracao passando.
4. Migrations versionadas e documentadas.
5. Funcionalidade validada contra criterios de aceitacao.
6. Sem erros no console/backend.
7. Documentacao interna atualizada.
8. Politicas RLS verificadas e versionadas.

---

## 2. Mapa de Dependencias com Waves 0/1/2/3

A Wave 4 **consome** os seguintes artefatos sem modifica-los:

| Artefato | Wave | Uso na Wave 4 |
|----------|------|---------------|
| `provas_digitais` (tabela + 13 registros) | 0 | Fonte de dados para contadores (`status`, `created_at`, `updated_at`) |
| `movimentacoes` (tabela + 7 registros) | 0 | Calculo de "Atrasadas" (ultimo `created_at` da movimentacao por prova) |
| `configuracoes_sistema.tempo_atraso_horas_uteis` | 0+2 | Parametro configavel para limite de atraso (RN-008) |
| `StatusProvaEnum` (10 valores) | 0 | Mapeamento para os 9 contadores do RF-014 |
| `GET /api/v1/provas/?status=X` | 2 (C07) | Destino dos contadores clicaveis (redirect com filtro) |
| `GET /api/v1/configuracoes/tempo_atraso_horas_uteis` | 2 (C09) | Leitura do parametro de atraso (se necessario no frontend) |
| `_scoping_filter(user)` | 2 | Scoping do dashboard por perfil (reuso) |
| `MAIN_NAV[0]` (placeholder "Dashboard") | 1 | Ativar href para `/dashboard` |
| Auth + RBAC (`get_current_user`) | 1 | Autenticacao no endpoint de dashboard |
| `@supabase/supabase-js` (frontend) | 1 | Cliente Supabase para subscription Realtime |
| Design tokens (`globals.css`) | 1 | Tokens `--color-card-*`, `--color-accent`, etc. |
| `framer-motion` | 3 (C12) | Animacoes nos contadores (reuso da dep existente) |

**Nenhum artefato de waves anteriores sera modificado**, exceto:
- `layout.tsx` linha 45: adicionar `href: "/dashboard"` ao item existente (1 palavra, identico ao padrao usado em `/escanear`).

---

## 3. Modelo de Dados

### Novas tabelas: NENHUMA

Os 9 contadores do RF-014 sao **derivados por query** das tabelas existentes. Nao ha necessidade de materializar contadores em tabela separada:
- Volume atual: 13 provas. Volume projetado Wave 4: < 500.
- Uma unica query com `GROUP BY status` + subquery de atraso atende RNF-001 (< 3s) neste volume.
- Se volume crescer acima de 10.000+, considerar materialized view em wave futura.

### Novas colunas: NENHUMA

### Novos indexes: NENHUM

Os indexes existentes ja cobrem as queries necessarias:
- `idx_provas_status` — `GROUP BY status`
- `idx_provas_status_created` — filtro composto `status + created_at`
- `idx_movimentacoes_prova_data` — `(prova_id, created_at DESC)` para ultima movimentacao

### Novas policies RLS: NENHUMA

O endpoint de dashboard usara `service_role` (como todos os outros endpoints) e aplicara scoping via `_scoping_filter()` na camada de aplicacao.

### Alteracao de infraestrutura Realtime:

```sql
-- Adicionar provas_digitais a publicacao Supabase Realtime
ALTER PUBLICATION supabase_realtime ADD TABLE provas_digitais;
```

**Justificativa:** A publicacao `supabase_realtime` existe no banco mas **nao tem nenhuma tabela adicionada** (confirmado via `pg_publication_tables`). Sem este comando, o Supabase Realtime nao consegue emitir eventos de INSERT/UPDATE em `provas_digitais`. Somente esta tabela sera adicionada — `movimentacoes`, `audit_logs`, etc. nao precisam de Realtime.

**Risco:** Nao precisa de migration Alembic — e uma configuracao do Supabase Realtime, gerenciada via SQL direto ou Dashboard. Sera documentada em `backend/migrations/rls/` como script SQL versionado por consistencia.

---

## 4. Contratos de API

### Endpoint novo: `GET /api/v1/provas/dashboard`

**Objetivo:** Retornar contadores agregados para o dashboard em uma unica chamada.

**RBAC:** Qualquer usuario autenticado (`get_current_user`). Scoping por perfil via `_scoping_filter()`.

```
GET /api/v1/provas/dashboard
Authorization: Bearer <jwt>

Response 200:
{
  "contadores": {
    "criadas_hoje": 3,
    "com_vendedor": 2,
    "aprovadas": 1,
    "reprovadas": 0,
    "aguardando_envio": 1,
    "com_motorista": 1,
    "na_clicheria": 2,
    "concluidas": 5,
    "atrasadas": 1
  },
  "total_ativas": 10,
  "tempo_atraso_horas": 48,
  "atualizado_em": "2026-04-14T15:30:00Z"
}
```

**Mapeamento RF-014 → StatusProvaEnum:**

| Contador RF-014 | Filtro SQL | Notas |
|-----------------|------------|-------|
| Criadas hoje | `status = 'CRIADA' AND created_at >= hoje_00h_BRT` | Fuso BRT (ADR-048 padrao) |
| Com vendedor | `status = 'RETIRADA_PELO_VENDEDOR'` | |
| Aprovadas | `status = 'APROVADA_PELO_VENDEDOR'` | |
| Reprovadas | `status = 'REPROVADA_PELO_VENDEDOR'` | |
| Aguardando envio | `status = 'DE_VOLTA_3STUDIO'` | Prova devolvida, aguardando motorista |
| Com motorista | `status = 'COM_MOTORISTA'` | |
| Na clicheria | `status IN ('ENVIADA_PARA_CLICHERIA', 'ENCAMINHADA_A_CLICHERIA')` | Ambas as rotas (padrao + direta) |
| Concluidas | `status = 'RECEBIDA_PELA_CLICHERIA'` | |
| Atrasadas | Calculo RN-008 (ver abaixo) | Cross-cutting, nao e um status |

**Calculo de "Atrasadas" (RN-008):**

Uma prova e "Atrasada" se:
1. Status NAO e terminal (`RECEBIDA_PELA_CLICHERIA` ou `CANCELADA`)
2. Tempo desde a **ultima movimentacao** (ou `created_at` se nunca movimentou) excede `tempo_atraso_horas_uteis`

```sql
-- Subquery: ultima movimentacao por prova (ou created_at se nenhuma)
WITH ultima_atividade AS (
  SELECT
    p.id,
    COALESCE(
      (SELECT MAX(m.created_at) FROM movimentacoes m WHERE m.prova_id = p.id),
      p.created_at
    ) AS ultima_at
  FROM provas_digitais p
  WHERE p.status NOT IN ('RECEBIDA_PELA_CLICHERIA', 'CANCELADA')
)
SELECT COUNT(*)
FROM ultima_atividade
WHERE ultima_at < NOW() - INTERVAL '1 hour' * :tempo_atraso_horas;
```

**Decisao sobre "horas uteis" vs "horas corridas":**

O Requisitos v3.0 (RN-008) especifica "horas uteis". Porem:
- A configuracao existente (`tempo_atraso_horas_uteis`) armazena apenas um inteiro (ex: 48).
- Nao ha definicao de calendario de feriados no sistema.
- Calcular horas uteis reais exige: horario comercial (07-18h), exclusao de sabados/domingos, feriados configurados.

**Proposta:** Implementar como **horas corridas** na Wave 4, com o nome do parametro preservado como `tempo_atraso_horas_uteis` (nao renomear — breaking change). Justificativa:
- O MVP opera em horario comercial (RNF-008: seg-sex 07-18h). Na pratica, 48h corridas ~ 4.4 dias uteis, o que e uma aproximacao razoavel.
- Calcular horas uteis reais requer: (a) tabela de feriados (nova tabela) + (b) logica de subtracao de weekends + (c) configuracao de horario comercial. Complexidade desproporcional para o volume atual.
- Se necessario, Wave 6 pode evoluir para calculo real de horas uteis com tabela de feriados.

> **PERGUNTA PARA O MARIO:** Aceita horas corridas como aproximacao na Wave 4, ou exige calculo real de horas uteis (com tabela de feriados)?

**Codigos HTTP:**

| Codigo | Cenario |
|--------|---------|
| 200 | Contadores retornados |
| 401 | Sem autenticacao |
| 502 | Erro de banco de dados |

**Pydantic Schemas:**

```python
class DashboardContadores(BaseModel):
    criadas_hoje: int
    com_vendedor: int
    aprovadas: int
    reprovadas: int
    aguardando_envio: int
    com_motorista: int
    na_clicheria: int
    concluidas: int
    atrasadas: int

class DashboardResponse(BaseModel):
    contadores: DashboardContadores
    total_ativas: int
    tempo_atraso_horas: int
    atualizado_em: datetime
```

---

## 5. Impacto no Frontend

### Rota Next.js nova: `/dashboard`

```
frontend/src/app/(dashboard)/dashboard/
  ├── page.tsx                 # Pagina principal do dashboard
  └── dashboard.module.css     # CSS Module dedicado
```

### Componentes

| Componente | Responsabilidade |
|------------|-----------------|
| `DashboardPage` | Pagina principal. Fetch inicial + subscription Realtime + layout dos cards |
| `ContadorCard` | Card individual: icone, label, valor numerico, cor, onClick → navigate |
| `ResumoChart` (opcional) | Grafico Recharts (bar chart horizontal) com distribuicao por status |

### Estados e Fluxo

1. **Carga inicial:** `GET /api/v1/provas/dashboard` → preenche contadores.
2. **Subscription Realtime:** Supabase channel em `provas_digitais` (INSERT/UPDATE). A cada evento, refetch do endpoint (debounced 2s para evitar flood).
3. **Click em contador:** `router.push('/provas?status=STATUS_VALUE')` usando o filtro URL-persisted que ja existe no C07.
4. **Fallback:** Se Realtime falhar (ex: desconexao), polling a cada 30s como degradacao graceful.

### Hooks novos

| Hook | Responsabilidade |
|------|-----------------|
| `useDashboard(getToken)` | GET `/provas/dashboard` + retorno tipado |
| `useRealtimeProvas(onEvent)` | Subscription Supabase Realtime em `provas_digitais`. Cleanup no unmount. |

### Integracoes com Supabase Realtime

```typescript
// Subscription em provas_digitais (INSERT e UPDATE)
const channel = supabase
  .channel('dashboard-provas')
  .on(
    'postgres_changes',
    { event: '*', schema: 'public', table: 'provas_digitais' },
    (payload) => {
      // Debounced refetch do endpoint /dashboard
      debouncedRefetch();
    }
  )
  .subscribe();
```

**Nota sobre RLS e Realtime:** O Supabase Realtime respeita RLS. O frontend usa a anon key com o token JWT do usuario logado. Os eventos recebidos sao filtrados pelas policies RLS existentes — o admin ve todas as mudancas, vendedor ve apenas suas provas, etc. Isso e consistente com o scoping do backend.

### Dependencias novas

| Pacote | Versao | Justificativa |
|--------|--------|---------------|
| `recharts` | `^2.15` | Grafico de distribuicao por status (DAT v2.0 especifica Recharts) |

**Dependencias reutilizadas:** `framer-motion` (animacao de entrada nos cards), `@supabase/supabase-js` (Realtime).

### Ativacao do menu

`layout.tsx` linha 45: `{ key: "dashboard", label: "Dashboard", icon: <HomeIcon />, href: "/dashboard" }`

---

## 6. Storage R2

**Nenhuma alteracao necessaria.** O dashboard nao interage com artes de provas. O bucket `rastreio-provas-artes` permanece inalterado.

---

## 7. Plano de Testes

### Camada 1 — Unitarios (backend)

| Teste | Cobertura |
|-------|-----------|
| `test_dashboard_contadores_mapping` | Mapeamento correto de cada status para o contador correspondente |
| `test_dashboard_criadas_hoje_filtro_brt` | `criadas_hoje` usa fuso BRT (padrao ADR-048) |
| `test_dashboard_atrasadas_calculo` | Prova com `updated_at` > `tempo_atraso_horas` aparece como atrasada |
| `test_dashboard_atrasadas_exclui_terminais` | `RECEBIDA_PELA_CLICHERIA` e `CANCELADA` nunca contam como atrasadas |
| `test_dashboard_na_clicheria_agrupa_dois_status` | `ENVIADA_PARA_CLICHERIA` + `ENCAMINHADA_A_CLICHERIA` somam no mesmo contador |
| `test_dashboard_scoping_vendedor` | Vendedor ve apenas contadores das suas provas |
| `test_dashboard_scoping_admin` | Admin ve contadores de todas as provas |
| `test_dashboard_pydantic_schema` | Validacao do schema `DashboardResponse` |

**Meta:** >= 80% das linhas do handler/service de dashboard.

### Camada 2 — Integracao (backend)

| Teste | Cobertura |
|-------|-----------|
| `test_dashboard_endpoint_200` | GET retorna 200 com estrutura correta |
| `test_dashboard_endpoint_401` | Sem auth retorna 401 |
| `test_dashboard_contadores_consistentes` | Soma dos contadores individuais = `total_ativas` + `concluidas` |
| `test_dashboard_tempo_atraso_from_config` | `tempo_atraso_horas` reflete valor de `configuracoes_sistema` |
| `test_dashboard_scoping_vendedor_ve_so_suas` | Vendedor com 2 provas ve contadores refletindo apenas suas 2 |

**Meta:** 100% do endpoint coberto.

### Camada 3 — Frontend

| Teste | Metodo |
|-------|--------|
| Contadores renderizam com valores do backend | Smoke manual |
| Click em contador navega para `/provas?status=X` | Smoke manual |
| Realtime: criar prova via outro browser → contador atualiza | Smoke manual com 2 sessoes |
| Fallback polling funciona se Realtime desconectar | Smoke manual (desconectar WS) |
| Responsividade mobile (> 5") | Smoke manual |
| `tsc --noEmit` limpo | CI |
| `next lint` limpo | CI |
| `next build` OK | CI |

---

## 8. Riscos e Pontos de Atencao

### R-01 — Supabase Realtime free tier: limite de conexoes simultaneas

**Risco:** O free tier do Supabase permite **ate 200 conexoes simultaneas de Realtime** e **200 mensagens/segundo**. Para 30 usuarios simultaneos (RNF-001), seriam 30 WebSockets — bem dentro do limite.

**Mitigacao:** Monitorar via Supabase Dashboard. Se atingir limites, degradar para polling.

### R-02 — Publication `supabase_realtime` sem tabelas

**Risco:** Confirmado via MCP que a publicacao existe mas **nenhuma tabela esta adicionada**. Sem o `ALTER PUBLICATION`, o Realtime nao emite eventos.

**Mitigacao:** Aplicar o SQL antes de iniciar o frontend Realtime. Sera o primeiro passo do Bloco 4.1.

### R-03 — Calculo de "Atrasadas" com horas corridas vs uteis

**Risco:** Usar horas corridas pode gerar falsos positivos de atraso em finais de semana. Ex: prova movimentada sexta 17h aparece como "atrasada" segunda 17h (48h corridas), mas sao apenas 2h uteis.

**Mitigacao:** Proposta de horas corridas na Wave 4 (simplicidade). Pendente aprovacao do Mario. Se requerido horas uteis, complexidade aumenta significativamente (tabela de feriados + logica de calendario).

### R-04 — Performance do calculo de atrasadas em escala

**Risco:** A subquery de "Atrasadas" faz `MAX(created_at)` por prova em `movimentacoes`. Com volume alto (>10k provas ativas), pode degradar.

**Mitigacao:** O index `idx_movimentacoes_prova_data (prova_id, created_at DESC)` ja existe e cobre este caso. Para volume >10k, considerar materialized view refreshed por cron (Wave 6).

### R-05 — Recharts bundle size

**Risco:** Recharts adiciona ~200-300 KB ao bundle JS.

**Mitigacao:** Import seletivo (`import { BarChart, Bar, XAxis, YAxis } from 'recharts'`) para tree-shaking. Monitorar via `next build` (First Load JS < 250 kB para a pagina de dashboard).

### R-06 — Realtime + RLS: visibilidade por perfil

**Risco:** Eventos Realtime sao filtrados por RLS. Um vendedor recebe eventos apenas das suas provas, o que significa que seu dashboard so atualiza em real-time para mudancas nas suas provas. Para mudancas em provas de outros vendedores, o vendedor nao recebe evento e o contador nao atualiza.

**Mitigacao:** Aceitavel — o vendedor so ve suas proprias provas (por design). Para admin (ve tudo), RLS nao filtra e o Realtime funciona plenamente. Para vendedor, o comportamento e consistente com o scoping existente.

### R-07 — Next.js 14 vulnerabilidades pre-existentes

**Risco:** 4 high severity do `npm audit` (debito B-02 da Wave 3). Nao sao regressao da Wave 4.

**Mitigacao:** Aceito como TODO Wave 6 (decisao anterior). Nao afeta funcionalidade do dashboard.

---

## 9. Ordem de Implementacao em Blocos

### Bloco 4.1 — Infraestrutura Realtime + Backend Dashboard

**Escopo:**
1. Adicionar `provas_digitais` a publicacao `supabase_realtime` (SQL versionado)
2. Criar Pydantic schemas: `DashboardContadores`, `DashboardResponse`
3. Implementar `GET /api/v1/provas/dashboard` com:
   - 9 contadores conforme mapeamento RF-014
   - Calculo de "Atrasadas" (RN-008)
   - Scoping via `_scoping_filter()`
   - Leitura de `tempo_atraso_horas_uteis` da config
4. Testes unitarios + integracao (meta: >= 15 testes)
5. Ruff + pytest com cobertura

**Entregaveis:** Endpoint funcional, testes passando, SQL de Realtime versionado.

**Estimativa de arquivos:**
- `backend/app/domain/schemas/dashboard.py` — novo
- `backend/app/api/v1/provas.py` — +handler (adicionar ao router existente)
- `backend/tests/test_provas_api.py` — +testes dashboard
- `backend/migrations/rls/007_enable_realtime_provas.sql` — novo (SQL de publicacao)

### Bloco 4.2 — Frontend Dashboard (Pagina + Cards + Recharts)

**Escopo:**
1. Criar rota `/dashboard` (page.tsx + CSS Module)
2. Hook `useDashboard` para fetch do endpoint
3. Layout de cards (9 contadores) com tokens de design existentes
4. Integracao Recharts (grafico de distribuicao)
5. Click em contador → navigate para `/provas?status=X`
6. Ativar item do menu ("Dashboard" → href="/dashboard")
7. `tsc --noEmit` + `next lint` + `next build`

**Entregaveis:** Pagina funcional com dados estaticos (sem Realtime ainda).

**Estimativa de arquivos:**
- `frontend/src/app/(dashboard)/dashboard/page.tsx` — novo
- `frontend/src/app/(dashboard)/dashboard/dashboard.module.css` — novo
- `frontend/src/hooks/useDashboard.ts` — novo
- `frontend/src/app/(dashboard)/layout.tsx` — 1 palavra (href)
- `frontend/package.json` — +recharts

### Bloco 4.3 — Supabase Realtime + Polish

**Escopo:**
1. Hook `useRealtimeProvas` (subscription + cleanup)
2. Integrar Realtime no dashboard (debounced refetch a cada evento)
3. Fallback para polling (30s) se Realtime desconectar
4. Animacoes de entrada/atualizacao nos cards (framer-motion)
5. Responsividade mobile (>= 5")
6. Smoke E2E manual (2 sessoes simultaneas)
7. Atualizar `CHANGELOG.md`, `DECISIONS.md`, `CLAUDE.md`

**Entregaveis:** Dashboard completo com tempo real, documentacao atualizada.

**Estimativa de arquivos:**
- `frontend/src/hooks/useRealtimeProvas.ts` — novo
- `frontend/src/app/(dashboard)/dashboard/page.tsx` — update (Realtime)
- `frontend/src/app/(dashboard)/dashboard/dashboard.module.css` — update (responsive)
- `CHANGELOG.md` — update
- `DECISIONS.md` — novos ADRs
- `CLAUDE.md` — Wave 4 status

### Bloco 4.4 — Closeout + Documentacao

**Escopo:**
1. `WAVE4_CLOSEOUT.md` com DoD item por item
2. Metricas finais consolidadas (testes, bundle, rotas)
3. Atualizacao final de `CLAUDE.md` (tabela de waves, endpoints, rotas frontend)
4. Verificacao de advisors Supabase pos-deploy

---

## Resumo de Impacto

| Categoria | Antes (Wave 3) | Depois (Wave 4) | Delta |
|-----------|----------------|-----------------|-------|
| Testes backend | 407 | ~425+ | +18+ |
| Rotas backend | 28 | 29 | +1 |
| Rotas frontend | 8 | 9 | +1 |
| Policies RLS | 12 | 12 | 0 |
| alembic_version | 009 | 009 | 0 |
| Deps npm prod | 8 | 9 | +1 (recharts) |
| Tabelas dominio | 6 | 6 | 0 |
| Realtime tables | 0 | 1 | +1 (provas_digitais) |
