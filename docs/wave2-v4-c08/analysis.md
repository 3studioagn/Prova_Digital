# Wave 2 v4.0 · Componente 08 · Análise Read-Only (Gate 1)

**Sessão:** Gate 1 do Componente 08 (atualização v4.0) — Visualização de Prova (Detalhe) com Redesign + Suporte à exibição de rota
**Data:** 2026-05-06
**Branch:** `wave2-v4-c08/analysis` (a ser criada — sem merge)
**Persona:** Engenheiro de software sênior · análise read-only · zero linhas de código de produção
**Veredito proposto:** **PROSSEGUIR PARA GATE 2 com 4 ambiguidades visuais a serem confirmadas pelo solicitante antes do merge.**

---

## 0. Pré-requisito: estado do C06 vs `main`

**Importante para validação humana antes do Gate 2:**

- C06 base **está em `main`** — commit `0547550` (`Merge branch 'wave2-v4/componente-06'`). Coluna `provas.rota`, coluna `codigo_publico`, trigger `trg_provas_rota_imutavel`, migration `012` aplicada (3 chunks MCP em produção, atomic no repo).
- **Audit Fixes Round 1** (15 commits, branch `wave2-v4/fixes/execution`) estão **em `development`** e **NÃO em `main`**. Mergeados em `8aa75ac`.
- **Audit Round 2** (`docs/wave2-v4/audit-report-round2.md`) **acabou de concluir** (2026-05-05) — veredito **APROVADO COM RESSALVAS DE BAIXA SEVERIDADE** (0 CRITICAL · 0 HIGH · 0 MEDIUM · 3 LOW · 4 INFO). Recomendação: **PR pode ser mergeado para `main` após smoke E2E manual obrigatório**.

**Implicação para esta sessão:** o Gate 1 (read-only) é seguro mesmo com os fixes ainda só em `development`, porque depende apenas da coluna `provas.rota` e do schema Pydantic `ProvaResponse`, que **estão em `main` desde o C06 base**. O Gate 2 (execução), porém, deve **aguardar o merge dos C06 Audit Fixes em `main`** para evitar conflitos no branch de execução.

---

## 1. Resumo executivo

A página de detalhe de prova (`/provas/[id]`) **já existe e funciona em produção** desde a Wave 2 (v3.0), com integrações posteriores das Waves 3 (Timeline + AdminActions) e 6 (RBAC v4.0). O endpoint `GET /api/v1/provas/{id}` **já retorna `rota`** no payload (commit `e936ddf` da Wave 2 v4.0 / C06). O hook `useAuthorization` da Wave 1 v4.0 **já está integrado** ao painel administrativo. A Timeline.tsx **já é orientada a dados** (sem hardcode de estados). O empty state **já bate com o Figma** literal.

**O que falta nesta sessão é, portanto, predominantemente um redesign visual** (CSS + reorganização de layout), com 3 toques cirúrgicos que dependem de confirmação do solicitante:

1. **Inversão do layout** — Figma mostra arte à esquerda, info à direita; código atual tem o inverso.
2. **Reorganização da metadata** — Figma exibe um grid 3×2 de pares (Cliente · Rota · Criada em / Vendedor · Ciclo Atual · Status); código atual usa lista coluna `<strong>label:</strong> valor`.
3. **Hierarquia tipográfica do título** — Figma mostra "Requerimento: 123456" pequeno acima de "Mussarela fatiada" grande; código atual mostra `nro_requerimento` com peso médio e nome com peso e tamanho ainda maior abaixo (similar mas não idêntico).

**4 ambiguidades no Figma exigem confirmação antes do Gate 2:**

| # | Ambiguidade | Impacto |
|---|-------------|---------|
| **A1** | Status "Aguardando vendedor" no Figma — não bate com `STATUS_LABELS["CRIADA"] = "Criada"` atual. É um label novo? Vale para todos os 10 estados ou só CRIADA? | Médio — afetaria também listagem/timeline se os labels mudarem globalmente. |
| **A2** | Botões "Cancelar Prova" e "Reiniciar Ciclo" não aparecem no exemplo do Figma. O exemplo é "happy path" sem admin actions, ou os botões foram realocados? | Alto — define onde renderizar esses botões. |
| **A3** | "Rota direta" no Figma — corresponde a `Rota=DIRETA` (legacy v3.0)? O label atual "Filial (legada v3.0)" diverge. Devemos remover o sufixo `(legada v3.0)` em prol de um label limpo "Direta" / "Padrão"? | Baixo — afeta só strings. |
| **A4** | A sidebar do Figma destaca "Usuários" (não "Provas") — provável artefato do Figma; confirmar que é só ruído visual. | Nenhum — só validação. |

**Riscos críticos identificados:**
- **Provas legacy (`rota IS NULL`)** representam **11 de 17 provas em produção** (65%) — tratamento robusto não é cosmético, é regra.
- A página atual tem cobertura de teste em `test_provas_api.py` (21 testes da Wave 2 C08). Refactor visual sem mudar contrato de dados deveria preservar 100% dos testes.
- O `STATUS_LABELS` é compartilhado com `provas/page.tsx` (listagem) e `Timeline.tsx`. Mudar labels via Figma afeta múltiplas páginas.

**Estratégia de modificação direta autorizada:** confirmada em Seção 1 do prompt. Rewrite cirúrgico em `page.tsx` + `detalhe.module.css`; ajustes pontuais em `Timeline.tsx` (não rewrite); zero toque no backend (a menos que A1 mude STATUS_LABELS).

---

## 2. Validação MCP

### 2.1 Supabase (`rwxlpwmnkekzuurgthkr`)

