# Relatório de Auditoria · Wave 2 v4.0 · Componente 08 (atualização v4.0)

**Auditor:** Claude (Opus 4.7 1M) · sessão de auditoria sênior independente
**Data:** 2026-05-06
**Branch auditada:** `wave2-v4/componente-08`
**Tip da branch (HEAD auditado):** `eb9e46c` (`docs(wave2-v4/c08): registrar 3 iteracoes pos-Figma no CHANGELOG`)
**Branch desta auditoria (read-only, sem merge):** `wave2-v4-c08/audit`
**Veredito final:** **REPROVADO E REFAZER (CONDICIONAL)** — bloqueado por 1 CRITICAL processual + 3 ALTOS de processo/cobertura. Implementação funcional e visualmente coerente com o `analysis.md`, mas viola requisitos de rastreabilidade explícitos (Seção 6.5 do prompt de execução) e descumpre cobertura de testes prometida no Gate 1. As correções são pequenas mas obrigatórias antes do PR para `main`.

---

## Sumário Executivo

A entrega do C08 v4.0 reformula a página `/provas/[id]` em conformidade com 4 ADRs (125-128) e respeita o escopo declarado: frontend-only, zero touch em backend/RLS/migrations, Timeline.tsx e AdminActions.tsx preservadas (já orientadas a dados desde Wave 3 e Wave 1 v4.0 respectivamente). Os 4 pontos visuais decididos pelo Mario (A1-A4) estão materializados no código com decisões registradas em ADRs. Backend response (`ProvaResponse`) e índices (`idx_movimentacoes_prova`, `idx_movimentacoes_prova_data`) já estavam prontos desde C06 — nada novo precisaria ser criado.

Apesar dessa qualidade de execução, a auditoria identificou **1 achado CRITICAL** (figma-reference NÃO preservado em `docs/wave2-v4-c08/figma-reference.png` — viola Seção 6.5 explícita do prompt de execução e Section 11.3 da própria `analysis.md`), **3 achados ALTOS** (analysis.md em branch separada quebra rastreabilidade e link no CHANGELOG, ZERO testes Vitest novos contradiz padrão estabelecido em Wave 1 v4.0 Audit Round 2 / AUD-W1V4-005, token de cor da arte ausente deixa placeholder quase invisível), **4 MÉDIOS**, **5 BAIXOS** e **3 INFOs**.

**Achados que afetam a Wave 3:** nenhum bloqueante. Timeline.tsx é orientada a dados; expansão para 14 estados exigirá apenas adicionar entradas em `STATUS_LABELS` e novas transições em `state_machine.py` — caminho documentado no CLAUDE.md e validado nesta auditoria. Não há hardcode de estado específico no componente.

**Resultado da fidelidade visual:** **NÃO AVALIÁVEL INTEGRALMENTE** — a imagem-referência do Figma não foi preservada no repositório, contrariando a Seção 6.5 do prompt de execução. A auditoria confiou exclusivamente na descrição textual da Seção 5 da `analysis.md` (preservada no branch `wave2-v4-c08/analysis`) e na verbalização das decisões A1-A4 do Mario nos ADRs 125-128. Comparação elemento-por-elemento contra o pixel não foi possível.

**Achados CRITICAL nominais:**
- AUD-W2C08-001 — Imagem do Figma não preservada em `docs/wave2-v4-c08/figma-reference.png`.

**Achados ALTOS nominais:**
- AUD-W2C08-002 — `analysis.md` ausente da branch da entrega (link quebrado no CHANGELOG).
- AUD-W2C08-003 — Zero testes Vitest novos no Gate 2 (analysis Section 12.1 prometeu 5+).
- AUD-W2C08-004 — `.artSlot` background usa token genérico `--color-card-surface=#e4e4e4` (quase invisível contra `--color-card-bg=#eaeaea`); token `--color-card-art-bg=#d9d9d9` proposto no analysis Section 5.3 nunca foi criado.

**Recomendação:** abrir sessão de correção curta (estimativa ≤ 1h) cobrindo os 4 achados acima + os 4 MÉDIOS antes do PR para `main`. Os 5 BAIXOS podem ser pegos numa segunda passada ou viram backlog técnico.

---

## Fase 1 — Verificação de Completude

### Confirmação de leitura dos artefatos da Seção 2 do prompt

| Artefato | Caminho real | Status |
|---|---|---|
| CLAUDE.md | `CLAUDE.md` | ✅ lido (carregado no contexto da sessão; tabela de Waves cobre C08 atual) |
| DECISIONS.md | `DECISIONS.md` (ADRs 125-128 nas linhas 5063-5258) | ✅ lido — todos os 4 ADRs presentes e bem fundamentados |
| CHANGELOG.md | `CHANGELOG.md` (seção C08 v4.0 nas linhas 9156-9263) | ✅ lido — seção completa, 15 itens de smoke E2E listados |
| schema.sql | `docs/db/schema.sql` (`alembic_version=012`) | ✅ existente, não tocado pelo C08 (frontend-only) |
| C08 analysis.md | `docs/wave2-v4-c08/analysis.md` em branch `wave2-v4-c08/analysis` (NÃO em `wave2-v4/componente-08`) | ⚠️ existe em branch separada; **link CHANGELOG.md:9159 quebra** na branch da entrega — ver AUD-W2C08-002 |
| Figma reference image | `docs/wave2-v4-c08/figma-reference.png` (esperado) | ❌ **AUSENTE** — nenhum PNG/JPG/SVG em `docs/` que represente o Figma — ver AUD-W2C08-001 |
| Audit reports anteriores | `docs/wave1-v4/audit-report.md`, `docs/wave2-v4/audit-report.md`, `docs/wave2-v4/audit-report-round2.md` | ✅ presentes; consultados para herança |
| Documentos canônicos v4.0 (`.docx`/`.drawio`) | `Desktop/Rastreio Prova Digital/` (RF-012, RNF-001, RN-006, US-008, BACKLOG C08, DAT) | ✅ confirmados via `analysis.md` Section 3 (Gate 1); nesta sessão consultei `.audit-tmp/{requisitos,backlog,dat}.txt` extraídos para texto |
| Código-fonte completo C08 | `frontend/src/app/(dashboard)/provas/[id]/{page.tsx,detalhe.module.css,Timeline.tsx,AdminActions.tsx,VisualizarEtiquetaModal.tsx,timeline.module.css}`, `frontend/src/app/(dashboard)/layout.tsx`, `frontend/src/lib/types/prova.ts`, `frontend/src/hooks/useProvaDetail.ts`, `frontend/src/app/globals.css`, `shared/access-matrix.json` | ✅ todos lidos integralmente |
| Histórico Git | 8 commits de `wave2-v4/componente-08` desde divergência de `development` (`d748269..eb9e46c`) | ✅ lido via `git log` |

### Confirmação de presença da imagem do Figma

❌ **CRÍTICO** — A imagem do Figma anexada ao prompt da execução **não foi preservada** em `docs/wave2-v4-c08/figma-reference.png` nem em qualquer outro path do repositório. Validações:
- `find /c/Users/mario.souza/provaDigital/docs -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.svg" -o -name "*.webp" \)` → **vazio**.
- `git ls-tree -r wave2-v4-c08/analysis -- docs/` → apenas `docs/wave2-v4-c08/analysis.md` (1 arquivo). Imagem nunca foi commitada.
- `analysis.md` Section 3 linha 108 confirma "a imagem anexada ao prompt **foi recebida**" — descrita textualmente em Section 5 com hierarquia, cores e tipografia. Mas o arquivo binário em si nunca foi salvo.
- `analysis.md` Section 11.3 linha 521 lista explicitamente "salvar a imagem do Figma anexada como referência permanente" como ação pós-Gate 2. **Não foi feito.**

Este é um achado **CRITICAL** explicitamente definido pelo prompt da execução (Seção 6.5) e da auditoria (Seção 7 da escala de severidade): "imagem do Figma ausente do repositório → CRÍTICO".

### Validação MCP — Supabase (read-only)

