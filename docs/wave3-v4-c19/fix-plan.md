# Plano de Correção Pós-Auditoria · Wave 3 v4.0 · Componente 19

**Sessão:** Correção dos achados do `audit-report.md` (pós-execução C19).
**Branch base:** `wave3-v4-c19/audit` (commit `999e5b0`), que contém o trabalho do C19 (6 commits acima de `development`) + o relatório de auditoria. A branch `development` ainda **NÃO** tem o C19 mergeado — divergência do prompt original anotada em §10.
**Branch desta etapa (Gate 1):** `wave3-v4-c19/fixes/plan` — apenas este `fix-plan.md` é commitado. Zero código de produção.
**Branch da próxima etapa (Gate 2):** `wave3-v4-c19/fixes/execution` (saindo de `wave3-v4-c19/audit`).
**PR final aponta para:** `development`.
**Data:** 2026-05-11.

---

## 0. Posicionamento Estratégico

O `audit-report.md` (commit `999e5b0`, 804 linhas) classificou a entrega do C19 como **APROVADO COM CORREÇÕES** com:

- **0 CRÍTICOS**
- **1 ALTO** — AUD-W3C19-001 (rate-limit backend ausente, já registrado pelo autor como ADR-145 / FOLLOW-UP OBRIGATÓRIO).
- **3 MÉDIOS** — AUD-W3C19-002 (`<strong>` no banner), AUD-W3C19-003 (teste de uniformização), AUD-W3C19-004 (`aria-invalid` no wrapper).
- **5 BAIXOS** — AUD-W3C19-005/031, AUD-W3C19-006, AUD-W3C19-007, AUD-W3C19-008, AUD-W3C19-028.
- **~20 INFOs distribuídos** (`013/014/015/016/017/018/019/020/021/022/023/024/025/026/027/029/030/032/033/034/035/036/037/038/039/040` + dois rotulados `009`).

O ALTO é **bloqueante para o PR em `main`** mas **não é corrigível nesta sessão** (rate-limit no `/scan` exige mexer no backend, vetado pelo escopo do prompt — Seção 1 "O que você NÃO FAZ" + Seção 5.3 "Achados de modificação não-autorizada do C10"). Vai DEFERRED com encaminhamento explícito para "sessão dedicada pós-auditoria do C10/C20+".

Os 3 MÉDIOS são corrigíveis. Os 5 BAIXOS dividem-se em "aceitar com documentação" (3) e "corrigir trivialmente" (1, com 1 coberto pelo MÉDIO AUD-003). Os INFOs são registrados com status final mas não exigem mudança de código (recomendação do próprio auditor).

---

## 1. Confirmação de Leitura de Contexto (Pré-Gate 1)

### 1.1 Artefato central

| Documento | Status | Linhas | Observações relevantes |
|---|---|---|---|
| [`docs/wave3-v4-c19/audit-report.md`](audit-report.md) | ✅ lido | 804 | 1 ALTO + 3 MÉDIOS + 5 BAIXOS acionáveis + ~20 INFOs. Veredito APROVADO COM CORREÇÕES. |
| [`docs/wave3-v4-c10/contrato-c19.md`](../wave3-v4-c10/contrato-c19.md) | ✅ lido | 393 | Seção 7 "Status: Entrega Completa" + 6 casos de uso + D1-D10. Será atualizado se a correção do AUD-003 mudar a forma de consumo. |

### 1.2 Arquivos de contexto vivo do repositório (estado pós-C19 em branch `wave3-v4-c19/audit`)

| Arquivo | Status |
|---|---|
| [`CLAUDE.md`](../../CLAUDE.md) | ✅ lido — seção "Identificação de provas" já marcada ENTREGUE; subseção "Notas do Componente 19" presente. |
| [`DECISIONS.md`](../../DECISIONS.md) | ✅ lido — ADRs 141-145 do C19. |
| [`CHANGELOG.md`](../../CHANGELOG.md) | ✅ lido — seção C19 2026-05-11 completa. |
| Schema do banco | ✅ validado via MCP — ver §3 abaixo. |
| [`docs/wave3-v4-c19/analysis.md`](analysis.md) | ✅ lido (992 LOC) — Gate 1 + Apêndice A da execução. R-1 a R-11 documentados. |
| [`docs/wave3-v4-c19/smoke-validation.md`](smoke-validation.md) | ✅ inventariado — 20 cenários humanos. |

### 1.3 Código-fonte tocado pelo C19 (revisado integralmente)

| Caminho | Estado | Observações |
|---|---|---|
| [`frontend/src/app/(dashboard)/escanear/page.tsx`](../../frontend/src/app/(dashboard)/escanear/page.tsx) | 785 LOC pós-C19 | `<ManualPanel>` linhas 657-765; `MENSAGENS_C19` / `mensagemFinal` linhas 45-51. |
| [`frontend/src/lib/codigo-publico.ts`](../../frontend/src/lib/codigo-publico.ts) | 144 LOC | Funções puras; AUD-W3C19-006 sugere JSDoc explícito sobre comportamento silencioso. |
| [`frontend/src/hooks/useCodigoPrvInput.ts`](../../frontend/src/hooks/useCodigoPrvInput.ts) | 68 LOC | Binding sem testes Vitest (D9). |
| [`frontend/src/lib/__tests__/codigo-publico.test.ts`](../../frontend/src/lib/__tests__/codigo-publico.test.ts) | 295 LOC | 43 testes. AUD-W3C19-003 adiciona testes novos em arquivo separado. |
| [`frontend/src/lib/services/identificacao-prova.ts`](../../frontend/src/lib/services/identificacao-prova.ts) | 192 LOC | **PROIBIDO TOCAR** (camada de serviço do C10). `git diff development..HEAD` retorna vazio — confirmado. |
| [`frontend/src/app/(dashboard)/escanear/escanear.module.css`](../../frontend/src/app/(dashboard)/escanear/escanear.module.css) | sem modificação | `git diff` retorna vazio. Regra `.errorBanner strong { font-weight: 600 }` (linha 510) **já existia em `development`** — confirmado via `git show development:...css`. Regra `.manualInputWrapper[aria-invalid="true"] { border-color: #b91c1c }` (linha 581) idem. |
| `backend/**` | sem modificação | `git diff` retorna vazio. |
| `shared/access-matrix.json` | sem modificação | Rule `scanner` inalterada. |

### 1.4 Documentos do produto v4.0

| Documento | Trechos consultados |
|---|---|
| `RequisitosProvasDigitais_v4_0.docx` | RF-005 (fallback), US-002, RNF-008 (a11y). |
| `BACKLOG_RastreioProvasDigitais_v4_0.docx` | Componente 19 — rate-limit citado textualmente nas Notas Técnicas (suporte ao DEFERRED do AUD-001). |
| `DAT_RastreioProvasDigitais_v3_0.docx` | §8.1 idempotência, §8.2 anti-enumeração + 30/min/user rate-limit, §8.3 alfabeto. |
| `UML_RastreioProvasDigitais_v4_0.drawio` | sem alteração de estado para C19 (C11 cobre transições). |

