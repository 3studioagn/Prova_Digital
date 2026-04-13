# Wave 3 — Lote C — Closeout

**Escopo:** Componente 13 (Cancelamento) + Componente 14 (Reinicio de Ciclo).
**Data:** 2026-04-13.
**Status:** COMPLETO — aguardando aprovacao final.

---

## 1. Checklist DoD — Componente 13 (Cancelamento de Prova Digital)

| # | Criterio (DoD global) | Status | Evidencia |
|---|---|---|---|
| 1 | Code review | Aguardando | Revisao pelo Mario |
| 2 | Testes unitarios >= 80% cobertura | OK | 10 testes novos cobrindo happy + error paths |
| 3 | Testes de integracao passando | OK | 407 passed, 0 failed |
| 4 | Migrations aplicadas e versionadas | N/A | Zero migrations |
| 5 | Validada contra criterios RF-010 + RN-005 | OK | Ver secao 2 |
| 6 | Sem erros no console/logs | OK | Build limpo, zero erros |
| 7 | Documentacao atualizada | OK | CHANGELOG, ADR-088, CLAUDE.md |
| 8 | Policies RLS versionadas | N/A | Zero mudancas RLS |

### Criterios RF-010 + RN-005

| # | Criterio | Implementacao |
|---|---|---|
| 1 | Motivo obrigatorio | `CancelarRequest.motivo_cancelamento` com `min_length=1` + strip validator |
| 2 | Apenas admin | `get_admin_user` dependency no endpoint |
| 3 | De qualquer estado ativo | `pode_cancelar(status)` validacao previa + `executar_transicao` |
| 4 | Pos-cancelamento irreversivel | `TRANSICOES[CANCELADA] = set()` — terminal |
| 5 | Historico preservado | Movimentacao imutavel; timeline renderiza CANCELADA |
| 6 | Motivo exibido | `prova.motivo_cancelamento` ja renderizado em page.tsx (Wave 2) |

---

## 2. Checklist DoD — Componente 14 (Reinicio de Ciclo)

| # | Criterio (DoD global) | Status | Evidencia |
|---|---|---|---|
| 1 | Code review | Aguardando | Revisao pelo Mario |
| 2 | Testes unitarios >= 80% cobertura | OK | 8 testes novos |
| 3 | Testes de integracao passando | OK | 407 passed, 0 failed |
| 4 | Migrations aplicadas e versionadas | N/A | Zero migrations |
| 5 | Validada contra criterios US-010 + RF-008 + RN-006 | OK | Ver abaixo |
| 6 | Sem erros no console/logs | OK | Build limpo |
| 7 | Documentacao atualizada | OK | CHANGELOG, ADR-088, CLAUDE.md |
| 8 | Policies RLS versionadas | N/A | Zero mudancas RLS |

### Criterios US-010

| # | Criterio | Implementacao |
|---|---|---|
| 1 | So reinicia REPROVADA | Validacao previa no endpoint + `validar_transicao` no state_machine |
| 2 | Status retorna a CRIADA | `executar_transicao(status_novo=CRIADA)` |
| 3 | `ciclo_atual` incrementa | `executar_transicao` faz `ciclo_atual + 1` (ADR-081) |
| 4 | Historico preservado | Movimentacao imutavel; timeline agrupa por ciclo (C12) |

---

## 3. Cobertura de testes

| Aspecto | Resultado |
|---|---|
| Backend `pytest` | **407 passed**, 1 warning pre-existente |
| Testes novos C13 | 10 (3 happy + 2 validacao motivo + 2 terminal/cancelada + 1 403 + 1 404 + 1 502) |
| Testes novos C14 | 8 (2 happy + 3 rejeicao estado + 1 403 + 1 404 + 1 502) |
| `ruff check` | Limpo |
| `tsc --noEmit` | Limpo |
| `next lint` | 0 warnings |
| `next build` | OK |

### Bundle size

| Pagina | Size | First Load JS |
|---|---|---|
| `/provas/[id]` | 47.2 kB | 206 kB |

Delta vs Lote B: +1.2 kB (AdminActions + 3 hooks). Desprezivel.

---

## 4. Arquivos criados

| Arquivo | Descricao |
|---|---|
| `frontend/src/hooks/useCurrentUser.ts` | Hook GET /users/me para detectar admin |
| `frontend/src/hooks/useCancelarProva.ts` | Hook POST /cancelar |
| `frontend/src/hooks/useReiniciarCiclo.ts` | Hook POST /reiniciar-ciclo |
| `frontend/src/app/(dashboard)/provas/[id]/AdminActions.tsx` | Botoes + modais |
| `WAVE3_LOTE_C_ANALYSIS.md` | Plano do Lote C |
| `WAVE3_LOTE_C_CLOSEOUT.md` | Este arquivo |