| Verificação | Resultado | Status |
|---|---|---|
| Projeto | `rwxlpwmnkekzuurgthkr` (sa-east-1, status ACTIVE_HEALTHY, Postgres 17) | ✅ |
| `provas_digitais.rota` | USER-DEFINED, nullable=YES (enum `rota_enum`) | ✅ preservado |
| `provas_digitais.codigo_publico` | character varying, nullable=NO | ✅ preservado (C06) |
| `provas_digitais.ciclo_atual` | integer, nullable=NO | ✅ |
| Trigger `trg_provas_rota_imutavel` | BEFORE UPDATE | ✅ |
| Trigger `trg_movimentacoes_imutavel` | BEFORE DELETE/UPDATE | ✅ |
| Trigger `trg_provas_updated_at` | BEFORE UPDATE | ✅ |
| Índice `idx_movimentacoes_prova` (prova_id) | EXISTE | ✅ |
| Índice composto `idx_movimentacoes_prova_data` (prova_id, created_at DESC) | EXISTE | ✅ |
| Índice `idx_movimentacoes_prova_ciclo` | EXISTE | ✅ |
| Índice `idx_movimentacoes_status_novo_created_at` | EXISTE | ✅ |
| Índice `idx_movimentacoes_created_at` | EXISTE | ✅ |
| Índice `idx_provas_codigo_publico` UNIQUE | EXISTE | ✅ |
| Índice `idx_provas_rota` | EXISTE | ✅ |
| `pol_provas_select` | usa `app_private.current_user_*()` (admin OR self_vendedor OR motorista_em_transito OR clicheria_states) | ✅ Wave 1 v4.0 |
| `pol_provas_insert` | `with_check: app_private.current_user_is_admin()` | ✅ |
| `pol_provas_update` | `qual: app_private.current_user_is_admin()` | ✅ |
| `pol_movimentacoes_select` | cobre admin/vendedor (via JOIN provas)/motorista/clicheria | ✅ |
| `pol_movimentacoes_insert` | `with_check: app_private.current_user_is_admin()` | ✅ |
| Total provas | 17 | ℹ️ |
| Provas com `rota IS NULL` (legacy v3.0) | **11** (65%) | ⚠️ tratamento legacy é norma, não caso de borda |
| Provas com rota | 6 (1 MATRIZ v4.0, 2 PADRAO legacy, 3 DIRETA legacy) | ℹ️ |
| Distribuição de status | CANCELADA=7, CRIADA=6, RECEBIDA_PELA_CLICHERIA=2, REPROVADA_PELO_VENDEDOR=2 | ℹ️ |
| Movimentações | 16 totais; max 4 por prova; max ciclo=2 | ℹ️ |
| status_novo distintos no histórico | 7 (APROVADA, CANCELADA, CRIADA, ENCAMINHADA_A_CLICHERIA, RECEBIDA_PELA_CLICHERIA, REPROVADA, RETIRADA) — todos mapeados em `STATUS_LABELS` | ✅ |
| `status_novo='CRIADA'` em `movimentacoes` | 1 row apenas (`status_anterior=REPROVADA, ciclo=2`) — confirma reinício; sem duplicação com nó implícito da Timeline | ✅ |
| EXPLAIN ANALYZE detalhe (4 rows) | Seq Scan (volume baixo) — Execution Time: 0.121 ms | ✅ esperado |
| Advisors security | 1 INFO (alembic_version, ADR-025) + 1 WARN (auth_leaked_password_protection, ADR-027) — pré-existentes; **nenhum novo após C08** | ✅ |
| Advisors performance | 13 INFO `unused_index` — todos pré-existentes (volume baixo); **nenhum novo após C08** | ✅ |
| Usuários ativos | 4 (2 admins STUDIO + 2 vendedores) — **sem MOTORISTA/CLICHERIA em produção** | ℹ️ |

### Validação MCP — Cloudflare

Não invocado nesta sessão (escopo do C08 é frontend-only). Validação indireta via `git diff main..wave2-v4/componente-08 -- backend/`: as alterações em backend listadas vêm exclusivamente das C06 Audit Fixes (`cbd6506..6b6c727`), todas anteriores ao C08. C08 não tocou storage, R2, workers ou KV.

### Critérios de aceitação do C08 (mapeados a partir do prompt de execução implícito + analysis Section 16)

| # | Critério (extraído do `analysis.md`/`CHANGELOG.md`) | Status | Evidência |
|---|---|---|---|
| 1 | Layout invertido (arte 380px esq · info 1fr dir) | ✅ | `detalhe.module.css:79` |
| 2 | Header tipográfico: "Requerimento: NNN" pequeno + nome grande | ✅ | `page.tsx:201-204` + `detalhe.module.css:97-112` |
| 3 | Divisor sob o título | ✅ | `page.tsx:205` + `detalhe.module.css:114-119` |
| 4 | Grid 3×2 de metadata (Cliente · Rota · Criada em / Vendedor · Ciclo Atual · Status) | ⚠️ Parcial — 7º item "Codigo:" extra (ver AUD-W2C08-005) | `page.tsx:207-250` |
| 5 | Banner full-width de cancelamento | ✅ | `page.tsx:252-257` + `detalhe.module.css:160-176` |
| 6 | Linha de ações com 2/3/4 botões side-by-side, sem quebra | ✅ | `detalhe.module.css:188-202` (`flex-wrap: nowrap`) |
| 7 | Card preto separado do innerCard branco | ✅ | `page.tsx:287-292` (section separada) |
| 8 | `STATUS_LABELS["CRIADA"] = "Aguardando vendedor"` (ADR-125) | ✅ | `prova.ts:157` |
| 9 | `ROTA_LABELS["PADRAO"] = "Padrao"` / `["DIRETA"] = "Direta"` (ADR-126) | ✅ | `prova.ts:198-199` |
| 10 | Layout invertido + grid 3×2 (ADR-127) | ✅ | `page.tsx` + `detalhe.module.css` reescritos |
| 11 | `isPathActive` para destacar "Provas" em `/provas/[id]` (ADR-128) | ✅ | `layout.tsx:90-94` |
| 12 | Timeline.tsx NÃO tocada | ✅ | `git diff` confirma — preservada |
| 13 | AdminActions.tsx NÃO tocada | ✅ | `git diff` confirma — preservada |
| 14 | Backend NÃO tocado | ✅ | `git diff development..wave2-v4/componente-08` cobre apenas frontend + docs |
| 15 | Migration NÃO criada | ✅ | nenhuma nova `versions/01N_*.py` |
| 16 | tsc --noEmit exit 0 | ✅ documentado em CHANGELOG:9259 — não re-executado nesta sessão (escopo read-only de auditoria não roda build) |
| 17 | next build 13/13 páginas | ✅ documentado em CHANGELOG:9260 |
| 18 | Tratamento de prova legacy (`rota IS NULL` → "—") preservado | ✅ | `page.tsx:30-37` `formatRota(null) = "—"` |
| 19 | Smoke E2E manual obrigatório executado | ❌ pendente — listado em CHANGELOG:9210 (15 itens) | CLAUDE.md tabela: "aguarda smoke visual humano + PR" |
| 20 | Imagem do Figma preservada em `docs/wave2-v4-c08/figma-reference.png` | ❌ **CRITICAL — AUD-W2C08-001** | inventário do diretório `docs/` mostra ZERO arquivos de imagem |
| 21 | `docs/wave2-v4-c08/analysis.md` em branch da entrega | ❌ ALTO — AUD-W2C08-002 | só presente na branch `wave2-v4-c08/analysis`; CHANGELOG:9159 link aponta para path inexistente |
| 22 | Cobertura de testes Vitest novos (analysis Section 12.1) | ❌ ALTO — AUD-W2C08-003 | zero testes novos commitados |

### Cobertura dos 4 valores de `rota_enum` + legacy + null (renderização de `formatRota`)

| Rota | `formatRota(value)` retorna | Caminho de código | Teste unitário | Teste E2E |
|---|---|---|---|---|
| `MATRIZ` | "Matriz" | `prova.ts:194` | ❌ ausente | ❌ ausente |
| `LAM_MATRIZ` | "Lam. Matriz" | `prova.ts:195` | ❌ ausente | ❌ ausente |
| `FILIAL` | "Filial" | `prova.ts:196` | ❌ ausente | ❌ ausente |
| `LAM_FILIAL` | "Lam. Filial" | `prova.ts:197` | ❌ ausente | ❌ ausente |
| `PADRAO` (legacy v3.0) | "Padrao" (sem sufixo "(legada v3.0)") | `prova.ts:198` | ❌ ausente | ❌ ausente |
| `DIRETA` (legacy v3.0) | "Direta" (sem sufixo) | `prova.ts:199` | ❌ ausente | ❌ ausente |
| `null` (legacy pré-Wave 7) | "—" | `page.tsx:30-37` | ❌ ausente | ❌ ausente |

Cobertura: **0/7 cenários** testados via Vitest. Suite backend `test_provas_api.py` tem 21 testes herdados do C08 v3.0 que validam o response payload com `rota`, mas nenhum exercita o helper de renderização do frontend (escopo TS, não Python).

### Tratamento de provas legacy (`rota IS NULL`)

✅ Funcional. `formatRota(null)` retorna `"—"` em em-dash literal. ADR-126 documenta a decisão (sem sufixo "legada v3.0"). A `Timeline.tsx` tampouco quebra com null em `rota_no_momento` (linha 239: `node.isRoteamento && node.rotaNoMomento && ...` — guard contra null).

⚠️ **Sem teste explícito** que monte um `ProvaResponse` com `rota: null` e valide ausência de quebra na renderização. Em produção, 11 de 17 provas (65%) são legacy → o código foi exercitado em produção pelo Mario nos commits do C06 e em smoke manual, mas a regressão na próxima passada não fica blindada por automação.

⚠️ Sem tooltip ou microcopy explicando que "—" significa "prova legacy v3.0 — rota a ser backfilled na Wave 7". Para um admin que não conhece o histórico, "—" é cripto. Decisão registrada em ADR-126 ("os usuarios convivem com isso ate Wave 7"); aceito mas marco INFO.

### Visibilidade condicional do painel de ações (matriz perfil × status)

