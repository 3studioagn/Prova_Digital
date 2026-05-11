# Plano de Correcao — Wave 3 v4.0 · Componente 10 (Pos-Auditoria)

**Branch:** `wave3-v4-c10/fixes/plan` (Gate 1) -> `wave3-v4-c10/fixes/execution` (Gate 2).
**Auditor de origem:** `docs/wave3-v4-c10/audit-report.md` (Claude Opus 4.7, 2026-05-11).
**Veredito original:** APROVAR COM CORRECOES — **0 CRITICO + 3 ALTOS + 6 MEDIOS + 8 BAIXOS + 5 INFO = 22 achados**.
**Sessao de correcao:** Engenheiro de Software Senior · Gate-based two-stage.

> **Status pre-execucao:** Gate 1 (este documento) define plano e ordem. Gate 2 executa,
> commit-por-achado, com smoke validation interna ao final. Recomendacao final dirige nova
> auditoria independente para confirmar resolucao.

---

## 1. Confirmacao de pre-requisitos (Secao 2/3 do prompt)

### 1.1 Artefatos no repo

| Caminho | Status |
|---|---|
| `docs/wave3-v4-c10/audit-report.md` | ✅ lido integralmente (832 LOC) |
| `docs/wave3-v4-c10/analysis.md` | ✅ lido (1012 LOC) — Gate 1 + Execucao + Refinamento Visual ate iteracao 7 |
| `docs/wave3-v4-c10/contrato-c19.md` | ✅ presente (226 LOC) |
| `docs/wave3-v4-c10/smoke-validation.md` | ✅ presente (324 LOC, template 20 cenarios — nao executado) |
| `docs/wave3-v4-c10/figma-references.md` | ✅ presente (71 LOC, placeholder textual) |
| `docs/wave3-v4-c10/figma-reference.png` ou variantes | ❌ **AUSENTE** mas **CHANCELADO** pelo Mario em 2026-05-11 (AUD-001 rebaixado de CRITICO para INFO) |
| `CLAUDE.md` | ✅ lido via system reminder — secao "Identificacao de provas: contrato compartilhado" + "Notas visuais consolidadas (pos-iteracoes 4-7 do C10)" |
| `DECISIONS.md` | ✅ ADR-132 a ADR-137 do C10 v4.0 (sem ADR-138/139 ainda) |
| `CHANGELOG.md` | ✅ secao C10 v4.0 vai ate iteracao 7 |

### 1.2 Codigo-fonte tocado pelos achados

| Caminho | Status / LOC | Achados que tocam |
|---|---|---|
| `frontend/src/app/(dashboard)/escanear/page.tsx` | ✅ lido (658 LOC) | AUD-004, AUD-006, AUD-018 |
| `frontend/src/app/(dashboard)/escanear/escanear.module.css` | ✅ (802 LOC, sera tocado em AUD-007 doc-only) | AUD-007 |
| `frontend/src/lib/services/identificacao-prova.ts` | ✅ lido (178 LOC) | AUD-020 |
| `frontend/src/lib/services/__tests__/identificacao-prova.test.ts` | ✅ lido (266 LOC, 16 testes) | AUD-020 (testes novos para `MENSAGENS_ERRO` exposta) |
| `frontend/src/hooks/useScanner.ts` | ✅ lido (179 LOC) | AUD-011, AUD-022 |
| `backend/app/api/v1/provas.py` (scan handler L1640-2030) | ✅ lido | AUD-005 (doc), AUD-010, AUD-013 |
| `backend/app/domain/schemas/prova.py` (ScanRequest L295-410) | ✅ lido | AUD-012 |
| `backend/tests/test_provas_api.py` (test_scan_* L1998-2676) | ✅ lido | AUD-013 (teste novo DB error camera) |
| `docs/wave3-v4-c10/analysis.md` (§Refinamento Visual L856-1012) | ✅ | AUD-008 |
| `CHANGELOG.md` (secao C10 v4.0 L5-200) | ✅ | AUD-002, AUD-016, AUD-019 |
| `DECISIONS.md` (final em ADR-137) | ✅ | AUD-002 (ADR-138/139), AUD-005 (ADR doc) |

### 1.3 MCP Supabase — estado em producao (read-only)

| Verificacao | Resultado | Bate com audit-report? |
|---|---|---|
| `alembic_version` | `"012"` | ✅ |
| `provas_digitais` total | **17** | ✅ |
| `provas_digitais WHERE codigo_publico IS NULL` | **0** | ✅ |
| `provas_digitais WHERE codigo_publico LIKE 'PRV-%'` | **17** (100%) | ✅ |
| `rota IS NULL` (legacy) | **11** | ✅ |
| `rota IS NOT NULL` | **6** (1 MATRIZ + 2 PADRAO + 3 DIRETA) | ✅ |
| Index `idx_provas_codigo_publico` | UNIQUE btree ✅ | ✅ |
| `pol_provas_select` (RLS) | 4 perfis cobertos via `app_private.current_user_*()` | ✅ |
| `EXPLAIN ANALYZE` em `codigo_publico = 'PRV-2026-05-TEX9GW'` | Seq Scan, 0.124ms (esperado em base de 17 linhas) | ✅ |
| `get_advisors` security | 1 INFO `rls_enabled_no_policy alembic_version` (ADR-025) + 1 WARN `auth_leaked_password_protection` (ADR-027) — **pre-existentes** | ✅ |
| `get_advisors` performance | 13 INFO `unused_index` (todos pre-existentes — incluindo `idx_provas_rota` esperado) — **nada novo** | ✅ |

**Veredito:** estado real bate 100% com `audit-report.md`. **Zero divergencia.**

### 1.4 Cloudflare R2

Nenhum achado do relatorio toca Cloudflare. Relatorio confirma bucket
`rastreio-provas-artes` saudavel; sessao de correcao **nao modificara nada**
em Cloudflare. Sem revalidacao desnecessaria nesta sessao.

