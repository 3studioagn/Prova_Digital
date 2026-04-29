# Wave 6 — Análise Read-Only (Gate 1)

**Componente:** 18 — Interface de Log de Auditoria
**Wave:** 6 · Segurança e Auditoria
**Prioridade:** Should Have
**Dependência:** Componente 11 (Wave 3 — operacional desde 2026-04-13)
**Estado do banco:** `alembic_version = 011` (Wave 5 closeout, 2026-04-27)
**Data desta análise:** 2026-04-29
**Branch:** `wave6/analysis`

---

## 0. Sumário executivo

A Wave 6 entrega exclusivamente uma **fachada de leitura** sobre o log de auditoria já populado desde a Wave 3. Não cria registros, não altera schema de tabelas existentes, não substitui endpoints anteriores.

A tabela primária é `public.audit_logs` (74 registros em produção, 6 valores distintos de `acao`). A tabela `public.movimentacoes` (16 registros) já é exposta por endpoint específico do Componente 08 (`GET /api/v1/provas/{id}/movimentacoes`), com scoping próprio — a Wave 6 **não** a substitui, apenas complementa com uma visão audit-centric exclusiva 3Studio. Imutabilidade está garantida em três camadas (trigger, RLS deny-by-default, RBAC backend) — a Wave 6 propõe uma quarta opcional via `REVOKE`.

API proposta: 3 endpoints sob `/api/v1/audit-log` (listagem paginada, detalhe por id, histórico por prova). UI: rota `/auditoria` reusando o padrão de tabela + filtros do `/provas` (Wave 2 C07) e dos componentes shared do `/relatorios` (Wave 5 ADR-106). RBAC em três camadas reusando `get_admin_user` + `pol_audit_select` + guard de menu condicional ao `is_admin`.

Riscos principais: PII em `detalhes_json` (mitigado por restrição admin-only), crescimento indefinido da tabela (mitigado por paginação obrigatória + índice já existente em `created_at`), e divergência conceitual entre log audit-centric (audit_logs) e timeline visual (movimentacoes) — endereçada por documentação clara no response e na UI.

---

## 1. Leitura obrigatória de contexto

Os artefatos abaixo foram lidos integralmente antes de qualquer análise.

| # | Artefato | Caminho real no repositório | Status |
|---|----------|------------------------------|--------|
| 1 | Guia operacional do projeto | [CLAUDE.md](../../CLAUDE.md) | ✅ |
| 2 | Decisões arquiteturais acumuladas (Waves 0–5, ADRs até 109) | [DECISIONS.md](../../DECISIONS.md) (3.685 linhas) | ✅ leitura focada nas ADRs 095–109 (Wave 5) e 080–094 (Wave 3+4) |
| 3 | Histórico por sessão | [CHANGELOG.md](../../CHANGELOG.md) (7.535 linhas) | ✅ leitura focada no estado pós-Wave 5 |
| 4 | Snapshot do schema | [docs/db/schema.sql](../db/schema.sql) (299 linhas) | ✅ |
| 4a | Migrations Alembic 001–011 | [backend/migrations/versions/](../../backend/migrations/versions/) | ✅ índice e datas conferidos |
| 4b | Policies RLS 001–007 | [backend/migrations/rls/](../../backend/migrations/rls/) | ✅ leitura integral de 004–006 |
| 5 | Componente 11 — state machine + audit | [backend/app/services/state_machine.py](../../backend/app/services/state_machine.py) (441 linhas), [backend/app/services/audit_service.py](../../backend/app/services/audit_service.py) (112 linhas) | ✅ |
| 5a | Componente 11 — endpoint de transições | [backend/app/api/v1/provas.py](../../backend/app/api/v1/provas.py) (linhas 1283-1351 movimentações, 1836+ transições, 2023+ cancelar, 2149+ reiniciar) | ✅ |
| 5b | Componente 05 — RBAC/auth | [backend/app/api/deps.py](../../backend/app/api/deps.py) (121 linhas) | ✅ |
| 5c | Componente 16 — padrão admin-only de Wave 5 (referência de estilo) | [backend/app/api/v1/reports.py](../../backend/app/api/v1/reports.py) | ✅ leitura parcial (200 linhas iniciais) |
| 6 | Documentos de negócio | Desktop\Rastreio Prova Digital\\{RequisitosProvasDigitais_v3_0.docx, DAT_RastreioProvasDigitais_v2_0.docx, BACKLOG_RastreioProvasDigitais_v3_0.docx} | ✅ via subagent — extraídos RF-007, RF-008, RN-005, RN-006, RNF-005, DoD global (8 itens), entrada do Componente 18 no backlog, Seção 3 do DAT (estratégia de testes) |

**Achados normativos relevantes:**

- **RF-007 (Must):** "Ao escanear o QR Code de uma prova no status 'Retirada pelo Vendedor', o sistema deve apresentar ao vendedor duas opções: Aprovar ou Reprovar. Na reprovação, o vendedor deve informar obrigatoriamente o motivo, assinar digitalmente e confirmar."
- **RF-008 (Must):** "Após a reprovação, a prova retorna a 3Studio com status 'Reprovada pelo Vendedor'. O perfil 3Studio pode então reiniciar o ciclo da prova, retornando-a ao status 'Criada', preservando integralmente o histórico de movimentações anteriores no log de auditoria."
- **RN-005:** "Provas canceladas não podem ter seu status reativado. (...) O histórico do registro cancelado é preservado."
- **RN-006:** "Provas reprovadas podem ter seu ciclo reiniciado exclusivamente pelo perfil 3Studio. O reinício retorna o status a 'Criada', preservando integralmente o histórico de movimentações do ciclo anterior no log de auditoria."
- **RNF-005:** "O sistema deve manter um log de auditoria completo e imutável de todas as movimentações de provas, incluindo reprovações e reinícios de ciclo, acessível apenas pelo perfil 3Studio (Administrador)."
- **DAT Seção 3 — Estratégia de Testes:** 3 camadas (unitário pytest, integração httpx AsyncClient + DB real, E2E Playwright). Meta de cobertura **≥ 80% nas camadas de domínio e serviço do backend**. 100% dos endpoints críticos.
- **Backlog — Componente 18:** "Interface de consulta ao log imutável gerado desde a Wave 3. Tabela imutável · acesso restrito ao perfil 3Studio · RNF-005 · inclui registros de reprovação e reinício de ciclo. Reclassificado de Must Have para Should Have: o log existe e é imutável independentemente desta tela."
- **DoD Global (8 itens):** code review, ≥80% cobertura unitária, integração em staging, migrations versionadas, validação contra critérios de aceitação, sem erros no console/backend, documentação atualizada, **políticas de RLS verificadas e versionadas em `/migrations/rls/`**.
- **Não existe US dedicada ao Componente 18.** As US do projeto vão até US-016. A base normativa é RNF-005 + entrada do backlog.
- **DAT não descreve a estrutura de `audit_logs`.** A estrutura foi inferida do código (`backend/app/db/models.py` AuditLog) e do schema (migrations 001).
- **DAT não documenta padrão de paginação.** A Wave 6 reusa o padrão já implementado em `GET /api/v1/provas` (Wave 2 C07).

---

## 2. Validação de infraestrutura via MCP

### 2.1 Supabase

**Projeto:** `rwxlpwmnkekzuurgthkr` — `Rastreio Provas Digitais` — região `sa-east-1` — status `ACTIVE_HEALTHY` — Postgres `17.6.1.104`.

**Tabelas no schema `public` (7, todas com RLS habilitada):**

| Tabela | RLS | Linhas (snapshot) |
|--------|-----|-------------------|
| usuarios | ✅ | 0 (campo metadata; usuários reais existem mas há overhead de contagem) |
| provas_digitais | ✅ | 2 |
| movimentacoes | ✅ | 16 (5 reportadas pelo MCP — divergência de cache; query agregada confirmou 16) |
| etiquetas | ✅ | 2 |
| **audit_logs** | ✅ | **74** (17 reportados pelo MCP — divergência de cache; query agregada confirmou 74) |
| configuracoes_sistema | ✅ | 0 |
| alembic_version | ✅ | 0 |

