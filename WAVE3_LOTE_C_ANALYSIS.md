# Wave 3 — Lote C — Analysis (Componentes 13 e 14)

**Escopo:** Componente 13 (Cancelamento) + Componente 14 (Reinicio de Ciclo).
**Data:** 2026-04-13.
**Status:** Aguardando GO implementacao.

---

## 1. Escopo exato dos Componentes 13 e 14

### Componente 13 — Cancelamento de Prova Digital

**Backlog v3.0:** Motivo obrigatorio. Imutabilidade pos-cancelamento (RN-005). Must Have. Depende de C06, C05.

**RF-010:** O sistema deve permitir o cancelamento de uma prova digital, registrando
obrigatoriamente o motivo, o usuario responsavel e a data/hora.

**RN-005:** Provas canceladas nao podem ter seu status reativado. Um novo registro deve
ser criado caso necessario. O historico do registro cancelado permanece acessivel.

**Criterios de aceitacao (derivados de RF-010 + RN-005):**

| # | Criterio | Como sera atendido |
|---|---|---|
| 1 | Cancelamento exige motivo obrigatorio | `CancelarRequest.motivo_cancelamento: str` com `min_length=1` |
| 2 | Apenas perfil 3Studio (admin) pode cancelar | Endpoint usa `get_admin_user` dependency |
| 3 | Cancelamento possivel de qualquer estado ativo | `pode_cancelar(status)` do state_machine ja implementa isso |
| 4 | Apos cancelamento, nenhuma transicao possivel | `TRANSICOES[CANCELADA] = set()` — estado terminal |
| 5 | Historico preservado e acessivel | Movimentacao imutavel gravada; timeline (C12) ja renderiza CANCELADA |
| 6 | Motivo exibido no detalhe da prova | `prova.motivo_cancelamento` ja renderizado em page.tsx |

### Componente 14 — Reinicio de Ciclo (Reprovacao)

**Backlog v3.0:** Acao administrativa 3Studio. Retorna status a "Criada". Preserva
historico completo no audit log. Must Have. Depende de C11, C06.

**RF-008:** Apos a reprovacao, a prova retorna a 3Studio com status "Reprovada pelo
Vendedor". O perfil 3Studio pode entao reiniciar o ciclo, retornando o status a
"Criada" e preservando o historico completo.

**RN-006:** Provas reprovadas podem ter seu ciclo reiniciado exclusivamente pelo perfil
3Studio. O reinicio retorna o status a "Criada" e incrementa o numero do ciclo.

**US-010:** Como usuario da 3Studio, eu quero reiniciar o ciclo de uma prova reprovada
para que ela volte ao fluxo apos correcao.

| # | Criterio (US-010) | Como sera atendido |
|---|---|---|
| 1 | So reinicia provas em REPROVADA_PELO_VENDEDOR | `validar_transicao` rejeita destino CRIADA de outros estados |
| 2 | Status retorna a CRIADA | `executar_transicao` ja implementa |
| 3 | `ciclo_atual` incrementa | `executar_transicao` ja faz `ciclo_atual + 1` |
| 4 | Historico do ciclo anterior preservado | Movimentacoes imutaveis; timeline (C12) agrupa por ciclo |

### Definition of Done (global)

| # | Criterio | Aplicabilidade |
|---|---|---|
| 1 | Code review | Revisao pelo Mario |
| 2 | Testes unitarios >= 80% | Novos testes para endpoints C13/C14 |
| 3 | Testes de integracao passando | 389 existentes + novos |
| 4 | Migrations aplicadas e versionadas | N/A — zero migrations |
| 5 | Validada contra criterios | RF-010, RN-005, US-010, RF-008, RN-006 |
| 6 | Sem erros no console/logs | Validado via preview tools |
| 7 | Documentacao atualizada | CHANGELOG, DECISIONS, CLAUDE.md |
| 8 | Policies RLS versionadas | N/A — zero mudancas RLS |

---

## 2. Interface com Lotes A e B — consumido sem modificacao