| Botão | Regra | Cobertura no código | Defesa em profundidade backend | Cobertura por teste |
|---|---|---|---|---|
| **Visualizar etiqueta** | Sempre visível para usuário com acesso à prova | `page.tsx:265-271` (sempre presente) | RLS `pol_provas_select` + `_scoping_filter_for_detail` | ❌ sem Vitest |
| **Baixar etiqueta** | Idem | `page.tsx:272-278` (sempre presente) | Mesmo path do anterior | ❌ sem Vitest |
| **Reiniciar Ciclo** | `useAuthorization("provas.restart").hasAccess` (admin) AND `prova.status === "REPROVADA_PELO_VENDEDOR"` | `AdminActions.tsx:106` (`podeReiniciar`) | endpoint `POST /{id}/reiniciar-ciclo` aplica `access_required("provas.restart")` (Wave 1 v4.0) | ❌ sem Vitest novo (testes backend C13/C14 herdados existem) |
| **Cancelar Prova** | `useAuthorization("provas.cancel").hasAccess` (admin) AND `prova.status IN CANCELAVEIS` | `AdminActions.tsx:104` (`podeCancelar`) + lista CANCELAVEIS linha 13-22 | endpoint `POST /{id}/cancelar` aplica `access_required("provas.cancel")` | ❌ sem Vitest novo |

| Cenário (perfil × status) | Comportamento esperado | Verificação na auditoria |
|---|---|---|
| 3Studio + REPROVADA_PELO_VENDEDOR | 4 botões visíveis (Visualizar / Baixar / Reiniciar / Cancelar) | ✅ código confirma |
| 3Studio + CRIADA | 3 botões (Visualizar / Baixar / Cancelar) — Reiniciar oculto | ✅ código confirma |
| 3Studio + CANCELADA | 2 botões (Visualizar / Baixar) — ambos admin ocultos | ✅ código confirma (CANCELADA não está em CANCELAVEIS) |
| 3Studio + RECEBIDA_PELA_CLICHERIA | 2 botões (Visualizar / Baixar) — ambos admin ocultos | ✅ código confirma |
| Vendedor + sua prova qualquer status | 2 botões (Visualizar / Baixar) — admin oculto via `useAuthorization` | ✅ código confirma (early return null em `AdminActions:102`) |
| Vendedor + prova alheia | 404 (RLS bloqueia leitura) | ✅ `pol_provas_select` confirmado |
| Motorista + prova COM_MOTORISTA | 2 botões (Visualizar / Baixar) — admin oculto | ✅ código confirma; RLS permite leitura via `current_user_setor()='MOTORISTA'` |
| Motorista + prova fora de COM_MOTORISTA | 404 (RLS bloqueia) | ✅ confirmado em `pol_provas_select` |
| Clicheria + prova `*_CLICHERIA` | 2 botões (Visualizar / Baixar) | ✅ confirmado |
| Clicheria + prova fora de `*_CLICHERIA` | 404 (RLS bloqueia) | ✅ — embora `_clicheria_divergence_note` em access-matrix.json:67 indique que a Matriz literal diz `full` para Clicheria; comportamento conservador foi mantido (parcial via status) |
| Anônimo | redirect para `/login` via middleware Next.js | ✅ middleware Wave 1 v4.0 |

⚠️ Nenhum desses 11 cenários tem teste Vitest. Cobertura é por inspeção de código + `pg_policies`. Em produção, há 4 usuários ativos (2 admins + 2 vendedores) — **sem MOTORISTA nem CLICHERIA em produção**, então o caminho de scoping para esses 2 perfis nunca foi exercitado em dados reais.

### Timeline estruturalmente capaz para Wave 3

✅ **Confirmado: orientada a dados.** Análise de `Timeline.tsx`:

- Linhas 73-93: `for (let i = 0; i < movimentacoes.length; i++)` — não há switch/if hardcoded por estado.
- Linhas 88-91: as 4 flags booleanas (`isReprovacao`, `isCancelamento`, `isTerminal`, `isRoteamento`) são derivadas por comparação direta com strings (`sNovo === "REPROVADA_PELO_VENDEDOR"` etc.). Adicionar um novo estado na Wave 3 não exige tocar o componente, apenas:
  1. Adicionar valor em `StatusProva` em `prova.ts`.
  2. Adicionar entrada em `STATUS_LABELS` (e `STATUS_LABELS_SHORT`).
  3. Adicionar transições em `state_machine.py` no backend.
  4. *Opcional:* se o novo estado precisar de cor/badge especial, expandir as 4 flags em `Timeline.tsx` (ex.: `isLaminacao`).
- `STATUS_LABELS` é o único ponto de tradução estado → texto pt-BR; ele é um `Record<StatusProva, string>` → o TS força exaustividade na compilação (toda chave do enum precisa estar mapeada, ou `tsc --noEmit` falha).

✅ Documentação em `CLAUDE.md` cobre o fluxo de adição de valor ao `rota_enum` (seção "Como adicionar valor ao enum `rota_enum`"). Não há seção análoga para `StatusProvaEnum`, mas o fluxo é simétrico — uma referência seria útil. **Marco como BAIXO.**

### Performance (RNF-001 — < 3 segundos)

| Componente do tempo | Medição/Análise | Status |
|---|---|---|
| Estratégia de carregamento | `Promise.allSettled` com 3 requests paralelos (`useProvaDetail.ts:75-79`) | ✅ |
| Race protection | `latestReqRef` em `useProvaDetail.ts:49` descarta loads antigos | ✅ |
| Tolerância parcial | imagem R2 pode falhar sem derrubar prova nem histórico | ✅ |
| EXPLAIN ANALYZE de `movimentacoes WHERE prova_id = ...` | Seq Scan (4 rows / 16 totais), 0.121 ms — Postgres escolhe Seq Scan em volume baixo | ✅ esperado |
| Índice usado em volume real | `idx_movimentacoes_prova` aparece em advisors `unused_index` (esperado em volume baixo; advisor não precisa ação) | ✅ |
| Bundle First Load `/provas/[id]` | 11.4 kB / 209 kB (CHANGELOG:9261) — alto (era ~10kB), mas dentro do orçamento de uma SPA Next.js 14 | ⚠️ |
| Teste automatizado de TTFP/TTI | Ausente — analysis Section 12.5 dizia "medir no Gate 2"; não foi feito | ⚠️ marco BAIXO |
| Cache HTTP | sem ETag/Cache-Control nos endpoints `/provas/{id}` | ⚠️ analysis Section 10.3 explicitamente fora de escopo; OK |

**Conclusão de performance:** atende RNF-001 com folga em volume atual (16 movs, 17 provas). Sem teste automatizado, regressão futura pode passar despercebida.

### Acessibilidade

| Aspecto | Status | Evidência |
|---|---|---|
| Contraste mínimo AA | ⚠️ NÃO MEDIDO — analysis prometeu Lighthouse no Gate 2 | nada commitado; `--color-card-text-muted = #575757` sobre `#eaeaea` ≈ 6.8:1 (passa AA); `--color-card-text = #000` sobre `#eaeaea` passa AAA |
| Labels ARIA nos modais | ✅ | `AdminActions.tsx:139-141, 193-195` (`aria-modal`, `aria-labelledby`) |
| Botão "Voltar" | ✅ ícone com `aria-hidden="true"` (`page.tsx:56`) — texto visível "Voltar" |
| Focus trap nos modais | ✅ via `useFocusTrap` (Wave 3 Auditoria) |
| Navegação por teclado | ⚠️ NÃO TESTADO automatizadamente; código não bloqueia tab order | ESC fecha modal (`AdminActions.tsx:75-79`) |
| Imagem da arte | ✅ `alt={...}` (`page.tsx:179`) |
| Heading hierarchy | ✅ `<h1>` único na página (`.title`); `<h2>` no card preto |
| Teste automatizado a11y (axe-core) | ❌ ausente | analysis Section 12.6 prometeu; não foi feito |

### Documentação atualizada

| Arquivo | Status | Observação |
|---|---|---|
| `CHANGELOG.md` (seção C08 v4.0) | ✅ presente nas linhas 9156-9263 | Lista os 4 ADRs, descreve adicionado/modificado/iterações; histórico anterior preservado (não sobrescrito) |
| `DECISIONS.md` (ADRs 125-128) | ✅ presente nas linhas 5063-5258 | 4 ADRs completos: contexto, decisão, alternativas, consequências. Sólida documentação |
| `CLAUDE.md` (seção sobre página de detalhe) | ⚠️ não há seção dedicada "Página de detalhe de prova: estrutura e extensão" como o prompt de auditoria recomendava — apenas tabela de Waves atualizada com a linha do C08. Para a Wave 3 expandir Timeline para 14 estados, falta documento operacional explícito. **Marco MÉDIO.** |
| `docs/wave2-v4-c08/analysis.md` | ⚠️ existe APENAS na branch `wave2-v4-c08/analysis`, NÃO na branch `wave2-v4/componente-08`. Link em CHANGELOG.md:9159 quebra. **Ver AUD-W2C08-002.** |
| `docs/wave2-v4-c08/figma-reference.png` | ❌ ausente. **AUD-W2C08-001** (CRITICAL). |
| `docs/wave2-v4-c08/audit-report.md` | ✅ este arquivo |