### 1.5 Decisao do dono do projeto sobre `figma-reference.png` (AUD-001)

Mario chancelou em 2026-05-11: "Nao vou anexar a image-reference, pois nao vamos mexer
no layout, pois ja esta tudo correto." AUD-W3C10-001 foi formalmente **rebaixado de
CRITICO para INFO** pelo proprio auditor antes desta sessao comecar. Esta sessao **nao
trata achados de fidelidade visual contra PNG** porque (a) PNG nao existe in-repo, (b)
layout chancelado, (c) zero achado restante e de fidelidade. Risco residual aceito.

---

## 2. Inventario consolidado dos 22 achados

### Legenda

| Coluna | Significado |
|---|---|
| **C19?** | "S" se afeta viabilidade do C19 (proximo componente). |
| **Enum?** | "S" se e achado de seguranca anti-enumeracao (DAT §8.2). |
| **Legacy?** | "S" se afeta provas com `rota=NULL` ou `codigo_publico=NULL`. |
| **Figma?** | "S" se e achado de fidelidade visual. |

### Tabela completa (22 entradas)

| ID | Sev | Categoria | Resumo | Arquivo/Linha | Status | C19? | Enum? | Legacy? | Figma? |
|---|---|---|---|---|---|---|---|---|---|
| AUD-W3C10-002 | ALTO | Documentacao | Iteracoes 8 (footer manual fix) e 9 (panel crossfade) NAO documentadas em analysis.md/CHANGELOG/DECISIONS | `analysis.md §Refinamento Visual` + CHANGELOG L5-200 + commits `dc7d347` + `bffe30b` | pendente | N | N | N | N |
| AUD-W3C10-003 | ALTO | Cobertura/Aderencia | `smoke-validation.md` (20 cenarios) **nao executado** — sem prova empirica de comportamento real | `docs/wave3-v4-c10/smoke-validation.md` | pendente — depende de execucao humana (Mario) em producao | N | N | parcial (cen.6+9) | N |
| AUD-W3C10-004 | ALTO | Correcao (bug) | Race em `handleDetect` (sem guard de estado) + `useEffect` com deps incompletas (`[cameraState.kind]`) — multi-scan rapido pode redirecionar para prova errada | `page.tsx:75-77 + 84-119` | pendente | N | N | N | N |
| AUD-W3C10-005 | MEDIO | Seguranca (anti-enum) | Timing differential 422 vs 404 no caminho camera — vetor real = 0 (RLS filtra antes do hash) mas merece ADR documentando como defesa em profundidade | `provas.py:1957-1973` | pendente (doc-only — recomendacao: ADR sem mudanca de codigo) | N | **S** (doc) | N | N |
| AUD-W3C10-006 | MEDIO | Manutenibilidade | Iteracao 9 (panel crossfade `AnimatePresence`) sem ADR + `prefers-reduced-motion` nao verificado especificamente para crossfade | `page.tsx:195-222` + DECISIONS.md (sem ADR-138) | pendente | N | N | N | N |
| AUD-W3C10-007 | MEDIO | Manutenibilidade | Iteracao 8 (footer manual width fix) sem ADR + sem entrada CHANGELOG | commit `dc7d347` (escanear.module.css `.innerFooter` 3 linhas) | pendente | N | N | N | N |
| AUD-W3C10-008 | MEDIO | Documentacao | `analysis.md §Refinamento Visual` (L856-1012) so vai ate iteracao 7 — falta R8 + R9 | `analysis.md` | pendente | N | N | N | N |
| AUD-W3C10-011 | MEDIO | Correcao (bug) | `useScanner` cleanup nao aguarda `stop()` antes de re-mount — re-iniciar camera rapido pode disparar "Cannot stop, scanner is not running" | `useScanner.ts:151-176` | pendente | N | N | N | N |
| AUD-W3C10-020 | MEDIO | Preparacao C19 | `MENSAGENS_ERRO` const nao exportada — C19 nao pode customizar mensagens condicionando por `result.codigo` sem reescrever mapa | `identificacao-prova.ts:66-73` | pendente | **S** | N | N | N |
| AUD-W3C10-009 | BAIXO | Documentacao | framer-motion: nota dizendo "sem Framer Motion novo" omitiu que e a primeira vez em `/escanear`. Dependencia pre-existente desde commit `86b0f9d` (Wave 3 v3.0) mas import e novo | analysis.md + ADR-135 | pendente — doc only | N | N | N | N |
| AUD-W3C10-010 | BAIXO | Seguranca (forense) | Audit log de scan NAO grava o `payload` ou `codigo` bruto recebido — investigacao forense de QR adulterado fica cega | `provas.py:1985-2001` | pendente | N | N | N | N |
| AUD-W3C10-012 | BAIXO | Aderencia/Documentacao | `body.codigo` `max_length=64` vs analysis.md §5.2 prometia `max_length=20` (PRV tem 18 chars) — discrepancia doc<->code | `prova.py:339` | pendente | N | N | N | N |
| AUD-W3C10-013 | BAIXO | Cobertura | Falta teste backend explicito de DB error no caminho camera v4.0 (manual ja tem `test_scan_manual_db_error_retorna_502`) | `test_provas_api.py:2633` | pendente | N | N | N | N |
| AUD-W3C10-015 | BAIXO | Performance | Bundle `/escanear` cresceu 168 -> 208 kB pos-iteracao 5 (framer-motion); ADR-135 ja explica. Confirmar documentado | `package.json` + ADR-135 | pendente (doc-only — apendice no CHANGELOG ja existe; nada a codigo) | N | N | N | N |
| AUD-W3C10-016 | BAIXO | Documentacao | CHANGELOG diz `page.tsx 740->414` e `css 589->433` mas estado real e `page.tsx 658`/`css 802` pos-iteracoes 3-9 | CHANGELOG L5-200 | pendente | N | N | N | N |
| AUD-W3C10-018 | BAIXO | Manutenibilidade | `eslint-disable-next-line react-hooks/exhaustive-deps` em `page.tsx:118` sem comentario do "por que" | `page.tsx:118` | pendente — sera resolvido em conjunto com AUD-004 (a correcao da race torna o `eslint-disable` desnecessario ou justificado) | N | N | N | N |
| AUD-W3C10-019 | BAIXO | Documentacao | CHANGELOG nao tem secao "Erros conhecidos" — bug AUD-004 nao listado (auditor identificou) | CHANGELOG L5-200 | pendente — sera resolvido junto com AUD-002 (atualizacao CHANGELOG) | N | N | N | N |
| AUD-W3C10-001 | INFO | Fidelidade/Doc | figma-reference PNGs ausentes; **chancelado** pelo Mario em 2026-05-11 — sem acao | `docs/wave3-v4-c10/` | RESOLVIDO_POR_DECISAO (registrar status final no apendice do audit-report) | N | N | N | S |
| AUD-W3C10-014 | INFO | Performance | Seq Scan em base de 17 linhas (Postgres planner ok) — comportamento esperado; planner usara index quando crescer | EXPLAIN | RESOLVIDO_POR_DESIGN (registrar no apendice) | N | N | N | N |
| AUD-W3C10-017 | INFO | Aderencia | Audit log inclui `transicoes_permitidas` que frontend nao consome mais (proposital para C11 v4.0 consumir do detalhe) | `provas.py:1998` + ADR-132 | RESOLVIDO_POR_DESIGN (registrar) | N | N | N | N |
| AUD-W3C10-021 | INFO | Manutenibilidade | `useExecutarTransicao` orfao — sera consumido pelo C11 v4.0 | `frontend/src/hooks/useExecutarTransicao.ts` | RESOLVIDO_POR_DESIGN (registrar — escopo explicitamente protegido) | N | N | N | N |
| AUD-W3C10-022 | INFO | Acessibilidade/Responsividade | `qrbox: {width: 250, height: 250}` fixo no html5-qrcode — pode quebrar em viewport <300px | `useScanner.ts:116` | pendente — fix trivial (~5 LOC) torna responsivo | N | N | N | N |

