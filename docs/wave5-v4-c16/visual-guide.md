# Guia Visual — Componente 16 · Wave 5 v4.0

**Componente:** Relatorios Gerenciais com Distribuicao por Rota.
**Wave:** 5 v4.0.
**Restricao operacional do Mario:** "Preservar layout v3 exatamente — zero mudancas visuais perceptiveis ao usuario." (ADR-162)
**Status:** stub criado em 2026-05-13 (Wave 5 v4.0 / C16 Audit Fixes — AUD-W5C16-001). Mario preenche screenshots no smoke E2E.
**Padrao:** copia da estrutura validada pela Wave 3 / C12 (`docs/wave3-v4-c12/visual-guide.md`).

---

## 0. Como usar este documento

1. Cada secao descreve um aspecto visual da entrega do C16 v4.0.
2. Onde aparece `[screenshot pendente]`, anexar PNG correspondente capturado no `/relatorios` em staging (browser autenticado como `admin@3studio.com.br` ou `ops@3studio.com.br`).
3. Cada secao tem uma **prova representativa** sugerida (ID/URL/filtro) para reproduzir o cenario.
4. Aspectos NAO entregues por decisao consciente (Linha 3 Tempo Medio por Etapa, Donut completo 5 segmentos, filtro Contexto Motorista, toggle Grafico/Tabela visivel) ficam fora deste guia. Justificativa em ADR-162.

---

## 1. Card ROTA (perspectiva Geral)

### Estado entregue (v4.0)

- **Localizacao:** Linha 1 do `ReportGeral`, ultimo card da direita (`metricCardRota`).
- **Conteudo visual:** 2 dots colorid + labels textuais.
  - Dot preto (`.rotaDotMatriz`) -> label "Matriz" + contador.
  - Dot amarelo `var(--color-accent)` (`.rotaDotFilial`) -> label "Filial" + contador.
- **Semantica v4.0 (oculta visualmente):** `consolidacao_rota.matriz` agrega `MATRIZ + LAM_MATRIZ + PADRAO + null_matriz` (heuristica C12 D11.2). `consolidacao_rota.filial` agrega `FILIAL + LAM_FILIAL + DIRETA + null_filial`. Layout v3 (2 dots) preservado.

### Diferenca vs v3.0

| Aspecto | v3 | v4 entregue |
|---|---|---|
| Layout | 2 dots Padrao/Direta | 2 dots Matriz/Filial (mesma posicao) |
| Labels exibidos | "Padrao" / "Direta" | "Matriz" / "Filial" (ADR-158) |
| Cores | preto / amarelo | preto / amarelo (preservadas) |
| Cobertura semantica | 2 rotas v3 (PADRAO/DIRETA) | 6 rotas + 3 sub-buckets NULL (consolidadas em 2 dots) |
| Classes CSS | `.rotaDotPadrao` / `.rotaDotDireta` | `.rotaDotMatriz` / `.rotaDotFilial` (Audit Fix AUD-W5C16-007+008) |

### Prova representativa

- URL: `/relatorios?scope=geral`.
- Em producao (2026-05-13): `Matriz = 3` (1 MATRIZ + 2 PADRAO + 0 null_matriz) · `Filial = 14` (0 FILIAL + 0 LAM_FILIAL + 3 DIRETA + 11 null_filial).

### Screenshot

`[screenshot pendente]` — Mario captura `/relatorios?scope=geral` mostrando o card ROTA com "Matriz 3 · Filial 14".

### Fallback

Para clientes com cache antigo (sem `consolidacao_rota` no payload), o frontend faz fallback para `distribuicao_rota` legacy contando PADRAO e DIRETA. Documentado em ADR-162 §"Como aplicar" e validado em `ReportGeral.tsx:170-177`.

---

## 2. RotaFilter (filtro por categoria de rota)

### Estado entregue

- **Localizacao:** FiltersBar do `/relatorios` (filtro de rota dentro da Linha 2 dos filtros).
- **Conteudo visual:** 3 botoes ID estilo segment — **Todas** · **Matriz** · **Filial**.
- **Comportamento:** clicar em "Matriz" aplica `?rota_categoria=matriz` na URL; backend filtra via `_categoria_predicate` (rota IN {MATRIZ, LAM_MATRIZ, PADRAO} OR (rota IS NULL AND vendedor.localizacao=MATRIZ)). Idem para "Filial".

### Diferenca vs v3.0

| Aspecto | v3 | v4 entregue |
|---|---|---|
| Numero de botoes | 3 (Todas/Padrao/Direta) | 3 (Todas/Matriz/Filial) — **mesmo numero** |
| Param URL | `?rota=PADRAO` ou `?rota=DIRETA` | `?rota_categoria=matriz` ou `?rota_categoria=filial` |
| Precedencia | n/a | `rota_categoria` tem precedencia sobre `rota` exata se ambos presentes |
| Cobertura | apenas 2 rotas legacy | 6 rotas + sub-buckets NULL via heuristica C12 |

