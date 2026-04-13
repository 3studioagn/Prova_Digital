# Wave 3 — Revisao Critica — Componente 11 (Assinatura Digital e Transicao de Status)

**Data:** 2026-04-13
**Revisor:** Claude (Opus 4.6)
**Escopo:** Apenas Componente 11. Nenhum outro componente ou wave foi tocado.

---

## A. Mapeamento

### Arquivos do Componente 11

**Backend:**
| Arquivo | Linhas | Funcao |
|---------|--------|--------|
| `app/services/state_machine.py` | 231-441 | `executar_transicao` — core de dominio |
| `app/api/v1/provas.py` | 846-896 | `_carregar_prova_com_scoping` (param `lock=True`) |
| `app/api/v1/provas.py` | 1315-1379 | `_computar_transicoes_permitidas` |
| `app/api/v1/provas.py` | 1571-1755 | `_decode_assinatura` + handler `executar_transicao_prova` |
| `app/domain/schemas/prova.py` | 342-424 | `TransicaoRequest`, `TransicaoResponse`, `ASSINATURA_BASE64_MAX_BYTES` |
| `migrations/rls/006_*.sql` | todo | `pol_movimentacoes_insert` + `pol_movimentacoes_select` expandida |

**Frontend:**
| Arquivo | Funcao |
|---------|--------|
| `hooks/useExecutarTransicao.ts` | POST `/transicoes` wrapper com error mapping |
| `app/(dashboard)/escanear/page.tsx` | Pagina: state machine client, `AssinaturaModal`, `ScanReadyView`, `DoneView`, `ErrorView` |
| `app/(dashboard)/escanear/escanear.module.css` | CSS Module (520 linhas) |
| `hooks/useScanner.ts` | html5-qrcode wrapper (compartilhado C10) |
| `hooks/useScanProva.ts` | POST `/scan` wrapper (compartilhado C10) |
| `lib/types/prova.ts` | `TransicaoRequest`, `TransicaoResponse`, `ScanResponse`, `ASSINATURA_BASE64_MAX_BYTES` |

**Testes:**
| Arquivo | Testes C11 |
|---------|-----------|
| `tests/test_state_machine.py` | 24 testes de `executar_transicao` |
| `tests/test_provas_api.py` | 37 testes de `POST /{id}/transicoes` |

### Fluxos de usuario cobertos
1. Scan QR (C10) -> escolher transicao -> assinar -> confirmar -> sucesso
2. Scan QR -> escolher "Reprovar" -> preencher motivo -> assinar -> confirmar -> sucesso
3. Scan QR -> nenhuma transicao disponivel (estado terminal ou perfil errado) -> mensagem informativa
4. Qualquer erro (token expirado, 404, 409, 422, 502) -> mensagem + opcao de retentar

### Integracoes com outros componentes
- **C10 (Scanner):** `POST /scan` retorna `transicoes_permitidas` -> C11 renderiza botoes
- **C12 (Timeline):** `MovimentacaoResponse` alimenta timeline visual
- **C13 (Cancelamento):** `executar_transicao(CANCELADA)` reutilizado via endpoint dedicado
- **C14 (Reinicio):** `executar_transicao(CRIADA)` reutilizado via endpoint dedicado
- **Wave 2:** `_carregar_prova_com_scoping`, `_build_prova_response`, `ProvaResponse` reutilizados sem alteracao

---

## B. Bugs e Riscos Latentes

### B-01 — Referencia stale de `scanHook.error` no useEffect de scan-loading
- **Arquivo:** `frontend/src/app/(dashboard)/escanear/page.tsx:101-121`
- **Severidade:** Media
- **Descricao:** O `useEffect` que dispara o `scanHook.escanear(state.payload)` captura `scanHook` da closure do render que disparou o efeito. Quando `escanear` retorna `null` (erro), o codigo lê `scanHook.error` na linha 110 — mas esse valor ainda e `null` porque o state do hook foi atualizado internamente (novo render) enquanto a closure mantem a referencia antiga.
- **Impacto:** O usuario sempre ve a mensagem generica "Nao foi possivel resolver o QR Code." em vez da mensagem especifica do backend (ex: "QR Code nao corresponde a prova esperada", "Prova nao encontrada").
- **Correcao sugerida:** Modificar `useScanProva.escanear` para retornar um objeto `{ data, error }` em vez de `ScanResponse | null`, permitindo que o useEffect acesse o erro diretamente do retorno da funcao em vez de depender do state do hook.

