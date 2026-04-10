# Wave 3 — Lote A — Analise de Implementacao

**Escopo:** Componentes 10 e 11 do Backlog v3.0 (apenas).
**Autor:** Claude Code — Wave 3 planning.
**Data:** 2026-04-10 (revisao 2 apos revalidacao MCP do estado real).
**Status:** Aguardando GO LOTE A para execucao.

Este documento e o produto da **Fase 3** do plano da Wave 3. Ele nao contem
codigo — apenas o desenho que sera usado como contrato para os sub-blocos
subsequentes. Depois do seu GO, cada sub-bloco sera implementado, commitado
e testado em sequencia, com update incremental de `CHANGELOG.md` e
`DECISIONS.md`.

**Fora do escopo deste documento:** Componentes 12 (Timeline), 13
(Cancelamento) e 14 (Reinicio de Ciclo). Eles aparecem apenas na secao 3
("Interface com Componentes 12/13/14") como contratos a expor.

**Historico de revisoes deste documento:**
- **Rev 1** (inicial) — 1683 linhas, plano completo cobrindo sub-blocos A.1 a
  A.6. Escrito assumindo `provas_digitais` = 11 em estado `CRIADA`/`rota=NULL`
  (snapshot pre-cancelamento de seeds de teste) e "2 admins ativos" conforme
  CLAUDE.md.
- **Rev 2** (atual) — revalidacao contra o estado real via MCP Supabase:
  - `provas_digitais`: 5 `CRIADA`/rota=NULL + 6 `CANCELADA` (3 com rota
    `PADRAO`/`DIRETA` pre-persistida em seeds de teste antigos). Correcao em
    §3.4 e §4.3.
  - Usuarios ativos: 3 (nao 2) — os 2 admins STUDIO + `Mario Souza`
    VENDEDOR **FILIAL**. Unico vendedor cadastrado e Filial, nao ha vendedor
    MATRIZ. Impacto no smoke E2E do sub-bloco A.6 (§9.3 P1 e §10.A.6) — exige
    cadastro previo de vendedor MATRIZ de teste.
  - Validacao dos helpers backend (`_scoping_filter`,
    `_carregar_prova_com_scoping`, `_determinar_rota_projetada`,
    `_build_prova_response`, `parse_prova_id`) contra `provas.py` atual —
    todos os helpers existem e tem as assinaturas que o plano assume.
  - `_carregar_prova_com_scoping` hoje retorna tupla de **4 elementos**
    `(prova, vendedor_nome, vendedor_localizacao, vendedor_setor)` (F05 da
    auditoria Wave 2, Sessao 22). Ver §2.3.
  - Estado do banco: alembic_version=009, 11 policies, 30 indexes, 0 linhas
    em `movimentacoes` — conforme assumido pelo plano.

---

## 1. Escopo exato

### 1.1 Componente 10 — Leitura de QR Code via Camera

**Referencia Backlog (linha do C10):**
> html5-qrcode — permissao de camera — decode do ID da prova.
> Must Have. Depende de C06. "E o mecanismo de identidade. O QR Code conecta
> o objeto fisico (prova impressa + etiqueta) ao registro digital."

**Requisitos funcionais atendidos:**
- **RF-004** — "cameara integrada na interface web que permita ao usuario
  escanear o QR Code da prova digital diretamente pelo sistema, sem
  necessidade de aplicativo externo".
- **RF-005** — "ao escanear, identificar automaticamente o usuario logado,
  validar seu perfil e exibir a tela de assinatura digital para confirmar
  a movimentacao para a proxima etapa do fluxo".
- Parte de **RF-006** — "registrar automaticamente o usuario responsavel,
  data/hora e novo status a cada movimentacao" (a parte de RF-006 que o
  C10 cobre e apenas o *inicio* do fluxo).

**Requisitos nao-funcionais atendidos:**
- **RNF-002** — "leitura do QR Code pela camera integrada e a exibicao da
  tela de assinatura devem ocorrer em no maximo 2 segundos".
- **RNF-007** — "fluxo de abrir camera, escanear, assinar e confirmar em
  no maximo 3 toques/cliques".
- **RNF-006** — responsivo em Chrome, Firefox, Edge e Safari (5+ pol).

**Historias de usuario (HUs):**
- **US-002** — "Como vendedor, eu quero escanear o QR Code da prova pela
  camera integrada para que o sistema me identifique automaticamente e me
  direcione a tela de assinatura digital".

**Criterios de aceitacao (de US-002, transcritos literalmente):**
1. A camera abre diretamente no sistema, sem app externo.
2. O sistema identifica o vendedor logado automaticamente ao escanear.
3. Apos a leitura, a tela de assinatura digital e exibida.
4. Apos assinar e confirmar, o status muda para "Retirada pelo vendedor"
   com data/hora e nome do vendedor. *(Este 4o criterio atravessa para o
   C11 — "assinar e confirmar" e do C11, mas o scan que alimenta a tela de
   assinatura e do C10.)*

**Definition of Done (global, todos os 8 itens do Backlog aplicam):**
1. Code review.
2. Testes unitarios da logica de negocio com cobertura >= 80%.
3. Testes de integracao passando em staging.
4. Migrations aplicadas e versionadas (N/A — nenhuma migration Alembic
   para este componente, ver secao 4).
5. Funcionalidade validada contra os criterios de aceitacao da US-002.
6. Sem erros no console do browser / logs do backend.
7. Documentacao interna atualizada (comentarios + CHANGELOG + DECISIONS).
8. Politicas RLS relacionadas versionadas em `/migrations/rls/` (aplicavel
   para o C11 — ver secao 4).

### 1.2 Componente 11 — Assinatura Digital e Transicao de Status

**Referencia Backlog (linha do C11):**
> react-signature-canvas — maquina de estados (Pydantic v2) — log imutavel
> — suporte a aprovacao/reprovacao — roteamento por localizacao.
> Must Have. Depende de C10 e C05. "A assinatura e o comprovante de cada
> movimentacao (RN-003). A maquina de estados implementa as tres rotas da
> Matriz de Transicoes (Secao 5 dos Requisitos): rota padrao (Matriz),
> rota direta (Filial) e reprovacao. O roteamento automatico por
> localizacao do vendedor (RN-007) e resolvido neste componente. Motivo
> obrigatorio na reprovacao (RF-007)."

**Requisitos funcionais atendidos:**
- **RF-005** — identificacao automatica do usuario logado + exibicao da
  tela de assinatura.
- **RF-006** — "registrar automaticamente usuario responsavel, data/hora e
  novo status a cada movimentacao. O QR Code e o identificador de
  autenticidade da acao. A transicao ocorre somente apos a assinatura
  digital e a confirmacao explicita do usuario".
- **RF-007** — reprovacao pelo vendedor com **motivo obrigatorio** no
  status `RETIRADA_PELO_VENDEDOR`, gerando `REPROVADA_PELO_VENDEDOR`.
- **RF-009** — roteamento automatico na aprovacao:
  - (a) Vendedor Matriz — rota padrao (Matriz -> 3Studio -> Motorista ->
    Clicheria). Na Wave 3, isto significa persistir `provas_digitais.rota
    = 'PADRAO'` no momento da transicao `APROVADA_PELO_VENDEDOR`.
  - (b) Vendedor Filial — rota direta (Filial -> Clicheria). Persiste
    `rota = 'DIRETA'`.

**Requisitos nao-funcionais atendidos:**
- **RNF-005** — log de auditoria completo e imutavel de todas as
  movimentacoes (via tabela `movimentacoes` + `audit_logs`, ambas com
  trigger de imutabilidade).
- **RNF-009** — "codigo deve permitir adicao de novas rotas e transicoes
  sem refatoracao estrutural" (atendido pelo desenho tabela-driven do
  `state_machine.py`, ADR-040).

**Regras de negocio atendidas:**
- **RN-002** — transicoes seguem a Matriz Secao 5 (ja codificada em
  `state_machine.TRANSICOES`).
- **RN-003** — "toda movimentacao de status exige assinatura digital do
  usuario responsavel, registrando nome, setor, data e hora".
- **RN-004** — "apenas o usuario do setor e localizacao autorizados para
  a proxima etapa pode realizar a transicao" (ja codificada em
  `state_machine.ATORES_POR_TRANSICAO` + `validar_transicao`).
- **RN-007** — rota determinada pela localizacao do vendedor na
  aprovacao; **nao e possivel alterar a rota apos confirmacao** (ja
  codificada em `state_machine.determinar_rota`, ADR-042 — a Wave 3
  persiste).

**Historias de usuario cobertas (transicoes que o Lote A implementa):**
Estas sao as **unicas** transicoes que o Lote A vai permitir via o
endpoint de transicao. As demais (cancelamento, reinicio de ciclo) ficam
explicitamente fora e sao tratadas no Lote C.

| # | HU | De | Para | Ator autorizado | Exige motivo? |
|---|---|---|---|---|---|
| 1 | US-002 | `CRIADA` | `RETIRADA_PELO_VENDEDOR` | `VENDEDOR` (qualquer localizacao) | nao |
| 2 | US-003 | `RETIRADA_PELO_VENDEDOR` | `APROVADA_PELO_VENDEDOR` | `VENDEDOR` (qualquer localizacao) | nao |
| 3 | US-004 | `RETIRADA_PELO_VENDEDOR` | `REPROVADA_PELO_VENDEDOR` | `VENDEDOR` (qualquer localizacao) | **SIM** (RF-007) |
| 4 | US-005 | `APROVADA_PELO_VENDEDOR` | `DE_VOLTA_3STUDIO` | `VENDEDOR` **com `localizacao = MATRIZ`** | nao |
| 5 | US-006 | `APROVADA_PELO_VENDEDOR` | `ENCAMINHADA_A_CLICHERIA` | `VENDEDOR` **com `localizacao = FILIAL`** | nao |
| 6 | US-007 | `DE_VOLTA_3STUDIO` | `COM_MOTORISTA` | `STUDIO` (ou `is_admin`) | nao |
| 7 | US-008 | `COM_MOTORISTA` | `ENVIADA_PARA_CLICHERIA` | `MOTORISTA` | nao |
| 8 | US-009a | `ENVIADA_PARA_CLICHERIA` | `RECEBIDA_PELA_CLICHERIA` | `CLICHERIA` | nao |
| 9 | US-009b | `ENCAMINHADA_A_CLICHERIA` | `RECEBIDA_PELA_CLICHERIA` | `CLICHERIA` | nao |

> **Observacao critica sobre #4 e #5:** a `state_machine.TRANSICOES` atual
> permite `APROVADA_PELO_VENDEDOR -> DE_VOLTA_3STUDIO` e
> `APROVADA_PELO_VENDEDOR -> ENCAMINHADA_A_CLICHERIA` ambas para o setor
> `VENDEDOR`, mas nao distingue MATRIZ vs FILIAL. A distincao por
> localizacao e **regra de negocio do RN-007 + RF-009** e precisa ser
> aplicada no momento da execucao pelo `executar_transicao`. Ver secao 5
> para o contrato exato.

**Criterios de aceitacao (agregados das 8 HUs do Lote A):**
- US-002: "apos assinar e confirmar, o status muda para Retirada pelo
  vendedor com data/hora e nome do vendedor".
- US-003: "o vendedor so consegue aprovar provas no status Retirada pelo
  vendedor"; "o sistema apresenta as opcoes Aprovar e Reprovar"; "o
  sistema determina a rota automaticamente pela localizacao do vendedor";
  "status muda para Aprovada pelo vendedor".
- US-004: "o vendedor so consegue reprovar provas no status Retirada pelo
  vendedor"; "o campo de motivo e obrigatorio"; "status muda para
  Reprovada pelo vendedor"; "a prova fica visivel no dashboard como
  reprovada".
- US-005: "vendedor Matriz so consegue devolver provas no status Aprovada
  pelo vendedor com rota padrao"; "apos assinar e confirmar, status muda
  para De volta a 3Studio".
- US-006: "vendedor Filial so consegue encaminhar provas no status
  Aprovada pelo vendedor com rota direta".
- US-007: "3Studio so consegue realizar esta acao em provas no status De
  volta a 3Studio".
- US-008: "motorista so consegue realizar esta acao em provas no status
  Com Motorista".
