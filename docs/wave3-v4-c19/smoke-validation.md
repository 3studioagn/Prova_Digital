# Smoke E2E Manual · Wave 3 v4.0 · Componente 19 (Fallback de Digitacao Manual)

**Branch:** `wave3-v4/componente-19`
**Executor:** Mario Souza
**Ambiente:** producao Vercel + Railway + Supabase + R2

> Este checklist deve ser executado **antes do PR final para `main`**.
> O preview programatico (Vercel) nao tem auth de producao —
> autenticar primeiro como cada perfil necessario.
>
> Marcar cada item: ✅ PASS · ❌ FAIL (com observacao) · ⏭ SKIP
> (com motivo). Bug encontrado vira nova sessao de correcao antes
> do merge.

---

## Pre-condicoes

- 17 provas em producao (MCP validou 2026-05-11 — todas com
  `codigo_publico` preenchido apos backfill da migration 012).
- Codigos publicos para teste (referencia):
  - `PRV-2026-05-TEX9GW` — prova MATRIZ v4.0, status CRIADA.
  - `PRV-2026-04-RVZF73` — prova legacy `rota=NULL`, status CRIADA.

---

## 1. Foco automatico ao entrar no tab Manual

3Studio loga, navega para `/escanear`. Clica na tab **"Manual"**. Confirma:
- O cursor automaticamente fica no `<input>` (cursor piscando, pode
  digitar imediatamente sem clicar).
- Outra forma de validar: pressionar uma tecla qualquer logo apos
  trocar de tab — o char (se valido) aparece no input.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

## 2. Digitacao incremental — mascara em tempo real

No tab Manual, digitar caractere por caractere:
- `2` → display: `"2"`.
- `2026` → display: `"2026"`.
- `20265` → display: `"2026-5"` (hifen aparece automaticamente).
- `202605` → display: `"2026-05"`.
- `2026059` → display: `"2026-05-9"` (segundo hifen automatico).
- `202605K3T9XB` → display: `"2026-05-K3T9XB"`.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

## 3. Auto-uppercase

Limpar o input. Digitar minusculo: `2026-05-k3t9xb`.
Confirma:
- Display final: `"2026-05-K3T9XB"` (tudo maiusculo).

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

## 4. Bloqueio rigido de chars no sufixo

Limpar input. Digitar `2026-05-` (parcial completo ate o segundo hifen).
Tentar adicionar `0` (zero), `O` (letra), `1` (um), `I` (i maiusculo),
`L` (ele maiusculo) no comeco do sufixo.

Confirma:
- Nenhum desses chars aparece no display.
- Tentar agora `K3T9XB` — completa normalmente.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

## 5. Bloqueio rigido de chars no ano (letra)

Limpar input. Tentar digitar `A2026` (letra primeiro). Confirma:
- O `A` nao aparece. Display: `"2026"`.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

## 6. Paste com prefixo PRV-

Limpar input. Copiar `PRV-2026-05-TEX9GW` da area de transferencia
externa. Colar no input. Confirma:
- Display: `"2026-05-TEX9GW"` (prefixo PRV- foi descartado, o resto
  ficou formatado).

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

## 7. Paste em minusculo + prefixo

Limpar input. Colar `prv-2026-05-tex9gw`. Confirma:
- Display: `"2026-05-TEX9GW"` (uppercase + strip de prefixo).

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

## 8. Botao "Buscar prova" desabilitado quando incompleto

Limpar input. Digitar parcialmente `2026-05-K3T9` (12 chars). Confirma:
- O botao "Buscar prova" tem aparencia desabilitada (bg `#dcdcdc`,
  texto `#9a9a9a`).
- Clicar nao faz nada (sem submit).
- Adicionar `XB` para completar 14 chars. Botao habilita (bg `#000`,
  texto branco).

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

## 9. Happy path — codigo PRV valido existente

Limpar input. Digitar (ou colar) `2026-05-TEX9GW`. Clicar "Buscar prova →".
Confirma:
- Estado intermediario: botao mostra "Buscando..." e fica desabilitado.
- Em ate 2s: pagina redireciona para `/provas/<id-da-TEX9GW>`.
- Detalhe da prova carrega (C08 v4.0 — visualizacao com header,
  metadata, timeline, etc.).

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

## 10. Codigo formato OK mas inexistente

Voltar a `/escanear`, tab Manual. Digitar `2026-05-AAAAAA` (formato
valido mas inexistente). Clicar "Buscar prova". Confirma:
- Banner vermelho com texto **"Prova nao encontrada."** (mensagem
  GENERICA — DAT v3.0 §8.2).