### B-02 — Canvas de assinatura com dimensoes fixas (500x200) em dispositivo movel
- **Arquivo:** `frontend/src/app/(dashboard)/escanear/page.tsx:537-540`
- **Severidade:** Media
- **Descricao:** `SigCanvas` recebe `canvasProps={{ width: 500, height: 200 }}` como atributos do canvas HTML. O CSS `.signatureCanvas` aplica `width: 100%` que escala visualmente, mas o canvas interno mantem resolucao 500x200. Em telas < 500px (celulares — caso de uso primario), a discrepancia entre coordenadas de toque e coordenadas do canvas pode causar:
  - Tracos que nao seguem o dedo com precisao
  - Assinatura distorcida (esticada/comprimida)
  - Em telas muito pequenas (< 320px), perda de resolucao significativa
- **Impacto:** Assinatura digital ilegivel ou imprecisa no dispositivo principal de uso (celular em campo).
- **Correcao sugerida:** Usar `useRef` + `ResizeObserver` (ou o evento `resize` do container) para definir `width` dinamicamente com base na largura real do container. Manter `height` fixo (ex: 200) ou proporcional. O `react-signature-canvas` suporta redimensionamento via `canvasProps` reativo.

### B-03 — 409 Conflict retorna ao modal de assinatura em vez de re-scan
- **Arquivo:** `frontend/src/app/(dashboard)/escanear/page.tsx:170-178`
- **Severidade:** Baixa
- **Descricao:** Quando `transicaoHook.executar` retorna `null` (qualquer erro), o state volta para `signing` com o modal aberto. Para o caso especifico de 409 ("O status da prova mudou. Escaneie novamente."), a mensagem diz ao usuario para escanear novamente, mas ele esta no modal de assinatura. Precisa: fechar modal -> clicar "Escanear outra" -> re-escanear. Fricao desnecessaria.
- **Impacto:** UX confusa — mensagem contradiz o estado visual.
- **Correcao sugerida:** No callback `submeterTransicao`, apos detectar que o erro e 409 (verificar `transicaoHook.error` ou retornar o status no hook), transicionar para `scan-error` com a mensagem do 409 em vez de voltar para `signing`. O `ErrorView` ja tem botao "Tentar novamente" que leva ao scan.

### B-04 — Prop `loading` do `AssinaturaModal` nunca e `true`
- **Arquivo:** `frontend/src/app/(dashboard)/escanear/page.tsx:244`
- **Severidade:** Baixa
- **Descricao:** O modal recebe `loading={false}` sempre. Durante o estado `submitting`, o modal nao e renderizado — um spinner separado ("Registrando movimentacao...") aparece no lugar. Os botoes do modal usam `disabled={loading}` que nunca e ativado. O botao "Confirmar" mostra `{loading ? "Enviando..." : "Confirmar"}` — o texto "Enviando..." nunca aparece.
- **Impacto:** Codigo morto/misleading. Se alguem mudar o fluxo para manter o modal durante `submitting`, os botoes nao vao desabilitar como esperado sem alterar tambem o prop.
- **Correcao sugerida:** Duas opcoes: (a) remover o prop `loading` e o condicional dos botoes (simplificar), ou (b) se desejavel manter o modal aberto durante o submit, passar `loading={state.kind === "submitting"}` e renderizar o modal em ambos `signing` e `submitting`.

