# Guia Visual · Wave 3 v4.0 · C12 — Timeline

**Wave:** 3 v4.0 / Componente 12
**Data inicial:** 2026-05-13 (criado como STUB pos-auditoria)
**Status:** STUB — screenshots serao adicionados pelo Mario apos smoke E2E manual
**Origem:** AUD-W3C12-003 (visual-guide.md ausente — auditoria pos-C12)
**Roteiro de smoke:** [docs/wave3-v4-c12/smoke-validation.md](smoke-validation.md)

---

## Como usar este documento

Para cada um dos 8 cenarios obrigatorios, este guia documenta:

1. **Descricao operacional** do cenario.
2. **Decisao de design relevante** (referencia a `DECISIONS.md` /
   `analysis.md §16`).
3. **Prova representativa em producao** (ou ⚠️ SKIP se nao existir
   fixture).
4. **Como reproduzir** no browser autenticado (URL + acoes).
5. **Critério de validacao visual** (o que olhar para confirmar
   aderencia).
6. **Placeholder de screenshot** — Mario captura quando rodar o
   smoke (cenario 14 do `smoke-validation.md`).

Quando Mario completar um screenshot, substituir o `[ANEXAR
SCREENSHOT]` pelo link Markdown da imagem (recomendado:
`docs/wave3-v4-c12/screenshots/cenario-N.png`).

**Distribuicao em producao** (snapshot via MCP em 2026-05-13):
| Rota | Status | Qtde | Notas |
|---|---|---|---|
| MATRIZ (v4.0) | CRIADA | 1 | `PRV-2026-05-TEX9GW` |
| PADRAO (legacy) | CANCELADA | 2 | `PRV-2026-04-XPXWKA`, `PRV-2026-04-CSN3YJ` |
| DIRETA (legacy) | RECEBIDA_PELA_CLICHERIA | 2 | `PRV-2026-04-9MGETS`, `PRV-2026-04-C67HZS` |
| DIRETA (legacy) | CANCELADA | 1 | `PRV-2026-04-XD8G73` |
| NULL (legacy puro) | CRIADA | 5 | varias |
| NULL (legacy puro) | REPROVADA_PELO_VENDEDOR | 2 | `PRV-2026-04-G5932T`, `PRV-2026-04-8Z8Z5R` |
| NULL (legacy puro) | CANCELADA | 4 | varias |
| LAM_MATRIZ / FILIAL / LAM_FILIAL | qualquer | **0** | R-4 herdado |

**Multi-ciclos:** `PRV-2026-04-B9CZ37` (rota=NULL, ciclo_atual=2).

---

## Cenario 1 — Rota Matriz em andamento

**Descricao operacional:** Prova v4.0 com `rota=MATRIZ`, sem
laminacao, em fase intermediaria do fluxo (ex.: `RETIRADA_PELO_VENDEDOR`).

**Decisoes de design relevantes:**
- D1 Vertical (orientacao da timeline).
- D2 Mesmo layout para 4 rotas + badge rota no header.
- D6 Dot amarelo + box-shadow + pulse via framer-motion (`motion.span`
  `scale=[1, 1.9, 1]`) + badge "Atual" — respeitando `useReducedMotion`.
- D10 Densa: label + ator + setor + timestamp + motivo (se aplicavel).

**Prova representativa:** `PRV-2026-05-TEX9GW` (status atual: CRIADA).

**Como reproduzir:** navegar para `/provas/<id_da_TEX9GW>` autenticado
como admin.

**Criterio de validacao visual:**
- Header tem `<span .rotaBadge>Rota: Matriz</span>` visivel.
- 6 nos da sequencia MATRIZ aparecem: 1 atual (CRIADA com dot amarelo
  + pulse + badge "Atual") + 5 pendentes (dot outline cinza + label
  "Aguardando").
- **Nao deve aparecer** bloco de laminacao (D11.3 — laminacao so para
  Lam.Matriz e Lam.Filial).
- Conector entre nos: solido nos concluidos, tracejado nos pendentes.

**Screenshot:** [ANEXAR SCREENSHOT — `screenshots/cenario-1-matriz.png`]