---

## 2. Inventário Consolidado dos Achados

Tabela completa dos achados mapeados a partir do `audit-report.md`. Total = 13 acionáveis + ~20 INFOs.

| ID | Severidade | Categoria | Descrição resumida | Arquivo / Evidência | Status nesta sessão | Anti-enum? | Visual? | C10? | Legacy? | A11y? |
|---|---|---|---|---|---|---|---|---|---|---|
| **AUD-W3C19-001** | ALTO | Segurança | Rate-limit backend ausente em `/api/v1/provas/scan` (DAT §8.2 + Backlog C19 "30/min/user → 429"). Já registrado pelo autor como ADR-145 FOLLOW-UP OBRIGATÓRIO. | `backend/app/api/v1/provas.py` (não tocado pelo C19) | **DEFERRED** — encaminhar para sessão dedicada pós-auditoria do C10 (ou C20+). Justificativa: implementar exige mexer no backend, vetado pelo escopo do prompt (Seção 1 "Não modifica a camada de serviço ou o endpoint do C10"). | sim (indireto) | não | sim (backend C10) | não | não |
| **AUD-W3C19-002** | MÉDIO | Manutenibilidade / Aderência | `<strong>` envolvendo `{state.mensagem}` adicionado no `<ManualPanel>` (`page.tsx:737`). Auditor classificou como modificação visual sutil. | `page.tsx:737` (diff confirmado: linha era `{state.mensagem}` em `development`). | **Plano A (recomendado): REVERTER** — remover `<strong>`. **Plano B alternativo** abaixo. | não | sim (sutil) | não | não | parcial |
| **AUD-W3C19-003** | MÉDIO | Cobertura de testes | Falta teste de integração da uniformização `mensagemFinal("QR_INVALIDO") === MENSAGENS_ERRO_PADRAO["PROVA_NAO_ENCONTRADA"]`. A função está em `page.tsx` (não testável sem render). | `page.tsx:45-51` | **CORRIGIR** — extrair `MENSAGENS_C19` + `mensagemFinal` para arquivo standalone `frontend/src/lib/c19-mensagens.ts` + 4-6 testes Vitest. | sim (validação) | não | não | não | não |
| **AUD-W3C19-004** | MÉDIO | A11y | `aria-invalid` no `<div className={manualInputWrapper}>` em vez do `<input>`. Auditor nota que é herança do C10 mas leitores de tela esperam o atributo no campo de entrada. | `page.tsx:695-725` | **CORRIGIR** — **adicionar** `aria-invalid` no `<input>` mantendo no wrapper (necessário para a regra CSS `.manualInputWrapper[aria-invalid="true"]` linha 581-583). Mudança a11y aprofundada, não-visual. | não | não | não | não | **sim** |
| AUD-W3C19-005 / 031 | BAIXO | Cobertura | `useCodigoPrvInput` sem teste isolado (D9 — sem JSDOM). | `hooks/useCodigoPrvInput.ts` | **ACEITO** — registrar status final no `audit-report.md` (apêndice) + manter justificativa D9. Sem mudança de código. | não | não | não | não | não |
| AUD-W3C19-006 | BAIXO | Manutenibilidade | `aplicarMascara` silencia entradas inválidas (`null`/`number`) retornando `""`. Comportamento OK mas docs implícitas. | `codigo-publico.ts:98-122` | **CORRIGIR** — adicionar 3-4 linhas de JSDoc explicitando "retorna '' para entrada não-string (`undefined`/`null`/`number`)". Trivial. | não | não | não | não | não |
| AUD-W3C19-007 | BAIXO | Aderência | Auto-submit ao completar 18 chars NÃO implementado (D6 NÃO). | `page.tsx` (decisão arquitetural) | **ACEITO** — registrar status final. D6 ratificada. Sem mudança de código. | não | não | não | não | não |
| AUD-W3C19-008 | BAIXO | Cobertura | Cobertura zero de `mensagemFinal` em `page.tsx`. | `page.tsx:49-51` | **COBERTO POR AUD-003** — quando `c19-mensagens.ts` for criado, o teste Vitest cobre. Sem ação separada. | sim (validação) | não | não | não | não |
| AUD-W3C19-028 | BAIXO | Manutenibilidade | `CODIGO_PUBLICO_REGEX` exportado **e** inline (`.test()` direto + função wrapper). Sem drift; intencional. | `codigo-publico.ts:40-53` | **ACEITO** — registrar status final. Auditor diz "decisão deliberada". Sem mudança. | não | não | não | não | não |
| AUD-W3C19-009 / 033 | INFO | Cobertura | Smoke E2E DEFERRED (`smoke-validation.md` 20 cenários). | `docs/wave3-v4-c19/smoke-validation.md` | **REGISTRADO** — Mario executa antes do PR para `main`. Sem mudança nesta sessão. | não | não | não | sim | não |
| AUD-W3C19-013 | INFO | Segurança | Vazamento via timing client-side vs backend (~100ms vs <1ms). | `page.tsx` (lógica de validação) | **ACEITO** — ADR-143 já registra. Sem mudança. | sim | não | não | não | não |
| AUD-W3C19-014 | INFO | Segurança | Auto-complete do browser corretamente desabilitado (`autoComplete="off"` + `autoCapitalize="characters"` + `spellCheck={false}`). | `page.tsx:713-715` | **REGISTRADO** — boa prática mantida. | não | não | não | não | não |
| AUD-W3C19-015 | INFO | Segurança | XSS via input descartado — código só vai para `mensagemFinal(codigo)` via constants. | `page.tsx` (caminho de mensagem) | **REGISTRADO** — zero risco. | não | não | não | não | não |
| AUD-W3C19-016 | INFO | UX | Submit via Enter com display incompleto dispara mensagem genérica via D7. | `page.tsx:172-179` | **REGISTRADO** — decisão de design (anti-enumeração). | sim | não | não | não | não |
| AUD-W3C19-017 | INFO | Bug | `aplicarMascara` silencia entradas não-string. | `codigo-publico.ts` | **COBERTO POR AUD-006** (JSDoc). | não | não | não | não | não |
| AUD-W3C19-018 | INFO | UX | Reset de banner é não-condicional ao começar a digitar (D8). | `page.tsx:201-209` | **REGISTRADO** — coerente. | não | não | não | não | não |
| AUD-W3C19-019 | INFO | Regressão | C10 scanner por câmera continua funcionando. | `useScanner`/`handleDetect` | **REGISTRADO** — zero regressão. | não | não | não | não | não |
| AUD-W3C19-020 | INFO | Regressão | Teste anti-acoplamento (`identificacao-prova.test.ts:286-299`) ainda passa. | testes | **REGISTRADO** — verde no Vitest. | não | não | não | não | não |
| AUD-W3C19-021 | INFO | Regressão | Navegação para `/provas/[id]` preservada em ambos os caminhos (câmera + manual). | `page.tsx` | **REGISTRADO**. | não | não | não | não | não |
| AUD-W3C19-022 | INFO | Regressão | Wave 1 (RBAC) preservada — middleware e RLS inalterados. | `middleware.ts` + RLS | **REGISTRADO**. | não | não | não | não | não |
| AUD-W3C19-023 | INFO | Regressão | C06 (cadastro) preservado — `git diff nova-prova/` vazio. | `nova-prova/page.tsx` | **REGISTRADO**. | não | não | não | não | não |
| AUD-W3C19-024 | INFO | Regressão (legacy) | 11 provas legacy preservadas com `codigo_publico` 100% backfilled. C19 funciona para elas. | MCP query | **REGISTRADO**. | não | não | não | **sim** | não |
| AUD-W3C19-025 | INFO | Performance | Bundle `/escanear` +0.63 kB (Size) / 0 kB (First Load). | next build | **REGISTRADO**. | não | não | não | não | não |
| AUD-W3C19-026 | INFO | Performance | Validação regex sem debounce (custo trivial). | `useCodigoPrvInput` | **REGISTRADO**. | não | não | não | não | não |
| AUD-W3C19-027 | INFO | Performance | Sem memory leak detectado. | `useScanner` cleanup | **REGISTRADO**. | não | não | não | não | não |
| AUD-W3C19-029 | INFO | Manutenibilidade | TypeScript estrito preservado. Zero `any`. | `tsconfig.json` + page.tsx | **REGISTRADO**. | não | não | não | não | não |
| AUD-W3C19-030 | INFO | Manutenibilidade | Comentários explicam o **porquê** com referência a ADRs/risks. | `page.tsx` + `codigo-publico.ts` | **REGISTRADO**. | não | não | não | não | não |
| AUD-W3C19-032 | INFO | Cobertura | 43 testes Vitest na util + 18 na camada de serviço = 89/89 verde. | vitest run | **REGISTRADO**. | não | não | não | não | não |
| AUD-W3C19-034 / 035 / 036 | INFO | Documentação | `CHANGELOG.md` + ADRs 141-145 + `contrato-c19.md` Seção 7 completos. | docs | **REGISTRADO**. | não | não | não | não | não |
| AUD-W3C19-037 / 038 | INFO | Aderência | Cada decisão coerente com `analysis.md` + escopo declarado respeitado. | docs | **REGISTRADO**. | não | não | não | não | não |
| AUD-W3C19-039 / 040 | INFO | Prep. futura | C19 não bloqueia C11 (state machine) nem C12 (timeline). | `page.tsx` (apenas `router.push`) | **REGISTRADO**. | não | não | não | não | não |