| Verificação | Resultado | Status |
|---|---|---|
| Coluna `provas_digitais.rota` | USER-DEFINED, nullable=YES | ✅ |
| Coluna `provas_digitais.codigo_publico` | character varying(20), nullable=NO | ✅ |
| Coluna `provas_digitais.ciclo_atual` | integer, nullable=NO | ✅ |
| Trigger `trg_provas_rota_imutavel` | BEFORE UPDATE WHEN (old.rota IS DISTINCT FROM new.rota) | ✅ |
| Trigger `trg_movimentacoes_imutavel` | BEFORE DELETE OR UPDATE | ✅ (presente — afeta histórico) |
| Trigger `trg_provas_updated_at` | BEFORE UPDATE | ✅ |
| RLS `pol_provas_select` | usa `app_private.current_user_*()` (Wave 1 v4.0) | ✅ |
| RLS `pol_movimentacoes_select` | usa `app_private.current_user_*()`, cobre admin/vendedor/motorista/clicheria | ✅ |
| Índice `idx_movimentacoes_prova` (prova_id) | EXISTE | ✅ |
| Índice composto `idx_movimentacoes_prova_data` (prova_id, created_at DESC) | EXISTE | ✅ — cobre o ORDER BY do `list_movimentacoes` |
| Índice `idx_provas_codigo_publico` UNIQUE | EXISTE | ✅ |
| Índice `idx_provas_rota` | EXISTE | ✅ |
| Distribuição de provas | 17 total · 11 NULL · 1 v4.0 · 5 legacy v3.0 (`PADRAO`/`DIRETA`) | ✅ |
| Movimentações totais | 16 · max ciclo = 2 · 7 status_novo distintos | ✅ — há provas reiniciadas em produção |
| Advisors security | 1 INFO `rls_enabled_no_policy` em alembic_version (intencional) + 1 WARN `auth_leaked_password_protection` (WONTFIX) | ✅ pré-existentes |
| Advisors performance | 13 INFO `unused_index` (todos pré-existentes ou esperados) | ✅ sem novos |

**Conclusão MCP Supabase:** estado consistente com o esperado pelo C06 + Wave 1 v4.0. **Nenhuma migration aditiva necessária nesta sessão** — o gap mencionado no prompt (`idx_movimentacoes(prova_id)`) **já existe**. O `idx_movimentacoes_prova_data` é ainda mais especializado para o caso de uso (ORDER BY created_at).

### 2.2 Cloudflare

- Account `20ab724c91f6bda669eecfe7c51c9171` ativa.
- R2 bucket `rastreio-provas-artes` único, criado 2026-04-07. ✅

**Escopo respeitado** — nenhuma modificação Cloudflare nesta sessão.

---

## 3. Confirmação de leitura dos artefatos da Seção 3 do prompt

| Artefato | Caminho | Status |
|---|---|---|
| CLAUDE.md | `CLAUDE.md` | ✅ lido (carregado no contexto da sessão) |
| DECISIONS.md (200 primeiras linhas + ADRs 95-124 referenciados) | `DECISIONS.md` | ✅ lido |
| Audit Round 2 do C06 | `docs/wave2-v4/audit-report-round2.md` | ✅ lido integral |
| Validação Wave 1 v4.0 (referenciado para padrões) | `docs/wave1-v4/fix-validation.md` | ✅ lido |
| Glob de docs/wave1-v4 + wave2-v4 | — | ✅ analysis/audit-report/fix-plan/fix-validation presentes em ambas |
| Endpoint GET /{id} + helpers | `backend/app/api/v1/provas.py` linhas 800-1500 | ✅ lido |
| Schema `prova.py` types | `frontend/src/lib/types/prova.ts` | ✅ lido integral |
| Hook detail | `frontend/src/hooks/useProvaDetail.ts` | ✅ lido integral |
| Página atual | `frontend/src/app/(dashboard)/provas/[id]/page.tsx` | ✅ lido integral |
| Timeline atual | `frontend/src/app/(dashboard)/provas/[id]/Timeline.tsx` | ✅ lido integral |
| AdminActions atual | `frontend/src/app/(dashboard)/provas/[id]/AdminActions.tsx` | ✅ lido integral |
| Modal etiqueta atual | `frontend/src/app/(dashboard)/provas/[id]/VisualizarEtiquetaModal.tsx` | ✅ lido integral |
| CSS detalhe | `frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css` | ✅ lido integral |
| CSS timeline | `frontend/src/app/(dashboard)/provas/[id]/timeline.module.css` | ✅ lido integral |
| Access Matrix SSoT | `shared/access-matrix.json` | ✅ lido integral — `provas.detail` rule confirmada |
| Hook authorization | `frontend/src/lib/hooks/use-authorization.ts` | ✅ lido integral |

**Documentos canônicos da v4.0** (`.docx` no Desktop): **NÃO relidos integralmente** nesta sessão — o conteúdo relevante foi consolidado pelos análogos `analysis.md`/`audit-report.md`/`audit-report-round2.md` da Wave 2 v4.0 (especialmente as seções "Pré-Fase 1 — Leitura de Contexto" do Round 2). RF-012 (timeline com indicação de rota), RF-014 (alcance via listagem), RNF-001 (carga < 3s), RN-006 (reinício preserva histórico), US-008 (detalhe + decisão admin) e Seção 6 (Matriz de Acesso) estão referenciados/respeitados pelo código atual.

