# WAVE 6 — ANÁLISE E PLANO DE EXECUÇÃO

> **Componente 18 — Interface de Log de Auditoria** (Should Have, RNF-005, acesso restrito ao perfil 3Studio).
> **Autor:** Claude (engenheiro sênior fullstack) · **Data:** 2026-04-14 · **Status:** aguardando aprovação do Renan
> **Escopo:** entrega da **interface de consulta** ao log imutável já gerado desde a Wave 3. Zero alteração na camada de escrita, zero alteração no schema da tabela.

---

## 1. ESCOPO EXATO DA WAVE 6

### 1.1 Componente 18 (verbatim do Backlog v3.0)

| Campo | Valor |
|---|---|
| **ID** | 18 |
| **Nome** | Interface de Log de Auditoria |
| **Prioridade** | Should Have |
| **Depends on** | 11 |
| **Descrição** | "Tabela imutável — acesso restrito ao perfil 3Studio — RNF-005 — inclui registros de reprovação e reinício de ciclo" |
| **Justificativa (Backlog)** | "O log em si é gerado a partir do Componente 11 (Wave 3) — esta entrada entrega apenas a interface de consulta acessível pelo perfil 3Studio. Reclassificado de Must Have para Should Have: o log existe e é imutável independentemente desta tela. A interface de visualização não bloqueia a operação." |

### 1.2 RNF-005 (verbatim dos Requisitos v3.0)

> **ID RNF-005 — Segurança:** "O sistema deve manter um log de auditoria completo e imutável de todas as movimentações de provas, incluindo reprovações e reinícios de ciclo, acessível apenas pelo perfil 3Studio (Administrador)."

### 1.3 Perfil 3Studio (verbatim dos Requisitos v3.0, Tabela 2 — Atores/Perfis)

> "3Studio (Administrador): Acesso total ao sistema. Cria provas digitais, gerencia configurações, cadastra usuários, acessa relatórios e dashboard. Responsável pela operação e controle do fluxo. **Único perfil com acesso à tela de configurações, ao log de auditoria e à função de reiniciar o ciclo de provas reprovadas.**"

**Mapeamento em código (confirmado):** `usuario.is_admin = true`. ADR-018 (Wave 1) unificou o conceito de "admin" em `is_admin` puro, desvinculando-o do `setor`. Gate já existente: `Depends(get_admin_user)` em `backend/app/api/deps.py:95-104`. **Wave 6 reaproveita — não reescreve.**

### 1.4 Escopo positivo (o que a Wave 6 entrega)

1. **Endpoint backend `GET /api/v1/auditoria/`** — listagem paginada do log, admin-only, com filtros.
2. **Endpoint backend `GET /api/v1/auditoria/{log_id}`** — detalhe pontual de uma entrada (para modal/popover).
3. **Camada de projeção** que enriquece cada entrada com:
   - Nome/setor do usuário autor (join leve com `usuarios`);
   - Nome/nº de requerimento da prova relacionada (join leve com `provas_digitais`);
   - **Campo derivado `tipo_evento`** que resolve o gap de granularidade da camada de escrita (seção 1.6).
4. **Rota frontend `/auditoria`** — página Next.js acessível apenas a admin, com:
   - Listagem em tabela com colunas: *Quando · Quem · Evento · Prova · IP*;
   - Filtros: período (início/fim), autor, prova (por número de requerimento), tipo de evento;
   - Paginação via cursor (carregar mais) ou botões próximo/anterior;
   - Modal/painel com `detalhes_json` formatado quando clicar numa linha.
5. **Suíte de testes** cobrindo os quatro objetivos críticos: **RBAC** (não-admin recebe 403), **imutabilidade** (inexistência de rota de escrita), **filtros** (cada filtro e suas combinações), **projeção** (cancelamento aparece como "Cancelamento", reinício como "Reinício de ciclo").
6. **Atualização de `CLAUDE.md`, `CHANGELOG.md`, `DECISIONS.md`** ao fim de cada bloco (convenção das Waves anteriores).

### 1.5 Escopo negativo (o que NÃO será entregue)

- ❌ **Não altera a camada de escrita** (`audit_service.py`, `state_machine.py`, call sites de `log_audit`).
- ❌ **Não altera o schema de `audit_logs`** (colunas, triggers, constraints).
- ❌ **Não altera a policy RLS existente** (`pol_audit_select` já é exatamente o que precisamos).
- ❌ **Não cria nova policy RLS** de INSERT/UPDATE/DELETE em `audit_logs` — o trigger `trg_audit_logs_imutavel` + ausência de policy INSERT já garantem imutabilidade e cobrem a defesa em profundidade.
- ❌ **Não exporta audit log em CSV/PDF** — não há RF-exp para audit log (RF-015 só cobre relatórios da Wave 5). Fica para bloco opcional ou wave futura, **salvo autorização explícita** do Renan.
- ❌ **Não loga acessos à tela de auditoria** — meta-auditoria gera ruído e pode virar recursão; default é não logar.
- ❌ **Não toca `/dashboard`, `/relatorios`, `/provas`, `/usuarios`, `/configuracoes`, `/escanear`, `/nova-prova`, `/login`** — Waves 0-5 continuam congeladas.
- ❌ **Não muda Railway/Vercel/R2/Realtime** — Wave 6 é feature frontend+backend pura.

### 1.6 O gap de granularidade da camada de escrita (observação carregada do checkpoint)

**Fato:** o `state_machine.py:348` seta `acao_audit = "transitar_status"` como default. O único branch que muda esse valor é REPROVADA→CRIADA que vira `"reiniciar_ciclo"` (linha 374). **Cancelamento (C13) cai no default** — é logado como `acao="transitar_status"` com `status_novo=CANCELADA` e `motivo_cancelamento` dentro do `detalhes_json` da movimentação.

**Implicação para a Wave 6:** a UI precisa distinguir visualmente "Cancelamento", "Reprovação" e "Transição de status comum" **sem tocar** na camada de escrita (que está congelada). A solução fica no **backend projection layer**, via um campo derivado `tipo_evento` calculado a partir de `(acao, detalhes_json)`:

| `acao` do banco | Condição no `detalhes_json` | `tipo_evento` derivado | Label pt-BR |
|---|---|---|---|
| `criar_prova` | — | `CRIACAO_PROVA` | Criação de prova |
| `escanear_prova` | — | `ESCANEAMENTO` | Escaneamento |
| `transitar_status` | `para == "CANCELADA"` | `CANCELAMENTO` | Cancelamento |
| `transitar_status` | `para == "REPROVADA_PELO_VENDEDOR"` | `REPROVACAO` | Reprovação |
| `transitar_status` | qualquer outro `para` | `TRANSICAO_STATUS` | Transição de status |
| `reiniciar_ciclo` | — | `REINICIO_CICLO` | Reinício de ciclo |
| `atualizar_configuracao` | — | `ALTERACAO_CONFIG` | Alteração de configuração |

**Por que no backend e não no frontend:** manter a regra única em um único ponto para o filtro do endpoint, a label e os testes trabalharem com o mesmo enum. A UI recebe `tipo_evento` pronto e o filtro por tipo vira um `WHERE` direto na query (com `CASE WHEN` ou JSONB extraction, dependendo da eficiência do EXPLAIN).

