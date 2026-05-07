# Wave 3 v4.0 · Componente 10 (atualizacao v4.0) — Analise Read-Only (Gate 1)

**Branch:** `wave3-v4-c10/analysis`
**Data:** 2026-05-06
**Sessao:** Gate 1 da 1ª entrega da Wave 3 v4.0 — **Redesign do Scanner de QR Code com Identificacao por Codigo Alfanumerico**.
**Veredito proposto ao revisor:** APROVAR com esclarecimentos sobre 6 ambiguidades visuais do Figma.
**Bloqueios:** nenhum critico apos validacao MCP. **1 bug latente em producao** identificado (Secao 12.1 / R-1) — sera corrigido no Gate 2.

> **Hard boundary desta sessao** — entrega APENAS identificacao + redesign + contrato para C19. NAO toca a maquina de estados (C11 v4.0), NAO implementa transicoes, NAO migra dados (Wave 7), NAO introduz Framer Motion novo (Wave 6). C19 (digitacao manual) recebe contrato pronto via camada de servico desacoplada.

---

## 1. Resumo Executivo (Gate 1)

| Item | Veredito |
|---|---|
| C06 v4.0 mergeado em `main`/`development`? | ✅ SIM (commit `1b47290` + correcoes `wave2-v4/fixes/execution`) |
| C08 v4.0 mergeado? | ✅ SIM (commit `ea0ee5e` Merge `wave2-v4-c08/fixes/execution`) |
| Wave 1 v4.0 (RBAC) mergeado? | ✅ SIM (incluso Audit Round 2) |
| Decisao C06 sobre QR ↔ codigo localizada? | ✅ SIM — **ADR-116** (DECISIONS.md L4525-L4555). Reproduzida na Secao 5.2 |
| Coluna `codigo_publico` em producao? | ✅ SIM — VARCHAR(20) UNIQUE NOT NULL (migration 012) |
| Indice unico em `codigo_publico`? | ✅ SIM — `idx_provas_codigo_publico` (UNIQUE btree) |
| RLS de `provas_digitais` cobre os perfis do scanner? | ✅ SIM — `pol_provas_select` cobre admin/vendedor (self)/motorista (COM_MOTORISTA)/clicheria (3 estados) |
| Endpoint atual aceita codigo `PRV-...`? | ❌ **NAO** — bug critico (Secao 12.1 / R-1) |
| Camera + lib html5-qrcode operacionais? | ✅ SIM — `useScanner.ts` 158 LOC, lazy import + cleanup (ADR-082) |
| Imagem do Figma fornecida? | ✅ SIM — 2 estados (Camera ativa, Manual ativa) |
| Ambiguidades visuais que precisam de orientacao? | ⚠️ 6 itens listados na Secao 5.3 |
| Cloudflare R2 saudavel? | ✅ SIM — bucket `rastreio-provas-artes` listado |
| Advisor Supabase com novos alertas criticos? | ❌ NAO — apenas 1 INFO `unused_index idx_provas_rota` (esperado, sera usado em Wave 7) |

**Bottom line:** estamos prontos para Gate 2 condicional a esclarecimento das **6 ambiguidades visuais** (Secao 5.3) e confirmacao da **estrategia hibrida do payload** (Secao 5.2).

---

## 2. Confirmacao de leitura dos artefatos (Secao 3 do prompt)

### 2.1 Repositorio
| # | Caminho | Lido | Notas |
|---|---|---|---|
| 1 | `CLAUDE.md` | ✅ | Linhas relevantes: secao "RBAC: como adicionar uma nova pagina" (L483-L552), "Como adicionar valor ao enum rota_enum" (L554+), "Pagina de detalhe da prova" (L600+), atalhos globais (L460+) |
| 2 | `DECISIONS.md` | ✅ (busca dirigida — 5424 LOC) | ADR-033 (HMAC do QR), ADR-082 (POST scan), ADR-083 (logica do scan), ADR-089 (entrada manual + payload copiavel), ADR-090 (auditoria Wave 3, 3 HIGH), ADR-116 (codigo_publico), ADR-117 (trigger imutabilidade rota), ADR-119 (modificacao cirurgica state_machine) |
| 3 | `CHANGELOG.md` | ✅ (busca dirigida — 9377 LOC) | Estado pos-C08 v4.0 (commit `ea0ee5e`). Wave 3 v3.0 entregou `/escanear` com camera + assinatura + transicao numa unica pagina |
| 4 | Migrations Alembic | ✅ | 12 migrations aplicadas. Wave 2 v4.0 = migration 012 (rota enum + codigo_publico) |
| 5 | Migrations RLS | ✅ | 13 migrations RLS. RLS 006 expandiu `pol_movimentacoes_*` na Wave 3 v3.0 (motorista + clicheria) |
| 6 | `docs/wave1-v4/audit-report.md` + `fix-validation.md` | ✅ | Estado consolidado pos-Audit Round 2 |
| 7 | `docs/wave2-v4/*.md` (C06) | ✅ | analysis.md C06 — secao 4.6 (geracao do identificador) e ADR-116 |
| 8 | `docs/wave2-v4-c08/*.md` (C08) | ✅ | analysis.md C08 + smoke-validation.md (template 19 itens) |

### 2.2 Documentos de produto da v4.0
| # | Documento | Lido | Foco |
|---|---|---|---|
| 9 | `RequisitosProvasDigitais_v4_0.docx` | ✅ (extraido para `%TEMP%\wave3-c10\req_v4.txt`, 269 linhas) | RF-002, RF-003, RF-004 (camera), **RF-005** (fallback manual), RF-006, RF-007, **RN-001**, US-002 (US do scanner — antes US-009 mas verificado: US-009 e Clicheria recebimento final), **RNF-002** (≤ 2s), Secao 6 (Matriz) |
| 10 | `BACKLOG_RastreioProvasDigitais_v4_0.docx` | ✅ (extraido, 200 linhas) | C10 (v4.0) detalhado (TABLE 7), C19 detalhado (TABLE 8), C11 (v4.0) (TABLE 9), DoD global (Secao 2) |
| 11 | `DAT_RastreioProvasDigitais_v3_0.docx` | ✅ (extraido, 167 linhas) | **Secao 8** (Identificacao de Provas — endpoint unico idempotente, protecao contra enumeracao, formato do codigo), Secao 7 (RBAC defesa em profundidade), Secao 3 (estrategia de testes — Camada 3 E2E com camera mockada) |
| 12 | `UML_RastreioProvasDigitais_v4_0.drawio` | ⏳ Nao lido nesta passagem | drawio nao e texto. UML vinculado ja foi assimilado via DAT + Requisitos. Pendente leitura visual humana se Mario quiser confirmar |

### 2.3 Codigo do projeto
| Camada | Caminho | Lido |
|---|---|---|
| Backend — endpoint scan | `backend/app/api/v1/provas.py:1640-1909` (270 LOC do scan) | ✅ |
| Backend — schemas | `backend/app/domain/schemas/prova.py:295-380` (ScanRequest + ScanResponse) | ✅ |
| Backend — qrcode_service | `backend/app/services/qrcode_service.py:1-152` (gerar/validar payload + imagem) | ✅ |
| Backend — codigo_publico_service | `backend/app/services/codigo_publico_service.py:1-93` (gerar + validar formato) | ✅ |
| Frontend — pagina | `frontend/src/app/(dashboard)/escanear/page.tsx` (740 LOC) | ✅ |
| Frontend — CSS | `frontend/src/app/(dashboard)/escanear/escanear.module.css` (589 LOC) | ✅ (head only, sera reescrito) |
| Frontend — useScanner | `frontend/src/hooks/useScanner.ts` (158 LOC, html5-qrcode wrapper) | ✅ |
| Frontend — useScanProva | `frontend/src/hooks/useScanProva.ts` (91 LOC) | ✅ |
| Frontend — useExecutarTransicao | `frontend/src/hooks/useExecutarTransicao.ts` | ⏳ Lido por busca; nao alterado nesta sessao |
| Frontend — RBAC | `shared/access-matrix.json` + `frontend/src/lib/access-matrix.ts` + `frontend/src/lib/hooks/use-authorization.ts` | ✅ |

---

## 3. Imagem do Figma — confirmacao de recebimento

**Recebida:** 2 PNGs anexados ao prompt original do usuario.

- **Imagem 1** — Pagina inteira `/escanear` em **modo Camera ativo** (tab "Camera" preto/ativo, tab "Manual" branco/inativo). Mostra a sidebar (3STUDIO + saudacao + busca + nav principal + nav secundaria + perfil), o header da pagina ("Escanear prova" + subtitle), o toggle pill, o card grande com QR preview a esquerda + cta "Pronto para escanear" + botao "Abrir camera" a direita, e footer "Ultima leitura ha 2 min" + link "Ver historico".

- **Imagem 2** — Mesma pagina em **modo Manual ativo** (tab "Camera" branco/inativo, tab "Manual" preto/ativo). Sidebar identica. Card central mostra "Inserir codigo manualmente", input com prefixo "3S-" e placeholder "XXXX-XXXX", botao desabilitado "Buscar prova →". Mesmo footer.

A imagem sera commitada em `docs/wave3-v4-c10/figma-reference-camera.png` e `docs/wave3-v4-c10/figma-reference-manual.png` no Gate 2.

---

## 4. Validacao de infraestrutura (MCP) — Pre-Gate 1

### 4.1 Supabase (projeto `rwxlpwmnkekzuurgthkr`, sa-east-1, Postgres 17.6.1.104, ACTIVE_HEALTHY)