| Contrato | Origem | Consumo |
|---|---|---|
| `executar_transicao(db, *, prova, status_novo, usuario, assinatura_digital, motivo_cancelamento=None, request=None)` | Lote A (ADR-081) | Chamado pelos endpoints de cancelar e reiniciar. **Nao modificado** |
| `pode_cancelar(status)` | Lote A | Usado internamente por `executar_transicao`. **Nao modificado** |
| `_carregar_prova_com_scoping(db, prova_id, user, lock=True)` | Lote A | Pattern reutilizado nos novos endpoints. **Nao modificado** |
| `_build_prova_response(prova, vendedor_nome, loc, setor)` | Wave 2/Lote A | Helper reutilizado para montar response. **Nao modificado** |
| `TransicaoInvalidaError`, `AtorNaoAutorizadoError` | Lote A | Exceptions de dominio traduzidas para HTTP nos novos handlers |
| `<Timeline>` (C12, Lote B) | Lote B | Ja renderiza CANCELADA (cinza) e ciclos multiplos. **Nao modificado** |
| `ProvaResponse.motivo_cancelamento` | Wave 2 | Ja exibido no detalhe (page.tsx:189-195). **Nao modificado** |
| `useProvaDetail.reload()` | Wave 2 | Chamado apos cancelar/reiniciar para atualizar a UI |
| `MovimentacaoResponse` | Wave 2 | Tipo do response dos novos endpoints |

**Compromisso:** nenhum contrato existente sera alterado. Os novos endpoints sao ADITIVOS.

---

## 3. Interface com Waves 0/1/2

| Recurso | Wave | Consumo |
|---|---|---|
| `get_admin_user` dependency | Wave 1 | Protege ambos os endpoints (admin-only) |
| `get_current_user` dependency | Wave 1 | Usado no frontend para detectar admin |
| `GET /api/v1/users/me` | Wave 1 | Frontend busca `is_admin` para condicionar botoes |
| Layout `UserInfo { nome, setor, is_admin }` | Wave 1 | Layout ja busca user info; detail page precisa de hook proprio |
| `globals.css` custom properties | Wave 1 | Design tokens para botoes/modais |
| CSS Modules pattern | Wave 1 | Seguido |
| `apiFetch` wrapper | Wave 2 | Usado pelos hooks do frontend |
| `detalhe.module.css` | Wave 2/Lote B | Estilos de botao e modal reutilizados |

---

## 4. Contratos a expor para Waves futuras

| Contrato | Para quem | Descricao |
|---|---|---|
| `POST /api/v1/provas/{id}/cancelar` | Wave 6 (auditoria) | Endpoint registrado no audit_log com acao "transitar_status" |
| `POST /api/v1/provas/{id}/reiniciar-ciclo` | Wave 6 (auditoria) | Endpoint registrado com acao "reiniciar_ciclo" |
| `useCurrentUser` hook | Qualquer pagina futura que precise saber se o user e admin | Hook reutilizavel |

---

## 5. Modelo de dados

**Nenhuma alteracao no banco de dados.**

- Zero tabelas, colunas, migrations, indexes ou RLS.
- `alembic_version` permanece `009`.
- Os campos ja existem: `provas_digitais.motivo_cancelamento`, `movimentacoes.motivo_reprovacao`.
- A coluna `movimentacoes.assinatura_digital BYTEA NOT NULL` permanece inalterada.

### Decisao: assinatura para acoes administrativas

`executar_transicao` exige `assinatura_digital` nao-vazia (RN-003). Cancelamento e reinicio
sao acoes administrativas **sem scan QR e sem canvas de assinatura** (recomendacao §9 do
closeout Lote A).

**Abordagem escolhida:** os endpoints geram uma assinatura sintetica:

```python
assinatura = f"ACAO_ADMINISTRATIVA:{acao}:{usuario.nome}".encode("utf-8")
```