- US-009: "a clicheria consegue realizar esta acao em provas no status
  Enviada para Clicheria ou Encaminhada a Clicheria".

**DoD global:** os mesmos 8 itens do C10, mais:
- Cobertura >= 80% em `state_machine.executar_transicao` + novos helpers
  de endpoint.
- Cobertura 100% nos novos handlers de transicao (padrao dos componentes
  Wave 2).
- Pelo menos 1 teste de integracao feliz por cada uma das 9 transicoes
  listadas acima, + testes de rejeicao para ator errado, transicao ilegal,
  motivo ausente na reprovacao, assinatura vazia, prova inexistente, QR
  payload invalido, localizacao errada em #4/#5.

---

## 2. Interface com Waves 0, 1 e 2

Esta secao enumera **o que sera consumido sem modificacao**. Qualquer
mudanca em Wave 0/1/2 fora dos helpers listados como "**CONSUMIR**" abaixo
e blocker — reporta em `WAVE3_BLOCKERS.md` antes de agir.

### 2.1 Banco de dados (Wave 0, alembic_version = 009)

**CONSUMIR (sem alterar schema):**
- **`public.provas_digitais`** — a WAVE 3 vai executar `UPDATE ... SET
  status, rota, updated_at` nas transicoes. A coluna `rota` (que estava
  NULL desde a criacao — ADR-042) **passa a ser populada na transicao
  `RETIRADA_PELO_VENDEDOR -> APROVADA_PELO_VENDEDOR`**. `ciclo_atual`
  permanece intocado no Lote A (so muda em C14). Nenhuma alteracao de
  coluna, constraint ou indice necessaria.
- **`public.movimentacoes`** — primeira vez que o sistema vai inserir
  linhas aqui. O schema esta pronto desde a Wave 0/migration 001 com o
  trigger `trg_movimentacoes_imutavel` ja ativo. Colunas utilizadas:
  - `id` (auto-gerado)
  - `prova_id` (FK)
  - `usuario_id` (FK — autor da transicao)
  - `status_anterior` (lido de `provas_digitais.status` antes do UPDATE)
  - `status_novo` (do request)
  - `assinatura_digital` (bytea, PNG decodificado do base64 do request)
  - `motivo_reprovacao` (text, obrigatorio quando status_novo =
    REPROVADA_PELO_VENDEDOR, NULL caso contrario)
  - `ciclo` (copiado de `provas_digitais.ciclo_atual` no momento)
  - `rota_no_momento` (copiado de `provas_digitais.rota` no momento;
    pode ser NULL para transicoes pre-aprovacao)
  - `created_at` (default `now()`)
- **`public.audit_logs`** — a cada transicao, 1 linha com
  `acao = "transitar_status"`. Trigger `trg_audit_logs_imutavel` ativo.
  Ja consumido pela Wave 2 em outras acoes — padrao estabelecido.
- **`public.usuarios`** — leitura do usuario atual via
  `get_current_user`. Nao alteramos nada.
- **`public.configuracoes_sistema`** — nao e consumida pelo Lote A.

**NAO alterar:**
- Nenhuma tabela existente precisa de nova coluna, nova constraint ou
  novo indice no Lote A. Verificado caso a caso — nenhuma query projetada
  precisa de indice que ja nao exista (ver secao 4).

### 2.2 RLS (policies existentes)

**CONSUMIR (sem alterar):**
- `pol_provas_select` em `provas_digitais` — cobre VENDEDOR proprio,
  MOTORISTA em `COM_MOTORISTA`, CLICHERIA em 3 status, admin. O endpoint
  `POST /scan` vai **reutilizar este padrao** via `_scoping_filter` +
  `_carregar_prova_com_scoping` (ADR-046 + ADR-049) para limitar
  visibilidade do scan a provas que o usuario ja poderia ver na listagem.
- `pol_provas_update` — hoje so admin. **Mantido assim** porque o backend
  roda com service_role e bypassa RLS por design (ADR-046). Wave 3
  continua executando UPDATE via service_role no mesmo padrao da Wave 2.
- `pol_movimentacoes_select` — hoje cobre admin + vendedor das proprias
  provas + autor. **Gap identificado na auditoria externa da Wave 2
  (F03 da Sessao 22) — nao cobre MOTORISTA e CLICHERIA**. Isso foi
  documentado como debito Wave 3 e sera endereado no sub-bloco A.5
  (ver secao 4.2).
- `pol_audit_select` — admin only. Nao tocamos.

**CRIAR (sub-bloco A.5):**
- Nova policy `pol_movimentacoes_insert` — admin-only (espelhando o
  padrao de `pol_provas_insert`). Isto e **defesa em profundidade** — o
  backend bypassa RLS via service_role, mas sem a policy de INSERT, um
  acesso direto via supabase-js client (se fosse autenticado como admin
  futuro) nao conseguiria inserir. Versionada em
  `backend/migrations/rls/006_movimentacoes_insert_and_select_extension.sql`.
- Expansao de `pol_movimentacoes_select` para cobrir MOTORISTA e
  CLICHERIA (F03 da Sessao 22). Idempotente — DROP IF EXISTS + CREATE.

### 2.3 Backend (helpers reutilizaveis)

**CONSUMIR sem alterar:**
- `app/api/deps.py`
  - `get_current_user` — verifica JWT + carrega Usuario + 403 se
    desativado.
  - `get_admin_user` — wrapper para `is_admin`.
  - `require_role(*setores)` — factory que restringe por setor.
    **Provavelmente nao usada** no Lote A — o endpoint de transicao
    aceita qualquer setor ativo e a validacao fina vem do
    `state_machine.validar_transicao`. Mas esta disponivel caso se
    prefira defesa em camadas.
- `app/services/state_machine.py`
  - `TRANSICOES`, `ATORES_POR_TRANSICAO` — tabelas ja completas.
  - `determinar_rota(vendedor)` — MATRIZ->PADRAO, FILIAL->DIRETA.
    **Reusada no handler de `APROVADA_PELO_VENDEDOR` para gravar
    `provas_digitais.rota`.**
  - `validar_transicao(atual, novo, usuario)` — valida transicao + ator.
    **Chamada pelo novo `executar_transicao`.**
  - `pode_cancelar`, `atores_permitidos`, `transicao_e_valida` — uteis
    em testes; nao alterados.
  - Excecoes `TransicaoInvalidaError`, `AtorNaoAutorizadoError`,
    `RotaIndeterminavelError` — reutilizadas.
- `app/services/qrcode_service.py`
  - `gerar_payload_qr(nro_requerimento, hash_hex)` — ja usado pelo C06
    para renderizar o payload dentro do PNG do QR Code.
  - `validar_payload_qr(payload, hash_hex_completo)` — **finalmente
    utilizado**. A funcao ja existe, ja e constant-time via
    `hmac.compare_digest`, e o formato `3SD|{nro_req}|{hash[:16]}` esta
    estavel desde o ADR-033.
  - `gerar_hash(prova_id, nro_requerimento)` — nao usado diretamente no
    scan (usariamos o hash armazenado como fonte de verdade), mas fica
    disponivel.
  - **Constantes:** `QR_PAYLOAD_PREFIX = "3SD"`,
    `QR_PAYLOAD_SEPARATOR = "|"`, `HASH_TRUNCADO_LEN = 16`.
- `app/services/audit_service.py`
  - `log_audit(db, *, acao, usuario_id, prova_id, detalhes, request)` —
    ja lida com X-Forwarded-For, user-agent, flush sem commit.
    **Chamada pelo novo handler de transicao** com `acao =
    "transitar_status"` + `detalhes = {de, para, rota_gravada, ciclo,
    motivo}`.
- `app/api/v1/provas.py` — helpers **explicitamente reutilizados**:
  - `parse_prova_id` — converte path-param UUID -> 404 elegante.
  - `_scoping_filter(user)` — ja filtra por setor (ADR-046).
  - `_carregar_prova_com_scoping(db, prova_id, user)` — retorna
    `(prova, vendedor_nome, vendedor_localizacao, vendedor_setor) | None`.
    **Essa e a primitiva que o novo endpoint de scan usa** para resolver
    o QR e verificar visibilidade no mesmo passo.
  - `_determinar_rota_projetada(setor, loc)` — calcula rota projetada
    sem carregar Usuario.
  - `_build_prova_response` — monta `ProvaResponse` uniformemente.
- `app/db/models.py` — todos os enums (`StatusProvaEnum`, `SetorEnum`,
  `LocalizacaoEnum`, `RotaEnum`) e modelos (`ProvaDigital`, `Movimentacao`,
  `Usuario`, `AuditLog`). Nada alterado.
- `app/domain/schemas/prova.py` — contratos **pre-existentes** que
  continuam:
  - `ProvaResponse` (detalhe) — usado como pedaco do scan response e do
    transition response.
  - `MovimentacaoResponse` e `MovimentacaoListResponse` — ja
    pre-existentes (ADR-051). Wave 3 popula sem mudanca de contrato.
  - Enums espelhados: `StatusProvaEnum`, `RotaEnum`, `SetorEnum`,
    `LocalizacaoEnum`.

**NAO alterar:**
- `config.py` — nenhum env var novo (nem QR secret, nem nada).
- `core/jwt.py` — verificacao de JWT intocada.
- `core/r2.py`, `core/supabase_admin.py` — nao tocados (o Lote A nao
  mexe em R2 nem em Supabase Auth).
- Todos os 8 endpoints Wave 2 de `provas.py` (POST /upload-url, POST /,
  GET /, GET /{id}, GET /{id}/imagem-url, GET /{id}/movimentacoes, GET
  /{id}/etiqueta.pdf, GET /{id}/qr-code.png). **Nenhuma mudanca
  comportamental.** Adicionamos novos handlers ao mesmo router.
- `app/api/v1/configuracoes.py` — intocada.
- `app/api/v1/users.py` — intocada.
- `app/services/etiqueta_service.py`, `app/services/r2_signed.py` —
  intocados.

### 2.4 Frontend (componentes/hooks reutilizaveis)

**CONSUMIR sem alterar:**
- `src/lib/api.ts` — `apiFetch<T>()` e `ApiError`. Usado para os novos
  endpoints POST /scan e POST /transicoes (ambos retornam JSON, nenhum
  binario — nao cai na restricao de binarios do CLAUDE.md).
- `src/lib/supabase/client.ts` — obter JWT via `createClient()`.
- `src/lib/types/prova.ts` — **extender** (nao substituir) com
  `TransicaoRequest`, `TransicaoResponse`, `ScanRequest`, `ScanResponse`.
- `src/lib/types/usuario.ts` — `MeResponse` (para saber o setor do user
  corrente, necessario para escolher o caminho UI no Componente 11).
- `src/hooks/useInactivityTimeout.ts` — ja aplicado no layout do
  dashboard; novas paginas herdam automaticamente.
- `src/app/(dashboard)/layout.tsx` — **mudanca minima: apenas ativar o
  item "Escanear" do menu `MAIN_NAV`** adicionando `href: "/escanear"`.
  Isso e uma edicao de 1 linha num item que ja existia como placeholder
  inativo. Nenhuma outra mudanca no layout.
- `middleware.ts` — session refresh + redirect, intocado. Ja protege
  qualquer rota dentro de `(dashboard)`.
- CSS vars em `globals.css` — todas reutilizadas. Zero CSS novo global.

**NAO alterar:**
- Nenhuma das 7 paginas existentes (`/login`, `/usuarios`, `/nova-prova`,
  `/provas`, `/provas/[id]`, `/configuracoes`) tem seu comportamento
  alterado. A unica interacao com elas e: *a pagina* `/provas/[id]` *vai
  automaticamente mostrar as novas movimentacoes na timeline assim que
  elas forem geradas* — isso e zero-modificacao porque o endpoint
  `/movimentacoes` ja retorna o contrato certo (Wave 2, ADR-051).

### 2.5 CI/CD e infraestrutura

**CONSUMIR sem alterar:**
- `.github/workflows/ci.yml` — ruff + pytest + deploy. Pipeline existente
  roda a suite backend (que vai ter testes novos); nenhum job novo
  necessario.