**Tabela primária do log auditoria identificada:** `public.audit_logs`. Campos: `id (uuid PK)`, `prova_id (uuid FK nullable)`, `usuario_id (uuid FK NOT NULL)`, `acao (varchar(100))`, `detalhes_json (jsonb)`, `ip_address (inet)`, `user_agent (text)`, `created_at (timestamptz)`.

**Distribuição por `acao` (query agregada em produção, 2026-04-29):**

| acao | qtd | primeira | última |
|------|-----|----------|--------|
| escanear_prova | 34 | 2026-04-13 | 2026-04-29 |
| criar_prova | 16 | 2026-04-09 | 2026-04-29 |
| transitar_status | 15 | 2026-04-13 | 2026-04-29 |
| REPORT_EXPORTED | 4 | 2026-04-28 | 2026-04-28 |
| atualizar_configuracao | 4 | 2026-04-09 | 2026-04-09 |
| reiniciar_ciclo | 1 | 2026-04-24 | 2026-04-24 |

**Eventos de reprovação e reinício de ciclo confirmados:**

- Reprovações: na `audit_logs` aparecem como `acao=transitar_status` com `detalhes_json.para = REPROVADA_PELO_VENDEDOR`. 3 movimentações de reprovação em `movimentacoes` (com `motivo_reprovacao` populado).
- Reinícios de ciclo: 1 evento em `audit_logs` (`acao=reiniciar_ciclo`). Em `movimentacoes`, 1 prova com `ciclo > 1` confirmando o reinício preservou o histórico anterior (RN-006 ✅).

**Sample de `detalhes_json` (5 últimos):** estrutura confirmada — `{de, para, ciclo, rota_antes, rota_depois, motivo_reprovacao?, motivo_cancelamento?}` para `transitar_status`; `{cliente, object_key, vendedor_id, vendedor_nome, rota_projetada, nro_requerimento}` para `criar_prova`; `{status_atual, nro_requerimento, transicoes_permitidas[]}` para `escanear_prova`. Todos os registros têm `ip_address` (em formato CIDR/32) e `user_agent` (UA truncado em 2000 chars conforme audit_service).

**Policies RLS em `audit_logs` e `movimentacoes` (query `pg_policies`):**

```
audit_logs        | pol_audit_select          | SELECT | (admin-only via is_admin=true)
movimentacoes     | pol_movimentacoes_insert  | INSERT | (admin-only)
movimentacoes     | pol_movimentacoes_select  | SELECT | (admin OR vendedor das suas provas OR autor OR
                                                          MOTORISTA c/ status COM_MOTORISTA OR
                                                          CLICHERIA c/ status de clicheria)
```

Não há policy `pol_audit_insert`, `pol_audit_update`, `pol_audit_delete`. Em Postgres com RLS habilitada, ausência de policy para um comando equivale a **deny-by-default** para clientes não-bypassrls. Backend usa `service_role` e bypassa RLS — escrita real acontece via backend através do `audit_service.log_audit`.

**Imutabilidade — verificação de privilégios em produção:**

```sql
SELECT
  has_table_privilege('authenticated','public.audit_logs','UPDATE') AS auth_update,
  has_table_privilege('authenticated','public.audit_logs','DELETE') AS auth_delete,
  ...
```

Resultado: GRANT-level UPDATE/DELETE/INSERT estão concedidos a `authenticated` e `anon`. **Mas:**

- RLS deny-by-default bloqueia (não há policy UPDATE/DELETE/INSERT em `audit_logs` — o role `authenticated` não consegue executar essas operações via supabase-js mesmo com GRANT).
- Trigger `trg_audit_logs_imutavel` (BEFORE UPDATE OR DELETE) bloqueia inclusive `service_role` (triggers fazem efeito independente de bypassrls).
- Logo: imutabilidade **já está garantida em duas camadas**, sendo o trigger a barreira final inviolável.

**Advisors Supabase (pós-Wave 5, snapshot 2026-04-29):**

- **Security:** apenas 1 INFO `rls_enabled_no_policy` em `alembic_version` (intencional, ADR-025) + 1 WARN `auth_leaked_password_protection` (WONTFIX, ADR-027 — plano pago). Nenhum lint atribuível à Wave 6 ainda.
- **Performance:** 14 INFO `unused_index` (incluindo `idx_audit_prova`, `idx_audit_usuario`, `idx_audit_acao`, `idx_audit_created_at`). **Implicação para Wave 6:** os 4 índices da `audit_logs` não foram exercitados ainda porque ninguém ainda consulta a tabela em produção via SQL. Após o Componente 18 entrar em uso, o advisor passará a removê-los da lista. Não criar novos índices preemptivamente — só se EXPLAIN ANALYZE mostrar gargalo concreto durante a implementação.

### 2.2 Cloudflare

Confirmado: **não há trabalho novo de R2 nesta wave**. Logs vivem 100% em Postgres. Bucket `rastreio-provas-artes` permanece apenas para PNG/JPG das artes (Wave 2). Não foi tocado nada em Cloudflare.

### 2.3 Bloqueio (Seção 2.3 do prompt)

Critérios de bloqueio:
- Tabela de log existe ✅ (`audit_logs`)
- RLS ativa ✅ (`pol_audit_select`)
- Registros coerentes com a operação pós-Wave 3 ✅ (74 audit_logs, 16 movimentações, com reprovações e reinício de ciclo presentes)
- Componente 11 escrevendo conforme contrato ✅ (visto no `executar_transicao` + `log_audit`)

**Nenhum bloqueio encontrado. Pode prosseguir para o desenho do Componente 18.**

---

## 3.1 Inventário do log existente

### 3.1.1 Tabela primária — `public.audit_logs`

