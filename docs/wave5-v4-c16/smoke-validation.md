# Smoke validation — Wave 5 v4.0 / C16

**Branch:** `wave5-v4/componente-16`.
**Pré-requisito:** logar como admin (`admin@3studio.com.br` ou `ops@3studio.com.br`) no preview/staging — preview programático não chega à página (RBAC frontend redireciona). Mario executa manualmente.
**Total:** 20 cenários (5 de RotaFilter + 4 do card ROTA + 3 de CSV + 4 de filtros + 2 de a11y + 2 de anti-regressão).

---

## RotaFilter (3 botões visualmente idênticos ao v3)

### 1. [LAYOUT] Visual idêntico ao v3
- Abrir `/relatorios`.
- ✅ Aceitar: 3 botões — **Todas** (ativo), **Matriz**, **Filial** — visual idêntico a antes (mesma pill, mesma altura, mesmo espaçamento).
- ❌ Recusar: se aparecerem 4+ botões, ou se a pill mudou de tamanho/cor.

### 2. [SEMÂNTICA] Filtro "Matriz" inclui v4.0 + legacy + NULL
- Em `/relatorios?scope=geral`, contar o número total no card ROTA (Matriz + Filial).
- Clicar em "Matriz". URL deve ganhar `?rota_categoria=matriz`.
- ✅ Aceitar: o número de provas exibidas deve **incluir** todas as rotas MATRIZ + LAM_MATRIZ + PADRAO + provas legacy NULL cujo vendedor é MATRIZ.
- Validação via MCP: `SELECT COUNT(*) FROM provas_digitais p JOIN usuarios u ON u.id=p.vendedor_id WHERE p.rota IN ('MATRIZ','LAM_MATRIZ','PADRAO') OR (p.rota IS NULL AND u.localizacao='MATRIZ');`

### 3. [SEMÂNTICA] Filtro "Filial" inclui v4.0 + legacy + NULL
- Análogo ao #2, mas para Filial (FILIAL + LAM_FILIAL + DIRETA + NULL com vendedor FILIAL).

### 4. [TOGGLE] Click em ativo limpa o filtro
- Clicar em "Matriz" (ativo), depois em "Todas".
- ✅ URL volta a `?scope=geral` (sem `rota_categoria`).

### 5. [DEEP LINK] URL com `?rota_categoria=matriz` ativa botão
- Colar URL `/relatorios?scope=geral&rota_categoria=matriz`.
- ✅ Botão "Matriz" deve estar `aria-pressed="true"`; ranking + indicadores filtrados.

---

## Card ROTA na perspectiva Geral

### 6. [LABELS] Card ROTA mostra "Matriz N · Filial N"
- Abrir `/relatorios?scope=geral` sem filtros.
- ✅ Card ROTA deve mostrar 2 dots: **Matriz N · Filial M**.
- ❌ Recusar se aparecer "Padrao N · Direta M" (resíduo v3).

### 7. [INTEGRIDADE] Soma dos 2 baldes = total
- O número total exibido no card TOTAL GERAL deve **>= matriz + filial** (igual se não houver provas "indefinidas" — rota=NULL sem vendedor).
- Hoje em produção: 17 provas totais; consolidacao_rota.matriz = 4 (1 MATRIZ + 2 PADRAO + 1 NULL com vendedor MATRIZ, se houver), filial = 13 (3 DIRETA + 11 NULL com vendedor FILIAL — apurar com SELECT). Mario confirma o número exato.

### 8. [FALLBACK] Cache antigo sem `consolidacao_rota`
- Hard refresh da página (Ctrl+Shift+R). Se backend retornar `consolidacao_rota: undefined` (cache antigo), frontend deve **fallback** para `distribuicao_rota` legacy contando PADRAO e DIRETA.
- ✅ Card ROTA renderiza sem quebrar (sem zeros artificiais ou crashes).

### 9. [VISUAL] Tamanho/cor do card preservados
- Comparar visualmente com screenshot anterior (Wave 5 v3 closeout).
- ✅ Card ROTA tem mesmas dimensões; dots têm mesmas cores (`.rotaDotPadrao` preto, `.rotaDotDireta` amarelo).

---

## CSV export

### 10. [PROOFS] Coluna `contexto_motorista` + `codigo_publico`
- Em `/relatorios?scope=geral`, clicar em "Exportar CSV" → "Provas" (dataset=proofs).
- ✅ Abrir arquivo: cabeçalho contém `codigo_publico` e `contexto_motorista`.
- ✅ Linhas com `status IN {COM_MOTORISTA, COM_MOTORISTA_*}` têm `contexto_motorista` preenchido (`entrega_final`/`ida_laminacao`/`volta_laminacao`).
- ✅ Linhas com outros status têm `contexto_motorista` vazio.