**Total acionável:** 13 (1 ALTO DEFERRED + 3 MÉDIOS CORRIGÍVEIS + 5 BAIXOS distribuídos).
**Total registrado sem mudança de código:** ~24 (INFOs + 3 BAIXOS aceitos).
**Nenhum CRÍTICO. Nenhum achado de modificação não-autorizada da camada de serviço.**

### 2.1 Notas críticas sobre AUD-W3C19-002

Investigação adicional do auditor (confirmada nesta sessão via `git show development:...`):

1. **CSS `.errorBanner strong { font-weight: 600 }` (linha 510 do `escanear.module.css`) JÁ existia em `development`** — o C10 antecipou suporte ao `<strong>` no banner.
2. **CameraPanel JÁ USAVA `<strong>{state.mensagem}</strong>`** no banner desde o C10 (linha 362 em `development` / linha 426 pós-C19).
3. O C19 adicionou o `<strong>` apenas no ManualPanel, **uniformizando** os dois banners do mesmo componente.

Isso justifica registrar como Plano B alternativo abaixo. Decisão final fica para o Mario no Gate 2.

---

## 3. Validação MCP Supabase (Read-Only)

Executada via `mcp__c7b61d2f-...__execute_sql` em projeto `rwxlpwmnkekzuurgthkr` (ACTIVE_HEALTHY, sa-east-1, Postgres 17.6.1.104). Resultado: **estado real bate exatamente com o descrito no `audit-report.md` §4** — zero divergência. Pode-se proceder com confiança no Gate 2.

### 3.1 Estado da tabela `provas_digitais`

```
codigo_publico   varchar(20)  NOT NULL  ✅
nro_requerimento varchar(50)  NOT NULL  ✅
rota             USER-DEFINED NULLABLE  ✅ (legacy)
status           USER-DEFINED NOT NULL  ✅
vendedor_id      uuid         NOT NULL  ✅
```

### 3.2 Índices em `provas_digitais` (10 totais)

`idx_provas_codigo_publico` (UNIQUE), `idx_provas_created_at`, `idx_provas_rota`, `idx_provas_status`, `idx_provas_status_created`, `idx_provas_vendedor`, `idx_provas_vendedor_status`, `provas_digitais_nro_requerimento_key` (UNIQUE), `provas_digitais_pkey`, `provas_digitais_qr_code_hash_key`. ✅

### 3.3 RLS policies

`provas_digitais` (3 policies):
- `pol_provas_select` — admin OR vendedor_id=user OR (status=COM_MOTORISTA AND setor=MOTORISTA) OR (status IN (ENVIADA/ENCAMINHADA/RECEBIDA) AND setor=CLICHERIA).
- `pol_provas_insert` — qual NULL (definido pela rota via guard backend).
- `pol_provas_update` — admin only.

`audit_logs` (1 policy):
- `pol_audit_select` — admin only.

✅ Anti-enumeração no backend preservada (vendedor digitando código alheio → 0 rows → 404 genérico).

### 3.4 Distribuição real de dados

```
total: 17 | sem_codigo: 0 | sem_rota: 11 | com_rota: 6 | rotas_distintas: 3 | criadas: 6
```

✅ 100% backfilled de `codigo_publico` — C19 funciona para todas as 17 provas, incluindo as 11 legacy v3.0 (`rota=NULL`).

### 3.5 Advisors

**Security (2 — pré-existentes):**
- `rls_enabled_no_policy` em `alembic_version` (INFO, intencional ADR-025).
- `auth_leaked_password_protection` (WARN, WONTFIX plano pago ADR-027).

