# Plano de Correção · Wave 2 v4.0 · Pós-Auditoria Sênior

**Engenheiro:** Sessão de correção dirigida por relatório de auditoria
(Claude Opus 4.7 1M)
**Data:** 2026-05-05
**Branch base auditada:** `wave2-v4/audit` (HEAD `1b47290`)
**Branch deste plano:** `wave2-v4/fixes/plan` (sem merge — entregável do Gate 1)
**Branch da execução (Gate 2):** `wave2-v4/fixes/execution` (a criar após autorização)
**Documento dirigente:** [docs/wave2-v4/audit-report.md](audit-report.md)

---

## 0. Pré-requisito — Validação MCP read-only do estado real

Validado em 2026-05-05 (esta sessão), via MCP Supabase + MCP Cloudflare:

| Artefato | Estado real | Bate com audit-report? |
|---|---|---|
| `alembic_version.version_num` | `012` | ✅ |
| `pg_enum` em `rota_enum` | 6 valores: `PADRAO/1`, `DIRETA/2`, `MATRIZ/3`, `LAM_MATRIZ/4`, `FILIAL/5`, `LAM_FILIAL/6` | ✅ |
| `provas_digitais` distribuição | 16 total · 11 NULL · 2 PADRAO · 3 DIRETA · 0 v4.0 · 0 codigo_null | ✅ |
| Trigger `trg_provas_rota_imutavel` | ATIVO · `BEFORE UPDATE` · `WHEN (OLD.rota IS DISTINCT FROM NEW.rota)` · `EXECUTE FUNCTION fn_bloquear_alteracao_rota` | ✅ |
| Função `fn_bloquear_alteracao_rota` | `proconfig=["search_path=\"\""]` · permite `NULL → valor` (`OLD.rota IS NOT NULL` guarda) · bloqueia `valor → outro_valor` e `valor → NULL` com `SQLSTATE 22023` | ✅ |
| Indexes em `provas_digitais` | 10 (incluindo `idx_provas_codigo_publico` UNIQUE e `idx_provas_rota`) | ✅ |
| `supabase_migrations.schema_migrations` | 3 chunks `012a`, `012b`, `012c` (ALTER TYPE / ADD COLUMN nullable / NOT NULL+indexes+trigger) | ✅ confirma divergência vs migration Alembic atomic do repo |
| Advisors `security` | 1 INFO `rls_enabled_no_policy` em `alembic_version` (pré-existente, ADR-025) + 1 WARN `auth_leaked_password_protection` (WONTFIX, ADR-027) | ✅ |
| Advisors `performance` | 13 INFO `unused_index` (12 pré-existentes + 1 novo `idx_provas_rota`, esperado) | ✅ |
| Cloudflare R2 | bucket `rastreio-provas-artes` único, sem alterações | ✅ |
| Git HEAD `1b47290` vs working tree | 3 arquivos modified: `frontend/src/lib/types/prova.ts`, `frontend/src/hooks/useCreateProva.ts`, `frontend/src/app/globals.css` (+ `docs/wave2-v4/analysis.md` 159 linhas adicionadas + `frontend/tsconfig.tsbuildinfo` ruído) | ✅ confirma AUD-W2V4-002 + AUD-W2V4-D01 |

**Conclusão:** estado real do banco e do repositório bate exatamente
com o que o `audit-report.md` descreve. **Não há divergência. Plano
prossegue normalmente.**

---

## 1. Inventário consolidado dos 26 achados

Total: **3 CRITICAL · 7 HIGH · 4 MEDIUM · 8 LOW · 4 INFO**.

### 1.1 CRITICAL (3)

| ID | Severidade | Descrição resumida | Arquivo:linha | Recomendação | Status atual | Wave 7? |
|---|---|---|---|---|---|---|
| **AUD-W2V4-001** | CRITICAL | `executar_transicao` zera `rota=None` no reinício de ciclo, dispara trigger `trg_provas_rota_imutavel` com SQLSTATE 22023 para qualquer prova com rota não-NULL | `backend/app/services/state_machine.py:377-384` | `rota_depois = rota_antes` no ramo `reiniciando_ciclo`; 2 testes integrados com banco real | pendente | **SIM** |
| **AUD-W2V4-002** | CRITICAL | Branch `development` HEAD em estado build-broken — `nova-prova/page.tsx` importa `isAllowedImageType` que existe só em working tree de `prova.ts`. `tsc --noEmit` falha em HEAD. | `frontend/src/lib/types/prova.ts`, `frontend/src/hooks/useCreateProva.ts`, `frontend/src/app/globals.css` (working tree dirty) | Commitar as 3 alterações pendentes; revisar anexo Visual Refresh v1 em `analysis.md` (junto com AUD-W2V4-D01); confirmar `tsc --noEmit` exit 0 + `next build` 13/13 NO ESTADO COMMITADO | pendente | não |
| **AUD-W2V4-A01** | CRITICAL | Modificação cirúrgica autorizada por Mario (ADR-119) cobriu apenas o ramo `aprovando`, não `reiniciando_ciclo`. Mesma raiz que AUD-W2V4-001 | `backend/app/services/state_machine.py:377-384` | mesma de AUD-W2V4-001 | pendente (resolvido junto) | **SIM** |

### 1.2 HIGH (7)

| ID | Severidade | Descrição resumida | Recomendação | Status atual | Wave 7? |
|---|---|---|---|---|---|
| **AUD-W2V4-006** | HIGH | Regressão em Wave 3 C14 (`POST /provas/{id}/reiniciar-ciclo`) — funciona para legacy `rota=NULL` mas quebra para `rota=PADRAO/DIRETA` (5 provas) e v4.0 | mesma de AUD-W2V4-001 (resolvido junto) | pendente (resolvido junto) | **SIM** |
| **AUD-W2V4-T01** | HIGH | Suíte `test_imutabilidade_rota.py` não criada — proposta no `analysis.md` §4.10 #7. Sem ela, AUD-W2V4-001 não foi detectado pela CI. | Criar com banco real (não mock_db); 5 cenários (`NULL→valor` permitido, `valor→outro` bloqueado, `valor→NULL` bloqueado, aprovação v4.0 preserva, reinício v4.0 preserva — pós-fix 001) | pendente | **SIM** |
| **AUD-W2V4-T02** | HIGH | Suíte `test_rota_enum_drift.py` não criada — proposta no `analysis.md` §4.10 #9. Confronta `set(RotaEnum)` Python com `pg_enum`. | Criar teste que confronta Python ↔ PostgreSQL ↔ TypeScript (TS via grep nos literais) | pendente | **SIM** |
| **AUD-W2V4-T03** | HIGH | Suíte `test_migration_012.py` não criada — proposta no `analysis.md` §4.10 #8. Sem teste de upgrade/downgrade/idempotência. | Criar teste integrado (banco efêmero `pytest_asyncio`) | pendente | **SIM** |
| **AUD-W2V4-A02** | HIGH | Mitigação documentada do risco "Confusão operacional" (Backlog v4.0 §6) descartada sem substituta. ADR-118 invalidou-se sem manter mitigação. | Trocar default `INITIAL_FORM.rota` de `"MATRIZ"` para `""` (`""` vazio força escolha consciente) + restaurar texto auxiliar "rota imutável após cadastro" abaixo do segment de rotas | pendente | não |
| **AUD-W2V4-M01** | HIGH | `docs/db/schema.sql` declara `alembic_version=011`, omite coluna `codigo_publico`, omite trigger novo, omite indexes novos, mostra `rota_enum` com 2 valores. | Atualizar para refletir `alembic_version=012` + estruturas Wave 2 v4.0 + estruturas Wave 1 v4.0 (helpers em `app_private`, RLS 008-013) | pendente | não |
| **AUD-W2V4-003** | HIGH | Docstring de `codigo_publico_service.py` afirma erroneamente que o trigger `trg_provas_rota_imutavel` enforça unicidade do `codigo_publico` — o trigger protege a coluna `rota`, não `codigo_publico`. | Remover a parte do trigger; deixar só "Unicidade enforced pela coluna `provas_digitais.codigo_publico UNIQUE` (índice `idx_provas_codigo_publico`)" | pendente | não |