- `.github/workflows/keep-alive.yml` — cron intocado.
- Railway (backend deploy) e Vercel (frontend deploy) — ambos seguem os
  mesmos workflows. Nenhuma env var nova necessaria.

---

## 3. Interface com Componentes 12, 13 e 14 — Contratos a expor

Este Lote A **nao implementa** C12, C13 ou C14. Mas precisa deixar
contratos e ganchos prontos, sem ultrapassar o escopo autorizado.

### 3.1 Componente 12 — Timeline Visual de Estagios (Lote C futuro)

**O que C12 precisa e que o Lote A ja entrega:**
- Linhas em `movimentacoes` geradas pelo Lote A tem todos os campos
  necessarios para o C12 renderizar a timeline:
  - `status_anterior`, `status_novo` — para mostrar "de -> para".
  - `usuario_nome` e `usuario_setor` — vem via JOIN no endpoint
    `GET /provas/{id}/movimentacoes` ja implementado na Wave 2.
  - `created_at` — timestamp do evento.
  - `ciclo` — para desenhar multiplos ciclos (relevante em C14).
  - `rota_no_momento` — para desenhar ramificacao PADRAO vs DIRETA.
  - `motivo_reprovacao` — para destacar reprovacoes com motivo visivel.
- O contrato `MovimentacaoResponse` + `MovimentacaoListResponse` ja
  existe em `schemas/prova.py` desde Wave 2 (ADR-051) — zero alteracao.
- O hook `useProvaDetail` no frontend ja faz o GET do historico e passa
  para a pagina `/provas/[id]` como placeholder. O C12 no Lote C apenas
  vai substituir o placeholder pelo componente real de timeline.

**O que o Lote A NAO faz:**
- Nao cria o componente visual `<TimelineProva>` nem animacoes com
  Framer Motion.
- Nao instala Framer Motion.
- Nao altera `useProvaDetail.ts`.

**Contrato exposto para C12:** zero mudanca. O componente C12 vai
consumir o endpoint Wave 2 inalterado.

### 3.2 Componente 13 — Cancelamento (Lote C futuro)

**O que o Lote A ja deixa pronto:**
- `state_machine.executar_transicao` precisa ser implementada de forma
  **generica** o suficiente para que C13 possa simplesmente chamar a
  mesma funcao passando `status_novo = CANCELADA` + `motivo`. A regra
  RN-005 ja esta na maquina de estados (via `pode_cancelar` + `setor ==
  STUDIO` em `validar_transicao`).
- O campo `provas_digitais.motivo_cancelamento` ja existe no schema e a
  coluna aceita `TEXT` — o Lote A nao escreve nela, mas ela esta pronta
  para o C13 escrever.
- O endpoint `POST /provas/{id}/transicoes` implementado no Lote A **nao
  vai aceitar** `status_novo = CANCELADA` por uma escolha explicita de
  escopo. Alternativas para C13:
  - (a) C13 cria um endpoint dedicado `POST /provas/{id}/cancelar` com
    payload `{motivo: str}` — **preferencia do desenho**, separa
    transicoes de fluxo (que exigem assinatura + QR) de acoes
    administrativas (cancelamento, reinicio).
  - (b) C13 expande o endpoint existente para tambem aceitar
    `status_novo = CANCELADA` + campo `motivo_cancelamento`. Vale se a
    Renan decidir que o cancelamento tambem passa por escaneamento do
    QR + assinatura no fisico da prova.
- A decisao (a) vs (b) fica **explicitamente para o Lote C**. O Lote A
  apenas garante que `executar_transicao` e uma funcao publica com
  assinatura documentada o suficiente para ambos os caminhos.

**Contrato exposto:**
```python
async def executar_transicao(
    db: AsyncSession,
    *,
    prova: ProvaDigital,  # carregada via FOR UPDATE pelo caller
    status_novo: StatusProvaEnum,
    usuario: Usuario,  # autor da acao
    assinatura_digital: bytes,  # PNG decodificado; nao vazio
    motivo_reprovacao: str | None,  # obrigatorio sse REPROVADA_PELO_VENDEDOR
    motivo_cancelamento: str | None = None,  # USO FUTURO C13
    request: Request | None = None,  # para audit_log (IP/UA)
) -> Movimentacao:
    """Executa uma transicao de status validada end-to-end.

    Responsabilidades:
      1. validar_transicao(status_atual, status_novo, usuario)
      2. Validar motivo obrigatorio conforme destino
      3. Copiar prova.ciclo_atual e prova.rota para a movimentacao
      4. Na transicao RETIRADA_PELO_VENDEDOR -> APROVADA_PELO_VENDEDOR,
         gravar prova.rota = determinar_rota(vendedor) ANTES do UPDATE
      5. INSERT em movimentacoes
      6. UPDATE em provas_digitais (status, rota se aplicavel)
      7. log_audit com detalhes completos
      8. Retorna a movimentacao criada (sem commit — caller controla)

    O caller e responsavel por:
      - Carregar a prova com FOR UPDATE (evita race com outras transicoes)
      - Commit da transacao
      - Tratar excecoes de dominio (TransicaoInvalidaError,
        AtorNaoAutorizadoError) e traduzir para HTTP

    Excecoes possiveis:
      - TransicaoInvalidaError — destino ilegal na Matriz
      - AtorNaoAutorizadoError — setor nao permitido
      - ValueError — motivo obrigatorio ausente ou assinatura vazia
      - RotaIndeterminavelError — transicao que exige rota mas vendedor
        nao tem localizacao
    """
```

Essa assinatura e estavel para o Lote C consumir sem refactor — o
parametro `motivo_cancelamento` ja esta reservado e ignorado no Lote A.

### 3.3 Componente 14 — Reinicio de Ciclo (Lote C futuro)

**O que o Lote A ja deixa pronto:**
- A transicao `REPROVADA_PELO_VENDEDOR -> CRIADA` ja esta em
  `TRANSICOES` com ator = `STUDIO` (state_machine atual).
- O Lote A implementa **a parte mecanica** — `executar_transicao`
  suporta essa transicao, incluindo o incremento de `ciclo_atual`.
  Justificativa: se o incremento de ciclo ficasse para o Lote C, seria
  uma ramificacao de logica dentro do handler de transicao que
  complicaria a implementacao agora. Fazer generico uma vez e mais
  simples.
- Contrato exposto no `executar_transicao`:
  ```
  Quando status_atual = REPROVADA_PELO_VENDEDOR e status_novo = CRIADA:
    - Incrementa prova.ciclo_atual += 1 ANTES do UPDATE
    - Reseta prova.rota = NULL (proxima aprovacao vai definir de novo)
    - Copia o novo valor de ciclo_atual para movimentacao.ciclo
    - Gera audit log com acao = "reiniciar_ciclo" (nao
      "transitar_status")
  ```
- O que **o Lote A NAO implementa** e o **endpoint** que expoe essa
  transicao. Justificativa: RF-008 fala em "acao administrativa 3Studio",
  que semanticamente e diferente de "transicao via scan + assinatura". O
  C14 provavelmente vai ter endpoint dedicado
  `POST /provas/{id}/reiniciar-ciclo` com `{motivo}` opcional, **sem
  exigir escaneamento de QR** (admin esta numa tela de gestao, nao
  pegando a prova fisica).
- Portanto: o endpoint `POST /provas/{id}/transicoes` do Lote A
  **REJEITA explicitamente** `status_novo = CRIADA` vindo por essa rota,
  para deixar claro que reinicio e acao administrativa separada.

**Decisao registrada:** o Lote A implementa o gancho no
`executar_transicao` mas nao expoe endpoint. C14 (Lote C) cria o
endpoint administrativo e chama a mesma funcao.

**Fica para Lote C decidir:**
- Exatamente qual e o endpoint, autenticacao (admin only ou STUDIO), e
  se exige motivo obrigatorio ou opcional.
- Se a UI de C14 vai mostrar explicitamente "reiniciar ciclo" numa lista
  de provas reprovadas ou via botao no detalhe.

### 3.4 Resumo — Contratos a expor ao Lote B/C

| Contrato | Estabelecido em | Usado por |
|---|---|---|
| `executar_transicao` com assinatura completa (incluindo `motivo_cancelamento=None`) | Sub-bloco A.1 | C13 (Lote C) |
| Suporte a `REPROVADA_PELO_VENDEDOR -> CRIADA` com incremento de ciclo | Sub-bloco A.1 | C14 (Lote C) |
| Endpoint `POST /provas/{id}/transicoes` **nao aceita** CANCELADA nem CRIADA como destino | Sub-bloco A.3 | — (rejeicao explicita) |
| `MovimentacaoResponse` populado na resposta | Sub-bloco A.3 | C12 (Lote C) |
| `provas_digitais.rota` populada para **provas no fluxo ativo** (estado `APROVADA_PELO_VENDEDOR`) | Sub-bloco A.1+A.3 | C12 (timeline exibe rota) + Wave 4 (dashboard filtra rota) |

> **Nota sobre rota pre-existente** (revalidacao Rev 2): o banco atual de
> producao tem 3 linhas em `provas_digitais` com `rota != NULL` — todas em
> estado `CANCELADA`, seeds de teste antigos inseridos antes do ADR-042
> formalizar "rota so persiste na aprovacao". Esses registros **nao afetam**
> o Lote A: (a) estao em estado terminal (cancelado), o state_machine nao
> aceita transicoes a partir de `CANCELADA`; (b) o filtro `rota` da listagem
> (C07) ja trata NULL corretamente; (c) a primeira linha viva com `rota`
> populada pelo Lote A sera a primeira `APROVADA_PELO_VENDEDOR` real em
> producao.
| Audit log com `acao = "transitar_status"` + `detalhes_json` estruturado | Sub-bloco A.1 | Wave 6 (tela de auditoria) |

---

## 4. Modelo de dados

### 4.1 Alembic — migrations necessarias

**NENHUMA migration Alembic e necessaria para o Lote A.** Todo o schema
de dominio ja foi criado nas Waves 0 e 2. Verificacao:

| Necessidade | Coluna ja existe? | Indice ja existe? |
|---|---|---|
| Inserir em `movimentacoes` (9 campos) | ✓ (migration 001) | — (sao 5 indexes em `movimentacoes`, sufcientes) |
| Atualizar `provas_digitais.status` | ✓ | `idx_provas_status`, `idx_provas_status_created` |
| Atualizar `provas_digitais.rota` na aprovacao | ✓ | nao precisa de indice (update por PK) |
| Atualizar `provas_digitais.ciclo_atual` no reinicio | ✓ (constraint `ciclo_atual >= 1`) | nao precisa |
| Ler `provas_digitais.qr_code_hash` no scan | ✓ (UNIQUE) | `provas_digitais_qr_code_hash_key` (auto) |
| Inserir em `audit_logs` | ✓ | existentes |

**Conclusao:** `alembic_version` permanece em `009` apos o Lote A.

### 4.2 RLS — novas policies necessarias

**Criar um novo arquivo** em `backend/migrations/rls/`:

**`006_movimentacoes_insert_and_expand_select.sql`** (idempotente, DROP IF
EXISTS + CREATE):

1. **`pol_movimentacoes_insert`** — nova policy:
   ```
   FOR INSERT TO public
   WITH CHECK (
     EXISTS (
       SELECT 1 FROM usuarios u
       WHERE u.auth_uid = (SELECT auth.uid()) AND u.is_admin = true
     )
   )
   ```
   Motivacao: defesa em profundidade. Backend com service_role bypassa
   RLS (mesmo padrao de `pol_provas_insert`), mas um acesso direto via
   supabase-js client — caso algum cliente do futuro tente — seria
   barrado a menos que fosse admin. Mantem consistencia com `pol_provas_insert`.

2. **Expandir `pol_movimentacoes_select`** — resolve o debito F03 da
   auditoria externa Wave 2 (Sessao 22). Adiciona:
   - `MOTORISTA` ve movimentacoes de provas atualmente em
     `COM_MOTORISTA` (espelha `pol_provas_select`).
   - `CLICHERIA` ve movimentacoes de provas em `ENVIADA_PARA_CLICHERIA`,
     `ENCAMINHADA_A_CLICHERIA`, `RECEBIDA_PELA_CLICHERIA`.
   - Padrao `(SELECT auth.uid())` para initplan optimization
     (ADR-029).

