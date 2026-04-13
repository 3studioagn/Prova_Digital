# Wave 3 — Lote A — Closeout

**Escopo:** Componentes 10 e 11 do Backlog v3.0.
**Data:** 2026-04-10 (desenvolvimento) / 2026-04-13 (deploy + closeout final).
**Status:** ✅ COMPLETO — deploy em producao realizado e validado.

---

## 1. Checklist DoD — Componente 10 (Leitura de QR Code via Camera)

| # | Criterio (DoD global) | Status | Evidencia |
|---|---|---|---|
| 1 | Code review | ✅ | Revisado por Mario durante o desenvolvimento iterativo |
| 2 | Testes unitarios >= 80% cobertura | ✅ | `schemas/prova.py` 97%, `provas.py` 96% — 20 testes de scan |
| 3 | Testes de integracao passando | ✅ | 389 passed, 0 failed |
| 4 | Migrations aplicadas e versionadas | ✅ | RLS 006 versionada em `migrations/rls/` e aplicada via MCP |
| 5 | Validada contra criterios US-002 | ✅ | Ver secao 1.1 |
| 6 | Sem erros no console/logs | ✅ | `preview_console_logs`: vazio; `preview_logs`: vazio; deploy Railway OK |
| 7 | Documentacao atualizada | ✅ | CHANGELOG (7 entradas), DECISIONS (ADR-081 a 086), CLAUDE.md |
| 8 | Policies RLS versionadas | ✅ | `006_movimentacoes_insert_and_expand_select.sql` |

### 1.1 Criterios de aceitacao US-002

| # | Criterio | Status | Como foi atendido |
|---|---|---|---|
| 1 | Camera abre no sistema, sem app externo | ✅ | `html5-qrcode` abre via `getUserMedia` em `useScanner` hook |
| 2 | Sistema identifica vendedor logado ao escanear | ✅ | `get_current_user` resolve o usuario via JWT; `POST /scan` retorna `transicoes_permitidas` filtradas por setor/localizacao |
| 3 | Tela de assinatura e exibida apos leitura | ✅ | `AssinaturaModal` abre no estado `signing` apos usuario escolher transicao |
| 4 | Status muda para "Retirada pelo vendedor" com data/hora e nome | ✅ | `POST /{id}/transicoes` com `status_novo=RETIRADA_PELO_VENDEDOR` grava movimentacao com usuario_nome + created_at |

---

## 2. Checklist DoD — Componente 11 (Assinatura Digital e Transicao de Status)

| # | Criterio (DoD global) | Status | Evidencia |
|---|---|---|---|
| 1 | Code review | ✅ | Revisado por Mario durante o desenvolvimento iterativo |
| 2 | Testes unitarios >= 80% cobertura | ✅ | `state_machine.py` 100%, `provas.py` 96%, `schemas/prova.py` 97% |
| 3 | Testes de integracao passando | ✅ | 389 passed, 0 failed |
| 4 | Migrations aplicadas e versionadas | ✅ | N/A Alembic (alembic_version=009 inalterado), RLS 006 aplicada |
| 5 | Validada contra criterios US-003 a US-009 | ✅ | Ver secao 2.1 |
| 6 | Sem erros no console/logs | ✅ | Backend pytest verde, frontend tsc/lint/build limpos, deploy Railway OK |
| 7 | Documentacao atualizada | ✅ | 6 ADRs (081-086), 7 entradas CHANGELOG, CLAUDE.md atualizado |
| 8 | Policies RLS versionadas | ✅ | `006_movimentacoes_insert_and_expand_select.sql` |

### 2.1 Criterios de aceitacao US-003 a US-009

| HU | Criterio chave | Status | Teste(s) que cobrem |
|---|---|---|---|
| US-003 | Vendedor so aprova em RETIRADA; rota determinada por localizacao | ✅ | `test_transicao_happy_retirada_para_aprovada_matriz_persiste_rota_padrao`, `..._filial_persiste_rota_direta` |
| US-004 | Reprovacao com motivo obrigatorio | ✅ | `test_transicao_happy_reprovacao_com_motivo`, `test_transicao_reprovacao_sem_motivo_422` |
| US-005 | MATRIZ devolve a 3Studio (rota padrao) | ✅ | `test_transicao_happy_aprovada_matriz_para_de_volta_3studio`, `test_transicao_aprovada_filial_tentando_de_volta_422` |
| US-006 | FILIAL encaminha diretamente a clicheria (rota direta) | ✅ | `test_transicao_happy_aprovada_filial_para_encaminhada_clicheria`, `test_transicao_aprovada_matriz_tentando_encaminhada_422` |
| US-007 | 3Studio registra envio ao motorista | ✅ | `test_transicao_happy_de_volta_para_com_motorista_studio` |
| US-008 | Motorista confirma transporte | ✅ | `test_transicao_happy_com_motorista_para_enviada_motorista` |
| US-009 | Clicheria confirma recebimento (ambas rotas) | ✅ | `test_transicao_happy_enviada_para_recebida_clicheria`, `test_transicao_happy_encaminhada_para_recebida_clicheria` |

