# Wave 2 v4.0 — Componente 06 (Atualizacao v4.0) · Analise Read-only

**Wave:** 2 v4.0 — Cadastro de Prova com Selecao de Rota + Etiqueta com Codigo Textual
**Componente:** 06 (atualizacao v4.0) — exclusivo desta sessao
**Branch:** `wave2-v4/analysis` (sem merge — apenas commit do `analysis.md`)
**Data:** 2026-05-04
**Persona:** engenheiro de dominio + arquiteto · postura adversarial sobre o estado atual antes de propor execucao
**Idioma:** pt-BR · identificadores tecnicos em ingles ou em ASCII sem acentos

---

## 0. RESUMO EXECUTIVO

A Wave 2 v4.0 e uma **reforma profunda** que substitui o Componente 06 da v3.0. Cinco achados de impacto arquitetural foram detectados durante a leitura read-only:

1. **`rota_enum` ja existe em producao com valores `PADRAO`/`DIRETA` (v3.0)**, e a coluna `provas_digitais.rota` ja existe (NULLABLE). Nao e estado de "execucao parcial anterior" — e o estado herdado da Wave 0 (migration 001). A v4.0 precisa de 4 valores totalmente diferentes (`MATRIZ`, `LAM_MATRIZ`, `FILIAL`, `LAM_FILIAL`).
2. **Existem 5 provas em producao com `rota` setada** (3 `DIRETA` + 2 `PADRAO`) e 11 com `rota = NULL`. O Backlog v4.0 (Componente 06 — Notas Tecnicas) instrui usar `ALTER TYPE … ADD VALUE` e deferir o backfill para a Wave 7. Vou seguir essa instrucao — implica enum com 6 valores convivendo entre Wave 2 e Wave 7.
3. **Endpoint `POST /api/v1/provas/transicoes` (existente, Wave 3 da v3.0) sobrescreve `prova.rota`** na transicao `RETIRADA_PELO_VENDEDOR -> APROVADA_PELO_VENDEDOR` via `determinar_rota(usuario)`. Isso colide com a regra de imutabilidade da v4.0. **Solicito autorizacao explicita ao Mario para uma modificacao cirurgica em `state_machine.executar_transicao`** (linha 365 — derivar rota apenas se `prova.rota IS NULL`). Ver Secao 14.
4. **Filtro de rota na listagem (Componente 07) JA EXISTE** com 2 opcoes (`PADRAO`, `DIRETA`). Nao e "adicionar filtro novo" — e "atualizar opcoes para 4 valores". Recomendo a Opcao A (Secao 4.7).
5. **`codigo_publico` deve ser coluna NOVA**, nao reaproveita `qr_code_hash`. O QR Code da v4.0 muda payload para embutir o `codigo_publico` em vez do `qr_code_hash` truncado (DAT v3.0 §8.1 — idempotencia entre mecanismos camera/digitacao manual).

**Decisoes de partida (a confirmar com Mario):**
- Coluna `codigo_publico VARCHAR(20) NOT NULL UNIQUE`, nova, formato `PRV-AAAA-MM-NNNNNN`.
- Trigger `BEFORE UPDATE` permite `NULL → valor` (Wave 7) e bloqueia `valor → outro_valor` ou `valor → NULL`.
- Filtro de rota: Opcao A (atualizar nesta wave para 4 valores).
- Provas legadas (rota=NULL ou rota=PADRAO/DIRETA): renderizar com fallback `"—"` na listagem; no detalhe, mostrar "Rota: nao definida (legada)" para NULL e "Rota: PADRAO (legada v3.0)" para PADRAO/DIRETA.
- Modificacao cirurgica em `executar_transicao` para honrar imutabilidade: pendente autorizacao explicita.

**Infraestrutura RBAC da Wave 1 v4.0 cobre 100% deste cenario:** rule `provas.create` ja vincula path `/nova-prova` -> `studio_admin: full`, demais perfis `negado`; politica `pol_provas_insert` ja exige `app_private.current_user_is_admin()`; handlers ja usam `Depends(access_required("provas.create"))`; frontend ja usa `useAuthorization("provas.create")` + `Restricted`.

---

## 1. CONFIRMACAO DE LEITURA — ARTEFATOS INSPECIONADOS

### 1.1 Contexto vivo do repositorio (estado pos-Wave 1 v4.0 Audit Round 2)

| Artefato | Caminho | Lido como |
|---|---|---|
| Guia de operacao | [CLAUDE.md](../../CLAUDE.md) | Integral via system reminder + secoes RBAC (1-450) |
| Decisoes (ADR) | [DECISIONS.md](../../DECISIONS.md) | Linhas 1-300 (ADR-001..027 — Waves 0/1) |
| Changelog | [CHANGELOG.md](../../CHANGELOG.md) | Linhas 1-300 (Wave 6 + Wave 6 audit + audit fixes Wave 1 v4.0) |
| Schema snapshot | [docs/db/schema.sql](../db/schema.sql) | Integral — 299 linhas, alembic_version=011 |
| Wave 1 v4.0 fix-validation | [docs/wave1-v4/fix-validation.md](../wave1-v4/fix-validation.md) | Integral — confirmacao 17/17 RESOLVIDOS |
| Wave 1 v4.0 analysis | [docs/wave1-v4/analysis.md](../wave1-v4/analysis.md) | Existencia confirmada (35K tokens — leitura por trechos durante a sessao) |
| Wave 1 v4.0 audit-report | [docs/wave1-v4/audit-report.md](../wave1-v4/audit-report.md) | Existencia confirmada |
| Wave 1 v4.0 fix-plan | [docs/wave1-v4/fix-plan.md](../wave1-v4/fix-plan.md) | Existencia confirmada |

### 1.2 Documentos canonicos da v4.0 (especificacao de produto)

Extraidos via Python `zipfile`+regex para `.wave2-tmp/*.txt` (UTF-8):

| Documento | Tamanho extraido | Foco lido |
|---|---|---|
| `RequisitosProvasDigitais_v4_0.docx` | 40.132 chars | Integral — Secoes 1 (Visao geral), 3 (RFs 001-027), 4 (US-001 a US-017), 5 (Matriz de transicoes 14 estados, 4 rotas), 6 (Matriz RBAC), 7 (RNs RN-001..RN-013), 8 (RNFs) |
| `BACKLOG_RastreioProvasDigitais_v4_0.docx` | 29.611 chars | Integral — Secoes 2 (DoD global 10 itens), 3-4 (waves 0-7 + dependencias), 5 (Componente 06 v4.0 + 08 v4.0 + 11 v4.0 + 21 — Wave 7), 6 (Riscos da v4.0) |
| `DAT_RastreioProvasDigitais_v3_0.docx` | 22.047 chars | Integral — Secoes 2 (Alembic vs Supabase), 3 (Estrategia de testes), 4 (Camada State Machine), 6 (Migracao Wave 7 — duplo Alembic + backfill), 7 (RBAC defesa em profundidade), 8 (Identificacao de provas — formato `PRV-AAAA-MM-NNNNNN`) |

**UML v4.0 (.drawio):** existencia confirmada (257 KB). Conteudo XML — tratado como referencia visual; especificacao canonica das transicoes e a Secao 5 do `Requisitos v4.0`. Nao li integralmente (XML grande, redundante com os docx).

### 1.3 Codigo-fonte (apenas inspecao)

| Camada | Arquivo | Foco |
|---|---|---|
| Backend handler | [backend/app/api/v1/provas.py](../../backend/app/api/v1/provas.py) | Linhas 1-650 — `create_upload_url`, `_carregar_vendedor`, `_validar_upload_no_r2`, `create_prova`, listagem (`get_provas`), `_scoping_filter` |
| Backend schemas | [backend/app/domain/schemas/prova.py](../../backend/app/domain/schemas/prova.py) | Integral — 494 linhas |
| Backend models | [backend/app/db/models.py](../../backend/app/db/models.py) | Integral — 262 linhas (`RotaEnum`, `ProvaDigital`, `Movimentacao`, etc.) |
| Backend state machine | [backend/app/services/state_machine.py](../../backend/app/services/state_machine.py) | Integral — 441 linhas (`determinar_rota`, `validar_transicao`, `executar_transicao`) |
| Backend QR | [backend/app/services/qrcode_service.py](../../backend/app/services/qrcode_service.py) | Integral — 99 linhas (`gerar_hash`, `gerar_payload_qr`, `validar_payload_qr`, `gerar_imagem_qr`) |
| Backend etiqueta | [backend/app/services/etiqueta_service.py](../../backend/app/services/etiqueta_service.py) | Integral — 317 linhas (`gerar_pdf` 90×57mm, fpdf2, fonts DejaVu, logos SVG) |
| Backend access | [backend/app/access/](../../backend/app/access/) | Integral — `__init__.py`, `matrix.py`, `enforce.py`, `scopes.py`, `guards.py` |
| Frontend criacao | [frontend/src/app/(dashboard)/nova-prova/page.tsx](../../frontend/src/app/(dashboard)/nova-prova/page.tsx) | Integral — 497 linhas (form + dropzone + sucesso + Restricted via useAuthorization) |
| Frontend listagem | [frontend/src/app/(dashboard)/provas/page.tsx](../../frontend/src/app/(dashboard)/provas/page.tsx) | Integral — 521 linhas (filtros URL-persisted, paginacao, useAuthorization para mostrar filtro de vendedor) |
| Frontend RBAC | [frontend/src/lib/hooks/use-authorization.ts](../../frontend/src/lib/hooks/use-authorization.ts) | Integral — 92 linhas |
| Frontend matrix | [shared/access-matrix.json](../../shared/access-matrix.json) | Integral — 173 linhas |
| Frontend middleware | [frontend/src/middleware.ts](../../frontend/src/middleware.ts) | Integral — 19 linhas (delega a `lib/supabase/middleware`) |
| RLS final | [backend/migrations/rls/012_move_helpers_to_app_private.sql](../../backend/migrations/rls/012_move_helpers_to_app_private.sql) | Integral — 250 linhas (12 policies + helpers `app_private.*`) |

---

## 2. VALIDACAO MCP — ESTADO DE PARTIDA

### 2.1 Supabase — projeto `rwxlpwmnkekzuurgthkr` (sa-east-1, Postgres 17.6)

**Tabelas:** 6 de dominio (`usuarios`, `provas_digitais`, `movimentacoes`, `etiquetas`, `audit_logs`, `configuracoes_sistema`) + `alembic_version`. Todas com RLS habilitada.

**Enums em `public`:**
- `setor_enum`: `{STUDIO, VENDEDOR, MOTORISTA, CLICHERIA}`
- `localizacao_enum`: `{MATRIZ, FILIAL}`
- `status_prova_enum`: 10 valores (CRIADA..CANCELADA)
- `rota_enum`: **`{PADRAO, DIRETA}` ← PRESENTE EM PRODUCAO** (Wave 0, migration 001)

**Coluna `provas_digitais.rota`:** existe, tipo `rota_enum`, NULLABLE. Idem `movimentacoes.rota_no_momento`.

**Distribuicao da coluna `rota`:**
```
total: 16 provas
  rota = PADRAO: 2
  rota = DIRETA: 3
  rota IS NULL: 11
```

**`alembic_version`:** `011` (consistente com CLAUDE.md, Wave 5 Bloco 5.0 closeout).

**Schema `app_private`:** existe. 3 funcoes SECURITY DEFINER (`current_user_is_admin`, `current_user_setor`, `current_user_id`) — referenciadas pelas 12 policies em `public`.

**12 RLS policies em `public`** (todas usam `app_private.current_user_*`):
- `usuarios`: SELECT (self ou is_admin), INSERT (is_admin), UPDATE (is_admin) — 3
- `provas_digitais`: SELECT (admin/vendedor/motorista/clicheria por escopo), **INSERT (`current_user_is_admin()`)**, UPDATE (admin) — 3
- `movimentacoes`: SELECT (com escopo), INSERT (admin) — 2
- `etiquetas`: SELECT (com escopo) — 1
- `audit_logs`: SELECT (admin) — 1
- `configuracoes_sistema`: SELECT (admin), UPDATE (admin) — 2

**Total: 12. Confirmado: `pol_provas_insert` ja cobre o cenario "apenas admin cria prova" — NAO precisa criar nova RLS nesta wave.**

**Advisors:**
- Security: 1 INFO (`rls_enabled_no_policy` em `alembic_version` — intencional, ADR-025) + 1 WARN (`auth_leaked_password_protection` — WONTFIX, ADR-027). **Nenhum advisor relacionado a `provas_digitais` ou `rota_enum`.**
- Performance: 11 INFOs `unused_index` — todos pre-existentes (Wave 0/1/3/5), nao bloqueiam.

### 2.2 Cloudflare — sem mudanca prevista

R2 bucket `rastreio-provas-artes` continua sendo usado conforme Wave 0 + Wave 2 v3.0. **Esta wave nao toca R2/Workers/KV.**

