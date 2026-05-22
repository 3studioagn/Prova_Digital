# Guia Visual — Componente 22 (Wave 8 v5.0)

**Componente:** 22 — Reativacao da Tela de Assinatura no Fluxo de Escaneamento
**Status:** STUB ESTRUTURADO — aguarda screenshots do smoke E2E do Mario.

> Este documento segue o padrao de `visual-guide.md` do C12/C16: estrutura
> pronta + placeholders. A verificacao programatica do modal nao foi viavel
> nesta sessao (exige backend local + sessao autenticada + provas-fixture —
> ver `analysis.md` §A.5). Mario preenche os placeholders `![...]()` apos o
> smoke (`smoke-validation.md`).

---

## 1. Visao geral

O C22 reativa a tela de assinatura como um **modal** que abre
automaticamente sobre `/escanear` apos a identificacao de uma prova,
quando o usuario logado e o proximo ator habilitado (RF-028). Animacao de
entrada via `framer-motion` (scale + fade, ~220ms; respeita
`prefers-reduced-motion`).

## 2. Estados visuais do modal

O modal tem 7 views internas (`ModalView` em `AssinaturaModal.tsx`):

| View | Quando | Conteudo |
|---|---|---|
| `selecionando` | Vendedor com 2 transicoes | Cabecalho + botoes "Aprovar" / "Reprovar" |
| `assinando` | Transicao escolhida | Cabecalho + linha de transicao + (motivo, se reprovacao) + canvas + rodape |
| `enviando` | Submit em andamento | Igual a `assinando`, botoes desabilitados, "Registrando..." |
| `sucesso` | 201 do backend | Icone ✓ amarelo + "Movimentacao registrada" + "Ver prova" |
| `conflito` | 409 (race) | Icone aviso + "A prova foi movimentada" + "Ver prova atualizada" |
| `sessao` | 401 | Icone aviso + "Sessao expirada" + "Fazer login" |
| `erro` | 422/404/outro | Icone aviso + "Nao foi possivel registrar" + "Ver prova" |

_Placeholder — montagem das 7 views:_

![Estados do modal de assinatura]()

## 3. Os 10 cenarios

Para cada cenario do `smoke-validation.md`, inserir 1-2 screenshots.

### Cenario 1 — Motorista · QR · assina
![Cenario 1]()

### Cenario 2 — Vendedor · Aprovar
![Cenario 2 — seletor Aprovar/Reprovar]()
![Cenario 2 — modal de assinatura]()

### Cenario 3 — Vendedor · Reprovar + motivo
![Cenario 3 — campo de motivo]()

### Cenario 4 — Ator errado (vai para `/provas/[id]`)
![Cenario 4]()

### Cenario 5 — Digitacao manual (C19) + assinatura
![Cenario 5]()

### Cenario 6 — Falha de rede + retry
![Cenario 6 — erro de rede com assinatura preservada]()

### Cenario 7 — Prova legacy v3.0
![Cenario 7]()

### Cenario 8 — Estado terminal
![Cenario 8]()

### Cenario 9 — Race condition (409)
![Cenario 9 — view de conflito]()

### Cenario 10 — Clicheria · recebimento final
![Cenario 10 — view de sucesso terminal]()

## 4. Notas de design aplicadas

- **D1 — Modal** sobre `/escanear` (fidelidade a arqueologia, commit
  `6add246`).
- **D2 — `react-signature-canvas`**: canvas de tracado dedo/mouse, fundo
  branco, borda tracejada, altura 200px, largura responsiva.
- **D3 — Seletor Aprovar/Reprovar**: so aparece quando ha 2+ transicoes
  (caso do vendedor). "Aprovar" = botao escuro; "Reprovar" = botao
  vermelho (`--color-danger`).
- **D10 — `framer-motion` direto** (C20 pendente): backdrop fade + card
  scale 0.96→1; `useReducedMotion` zera a animacao.
- Tokens canonicos de `globals.css` — sem cores hard-coded (excecao
  `#ffffff` para a superficie elevada).
- Touch targets ≥ 44px (RNF-013 — mobile-ready; o polimento mobile fino
  e o C23).

## 5. Casos de borda documentados

- **Ator errado in-scope** → navega para `/provas/[id]` sem mensagem de
  bloqueio (Decisao D6 / ADR-164).
- **Ator errado fora-de-escopo** → o `/scan` retorna 404 → banner generico
  na pagina `/escanear` (anti-enumeracao — inalterado).
- **Estado terminal** → `transicoes_permitidas` vazio → mesma regra do
  ator-errado → `/provas/[id]`.
- **Falha de rede** → modal permanece aberto, assinatura preservada no
  canvas, "Tentar novamente" (D5).
- **Cancelar / Esc** → fecha o modal e navega para `/provas/[id]`.

## 6. Acessibilidade

- `role="dialog"` + `aria-modal="true"` + `aria-labelledby` no titulo.
- Focus trap (`useFocusTrap`) — Tab/Shift+Tab presos no modal; `Esc`
  fecha; o foco vai ao titulo a cada troca de view.
- Banner de erro com `role="alert"`.
- Validar com axe DevTools no smoke (item 11 do `smoke-validation.md`).