- `aria-invalid="true"` no wrapper do input (DevTools).
- Input continua editavel; usuario pode corrigir.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

## 11. Reset do banner ao editar

Apos cenario 10, comecar a editar o codigo (apagar um char). Confirma:
- O banner de erro **some imediatamente** (D8).
- Banner volta apenas no proximo submit que falhe.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

## 12. Falha de rede

Limpar input. Digitar codigo valido (qualquer um existente).
DevTools → Network → throttling "Offline". Clicar "Buscar prova".
Confirma:
- Banner vermelho com texto **"Falha de conexao. Tente novamente em instantes."**
- Botao "Tentar novamente" aparece dentro do banner.
- Codigo permanece no input.
- Voltar para "Online" + clicar "Tentar novamente" → banner some.
- Clicar "Buscar prova" novamente → sucesso (redirect).

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

## 13. Estado preservado ao alternar tabs (R-9)

No tab Manual, digitar parcialmente `2026-05`. Clicar na tab
**"Camera"**. Voltar para **"Manual"**. Confirma:
- O display ainda mostra `2026-05` (codigo nao foi perdido).
- O foco automatico re-dispara (cursor no input).

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

## 14. RLS — vendedor escaneando prova alheia

Logar como `mariosouza@teste.com.br` (vendedor FILIAL). Navegar para
`/escanear`. Tab Manual. Digitar codigo de prova de OUTRO vendedor
(ex.: `2026-05-TEX9GW` se a prova for de outro). Submeter. Confirma:
- Banner: **"Prova nao encontrada."** (RLS filtrou — mesma mensagem
  que cenario 10).
- Audit log NAO registra a tentativa (handler retorna antes do log).

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP · [ ] N/A (apenas uma prova
de teste hoje)
**Observacoes:**

---

## 15. Sessao expirada

DevTools → Application → Storage → Limpar localStorage do Supabase
Auth. Tab Manual. Digitar codigo valido + submeter. Confirma:
- Banner: **"Sua sessao expirou. Faca login novamente."**.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

## 16. Acessibilidade — teclado puro

Sem mouse, navegar para `/escanear` via atalho `g s`. Tab para chegar
no tab "Manual". Enter para alternar. Confirma:
- Foco vai automaticamente para o input.
- Digitar com teclado → mascara funciona.
- Pressionar Enter dentro do input dispara submit.
- Em estado idle, Tab vai para botao "Buscar prova", depois para
  link "Ver historico" desabilitado, depois para footer.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

## 17. Acessibilidade — leitor de tela

Ativar leitor de tela (NVDA / VoiceOver / Narrator). Trocar para tab
Manual. Confirma o anuncio:
- "Codigo da prova no formato PRV-AAAA-MM-NNNNNN. Digite 4 digitos
  para o ano, 2 digitos para o mes e 6 caracteres alfanumericos do
  alfabeto sem chars ambiguos (sem zero, O, um, I ou L). Hifens sao
  inseridos automaticamente."
- Em estado erro: banner com `role="alert"` e anunciado imediatamente
  ("Prova nao encontrada.").

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

## 18. Performance < 2s (RNF-001)

DevTools → Network → throttling "Fast 3G". Tab Manual. Digitar codigo
valido. Submeter. Medir do clique ate o detalhe carregar.
Confirma:
- Total < 2s.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

## 19. Auditoria — origem 'manual' gravada

Apos cenario 9 (happy path manual), logar como 3Studio. Navegar
`/auditoria`. Filtrar por `acao = escanear_prova`. Confirma:
- A entrada mais recente tem `detalhes.origem = "manual"`.
- `detalhes.codigo_publico` preenchido com o codigo escaneado.
- `detalhes.payload_recebido = null` (caminho manual nao envia payload).
- `detalhes.codigo_recebido` preenchido com o codigo digitado.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

## 20. axe-core / Lighthouse Accessibility

Rodar `axe-core` (ou Lighthouse Accessibility) no tab Manual.
Confirma:
- 0 violacoes serious/critical.
- Score >= 95.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

## Apendice: bugs encontrados durante o smoke

(preencher se houver)

---

## Conclusao

- Total de cenarios: **20**
- PASS: __
- FAIL: __
- SKIP: __
- N/A: __

**Veredito final:** [ ] APROVADO PARA MERGE EM `main` · [ ] CORRECOES NECESSARIAS

**Pendencias antes do PR em `main`:**
- [ ] Smoke E2E acima OK (>= 18/20 PASS).
- [ ] **Rate limit backend** (ADR-145) — sessao separada (FOLLOW-UP
      OBRIGATORIO).

**Assinatura:** Mario Souza, em ____ / ____ / 2026
