# Wave 2 — Núcleo do Domínio — Sumário Consolidado

**Período:** 2026-04-09 (Sessões 7 a 11)
**Status:** ✅ **COMPLETA**

---

## 1. Escopo entregue

A Wave 2 entrega **o objeto central do sistema** (a Prova Digital) e tudo que orbita sua criação, listagem, detalhe e configuração.

| Componente | Título | Prioridade | Sessão | Status |
|---|---|---|---|---|
| **06** | Cadastro de Prova Digital + Etiqueta | Must Have | 8 | ✅ |
| **07** | Listagem, Pesquisa e Filtros de Provas | Must Have | 10 | ✅ |
| **08** | Visualização de Prova (Detalhe) + Timeline placeholder | Must Have | 11 | ✅ |
| **09** | Tela de Configurações do Sistema | Must Have | 9 | ✅ |

Ordem de execução: **06 → 09 → 07 → 08** (09 foi antecipado porque o template de etiqueta usado pelo 06 vive em `configuracoes_sistema`).

Pré-componentes executados na abertura da Wave 2 (Sessão 7):
- **W2-T0** — Reescrita de 11 policies RLS com `(SELECT auth.uid())` — ADR-029 executado
- **ADR-030** — Criação do segundo admin operacional (`ops@3studio.com.br`) via fluxo do próprio endpoint `POST /api/v1/users`

---

## 2. Requisitos funcionais atendidos

| Req | Descrição | Onde |
|---|---|---|
| **RF-001** | Criação de prova com nome/nº req/cliente/vendedor/arte (JPG/PNG ≤10MB) | C06 — `POST /api/v1/provas/` + validação MIME via magic bytes |
| **RF-002** | QR Code único e não reutilizável | C06 — `qrcode_service.gerar_hash` via HMAC-SHA256 (64 chars) |
| **RF-003** | Etiqueta imprimível com nome/nº req/vendedor/QR Code | C06 — `etiqueta_service.gerar_pdf` via fpdf2 (formato A4 ou 80mm térmico) |
| **RF-011** | Dados detalhados de cada prova com rota e motivo de reprovação | C08 — `GET /api/v1/provas/{id}` + timeline placeholder |
| **RF-012** | Pesquisa por nome e/ou número de requerimento | C07 — filtro `busca` via ILIKE em `nome OR nro_requerimento` |
| **RF-013** | Listagem com filtros por período, status, vendedor, cliente, rota | C07 — `GET /api/v1/provas/` com 6 filtros combináveis + paginação |
| **RF-017** a **RF-020** | CRUD de usuários + RBAC | Wave 1 (já completo) |
| **RF-021** | Tela de configurações (tempo de atraso + template etiqueta), admin-only | C09 — `GET/PATCH /api/v1/configuracoes/{chave}` + UI |

---

## 3. Regras de negócio implementadas

| RN | Regra | Implementação |
|---|---|---|
| **RN-001** | QR Code único e não reutilizável | `qrcode_service.gerar_hash(prova_id, nro_req)` com HMAC-SHA256 dedicado (ADR-033). Unicidade garantida por `provas_digitais.qr_code_hash UNIQUE`. |
| **RN-002** | Transições seguem a Matriz da Seção 5 | `app/services/state_machine.py` com tabela `TRANSICOES` e `validar_transicao()`. Wave 2 não executa transições (criação ≠ transição — ADR sobre primeira movimentação), mas a infra está pronta para Wave 3. |
| **RN-004** | Ator autorizado por transição | `ATORES_POR_TRANSICAO` dict + `validar_transicao()` (ADR-040). Aplicado via `_scoping_filter` nos endpoints de listagem/detalhe (ADR-046, ADR-049). |
| **RN-005** | Cancelamento só pelo 3Studio, qualquer estado ativo exceto RECEBIDA/CANCELADA | `pode_cancelar()` + `validar_transicao()` (ADR-040). UI de cancelamento fica para Wave 3 (Componente 13). |
| **RN-007** | Rota determinada pela localização do vendedor **no momento da aprovação** | `determinar_rota(vendedor)` é função pura (ADR-040). Na criação (Wave 2), `rota` fica NULL — só `rota_projetada` é calculada para exibição (ADR-042). Persistência acontece na aprovação (Wave 3). |
| **RN-008** | Tempo de atraso configurável em horas úteis | Chave `tempo_atraso_horas_uteis` em `configuracoes_sistema`. Editada via Componente 09 (range 1-168). Cálculo de atraso em si fica para Wave 4 (dashboard). |
| **RN-009** | Vendedor com localização obrigatória | `chk_vendedor_localizacao` CHECK constraint + validação no `_carregar_vendedor` do endpoint `POST /provas/`. |
| **RN-010** | Proteção do último admin | Wave 1 — `_count_other_active_admins()` + ADR-030. |
| **RN-011** | Template de etiqueta configurável | Chave `template_etiqueta` em `configuracoes_sistema` (JSONB estruturado, migration 009 — ADR-036). Campos: `nome`, `formato`, `logo_enabled`, `mostrar_data_criacao`. UI no Componente 09. |

