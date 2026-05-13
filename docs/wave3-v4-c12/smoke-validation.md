# Smoke validation — Wave 3 v4.0 / Componente 12

**Branch:** `wave3-v4/componente-12`.
**Pré-requisitos:** backend rodando (`uvicorn` ou Railway), frontend
rodando (`next dev` ou Vercel preview), Supabase produção (ou staging
com seed).
**Tempo estimado:** 15-25 minutos cobrindo os 18 cenários.

> Este documento é o roteiro de smoke manual obrigatório antes do PR
> de `development → main`. Itens marcados como ⚠️ SKIP são esperados
> caso a base não tenha fixture para aquele cenário.

---

## Pré-checagem

- [ ] **C1.** Backend de pé: `GET /health` retorna 200.
- [ ] **C2.** Frontend renderiza `/login` sem erros no console.
- [ ] **C3.** Login admin (ex.: `admin@3studio.com.br`) entra e cai
  em `/dashboard` sem flash de UI proibida.

---

## Cenário 1 — Rota Matriz · em andamento

Pré-requisito: prova com `rota=MATRIZ` e status diferente de
`RECEBIDA_PELA_CLICHERIA`/`CANCELADA`. Em produção: prova
`PRV-2026-05-TEX9GW`.

- [ ] **1.1** Abrir `/provas/{id}`. Card preto do histórico renderiza.
- [ ] **1.2** Header da Timeline mostra badge `Rota: Matriz`.
- [ ] **1.3** Nó `CRIADA` aparece com dot amarelo e label "Aguardando
  vendedor".
- [ ] **1.4** Se houver `current` (movimentação real), o dot tem
  glow amarelo + badge "Atual" e o pulse anima.
- [ ] **1.5** Nós **pendentes** após o `current` aparecem com dot
  outline cinza, conector tracejado e label "Aguardando".
- [ ] **1.6** **Nenhum** bloco "Etapa de laminação" aparece (rota
  Matriz não tem laminação).

## Cenário 2 — Rota Lam. Matriz · em andamento (com laminação) ⚠️ SKIP em produção

Pré-requisito: prova com `rota=LAM_MATRIZ`. **Em produção: 0 provas.**
Criar seed em staging ou pular.

- [ ] **2.1** Badge `Rota: Lam. Matriz` no header.
- [ ] **2.2** Bloco com label `ETAPA DE LAMINAÇÃO` envolvendo os
  nós `ENCAMINHADA_PARA_LAMINACAO`, `COM_MOTORISTA_IDA_LAMINACAO`,
  `LAMINACAO_CONCLUIDA`, `COM_MOTORISTA_VOLTA_LAMINACAO`,
  `DE_VOLTA_3STUDIO_POS_LAMINACAO`.
- [ ] **2.3** Badge `→ Laminação` no nó de ida.
- [ ] **2.4** Badge `Laminação →` no nó de volta.
- [ ] **2.5** Após o bloco, sequência continua com `RETIRADA_PELO_VENDEDOR`
  → `APROVADA` → `DE_VOLTA_3STUDIO` → `COM_MOTORISTA_ENTREGA_FINAL` →
  `RECEBIDA_PELA_CLICHERIA`.
- [ ] **2.6** Badge `→ Clicheria` no nó de entrega final.

## Cenário 3 — Rota Filial · em andamento (4 etapas curtas) ⚠️ SKIP em produção

Pré-requisito: prova com `rota=FILIAL`. **Em produção: 0 provas.**

- [ ] **3.1** Badge `Rota: Filial`.
- [ ] **3.2** Sequência exibida: `CRIADA` → `ENCAMINHADA_PARA_O_VENDEDOR`
  → `APROVADA_PELO_VENDEDOR` → `RECEBIDA_PELA_CLICHERIA`.
- [ ] **3.3** Sem bloco de laminação.
- [ ] **3.4** Sem badges de motorista.

## Cenário 4 — Rota Lam. Filial · em andamento ⚠️ SKIP em produção

Pré-requisito: prova com `rota=LAM_FILIAL`. **Em produção: 0 provas.**

- [ ] **4.1** Badge `Rota: Lam. Filial`.
- [ ] **4.2** Bloco com 3 nós (sem `VOLTA` nem `POS_LAMINACAO` — só
  Lam. Matriz tem).
- [ ] **4.3** Após o bloco: `ENCAMINHADA_PARA_O_VENDEDOR` → `APROVADA`
  → `RECEBIDA_PELA_CLICHERIA`.

## Cenário 5 — Múltiplos ciclos (reprovação + reinício)

Pré-requisito: prova com `ciclo_atual > 1` ou histórico de reprovação.
Em produção: prova `PRV-2026-04-B9CZ37` (ciclo_atual=2, legacy NULL).

- [ ] **5.1** Header com badge da rota (heurística → "Filial" se
  legacy NULL + vendedor FILIAL).