### Migrations versionadas

✅ Nenhuma migration nova exigida (frontend-only). `alembic_version=012` em produção (consistente com C06 + C06 Audit Fixes Round 1). Trigger `trg_provas_rota_imutavel` ativo. Índices necessários presentes.

### Refactor coordenado completo

✅ A lista de pontos modificados fora da página de detalhe foi:
- `frontend/src/app/(dashboard)/layout.tsx` (helper `isPathActive`)
- `frontend/src/lib/types/prova.ts` (STATUS_LABELS, STATUS_LABELS_SHORT, ROTA_LABELS)

✅ Endpoints de Cancelamento (C13) e Reinício de Ciclo (C14) **NÃO foram modificados** — apenas integrados pelo `AdminActions` que já existia.
✅ Cadastro (C06) e RBAC (Wave 1) **NÃO foram tocados** (zero diff em backend para o C08 — apenas as alterações herdadas das C06 Audit Fixes que vieram via base `development`).

---

## Fase 2 — Auditoria Qualitativa Aprofundada

### Achados de Segurança

#### AUD-W2C08-S01 — Visibilidade no cliente é apoiada por defesa em profundidade no servidor (POSITIVO, não-finding)

**Severidade:** INFO (positivo)
**Evidência:** `AdminActions.tsx:102, 104, 106` — `useAuthorization("provas.cancel/restart")` esconde botões. Backend `provas.py` aplica `access_required("provas.cancel/restart")` nos endpoints (Wave 1 v4.0). RLS `pol_provas_update` exige `current_user_is_admin()`. Atacante que inspecione o DOM ou envie POST direto continua bloqueado nas 3 camadas.
**Recomendação:** preservar este padrão em entregas futuras.

#### AUD-W2C08-S02 — Acesso direto via URL para prova alheia respeita RLS

**Severidade:** INFO (positivo)
**Evidência:** `pol_provas_select` retorna 0 rows para vendedor acessando prova de outro vendedor; `useProvaDetail.ts:88-92` traduz 404 do backend para "Prova nao encontrada." sem vazar informação sobre existência. Middleware Next.js (Wave 1 v4.0) redireciona para `/login` se não autenticado.
**Recomendação:** preservar.

#### AUD-W2C08-S03 — `_clicheria_divergence_note` continua não-resolvido

**Severidade:** INFO
**Evidência:** `shared/access-matrix.json:67` documenta que a Matriz literal Section 6 dos Requisitos diz que Clicheria tem `full` em Listagem e Detalhe, mas a implementação aplica `parcial` (filtro por status). O follow-up está registrado desde Wave 1 v4.0 mas não foi resolvido. C08 não introduz nem corrige a divergência — herda comportamento.
**Recomendação:** abrir ticket para confirmar com Mario qual é a fonte canônica (Matriz Section 6 ou comportamento conservador). Não bloqueia C08.

### Achados de Correção (Bugs)

#### AUD-W2C08-B01 — `formatRota(null) = "—"` é discreto mas críptico

**Severidade:** BAIXO (defensável; já em ADR-126)
**Evidência:** `page.tsx:30-37` retorna em-dash literal sem tooltip. Em produção, 65% das provas exibem isso.
**Recomendação:** preservar como está; opcionalmente adicionar `<span title="Prova legacy v3.0 — rota será backfilled na Wave 7">—</span>` com `title` HTML padrão (zero JS). Marco BAIXO.

#### AUD-W2C08-B02 — `.metaGrid` adiciona "Codigo:" como 7º item (fora do plano 3×2 do Figma)

**Severidade:** MÉDIO
**Evidência:** `page.tsx:242-249` adiciona um 7º item "Codigo: PRV-AAAA-MM-NNNNNN" em mono. Figma mostra grid 3×2 com 6 campos (Cliente · Rota · Criada em / Vendedor · Ciclo Atual · Status). ADR-127 cita "Codigo aparecendo no slot 7 quando disponivel" sem documentar como divergência consciente da imagem do Figma.
**Recomendação:** ou remover o campo do metaGrid e exibir o `codigo_publico` em outro lugar (ex.: subtítulo do header, ao lado de "Requerimento: NNN"), ou registrar em ADR-127 como divergência consciente. Marco MÉDIO porque viola o "grid 3x2" prometido literalmente.

#### AUD-W2C08-B03 — `.metaGrid` em mobile (≤1100px) deixa "Codigo" sozinho na última linha

**Severidade:** MÉDIO
**Evidência:** `detalhe.module.css:614-617` reduz para `repeat(2, 1fr)` em ≤1100px. Resultado: 4 linhas sequenciais (Cliente/Rota, Criada em/Vendedor, Ciclo Atual/Status, **Codigo / —**). Layout assimétrico que contradiz o "blocado" pedido pelo Mario.
**Recomendação:** ou remover Codigo do grid (resolve o B02 + B03 juntos), ou pôr Codigo em `grid-column: 1 / -1` (linha cheia) tanto em desktop quanto em mobile.

#### AUD-W2C08-B04 — `.title` em viewports < 800px cai a 16px (fora da escala do Figma)

**Severidade:** MÉDIO
**Evidência:** `detalhe.module.css:106` — `font-size: clamp(1rem, 2.5vw, 2.5rem)`. Em 768px, `2.5vw = 19.2px ≈ 1.2rem`; entre 768 e 1100px, valor varia de 19px a 27px. Análise textual do Figma sugere ~36-40px (= 2.25-2.5rem). Em mobile o título fica menor que valores da metadata (16px = 1rem).
**Recomendação:** trocar para `clamp(1.5rem, 2.5vw, 2.5rem)` (mantém máximo 40px, mínimo 24px). Mas note: `@media (max-width: 768px)` esconde a página inteira via `mobileNotice`, então o problema só aparece em ~769px-1100px. Marco MÉDIO.

#### AUD-W2C08-B05 — `.artImg` `object-fit: cover` pode cortar conteúdo crítico de artes retangulares

**Severidade:** BAIXO
**Evidência:** `detalhe.module.css:298` — slot quadrado 1:1 com `object-fit: cover`. Provas reais costumam ser etiquetas retangulares (8.5×11 polegadas). `cover` corta laterais ou topo/base para preencher.
**Recomendação:** considerar `object-fit: contain` (preserva proporção, deixa "letterbox" cinza). Decisão depende do Mario — pode ser intencional. Marco BAIXO.

#### AUD-W2C08-B06 — Timeline.tsx hardcoda `usuarioNome: "3Studio"` no nó implícito inicial

**Severidade:** BAIXO (pré-existente, não introduzido pelo C08)
**Evidência:** `Timeline.tsx:60-61` — `usuarioNome: "3Studio"`, `usuarioSetor: "STUDIO"`. Isso é correto para a maior parte dos casos (a prova é criada por um admin STUDIO), mas o admin específico que criou (e que existe em `audit_logs` por `usuario_id` — campo `criado_por`) é genericizado. O CLAUDE.md mostra 2 admins ativos (`Admin Master`, `Operacao 3Studio`) — qualquer um deles pode criar uma prova, mas a Timeline mostra "3Studio" genericamente.
**Recomendação:** opcional — passar `prova.criado_por_nome` ao Timeline (exigiria expandir `ProvaResponse`). Não C08-blocking. Marco BAIXO.

#### AUD-W2C08-B07 — `formatStatus` é wrapper trivial sem valor agregado

**Severidade:** BAIXO
**Evidência:** `page.tsx:39-41` — `function formatStatus(status: StatusProva): string { return STATUS_LABELS[status]; }`. Idêntico a inline `STATUS_LABELS[prova.status]`. Adiciona ruído.
**Recomendação:** remover a função; usar `STATUS_LABELS[prova.status]` direto. Marco BAIXO.

### Achados de Regressões em Waves Anteriores

#### AUD-W2C08-R01 — `STATUS_LABELS["CRIADA"]` rename afeta 5+ páginas (esperado pelo ADR-125, validar smoke)

**Severidade:** BAIXO (controlado pelo ADR; impacto cross-page é a decisão consciente do Mario)
**Evidência:** ADR-125 lista os 5 lugares afetados: `escanear/page.tsx`, `provas/page.tsx`, `provas/[id]/Timeline.tsx`, `relatorios/perspectivas/ReportGeral.tsx`, `relatorios/StatusFilter.tsx`. CHANGELOG:9210 lista smoke E2E manual. Não há teste de paridade automatizado.
**Recomendação:** smoke manual é obrigatório antes do PR. Garantir que filtro de Status na listagem (`/provas`) e nas perspectivas de Relatórios mostram "Aguardando" / "Aguardando vendedor" em vez de "Criada".

#### AUD-W2C08-R02 — `ROTA_LABELS` rename afeta filtros/badges (esperado pelo ADR-126)

**Severidade:** BAIXO (idem)
**Evidência:** ADR-126 lista 4 lugares afetados. Sem teste de paridade.
**Recomendação:** mesmo smoke manual.

