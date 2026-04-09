# Changelog

---

## [2026-04-09 — Sessao 12] — Wave 2: Auditoria de engenharia senior + hardening (semi-pronta)

### Contexto

Apos o fechamento da Wave 2 na Sessao 11 e o hotfix `params` da Sessao 11b,
Mario pediu uma auditoria de engenharia senior com olhar critico e metodico:
"procure com um olhar critico e metodico possiveis falhas e erros e me ajude
a deixar a Wave 2 o mais robusta e feita da melhor forma possivel."

Escopo autorizado: todos os componentes Wave 2 (C06/C07/C08/C09). Wave 0
e Wave 1 intocadas salvo autorizacao explicita; itens que pertencam a Wave 3
devem ser feitos na Wave 3.

### Metodo da auditoria

1. **Leitura dirigida** (nao delegada — lida diretamente para manter o
   contexto): DECISIONS.md completa, CHANGELOG recente, `docs/db/schema.sql`,
   todas as migrations RLS, todo codigo Wave 2 (backend: provas.py,
   configuracoes.py, services/*, schemas/*; frontend: paginas, hooks, types;
   testes completos).
2. **Verificacao empirica** de hipoteses suspeitas:
   - `typing.get_type_hints()` em runtime nas funcoes de `provas.py`
   - `fpdf2` gerando PDF com `€`, smart quotes, em-dash, CJK, emoji
   - `ruff check app/ tests/`
   - `npx tsc --noEmit`
   - `next lint` + `next build`
   - Rodar os 250 testes backend existentes antes de mexer em nada
3. **Catalogo de issues** agrupadas por severidade + plano de execucao.
4. **Execucao priorizada** apos autorizacao por fase do Mario.

### Diagnostico: 17 issues encontradas

**Criticos (2):**
- **C1** — `fpdf2` com Helvetica builtin: **crash** com caracteres fora de
  Latin-1 (€, smart quotes, em/en dash, CJK, emoji). Vetor real: nome
  colado do Word vira 500 silencioso. Pior: como `gerar_pdf` rodava APOS
  o commit, deixava banco inconsistente.
- **C2** — `LocalizacaoEnum` usado em anotacoes de tipo de `provas.py` sem
  import no top-level. Python 3.14 (PEP 649) deixa o modulo carregar, mas
  `typing.get_type_hints()` quebra com `NameError`. Confirmado via runtime.

**Altos (5):**
- **A1** — `gerar_pdf` depois do commit: falha tardia deixa prova criada
  sem PDF.
- **A2** — Parametro `expected_content_type` em `_validar_upload_no_r2`
  era codigo morto (handler nunca passava o valor).
- **A3** — Dropzone de `/nova-prova` descartava arquivo invalido silenciosamente.
- **A4** — Divergencia RLS `movimentacoes` x backend scoping (latente Wave 3).
- **A5** — `nro_requerimento` case-sensitive no banco + validator so com
  `.strip()`: `REQ-001` e `req-001` passavam como linhas distintas.

**Medios (6):**
- **M1** — `sanitize_filename` perdia extensao ao truncar em 100 chars.
- **M2** — `sanitize_filename` permitia stems so-de-pontos (`"..."`).
- **M3** — `template_etiqueta.nome` aceitava qualquer string (sem whitelist).
- **M4** — `ProvaResponse` e `ProvaDetailResponse` duplicados com
  nullability divergente em `rota_projetada`.
- **M5** — `VisualizarEtiquetaModal` tinha race condition no cleanup de
  Blob URLs (closure vars criadas apos o cleanup rodar).
- **M6** — Filtro de periodo usa UTC mas UI exibe hora local (ADR-048 ja
  aceita; documentacional).

**Baixos (4):**
- **B1** — `RotaIndeterminavel` deveria ser `RotaIndeterminavelError` (N818).
- **B2** — Imports desordenados em 5 arquivos (I001 ruff).
- **B3** — Linha longa em `state_machine.py:195` (E501).
- **B4** — Imports inline em `test_provas_api.py` (code smell).

### Decisoes do Mario

- **A4** → Nao mexer. O que eh da Wave 3 deve ser feito nela.
- **A5** → Seguir com Camada 1 only (normalizacao no validator),
  **sem** migration case-insensitive index (Wave 0 fora de escopo).
- **C1** → Baixar fonte DejaVu TTF e commitar no repo (opcao "a").
- **M6** → Deixar para Wave 4 quando Dashboard entrar.

### Itens executados (13 de 13 autorizados)

#### Criticos — fixes

**C1 — Fonte Unicode DejaVu**
- Download `DejaVuSans.ttf` (757KB) + `DejaVuSans-Bold.ttf` (706KB) +
  `LICENSE` do release oficial `dejavu-fonts/dejavu-fonts@version_2_37`
  no GitHub. Licenca Bitstream Vera (permissiva, uso comercial permitido).
- `backend/app/services/fonts/` criado com os 3 arquivos.
- `etiqueta_service.py` reescrito para registrar a familia `DejaVu` via
  `pdf.add_font()` e substituir todas as chamadas `set_font("Helvetica")`.
- Path resolvido via `Path(__file__).resolve().parent / "fonts"` (cwd-safe).
- Italico nao bundled — economizou ~700KB e foi trocado por regular em
  tamanho menor com mesmo destaque visual.
- `_register_fonts()` levanta `RuntimeError` se TTFs ausentes (falha rapida).
- **Testes**: 5 casos novos em `test_etiqueta_service.py` cobrindo acentos
  Latin-1, euro, smart quotes, em/en dash, CJK+emoji.
- **ADR-053** documenta a decisao completa.

**C2 — `LocalizacaoEnum` top-level import**
- Adicionado na tupla de imports de `app.db.models` no topo de `provas.py`.
- Removido o import local `from app.db.models import LocalizacaoEnum` de
  dentro de `_carregar_prova_com_scoping` (o comentario `# local import to
  avoid cycles` era enganoso — nunca houve ciclo real).
- Verificado em runtime: `typing.get_type_hints()` passa sem `NameError`
  em `_carregar_prova_com_scoping` e `_build_prova_response`.
- Descoberto via `ruff check` (F821) + smoke test `python -c "import typing"`.

#### Altos — fixes

**A1 — `gerar_pdf` antes do commit**
- Reordenado `create_prova`: template + PDF gerados em `try/except`
  dedicado **antes** de qualquer `db.add`.
- Falha de PDF → **422** com mensagem descritiva + `_cleanup_r2` +
  **zero** mudanca no banco.
- `created_at` do PDF passa a ser `datetime.now(tz=UTC)` gerado no
  backend (consistente com `now()` do Postgres dentro do segundo).
- **Teste novo**: `test_create_prova_pdf_generation_failure_rollsback_before_commit`
  garante que `db.commit` **nunca** eh chamado quando `gerar_pdf` lanca.
- **Teste ajustado**: `test_create_prova_commit_failure_rollback_and_cleanup`
  ganhou 1 `_scalar(DEFAULT_TEMPLATE)` extra no `side_effect` porque o
  template agora e carregado antes do commit.
- **ADR-054** documenta a reordenacao.

**A2 — Codigo morto removido**
- Parametro `expected_content_type` e bloco de verificacao "declarou PNG
  mas subiu JPG" removidos de `_validar_upload_no_r2`.
- Docstring substituida por explicacao honesta: "o content_type declarado
  no step 1 nao eh persistido entre requests, entao aqui so olhamos o
  conteudo real do arquivo no R2".
- **ADR-057** documenta a remocao (e por que ADR-032 continua valido —
  magic bytes sao a barreira real).

**A3 — Erros inline no dropzone de nova-prova**
- Novo state `arquivoError: string | null` em `nova-prova/page.tsx`.
- `handleFileSelect` agora diferencia 3 caminhos: tipo invalido →
  "`Tipo de arquivo nao permitido (X). Use JPG ou PNG.`"; tamanho > 10MB →
  "`Arquivo excede o limite de 10 MB (Y MB).`"; OK → limpa erro.
- Erro renderizado no proprio campo do dropzone via classe `inlineError`
  (ja existente no CSS module).
- `handleNovaProva` (reset pos-sucesso) tambem limpa o erro.

**A5 — Normalizacao case-insensitive**
- Novo helper `_normalize_nro_requerimento(v)` em `prova.py`:
  - `.strip().upper()`
  - Rejeita vazio pos-strip com mensagem explicita
  - Valida charset via `NRO_REQ_RE` (existente)
- Aplicado em `UploadUrlRequest._valida_nro_req` e
  `ProvaCreateRequest._valida_nro_req` — refs para o mesmo helper.
- `REQ-001` e `req-001` agora geram o mesmo valor → conflito cai no 409
  duplicate normal.
- **Testes**: 6 casos em `TestNormalizeNroRequerimento` +
  `TestUploadUrlRequestNormalization` + `TestProvaCreateRequestNormalization`.
- **ADR-055** documenta a decisao (Camada 1 only, sem index no banco).

#### Medios — fixes

**M1 + M2 — `sanitize_filename` robusto**
- Separa stem + ext via `rpartition(".")`.
- `.strip("._")` no stem (remove pontos/underscores nas bordas) — protege
  `...`, `..`, `.hidden`.
- Trunca stem preservando `ext` dentro do limite de 100 chars (formula:
  `max_stem = max_total - len(ext) - 1`).
- Fallback `"arquivo"` quando stem fica vazio.
- **Testes**: 9 casos em `TestSanitizeFilename`.

**M3 — Whitelist de `template_etiqueta.nome`**
- Nova constante `TEMPLATE_NOMES_VALIDOS = frozenset({"padrao"})`.
- `validar_template_etiqueta` rejeita qualquer nome fora da whitelist.
- Mensagem de erro lista os validos.
- **Testes**: 5 casos em `TestValidarTemplateEtiquetaNomeWhitelist`.
- **ADR-056** documenta.

**M4 — Consolidacao de types frontend**
- `rota_projetada: Rota` → `Rota | null` em `ProvaResponse`.
- `ProvaDetailResponse` virou `type alias` de `ProvaResponse` (sem
  divergencia possivel entre criacao e detalhe).

**M5 — Fix race condition no modal**
- `VisualizarEtiquetaModal.tsx`: substitui closure vars por um
  `createdUrls: string[]` que acumula toda blob URL criada durante o
  effect.
- Criacao das 2 URLs + check `aborted` eh atomico; se `aborted` foi
  marcado entre a criacao e o `setState`, as URLs sao revogadas
  imediatamente dentro do `load()`.
- Cleanup do effect itera pelo array acumulado — zero dependencia de
  closure capture timing.

**M6** — Nao executado (deferido para Wave 4 quando Dashboard chegar).

#### Baixos — fixes

- **B1** — `RotaIndeterminavel` → `RotaIndeterminavelError` em 3 arquivos
  (state_machine, provas, test_state_machine).
- **B2** — `ruff check --fix` resolveu imports desordenados em 6 arquivos.
- **B3** — Linha longa quebrada em 2 em `state_machine.py:195`.
- **B4** — `test_provas_api.py`: consolidados 7+ imports inline no bloco
  do topo; removido helper `qrcode_service_module_import()` obsoleto;
  removido `noqa: E402` do import `ProvaDigital, RotaEnum, SetorEnum,
  StatusProvaEnum` no meio do arquivo.

### Metricas antes/depois

| Gate | Antes (Sessao 11b) | Depois (Sessao 12) |
|---|---|---|
| Testes backend | 250 passed | **278 passed** (+28) |
| Coverage backend | 92% | **93%** |
| `ruff check app/ tests/` | 9 errors | **All checks passed** |
| `tsc --noEmit` frontend | clean | clean |
| `next lint` | clean | clean |
| `next build` | clean | clean |
| `typing.get_type_hints(provas.*)` | NameError | **OK** |
| PDF com `€`, smart quotes, CJK, emoji | Crash | **Gera sem crash** |

### Testes novos (28 adicionados)

```
test_schemas.py:
  TestNormalizeNroRequerimento (6)
  TestUploadUrlRequestNormalization (1)
  TestProvaCreateRequestNormalization (1)
  TestSanitizeFilename (9)
  TestValidarTemplateEtiquetaNomeWhitelist (5)

test_etiqueta_service.py:
  test_pdf_acentos_latin1_ok
  test_pdf_euro_simbolo_ok
  test_pdf_smart_quotes_ok
  test_pdf_em_en_dash_ok
  test_pdf_chars_fora_do_font_nao_crashea

test_provas_api.py:
  test_create_prova_pdf_generation_failure_rollsback_before_commit
```

### Assets novos

```
backend/app/services/fonts/DejaVuSans.ttf        757 KB
backend/app/services/fonts/DejaVuSans-Bold.ttf   706 KB
backend/app/services/fonts/LICENSE               8.8 KB  (Bitstream Vera)
```

### Arquivos modificados

**Backend (codigo):**
- `backend/app/api/v1/provas.py` — C2, A1, A2, B1
- `backend/app/services/state_machine.py` — B1, B3
- `backend/app/services/etiqueta_service.py` — C1 (reescrito)
- `backend/app/services/qrcode_service.py` — B2
- `backend/app/domain/schemas/prova.py` — A5, M1, M2, B2
- `backend/app/domain/schemas/configuracao.py` — M3, B2

**Backend (tests):**
- `backend/tests/test_provas_api.py` — A1 + B4 (limpeza de imports)
- `backend/tests/test_etiqueta_service.py` — C1 (5 testes Unicode)
- `backend/tests/test_state_machine.py` — B1 rename + B2
- `backend/tests/test_schemas.py` — A5 + M1 + M2 + M3 (22 testes)
- `backend/tests/test_configuracoes_api.py` — B2 cleanup import nao usado

**Frontend:**
- `frontend/src/app/(dashboard)/nova-prova/page.tsx` — A3
- `frontend/src/app/(dashboard)/provas/[id]/VisualizarEtiquetaModal.tsx` — M5
- `frontend/src/lib/types/prova.ts` — M4

**Contexto:**
- `DECISIONS.md` — ADR-053, 054, 055, 056, 057, 058
- `CHANGELOG.md` — esta secao

### Riscos residuais conhecidos (documentados, nao bugs)

1. **A4 latente** — Quando a Wave 3 popular `movimentacoes`, decidir se a
   RLS vira mais permissiva ou o backend vira mais restritivo. Nao eh bug
   agora (tabela vazia). Registrar ADR novo na Wave 3.
2. **M6 timezone** — Filtro de periodo no `/provas` usa UTC; ADR-048 ja
   aceita. Reavaliar no Dashboard da Wave 4.
3. **CJK/emoji fonts** — fpdf2 loga warning e renderiza como tofu (`□`).
   Aceitavel; se virar requisito, adicionar `NotoSansCJK` (~10MB).

### Nao executado (pendente de autorizacao futura)

- **A5 Camada 2** — index case-insensitive no banco. Camada 1 (validator)
  cobre 100% dos writes via HTTP. Reavaliar quando volume crescer.

### ADRs novos

- **ADR-053** — Fonte Unicode DejaVu Sans para geracao de PDF
- **ADR-054** — `gerar_pdf` antes do commit em `POST /api/v1/provas/`
- **ADR-055** — Normalizacao case-insensitive do `nro_requerimento`
- **ADR-056** — Whitelist fechada de `template_etiqueta.nome`
- **ADR-057** — Remocao do parametro morto `expected_content_type`
- **ADR-058** — Auditoria da Wave 2 + hardening pre-commit (meta-ADR do processo)

### Status

**Wave 2 semi-pronta** — todos os 13 itens autorizados executados, 278
testes passando, ruff/tsc/lint/build limpos, PDF Unicode resolvido,
`get_type_hints()` funciona em runtime. O label "semi-pronta" reflete:
(a) A4 pendente para Wave 3, (b) M6 cosmetico pendente para Wave 4,
(c) alguns itens foram reavaliados (CJK fonts, A5 Camada 2) mas
deliberadamente nao executados ate haver necessidade real.

---

## [2026-04-09 — Sessao 11b] — Hotfix Next 14: `params` nao e Promise

### Contexto
Apos a entrega da Sessao 11, Mario clicou no botao "Ver detalhes" de uma
prova no `/provas` e recebeu no browser:
```
Unhandled Runtime Error
Error: An unsupported type was passed to use(): [object Object]
  src/app/(dashboard)/provas/[id]/page.tsx (41:22) @ params
```

### Causa raiz
Na Sessao 11 escrevi a pagina de detalhe assumindo **Next 15 App Router**,
que tornou `params` uma `Promise<{id: string}>` e exige unwrap via
`use()` do React:
```tsx
import { use } from "react";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function ProvaDetalhePage({ params }: PageProps) {
  const { id } = use(params);  // ← quebra em Next 14
  ...
}
```
Mas o `package.json` declara `"next": "^14.2"`. **No Next 14.2, `params`
e um objeto sincrono**, nao uma Promise. O React `use()` hook espera
uma thenable e quebra com o erro acima quando recebe um `[object Object]`
comum.

**Por que `tsc --noEmit` nao pegou?** Porque o tipo declarado
(`Promise<{id: string}>`) e valido para o TypeScript — o compiler nao
sabe a assinatura runtime que o Next vai passar. O bug so aparece em
runtime, quando a rota e acessada.

**Por que o `next build` nao pegou?** Porque build faz static generation
das rotas `○` e deixa as rotas `ƒ` (dinamicas) sem pre-render. Como
`/provas/[id]` e `ƒ`, o handler so roda em request real.

### Fix aplicado

`frontend/src/app/(dashboard)/provas/[id]/page.tsx`:

```diff
- import { use, useCallback, useState } from "react";
+ import { useCallback, useState } from "react";

  ...

- interface PageProps {
-   params: Promise<{ id: string }>;
- }
+ interface PageProps {
+   params: { id: string };
+ }

  export default function ProvaDetalhePage({ params }: PageProps) {
-   // Next 15 compat: `use()` para unwrap da Promise<params>
-   const { id } = use(params);
+   // Next 14: `params` e sincrono (plain object). Next 15+ passaria a ser
+   // Promise<{id}> e exigiria `use(params)` — mas este projeto esta no 14.2.
+   const { id } = params;
```

### Validacao

- `npx tsc --noEmit` → limpo
- `rm -rf .next && npm run build` → limpo. `/provas/[id]` 5.77 kB
  (identico ao pre-fix)
- Bundle e output de build identicos ao da Sessao 11 — so mudou a forma
  de consumir `params`.

### Arquivos alterados

```
M  frontend/src/app/(dashboard)/provas/[id]/page.tsx  (import + tipo + consumo de params)
M  CHANGELOG.md                                       (esta secao)
```

### Licao aprendida

**Nao assumir Next 15** em projetos que declaram `"next": "^14.x"`. O
upgrade para Next 15 e uma decisao pendente — quando/se acontecer, a
assinatura de `params` muda (entre outras coisas) e esse trecho vai
precisar voltar para `use(params)`.

Adicionado um comentario no proprio codigo explicando o que mudaria no
Next 15, para qualquer futuro upgrade saber onde mexer.

---

## [2026-04-09 — Sessao 11] — Wave 2: Componente 08 (Visualizacao de Prova + Modal Etiqueta/QR) — FECHAMENTO DA WAVE 2

### Contexto
Quarto e ultimo componente funcional da Wave 2. Entrega a tela de detalhe
de uma prova digital com: dados completos, preview da arte via signed URL,
placeholder de timeline de movimentacoes (contrato estavel para Wave 3),
download direto do PDF da etiqueta e — por pedido explicito do Mario
durante o planejamento — um modal "Visualizar etiqueta" que mostra o PDF
completo + QR code isolado lado a lado. 4 ADRs novos (049-052). Ativacao
do botao "Ver detalhes" no Componente 07. **Com esta sessao a Wave 2
esta funcionalmente completa** — os 4 componentes (06, 07, 08, 09) estao
em producao e validados.

### Entregas

**Backend — Schemas Pydantic (editar `domain/schemas/prova.py`):**
- `MovimentacaoResponse` — contrato pronto para Wave 3. Inclui `usuario_nome`
  e `usuario_setor` via JOIN. NAO expoe `assinatura_digital` (fica como
  prova server-side apenas).
- `MovimentacaoListResponse` — `{items, total}`. Na Wave 2 sempre
  retorna `items=[]`.
- `ImagemUrlResponse` — `{url, expires_at}` para presigned GET do R2.
- **Mudanca**: `ProvaResponse.rota_projetada` passa de `RotaEnum` para
  `RotaEnum | None`. Permite edge case onde o vendedor original mudou
  de setor/localizacao depois da criacao da prova. Nao e breaking —
  cliente TypeScript trata `| null` e o POST /provas/ continua populando
  sempre (vendedor validado na criacao).

**Backend — Endpoints (5 novos em `api/v1/provas.py`):**

1. **`GET /api/v1/provas/{prova_id}`** — dados completos (`ProvaResponse`).
   - `get_current_user` + `_scoping_filter` (ADR-049 — reutiliza o helper
     do Componente 07).
   - JOIN com `usuarios` para `vendedor_nome` + `vendedor_localizacao`.
   - Segunda query para carregar o `Usuario` completo e calcular
     `rota_projetada` via `determinar_rota(vendedor)`. Retorna None
     gracefully quando vendedor nao e mais VENDEDOR com localizacao.
   - 404 se nao encontrada ou scoping esconde (nao 403 — nao vazar existencia).

2. **`GET /api/v1/provas/{prova_id}/imagem-url`** — URL assinada do R2 (ADR-050).
   - Mesma dep + scoping. Valida acesso antes de gerar URL.
   - Chama `r2_signed.generate_presigned_get_url(prova.imagem_url, expires_in=900)`.
   - TTL fixo de 15 minutos.
   - 502 se R2 falhar.
   - Retorna `ImagemUrlResponse`.

3. **`GET /api/v1/provas/{prova_id}/movimentacoes`** — historico (ADR-051).
   - Valida scoping via `_carregar_prova_com_scoping`.
   - SELECT real em `movimentacoes` JOIN `usuarios` ORDER BY created_at ASC.
   - Na Wave 2 retorna sempre `{items: [], total: 0}` porque nao ha transicoes.
   - Contrato HTTP pronto para Wave 3 popular sem mudanca.

4. **`GET /api/v1/provas/{prova_id}/etiqueta.pdf`** — re-download do PDF.
   - Scoping + SELECT da `Etiqueta` associada (snapshot imutavel).
   - `_carregar_template_etiqueta(db)` para ler o template atual.
   - Re-gera via `etiqueta_service.gerar_pdf(...)` usando o
     `qr_code_image` BYTEA armazenado.
   - Retorna `Response(content=pdf_bytes, media_type="application/pdf",
     headers={"Content-Disposition": f'attachment; filename="etiqueta-{nro_req}.pdf"',
     "Cache-Control": "private, no-cache"})`.
   - `nro_requerimento` sanitizado no filename (so alfanum + `-_`).

5. **`GET /api/v1/provas/{prova_id}/qr-code.png`** — QR isolado (ADR-052).
   - Scoping + SELECT do `qr_code_image` BYTEA direto (sem regerar).
   - `Response(content=png_bytes, media_type="image/png", headers={
     "Content-Disposition": 'inline; filename="qr-code.png"',
     "Cache-Control": "private, max-age=300"})`.
   - Cache 5 min porque QR code e imutavel apos criacao (RN-001).

**Backend — Helpers reutilizados em 4 dos 5 endpoints novos:**
- `_carregar_prova_com_scoping(db, prova_id, user)` — nova funcao interna
  que encapsula o SELECT com scoping + JOIN. Retorna `(prova, vendedor_nome,
  vendedor_localizacao) | None`. 100% reutilizada nos 4 endpoints que
  precisam validar acesso + carregar a prova.
- `_build_prova_response(prova, vendedor_obj, vendedor_nome, vendedor_localizacao)`
  — fabrica o `ProvaResponse` com `rota_projetada` calculada via
  `determinar_rota` com try/except para `RotaIndeterminavel`.

**Backend — Testes (`tests/test_provas_api.py`, 21 novos):**
- **Detail (7):** happy admin, rota_projetada para filial, rota_projetada
  None para ex-vendedor, vendedor scoping happy, vendedor scoping other
  owner 404, not found, no auth 401.
- **Imagem-url (4):** happy com mock `generate_presigned_get_url`, scoping
  404, not found, R2 failure 502.
- **Movimentacoes (3):** empty on Wave 2 (items=[], total=0), scoping
  404, not found.
- **Etiqueta.pdf (4):** happy com QR real gerado por `qrcode_service` +
  header Content-Disposition contendo nro_req sanitizado + body `%PDF-...%%EOF`,
  scoping 404, etiqueta ausente 404 (edge defensivo), no auth 401.
- **Qr-code.png (3):** happy com magic bytes PNG no body + Cache-Control
  private, scoping 404, etiqueta ausente 404.
- **Total do arquivo**: **59 testes** (15 C06 + 23 C07 + 21 C08).
- **Cobertura**: `provas.py` subiu para **93%** (de 90%). Global manteve **92%**.
- **Suite completa**: **250 passed, 1 warning**.

**Validacao contra banco real (Fase 4):**
Script `scripts/reproduce_prova_detail.py` (temporario, removido apos
validacao) que invoca os 5 handlers diretamente contra producao usando a
prova `DEBUG-5002C5CD` (que e real — tem etiqueta com QR code armazenado):
  1. GET /{id} -> ProvaResponse com `vendedor_nome="Mario Souza"`,
     `vendedor_localizacao="FILIAL"`, `rota_projetada="DIRETA"`
  2. GET /{id}/imagem-url -> URL mockada (R2 GET e so o mock; em producao
     vai buscar a URL real do objeto)
  3. GET /{id}/movimentacoes -> `total=0` (confirma Wave 2 vazio)
  4. GET /{id}/etiqueta.pdf -> 2474 bytes, comeca com `%PDF-`,
     Content-Disposition `attachment; filename="etiqueta-DEBUG-5002C5CD.pdf"`
  5. GET /{id}/qr-code.png -> 538 bytes, magic PNG `89 50 4E 47`,
     Cache-Control `private, max-age=300`
  6. **Bonus scoping**: admin + vendedor (mario) ambos acessam a prova
     (Mario e o vendedor da prova debug, entao o scoping `vendedor_id ==
     user.id` permite)

Todos os 5 endpoints validados end-to-end. Script removido.

**Frontend — Tipos (editar `lib/types/prova.ts`):**
- `ProvaDetailResponse` — espelho de `ProvaResponse` com `rota_projetada: Rota | null`.
- `MovimentacaoResponse` — inclui `usuario_nome`, `usuario_setor`,
  `status_anterior/novo`, `motivo_reprovacao`, `ciclo`, `rota_no_momento`.
- `MovimentacaoListResponse` — `{items, total}`.
- `ImagemUrlResponse` — `{url, expires_at}`.
- `Setor` — tipo auxiliar exportado para usar em `MovimentacaoResponse`.

**Frontend — Hook (`hooks/useProvaDetail.ts`):**
- Parametros: `provaId`, `getToken`.
- Executa **3 requests em paralelo** via `Promise.allSettled`:
  1. `GET /api/v1/provas/{id}`
  2. `GET /api/v1/provas/{id}/imagem-url`
  3. `GET /api/v1/provas/{id}/movimentacoes`
- **Tolerancia a falhas parciais**: se o detail falha, a pagina inteira
  exibe erro. Se apenas a imagem-url falha, exibe placeholder "Falha ao
  carregar arte" mas mantem o resto. Se movimentacoes falha, lista fica
  null e a UI exibe fallback.
- Estado: `{loading, error, prova, imagemUrl, imagemError, movimentacoes}`.
- Expoe `reload()` para retry.

**Frontend — Modal VisualizarEtiquetaModal (`provas/[id]/VisualizarEtiquetaModal.tsx`):**
- Componente cliente isolado. Aceita props `{provaId, nroRequerimento,
  isOpen, onClose, getToken}`.
- Ao abrir, dispara **2 fetches em paralelo com token** (usando `fetch`
  direto porque `apiFetch` tenta `response.json()` e esses endpoints
  retornam binarios):
  1. `/api/v1/provas/{id}/etiqueta.pdf` -> `blob` -> `URL.createObjectURL`
  2. `/api/v1/provas/{id}/qr-code.png` -> `blob` -> `URL.createObjectURL`
- Layout do modal:
  - Overlay escuro com blur (`backdrop-filter: blur(2px)`)
  - Container preto (superficie escura consistente com modais de `/usuarios`)
  - Header: titulo "Etiqueta — {nro_req}" + botao close
  - Body grid 2 colunas (colapsa em <1000px):
    - Esquerda (flex 2): `<iframe>` com `src={pdfBlobUrl}` em container branco
    - Direita (flex 1): container branco com `<img src={qrBlobUrl}>` 280x280
      (`image-rendering: pixelated` para preservar bordas das celulas) +
      texto "Escaneie com a camera do sistema"
  - Footer: botao "Baixar PDF" (usa `<a download>` com o mesmo blob URL) +
    botao "Fechar"
- **Cleanup**: ambas as object URLs sao revogadas no cleanup do `useEffect`
  para evitar memory leak.
- **ESC fecha** via listener global. **Click no backdrop fecha** via
  comparacao `e.target === e.currentTarget`.
- **Body scroll lock** enquanto modal aberto.

**Frontend — Pagina Detalhe (`provas/[id]/page.tsx`):**
- Client Component usando `use()` para unwrap do `params: Promise<{id: string}>`
  (Next 15 compat).
- Estado local: `etiquetaModalOpen` + `imgLoadError`.
- Layout:
  - **Breadcrumb** no topo: `<Link href="/provas">← Voltar para provas</Link>`
    (ADR-Q08.3 aprovado — volta simples, back do browser preserva filtros).
  - **Header**: titulo monospace (`nro_requerimento`) + subtitulo
    (`nome`) + badge grande de status colorido.
  - **Grid 2 colunas** (colapsa em <1000px):
    - **Coluna esquerda (dados)**:
      - Campo "Cliente"
      - Campo "Vendedor" + chip de `vendedor_localizacao`
      - Campo "Rota": `formatRota()` exibe `prova.rota` ou
        "`prova.rota_projetada` (projetada)" quando `rota IS NULL`
      - Campo "Ciclo atual"
      - "Criada em" / "Atualizada em" formato pt-BR com horario
      - Campo condicional "Motivo do cancelamento" em estilo italic/vermelho
        se `motivo_cancelamento` presente
      - **Botoes de acao**:
        - **"Visualizar etiqueta"** (primary) → abre modal
        - **"Baixar etiqueta (PDF)"** (secondary) → fetch direto +
          download sem abrir modal
    - **Coluna direita (arte)**:
      - `<img src={imagemUrl.url}>` com `object-fit: contain` em
        container 360px max
      - **Placeholder tolerante a falhas**: se `imagemError` (endpoint
        `/imagem-url` falhou), exibe mensagem + tip; se `imagemUrl`
        carrega mas o `<img>` dispara `onError` (URL assinada retornou
        403/404 do R2, tipico das provas seed LIST-TEST-* com objeto
        fake), exibe "Nao foi possivel carregar a arte — a prova pode
        ter sido cadastrada com um arquivo que nao existe mais no storage"
  - **Seccao Timeline (placeholder Wave 2)**:
    - Titulo "Historico de movimentacoes"
    - Se `movimentacoes.total === 0`: bloco central com "Esta prova
      ainda nao teve movimentacoes. A timeline visual fica disponivel
      quando a prova for escaneada pela primeira vez."
    - Se populada (Wave 3+): lista `<ul>` de `<li>` com header
      (`status_anterior → status_novo` + data), meta
      ("Por {nome} ({setor}) · Ciclo N · {rota}"), e bloco de
      `motivo_reprovacao` se presente. **Esse codigo ja esta pronto**
      e nao sera tocado na Wave 3 — so vai comecar a exercitar quando
      a primeira movimentacao for inserida.
  - **`<VisualizarEtiquetaModal>`** montado sempre (render condicional
    interno via `if (!isOpen) return null`).
  - Mobile: `mobileNotice` (mesmo padrao das outras paginas).

**Frontend — CSS (`provas/[id]/detalhe.module.css`, 560 linhas):**
- Tokens reutilizados do `globals.css`.
- Badges de status com as mesmas cores do `/provas` (consistencia visual).
- Timeline com border-left amarela (acent color) em cada item.
- Modal em superficie escura com sub-containers brancos para o PDF e QR.
- Responsive breakpoints em 1000px (grid 2→1 col) e 768px (mobile notice).

**Frontend — Ativacao do botao no Componente 07 (editar `provas/page.tsx`):**
- Import `<Link>` do Next.
- `<button disabled title="...">Ver detalhes</button>` →
  `<Link href={`/provas/${p.id}`} className={styles.detailBtn}>Ver detalhes</Link>`
- CSS `.detailBtn` ajustado: removido `:disabled`, adicionado
  `text-decoration: none` para `<a>`.

### Verificacao

- **Backend**: `../.venv/Scripts/python -m pytest --cov=app -q` →
  **250 passed, 1 warning, 92% cobertura global**. `provas.py` 93%.
  Zero regressao.
- **Frontend**: `npx tsc --noEmit` limpo. `npm run build` limpo apos
  `rm -rf .next`. Bundles:
  - `/provas/[id]` **5.77 kB** (164 kB first load) — rota dinamica `ƒ`
  - `/provas` 4.56 kB (163 kB)
  - `/nova-prova` 4.46 kB, `/configuracoes` 3.2 kB, `/usuarios` 4.9 kB
- **Reproduce contra banco real**: 5/5 endpoints validados, bonus
  scoping vendedor OK.
- **Advisor Supabase**: inalterado (1 INFO ADR-025 + 1 WARN ADR-027
  WONTFIX). Zero novos WARN.

### Pegadinhas resolvidas

- **`apiFetch` nao serve para binarios**: o helper `apiFetch<T>` no
  frontend chama `response.json()` internamente, o que quebra com
  `/etiqueta.pdf` e `/qr-code.png`. Solucao: usar `fetch` direto no
  `VisualizarEtiquetaModal` e no `handleDownloadEtiqueta` da pagina,
  com header Authorization manual e `response.blob()`.
- **Object URLs vazam memoria sem cleanup**: `URL.createObjectURL(blob)`
  aloca ref que nunca expira ate `URL.revokeObjectURL()`. Fix: cleanup
  function no `useEffect` revoga ambas (pdf + qr) quando o modal
  desmonta ou fecha.
- **Next 15 App Router: params sao Promise**: `PageProps` agora tem
  `params: Promise<{id: string}>` em vez de `{id: string}` direto.
  Solucao: `const { id } = use(params)` com `use()` do React.
- **Race de dois requests em paralelo**: no hook `useProvaDetail`, se
  o componente desmontar enquanto os 3 fetches estao pendentes, o
  `setState` vai atualizar estado de componente desmontado (React
  warning). Solucao: **nao implementado** por simplicidade — no caso
  real o unmount so acontece via navegacao, e a tela ja e substituida
  (ninguem ve o warning). Registrado como possivel polish futuro.
- **Imagem 403 do R2 para provas seed**: todas as provas
  `LIST-TEST-*` foram seedadas com `imagem_url=provas/seed/.../fake.jpg`
  que nunca existiu no bucket. A signed URL e gerada normalmente, mas
  o GET retorna 404 do R2. A pagina trata com `onError` no `<img>`
  exibindo placeholder amigavel.

### Arquivos criados/editados

```
A  backend/tests/test_provas_api.py           (+21 testes, 59 total)
A  frontend/src/hooks/useProvaDetail.ts
A  frontend/src/app/(dashboard)/provas/[id]/page.tsx
A  frontend/src/app/(dashboard)/provas/[id]/VisualizarEtiquetaModal.tsx
A  frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css

M  backend/app/domain/schemas/prova.py        (+3 schemas, rota_projetada opcional)
M  backend/app/api/v1/provas.py               (+5 endpoints, helpers privados)
M  frontend/src/lib/types/prova.ts            (+4 interfaces, tipo Setor)
M  frontend/src/app/(dashboard)/provas/page.tsx (botao → Link ativo)
M  frontend/src/app/(dashboard)/provas/provas.module.css (.detailBtn para <a>)
```

Zero mudanca em: migrations, RLS, models, services (audit, qrcode, etiqueta,
r2_signed, state_machine), outros routers, outros testes, Componentes
06/07/09 em si (exceto a ativacao do botao no 07).

### Documentos atualizados (incrementais)
- `CHANGELOG.md` — esta secao.
- `DECISIONS.md` — ADRs 049 (scoping reutilizado), 050 (signed URL
  endpoint dedicado), 051 (endpoint movimentacoes vazio na Wave 2),
  052 (QR PNG endpoint dedicado com cache).

### Definition of Done
- [x] Lint + typecheck + build verdes (backend e frontend)
- [x] Cobertura global >= 90% (manteve 92%)
- [x] 18+ testes novos (21 entregues)
- [x] Reproduce contra banco real validada (5/5 endpoints + scoping)
- [x] Botao "Ver detalhes" do Componente 07 ativado como `<Link>`
- [x] CHANGELOG + DECISIONS atualizados
- [x] Advisor Supabase sem novos WARN
- [x] Zero mudanca em Wave 1 / Componentes 06/09
- [ ] Smoke manual pendente (proximo item do Mario)

### Proximo passo
Smoke manual da tela de detalhe pelo Mario:
  - `/provas` → click "Ver detalhes" em qualquer linha
  - Verifica carregamento do detail (dados + badge de status)
  - Verifica tratamento de erro da arte nas provas seed (placeholder)
  - Verifica que na prova `123456` (Prova de teste com arte real) a
    imagem carrega de verdade via R2 signed URL
  - Click "Visualizar etiqueta" → modal abre com PDF + QR lado a lado
  - Click "Baixar PDF" dentro do modal → download direto
  - ESC / click backdrop fecha modal
  - Click "Baixar etiqueta (PDF)" fora do modal → download direto sem abrir modal
  - Click "← Voltar para provas" → volta para listagem (back do browser
    preserva filtros aplicados)

Apos smoke OK, a **Wave 2 esta FORMALMENTE COMPLETA**. Na sessao seguinte,
vou fazer a consolidacao da documentacao + planejamento da Wave 3.

---

## [2026-04-09 — Sessao 10b] — Wave 2: Fixes pos-Componente 07 (seed --cleanup, uvicorn cwd, .env resolution)

### Contexto
Apos a entrega da Sessao 10 (Componente 07), Mario rodou
`python scripts/seed_list_test_provas.py --cleanup` esperando marcar as
5 provas LIST-TEST-* como CANCELADA, e na sequencia tentou subir o
uvicorn. Dois problemas bateram simultaneamente:

  1. O cleanup **nao executou** (provas continuaram ativas no banco)
  2. O uvicorn quebrou com `ModuleNotFoundError: No module named 'app'`

### Problema 1: `--cleanup` nao funcionava

**Causa raiz**: o script `seed_list_test_provas.py` tinha um bug no fluxo
do `main()`. A logica era:

```python
async def main():
    ...
    existing = ... # select LIST-TEST-*
    if existing:
        print("Ja existem X provas. Abortando.")
        return 1  # ← aborta aqui

    # seed + tests
    ...

    if "--cleanup" in sys.argv:  # ← nunca alcanca quando ha provas existentes
        await mark_test_provas_as_cancelled()
```

A flag `--cleanup` so era checada **apos** o seed + testes, ou seja, a
unica forma de ativar o cleanup era rodando **sem provas existentes** —
exatamente o caso oposto do uso real. Quando Mario rodou com `--cleanup`
depois do seed, o script detectou as 5 provas, printou "Abortando" e
retornou antes de tocar no cleanup.

**Fix aplicado**: `--cleanup` agora e um **modo standalone**. Quando a
flag esta presente, o script pula o seed inteiro e so executa a limpeza:

```python
if is_cleanup_only:
    # Le as LIST-TEST-*, marca como CANCELADA, retorna.
    return 0

# ... seed mode (so sem --cleanup) ...
```

**Validacao**: rodei `python scripts/seed_list_test_provas.py --cleanup`
e confirmei via Supabase MCP que todas as 5 LIST-TEST-* estao agora
`CANCELADA` com motivo explicito (LIST-TEST-005 mantem seu motivo
original do seed; LIST-TEST-001..004 receberam o motivo novo "Registro
de seed da Sessao 10 — smoke do Componente 07..."). Depois **removi o
script** do repo (`scripts/seed_list_test_provas.py` deletado).

### Problema 2: uvicorn `ModuleNotFoundError: No module named 'app'`

**Causa raiz dupla:**

**(2a)** O comando que Mario rodou foi:
```
(.venv) C:\Users\mario.souza\provaDigital>python -m uvicorn app.main:app --reload
```
A partir do **repo root**, nao de `backend/`. O pacote `app/` vive em
`backend/app/`, entao o import `app.main` nao resolve no repo root.

O fix naive seria sempre rodar o uvicorn de `backend/`, mas isso e
fragil — qualquer um que abrir o repo na raiz vai bater no mesmo erro,
e eu mesmo dei a instrucao errada varias vezes ao Mario.

**(2b)** Apos corrigir com `--app-dir backend` (que diz ao uvicorn para
adicionar `backend/` ao `sys.path`), o import passou, mas o
`pydantic-settings` em `app/core/config.py` quebrou com 10 erros de
validacao:
```
ValidationError: 10 validation errors for Settings
supabase_url: Field required
...
```
Porque `model_config = {"env_file": ".env"}` resolve o caminho
**relativo ao cwd**, e o cwd era o repo root. O `.env` do projeto vive
em `backend/.env` — o `config.py` nao estava encontrando.

**Fix aplicado (2a)**: `.claude/launch.json` — adicionado
`"--app-dir", "backend"` aos `runtimeArgs` do config "backend". Agora a
linha completa e:
```json
"runtimeArgs": [
  "-m", "uvicorn", "app.main:app",
  "--reload",
  "--host", "0.0.0.0",
  "--app-dir", "backend"
]
```
Assim o launcher funciona a partir do repo root (que e o cwd padrao).

**Fix aplicado (2b)**: `backend/app/core/config.py` — troquei
`env_file: ".env"` por caminho absoluto resolvido relativamente ao
proprio arquivo:

```python
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"

class Settings(BaseSettings):
    ...
    model_config = {
        "env_file": str(_ENV_FILE),
        "env_file_encoding": "utf-8",
    }
```

Agora o `.env` e encontrado **independentemente do cwd** — seja rodando
do `backend/`, do repo root, ou de qualquer outro diretorio. O
`_BACKEND_DIR` resolve para `backend/` porque `config.py` vive em
`backend/app/core/config.py` (3 niveis acima).

**Validacao end-to-end**:
```bash
# Do repo root (cwd = provaDigital/):
.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8766

# INFO:     Started server process [72280]
# INFO:     Uvicorn running on http://127.0.0.1:8766
# curl http://127.0.0.1:8766/health -> {"status":"ok"}
```

Funcionou. 19 rotas carregadas, health check respondendo 200.

### Formas de rodar o backend apos este fix

Qualquer uma funciona agora:

**Opcao 1** — do repo root (recomendada):
```bash
cd C:/Users/mario.souza/provaDigital
.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --reload
```

**Opcao 2** — do diretorio backend:
```bash
cd C:/Users/mario.souza/provaDigital/backend
../.venv/Scripts/python -m uvicorn app.main:app --reload
```

**Opcao 3** — via `.claude/launch.json` (o que o Claude Code usa):
Basta o config "backend" estar no launch.json — ja fixado.

### Validacao pos-fix

- `pytest -q` do `.venv`: **229 passed, 1 warning**. Zero regressao.
- `from app.main import app` do repo root: 19 routes OK.
- `curl /health` do repo root: 200 OK.
- Supabase MCP: todas as 5 LIST-TEST-* estao CANCELADA.
- Banco `configuracoes_sistema` e demais tabelas intactos.

### Arquivos alterados

```
D  scripts/seed_list_test_provas.py          (removido — cleanup concluido)
M  backend/app/core/config.py                (env_file com caminho absoluto)
M  .claude/launch.json                       (--app-dir backend nos runtimeArgs)
M  CHANGELOG.md                              (esta secao)
```

### Licao aprendida (para Componente 08 em diante)

**Config baseada em cwd e sempre uma armadilha futura**. Qualquer path
relativo no projeto (env_file, imports, leitura de templates, etc) deve
ser resolvido a partir de `Path(__file__).resolve()`, nunca de `cwd`.
Vou auditar o restante do backend procurando caminhos relativos
problematicos antes do Componente 08.

Scripts "--cleanup" do tipo destruct/reset devem ser sempre tratados
como modos standalone — primeira coisa no main, antes de qualquer check
de estado. Nunca depender de alcancar a flag no final do fluxo normal.

### Proximo passo
Uvicorn funcionando, cleanup concluido, pytest verde. Aguardando Mario
validar o smoke manual de `/provas` no browser (agora com o uvicorn
rodando certo) e OK para iniciar o **Componente 08 — Visualizacao de
Prova (Detalhe)**.

---

## [2026-04-09 — Sessao 10] — Wave 2: Componente 07 (Listagem, Pesquisa e Filtros de Provas)

### Contexto
Terceiro componente funcional da Wave 2. Entrega a tela de listagem de
provas digitais com filtros combinaveis, paginacao offset-based e scoping
por setor (RF-012, RF-013, US-012). Consumido pelo fluxo diario da 3Studio
(admin ve tudo) e pelos demais perfis com visibilidade restrita via RLS
replicada no backend. 5 ADRs novos (037, 038, 046, 047, 048). Zero mudanca
na Wave 1 ou nos Componentes 06/09.

### Entregas

**Backend — Schemas Pydantic (`domain/schemas/prova.py`):**
- `ProvaListItem` — versao slim de ProvaResponse para listagem (sem
  `imagem_url`, `qr_code_hash`, `rota_projetada`, `motivo_cancelamento`).
  Inclui `vendedor_nome` populado via JOIN com `usuarios`.
- `ProvaListResponse` — mesmo shape de `UserListResponse` (items, total,
  page, page_size, pages) — ADR-037.

**Backend — Endpoint GET /api/v1/provas/ (`api/v1/provas.py`):**
- Dependencia `get_current_user` (nao admin-only, ADR-046). Qualquer
  usuario autenticado ativo pode listar, mas o escopo do que ve depende
  do setor.
- Helper `_scoping_filter(user)` — retorna a clausula WHERE base que
  replica a semantica das RLS policies de `provas_digitais`:
    * `is_admin=true`              → None (ve tudo)
    * `setor=VENDEDOR`             → `vendedor_id == user.id`
    * `setor=MOTORISTA`            → `status == COM_MOTORISTA`
    * `setor=CLICHERIA`            → `status IN (ENVIADA, ENCAMINHADA, RECEBIDA clicheria)`
    * `setor=STUDIO sem is_admin`  → `func.false()` (defensivo)
- Query params (todos opcionais exceto paginacao):
    * `page` (ge=1, default 1)
    * `page_size` (ge=1, le=100, default 20)
    * `status` (StatusProvaEnum, alias de query param)
    * `periodo_inicio` / `periodo_fim` (date ISO YYYY-MM-DD)
    * `vendedor_id` (UUID)
    * `cliente` (ILIKE `%termo%`)
    * `rota` (RotaEnum)
    * `busca` (ILIKE em `nome` OR `nro_requerimento`)
- Periodo inclusivo no dia final (ADR-048): `created_at < fim_dt + 1 day`.
- Count query + data query separadas, ambas com os mesmos filtros.
- Data query usa JOIN com `usuarios` para trazer `vendedor_nome`.
- ORDER BY `created_at DESC`, paginacao via `LIMIT/OFFSET`.

**Backend — Testes (`tests/test_provas_api.py`, 23 novos):**
- Helpers novos: `_make_prova` (fabrica ORM), `_list_result`
  (mock de `result.all()` para JOIN), `_capture_list_stmts`
  (captura ambos os statements para inspecao via `_compiled_sql`),
  `_compiled_sql` (compila contra dialect PostgreSQL para verificar
  clausulas WHERE aplicadas).
- **Happy paths** (admin sem filtros, filtro status, filtro periodo,
  filtro vendedor_id, filtro cliente ILIKE, filtro rota, filtro busca
  nome OU nro_req, filtros combinados).
- **Paginacao** (offset+limit correto, calculo de pages com borda
  21/10=3, total=0 retorna items=[] pages=0).
- **Scoping por setor** (VENDEDOR ve so as proprias, MOTORISTA so
  COM_MOTORISTA, CLICHERIA so status de clicheria, admin sem scoping).
- **Validacao de query params** (status invalido 422, rota invalida 422,
  page=0 422, page_size=101 422, date mal formatada 422, sem auth 401).
- **Testes totais do arquivo**: 38 (15 do Componente 06 + 23 do Componente 07).
- **Cobertura**: `provas.py` subiu de 87% → 90%. Global subiu de 91% → 92%.
  Total de **229 testes passando** (203 + 26 anteriores + 23 novos).

**Validacao contra banco real (Fase 4):**
`scripts/seed_list_test_provas.py` — script que insere 5 provas fake
diretamente no banco (via ORM sync, sem passar pelo endpoint de criacao
para evitar upload R2):
  - `LIST-TEST-001` Rotulo Verao Amarelo / ACME Corp / CRIADA / rota NULL
  - `LIST-TEST-002` Caixa Embalagem / Beta Industries / COM_MOTORISTA / PADRAO
  - `LIST-TEST-003` Rotulo Geleia / Gamma Foods / ENVIADA_PARA_CLICHERIA / PADRAO
  - `LIST-TEST-004` Tag Jeans Delta / Delta Fashion / RECEBIDA_PELA_CLICHERIA / DIRETA
  - `LIST-TEST-005` Selo Premium / Epsilon Ltda / CANCELADA / rota NULL

  Cada uma com `created_at` em dias distintos (0, 1, 2, 3, 5 dias atras)
  para exercitar filtro de periodo. Etiquetas + audit_logs gravados junto.

  Apos o INSERT, invoca `list_provas` handler diretamente (sem HTTP):
  1. Como admin sem filtros → ve 7 provas (5 seed + 2 historicas)
  2. Como admin com `status=CRIADA` + `busca=LIST-TEST` → 1 item
  3. Como admin com `cliente=Gamma` → 1 item
  4. Como admin com `rota=PADRAO` + `busca=LIST-TEST` → 2 itens
  5. Como vendedor Mario Souza → ve 7 provas (todas as suas, incluindo as
     seed porque o script gravou Mario como vendedor_id)

  Validacao 100% OK contra producao. As 5 provas seed ficam **ativas** no
  banco para Mario validar o frontend `/provas`. Apos validacao manual,
  rodar `python scripts/seed_list_test_provas.py --cleanup` marca todas
  como CANCELADA com motivo explicito.

**Frontend — Tipos (`lib/types/prova.ts`, editado):**
- `ProvaListItem` interface (espelho do schema Pydantic).
- `ProvaListResponse` interface.
- `STATUS_LABELS: Record<StatusProva, string>` — labels pt-BR reutilizaveis
  pelo Componente 08.
- `ROTA_LABELS: Record<Rota, string>`.
- `STATUS_OPTIONS: readonly StatusProva[]` — ordem canonica para selects.
- `ROTA_OPTIONS: readonly Rota[]`.

**Frontend — Hook (`hooks/useListProvas.ts`):**
- Estado `{loading, error, data: ProvaListResponse | null}`.
- `load(filters)` — dispara GET com todos os filtros como query string.
  Usa `latestReqRef` para descartar respostas de requests antigos quando
  chegam fora de ordem (race protection).
- `loadDebounced(filters)` — variante com 300ms debounce para campos
  textuais. Cancela timer anterior.
- Cleanup de timer no unmount.

**Frontend — Pagina (`(dashboard)/provas/page.tsx`):**
- Envolto em `<Suspense>` porque `useSearchParams` do Next.js 14 App
  Router exige durante pre-render.
- **Filtros persistentes na URL** via `useSearchParams` (Q07.3 aprovada):
    * Mudancas em selects/dates chamam `router.replace("/provas?...")`
      imediato
    * Mudancas em campos textuais (busca, cliente) atualizam o input
      local na hora mas fazem `router.replace` apenas apos 350ms de
      inatividade (debounce implementado via `setTimeout` dentro do
      componente — nao usa o debounce do hook porque ali cada request
      teria resultado discartado pelo race protection)
    * Mudanca de qualquer filtro reseta `page` para 1 (exceto quando e
      mudanca direta de paginacao)
    * Back/forward do browser respeitam o historico de filtros (URL-first)
- **Header**: titulo + badge "N provas".
- **Filtros** (grid 4 colunas colapsando para 2/1 em <1200/<900px):
    * Busca (nome/requerimento)
    * Cliente
    * Status (select com todos os 10 statuses + "Todos")
    * Rota (select com PADRAO, DIRETA, "Todas")
    * Vendedor (select, **escondido para non-admin** — carrega `GET /users?setor=VENDEDOR&ativo=true`)
    * Periodo inicio/fim (input type="date")
    * Botao "Limpar filtros" (desabilitado se nao ha filtros)
- **Tabela**: Requerimento (mono), Nome, Cliente, Vendedor, Status (badge
  colorido por categoria), Rota (label ou "—"), Criada em (format pt-BR),
  Acoes ("Ver detalhes" **disabled** com tooltip "Disponivel no Componente 08").
- **Estado vazio contextual**:
    * Com filtros: "Nenhuma prova encontrada com esses filtros."
    * Sem filtros: "Nenhuma prova cadastrada ainda."
- **Estado de erro**: mensagem + botao "Tentar novamente" que re-invoca
  `load(urlFilters)`.
- **Estado de loading**: mensagem "Carregando..." dentro da tabela.
- **Paginacao** rodape: "Pagina X de Y · Z resultados" + 4 botoes
  (primeira, anterior, proxima, ultima) com disabled state correto.
- **Mobile**: mensagem "acesse a versao desktop".

**Frontend — CSS (`provas.module.css`, 335 linhas):**
- Mesma paleta dos outros componentes (tokens do `globals.css`).
- Tabela com borda externa + bordas verticais internas, scroll horizontal
  em mobile pelo wrapper `.tableScroll`.
- **Badges de status com cores semanticas**:
    * CRIADA → amarelo claro (var(--color-accent) 25%)
    * Em andamento vendedor → azul (#d4ecff / #003766)
    * Em transporte → amarelo escuro (#fff3c4 / #664000)
    * Concluida → verde (#c9f0d1 / #0a4a19)
    * Reprovada/Cancelada → vermelho (var(--color-danger) 20%)
- Pagina responsive: filter grid colapsa 4→3→2 em breakpoints 1200/900.

**Frontend — Ativacao do menu:**
- `layout.tsx`: `MAIN_NAV[1]` (Provas) ganha `href: "/provas"`. 1 linha.

### Verificacao

- **Backend**: `../.venv/Scripts/python -m pytest --cov=app -q` →
  **229 passed, 1 warning, 92% cobertura global**. `provas.py` 90% (de 87%).
  Zero regressao.
- **Frontend**: `npx tsc --noEmit` limpo (com 1 warning autoprefixer
  `align-items: end` corrigido para `flex-end`). `npm run build` limpo
  apos `rm -rf .next` (cache bug conhecido do Next). Bundles:
  `/provas` **4.55 kB** (154 kB first load), outras paginas inalteradas.
- **Reproduce contra banco real**: 5 provas seed inseridas, 4 cenarios
  de filtro validados via MCP, scoping por vendedor confirmado.
- **Advisor Supabase**: inalterado (1 INFO + 1 WARN WONTFIX).
- **Banco**: `alembic_version = 009`. 7 provas ativas (5 seed + 1 debug
  CANCELADA + 1 de teste do smoke Componente 06 "Prova de teste" 123456
  CRIADA).

### Pegadinhas resolvidas

- **`useSearchParams` exige Suspense boundary no Next 14 App Router** —
  sem `<Suspense>`, o build quebra na fase de static generation com
  "useSearchParams should be wrapped in a suspense boundary". Fix:
  dividir o componente em `ProvasPageInner` e exportar um wrapper com
  `<Suspense fallback={...}>`.
- **Race condition em requests paralelos** — se o usuario digitar rapido
  na busca, multiplos `load()` disparam em sequencia. Sem protecao, a
  ordem de retorno pode ser diferente da ordem de disparo (request N+1
  pode chegar antes de request N), exibindo dados obsoletos.
  Fix: `latestReqRef` incrementa a cada chamada; quando a resposta chega,
  compara com o valor corrente — se diferente, a resposta e descartada.
- **Debounce duplicado**: o hook tem `loadDebounced` mas a pagina precisa
  do proprio debounce (e nao do hook) porque o que precisa ser debounced
  e a ATUALIZACAO DA URL, nao apenas o request. `router.replace` a cada
  tecla polui o historico do browser. Solucao: a pagina usa `setTimeout`
  local + `updateUrl` de 350ms, o hook apenas faz `load` puro a partir
  dos search params.
- **`align-items: end` quebrou build** — autoprefixer warning virou erro
  no Next 14 strict mode. Trocado para `align-items: flex-end` (sintaxe
  pre-flexbox que todos os navegadores entendem). Detectado no primeiro
  build, corrigido antes do merge.
- **Cache corrompido do Next apos adicionar pagina nova** — sintoma:
  `PageNotFoundError: Cannot find module for page: /_document`. Fix
  conhecido: `rm -rf .next && npm run build`. Documentado desde a
  Sessao 4 do Wave 1.

### Arquivos criados/editados

```
A  backend/tests/test_provas_api.py          (+23 testes, 38 total)
A  scripts/seed_list_test_provas.py          (a ser removido apos --cleanup)
A  frontend/src/hooks/useListProvas.ts
A  frontend/src/app/(dashboard)/provas/page.tsx
A  frontend/src/app/(dashboard)/provas/provas.module.css

M  backend/app/domain/schemas/prova.py       (+ProvaListItem, +ProvaListResponse)
M  backend/app/api/v1/provas.py              (+GET / com scoping + filtros)
M  frontend/src/lib/types/prova.ts           (+tipos + labels + options)
M  frontend/src/app/(dashboard)/layout.tsx   (1 linha — href /provas)
```

Zero mudanca em: migrations, RLS, models, services, outros routers, outros
tests, Componentes 06 e 09.

### Documentos atualizados
- `CHANGELOG.md` — esta secao.
- `DECISIONS.md` — ADRs 037 (offset pagination), 038 (ILIKE search), 046
  (scoping por setor no backend), 047 (filtro rota direta), 048 (periodo
  inclusivo).
- `CLAUDE.md` — listagem de schemas + router novo + frontend pages.

### Definition of Done
- [x] Lint + typecheck + build verdes (backend e frontend)
- [x] Cobertura global >= 88% (subiu para 92%)
- [x] 18+ testes novos (23 entregues)
- [x] Reproduce contra banco real validada (seed + 4 cenarios de filtro + scoping)
- [x] CHANGELOG + DECISIONS + CLAUDE.md atualizados
- [x] Advisor Supabase sem novos WARN
- [x] Zero mudanca em Wave 1 / Componentes 06 / 09

### Proximo passo
Smoke manual pendente: Mario abre `/provas` no browser, valida que as
5 provas LIST-TEST aparecem, testa filtros (status, cliente, rota,
periodo, busca), valida paginacao (com page_size baixo: `?page_size=2`
para paginar), confirma que o botao "Ver detalhes" aparece disabled.
Apos OK, rodar `python scripts/seed_list_test_provas.py --cleanup` para
marcar as seed como CANCELADA. Depois autorizacao para comecar o
**Componente 08 — Visualizacao de Prova (Detalhe)** + timeline stub.

---

## [2026-04-09 — Sessao 9] — Wave 2: Componente 09 (Tela de Configuracoes do Sistema)

### Contexto
Segundo componente funcional da Wave 2. Entrega os endpoints + UI de edicao
dos parametros do sistema (RF-021): tempo de atraso (RN-008) e template da
etiqueta (RN-011). Acesso exclusivo do perfil 3Studio via `get_admin_user`
(RF-019) e RLS admin-only ja existente em `configuracoes_sistema`.
3 ADRs novos (043, 044, 045). Zero mudanca na Wave 1 ou no Componente 06.

### Entregas

**Backend — Schemas Pydantic (`app/domain/schemas/configuracao.py`):**
- `EDITABLE_KEYS` — whitelist frozenset com `tempo_atraso_horas_uteis`
  e `template_etiqueta` (ADR-043). Chaves fora disso sao 404 via API.
- `validar_tempo_atraso(valor)` — valida tipo int (rejeita bool explicitamente
  porque bool e subclass de int em Python) e range 1-168 horas. Raise
  `ConfiguracaoValidationError`.
- `validar_template_etiqueta(valor)` — valida objeto com 4 campos obrigatorios
  (`nome: str`, `formato: "A4"|"80mm_thermal"`, `logo_enabled: bool`,
  `mostrar_data_criacao: bool`). Campos extras no body sao descartados.
  Rejeita tipo errado com mensagem especifica por campo.
- `VALIDATORS: dict[str, Callable]` — dispatch table para escalar quando
  tiverem 3+ chaves (ADR-045). Na Wave 2, so as 2 chaves editaveis.
- `validar_valor_por_chave(chave, valor)` — dispatcher.
- `ConfiguracaoResponse`, `ConfiguracaoListResponse`,
  `ConfiguracaoUpdateRequest` — tipos de I/O.

**Backend — Router (`app/api/v1/configuracoes.py`, 3 endpoints):**
- `GET /api/v1/configuracoes/` — admin-only. Retorna lista filtrada por
  `EDITABLE_KEYS` (chaves nao-whitelisted nunca vazam no response, mesmo
  que existam no banco).
- `GET /api/v1/configuracoes/{chave}` — admin-only. 404 quando chave
  nao e whitelisted OU quando e whitelisted mas nao foi seedada (edge case,
  log de erro para investigacao operacional).
- `PATCH /api/v1/configuracoes/{chave}` — admin-only. Fluxo:
  1. Valida chave ∈ EDITABLE_KEYS (404 senao)
  2. `SELECT ... FOR UPDATE` da linha (trava race com outro admin)
  3. Valida `body.valor` via dispatch table → 422 com detalhe especifico
  4. Captura `valor_anterior` e `descricao_anterior` antes de mutar
  5. Aplica mudanca em memoria + `updated_by = admin.id`
  6. `flush` → `log_audit(acao="atualizar_configuracao", detalhes={chave,
     valor_anterior, valor_novo, descricao_anterior, descricao_nova})` → `commit`
  7. Em caso de falha pos-validacao, rollback completo + 500
- `app/main.py` — include_router adicionado. Total de rotas: 18 (13 Wave 1 +
  2 Componente 06 + 3 Componente 09).

**Backend — Testes mock-only (`tests/test_configuracoes_api.py`, 26 novos):**
- GET list happy path + non-admin 403 + sem auth 401
- GET by chave happy (tempo + template) + nao-whitelisted 404 (sem chegar
  ao DB) + whitelisted mas ausente 404 + non-admin 403
- PATCH tempo_atraso: happy (48 → 72) + rejeita 0 + rejeita negativo +
  rejeita > 168 + rejeita string + rejeita bool (edge case subclass int)
- PATCH template: happy (muda 3 campos) + rejeita formato invalido +
  rejeita campo faltando + rejeita tipo errado + rejeita nao-objeto +
  descarta campos extras
- PATCH edge cases: chave nao-whitelisted 404 + non-admin 403 + sem auth
  401 + commit failure rollback 500 + atualiza descricao + sem descricao
  mantem a atual
- **Cobertura**: `configuracoes.py` 96%, `schemas/configuracao.py` 95%.
  Global mantem 91%.

**Validacao contra banco real (Fase 4):**
Seguindo a licao aprendida na Sessao 8c (mocks nao pegam bugs de ordem
SQL), criei `scripts/reproduce_configuracoes.py` (temporario, removido apos
validacao) que invoca os 3 handlers diretamente contra producao:
  1. GET list → retorna `template_etiqueta` + `tempo_atraso_horas_uteis`
  2. GET `/tempo_atraso_horas_uteis` → valor 48 ok
  3. PATCH `/tempo_atraso_horas_uteis` valor=72 → persiste no banco, `updated_by`
     setado para admin
  4. PATCH `/template_etiqueta` com `mostrar_data_criacao: true` → persiste
  5. Verifica que audit_logs tem 2 novas linhas com `detalhes_json`
     contendo `chave`, `valor_anterior`, `valor_novo`, `descricao_anterior`,
     `descricao_nova` (ADR-044)
  6. Reverte ambas as configs para os valores originais
  Total de 4 linhas em `audit_logs` foram gravadas durante a reproducao
  (2 mudancas + 2 reversoes) — ficam permanentemente no banco por
  imutabilidade (RNF-005). Estado das configuracoes esta 100% identico
  ao baseline pos-reproducao.

**Frontend — Tipos (`lib/types/configuracao.ts`):**
- Constantes `CHAVE_TEMPO_ATRASO`, `CHAVE_TEMPLATE_ETIQUETA` (sincronizado
  com backend), limites `TEMPO_ATRASO_MIN_HORAS = 1`, `TEMPO_ATRASO_MAX_HORAS = 168`,
  `FORMATOS_ETIQUETA = ["A4", "80mm_thermal"]`, `FORMATO_LABELS` com strings
  pt-BR.
- Interfaces `TemplateEtiquetaValor`, `ConfiguracaoResponse`,
  `ConfiguracaoListResponse`.
- Type guards `isTemplateEtiquetaValor`, `isTempoAtrasoValor` para narrow
  no uso.

**Frontend — Hook (`hooks/useConfiguracoes.ts`):**
- Carrega `/api/v1/configuracoes/` on-mount e indexa por chave (O(1) por
  seccao).
- `updateConfiguracao(chave, valor, descricao?)` → PATCH e atualiza cache
  local no sucesso. Retorna `{ok, error}` para a seccao tratar feedback
  inline.
- `reload()` exposto para refresh manual.

**Frontend — Pagina (`(dashboard)/configuracoes/page.tsx`):**
- Duas seccoes independentes: "Tempo de atraso" e "Template da etiqueta".
  Cada uma tem seu proprio form, botao Salvar, estado de loading e
  feedback inline de sucesso/erro. Mudar uma nao obriga salvar a outra.
- **Tempo de atraso**: input number com min=1, max=168, step=1 + sufixo
  visual. Valida client-side antes de enviar.
- **Template da etiqueta**:
  - Campo `nome` **read-only** (Q09.3 — edicao futura via SQL quando
    houver multiplos templates)
  - Select `formato` com as 2 opcoes (A4, 80mm_thermal) + labels pt-BR
  - Checkbox `logo_enabled` e `mostrar_data_criacao` usando accent-color
    = --color-accent
- Loading state inicial ("Carregando configuracoes..."), erro geral
  (falha ao carregar), erros por seccao (validacao ou falha do PATCH).
- Mobile: aviso "acesse a versao desktop" (padrao das outras paginas).
- CSS: reutiliza tokens do `globals.css`, 2 cards empilhados em
  superficie clara, grid 2-col colapsando para 1-col em <=900px.

**Frontend — Ativacao do menu:**
- `layout.tsx`: `SECONDARY_NAV[0]` (Configuracoes) ganha `href: "/configuracoes"`.
  1 linha alterada. `NavEntry` detecta e renderiza `<Link>` automaticamente.

### Verificacao

- **Backend**: `../.venv/Scripts/python -m pytest --cov=app -q` →
  **208 passed, 1 warning, 91% cobertura global**. Zero regressao.
- **Frontend**: `npx tsc --noEmit` limpo, `npm run build` limpo. Bundles:
  `/configuracoes` 3.2 kB, `/nova-prova` 4.13 kB, `/usuarios` 4.9 kB,
  `/login` 1.81 kB. Middleware 80.1 kB.
- **Reproduce contra banco real**: 6/6 steps OK + reversao limpa.
- **Advisor Supabase**: inalterado (1 INFO ADR-025 + 1 WARN ADR-027
  WONTFIX). Zero novos WARN.
- **Banco**: `alembic_version = 009`. `configuracoes_sistema` com valores
  originais (48h + template A4 padrao). `audit_logs` com 4 linhas
  historicas da reproducao.

### Pegadinhas resolvidas

- **`bool` e subclass de `int` em Python**: `isinstance(True, int)` retorna
  `True`. Sem check explicito em `validar_tempo_atraso`, `{"valor": true}`
  passaria na validacao como se fosse um numero. Fix: checar `isinstance(
  valor, bool)` ANTES do check de `int` e rejeitar. Teste dedicado:
  `test_patch_tempo_atraso_rejects_bool`.
- **Whitelist bloqueia antes do DB**: `test_get_configuracao_nao_whitelisted`
  e `test_patch_chave_nao_whitelisted` confirmam que a chave inexistente e
  rejeitada pelo check `chave not in EDITABLE_KEYS` ANTES de qualquer query
  ao banco (via `mock_db.execute.assert_not_called()`).
- **Campos extras no template sao descartados, nao rejeitados**: o contrato
  e "o backend so persiste os 4 campos conhecidos". Teste
  `test_patch_template_descarta_campos_extras` confirma que
  `campo_desconhecido: "foo"` no body nao causa erro nem e persistido.
- **Descricao opcional**: quando `body.descricao` e None, o PATCH mantem
  a `descricao` atual (nao limpa para NULL). Tests
  `test_patch_atualiza_descricao` e `test_patch_sem_descricao_mantem_atual`.

### Arquivos criados/editados

```
A  backend/app/domain/schemas/configuracao.py
A  backend/app/api/v1/configuracoes.py
A  backend/tests/test_configuracoes_api.py
A  frontend/src/lib/types/configuracao.ts
A  frontend/src/hooks/useConfiguracoes.ts
A  frontend/src/app/(dashboard)/configuracoes/page.tsx
A  frontend/src/app/(dashboard)/configuracoes/configuracoes.module.css
M  backend/app/main.py                           (+include_router +1 import)
M  frontend/src/app/(dashboard)/layout.tsx       (1 linha — href configuracoes)
```

Zero mudanca em: migrations, RLS, models, audit_service, state_machine,
outros routers, outros tests.

### Documentos atualizados
- `CHANGELOG.md` — esta secao.
- `DECISIONS.md` — ADRs 043 (whitelist), 044 (audit trail detalhado),
  045 (dispatch table de validators).
- `CLAUDE.md` — listagem de schemas + routers + frontend pages.

### Definition of Done
- [x] Lint + typecheck + build verdes (backend e frontend)
- [x] Cobertura global >= 88% (manteve 91%)
- [x] 15+ testes novos cobrindo happy + erros + RLS + commit failure
- [x] Reproduce contra banco real (fluxo completo + reversao)
- [x] CHANGELOG + DECISIONS + CLAUDE.md atualizados
- [x] Advisor Supabase sem novos WARN
- [x] Zero mudanca em Wave 1 / Componente 06

### Proximo passo
Aguardando Mario validar smoke manual de `/configuracoes` no browser
(alterar tempo de atraso e template, verificar persistencia) + OK para
comecar o **Componente 07 — Listagem, Pesquisa e Filtros de Provas**
(RF-012, RF-013).

---

## [2026-04-09 — Sessao 8c] — Wave 2: Bugfix critico em POST /api/v1/provas/ (ordem de flush SQLAlchemy)

### Contexto
Mario subiu o backend via uvicorn apos a correcao de ambiente da 8b, abriu
`/nova-prova` no browser, preencheu o form e tentou criar uma prova de teste.
Recebeu erro 500 do endpoint `POST /api/v1/provas/`. Reportou o sintoma
sem traceback — precisei reproduzir localmente via script one-shot para
capturar o stack completo.

### Reproducao

- **`scripts/reproduce_create_prova.py`** (temporario, removido apos fix) —
  script que carrega `.env`, seleciona o primeiro vendedor ativo (Mario
  Souza, FILIAL), faz upload de um JPG minimo (20 bytes, so cabecalho JFIF)
  direto no R2 via boto3, monta um `Request` mock e invoca `create_prova`
  sem passar por HTTP. Qualquer excecao e impressa via `traceback.print_exc()`
  sem middleware escondendo.
- **Execucao 1 (codigo pre-fix)**: falhou com
  ```
  asyncpg.exceptions.ForeignKeyViolationError:
  insert or update on table "etiquetas" violates foreign key constraint
  "etiquetas_prova_id_fkey"
  DETAIL: Key (prova_id)=(...) is not present in table "provas_digitais".
  ```

### Causa raiz

No endpoint original, o fluxo fazia:

```python
db.add(nova_prova)
db.add(nova_etiqueta)
await db.flush()       # flush coletivo
await log_audit(...)   # outro add + flush
await db.commit()
```

Sem `relationship()` declarado entre `ProvaDigital` e `Etiqueta`, o
SQLAlchemy **nao detecta** a dependencia FK automaticamente. A ordem de
`db.add()` NAO garante a ordem de INSERT no flush coletivo — a unit of
work do SQLAlchemy 2.0 organiza INSERTs por heuristicas internas quando
nao ha relationship declarada, e neste caso decidiu emitir
`INSERT INTO etiquetas` ANTES de `INSERT INTO provas_digitais`. O log real
do SQLAlchemy confirmou: so um INSERT (etiquetas) foi emitido antes do
ROLLBACK automatico.

Os testes unitarios (`tests/test_provas_api.py`) nao pegaram porque
mockam `db.flush` e `db.add` — a ordem real de INSERT no banco nao e
exercitada pelos mocks. Esse e exatamente o tipo de bug que so um teste
de integracao com Postgres real pegaria — e a Q6 do plano global da
Wave 2 (vetada por Mario, opcao consciente) teria trazido
`pytest-postgresql` para cobrir esses cenarios. Fica como ponto de
atencao para revisao em Wave 6.

### Fix aplicado

**`backend/app/api/v1/provas.py`** — `create_prova` passa a fazer **dois
flushes explicitos** dentro da mesma transacao:

```python
try:
    db.add(nova_prova)
    await db.flush()    # garante INSERT de provas_digitais PRIMEIRO

    db.add(nova_etiqueta)
    await db.flush()    # depois insere etiquetas (FK ja existe)

    await log_audit(...)  # audit_log usa o prova_id ja commitado
    await db.commit()
except Exception:
    await db.rollback()
    ...
```

A transacao inteira continua atomica (rollback cobre tudo em caso de
falha). A mudanca e cirurgica: nao mexe nos models, nao adiciona
relationships, nao cria migrations. Comentario extenso adicionado ao
codigo explicando o motivo do fix para quem vier depois.

**Alternativa considerada e rejeitada:** declarar
`relationship("Etiqueta", back_populates="prova")` em `ProvaDigital` e o
reverso em `Etiqueta`. Funcionaria mas:
  - Toca nos models da Wave 2 (mais superficie de mudanca)
  - Risco de introduzir lazy-loading implicito em queries futuras
  - Performance difference zero comparado aos dois flushes explicitos
  - Escolhido: fix cirurgico + comentario explicativo

### Validacao pos-fix

- **`scripts/reproduce_create_prova.py` re-executado**: **sucesso**.
  Log do SQLAlchemy agora emite, na ordem correta:
  1. `INSERT INTO provas_digitais ... RETURNING created_at, updated_at`
  2. `INSERT INTO etiquetas ... RETURNING id, created_at`
  3. `INSERT INTO audit_logs ... RETURNING id, created_at`
  4. `COMMIT`

  Prova criada com sucesso: `id=ff56dccf-3b30-4cb8-a425-bcf425ad6ce9`,
  `rota_projetada=DIRETA` (Mario Souza e vendedor FILIAL), PDF da etiqueta
  gerado (3300 chars base64).

- **`../.venv/Scripts/python -m pytest -q` do `.venv`**: **182 passed,
  1 warning**. Zero regressao. Os mocks aceitam multiplos awaits de
  `db.flush` sem alterar os asserts existentes (`assert_awaited()`
  cobre >= 1 chamada).

### Registro de debug em producao

Como `audit_logs` e `etiquetas` tem triggers de imutabilidade
(`trg_audit_logs_imutavel`, `trg_etiquetas_imutavel`), **nao e possivel
apagar** a prova de debug criada durante a reproducao. Opcao adotada:
marcar a prova como `CANCELADA` com motivo explicito via UPDATE em
`provas_digitais` (essa tabela NAO tem trigger de imutabilidade).

```sql
UPDATE public.provas_digitais
SET status = 'CANCELADA',
    motivo_cancelamento = 'Registro de debug da Sessao 8c — reproducao
    do bug de ordem de flush. Mantido por imutabilidade de etiquetas/
    audit_logs. Ver CHANGELOG.'
WHERE nro_requerimento = 'DEBUG-5002C5CD';
```

Aplicado via Supabase MCP. A prova (`id=ff56dccf-3b30-4cb8-a425-bcf425ad6ce9`)
fica no banco como registro historico de validacao, CANCELADA, e nao
polui contadores futuros (dashboards da Wave 4 vao filtrar por status
ativo por default).

Existe tambem um objeto R2 correspondente em
`provas/2026/04/debug-5f094260aa0240d79738254c776d81e3/teste.jpg` (20
bytes, cabecalho JFIF minimo). Mario pode remove-lo manualmente pelo
dashboard Cloudflare se quiser — o sistema nao depende dele.

### Licao aprendida

**Mocks de SQLAlchemy nao testam ordem de INSERTs**. Qualquer fluxo com
multiplos INSERTs encadeados por FK precisa ser validado em integracao
real (ou via script de reproducao como o dessa sessao). Para o Componente
09 em diante, quando houver CRUD com cross-table INSERTs, vou:
  1. Rodar um smoke de reproducao contra banco real antes de declarar Done
  2. Documentar no CHANGELOG o comando exato usado

### Arquivos alterados

```
M  backend/app/api/v1/provas.py   (dois flushes explicitos + comentario
                                    extenso explicando o bug)
M  CHANGELOG.md                    (esta secao)
```

Zero mudanca em models, migrations, schema, RLS, testes. A Definition
of Done da Sessao 8 continua valida apos este fix.

### Estado producao pos-sessao
- `provas_digitais`: 1 linha (DEBUG-5002C5CD, CANCELADA)
- `etiquetas`: 1 linha (snapshot imutavel da prova de debug)
- `audit_logs`: 1 linha (acao=`criar_prova`, detalhes completos)
- `movimentacoes`: 0 linhas
- `configuracoes_sistema`: 2 linhas (tempo_atraso + template_etiqueta evoluido)
- `usuarios`: 3 linhas (2 admins ativos + Mario Souza vendedor)
- `alembic_version`: 009

Advisor Supabase: inalterado (1 INFO ADR-025 + 1 WARN ADR-027 WONTFIX,
zero novos WARN).

### Proximo passo
Mario vai reabrir `/nova-prova` no browser e validar que o fluxo agora
funciona end-to-end. Apos OK, comecamos o **Componente 09 — Tela de
Configuracoes do Sistema** (RF-021).

---

## [2026-04-09 — Sessao 8b] — Wave 2: Correcao de ambiente (.venv deps + pytest-asyncio 1.x)

### Contexto
Apos a entrega da Sessao 8 (Componente 06), Mario tentou rodar o backend
via `uvicorn` e bateu em `ModuleNotFoundError: No module named 'qrcode'`.
Investigacao revelou DOIS problemas de ambiente:

1. **`qrcode` e `fpdf2` instalados no Python global, nao no `.venv`** — na
   Sessao 8 eu rodei `pip install 'qrcode[pil]' fpdf2` sem prefixar com
   `.venv/Scripts/pip`, entao as deps foram parar no
   `C:\Users\mario.souza\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\`.
   Meus smoke checks e testes passaram porque o pytest global tambem tinha
   as deps. Mas `uvicorn` roda do `.venv` (`C:\Users\mario.souza\provaDigital\.venv\Scripts\uvicorn`),
   que nao viu as deps novas.
2. **`pytest-asyncio 0.26.0` do `.venv` e incompativel com Python 3.14** —
   quando Mario rodou `pytest` do `.venv`, o output foi `182 passed, 1037
   warnings` (vs 1 warning do Python global). Os 1037 warnings vieram
   100% do `pytest_asyncio/plugin.py` usando APIs `asyncio.get_event_loop_policy()`
   e `asyncio.set_event_loop_policy()` que foram deprecadas no Python 3.14
   e marcadas para remocao no 3.16. O Python global tem
   `pytest-asyncio 1.3.0` (que ja mitigou essas chamadas), mas o `.venv`
   estava preso em `0.26.0` por causa da constraint `<1.0` no `pyproject.toml`.

### Correcoes aplicadas

**Deps Wave 2 instaladas no `.venv` (correto):**
- `.venv/Scripts/pip install 'qrcode[pil]>=7.4,<8.0' 'fpdf2>=2.7,<3.0'`
- Instalou `qrcode 7.4.2`, `fpdf2 2.8.7`, `Pillow 12.2.0`, `fonttools 4.62.1`,
  `pypng 0.20220715.0`, `defusedxml 0.7.1`. Todas compativeis com Python 3.14.
- Verificado: `cd backend && ../.venv/Scripts/python -c "from app.main import app; print(len(app.routes))"` retornou 15 (as 13 de Wave 1 + 2 de Wave 2).
- `uvicorn` do `.venv` agora sobe sem erro.

**`backend/pyproject.toml` — constraint de `pytest-asyncio` relaxada:**
- Antes: `pytest-asyncio>=0.23,<1.0`
- Depois: `pytest-asyncio>=1.0,<2.0`
- Comentario explicativo adicionado no arquivo apontando para esta sessao.
- `.venv/Scripts/pip install 'pytest-asyncio>=1.0,<2.0' --upgrade` → pulou
  de `0.26.0` para `1.3.0`. Zero breaking changes no nosso codigo (os 182
  testes continuam passando).

### Validacao pos-correcao

- **`../.venv/Scripts/python -m pytest -q` do `.venv`**: **182 passed, 1 warning**.
  O warning unico remanescente e o intencional do JWT test com chave curta.
- **Cobertura**: **91% global** (identica a Sessao 8). Modulos Wave 2 preservados:
  `state_machine.py` 97%, `qrcode_service.py` 97%, `etiqueta_service.py` 98%,
  `audit_service.py` 100%, `provas.py` 87%.
- **Backend import limpo via venv**: confirmado com `from app.main import app`
  rodando do `.venv` Python.

### Licao aprendida (para Componente 09 em diante)

Sempre prefixar comandos de pip e pytest com `.venv/Scripts/` (Windows) ou
`.venv/bin/` (Unix) quando o projeto tem `.venv` no root. O fato do Python
global ter todas as deps mascarou o problema ate o Mario tentar subir o
servidor real. Regra operacional: **qualquer pip/pytest fora do venv do
projeto e bug em potencial**, mesmo que o teste passe.

### Arquivos alterados

```
M  backend/pyproject.toml   (pytest-asyncio constraint: <1.0 -> <2.0)
M  CHANGELOG.md             (esta secao)
```

Nenhum arquivo de codigo de dominio alterado. Testes, migrations e schema
iguais a Sessao 8.

---

## [2026-04-09 — Sessao 8] — Wave 2: Componente 06 (Cadastro de Prova Digital + Etiqueta)

### Contexto
Primeiro componente funcional da Wave 2. Entrega o objeto central do sistema
(a Prova Digital) com upload direto frontend->R2 via presigned URL, geracao
de QR Code via HMAC-SHA256, geracao automatica de etiqueta em PDF e audit
log estruturado. Zero mudanca nos contratos da Wave 1. 10 ADRs novos
(031-036, 039-042) formalizados nesta sessao. Todos aprovados pelo Mario
no plano detalhado pre-execucao.

### Entregas

**Backend — Migration Alembic:**
- `backend/migrations/versions/009_evolve_template_etiqueta_schema.py` — evolui
  `configuracoes_sistema.template_etiqueta` de string JSONB (`"padrao"`) para
  objeto estruturado `{"nome":"padrao","formato":"A4","logo_enabled":true,
  "mostrar_data_criacao":false}`. Aplicada em producao via `alembic upgrade head`.
  `alembic_version` passou de 008 -> 009. Idempotente (WHERE filtra pelo tipo
  JSONB legacy). Ver ADR-036.

**Backend — Dependencias:**
- `backend/pyproject.toml` — adicionadas `qrcode[pil]>=7.4,<8.0` (ADR-034) e
  `fpdf2>=2.7,<3.0` (ADR-035). Instaladas: qrcode 7.4.2, fpdf2 2.8.7,
  Pillow 12.2.0, fonttools 4.62.1, pypng 0.20220715.0, defusedxml 0.7.1.
  Todas compativeis com Python 3.14.

**Backend — Nova env var:**
- `backend/.env` + `.env.example` + `app/core/config.py` — `QR_CODE_HMAC_SECRET`
  (64 chars hex = 32 bytes de entropia). Valor real gerado via
  `secrets.token_hex(32)` e nao commitado. Ver ADR-033.

**Backend — Models SQLAlchemy (todos adicionados em `app/db/models.py`):**
- `StatusProvaEnum` (10 valores — Secao 5 dos Requisitos)
- `RotaEnum` (PADRAO, DIRETA)
- `ProvaDigital` (13 colunas — espelha o schema real)
- `Movimentacao` (9 colunas — Wave 2 nao escreve, mas estrutura criada para
  Componente 08 ler o historico e Wave 3 comecar a escrever)
- `Etiqueta` (7 colunas — snapshot dos dados impressos + QR image BYTEA)
- `AuditLog` (8 colunas — alvo do audit_service novo)
- `ConfiguracaoSistema` (6 colunas — acessada pelo endpoint de criacao
  para ler o template_etiqueta)

**Backend — Schemas Pydantic v2 (`app/domain/schemas/prova.py`):**
- `UploadUrlRequest`, `UploadUrlResponse` — step 1 do fluxo
- `ProvaCreateRequest`, `ProvaResponse`, `ProvaCreateResponse` — step 2
- Validacao de MIME (apenas `image/jpeg` e `image/png`)
- Validacao de `nro_requerimento` (charset basico, max 50 chars)
- Validacao de `object_key` (comeca com `provas/`, sem `..`)
- `sanitize_filename` utility (substitui caracteres nao-safe por `_`)

**Backend — Services (nova pasta `app/services/`):**
- `state_machine.py` (ADR-040) — tabela de transicoes completas da Secao 5
  dos Requisitos, `determinar_rota(vendedor)` funcional, `validar_transicao`
  com excecoes customizadas `TransicaoInvalidaError` e `AtorNaoAutorizadoError`,
  `pode_cancelar`, `atores_permitidos`, `executar_transicao` stub que levanta
  `NotImplementedError("Wave 3")`.
- `qrcode_service.py` (ADR-033, ADR-034) — `gerar_hash(prova_id, nro_req)`
  via HMAC-SHA256 (64 chars hex), `gerar_payload_qr` no formato
  `3SD|{nro_req}|{hash_first_16}`, `validar_payload_qr` com
  `hmac.compare_digest` constant-time, `gerar_imagem_qr` via `qrcode[pil]`
  (ERROR_CORRECT_M, 200x200 px default, nearest-neighbor resize para
  preservar bordas das celulas).
- `etiqueta_service.py` (ADR-035) — `gerar_pdf(...)` via fpdf2 com dois
  formatos suportados (`A4` e `80mm_thermal`), suporte a `logo_enabled`
  e `mostrar_data_criacao` via template JSONB, `TEMPLATE_PADRAO` como
  fallback quando a config nao esta carregada.
- `audit_service.py` (ADR-039) — `log_audit(db, acao, usuario_id, *,
  prova_id, detalhes, request)` que faz INSERT em `audit_logs` dentro
  da mesma transacao do caller (flush sem commit), extrai IP e User-Agent
  de `request.client.host` e `request.headers["user-agent"]` (truncado a
  2000 chars).
- `r2_signed.py` — `generate_presigned_upload_url` (ADR-031),
  `generate_presigned_get_url` (pronto para Componente 08), `head_object`,
  `get_object_head_bytes` (para magic bytes do ADR-032). Todos async via
  `run_in_executor` sobre boto3. Coexiste com `app/core/r2.py` sem conflito.

**Backend — Router FastAPI (`app/api/v1/provas.py`):**
- `POST /api/v1/provas/upload-url` (ADR-031) — retorna presigned URL PUT
  com TTL 15min. Valida unicidade do nro_requerimento ANTES de assinar
  (evita upload de arquivo que jamais vai virar prova). Gera `object_key`
  particionado por ano/mes: `provas/{yyyy}/{mm}/{uuid_hex}/{sanitized_filename}`.
- `POST /api/v1/provas/` — fluxo completo:
  1. Re-valida unicidade do nro_requerimento (race window)
  2. SELECT FOR UPDATE do vendedor + validacoes (ativo, setor=VENDEDOR,
     localizacao NOT NULL)
  3. `HeadObject` no R2 -> existe + ContentLength <= 10MB (RF-001)
  4. Range GET 16 bytes -> magic bytes de JPG (`FF D8 FF`) ou PNG
     (`89 50 4E 47 0D 0A 1A 0A`) (ADR-032)
  5. Gera UUID da prova no backend (precisa do UUID ANTES para o HMAC)
  6. HMAC-SHA256 para `qr_code_hash` (ADR-033)
  7. Renderiza PNG 200x200 do QR Code (ADR-034)
  8. `determinar_rota(vendedor)` -> rota_projetada (Wave 2 NAO persiste em
     `provas_digitais.rota` — fica NULL; ADR-042)
  9. INSERT atomico: `provas_digitais` + `etiquetas` + `audit_logs` via
     flush + log_audit + commit (transacao unica)
  10. Carrega `template_etiqueta` de `configuracoes_sistema`
  11. Gera PDF da etiqueta via fpdf2 (ADR-035)
  12. Retorna 201 com `{prova, etiqueta_pdf_base64, qr_code_payload}`

  Cleanup best-effort (ADR-041): qualquer falha apos o upload ter acontecido
  no R2 (duplicata, vendedor invalido, MIME invalido, commit falhando)
  dispara `r2_delete(object_key)` para evitar orfao. Falha de cleanup loga
  "drift manual" via `logger.exception`.

- `app/main.py` — include_router adicionado.

**Backend — Testes (74 novos, total 182 passed):**
- `tests/test_state_machine.py` — 26 testes: determinar_rota (4 cenarios),
  transicao_e_valida (todos os paths validos + ilegais + estados terminais),
  pode_cancelar (estados ativos vs terminais), atores_permitidos (por
  transicao e por cancelamento), validar_transicao (happy, invalida,
  ator errado, admin bypass, cancelamento studio-only), executar_transicao
  stub, consistencia estrutural da tabela (toda transicao tem ator definido).
- `tests/test_qrcode_service.py` — 13 testes: hash tem 64 chars hex,
  determinismo, variacao por prova_id e nro_req, variacao por secret
  (monkeypatch), formato do payload, validacao aceita/rejeita, magic bytes
  do PNG, tamanho crescente com `size_px`.
- `tests/test_etiqueta_service.py` — 7 testes: magic header %PDF-, A4 nao
  vazio, A4 difere de 80mm_thermal, logo_enabled=false nao quebra,
  mostrar_data_criacao, template None usa padrao, nome com 200 chars.
- `tests/test_audit_service.py` — 4 testes: happy path com request,
  sem request (IP e UA None), client=None no request, user_agent
  truncado a 2000 chars.
- `tests/test_provas_api.py` — 15 testes: upload-url happy path, rejeita
  content_type invalido, rejeita duplicata, requires admin, sem auth;
  create_prova happy path matriz (rota_projetada=PADRAO), happy path
  filial (rota_projetada=DIRETA), duplicata limpa R2, vendedor nao
  encontrado limpa R2, vendedor nao-VENDEDOR, vendedor inativo, object
  nao existe no R2 (404), arquivo >10MB, magic bytes invalidos, commit
  failure com rollback + cleanup R2, requires admin, object_key fora
  de `provas/` (422).

- **Cobertura:** 91% global (sem regressao). Modulos do Componente 06:
  `state_machine.py` 97%, `qrcode_service.py` 97%, `etiqueta_service.py`
  98%, `audit_service.py` 100%, `models.py` 100%, `schemas/prova.py` 92%,
  `api/v1/provas.py` 87%. `r2_signed.py` fica em 50% porque os wrappers
  sao mockados nos testes — esperado e coerente com o padrao `r2.py`
  (40%) que ja era mockado desde Wave 1.

**Frontend — Tipos (novos):**
- `frontend/src/lib/types/prova.ts` — espelho TS dos schemas Pydantic.
  Inclui enums `StatusProva`, `Rota`, `Localizacao` e interfaces
  `UploadUrlResponse`, `ProvaCreateRequest`, `ProvaResponse`,
  `ProvaCreateResponse`. Constantes `ALLOWED_IMAGE_TYPES` e
  `MAX_UPLOAD_BYTES` (10 MB) ficam no client para pre-validar antes
  do upload.
- `frontend/src/lib/types/usuario.ts` — tipos `UsuarioResponse` e
  `UsuarioListResponse` para consumir `GET /api/v1/users/`.

**Frontend — Hook (novo):**
- `frontend/src/hooks/useCreateProva.ts` — encapsula o fluxo 3-step
  (upload-url -> PUT R2 -> POST /provas/). Estado: `{loading, error,
  result}`. Pre-valida MIME e tamanho antes de comecar. `getToken` e
  passado como callback (injeta sessao do Supabase). Em qualquer erro
  seta `error` com mensagem amigavel — nunca silencia.

**Frontend — Pagina (nova):**
- `frontend/src/app/(dashboard)/nova-prova/page.tsx` — formulario com:
  - Grid 2-col para campos: nome, nro_requerimento, cliente, vendedor
    (select carregado de `GET /users?setor=VENDEDOR&ativo=true`)
  - Dropzone para arquivo com drag-and-drop + click + preview local
    via `URL.createObjectURL` (preview sem ida ao R2)
  - Validacao client-side com feedback visual
  - Estado de loading que desabilita o submit
  - Tela de sucesso apos criar: bloco com detalhes da prova (nome,
    requerimento, cliente, vendedor + localizacao, rota projetada,
    status, ciclo) + preview do PDF em `<iframe>` + botoes "Baixar
    etiqueta (PDF)" e "Imprimir etiqueta" e "Nova prova"
  - Mobile: mensagem "acesse a versao desktop" (mesmo padrao de
    `/usuarios`) — o Componente 10 (scan via camera) e que sera a
    porta de entrada mobile

- `frontend/src/app/(dashboard)/nova-prova/nova-prova.module.css` —
  estilos reutilizando tokens de `globals.css`. Dropzone com dashed
  border, hover/active/filled states. Preview de arte 180x180 com
  `object-fit: cover`. Grid de sucesso 2 colunas colapsando para 1
  em <=1080px. iframe do PDF com min-height 540px para caber a
  etiqueta A4 visualmente.

**Frontend — Ativacao do menu:**
- `frontend/src/app/(dashboard)/layout.tsx` — **1 linha alterada**:
  `MAIN_NAV[2]` (Nova prova) agora tem `href: "/nova-prova"`. O
  `NavEntry` automaticamente detecta e renderiza `<Link>` em vez de
  `<span aria-disabled>`. Zero mudanca de CSS (ja previsto desde a
  Sessao 4 do Wave 1).

### Verificacao

- **Backend:** `python -m pytest --cov=app -q` -> **182 passed, 1
  warning, 91% global**. Todos os modulos Componente 06 acima de 80%.
- **Frontend:** `npx tsc --noEmit` limpo, `npm run build` limpo.
  Novo bundle: `/nova-prova` 4.13 kB (154 kB first load). `/usuarios`
  e `/login` sem mudanca.
- **Banco:** `alembic_version = 009`, migration 009 aplicada,
  `template_etiqueta` agora e objeto JSONB validado.
- **Supabase advisor:** inalterado — 1 INFO (alembic_version RLS no
  policy, ADR-025), 1 WARN (leaked password, ADR-027 WONTFIX). Zero
  `auth_rls_initplan` remanescente. Zero novos WARN.

### Pegadinhas encontradas e resolvidas
- **Python 3.14 e fpdf2**: sem incompatibilidade — `fpdf2 2.8.7`
  instalou limpo com `Pillow 12.2.0`. O `pdf.output()` retorna
  `bytearray` no 2.8.7 (convertido para `bytes` no service).
- **fpdf2 API novo**: `cell(..., new_x=, new_y=)` substituiu o
  deprecated `ln=`. Ajustado em toda a funcao `gerar_pdf`.
- **`qrcode.QRCode` com `ERROR_CORRECT_M`** importa de
  `qrcode.constants`. Usado sem deprecation.
- **Race window entre `/upload-url` e `/`**: re-validacao de
  `nro_requerimento` no step 2 e intencional — se outro admin
  cadastrar a mesma prova entre os dois cliques, o segundo recebe
  409 e o backend limpa o R2.
- **`detalhes_json` do audit**: object_key vai junto pra ter
  rastreamento de onde a arte foi parar no R2 (alguem consegue
  auditar "qual arte foi a prova X" sem depender do campo
  `imagem_url` da prova — redundancia proposital).

### Arquivos criados/editados

```
A  backend/migrations/versions/009_evolve_template_etiqueta_schema.py
A  backend/app/services/__init__.py
A  backend/app/services/state_machine.py
A  backend/app/services/qrcode_service.py
A  backend/app/services/etiqueta_service.py
A  backend/app/services/audit_service.py
A  backend/app/services/r2_signed.py
A  backend/app/domain/schemas/prova.py
A  backend/app/api/v1/provas.py
A  backend/tests/test_state_machine.py
A  backend/tests/test_qrcode_service.py
A  backend/tests/test_etiqueta_service.py
A  backend/tests/test_audit_service.py
A  backend/tests/test_provas_api.py
A  frontend/src/lib/types/prova.ts
A  frontend/src/lib/types/usuario.ts
A  frontend/src/hooks/useCreateProva.ts
A  frontend/src/app/(dashboard)/nova-prova/page.tsx
A  frontend/src/app/(dashboard)/nova-prova/nova-prova.module.css
M  backend/pyproject.toml                 (+2 deps)
M  backend/app/core/config.py             (+1 env var)
M  backend/.env.example                   (+QR_CODE_HMAC_SECRET)
M  backend/.env                           (+valor real, nao commitado)
M  backend/app/db/models.py               (+enums + 5 classes)
M  backend/app/main.py                    (+include_router)
M  backend/tests/conftest.py              (+QR_CODE_HMAC_SECRET test env,
                                            +2 fixtures vendedor_matriz/filial)
M  frontend/src/app/(dashboard)/layout.tsx (1 linha — href nova-prova)
```

### Documentos atualizados
- `CHANGELOG.md` — esta secao.
- `DECISIONS.md` — ADRs 031 (presigned URL), 032 (magic bytes), 033
  (HMAC QR hash), 034 (qrcode[pil]), 035 (fpdf2), 036 (template_etiqueta
  JSONB), 039 (audit service), 040 (state_machine), 041 (cleanup orfao
  R2), 042 (rota persistida na aprovacao).
- `CLAUDE.md` — listagem de migrations atualizada + servicos novos.
- `docs/db/schema.sql` — nota sobre migration 009 e evolucao do
  template_etiqueta.

### Definition of Done
- [x] Lint + typecheck + build verdes (backend e frontend)
- [x] Migration 009 aplicada e verificada via MCP
- [x] Testes unitarios dos services novos >=80%
- [x] Testes de integracao com happy path + 5 erros + 1 RLS
- [x] CHANGELOG + DECISIONS + CLAUDE.md atualizados
- [x] docs/db/schema.sql atualizado
- [x] Advisor Supabase sem novos WARN
- [ ] **Smoke manual** do frontend: login como admin@3studio.com.br,
  criar uma prova teste, verificar PDF preview. **Acao pendente do
  Mario** — automacao depende de subir backend + frontend simultaneamente
  em preview, e o foco desta sessao foi entrega.

### Proximo passo
Aguardando Mario validar o smoke manual e dar OK para comecar o
**Componente 09 — Tela de Configuracoes do Sistema** (RF-021).

---

## [2026-04-09 — Sessao 7] — Wave 2: Abertura (W2-T0 RLS initplan + ADR-030 2o admin)

### Contexto
Abertura formal da Wave 2. Mario aprovou o plano global da Wave 2 (ordem
06 -> 09 -> 07 -> 08), os 10 ADRs novos propostos (031-040, ainda nao lavrados),
a execucao imediata do W2-T0 (ADR-029 — reescrita RLS initplan) e a criacao do
segundo admin operacional (ADR-030). Q6 do plano foi recusada: testes seguem
mock-only no nivel da Wave 1 (sem `pytest-postgresql`).

Esta sessao e de pre-componentes: ZERO codigo de dominio Wave 2 entregue aqui.
Apenas tarefas de plataforma que destravam o Componente 06.

### Relatorio de leitura + inspecao MCP

Antes de executar, completei a leitura obrigatoria dos docs de negocio
(Requisitos v3.0, Backlog v3.0, DAT v2.0, UML v3.0 .drawio — este ultimo via
subagente que parseou o ZIP XML das paginas drawio) + inspecao completa do
Supabase via MCP + Cloudflare via MCP. Cruzamento `/docs/db/schema.sql` com o
banco real confirmou zero drift estrutural — tudo em dia apos a Sessao 5b.

Divergencias menores identificadas e **nao tocadas** (aguardando autorizacao):
- Bucket R2 em `ENAM` (escolha Wave 0, aceita).
- Cloudflare MCP nao expoe CORS/lifecycle — impossivel validar via API.
  Mario confirmara manualmente se `docs/cloudflare_r2_setup.md` foi aplicado.
- Inconsistencia documental: `Etiqueta.template_id` no diagrama de classes do
  UML existe, mas nao existe no ER nem no schema real. Interpretacao adotada
  (a confirmar formalmente em ADR-036 do Componente 06): template de etiqueta
  vive em `configuracoes_sistema` como chave `template_etiqueta`, e o seed
  atual (`"padrao"`) sera evoluido para JSONB estruturado no Componente 06.

### W2-T0 — RLS initplan optimization (ADR-029 executado)

- **`backend/migrations/rls/005_initplan_optimization.sql`** (novo) — reescreve
  as 11 policies RLS em `public.usuarios`, `public.provas_digitais`,
  `public.movimentacoes`, `public.etiquetas`, `public.audit_logs` e
  `public.configuracoes_sistema`, substituindo `auth.uid()` por
  `(SELECT auth.uid())` em todos os `USING` e `WITH CHECK`. Zero mudanca
  semantica — apenas reestruturacao que faz o planner promover a expressao
  a InitPlan (avaliado uma vez por query) em vez de SubPlan (avaliado por
  linha). Idempotente (DROP IF EXISTS antes de cada CREATE).
- **Aplicacao em producao** — via Supabase MCP `execute_sql`, bloco unico
  com todas as 11 operacoes DROP + CREATE. Sucesso sem erros. Confirmei via
  `pg_policies` que cada `qual` (ou `with_check` para os INSERT) contem o
  novo padrao `( SELECT auth.uid()`.
- **Validacao via advisor** — antes: 11 WARN `auth_rls_initplan`. Depois:
  **zero WARN `auth_rls_initplan`**. O advisor de performance agora reporta
  apenas 13 INFO `unused_index` (esperado: tabelas ainda vazias, indexes
  Wave 2/3 nao foram exercitados por queries reais). Advisor de seguranca
  inalterado (1 INFO `alembic_version` ADR-025, 1 WARN leaked password
  ADR-027 WONTFIX).
- **Observacao sobre EXPLAIN ANALYZE** — o plano original previa medir
  `EXPLAIN (ANALYZE, BUFFERS)` antes/depois em uma query representativa.
  Pulei porque as tabelas estao com 0-3 linhas e qualquer benchmark seria
  teatro; o advisor do Supabase e quem faz a validacao canonica da
  substituicao, e ele zerou os 11 WARN imediatamente apos a aplicacao. Se
  quisermos medir ganho real, sera no Componente 07 com carga de teste.

### ADR-030 — Criacao do segundo admin operacional (executado)

- **`scripts/create_second_admin.py`** (one-shot) — script Python que carrega
  `.env` do backend, chama `app.core.supabase_admin.create_auth_user` para
  criar a conta em `auth.users` via GoTrue Admin API (mesmo caminho do
  endpoint `POST /api/v1/users`), faz INSERT em `public.usuarios` com
  `setor=STUDIO`, `is_admin=true`, `localizacao=null`, `created_by=null`
  (conta de sistema), verifica que o resultado final tem >=2 admins ativos,
  e printa a credencial para salvamento manual. Inclui rollback de auth
  em caso de falha no INSERT (mesma saga do endpoint).
- **Execucao** — rodou com sucesso. Senha gerada via
  `secrets.token_urlsafe(16)` (128 bits de entropia). Conta criada:
  - email: `ops@3studio.com.br`
  - nome: `Operacao 3Studio`
  - setor: `STUDIO`
  - is_admin: `true`
  - id (public.usuarios): `0c20be3e-50f3-40b1-b07b-ebacccd66760`
  - auth_uid: `8e230fdf-2a9e-44f7-a0d6-2bfa0cdbcd96`
  - created_at: `2026-04-09 12:56:40+00`
- **Validacao final** — `SELECT COUNT(*) FROM public.usuarios WHERE
  is_admin=true AND ativo=true` retornou **2**. Agora:
  - Admin Master (`admin@3studio.com.br`) — admin original
  - Operacao 3Studio (`ops@3studio.com.br`) — novo admin operacional
  - Mario Souza (`mariosouza@teste.com.br`) — vendedor, nao-admin
- **Acao manual pendente para Mario:**
  1. Salvar a senha no gerenciador de senhas corporativo (1Password /
     Bitwarden / similar). A senha so aparece uma vez no output do script.
  2. Documentar quem tem acesso compartilhado a essa conta.
  3. Remover `scripts/create_second_admin.py` apos confirmar salvamento.

### Testes e estado do codigo

- **`python -m pytest -q --no-header`** apos RLS 005 + criacao do admin:
  **108 passed, 1 warning** (warning intencional do JWT test). Zero regressao
  em relacao ao baseline da Sessao 6. As migrations de RLS sao metadata-only
  e os testes mockam Supabase Auth, entao o resultado e esperado mas foi
  validado por precaucao.
- **Zero mudanca** em `backend/app/` — nenhuma linha de codigo Wave 1 tocada.
- **Arquivos novos:**
  - `backend/migrations/rls/005_initplan_optimization.sql`
  - `scripts/create_second_admin.py` (**a ser removido apos Mario salvar a senha**)

### Estado pos-sessao
- Banco producao: 3 linhas em `public.usuarios`, 2 admins ativos, 11 policies
  RLS otimizadas, `alembic_version = 008`, zero drift.
- Performance advisor: limpo de `auth_rls_initplan` (era 11 WARN, agora 0).
- Security advisor: inalterado (perfil de Sessao 6 preservado).
- SPOF organizacional (ADR-030): **resolvido**.
- Wave 1: ainda intacta — nenhum contrato, schema ou teste da Wave 1 foi alterado.

### Documentos atualizados
- `CHANGELOG.md` — esta secao.
- `DECISIONS.md` — marcador `**Status:** EXECUTADO em Sessao 7` nos ADR-029 e
  ADR-030, com resumo do resultado.
- `CLAUDE.md` — listagem de migrations RLS atualizada com `005_initplan_optimization.sql`.
- `docs/db/schema.sql` — **sem mudanca** (as RLS policies nao estao no snapshot;
  apenas a menção a `002_policies_por_perfil.sql` e `003_policies_wave1_usuarios.sql`
  permanece valida. A evolucao do `004_unify_rls_is_admin.sql` e `005_initplan_optimization.sql`
  sera refletida quando o snapshot for atualizado no Componente 06).

### Proximo passo
Aguardando OK do Mario para comecar o **Componente 06 — Cadastro de Prova
Digital + Etiqueta**, seguindo o plano detalhado em B.4 do relatorio de
abertura + os 10 ADRs novos propostos (031-040) que serao formalizados
durante a sessao do Componente 06.

---

## [2026-04-09 — Sessao 6] — Wave 1: Auditoria de validacao final (sign-off pre-Wave 2)

### Contexto
Mario pediu uma segunda passada de auditoria, agora puramente de validacao: confirmar
que tudo o que foi planejado nas Sessoes 5/5b realmente esta no codigo, no banco e nos
testes; que nao houve regressao silenciosa; e que a Wave 1 pode ser declarada pronta
para a Wave 2. **Escopo: zero mudancas de codigo, apenas verificacao + atualizacao
aditiva de CHANGELOG/DECISIONS/CLAUDE se algo estivesse defasado.** Se a auditoria
encontrasse novos problemas, eu pararia e reportaria antes de tocar em qualquer arquivo.

### Verificacoes executadas

**1. Backend — testes + cobertura**
- `python -m pytest --cov=app --cov-report=term-missing -q`: **108 passed, 1 warning,
  91% cobertura global**. Identico ao baseline da Sessao 5b — zero regressao.
- Cobertura por modulo critico: `app/api/v1/users.py` 93%, `app/core/supabase_admin.py`
  100%, `app/api/deps.py` 100%, `app/core/jwt.py` 88%, `app/domain/schemas/user.py` 100%.
- Warning unico: `JWT test com chave curta` (intencional, ja documentado).
- 0 deprecation warnings (`HTTP_422_UNPROCESSABLE_CONTENT` confirmado em uso, ADR-021).

**2. Frontend — typecheck + lint + build**
- `npx tsc --noEmit`: 0 erros.
- `npm run lint`: 0 warnings.
- `npm run build`: 0 erros. Bundles: `/usuarios` 4.9 kB, `/login` 1.81 kB,
  middleware 80.1 kB. Identicos ao baseline da Sessao 5b.

**3. Estado do banco em producao (via Supabase MCP)**
- `public.alembic_version` = `008` com RLS habilitado, 0 policies (ADR-025 confirmado).
- 11 RLS policies em `public.*` todas usando `is_admin = true` (ADR-018 confirmado em runtime).
- Constraints da migration 003 todas presentes: `chk_ciclo_positivo`,
  `chk_status_diferente`, `chk_ciclo_atual_positivo`, `chk_vendedor_localizacao`.
- Triggers de imutabilidade: `trg_etiquetas_imutavel`, `trg_audit_logs_imutavel`,
  `trg_movimentacoes_imutavel` + 3 triggers `_updated_at` ativos.
- Indexes Wave 1: `idx_usuarios_created_by` (migration 005),
  `idx_configuracoes_sistema_updated_by` (migration 008).
- Trigger functions: `fn_bloquear_alteracao` e `fn_atualizar_updated_at` ambas com
  `search_path = ''` (ADR-024 confirmado).
- **Estado de usuarios**: 2 linhas em `public.usuarios`, 2 em `auth.users`,
  0 banidos, 0 orfaos, sync_state=OK. **1 admin ativo** (vide notas operacionais abaixo).

**4. Advisors do Supabase**
- **Security**: 1x INFO `rls_enabled_no_policy` em `alembic_version` (esperado, ADR-025)
  + 1x WARN `auth_leaked_password_protection` (WONTFIX, ADR-027). **Sem novos achados.**
- **Performance**: 11x WARN `auth_rls_initplan` (Decisao 4b, adiado para Wave 2) +
  varios INFO `unused_index` (esperado — indexes Wave 2/3 sem queries ainda).
  **Sem novos achados.**

**5. Cruzamento Codigo ↔ Requisitos (Wave 1)**

| Req | Implementacao confirmada | Evidencia |
|-----|--------------------------|-----------|
| RF-017 (cadastro com setor + localizacao) | `UserCreate` schema + `chk_vendedor_localizacao` no DB | `backend/app/domain/schemas/user.py:40-77`, migration 003 |
| RF-018 (login Supabase Auth) | Login form + middleware Next.js | `frontend/src/app/login/page.tsx:1-132`, `frontend/src/lib/supabase/middleware.ts:1-47` |
| RF-019 (CRUD usuarios admin-only) | `get_admin_user` em todos os 6 endpoints | `backend/app/api/v1/users.py` (todos os routes), `backend/app/api/deps.py:1-121` |
| RF-020 (RBAC por setor) | `require_role(*allowed_setors)` factory + RLS unificada | `backend/app/api/deps.py`, RLS migration 004 |
| RN-009 (vendedor com localizacao obrigatoria) | `model_validator` Pydantic + DB constraint | `backend/app/domain/schemas/user.py:60-77`, `backend/app/api/v1/users.py` PATCH cross-validation |
| RN-010 (proteger ultimo admin) | 4 protecoes empilhadas (PATCH self/last + DELETE self/last) | `backend/app/api/v1/users.py:33-49` (`_count_other_active_admins`) + uso em PATCH/DELETE |
| RNF-003 (timeout 30 min) | `useInactivityTimeout(30*60*1000, handleLogout)` | `frontend/src/app/(dashboard)/layout.tsx:30,148`, `frontend/src/hooks/useInactivityTimeout.ts:1-34` |
| RNF-004 (senha hashed, nunca em plaintext) | Supabase Auth gerencia bcrypt; backend so passa em POST | `backend/app/core/supabase_admin.py:create_auth_user` |

**6. Cruzamento com Backlog (Components 03/04/05 da Wave 1)**
- **Component 03 — Login**: pagina `/login` funcional, redireciona para `/usuarios`,
  middleware bloqueia acesso a rotas `(dashboard)/*` sem sessao. ✅
- **Component 04 — Users CRUD**: 6 endpoints (GET list, GET me, GET id, POST, PATCH,
  DELETE), UI com tabela + filtros + 3 modais (criar/editar/desativar). ✅
- **Component 05 — RBAC**: `is_admin` boolean no domain DB, `get_admin_user` dependency
  protegendo todos os endpoints sensiveis, RLS unificada com `is_admin = true`,
  `require_role` factory pronta para Waves futuras (uso ja preparado). ✅

### Saga auth↔DB confirmada por leitura de codigo (4 cenarios)
- **POST /users** com falha no commit → `delete_auth_user` (best-effort, ADR-020).
- **PATCH /users/{id}** ativo:false→true com falha no commit → `disable_auth_user`
  (compensacao reversa).
- **PATCH /users/{id}** ativo:true→false com falha no commit → `enable_auth_user`
  (compensacao reversa). `disable_auth_user` chamado ANTES do commit.
- **DELETE /users/{id}** com falha no commit → `enable_auth_user` (compensacao reversa).
  `disable_auth_user` chamado ANTES do commit.
- Compensacao falha → loga "drift manual" para investigacao (ADR-020).

### Resultado
- **Zero mudancas de codigo nesta sessao** — auditoria foi puramente verificadora.
- **Zero regressao**: 108 testes passando, frontend buildando limpo, advisors com mesmo
  perfil da Sessao 5b.
- **Zero drift entre auth e public.usuarios** em producao.
- **Documentacao em dia**: CHANGELOG/DECISIONS/CLAUDE refletem com precisao o estado
  atual do codigo e do banco.

### Veredicto
**Wave 1 esta APROVADA para sign-off.** Todos os requisitos funcionais (RF-017 a RF-020)
e nao-funcionais (RNF-003, RNF-004) da Wave 1 estao implementados, testados e
verificados em producao. As 3 ressalvas conhecidas (single-admin SPOF, deferred
initplan, leaked password WONTFIX) estao documentadas, monitoradas, e nao sao
bloqueantes para iniciar a Wave 2.

### Decisoes formalizadas para a Wave 2 (ADRs novos)

A auditoria nao mudou codigo, mas formalizou como ADRs duas decisoes que ate aqui
estavam soltas em texto livre no CHANGELOG. Ambas precisam ser executadas no inicio
da Wave 2:

- **ADR-029 — Reescrita das policies RLS para `(SELECT auth.uid())`** (adiada para
  Wave 2). Os 11 WARN `auth_rls_initplan` do advisor sao otimizacao, nao bug. Sem
  volume nao da para medir o ganho — a Wave 2 vai trazer `provas_digitais` e
  `movimentacoes` com dados suficientes. Plano de execucao detalhado no ADR (criar
  `backend/migrations/rls/005_initplan_optimization.sql`, aplicar via `apply_rls.py`,
  medir `EXPLAIN ANALYZE` antes/depois, confirmar zero WARN no advisor).
- **ADR-030 — Criar segundo admin operacional antes da Wave 2 entrar em uso real**
  (resolve o SPOF organizacional). Producao tem 1 unico admin (Mario). RN-010 protege
  contra auto-delete, mas se a conta auth for perdida a unica recuperacao e
  intervencao manual fora do app. Decisao: criar `ops@3studio.com.br` (ou similar) via
  o proprio fluxo `POST /api/v1/users` antes da primeira prova digital cadastrada.
  Restricoes detalhadas no ADR (conta dedicada, senha em gerenciador, validacao
  pos-criacao, registro de quem tem acesso compartilhado).

### Notas operacionais (nao bloqueantes — todas formalizadas em ADRs)
- **Single admin ativo (SPOF organizacional)** → ADR-030. Resolver na Sessao 7
  (abertura da Wave 2), antes de qualquer tarefa funcional.
- **`auth_rls_initplan` (11 WARN)** → ADR-029. Primeira tarefa tecnica da Wave 2,
  apos a primeira leva de dados de carga real.
- **`auth_leaked_password_protection`** → ADR-027 (WONTFIX). Recurso pago do Supabase.
  Compensado por: senha minima GoTrue, rate limiting nativo, signup publico
  desabilitado (todos via Admin API — ADR-013). Re-avaliar quando houver upgrade de
  plano OU se o backlog acrescentar signup publico.

### Documentos atualizados
- `CHANGELOG.md` — esta secao (sign-off da Wave 1 + referencias aos ADRs novos).
- `DECISIONS.md` — **ADR-029** (RLS initplan rewrite adiada para Wave 2) e
  **ADR-030** (criar segundo admin operacional antes da Wave 2).
- `CLAUDE.md` — sem alteracao (listagem de migrations ja estava em dia, e ADRs novos
  nao tocam migrations).

---

## [2026-04-08 — Sessao 5] — Wave 1: Auditoria critica pre-Wave 2

### Contexto
Mario pediu uma auditoria completa, critica e exigente da Wave 1 (Componentes 03-Login,
04-Users CRUD, 05-RBAC) antes de avancar para a Wave 2. Objetivo: provar que a Wave 1 esta
"100% pronta, fail-safe, robusta". Acesso a Supabase MCP e Cloudflare MCP autorizado.
Escopo: NAO tocar nas Waves 2-6. Wave 0 so com permissao explicita. Atualizar
CHANGELOG/CLAUDE/DECISIONS aditivamente.

### Verificacoes feitas (sem mudar codigo)

- **Backend testes**: 96 → 108 passed, 0 deprecation warnings, cobertura 91% global,
  `app/api/v1/users.py` 93%, `app/core/supabase_admin.py` 100%, `app/api/deps.py` 100%.
- **Frontend**: `tsc --noEmit` sem erros, `next lint` sem warnings, `next build` sem erros.
  Bundle final: `/usuarios` 4.9 kB, `/login` 1.81 kB, middleware 80.1 kB.
- **Supabase MCP** (`rwxlpwmnkekzuurgthkr`, sa-east-1, ACTIVE_HEALTHY, Postgres 17.6.1.104):
  - 6 tabelas com RLS habilitado: `usuarios` (3 linhas), `provas_digitais`, `movimentacoes`,
    `etiquetas`, `audit_logs`, `configuracoes_sistema` (2 linhas).
  - 11 policies RLS confirmadas usando `is_admin = true` (consistente com ADR-018).
  - Constraints da migration 003 presentes: `chk_ciclo_positivo`, `chk_status_diferente`,
    `chk_ciclo_atual_positivo`, `chk_vendedor_localizacao`.
  - 3 triggers de imutabilidade ativos: `trg_etiquetas_imutavel`, `trg_audit_logs_imutavel`,
    `trg_movimentacoes_imutavel` + 3 triggers `_updated_at`.
  - Indexes da migration 003 presentes: `idx_movimentacoes_created_at`, `idx_movimentacoes_prova_data`.
  - **Drift de tracking detectado**: `public.alembic_version` NAO existe e
    `supabase_migrations.schema_migrations` so tem 001/002 — migrations 003/004 foram
    aplicadas via SQL direto (ver ADR-022 para o plano de remediacao).
  - **Drift de auth detectado**: `regianepetrim@teste.com.br` tem `auth.users.banned_until =
    2126-04-09` (banido por 100 anos por DELETE antigo) MAS `public.usuarios.ativo = true`
    (alguem reativou via PATCH sem unban). Prova ao vivo dos bugs corrigidos abaixo.
  - Performance advisor (level INFO): FK `usuarios.created_by` sem index.
- **Cloudflare R2 MCP**: bucket `rastreio-provas-artes` confirmado (account
  `20ab724c91f6bda669eecfe7c51c9171`, location ENAM). Sem mudancas — Wave 0.

### Bugs CRITICOS encontrados e corrigidos

- **`backend/app/core/supabase_admin.py`** — `disable_auth_user` agora chama
  `resp.raise_for_status()` (era best-effort, apenas logava). Adicionada nova funcao
  `enable_auth_user(auth_uid)` que faz `PUT /auth/v1/admin/users/{id}` com
  `{"ban_duration": "none"}` (convencao GoTrue para desbanir). `delete_auth_user` PERMANECE
  best-effort por design (so e chamada no rollback de create — la o erro do DB ja aconteceu
  e nao podemos mascara-lo). Ver ADR-020.
- **`backend/app/api/v1/users.py` — PATCH `/users/{id}`**:
  - **Bug fixado**: PATCH `ativo: false → true` agora chama `enable_auth_user` ANTES do
    commit. Antes, o usuario continuava banido em `auth.users` mesmo apos reativacao no
    app DB → drift real em producao (regiane).
  - **Logica nova**: detecta `was_active != will_be_active` antes de mutar o objeto. Se
    `needs_ban`, chama `disable_auth_user`; se `needs_unban`, chama `enable_auth_user`.
    Falha auth → 502 + rollback, sem persistir nada.
  - **Compensacao saga**: se `db.commit()` falhar APOS auth ja ter mudado, faz a operacao
    inversa (re-enable apos ban falho, re-disable apos unban falho). Falha de compensacao
    loga "drift manual" para investigacao operacional.
- **`backend/app/api/v1/users.py` — DELETE `/users/{id}`**:
  - **Bug fixado**: `disable_auth_user` agora roda ANTES de `db.commit()`. Antes, se a
    chamada GoTrue falhasse, o usuario ficava `ativo=false` no app DB mas com tokens
    ainda renovaveis na auth.
  - **Compensacao saga**: se `db.commit()` falhar apos disable, chama `enable_auth_user`
    para reverter o ban. Falha de compensacao loga "drift manual".
- **Deprecation warnings**: 4 ocorrencias de `HTTP_422_UNPROCESSABLE_ENTITY` substituidas
  por `HTTP_422_UNPROCESSABLE_CONTENT` (Starlette 0.40+, RFC 9110). Ver ADR-021.

### Migration nova (NAO aplicada — aguarda decisao do Mario)

- **`backend/migrations/versions/005_add_index_on_usuarios_created_by.py`** — Cria
  `idx_usuarios_created_by` na FK `usuarios.created_by → usuarios.id`. Idempotente
  (`IF NOT EXISTS`). Resolve o aviso INFO do Supabase advisor. **Pendente:** definir como
  aplicar — via Alembic (precisa estabilizar tracking — ADR-022) ou via Supabase MCP
  `apply_migration` (mais rapido, mas perpetua o drift).

### Tests adicionados

- **`backend/tests/test_supabase_admin.py`** (+2 testes):
  - `test_disable_auth_user_failure_raises` (substitui `_does_not_raise`) — confirma novo
    contrato de raise.
  - `test_enable_auth_user_success` — verifica metodo PUT, URL, payload `{"ban_duration": "none"}`.
  - `test_enable_auth_user_failure_raises` — confirma propagacao de erro.
- **`backend/tests/test_users_api.py`** (+9 testes):
  - `test_update_user_reactivation_unbans_in_auth` — PATCH `ativo:false→true` chama
    `enable_auth_user`.
  - `test_update_user_deactivation_bans_in_auth_before_commit` — PATCH `ativo:true→false`
    chama `disable_auth_user` ANTES do commit (verifica ordem).
  - `test_update_user_unrelated_field_does_not_touch_auth` — PATCH so de `nome` nao toca
    em auth.
  - `test_update_user_ban_failure_returns_502_and_does_not_commit`.
  - `test_update_user_unban_failure_returns_502_and_does_not_commit`.
  - `test_update_user_db_commit_fails_after_ban_compensates` — saga reversa.
  - `test_update_user_db_commit_fails_after_unban_compensates` — saga reversa inversa.
  - `test_deactivate_user_disable_runs_before_commit` — DELETE: ordem `disable → commit`.
  - `test_deactivate_user_ban_failure_returns_502_and_does_not_commit`.
  - `test_deactivate_user_db_commit_fails_after_ban_compensates`.
- Atualizado `test_patch_skips_last_admin_check_for_non_admin_target` para mockar
  `disable_auth_user` (agora a transicao `ativo:true→false` chama auth).

### Resultado final

- **108 passed, 1 warning** (warning intencional do JWT test com chave curta), 0
  deprecation warnings, **91% cobertura global**, 93% em `users.py`, 100% em
  `supabase_admin.py`/`api/deps.py`.
- Frontend continua passando em `tsc`, `next lint`, `next build`.
- Estado auth↔app no codigo: garantidamente convergente ou logado como drift explicito.

### Acoes pendentes (aguardam Mario)

1. **Reativar `regianepetrim@teste.com.br` no Supabase Auth**: o drift atual continua em
   producao. Opcoes: (a) chamar `enable_auth_user(uid)` via script, (b) Supabase Dashboard
   → Authentication → Users → Unban.
2. **Aplicar migration 005**: via Alembic (precisa estabilizar tracking primeiro — ver
   ADR-022) ou via Supabase MCP `apply_migration` (mais rapido, perpetua drift).
3. **Estabilizar tracking de migrations**: rodar `alembic stamp head` para criar
   `public.alembic_version` apontando para 004, antes de aplicar 005 via Alembic.
4. **Wave 0 — issues do advisor (NAO toquei, aguarda autorizacao)**:
   - `function_search_path_mutable` em `fn_bloquear_alteracao` e `fn_atualizar_updated_at`.
   - `auth_rls_initplan` (multiple permissive policies — performance, nao seguranca).
   - `leaked_password_protection` desabilitado no Auth (HaveIBeenPwned check off).

### Documentos atualizados

- `DECISIONS.md` — ADRs 020 (saga auth↔DB), 021 (HTTP_422_UNPROCESSABLE_CONTENT), 022
  (drift de tracking), 023 (index FK created_by).
- `CHANGELOG.md` — esta sessao.

---

## [2026-04-08 — Sessao 5b] — Wave 1: Execucao do plano da auditoria (migrations 005→008)

### Contexto
Apos a auditoria da Sessao 5, Mario aprovou o plano completo: estabilizar o tracking
Alembic, aplicar a migration 005, e tratar os warnings Wave 0 que eu havia listado como
pendentes (search_path mutavel + impactos colaterais detectados durante a execucao).
Mario ficou com 2 acoes manuais no Dashboard (unban da regiane + ativar leaked password
protection); todo o resto foi executado nesta sessao via Supabase MCP. **Escopo Wave 0
liberado explicitamente para os 3 warnings desta sessao** — nao para o restante.

### Estabilizacao do tracking Alembic (ADR-022 endereçado)

- **`python -m alembic stamp 004`** rodado contra producao com `DATABASE_URL` apontando
  para `aws-1-sa-east-1.pooler.supabase.com:5432` (pooler Session). `env.py` usa
  `python-dotenv` para carregar `.env` e converte `postgresql+asyncpg://` →
  `postgresql://` para o driver sync do Alembic.
- Criou `public.alembic_version` com `version_num = '004'`. **Side effect detectado pelo
  advisor de seguranca**: tabela criada SEM RLS no schema `public`, exposto via PostgREST
  (qualquer cliente com a anon key conseguia ler/escrever o numero da versao). Tratado
  por uma migration nova (007) ainda nesta sessao — ver abaixo.
- **`python -m alembic upgrade head`** aplicou a migration 005 normalmente. Verificacao
  via MCP `execute_sql` confirmou `idx_usuarios_created_by` em `pg_indexes` e
  `alembic_version = 005`.

### Migrations novas aplicadas em producao (todas via Alembic, idempotentes)

- **`backend/migrations/versions/005_add_index_on_usuarios_created_by.py`** (criada na
  Sessao 5, aplicada nesta) — `CREATE INDEX IF NOT EXISTS idx_usuarios_created_by ON
  usuarios(created_by)`. Resolveu o INFO `unindexed_foreign_keys` do advisor.
- **`backend/migrations/versions/006_set_search_path_on_trigger_functions.py`** (nova) —
  `ALTER FUNCTION public.fn_bloquear_alteracao() SET search_path = '';` +
  `ALTER FUNCTION public.fn_atualizar_updated_at() SET search_path = '';`. Resolveu os
  WARN `function_search_path_mutable` (ADR-024). Validado em runtime: `UPDATE` em
  `configuracoes_sistema` continuou disparando o `_updated_at` corretamente
  (`updated_at` mudou de `2026-04-07` para `2026-04-08`). As tabelas imutaveis
  (`movimentacoes`/`etiquetas`/`audit_logs`) estao vazias e nao foi possivel testar
  `fn_bloquear_alteracao` ao vivo, mas a fonte usa apenas built-ins schema-qualified
  (`NOW()`, `RAISE EXCEPTION`) — sem dependencia de `search_path`.
- **`backend/migrations/versions/007_enable_rls_on_alembic_version.py`** (nova, **fix de
  side effect** do `alembic stamp`) — `ALTER TABLE public.alembic_version ENABLE ROW
  LEVEL SECURITY;` sem nenhuma policy. Postgres com RLS ligado e zero policies bloqueia
  100% do PostgREST por default. O role `postgres` usado pelo Alembic bypassa RLS, entao
  `alembic upgrade head` continua funcionando. Verificacao via MCP confirmou
  `relrowsecurity = true`. Resolveu o ERROR `rls_disabled_in_public` que apareceu
  imediatamente apos o stamp. Ver ADR-025.
- **`backend/migrations/versions/008_add_index_on_configuracoes_sistema_updated_by.py`**
  (nova, **bonus finding** durante o re-run do advisor) — `CREATE INDEX IF NOT EXISTS
  idx_configuracoes_sistema_updated_by ON configuracoes_sistema(updated_by)`. Mesmo
  padrao do 005, em uma FK da migration 001 que tinha sido esquecida. Provavelmente o
  advisor so reportava a primeira FK sem index, e expos a segunda quando o primeiro foi
  corrigido. Ver ADR-026.

### Estado final do tracking
- `public.alembic_version` existe, esta com RLS habilitado (zero policies = bloqueia
  PostgREST), `version_num = '008'`, e e a fonte de verdade do dominio Wave 1.
- `supabase_migrations.schema_migrations` continua refletindo apenas o que a CLI Supabase
  aplicou (001/002). Convivencia documentada — Alembic = dominio, Supabase migrations =
  setup inicial fora do escopo Alembic.

### Resultado dos advisors apos as migrations

- **Security advisor** — antes: 2x WARN `function_search_path_mutable` + 1x WARN
  `auth_leaked_password_protection`. Depois: 1x INFO `rls_enabled_no_policy` em
  `public.alembic_version` (esperado, e o objetivo do fix) + 1x WARN
  `auth_leaked_password_protection` (Decisao 4c — Mario precisa habilitar via Dashboard,
  nao tem API). Tudo o mais limpo.
- **Performance advisor** — antes: 1x INFO `unindexed_foreign_keys`
  (`usuarios.created_by`) + 11x WARN `auth_rls_initplan` + varios INFO `unused_index`.
  Depois: o INFO original sumiu (resolvido por 005), surgiu e foi resolvido o INFO
  bonus em `configuracoes_sistema.updated_by` (resolvido por 008), os 11 WARN
  `auth_rls_initplan` permanecem (Decisao 4b — adiado para a Wave 2 quando houver
  trafego real para medir o ganho), os INFO `unused_index` permanecem (esperado — sao
  indexes para Wave 2/3 que ainda nao tem queries).

### Tests
- **`python -m pytest -q --no-header`** depois das 4 migrations: **108 passed, 1
  warning** (mesmo warning intencional do JWT test). Migrations sao DDL/metadata-only
  (CREATE INDEX, ALTER FUNCTION, ALTER TABLE) e os testes mockam Supabase Auth, entao
  nao dependem do estado real de producao — confirmacao de que a aplicacao continua
  estavel apos as mudancas no banco.

### Acoes manuais (resolvidas em adendo apos o relatorio)

1. ~~**Unban da regiane**~~ — **RESOLVIDO POR DELETE** (ver ADR-028). Mario informou que
   (a) nao conseguiu unban no Dashboard, e (b) a conta foi criada apenas para teste e
   poderia ser apagada. Executei a remocao completa:
   - Verificacao via MCP: 0 usuarios dependiam dela via FK `created_by` — seguro apagar.
   - `DELETE FROM public.usuarios WHERE id = '038fa2a9...'` via MCP `execute_sql`.
   - `delete_auth_user('2943ba9a...')` via `python -c` (usa o GoTrue Admin API ja
     implementado em `app/core/supabase_admin.py`, limpa `auth.users` + `auth.identities`
     em cascata e revoga sessions).
   - Verificacao final via MCP: 0 linhas em `public.usuarios`, `auth.users`,
     `auth.identities`, `auth.sessions`. Drift 100% resolvido.
   - Estado pos-cleanup: 2 usuarios ativos em `public.usuarios` (Mario + outro admin),
     2 correspondentes em `auth.users`, sem drift.
2. ~~**Habilitar `auth_leaked_password_protection`**~~ — **WONTFIX** (ver ADR-027). Mario
   informou que o feature nao esta disponivel no plano atual do projeto (recurso pago).
   Aceito como WARN permanente do advisor enquanto nao houver upgrade de plano.
   Compensacoes em vigor: senha minima do GoTrue, rate limiting nativo, ausencia de
   signup publico (todos os usuarios sao criados por admin via Admin API — ADR-013).
   Quando o plano for upgrade, basta ativar o toggle no Dashboard, sem mudanca de codigo.

### Decisoes adiadas (registradas, NAO executadas nesta sessao)

- **`auth_rls_initplan` (11 WARN)** — Decisao 4b. Reescrever as policies para usar
  `(SELECT auth.uid())` em vez de `auth.uid()` direto, evitando re-execucao por linha.
  Ganho de performance so e mensuravel com volume real (tabelas estao com 0-3 linhas).
  Adiado para a Wave 2, quando houver dados de teste suficientes para medir.

### Documentos atualizados

- `DECISIONS.md` — ADRs 024 (search_path nas trigger functions), 025 (RLS na
  alembic_version — fix de side effect), 026 (index FK configuracoes_sistema.updated_by),
  **027 (leaked password protection WONTFIX)**, **028 (remocao da conta de teste regiane)**.
- `CLAUDE.md` — listagem de migrations atualizada (005 marcada como aplicada, 006/007/008
  adicionadas).
- `CHANGELOG.md` — esta secao.

---

## [2026-04-08 — Sessao 4] — Wave 1: Redesign Gerenciador de usuarios (Figma)

### Contexto
Mario forneceu 2 referencias do Figma (pagina admin e modal de novo usuario) e a paleta
exportada do documento. Figma MCP bloqueado por quota Starter, entao a implementacao usou
os PNGs colados na conversa + a lista de cores do guia. Escopo restrito a Wave 1 (somente
gerenciamento de usuarios); sidebar foi expandida com os itens das waves futuras
(Dashboard/Provas/Nova prova/Escanear/Relatorios/Configuracoes/Informacoes) mas renderizados
como `<span>` sem `href` — quando cada pagina for criada, basta trocar por `<Link>` sem
acoplamento adicional. Backend intocado (ja passa nos 96 testes com 91% de cobertura).

### Design tokens (Figma → CSS custom properties)

- **frontend/src/app/globals.css** — Arquivo reescrito para separar explicitamente DUAS
  superficies visuais:
  - Superficie escura (sidebar, login, modais): `--color-bg: #000`, `--color-bg-input: #1f1f1f`,
    `--color-text-primary: #fff`, `--color-text-secondary: #b7b7b7`, `--color-text-dim: #868686`.
  - Superficie clara (cartao principal do dashboard): `--color-card-bg: #eaeaea`,
    `--color-card-surface: #d9d9d9` (inputs/filtros), `--color-card-surface-alt: #d7d7d7` (tabela),
    `--color-card-divider: #b7b7b7`, `--color-card-text: #000`, `--color-card-text-muted: #575757`,
    `--color-card-border: #868686`.
  - Acentos compartilhados: `--color-accent: #ffcb5c`, `--color-danger: #ff5959` (antes `#e74c3c`,
    trocado para casar com o guia do Figma), `--color-overlay: rgba(59, 59, 59, 0.4)` (= `#3B3B3B` a 40%).
  - Radius: `--radius-pill: 9999px` (antes `50px`), `--radius-card-lg: 24px`, `--radius-card-xl: 28px`.
  - Tipografia: escala `--fs-display/title/h2/xl/lg/base/sm/xs` + `--fs-display` com `clamp()`
    para o titulo do cartao escalar com a viewport.
  - `select { appearance: none }` global para que o chevron SVG seja posicionado via CSS.
  - `--card-padding: clamp(1.5rem, 3vw, 3rem)` — padding interno responsivo do cartao.
  - Verificado em runtime via `preview_eval` que todos os 10 tokens criticos estao disponiveis
    no `:root` com os valores exatos da paleta.

### Componente de icones

- **frontend/src/components/icons.tsx** (novo) — 12 icones SVG inline outline, `stroke="currentColor"`,
  `strokeWidth: 1.75`, `viewBox 0 0 24 24`: `SearchIcon`, `HomeIcon`, `LaptopIcon`, `PlusIcon`,
  `ScanIcon`, `ChartIcon`, `UserIcon`, `GearIcon`, `InfoIcon`, `ChevronDownIcon`, `CheckIcon`,
  `CloseIcon`. Todos aceitam `SVGProps<SVGSVGElement>` (size via width/height, className, etc).
  Decisao: **nao instalar `lucide-react`/`heroicons`** — zero dependencia nova, peso minimo,
  controle total sobre o stroke.

### Layout do dashboard (sidebar + cartao)

- **frontend/src/app/(dashboard)/layout.tsx** — Sidebar reescrita fiel ao Figma:
  - Bloco topo: logo "3STUDIO" + "Ola {firstName}!" + campo de busca (pill cinza escuro).
  - `MAIN_NAV` (6 itens: Dashboard, Provas, Nova prova, Escanear, Relatorios, Usuarios) e
    `SECONDARY_NAV` (Configuracoes, Informacoes). Apenas "Usuarios" tem `href: "/usuarios"`.
    Componente interno `NavEntry` renderiza `<Link>` quando ha href ou `<span aria-disabled>`
    caso contrario — **nao cria rotas 404** para as waves futuras.
  - Item ativo marcado por barra vertical amarela (`::before` absoluto com `background: var(--color-accent)`).
  - Rodape: grid 44px/1fr/auto com avatar circular cinza, nome/"3Studio", botao "Sair" em amarelo.
  - Preservados: drawer mobile off-canvas, ESC fecha, backdrop, body scroll lock, `useInactivityTimeout`.
- **frontend/src/app/(dashboard)/layout.module.css** — CSS reescrito:
  - `.sidebar` com `padding: 2.25rem 1.5rem 1.75rem`, flex column com `justify-content: space-between`.
  - `.main` com `padding: 1.5rem` (mostra fundo preto em volta do cartao) + `.card` com
    `background: var(--color-card-bg); border-radius: var(--radius-card-xl); padding: var(--card-padding)`.
  - Mobile (<=768px): `.main { padding: 0.75rem }`, `.card { padding: 1.25rem; border-radius: var(--radius-card-lg) }`.

### Pagina /usuarios (conteudo do cartao)

- **frontend/src/app/(dashboard)/usuarios/page.tsx** — Estrutura JSX reescrita:
  - `<header class="pageHeader">` com titulo "Gerenciador de usuarios" (var(--fs-display)) + botao
    "Novo usuario" (pill amarelo).
  - `<section class="filters">` com 3 campos pill:
    - `.searchField` (flex: 1) com `<SearchIcon>` absoluto a esquerda do `<input type="search">`.
    - 2 `.selectField` com `<select>` + `<ChevronDownIcon>` absoluto a direita (appearance: none).
  - `<section class="tableWrap">` — tabela sobre `--color-card-surface-alt` (#d7d7d7), headers em
    `--color-card-text-muted`, divisores horizontais sutis (`rgba(183, 183, 183, 0.55)`).
  - Acoes por linha: `.editBtn` (pill preto) + `.dangerBtn` (pill vermelho) — apenas quando a linha
    esta ativa.
  - 3 modais (create/edit/deactivate) com:
    - Overlay `rgba(59, 59, 59, 0.4)` + `backdrop-filter: blur(1px)`.
    - `.modal` em fundo preto puro, `border-radius: var(--radius-card-lg)`, `padding: 2rem 2.25rem`.
    - Titulo `var(--fs-h2)` + `.modalDivider` (linha horizontal branca a 35%).
    - Inputs em `--color-bg-input` (pill) com foco amarelo.
    - Checkbox "Administrador" custom: `<span class="checkBox">` com `:checked + .checkBox::after`
      desenhando o check via bordas rotacionadas (preto sobre amarelo).
    - Botoes: `.btnSecondary` (pill cinza escuro "Cancelar") + `.btnPrimary` (pill amarelo "Cadastrar")
      ou `.btnDanger` (pill vermelho "Desativar").
  - `role="dialog"`, `aria-modal="true"`, `aria-labelledby` apontando para o `<h2>` de cada modal.
- **frontend/src/app/(dashboard)/usuarios/usuarios.module.css** — Reescrito (540 linhas) para
  implementar tudo acima + breakpoint mobile (tabela com `min-width: 720px` e scroll horizontal,
  modal `flex-direction: column-reverse` nas acoes, botoes ocupando 100%).

### Itens das waves futuras (sem acoplamento)

- `MAIN_NAV[0..4]` e `SECONDARY_NAV` sao renderizados como `<span aria-disabled="true">` dentro do
  `NavEntry`. Quando a Wave 2 criar `/dashboard`, `/provas`, etc, basta **adicionar `href` no array
  correspondente** e o `NavEntry` automaticamente vira `<Link>`. Zero mudanca de CSS, zero mudanca
  estrutural. O active-state por pathname ja funciona.
- Os icones ja estao prontos em `@/components/icons` — nao sera necessario criar novos para as
  Waves 2-5 a menos que aparecam itens especificos.

### Verificacao

- **TypeScript**: `npx tsc --noEmit` passou sem output (strict mode, 2 arquivos novos + 4 alterados).
- **Build Next**: `npx next build` → `✓ Compiled successfully`, `✓ Generating static pages (6/6)`.
  Paginas: `/usuarios` 4.75 kB (154 kB first load), `/login` 7.16 kB (157 kB). Middleware 80.1 kB.
- **Preview runtime**: server subiu em porta 57870 (autoPort ligado no `.claude/launch.json` porque
  ha processo node leftover na 3000), sem erros de servidor, sem erros de console, login renderiza
  identico ao anterior em desktop e mobile (375x812), tokens claros confirmados em runtime via
  `getComputedStyle(:root)` — todos batem exatamente com a paleta do Mario.
- **Middleware**: `window.location.href = '/usuarios'` no preview redireciona para `/login` (auth
  middleware continua funcionando; a pagina renderizada so pode ser vista com sessao autenticada).

### Arquivos alterados nessa sessao

```
M  .claude/launch.json                                (autoPort: true em frontend)
M  frontend/src/app/globals.css                       (tokens + superficies)
A  frontend/src/components/icons.tsx                  (12 icones SVG)
M  frontend/src/app/(dashboard)/layout.tsx            (sidebar completa)
M  frontend/src/app/(dashboard)/layout.module.css    (estilos sidebar + cartao)
M  frontend/src/app/(dashboard)/usuarios/page.tsx    (JSX redesign)
M  frontend/src/app/(dashboard)/usuarios/usuarios.module.css  (CSS redesign)
M  CHANGELOG.md                                       (este bloco)
```

### Pegadinhas resolvidas

1. **Figma MCP bloqueado por quota do plano Starter** — `get_design_context`, `get_screenshot`
   e `get_metadata` retornaram todos o mesmo paywall. Solucao: Mario colou PNGs @2x + paleta
   exportada, e a implementacao usou os pixels das imagens + os hex codes escritos.
2. **Port 3000 ocupado** — Processo node leftover (provavelmente de outra sessao). Em vez de
   matar sem permissao, habilitei `autoPort: true` em `.claude/launch.json` e o preview subiu em
   57870. Nao toca no dev server que estava rodando antes.
3. **`--color-danger` antigo (`#e74c3c`) nao batia com a paleta do Figma (`#ff5959`)** — trocado
   no `:root`. O login usa o token via `var(--color-danger)` para mensagens de erro, entao agora
   fica coerente com o resto do sistema (antes tinha 2 tons de vermelho no projeto).
4. **`--radius-pill` estava `50px` (fixo)** — botoes grandes do Figma exigem pill verdadeiro
   independentemente da altura. Trocado para `9999px`.

### Pendente

- Visualizacao manual autenticada de `/usuarios` (exige login real, fora do escopo automatizado).
- Quando as paginas das Waves 2+ forem criadas, substituir `<span aria-disabled>` por `<Link>`
  nos items correspondentes do `MAIN_NAV`/`SECONDARY_NAV` em `layout.tsx`.

### Ajustes pos-feedback (mesma sessao)

Mario revisou o resultado e pediu 3 correcoes baseadas em um PNG adicional da tabela:

1. **Tabela sem preenchimento** — o `background: var(--color-card-surface-alt)` saiu. Agora
   `.tableWrap` e transparente e mostra apenas um contorno `1px solid var(--color-card-border)`
   com `border-radius: var(--radius-card-lg)` e `overflow: hidden` (pra borda nao vazar sobre
   o scroll interno).
2. **Conteudo centralizado** — todos os `th`/`td` passaram de `text-align: left` para `center`,
   com `vertical-align: middle`. `.actions` (botoes Editar/Desativar) passou de `justify-content:
   flex-end` para `center`. `.thActions` tambem.
3. **Linhas verticais entre colunas** — cada `th`/`td` recebeu `border-right: 1px solid
   var(--color-card-border)`. A regra `:last-child { border-right: none }` evita linha dupla
   encostando na borda direita do contorno externo. A linha horizontal abaixo do header
   (`thead tr { border-bottom }`) foi mantida. Nao ha linhas horizontais entre rows (fiel ao
   PNG).
4. **Scroll interno** — `.tableScroll` (novo wrapper `<div>` dentro de `.tableWrap`) isola o
   `overflow-x: auto`, mantendo o contorno arredondado do pai intacto quando a tabela precisa
   rolar horizontalmente (mobile).
5. **Logo da sidebar = logo do login** — `layout.tsx` agora importa `next/image` e renderiza
   `<Image src="/images/logo-3studio.svg" width={132} height={28} priority />` em vez do texto
   `<div>3STUDIO</div>`. O CSS `.logo` foi simplificado para `width: 132px; height: auto;
   margin-bottom: 2rem`. Mesmo asset que a tela de login (carregamento ja cacheado).

Rebuild apos ajustes:
- `npx tsc --noEmit` → limpo
- `npx next build` → `✓ Compiled successfully`, `/usuarios` 4.77 kB, `/login` 1.81 kB
- `preview_eval` confirmou que o `img[alt="3Studio"]` carrega com `src="/images/logo-3studio.svg"`,
  `naturalWidth: 122`, sem erros de servidor nem console.

### Segunda rodada de feedback (mesma sessao) — respiro nas linhas verticais

Mario notou que no Figma as linhas verticais internas da tabela tem um "respiro" (nao
encostam no contorno externo do card — tem um gap de ~12px no topo e embaixo). Minha
implementacao anterior deixava as linhas verticais indo de borda a borda.

**Fix**: `padding: 4rem 0` no `.tableWrap` (apenas top/bottom, zero nos lados — valor
ajustado por Mario depois de visualizar, pra casar com o respiro generoso do Figma).
Como as bordas verticais (`border-right`) dos `th`/`td` ficam DENTRO da area padded,
elas ficam naturalmente contidas a 64px do topo e 64px da base do card — sem tocar a
linha de contorno externa. A linha horizontal do `thead tr { border-bottom }` continua
full width porque nao ha padding horizontal.

### Terceira rodada — Mobile redesign (mesma sessao)

Mario ajustou o desktop manualmente (sidebar-width 400px, padding 4rem, logo SVG via
`<Image>`, itens centralizados, espessuras ajustadas) e pediu para redesenhar APENAS o
mobile: header novo em formato pill arredondado com logo a esquerda e hamburger a
direita (igual ao Figma), e a tela de gerenciamento trocada por uma mensagem no mobile.

#### Mudancas

- **`frontend/src/app/(dashboard)/layout.tsx`**
  - Importa `CloseIcon` do `@/components/icons`.
  - Novo markup do mobile header: `<header className={styles.mobileHeader}>` contendo
    um `<div className={styles.mobileHeaderInner}>` com `<Image src="/images/logo-3studio.svg" />`
    (100x22) a esquerda e o botao hamburger a direita. O hamburger so ABRE o drawer
    (`setIsMobileNavOpen(true)`) — o fechamento passou a ser responsabilidade do X
    dentro do drawer e do backdrop/ESC, que ja existiam.
  - Dentro do `<aside>` drawer, novo botao `<button className={styles.closeBtn}>` com
    `<CloseIcon />` no topo-direita — visivel apenas no mobile, esconde no desktop.

- **`frontend/src/app/(dashboard)/layout.module.css`**
  - Bloco `@media (max-width: 768px)` completamente reescrito.
  - `.mobileHeader` vira um container com padding externo (1rem 1rem 0.5rem) que cria
    respiro em volta do pill. `.mobileHeaderInner` e o pill propriamente: altura 56px,
    `background: var(--color-bg-input)`, `border-radius: 9999px`, padding 0 1.5rem,
    flex space-between.
  - `.hamburger` dentro do pill: 26x18, 3 barras brancas de 2px.
  - `.closeBtn` desktop: `display: none`. Mobile: `display: inline-flex`, absolute top
    1.5rem right 1.25rem, 36x36, stroke branco.
  - `.sidebar` mobile agora tem `border-top-right-radius: 28px` e `border-bottom-right-radius: 28px`
    (drawer com cantos arredondados no lado direito, fiel ao Figma). Width `min(80vw, 340px)`.
  - `.greeting` e `.searchBox` escondidos no mobile (`display: none`) — o Figma nao mostra
    esses elementos dentro do drawer mobile, so logo + menu + bloco usuario.
  - `.logo` reduzida para 100px no mobile e `margin-bottom: 1.5rem`.
  - `.main` mobile: `padding: 0 1rem 1rem` (sem top, porque o `.mobileHeader` ja tem
    `padding-top: 1rem`). `.card` com `padding: 1.5rem 1.25rem`.

- **`frontend/src/app/(dashboard)/usuarios/page.tsx`**
  - Adicionado wrapper `<div className={styles.mobileNotice}>` com o paragrafo
    "Para acessar esse recurso, acesse a versão desktop." — sempre presente no DOM
    mas escondido no desktop.
  - Todo o conteudo existente (header + filtros + tabela + pagination) envolvido em
    `<div className={styles.desktopOnly}>`. Os modais ficam FORA desse wrapper porque
    (1) sao `position: fixed` e nao entrariam no fluxo de "contents" de qualquer jeito,
    (2) no mobile os botoes que disparam os modais (Novo usuario / Editar / Desativar)
    estao dentro do `.desktopOnly` escondido, entao nao ha como abrir um modal no mobile.

- **`frontend/src/app/(dashboard)/usuarios/usuarios.module.css`**
  - Novos seletores `.mobileNotice` (desktop: `display: none`) e `.desktopOnly`
    (desktop: `display: contents` — nao interfere no layout flex dos filhos).
  - Bloco `@media (max-width: 768px)` simplificado: esconde `.desktopOnly` e mostra
    `.mobileNotice` como flex centralizado (min-height 60vh, paragrafo 1.125rem em
    `--color-card-text-muted`, max-width 320px pra quebrar bonito em textos longos).
  - Removido o bloco antigo que tentava adaptar tabela/modais no mobile — nao sao
    mais alcancaveis.

#### Verificacao
- `npx tsc --noEmit` → limpo
- `rm -rf .next && npx next build` → `✓ Compiled successfully`, `/usuarios` 4.9 kB
  (era 4.77 kB; delta de 130B pelo aviso mobile + wrapper), `/login` 1.81 kB
- Preview no viewport mobile 375x812: login renderiza normalmente, sem erros de
  servidor nem console. `/usuarios` retorna `opaqueredirect` (middleware de auth
  funcionando — comportamento esperado sem sessao).

#### Decisao de arquitetura (explica porque `display: contents` no wrapper)

Usei `display: contents` no `.desktopOnly` em vez de `display: block` pra nao criar
um `div` extra no grafo de layout quando visivel no desktop. Isso garante que o CSS
existente do `.pageHeader`, `.filters`, `.tableWrap` e `.pagination` continue se
comportando igual (flex gaps, margin-bottom entre secoes, etc) — como se o wrapper
nao estivesse la. No mobile o `display: none` esconde normalmente e os filhos nao
renderizam. Trade-off: `display: contents` tem suporte desigual em screen readers
historicamente, mas para um wrapper visual sem semantica acessivel essa e uma
aplicacao OK (o proprio MDN recomenda pra esse caso).

Apos o fix tambem precisei fazer `rm -rf .next && npx next build` — o cache do Next
estava retornando `PageNotFoundError: /_document` num primeiro rebuild. Depois da
limpeza compilou limpo (`✓ Compiled successfully`, mesmos tamanhos).

---

## [2026-04-08 — Sessao 3] — Wave 1: Estabilizacao (auditoria + testes + UX)

### Contexto
Auditoria completa antes de avancar para a Wave 2. Mario solicitou conferencia minuciosa
de toda a Wave 1 (Wave 0 esta congelada). 5 frentes: bloqueantes da Sessao 2, hardening
de seguranca, cobertura de testes, polimentos de frontend, atualizacao de docs.
Pre-condicao do Mario: nao iniciar Wave 2 ate Wave 1 estar 100% estavel.

### Bloco 1 — Bloqueantes resolvidos

- **backend/.env, backend/.env.example** — `DATABASE_URL` corrigida de `aws-0-sa-east-1.pooler.supabase.com:6543` para `aws-1-sa-east-1.pooler.supabase.com:5432`. Causa raiz: Supabase atualizou a infraestrutura do Supavisor em sa-east-1 e migrou tenants para `aws-1-`. Mesma senha funciona com o novo hostname/porta. `/health/db` agora retorna `method: "pooler"`.
- **backend/app/core/jwt.py** — `_fetch_jwks` reescrito com `httpx.AsyncClient` (era sync, bloqueava o event loop). Adicionado `JWKS_CACHE_TTL_SECONDS = 3600`, `_jwks_cached_at` e `asyncio.Lock` para anti-thundering-herd. Algoritmos restritos a `{"ES256", "HS256"}` — qualquer outro `alg` no header e rejeitado antes de tentar verificar (mitiga algorithm confusion). Ver ADR-016.
- **backend/app/main.py** — Registrado `@app.exception_handler(Exception)` que retorna `JSONResponse(500)` DENTRO da pilha de middleware. Sem isso, o `ServerErrorMiddleware` default do Starlette respondia fora do `CORSMiddleware` e o browser reportava "CORS error" para qualquer 500 real. Ver ADR-017.
- **backend/app/api/deps.py** — `verify_token(token)` agora `await`-ado (era chamada sincrona).
- **backend/pyproject.toml** — Adicionado `psycopg2-binary>=2.9,<3.0` (necessario para Alembic e `apply_rls.py` que usam driver sync). Adicionado `pytest-cov>=5.0,<7.0` em dev deps.

### Bloco 2 — Hardening RLS + RBAC

- **backend/migrations/rls/004_unify_rls_is_admin.sql** (novo, aplicado ao Supabase via MCP) — Substitui `setor = 'STUDIO'` por `is_admin = true` em TODAS as policies admin de `provas_digitais` (SELECT/INSERT/UPDATE), `movimentacoes` (SELECT), `etiquetas` (SELECT), `audit_logs` (SELECT) e `configuracoes_sistema` (SELECT/UPDATE). Logica de negocio por setor (VENDEDOR/MOTORISTA/CLICHERIA) preservada. Verificado em `pg_policies`: 11 policies usando `is_admin`, zero `setor=STUDIO` remanescente. Ver ADR-018.
- **backend/app/api/v1/users.py** — Helper `_count_other_active_admins(db, exclude_id)`. PATCH e DELETE agora bloqueiam (409 "ultimo administrador") qualquer operacao que deixaria o sistema sem admin ativo. Cobre os casos: demover (`is_admin=false`) ou desativar (`ativo=false`) o unico admin restante. Self-protection (admin nao pode se demover) permanece como check anterior. Ver ADR-019.

### Bloco 3 — Cobertura de testes (38 → 83 testes)

- **backend/tests/test_jwt.py** (novo, 11 testes) — Algoritmos rejeitados (`HS384`, `none`), ES256 happy path com keypair gerado em runtime e JWKS mockado, ES256 com kid desconhecido, expiracao, audience errado, HS256 fallback, cache reuso dentro do TTL, refresh apos TTL expirado, refresh em cache miss por kid (rotacao de chave).
- **backend/tests/test_supabase_admin.py** (novo, 7 testes) — `_admin_headers` com Service Role Key, `create_auth_user` happy path + 422 propagado, `delete_auth_user` happy path + falha que NAO levanta (best-effort log), `disable_auth_user` happy path + falha que NAO levanta. Mock de `httpx.AsyncClient` via `_FakeAsyncClient` que grava chamadas.
- **backend/tests/test_health.py** (novo, 7 testes) — `/health` ok, `/health/db` happy path pooler, fallback REST quando pooler falha, erro quando ambos falham, fallback REST 5xx tambem reporta erro, `/health/r2` ok e falha.
- **backend/tests/test_users_api.py** — +20 testes:
  - 12 testes de filtros/paginacao: setor, localizacao, ativo true/false, busca em nome+email, filtros combinados, OFFSET/LIMIT corretos, validacao 422 para setor/localizacao invalidos, page>=1, page_size<=100, busca max_length=200. Helper `_capture_list_stmts` registra os stmts e `_compiled_sql` compila com dialect Postgres (default rendia `LOWER LIKE` em vez de `ILIKE`).
  - 8 testes de protecao do ultimo admin: PATCH bloqueia democao/desativacao do ultimo, PATCH permite quando ha outros, PATCH skip check para non-admin e admin ja inativo, DELETE bloqueia, DELETE permite, DELETE skip para non-admin.
- **Total: 83 testes passando (era 38).** Suite roda em ~0.3s.

### Bloco 4 — Frontend (UX)

- **frontend/src/app/(dashboard)/layout.tsx** — Mobile navigation off-canvas. Estado `isMobileNavOpen` controla um drawer que desliza da esquerda em < 768px. Backdrop fecha ao tap, ESC fecha, route change fecha automaticamente, `body { overflow: hidden }` enquanto aberto. Hamburger button no `mobileHeader` com `aria-expanded`, `aria-controls`, `aria-label`. Antes: sidebar simplesmente sumia (`display: none`) deixando o usuario sem navegacao.
- **frontend/src/app/(dashboard)/layout.module.css** — Novas classes `.mobileHeader`, `.hamburger`, `.hamburgerBar`, `.mobileLogo`, `.backdrop`, `.sidebarOpen`. Em < 768px: sidebar `transform: translateX(-100%)` por default, `translateX(0)` quando aberta, `transition: 0.25s ease-out`, `width: min(86vw, 280px)`, `z-index` acima do backdrop.
- **frontend/src/app/(dashboard)/usuarios/page.tsx** — `fetchUsers` agora popula `listError` no catch (era silent). UI renderiza linha de erro na tabela com mensagem (do `ApiError` quando disponivel) + botao "Tentar novamente" que rechama `fetchUsers`. Antes: erro de API mostrava "Nenhum usuario encontrado", mascarando outages.
- **frontend/src/app/(dashboard)/usuarios/usuarios.module.css** — Novas classes `.errorCell`, `.errorMessage`, `.retryBtn`.
- **frontend/.env.local.example** — Reescrito com docstrings explicando cada variavel, prefixo `NEXT_PUBLIC_` (browser-safe), aviso explicito de que service role key NUNCA vai aqui.

### Bloco 5 — Documentacao
- **DECISIONS.md** — 4 ADRs novos: ADR-016 (JWKS async + TTL + algoritmo restrito), ADR-017 (exception handler global p/ CORS em 500), ADR-018 (RLS unificada em is_admin), ADR-019 (protecao do ultimo admin ativo).
- **CHANGELOG.md** — Esta entrada.

### Pegadinhas descobertas nesta sessao
- **`aws-0-` -> `aws-1-` no pooler Supabase**: o Supavisor migra tenants entre clusters sem aviso; o erro `Tenant or user not found` pode ser puramente DNS/hostname errado, nao credencial. Sempre confirmar o hostname atual no dashboard.
- **`str(stmt.compile(...))` sem dialect renderiza `ILIKE` como `LOWER(col) LIKE LOWER(...)`**: o default compiler do SQLAlchemy nao suporta ilike. Para testar SQL real, compilar com `dialect=postgresql.dialect()`.
- **Starlette `ServerErrorMiddleware` esta FORA da user middleware stack**: respostas 500 nao tratadas pulam o `CORSMiddleware`. Solucao e registrar `@app.exception_handler(Exception)` que vira a resposta dentro da stack.
- **Algoritmos JWT permitidos devem ser explicitos**: PyJWT por default tenta o algoritmo declarado no header. Se voce nao restringe, um atacante pode trocar `alg` para outra coisa que sua chave aceite por acidente. `ALLOWED_ALGORITHMS = {...}` blindado antes do `jwt.decode`.

### Pendente para Wave 2
- Deploy Railway/Vercel (intencionalmente adiado pelo Mario).
- Testes E2E com banco real (atualmente todos os testes mockam DB e httpx).

---

## [2026-04-07 — Sessao 2] — Wave 1: UI Login (Figma) + JWT ES256 + Investigacao Pooler DB

### Contexto
Continuacao da Wave 1. Foco em: polir tela de login conforme Figma, corrigir problemas de autenticacao
descobertos durante testes manuais e investigar erro de conexao com o pooler do Supabase.

### Frontend — Login UI (match Figma)

#### Arquivos criados
- **frontend/public/images/logo-3studio.svg** — Logo branco 3STUDIO extraido do Figma (asset direto)
- **frontend/public/images/login-bg.png** — Foto de fundo do painel de imagem (asset Figma)
- **frontend/src/types/global.d.ts** — Declaracao TypeScript para imports de `.css` (fix `Cannot find module`)

#### Arquivos modificados
- **frontend/src/app/layout.tsx** — Adicionado `next/font/google` para carregar Inter com suporte a font-weight variavel
- **frontend/src/app/login/page.tsx** — Reescrito para match Figma:
  - SVG inline `<clipPath>` com `clipPathUnits="objectBoundingBox"` para borda inclinada do painel de imagem
  - Painel de imagem via CSS background (nao Next.js Image)
  - Logo via `next/image`
  - Links "Nao possui conta? Registre-se" + "Esqueci minha senha"
- **frontend/src/app/login/login.module.css** — Reescrito + ajustes manuais do Mario:
  - Painel imagem: `flex: 0 1 55%`, `clip-path: url(#imagePanelClip)`
  - Logo: `align-self: center`, `margin-bottom: 4rem`
  - Titulo: `font-weight: 400`, sem italico
  - Subtitulo/labels: `font-weight: 300`
  - Button: `font-weight: 400`, `margin-top: 1rem`
  - Footer: `margin-top: 5rem`

### Backend — JWT ES256 (fix critico)

#### Problema
Supabase Auth assina JWTs com **ES256 (ECDSA)**, nao HS256 como assumido no ADR-011.
O backend verificava com HS256 → 401 Unauthorized em todos os endpoints protegidos.

#### Arquivos modificados
- **backend/app/core/jwt.py** — Reescrito completamente:
  - Detecta algoritmo do header JWT (ES256 vs HS256)
  - ES256: busca chave publica via JWKS (`/.well-known/jwks.json`) com cache in-memory + refresh on miss
  - HS256: fallback para projetos legacy usando `supabase_jwt_secret`
  - Dependencia: `pyjwt[crypto]` (pacote `cryptography` para ECDSA)
- **backend/app/api/deps.py** — `get_current_user` agora usa `verify_token()` centralizado (import de `app.core.jwt`)

### Backend — Admin user via GoTrue API

#### Problema
Usuario master criado via `INSERT INTO auth.users` + `INSERT INTO auth.identities` falhava no login (500).
GoTrue exige campos internos que raw SQL nao popula corretamente.

#### Correcao
- Deletado usuario criado via SQL
- Recriado via GoTrue Admin API (`POST /auth/v1/admin/users` com Service Role Key)
- `auth_uid` atualizado na tabela `public.usuarios`

### Investigacao — CORS / Pooler DB (nao resolvido)

#### Sintoma
`Access to fetch at 'http://localhost:8000/api/v1/users/' blocked by CORS policy`

#### Diagnostico detalhado
1. CORS middleware **funciona corretamente** — verificado via curl (preflight OPTIONS retorna headers corretos)
2. Erro real: **banco de dados inacessivel via pooler** → endpoint retorna 500 → resposta de erro nao inclui headers CORS (Starlette exception handler default)
3. `GET /health/db` confirma: `"method": "rest_api", "note": "Pooler indisponivel"`
4. Teste direto asyncpg: `InternalServerError: Tenant or user not found`
5. `DATABASE_URL` atual: `postgresql+asyncpg://postgres.rwxlpwmnkekzuurgthkr:...@aws-0-sa-east-1.pooler.supabase.com:5432/postgres`

#### Causa raiz provavel
- Senha do pooler expirada/incorreta
- Formato da URL de conexao pode ter mudado no Supabase (verificar dashboard)
- Possivel necessidade de parametro SSL

### Pendente para proxima sessao

1. **[BLOQUEANTE] Corrigir conexao pooler DB** — Verificar `DATABASE_URL` correto no dashboard Supabase, testar conexao, atualizar `.env`
2. **[BLOQUEANTE] Garantir CORS em respostas de erro** — Quando o handler lanca excecao (500), a resposta precisa incluir CORS headers. Opções: middleware de exception ou wrapper
3. **Teste E2E completo** — Login → Dashboard → Criar usuario → Listar → Editar → Desativar
4. **Testes unitarios/integracao** — Refinar os 38 testes existentes, adicionar cobertura para JWT ES256, error paths
5. **Deploy staging** — Railway (backend) + Vercel (frontend) — pendente desde Wave 0

### Pegadinhas descobertas nesta sessao

- **Supabase JWT usa ES256, NAO HS256**: O `supabase_jwt_secret` (variavel de ambiente) e para HS256, mas projetos novos assinam com ECDSA (ES256). Sempre verificar `jwt.get_unverified_header(token)["alg"]`
- **Criar auth users via GoTrue Admin API, NUNCA via raw SQL**: `POST /auth/v1/admin/users` com Service Role Key. Raw SQL em `auth.users`/`auth.identities` falta campos internos do GoTrue e causa login failure
- **Erro CORS pode mascarar erro 500**: Quando o backend retorna 500 via exception handler default do Starlette, headers CORS nao sao incluidos. O browser reporta como "CORS error" mesmo sendo erro de servidor
- **Font-weight nao funciona sem next/font**: CSS `font-weight: 300/400/700` nao tem efeito se o font nao for carregado com os weights corretos. `next/font/google` com `Inter({ subsets: ["latin"] })` carrega todos os weights automaticamente

---

## [2026-04-07] — Wave 1: Auth + Users CRUD + RBAC

### Backend

#### Auth (Componente 03)
- **app/api/deps.py** — `get_current_user` (JWT HS256 via PyJWT, audience=authenticated), `get_admin_user`, `require_role(*setors)` — 3 camadas de protecao
- **app/core/supabase_admin.py** — Supabase Auth Admin API client (create, delete, disable via Service Role Key)
- **app/db/models.py** — SQLAlchemy 2.0 model `Usuario` com 11 colunas, `SetorEnum`, `LocalizacaoEnum`
- **app/domain/schemas/user.py** — Pydantic v2: UserCreate (email regex, senha validacao, model_validator RN-009), UserUpdate (exclude_unset), UserResponse, UserListResponse

#### Users CRUD (Componente 04)
- **app/api/v1/users.py** — 6 endpoints:
  - `GET /me` — qualquer autenticado
  - `POST /` — admin: cria em Supabase Auth + DB com rollback atomico
  - `GET /` — admin: lista paginada com filtros (setor, localizacao, ativo, busca)
  - `GET /{id}` — admin ve qualquer, nao-admin ve apenas self
  - `PATCH /{id}` — admin: atualizacao parcial, RN-009 + RN-010 enforced
  - `DELETE /{id}` — admin: soft delete (ativo=false) + ban no Supabase Auth, RN-010 enforced

#### Migration e RLS (Componente 05)
- **migrations/versions/004_add_is_admin_created_by_to_usuarios.py** — `is_admin BOOLEAN NOT NULL DEFAULT false`, `created_by UUID REFERENCES usuarios(id)`
- **migrations/rls/003_policies_wave1_usuarios.sql** — 3 policies atualizadas: SELECT (self ou admin), INSERT/UPDATE (admin only), usando `is_admin = true` em vez de `setor = 'STUDIO'`

### Frontend

#### Login (Componente 03)
- **src/lib/supabase/client.ts** — Browser client via @supabase/ssr `createBrowserClient`
- **src/lib/supabase/server.ts** — Server client via `createServerClient` + cookies()
- **src/lib/supabase/middleware.ts** — Session refresh + redirect logic
- **src/middleware.ts** — Next.js middleware: atualiza sessao, redireciona /login <-> /usuarios
- **src/hooks/useInactivityTimeout.ts** — Timer 30 min (RNF-003): mouse, keyboard, touch, scroll resetam
- **src/app/login/page.tsx** — Formulario email/senha, Supabase signInWithPassword, mensagens de erro
- **src/app/login/login.module.css** — Split layout (imagem + form), dark theme, gold accent
- **src/app/globals.css** — CSS custom properties (cores, radius, font) extraidas do Figma
- **src/lib/api.ts** — `apiFetch` wrapper com ApiError, token injection, 204 handling

#### Dashboard (Componente 04)
- **src/app/(dashboard)/layout.tsx** — Sidebar fixa, user info (/me), logout, inactivity timeout 30 min
- **src/app/(dashboard)/layout.module.css** — Sidebar 280px, nav com active state, responsive
- **src/app/(dashboard)/usuarios/page.tsx** — Tabela com filtros/busca/paginacao + modais Create/Edit/Deactivate
- **src/app/(dashboard)/usuarios/usuarios.module.css** — Badges (ativo/inativo/admin), modal overlay, form fields

### Testes
- **tests/conftest.py** — Fixtures: make_user factory, admin_user, regular_user, mock_db
- **tests/test_schemas.py** — 13 testes unitarios (UserCreate validacao, UserUpdate parcial)
- **tests/test_users_api.py** — 25 testes integracao (todos endpoints, RBAC, RN-009, RN-010, rollback)
- **38 testes passing** (0 falhas)

### Banco de dados (aplicado no Supabase)
- `usuarios`: +2 colunas (`is_admin`, `created_by`)
- 3 RLS policies atualizadas para `is_admin`-based

### Dependencias adicionadas
- **Backend**: httpx (ja existia), pyjwt[crypto] (ja existia)
- **Frontend**: `@supabase/supabase-js`, `@supabase/ssr`

---

## [2026-04-07] — Wave 0: Infraestrutura completa

### Criado
- **backend/pyproject.toml** — dependencias pinadas conforme DAT Secao 1 (13 deps + 3 dev)
- **backend/app/main.py** — FastAPI com 3 health checks (`/health`, `/health/db`, `/health/r2`) e CORS
- **backend/app/core/config.py** — Pydantic Settings com 12 env vars (Supabase, R2, app)
- **backend/app/core/jwt.py** — esqueleto de verificacao JWT (HS256, audience=authenticated). Sera plugado na Wave 1
- **backend/app/core/r2.py** — cliente Cloudflare R2 (singleton + async via run_in_executor)
- **backend/app/db/session.py** — SQLAlchemy 2.0 async engine + session factory (asyncpg, pool_pre_ping=True)
- **backend/migrations/versions/001_create_enums_tables_triggers_indexes.py** — schema central: 4 enums, 6 tabelas, 2 funcoes trigger, 5 triggers, 14 indices
- **backend/migrations/versions/002_seed_configuracoes_iniciais.py** — seeds: tempo_atraso=48h, template_etiqueta=padrao
- **backend/migrations/versions/003_fix_constraints_indexes_trigger.py** — correcoes de auditoria: 3 CHECKs, trigger etiquetas, 2 indices novos, 2 indices redundantes removidos
- **backend/migrations/rls/001_enable_rls.sql** — RLS habilitado em 6 tabelas
- **backend/migrations/rls/002_policies_por_perfil.sql** — 11 policies RLS por setor (STUDIO, VENDEDOR, MOTORISTA, CLICHERIA)
- **backend/migrations/rls/apply_rls.py** — script para aplicar .sql files em ordem
- **backend/.env.example** — template com 12 env vars
- **frontend/** — boilerplate Next.js 14 (layout.tsx, page.tsx, tsconfig strict)
- **scripts/smoke_r2.py** — teste ciclo completo R2 (upload→list→download→delete)
- **scripts/keep_alive.py** — GET /health/db com log para cron
- **.github/workflows/ci.yml** — lint (ruff) + testes + deploy staging condicional
- **.github/workflows/keep-alive.yml** — cron cada 6 dias + workflow_dispatch
- **docs/cloudflare_r2_setup.md** — guia passo a passo CORS + API token
- **.claude/launch.json** — config dev servers (backend :8000, frontend :3000)

### Banco de dados (aplicado no Supabase)
- 4 enums: `setor_enum`(4), `localizacao_enum`(2), `status_prova_enum`(10), `rota_enum`(2)
- 6 tabelas: `usuarios`, `provas_digitais`, `movimentacoes`, `etiquetas`, `audit_logs`, `configuracoes_sistema`
- 6 triggers: 3 imutabilidade (audit_logs, movimentacoes, etiquetas) + 3 updated_at
- 4 CHECK constraints: `chk_vendedor_localizacao`, `chk_status_diferente`, `chk_ciclo_positivo`, `chk_ciclo_atual_positivo`
- 27 indices (0 redundantes)
- 11 RLS policies
- 2 seeds em configuracoes_sistema

### Pegadinhas descobertas
- **Supabase pooler "Tenant or user not found"**: projetos recem-criados precisam de tempo para o Supavisor provisionar o tenant. Solucao: fallback via REST API no health check
- **Supabase direct connection e IPv6-only**: maquina sem IPv6 nao conecta. Pooler (Supavisor) fornece IPv4
- **pyproject.toml build-backend**: `setuptools.backends._legacy:_Backend` nao existe. Usar `setuptools.build_meta`
- **Port 8000 ocupada**: processos python.exe de sessoes anteriores. `taskkill //F //PID <pid>`
- **tsconfig target es5**: conflita com `moduleResolution: "bundler"` do Next.js 14. Corrigido para ES2017
- **Dependencias do venv incompletas**: venv tinha apenas boto3 e psycopg2. Instaladas todas as 40 deps de uma vez

### Correcoes de auditoria (3 rodadas)
1. **C1**: `pol_movimentacoes_select` — VENDEDOR so via movimentacoes proprias, nao das suas provas. Corrigido para incluir `prova_id IN (provas do vendedor)`
2. **C2**: `etiquetas` sem trigger de imutabilidade — adicionado `trg_etiquetas_imutavel`
3. **C3**: R2 client sincrono bloqueava event loop — reescrito com singleton + `run_in_executor`
4. **M1**: indices `idx_usuarios_auth_uid` e `idx_provas_nro_requerimento` redundantes (duplicatas de UNIQUE) — removidos
5. **M2**: faltava CHECK `status_anterior != status_novo` em movimentacoes — adicionado
6. **M3**: faltava CHECK `ciclo >= 1` — adicionado em movimentacoes e provas_digitais
7. **M4**: faltava indice em `movimentacoes.created_at` para deteccao de atraso — adicionado
8. **R1**: indice composto `(prova_id, created_at DESC)` para query "ultima movimentacao" — adicionado
9. **Policy CLICHERIA**: faltava `RECEBIDA_PELA_CLICHERIA` no `pol_provas_select` — adicionado
10. **r2_download**: `Body.read()` fora do executor — movido para dentro da closure

### Pendencias para Wave 1
- Deploy Railway + Vercel (plataformas escolhidas, nao configuradas)
- Pooler do Supabase pode ja estar disponivel (re-testar)
- Diretorio `backend/tests/` vazio — criar testes na Wave 1
- Diretorios `backend/app/api/` e `backend/app/domain/` vazios — endpoints e modelos na Wave 1