### 11. [OVERDUE] Coluna `contexto_motorista`
- Análogo ao #10, mas dataset=overdue.

### 12. [SUMMARY] Linhas `rota_v4_*` + `consolidacao_rota_*` + `contexto_motorista_*`
- Em `/relatorios?scope=geral`, "Exportar CSV" → "Resumo" (dataset=summary).
- ✅ Cabeçalho `scope,indicador,valor`.
- ✅ Linhas (entre outras):
  - `geral,rota_PADRAO,N` (legacy preservado)
  - `geral,rota_v4_v4_matriz,M` (Wave 5 v4.0 novo)
  - `geral,rota_v4_legacy_null_matriz,K` (Wave 5 v4.0 novo)
  - `geral,consolidacao_rota_matriz,X`
  - `geral,consolidacao_rota_filial,Y`
  - `geral,contexto_motorista_entrega_final,Z` (apenas se houver provas com motorista)

---

## Filtros expandidos

### 13. [STATUS] Aceitação dos 17 valores v3+v4
- Inspecionar dropdown `Status` na FiltersBar.
- ✅ Lista contém todos os 17 estados (`STATUS_OPTIONS`): CRIADA, RETIRADA, ..., COM_MOTORISTA_IDA_LAMINACAO, ..., LAMINACAO_CONCLUIDA, ..., ENCAMINHADA_PARA_O_VENDEDOR.

### 14. [STATUS] Filtro por COM_MOTORISTA_IDA_LAMINACAO
- Selecionar `Status: Com motorista (ida laminacao)`.
- ✅ URL ganha `?status=COM_MOTORISTA_IDA_LAMINACAO`; resultado mostra apenas provas naquele status.
- ✅ Antes da Wave 5 v4.0, URL com esse status era zerada silenciosamente — agora preserva.

### 15. [ROTA] Filtro por rota exata `?rota=MATRIZ`
- Colar URL `/relatorios?scope=geral&rota=MATRIZ`.
- ✅ Reports retorna apenas provas com `rota=MATRIZ` (1 prova hoje em produção).

### 16. [PRECEDÊNCIA] `rota_categoria` tem precedência sobre `rota`
- Colar URL `/relatorios?scope=geral&rota=MATRIZ&rota_categoria=filial`.
- ✅ Backend aplica `rota_categoria=filial` (precedência) — resultado filtra Filial, ignorando `?rota=MATRIZ`.
- Confirmar via API direta: `curl -H "Authorization: Bearer ..." "<URL>"`.

---

## Acessibilidade

### 17. [SR-ONLY] Tabela permanente no DonutChart
- No `/relatorios?scope=geral`, ativar leitor de tela (NVDA/VoiceOver) ou inspecionar DOM.
- ✅ Localizar `<table class="srOnly">` antes do `<details>` no DonutChart "Provas Ativas".
- ✅ Tabela tem `<caption>` + `<thead>` (Categoria/Quantidade/Percentual) + linhas para cada segmento.
- ✅ Leitor de tela lê automaticamente sem precisar clicar no `<details>`.

### 18. [ARIA-HIDDEN] `<details>` não duplica na leitura por AT
- Inspecionar DOM: `<details aria-hidden="true">` deve estar presente.
- ✅ Leitor de tela **não** lê a tabela interna duas vezes.

---

## Anti-regressão

### 19. [DASHBOARD V3] `/dashboard` intocado
- Abrir `/dashboard`.
- ✅ Cards de contadores funcionam idêntico ao v3 (RF-014, US-013).
- ✅ Sem erros no console. Sem regressão visual.

### 20. [REPORT 3STUDIO + VENDEDORES + CLICHERIA] tabs preservadas
- Clicar nas tabs 3Studio, Vendedores, Clicheria.
- ✅ Cada perspectiva renderiza idêntico ao v3.
- ✅ Em Clicheria, `via_padrao`/`via_direta` agora incluem v4.0 (motorista + filial direto), mas labels "Via PADRAO (motorista)" / "Via DIRETA (filial)" permanecem (preserva layout).

---

## Critério de aprovação

- ✅ **TODOS os 20 cenários verdes** → PR autorizado para auditoria sênior.
- ⚠️ 1-3 cenários amarelos (esperado, mas validável em retest) → discutir com Mario.
- ❌ Qualquer cenário vermelho → corrigir antes do PR.

**Items 4, 5, 14, 15, 16, 17, 18, 20 podem ser SKIP em produção:** dependem de Mario logar e clicar; preview programático não cobre.

---

**Fim do smoke-validation.md.**