**Total:** 22 entradas. Nenhuma omitida.

**Distribuicao por categoria de tratamento especial:**
- **C19 (afeta viabilidade do proximo componente):** 1 (AUD-020).
- **Anti-enumeracao (seguranca):** 1 (AUD-005, doc-only — vetor real = 0 confirmado).
- **Provas legacy:** 1 parcial (AUD-003, cenarios 6 e 9 do smoke).
- **Fidelidade Figma:** 1 (AUD-001, chancelado — sem acao).

---

## 3. Plano de correcao por achado

Cada entrada abaixo tem: **estrategia · arquivos · risco regressao · risco C19 · validacao**.

### 3.1 ALTOS

#### AUD-W3C10-002 — Iteracoes 8/9 sem documentacao
- **Estrategia:** Acumular em 3 documentos: (a) apender bloco "Iteracao 8" + "Iteracao 9"
  no CHANGELOG L189-200 (com SHAs `dc7d347` + `bffe30b`, motivacao, escopo, impacto),
  (b) criar ADR-138 (panel crossfade — trade-off bundle/a11y/UX) e ADR-139 (footer
  manual width fix — bug de regressao da iteracao 4 corrigido), (c) cobertura
  parcial em `analysis.md §Refinamento Visual` ja inclusa em AUD-008.
- **Arquivos:** `CHANGELOG.md` (modificacao), `DECISIONS.md` (modificacao — apender 2 ADRs novos).
- **Risco regressao:** baixo (doc-only).
- **Risco C19:** nenhum.
- **Validacao:** revisao manual da existencia dos ADRs e da nova secao do CHANGELOG.

#### AUD-W3C10-003 — smoke-validation.md nao executado
- **Estrategia:** Marcar formalmente como **deferred com responsavel humano**:
  Mario executa em producao apos PR (paridade com Wave 2 v4.0 / C08 — smoke E2E e
  responsabilidade do dono). Esta sessao **nao executa** porque (a) requer login
  como vendedor/motorista/clicheria que so o Mario tem, (b) requer impressao de
  etiqueta fisica para cenarios camera, (c) requer browser real em telefone (HTTPS).
- **Tratamento:** apendice no `audit-report.md` registrando status "DEFERRED — humano
  executa antes do merge final; bug encontrado vira issue/correcao em sessao separada".
- **Arquivos:** `docs/wave3-v4-c10/audit-report.md` (apendice de status), `docs/wave3-v4-c10/fix-validation.md` (a criar no Gate 2).
- **Risco regressao:** nenhum.
- **Risco C19:** nenhum.
- **Validacao:** apendice escrito + smoke-validation.md preserva estado como template.

#### AUD-W3C10-004 — Race em handleDetect + useEffect deps incompletas
- **Estrategia:**
  ```tsx
  // Antes:
  const handleDetect = useCallback((payload: string) => {
    setCameraState({ kind: "identifying", payload });
  }, []);

  // Depois:
  const handleDetect = useCallback((payload: string) => {
    setCameraState((prev) =>
      prev.kind === "scanning" ? { kind: "identifying", payload } : prev,
    );
  }, []);
  ```
  Mais: trocar `useEffect` dep `[cameraState.kind]` por `[cameraState]` (rerun
  sempre que o objeto state muda, mas o early-return em `if (cameraState.kind !== "identifying")` continua barrando recomputacoes desnecessarias). A `cancelled` flag preserva a semantica de cancelamento em caso de unmount. O `eslint-disable` linha 118 ja fica desnecessario (deps agora completas) — remover.