**Decisão de escopo:** corrigir o gap na camada de escrita (introduzir `acao="cancelar_prova"` dedicada, por exemplo) **seria fora de escopo** — quebraria a regra inviolável #1 (não modificar Wave 3 sem autorização). Se o Renan preferir essa abordagem, abro `WAVE6_BLOCKERS.md` e aguardo a decisão antes de seguir.

### 1.7 Definition of Done (critério objetivo)

Wave 6 está "pronta" quando:

1. ✅ `GET /api/v1/auditoria/` lista as 49 linhas existentes com paginação cursor-based, ordem `created_at DESC, id DESC`.
2. ✅ Usuário **não-admin** chamando qualquer endpoint de auditoria recebe **403**.
3. ✅ Cada filtro isoladamente e em combinação retorna resultados corretos (validado por teste de integração contra banco real ou mock fiel).
4. ✅ Um cancelamento (prova em CANCELADA) aparece na listagem com `tipo_evento = "CANCELAMENTO"`, label "Cancelamento", e o `motivo_cancelamento` visível no modal de detalhes.
5. ✅ Um reinício de ciclo aparece com `tipo_evento = "REINICIO_CICLO"` — e como ainda não há nenhum em produção, o teste cria uma linha via fixture.
6. ✅ Rota `/auditoria` no Next.js renderiza a listagem real (conectada ao backend), com filtros funcionando, paginação funcional, e acesso bloqueado para não-admin (redirect ou 403 handler).
7. ✅ Nenhum endpoint de escrita em `audit_logs` foi adicionado ao backend (grep verifica zero `INSERT`/`UPDATE`/`DELETE` contra `audit_logs` fora de `audit_service.py`).
8. ✅ Cobertura de testes: **≥ 80%** nos arquivos novos (`app/api/v1/auditoria.py`, `app/domain/schemas/auditoria.py`, `app/services/auditoria_projection.py`). Testes do frontend executam o fluxo golden path via preview server.
9. ✅ `get_advisors` Supabase (security + performance) continua com o mesmo conjunto de WARN/INFO pré-Wave 6 (nenhum regresso).
10. ✅ `ruff check .` limpo, `pytest` verde (novo total ≈ **459 + N**), sem testes legados quebrados.
11. ✅ `CLAUDE.md`, `CHANGELOG.md`, `DECISIONS.md` atualizados, seguindo a convenção das Waves anteriores.

---

## 2. MAPA DE DEPENDÊNCIAS COM WAVES 0-5 (consumir sem modificar)

### 2.1 O que Wave 6 USA (mas NÃO modifica)

| Origem | Item | Uso pela Wave 6 | Regra |
|---|---|---|---|
| **Wave 0 — Infra** | Tabela `audit_logs` (migration `001`) com 8 colunas e trigger de imutabilidade | SELECT read-only | **Não toca** |
| Wave 0 | Função `fn_bloquear_alteracao()` + trigger `trg_audit_logs_imutavel` | Garantia de imutabilidade (defesa em profundidade) | **Não toca** |
| Wave 0 | Índices atuais de `audit_logs`: `idx_audit_prova`, `idx_audit_usuario`, `idx_audit_acao`, `idx_audit_created_at` + `audit_logs_pkey` | Queries de listagem e filtro (seção 3.2 valida cobertura) | **Não remove nem renomeia** |
| **Wave 1 — Auth + RBAC** | `get_current_user`, `get_admin_user`, `require_role` em `backend/app/api/deps.py` | Dependency injection para gate 3Studio-only | **Não modifica — importa como está** |
| Wave 1 | Modelo ORM `Usuario` com `is_admin` (coluna adicionada pela migration `004`) | Join para exibir nome + setor do autor | **Não modifica** |
| Wave 1 | Policy RLS `pol_audit_select` (criada na RLS 001→004, otimizada na RLS 005 com `(SELECT auth.uid())`) | Defesa em profundidade quando/se frontend chamar Supabase JS direto. Backend usa `service_role` e bypassa RLS. | **Não modifica — documento no plano que continua ativa** |
| **Wave 2 — Núcleo** | Modelo `ProvaDigital` com `nro_requerimento`, `nome`, `cliente` | Join para exibir a prova relacionada em cada log | **Não modifica** |
| Wave 2 | `audit_service.log_audit()` (ADR-039) | Observa as chamadas existentes para confirmar o schema de `detalhes_json` por `acao` | **Não modifica — é a via de escrita, Wave 6 é só leitura** |
| Wave 2 | Call site `criar_prova` em `provas.py:501` e `atualizar_configuracao` em `configuracoes.py:223` | Inspeção apenas — define o shape do `detalhes_json` que a projeção precisa conhecer | **Não toca** |
| Wave 2 | Componente 07 — `/provas` (listagem filtrada com URL-persisted params) | Padrão visual e de UX reutilizável: filtros no topo + tabela abaixo + paginação | **Não toca — apenas inspira o layout** |
| Wave 2 | Componente 08 — `/provas/[id]` (detalhe + timeline Wave 3) | Ponto de retorno: no modal de detalhes de um log, um link rápido "abrir prova" leva para `/provas/{prova_id}` quando `prova_id != null` | **Não toca** |
| **Wave 3 — Scanner + Transições** | Call site `executar_transicao` em `state_machine.py:430` | Inspeção apenas — confirma a origem de `transitar_status` e `reiniciar_ciclo` | **Não toca** |
| Wave 3 | Call site `escanear_prova` em `provas.py:2378` | Inspeção apenas | **Não toca** |
| Wave 3 | Componente 12 — Timeline visual em `/provas/[id]` com Framer Motion | Referência de UX para quem quiser ver o histórico de uma prova específica | **Não toca** |
| Wave 3 | Endpoints admin C13 (cancelar) + C14 (reiniciar-ciclo) | Fonte do `tipo_evento = CANCELAMENTO`/`REINICIO_CICLO` | **Não toca** |
| **Wave 4 — Dashboard** | Hook `useCurrentUser` (detecta `is_admin` no frontend) + layout do dashboard que já esconde/mostra menus admin | Reaproveitado para proteger a rota `/auditoria` (guard client-side) | **Não modifica — importa e usa** |
| Wave 4 | `apiFetch` wrapper (`frontend/src/lib/api.ts`) | Usado pelo hook `useAuditoria` para chamar o backend com token injection | **Não modifica** |
| **Wave 5 — Relatórios** | Padrão de filtro de período (ADR-095: início/fim, date-range com label pt-BR, debounce no hook) | Reaproveitado para o filtro de período do audit log | **Não modifica — imita o padrão** |
| Wave 5 | `relatorios.module.css` (padrão de tabela, card, filtro) | **Apenas referência visual** — Wave 6 cria seu próprio CSS Module | **Não modifica** |

### 2.2 O que Wave 6 CRIA (arquivos novos)

**Backend:**
- `backend/app/api/v1/auditoria.py` — router com 2 endpoints (list + detail)
- `backend/app/domain/schemas/auditoria.py` — Pydantic v2 schemas (request params, response items, paginação)
- `backend/app/services/auditoria_projection.py` — função `projetar_tipo_evento(log: AuditLog) -> TipoEvento` (regra única do gap 1.6) + função `enriquecer_log(log, usuario, prova) -> AuditLogResponse`
- `backend/app/services/auditoria_query.py` — builder da query SQLAlchemy com filtros, keyset pagination e joins otimizados
- `backend/tests/test_auditoria_projection.py` — testes unitários da projeção (mínimo 1 teste por linha da matriz 1.6)
- `backend/tests/test_auditoria_api.py` — testes de integração dos 2 endpoints (RBAC, filtros, paginação, imutabilidade garantida pelo cenário "não existe rota de escrita")