Razoes:
1. **Nao modifica `executar_transicao`** — contrato Lote A preservado.
2. **Nao requer migration** — coluna continua NOT NULL, bytes nao-vazios satisfazem a validacao.
3. **Semanticamente correto** — a movimentacao registra que foi uma acao administrativa, nao
   uma assinatura visual. O campo `assinatura_digital` nesse contexto funciona como marcador
   da natureza da acao.
4. **Auditavel** — `audit_log.detalhes_json` ja registra o usuario e a acao.

---

## 6. Contratos de API

### 6.1 POST /api/v1/provas/{id}/cancelar (C13)

| Aspecto | Valor |
|---|---|
| Metodo | POST |
| Path | `/api/v1/provas/{id}/cancelar` |
| Auth | `get_admin_user` (is_admin=true) |
| Request body | `CancelarRequest { motivo_cancelamento: str (min 1, max 500) }` |
| Response 200 | `TransicaoResponse { prova: ProvaResponse, movimentacao: MovimentacaoResponse }` |
| 401 | Token ausente/invalido |
| 403 | Usuario nao admin |
| 404 | Prova nao encontrada ou fora do scoping |
| 409 | Status mudou (race — prova ja cancelada ou terminal) |
| 422 | Motivo vazio, prova em estado terminal |
| 502 | Falha de DB |

**Fluxo interno:**
1. `get_admin_user` valida admin.
2. `_carregar_prova_com_scoping(db, id, user, lock=True)` carrega com FOR UPDATE.
3. Gera assinatura sintetica.
4. `executar_transicao(db, prova=prova, status_novo=CANCELADA, usuario=user, assinatura_digital=sig, motivo_cancelamento=body.motivo_cancelamento, request=request)`.
5. `db.commit()`.
6. Retorna `TransicaoResponse`.

### 6.2 POST /api/v1/provas/{id}/reiniciar-ciclo (C14)

| Aspecto | Valor |
|---|---|
| Metodo | POST |
| Path | `/api/v1/provas/{id}/reiniciar-ciclo` |
| Auth | `get_admin_user` (is_admin=true) |
| Request body | Nenhum (a acao nao exige input alem da confirmacao) |
| Response 200 | `TransicaoResponse { prova: ProvaResponse, movimentacao: MovimentacaoResponse }` |
| 401 | Token ausente/invalido |
| 403 | Usuario nao admin |
| 404 | Prova nao encontrada |
| 409 | Status mudou (race — prova nao mais em REPROVADA) |
| 422 | Prova nao esta em REPROVADA_PELO_VENDEDOR |
| 502 | Falha de DB |

**Fluxo interno:**
1. `get_admin_user` valida admin.
2. `_carregar_prova_com_scoping(db, id, user, lock=True)`.
3. Gera assinatura sintetica.
4. `executar_transicao(db, prova=prova, status_novo=CRIADA, usuario=user, assinatura_digital=sig, request=request)`.
5. `db.commit()`.
6. Retorna `TransicaoResponse`.

---

## 7. Impacto no frontend

### 7.1 Nova dependencia

Nenhuma. Tudo usa libs ja instaladas (React, apiFetch, CSS Modules).

### 7.2 Arquivos novos

| Arquivo | Descricao |
|---|---|
| `frontend/src/hooks/useCurrentUser.ts` | Hook que chama `GET /api/v1/users/me` e retorna `{ user, loading }`. Usado para condicionar botoes admin |
| `frontend/src/hooks/useCancelarProva.ts` | Hook wrapper para `POST /{id}/cancelar` |
| `frontend/src/hooks/useReiniciarCiclo.ts` | Hook wrapper para `POST /{id}/reiniciar-ciclo` |
| `frontend/src/app/(dashboard)/provas/[id]/AdminActions.tsx` | Componente com botoes + modais de cancelar e reiniciar |

### 7.3 Arquivos modificados