- **Arquivos:** `page.tsx:75-77 + 84-119` (modificacao cirurgica de ~6 linhas).
- **Risco regressao:** baixo. O `cancelled` flag ja previne side-effect duplicado; mudanca de deps so faz o efeito reagir corretamente a um payload novo no mesmo estado (que ja era o comportamento desejado).
- **Risco C19:** nenhum (nao toca camada de servico).
- **Validacao:**
  - Teste unitario manual (mental): simular 2 onDetect com payloads A e B em sequencia rapida — depois da correcao, o segundo `setCameraState` nao executa porque `prev.kind` ja e `"identifying"` (nao `"scanning"`).
  - Teste de regressao via build (`npx tsc --noEmit` + `npx next build`).
  - Adicionar caso ao `smoke-validation.md` cenario 15 (verificar comportamento sob multi-scan rapido).

### 3.2 MEDIOS

#### AUD-W3C10-005 — Timing differential 422 vs 404 (doc-only)
- **Estrategia:** Adicionar ADR-140 "Timing differential 422 vs 404 no caminho camera
  (defesa em profundidade)" documentando que: (a) RLS filtra fora-do-scope ANTES do
  hash check entao 422 so dispara para prova IN scope (vetor real = 0); (b) hash check
  apos lookup e intencional para nao gastar timing em casos invalidos massivos; (c)
  manter como esta, sem mudanca de codigo.
- **Anti-enumeracao:** ja garantida no caminho manual (`validar_formato_codigo_publico` antes do SELECT retorna 404 generico). No caminho camera, RLS faz o mesmo papel implicitamente.
- **Arquivos:** `DECISIONS.md` (apender ADR-140).
- **Risco regressao:** zero (doc-only).
- **Risco C19:** nenhum.
- **Validacao:** ADR-140 publicado + cross-link no `audit-report.md` apendice.

#### AUD-W3C10-006 — Iteracao 9 (crossfade) sem ADR + a11y nao verificado
- **Estrategia:** Coberto por AUD-002 (criar ADR-138). ADR-138 deve incluir:
  (a) trade-off bundle/a11y/UX, (b) confirmacao explicita de que framer-motion `useReducedMotion`
  ja respeita `prefers-reduced-motion` por padrao em `AnimatePresence` + `motion.div`
  (referencia: docs framer-motion), (c) teste empirico mental do comportamento durante
  transicao (panel sai com fade ANTES de o `enabled={cameraState === "scanning"}`
  desligar — `cancelarCamera` e chamado em `trocarParaManual`, o que ja desliga o
  scanner antes do fade exit).
- **Arquivos:** `DECISIONS.md` (ADR-138, ja contado em AUD-002).
- **Risco regressao:** zero (doc-only).
- **Risco C19:** nenhum.
- **Validacao:** ADR-138 cobre os 3 pontos.

#### AUD-W3C10-007 — Iteracao 8 (footer fix) sem ADR/CHANGELOG
- **Estrategia:** Coberto por AUD-002 (criar ADR-139). ADR-139 deve documentar:
  (a) bug residual pos-iteracao 4: `.innerFooter` no tab Manual com `width: auto` (collapse no conteudo) em vez dos 100% da coluna do Camera; (b) fix de 3 linhas em
  `escanear.module.css` adicionando `width: 100%`, `max-width: 554px`, `align-self: stretch`; (c) sem regressao no tab Camera (la `width: 100%` ja estava implicito por flex).
- **Arquivos:** `DECISIONS.md` (ADR-139, ja contado em AUD-002).
- **Risco regressao:** zero (doc-only).
- **Risco C19:** nenhum.
- **Validacao:** ADR-139 publicado.

#### AUD-W3C10-008 — analysis.md so vai ate iteracao 7
- **Estrategia:** Apender 2 blocos `R8` e `R9` na secao "Refinamento Visual" do
  `analysis.md` (L856-1012). Cada bloco com: SHA, motivacao, codigo mudado em
  resumo (sem reproduzir CSS inteiro), referencia ao ADR correspondente.
- **Arquivos:** `docs/wave3-v4-c10/analysis.md` (modificacao final).
- **Risco regressao:** zero (doc-only).
- **Risco C19:** nenhum.
- **Validacao:** secao R8 + R9 presentes; cross-link com ADR-138/139.

#### AUD-W3C10-011 — useScanner cleanup nao aguarda stop()
- **Estrategia:** Refatorar cleanup do `useEffect` em `useScanner.ts:151-176` para
  guardar uma Promise em ref e aguardar com `await` antes de criar nova instancia
  no proximo run. Pseudo-codigo:
  ```tsx
  const stoppingRef = useRef<Promise<void> | null>(null);
  // No effect:
  if (stoppingRef.current) await stoppingRef.current; // aguarda cleanup anterior
  // ... cria instancia
  // No cleanup:
  stoppingRef.current = instance.stop().catch(/* ok */).finally(() => { instance.clear(); });
  return () => { /* nada — cleanup ja agendado */ };
  ```
  Alternativa mais conservadora: aceitar o comportamento atual e documentar limite
  conhecido em ADR (bug de re-init rapido raramente reproduzivel). **Recomendacao:**
  manter cirurgico — usar a `stoppingRef` mas com guard simples.
- **Arquivos:** `frontend/src/hooks/useScanner.ts:64-179` (modificacao localizada).
- **Risco regressao:** **medio**. O `useScanner` e o ponto critico do scan; mudanca
  de cleanup pode causar regressao em "abrir camera, cancelar, abrir de novo". Mitigacao:
  validacao manual antes do commit (npm dev + browser real cancela e abre 3x em sequencia).
- **Risco C19:** nenhum (useScanner nao e tocado por C19).
- **Validacao:**
  - `tsc --noEmit` + `next build`.
  - Smoke manual cenario 16 do smoke-validation (mid-scan cancel + abrir de novo).
  - Sem teste automatizado para html5-qrcode (acoplado a hardware).