### B-05 — `motivo_reprovacao` armazenado sem sanitizacao HTML
- **Arquivo:** `backend/app/services/state_machine.py:307` + `backend/app/domain/schemas/prova.py:396-403`
- **Severidade:** Baixa
- **Descricao:** O `motivo_reprovacao` recebe apenas `strip()` no validator Pydantic. Conteudo como `<script>alert(1)</script>` e armazenado literalmente no banco e retornado na API via `MovimentacaoResponse.motivo_reprovacao`.
- **Impacto:** Se algum frontend futuro renderizar o motivo via `dangerouslySetInnerHTML` ou equivalente, XSS. O frontend atual usa `{motivo}` em JSX (React escapa automaticamente), entao **nao ha vulnerabilidade hoje**. Risco futuro baixo.
- **Correcao sugerida:** Nao corrigir agora. React escapa por padrao. Se futuramente houver consumidores fora do React (email, PDF, etc), sanitizar na camada de saida, nao na entrada (preservar dado original).

### B-06 — Heranca `TransicaoInvalidaError(ValueError)` cria armadilha de ordenacao
- **Arquivo:** `backend/app/services/state_machine.py:39-41` + `backend/app/api/v1/provas.py:1651-1692`
- **Severidade:** Baixa
- **Descricao:** `TransicaoInvalidaError` herda de `ValueError`. No handler, o `except TransicaoInvalidaError` (linha 1651) precisa vir ANTES de `except ValueError` (linha 1682) — se a ordem inverter, `ValueError` captura tudo e retorna 422 em vez de 409. Ha um comentario explicativo nas linhas 1684-1686, mas e fragil.
- **Impacto:** Nenhum hoje. Armadilha para manutencao futura.
- **Correcao sugerida:** Nao alterar agora — o comentario documenta. Opcao futura: mudar heranca para `TransicaoInvalidaError(Exception)`, mas isso quebraria testes existentes. Documentar como WONTFIX.

### B-07 — Fallback `created_at or datetime.now()` e codigo morto
- **Arquivo:** `backend/app/api/v1/provas.py:1753`
- **Severidade:** Baixa (higiene)
- **Descricao:** `movimentacao.created_at or datetime.now(tz=timezone.utc)` — o `or` nunca e acionado porque `executar_transicao` gera `created_at` explicitamente no Python (ADR-084 Decisao 6). O fallback era necessario antes dessa decisao.
- **Impacto:** Codigo morto, sem impacto funcional. Pode confundir leitores ("sera que created_at pode ser None?").
- **Correcao sugerida:** Remover o `or datetime.now(...)`, deixando apenas `movimentacao.created_at`.

---

## C. Qualidade de Codigo

### C-01 — `page.tsx` com 644 linhas e 5 componentes no mesmo arquivo
- **Arquivo:** `frontend/src/app/(dashboard)/escanear/page.tsx`
- **Severidade:** Baixa
- **Descricao:** O arquivo contem `EscanearPage`, `IdleView`, `ScanningView`, `ScanReadyView`, `AssinaturaModal`, `DoneView`, `ErrorView`. A organizacao interna e boa (separacao por secoes com comentarios), mas o tamanho total dificulta navegacao.
- **Avaliacao:** Aceitavel para Wave 3. Os sub-componentes sao especificos desta pagina e nao sao reutilizados. Extrair para arquivos separados seria melhoria cosmetica, nao funcional.
- **Recomendacao:** Nao refatorar agora. Se Wave 4+ tocar nesta pagina, considerar extrair `AssinaturaModal` para arquivo proprio (e o maior e mais autonomo).

### C-02 — Callbacks `comecarScan`/`resetar` com deps instáveis
- **Arquivo:** `frontend/src/app/(dashboard)/escanear/page.tsx:123-133`
- **Severidade:** Baixa
- **Descricao:** `useCallback` com `[scanHook, transicaoHook]` como deps. Hooks retornam objetos novos a cada render, recriando os callbacks desnecessariamente.
- **Impacto:** Micro-ineficiencia. Nao causa bugs — esses callbacks sao usados em `onClick` de botoes, nao como deps de `useEffect`.
- **Recomendacao:** Nao corrigir. Otimizacao prematura.