**Frontend:**
- `frontend/src/lib/types/auditoria.ts` — espelho TS das schemas Pydantic
- `frontend/src/hooks/useAuditoria.ts` — lista via `apiFetch` com filtros + paginação cursor
- `frontend/src/hooks/useAuditoriaDetail.ts` — detalhe pontual
- `frontend/src/app/(dashboard)/auditoria/page.tsx` — página principal (server component + client component para filtros/paginação)
- `frontend/src/app/(dashboard)/auditoria/AuditoriaClient.tsx` — client component com estado dos filtros
- `frontend/src/app/(dashboard)/auditoria/AuditoriaDetailModal.tsx` — modal de detalhes com `detalhes_json` formatado
- `frontend/src/app/(dashboard)/auditoria/auditoria.module.css` — CSS Module isolado

**Menu lateral:**
- Atualizar `frontend/src/app/(dashboard)/layout.tsx` **para ativar** o item "Auditoria" (hoje placeholder ou inexistente — vou confirmar no Bloco 6.0). Visível **apenas** quando `user.is_admin === true`.

### 2.3 Waves congeladas — proibição explícita

**Nenhum dos arquivos abaixo será tocado pela Wave 6:**
- `backend/migrations/versions/001`–`009` (todas)
- `backend/migrations/rls/001`–`007` (todas — inclui a policy `pol_audit_select`)
- `backend/app/services/audit_service.py` (camada de escrita do log)
- `backend/app/services/state_machine.py`
- `backend/app/services/qrcode_service.py`, `etiqueta_service.py`, `r2_signed.py`
- `backend/app/api/v1/users.py`, `provas.py`, `configuracoes.py`
- `backend/app/api/deps.py` (reaproveita, não modifica)
- `backend/app/core/*` (config, jwt, r2, supabase_admin)
- `backend/app/db/models.py` — **exceção única**: adicionar classe `AuditLog` já existe (não toca). Se precisar adicionar um helper `__repr__` é alteração mínima; caso contrário, zero tocado.
- `frontend/src/app/(dashboard)/{dashboard,usuarios,nova-prova,provas,escanear,configuracoes,relatorios}` (todas)
- `frontend/src/lib/types/{prova,usuario,configuracao,relatorio}.ts`
- Testes das Waves 0-5 (todos os 459 atuais precisam continuar passando sem modificação).

**Se durante a implementação identificar bug real em Wave anterior:** abro `WAVE6_BLOCKERS.md` com descrição + impacto + proposta e aguardo decisão — não conserto silenciosamente.

---

## 3. MODELO DE DADOS

### 3.1 Tabela `audit_logs` (estado atual — fonte de verdade)

