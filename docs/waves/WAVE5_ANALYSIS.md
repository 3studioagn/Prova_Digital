# WAVE 5 — ANALYSIS (Plano de Execução · Gate Obrigatório)

> **Camada analítica do sistema.** Esta wave existe para revelar gargalos da operação real. Cada agregação, cada índice e cada contrato de API serão tratados como auditados em produção.
>
> **Status:** aguardando GO do Mario antes de qualquer escrita de código (Fase 4).
>
> **Princípio inviolável desta wave (reforço do briefing 2026-04-27):** *minimizar o número de queries e requisições que tocam o banco em qualquer sessão de uso real.* Cada decisão deste documento está justificada também por esse vetor.

---

## 0. Pré-Wave 5 — Reconciliação de drift detectado na Fase 1

Antes de tocar em qualquer arquivo da Wave 5, é preciso reconciliar a divergência entre `alembic_version=010` em produção e o repo em `009`. **Não há mudança de banco** — apenas restaurar arquivos no repositório para refletir a realidade.

### 0.1 Migration 010 — recovery 1:1 do estado de produção

A inspeção mostrou que a migration `010_add_indexes_for_wave5_reports.py` foi aplicada ao banco em 2026-04-15 (commit antigo `5db44bb`, depois revertido com `git reset` mas o banco permaneceu em 010). Os 2 índices criados estão exatamente onde a Wave 5 precisa:

```sql
-- Já existem em produção, NÃO recriar:
CREATE INDEX IF NOT EXISTS idx_movimentacoes_status_novo_created_at
  ON public.movimentacoes (status_novo, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_provas_vendedor_status
  ON public.provas_digitais (vendedor_id, status);
```

**Plano**: copiar `backend/migrations/versions/010_add_indexes_for_wave5_reports.py` literalmente do commit `5db44bb` (`down_revision="009"`, idempotente com `IF NOT EXISTS`, downgrade reversível). Atualizar [docs/db/schema.sql](../db/schema.sql) para incluir os 2 índices no bloco "5. ÍNDICES". Nenhuma chamada SQL contra produção será feita — `alembic upgrade head` rodando localmente vai detectar `IF NOT EXISTS` e não fazer nada além de carimbar `alembic_version`.

**ADR a registrar:** ADR-095 — Recovery da migration 010 órfã da Wave 5 anterior.

### 0.2 Indicador de drift residual

Sem outro drift detectado. Volumetria atual (sa-east-1):

| Tabela | Linhas | Tamanho total | Tamanho índices |
|---|---:|---:|---:|
| `provas_digitais` | 14 | 144 kB | 128 kB |
| `movimentacoes` | 14 | 296 kB | 112 kB |
| `audit_logs` | 64 | 144 kB | 80 kB |
| `usuarios` | 4 | 104 kB | 96 kB |

Total **< 1 MB**, free tier 500 MB. Em volume tão baixo, `EXPLAIN ANALYZE` mostra **planning time (0.85 ms) > execution time (0.22 ms)** — o gargalo não é throughput de DB, é **número de roundtrips e overhead de planejamento**. Isso pauta toda a estratégia de cache desta wave.

---

## 1. Escopo exato da Wave 5

Extraído de [BACKLOG_RastreioProvasDigitais_v3_0.docx](../../../Desktop/Rastreio%20Prova%20Digital/BACKLOG_RastreioProvasDigitais_v3_0.docx) e amarrado a [Requisitos v3.0](../../../Desktop/Rastreio%20Prova%20Digital/RequisitosProvasDigitais_v3_0.docx).

### 1.1 Componente 16 — Relatórios Gerenciais (RF-015, US-014)

**O que tem que estar no relatório (literal do RF-015 + Requisitos §3.3 + briefing §4):**
- Tempo médio de aprovação por vendedor e geral
- Total de provas por vendedor
- Quantidade de provas atrasadas (RN-008 — horas corridas, ver §1.4)
- Total geral de provas
- Taxa de reprovação por vendedor
- Distribuição por rota (padrão vs. direta)
- Exportação CSV

**Quatro perspectivas tipadas (briefing §4):** `geral`, `3studio`, `vendedores`, `clicheria`. Cada uma com seu schema próprio em discriminated union — não shape genérico `dict[str, Any]`.

**Filtros obrigatórios** (RF-013 + briefing): `from`, `to`, `q` (busca por nome / cliente / nº requerimento), opcionais `vendedor_id`, `rota`, `status`. Padrão de janela: **últimos 30 dias** se `from`/`to` ausentes — protege a operação de uma query "tudo desde o início" acidental.

**Critérios de aceite (DoD adaptado):**
1. RBAC: somente `is_admin=true` acessa qualquer endpoint de `/reports/*`. Vendedores, motoristas, clicheria recebem 403.
2. Cobertura ≥ 80% em `app/services/report_*.py` (domínio/serviço). 100% em endpoints críticos via testes de integração.
3. RLS de `provas_digitais`, `movimentacoes`, `usuarios` cobre o admin (já cobre — confirmado em §3.4).
4. CSV exporta em UTF-8 com BOM, abrível em Excel sem mojibake; streaming via `StreamingResponse` + cursor (sem materializar resultado completo em memória).
5. Resposta JSON < 1s p95 para janela de 30 dias com volumetria projetada (3000 provas, 30000 movimentações). Em volumetria atual, deve ser <100ms.
6. Agregações idempotentes: mesma combinação (scope + filtros) na mesma janela temporal devolve resultado bit-exato — exceto quando o cache tem TTL e expirou.
7. Sem regressão nas Waves 0–4 (zero alteração em arquivos delas, exceto link "Relatórios" no sidebar e atalho no dashboard, ambos autorizados pelo escopo do Componente 17).

### 1.2 Componente 17 — Atalhos Rápidos (RF-016)

