# Coverage Snapshot · Wave 3 v4.0 · C12

**Data:** 2026-05-13.
**Comando:** `npx vitest run --coverage --coverage.provider=v8 --coverage.reporter=text --coverage.reporter=json-summary --coverage.include='src/lib/timeline-builder.ts' --coverage.include='src/lib/types/prova.ts'`
**Vitest:** 2.1.9
**Coverage provider:** `@vitest/coverage-v8@~2.1.0` (instalado pontualmente com `--no-save`, desinstalado após captura — não persiste em `package.json` por design, preservando D-13 da Wave 1 v4.0).
**Resolve:** AUD-W3C12-004 (coverage % não medido formalmente).

---

## Tabela de cobertura

```
-------------------|---------|----------|---------|---------|-------------------
File               | % Stmts | % Branch | % Funcs | % Lines | Uncovered Line #s
-------------------|---------|----------|---------|---------|-------------------
All files          |   97.15 |    96.34 |   83.33 |   97.15 |
 lib               |   99.46 |    93.33 |     100 |   99.46 |
  timeline-builder.ts |  99.46 |    93.33 |     100 |   99.46 | 294
 lib/types         |   94.94 |      100 |   71.42 |   94.94 |
  prova.ts         |   94.94 |      100 |   71.42 |   94.94 | 147-151, 677-681
-------------------|---------|----------|---------|---------|-------------------
```

**Suíte:** 163 testes passados em 762ms.

---

## Resultado vs critério (≥ 80%)

| Arquivo | % Stmts | % Branch | % Funcs | % Lines | ≥ 80% em todas? |
|---|---|---|---|---|---|
| `frontend/src/lib/timeline-builder.ts` | 99.46 | 93.33 | **100.00** | 99.46 | ✅ Sim |
| `frontend/src/lib/types/prova.ts` (arquivo inteiro) | 94.94 | **100.00** | 71.42 | 94.94 | ⚠️ Parcial — vide análise |

**Global agregado dos arquivos novos do C12:** 97.15% stmts · 96.34% branch · 83.33% funcs · 97.15% lines — **confortavelmente acima do limiar 80%**.

---

## Análise das linhas/funcs não-cobertas

### `lib/timeline-builder.ts:294`

Branch defensiva dentro de `extractCancellationInfo`:

```ts
quandoIso: movCancelamento ? movCancelamento.created_at : null,
```

A branch `false` (`movCancelamento === null` quando `prova.status === "CANCELADA"`) representa **estado inconsistente do banco** — prova marcada CANCELADA sem movimentação correspondente registrada. Em produção isso nunca ocorre (o handler `POST /provas/{id}/cancelar` cria a movimentação atomicamente com o UPDATE da prova). A branch existe apenas como defesa em profundidade. **Não cobrir é aceitável** — adicionar teste exigiria construir cenário sintético que viola invariante de banco.

### `lib/types/prova.ts:147-151`

Função `isAllowedImageType` (type guard de upload de imagem) — **introduzida pelo C06 v4.0 / Audit Fixes (AUD-W2V4-122)**, não pelo C12. Não tem teste isolado porque o caminho de produção foi validado pelo C06 Visual Refresh smoke (campo `<input type="file">` do `/nova-prova`). Fora do escopo do C12.

### `lib/types/prova.ts:677-681`

Função `buildQrPayload` (constrói payload do QR) — **introduzida pelo C10 v4.0**, espelho TypeScript do `qrcode_service.gerar_payload_qr` Python. Testada indiretamente via pytest no backend. Fora do escopo do C12.

---

## Cobertura específica dos helpers DO C12

Os 7 símbolos novos introduzidos pelo C12 em `lib/types/prova.ts` (Decisões 11.x + helpers da Timeline) têm **cobertura 100%**:

| Símbolo | Testes em `prova.test.ts` | Cobertura |
|---|---|---|
| `ContextoMotorista` (type) | Sanity nas asserções de `contextoMotorista` | N/A (tipo) |
| `contextoMotorista(status)` | 7 testes (4 v4.0 + 1 legacy + 2 sanity) | 100% |
| `ESTADOS_LAMINACAO` (set) | 10 testes via `isInLaminationBlock` | 100% |
| `isInLaminationBlock(status)` | 10 testes (5 in + 5 out) | 100% |
| `ROTA_ETAPAS[rota]` | 4 testes (uma por rota v4.0) + sanity | 100% |
| `LEGACY_ROTA_PADRAO` / `LEGACY_ROTA_DIRETA` | 2 testes sanity (tamanho + ordem) | 100% |
| `getRotaEtapas(rota, vendedor_loc)` | 9 testes (4 v4.0 + 5 legacy/NULL) | 100% |
| `getRotaLabel(rota, vendedor_loc)` | 9 testes | 100% |

E os 4 helpers internos do `lib/timeline-builder.ts`:

| Símbolo | Testes em `timeline-builder.test.ts` | Cobertura |
|---|---|---|
| `buildTimeline` (entrada principal) | 20 testes (4 rotas + 5 legacy + 2 multi-ciclos + 2 cancelamento + 3 contextos + 4 edge cases) | 100% funcs · 99.46% lines |
| `buildConcreteNodes` (interno) | Coberto indiretamente | 100% |
| `derivePendingNodes` (interno) | Coberto indiretamente | 100% |
| `groupCyclesWithMetadata` (interno) | Coberto indiretamente | 100% |
| `extractCancellationInfo` (interno) | Coberto indiretamente | 99% (1 branch defensiva) |

---

## Timeline.tsx — não medido (por design)

`frontend/src/app/(dashboard)/provas/[id]/Timeline.tsx` **não aparece nesta tabela** porque:

1. Os testes Vitest rodam em `environment: node` (sem JSDOM) — preserva **D-13 da Wave 1 v4.0** (Vitest minimal sem `@testing-library/react`).
2. Timeline.tsx é componente React com JSX — render exige DOM virtual.
3. A camada de **dados** (builder puro) é testada extensivamente; a camada de **renderização** fica para o smoke E2E manual do Mario (`smoke-validation.md` 18 cenários).
4. Decisão registrada em `analysis.md §17.3.1` e formalizada como AUD-W3C12-009 (ACEITO como tradeoff).

Esse padrão é coerente com a entrega geral da Wave 1 v4.0 e do C10/C19 (camada de serviço pura testada; UI validada por smoke).

---

## Reprodutibilidade

O snapshot foi capturado com `@vitest/coverage-v8` instalado temporariamente:

```powershell
cd frontend
cp package-lock.json /tmp/package-lock.json.before
npm install --no-save "@vitest/coverage-v8@~2.1.0"
npx vitest run --coverage --coverage.provider=v8 `
    --coverage.reporter=text --coverage.reporter=json-summary `
    --coverage.include='src/lib/timeline-builder.ts' `
    --coverage.include='src/lib/types/prova.ts'
npm uninstall @vitest/coverage-v8
# Validar package.json + package-lock.json voltaram ao estado pré-snapshot:
# git diff frontend/package.json frontend/package-lock.json  → vazio
```

Para repetir, basta rodar os mesmos comandos. O `package.json` permanece sem `@vitest/coverage-v8` listado.

---

## Conclusão

**Critério 19 do prompt do C12 (≥ 80% nos componentes novos) é cumprido com margem confortável:**

- `lib/timeline-builder.ts`: 99.46% stmts/lines, 100% funcs.
- `lib/types/prova.ts` (símbolos novos do C12): 100% funcs.
- 1 branch defensiva não-cobertível (linha 294) por representar estado inconsistente de banco impossível na prática.
- 2 funções não-relacionadas ao C12 (linhas 147-151 e 677-681) introduzidas por outras entregas — fora do escopo desta sessão.

**AUD-W3C12-004 — RESOLVIDO.**