#### AUD-W3C10-020 — MENSAGENS_ERRO nao exportada (C19!)
- **Estrategia:** Adicionar **export** em `identificacao-prova.ts` para o objeto
  `MENSAGENS_ERRO` (renomeando para `MENSAGENS_ERRO_PADRAO` para deixar claro
  que e o default) + funcao helper `mensagemPara(codigo: CodigoErro): string`.
  Atualizar `contrato-c19.md` documentando como C19 customiza:
  ```tsx
  import { mensagemPara } from "@/lib/services/identificacao-prova";
  // C19 pode chamar para reutilizar OU sobrescrever via switch local.
  ```
  **Importante:** NAO mover `MENSAGENS_ERRO` para outro arquivo; manter co-localizado
  com `CodigoErro` para refactor seguro.
- **Arquivos:** `frontend/src/lib/services/identificacao-prova.ts` (modificacao ~5 LOC),
  `docs/wave3-v4-c10/contrato-c19.md` (adicionar secao "Customizando mensagens no C19").
- **Risco regressao:** baixo (apenas adiciona export — sem remover/mudar nada).
- **Risco C19:** **resolve risco existente** (C19 nao tinha como customizar mensagens sem reescrever o mapa).
- **Validacao:**
  - Novo teste Vitest verificando `MENSAGENS_ERRO_PADRAO` exportada + chave por `CodigoErro` exhaustiva.
  - Teste do helper `mensagemPara`.
  - `npx vitest run` (esperado: 46 testes — era 44 + 2 novos).

### 3.3 BAIXOS

#### AUD-W3C10-009 — framer-motion: importacao nova
- **Estrategia:** Coberto parcialmente por ADR-135. Apender bloco
  "Nota historica: framer-motion ja estava em package.json desde commit `86b0f9d`
  (Wave 3 v3.0 / C12); este foi o primeiro uso em `/escanear`" em ADR-135 OU em
  apendice do analysis.md §Refinamento Visual R5.
- **Arquivos:** `DECISIONS.md` (ADR-135 — adicionar bloco "Nota historica") OU
  `analysis.md` (decisao final: vai no ADR-135 para manter no lugar canonico).
- **Risco regressao:** zero (doc-only).
- **Risco C19:** nenhum.
- **Validacao:** bloco presente.

#### AUD-W3C10-010 — Audit log sem payload bruto
- **Estrategia:** Adicionar `payload_recebido` (truncado em 64 chars) e
  `codigo_recebido` (manual) em `detalhes` do audit_log. Para evitar polluition
  com dados crus: truncar a 64 chars; nao loggar `payload_recebido` quando
  origem='manual'. Atualizar 1 teste backend que ja valida `detalhes['origem']`
  para incluir `payload_recebido`/`codigo_recebido`.
  ```python
  detalhes={
      "origem": origem_scan,
      "nro_requerimento": prova.nro_requerimento,
      "codigo_publico": prova.codigo_publico,
      # NOVO (AUD-010):
      "payload_recebido": (body.payload or "")[:64] if origem_scan == "camera" else None,
      "codigo_recebido": body.codigo if origem_scan == "manual" else None,
      "status_atual": prova.status.value,
      "transicoes_permitidas": [s.value for s in transicoes_permitidas],
  }
  ```
- **Arquivos:** `backend/app/api/v1/provas.py:1993-1999` (~6 LOC adicionadas),
  `backend/tests/test_provas_api.py:2585+` (atualizar `test_scan_manual_audit_log_origem_manual` para asserir `codigo_recebido`; atualizar `test_scan_audit_log_contem_acao_e_status_atual` para `payload_recebido`).
- **Risco regressao:** baixo. Audit log e additive — schema JSONB aceita campos novos sem migration.
- **Risco C19:** nenhum.
- **Validacao:** testes atualizados passam; `pytest backend/tests/test_provas_api.py::test_scan_manual_audit_log_origem_manual -v` verde.

#### AUD-W3C10-012 — body.codigo max_length=64 vs documentacao prometia 20
- **Estrategia:** Decidir: (A) reduzir Pydantic `max_length=64 -> max_length=20`
  para alinhar com doc, ou (B) atualizar doc para `64`. Decisao: **(A) reduzir
  para 32**. Justificativa: PRV-AAAA-MM-NNNNNN tem 18 chars; `max_length=32` da
  margem para typos do usuario sem inflar superficie. Nao baixar para 20 estrito
  porque (a) chars extras ainda caem no `validar_formato_codigo_publico` retornando
  404 generico (DAT §8.2 preservado), (b) `max_length=20` rejeitaria UI typos via
  422 Pydantic em vez do 404 generico, violando levemente a anti-enumeracao
  ("Pydantic 422 vs handler 404" e o mesmo timing differential do AUD-005, mas
  agora ANTES do DB).
- **Arquivos:** `backend/app/domain/schemas/prova.py:339` (1 LOC: `max_length=32`),
  `analysis.md §5.2` (atualizar nota — `max_length=32`, nao `20`).
- **Risco regressao:** baixissimo (rejeita codigos com mais de 32 chars que sao
  invalidos de qualquer forma).
- **Risco C19:** **C19 deve respeitar `max_length=32` em sua validacao client-side**.
- **Validacao:** novo teste Vitest verificando que 33 chars retorna 422 (caminho
  manual). Atualizar `contrato-c19.md` documentando limite.

#### AUD-W3C10-013 — Teste DB error caminho camera ausente
- **Estrategia:** Adicionar `test_scan_camera_v4_db_error_retorna_502` em
  `test_provas_api.py:2645+`. Espelha `test_scan_manual_db_error_retorna_502`
  mas envia `payload` v4.0 valido + mocka `execute.side_effect = RuntimeError`.
  Tambem adicionar `test_scan_camera_legacy_db_error_retorna_502` para cobrir
  o caminho fallback `nro_requerimento` (4 LOC).