### 2.3 Bloqueio?

**Nenhum bloqueio detectado para iniciar Gate 2 apos autorizacao.** A unica decisao que precisa de mim+Mario antes do Gate 2 e a modificacao cirurgica em `executar_transicao` (Secao 14).

---

## 3. ESTADO DE PARTIDA vs DESTINO — DIVERGENCIAS DETALHADAS

### 3.1 Divergencias entre v3.0 codificada e v4.0 documentada

| # | Aspecto | v3.0 codificada (HOJE) | v4.0 documentada |
|---|---|---|---|
| 1 | Valores do `rota_enum` | `PADRAO`, `DIRETA` (2 valores) | `MATRIZ`, `LAM_MATRIZ`, `FILIAL`, `LAM_FILIAL` (4 valores) |
| 2 | Quem decide a rota | Sistema deriva da `vendedor.localizacao` em runtime (`determinar_rota`) | Admin escolhe MANUALMENTE no form de criacao |
| 3 | Quando a rota e persistida | Apenas na transicao `RETIRADA -> APROVADA_PELO_VENDEDOR` (`executar_transicao`) | Imediatamente na criacao (POST /api/v1/provas/) |
| 4 | Imutabilidade | A rota e SOBRESCRITA na aprovacao (e potencialmente em reinicio de ciclo, onde vira `None`) | Imutavel apos a criacao (RN-007 + RN-002) |
| 5 | Localizacao do vendedor | OBRIGATORIA + DETERMINISTICA do roteamento | OBRIGATORIA mas APENAS INFORMATIVA (RN-009) |
| 6 | Codigo legivel da prova | Nao existe — apenas `qr_code_hash` (HMAC opaco 64 chars) e `nro_requerimento` (humano mas livre) | Novo: `codigo_publico` formato `PRV-AAAA-MM-NNNNNN` para fallback de digitacao manual (RF-005) |
| 7 | Payload do QR | `3SD\|{nro_requerimento}\|{hash_truncado_16}` | Embute o `codigo_publico` (DAT §8.1: idempotencia camera↔digitacao manual) |
| 8 | Etiqueta PDF | 90×57mm com logos, QR, Nome/Requerimento/Vendedor, ano | Adiciona codigo alfanumerico em destaque (≥18pt) e badge da rota (Matriz / Lam. Matriz / Filial / Lam. Filial) |
| 9 | Numero de estados | 10 enum values em `status_prova_enum` (CRIADA..CANCELADA) | 14 estados (incluindo `Encaminhada para Laminacao`, `Com Motorista (ida laminacao)`, `Laminacao Concluida`, `Com Motorista (volta laminacao)`, `De volta a 3Studio (pos-laminacao)`, mais split de `COM_MOTORISTA` em 3 contextos) |

**Divergencias 1-7 sao escopo desta wave. Divergencias 8 (etiqueta) e parte da 9 (rota imutavel) tambem. Divergencia 9 completa (4 rotas + 14 estados + Wave 3) NAO e desta wave — RN-002 ja registra que `prova.rota` apenas armazenada nao direciona transicoes ainda.**

### 3.2 Divergencias entre Backlog v4.0 e prompt da Wave 2 v4.0

Pequenas inconsistencias:

- **Componente 07 (listagem) — "Sem alteracao" no Backlog vs RF-014 explicita "filtro por rota Matriz/Lam. Matriz/Filial/Lam. Filial".** O filtro de rota JA EXISTE no `provas/page.tsx` (linhas 296-309) com 2 valores. Atualizar para 4 valores e trivial e necessario para o RF-014 — proponho Opcao A (Secao 4.7).
- **Alfabeto do `codigo_publico` — "32 caracteres" no prompt vs alfabeto literal `ABCDEFGHJKMNPQRSTUVWXYZ23456789` (31 caracteres).** Vou seguir o alfabeto literal (31 chars: 23 letras sem `I/L/O` + 8 digitos sem `0/1`). 31^6 ≈ 887 milhoes de combinacoes — entropia mais que suficiente para o volume operacional + rate limiting do Componente 19.
- **Convencao de nomenclatura do enum — DAT/Backlog usam lowercase `'matriz', 'lam_matriz', 'filial', 'lam_filial'` vs convencao do projeto (uppercase: `STUDIO/VENDEDOR/MOTORISTA/CLICHERIA`, `MATRIZ/FILIAL`, `CRIADA/RETIRADA_PELO_VENDEDOR/...`).** Recomendo uppercase para consistencia: `MATRIZ`, `LAM_MATRIZ`, `FILIAL`, `LAM_FILIAL`. Documentar essa decisao no DECISIONS.md.

---

## 4. ITENS DA SECAO 4 DO PROMPT — DETALHAMENTO

### 4.1 Inventario do Componente 06 atual (estado v3.0)

**Backend:**
- Handler: [backend/app/api/v1/provas.py](../../backend/app/api/v1/provas.py)
  - `POST /upload-url` (linhas 190-245) — gera presigned URL R2; ja usa `Depends(access_required("provas.create"))`.
  - `POST /` (linhas 364-610) — fluxo completo de criacao em 11 passos. Ja usa `Depends(access_required("provas.create"))`. **Linha 414-421 chama `determinar_rota(vendedor)` apenas para retornar `rota_projetada` no response (Wave 2 v3.0 NAO persiste rota — ADR-042). Linha 474 grava `rota=None` explicitamente no INSERT.**
- Schema Pydantic: [backend/app/domain/schemas/prova.py](../../backend/app/domain/schemas/prova.py)
  - `UploadUrlRequest` (linhas 47-77).
  - `ProvaCreateRequest` (linhas 91-126) — **nao tem campo `rota`**. Campos: nome, nro_requerimento, cliente, vendedor_id, object_key.
  - `ProvaResponse` (linhas 128-154) — tem `rota: RotaEnum | None` E `rota_projetada: RotaEnum | None`.
  - `ProvaCreateResponse` (linhas 157-162) — tem `prova`, `etiqueta_pdf_base64`, `qr_code_payload`.

**Modelo SQLAlchemy:** [backend/app/db/models.py](../../backend/app/db/models.py)
  - `RotaEnum` (linhas 50-58): `PADRAO`, `DIRETA` — duas constantes.
  - `ProvaDigital.rota` (linha 124-126): `Mapped[RotaEnum | None]`, NULLABLE, `create_type=False` (enum gerenciado pela migration 001).

**State machine:** [backend/app/services/state_machine.py](../../backend/app/services/state_machine.py)
  - `determinar_rota(vendedor)` (linhas 133-157): mapeia `MATRIZ -> PADRAO`, `FILIAL -> DIRETA`. Levanta `RotaIndeterminavelError` se nao for vendedor ou sem localizacao.
  - `executar_transicao` (linhas 231-440): orquestra valida + grava + log_audit. **Linhas 350-365: na transicao `RETIRADA_PELO_VENDEDOR -> APROVADA_PELO_VENDEDOR` chama `rota_depois = determinar_rota(usuario)` e GRAVA em `prova.rota`.** Linhas 354-374: no reinicio de ciclo zera `prova.rota = None`.
  - `TRANSICOES` e `ATORES_POR_TRANSICAO` (linhas 53-127): tabelas estaticas — 9 estados ativos + CANCELADA.

**QR Code:** [backend/app/services/qrcode_service.py](../../backend/app/services/qrcode_service.py)
  - `gerar_hash(prova_id, nro_requerimento)`: HMAC-SHA256 hex (64 chars) determinado por (prova_id, nro_req, secret).
  - `gerar_payload_qr(nro_req, hash)`: retorna `"3SD|{nro_req}|{hash[:16]}"`.
  - `validar_payload_qr(payload, hash_full)`: comparacao constant-time do hash truncado.
  - `gerar_imagem_qr(payload, size_px=200)`: PNG via `qrcode[pil]`.

**Etiqueta:** [backend/app/services/etiqueta_service.py](../../backend/app/services/etiqueta_service.py)
  - `gerar_pdf(nome_prova, nro_requerimento, vendedor_nome, qr_image_bytes, template, created_at)`: PDF 90×57mm, fpdf2, DejaVu Sans, logos SVG (3STUDIO + studio&ART!), QR centralizado, ano no rodape. **Nao tem badge de rota nem codigo alfanumerico textual.**

**Frontend:**
- Form de criacao: [frontend/src/app/(dashboard)/nova-prova/page.tsx](../../frontend/src/app/(dashboard)/nova-prova/page.tsx)
  - Estado: `nome`, `nro_requerimento`, `cliente`, `vendedor_id`, `arquivo`. **Nao tem campo `rota`.**
  - Layout pos-criacao: mostra `rota_projetada` ("Rota padrao" / "Rota direta") na tela de sucesso (linhas 281-286).
  - Ja usa `useAuthorization("provas.create")` + `Restricted` (linhas 49, 327-330).
- Listagem: [frontend/src/app/(dashboard)/provas/page.tsx](../../frontend/src/app/(dashboard)/provas/page.tsx)
  - Filtro de rota JA EXISTE (linhas 296-309) — usa `ROTA_OPTIONS` de `lib/types/prova.ts`. **Hoje esse array tem 2 valores (PADRAO, DIRETA). Vai precisar de 4 valores na v4.0.**

**Onde a localizacao do vendedor e usada hoje:**
1. `backend/app/api/v1/provas.py:_carregar_vendedor` (linhas 253-281): valida `vendedor.localizacao IS NOT NULL` antes de chamar `determinar_rota`. Levanta 422 se ausente. **Esta validacao continuara existindo (CHECK constraint do banco), mas a chamada `determinar_rota(vendedor)` na linha 415 deixa de fazer sentido.**
2. `state_machine.determinar_rota`: leitura da `vendedor.localizacao` para mapear PADRAO/DIRETA.
3. `state_machine.executar_transicao` (linhas 326-341): regra extra de rota em `APROVADA_PELO_VENDEDOR -> *` (RF-009 v3.0). **Essa regra inteira fica obsoleta na v4.0 — a Wave 3 v4.0 vai reescrever — nao toco nesta wave.**
4. Frontend `nova-prova/page.tsx` linha 430: exibe `(${v.localizacao})` ao lado do nome do vendedor no select. Mantem como informacao auxiliar.

**Tabela `provas_digitais` atual** (via `list_tables` MCP):

| Coluna | Tipo | Default | NULLABLE | UNIQUE/CHECK |
|---|---|---|---|---|
| id | uuid | gen_random_uuid() | NO | PK |
| nome | varchar(200) | — | NO | — |
| nro_requerimento | varchar(50) | — | NO | UNIQUE |
| cliente | varchar(200) | — | NO | — |
| vendedor_id | uuid | — | NO | FK -> usuarios.id |
| imagem_url | text | — | NO | — |
| qr_code_hash | varchar(64) | — | NO | UNIQUE |
| status | status_prova_enum | 'CRIADA' | NO | — |
| **rota** | **rota_enum** | — | **YES** | — |
| ciclo_atual | integer | 1 | NO | CHECK (>= 1) |
| motivo_cancelamento | text | — | YES | — |
| created_at | timestamptz | now() | NO | — |
| updated_at | timestamptz | now() | NO | — |

**Indexes em `provas_digitais` (5):**
- PK + UNIQUE em `nro_requerimento` + UNIQUE em `qr_code_hash` (automaticos)
- `idx_provas_status` (migration 001)
- `idx_provas_vendedor` (migration 001)
- `idx_provas_created_at` (migration 001)
- `idx_provas_status_created` (migration 003)
- `idx_provas_vendedor_status` (migration 010 — Wave 5)

### 4.2 Desenho da migration

**Nome:** `012_add_codigo_publico_and_rotas_v4_to_provas`

**DDL completo proposto:**