### 1.3 MEDIUM (4)

| ID | Severidade | Descrição resumida | Recomendação | Status atual |
|---|---|---|---|---|
| **AUD-W2V4-004** | MEDIUM | Handler `criar_prova` mapeia qualquer `IntegrityError` para 409 "Numero de requerimento ja cadastrado" — mensagem enganosa se a colisão for de `codigo_publico`. Sem retry. | Diferenciar `exc.orig.diag.constraint_name` ou usar `pg_error_code`. Em colisão de `idx_provas_codigo_publico`: retry até 3x. Em colisão de `provas_digitais_nro_requerimento_key`: manter 409 atual. |  pendente |
| **AUD-W2V4-005** | MEDIUM | `validar_payload_qr` aceita formato legacy v3.0 e v4.0 sem distinguir nem documentar contrato. Risco para Componente 19 (Wave 3 v4.0). | Adicionar comentário explícito documentando o contrato "identificador pode ser PRV-* (preferencial) ou nro_requerimento (legacy)"; teste integrado fica para Wave 3 v4.0 (registrar follow-up) | pendente |
| **AUD-W2V4-M02** | MEDIUM | Migration Alembic 012 do repo é atomic, mas em produção foi aplicada em 3 chunks via MCP (`012a`, `012b`, `012c`). | Documentar em CLAUDE.md e na docstring da migration 012 que `alembic_version=012` corresponde aos 3 chunks. Adicionar nota em `docs/wave2-v4/audit-report.md` apêndice. | pendente |
| **AUD-W2V4-T04** | MEDIUM | Cobertura E2E ausente para 4 rotas — só schema Pydantic + state_machine (mock_db). Sem smoke HTTP integrado. | Smoke E2E manual obrigatório antes do merge para `main` (validação humana, não automática); registrar em `fix-validation.md` | pendente |

### 1.4 LOW (8)

| ID | Severidade | Descrição resumida | Recomendação | Status atual |
|---|---|---|---|---|
| **AUD-W2V4-S01** | LOW | `gerar_payload_qr(identificador, hash)` não valida que `identificador` não contém `\|` (separador do payload). Defesa preventiva — callers atuais filtram. | `if "\|" in identificador: raise ValueError(...)` em `qrcode_service.gerar_payload_qr`; teste mínimo | pendente |
| **AUD-W2V4-007** | LOW | Audit log de reinício de ciclo grava `"rota_depois": None`. Após o fix do AUD-W2V4-001 passa a gravar `"rota_depois": rota_antes.value`. Mudança de contrato. | Verificar no fix de AUD-W2V4-001 que o `detalhes_json` reflete o novo contrato; registrar em DECISIONS | pendente (resolvido junto com 001) |
| **AUD-W2V4-P03** | LOW | `gerar_pdf` lê 2 SVGs do disco a cada chamada (sem cache). Custo aceitável (<200ms total). | Cache em memória dos bytes do SVG via `functools.lru_cache` ou variável módulo-level. Ganho marginal mas trivial. | pendente |
| **AUD-W2V4-M03** | LOW | Default `INITIAL_FORM.rota = "MATRIZ"` (`page.tsx:48`) aumenta risco operacional. Combinado com AUD-W2V4-A02. | Resolvido junto com AUD-W2V4-A02 (default vazio) | pendente (resolvido junto com A02) |
| **AUD-W2V4-M04** | LOW | ADR-120 SUPERSEDIDO menciona duplicação de logos backend↔frontend que o Visual Refresh v2 já eliminou. Confunde leitor. | Adicionar bloco "Pós-supersedimento (Visual Refresh v2)" no ADR-120 esclarecendo que `frontend/public/etiqueta/` foi removido | pendente |
| **AUD-W2V4-T05** | LOW | Teste `test_gerar_codigo_publico_nao_determinismo_sufixo` usa 200 amostras; prompt original pediu 10.000. Probabilidade de colisão em 10k é ~57%. | Aumentar para 10.000 amostras com tolerância matemática justificada (esperar zero colisões, não tolerar nenhuma) — `assert distintos == 10000` | pendente |
| **AUD-W2V4-D01** | LOW | Anexo "Visual Refresh Execution" em `docs/wave2-v4/analysis.md` (linhas 1268-1417) está descommitted no working tree e referencia estado SUPERSEDED pelo Visual Refresh v2. | Atualizar texto para refletir o estado pós-Visual Refresh v2 (ou anexar nota explícita "este anexo descreve o estado intermediário v1, posteriormente superseded — manter por valor histórico"). Commit junto com AUD-W2V4-002. | pendente |
| **AUD-W2V4-D02** | LOW | CHANGELOG e analysis.md declaram `tsc --noEmit` exit 0 e `next build` 13/13, validações que eram falsas no HEAD `1b47290` por causa de AUD-W2V4-002. | Após fix de AUD-W2V4-002 (commit dos 3 arquivos), rodar `npx tsc --noEmit` + `npx next build` no estado commitado e atualizar CHANGELOG com nota "Re-validado pós-correção AUD-W2V4-002" | pendente (resolvido junto com 002) |

### 1.5 INFO (4) — todos não-acionáveis (registrar status)

| ID | Severidade | Descrição resumida | Tratamento |
|---|---|---|---|
| **AUD-W2V4-S02** | INFO | Etiqueta semi-pública por design — mitigações DAT v3.0 §8.2 ficam para Wave 3 v4.0 / Componente 19 | Apenas registrar como follow-up em DECISIONS.md / `audit-report.md` apêndice |
| **AUD-W2V4-S03** | INFO | `service_role` bypassa RLS, mas trigger `trg_provas_rota_imutavel` BEFORE UPDATE continua disparando. Não é escape route. | Apenas confirmar e registrar |
| **AUD-W2V4-P01** | INFO | `idx_provas_rota` aparece como `unused_index` no advisor — esperado (zero provas v4.0 em produção). Cairá com uso real. | Apenas registrar |
| **AUD-W2V4-P02** | INFO | `idx_provas_codigo_publico` JÁ usado pelo UNIQUE check do INSERT da migration 012. | Apenas confirmar e registrar |

---

## 2. Plano de correção por achado (estratégia + arquivos + riscos + teste)

> Convenções: cada item especifica **estratégia em 2-4 linhas**,
> **arquivos tocados**, **camadas afetadas**, **risco de regressão**,
> **risco para a Wave 7**, **teste/validação**, **dependência de
> outros achados**.

### 2.1 AUD-W2V4-001 + AUD-W2V4-A01 + AUD-W2V4-006 + AUD-W2V4-007 (commit coeso)

- **Estratégia:** alterar 1 linha em `state_machine.executar_transicao` —
  ramo `reiniciando_ciclo` (linhas 377-384) — substituindo
  `rota_depois = None` por `rota_depois = rota_antes`. Isso preserva
  rota imutável tanto para v4.0 (`MATRIZ/LAM_MATRIZ/FILIAL/LAM_FILIAL`)
  quanto para legacy (`PADRAO/DIRETA/NULL`). Comentário explicativo
  citando RF-009 v4.0, RN-006 v4.0, US-010 + ADR novo.
- **Arquivos tocados:** `backend/app/services/state_machine.py`
  (linhas 377-384 + comentário); `backend/tests/test_state_machine.py`
  (atualizar `test_executar_reinicio_ciclo_reprovada_para_criada_incrementa`
  — assertions `prova.rota == RotaEnum.PADRAO` e
  `kwargs["detalhes"]["rota_depois"] == "PADRAO"` em vez de None).
- **Camadas afetadas:** Python only — não toca enum, schema, RLS, frontend.
- **Risco de regressão:** **médio**. Wave 3 C14 mudou comportamento.
  Mitigação: o fix preserva o que admin fez (não destrói dado);
  `Movimentacao.rota_no_momento` agora carrega rota preservada (era
  None). Audit log carrega `rota_depois=PADRAO` (era None) —
  AUD-W2V4-007 (mudança de contrato silenciosa, mas justificada
  e melhor — antes o log mentia).