---

## Cenario 2 — Rota Lam. Matriz

**Descricao operacional:** Prova v4.0 com `rota=LAM_MATRIZ`, com
laminacao, em fase intermediaria (ex.: `LAMINACAO_CONCLUIDA`).

**Decisoes de design relevantes:**
- D3 Bloco visualmente separado com label "Etapa de Laminação"
  envolvendo nos adjacentes do bloco (ADR-160).
- D4 Badges textuais para contextos do motorista ("→ Laminação",
  "Laminação →", "→ Clicheria").
- D6 + D10 (vide cenario 1).

**Prova representativa:** ⚠️ **SKIP em producao** — 0 provas
LAM_MATRIZ. Mario precisa criar seed em ambiente local/staging via
`POST /api/v1/provas` com `rota: "LAM_MATRIZ"`.

**Como reproduzir (com seed):**
1. Criar prova com `rota: "LAM_MATRIZ"` (escanear como admin no
   `/nova-prova` com toggle Matriz + Laminacao).
2. Avancar manualmente algumas transicoes via `/escanear` + assinatura
   ate `LAMINACAO_CONCLUIDA`.
3. Navegar para `/provas/<id>`.

**Criterio de validacao visual:**
- Header tem `<span .rotaBadge>Rota: Lam. Matriz</span>`.
- 11 nos da sequencia LAM_MATRIZ.
- **Bloco visual `.laminationBlock`** envolvendo os 5 estados
  adjacentes do bloco de laminacao (ENCAMINHADA_PARA_LAMINACAO,
  COM_MOTORISTA_IDA_LAMINACAO, LAMINACAO_CONCLUIDA,
  COM_MOTORISTA_VOLTA_LAMINACAO, DE_VOLTA_3STUDIO_POS_LAMINACAO) — com
  borda tracejada verde `#c0ca33` + label uppercase "Etapa de
  laminação".
- Badges contextuais nos nos do motorista: "→ Laminação" para IDA,
  "Laminação →" para VOLTA, "→ Clicheria" para ENTREGA_FINAL.

**Screenshot:** [ANEXAR SCREENSHOT pos-seed — `screenshots/cenario-2-lam-matriz.png`]

---

## Cenario 3 — Rota Filial

**Descricao operacional:** Prova v4.0 com `rota=FILIAL`, sem
laminacao, fluxo simplificado de 4 etapas.

**Decisoes de design relevantes:**
- D2 Mesmo layout + badge.
- Primeiro nos: `CRIADA → ENCAMINHADA_PARA_O_VENDEDOR` (ator
  Vendedor, vide M-1 do contrato §8 que confirma esta atribuicao).

**Prova representativa:** ⚠️ **SKIP em producao** — 0 provas FILIAL.
Seed local/staging.

**Criterio de validacao visual:**
- Header com `Rota: Filial`.
- 4 nos da sequencia FILIAL.
- Sem bloco de laminacao.

**Screenshot:** [ANEXAR SCREENSHOT pos-seed — `screenshots/cenario-3-filial.png`]

---

## Cenario 4 — Rota Lam. Filial

**Descricao operacional:** Prova v4.0 com `rota=LAM_FILIAL`, com
laminacao em fluxo simplificado de 7 etapas.

**Decisoes de design relevantes:**
- D3 Bloco visual de laminacao.
- D4 Badges contextuais do motorista (so `→ Laminação`, sem volta).

**Prova representativa:** ⚠️ **SKIP em producao** — 0 provas
LAM_FILIAL. Seed local/staging.

**Criterio de validacao visual:**
- Header com `Rota: Lam. Filial`.
- 7 nos da sequencia LAM_FILIAL.
- Bloco visual de laminacao envolvendo 3 estados
  (ENCAMINHADA_PARA_LAMINACAO + COM_MOTORISTA_IDA_LAMINACAO +
  LAMINACAO_CONCLUIDA).

**Screenshot:** [ANEXAR SCREENSHOT pos-seed — `screenshots/cenario-4-lam-filial.png`]

---