```sql
CREATE TABLE audit_logs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prova_id      UUID REFERENCES provas_digitais(id),    -- nullable (atualizar_configuracao não tem prova)
    usuario_id    UUID NOT NULL REFERENCES usuarios(id),
    acao          VARCHAR(100) NOT NULL,
    detalhes_json JSONB,
    ip_address    INET,
    user_agent    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

- **Triggers:** `trg_audit_logs_imutavel BEFORE UPDATE OR DELETE` (RNF-005). Levanta `Operação % não permitida na tabela %` para qualquer tentativa de mutação, incluindo `service_role`.
- **Índices explícitos (4):** `idx_audit_prova`, `idx_audit_usuario`, `idx_audit_acao`, `idx_audit_created_at` (todos criados em migration 001). PK gera `audit_logs_pkey` automático.
- **FKs:** `prova_id → provas_digitais(id)`, `usuario_id → usuarios(id)`. Não há cascata.
- **Volume:** 74 linhas em produção, crescimento linear ~4-8 entradas/dia em uso atual (subestimado — uso real será maior pós-Wave 6 já que a auditoria poderá observá-lo).
- **Distribuição de `acao` (universo conhecido após Wave 5):** `criar_prova`, `escanear_prova`, `transitar_status`, `reiniciar_ciclo`, `atualizar_configuracao`, `REPORT_EXPORTED`. Inserções futuras (Waves 7+) podem adicionar valores — o endpoint deve tratar qualquer string `<= 100 chars` sem hardcode.

### 3.1.2 Tabela secundária imutável — `public.movimentacoes`

```sql
CREATE TABLE movimentacoes (
    id, prova_id, usuario_id,
    status_anterior, status_novo,
    assinatura_digital BYTEA NOT NULL,    -- evidência criptográfica do RF-007/RN-003
    motivo_reprovacao TEXT,               -- preenchido apenas em REPROVADA_PELO_VENDEDOR
    ciclo INTEGER NOT NULL,
    rota_no_momento RotaEnum,
    created_at
);
```

- Trigger `trg_movimentacoes_imutavel BEFORE UPDATE OR DELETE`.
- 6 índices: `idx_movimentacoes_prova`, `idx_movimentacoes_usuario`, `idx_movimentacoes_prova_ciclo`, `idx_movimentacoes_created_at`, `idx_movimentacoes_prova_data`, `idx_movimentacoes_status_novo_created_at`.
- **Já é exposta** por `GET /api/v1/provas/{prova_id}/movimentacoes` (Wave 2 C08), com scoping `_carregar_prova_com_scoping` (admin OR vendedor da prova OR motorista/clicheria por status).
- **Cada `transitar_status` em `audit_logs` corresponde a 1 linha em `movimentacoes`** (escrita na mesma transação por `executar_transicao`). Estado redundante intencional: `audit_logs` é a fonte universal (tem `ip_address`, `user_agent`, `detalhes_json` flexível); `movimentacoes` é a fonte estruturada para reprodução da timeline (tem `assinatura_digital`, `status_anterior` explícito).

### 3.1.3 Decisão de escopo — fonte de dados da Wave 6

- **`GET /api/v1/audit-log` consulta `audit_logs`** (alinhado com RNF-005 que fala de "log de auditoria completo e imutável"). A interface é audit-centric: lista cada AÇÃO do sistema, com seu ator, IP, UA e detalhes JSON.
- **`GET /api/v1/audit-log/by-prova/{prova_id}` faz JOIN opcional com `movimentacoes`** apenas quando o evento é `transitar_status`/`reiniciar_ciclo`, para enriquecer o detalhe com `assinatura_digital_presente: true` e `status_anterior` validado por DDL (não confiar só em `detalhes_json`).
- **A Wave 6 NÃO substitui** `GET /api/v1/provas/{id}/movimentacoes` — esse endpoint continua existindo, é consumido pelo Componente 12 (Timeline visual da prova individual) e tem scoping próprio mais permissivo (vendedor pode ver suas movimentações). Wave 6 oferece a visão **3Studio-only, transversal, que cruza todas as ações do sistema**.

### 3.1.4 Políticas de RLS atualmente aplicadas

Em `audit_logs`:
- `pol_audit_select` (RLS 005, idempotente — referenciada também em RLS 004): admin-only via `is_admin=true`.
- Sem policy INSERT/UPDATE/DELETE → deny-by-default.

Em `movimentacoes`:
- `pol_movimentacoes_select` (RLS 006, expandida ADR-082): admin OR vendedor das suas provas OR autor da movimentação OR motorista c/ prova em `COM_MOTORISTA` OR clicheria c/ prova em status de clicheria.
- `pol_movimentacoes_insert` (RLS 006, ADR-082): admin-only.
- Sem UPDATE/DELETE → deny-by-default + trigger.

---

## 3.2 Contrato de imutabilidade

### 3.2.1 Camadas de defesa em `audit_logs`

| Camada | Mecanismo | Status | Bloqueia... |
|--------|-----------|--------|-------------|
| 1. Trigger DB | `trg_audit_logs_imutavel BEFORE UPDATE OR DELETE` | ✅ ATIVO (migration 001) | UPDATE/DELETE de qualquer role, inclusive `service_role` |
| 2. RLS (deny-by-default) | Sem policy INSERT/UPDATE/DELETE com RLS habilitada | ✅ ATIVO (RLS 001 + 004 + 005) | INSERT/UPDATE/DELETE via `authenticated` ou `anon` (supabase-js) |
| 3. RBAC backend | Endpoint Wave 6 não expõe `PUT/PATCH/DELETE/POST` para audit_logs | ✅ Garantia de design | Qualquer mutação via API HTTP |
| 4. GRANT (opcional) | `REVOKE UPDATE, DELETE, INSERT ON audit_logs FROM anon, authenticated` | ❌ NÃO APLICADO | Reforço de defesa em profundidade — útil se RLS for desabilitada por engano |

**Verificação em produção (2026-04-29) via `has_table_privilege`:** os roles `anon` e `authenticated` ainda têm GRANT de UPDATE/DELETE/INSERT sobre `audit_logs`. **Não há vazamento real** porque RLS deny-by-default + trigger fazem o trabalho — mas seria higiênico revogar para tornar o erro mais explícito (`permission denied` em vez de `RLS no policy`).

### 3.2.2 Risco residual e mitigação proposta

**Risco baixo:** se uma migration futura adicionar uma policy UPDATE/DELETE por engano (ex: alguém copiando boilerplate do CRUD de `usuarios`), o trigger ainda blocaria — mas o sinal seria mais sutil.

**Mitigação proposta para a Wave 6 (NÃO aplicada agora — apenas registrada):** criar `backend/migrations/rls/008_revoke_audit_logs_mutation.sql`:

```sql
-- Defesa em profundidade — RNF-005.
-- Trigger trg_audit_logs_imutavel já bloqueia UPDATE/DELETE.
-- RLS deny-by-default bloqueia clientes não-bypassrls.
-- Este REVOKE adiciona uma 3ª camada: erro de permissão antes mesmo da RLS.
REVOKE INSERT, UPDATE, DELETE ON public.audit_logs FROM anon, authenticated;
-- service_role mantém os GRANTS — backend continua escrevendo via log_audit().
-- Idempotente: REVOKE de privilégio já ausente é no-op silencioso.
```

A decisão de aplicar (ou não) será registrada em ADR durante o Gate 2 — apenas após confirmar com Mario que o trade-off (mais explicit denial vs. mudança em produção) faz sentido. **Default conservador:** aplicar, porque é puramente aditivo, idempotente e zero-risco.

---

## 3.3 Desenho da API da Wave 6

Prefixo: `/api/v1/audit-log` (lowercase, hífen — consistente com `/api/v1/users` e `/api/v1/provas`). Nome em português faria choque com `/api/v1/auditoria` que tem conotação de "processo de auditoria"; `audit-log` é o substantivo da tabela.

### 3.3.1 `GET /api/v1/audit-log` — Listagem paginada com filtros

**Auth:** `Depends(get_admin_user)` — 401 (sem token), 403 (token sem `is_admin=true`).

**Query parameters (Pydantic v2 schema `AuditLogListQuery`):**

| Parâmetro | Tipo | Default | Descrição |
|-----------|------|---------|-----------|
| `page` | int ≥ 1 | 1 | Número da página (1-indexed) |
| `page_size` | int 1–200 | 50 | Linhas por página |
| `sort` | `"asc"` \| `"desc"` | `"desc"` | Ordem por `created_at` |
| `from_dt` | datetime (ISO 8601) | none | Início do intervalo (UTC; UI converte de America/Sao_Paulo) |
| `to_dt` | datetime (ISO 8601) | none | Fim do intervalo |
| `prova_id` | UUID | none | Filtra por prova específica |
| `usuario_id` | UUID | none | Filtra por ator |
| `acao` | string (in lista discoverável) | none | Filtra por tipo de evento |
| `q` | string (max 200) | none | Busca textual em `detalhes_json::text` (LIKE case-insensitive) — útil para encontrar `motivo_reprovacao` específico |

**Validações Pydantic:**
- `from_dt < to_dt` quando ambos presentes.
- Range total ≤ 366 dias (consistente com `/api/v1/reports`).
- `q` sem caracteres de controle.

**Response (`AuditLogListResponse`):**

```python
class AuditLogItemResponse(BaseModel):
    id: UUID
    acao: str
    prova_id: UUID | None
    prova_nro_requerimento: str | None  # join com provas_digitais
    usuario_id: UUID
    usuario_nome: str                    # join com usuarios
    usuario_setor: SetorEnum             # join com usuarios
    detalhes_json: dict[str, Any] | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime                 # UTC; frontend formata em America/Sao_Paulo

class AuditLogListResponse(BaseModel):
    items: list[AuditLogItemResponse]
    total: int                           # SELECT count(*) com mesmos filtros
    page: int
    page_size: int
```

**Códigos HTTP:** 200, 401, 403, 422 (validação Pydantic), 500 (DB indisponível — mapeado para 502 conforme convenção do projeto, ver Wave 2 A1 audit).

**SQL essencial:**

```sql
SELECT al.*, u.nome, u.setor, pd.nro_requerimento
FROM audit_logs al
JOIN usuarios u ON u.id = al.usuario_id
LEFT JOIN provas_digitais pd ON pd.id = al.prova_id
WHERE al.created_at BETWEEN :from_dt AND :to_dt
  AND (:prova_id IS NULL OR al.prova_id = :prova_id)
  AND (:usuario_id IS NULL OR al.usuario_id = :usuario_id)
  AND (:acao IS NULL OR al.acao = :acao)
  AND (:q IS NULL OR al.detalhes_json::text ILIKE '%' || :q || '%')