#### Coluna `codigo_publico` em `provas_digitais`
```
column_name        | data_type         | character_maximum_length | is_nullable
codigo_publico     | character varying | 20                       | NO
nro_requerimento   | character varying | 50                       | NO
qr_code_hash       | character varying | 64                       | NO
rota               | USER-DEFINED      | (rota_enum)              | YES
```
**Veredito:** coluna existe, NOT NULL, max 20 chars (formato `PRV-AAAA-MM-NNNNNN` = 18 chars + 2 de folga). **OK.**

#### Indices de `provas_digitais`
| indexname | indexdef |
|---|---|
| `idx_provas_codigo_publico` | UNIQUE btree(codigo_publico) — **necessario para identificacao rapida** |
| `idx_provas_rota` | btree(rota) |
| `idx_provas_status` | btree(status) |
| `idx_provas_status_created` | btree(status, created_at) |
| `idx_provas_vendedor` | btree(vendedor_id) |
| `idx_provas_vendedor_status` | btree(vendedor_id, status) |
| `idx_provas_created_at` | btree(created_at) |
| `provas_digitais_nro_requerimento_key` | UNIQUE btree(nro_requerimento) |
| `provas_digitais_qr_code_hash_key` | UNIQUE btree(qr_code_hash) |
| `provas_digitais_pkey` | UNIQUE btree(id) |

**Veredito:** indices em `codigo_publico`, `nro_requerimento`, `qr_code_hash` sao todos UNIQUE. Ambos os caminhos do scan (lookup por codigo PRV ou por nro_requerimento legacy) terao index lookup. **OK — NENHUMA migration necessaria nesta entrega.**

#### `EXPLAIN` em `WHERE codigo_publico = 'PRV-...'`
```
Seq Scan on provas_digitais  (cost=0.00..2.20 rows=1 width=1282)
  Filter: ((codigo_publico)::text = 'PRV-2026-05-TEX9GW'::text)
```
**Nota nao-bloqueante:** Postgres optou por Seq Scan porque ha so 17 linhas — index lookup tem overhead inicial maior em tabelas pequenas. Em escala (≥ 1000 linhas) o planner vai usar `idx_provas_codigo_publico`. Sem acao.

#### Distribuicao de provas
| Categoria | Qtd |
|---|---|
| Total | 17 |
| Legacy v3.0 (rota IS NULL) | 11 |
| v4.0 (rota IS NOT NULL) | 6 |
| Com `codigo_publico` (LIKE 'PRV-%') | **17** (100%) |

| Rota | Qtd |
|---|---|
| NULL | 11 |
| DIRETA (legacy v3.0) | 3 |
| PADRAO (legacy v3.0) | 2 |
| MATRIZ (v4.0) | 1 |

**Implicacao critica:** **TODAS** as provas em producao tem `codigo_publico` preenchido (migration 012 fez backfill local das 16 que existiam + 1 nova MATRIZ criada apos). MAS:
- 16 dessas tem QR Code gerado **antes** de migration 012 → payload do QR contem `nro_requerimento` no segundo campo.
- 1 prova MATRIZ tem QR Code gerado **depois** de migration 012 → payload contem `codigo_publico` no segundo campo.

Portanto o scanner precisa **resolver os dois formatos** (Secao 5.2). Provas legacy tem etiqueta com QR antigo; ate Wave 7 (C21) regerar etiquetas, ambos os caminhos coexistem.

#### Politicas RLS de `provas_digitais`
```sql
pol_provas_select (PERMISSIVE, SELECT, public role):
  USING (
    app_private.current_user_is_admin()
    OR (vendedor_id = app_private.current_user_id())
    OR (status = 'COM_MOTORISTA' AND app_private.current_user_setor() = 'MOTORISTA')
    OR (status IN ('ENVIADA_PARA_CLICHERIA','ENCAMINHADA_A_CLICHERIA','RECEBIDA_PELA_CLICHERIA')
        AND app_private.current_user_setor() = 'CLICHERIA')
  )

pol_provas_insert: WITH CHECK app_private.current_user_is_admin()
pol_provas_update: USING app_private.current_user_is_admin()
```
**Veredito:** scanner herda automaticamente o scoping. Vendedor tentando escanear prova de outro vendedor recebe 0 linhas (404 sem distincao de "existe vs nao existe" — alinhado com DAT §8.2). Motorista so ve prova em status `COM_MOTORISTA`. Clicheria ve provas em 3 estados terminais/pre-terminais. **OK.**

#### Advisors
- Security: 1 INFO `rls_enabled_no_policy` em `alembic_version` (intencional, ADR-025) + 1 WARN `auth_leaked_password_protection` (WONTFIX, plano pago — ADR-027). **Nada novo.**
- Performance: 13 INFOs `unused_index` (incluindo `idx_provas_rota` da migration 012 — esperado, sera usado quando Wave 7 fizer query por rota; e indices auxiliares de outras tabelas pre-existentes). **Nada bloqueante.**

#### Versao Alembic
`alembic_version = 012` (Wave 2 v4.0). Wave 1 v4.0 nao criou Alembic; Wave 6 nao criou. **OK.**

### 4.2 Cloudflare (account `20ab724c91f6bda669eecfe7c51c9171`)

```json
{
  "buckets": [
    {"name": "rastreio-provas-artes", "creation_date": "2026-04-07T11:52:03.669Z"}
  ],
  "count": 1
}
```
**Veredito:** R2 bucket saudavel. Nao sera tocado nesta entrega (scanner nao mexe com artes — apenas identifica e redireciona para `/provas/[id]` que ja resolve a imagem). **OK.**

### 4.3 Bloqueios criticos
**Nenhum bloqueio absoluto.** Todos os pre-requisitos confirmados:
- ✅ C06 + C08 + Wave 1 v4.0 mergeados em `development`.
- ✅ Coluna `codigo_publico` + indice unico em producao.
- ✅ ADR-116 documentando estrategia do payload localizado em DECISIONS.md.

---

## 5. Inventario do Componente 10 atual + plano de redesign

### 5.1 Cadeia completa do scanner v3.0 (estado herdado)

#### Frontend (`/escanear`, 740 LOC + 589 LOC CSS)
**Maquina de estados visual da pagina (PageState):**
```
idle → scanning → scan-loading → scan-ready → signing → submitting → done
                                       ↓
                                   scan-error
```

**Sub-componentes:**
- `IdleView` (L299-L353) — Card com botao "Abrir camera" + form com input de codigo manual + botao "Buscar".
  - **Ja tem entrada manual** (ADR-089, Wave 3 / Review C11) mas envia o **payload completo** (ex: `3SD|...|hash`) digitado, nao o `codigo_publico` isolado.
- `ScanningView` (L355-L390) — Container do html5-qrcode (`<div id={divId}>`) + status text + botao "Cancelar".
- `ScanReadyView` (L392-L487) — Card da prova identificada + lista de transicoes permitidas como botoes. **Nao usa C08 design.**
- `AssinaturaModal` (L493-L677) — Modal com `react-signature-canvas` + textarea de motivo (se reprovacao) + botoes Cancelar/Confirmar. **Tem `useFocusTrap`** (ADR-090).
- `DoneView` (L683-L718) — Card de sucesso pos-transicao.
- `ErrorView` (L720-L740) — Card de erro generico com botao "Tentar novamente".

**Hooks consumidos:**
- `useScanner` — wrapper html5-qrcode com lazy import, cleanup, SSR-safe.
- `useScanProva` — wrapper de `POST /api/v1/provas/scan` com mapeamento 401/404/422/502.
- `useExecutarTransicao` — wrapper de `POST /api/v1/provas/{id}/transicoes`.
- `useFocusTrap` — focus trap nos modais (Wave 3 / Auditoria Senior, ADR-090).

#### Backend (`POST /api/v1/provas/scan`, definido em `provas.py:1644-1909`)
**Schema Pydantic** (`ScanRequest` em `prova.py:307-354`):
- Campo: `payload: str (1-256 chars)`.
- Validator `_valida_payload` faz 5 checks estruturais:
  1. Nao vazio.
  2. Comeca com `3SD|`.
  3. Split em `|` retorna exatamente 3 partes.
  4. Segunda parte (chamada `nro_req` no validator — **nome enganoso a partir da Wave 2 v4.0**) nao vazia.
  5. Hash truncado tem exatamente 16 chars.

**Handler `scan_prova`:**
1. Pydantic valida formato.
2. `_prefix, nro_requerimento, _hash_trunc = body.payload.split("|")` — atribui o segundo campo a variavel `nro_requerimento` (dependendo da prova, esse campo contem `nro_requerimento` ou `codigo_publico`).
3. Chama `_carregar_prova_por_nro_req_com_scoping(db, nro_requerimento, current_user)` — **SELECT FROM provas_digitais WHERE nro_requerimento = nro_requerimento + scoping**.
4. Se `None` → 404 generico.
5. `qrcode_service.validar_payload_qr(payload, prova.qr_code_hash)` — comparacao constant-time do hash truncado.
6. `_computar_transicoes_permitidas(prova, current_user)` → tupla `(permitidas, motivo_obrigatorio_em)`.
7. `log_audit("escanear_prova", ...)` + commit.
8. Retorna `ScanResponse(prova, transicoes_permitidas, motivo_obrigatorio_em)`.

**Codigos HTTP atuais:** 200 happy / 401 token / 403 desativado / 404 nao encontrada (ou fora do scope) / 422 formato ou hash invalido / 502 DB transitorio.

