# Smoke E2E Manual · Wave 2 v4.0 · Componente 08 (atualização v4.0)

**Origem:** itens 1-15 listados em `CHANGELOG.md:9210-9231` da entrega C08 v4.0
**Branch:** `wave2-v4-c08/fixes/execution` (pos-correcoes da auditoria)
**Executor:** Mario Souza
**Ambiente:** producao Vercel + Railway + Supabase + R2

> Este checklist deve ser executado **antes do PR final para `main`** (ou
> antes do merge para `development`). O preview programatico (Vercel) nao
> tem auth de produção — alguns itens exigem o Mario logado em conta
> real (admin, vendedor, motorista, clicheria).
>
> Marcar cada item como ✅ PASS · ❌ FAIL (com observacao) · ⏭ SKIP (com
> motivo). Se algum item FAIL, registrar bug em apêndice deste arquivo
> e abrir nova sessão de correção antes do merge.

---

## Cenarios

### 1. Labels de rota (4 v4.0 + 2 legacy + null)

3Studio acessa `/provas/[id]` de prova com cada uma das 4 rotas v4.0
(`MATRIZ`, `LAM_MATRIZ`, `FILIAL`, `LAM_FILIAL`) + 2 legacy v3.0
(`PADRAO`, `DIRETA`) + 1 com `rota=NULL` (legacy pre-Wave 7). Confirma
labels novos: `Matriz`, `Lam. Matriz`, `Filial`, `Lam. Filial`,
`Padrao`, `Direta`, `—`.

Provas candidatas em produção (validadas via MCP Supabase em 2026-05-06):
- `MATRIZ` v4.0: 1 disponivel
- `PADRAO` legacy: 2 disponiveis
- `DIRETA` legacy: 3 disponiveis
- `rota=NULL` legacy: 11 disponiveis (qualquer uma serve — e.g.
  `66f36e8b-13ec-45a7-812d-f2111db2a9e9`)

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP

**Observacoes:**

---

### 2. Status `CRIADA` exibido como "Aguardando vendedor"

3Studio acessa qualquer prova em `CRIADA` (6 disponiveis em produção).
Confirma campo `Status:` no metaGrid mostra `Aguardando vendedor`
(nao `Criada`). ADR-125.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP

---

### 3. Vendedor: prova dele (200) e alheia (404 + redirect)

Logar como vendedor. Acessar `/provas/<id-prova-dele>` → 200 + render
normal. Acessar `/provas/<id-prova-alheia>` → 404 + mensagem
"Prova nao encontrada." (RLS bloqueia, hook traduz erro).

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP

> Em produção há apenas 2 vendedores cadastrados; pode pegar uma
> prova do outro vendedor para testar.

---

### 4. Motorista: prova `COM_MOTORISTA*` (200)

Logar como motorista. Acessar `/provas/<id>` de prova com
`status=COM_MOTORISTA` → 200 + render normal sem botoes admin.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP

> ⚠️ Em produção nao há usuarios MOTORISTA cadastrados (validado MCP
> 2026-05-06). Item pode ser SKIP ou exigir setup temporario.

---

### 5. Clicheria: prova `*_CLICHERIA` (200)

Logar como clicheria. Acessar `/provas/<id>` de prova com
`status IN (ENVIADA_PARA_CLICHERIA, ENCAMINHADA_A_CLICHERIA,
RECEBIDA_PELA_CLICHERIA)` → 200 + render sem admin.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP

> ⚠️ Sem usuarios CLICHERIA em produção. Item pode ser SKIP.

---

### 6. Status `REPROVADA_PELO_VENDEDOR` (admin) → 4 botoes

3Studio acessa prova com `status=REPROVADA_PELO_VENDEDOR` (2
disponiveis: `73be85ae`, `bd1d722d`). Linha de acoes mostra
4 botoes side-by-side, sem quebra de linha:
  - Visualizar etiqueta (amarelo)
  - Baixar etiqueta (preto)
  - Reiniciar ciclo (amarelo)
  - Cancelar prova (vermelho/outline)

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP

---

### 7. Status `CANCELADA` → 2 botoes (admin)

Acessar prova `CANCELADA` (7 disponiveis). Linha de acoes mostra
apenas Visualizar + Baixar. Banner "Motivo do cancelamento: ..."
aparece full-width abaixo do metaGrid.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP

---

### 8. Status `RECEBIDA_PELA_CLICHERIA` → 2 botoes

Acessar prova nesse status (2 disponiveis). Linha de acoes mostra
apenas Visualizar + Baixar.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP

---

### 9. Demais status (admin) → 3 botoes