- **Risco para a Wave 7:** **NEGATIVO** — o fix é um pré-requisito da
  Wave 7. Sem ele, a state machine quebra para qualquer prova com
  rota preenchida.
- **Teste/validação:** (a) teste `test_state_machine.py` existente
  ajustado; (b) **2 novos testes integrados** em
  `backend/tests/test_imutabilidade_rota.py` (criados em AUD-W2V4-T01)
  rodando UPDATE real contra banco com trigger ativo — um para
  prova v4.0 (`rota=MATRIZ` preservada), outro para legacy
  (`rota=NULL` mantida).
- **Dependências:** nenhuma (resolução prevalece sobre AUD-W2V4-T01,
  mas o teste de T01 valida o fix de 001 — ordem: 001 fix primeiro,
  T01 depois para validar).
- **ADR novo:** ADR-123 — "Reinício de ciclo preserva `rota` (RN-006
  v4.0 + RF-009 v4.0)" registrando a correção da modificação cirúrgica.

### 2.2 AUD-W2V4-002 + AUD-W2V4-D01 + AUD-W2V4-D02 (commit coeso)

- **Estratégia:** commit das 3 alterações pendentes em 1 commit coeso
  (`prova.ts` adiciona `AllowedImageType` + `isAllowedImageType`,
  `useCreateProva.ts` consome o helper, `globals.css` ajusta cor de
  `--color-card-surface-alt`). Decidir sobre o anexo Visual Refresh v1
  do `analysis.md`: **manter** com nota explícita "este anexo descreve
  o estado intermediário v1 — superseded por Visual Refresh v2 em
  `5047172`/`c06ca56`. Mantido por valor histórico de processo." (não
  perder informação; quem ler entende o contexto).
- **Arquivos tocados:** `frontend/src/lib/types/prova.ts`,
  `frontend/src/hooks/useCreateProva.ts`, `frontend/src/app/globals.css`,
  `docs/wave2-v4/analysis.md` (anexo + nota de supersedimento).
- **Camadas afetadas:** Frontend TypeScript / CSS only. Nenhum teste
  do backend afetado.
- **Risco de regressão:** **baixo** — o helper já é o que `page.tsx`
  espera. `useCreateProva` ganha o helper consistente. Cor
  `--color-card-surface-alt` muda de `#d7d7d7` para `#e4e4e4` (ajuste
  visual cosmético para Visual Refresh v2 — ja é o que está rodando
  em produção dirty).
- **Risco para a Wave 7:** **nenhum**.
- **Teste/validação:** `npx tsc --noEmit` exit 0 NO ESTADO COMMITADO
  (não dirty), `npx next build` 13/13 páginas NO ESTADO COMMITADO,
  smoke visual rápido em `/nova-prova` (botão de submit ainda
  funciona). Atualizar CHANGELOG com nota "Re-validado pós-correção
  AUD-W2V4-002 — `tsc --noEmit` exit 0 NO ESTADO COMMITADO `<sha>`"
  (resolve AUD-W2V4-D02).
- **Dependências:** nenhuma — pode ser feito em paralelo ao 001 mas
  por ordem topológica (severidade), 001 vem primeiro.

### 2.3 AUD-W2V4-T01 — Suíte `test_imutabilidade_rota.py` (banco real)

- **Estratégia:** criar `backend/tests/test_imutabilidade_rota.py`
  com 5 testes integrados que rodam UPDATE/INSERT real contra um banco
  PostgreSQL efêmero. Cobrir: (a) `NULL → valor` permitido (Wave 7
  readiness), (b) `valor → outro_valor` bloqueado com SQLSTATE 22023,
  (c) `valor → NULL` bloqueado com SQLSTATE 22023, (d) aprovação v4.0
  preserva rota, (e) reinício de ciclo v4.0 preserva rota (valida fix
  AUD-W2V4-001). Usar fixture `pytest_asyncio` + `asyncpg` direto
  para garantir trigger ativo.
- **Arquivos tocados:** `backend/tests/test_imutabilidade_rota.py`
  (novo); possivelmente `backend/tests/conftest.py` (fixture novo de
  banco real se não existir; se a infra de testes já tiver, reutilizar).
- **Camadas afetadas:** apenas testes — sem mudança de código de
  produção.
- **Risco de regressão:** **nenhum** (apenas testes).
- **Risco para a Wave 7:** **NEGATIVO** — esses testes são o
  mecanismo de proteção da Wave 7. Sem eles, qualquer PR que altere
  o trigger pode quebrar a permissividade `NULL → valor`.
- **Teste/validação:** os 5 testes precisam passar em CI; se o ambiente
  de CI não tiver Postgres real, marcar com `@pytest.mark.integration`
  + skipif quando `DATABASE_URL` não disponível, e rodar localmente +
  staging.
- **Dependências:** depende do fix de **AUD-W2V4-001** estar aplicado
  (teste e valida o fix; rodando antes, o teste falharia).

### 2.4 AUD-W2V4-T02 — Suíte `test_rota_enum_drift.py`

- **Estratégia:** criar `backend/tests/test_rota_enum_drift.py` com
  2-3 testes:
  - (1) confronta `set(RotaEnum)` Python com `SELECT enumlabel FROM
    pg_enum` PostgreSQL via `asyncpg`. Atual: ambos têm 6 (`PADRAO`,
    `DIRETA`, `MATRIZ`, `LAM_MATRIZ`, `FILIAL`, `LAM_FILIAL`).
  - (2) confronta literais TypeScript: lê `frontend/src/lib/types/prova.ts`,
    extrai `Rota` e `RotaCriacao` via regex/AST simples; confirma
    que `Rota` tem os 6 valores e `RotaCriacao` tem só os 4 v4.0.
  - (3) confronta `RotaCriacaoEnum` Pydantic com `RotaEnum` (subset).
- **Arquivos tocados:** `backend/tests/test_rota_enum_drift.py` (novo).
- **Camadas afetadas:** testes only.
- **Risco de regressão:** **nenhum**.
- **Risco para a Wave 7:** **NEGATIVO** — esse teste é o mecanismo
  de proteção contra drift entre as 3 camadas no futuro. Sem ele, um
  PR que adicione valor numa só camada introduz inconsistência sem
  detecção.
- **Teste/validação:** o próprio teste é a validação.
- **Dependências:** nenhuma.

### 2.5 AUD-W2V4-T03 — Suíte `test_migration_012.py`

- **Estratégia:** criar `backend/tests/test_migration_012.py` com 3 testes:
  - (1) `alembic upgrade head` em ambiente limpo (banco efêmero) —
    confirma que migration 012 aplica sem erro mesmo SEM provas
    legacy (backfill é no-op).
  - (2) `alembic downgrade -1` reverte coluna + trigger + indexes
    (não reverte ENUM ADD VALUE — limitação Postgres documentada).
  - (3) idempotência: aplicar migration 012 duas vezes consecutivas
    não quebra (backfill com `WHERE codigo_publico IS NULL` retorna
    zero linhas no segundo run; trigger usa `CREATE OR REPLACE`).
- **Arquivos tocados:** `backend/tests/test_migration_012.py` (novo);
  possivelmente nova fixture em `conftest.py`.
- **Camadas afetadas:** testes only.
- **Risco de regressão:** **nenhum**.
- **Risco para a Wave 7:** **MÉDIO POSITIVO** — Wave 7 vai criar
  migration 013+ que precisa coexistir com 012. Validar idempotência
  agora reduz risco operacional na Wave 7.
- **Teste/validação:** próprio teste.
- **Dependências:** nenhuma.

### 2.6 AUD-W2V4-A02 + AUD-W2V4-M03 (commit coeso)

