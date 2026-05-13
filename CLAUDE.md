# Rastreio de Provas Digitais

Sistema de rastreamento de provas digitais (artes graficas) para a 3Studio.
Acompanha o ciclo de vida completo: criacao, aprovacao, transporte e entrega a clicheria,
com QR Code, assinatura digital de cada movimentacao e auditoria imutavel.

---

## Progresso das Waves

| Wave | Status | Escopo | Sessoes |
|------|--------|--------|---------|
| **0 — Infra** | ✅ **COMPLETA** | Schema Postgres (6 tabelas de dominio + enums + triggers imutabilidade), RLS inicial, R2 bucket, keep-alive cron, CI/CD | 1 |
| **1 — Auth + RBAC** | ✅ **COMPLETA** (sign-off Sessao 6) | Supabase Auth (ES256 JWKS), CRUD de usuarios com saga auth↔DB, RLS `is_admin=true`, tela `/usuarios` | 1-6 |
| **2 — Nucleo do Dominio** | ✅ **COMPLETA** (sign-off Sessao 22 pos-auditoria externa) | Cadastro de prova + etiqueta + QR Code (C06), Listagem com filtros (C07), Detalhe + modal etiqueta/QR (C08), Configuracoes do sistema (C09) | 7-22 |
| **3 — Scanner + Transicoes** | ✅ **COMPLETA** + Review C11 + Auditoria Senior | Camera HTML5, scanner QR, assinatura digital, maquina de estados, reprovacao, roteamento, timeline visual (C12), cancelamento admin (C13), reinicio de ciclo admin (C14). Review C11: bugs stale error, canvas responsivo, modal fluido, entrada manual de codigo QR. Auditoria: 0 CRITICAL, 3 HIGH corrigidos (scan filter admin, getToken try/catch, focus trap modais) | 23+ |
| **4 — Dashboard + Atrasos** | ✅ **COMPLETA** + Auditoria Senior | Dashboard tempo real (RF-014, US-013) com layout Figma: 5 contadores (criadas hoje, com vendedor, aprovadas, na clicheria, atrasadas c/ breakdown por vendedor) + 2 atalhos rapidos. Query consolidada + cache TTL 5s (ADR-092). Calculo de atraso horas corridas (RN-008). Supabase Realtime (postgres_changes) + fallback polling 10s. Auditoria: 0 CRITICAL, 1 HIGH corrigido (click Na clicheria), 2 MEDIUM corrigidos (breakpoint mobile, GROUP BY), 2 LOW corrigidos (ValueError guard, CHANGELOG). ADR-094 | — |
| **5 — Relatorios + Atalhos** | ✅ **COMPLETA** + Visual Refresh + 2 rounds de Auditoria Senior | Componente 16 (Relatorios) + Componente 17 (Atalhos). Endpoint UNICO discriminado por scope (geral/3studio/vendedores/clicheria) com cache TTL 60s + ETag SHA-256 + Realtime invalidation (4 camadas, ~20x reducao queries) + bypass `?_force=1` (ADR-107). Frontend `/relatorios` com 4 perspectivas alinhadas ao design Mario, graficos SVG inline interativos (DonutChart com toggle ADR-108 + BarChart + TimeSeriesChart + Sparkline + DeltaBadge). 5 filtros UI completos por construcao (RotaFilter + StatusFilter + VendedorFilter + DateRangeFilter + SearchInput — RF-013, ADR-106). CSV streaming UTF-8 BOM com 4 datasets enriquecidos (taxas + tempo medio por vendedor — L-A1 Round 2) + audit `REPORT_EXPORTED`. Atalhos globais por teclado (g+s, g+p, g+r admin, ?) + 3º card "Acessar Relatorios" no dashboard. **Round 2 de auditoria senior** (2026-04-29) corrigiu H-A1 (Q4 do `_aggregate_geral` agora aplica filtros via JOIN + `_aplicar_filtros_provas`), M-A1 (Q5 do `_aggregate_3studio` cancelamentos_top tambem), M-F1 (a11y modal sem `aria-hidden` no overlay), L-A1 (CSV summary expoe taxas) e L-F1 (`useMemo` em visibleShortcuts) — ADR-109. ADRs 095-109 (095-101 closeout + 102-105 visual refresh + 106-108 audit Round 1 + 109 audit Round 2). Migration 010 (recovery) + 011 (clarify descricao). **639 testes** (era 424); 0 regressao. | 5.0-5.6 + Visual Refresh + Audit R1 + Audit R2 |
| **6 — Seguranca e Auditoria** | ✅ **COMPLETA** + UX iteration + Auditoria Senior | Componente 18 (Interface de Log de Auditoria) — RNF-005. 3 endpoints `/api/v1/audit-log` (listagem paginada com filtros, detalhe com `MovimentacaoSnapshot`, by-prova). Frontend `/auditoria` admin-only com filtros (busca, tipo_evento semantico, ator, periodo), drawer lateral com focus trap, atalho `g a`, badges coloridos por categoria (reprovacao/reinicio/cancelamento/criacao). RLS 008 (REVOKE INSERT/UPDATE/DELETE em `audit_logs` para `anon`/`authenticated` — defesa em profundidade RNF-005, terceira camada apos trigger e RLS deny-by-default). UX iteration pos-Gate 2: presets de data (Hoje/7d/30d/90d), tipo_evento (6 categorias semanticas), paginacao numerada com janela inteligente, sticky header, ordenacao clicavel, page size selector (whitelist + tiebreaker por id). Auditoria Senior (2026-04-29): 0 CRITICAL, 2 HIGH (focus trap + F401 unused), 4 MEDIUM (ruff I001 + Pydantic 422 + Pragma legacy + OUTERJOIN condicional), 4 LOW (shadowing id + magic number + label botao + catch silencioso) — todos corrigidos. ADRs 110-114. **724 testes** (era 633); 0 regressao. | — |
| **v4.0 W1 — RBAC Matriz** | ✅ **COMPLETA** | Componente 05 (atualizacao v4.0) — Matriz de Acesso por Perfil em 3 camadas independentes. SSoT em `shared/access-matrix.json` (12 regras x 4 perfis = 48 celulas). Camada Python: `backend/app/access/` (matrix + enforce + scopes + guards) + 36 testes. Camada Frontend: `lib/access-matrix.ts` + `lib/hooks/use-authorization.ts` + `components/Restricted` + `components/AuthToast` + middleware reescrito com lookup de perfil + cache LRU 30s + cookie `auth-toast` em redirect. Camada RLS: 4 migrations (009-012) — helpers SECURITY DEFINER em schema `app_private` (resolve advisor `*_security_definer_function_executable`) + rebase das 12 policies + extensao de `pol_etiquetas_select` para Motorista/Clicheria (lacuna L-RLS-1). Refactor coordenado: substituicao de `Depends(get_admin_user)` por `Depends(access_required(rule_key))` em audit_log/reports/configuracoes/users/provas; `_scoping_filter` delega para `scope_filter_for`; `require_role` removido. Frontend: guards proativos em /auditoria, /relatorios (promovido de reativo), /usuarios, /configuracoes, /nova-prova; layout consulta Matriz para esconder itens; `useGlobalShortcuts` deriva da Matriz. Validado via `scripts/verify_rbac_equivalence.py` em producao (3 camadas batem: admin 16/16, vendedor 0, motorista 0, clicheria 2). **757 testes** (era 724 + 36 novos - 3 removidos). Decisao a confirmar: Clicheria PARCIAL com scope `status_clicheria` mantida (Matriz literal diz FULL — registrado follow-up). | — |
| **v4.0 W1 — Audit Fixes** | ✅ **COMPLETO** | Auditoria critica + metodica do trabalho da Wave 1 v4.0 (2026-04-30, commit `ac3be70`). Findings: 0 CRITICAL · 2 HIGH · 6 MEDIUM · 8 LOW. Corrigidos os 2 HIGH (H-1 middleware sem `ativo` no select permitia user desativado passar; H-2 cookie `auth-toast` sem `Secure` em prod) + 5 MEDIUM (M-1 flash de UI proibida nas 5 pages durante carga do `/users/me` — `if (auth.loading) return null` antes do guard; M-2 `_load_matrix` Python valida scope/acesso/match com FAIL FAST + 4 testes novos; M-3 `buildRules` TS valida runtime com paridade ao Python; M-4 `getRuleForPath` normaliza trailing slash defensivamente; M-5 etapa [4/4] do `verify_rbac_equivalence.py` agora asserta de verdade — confronta Matriz Python com counts RLS para 48 celulas). Tests: **761** (era 757 + 4 novos M-2). Smoke preview validou redirect anonimo + trailing slash. Script verify rodou em producao: SUCESSO. ADRs novos: D-6 (validacao runtime FAIL FAST do JSON SSoT em ambos os lados) + D-7 (trailing slash normalizado defensivamente em `getRuleForPath`). Follow-up registrado: M-6 + L-1..L-8. | — |
| **v4.0 W1 — Audit Round 2** | ✅ **COMPLETO** | Auditoria sênior independente pos-Audit Fixes (2026-04-30, commit `09eaf78` em `wave1-v4/audit`). Veredito: APROVADO COM CORRECOES. Findings: **0 CRITICAL · 0 ALTO · 6 MEDIUM · 7 BAIXO · 4 INFO**. Sessao de correcao 2026-05-04 (`wave1-v4/fixes/execution`) corrigiu **17/17 achados** em 13 commits atomicos. **MEDIUM**: AUD-001+006 (CLAUDE.md snippet pos-M-1), AUD-002 (verify script cobre 6 tabelas — promove M-6), AUD-003 ([4/4] valida (rule,profile,table) triple), AUD-004 (rename test_matrix_rls_equivalence -> _python_), AUD-005 (Vitest minimo + 15 testes do middleware — promove L-1). **BAIXO**: AUD-101 (RLS 013 REVOKE TRUNCATE audit_logs — 4a camada RNF-005), AUD-102+103 (CLAUDE.md notas), AUD-104 (useCurrentUser runtime guard de setor), AUD-105 (provas.detail key em endpoints de detalhe), AUD-106 (D-8 _scoping_filter shim status formal de L-2), AUD-107 (comentario script — junto com AUD-003). **INFO**: AUD-201..204 registrados como D-9..D-12 em DECISIONS. **Validacao**: backend pytest 176/176 nos modulos tocados; frontend Vitest 15/15; verify_rbac_equivalence em producao SUCESSO (24 cells governadas + 32 sanity); RLS 013 aplicada via MCP — `has_table_privilege('authenticated','audit_logs','TRUNCATE') = false`; advisors sem novos alertas. ADRs novos: D-8 (_scoping_filter shim) + D-9 (invariante dashboard×home_by_profile) + D-10 (registro orfao improvavel) + D-11 (RLS rastreada via supabase_migrations+Git) + D-12 (extracts removidos por design) + D-13 (Vitest minimo Opcao A). | — |
| **v4.0 W2 — C06 Cadastro com Rota** | ✅ **COMPLETO** | Componente 06 (atualizacao v4.0) — Cadastro de Prova com Selecao de Rota + Etiqueta com Codigo Textual. **Migration 012** (alembic_version=012): ALTER TYPE rota_enum ADD VALUE 4 novos (`MATRIZ`/`LAM_MATRIZ`/`FILIAL`/`LAM_FILIAL` — UPPERCASE, ADR-115); legacy `PADRAO`/`DIRETA` permanecem ate Wave 7. ADD COLUMN `codigo_publico VARCHAR(20) UNIQUE NOT NULL` formato `PRV-AAAA-MM-NNNNNN` (DAT v3.0 §8.3, ADR-116). Backfill local das 16 provas existentes na propria migration. UNIQUE INDEX `idx_provas_codigo_publico` + INDEX `idx_provas_rota`. Trigger `trg_provas_rota_imutavel` permite NULL→valor (Wave 7) e bloqueia valor→outro_valor / valor→NULL com SQLSTATE 22023 (ADR-117). **Backend**: `codigo_publico_service.py` (gerar com CSPRNG `secrets.choice` + alfabeto 31 chars sem 0/O/1/I/L); `RotaCriacaoEnum` Pydantic bloqueia legacy na criacao; `qrcode_service.gerar_payload_qr` embute `codigo_publico` no segundo campo (DAT §8.1 — idempotencia camera↔digitacao manual via Componente 19 da Wave 3 v4.0); `etiqueta_service.gerar_pdf` renderiza codigo abaixo do QR + badge da rota no rodape; `state_machine.executar_transicao` modificacao cirurgica autorizada (ADR-119 — preserva rota se ja preenchida; deriva apenas em prova legada `rota=NULL`). Handler `POST /api/v1/provas/` persiste `body.rota` + `codigo_publico`; removeu `rota_projetada` do response. **Frontend**: `nova-prova/page.tsx` REWRITE COMPLETO seguindo print do design — canvas com grid de pontos + blob amarelo + onda; topbar pill+botoes; box branco da ficha com 2 toggles (segment Matriz/Filial + switch Laminacao — ADR-118 — derivam as 4 rotas no submit); cards laterais (Unidade Selecionada + cole imagem com paste handler real ⌘V); footer ORIGEM/STATUS. Tipos atualizados (Rota com 6 valores + RotaCriacao com 4 + ROTA_LABELS); detalhe da prova exibe codigo_publico em mono. **Testes**: 795 (era 781 + 14 novos — 20 do `test_codigo_publico_service` + 14 do `test_provas_api_v4`); 0 regressao Wave 0..6 + Wave 1 v4.0. Frontend `tsc --noEmit` exit 0; `next build` 13/13 paginas OK. ADRs 115-119. | — |
| **v4.0 W2 — C06 Visual Refresh v2** | ✅ **COMPLETO** | Segundo refresh visual da pagina `/nova-prova` apos feedback do Mario com novo print Figma (frontend-only, zero backend touch). **Diagnostico v2**: a v1 (mesmo dia) ainda nao alinhava — usava layout 2-col (380px ficha + 1fr `EtiquetaPreview` SVG) que deixava o box branco com so 380px; `.canvas::before` com `inset: calc(-1 * var(--card-padding))` desenhava pattern de pontos vazando POR FORA do `.canvas` simulando "card branco sumiu"; topbar `position: absolute` sem `.pageHeader` (fora do padrao das outras paginas); composto `segment(2) + switch(laminacao)` em vez dos 4 botoes diretos do design; dropzone com `min-height: 64px`. **Estrutura nova**: 1 box branco unico `.ficha { flex: 1; padding: 2.25rem 2.75rem; radius: --radius-card-xl }` preenche tudo abaixo do `.pageHeader` (espelho de `/usuarios` — h1 grande a esquerda + botao "Cadastrar prova" amarelo a direita); 2 fieldRow grid 2-col (Nome/Req, Cliente/Vendedor) com inputs 48px; segment de 4 botoes diretos (Matriz \| Filial \| Lam. Matriz \| Lam. Filial) com pill preto animado via `framer-motion` `layoutId="rota-pill"` (spring bounce 0.2 · 350ms); dropzone com classe dedicada `.anexoField { flex: 1 }` que cresce ate o limite inferior do box (sem `min-height` rigido — acompanha o espaco disponivel sem transbordar). **Removidos** (~340 linhas entre TS+CSS): `EtiquetaPreview` SVG inteiro (216 linhas) + helpers (`truncar`, `vendedorSelecionado`/`vendedorNome`); `.canvas::before` pattern de pontos; `.topbar position: absolute`; `.layout` 2-col + `.center` + `.etiquetaWrap`/`Paper`/`Svg`; `.fichaTitle` (titulo migrou para `.pageTitle` no header); composto `Origem` type + `deriveRota()` helper + `rotaDerivada` useMemo (`FormState` agora armazena `rota: RotaCriacao` direto); `.toggleRow`/`.switch*`/`.segmentIcon`/`.anexoHead`/`.anexoMeta` rules; hint "imutavel apos cadastro"; pasta `frontend/public/etiqueta/` (logos orfaos apos remocao do `EtiquetaPreview`). **ADRs 118, 120, 121 marcados SUPERSEDIDO**. **Validacao**: tsc 0 · `next build` 13/13 · `/nova-prova` em **6.79 kB / 209 kB** (era ~9.18 kB / 211 kB — -2.39 kB / -2 kB First Load por causa da remocao do SVG inline). Smoke visual confirmado pelo Mario antes do commit. | — |
| **v4.0 W2 — C06 Visual Refresh** | ✅ **COMPLETO** (superseded por Visual Refresh v2) | Refresh visual completo da pagina `/nova-prova` (frontend-only, zero backend touch). **Diagnostico**: a entrega anterior tinha `.canvas` com `height: calc(100vh - 64px)`, `padding: 12px` e `background: #fafaf7` que conflitavam com o `.cardInner` do layout — efeito de "retangulo flutuante" sem preencher o box do card. **Correcoes estruturais**: `.canvas { height: 100% }` puro (igual `/dashboard`); topbar virou `position: absolute; top: 0; right: 0` (botao "Cadastrar prova" flutua no canto superior, ficha estende ate a mesma linha); ficha com `justify-content: center` (conteudo verticalmente centralizado); layout 2 colunas `380px 1fr` (era 3 colunas com cards laterais). **Tokens canonicos**: substituicao de TODAS as cores/tipografias/radius hardcoded por `var(--color-accent)`, `var(--color-card-surface)`, `var(--color-card-text)`, `var(--radius-pill)`, `clamp(...)`. **Tipografia Title Case** (NOME→Nome, REQUERIMENTO→Requerimento, ROTA→Rota, ANEXO→Anexo, ORIGEM→Origem); removido `text-transform: uppercase` + `letter-spacing` agressivo dos labels. **Removidos** (~340 linhas entre TS+CSS): timestamp pill, botao "Salvar rascunho", eyebrow "FICHA DE CADASTRO", footer "ORIGEM/STATUS", cards laterais "Unidade selecionada"+"Cole imagem", `RotaVisualization` SVG decorativo, `VIZ_NODES`+`buildVizPath`+`VizPoint`+`UNIDADES_INFO`+`MatrizIcon`+`FilialIcon`+`OrigemNodeIcon`+`LaminationIcon`+`QR_DOTS`+`FinderPattern`+`ROTA_BADGE_LABELS_PREVIEW`+`ROTA_BADGE_W_PREVIEW`. **EtiquetaPreview** (ADR-120): substitui o SVG decorativo por uma replica fiel da etiqueta 90×57mm que sai impressa, espelhando `etiqueta_service.py` mm-a-mm — logos reais (`logo_3studio.svg` + `logo_studio_e_arte.svg`) copiados de `backend/app/services/etiqueta_assets/` para `frontend/public/etiqueta/`; campos Nome/Requerimento/Vendedor com live update (truncados se necessario para nao quebrar o SVG); QR como placeholder vazio (apenas o quadrado com cantos arredondados); rodape com ano + "Etiqueta de rastreio". Sem codigo publico (PRV) e sem badge da rota no preview — esses ficam apenas no PDF impresso real. **Type safety** (ADR-122): adicionado `AllowedImageType` type literal + `isAllowedImageType` type guard em `lib/types/prova.ts`; eliminados todos os `as` agressivos em `page.tsx` e `useCreateProva.ts` (substituidos por `instanceof HTMLInputElement \| HTMLTextAreaElement \| HTMLSelectElement` checks e o type guard); apenas `as const` literais permanecem. **Animacoes**: Framer Motion stagger entre topbar/ficha/visualizacao na entrada (ENTER_EASE = `[0.32, 0.72, 0, 1]`), `AnimatePresence` no crossfade form↔sucesso (200ms), respeito a `prefers-reduced-motion`. **Sem touch**: backend, RLS, migrations, RBAC, hooks compartilhados, layout dashboard, `useCreateProva` (so 1 linha mudada para usar o helper). **Validacao**: `npx tsc --noEmit` exit 0; `npx next build` 13/13 paginas; `/nova-prova` em ~9 kB / 211 kB First Load (era 6.34 kB / 169 kB — overhead Framer Motion + EtiquetaPreview SVG). ADRs 120-122. | — |
| **v4.0 W2 — C06 Audit Fixes** | ✅ **COMPLETO** | Auditoria sênior independente pos-Wave 2 v4.0 (2026-05-05, commit `1b47290` em `wave2-v4/audit`). Veredito: REPROVADO E REFAZER — 2 CRITICAL bloqueantes (AUD-W2V4-001 reinicio zera rota disparando trigger SQLSTATE 22023; AUD-W2V4-002 branch development build-broken com helper `isAllowedImageType` uncommitted). Findings: **3 CRITICAL · 7 HIGH · 4 MEDIUM · 8 LOW · 4 INFO = 26 totais**. Sessao de correcao 2026-05-05 (`wave2-v4/fixes/execution`) corrigiu **22/22 acionaveis em 15 commits atomicos** + 4 INFO confirmados/registrados. **CRITICAL**: AUD-001+A01+006+007 (state_machine reinicio agora preserva `rota_antes` em vez de zerar — completa modificacao cirurgica do ADR-119; commit `cbd6506`); AUD-002+D01+D02 (commit dos 3 frontend uncommitted + nota anexo Visual Refresh v1; tsc + next build re-validados; commit `1a88ab8`). **HIGH**: AUD-T01 (suite `test_imutabilidade_rota.py` 5 cenarios banco real — Wave 7 readiness automatizada); AUD-T02 (suite `test_rota_enum_drift.py` 5 testes confrontando Python↔Postgres↔TS↔Pydantic — confirma zero drift atual); AUD-T03 (suite `test_migration_012.py` 3 testes upgrade/downgrade/idempotencia); AUD-A02+M03 (default `INITIAL_FORM.rota=""` + texto auxiliar restaurado — mitigacao "Confusao operacional" Backlog v4.0 §6); AUD-M01 (`schema.sql` reescrito refletindo `alembic_version=012` + 3 chunks MCP); AUD-003 (docstring `codigo_publico_service` corrigida — trigger nao protege codigo). **MEDIUM**: AUD-004 (handler `criar_prova` com retry 3x em colisao de `idx_provas_codigo_publico` + classificacao por constraint_name); AUD-005 (docstring `validar_payload_qr` documenta contrato polimorfico segundo campo); AUD-M02 (CLAUDE.md + docstring migration 012 documentam divergencia 3 chunks MCP); AUD-T04 (smoke E2E manual obrigatorio antes do merge — 11 itens de checklist). **LOW**: AUD-S01 (gerar_payload_qr rejeita identificador com `\|`); AUD-007 (audit log de reinicio agora grava `rota_depois=rota_antes.value`); AUD-P03 (`lru_cache` em `_check_assets`; cache de bytes WONTFIX-parcial); AUD-M04 (bloco "Pos-supersedimento" no ADR-120); AUD-T05 (200 → 10k amostras unicidade); AUD-D01+D02 (anexo + re-validacao). **INFO**: S02/S03/P01/P02 confirmados/follow-up. **Validacao**: backend pytest **805 passed + 9 skipped** (era 795 + 0; +19 novos -- 2 AUD-001 + 5 T01 + 5 T02 + 3 T03 + 3 AUD-004 + 1 S01); 9 skipped sao integrados sem `INTEGRATION_DATABASE_URL`. tsc --noEmit exit 0; next build 13/13 paginas; `/nova-prova` 6.84 kB / 209 kB. Advisors MCP sem novos alertas. ADRs novos: ADR-123 (reinicio preserva rota completa modificacao cirurgica do ADR-119) + ADR-124 (default vazio + texto auxiliar — substitui mitigacao descartada em ADR-118 SUPERSEDIDO). Recomendacao final: **PR pronto para merge condicional** (smoke E2E manual obrigatorio + nova auditoria independente em sessao separada apos merge para validar resolucao + ausencia de regressao + Wave 7 viavel). | — |
| **v4.0 W2 — C08 Visualizacao de Prova (atualizacao v4.0)** | ✅ **COMPLETO** (aguarda smoke visual humano + PR) | Componente 08 (atualizacao v4.0) — Visualizacao de Prova com Redesign + Suporte a Exibicao de Rota. Gate-based two-stage com 4 ambiguidades visuais resolvidas pelo Mario (A1: `STATUS_LABELS["CRIADA"]` -> "Aguardando vendedor" global; A2: `actionsRow` com 2/3/4 botoes side-by-side via `flex: 1 1 220px`; A3: rotas legacy `PADRAO`/`DIRETA` perdem sufixo "(legada v3.0)" e viram "Padrao"/"Direta"; A4: `isPathActive` por prefix-match destaca "Provas" em `/provas/[id]`). Frontend-only — zero touch em backend, RLS, migrations. Layout invertido (arte esquerda 480px · info direita 1fr) + header com "Requerimento: NNN" pequeno + nome grande + divisor + grid 3x2 de metadata (Cliente · Rota · Criada em / Vendedor · Ciclo Atual · Status) + Codigo em mono como item adicional + banner full-width de cancelamento + linha de acoes. Card preto do historico passa a ser secao separada (era aninhada no innerCard branco). Timeline.tsx **nao tocada** — ja era orientada a dados (preparada para Wave 3 v4.0). AdminActions.tsx **nao tocada** — `useAuthorization` integrado desde Wave 1 v4.0. **Validacao**: tsc --noEmit exit 0; next build 13/13 paginas; `/provas/[id]` em **11.4 kB / 209 kB** First Load (era ~10 kB — overhead pelo import de `STATUS_LABELS`/`StatusProva` e novos seletores CSS). Advisors MCP sem novos alertas. ADRs 125-128. Smoke visual humano obrigatorio antes do PR (preview programatico nao tem auth). | — |
| **v4.0 W2 — C08 Audit Fixes** | ✅ **COMPLETO** (mergeado em `development`) | Auditoria sênior independente pos-C08 v4.0 (2026-05-06, commit `d90c672` em `wave2-v4-c08/audit`). Veredito: REPROVADO E REFAZER (CONDICIONAL). Findings: **1 CRITICAL · 3 ALTOS · 4 MÉDIOS · 5 BAIXOS · 3 INFOs = 16 totais**. Sessao de correcao 2026-05-06 (`wave2-v4-c08/fixes/execution`) corrigiu **16/16 acionaveis em 13 commits atomicos** + 3 ajustes visuais finais validados pelo Mario. **CRITICAL**: AUD-001 (figma-reference.png commitada). **ALTOS**: AUD-002 (analysis.md cherry-pick para branch da entrega — link CHANGELOG resolve); AUD-003 (refactor `formatRota` -> `lib/types/prova.ts` + `isPathActive` -> `lib/path-active.ts` + 13 testes Vitest novos cobrindo 4 v4.0 + 2 legacy + null + sanity exhaustividade + 5 cenarios isPathActive — total Vitest do projeto 15 -> 28); AUD-004 (token semantico `--color-card-art-bg=#d9d9d9` em globals.css desacoplado de `--color-card-surface` — ADR-129). **MÉDIOS**: AUD-005+006 (`codigo_publico` migrado do metaGrid para `requerimentoLabel` no header — restaura grid 3x2 estrito; apendice no ADR-127); AUD-007 (`.title` clamp 1.5rem/2.5vw/2.5rem — minimo 24px em viewport tablet); AUD-008 (nova secao "Pagina de detalhe da prova: estrutura e extensao para Wave 3" em CLAUDE.md cobrindo 4 camadas para adicionar valor a `StatusProvaEnum`). **BAIXOS**: AUD-009 (object-fit cover WONTFIX — ADR-130); AUD-010 (wrapper trivial `formatStatus` removido); AUD-011 (tooltip nativo HTML title no em-dash de prova legacy); AUD-012 (coberto por AUD-003); AUD-013 (template `smoke-validation.md` 19 itens — Mario percorre antes do PR final). **INFOs**: AUD-014/015/016 consolidados em ADR-131. **Ajustes visuais finais (3 commits pos-Mario)**: card branco com `flex: 1` para preencher altura disponivel; `timelineCard` REANINHADO dentro do `innerCard` branco (correcao de interpretacao errada do ADR-127 — apendice 2); `artSlot` reduzido de 380px para 320px (proporcao Figma). **Validacao final**: npx vitest run 28/28; npx tsc --noEmit exit 0; npx next build 13/13 paginas; `/provas/[id]` em 11.4 kB / 209 kB (sem regressao). Advisors MCP sem novos alertas. **B1 default aplicado**: stash@{0} preserva CSS uncommitted experimentais — Mario decide se reaplica. ADRs novos: 129, 130, 131 + 2 apendices ADR-127. **Pendencias**: smoke E2E manual (`smoke-validation.md` 19 itens — itens 4/5 podem ser SKIP por ausencia de motorista/clicheria em producao); nova auditoria independente em sessao separada para validar resolucao + ausencia de regressao + viabilidade Wave 3 + fidelidade visual contra figma-reference.png. | — |
| **v4.0 W3 — C10 Scanner Reformulado** | ✅ **COMPLETO** (aguarda smoke E2E + PR) + 4 iteracoes de refinamento visual | Componente 10 (atualizacao v4.0) — Redesign do Scanner de QR Code com Identificacao por Codigo Alfanumerico. **1ª entrega da Wave 3 v4.0** (de 4 — C19, C11, C12 a seguir). Gate-based two-stage: 4 ambiguidades visuais resolvidas pelo Mario (Q1 estrategia hibrida do payload — camera valida `payload` completo + hash, manual valida `codigo_publico` isolado; Q2 tab Manual como shell funcional + chamada da camada de servico — sem mascara/realtime/rate-limit-client que ficam para C19; Q3 footer "Ultima leitura ha —" + "Ver historico" como placeholder visual OUT OF SCOPE; Q4 input usa formato real `PRV-AAAA-MM-NNNNNN` em vez do `3S- XXXX-XXXX` do Figma). **Bug corrigido R-1:** `scan_prova` fazia lookup por `nro_requerimento` mesmo quando QR carregava `codigo_publico` — provas v4.0 nao escaneavam. Agora detecta formato via `validar_formato_codigo_publico` e usa lookup correto. **Backend:** `ScanRequest` aceita `payload` XOR `codigo` via `model_validator`. Novo helper `_carregar_prova_por_codigo_publico_com_scoping` (canonico v4.0+). Audit log com novo campo `origem` ('camera' \| 'manual'). Mensagens 404 GENERICAS para inexistente / fora-do-scope / formato invalido (DAT §8.2 — protecao contra enumeracao). **Frontend:** camada de servico desacoplada `lib/services/identificacao-prova.ts` com `identificarProvaPorPayload` + `identificarProvaPorCodigo`. Tipos `CodigoErro` (5 codigos) + `ResultadoIdentificacao` (tagged union). Mensagens em pt-BR pre-resolvidas. **Constraint dura: zero acoplamento com DOM/camera** — testavel em `vitest --environment node`; teste anti-acoplamento (regex contra `navigator.`/`document.`/`window.`/`html5-qrcode`) garante. Page reescrita 740→414 LOC. CSS reescrito 589→433 LOC. UI fiel ao Figma: toggle pill Camera/Manual, painel da camera com QR mock idle / live preview scanning + brackets viewfinder, painel manual com input PRV + botao "Buscar prova →" + chamada da camada de servico, footer placeholder, banners de erro contextuais (DISPOSITIVO_SEM_CAMERA com link para Manual inline). Removidos `useScanProva`, `AssinaturaModal`, `ScanReadyView`, `DoneView`, `react-signature-canvas` import (transicao migra para `/provas/[id]` no C11 v4.0). **4 iteracoes de refinamento visual pos-feedback do Mario:** (4) footer movido para dentro da coluna direita do innerCard alinhado com a sidebar/panel (specs Figma divisor `w[554]`) — ADR-136; (5) tabs Camera/Manual ganharam pill preto animado via `framer-motion` `layoutId="scanner-tab-pill"` espelhando o `.segmentBtn` da `/nova-prova` + `JetBrains_Mono` adicionado via `next/font/google` para o input — ADR-135; (6) `.cameraSidebarTop` alinhado ao topo (`flex-start`) e `.manualPanelTop` centralizado verticalmente (`center`) — Camera ≠ Manual; (7) feixe amarelo no QR mock anima infinito subindo/descendo via CSS `@keyframes qrScanBeam 2.2s ease-in-out infinite` simulando scanner real + `prefers-reduced-motion` desabilita — ADR-137. **Specs visuais extraidos via MCP Figma** (`mcp__9b97d32e-...__get_design_context` em file `kqOrPgP07y6y1SV7BUlEBs` nodes `206:87` Camera + `240:6448` Manual) — tokens corretos: bg `#eaeaea`, radius wrapper 43/innerCard 37/tabs 39/preview 16/btnCamera 17/btnManual 12, titulo 64px, sidebar h2 40px, descs 18px line-height 20.8px, brackets AMARELOS `#f5c518` 20x20 inset -10px, footer 11px `#7a7a7a`, input prefix JetBrains Mono 13px `#9a9a9a`. **825 testes backend (era 805 + 20 novos)** + **44 Vitest (era 28 + 16 novos)**. tsc 0; next build 13/13; `/escanear` 5.73 kB / **208 kB** First Load (subiu de 168 kB pelo framer-motion da iteracao 5). Zero migration. RLS inalterada. ADRs 132 (lookup polimorfico) + 133 (camada de servico desacoplada) + 134 (tab Manual + Q3 + Q4 do Mario) + 135 (pill animado tabs) + 136 (footer coluna direita) + 137 (scanner beam animation). 10 commits totais. Documentos: `docs/wave3-v4-c10/analysis.md` (Gate 1 + Execucao + Refinamento Visual iteracoes 4-7), `contrato-c19.md` (contrato pronto para Componente 19 consumir), `smoke-validation.md` (20 cenarios), `figma-references.md` (guia para adicionar PNGs). | — |
| **v4.0 W3 — C11 Maquina de Estados Expandida** | ✅ **COMPLETO** (aguarda smoke E2E + PR) | Componente 11 (atualizacao v4.0) — **maior risco da v4.0**. **3a entrega da Wave 3 v4.0** (de 4 — C12 a seguir). Expande maquina de estados de 10 valores (v3.0) para **17 valores** (10 v3.0 + 7 v4.0) distribuidos por 4 rotas, em **coexistencia** com a v3.0 (provas legacy continuam funcionando via roteador). Gate-based two-stage: 8 pontos de escalacao confirmados pelo Mario (M-1 a M-8 — ADRs 146-153). **Migration Alembic 013**: `ALTER TYPE status_prova_enum ADD VALUE IF NOT EXISTS` x 7 valores em ordem alfabetica (COM_MOTORISTA_ENTREGA_FINAL, COM_MOTORISTA_IDA_LAMINACAO, COM_MOTORISTA_VOLTA_LAMINACAO, DE_VOLTA_3STUDIO_POS_LAMINACAO, ENCAMINHADA_PARA_LAMINACAO, ENCAMINHADA_PARA_O_VENDEDOR, LAMINACAO_CONCLUIDA). Aplicada via MCP em transacao unica; alembic_version='013' setado manualmente. **Modulo `backend/app/state_machine/`** (DAT §4.1): facade `__init__.py` com roteador v3.0/v4.0 + `v4/rules.py` (24 entradas em `TRANSITION_RULES` distribuidas em 5+10+3+6) + `v4/contextos.py` (3 contextos do Motorista — derivado de status, gravado em audit_log) + `v4/machine.py` (validar+executar). Princípio de invariancia (DAT §4.2): tabela em Python versionado, NAO no banco. **Decisao M-1**: ator de `FILIAL.CRIADA → ENCAMINHADA_PARA_O_VENDEDOR` = VENDEDOR (texto literal §5.4 prevalece sobre UML 06.3 — ADR-146). **Decisao M-2b(a)**: `COM_MOTORISTA` legacy ≠ `COM_MOTORISTA_ENTREGA_FINAL` v4.0 (valores DISTINTOS no enum, semanticamente unificados via `contexto_motorista()` que mapeia ambos para "entrega_final"). **Migration RLS 014**: 3 policies (provas/movimentacoes/etiquetas) DROP+CREATE expandindo visibilidade — MOTORISTA ve 4 estados (3 v4.0 + 1 legacy), CLICHERIA ve 6 estados (3 v4.0 + 3 legacy). **Frontend**: `lib/types/prova.ts` com 17 valores em `StatusProva` + `STATUS_LABELS` + `STATUS_LABELS_SHORT` + `STATUS_OPTIONS` reorganizado. `AdminActions.tsx` CANCELAVEIS estendido para 15 ativos. `ReportGeral.tsx` paleta expandida. **Sem novo endpoint** (Decisao M-3): `POST /{id}/transicoes` continua generico; roteador interno dispatcha. **Sem trigger semantico no Postgres** (Decisao M-4): invariancia no Python. **Sem rate limit** (Decisao M-8): follow-up unificado com ADR-145 do C19 antes do PR para `main`. **Testes**: `backend/tests/state_machine/` com 139 testes (rules+contextos+machine+facade) cobrindo **100%** em `app/state_machine/v4/*` (187/187 stmts) + `test_status_prova_enum_drift.py` (3 pure-Python + 1 skipped integrado). Suite total: **961 passed + 10 skipped** (era 825+9 pos-C19; +136 testes da Wave 3 v4.0 C11). Frontend tsc 0; Vitest 98/98; advisor MCP sem novos alertas. ADRs 146-153 + `docs/wave3-v4-c11/` (analysis.md Gate 1 + _agent_extraction.md literal + contrato-c12.md). **Limitacao assumida**: criterio 15 do prompt (§6.3) — botoes inline de transicao na pagina de detalhe — NAO entregue. Scanner em `/escanear` permanece como caminho canonico de transicao (RNF-002: ≤2s captura → assinatura). Pagina de detalhe exibe os labels v4.0 corretos + admin actions cobrem cancelar/reiniciar; mas botoes "Aprovar/Reprovar/Encaminhar" inline no detalhe requereriam signature canvas modal (~200 LOC) e foram deferidos. **Follow-up registrado para decisao do Mario no merge**. | — |
| **v4.0 W3 — C11 Audit Fixes** | ✅ **COMPLETO** (mergeado em `development` em 2026-05-13) | Auditoria sênior independente pos-C11 (2026-05-13, branch `wave3-v4/componente-11` HEAD `f57ba28`). Veredito: **REPROVADO E REFAZER (CONDICIONAL)** — bloqueio limitado a correcoes cirurgicas no acoplamento Wave 1 v4.0 ↔ Wave 3 v4.0. Implementacao central da maquina v4.0 (rules, machine, contextos, facade, enum 3 camadas) correta e bem testada (100% cobertura, 24/24 Matriz par a par, coexistencia v3.0↔v4.0 preservada — 17 provas sem cruzamento). Findings: **2 CRITICOS · 3 ALTOS · 5 MEDIOS · 6 BAIXOS · 6 INFO = 22 entradas (19 unicos apos dedup)**. Sessao de correcao 2026-05-13 (`wave3-v4-c11/fixes/execution` base `wave3-v4/componente-11`) corrigiu **TODOS os 22 IDs em 10 commits atomicos** + 4 ADRs novos (154-157). **CRITICOS**: AUD-001 (`_MOTORISTA_STATUSES` estendido com 3 contextos v4.0 — defesa primaria do scope motorista agora bate com Matriz + RLS 014); AUD-002 (`_CLICHERIA_STATUSES` estendido com 4 estados v4.0 incluindo `COM_MOTORISTA_ENTREGA_FINAL` + migration RLS 015 aplicada via MCP em producao — paridade primaria↔secundaria; uniformiza `pol_movimentacoes_select` para EXISTS combinando AUD-008/016). **ALTOS**: AUD-003 (`shared/access-matrix.json scope_kinds` enumera literalmente os 4+7 estados); AUD-004/006 (6 testes novos asserindo cada literal v4.0 explicitamente — 4 unit em `test_scope_filter_for.py` + 2 API em `test_provas_api.py`); AUD-005 Opcao (a) decidida pelo Mario (criterio 15 dos botoes inline na detail page DEFERRED — scanner `/escanear` cumpre RNF-002 ≤2s — ADR-155). **MEDIOS**: AUD-007 ADR-156 (drift Python↔Postgres em CI sem `INTEGRATION_DATABASE_URL` aceito como gap conhecido — mitigado por Python↔TS regex em CI + validacao MCP manual em cada migration); AUD-008+016 (combinados com AUD-002 — EXISTS uniformizado); AUD-009+014 ADR-154 (M-7 post-hoc — mensagens em pt-BR voz ativa concisa); AUD-010 (docstring de `pode_cancelar` reformulada: 8 v3.0 ativos + 7 v4.0 ativos = 15 cancelaveis). **BAIXOS**: AUD-011 (JSDoc do `STATUS_LABELS_SHORT` reflete 17 estados); AUD-012+013 (narrativa CHANGELOG esclarecida via apendice — 87 funcoes + 52 parametrize = 139 instances); AUD-017 ADR-157 (benchmark dedicado DEFERRED para sessao de rate limit + benchmarks antes do PR para `main`); AUD-024 ACEITO (auditor declarou aceitavel). **INFOs** (015/018/019/020/021/022): ACEITOS sem acao. **Validacao**: backend pytest **967 passed + 10 skipped** (era 961 + 6 novos AUD-004); frontend tsc exit 0; Vitest 98/98; MCP `apply_migration` RLS 015 success; `pg_policies` confirma `COM_MOTORISTA_ENTREGA_FINAL` em 3 policies de clicheria; `get_advisors security` 0 novos alertas; `git diff` em maquina v3.0/CSS/C10/C06/C19: VAZIO; 23/23 itens do checklist de validacao verdes. ADRs novos: 154 (M-7 post-hoc) + 155 (AUD-005 (a) DEFERRED) + 156 (drift CI/CD) + 157 (benchmark DEFERRED). **Pendencias para PR em `main`**: sessao de rate limit + benchmarks (ADR-145 + ADR-153 + ADR-157) OBRIGATORIA; sessao de CI/CD pos-Wave 3 (ADR-156); smoke E2E manual motorista nos 3 contextos v4.0 + clicheria em `COM_MOTORISTA_ENTREGA_FINAL`; C12 entregue. **Recomendado**: nova rodada de auditoria independente em sessao separada (foco extra: RLS 015 + 6 testes novos AUD-004 + 4 ADRs novos). | — |
| **v4.0 W3 — C19 Fallback Digitacao Manual** | ✅ **COMPLETO** (aguarda smoke E2E + PR) | Componente 19 (NOVO na v4.0 — RF-005 / US-002 / Backlog item 19). **2ª entrega da Wave 3 v4.0** (de 4 — C11, C12 a seguir). Frontend-only, ativa logica em UI ja entregue pelo C10 (`<ManualPanel>` em `escanear/page.tsx`). Gate-based two-stage: 10 decisoes (D1-D10) propostas no Gate 1 e confirmadas pelo Mario com defaults. **Novos:** `lib/codigo-publico.ts` (139 LOC — `CODIGO_PUBLICO_REGEX` paridade com `validar_formato_codigo_publico` do backend; `ALFABETO_SUFIXO` (`ABCDEFGHJKMNPQRSTUVWXYZ23456789` — 31 chars sem 0/O/1/I/L); `aplicarMascara` com auto-uppercase + strip do prefixo PRV- + hifens automaticos + **bloqueio rigido por posicao** (ano/mes=digitos, sufixo=alfabeto) + truncamento 14 chars; `montarCodigoCompleto` prepende "PRV-"; `validarFormatoCodigoPublico` + `isDisplayCompleto` + `isCharValidoEmPosicaoSemHifen`. Modulo puro testavel em `environment: node` — 43 testes Vitest cobrindo paridade backend + mascara incremental + bloqueio por posicao + idempotencia + integracao mascara → validacao). `hooks/useCodigoPrvInput.ts` (68 LOC — binding trivial sobre as funcoes puras; sem testes Vitest dedicados conforme D-13 da Wave 1 v4.0; validado por E2E). **Modificado:** `(dashboard)/escanear/page.tsx` (+133/-21 LOC) — `<ManualPanel>` recebe `display`/`isFormatValid`/`onChange`/`onTentarNovamente` do container, valida formato client-side ANTES de chamar o servico (botao "Buscar prova" so habilita com formato completo), **uniformiza `QR_INVALIDO` (client OR 422 backend) com "Prova nao encontrada."** via `MENSAGENS_C19` + `mensagemFinal` helper (anti-enumeracao em camada UI — ADR-143), foco automatico no input ao mount via `useRef` + `useEffect([])` (R-8 / ADR-144), label sr-only estendida ("Codigo da prova no formato PRV-AAAA-MM-NNNNNN") + hint sr-only adicional `id="manual-hint"` + `aria-describedby` dinamico (alterna entre `#manual-error` e `#manual-hint`), botao "Tentar novamente" no estado `ERRO_REDE` reseta sem mexer no codigo digitado (R-10), reset de banner no `onChange` do input (D8), `maxLength={14}` no input (defesa em profundidade alinhada ao backend `max_length=32` — AUD-W3C10-012), `codigoInput` preservado ao alternar para tab Camera (R-9 — usuario nao perde digitacao parcial). **Zero touch backend** (camada de servico `identificacao-prova.ts` consumida sem modificacao; endpoint `/scan` ja aceita `body.codigo` desde o C10 v4.0). **Zero touch RLS, zero migration, zero advisor MCP novo.** **89 testes Vitest** (era 46 + 43 novos do `codigo-publico.test.ts`); tsc 0; next build 13/13; `/escanear` 7.68 kB → **8.31 kB** (+0.63 kB Size) / First Load 210 kB inalterado. **Decisoes (ADRs 141-145):** 141 mascara manual sem nova dep (`imask`/`react-input-mask` rejeitados — economiza ~8-15 kB); 142 bloqueio rigido por posicao; 143 uniformizacao `QR_INVALIDO` → "Prova nao encontrada." (anti-enumeracao em camada UI); 144 foco automatico + a11y aprofundada (label estendida + hint sr-only + aria-describedby dinamico); 145 **rate-limit backend permanece como FOLLOW-UP OBRIGATORIO antes do PR para `main`** (DAT v3.0 §8.2 + Backlog C19 Notas Tecnicas exigem 30/min/user → 429 → novo codigo `RATE_LIMITED`; sessao separada com `slowapi` no `/scan` filtrado por `current_user.id`). Defesa em profundidade corrente (validacao client + formato antes do SELECT backend + RLS antes da resposta + 404 unificado + alfabeto 31^6=887M combinacoes/mes + audit log com `codigo_recebido` truncado) cobre descoberta lenta mas nao substitui o rate-limit prescrito pelo DAT. 5 commits (analysis read-only `8dc6a92` + util `f5e3271` + hook `f8f7492` + integracao `6e42129` + docs `fcb3d48`). Documentos: `docs/wave3-v4-c19/analysis.md` (Gate 1 + Apendice A Execucao); `docs/wave3-v4-c19/smoke-validation.md` (20 cenarios para Mario rodar em producao antes do PR para `main` — cobre foco automatico, mascara incremental, auto-uppercase, bloqueio rigido, paste com prefixo, happy path, anti-enumeracao, falha de rede + Tentar novamente, RLS, sessao expirada, acessibilidade teclado + leitor de tela, performance, audit log `origem='manual'`, axe-core). | — |