**Nao precisamos de policy `pol_movimentacoes_update` ou
`pol_movimentacoes_delete`** — o trigger `trg_movimentacoes_imutavel`
ja bloqueia qualquer UPDATE/DELETE (RNF-005).

### 4.3 Dados pre-existentes no banco de producao

Snapshot revalidado em 2026-04-10 via MCP `execute_sql`:

| Tabela | Rows | Observacao |
|---|---|---|
| `movimentacoes` | **0** | Zero migracao/backfill. Primeira linha sera inserida pelo Lote A. |
| `provas_digitais` | **11** | Distribuicao abaixo |
| `etiquetas` | 11 | 1 por prova (snapshot imutavel) |
| `audit_logs` | 15 | Acoes Waves 0-2 — intocado |
| `configuracoes_sistema` | 2 | `tempo_atraso_horas_uteis=48`, `template_etiqueta` objeto JSONB |
| `usuarios` | 3 | 2 admins STUDIO + 1 vendedor FILIAL (ver §9.3 P1) |

**Distribuicao real das 11 linhas em `provas_digitais`:**

| status | rota | ciclo_atual | count |
|---|---|---|---|
| `CRIADA` | NULL | 1 | **5** (provas "vivas", escaneaveis pelo Lote A) |
| `CANCELADA` | NULL | 1 | 3 (seeds canceladas antes de `rota` ter sido populada) |
| `CANCELADA` | `PADRAO` | 1 | 2 (seeds de teste criadas com rota pre-persistida) |
| `CANCELADA` | `DIRETA` | 1 | 1 (idem) |

**Impacto no Lote A:**
- As **5 provas em `CRIADA`** sao as unicas escaneaveis. Apos o deploy, o
  primeiro vendedor que escanear uma delas gera a primeira movimentacao do
  sistema.
- As **6 provas em `CANCELADA`** nao aceitam transicao (state_machine ja
  bloqueia), entao o Lote A nao precisa tratar esse subset especificamente.
- As **3 provas com `rota != NULL` ja pre-populada** (todas canceladas) NAO
  sao "contaminantes" do Lote A — a coluna `rota` da `APROVADA_PELO_VENDEDOR`
  e populada do zero para cada prova que transitar viva pelo fluxo.

**Nenhuma data migration necessaria.**

### 4.4 Constraints novas?

Nenhuma. Todas as invariantes de Lote A sao enforcaveis em camada de
aplicacao:
- `motivo_reprovacao` nao vazio sse `status = REPROVADA_PELO_VENDEDOR` —
  poderia virar um CHECK constraint em `movimentacoes`, mas ja e
  enforcado pelo `executar_transicao` + validator Pydantic. CHECK
  redundante complica diff de schema sem ganho.
- Assinatura nao vazia — enforcado no Pydantic (`min_length=1` no byte
  array apos decode base64).
- Ciclo coerente — ja protegido por `CHECK (ciclo >= 1)` existente.

---

## 5. Contratos de API

Esta secao define **exatamente** os novos endpoints, schemas Pydantic, e
contratos HTTP. Numero final de endpoints publicos pos-Wave 3 Lote A:
**24 existentes + 2 novos = 26 rotas**.

### 5.1 `POST /api/v1/provas/scan` (Componente 10)

**Proposito:** resolver um payload de QR Code escaneado, validar e
retornar os dados da prova + as transicoes que o usuario corrente pode
executar sobre ela.

**Metodo + Path:** `POST /api/v1/provas/scan`

**Dependencies:**
- `db: AsyncSession = Depends(get_db)`
- `current_user: Usuario = Depends(get_current_user)` — **qualquer**
  usuario autenticado ativo (scoping interno limita o resto).
- `request: Request` (para audit log, nao obrigatorio mas util).

**Request body (`ScanRequest`):**
```python
class ScanRequest(BaseModel):
    payload: str = Field(..., min_length=1, max_length=256)

    @field_validator("payload")
    @classmethod
    def _valida_payload(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(f"{QR_PAYLOAD_PREFIX}{QR_PAYLOAD_SEPARATOR}"):
            raise ValueError("Formato de QR Code invalido")
        parts = v.split(QR_PAYLOAD_SEPARATOR)
        if len(parts) != 3:
            raise ValueError("QR Code mal formado")
        return v
```

**Response body (`ScanResponse`, HTTP 200):**
```python
class ScanResponse(BaseModel):
    prova: ProvaResponse              # reusa o schema ja existente (Wave 2)
    transicoes_permitidas: list[StatusProvaEnum]  # destinos validos PARA ESTE usuario
    motivo_obrigatorio_em: list[StatusProvaEnum]  # subset onde reprovacao exige motivo
```

- `transicoes_permitidas` e calculado por:
  `validar_transicao_para_usuario(prova.status, destino, current_user)`
  iterando sobre `TRANSICOES[prova.status]`. Para vendedor aprovado,
  pode retornar apenas um destino alinhado com `localizacao`. **Aqui e
  onde a distincao MATRIZ vs FILIAL das HUs US-005/US-006 e aplicada**:
  - Vendedor MATRIZ em `APROVADA_PELO_VENDEDOR` -> lista contem apenas
    `DE_VOLTA_3STUDIO`.
  - Vendedor FILIAL em `APROVADA_PELO_VENDEDOR` -> lista contem apenas
    `ENCAMINHADA_A_CLICHERIA`.
- `motivo_obrigatorio_em` = `[REPROVADA_PELO_VENDEDOR]` sse aplicavel;
  caso contrario `[]`.

**Fluxo de execucao:**
1. Pydantic valida formato basico do payload.
2. Parse `parts = payload.split("|")` -> `(prefixo, nro_req, hash_trunc)`.
3. Query: `SELECT ... FROM provas_digitais WHERE nro_requerimento = ?`
   (usa index UNIQUE).
4. Se nao encontrado -> 404 "Prova nao encontrada".
5. `qrcode_service.validar_payload_qr(payload, prova.qr_code_hash)` ->
   se retornar False, 422 "QR Code nao corresponde a prova esperada".
   **Constant-time**, resistente a timing attacks.
6. Aplicar scoping: verificar se `_scoping_filter(current_user)`
   permitiria ver essa prova. Se nao permitir -> 404 "Prova nao
   encontrada" (mesma mensagem que ausencia, nao vazamos existencia).
7. Resolver `vendedor_nome`, `vendedor_localizacao`, `vendedor_setor`
   via JOIN (reutilizar o mesmo JOIN do
   `_carregar_prova_com_scoping`).
8. Calcular `transicoes_permitidas` iterando `TRANSICOES[prova.status]`
   e filtrando com `validar_transicao` (catch das excecoes). Aplicar o
   filtro MATRIZ/FILIAL extra para o caso `APROVADA_PELO_VENDEDOR`.
9. Log audit: `acao = "escanear_prova"`, `detalhes = {"nro_req": ...,
   "status_atual": ...}`. Commit. Retorna 200.

**Codigos HTTP:**
| Status | Quando |
|---|---|
| 200 | Happy path. `transicoes_permitidas` pode ser `[]` se a prova esta em estado terminal ou se o usuario nao tem nenhuma transicao permitida a partir do estado atual. |
| 401 | Token ausente/invalido (herdado de `get_current_user`). |
| 403 | Usuario desativado (herdado de `get_current_user`). |
| 404 | `payload` apontando para prova inexistente OU nao visivel para o scoping do usuario. |
| 422 | Payload nao bate com hash armazenado (validar_payload_qr falha) OU formato invalido (Pydantic). |
| 502 | DB transient error (padrao ADR-074/076 — try/except em volta das queries). |

**Motivos de desenhar como POST e nao GET:**
- Request body com payload (o QR Code escaneado) — poderia ser query
  string mas complica logs/cache.
- Registra audit log a cada scan — e uma acao, nao uma consulta pura.
- Consistente com `POST /api/v1/provas/upload-url` (tambem e scan/
  request de acao).

### 5.2 `POST /api/v1/provas/{prova_id}/transicoes` (Componente 11)

**Proposito:** executar uma transicao de status com assinatura digital,
aplicando a maquina de estados completa.

**Metodo + Path:** `POST /api/v1/provas/{prova_id}/transicoes`

**Dependencies:**
- `prova_id: uuid.UUID = Depends(parse_prova_id)`
- `db: AsyncSession = Depends(get_db)`
- `current_user: Usuario = Depends(get_current_user)`
- `request: Request`

**Request body (`TransicaoRequest`):**
```python
class TransicaoRequest(BaseModel):
    status_novo: StatusProvaEnum  # destino desejado
    assinatura_base64: str = Field(..., min_length=1, max_length=700_000)
    motivo_reprovacao: str | None = Field(None, max_length=1000)

    @field_validator("status_novo")
    @classmethod
    def _rejeita_cancelada_e_criada(cls, v: StatusProvaEnum) -> StatusProvaEnum:
        if v == StatusProvaEnum.CANCELADA:
            raise ValueError(
                "Cancelamento nao e permitido por este endpoint (ver C13)"
            )
        if v == StatusProvaEnum.CRIADA:
            raise ValueError(
                "Reinicio de ciclo nao e permitido por este endpoint (ver C14)"
            )
        return v

    @field_validator("motivo_reprovacao")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None  # string vazia -> None
```

Notes:
- `assinatura_base64` e o PNG gerado no frontend pelo
  `react-signature-canvas` (dataURL sem o prefixo `data:image/png;base64,`).
  Limite 700 KB = ~500 KB de PNG decodificado (base64 tem overhead
  de ~33%). Folga generosa para canvas high-DPI em celulares.
- Validacao cruzada (motivo obrigatorio sse status_novo =
  REPROVADA_PELO_VENDEDOR) acontece **no handler**, nao no validator, pois
  envolve uma comparacao entre dois campos. Pydantic model_validator
  tambem e aceitavel mas o handler ja vai ter try/except de dominio
  entao fica mais coeso la.

**Response body (`TransicaoResponse`, HTTP 201):**
```python
class TransicaoResponse(BaseModel):
    prova: ProvaResponse           # com status/rota atualizados
    movimentacao: MovimentacaoResponse  # a linha recem-inserida
```

**Fluxo de execucao:**
1. Pydantic valida payload + rejeita status_novo em {CANCELADA, CRIADA}.
2. Decode base64 -> bytes. Se falhar, 422 "Assinatura invalida".
3. `_carregar_prova_com_scoping(db, prova_id, current_user)` com lock
   **FOR UPDATE** sobre `provas_digitais` (evita race entre dois scans
   simultaneos). **OBS:** vamos precisar de uma variante
   `_carregar_prova_com_scoping_locked` ou adicionar flag `lock=True` a
   funcao existente. Resolucao no sub-bloco A.1 — **nao altera a
   assinatura dos callers existentes**.
4. Se None -> 404 "Prova nao encontrada".
5. `executar_transicao(...)` faz todo o trabalho sujo:
   - `validar_transicao` (state_machine existente, inalterado)
   - Se `status_novo = REPROVADA_PELO_VENDEDOR` e motivo vazio -> raise
     `ValueError("Motivo da reprovacao e obrigatorio")`
   - Se `status_novo = APROVADA_PELO_VENDEDOR`, calcula e grava
     `prova.rota` via `determinar_rota(vendedor)`
   - **Regra nova especifica do Lote A (RF-009):** se
     `status_atual = APROVADA_PELO_VENDEDOR` e `status_novo =
     DE_VOLTA_3STUDIO`, valida que `vendedor.localizacao == MATRIZ`.
     Caso contrario, AtorNaoAutorizadoError (rota errada).
   - **Analoga:** se `status_novo = ENCAMINHADA_A_CLICHERIA`, valida
     `vendedor.localizacao == FILIAL`.
   - Insert em `movimentacoes` com todos os campos (ver secao 2.1)
   - Update em `provas_digitais` (status sempre; rota sse aprovacao)
   - `log_audit(..., acao="transitar_status", detalhes={...})` com
     estrutura: `{de, para, rota_antes, rota_depois, ciclo, motivo}`
   - Return Movimentacao (sem commit)
6. Commit.
7. Re-carregar `ProvaResponse` via `_build_prova_response`.
8. Montar `MovimentacaoResponse` com o autor.
9. Return 201 + body.

