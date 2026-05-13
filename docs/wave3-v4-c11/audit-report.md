# Relatório de Auditoria · Wave 3 v4.0 · Componente 11

**Auditor:** Claude Opus 4.7 (sessão independente, read-only)
**Data:** 2026-05-13
**Branch auditada:** `wave3-v4/componente-11` (HEAD `f57ba28`)
**Base:** `development` (HEAD `4aaf806`)
**PR aponta para:** `development` (esperado — Wave 3 ainda não mergeada para `main`)
**Veredito final:** **REPROVADO E REFAZER (CONDICIONAL)**

> Bloqueio limitado a correções cirúrgicas no acoplamento Wave 1 v4.0 ↔ Wave 3 v4.0. A
> implementação central da máquina de estados v4.0 (rules, machine, contextos, facade,
> trigger DB, enum em 3 camadas) está correta e bem testada — 100% de cobertura no
> módulo novo. Os 24 pares da Matriz canônica batem par a par com a implementação. Não
> houve violação de escopo nem ignoração de escalações humanas. **O bloqueio é
> funcional**: o sistema de RBAC (scope_filter_for) só conhece estados v3.0 — motorista
> e clicheria não conseguem operar provas v4.0 em seus estados pelo `/scan` nem pela
> listagem. C12 (timeline) pode iniciar em paralelo, mas C11 não deve mergear para
> `development` enquanto AUD-W3C11-001 e AUD-W3C11-002 não forem corrigidos.

---

## Sumário Executivo

**Achados:** 2 CRÍTICOS · 3 ALTOS · 5 MÉDIOS · 6 BAIXOS · 4 INFO = **20 totais**.

**Itens de bloqueio** (impedem aprovação automática):
- **AUD-W3C11-001 (CRÍTICO):** `backend/app/access/scopes.py` lista `_MOTORISTA_STATUSES = (COM_MOTORISTA,)` — apenas legacy. O comentário no próprio arquivo (linhas 47-49) explicitamente declara "Wave 3 v4.0 ampliará para os 3 contextos COM_MOTORISTA_IDA_LAMINACAO / VOLTA_LAMINACAO / ENTREGA_FINAL" — mas a Wave 3 v4.0 não fez. Defesa **primária** quebrada.
- **AUD-W3C11-002 (CRÍTICO):** `_CLICHERIA_STATUSES` lista apenas 3 estados v3.0; falta cobertura dos 4 estados v4.0 onde clicheria atua (`ENCAMINHADA_PARA_LAMINACAO`, `COM_MOTORISTA_IDA_LAMINACAO`, `LAMINACAO_CONCLUIDA`, `COM_MOTORISTA_ENTREGA_FINAL`). US-007 v4.0 e duas últimas transições de Matriz/Lam.Matriz quebradas pela primária.

**Itens HIGH:**
- **AUD-W3C11-003** (HIGH): `shared/access-matrix.json` (`scope_kinds`) descreve `status_motorista_em_transito` como "COM_MOTORISTA*" (com asterisco — sugere todos os v4.0) mas `status_clicheria` enumera explicitamente apenas os 3 estados v3.0. Documentação SSoT inconsistente com Matriz canônica §6 + Notas Técnicas do Backlog C11.
- **AUD-W3C11-004** (HIGH): Falta cobertura de testes API end-to-end para motorista/clicheria escaneando provas em estados v4.0 — bugs como AUD-001/002 não são capturados pela suíte atual.
- **AUD-W3C11-005** (HIGH): Critério de aceitação 15 do prompt (botões inline de transição na detail page) **NÃO entregue**. Documentado em `analysis.md` §A.4 como follow-up, sem decisão registrada do Mario aceitando a limitação.

**Estado da conformidade da Matriz canônica vs implementação:** **CONFORME PAR A PAR**. As 5+10+3+6 = 24 entradas em `TRANSITION_RULES` batem byte-a-byte com a Seção 5.2-5.5 do `RequisitosProvasDigitais_v4_0.docx`. A divergência texto-vs-UML da Filial §5.4 foi escalada (M-1 ADR-146) e resolvida via texto literal. Reprovação tratada como transição embutida em cada `(rota, RETIRADA|ENCAMINHADA_PARA_O_VENDEDOR)`. Cancelamento e Reinicio são transversais via endpoints dedicados.

**Estado da coexistência v3.0 ↔ v4.0:** **PRESERVADA**. v3.0 `state_machine.py` intocado (`git diff` vazio). Roteador no facade `app.state_machine.executar_transicao` despacha por `prova.rota` — provas com `rota IS NULL` ou `rota IN {PADRAO, DIRETA}` vão para v3.0; rota IN {MATRIZ, LAM_MATRIZ, FILIAL, LAM_FILIAL} vão para v4.0. Distribuição em produção (17 provas) sem cruzamento: nenhuma prova legacy em estado v4.0, nenhuma prova v4.0 em estado exclusivo v3.0.

**Estado do trigger no banco e RLS por estado:** **TRIGGER: conforme decisão M-4 (ADR-150) — não há trigger semântico de validação de transições; apenas `trg_provas_rota_imutavel` (Wave 2 v4.0/ADR-117) preservado.** RLS migração 014 aplicada e ativa, expandiu visibilidade de motorista para 4 estados e clicheria para 6 estados. RLS é defesa em profundidade — funciona corretamente. **A primária (Python scope_filter_for) não acompanhou — daí o bloqueio AUD-001/002.**

**Cumprimento das decisões de escalação humana:** **8 de 8 implementadas conforme registrado.** M-1, M-2, M-2b, M-3, M-4, M-5, M-6, M-8 têm ADRs (146-153). **M-7 implementada (mensagens em voz ativa concisa em `machine.py`) sem ADR dedicado** — registrada apenas em `analysis.md §A.1` — finding LOW.

**Estado do `contrato-c12.md`:** **VIÁVEL para o C12.** 408 linhas, 11 seções, tipos exportados, helpers documentados (`contexto_motorista` Python + sugestão TS), sequência canônica de etapas por rota (`ROTA_ETAPAS`), endpoints listados, exemplos funcionais, recomendações de a11y, lista de arquivos que C12 pode tocar vs não tocar. C12 pode iniciar em paralelo à correção dos achados desta auditoria.

**Achados que afetam o C12:** Nenhum bloqueador para C12 isolado. Os achados CRÍTICOS afetam apenas a operação real do C11 com motorista/clicheria — C12 é puramente visual e consome dados via `useScanProva`/`useProvaDetail` que (para vendedor/admin) continuam funcionando.

**Recomendação de próximo passo:** **Sessão de correção dedicada (~2h)** para AUD-001, AUD-002, AUD-003, AUD-004 (adicionar testes que pegariam a regressão). Pós-correção: re-auditoria leve focada nas mudanças. Em paralelo, C12 pode começar consumindo `contrato-c12.md`.

---

## Fase 1 — Verificação de Completude

### Critérios de Aceitação (Backlog Componente 11 v4.0 e §6.3 do prompt de execução)

Reproduzidos abaixo conforme `analysis.md §A.3` + leitura do Backlog. Numeração mantida em paralelo ao prompt de execução do C11.

| # | Critério | Status | Evidência |
|---|---|---|---|
| 1 | Migration Alembic 013 — ALTER TYPE com 7 valores idempotente | ✅ | `backend/migrations/versions/013_expand_status_prova_enum_v4.py` + MCP `SELECT enumlabel FROM pg_enum` retornou 17 valores |
| 2 | `alembic_version='013'` em produção | ✅ | MCP `SELECT version_num FROM alembic_version` retornou `'013'` |
| 3 | Sincronização Python `StatusProvaEnum` ↔ Postgres `status_prova_enum` | ✅ | 17 valores idênticos nas duas camadas + teste `test_status_prova_enum_drift_python_postgres` (skipif em CI) |
| 4 | Sincronização Python ↔ TypeScript | ✅ | `test_status_prova_drift_typescript_python` valida regex contra `lib/types/prova.ts` |
| 5 | Módulo `state_machine/v4/` criado conforme DAT §4.1 | ✅ | `__init__.py` + `v4/{rules,machine,contextos}.py` presentes |
| 6 | Matriz canônica `TRANSITION_RULES` com 24 entradas (5+10+3+6) | ✅ | `test_total_de_entradas_eh_24` + `test_total_por_rota` |
| 7 | Cada transição da Matriz §5.2-5.5 implementada com ator correto | ✅ | 43 testes em `test_rules_v4.py` cobrindo cada `(rota, origem) → destino + ator` |
| 8 | Decisão M-1 (Filial ator = Vendedor) implementada | ✅ | `(FILIAL, CRIADA) → Transition(_ENV_VENDEDOR, _VENDEDOR)` em `rules.py:155` |
| 9 | Roteador v3.0/v4.0 funcional | ✅ | `executar_transicao` facade dispatcha por `is_rota_v4` — 8 testes `test_facade.py` |
| 10 | RLS 014 aplicada com motorista/clicheria nos estados v4.0 | ✅ | MCP `pg_policies` confirma policies expandidas para 4 estados (motorista) + 6 estados (clicheria) |
| 11 | 3 contextos do motorista derivados de `status_novo` | ✅ | `state_machine/v4/contextos.py` + 6 testes em `test_contextos_v4.py` |
| 12 | Audit log com `detalhes_json.contexto_motorista` quando aplicável | ✅ | `machine.py:371-373` + `test_executar_lam_matriz_ida_laminacao_grava_contexto_motorista` |
| 13 | Reinício de ciclo preserva rota (RN-002 v4.0) | ✅ | `machine.py:322-323` (`rota_depois = rota_antes`) + `test_executar_reinicio_preserva_rota_e_incrementa_ciclo` |
| 14 | Cancelamento transversal funciona em todos os ativos v4.0 | ✅ | `pode_cancelar` returns True para 15 estados ativos + `AdminActions.tsx CANCELAVEIS` expandido |
| 15 | **Botões inline de transição na página de detalhe** | ❌ | **NÃO ENTREGUE.** Documentado em `analysis.md §A.4`. Scanner em `/escanear` segue como caminho canônico — RNF-002 (≤ 2s) preservado. |
| 16 | Frontend `StatusProva` com 17 valores + labels | ✅ | `lib/types/prova.ts:27-50` + STATUS_LABELS + STATUS_LABELS_SHORT |
| 17 | `AdminActions.tsx CANCELAVEIS` expandido | ✅ | `git diff` mostra 7 v4.0 adicionados (commit `1a41e25`) |
| 18 | `ReportGeral.tsx STATUS_DONUT_COLOR` expandido | ✅ | `git diff` mostra +13 linhas (commit `7fb7629` parcial) |
| 19 | Coexistência preservada: provas legacy continuam funcionando | ✅ | v3.0 `state_machine.py` intocado + facade roteia corretamente + distribuição em produção verificada |
| 20 | Cobertura ≥ 95% no módulo v4 | ✅ | `analysis.md §A.5`: 100% em `app/state_machine/v4/*` (187/187 stmts) |
| 21 | Anti-enumeração preservada (404 genérico) | ⚠️ | RLS sim. `/scan` mantém DAT §8.2. Porém, **AUD-001/002 fazem motorista/clicheria receberem 404 EM PROVAS QUE DEVERIAM PODER ESCANEAR** — não é vazamento de enumeração, é o oposto (falso negativo). |
| 22 | Audit log gravado em todas as transições | ✅ | `log_audit` chamado em `executar_transicao_v4` |
| 23 | `contrato-c12.md` criado e completo | ✅ | 408 linhas, 11 seções |
| 24 | Documentação atualizada (CHANGELOG, DECISIONS, CLAUDE.md, analysis §Execução) | ✅ | Commits `f57ba28` |