**RF-016 literal:** "atalhos rápidos com acesso direto a: escanear QR Code, visualizar provas e acessar relatórios."

**Estado atual (Wave 4):** dashboard tem 2 cards de atalho ("Escanear QR Code" + "Nova Prova"). Wave 4 marcou como aceito sem correção (M-02, ADR-093) reconhecendo a divergência com RF-016.

**Proposta para resolver D3 (sem tocar a Wave 4 em violação da regra inviolável §2.1):**

1. **Adicionar 3º card "Acessar Relatórios"** ao painel de atalhos do dashboard, na grade existente. Esta é a **única alteração permitida em arquivo da Wave 4** (`frontend/src/app/(dashboard)/dashboard/page.tsx` + seu CSS Module). Justificativa: o painel já existe, a alteração é puramente aditiva, e o RF-016 exige 3 atalhos visíveis. Sem essa adição, Wave 5 não pode declarar conformidade com RF-016.

2. **Camada nova de atalhos globais por teclado** — Componente 17 propriamente dito:
   - Hook `useGlobalShortcuts()` registrado no `(dashboard)/layout.tsx` (alteração mínima de 1 import + 1 chamada).
   - Atalhos: `g s` → `/escanear`, `g p` → `/provas`, `g r` → `/relatorios` (estilo GitHub two-keystroke).
   - Modal `<KeyboardShortcutsHelp />` aberto com `?` que lista os atalhos. Acessibilidade: focusable, fecha com Escape, focus trap reaproveitando `useFocusTrap` da Wave 3.
   - Filtragem por permissão: vendedor não vê atalho `g r` (Relatórios); admin 3Studio vê todos.
   - Documentar em `CLAUDE.md` na seção "Operacional".

**Critério de aceite Componente 17:**
1. 3 cards no dashboard cobrem RF-016 literal.
2. Atalhos de teclado funcionam em qualquer rota autenticada.
3. Modal de help acessível via `?`, fechável por Escape, com focus trap.
4. Atalhos respeitam RBAC (vendedor não navega para `/relatorios` via `g r` — UI não mostra a opção, e se digitar manualmente `/relatorios`, middleware redireciona).

### 1.3 Definition of Done — global da Wave 5

Espelho do DoD do Backlog Wave 0–3, adaptado para camada analítica:

1. Code review (manual via diff antes de cada commit).
2. Cobertura testes unit ≥ 80% em domínio/serviço novo.
3. Testes integração no endpoint, contra Postgres real (Supabase staging).
4. Migration 010 documentada (recovery — não nova).
5. Cada endpoint validado contra critério de aceite da US-014.
6. Console limpo no browser, log limpo no backend.
7. CLAUDE.md, CHANGELOG.md, DECISIONS.md atualizados ao fim da wave.
8. RLS auditada — sem novas policies necessárias (§3.4 confirma).

### 1.4 Decisão sobre RN-008 — horas corridas (opção B aprovada por Mario)

- **Requisito literal RN-008:** "horas úteis sem movimentação".
- **Wave 4 (ADR-091, decisão 4):** decidiu horas **corridas** com aprovação do Mario, justificando que "calcular horas úteis reais exigiria tabela de feriados + lógica de calendário — complexidade desproporcional para MVP".
- **Wave 5 (decisão Mario, 2026-04-27):** **manter horas corridas**, alinhando-se com Dashboard. Atualizar `descricao` da chave `tempo_atraso_horas_uteis` em `configuracoes_sistema` para refletir que o cálculo é em horas corridas (a chave **mantém o nome legacy** para não quebrar Wave 2/Wave 4 — ADR registra essa dívida nominal).
- **ADR a registrar:** ADR-099 — Wave 5 adota horas corridas (consistência com Wave 4) e documenta o desvio explícito do RN-008 literal. Re-evaluar em Wave 7+ se houver demanda de auditor externo.

---

## 2. Mapa de dependências (consumir, não modificar)

### 2.1 Tabelas (Wave 0/1/2/3)

| Tabela | Uso na Wave 5 |
|---|---|
| `movimentacoes` | **Fonte primária**. Todas as métricas temporais (tempo médio aprovação, taxa de reprovação por ciclo, distribuição) dependem do log imutável. |
| `provas_digitais` | Snapshot de status atual (filtro de "ativas vs terminais"), agrupamento por rota e vendedor. |
| `usuarios` | Joins para nome do vendedor e localização (`MATRIZ`/`FILIAL`) — desambiguação de homônimos via `Usuario.id` (lição L-01 da auditoria Wave 4). |
| `configuracoes_sistema` | Chave `tempo_atraso_horas_uteis` — leitura única por request (ou por cache hit). |
| `audit_logs` | Apenas para registrar acesso aos relatórios (RNF-005). Não é fonte de métricas. |
| `etiquetas` | Não é consumida na Wave 5. |

### 2.2 Helpers Python já existentes a reaproveitar

| Helper | Caminho | Reuso |
|---|---|---|
| `_scoping_filter(user)` | [backend/app/api/v1/provas.py:660](../../backend/app/api/v1/provas.py:660) | Defesa em profundidade (admin não filtra, mas helper devolve `None`). Endpoint de relatórios é admin-only via dependency, mas a borda do query builder pode usar para futuras extensões. |
| `BRT_TIMEZONE` | provas.py | Conversão UTC ↔ BRT em datas vindas do front. |
| `_dashboard_cache_get/_dashboard_cache_set` (padrão TTL) | provas.py | **Não reutilizar diretamente**. Wave 5 vai criar seu cache próprio (TTL maior, chaveamento por hash de filtros). Mas o padrão é o mesmo. |
| `audit_service.log_audit` | `backend/app/services/audit_service.py` | Logar `acao="REPORT_VIEWED"` ou `REPORT_EXPORTED` com detalhes do scope/filtros. |
| `get_admin_user` | `backend/app/api/deps.py` | Dependency RBAC para todos os endpoints. |