#### AUD-W2C08-R03 — `isPathActive` muda destaque do menu globalmente (não só /provas)

**Severidade:** BAIXO (intencional pelo ADR-128, mas sem teste)
**Evidência:** `layout.tsx:90-94` — agora qualquer item de menu com `pathname.startsWith(href + "/")` fica ativo. Anteriormente, `pathname === href`. Ex.: em `/auditoria/[id]` (futura sub-rota não-existente hoje) o item "Auditoria" passaria a destacar; em `/escanear/abc-uuid` (também não existente) o "Escanear" destacaria. Comportamento desejado pelo Mario, mas sem teste.
**Recomendação:** adicionar 1 teste Vitest para `isPathActive(pathname, href)` com 5 casos (exato, prefix, prefix-with-trailing-slash, false-positive `/provas-other`, undefined href). Marco BAIXO.

#### AUD-W2C08-R04 — Histórico do CHANGELOG NÃO foi sobrescrito

**Severidade:** INFO (positivo)
**Evidência:** `git log --stat -- CHANGELOG.md` mostra que `b59345c` adiciona 88 linhas e `eb9e46c` adiciona 33 linhas (sem deleções). Histórico de 9156 linhas anteriores preservado.

#### AUD-W2C08-R05 — Endpoints C13/C14 não modificados

**Severidade:** INFO (positivo)
**Evidência:** `git diff development..wave2-v4/componente-08 -- backend/` retorna 0 (apenas frontend tocado nesta entrega).

### Achados de Performance

#### AUD-W2C08-P01 — Performance dentro de RNF-001 em volume atual; sem teste automatizado para regressão

**Severidade:** BAIXO
**Evidência:** análise EXPLAIN ANALYZE retorna 0.121 ms para a query mais quente (movimentações de uma prova). 16 movs totais, max 4 por prova. No volume atual, qualquer estratégia é rápida.
**Recomendação:** quando o volume crescer (>1000 movs por prova ou >100k provas), revisitar. Adicionar Lighthouse run em CI (opcional para v4.0).

#### AUD-W2C08-P02 — First Load `/provas/[id]` saltou de ~10kB para 11.4kB (+14%)

**Severidade:** INFO
**Evidência:** CHANGELOG:9261. O salto vem da reescrita do CSS (mais classes), não de novas dependências. JS bundle inalterado.
**Recomendação:** ok no orçamento atual.

#### AUD-W2C08-P03 — `useProvaDetail` dispara 3 requests por mount

**Severidade:** INFO
**Evidência:** `useProvaDetail.ts:75-79`. Documentado em analysis Section 10.3. Estratégia paralela via `Promise.allSettled` mantém p99 baixo.
**Recomendação:** preservar. Endpoint agregado seria YAGNI (Section 10.3).

### Achados de Manutenibilidade

#### AUD-W2C08-M01 — `--color-card-art-bg` token nunca foi criado, `.artSlot` usa `--color-card-surface=#e4e4e4`

**Severidade:** ALTO (pode prejudicar percepção visual em loading)
**Evidência:** `detalhe.module.css:290` — `background: var(--color-card-surface, #d9d9d9)`. `--color-card-surface = #e4e4e4` (`globals.css:27`). O fallback `#d9d9d9` é dead code. `.cardInner` no layout pai tem `background: #eaeaea`. Diferença `#e4e4e4` vs `#eaeaea` ≈ delta de 6 unidades RGB → quase invisível.

Quando a imagem carrega normalmente: invisível (img preenche via `object-fit: cover`).
Quando a imagem está carregando OU falhou: o slot fica com cor "fantasma" do mesmo cinza-claro do card-pai. Placeholder textual (`<p>Carregando arte...</p>`) é visível, mas o "quadrado cinza" do Figma — que serve para sinalizar "espaço da arte" mesmo sem imagem — não aparece.

Analysis Section 5.3 propôs explicitamente `--color-card-art-bg = #d9d9d9` (cinza médio). Token nunca foi criado.

**Recomendação:** criar token `--color-card-art-bg = #d9d9d9` em `globals.css` e usá-lo em `.artSlot`. Mudança de 2 linhas. Marco **ALTO** porque viola fidelidade visual prometida no analysis e impacta UX em estado loading/erro (que é frequente em produção — arte pode não carregar do R2 enquanto presigned URL é gerada).

#### AUD-W2C08-M02 — `formatStatus` wrapper trivial (ver B07)

**Severidade:** BAIXO (já listado).

#### AUD-W2C08-M03 — `Codigo:` no metaGrid quebra hierarquia visual (ver B02 e B03)

**Severidade:** MÉDIO (já listados).

#### AUD-W2C08-M04 — Comentários de código são bons; `Why` documentado em pontos críticos

**Severidade:** INFO (positivo)
**Evidência:** `page.tsx:31-34` (formatRota explica decisão Wave 7); `page.tsx:259-263` (actionsRow explica decisão A2 do Mario); `detalhe.module.css:60-68` (innerCard explica iteração pós-Figma). Comentários focam no "por quê", não no "o quê".

#### AUD-W2C08-M05 — TypeScript estrito preservado; sem `any` introduzido

**Severidade:** INFO (positivo)
**Evidência:** `git diff` em `page.tsx`, `Timeline.tsx`, `AdminActions.tsx`, `prova.ts` — nenhum `any` ou `as` agressivo novo. Único `as` é em `Timeline.tsx:76` (`const sNovo = m.status_novo as StatusProva`) — pré-existente, não C08.

#### AUD-W2C08-M06 — Falta seção dedicada no CLAUDE.md sobre "Página de detalhe: estrutura e extensão"

**Severidade:** MÉDIO
**Evidência:** o prompt de auditoria Section 4.10 explicitamente esperava essa seção para que a Wave 3 expanda Timeline para 14 estados sem "ler o código todo". CLAUDE.md tem seção sobre `rota_enum` (similar) mas não sobre `StatusProvaEnum`. CHANGELOG documenta o estado atual mas não orienta o próximo manutentor.
**Recomendação:** adicionar seção operacional de ~30 linhas em CLAUDE.md cobrindo: como adicionar valor a `StatusProva`, como mapear em `STATUS_LABELS`/`STATUS_LABELS_SHORT`, como expandir flags em `Timeline.tsx` se o estado tiver cor/badge especial, como atualizar `state_machine.py`. Marco MÉDIO.

### Achados de Cobertura de Testes

#### AUD-W2C08-T01 — ZERO testes Vitest novos no Gate 2 (analysis Section 12.1 prometeu 5+)

**Severidade:** ALTO
**Evidência:** `git diff development..wave2-v4/componente-08 -- frontend/` retorna 0 arquivos `.test.ts`/`.test.tsx`. Analysis explicitamente lista:
- `formatRota` para 4 v4.0 + 2 legacy + null = 7 cenários
- `MetadataGrid` render para todos os campos completos = 1
- `MetadataGrid` render para `motivo_cancelamento` presente = 1
- `MetadataGrid` render para `rota IS NULL` = 1
- `<AdminActions>` snapshot por perfil × status (~10 chave) = 10

Total prometido: ≥ 18 testes Vitest. Total entregue: 0. Wave 1 v4.0 Audit Round 2 (AUD-W1V4-005) estabeleceu Vitest como padrão obrigatório para entregas frontend que tocam UI.

**Recomendação:** adicionar pelo menos 7 testes para `formatRota` (4+2+null) + 1 para `isPathActive` (5 casos) antes do PR. Marco **ALTO**.

#### AUD-W2C08-T02 — Sem teste E2E (Playwright fora do escopo desde Wave 1 v4.0)

**Severidade:** INFO
**Evidência:** smoke E2E manual obrigatório em CHANGELOG:9210-9231 (15 itens). Esse compromisso é compatível com Wave 1 v4.0 que excluiu Playwright do escopo da v4.0.
**Recomendação:** executar smoke manual antes do PR. Documentar resultado em fix-validation-style.

#### AUD-W2C08-T03 — Suite backend `test_provas_api.py` (21 testes) preservada — sem regressão esperada

**Severidade:** INFO (positivo)
**Evidência:** `git diff development..wave2-v4/componente-08 -- backend/` = 0. Suite Python intacta.

### Achados de Documentação

#### AUD-W2C08-D01 — Imagem do Figma não preservada (CRITICAL — ver Achados Consolidados)

#### AUD-W2C08-D02 — analysis.md em branch separada, link CHANGELOG.md:9159 quebrado (ALTO — ver Achados Consolidados)

#### AUD-W2C08-D03 — Falta seção "Página de detalhe" em CLAUDE.md (MÉDIO — ver M06)

#### AUD-W2C08-D04 — Iterações pós-Figma documentadas no CHANGELOG (POSITIVO)

**Severidade:** INFO (positivo)
**Evidência:** CHANGELOG:9233-9251 documenta 3 iterações com commits + razão verbalizada do Mario. Excelente rastreabilidade.

#### AUD-W2C08-D05 — ADRs 125-128 cobrem alternativas e trade-offs