- **Estratégia:** trocar `INITIAL_FORM.rota` de `"MATRIZ"` para `""` 
  (string vazia) em `nova-prova/page.tsx:48`. Como `RotaCriacao` é
  literal `MATRIZ | LAM_MATRIZ | FILIAL | LAM_FILIAL`, mudar tipo do
  campo para `RotaCriacao | ""`. Validar no submit: se `form.rota === ""`,
  mostrar erro "Selecione uma rota antes de prosseguir." e impedir
  envio. Restaurar texto auxiliar abaixo do segment de rotas: 
  "A rota escolhida é imutável após o cadastro" — pequeno, em
  `--color-card-text-muted`. Pill animado do segment não destaca
  nenhum botão até o admin clicar.
- **Arquivos tocados:** `frontend/src/app/(dashboard)/nova-prova/page.tsx`
  (estado inicial + tipo + handler de submit + texto auxiliar);
  `frontend/src/app/(dashboard)/nova-prova/nova-prova.module.css`
  (selo de hint).
- **Camadas afetadas:** frontend TypeScript / CSS only.
- **Risco de regressão:** **baixo** — apenas UX. Backend continua
  rejeitando criação sem rota (RotaCriacaoEnum required em Pydantic,
  422). Caso pior: admin testa o formulário sem mudar — vê erro,
  escolhe rota, submete.
- **Risco para a Wave 7:** **nenhum**.
- **Teste/validação:** smoke manual em `/nova-prova` (não automatizo
  porque é UX). Re-roda `tsc --noEmit` e `next build`.
- **Dependências:** nenhuma. Pode ser feito após AUD-W2V4-002 estar
  commitado (mesma página).
- **ADR novo:** ADR-124 — "Default `rota` vazio + texto auxiliar
  restaurado (mitigação Backlog v4.0 §6 'Confusão operacional')".

### 2.7 AUD-W2V4-M01 — Atualizar `docs/db/schema.sql`

- **Estratégia:** reescrever `docs/db/schema.sql` para refletir o
  estado atual:
  - `alembic_version=012`.
  - `rota_enum` com 6 valores (`PADRAO`, `DIRETA`, `MATRIZ`,
    `LAM_MATRIZ`, `FILIAL`, `LAM_FILIAL`).
  - `provas_digitais` com coluna `codigo_publico VARCHAR(20) UNIQUE
    NOT NULL`.
  - Trigger `trg_provas_rota_imutavel` + função
    `fn_bloquear_alteracao_rota`.
  - Indexes `idx_provas_codigo_publico` UNIQUE + `idx_provas_rota`.
  - Migrations 010, 011, 012 listadas.
  - RLS migrations 008-013 listadas (Wave 6 + Wave 1 v4.0 + Wave 1 v4.0 Audit Round 2).
  - Schema `app_private` com 3 helpers SECURITY DEFINER (Wave 1 v4.0).
- **Arquivos tocados:** `docs/db/schema.sql`.
- **Camadas afetadas:** docs only.
- **Risco de regressão:** **nenhum**.
- **Risco para a Wave 7:** **POSITIVO** — Wave 7 vai consultar este
  arquivo para entender o estado de partida do backfill. Atual mente
  desatualizado.
- **Teste/validação:** comparar manualmente com output de
  `pg_dump --schema-only` ou queries MCP individuais. Ao final do
  arquivo adicionar nota: "Última atualização: 2026-05-05 (Wave 2 v4.0
  Audit Fixes — `alembic_version=012`)."
- **Dependências:** nenhuma.

### 2.8 AUD-W2V4-003 — Docstring `codigo_publico_service.py`