### 2.3 Frontend — reaproveitar

| Helper | Reuso |
|---|---|
| `apiFetch<T>` | Endpoints JSON de relatório. Para CSV usar `fetch` direto + `response.blob()` (binário, igual à etiqueta PDF — regra documentada em CLAUDE.md "Operacionais Aprendidas"). |
| `STATUS_LABELS`, `ROTA_LABELS` | i18n em CSV e UI. |
| `useFocusTrap` | Modal de help dos atalhos. |
| Tokens CSS (`--color-accent`, `--radius-*`) | Sem nova paleta. |
| Recharts | **Não reinstalar.** Wave 4 removeu (ADR-093). Para gráficos da Wave 5 ver §5.4 — opção é reaproveitar Framer Motion + SVG simples, ou aprovar reinstalação caso `BarChart` se mostre necessário. |

### 2.4 Realtime (Wave 4)

A publicação `supabase_realtime` já tem `provas_digitais`. **A Wave 5 reutiliza o canal** para invalidação de cache do front (qualquer INSERT/UPDATE → invalidar ETag local + refetch debounced). Sem nova publicação. Sem nova subscription server-side.

---

## 3. Modelo de dados

**Premissa central**: Wave 5 é primariamente leitura. Toda decisão de objeto novo precisa de justificativa explícita.

### 3.1 Tabelas e colunas novas

**Zero.** Confirmado pela inspeção da Fase 1 — nenhuma necessidade. Movimentações imutáveis já carregam todos os dados necessários (`status_anterior`, `status_novo`, `created_at`, `usuario_id`, `prova_id`, `ciclo`, `rota_no_momento`).

### 3.2 Índices

**Existentes em produção (após recovery 010):**

```
idx_provas_status_created                (status, created_at)        — janela temporal por status
idx_provas_vendedor_status               (vendedor_id, status)       — breakdown por vendedor (recovery 010)
idx_provas_created_at                    (created_at)                — janela temporal sem filtro
idx_movimentacoes_prova_data             (prova_id, created_at DESC) — última movimentação por prova
idx_movimentacoes_status_novo_created_at (status_novo, created_at DESC) — métricas por tipo de transição (recovery 010)
idx_movimentacoes_prova_ciclo            (prova_id, ciclo)           — agrupamento por ciclo
```

**Análise por query da Wave 5** (cada uma rodada com `EXPLAIN ANALYZE` antes de declarar Done):

| Query | Plano alvo | Índice atendendo |
|---|---|---|
| Provas no período (criadas) | Index Scan range em `created_at` | `idx_provas_created_at` ✅ |
| Snapshot por status no período | Index Scan + filter | `idx_provas_status_created` ✅ |
| Distribuição por rota (provas com `rota IS NOT NULL`) | Seq Scan em volume baixo aceitável; em volume alto `WHERE rota IS NOT NULL` é seletivo (~50%) | aceitável até 100k provas |
| Provas por vendedor com breakdown status | Index Scan composto | `idx_provas_vendedor_status` ✅ (recovery 010) |
| Tempo médio de aprovação por vendedor | Subquery `JOIN movimentacoes ON status_novo IN (APROVADA, REPROVADA)` | `idx_movimentacoes_status_novo_created_at` ✅ (recovery 010) |
| Taxa de reprovação por vendedor | Análoga acima — sobre **ciclos** (RN-006), não provas | `idx_movimentacoes_status_novo_created_at` ✅ |
| Reprovações por ciclo (3studio scope) | Mesma família | `idx_movimentacoes_status_novo_created_at` ✅ |
| Provas atrasadas | `coalesce(max(mov.created_at), prova.created_at) < limite` | `idx_movimentacoes_prova_data` ✅ + `idx_provas_status` ✅ |

**Conclusão**: **Nenhum índice novo é necessário** para esta wave. A migration 010 já cobre 100% das queries propostas. Decisão de não criar índices preventivos: cada índice tem custo de INSERT/UPDATE (`movimentacoes` é tabela quente), e a auditoria Wave 4 já reportou 16 índices "unused" — não vamos engrossar a lista sem evidência.

**Reserva técnica**: caso `EXPLAIN ANALYZE` no Bloco 5.2 mostre seq scan em alguma agregação não prevista, abriremos uma migration **011_add_index_*.py** específica e justificada — fora do escopo planejado mas dentro da wave.

### 3.3 Views e materialized views

**Decisão: não criar nenhuma.**

Argumentação contra matview no momento:
1. **Volumetria não justifica** (< 1 MB total). REFRESH de matview tocaria disco e seria mais caro que a query direta.
2. **Cache TTL no app** (§4.4) entrega o mesmo benefício sem o custo operacional de manter view sincronizada.
3. **Realtime já invalida** o cache quando uma prova muda — matview não consegue invalidação reativa sem trigger + REFRESH CONCURRENTLY (custo adicional alto).
4. **Free tier 500 MB**: matview duplicaria dados (custo de armazenamento) sem ganho de performance.

Argumentação contra view normal:
1. View normal **não cacheia** — apenas encapsula SQL. O ganho seria estético (legibilidade no `reports.py`), mas o custo é dispersar a lógica entre o repositório e o banco. **Lógica de agregação fica em Python/SQLAlchemy**, alinhada com o resto do projeto.

**Reavaliar em Wave 7+** caso volume passe de ~100k linhas em `movimentacoes`.

### 3.4 RLS — auditoria de cobertura

Inspeção via `pg_policies`:

| Tabela | SELECT policy cobre admin? | Wave 5 precisa? |
|---|---|---|
| `provas_digitais` | ✅ `is_admin=true` ramo do OR | ✅ não precisa adicionar |
| `movimentacoes` | ✅ `is_admin=true` ramo do OR | ✅ não precisa adicionar |
| `usuarios` | ✅ `is_admin=true` ramo do OR | ✅ não precisa adicionar |
| `configuracoes_sistema` | ✅ `is_admin=true` | ✅ não precisa adicionar |
| `audit_logs` | ✅ `is_admin=true` only | ✅ não precisa adicionar |