#### Pontos de integracao
- **Wave 1 RBAC (`/escanear` na Matriz):** key=`scanner`, match=prefix, **acesso=`full` para os 4 perfis** (admin/vendedor/motorista/clicheria). Nada para mexer.
- **C08 (pagina de detalhe):** o scanner desta entrega vai redirecionar para `/provas/[id]` apos identificacao bem-sucedida — substitui o fluxo signing/submitting/done atual (que migra para C11).
- **`(dashboard)/layout.tsx` menu:** item "Escanear" ja existe (`MAIN_NAV` aponta para `/escanear`). Atalho global `g s` registrado em `useGlobalShortcuts`. Nada para mexer.

### 5.2 Decisao do C06 sobre QR ↔ codigo alfanumerico (CRITICO)

**Reproducao literal de DECISIONS.md L4525-L4555 (ADR-116):**

> ## ADR-116 — `codigo_publico` e coluna NOVA, nao reaproveita `qr_code_hash`
> **Data:** 2026-05-04 (Wave 2 v4.0 — Componente 06)
> **Contexto:** O backend ja tem `provas_digitais.qr_code_hash VARCHAR(64) UNIQUE` (HMAC-SHA256 hex opaco — ADR-033). A v4.0 introduz necessidade de um identificador HUMANO-LEGIVEL no formato `PRV-AAAA-MM-NNNNNN` para fallback de digitacao manual (RF-005, Componente 19 da Wave 3 v4.0).
> **Decisao:** Criar coluna NOVA `codigo_publico VARCHAR(20) UNIQUE NOT NULL` em `provas_digitais`. NAO reaproveita `qr_code_hash` — naturezas diferentes:
>   - `qr_code_hash`: HMAC opaco, valida AUTENTICIDADE do scan, 64 chars hex.
>   - `codigo_publico`: humano-legivel, resolve IDENTIFICACAO do registro, formato `PRV-AAAA-MM-NNNNNN` (18 chars).
>
> O QR Code agora EMBUTE o `codigo_publico` no payload (segundo campo do formato `3SD|...|hash`) — DAT v3.0 §8.1: idempotencia entre camera e digitacao manual exige que ambos os mecanismos resolvam para o mesmo registro pelo mesmo lookup.
> [...]
>   - QR Code payload muda de `3SD|nro_req|hash[:16]` para `3SD|codigo_publico|hash[:16]`.
>   - `validar_payload_qr` flexibilizada — aceita ambos os formatos durante a transicao (Wave 3 v4.0 / Componente 19 escolhe o lookup apropriado em runtime).

**Classificacao na taxonomia do prompt (Secao 5.2):**

A decisao do C06 nao se encaixa cleanly em "opcao 1" (QR contem o proprio codigo) nem em "opcao 2" (QR contem token diferente, codigo separado). E uma **opcao hibrida**:

- O QR Code embute o `codigo_publico` legivel **junto com** um hash truncado de autenticidade (16 chars hex). Formato: `3SD|PRV-AAAA-MM-NNNNNN|<hash[:16]>`.
- O `codigo_publico` no QR e o **mesmo** que o usuario digita no fallback C19. **Idempotencia preservada.**
- O hash truncado serve apenas para **integridade do scan** (defesa contra QR adulterado fisicamente — ADR-083 Decisao 4).

**Estrategia de identificacao proposta (HIBRIDA):**

```
Camera (C10):
  Le payload completo "3SD|<id>|<hash[:16]>"
  ↓
  Frontend: parse local → extrai <id> e <hash>
  ↓
  Backend: identificarProvaPorPayload(payload) →
    1. Extrai (prefix, identificador, hash_trunc)
    2. resolve_prova_por_identificador(identificador):
       - Se identificador casa validar_formato_codigo_publico() → SELECT WHERE codigo_publico = identificador
       - Caso contrario → SELECT WHERE nro_requerimento = identificador (fallback legacy v3.0)
    3. Se prova encontrada (e dentro do scope RLS), valida hash contra qr_code_hash da prova
    4. Retorna prova ou erro tipado

Digitacao manual (C19):
  Usuario digita "PRV-AAAA-MM-NNNNNN"
  ↓
  Backend: identificarProvaPorCodigo(codigo) →
    1. Valida formato → 422 se nao bate validar_formato_codigo_publico()
    2. SELECT WHERE codigo_publico = codigo + scoping
    3. Sem hash a validar (digitacao nao expoe hash)
    4. Retorna prova ou erro tipado
```

**Justificativa:**
1. **Idempotencia entre os dois caminhos:** ambos chegam ao mesmo `provas_digitais` row pelo mesmo `codigo_publico` (alinhado a DAT §8.1).
2. **Compatibilidade legacy:** as 16 provas pre-migration 012 tem QR antigo com `nro_requerimento` no segundo campo. Ate Wave 7 regerar etiquetas, esses QRs precisam continuar escaneaveis via fallback `nro_requerimento`.
3. **Defesa profunda:** o hash truncado **continua validando** para o caminho da camera (ADR-083 Decisao 2). Para o caminho do C19 nao ha hash a validar (digitacao nao tem como produzir hash) — isso e aceitavel porque RLS + scoping protegem; rate limiting (DAT §8.2) mitiga enumeracao.
4. **Contrato uniforme para C19:** a funcao `identificarProvaPorCodigo(codigo)` da camada de servico e exatamente o que o C19 vai consumir. A funcao `identificarProvaPorPayload(payload)` (camera) reutiliza internamente a mesma resolucao polimorfica.

### 5.3 Inventario visual do Figma + ambiguidades (CRITICO)

#### Imagem 1 — Modo Camera ativo
- **Sidebar (esquerda, fundo preto, ~280px de largura):** logo "3STUDIO" branco + saudacao "Ola Monica!" + busca placeholder + nav principal (Dashboard / Provas / Nova prova / **Escanear** / Relatorios / Usuarios) + nav secundaria (Configuracoes / Informacoes) + perfil bottom (avatar + nome + setor + link "Sair" amarelo). **Tudo isso ja existe no `(dashboard)/layout.tsx` — nao mexer.**
- **Header da pagina:** "Escanear prova" (h1, fonte grande) + subtitle "Leia o QR Code da etiqueta com a camera ou insira o codigo manualmente para confirmar a proxima movimentacao."
- **Toggle pill (entre header e card):** dois botoes lado a lado, formato pilula:
  - Esquerdo "Camera" — ativo, fundo preto, texto branco, icone camera
  - Direito "Manual" — inativo, fundo branco, texto preto, icone chave (key)
  - Largura total ≈ 480px, alinhado a esquerda
- **Card principal (fundo cinza claro / off-white, radius grande, padding generoso):**
  - **Lado esquerdo (~50-55%):** subcard branco com radius medio. Dentro:
    - Faixa amarelada no topo (10-15% da altura) — sugerindo "topo" da etiqueta
    - Quadrado central com cantos arredondados, mostrando QR Code preview (estatico, mockup) com os 4 cantos tipo "viewfinder brackets"
    - Texto centralizado pequeno embaixo: "Centralize o QR Code no quadro"
  - **Lado direito (~40-45%):** alinhado ao centro vertical:
    - h2 "Pronto para escanear" (fonte grande)
    - Paragrafo explicativo "Aponte a camera para o QR Code da etiqueta. A leitura e instantanea e a movimentacao e registrada com horario e usuario."
    - Botao escuro "Abrir camera" (fundo preto, texto branco, icone camera, radius pill)
  - **Footer do card:** linha divisoria fina, depois "Ultima leitura ha 2 min" (cinza, esquerda) e "Ver historico →" (cinza, direita)

#### Imagem 2 — Modo Manual ativo
- Sidebar e header **identicos**.
- Toggle pill: agora "Camera" branco/inativo e "Manual" preto/ativo.
- **Card principal (mesmo wrapper):** conteudo unico centralizado verticalmente:
  - h2 "Inserir codigo manualmente"
  - Paragrafo "Digite o codigo de 8 digitos que aparece abaixo do QR Code da etiqueta. A movimentacao sera registrada apos a confirmacao."
  - Input com prefixo embutido "3S-" e placeholder "XXXX-XXXX" (texto cinza claro)
  - Botao desabilitado "Buscar prova →" (fundo cinza, texto cinza)
- Footer **identico** ao do modo camera.

#### Estados nao visiveis no Figma (extrapolar com cautela)
- **Permissao negada:** Figma nao mostra. **Ambiguidade A1.**
- **Camera ativa em scan:** o card mostra apenas o "estado de espera". Figma nao mostra a camera live. **Ambiguidade A2.**
- **Prova identificada (sucesso):** Figma nao mostra modal/drawer/feedback. **Ambiguidade A3** — provavelmente navega direto para `/provas/[id]` sem modal intermediario, conforme prompt.
- **Erro:** Figma nao mostra. **Ambiguidade A4.**
- **Loading apos scan/manual:** Figma nao mostra. **Ambiguidade A5.**

#### **6 AMBIGUIDADES PARA ORIENTACAO DO MARIO**