- **Arquivos:** `backend/tests/test_provas_api.py` (~25 LOC adicionadas: 2 testes).
- **Risco regressao:** zero (testes novos).
- **Risco C19:** nenhum.
- **Validacao:** `pytest backend/tests/test_provas_api.py -k "db_error" -v` deve mostrar 4 testes verdes (2 antigos + 2 novos).

#### AUD-W3C10-015 — Bundle cresceu 168 -> 208 kB (doc-only)
- **Estrategia:** Confirmar que ADR-135 ja documenta o crescimento. Apender 1 linha
  no CHANGELOG L184-200 explicitando o bundle First Load (208 kB) como custo aceito
  pelo trade-off de consistencia visual.
- **Arquivos:** `CHANGELOG.md` (1 linha).
- **Risco regressao:** zero.
- **Risco C19:** nenhum.
- **Validacao:** linha presente no CHANGELOG.

#### AUD-W3C10-016 — LOC reportado desatualizado
- **Estrategia:** Atualizar LOC no CHANGELOG L66-80 (ou onde estiver) para refletir
  o estado real pos-iteracoes 3-9:
  - `page.tsx`: 740 (v3.0) -> 414 (iteracao 1) -> **658** (estado final pos-iteracoes 3-9).
  - `escanear.module.css`: 589 (v3.0) -> 433 (iteracao 1) -> **802** (estado final).
- **Arquivos:** `CHANGELOG.md` (~3 LOC).
- **Risco regressao:** zero.
- **Risco C19:** nenhum.
- **Validacao:** numeros conferidos com `wc -l`.

#### AUD-W3C10-018 — eslint-disable sem comentario
- **Estrategia:** Coberto por AUD-004 — depois da correcao da race, as deps do
  `useEffect` ficam completas (`[cameraState]` no lugar de `[cameraState.kind]`),
  e o `eslint-disable-next-line` pode ser **REMOVIDO**. Se permanecer
  alguma justificativa, adicionar comentario `// safe: cancelled flag captures latest closure values`.
- **Arquivos:** `page.tsx:118` (ja contado em AUD-004 — remocao do eslint-disable).
- **Risco regressao:** zero.
- **Risco C19:** nenhum.
- **Validacao:** `npx next build` sem warnings de eslint na linha.

#### AUD-W3C10-019 — Sem secao "Erros conhecidos" no CHANGELOG
- **Estrategia:** Coberto por AUD-002 — secao nova "Pos-auditoria 2026-05-11" no
  CHANGELOG lista todos os achados corrigidos com SHA + ID. Bug AUD-004 fica
  explicito como "Race em handleDetect — RESOLVIDO em AUD-004".
- **Arquivos:** `CHANGELOG.md` (ja contado em AUD-002).
- **Risco regressao:** zero.
- **Risco C19:** nenhum.
- **Validacao:** secao "Pos-auditoria" presente.

### 3.4 INFO

#### AUD-W3C10-001 — figma-reference PNGs ausentes (chancelado)
- **Estrategia:** Registrar status final "RESOLVIDO_POR_DECISAO em commit do Mario
  2026-05-11" no apendice do `audit-report.md`. Nenhuma mudanca de codigo. ja
  documentado em `figma-references.md` placeholder textual.
- **Risco:** zero.
- **Validacao:** apendice escrito.

#### AUD-W3C10-014 — Seq Scan em base de 17 linhas
- **Estrategia:** RESOLVIDO_POR_DESIGN. Documentar em apendice do `audit-report.md`
  como "Comportamento esperado do Postgres planner. Quando `provas_digitais` ultrapassar
  ~100 linhas, planner adotara `idx_provas_codigo_publico` automaticamente."
- **Risco:** zero.
- **Validacao:** apendice escrito.

#### AUD-W3C10-017 — Audit log com transicoes_permitidas que frontend nao consome
- **Estrategia:** RESOLVIDO_POR_DESIGN. Documentar em apendice do `audit-report.md`
  como "Proposital: C11 v4.0 consumira `transicoes_permitidas` do detalhe da prova,
  nao mais do scan response (decisao ADR-132)."
- **Risco:** zero.
- **Validacao:** apendice escrito.

#### AUD-W3C10-021 — useExecutarTransicao orfao
- **Estrategia:** RESOLVIDO_POR_DESIGN. Documentar em apendice do `audit-report.md`
  como "Hook preservado para o C11 v4.0 consumir. Escopo explicitamente protegido
  pela autorizacao do prompt do C10."
- **Risco:** zero.
- **Validacao:** apendice escrito.

#### AUD-W3C10-022 — qrbox fixo 250x250
- **Estrategia:** Corrigir trivial: alterar `qrbox: {width: 250, height: 250}` para
  funcao responsiva: `qrbox: (vw, vh) => { const m = Math.min(vw, vh, 250) - 20; return { width: m, height: m }; }`. Mantem 250 como teto; reduz proporcionalmente em
  viewports menores. Nao toca caminho de teste (apenas afeta UI em runtime do browser).
- **Arquivos:** `frontend/src/hooks/useScanner.ts:116` (5 LOC).
- **Risco regressao:** baixo. html5-qrcode aceita funcao como qrbox; comportamento
  diferente apenas em viewports < 250+20=270px.
- **Risco C19:** nenhum.
- **Validacao:** `npx next build` ok. Validacao runtime depende do smoke (cen.17).

---

## 4. Ordem de execucao (topologica)

Aplicar a ordem rigida: SEVERIDADE -> AFETA_C19/ENUM/LEGACY/FIGMA -> DEPENDENCIAS -> CAMADA_SERVICO_FIRST.