**Defesa em profundidade**: backend roda com `service_role` que bypassa RLS. RBAC efetivo é via `get_admin_user` dependency. RLS continua ativo como segunda camada se algum dia o backend mudar para usar token do usuário.

**Conclusão: zero alteração em `backend/migrations/rls/*.sql`.**

### 3.5 Extensões Postgres

`pg_stat_statements` já instalada — usada para `EXPLAIN`. `pg_trgm` e `unaccent` disponíveis mas **não serão instaladas nesta wave**: a busca textual `q` da Wave 5 é prefix/contains simples (`ILIKE '%q%'`) sobre 3 colunas (nome, cliente, nro_requerimento) com volumes que comportam seq scan. Reavaliar em Wave 7+ se busca for percebida como lenta.

---

## 4. Contratos de API

### 4.1 Roteamento

**Prefixo:** `/api/v1/reports/*`. Router novo em `backend/app/api/v1/reports.py`. Registrado em `app/main.py` com `app.include_router(reports.router)`.

### 4.2 Endpoint único discriminado por `scope`

```
GET /api/v1/reports?scope={geral|3studio|vendedores|clicheria}
                   &from={ISO-8601}&to={ISO-8601}
                   &q={busca}
                   &vendedor_id={uuid}
                   &rota={PADRAO|DIRETA}
                   &status={status_prova_enum}
```

**Parâmetros e validação Pydantic v2:**

```python
class ReportFilters(BaseModel):
    scope: Literal["geral", "3studio", "vendedores", "clicheria"]
    from_: datetime | None = Field(default=None, alias="from")
    to: datetime | None = None
    q: str | None = Field(default=None, max_length=200)
    vendedor_id: uuid.UUID | None = None
    rota: RotaEnum | None = None
    status: StatusProvaEnum | None = None

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    @model_validator(mode="after")
    def _defaults_and_invariants(self):
        # Default: últimos 30 dias se ausentes
        if self.to is None: object.__setattr__(self, "to", datetime.now(UTC))
        if self.from_ is None:
            object.__setattr__(self, "from_", self.to - timedelta(days=30))
        if self.from_ >= self.to:
            raise ValueError("from must be earlier than to")
        if (self.to - self.from_) > timedelta(days=366):
            raise ValueError("date range must be at most 366 days")
        return self
```

**Resposta — discriminated union (Pydantic v2 `Field(discriminator="scope")`):**

```python
class ReportResponseGeral(BaseModel):
    scope: Literal["geral"]
    periodo: PeriodoMeta            # from, to, total_dias
    indicadores: IndicadoresGeral   # ver abaixo
    serie_temporal: list[PontoSerie]
    distribuicao_status: list[DistStatus]
    distribuicao_rota: list[DistRota]
    atualizado_em: datetime

class ReportResponse3Studio(BaseModel):
    scope: Literal["3studio"]
    periodo: PeriodoMeta
    indicadores: Indicadores3Studio
    cancelamentos_top: list[CancelamentoTop]
    atualizado_em: datetime

class ReportResponseVendedores(BaseModel):
    scope: Literal["vendedores"]
    periodo: PeriodoMeta
    ranking: list[VendedorMetrica]
    distribuicao_localizacao: DistLocalizacao
    atrasadas_em_poder: list[VendedorAtrasoAtual]
    atualizado_em: datetime

class ReportResponseClicheria(BaseModel):
    scope: Literal["clicheria"]
    periodo: PeriodoMeta
    indicadores: IndicadoresClicheria
    em_transito_atual: int
    atualizado_em: datetime

ReportResponse = Annotated[
    ReportResponseGeral | ReportResponse3Studio | ReportResponseVendedores | ReportResponseClicheria,
    Field(discriminator="scope"),
]
```

**Indicadores (alinhados com briefing §4):**

- `IndicadoresGeral`: `total_provas`, `tempo_medio_ciclo_horas`, `tempo_mediano_ciclo_horas`, `tempo_medio_aprovacao_horas`, `taxa_reprovacao` (sobre **ciclos**, não provas — ADR a registrar), `qtd_atrasadas`.
- `Indicadores3Studio`: `provas_criadas`, `media_diaria_criacao`, `reinicios_de_ciclo`, `devolvidas_motorista`, `reprovadas_aguardando_acao`, `cancelamentos`, `tempo_medio_criacao_ate_primeira_mov_horas`.
- `VendedorMetrica`: `vendedor_id`, `vendedor_nome`, `localizacao`, `volume`, `taxa_aprovacao`, `taxa_reprovacao`, `tempo_medio_retirada_a_decisao_horas`, `provas_atrasadas_em_poder`.
- `IndicadoresClicheria`: `recebidas_no_periodo`, `tempo_medio_aguardando_recebimento_horas`, `por_origem_rota` (PADRAO vs DIRETA).

### 4.3 Endpoint de exportação CSV

```
GET /api/v1/reports/export?scope=...&from=...&to=...&q=...&format=csv
                          &dataset={summary|by-seller|overdue|proofs}
```

- `StreamingResponse` com `media_type="text/csv; charset=utf-8"`.
- `Content-Disposition: attachment; filename="relatorio_{scope}_{from}_{to}.csv"`.
- **UTF-8 BOM** prefixo (`\ufeff`) para Excel abrir acentos sem mojibake.
- **Cursor server-side** via `db.stream(stmt, execution_options={"yield_per": 500})` em datasets longos (`overdue`, `proofs`). Schema `summary` cabe em uma única página; `by-seller` é limitado a top-N (default 50, max 200).
- **Truncamento hard em 100.000 linhas** com linha final `# TRUNCATED` para evitar gerar arquivo de centenas de MB.
- **Sem cache** — exportação é sempre fresca. Auditoria registra cada export em `audit_logs` (`acao="REPORT_EXPORTED"`, `detalhes_json={scope, filtros, dataset, linhas}`).