ORDER BY al.created_at DESC
LIMIT :page_size OFFSET (:page - 1) * :page_size;
```

Mais um `SELECT count(*)` com os mesmos filtros para o `total`. Consciência de cost: ambas consultas executam — para 74 linhas atuais é instantâneo; conforme tabela cresce, índice `idx_audit_created_at` mantém o ORDER BY barato. Se EXPLAIN ANALYZE mostrar problema em volumes >100k, considerar paginação por keyset (cursor) em ADR posterior.

### 3.3.2 `GET /api/v1/audit-log/{id}` — Detalhe de um registro

**Auth:** mesma do listagem.

**Path param:** `id: UUID` (FastAPI `Depends(parse_audit_id)` — pattern `parse_prova_id` reusado).

**Response:** `AuditLogItemResponse` enriquecido com:

```python
class AuditLogDetailResponse(AuditLogItemResponse):
    # Quando acao IN ('transitar_status', 'reiniciar_ciclo') — JOIN com movimentacoes:
    movimentacao_relacionada: MovimentacaoSnapshot | None = None

class MovimentacaoSnapshot(BaseModel):
    id: UUID
    status_anterior: StatusProvaEnum
    status_novo: StatusProvaEnum
    motivo_reprovacao: str | None
    ciclo: int
    rota_no_momento: RotaEnum | None
    assinatura_digital_presente: bool   # nunca expor o BYTEA — só boolean
```

**Códigos HTTP:** 200, 401, 403, 404 (id não encontrado), 422.

**Lookup de `movimentacao_relacionada`:** quando `acao` é `transitar_status` ou `reiniciar_ciclo`, fazer 1 query extra:

```sql
SELECT * FROM movimentacoes
WHERE prova_id = :al.prova_id
  AND created_at BETWEEN al.created_at - interval '5 seconds' AND al.created_at + interval '5 seconds'
ORDER BY abs(extract(epoch from (created_at - al.created_at))) ASC
LIMIT 1;
```

A janela de ±5s é defensiva: `executar_transicao` insere `movimentacoes` antes do `audit_log` no mesmo flush; `created_at` em ambos vem de `now()` (audit) e `datetime.now(tz=utc)` (movimentação) — diferenças de microssegundos são esperadas. **Decisão alternativa simpler que adoto na implementação:** usar o `detalhes_json.movimentacao_id` se a Wave 6 começar a registrá-lo no audit. Como **hoje** o audit não tem esse link, vou avaliar entre (a) a query por janela e (b) propor pequena alteração no `audit_service.log_audit` (ou no caller `executar_transicao`) para passar `movimentacao_id` no `detalhes_json` adiante. **Opção (b) é mais limpa, mas viola o isolamento da Wave 3.** A Seção 5 lista isso como ponto a confirmar com Mario antes do Gate 2.

### 3.3.3 `GET /api/v1/audit-log/by-prova/{prova_id}` — Histórico completo por prova

**Auth:** mesma.

**Path param:** `prova_id: UUID`.

**Query params:** apenas `sort` (default `asc` aqui, para mostrar a história em ordem cronológica).

**Response:** `AuditLogListResponse` filtrado por `prova_id = :prova_id`. **Sem paginação** — uma prova com mesmo histórico extenso (ex: 5 reinícios de ciclo + 30 transições) ainda cabe folgadamente em uma resposta. Hard cap defensivo: 500 itens (se ultrapassar, retorna 500 ordenado por `desc` truncado — sentinela para investigação).

**Códigos HTTP:** 200, 401, 403, 404 (prova não existe), 422.

**Convivência com `GET /api/v1/provas/{id}/movimentacoes`:** os endpoints são **diferentes em escopo**:

| Endpoint | Escopo | Acesso | Tabela |
|----------|--------|--------|--------|
| `GET /api/v1/provas/{id}/movimentacoes` (Wave 2) | Apenas transições (`status_anterior → status_novo`) | Admin + vendedor da prova + motorista/clicheria por status | `movimentacoes` |
| `GET /api/v1/audit-log/by-prova/{id}` (Wave 6) | Todas as ações (criação, scan, transição, reinício, cancelamento) | Admin-only | `audit_logs` |

A Wave 6 **NÃO altera** o endpoint da Wave 2. O Componente 08 (detalhe da prova) e o Componente 12 (Timeline) continuam usando o endpoint anterior. A Seção 3.8 detalha a checagem de regressão.

---

## 3.4 Modelo de autorização em três camadas

| Camada | Implementação | Reuso? | Falha quando? |
|--------|---------------|--------|---------------|
| 1. Middleware RBAC | `Depends(get_admin_user)` em `backend/app/api/deps.py` (linhas 95-104) | 100% reuso — mesma função usada em `/api/v1/users`, `/api/v1/configuracoes`, `/api/v1/provas` (POST/PATCH), `/api/v1/reports` | 401 se sem JWT, 403 se `is_admin != true` — antes de qualquer query DB |
| 2. RLS (defesa em profundidade) | `pol_audit_select` em `audit_logs` (RLS 005) — `auth_uid = (SELECT auth.uid()) AND is_admin = true` | 100% reuso — policy já existe e está ativa em produção | Mesmo se backend bypassasse o middleware (bug), supabase-js direto retorna 0 linhas para não-admin. Backend usa `service_role` e bypassa RLS — esta camada protege o **caso supabase-js direto** (que hoje não acontece, mas é a camada que protege se a arquitetura mudar) |
| 3. Frontend guard | (a) Item de menu "Auditoria" condicional ao `is_admin` no `(dashboard)/layout.tsx`. (b) Página `/auditoria` faz fetch `/api/v1/users/me` no mount; se `!is_admin`, renderiza estado de erro "Acesso restrito" e oferece link de retorno. (c) Atalho de teclado `g a` (admin-only) opcional, padrão `g r` da Wave 5 | Reusa pattern do `g r` em `useGlobalShortcuts.ts` | UX: usuário sem permissão nunca vê o link nem é levado à URL diretamente. Mas a defesa real está nas camadas 1 e 2 — frontend é apenas conveniência |

**Teste explícito da camada 2 (independente da 1):**

```python
# tests/test_audit_log_api.py — RLS test
async def test_rls_blocks_non_admin_via_postgres_role(db_authenticated_as_vendedor):
    """Mesmo se um vendedor pegar conexão direta com role authenticated,
    RLS retorna 0 linhas. Defesa em profundidade RNF-005."""
    rows = await db_authenticated_as_vendedor.execute(
        text("SELECT count(*) FROM audit_logs")
    )
    assert rows.scalar() == 0  # mesmo com 74 linhas reais na tabela