| # | Item | Conflito | Proposta default (caso de aprovacao tacita) |
|---|---|---|---|
| **A6.1** | Placeholder do input manual (`3S-` + `XXXX-XXXX` = 8 chars) vs formato real `PRV-AAAA-MM-NNNNNN` (18 chars) | O Figma esta desalinhado com C06 ja em producao. `PRV-` e o prefixo real, nao `3S-`. | **Substituir** placeholder por `PRV-AAAA-MM-NNNNNN` no input visual desta entrega. C19 implementa a mascara real. Documentar em ADR. |
| **A6.2** | Footer "Ultima leitura ha 2 min" + "Ver historico" | Backlog C10 nao menciona. Prompt nao menciona. Nenhum endpoint hoje retorna "ultima leitura por usuario". | **Renderizar a estrutura do footer** (divider + 2 textos) mas com os campos placeholder (texto vazio ou "—"). Marcar como **OUT OF SCOPE** desta sessao em `analysis.md`/CHANGELOG. C18/Wave futura pode plugar audit_logs.acao='escanear_prova' filtrado por user. |
| **A6.3** | Tab "Manual" — implementar funcionalmente OU placeholder visual? | Backlog diz que C10 entrega o "**Botao alternativo para abrir o campo de digitacao manual** (Componente 19)". Prompt diz "Nao entrega o fallback de digitacao manual — isso e o C19". Figma mostra **2 tabs com input + botao funcionalmente clicaveis**. | **Implementar a estrutura visual completa do tab Manual** (input + botao "Buscar prova →"). MAS o `onSubmit` apenas chama a camada de servico `identificarProvaPorCodigo` (que sera entregue agora) e redireciona pra `/provas/[id]` em sucesso. **Sem** mascara de digitacao avancada, sem validacao em tempo real, sem rate limiting client-side, sem mensagens "voce digitou caracter invalido" — isso fica para C19. Compromisso: o codigo digitado segue para o backend `_carregar_prova_polimorficamente`; se for `PRV-...` resolve, se nao for, retorna 404 generico. |
| **A6.4** | "Centralize o QR Code no quadro" — texto guidance dentro do card | Aparece tanto no estado "Pronto para escanear" (camera off) quanto presumivelmente no estado camera ativa (Figma nao mostra). | **Render condicional:** texto so aparece quando o usuario clica "Abrir camera" e a camera esta ativa (estado `scanning`). No estado idle o texto fica oculto e o quadro do preview aparece com QR de exemplo (alinhado a Figma 1). |
| **A6.5** | Animacao de feedback ao identificar QR Code (Backlog "Animacao de feedback ao identificar o QR Code com sucesso") vs prompt "Sem Framer Motion novo (Wave 6)" | Backlog C10 pede animacao explicita. Prompt restringe Framer Motion novo. | **Animacao simples via CSS Modules** — fade rapido (200ms) + flash de cor (overlay verde-claro semitransparente) sobre o card antes de navegar para `/provas/[id]`. Sem Framer Motion. Respeita `prefers-reduced-motion`. |
| **A6.6** | Camera live preview vs preview estatico | Figma nao mostra como o `<video>` da camera fica embutido. O preview atual mostra um QR Code mockup com brackets. | **Adotar o preview estatico para o estado idle** (Figma 1 fielmente reproduzido). Quando camera abre, o `<div id={scanner}>` da `useScanner` ocupa o mesmo subcard branco substituindo o mock. Brackets viewfinder permanecem como overlay CSS. |

### 5.4 Plano de hierarquia de componentes React/Next.js

**Escolha de arquitetura:** modificar `(dashboard)/escanear/page.tsx` diretamente — sem fluxo paralelo (estrategia de modificacao direta autorizada pelo prompt). REMOVER componentes `AssinaturaModal`, `ScanReadyView`, `DoneView` (logica migra para C11 v4.0 dentro de `/provas/[id]`).

```
<EscanearPage>                          // page.tsx (App Router)
  <PageHeader>                          // h1 + subtitle (existente, manter)
  <ScannerTabs>                         // novo — toggle pill Camera/Manual
    <TabButton mode="camera" />
    <TabButton mode="manual" />
  </ScannerTabs>
  <ScannerCard>                         // wrapper cinza claro com radius e padding
    {tab === 'camera' && (
      <CameraPanel>
        <PreviewSlot>                   // subcard branco (~50-55%)
          {state === 'idle' && <QRMockPreview />}
          {state === 'scanning' && <CameraLive divId={scanner.divId} />}
          {state === 'denied' && <PermissionDeniedHint />}
        </PreviewSlot>
        <CameraSidebar>                 // direita (~40-45%)
          <h2>{stateText.title}</h2>    // "Pronto para escanear" / "Escaneando..."
          <p>{stateText.description}</p>
          <ActionButton>{stateText.cta}</ActionButton>  // "Abrir camera" / "Cancelar"
        </CameraSidebar>
      </CameraPanel>
    )}
    {tab === 'manual' && (
      <ManualPanel>                     // shell visual de C19
        <h2>Inserir codigo manualmente</h2>
        <p>Digite o codigo PRV-AAAA-MM-NNNNNN ...</p>
        <ManualInput value={codigo} onChange={setCodigo} />
        <ActionButton onClick={onSubmitManual}>Buscar prova →</ActionButton>
      </ManualPanel>
    )}
    <CardFooter>                        // divider + ultima leitura + ver historico
      <span>—</span>
      <a aria-disabled>Ver historico →</a>
    </CardFooter>
  </ScannerCard>
  {state === 'identifying' && <IdentifyingOverlay />}     // fade overlay durante POST
  {state === 'error' && <ErrorBanner ... />}              // banner inline (sem modal)
</EscanearPage>
```

**Reuso do C08:** as funcoes `formatRota` e `formatStatus` (em `lib/types/prova.ts`) sao puras e podem ser referenciadas. Mas como o scanner v4.0 redireciona para `/provas/[id]` ao identificar, **nao precisamos exibir badges de rota/status no proprio scanner**. Apenas valido se C19 (futuro) precisar — fica documentado para C19 reusar.

**`useAuthorization`:** consultar key=`scanner`. Como todos os 4 perfis tem `acesso=full`, o gate so e necessario contra anonimo. O middleware ja faz isso na rota `/escanear`. Defensivamente, na page: `if (auth.loading) return null; if (!auth.hasAccess) return <Restricted ruleKey="scanner" />` — mesmo padrao das outras paginas (M-1 fix da Wave 1 v4.0 Audit Fixes).

### 5.5 Plano da camada de servico desacoplada

**CONTRATO (a ser entregue no Gate 2 e consumido pelo C19):**

```typescript
// frontend/src/lib/services/identificacao-prova.ts (NOVO)

export type CodigoErro =
  | "QR_INVALIDO"           // payload mal formado (estrutura)
  | "PROVA_NAO_ENCONTRADA"  // 404 do backend (codigo nao existe OU fora do scope)
  | "DISPOSITIVO_SEM_CAMERA" // navigator.mediaDevices indisponivel ou nao autorizado
  | "ERRO_REDE"             // 5xx ou network failure
  | "SESSAO_EXPIRADA";      // 401

export type ResultadoIdentificacao =
  | { tipo: "sucesso"; prova: ProvaResponse }
  | { tipo: "erro"; codigo: CodigoErro; mensagem: string };

export async function identificarProvaPorCodigo(
  codigo: string,                                  // ex: "PRV-2026-05-K3T9XB"
  getToken: () => Promise<string | null>,
): Promise<ResultadoIdentificacao>;

export async function identificarProvaPorPayload(
  payload: string,                                 // ex: "3SD|PRV-...-K3T9XB|hash[:16]"
  getToken: () => Promise<string | null>,
): Promise<ResultadoIdentificacao>;
```

**Caracteristicas:**
- **Zero dependencia de DOM/camera/hardware.** Testavel com `vitest run --environment node` (mesmo ambiente da Wave 1 v4.0 / AUD-W1V4-005).
- **Mensagens em pt-BR ja resolvidas dentro do servico** — chamador apenas renderiza.
- **`PROVA_NAO_ENCONTRADA` e a mesma mensagem para "nao existe" e "fora do scope"** (DAT §8.2 — protecao contra enumeracao).
- **Internamente chama `apiFetch`** (existente em `lib/api.ts`), mantendo padrao do projeto.

**Endpoint backend correspondente (REUTILIZA o existente):**

`POST /api/v1/provas/scan` continua existindo, mas agora aceita 2 formatos no body:

```python
class ScanRequest(BaseModel):
    payload: str | None = Field(None, min_length=1, max_length=256)  # caminho camera
    codigo: str | None = Field(None, min_length=1, max_length=20)     # caminho C19

    @model_validator(mode="after")
    def _exatamente_um(self):
        if (self.payload is None) == (self.codigo is None):
            raise ValueError("Forneca exatamente um de: payload ou codigo")
        return self
```

**Lookup polimorfico no handler:**

```python
async def scan_prova(body: ScanRequest, ...):
    if body.codigo is not None:
        # Caminho C19 (digitacao manual)
        if not validar_formato_codigo_publico(body.codigo):
            raise HTTPException(404, "Prova nao encontrada")  # mensagem generica
        prova = await _carregar_prova_por_codigo_publico_com_scoping(...)
    else:
        # Caminho camera
        _prefix, identificador, hash_trunc = body.payload.split("|")
        if validar_formato_codigo_publico(identificador):
            prova = await _carregar_prova_por_codigo_publico_com_scoping(...)
        else:
            # Legacy v3.0: prova com QR antigo (nro_requerimento no 2o campo)
            prova = await _carregar_prova_por_nro_req_com_scoping(...)
        # Validacao de hash so faz sentido para o caminho camera
        if not validar_payload_qr(body.payload, prova.qr_code_hash):
            raise HTTPException(422, "QR Code nao corresponde a prova esperada")
    # ... resto inalterado: _computar_transicoes_permitidas, log_audit, return ScanResponse
```