**Performance (13 unused_index — pré-existentes):**
- `idx_configuracoes_sistema_updated_by`, `idx_usuarios_setor`, `idx_usuarios_ativo`, `idx_provas_status`, `idx_provas_vendedor`, `idx_movimentacoes_prova`, `idx_movimentacoes_usuario`, `idx_movimentacoes_prova_ciclo`, `idx_audit_prova`, `idx_movimentacoes_created_at`, `idx_usuarios_created_by`, `idx_movimentacoes_status_novo_created_at`, `idx_provas_rota`.

Zero novo alerta. Conformidade com pós-C10 / pós-C19.

### 3.6 `alembic_version`

```
version_num = 012
```

Wave 2 v4.0. Zero migration nova nesta auditoria/correção. C19 é frontend-only.

### 3.7 Cloudflare R2

Não tocado. Sem chamada no C19. Conformidade integral.

---

## 4. Plano de Correção por Achado

Estratégias para cada achado CORRIGÍVEL e DEFERRED, ordenadas pela ordem de execução proposta na §5.

### 4.1 AUD-W3C19-003 (MÉDIO) — Teste de integração da uniformização

**Estratégia:** extrair `MENSAGENS_C19` + `mensagemFinal` de `page.tsx` (linhas 32-51) para arquivo standalone `frontend/src/lib/c19-mensagens.ts`. Permite teste sem render.

**Confirmação de escopo:**
- ✅ Não toca CSS/visual da UI do C10.
- ✅ Não toca `identificacao-prova.ts` (camada de serviço — apenas IMPORTA `CodigoErro` + `mensagemPara`).
- ✅ Não toca backend.

**Arquivos tocados:**
- **NEW** `frontend/src/lib/c19-mensagens.ts` (~25 LOC: export `MENSAGENS_C19` + `mensagemFinal` + JSDoc explicando anti-enumeração).
- **NEW** `frontend/src/lib/__tests__/c19-mensagens.test.ts` (~50 LOC: 6 testes — 4 cobrindo `mensagemFinal` para cada codigo + 1 paridade byte-a-byte `mensagemFinal("QR_INVALIDO") === MENSAGENS_ERRO_PADRAO["PROVA_NAO_ENCONTRADA"]` + 1 garantindo que `MENSAGENS_C19` só sobrescreve `QR_INVALIDO`).
- **EDIT** `frontend/src/app/(dashboard)/escanear/page.tsx` — remove definição local de `MENSAGENS_C19`/`mensagemFinal` e importa de `@/lib/c19-mensagens`. Diff esperado: -15 LOC, +1 LOC import.

**Tipo de mudança:** novo arquivo + edição (refactor para extrair função pura).

**Camadas afetadas:** apenas lógica do C19. Camada de serviço inalterada.

**Risco de regressão:** BAIXO. Função extraída é determinística e tem 0 lado-efeito. Smoke check: `next build` + Vitest passam após o refactor.

**Anti-enumeração:** **SIM, é o ponto central**. O teste de paridade byte-a-byte garante a invariante crítica.

**Teste de validação:** 
```bash
npx vitest run frontend/src/lib/__tests__/c19-mensagens.test.ts
# Esperado: 6 passed
```
Adicionalmente: rodar suite completa (`npx vitest run`) e confirmar 89 + 6 = **95 testes passed**.

**Dependências:** nenhuma. Resolve AUD-W3C19-008 automaticamente (cobertura de `mensagemFinal`).

---

### 4.2 AUD-W3C19-004 (MÉDIO) — `aria-invalid` no input

**Estratégia:** adicionar `aria-invalid={isError ? "true" : "false"}` ao `<input>` (page.tsx:705-725), **mantendo** o atributo no `<div className={styles.manualInputWrapper}>` (page.tsx:695-697). Justificativa do "manter no wrapper": a regra CSS `.manualInputWrapper[aria-invalid="true"] { border-color: #b91c1c }` (linha 581-583 do `escanear.module.css`) depende do seletor de atributo. Mover para `:has(input[aria-invalid="true"])` ou para CSS-in-JS exigiria modificar CSS — vetado.

Duplicação de `aria-invalid` no wrapper e no input é **benigna e padrão recomendado** quando o estado de validação precisa simultaneamente alimentar (a) tecnologias assistivas que consultam o input e (b) regras de estilo no contêiner.

**Confirmação de escopo:**
- ✅ Não toca CSS/visual da UI do C10 (atributo a11y, não renderização).
- ✅ Não toca camada de serviço nem backend.

**Arquivos tocados:**
- **EDIT** `frontend/src/app/(dashboard)/escanear/page.tsx` — 1 linha adicionada no `<input>`.

**Tipo de mudança:** edição mínima (1 atributo a11y).

**Camadas afetadas:** apenas a11y do C19.

**Risco de regressão:** BAIXO. Adicionar `aria-invalid` ao input não afeta CSS (regra continua sobre o wrapper). Validação: axe-core não deve reportar novo issue; leitor de tela passa a anunciar "inválido" ao focar no campo.

**Anti-enumeração:** não aplicável.

**A11y:** **SIM**, é a categoria principal. Validação:
1. `npx vitest run` — sem regressão.
2. Smoke E2E manual: focar no input em erro, leitor de tela (VoiceOver/NVDA) deve anunciar "inválido".
3. Smoke axe-core (cenário 20 do smoke-validation.md) — sem nova violação.

**Dependências:** nenhuma.

---

### 4.3 AUD-W3C19-002 (MÉDIO) — `<strong>` no banner do ManualPanel

**Decisão pendente — duas opções formais para o Gate 2:**

#### Plano A (recomendado pelo prompt) — REVERTER

**Estratégia:** remover `<strong>` do `<ManualPanel>` (page.tsx:737), retornando ao texto puro `{state.mensagem}`. **Não tocar** o CameraPanel (que já tinha `<strong>` em `development` — não foi introdução do C19).

**Justificativa:** o prompt Seção 5.3 "Achados de modificação visual a reverter" diz: "Não adicionar nova mudança visual para 'corrigir' — apenas reverter."

**Efeito colateral:** disparidade visual entre os dois banners. CameraPanel mantém peso 600 (vinha do C10), ManualPanel volta a peso 400 (padrão). Possível regressão UX de uniformidade. **Aceitável** porque o C10 originalmente entregou os dois banners com peso 400 ou similar; foi o C19 que uniformizou via `<strong>` no ManualPanel.

**Arquivos tocados:** `frontend/src/app/(dashboard)/escanear/page.tsx` — 1 linha (remove `<strong>...</strong>`).

**Tipo:** reversão (`revert(...)` conventional commit).

#### Plano B (recomendado pelo auditor) — REGISTRAR formalmente + manter