```

---

## 3.5 Desenho da UI

### 3.5.1 Rota e estrutura

- **Rota:** `/auditoria` (português, consistente com `/relatorios`, `/usuarios`, `/configuracoes`).
- **Layout:** `frontend/src/app/(dashboard)/auditoria/page.tsx` + `auditoria.module.css` (CSS Modules — projeto não usa Tailwind).
- **Subrota opcional:** `frontend/src/app/(dashboard)/auditoria/[id]/page.tsx` para detalhe — **considerada e rejeitada** em favor de drawer/modal lateral (estado da rota não muda, evita reload visual).

### 3.5.2 Componentes da página

```
┌─────────────────────────────────────────────────────────────────┐
│ <h1>Auditoria</h1>                                              │
│ <p>Log imutável de todas as ações do sistema (RNF-005).</p>     │
│                                                                 │
│ ┌──────────────────── filtersBar ─────────────────────────────┐ │
│ │ DateRangeFilter | SearchInput (q) | acao select | usuario   │ │
│ │                                              | prova        │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌────────────────────────── tabela ─────────────────────────────┐│
│ │ Data | Ação | Ator (setor) | Prova (#req) | IP | [→]          ││
│ │ ...74 linhas com badge colorido em REPROVADA / reiniciar_ciclo││
│ └───────────────────────────────────────────────────────────────┘│
│                                                                 │
│ ┌── paginação (Wave 2 C07 padrão) ───────────────────────────┐  │
│ │ [<] 1 2 3 ... 8 [>]    Mostrando 1–50 de 374              │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                 │
│ Estado vazio: "Nenhum registro encontrado para os filtros..."   │
│ Estado de erro: "Falha ao carregar auditoria. [Tentar novamente]│
│ Sem permissão: "Acesso restrito ao perfil 3Studio."            │
│                                                                 │
│ Drawer lateral ao clicar [→]:                                   │
│ ┌─── AuditLogDetailDrawer ────────────────────────────────────┐ │
│ │ Cabeçalho: Ação · Data · Ator                               │ │
│ │ Detalhes: <pre>{JSON.stringify(detalhes_json, null, 2)}</pre>│ │
│ │ Se transitar_status: status_anterior → status_novo + motivo │ │
│ │ Se reiniciar_ciclo: ciclo_X → ciclo_Y                       │ │
│ │ IP, User Agent (truncado em 80 chars + tooltip)             │ │
│ │ Botão "Fechar" — NENHUM botão de mutação                    │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 3.5.3 Reuso de componentes shared

| Componente | Origem | Reuso na Wave 6 |
|-----------|--------|------------------|
| `DateRangeFilter` | `frontend/src/components/filters/DateRangeFilter.tsx` (Wave 5 ADR-106) | ✅ direto |
| `SearchInput` | `frontend/src/components/filters/SearchInput.tsx` (Wave 5) | ✅ direto, com debounce 300ms |
| Padrão de paginação | `frontend/src/app/(dashboard)/provas/page.tsx` (Wave 2 C07) | ✅ extrair em `<Pagination>` shared se ainda não foi feito (verificar; senão duplicar inline e abrir spawn task para refator pós-Wave 6) |
| Drawer/modal lateral | `frontend/src/app/(dashboard)/provas/[id]/AdminActions.tsx` modais (Wave 3 C13) | ✅ pattern direto |
| Badge de status | `STATUS_LABELS` em `frontend/src/lib/types/prova.ts` (Wave 2) | ✅ |
| `useFocusTrap` | `frontend/src/hooks/useFocusTrap.ts` (Wave 3 audit) | ✅ obrigatório no drawer |
| `apiFetch` | `frontend/src/lib/api.ts` | ✅ |
| `getToken` pattern | Wave 2 C07 página de provas (linha 53) | ✅ |

### 3.5.4 Indicadores visuais

Consistente com `Timeline.tsx` (Wave 3 C12):

- **Reprovação** (`acao=transitar_status` com `detalhes_json.para = REPROVADA_PELO_VENDEDOR`): badge vermelho `nodeReprovacao`.
- **Reinício de ciclo** (`acao=reiniciar_ciclo`): badge laranja (novo — adicionar `nodeReinicio` em `auditoria.module.css`).
- **Cancelamento** (`acao=transitar_status` com `detalhes_json.para = CANCELADA`): badge vermelho-marrom `nodeCancelamento`.
- **Demais**: cinza neutro.

### 3.5.5 Proibições explícitas

A página NÃO terá:
- Botão "Editar"
- Botão "Excluir"
- Botão "Exportar CSV/PDF" (fora de escopo — registrar como Won't Have v1 no DECISIONS.md)
- Botão "Anonimizar"
- Botão "Marcar como visto"

A interface é **estritamente read-only** por construção. Teste explícito de regressão verifica ausência de qualquer `<button>` ou `<form>` que postcommit dispare HTTP `POST/PUT/PATCH/DELETE` na página.

---

## 3.6 Estratégia de testes

Alinhada com Seção 3 do DAT v2.0 — três camadas, meta ≥80% na lógica de negócio.

### 3.6.1 Unitários (pytest + pytest-asyncio)

**Localização:** `backend/tests/test_audit_log_api.py` (testes que não precisam de DB) + `backend/tests/test_audit_log_service.py` (camada de serviço).

| Teste | Cobre |
|-------|-------|
| `test_query_pagination_offset_calc` | `(page-1) * page_size` — bordas: page=1, page=N, page_size=200 |
| `test_query_filter_validation_rejects_negative_page` | Pydantic `page >= 1` |
| `test_query_filter_validation_rejects_oversized_q` | Pydantic `q.max_length = 200` |
| `test_query_filter_validation_rejects_inverted_dates` | `from_dt < to_dt` |
| `test_query_filter_validation_rejects_range_over_366_days` | Consistência com reports |
| `test_query_filter_parses_q_strips_control_chars` | Sanitização defensiva |
| `test_response_serializer_omits_assinatura_digital` | Garantia de privacidade — BYTEA nunca vai pra response |
| `test_response_serializer_truncates_user_agent_at_2000_chars` | (já feito por audit_service mas regressão na response) |
| `test_admin_guard_function_isolated` | `get_admin_user` separado |

### 3.6.2 Integração (pytest + httpx AsyncClient + DB real)

**Localização:** `backend/tests/test_audit_log_api.py` (mesma file).

**Fixtures novas em `conftest.py`:** `seed_audit_logs(make_user, mock_db)` — popula 20 linhas variadas em `audit_logs` cobrindo todas as 6 ações conhecidas + 1 admin user, 1 vendedor, 1 motorista, 1 clicheria.

| Cenário | Resultado esperado |
|---------|---------------------|
| `GET /api/v1/audit-log` como **admin** sem filtros | 200 — 20 itens, total=20 |
| `GET /api/v1/audit-log?page_size=5&page=2` como admin | 200 — 5 itens da página 2, total=20 |
| `GET /api/v1/audit-log?acao=transitar_status` como admin | 200 — só transições |
| `GET /api/v1/audit-log?prova_id=<X>` como admin | 200 — só linhas dessa prova |
| `GET /api/v1/audit-log?from_dt=...&to_dt=...` como admin | 200 — só dentro do intervalo |
| `GET /api/v1/audit-log?q=cor%20errada` como admin | 200 — encontra `motivo_reprovacao` |
| `GET /api/v1/audit-log` como **vendedor** | 403 |
| `GET /api/v1/audit-log` como **motorista** | 403 |
| `GET /api/v1/audit-log` como **clicheria** | 403 |
| `GET /api/v1/audit-log` **sem token** | 401 |
| `GET /api/v1/audit-log/{uuid_inexistente}` como admin | 404 |
| `GET /api/v1/audit-log/by-prova/{uuid_inexistente}` como admin | 404 |
| `GET /api/v1/audit-log/by-prova/{prova_existente}` como admin | 200 — todas as ações dessa prova ordem cronológica |
| `POST /api/v1/audit-log` (qualquer payload) como admin | 405 Method Not Allowed (router não declara POST) |
| `PUT/PATCH/DELETE /api/v1/audit-log/{id}` como admin | 405 |
| Verbo HEAD/OPTIONS funcionam (FastAPI default) | 200/204 |

### 3.6.3 RLS direto (cliente impersonando role) — defesa em profundidade

| Cenário | Resultado esperado |
|---------|---------------------|
| `SET ROLE authenticated; SET request.jwt.claim.sub = '<vendedor_auth_uid>'; SELECT count(*) FROM audit_logs;` | 0 — RLS bloqueia mesmo com 20 linhas |
| Mesmo SQL com `<admin_auth_uid>` | 20 |
| `SET ROLE authenticated; INSERT INTO audit_logs (...) VALUES (...);` | RLS error — sem policy INSERT |
| `SET ROLE authenticated; UPDATE audit_logs SET acao='hack' WHERE ...;` | Trigger error `Operação UPDATE não permitida` |
| `SET ROLE authenticated; DELETE FROM audit_logs;` | Trigger error |

Testes implementados via `execute_sql` direto contra DB de teste (Supabase local ou container). Padrão visto em `tests/test_provas_api.py` da Wave 2 quando se cobriu RLS.

### 3.6.4 E2E (Playwright)

**Localização:** `frontend/tests/e2e/auditoria.spec.ts` (criar diretório se não existir).

**Pré-requisito:** Playwright já configurado para Wave 4+ E2E (verificar — se não, instalar como parte da Wave 6 só para o cenário de auditoria; sem mudar versão de outras libs).

| Cenário | Passos | Resultado |
|---------|--------|-----------|
| Admin happy path | login admin → menu "Auditoria" → ver listagem → aplicar filtro de data → ver subset → clicar em uma linha → drawer abre com detalhes | Drawer não tem botão de mutação |
| Vendedor bloqueado | login vendedor → tentar `/auditoria` direto na URL | Página renderiza estado "Acesso restrito" + link "Voltar" |
| Anônimo bloqueado | sem login → tentar `/auditoria` direto | Redirect para `/login` (middleware Next.js) |

### 3.6.5 Cobertura

- Meta: **≥ 80% nas camadas de serviço e de domínio** do backend novo (`backend/app/api/v1/audit_log.py` + helpers).
- Meta: **100% dos endpoints críticos** (todos os 3) com teste de integração verde.
- Verificação: `coverage report --fail-under=80 --include=backend/app/api/v1/audit_log.py` no CI.

---

## 3.7 Migrations previstas

Todas **aditivas e idempotentes**. Nenhum `DROP`, `ALTER COLUMN` destrutivo, ou renomeação.

### 3.7.1 Migration 012 (Alembic) — possíveis índices de leitura

**Aplicar apenas se EXPLAIN ANALYZE durante a implementação mostrar gargalo.** Hoje a tabela tem 74 linhas e qualquer query é instantânea. Avaliar quando:
- Query de listagem com 4 filtros simultâneos (data + acao + usuario + prova).
- Tabela > 10k linhas.

**Candidatos:**

```sql
-- (a) Composite para filtro mais comum: período + ação
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_acao
  ON audit_logs (created_at DESC, acao);

-- (b) Composite para detalhe por prova + ordem cronológica
CREATE INDEX IF NOT EXISTS idx_audit_logs_prova_created
  ON audit_logs (prova_id, created_at ASC) WHERE prova_id IS NOT NULL;
```

**Decisão default:** **NÃO criar** preemptivamente. Os 4 índices existentes (`idx_audit_prova`, `idx_audit_usuario`, `idx_audit_acao`, `idx_audit_created_at`) já cobrem os filtros isolados; o planner escolherá o melhor. Criar só se EXPLAIN mostrar `Seq Scan` em volume real. Registrar em ADR a decisão tomada após o EXPLAIN.

### 3.7.2 RLS 008 — REVOKE explícito (proposta opcional)

```sql
-- backend/migrations/rls/008_revoke_audit_logs_mutation.sql
-- Defesa em profundidade RNF-005 — ver §3.2 do docs/wave6/analysis.md.
REVOKE INSERT, UPDATE, DELETE ON public.audit_logs FROM anon, authenticated;
```

**Aplicar:** sim (default), salvo manifestação contrária do Mario. Aditivo, idempotente, zero-impacto operacional.

### 3.7.3 NÃO PROIBIDO

- Tocar em `001_create_enums_tables_triggers_indexes.py` (Wave 0)
- Renomear ou alterar `audit_logs.acao` ou qualquer coluna existente
- Alterar policy `pol_audit_select` (já correta)
- Adicionar trigger novo a `audit_logs` (já tem o de imutabilidade — adicionar mais é confuso e desnecessário)

---

## 3.8 Riscos e pontos de atenção

| # | Risco | Probabilidade | Impacto | Mitigação |
|---|-------|---------------|---------|-----------|
| R1 | **Vazamento de PII via log** — `detalhes_json` contém `cliente`, `vendedor_nome`, `motivo_reprovacao` em texto livre. Em produção há registros tipo `"motivo_reprovacao": "Cor errada"`. Em pior caso futuro, alguém pode escrever info sensível. | Médio | Médio | Restrição admin-only + log do próprio acesso ao audit (logger.info no endpoint). Documentar no DECISIONS.md que `detalhes_json` é considerado PII e nunca deve ser exportado para fora do sistema. UI exibe o JSON dentro do drawer (sem permitir copiar para clipboard sem ação explícita). |
| R2 | **Crescimento indefinido da tabela** — 74 linhas hoje, mas poderá chegar a 100k+/ano em uso pleno. Listagem sem paginação seria fatal. | Alta (longo prazo) | Alto se mal planejado | Paginação obrigatória (sem `?all=true`). `page_size` máximo 200. Hard cap em `by-prova` de 500. Considerar partition por mês em Wave 7+ (não é problema agora — registrar como Won't Have v1). |
| R3 | **Divergência UI vs realidade pós-reinício de ciclo** — uma prova com 3 ciclos tem `audit_logs` com `detalhes_json.ciclo` variando de 1 a 3. Listagem precisa exibir o ciclo do evento, não confundir com `provas_digitais.ciclo_atual`. | Baixa (já tratado por design) | Médio | Frontend lê `detalhes_json.ciclo` (preservado pelo `executar_transicao`) para exibir "Ciclo X" no card; nunca confiar em `prova.ciclo_atual` para reconstrução histórica. |
| R4 | **Dependência implícita do Componente 08/12** — se durante o Gate 2 surgir tentação de "unificar a Timeline da prova com o /auditoria/by-prova/{id}", isso violaria o isolamento de wave. | Média | Alto | NÃO unificar. Componentes 08 e 12 continuam intocados. A Wave 6 oferece **outra visão**, complementar — admin-only. Documentar essa convivência claramente no DECISIONS.md. |
| R5 | **Cache stale** — diferente do Wave 5 reports, o audit-log NÃO deve ter cache TTL. Cada request deve refletir o estado atual da tabela (admin pode estar investigando incidente em tempo real). | Baixa | Médio | NÃO usar `ReportCache` (Wave 5). Sem ETag agressivo. `Cache-Control: no-store`. Log de aplicação INFO confirma "no caching by design". |
| R6 | **Carga em produção pelos 4 índices `unused_index` advisor** — após Wave 6 entrar em uso, advisor passa a remover esses 4 da lista. | Nenhuma | Nenhuma | Não-issue. Apenas informacional. Verificar pós-deploy que o advisor reflete o uso. |
| R7 | **Imutabilidade NÃO endurecida no GRANT level** — risco residual baixíssimo, hoje protegido por trigger + RLS. | Muito baixa | Médio (se RLS for desabilitada por engano no futuro) | RLS 008 com REVOKE — proposta na §3.7.2. |
| R8 | **`movimentacao_relacionada` no detalhe (§3.3.2)** — solução A (query por janela ±5s) é frágil se 2 transições da mesma prova ocorrerem em < 5s; solução B (passar `movimentacao_id` no `detalhes_json`) é mais limpa mas requer pequena alteração no `executar_transicao`. | Média (de ocorrência da janela) | Baixa (ambiguidade na UI, não corrupção de dado) | **Decisão a confirmar antes do Gate 2:** preferir B, mas só se Mario autorizar a alteração mínima na Wave 3. Alternativa C: pular o enriquecimento no detalhe — mostrar só o JSON. |
| R9 | **Frontend admin guard via fetch `/users/me`** — janela de 200-500ms entre carregamento e checagem do `is_admin` em que a UI pode "flickar". | Baixa | Baixo (UX) | Renderizar skeleton/spinner enquanto `me` é null. **Defesa real está nas camadas 1+2** — mesmo com flicker, vendedor recebe 403 ao tentar listar. |
| R10 | **Item de menu "Informacoes" no layout** ainda placeholder (visto em `(dashboard)/layout.tsx` linha 57). Adicionar "Auditoria" requer extender `MAIN_NAV` ou `SECONDARY_NAV` — sem mexer em outras entries. | Baixa | Baixo | Adicionar como item novo em `MAIN_NAV` (entre `relatorios` e `usuarios`) ou em `SECONDARY_NAV` (depende de orientação visual do Mario). Default proposto: **`MAIN_NAV`** entre `usuarios` e `configuracoes`. Item visível só se `user.is_admin`. |

---

## 3.9 Entregável do Gate 1

- **Arquivo:** [docs/wave6/analysis.md](analysis.md) (este documento)
- **Branch:** `wave6/analysis` (criado a partir de `main` no estado HEAD = `dbd250c`)
- **Commit:** `docs(wave6): analise read-only pre-execucao` (a fazer agora, com escopo restrito apenas a este arquivo — `git add docs/wave6/analysis.md` específico, não usar `-A`)
- **Sem merge:** o branch fica disponível para revisão; merge para `main` só após autorização do Gate 2 e conclusão do Componente 18.

**Próximos passos (após autorização):**

1. Receber a string exata `AUTORIZADO GATE 2 — WAVE 6` do solicitante.
2. Incorporar correções/ajustes que vierem junto da autorização.
3. Criar branch `wave6/componente-18` a partir do estado mais recente de `main`.
4. Seguir a ordem de execução da §4.1 do prompt (migrations → backend domínio → backend serviço → backend API → testes → frontend cliente → frontend página → frontend guard → E2E → docs).
5. Confirmar com Mario as 3 decisões pendentes:
   - **D1:** Aplicar `REVOKE` em RLS 008? (default proposto: **sim**)
   - **D2:** Como resolver `movimentacao_relacionada` no detalhe? (default proposto: **opção B** — passar `movimentacao_id` no `detalhes_json` via pequena alteração em `executar_transicao` — REQUER autorização explícita por violar isolamento da Wave 3)
   - **D3:** Item "Auditoria" em `MAIN_NAV` ou `SECONDARY_NAV`? (default proposto: **MAIN_NAV** entre `usuarios` e `configuracoes`)

---

## Apêndice A — Endpoints existentes consultados (read-only) para entender contratos

Lista exaustiva dos arquivos lidos e linhas de referência principais:

- [backend/app/db/models.py:209-236](../../backend/app/db/models.py) — modelo `AuditLog`
- [backend/app/db/models.py:139-179](../../backend/app/db/models.py) — modelo `Movimentacao`
- [backend/app/services/audit_service.py:24-111](../../backend/app/services/audit_service.py) — `_extract_client_ip` + `log_audit`
- [backend/app/services/state_machine.py:231-440](../../backend/app/services/state_machine.py) — `executar_transicao` (escreve audit_logs + movimentacoes na mesma transação)
- [backend/app/api/deps.py:30-104](../../backend/app/api/deps.py) — `get_current_user`, `get_admin_user`, `require_role`
- [backend/app/api/v1/provas.py:1283-1351](../../backend/app/api/v1/provas.py) — `list_movimentacoes` (Wave 2 C08; convive com `/audit-log/by-prova/{id}` da Wave 6)
- [backend/app/api/v1/provas.py:1836+](../../backend/app/api/v1/provas.py) — endpoint `POST /transicoes` (Wave 3 C11; produtor primário do log)
- [backend/app/api/v1/provas.py:2023+](../../backend/app/api/v1/provas.py) — endpoint `POST /cancelar` (Wave 3 C13)
- [backend/app/api/v1/provas.py:2149+](../../backend/app/api/v1/provas.py) — endpoint `POST /reiniciar-ciclo` (Wave 3 C14)
- [backend/app/api/v1/reports.py:14-106](../../backend/app/api/v1/reports.py) — padrão admin-only de Wave 5 (referência de estilo)
- [backend/migrations/rls/004_unify_rls_is_admin.sql:116-126](../../backend/migrations/rls/004_unify_rls_is_admin.sql) — `pol_audit_select` original
- [backend/migrations/rls/005_initplan_optimization.sql:187-198](../../backend/migrations/rls/005_initplan_optimization.sql) — `pol_audit_select` otimizada com `(SELECT auth.uid())`
- [backend/migrations/rls/006_movimentacoes_insert_and_expand_select.sql](../../backend/migrations/rls/006_movimentacoes_insert_and_expand_select.sql) — INSERT policy + SELECT expandida (ADR-082)
- [docs/db/schema.sql:136-145, 252, 270](../db/schema.sql) — DDL `audit_logs` + RLS comment
- [frontend/src/app/(dashboard)/layout.tsx:46-58](../../frontend/src/app/(dashboard)/layout.tsx) — `MAIN_NAV` + `SECONDARY_NAV` (item "Informacoes" placeholder)
- [frontend/src/app/(dashboard)/provas/[id]/Timeline.tsx:1-273](../../frontend/src/app/(dashboard)/provas/%5Bid%5D/Timeline.tsx) — convenções visuais para reprovação/cancelamento/terminal
- [frontend/src/app/(dashboard)/provas/page.tsx:1-120](../../frontend/src/app/(dashboard)/provas/page.tsx) — padrão de paginação + filtros URL-persisted (a reusar)

---

**Fim da análise — Gate 1.** Aguardando autorização explícita `AUTORIZADO GATE 2 — WAVE 6` para iniciar a execução.

---

## Execução (anexado pós-Gate 2 — 2026-04-29)

Autorização recebida em 2026-04-29 ("Autorizado", interpretado como liberação para Gate 2 com defaults da §3.9). 11 tarefas executadas em sequência, todos os commits no branch `wave6/componente-18` (a partir de `wave6/analysis`):

| # | Commit | Descrição | Linhas |
|---|--------|-----------|--------|
| 1 | `be63f22` | RLS 008: REVOKE INSERT/UPDATE/DELETE em audit_logs | +47 |
| 2 | `a556a4a` | Backend — schemas + service + router | +899 |
| 3 | `e6bb772` | Backend tests (63 testes, 95% cov) | +943 |
| 4 | `8372da6` | (Housekeeping) commitar L-F1 do useGlobalShortcuts (Wave 5 R2 ADR-109) | +6 -3 |
| 5 | `eb771b3` | Frontend — página /auditoria + tipos + hook + ícone + atalho `g a` + menu admin-only | +1581 -1 |

Total Wave 6: **5 commits, ~3470 linhas adicionadas, 0 regressão** (689 testes passando, era 639 antes).

### Diff Gate 1 → execução real

| Item proposto no Gate 1 | Implementado | Justificativa de divergência |
|------------------------|--------------|------------------------------|
| 3 endpoints sob `/api/v1/audit-log` | ✅ idêntico | — |
| RBAC via `Depends(get_admin_user)` reusado | ✅ idêntico | — |
| RLS já existente + REVOKE 008 | ✅ aplicado em produção | D1 default = sim |
| `movimentacao_relacionada` matching com 3 chaves + janela ±5s | ✅ implementado | D2 endurecida — usa `prova_id + status_novo (de detalhes_json.para) + ciclo (de detalhes_json.ciclo)` para desambiguar matches dentro da janela. **Não tocou** código da Wave 3. |
| Item de menu "Auditoria" entre `usuarios` e `configuracoes` | ✅ idêntico | D3 default = MAIN_NAV |
| Atalho `g a` admin-only | ✅ idêntico | Adicionado ao SHORTCUT_DEFS |
| Cache `no-store` (sem TTL/ETag) | ✅ idêntico | ADR-111 |
| Reuso de DateRangeFilter/SearchInput shared | ❌ não reusado, criado inline | Descoberto durante implementação que esses componentes vivem em `(dashboard)/relatorios/`, não em `components/filters/`. Estão acoplados ao módulo `relatorios.module.css` e seria refator maior do que a Wave 6 acomoda. **Inline simples** com `<input type="search">` e `<input type="date">` consistente com o padrão de `/provas` (Wave 2 C07). Registrado como follow-up para refator pós-Wave 6 se ficar evidente que múltiplas páginas precisam dos mesmos filtros. |
| Migration Alembic 012 com índices preemptivos | ❌ não criada | EXPLAIN ANALYZE não foi necessário em smoke — 74 linhas instantâneas. Os 4 índices existentes em `audit_logs` cobrem os filtros isolados. Decisão: criar só se gargalo aparecer em produção. |
| E2E Playwright (`auditoria.spec.ts`) | ⚠️ não implementado | Playwright não está configurado para Wave 4+. Smoke manual via curl + build estático Next.js (passou) substitui o critério no curto prazo. **Marcado como follow-up para Wave 7** — registrar em DECISIONS se necessário. |

### Validação manual executada

- `pytest` suite completa: **689 passou, 0 falhou, 2 warnings** (Pydantic deprecation + JWT key length, ambos pré-existentes).
- `coverage`: novo código a 95% (router 86%, service 99%, schemas 99%).
- `npx next build`: rota `/auditoria` compila como **5.68 kB / 164 kB First Load**, 13 rotas estáticas.
- `npx tsc --noEmit`: TypeScript strict OK.
- `curl` smoke contra backend local (porta 8001):
  - `GET /api/v1/audit-log` sem auth → **401** ✅
  - `GET /api/v1/audit-log/abc` (UUID malformado) → **404** ✅
  - `GET /api/v1/audit-log/by-prova/abc` → **404** ✅
  - `POST /api/v1/audit-log` → **405** ✅ (imutabilidade)
  - `DELETE /api/v1/audit-log/abc` → **405** ✅
  - `GET /api/v1/audit-log` com bad token → **401** ✅
- Validação Supabase via MCP `has_table_privilege` pós-RLS 008:
  - `authenticated`: SELECT=true, INSERT/UPDATE/DELETE=**false** ✅
  - `anon`: SELECT=true, INSERT/UPDATE/DELETE=**false** ✅
  - `service_role`: INSERT=true, SELECT=true ✅ (backend continua escrevendo)

### Pendências e follow-ups

- **E2E Playwright:** scenário de admin autorizado + vendedor bloqueado + anônimo bloqueado. Pode ser feito via Playwright em Wave 7 (Polish) ou via teste manual com browser real apenas no momento de PR review.
- **Reuso de filtros shared:** extrair `DateRangeFilter`/`SearchInput`/`StatusFilter`/`VendedorFilter` para `frontend/src/components/filters/` em refator dedicado, reusando em `/relatorios` + `/auditoria` + `/provas`. Não é trivial — depende de extrair também o CSS shared. Wave 7 candidata.
- **Migration Alembic 012:** acompanhar advisor Supabase pós-Wave 6 — quando os 4 índices `unused_index` deixarem a lista (sinal de uso real), avaliar se filtros compostos justificam novos índices.
- **REVOKE em movimentacoes/etiquetas:** consistência conceitual com RLS 008. Wave 7 candidata (registrado em ADR-112 alternativas rejeitadas).

### Estado final do banco em produção (`rwxlpwmnkekzuurgthkr`)

- `alembic_version = 011` (inalterado — Wave 6 não criou Alembic).
- 7 migrations RLS aplicadas (007 → 008 nova).
- 12 RLS policies inalteradas + REVOKE explícito em `audit_logs`.
- 32 índices inalterados.
- Advisors pós-Wave 6: idêntico ao pré-Wave 6 (1 INFO `rls_enabled_no_policy` em `alembic_version`, 1 WARN `auth_leaked_password_protection`, 14 INFO `unused_index` — esperado-cair conforme Wave 6 entrar em uso).

---

## UX iteration — pacote A+B (anexado pós-conversa em 2026-04-29)

Após o Gate 2 entregue, Mario pediu reforço de UX visando uso real em produção (~350 provas/mês × ~15 audits/prova = ~5k audits/mês = ~60k/ano). O caso de uso primário do admin é "encontrar o que aconteceu rapidamente em volume crescente". Pacote A (filtros mais inteligentes) + B (navegação em volume) implementado neste mesmo branch.

### Itens entregues

| Item | Descrição | Arquivos |
|------|-----------|----------|
| **A1** | Presets de data (Hoje · 7d · 30d · 90d · Personalizado) com default automático "Hoje" no primeiro acesso | [auditLog.ts](../../frontend/src/lib/types/auditLog.ts) (`presetToRange`, `detectPreset`), [page.tsx](../../frontend/src/app/(dashboard)/auditoria/page.tsx) |
| **A2** | Dropdown semântico de tipo de evento (6 categorias) que esconde do admin a complexidade do par `(acao, detalhes_json.para)` | [audit_log.py schema](../../backend/app/domain/schemas/audit_log.py) (`tipo_evento` + `TIPOS_EVENTO_VALIDOS`), [audit_log_service.py](../../backend/app/services/audit_log_service.py) (`_aplicar_tipo_evento`) |
| **A3** | Dropdown de Ator populado via `GET /api/v1/users` (todos ativos, max 200) | [page.tsx](../../frontend/src/app/(dashboard)/auditoria/page.tsx) (`useEffect fetchUsuarios`) |
| **A4** | Busca `q` agora procura simultaneamente em `audit_logs.detalhes_json::text` E em `provas_digitais.nro_requerimento` (admin pode colar nº de requerimento humano) | [audit_log_service.py:_aplicar_filtros](../../backend/app/services/audit_log_service.py) (OR clause + count com JOIN) |
| **B1** | Paginação numerada com janela inteligente + form "Ir para página" quando total > 5 | [page.tsx:buildPageWindow](../../frontend/src/app/(dashboard)/auditoria/page.tsx), [auditoria.module.css](../../frontend/src/app/(dashboard)/auditoria/auditoria.module.css) |
| **B2** | Dropdown "Linhas por página" com 25/50/100/200 | [page.tsx](../../frontend/src/app/(dashboard)/auditoria/page.tsx) |
| **B3** | Sticky header (`position: sticky; top: 0; z-index: 5`) + container com `max-height: 70vh; overflow-y: auto` | [auditoria.module.css](../../frontend/src/app/(dashboard)/auditoria/auditoria.module.css) |
| **B4** | Cabeçalhos clicáveis nas colunas Data/Ação/Ator. `order_by` no backend com whitelist defensiva (created_at, acao, usuario_nome). Tiebreaker por id mantido | [audit_log.py schema](../../backend/app/domain/schemas/audit_log.py) (`order_by` + `ORDER_BY_VALIDOS`), [audit_log_service.py](../../backend/app/services/audit_log_service.py) (`_resolver_order_by_column`) |

### Mudanças de contrato

Sem breaking changes. Novos query params no `GET /api/v1/audit-log`:
- `tipo_evento` (string opcional, whitelist 6 valores)
- `order_by` (string opcional, whitelist 3 valores, default `created_at`)

Comportamento default preservado: clientes existentes sem esses params continuam recebendo a mesma resposta de antes.

### Testes

20 testes novos em `tests/test_audit_log_api.py`:
- 7 cobrindo `tipo_evento` (schema validation, normalização case-insensitive, mapeamento por valor)
- 7 cobrindo `order_by` (whitelist, default, defesa anti-SQL-injection, helper de resolução)
- 1 cobrindo expansão de `q` para `nro_requerimento` (inspeção do SQL compilado)
- 5 cobrindo edge cases adicionais

Suite total: **722 passando** (era 689 antes desta iteração). Cobertura novo código: 92% (router 86%, service 88%, schemas 99%).

### Validação

- `npx tsc --noEmit`: OK
- `npx next build`: `/auditoria` cresceu de 5.68 kB → 7.27 kB (+1.59 kB), First Load 164 kB → 166 kB. Build limpo (warning é pré-existente em `provas.module.css`).
- Suite backend completa: 722 passando, 0 regressão.

### Defesa contra SQL injection no `order_by`

Embora `order_by` seja string que poderia ser injetado num `ORDER BY <col>`, a defesa é em duas camadas:

1. **Schema Pydantic** (`validate_order_by`) valida contra `ORDER_BY_VALIDOS = frozenset({"created_at", "acao", "usuario_nome"})`. Qualquer outro valor produz 422.
2. **Service** (`_resolver_order_by_column`) usa `if/elif` explícito em vez de `getattr` reflexivo — mesmo se o schema for contornado, apenas as 3 colunas conhecidas chegam ao SQL.

Teste explícito: `test_schema_rejeita_coluna_arbitraria` cobre `"id; DROP TABLE"` e `"ip_address"` (não na whitelist).

### Pendências e follow-ups

- Verificação visual com login real ainda dependente do Mario (sem credenciais durante a sessão).
- E2E Playwright continua como follow-up Wave 7.
- C (live mode) e D (conveniência) não foram implementados — pacotes que podem entrar em iteração futura conforme uso real evidenciar necessidade.