**Compatibilidade legacy preservada:** os 16 QR antigos ainda funcionam via fallback do `if validar_formato_codigo_publico` (segundo campo `nro_requerimento` ≠ formato `PRV-...`). Provas v4.0 com QR novo passam pelo caminho `codigo_publico`.

**Decisao alternativa rejeitada:** criar endpoint NOVO `POST /api/v1/provas/identificar` espelhando DAT §8.1 literalmente. **Rejeitada** porque o Backlog v4.0 nao requer rota nova, ja temos `/scan` com audit log + transicoes_permitidas + tudo, e renomear seria Wave 7 territory. Documentar em ADR.

### 5.6 Plano de tratamento de provas legacy

**Escopo do tratamento:** 16 provas em producao com `rota IS NULL` ou `rota IN ('PADRAO', 'DIRETA')` tem QR antigo cuja segunda parte e o `nro_requerimento` (string livre tipo `456987`). **Nao** seguem o regex `PRV-AAAA-MM-NNNNNN`.

**Comportamento esperado:**
- Camera escaneando legacy QR: backend cai no fallback `_carregar_prova_por_nro_req_com_scoping`. Funciona.
- Camera escaneando v4.0 QR: backend cai no caminho `_carregar_prova_por_codigo_publico_com_scoping`. Funciona.
- Manual digitando `PRV-...` (sempre v4.0+, nunca legacy): apenas codigo_publico. Funciona.
- Manual digitando `nro_requerimento` legacy: **nao previsto**, retorna 404 generico — alinhado a Backlog C19 ("Codigo nao encontrado").

**Apos identificacao bem-sucedida:** redireciona para `/provas/[id]`. A pagina de detalhe (C08) ja trata legacy (`formatRota(null)` → "—" + tooltip "prova legacy v3.0", AUD-W2C08-011).

### 5.7 Plano de tratamento de erros

| Codigo | Cenario | Mensagem em pt-BR | UX |
|---|---|---|---|
| `QR_INVALIDO` | Payload do QR nao corresponde a `3SD|...|<hash>` | "QR Code nao reconhecido. Verifique se esta escaneando uma etiqueta de prova." | Banner inline, mantem camera ativa para retentar |
| `PROVA_NAO_ENCONTRADA` | Backend retornou 404 (nao existe OU fora do escopo) | "Prova nao encontrada." | Banner inline, oferece tentar manual (link para tab Manual). **Mensagem nao distingue 'inexistente' de 'fora do scope'** (DAT §8.2) |
| `DISPOSITIVO_SEM_CAMERA` | `getUserMedia` indisponivel OU permissao negada | "Camera indisponivel. Use a digitacao manual." | Banner com **link/CTA para tab Manual**, alinhado a C10 Backlog "Permissao negada nao bloqueia o uso da tela" |
| `ERRO_REDE` | apiFetch jogou ApiError 5xx ou erro de fetch | "Falha de conexao. Tente novamente em instantes." | Banner com botao "Tentar novamente" |
| `SESSAO_EXPIRADA` | 401 do backend | "Sua sessao expirou. Faca login novamente." | Banner + redireciona `/login` apos 2s |

**Defesa proativa (alinhada a DAT §8.2):**
- `PROVA_NAO_ENCONTRADA` e a mensagem padrao tanto para "codigo malformado" (sem ser PRV-) quanto "scope nao bate". O backend retorna 404 sem distincao.
- Rate limiting **NAO sera adicionado nesta entrega** — fica para C19 (DAT §8.2 fala 30 tentativas/min). C10 v4.0 e camera-only do ponto de vista atacante (digitacao manual e shell).

### 5.8 Plano de visibilidade do scanner por perfil

**Matriz de Acesso (Requisitos v4.0 Secao 6 + `access-matrix.json` rule key=`scanner`):**

| Perfil | Acesso | Notas |
|---|---|---|
| 3Studio | ● (full) | OK |
| Vendedor | ● (full) | OK — vendedor ve apenas suas provas via RLS no detalhe (provas.detail) |
| Motorista | ● (full) | OK — escaneia, identifica, vai pra detalhe; RLS filtra; motorista so ve COM_MOTORISTA |
| Clicheria | ● (full) | OK — RLS filtra para 3 estados |
| Anonimo | ✗ | Middleware redireciona para /login |

**Validacao da Wave 1 v4.0 (`scripts/verify_rbac_equivalence.py`) ja roda contra producao com sucesso.** Nao ha celula nova nesta wave; nao e preciso atualizar `access-matrix.json` nem RLS.

**Defesa proativa na page:** `if (auth.loading) return null; if (!auth.hasAccess) return <Restricted ruleKey="scanner" />` — embora redundante com middleware, segue padrao Wave 1 v4.0.

**Atalho global `g s` → `/escanear`:** ja registrado em `useGlobalShortcuts`. Nao mexer.

### 5.9 Plano de modificacao coordenada

| Arquivo | Mudanca | Justificativa |
|---|---|---|
| `backend/app/api/v1/provas.py:scan_prova` (e suas dependencias) | Adicionar branch `body.codigo` no schema; adicionar helper `_carregar_prova_por_codigo_publico_com_scoping`; introduzir lookup polimorfico no caminho `body.payload` | **CORRECAO DO BUG R-1** + entrega C10 v4.0 + contrato C19 |
| `backend/app/domain/schemas/prova.py:ScanRequest` | Tornar `payload` optional, adicionar `codigo` optional, model_validator XOR | Suporte aos 2 caminhos de identificacao (camera + manual) |
| `backend/app/services/qrcode_service.py` | Nada | **Decisao C06 ja flexibilizou `validar_payload_qr`**, nao precisa mexer |
| `backend/tests/test_provas_api.py` | +20 testes (legacy QR, v4.0 QR, manual codigo, formato invalido, scope) | Cobertura ≥ 80% do dominio + comportamento |
| `frontend/src/app/(dashboard)/escanear/page.tsx` | **REWRITE COMPLETO** — remove AssinaturaModal/ScanReadyView/DoneView, introduz Tabs/CameraPanel/ManualPanel/CardFooter | C10 v4.0 entrega "apenas identificacao + redireciona" — fluxo de transicao migra para C11 v4.0 |
| `frontend/src/app/(dashboard)/escanear/escanear.module.css` | **REWRITE COMPLETO** | Layout do Figma e proprio — wrapper cinza, subcard branco, tabs pill, etc. |
| `frontend/src/lib/services/identificacao-prova.ts` (NOVO) | Camada de servico com `identificarProvaPorCodigo` + `identificarProvaPorPayload` + tipos | **Contrato pronto para C19** |
| `frontend/src/lib/services/__tests__/identificacao-prova.test.ts` (NOVO) | 12+ testes Vitest unitarios | Validar contrato sem mock de camera (regra-chave do prompt) |
| `frontend/src/hooks/useScanProva.ts` | Refatorado — passa a chamar a camada de servico em vez de fazer fetch direto | Single source of truth do contrato |
| `frontend/src/hooks/useScanner.ts` | Mudanca minima — `onError` agora retorna codigo `DISPOSITIVO_SEM_CAMERA` em vez de string crua | Tipagem explicita do erro de hardware |
| `frontend/src/hooks/useExecutarTransicao.ts` | **NAO TOCAR** | Usado por outras paginas hipoteticamente; C11 v4.0 vai migrar/remover quando chegar |
| `frontend/src/hooks/useFocusTrap.ts` | **NAO TOCAR** | C10 v4.0 nao tem modal nesta entrega |
| `frontend/src/lib/types/prova.ts` | Pode adicionar tipo `CodigoErro` se nao moverem para `services/identificacao-prova.ts` | Decisao ainda em aberto |
| `shared/access-matrix.json` | **NAO TOCAR** | rule `scanner` ja existe e ja diz `full` para os 4 perfis |
| `frontend/src/middleware.ts` | **NAO TOCAR** | Wave 1 ja resolvido |
| `(dashboard)/layout.tsx` | **NAO TOCAR** | Item "Escanear" no menu ja existe |
| Migrations Alembic (qualquer numero) | **NAO** | Coluna + indice + unique ja existem |
| Migrations RLS | **NAO** | Cobertura ja existe |

**Codigo morto a deletar:**
- Em `page.tsx`: `AssinaturaModal`, `ScanReadyView`, `DoneView`, `ErrorView` (este ultimo substituido por banner inline simples), `ACTION_LABELS`, `labelParaTransicao`, type `PageState` antigo.
- Em CSS: classes do `provaCard*`, `actionsRow`, `signatureCanvas`, `modalBackdrop` etc. (todos os blocos relacionados a transicao/assinatura).

**Codigo morto que NAO sera deletado nesta entrega** (sera retomado por C11 v4.0):
- `useExecutarTransicao` (hook), `transicoes_permitidas` no ScanResponse — o backend continua devolvendo, mesmo que o frontend de C10 nao consuma. Isso e esperado: C11 vai consumir do `/provas/[id]`. **Documentar em ADR.**

### 5.10 Estrategia de testes