**Estado atual do banco de producao:**
- `alembic_version = 013` (migration 013 aplicada na Wave 3 v4.0 / C11, 2026-05-13 — ADRs 146-153). Migration 012 aplicada na Wave 2 v4.0 (2026-05-04 — ADRs 115-119). Wave 6 nao criou Alembic. Wave 1 v4.0 nao criou Alembic.
- **Migration 013 (Wave 3 v4.0 / C11, 2026-05-13)**: `ALTER TYPE status_prova_enum ADD VALUE IF NOT EXISTS` x 7 valores. Aplicada via MCP `apply_migration` em transacao unica (sem UPDATE que use valores recem-adicionados — seguro vs limitacao Postgres). alembic_version setado para '013' via UPDATE manual apos aplicacao. Total final no enum: 17 valores (10 v3.0 + 7 v4.0).
- **Divergencia migration 012 (AUD-W2V4-M02)**: a migration Alembic do repo e atomica, mas em producao foi aplicada via MCP `apply_migration` em 3 chunks — `012a` (`ALTER TYPE rota_enum ADD VALUE`), `012b` (`ADD COLUMN codigo_publico` nullable), `012c` (`ALTER COLUMN SET NOT NULL` + indexes + trigger + UPDATE alembic_version). O split foi necessario por precaucao com `ALTER TYPE ADD VALUE` em transacao. `alembic_version='012'` foi setado manualmente apos o terceiro chunk. Estado funcional final equivalente ao da migration atomic do repo; idempotencia validada em `backend/tests/test_migration_012.py` (AUD-W2V4-T03). Em ambiente fresh (dev local, branch Supabase), `alembic upgrade head` produz o mesmo estado em uma so transacao.
- **6 tabelas de dominio** + `alembic_version` (todas com RLS habilitada)
- **`provas_digitais.codigo_publico VARCHAR(20) UNIQUE NOT NULL`** (Wave 2 v4.0, ADR-116): identificador alfanumerico humano-legivel `PRV-AAAA-MM-NNNNNN`. UNIQUE INDEX `idx_provas_codigo_publico`. Embutido no payload do QR Code (DAT §8.1 — idempotencia camera↔digitacao manual via Componente 19 da Wave 3 v4.0).
- **`rota_enum` com 6 valores**: 4 v4.0 (`MATRIZ`/`LAM_MATRIZ`/`FILIAL`/`LAM_FILIAL`) + 2 legacy v3.0 (`PADRAO`/`DIRETA`). Os legacy permanecem ate a Wave 7 (Componente 21) fazer o backfill final — drop nao e suportado pelo Postgres em transacao.
- **Trigger `trg_provas_rota_imutavel` (BEFORE UPDATE)** (Wave 2 v4.0, ADR-117): bloqueia mudanca de rota apos definicao com SQLSTATE 22023. Permite NULL→valor (Wave 7 backfill); bloqueia valor→outro_valor e valor→NULL.
- **`status_prova_enum` com 17 valores**: 10 v3.0 (CRIADA, RETIRADA_PELO_VENDEDOR, APROVADA_PELO_VENDEDOR, DE_VOLTA_3STUDIO, COM_MOTORISTA, ENVIADA_PARA_CLICHERIA, ENCAMINHADA_A_CLICHERIA, RECEBIDA_PELA_CLICHERIA, REPROVADA_PELO_VENDEDOR, CANCELADA) + 7 v4.0 (COM_MOTORISTA_ENTREGA_FINAL, COM_MOTORISTA_IDA_LAMINACAO, COM_MOTORISTA_VOLTA_LAMINACAO, DE_VOLTA_3STUDIO_POS_LAMINACAO, ENCAMINHADA_PARA_LAMINACAO, ENCAMINHADA_PARA_O_VENDEDOR, LAMINACAO_CONCLUIDA — migration 013, Wave 3 v4.0 / C11). Sincronizado com Python `StatusProvaEnum` + TypeScript `StatusProva`; drift detectado por `backend/tests/test_status_prova_enum_drift.py`.
- **Schema `app_private`** (Wave 1 v4.0, RLS 012): 3 funcoes helper SECURITY DEFINER `current_user_is_admin()` / `current_user_setor()` / `current_user_id()` referenciadas pelas 12 policies. Schema NAO listado em `db-schemas` do PostgREST (nao exposto via REST).
- **12 policies RLS** reescritas na Wave 1 v4.0 usando os helpers. Cobertura semantica preservada vs RLS 005/006; `pol_etiquetas_select` estendida para incluir Motorista (status COM_MOTORISTA) e Clicheria (clicheria-states) — fecha lacuna L-RLS-1. **Wave 2 v4.0 nao criou nova policy** — `pol_provas_insert` ja exigia admin (cobre o cenario v4.0). **Wave 3 v4.0 C11 (migration RLS 014)** expandiu motorista para 4 estados (1 legacy + 3 contextos v4.0) e clicheria para 6 estados (3 legacy + 3 v4.0). **Wave 3 v4.0 C11 Audit Fixes (migration RLS 015, 2026-05-13)** adicionou `COM_MOTORISTA_ENTREGA_FINAL` a clicheria nas 3 policies (paridade primaria↔secundaria com `_CLICHERIA_STATUSES` Python — AUD-W3C11-002) e uniformizou `pol_movimentacoes_select` para EXISTS (estilo consistente com `pol_etiquetas_select` — AUD-W3C11-008/016). Total clicheria pos-015: 7 estados (3 legacy + 4 v4.0).
- **`audit_logs` com 4 camadas de defesa** (RNF-005): (1) trigger `trg_audit_logs_imutavel` (Wave 0); (2) RLS deny-by-default `pol_audit_select` admin-only (Wave 0/1/2); (3) REVOKE GRANT-level INSERT/UPDATE/DELETE para `anon`/`authenticated` (Wave 6, RLS 008 — ADR-112); (4) REVOKE TRUNCATE para `anon`/`authenticated` (Wave 1 v4.0 Audit Round 2, RLS 013 — AUD-W1V4-101 — fecha lacuna onde TRUNCATE bypassa RLS e nao dispara trigger BEFORE UPDATE/DELETE). `service_role` mantem GRANT em todas as camadas (preserva flexibilidade operacional).
- **34 indexes** cobrindo filtros dos Componentes 07 + relatorios da Wave 5 (migration 010: +`idx_provas_vendedor_status` +`idx_movimentacoes_status_novo_created_at` — ADR-095) + Wave 2 v4.0 (migration 012: +`idx_provas_codigo_publico` UNIQUE +`idx_provas_rota`). Wave 6 nao criou indice (4 indices em `audit_logs` ja cobrem; advisor `unused_index` deve cair conforme uso real).
- **3 usuarios ativos**: 2 admins (`admin@3studio.com.br` + `ops@3studio.com.br`) + 1 vendedor FILIAL (`mariosouza@teste.com.br`)
- **Advisor Supabase limpo** exceto: 1 INFO `rls_enabled_no_policy` em `alembic_version` (intencional, ADR-025) + 1 WARN `auth_leaked_password_protection` (WONTFIX plano pago, ADR-027)

