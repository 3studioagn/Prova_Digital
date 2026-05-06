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

**Estado atual do banco de producao:**
- `alembic_version = 012` (migration 012 aplicada na Wave 2 v4.0, 2026-05-04 — ADRs 115-119). Wave 6 nao criou Alembic. Wave 1 v4.0 nao criou Alembic.
- **Divergencia migration 012 (AUD-W2V4-M02)**: a migration Alembic do repo e atomica, mas em producao foi aplicada via MCP `apply_migration` em 3 chunks — `012a` (`ALTER TYPE rota_enum ADD VALUE`), `012b` (`ADD COLUMN codigo_publico` nullable), `012c` (`ALTER COLUMN SET NOT NULL` + indexes + trigger + UPDATE alembic_version). O split foi necessario por precaucao com `ALTER TYPE ADD VALUE` em transacao. `alembic_version='012'` foi setado manualmente apos o terceiro chunk. Estado funcional final equivalente ao da migration atomic do repo; idempotencia validada em `backend/tests/test_migration_012.py` (AUD-W2V4-T03). Em ambiente fresh (dev local, branch Supabase), `alembic upgrade head` produz o mesmo estado em uma so transacao.
- **6 tabelas de dominio** + `alembic_version` (todas com RLS habilitada)
- **`provas_digitais.codigo_publico VARCHAR(20) UNIQUE NOT NULL`** (Wave 2 v4.0, ADR-116): identificador alfanumerico humano-legivel `PRV-AAAA-MM-NNNNNN`. UNIQUE INDEX `idx_provas_codigo_publico`. Embutido no payload do QR Code (DAT §8.1 — idempotencia camera↔digitacao manual via Componente 19 da Wave 3 v4.0).
- **`rota_enum` com 6 valores**: 4 v4.0 (`MATRIZ`/`LAM_MATRIZ`/`FILIAL`/`LAM_FILIAL`) + 2 legacy v3.0 (`PADRAO`/`DIRETA`). Os legacy permanecem ate a Wave 7 (Componente 21) fazer o backfill final — drop nao e suportado pelo Postgres em transacao.
- **Trigger `trg_provas_rota_imutavel` (BEFORE UPDATE)** (Wave 2 v4.0, ADR-117): bloqueia mudanca de rota apos definicao com SQLSTATE 22023. Permite NULL→valor (Wave 7 backfill); bloqueia valor→outro_valor e valor→NULL.
- **Schema `app_private`** (Wave 1 v4.0, RLS 012): 3 funcoes helper SECURITY DEFINER `current_user_is_admin()` / `current_user_setor()` / `current_user_id()` referenciadas pelas 12 policies. Schema NAO listado em `db-schemas` do PostgREST (nao exposto via REST).
- **12 policies RLS** reescritas na Wave 1 v4.0 usando os helpers. Cobertura semantica preservada vs RLS 005/006; `pol_etiquetas_select` estendida para incluir Motorista (status COM_MOTORISTA) e Clicheria (clicheria-states) — fecha lacuna L-RLS-1. **Wave 2 v4.0 nao criou nova policy** — `pol_provas_insert` ja exigia admin (cobre o cenario v4.0).
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
│       │   └── useDashboard.ts          # Wave 4 C15 — GET /dashboard wrapper
│       ├── lib/
│       │   ├── api.ts           # apiFetch wrapper (token injection, ApiError). Nao usar p/ binarios
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