### Prova representativa

- URL inicial: `/relatorios?scope=geral`.
- Clicar em "Matriz" -> URL passa a `?scope=geral&rota_categoria=matriz`.
- Filtra para 3 provas (1 MATRIZ + 2 PADRAO + 0 NULL com vendedor MATRIZ).
- Toggle de volta clicando em "Todas".

### Screenshot

`[screenshot pendente]` — Mario captura RotaFilter no estado "Matriz" (`aria-pressed="true"`) + outro com "Filial" + outro com "Todas".

---

## 3. 4 perspectivas preservadas

### Estado entregue

`ScopeSelector` no topo da pagina mantem as 4 tabs do v3:

| Tab | Componente | Mudancas v4.0 |
|---|---|---|
| **Geral** | `ReportGeral.tsx` | Card ROTA agora consome `consolidacao_rota` (heuristica v4.0) — labels Matriz/Filial; card visualmente identico (Audit Fix AUD-007+008 renomeou classes CSS) |
| **3Studio** | `Report3Studio.tsx` | Sem mudanca visual; backend Q5 cancelamentos_top filtros aplicados v4.0 |
| **Vendedores** | `ReportVendedores.tsx` | Sem mudanca visual; backend distribuicao_localizacao preservada |
| **Clicheria** | `ReportClicheria.tsx` | Sem mudanca visual; backend `via_padrao` agora consolida v4.0 (`COM_MOTORISTA_ENTREGA_FINAL`) + legacy (`COM_MOTORISTA`); `via_direta` consolida v4.0 (`APROVADA -> RECEBIDA` direto para FILIAL/LAM_FILIAL) + legacy (`ENCAMINHADA_A_CLICHERIA`) |

### Screenshots

`[screenshot pendente]` — Mario captura 1 screenshot por tab demonstrando preservacao do layout v3. Comparar lado-a-lado com screenshots da Wave 5 v3 closeout (se disponiveis).

---

## 4. Tabela acessivel sr-only no DonutChart (D7 Opcao ii)

### Estado entregue

- **Localizacao:** card "Provas Ativas" (DonutChart) na Linha 2 do `ReportGeral`.
- **Comportamento:** tabela com `className={srOnlyBlock}` renderizada sempre, escondida visualmente via CSS (`position: absolute; width: 1px; height: 1px; overflow: hidden`). Leitor de tela (NVDA/VoiceOver) le imediatamente sem precisar interagir com o `<details>` toggle.
- **Estrutura:** `<caption>`, `<thead>` com `<th scope="col">` (Categoria/Quantidade/Percentual), `<tbody>` com 1 row por segmento.
- **Toggle visivel `<details>`:** preservado da v3 para usuario vidente que queira inspecionar valores; nao duplica leitura (a `<table>` interna do `<details>` foi marcada `aria-hidden="true"` — Audit Fix AUD-W5C16-003).

### Diferenca vs v3.0

| Aspecto | v3 | v4 entregue |
|---|---|---|
| Toggle visivel | `<details>` clicavel | Preservado |
| Conteudo do `<details>` | Lido por AT (potencialmente duplicado) | Marcado `aria-hidden="true"` |
| Tabela sr-only permanente | Nao existia | Adicionada (acessivel desde o load) |
| Conformidade WAI-ARIA | aria-hidden no `<details>` (focavel) -> violava `aria-hidden-focus` | aria-hidden movido para `<table>` interna (Audit Fix AUD-003) |

### Screenshot

`[screenshot pendente]` — DOM inspector mostrando:
- `<table class="srOnlyBlock">...</table>` (visivel no DOM, hidden visualmente)
- `<details class="chartDetails"><summary>...</summary><table aria-hidden="true">...</table></details>`

---

## 5. Snippet do CSV summary com linhas v4.0 novas

### Estado entregue

Dataset `summary` do scope `geral` expoe linhas aditivas em `scope,indicador,valor`:

```csv
﻿scope,indicador,valor
geral,periodo_from,2026-04-01T00:00:00+00:00
geral,periodo_to,2026-05-01T00:00:00+00:00
geral,periodo_total_dias,30
geral,total_provas,17
geral,tempo_medio_ciclo_horas,12.0
geral,...
geral,status_CRIADA,6
geral,status_CANCELADA,7
...
# Distribuicao legacy preservada (clientes v3 nao quebram):
geral,rota_PADRAO,2
geral,rota_DIRETA,3
geral,rota_MATRIZ,1
geral,rota_NAO_DEFINIDA,11
# Wave 5 v4.0 — distribuicao detalhada por categoria (9 categorias):
geral,rota_v4_v4_matriz,1
geral,rota_v4_legacy_padrao,2
geral,rota_v4_legacy_direta,3
geral,rota_v4_legacy_null_filial,11
# Wave 5 v4.0 — consolidacao em 2 baldes (Audit Fix AUD-011: indefinida sempre):
geral,consolidacao_rota_matriz,3
geral,consolidacao_rota_filial,14
geral,consolidacao_rota_indefinida,0
# Wave 5 v4.0 — contexto do motorista (snapshot):
# (vazio em producao atual — nenhuma prova em COM_MOTORISTA_* no momento)
```

Encoding: UTF-8 com BOM (`﻿`). Separador: virgula. Quoting: QUOTE_MINIMAL.

### Diferenca vs v3.0

- **Adicionado:** linhas `rota_v4_*` (9 categorias detalhadas), `consolidacao_rota_*` (3 baldes simetricos pos-AUD-011), `contexto_motorista_*` (3 contextos quando aplicavel).
- **Adicionado em proofs:** colunas `codigo_publico` + `contexto_motorista`.
- **Adicionado em overdue:** coluna `contexto_motorista`.
- **Preservado:** todas as linhas/colunas v3 (anti-regressao para parsers existentes).

### Screenshot

`[screenshot pendente]` — Mario abre `/api/v1/reports/export?scope=geral&dataset=summary` em Excel pt-BR e LibreOffice Calc; confirma que acentos renderizam corretamente e que as 3 linhas `consolidacao_rota_*` aparecem juntas.

---

## 6. Cenarios 8/9/10 (estados de borda)

Cobertos no `smoke-validation.md` apos Audit Fix AUD-W5C16-002. Resumo:

| Cenario | Comportamento esperado |
|---|---|
| **8 — Estado vazio** | Filtrar `?vendedor_id=<uuid-ficticio>` -> `EmptyState` renderiza sem crash; contadores zerados |
| **9 — Estado de erro** | DevTools Network throttle Offline + reload -> banner de erro / retry visivel; sem crash |
| **10 — Acesso negado** | Logar como vendedor (`mariosouza@teste.com.br`) -> middleware Wave 1 redireciona para `Restricted` antes mesmo de chegar ao backend; URL volta para `/dashboard` ou pagina restrita |

### Screenshots

`[screenshots pendentes]` — Mario captura 1 por cenario.

---

## 7. Conformidade com as 11 decisoes de design (ADR-162)

| # | Decisao aprovada (Gate 1) | Estado entregue (Gate 2) | Conformidade |
|---|---|---|:---:|
| D1 | tabs preservadas | Linha 3 (Tempo Medio por Etapa) NAO entregue como UI | ✅ adaptada |
| D2 | Donut compacto | Donut completo NAO renderizado; backend expoe via API/CSV | ✅ adaptada |
| D3 | Categoria Legacy | Backend `consolidacao_rota` via heuristica C12 D11.2; UI 2 dots | ✅ |
| D4 | 6 filtros | rota_categoria ✅; status 17 ✅; Contexto Motorista NAO exposto | ✅ adaptada |
| D5 | Atalhos + customizado | Preservado | ✅ |
| D6 | UTF-8 BOM + virgula | Preservado; colunas aditivas | ✅ |
| D7 | Ambos (toggle + tabela) | Ajustado para (ii) puro: tabela sr-only permanente | ✅ adaptada |
| D8 | Proxy via metades | Preservado | ✅ |
| D9 | Cache TTL 60s | Preservado | ✅ |
| D10 | Endpoint unico | Preservado | ✅ |
| D11 | Manter 403 | Preservado | ✅ |

11/11 decisoes implementadas conforme registro em ADR-162 (adaptacoes Gate 2 documentadas).

---

## 8. Referencias

- `docs/wave5-v4-c16/analysis.md` — Gate 1 (proposta + ASCII wireframes) + Apendice A (execucao).
- `docs/wave5-v4-c16/smoke-validation.md` — 23 cenarios para Mario rodar antes do PR (apos AUD-002 ampliar de 20 para 23).
- `docs/wave5-v4-c16/audit-report.md` — auditoria senior independente pos-execucao.
- `docs/wave5-v4-c16/fix-plan.md` — plano da sessao de correcao pos-auditoria (Wave 5 v4.0 C16 Audit Fixes).
- `docs/wave5-v4-c16/fix-validation.md` — relatorio de validacao apos correcao.
- ADR-162 em `DECISIONS.md`.

---

**Fim do `visual-guide.md`.** Stub estruturado pronto; Mario preenche screenshots durante o smoke E2E.