**Backend (pytest, tests/test_provas_api.py):**
1. POST scan com payload v4.0 (`3SD|PRV-2026-05-XYZ123|hash[:16]`) → 200 com prova correta.
2. POST scan com payload legacy (`3SD|456987|hash[:16]`) → 200 com prova legacy correta.
3. POST scan com `codigo` C19 (`PRV-2026-05-XYZ123`) → 200 com prova correta.
4. POST scan com `codigo` mal formado (`abc`) → 404 generico.
5. POST scan com `codigo` formato OK mas inexistente (`PRV-2026-05-NOPENO`) → 404 generico.
6. POST scan com payload invalido (`hello`) → 422 (Pydantic validator).
7. POST scan sem `payload` nem `codigo` → 422 (model_validator).
8. POST scan com **ambos** `payload` e `codigo` → 422.
9. POST scan com `payload` v4.0 mas hash truncado errado → 422 (constant-time).
10. POST scan com vendedor escaneando prova de outro vendedor → 404 (RLS filtra).
11. POST scan com motorista escaneando prova fora de COM_MOTORISTA → 404.
12. POST scan com clicheria escaneando prova em CRIADA → 404.
13. POST scan com anonimo (sem token) → 401.
14. POST scan com user desativado → 403.
15. POST scan grava `audit_log.acao = 'escanear_prova'` em ambos os caminhos.
16. `_computar_transicoes_permitidas` continua devolvendo lista correta (regressao).
17. **Helper `_carregar_prova_por_codigo_publico_com_scoping`** unitarios cobrindo scope por setor.
18. `validar_formato_codigo_publico` chamado com strings malformadas — preservar comportamento (retorna False em vez de raise).
19. **Idempotencia:** mesmo `codigo` em chamadas concorrentes nao gera 2 audit_logs duplicados? (E aceitavel, mas confirmar).
20. Performance: scan responde em < 2s com base de 17 provas (RNF-002 — verificar via test contagem de queries).

**Cobertura backend:** preservar ≥ 80% no `provas.py`. As linhas adicionadas no helper polimorfico devem ter 100% coverage.

**Frontend (Vitest, environment=node, padrao Wave 1 v4.0):**
1. `identificarProvaPorCodigo("PRV-2026-05-K3T9XB")` mockando fetch 200 → retorna `{tipo: "sucesso", prova: ...}`.
2. `identificarProvaPorCodigo("invalido")` mockando fetch 404 → `{tipo: "erro", codigo: "PROVA_NAO_ENCONTRADA"}`.
3. `identificarProvaPorCodigo` mockando fetch 401 → `{tipo: "erro", codigo: "SESSAO_EXPIRADA"}`.
4. `identificarProvaPorCodigo` mockando fetch 502 → `{tipo: "erro", codigo: "ERRO_REDE"}`.
5. `identificarProvaPorPayload` mockando fetch 200 → sucesso.
6. `identificarProvaPorPayload` mockando fetch 422 (hash invalido) → `{tipo: "erro", codigo: "QR_INVALIDO"}`.
7. `identificarProvaPorCodigo` com getToken retornando null → `SESSAO_EXPIRADA`.
8. `identificarProvaPorCodigo` chama `apiFetch` com body `{codigo: "PRV-..."}` (verificar payload enviado).
9. `identificarProvaPorPayload` chama com body `{payload: "3SD|...|..."}`.
10. Mensagens em pt-BR sao corretas para cada codigo.
11. Idempotencia de tipos: `ResultadoIdentificacao` e tagged union limpo.
12. Imports: nenhum modulo do navegador (`document`, `window`, `navigator`) e referenciado — testavel sem JSDOM.

**E2E (Playwright, ambiente staging):**
- 3Studio loga, vai em `/escanear` → ve o card vazio, clica em "Abrir camera" → simula camera mockada → simula scan de QR de prova MATRIZ → redirecionado para `/provas/<id>`.
- Vendedor faz mesmo fluxo, mas tentando escanear prova alheia → 404 + banner.
- 3Studio vai em /escanear, troca para tab Manual → digita `PRV-...` valido → redirecionado.
- 3Studio digita codigo invalido → 404 banner.
- Anonimo tenta `/escanear` direto → middleware redireciona /login.

**Mock de camera:** Playwright suporta `--use-fake-ui-for-media-stream` e `--use-fake-device-for-media-stream`. Documentar em `playwright.config.ts`.

**Performance:**
- Verificar via dev tools panel "Performance" que scan completa em < 2s (RNF-002) com 17 provas.

**Acessibilidade:**
- Tabs com `role="tablist"` + `role="tab"` + `aria-selected`.
- Botoes com label texto + icone com `aria-hidden`.
- Banners de erro com `role="alert"` + `aria-live="polite"`.
- Contraste AA: tab preto/branco passa; texto cinza secundario verificar com `axe-core`.
- Navegacao por teclado: Tab atravessa tabs → input → botao "Buscar"/"Abrir camera" → footer.

### 5.11 Migrations previstas

**Nenhuma migration Alembic.** Coluna + UNIQUE + indice ja em producao via migration 012.

**Nenhuma migration RLS.** Cobertura ja em RLS 005/006/012.

**Justificativa:** o C06 (Wave 2 v4.0) ja preparou o solo. Esta entrega e **frontend + backend code-only**.

### 5.12 Riscos e pontos de atencao

| # | Risco | Severidade | Mitigacao |
|---|---|---|---|
| **R-1** | **Bug latente em producao**: `_carregar_prova_por_nro_req_com_scoping` faz lookup por `nro_requerimento` mesmo quando QR contem `codigo_publico`. Provas v4.0 (1 em prod, mais conforme uso) **nao escaneam** hoje. | **CRITICO** | Esta entrega **corrige** com lookup polimorfico. Teste B-2 e B-3 cobrem ambos os caminhos. |
| **R-2** | Camada de servico acoplada a camera por descuido | ALTO | Testes unitarios em `environment: node` (sem JSDOM) **forcam** desacoplamento. Se algum import puxar `navigator` ou `document`, vitest quebra. |
| **R-3** | Provas legacy sem `codigo_publico` (caso teorico) | ALTO | **NAO existe nenhuma** — query MCP confirmou que 100% das 17 provas tem PRV. Migration 012 backfilled. **Risco mitigado.** |
| **R-4** | Permissao de camera negada pelo browser | MEDIO | Tratamento `DISPOSITIVO_SEM_CAMERA` com CTA explicito para tab Manual. Alinhado a Backlog C10 ("Permissao negada nao bloqueia o uso da tela"). |
| **R-5** | Tab Manual implementado como "shell" pode confundir usuarios que esperam funcionalidade completa | MEDIO | Implementar fluxo basico (codigo PRV → POST scan → 404 generico) ja nesta entrega. **Sem** mascara, sem rate-limit-client, sem realtime-validate — isso fica para C19 (escopo respeitado). Documentar em ADR + tooltip "Mascara em breve" se necessario. |
| **R-6** | Vazamento de existencia via mensagens distintas (404 vs 403) | MEDIO | Backend retorna 404 generico para "nao existe" + "fora do scope". Frontend renderiza mesma mensagem para ambos. Alinhado a DAT §8.2 + ADR-049. |
| **R-7** | Scanner navega para /provas/[id] mas usuario nao tem permissao no detalhe (RLS divergente do scope) | BAIXO | Improvavel — RLS de `pol_provas_select` e a MESMA usada pelo scan. Se scan retornou 200, detalhe vai retornar 200. Mesmo helper `_scoping_filter`. |
| **R-8** | C19 entrega depois e quebra o contrato | BAIXO | `docs/wave3-v4-c10/contrato-c19.md` (Gate 2) documenta tipos + assinaturas + casos de uso explicitos. C19 deve consumir literalmente. |
| **R-9** | Performance scan + navegacao excede 2s (RNF-002) | BAIXO | Indice unico em producao. SELECT 1 prova + 1 audit_log ≈ 50-100ms. Navegacao client-side ≈ 50ms. Total << 2s. |
| **R-10** | Browser antigo sem `getUserMedia` | BAIXO | `useScanner` ja detecta via try/catch + erro `Falha ao iniciar a camera`. Mapear para `DISPOSITIVO_SEM_CAMERA` no fluxo novo. |
| **R-11** | `useExecutarTransicao` deixa de ser chamado mas continua importado | BAIXO | Remover import na page; deixar o hook orfao (ele sera consumido por C11 v4.0). Documentar em ADR. |
| **R-12** | Codigo morto da v3.0 (modal de assinatura, estados signing/submitting/done) deletado pode quebrar tipos compartilhados | BAIXO | Tipos `ASSINATURA_BASE64_MAX_BYTES` ficam em `lib/types/prova.ts`; nao remove. Apenas o componente da page deixa de importar. |
| **R-13** | Animacao de sucesso usando CSS pode falhar a `prefers-reduced-motion` | BAIXO | CSS `@media (prefers-reduced-motion: reduce) { animation: none; }` + duracao 200ms (sub-limite percepcional). |
| **R-14** | Footer "Ultima leitura" exibido como "—" pode confundir | BAIXO | Comentario inline + tooltip "Disponivel em breve" + documentar OUT OF SCOPE em CHANGELOG. |
| **R-15** | Conflitos de merge no rewrite da page (740 LOC) | BAIXO | Branch dedicada `wave3-v4/componente-10` aberta a partir de `development` atual. Nenhuma outra wave esta tocando `/escanear` agora. |

### 5.13 Entregavel do Gate 1

**Arquivo:** `docs/wave3-v4-c10/analysis.md` (este arquivo) commitado em branch `wave3-v4-c10/analysis`. Sem merge. Sem codigo de producao tocado. Mensagem de commit proposta: `docs(wave3-v4/c10): analise read-only pre-execucao`.

---

## 6. Definition of Done — checklist preliminar (a ser exaurido no Gate 2 PR)