**Severidade:** INFO (positivo)
**Evidência:** cada ADR tem seções "Decisão", "Alternativas", "Consequências". ADR-127 cita até propostas de implementação rejeitadas (ex.: `auto-fit` no `actionsRow`).

### Achados de Aderência ao Especificado

#### AUD-W2C08-A01 — Escopo respeitado: zero touch em backend/RLS/migrations

**Severidade:** INFO (positivo)
**Evidência:** confirmado via `git diff development..wave2-v4/componente-08`. Nenhum endpoint tocado. Nenhuma migration. Nenhum arquivo RLS.

#### AUD-W2C08-A02 — Framer Motion existente preservado, nenhum novo introduzido

**Severidade:** INFO (positivo)
**Evidência:** `Timeline.tsx` ainda usa Framer Motion (animações de entrada e pulso) — pré-existente desde Wave 3 Lote B. `page.tsx` e `detalhe.module.css` não importam framer-motion. Sem violação do escopo "esperar Wave 6".

#### AUD-W2C08-A03 — Máquina de estados não expandida

**Severidade:** INFO (positivo)
**Evidência:** `state_machine.py` não tocado. `StatusProva` em `prova.ts` mantém 10 valores.

### Achados de Fidelidade ao Figma

#### AUD-W2C08-F01 — Imagem do Figma não preservada — auditoria de fidelidade pixel-a-pixel impossível

**Severidade:** CRITICAL (ver AUD-W2C08-001)

#### AUD-W2C08-F02 — `.artSlot` quase invisível em loading/falha (ver M01)

**Severidade:** ALTO

#### AUD-W2C08-F03 — `Codigo:` adicionado fora do plano 3×2 do Figma (ver B02)

**Severidade:** MÉDIO

#### AUD-W2C08-F04 — `.title` muito pequeno em mobile-tablet (ver B04)

**Severidade:** MÉDIO

#### AUD-W2C08-F05 — Hierarquia tipográfica preservada quanto à descrição textual da analysis Section 5.2.2 (POSITIVO)

**Severidade:** INFO (positivo)
**Evidência:** `requerimentoLabel` 0.9rem (analysis estimou ~12-14px = 0.75-0.875rem; ligeira divergência); `title` clamp(...,2.5rem); `metaLabel` 0.8rem; `metaValue` 1rem. Hierarquia (label < requerimento < value < title) preservada.

#### AUD-W2C08-F06 — Card preto separado do innerCard branco (POSITIVO)

**Severidade:** INFO (positivo)
**Evidência:** `page.tsx:287-292` — `<section className={styles.timelineCard}>` é irmão de `<section className={styles.innerCard}>`. Espelha a hierarquia textual do analysis Section 5.2.3. Antes era aninhado.

---

## Fase 3 — Verificação Comportamental em Staging (read-only)

### Estado real das tabelas

| Tabela | Estado | Status |
|---|---|---|
| `provas_digitais.rota` | nullable USER-DEFINED `rota_enum` (6 valores: 4 v4.0 + 2 legacy) | ✅ |
| `provas_digitais.codigo_publico` | NOT NULL VARCHAR | ✅ |
| `trg_provas_rota_imutavel` | BEFORE UPDATE | ✅ |
| `idx_movimentacoes_prova` | EXISTE (advisor `unused_index` esperado em volume baixo) | ✅ |
| `idx_movimentacoes_prova_data` (composto) | EXISTE | ✅ |

### Distribuição de dados

| Métrica | Valor |
|---|---|
| Total de provas | 17 |
| Legacy (`rota IS NULL`) | 11 (65%) |
| Com rota v4.0 (`MATRIZ`) | 1 (6%) |
| Com rota legacy v3.0 (`PADRAO`/`DIRETA`) | 5 (29%) |
| Provas em CANCELADA | 7 |
| Provas em CRIADA (mostrado como "Aguardando vendedor") | 6 |
| Provas em RECEBIDA_PELA_CLICHERIA (terminal) | 2 |
| Provas em REPROVADA_PELO_VENDEDOR | 2 (ambas com `rota IS NULL`, com 2 movs cada — botão Reiniciar visível) |
| Movimentações totais | 16 |
| Max movimentações por prova | 4 |
| Max ciclo_atual em produção | 2 |
| Provas com 2+ ciclos identificadas | 1 (`66f36e8b-13ec-45a7-812d-f2111db2a9e9`) |

### Cenários de borda observáveis

| Cenário | Resultado |
|---|---|
| Prova com >100 movimentações | ❌ inexistente em produção (max=4) |
| Prova com `prova.rota` divergente do histórico | ❌ inexistente (consistência preservada) |
| Movimentações com timestamps fora de ordem cronológica | ❌ inexistente (validador automatizado) |
| Provas REPROVADAS para teste do botão Reiniciar | ✅ 2 disponíveis (`bd1d722d`, `73be85ae`) |
| Prova com 2 ciclos para teste de agrupamento | ✅ 1 disponível (`66f36e8b`) |
| Prova com `motivo_cancelamento` para teste de banner | ✅ 7 candidatas (CANCELADAs) |

### Acesso simulado por perfil (via leitura das policies)

Não foi possível impersonar role `authenticated` via MCP sem `set_config('request.jwt.claims', ...)`. Análise feita via leitura literal de `pg_policies`:

| Perfil | Cenário | Comportamento esperado | Validação |
|---|---|---|---|
| 3Studio (admin) | qualquer prova | retorna registro | `pol_provas_select`: primeiro disjunto `app_private.current_user_is_admin()` ✅ |
| Vendedor | prova dele | retorna registro | `pol_provas_select`: `vendedor_id = app_private.current_user_id()` ✅ |
| Vendedor | prova alheia | 0 linhas (404 no endpoint) | mesma policy não retorna ✅ |
| Motorista | prova `COM_MOTORISTA` | retorna registro | `pol_provas_select`: `(status = 'COM_MOTORISTA' AND current_user_setor() = 'MOTORISTA')` ✅ |
| Motorista | prova fora de COM_MOTORISTA | 0 linhas | mesma policy ✅ |
| Clicheria | prova `*_CLICHERIA` (3 estados) | retorna registro | `pol_provas_select`: `(status IN [ENVIADA, ENCAMINHADA, RECEBIDA] AND current_user_setor()='CLICHERIA')` ✅ |
| Clicheria | prova fora dos 3 estados | 0 linhas | mesma policy ✅ — divergência da Matriz literal documentada em access-matrix.json:67 |
| Anônimo (sem JWT) | qualquer | 0 linhas (RLS bloqueia) | nenhuma policy avaliá-lo como autorizado ✅ |

⚠️ **Limitação:** Em produção há 4 usuários ativos (2 admins + 2 vendedores). Sem MOTORISTA nem CLICHERIA cadastrados. Os caminhos de RLS para esses 2 perfis nunca foram exercitados em dados reais — funcionam por construção da policy, não por amostragem.

### Audit log do C08

C08 foi entregue como mudança puramente frontend. **Nenhuma DDL foi aplicada em produção** durante o C08 (validado: `alembic_version=012` desde C06; sem novas RLS migrations). Logo, **nenhuma entrada no audit log do C18 corresponde ao C08** — esperado e correto.

Acessos à página `/provas/[id]` não são logados em audit_log (auditoria do C18 cobre apenas operações de domínio: cancelamento, reinício, criação de prova, criação/edição de usuário). Leitura de detalhe não fica auditada — comportamento estabelecido em Wave 6 e fora do escopo do C08.

---

## Achados Consolidados Ordenados por Severidade

### CRÍTICOS (1)

#### AUD-W2C08-001 — Imagem do Figma não preservada em `docs/wave2-v4-c08/figma-reference.png`

**Arquivo/path:** `docs/wave2-v4-c08/figma-reference.png` (esperado, ausente)
**Descrição:** O prompt de execução do C08 (Seção 6.5) explicitamente exige que a imagem do Figma anexada ao prompt seja preservada como referência visual canônica no repositório. O analysis Section 11.3 linha 521 reconhece o requisito ("salvar a imagem do Figma anexada como referência permanente"). Após 8 commits no `wave2-v4/componente-08` e 1 commit na branch `wave2-v4-c08/analysis`, a imagem nunca foi salva. Isso torna **impossível** auditar fidelidade visual pixel-a-pixel — a auditoria atual confiou exclusivamente na descrição textual da analysis Section 5 e nas verbalizações dos ADRs 125-128.
**Recomendação:** o solicitante precisa fornecer a imagem original (do prompt de execução); commitá-la em `docs/wave2-v4-c08/figma-reference.png`. O dono sugerido para corrigir é a sessão de execução que recebeu o prompt original (somente ela tem acesso à imagem anexada). Este achado **bloqueia a aprovação** per regra explícita do prompt de auditoria.

### ALTOS (3)

#### AUD-W2C08-002 — `analysis.md` ausente da branch da entrega; link em CHANGELOG quebrado

