# Wave 3 — Revisao Critica C11 — Closeout

**Data:** 2026-04-13
**Escopo:** Componente 11 (Assinatura Digital e Transicao de Status)
**Status:** COMPLETO

---

## 1. Itens aplicados

| ID | Categoria | Descricao | Arquivos tocados |
|----|-----------|-----------|-----------------|
| B-01 | Bug | `scanHook.error` stale — hooks retornam `{ data, error }` | `useScanProva.ts`, `useExecutarTransicao.ts`, `page.tsx` |
| B-02 | Bug | Canvas responsivo via `ResizeObserver` | `page.tsx` |
| B-03 | Bug/UX | 409 Conflict redireciona para re-scan | `useExecutarTransicao.ts`, `page.tsx` |
| B-04 | UX/Fluidez | Modal permanece durante submit com loading state | `page.tsx` |
| B-07 | Qualidade | Removido fallback morto `created_at or now()` | `provas.py` |
| C-03 | Observ | Log `logger.warning` em `_decode_assinatura` | `provas.py` |
| D-01 | UX | Transicao "Status A -> Status B" no modal | `page.tsx`, `escanear.module.css` |
| D-02 | UX | Badge do novo status na DoneView | `page.tsx` |
| D-03 | UX | Mensagem diferenciada para estado terminal | `page.tsx` |
| D-04 | A11y | Handler Escape fecha modal (WAI-ARIA) | `page.tsx` |

---

## 2. Itens adiados

| ID | Categoria | Motivo | Prioridade futura |
|----|-----------|--------|-------------------|
| B-05 | Seguranca | `motivo_reprovacao` sem sanitizacao — React escapa por padrao, zero risco hoje | Wave 6 (se novos consumidores) |
| B-06 | Qualidade | Heranca `TransicaoInvalidaError(ValueError)` — documentado em comentario, funcional | WONTFIX |
| C-01 | Qualidade | `page.tsx` 644 linhas — cosmetico, nao funcional | Wave 4+ (se tocar pagina) |
| C-02 | Qualidade | Callbacks com deps instaveis — otimizacao prematura | WONTFIX |
| D-05 | A11y | Focus trap no modal — baixo impacto em mobile-first | Wave 6 (polish) |

---

## 3. Cobertura de testes

| Aspecto | Antes | Depois |
|---------|-------|--------|
| Backend `pytest` | **407 passed** | **407 passed** (0 regressoes) |
| `tsc --noEmit` | limpo | **limpo** |
| `next lint` | 0 warnings | **0 warnings** |
| `next build` | OK | **OK** |
| Bundle `/escanear` | 11.4 kB / 161 kB FL JS | **11.9 kB / 162 kB FL JS** |
| Bundle `/provas/[id]` | 47.2 kB / 206 kB FL JS | **47.5 kB / 206 kB FL JS** |

### Funcionalidade adicional (pos-review, mesma sessao)

| Feature | Descricao | ADR |
|---------|-----------|-----|
| Entrada manual de codigo QR | Campo de texto na IdleView do `/escanear` — alternativa a camera | ADR-089 |
| Codigo copiavel no modal | Payload do QR exibido no modal de etiqueta com botao "Copiar" | ADR-089 |
| Helper `buildQrPayload()` | Computa payload client-side a partir de dados ja expostos | ADR-089 |
| Layout Figma | Label + input pill + botao escuro conforme design do Mario | — |

---

## 4. Confirmacao de escopo

- Nenhum outro componente foi tocado (C10, C12, C13, C14 intactos).
- Nenhuma migration, policy RLS ou endpoint adicionado/removido.
- `alembic_version` permanece `009`.
- 12 policies RLS intactas.
- 28 rotas backend intactas.

---

## 5. Riscos residuais

| # | Risco | Mitigacao |
|---|-------|----------|
| 1 | Canvas responsivo pode resetar desenho em rotacao de tela | Aceitavel — rotacao durante assinatura e rara; usuario pode redesenhar |
| 2 | `ResizeObserver` nao disponivel em browsers muito antigos | Cobertura > 96% global; mobile Chrome/Safari suportam desde 2020 |
| 3 | Focus trap ausente no modal (D-05 adiado) | Impacto baixo em mobile-first; Escape handler ja implementado |
| 4 | `motivo_reprovacao` sem sanitizacao (B-05 adiado) | React escapa por padrao; zero risco com consumidores atuais |