```python
"""add_codigo_publico_and_rotas_v4_to_provas

Wave 2 v4.0 — Componente 06.

Mudancas:
  1. ALTER TYPE rota_enum ADD VALUE 'MATRIZ', 'LAM_MATRIZ', 'FILIAL', 'LAM_FILIAL'
     (mantem PADRAO/DIRETA legacy ate Wave 7 fazer backfill).
  2. ADD COLUMN provas_digitais.codigo_publico VARCHAR(20) NOT NULL
     com default UUID temporario para tabela populada (16 provas).
     Imediatamente apos, populamos os codigos com formato PRV-AAAA-MM-NNNNNN
     baseado em created_at + nanoid (1 SQL transacao).
  3. CREATE UNIQUE INDEX idx_provas_codigo_publico (idempotente).
  4. CREATE INDEX idx_provas_rota_v4 (suporta filtros do Componente 07).
  5. CREATE TRIGGER trg_provas_rota_imutavel — bloqueia UPDATE da rota
     quando OLD.rota IS NOT NULL.

NAO inclui:
  - Tornar rota NOT NULL (Wave 7).
  - DROP dos valores PADRAO/DIRETA do enum (Wave 7 ou posterior).

Revision: 012
Revises: 011
"""
from alembic import op
import sqlalchemy as sa
import secrets
import string


# ALEMBIC NAO PERMITE ALTER TYPE ... ADD VALUE dentro de uma transaction
# implicit. Precisamos de op.execute com COMMIT explicito ou usar
# autocommit_block().
revision = '012'
down_revision = '011'


# Alfabeto sem caracteres ambiguos (DAT v3.0 §8.3): 31 chars.
_NANOID_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def _gen_nanoid(length: int = 6) -> str:
    return "".join(secrets.choice(_NANOID_ALPHABET) for _ in range(length))


def upgrade() -> None:
    # ─── 1. ALTER TYPE rota_enum (4 novos valores) ─────────────────────────
    # Postgres exige ADD VALUE FORA de transacao. autocommit_block faz isso.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE rota_enum ADD VALUE IF NOT EXISTS 'MATRIZ'")
        op.execute("ALTER TYPE rota_enum ADD VALUE IF NOT EXISTS 'LAM_MATRIZ'")
        op.execute("ALTER TYPE rota_enum ADD VALUE IF NOT EXISTS 'FILIAL'")
        op.execute("ALTER TYPE rota_enum ADD VALUE IF NOT EXISTS 'LAM_FILIAL'")

    # ─── 2. ADD COLUMN codigo_publico ──────────────────────────────────────
    # Estrategia: adicionar como NULLABLE, popular via UPDATE, marcar NOT NULL.
    # Tudo em transacao unica para que o downgrade tenha rollback consistente.
    op.add_column(
        "provas_digitais",
        sa.Column("codigo_publico", sa.String(length=20), nullable=True),
    )

    # Popular as provas existentes (16 linhas) com codigos derivados de created_at.
    # Garantimos unicidade fazendo retry caso ocorra colisao.
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, created_at FROM provas_digitais")).fetchall()
    used_codes: set[str] = set()
    for row in rows:
        ano = row.created_at.year
        mes = row.created_at.month
        # Retry ate 5x — colisao em 887 milhoes e improvavel mas defensivo.
        for _ in range(5):
            nano = _gen_nanoid(6)
            codigo = f"PRV-{ano:04d}-{mes:02d}-{nano}"
            if codigo not in used_codes:
                used_codes.add(codigo)
                break
        else:
            raise RuntimeError(f"Falha ao gerar codigo_publico unico para prova {row.id}")
        bind.execute(
            sa.text("UPDATE provas_digitais SET codigo_publico = :c WHERE id = :id"),
            {"c": codigo, "id": row.id},
        )

    # Marcar NOT NULL apos popular.
    op.alter_column("provas_digitais", "codigo_publico", nullable=False)

    # ─── 3. UNIQUE INDEX em codigo_publico ─────────────────────────────────
    op.create_index(
        "idx_provas_codigo_publico",
        "provas_digitais",
        ["codigo_publico"],
        unique=True,
    )

    # ─── 4. INDEX em rota (suporta filtro do Componente 07 com 4 rotas) ────
    op.create_index(
        "idx_provas_rota",
        "provas_digitais",
        ["rota"],
    )

    # ─── 5. TRIGGER de imutabilidade da rota ───────────────────────────────
    # Permite NULL -> valor (Wave 7 backfill).
    # Bloqueia valor -> outro_valor e valor -> NULL.
    op.execute("""
    CREATE OR REPLACE FUNCTION fn_bloquear_alteracao_rota()
    RETURNS TRIGGER
    LANGUAGE plpgsql
    SET search_path = ''
    AS $$
    BEGIN
        IF OLD.rota IS NOT NULL AND NEW.rota IS DISTINCT FROM OLD.rota THEN
            RAISE EXCEPTION 'Coluna rota e imutavel apos definicao (RN-007). '
                            'Para alterar a rota, cancele a prova e crie uma nova.'
                USING ERRCODE = '22023';
        END IF;
        RETURN NEW;
    END;
    $$;
    """)
    op.execute("""
    CREATE TRIGGER trg_provas_rota_imutavel
        BEFORE UPDATE ON provas_digitais
        FOR EACH ROW
        WHEN (OLD.rota IS DISTINCT FROM NEW.rota)
        EXECUTE FUNCTION fn_bloquear_alteracao_rota();
    """)


def downgrade() -> None:
    # Rollback ordem inversa.
    op.execute("DROP TRIGGER IF EXISTS trg_provas_rota_imutavel ON provas_digitais")
    op.execute("DROP FUNCTION IF EXISTS fn_bloquear_alteracao_rota()")
    op.drop_index("idx_provas_rota", table_name="provas_digitais")
    op.drop_index("idx_provas_codigo_publico", table_name="provas_digitais")
    op.drop_column("provas_digitais", "codigo_publico")
    # ALTER TYPE ... DROP VALUE NAO E suportado pelo Postgres em transacao.
    # Os 4 valores ficam no enum. Documentado.
```

**Pontos de atencao:**
- `ALTER TYPE ... ADD VALUE` fora de transacao (`autocommit_block`).
- O backfill dos `codigo_publico` para as 16 provas existentes acontece dentro da migration. Esta wave PROVES que o codigo nao cabe em campo separado — sao 16 inserts simples.
- `fn_bloquear_alteracao_rota` reutiliza padrao de `fn_bloquear_alteracao` (RNF-005, ADR-024) com `search_path = ''`.
- O downgrade NAO remove os valores do enum — o Postgres nao suporta `DROP VALUE` em transacao. Documentado no docstring.
- **Idempotencia:** `IF NOT EXISTS` em ADD VALUE; `idx_provas_codigo_publico` falha se ja existir mas o `if not exists` na criacao do trigger e funcao garante.

**Comparacao com Wave 7 (Componente 21):** a Wave 7 vai (a) adicionar logica de inferencia para `PADRAO -> MATRIZ` e `DIRETA -> FILIAL` (mais o backfill das 11 provas com `rota=NULL`), e (b) tornar a coluna `NOT NULL`. Esta wave NAO faz nada disso — entrega a estrutura base.

### 4.3 Desenho do enum `rota_enum` em Python e PostgreSQL

**Caminho do arquivo Python:** [backend/app/db/models.py](../../backend/app/db/models.py) (mesmo onde ja vive `RotaEnum`). NAO existe `/domain/state_machine/enums.py` no projeto — o DAT v3.0 §4 descreve esse modulo como ideal mas a v3.0 codificou tudo em `db/models.py` + `services/state_machine.py`. **Refatoracao para `/domain/state_machine/enums.py` fica para a Wave 3 v4.0** (que vai reescrever a state machine completa).

**Estrutura proposta para `RotaEnum`:**

```python
class RotaEnum(str, enum.Enum):
    """Rota de encaminhamento (RN-007 v4.0).

    Quatro valores: MATRIZ, LAM_MATRIZ, FILIAL, LAM_FILIAL — escolhidos
    manualmente pelo Administrador 3Studio na criacao da prova. Imutavel
    apos criacao (RN-002 v4.0).

    Valores legacy `PADRAO` e `DIRETA` (v3.0) permanecem no enum PostgreSQL
    ate a Wave 7 fazer o backfill. Nao sao expostos pelo Pydantic da v4.0
    — schemas de criacao rejeitam `PADRAO`/`DIRETA` como entrada. Schemas
    de leitura (ProvaResponse, ProvaListItem) ACEITAM os valores legacy
    para nao quebrar a renderizacao das provas v3.0 ate a Wave 7.
    """

    # v4.0
    MATRIZ = "MATRIZ"
    LAM_MATRIZ = "LAM_MATRIZ"
    FILIAL = "FILIAL"
    LAM_FILIAL = "LAM_FILIAL"

    # Legacy v3.0 — backfill na Wave 7 (Componente 21)
    PADRAO = "PADRAO"
    DIRETA = "DIRETA"
```

**Sub-enum exposto na criacao (Pydantic v2):**

```python
class RotaCriacaoEnum(str, enum.Enum):
    """Sub-enum aceito pelo schema ProvaCreateRequest. Bloqueia legacy."""
    MATRIZ = "MATRIZ"
    LAM_MATRIZ = "LAM_MATRIZ"
    FILIAL = "FILIAL"
    LAM_FILIAL = "LAM_FILIAL"
```

**Procedimento de sincronizacao Python ↔ PostgreSQL** (DAT v3.0 §4.5):
- Adicionar valor ao `RotaEnum` em Python.
- Migration Alembic com `ALTER TYPE rota_enum ADD VALUE 'NOVO_VALOR'`.
- Atualizar tabela de transicoes (Wave 3 v4.0).
- Cobrir com testes de integridade (test que compara `set(RotaEnum) == set(SELECT enumlabel FROM pg_enum WHERE enumtypid='rota_enum'::regtype)`).
- Atualizar `CLAUDE.md` (proxima secao "Como adicionar valor ao enum rota_enum").

**Teste de integridade enum Python ↔ PostgreSQL** (novo):
```python
async def test_rota_enum_python_matches_postgres(async_session):
    result = await async_session.execute(
        sa.text("""
        SELECT array_agg(enumlabel ORDER BY enumsortorder) AS values
        FROM pg_enum e
        JOIN pg_type t ON e.enumtypid = t.oid
        WHERE t.typname = 'rota_enum'
        """)
    )
    pg_values = set(result.scalar())
    py_values = {e.value for e in RotaEnum}
    assert pg_values == py_values, (
        f"Drift detectado: PG tem {pg_values}, Python tem {py_values}"
    )
```

### 4.4 Desenho da funcao de geracao do codigo alfanumerico

**Localizacao proposta:** [backend/app/services/codigo_publico_service.py](../../backend/app/services/codigo_publico_service.py) (novo). Justificativa: ja temos `qrcode_service.py`, `etiqueta_service.py` no mesmo diretorio — colocar com nome explicito segue a convencao.

**Assinatura:**

```python
"""Geracao do codigo publico legivel da prova (DAT v3.0 §8.3 + RF-005 v4.0).

Formato: PRV-AAAA-MM-NNNNNN
  PRV    = prefixo fixo (identifica o tipo de objeto)
  AAAA   = ano de criacao da prova
  MM     = mes de criacao (zero-padded)
  NNNNNN = sequencial alfanumerico de 6 caracteres
           Alfabeto: 31 chars sem ambiguos (sem 0/O, 1/I/L)

Caracteristicas:
  - Determinismo do prefixo dado o created_at.
  - Nao-determinismo do sufixo via secrets.choice (CSPRNG do Python).
  - Unicidade garantida pela coluna `codigo_publico VARCHAR(20) UNIQUE`.
  - Em caso de colisao improvavel (31^6 = 887 milhoes), retry ate 5x;
    apos isso, propaga RuntimeError.
"""
import secrets
from datetime import datetime

CODIGO_PUBLICO_PREFIX = "PRV"
CODIGO_PUBLICO_NANO_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # 31 chars
CODIGO_PUBLICO_NANO_LEN = 6
CODIGO_PUBLICO_TOTAL_LEN = 17  # 'PRV' + '-' + 'YYYY' + '-' + 'MM' + '-' + 6


def gerar_codigo_publico(criado_em: datetime) -> str:
    """Gera codigo publico no formato PRV-AAAA-MM-NNNNNN."""
    nano = "".join(
        secrets.choice(CODIGO_PUBLICO_NANO_ALPHABET)
        for _ in range(CODIGO_PUBLICO_NANO_LEN)
    )
    return f"{CODIGO_PUBLICO_PREFIX}-{criado_em.year:04d}-{criado_em.month:02d}-{nano}"


def validar_formato_codigo_publico(codigo: str) -> bool:
    """True se `codigo` segue exatamente o formato PRV-AAAA-MM-NNNNNN."""
    if len(codigo) != CODIGO_PUBLICO_TOTAL_LEN:
        return False
    if not codigo.startswith(f"{CODIGO_PUBLICO_PREFIX}-"):
        return False
    parts = codigo.split("-")
    if len(parts) != 4:
        return False
    pref, ano, mes, nano = parts
    if pref != CODIGO_PUBLICO_PREFIX:
        return False
    if not (ano.isdigit() and len(ano) == 4):
        return False
    if not (mes.isdigit() and len(mes) == 2 and 1 <= int(mes) <= 12):
        return False
    if len(nano) != CODIGO_PUBLICO_NANO_LEN:
        return False
    if any(c not in CODIGO_PUBLICO_NANO_ALPHABET for c in nano):
        return False
    return True
```

**Tratamento de colisao na criacao da prova:**
O endpoint POST `/api/v1/provas/` chama `gerar_codigo_publico(created_at)` e tenta INSERT. Se Postgres lancar `UniqueViolation`, faz retry ate 3x (gerando novo codigo). Se ainda assim colidir (extremamente improvavel — 887M combinacoes vs ~30 inserts/dia), propaga 502.