**Codigos HTTP:**
| Status | Quando |
|---|---|
| 201 | Transicao executada. |
| 401 | Token invalido. |
| 403 | Usuario desativado. |
| 404 | Prova nao encontrada ou fora do scoping. |
| 409 | **Race condition** — `status_atual` leu A, mas outro escrevente ja transicionou para B antes do FOR UPDATE pegar. Nessa situacao o cliente ve 409 com mensagem "Status da prova mudou. Recarregue e tente novamente". Traduz `TransicaoInvalidaError` apos lock. |
| 422 | Transicao ilegal (destino nao alcancavel), ator nao autorizado, motivo ausente na reprovacao, assinatura invalida, base64 mal formado, setor/localizacao incompativel com rota. |
| 502 | DB transient error. |

**Motivos de 201 vs 200:** criamos uma linha em `movimentacoes` — POST
que cria recurso retorna 201, consistente com `POST /api/v1/provas/` do
C06.

**Idempotencia:** o endpoint **nao e idempotente**. Um segundo request
identico retornaria 422 "transicao ilegal" porque o status atual ja
mudou. Nao ha idempotency-key — considerar para Wave 5 se o volume
justificar.

### 5.3 Resumo dos endpoints pos-Lote A

| Prefix | Endpoint | Wave | Adicionado no Lote A? |
|---|---|---|---|
| `/api/v1/users` | GET /me, GET /, GET /{id}, POST /, PATCH /{id}, DELETE /{id} | 1 | nao |
| `/api/v1/provas` | 8 existentes (upload-url, POST, GET list, GET {id}, imagem-url, movimentacoes, etiqueta.pdf, qr-code.png) | 2 | nao |
| `/api/v1/provas` | **POST /scan** | 3 | **SIM** |
| `/api/v1/provas` | **POST /{id}/transicoes** | 3 | **SIM** |
| `/api/v1/configuracoes` | 3 existentes | 2 | nao |
| `/health*` | 3 existentes | 0 | nao |

**Total: 24 -> 26 rotas.**

---

## 6. Impacto no frontend

### 6.1 Dependencias novas (package.json)

Duas dependencias explicitamente pedidas pelo Backlog C10 e C11 + DAT v2.0:

```json
{
  "html5-qrcode": "^2.3.8",
  "react-signature-canvas": "^1.0.6",
  "@types/react-signature-canvas": "^1.0.7"
}
```

- `html5-qrcode` — lib de camera + decode QR, funciona em qualquer
  browser moderno via getUserMedia. Dependencia zero em outras libs
  (sem React). Precisa ser envolvida num wrapper React para montar/
  desmontar corretamente.
- `react-signature-canvas` — wrapper React ao redor de `signature_pad`.
  Retorna canvas ou toDataURL para a assinatura. Tipagem via
  `@types/react-signature-canvas`.
- Nada mais. Nenhuma lib de state management, framer motion, etc.
- Versoes pinadas com `^` permitindo minor+patch (padrao do resto do
  projeto).

### 6.2 Nova rota: `/escanear`

**Arquivo:** `frontend/src/app/(dashboard)/escanear/page.tsx` +
`escanear.module.css`.

**Maquina de estados da pagina** (client-only, React `useReducer` ou
`useState`):
```
InitialState: 'idle'
-> click "Abrir camera" -> 'camera-starting'
-> html5-qrcode ready -> 'scanning'
-> QR detected -> fetch POST /scan -> 'scan-loading'
-> 200 ok -> 'scan-ready' (mostra detalhes da prova + botoes de transicao)
-> 404/422 -> 'scan-error' (mostra erro + botao "Tentar outro QR")

From 'scan-ready':
-> click "Aprovar"/"Reprovar"/"Confirmar" -> 'signing'
  (abre modal ou painel com SignatureCanvas + textarea motivo quando reprovar)
-> submit assinatura -> fetch POST /{id}/transicoes -> 'submitting'
-> 201 ok -> 'done' (mostra sucesso + botao "Escanear proxima" volta ao idle)
-> 409/422/502 -> 'submit-error' (mostra erro; permite retry da assinatura)
```

**Componentes React a criar:**
- `ScannerView` (client component) — container principal da pagina.
- `QrScanner` (client component) — wrapper html5-qrcode:
  - `useEffect` monta/desmonta o scanner. **Crucial**: chamar
    `.clear()` no cleanup para liberar a camera, senao fica travada ate
    o refresh.
  - Props: `onDetect(payload: string)`, `onError(err: Error)`.
  - Internamente usa `new Html5Qrcode("scanner-div")` + `start()` com
    `fps: 10` + `qrbox: { width: 250, height: 250 }`.
- `SignatureCapture` (client component) — wrapper
  react-signature-canvas:
  - Props: `onConfirm(base64: string)`, `onClear()`.
  - Internamente usa `ref.current.toDataURL("image/png")` +
    `.split(',')[1]` para tirar o prefixo `data:image/png;base64,`.
  - Inclui botao "Limpar" e "Confirmar".
- `ProvaPreview` — card visual com nome, nro_req, cliente, vendedor,
  status atual, rota, miniatura da arte. Re-utiliza estilos do card de
  `/provas/[id]/page.tsx` (mesmas variaveis CSS).
- `TransicoesDisponiveis` — lista de botoes gerados dinamicamente a
  partir de `scanResponse.transicoes_permitidas`. Labels legiveis via
  `STATUS_LABELS`:
  - Se `REPROVADA_PELO_VENDEDOR` estiver na lista, o botao abre modal
    de reprovacao (textarea motivo + SignatureCapture).
  - Para qualquer outra transicao, abre modal de assinatura simples.
- `TransicaoConfirmModal` — modal de confirmacao (reutilizavel entre
  aprovacao, reprovacao, devolucao a 3Studio, etc).

**Estilos:**
- Arquivo `escanear.module.css` com o card da pagina seguindo o mesmo
  layout de `/nova-prova/nova-prova.module.css` (header, corpo, footer).
- Video stream do scanner com `aspect-ratio: 1 / 1`, `max-width: 320px`,
  centralizado. Borda arredondada com `var(--radius-lg)`.
- CSS `:has()` nao necessario — tudo com classes explicitas.

**Acessibilidade:**
- Botoes com `aria-label` explicitos.
- Estado visual claro para cada fase da maquina (idle, scanning,
  signing, submitting).
- Toast-less por enquanto — usar `alert()` como fallback conforme
  padrao do C08 M1 (ADR-076). Toast sistema vem na Wave 4+.

**Autorizacoes por setor na UI:**
- O endpoint `/scan` ja filtra `transicoes_permitidas` pelo setor. A UI
  apenas renderiza o que o backend diz. **Zero logica de "qual setor
  pode fazer o que" no frontend** — evita divergencia.
- Entretanto, a pagina `/escanear` e acessivel a qualquer setor
  autenticado. Nao bloqueamos por setor no nivel do menu — alguem sem
  permissao para nenhuma transicao vai escanear e receber
  `transicoes_permitidas = []` + mensagem "Voce nao tem permissao para
  movimentar esta prova no estado atual".

### 6.3 Novos hooks

**`src/hooks/useScanner.ts`** — wrapper em torno do `html5-qrcode` que
expoe uma API React-idiomatica:
```typescript
export function useScanner({
  onDetect: (payload: string) => void,
  onError: (err: Error) => void,
  enabled: boolean,
}): { ready: boolean, divId: string }
```
- Cria um `divId` estavel via `useId()`.
- Se `enabled=true`, monta o scanner; se `false`, desmonta.
- **Crucial**: cleanup no `useEffect` return + try/catch em
  `.stop()` + `.clear()` (html5-qrcode tem bug conhecido onde stop
  pode throw se o stream ja foi interrompido externamente).

**`src/hooks/useExecutarTransicao.ts`** — hook que encapsula o POST
`/provas/{id}/transicoes`:
```typescript
export function useExecutarTransicao(provaId: string): {
  executar: (status_novo: StatusProva, assinatura_base64: string, motivo?: string) => Promise<TransicaoResponse>,
  loading: boolean,
  error: ApiError | null,
}
```
- Obtem o token via `useSupabase()`/`createClient()`.
- Chama `apiFetch<TransicaoResponse>(`/api/v1/provas/${provaId}/transicoes`, ...)`.
- **Nao e um hook de GET com state compartilhado** — cada invocacao
  executa uma transicao isolada.

**`src/hooks/useScanProva.ts`** — hook que encapsula o POST
`/api/v1/provas/scan`:
```typescript
export function useScanProva(): {
  escanear: (payload: string) => Promise<ScanResponse>,
  loading: boolean,
  error: ApiError | null,
}
```

**Nao criamos hook generico `useTransicao()` com state global** — cada
transicao e uma acao explicita, nao ha cache a invalidar.

### 6.4 Novos tipos

**`src/lib/types/prova.ts`** recebe (mesma convencao dos outros tipos):
```typescript
export interface ScanRequest {
  payload: string;
}

export interface ScanResponse {
  prova: ProvaResponse;
  transicoes_permitidas: StatusProva[];
  motivo_obrigatorio_em: StatusProva[];
}

export interface TransicaoRequest {
  status_novo: StatusProva;
  assinatura_base64: string;
  motivo_reprovacao: string | null;
}

export interface TransicaoResponse {
  prova: ProvaResponse;
  movimentacao: MovimentacaoResponse;
}
```

`MovimentacaoResponse` **ja existe** no arquivo desde Wave 2.

### 6.5 Alteracao no layout do dashboard

**Unica edicao fora de `/escanear`**: `src/app/(dashboard)/layout.tsx`,
linha do `MAIN_NAV`:

```diff
 const MAIN_NAV: NavItemSpec[] = [
   { key: "dashboard", label: "Dashboard", icon: <HomeIcon /> },
   { key: "provas", label: "Provas", icon: <LaptopIcon />, href: "/provas" },
   { key: "nova-prova", label: "Nova prova", icon: <PlusIcon />, href: "/nova-prova" },
-  { key: "escanear", label: "Escanear", icon: <ScanIcon /> },
+  { key: "escanear", label: "Escanear", icon: <ScanIcon />, href: "/escanear" },
   { key: "relatorios", label: "Relatorios", icon: <ChartIcon /> },
   { key: "usuarios", label: "Usuarios", icon: <UserIcon />, href: "/usuarios" },
 ];
```

Uma unica linha alterada em todo o layout. Nenhuma outra mudanca no
layout, sidebar, menu, ou qualquer componente compartilhado.

### 6.6 Integracao com Supabase Realtime

**NAO** faz parte do Lote A. Realtime e do Componente 15 (Wave 4 —
Dashboard). A pagina `/escanear` e puramente acionada pelo usuario, sem
subscribers.

### 6.7 Impacto em paginas existentes (zero)

- `/provas/[id]` vai passar a mostrar movimentacoes reais no placeholder
  de timeline **automaticamente** — o endpoint ja retorna o contrato
  certo, e o placeholder atual ja itera o array. Nenhuma mudanca de
  codigo. Se a Renan quiser o polish da timeline visual, isso e C12
  (Lote C).
- `/provas` (listagem) vai mostrar provas com status variados conforme
  movimentacoes acontecerem — zero mudanca de codigo.
- `/nova-prova` — intocada.
- `/configuracoes` — intocada.
- `/usuarios` — intocada.
- `/login` — intocada.

---

## 7. Storage R2

**Nao aplicavel ao Lote A.**

Nenhum dos componentes 10 e 11 escreve ou le R2. A assinatura digital e
armazenada **como bytea dentro da tabela `movimentacoes`** — nao como
arquivo separado no R2. Motivos:

1. Tamanho: assinatura PNG de canvas e tipicamente 20-100 KB. Mesmo
   com 10 transicoes por prova, total de 200 KB-1 MB por prova,
   trivial no Postgres free tier (500 MB total). Escala bem ate
   dezenas de milhares de provas.
2. Atomicidade: o INSERT na movimentacao precisa ser atomico com o
   UPDATE do status da prova. Separar em dois storages (bytea na db,
   arquivo no R2) quebra atomicidade e introduz orfaos.
3. Auditoria: `movimentacoes` tem trigger de imutabilidade. R2 nao.
   Para RNF-005 ("log imutavel"), o bytea na tabela e mais robusto.