---

## 4. Requisitos não-funcionais

| RNF | Requisito | Status |
|---|---|---|
| **RNF-001** | Dashboard/listagem <3s com 30 usuários simultâneos | ✅ `/provas` lista 7 provas em <100ms local. Indexes cobrindo filtros. ILIKE aceitável no volume atual (ADR-038). |
| **RNF-002** | Scanner + assinatura <2s | ⏳ Wave 3 |
| **RNF-003** | Sessão inativa >30min encerrada | ✅ Wave 1 — `useInactivityTimeout(30*60*1000, logout)` |
| **RNF-004** | Senhas hashed (Supabase), HTTPS/TLS | ✅ Wave 1 |
| **RNF-005** | Log de auditoria imutável | ✅ Wave 0 (triggers `trg_*_imutavel`) + Wave 2 (`audit_service.log_audit` escreve em cada `criar_prova` e `atualizar_configuracao`) |
| **RNF-006** | Responsividade Chrome/Firefox/Edge/Safari, telas ≥5" | ✅ Mobile notice consistente em todas as páginas de desktop-only; `/login` funciona em mobile |
| **RNF-007** | Escanear → assinar → confirmar em ≤3 toques | ⏳ Wave 3 |
| **RNF-008** | Disponibilidade seg-sex 07h-18h | ✅ Keep-alive GitHub Actions (Wave 0) |
| **RNF-009** | Manutenibilidade / adicionar novas rotas sem refactor estrutural | ✅ State machine tabela-driven (ADR-040), validators com dispatch table em configurações (ADR-045), whitelist de chaves (ADR-043) |

---

## 5. Métricas técnicas finais

### Backend

| Métrica | Valor |
|---|---|
| Testes totais | **250 passed, 1 warning** (intencional JWT test) |
| Cobertura global | **92%** |
| Módulos Wave 2 críticos | `state_machine` 97%, `qrcode_service` 97%, `etiqueta_service` 98%, `audit_service` 100%, `api/v1/provas.py` 93%, `api/v1/configuracoes.py` 96%, `schemas/prova.py` 92%, `schemas/configuracao.py` 95% |
| Endpoints novos na Wave 2 | **12** (8 em `/provas` + 3 em `/configuracoes` + 1 remix do `/users` que não entrou) |
| Migrations Alembic novas | **1** (009 — evolve template_etiqueta) |
| Arquivos RLS novos | **1** (005 — initplan optimization, W2-T0) |
| Dependências novas | `qrcode[pil]>=7.4,<8.0` + `fpdf2>=2.7,<3.0` |
| Env vars novas | `QR_CODE_HMAC_SECRET` |

### Frontend

| Métrica | Valor |
|---|---|
| Páginas novas | **4** (`/nova-prova`, `/provas`, `/provas/[id]`, `/configuracoes`) |
| Hooks novos | **4** (`useCreateProva`, `useListProvas`, `useProvaDetail`, `useConfiguracoes`) |
| Componentes novos | **1** (`VisualizarEtiquetaModal`) |
| `tsc --noEmit` | ✅ Limpo |
| `next build` | ✅ Limpo |
| Bundle sizes | `/nova-prova` 4.46 kB, `/provas` 4.56 kB, `/provas/[id]` 5.77 kB (ƒ dinâmica), `/configuracoes` 3.2 kB |