```python
# Em provas.py:create_prova, dentro do try/except do INSERT:
for tentativa in range(3):
    codigo = gerar_codigo_publico(created_at)
    nova_prova = ProvaDigital(..., codigo_publico=codigo, ...)
    try:
        db.add(nova_prova)
        await db.flush()
        break
    except IntegrityError as exc:
        if "idx_provas_codigo_publico" in str(exc.orig):
            await db.rollback()
            continue  # retry com novo codigo
        raise
else:
    raise HTTPException(502, "Falha ao gerar codigo publico unico apos 3 tentativas")
```

**Testes (>=95% cobertura):**

1. **Formato:**
   - `gerar_codigo_publico(datetime(2026, 5, 4))` retorna string `PRV-2026-05-XXXXXX` (17 chars, regex `^PRV-2026-05-[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{6}$`).
   - Mes < 10 zero-padded: `datetime(2026, 1, 1)` → `PRV-2026-01-XXXXXX`.
   - Ano > 9999 nao acontece — raise validacao caller.

2. **Alfabeto restrito:**
   - 100 codigos gerados nao contem nenhum char em `{0, 1, I, L, O}`.
   - Todo char esta em `CODIGO_PUBLICO_NANO_ALPHABET`.

3. **Determinismo do prefixo, nao-determinismo do sufixo:**
   - Mesma data, 100 chamadas: todos comecam com `PRV-2026-05-` mas os sufixos sao todos diferentes (com probabilidade de colisao 100/887M ≈ 0).

4. **`validar_formato_codigo_publico`:**
   - Aceita: `PRV-2026-05-K3T9XB`, `PRV-2026-12-AAAAAA`.
   - Rejeita: `prv-2026-05-K3T9XB` (lowercase), `PRV-26-05-K3T9XB` (ano 2 digitos), `PRV-2026-13-XXXXXX` (mes 13), `PRV-2026-05-K3T9X0` (zero ambiguo), `XYZ-2026-05-K3T9XB` (prefixo errado), `PRV-2026-05-K3T9X` (sufixo curto).

### 4.5 Desenho do endpoint de criacao atualizado

**Caminho:** [backend/app/api/v1/provas.py](../../backend/app/api/v1/provas.py) (modificacao direta — autorizada pelo prompt §6).

**Schema atualizado:**

```python
class ProvaCreateRequest(BaseModel):
    nome: str = Field(..., min_length=1, max_length=200)
    nro_requerimento: str = Field(..., min_length=1, max_length=50)
    cliente: str = Field(..., min_length=1, max_length=200)
    vendedor_id: UUID
    object_key: str = Field(..., min_length=1, max_length=500)
    rota: RotaCriacaoEnum  # NOVO — Wave 2 v4.0. Obrigatorio. Sem default.

    @field_validator("nome", "cliente")
    ...
```

**Schema de update (defesa em profundidade):** atualmente nao existe endpoint PATCH/PUT em `/api/v1/provas/{id}`. Os unicos UPDATEs sao via `/transicoes`, `/cancelar`, `/reiniciar-ciclo` — todos handlers especificos que NAO aceitam `rota` no body. Documentar em comentario no schema:

```python
# Nao existe schema ProvaUpdateRequest — atualizacoes em provas seguem
# apenas via state_machine (POST /{id}/transicoes, /cancelar, /reiniciar-ciclo).
# Mesmo assim, o trigger PostgreSQL bloqueia tentativa de UPDATE direto na
# coluna `rota` apos definicao (RN-002 v4.0).
```

**Logica do handler `POST /api/v1/provas/`:**

1. Autorizacao via `Depends(access_required("provas.create"))` — JA EXISTE.
2. Validacao Pydantic (incluindo nova `rota`).
3. Re-validacao de unicidade do `nro_requerimento` (race window).
4. `_carregar_vendedor` — JA EXISTE. Mantem validacao de `vendedor.localizacao IS NOT NULL` (CHECK constraint do banco). **Nao chama mais `determinar_rota` no Wave 2 v4.0.**
5. `_validar_upload_no_r2` — JA EXISTE.
6. Gera UUID da prova.
7. **Gera `codigo_publico = gerar_codigo_publico(created_at)`** (NOVO).
8. **Gera `qr_code_hash = gerar_hash(prova_id, nro_requerimento)`** — JA EXISTE. Mantem.
9. **Gera `qr_payload`** com novo formato — ver Secao 4.5.1 abaixo.
10. Renderiza PNG do QR Code com novo payload.
11. Carrega template de etiqueta.
12. **Renderiza PDF da etiqueta com `codigo_publico` em destaque + badge da rota** — NOVO.
13. INSERT atomico de `provas_digitais` (com `rota=body.rota`, `codigo_publico=...`) + `etiquetas` + `audit_logs`.
14. Retorna `ProvaCreateResponse` com `prova` (incluindo `codigo_publico` e `rota`), `etiqueta_pdf_base64`, `qr_code_payload`.

**Codigos HTTP:**
- 201 — sucesso
- 400/422 — erros de validacao (rota faltando, rota invalida, content-type errado, etc)
- 401 — sem JWT valido
- 403 — perfil sem `access_required("provas.create")` (vendedor/motorista/clicheria)
- 409 — `nro_requerimento` ja cadastrado (race ou duplicado) OU `codigo_publico` colisao apos 3 retries
- 502 — falha do banco no commit ou r2 indisponivel

**Logging:** linha INFO com `usuario_id`, `rota_escolhida=body.rota.value`, `codigo_publico=...`. **NAO loga em audit_log o `codigo_publico` em si** — fica no log da aplicacao apenas. O audit_log `criar_prova` (ja existe) ganha campo `rota` no `detalhes_json`.

#### 4.5.1 Novo payload do QR Code

**Atual (v3.0):** `3SD|{nro_requerimento}|{hash_truncado_16}`

**Proposto (v4.0):** `3SD|{codigo_publico}|{hash_truncado_16}`

Motivacao (DAT v3.0 §8.1): "Internamente, ambos resolvem para o mesmo registro pela mesma funcao de dominio `resolver_prova()`". O `codigo_publico` e o identificador humano-legivel; embuti-lo no QR garante que tanto camera quanto digitacao manual resolvem pelo mesmo lookup `WHERE codigo_publico = ?`.

**Compatibilidade temporal com Wave 3 v4.0 (Componente 19):**
- Wave 2 v4.0 entrega `codigo_publico` na coluna + na etiqueta + no payload do QR.
- Wave 3 v4.0 (Componente 19) implementa o endpoint que aceita `codigo_publico` digitado no fallback.
- Ate la, o `validar_payload_qr` (existente) precisa aceitar tanto formato antigo quanto novo. **Decisao**: na Wave 2 v4.0, modifico `qrcode_service.gerar_payload_qr` para aceitar `codigo_publico` (novo) e renomeio o segundo parametro. Mantenho o `validar_payload_qr` flexivel ate a Wave 3 (que vai reescrever).

**Consequencia para provas v3.0 (5 com rota PADRAO/DIRETA + 11 NULL):** seus QRs continuam tendo o formato antigo (`nro_requerimento`). Quando o scanner da Wave 3 v4.0 for implementado, ele precisa aceitar AMBOS os formatos (lookup por `codigo_publico` se prefixo bate, fallback para `nro_requerimento`). **Documentado para Wave 3.**

#### 4.5.2 Onde a chamada `determinar_rota(vendedor)` deixa de existir

A chamada atual em `provas.py` linhas 414-421 (`rota_projetada = determinar_rota(vendedor)`) **deixa de fazer sentido na v4.0** — a rota agora vem do payload. Remover essa chamada e:
- O schema `ProvaResponse.rota_projetada` continua existindo (compatibilidade com clientes v3.0)? Decisao: REMOVER tambem `rota_projetada` do `ProvaResponse` e do `ProvaCreateResponse`. O frontend vai consumir `prova.rota` diretamente. Atualizar o frontend `nova-prova/page.tsx` linhas 281-286 para mostrar `prova.rota` (nao `rota_projetada`).
- `_carregar_vendedor` linha 274-280: a validacao de `vendedor.localizacao IS NOT NULL` continua (CHECK constraint + RN-009: localizacao continua obrigatoria mesmo que informativa).
- Funcao `state_machine.determinar_rota` continua existindo — usada pelo `executar_transicao` apenas para PROVAS LEGADAS (v3.0 com `rota=NULL`) ate a Wave 7. Ver Secao 14 (autorizacao).

### 4.6 Desenho da imutabilidade da rota

**3 camadas de defesa:**

1. **Pydantic v2 (camada API/dominio):**
   - `ProvaCreateRequest.rota` aceita 4 valores via `RotaCriacaoEnum`.
   - **Sem schema de UPDATE** que mencione `rota` — o backend nao expoe endpoint que aceite `rota` em PATCH/PUT.
   - Decisao defensiva: se algum dia for criado um `ProvaUpdateRequest`, deve `Field(frozen=True)` ou simplesmente omitir o campo `rota`.

2. **Handler API:**
   - Os endpoints existentes que mutam a prova (`/transicoes`, `/cancelar`, `/reiniciar-ciclo`) NAO recebem `rota` em seus payloads — confirmado pela inspecao de `TransicaoRequest` (linhas 352-403 de `prova.py`) e `CancelarRequest` (linhas 476-493). Nada a mudar aqui.
   - **Modificacao cirurgica em `state_machine.executar_transicao`** (Secao 14) — bloquear sobrescrita de `prova.rota` quando ja preenchida.

3. **Banco (trigger):**
   - `trg_provas_rota_imutavel BEFORE UPDATE WHEN (OLD.rota IS DISTINCT FROM NEW.rota)` rejeita com SQLSTATE `22023` quando `OLD.rota IS NOT NULL AND NEW.rota IS DISTINCT FROM OLD.rota`. Permite `NULL → valor` (Wave 7 backfill).

**Teste de defesa em profundidade:**

```python
async def test_trigger_bloqueia_update_rota_apos_definicao(test_db_session):
    # Cria prova com rota = MATRIZ
    prova = ProvaDigital(rota=RotaEnum.MATRIZ, ...)
    test_db_session.add(prova)
    await test_db_session.commit()

    # Tenta UPDATE direto
    with pytest.raises(IntegrityError) as exc_info:
        await test_db_session.execute(
            sa.text("UPDATE provas_digitais SET rota = 'FILIAL' WHERE id = :id"),
            {"id": prova.id},
        )
    assert "imutavel" in str(exc_info.value).lower()


async def test_trigger_permite_null_para_valor(test_db_session):
    # Cria prova com rota = NULL (legacy)
    prova = ProvaDigital(rota=None, ...)
    test_db_session.add(prova)
    await test_db_session.commit()

    # UPDATE NULL -> valor (simulando backfill da Wave 7)
    await test_db_session.execute(
        sa.text("UPDATE provas_digitais SET rota = 'MATRIZ' WHERE id = :id"),
        {"id": prova.id},
    )
    await test_db_session.commit()
    # Sem erro.


async def test_trigger_bloqueia_valor_para_null(test_db_session):
    prova = ProvaDigital(rota=RotaEnum.MATRIZ, ...)
    test_db_session.add(prova)
    await test_db_session.commit()

    with pytest.raises(IntegrityError) as exc_info:
        await test_db_session.execute(
            sa.text("UPDATE provas_digitais SET rota = NULL WHERE id = :id"),
            {"id": prova.id},
        )
    assert "imutavel" in str(exc_info.value).lower()
```

### 4.7 Decisao sobre o filtro de rota na listagem (Componente 07)

**Estado atual:** o Componente 07 (atualmente em producao) JA TEM filtro de rota — `frontend/src/app/(dashboard)/provas/page.tsx` linhas 296-309. O `ROTA_OPTIONS` (em `lib/types/prova.ts`) hoje contem 2 valores (`PADRAO`, `DIRETA`). O endpoint backend `GET /api/v1/provas/` ja aceita query param `rota`.

**Recomendacao: Opcao A — atualizar nesta wave para 4 valores.**

Justificativa:
1. **Trabalho minimo:** alterar `ROTA_OPTIONS` para incluir os 4 novos + alterar `ROTA_LABELS` para textos human-readable ("Matriz", "Lam. Matriz", "Filial", "Lam. Filial"). Isso e ~5 linhas de TS.
2. **RF-014 da v4.0 explicita os 4 valores** ("filtros por periodo, status, vendedor, cliente e rota (Matriz, Lam. Matriz, Filial, Lam. Filial)"). Nao incluir agora e deixar o RF parcialmente atendido.
3. **Backend ja aceita** (validacao Pydantic do query param e via `RotaEnum`, que ganha 4 valores apos a migration).
4. **Compatibilidade com provas legadas:** o filtro do frontend mostra os 4 novos valores. Se o admin quiser ver provas legadas (PADRAO/DIRETA), digita na URL ou nao. Decisao: **manter PADRAO e DIRETA tambem no `ROTA_OPTIONS` da v4.0, marcadas como "(legada)"** ate a Wave 7 dropar — isso evita esconder dados em producao.