**Estratégia:** **manter** o `<strong>` no ManualPanel. Adicionar apêndice no ADR-144 (`DECISIONS.md`) justificando: "uniformização semântica com o `<strong>` pré-existente do CameraPanel — regra CSS `.errorBanner strong` já estava em `development`, não é introdução de regra visual nova."

**Justificativa:** o auditor explicitamente classificou como "justificável como melhoria semântica de a11y" e recomendou registrar. O prompt Seção 7 "Regras de Integridade" permite "reclassificação para DEFERRED apenas para achados de modificação visual ou de camada/endpoint do C10".

**Arquivos tocados:** apenas `DECISIONS.md` (apêndice no ADR-144) + `CHANGELOG.md` (linha justificando).

**Tipo:** `docs(...)` conventional commit.

#### Decisão proposta

**Plano A** (REVERTER) é o **default seguido pela sessão** caso o Mario não escolha no Gate 2 — alinhado com fidelidade estrita ao prompt. Plano B é a alternativa que o Mario pode autorizar nominalmente.

**Risco de regressão:**
- Plano A: BAIXO (apenas semântica de fonte). Disparidade visual entre os dois banners é nova mas não-bloqueante.
- Plano B: ZERO em runtime; o trade-off é apenas documental.

**Dependências:** nenhuma.

---

### 4.4 AUD-W3C19-006 (BAIXO) — JSDoc em `aplicarMascara`

**Estratégia:** adicionar bloco JSDoc explícito documentando comportamento para entradas não-string. Texto sugerido:

```typescript
/**
 * ...
 * @param raw Entrada crua do usuário (tipicamente `e.target.value`).
 * @returns Display formatado `YYYY-MM-NNNNNN` (sem prefixo).
 *   Para entradas não-string (`null`, `undefined`, `number`, etc.),
 *   retorna `""` silenciosamente. Por construção, `e.target.value`
 *   é sempre string em handlers de `<input>`, então o risco é zero
 *   em uso normal — a salvaguarda existe contra reutilizações
 *   indevidas da função (testes, etc.).
 */
```

**Confirmação de escopo:**
- ✅ Não toca CSS nem visual.
- ✅ Não toca camada de serviço nem backend.

**Arquivos tocados:**
- **EDIT** `frontend/src/lib/codigo-publico.ts` — 7-10 linhas de JSDoc adicionadas.

**Tipo:** `docs(...)` conventional commit.

**Risco de regressão:** ZERO (apenas comentário).

**Validação:** `npx tsc --noEmit` continua exit 0.

**Dependências:** nenhuma.

---

### 4.5 AUD-W3C19-008 (BAIXO) — Cobertura de `mensagemFinal`

**Resolução:** **automática via AUD-W3C19-003**. Quando `mensagemFinal` for movida para `frontend/src/lib/c19-mensagens.ts` (arquivo standalone), o teste Vitest correspondente passa a existir.

**Arquivos tocados:** nenhum extra (coberto por §4.1).

**Status final:** RESOLVIDO no commit de AUD-003.

---

### 4.6 AUD-W3C19-001 (ALTO) — Rate-limit backend

**Estratégia:** **DEFERRED** com encaminhamento explícito.

**Justificativa do deferral:**
- Implementar exige modificar `backend/app/api/v1/provas.py` (endpoint `/scan`) e schemas Pydantic + middleware `slowapi`. Isso é **modificação não-autorizada do C10** sob a perspectiva desta sessão (prompt Seção 1 "Não modifica a camada de serviço ou o endpoint do C10").
- O autor do C19 já registrou em ADR-145 (`DECISIONS.md`) como FOLLOW-UP OBRIGATÓRIO.
- Auditor confirmou (`audit-report.md` §6.1 + §"Recomendações") como bloqueante para PR em `main`, não para PR em `development`.

**Encaminhamento:** "Tratar em sessão dedicada de implementação backend (sugestão de slug: `wave3-v4-rate-limit-scan` ou C20+), com:
1. Middleware `slowapi` no `/scan` filtrado por `current_user.id` (30/min).
2. Mapear 429 para novo codigo `RATE_LIMITED` em `frontend/src/lib/services/identificacao-prova.ts` (`CodigoErro` união + entrada em `MENSAGENS_ERRO_PADRAO`).
3. Testes backend + Vitest na camada de serviço.
4. Atualizar `contrato-c19.md` e `DECISIONS.md`.
5. Smoke E2E manual."

**Arquivos tocados nesta sessão:** apenas documentais — `audit-report.md` (apêndice) + `DECISIONS.md` (apêndice ao ADR-145) + `CHANGELOG.md` (linha confirmando deferral).

**Tipo:** `docs(...)` conventional commit registrando o DEFERRED.

**Risco de regressão:** ZERO (apenas docs).

**Dependências:** nenhuma — mas o status do C19 em `main` permanece BLOQUEADO até implementação na sessão dedicada.

---

### 4.7 AUD-W3C19-005 / 031 (BAIXO) — `useCodigoPrvInput` sem teste

**Estratégia:** **ACEITO** — registrar status final.

**Justificativa:** D9 da `analysis.md` ratificada — hook é binding trivial (3 funções `useCallback` + 3 `useMemo` sobre lib pura já testada com 43 testes). Vitest config em `environment: node` (Wave 1 v4.0 / D-13). Cobertura por E2E.

**Arquivos tocados nesta sessão:** apenas `audit-report.md` (apêndice) com status "ACEITO — D9".

**Tipo:** `docs(...)` conventional commit registrando aceitação.

**Risco de regressão:** ZERO.

---

### 4.8 AUD-W3C19-007 (BAIXO) — Auto-submit ao completar 18 chars

**Estratégia:** **ACEITO** — D6 NÃO ratificada.

**Justificativa:** auto-submit cria UX imprevisível em smoke (cenário 2 do smoke-validation.md prevê clique explícito). Decisão alinhada com C10 smoke.

**Arquivos tocados nesta sessão:** apenas `audit-report.md` (apêndice) com status "ACEITO — D6".

**Tipo:** `docs(...)`.

**Risco de regressão:** ZERO.

---

### 4.9 AUD-W3C19-028 (BAIXO) — `CODIGO_PUBLICO_REGEX` exportado + inline

**Estratégia:** **ACEITO** — auditor classificou como "decisão deliberada, sem drift". Sem mudança.

**Justificativa:** o export é útil para consumidores que precisam `.test()` direto; o uso interno em `validarFormatoCodigoPublico` (linha 50-53) garante o caminho recomendado. Teste de paridade no `codigo-publico.test.ts` (linhas 100-109) confirma identidade.

**Arquivos tocados nesta sessão:** apenas `audit-report.md` (apêndice) com status "ACEITO — sem drift".

**Tipo:** `docs(...)`.

**Risco de regressão:** ZERO.

---