## Cenario 5 — Multiplos ciclos (RF-009 v4.0)

**Descricao operacional:** Prova reprovada e reiniciada — `ciclo_atual >= 2`.

**Decisoes de design relevantes:**
- D5 Empilhados verticalmente com separador "↻ reinício de ciclo"
  entre ciclos.
- Header de cada ciclo passado: "Ciclo N · reprovado em DD/MM" +
  badge "Reprovado".
- Header do ciclo atual: "Ciclo N" + badge "Em andamento".
- Motivo da reprovacao destacado em vermelho dentro do ciclo passado.

**Prova representativa:** `PRV-2026-04-B9CZ37` (rota=NULL,
ciclo_atual=2, 3 movs no historico).

**Como reproduzir:** navegar para `/provas/<id_da_B9CZ37>`.

**Criterio de validacao visual:**
- 2 ciclos empilhados.
- Separador `<li .cycleSeparator aria-hidden="true">↻ reinício de
  ciclo</li>` visivel entre eles.
- Ciclo 1 com header de reprovacao + motivo em vermelho.
- Ciclo 2 com header de "Em andamento" + dot atual com pulse.
- **Heuristica D11.2 (ADR-159):** como `rota=NULL` e
  `vendedor_localizacao=FILIAL`, header mostra `Rota: Filial` +
  sequencia `LEGACY_ROTA_DIRETA`.

**Screenshot:** [ANEXAR SCREENSHOT — `screenshots/cenario-5-multi-ciclos.png`]

---

## Cenario 6 — Provas legacy v3.0

**Descricao operacional:** Provas criadas antes da v4.0, com
`rota IN {PADRAO, DIRETA}` ou `rota=NULL`.

**Decisoes de design relevantes:**
- D11.1 (ADR-158, supersede ADR-126): `PADRAO → "Matriz"` e `DIRETA → "Filial"`
  globalmente em `ROTA_LABELS`.
- D11.2 (ADR-159): heuristica `vendedor_localizacao → rota visual`
  para `rota=NULL` (FILIAL → "Filial" + `LEGACY_ROTA_DIRETA`).
- D11.3: bloco de laminacao NUNCA renderizado para legacy.

**Provas representativas:**
- DIRETA terminal: `PRV-2026-04-9MGETS` (status: RECEBIDA_PELA_CLICHERIA)
- PADRAO cancelada: `PRV-2026-04-XPXWKA` (status: CANCELADA)
- NULL+vendedor FILIAL CRIADA: qualquer das 5 com `status=CRIADA` e
  `rota=NULL`.

**Criterio de validacao visual:**
- DIRETA: header com `Rota: Filial`, sequencia de 5 nos da legacy direta
  (CRIADA → RETIRADA → APROVADA → ENCAMINHADA_A_CLICHERIA → RECEBIDA).
- PADRAO: header com `Rota: Matriz`, sequencia de 7 nos da legacy
  padrao (CRIADA → RETIRADA → APROVADA → DE_VOLTA → COM_MOTORISTA →
  ENVIADA_PARA_CLICHERIA → RECEBIDA).
- NULL+FILIAL: header com `Rota: Filial` (via heuristica) + sequencia
  da DIRETA.
- **Nenhum** bloco de laminacao em qualquer caso legacy.

**Screenshot:** [ANEXAR SCREENSHOT (1 por subcenario) —
`screenshots/cenario-6a-direta.png`, `cenario-6b-padrao.png`, `cenario-6c-null-filial.png`]

---

## Cenario 7 — Prova cancelada

**Descricao operacional:** Prova com `status=CANCELADA` e
`motivo_cancelamento` preenchido.

**Decisoes de design relevantes:**
- D7 OPCAO A pos-auditoria (apendice DECISIONS.md):
  - Card transversal vermelho `<div role="alert">` exibido sobre o
    ciclo atual.
  - No `.nodeCancelamento` cinza terminal.
  - Motivo destacado em vermelho dentro do card vermelho.
  - **Sem strikethrough no no anterior** (decisao consciente —
    AUD-W3C12-006 OPÇÃO A).