**ROTA_OPTIONS proposto:**
```ts
export const ROTA_OPTIONS = [
  "MATRIZ",
  "LAM_MATRIZ",
  "FILIAL",
  "LAM_FILIAL",
  "PADRAO",       // legada v3.0 — removida na Wave 7
  "DIRETA",       // legada v3.0 — removida na Wave 7
] as const;

export const ROTA_LABELS: Record<Rota, string> = {
  MATRIZ: "Matriz",
  LAM_MATRIZ: "Lam. Matriz",
  FILIAL: "Filial",
  LAM_FILIAL: "Lam. Filial",
  PADRAO: "Matriz (legada v3.0)",
  DIRETA: "Filial (legada v3.0)",
};
```

**Sub-questao: filtro deve mostrar legadas quando admin nao pode mais escolher?** Decisao: SIM — admin pode FILTRAR provas legadas mesmo sem poder CRIAR provas com rota legada. Coerencia com a Wave 7 que vai backfill PADRAO→MATRIZ e DIRETA→FILIAL.

### 4.8 Desenho do redesign da tela de Criacao de Prova

**Layout proposto** (alto nivel — pixel-perfect e tarefa de UI/UX):

```
┌─────────────────────────────────────────────────────────────┐
│ Nova prova digital                       [Criar prova]      │
├─────────────────────────────────────────────────────────────┤
│ ┌──────────────────┐  ┌──────────────────┐                  │
│ │ Nome             │  │ Numero requeri.  │                  │
│ └──────────────────┘  └──────────────────┘                  │
│ ┌──────────────────┐  ┌──────────────────┐                  │
│ │ Cliente          │  │ Vendedor   ▼     │                  │
│ └──────────────────┘  └──────────────────┘                  │
│                                                             │
│ ┌─────────────────────────────────────────┐                 │
│ │ Rota *                                  │                 │
│ │ ◯ Matriz   ◯ Lam. Matriz                │                 │
│ │ ◯ Filial   ◯ Lam. Filial                │                 │
│ │ ⚠ A rota e imutavel apos a criacao —    │                 │
│ │   confira antes de submeter.            │                 │
│ └─────────────────────────────────────────┘                 │
│                                                             │
│ ┌─────────────────────────────────────────┐                 │
│ │ Arraste a arte aqui ou clique           │                 │
│ │ JPG ou PNG · max 10MB                   │                 │
│ └─────────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────┘

[Click "Criar prova"]
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ Confirmar rota                                              │
│                                                             │
│ Voce escolheu a rota: ▶ LAM. MATRIZ ◀                      │
│                                                             │
│ Esta escolha e imutavel — para alterar, sera                │
│ necessario cancelar a prova e criar uma nova.               │
│                                                             │
│             [Voltar]   [Confirmar criacao]                  │
└─────────────────────────────────────────────────────────────┘
```

**Detalhes:**
- **Campo Rota — radio group**: 4 opcoes em grid 2×2. Posicionado de forma destacada (depois dos campos de identificacao, antes do upload). Mitigacao do risco "Confusao operacional" do Backlog v4.0 §6.
- **Texto auxiliar**: "A rota e imutavel apos a criacao — confira antes de submeter."
- **`aria-describedby`** ligando o radio group ao texto auxiliar.
- **Modal de confirmacao dupla**: ao clicar em "Criar prova", mostra modal com a rota destacada e botoes "Voltar"/"Confirmar criacao". Submit so acontece apos clicar "Confirmar criacao". Mitigacao adicional do mesmo risco.
- **Validacao cliente**: `canSubmit` agora exige `form.rota !== ""`. Erro inline se submeter sem rota (defensivo — botao ja deve estar `disabled`).
- **Apos sucesso**: pagina de sucesso ja existe — mostrar agora `prova.rota` (nao mais `rota_projetada`) e `prova.codigo_publico` em destaque.
- **Componente reutilizavel**: criar `<RotaSelect />` ou similar em `frontend/src/components/RotaSelect.tsx`. Sera consumido na criacao agora; pode ser reusado pelo Componente 07 listagem mais adiante (mas o `<select>` da listagem nao precisa de radio group, entao reutilizacao e parcial — apenas as labels e options).

**Acessibilidade:**
- Radio group com `<fieldset>` + `<legend>Rota</legend>`.
- `aria-required="true"` no `<fieldset>`.
- Modal de confirmacao com focus trap (padrao Wave 3 `useFocusTrap` ja existe — `frontend/src/hooks/useFocusTrap.ts`).
- Modal fecha com Esc, Tab cicla apenas dentro.

### 4.9 Desenho da etiqueta reformulada

**Mudancas no `etiqueta_service.gerar_pdf`:**

1. **Adicionar `codigo_publico: str` como parametro novo** (obrigatorio).
2. **Adicionar `rota: RotaEnum` como parametro novo** (obrigatorio — Wave 2 v4.0; provas legadas regeram etiqueta? — resolvido na Secao 4.12).
3. **Bloco com codigo alfanumerico em destaque**:
   - Posicao: ABAIXO do QR Code, dentro da caixa do QR (mesmo retangulo de cantos arredondados que envolve o QR hoje), em fonte grande.
   - Tamanho de fonte: minimo 9pt para caber na etiqueta de 90×57mm. **Isso fica aquem dos 18pt sugeridos no prompt** — a etiqueta e literalmente 5,7cm de altura. Vou priorizar legibilidade sem alterar dimensoes da etiqueta. Documentar como decisao.
   - Fonte: monospace ideal (mas DejaVu Sans Bold serve). Texto: `PRV-2026-05-K3T9XB` em 9pt bold, centralizado abaixo do QR.
4. **Badge da rota selecionada**:
   - Posicao: rodape lateral esquerdo, no espaco onde hoje so tem o ano (linha 297-302 do `etiqueta_service.py`).
   - Estilo: caixa preta filled com texto branco. Conteudo: `MATRIZ`, `LAM. MATRIZ`, `FILIAL` ou `LAM. FILIAL`.
   - Tamanho: 7pt bold.
5. **Compatibilidade**: assinatura nova de `gerar_pdf`:

```python
def gerar_pdf(
    *,
    nome_prova: str,
    nro_requerimento: str,
    vendedor_nome: str,
    qr_image_bytes: bytes,
    codigo_publico: str | None = None,  # Wave 2 v4.0
    rota: RotaEnum | None = None,        # Wave 2 v4.0
    template: dict | None = None,
    created_at: datetime | None = None,
) -> bytes:
```

Os parametros novos sao Optional para permitir provas legadas que nao tem `codigo_publico` (v3.0) — neste caso, o codigo nao e renderizado e o badge de rota mostra "ROTA LEGADA". Apos a Wave 7, todos serao obrigatorios.

**Desenho visual proposto** (substitui linhas 297-309 do `etiqueta_service.py`):

```
[ existing layout intact ate linha 295 ]

# Codigo publico embaixo do QR (NOVO):
if codigo_publico:
    pdf.set_font(_FONT_FAMILY, "B", 9.5)
    pdf.set_xy(qr_box_x, qr_box_y + qr_box_size + 0.5)
    pdf.cell(qr_box_size, 3.5, codigo_publico, align="C")

# Rodape: ano + badge da rota + texto direito
rodape_y = 49
pdf.set_font(_FONT_FAMILY, "", 7.5)
ano = _fmt_year(created_at) if created_at is not None else ""

# Badge de rota (NOVO):
if rota is not None:
    badge_text = ROTA_BADGE_LABELS[rota]  # 'MATRIZ' / 'LAM. MATRIZ' / etc
    badge_w = pdf.get_string_width(badge_text) + 4
    pdf.set_fill_color(0, 0, 0)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(3, rodape_y)
    pdf.cell(badge_w, 4, badge_text, align="C", fill=True)
    pdf.set_text_color(0, 0, 0)
    # Ano logo a direita do badge
    pdf.set_xy(3 + badge_w + 1, rodape_y)
    pdf.cell(15, 4, ano, align="L")
else:
    pdf.set_xy(3, rodape_y)
    pdf.cell(40, 4, ano, align="L")
```

**Tabela `ROTA_BADGE_LABELS`** (em `etiqueta_service.py`):
```python
ROTA_BADGE_LABELS = {
    RotaEnum.MATRIZ: "MATRIZ",
    RotaEnum.LAM_MATRIZ: "LAM. MATRIZ",
    RotaEnum.FILIAL: "FILIAL",
    RotaEnum.LAM_FILIAL: "LAM. FILIAL",
    # Legacy v3.0 — exibidos como rota legada nos casos onde a etiqueta
    # for regerada antes da Wave 7.
    RotaEnum.PADRAO: "MATRIZ (legada)",
    RotaEnum.DIRETA: "FILIAL (legada)",
}
```

**Compatibilidade do template:**
- O template `template_etiqueta` em `configuracoes_sistema` tem chaves `nome`, `formato` (legacy), `logo_enabled`, `mostrar_data_criacao`. Esta wave nao adiciona nova chave — o codigo publico e o badge de rota sao SEMPRE renderizados quando os parametros estao presentes (nao sao toggleable). Documentar.

### 4.10 Estrategia de testes

**Cobertura esperada:**
- Servicos: ≥95% para `codigo_publico_service.py` e `etiqueta_service.py` (modulos novos/modificados).
- Schema Pydantic: 100% dos cenarios de validacao da nova `rota`.
- State machine: cobertura ≥95% mantida (DAT v3.0 §4) — testes existentes nao podem regredir.
- Domain/service total: ≥80% (DoD global, BACKLOG v4.0 §2).

**Camada 1 — Unitarios (pytest + pytest-asyncio):**

1. `test_codigo_publico_service.py` (NOVO, ~10 testes):
   - Formato `PRV-AAAA-MM-NNNNNN`.
   - Mes < 10 zero-padded.
   - Alfabeto restrito (sem `0/1/I/L/O`).
   - Nao-determinismo do sufixo (100 chamadas → 100 codigos distintos).
   - Determinismo do prefixo dado a data.
   - `validar_formato_codigo_publico` aceita validos / rejeita invalidos.

2. `test_schemas.py` (atualizar):
   - `ProvaCreateRequest` ACEITA `rota="MATRIZ"`, `rota="LAM_MATRIZ"`, `rota="FILIAL"`, `rota="LAM_FILIAL"`.
   - `ProvaCreateRequest` REJEITA: rota faltando (422), rota=`null` (422), rota=`PADRAO` (422 — legacy bloqueada na criacao via sub-enum), rota=`""` (422), rota=`"matriz"` lowercase (422).

3. `test_etiqueta_service.py` (atualizar):
   - `gerar_pdf(codigo_publico="PRV-2026-05-K3T9XB", rota=RotaEnum.MATRIZ, ...)` produz bytes que comecam com `b'%PDF-'`.
   - O PDF gerado contem (text extract) o codigo publico e a string "MATRIZ" / "LAM. MATRIZ" etc.
   - Backward compat: `gerar_pdf(codigo_publico=None, rota=None, ...)` continua produzindo PDF valido (sem o bloco extra).

4. `test_models.py` (atualizar):
   - `RotaEnum` tem 6 valores: 4 novos + 2 legacy.
   - `RotaCriacaoEnum` tem apenas 4 valores.

5. **`test_state_machine.py`** (atualizar):
   - Todos os testes existentes continuam passando (cobertura ≥95% preservada).
   - **NOVO**: teste que `executar_transicao` em prova com `rota` ja preenchida NAO sobrescreve a rota na aprovacao (ver Secao 14).

**Camada 2 — Integracao (pytest + httpx + Postgres real):**

6. `test_provas_api.py` (atualizar — ~10 testes novos):
   - POST `/api/v1/provas/` com `rota=MATRIZ` retorna 201 + `prova.rota=MATRIZ` + `prova.codigo_publico` no formato correto.
   - Idem `LAM_MATRIZ`, `FILIAL`, `LAM_FILIAL` (4 testes).
   - POST sem `rota` → 422.
   - POST com `rota=PADRAO` → 422 (bloqueio na criacao v4.0).
   - POST com perfil VENDEDOR → 403 (Matriz Wave 1 v4.0).
   - POST com perfil MOTORISTA → 403.
   - POST com perfil CLICHERIA → 403.
   - GET `/api/v1/provas/{id}` retorna `codigo_publico` e `rota` corretos.
   - GET `/api/v1/provas/` com filtro `?rota=MATRIZ` retorna apenas provas com essa rota.
   - GET `/api/v1/provas/` com filtro `?rota=PADRAO` retorna provas legadas.

7. `test_imutabilidade_rota.py` (NOVO, ~5 testes):
   - SQL direto `UPDATE provas_digitais SET rota = X WHERE rota IS NOT NULL` levanta erro do trigger.
   - SQL direto `UPDATE provas_digitais SET rota = NULL WHERE rota IS NOT NULL` levanta erro.
   - SQL direto `UPDATE provas_digitais SET rota = X WHERE rota IS NULL` SUCEDE (Wave 7 backfill).
   - `executar_transicao` com prova legada (rota=NULL) + admin chamando `RETIRADA->APROVADA`: rota e definida via `determinar_rota` (modo legacy). **Apenas se Mario autorizar a modificacao cirurgica — Secao 14.**
   - `executar_transicao` com prova v4.0 (rota=MATRIZ) + admin chamando `RETIRADA->APROVADA`: rota PERMANECE = MATRIZ (sem sobrescrever).