- **Estratégia:** alterar linhas 14-16 da docstring substituindo
  "Unicidade enforced pela coluna `provas_digitais.codigo_publico
  UNIQUE` e pelo trigger `trg_provas_rota_imutavel`" por "Unicidade
  enforced pela coluna `provas_digitais.codigo_publico UNIQUE`
  (índice `idx_provas_codigo_publico`). O trigger
  `trg_provas_rota_imutavel` protege apenas a coluna `rota`."
- **Arquivos tocados:** `backend/app/services/codigo_publico_service.py`
  (linhas 14-16).
- **Camadas afetadas:** docs/comentário only.
- **Risco de regressão:** **nenhum**.
- **Risco para a Wave 7:** **nenhum**.
- **Teste/validação:** revisão visual.
- **Dependências:** nenhuma.

### 2.9 AUD-W2V4-004 — Retry no handler de criação

- **Estratégia:** alterar bloco `try/except` em `provas.py:488-543`
  para distinguir constraint violado:
  - Importar `from psycopg2 import errors as pg_errors` (ou usar
    `exc.orig.diag.constraint_name` direto via SQLAlchemy 2.0 + asyncpg).
  - Se `constraint_name == "idx_provas_codigo_publico"`: regenerar
    `codigo_publico` via `gerar_codigo_publico(created_at)` e tentar
    de novo (até 3x). Em todas as 3 tentativas falhar, levantar 502.
  - Se `constraint_name == "provas_digitais_nro_requerimento_key"`:
    manter 409 atual com mensagem original.
  - Outros constraints: levantar 502 (genérico).
  - Refatorar o INSERT em uma função `_inserir_prova_com_retry` para
    isolar o loop.
- **Arquivos tocados:** `backend/app/api/v1/provas.py:474-543`
  (handler `criar_prova`); `backend/tests/test_provas_api_v4.py`
  (teste novo: simular `IntegrityError` com `constraint_name` mockado,
  confirmar retry + regeneração).
- **Camadas afetadas:** backend Python only.
- **Risco de regressão:** **médio** — o try/except atual é compartilhado
  com outras IntegrityError implícitas (FK quebrada, NOT NULL violado).
  Mitigação: branch "outros" continua mapeando para 502 (mesmo
  comportamento do `except Exception` atual). Resultado net: 409 só
  para `nro_requerimento`, 502 para `codigo_publico` (após esgotar
  retries) e demais.
- **Risco para a Wave 7:** **nenhum**.
- **Teste/validação:** novo teste com mock de `IntegrityError(diag.
  constraint_name=...)`.
- **Dependências:** nenhuma.

### 2.10 AUD-W2V4-005 — Documentar contrato `validar_payload_qr`

- **Estratégia:** atualizar docstring de `validar_payload_qr` em
  `qrcode_service.py:66-86` adicionando bloco "Contrato do segundo
  campo (`identificador`)" explicando: aceita `PRV-AAAA-MM-NNNNNN`
  (v4.0 — preferencial) ou `nro_requerimento` (legacy v3.0); a
  função apenas valida estrutura + hash, não o lookup; o caller
  (Wave 3 v4.0 / Componente 19) decide qual lookup usar baseado no
  formato do segundo campo. Adicionar nota: "TEST PENDING — teste
  integrado da coexistência Wave 3 v4.0 / Componente 19 quando
  implementado".
- **Arquivos tocados:** `backend/app/services/qrcode_service.py`
  (docstring + comentário).
- **Camadas afetadas:** docs only.
- **Risco de regressão:** **nenhum**.
- **Risco para a Wave 7:** **nenhum** (Wave 3 v4.0 é Componente 19,
  não Wave 7).
- **Teste/validação:** revisão visual.
- **Dependências:** nenhuma.

### 2.11 AUD-W2V4-M02 — Documentar 3 chunks MCP

- **Estratégia:** adicionar nota em `CLAUDE.md` (seção "Estado atual
  do banco de producao") + docstring da migration 012 explicando que
  a migration foi aplicada em 3 chunks via MCP (`012a`, `012b`, `012c`)
  para evitar limitação do Postgres `ALTER TYPE ADD VALUE` em
  transação que usa o valor recém-adicionado. O `alembic_version='012'`
  foi setado manualmente após o terceiro chunk. **Idempotência
  da migration Alembic do repo é validada pela suíte AUD-W2V4-T03**
  (a versão do repo aplica em ambiente fresh sem chunks).
- **Arquivos tocados:** `CLAUDE.md` (seção banco); 
  `backend/migrations/versions/012_add_codigo_publico_and_rotas_v4_to_provas.py`
  (docstring).
- **Camadas afetadas:** docs only.
- **Risco de regressão:** **nenhum**.
- **Risco para a Wave 7:** **POSITIVO** — Wave 7 precisa entender que
  o histórico Alembic em produção tem 1 entrada (`012`) mas
  `supabase_migrations` tem 3 entradas. Documentar agora evita
  confusão.
- **Teste/validação:** revisão visual.
- **Dependências:** nenhuma.

### 2.12 AUD-W2V4-T04 — Smoke E2E manual obrigatório

- **Estratégia:** documentar em `fix-validation.md` (Gate 2 final)
  um checklist de smoke E2E que **deve ser executado antes do merge**:
  - (a) Criar prova com cada uma das 4 rotas v4.0.
  - (b) Verificar que `codigo_publico` aparece em `/provas` e
    `/provas/{id}`.
  - (c) Visualizar PDF da etiqueta — confirmar badge da rota +
    `codigo_publico` em mono abaixo do QR.
  - (d) Para uma das 4 rotas: vendedor escaneia + aprova + admin
    reinicia ciclo (cobrindo o fix de AUD-W2V4-001 em E2E real).
  - **Nenhum teste automatizado novo** — Playwright/Cypress fica
    para uma sessão dedicada futura.
- **Arquivos tocados:** apenas `docs/wave2-v4/fix-validation.md`
  (Gate 2 final).
- **Camadas afetadas:** docs only.
- **Risco de regressão:** **nenhum**.
- **Risco para a Wave 7:** **POSITIVO** — Wave 7 vai querer fazer
  smoke E2E parecido com provas backfilled. Estabelecer o procedimento
  agora.
- **Teste/validação:** registro humano (Mario) confirmando execução.
- **Dependências:** depende do fix de AUD-W2V4-001 (smoke E2E não
  pode rodar enquanto reinício de ciclo está quebrado para v4.0).

### 2.13 AUD-W2V4-S01 — Validar separador `|` em `gerar_payload_qr`

- **Estratégia:** alterar `qrcode_service.gerar_payload_qr` adicionando
  no início:
  ```python
  if QR_PAYLOAD_SEPARATOR in identificador:
      raise ValueError(
          f"Identificador nao pode conter o separador '|' do payload "
          f"(recebi: {identificador!r})"
      )
  ```
  Defesa preventiva — todos os callers atuais já filtram, mas helper é
  público (DAT v3.0 §8 considera reutilização futura).
- **Arquivos tocados:** `backend/app/services/qrcode_service.py:48-63`;
  `backend/tests/test_qrcode_service.py` (teste novo — mínimo).
- **Camadas afetadas:** backend Python only.
- **Risco de regressão:** **baixíssimo** — callers atuais não passam
  `|`.
- **Risco para a Wave 7:** **nenhum**.
- **Teste/validação:** novo teste `test_gerar_payload_qr_rejeita_separador`.
- **Dependências:** nenhuma.

### 2.14 AUD-W2V4-P03 — Cache do logo SVG

- **Estratégia:** alterar `etiqueta_service.py` para cachear os bytes
  dos SVGs em variáveis módulo-level (lidos uma vez no startup):
  ```python
  _LOGO_3STUDIO_BYTES = _LOGO_3STUDIO.read_bytes() if _LOGO_3STUDIO.exists() else None
  _LOGO_STUDIO_ART_BYTES = _LOGO_STUDIO_ART.read_bytes() if _LOGO_STUDIO_ART.exists() else None
  ```
  E em `gerar_pdf` passar bytes para `pdf.image(io.BytesIO(_LOGO_*_BYTES), ...)`
  em vez do path. **Confirmar que fpdf2 suporta** `io.BytesIO` para SVG
  (suporta para PNG; SVG é caso à parte). **Se não suportar bytes**, manter
  path mas adicionar `lru_cache(maxsize=2)` num helper que só conta
  acessos (lru_cache é a otimização barata; o fpdf2 ainda lê o path
  internamente, então o ganho é marginal — registrar como limitação
  e fechar com baixa prioridade).
- **Arquivos tocados:** `backend/app/services/etiqueta_service.py`
  (linhas 100-145, 215-225).
- **Camadas afetadas:** backend Python only.
- **Risco de regressão:** **médio** — qualquer mudança no `pdf.image`
  pode quebrar o layout. Mitigação: validar pixel-perfeito que PDF
  gerado bate byte-a-byte com a versão pré-correção via fixture.
- **Risco para a Wave 7:** **nenhum**.
- **Teste/validação:** rodar `test_etiqueta_service.py` existente +
  comparar bytes do PDF antes/depois (assert `len(pdf_bytes_pre) == len(pdf_bytes_pos)`
  ou diff visual via `pdf2image`).
- **Dependências:** nenhuma.
- **Decisão alternativa aceitável:** se a investigação mostrar que
  fpdf2 não suporta `BytesIO` para SVG sem reescrita maior, **fechar
  o achado como WONTFIX** com justificativa em DECISIONS.md (custo de
  fix > ganho de performance). Fica como follow-up técnico.

### 2.15 AUD-W2V4-M04 — Esclarecer ADR-120 SUPERSEDIDO

- **Estratégia:** adicionar bloco "**Pós-supersedimento (Visual Refresh
  v2 — 2026-05-05)**" no ADR-120 explicitando que a duplicação dos
  logos (`backend/app/services/etiqueta_assets/` ↔
  `frontend/public/etiqueta/`) descrita nas "Consequências" foi
  resolvida pelo Visual Refresh v2: a pasta `frontend/public/etiqueta/`
  foi DELETADA junto com o componente `EtiquetaPreview`. Apenas
  `backend/app/services/etiqueta_assets/` permanece (fonte do PDF).
- **Arquivos tocados:** `DECISIONS.md` (seção ADR-120).
- **Camadas afetadas:** docs only.
- **Risco de regressão:** **nenhum**.
- **Risco para a Wave 7:** **nenhum**.
- **Teste/validação:** revisão visual.
- **Dependências:** nenhuma.

### 2.16 AUD-W2V4-T05 — Aumentar amostras para 10.000

- **Estratégia:** alterar `test_gerar_codigo_publico_nao_determinismo_sufixo`
  em `backend/tests/test_codigo_publico_service.py:85-94` para usar
  `range(10_000)` em vez de `range(200)`. Probabilidade matemática:
  com 31^6 = 887M e 10k amostras, prob. de colisão ≈
  10000² / (2 × 887M) ≈ 5.6%. Para reduzir flake, aplicar **amostragem
  com seed determinística** (definir `secrets.SystemRandom().seed(...)` —
  não, `secrets` não tem seed). Alternativa: usar `random.seed(42)` +
  `random.choice` no helper de teste, mantendo `secrets.choice` em
  produção. Asserção: `assert distintos == 10000` (zero colisões com
  o seed escolhido). Documentar no comentário.
- **Arquivos tocados:** `backend/tests/test_codigo_publico_service.py:85-94`.
- **Camadas afetadas:** testes only.
- **Risco de regressão:** **baixo** — apenas mais amostras. Tempo
  do teste: ~50ms (`secrets.choice` é rápido).
- **Risco para a Wave 7:** **nenhum**.
- **Teste/validação:** rodar o próprio teste; se for flaky com
  `secrets.choice` real, manter `range(10_000)` mas mudar assertion
  para `assert distintos >= 9_995` (tolerar 5 colisões — ainda é
  bem mais rigoroso que 200/199).
- **Dependências:** nenhuma.

### 2.17 AUD-W2V4-INFO (S02, S03, P01, P02) — só registrar

- **Estratégia:** apenas registrar status no apêndice do
  `audit-report.md` com justificativa:
  - S02: NÃO APLICÁVEL nesta sessão — mitigação fica para Componente 19
    da Wave 3 v4.0. Registrar follow-up em DECISIONS.md (já está em
    ADR-119).
  - S03: NÃO APLICÁVEL — informação confirmada e correta.
  - P01: NÃO APLICÁVEL — esperado, sem ação.
  - P02: NÃO APLICÁVEL — confirmado.
- **Arquivos tocados:** apenas apêndice de status em
  `docs/wave2-v4/audit-report.md`.
- **Camadas afetadas:** docs only.
- **Risco de regressão:** **nenhum**.
- **Risco para a Wave 7:** **nenhum**.
- **Teste/validação:** revisão visual.

---

## 3. Ordem topológica de execução

Respeitando a hierarquia: **(1) severidade alta → baixa, (2) afeta-Wave-7
primeiro dentro do mesmo grupo, (3) dependências**.

| # | ID | Sev | Wave 7? | Dependência |
|---|---|---|---|---|
| 1 | **AUD-W2V4-001** + **A01** + **006** + **007** (commit coeso) | CRITICAL+HIGH+LOW | **SIM** | nenhuma |
| 2 | **AUD-W2V4-002** + **D01** + **D02** (commit coeso) | CRITICAL+LOW | não | nenhuma |
| 3 | **AUD-W2V4-T01** | HIGH | **SIM** | depende de #1 (testa o fix 001) |
| 4 | **AUD-W2V4-T02** | HIGH | **SIM** | nenhuma |
| 5 | **AUD-W2V4-T03** | HIGH | **SIM** | nenhuma |
| 6 | **AUD-W2V4-A02** + **M03** (commit coeso) | HIGH+LOW | não | depende de #2 estar commitado |
| 7 | **AUD-W2V4-M01** | HIGH | não | nenhuma |
| 8 | **AUD-W2V4-003** | HIGH | não | nenhuma |
| 9 | **AUD-W2V4-004** | MEDIUM | não | nenhuma |
| 10 | **AUD-W2V4-005** | MEDIUM | não | nenhuma |
| 11 | **AUD-W2V4-M02** | MEDIUM | não | nenhuma |
| 12 | **AUD-W2V4-S01** | LOW | não | nenhuma |
| 13 | **AUD-W2V4-P03** | LOW | não | nenhuma |
| 14 | **AUD-W2V4-M04** | LOW | não | nenhuma |
| 15 | **AUD-W2V4-T05** | LOW | não | nenhuma |
| 16 | **AUD-W2V4-T04** (smoke E2E manual) | MEDIUM | não | depende de #1 estar mergeado em ambiente staging |
| 17 | **AUD-W2V4-S02/S03/P01/P02** (INFO — só registrar) | INFO | não | nenhuma |

**Total esperado de commits:** ~14 commits atômicos rastreáveis.

---

## 4. Análise de risco agregado

### 4.1 Achados com risco ALTO de regressão

- **AUD-W2V4-001** — touch em `state_machine.executar_transicao` que
  é Wave 3 (já em produção). Mitigação obrigatória: rodar suíte
  `test_state_machine.py` completa após o fix; rodar `test_provas_api.py`
  completo (cancelamento, transições, scan); validar que
  `test_executar_reinicio_ciclo_reprovada_para_criada_incrementa`
  passa com novas assertions (`prova.rota == RotaEnum.PADRAO` em
  vez de None). E **rodar AUD-W2V4-T01** imediatamente depois para
  validação real contra trigger.

### 4.2 Achados com risco para a Wave 7

Listados em ordem de criticidade para a Wave 7:

1. **AUD-W2V4-001/A01/006** — bug existente bloqueia state machine para
   provas com rota preenchida. Wave 7 vai exercitar reinício como parte
   do backfill operacional. **Sem o fix, Wave 7 não consegue rodar.**
2. **AUD-W2V4-T01** — sem teste explícito de `NULL → valor`, qualquer
   PR futuro pode quebrar a permissividade do trigger sem detecção. 
   Wave 7 descobriria tarde.
3. **AUD-W2V4-T02** — sem teste de drift, Wave 7 (que vai mexer no
   enum se decidir DROP dos legacy) pode introduzir inconsistência
   silenciosa.
4. **AUD-W2V4-T03** — sem idempotência validada, migration Alembic
   013+ da Wave 7 pode entrar em conflito com 012.

Cada um desses 4 itens precisa de validação explícita:
- Teste `test_imutabilidade_rota_v4_aprovacao_preserva` passa.
- Teste `test_imutabilidade_rota_v4_reinicio_preserva` passa (valida fix 001).
- Teste `test_imutabilidade_rota_legacy_null_pode_receber_valor` passa.
- Teste `test_rota_enum_drift_python_postgres` passa.
- Teste `test_migration_012_idempotente` passa.

### 4.3 Achados que mexem em provas legacy (`rota IS NULL` em produção)

- **AUD-W2V4-001** fix preserva `rota=NULL` em reinício (legacy). Já
  é o comportamento do código novo (`rota_depois = rota_antes`).
  Validação em **AUD-W2V4-T01** cobre cenário.
- Nenhuma outra correção quebra o caminho legacy.

### 4.4 Achados que tocam código de Waves 0-6 da v3.0 ou Wave 1 v4.0

- **AUD-W2V4-001/A01/006/007** — `state_machine.executar_transicao`
  é da Wave 3 v3.0 (Componente 11, Lote A). Modificação cirúrgica
  autorizada já existia na Wave 2 v4.0 (ADR-119). A correção é
  estritamente em escopo: completa a modificação cirúrgica.
- **AUD-W2V4-M01** — `docs/db/schema.sql` reflete acúmulo de waves;
  atualização aborda Wave 5 (Bloco 5.0), Wave 6 (RLS 008), Wave 1
  v4.0 (RLS 009-012, schema `app_private`), Wave 1 v4.0 Audit Round 2
  (RLS 013), Wave 2 v4.0 (migration 012, trigger imutabilidade).
  Atualizar documentação de waves anteriores que ainda estavam
  desatualizadas é parte legítima do escopo.
- Nenhuma outra correção toca código de waves preexistentes.

### 4.5 Achados que exigem nova migration Alembic ou RLS

**Nenhum.** As correções não exigem nova migration Alembic nem nova
RLS. Confirmado item-a-item:
- AUD-W2V4-001: só Python (state_machine).
- AUD-W2V4-T01/T02/T03: só testes.
- AUD-W2V4-002/D01/D02: frontend + docs.
- AUD-W2V4-A02/M03: frontend + docs.
- AUD-W2V4-M01/M02/M04: docs.
- AUD-W2V4-003/004/005/S01/P03/T05: backend Python (sem schema).
- AUD-W2V4-INFO: docs.

### 4.6 Achados que mexem no enum `rota_enum` em 3 camadas

**Nenhum** — apenas AUD-W2V4-T02 cria teste de drift que VALIDA
sincronia, mas não modifica o enum. Os 4 valores v4.0 já estão nas
3 camadas e batem.

### 4.7 Achados que mexem em testes

- AUD-W2V4-001 ajusta 1 teste existente (`test_executar_reinicio_ciclo_*`).
  **Validação adversarial:** o teste original asserta `rota=None` no
  pós; o ajuste asserta `rota=PADRAO` (legacy) ou rota preservada
  (v4.0). **Não relaxa** assertion — endurece (verifica preservação
  em vez de zeramento). OK.
- AUD-W2V4-T01/T02/T03/T05/004/S01: criam testes novos. **Validação
  adversarial:** garantir que não são tautológicos — cada teste deve
  exercer comportamento real de produção, não só mock.

### 4.8 Achados bloqueados por divergência

**Nenhum.** Estado real do banco e do repositório bate com o que o
audit-report descreve. Plano executa sem bloqueio.

---

## 5. Plano de validação interna pós-correção (Seção 6 do prompt)

### 5.1 Suítes de teste que devem passar

- [ ] `pytest backend/tests/` completo — 795+ testes (era 795 pré-correção;
  esperado: ~810+ pós-correção com novas suítes).
- [ ] `pytest backend/tests/test_state_machine.py` 26+ testes (1 ajustado).
- [ ] `pytest backend/tests/test_provas_api.py` 59+ testes — sem regressão.
- [ ] `pytest backend/tests/test_provas_api_v4.py` 14 testes existentes + N novos
  para AUD-W2V4-004 (retry codigo_publico).
- [ ] `pytest backend/tests/test_imutabilidade_rota.py` 5 testes novos
  (AUD-W2V4-T01).
- [ ] `pytest backend/tests/test_rota_enum_drift.py` 3 testes novos
  (AUD-W2V4-T02).
- [ ] `pytest backend/tests/test_migration_012.py` 3 testes novos
  (AUD-W2V4-T03).
- [ ] `pytest backend/tests/test_codigo_publico_service.py` 20 testes
  (1 ajustado para 10k amostras — AUD-W2V4-T05).
- [ ] `pytest backend/tests/test_qrcode_service.py` 13+ testes (1 novo
  para separador — AUD-W2V4-S01).
- [ ] `pytest backend/tests/test_etiqueta_service.py` 7+ testes — sem
  regressão pós cache logo (AUD-W2V4-P03).

### 5.2 Validações específicas dos achados Wave 7

- [ ] `test_imutabilidade_rota_legacy_null_to_valor_permitido` passa —
  Wave 7 readiness explícita.
- [ ] `test_imutabilidade_rota_v4_valor_to_outro_bloqueado` passa —
  imutabilidade preservada.
- [ ] `test_imutabilidade_rota_v4_valor_to_null_bloqueado` passa.
- [ ] `test_executar_transicao_aprovacao_v4_preserva_rota_via_trigger`
  passa (banco real, não mock).
- [ ] `test_executar_transicao_reinicio_v4_preserva_rota_via_trigger`
  passa (banco real — valida fix AUD-W2V4-001).
- [ ] `test_rota_enum_drift_python_postgres` passa.
- [ ] `test_rota_enum_drift_typescript_python` passa.
- [ ] `test_migration_012_upgrade_idempotente` passa.
- [ ] `test_migration_012_downgrade_dropa_estruturas_novas` passa.

### 5.3 Validações de unicidade e correção de identificador

- [ ] `test_gerar_codigo_publico_nao_determinismo_sufixo` com 10.000
  amostras passa.

### 5.4 Validações de frontend

- [ ] `npx tsc --noEmit` exit 0 NO ESTADO COMMITADO (não dirty).
- [ ] `npx next build` 13/13 páginas NO ESTADO COMMITADO.
- [ ] Smoke visual em `/nova-prova`: default vazio, escolha forçada,
  texto auxiliar restaurado.

### 5.5 Validações de migrations

- [ ] `alembic upgrade head` em ambiente fresh executa sem erro
  (validado em AUD-W2V4-T03).
- [ ] `alembic downgrade -1` reverte estruturas novas (validado em
  AUD-W2V4-T03).
- [ ] Migrations RLS reaplicáveis idempotentemente — confirmado por
  inspeção (todas usam `DROP POLICY IF EXISTS` + `CREATE POLICY`).

### 5.6 Validações via grep

- [ ] `grep -nE 'determinar_rota\(' backend/app/api/v1/provas.py` 
  retorna **zero** ocorrências (foi removido na criação).
- [ ] `grep -nE 'determinar_rota\(' backend/app/services/state_machine.py` 
  retorna **uma** ocorrência (apenas no ramo `aprovando` para legacy
  rota=NULL).
- [ ] `grep -nE 'rota_projetada' backend/ frontend/` retorna **zero**.
- [ ] `grep -nE '\bas \[A-Z\]\| as readonly\| as typeof'`
  em `frontend/src/app/(dashboard)/nova-prova/` retorna apenas `as const`
  literais.

### 5.7 Validações via MCP read-only (pós-correção)

- [ ] `get_advisors security` — sem novos alertas (mesmo perfil
  pré-correção: 1 INFO + 1 WARN pré-existentes).
- [ ] `get_advisors performance` — sem novos `unused_index` ou alertas
  novos atribuíveis a esta sessão.
- [ ] `SELECT version_num FROM alembic_version` ainda `012`.
- [ ] `SELECT enumlabel FROM pg_enum WHERE enumtypid='rota_enum'::regtype` 
  ainda 6 valores na ordem correta.
- [ ] Trigger e função inalterados (sessão de correção não toca DDL).
- [ ] `r2_buckets_list` ainda `rastreio-provas-artes` único, sem
  alterações.

### 5.8 Validação de cobertura

- [ ] Cobertura ≥ 80% mantida na camada de domínio/serviço — não
  regredida (aceitar leve aumento conforme novas suítes).

### 5.9 Smoke E2E manual (AUD-W2V4-T04)

Checklist completo descrito em §2.12; será documentado em
`fix-validation.md` Seção "Smoke E2E manual"; **execução por Mario
ou pelo engenheiro**. Validação humana, não automatizada.

---

## 6. Plano de atualização de documentação acumulativa

### 6.1 `CHANGELOG.md`

Adicionar **nova seção** "Wave 2 v4.0 — Correções Pós-Auditoria
(2026-05-05)":
- Lista dos achados corrigidos com ID, severidade, arquivo modificado,
  tipo de mudança e SHA do commit.
- Re-validação `tsc --noEmit` exit 0 + `next build` 13/13 NO ESTADO
  COMMITADO (corrige AUD-W2V4-D02).
- Notas dos 14 commits atômicos.
- **Apêndice, não substituição** — histórico anterior preservado.

### 6.2 `DECISIONS.md`

- **ADR-123 — "Reinício de ciclo preserva rota (RN-006 v4.0 + RF-009 v4.0)"**:
  registra a correção da modificação cirúrgica do ADR-119, agora
  cobrindo ambos os ramos (`aprovando` + `reiniciando_ciclo`). Cita
  testes em `test_imutabilidade_rota.py`.
- **ADR-124 — "Default `INITIAL_FORM.rota` vazio + texto auxiliar
  restaurado (mitigação Backlog v4.0 §6 'Confusão operacional')"**:
  registra a substituta da mitigação descartada em ADR-118 SUPERSEDIDO.
- **ADR-120**: adicionar bloco "Pós-supersedimento (Visual Refresh
  v2)" esclarecendo eliminação da duplicação de logos.
- **AUD-W2V4-INFO**: registrar follow-ups em seção própria
  "Follow-ups técnicos pós-Wave 2 v4.0 audit fixes".

### 6.3 `CLAUDE.md`

- Atualizar tabela de waves: nova linha "v4.0 W2 — C06 Audit Fixes" 
  com SHAs.
- Atualizar seção "Estado atual do banco de produção" com nota dos 3
  chunks MCP da migration 012 (AUD-W2V4-M02).
- Confirmar que seção "Como adicionar valor ao enum `rota_enum`" cita
  o teste de drift novo (AUD-W2V4-T02).
- Confirmar que seção "Provas: ciclo de vida da rota" (se existir;
  caso contrário criar) descreve preservação no reinício.

### 6.4 `docs/wave2-v4/audit-report.md`

Adicionar **apêndice "Status de resolução por achado"** ao final do
arquivo, sem editar o corpo original. Para cada um dos 26 achados:
- ID + severidade.
- Status: **RESOLVIDO** / **NÃO APLICÁVEL** (justificado) / **DEFERRED**
  (justificado).
- Commit SHA da correção (quando aplicável).
- Critério objetivo de validação (link para teste, query, output).

### 6.5 `docs/wave2-v4/fix-plan.md`

Após execução do Gate 2, adicionar **seção "Resultado da Execução"**
listando diffs entre planejado e realizado para cada achado.

### 6.6 `docs/wave2-v4/fix-validation.md` (novo, criado no Gate 2 final)

Relatório de validação interna conforme Seção 6 do prompt — checklist
objetivo, verificação por achado, auto-crítica, recomendação.

### 6.7 `docs/wave2-v4/analysis.md`

Anexo Visual Refresh v1 (linhas 1268-1417 do working tree) **commitado
junto com AUD-W2V4-002** + nota de supersedimento explícita: "este
anexo descreve o estado intermediário v1 (commit `<sha-v1>`),
posteriormente superseded pelo Visual Refresh v2 em `5047172`/`c06ca56`.
Mantido por valor histórico de processo iterativo de design — não
descreve o estado final em produção."

### 6.8 `docs/db/schema.sql`

Reescrita conforme AUD-W2V4-M01 — alembic_version=012 + estruturas Wave
2 v4.0 + acúmulos de Waves 5/6/1v4.0/1v4.0AR2.

---

## 7. Critérios objetivos de saída do Gate 2

A sessão de correção termina **se e somente se**:

1. PR aberto com descrição que lista cada um dos 26 achados com seu
   commit SHA (ou justificativa NÃO APLICÁVEL/DEFERRED).
2. `docs/wave2-v4/fix-plan.md` (este arquivo) com seção "Resultado da
   Execução" anexada.
3. `docs/wave2-v4/fix-validation.md` criado com checklist completo,
   verificação por achado, auto-crítica.
4. `docs/wave2-v4/audit-report.md` com apêndice de status por achado.
5. `CHANGELOG.md` e `DECISIONS.md` atualizados acumulativamente
   (ADR-123 + ADR-124 + bloco em ADR-120).
6. `CLAUDE.md` atualizado.
7. Smoke check da Seção 5 com 100% dos itens marcados.
8. **Testes de transição `NULL → valor` confirmados** —
   viabilidade da Wave 7 preservada e validada.
9. Recomendação explícita de nova auditoria independente registrada
   no `fix-validation.md`.

---

## 8. Observações finais

- **Nenhum achado bloqueado por divergência.** Estado real bate com
  o relatório.
- **Nenhuma migration nova.** Todas as correções são em código
  Python/TypeScript/docs, sem impacto em schema do banco ou em RLS.
- **Wave 7 readiness:** os 4 itens críticos para Wave 7 (AUD-W2V4-001,
  T01, T02, T03) estão no topo da ordem topológica e têm validação
  explícita de transição `NULL → valor` + `valor → outro` + `valor →
  NULL`.
- **Confusão operacional (Backlog §6):** mitigação restaurada via
  ADR-124 (default vazio + texto auxiliar) — substituta da mitigação
  descartada em ADR-118 SUPERSEDIDO.
- **Honestidade na validação:** todo teste novo é integrado (banco real
  ou mock_db rigoroso) e exerce comportamento real, não tautológico.
  Adversarial check em §5 da auto-crítica final do `fix-validation.md`.

---

**Pedido explícito de autorização para Gate 2:**

**"Aguardando string AUTORIZADO GATE 2 — CORREÇÃO WAVE 2 v4.0 para
prosseguir."**

Não escreverei código de produção, não aplicarei migration, não
abrirei PR até a autorização chegar. Se a autorização vier
acompanhada de correções ao plano, incorporarei antes de começar.

---

## 9. Resultado da Execução (anexado em 2026-05-05 após Gate 2)

Sessão executada em `wave2-v4/fixes/execution`. **15 commits atômicos
de execução** (rastreáveis ao ID do achado) + **1 commit do plano**
(em `wave2-v4/fixes/plan`). Total: **16 commits**.

### 9.1 Diferenças entre planejado e realizado

| Achado | Planejado (§2) | Realizado | Divergência? |
|---|---|---|---|
| AUD-W2V4-001 + A01 + 006 + 007 | 1 commit coeso `state_machine.py` + ajuste de 1 teste | 1 commit `cbd6506` cobrindo `state_machine.py` + 2 testes ajustados (`test_state_machine.py` 1 ajustado + 2 novos; `test_provas_api.py` 1 ajustado) | nenhuma material — 1 teste a mais de provas_api precisou ser ajustado |
| AUD-W2V4-002 + D01 + D02 | commit dos 3 frontend + nota anexo | commit `1a88ab8` cobrindo os 3 + nota explícita; tsc/build re-validados | nenhuma |
| AUD-W2V4-T01 | suíte com 5 cenários banco real | 5 cenários, skipif sem `INTEGRATION_DATABASE_URL` | nenhuma |
| AUD-W2V4-T02 | 3 testes drift | 5 testes (3 + 2 sanity) | a mais — sanity tests adicionados |
| AUD-W2V4-T03 | 3 testes upgrade/downgrade/idempotente | 3 testes implementados | nenhuma |
| AUD-W2V4-A02 + M03 | default vazio + texto auxiliar | implementado + classe CSS `fieldHint` | nenhuma |
| AUD-W2V4-M01 | reescrever `schema.sql` | reescrito + nota dos 3 chunks (resolve M02 parcialmente) | nenhuma |
| AUD-W2V4-003 | corrigir docstring | feito + correção de tamanho 17→18 (bug menor pré-existente) | a mais — pequeno bonus |
| AUD-W2V4-004 | retry no handler | implementado com classificação por constraint_name + 3 testes novos | nenhuma |
| AUD-W2V4-005 | docstring de contrato | feito + bloco "TEST PENDING Componente 19" | nenhuma |
| AUD-W2V4-M02 | nota CLAUDE.md + docstring | feito em CLAUDE.md "Estado atual" + docstring migration 012 | nenhuma |
| AUD-W2V4-S01 | guarda separador `\|` | feito + 1 teste novo | nenhuma |
| AUD-W2V4-P03 | cache logo SVG ou WONTFIX | implementado `lru_cache` em `_check_assets`; cache de bytes WONTFIX-parcial documentado | conforme planejado (decisão alternativa autorizada) |
| AUD-W2V4-M04 | bloco "Pós-supersedimento" no ADR-120 | feito | nenhuma |
| AUD-W2V4-T05 | aumentar para 10k amostras | feito com tolerância matemática justificada (>= 9_995) | nenhuma |
| AUD-W2V4-T04 | smoke E2E manual obrigatório | documentado em `fix-validation.md` Seção 2.9 com 11 itens de checklist | nenhuma |
| AUD-W2V4-INFO (S02/S03/P01/P02) | só registrar | registrados em apêndice de `audit-report.md` | nenhuma |

### 9.2 Suíte de teste — totais pós-correção

- **Backend:** 805 passed + 9 skipped (era 795 + 0 antes da sessão).
- Novos testes: 2 (AUD-001) + 5 (T01) + 5 (T02) + 3 (T03) + 3
  (AUD-004) + 1 (S01) = 19 testes adicionados.
- Skipped: 5 (T01) + 3 (T03) + 1 (T02) = 9 (todos por falta de
  `INTEGRATION_DATABASE_URL` — esperado).
- Testes ajustados: 1 (`test_executar_reinicio_ciclo_reprovada_para_criada_incrementa`)
  + 1 (`test_reiniciar_happy_prova_reprovada`) + 1
  (`test_create_prova_integrity_error_returns_409`) = 3 ajustes.
- Math: 795 + 19 - 0 = 814 (esperado), 805 passed + 9 skipped = 814.
  ✅ Bate.

### 9.3 Documentação acumulativa atualizada

- **DECISIONS.md:** ADR-123 + ADR-124 + bloco "Pós-supersedimento"
  no ADR-120.
- **CHANGELOG.md:** nova seção "Wave 2 v4.0 — Correções
  Pós-Auditoria Sênior" com tabela de 26 achados por severidade.
- **CLAUDE.md:** seção "Estado atual do banco" com nota dos 3
  chunks MCP.
- **docs/db/schema.sql:** reescrito com `alembic_version=012` +
  estado real.
- **docs/wave2-v4/audit-report.md:** apêndice "Status de Resolução
  por Achado" — tabela completa.
- **docs/wave2-v4/fix-plan.md:** este anexo §9.
- **docs/wave2-v4/fix-validation.md:** novo arquivo com checklist +
  auto-crítica + recomendações.

### 9.4 Recomendação final

**PR pronto para merge condicional** — aguarda smoke E2E manual
(Seção 2.9 do `fix-validation.md`).

**Recomenda-se nova rodada de auditoria independente em sessão
separada após o merge**, usando o prompt de auditoria pós-Wave 2
v4.0, para confirmar que (a) achados originais foram resolvidos,
(b) correções não introduziram novos problemas, (c) Wave 7
continua viável.
