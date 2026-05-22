# Smoke E2E manual — Componente 22 (Wave 8 v5.0)

**Componente:** 22 — Reativacao da Tela de Assinatura no Fluxo de Escaneamento
**Quem executa:** Mario (smoke manual — Decisao D11 Opcao B; a verificacao
programatica nao e viavel — exige backend local + auth + provas-fixture).
**Quando:** antes do PR `wave8-v5/componente-22 → development` e antes do
merge para `main`.

Marque cada cenario como ✅ aprovado / ❌ reprovado / ⏭️ pulado (com
justificativa).

---

## 0. Setup

1. **Backend local** (a partir da raiz do repo, com o `.venv` do projeto):
   `.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload`
2. **Frontend local:** `cd frontend && npm run dev`. Confirmar que
   `NEXT_PUBLIC_API_URL` aponta para o backend local (`http://localhost:8000`).
3. **Usuarios:** e preciso poder logar como **3Studio (admin)**, **Vendedor**,
   **Motorista** e **Clicheria**. Em producao ha 2 admins + 1 vendedor; para
   o smoke completo, cadastrar (via `/usuarios`, como admin) um motorista e
   um operador de clicheria de teste.
4. **Provas-fixture:** crie provas novas via `/nova-prova` (admin) em cada
   rota. Como toda prova nasce em `CRIADA`, o smoke **caminha** cada prova
   pelo fluxo — cada transicao assinada e, ela mesma, um teste. Sugestao:
   1 prova `Matriz`, 1 `Lam. Matriz`, 1 `Filial`, 1 `Lam. Filial`, e 1
   prova legacy (se houver alguma com `rota=NULL` em producao — ha 11).

> O modal de assinatura abre **automaticamente** apos o scan quando o
> usuario logado e o proximo ator. Toda saida do modal leva a `/provas/[id]`.

---

## 1. Motorista · QR · assina · prova movimenta

- **Pre:** prova em `Encaminhada para Laminacao` (rota Lam. Matriz). Logar
  como Motorista.
- **Passos:** `/escanear` → aba Camera → escanear o QR da prova.
- **Esperado:** o modal abre automaticamente (≤ ~500ms); exibe nome/codigo/
  rota da prova, a linha "Encaminhada para laminacao → Com motorista (ida
  laminacao)" e o badge de contexto "Travessia: ida para a laminacao".
  Assinar no canvas → "Confirmar" → view de sucesso "Movimentacao
  registrada" → "Ver prova" leva a `/provas/[id]` com o novo status.
- [ ] Resultado: ____

## 2. Vendedor · Aprovar · assina · prova movimenta

- **Pre:** prova em `Encaminhada para o Vendedor` (rota Filial). Logar como
  o Vendedor responsavel.
- **Passos:** escanear → o modal abre mostrando o seletor **Aprovar /
  Reprovar** → clicar "Aprovar" → assinar → "Confirmar".
- **Esperado:** status muda para `Aprovada pelo Vendedor`; sucesso; vai
  para `/provas/[id]`.
- [ ] Resultado: ____

## 3. Vendedor · Reprovar + motivo · assina

- **Pre:** prova em `Retirada pelo Vendedor` ou `Encaminhada para o
  Vendedor`. Logar como o Vendedor.
- **Passos:** escanear → seletor → "Reprovar" → o campo **Motivo da
  reprovacao** aparece (obrigatorio) → preencher → assinar → "Confirmar".