### Justificativa da ordem
1. **AUD-020 primeiro entre ALTOS+MEDIOS** porque afeta C19 (camada de servico — viabilidade do proximo componente). E o unico desta categoria.
2. **AUD-004 segundo** porque e bug real, ALTO, e resolve tambem AUD-018 (eslint-disable). Implementacao localizada com baixo risco.
3. **AUD-011 terceiro** (medio bug em useScanner) — risco regressao medio, mas ainda em codigo critico (vale fazer antes da bateria de docs).
4. **AUD-022 quarto** (info, mas e fix de codigo trivial — ja antes das docs).
5. **AUD-010 quinto** (audit log payload — codigo backend trivial + atualizacao de teste).
6. **AUD-012 sexto** (max_length doc/code alinhamento + teste).
7. **AUD-013 setimo** (testes novos backend — depende de AUD-012 estar estavel).
8. **DOCS em bloco final** — AUD-002, AUD-005, AUD-006, AUD-007, AUD-008, AUD-009, AUD-015, AUD-016, AUD-019. Acumulativos em CHANGELOG/DECISIONS/analysis.md. Tipicamente 1 commit `docs(...)` por tema.
9. **APENDICE NO AUDIT-REPORT** ultimo — AUD-001, 003, 014, 017, 021 (e o resumo de status de TODOS) — registra status final por achado.

### Sequencia exata de commits

```
[1]  AUD-W3C10-020 — feat: export MENSAGENS_ERRO_PADRAO + mensagemPara + testes
[2]  AUD-W3C10-004 — fix: guard race handleDetect + deps completas useEffect (resolve AUD-018)
[3]  AUD-W3C10-011 — fix: useScanner cleanup aguarda stop() antes de re-mount
[4]  AUD-W3C10-022 — fix: qrbox responsivo no useScanner
[5]  AUD-W3C10-010 — feat: audit log do scan grava payload/codigo recebido truncado
[6]  AUD-W3C10-012 — refactor: ScanRequest.codigo max_length 64->32 + alinhamento doc
[7]  AUD-W3C10-013 — test: DB error no caminho camera (v4.0 + legacy fallback)
[8]  AUD-W3C10-002 — docs: ADR-138 (crossfade) + ADR-139 (footer fix) + CHANGELOG
[9]  AUD-W3C10-005 — docs: ADR-140 timing differential 422 vs 404 camera (defesa em profundidade)
[10] AUD-W3C10-006 — docs: ADR-138 detalha a11y prefers-reduced-motion + comportamento durante transicao (consolidado no commit [8])
[11] AUD-W3C10-007 — docs: ADR-139 detalha footer width fix (consolidado no commit [8])
[12] AUD-W3C10-008 — docs: apender R8 + R9 em analysis.md §Refinamento Visual
[13] AUD-W3C10-009 — docs: nota historica framer-motion pre-existente em ADR-135
[14] AUD-W3C10-015 — docs: confirmar bundle 208 kB no CHANGELOG (1 linha)
[15] AUD-W3C10-016 — docs: atualizar LOC reportado no CHANGELOG (page.tsx 658, css 802)
[16] AUD-W3C10-019 — docs: secao "Pos-auditoria" no CHANGELOG (consolidado no commit [8])
[17] AUD-W3C10-001, 003, 014, 017, 021 — docs: apendice de status final no audit-report.md
```

Commits 10, 11, 16 estao **consolidados** no commit 8 (todos sao
modificacoes do mesmo arquivo `CHANGELOG.md` + `DECISIONS.md` adicionando
os mesmos ADRs). Total real: **13 commits atomicos** (5 fix/feat + 1
refactor + 1 test + 6 docs).

---

## 5. Analise de risco agregado

### 5.1 Risco ALTO de regressao

- **Nenhum.** Achado de mais alto risco e AUD-004 (page.tsx race) — risco medio
  por estar em caminho hot. Mitigacao: testes Vitest atualizados + tsc +
  next build + apend ao smoke cen.15.
- AUD-011 (useScanner cleanup) tem risco medio mas mitigado por validacao manual cen.16.

### 5.2 Achados que afetam o C19

- **AUD-W3C10-020 (MEDIO)**: exporta `MENSAGENS_ERRO_PADRAO` + helper `mensagemPara`.
  Validacao especifica: novo teste Vitest verifica exhaustividade do export.
- **AUD-W3C10-012 (BAIXO)**: alinha max_length=32. C19 deve respeitar limite.

### 5.3 Achados de seguranca / anti-enumeracao

- **AUD-W3C10-005 (MEDIO)**: doc-only (ADR-140). Vetor real = 0 confirmado.
- **AUD-W3C10-012 (BAIXO)**: redutor de superficie sem violar 404 generico.

### 5.4 Achados que afetam provas legacy

- **AUD-W3C10-003 (ALTO, parcial)**: cenarios 6 e 9 do smoke-validation cobrem
  prova legacy (`nro_requerimento` direto na manual = 404 generico; camera
  legacy QR cai no fallback). Deferred para humano executar.
- **AUD-W3C10-013 (BAIXO)**: novo `test_scan_camera_legacy_db_error_retorna_502`.

### 5.5 Achados de fidelidade visual contra Figma

- **AUD-W3C10-001 (INFO)**: chancelado, sem acao.
- Nenhum outro.

### 5.6 Achados que tocam codigo de Waves anteriores

- **Nenhum.** Todas as modificacoes ficam no escopo do scanner ou camada de
  servico de identificacao. C06 (Wave 2 v4.0), C08 (Wave 2 v4.0), C12-C14
  (Wave 3 v3.0), Wave 1 v4.0 nao sao tocados.

### 5.7 Achados que exigem nova migration Alembic ou RLS

- **Nenhum.** Audit log JSONB e additive sem migration (campos novos cabem em `detalhes`).

### 5.8 Achados de performance