### 4.4 Estratégia de cache — coração do "minimizar queries"

A combinação a seguir é o que faz a Wave 5 entregar **mínimo de queries** sem comprometer frescor.

**Camada 1 — HTTP cache no cliente (resposta JSON):**
- Backend emite `ETag: "<sha256(payload)>"` e `Cache-Control: private, max-age=30, stale-while-revalidate=60`.
- Cliente envia `If-None-Match: "<etag>"` em refetch.
- Quando ETag bate, backend devolve **304 Not Modified com body vazio** — zero bytes adicionais ao cliente, mas o backend ainda computa o ETag (precisa rodar a query para saber se mudou). **Só vale a pena se conjugado com camada 2.**

**Camada 2 — Cache in-memory no backend (chave determinística):**
- Estrutura `dict[str, tuple[float, ReportResponse, str]]` (timestamp, payload, etag) — mesma família do cache do dashboard ([provas.py:_dashboard_cache_*](../../backend/app/api/v1/provas.py)).
- Chave: `sha256(scope + filtros normalizados em JSON canônico)` — filtros idênticos colidem.
- TTL: **60 segundos** por chave (Mario aprovou 5s no Dashboard porque é tempo real; Wave 5 é analítica, 60s é seguro). Ajustável via env var `REPORTS_CACHE_TTL_SECONDS`.
- Em cache hit: backend devolve resposta com mesmo ETag → se `If-None-Match` bater, **304 sem tocar DB nem reserialização**.
- Cache **por worker uvicorn** (in-memory). Em volume atual, 1–2 workers, irrelevante. Se escalar para N workers, worst-case = N queries cold-start; aceitável.

**Camada 3 — Realtime invalida o cache do frontend:**
- Frontend já assina `postgres_changes` em `provas_digitais` (Wave 4). Wave 5 acrescenta um listener no hook `useReport()` que, ao receber evento, **invalida ETag local** e dispara refetch debounced (2s).
- Backend não invalida sua cache via Realtime — deixa o TTL expirar naturalmente. O `If-None-Match` resolve: o cliente pode ter ETag obsoleto por até 60s, mas o resultado é igual ao do cache (até o TTL expirar e a query rodar de novo). Cenário pior: latência de 60s entre uma mudança de status e o relatório refletir. **Aceitável para camada analítica.**

**Camada 4 — SQLAlchemy compiled cache + prepared statements:**
- SQLAlchemy 2.0 compila cada query 1x e reusa. Já está habilitado por padrão. Para queries da Wave 5 com filtros dinâmicos (`from`, `to`, `q`), os parâmetros viram bind params — compilação cacheada vale para todas as variantes.
- Reduz o **planning time** (que vimos ser dominante em volume baixo) de ~0.85ms para ~0.05ms após primeira execução.

**Cenário concreto — 30 usuários no painel de relatórios:**
| Sem cache | Com Wave 5 |
|---|---|
| 30 × 1 query a cada navegação = 30 queries | Cold start: 1 query. Próximos 29 usuários em <60s: 0 queries (cache hit + 304). |
| 30 × 1 query a cada polling 30s = 30 queries / 30s | TTL 60s: 1 query / 60s, 29 ETag matches. |
| Refetch após mudança Realtime: 30 queries | 1 query global (depois do TTL expirar). Dentro do TTL, ETag ainda é válido se conteúdo não mudou. |

Estimado: **redução de 25–30x nas queries** vs. implementação ingênua, com latência percebida idêntica.

### 4.5 RBAC

- Todos os endpoints `/api/v1/reports/*` dependem de `get_admin_user`. Vendedores, motoristas, clicheria recebem `403 Forbidden` na borda.
- RLS continua ativo como defesa em profundidade.
- Nenhum endpoint de relatório vaza `vendedor_id` específico se quem chamar não for admin (o endpoint nem responde).

### 4.6 Performance — alvo

| Métrica | Alvo |
|---|---|
| Resposta JSON (volumetria atual, < 14 provas) | < 50ms p99 |
| Resposta JSON (volumetria projetada, 3000 provas / 30000 movimentações) | < 1s p95 |
| Resposta 304 Not Modified | < 10ms |
| Export CSV `proofs` 10k linhas | < 5s, memória < 50MB |
| Export CSV truncado 100k | < 30s |

`EXPLAIN ANALYZE` exigido em cada query nova **antes de declarar bloco pronto**. Resultado anexo no commit de cada bloco backend.

---

## 5. Frontend

### 5.1 Rota nova

`/relatorios` em `frontend/src/app/(dashboard)/relatorios/page.tsx`. **Acesso restrito a admin**: middleware existente já redireciona usuários não-autenticados; vendedores autenticados serão tratados na própria página (mostra mensagem "Acesso restrito" se a API responder 403). Se quiser proteção por middleware, é preciso popular `is_admin` no JWT — fora do escopo, mantém-se 403 da API.

### 5.2 Componentes

```
relatorios/
├── page.tsx                  # orquestrador + Suspense boundary
├── relatorios.module.css     # tokens reaproveitados
├── ScopeSelector.tsx         # tabs/segmented control com 4 scopes
├── DateRangeFilter.tsx       # 2 inputs date nativos + presets (hoje, 7d, 30d, custom)
├── SearchInput.tsx           # debounce 300ms
├── ExportButton.tsx          # disparra /reports/export (download blob)
├── perspectivas/
│   ├── ReportGeral.tsx       # KPIs + série temporal + distribuições
│   ├── Report3Studio.tsx     # KPIs + top cancelamentos
│   ├── ReportVendedores.tsx  # ranking + tabela + atrasadas em poder
│   └── ReportClicheria.tsx   # KPIs + em-trânsito
└── shared/
    ├── KpiCard.tsx           # card numérico reutilizável
    ├── PeriodoBadge.tsx
    └── EmptyState.tsx
```

