# Guia Visual — Componente 23 (Wave 8 v5.0)

**Componente:** 23 — Responsividade Mobile da Página de Escaneamento
**Status:** STUB ESTRUTURADO — aguarda screenshots do smoke do Mario (DevTools
device emulator + dispositivos físicos Android/iOS).

> Segue o padrão de `visual-guide.md` do C12/C16/C22: estrutura pronta +
> placeholders `![...]()`. A verificação programática de `/escanear` e do modal
> de assinatura não é viável nesta sessão (exigem sessão autenticada; não há
> `frontend/.env` local). O Mario preenche os placeholders após o smoke
> (`smoke-validation.md`).

---

## 1. Visão geral

O C23 adapta para mobile a página `/escanear` (C10 câmera + C19 manual) e o modal
de assinatura (C22), **sem alterar o design desktop** (estratégia desktop-first
com overrides — ADR-166). Toda mudança vive em `@media` mobile/landscape.

## 2. Regressão desktop (diff visual ZERO — critério crítico)

Capturar `/escanear` (câmera + manual) e o modal em **≥1024px** antes e depois do
C23. Devem ser **idênticos** (o estado base não foi tocado).

### Desktop câmera — antes/depois
![Desktop câmera antes]()
![Desktop câmera depois]()

### Desktop manual — antes/depois
![Desktop manual antes]()
![Desktop manual depois]()

### Desktop modal de assinatura — antes/depois
![Desktop modal antes]()
![Desktop modal depois]()

## 3. Os 10 cenários mobile

Inserir 1–2 screenshots por cenário (ver `smoke-validation.md` para os passos).

### Cenário 1 — 360px portrait · câmera ativa
![C1 — câmera 360 portrait]()

### Cenário 2 — 360px landscape · câmera ativa
![C2 — câmera 360 landscape]()

### Cenário 3 — 360px portrait · digitação manual
![C3 — manual 360 portrait + teclado]()

### Cenário 4 — 360px landscape · digitação manual
![C4 — manual 360 landscape]()

### Cenário 5 — mobile portrait · assinatura (Motorista)
![C5 — modal assinatura portrait]()

### Cenário 6 — mobile landscape · assinatura (Vendedor reprovar + motivo)
![C6 — modal landscape + motivo + teclado]()

### Cenário 7 — notch · safe areas
![C7 — iPhone com notch, nada oculto]()

### Cenário 8 — uso one-handed · botões alcançáveis
![C8 — sobreposição zona do polegar]()

### Cenário 9 — contraste sob luz forte (simulação)
![C9 — filtro de brilho / Lighthouse contrast]()

### Cenário 10 — transição de orientação portrait↔landscape
![C10 — antes/depois da rotação, estado preservado]()

## 4. Notas de design aplicadas

- **Desktop-first overrides (ADR-166 D1):** estado base intocado; mudanças só em
  `@media`.
- **Touch targets ≥44px (RNF-013):** `.tab` 42→44px (≤540px), `.linkButton`
  min-height 44px (≤768px); botões do modal já 46px.
- **Safe areas (D5):** `viewport-fit=cover` no root + `max(1rem, var(--safe-*))`.
- **Landscape (D3):** telefone deitado (`max-height:600px`) — câmera 2 colunas +
  preview quadrado; modal painel de altura dinâmica + rodapé sticky.
- **One-handed (D4):** CTAs full-width na metade inferior; sticky só no modal
  landscape.
- **Contraste (D6):** `#7a7a7a→#6b6b6b` só no mobile.
- **Input C19 (D9):** `inputMode="text"` + `enterKeyHint="search"`; 16px (sem
  auto-zoom iOS).
- **prefers-reduced-motion:** beam do scanner e animações já degradam.

## 5. Dispositivos testados (preencher no smoke)

| Dispositivo | OS / Browser | Portrait | Landscape | Notch |
|---|---|---|---|---|
| (ex.: iPhone SE) | iOS / Safari | ☐ | ☐ | n/a |
| (ex.: iPhone 13) | iOS / Safari | ☐ | ☐ | ☐ |
| (ex.: Galaxy/Pixel) | Android / Chrome | ☐ | ☐ | ☐ |