4. Custo operacional: zero R2 writes = zero risco de orfaos R2 no
   fluxo de transicao (diferente da criacao de prova, onde R2 e
   necessario pela natureza das imagens grandes).

**Constraint implicito:** 700 KB max no base64 do request (ver
`TransicaoRequest`) = ~500 KB PNG decodificado. Se alguem submeter
signature canvas em tela 4K com stroke grosso, pode estourar esse
limite — validar no frontend antes de enviar e comprimir se necessario.
500 KB e generoso para signature pad tipico.

---

## 8. Plano de testes

Seguindo a estrategia do DAT v2.0 (Secao 3 — tres camadas) + padrao
Wave 2 (cobertura 95-100% nos arquivos novos).

### 8.1 Camada 1 — Testes unitarios (sem DB, sem HTTP)

**Arquivo existente: `backend/tests/test_state_machine.py`**
- 26 testes ja existentes cobrem `TRANSICOES`, `ATORES_POR_TRANSICAO`,
  `determinar_rota`, `validar_transicao`, `pode_cancelar`. **Nao
  alterar** exceto o teste do stub:
  - Teste `test_executar_transicao_e_stub` vai precisar **substituir**
    por testes reais do `executar_transicao`. O stub morre no sub-bloco
    A.1.

**Novos testes em `test_state_machine.py` para `executar_transicao`:**
1. Happy path: CRIADA -> RETIRADA com vendedor MATRIZ. Verifica:
   - `db.add` chamado com Movimentacao correta
   - `prova.status == RETIRADA_PELO_VENDEDOR` apos a chamada
   - `prova.rota is None` (so persiste na aprovacao)
   - `movimentacao.rota_no_momento is None`
   - `log_audit` chamado com `acao = "transitar_status"`
2. Happy path aprovacao MATRIZ: RETIRADA -> APROVADA. Verifica:
   - `prova.rota == PADRAO`
   - `movimentacao.rota_no_momento == PADRAO`
   - audit log contem `rota_depois == PADRAO`
3. Happy path aprovacao FILIAL: RETIRADA -> APROVADA. Verifica:
   - `prova.rota == DIRETA`
4. Happy path reprovacao com motivo: RETIRADA -> REPROVADA.
5. Rejeicao: reprovacao sem motivo -> ValueError.
6. Rejeicao: reprovacao com motivo vazio/whitespace -> ValueError.
7. Rejeicao: transicao ilegal -> TransicaoInvalidaError.
8. Rejeicao: ator errado -> AtorNaoAutorizadoError.
9. Rejeicao: assinatura vazia -> ValueError.
10. Rota MATRIZ: APROVADA -> DE_VOLTA_3STUDIO com vendedor Matriz OK.
11. Rota MATRIZ: APROVADA -> DE_VOLTA_3STUDIO com vendedor Filial
    rejeita (rota errada -> AtorNaoAutorizadoError).
12. Rota FILIAL: APROVADA -> ENCAMINHADA_A_CLICHERIA com vendedor Filial
    OK.
13. Rota FILIAL: APROVADA -> ENCAMINHADA_A_CLICHERIA com vendedor Matriz
    rejeita.
14. Motorista: COM_MOTORISTA -> ENVIADA feliz.
15. Clicheria: ENVIADA -> RECEBIDA feliz.
16. Clicheria: ENCAMINHADA -> RECEBIDA feliz.
17. 3Studio: DE_VOLTA_3STUDIO -> COM_MOTORISTA feliz.
18. **Reinicio de ciclo (C14 futuro):** REPROVADA -> CRIADA por STUDIO
    funciona + `prova.ciclo_atual` incrementa + `prova.rota = None`.
    Este teste verifica o gancho do contrato sem criar endpoint.
19. Admin bypassa setor em qualquer transicao valida.
20. Inserir movimentacao copia `prova.ciclo_atual` no momento (testar
    com ciclo_atual=2 pre-setado).

Meta de cobertura: 100% das linhas novas de `executar_transicao`.

**Novos testes de qrcode_service** (apenas se necessario — a funcao
`validar_payload_qr` ja esta coberta por testes Wave 2). Adicionar
talvez:
21. `test_validar_payload_qr_com_prefixo_errado_retorna_false`
22. `test_validar_payload_qr_com_hash_truncado_errado_retorna_false`

(Confirmar no sub-bloco A.1 se esses testes ja existem — se sim,
pular.)

### 8.2 Camada 2 — Testes de integracao (`test_provas_api.py`)

Estender o arquivo existente (nao criar novo). Seguindo o padrao de 59
testes Wave 2.

**Testes para `POST /api/v1/provas/scan` (C10):**
23. `test_scan_happy_path_vendedor_matriz` — scan de prova CRIADA por
    VENDEDOR retorna transicoes_permitidas = [RETIRADA_PELO_VENDEDOR].
24. `test_scan_prova_nao_encontrada_retorna_404` — payload com nro_req
    inexistente.
25. `test_scan_payload_formato_invalido_retorna_422` — payload sem
    prefixo 3SD.
26. `test_scan_hash_nao_bate_retorna_422` — payload com nro_req certo
    mas hash truncado errado.
27. `test_scan_scoping_vendedor_outra_prova_retorna_404` — vendedor A
    escaneando prova do vendedor B.
28. `test_scan_scoping_motorista_fora_status_retorna_404` — motorista
    escaneando prova em status CRIADA (so ve COM_MOTORISTA).
29. `test_scan_scoping_clicheria_fora_status_retorna_404`.
30. `test_scan_vendedor_aprovada_matriz_transicoes_so_de_volta` — valida
    que transicoes_permitidas contem apenas DE_VOLTA_3STUDIO.
31. `test_scan_vendedor_aprovada_filial_transicoes_so_encaminhada`.
32. `test_scan_status_retirada_ator_vendedor_motivo_obrigatorio` —
    motivo_obrigatorio_em contem REPROVADA_PELO_VENDEDOR.
33. `test_scan_db_error_returns_502` — padrao ADR-074.
34. `test_scan_audit_log_criado` — valida que log_audit foi chamado.
35. `test_scan_sem_token_retorna_401`.

**Testes para `POST /api/v1/provas/{id}/transicoes` (C11):**
36. `test_transicao_happy_criada_para_retirada_vendedor_matriz` —
    vendedor scaneia CRIADA, assina, retirada registra. Valida
    response + DB state (via refresh).
37. `test_transicao_happy_retirada_para_aprovada_matriz` — valida
    `prova.rota == PADRAO` persistido.
38. `test_transicao_happy_retirada_para_aprovada_filial` — valida
    `prova.rota == DIRETA` persistido.
39. `test_transicao_happy_retirada_para_reprovada_com_motivo`.
40. `test_transicao_retirada_para_reprovada_sem_motivo_retorna_422`.
41. `test_transicao_retirada_para_reprovada_motivo_whitespace_retorna_422`.
42. `test_transicao_happy_aprovada_matriz_para_de_volta_3studio`.
43. `test_transicao_happy_aprovada_filial_para_encaminhada_clicheria`.
44. `test_transicao_aprovada_matriz_tentando_encaminhada_retorna_422`.
45. `test_transicao_aprovada_filial_tentando_de_volta_retorna_422`.
46. `test_transicao_happy_de_volta_para_com_motorista_studio`.
47. `test_transicao_happy_com_motorista_para_enviada_motorista`.
48. `test_transicao_happy_enviada_para_recebida_clicheria`.
49. `test_transicao_happy_encaminhada_para_recebida_clicheria`.
50. `test_transicao_ator_errado_retorna_422` — vendedor tentando agir
    quando estado exige motorista.
51. `test_transicao_ilegal_retorna_422` — tentar pular estado.
52. `test_transicao_estado_terminal_retorna_422` — tentar transitar
    RECEBIDA_PELA_CLICHERIA para qualquer coisa.
53. `test_transicao_prova_inexistente_retorna_404`.
54. `test_transicao_uuid_invalido_retorna_404`.
55. `test_transicao_scoping_esconde_prova_retorna_404`.
56. `test_transicao_cancelada_rejeitada_422` — rejeita CANCELADA no
    endpoint (vai para C13).
57. `test_transicao_criada_como_destino_rejeitada_422` — rejeita CRIADA
    (vai para C14).
58. `test_transicao_assinatura_vazia_retorna_422`.
59. `test_transicao_assinatura_base64_invalido_retorna_422`.
60. `test_transicao_assinatura_muito_grande_retorna_422` — > 700 KB.
61. `test_transicao_race_condition_retorna_409` — mockar: leitura
    carrega CRIADA, mas executar_transicao levanta TransicaoInvalidaError
    apos FOR UPDATE porque status mudou para RETIRADA por outro request.
    Traduzir para 409.
62. `test_transicao_db_error_returns_502` — padrao ADR-074.
63. `test_transicao_audit_log_completo` — verifica estrutura do
    detalhes_json.
64. `test_transicao_movimentacao_copia_ciclo_atual`.
65. `test_transicao_movimentacao_copia_rota_depois_da_aprovacao`.
66. `test_transicao_sem_token_retorna_401`.

**Total novos testes: ~44 (13 scan + 31 transicoes).** Suite vai de
308 -> ~352 testes backend.

**Cobertura alvo:**
- `app/services/state_machine.py`: 100%
- `app/api/v1/provas.py`: manter >= 95%, adicionando cobertura para os
  novos handlers
- `app/domain/schemas/prova.py`: manter 100% nos schemas novos
  (ScanRequest, ScanResponse, TransicaoRequest, TransicaoResponse)

### 8.3 Camada 3 — E2E (Playwright)

DAT v2.0 descreve: "Fluxo completo: login -> escanear QR -> assinar ->
confirmar transicao" + "camera mockada via API de permissoes" +
"cenarios criticos cobertos manualmente antes de cada deploy em staging".

**Lote A decisao:** seguir o padrao Wave 2 — **validacao manual em
staging** usando Playwright apenas se o custo justificar, ou testes
manuais no ambiente de preview local. Motivo:
- Playwright e muito sensivel a camera e mockar video stream. Testes
  flaky sao o pior resultado.
- Wave 2 nao escreveu testes Playwright e fechou OK.
- A auditoria Wave 2 aceitou "testes de integracao com Postgres real"
  como debito para Wave 6 (F17/F22/F24).
- O volume de testes de integracao com mocks (Camada 2) ja e 44
  testes novos cobrindo praticamente todos os paths.

**Validacao manual prevista no sub-bloco A.6:**
1. Login como admin/3Studio -> criar prova -> imprimir etiqueta ->
   abrir `/escanear` -> scan do QR -> ver transicoes = [RETIRADA].
2. Login como VENDEDOR MATRIZ -> escanear -> aprovar -> escanear -> ver
   transicao = DE_VOLTA_3STUDIO.
3. Login como STUDIO -> escanear a mesma prova -> ver transicao =
   COM_MOTORISTA.
4. Login como MOTORISTA -> escanear -> confirmar -> ENVIADA.
5. Login como CLICHERIA -> escanear -> confirmar -> RECEBIDA (terminal).
6. Fluxo FILIAL: vendedor Filial aprova -> escanear -> ENCAMINHADA ->
   clicheria -> RECEBIDA.
7. Fluxo reprovacao: vendedor escaneia RETIRADA -> reprovar com motivo
   -> verifica que aparece como REPROVADA_PELO_VENDEDOR.
8. Tentar escanear QR de prova invalida (payload editado) -> espera
   422.
9. Tentar acessar `/escanear` sem permissao camera -> mensagem clara.
10. Tentar no Chrome / Firefox / Edge — confirmar que lib funciona em
    todos.

Cada caminho **registrado no closeout** do Lote A (`WAVE3_LOTE_A_CLOSEOUT.md`).

### 8.4 Tests infra — mudancas

- `backend/tests/conftest.py` **nao precisa** de fixtures novas. Ja tem
  `mock_db`, `vendedor_matriz`, `vendedor_filial`, `admin_user`.
  Possivel adicionar um `motorista_user` e `clicheria_user` para
  conveniencia dos novos testes — verificar se vale a pena.

---

## 9. Riscos e pontos de atencao

### 9.1 Riscos tecnicos