---

## 3. Cobertura de testes final

| Arquivo | Stmts | Miss | Cover | Notas |
|---|---|---|---|---|
| `app/services/state_machine.py` | 92 | 0 | **100%** | Sub-bloco A.1 |
| `app/api/v1/provas.py` | 430 | 17 | **96%** | 17 missing sao pre-Wave 2 |
| `app/domain/schemas/prova.py` | 134 | 4 | **97%** | 4 missing sao pre-Wave 2 |
| Frontend (tsc --noEmit) | — | — | **limpo** | Zero erros TS strict |
| Frontend (next lint) | — | — | **limpo** | Zero warnings ESLint |
| Frontend (next build) | — | — | **OK** | 1 warning pre-Wave 2 (autoprefixer) |

**Total de testes backend: 389** (era 308 pos-Sessao 22 → +81 novos).

| Sub-bloco | Testes adicionados |
|---|---|
| A.1 (state_machine) | +24 |
| A.2 (RLS 006) | 0 (infraestrutural) |
| A.3 (POST /scan) | +20 |
| A.4 (POST /transicoes) | +37 |
| **Total Lote A** | **+81** |

---

## 4. Arquivos criados

| Arquivo | Sub-bloco | Linhas |
|---|---|---|
| `backend/migrations/rls/006_movimentacoes_insert_and_expand_select.sql` | A.2 | 130 |
| `frontend/src/hooks/useScanner.ts` | A.5 | 152 |
| `frontend/src/hooks/useScanProva.ts` | A.5 | 94 |
| `frontend/src/hooks/useExecutarTransicao.ts` | A.5 | 115 |
| `frontend/src/app/(dashboard)/escanear/page.tsx` | A.5 | 463 |
| `frontend/src/app/(dashboard)/escanear/escanear.module.css` | A.5 | 376 |
| `WAVE3_LOTE_A_ANALYSIS.md` | Fase 3 | 1787 |
| `WAVE3_BLOCKERS.md` | A.1 | 108 |
| `WAVE3_LOTE_A_CLOSEOUT.md` | A.6 | este arquivo |
| `backend/Procfile` | Deploy | 1 |
| `backend/requirements.txt` | Deploy | 14 |

---

## 5. Arquivos modificados

| Arquivo | Sub-bloco(s) | O que mudou |
|---|---|---|
| `backend/app/services/state_machine.py` | A.1, A.4 | Stub removido, `executar_transicao` implementada (+150 linhas) + id/created_at no Python (+3 linhas) |
| `backend/app/api/v1/provas.py` | A.3, A.4 | `_carregar_prova_com_scoping` com `lock=True`, `POST /scan`, `POST /{id}/transicoes`, imports (+409 linhas) |
| `backend/app/domain/schemas/prova.py` | A.3, A.4 | `ScanRequest`, `ScanResponse`, `TransicaoRequest`, `TransicaoResponse`, constantes (+150 linhas) |
| `backend/pyproject.toml` | B-01, Deploy | `extend-exclude = ["migrations"]` + `[tool.setuptools.packages.find]` (+9 linhas) |
| `backend/tests/test_state_machine.py` | A.1 | Stub test removido, 24 testes novos de `executar_transicao` + helper `make_prova` (+467 linhas) |
| `backend/tests/test_provas_api.py` | A.3, A.4 | 57 testes novos (scan + transicao) + helpers `_make_prova_com_hash`, `_transicao_body` (+1080 linhas) |
| `frontend/package.json` | A.5 | +3 dependencias |
| `frontend/src/lib/types/prova.ts` | A.5 | +66 linhas (tipos Scan/Transicao + constante max bytes) |
| `frontend/src/app/(dashboard)/layout.tsx` | A.5 | **1 linha**: `href: "/escanear"` no item do menu |
| `docs/db/schema.sql` | A.2 | Header + secao RLS atualizada (11→12 policies) |
| `CLAUDE.md` | A.6, Deploy | Tabela waves, rotas 24→26, paginas 7→8, estrutura pastas, menu, secao Deploy em producao |
| `DECISIONS.md` | A.1-A.5, Deploy | ADR-081, 082, 083, 084, 085, 086 |
| `CHANGELOG.md` | A.1-A.6, Deploy | 7 entradas incrementais |
| `WAVE3_BLOCKERS.md` | A.1, A.5 | B-01 (ruff, resolvido), B-02 (next@14.2 audit, aceito Wave 6) |