**Total: 22 atendidos / 1 deferido (#15) / 1 com nuance funcional (#21).**

### Definition of Done Global (10 itens — Backlog §2)

| # | Item | Status | Evidência |
|---|---|---|---|
| 1 | Migration Alembic versionada e reversível | ⚠️ | Versionada; downgrade documentado como no-op (Postgres não suporta DROP VALUE). Aceitável arquiteturalmente (ADR-148). |
| 2 | RLS versionada em `/migrations/rls/` | ✅ | `014_expand_visibility_v4_states.sql` (179 LOC) com DROP+CREATE idempotente |
| 3 | Testes ≥ 95% na camada de domínio | ✅ | 100% em `state_machine/v4/*` |
| 4 | Backend lint (ruff) limpo | 🔍 | Não validado nesta sessão (modo read-only). Suposto verde por CI. |
| 5 | Frontend `tsc --noEmit` exit 0 | 🔍 | `analysis.md §A.5` declara verde. Não re-rodado nesta sessão. |
| 6 | E2E flow tests para cada rota | ✅ | `test_fluxo_completo_rota_*` (4 testes) + `test_fluxo_reprovacao_e_reinicio_lam_matriz` |
| 7 | Documentação coerente (CLAUDE.md, DECISIONS.md, CHANGELOG.md) | ✅ | Todos atualizados com seção dedicada |
| 8 | Sem novos advisor Supabase | ✅ | MCP `get_advisors`: 0 novos. Pré-existentes mantidos (alembic_version RLS, leaked password). |
| 9 | Contrato preparatório para próximo componente | ✅ | `contrato-c12.md` completo |
| 10 | Zero regressão funcional em waves anteriores | ❌ | **Quebra funcional em motorista/clicheria operando provas v4.0 — AUD-001/002.** Bug introduzido pela combinação migration 013 + RLS 014 + scope_filter_for não-atualizado. |

### Cumprimento das Decisões de Escalação Humana

| Decisão | Registrada em DECISIONS.md? | ADR | Implementação bate com a resposta? |
|---|---|---|---|
| M-1 — Ator FILIAL.CRIADA→ENCAMINHADA_PARA_O_VENDEDOR | ✅ | ADR-146 | ✅ `rules.py:155` |
| M-2 — Estrutura do enum (ALTER TYPE) | ✅ | ADR-147 | ✅ Migration 013 |
| M-2b — COM_MOTORISTA legacy ≠ ENTREGA_FINAL v4.0 | ✅ | ADR-148 | ✅ valores distintos no enum + `contexto_motorista` unifica visualmente |
| M-3 — Reusar `POST /{id}/transicoes` (sem novos endpoints) | ✅ | ADR-149 | ✅ Total de rotas backend = 34 (inalterado) |
| M-4 — Sem trigger PostgreSQL semântico | ✅ | ADR-150 | ✅ MCP `pg_get_triggerdef` confirma só `trg_provas_rota_imutavel` + `_updated_at` |
| M-5 — Contexto derivado de status + audit_log.detalhes_json | ✅ | ADR-151 | ✅ `machine.py:371-373` + `contextos.py` |
| M-6 — Payload `TransicaoRequest` inalterado | ✅ | ADR-152 | ✅ `git diff` em `schemas/prova.py` vazio |
| **M-7 — Mensagens de erro pt-BR conciso, voz ativa** | ⚠️ | **AUSENTE** (só em `analysis.md §A.1`) | ✅ implementação verificada em `machine.py:186-207` |
| M-8 — Sem rate limit nesta wave (follow-up) | ✅ | ADR-153 | ✅ unificado com follow-up de ADR-145 (C19) |

**Resultado:** 8/8 decisões implementadas conforme o registrado. M-7 carece de ADR dedicado — **finding LOW (AUD-W3C11-014)**.

### Conformidade da Matriz de Transições — comparação par a par

Reproduzo a Matriz canônica (Seção 5.2-5.5 do `RequisitosProvasDigitais_v4_0.docx`) e a confronto com a tabela em `backend/app/state_machine/v4/rules.py`.

#### §5.2 Matriz (5 transições não-iniciais)

| # | Origem | Destino canônico | Ator canônico | Implementação | Status |
|---|---|---|---|---|---|
| 1 | Criada | Retirada pelo Vendedor | Vendedor | `(MATRIZ, CRIADA) → (RETIRADA, VENDEDOR)` | ✅ |
| 2 | Retirada pelo Vendedor | Aprovada pelo Vendedor | Vendedor | `(MATRIZ, RETIRADA) → (APROVADA, VENDEDOR)` | ✅ |
| 2′ | Retirada pelo Vendedor | Reprovada pelo Vendedor (transversal §5.6) | Vendedor | `_REPROVAR_VENDEDOR` embutida no frozenset | ✅ |
| 3 | Aprovada pelo Vendedor | De volta à 3Studio | 3Studio | `(MATRIZ, APROVADA) → (DE_VOLTA, STUDIO)` | ✅ |
| 4 | De volta à 3Studio | Com Motorista (entrega final) | Motorista | `(MATRIZ, DE_VOLTA) → (COM_MOTORISTA_ENTREGA_FINAL, MOTORISTA)` | ✅ |
| 5 | Com Motorista (entrega final) | Recebida pela Clicheria | Clicheria | `(MATRIZ, COM_MOTORISTA_ENTREGA_FINAL) → (RECEBIDA, CLICHERIA)` | ✅ |

#### §5.3 Lam. Matriz (10 transições não-iniciais)

| # | Origem | Destino canônico | Ator canônico | Implementação | Status |
|---|---|---|---|---|---|
| 1 | Criada | Encaminhada para Laminação | 3Studio | `(LAM_MATRIZ, CRIADA) → (ENV_LAMINACAO, STUDIO)` | ✅ |
| 2 | Encaminhada para Laminação | Com Motorista (ida laminação) | Motorista | `(LAM_MATRIZ, ENV_LAMINACAO) → (MOT_IDA, MOTORISTA)` | ✅ |
| 3 | Com Motorista (ida laminação) | Laminação Concluída | Clicheria | `(LAM_MATRIZ, MOT_IDA) → (LAMINACAO_OK, CLICHERIA)` | ✅ |
| 4 | Laminação Concluída | Com Motorista (volta laminação) | Motorista | `(LAM_MATRIZ, LAMINACAO_OK) → (MOT_VOLTA, MOTORISTA)` | ✅ |
| 5 | Com Motorista (volta laminação) | De volta à 3Studio (pós-laminação) | 3Studio | `(LAM_MATRIZ, MOT_VOLTA) → (POS_LAMINACAO, STUDIO)` | ✅ |
| 6 | De volta à 3Studio (pós-laminação) | Retirada pelo Vendedor | Vendedor | `(LAM_MATRIZ, POS_LAMINACAO) → (RETIRADA, VENDEDOR)` | ✅ |
| 7 | Retirada pelo Vendedor | Aprovada pelo Vendedor | Vendedor | `(LAM_MATRIZ, RETIRADA) → (APROVADA, VENDEDOR)` | ✅ |
| 7′ | Retirada pelo Vendedor | Reprovada pelo Vendedor | Vendedor | `_REPROVAR_VENDEDOR` embutida | ✅ |
| 8 | Aprovada pelo Vendedor | De volta à 3Studio | 3Studio | `(LAM_MATRIZ, APROVADA) → (DE_VOLTA, STUDIO)` | ✅ |
| 9 | De volta à 3Studio | Com Motorista (entrega final) | Motorista | `(LAM_MATRIZ, DE_VOLTA) → (COM_MOTORISTA_ENTREGA_FINAL, MOTORISTA)` | ✅ |
| 10 | Com Motorista (entrega final) | Recebida pela Clicheria | Clicheria | `(LAM_MATRIZ, COM_MOTORISTA_ENTREGA_FINAL) → (RECEBIDA, CLICHERIA)` | ✅ |

#### §5.4 Filial (3 transições não-iniciais)

| # | Origem | Destino canônico | Ator canônico (texto) | UML | Implementação | Status |
|---|---|---|---|---|---|---|
| 1 | Criada | Encaminhada para o Vendedor | **Vendedor** (texto literal) | 3Studio | `(FILIAL, CRIADA) → (ENV_VENDEDOR, VENDEDOR)` — texto literal prevalece (ADR-146 / M-1) | ✅ |
| 2 | Encaminhada para o Vendedor | Aprovada pelo Vendedor | Vendedor | Vendedor | `(FILIAL, ENV_VENDEDOR) → (APROVADA, VENDEDOR)` | ✅ |
| 2′ | Encaminhada para o Vendedor | Reprovada pelo Vendedor | Vendedor | Vendedor | `_REPROVAR_VENDEDOR` embutida | ✅ |
| 3 | Aprovada pelo Vendedor | Recebida pela Clicheria | Clicheria | Clicheria | `(FILIAL, APROVADA) → (RECEBIDA, CLICHERIA)` | ✅ |

#### §5.5 Lam. Filial (6 transições não-iniciais)

| # | Origem | Destino canônico | Ator canônico | Implementação | Status |
|---|---|---|---|---|---|
| 1 | Criada | Encaminhada para Laminação | 3Studio | `(LAM_FILIAL, CRIADA) → (ENV_LAMINACAO, STUDIO)` | ✅ |
| 2 | Encaminhada para Laminação | Com Motorista (ida laminação) | Motorista | `(LAM_FILIAL, ENV_LAMINACAO) → (MOT_IDA, MOTORISTA)` | ✅ |
| 3 | Com Motorista (ida laminação) | Laminação Concluída | Clicheria | `(LAM_FILIAL, MOT_IDA) → (LAMINACAO_OK, CLICHERIA)` | ✅ |
| 4 | Laminação Concluída | Encaminhada para o Vendedor | Vendedor | `(LAM_FILIAL, LAMINACAO_OK) → (ENV_VENDEDOR, VENDEDOR)` | ✅ |
| 5 | Encaminhada para o Vendedor | Aprovada pelo Vendedor | Vendedor | `(LAM_FILIAL, ENV_VENDEDOR) → (APROVADA, VENDEDOR)` | ✅ |
| 5′ | Encaminhada para o Vendedor | Reprovada pelo Vendedor | Vendedor | `_REPROVAR_VENDEDOR` embutida | ✅ |
| 6 | Aprovada pelo Vendedor | Recebida pela Clicheria | Clicheria | `(LAM_FILIAL, APROVADA) → (RECEBIDA, CLICHERIA)` | ✅ |

**Contagem:**
- Não-iniciais canônicas: 5 + 10 + 3 + 6 = **24 transições rota-específicas**
- Reprovações transversais embutidas em `(MATRIZ/LAM_MATRIZ, RETIRADA)` + `(FILIAL/LAM_FILIAL, ENV_VENDEDOR)` = 4 origens × 1 reprovação cada = 4 (não contadas como entrada separada, ramo dentro do frozenset)
- Cancelamento + Reinício: 2 transversais via endpoints dedicados (`/cancelar`, `/reiniciar-ciclo`)

**Implementação:** `len(TRANSITION_RULES) == 24` validado por `test_total_de_entradas_eh_24` em `test_rules_v4.py:31`.

**Veredito:** **CONFORME PAR A PAR — zero drift entre Matriz canônica e implementação.**

### Sincronização do Enum em 3 Camadas

| Camada | Valores | Contagem | Fonte |
|---|---|---|---|
| Python `StatusProvaEnum` | CRIADA, RETIRADA_PELO_VENDEDOR, APROVADA_PELO_VENDEDOR, DE_VOLTA_3STUDIO, COM_MOTORISTA, ENVIADA_PARA_CLICHERIA, ENCAMINHADA_A_CLICHERIA, RECEBIDA_PELA_CLICHERIA, REPROVADA_PELO_VENDEDOR, CANCELADA, COM_MOTORISTA_IDA_LAMINACAO, COM_MOTORISTA_VOLTA_LAMINACAO, COM_MOTORISTA_ENTREGA_FINAL, ENCAMINHADA_PARA_LAMINACAO, LAMINACAO_CONCLUIDA, DE_VOLTA_3STUDIO_POS_LAMINACAO, ENCAMINHADA_PARA_O_VENDEDOR | 17 | `backend/app/db/models.py:32-80` |
| PostgreSQL `pg_enum status_prova_enum` | Mesmo conjunto (ordem alfabética para v4.0 conforme `enumsortorder` 11-17) | 17 | MCP `SELECT enumlabel FROM pg_enum` |
| TypeScript `StatusProva` | Mesmo conjunto | 17 | `frontend/src/lib/types/prova.ts:27-50` |

**Diff:** **0 valores divergentes.** Conjuntos idênticos nas 3 camadas. Teste automatizado `test_status_prova_drift_typescript_python` valida regex contra arquivo TS; `test_status_prova_enum_drift_python_postgres` valida contra Postgres real (skipif sem `INTEGRATION_DATABASE_URL`).

### Coexistência v3.0 vs v4.0

#### Inspeção de código

| Item | Estado | Evidência |
|---|---|---|
| v3.0 `app.services.state_machine` intocada | ✅ | `git diff development...wave3-v4/componente-11 -- backend/app/services/state_machine.py` retorna vazio |
| Roteador funcional | ✅ | `app.state_machine.executar_transicao` dispatcha via `is_rota_v4(prova.rota)` — `__init__.py:64-107` |
| `is_rota_v4`: NULL/legacy → False; v4 → True | ✅ | 7 testes em `test_facade.py` (NULL + PADRAO + DIRETA + 4 v4.0) |
| Prova v4.0 NÃO acessa máquina v3.0 | ✅ | `executar_transicao_v4` rejeita se `rota not in ROTAS_V4` (`machine.py:263-269`) |
| Prova legacy continua usando v3.0 | ✅ | facade chama `_executar_v3` quando `not is_rota_v4` |

#### Inspeção do banco (MCP)

Query: `SELECT rota::text, status::text, COUNT(*) FROM provas_digitais GROUP BY rota, status ORDER BY rota, status;`

| rota | status | qtd |
|---|---|---|
| DIRETA | CANCELADA | 1 |
| DIRETA | RECEBIDA_PELA_CLICHERIA | 2 |
| MATRIZ | CRIADA | 1 |
| PADRAO | CANCELADA | 2 |
| `NULL` | CANCELADA | 4 |
| `NULL` | CRIADA | 5 |
| `NULL` | REPROVADA_PELO_VENDEDOR | 2 |

**Total 17 provas.** **Sem cruzamento:**
- Nenhuma prova com `rota IS NULL` em estado exclusivo v4.0 — todos os estados em provas legacy são v3.0 (CRIADA, CANCELADA, REPROVADA — compartilhados ou legacy puros).
- Nenhuma prova com `rota IN {MATRIZ, LAM_MATRIZ, FILIAL, LAM_FILIAL}` em estado legacy puro — a única prova v4.0 (MATRIZ + CRIADA) usa o estado compartilhado CRIADA (válido nas duas máquinas).
- Provas legacy `PADRAO`/`DIRETA` permanecem com seus estados terminais ou ativos v3.0.

**Veredito:** **COEXISTÊNCIA PRESERVADA INTEGRALMENTE.**

### Trigger no Banco

```sql
-- pg_get_triggerdef em provas_digitais, movimentacoes, audit_logs:
trg_provas_rota_imutavel    BEFORE UPDATE WHEN (old.rota IS DISTINCT FROM new.rota)
trg_provas_updated_at       BEFORE UPDATE (set updated_at = now())
trg_movimentacoes_imutavel  BEFORE DELETE OR UPDATE (RAISE)
trg_audit_logs_imutavel     BEFORE DELETE OR UPDATE (RAISE)
```

**Análise:**
- Nenhum trigger semântico de validação de transição foi criado — consistente com Decisão M-4 (ADR-150) e DAT §4.2 princípio de invariância.
- `trg_provas_rota_imutavel` (ADR-117) preservado intocado — continua bloqueando mudança da rota após definição (permitindo NULL → valor para Wave 7 backfill).
- Triggers de imutabilidade em `movimentacoes` e `audit_logs` operacionais — RNF-005.

### RLS por Estado v4.0 — Defesa em Profundidade

#### Policies pos-migration 014

| Política | Cobertura motorista | Cobertura clicheria |
|---|---|---|
| `pol_provas_select` | 4 estados: COM_MOTORISTA + 3 v4.0 contextos | 6 estados: 3 v3.0 + 3 v4.0 (ENCAMINHADA_PARA_LAMINACAO, COM_MOTORISTA_IDA_LAMINACAO, LAMINACAO_CONCLUIDA) |
| `pol_movimentacoes_select` | 4 estados (via subquery em provas) | 6 estados (via subquery) |
| `pol_etiquetas_select` | 4 estados (via EXISTS em provas) | 6 estados (via EXISTS) |

**Lacuna funcional vs Matriz §5:**
- COM_MOTORISTA_ENTREGA_FINAL **NÃO está** na lista de clicheria. Cenário: motorista entrega prova → clicheria escaneia em `COM_MOTORISTA_ENTREGA_FINAL` para confirmar recebimento. Como a clicheria não vê esse estado, a query falha. **Limitação ressalvada — operação ocorre pelo `/scan` que usa service_role → bypassa RLS → consulta backend → primária via scope_filter_for falha (AUD-002).**

A RLS é DEFESA em profundidade. O bloqueio funcional está na primária (Python `scope_filter_for` — AUD-001/002).

#### Anti-enumeração

- `/scan` mantém 404 genérico para "não encontrada" / "fora do scope" / "formato inválido" (DAT §8.2) — preservado pelo C19.
- C11 não altera o handler de `/scan` exceto pelo roteador interno de `_computar_transicoes_permitidas`.
- **Porém AUD-001/002 cria FALSO NEGATIVO** — motorista/clicheria recebem 404 em provas que deveriam acessar. Anti-enumeração preservada; funcionalidade quebrada.

### Detecção de Contexto do Motorista

Tabela de derivação (verificada em `contextos.py` + `test_contextos_v4.py`):

| Status novo | Contexto esperado | Implementado em `contexto_motorista()` |
|---|---|---|
| `COM_MOTORISTA_IDA_LAMINACAO` | `"ida_laminacao"` | ✅ `contextos.py:47-48` |
| `COM_MOTORISTA_VOLTA_LAMINACAO` | `"volta_laminacao"` | ✅ `contextos.py:49-50` |
| `COM_MOTORISTA_ENTREGA_FINAL` | `"entrega_final"` | ✅ `contextos.py:51-52` |
| `COM_MOTORISTA` (legacy v3.0) | `"entrega_final"` (compat) | ✅ `contextos.py:53-57` |
| Qualquer outro status | `None` | ✅ `contextos.py:58` |

**Contexto por rota:**

| Rota | Estados de motorista visitados | Contextos correspondentes | Quem confirma a chegada |
|---|---|---|---|
| Matriz | COM_MOTORISTA_ENTREGA_FINAL | entrega_final (1) | Clicheria |
| Lam. Matriz | COM_MOTORISTA_IDA_LAMINACAO, COM_MOTORISTA_VOLTA_LAMINACAO, COM_MOTORISTA_ENTREGA_FINAL | ida_laminacao, volta_laminacao, entrega_final (3) | Clicheria, 3Studio, Clicheria respectivamente |
| Filial | (nenhum — vendedor entrega à clicheria diretamente) | — | — |
| Lam. Filial | COM_MOTORISTA_IDA_LAMINACAO | ida_laminacao (1) | Clicheria |

**Coerência com UML 06.2 + 06.4:** ✅ confirmada em `analysis.md §4.9`.

### Cancelamento Transversal

| Cenário | Esperado | Verificado |
|---|---|---|
| Cancelar prova legacy v3.0 em estado ativo | OK (pode_cancelar = True) | `test_pode_cancelar_estados_ativos_v3_e_v4` |
| Cancelar prova v4.0 em estado ativo | OK | `test_pode_cancelar_estados_ativos_v3_e_v4` |
| Cancelar em RECEBIDA_PELA_CLICHERIA | REJEITAR | `test_nao_pode_cancelar_recebida_pela_clicheria` + `test_executar_cancelamento_rejeita_terminal` |
| Cancelar prova já CANCELADA | REJEITAR | `test_nao_pode_cancelar_ja_cancelada` |
| Admin pode cancelar | OK | `test_executar_cancelamento_admin_v4` |
| Não-admin com setor=STUDIO pode cancelar (RN-005) | OK | `test_executar_cancelamento_studio_sem_admin` |
| Vendedor tenta cancelar | REJEITAR (AtorNaoAutorizadoError) | `test_executar_cancelamento_vendedor_rejeitado` |
| Motivo obrigatório | OK (rejeitar se ausente/whitespace) | `test_executar_cancelamento_exige_motivo` |

**Veredito:** Cobertura completa. Comportamento idêntico para v3.0 e v4.0 — `pode_cancelar` em `machine.py:64-75` retorna `True` para qualquer status ∉ {RECEBIDA, CANCELADA}.

### Reinício de Ciclo

| Cenário | Esperado | Verificado |
|---|---|---|
| Reinício de prova v4.0 reprovada | OK + ciclo+1 + rota preservada (RN-002 v4.0 + ADR-123) | `test_executar_reinicio_preserva_rota_e_incrementa_ciclo` |
| Reinício por vendedor | REJEITAR | `test_executar_reinicio_vendedor_rejeitado` |
| Prova v4.0 reprovada → reiniciada → fluxo completo | Encadeia corretamente | `test_fluxo_reprovacao_e_reinicio_lam_matriz` |
| Rota preservada em todas as 4 v4.0 | OK | `executar_transicao_v4` setando `rota_depois = rota_antes` (`machine.py:322-323`) |

**Veredito:** Conformidade com RF-009 v4.0 + ADR-123.

### Roteamento v3.0 ↔ v4.0

| Cenário | Esperado | Verificado |
|---|---|---|
| `prova.rota IS NULL` → máquina v3.0 | Dispatcha para `app.services.state_machine` | `test_is_rota_v4_none_eh_false` + `executar_transicao` em `__init__.py:87-107` |
| `prova.rota IN {PADRAO, DIRETA}` → v3.0 | Dispatcha para v3.0 | `test_is_rota_v4_legacy_padrao_eh_false`, `_legacy_direta_eh_false` |
| `prova.rota IN {MATRIZ, LAM_MATRIZ, FILIAL, LAM_FILIAL}` → v4.0 | Dispatcha para `executar_transicao_v4` | `test_is_rota_v4_v4_eh_true` (parametrizado) |
| Endpoint `/scan` aplica roteamento | OK | `_computar_transicoes_permitidas` em `provas.py:1697-1709` |
| Endpoint `/{id}/transicoes` aplica roteamento | OK (via facade) | Import `from app.state_machine import executar_transicao` em `provas.py:107-111` |

### Integração com C08 (Página de Detalhe)

| Item | Esperado | Verificado |
|---|---|---|
| 7 novos estados em STATUS_LABELS | OK | `lib/types/prova.ts:202-210` |
| 7 novos estados em STATUS_LABELS_SHORT | OK | `lib/types/prova.ts:227-234` |
| 7 novos estados em STATUS_OPTIONS | OK | `lib/types/prova.ts:286-303` |
| `AdminActions.CANCELAVEIS` estendido com 7 v4.0 | OK | commit `1a41e25` |
| Sem CSS novo introduzido | OK | `git diff` em `*.module.css` retorna vazio para o C11 |
| Sem Framer Motion novo | OK | `git diff` em `package.json` vazio |
| Timeline.tsx **intocada** | OK | C12 receberá o refactor visual |
| Página `/provas/[id]/page.tsx` **intocada** | OK | Labels fluem automaticamente via `STATUS_LABELS[prova.status]` |
| **Critério 15 — botões inline de transição** | ❌ **NÃO ENTREGUE** | Documentado em `analysis.md §A.4` como follow-up |

### Anti-enumeração nas Mensagens de Erro

Verificado em `machine.py`:
- `validar_transicao_v4` levanta `TransicaoInvalidaError` com texto `f"Esta prova segue a rota {rota.value}, que nao permite a transicao {status_atual.value} -> {status_destino.value}."` — voz ativa, conciso (Decisão M-7).
- `AtorNaoAutorizadoError` com `f"Voce nao tem permissao para esta transicao (setor {usuario.setor.value})."` — não expõe estado destino ou rota da prova.
- Handler HTTP em `provas.py` (ADR-084 preservado): TransicaoInvalidaError → 409; AtorNaoAutorizadoError → 422; 404 genérico para prova fora de scope.

**Veredito:** mensagens consistentes com DAT §8.2. Anti-enumeração preservada por construção.

### Performance (RNF-001 ≤ 1s e RNF-002 ≤ 2s)

| Item | Esperado | Status |
|---|---|---|
| `transicoes_validas_v4` lookup O(1) | OK | `dict.get((rota, status))` é O(1) |
| `validar_transicao_v4` sem N+1 | OK | Iteração linear sobre `frozenset` pequeno (max 2-3 elementos) |
| `executar_transicao_v4` async | OK | `async def` em `machine.py:213` |
| `pol_movimentacoes_select` com subquery | ⚠️ | `prova_id IN (SELECT pd.id ...)` 2x — escala razoavelmente com índice em `prova_id` mas pode degradar em altas linhas. Veja AUD-W3C11-016. |
| Métricas reais não medidas | ⚠️ | `analysis.md §A.5` declara "Lookup O(1) na tabela em memória; benchmark indireto via 961 testes em 4s" — não há benchmark dedicado |

### Documentação Atualizada

| Arquivo | Status | Observação |
|---|---|---|
| `CHANGELOG.md` | ✅ | Seção dedicada com lista de migrations, decisões, testes, métricas. Bug menor de redação: "9 estados v3.0 para 14 estados v4.0" — implementação real são 10 v3.0 + 7 v4.0 = 17 (canônica 14 nomes únicos por unificação semântica). LOW. |
| `DECISIONS.md` | ✅ | ADR-146 a 153 com formato consistente. **M-7 ausente** — só em `analysis.md §A.1`. LOW. |
| `CLAUDE.md` | ✅ | Seção "Máquina de Estados: coexistência v3.0 e v4.0" presente, prática, instruções para adicionar valor ao enum em 3+ camadas. |
| `docs/wave3-v4-c11/analysis.md` | ✅ | Gate 1 completo + Apêndice A Execução com diffs proposto/executado |
| `docs/wave3-v4-c11/contrato-c12.md` | ✅ | 408 LOC, 11 seções, exemplos completos, tipos exportados |
| `docs/wave3-v4-c11/_agent_extraction.md` | ✅ | Extração literal dos 4 docs canônicos (633 LOC) |

### Migrations Versionadas

| Migration | Versionada | Reversível | Idempotente | Aplicada |
|---|---|---|---|---|
| Alembic 013 | ✅ | ⚠️ downgrade no-op (Postgres não suporta DROP VALUE) | ✅ `ADD VALUE IF NOT EXISTS` | ✅ `alembic_version='013'` em produção |
| RLS 014 | ✅ | ✅ DROP+CREATE | ✅ | ✅ MCP confirma policies expandidas |

**Validação `alembic upgrade head` em ambiente limpo:** Não re-rodado nesta sessão (modo read-only). Em CI seria validado.

### Refactor Coordenado Completo

| Camada | Esperado | Status |
|---|---|---|
| Backend Python (`state_machine/v4/*`, `provas.py` roteamento) | OK | `git diff` |
| Banco (migration 013 + RLS 014) | OK | MCP |
| Frontend (tipos + AdminActions + ReportGeral) | OK | `git diff` |
| **Backend RBAC (`access/scopes.py`)** | ❌ | **NÃO atualizado** — AUD-W3C11-001/002 |
| **SSoT (`shared/access-matrix.json scope_kinds`)** | ❌ | **NÃO atualizado** — AUD-W3C11-003 |
| C10 service layer (`identificacao-prova.ts`) | OK (intocada) | `git diff` vazio |
| C06 (cadastro) | OK (intocado) | `git diff` vazio |
| C19 (fallback manual) | OK (intocado) | `git diff` vazio |
| C08 (detail page) | OK (sem touch direto — labels fluem via STATUS_LABELS) | `git diff` vazio |
| v3.0 state_machine | OK (intocada) | `git diff` vazio |

### Violação de Escopo

| Item proibido | Verificação | Resultado |
|---|---|---|
| Máquina v3.0 modificada | `git diff backend/app/services/state_machine.py` | ✅ Vazio |
| Timeline visual (C12) implementada | `git diff Timeline.tsx, timeline.module.css` | ✅ Vazio |
| Backfill da `rota` executado | MCP: `rota IS NULL` ainda existe em 11 provas | ✅ Não executado |
| Coluna `rota` tornada NOT NULL | MCP: NULL ainda permitido | ✅ Não alterada |
| Máquina v3.0 removida | `app/services/state_machine.py` existe | ✅ Preservada |
| UI visual nova não-autorizada | `git diff *.module.css` | ✅ Vazio |
| CSS novo | `git diff *.module.css` | ✅ Vazio |
| Framer Motion novo | `git diff package.json` | ✅ Vazio |
| Dashboard/relatórios v4.0 | `git diff provas.py /dashboard, reports.py` | ✅ Sem mudança funcional (apenas `STATUS_DONUT_COLOR` em ReportGeral) |
| Decisões M-1..M-8 puladas | DECISIONS.md inspecionado | ✅ Apenas M-7 sem ADR formal (LOW) |

**Veredito:** **NENHUMA violação de escopo.**

### PR aponta para `development`

`CHANGELOG.md` declara: "Branch: `wave3-v4/componente-11` → PR contra `development`". Wave 3 completa (C10 + C19 + C11 + C12) só mergeará para `main` após C12 e correções pendentes.

---

## Fase 2 — Auditoria Qualitativa Aprofundada

### Achados de Segurança

#### AUD-W3C11-018 (INFO) — Sem trigger PostgreSQL semântico

Aprovado por Decisão M-4 (ADR-150). Defesa em profundidade depende de:
1. Backend FastAPI como única porta legítima de UPDATE em `status` (service_role)
2. RLS deny-by-default em INSERT/UPDATE/DELETE (`pol_provas_update` = admin only)
3. Check constraint `status_anterior != status_novo` em `movimentacoes`
4. Triggers de imutabilidade em `movimentacoes`/`audit_logs`

Risco aceito: admin com acesso direto via psql pode contornar validação semântica. Aceitável por design (operador de banco).

#### AUD-W3C11-019 (INFO) — Race conditions

`executar_transicao` usa `FOR UPDATE` no `_carregar_prova_com_scoping(..., lock=True)` (ADR-084). Race entre 2 usuários simultâneos resulta em 409 Conflict no segundo. Verificado por análise estática.

#### AUD-W3C11-020 (INFO) — Anti-enumeração preservada

Mensagens de erro de transição inválida (`TransicaoInvalidaError`) não expõem outras provas; apenas o status_atual + status_destino + rota da prova **que o usuário já viu**. Não é vetor de enumeração.

### Achados de Correção (Bugs Funcionais)

#### AUD-W3C11-001 (CRÍTICO) — `_MOTORISTA_STATUSES` não atualizado para v4.0

**Arquivo:** `backend/app/access/scopes.py:50-52`
```python
_MOTORISTA_STATUSES: tuple[StatusProvaEnum, ...] = (
    StatusProvaEnum.COM_MOTORISTA,
)
```

**Comentário existente no próprio arquivo (linhas 47-49) avisa do follow-up:**
```python
# Status que motorista visualiza ("Em Trânsito"). Wave 1 v4.0: apenas
# COM_MOTORISTA (legado v3.0). Wave 3 v4.0 ampliara para os 3 contextos
# COM_MOTORISTA_IDA_LAMINACAO / VOLTA_LAMINACAO / ENTREGA_FINAL.
```

**Impacto:** A função `scope_filter_for("provas.list", motorista_user)` retorna `ProvaDigital.status.in_(('COM_MOTORISTA',))`. Quando aplicada em:
- `GET /api/v1/provas/` (listagem)
- `POST /api/v1/provas/scan` (scanner via `_carregar_prova_por_codigo_publico_com_scoping` e `_carregar_prova_por_nro_req_com_scoping` em `provas.py:1856-1858`)
- `GET /api/v1/provas/{id}/...` (qualquer detalhe via `_carregar_prova_com_scoping`)

→ **motorista NÃO consegue ver/escanear provas v4.0 em qualquer um dos 3 estados v4.0 de motorista** (`COM_MOTORISTA_IDA_LAMINACAO`, `COM_MOTORISTA_VOLTA_LAMINACAO`, `COM_MOTORISTA_ENTREGA_FINAL`).

**Cenários quebrados:**
- Lam. Matriz transição 2: motorista escaneia prova em `ENCAMINHADA_PARA_LAMINACAO` ✗ (clicheria scope tampouco cobre — ver AUD-002).
- Lam. Matriz transição 4: motorista escaneia prova em `LAMINACAO_CONCLUIDA` → IDA_LAMINACAO ✗ (clicheria scope falha — AUD-002; mesmo se OK, motorista não veria a prova no momento seguinte).
- Lam. Filial transição 2: motorista escaneia prova em `ENCAMINHADA_PARA_LAMINACAO` ✗.
- Matriz transição 4: motorista escaneia prova em `DE_VOLTA_3STUDIO` → ENTREGA_FINAL ✗.
- Lam. Matriz transição 9: motorista em `DE_VOLTA_3STUDIO` (compartilhado) ✗ (não cai sob scope motorista v3.0).

**Resultado em produção:** sequência inteira de transições motorista em todas as 4 rotas v4.0 retorna **404 "Prova não encontrada"** (mensagem anti-enumeração) para qualquer usuário motorista.

**A defesa secundária (RLS migração 014) está correta e cobre os 4 estados. Mas como o backend usa service_role e bypassa RLS, a primária é a única que vale.**

**Recomendação:**
```python
_MOTORISTA_STATUSES: tuple[StatusProvaEnum, ...] = (
    StatusProvaEnum.COM_MOTORISTA,                       # legacy v3.0
    StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO,         # v4.0
    StatusProvaEnum.COM_MOTORISTA_VOLTA_LAMINACAO,       # v4.0
    StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL,         # v4.0
)
```

**Dono sugerido:** sessão de correção pós-auditoria — atualizar `scopes.py` + adicionar testes E2E motorista + atualizar `_clicheria_divergence_note` no JSON.

#### AUD-W3C11-002 (CRÍTICO) — `_CLICHERIA_STATUSES` não atualizado para v4.0

**Arquivo:** `backend/app/access/scopes.py:55-59`
```python
_CLICHERIA_STATUSES: tuple[StatusProvaEnum, ...] = (
    StatusProvaEnum.ENVIADA_PARA_CLICHERIA,
    StatusProvaEnum.ENCAMINHADA_A_CLICHERIA,
    StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
)
```

**Impacto:** Análogo a AUD-001 para clicheria. Os 4 estados v4.0 que clicheria deveria ver não estão listados:
- `ENCAMINHADA_PARA_LAMINACAO` (clicheria recebe prova para laminar — US-007 v4.0)
- `COM_MOTORISTA_IDA_LAMINACAO` (clicheria precisa "ver" para escanear motorista chegando)
- `LAMINACAO_CONCLUIDA` (clicheria está com a prova preparada — visibilidade contínua até motorista/vendedor pegar)
- `COM_MOTORISTA_ENTREGA_FINAL` (clicheria escaneia para confirmar recebimento — última transição de Matriz/Lam.Matriz)

**Cenários quebrados:**
- Lam. Matriz transição 1→2: 3Studio passa para `ENCAMINHADA_PARA_LAMINACAO`. Clicheria deveria poder escanear (e na verdade na Matriz §5.3 quem confirma a próxima transição é Motorista, não Clicheria — para esta entrada Clicheria só ver pela listagem). ✗
- Lam. Matriz transição 3: clicheria escaneia prova em `COM_MOTORISTA_IDA_LAMINACAO` → LAMINACAO_CONCLUIDA. ✗ — bloqueador funcional direto.
- Lam. Filial transição 3: idem. ✗ — bloqueador funcional direto.
- Matriz transição 5: clicheria escaneia prova em `COM_MOTORISTA_ENTREGA_FINAL` → RECEBIDA. ✗ — última transição da rota, **a mais crítica**.
- Lam. Matriz transição 10: idem. ✗ — última transição.

**Resultado em produção:** clicheria **NÃO consegue concluir nenhuma rota v4.0** ao tentar a última transição.

**Recomendação:**
```python
_CLICHERIA_STATUSES: tuple[StatusProvaEnum, ...] = (
    # Legacy v3.0
    StatusProvaEnum.ENVIADA_PARA_CLICHERIA,
    StatusProvaEnum.ENCAMINHADA_A_CLICHERIA,
    StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
    # v4.0 — laminação (US-007)
    StatusProvaEnum.ENCAMINHADA_PARA_LAMINACAO,
    StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO,
    StatusProvaEnum.LAMINACAO_CONCLUIDA,
    # v4.0 — entrega final (transição final Matriz/Lam.Matriz)
    StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL,
)
```

**Atenção:** isto inclui `COM_MOTORISTA_ENTREGA_FINAL` que **não está** na RLS migração 014 atual — recomendação adicional: atualizar a RLS para incluir esse estado também (paridade primária↔secundária).

#### AUD-W3C11-006 (HIGH) — Bug funcional em scoping não capturado por testes existentes

**Arquivo:** `backend/tests/test_provas_api.py` (e `_v4.py`)

**Estado atual:** Testes em `test_provas_api.py:1305-1331` validam scoping motorista/clicheria apenas para estados v3.0:
```python
assert "'COM_MOTORISTA'" in sql
assert "'ENVIADA_PARA_CLICHERIA'" in sql
assert "'ENCAMINHADA_A_CLICHERIA'" in sql
assert "'RECEBIDA_PELA_CLICHERIA'" in sql
```

Não há teste cobrindo:
- Motorista listando provas v4.0
- Clicheria listando provas v4.0
- Motorista escaneando prova em `COM_MOTORISTA_IDA_LAMINACAO`
- Clicheria escaneando prova em `LAMINACAO_CONCLUIDA`, `ENCAMINHADA_PARA_LAMINACAO` ou `COM_MOTORISTA_ENTREGA_FINAL`
- Motorista confirmando transição motorista → próximo estado (linha completa do fluxo)

**Recomendação:** sessão de correção deve incluir testes E2E para os cenários acima — sem isso, regressão futura passaria igualmente despercebida.

### Achados de Regressões em Waves Anteriores

#### AUD-W3C11-021 (INFO) — Camadas anteriores intocadas (positivo)

`git diff development...wave3-v4/componente-11` confirma que os arquivos a seguir **não foram modificados**:

| Arquivo / módulo | Status |
|---|---|
| `backend/app/services/state_machine.py` (v3.0) | ✅ vazio |
| `backend/app/services/qrcode_service.py` | ✅ vazio |
| `backend/app/services/codigo_publico_service.py` | ✅ vazio |
| `backend/app/services/etiqueta_service.py` | ✅ vazio |
| `frontend/src/lib/services/identificacao-prova.ts` (C10) | ✅ vazio |
| `frontend/src/lib/codigo-publico.ts` (C19) | ✅ vazio |
| `frontend/src/hooks/useCodigoPrvInput.ts` (C19) | ✅ vazio |
| `frontend/src/app/(dashboard)/escanear/page.tsx` (C10/C19) | ✅ vazio |
| `frontend/src/app/(dashboard)/nova-prova/page.tsx` (C06) | ✅ vazio |
| `frontend/src/app/(dashboard)/provas/[id]/page.tsx` (C08) | ✅ vazio |
| `frontend/src/app/(dashboard)/provas/[id]/Timeline.tsx` (C08, reserva C12) | ✅ vazio |

### Achados de Performance

#### AUD-W3C11-016 (MÉDIO) — Padrão inconsistente entre policies RLS (subquery vs EXISTS)

**Arquivo:** `backend/migrations/rls/014_expand_visibility_v4_states.sql`

`pol_movimentacoes_select` usa `prova_id IN (SELECT pd.id FROM provas_digitais pd WHERE ...)` duas vezes (uma para motorista, outra para clicheria). `pol_etiquetas_select` usa `EXISTS (SELECT 1 FROM provas_digitais pd WHERE pd.id = etiquetas.prova_id AND ...)`.

Em PostgreSQL, ambos são geralmente equivalentes após otimização, mas EXISTS termina ao primeiro match — preferível em escala. Inconsistência também dificulta leitura/manutenção.

**Recomendação:** uniformizar para EXISTS em todas as 3 policies — refactor cosmético, baixo risco. Pode ser feito junto com a correção do scope_filter_for.

#### AUD-W3C11-017 (BAIXO) — Sem benchmark dedicado de transição

`analysis.md §A.5` diz "Lookup O(1) na tabela em memória; benchmark indireto via 961 testes em 4s". Não há benchmark real medindo tempo `/transicoes` end-to-end. Aceitável dado o lookup O(1) e o lock fino, mas se RNF-002 (≤ 2s) virar requisito de auditoria formal, falta evidência numérica.

### Achados de Manutenibilidade

#### AUD-W3C11-010 (MÉDIO) — Docstring arithmétic error em `pode_cancelar`

**Arquivo:** `backend/app/state_machine/v4/machine.py:71-72`
```python
"""Os outros 15 valores do enum (10 v3.0 + 5 v4.0 ativos) sao todos
cancelaveis."""
```

Deveria ser "8 v3.0 ativos + 7 v4.0 ativos = 15". A conta `10 + 5 = 15` está correta numericamente mas a decomposição (`10 v3.0 + 5 v4.0`) está errada — todos os 7 v4.0 são ativos, e dos 10 v3.0 dois são terminais (RECEBIDA + CANCELADA), restando 8 v3.0 ativos.

#### AUD-W3C11-011 (BAIXO) — STATUS_LABELS_SHORT comment desatualizado

**Arquivo:** `frontend/src/lib/types/prova.ts:215`
```
/** Labels pt-BR curtos — usados na listagem (Componente 07), onde a coluna
 * Status tem espaco limitado e o Figma pede versao abreviada. Preserva a
 * distintividade de todos os 10 estados. */
```

Deveria ser "17 estados". Atualização cosmética.

#### AUD-W3C11-012 (BAIXO) — CHANGELOG: "9 estados v3.0 para 14 estados v4.0"

**Arquivo:** `CHANGELOG.md` linha 9-10 (versão atualizada na branch C11)

A frase está semanticamente correta (9 ativos v3.0 + cancelada = 10 enum values v3.0; 14 estados únicos canônicos na v4.0). Mas a implementação real é 10 v3.0 + 7 v4.0 = 17 enum values. A discrepância vem da decisão M-2b(a) de preservar valores legacy distintos. Aceitável, mas pode confundir leitor — sugere-se reformular para "10 valores v3.0 → 17 valores no enum (com 14 estados canônicos via unificação semântica)".

#### AUD-W3C11-013 (BAIXO) — Discrepância na contagem de testes

CHANGELOG declara `(56+18+50+15) = 139` testes novos na suíte v4.0. `grep -c "^def test_"` retornou 43+30+8+6 = 87 funções; com `@pytest.mark.parametrize`, a contagem real (test instances) sobe — provavelmente bate com 139 quando se conta cada cenário parametrizado como separado. Não bloqueante; apenas inconsistência de medição entre relatório e arquivo.

### Achados de Cobertura de Testes

#### AUD-W3C11-022 (INFO) — Cobertura 100% no módulo v4

`analysis.md §A.5` declara 100% (187/187 stmts) em `app/state_machine/v4/*`. Acima do alvo 95% (DAT §3 + Backlog C11).

Tests sumarizados:
- `test_rules_v4.py` — 43 testes, sanidade + matriz par a par + exhaustividade
- `test_machine_v4.py` — 30 testes, todos os caminhos (cancelamento, reinicio, reprovacao, normais, errors)
- `test_facade.py` — 8 testes, roteamento e compat
- `test_contextos_v4.py` — 6 testes, 3 contextos + legacy + None
- `test_status_prova_enum_drift.py` — 3 pure + 1 integration

#### AUD-W3C11-007 (MÉDIO) — Drift Python↔Postgres só roda com env var

**Arquivo:** `backend/tests/test_status_prova_enum_drift.py:74-114`

O teste `test_status_prova_enum_drift_python_postgres` tem `@pytest.mark.skipif(_INTEGRATION_DB_URL is None, ...)`. Em CI normal (sem `INTEGRATION_DATABASE_URL`), o teste é skipped — **drift entre Python e Postgres não é detectado automaticamente**. Apenas Python ↔ TS (regex) e sanity check rodam.

Mitigado por validação MCP manual durante a entrega (analysis.md §A.5). Mas se algum PR futuro adicionar valor no Python sem migration correspondente, não há detecção automatica em CI.

**Recomendação:** considerar separar como "smoke test" rodado pelo CI/CD com banco temporário ou usar pytest fixture `pg_temporary` quando disponível.

#### AUD-W3C11-004 (HIGH) — Falta cobertura E2E motorista/clicheria em v4.0

Já listado em "Bugs Funcionais" como AUD-006. Repetido aqui por foco em testes.

### Achados de Documentação

#### AUD-W3C11-014 (BAIXO) — Decisão M-7 sem ADR formal

`analysis.md §A.1` lista M-7 com decisão B (mensagens concisas, voz ativa), implementada em `machine.py:186-207`. Mas DECISIONS.md não tem ADR dedicado para M-7 — apenas ADR-146 (M-1), ADR-147 (M-2), ADR-148 (M-2b), ADR-149 (M-3), ADR-150 (M-4), ADR-151 (M-5), ADR-152 (M-6), ADR-153 (M-8).

Não viola escalação humana (a decisão foi tomada), mas documentação inconsistente com as outras 7 decisões. Sugere-se criar ADR-154 (post-hoc) para M-7.

#### AUD-W3C11-003 (HIGH) — `shared/access-matrix.json` scope_kinds desatualizado

**Arquivo:** `shared/access-matrix.json:22-23`

```json
"status_motorista_em_transito": "status IN (estados COM_MOTORISTA*) (motorista ve apenas em transito)",
"status_clicheria": "status IN (ENVIADA_PARA_CLICHERIA, ENCAMINHADA_A_CLICHERIA, RECEBIDA_PELA_CLICHERIA)"
```

- Para motorista, a string usa "COM_MOTORISTA*" (asterisco) sugerindo todos os v4.0 — semântica correta da v4.0, mas a implementação Python só cobre `COM_MOTORISTA`. **Documentação ↔ implementação divergentes.**
- Para clicheria, a string lista 3 estados v3.0 literais. Sem menção aos v4.0. **Documentação ↔ Matriz canônica §6 + Backlog C11 §Notas Técnicas divergentes.**

Esta documentação é a SSoT da Wave 1 v4.0. PR que modifica scope_kinds aqui deve sincronizar:
- Python `_MOTORISTA_STATUSES` / `_CLICHERIA_STATUSES`
- RLS migration (já feita por C11)
- Frontend access-matrix.ts (TS espelho)

**Recomendação:** sessão de correção atualizar JSON + scopes.py + adicionar testes — tudo no mesmo PR.

### Achados de Aderência ao Especificado

#### AUD-W3C11-005 (HIGH) — Critério 15 do prompt não entregue

**Item:** "Botões inline de transição na página de detalhe da prova" (RF-008 v4.0 RF-011 v4.0 — fluxo de "Identificar prova → Selecionar Aprovar/Reprovar → Assinar → Confirmar").

**Documentação:** `analysis.md §A.4` reconhece a deferral:
> "A UX canônica de transição é via scanner (`/escanear`) com signature canvas. Botões inline na página de detalhe requereriam: Modal com signature canvas (~150 LOC novo) + Hook `useTransitionFromDetail` ... + Lista dinâmica de transições disponíveis baseada em (rota, status, perfil).
>
> Registrado como follow-up para decisão do Mario no merge:
> (a) Aceitar a limitação no merge; criar como tarefa separada se necessário.
> (b) Pedir nova sessão para entregar antes do PR para `main`."

**Estado atual:** decisão pendente; PR não pode ser totalmente fechado sem ela.

**Recomendação:** Mario decidir explicitamente entre (a) e (b) antes do merge. Sem decisão explícita, scanner em `/escanear` é o único caminho — funciona, mas pode ser confuso para admin que esperava clicar direto no detalhe.

### Achados de Preparação para o C12

#### AUD-W3C11-015 (INFO) — `contrato-c12.md` adequado para o C12

408 LOC, 11 seções organizadas:
1. Mapeamento de estados → metadata visual
2. Helpers de detecção de contexto do Motorista
3. Sequência canônica de etapas por rota (`estados_da_rota` + `ROTA_ETAPAS` sugerido para C12 criar em TS)
4. Estado atual e progresso da prova
5. Endpoints e dados a consumir
6. Animações e a11y (incluindo `prefers-reduced-motion`)
7. Patterns a NÃO duplicar
8. Decisões fixadas no Gate 1 que afetam C12 (M-1, M-2b, M-5, M-7)
9. Testes de regressão recomendados
10. Arquivos que C12 PODE tocar sem fricção
11. Arquivos que C12 NÃO DEVE tocar

Exemplos funcionais incluídos. C12 pode iniciar consumindo este contrato.

### Achados de Concorrência e Race Conditions

#### AUD-W3C11-019 (INFO) — Concorrência tratada via FOR UPDATE + 409

Cenário 1 (dois usuários simultâneos transitionando mesma prova): `_carregar_prova_com_scoping(..., lock=True)` aplica `FOR UPDATE` (`provas.py:1009-1080`). A segunda transação aguarda; quando libera, o status mudou → `TransicaoInvalidaError` → 409 Conflict. UX bem definida (ADR-084 Decisão 3).

Cenário 2 (cancelamento + transição simultâneos): mesmo mecanismo.

Cenário 3 (reinício + transição): mesmo mecanismo.

**Veredito:** Concorrência adequadamente tratada. Sem race conditions reproduzíveis.

---

## Fase 3 — Verificação Comportamental em Staging (Read-only)

### Estado real das tabelas

#### Enum `status_prova_enum`

MCP `SELECT enumlabel, enumsortorder FROM pg_enum WHERE typname='status_prova_enum'`:

```
 1. CRIADA
 2. RETIRADA_PELO_VENDEDOR
 3. APROVADA_PELO_VENDEDOR
 4. DE_VOLTA_3STUDIO
 5. COM_MOTORISTA                       (legacy v3.0 — 1 unico contexto)
 6. ENVIADA_PARA_CLICHERIA              (legacy-only)
 7. ENCAMINHADA_A_CLICHERIA             (legacy-only)
 8. RECEBIDA_PELA_CLICHERIA             (terminal)
 9. REPROVADA_PELO_VENDEDOR
10. CANCELADA                            (terminal transversal)
11. COM_MOTORISTA_ENTREGA_FINAL         ← v4.0 (migration 013)
12. COM_MOTORISTA_IDA_LAMINACAO         ← v4.0
13. COM_MOTORISTA_VOLTA_LAMINACAO       ← v4.0
14. DE_VOLTA_3STUDIO_POS_LAMINACAO      ← v4.0
15. ENCAMINHADA_PARA_LAMINACAO          ← v4.0
16. ENCAMINHADA_PARA_O_VENDEDOR         ← v4.0
17. LAMINACAO_CONCLUIDA                 ← v4.0
```

**Veredito:** 17 valores, ordem alfabética dos novos coerente com `_NOVOS_VALORES_V4` em `013_expand_status_prova_enum_v4.py:82-90`.

#### `alembic_version`

MCP retorna `'013'`.

#### Triggers ativos

MCP retorna 4 triggers:
- `trg_provas_rota_imutavel` (preservado)
- `trg_provas_updated_at` (preservado)
- `trg_movimentacoes_imutavel` (preservado)
- `trg_audit_logs_imutavel` (preservado)

Nenhum trigger semântico de validação de transição foi criado (Decisão M-4, ADR-150).

### Distribuição de Dados (coexistência)

Já documentada em Fase 1 (§Coexistência). Resumo: 17 provas, 0 cruzamento legacy↔v4.0.

### Cenários de Borda

| Cenário | Verificado |
|---|---|
| Provas com `rota IS NULL` em estado v4.0 | ✅ Nenhuma (MCP query) |
| Provas com `rota IN {MATRIZ, ...}` em estado exclusivo v3.0 | ✅ Nenhuma (a única MATRIZ está em CRIADA — compartilhado) |
| Provas legacy sem `codigo_publico` (Wave 7 backfill futuro) | N/A — todas têm codigo_publico desde Wave 2 v4.0 |
| Movimentação sem `responsavel_id`/`created_at` | N/A — colunas NOT NULL |

### Acesso simulado por perfil

Não foi possível impersonar perfis via MCP read-only — o módulo Supabase MCP usa service_role e não suporta `SET ROLE authenticated` + `SET LOCAL request.jwt.claims = ...`. **A validação RBAC é feita por inspeção do código** (`scope_filter_for` + RLS policies SQL).

Tabelinha esperada (não-validada empiricamente — base teórica derivada de `scope_filter_for + RLS policies`):

| Perfil | Lista provas v3.0 | Lista provas v4.0 | Esperado conforme Matriz |
|---|---|---|---|
| **studio_admin** | Todas | Todas | ✅ FULL |
| **vendedor** | Apenas as próprias | Apenas as próprias | ✅ PARCIAL self_vendedor |
| **motorista** | Apenas COM_MOTORISTA legacy | **❌ Nenhuma** (deveriam ser 3 v4.0) | ❌ AUD-001 |
| **clicheria** | Apenas 3 v3.0 (ENVIADA/ENCAMINHADA/RECEBIDA) | **❌ Nenhuma** (deveriam ser 4 v4.0) | ❌ AUD-002 |

### Performance Real

Não medida nesta sessão (modo read-only sem execução de benchmark). Estimativa indireta:
- `transicoes_validas_v4` lookup: O(1) via `dict.get`
- `executar_transicao_v4` async + FOR UPDATE: 1 lock + 1 INSERT + 1 audit_log = 3 round trips ao banco
- Total esperado: < 500ms na maioria dos casos

### Audit Log

Verificado em `machine.py:359-386`:
- `acao='transitar_status'` ou `'reiniciar_ciclo'`
- `detalhes_json` contém `de`, `para`, `ciclo`, `rota_antes`, `rota_depois`, `maquina='v4'`, `contexto_motorista` (quando aplicável), `motivo_reprovacao` ou `motivo_cancelamento` (quando aplicável)
- Tabela `audit_logs` é append-only via `trg_audit_logs_imutavel`

---

## Achados Consolidados Ordenados por Severidade

### CRÍTICOS (2)

| ID | Título | Arquivo | Recomendação |
|---|---|---|---|
| **AUD-W3C11-001** | `_MOTORISTA_STATUSES` não inclui 3 contextos v4.0 — motorista não vê/escaneia provas v4.0 | `backend/app/access/scopes.py:50-52` | Adicionar `COM_MOTORISTA_IDA_LAMINACAO`, `COM_MOTORISTA_VOLTA_LAMINACAO`, `COM_MOTORISTA_ENTREGA_FINAL` ao tuple + 4 testes API E2E motorista |
| **AUD-W3C11-002** | `_CLICHERIA_STATUSES` não inclui 4 estados v4.0 — clicheria não conclui rotas v4.0 | `backend/app/access/scopes.py:55-59` | Adicionar `ENCAMINHADA_PARA_LAMINACAO`, `COM_MOTORISTA_IDA_LAMINACAO`, `LAMINACAO_CONCLUIDA`, `COM_MOTORISTA_ENTREGA_FINAL` ao tuple + 4 testes API E2E clicheria + adicionar `COM_MOTORISTA_ENTREGA_FINAL` à RLS 014 para paridade |

### ALTOS (3)

| ID | Título | Arquivo | Recomendação |
|---|---|---|---|
| **AUD-W3C11-003** | `shared/access-matrix.json` scope_kinds documenta v3.0 only — SSoT inconsistente | `shared/access-matrix.json:19-24` | Atualizar strings `status_motorista_em_transito` e `status_clicheria` para enumerar todos os estados v4.0 |
| **AUD-W3C11-004** | Falta cobertura E2E motorista/clicheria em estados v4.0 — bugs como AUD-001/002 não capturados | `backend/tests/test_provas_api.py` (e `_v4.py`) | Adicionar `test_scope_motorista_v4_estados`, `test_scope_clicheria_v4_estados`, `test_scan_motorista_v4_*`, `test_scan_clicheria_v4_*` (≥ 6 testes novos) |
| **AUD-W3C11-005** | Critério 15 (botões inline transição) não entregue — decisão pendente do Mario | `frontend/src/app/(dashboard)/provas/[id]/page.tsx` | Mario decidir (a) aceitar limitação + criar tarefa separada OU (b) pedir nova sessão antes do PR para `main` |

### MÉDIOS (5)

| ID | Título | Arquivo | Recomendação |
|---|---|---|---|
| **AUD-W3C11-007** | Teste de drift Python↔Postgres só roda com env var — skipped em CI normal | `backend/tests/test_status_prova_enum_drift.py:78-83` | Considerar usar fixture `pg_temporary` ou separar como job CI/CD dedicado |
| **AUD-W3C11-008** | RLS 014 `pol_movimentacoes_select` usa subquery 2x; `pol_etiquetas_select` usa EXISTS — inconsistência de padrão | `backend/migrations/rls/014_expand_visibility_v4_states.sql:93-129` | Uniformizar para EXISTS em todas as 3 policies |
| **AUD-W3C11-009** | Decisão M-7 implementada sem ADR formal | `DECISIONS.md` | Criar ADR-154 post-hoc para M-7 documentando mensagens em voz ativa concisa |
| **AUD-W3C11-010** | Docstring de `pode_cancelar` com arithmetic error (10+5 vs 8+7) | `backend/app/state_machine/v4/machine.py:71-72` | Corrigir "10 v3.0 + 5 v4.0 ativos" → "8 v3.0 ativos + 7 v4.0 ativos" |
| **AUD-W3C11-016** | Inconsistência subquery vs EXISTS entre RLS policies | `backend/migrations/rls/014_*.sql` | Refactor cosmético na próxima oportunidade (junto com correções AUD-001/002 idealmente) |

### BAIXOS (6)

| ID | Título | Arquivo | Recomendação |
|---|---|---|---|
| **AUD-W3C11-011** | STATUS_LABELS_SHORT comment diz "10 estados" — outdated | `frontend/src/lib/types/prova.ts:215` | Atualizar para "17 estados" |
| **AUD-W3C11-012** | CHANGELOG: "9 estados v3.0 para 14 estados v4.0" — narrativamente confuso (17 reais no enum) | `CHANGELOG.md` | Reformular para "10 valores v3.0 → 17 valores no enum (14 estados canônicos)" |
| **AUD-W3C11-013** | Test count discrepância 87 funções vs 139 testes declarados | `analysis.md §A.5`, `CHANGELOG.md` | Esclarecer que 139 inclui expansão de parametrize |
| **AUD-W3C11-014** | M-7 sem ADR formal | `DECISIONS.md` | Já listado como MÉDIO em AUD-009 — duplicação intencional |
| **AUD-W3C11-017** | Sem benchmark dedicado de transição | `analysis.md §A.5` | Documentar tempo medido em sessão pós-merge |
| **AUD-W3C11-024** | `motivo_cancelamento_norm` em `executar_transicao_v4` é setado em `prova.motivo_cancelamento` (linha 354) mesmo se a coluna não exigir mudança em outros campos — comportamento idêntico ao v3.0, mas vale documentar | `backend/app/state_machine/v4/machine.py:354` | Aceitável, sem ação |

### INFO (4)

| ID | Título | Recomendação |
|---|---|---|
| **AUD-W3C11-015** | `contrato-c12.md` adequado | Sem ação |
| **AUD-W3C11-018** | Sem trigger semântico — Decisão M-4 (ADR-150) | Sem ação |
| **AUD-W3C11-019** | Concorrência adequadamente tratada via FOR UPDATE + 409 | Sem ação |
| **AUD-W3C11-020** | Anti-enumeração preservada nas mensagens | Sem ação |
| **AUD-W3C11-021** | Camadas anteriores intocadas | Sem ação |
| **AUD-W3C11-022** | Cobertura 100% no módulo v4 (DAT § 95% alvo) | Sem ação |

---

## Recomendações de Próximos Passos

### Ações requeridas antes do merge para `development`

1. **Corrigir AUD-W3C11-001 + AUD-W3C11-002 (CRÍTICOS):** atualizar `backend/app/access/scopes.py` para incluir os estados v4.0 nos tuples `_MOTORISTA_STATUSES` e `_CLICHERIA_STATUSES`. Adicionar `COM_MOTORISTA_ENTREGA_FINAL` à RLS 014 (paridade primária↔secundária — migration 015).
2. **Atualizar AUD-W3C11-003 (HIGH):** atualizar `shared/access-matrix.json` strings de `scope_kinds`.
3. **Adicionar testes AUD-W3C11-004 (HIGH):** ≥ 6 testes novos em `test_provas_api.py` ou novo arquivo `test_provas_api_v4_rbac.py`:
   - `test_scope_motorista_v4_3_contextos`
   - `test_scope_clicheria_v4_4_estados`
   - `test_scan_motorista_pode_escanear_em_com_motorista_ida_laminacao`
   - `test_scan_clicheria_pode_escanear_em_com_motorista_entrega_final`
   - `test_listar_provas_motorista_v4_traz_todas_3_contextos`
   - `test_listar_provas_clicheria_v4_traz_estados_laminacao`
4. **Resolver AUD-W3C11-005 (HIGH):** decisão explícita do Mario entre (a) aceitar deferral do critério 15 com documentação ou (b) nova sessão.
5. **Atualizar M-7 ADR-154 (LOW AUD-W3C11-009):** post-hoc, documentar a decisão sobre mensagens de erro.

### Ações recomendadas (não bloqueantes)

6. Uniformizar RLS para EXISTS em todas as 3 policies (AUD-W3C11-008/016).
7. Corrigir arithmetic na docstring de `pode_cancelar` (AUD-W3C11-010).
8. Atualizar comments outdated (AUD-W3C11-011, 012, 013).
9. Documentar tempo real de transição em sessão pós-merge (AUD-W3C11-017).

### Pré-requisitos que o C12 precisa verificar

- **C12 pode iniciar em paralelo às correções.** Os bugs CRÍTICOS afetam motorista/clicheria operando provas v4.0; o C12 é puramente visual (timeline) e consome `useScanProva`/`useProvaDetail` que funcionam corretamente para vendedor/admin.
- Antes do PR final do C12 para `development`, validar que AUD-W3C11-001/002 foram corrigidos para que a Timeline visualize provas v4.0 acessadas por motorista/clicheria também.

### Itens de backlog técnico (após correções desta auditoria)

- Rate limit em `/scan` + `/transicoes` + `/cancelar` + `/reiniciar-ciclo` (ADR-145 + ADR-153) — sessão dedicada antes de PR para `main`.
- Wave 7 (Componente 21): backfill `rota NULL → valor`, eventualmente `rota` NOT NULL, eventualmente remoção da máquina v3.0.
- Validação real de impersonation RBAC via MCP (quando disponível) — testar todos os 4 perfis × 4 rotas × N estados.

---

## Anexos

### A. Output MCP Supabase (read-only)

- **`alembic_version`** = `'013'`
- **Enum `status_prova_enum`** = 17 valores listados em §Fase 3
- **Distribuição de provas** = 17 provas, sem cruzamento legacy↔v4.0
- **Advisors:** 1 INFO (alembic_version RLS) + 1 WARN (leaked password) — pré-existentes; 13 unused_index INFO — pré-existentes
- **Policies RLS** = 6 policies em provas/movimentacoes/etiquetas; cobertura v4.0 conforme migration 014

### B. Diffs amostrais examinados (não-modificação)

- `backend/app/services/state_machine.py`: vazio ✅
- `backend/app/services/qrcode_service.py`: vazio ✅
- `frontend/src/lib/services/identificacao-prova.ts`: vazio ✅
- `frontend/src/lib/codigo-publico.ts`: vazio ✅
- `frontend/src/app/(dashboard)/escanear/page.tsx`: vazio ✅
- `frontend/src/app/(dashboard)/nova-prova/page.tsx`: vazio ✅
- `frontend/src/app/(dashboard)/provas/[id]/page.tsx`: vazio ✅
- `frontend/src/app/(dashboard)/provas/[id]/Timeline.tsx`: vazio ✅

### C. Cenários reproduzidos mentalmente

1. **Motorista escaneando prova MATRIZ em COM_MOTORISTA_ENTREGA_FINAL:**
   - `POST /scan` com payload `3SD|PRV-2026-05-XYZ|abcd1234567890ef`
   - Backend: `_carregar_prova_por_codigo_publico_com_scoping(db, "PRV-2026-05-XYZ", motorista)` → aplica `_scoping_filter(motorista)` → retorna `ProvaDigital.status.in_(('COM_MOTORISTA',))`
   - Query: `SELECT ... WHERE codigo_publico = 'PRV-2026-05-XYZ' AND status IN ('COM_MOTORISTA')`
   - Resultado: 0 rows (a prova está em `COM_MOTORISTA_ENTREGA_FINAL`, não em `COM_MOTORISTA`)
   - Resposta: 404 "Prova não encontrada"
   - **Bug confirmado.**
2. **Clicheria escaneando prova LAM_MATRIZ em LAMINACAO_CONCLUIDA:**
   - Mesmo pipeline com `_CLICHERIA_STATUSES = (ENVIADA, ENCAMINHADA_A, RECEBIDA)`
   - Resultado: 0 rows → 404
   - **Bug confirmado.**
3. **Vendedor escaneando sua prova MATRIZ em CRIADA:**
   - `_scoping_filter(vendedor)` → `ProvaDigital.vendedor_id == vendedor.id`
   - Query encontra a prova (vendedor.id = prova.vendedor_id) → 200 OK + `transicoes_permitidas = ['RETIRADA_PELO_VENDEDOR']`
   - **Funciona corretamente.**
4. **Admin escaneando qualquer prova:**
   - `_scoping_filter(admin)` → `None` (sem restrição)
   - Funciona corretamente.

### D. Tabela de comparação par a par da Matriz canônica vs implementação

Reproduzida em §Conformidade da Matriz de Transições. **24/24 transições conformes.**

### E. Suite de testes do C11

- `backend/tests/state_machine/test_rules_v4.py` (43 funções; ~70+ asserts com parametrize)
- `backend/tests/state_machine/test_machine_v4.py` (30 funções; ~50+ com parametrize)
- `backend/tests/state_machine/test_facade.py` (8 funções)
- `backend/tests/state_machine/test_contextos_v4.py` (6 funções)
- `backend/tests/test_status_prova_enum_drift.py` (4 funções, 1 skipif integração)
- `backend/tests/test_state_machine.py` — modificado: 1 teste v3.0 reescrito para escopar invariante a 10 valores legacy

**Cobertura declarada:** 100% em `app/state_machine/v4/*` (`analysis.md §A.5`).

### F. Definição completa dos triggers no banco

```sql
trg_provas_rota_imutavel    BEFORE UPDATE ON provas_digitais
                            WHEN (old.rota IS DISTINCT FROM new.rota)
                            EXECUTE FUNCTION fn_bloquear_alteracao_rota()
trg_provas_updated_at       BEFORE UPDATE ON provas_digitais
                            EXECUTE FUNCTION fn_atualizar_updated_at()
trg_movimentacoes_imutavel  BEFORE DELETE OR UPDATE ON movimentacoes
                            EXECUTE FUNCTION fn_bloquear_alteracao()
trg_audit_logs_imutavel     BEFORE DELETE OR UPDATE ON audit_logs
                            EXECUTE FUNCTION fn_bloquear_alteracao()
```

Nenhum trigger semântico de transição (consistente com Decisão M-4 / ADR-150).

---

**Fim do relatório. Aguardando decisão humana sobre próximos passos.**

---

## Apêndice: Status pós-correção (2026-05-13)

Sessão de correção em branch `wave3-v4-c11/fixes/execution` (sai de
`wave3-v4/componente-11`). Plano em `docs/wave3-v4-c11/fix-plan.md`.
O corpo original do relatório acima **não foi editado** — esta seção
acrescenta status pós-correção por ID.

| ID | Severidade | Status pós-correção | Commit SHA-friendly | Notas |
|---|---|---|---|---|
| **AUD-W3C11-001** | CRÍTICO | **RESOLVIDO** | `fix(...AUD-001)` | `_MOTORISTA_STATUSES` estendido com 3 contextos v4.0 (`backend/app/access/scopes.py`). Validado por testes novos (AUD-004). |
| **AUD-W3C11-002** | CRÍTICO | **RESOLVIDO** | `fix(...AUD-002)` | `_CLICHERIA_STATUSES` estendido com 4 estados v4.0 + RLS 015 aplicada via MCP (paridade primária↔secundária com `COM_MOTORISTA_ENTREGA_FINAL` em todas as 3 policies). Combinada com uniformização EXISTS (AUD-008/016). |
| **AUD-W3C11-003** | HIGH | **RESOLVIDO** | `docs(...AUD-003)` | `shared/access-matrix.json scope_kinds` enumera todos os estados (4 motorista + 7 clicheria) literalmente. |
| **AUD-W3C11-004** | HIGH | **RESOLVIDO** | `test(...AUD-004)` | 6 testes novos (4 unit em `test_scope_filter_for.py` + 2 API em `test_provas_api.py`) asserindo cada literal v4.0 explicitamente. |
| **AUD-W3C11-005** | HIGH | **RESOLVIDO via documentação (Opção (a))** | `docs(...AUD-005)` | Decisão do Mario em 2026-05-13: aceita deferral do critério 15. Botões inline ficam como follow-up técnico opcional pós-Wave 3. ADR-155. |
| **AUD-W3C11-006** | HIGH | **RESOLVIDO (duplicação de AUD-004)** | `test(...AUD-004)` | Coberto pelo mesmo commit. |
| **AUD-W3C11-007** | MED | **DEFERRED — encaminhado para sessão de CI/CD pós-Wave 3** | `docs(...AUD-007)` | ADR-156 documenta decisão técnica (Opção C — aceitar gap conhecido, mitigado por Python↔TS regex em CI + validação MCP manual). |
| **AUD-W3C11-008** | MED | **RESOLVIDO (combinado com AUD-002)** | `fix(...AUD-002)` | RLS 015 reescreve `pol_movimentacoes_select` em EXISTS; `pol_etiquetas_select` já era EXISTS; `pol_provas_select` é filtro direto (não cabe EXISTS). |
| **AUD-W3C11-009** | MED | **RESOLVIDO** | `docs(...AUD-005,007,009,014,017)` | ADR-154 documenta decisão M-7 (mensagens em pt-BR voz ativa concisa) post-hoc. |
| **AUD-W3C11-010** | MED | **RESOLVIDO** | `docs(...AUD-010)` | Docstring de `pode_cancelar` corrigida — decomposição "8 v3.0 ativos + 7 v4.0 ativos = 15". |
| **AUD-W3C11-011** | LOW | **RESOLVIDO** | `docs(...AUD-011)` | JSDoc do `STATUS_LABELS_SHORT` reflete 17 estados. |
| **AUD-W3C11-012** | LOW | **RESOLVIDO via apêndice** | `docs(...AUD-012,013)` | Narrativa "9 v3.0 → 14 v4.0" da seção original do CHANGELOG preservada por valor histórico; esclarecida no apêndice de Correções Pós-Auditoria. |
| **AUD-W3C11-013** | LOW | **RESOLVIDO via apêndice** | `docs(...AUD-012,013)` | Discrepância 87 vs 139 esclarecida — 87 funções base + 52 expansões `@pytest.mark.parametrize`. |
| **AUD-W3C11-014** | LOW | **RESOLVIDO (duplicação de AUD-009)** | `docs(...AUD-005,007,009,014,017)` | Coberto pelo mesmo ADR-154. |
| **AUD-W3C11-015** | INFO | **ACEITO sem ação** | — | `contrato-c12.md` adequado conforme auditor. Sem mudança. |
| **AUD-W3C11-016** | MED | **RESOLVIDO (combinado com AUD-002/008)** | `fix(...AUD-002)` | Uniformização EXISTS na migration RLS 015. |
| **AUD-W3C11-017** | LOW | **DEFERRED — encaminhado para sessão de rate limit pós-merge `main`** | `docs(...AUD-005,007,009,014,017)` | ADR-157 documenta deferral junto com ADR-145/153. |
| **AUD-W3C11-018** | INFO | **ACEITO sem ação** | — | Sem trigger semântico — Decisão M-4 (ADR-150). |
| **AUD-W3C11-019** | INFO | **ACEITO sem ação** | — | Concorrência tratada via FOR UPDATE + 409 (ADR-084). |
| **AUD-W3C11-020** | INFO | **ACEITO sem ação** | — | Anti-enumeração preservada nas mensagens. |
| **AUD-W3C11-021** | INFO | **ACEITO sem ação** | — | Camadas anteriores intocadas (positivo). |
| **AUD-W3C11-022** | INFO | **ACEITO sem ação** | — | Cobertura 100% no módulo v4 (acima de 95% alvo). |
| **AUD-W3C11-024** | LOW | **ACEITO sem ação** | — | `motivo_cancelamento_norm` em `executar_transicao_v4` aceitável; comportamento idêntico ao v3.0. Auditor declarou "Aceitável, sem ação". |

**Sumário:**
- **RESOLVIDOS com código:** 11 IDs (AUD-001, 002, 003, 004, 006, 008, 010, 011, 016 + parciais de 005, 009, 012, 013, 014).
- **RESOLVIDOS via documentação:** 6 IDs (AUD-005, 009, 012, 013, 014 + ADR-154/155/156/157).
- **DEFERRED com encaminhamento:** 2 IDs (AUD-007 → CI/CD pós-Wave 3; AUD-017 → sessão de rate limit pós-merge `main`).
- **ACEITOS sem ação:** 7 IDs (AUD-015, 018, 019, 020, 021, 022, 024) — auditor declarou aceitável.
- **Total:** 22 entradas (19 únicos após dedup) — **0 não resolvidos**.

**Critério de aceitação:** Achados CRÍTICOS, ALTOS e MÉDIOS corrigíveis com código têm commit dedicado. INFOs e AUD-024 ficam registrados aqui sem código. AUD-005 obteve decisão humana explícita (Opção (a)) registrada em ADR-155. AUD-007 e AUD-017 estão encaminhados para sessões específicas com timing fixado (CI/CD pós-Wave 3 e rate-limit antes do PR para `main`).

**Detalhes da execução:** ver `docs/wave3-v4-c11/fix-validation.md` (smoke check + auto-crítica) e `docs/wave3-v4-c11/fix-plan.md` Seção "Resultado da Execução".