```sql
-- Criada na migration 001 (Wave 0), intocada desde então.
CREATE TABLE audit_logs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prova_id      UUID REFERENCES provas_digitais(id),  -- nullable
    usuario_id    UUID NOT NULL REFERENCES usuarios(id),
    acao          VARCHAR(100) NOT NULL,
    detalhes_json JSONB,                                  -- nullable
    ip_address    INET,                                   -- nullable
    user_agent    TEXT,                                   -- nullable
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

- **RLS:** habilitada, única policy `pol_audit_select` (SELECT, `is_admin=true` via `(SELECT auth.uid())`).
- **Trigger:** `trg_audit_logs_imutavel` BEFORE UPDATE OR DELETE → `fn_bloquear_alteracao()` (lança exceção com mensagem RNF-005).
- **Volumetria atual:** **50 linhas** (Bloco 6.0, sistema vivo), 144 kB total, 2 usuários distintos, 13 provas distintas, 5 sem IP (dev early), 0 sem user_agent. **1 cancelamento real** já em prod com `detalhes_json.motivo_cancelamento` preenchido — pronto para validar a projeção `CANCELAMENTO` com dado real. **Zero** linhas com `acao='reiniciar_ciclo'` — fixture dedicada cria 1 em memória para os testes.

### 3.2 Cobertura de índices × filtros propostos

A Wave 6 vai expor 6 filtros. Mapeamento contra os 5 índices atuais de `audit_logs`:

| Filtro | Query (pseudo) | Índice que cobre | Ação |
|---|---|---|---|
| Período (`created_at >= X AND created_at < Y`) | `WHERE created_at BETWEEN ...` + `ORDER BY created_at DESC` | `idx_audit_created_at` | ✅ cobre |
| Autor (`usuario_id = ?`) | `WHERE usuario_id = ?` | `idx_audit_usuario` | ✅ cobre |
| Prova (`prova_id = ?` ou `nro_requerimento`) | `WHERE prova_id = ?` (após resolver `nro_req` → `id` em subquery) | `idx_audit_prova` | ✅ cobre |
| Ação crua (`acao IN (...)`) | `WHERE acao = ANY(...)` | `idx_audit_acao` | ✅ cobre |
| Tipo de evento derivado (`tipo_evento IN ('CANCELAMENTO', ...)`) | WHERE combinando `acao` + `detalhes_json->>'para'` | `idx_audit_acao` (para parte `acao`) + full table scan do JSONB (pequeno volume) | ✅ cobre hoje; revisitar se dor futura |
| Keyset pagination (`(created_at, id) < (?, ?)`) | `ORDER BY created_at DESC, id DESC LIMIT N` | `idx_audit_created_at` + PK `audit_logs_pkey` | ✅ cobre |

**Conclusão:** **zero índices novos** na primeira versão. Todos os filtros especificados caem em índices existentes. Justificativa formal (ADR-099): **nenhum índice especulativo — medir antes de criar**.

**Validado empiricamente no Bloco 6.0** (5 EXPLAIN ANALYZE contra o banco real de 50 linhas):

| Query | Índice usado | Execution Time |
|---|---|---|
| Q1 — listagem default + JOINs + keyset | `idx_audit_created_at` (Index Scan Backward) + Nested Loop LEFT JOIN | **1.315 ms** |
| Q2 — filtro período 2 dias + keyset | `idx_audit_created_at` (Index Cond range) | **0.219 ms** |
| Q3 — `tipo_evento=CANCELAMENTO` (JSONB extract) | `idx_audit_acao` (Index Scan) + Filter heap | **2.176 ms** (Rows Removed by Filter: 7) |
| Q4 — filtro por autor + keyset | `idx_audit_usuario` (Index Scan) | **1.923 ms** |
| Q5 — período + `acao IN (2)` | `idx_audit_acao` (Bitmap Heap Scan) + Filter `created_at` | **0.184 ms** |

**Zero Seq Scan** em `audit_logs` em qualquer consulta. Q3 é o único candidato legítimo a índice parcial futuro — registrado como **follow-up condicional** no ADR-099 (criar `idx_audit_cancelamentos` somente se `pg_stat_statements` mostrar tempo sustentado > 50 ms).

### 3.3 Views read-only

**Decisão:** **não criar view**.
Motivos:
- Views materializadas adicionariam complexidade de refresh (não é caso de uso aqui — dados não crescem em rajada).
- Views não-materializadas seriam apenas açúcar sintático — a query do backend já pode fazer o `LEFT JOIN usuarios` + `LEFT JOIN provas_digitais` com `joinedload()`/`selectinload()`.
- Manter a lógica de projeção em código Python facilita testes unitários da função `projetar_tipo_evento`.
- Views exigiriam migration Alembic e RLS dedicada — overengineering para 6 filtros sobre uma tabela de 49 linhas.

### 3.4 Política RLS — proposta

**Estado atual (inspecionado via MCP):**
```sql
pol_audit_select  FOR SELECT  USING (
  EXISTS (SELECT 1 FROM usuarios u
          WHERE u.auth_uid = (SELECT auth.uid()) AND u.is_admin = true)
)
```

**Proposta Wave 6: não mexer.** A policy já tem exatamente a semântica que a RNF-005 exige (SELECT admin-only). O backend vai usar `service_role` (que bypassa RLS por design — ADR-046/049), mas a policy permanece ativa como defesa em profundidade para qualquer acesso direto via Supabase JS client (presente ou futuro).

**O que NÃO adicionar:**
- Policy `pol_audit_insert`/`update`/`delete` com `USING (false)` — o trigger já bloqueia UPDATE/DELETE e o backend é quem faz o INSERT via service_role. Adicionar policies redundantes polui `pg_policies` sem ganho real.
- Policy para setor específico — ADR-018 deixa claro que admin = `is_admin=true`, não setor STUDIO.

**Se o Renan quiser "sobrepor" com uma policy INSERT admin-only por paridade** com `pol_movimentacoes_insert` (ADR-082, RLS 006), posso adicionar `008_audit_logs_insert_admin_only.sql` como **único script novo de RLS**. Isso é decisão a tomar antes do bloco 6.1 — não entra como default. Minha recomendação: **não adicionar** (redundante com `service_role` + ausência de policy de INSERT bloqueia por default no Postgres quando RLS está ativa).

### 3.5 Migrations Alembic

**Zero migrations Alembic nesta Wave**, **exceto** se a decisão da seção 3.2 (validação via EXPLAIN) revelar necessidade de índice composto. Neste caso, seria:

- `backend/migrations/versions/010_add_audit_logs_indexes_wave6.py`
- Reversível (`downgrade()` implementado)
- ADR-099 documentaria a escolha do índice com EXPLAIN antes/depois

**Estado-base da Wave 6:** `alembic_version` continua `009`. Se migration for criada, sobe para `010`.

---

## 4. CONTRATOS DE API

### 4.1 Design decisions

| Decisão | Escolha | Razão |
|---|---|---|
| Prefixo | `/api/v1/auditoria` | Consistente com `/api/v1/provas`, `/api/v1/configuracoes`, `/api/v1/users` (pt-BR em todo o projeto) |
| Paginação | **Keyset/cursor** via `(created_at DESC, id DESC)` | Estável sob writes concorrentes, O(1) por página, aproveita `idx_audit_created_at` + PK; offset degrada com crescimento da tabela |
| `total_count` | `total_estimado` via `COUNT(*)` **filtrado** (49 linhas hoje, ainda aceitável) + cap de 100k | Evita `pg_class.reltuples` (impreciso com filtro); se a tabela crescer muito, migrar para estimativa posteriormente |
| Ordem | `created_at DESC, id DESC` fixo (não configurável) | Caso de uso: "mostre os eventos mais recentes primeiro". Não há valor em permitir reordenar na MVP |
| Tamanho de página | `limit` 1–100, default 50 | Bate com `/api/v1/provas` da Wave 2 |
| Enriquecimento | LEFT JOIN `usuarios` + `provas_digitais` | Evita N+1 no frontend, ocupa o mesmo "round trip" |
| Projeção `tipo_evento` | Computada em Python (função pura, testável) | A regra é simples o suficiente; SQL CASE ficaria confuso com extração JSONB |

### 4.2 `GET /api/v1/auditoria/` — listagem

**Auth:** `Depends(get_admin_user)` → 403 para qualquer `is_admin=false`.

**Query params (Pydantic v2 no backend):**

| Param | Tipo | Obrigatório | Default | Regra |
|---|---|---|---|---|
| `data_inicio` | `date` ISO-8601 | ❌ | — | Interpretado como `00:00:00` no timezone do servidor (America/Sao_Paulo). Se presente, filtra `created_at >= data_inicio` |
| `data_fim` | `date` ISO-8601 | ❌ | — | Interpretado como `23:59:59.999999` no timezone do servidor. Filtra `created_at <= data_fim` |
| `usuario_id` | `UUID` | ❌ | — | Filtra `usuario_id = ?` |
| `nro_requerimento` | `string` (max 50) | ❌ | — | Resolvido em subquery `prova_id IN (SELECT id FROM provas_digitais WHERE nro_requerimento = ?)`; retorna vazio se não existir |
| `acao` | `list[str]` | ❌ | — | Multi-value via `?acao=criar_prova&acao=escanear_prova`. Whitelist validada (5 valores: `criar_prova`, `escanear_prova`, `transitar_status`, `reiniciar_ciclo`, `atualizar_configuracao`) |
| `tipo_evento` | `list[TipoEventoEnum]` | ❌ | — | Multi-value. Quando presente, compila para WHERE combinando `acao` + `detalhes_json->>'para'`. Mutuamente exclusivo com `acao` (usar um ou outro) |
| `cursor` | `string` opaco base64 | ❌ | — | Opaco: base64 de `{"created_at": "...", "id": "..."}` — frontend só repassa |
| `limit` | `int` 1–100 | ❌ | 50 | Cap máximo 100 |

**Response 200 (Pydantic v2):**

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "acao": "transitar_status",
      "tipo_evento": "CANCELAMENTO",
      "tipo_evento_label": "Cancelamento",
      "usuario": {
        "id": "uuid",
        "nome": "Mário Souza",
        "setor": "STUDIO",
        "is_admin": true
      },
      "prova": {
        "id": "uuid",
        "nro_requerimento": "REQ-001",
        "nome": "Rótulo Lata 350ml"
      },
      "detalhes_json": { "de": "APROVADA_PELO_VENDEDOR", "para": "CANCELADA", "motivo_cancelamento": "cliente cancelou pedido" },
      "ip_address": "203.0.113.42",
      "user_agent": "Mozilla/5.0 ...",
      "created_at": "2026-04-14T19:55:00.819960Z"
    }
  ],
  "next_cursor": "eyJjcmVhdGVkX2F0Ijoi...",
  "has_more": true,
  "total_estimado": 49,
  "filtros_aplicados": { "data_inicio": "2026-04-09", "data_fim": "2026-04-14", "tipo_evento": ["CANCELAMENTO"] }
}
```

- `prova` é `null` quando `prova_id` é `NULL` (caso de `atualizar_configuracao`).
- `detalhes_json` preservado como-está (não sanitizado) — dentro do modal, o frontend renderiza como JSON pretty-printed. **Nenhum detalhes_json existente contém PII além de IP e nro_requerimento**; vou validar durante o bloco 6.1 varrendo todas as 49 linhas.
- `next_cursor` é `null` quando `has_more = false`.
- `total_estimado` é um `COUNT(*)` real com os mesmos filtros aplicados, capped em 100k (se exceder, retorna `100001` e o frontend mostra "100k+"). Hoje, o valor real é instantâneo.