Para `CRIADA`, `RETIRADA_PELO_VENDEDOR`, `APROVADA_PELO_VENDEDOR`,
`DE_VOLTA_3STUDIO`, `COM_MOTORISTA`, `ENVIADA_PARA_CLICHERIA`,
`ENCAMINHADA_A_CLICHERIA` — admin ve 3 botoes (Visualizar | Baixar
| Cancelar). Botao Reiniciar oculto (so aparece em REPROVADA).

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP

---

### 10. Modal "Visualizar etiqueta"

Clicar em "Visualizar etiqueta" → modal abre com PDF da etiqueta
(esquerda) + QR code (direita) + payload copiavel + botao Copiar.
ESC fecha modal. Botao X tambem fecha. Click no overlay fecha.
Focus trap funcional (Tab nao escapa do modal).

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP

---

### 11. Historico vazio mostra empty state literal do Figma

Acessar prova com `total=0` movimentacoes (geralmente CRIADA recem
criada). Card preto mostra:
  > "Esta prova ainda nao teve movimentacoes."
  > "A timeline visual fica disponivel quando a prova for escaneada
  > pela primeira vez."

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP

---

### 12. Prova com 2 ciclos mostra agrupamento

Acessar `66f36e8b-13ec-45a7-812d-f2111db2a9e9` (CRIADA, ciclo 2 —
unica em produção). Timeline mostra labels "Ciclo 1" e "Ciclo 2"
separando os grupos de movimentacoes.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP

---

### 13. Sidebar destaca "Provas" em `/provas/[id]`

Em qualquer `/provas/<uuid>`, item "Provas" do menu lateral fica
destacado em amarelo (ADR-128). Validar tambem em `/provas` (exact
match).

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP

---

### 14. Mobile: `mobileNotice` em viewport ≤ 768px

Redimensionar viewport para 600px. Card branco e card preto somem;
aparece mensagem "Para acessar esse recurso, acesse a versao desktop."

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP

---

### 15. Lighthouse / acessibilidade basica

Rodar Lighthouse audit em `/provas/[id]`:
  - Score Accessibility ≥ 90.
  - Sem alertas criticos de contraste em texto sobre cinza claro
    (`#575757` sobre `#eaeaea` ≈ 6.8:1 → AA).
  - Navegacao por teclado: Tab passeia entre os 3-4 botoes da
    actionsRow + voltar + modal etiqueta abre/fecha.
  - Screen reader le `<h1>{prova.nome}</h1>` como heading principal;
    le `Requerimento: NNN · PRV-...` como subtitulo (sem confundir).
  - Tooltip do em-dash (AUD-011) em prova legacy: hover do mouse
    mostra "Prova legacy v3.0 — rota sera definida pelo backfill
    da Wave 7".

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP

---

## Validacoes pos-correcoes da auditoria (adicionais)

### 16. AUD-W2C08-004: artSlot visivel em loading e em erro

Acessar prova legacy (`66f36e8b` ou similar) onde a arte pode nao
estar mais no R2 (`imagem_url` vazia ou objeto removido). O slot da
arte deve aparecer como **quadrado cinza medio claramente distinto
do card branco** (token `--color-card-art-bg=#d9d9d9`). Texto
"Carregando arte..." ou "Nao foi possivel carregar a arte." aparece
sobre o cinza.

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP

---

### 17. AUD-W2C08-005+006: grid 3x2 sem 7o item

Confirmar visualmente que o `metaGrid` mostra exatamente **6 itens**
em 3 colunas × 2 linhas (Cliente / Rota / Criada em na linha 1;
Vendedor / Ciclo Atual / Status na linha 2). O `codigo_publico` agora
aparece no header (junto com `Requerimento: NNN`), nao no grid.

Em viewport 768-1100px, grid colapsa para `repeat(2, 1fr)` →
3 linhas × 2 colunas, todas as celulas preenchidas (sem orfa).

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP

---

### 18. AUD-W2C08-007: title >= 24px em viewport tablet

Em viewport 800-1000px, medir `.title` via DevTools. Tamanho deve ser
no minimo 24px (era ~16-19px antes).

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP

---

### 19. AUD-W2C08-011: tooltip no em-dash de prova legacy

Acessar prova legacy (`rota=NULL`). Hover do mouse no em-dash do
campo "Rota:" deve mostrar tooltip nativo do browser:
"Prova legacy v3.0 — rota sera definida pelo backfill da Wave 7".

**Status:** [ ] PASS · [ ] FAIL · [ ] SKIP

---

## Resumo

- Total de itens: 19 (15 originais do C08 + 4 novos pos-auditoria).
- PASS: __ / 19
- FAIL: __ / 19
- SKIP: __ / 19 (com motivo)

**Recomendacao final** (preencher apos execucao):
- [ ] Aprovado para PR final
- [ ] Bloqueado por items: ____

**Apêndice:** registrar aqui qualquer FAIL com bug + tela.