- **1 tabela na publicacao `supabase_realtime`**: `provas_digitais` (INSERT/UPDATE para dashboard tempo real)

**Endpoints publicos em producao (34 rotas):**

| Prefix | Endpoints | Wave |
|---|---|---|
| `/api/v1/users` | `GET /me`, `GET /`, `GET /{id}`, `POST /`, `PATCH /{id}`, `DELETE /{id}` | 1 |
| `/api/v1/provas` | `POST /upload-url`, `POST /`, `GET /`, `GET /{id}`, `GET /{id}/imagem-url`, `GET /{id}/movimentacoes`, `GET /{id}/etiqueta.pdf`, `GET /{id}/qr-code.png` | 2 |
| `/api/v1/provas` | `POST /scan`, `POST /{id}/transicoes`, `POST /{id}/cancelar`, `POST /{id}/reiniciar-ciclo` | 3 |
| `/api/v1/provas` | `GET /dashboard` | 4 |
| `/api/v1/reports` | `GET /` (scope discriminado), `GET /export` (CSV streaming) | 5 |
| `/api/v1/audit-log` | `GET /` (paginada + filtros), `GET /{id}` (detalhe + MovimentacaoSnapshot), `GET /by-prova/{id}` (historico cronologico) | 6 |
| `/api/v1/configuracoes` | `GET /`, `GET /{chave}`, `PATCH /{chave}` | 2 |
| `/health*` | `/health`, `/health/db`, `/health/r2` | 0 |