**Códigos HTTP:**

| Código | Cenário |
|---|---|
| 200 | OK, com lista (pode ser vazia) |
| 401 | Token ausente/inválido/expirado (já tratado por `get_current_user`) |
| 403 | Usuário autenticado sem `is_admin=true` (tratado por `get_admin_user`) |
| 422 | Parâmetros inválidos (cursor corrompido, `data_inicio > data_fim`, `acao` fora do whitelist, mutuamente exclusivo violado) |
| 502 | Falha transiente ao ler DB (consistente com padrão Wave 2-3) |

### 4.3 `GET /api/v1/auditoria/{log_id}` — detalhe

**Auth:** mesmo gate `get_admin_user`.

**Response 200:** mesmo shape de cada `item` do endpoint anterior (enriquecido com usuário e prova).
**404:** log não encontrado.

**Por que existe um endpoint separado:** o modal de detalhes do frontend pode ser aberto a partir de um deep link (`/auditoria?id=...`). Buscar a linha específica via query string em vez de armazenar no estado da listagem torna a rota compartilhável e mantém o frontend stateless para o modal.

### 4.4 O que NÃO existe no contrato

- ❌ `POST /api/v1/auditoria/` — **impossível por design.** Backend nunca recebe requests para criar audit logs; a criação é interna via `audit_service.log_audit()` chamada pelos outros endpoints.
- ❌ `PATCH`/`PUT`/`DELETE /api/v1/auditoria/{id}` — **impossível por design** (trigger bloqueia no DB; ausência de route no backend).
- ❌ `GET /api/v1/auditoria/export.csv` — fora do escopo, salvo autorização.

---

## 5. IMPACTO NO FRONTEND

### 5.1 Rota e arquivo principal

- Rota: `/auditoria` (grupo `(dashboard)` já existente).
- Arquivo: `frontend/src/app/(dashboard)/auditoria/page.tsx`.
- **Server component** faz o gate de admin lendo o usuário via `createServerClient` (pattern já usado em `layout.tsx` da Wave 1) — se `!user.is_admin`, retorna `redirect('/dashboard')` com uma mensagem flash.
- **Client component** `AuditoriaClient.tsx` gerencia estado de filtros, cursor, modal. Hook `useAuditoria` (SWR-like via `useEffect` + AbortController — padrão ADR-098 da Wave 5).

### 5.2 Componentes e estrutura visual

```
/auditoria
├─ Header (Breadcrumb: Dashboard > Auditoria)
├─ Filtros (card)
│   ├─ Período (date range inicio/fim — reaproveita padrão ADR-095/Wave 5)
│   ├─ Autor (select com os N usuários ativos — fetch /api/v1/users/ no load)
│   ├─ Prova (input de número de requerimento)
│   ├─ Tipo de evento (multi-select com 7 valores derivados)
│   └─ Botão "Aplicar" (disabled até haver mudança) + "Limpar"
├─ Tabela
│   ├─ Colunas: Quando · Quem · Evento (chip colorido) · Prova · IP
│   ├─ Empty state: "Nenhum evento encontrado com os filtros atuais."
│   ├─ Loading state: skeleton de 5 linhas
│   └─ Error state: retry button
├─ Paginação
│   ├─ Contador "Mostrando 1-50 de ~49"
│   ├─ Botão "Carregar mais" (quando `has_more === true`)
│   └─ (opção 2, futuro) Próximo/Anterior
└─ Modal de detalhes
    ├─ Aberto ao clicar em uma linha
    ├─ Cabeçalho: Evento + Quando + Quem
    ├─ Corpo: JSON pretty-printed de `detalhes_json`
    ├─ IP/User-Agent expostos
    └─ Link "Abrir prova" quando `prova != null` → `/provas/{id}`
```

### 5.3 Design system e acessibilidade