- [ ] **5.2** **Dois grupos visuais** com header "Ciclo 1" e "Ciclo 2".
- [ ] **5.3** Ciclo 1 está em container "tampão" (`.cyclePassed`) com
  borda tracejada, badge "Reprovado" no header.
- [ ] **5.4** Header do Ciclo 1 mostra "Ciclo 1 · reprovado em
  DD/MM/AAAA HH:MM" + badge vermelho "Reprovado".
- [ ] **5.5** **Motivo da reprovação** destacado em card vermelho
  dentro do Ciclo 1.
- [ ] **5.6** Separador `↻ reinício de ciclo` entre Ciclo 1 e Ciclo 2.
- [ ] **5.7** Ciclo 2 está sem container "tampão", badge amarelo
  "Em andamento".
- [ ] **5.8** Pendentes aparecem **apenas no Ciclo 2** (ciclo atual).

## Cenário 6 — Provas legacy (rota=PADRAO ou DIRETA)

Pré-requisito: prova legacy. Em produção: `PRV-2026-04-9MGETS`
(DIRETA, RECEBIDA), `PRV-2026-04-C67HZS` (DIRETA, RECEBIDA),
`PRV-2026-04-XPXWKA` (PADRAO, CANCELADA), `PRV-2026-04-CSN3YJ`
(PADRAO, CANCELADA).

- [ ] **6.1** Para `rota=PADRAO`, header mostra badge `Rota: Matriz`
  (Decisão 11.1 — supersede ADR-126).
- [ ] **6.2** Para `rota=DIRETA`, header mostra badge `Rota: Filial`
  (Decisão 11.1).
- [ ] **6.3** Sequência segue `LEGACY_ROTA_PADRAO` (7 estados) ou
  `LEGACY_ROTA_DIRETA` (5 estados) — distinta da v4.0.
- [ ] **6.4** **Nenhum** bloco de laminação (Decisão 11.3).
- [ ] **6.5** Estados v3.0 puros (`COM_MOTORISTA` legacy,
  `ENVIADA_PARA_CLICHERIA`, `ENCAMINHADA_A_CLICHERIA`) renderizam
  com labels corretos.

## Cenário 7 — Prova legacy com rota=NULL (heurística)

Pré-requisito: prova com `rota=NULL`. Em produção: 11 provas, todas
com `vendedor_localizacao=FILIAL` (ex.: `PRV-2026-04-RVZF73`).

- [ ] **7.1** Header mostra badge `Rota: Filial` (heurística Decisão
  11.2 — vendedor FILIAL → label "Filial").
- [ ] **7.2** Sequência segue `LEGACY_ROTA_DIRETA`.
- [ ] **7.3** Se houver prova com `vendedor_localizacao=MATRIZ` (não
  em produção), o badge é `Rota: Matriz` e sequência
  `LEGACY_ROTA_PADRAO` — ⚠️ SKIP em produção.

## Cenário 8 — Prova cancelada

Pré-requisito: prova `CANCELADA`. Em produção: várias (ex.:
`PRV-2026-04-DYHG65`, `PRV-2026-04-HQGYZJ`).

- [ ] **8.1** Header da Timeline mostra badge `Cancelada` (cinza)
  ao lado do badge da rota.
- [ ] **8.2** No final do ciclo atual, **card vermelho** com:
  - Ícone alert-triangle no canto
  - Título "Esta prova foi cancelada"
  - Linha "Por: {nome} ({setor})"
  - Linha "Quando: DD/MM/AAAA HH:MM"
  - Linha "Motivo: ..." (se houver `motivo_cancelamento`)
- [ ] **8.3** Último nó do histórico é "Cancelada" com dot cinza
  (não amarelo).
- [ ] **8.4** **Sem** nós pendentes (cancelamento encerra fluxo).

## Cenário 9 — Estado terminal de sucesso

Pré-requisito: prova `RECEBIDA_PELA_CLICHERIA`. Em produção:
`PRV-2026-04-9MGETS`, `PRV-2026-04-C67HZS`.

- [ ] **9.1** Header com badge `Concluída` verde + ícone check-circle.
- [ ] **9.2** Último nó é "Recebida pela Clicheria" com dot verde,
  badge "Concluída" + ícone check verde.
- [ ] **9.3** Sem nós pendentes.
- [ ] **9.4** Sem nó "current" (todos passed).

## Cenário 10 — Estado em andamento (current visivel)

Pré-requisito: qualquer prova ativa não-cancelada e não-terminal.

- [ ] **10.1** O último nó concreto tem dot amarelo com glow + pulse
  framer-motion + badge "Atual".
- [ ] **10.2** Após o nó atual, nós pendentes aparecem em cinza
  outline.
- [ ] **10.3** Conector tracejado liga `current` ao primeiro pendente.

## Cenário 11 — Reduced motion (RN-012 / RNF-010)

Pré-requisito: ativar `prefers-reduced-motion: reduce` no DevTools
(Rendering tab → Emulate CSS media feature `prefers-reduced-motion`).