### 4.10 INFOs (AUD-W3C19-009 / 013 / 014 / 015 / 016 / 017 / 018 / 019 / 020 / 021 / 022 / 023 / 024 / 025 / 026 / 027 / 029 / 030 / 032 / 033 / 034 / 035 / 036 / 037 / 038 / 039 / 040)

**Estratégia:** **REGISTRADO** em apêndice do `audit-report.md` com status "INFO — sem ação requerida". Mesma justificativa do auditor.

**Caso especial AUD-W3C19-017:** coberto pelo JSDoc do AUD-006.

**Arquivos tocados:** apenas `audit-report.md` (apêndice consolidando todos os INFOs em 1 tabela).

**Tipo:** `docs(...)`.

**Risco de regressão:** ZERO.

---

## 5. Ordem de Execução Proposta (Topológica)

Respeitando hierarquia: CRÍTICO → ALTO → MÉDIO → BAIXO → INFO, e dentro de cada nível: anti-enumeração → legacy → a11y → outros.

### 5.1 Ordem dos commits

| # | Commit | Achado(s) | Tipo | Resolve |
|---|---|---|---|---|
| 1 | `refactor(wave3-v4/c19/AUD-W3C19-003): extrai MENSAGENS_C19 + mensagemFinal para lib/c19-mensagens.ts` | AUD-003 + AUD-008 | refactor + test | MÉDIO + BAIXO |
| 2 | `a11y(wave3-v4/c19/AUD-W3C19-004): aria-invalid tambem no <input>` | AUD-004 | a11y | MÉDIO |
| 3 | `revert(wave3-v4/c19/AUD-W3C19-002): remove <strong> do banner do ManualPanel` **OU** `docs(wave3-v4/c19/AUD-W3C19-002): registra <strong> como uniformizacao com CameraPanel em ADR-144` | AUD-002 | revert OU docs | MÉDIO |
| 4 | `docs(wave3-v4/c19/AUD-W3C19-006): JSDoc explicita comportamento silencioso de aplicarMascara` | AUD-006 | docs | BAIXO |
| 5 | `docs(wave3-v4/c19/AUD-W3C19-001): deferred backend rate-limit (encaminhado para sessao dedicada)` | AUD-001 | docs (DEFERRED) | ALTO |
| 6 | `docs(wave3-v4/c19/fixes): registra status final dos BAIXO/INFO aceitos no audit-report` | 005/031, 007, 028 + ~20 INFOs | docs | BAIXO + INFO |
| 7 | `docs(wave3-v4/c19/fixes): atualiza CHANGELOG + DECISIONS + CLAUDE + contrato-c19 pos-correcao` | — | docs | acumulativo |

Total: **7 commits atômicos**.

**Validação intermediária** após cada CRÍTICO/ALTO/MÉDIO: rodar `npx vitest run` + `npx tsc --noEmit` antes do próximo commit.

### 5.2 Decisão pendente no Gate 2 — AUD-002

| Opção | Plano de execução | Implicação |
|---|---|---|
| **A — Reverter** (default) | Remove `<strong>` no ManualPanel. Commit `revert(...)`. | Disparidade visual entre os 2 banners. |
| **B — Registrar formalmente** | Mantém `<strong>`. Apêndice ADR-144 + CHANGELOG. Commit `docs(...)`. | Uniformidade visual mantida. Alinhamento com recomendação do auditor. |

**Solicitação ao Mario no Gate 2:** confirmar "A" ou "B" ao autorizar.

---

## 6. Análise de Risco Agregado

### 6.1 Achados com risco ALTO de regressão

**Nenhum.** Os 3 MÉDIOS são mudanças cirúrgicas (1 arquivo novo + 1 import refatorado + 1 atributo a11y + 1 linha removida/registrada).

### 6.2 Achados de anti-enumeração na UI

- **AUD-W3C19-003** (validação): após correção, terá teste de paridade byte-a-byte garantindo `mensagemFinal("QR_INVALIDO") === MENSAGENS_ERRO_PADRAO["PROVA_NAO_ENCONTRADA"]`. **Bloqueante de qualquer regressão futura por TypeScript build-time + Vitest run-time.**
- **AUD-W3C19-013** (timing): aceito por ADR-143. Sem ação.
- **AUD-W3C19-008** (cobertura): resolvido em conjunto com AUD-003.

**Validação adicional ao final:** comparar respostas do backend para os 3 cenários de 404 (inexistente, fora-do-scope, formato inválido) byte-a-byte. Validação via curl em staging — não exige Mario porque é confronto de strings.

### 6.3 Achados de modificação visual não-autorizada

- **AUD-W3C19-002** — único achado nesta categoria. Plano A (REVERTER) é o default.

**Verificação pós-correção (independente do plano escolhido):**

```bash
git diff <hash inicial = 999e5b0>..HEAD -- '**/*.css' '**/*.module.css' '**/*.scss'
# Esperado: VAZIO
```

### 6.4 Achados de modificação não-autorizada do C10

- **AUD-W3C19-001** — DEFERRED com encaminhamento. Esta sessão não toca o backend.

**Verificação pós-correção:**

```bash
git diff <hash inicial = 999e5b0>..HEAD -- backend/ frontend/src/lib/services/identificacao-prova.ts shared/access-matrix.json
# Esperado: VAZIO
```

### 6.5 Achados que afetam provas legacy

- **AUD-W3C19-024** (INFO) — 11 provas legacy preservadas via `codigo_publico` 100% backfilled. Confirmado via MCP (`sem_codigo=0`).

**Verificação pós-correção:** rodar `npx vitest run frontend/src/lib/__tests__/codigo-publico.test.ts` — 43 testes incluem cenários para formato esperado das 11 provas legacy. Adicionalmente: smoke cenário 9 do `smoke-validation.md` usa `PRV-2026-04-RVZF73` (legacy `rota=NULL`) para confirmar identificação.

### 6.6 Achados de acessibilidade

- **AUD-W3C19-004** — `aria-invalid` no input.
- **AUD-W3C19-002** Plano A (reverter `<strong>`) tem impacto a11y parcial (perda de ênfase semântica em alertas).

**Verificação:**
1. `npx vitest run` (sem regressão de testes existentes).
2. Smoke E2E manual: navegação por teclado (Tab/Shift+Tab) através do ManualPanel.
3. Smoke axe-core (cenário 20 do `smoke-validation.md`) — deve continuar com 0 violações críticas.
4. (Se possível) Mario testa com VoiceOver no celular ou NVDA no Windows: anúncio "inválido" no campo após erro.

### 6.7 Achados que tocam código de Waves anteriores

**Nenhum.** Todas as correções operam dentro do escopo do C19:
- `page.tsx (escanear)` — arquivo modificado pelo C19.
- `codigo-publico.ts` — arquivo CRIADO pelo C19.
- `c19-mensagens.ts` — arquivo NOVO desta sessão de correção.