**Arquivo/path:** `docs/wave2-v4-c08/analysis.md` (referenciado em `CHANGELOG.md:9159`)
**Descrição:** O analysis foi commitado em branch separada (`wave2-v4-c08/analysis`, commit `2f721cb`) e nunca foi mergeado/incorporado na branch da entrega (`wave2-v4/componente-08`). Resultado: o link em `CHANGELOG.md:9159` (`docs/wave2-v4-c08/analysis.md`) aponta para um arquivo que **não existe** quando o leitor está na branch da entrega. Quebra de rastreabilidade Gate 1 → Gate 2. Quem mergear o PR e for ler o changelog não acha o documento canônico.
**Recomendação:** mergear `wave2-v4-c08/analysis` em `wave2-v4/componente-08` (ou cherry-pick o commit `2f721cb`) ANTES do PR final, ou ajustar o link em CHANGELOG para apontar para a branch (`https://github.com/...wave2-v4-c08/analysis/...`). Decisão do Mario.

#### AUD-W2C08-003 — Zero testes Vitest novos no Gate 2 (analysis prometeu 5+)

**Arquivo/path:** `frontend/src/**` — sem novo arquivo `*.test.ts(x)` commit
**Descrição:** Analysis Section 12.1 (linhas 528-536) lista 5 categorias de teste Vitest que totalizam ≥ 18 testes específicos: formatRota (7 cenários), MetadataGrid render (3 cenários), AdminActions snapshot (10 cenários). Wave 1 v4.0 Audit Round 2 (AUD-W1V4-005) estabeleceu Vitest como padrão obrigatório do projeto, criando 15 testes para o middleware. Esta entrega contradiz esse padrão sem registro de exceção em DECISIONS.md.
**Recomendação:** adicionar antes do PR ao menos:
- 7 testes para `formatRota(rota)` cobrindo todos os 6 valores do enum + null
- 5 testes para `isPathActive(pathname, href)` (exact, prefix, prefix-trailing-slash, false-positive, undefined)
- 3 testes de smoke para a página de detalhe (render full / render legacy / render motivo_cancelamento)
Total mínimo: 15 testes. Custo: ~1h. Marco ALTO porque o desvio do padrão estabelecido está sem justificativa formal.

#### AUD-W2C08-004 — `--color-card-art-bg` ausente; `.artSlot` quase invisível contra `.cardInner`

**Arquivo/path:** `frontend/src/app/globals.css` (token ausente) + `frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css:290`
**Descrição:** Analysis Section 5.3 propôs token `--color-card-art-bg = #d9d9d9` (cinza médio, visível contra fundo claro). Token nunca foi criado. `.artSlot` usa `var(--color-card-surface, #d9d9d9)` mas `--color-card-surface = #e4e4e4` (globals.css:27). `.cardInner` no layout pai tem `background: #eaeaea`. Diferença de 6 unidades RGB. Em estado loading ou erro de imagem (frequente em produção: presigned URL leva 100-300ms; arte pode não existir mais no R2), o "quadrado de arte" do Figma fica praticamente invisível contra o fundo do card branco. Viola fidelidade visual descrita textualmente na analysis.
**Recomendação:** adicionar em `globals.css` o token `--color-card-art-bg: #d9d9d9;` e atualizar `detalhe.module.css:290` para usá-lo. Mudança de 2 linhas. Validar via smoke visual com prova legacy (cuja arte talvez não esteja mais no R2). Marco ALTO porque afeta UX em estado comum (loading/erro de imagem).

### MÉDIOS (4)

#### AUD-W2C08-005 — `.metaGrid` adiciona "Codigo:" como 7º item (fora do grid 3×2 do Figma)

**Arquivo/path:** `frontend/src/app/(dashboard)/provas/[id]/page.tsx:242-249`
**Descrição:** Figma (descrito na analysis Section 5.2.2) mostra grid 3×2 com 6 campos. Implementação adiciona um 7º item "Codigo: PRV-AAAA-MM-NNNNNN" em mono. ADR-127 menciona ("Codigo aparecendo no slot 7 quando disponivel") sem documentar como divergência consciente da imagem.
**Recomendação:** ou (a) remover o campo do metaGrid e exibir o `codigo_publico` em outro lugar (ex.: subtítulo do header ao lado de "Requerimento"), ou (b) registrar em ADR-127 como divergência aprovada do Figma com justificativa explícita. Resolve junto AUD-W2C08-006.

#### AUD-W2C08-006 — Layout responsivo ≤1100px deixa "Codigo" sozinho na última linha

**Arquivo/path:** `detalhe.module.css:614-617`
**Descrição:** `@media (max-width: 1100px)` reduz `.metaGrid` para `repeat(2, 1fr)`. Com 7 itens, isso cria 4 linhas: (Cliente/Rota), (Criada em/Vendedor), (Ciclo Atual/Status), (Codigo/—). Layout assimétrico contradiz o "blocado" pedido pelo Mario.
**Recomendação:** resolução combinada com AUD-W2C08-005. Se mantiver Codigo no grid, aplicar `grid-column: 1 / -1` (linha cheia em ambos os breakpoints).

#### AUD-W2C08-007 — `.title` font-size colapsa para 16px em viewports 768-1100px

**Arquivo/path:** `detalhe.module.css:106`
**Descrição:** `font-size: clamp(1rem, 2.5vw, 2.5rem)` — em 800px viewport, valor é 20px; em 768px, 19.2px. Figma textual indica ~36-40px para o título. Em viewports tablet (768-1100px) o título fica menor que `metaValue` (16px).
**Recomendação:** trocar para `clamp(1.5rem, 2.5vw, 2.5rem)` (mínimo 24px). Custo: 1 linha.

#### AUD-W2C08-008 — Falta seção dedicada em CLAUDE.md sobre página de detalhe e extensão para Wave 3

**Arquivo/path:** `CLAUDE.md`
**Descrição:** O prompt de auditoria Section 4.10 esperava seção "Página de detalhe de prova: estrutura e extensão". Hoje há apenas a entrada na tabela de Waves. Para Wave 3 expandir Timeline para 14 estados sem ler todo o código fonte, falta documento operacional. CLAUDE.md já tem uma seção análoga para `rota_enum` — replicar o padrão para `StatusProvaEnum`.
**Recomendação:** adicionar ~30 linhas em CLAUDE.md cobrindo: lista das 4 camadas (Python, Pydantic, Postgres, TypeScript) que precisam ser sincronizadas, como `STATUS_LABELS`/`STATUS_LABELS_SHORT` se mantêm consistentes, como `Timeline.tsx` flags são derivadas e quando expandi-las, ponto de extensão em `state_machine.py`.

### BAIXOS (5)

#### AUD-W2C08-009 — `.artImg` `object-fit: cover` corta artes retangulares

**Arquivo/path:** `detalhe.module.css:298`
**Recomendação:** considerar `object-fit: contain` se artes são tipicamente retangulares; consultar Mario.

#### AUD-W2C08-010 — `formatStatus` é wrapper trivial sem agregar valor

**Arquivo/path:** `page.tsx:39-41`
**Recomendação:** remover; usar `STATUS_LABELS[prova.status]` direto.

#### AUD-W2C08-011 — `formatRota(null) = "—"` é discreto mas críptico para usuário novo

**Arquivo/path:** `page.tsx:30-37`
**Recomendação:** opcionalmente envolver em `<span title="Prova legacy v3.0 — rota será backfilled na Wave 7">—</span>`.

#### AUD-W2C08-012 — `isPathActive` sem teste apesar de impactar destaque global

**Arquivo/path:** `layout.tsx:90-94`
**Recomendação:** adicionar teste unitário (5 casos). Já contemplado em AUD-W2C08-003.

#### AUD-W2C08-013 — Smoke E2E manual obrigatório listado mas não executado

**Arquivo/path:** `CHANGELOG.md:9210-9231`
**Recomendação:** executar antes do PR; documentar em `docs/wave2-v4-c08/smoke-validation.md`. Status atual em CLAUDE.md: "aguarda smoke visual humano + PR".

### INFOs (3)

#### AUD-W2C08-014 — Distribuição em produção mostra 65% provas legacy, 6% v4.0 nova

**Implicação:** redesenho do detalhe é exercitado dominantemente em provas com `rota IS NULL`. Tratamento "—" é norma.

#### AUD-W2C08-015 — Cloudflare R2 não tocado (escopo respeitado)

**Implicação:** sem novos buckets, workers ou KV.

#### AUD-W2C08-016 — Advisors sem novos alertas após C08

**Implicação:** apenas 2 INFOs/WARNs pré-existentes (alembic_version + auth_leaked_password). 13 INFO `unused_index` esperados em volume baixo. Saúde de infra preservada.

---

## Recomendações de Próximos Passos

### Ações requeridas antes de prosseguir (bloqueantes)

1. **Solicitante anexar a imagem do Figma original** ao próximo prompt de correção; sessão de execução commit-a `docs/wave2-v4-c08/figma-reference.png` (resolve AUD-W2C08-001).
2. **Mergear branch `wave2-v4-c08/analysis` em `wave2-v4/componente-08`** OU ajustar link em CHANGELOG para URL do GitHub (resolve AUD-W2C08-002).
3. **Adicionar mínimo 15 testes Vitest** (formatRota×7 + isPathActive×5 + render smoke×3) (resolve AUD-W2C08-003).
4. **Criar token `--color-card-art-bg = #d9d9d9` em globals.css** e usar em `.artSlot` (resolve AUD-W2C08-004).