**Rotas frontend em producao (11 paginas):**
- `/login` — Wave 1
- `/dashboard` — Wave 4 C15 + Wave 5 C17 (3º card Acessar Relatorios)
- `/usuarios` — Wave 1 (CRUD + modais)
- `/nova-prova` — Wave 2 C06 (form + dropzone + preview etiqueta)
- `/provas` — Wave 2 C07 (listagem + filtros URL-persisted + paginacao)
- `/provas/[id]` — Wave 2 C08 (detalhe + modal etiqueta/QR + timeline placeholder)
- `/configuracoes` — Wave 2 C09 (tempo atraso + template etiqueta)
- `/escanear` — Wave 3 C10+C11 (scanner QR + assinatura digital + transicao de status + entrada manual de codigo QR)
- `/relatorios` — Wave 5 C16 (4 perspectivas com gráficos SVG inline interativos: Geral, 3Studio, Vendedores, Clicheria + CSV export streaming + atalhos teclado globais)
- `/auditoria` — Wave 6 C18 (listagem do log imutavel admin-only com filtros semanticos, presets de data, paginacao numerada + sticky header + ordenacao clicavel + drawer lateral com focus trap e MovimentacaoSnapshot)

**Atalhos globais por teclado** (Wave 5 C17 + Wave 6): `g s` → /escanear, `g p` → /provas, `g r` → /relatorios (admin-only), `g a` → /auditoria (admin-only), `?` → painel de ajuda.