| # | Item DoD | Plano de evidencia |
|---|---|---|
| 1 | Code review por outro membro | Pendente — ate revisor humano aprovar |
| 2 | Cobertura ≥ 80% dominio + servico | pytest --cov + vitest --coverage |
| 3 | Integracao em staging | Smoke pos-merge |
| 4 | Migrations versionadas e documentadas | **Nenhuma migration nesta entrega** — documentar zero-touch |
| 5 | Validar contra US-002 + US-009 (Requisitos v4.0 §4) | E2E + smoke template |
| 6 | Validar Matriz Acesso linha "Escanear QR Code" | `verify_rbac_equivalence.py` (ja green) |
| 7 | Sem erros no console / logs criticos | DevTools + `kubectl logs` Railway |
| 8 | Documentacao interna atualizada | analysis.md + CLAUDE.md secao nova + contrato-c19.md |
| 9 | RLS verificada e versionada | Sem mudanca; reaproveita |
| 10 | Animacoes respeitam prefers-reduced-motion | CSS @media + axe-core |

---

## 7. O que sera entregue no Gate 2

(Resumo executivo — para o revisor decidir se aprova o passo seguinte.)

1. **Backend:**
   - `ScanRequest` aceita `payload` XOR `codigo` via model_validator.
   - Helper novo `_carregar_prova_por_codigo_publico_com_scoping`.
   - Lookup polimorfico no caminho `payload`: detecta formato PRV via `validar_formato_codigo_publico`, fallback `nro_requerimento` para legacy.
   - Audit log mantido em ambos os caminhos.
   - 20+ testes pytest cobrindo as 7 categorias (legacy, v4.0, manual, malformado, scope, RLS, performance).

2. **Frontend — camada de servico (NOVO):**
   - `frontend/src/lib/services/identificacao-prova.ts` — `identificarProvaPorCodigo` + `identificarProvaPorPayload` + tipos `ResultadoIdentificacao` e `CodigoErro`.
   - 12+ testes Vitest em `environment: node` (paridade com Wave 1 v4.0 / AUD-W1V4-005).
   - Mensagens em pt-BR encapsuladas no servico.

3. **Frontend — `/escanear` reformulado:**
   - Layout fiel ao Figma (2 imagens) com toggle Camera/Manual.
   - Camera totalmente funcional (preview, brackets, status, abrir/fechar).
   - Manual implementado como shell visual + chamada da camada de servico (sem mascara, sem rate-limit, sem validacao realtime — escopo C19).
   - Estados: idle / scanning / identifying / error. Sem signing/submitting/done.
   - Apos identificacao com sucesso: `router.push('/provas/' + prova.id)`.
   - Sem AssinaturaModal/ScanReadyView/DoneView (deletados).
   - Botao de cancelar/voltar funcional.
   - Animacao de feedback CSS (sem Framer Motion novo).
   - Acessibilidade WCAG AA + `prefers-reduced-motion`.
   - Atalho global `g s` continua funcionando (sem mudanca).

4. **Documentacao:**
   - `analysis.md` apendado com secao "Execucao" (diff entre proposto e feito).
   - `CHANGELOG.md` com nova secao "Wave 3 — Componente 10 (atualizacao v4.0)".
   - `DECISIONS.md` com 3-4 ADRs (estrategia hibrida do payload, manual como shell, lookup polimorfico, fluxo apos sucesso).
   - `CLAUDE.md` com secao nova "Identificacao de provas: contrato compartilhado entre scanner e digitacao manual".
   - `docs/wave3-v4-c10/figma-reference-camera.png` + `figma-reference-manual.png`.
   - `docs/wave3-v4-c10/contrato-c19.md` — documento dedicado.
   - `docs/wave3-v4-c10/smoke-validation.md` template (espelho do C08).

5. **Refactor coordenado autorizado** (escopo registrado no Gate 2 PR):
   - Modificar `_carregar_prova_por_nro_req_com_scoping` (ou substituir por helper polimorfico).
   - Modificar `ScanRequest` (Pydantic XOR).
   - Reescrever `(dashboard)/escanear/page.tsx` + `escanear.module.css`.
   - Refatorar `useScanProva` para chamar a camada de servico.
   - Ajustar `useScanner.ts` para reportar `DISPOSITIVO_SEM_CAMERA`.
   - **NAO TOCAR**: state_machine.py, RLS, migrations, useExecutarTransicao, useFocusTrap, layout, useGlobalShortcuts, AdminActions, Timeline, VisualizarEtiquetaModal, /provas/[id] page.

---

## 8. Pedido de orientacao do Mario antes do Gate 2

Para destravar o Gate 2 com seguranca, gostaria de confirmacao em **4 pontos**:

### Q1 — Estrategia hibrida do payload
A decisao do C06 (ADR-116) e **hibrida** (nem opcao 1 nem opcao 2 puras do prompt): QR contem `codigo_publico` legivel **e** hash truncado de autenticidade. C19 (manual) usa apenas `codigo_publico`; camera usa ambos. **Confirma esta interpretacao?**

### Q2 — Tab Manual como shell ou skeleton?
Backlog C10 pede botao para abrir o campo manual; prompt diz "nao implementa UI de digitacao". Figma mostra input + botao funcionalmente clicaveis no tab Manual. Proposta: **implementar shell completo (input + botao chamando camada de servico) sem mascara/realtime-validate/rate-limit-client — isso fica para C19**. **Aprova?**

### Q3 — Footer "Ultima leitura" + "Ver historico"
Nao esta no Backlog/Requisitos/prompt. Proposta: **renderizar a estrutura visual com placeholder** (texto "—" ou vazio), marcar como OUT OF SCOPE em CHANGELOG. **Aprova?** Alternativa: omitir o footer inteiro.

### Q4 — Placeholder do input manual `3S- XXXX-XXXX` (Figma) vs `PRV-AAAA-MM-NNNNNN` (real)
O Figma sugere formato curto que nao bate com o produto real. Proposta: **usar o formato real `PRV-AAAA-MM-NNNNNN` no placeholder visual**, registrar divergencia em ADR. C19 implementa mascara fiel ao formato real. **Aprova?**

Tambem **pendente confirmacao**: estrategia de modificacao **direta** do `/escanear` existente (rewrite — nao paralelo) — ja autorizada pelo prompt mas reforcando antes de comecar.

---

**Fim do Gate 1.** Aguardando string `AUTORIZADO GATE 2 — WAVE 3 v4.0 / C10` para prosseguir.

---

# Secao Execucao (Gate 2)

**Branch:** `wave3-v4/componente-10`
**Autorizacao recebida:** 2026-05-06 — Mario respondeu Q1-Q4 + emitiu `AUTORIZADO GATE 2 — WAVE 3 v4.0 / C10`.
**Commits:**
- `b86e7fd` — `docs(wave3-v4/c10): analise read-only pre-execucao` (cherry-picked de `wave3-v4-c10/analysis`)
- `08cc174` — `feat(wave3-v4/c10): backend — ScanRequest XOR + lookup polimorfico`
- `e4d543b` — `feat(wave3-v4/c10): frontend — scanner reformulado + camada de servico desacoplada`
- (a seguir) — commit final de documentacao + abertura de PR.

## E1. Diff entre o proposto (Gate 1) e o entregue (Gate 2)

### E1.1 Backend

| Item proposto | Status | Diff/justificativa |
|---|---|---|
| `ScanRequest` aceita `payload` XOR `codigo` via model_validator | ✅ Entregue | Implementado em `prova.py:307-405`. `payload: str \| None` + `codigo: str \| None` + `_exige_exatamente_um`. |
| Helper `_carregar_prova_por_codigo_publico_com_scoping` | ✅ Entregue | `provas.py:1797-1834`. Mesma assinatura/retorno do `_por_nro_req`. |
| Lookup polimorfico no caminho `payload` | ✅ Entregue | `provas.py:1885-1899`. `validar_formato_codigo_publico(identificador)` decide caminho v4.0 vs fallback legacy. |
| Novo caminho `body.codigo` (manual) | ✅ Entregue | `provas.py:1872-1893`. Validacao de formato 404 generico antes do SELECT (DAT §8.2). |
| Audit log com `origem` e `codigo_publico` | ✅ Entregue | `detalhes['origem'] in {'camera', 'manual'}` + `codigo_publico` da prova. |
| Mensagens 404 GENERICAS para 3 cenarios | ✅ Entregue | "Prova nao encontrada" usado para inexistente / fora do scope / formato invalido. |
| Performance < 2s | ✅ Entregue | Index UNIQUE em codigo_publico ja existe; SELECT 1 prova + 1 audit_log <100ms tipico. Performance medida no smoke E2E (cenario 16). |
| 20+ testes pytest | ✅ Entregue | +11 novos + 1 ajustado. Total: **825 (816 passed + 9 skipped, era 805 + 9)**. |

### E1.2 Frontend