### C-03 — Sem log estruturado para erros de decode de assinatura
- **Arquivo:** `backend/app/api/v1/provas.py:1571-1586`
- **Severidade:** Baixa
- **Descricao:** `_decode_assinatura` levanta HTTPException(422) sem logar nada. Em caso de ataques ou bugs de encoding no frontend, nao haveria rastro nos logs do backend.
- **Recomendacao:** Adicionar `logger.warning(...)` antes de levantar a excecao, incluindo user_id e tamanho do payload.

---

## D. UX e Clareza de Fluxo

### D-01 — Falta de contexto sobre consequencia da acao antes de assinar
- **Tela:** `scan-ready` -> botoes de acao
- **Descricao:** O usuario ve botoes como "Retirar prova", "Aprovar", "Devolver a 3Studio". Ao clicar, vai direto para o modal de assinatura com titulo "Confirmar: Retirar prova" e descricao generica "Assine no quadro abaixo para confirmar a movimentacao." **Falta:** uma indicacao explicita da consequencia, tipo "Status vai mudar de **Criada** para **Retirada pelo vendedor**".
- **Ganho:** O operador em campo (vendedor, motorista, clicheria) entende com certeza o que esta confirmando, reduzindo erros acidentais.
- **Proposta:** Adicionar uma linha na descricao do modal: `"Status: {STATUS_LABELS[statusAtual]} → {STATUS_LABELS[statusNovo]}"`. Respeita o estilo existente — apenas uma `<p>` extra com classe `modalDescription`.

### D-02 — Mensagem de sucesso (DoneView) nao mostra o novo status
- **Tela:** `done`
- **Descricao:** A tela mostra "Tudo certo!" e "{nome_prova} — Retirar prova — movimentacao registrada." Nao mostra o **novo status** da prova. O operador precisaria voltar ao detalhe para confirmar.
- **Ganho:** Confirmacao visual imediata.
- **Proposta:** Adicionar badge do novo status abaixo da mensagem: `"Novo status: {STATUS_LABELS[scan.prova.status]}"`. O `scan.prova` ja contem os dados atualizados pos-transicao (o frontend atualiza em `submeterTransicao`).

### D-03 — `ScanReadyView` sem indicacao de que prova esta em estado terminal
- **Tela:** `scan-ready` com `transicoes_permitidas = []`
- **Descricao:** Quando a prova esta em estado terminal (RECEBIDA_PELA_CLICHERIA, CANCELADA), a mensagem e a mesma para quando o usuario nao tem permissao: "Voce nao tem permissao para movimentar esta prova no estado atual." Isso e impreciso — a prova pode estar finalizada, nao e questao de permissao.
- **Ganho:** Clareza — o operador entende se precisa buscar outro perfil ou se a prova ja encerrou o ciclo.
- **Proposta:** Verificar `prova.status` no frontend: se CANCELADA ou RECEBIDA_PELA_CLICHERIA, mostrar "Esta prova ja foi finalizada (status: {STATUS_LABELS[prova.status]})." em vez da mensagem de permissao. Caso contrario, manter a mensagem atual.

### D-04 — Modal de assinatura sem handler de Escape
- **Tela:** `signing` (AssinaturaModal)
- **Descricao:** O modal nao fecha ao pressionar Escape. Padrao de acessibilidade (WAI-ARIA Modal Dialog) exige que Escape feche o dialog.
- **Ganho:** Acessibilidade e conveniencia (especialmente em desktop).
- **Proposta:** Adicionar `useEffect` com `keydown` listener para Escape que chama `onCancelar`.