**Itens do menu ainda inativos (placeholders para Waves futuras):**
- "Informacoes" — sem wave atribuida

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Frontend | Next.js 14, React 18, TypeScript 5, CSS Modules |
| Backend | FastAPI, SQLAlchemy 2.0 async, Pydantic v2, Alembic |
| Banco | PostgreSQL (Supabase, projeto `rwxlpwmnkekzuurgthkr`, sa-east-1) |
| Auth | Supabase Auth (emite JWT) + PyJWT >=2.8 (verifica, nunca emite) |
| Storage | Cloudflare R2 (bucket `rastreio-provas-artes`, account `20ab724c91f6bda669eecfe7c51c9171`) |
| CI/CD | GitHub Actions (lint, testes, keep-alive cron 6 dias) |
| Deploy | Railway (backend) + Vercel (frontend) — configurado na Wave 3 Lote A |

**Deploy em producao (configurado 2026-04-13):**
- **Backend (Railway):** `https://provadigital-production.up.railway.app`
  - Root Directory: `backend`
  - Start Command: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
  - Variavel `FRONTEND_URL` deve apontar para a URL da Vercel (CORS)
  - Todas as env vars do `backend/.env.example` configuradas no painel Variables
  - Procfile presente em `backend/Procfile`
  - `requirements.txt` presente em `backend/requirements.txt` (Railway detecta automaticamente)
  - `pyproject.toml` tem `[tool.setuptools.packages.find] include = ["app*"]` para evitar flat-layout error