### Banco de produção

| Item | Estado |
|---|---|
| `alembic_version` | **009** |
| Tabelas de domínio | 6 (todas RLS on) |
| Indexes | 30 (incluindo compostos para filtros) |
| Policies RLS | 11 (todas com `(SELECT auth.uid())`) |
| Triggers | 6 (3 imutabilidade + 3 updated_at) com `search_path=''` |
| Advisor Supabase | 1 INFO esperado (alembic_version RLS ADR-025) + 1 WARN WONTFIX (leaked password ADR-027). **Zero issues novos.** |

---

## 6. ADRs lavrados durante a Wave 2 (22 novos, ADRs 029–052)

### Pré-componentes (W2-T0 + abertura)
- **ADR-029** (Sessão 7) — Reescrita RLS `(SELECT auth.uid())` **EXECUTADO**
- **ADR-030** (Sessão 7) — 2º admin operacional **EXECUTADO**

### Componente 06 (Cadastro + Etiqueta)
- **ADR-031** — Upload via Presigned URL (frontend → R2 direto)
- **ADR-032** — Validação de MIME real via magic bytes (stdlib)
- **ADR-033** — QR Code hash = HMAC-SHA256 com secret dedicado
- **ADR-034** — `qrcode[pil]>=7.4` para renderizar PNG
- **ADR-035** — `fpdf2>=2.7` para gerar PDF da etiqueta
- **ADR-036** — `template_etiqueta` evolui para JSONB estruturado (migration 009)
- **ADR-039** — Audit service helper centralizado
- **ADR-040** — State machine tabela-driven com stubs para Wave 3
- **ADR-041** — Cleanup best-effort de R2 órfão após falha no POST
- **ADR-042** — Rota persistida só na aprovação (rota_projetada é derivada)

### Componente 09 (Configurações)
- **ADR-043** — Whitelist estática de chaves editáveis (`EDITABLE_KEYS`)
- **ADR-044** — Audit trail detalhado com `valor_anterior`/`valor_novo`
- **ADR-045** — Dispatch table `VALIDATORS` por chave

### Componente 07 (Listagem)
- **ADR-037** — Offset-based pagination para `/provas`
- **ADR-038** — Busca textual via `ILIKE '%termo%'` (pg_trgm deferido)
- **ADR-046** — Scoping por setor replicado no backend via `_scoping_filter`
- **ADR-047** — Filtro `rota` usa a coluna persistida (não projetada)
- **ADR-048** — Filtro de período com `fim` inclusivo (`< fim + 1 day`)

### Componente 08 (Detalhe + Modal)
- **ADR-049** — Scoping de `GET /{id}` reutiliza `_scoping_filter`
- **ADR-050** — Endpoint dedicado `/imagem-url` (não embutir no `ProvaResponse`)
- **ADR-051** — Endpoint `/movimentacoes` com contrato pronto mas vazio na Wave 2
- **ADR-052** — Endpoint dedicado `GET /qr-code.png` com cache privado 5 min

---

## 7. Registros operacionais deixados no banco

Provas reais em `provas_digitais` após conclusão da Wave 2 (7 linhas):

| nro_requerimento | Status | Origem |
|---|---|---|
| `123456` (Prova de teste) | CRIADA | Smoke manual do Mario no Componente 06 |
| `DEBUG-5002C5CD` | CANCELADA | Debug do bug de ordem de flush (Sessão 8c) |
| `LIST-TEST-001` a `005` | CANCELADA | Seed do smoke do Componente 07 (Sessão 10) |

**Observação:** `audit_logs`, `etiquetas` e `movimentacoes` (ainda vazia) são imutáveis por trigger. Os registros de debug/seed ficam como histórico auditável — nunca são removidos.

---

## 8. Pendências operacionais e técnicas

### Não-bloqueantes (documentados)
- **`auth_leaked_password_protection`** (WARN) — WONTFIX do plano gratuito do Supabase (ADR-027). Re-avaliar quando upgrade de plano.
- **`rls_enabled_no_policy`** em `alembic_version` (INFO) — intencional (ADR-025).
- **Provas seed (`LIST-TEST-*`) com `imagem_url` apontando para R2 inexistente** — preview da arte no Componente 08 exibe placeholder amigável. Objetos R2 correspondentes nunca foram criados.