### D-05 — Modal sem focus trap
- **Tela:** `signing` (AssinaturaModal)
- **Descricao:** `role="dialog" aria-modal="true"` indica modal, mas nao ha focus trap implementado. O usuario pode usar Tab para navegar para elementos atras do backdrop.
- **Ganho:** Acessibilidade. Cumprimento do padrao WAI-ARIA.
- **Proposta:** Implementar focus trap basico: na montagem do modal, focar o primeiro elemento interativo; no `onKeyDown` do backdrop, interceptar Tab e shift+Tab para ciclar entre os elementos do modal. Alternativa: extrair para um `<FocusTrap>` wrapper reutilizavel.

---

## E. Cobertura de Testes

### Cobertura atual
| Arquivo | Cobertura | Meta |
|---------|-----------|------|
| `state_machine.py` | **100%** | >= 80% |
| `provas.py` (todo) | **96%** (17 missing) | >= 80% |
| `schemas/prova.py` | **97%** (4 missing) | >= 80% |
| Total backend | **407 passed** | — |
| Frontend | tsc + lint + build limpos | — |

### Cenarios faltantes (especificos de C11)

| # | Cenario | Criticidade | Notas |
|---|---------|-------------|-------|
| E-01 | `scanHook.error` stale no useEffect (B-01) | Media | Nao testavel unitariamente sem test framework frontend; validavel com fix + smoke |
| E-02 | Canvas 500px em tela < 320px (B-02) | Media | Requer teste visual em device real |
| E-03 | Transicao concorrente real (2 requests simultaneos com FOR UPDATE) | Baixa | Testado indiretamente via mock; FOR UPDATE e mecanismo do banco — teste de integracao real exigiria 2 connections concorrentes |
| E-04 | Base64 valido mas que decodifica para conteudo nao-PNG | Baixa | O backend aceita qualquer binario na `assinatura_digital` — nao valida magic bytes da assinatura (diferente da arte do R2). Aceitavel: assinatura e prova server-side, nao renderizada |
| E-05 | `motivo_reprovacao` com 1000 chars (limite maximo) | Baixa | Pydantic `max_length=1000` valida; nao ha teste explicito com string de 1000 chars |

---

## F. Performance e Observabilidade

### Performance
- **Queries:** Unica query JOIN `provas_digitais + usuarios` com FOR UPDATE. Sem N+1. Indices existentes cobrem: `provas_digitais_pkey` + `usuarios_pkey`.
- **Lock duration:** FOR UPDATE mantido entre `_carregar_prova_com_scoping` e `db.commit()`. Inclui: `executar_transicao` (INSERT movimentacao + flush + INSERT audit_log + flush) + commit. Para sistema com baixo trafego (< 10 TPS), tempo de lock e desprezivel.
- **Payload size:** `assinatura_base64` ate 700KB por request. Em campo, assinaturas tipicas de signature pad geram 30-100KB. O limite e generoso mas aceitavel.
- **Frontend bundle:** `/escanear` = 11.4 kB (161 kB First Load JS). Compacto.

### Observabilidade
- **Logs:** `logger.info("Transicao OK: ...")` com prova, status_de, status_para, user, ciclo, rota. Excelente para rastreamento.
- **Audit log:** Cada transicao grava `detalhes_json` estruturado com `de`, `para`, `ciclo`, `rota_antes`, `rota_depois`, motivos. Completo.
- **Faltante:** Log no `_decode_assinatura` para tentativas invalidas (C-03). Nao ha metricas/tracing expliciteas, mas aceitavel para o estagio do projeto.

---

## G. Seguranca

### Supabase Advisors
- `rls_enabled_no_policy` (INFO) em `alembic_version` — intencional (ADR-025).
- `auth_leaked_password_protection` (WARN) — plano pago (ADR-027).
- **Zero achados novos.** Status inalterado desde Wave 2.