- **Frontend (Vercel):** `https://prova-digital-five.vercel.app`
  - Root Directory: `frontend`
  - Framework: Next.js (auto-detectado)
  - 3 env vars: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL`
  - `NEXT_PUBLIC_API_URL` deve apontar para a URL do Railway (sem `/` no final)
- **Fluxo:** Celular → Vercel (frontend) → Railway (backend) → Supabase (DB) + R2 (imagens)
- **CORS:** `FRONTEND_URL` no Railway = URL da Vercel. Sem isso, o browser bloqueia as chamadas.
- **Redeploy automatico:** ambos redeployam quando ha push na `main` do GitHub

---

## Regras criticas

1. **Separacao Alembic / Supabase**: Alembic gerencia APENAS tabelas de dominio (`public.*`).
   Nunca tocar em `auth.*` via Alembic — Supabase gerencia auth.
2. **RLS sempre versionado**: toda policy deve existir como `.sql` em `backend/migrations/rls/`
   ANTES de ser aplicada ao banco. Scripts sao idempotentes (DROP IF EXISTS + CREATE).
3. **PyJWT >= 2.8**: nunca usar python-jose. O backend apenas verifica tokens, nunca emite.
4. **SERVICE_ROLE_KEY**: nunca expor ao frontend. Apenas o backend FastAPI usa.
5. **CSS Modules**: sem framework CSS externo (Tailwind, Bootstrap, etc).
6. **TypeScript estrito**: `strict: true` no tsconfig.

---

## Estrutura de pastas

```
provaDigital/
├── .claude/launch.json          # Dev servers (backend :8000, frontend :3000)
├── .github/workflows/
│   ├── ci.yml                   # Lint (ruff) + testes + deploy staging
│   └── keep-alive.yml           # Cron cada 6 dias para evitar pausa Supabase
├── backend/
│   ├── alembic.ini
│   ├── pyproject.toml           # Dependencias pinadas
│   ├── .env / .env.example
│   ├── app/
│   │   ├── main.py              # FastAPI + 3 health checks + CORS + users router
│   │   ├── core/
│   │   │   ├── config.py        # Pydantic Settings (13 env vars — +QR_CODE_HMAC_SECRET)
│   │   │   ├── jwt.py           # JWT ES256 (JWKS) + HS256 fallback (ADR-014)
│   │   │   ├── r2.py            # Cliente R2 async (singleton + run_in_executor)
│   │   │   └── supabase_admin.py # GoTrue Admin API client (ADR-013/015)
│   │   ├── db/
│   │   │   ├── session.py       # SQLAlchemy async engine + session
│   │   │   └── models.py        # Usuario + ProvaDigital + Movimentacao + Etiqueta + AuditLog + ConfiguracaoSistema + enums (Setor, Localizacao, StatusProva, Rota)
│   │   ├── api/
│   │   │   ├── deps.py          # Auth dependencies (get_current_user, get_admin_user, require_role)
│   │   │   ├── v1/users.py      # 6 endpoints CRUD usuarios
│   │   │   ├── v1/provas.py     # 10 endpoints Wave 2+3: C06-C08 (8) + POST /scan (C10) + POST /{id}/transicoes (C11)
│   │   │   └── v1/configuracoes.py # 3 endpoints Wave 2 C09: GET/, GET/{chave}, PATCH/{chave}
│   │   ├── domain/
│   │   │   └── schemas/
│   │   │       ├── user.py      # Pydantic v2: UserCreate, UserUpdate, UserResponse
│   │   │       ├── prova.py     # Pydantic v2 Wave 2: Upload/ProvaCreate/ProvaResponse + sanitize_filename
│   │   │       ├── configuracao.py # Pydantic v2 Wave 2 C09: whitelist + validators por chave
│   │   │       └── dashboard.py   # Pydantic v2 Wave 4 C15: DashboardContadores + DashboardResponse
│   │   └── services/            # Wave 2 (ADR-040) + Wave 3 (ADR-081)
│   │       ├── state_machine.py # Transicoes + atores + determinar_rota + executar_transicao (Wave 3 A.1)
│   │       ├── qrcode_service.py # HMAC-SHA256 hash + PNG via qrcode[pil] (ADR-033/034)
│   │       ├── etiqueta_service.py # PDF via fpdf2, templates A4/80mm (ADR-035)
│   │       ├── audit_service.py # log_audit helper (ADR-039)
│   │       └── r2_signed.py     # presigned URL + HeadObject + Range GET (ADR-031)
│   ├── migrations/
│   │   ├── env.py               # Alembic config (asyncpg→psycopg2)
│   │   ├── versions/
│   │   │   ├── 001_create_enums_tables_triggers_indexes.py
│   │   │   ├── 002_seed_configuracoes_iniciais.py
│   │   │   ├── 003_fix_constraints_indexes_trigger.py
│   │   │   ├── 004_add_is_admin_created_by_to_usuarios.py
│   │   │   ├── 005_add_index_on_usuarios_created_by.py  # auditoria Wave 1 — index FK created_by
│   │   │   ├── 006_set_search_path_on_trigger_functions.py  # ADR-024 — search_path='' nas funcoes
│   │   │   ├── 007_enable_rls_on_alembic_version.py  # ADR-025 — fix side effect do alembic stamp
│   │   │   ├── 008_add_index_on_configuracoes_sistema_updated_by.py  # ADR-026 — index FK
│   │   │   └── 009_evolve_template_etiqueta_schema.py  # ADR-036 — JSONB estruturado
│   │   └── rls/
│   │       ├── 001_enable_rls.sql
│   │       ├── 002_policies_por_perfil.sql
│   │       ├── 003_policies_wave1_usuarios.sql
│   │       ├── 004_unify_rls_is_admin.sql  # ADR-018
│   │       ├── 005_initplan_optimization.sql  # ADR-029 — (SELECT auth.uid()) em 11 policies
│   │       ├── 006_movimentacoes_insert_and_expand_select.sql  # ADR-082 — INSERT admin + SELECT c/ MOTORISTA/CLICHERIA
│   │       ├── 007_enable_realtime_provas.sql                 # Wave 4 — provas_digitais na publicacao supabase_realtime
│   │       ├── 008_revoke_audit_logs_mutation.sql             # Wave 6 — defesa em profundidade RNF-005 (3a camada — INSERT/UPDATE/DELETE)
│   │       ├── 009_helpers_v4.sql                             # Wave 1 v4.0 — superseded por 012
│   │       ├── 010_rebase_rls_v4.sql                          # Wave 1 v4.0 — superseded por 012
│   │       ├── 011_etiquetas_select_motorista_clicheria.sql   # Wave 1 v4.0 — superseded por 012
│   │       ├── 012_move_helpers_to_app_private.sql            # Wave 1 v4.0 — estado final dos helpers SECURITY DEFINER em schema app_private
│   │       ├── 013_revoke_truncate_audit_logs.sql             # Wave 1 v4.0 Audit Round 2 — AUD-W1V4-101 (4a camada RNF-005)
│   │       ├── 014_expand_visibility_v4_states.sql            # Wave 3 v4.0 C11 — expande motorista/clicheria para 7 novos estados v4.0 (migration 013)
│   │       ├── 015_clicheria_entrega_final_e_uniformizar_exists.sql # Wave 3 v4.0 C11 Audit Fixes — AUD-002 paridade primaria<->secundaria + AUD-008/016 uniformiza EXISTS
│   │       └── apply_rls.py
│   └── tests/
│       ├── conftest.py          # Fixtures: make_user, admin_user, mock_db, vendedor_matriz/filial
│       ├── test_schemas.py      # 13 testes validacao Pydantic
│       ├── test_users_api.py    # Testes integracao endpoints usuarios
│       ├── test_state_machine.py # 26 testes Wave 2 — maquina de estados
│       ├── test_qrcode_service.py # 13 testes Wave 2 — hash + PNG
│       ├── test_etiqueta_service.py # 7 testes Wave 2 — PDF etiqueta
│       ├── test_audit_service.py # 4 testes Wave 2 — audit helper
│       ├── test_provas_api.py   # 59 testes Wave 2 C06+C07+C08 (15+23+21)
│       └── test_configuracoes_api.py # 26 testes Wave 2 C09 — endpoints configuracoes
├── frontend/
│   ├── package.json             # Next.js 14, @supabase/ssr, @supabase/supabase-js, framer-motion
│   ├── tsconfig.json            # strict, ES2017, path aliases @/*
│   ├── next.config.js
│   ├── public/images/
│   │   ├── logo-3studio.svg     # Logo branco 3STUDIO (Figma asset)
│   │   └── login-bg.png         # Background login (Figma asset)
│   └── src/
│       ├── types/global.d.ts    # Declaracao CSS Modules p/ TypeScript
│       ├── hooks/
│       │   ├── useInactivityTimeout.ts  # Timer 30min (RNF-003)
│       │   ├── useCreateProva.ts        # Wave 2 C06 — fluxo upload-url -> PUT R2 -> POST /provas
│       │   ├── useListProvas.ts         # Wave 2 C07 — GET /provas com filtros + debounce
│       │   ├── useProvaDetail.ts        # Wave 2 C08 — GET detail + imagem-url + movimentacoes
│       │   ├── useConfiguracoes.ts      # Wave 2 C09 — GET list + PATCH por chave
│       │   ├── useFocusTrap.ts           # Wave 3 Auditoria — focus trap reutilizavel para modais (WCAG 2.1)
│       │   ├── useScanner.ts            # Wave 3 C10 — wrapper html5-qrcode (SSR-safe + cleanup)
│       │   ├── useScanProva.ts          # Wave 3 C10 — POST /scan wrapper (retorna {data,error})
│       │   ├── useExecutarTransicao.ts  # Wave 3 C11 — POST /{id}/transicoes wrapper (retorna {data,error,isConflict})
│       │   ├── useCurrentUser.ts        # Wave 3 C13 — GET /users/me para detectar admin
│       │   ├── useCancelarProva.ts      # Wave 3 C13 — POST /{id}/cancelar wrapper
│       │   ├── useReiniciarCiclo.ts     # Wave 3 C14 — POST /{id}/reiniciar-ciclo wrapper
│       │   ├── useDashboard.ts          # Wave 4 C15 — GET /dashboard wrapper
│       │   └── useCodigoPrvInput.ts     # Wave 3 v4.0 C19 — binding sobre lib/codigo-publico (mascara + validacao do input PRV-AAAA-MM-NNNNNN)
│       ├── lib/
│       │   ├── api.ts           # apiFetch wrapper (token injection, ApiError). Nao usar p/ binarios
│       │   ├── codigo-publico.ts  # Wave 3 v4.0 C19 — regex/mascara/alfabeto sem 0/O/1/I/L (paridade backend; 43 testes Vitest)
│       │   ├── c19-mensagens.ts   # Wave 3 v4.0 C19 (AUD-W3C19-003 pos-auditoria) — MENSAGENS_C19 + mensagemFinal extraidos de page.tsx para teste isolado da invariante anti-enumeracao byte-a-byte (9 testes Vitest)
│       │   ├── types/
│       │   │   ├── prova.ts     # Wave 2 C06-C08 — tipos completos + STATUS_LABELS + ROTA_LABELS
│       │   │   ├── usuario.ts   # Wave 2 — tipos TS espelho de schemas/user.py
│       │   │   └── configuracao.ts # Wave 2 C09 — tipos + type guards
│       │   └── supabase/
│       │       ├── client.ts    # Browser client (@supabase/ssr)
│       │       ├── server.ts    # Server client + cookies()
│       │       └── middleware.ts # Session refresh + redirect
│       ├── middleware.ts        # Next.js middleware (auth redirect)
│       └── app/
│           ├── layout.tsx       # Inter font (next/font/google) + globals.css
│           ├── globals.css      # CSS custom properties (cores, radius)
│           ├── login/
│           │   ├── page.tsx     # Login form + SVG clip-path (Figma match)
│           │   └── login.module.css
│           └── (dashboard)/
│               ├── layout.tsx   # Sidebar + user info + logout + inactivity
│               ├── layout.module.css
│               ├── usuarios/
│               │   ├── page.tsx # Tabela + filtros + modais CRUD
│               │   └── usuarios.module.css
│               ├── nova-prova/  # Wave 2 (Componente 06)
│               │   ├── page.tsx # Form + dropzone + preview PDF da etiqueta
│               │   └── nova-prova.module.css
│               ├── provas/      # Wave 2 (Componentes 07 + 08)
│               │   ├── page.tsx # C07: listagem + filtros URL-persisted + paginacao
│               │   ├── provas.module.css
│               │   └── [id]/    # C08: detalhe + C12: timeline + C13/C14: admin actions
│               │       ├── page.tsx                     # dados + arte + timeline + admin actions
│               │       ├── Timeline.tsx                 # C12: timeline visual com Framer Motion
│               │       ├── timeline.module.css          # C12: estilos da timeline
│               │       ├── AdminActions.tsx             # C13/C14: botoes cancelar + reiniciar + modais
│               │       ├── VisualizarEtiquetaModal.tsx  # modal PDF + QR code
│               │       └── detalhe.module.css
│               ├── escanear/     # Wave 3 (Componentes 10 + 11)
│               │   ├── page.tsx                     # scanner QR + assinatura + state machine
│               │   └── escanear.module.css
│               ├── dashboard/    # Wave 4 (Componente 15)
│               │   ├── page.tsx                     # contadores + Recharts + Realtime
│               │   └── dashboard.module.css
│               └── configuracoes/ # Wave 2 (Componente 09)
│                   ├── page.tsx # Tempo atraso + template etiqueta
│                   └── configuracoes.module.css
├── scripts/
│   ├── smoke_r2.py              # Teste ciclo R2: upload→list→download→delete
│   └── keep_alive.py            # GET /health/db com log
├── docs/
│   ├── cloudflare_r2_setup.md   # Guia manual CORS + API token
│   └── db/schema.sql            # Snapshot do schema atual
├── CLAUDE.md                    # Este arquivo
├── DECISIONS.md                 # Registro de decisoes tecnicas (ADR)
└── CHANGELOG.md                 # Historico por sessao
```

---

## Documentos de referencia

| Documento | Local | Nota |
|-----------|-------|------|
| Requisitos v3.0 | Desktop/Rastreio Prova Digital/ | Requisitos funcionais e regras de negocio |
| UML v3.0 | Desktop/Rastreio Prova Digital/ | Modelagem (diagramas de estado, classes, etc) |
| DAT v2.0 | Desktop/Rastreio Prova Digital/ | Arquitetura tecnica detalhada |
| Backlog v3.0 | Desktop/Rastreio Prova Digital/ | NAO editar — gerenciado pelo Renan fora do Claude Code |

Consultar tambem: [DECISIONS.md](DECISIONS.md) | [CHANGELOG.md](CHANGELOG.md) | [docs/db/schema.sql](docs/db/schema.sql) | [docs/waves/](docs/waves/) (closeouts por wave)

---

## Fluxo de trabalho

1. Ler este CLAUDE.md para contexto rapido
2. Consultar o item do backlog indicado pelo Renan
3. Implementar conforme Requisitos + UML + DAT
4. Ao finalizar: atualizar CHANGELOG.md e DECISIONS.md (se houve decisao nova)

---

## Regras operacionais aprendidas ao longo das Waves

**Sempre usar o `.venv/` do projeto para pip/pytest/uvicorn** (Sessao 8b, 10b, 11b):
- **Windows cmd.exe usa `\` (backslash)**, PowerShell aceita `\` ou `/`, Git Bash usa `/`:
  - cmd:       `.venv\Scripts\python -m pytest`
  - PowerShell: `.venv\Scripts\python -m pytest` ou `.venv/Scripts/python -m pytest`
  - Git Bash:  `.venv/Scripts/python -m pytest`
- **Alternativa confortavel**: ativar o venv primeiro com `.venv\Scripts\activate` (ou `source .venv/Scripts/activate` no Git Bash). Depois de ativado, pode rodar `python`, `pip`, `pytest` direto sem prefixo.
- Para **subir o backend do repo root**: `.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload`
- Qualquer comando sem prefixar o venv (ou sem ativar ele antes) e bug em potencial — pode pegar Python global.

**Paths relativos no codigo** (Sessao 10b):
- `config.py` usa `Path(__file__).resolve().parent.parent.parent / ".env"` para resolver o `.env` independente do cwd
- Qualquer novo path relativo no backend deve seguir o mesmo padrao — nunca depender do cwd

**Mocks de SQLAlchemy NAO testam ordem de INSERTs** (Sessao 8c):
- Fluxos com multiplos INSERTs encadeados por FK precisam de `await db.flush()` explicito entre cada `db.add()`
- Sem relationship declarada, o SQLAlchemy nao detecta a dependencia FK automaticamente
- Rodar `scripts/reproduce_*.py` contra banco real antes de declarar Done — regra desde a Sessao 8c

**Binarios no frontend**:
- `apiFetch<T>()` serializa como JSON — **nao usar** para `/etiqueta.pdf`, `/qr-code.png` ou outros endpoints binarios
- Fazer `fetch` direto com header Authorization manual + `response.blob()` → `URL.createObjectURL(blob)`
- Sempre revogar object URLs no cleanup do `useEffect` para nao vazar memoria

**Scripts one-shot temporarios**:
- Colocar em `scripts/reproduce_*.py` ou `scripts/seed_*.py`
- Ter um modo `--cleanup` que funciona como **primeiro** check do `main()`, nao no final
- Remover do repo apos validacao — nao deixar codigo morto

**Registros imutaveis**:
- `audit_logs`, `movimentacoes` e `etiquetas` tem triggers de imutabilidade
- Nunca esperar conseguir apagar essas linhas — para "limpar" provas de teste, marcar como `CANCELADA` via UPDATE em `provas_digitais`
- O objeto R2 correspondente pode ser deletado via boto3, mas e best-effort (nao atomic com a transacao do banco)

---

## Atalhos de teclado globais (Wave 5 Componente 17 — RF-016, expandido na Wave 6)

Disponiveis em qualquer pagina autenticada, registrados via
`useGlobalShortcuts` em `(dashboard)/layout.tsx`. Padrao 2-keystroke
estilo GitHub: pressionar `g` ativa "modo leader" por 1.5s, depois a
segunda tecla dispara a acao.

| Atalho | Acao |
|--------|------|
| `g` `s` | Ir para `/escanear` |
| `g` `p` | Ir para `/provas` |
| `g` `r` | Ir para `/relatorios` (apenas admin — vendedor/motorista/clicheria nao veem) |
| `g` `a` | Ir para `/auditoria` (apenas admin — Wave 6 C18, RNF-005) |
| `?` | Abrir/fechar painel de ajuda dos atalhos (`<KeyboardShortcutsHelp />`) |
| `Esc` | Fechar painel de ajuda ou cancelar leader |

**Comportamento:**
- Atalhos sao **desativados** quando o foco esta em `<input>`, `<textarea>`,
  `<select>` ou elemento `[contenteditable]` — nao quebra digitacao em
  formularios e buscas.
- Modificadores (Ctrl/Cmd/Alt/Meta) sao ignorados — atalhos so disparam
  com a tecla pura. Evita conflito com shortcuts do navegador.
- `g r` e `g a` aparecem no painel de ajuda **apenas para `is_admin = true`**;
  vendedores/motoristas/clicheria nao veem os atalhos na lista nem podem
  ativar via teclado. Defesa adicional: backend dos `/api/v1/reports` e
  `/api/v1/audit-log` retornam 403 se acesso direto.

**Implementacao:**
- Hook: `frontend/src/hooks/useGlobalShortcuts.ts`
- Modal: `frontend/src/components/KeyboardShortcutsHelp.tsx`
- Estilos: `frontend/src/components/KeyboardShortcutsHelp.module.css`
- Registro no layout: `frontend/src/app/(dashboard)/layout.tsx`
  (1 import + 1 hook call + 1 render condicional)

**Atalhos visuais (3 cards no `/dashboard`)** complementam os de teclado
para usuarios mouse-only:
- "Escanear QR Code" (preto) -> `/escanear`
- "Nova Prova" (amarelo) -> `/nova-prova`
- "Acessar Relatorios" (laranja) -> `/relatorios`

Esses 3 cards estao no `shortcutsCell` (col 1, row 3 do grid Figma do
Dashboard — Wave 4 ADR-093 expandido pelo Componente 17 da Wave 5).

---

## RBAC: como adicionar uma nova pagina (Wave 1 v4.0 — Componente 05)

A Matriz de Acesso vive em **`shared/access-matrix.json`** — fonte unica
de verdade espelhada por TS/Python/RLS. Para adicionar uma nova pagina:

1. **Editar `shared/access-matrix.json`** acrescentando 1 entrada em
   `rules`. Campos obrigatorios:
   - `key`: nome curto kebab-case (ex.: `relatorios.export-mensal`).
   - `path`: caminho real do App Router (ex.: `/relatorios/exportacao`).
   - `match`: `"exact"` | `"prefix"` | `"dynamic"` | `"action"`.
   - `perfis`: objeto com decisao para os 4 perfis
     (`studio_admin`, `vendedor`, `motorista`, `clicheria`). Cada
     decisao tem `acesso` (`"full"`/`"parcial"`/`"negado"`) e, se
     parcial, `scope` (um dos 3 kinds em `scope_kinds`).

   **AVISO (AUD-W1V4-102)**: o middleware faz **pass-through silencioso**
   para rotas com `getRuleForPath = null` (sem entrada na Matriz). Isso
   significa que se voce criar `app/(dashboard)/<x>/page.tsx` SEM
   adicionar entrada correspondente aqui, qualquer usuario autenticado
   acessa a pagina — mesmo vendedor/motorista/clicheria. O comportamento
   e intencional para nao quebrar prototipagem, mas exige disciplina:
   **toda nova rota precisa de entrada na Matriz**, mesmo que seja `full`
   para os 4 perfis. Defesa de fundo (backend `access_required` + RLS)
   continua valendo — a Matriz e a CAMADA SUPERIOR.

2. **Atualizar `EXPECTED_KEYS` em `backend/tests/access/test_matrix_structure.py`**
   para incluir a nova chave. Se for chave cuja regra nao se encaixa nas
   semanticas existentes (ex.: novo scope kind), atualizar tambem
   `VALID_SCOPES` + adicionar branch no `scope_filter_for` em
   `backend/app/access/scopes.py`.

3. **No backend**, no endpoint correspondente:
   ```python
   from app.access import access_required, scope_filter_for

   @router.get("/")
   async def listar(user: Usuario = Depends(access_required("nova.chave"))):
       scope = scope_filter_for("nova.chave", user)  # so para parcial
       ...
   ```

4. **No frontend**, na pagina:
   ```tsx
   const auth = useAuthorization("nova.chave");
   if (auth.loading) return null; // M-1: evita flash de UI proibida antes do guard
   if (!auth.hasAccess) {
     return <Restricted ruleKey="nova.chave" profile={auth.profile} />;
   }
   ```
   **Importante**: `if (auth.loading) return null` precisa vir ANTES do guard
   (`!auth.hasAccess`). Inverter a ordem reintroduz o bug M-1 (~50-200ms de
   flash de controles admin para vendedor enquanto `useCurrentUser` resolve
   `/users/me`). Ver CHANGELOG (Wave 1 v4.0 Audit Fixes — M-1) e auditoria
   Round 2 (AUD-W1V4-001/006).

5. **Se a pagina deve aparecer no menu** (`(dashboard)/layout.tsx`),
   adicionar entrada em `MAIN_NAV` ou `SECONDARY_NAV` com o campo
   `ruleKey` apontando para a nova chave. A filtragem
   `isNavItemVisible` cuidara da visibilidade.

6. **Se a tabela do banco precisa de proteção nova ou diferente**, criar
   migration RLS em `backend/migrations/rls/` referenciando os helpers
   `app_private.current_user_is_admin()` / `_setor()` / `_id()`. PR deve
   incluir as 3 camadas no mesmo commit (regra do projeto — risco R-1
   da analysis).

7. **Validar via `scripts/verify_rbac_equivalence.py`** com
   `DATABASE_URL` setado: o script insere 4 usuarios smoke, impersona
   role authenticated via `set_config request.jwt.claims`, conta linhas
   visiveis por perfil em `provas_digitais` e compara com o esperado da
   Matriz. Cleanup automatico no final.

**Importante:**
- NUNCA criar `if user.is_admin` ou `Depends(get_admin_user)` em
  endpoints novos. Use `access_required(rule_key)`.
- NUNCA escrever filtragem por `setor` direto em queries SQLAlchemy.
  Use `scope_filter_for(rule_key, user)`.
- `get_admin_user` continua existindo mas e legacy — apenas para
  invariantes de negocio que NAO sao celula da Matriz (ex.: RN-010 em
  `users.py`).

**Latencia de revogacao no middleware (AUD-W1V4-103):** o middleware
mantem um cache LRU em memoria (`PROFILE_CACHE`, TTL 30s) com snapshot
de `is_admin`/`setor`/`ativo` por `auth_uid`. **Apos PATCH/DELETE em
`/api/v1/users/{id}` que altera essas colunas, o middleware pode
continuar deixando o usuario passar pelas regras antigas por ate ~30
segundos.** Defesa em profundidade preserva: o backend valida
`get_current_user` (`ativo=true`) por request — sem cache; e o RLS
usa `app_private.current_user_*()` que sempre le `usuarios` fresh.
Logo, o pior caso da janela de 30s e o middleware permitir navegar
ate uma pagina admin-only — o backend ainda retornara 403 e a RLS
ainda filtrara dados. Para invalidacao ativa do cache (publicacao
via Realtime ou similar), ver follow-up em `audit-report.md` §
"Itens de backlog tecnico" item 7.


---

## Identificacao de provas: contrato compartilhado entre scanner e digitacao manual (Wave 3 v4.0+)

A Wave 3 v4.0 introduz **2 mecanismos** de identificacao de provas que
compartilham o mesmo lookup logico:

1. **Camera (Componente 10 v4.0 — entregue):** o `html5-qrcode`
   decodifica o QR Code da etiqueta e devolve o **payload completo**
   (ex.: `3SD|PRV-2026-05-K3T9XB|abcd1234567890ef`).
2. **Digitacao manual (Componente 19 — ENTREGUE):** o usuario digita
   o **codigo legivel** (ex.: `PRV-2026-05-K3T9XB`). C19 entregue em
   2026-05-11 (branch `wave3-v4/componente-19`) — mascara client-side
   ativa, validacao de formato espelha o backend, foco automatico,
   anti-enumeracao preservada na UI via uniformizacao de
   `QR_INVALIDO` → "Prova nao encontrada." (ADR-143).

DAT v3.0 §8.1 exige **idempotencia** — ambos resolvem para o mesmo
registro pelo mesmo lookup.

**Camada de servico desacoplada:** `frontend/src/lib/services/identificacao-prova.ts`.

```typescript
// Caminho camera (C10):
identificarProvaPorPayload(payload, { getToken }): Promise<ResultadoIdentificacao>