**Renderização condicional** via match exaustivo no `scope` (TypeScript discriminated union — sem `if/else` sobre campos opcionais):

```tsx
function PerspectivaRenderer({ data }: { data: ReportResponse }) {
  switch (data.scope) {
    case "geral": return <ReportGeral data={data} />;
    case "3studio": return <Report3Studio data={data} />;
    case "vendedores": return <ReportVendedores data={data} />;
    case "clicheria": return <ReportClicheria data={data} />;
  }
}
```

### 5.3 Hooks

**Hook único `useReport(filters: ReportFilters)`** — não 4 hooks separados. Razão: o cliente faz 1 request por (scope+filtros), e o cache HTTP/ETag é compartilhado. Hook gerencia:
- Fetch com `If-None-Match` se houver ETag local.
- Cache local em `useRef<Map<string, {etag, data}>>` por chave (mesma normalização do backend).
- Subscription a `postgres_changes` em `provas_digitais` → invalidar ETag local + refetch debounced 2s.
- Race protection (mounted ref).
- Estados explícitos: `loading | refreshing | empty | error | success`.

Hook acessório `useReportExport()` para o botão CSV — fetch direto + `response.blob()` + `URL.createObjectURL` + cleanup. **Não usa apiFetch** (binário, igual `/etiqueta.pdf`).

### 5.4 Gráficos

Decisão: **sem reinstalar Recharts agora**. Para a série temporal e distribuições da `ReportGeral`, vou usar **SVG inline com Framer Motion** (já no bundle):
- BarChart simples em SVG (rect + text + grid). ~150 linhas de componente. Sem dependência adicional.
- Animação de entrada via Framer Motion (já presente).
- Se Mario preferir Recharts, autorizar reinstalação no checkpoint do Bloco 5.5 — bundle aumenta ~100kB.

### 5.5 URL persistida

Filtros codificados na URL (`?scope=...&from=...&to=...`) via `useSearchParams` + `useRouter`. Permite deep-link, bookmark, voltar/avançar do browser. ScopeSelector troca a URL sem perder filtros temporais.

### 5.6 Estados explícitos

Cada perspectiva tem:
- **Loading**: skeleton dos KPIs (sem placeholder genérico).
- **Empty**: copy específico ("Nenhuma prova no período selecionado").
- **Error**: card com retry button + mensagem do backend.
- **Success**: render normal.

### 5.7 Componente 17 — atalhos globais (detalhe)

`frontend/src/hooks/useGlobalShortcuts.ts`:
- Listener `keydown` em `document` (registrado no layout).
- State machine de 2 keystrokes com timeout 1.5s (estilo GitHub).
- Mapping: `g s` → push `/escanear`, `g p` → push `/provas`, `g r` → push `/relatorios`, `?` → abre modal help.
- Ignorar quando target é `<input>`, `<textarea>`, `[contenteditable]`.
- Filtragem por `is_admin`: `g r` só para admin (dispatch só registra se permission OK).

`frontend/src/components/KeyboardShortcutsHelp.tsx`:
- Modal com lista dos atalhos disponíveis para o usuário logado.
- Reaproveita `useFocusTrap` da Wave 3.
- Fechamento: Escape, click fora, click no botão close.

Documentação em CLAUDE.md (Operacional / Atalhos).

---

## 6. Storage R2

**Wave 5 não escreve no R2.** Exportação CSV é stateless (streaming direto ao cliente). Não há valor em persistir snapshots: cada export é um snapshot fresh, e armazenar duplica conteúdo de baixo valor (lifecycle não traz benefício mensurável). Confirmado.

Bucket `rastreio-provas-artes` permanece intocado.

---

## 7. Plano de testes

### 7.1 Camada 1 — Unitários (≥ 80%)

**Alvo:** funções de agregação isoladas em `app/services/report_*.py`.

Casos críticos:
- `compute_tempo_medio_aprovacao(movs)` — mocks com 0, 1, N movimentações; provas com ciclos reiniciados (RN-006).
- `compute_taxa_reprovacao_ciclos(movs)` — divide reprovações por ciclos (não por provas). Casos de borda: 0 ciclos (denominador zero → retorna 0.0); ciclos sem reprovação; ciclos só com reprovação.
- `compute_provas_atrasadas(provas, ultima_mov_por_prova, tempo_atraso_horas)` — mock com datas que cruzam fim de semana; 0 atrasadas; todas atrasadas.
- `compute_distribuicao_rota(provas)` — provas com `rota=NULL` (pré-aprovação).
- `normalize_filters(filters) -> str` — filtros idênticos produzem string idêntica (chave de cache estável).
- `validate_report_filters` — Pydantic rejeita: scope inválido, from > to, range > 366 dias, q > 200 chars, vendedor_id malformado.

**Ferramenta:** pytest + pytest-asyncio. Sem banco real (mocks de repositório).

### 7.2 Camada 2 — Integração (100% endpoints críticos)

Banco PostgreSQL real (Supabase staging) com seed determinístico via `scripts/seed_reports_fixture.py` (recuperar do commit antigo `5db44bb` — script é reutilizável).

