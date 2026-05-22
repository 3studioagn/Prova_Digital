# Analise Read-Only + Proposta — Componente 22 (Wave 8 v5.0)

**Sessao:** Wave 8 v5.0 / C22 — Reativacao da Tela de Assinatura no Fluxo de Escaneamento
**Tipo:** Gate 1 — analise read-only + arqueologia + proposta de estrategia (NENHUMA linha de codigo de producao)
**Data:** 2026-05-22
**Branch base:** `development`
**Branch desta entrega:** `wave8-v5-c22/analysis` (sem merge)
**Status:** Gate 1 CONCLUIDO — aguardando 11 decisoes humanas + autorizacao para o Gate 2
**Documento irmao:** [arqueologia.md](arqueologia.md) (fase preliminar — recuperacao de codigo)

---

## 0. Confirmacao de leitura + Divergencias criticas (PRE-GATE 1)

### 0.1 Artefatos lidos integralmente (prompt Secao 3)

| Artefato | Caminho real | Estado |
|---|---|---|
| Contrato C12 | `docs/wave3-v4-c11/contrato-c12.md` | ✅ existe, ATIVO, coerente |
| Contrato C19 | `docs/wave3-v4-c10/contrato-c19.md` | ✅ existe, coerente |
| Requisitos v5.0 | `RequisitosProvasDigitais_v5_0.docx` (extraido) | ✅ lido (RF-006, RF-007, RF-008, RF-028, RN-014, Secao 5, Secao 6, US-018/019/020) |
| Backlog v5.0 | `BACKLOG_RastreioProvasDigitais_v5_0.docx` (extraido) | ✅ lido (C22, C23, DoD global Secao 2, Secao 4 waves) |
| DAT v3.0 | `DAT_RastreioProvasDigitais_v3_0.docx` (extraido) | ✅ lido (Secao 3 testes, Secao 4 maquina, Secao 7 RBAC, Secao 8 identificacao) |
| UML v4.0 | `UML_RastreioProvasDigitais_v4_0.drawio` | ✅ lido (diagrama de casos de uso — UC-05 "Assinar Digitalmente e Confirmar") |
| CLAUDE.md / DECISIONS.md / CHANGELOG.md | raiz do repo | ✅ consultados |
| Codigo backend/frontend | `provas.py`, `state_machine/`, `escanear/page.tsx`, `identificacao-prova.ts`, `prova.ts`, hooks, `package.json` | ✅ mapeados (subagentes + leitura direta) |

### 0.2 contrato-c12.md — presenca e qualidade (bloqueio critico 1)

**SUPERADO.** O `docs/wave3-v4-c11/contrato-c12.md` existe, esta com status
"ATIVO", e e coerente com o codigo real. Reproducao literal do que o C22
consome:

- **Mapeamento estado -> metadata visual:** "**`frontend/src/lib/types/prova.ts`**
  — fonte unica de verdade dos tipos + labels." Exporta `STATUS_LABELS` e
  `STATUS_LABELS_SHORT` (`Record<StatusProva, string>`).
- **Helper de deteccao de contexto do Motorista** (assinaturas literais):
  - Python: `def contexto_motorista(status: StatusProvaEnum) -> ContextoMotorista | None`
    em `backend/app/state_machine/v4/contextos.py`.
  - `ContextoMotorista = Literal["ida_laminacao", "volta_laminacao", "entrega_final"]`.
  - TypeScript (espelho): `export function contextoMotorista(status: StatusProva): ContextoMotorista | null`
    em `frontend/src/lib/types/prova.ts` (confirmado presente).

### 0.3 DIVERGENCIAS CRITICAS — premissas do prompt vs realidade do repo

> Esta sub-secao e o achado mais importante do Gate 1. O prompt declara um
> "Estado de Partida" que **nao corresponde ao estado real do repositorio**.
> Nenhuma das divergencias bloqueia o C22 em si, mas TODAS exigem decisao
> humana antes do Gate 2.

**D-1 — C20 (Camada de Animacoes) NAO existe.** O prompt afirma "Wave 6 v4.0
(C20) entregue" e instrui reusar `<MotionModal>`, `<PageTransition>`, sistema
de toasts, `/lib/motion/tokens.ts`, `useReducedMotion`. **Nenhum desses
existe.** `frontend/src/components/` tem apenas 4 componentes
(`KeyboardShortcutsHelp`, `Restricted`, `AuthToast`, `icons`). Nao ha pasta
`lib/motion/`. O projeto usa `framer-motion` (`^12.38.0`) **diretamente**
(pill animations, timeline). Impacto: a **Decisao 10 precisa ser
reformulada** (ver §5.5).

**D-2 — C21 (Migracao de Dados, Wave 7) NAO foi executado.** Nao ha branch,
docs nem script. Confirmado via banco: **16 de 20 provas sao legacy** (11 com
`rota IS NULL`, 5 com `rota IN {PADRAO, DIRETA}`); apenas 4 sao v4.0. A
maquina v3.0 segue ativa em coexistencia. Impacto: o **Cenario 7 (prova
legacy) e mais relevante que o esperado** — nao bloqueia (a coexistencia
v3/v4 ja funciona), mas exige cobertura de teste solida.