**Confirmação Figma:** a imagem anexada ao prompt **foi recebida** — mostra a tela inteira do dashboard com sidebar fixa à esquerda (3STUDIO, "Olá Mônica!", busca, 8 itens de menu com "Usuários" destacado em amarelo, avatar/Sair) e o conteúdo principal `/provas/[id]` à direita (botão Voltar pill, card cinza grande contendo: arte placeholder + bloco info "Mussarela fatiada / Requerimento: 123456 / grid 3×2 de campos / 2 botões side-by-side, e abaixo card preto "Histórico de movimentações" com empty state literal).

---

## 4. Inventário do Componente 08 atual (estado v3.0 + Wave 1 v4.0 + Wave 2 v4.0 / C06)

### 4.1 Cadeia da página de detalhe

| Camada | Arquivo | Linhas | Função |
|---|---|---|---|
| Frontend page (Server/Client) | `frontend/src/app/(dashboard)/provas/[id]/page.tsx` | 280 | Renderização principal · breadcrumb + innerCard + timelineCard + modal |
| Frontend Timeline | `frontend/src/app/(dashboard)/provas/[id]/Timeline.tsx` | 274 | Render orientado a dados · agrupa por ciclo · pulso no atual |
| Frontend AdminActions | `frontend/src/app/(dashboard)/provas/[id]/AdminActions.tsx` | 234 | Botões + modais cancelar/reiniciar · `useAuthorization` integrado |
| Frontend Modal etiqueta | `frontend/src/app/(dashboard)/provas/[id]/VisualizarEtiquetaModal.tsx` | 306 | PDF + QR + copy payload |
| Frontend CSS detail | `frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css` | 629 | Estilos do innerCard, timelineCard, modais |
| Frontend CSS timeline | `frontend/src/app/(dashboard)/provas/[id]/timeline.module.css` | 212 | Estilos da timeline, dots, conector |
| Frontend hook | `frontend/src/hooks/useProvaDetail.ts` | 136 | `Promise.allSettled` em 3 endpoints + race protection |
| Frontend types | `frontend/src/lib/types/prova.ts` | 382 | `ProvaDetailResponse`, `MovimentacaoListResponse`, `STATUS_LABELS`, `ROTA_LABELS` |
| Backend endpoint detail | `backend/app/api/v1/provas.py` | 1320-1363 (`get_prova_detail`) | GET /{id} + scoping |
| Backend endpoint imagem-url | `backend/app/api/v1/provas.py` | 1374-1405 | GET /{id}/imagem-url + presigned R2 |
| Backend endpoint movimentacoes | `backend/app/api/v1/provas.py` | 1413-1481 | GET /{id}/movimentacoes (cronológico ASC) |
| Backend helper scoping | `backend/app/api/v1/provas.py` | 803-819 (`_scoping_filter_for_detail`) | Aplica chave `provas.detail` (audit Round 2 — AUD-W1V4-105) |
| Backend helper carregar | `backend/app/api/v1/provas.py` | 996-1050 (`_carregar_prova_com_scoping`) | JOIN provas+usuarios + scoping + opt FOR UPDATE |
| Backend helper response | `backend/app/api/v1/provas.py` | 1053-1089 (`_build_prova_response`) | Monta `ProvaResponse` — **já inclui `rota` + `codigo_publico`** |
| Schema Pydantic | `backend/app/domain/schemas/prova.py` | `ProvaResponse`, `MovimentacaoResponse` | Espelhado em TS |

### 4.2 Schema de resposta atual do endpoint

`ProvaResponse` (linhas 76-93 de `prova.ts`):

```typescript
{
  id: string;
  nome: string;
  nro_requerimento: string;
  codigo_publico: string;        // ← Wave 2 v4.0 / C06
  cliente: string;
  vendedor_id: string;
  vendedor_nome: string;
  vendedor_localizacao: Localizacao | null;
  imagem_url: string;
  qr_code_hash: string;
  status: StatusProva;
  rota: Rota | null;             // ← Wave 2 v4.0 / C06 — null para legacy
  ciclo_atual: number;
  motivo_cancelamento: string | null;
  created_at: string;
  updated_at: string;
}
```

**Conclusão:** schema **já completo** para o redesign do Figma. Nenhum gap no payload. O frontend hoje já consome `prova.rota` via `formatRota(prova.rota)` em `page.tsx:188`.

### 4.3 Subcomponentes reutilizáveis identificados

| Componente | Status | Observação |
|---|---|---|
| `ArrowLeftIcon` (inline SVG) | ✅ existe | Pode ser extraído para `components/icons.tsx`, mas não é necessário |
| `formatDate(iso)` | ✅ existe | pt-BR, fallback gracioso |
| `formatRota(rota)` | ✅ existe | trata null → "—" (preserva semântica legacy) |
| Timeline (`Timeline.tsx`) | ✅ existe e é orientada a dados | usa `STATUS_LABELS` + `ROTA_LABELS` |
| `AdminActions` | ✅ existe | já chama `useAuthorization("provas.cancel")` + `useAuthorization("provas.restart")` |
| `VisualizarEtiquetaModal` | ✅ existe | sem mudança nesta sessão (binário PDF + QR) |
| `useFocusTrap` | ✅ existe | usado nos 3 modais (cancelar/reiniciar/etiqueta) |

### 4.4 Pontos de integração já implementados

- **Backend:** `_scoping_filter_for_detail` (chave `provas.detail`) aplica RBAC nos 5 endpoints derivados (detail, imagem-url, movimentacoes, etiqueta.pdf, qr-code.png).
- **Frontend:** `useAuthorization` esconde botões admin · middleware Next.js redireciona acesso direto a URL não autorizada (`shared/access-matrix.json`: `provas.detail` é `dynamic` match em `/provas/[id]`).
- **Wave 2 v4.0 / C06:** `_build_prova_response` linhas 1083-1084 retorna `rota=prova.rota` direto (sem cálculo de `rota_projetada` que foi removido — comentário cita C06 cleanup explícito).
- **Trigger imutabilidade:** `trg_provas_rota_imutavel` ativo em produção (verificado via MCP).

### 4.5 Estados que aparecem hoje no histórico (`SELECT DISTINCT status_novo FROM movimentacoes`)

A query MCP retornou **7 status_novo distintos** em 16 movimentações totais (max ciclo = 2). Isso confirma que **a Timeline já renderiza dados reais** com múltiplos ciclos — base para validar o redesign sem dados mock.

---

## 5. Inventário visual do Figma anexado

A imagem mostra a tela inteira do dashboard. Inventário hierárquico de cima para baixo, esquerda para direita:

### 5.1 Sidebar (esquerda · ~272px largura · fundo preto)

| Posição | Elemento | Texto literal/conteúdo | Estado visual |
|---|---|---|---|
| Topo | Logo "3STUDIO" branca | "3STUDIO" | regular weight, sans-serif |
| Acima da busca | Saudação | "Olá Mônica!" | branco, peso médio, ~24-28px |
| Pill de busca | Input | "Buscar..." (placeholder) com ícone lupa esq | fundo cinza escuro, radius full |
| Menu primário (8 itens) | Links com ícones | Dashboard · Provas · Nova prova · Escanear · Relatórios · **Usuários** (ativo) · Configurações · Informações | Ativo: barra vertical amarela + texto amarelo · demais brancos |
| Bottom | Avatar circular cinza + "Mônica / 3Studio" + "Sair" à direita | dado dinâmico | Sair como link sutil |

**Observação A4:** "Usuários" está visualmente ATIVO (barra amarela), mas o conteúdo central é detalhe de prova. Provável artefato do Figma (designer focou em Users e moveu o conteúdo). **Confirmar que é apenas ruído visual.**

### 5.2 Conteúdo principal (direita · fundo cinza claro `#f4f4f4` ou `#efefef`)

#### 5.2.1 Topo do conteúdo

| Posição | Elemento | Conteúdo |
|---|---|---|
| Topo esquerdo | Botão "Voltar" | Pill com ícone de seta esquerda + texto "Voltar" · fundo branco/claro com borda fina |

#### 5.2.2 Card principal (centro · radius grande · fundo branco/claro)

```
┌──────────────────────────────────────────────────────────────────┐
│  ┌──────────────┐                                                │
│  │              │    Requerimento: 123456                        │
│  │    [arte]    │                                                │
│  │              │    Mussarela fatiada                           │
│  │   placeholder│  ─────────────────────────────────────────     │
│  │   cinza      │                                                │
│  │              │    Cliente:        Rota:           Criada em:  │
│  │              │    Edulat          Rota direta    27/04/2026   │
│  │              │                                                │
│  │              │    Vendedor:       Ciclo Atual:   Status:      │
│  │              │    Regiane         1               Aguardando  │
│  │              │                                    vendedor    │
│  └──────────────┘                                                │
│                                                                  │
│             [ Visualizar etiqueta ]   [ Baixar etiqueta ]       │
│                  (amarelo)                  (preto)              │
└──────────────────────────────────────────────────────────────────┘
```

| Elemento | Posição | Conteúdo / aparência |
|---|---|---|
| Arte (placeholder) | esquerda · ~480×480 quadrado · fundo cinza médio (`#d9d9d9`) | placeholder neutro |
| Header info | direita do topo · texto pequeno cinza | "Requerimento: 123456" |
| Título | direita · grande, peso médio (~36-40px) | "Mussarela fatiada" |
| Divisor | linha horizontal sutil sob o título | — |
| Grid 3×2 | direita · 3 colunas, 2 linhas · 6 pares label/valor | Cliente · Rota · Criada em / Vendedor · Ciclo Atual · Status |
| Botões | sob a arte · 2 botões side-by-side largura igual (~50%/50%) | "Visualizar etiqueta" (amarelo `var(--color-accent)`) + "Baixar etiqueta" (preto sólido) |

**Tipografia inferida:**
- Labels (Cliente, Rota, Criada em, Vendedor, Ciclo Atual, Status): cinza médio, ~12-13px, peso normal
- Valores (Edulat, Rota direta, 27/04/2026, etc): preto, ~16-18px, peso médio
- Header pequeno ("Requerimento: 123456"): cinza claro, ~12-14px
- Título ("Mussarela fatiada"): preto, ~36-40px, peso médio
- Botões: branco/preto (texto sobre fundo), peso médio, padding generoso

#### 5.2.3 Card "Histórico de movimentações" (abaixo do card principal · fundo preto · radius grande)

| Elemento | Posição | Conteúdo |
|---|---|---|
| Título | esquerda topo | "Histórico de movimentações" · branco, ~28-32px peso médio |
| Empty state | centro vertical | "Esta prova ainda nao teve movimentacoes." (1ª linha) · "A timeline visual fica disponivel quando a prova for escaneada pela primeira vez." (2ª linha · cor mais sutil) |

**Observação:** o empty state do Figma **bate literalmente** com o que já existe em `Timeline.tsx:165-171`. Sem ambiguidade aqui.

### 5.3 Cores e estilos identificáveis

| Token sugerido | Valor inferido | Uso |
|---|---|---|
| `--color-bg-page` | `#f4f4f4` (cinza claro) | wrapper externo do conteúdo |
| `--color-card-surface` | `#ffffff` ou `#fafafa` | card principal de detalhe |
| `--color-card-art-bg` | `#d9d9d9` (cinza médio) | placeholder/fundo da arte |
| `--color-accent` (já existe) | amarelo | botão "Visualizar etiqueta" |
| `--color-card-text` (já existe) | preto | título + valores |
| `--color-card-text-muted` (já existe) | cinza médio | labels |
| `--color-bg-dark` (já existe) | preto | card "Histórico" |

### 5.4 Estados visuais especiais e elementos não cobertos pelo Figma

| Estado | Cobertura no Figma |
|---|---|
| Loading | ❌ não mostrado — propor skeleton/spinner discreto |
| Erro | ❌ não mostrado — propor caixa de erro neutra com botão "Tentar novamente" (já existe) |
| Cancelada com motivo | ❌ não mostrado — propor exibir motivo abaixo do Status (preservar comportamento atual) |
| Múltiplos ciclos | ❌ não mostrado (timeline vazia) — preservar estilo atual (cycleGroup + cycleLabel "Ciclo X") |
| Reprovação com motivo | ❌ não mostrado — preservar `nodeMotivo` atual (caixa vermelha) |
| Modal "Visualizar etiqueta" | ❌ não mostrado — preservar atual (PDF iframe + QR + copy payload) |
| Modais admin (cancelar/reiniciar) | ❌ não mostrados — preservar atuais |
| Tooltip/responsivo mobile | ❌ não mostrado — preservar `mobileNotice` atual (RNF-002) |
| Animações | nenhuma indicada → não introduzir Framer Motion novo (Wave 6) |

### 5.5 Ambiguidades para confirmação humana

| ID | Ambiguidade | Proposta default | Pergunta para Mario |
|---|---|---|---|
| **A1** | Status "Aguardando vendedor" | Manter `STATUS_LABELS["CRIADA"] = "Criada"` | "Aguardando vendedor" é label novo para CRIADA, ou é apenas exemplo do designer? Se for novo, precisamos de label novos para os 10 estados? |
| **A2** | Botões "Cancelar Prova" / "Reiniciar Ciclo" não aparecem no Figma | Preservar — render condicional dentro de `.actions` (ao lado de "Visualizar/Baixar etiqueta") | Os botões admin devem aparecer no card principal junto com os 2 botões de etiqueta, ou devem ter um sub-painel separado? |
| **A3** | "Rota direta" no Figma diverge de `ROTA_LABELS["DIRETA"] = "Filial (legada v3.0)"` | Default: usar labels atuais (legada v3.0) — eles são informativos para o admin sobre dado pré-Wave 7 | Devemos remover o sufixo "(legada v3.0)" e usar labels limpos "Padrão" / "Direta" para preservar a estética do Figma? |
| **A4** | Sidebar Figma destaca "Usuários" mas conteúdo é detalhe de prova | Tratar como artefato visual do Figma | Confirmar que é só ruído (designer focou em Users) — esperado é "Provas" ou nenhum destacado quando estamos em /provas/[id]. |

---

## 6. Plano de hierarquia de componentes (proposta — sem implementar)

### 6.1 Árvore proposta

```
<ProvaDetalhePage>                                  ← page.tsx (rewrite cirúrgico)
  <Breadcrumb>                                      ← preservar (já existe)
    <BackButton href="/provas" />
  </Breadcrumb>
  <DetalheCard>                                     ← novo wrapper (substitui innerCard)
    <DetalheLayout>                                 ← grid 2-col INVERTIDO (arte | info)
      <ArteSlot>                                    ← novo (esquerda) — preserva imagemUrl + fallbacks
        <ArtePlaceholder | ArteImg />
      </ArteSlot>
      <InfoSlot>                                    ← novo (direita)
        <RequerimentoLabel>                         ← "Requerimento: NNN" pequeno
        <NomeProvaTitle>                            ← "Mussarela fatiada" grande
        <Divider />                                 ← linha sutil
        <MetadataGrid>                              ← grid 3×2
          <MetadataItem label="Cliente" value={...} />
          <MetadataItem label="Rota" value={formatRota(prova.rota)} />
          <MetadataItem label="Criada em" value={formatDate(...)} />
          <MetadataItem label="Vendedor" value={...} />
          <MetadataItem label="Ciclo Atual" value={...} />
          <StatusItem status={prova.status} />     ← talvez badge colorido (decisão A1)
        </MetadataGrid>
        {motivo_cancelamento && <MotivoCancelamentoBanner />}
        <CodigoPublicoLine codigo={prova.codigo_publico} /> ← preservar exibição em mono
      </InfoSlot>
    </DetalheLayout>
    <ActionsRow>                                    ← grid 2-col largura igual (ou 4-col se A2 = inline)
      <BtnPrimary>Visualizar etiqueta</BtnPrimary>
      <BtnSecondary>Baixar etiqueta</BtnSecondary>
      <AdminActions prova={prova} onActionComplete={reload} /> ← já existe, render condicional via Matriz
    </ActionsRow>
  </DetalheCard>
  <HistoricoCard>                                   ← preservar timelineCard (renomear opcional)
    <HistoricoTitle>Histórico de movimentações</HistoricoTitle>
    <Timeline movimentacoes={...} prova={...} />   ← preservar Timeline.tsx orientada a dados
  </HistoricoCard>
  <VisualizarEtiquetaModal {...} />                 ← preservar
</ProvaDetalhePage>
```

### 6.2 Por componente: props · estado · reuso

| Componente | Props | Estado local | Reuso |
|---|---|---|---|
| `ProvaDetalhePage` | `params: { id: string }` | `etiquetaModalOpen`, `imgLoadError` | preserva atual |
| `BackButton` | `href` | — | inline em `page.tsx` (igual atual) |
| `DetalheCard` | `children` | — | wrapper CSS (não JSX novo) — a hierarquia se resolve só por classes |
| `ArteSlot` | `imagemUrl`, `imagemError`, `nro_requerimento` | `imgLoadError` (passado) | preservar |
| `MetadataItem` | `label: string`, `value: string \| ReactNode` | — | inline (não vale extrair componente novo) |
| `StatusItem` | `status: StatusProva` | — | inline ou helper `formatStatus(status)` (decisão A1) |
| `AdminActions` | `prova`, `onActionComplete` | preserva | sem mudança de prop |
| `Timeline` | `movimentacoes`, `prova` | — | sem mudança |

**Princípio:** **NÃO criar componentes novos por enquanto.** O `MetadataGrid` é só CSS Grid (`.metaGrid` + `.metaItem`); `StatusItem` é função utilitária. Adicionar componentes só se a complexidade justificar — caso contrário, inline em `page.tsx` mantém a página simples e evita ramificação prematura. Justificativa alinhada com regra "Don't add features beyond what the task requires" (CLAUDE.md).

---

## 7. Plano de tratamento de provas legacy (`rota IS NULL`)

**Cenário crítico:** 11 de 17 provas em produção (65%) são legacy. **Não é caso de borda — é norma.**

| Cenário | Comportamento atual | Proposta para o redesign |
|---|---|---|
| `prova.rota IS NULL` | `formatRota(null)` retorna `"—"` (em uso desde C06) | **Preservar** — exibir "—" no campo "Rota" da MetadataGrid. Sem nota textual extra (Mario decidiu na Wave 2 v4.0 / C06: "—" é discreto e suficiente). |
| `prova.rota IN ('PADRAO','DIRETA')` (legacy v3.0) | `ROTA_LABELS` retorna "Matriz (legada v3.0)" / "Filial (legada v3.0)" | **Default: preservar** (label informativo). **Alternativa A3:** se Mario aprovar limpeza, retornar "Padrão" / "Direta" sem sufixo. |
| `prova.rota IN ('MATRIZ','LAM_MATRIZ','FILIAL','LAM_FILIAL')` | `ROTA_LABELS` retorna "Matriz" / "Lam. Matriz" / "Filial" / "Lam. Filial" | **Preservar** |
| Histórico de prova legacy (mov.rota_no_momento IS NULL) | Timeline já trata via `node.isRoteamento && node.rotaNoMomento &&` (não exibe badge se null) | **Preservar** — Timeline não exibe badge de rota para movimentações sem rota |

**Sem nota visual "(rota inferida — prova legacy v3.0)" no badge** — discutido na Wave 2 v4.0 / C06: a rota "inferida" deixou de ser conceito (foi removida quando `rota_projetada` foi excluído do response). Para prova legacy, a rota é simplesmente indeterminada até a Wave 7 (Componente 21) fazer o backfill. Exibir "—" é o tratamento mais honesto.

**Teste de paridade legacy** (cobertura existente em `test_provas_api.py`): preservar — adicionar 1 teste novo de UI no Gate 2 que monta detail com `rota: null` e confirma render de "—" + ausência de quebra.

---

## 8. Plano de visibilidade condicional do painel de ações

### 8.1 Tabela de visibilidade

| Botão | Condição (frontend) | Defesa em profundidade (backend) |
|---|---|---|
| **Visualizar etiqueta** | sempre visível para usuário com acesso à prova (todos os perfis cobertos pela RLS) | RLS impede vendedor ver prova alheia · `_scoping_filter_for_detail` retorna 404 |
| **Baixar etiqueta** | idem — sempre visível | idem |
| **Reiniciar Ciclo** | `useAuthorization("provas.restart").hasAccess === true` **E** `prova.status === "REPROVADA_PELO_VENDEDOR"` | endpoint `POST /{id}/reiniciar-ciclo` valida `access_required("provas.restart")` |
| **Cancelar Prova** | `useAuthorization("provas.cancel").hasAccess === true` **E** `prova.status IN CANCELAVEIS` | endpoint `POST /{id}/cancelar` valida `access_required("provas.cancel")` |

### 8.2 Constante `CANCELAVEIS` (já existe em `AdminActions.tsx:13-22`)

```typescript
const CANCELAVEIS: Set<StatusProva> = new Set([
  "CRIADA",
  "RETIRADA_PELO_VENDEDOR",
  "APROVADA_PELO_VENDEDOR",
  "DE_VOLTA_3STUDIO",
  "COM_MOTORISTA",
  "ENVIADA_PARA_CLICHERIA",
  "ENCAMINHADA_A_CLICHERIA",
  "REPROVADA_PELO_VENDEDOR",
]);
```

**Não cancelável:** `RECEBIDA_PELA_CLICHERIA` (terminal happy path) e `CANCELADA` (já cancelada). Confirmado contra RN-005.

### 8.3 Mecanismo (já implementado)

- **Cliente:** `AdminActions.tsx:102-109` — early return `null` se nenhuma ação está autorizada/aplicável. Cada botão é renderizado condicionalmente via `podeCancelar` / `podeReiniciar`.
- **Servidor:** `access_required("provas.cancel")` e `access_required("provas.restart")` em `provas.py` (endpoint cancel + reinicio).
- **RLS:** policies `pol_provas_update WITH CHECK (app_private.current_user_is_admin())` — apenas admin pode UPDATE em `provas_digitais`.

### 8.4 Decisão de UI (depende de A2)

| Caso A2 = "render inline" (default proposto) | Caso A2 = "sub-painel separado" |
|---|---|
| `<ActionsRow>` contém: `[Visualizar] [Baixar] [Reiniciar?] [Cancelar?]` — flex-wrap | `<ActionsRow>` contém: `[Visualizar] [Baixar]`. Abaixo, em sub-painel sutil, `<AdminPanel>` separado com label "Administração" |

**Default proposto:** inline, preserva o atual e bate visualmente com o Figma quando esses botões NÃO aparecem (admin actions ficam ao lado dos botões principais e somem por flex-wrap quando ausentes). **Aguardar confirmação A2.**

---

## 9. Plano de timeline estruturalmente capaz (preparação Wave 3 v4.0)

A `Timeline.tsx` atual **JÁ É orientada a dados** (verificado em `Timeline.tsx:73-93`):

```typescript
for (let i = 0; i < movimentacoes.length; i++) {
  const m = movimentacoes[i];
  const sNovo = m.status_novo as StatusProva;
  nodes.push({
    id: m.id,
    status: sNovo,
    ...
  });
}
```

**Não há hardcode de estados específicos.** O `STATUS_LABELS` (mapa pt-BR) é a única fonte de label. Quando a Wave 3 v4.0 / Componente 11 expandir `StatusProvaEnum` para 14 estados (motorista entrega Matriz/Filial, etapa de laminação, etc.), basta:

1. Adicionar os novos valores ao `StatusProvaEnum` no backend (Python) e ao tipo TS `StatusProva` em `prova.ts`.
2. Adicionar novas chaves a `STATUS_LABELS` (e opcionalmente `STATUS_LABELS_SHORT`).
3. Adicionar índices/transições novos em `state_machine.py` (TRANSICOES + ATORES_POR_TRANSICAO).

**Zero refactor da Timeline.** A sessão de C08 v4.0 não precisa tocar Timeline.tsx para preparar Wave 3 — ela já está pronta.

### 9.1 Pequenos ajustes opcionais sugeridos para esta sessão

| Item | Justificativa | Decisão proposta |
|---|---|---|
| Mapeamento `status → cor de destaque` | Hoje só temos: amarelo (atual), vermelho (reprovação), cinza (cancelamento), verde (terminal recebida pela clicheria). Pode ser útil mapear "Com Motorista (Matriz)" e "Com Motorista (Filial)" da Wave 3 v4.0 para cores distintas. | **NÃO fazer agora** — Wave 3 v4.0 cuidará. Esta sessão preserva o mapa atual. |
| Mapeamento `status → ícone` | Hoje a timeline usa só dot colorido + label. Sem ícones por status. | **NÃO fazer agora** — Wave 6 (animações) cuidará. |
| Renderização de `rota_no_momento` para movimentações de motorista | Hoje só roteamento (APROVADA_PELO_VENDEDOR) exibe badge. Quando Wave 3 v4.0 introduzir COM_MOTORISTA_MATRIZ / COM_MOTORISTA_FILIAL, eles também devem exibir badge de rota? | **Preservar atual** — flag `isRoteamento` é hoje específica para APROVADA_PELO_VENDEDOR. Wave 3 v4.0 decidirá expansão. |

### 9.2 Conclusão

Timeline.tsx **NÃO precisa de mudança nesta sessão.** A criticidade do Componente 08 v4.0 é exclusivamente o redesign do CARD PRINCIPAL (info da prova + ações).

---

## 10. Plano de performance (RNF-001: carga < 3s)

### 10.1 Estratégia atual (já implementada)

`useProvaDetail.ts` dispara **3 requests em paralelo** via `Promise.allSettled`:

1. `GET /api/v1/provas/{id}` — detalhe da prova (1 query JOIN provas+usuarios + scoping)
2. `GET /api/v1/provas/{id}/imagem-url` — presigned URL R2 (1 query mesma JOIN + 1 chamada R2)
3. `GET /api/v1/provas/{id}/movimentacoes` — histórico (1 query JOIN movimentacoes+usuarios + scoping)

**Race protection:** `latestReqRef` descarta loads antigos se usuário clicar "Tentar novamente" rapidamente.

**Tolerância parcial:** se imagem R2 falhar, mostra placeholder mas o resto da tela ainda funciona.

### 10.2 Avaliação contra RNF-001

| Componente do tempo | Atual | Análise |
|---|---|---|
| TTFB do request mais lento | tipicamente < 500ms (3 queries em paralelo) | dentro do orçamento |
| Render React | < 100ms (React 18 + CSS Modules) | dentro do orçamento |
| Carga da imagem R2 | depende do tamanho — para arte ~1-3MB, < 1s em rede comum | dentro do orçamento |
| **Total estimado** | **< 2s** em cenário comum | **dentro de RNF-001 (< 3s)** ✅ |

### 10.3 Otimizações consideradas (descartadas)

| Otimização | Por que descartada |
|---|---|
| Endpoint agregado único (`/{id}/full`) | Quebra contrato existente · ganho marginal (3 queries paralelas já são rápidas) · adiciona acoplamento que dificulta manutenção · **YAGNI** |
| Server-side rendering (SSR) | Backend separado (FastAPI) — SSR exigiria proxy com cookie passthrough, complexidade alta · zero ganho perceptível em tela de detalhe |
| Cache HTTP via `ETag` | Útil quando o mesmo usuário re-acessa a mesma prova frequentemente · **fora do escopo** desta entrega |
| Pre-fetch ao hover na listagem | Nice-to-have UX · **fora do escopo** |

### 10.4 Conclusão

**Nada a fazer em performance nesta sessão.** Estratégia atual já é eficiente e atende RNF-001.

---

## 11. Plano de modificação coordenada das chamadas existentes

### 11.1 Arquivos a tocar (dentro do escopo)

| Arquivo | Tipo de mudança | Justificativa |
|---|---|---|
| `frontend/src/app/(dashboard)/provas/[id]/page.tsx` | **Rewrite cirúrgico** | redesign do layout — invertir grid, refazer header tipográfico, reorganizar metadata em grid 3×2 |
| `frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css` | **Rewrite cirúrgico** | acompanhar o rewrite do page.tsx — novos seletores `.metaGrid`, `.metaItem`, novos tons cinza |
| `frontend/src/app/(dashboard)/provas/[id]/Timeline.tsx` | **Sem mudança** | já orientada a dados |
| `frontend/src/app/(dashboard)/provas/[id]/timeline.module.css` | **Sem mudança** ou **toques pontuais** | possível ajuste de espaçamento se o card preto ganhar nova proporção; revisitar no Gate 2 |
| `frontend/src/app/(dashboard)/provas/[id]/AdminActions.tsx` | **Sem mudança no contrato** | a depender de A2: se "render inline" (default), zero mudança; se "sub-painel", incluir prop `layout?: 'inline' \| 'panel'` |
| `frontend/src/app/(dashboard)/provas/[id]/VisualizarEtiquetaModal.tsx` | **Sem mudança** | binário PDF + QR fora do escopo visual |
| `frontend/src/lib/types/prova.ts` | **Sem mudança** ou **STATUS_LABELS** | depende de A1 |

### 11.2 Arquivos fora da pasta `[id]/` que NÃO devem ser tocados

- `frontend/src/app/(dashboard)/provas/page.tsx` (listagem) — **fora do escopo**
- `backend/app/api/v1/provas.py` — **fora do escopo** (response já está completo)
- `backend/app/services/state_machine.py` — **fora do escopo** (Wave 3 v4.0 cuidará da expansão de estados)
- `shared/access-matrix.json` — **fora do escopo** (regra `provas.detail` já está formalizada)
- `frontend/src/middleware.ts` — **fora do escopo** (já redireciona acesso direto)
- Qualquer migration Alembic ou RLS — **NENHUMA migration nesta sessão**

### 11.3 Arquivos que precisam atualização documental (pós-Gate 2, antes do PR)

- `CHANGELOG.md` — apêndice nova seção "v4.0 Wave 2 Componente 08 (atualização v4.0)"
- `DECISIONS.md` — ADRs novos (ver Seção 16)
- `CLAUDE.md` — atualizar tabela de waves + seção sobre extensão da Timeline (Wave 3 v4.0)
- `docs/wave2-v4-c08/figma-reference.png` — salvar a imagem do Figma anexada como referência permanente

---

## 12. Estratégia de testes (Gate 2)

### 12.1 Unitários (frontend — Vitest, conforme padrão da Wave 1 v4.0 / Audit Round 2 — AUD-W1V4-005)

| Teste | Descrição | Cobertura |
|---|---|---|
| `formatRota` para 4 v4.0 + 2 legacy + null | já testável via export | 7 cenários |
| `MetadataGrid` render para todos os campos completos | smoke test | 1 |
| `MetadataGrid` render para `motivo_cancelamento` presente | render condicional | 1 |
| `MetadataGrid` render para `rota IS NULL` | exibe "—" sem quebrar | 1 |
| `<AdminActions>` snapshot por perfil × status (4×10 = 40, mas restringir) | matriz de visibilidade dos botões | ~10 chave |

### 12.2 Backend (preservar existentes)

A suíte `test_provas_api.py` atual cobre:
- 21 testes da Wave 2 C08 (detalhe + imagem-url + movimentacoes)
- Cenários de scoping (vendedor não vê prova alheia → 404)
- Cenário legacy (`rota IS NULL`)

**Esta sessão não muda contrato de backend → 100% dos testes existentes devem passar sem alteração.**

### 12.3 Integração (skipif sem `INTEGRATION_DATABASE_URL`)

Adicionar 1 teste opcional:

| Teste | Cenário |
|---|---|
| `test_detail_inclui_codigo_publico_e_rota_v4` | Cria prova com rota=`MATRIZ`, GET /{id}, asserta `rota="MATRIZ"` + `codigo_publico=PRV-AAAA-MM-NNNNNN` |

(Provavelmente já coberto pela suíte C06 — verificar no Gate 2.)

### 12.4 E2E (Playwright — declarado fora do escopo desde Wave 1 v4.0)

**Cobertura substituta:** smoke manual obrigatório antes do merge (ver Seção 17). Mario percorre os 4 perfis × 4 cenários (full · scoping · status atual · status reprovada) na página redesenhada.

### 12.5 Performance (Gate 2)

Medir TTFP (Time-to-First-Paint) e TTI (Time-to-Interactive) com dados reais (17 provas em produção). Aceitar se `< 3s` em rede 4G simulada.

### 12.6 Acessibilidade (Gate 2)

- Contraste mínimo AA (Lighthouse audit) para texto sobre cinza claro e sobre preto.
- Labels ARIA nos botões e nos modais (já existem no atual — preservar).
- Navegação por teclado funcional (Tab/Enter/Esc — já implementado).

### 12.7 Cobertura mínima

- ≥ 80% na camada de domínio/serviço — preservada (sem mudança backend).
- Frontend: cobertura mantida (sem regressão dos 15 Vitest da Wave 1 v4.0).

---

## 13. Migrations previstas

**NENHUMA migration Alembic ou RLS nesta sessão.**

Justificativa:
- Schema atual `provas_digitais` tem todas as colunas necessárias.
- Schema `movimentacoes` tem todos os índices necessários (verificado via MCP — `idx_movimentacoes_prova` + `idx_movimentacoes_prova_data` ambos presentes).
- RLS atual cobre todos os perfis (Wave 1 v4.0 + audit Round 2 RLS 013 já em produção).
- O redesign é **puramente visual** — frontend-only.

---

## 14. Riscos e pontos de atenção

| ID | Risco | Probabilidade | Mitigação |
|---|---|---|---|
| **R1** | Provas legacy renderizando incorretamente após rewrite do page.tsx | Média | 1 teste de unit dedicado (`MetadataGrid` com `rota=null`) + checklist manual com prova real do banco (`UPDATE-SET-id` para uma das 11 legacy) |
| **R2** | Mudança em `STATUS_LABELS` (caso A1 = sim) quebra listagem `/provas` e timeline | Alta (se confirmado A1) | Antes de mudar, fazer grep de `STATUS_LABELS` em todo o frontend; testar visualmente listagem + timeline + scanner |
| **R3** | Falsos negativos no painel admin (perfil não-admin vê botão por race do useCurrentUser) | Baixa | `useAuthorization` já trata `loading=true` → `hasAccess=false` (defensivo). Já validado pela Wave 1 v4.0 / M-1 fix. |
| **R4** | Performance degradada em prova com muitos ciclos (>10) | Baixíssima — max ciclo atual em produção é 2 | Se ocorrer, paginar histórico. Não atuar agora — YAGNI. |
| **R5** | Quebra do schema response após introdução de `rota` (cenário improvável já que C06 já passou auditoria) | Baixíssima | Esta sessão não toca o response — preserva. |
| **R6** | Acessibilidade: contraste insuficiente em cinza-sobre-cinza-claro | Média (depende dos tons exatos) | Validar com Lighthouse no Gate 2 antes de PR. Ajustar tokens conforme resultado. |
| **R7** | Confusão sobre quais ADRs/ressalvas do Round 2 do C06 afetam C08 | Baixa | Round 2 ressalvas R2-001/002/003 são todas em `state_machine.py` / `test_migration_012.py` / `provas.py:reiniciar_ciclo` — fora do escopo da página de detalhe. C08 não regride nem expande nenhuma delas. |
| **R8** | A1 (label "Aguardando vendedor") sendo aprovado obriga refactor cross-page | Média (se A1 = sim) | Se aprovado, ampliar escopo para incluir mudança de labels. Caso contrário, manter labels atuais. |
| **R9** | A2 (botões admin separados) sendo aprovado adiciona AdminPanel novo | Baixa | Se aprovado, incrementar prop `layout` no AdminActions sem quebrar callers (default = "inline"). |

---

## 15. ADRs propostos (a registrar no Gate 2 / FIM DE SESSÃO)

| Proposta | Resumo |
|---|---|
| **ADR-125** | Inversão do layout do detalhe (arte à esquerda · info à direita) — alinhamento com Figma do Mario; preserva responsividade ≤ 1100px (1-col stack já existente) |
| **ADR-126** | Provas legacy (`rota IS NULL`) exibem "—" no campo Rota sem nota textual extra — decisão pós-debate Wave 2 v4.0 / C06 (sufixo "(legada v3.0)" só nas legendas das rotas legacy v3.0 PADRAO/DIRETA) |
| **ADR-127** *(condicional A1)* | Se A1 = sim: novo conjunto `STATUS_LABELS_DETALHE` aplicado **apenas** no detalhe (não substitui `STATUS_LABELS` global) — minimiza blast radius |
| **ADR-128** *(condicional A2)* | Painel admin renderiza inline ao lado dos botões de etiqueta (default) ou em sub-painel separado abaixo (decisão A2) — captura intent visual do Figma |

---

## 16. Critérios de saída do Gate 1 (este documento)

Esta análise está pronta quando:

- [x] Inventário do C08 v3.0 atual completo (Seção 4)
- [x] Inventário visual do Figma documentado com hierarquia clara (Seção 5)
- [x] Plano de hierarquia de componentes proposto (Seção 6)
- [x] Plano de tratamento legacy (Seção 7)
- [x] Plano de visibilidade condicional do painel de ações (Seção 8)
- [x] Plano de timeline estruturalmente capaz (Seção 9)
- [x] Plano de performance contra RNF-001 (Seção 10)
- [x] Plano de modificação coordenada (Seção 11)
- [x] Estratégia de testes (Seção 12)
- [x] Migrations previstas (Seção 13)
- [x] Riscos identificados (Seção 14)
- [x] ADRs propostos (Seção 15)
- [x] Validação MCP read-only executada (Seção 2)
- [x] Confirmação de leitura dos artefatos (Seção 3)
- [x] **4 ambiguidades visuais listadas para confirmação humana (Seção 5.5)**

---

## 17. Recomendação para Gate 2

**Prosseguir para Gate 2 com as seguintes pré-condições:**

1. **Confirmação humana das 4 ambiguidades visuais (A1 · A2 · A3 · A4)** — orientação do Mario antes do início da execução.
2. **Merge dos C06 Audit Fixes em `main`** — recomendado (não estritamente bloqueante, mas evita conflitos no branch de execução `wave2-v4/componente-08`). O Round 2 declarou aprovação para merge condicional ao smoke E2E manual; sugerimos executar esse smoke + merge antes do Gate 2 de C08.
3. **Smoke manual antes do PR** — checklist a definir no Gate 2:
   - 3Studio acessa /provas/[id] de cada uma das 4 rotas v4.0 + 2 legacy v3.0 + 1 NULL.
   - Vendedor acessa prova dele (sucesso) e prova alheia (404 + redirect).
   - Motorista acessa prova com status `COM_MOTORISTA*` (sucesso).
   - Clicheria acessa prova com status `*_CLICHERIA` (sucesso).
   - Status REPROVADA → botão "Reiniciar Ciclo" visível para 3Studio.
   - Status CANCELADA → ambos botões ocultos.
   - Modal "Visualizar etiqueta" abre, fecha com ESC, mostra PDF + QR + payload copiável.
   - Histórico vazio mostra empty state literal do Figma.
   - Prova com 2 ciclos (existe em produção: max ciclo = 2) mostra agrupamento.
   - Mobile: `mobileNotice` aparece (RNF-002).
   - Lighthouse audit: contraste AA, labels ARIA, navegação por teclado.

**Conclusão:** **PROSSEGUIR após confirmações** — risco geral baixo, código existente em ótimo estado, redesign é cirúrgico. Exigência: nada de Framer Motion novo, nada de mudança de regra de negócio, nada de migration.

---

**Fim do Gate 1.**