---

## 5. Arquivos modificados

| Arquivo | O que mudou |
|---|---|
| `backend/app/api/v1/provas.py` | +2 endpoints (`cancelar_prova`, `reiniciar_ciclo_prova`), +helper `_assinatura_administrativa`, +import `CancelarRequest`, +import `pode_cancelar` |
| `backend/app/domain/schemas/prova.py` | +`CancelarRequest` schema (21 linhas) |
| `backend/tests/test_provas_api.py` | +18 testes (~250 linhas) |
| `frontend/src/app/(dashboard)/provas/[id]/page.tsx` | +import `AdminActions` + 1 linha JSX |
| `frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css` | +estilos admin (~100 linhas: secao, botao danger, modal) |
| `CHANGELOG.md` | Entrada Lote C |
| `DECISIONS.md` | ADR-088 (4 decisoes) |
| `CLAUDE.md` | Wave 3 "COMPLETA", rotas 26→28, estrutura pastas |

---

## 6. Evidencias de integracao com Lotes A/B e Waves anteriores

| Aspecto | Impacto | Evidencia |
|---|---|---|
| `executar_transicao` (Lote A) | **0 alteracoes** | Chamada pelos novos endpoints, nao modificada |
| `TransicaoRequest` (Lote A) | **0 alteracoes** | Continua rejeitando CANCELADA/CRIADA no endpoint generico |
| `<Timeline>` (Lote B, C12) | **0 alteracoes** | Ja renderiza CANCELADA + ciclos multiplos |
| Schema Alembic | **0 alteracoes** | `alembic_version` = 009 |
| RLS | **0 alteracoes** | 12 policies intactas |
| Endpoints Wave 2+3 | **0 alteracoes** | 26 endpoints anteriores intactos |
| Layout dashboard | **0 alteracoes** | Nao tocado |
| Hooks Wave 2/3 | **0 alteracoes** | Todos intocados |

---

## 7. Contratos expostos para Waves futuras

| Contrato | Para quem |
|---|---|
| `POST /cancelar` endpoint | Wave 4 (dashboard pode ter botao de cancelamento rapido) |
| `POST /reiniciar-ciclo` endpoint | Wave 4 (idem) |
| `useCurrentUser` hook | Qualquer pagina que precise condicionar UI por perfil |
| `useCancelarProva` / `useReiniciarCiclo` hooks | Reutilizaveis em outras paginas |

---

## 8. Riscos residuais

| # | Item |
|---|---|
| 1 | **Verificacao visual com dados reais** requer autenticacao em producao |
| 2 | **Assinatura sintetica** e um marcador, nao assinatura visual — documentado no ADR-088 |
| 3 | **B-02 permanece**: npm audit 4 high em next@14.2 — TODO Wave 6 |
| 4 | **`useCurrentUser` duplica request do layout** — desprezivel, documentado no ADR-088 |

---

## 9. Metricas consolidadas — Wave 3 completa

| Aspecto | Pos-Wave 2 | Pos-Lote A | Pos-Lote B | Pos-Lote C | Delta total |
|---|---|---|---|---|---|
| **Testes backend** | 308 | 389 | 389 | **407** | **+99** |
| **Rotas backend** | 24 | 26 | 26 | **28** | **+4** |
| **Rotas frontend** | 7 | 8 | 8 | **8** | +1 |
| **Policies RLS** | 11 | 12 | 12 | **12** | +1 |
| **alembic_version** | 009 | 009 | 009 | **009** | 0 |
| **Deps npm (prod)** | 7 | 10 | 11 | **11** | +4 |
| **ADRs** | 080 | 086 | 087 | **088** | +8 |
| **Bundle `/provas/[id]`** | ~11 kB | ~11 kB | 46 kB | **47.2 kB** | +36 kB |

---

## 10. Wave 3 — Fechamento completo

Com o Lote C, a **Wave 3 esta COMPLETA**:

| Lote | Componentes | Status |
|---|---|---|
| Lote A | C10 (QR Scanner) + C11 (Assinatura + Transicao) | COMPLETO |
| Lote B | C12 (Timeline Visual) | COMPLETO |
| Lote C | C13 (Cancelamento) + C14 (Reinicio de Ciclo) | COMPLETO |

Proxima Wave: **Wave 4 — Dashboard + Atrasos** (quando o Mario autorizar).
