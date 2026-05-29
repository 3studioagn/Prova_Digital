# Smoke / Validação Manual — Componente 23 (Wave 8 v5.0)

**Componente:** 23 — Responsividade Mobile da Página de Escaneamento
**Como rodar:** staging autenticado (Vercel) + Chrome DevTools device emulator +
ao menos **1 Android físico** e **1 iOS físico** (RF-029, RNF-013, US-020).
**Pré-requisito:** backend do Railway no ar; usuário de cada perfil necessário
para os cenários 5/6/10 (motorista/vendedor) — se indisponível, marcar SKIP.

> A validação automatizada de `/escanear`+assinatura não é viável programaticamente
> (exige auth). Por isso esta matriz manual — padrão C10/C12/C16/C22. O Mario
> preenche PASS/FAIL e anexa screenshots ao `visual-guide.md`.

---

## A. Matriz viewport × orientação

| Viewport | Portrait | Landscape |
|---|---|---|
| 360×640 (mobile pequeno) | ☐ | ☐ |
| 390×844 (iPhone 12/13) | ☐ | ☐ |
| 430×932 (iPhone Pro Max — notch) | ☐ | ☐ |
| 768×1024 (tablet) | ☐ | ☐ |
| 1280×800 (desktop — REGRESSÃO: deve ficar idêntico ao atual) | ☐ | — |

## B. Os 10 cenários

### Cenário 1 — 360px portrait · câmera
- [ ] Sem scroll horizontal; `.wrapper`/innerCard cabem.
- [ ] Tabs Camera/Manual com altura ≥44px (toque confortável).
- [ ] "Abrir câmera" full-width, na metade inferior, alcançável com o polegar.
- [ ] Preview com QR mock quadrado + brackets amarelos visíveis; hint legível.

### Cenário 2 — 360px landscape · câmera
- [ ] Layout NÃO força scroll vertical enorme (sem `min-height:720px`).
- [ ] Câmera/preview e textos lado a lado (2 colunas); preview quadrado.
- [ ] CTA acessível sem rolar muito.

### Cenário 3 — 360px portrait · digitação manual
- [ ] Teclado nativo abre como texto (letras + números); tecla de ação "buscar".
- [ ] Ao focar o input, **não** há auto-zoom (font 16px).
- [ ] Input + "Buscar prova" full-width; botão ≥44px.
- [ ] Máscara `PRV-AAAA-MM-NNNNNN` e validação funcionam como antes (sem regressão C19).

### Cenário 4 — 360px landscape · digitação manual
- [ ] Input + botões reorganizados, sem corte; sem auto-zoom.
- [ ] Mensagem de erro (banner) visível e legível.

### Cenário 5 — mobile portrait · assinatura (Motorista)
- [ ] Após escanear prova sob responsabilidade, o modal abre automaticamente (RF-028).
- [ ] Canvas de assinatura dimensionado à largura; assinar com o dedo funciona.
- [ ] Contexto da prova (nome, código, rota) visível.
- [ ] "Confirmar"/"Cancelar" ≥46px e alcançáveis.
- [ ] (SKIP se não houver motorista/prova no estado certo.)

### Cenário 6 — mobile landscape · assinatura (Vendedor reprovar + motivo)
- [ ] Seletor Aprovar/Reprovar visível; "Reprovar" abre campo de motivo.
- [ ] Com o teclado aberto no motivo, o rodapé de ações continua alcançável (sticky).
- [ ] Submeter registra a reprovação; modal sai para `/provas/[id]`.
- [ ] (SKIP se não houver vendedor/prova no estado certo.)

### Cenário 7 — notch · safe areas
- [ ] Em iPhone com notch (portrait e landscape), nenhum botão/conteúdo essencial
      fica sob o notch ou o home indicator.
- [ ] Há respiro lateral em landscape (safe-left/right) e inferior (safe-bottom).

### Cenário 8 — uso one-handed
- [ ] Os botões principais (alternar modo, abrir câmera/buscar, confirmar) ficam
      na metade/terço inferior, alcançáveis com o polegar.

### Cenário 9 — contraste sob luz forte (simulação)
- [ ] Sob filtro de brilho/contraste do DevTools, textos e ícones permanecem legíveis.
- [ ] Lighthouse/axe: textos auxiliares (hint, footer) passam AA no mobile.

### Cenário 10 — transição de orientação
- [ ] Girar portrait↔landscape adapta sem flash de layout quebrado.
- [ ] O valor digitado no input do C19 **não** é perdido na rotação.
- [ ] A câmera não reinicia desnecessariamente.

## C. Acessibilidade (axe DevTools nos viewports mobile)
- [ ] 0 violações críticas em `/escanear` (câmera e manual).
- [ ] 0 violações críticas no modal de assinatura.
- [ ] Foco visível em todos os controles; navegação por teclado virtual ok.
- [ ] `prefers-reduced-motion` ativado: beam do scanner e animações degradam.

## D. Regressão (deve passar)
- [ ] **Desktop ≥1024px:** `/escanear` (câmera+manual) e modal **idênticos** ao
      anterior (diff visual zero). Critério crítico — desktop congelado.
- [ ] C10: escaneamento por câmera funciona (desktop e mobile).
- [ ] C19: digitação manual + máscara + anti-enumeração funcionam.
- [ ] C22: 7 views do modal (selecionando/assinando/enviando/sucesso/conflito/
      sessão/erro) funcionam; focus trap + Esc ok.
- [ ] Sem erros no console do browser.

## E. Definition of Done — Global (Backlog §2) — aplicável ao C23
- [ ] Code review aprovado por ao menos 1 revisor humano.
- [ ] (N/A) Testes unitários ≥80% de domínio/serviço backend — C23 não toca backend
      nem adiciona lógica TS (CSS + atributos). Vitest 237 sem regressão.
- [ ] Validado contra US-018/019/020 + RF-029 + RNF-013.
- [ ] Validado contra a Matriz de Acesso (escanear = universal; sem mudança RBAC).
- [ ] Sem erros no console / logs de erro crítico.
- [ ] Documentação atualizada (CHANGELOG, DECISIONS, CLAUDE, analysis, visual-guide).
- [ ] (N/A) Migrations/RLS — zero alteração de banco.
- [ ] Animações novas validadas com prefers-reduced-motion (nenhuma animação nova;
      as existentes já degradam).