### 6.8 Achados bloqueados por divergência

**Nenhum** (validação MCP §3 confirmou estado real bate com o descrito no `audit-report.md`).

### 6.9 Achados DEFERRED com encaminhamento

| ID | Categoria | Encaminhamento |
|---|---|---|
| AUD-W3C19-001 (ALTO) | Modificação não-autorizada do backend C10 | Sessão dedicada de rate-limit backend (`wave3-v4-rate-limit-scan` ou C20+). Sem prazo desta sessão. |
| AUD-W3C19-002 Plano B (MÉDIO — se Mario escolher B no Gate 2) | Modificação visual | Não aplicável: Plano B mantém o `<strong>`. Plano A reverte sem deferral. |

---

## 7. Plano de Validação Interna Pós-Correção

Conforme §6 do prompt. Resultado vai para `docs/wave3-v4-c19/fix-validation.md` no fim do Gate 2.

### 7.1 Checklist objetivo

| # | Item | Critério |
|---|---|---|
| 1 | Verificação de não-modificação visual | `git diff 999e5b0..HEAD -- '**/*.css' '**/*.module.css' '**/*.scss'` retorna **vazio**. |
| 2 | Verificação de não-modificação da camada de serviço | `git diff 999e5b0..HEAD -- 'frontend/src/lib/services/identificacao-prova.ts'` retorna **vazio**. |
| 3 | Verificação de não-modificação do backend | `git diff 999e5b0..HEAD -- backend/` retorna **vazio**. |
| 4 | Suíte completa Vitest | `npx vitest run` → **95 passed** (era 89 + 6 novos do `c19-mensagens.test.ts`). |
| 5 | tsc --noEmit | `npx tsc --noEmit` exit 0. |
| 6 | next build | 13/13 páginas (sem regressão de bundle). |
| 7 | Teste anti-enumeração na UI | Teste do `c19-mensagens.test.ts` paridade byte-a-byte passa. **Mensagem do banner** em runtime (smoke E2E) idêntica para QR_INVALIDO (client) + QR_INVALIDO (422) + PROVA_NAO_ENCONTRADA (404). |
| 8 | Teste anti-enumeração no backend | curl em staging: `POST /scan` com `{"codigo": "PRV-1234-13-XYZTUV"}` (fora do range mes) e `{"codigo": "PRV-2026-05-NAOEXIST"}` (formato OK, inexistente). Comparar HTTP status + body. **Esperado:** 404 idêntico nos 2 (DAT §8.2). |
| 9 | Teste de validação client-side | 43 testes do `codigo-publico.test.ts` continuam verdes. |
| 10 | Teste de máscara (paste) | Coberto pelos 43 testes. |
| 11 | Prova legacy (`rota IS NULL`) | Smoke cenário 9 com `PRV-2026-04-RVZF73`. (DEFERRED — Mario executa). |
| 12 | Prova sem código alfanumérico (`codigo IS NULL`) | MCP confirma `sem_codigo=0` em produção — cenário não-aplicável atualmente, mas backend retornaria 404 (lookup falha) — comportamento documentado. |
| 13 | Acessibilidade axe-core | Smoke cenário 20 — 0 violações críticas. (DEFERRED). |
| 14 | Acessibilidade navegação por teclado | Smoke cenários 16-17. (DEFERRED). |
| 15 | Acessibilidade leitor de tela | Smoke cenário 16. (DEFERRED — Mario testa com VoiceOver/NVDA). |
| 16 | Cobertura ≥ 80% domínio | `npx vitest run --coverage` (DEFERRED — não bloqueante; lib pura tem ~100%). |
| 17 | get_advisors MCP sem novos alertas | Comparação byte-a-byte com snapshot do §3.5. Esperado: 2 security + 13 performance, idênticos. |
| 18 | Performance < 2s (RNF-001) | EXPLAIN ANALYZE do backend continua 0.105 ms. Smoke real (DEFERRED). |
| 19 | Sem erros no console | DEFERRED via smoke. |
| 20 | `contrato-c19.md` atualizado | Se a correção afetou consumo: adicionar nota em §3.5 sobre a extração para `c19-mensagens.ts`. |

### 7.2 Verificação por achado

Em `fix-validation.md`, atestar para cada um:
- Status final: **RESOLVIDO** (commit SHA) / **DEFERRED** (encaminhamento) / **ACEITO** (justificativa) / **REGISTRADO INFO** (sem ação) / **BLOQUEADO** (motivo) / **NÃO APLICÁVEL** (justificativa).
- Critério objetivo de prova.
- Se era anti-enumeração: confirmação byte-a-byte.
- Se era visual: confirmação de não-modificação CSS.
- Se era C10/backend: confirmação de não-toque.
- Se era legacy: confirmação de funcionamento.
- Se era a11y: confirmação axe-core + navegação por teclado.

### 7.3 Auto-crítica obrigatória (§6.3 do prompt)

Lista de perguntas adversariais a responder com evidência no `fix-validation.md`:

- Algum teste foi feito sob medida para passar?
- Alguma correção mascarou sintoma sem resolver causa?
- Alguma assertion foi relaxada?
- A anti-enumeração foi validada com comparação byte-a-byte (UI + backend)?
- Algum arquivo CSS/SCSS foi tocado?
- Alguma mudança em JSX afetou aparência?
- A camada de serviço ou backend foi tocada?
- Provas legacy ainda funcionam?
- Acessibilidade foi declarada validada sem axe-core / navegação por teclado?
- As mensagens de erro estão centralizadas em arquivo de constantes (após AUD-003)?
- Validação client-side e máscara estão consistentes?

---

## 8. Plano de Atualização de Documentação

### 8.1 `CHANGELOG.md`

**Apêndice nova seção:** `v4.0 — Wave 3 — Componente 19 — Correcoes Pos-Auditoria Senior (2026-05-11)`. Conteúdo:

- **Corrigidos (3 MÉDIOS + 1 BAIXO + 1 BAIXO auto-resolvido):**
  - AUD-W3C19-003 — extracao de `MENSAGENS_C19` + `mensagemFinal` para `frontend/src/lib/c19-mensagens.ts` + 6 testes Vitest. Resolve AUD-W3C19-008 automaticamente.
  - AUD-W3C19-004 — `aria-invalid` adicionado ao `<input>` (mantido tambem no wrapper para CSS).
  - AUD-W3C19-002 — [Plano A: revert do `<strong>` no banner do ManualPanel] OU [Plano B: ADR-144 apendice + nota neste CHANGELOG explicando uniformizacao com CameraPanel pre-existente].
  - AUD-W3C19-006 — JSDoc em `aplicarMascara` documentando entrada nao-string.