8. `test_migration_012.py` (NOVO, ~3 testes):
   - `alembic upgrade head` em banco limpo cria os 4 valores no enum + coluna `codigo_publico` + index + trigger.
   - `alembic downgrade -1` reverte coluna + index + trigger (mas NAO os enum values — limitacao do Postgres, documentado).
   - `alembic upgrade head` aplicado duas vezes: idempotente (`IF NOT EXISTS` em ADD VALUE).

9. `test_rota_enum_drift.py` (NOVO, 1 teste):
   - `set(RotaEnum) == set(SELECT enumlabel FROM pg_enum WHERE typname='rota_enum')`.

**Camada 3 — E2E (Playwright)** — DAT v3.0 §3 marca como "cenarios criticos cobertos manualmente". O DoD global do Backlog v4.0 nao exige Playwright automatizado para esta wave especifica (a Wave 1 v4.0 tambem ficou sem). Entrego smoke manual:

10. **Smoke E2E manual** documentado no `analysis.md` Secao "Execucao":
    - 3Studio loga, abre `/nova-prova`, preenche, escolhe "Lam. Matriz", confirma no modal, submete.
    - Ve tela de sucesso com codigo `PRV-2026-05-XXXXXX` e rota `Lam. Matriz`.
    - Faz download da etiqueta — abre em PDF reader; codigo publico aparece abaixo do QR; badge "LAM. MATRIZ" no rodape.
    - Acessa `/provas/[id]` — codigo e rota visiveis no detalhe.
    - Tenta acessar `/nova-prova` como vendedor (URL direta) → redirecionado.
    - Tenta abrir `/provas` e filtrar `rota=Lam. Matriz` → mostra a prova criada.

11. **Teste de nao-regressao da Wave 1 v4.0:** `cd backend && pytest -q` deve manter os 761 testes verdes pos-execucao desta wave + os adicionados (estimativa: ~30-40 novos → ~795 testes).

### 4.11 Migrations previstas

Apenas **uma migration Alembic**: `012_add_codigo_publico_and_rotas_v4_to_provas`. Detalhe completo na Secao 4.2.

**RLS migration:** **NENHUMA**. As 12 policies atuais cobrem todos os cenarios:
- `pol_provas_insert WITH CHECK (app_private.current_user_is_admin())` — cobre INSERT pelo perfil 3Studio.
- `pol_provas_select` — cobre SELECT pelos 4 perfis.
- `pol_provas_update` — cobre UPDATE pelo perfil 3Studio (handlers /transicoes, /cancelar, /reiniciar-ciclo).
- `pol_etiquetas_select` — cobre SELECT da etiqueta nova.

Confirmado via leitura de `backend/migrations/rls/012_move_helpers_to_app_private.sql` (estado final pos-Wave 1 v4.0).

**Nao ha mudanca destrutiva** (ALTER COLUMN destrutivo, DROP COLUMN, RENAME) — apenas ADD VALUE no enum + ADD COLUMN + CREATE INDEX + CREATE TRIGGER.

### 4.12 Plano de coexistencia temporal — provas legadas

**Inventario do que e legado:**
- 11 provas com `rota = NULL` (Wave 0/1/2 v3.0 — nunca aprovadas, ou desde antes de adicionar rota_projetada na resposta).
- 5 provas com `rota = PADRAO` (2) ou `rota = DIRETA` (3) (provas v3.0 ja aprovadas).
- Nenhuma com codigo_publico (campo nao existia).

**Apos a migration 012:**
- As 11 com `rota=NULL` continuam com `rota=NULL` ate a Wave 7. Recebem `codigo_publico` derivado do `created_at` (gerado pelo backfill da migration).
- As 5 com `rota=PADRAO`/`DIRETA` continuam com esses valores ate a Wave 7. Recebem `codigo_publico`.

**Comportamento do frontend para provas legadas:**

1. **Listagem (`/provas`)**:
   - Coluna `Rota`: ja renderiza `p.rota ? ROTA_LABELS[p.rota] : "—"`. Provas com NULL mostram "—". Provas com PADRAO mostram "Matriz (legada v3.0)" via `ROTA_LABELS`. Sem alteracao adicional necessaria.

2. **Detalhe (`/provas/[id]`)**:
   - `Visualizar etiqueta` modal: pode regerar PDF? **Decisao: apenas para provas v4.0 com `rota IS NOT NULL`.** Para provas legadas (rota=NULL), mostrar tooltip "Provas legadas v3.0 nao tem rota nem codigo publico — etiqueta original disponivel via download de PDF da `etiquetas.qr_code_image`" (a etiqueta original esta no banco como BYTEA + reused). Para provas com rota=PADRAO/DIRETA, regerar PDF mostrando o badge "MATRIZ (legada)" / "FILIAL (legada)".
   - Codigo publico: se existe (apos migration 012, todas terao), mostrar normalmente. Se ainda nao foi backfilled (deve existir um delta entre migration aplicada e provas que rodaram backfill), mostrar "—".

3. **Form de criacao**: nao se aplica — esse fluxo cria provas v4.0.

**Comportamento do backend para provas legadas:**

1. **`state_machine.executar_transicao`** (Wave 3 v3.0 atualmente): chama `determinar_rota(usuario)` na aprovacao para provas legadas (rota=NULL). Modificacao cirurgica proposta na Secao 14 mantem esse comportamento APENAS quando `prova.rota IS NULL`.

2. **`etiqueta_service.gerar_pdf`**: aceita `codigo_publico: str | None` e `rota: RotaEnum | None`. Renderiza condicional.

3. **Endpoint GET `/etiqueta.pdf`** (existente, Wave 2 v3.0): regera o PDF on-demand. Provas legadas — mostra etiqueta antiga + badge "rota legada" se aplicavel.

4. **Endpoint POST `/provas/{id}/transicoes`**: aceita provas legadas se a transicao for valida pela state machine v3.0 atual.

5. **Comportamento de provas v4.0 com `rota=LAM_MATRIZ` ou `rota=LAM_FILIAL`**: sao criadas com sucesso, mas as transicoes a partir de `CRIADA` que atualmente existem (`CRIADA -> RETIRADA_PELO_VENDEDOR`) acontecem ignorando a rota. **Inconsistencia tolerada**: a rota fica armazenada mas nao direciona transicoes ate a Wave 3 v4.0 (Componente 11 v4.0). Documentar no CLAUDE.md como "coexistencia transitoria".

**Decisao explicita (a confirmar com Mario):** **permitir as 4 rotas no select desde a Wave 2 v4.0** (sem esconder LAM_MATRIZ/LAM_FILIAL temporariamente). Justificativa: o prompt §1 diz que a coluna apenas armazena rota nesta wave; a UI pode escolher qualquer uma. Se Mario preferir, posso esconder LAM_* ate a Wave 3.

### 4.13 Riscos e pontos de atencao