- [ ] **11.1** Recarregar `/provas/{id}` com a opção ativada.
- [ ] **11.2** Pulse do nó atual **NÃO** anima (CSS `@media` esconde
  `.dotPulse` + framer-motion `useReducedMotion` também).
- [ ] **11.3** Transições do AnimatePresence ficam instantâneas.

## Cenário 12 — Acessibilidade (leitor de tela)

Pré-requisito: ativar VoiceOver (Mac) ou NVDA (Windows).

- [ ] **12.1** Navegar até a Timeline. Leitor anuncia "Histórico de
  movimentações da prova {nro_requerimento} — região".
- [ ] **12.2** Em cada step, leitor anuncia label + fase + ator +
  timestamp (ex.: "Retirada pelo vendedor — etapa atual — desde
  12/05/2026 16:00 — por João da Silva (Vendedor)").
- [ ] **12.3** Bloco de laminação é anunciado como "Etapa de
  laminação — grupo".
- [ ] **12.4** Card de cancelamento é anunciado com alerta
  (`role="alert"`).
- [ ] **12.5** Navegação por TAB pula a Timeline (sem itens
  focáveis — Decisão 9 estática).

## Cenário 13 — Navegação por teclado

- [ ] **13.1** Pressionar TAB a partir do botão "Voltar" não foca
  nenhum elemento dentro da Timeline (Decisão 9 — estática, sem
  interatividade).
- [ ] **13.2** Apenas os botões da `actionsRow` (Visualizar etiqueta,
  Baixar etiqueta, Admin actions) recebem foco.

## Cenário 14 — Acessibilidade visual (contraste AA)

- [ ] **14.1** Texto branco sobre fundo preto — contraste 21:1 (AAA).
- [ ] **14.2** Badge amarelo (`var(--color-accent)`) sobre fundo
  preto — contraste 9.55:1 (AAA).
- [ ] **14.3** Texto vermelho do motivo de reprovação sobre fundo
  vermelho transparente — passível de validação manual com axe-core.
- [ ] **14.4** Texto verde do "Concluída" sobre fundo verde
  transparente — passível com axe-core.

## Cenário 15 — Performance (RNF-001)

Pré-requisito: prova com 3+ movimentações + pendentes (Lam. Matriz
em andamento dá ~11 nós).

- [ ] **15.1** Abrir `/provas/{id}` com DevTools Performance gravando.
- [ ] **15.2** Renderização inicial da Timeline ocorre em **< 500ms**
  após `useProvaDetail` resolver.
- [ ] **15.3** Sem warnings de "Long task" no DevTools.

## Cenário 16 — Responsividade

- [ ] **16.1** Em desktop ≥ 1280px, Timeline renderiza normalmente.
- [ ] **16.2** Em tablet 768-1100px, Timeline preserva layout vertical.
- [ ] **16.3** Em mobile < 768px, página redireciona para `.mobileNotice`
  ("Para acessar esse recurso, acesse a versão desktop") — sem
  regressão do C08.

## Cenário 17 — Consistência cross-tela (Decisão 11.1)

- [ ] **17.1** Ir para `/provas` (listagem). Coluna "Rota" mostra
  "Matriz" para PADRAO e "Filial" para DIRETA (não "Padrão"/"Direta").
- [ ] **17.2** Ir para `/relatorios` aba Geral. Distribuição por rota
  mostra "Matriz" e "Filial" (não os legacy).
- [ ] **17.3** Exportar CSV pelos relatórios. Coluna "Rota" usa
  "Matriz"/"Filial".
- [ ] **17.4** **R-12** (a confirmar): filtros do C07 podem ter
  opções duplicadas (`MATRIZ`+`PADRAO` ambos rotulados "Matriz",
  `FILIAL`+`DIRETA` ambos "Filial"). Decidir pós-merge se colapsa.

## Cenário 18 — Console limpo

- [ ] **18.1** DevTools Console sem erros novos em nenhum dos cenários.
- [ ] **18.2** DevTools Console sem warnings de framer-motion ou React.
- [ ] **18.3** Network tab sem requests com status 5xx.

---

## Resumo

Cenários cobrindo 8 rotas/estados × dispositivo/a11y/performance:

| Categoria | Cenários |
|---|---|
| Rotas v4.0 (4) | 1, 2 ⚠️, 3 ⚠️, 4 ⚠️ |
| Legacy v3.0 | 6, 7 |
| Múltiplos ciclos | 5 |
| Cancelamento + Terminal | 8, 9 |
| Estado atual | 10 |
| A11y + reduced motion | 11, 12, 13, 14 |
| Performance | 15 |
| Responsivo | 16 |
| Cross-tela (Decisão 11.1) | 17 |
| Sanidade | 18 |

⚠️ = SKIP em produção (sem fixtures). Criar seed em staging ou
documentar como pendência da Wave 3 inteira.

**Aprovação:** todos os itens devem estar marcados (ou SKIP justificado)
antes do PR `development → main`.