**D-3 — A v4.0 NAO esta integralmente concluida (bloqueio critico 3).** O
prompt instrui "parar se a v4.0 nao estiver integralmente concluida". Estado
real: C16 (Wave 5 v4.0) esta em `development` aguardando PR/auditoria; **C20
e C21 nunca foram iniciados**; nada da v4.0 esta em `main`. **PORÉM** — as
**dependencias REAIS do C22**, conforme o Backlog v5.0 Secao 4 ("Depende de:
10 (v4.0), 19, 11 (v4.0)") e a propria linha de pre-requisitos do prompt
(05, 06, 10, 19, 11), estao **TODAS concluidas, auditadas, corrigidas e
mergeadas em `development`**. C20 e C21 NAO sao dependencia do C22.
**Avaliacao:** o bloqueio critico 3 esta tecnicamente disparado, mas e
**nao-fatal para o C22** — as pre-condicoes funcionais estao satisfeitas.
Decisao do solicitante necessaria (ver §0.4).

**D-4 — Deploy de producao (Railway) esta FORA DO AR.** Probe em
`https://provadigital-production.up.railway.app/`:
`{"status":"error","code":404,"message":"Application not found"}` — pagina de
erro **da plataforma Railway**, nao do FastAPI. `/health`, `/docs`, `/scan`,
`/transicoes` todos retornam 404. O frontend Vercel
(`https://prova-digital-five.vercel.app`) responde **307** (no ar). Impacto:
infraestrutura, **nao codigo**. O codigo de backend de assinatura esta
intacto e verificado (§5.2). O C22 sera desenvolvido/testado contra backend
local. Mario precisa redeployar o Railway antes do release — item de
escalacao, paralelo ao C22.

**D-5 — Erros factuais no CHANGELOG.** (a) Afirma que `react-signature-canvas`
foi removido do `package.json` — **falso**, segue instalado (`^1.0.7`,
orfao). (b) "page.tsx redesenhado ~414 LOC" — real: 545 LOC no commit do
redesenho, 777 hoje. Detalhes em [arqueologia.md](arqueologia.md) §2 e §5.

**D-6 — Playwright e axe-core NAO instalados.** O prompt (criterios 17 e 22)
e o DAT Secao 3 pedem "E2E com Playwright" e "axe-core". `package.json` so
tem `vitest@^2.1.9`. O projeto adota historicamente "Vitest minimo + smoke
E2E manual" (decisao D-13 da Wave 1 v4.0). Impacto: a **Decisao 11 precisa
incluir a sub-decisao "instalar Playwright+axe vs seguir a cultura do
projeto"** (ver §5.5).

**D-7 — "14 estados" (docs) vs 17 valores (enum).** Requisitos Secao 5.1
descreve "14 estados" — esse e o conjunto **logico v4.0**. O enum PostgreSQL
`status_prova_enum` tem **17 valores** (10 v3.0 + 7 v4.0) por **coexistencia**
— provas legacy ainda usam estados v3.0-exclusivos (`ENVIADA_PARA_CLICHERIA`,
`ENCAMINHADA_A_CLICHERIA`, `COM_MOTORISTA` legacy). Nao e conflito; e o
design de coexistencia. Confirmado via MCP.

### 0.4 Recomendacao sobre o bloqueio critico 3

O C22 **pode e deve prosseguir** assim que as 11 decisoes forem respondidas,
pelos seguintes motivos:

1. Todas as dependencias funcionais reais (C05/C06/C10/C19/C11) estao prontas.
2. O C22 destrava um **bug de producao critico**: hoje nenhum ator consegue
   movimentar prova alguma pelo fluxo de scanner (a UI de assinatura sumiu).
3. C20 e C21 nao sao dependencia do C22 (Backlog Secao 4 confirma).
4. A unica adaptacao causada pela ausencia do C20 e usar `framer-motion`
   direto — o que o resto do app ja faz.

**Alternativa** (se o solicitante preferir): pausar o C22 para entregar C20 e
C21 antes, restaurando a ordem do Backlog. Nao recomendado — atrasa a
correcao de um bug de producao sem ganho funcional para o C22.

---

## 5.1 Resultado da arqueologia

Investigacao completa em [arqueologia.md](arqueologia.md). Sintese:

- **Recuperacao bem-sucedida, zero lacunas bloqueantes.** Commit-fonte:
  `6add246` ("Wave 04 concluida", 2026-04-14). Commit do redesenho que
  removeu a UI: `e4d543b` ("feat(wave3-v4/c10): ...", 2026-05-07).
- **Mecanismo de captura confirmado:** `react-signature-canvas` (`^1.0.7`)
  — canvas de tracado com dedo/mouse, export PNG base64. **O pacote segue
  instalado** (Decisao 2 resolvida pela arqueologia).
- **Componentes recuperados verbatim:** `AssinaturaModal`, `ScanReadyView`,
  `DoneView`, `ErrorView`, maquina `PageState`, `useScanProva` (deletado),
  CSS do modal.
- **Backend 100% intacto.** `useExecutarTransicao.ts` **ainda existe** em
  `development` (orfao, sem importador) — reusavel direto. Tipos
  `ScanResponse`/`TransicaoRequest`/`TransicaoResponse`/`ASSINATURA_BASE64_MAX_BYTES`
  preservados. Tokens CSS confirmados em `globals.css`.
- **Compatibilidade com a v4.0:** o `AssinaturaModal` original e
  **agnostico de rota** — recebe `statusAtual`/`statusNovo`/`precisaMotivo`
  ja resolvidos. **Nao ha incompatibilidade estrutural** com a maquina v4.0
  (14 estados). Ponto de escalacao do prompt (Secao 2.1) resolvido: a
  reativacao e viavel **sem adaptacoes maiores** — apenas labels v4.0,
  anti-enumeracao e seletor Aprovar/Reprovar explicito.

---

## 5.2 Mapeamento do backend de assinatura

### 5.2.1 Endpoint de transicao (consome a assinatura)

| Campo | Valor |
|---|---|
| Rota | `POST /api/v1/provas/{prova_id}/transicoes` |
| Handler | `executar_transicao_prova` — `backend/app/api/v1/provas.py:2138` |
| Autenticacao | Bearer JWT — `Depends(get_current_user)` |
| Body | `TransicaoRequest` (Pydantic v2) |
| Sucesso | **201** `TransicaoResponse { prova, movimentacao }` |

**`TransicaoRequest`** (`backend/app/domain/schemas/prova.py`):

```python
class TransicaoRequest(BaseModel):
    status_novo: StatusProvaEnum
    assinatura_base64: str = Field(..., min_length=1, max_length=700_000)
    motivo_reprovacao: str | None = Field(None, max_length=1000)
    # validator: rejeita CANCELADA e CRIADA como status_novo (ganchos C13/C14)
    # validator: strip do motivo_reprovacao
```

**Codigos de erro (mapeamento exato — `provas.py:2195-2251`):**

| HTTP | Causa | Tratamento C22 |
|---|---|---|
| 201 | Sucesso | Atualiza UI (Decisao 7) |
| 401 | Token ausente/invalido | Sessao expirada → redirect login (Cenario nao listado, mas tratar) |
| 404 | Prova inexistente OU fora do scope | Mensagem generica (anti-enum) |
| 409 | `TransicaoInvalidaError` — status mudou (**race condition**) | Cenario 9 — feedback claro + refresh |
| 422 | `AtorNaoAutorizadoError` / `RotaIndeterminavelError` / `ValueError` (motivo ausente) / base64 invalido | Mapear para mensagem **generica** se for ator (anti-enum) |
| 502 | Erro transitorio de DB | Falha de rede — retry (Decisao 5) |

> **Atencao anti-enumeracao (R-3):** `AtorNaoAutorizadoError` vira **422**
> com mensagem que LISTA os setores permitidos. O C22 nunca cai nesse
> caminho no fluxo feliz (so abre assinatura quando `transicoes_permitidas`
> e nao-vazio), mas o tratamento de erro do C22 deve mapear 422 inesperado
> para mensagem generica — nunca exibir o texto cru.

**Helper `_decode_assinatura`** (`provas.py:2110`): decodifica o base64;
levanta 422 ("Assinatura base64 invalida" / "Assinatura vazia apos decode").

O handler chama `executar_transicao(db, prova=, status_novo=, usuario=,
assinatura_digital=, motivo_reprovacao=, request=)` (o **facade** v3/v4),
carrega a prova com `FOR UPDATE` (serializa transicoes concorrentes — base
do tratamento de race), comita e retorna 201.

### 5.2.2 Endpoint de identificacao (origem do fluxo)

`POST /api/v1/provas/scan` → `ScanResponse { prova, transicoes_permitidas,
motivo_obrigatorio_em }`. **Descoberta-chave:** o `/scan` **ja calcula e
retorna `transicoes_permitidas`** via `_computar_transicoes_permitidas`
(`provas.py:1692`); o redesenho do C10 apenas **parou de consumir** esse
campo (comentario literal em `provas.py:2006-2010`). **O C22 reativa o
consumo** — nao precisa de endpoint novo.

### 5.2.3 Persistencia

`movimentacoes.assinatura_digital` — coluna **`bytea NOT NULL`** (confirmado
via MCP). A assinatura nunca e exposta em resposta de API (so server-side).

### 5.2.4 Confirmacao "operacional"

- **Nivel de codigo:** ✅ operacional. Handlers lidos e verificados; rota
  registrada no `APIRouter`; mapeamento de excecoes correto; coberto pela
  suite de 967 testes de backend (Wave 3 v4.0 / C11).
- **Nivel de producao:** ❌ **indisponivel** — o deploy Railway retorna
  "Application not found" (D-4). Nao foi possivel teste curl autenticado
  (sem token no Gate 1; e o deploy esta fora do ar). **Conclusao:** o
  backend de assinatura esta **intacto no codigo**; a indisponibilidade e
  de infraestrutura. C22 desenvolve contra backend local. **Escalar a D-4
  ao Mario** para redeploy antes do release.

---

## 5.3 Mapeamento da maquina de estados (C11)

### 5.3.1 Como obter o(s) proximo(s) perfil(is) habilitado(s)

**O C22 NAO reimplementa a maquina.** Ele consome `transicoes_permitidas`
do `ScanResponse` — ja calculado pelo backend:

`_computar_transicoes_permitidas(prova, usuario)` (`provas.py:1692`) roteia
por `prova.rota`:

- `rota IN {MATRIZ, LAM_MATRIZ, FILIAL, LAM_FILIAL}` → **maquina v4.0**:
  `transicoes_validas_v4(rota, status, usuario)` consulta
  `TRANSITION_RULES[(rota, status)]` e filtra por `usuario.is_admin OR
  usuario.setor == transicao.ator`.
- `rota IS NULL` ou `rota IN {PADRAO, DIRETA}` → **maquina v3.0 legacy**:
  `TRANSICOES` + `ATORES_POR_TRANSICAO` (`services/state_machine.py`).

**Regra de decisao do C22** apos identificacao bem-sucedida:

| Resultado do `/scan` | Significado | Acao do C22 |
|---|---|---|
| 200, `transicoes_permitidas` nao-vazio | Usuario **e** o proximo ator | Abrir tela de assinatura |
| 200, `transicoes_permitidas` vazio, `status` terminal | Prova concluida/cancelada (in-scope) | Mensagem "ja concluida" (Decisao 8) |
| 200, `transicoes_permitidas` vazio, `status` ativo | **Ator errado** (in-scope, nao e a vez dele) | Mensagem **generica** = 404 (RN-014) |
| 404 | Inexistente OU fora do scope | Mensagem **generica** (anti-enum) |

> A validacao "perfil x proxima transicao" e portanto **delegada ao
> backend**. O `useAuthorization("scanner")` (frontend) so controla acesso
> a *pagina* `/escanear` (universal — Matriz Secao 6). A elegibilidade para
> assinar uma prova especifica vem de `transicoes_permitidas`.

### 5.3.2 Estrutura da regra v4.0

`backend/app/state_machine/v4/rules.py`:
`TRANSITION_RULES: Mapping[tuple[RotaEnum, StatusProvaEnum], FrozenSet[Transition]]`,
onde `Transition` = dataclass `(destino: StatusProvaEnum, ator: SetorEnum,
motivo_obrigatorio: bool)`. A Matriz de Transicoes (Requisitos Secao 5.2-5.6)
e a especificacao canonica — 4 rotas, contadas no Backlog como 5+10+3+6
transicoes nao-iniciais.

### 5.3.3 Contexto do Motorista (3 contextos)

`contexto_motorista(status)` / `contextoMotorista(status)` (contrato-c12 §2):
- `COM_MOTORISTA_IDA_LAMINACAO` → `"ida_laminacao"`
- `COM_MOTORISTA_VOLTA_LAMINACAO` → `"volta_laminacao"`
- `COM_MOTORISTA_ENTREGA_FINAL` → `"entrega_final"`
- `COM_MOTORISTA` (legacy) → `"entrega_final"`
- demais → `null`

O C22 usa o helper TS para exibir o contexto na tela de assinatura do
motorista (Cenario 1). O contexto **detectado** e o do estado-**destino**
da transicao (ex.: motorista em `ENCAMINHADA_PARA_LAMINACAO` assina e a
prova vai para `COM_MOTORISTA_IDA_LAMINACAO` → contexto "ida laminacao").

### 5.3.4 Provas legacy v3.0

Deteccao: `prova.rota === null` OU `prova.rota IN {"PADRAO","DIRETA"}`. A
maquina v3.0 tem 9 estados; o `/scan` calcula `transicoes_permitidas`
corretamente para elas. O `AssinaturaModal` recuperado e agnostico de rota
— funciona identico para legacy. **Cenario 7 atendido pelo mesmo codigo.**

### 5.3.5 Estados terminais

`RECEBIDA_PELA_CLICHERIA` e `CANCELADA` — `pode_cancelar()` retorna False,
`transicoes_permitidas` sempre vazio. Tratamento: Decisao 8.

---

## 5.4 Cenarios obrigatorios (10)

Todos exigem render no browser em staging + screenshots (→ `visual-guide.md`
no Gate 2). Backend local; provas-fixture criadas conforme R-6.

| # | Cenario | Comportamento esperado | Criterio de validacao |
|---|---|---|---|
| 1 | **Motorista · QR · assina · movimenta** | Escaneia prova em `ENCAMINHADA_PARA_LAMINACAO` (rota Lam. Matriz). Modal abre automatico exibindo rota + contexto "→ Laminacao". Assina → prova vai a `COM_MOTORISTA_IDA_LAMINACAO`. Feedback de sucesso. | Status muda; movimentacao gravada; modal ≤500ms apos identificacao. |
| 2 | **Vendedor · Aprovar · assina · movimenta** | Escaneia prova em `ENCAMINHADA_PARA_O_VENDEDOR` (rota Filial). UI mostra seletor Aprovar/Reprovar. Aprovar → modal de assinatura → `APROVADA_PELO_VENDEDOR`. | Seletor presente; status muda para Aprovada. |
| 3 | **Vendedor · Reprovar + motivo · assina** | Mesmo que #2, escolhe Reprovar. Campo de motivo obrigatorio aparece. Preenche + assina → `REPROVADA_PELO_VENDEDOR` com motivo gravado. | Motivo obrigatorio; status Reprovada; motivo no banco. |
| 4 | **Ator errado · mensagem generica (RN-014)** | Vendedor escaneia prova em `COM_MOTORISTA_IDA_LAMINACAO`. Sistema retorna mensagem **identica** a "prova nao encontrada". Modal NAO abre. | Comparacao **byte a byte** da mensagem renderizada vs cenario de prova inexistente. |
| 5 | **Digitacao manual (C19) + assinatura** | Motorista usa tab Manual, digita `PRV-AAAA-MM-NNNNNN`. Apos identificacao, mesmo fluxo do #1. | Fluxo identico ao #1 a partir da identificacao. |
| 6 | **Falha de rede ao submeter** | Assina, submissao falha. Erro exibido + opcao retry; assinatura preservada (modal aberto, canvas intacto). Retry OK → movimenta. | Erro claro; retry funciona; assinatura nao perdida. |
| 7 | **Prova legacy v3.0 (`rota IS NULL`)** | Escaneia prova legacy. Maquina v3.0 calcula transicoes; assinatura compativel; movimenta conforme v3.0. | Coexistencia preservada; modal funciona identico. |
| 8 | **Prova em estado terminal** | Escaneia prova `RECEBIDA_PELA_CLICHERIA`. Mensagem "Esta prova ja foi concluida". Modal NAO abre. | Mensagem informativa; sem assinatura habilitada. |
| 9 | **Race condition** | Motorista A escaneia; Motorista B movimenta antes; A submete → backend **409**. UI mostra feedback claro + refresh do estado. | 409 tratado; mensagem clara; nao corrompe. |
| 10 | **Clicheria · recebimento final** | Operador escaneia prova em `COM_MOTORISTA_ENTREGA_FINAL`. Assina → `RECEBIDA_PELA_CLICHERIA` (terminal). Feedback de finalizacao. | Status terminal; feedback indica conclusao. |

---

## 5.5 Decisoes de design propostas (escalacao humana — 11 decisoes)

> Cada decisao tem opcoes + analise + **recomendacao tecnica**. Aguardam
> resposta humana antes do Gate 2.

### Decisao 1 — Apresentacao da tela de assinatura (CRITICA)

- **(i) Modal** sobre a pagina `/escanear`.
  - Pro: fidelidade a arqueologia (era modal); RF-028 "automaticamente";
    mantem contexto; menos toques (RNF-009 ≤3); sem troca de rota.
  - Contra: menos espaco vertical em mobile (mitigado no C23).
- **(ii) Pagina dedicada** `/assinar/[provaId]`.
  - Pro: mais espaco; deep-link.
  - Contra: troca de pagina; mais ceremonia; o `escanear/page.tsx` teria de
    persistir o `ScanResponse` (state cross-route).
- **(iii) Drawer/bottom-sheet.**
  - Pro: mobile-friendly.
  - Contra: menos espaco vertical; diverge da arqueologia.

**Recomendacao: (i) Modal.** Fidelidade total a arqueologia, RF-028
satisfeito (modal abre automatico), zero rota nova. O modal recuperado ja e
mobile-responsive (canvas dimensionado por `ResizeObserver`).

### Decisao 2 — Mecanismo de captura

Arqueologia **confirma:** `react-signature-canvas` (`^1.0.7`, canvas de
tracado dedo/mouse → PNG base64). O pacote segue instalado.

**Recomendacao: reusar `react-signature-canvas`.** Confirma o "vamos usar o
mesmo que ja estavamos fazendo"; zero dependencia nova.

### Decisao 3 — Fluxo Vendedor (Aprovar vs Reprovar)

- **(i) Seletor** (2 botoes Aprovar/Reprovar) antes do modal de assinatura.
- (ii) Duas telas separadas.
- (iii) Toggle dentro do modal.

RF-008 v4.0: "apresentar ao vendedor duas opcoes: Aprovar ou Reprovar". A
arqueologia listava `transicoes_permitidas` como botoes (efetivamente um
seletor).

**Recomendacao: (i) Seletor.** Para o vendedor em `RETIRADA_PELO_VENDEDOR` /
`ENCAMINHADA_PARA_O_VENDEDOR`, exibir 2 botoes; o escolhido abre o modal
(Reprovar inclui o campo de motivo).

### Decisao 4 — Captura do motivo da reprovacao

Sub-questoes: tamanho minimo? lista pre-definida vs texto livre? antes/depois
da assinatura?

Arqueologia + backend: `textarea` livre, `maxLength=1000`, `required`, **sem
minimo**, capturado **no mesmo modal** que a assinatura.

**Recomendacao:** texto livre, `maxLength=1000` (espelho do backend), **sem
minimo rigido** (ou minimo de sanidade de 3 chars), capturado **no mesmo
modal** da assinatura. Lista pre-definida = escopo extra desnecessario.
*(Confirmar com o solicitante se deseja um minimo — ex.: 10 chars.)*

### Decisao 5 — Tratamento de falha de rede

- (i) Retry automatico com backoff.
- (ii) Preservacao local (localStorage/IndexedDB) + retry manual.
- (iii) Combinacao.
- (iv) Rejeicao + re-assinatura.

Arqueologia: na falha (nao-409), o original mantinha o modal aberto no estado
`signing` — o canvas **permanece montado, assinatura preservada in-memory** —
e o usuario reclica Confirmar.

**Recomendacao: (iii) pragmatico** — manter o modal aberto na falha, exibir
erro + botao "Tentar novamente", **assinatura preservada in-memory** (canvas
nao desmonta). Persistencia em `localStorage` cross-reload e provavelmente
overkill para uma imagem de assinatura (o usuario re-assinaria de qualquer
forma) — **disponivel se o solicitante exigir robustez offline total** para
o motorista em campo. *(Decisao do solicitante: in-memory basta, ou exige
localStorage?)*

### Decisao 6 — Mensagem anti-enumeracao (ator errado)

- **(i) "Prova nao encontrada."** — identica ao 404 generico e ao
  `mensagemFinal` do C19.
- (ii) "Nao foi possivel processar esta prova no momento."
- (iii) "Acesso negado" — **viola** RN-014, descartar.

**Recomendacao: (i).** Alinhamento estrito a RN-014 e a defesa de
anti-enumeracao ja existente (C19 / 404 do backend). Mesma string,
byte a byte.

### Decisao 7 — Comportamento pos-sucesso

- **(i) Feedback de sucesso + volta ao scanner** pronto para a proxima.
- (ii) Tela de confirmacao com novo estado.
- (iii) Redirect para `/provas/[id]`.

Arqueologia: `DoneView` (card de sucesso inline) + botao "Escanear proxima"
— ficava no scanner.

**Recomendacao: (i) para todos os perfis.** Motorista/clicheria escaneiam
varias em sequencia; voltar ao scanner e mais eficiente (RNF-009). Exibir
card de sucesso inline (padrao `DoneView`) com o novo estado + um link
opcional "Ver prova" → `/provas/[id]`. *(Se o solicitante preferir o
redirect (iii) para o vendedor, e simples diferenciar por perfil — mas (i)
uniforme e mais previsivel.)*

### Decisao 8 — Prova em estado terminal

- **(i) Mensagem informativa** ("Esta prova ja foi concluida") + Voltar.
- (ii) Mensagem + ver detalhe (somente leitura).
- (iii) Mensagem generica (esconde que e terminal).

**Interacao com RN-014:** RN-014 governa "ator errado em prova **ativa**".
Provas terminais que o usuario escaneia ja estao **no escopo de visibilidade
dele** (aparecem na listagem) — revelar "concluida" **nao vaza informacao
nova**. Enumeracao de provas fora-de-escopo continua coberta pelo 404. A
distincao terminal vs ator-errado e feita por `prova.status` no `ScanResponse`.

**Recomendacao: (i)** — mensagem "Esta prova ja foi concluida
(`STATUS_LABELS[status]`)". Seguro perante RN-014 pelo raciocinio acima.
*(Ponto que merece confirmacao explicita do solicitante por tocar regra de
seguranca.)*

### Decisao 9 — Capturar geolocalizacao com a assinatura?

- (i) Sempre. (ii) Com consentimento. **(iii) Nao.**

A tabela `movimentacoes` **nao tem coluna de geolocalizacao** (confirmado via
MCP: id/prova_id/usuario_id/status_anterior/status_novo/assinatura_digital/
motivo_reprovacao/ciclo/rota_no_momento/created_at). Capturar geo exigiria
**migration de backend** — **proibido pelo escopo do C22** ("zero alteracao
no backend"). A arqueologia confirma: o original nao capturava geo.

**Recomendacao: (iii) Nao.** Fora de escopo, sem coluna no banco, sem
precedente, e evita questao de LGPD. Se desejado no futuro, e um componente
proprio com migration.

### Decisao 10 — Integracao com C20 (REFORMULADA — C20 NAO EXISTE)

O C20 (camada de animacoes) **nao foi implementado** (D-1). As opcoes
originais do prompt (reusar `<MotionModal>` / `<PageTransition>` / toasts)
**sao inviaveis**. Opcoes reais:

- **(a) `framer-motion` direto** — ja e dependencia (`^12.38.0`), usado em
  todo o app. Modal entra com `scale 0.96→1 + fade` (~200ms); `prefers-
  reduced-motion` respeitado via `useReducedMotion()` **do proprio
  framer-motion** (nao precisa de hook do C20).
- (b) Construir um `<MotionModal>` local minimo (antecipa parte do C20).
- (c) Sem animacao / instantaneo.

Para feedback (sucesso/erro): **nao ha sistema de toasts**. O
`AuthToast.tsx` existente e especifico de redirect de RBAC. Opcoes:
feedback **inline** (padrao `DoneView`/`ErrorView` da arqueologia) ou um
toast minimo local.

**Recomendacao: (a) `framer-motion` direto + feedback inline.** E o caminho
de menor atrito, consistente com o resto do app, sem inventar abstracao que
o C20 deveria prover. **Nao** construir o C20 dentro do C22 (escopo).
*(Decisao do solicitante: aceitar (a), ou autorizar (b) um modal-motion
local reusavel?)*

### Decisao 11 — Cobertura de testes (com sub-decisao de ferramentas)

- **(i) Minima (DoD global 80%)** — unitarios + integracao + E2E dos 10
  cenarios.
- (ii) Estendida (stress, regressao visual).
- (iii) Minima agora + estendida depois.

**Sub-decisao critica (D-6):** Playwright e axe-core **nao estao
instalados**. O DAT Secao 3 e os criterios 17/22 do prompt pedem ambos. O
projeto adota historicamente "Vitest minimo + smoke E2E manual" (D-13).
Duas execucoes possiveis para o escopo (i):

- **Opcao A:** instalar `@playwright/test` + `@axe-core/playwright` (novas
  dev-deps) e automatizar os 10 cenarios + axe.
- **Opcao B:** seguir a cultura do projeto — Vitest para logica pura
  (helpers, anti-enumeracao byte a byte, validacao de perfil) + **smoke E2E
  manual** dos 10 cenarios via `smoke-validation.md` (Mario executa) + axe
  via DevTools manual. Sem dep nova.

**Recomendacao: escopo (i), execucao Opcao B.** Coerente com D-13 e com
todas as waves anteriores; sem dep nova; o Vitest cobre a logica testavel
(meta ≥80% nos helpers/hooks novos); os 10 cenarios viram checklist de smoke
manual. *(Se o solicitante exigir E2E automatizado real, autorizar Opcao A
como dependencia nova — decisao explicita necessaria.)*

---

## 5.6 Plano de arquitetura

### 5.6.1 Estrutura de arquivos proposta

```
frontend/src/components/assinatura/
  AssinaturaModal.tsx          # modal principal (Decisao 1) — base verbatim do 6add246
  CapturaAssinatura.tsx        # wrapper do react-signature-canvas (canvas + ResizeObserver)
  SeletorAprovarReprovar.tsx   # vendedor — 2 botoes (Decisao 3)
  ContextoMovimentacao.tsx     # exibe rota + transicao + contexto do motorista
  FeedbackResultado.tsx        # sucesso/erro inline (base DoneView/ErrorView)
  assinatura.module.css        # CSS Module (migra classes verbatim da arqueologia §6.5)
  __tests__/
frontend/src/hooks/
  useExecutarTransicao.ts      # JA EXISTE (orfao) — reativar, zero recriacao
  useAssinaturaFlow.ts         # [novo] orquestra: ScanResponse -> validar -> abrir modal -> submit
frontend/src/lib/assinatura/
  helpers.ts                   # labels v4.0, deteccao terminal/ator-errado, anti-enum
  types.ts                     # tipos compartilhados do fluxo
```

Hooks `usePreservacaoLocalAssinatura` so se a Decisao 5 escolher
localStorage. Reuso direto: `useFocusTrap`, `identificacao-prova.ts`,
`useCurrentUser`, `useAuthorization`, `STATUS_LABELS`/`ROTA_LABELS`/
`contextoMotorista` de `prova.ts`.

### 5.6.2 Integracao com C10 e C19 (refactor coordenado leve — autorizado)

**Ponto exato de integracao:** `frontend/src/app/(dashboard)/escanear/page.tsx`.
Hoje, apos identificacao bem-sucedida, **ambos** os caminhos fazem:

```tsx
// linha 133 (camera) e linha 170 (manual):
if (result.tipo === "sucesso") {
  router.push(`/provas/${result.prova.prova.id}`);   // <- C22 substitui isto
  return;
}
```

O C22 substitui essas 2 chamadas por: passar o `ScanResponse`
(`result.prova`) ao fluxo de assinatura. Decisao do C22:
`transicoes_permitidas` nao-vazio → abre `AssinaturaModal`; vazio → seta o
estado de erro da pagina com mensagem generica/terminal. **Sem tocar a
logica interna de identificacao** (camera, html5-qrcode, mascara C19) — so
o callback de conclusao. Conforme prompt §1: "Integracao leve com C10 e C19:
adicionar hook ou callback... Sem modificar a logica interna."

### 5.6.3 Integracao com animacoes (ver Decisao 10)

Sem C20: `framer-motion` direto para o modal (`AnimatePresence` +
`motion.div` scale+fade); `useReducedMotion()` do framer-motion para
`prefers-reduced-motion` (RN-012/RNF-010 — item da DoD global). Feedback
inline (sem toast system).

---

## 5.7 Plano de testes

| Camada | Foco | Ferramenta | Meta |
|---|---|---|---|
| Unitarios | `lib/assinatura/helpers.ts` (deteccao de terminal/ator-errado, labels v4.0, anti-enum byte a byte), validacao de perfil | Vitest (`environment: node`) | ≥80% nos arquivos novos |
| Integracao | Fluxo `ScanResponse → decisao → modal → submit` com `useExecutarTransicao` mockado; 4 perfis × estados que correspondem vs nao-correspondem | Vitest | Fluxo completo coberto |
| Anti-enumeracao | Mensagem para ator-errado **===** mensagem para prova inexistente (igualdade de string) | Vitest | Invariante RN-014 |
| Race condition | 409 → feedback + refresh | Vitest (mock) | Cenario 9 |
| Falha de rede | Erro de submit → retry, assinatura preservada | Vitest (mock) | Cenario 6 |
| E2E (10 cenarios) | Secao 5.4 | **Opcao B (recomendada):** smoke manual `smoke-validation.md`. **Opcao A:** Playwright (dep nova) | Decisao 11 |
| a11y | `role="dialog"`/`aria-modal`, focus trap, teclado, axe | axe manual (Opcao B) ou `@axe-core/playwright` (Opcao A) | Sem violacao critica |

### 5.8 Plano de testes de regressao

Garantir que o C22 nao quebra entregas anteriores:

- **C10 (Scanner):** camera continua identificando; `identificacao-prova.ts`
  intacto.
- **C19 (Fallback manual):** digitacao manual + mascara continuam; tab
  Manual preservada.
- **C11 (Maquina de estados):** `executar_transicao` facade + endpoint
  intactos (zero touch backend).
- **C06/C08/C12/C16:** criacao, detalhe, timeline, relatorios renderizam
  (C22 nao toca esses arquivos).
- **Wave 1 RBAC:** `useAuthorization`, middleware, RLS preservados (so
  consumo).
- **Backend de assinatura:** `git diff` em `backend/` deve retornar VAZIO.
- **Validacao tecnica:** `npx tsc --noEmit` exit 0; `npx next build` 13/13;
  `npx vitest run` sem regressao; advisors MCP sem novos alertas.

---

## 5.9 Riscos e pontos de atencao

| ID | Risco | Mitigacao |
|---|---|---|
| R-1 | **C20 inexistente** — nao ha `<MotionModal>`/toasts/`useReducedMotion` para reusar. | Decisao 10 reformulada: `framer-motion` direto + feedback inline. Sem inventar o C20 dentro do C22. |
| R-2 | **Anti-enumeracao quebrada** — distinguir ator-errado de inexistente vaza informacao (RN-014). | Uniformizar mensagem (Decisao 6); teste Vitest de igualdade byte a byte; nunca exibir texto cru de 422/`AtorNaoAutorizadoError`. |
| R-3 | **Backend 422 vaza setores permitidos** — `AtorNaoAutorizadoError` lista perfis. | C22 so abre assinatura com `transicoes_permitidas` nao-vazio; mapear 422 inesperado para mensagem generica. |
| R-4 | **Race condition** — dois atores simultaneos. | Backend ja serializa com `FOR UPDATE` + retorna 409; C22 trata 409 com feedback claro + refresh (Cenario 9). |
| R-5 | **Provas legacy v3.0** — 16/20 provas sao legacy (C21 nao rodou). | `AssinaturaModal` e agnostico de rota; `/scan` calcula transicoes legacy; teste dedicado (Cenario 7). |
| R-6 | **Poucas provas em estado acionavel em producao** — 8 CRIADA, 1 REPROVADA, 9 CANCELADA, 2 RECEBIDA; **zero** em estados de motorista/clicheria/vendedor-mid-flow. | O smoke E2E exige **criar provas-fixture** nos estados-alvo (admin cria + transiciona via backend local). Documentar no `smoke-validation.md`. |
| R-7 | **Railway de producao fora do ar** (D-4). | Escalar ao Mario (redeploy). C22 desenvolve/testa contra backend local — nao bloqueia. |
| R-8 | **Playwright/axe ausentes** (D-6). | Decisao 11 — Opcao B (smoke manual, sem dep nova) recomendada; Opcao A precisa de aprovacao. |
| R-9 | **`globals.css` com alteracoes nao-commitadas do Mario.** | Nao tocar `globals.css`. Confirmar tokens `--radius-sm`/`--fs-*`/`--font-family` no inicio do Gate 2 (a arqueologia ja confirmou os principais). |
| R-10 | **Labels v4.0** — `ACTION_LABELS` recuperado e vocabulario v3.0 (9 estados). | Estender para os 7 estados v4.0 antes de usar; teste de exaustividade. |
| R-11 | **Performance <500ms** (RNF-002/criterio 16). | Modal sem fetch extra (consome o `ScanResponse` ja em maos); medir no smoke. |
| R-12 | **Mobile** — RNF-013 pede touch targets 44px na tela de assinatura. | C22 entrega "mobile-ready" (canvas responsivo herdado); polimento fino e o C23. Botoes ≥44px ja no C22. |
| R-13 | **Integracao fragil com C10/C19** — callback mal-feito quebra scanner. | Substituir apenas as 2 linhas de `router.push`; testes de regressao de identificacao. |

---

## 5.10 Entregavel do Gate 1

- `docs/wave8-v5-c22/arqueologia.md` — recuperacao de codigo (verbatim).
- `docs/wave8-v5-c22/analysis.md` — este documento.
- Branch: `wave8-v5-c22/analysis` (a partir de `development`, sem merge).
- Commit: `docs(wave8-v5/c22): arqueologia + analise read-only + proposta pre-execucao`.

**O Gate 2 NAO inicia** antes de: (a) respostas humanas as 11 decisoes de
§5.5; (b) a string `AUTORIZADO GATE 2 — WAVE 8 v5.0 / C22`.

---

## Anexo A — Sintese executiva das divergencias (para decisao rapida)

1. **C20 e C21 nao existem** no codigo (so no Backlog). C22 nao depende
   deles — prossegue com `framer-motion` direto.
2. **v4.0 nao esta em `main`**; esta em `development`. Dependencias reais do
   C22 (C05/06/10/19/11) prontas e mergeadas.
3. **Railway de producao fora do ar** — infra, nao codigo. Escalar.
4. **Playwright/axe ausentes** — Decisao 11 trata.
5. **Arqueologia 100% bem-sucedida** — UI recuperavel verbatim; backend
   intacto; reativacao viavel sem reescrita estrutural.
6. **Recomendacao:** prosseguir com o C22 apos as 11 decisoes — ele corrige
   um bug de producao (nenhuma prova pode ser movimentada hoje).

**Fim do Gate 1.**

---

## Apendice — Execução (Gate 2)

**Data:** 2026-05-22 · **Branch:** `wave8-v5/componente-22` (a partir de
`wave8-v5-c22/analysis`) · **Autorizacao:** `AUTORIZADO GATE 2 — WAVE 8
v5.0 / C22` + respostas as 11 decisoes + Q1/Q2 (Mario, 2026-05-22).

### A.1 Decisoes finais

Consolidadas em ADR-163 (11 decisoes) + ADR-164 (ator-errado in-scope).
Resumo: D1 Modal · D2 `react-signature-canvas` · D3 seletor
Aprovar/Reprovar · D4 motivo sem minimo · D5 retry in-memory · D6
ator-errado -> `/provas/[id]` · D7 pos-sucesso -> `/provas/[id]` · D8
subsumido por D6 · D9 sem geo · D10 `framer-motion` direto · D11 Opcao B ·
Q1 abrir detalhe · Q2 modal automatico. C20 e C21 mantidos **pendentes**
por decisao do Mario — o C22 prossegue sem eles.

### A.2 Diferencas entre o proposto (Gate 1 §5.6.1) e o realizado

| Proposto no Gate 1 | Realizado | Motivo |
|---|---|---|
| `components/assinatura/` com ~8 arquivos (Seletor, CampoMotivo, ContextoMotorista, ConfirmacaoRecebimento, FeedbackSucesso, FeedbackErro, ...) | 3 arquivos: `AssinaturaModal.tsx` (sub-componentes `CabecalhoContexto`/`ResultadoView` inline), `CapturaAssinatura.tsx`, `assinatura.module.css` | O fluxo e data-driven (uma regra unica sobre `transicoes_permitidas`/`motivo_obrigatorio_em`); componentes por-perfil separados seriam abstracao desnecessaria. O modal da arqueologia tambem era um arquivo unico. |
| `lib/assinatura/types.ts` | Nao criado | Os tipos necessarios ja vivem em `prova.ts` (`ScanResponse`, `StatusProva`, etc.). |
| `hooks/useAssinaturaFlow.ts` | Nao criado | A orquestracao "abrir modal vs navegar" e a `useCallback` `handleIdentificada` (~6 linhas) no `escanear/page.tsx`. |
| `usePreservacaoLocalAssinatura` | Nao criado | D5 = retry in-memory (o canvas nao desmonta entre "assinando" e "enviando"). Sem `localStorage`. |
| D6/D7/D8 como decisoes separadas | Unificadas pela regra do Mario (Q1/ADR-164): scan -> ator certo assina; senao `/provas/[id]` | Esclarecimento de fluxo do Mario na autorizacao do Gate 2. |

### A.3 Arquivos entregues

**Novos:** `lib/assinatura/helpers.ts` · `lib/assinatura/__tests__/helpers.test.ts`
· `components/assinatura/AssinaturaModal.tsx` ·
`components/assinatura/CapturaAssinatura.tsx` ·
`components/assinatura/assinatura.module.css`.
**Modificados:** `app/(dashboard)/escanear/page.tsx` (integracao leve — 2
pontos pos-identificacao) · `hooks/useExecutarTransicao.ts` (reativado +
campo `status`).
**Docs:** `CHANGELOG.md` · `DECISIONS.md` (ADR-163/164) · `CLAUDE.md` ·
este `analysis.md` · `visual-guide.md` · `smoke-validation.md`.

### A.4 Validacao tecnica

- `npx tsc --noEmit`: exit 0.
- `npx next build`: 13/13 paginas. `/escanear` em 15.9 kB / 220 kB
  (era 8.31 kB / 210 kB — `react-signature-canvas` entra no bundle).
- `npx next lint`: 0 warnings, 0 errors.
- `npx vitest run`: **222 testes** (205 + 17 novos em `helpers.test.ts`),
  0 regressao.
- Advisors MCP (security + performance): identicos ao baseline do Gate 1
  — esperado, o C22 nao toca o banco.

### A.5 Verificacao funcional — limitacao assumida

A verificacao **programatica** do modal no browser nao e viavel nesta
sessao: exige (a) backend FastAPI rodando localmente; (b) uma sessao
Supabase autenticada — sem credenciais de usuario disponiveis; (c)
provas-fixture em estados acionaveis (R-6 — em producao so ha provas
CRIADA / terminais; nenhuma em estado de motorista/clicheria/vendedor
mid-flow). O deploy Railway esta fora do ar (D-4). Conforme a Decisao
D11 (Opcao B) e a cultura do projeto (D-13), a verificacao funcional dos
10 cenarios e o **smoke E2E manual** — checklist em `smoke-validation.md`.
A correcao do codigo esta coberta por tsc + build + lint + 222 testes.

### A.6 Pendencias

Smoke E2E manual (Mario, `smoke-validation.md`) · auditoria senior
independente · screenshots para o `visual-guide.md` · redeploy do backend
no Railway · heranca da Wave 3 (rate limit C19 — ADR-145; CI/CD — ADR-156).

**Fim do Apendice de Execucao.**