- **Aceitos sem mudanca de codigo (3 BAIXOS):**
  - AUD-W3C19-005 / 031 — `useCodigoPrvInput` sem teste isolado (D9 ratificada).
  - AUD-W3C19-007 — auto-submit nao implementado (D6 ratificada).
  - AUD-W3C19-028 — `CODIGO_PUBLICO_REGEX` exportado + inline (decisao deliberada).

- **Deferred (1 ALTO):**
  - AUD-W3C19-001 — rate-limit backend `/scan` → sessao dedicada (`wave3-v4-rate-limit-scan` ou C20+). Bloqueante para PR em `main`.

- **Validacao numerica final:**
  - Vitest: 89 → 95 (+6 do `c19-mensagens.test.ts`).
  - tsc --noEmit: exit 0.
  - next build: 13/13.
  - Bundle `/escanear`: <verificar pos-execucao>.
  - Advisors: 2 security + 13 performance (idênticos ao pós-C19).

### 8.2 `DECISIONS.md`

**Apêndice ao ADR-145** (rate-limit follow-up): atualizar status para "DEFERRED — sessao dedicada `wave3-v4-rate-limit-scan` ou C20+".

**Apêndice ao ADR-144** (se Plano B for escolhido): registrar `<strong>` no ManualPanel como uniformizacao com CameraPanel pre-existente.

**ADR novo** (se aplicável — depende do Plano A vs B do AUD-002): considerar criar ADR-146 "Extração de mensagens C19 para módulo standalone" caso a refatoração do AUD-003 mude o contrato.

### 8.3 `CLAUDE.md`

**Atualização da seção "Notas do Componente 19":** linha sobre `MENSAGENS_C19` atualizada para apontar para `frontend/src/lib/c19-mensagens.ts` (era `page.tsx`).

**Atualização da árvore de pastas:** acrescentar `c19-mensagens.ts` em `frontend/src/lib/`.

### 8.4 `docs/wave3-v4-c19/audit-report.md`

**Apêndice de Status por Achado** (não editar corpo original). Tabela com 1 linha por ID listando:

- ID
- Status final (RESOLVIDO / DEFERRED / ACEITO / REGISTRADO INFO / NÃO APLICÁVEL)
- Commit SHA (se RESOLVIDO)
- Encaminhamento (se DEFERRED)

### 8.5 `docs/wave3-v4-c19/fix-plan.md` (este arquivo)

**Apêndice "Resultado da Execução"** com diffs entre planejado e realizado. Adicionado no final do Gate 2.

### 8.6 `docs/wave3-v4-c10/contrato-c19.md`

**Atualização §3.5** "Customizando mensagens no C19" — se a correção do AUD-003 mudar o caminho de import. Apêndice de status final na §7.

### 8.7 Novo arquivo `docs/wave3-v4-c19/fix-validation.md`

Criado no fim do Gate 2 com checklist completo + verificação por achado + auto-crítica + recomendação final.

---

## 9. Entregável do Gate 1

Este arquivo `docs/wave3-v4-c19/fix-plan.md` commitado na branch `wave3-v4-c19/fixes/plan` (saindo de `wave3-v4-c19/audit` — ver §10 nota sobre divergência).

Mensagem do commit:
```
docs(wave3-v4/c19/fixes): plano de correção pós-auditoria
```

PARE APÓS O GATE 1. Reportar:
- Caminho do arquivo.
- Sumário ≤ 25 linhas (ver mensagem da próxima resposta).
- Pedido explícito de autorização: "Aguardando string AUTORIZADO GATE 2 — CORREÇÃO C19 v4.0 para prosseguir."

---

## 10. Notas sobre divergências e premissas

### 10.1 Divergência da premissa do prompt — branch base

O prompt original dizia "sai de `development`". Verificação realizada nesta sessão (§1 + git log) mostrou que **a branch `development` ainda não contém o C19 mergeado** — toda a entrega C19 + audit-report vivem em `wave3-v4-c19/audit` (commit `999e5b0`).

**Decisão tomada:** criar `wave3-v4-c19/fixes/plan` saindo de `wave3-v4-c19/audit`. Caso o Mario tenha mergeado o C19 em `development` desde a auditoria, basta rebase trivial; a sequência de commits permanece atômica e rastreável.

**Validação:** `git log --oneline wave3-v4-c19/fixes/plan -10` deve mostrar `f5e3271`, `f8f7492`, `6e42129`, `fcb3d48`, `3048e2e`, `999e5b0` como ancestrais. ✅

### 10.2 Premissa do prompt — Cloudflare

C19 não tocou Cloudflare R2. Nenhum achado da auditoria envolve R2. Não há ação Cloudflare nesta sessão de correção. Conformidade integral.

### 10.3 Premissa do prompt — preview programático

Esta sessão não rodará dev server programático (preview não tem auth de produção — mesma limitação do C10 e da auditoria). Smoke E2E permanece DEFERRED para Mario com `smoke-validation.md` 20 cenários.

### 10.4 Conformidade com o prompt

| Regra do prompt | Conformidade desta sessão |
|---|---|
| LAYOUT/VISUAL INTOCÁVEL | ✅ Plano A do AUD-002 = REVERTER (não adiciona visual); Plano B = só docs. AUD-004 = a11y não-visual. AUD-003 = refactor sem CSS. AUD-006 = JSDoc. |
| Camada de serviço e endpoint do C10 INTOCÁVEIS | ✅ AUD-001 DEFERRED. Demais não tocam. |
| Rastreabilidade (1 commit / 1 achado) | ✅ 6 commits funcionais + 1 docs acumulativo. |
| Reversibilidade | ✅ Cada commit pode ser revertido individualmente. |
| Sem desvio de escopo | ✅ Nenhum achado novo será introduzido. |
| Sem Framer Motion novo | ✅ Wave 6. |
| Sem expandir máquina de estados | ✅ C11. |
| Sem tocar timeline | ✅ C12. |
| PR aponta para `development` | ✅ |

---

## 11. Sumário Executivo Final

**Total acionável:** 13 achados (1 ALTO DEFERRED + 3 MÉDIOS corrigíveis + 5 BAIXOS distribuídos em corrigir/aceitar).
**Achados sem ação de código:** ~24 (INFOs registrados + 3 BAIXOS aceitos por D6/D9/decisão deliberada).
**Decisão pendente Mario:** Plano A vs B para AUD-W3C19-002 (`<strong>` no banner).
**Commits previstos:** 7 atômicos.
**Risco agregado:** BAIXO.
**Validação E2E:** DEFERRED (Mario executa via `smoke-validation.md`).

Aguardando `AUTORIZADO GATE 2 — CORREÇÃO C19 v4.0` (com preferência A ou B para AUD-002) para iniciar a execução.