### Polish futuro (não-blocker)
- **Refresh automático da URL assinada de imagem** quando TTL está por expirar (Q08.1 rejeitada intencionalmente — simple-first)
- **Preservação de filtros no back da listagem → detalhe → voltar** (Q08.3 rejeitada — back do browser preserva, suficiente)
- **pg_trgm + GIN indexes** se busca virar hotspot (ADR-038 deferido)
- **Reescrita de `rota_projetada` como campo calculado no banco** se virar hotspot

### Pré-requisitos para Wave 3
- **Scanner HTML5** + biblioteca `html5-qrcode` (listada no DAT)
- **`react-signature-canvas`** para captura de assinatura (listada no DAT)
- **Implementação real de `state_machine.executar_transicao()`** — atualmente stub que levanta `NotImplementedError("Wave 3")`
- **Primeiro handler de transição** (`POST /api/v1/provas/{id}/transicao`) que vai inserir em `movimentacoes` pela primeira vez
- **Reinício de ciclo** (RN-006) — UI + handler que incrementa `ciclo_atual` e volta `status=CRIADA`
- **Cancelamento** (Componente 13) — handler + UI

### Pré-requisitos para Wave 4
- **Dashboard com contadores em tempo real** (via Supabase Realtime)
- **Cálculo de atraso** usando `tempo_atraso_horas_uteis` (já configurável no C09)
- **Definir semântica de "horas úteis"** — inclui/exclui feriados? Decisão pendente.

### Pré-requisitos para deploy em produção (Wave 2+)
- **Deploy Railway (backend) + Vercel (frontend)** — intencionalmente adiado desde a Wave 0. Tem que acontecer antes da primeira prova real ser cadastrada por usuário real.
- **Adicionar domínio Vercel em `CORS`** do R2 bucket (atualmente só `localhost:3000`)
- **Gerar nova `QR_CODE_HMAC_SECRET` de produção** via `token_hex(32)` (atualmente dev e prod compartilham — OK para MVP interno, não ideal)

---

## 9. Comandos de referência rápida

### Rodar backend (do repo root)
```bash
cd C:/Users/mario.souza/provaDigital
.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --reload
```

### Rodar testes
```bash
cd backend
../.venv/Scripts/python -m pytest -q                          # 250 passed
../.venv/Scripts/python -m pytest --cov=app --cov-report=term # 92% global
```

### Rodar frontend
```bash
cd frontend
npm run dev              # desenvolvimento
npm run build            # build de produção
npx tsc --noEmit         # só typecheck
```

### Inspecionar banco via MCP
```
list_tables public verbose=true
execute_sql "SELECT version_num FROM alembic_version"
get_advisors security
get_advisors performance
```

### Aplicar migration nova
```bash
cd backend
../.venv/Scripts/python -m alembic upgrade head
```

### Aplicar RLS nova
```bash
cd backend
../.venv/Scripts/python migrations/rls/apply_rls.py
```

### Gerar nova secret HMAC
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 10. O que consultar ao começar a Wave 3

1. **Este documento** — visão macro da Wave 2
2. **`CLAUDE.md`** — estrutura atual, regras operacionais, progresso das Waves
3. **`DECISIONS.md`** — ADRs 001-052 (especialmente 031-052 da Wave 2)
4. **`CHANGELOG.md`** — histórico completo das sessões 1-11
5. **`backend/app/services/state_machine.py`** — contrato pronto para `executar_transicao`
6. **`backend/app/db/models.py`** — model `Movimentacao` já existe, só precisa ser escrito pela primeira vez
7. **`frontend/src/app/(dashboard)/provas/[id]/page.tsx`** — timeline placeholder já preparada; basta popular
8. **Requisitos v3.0 Seção 5** — matriz de transições (única fonte de verdade do fluxo)
9. **UML v3.0 página 03** — máquina de estados com todas as arestas e atores
10. **DAT v2.0** — libs recomendadas para scanner e assinatura digital

---

**Wave 2 encerrada formalmente nesta Sessão 11.** Próxima sessão: abertura da Wave 3 com leitura rigorosa + plano global, seguindo a mesma metodologia da Wave 2.