- **Esperado:** tentar confirmar sem motivo → erro "O motivo da reprovacao
  e obrigatorio." Com motivo + assinatura → status `Reprovada pelo
  Vendedor`; o motivo fica registrado (conferir em `/provas/[id]`).
- [ ] Resultado: ____

## 4. Ator errado · abre `/provas/[id]` (RN-014 / ADR-164)

- **Pre:** prova do proprio vendedor mas em estado de outro ator (ex.:
  `Com Motorista (ida laminacao)`). Logar como esse Vendedor.
- **Passos:** escanear a prova.
- **Esperado:** o modal **NAO** abre; navega direto para `/provas/[id]`
  (Decisao D6/ADR-164 — ator-errado in-scope). Escanear uma prova de
  **outro** vendedor (fora do escopo) → banner generico "Prova nao
  encontrada", sem navegar.
- [ ] Resultado: ____

## 5. Digitacao manual (C19) + assinatura

- **Pre:** mesma prova do Cenario 1. Logar como Motorista.
- **Passos:** `/escanear` → aba Manual → digitar o codigo
  `PRV-AAAA-MM-NNNNNN` da etiqueta → "Buscar prova".
- **Esperado:** apos a identificacao, o modal abre exatamente como no
  Cenario 1. Fluxo identico.
- [ ] Resultado: ____

## 6. Falha de rede ao submeter — retry

- **Pre:** prova acionavel pelo usuario logado. Abrir o modal e assinar.
- **Passos:** desligar a rede (DevTools → Offline) → "Confirmar".
- **Esperado:** erro "Falha de conexao..." no modal, **a assinatura
  permanece no canvas** (modal aberto). Religar a rede → "Confirmar"
  novamente → sucesso.
- [ ] Resultado: ____

## 7. Prova legacy v3.0 (`rota IS NULL`)

- **Pre:** uma prova legacy (rota NULL/PADRAO/DIRETA) num estado
  acionavel pelo usuario logado.
- **Passos:** escanear → assinar → confirmar.
- **Esperado:** o modal funciona identico; a prova movimenta conforme a
  maquina v3.0. Coexistencia preservada.
- [ ] Resultado: ____

## 8. Prova em estado terminal

- **Pre:** prova em `Recebida pela Clicheria` ou `Cancelada`. Qualquer
  perfil que a veja na listagem.
- **Passos:** escanear a prova.
- **Esperado:** o modal **NAO** abre; navega para `/provas/[id]` (sem
  `transicoes_permitidas` → regra unica D6/D8).
- [ ] Resultado: ____

## 9. Race condition (movimentacao simultanea)

- **Pre:** prova acionavel por 2 motoristas (ou simular). Abrir o modal
  no dispositivo A.
- **Passos:** no dispositivo B (ou outra aba), movimentar a mesma prova.
  Voltar ao A e "Confirmar".
- **Esperado:** backend responde 409; o modal mostra "A prova foi
  movimentada" + "Ver prova atualizada" → `/provas/[id]` com o estado
  atual (refresh).
- [ ] Resultado: ____

## 10. Clicheria · recebimento final

- **Pre:** prova em `Com Motorista (entrega final)`. Logar como Clicheria.
- **Passos:** escanear → assinar → "Confirmar".
- **Esperado:** status muda para `Recebida pela Clicheria` (terminal);
  view de sucesso; `/provas/[id]` mostra a prova concluida.
- [ ] Resultado: ____

---

## 11. Verificacoes transversais

- [ ] **Performance (RNF-002):** o modal aparece em ≤ 2s apos a
  identificacao (na pratica ≤ ~500ms — sem fetch extra, consome o
  `ScanResponse`).
- [ ] **Acessibilidade — teclado:** abrir o modal, navegar so com Tab /
  Shift+Tab (foco preso no modal — focus trap); `Esc` fecha; o foco vai
  para o titulo a cada troca de view.
- [ ] **Acessibilidade — axe:** rodar a extensao axe DevTools com o modal
  aberto (cada view) — sem violacoes criticas.
- [ ] **prefers-reduced-motion:** ativar "reduzir movimento" no SO/DevTools
  — o modal abre sem animacao de escala/fade.
- [ ] **Mobile-ready (RNF-013):** abrir em viewport ~360px — o modal cabe,
  rola se preciso, botoes empilham e tem ≥44px de altura. (Polimento fino
  e o C23.)
- [ ] **Console limpo:** nenhum erro/warning critico no console do browser
  durante todo o smoke.
- [ ] **Regressao C10/C19:** a camera ainda escaneia; a digitacao manual
  ainda funciona; provas sem transicao para o usuario continuam indo a
  `/provas/[id]`.

---

**Notas do executor:**

_(registrar aqui qualquer desvio, prints, ou cenario pulado com motivo)_
