# Smoke E2E Manual · Wave 3 v4.0 · Componente 10 (atualizacao v4.0)

**Branch:** `wave3-v4/componente-10`
**Executor:** Mario Souza
**Ambiente:** producao Vercel + Railway + Supabase + R2

> Este checklist deve ser executado **antes do PR final para `main`**
> (ou antes do merge para `development`). O preview programatico
> (Vercel) nao tem auth de producao — alguns itens exigem o Mario
> logado em conta real (admin, vendedor, motorista, clicheria).
>
> Marcar cada item como ✅ PASS · ❌ FAIL (com observacao) · ⏭ SKIP
> (com motivo). Se algum item FAIL, registrar bug em apendice deste
> arquivo e abrir nova sessao de correcao antes do merge.

---

## Pre-condicoes

- 17 provas em producao (16 com QR antigo `nro_requerimento` + 1 com
  QR novo `codigo_publico`). Validado via MCP Supabase em 2026-05-06.
- Codigos publicos confirmados (uma amostra do MCP execute_sql):
  - `PRV-2026-05-TEX9GW` (prova MATRIZ v4.0, status CRIADA)
  - `PRV-2026-04-RVZF73` (prova legacy rota=NULL, status CRIADA)
  - `PRV-2026-04-G5932T` (prova legacy rota=NULL, status REPROVADA)
  - `PRV-2026-04-9MGETS` (prova DIRETA legacy, status RECEBIDA)

---

## Cenarios

### 1. Render inicial (modo Camera)

3Studio loga e navega para `/escanear` (ou usa atalho `g s`). Confirma:
- Sidebar visivel com item "Escanear" destacado.
- h1 "Escanear prova" + subtitulo correto.
- Toggle pill com 2 botoes: **"Camera" preto/ativo** + **"Manual"
  branco/inativo**.
- Card grande cinza claro com 2 colunas:
  - Esquerda: subcard branco com QR mockado + brackets + texto
    "Centralize o QR Code no quadro".
  - Direita: h2 "Pronto para escanear" + descricao + botao escuro
    "Abrir camera".
- Footer placeholder: "Ultima leitura ha —" + "Ver historico →" cinza
  desabilitado.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

### 2. Toggle de tab para Manual

Clicar na pill "Manual". Confirma:
- "Manual" passa para preto/ativo, "Camera" para branco/inativo.
- Card mostra o painel central com h2 "Inserir codigo manualmente",
  descricao com `<code>PRV-AAAA-MM-NNNNNN</code>`, input com placeholder
  do mesmo formato, botao escuro "Buscar prova →" inicialmente
  desabilitado (input vazio).

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

### 3. Identificacao manual happy path (codigo PRV valido)

No tab Manual, digitar `PRV-2026-05-TEX9GW` (prova MATRIZ existente).
Botao habilita. Clicar "Buscar prova →".
- Estado intermediario: botao mostra "Buscando..." e e desabilitado.
- Em ate 2s: redireciona para `/provas/<id-da-MATRIZ>`.
- Pagina de detalhe carrega (ja entregue no C08 v4.0).

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

### 4. Identificacao manual com codigo invalido (formato)

Voltar para `/escanear`, tab Manual. Digitar `abc-bad`. Submeter.
Confirma:
- Banner de erro vermelho aparece com texto "Prova nao encontrada."
  (mensagem **GENERICA** alinhada a DAT §8.2 — nao distingue formato
  invalido de fora-do-scope).
- `aria-invalid="true"` no input (verificar via DevTools).
- Input continua editavel.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

### 5. Identificacao manual com codigo formato OK mas inexistente

Tab Manual. Digitar `PRV-2026-05-AAAAAA` (formato valido mas nao
existe em producao). Submeter. Confirma:
- Mesma mensagem "Prova nao encontrada." que o caso de formato
  invalido (cenario 4) — **identicas**, sem pista para enumeracao.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

### 6. Identificacao manual com codigo de prova legacy v3.0 (`nro_requerimento` puro)

Tab Manual. Digitar `456987` (nro_requerimento de prova legacy v3.0
em producao). Submeter. Confirma:
- Banner "Prova nao encontrada." (formato nao casa PRV-).
- Esta e uma decisao de design alinhada ao C19 — manual SO aceita
  codigos legiveis no formato `PRV-AAAA-MM-NNNNNN`. As provas legacy
  v3.0 que ainda nao tem etiqueta regerada precisam usar **camera**
  para escanear (caminho legacy fallback continua funcionando — ver
  cenario 9).

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

### 7. Camera — abertura e UI ativa

Voltar ao tab Camera. Clicar "Abrir camera". Confirma:
- Browser pede permissao de camera (se primeira vez).
- Apos permitir: o slot esquerdo do card vira live preview da camera
  (com brackets em branco sobrepostos).
- Sidebar direita: h2 "Aponte para o QR Code" + descricao + CTA
  "Cancelar" (ainda preto).

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

### 8. Camera — scan de QR v4.0 (prova MATRIZ)