// Caminho manual / contrato C19:
identificarProvaPorCodigo(codigo, { getToken }): Promise<ResultadoIdentificacao>

// Tagged union — garante exhaustividade no chamador:
type ResultadoIdentificacao =
  | { tipo: "sucesso"; prova: ScanResponse }
  | { tipo: "erro"; codigo: CodigoErro; mensagem: string };

type CodigoErro =
  | "QR_INVALIDO"
  | "PROVA_NAO_ENCONTRADA"  // mensagem GENERICA para 3 cenarios — DAT §8.2
  | "DISPOSITIVO_SEM_CAMERA"
  | "ERRO_REDE"
  | "SESSAO_EXPIRADA";
```

**Constraint dura:** **zero acoplamento com DOM/camera**. A camada e
testavel em `vitest --environment node`. Um teste especial faz regex
contra `navigator.`/`document.`/`window.`/`html5-qrcode` no source —
quebra o build se alguem reintroduzir acoplamento. Isso garante que o
C19 herda a camada testavel sem precisar de JSDOM.

**Backend correspondente:** `POST /api/v1/provas/scan` aceita
`payload` XOR `codigo` via `model_validator`. **Lookup polimorfico** no
caminho camera:
  - Se segundo campo do payload casa `validar_formato_codigo_publico`
    (`PRV-AAAA-MM-NNNNNN`) → busca por `provas_digitais.codigo_publico`.
  - Caso contrario → fallback `provas_digitais.nro_requerimento`
    (provas legacy v3.0 com QR antigo, ate Wave 7 / C21 regerar
    etiquetas).

**Audit log:** ambos os caminhos gravam `acao='escanear_prova'` com
`detalhes['origem']` em {`camera`, `manual`} + `codigo_publico` da
prova.

**Mensagens 404 GENERICAS:** "Prova nao encontrada" e a mesma
resposta para inexistente / fora do scope / formato invalido.
Frontend nao distingue. **DAT §8.2 protecao contra enumeracao.**

**Como o C19 consome:** ver `docs/wave3-v4-c10/contrato-c19.md` —
documento dedicado com tipos, funcoes, casos de uso e roteiro de
implementacao do C19 (mascara, validacao client-side, rate-limit
backend, etc.).

**Importante para waves futuras:**
- NUNCA criar fetch direto para `/scan` em outro lugar — sempre via
  a camada de servico.
- NUNCA importar `html5-qrcode` na camada de servico.
- Se precisar adicionar codigo de erro novo, estender `CodigoErro`
  + `MENSAGENS_ERRO_PADRAO` + atualizar `contrato-c19.md`. O record
  e `Record<CodigoErro, string>` — TypeScript barra build se faltar
  entrada para um codigo novo.
- Mensagem 404 generica nao pode ser quebrada: introduzir distincao
  entre "inexistente" e "fora do scope" abre vetor de enumeracao.
- **`max_length` do `body.codigo`** e **32** (era 64 ate AUD-W3C10-012
  da auditoria do C10 v4.0). Folga sobre os 18 chars do
  `PRV-AAAA-MM-NNNNNN`. Acima de 32 retorna 422 Pydantic — fora da
  faixa plausivel. C19 deve respeitar.
- **`MENSAGENS_ERRO_PADRAO`** e **`mensagemPara(codigo)`** sao
  exportados (AUD-W3C10-020 da auditoria do C10 v4.0) — C19 pode
  reutilizar/sobrescrever mensagens condicionando por `result.codigo`.

**Notas visuais consolidadas (pos-iteracoes 4-7 do C10):**
- Estrutura visual da pagina: `.pageWrapper` → `.wrapper` (cinza
  `#eaeaea` rounded 43px) → `.header` + `.tabsRow` (alinhado a
  esquerda) + `.innerCard` (white rounded 37px). Dentro do innerCard:
  `.cameraPanel` (grid 2 col, align stretch) com `.previewSlot` +
  `.cameraSidebar` (flex column space-between aninhando
  `.cameraSidebarTop` justify flex-start + `<InnerFooter />`); OU
  `.manualPanel` (flex column space-between aninhando
  `.manualPanelTop` justify center + `<InnerFooter />`).
- **Footer SEMPRE dentro da coluna direita** (ADR-136) — `width 100%
  max-width 554px`, herda largura da coluna pai. NUNCA atravessa a
  largura total do innerCard.
- **Tabs com pill animado** (`framer-motion` layoutId
  `scanner-tab-pill`, ADR-135) espelhando o `.segmentBtn` da
  `/nova-prova` (Wave 2 v4.0). Transition spring bounce 0.2 duration
  0.35.
- **Camera idle** mostra `.qrMockCard` (branco 1px #ececec rounded
  16px shadow 0 12px 36px -12px 0.18) com SVG QR 120x120 + feixe
  amarelo `.qrMockYellowBar` animado infinito (ADR-137,
  `@keyframes qrScanBeam`).
- **Brackets AMARELOS** (`#f5c518`, NAO pretos) 20x20 inset -10px do
  `.qrMockBox`.
- **Input do tab Manual** usa `JetBrains_Mono` via `next/font/google`
  importada em `layout.tsx` como CSS variable `--font-jetbrains-mono`.
  Prefix "PRV-" 13px `#9a9a9a` letter-spacing 0.65px; placeholder
  "AAAA-MM-NNNNNN" 16px `#757575` letter-spacing 0.8px; bg `#fafafa`
  border 1px `#e3e3e3` rounded 12px.
- **Botao "Buscar prova"** desabilitado quando input vazio: bg
  `#dcdcdc` texto `#9a9a9a 13.2px` Inter Medium. Habilitado vira
  preto/branco.

**Notas do Componente 19 (Wave 3 v4.0 — entregue):**
- **Logica testavel pura:** `frontend/src/lib/codigo-publico.ts` —
  regex, mascara, alfabeto, validacao. 43 testes Vitest em
  `environment: node` (sem JSDOM, alinhado com D-13 da Wave 1 v4.0).
- **Hook React:** `frontend/src/hooks/useCodigoPrvInput.ts` — binding
  trivial sobre as funcoes puras. Sem testes isolados; validado por
  E2E (smoke do Mario).
- **Mascara por posicao** (ADR-142): ano/mes = digitos 0-9; sufixo =
  `ALFABETO_SUFIXO` (`ABCDEFGHJKMNPQRSTUVWXYZ23456789`). Bloqueio
  rigido — char fora do alfabeto da posicao **nao aparece**.
- **Strip do prefixo "PRV-" no paste** — usuario pode colar codigo
  completo ou parcial; a mascara normaliza.
- **Auto-uppercase** dentro de `aplicarMascara` — usuario pode
  digitar minusculo.
- **Validacao client-side** ANTES do submit (`validarFormatoCodigoPublico`).
  Botao "Buscar prova" so habilita com formato completo (`isFormatValid`).
- **Anti-enumeracao em UI** (ADR-143): `QR_INVALIDO` (validacao
  client-side OU 422 backend) e uniformizado para
  `"Prova nao encontrada."` via `MENSAGENS_C19` + `mensagemFinal`
  em `frontend/src/lib/c19-mensagens.ts` (extraidos de `page.tsx`
  na sessao de correcao pos-auditoria 2026-05-11, AUD-W3C19-003).
  Identica ao 404 generico do backend — preserva DAT v3.0 §8.2.
  Invariante critica garantida por 9 testes Vitest em
  `__tests__/c19-mensagens.test.ts` (paridade byte-a-byte).
- **Foco automatico** no `<input>` ao mount do `<ManualPanel>`
  (ADR-144) — `useRef` + `useEffect([])`. Dispara em cada troca para
  tab Manual via `AnimatePresence mode="wait"`.
- **a11y aprofundada** (ADR-144 + Apendices 1+2 pos-auditoria):
  - Label sr-only estendida ("Codigo da prova no formato PRV-AAAA-MM-NNNNNN").
  - Hint sr-only adicional (`#manual-hint`).
  - `aria-describedby` dinamico apontando para `#manual-error` ou
    `#manual-hint`.
  - `aria-invalid` no `<input>` **e** no `<div>` wrapper
    (AUD-W3C19-004 pos-auditoria — wrapper preservado por causa da
    regra CSS `.manualInputWrapper[aria-invalid="true"]`).
  - `<strong>{state.mensagem}</strong>` no banner com `role="alert"`
    (AUD-W3C19-002 Plano B — uniformizado com CameraPanel
    pre-existente do C10; regra CSS `.errorBanner strong` ja vinha
    de `development`).
- **Botao "Tentar novamente"** no estado `ERRO_REDE` — reseta
  `manualState` sem mexer no codigo digitado.
- **Estado preservado** ao alternar para tab Camera — `codigoInput`
  vive no container; `trocarParaCamera` zera apenas `manualState`.
- **`maxLength=14`** no `<input>` (display sem prefixo) — defesa em
  profundidade alinhada ao backend `max_length=32`.
- **Rate limiting backend** (DAT §8.2 + Backlog C19 Notas Tecnicas):
  **NAO entregue** — registrado como FOLLOW-UP OBRIGATORIO em
  ADR-145 antes do PR final para `main`. Defesa em profundidade
  corrente cobre descoberta lenta; nao substitui o rate-limit
  prescrito.

---

## Maquina de Estados: coexistencia v3.0 e v4.0 (Wave 3 v4.0 / Componente 11)