### Analise especifica do C11
- **Auth:** Todos os endpoints C11 usam `get_current_user` (JWT obrigatorio). Correto.
- **RBAC:** Validacao de setor/localizacao via `validar_transicao` + regra RF-009. Admin bypassa validacao de setor. Consistente.
- **RLS:** `pol_movimentacoes_insert` admin-only + `pol_movimentacoes_select` expandida. Backend usa service_role (bypassa RLS). Correto como defesa em profundidade.
- **CORS:** Configurado via `FRONTEND_URL` no Railway. OK.
- **Input validation:** `TransicaoRequest` valida enum, max_length, rejeita CANCELADA/CRIADA. `_decode_assinatura` valida base64. `motivo_reprovacao` tem strip + max_length. Adequado.
- **Rate limiting:** Ausente em `POST /scan` e `POST /{id}/transicoes`. Mitigado por JWT obrigatorio. Risco baixo para o volume atual.
- **FOR UPDATE:** Previne race condition em transicoes concorrentes. Correto.
- **Constant-time hash:** `qrcode_service.validar_payload_qr` usa comparacao constant-time. Correto.

---

## H. Plano de Acao Priorizado

| ID | Cat | Descricao | Sev | Esf | Recomendacao | Risco de nao fazer |
|----|-----|-----------|-----|-----|------|-----|
| **B-01** | Bug | `scanHook.error` stale — erro generico sempre | Media | P | **Aplicar agora** | Usuario em campo ve "Nao foi possivel resolver" em vez de "Prova nao encontrada" ou "QR Code invalido" — dificulta diagnostico |
| **B-02** | Bug | Canvas 500x200 fixo — assinatura imprecisa em mobile | Media | M | **Aplicar agora** | Assinatura digital ilegivel no dispositivo principal; pode invalidar prova legalmente |
| **D-01** | UX | Falta status de→para no modal de assinatura | Media | P | **Aplicar agora** | Operador confirma transicao errada por falta de contexto |
| **D-03** | UX | Mensagem incorreta para estado terminal | Baixa | P | **Aplicar agora** | Confusao desnecessaria ("sem permissao" quando na verdade esta finalizada) |
| **B-03** | Bug/UX | 409 volta ao modal em vez de re-scan | Baixa | P | **Aplicar nesta sessao se tempo** | Fricao em cenario de race (raro) |
| **D-02** | UX | DoneView sem badge do novo status | Baixa | P | **Aplicar nesta sessao se tempo** | Operador nao tem confirmacao visual do status resultante |
| **D-04** | UX/A11y | Modal sem handler Escape | Baixa | P | **Aplicar nesta sessao se tempo** | Acessibilidade incompleta |
| **B-04** | Qualidade | Prop `loading` nunca true no modal | Baixa | P | **Aplicar nesta sessao se tempo** | Codigo morto confuso |
| **B-07** | Qualidade | Fallback `created_at or now()` morto | Baixa | P | **Aplicar nesta sessao se tempo** | Codigo confuso |
| **C-03** | Observ | Log em `_decode_assinatura` ausente | Baixa | P | **Aplicar nesta sessao se tempo** | Sem rastro de tentativas de assinatura invalida |
| **D-05** | A11y | Modal sem focus trap | Baixa | M | **Adiar** — Wave 6 (polish) | Acessibilidade incompleta; baixo impacto em mobile-first |
| **B-05** | Seguranca | `motivo_reprovacao` sem sanitizacao | Baixa | — | **Adiar** — React escapa por padrao; nao ha risco hoje | XSS se futuro consumidor nao escapar (improvavel) |
| **B-06** | Qualidade | Heranca ValueError armadilha | Baixa | — | **Adiar** — documentado em comentario | Bug se alguem reordenar excepts (improvavel) |
| **C-01** | Qualidade | page.tsx 644 linhas | Baixa | M | **Adiar** — cosmetico | Nenhum |
| **C-02** | Qualidade | Callbacks com deps instaveis | Baixa | — | **Nao corrigir** — otimizacao prematura | Nenhum |

**Legenda de esforco:** P = Pequeno (< 30 min), M = Medio (30-90 min), G = Grande (> 90 min)

---

**PARE AQUI.** Aguardo priorizacao: quais itens da tabela H entram nesta sessao?