| Arquivo | Alteracao |
|---|---|
| `frontend/src/app/(dashboard)/provas/[id]/page.tsx` | Import `AdminActions` + renderizar dentro do card branco, abaixo dos botoes de etiqueta, condicionado a `prova` existir |
| `frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css` | Adicionar estilos para botoes admin (danger) e modais de confirmacao |
| `backend/app/api/v1/provas.py` | +2 endpoints (`cancelar_prova`, `reiniciar_ciclo_prova`) + imports |
| `backend/app/domain/schemas/prova.py` | +1 schema: `CancelarRequest` |
| `backend/tests/test_provas_api.py` | +N testes para C13 e C14 |

### 7.4 Design do frontend

**Botoes na pagina de detalhe:**

```
┌──────────────────────────────────────┐
│  Metadata da prova ...               │
│                                      │
│  [Visualizar etiqueta] [Baixar]      │
│                                      │
│  ── Acoes administrativas ────────── │  ← so visivel para admin
│  [Reiniciar ciclo]  [Cancelar prova] │
│   (amarelo, só se    (vermelho, só   │
│    REPROVADA)         se ativa)      │
└──────────────────────────────────────┘
```

**Modal de cancelamento:**
- Titulo: "Cancelar prova — {nro_requerimento}"
- Textarea: "Motivo do cancelamento" (obrigatorio)
- Botoes: [Voltar] [Confirmar cancelamento] (vermelho)

**Modal de reinicio:**
- Titulo: "Reiniciar ciclo — {nro_requerimento}"
- Texto: "A prova voltara ao status Criada (ciclo {N+1}). O historico sera preservado."
- Botoes: [Voltar] [Confirmar reinicio]

**Apos confirmacao:** `reload()` do `useProvaDetail` para atualizar dados + timeline.

### 7.5 Deteccao de admin no frontend

O layout (`layout.tsx:98-114`) ja busca `GET /api/v1/users/me` e tem `UserInfo { is_admin }`,
mas **nao compartilha** com child pages (nao ha React Context). Opcoes:

**(A)** Criar `useCurrentUser` hook — novo fetch `GET /users/me` na detail page.
Duplica a chamada do layout, mas e leve (<1 KB response, cacheavel pelo browser).

**(B)** Criar React Context no layout e prover `user` para children.
Requer modificacao do layout.tsx (Wave 1).

**Escolha: (A)** — hook dedicado. Nao toca no layout, nao toca em Wave 1.

---

## 8. Storage R2

**Nao aplicavel.** Cancelamento e reinicio nao interagem com R2.

---

## 9. Plano de testes

### 9.1 Camada 1 — Unitarios backend

**C13 — Cancelamento:**

| Teste | Status HTTP | Descricao |
|---|---|---|
| Happy: cancelar prova CRIADA | 200 | Motivo gravado, status=CANCELADA |
| Happy: cancelar prova RETIRADA | 200 | De qualquer estado ativo |
| Happy: cancelar prova APROVADA | 200 | Idem |
| Rejeita: motivo vazio | 422 | Pydantic min_length=1 |
| Rejeita: prova ja CANCELADA | 409 | `pode_cancelar()` retorna False |
| Rejeita: prova RECEBIDA (terminal) | 409 | Idem |
| Rejeita: usuario nao admin | 403 | `get_admin_user` |
| Rejeita: prova inexistente | 404 | Scoping |
| DB error | 502 | Exception no commit |

**C14 — Reinicio:**

| Teste | Status HTTP | Descricao |
|---|---|---|
| Happy: reiniciar REPROVADA | 200 | Status=CRIADA, ciclo_atual+1, rota=None |
| Rejeita: prova CRIADA (nao reprovada) | 409 | Transicao invalida |
| Rejeita: prova APROVADA | 409 | Idem |
| Rejeita: prova CANCELADA | 409 | Terminal |
| Rejeita: usuario nao admin | 403 | `get_admin_user` |
| Rejeita: prova inexistente | 404 | Scoping |
| DB error | 502 | Exception no commit |

**Estimativa: ~16 testes novos.**

### 9.2 Camada 2 — Integracao

389 testes existentes devem continuar passando (regressao zero).

### 9.3 Camada 3 — Visual/E2E