Apontar a camera para o QR Code da prova `PRV-2026-05-TEX9GW`
(ou imprimir/abrir a etiqueta no celular). Confirma:
- O scanner detecta em ate 2s (RNF-002).
- A pagina redireciona para `/provas/<id-da-MATRIZ>`.
- Audit log gravado: `acao='escanear_prova'`, `detalhes.origem='camera'`,
  `detalhes.codigo_publico=PRV-2026-05-TEX9GW`. Verificar via
  `/auditoria` (admin).

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

### 9. Camera — scan de QR legacy v3.0 (prova com `nro_requerimento` no segundo campo)

Apontar a camera para o QR de uma prova legacy (ex.:
`PRV-2026-04-9MGETS`, prova DIRETA legacy, status RECEBIDA — esta
prova **terminal** nao gera transicao mas e identificada). Confirma:
- Backend cai no caminho fallback `_carregar_prova_por_nro_req` (porque
  o segundo campo do QR nao casa formato `PRV-`).
- Redireciona para `/provas/<id-da-9MGETS>`.
- Audit log: `origem='camera'`, `codigo_publico=PRV-2026-04-9MGETS`.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

### 10. Camera — permissao negada

Voltar a `/escanear`. Em DevTools, ir em Site Settings → bloquear
camera. Recarregar. Clicar "Abrir camera". Confirma:
- Banner de erro vermelho: "Camera indisponivel. Use a digitacao
  manual."
- Link "Ir para digitacao manual →" abaixo do banner.
- Clicar no link → tab Manual ativa.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

### 11. Vendedor — escopo via RLS

Logar como vendedor (mariosouza@teste.com.br, FILIAL). Tentar escanear
QR de prova de outro vendedor (ou digitar codigo de prova alheia).
Confirma:
- Banner "Prova nao encontrada." (RLS filtrou — `pol_provas_select`
  com `vendedor_id = current_user_id`).
- **Mesma mensagem** que codigo inexistente — sem pista para
  enumeracao (DAT §8.2).
- Audit log NAO gravado para esse caso.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

### 12. Sessao expirada

Limpar localStorage do Supabase Auth (DevTools → Application →
Storage). Tentar escanear ou digitar codigo manualmente. Confirma:
- Banner "Sua sessao expirou. Faca login novamente."
- Apos clique: redireciona para `/login` apos ~2s.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

### 13. Atalho global `g s` (Wave 5 C17)

Em qualquer pagina autenticada, pressionar `g` (vai para "leader mode")
e depois `s`. Confirma:
- Navega para `/escanear`.
- Atalho continua funcionando depois do redesign.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

### 14. Acesso anonimo

Logout. Tentar acessar `/escanear` direto via URL. Confirma:
- Middleware redireciona para `/login` com toast.
- Pagina nao renderiza nem brevemente.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

### 15. Defesa proativa RBAC

Pos-merge, em DevTools, simular `is_admin: false` no /users/me
hipoteticamente. Confirma que `useAuthorization` evita flash de UI
proibida via `if (auth.loading) return null;` (M-1 fix da Wave 1
v4.0). Padrao identico as outras paginas.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP · [ ] N/A (todos os 4
perfis tem `acesso=full` em `scanner` — defesa proativa e
puramente defensiva)

**Observacoes:**

---

### 16. Performance < 2s (RNF-002)

Em DevTools → Network → throttling "Fast 3G". Tab Manual com codigo
valido. Submeter. Medir tempo da requisicao + redirecionamento.
Confirma:
- Total < 2s do clique ate o detalhe carregar.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

### 17. Acessibilidade — navegacao por teclado

Sem usar mouse: Tab atravessa: Logo → Busca → Nav items → Tab Camera →
Tab Manual → Botao "Abrir camera" / "Buscar prova" → Footer link.
Cada elemento tem outline visivel (focus-visible).

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

### 18. Acessibilidade — contraste AA

Rodar `axe-core` ou Lighthouse Accessibility. Confirmar:
- Score 100 ou 95+.
- Sem warnings de contraste.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

### 19. `prefers-reduced-motion`

DevTools → Rendering → Emulate CSS prefers-reduced-motion. Recarregar.
Confirmar:
- Toggle pill nao tem transicao animada.
- Botao primary nao tem transicao.
- Input nao tem transicao no focus.
- (Em geral o redesign tem transicoes simples — todas degradam.)

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP
**Observacoes:**

---

### 20. Audit log — ambos os caminhos

Apos cenarios 3 (manual) e 8 (camera), 3Studio acessa `/auditoria` e
filtra por `acao='escanear_prova'`. Confirma:
- 2 entradas novas.
- Uma com `detalhes.origem='manual'`, outra com `'camera'`.
- Ambas tem `codigo_publico` preenchido.
- Vendedor responsavel + status atual + transicoes_permitidas.

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

**Veredito final:** [ ] APROVADO PARA MERGE · [ ] CORRECOES NECESSARIAS

**Assinatura:** Mario Souza, em ____ / ____ / 2026