- **AUD-W3C10-014 (INFO)**: Seq Scan em base de 17 linhas — doc-only.
- **AUD-W3C10-015 (BAIXO)**: bundle 208 kB — doc-only, ADR-135 ja registrou.

### 5.9 Achados de acessibilidade

- **AUD-W3C10-006 (MEDIO)** parcial: ADR-138 deve confirmar `prefers-reduced-motion` no crossfade.
- **AUD-W3C10-022 (INFO)**: qrbox responsivo — melhora UX em viewports pequenos.

### 5.10 Achados bloqueados por divergencia

- **Nenhum.** Estado MCP bate com `audit-report.md` em 100% dos pontos verificados.

---

## 6. Plano de validacao interna pos-correcao (Gate 2 Secao 6.1)

Sera executado no Gate 2, com relatorio em `docs/wave3-v4-c10/fix-validation.md`.

### Checklist objetivo

- [ ] **Backend pytest:** `python -m pytest backend/tests/test_provas_api.py -v` — esperado **827 passed + 9 skipped** (era 825 + 0 novos + 2 novos AUD-013).
- [ ] **Frontend Vitest:** `npx vitest run` — esperado **46 passed** (era 44 + 2 novos AUD-020: export + helper).
- [ ] **TypeScript strict:** `npx tsc --noEmit` — exit 0.
- [ ] **Next build:** `npx next build` — 13/13 paginas.
- [ ] **Camada de servico desacoplada:** confirmar `npx vitest run --environment node src/lib/services` ainda passa todos os 16 + 2 novos testes.
- [ ] **Anti-enumeracao manual path:** `pytest backend/tests/test_provas_api.py -k "formato_invalido" -v` + `-k "fora_do_scope" -v` — mesmas mensagens "Prova nao encontrada" + status 404 + headers `Content-Type` identicos.
- [ ] **Anti-enumeracao via novo ADR-140:** registro publicado.
- [ ] **Provas legacy:** novo teste `test_scan_camera_legacy_db_error_retorna_502` passa.
- [ ] **Audit log com payload_recebido/codigo_recebido:** testes existentes atualizados verdes.
- [ ] **Tratamento dos 5 codigos de erro:** mantido — 16 testes Vitest originais ainda passam.
- [ ] **MCP advisors:** `get_advisors security` + `get_advisors performance` sem novos alertas criticos.
- [ ] **CHANGELOG / DECISIONS / analysis.md / contrato-c19.md:** atualizados conforme plano.
- [ ] **Apendice `audit-report.md`:** status final por achado (22 entradas) escrito.
- [ ] **`fix-validation.md`:** criado com auto-critica + recomendacao de nova auditoria independente.

### Auto-critica (Secao 6.3 do prompt)

A ser preenchida no Gate 2 com evidencia para cada pergunta. Pontos de atencao especificos desta sessao:
- Algum teste backend novo foi feito sob medida? (Verificar — esperado: cobrir DB error real, nao apenas fazer assert do mock).
- AUD-005 documentacao mascarou problema? (Vetor real = 0 e fato verificavel — RLS filtra antes do hash. Sem mudanca de codigo justificada.)
- A correcao do AUD-004 mantem o `cancelled` flag funcional? (Sim — flag impede side-effect duplicado mesmo se 2 effects rodarem com payloads diferentes.)

### Recomendacao final (Secao 6.4)

Sera uma das tres:
- **PR pronto para merge.** (Todas as correcoes aplicadas + smoke pendente deferido para humano.)
- **PR pronto para merge condicional.** (Algumas correcoes deferidas com justificativa explicita.)
- **Sessao precisa ser estendida.** (Algo durante execucao inviavel — incluiria escalada ao Mario.)

Em qualquer caso: recomendar nova rodada de auditoria independente em sessao separada
usando `PROMPT_Auditoria_PosWave3_C10_v4.md` (ou equivalente).

---

## 7. Plano de atualizacao de documentacao

Cada arquivo cresce acumulativamente — **nunca substituir, sempre apender**.

| Arquivo | Acao |
|---|---|
| `CHANGELOG.md` | Apender secao "## v4.0 — Wave 3 — Componente 10 — Correcoes Pos-Auditoria (2026-05-11)" listando 22 achados por ID, sev, SHA, tipo |
| `DECISIONS.md` | Apender ADR-138 (crossfade), ADR-139 (footer fix), ADR-140 (timing differential 422 vs 404 camera) |
| `CLAUDE.md` | Atualizar secao "Identificacao de provas: contrato compartilhado" mencionando `MENSAGENS_ERRO_PADRAO` exportada + `mensagemPara` helper (parte do contrato C19) |
| `docs/wave3-v4-c10/audit-report.md` | Apendice "Status por achado" — 22 linhas, status final + commit SHA (preserva corpo original) |
| `docs/wave3-v4-c10/analysis.md` | Apender R8 + R9 na secao "Refinamento Visual" |
| `docs/wave3-v4-c10/contrato-c19.md` | Adicionar secao "Customizando mensagens no C19" + atualizar limite `max_length=32` do `codigo` |
| `docs/wave3-v4-c10/fix-plan.md` | Apender "Resultado da Execucao" ao final apos Gate 2 |
| `docs/wave3-v4-c10/fix-validation.md` | Criar ao final do Gate 2 |
| `docs/wave3-v4-c10/smoke-validation.md` | NAO modificar agora — Mario preenche em execucao real |

---

## 8. Entregavel deste Gate 1

Arquivo `docs/wave3-v4-c10/fix-plan.md` (este documento). Sera commitado em
`wave3-v4-c10/fixes/plan` com mensagem: `docs(wave3-v4/c10/fixes): plano de correcao pos-auditoria`.

---

**Fim do plano.** Aguardando autorizacao "AUTORIZADO GATE 2 — CORREÇÃO C10 v4.0" do Mario para iniciar a execucao.