---

## 6. Evidencias de integracao com Waves anteriores

| Aspecto | Impacto | Evidencia |
|---|---|---|
| Schema Alembic | **0 alteracoes** | `alembic_version` permanece `009` |
| Endpoints Wave 2 | **0 alteracoes** | Os 8 endpoints de `/provas` + 3 de `/configuracoes` permanecem intactos |
| Layout dashboard | **1 linha** | Apenas `href: "/escanear"` adicionado ao item ja existente no menu |
| Hooks Wave 2 | **0 alteracoes** | `useCreateProva`, `useListProvas`, `useProvaDetail`, `useConfiguracoes`, `useInactivityTimeout` intocados |
| Paginas Wave 1/2 | **0 alteracoes** | `/login`, `/usuarios`, `/nova-prova`, `/provas`, `/provas/[id]`, `/configuracoes` intocadas |
| RLS Wave 2 | **1 policy expandida** | `pol_movimentacoes_select` expandida para cobrir MOTORISTA/CLICHERIA (F03 da Sessao 22 — debito aceito) |
| CSS global | **0 alteracoes** | `globals.css` intocado; todos os estilos novos sao CSS Modules |

---

## 7. Contratos expostos para Lotes B e C

| Contrato | Para quem |
|---|---|
| `executar_transicao(db, *, prova, status_novo, usuario, assinatura_digital, motivo_reprovacao, motivo_cancelamento=None, request=None) -> Movimentacao` | C13 (cancelamento) e C14 (reinicio) via endpoints admin dedicados |
| Rejeicao explicita de `CANCELADA` e `CRIADA` em `TransicaoRequest` | C13 e C14 criarao seus proprios endpoints sem conflito |
| Suporte a `REPROVADA_PELO_VENDEDOR -> CRIADA` com incremento de `ciclo_atual` + reset de `rota` | C14 — gancho mecanico pronto |
| `provas_digitais.motivo_cancelamento` populado quando `status_novo == CANCELADA` | C13 — campo ja existe no schema |
| `MovimentacaoResponse` com todos os campos para timeline | C12 — endpoint `GET /movimentacoes` retorna dados reais |
| `provas_digitais.rota` populada na `APROVADA_PELO_VENDEDOR` | C12 + Wave 4 dashboard |
| `audit_log.acao = "transitar_status" / "reiniciar_ciclo"` com `detalhes_json` estruturado | Wave 6 tela de auditoria |

---

## 8. Riscos residuais para Lote B (C12 — Timeline Visual)

- Framer Motion ainda nao instalado — C12 vai precisar adicionar.
- O endpoint `GET /provas/{id}/movimentacoes` ja retorna dados reais apos o Lote A — C12 apenas substitui o placeholder JSX pelo componente visual.
- Nenhuma mudanca de contrato de API necessaria — `MovimentacaoResponse` e `MovimentacaoListResponse` estao estaveis desde a Wave 2.

---

## 9. Riscos residuais para Lote C (C13 Cancelamento + C14 Reinicio)

- **C13** precisa decidir entre endpoint unificado (`POST /{id}/transicoes` aceitando `CANCELADA`) ou dedicado (`POST /{id}/cancelar`). Recomendacao do plano: dedicado (acao admin sem scan/assinatura).
- **C14** precisa definir endpoint admin (`POST /{id}/reiniciar-ciclo`) e se exige motivo.
- O `executar_transicao` ja suporta ambas as transicoes mecanicamente — os endpoints dedicados precisam apenas orquestrar `FOR UPDATE + executar_transicao + commit` no mesmo padrao do handler do A.4.

---

## 10. Debitos pre-existentes observados (nao-regressao do Lote A)

| # | Debito | Origem | Acao |
|---|---|---|---|
| B-01 | `ruff check .` reportava 6 erros em `migrations/` | Wave 0/1 | ✅ Resolvido: `extend-exclude = ["migrations"]` no `pyproject.toml` |
| B-02 | `npm audit` 4 high em `next@14.2` (DoS, smuggling) | Wave 1 | Aceito como TODO Wave 6 (upgrade para Next 16 = breaking) |
| F03 | `pol_movimentacoes_select` sem MOTORISTA/CLICHERIA | Wave 2 (Sessao 22) | ✅ Resolvido no sub-bloco A.2 (RLS 006) |