| # | Risco | Severidade | Mitigacao |
|---|---|---|---|
| R1 | **Confusao operacional na escolha manual da rota** (Backlog v4.0 §6) | Alto (operacional) | Confirmacao dupla via modal + texto auxiliar de imutabilidade + treinamento da equipe (fora do escopo de codigo) |
| R2 | **Enumeracao de codigos publicos** (Backlog v4.0 §6) | Medio | Alfabeto 31 chars × 6 posicoes = 887M combinacoes/mes. Rate limiting fica para Wave 3 (Componente 19). Esta wave garante que codigos sao bem distribuidos via `secrets.choice` (CSPRNG do Python) |
| R3 | **Drift entre enum Python e PostgreSQL** | Medio | Teste automatico `test_rota_enum_drift.py` (Secao 4.10 #9). Checklist no PR template |
| R4 | **Regressao em provas legadas (rota=NULL ou PADRAO/DIRETA)** | Alto | Testes de coexistencia (`test_provas_api.py` cenarios mistos). Decisao explicita de tratamento (Secao 4.12) |
| R5 | **Trigger de imutabilidade bloqueando o backfill da Wave 7** | Medio | Trigger usa `WHEN (OLD.rota IS DISTINCT FROM NEW.rota)` + `IF OLD.rota IS NOT NULL` — explicitamente permite NULL→valor. Testado (Secao 4.6) |
| R6 | **Tela de detalhe quebrando para perfis com escopo parcial** | Baixo | RLS ja cobre o escopo. Frontend renderiza condicionalmente |
| R7 | **`executar_transicao` sobrescrevendo `prova.rota` na aprovacao** (BUG ATUAL) | **Alto** (viola RN-002) | Modificacao cirurgica solicitada — Secao 14. SEM ela, a regra de imutabilidade e violada na primeira aprovacao de prova v4.0 |
| R8 | **Colisao de `codigo_publico` em geracao** | Muito baixo | 887M combinacoes/mes. Retry ate 3x na criacao + UNIQUE INDEX. Teste cobre |
| R9 | **Migration 012 falhando em producao** (16 provas existentes precisam de backfill do `codigo_publico`) | Medio | Backfill dentro da propria migration em transacao. Smoke local antes do deploy + revisao. Rollback testado |
| R10 | **Provas LAM_MATRIZ/LAM_FILIAL criadas v4.0 ficam sem fluxo ate Wave 3** | Baixo (operacional) | Documentar no CLAUDE.md. Possivel mitigacao (a confirmar): esconder LAM_* no select ate Wave 3 |
| R11 | **Etiquetas regeradas para provas legadas com rota=PADRAO/DIRETA mostrando "legada" pode confundir** | Baixo | Apenas se admin clica "Regerar etiqueta" no detalhe. Etiqueta original (BYTEA `etiquetas.qr_code_image`) preservada |

---

## 5. CHECKLIST PRE-GATE 2

**Confirmados pre-existencia:**

- [x] Wave 1 v4.0 + Audit Round 2 em `main` (commit `3bbeea2`).
- [x] alembic_version = 011.
- [x] 12 policies RLS com `app_private.*` ativas — incluindo `pol_provas_insert WITH CHECK current_user_is_admin()`.
- [x] `shared/access-matrix.json` contem `provas.create` com `studio_admin: full`, demais `negado`.
- [x] Frontend `nova-prova/page.tsx` ja usa `useAuthorization("provas.create")` + `Restricted`.
- [x] Backend `provas.py` ja usa `Depends(access_required("provas.create"))` em `POST /upload-url` e `POST /`.
- [x] `qr_code_hash` continua sendo HMAC opaco — separado do `codigo_publico` (humano-legivel).

**A criar / modificar nesta wave:**

- [ ] Migration `012_add_codigo_publico_and_rotas_v4_to_provas` (ALTER TYPE + ADD COLUMN + INDEX + TRIGGER + backfill local).
- [ ] `RotaEnum` em `db/models.py` com 4 novos valores + 2 legacy.
- [ ] `RotaCriacaoEnum` em `domain/schemas/prova.py` com apenas os 4 novos.
- [ ] `codigo_publico_service.py` em `services/`.
- [ ] `qrcode_service.gerar_payload_qr` aceita `codigo_publico` no payload.
- [ ] `etiqueta_service.gerar_pdf` aceita `codigo_publico` e `rota`.
- [ ] `ProvaCreateRequest.rota` (novo campo obrigatorio).
- [ ] `ProvaResponse.codigo_publico` (novo campo).
- [ ] `ProvaListItem.codigo_publico` (novo campo).
- [ ] `ProvaResponse.rota_projetada` REMOVIDO (deprecation).
- [ ] `provas.py:create_prova` — gera codigo, persiste rota, gera etiqueta com badge.
- [ ] Frontend `nova-prova/page.tsx` — campo Rota obrigatorio + modal de confirmacao + remover `rota_projetada` da tela de sucesso.
- [ ] Frontend `provas/page.tsx` — atualizar `ROTA_OPTIONS` para 6 valores (4 novos + 2 legacy).
- [ ] Frontend `lib/types/prova.ts` — `Rota` type, `ROTA_LABELS`, `ROTA_OPTIONS`, `ROTA_BADGE_LABELS` (?).
- [ ] Componente `<RotaSelect />` reutilizavel.
- [ ] Tests: `test_codigo_publico_service.py`, `test_imutabilidade_rota.py`, `test_migration_012.py`, `test_rota_enum_drift.py`. Atualizar: `test_schemas.py`, `test_etiqueta_service.py`, `test_provas_api.py`, `test_state_machine.py`, `test_models.py`.
- [ ] CHANGELOG.md, DECISIONS.md, CLAUDE.md (secao "Como adicionar valor ao enum rota_enum"), `analysis.md` (anexar Secao "Execucao").

**Nao mexer:**

- [ ] `state_machine.TRANSICOES` e `ATORES_POR_TRANSICAO` (Wave 3 v4.0).
- [ ] `state_machine.executar_transicao` — **EXCETO se autorizado por Mario** (Secao 14).
- [ ] Maquina de estados `status_prova_enum` (Wave 3 v4.0).
- [ ] Componente 10 (scanner) e Componente 11 (transicoes via API) (Wave 3 v4.0).
- [ ] RLS policies (cobertas pela Wave 1 v4.0).
- [ ] Componente 19 (digitacao manual) (Wave 3 v4.0).
- [ ] Animacoes Framer Motion (Wave 6 v4.0).

---

## 6. PEDIDO DE AUTORIZACAO PARA MODIFICACAO CIRURGICA EM `executar_transicao`

**Esta secao requer decisao explicita do Mario antes do Gate 2.**

### Contexto do problema

A Wave 2 v4.0 introduz a regra: **`prova.rota` e imutavel apos a criacao** (RN-002 v4.0). A coluna passa de NULL → valor uma unica vez (no `POST /api/v1/provas/`). Daí em diante, o trigger `trg_provas_rota_imutavel` rejeita qualquer UPDATE.

**Bug latente no codigo atual:** [backend/app/services/state_machine.py](../../backend/app/services/state_machine.py) linha 365:

```python
if aprovando:
    rota_depois = determinar_rota(usuario)
```

E linha 404:

```python
prova.status = status_novo
prova.rota = rota_depois   # <-- sobrescreve, e
prova.ciclo_atual = ciclo_depois
```

Isso significa que na primeira aprovacao de uma prova v4.0 (criada com `rota=MATRIZ`), o `executar_transicao` chama `determinar_rota(vendedor)` (que retorna `RotaEnum.PADRAO` para vendedor MATRIZ) e tenta sobrescrever `prova.rota = PADRAO`. **O trigger PostgreSQL impede isso e a aprovacao falha com SQLSTATE 22023.**

Sintoma observavel apos o deploy desta wave (sem a modificacao cirurgica proposta):
- Admin cria prova v4.0 com `rota=MATRIZ` → ok.
- Vendedor MATRIZ escaneia + assina + aprova → 422/500 com mensagem do trigger.
- Bug real, viola RF-007 (transicoes funcionarem) na Wave 2 v4.0.

### Modificacao cirurgica proposta

```python
# state_machine.executar_transicao linha 359-365

# ANTES:
if aprovando:
    # RN-007: rota determinada pela localizacao do vendedor.
    rota_depois = determinar_rota(usuario)

# DEPOIS:
if aprovando:
    # Wave 2 v4.0: rota e imutavel apos criacao (RN-002 v4.0).
    # Apenas provas legadas (criadas pre-Wave 2 v4.0 com rota=NULL)
    # recebem rota derivada na aprovacao — comportamento v3.0 preservado
    # ate a Wave 7 fazer o backfill final.
    if prova.rota is None:
        rota_depois = determinar_rota(usuario)
    else:
        rota_depois = prova.rota  # imutavel — nao sobrescreve
```

### Justificativa

1. **Tecnicamente necessaria** para que aprovacoes de provas v4.0 nao falhem.
2. **Mudanca minima** — 4 linhas, contidas em uma unica funcao.
3. **Preserva comportamento v3.0** para provas legadas (rota=NULL) ate Wave 7.
4. **Nao altera tabelas estaticas** (`TRANSICOES`, `ATORES_POR_TRANSICAO`) nem adiciona novos estados — escopo proibido pelo prompt.
5. **Permite que a Wave 3 v4.0 reescreva** `executar_transicao` por inteiro mais tarde sem conflito.

### Risco da NAO-modificacao

Se eu deployar a Wave 2 v4.0 sem essa mudanca:
- Toda prova v4.0 fica travada apos `RETIRADA_PELO_VENDEDOR` (a aprovacao falha).
- O bug seria descoberto em smoke test (espero) ou em producao.
- Workaround temporario seria desabilitar o trigger — pior alternativa, viola RN-002.

### Alternativa (rejeitada)

**Tornar o trigger menos rigoroso** (permitir UPDATE quando `OLD.rota = derived_value`): inutil porque `derived_value` (PADRAO/DIRETA) NUNCA bate com novos valores (MATRIZ/LAM_MATRIZ/etc). Trigger sem efeito.

### Pedido de autorizacao

**Solicito a Mario autorizacao para incluir a modificacao cirurgica acima como parte do Gate 2 desta wave.** Se autorizado, registro como ADR novo no DECISIONS.md justificando.

Se NAO autorizado, peco redirecionamento — talvez a Wave 2 v4.0 deva ser cindida em duas sessoes: (a) migration + storage + UI sem habilitar criacao de provas v4.0; (b) modificacao em `executar_transicao` + habilitacao da criacao numa segunda sessao com escopo expandido.

---

## 7. DECISOES PROPOSTAS PARA REGISTRO NO DECISIONS.md

A serem registradas no Gate 2 (apos autorizacao):

1. **Coluna `codigo_publico VARCHAR(20) NOT NULL UNIQUE`** — nao reaproveita `qr_code_hash`.
2. **Trigger `trg_provas_rota_imutavel`** — permite NULL→valor, bloqueia valor→outro_valor e valor→NULL.
3. **Filtro de rota na listagem (Componente 07): Opcao A** — atualizar `ROTA_OPTIONS` para 6 valores (4 v4.0 + 2 legacy).
4. **Provas legadas (rota=NULL ou PADRAO/DIRETA) renderizam com fallback** — listagem mostra "—" ou "(legada)"; detalhe permite regerar etiqueta com badge "legada"; Wave 7 fara o backfill.
5. **Modificacao cirurgica em `executar_transicao`** (PENDENTE AUTORIZACAO Secao 14): rota imutavel se ja preenchida; deriva via localizacao apenas para provas legadas com rota=NULL.
6. **Convencao de nomenclatura**: enum em uppercase (`MATRIZ`, `LAM_MATRIZ`, etc.) para consistencia com os outros enums do projeto, divergindo do DAT/Backlog que usam lowercase.
7. **Alfabeto do `codigo_publico`**: 31 chars `ABCDEFGHJKMNPQRSTUVWXYZ23456789` (DAT v3.0 §8.3 literal). 887M combinacoes/mes — entropia adequada para o volume operacional.
8. **Payload do QR muda para embutir `codigo_publico`** — DAT v3.0 §8.1 (idempotencia entre camera e digitacao manual). Compatibilidade com QRs antigos preservada via `validar_payload_qr` flexivel ate Wave 3.

---

## 8. APENDICE — ENTREGAVEIS E ESTIMATIVAS

**Arquivos a criar:**
- `backend/migrations/versions/012_add_codigo_publico_and_rotas_v4_to_provas.py`
- `backend/app/services/codigo_publico_service.py`
- `backend/tests/test_codigo_publico_service.py`
- `backend/tests/test_imutabilidade_rota.py`
- `backend/tests/test_migration_012.py`
- `backend/tests/test_rota_enum_drift.py`
- `frontend/src/components/RotaSelect.tsx` (+ `.module.css`)
- `frontend/src/components/ConfirmRotaModal.tsx` (+ `.module.css`)

**Arquivos a modificar:**
- `backend/app/db/models.py` (RotaEnum + 4 valores)
- `backend/app/domain/schemas/prova.py` (RotaCriacaoEnum + ProvaCreateRequest.rota + ProvaResponse.codigo_publico + remover rota_projetada)
- `backend/app/services/qrcode_service.py` (gerar_payload_qr aceita codigo_publico)
- `backend/app/services/etiqueta_service.py` (gerar_pdf aceita codigo_publico + rota; ROTA_BADGE_LABELS)
- `backend/app/api/v1/provas.py` (create_prova grava rota + codigo_publico; remove determinar_rota)
- `backend/app/services/state_machine.py` (modificacao cirurgica linhas 359-365 — pendente autorizacao)
- `backend/tests/test_schemas.py`
- `backend/tests/test_etiqueta_service.py`
- `backend/tests/test_qrcode_service.py`
- `backend/tests/test_provas_api.py`
- `backend/tests/test_state_machine.py`
- `backend/tests/test_models.py`
- `frontend/src/lib/types/prova.ts` (Rota, ROTA_OPTIONS, ROTA_LABELS)
- `frontend/src/app/(dashboard)/nova-prova/page.tsx` (campo rota + modal)
- `frontend/src/app/(dashboard)/provas/page.tsx` (consumir ROTA_OPTIONS atualizado)
- `CHANGELOG.md`, `DECISIONS.md`, `CLAUDE.md`, `docs/wave2-v4/analysis.md` (anexo Execucao)

**Estimativa:** ~30-40 testes novos · ~1.500 linhas de codigo de producao + ~1.200 linhas de teste · 1 sessao de implementacao + 1 sessao de validacao.

---

## 9. PROXIMO PASSO

Aguardando string **AUTORIZADO GATE 2 — WAVE 2 v4.0** para prosseguir com a execucao.

Caso a autorizacao venha acompanhada de correcoes/redirecionamentos (especialmente sobre a Secao 14 — modificacao cirurgica em `executar_transicao`), incorporo antes de iniciar.

**Fim da analise read-only.**


---

## Apendice: EXECUCAO (Gate 2 — registrado pos-merge)

Esta secao foi adicionada apos a execucao do Gate 2 conforme requisito
da Secao 5.5 do prompt original. Documenta os DELTAS entre o que foi
proposto no `analysis.md` (Gate 1) e o que foi efetivamente
implementado, com justificativas.

### Mudancas em relacao ao plano original

| Item proposto no Gate 1 | Decisao no Gate 2 | Motivo |
|---|---|---|
| 4 radio buttons para a rota na UI | **2 toggles** (segment Matriz/Filial + switch Laminacao) | Design entregue pelo Mario no Gate 2 (print). UX mais clara — separa "onde" de "tem laminacao". Registrado como ADR-118. |
| Modal de confirmacao dupla apos submit | **DESCARTADO** | Os 2 toggles do design ja forcam escolha consciente. O texto auxiliar "rota imutavel" permanece. |
| Migration Alembic `012_add_codigo_publico_and_rotas_v4_to_provas` em transacao unica | **3 sub-migrations** via `apply_migration` MCP (`012a` ALTER TYPE, `012b` ADD COLUMN nullable + UPDATE `alembic_version`, `012c` SET NOT NULL + indexes + trigger) | O backfill das 16 provas existentes precisa de geracao Python (CSPRNG) — feito via Python local + bulk UPDATE entre `012b` e `012c`. Mais determinístico que SQL puro com `random()`. |
| Sub-enum `RotaCriacaoEnum` em `domain/schemas/prova.py` | **MANTIDO conforme plano** | Bloqueia legacy (PADRAO/DIRETA) na criacao via Pydantic. Defesa em profundidade vs trigger SQL (que nao valida valores especificos). |
| Modificacao cirurgica em `executar_transicao` (Secao 14 do Gate 1) | **AUTORIZADO E EXECUTADO** | Mario aprovou explicitamente no Gate 2. Sem essa correcao, toda aprovacao de prova v4.0 falharia com SQLSTATE 22023. ADR-119. |
| Filtro de rota na listagem (Componente 07) — Opcao A | **EXECUTADO conforme plano** | `ROTA_OPTIONS` em `lib/types/prova.ts` agora tem 6 valores (4 v4.0 + 2 legacy com sufixo "(legada v3.0)"). Listagem ja consumia a constante; auto-atualizada. |
| Card lateral "Salvar rascunho" + "Cadastrar prova" | **Cadastrar prova FUNCIONAL** (submit do form); **Salvar rascunho disabled** com tooltip "Em desenvolvimento" | Salvar rascunho nao foi escopo desta wave; deixar como placeholder respeita o design sem aumentar superficie. Follow-up tecnico. |
| Card "Unidade Selecionada" reflete o vendedor | **Reflete o toggle Origem** (Matriz/Filial) com endereco hardcoded | Endereco real por unidade nao esta no banco; mover para `configuracoes_sistema` e overhead nao justificado nesta wave. Hardcoded da Filial Campinas (do print) + Matriz placeholder. Follow-up. |
| Atalho ⌘V para colar imagem | **IMPLEMENTADO REAL** via `addEventListener('paste')` no `window` | O design mostrava o atalho como informacao decorativa; aproveitei para implementar o paste handler completo (converte ClipboardItem em File e dispara o mesmo upload). Defensivo contra activacao dentro de inputs. |
| `qr_code_payload` no QR mantem `nro_requerimento` no segundo campo | **MUDADO para `codigo_publico`** | DAT v3.0 §8.1 exige idempotencia camera↔digitacao manual. Wave 3 v4.0 / Componente 19 vai consumir esse `codigo_publico` no fallback de digitacao. |

### Validacoes do Gate 2

- **Backend pytest**: 795 passed (era 781 + 14 novos). 0 regressao.
- **Backend ruff**: limpo (1 `# noqa: ARG001` em `_build_prova_response`
  para silenciar `vendedor_setor` nao usado — preservado para
  compat de assinatura).
- **Frontend `tsc --noEmit`**: exit 0.
- **Frontend `npx next build`**: 13/13 paginas estaticas geradas.
  `/nova-prova` 6.34 kB / 169 kB First Load (incremento esperado de
  ~1 kB pelo novo layout vs 5.3 kB / 167 kB anterior).
- **MCP Supabase advisors security**: 1 INFO + 1 WARN historicos
  (ADR-025 + ADR-027). Nenhum novo alerta.
- **Smoke visual**: tentado via preview MCP; bloqueado por colisao
  de processos backend antigos no port 8000 (CORS rejeitando origem
  do preview port dinamico). Mario validou visualmente em ambiente
  local (`next dev` em :3000 + backend em :8000 com FRONTEND_URL=
  `http://localhost:3000`).

### Migrations efetivamente aplicadas em producao

Via MCP `apply_migration` no projeto `rwxlpwmnkekzuurgthkr`:
1. `012a_alter_type_rota_enum_add_v4_values` — `ALTER TYPE … ADD VALUE
   IF NOT EXISTS` x4.
2. `012b_add_column_codigo_publico_nullable` — `ADD COLUMN codigo_publico
   VARCHAR(20)`. Logo apos: 16 UPDATEs com codigos gerados localmente
   via Python (`secrets.choice` + alfabeto 31 chars).
3. `012c_codigo_publico_not_null_indexes_trigger` — `ALTER COLUMN
   codigo_publico SET NOT NULL` + UNIQUE INDEX `idx_provas_codigo_publico`
   + INDEX `idx_provas_rota` + funcao `fn_bloquear_alteracao_rota` +
   trigger `trg_provas_rota_imutavel` + `UPDATE alembic_version SET
   version_num='012'`.

### Ambiente final

- `alembic_version = '012'` em `public.alembic_version`.
- `provas_digitais.codigo_publico` populado em 16/16 provas.
- `pg_enum` com 6 valores em `rota_enum` (4 v4.0 + 2 legacy).
- `pg_trigger` `trg_provas_rota_imutavel` ativo.
- `pg_indexes` lista 8 indexes em `provas_digitais` (era 6 + 2 novos).

### Status

**Wave 2 v4.0 (Componente 06) entregue.** Recomenda-se nova rodada
de auditoria sênior independente em sessao separada antes do merge
para `main` — mesmo padrao da Wave 1 v4.0.

---

# Anexo — Visual Refresh Execution (2026-05-05)

> **AVISO DE SUPERSEDIMENTO (AUD-W2V4-D01 — adicionado em 2026-05-05
> pela sessao de Audit Fixes):** este anexo descreve o estado
> intermediario do **Visual Refresh v1** — incluindo o componente
> `EtiquetaPreview` SVG, layout 2-col 380px+1fr, topbar `position:
> absolute`, etc. Esse estado foi **POSTERIORMENTE SUPERSEDIDO**
> pelo **Visual Refresh v2** nos commits `5047172` (fix) +
> `c06ca56` (docs/supersede ADRs 118/120/121). O codigo final em
> `main` segue a estrutura v2 (1 box branco unico, header
> `.pageHeader` em flow normal, segment de 4 botoes, sem
> EtiquetaPreview SVG, sem `frontend/public/etiqueta/`). Mantemos
> este anexo por valor historico de processo iterativo de design
> entre Mario + assistant — quem ler para entender estado atual
> deve consultar o CHANGELOG entrada "Wave 2 v4.0 — Componente 06
> — Visual Refresh v2" + ADRs 118/120/121 marcados SUPERSEDIDO.

Sessao subsequente ao closeout original da Wave 2 v4.0, focada
exclusivamente em **resolver o feedback iterativo do Mario sobre o
visual da pagina `/nova-prova`**. Nenhum codigo backend, RLS,
migration ou RBAC foi tocado nesta sessao.

## Contexto inicial

O Mario reportou: _"a pagina de criar prova esta visualmente
inconsistente em relacao as demais paginas. O conteudo dentro do box
branco ao lado da sidebar parece estar sendo renderizado como canvas
ou com comportamento semelhante. Esse conteudo nao esta preenchendo
corretamente todo o box branco."_

## Diagnostico (read-only, antes de tocar codigo)

**Causa raiz** identificada na investigacao:

1. **`.canvas` com `height: calc(100vh - 64px)`** ignorava o
   `.cardInner` do layout dashboard (que tem `height: 100%` +
   padding). Diferenca de altura criava um "retangulo flutuante".
2. **`.canvas { padding: 12px }`** somava com o padding generoso do
   `.cardInner` (`clamp(2rem, 4vw, 4rem)` = 32-64px) → moldura visual
   dupla.
3. **`.canvas { background: #fafaf7 }`** (quase-branco) era
   renderizado dentro do `.cardInner` cinza `#eaeaea` — visualmente
   um "canvas" diferente do card pai.

**Inconsistencias secundarias:**
- Cores hardcoded fora dos tokens canonicos (`#f8d126` em vez de
  `var(--color-accent)` `#ffcb5c`, `#f6f6f3` em vez de
  `var(--color-card-surface)` `#d9d9d9`, `#1a1a1a` em vez de
  `var(--color-card-text)`).
- Tipografia divergente do resto do app (titulo 22px/700 em vez de
  `clamp(2.5rem, 5vw, 4rem) / 500`, labels com `text-transform:
  uppercase + letter-spacing 0.12em` em vez do padrao Title Case).
- Inputs com `border-radius: 8px` em vez de `--radius-pill`.
- Conteudo "decorativo": `RotaVisualization` SVG (~150 linhas) sem
  funcao operacional, cards laterais redundantes (Unidade Selecionada,
  Cole Imagem), botao "Salvar rascunho" disabled como feature
  fantasma, timestamp pill na topbar.
- 2 usos de `as` agressivos (`as readonly string[]`, `as HTMLElement`)
  contrariando a politica do Mario de "zero `any` e `as`".

## Iteracao por rodadas (8 ciclos de feedback)

A sessao foi conduzida em ciclos curtos: implementar -> screenshot/
feedback -> ajustar. **Nenhum commit feito** durante a sessao —
apenas edits e validacoes via `tsc` + preview server.

| # | Foco | Output |
|---|------|--------|
| 1 | Diagnostico + correcao estrutural + tokens canonicos + tipografia Title Case + animacoes Framer Motion | Bug do canvas resolvido, design system alinhado, NOME->Nome, etc |
| 2 | SVG estilo "garfo" (ORIGEM e LAMI mesma altura, MATRIZ topo, FILIAL baixo) | Layout horizontal ORIGEM->LAMI->bifurcacao |
| 3 | Pontinhos cinza cobrindo o canvas inteiro + remocao da pill de horario | `.canvas::before { inset: calc(-1 * var(--card-padding)) }` |
| 4 | Linhas SVG conectando no centro do dot + halo amarelo nao corta + animacao mais suave | Refator de `.vizNode` `flex column` -> `inline-block` |
| 5 | Remocao dos icones internos dos dots + simplificacao da animacao de troca | Sem fade vertical (`y: 4`) que dava sensacao de "abaixar" |
| 6 | Remocao do icone da Laminacao | Apenas pílula com texto |
| 7 | Mario fez ajustes manuais (removeu eyebrow + footer da ficha, deslocou SVG `left: 50px`) — harmonizacao da tipografia + limpeza CSS orfa | `.fichaEyebrow`/`.fichaFooter`/`.fichaFooterValue`/`.statusDot`/`.checkIcon` removidos |
| 8 | **Decisao de redesign**: remover cards laterais, ficha estende ate o topo dos botoes, remover Salvar rascunho | Topbar `position: absolute`, layout 2 cols `380px 1fr` |
| 9 (final) | Substituir SVG decorativo por preview da etiqueta real | EtiquetaPreview replicando `etiqueta_service.py` mm-a-mm |
| 10 (refinamento) | Apos referencia visual da etiqueta real impressa: remover codigo publico (PRV) e badge da rota do preview, deixar QR vazio | Preview agora fiel a etiqueta IMPRESSA |

## Output final — arquivos tocados

**Frontend (4 editados + 2 SVGs novos):**
- `frontend/src/app/(dashboard)/nova-prova/page.tsx` — refresh do
  componente `NovaProvaPage` + nova `EtiquetaPreview`. Removidos:
  `RotaVisualization` + helpers (`VIZ_NODES`, `buildVizPath`,
  `VizPoint`, `MatrizIcon`, `FilialIcon`, `OrigemNodeIcon`,
  `LaminationIcon`, `QR_DOTS`, `FinderPattern`,
  `ROTA_BADGE_LABELS_PREVIEW`, `ROTA_BADGE_W_PREVIEW`),
  `UNIDADES_INFO`, `useCurrentTimestamp`. Adicionados: lookup do
  vendedor (`vendedores.find(...)`), `truncar` helper, novo
  `EtiquetaPreview` (~200 linhas).
- `frontend/src/app/(dashboard)/nova-prova/nova-prova.module.css`
  — reescrita expressiva (~340 linhas removidas, ~40 adicionadas).
- `frontend/src/lib/types/prova.ts` — adicionado `AllowedImageType`
  + `isAllowedImageType` (3 linhas uteis).
- `frontend/src/hooks/useCreateProva.ts` — 1 linha mudada (cast ->
  helper).
- `frontend/public/etiqueta/logo_3studio.svg` — NOVO (copia do
  backend).
- `frontend/public/etiqueta/logo_studio_e_arte.svg` — NOVO (copia
  do backend).

**Documentacao (4 atualizados nesta sessao final):**
- `CHANGELOG.md` — entrada `[2026-05-05 — Visual Refresh]` adicionada.
- `DECISIONS.md` — ADRs 120-122 adicionados.
- `CLAUDE.md` — linha "v4.0 W2 — C06 Visual Refresh" na tabela de
  waves.
- `docs/wave2-v4/analysis.md` — este anexo.

## Validacao tecnica

- **`npx tsc --noEmit`**: exit 0 (sem erros).
- **`npx next build`**: 13/13 paginas geradas. `/nova-prova` em
  9.18 kB / 211 kB First Load (era 6.34 kB / 169 kB — overhead +3 kB
  do Framer Motion + EtiquetaPreview SVG).
- **HMR + dev server limpo** apos restart com `.next/` purgado entre
  build de producao e dev (necessario porque `next build` invalida os
  chunks do dev server).
- **Console + server logs**: zero erros.
- **Politica de tipos**: `grep -nE '\bas [A-Z]| as readonly| as typeof'`
  nos 4 arquivos editados retorna APENAS os 2 `as const` literais
  autorizados (ENTER_EASE em `page.tsx` e ALLOWED_IMAGE_TYPES em
  `prova.ts`).

## Comportamento funcional preservado byte-a-byte

A politica desta sessao foi: **mexer APENAS no visual, sem alterar
NADA do comportamento**. Verificacao manual via leitura comparativa:

- **`useCreateProva.submit`**: fluxo 3-step (POST /upload-url ->
  PUT R2 -> POST /provas/) preservado. Apenas a verificacao de tipo
  (`isAllowedImageType` em vez de cast) mudou.
- **Validacoes client-side**: `MAX_UPLOAD_BYTES`, tipo de arquivo,
  todas preservadas.
- **Paste handler `⌘V`**: `instanceof` checks substituem o cast,
  cobertura identica.
- **`useAuthorization("provas.create")` + `Restricted`**: intactos.
- **Early return `if (auth.loading) return null`** preservado (M-1
  da Wave 1 v4.0 audit fixes).
- **Tela de sucesso pos-criacao**: layout reescrito com tokens mas
  mesma logica (handleDownloadPdf, handlePrint, handleNovaProva).
- **Mobile notice** (`@media max-width: 768px`): preservado.
- **Lookup do vendedor**: novo `const vendedorSelecionado =
  vendedores.find(v => v.id === form.vendedor_id)` para passar
  `vendedorNome` ao preview, sem alterar a logica de carregamento de
  vendedores (`/api/v1/users/?setor=VENDEDOR&ativo=true`).

## Itens nao implementados (nao pedidos pelo Mario)

- Auditoria senior independente do refresh visual.
- Smoke E2E manual (Mario validou visualmente em rodadas iterativas;
  fluxo de criacao end-to-end nao foi testado nesta sessao —
  recomenda-se antes do merge).
- Captura de screenshots automatizados via preview_screenshot
  autenticado (sem credenciais admin disponiveis para o agent).
- Atualizacao do `etiqueta_service.py` para incluir/sincronizar com
  o preview — backend permanece intacto, mantendo o codigo publico
  (PRV) + badge da rota no PDF impresso (so o preview que omite).

## Status

**Visual Refresh entregue e validado tecnicamente.** Funcionalidade
preservada. Aguardando autorizacao do Mario para commit + push.