**R1 — html5-qrcode em producao:**
- A lib funciona em HTTPS obrigatoriamente (browser exige SSL para
  getUserMedia exceto em localhost). Vercel ja serve HTTPS por padrao,
  entao zero problema em producao.
- Preview local via `next dev` em HTTP tambem funciona porque localhost
  e exceto.
- **Risco:** funciona em Chrome/Firefox/Edge desktop e mobile. Safari
  iOS historicamente tinha problemas com getUserMedia em inner iframes
  — `/escanear` nao e iframe, entao OK. Validar manualmente no Safari
  no sub-bloco A.6.

**R2 — Reentrance da camera ao desmontar:**
- html5-qrcode requere explicitamente `.stop()` + `.clear()` no
  cleanup do `useEffect`. Se esquecermos, usuario volta pro menu e a
  camera fica em uso, precisando refresh da pagina.
- **Mitigacao:** teste manual explicito no sub-bloco A.6 (navegar para
  `/escanear`, voltar para `/provas`, verificar se a camera parou).

**R3 — Race condition em transicao simultanea:**
- Dois usuarios escaneando a mesma prova ao mesmo tempo. Sem lock, dois
  INSERTs em `movimentacoes` com mesmo `status_anterior` seriam
  gravados mas um dos UPDATEs falharia ou pior — ambos passariam e o
  segundo sobrescreveria.
- **Mitigacao:** `SELECT ... FOR UPDATE` no `_carregar_prova_com_scoping`
  quando chamado de `POST /transicoes` (novo argumento `lock=True`).
  Isso serializa os dois requests. O segundo ve o estado ja atualizado e
  `validar_transicao` levanta `TransicaoInvalidaError` -> traduzir para
  **409 Conflict** (novo codigo HTTP no endpoint). Teste 61 cobre isso.

**R4 — Assinatura grande:**
- Canvas em device alto DPI + stroke alto pode gerar PNG de 500+ KB.
  Nosso limite e 700 KB base64 = ~500 KB PNG.
- **Mitigacao:** frontend comprime o canvas para `toDataURL("image/png",
  0.6)` (60% quality). Se mesmo assim estourar, mostrar erro amigavel
  antes de enviar.
- Alternativamente, canvas export em JPEG (menor que PNG mas perde
  transparencia — nao e critico para assinatura).

**R5 — Timing attack em validar_payload_qr:**
- Ja mitigado no ADR-033 via `hmac.compare_digest`. Nenhum trabalho
  novo.

**R6 — Sincronizacao entre state_machine e RLS:**
- Se alguem alterar `ATORES_POR_TRANSICAO` sem atualizar
  `pol_movimentacoes_select`, rota fica inconsistente.
- **Mitigacao:** comentario explicito no topo do `005_initplan_optimization.sql`
  e `006_movimentacoes_insert_and_expand_select.sql` ja aponta para o
  state_machine.py. Documentar tambem no DECISIONS.md ADR novo.

**R7 — Re-assignacao de vendedor entre scan e transicao:**
- Admin desativa o vendedor ou muda localizacao entre o scan e o
  submit da assinatura. O que a validacao deve fazer?
- **Decisao:** o `executar_transicao` le o estado do usuario **atual**
  (o que submete) via `get_current_user`. Se o estado do usuario
  submissor mudar, validacao falha com 403/422. Nao ha "memoria" do
  estado da prova no scan — cada submit e validado fresco. Isso esta
  alinhado com o desenho sem estado do endpoint.

### 9.2 Limites de free tier

**Supabase (500 MB Postgres):**
- Cada movimentacao escreve ~100 KB em `movimentacoes.assinatura_digital`
  (bytea) + ~1 KB em `audit_logs`. Total ~100 KB por transicao.
- Volume esperado: 10 transicoes por prova media × 500 provas/mes =
  5000 transicoes/mes × 100 KB = 500 MB/ano.
- **Timing:** essa projecao esgota o free tier em ~1 ano. Observar
  metric `pg_database_size` via Supabase dashboard apos Wave 3 ir ao
  ar por 1 mes e extrapolar. Se o volume real exceder, opcoes:
  1. Reduzir qualidade do canvas (150x150 vs 400x400).
  2. Mover assinaturas para R2 em um cleanup job Wave 6.
  3. Upgrade para Supabase Pro ($25/mes).

**Cloudflare R2 (10 GB gratis):**
- Lote A nao escreve R2. Zero impacto.

**Railway (backend):**
- Cada transicao e 3 INSERTs + 1 UPDATE + audit. Tempo <100 ms tipico.
  Zero impacto no free tier (500 horas/mes para quanto basta).

**Vercel (frontend):**
- Build adiciona ~150 KB ao bundle `/escanear` (html5-qrcode +
  react-signature-canvas). Ainda bem abaixo do limite Vercel.

### 9.3 Pontos de atencao operacionais

**P1 — Primeira transicao em producao + usuarios de teste:**
- Ha **5** provas em `CRIADA` em producao (ver §4.3). A primeira vez que
  alguem escanear uma delas na Wave 3, uma linha em `movimentacoes` sera
  criada pela primeira vez no sistema. Validar que nada explode com linha #1.
- **Usuarios ativos no banco (3 total):**
  - `admin@3studio.com.br` (STUDIO, is_admin=true)
  - `ops@3studio.com.br` (STUDIO, is_admin=true)
  - `mariosouza@teste.com.br` (**VENDEDOR FILIAL**, nao-admin) — unico
    vendedor cadastrado.
- **Nao ha vendedor MATRIZ cadastrado.** Isso impede o smoke E2E da rota
  padrao (MATRIZ → 3Studio → Motorista → Clicheria) sem cadastro previo.
  Tambem nao ha usuarios MOTORISTA nem CLICHERIA.
- **Acao para o sub-bloco A.6:** antes do smoke E2E em staging, cadastrar
  via admin os 4 usuarios de teste necessarios: 1 VENDEDOR MATRIZ, 1
  MOTORISTA, 1 CLICHERIA, e opcionalmente 1 STUDIO nao-admin para teste do
  "DE_VOLTA_3STUDIO -> COM_MOTORISTA". Os 2 admins STUDIO existentes
  bypassam a validacao de setor via `is_admin=true` (state_machine
  `validar_transicao` linha 207), entao alguns cenarios de "ator errado"
  exigem um non-admin para serem observados.

**P2 — Deploy order:**
- Backend deve ir antes do frontend. Se for invertido, o frontend
  chama endpoints que nao existem -> 404. Padrao usual, nao ha
  regressao.

**P3 — Variaveis de ambiente:**
- Nenhuma variavel nova. `QR_CODE_HMAC_SECRET` ja existe desde o C06.
  Mesma chave e usada para validar (constant-time) — nao rotacionar
  agora (Wave 6 tem rotacao no escopo).

**P4 — Documentacao:**
- Atualizar `CLAUDE.md` para:
  - Atualizar tabela de Waves (Wave 3 parcial apos Lote A)
  - Atualizar contagem de rotas publicas (24 -> 26)
  - Atualizar tabela de rotas frontend (adicionar `/escanear`)
  - Menu do dashboard: "Escanear" deixa de ser placeholder
  - **Corrigir a linha "2 admins ativos" (atual: desatualizada)** — hoje ha
    3 usuarios ativos: 2 admins + 1 vendedor FILIAL (Mario Souza). Essa
    linha deve refletir o snapshot real no momento do closeout; **ou** (se
    os usuarios de teste de P1 forem criados so para smoke e depois
    desativados) pode continuar descrevendo a "operacao" em termos de
    admins master. A decisao fica no closeout.
- Esse update faz parte do closeout, nao de cada sub-bloco — evita
  conflito em commits paralelos.

**P5 — Fora do escopo mas importante de lembrar:**
- Dashboard (C15, Wave 4) precisa de Realtime. Wave 3 nao.
- O timer de "atrasada" (RN-008) so dispara com base em `updated_at`
  ou na data da ultima movimentacao. Wave 4 decide.

### 9.4 Riscos que **nao** existem

Nao contam como riscos porque sao explicitamente fora de escopo ou
nao aplicam:
- Downtime de deploy — Railway e Vercel fazem blue-green.
- Perda de dados — triggers de imutabilidade garantem.
- Rollback de migration — nao ha migration Alembic no Lote A.
- Conflito com Wave 2 — zero mudanca de schema.

---

## 10. Sub-blocos de implementacao

Quebra do Lote A em 6 sub-blocos sequenciais. Cada um termina com
commit proprio + atualizacao incremental de `CHANGELOG.md` e (se
houver decisao nova) `DECISIONS.md`. Apos cada sub-bloco backend, rodo
`pytest --cov` e reporto o delta.

### Sub-bloco A.1 — State machine `executar_transicao` (backend puro)

**Arquivos tocados:**
- `backend/app/services/state_machine.py` — substituir o stub
  `executar_transicao` pela implementacao real + adicionar helpers
  privados.
- `backend/tests/test_state_machine.py` — substituir o teste do stub,
  adicionar os 17 testes novos (numeros 1-18 + 19-20 da secao 8.1).
- `DECISIONS.md` — ADR novo registrando decisoes nao capturadas no
  ADR-040:
  - Regra extra "rota no momento" (MATRIZ->DE_VOLTA, FILIAL->
    ENCAMINHADA) enforcada fora da tabela ATORES.
  - Incremento de ciclo_atual na transicao REPROVADA->CRIADA como
    gancho para C14.
- `CHANGELOG.md` — entrada Sessao 23 sub-bloco A.1.

**Entregaveis:**
- `executar_transicao(db, *, prova, status_novo, usuario,
  assinatura_digital, motivo_reprovacao, motivo_cancelamento=None,
  request=None) -> Movimentacao` completa com assinatura da secao 3.4.
- 100% cobertura da funcao.
- Suite: 308 + ~17 = ~325 testes.

**Validacao:**
- `pytest backend/tests/test_state_machine.py -v` passa.
- `pytest --cov=app/services/state_machine --cov-report=term-missing`
  mostra 100%.
- `ruff check backend/` limpo.

**Gate para o proximo sub-bloco:** OK dos testes + approval do commit.

### Sub-bloco A.2 — RLS: movimentacoes insert + expansao select

**Arquivos tocados:**
- `backend/migrations/rls/006_movimentacoes_insert_and_expand_select.sql`
  — novo arquivo, idempotente (DROP IF EXISTS + CREATE).
- `backend/migrations/rls/apply_rls.py` — se houver lista/manifest,
  adicionar o novo arquivo.
- `docs/db/schema.sql` — atualizar a secao "6. ROW LEVEL SECURITY" para
  refletir 11 -> 12 policies (se contarmos o insert novo) ou melhor,
  documentar o conjunto atual na migration RLS.
- `DECISIONS.md` — ADR novo (talvez ADR-081) registrando:
  - Decisao de adicionar pol_movimentacoes_insert admin-only.
  - Decisao de expandir pol_movimentacoes_select para cobrir MOTORISTA
    e CLICHERIA (resolve F03 da Sessao 22).
- `CHANGELOG.md` — entrada sub-bloco A.2.

**Entregaveis:**
- Script SQL aplicado em producao via MCP `execute_sql`.
- Verificacao via `pg_policies`: 12 policies totais no public.
- Advisor Supabase limpo (exceto os 2 ja aceitos).

**Validacao:**
- Rodar MCP `execute_sql("SELECT policyname FROM pg_policies WHERE
  schemaname='public' AND tablename='movimentacoes' ORDER BY
  policyname")` -> ver 2 policies: `pol_movimentacoes_insert` e
  `pol_movimentacoes_select`.
- Rodar MCP `get_advisors type=security` -> confirmar que nada mudou.

**Gate:** verificacao manual via MCP que o aplicativo ainda funciona
(smoke test) + approval.

### Sub-bloco A.3 — Backend endpoint `POST /provas/scan` (C10)

**Arquivos tocados:**
- `backend/app/domain/schemas/prova.py` — adicionar `ScanRequest`,
  `ScanResponse`.
- `backend/app/api/v1/provas.py` — novo handler `scan_prova`, com helper
  interno para calcular transicoes permitidas dado o estado atual + o
  usuario + a prova. Padrao de try/except + 502 ja estabelecido.