---

## 11. Metricas consolidadas

| | Sessao 22 (pos-Wave 2) | Lote A (pos-A.6) | Delta |
|---|---|---|---|
| **Testes backend** | 308 | **389** | +81 |
| **Cobertura `state_machine.py`** | n/d (stub) | **100%** | — |
| **Cobertura `provas.py`** | 95% | **96%** | +1pp |
| **Cobertura `schemas/prova.py`** | 100% | **97%** | -3pp (novos schemas adicionam stmts; 4 missing sao pre-Wave 2) |
| **Rotas backend** | 24 | **26** | +2 |
| **Rotas frontend** | 7 | **8** | +1 |
| **Policies RLS** | 11 | **12** | +1 |
| **alembic_version** | 009 | **009** | 0 |
| **Deps npm (prod)** | 7 | **10** | +3 |
| **ADRs** | 080 | **086** | +6 |
| **Bundle `/escanear`** | — | **11.4 kB / 161 kB FL JS** | novo |
| **Ruff backend** | limpo | **limpo** | — |
| **tsc --noEmit** | limpo | **limpo** | — |
| **next lint** | limpo | **limpo** | — |
| **next build** | limpo* | **limpo*** | *mesmo warning pre-Wave 2 |

---

## 12. Deploy em producao

Deploy realizado em 2026-04-13. Detalhes completos no ADR-086.

**URLs de producao:**
- Backend: `https://provadigital-production.up.railway.app`
- Frontend: `https://prova-digital-five.vercel.app`
- Health check: `https://provadigital-production.up.railway.app/health`

**Validacoes de deploy:**
- Backend Railway sobe e responde `{"detail":"Not Found"}` na raiz ✅
- Health check `/health` acessivel ✅
- Frontend Vercel builda e serve a pagina de login ✅
- CORS configurado via `FRONTEND_URL` no Railway ✅
- Redeploy automatico via push no GitHub ✅

**Problemas resolvidos durante o deploy (4):**
1. Setuptools flat-layout error (`app` + `migrations` como dois pacotes).
   Fix: `[tool.setuptools.packages.find] include = ["app*"]`.
2. `uvicorn: command not found` no Railway.
   Fix: `python -m uvicorn` em vez de `uvicorn` direto.
3. `No module named uvicorn` — `pip install -e .` nao instalava deps no
   runtime do Railway.
   Fix: `requirements.txt` explicito (Railway nixpacks detecta automaticamente).
4. CORS bloqueado — `NEXT_PUBLIC_API_URL` apontava para `localhost` em vez
   da URL do Railway; e URL com barra no final gerava dupla `//`.
   Fix: variavel corrigida na Vercel sem barra final.

---

## 13. Smoke E2E

**Validacoes pre-deploy (sessao de desenvolvimento 2026-04-10):**
- Dev server sobe sem erros: `preview_start frontend` ✅
- `/escanear` rota acessivel (compila, middleware redireciona corretamente) ✅
- Zero erros no console do browser ✅
- Zero erros no servidor ✅
- Backend 389 testes passing ✅
- `ruff check .` limpo ✅
- `tsc --noEmit` limpo ✅
- `next lint` limpo ✅
- `next build` OK (11.4 kB bundle) ✅

**Validacoes pos-deploy (2026-04-13):**
- Backend Railway sobe na porta 8080 e responde OK ✅
- Frontend Vercel builda e serve paginas corretamente ✅
- Login funciona via Supabase Auth ✅
- CORS entre Vercel → Railway configurado e funcionando ✅

**Smoke E2E com camera real (pendente):**
Os 10 cenarios com camera real + usuarios de teste (Vendedor MATRIZ, Motorista,
Clicheria) serao executados pelo Mario diretamente no celular, agora que o
deploy esta no ar. Os usuarios de teste precisam ser cadastrados previamente
via `POST /api/v1/users/` (ver §9.3 P1 do `WAVE3_LOTE_A_ANALYSIS.md`).

---

## 14. Proximo passo — Lote B

O Lote B (Componente 12 — Timeline Visual) so sera iniciado apos o **"GO
LOTE B"** explicito do Mario. Ate la, nenhuma analise, planejamento ou codigo
do C12 sera produzido. Ver secao 8 acima para riscos residuais.

Os Componentes 13 (Cancelamento) e 14 (Reinicio de Ciclo) ficam para o
Lote C, apos o Lote B.