**Provas representativas:**
- Legacy PADRAO cancelada: `PRV-2026-04-XPXWKA` ou `PRV-2026-04-CSN3YJ`.
- Legacy DIRETA cancelada: `PRV-2026-04-XD8G73`.
- Legacy NULL cancelada: 4 opcoes.

**Criterio de validacao visual:**
- Card vermelho transversal aparece logo abaixo dos nos do ciclo
  atual, com:
  - Icone `AlertTriangleIcon`.
  - Titulo "Esta prova foi cancelada".
  - Linha "Por: <nome> (<setor>)" se ator presente.
  - Linha "Quando: <DD/MM/AAAA HH:MM>".
  - Linha "Motivo: <texto>".
- No CANCELADA aparece como ultimo no do ciclo, com classe
  `.nodeCancelamento` (cinza, icone `BanIcon`).
- Leitor de tela anuncia imediatamente o card (`role="alert"`).
- **Nao deve aparecer** strikethrough no no anterior — confirmacao da
  Opcao A.

**Screenshot:** [ANEXAR SCREENSHOT — `screenshots/cenario-7-cancelada.png`]

---

## Cenario 8 — Terminal sucesso (RECEBIDA_PELA_CLICHERIA)

**Descricao operacional:** Prova chegou ao estado terminal de
sucesso — `RECEBIDA_PELA_CLICHERIA`.

**Decisoes de design relevantes:**
- D8 OPCOES (a)+(b): `CheckCircleIcon` verde + badge "Concluída":
  - No header da Timeline: `<span .headerStatusBadge
    .headerStatusBadgeOk>` com check + "Concluída".
  - No no terminal: badge `.terminalBadge` com check + "Concluída".

**Provas representativas:** `PRV-2026-04-9MGETS` ou `PRV-2026-04-C67HZS`
(DIRETA legacy, RECEBIDA_PELA_CLICHERIA).

**Criterio de validacao visual:**
- Header da Timeline com badge verde "Concluída" + icone check.
- Ultimo no (RECEBIDA_PELA_CLICHERIA) destacado em verde com
  `.nodeTerminalOk` + badge "Concluída".
- **Sem** dot amarelo de "Atual" (terminal nao eh atual).
- **Sem** nos pendentes (terminal nao tem proximo).

**Screenshot:** [ANEXAR SCREENSHOT — `screenshots/cenario-8-terminal.png`]

---

## Checks adicionais cobertos pelo smoke

Esses nao tem secao propria mas devem ser confirmados durante a
captura:

| Smoke # | O que testar | Onde |
|---|---|---|
| 12 | Leitor de tela (VoiceOver/NVDA/Orca) anuncia corretamente cada cenario | qualquer prova |
| 13 | `prefers-reduced-motion: reduce` no DevTools desabilita o pulse do nodo atual | cenario 1 ou 5 |
| 14 | axe-core no DevTools nao retorna violacoes criticas | todos cenarios disponiveis |
| 15 | Render < 500ms via DevTools Performance | cenario 5 (multi-ciclos eh o mais carregado) |

---

## Roteiro para Mario completar este guia

1. Rodar o smoke E2E manual completo (`smoke-validation.md` 18 cenarios)
   em ambiente autenticado (producao ou staging).
2. Para cada cenario disponivel (1, 5, 6, 7, 8), capturar screenshot
   via DevTools / ferramentas do navegador.
3. Salvar em `docs/wave3-v4-c12/screenshots/cenario-N.png` (criar a
   pasta se nao existir).
4. Substituir os `[ANEXAR SCREENSHOT ...]` por links Markdown:
   `![Cenario N](screenshots/cenario-N.png)`.
5. Para cenarios 2/3/4 (Lam.Matriz/Filial/Lam.Filial): criar seed em
   staging via API e capturar; OU deixar como SKIP com nota
   explicativa.
6. Validar smoke 12-15 (a11y + perf) e documentar resultados nas
   secoes correspondentes do `fix-validation.md`.

---

**Status do guia:** STUB criado. Aguarda preenchimento com screenshots
e medicoes do Mario apos smoke E2E.