Casos:
- `GET /api/v1/reports?scope=geral` retorna shape correto, indicadores corretos, total_provas bate com fixture.
- `GET /api/v1/reports?scope=vendedores` retorna ranking ordenado por volume, taxa_reprovacao calculada sobre ciclos.
- `GET /api/v1/reports?scope=3studio` conta reinícios de ciclo (movs com `status_anterior=REPROVADA, status_novo=CRIADA`).
- `GET /api/v1/reports?scope=clicheria` agrega corretamente PADRAO vs DIRETA.
- RBAC: vendedor recebe 403, motorista 403, clicheria 403, admin 200.
- ETag idempotente: mesmo request 2x produz mesmo ETag.
- `If-None-Match` correto: 304 com body vazio, headers preservados.
- Cache TTL: 2 requests dentro de 60s atingem cache (verifica via `Server-Timing` header customizado em modo debug).
- `GET /api/v1/reports/export?dataset=overdue&format=csv` retorna 200, `Content-Type` correto, BOM UTF-8 presente, parser CSV consegue ler.
- Truncamento: seed com 100.001 movs → CSV termina com `# TRUNCATED`.
- Auditoria: cada `/export` insere linha em `audit_logs` com `acao="REPORT_EXPORTED"`.
- Filtros combinados: `from + to + q + vendedor_id` produzem subset coerente.

**Ferramenta:** pytest + httpx AsyncClient + DB Postgres real.

### 7.3 Camada 3 — E2E (Playwright)

Cenários happy-path (manuais antes do deploy):
1. Login como admin → navega para `/relatorios` → URL contém `?scope=geral&from=...&to=...`.
2. Troca scope → KPIs e gráficos mudam, URL atualiza.
3. Aplica filtro de busca → debounce 300ms, lista atualiza.
4. Exportar CSV → file download confirmado.
5. Atalho `g r` em qualquer rota autenticada → push para `/relatorios`.
6. Atalho `?` → abre modal de help, Escape fecha.

### 7.4 Verificação de equivalência semântica Dashboard ↔ Relatórios

Briefing §8 marca como blocker o drift entre Dashboard e Relatórios. Adicionar teste de integração:

```python
async def test_dashboard_e_relatorios_concordam_em_atrasadas(...):
    # Seed com N provas, M atrasadas
    dashboard = await client.get("/api/v1/provas/dashboard")
    geral = await client.get("/api/v1/reports?scope=geral&from=...&to=...")
    assert dashboard.json()["contadores"]["atrasadas"] == geral.json()["indicadores"]["qtd_atrasadas"]
```

Esse teste blinda contra futura regressão se alguém alterar o cálculo num dos lados.

---

## 8. Riscos & RNF

| # | Risco | Mitigação |
|---|---|---|
| R1 | **Free tier Supabase 500MB** | Volumetria atual <1MB. Wave 5 não escreve. Sem risco imediato. Wave 7+ revisa retenção de `audit_logs` e `movimentacoes`. |
| R2 | **Plan de query degradar com volume** | `EXPLAIN ANALYZE` exigido por bloco. Reserva técnica para criar índices reativos (migration 011) se aparecer seq scan inesperado. |
| R3 | **Janela temporal default ausente** | Pydantic preenche default 30 dias. Limite hard 366 dias rejeita "tudo desde o início". |
| R4 | **Timezone** | Datas vêm do front em fuso local; backend opera em UTC; conversão na borda Pydantic. ADR-100 a documentar a estratégia. |
| R5 | **Ciclos reiniciados (RN-006)** | Taxa de reprovação calculada **sobre ciclos**, não provas. ADR-101 a documentar a decisão de modelagem. |
| R6 | **CSV com acentos** | UTF-8 com BOM. Test de regressão lê o arquivo via `csv.reader` em Python e por `pandas` (caso disponível em CI). |
| R7 | **Drift Dashboard ↔ Relatórios** | Teste de equivalência §7.4. ADR-099 documenta horas corridas adotadas em ambos. |
| R8 | **Cache stale após mudança de Configuração** | Cache do `tempo_atraso_horas_uteis` invalidado quando o admin faz PATCH em `/configuracoes/{chave}` (acionar bump de cache key global do reports). Edge case raro. |
| R9 | **Componente 17 keyboard shortcuts conflitar com browser shortcuts** | `g+letter` é seguro (não colide com Ctrl/Cmd/Alt). Modal `?` documentado. |
| R10 | **Recharts removido** | Decisão Bloco 5.5: SVG + Framer Motion, sem dep nova. Reavaliar se gráfico ficar pobre. |

---

## 9. Ordem de implementação em blocos

Espelhando o padrão das Waves anteriores, com gates explícitos.

### Bloco 5.0 — Recovery e fundação (sem código novo de domínio)
- Restaurar `backend/migrations/versions/010_add_indexes_for_wave5_reports.py` do commit `5db44bb`.
- Atualizar [docs/db/schema.sql](../db/schema.sql) (adicionar os 2 índices na seção 5).
- Atualizar `descricao` da chave `tempo_atraso_horas_uteis` em `configuracoes_sistema` via migration **011_clarify_tempo_atraso_descricao.py** (ADR-099 — horas corridas).
- ADR-095 (recovery), ADR-099 (horas corridas Wave 5).
- `alembic upgrade head` em local dev → migration 010 já aplicada (no-op via IF NOT EXISTS), migration 011 executa o UPDATE da descricao.
- Smoke: `alembic_version` em dev = 011.
- **Commit:** "chore(wave5): recover migration 010 + clarify atraso config (RN-008 desvio)".

### Bloco 5.1 — Backend domínio/serviço (puro)
- `app/services/report_filters.py` — Pydantic `ReportFilters` + normalização determinística para chave de cache.
- `app/services/report_metrics.py` — funções puras: `compute_tempo_medio_aprovacao`, `compute_taxa_reprovacao_ciclos`, `compute_distribuicao_rota`, etc. Mockáveis.
- `app/services/report_cache.py` — wrapper TTL 60s sobre `dict` (mesma família do cache do dashboard, generalizado).
- `app/services/report_etag.py` — gera ETag determinístico via SHA-256 do payload.
- `app/domain/schemas/report.py` — discriminated union completa (4 perspectivas).
- 60+ testes unit cobrindo cada função.
- **Commit:** "feat(wave5/5.1): report metrics + filters + cache + etag (services puros)".