A v4.0 expandiu a maquina de estados de 10 valores (v3.0) para 17 valores
(10 v3.0 + 7 v4.0). Provas legacy e v4.0 **coexistem** — cada uma usa
sua propria maquina, roteadas automaticamente pelo facade.

### Roteamento

```python
from app.state_machine import executar_transicao, transicoes_validas, pode_cancelar

# O facade dispatcha conforme prova.rota:
#   rota IS NULL ou rota IN {PADRAO, DIRETA}        -> maquina v3.0 (legacy)
#   rota IN {MATRIZ, LAM_MATRIZ, FILIAL, LAM_FILIAL} -> maquina v4.0
```

NUNCA importe direto de `app.services.state_machine` (v3.0) ou de
`app.state_machine.v4.*`. Use sempre o facade `app.state_machine`.

### Arquivos relevantes

| Arquivo | Responsabilidade |
|---|---|
| `backend/app/state_machine/__init__.py` | Facade publica + roteador v3/v4 |
| `backend/app/state_machine/v4/rules.py` | Matriz canonica (24 entradas, 4 rotas) |
| `backend/app/state_machine/v4/contextos.py` | 3 contextos do motorista |
| `backend/app/state_machine/v4/machine.py` | `validar_transicao_v4`, `executar_transicao_v4` |
| `backend/app/services/state_machine.py` | Maquina v3.0 LEGACY (intocada — Wave 7 removera) |

### Quando uma nova prova nasce

1. Admin escolhe rota na criacao (C06 v4.0) — uma das 4 v4.0
   (MATRIZ/LAM_MATRIZ/FILIAL/LAM_FILIAL).
2. Prova nasce com `rota=<escolhida>` e `status=CRIADA`.
3. Primeira transicao usa a maquina v4.0 automaticamente.
4. RN-002 v4.0: rota eh IMUTAVEL apos a criacao — trigger
   `trg_provas_rota_imutavel` bloqueia UPDATE da rota.

### Quando uma prova legacy v3.0 transita

Provas existentes em producao tem `rota IS NULL` (11 em producao no
momento da migration 013) ou `rota IN {PADRAO, DIRETA}` (5 em
producao). Essas continuam usando exclusivamente a maquina v3.0 —
o roteador detecta e despacha para `app.services.state_machine`.

A Wave 7 (Componente 21) fara o backfill `rota=NULL → valor v4.0`
deduzido da localizacao do vendedor; depois disso, provas hoje
legacy passam a usar a maquina v4.0 (trigger permite `NULL → valor`).

### Cancelamento e reinicio de ciclo sao TRANSVERSAIS

Ambos usam endpoints admin dedicados (`POST /{id}/cancelar`,
`POST /{id}/reiniciar-ciclo`) que vao por meio do facade. O reinicio
preserva `rota_antes` (RN-002 v4.0 + ADR-123) em ambas as maquinas.

### Como adicionar um novo valor a `status_prova_enum`

Sincronizacao em 3 camadas (DAT §4.5):

1. **Python `StatusProvaEnum`** em `backend/app/db/models.py`: adicionar
   o membro com nome `UPPER_SNAKE_CASE`.
2. **PostgreSQL via Alembic**: nova migration com
   `ALTER TYPE status_prova_enum ADD VALUE IF NOT EXISTS '<NOVO>';`.
3. **TypeScript** em `frontend/src/lib/types/prova.ts`: adicionar a
   `StatusProva` + `STATUS_LABELS` + `STATUS_LABELS_SHORT` +
   `STATUS_OPTIONS`.

E depois (apenas se o valor pertencer ao fluxo v4.0):
4. **Adicionar transicao em `state_machine/v4/rules.py`** (com teste
   correspondente em `tests/state_machine/test_rules_v4.py`).
5. **Atualizar RLS** se motorista/clicheria precisam ver o novo estado
   (`backend/migrations/rls/`).
6. **Atualizar `contexto_motorista`** se o novo estado eh de motorista
   (`state_machine/v4/contextos.py`).

Drift entre as camadas eh detectado por
`backend/tests/test_status_prova_enum_drift.py`.

### 3 contextos do motorista (US-006 v4.0)

```python
from app.state_machine.v4.contextos import contexto_motorista

contexto_motorista(StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO)
# "ida_laminacao"

contexto_motorista(StatusProvaEnum.COM_MOTORISTA)  # legacy v3.0
# "entrega_final"  (compat — ADR-148)

contexto_motorista(StatusProvaEnum.CRIADA)
# None
```

O contexto eh gravado em `audit_log.detalhes_json.contexto_motorista`
para investigacao (Decisao M-5 do Gate 1 — ADR-151). NAO eh coluna
separada de `movimentacoes`.

### Onde NAO duplicar regras

- **NAO escrever um trigger no Postgres** que valide transicoes
  semantica (Decisao M-4 do Gate 1 — ADR-150). Invariancia no Python
  via DAT §4.2.
- **NAO importar `TRANSICOES` de `app.services.state_machine`** se for
  codigo novo — use o facade `app.state_machine.transicoes_validas`.
- **NAO criar endpoints novos para transicoes v4.0** (Decisao M-3 do
  Gate 1 — ADR-149). O `POST /{id}/transicoes` ja eh generico.

---

## Como adicionar valor ao enum `rota_enum` (Wave 2 v4.0+)

A `rota` e uma das colunas centrais da v4.0: 4 valores
(`MATRIZ`/`LAM_MATRIZ`/`FILIAL`/`LAM_FILIAL`) + 2 legacy v3.0
(`PADRAO`/`DIRETA`) que sao mantidos ate a Wave 7 (Componente 21).

Adicionar um novo valor exige sincronizacao em CINCO camadas — sem
todas as 5, o sistema fica em estado inconsistente:

1. **Python `RotaEnum`** em `backend/app/db/models.py`: adicionar o
   novo membro (UPDATE com UPPERCASE conforme ADR-115).
2. **Pydantic `RotaCriacaoEnum`** em
   `backend/app/domain/schemas/prova.py`: adicionar o novo membro SE
   o valor for valido para criacao de prova v4.0 em diante. Legacy
   nao entra aqui (bloqueio na criacao).
3. **PostgreSQL via Alembic**: nova migration com
   `ALTER TYPE rota_enum ADD VALUE IF NOT EXISTS '<NOVO>';` (em
   transacao, ja que Postgres 12+ permite com IF NOT EXISTS).
4. **Tabela de transicoes da Wave 3 v4.0** (`state_machine.TRANSICOES`
   + `ATORES_POR_TRANSICAO`): adicionar as transicoes da nova rota.
   ATENCAO: na Wave 2 v4.0 (atual) a tabela ainda usa o modelo v3.0;
   essa atualizacao e responsabilidade do Componente 11 v4.0.
5. **Frontend** (`frontend/src/lib/types/prova.ts`): adicionar o valor
   em `Rota`, `RotaCriacao` (se aplicavel), `ROTA_LABELS` e
   `ROTA_OPTIONS`/`ROTA_CRIACAO_OPTIONS`. Tambem adicionar em
   `ROTA_BADGE_LABELS` em `backend/app/services/etiqueta_service.py`
   para o PDF nao explodir.

**Teste de drift Python ↔ PostgreSQL** existe em
`tests/test_rota_enum_drift.py` (a ser criado na primeira oportunidade
— Wave 3 v4.0 ou auditoria) — confronta `set(RotaEnum)` com
`SELECT enumlabel FROM pg_enum WHERE typname='rota_enum'`. Se algum
PR adicionar valor em apenas um dos lados, o teste falha.

**Trigger de imutabilidade** (`trg_provas_rota_imutavel`, ADR-117) NAO
muda. Continua bloqueando mudanca de valor existente.

**RLS** nao precisa ser alterada para novos valores de rota — as
policies operam sobre `vendedor_id` / `setor` / `status`, nao sobre
`rota`.

**`codigo_publico`** NAO depende da rota — formato `PRV-AAAA-MM-NNNNNN`
e estavel independente do enum.

---

## Pagina de detalhe da prova: estrutura e extensao para Wave 3 (Componente 08 v4.0+)

A rota `/provas/[id]` e o ponto onde o usuario consulta uma prova
individual. O C08 v4.0 entregou redesign visual + suporte para as 4
rotas v4.0 + tratamento de provas legacy (`rota=NULL`). A Wave 3 v4.0
expandira a maquina de estados de 10 para 14 valores em
`StatusProvaEnum` (Componente 11) — esta secao orienta como adicionar
um novo valor sem reescrever a Timeline ou os labels.

### Arquivos da pagina (estado pos-AUD-W2C08)

| Arquivo | Responsabilidade |
|---|---|
| `frontend/src/app/(dashboard)/provas/[id]/page.tsx` | Header (`Requerimento: NNN · PRV-...`), grid 3x2 de metadata, banner de cancelamento, linha de acoes (`AdminActions`). |
| `frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css` | Estilos do card branco principal + card preto do historico + modais admin. Token `--color-card-art-bg` (ADR-129) garante slot da arte visivel. |
| `frontend/src/app/(dashboard)/provas/[id]/Timeline.tsx` | Componente orientado a dados — derivado de `movimentacoes[]`. As 4 flags booleanas (`isReprovacao`, `isCancelamento`, `isTerminal`, `isRoteamento`) sao calculadas por comparacao direta com strings de `status_novo`. |
| `frontend/src/app/(dashboard)/provas/[id]/AdminActions.tsx` | Botao Cancelar (status em `CANCELAVEIS`) + Reiniciar (`REPROVADA_PELO_VENDEDOR`) — usa `useAuthorization("provas.cancel")` / `provas.restart` da Matriz Wave 1 v4.0. |
| `frontend/src/app/(dashboard)/provas/[id]/VisualizarEtiquetaModal.tsx` | Modal com PDF da etiqueta + QR code (binarios via fetch direto, nao apiFetch). |
| `frontend/src/lib/types/prova.ts` | `StatusProva`, `Rota`, `STATUS_LABELS`, `STATUS_LABELS_SHORT`, `ROTA_LABELS`, helper puro `formatRota` (extraido em AUD-W2C08-003 — testado em `__tests__/prova.test.ts`). |
| `frontend/src/lib/path-active.ts` | Helper puro `isPathActive` (extraido em AUD-W2C08-003 — testado em `__tests__/path-active.test.ts`). Consumido por `(dashboard)/layout.tsx`. |

### Como adicionar valor a `StatusProvaEnum` (4 camadas)

Toda adicao precisa sincronizar 4 camadas (mesmo padrao da secao
`rota_enum`); sem todas, o sistema fica inconsistente.

1. **Python `StatusProvaEnum`** em `backend/app/db/models.py`: adicionar
   o membro com nome `UPPER_SNAKE_CASE` (e.g. `LAMINANDO_MATRIZ`).
2. **PostgreSQL via Alembic**: nova migration com
   `ALTER TYPE status_prova_enum ADD VALUE IF NOT EXISTS '<NOVO>';`
   (Postgres 12+ permite em transacao com `IF NOT EXISTS`).
3. **Tabela de transicoes** (Wave 3 v4.0 — Componente 11):
   `state_machine.TRANSICOES` + `ATORES_POR_TRANSICAO` em
   `backend/app/services/state_machine.py`. Adicionar linhas para
   transicoes que ENTRAM e SAEM do novo estado, respeitando RN/RF.
4. **TypeScript**: em `frontend/src/lib/types/prova.ts`:
   - Adicionar valor a `StatusProva` (union literal).
   - Adicionar entrada em `STATUS_LABELS` (label completo, e.g.
     `"Laminando (matriz)"`).
   - Adicionar entrada em `STATUS_LABELS_SHORT` (label curto para
     listagem, e.g. `"Laminando"`).
   - Adicionar valor em `STATUS_OPTIONS` (ordem canonica de exibicao).
   - O `Record<StatusProva, string>` forca exhaustividade — se faltar
     entrada, `tsc --noEmit` falha.

### Quando expandir as flags em `Timeline.tsx`

A Timeline ja e orientada a dados — adicionar um novo estado nao exige
tocar o componente, **a menos que** o estado precise de cor/badge
distinto. As 4 flags atuais derivam diretamente de `status_novo`:

```ts
isReprovacao: sNovo === "REPROVADA_PELO_VENDEDOR",
isCancelamento: sNovo === "CANCELADA",
isTerminal: sNovo === "RECEBIDA_PELA_CLICHERIA",
isRoteamento: sNovo === "APROVADA_PELO_VENDEDOR",
```

Wave 3 v4.0 podera adicionar `isLaminacao` (cor/badge especial para
LAMINANDO_MATRIZ + LAMINANDO_FILIAL) ou expandir `isRoteamento` para
incluir transicoes de motorista (COM_MOTORISTA_MATRIZ etc.). Decisao
fora do escopo do C08; quando ocorrer, atualizar tambem
`timeline.module.css` com classe correspondente (e.g. `.nodeLaminacao`).

### Tratamento de provas legacy (`rota IS NULL`)

`formatRota(null)` retorna `"—"`. Ate Wave 7 (Componente 21) fazer o
backfill, **65% das provas em producao** sao legacy v3.0 — o
tratamento deve ser preservado em qualquer iteracao futura. AUD-W2C08-011
adicionou `title` HTML no em-dash explicando que e prova legacy.

### Testes Vitest da pagina

Existem em `frontend/src/lib/__tests__/path-active.test.ts` (5 cenarios)
e `frontend/src/lib/types/__tests__/prova.test.ts` (8 cenarios).
Padrao: testar funcoes puras isoladas em `__tests__/<nome>.test.ts`,
sem render do componente — Vitest config esta em `environment: node`
(sem jsdom) para minimizar superficie instalada (Wave 1 v4.0 / AUD-W1V4-005).