- **CSS Modules** exclusivamente (regra crítica #5 do CLAUDE.md). Arquivo: `auditoria.module.css`.
- **Chips de evento coloridos** — 7 cores derivadas do design token do projeto (sem criar novos tokens):
  - `CANCELAMENTO` — vermelho
  - `REPROVACAO` — laranja
  - `REINICIO_CICLO` — amarelo
  - `CRIACAO_PROVA` — verde
  - `ESCANEAMENTO` — azul
  - `TRANSICAO_STATUS` — cinza
  - `ALTERACAO_CONFIG` — roxo
- **Focus trap no modal** — reutiliza `useFocusTrap` da Wave 3 (hardening auditoria).
- **Keyboard navigation** — `Esc` fecha modal; `Enter` em linha abre modal; `Tab` percorre filtros.
- **a11y** — `aria-live="polite"` no contador, `aria-label` nos botões de filtro, `role="dialog"` no modal.

### 5.4 Realtime?

**Decisão: não integrar Supabase Realtime na Wave 6.**
Razão: o log cresce em eventos discretos (poucas dezenas/dia hoje) e o caso de uso da tela é investigativo (admin olha quando precisa), não operacional (ninguém "fica assistindo" o log). Realtime introduziria complexidade (subscrição + auth) sem ganho real. **Se o Renan pedir, dá para adicionar em bloco posterior** — a publicação `supabase_realtime` atual só inclui `provas_digitais` (RLS 007, Wave 4) e adicionar `audit_logs` seria uma linha de SQL + um hook.

### 5.5 Menu lateral

- **Confirmado empiricamente no Bloco 6.0**: o menu hoje **NÃO tem** item "Auditoria". Estado real: `MAIN_NAV` com 6 entradas (`dashboard`, `provas`, `nova-prova`, `escanear`, `relatorios`, `usuarios`) e `SECONDARY_NAV` com `configuracoes` (com href) + `informacoes` (placeholder sem href). A Wave 6 **cria** o item novo — não é "ativar placeholder".
- **Posição:** inserir como penúltimo item do `SECONDARY_NAV`, ficando `[configuracoes, auditoria, informacoes]`.
- **Novo campo** `adminOnly?: boolean` na interface `NavItemSpec`. Apenas o item `auditoria` recebe `adminOnly: true` nesta Wave — os outros continuam visíveis para todos (comportamento pré-existente).
- **Visibilidade condicional** via filtro `.filter((item) => !item.adminOnly || user?.is_admin === true)` aplicado somente à renderização de `SECONDARY_NAV`. O estado `user.is_admin` já é carregado pelo `useEffect` existente (linha 98 do `layout.tsx`).
- **Novo ícone SVG** `ShieldIcon` (ou `ClipboardCheckIcon`) em `frontend/src/components/icons/` — os 10 ícones atuais (`Chart`, `Close`, `Gear`, `Home`, `Info`, `Laptop`, `Plus`, `Scan`, `Search`, `User`) não cobrem bem "auditoria/histórico". Decisão final do nome + formato fica no Bloco 6.4.
- Essas são as **únicas** mudanças em `layout.tsx`. Outros itens e lógica permanecem intactos.

---

## 6. STORAGE R2

**Decisão explícita:** **Wave 6 tem zero impacto no Cloudflare R2.**

Justificativa:
- O log de auditoria existe 100% em Postgres (`public.audit_logs`).
- `detalhes_json` é JSONB, sem referência a objetos R2.
- Nenhum blob é lido, escrito, listado ou deletado em R2 durante os fluxos da Wave 6.
- O bucket `rastreio-provas-artes` (inspecionado via MCP) continua exclusivamente para artes/preview de provas digitais (Wave 2).

Nenhum arquivo em `backend/app/core/r2.py` ou `backend/app/services/r2_signed.py` será tocado. Zero novas credenciais R2. Zero novas entradas no `r2_buckets_list`.

---

## 7. PLANO DE TESTES

### 7.1 Camada 1 — Unit (função pura de projeção)

**Arquivo:** `backend/tests/test_auditoria_projection.py`

| Teste | O que valida |
|---|---|
| `test_projecao_criar_prova` | `acao="criar_prova"` → `tipo_evento="CRIACAO_PROVA"`, label pt-BR correta |
| `test_projecao_escanear_prova` | `acao="escanear_prova"` → `tipo_evento="ESCANEAMENTO"` |
| `test_projecao_transitar_status_generico` | `acao="transitar_status"`, `detalhes={"para":"COM_MOTORISTA"}` → `TRANSICAO_STATUS` |
| `test_projecao_cancelamento` | `acao="transitar_status"`, `detalhes={"para":"CANCELADA"}` → `CANCELAMENTO`, label "Cancelamento" |
| `test_projecao_reprovacao` | `acao="transitar_status"`, `detalhes={"para":"REPROVADA_PELO_VENDEDOR"}` → `REPROVACAO` |
| `test_projecao_reiniciar_ciclo` | `acao="reiniciar_ciclo"` → `REINICIO_CICLO` |
| `test_projecao_atualizar_config` | `acao="atualizar_configuracao"` → `ALTERACAO_CONFIG` |
| `test_projecao_acao_desconhecida` | `acao="foobar"` → fallback `TRANSICAO_STATUS` + log de warning (decisão tomada no Bloco 6.1: fallback sem raise, para não quebrar a listagem quando Waves futuras introduzirem `acao` nova sem atualizar a matriz) |
| `test_projecao_detalhes_json_vazio` | `detalhes_json = None` com `acao="transitar_status"` → `TRANSICAO_STATUS` (não crasha) |
| `test_projecao_detalhes_json_sem_chave_para` | `detalhes = {}` com `acao="transitar_status"` → `TRANSICAO_STATUS` |

**Meta de cobertura:** 100% no `auditoria_projection.py`.

### 7.2 Camada 2 — Integração (API contra mock fiel ou banco real de teste)

**Arquivo:** `backend/tests/test_auditoria_api.py`

**Fixtures reaproveitadas de `tests/conftest.py`:** `admin_user`, `vendedor_matriz`, `vendedor_filial`, `mock_db`.

| Teste | O que valida |
|---|---|
| `test_list_401_sem_token` | Sem header Authorization → 401 |
| `test_list_401_token_invalido` | Bearer garbage → 401 |
| `test_list_403_nao_admin` | Token de vendedor → 403, mensagem padrão do `get_admin_user` |
| `test_list_200_admin_retorna_lista` | Token admin → 200, estrutura de resposta bate com schema |
| `test_list_filtro_periodo` | `data_inicio`/`data_fim` restringe corretamente |
| `test_list_filtro_autor` | `usuario_id` retorna apenas logs daquele usuário |
| `test_list_filtro_prova_por_nro_req` | `nro_requerimento` resolve em `prova_id` e filtra |
| `test_list_filtro_prova_nro_req_inexistente` | `nro_requerimento` sem match → lista vazia (não 404) |
| `test_list_filtro_acao_single` | `acao=criar_prova` retorna só os 13 |
| `test_list_filtro_acao_multi` | `acao=criar_prova&acao=escanear_prova` retorna união |
| `test_list_filtro_tipo_evento_cancelamento` | `tipo_evento=CANCELAMENTO` filtra via JSONB extraction |
| `test_list_filtro_tipo_evento_reprovacao` | idem para reprovações |
| `test_list_combinacao_filtros` | período + autor + tipo → resultado conjunto |
| `test_list_conflito_acao_e_tipo_evento` | usar ambos → 422 "mutuamente exclusivos" |
| `test_list_paginacao_cursor` | página 1 → pega cursor → página 2 → sem duplicar itens |
| `test_list_paginacao_limit_invalido` | `limit=0` e `limit=101` → 422 |
| `test_list_cursor_corrompido` | `cursor="gibberish"` → 422 |
| `test_list_data_invertida` | `data_inicio > data_fim` → 422 |
| `test_detail_200_admin` | `GET /auditoria/{id_valido}` → 200, item enriquecido |
| `test_detail_403_nao_admin` | Vendedor → 403 |
| `test_detail_404_nao_existe` | UUID inexistente → 404 |
| `test_detail_enriquece_prova_null_quando_config` | Log de `atualizar_configuracao` → `prova = null` |
| `test_imutabilidade_nenhuma_rota_de_escrita` | `POST/PUT/PATCH/DELETE /api/v1/auditoria/*` → 405 Method Not Allowed (garantia de escopo) |
| `test_ordem_desc_por_created_at` | Ordem correta em todas as páginas |

**Meta de cobertura:** ≥ 80% em `api/v1/auditoria.py`, ≥ 90% em `services/auditoria_query.py`.

### 7.3 Camada 3 — E2E (preview server + preview_* tools)

**Script mental (executado durante bloco 6.5):**

1. `preview_start frontend` + `preview_start backend` (via `.claude/launch.json`).
2. `preview_eval` para logar como admin (usando `ops@3studio.com.br` do seed).
3. `preview_click` no menu lateral "Auditoria" → confirma `/auditoria` carregou.
4. `preview_snapshot` → confirma tabela com 49 linhas (ou contagem real atual).
5. `preview_fill` para preencher `data_inicio` → `preview_click` Aplicar → `preview_snapshot` confere filtragem.
6. `preview_click` em uma linha de cancelamento → `preview_snapshot` do modal → confere "Cancelamento" no título e `motivo_cancelamento` no corpo.
7. `preview_click` "Carregar mais" (se houver) → confere paginação.
8. Log out do admin, login como vendedor → navegar para `/auditoria` manualmente → confere redirect ou 403.
9. `preview_console_logs level=error` → zero erros.
10. `preview_network filter=failed` → zero requests 4xx/5xx inesperados.

Sem script ci-cd E2E automatizado (escopo fora). O preview manual cobre o golden path e edge cases principais. Cada bloco que mexer em UI vai passar por esse mini-E2E.

### 7.4 Matriz de garantia de imutabilidade

Estes testes cobrem explicitamente a RNF-005 e a regra inviolável #2:

| Garantia | Como é testada |
|---|---|
| Nenhum `INSERT` novo em `audit_logs` fora de `audit_service.log_audit` | `test_grep_no_new_inserts` — grep programático em `backend/app/api/v1/auditoria.py` procurando `INSERT INTO audit_logs` ou `db.add(AuditLog` → falha se achar |
| Nenhum `UPDATE`/`DELETE` em `audit_logs` em qualquer lugar | mesmo grep, procurando `UPDATE audit_logs` ou `delete(AuditLog)` |
| Endpoints POST/PUT/PATCH/DELETE não existem | teste `test_imutabilidade_nenhuma_rota_de_escrita` da seção 7.2 |
| Policy RLS `pol_audit_select` permanece a única | teste `test_rls_audit_logs_policies_count` que consulta `pg_policies` e valida exatamente 1 row |
| Trigger `trg_audit_logs_imutavel` continua habilitado | teste `test_trigger_imutabilidade_ativo` que consulta `pg_trigger` |

### 7.5 Regressão das Waves 0-5

- **Todos os 459 testes atuais precisam continuar verdes** sem modificação.
- `pytest` será rodado ao fim de cada bloco — se algum teste pré-existente quebrar, é sinal de que a Wave 6 tocou algo que não deveria → vou parar e investigar antes de seguir.

---

## 8. RISCOS E PONTOS DE ATENÇÃO

| # | Risco | Probab. | Impacto | Mitigação |
|---|---|---|---|---|
| R-01 | **Crescimento da tabela `audit_logs`** indefinido — eventualmente explode o free tier Supabase (500 MB) | Média | Alto (longo prazo) | Hoje são 144 kB para 49 linhas → ~3 KB/linha. A 3-5 eventos/dia/admin × 1 ano = ~5 MB/ano. **Não é risco iminente.** Documentar no ADR-099 que política de retenção é "para sempre" e revisar se passar de 50 MB |
| R-02 | **Queries com filtro de `tipo_evento` usando JSONB extraction** podem gerar Seq Scan | **Baixa** (confirmado via EXPLAIN no Bloco 6.0: 2.176 ms com `idx_audit_acao` + Filter heap, Rows Removed by Filter: 7) | Médio (volume futuro) | **Follow-up condicional** no ADR-099: criar `CREATE INDEX idx_audit_cancelamentos ON audit_logs ((detalhes_json->>'para')) WHERE acao = 'transitar_status'` apenas quando `pg_stat_statements` mostrar essa query com tempo sustentado > 50 ms. **Não criar especulativamente.** |
| R-03 | **Vazamento de PII em `detalhes_json`** — algum log carrega dado sensível não previsto | Baixa | **Baixo** (downgradeado no Bloco 6.0 via varredura empírica) | Inventário das 50 linhas de produção no Bloco 6.0 confirmou: **zero** ocorrências de chaves `password`/`token`/`secret`/`api_key`. Apenas dados legítimos de auditoria (nome de cliente, vendedor, IP real, filename). Estratégia: expor como-está com policy admin-only via `pol_audit_select` + `get_admin_user` |
| R-04 | **Admin malicioso vazar o log** — é quem tem acesso legítimo | Baixa | Alto | Fora do escopo técnico (controle organizacional). Registrar como "known limitation" no ADR-099 |
| R-05 | **Performance do `COUNT(*) filtrado`** para `total_estimado` com tabela grande | Baixa (hoje) | Médio (futuro) | Cap em 100k linhas; acima disso, retornar estimativa via `pg_class.reltuples` ou dispensar o total |
| R-06 | **Frontend quebra RLS ao chamar Supabase JS direto** (hipótese) | Muito baixa | Crítico | Backend + service_role + `pol_audit_select` já cobrem. Adicionar teste E2E que tenta `supabase.from('audit_logs').select()` como vendedor e verifica que RLS bloqueia |
| R-07 | **Projeção `tipo_evento` ficar inconsistente se Wave futura alterar `state_machine.py`** (ex: novo `acao_audit`) | Média | Baixo | Teste `test_projecao_acao_desconhecida` loga warning. Código de projeção tem fallback seguro. Documentar no ADR-099 que adicionar novas `acao` implica atualizar a matriz 1.6 |
| R-08 | **Bug de paginação cursor** — registros duplicados ou sumidos entre páginas | Média | Médio | Cursor determinístico `(created_at, id)`. Teste de integração específico (`test_list_paginacao_cursor`) com fixture de ≥ 3 páginas |
| R-09 | **Item de menu "Auditoria" aparecer para não-admin** por renderização server/client desalinhada | Baixa | Médio | Guard em **dois lugares** — server component `redirect()` + client hook `useCurrentUser`. Teste E2E da seção 7.3 passo 8 cobre explicitamente |
| R-10 | **Testes novos acidentalmente quebram testes antigos** (flaky state em fixture) | Baixa | Médio | Cada teste novo recebe fixture isolada; nenhuma fixture das Waves 0-5 é modificada. Rodar `pytest -x` ao fim do bloco garante fail-fast |
| R-11 | **Ambiguidade de fuso horário na filtragem por `data_inicio`/`data_fim`** — `created_at` é TIMESTAMPTZ UTC, mas usuário pensa em São Paulo | Alta (UX) | Baixo | Backend converte `date` do usuário para intervalo UTC usando `America/Sao_Paulo` explicitamente. Documentar no schema Pydantic. Teste `test_list_filtro_periodo_fuso_horario` cobre |
| R-12 | **Regra inviolável #2 violada acidentalmente** (ex: eu adicionar um endpoint de DELETE sem querer) | Baixa | **Crítico** | Teste automatizado da seção 7.4 (`test_grep_no_new_inserts`, `test_imutabilidade_nenhuma_rota_de_escrita`) roda em CI como gate |

### 8.1 Limitações conhecidas que NÃO serão resolvidas nesta Wave

- Cancelamento logado como `transitar_status` com `detalhes.para=CANCELADA` (gap 1.6). **Resolvido via projeção backend**, mas a camada de escrita permanece como está por regra.
- Ausência de exportação CSV.
- Ausência de Realtime.
- Ausência de meta-auditoria (quem acessou a tela de auditoria).
- Ausência de filtro por texto livre em `detalhes_json`.
- **5 linhas legadas de `criar_prova` com `seed_test: true`** no banco de produção, criadas no seed inicial da Wave 2 em 2026-04-09 16:35:34. Por imutabilidade (RNF-005), não podem ser apagadas. A interface Wave 6 vai exibi-las normalmente (transparência total). Documentado no ADR-099 como dado histórico preservado.

---

## 9. ORDEM DE IMPLEMENTAÇÃO EM BLOCOS

Cada bloco termina com: **commit descritivo + update do `CHANGELOG.md` + update do `DECISIONS.md` (quando houver ADR novo) + `pytest` verde com relatório de cobertura**. Entre blocos, o Renan pode pausar/ajustar/aprovar.

### Bloco 6.0 — Setup e reconhecimento final (NÃO mexe em código)

1. Confirmar o estado do item de menu "Auditoria" em `layout.tsx` (hoje placeholder ou inexistente?).
2. Executar varredura empírica do `detalhes_json` atual via `execute_sql`: listar todas as 49 linhas agrupadas por `acao` para inventariar chaves reais (mitiga R-03).
3. Rodar `EXPLAIN (ANALYZE, BUFFERS)` de uma query representativa contra os 49 logs atuais para validar que os 5 índices existentes cobrem os filtros (mitiga 3.2).
4. Confirmar que `alembic_version = 009`, `pol_audit_select` ativa, `trg_audit_logs_imutavel` ativo.
5. Gerar um tag-baseline do pytest (expecting **459 passando**).

**Saída:** nenhum commit, apenas relatório curto no chat do Renan com "achei isso e isso, sigo?". Se mudança de plano for necessária, atualizo este arquivo antes de ir pro 6.1.

### Bloco 6.1 — Schemas Pydantic + projeção (backend, sem rota)

**Arquivos criados:**
- `backend/app/domain/schemas/auditoria.py` (request params + response DTOs + TipoEventoEnum + label map)
- `backend/app/services/auditoria_projection.py` (função pura `projetar_tipo_evento`)

**Arquivos criados de teste:**
- `backend/tests/test_auditoria_projection.py` (camada 1, meta 100% cobertura)

**Saída:** commit "feat(wave-6): schemas + projecao tipo_evento (Bloco 6.1)"; CHANGELOG atualizado; pytest verde (novo total = 459 + ~10); DECISIONS.md ganha **ADR-099 — Projeção de tipo_evento para audit log**.

### Bloco 6.2 — Query builder + endpoints API

**Arquivos criados:**
- `backend/app/services/auditoria_query.py` (builder com filtros + keyset + joins)
- `backend/app/api/v1/auditoria.py` (router com 2 endpoints)

**Arquivos modificados (apenas 1, apenas 1 linha):**
- `backend/app/main.py` (adicionar `app.include_router(auditoria.router, prefix="/api/v1/auditoria", tags=["auditoria"])`)

**Arquivos criados de teste:**
- `backend/tests/test_auditoria_api.py` (camada 2 + matriz 7.4)

**Saída:** commit "feat(wave-6): endpoints GET auditoria list+detail (Bloco 6.2)"; CHANGELOG atualizado; pytest verde (novo total = 459 + ~35). Se surgir risco R-02, ADR-100 adiciona índice composto + migration `010`.

### Bloco 6.3 — Types + hooks frontend

**Arquivos criados:**
- `frontend/src/lib/types/auditoria.ts` (espelho TS)
- `frontend/src/hooks/useAuditoria.ts` (listagem com AbortController)
- `frontend/src/hooks/useAuditoriaDetail.ts` (detalhe pontual)

**Nenhum arquivo modificado além dos novos.**

**Saída:** commit "feat(wave-6): tipos TS + hooks frontend (Bloco 6.3)"; CHANGELOG atualizado.

### Bloco 6.4 — Página e componentes UI

**Arquivos criados:**
- `frontend/src/app/(dashboard)/auditoria/page.tsx`
- `frontend/src/app/(dashboard)/auditoria/AuditoriaClient.tsx`
- `frontend/src/app/(dashboard)/auditoria/AuditoriaDetailModal.tsx`
- `frontend/src/app/(dashboard)/auditoria/auditoria.module.css`
- `frontend/src/components/icons/ShieldIcon.tsx` *(novo ícone SVG — descoberta do Bloco 6.0)*

**Arquivos modificados (mínimo necessário):**
- `frontend/src/app/(dashboard)/layout.tsx` — **criar** item "Auditoria" em `SECONDARY_NAV` (novo) + adicionar campo `adminOnly?: boolean` em `NavItemSpec` + filtro de visibilidade condicional
- `frontend/src/components/icons/index.ts` — adicionar `export { ShieldIcon }` (barrel)

**Saída:** commit "feat(wave-6): pagina /auditoria com filtros + modal (Bloco 6.4)"; CHANGELOG atualizado.

### Bloco 6.5 — Validação E2E + auditoria interna

1. Rodar mini-E2E da seção 7.3 via preview tools.
2. Screenshots/snapshots de comprovação.
3. Rodar `get_advisors` (security + performance) pós-mudança → comparar com baseline (deve haver **nenhum regresso**; `unused_index` sobre `idx_audit_created_at` deve desaparecer).
4. Rodar `pytest --cov` completo e reportar cobertura.
5. Check manual do gap 1.6 na UI: criar um cancelamento fake via C13 direto contra `localhost:8000` e ver aparecer como "Cancelamento" na tela.
6. Grep final de segurança: procurar em todos os arquivos da Wave 6 por strings proibidas (`DELETE FROM audit_logs`, `UPDATE audit_logs`, `ON CONFLICT`, etc.).

**Saída:** commit "chore(wave-6): validacao E2E + auditoria interna (Bloco 6.5)"; CHANGELOG atualizado com seção de medições; **Wave 6 pronta para closeout**.

### Bloco 6.6 (opcional — não incluído por default) — Auditoria Senior Ronda 1

Caso o Renan decida aplicar a mesma prática de auditoria senior que encerrou as Waves 2-5 (ADRs 079/080/094/095/096/097/098), este bloco receberia um ticket-by-ticket dos HIGHs/MEDIUMs/LOWs encontrados. **Fora do escopo deste plano** — decisão post-Bloco 6.5.

---

## 10. DECISÕES PENDENTES QUE PRECISAM DO SEU OK

Antes de começar o Bloco 6.0, preciso de confirmação em **três pontos** que afetam o rumo da implementação:

1. **Gap 1.6 (cancelamento como `transitar_status`)** — concorda com a resolução via projeção backend (`tipo_evento` derivado), mantendo a camada de escrita intocada? Se preferir corrigir na raiz (introduzir `acao="cancelar_prova"` em `state_machine.py` ou no endpoint `/cancelar`), abro `WAVE6_BLOCKERS.md` e aguardo decisão — mas isso **tocaria Wave 3**.

2. **Policy RLS extra** — concorda em **não adicionar** uma `pol_audit_insert` redundante (trigger + ausência de policy INSERT já bloqueiam)? Se preferir paridade com RLS 006 (ADR-082 para movimentacoes), incluo `008_audit_logs_defense_in_depth.sql` — apenas 1 arquivo novo, 1 ADR extra.

3. **Export CSV de audit log** — confirmo o **não-entregar** como default? Ou quer que eu adicione como Bloco 6.6 (follow-up) reaproveitando o sanitizer do ADR-097 (CSV Injection) e o `Cache-Control: no-store` do ADR-098?

---

## 11. RESUMO EXECUTIVO

| Dimensão | Valor |
|---|---|
| Componente entregue | 18 — Interface de Log de Auditoria |
| Endpoints novos | 2 (`GET /api/v1/auditoria/` + `GET /api/v1/auditoria/{id}`) |
| Rotas frontend novas | 1 (`/auditoria`) |
| Migrations Alembic novas | **0** (default; 1 se surgir necessidade de índice no Bloco 6.1) |
| Scripts RLS novos | **0** (default; 1 opcional se o Renan pedir paridade com ADR-082) |
| Policies RLS modificadas | **0** |
| Tabelas alteradas | **0** |
| Triggers tocados | **0** |
| R2 impactado? | **Não** |
| Realtime impactado? | **Não** |
| Testes novos estimados | ~45 (10 unit + 25 integração + 10 de imutabilidade e regressão) |
| ADRs novos estimados | 1 (ADR-099) + possíveis 100, 101 se R-02 ou decisão de RLS exigirem |
| Arquivos Wave 0-5 tocados | **1** (`frontend/src/app/(dashboard)/layout.tsx` — apenas ativação do item de menu condicional) + **1** (`backend/app/main.py` — apenas `include_router` novo) |
| Regressão esperada | Nenhum dos 459 testes atuais deve quebrar |
| Tempo de execução | Sem estimativas (convenção CLAUDE.md) |

---

**Status do documento:** rascunho completo aguardando GO para o Bloco 6.0.
**Próximo passo se aprovado:** Bloco 6.0 — reconhecimento final + varredura empírica do `detalhes_json` + EXPLAIN das queries + tag-baseline do pytest. Nenhum commit no 6.0.