### Bloco 5.2 — Backend API (endpoint único + CSV)
- `app/api/v1/reports.py` — handler único `/reports` com switch por scope.
- `/reports/export` — StreamingResponse, BOM UTF-8, truncamento.
- Audit logging em cada acesso.
- ETag/304 + Cache-Control.
- 30+ testes integração com seed determinístico.
- `EXPLAIN ANALYZE` rodado em cada query, anexado ao commit.
- **Commit:** "feat(wave5/5.2): /api/v1/reports — endpoint discriminado + CSV streaming + ETag".

### Bloco 5.3 — Frontend rota + hooks
- `lib/types/report.ts` — espelho TS dos schemas.
- `hooks/useReport.ts` (único, com cache local + ETag + Realtime invalidation).
- `hooks/useReportExport.ts` (download blob).
- Rota `/relatorios` página + ScopeSelector + DateRangeFilter + SearchInput.
- URL-persistence dos filtros.
- TypeScript estrito, zero `any`.
- **Commit:** "feat(wave5/5.3): /relatorios route + hooks + filtros".

### Bloco 5.4 — Frontend perspectivas
- `ReportGeral`, `Report3Studio`, `ReportVendedores`, `ReportClicheria`.
- KpiCard, PeriodoBadge, EmptyState compartilhados.
- Gráficos SVG + Framer Motion.
- Estados loading/empty/error explícitos.
- **Commit:** "feat(wave5/5.4): 4 perspectivas tipadas com SVG charts".

### Bloco 5.5 — Componente 17 (atalhos)
- `useGlobalShortcuts` hook + `KeyboardShortcutsHelp` modal.
- Registro no `(dashboard)/layout.tsx` (1 import + 1 hook call).
- 3º card "Acessar Relatórios" no dashboard (ÚNICA edição em arquivo da Wave 4 — autorizada pelo escopo do Componente 17).
- Documentação CLAUDE.md.
- ADR-098 (atalhos globais).
- **Commit:** "feat(wave5/5.5): Componente 17 — atalhos globais + 3º card no dashboard".

### Bloco 5.6 — E2E + closeout
- Cenários Playwright (manuais).
- Teste de equivalência Dashboard ↔ Relatórios (§7.4).
- Atualizar CHANGELOG.md, DECISIONS.md (ADRs 095, 098, 099, 100, 101).
- `docs/waves/WAVE5_CLOSEOUT.md` com DoD check, métricas, lessons.
- CLAUDE.md status "✅ COMPLETA".
- **Commit:** "docs(wave5): closeout + ADRs + CHANGELOG".

---

## 10. ADRs a registrar (ordem de aparição)

| ADR | Quando | Tema |
|---|---|---|
| **ADR-095** | Bloco 5.0 | Recovery da migration 010 órfã + reconciliação de drift |
| **ADR-096** | Bloco 5.1 | Endpoint único discriminado vs. 4–5 endpoints separados (vs. abordagem antiga commit 5db44bb) |
| **ADR-097** | Bloco 5.2 | HTTP ETag + cache server-side TTL 60s + Realtime invalidation no front |
| **ADR-098** | Bloco 5.5 | Atalhos globais por teclado (Componente 17) |
| **ADR-099** | Bloco 5.0 | RN-008: Wave 5 mantém horas corridas alinhada à Wave 4 (desvio explícito do RN-008 literal — opção B aprovada por Mario 2026-04-27) |
| **ADR-100** | Bloco 5.2 | Estratégia de timezone (UTC no banco, conversão na borda Pydantic) |
| **ADR-101** | Bloco 5.1 | Taxa de reprovação calculada sobre ciclos (RN-006), não provas |

---

## 11. Sumário das decisões pedindo GO

| # | Decisão | Proposta |
|---|---|---|
| 1 | Migration 010 recovery | Copiar literalmente do commit `5db44bb` (idempotente, já em produção) |
| 2 | Horas corridas (RN-008) | Manter (opção B Mario), atualizar `descricao` da config + ADR-099 |
| 3 | Componente 17 — escopo | (a) Adicionar 3º card "Acessar Relatórios" no dashboard + (b) atalhos de teclado globais com modal de help |
| 4 | Endpoint único discriminado | Sim — rejeita os 5 endpoints separados da implementação antiga |
| 5 | Cache | TTL 60s in-memory + ETag/304 + Realtime-invalidates-front |
| 6 | Sem matview, sem view | Justificado (§3.3) — volume não compensa |
| 7 | Sem novo índice nesta wave | Os 2 índices da migration 010 (já em produção) cobrem tudo |
| 8 | Sem Recharts agora | SVG + Framer Motion, reavaliar caso o gráfico fique pobre |
| 9 | Taxa de reprovação sobre ciclos | RN-006 obriga; ADR-101 |
| 10 | Timezone UTC + conversão na borda | ADR-100 |
| 11 | Plano de testes | ≥ 80% unit, 100% integ críticos, 6 cenários E2E manuais, 1 teste de equivalência cross-wave |

---

## 12. Pergunta de GO

Mario, este plano:
- **Cumpre RF-013, RF-015, RF-016, US-014, RN-006, RN-008** (com desvio documentado), **RNF-001** (< 1s p95), **RNF-005** (audit), **RNF-006** (responsivo), **RNF-009** (manutenibilidade).
- **Minimiza queries** via cache em 4 camadas (HTTP, app, Realtime invalidation, prepared statements).
- **Zero toque** em Waves 0–4 exceto pelas exceções autorizadas (link sidebar + 3º card dashboard).
- **Bloqueado em escrita de código** até seu **GO**.

**Posso prosseguir para o Bloco 5.0 (recovery da migration 010 + ADRs 095/099) seguindo este plano?**

Se houver ajustes (preferência por matview, autorização Recharts, mudança de TTL, ou outra arquitetura para os atalhos), me orienta antes do GO.