### Ações recomendadas, não bloqueantes

5. Resolver `Codigo:` no metaGrid: ou tirar do grid, ou registrar como divergência consciente em ADR-127 (resolve AUD-W2C08-005 + 006).
6. Ajustar `.title` para `clamp(1.5rem, 2.5vw, 2.5rem)` (resolve AUD-W2C08-007).
7. Adicionar seção "Página de detalhe" em CLAUDE.md (resolve AUD-W2C08-008).
8. Executar e documentar smoke E2E manual (resolve AUD-W2C08-013).

### Itens de backlog técnico

9. Revisitar `object-fit: cover` para artes retangulares — consultar Mario (AUD-W2C08-009).
10. Remover wrapper trivial `formatStatus` (AUD-W2C08-010).
11. Tooltip explicativo no em-dash de prova legacy (AUD-W2C08-011).
12. Resolver `_clicheria_divergence_note` (open desde Wave 1 v4.0 — não C08).

### Pré-requisitos que a Wave 3 precisará verificar

- **Timeline.tsx orientada a dados:** ✅ confirmada nesta auditoria. Adicionar 4 estados COM_MOTORISTA_MATRIZ / COM_MOTORISTA_FILIAL / LAMINANDO_MATRIZ / LAMINANDO_FILIAL exigirá apenas: (a) novo valor em `StatusProva` (TS + Python enum), (b) novo mapping em `STATUS_LABELS`/`SHORT`, (c) atualizar `state_machine.TRANSICOES` + `ATORES_POR_TRANSICAO`, (d) opcional: expandir `Timeline.tsx` flags se o estado precisar de cor distinta.
- **Trigger imutabilidade ativo:** ✅ verificado (`trg_provas_rota_imutavel` ativo).
- **`isRoteamento` flag em Timeline:** hoje é `sNovo === "APROVADA_PELO_VENDEDOR"`. Wave 3 v4.0 expandirá: badge de rota também aparecerá em transições de motorista (COM_MOTORISTA_MATRIZ etc.). Decisão fora do escopo C08.
- **Provas legacy (`rota IS NULL`):** continuam navegáveis. Wave 7 (Componente 21) fará backfill. Até lá, "—" é o tratamento.

---

## Anexos

### A.1 — Output do MCP Supabase (read-only)

```
list_projects → 1 projeto (rwxlpwmnkekzuurgthkr, sa-east-1, Postgres 17, ACTIVE_HEALTHY)

provas_digitais columns: id, nome, nro_requerimento, cliente, vendedor_id, imagem_url,
qr_code_hash, status, rota (USER-DEFINED nullable), ciclo_atual, motivo_cancelamento,
created_at, updated_at, codigo_publico (NOT NULL)

triggers (provas_digitais + movimentacoes):
  - trg_movimentacoes_imutavel BEFORE DELETE/UPDATE
  - trg_provas_rota_imutavel BEFORE UPDATE
  - trg_provas_updated_at BEFORE UPDATE

indexes movimentacoes: 7 total (incluindo idx_movimentacoes_prova, idx_movimentacoes_prova_data,
idx_movimentacoes_prova_ciclo, idx_movimentacoes_status_novo_created_at)

policies (provas_digitais + movimentacoes):
  - pol_provas_select (admin OR self_vendedor OR motorista_em_transito OR clicheria_states)
  - pol_provas_insert (admin)
  - pol_provas_update (admin)
  - pol_movimentacoes_select (admin OR via JOIN provas OR usuario_id self OR motorista OR clicheria)
  - pol_movimentacoes_insert (admin)

distribuição: 17 provas, 11 NULL (65%), 1 MATRIZ v4.0, 5 legacy v3.0
status: CANCELADA=7, CRIADA=6, RECEBIDA_PELA_CLICHERIA=2, REPROVADA=2
movimentações: 16 totais, max 4/prova, max ciclo=2, 1 prova reiniciada (66f36e8b)
status_novo distintos: 7 (todos mapeados em STATUS_LABELS)

EXPLAIN ANALYZE detail query: Seq Scan, 0.121 ms execution

advisors security: 1 INFO + 1 WARN (pré-existentes)
advisors performance: 13 INFO unused_index (pré-existentes, esperados em volume baixo)

usuários ativos: 4 (2 admin STUDIO + 2 vendedores) — sem MOTORISTA/CLICHERIA em produção
```

### A.2 — Diffs amostrais examinados

```
git log --oneline development..wave2-v4/componente-08
  eb9e46c docs(wave2-v4/c08): registrar 3 iteracoes pos-Figma no CHANGELOG
  80388da fix(wave2-v4/c08): centralizar verticalmente info em relacao a arte
  fd2bb24 fix(wave2-v4/c08): reduzir arte 480px->380px e apertar gaps (Figma)
  a2174e3 fix(wave2-v4/c08): manter botoes da actionsRow na mesma linha (sem quebra)
  b59345c docs(wave2-v4/c08): CHANGELOG + DECISIONS + CLAUDE.md
  969e080 feat(wave2-v4/c08): redesign visual da pagina de detalhe da prova
  9640ef5 feat(wave2-v4/c08): destacar Provas no menu em /provas/[id]
  d748269 refactor(wave2-v4/c08): renomear CRIADA->Aguardando vendedor + simplificar legacy

git diff --stat development..wave2-v4/componente-08
  CHANGELOG.md                           111 ++++
  CLAUDE.md                                1 +
  DECISIONS.md                           199 ++++++
  frontend/.../layout.tsx                 18 ++-
  frontend/.../[id]/detalhe.module.css   254 +/-/-
  frontend/.../[id]/page.tsx             172 +/-/-
  frontend/src/lib/types/prova.ts         23 +-
```

### A.3 — Cenários reproduzidos mentalmente com resultado

| Cenário | Reprodução mental | Resultado esperado | Confirmação na auditoria |
|---|---|---|---|
| Renderização prova legacy (`rota: null`) | `formatRota(null)` em page.tsx:30-37 | retorna "—" sem quebrar | ✅ código confirma |
| Renderização prova com 4 ciclos hipotéticos | `Timeline.tsx:98-111` agrupa por `ciclo`; renderiza com `cycleLabel` "Ciclo X" | label visível, separador `border-top: dashed` entre ciclos | ✅ |
| Renderização prova histórico vazio | `Timeline.tsx:163-172` | empty state literal "Esta prova ainda nao teve movimentacoes." + hint | ✅ código confirma |
| Renderização prova com `motivo_cancelamento` | `page.tsx:252-257` | banner full-width vermelho-suave abaixo do metaGrid | ✅ |
| Renderização botão Reiniciar para 3Studio + REPROVADA | `AdminActions.tsx:106 podeReiniciar=true` | botão "Reiniciar ciclo" visível | ✅ |
| Renderização botão Reiniciar para 3Studio + CRIADA | `podeReiniciar=false` (status mismatch) | botão oculto | ✅ |
| Renderização para vendedor + sua prova | `useAuthorization("provas.cancel/restart").hasAccess=false` | `AdminActions:102 return null` — apenas Visualizar/Baixar visíveis | ✅ |
| Acesso direto a prova alheia (vendedor) | RLS retorna 0 rows; backend retorna 404; useProvaDetail traduz para "Prova nao encontrada." | mensagem genérica sem vazar info | ✅ |
| Carregamento simultâneo de detail + imagem-url + movimentações | `Promise.allSettled` 3-way | prova obrigatória, imagem/movs toleradas | ✅ |
| Race condition de reload | `latestReqRef` filtra resultados antigos | apenas o load mais recente atualiza estado | ✅ |
| Mobile ≤768px | `mobileNotice` aparece, `desktopOnly` esconde | mensagem "acesse versao desktop" | ✅ código confirma |
| `/provas/[id]` destaque do menu | `isPathActive(pathname, "/provas")` retorna true para subpath | item "Provas" amarelo no menu | ✅ ADR-128 + código |
| Prova com 2 ciclos | `groupByCycle` em Timeline divide em 2 grupos | label "Ciclo 1" + "Ciclo 2" | ✅ |
| `STATUS_LABELS["CRIADA"]` em listagem | `provas/page.tsx` usa `STATUS_LABELS_SHORT["CRIADA"] = "Aguardando"` | filtro Status mostra "Aguardando" | ✅ ADR-125 |
| `ROTA_LABELS["DIRETA"]` em filtro | `provas/page.tsx` filtro Rota: "Direta" sem sufixo | ✅ ADR-126 |

---

**Fim do Relatório de Auditoria.**

**Resumo final:** 1 CRITICAL · 3 ALTOS · 4 MÉDIOS · 5 BAIXOS · 3 INFOs = 16 achados.

**Veredito:** REPROVADO E REFAZER (CONDICIONAL) — correções estimadas em ≤ 1h-2h. Após corrigir os 4 itens bloqueantes (figma-reference, analysis na branch, ≥15 testes Vitest, token de cor da arte), o C08 está pronto para PR para `main`.