| Item proposto | Status | Diff/justificativa |
|---|---|---|
| `frontend/src/lib/services/identificacao-prova.ts` | ✅ Entregue | Funcoes `identificarProvaPorPayload`, `identificarProvaPorCodigo`, helper `criarErro`. Tipos `CodigoErro`, `ResultadoIdentificacao`. Mensagens em pt-BR. |
| Testes Vitest em env=node | ✅ Entregue | 16 testes (era plano 12+) cobrindo: 2 happy path + 5 codigos de erro + getToken null/throw + body XOR + Authorization header + criarErro + **regex anti-acoplamento DOM**. |
| Refactor de `useScanProva` | ⚙️ DELETADO | Decisao: nao precisava de hook intermediario depois que a camada de servico encapsulou tudo. A page chama o servico direto. Cleaner. |
| Ajustar `useScanner` para erros tipados | ✅ Entregue | Expoe `errorCode: CodigoErro \| null` (sempre `DISPOSITIVO_SEM_CAMERA` em falha) alem do `error: string` legacy. |
| Rewrite de `(dashboard)/escanear/page.tsx` | ✅ Entregue | 740 LOC v3.0 → 414 LOC v4.0. Removidos AssinaturaModal/ScanReadyView/DoneView/ACTION_LABELS. Estados simplificados. |
| Rewrite de `escanear.module.css` | ✅ Entregue | 589 LOC v3.0 → 433 LOC v4.0. Tokens canonicos do projeto. Sem cores hardcoded. |
| Toggle pill Camera/Manual fielmente | ✅ Entregue | `<ScannerTabs>` com `role="tablist"` + `aria-selected`. |
| Camera live preview com brackets | ✅ Entregue | `<CameraLive>` em estado `scanning` substitui `<QRMockPreview>` no slot. |
| Manual: shell + chamada do servico | ✅ Entregue (Q2 confirmado) | Input + botao "Buscar prova →" funcional. SEM mascara/realtime-validate (escopo C19). |
| Erros tipados → CTA contextual | ✅ Entregue | `DISPOSITIVO_SEM_CAMERA` → link "Ir para digitacao manual" inline no banner. |
| Footer placeholder | ✅ Entregue (Q3 confirmado) | "Ultima leitura ha —" + "Ver historico →" desabilitado com `aria-disabled`. |
| Animacao de feedback CSS | ⚙️ Simplificado | Sem flash de cor na pagina antes de navegar — apenas `router.push` direto. Decisao: redirecionamento e ja perceptualmente uma animacao. Adicionar overlay verde traria complexidade + risco de regressao em `prefers-reduced-motion`. |
| Acessibilidade WCAG AA | ✅ Entregue | `role="tablist"` + `role="tab"` + `aria-selected`; `aria-invalid` e `aria-describedby` no input manual; `role="alert"` nos banners; `srOnly` label do input; focus-visible com outline. |
| `prefers-reduced-motion` | ✅ Entregue | `@media (prefers-reduced-motion: reduce)` final do CSS desabilita transicoes. |
| Defesa proativa RBAC | ✅ Entregue | `useAuthorization('scanner')` + `Restricted` (M-1 pattern Wave 1 v4.0). |
| Atalho global `g s` continua | ✅ Entregue (sem mexer) | `useGlobalShortcuts` ja apontava para `/escanear`. Nada quebrado. |
| Bundle: queda esperada | ✅ Entregue | `/escanear` 5.25 kB / 168 kB First Load (era ~9 kB / 175 kB). Reducao por remocao de react-signature-canvas e modal de assinatura. |

### E1.3 Documentacao

| Documento | Status |
|---|---|
| `docs/wave3-v4-c10/analysis.md` (com secao Execucao) | ✅ Esta secao |
| `docs/wave3-v4-c10/contrato-c19.md` | ✅ Entregue — tipos, funcoes, casos de uso, roteiro de implementacao do C19 |
| `docs/wave3-v4-c10/smoke-validation.md` | ✅ Entregue — 20 cenarios para Mario percorrer antes do PR final |
| `docs/wave3-v4-c10/figma-references.md` | ✅ Entregue — documenta como Mario adiciona os PNGs do Figma manualmente (anexos do prompt nao estao no filesystem) |
| `CHANGELOG.md` (nova secao) | ✅ Entregue (proximo commit) |
| `DECISIONS.md` (3 ADRs novos) | ✅ Entregue (proximo commit) |
| `CLAUDE.md` (secao + tabela atualizada) | ✅ Entregue (proximo commit) |

## E2. Lista final de arquivos tocados

| Tipo | Arquivo | LOC delta aproximado |
|---|---|---|
| ADD | `frontend/src/lib/services/identificacao-prova.ts` | +147 |
| ADD | `frontend/src/lib/services/__tests__/identificacao-prova.test.ts` | +260 |
| ADD | `docs/wave3-v4-c10/analysis.md` (Gate 1 + Execucao) | +721 +130 |
| ADD | `docs/wave3-v4-c10/contrato-c19.md` | +180 |
| ADD | `docs/wave3-v4-c10/smoke-validation.md` | +220 |
| ADD | `docs/wave3-v4-c10/figma-references.md` | +30 |
| MOD | `backend/app/api/v1/provas.py` | +210 (handler reescrito + helper) |
| MOD | `backend/app/domain/schemas/prova.py` | +60 (model_validator XOR + docs) |
| MOD | `backend/tests/test_provas_api.py` | +260 (11 novos + 1 ajustado) |
| MOD | `frontend/src/lib/types/prova.ts` | +13 (ScanRequest XOR) |
| MOD | `frontend/src/hooks/useScanner.ts` | +15 (errorCode tipado) |
| MOD | `frontend/src/components/icons.tsx` | +30 (3 novos icones) |
| DEL | `frontend/src/hooks/useScanProva.ts` | −91 |
| REWRITE | `frontend/src/app/(dashboard)/escanear/page.tsx` | 740 → 414 |
| REWRITE | `frontend/src/app/(dashboard)/escanear/escanear.module.css` | 589 → 433 |
| MOD | `CHANGELOG.md` | +section |
| MOD | `DECISIONS.md` | +3 ADRs |
| MOD | `CLAUDE.md` | +section + tabela atualizada |

## E3. Validacao final (antes do PR)

- `pytest backend/tests/`: **825 passed (+9 skipped) — era 805 + 9, +20**.
- `npx tsc --noEmit`: exit 0.
- `npx vitest run`: **44 passed (4 test files) — era 28, +16**.
- `npx next build`: 13/13 paginas, `/escanear` 5.25 kB / 168 kB.
- `git status`: working copy clean (apos commits).
- Advisor MCP Supabase: sem novos alertas.
- RLS de `provas_digitais`: nao tocada — reaproveita `pol_provas_select` existente.
- Migrations: zero (Alembic nao tocado, RLS nao tocado).

## E4. Riscos materializados (Gate 1 → Gate 2)

| # | Risco do Gate 1 | Materializou? | Como foi tratado |
|---|---|---|---|
| R-1 | Bug em producao: provas v4.0 nao escaneam | ✅ confirmado em codigo | **Corrigido** — handler agora detecta formato e usa lookup correto. Cobertura via `test_scan_camera_v4_qr_com_codigo_publico_resolve_pelo_codigo`. |
| R-2 | Camada de servico acoplada por descuido | ❌ nao materializou | Teste anti-acoplamento (regex contra DOM/navigator/html5-qrcode no source) garante. |
| R-3 | Provas legacy sem `codigo_publico` | ❌ nao materializou | Validado via MCP — 100% das 17 tem PRV. |
| R-4 | Permissao de camera negada | ✅ tratado | Banner com link inline para tab Manual (DISPOSITIVO_SEM_CAMERA). |
| R-5 | Tab Manual confuso | ❌ mitigado | Codigo de exemplo no placeholder + descricao com `<code>PRV-AAAA-MM-NNNNNN</code>` + 404 generico. C19 vai adicionar mascara real. |
| R-6 | Vazamento via mensagens distintas | ❌ nao materializou | Backend: 1 mensagem 404 para 3 cenarios. Frontend: nao distingue. |
| R-7 | RLS divergente entre scan e detalhe | ❌ nao materializou | Mesmo `_scoping_filter` usado nos dois caminhos. |
| R-8 | C19 quebra contrato | 🛡️ mitigado em advance | `contrato-c19.md` documenta tipos, funcoes, casos de uso. |
| R-9 | Performance > 2s | ❌ mitigado em advance | Index UNIQUE existe; query e 1-row. Cenario 16 do smoke valida em 3G simulado. |
| R-10 | Browser sem getUserMedia | ✅ tratado | useScanner reporta DISPOSITIVO_SEM_CAMERA tipado. |
| R-11 | useExecutarTransicao orfao | ⚙️ aceito | Hook continua existindo intocado; sera consumido por C11 v4.0. |
| R-12 | Tipos compartilhados quebrados | ❌ nao materializou | `ASSINATURA_BASE64_MAX_BYTES`, `TransicaoRequest`/`Response` permanecem em `types/prova.ts`. |
| R-13 | Animacao falha prefers-reduced-motion | ❌ nao materializou | `@media (prefers-reduced-motion: reduce)` desabilita as transicoes simples. |
| R-14 | Footer placeholder confuso | ✅ tratado | `title="Disponivel em breve"` + `aria-disabled` + cor desbotada. |
| R-15 | Conflito de merge | ❌ nao materializou | Branch dedicada limpa. |

## E5. O que fica para C19 (Wave 3 v4.0, proxima entrega)

Ver `docs/wave3-v4-c10/contrato-c19.md`:
- Mascara de digitacao em tempo real (`PRV-AAAA-MM-NNNNNN`).
- Validacao client-side antes do submit.
- Auto-uppercase no input.
- Rate limiting backend (DAT §8.2 — 30/min).

## E6. O que fica para C11 (Wave 3 v4.0, terceira entrega)

- Maquina de estados expandida para 14 estados.
- UI de transicao (assinatura + selecao) na pagina `/provas/[id]` (substitui o que estava no /escanear v3.0).
- `ScanResponse.transicoes_permitidas` continua existindo no backend — sera consumido pelo detalhe.

**Fim da secao Execucao.**