- `backend/tests/test_provas_api.py` — 13 testes novos (numeros 23-35
  da secao 8.2).
- `DECISIONS.md` — ADR novo se houver decisao nao obvia (ex: motivo de
  retornar 404 em vez de 403 para prova fora do scoping — ja e padrao
  ADR-049, entao talvez nao precise).
- `CHANGELOG.md` — entrada sub-bloco A.3.

**Entregaveis:**
- Endpoint `POST /api/v1/provas/scan` respondendo conforme contrato
  secao 5.1.
- Cobertura do novo handler: 100%.
- Cobertura global de `provas.py`: manter >= 95%.
- Suite: ~325 + 13 = ~338 testes.

**Validacao:**
- `pytest backend/tests/test_provas_api.py::test_scan_* -v` passa.
- `pytest --cov=app/api/v1/provas --cov-report=term-missing` mostra >=
  95%.
- Smoke manual via curl/Postman: payload valido retorna ScanResponse.

**Gate:** approval + OK do closeout parcial.

### Sub-bloco A.4 — Backend endpoint `POST /provas/{id}/transicoes` (C11)

**Arquivos tocados:**
- `backend/app/domain/schemas/prova.py` — adicionar `TransicaoRequest`,
  `TransicaoResponse`.
- `backend/app/api/v1/provas.py` — novo handler `executar_transicao_prova`
  (endpoint). Orquestra o fluxo: carrega com FOR UPDATE, chama
  `state_machine.executar_transicao`, commit, retorna response.
  Extende `_carregar_prova_com_scoping` para aceitar `lock: bool =
  False`, default False para callers existentes (zero impacto em C06-
  C08-Wave 2). Nova variante passa `.with_for_update()` no select.
- `backend/tests/test_provas_api.py` — 31 testes novos (numeros 36-66
  da secao 8.2).
- `DECISIONS.md` — ADR novo capturando:
  - Decisao de usar FOR UPDATE para serializar transicoes concorrentes.
  - Decisao de limite 700 KB no base64.
  - Decisao de rejeitar CANCELADA e CRIADA como destino neste
    endpoint.
- `CHANGELOG.md` — entrada sub-bloco A.4.

**Entregaveis:**
- Endpoint `POST /api/v1/provas/{id}/transicoes` respondendo conforme
  contrato secao 5.2.
- Cobertura do novo handler: 100%.
- Cobertura global de `provas.py`: manter >= 95%.
- Suite: ~338 + 31 = ~369 testes.

**Validacao:**
- `pytest backend/tests/test_provas_api.py::test_transicao_* -v` passa.
- `pytest --cov` mostra delta esperado.
- Smoke manual: criar prova -> scan -> transicao feliz -> detalhe da
  prova mostra novo status + movimentacao.

**Gate:** approval.

### Sub-bloco A.5 — Frontend: `/escanear` com scanner + assinatura

**Arquivos criados/tocados:**
- `frontend/package.json` — adicionar `html5-qrcode`,
  `react-signature-canvas`, `@types/react-signature-canvas`.
- `frontend/package-lock.json` — gerado por `npm install`.
- `frontend/src/lib/types/prova.ts` — adicionar `ScanRequest`,
  `ScanResponse`, `TransicaoRequest`, `TransicaoResponse`.
- `frontend/src/hooks/useScanProva.ts` — novo.
- `frontend/src/hooks/useExecutarTransicao.ts` — novo.
- `frontend/src/hooks/useScanner.ts` — novo (wrapper html5-qrcode).
- `frontend/src/app/(dashboard)/escanear/page.tsx` — nova pagina.
- `frontend/src/app/(dashboard)/escanear/escanear.module.css` — novo.
- `frontend/src/app/(dashboard)/escanear/_components/` (se
  necessario):
  - `QrScanner.tsx`
  - `SignatureCapture.tsx`
  - `ProvaPreview.tsx`
  - `TransicoesDisponiveis.tsx`
  - `TransicaoConfirmModal.tsx`
  (alguns destes podem acabar inline na page.tsx se ficarem pequenos)
- `frontend/src/app/(dashboard)/layout.tsx` — 1 linha: adicionar
  `href: "/escanear"` ao item do menu.
- `DECISIONS.md` — ADR novo: decisao de usar html5-qrcode + decisoes
  de UX.
- `CHANGELOG.md` — entrada sub-bloco A.5.

**Entregaveis:**
- Pagina `/escanear` funcional: abre camera, decodifica QR, chama
  `/scan`, mostra detalhes + botoes, abre modal com assinatura, chama
  `/transicoes`, mostra sucesso ou erro.
- `tsc --noEmit` limpo.
- `next lint` limpo.
- `next build` limpo. Bundle size tracking (antes/depois) registrado
  no closeout.
- Dev server `preview_start` sobe sem erro e pagina carrega.
- Smoke com browser: abrir `/escanear`, scanner mostra pedido de
  permissao, ao conceder abre camera.

**Validacao:**
- Visual inspection via `preview_screenshot` da pagina idle.
- `preview_inspect` de elementos chave (botoes, scanner container).
- `preview_console_logs` sem erros.

**Gate:** approval.

### Sub-bloco A.6 — Smoke end-to-end em staging + closeout

**Arquivos tocados:**
- `CLAUDE.md` — atualizar:
  - Tabela de Waves (Wave 3 Lote A completo)
  - Contagem de rotas backend (24 -> 26)
  - Tabela de paginas frontend (adicionar `/escanear`)
  - Nota sobre Wave 3 Lote A completo
- `WAVE3_LOTE_A_CLOSEOUT.md` — novo arquivo, conteudo descrito em 11
  abaixo.
- `DECISIONS.md` — ADR meta de fechamento do Lote A.
- `CHANGELOG.md` — entrada final com metricas consolidadas.

**Pre-requisito — seed de usuarios de teste:**
O banco hoje so tem 2 admins STUDIO + 1 vendedor FILIAL (Mario Souza). Antes
do smoke, cadastrar via `POST /api/v1/users/` (logado como admin) os
usuarios minimos abaixo. Nomes e emails sao sugestoes — ajustar se colidir
com usuarios ja cadastrados:

| nome | email | setor | localizacao |
|---|---|---|---|
| Vendedor Matriz Teste | vendedor.matriz@teste.com.br | VENDEDOR | MATRIZ |
| Motorista Teste | motorista@teste.com.br | MOTORISTA | — |
| Clicheria Teste | clicheria@teste.com.br | CLICHERIA | — |

O vendedor FILIAL existente (Mario Souza) ja cobre o smoke da rota direta.
Esses 3 novos usuarios cobrem rota padrao + etapas Studio/Motorista/Clicheria.
Todos **nao-admin** — garantem que a validacao de setor do
`state_machine.validar_transicao` e exercitada corretamente.

**Validacoes manuais (Lote A smoke, conforme secao 8.3):**
1. Criar uma prova em staging como admin.
2. Imprimir etiqueta em PDF, abrir no celular.
3. Login como vendedor MATRIZ (Vendedor Matriz Teste), `/escanear`, scan
   do QR da prova. Conceder permissao camera. Assinar. Verificar status
   -> RETIRADA.
4. Continuar como vendedor, scan -> aprovar -> verificar status
   APROVADA + rota = PADRAO.
5. Scan novamente -> DE_VOLTA_3STUDIO.
6. Login como STUDIO (admin@3studio.com.br) -> scan -> COM_MOTORISTA.
7. Login como MOTORISTA (Motorista Teste) -> scan -> ENVIADA.
8. Login como CLICHERIA (Clicheria Teste) -> scan -> RECEBIDA (terminal).
9. Repetir 3-8 com vendedor FILIAL (Mario Souza), validando rota direta:
   vendedor FILIAL aprova -> ENCAMINHADA_A_CLICHERIA -> clicheria -> RECEBIDA.
10. Teste de reprovacao: criar nova prova, vendedor scan, reprovar
    com motivo, abrir detalhe -> ver motivo preservado.
11. Teste de erro: payload invalido -> mensagem clara.
12. Teste de camera: voltar para `/provas` e verificar que a camera
    parou.
13. Teste no Safari (desktop ou iOS se disponivel).

**Pos-smoke — limpeza:**
- Os usuarios de teste criados para este smoke podem ser desativados
  (`ativo=false`) ou mantidos conforme decisao do closeout. Sem limpeza,
  contagem real em producao passa a ser 5 usuarios (2 admins + 1 FILIAL +
  1 MATRIZ + 1 MOTORISTA + 1 CLICHERIA).
- As provas criadas/escaneadas no smoke podem ser marcadas como CANCELADAS
  (RN-005) ou deixadas no estado terminal — nao mexem na Wave 4+ porque o
  dashboard ainda nao existe.

**Metricas finais:**
- Total de testes passing.
- Cobertura global + por arquivo.
- Bundle size delta.
- Ruff, tsc, lint, build.
- Screenshots das paginas novas.

**Gate:** approval final.

---

## 11. Estrutura do `WAVE3_LOTE_A_CLOSEOUT.md` (para Fase 5)

Apenas o esboco, para deixar claro o que sera entregue quando o Lote A
fechar:

1. **Checklist DoD C10** — 8 itens globais + criterios US-002.
2. **Checklist DoD C11** — 8 itens globais + criterios US-003 a US-009.
3. **Cobertura de testes final:**
   - Backend global %
   - `state_machine.py` %
   - `provas.py` %
   - `schemas/prova.py` %
   - Frontend: nao ha metricas de cobertura (sem jest) — anota-se TS
     strict zero errors + build ok.
4. **Arquivos criados** (listagem completa).
5. **Arquivos modificados** (listagem com motivo resumido).
6. **Evidencias de integracao com Waves anteriores:**
   - 0 alteracoes de schema (alembic_version permanece 009).
   - 0 alteracoes em endpoints existentes.
   - 0 alteracoes no layout exceto a linha do menu.
   - 0 alteracoes nos hooks e paginas existentes.
   - RLS 11 -> 12 policies (uma nova + uma expandida).
7. **Contratos expostos para Lotes B e C:**
   - `executar_transicao` signature publica.
   - Rejeicoes explicitas no endpoint (CANCELADA, CRIADA).
   - Gancho de incremento de ciclo pronto para C14.
   - `MovimentacaoResponse` populado para C12 consumir.
   - `provas_digitais.rota` populada pela primeira vez.
8. **Riscos residuais para Lote B (C12):**
   - Timeline visual precisa polish.
   - Framer Motion ainda nao instalado.
9. **Riscos residuais para Lote C (C13, C14):**
   - Decidir endpoint de cancelamento: unificar no `/transicoes` ou
     criar rota dedicada (ver secao 3.2).
   - Definir endpoint de reinicio de ciclo (ver secao 3.3).
10. **Screenshots / smoke E2E** — conforme secao 8.3 + 10.A.6.

---

## 12. Resumo executivo

**O Lote A entrega:**
- 2 endpoints backend novos (`POST /scan` + `POST /transicoes`).
- 1 pagina frontend nova (`/escanear`).
- Maquina de estados `executar_transicao` implementada.
- 2 dependencias npm novas (`html5-qrcode`, `react-signature-canvas`).
- 1 migration RLS (INSERT em movimentacoes + expansao SELECT).
- Zero migrations Alembic.
- Zero mudanca de schema.
- Zero mudanca em endpoints ou paginas existentes (exceto 1 linha no
  layout do menu).
- ~44 testes backend novos.

**O Lote A nao entrega (explicitamente):**
- Timeline visual (C12 - Lote C futuro)
- Cancelamento de prova (C13 - Lote C futuro)
- Reinicio de ciclo (C14 - Lote C futuro)
- Dashboard Realtime (C15 - Wave 4)

**Consumo de infraestrutura:** zero novo (mesmos Postgres, Auth, R2,
Railway, Vercel).

**Risco principal:** razoavel e mitigado — `html5-qrcode` e
`react-signature-canvas` sao libs maduras e usadas em producao
amplamente. Race condition em transicao e mitigada via FOR UPDATE.

**Pergunta para o Mario:** posso prosseguir com o sub-bloco A.1? Ao
confirmar "GO LOTE A", comeco imediatamente pelo
`executar_transicao` no `state_machine.py`, commitando ao final e
reportando o delta de testes + cobertura antes de ir para o A.2.