| Cenario | Verificacao |
|---|---|
| Admin ve botoes, nao-admin nao ve | `preview_snapshot` com e sem admin |
| Botao "Cancelar" abre modal | `preview_click` + `preview_snapshot` |
| Modal rejeita submit sem motivo | Validacao client-side |
| Cancelamento bem-sucedido atualiza pagina | `preview_snapshot` apos submit |
| Botao "Reiniciar" so visivel em REPROVADA | `preview_snapshot` |
| Reinicio atualiza ciclo na timeline | `preview_snapshot` apos submit |
| TypeScript, ESLint, build limpos | CI tools |

---

## 10. Riscos e pontos de atencao

| # | Risco | Prob. | Impacto | Mitigacao |
|---|---|---|---|---|
| R1 | Assinatura sintetica pode confundir analise de audit futura | Baixa | Baixo | `audit_log.detalhes_json` ja distingue "transitar_status" de "reiniciar_ciclo" |
| R2 | `useCurrentUser` duplica request do layout | Baixa | Nulo | Response <1 KB; browser pode cachear; custo desprezivel |
| R3 | Race condition no cancelamento (2 admins cancelando ao mesmo tempo) | Muito baixa | Nulo | FOR UPDATE + 409 Conflict ja tratam isso |
| R4 | Provas em producao nao tem REPROVADA para testar reinicio | Alta | Baixo | Smoke test manual: criar prova → retirar → reprovar → reiniciar |
| R5 | `npm audit` 4 high em next@14.2 | Pre-existente | — | B-02 Wave 6 |

---

## 11. Sub-blocos de implementacao

### Bloco C.1 — Backend: POST /cancelar + POST /reiniciar-ciclo

**Escopo:** Dois endpoints admin-only em `provas.py` + schema `CancelarRequest` + testes.

**Entregaveis:**
- `CancelarRequest` em `schemas/prova.py` (motivo obrigatorio, min 1, max 500 chars)
- Handler `cancelar_prova` em `provas.py` com padrao FOR UPDATE → executar_transicao → commit
- Handler `reiniciar_ciclo_prova` em `provas.py` com mesmo padrao
- ~16 testes em `test_provas_api.py`
- `pytest --tb=short -q` → 389 + ~16 = ~405 passed

**Validacao:** ruff limpo, pytest verde.

### Bloco C.2 — Frontend: botoes admin + modais + hooks

**Escopo:** Hooks + componente `AdminActions` + modais de confirmacao.

**Entregaveis:**
- `useCurrentUser.ts` — hook GET /users/me
- `useCancelarProva.ts` — hook POST /{id}/cancelar
- `useReiniciarCiclo.ts` — hook POST /{id}/reiniciar-ciclo
- `AdminActions.tsx` — botoes + modais
- `page.tsx` — integrar `<AdminActions>`
- `detalhe.module.css` — estilos adicionais (botao danger, modal de confirmacao)
- tsc + lint + build limpos

### Bloco C.3 — Verificacao + Documentacao + Closeout

**Escopo:** Verificacao visual, edge cases, documentacao, closeout.

**Entregaveis:**
- Verificacao via preview tools
- CHANGELOG.md, DECISIONS.md, CLAUDE.md
- WAVE3_LOTE_C_CLOSEOUT.md
- pytest final

---

## Resumo de impacto

| Dimensao | C13+C14 |
|---|---|
| Backend — endpoints novos | +2 (`/cancelar`, `/reiniciar-ciclo`) |
| Backend — schemas novos | +1 (`CancelarRequest`) |
| Backend — testes novos | ~16 |
| Backend — arquivos modificados | 2 (`provas.py`, `schemas/prova.py`) |
| Banco de dados | **Zero** alteracoes |
| RLS | **Zero** alteracoes |
| Frontend — arquivos novos | 4 (3 hooks + 1 componente) |
| Frontend — arquivos modificados | 2 (`page.tsx`, `detalhe.module.css`) |
| Frontend — deps novas | 0 |
| Sub-blocos | 3 (C.1 backend, C.2 frontend, C.3 closeout) |
