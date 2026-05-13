# Wave 3 (v4.0) · Componente 11 · Análise de Gate 1 (read-only)

**Data:** 2026-05-13
**Branch alvo:** `wave3-v4-c11/analysis` (sai de `development`, sem merge)
**PR de execução:** `wave3-v4/componente-11` (Gate 2) → `development`
**Autor:** Claude (Sonnet/Opus) sob direção de Mario Souza
**Tipo:** Análise read-only. Nenhuma linha de código de produção foi tocada. Nenhuma migration foi aplicada.

---

## 0. Sumário executivo (≤ 22 linhas)

1. **A Matriz de Transições v4.0 está na Seção 5 do `RequisitosProvasDigitais_v4_0.docx`**, decomposta em 4 sub-tabelas (5.2 Matriz, 5.3 Lam. Matriz, 5.4 Filial, 5.5 Lam. Filial) + 5.6 Transversais (Reprovação + Cancelamento). Foi reproduzida literalmente na §6 desta análise.
2. **Contagem oficial de transições** (incluindo "criação inicial" como linha contável conforme critérios de aceitação do Backlog C11): **Matriz 6, Lam. Matriz 11, Filial 4, Lam. Filial 7**. Total não-iniciais: **5 + 10 + 3 + 6 = 24 transições rota-específicas + 2 transversais (Reprovar, Reiniciar Ciclo) + 1 transversal universal (Cancelar)**.
3. **Inventário oficial = 14 estados** (incluindo "Cancelada" transversal). Reproduzido literalmente na §6.1. Diferença em relação aos 9 do prompt-de-usuário: o estado v3.0 real é de **10 valores** (`status_prova_enum` em produção), e o número "9" do prompt parece descrever apenas estados ativos sem CANCELADA.
4. **Coerência texto ↔ UML drawio (abas 06.1-06.4): COERENTE em 3 de 4 rotas**. Uma divergência aparente isolada na Rota Filial (Seção 5.4 do Requisitos vs aba 06.3) — texto nomeia "Vendedor" como ator de "Criada → Encaminhada para o Vendedor"; UML posiciona a ação na coluna 3Studio. Recomendação técnica: aderir ao texto (interpretação semântica do agente: "ator = quem assina ao receber"), mas é decisão para Mario fechar.
5. **3 contextos distintos do Motorista** confirmados literalmente no UML (06.2 + 06.4): ida laminação, volta laminação, entrega final — cada um é um nó (estado) separado.
6. **Backlog C11 v4.0 Notas Técnicas recomendam ALTER TYPE em enum existente** — não criar enum novo, não criar coluna nova. Quero confirmar com Mario porque ainda há 2 alternativas defensáveis.
7. **Estrutura prescrita pelo DAT v3.0 §4.1**: `/domain/state_machine/` com 3 arquivos (`rules.py`, `machine.py`, `enums.py`). Hoje o módulo equivalente vive em `backend/app/services/state_machine.py` (~460 LOC). Proposta no §10 desta análise: criar `backend/app/state_machine/v4/`.
8. **Cobertura mínima 95% na máquina de estados** está mandatória — declarada 3 vezes (DAT §3, §4.2, Backlog C11 critério).
9. **Princípio de invariância**: tabela de transições vive em código Python versionado, NÃO no banco. Trigger PostgreSQL apenas valida defensivamente.
10. **Máquina v3.0 INTOCADA**. Coexistência via roteamento por `rota IS NULL` (legacy) vs preenchida (v4.0). Wave 7 fará o backfill final.
11. **RNF "< 1 segundo para transição" NÃO existe na v4.0.** Os RNFs análogos são RNF-002 (≤ 2s captura → assinatura) e RNF-009 (≤ 3 cliques após identificação).
12. **Riscos críticos**: drift entre matriz canônica e implementação; sincronização Python ↔ TypeScript ↔ PostgreSQL; renomeação de `COM_MOTORISTA` v3.0 que tem 1 contexto vs 3 contextos v4.0; reinicio de ciclo preservando rota (já corrigido em ADR-123).
13. **7 pontos de escalação humana identificados** — listados na §8. Mínimo do prompt era 6.
14. **Validação MCP Supabase**: alembic_version=012, `status_prova_enum` com 10 valores, 17 provas em produção (11 legacy + 6 v4.0), 16 movimentações, advisor de segurança limpo. `status_prova_v4` NÃO existe ainda — confirmado estado de partida.

---

## 1. Confirmação de leitura dos artefatos de contexto

### 1.1 Arquivos vivos do repositório (estado pós-C19 em `development`)

| # | Caminho | Lido | Observação |
|---|---|---|---|
| 1 | [CLAUDE.md](../../CLAUDE.md) | ✅ | Carregado integralmente como contexto do sistema |
| 2 | [DECISIONS.md](../../DECISIONS.md) | ✅ (chunks) | 455 KB — lido via Grep + Read seletivo: ADRs 040, 081, 082, 083, 084, 085, 088, 089, 115-124, 129, 132-145 |
| 3 | [CHANGELOG.md](../../CHANGELOG.md) | ✅ (grep) | Wave 3 v3.0 entries localizadas; Wave 3 v4.0 (C10/C19) entries no CLAUDE.md atual |
| 4 | [docs/db/schema.sql](../db/schema.sql) | ✅ integralmente | Snapshot completo do schema atual (alembic_version=012) |
| 5 | [backend/app/services/state_machine.py](../../backend/app/services/state_machine.py) | ✅ integralmente | 463 LOC, máquina v3.0 + executar_transicao do Lote A + ajustes ADR-119/ADR-123 |
| 6 | [backend/app/db/models.py](../../backend/app/db/models.py) | ✅ integralmente | Modelos ORM: 4 enums (Setor, Localizacao, StatusProva, Rota) + 6 tabelas |
| 7 | [backend/app/api/v1/provas.py](../../backend/app/api/v1/provas.py) | ✅ chunks 1-1500 + 1700-2500 | 2500+ LOC; foco nos endpoints `scan`, `transicoes`, `cancelar`, `reiniciar-ciclo` |
| 8 | [shared/access-matrix.json](../../shared/access-matrix.json) | ✅ integralmente | 12 regras × 4 perfis (Wave 1 v4.0) |
| 9 | [backend/app/services/qrcode_service.py](../../backend/app/services/qrcode_service.py) | ✅ integralmente | Payload format + HMAC |

### 1.2 Documentos canônicos v4.0 (especificação)

Extração delegada a agente `general-purpose` por causa do formato binário `.docx` (zip de OOXML) + tamanho do `.drawio` (~470 KB XML). O extrato literal está em `_agent_extraction.md` neste mesmo diretório (61 KB legíveis em pt-BR, com encoding UTF-8 dos caracteres acentuados parcialmente corrompidos — conteúdo informacionalmente íntegro).

| # | Documento | Local | Estado |
|---|---|---|---|
| 1 | `RequisitosProvasDigitais_v4_0.docx` | `C:\Users\mario.souza\Desktop\Rastreio Prova Digital\` | ✅ Seções 5.1 a 5.6 (Matriz), RF-007 a RF-012, RN-001 a RN-007 + RN-012, US-002 a US-007, Matriz de Acesso §6, RNF-001/002/009 — todos literalmente extraídos |
| 2 | `BACKLOG_RastreioProvasDigitais_v4_0.docx` | mesmo dir | ✅ Componente 11 v4.0 + Componente 12 v4.0 + Definition of Done global Seção 2 |
| 3 | `DAT_RastreioProvasDigitais_v3_0.docx` | mesmo dir | ✅ Seção 2 (Alembic vs Supabase), §3 (Testes), §4 (Máquina de Estados — completo), §7 (RBAC defesa em profundidade) |
| 4 | `UML_RastreioProvasDigitais_v4_0.drawio` | mesmo dir | ✅ Abas 06.1 (Matriz), 06.2 (Lam. Matriz), 06.3 (Filial), 06.4 (Lam. Filial) — nós, edges, atores inferidos por correlação posicional |

### 1.3 Bloqueios críticos verificados

| Bloqueio | Resultado |
|---|---|
| Matriz de Transições do Requisitos v4.0 (§5) ausente/incompleta | **OK — presente e completa.** Divergência única detectada §5.4 vs UML 06.3 (escalada na §8) |
| Timeline do C08 estruturalmente capaz | **OK — confirmado em CLAUDE.md (`apêndice 2 ADR-127`)**. C12 vai consumir mapeamento ainda a ser entregue por esta wave |
| Componentes anteriores (Wave 1, C06, C08, C10, C19) integralmente em `development` | **OK — branch atual confirmado em `development`** com working tree limpo (apenas `.next/`, `docs/wave2-v4/audit-report-round2.md` e este novo diretório `docs/wave3-v4-c11/`) |
| `status_prova_v4` já existe no banco | **NÃO existe — confirmado.** Estado de partida limpo |

---

## 2. Validação de infraestrutura MCP (pré-Gate 1)

### 2.1 Supabase (MCP `supabase` em projeto `rwxlpwmnkekzuurgthkr` — sa-east-1)

**Saúde do projeto:** `ACTIVE_HEALTHY`, Postgres 17.6.1.104.

**Enum `status_prova_enum`** (10 valores, ordem do `enumsortorder`):
```
1. CRIADA                       (estado inicial)
2. RETIRADA_PELO_VENDEDOR
3. APROVADA_PELO_VENDEDOR
4. DE_VOLTA_3STUDIO
5. COM_MOTORISTA                (v3.0: 1 único contexto)
6. ENVIADA_PARA_CLICHERIA       (rota PADRAO via motorista)
7. ENCAMINHADA_A_CLICHERIA      (rota DIRETA do vendedor)
8. RECEBIDA_PELA_CLICHERIA      (terminal sucesso)
9. REPROVADA_PELO_VENDEDOR
10. CANCELADA                   (terminal cancelamento — transversal)
```

**Enum `rota_enum`** (6 valores — Wave 2 v4.0 + legacy v3.0):
```
1. PADRAO       (legacy v3.0)
2. DIRETA       (legacy v3.0)
3. MATRIZ       (v4.0 Wave 2)
4. LAM_MATRIZ   (v4.0 Wave 2)
5. FILIAL       (v4.0 Wave 2)
6. LAM_FILIAL   (v4.0 Wave 2)
```

**Enum `setor_enum`** (4 valores): `STUDIO`, `VENDEDOR`, `MOTORISTA`, `CLICHERIA`.
**Enum `localizacao_enum`** (2 valores): `MATRIZ`, `FILIAL`.

**Distribuição de provas atual** (17 provas em produção):
```
CANCELADA                  7
CRIADA                     6
RECEBIDA_PELA_CLICHERIA    2
REPROVADA_PELO_VENDEDOR    2
─────────────────────────────
TOTAL                     17
```

Por relação legacy/v4.0:
```
rota IS NULL (legacy v3.0)             11
rota IS NOT NULL (v4.0 ou legacy preenchido)    6
total movimentações em todos os ciclos          16
```

Por rota (apenas provas com rota preenchida):
```
PADRAO  + CANCELADA                  2
DIRETA  + RECEBIDA_PELA_CLICHERIA    2
DIRETA  + CANCELADA                  1
MATRIZ  + CRIADA                     1   ← única prova v4.0 ativa
```

**Distinct `status_novo`** já gravados em `movimentacoes`:
```
CRIADA, RETIRADA_PELO_VENDEDOR, APROVADA_PELO_VENDEDOR,
ENCAMINHADA_A_CLICHERIA, RECEBIDA_PELA_CLICHERIA,
REPROVADA_PELO_VENDEDOR, CANCELADA
```

Notar que `COM_MOTORISTA`, `ENVIADA_PARA_CLICHERIA` e `DE_VOLTA_3STUDIO` **nunca foram usados em movimentações reais** — produção saltou direto da rota DIRETA (FILIAL → CLICHERIA) e não tem provas que passaram pelo fluxo via motorista. Isso é relevante para a coexistência: o risco de "regressão na rota PADRAO" é teórico, sem dados reais para validar.

**Trigger `trg_provas_rota_imutavel` (Wave 2 v4.0):** ativo, atual e funcional (resposta vazia ao filtro restritivo, mas o trigger está no schema.sql confirmado).

**Indexes em `movimentacoes`** (relevantes ao C11):
```
movimentacoes_pkey                      (id)
idx_movimentacoes_prova                 (prova_id)                                     [unused — Wave 6 advisor]
idx_movimentacoes_usuario               (usuario_id)                                   [unused]
idx_movimentacoes_prova_ciclo           (prova_id, ciclo)                              [unused]
idx_movimentacoes_created_at            (created_at)                                   [unused]
idx_movimentacoes_prova_data            (prova_id, created_at DESC)                    [usado na Timeline C12 + dashboard]
idx_movimentacoes_status_novo_created_at (status_novo, created_at DESC)                [unused — Wave 5 reports]
```

Índices cobrindo o caminho de inserção da C11 (FOR UPDATE em `provas_digitais.id` + INSERT em `movimentacoes`): adequados. Não vejo necessidade de novo índice para o C11.

**Policies RLS em `provas_digitais` / `movimentacoes` / `etiquetas`** (5 policies relevantes — Wave 1 v4.0 RLS 012 + Wave 3 v3.0 RLS 006):
- `pol_provas_select`: admin OR self vendedor OR motorista quando status=COM_MOTORISTA OR clicheria quando status IN (ENVIADA, ENCAMINHADA, RECEBIDA)
- `pol_provas_insert`: admin only
- `pol_provas_update`: admin only
- `pol_movimentacoes_select`: admin OR vendedor das suas OR autor da movimentação OR motorista (COM_MOTORISTA) OR clicheria (3 clicheria-states)
- `pol_movimentacoes_insert`: admin only
- `pol_etiquetas_select`: admin OR vendedor OR motorista (COM_MOTORISTA) OR clicheria (3 clicheria-states)

**Implicação crítica para C11:** todas as 4 policies que filtram por `status` listam estados **v3.0 literais**. Quando os 5+ novos estados v4.0 forem adicionados ao enum, as policies precisam ser atualizadas para reconhecer:
- Motorista nos 3 contextos: `COM_MOTORISTA_IDA_LAMINACAO`, `COM_MOTORISTA_VOLTA_LAMINACAO`, `COM_MOTORISTA_ENTREGA_FINAL` (nomes propostos, ver §8.2).
- Clicheria nos estados onde a clicheria atua: `ENCAMINHADA_PARA_LAMINACAO` (recebe para laminar), `LAMINACAO_CONCLUIDA` (preparou prova) — coerente com US-007.

**Advisors de segurança** (após Wave 1 v4.0 Audit Round 2):
- INFO: `rls_enabled_no_policy` em `alembic_version` (ADR-025 — intencional)
- WARN: `auth_leaked_password_protection` (ADR-027 — WONTFIX plano pago)

Nenhum novo alerta atribuível a Waves prévias.

**Advisors de performance:** 13 `unused_index` INFOs — todos esperados (indexes cobrindo queries que ainda não rodaram em produção devido ao volume baixo). Não bloqueia a C11.

### 2.2 Cloudflare R2

**Status:** Não inspecionado nesta análise. A C11 é exclusivamente backend + frontend de transição — nenhuma operação em R2. As únicas escritas em R2 acontecem em `create_prova` (criação de prova) e leituras em `imagem-url`, ambas fora do escopo da C11.

**Decisão:** considerar Cloudflare R2 saudável até prova em contrário (ver follow-up M-6 da Wave 1 v4.0 Audit Fixes). Se Gate 2 levantar dúvida, validar via `scripts/smoke_r2.py`.

### 2.3 Bloqueios MCP

| Bloqueio | Resultado |
|---|---|
| `status_prova_v4` já existe no banco | ❌ Não existe — estado limpo (confirma criação inédita) |
| Índice em `prova_id` ausente | ✅ `idx_movimentacoes_prova` presente |
| Provas legacy em estados inesperados | ✅ Nenhuma — todos os status estão dentro do enum atual |
| Schema `app_private` existe (Wave 1 v4.0) | ✅ Presente — helpers SECURITY DEFINER disponíveis para novas policies |

---

## 3. Inventário da máquina de estados v3.0 atual

### 3.1 9 estados ativos + 1 transversal (CANCELADA) = 10 valores no enum

Reproduzido textualmente do `backend/app/db/models.py` linhas 32-47 (StatusProvaEnum) e do `backend/app/services/state_machine.py` linhas 53-95 (TRANSICOES):

```
CRIADA → {RETIRADA_PELO_VENDEDOR, CANCELADA}
RETIRADA_PELO_VENDEDOR → {APROVADA_PELO_VENDEDOR, REPROVADA_PELO_VENDEDOR, CANCELADA}
APROVADA_PELO_VENDEDOR → {DE_VOLTA_3STUDIO, ENCAMINHADA_A_CLICHERIA, CANCELADA}
                          [bifurcação por localização do vendedor: MATRIZ → DE_VOLTA_3STUDIO; FILIAL → ENCAMINHADA_A_CLICHERIA]
DE_VOLTA_3STUDIO → {COM_MOTORISTA, CANCELADA}
COM_MOTORISTA → {ENVIADA_PARA_CLICHERIA, CANCELADA}
ENVIADA_PARA_CLICHERIA → {RECEBIDA_PELA_CLICHERIA, CANCELADA}
ENCAMINHADA_A_CLICHERIA → {RECEBIDA_PELA_CLICHERIA, CANCELADA}
REPROVADA_PELO_VENDEDOR → {CRIADA, CANCELADA}   [reinicio de ciclo + cancelamento]
RECEBIDA_PELA_CLICHERIA → {}                    [terminal sucesso]
CANCELADA → {}                                  [terminal cancelamento]
```

### 3.2 Atores autorizados por transição (ATORES_POR_TRANSICAO)

```python
(CRIADA, RETIRADA_PELO_VENDEDOR): VENDEDOR
(RETIRADA, APROVADA): VENDEDOR
(RETIRADA, REPROVADA): VENDEDOR
(APROVADA, DE_VOLTA_3STUDIO): VENDEDOR (apenas MATRIZ — checado em executar_transicao)
(APROVADA, ENCAMINHADA_A_CLICHERIA): VENDEDOR (apenas FILIAL — checado em executar_transicao)
(DE_VOLTA_3STUDIO, COM_MOTORISTA): STUDIO
(COM_MOTORISTA, ENVIADA_PARA_CLICHERIA): MOTORISTA
(ENVIADA, RECEBIDA): CLICHERIA
(ENCAMINHADA, RECEBIDA): CLICHERIA
(REPROVADA, CRIADA): STUDIO  [reinicio de ciclo — admin-only]
(*, CANCELADA): STUDIO       [cancelamento — admin-only, qualquer estado ativo]
```

### 3.3 Endpoints de transição existentes

```
POST /api/v1/provas/scan                        get_current_user   [todos os perfis]
POST /api/v1/provas/{id}/transicoes              get_current_user   [todos os perfis com setor]
POST /api/v1/provas/{id}/cancelar               access_required("provas.cancel")   [admin only]
POST /api/v1/provas/{id}/reiniciar-ciclo        access_required("provas.restart")   [admin only]
```

### 3.4 Tabela `movimentacoes` — schema atual

```sql
CREATE TABLE movimentacoes (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prova_id           UUID NOT NULL REFERENCES provas_digitais(id),
    usuario_id         UUID NOT NULL REFERENCES usuarios(id),
    status_anterior    status_prova_enum NOT NULL,
    status_novo        status_prova_enum NOT NULL,
    assinatura_digital BYTEA NOT NULL,
    motivo_reprovacao  TEXT,
    ciclo              INTEGER NOT NULL,
    rota_no_momento    rota_enum,           -- Wave 3 Lote A — reflete rota pós-transição
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (status_anterior != status_novo),
    CHECK (ciclo >= 1)
);

-- Trigger imutabilidade BEFORE UPDATE OR DELETE → RAISE EXCEPTION (RNF-005).
```

**Discussão (C11):** este schema é razoável para v4.0 sem mudanças mecânicas. A coluna que pode requerer adição: `contexto_motorista` (se a decisão da §8.5 for "campo dedicado" em vez de "derivado de status_novo"). A favor de NÃO adicionar: o contexto é derivável de `status_novo` (3 estados v4.0 distinguem os 3 contextos). Contra: torna queries de auditoria mais frágeis quanto à nomenclatura. Decisão pendente em §8.

### 3.5 Triggers em `movimentacoes` e `provas_digitais`

- `trg_movimentacoes_imutavel` (BEFORE UPDATE OR DELETE) → RAISE — RNF-005
- `trg_provas_updated_at` (BEFORE UPDATE) → atualiza `updated_at`
- `trg_provas_rota_imutavel` (BEFORE UPDATE WHEN OLD.rota IS DISTINCT FROM NEW.rota) → bloqueia NULL→valor é permitido; valor→outro_valor bloqueado com 22023; valor→NULL bloqueado

### 3.6 Pontos de uso do `executar_transicao` v3.0 no código

| Caminho | Função | Comentário |
|---|---|---|
| `POST /scan` | `_computar_transicoes_permitidas` (chama `validar_transicao` em loop) | C11 vai precisar adaptar para v4.0 — RF-009 v4.0 muda a regra "rota por localização" para "rota imutável da prova" |
| `POST /{id}/transicoes` | `executar_transicao(...)` | Cliente público da máquina — sub-bloco A.4 v3.0 |
| `POST /{id}/cancelar` | `executar_transicao(..., status_novo=CANCELADA)` | Wave 3 Lote C v3.0 — independente de rota |
| `POST /{id}/reiniciar-ciclo` | `executar_transicao(..., status_novo=CRIADA)` | Wave 3 Lote C v3.0 — agora preserva rota (ADR-123) |

**Observação crítica:** o handler `POST /{id}/transicoes` v3.0 usa `Depends(get_current_user)` (sem `access_required` da Wave 1 v4.0 / Matriz). Para a C11 v4.0, isso pode permanecer (a Matriz não tem regra `transicoes.executar` mapeada hoje), mas vale revisar — escalação na §8.

---

## 4. Reprodução literal da Matriz de Transições v4.0

Esta seção replica byte-a-byte a Seção 5 do `RequisitosProvasDigitais_v4_0.docx`. Fonte: extrato do agente em `_agent_extraction.md` §§1.1.1 a 1.1.6.

### 4.1 §5.1 — Inventário Geral de Estados (14 valores)

| # | Estado | Rotas em que aparece |
|---|---|---|
| 01 | Criada | Todas as rotas (estado inicial) |
| 02 | Encaminhada para Laminação | Lam. Matriz, Lam. Filial |
| 03 | Com Motorista (ida laminação) | Lam. Matriz, Lam. Filial |
| 04 | Laminação Concluída | Lam. Matriz, Lam. Filial |
| 05 | Com Motorista (volta laminação) | Lam. Matriz |
| 06 | De volta à 3Studio (pós-laminação) | Lam. Matriz |
| 07 | Retirada pelo Vendedor | Matriz, Lam. Matriz |
| 08 | Encaminhada para o Vendedor | Filial, Lam. Filial |
| 09 | Aprovada pelo Vendedor | Todas as rotas |
| 10 | Reprovada pelo Vendedor | Todas as rotas |
| 11 | De volta à 3Studio | Matriz, Lam. Matriz |
| 12 | Com Motorista (entrega final) | Matriz, Lam. Matriz |
| 13 | Recebida pela Clicheria (terminal) | Todas as rotas |
| 14 | Cancelada (transversal) | Todas — disponível em qualquer estado ativo |

### 4.2 §5.2 — Rota Matriz (6 transições incluindo criação)

| Estado Atual | Ator | Mecanismo | Estado Destino |
|---|---|---|---|
| (início) | 3Studio | Preenchimento do formulário de criação. Rota "Matriz" selecionada. Etiqueta gerada automaticamente. | Criada |
| Criada | Vendedor | Identificar prova → Assinar → Confirmar. | Retirada pelo Vendedor |
| Retirada pelo Vendedor | Vendedor | Identificar prova → Selecionar "Aprovar" → Assinar → Confirmar. | Aprovada pelo Vendedor |
| Aprovada pelo Vendedor | 3Studio | Identificar prova → Assinar → Confirmar recebimento. | De volta à 3Studio |
| De volta à 3Studio | Motorista | Identificar prova → Assinar → Confirmar entrega final. | Com Motorista (entrega final) |
| Com Motorista (entrega final) | Clicheria | Identificar prova → Assinar → Confirmar recebimento. | Recebida pela Clicheria (Concluída) |

### 4.3 §5.3 — Rota Lam. Matriz (11 transições incluindo criação)

| Estado Atual | Ator | Mecanismo | Estado Destino |
|---|---|---|---|
| (início) | 3Studio | Preenchimento do formulário de criação. Rota "Lam. Matriz" selecionada. Etiqueta gerada automaticamente. | Criada |
| Criada | 3Studio | Identificar prova → Assinar → Confirmar encaminhamento para laminação. | Encaminhada para Laminação |
| Encaminhada para Laminação | Motorista | Identificar prova → Assinar → Confirmar travessia (ida laminação). | Com Motorista (ida laminação) |
| Com Motorista (ida laminação) | Clicheria | Identificar prova → Assinar → Confirmar conclusão da laminação. | Laminação Concluída |
| Laminação Concluída | Motorista | Identificar prova → Assinar → Confirmar travessia (volta laminação). | Com Motorista (volta laminação) |
| Com Motorista (volta laminação) | 3Studio | Identificar prova → Assinar → Confirmar recebimento da prova laminada. | De volta à 3Studio (pós-laminação) |
| De volta à 3Studio (pós-laminação) | Vendedor | Identificar prova → Assinar → Confirmar. | Retirada pelo Vendedor |
| Retirada pelo Vendedor | Vendedor | Identificar prova → Selecionar "Aprovar" → Assinar → Confirmar. | Aprovada pelo Vendedor |
| Aprovada pelo Vendedor | 3Studio | Identificar prova → Assinar → Confirmar recebimento. | De volta à 3Studio |
| De volta à 3Studio | Motorista | Identificar prova → Assinar → Confirmar entrega final. | Com Motorista (entrega final) |
| Com Motorista (entrega final) | Clicheria | Identificar prova → Assinar → Confirmar recebimento. | Recebida pela Clicheria (Concluída) |

**⚠️ Ambiguidade nomeada no texto:** o estado #06 (`De volta à 3Studio (pós-laminação)`) e o estado #11 (`De volta à 3Studio`) coexistem nesta rota e têm nomes muito próximos. **Decisão técnica recomendada na implementação:** preservar a distinção via `DE_VOLTA_3STUDIO_POS_LAMINACAO` (estado #06) vs `DE_VOLTA_3STUDIO` (estado #11 — preserva enum value v3.0). Detalhe em §8.2.

### 4.4 §5.4 — Rota Filial (4 transições incluindo criação)

| Estado Atual | Ator | Mecanismo | Estado Destino |
|---|---|---|---|
| (início) | 3Studio | Preenchimento do formulário de criação. Rota "Filial" selecionada. Etiqueta gerada automaticamente. | Criada |
| Criada | **Vendedor** (texto) / 3Studio (UML — divergência) | Identificar prova → Assinar → Confirmar encaminhamento para o vendedor. | Encaminhada para o Vendedor |
| Encaminhada para o Vendedor | Vendedor | Identificar prova → Selecionar "Aprovar" → Assinar → Confirmar. | Aprovada pelo Vendedor |
| Aprovada pelo Vendedor | Clicheria | Identificar prova → Assinar → Confirmar recebimento. | Recebida pela Clicheria (Concluída) |

**⚠️ Divergência aparente nomeada na §5.4 vs UML 06.3:** o ator de `Criada → Encaminhada para o Vendedor` é "Vendedor" no texto, mas o UML posiciona a ação na coluna 3Studio. Escalação obrigatória — §8.1.

### 4.5 §5.5 — Rota Lam. Filial (7 transições incluindo criação)

| Estado Atual | Ator | Mecanismo | Estado Destino |
|---|---|---|---|
| (início) | 3Studio | Preenchimento do formulário de criação. Rota "Lam. Filial" selecionada. Etiqueta gerada automaticamente. | Criada |
| Criada | 3Studio | Identificar prova → Assinar → Confirmar encaminhamento para laminação. | Encaminhada para Laminação |
| Encaminhada para Laminação | Motorista | Identificar prova → Assinar → Confirmar travessia (ida laminação). | Com Motorista (ida laminação) |
| Com Motorista (ida laminação) | Clicheria | Identificar prova → Assinar → Confirmar conclusão da laminação. | Laminação Concluída |
| Laminação Concluída | Vendedor | Identificar prova → Assinar → Confirmar. | Encaminhada para o Vendedor |
| Encaminhada para o Vendedor | Vendedor | Identificar prova → Selecionar "Aprovar" → Assinar → Confirmar. | Aprovada pelo Vendedor |
| Aprovada pelo Vendedor | Clicheria | Identificar prova → Assinar → Confirmar recebimento. | Recebida pela Clicheria (Concluída) |

### 4.6 §5.6 — Transversais (Reprovação + Cancelamento)

| Estado Atual | Ator | Mecanismo | Estado Destino |
|---|---|---|---|
| Retirada pelo Vendedor (Matriz, Lam. Matriz) | Vendedor | Identificar prova → Selecionar "Reprovar" → Informar motivo → Assinar → Confirmar. | Reprovada pelo Vendedor |
| Encaminhada para o Vendedor (Filial, Lam. Filial) | Vendedor | Identificar prova → Selecionar "Reprovar" → Informar motivo → Assinar → Confirmar. | Reprovada pelo Vendedor |
| Reprovada pelo Vendedor | 3Studio | Ação administrativa: "Reiniciar Ciclo". Rota da prova é preservada. Histórico do ciclo anterior é preservado integralmente. | Criada (novo ciclo) |
| Qualquer estado ativo (≠ Cancelada, ≠ Recebida pela Clicheria) | 3Studio | Ação administrativa: "Cancelar Prova". Motivo obrigatório. | Cancelada |

### 4.7 Contagem oficial de transições

| Rota | Não-iniciais | Com criação | Critério aceitação Backlog C11 |
|---|---|---|---|
| Matriz | 5 | 6 | — |
| Lam. Matriz | 10 | **11** | "11 transições" ✓ |
| Filial | 3 | 4 | — |
| Lam. Filial | 6 | **7** | "7 transições" ✓ |
| **Subtotal por rota** | **24** | **28** | |
| Transversais (Reprovar, Reiniciar, Cancelar) | 2 + 1 + 1 = 4 | — | — |
| **TOTAL** | **28 + 4 = 32** | — | — |

Excluindo a criação (que é via formulário, não scan/assinatura), são **24 transições rota-específicas + 4 transversais = 28 transições autenticáveis** que precisam ser cobertas por testes unitários. A "criação inicial" não tem ator com assinatura digital — é a `create_prova` do C06, fora do escopo do C11.

### 4.8 Coerência texto ↔ UML drawio (resumo §5 do extrato do agente)

| Rota | Texto §5 ↔ UML 06.x | Status |
|---|---|---|
| Matriz | §5.2 ↔ 06.1 | ✅ COERENTE |
| Lam. Matriz | §5.3 ↔ 06.2 | ✅ COERENTE (3 contextos de Motorista distintos confirmados) |
| Filial | §5.4 ↔ 06.3 | ⚠️ DIVERGÊNCIA APARENTE na transição `Criada → Encaminhada para o Vendedor` (escalação §8.1) |
| Lam. Filial | §5.5 ↔ 06.4 | ✅ COERENTE |

### 4.9 Confirmação dos 3 contextos diferenciados do Motorista

Todos os 3 contextos aparecem como **nós (estados) separados** no UML, com rótulos de ação distintos:

| Contexto | Rotas em que aparece | Estado destino canônico | Confirmado em |
|---|---|---|---|
| **ida laminação** | Lam. Matriz + Lam. Filial | `Com Motorista (ida laminação)` | UML 06.2 + 06.4 |
| **volta laminação** | Lam. Matriz **apenas** | `Com Motorista (volta laminação)` | UML 06.2 |
| **entrega final** | Matriz + Lam. Matriz | `Com Motorista (entrega final)` | UML 06.1 + 06.2 |

Notar: rota **Lam. Filial NÃO tem motorista no retorno** (Vendedor e Clicheria estão ambos na Filial — vendedor entrega direto à clicheria após aprovação). Coerente com a descrição da §5.5: "Não há Motorista no retorno".

---

## 5. RF, RN, US e RNF relevantes (literais)

Reproduzidos integralmente em `_agent_extraction.md` §§1.2-1.6. Resumo aqui dos itens que impactam diretamente a C11:

### 5.1 Requisitos funcionais (RF)

- **RF-007**: registro automático de responsável, data/hora e novo status. QR Code (ou código textual) é identificador de autenticidade. Transição ocorre apenas após assinatura digital + confirmação explícita.
- **RF-008** [v4.0 ALTERADO]: dois pontos de partida do vendedor — `Retirada pelo Vendedor` (Matriz, Lam. Matriz) **OU** `Encaminhada para o Vendedor` (Filial, Lam. Filial). Vendedor escolhe Aprovar OU Reprovar. Reprovar exige motivo + assinatura.
- **RF-009** [v4.0 ALTERADO]: após reprovação, prova retorna à 3Studio com status `Reprovada pelo Vendedor`. 3Studio pode reiniciar ciclo → `Criada`, **preservando a rota original** (ou cancelar e criar nova com rota diferente).
- **RF-010** [v4.0 ALTERADO]: aprovação transita conforme rota previamente escolhida no momento da criação (Matriz de Transições §5). Rota é imutável após criação.
- **RF-011**: cancelamento em qualquer estado ativo, com motivo + responsável + data/hora.
- **RF-012** [v4.0 ALTERADO]: timeline visual indica estágios percorridos, rota seguida, etapa de laminação quando aplicável, reprovações com motivo, responsável + timestamp. Adaptativa por número de etapas. Esta é a entrega do C12 — **contrato preparatório do C11**.

### 5.2 Regras de negócio (RN)

- **RN-001** [v4.0 ALTERADO]: QR único + código alfanumérico textual impresso na etiqueta.
- **RN-002** [v4.0 ALTERADO]: transições seguem apenas os caminhos da Seção 5 para a rota da prova. Não é permitido pular etapas nem alternar rotas após criação.
- **RN-003**: toda movimentação exige assinatura digital + nome + setor + data + hora.
- **RN-004** [v4.0 ALTERADO]: apenas usuário do setor autorizado pode transicionar. Mapeamento completo na Seção 5.
- **RN-005**: provas canceladas não podem ter status reativado. Histórico preservado.
- **RN-006** [v4.0 ALTERADO]: provas reprovadas só podem ser reiniciadas pelo perfil 3Studio. **Reinício preserva rota** e mantém histórico do ciclo anterior.
- **RN-007** [v4.0 ALTERADO]: **rota é escolhida MANUALMENTE pelo Administrador 3Studio na criação**, entre 4 opções, e é **imutável**. Não há mais derivação automática por localização do vendedor.
- **RN-012** [v4.0 NOVO]: respeitar `prefers-reduced-motion`.

### 5.3 User Stories (US)

US-002 a US-007 (todas listadas no extrato §1.4). Destaques:
- **US-005** [v4.0 NOVO]: Admin encaminha prova de rota laminada para laminação (`Criada → Encaminhada para Laminação`). Apenas Lam. Matriz e Lam. Filial.
- **US-006** [v4.0 NOVO]: Motorista confirma 3 travessias: ida laminação, volta laminação, entrega final.
- **US-007** [v4.0 NOVO]: Clicheria confirma término da laminação (`Com Motorista (ida laminação) → Laminação Concluída`). Próxima transição depende da rota (Lam. Matriz → Motorista volta; Lam. Filial → Vendedor).

### 5.4 Requisitos não-funcionais (RNF)

- **RNF-001**: dashboard + listagem em ≤ 3 segundos com até 30 usuários simultâneos. NÃO se aplica diretamente à C11 (não é dashboard nem listagem).
- **RNF-002** [v4.0 ALTERADO]: leitura QR ou confirmação digitação manual + exibição assinatura em ≤ **2 segundos**. **Substitui a referência "<1 segundo" do prompt do usuário**, que não existe nos requisitos canônicos.
- **RNF-009** [v4.0 ALTERADO]: fluxo identificar → assinar → confirmar em **≤ 3 cliques** após identificação.

### 5.5 Matriz de Acesso §6 (linhas relevantes)

```
Página/Funcionalidade        | 3Studio | Vendedor | Motorista | Clicheria | Observação
Escanear QR Code             |  full   |  full    |  full     |  full     | Validação por identificação
Visualização Prova (detalhe) | full    | parcial  | parcial   | parcial   | Mesmo escopo da listagem
Timeline da Prova            | full    | parcial  | parcial   | parcial   | Embutida no detalhe
Listagem de Provas           | full    | parcial  | parcial   | full      | Clicheria full (Matriz literal)
Reiniciar Ciclo (Reprovação) | full    | negado   | negado    | negado    | Ação admin
Cancelar Prova               | full    | negado   | negado    | negado    | Ação admin
```

Notar: a Matriz literal diz **Clicheria = full** na listagem, mas na produção atual (Wave 1 v4.0) está implementada como **parcial com `status_clicheria`**. Há follow-up `_clicheria_divergence_note` registrado em `shared/access-matrix.json` — esta C11 **não resolve** essa divergência (escopo: máquina de estados, não RBAC).

---

## 6. Plano de implementação backend (PROPOSTO — sujeito a aprovação)

### 6.1 Localização do código da máquina v4.0 (PROPOSTA com 3 opções)

**Opção A — Seguir DAT §4.1 literalmente:** criar `backend/app/state_machine/v4/`:
```
backend/app/state_machine/__init__.py        (re-export do v4 — preferencial após Wave 7)
backend/app/state_machine/v4/__init__.py
backend/app/state_machine/v4/enums.py         (re-uso StatusProvaEnum/RotaEnum dos models.py)
backend/app/state_machine/v4/rules.py         (TRANSITION_RULES + ATORES_POR_TRANSICAO + helpers)
backend/app/state_machine/v4/machine.py       (executar_transicao + validar_transicao + helpers)
```

**Opção B — Manter localização atual:** estender `backend/app/services/state_machine.py` para conter máquina v3.0 (intacta) + máquina v4.0 (nova), com roteador.

**Opção C — Híbrido:** criar `backend/app/services/state_machine_v4.py` ao lado do existente, ambos isolados. Roteador em `state_machine.py` decide qual chamar.

**Recomendação técnica:** Opção A. Justificativa: DAT prescreve estrutura, princípio de invariância separa `rules.py` de `machine.py`, ergonomia de testes (`tests/state_machine/v4/` espelha estrutura). Trade-off: refactor parcial.

**Decisão pendente:** §8.2.

### 6.2 Estrutura do arquivo `rules.py` (esqueleto)

```python
# backend/app/state_machine/v4/rules.py
from dataclasses import dataclass
from typing import FrozenSet, Mapping
from app.db.models import StatusProvaEnum, RotaEnum, SetorEnum

@dataclass(frozen=True)
class Transition:
    """Uma transição válida na máquina v4.0."""
    destino: StatusProvaEnum
    ator: SetorEnum
    motivo_obrigatorio: bool = False  # True apenas para REPROVADA_PELO_VENDEDOR

# Tipo da tabela canônica: (rota, estado_atual) → frozenset de Transition
TRANSITION_RULES: Mapping[
    tuple[RotaEnum, StatusProvaEnum],
    FrozenSet[Transition]
] = {
    # ───── ROTA MATRIZ ─────
    (RotaEnum.MATRIZ, StatusProvaEnum.CRIADA): frozenset({
        Transition(StatusProvaEnum.RETIRADA_PELO_VENDEDOR, SetorEnum.VENDEDOR),
    }),
    (RotaEnum.MATRIZ, StatusProvaEnum.RETIRADA_PELO_VENDEDOR): frozenset({
        Transition(StatusProvaEnum.APROVADA_PELO_VENDEDOR, SetorEnum.VENDEDOR),
        Transition(StatusProvaEnum.REPROVADA_PELO_VENDEDOR, SetorEnum.VENDEDOR, motivo_obrigatorio=True),
    }),
    # ... 4 entradas restantes para Matriz
    # ───── ROTA LAM_MATRIZ ─────
    # ... 11 entradas
    # ───── ROTA FILIAL ─────
    # ... 4 entradas
    # ───── ROTA LAM_FILIAL ─────
    # ... 7 entradas
}

# Transições transversais (não rota-específicas):
#  - REPROVAR (qualquer Retirada/Encaminhada-para-Vendedor → Reprovada): mapeada nas rules acima
#  - REINICIAR_CICLO (Reprovada → Criada): apenas admin, qualquer rota — função `reiniciar_ciclo()`
#  - CANCELAR (qualquer ativo → Cancelada): apenas admin, qualquer rota — função `cancelar()`
```

**Total esperado de entradas em TRANSITION_RULES**: 5 + 10 + 3 + 6 = **24** entradas (rota × estado_origem onde há ≥1 destino válido). As 4 entradas terminais (RECEBIDA_PELA_CLICHERIA, CANCELADA por rota) ficam ausentes (sem saída).

### 6.3 Roteador v3.0 vs v4.0

```python
# backend/app/state_machine/__init__.py
async def executar_transicao(db, *, prova, status_novo, usuario, ...):
    """Roteia para máquina v3.0 ou v4.0 conforme prova.rota."""
    if prova.rota is None:
        # Provas legacy v3.0 — usar comportamento antigo
        from app.services.state_machine import executar_transicao as _v3
        return await _v3(db, prova=prova, status_novo=status_novo, usuario=usuario, ...)
    if prova.rota in (RotaEnum.PADRAO, RotaEnum.DIRETA):
        # Provas legacy v3.0 com rota persistida — também v3.0
        from app.services.state_machine import executar_transicao as _v3
        return await _v3(db, prova=prova, status_novo=status_novo, usuario=usuario, ...)
    # rota in {MATRIZ, LAM_MATRIZ, FILIAL, LAM_FILIAL} → v4.0
    from app.state_machine.v4.machine import executar_transicao as _v4
    return await _v4(db, prova=prova, status_novo=status_novo, usuario=usuario, ...)
```

**Onde o roteador é chamado:** 3 endpoints existentes (`POST /scan` via `_computar_transicoes_permitidas`, `POST /{id}/transicoes`, `POST /{id}/cancelar`, `POST /{id}/reiniciar-ciclo`) — todos passam pelo mesmo ponto de entrada (`executar_transicao`).

**Novos endpoints da v4.0:** 0. **Decisão proposta** (sujeita a §8.3): reutilizar `POST /{id}/transicoes` para os 5 novos estados v4.0 — o handler já é genérico (recebe `status_novo`). O Pydantic `TransicaoRequest` rejeita explicitamente `CANCELADA` e `CRIADA` (ganchos C13/C14); precisaríamos garantir que aceita todos os 5 estados v4.0.

### 6.4 Cancelamento e Reinício na v4.0

Mantém-se os endpoints existentes (`POST /{id}/cancelar` e `POST /{id}/reiniciar-ciclo`) — ambos admin-only via `access_required("provas.cancel"/"provas.restart")`. Sem mudança de contrato HTTP.

**Cancelamento:** `pode_cancelar(status_atual)` precisa reconhecer os 5 novos estados v4.0 como ativos (não-terminais).

**Reinício:** RF-009 v4.0 já está implementado (ADR-123) — preserva rota. Validar com prova v4.0 real.

---

## 7. Plano de migration Alembic (PROPOSTO)

### 7.1 Migração 013 — esqueleto (depende da §8.2)

Assumindo a Opção A da §8.2 (ampliar enum existente — recomendação do Backlog C11):

```python
# backend/migrations/versions/013_expand_status_prova_enum_v4.py
"""Wave 3 v4.0 — Componente 11: expandir status_prova_enum com 5+ valores v4.0"""

def upgrade():
    # ALTER TYPE ... ADD VALUE em transações separadas (limitação Postgres)
    op.execute("ALTER TYPE status_prova_enum ADD VALUE IF NOT EXISTS 'ENCAMINHADA_PARA_LAMINACAO'")
    op.execute("ALTER TYPE status_prova_enum ADD VALUE IF NOT EXISTS 'COM_MOTORISTA_IDA_LAMINACAO'")
    op.execute("ALTER TYPE status_prova_enum ADD VALUE IF NOT EXISTS 'LAMINACAO_CONCLUIDA'")
    op.execute("ALTER TYPE status_prova_enum ADD VALUE IF NOT EXISTS 'COM_MOTORISTA_VOLTA_LAMINACAO'")
    op.execute("ALTER TYPE status_prova_enum ADD VALUE IF NOT EXISTS 'DE_VOLTA_3STUDIO_POS_LAMINACAO'")
    op.execute("ALTER TYPE status_prova_enum ADD VALUE IF NOT EXISTS 'ENCAMINHADA_PARA_O_VENDEDOR'")
    # NOTA: COM_MOTORISTA_ENTREGA_FINAL pode ser:
    #   (a) ALIAS literal de COM_MOTORISTA via rename (rejeitado: muda comportamento legacy)
    #   (b) Novo valor adicionado + view de compatibilidade (proposto)
    op.execute("ALTER TYPE status_prova_enum ADD VALUE IF NOT EXISTS 'COM_MOTORISTA_ENTREGA_FINAL'")
    # Total: 7 novos valores (ver §8.2 alternativa C)

def downgrade():
    # Postgres não suporta DROP VALUE em transação.
    # Downgrade só seria possível com nova table + COPY + DROP TYPE + recreate — destrutivo.
    raise NotImplementedError(
        "Postgres não suporta ALTER TYPE ... DROP VALUE em transação. "
        "Downgrade requer migração manual + COPY de dados."
    )
```

**Aplicação em produção:** seguir o mesmo padrão da migration 012 (3 chunks via MCP `apply_migration` se houver risco de "valor recém-adicionado usado em transição"). Validar com `alembic upgrade head` em dev.

**Trigger defensivo de transições inválidas:** considerar adicionar um trigger `BEFORE UPDATE` em `provas_digitais` que valide se `(rota, OLD.status, NEW.status)` está na tabela canônica. **Trade-off pesado:** o trigger precisaria consultar a tabela `transition_rules` (no banco) ou hard-codar — viola princípio de invariância (DAT §4.2). **Recomendação técnica:** NÃO adicionar trigger desse tipo. RNF-005 já garante imutabilidade do log; a validação do `status_novo` é responsabilidade da camada de aplicação (Python). Escalação §8.4.

### 7.2 Novos índices

Nenhum índice novo necessário. Os 7 índices existentes em `movimentacoes` cobrem o caminho de inserção da C11.

### 7.3 Backfill

Nenhum backfill necessário. Provas legacy continuam intocadas. Wave 7 (Componente 21) fará o backfill da rota e, eventualmente, da semântica COM_MOTORISTA → COM_MOTORISTA_ENTREGA_FINAL nas provas legacy que passaram por motorista.

---

## 8. Pontos de escalação humana (OBRIGATÓRIOS)

**Cláusula pétrea desta sessão:** não decidir unilateralmente nenhum dos pontos abaixo. Aguardar resposta explícita do Mario.

### 8.1 Decisão M-1 — Ambiguidade Filial: ator da transição `Criada → Encaminhada para o Vendedor`

**Contexto:** §5.4 do Requisitos diz textualmente "Vendedor"; UML 06.3 posiciona a ação na coluna 3Studio.

**Opções:**

| Opção | Ator | Argumento técnico |
|---|---|---|
| **A** | **Vendedor** (seguir texto literal) | Texto canônico (Backlog C11 Justificativa: "A Matriz de Transições da v4.0 é a especificação canônica"). Vendedor "recebe" prova e assina ao receber — analogia direta com Matriz onde Vendedor faz `Criada → Retirada`. |
| **B** | **3Studio** (seguir UML 06.3 + analogia com Lam. Filial) | Mesma coluna que `Lam. Filial: 3Studio faz "encaminhamento p/ laminação"`. Mecanismo "Identificar prova → confirmar **encaminhamento para o vendedor**" sugere que quem **encaminha** é a 3Studio. |
| **C** | Vendedor — interpretado como "ator que assina ao receber" | Resolve ambiguidade do verbo: o estado `Encaminhada para o Vendedor` descreve **o resultado** (prova já foi encaminhada e está com vendedor que assinou), não a ação de um terceiro. Compatível com texto e com analogia US-002 v4.0 (vendedor assina ao receber). |

**Recomendação técnica:** Opção A ou C (equivalentes operacionalmente). Discordância do texto canônico carrega risco de drift.

**Pergunta para Mario:** Qual ator?

### 8.2 Decisão M-2 — Estrutura do enum `status_prova_enum`

**Contexto:** Backlog C11 Notas Técnicas recomendam ampliar enum existente. Prompt do usuário cita 3 alternativas. Os 7 novos estados v4.0 propostos:

```
ENCAMINHADA_PARA_LAMINACAO
COM_MOTORISTA_IDA_LAMINACAO
LAMINACAO_CONCLUIDA
COM_MOTORISTA_VOLTA_LAMINACAO
DE_VOLTA_3STUDIO_POS_LAMINACAO
ENCAMINHADA_PARA_O_VENDEDOR
COM_MOTORISTA_ENTREGA_FINAL   (novo — distinguir do COM_MOTORISTA v3.0 que tem 1 só contexto)
```

**Opções:**

| Opção | Estratégia | Prós | Contras |
|---|---|---|---|
| **A** (recomendada pelo Backlog) | `ALTER TYPE status_prova_enum ADD VALUE` — uma coluna `status` para v3.0 + v4.0 | Uma coluna, queries simples, RLS policies se ajustam diretamente. Backlog explicitamente prescreve. | Provas v3.0 ficam expostas a valores do enum que elas não usam. Risco de drift se algum switch v3.0 não atualizar. Recomendação técnica: testes de exhaustividade que validam matchings v3.0. |
| **B** | Coluna nova `status_v4` + `status` v3.0 intocada | Isolamento total v3.0 / v4.0. | Queries de leitura precisam COALESCE. Dashboard, listagem, relatórios precisam tratar coluna dupla. RLS dobra a complexidade. |
| **C** | Enum novo `status_prova_v4_enum` + coluna `status_v4 status_prova_v4_enum NULL` | Isolamento type-safe no Postgres. | Igual B. Pior: 2 enums para o mesmo conceito. |

**Sub-decisão M-2b — Renomear `COM_MOTORISTA` v3.0:**
- (a) Manter `COM_MOTORISTA` no enum (semântica v3.0) + adicionar `COM_MOTORISTA_ENTREGA_FINAL` (semântica v4.0). Provas v4.0 nunca usam o valor antigo. **Risco:** confusão para humano lendo o enum.
- (b) Renomear `COM_MOTORISTA` → `COM_MOTORISTA_ENTREGA_FINAL` no enum (Postgres não suporta direto — exige nova table + COPY ou USAGE da técnica `ADD VALUE/UPDATE/RENAME`). **Risco:** alto na execução.
- (c) Manter `COM_MOTORISTA` mapeado a `COM_MOTORISTA_ENTREGA_FINAL` no v4.0 via alias em código Python. **Risco:** baixo, mas ambíguo no SQL.

**Recomendação técnica:** A + M-2b(a). Justificativa: A é recomendado pelo Backlog; M-2b(a) preserva compatibilidade absoluta com provas legacy v3.0 que já estão em `COM_MOTORISTA`.

**Pergunta para Mario:** Confirma Opção A + M-2b(a)? Ou prefere outra combinação?

### 8.3 Decisão M-3 — Endpoints da v4.0 (novos vs reutilizar `POST /{id}/transicoes`)

**Contexto:** A v4.0 introduz novas transições, mas `POST /{id}/transicoes` v3.0 já é genérico (aceita `status_novo` no body).

**Opções:**

| Opção | Estratégia | Prós | Contras |
|---|---|---|---|
| **A** | Reutilizar endpoint atual — o handler ramifica internamente para máquina v3.0 ou v4.0 conforme `prova.rota` | Zero novo endpoint, contrato HTTP estável. UI já consome via `useExecutarTransicao`. | `TransicaoRequest` precisa aceitar todos os novos valores v4.0 (validar via Pydantic enum). |
| **B** | 1 endpoint dedicado por nova transição (e.g. `POST /{id}/encaminhar-laminacao`, `POST /{id}/confirmar-laminacao`, etc — total 5+) | Self-documenting (OpenAPI). UI tem `useEncaminharLaminacao()` etc. | Multiplicação de handlers similares. Manutenção pior. |
| **C** | 1 endpoint admin dedicado `POST /{id}/encaminhar-laminacao` (apenas o NEW que requer ação admin US-005), demais reutilizam | Compatível com padrão de C13 (cancelar) e C14 (reiniciar) que são admin-only. | Inconsistência: por que só esse é admin dedicado? |

**Recomendação técnica:** Opção A. Justificativa: princípio DRY, contrato HTTP estável, `executar_transicao_prova` em [provas.py:2108](backend/app/api/v1/provas.py:2108) já valida `pode_cancelar` separadamente — fácil adicionar lógica.

**Pergunta para Mario:** Confirma Opção A?

### 8.4 Decisão M-4 — Trigger PostgreSQL de transições inválidas (defesa em profundidade)

**Contexto:** Backlog C11 não exige trigger. DAT §4.2 desencoraja (princípio de invariância). Mas o ADR-082 mostra padrão de defesa em profundidade via RLS — não trigger de validação semântica.

**Opções:**

| Opção | Estratégia | Argumento |
|---|---|---|
| **A** | **Não criar trigger** (estado atual) | DAT prescreve invariância no Python. RLS deny-by-default protege INSERTs por perfil. Backend é única porta legítima de UPDATE. |
| **B** | Trigger que valida `(rota, OLD.status, NEW.status)` contra tabela explicita no banco | Defesa em profundidade total — qualquer UPDATE direto via psql falha. |
| **C** | Trigger que apenas valida que `NEW.status ∈ status_prova_enum` e que `OLD.status ≠ NEW.status` (já tem check constraint) | Validação mínima de integridade — não-semântica. |

**Recomendação técnica:** Opção A. Trigger semântico (B) viola DAT §4.2; opção C já está coberta por check constraint existente.

**Pergunta para Mario:** Confirma Opção A?

### 8.5 Decisão M-5 — Detecção do contexto do Motorista (3 contextos)

**Contexto:** Motorista tem 3 contextos distintos (ida laminação, volta laminação, entrega final), cada um com seu estado v4.0 dedicado.

**Opções:**

| Opção | Estratégia | Prós | Contras |
|---|---|---|---|
| **A** | Contexto **derivado de `status_novo`** em runtime — não persistido em coluna separada | Zero migração. Estados v4.0 distintos já carregam a informação. | Queries de auditoria fazem string matching em `status_novo`. |
| **B** | Coluna nova `movimentacoes.contexto_motorista VARCHAR(30) NULL` — preenchida pelo `executar_transicao` da v4.0 | Auditoria pode filtrar `WHERE contexto_motorista = 'ida_laminacao'` direto. | Migração extra. Redundante com `status_novo`. |
| **C** | `audit_log.detalhes_json` carrega o contexto — sem coluna separada | Já temos `detalhes_json` rico (ADR-081 Decisão 8). | Audit log é separado de movimentacoes. Queries cruzadas precisam JOIN. |

**Recomendação técnica:** Opção A + Opção C (combinadas). Estado v4.0 distinto já é o contexto; `audit_log.detalhes_json` registra contexto extra para investigações.

**Pergunta para Mario:** Confirma A + C?

### 8.6 Decisão M-6 — Payload do endpoint `POST /{id}/transicoes`

**Contexto:** Schema atual (`TransicaoRequest`) tem campos: `status_novo: StatusProvaEnum`, `assinatura_base64: str`, `motivo_reprovacao: str | None`. Para v4.0, precisa-se de algo novo?

**Opções:**

| Opção | Estratégia | Comentário |
|---|---|---|
| **A** | **Manter schema atual** — `executar_transicao` decide se a transição é v3.0 ou v4.0 baseado em `prova.rota` (já carregada) | Zero mudança no contrato HTTP. UI atual não muda. |
| **B** | Adicionar campo opcional `rota_esperada: RotaEnum \| None` para validação extra | Cliente envia `rota_esperada=MATRIZ` → backend valida `prova.rota == rota_esperada` (rejeita 409 se divergiu por race). Defesa em profundidade contra clients desatualizados. |
| **C** | Adicionar campo `version: Literal["v3","v4"] \| None` para forçar máquina específica | Anti-padrão — o cliente não deveria saber qual máquina | usar. |

**Recomendação técnica:** Opção A. Princípio: o backend é a única autoridade sobre a rota da prova; cliente não precisa replicar.

**Pergunta para Mario:** Confirma Opção A?

### 8.7 Decisão M-7 — Mensagens de erro novas (em pt-BR)

**Contexto:** A v4.0 introduz transições novas. Cada erro de transição precisa de mensagem em pt-BR consistente com as atuais.

**Cenários e propostas:**

| Cenário | Mensagem proposta A | Mensagem proposta B | Mensagem proposta C |
|---|---|---|---|
| Transição inválida (rota X não permite origem→destino) | "Transição inválida na rota {rota}: {origem} → {destino} não consta na Matriz da v4.0." | "Esta prova segue a rota {rota}, que não permite a transição {origem} → {destino}." | "Transição {origem} → {destino} não é válida para a rota {rota}." |
| Ator errado para transição válida | "Apenas {atores_permitidos} podem executar essa ação. Seu setor: {setor_atual}." | "Você não tem permissão para esta transição (setor {setor_atual})." | "Setor {setor_atual} não autorizado. Permitidos: {atores_permitidos}." |
| Estado terminal (Recebida/Cancelada) | "Esta prova já está em estado terminal ({status_atual}) e não admite mais transições." | "Prova em {status_atual} é estado final." | "Estado {status_atual} não tem transições subsequentes." |
| Reinício rejeitado em estado errado | (já existe — preservar v3.0) | — | — |
| Cancelamento em terminal | (já existe — preservar v3.0) | — | — |

**Recomendação técnica:** propor B para todas (mais conciso, voz ativa).

**Pergunta para Mario:** Qual conjunto? B?

### 8.8 Decisão M-8 — Idempotência / rate limiting / retries em transições

**Contexto:** Sem rate limit hoje no `POST /{id}/transicoes`. C19 já registrou follow-up de rate limit em `/scan` (ADR-145).

**Opções:**

| Opção | Estratégia | Trade-off |
|---|---|---|
| **A** | Manter sem rate limit nesta wave | FOR UPDATE já serializa via Postgres lock. Race entre 2 usuários gera 409 Conflict (UX boa). |
| **B** | Adicionar rate limit por usuário (e.g. 30/min) via `slowapi` | Defesa contra cliente em loop. Coerente com ADR-145 follow-up. |
| **C** | Adicionar idempotency key opcional no header (`Idempotency-Key`) | Permite cliente retentar safely sem duplicar movimentação. |

**Recomendação técnica:** Opção A para esta wave. ADR-145 já registrou rate limit como follow-up para `/scan` antes do PR para `main` — alinhar com C11 nessa mesma sessão de follow-up faz sentido. Trade-off: defesa em profundidade não está ainda no produto.

**Pergunta para Mario:** Confirma A (sem rate limit nesta wave, follow-up depois)?

---

## 9. Plano de migrations RLS (PROPOSTO — depende de §8.2)

### 9.1 Atualização das policies em `provas_digitais` (motorista + clicheria)

Assumindo Opção A da §8.2 (ampliar enum), as policies que filtram por status precisam ser atualizadas:

**`pol_provas_select` — atual:**
```sql
USING (
  app_private.current_user_is_admin()
  OR (vendedor_id = app_private.current_user_id())
  OR ((status = 'COM_MOTORISTA') AND (current_user_setor() = 'MOTORISTA'))
  OR ((status IN ('ENVIADA_PARA_CLICHERIA', 'ENCAMINHADA_A_CLICHERIA', 'RECEBIDA_PELA_CLICHERIA'))
       AND (current_user_setor() = 'CLICHERIA'))
)
```

**`pol_provas_select` — proposta v4.0:**
```sql
USING (
  app_private.current_user_is_admin()
  OR (vendedor_id = app_private.current_user_id())
  OR (
    current_user_setor() = 'MOTORISTA'
    AND status IN (
      'COM_MOTORISTA',                       -- legacy v3.0
      'COM_MOTORISTA_IDA_LAMINACAO',         -- v4.0
      'COM_MOTORISTA_VOLTA_LAMINACAO',       -- v4.0
      'COM_MOTORISTA_ENTREGA_FINAL'          -- v4.0
    )
  )
  OR (
    current_user_setor() = 'CLICHERIA'
    AND status IN (
      'ENVIADA_PARA_CLICHERIA',              -- legacy v3.0
      'ENCAMINHADA_A_CLICHERIA',             -- legacy v3.0
      'RECEBIDA_PELA_CLICHERIA',             -- terminal
      'ENCAMINHADA_PARA_LAMINACAO',          -- v4.0 — Clicheria recebe para laminar (US-007)
      'COM_MOTORISTA_IDA_LAMINACAO'          -- v4.0 — Clicheria pode ver para confirmar
    )
  )
)
```

**Discussão crítica:** o estado `LAMINACAO_CONCLUIDA` deve ser visível à Clicheria? Tecnicamente, a Clicheria preparou a prova; depois o Motorista (Lam. Matriz) ou Vendedor (Lam. Filial) pega. Decisão SQL: incluir `LAMINACAO_CONCLUIDA` no scoping da Clicheria para que ela continue vendo até ser pega? Recomendação técnica: SIM.

### 9.2 Atualização de `pol_movimentacoes_select` e `pol_etiquetas_select`

Mesmo padrão — atualizar listas de status que motorista/clicheria veem. Migration RLS `014_expand_visibility_v4.sql`.

### 9.3 Aplicação coordenada

Migration Alembic 013 (enum) + migration RLS 014 (policies) devem ser aplicadas no mesmo PR. Apply order: 013 primeiro (cria valores) → 014 (referencia valores).

---

## 10. Plano de integração com a página de detalhe (C08)

### 10.1 Mapeamento dos 7 novos estados em `frontend/src/lib/types/prova.ts`

Adicionar 7 entradas em `StatusProva`, `STATUS_LABELS`, `STATUS_LABELS_SHORT`, `STATUS_OPTIONS`:

```typescript
export type StatusProva =
  | "CRIADA"
  | "RETIRADA_PELO_VENDEDOR"
  | "APROVADA_PELO_VENDEDOR"
  | "DE_VOLTA_3STUDIO"
  | "COM_MOTORISTA"                              // legacy v3.0
  | "ENVIADA_PARA_CLICHERIA"                     // legacy v3.0
  | "ENCAMINHADA_A_CLICHERIA"                    // legacy v3.0
  | "RECEBIDA_PELA_CLICHERIA"
  | "REPROVADA_PELO_VENDEDOR"
  | "CANCELADA"
  // v4.0 (Wave 3 C11)
  | "ENCAMINHADA_PARA_LAMINACAO"
  | "COM_MOTORISTA_IDA_LAMINACAO"
  | "LAMINACAO_CONCLUIDA"
  | "COM_MOTORISTA_VOLTA_LAMINACAO"
  | "DE_VOLTA_3STUDIO_POS_LAMINACAO"
  | "ENCAMINHADA_PARA_O_VENDEDOR"
  | "COM_MOTORISTA_ENTREGA_FINAL";

export const STATUS_LABELS: Record<StatusProva, string> = {
  // ... 10 existentes
  ENCAMINHADA_PARA_LAMINACAO: "Encaminhada para Laminação",
  COM_MOTORISTA_IDA_LAMINACAO: "Com Motorista (ida laminação)",
  LAMINACAO_CONCLUIDA: "Laminação Concluída",
  COM_MOTORISTA_VOLTA_LAMINACAO: "Com Motorista (volta laminação)",
  DE_VOLTA_3STUDIO_POS_LAMINACAO: "De volta à 3Studio (pós-laminação)",
  ENCAMINHADA_PARA_O_VENDEDOR: "Encaminhada para o Vendedor",
  COM_MOTORISTA_ENTREGA_FINAL: "Com Motorista (entrega final)",
};

export const STATUS_LABELS_SHORT: Record<StatusProva, string> = {
  // ... idem (versões curtas para tabela de listagem)
};
```

### 10.2 Botões de transição em `AdminActions.tsx` (e/ou novo componente)

Para a v4.0, o detalhe da prova precisa exibir condicionalmente os botões de transição conforme `(rota, status, perfil)`. Não é admin-only — vendedor/motorista/clicheria também transitam. **Decisão técnica:** criar novo componente `<TransitionActions />` separado do `<AdminActions />` que continua dedicado a cancelar/reiniciar.

Reuso de padrão visual: botões side-by-side com `flex: 1 1 220px` (mesmo padrão de [detalhe.module.css](frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css)).

### 10.3 Sem touch visual no design

Esta wave **NÃO reformula visualmente** a página de detalhe. Apenas adiciona:
- 7 entradas no mapeamento
- 1 componente `<TransitionActions />` que reusa estilo de `<AdminActions />`

A Timeline (C08) já é estruturalmente capaz — não exige refactor.

---

## 11. Plano de contrato para o C12

### 11.1 Documento a entregar: `docs/wave3-v4-c11/contrato-c12.md`

Estrutura proposta (criar na sessão de Gate 2):

```markdown
# Contrato para C12 — Timeline Visual com 4 Rotas e Laminação

## 1. Mapeamento de estados → metadata visual

Localização: `frontend/src/lib/types/prova.ts`
- `STATUS_LABELS[status]`: nome completo
- `STATUS_LABELS_SHORT[status]`: nome curto
- (novo na C12) `STATUS_TIMELINE_META[status]`: { cor, ícone, fase ("inicial"/"laminação"/"vendedor"/"entrega"/"terminal") }

## 2. Helpers de detecção de contexto do Motorista

```typescript
type ContextoMotorista = "ida_laminacao" | "volta_laminacao" | "entrega_final";

export function contextoMotorista(status: StatusProva): ContextoMotorista | null {
  if (status === "COM_MOTORISTA_IDA_LAMINACAO") return "ida_laminacao";
  if (status === "COM_MOTORISTA_VOLTA_LAMINACAO") return "volta_laminacao";
  if (status === "COM_MOTORISTA_ENTREGA_FINAL") return "entrega_final";
  if (status === "COM_MOTORISTA") return "entrega_final";  // legacy v3.0
  return null;
}
```

## 3. Sequência canônica de etapas por rota

`ROTA_ETAPAS[rota]: StatusProva[]` — sequência ordenada de estados pelos quais a prova passa em cada rota. Usado pela timeline para renderizar adaptativamente (rota Filial: 4 etapas; rota Lam. Matriz: 11 etapas).

## 4. Exemplos de consumo

[código real para C12 implementar]
```

---

## 12. Estratégia de testes (95% mínimo na máquina v4.0)

### 12.1 Camada 1 — Unitários (`backend/tests/state_machine/v4/`)

**Cobertura mínima da máquina v4.0:** ≥ 95% (DAT §3, §4.2, Backlog C11).

**Casos esperados:**

| # testes | Cenário | Comentário |
|---|---|---|
| **24** | Para cada `(rota, estado_origem)` da `TRANSITION_RULES`, testar que cada destino aceita o ator correto e rejeita outros | 24 entradas × variantes = ~80 testes |
| **N** | Para cada `(rota, estado_origem, destino_que_NÃO está na lista)`, testar `TransicaoInvalidaError` | combinatória — limitar a casos representativos |
| **4** | Cancelamento em cada um dos 5+ estados novos da v4.0 (US-005 a US-007 contextos ativos) | |
| **4** | Reinício de ciclo em provas das 4 rotas (preserva rota — RF-009 v4.0) | |
| **8** | 3 contextos de motorista × ordenação correta | |
| **6** | Coexistência v3.0 / v4.0: prova `rota IS NULL` continua usando v3.0; prova `rota = MATRIZ/...` usa v4.0; tentativas inválidas | |
| **6** | RLS scoping por (estado, perfil, rota) | integração com banco real |
| **4** | E2E (Playwright) — fluxo completo das 4 rotas | |
| **1** | E2E — prova legacy v3.0 completa ciclo | validar coexistência |
| **2** | Performance — cada transição em < 1s (NÃO existe na v4.0, mas razoável manter via RNF-002) | |

**Estimativa total: 90-120 testes novos.** Atual: 825 testes backend (CLAUDE.md) → após C11: ~925-945.

### 12.2 Test de drift Python ↔ TypeScript ↔ PostgreSQL

Criar `backend/tests/test_status_prova_enum_drift_v4.py` — espelha o que existe para `rota_enum`:

```python
def test_status_prova_enum_python_vs_postgres():
    """Confronta StatusProvaEnum Python com pg_enum no banco."""
    python_values = {v.value for v in StatusProvaEnum}
    db_values = set(execute_sql_sync(
        "SELECT enumlabel FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid "
        "WHERE typname = 'status_prova_enum'"
    ))
    assert python_values == db_values

def test_status_prova_enum_python_vs_typescript():
    """Confronta StatusProvaEnum Python com lib/types/prova.ts."""
    # parse TS file via regex; comparar
```

### 12.3 Cobertura de RBAC v4.0

Já existe `scripts/verify_rbac_equivalence.py` (Wave 1 v4.0). Adicionar verificação para os 7 novos estados.

---

## 13. Riscos e pontos de atenção

| # | Risco | Severidade | Mitigação |
|---|---|---|---|
| **R1** | Quebra da máquina v3.0 (legacy) por roteamento incorreto | CRITICAL | Testes explícitos de coexistência + E2E ciclo completo de prova legacy + 11 provas v3.0 reais em produção |
| **R2** | Drift entre matriz canônica e código | HIGH | `rules.py` como single source of truth + teste de equivalência contra a Matriz textual (parser do Markdown extraído ou JSON espelho do Backlog) |
| **R3** | Sincronização Python ↔ TS ↔ Postgres do enum | HIGH | Teste de drift por camada (§12.2) |
| **R4** | Renomeação `COM_MOTORISTA` v3.0 quebra dados legacy | HIGH | M-2b(a) — manter valor legacy + adicionar `COM_MOTORISTA_ENTREGA_FINAL` |
| **R5** | RLS policies não cobrem novos estados (motorista/clicheria perdem acesso) | HIGH | Migration RLS 014 obrigatória no mesmo PR |
| **R6** | Reinício de ciclo na coexistência (RF-009 v4.0 preserva rota; v3.0 também via ADR-123) | MEDIUM | Já corrigido (ADR-123). Testar 4 cenários: 2 v4.0 + 2 legacy |
| **R7** | Cancelamento transversal em qualquer estado ativo, ambas as máquinas | MEDIUM | `pode_cancelar(status)` reconhece os 7 novos estados |
| **R8** | Performance do FOR UPDATE com mais estados | LOW | Index `idx_movimentacoes_prova` já presente. Lock fino com `of=ProvaDigital` (já implementado ADR-084 Decisão 2) |
| **R9** | Concorrência entre 2 usuários transitionando mesma prova | LOW | Já mitigado por FOR UPDATE + 409 Conflict (ADR-084 Decisão 3) |
| **R10** | Anti-enumeração quebrada por novos estados expor scoping | LOW | RLS impede SELECT direto; mensagens 404 genéricas; auditoria registra mesmo |
| **R11** | Cobertura de testes < 95% | MEDIUM | pytest-cov com fail_under=95 em `app/state_machine/v4/*` |
| **R12** | RNF-002 (≤ 2s) violado por nova lógica de validação | LOW | Tabela em memória + lookup O(1). Validar com benchmark Playwright |
| **R13** | UI mostra botão para transição que backend rejeita (`/scan` retorna lista atualizada, mas usuário recarrega tarde) | LOW | 409 Conflict já trata. Mensagem "Status mudou. Recarregue." (ADR-084 Decisão 3) |
| **R14** | Wave 7 fica inviável por mudança incompatível | CRITICAL | Wave 7 (Componente 21) faz backfill `rota NULL → valor` — trigger `trg_provas_rota_imutavel` permite. Já validado ADR-117. C11 NÃO deve adicionar trigger semântico de status (M-4 Opção A) |

---

## 14. Decisões já fixadas pelo CLAUDE.md / ADRs anteriores (NÃO escalar)

Para evitar re-discutir o que já foi decidido:

| Decisão | Onde foi decidido | Comportamento esperado |
|---|---|---|
| Reinício de ciclo preserva rota | ADR-123 (Wave 2 v4.0 Audit Fixes) | `executar_transicao` v3.0 e v4.0 ambos preservam `rota_antes` em reinício |
| Trigger imutabilidade da rota permite NULL→valor | ADR-117 (Wave 2 v4.0) | Wave 7 backfill funcionará. C11 NÃO deve mexer no trigger |
| Enum em UPPERCASE | ADR-115 (Wave 2 v4.0) | Novos valores: UPPERCASE com underscores |
| `codigo_publico` é coluna separada de `qr_code_hash` | ADR-116 (Wave 2 v4.0) | C11 NÃO toca em codigo_publico nem em qr_code_hash |
| Camada de serviço desacoplada de DOM | ADR-133 (Wave 3 v4.0 / C10) | C11 NÃO acopla com `html5-qrcode`. Frontend de detalhe consome `useExecutarTransicao` (já desacoplado) |
| Anti-enumeração via 404 unificado | ADR-049 + DAT §8.2 | C11 mantém mensagens 404 genéricas |
| Endpoint de transição usa FOR UPDATE | ADR-084 | C11 NÃO muda — mantém |
| 409 Conflict para race | ADR-084 Decisão 3 | C11 mantém |
| Audit log detalhes_json com `de/para/ciclo/rota_antes/rota_depois` | ADR-081 Decisão 8 | C11 pode adicionar `contexto_motorista` opcional |

---

## 15. Resumo de itens NÃO entregues por esta sessão (hard boundary)

**Reafirma escopo do prompt:**

- ❌ Não migra dados de provas legacy v3.0 (Wave 7)
- ❌ Não torna `rota` NOT NULL (Wave 7)
- ❌ Não remove máquina v3.0 (Wave 7)
- ❌ Não reformula visualmente a página de detalhe (apenas adiciona botões + mapeamento)
- ❌ Não reformula a Timeline (C12)
- ❌ Não muda C06 (criação), C08 (detalhe), C10 (scanner), C19 (manual)
- ❌ Não muda RBAC (Wave 1) — apenas adiciona policies RLS para novos estados
- ❌ Não introduz Framer Motion novo (Wave 6 reservada)
- ❌ Não implementa dashboard/relatórios para novos estados (Wave 4 v4.0 futura)
- ❌ Não executa backfill ou drop de valores legacy do enum

---

## 16. Próximos passos (post-Gate 1)

Após receber resposta dos 8 pontos de escalação (§8) e a string `AUTORIZADO GATE 2 — WAVE 3 v4.0 / C11`, iniciar Gate 2 conforme ordem do prompt:

1. Migration Alembic 013 (enum extension)
2. Sincronização de enums em Python, TS, Postgres
3. Módulo `backend/app/state_machine/v4/` com rules.py + machine.py
4. Testes unitários (≥ 95%)
5. Roteador v3.0 vs v4.0 nos endpoints existentes
6. Migrations RLS 014 (visibilidade por novos estados)
7. (Opcional, dependendo de M-4) Trigger PostgreSQL — NÃO recomendado
8. Frontend: mapeamento dos 7 novos estados + componente `<TransitionActions />`
9. E2E Playwright: 4 fluxos + 1 ciclo legacy
10. Validação de performance
11. `contrato-c12.md` (criar)
12. Atualizações: CHANGELOG.md, DECISIONS.md, CLAUDE.md, este analysis.md (§Execução)
13. PR `wave3-v4/componente-11` → `development`

---

## Apêndice A — Tabela de mudanças em endpoints existentes (resumo)

| Endpoint | Wave/Status | Mudança esperada na C11 |
|---|---|---|
| `POST /api/v1/provas/upload-url` | C06 v3.0 + v4.0 | nenhuma |
| `POST /api/v1/provas/` | C06 v4.0 (rota persistida) | nenhuma |
| `GET /api/v1/provas/` | C07 v3.0 | nenhuma (já filtra por rota) |
| `GET /api/v1/provas/{id}` | C08 v3.0 + v4.0 | nenhuma |
| `GET /api/v1/provas/{id}/imagem-url` | C08 v3.0 | nenhuma |
| `GET /api/v1/provas/{id}/movimentacoes` | C08 v3.0 | nenhuma (Timeline já é orientada a dados) |
| `GET /api/v1/provas/{id}/etiqueta.pdf` | C08 v3.0 | nenhuma |
| `GET /api/v1/provas/{id}/qr-code.png` | C08 v3.0 | nenhuma |
| `POST /api/v1/provas/scan` | C10 v4.0 | atualizar `_computar_transicoes_permitidas` para a máquina v4.0 quando `prova.rota` está preenchida com valor v4.0 |
| `POST /api/v1/provas/{id}/transicoes` | C11 v3.0 | roteamento interno v3.0/v4.0; aceitar 7 novos valores no `TransicaoRequest.status_novo` (Pydantic enum sincronizado) |
| `POST /api/v1/provas/{id}/cancelar` | C13 v3.0 | atualizar `pode_cancelar` para reconhecer 7 novos como ativos |
| `POST /api/v1/provas/{id}/reiniciar-ciclo` | C14 v3.0 (ADR-123 v4.0) | nenhuma direta (já preserva rota) |
| `GET /api/v1/provas/dashboard` | C15 v3.0 (Wave 4) | **fora do escopo C11** — Wave 4 v4.0 futura precisará atualizar contadores |
| `GET /api/v1/reports` | Wave 5 v3.0 | **fora do escopo C11** — Wave 5 v4.0 futura |
| `GET /api/v1/audit-log` | C18 v3.0 | nenhuma |
| `GET /api/v1/configuracoes` | C09 v3.0 | nenhuma |

**Total: 3 endpoints modificados pela C11** (`/scan`, `/transicoes`, `/cancelar`), 0 endpoints novos.

---

## Apêndice B — Conferência de bloqueios MCP

| Bloqueio | Estado | Comentário |
|---|---|---|
| `status_prova_v4` já existe no banco | ❌ Não existe | Confirmado por `SELECT typname FROM pg_type WHERE typname='status_prova_v4'` |
| Índice `idx_movimentacoes_prova` ausente | ✅ Presente | Validado em §2.1 |
| Provas legacy em estados inesperados | ✅ Nenhuma | `SELECT DISTINCT status` retornou apenas os 10 valores oficiais |
| Esquema `app_private` ausente | ✅ Presente | Wave 1 v4.0 RLS 012 |
| Trigger `trg_provas_rota_imutavel` ausente | ✅ Presente | Schema.sql + ADR-117 |
| Componentes anteriores parcialmente em `development` | ✅ Tudo em `development` | `git status` limpo (apenas `.next/`, `docs/wave2-v4/audit-report-round2.md`, `docs/wave3-v4-c11/` novos) |

---

**Fim do Gate 1. Aguardando decisões humanas sobre os 8 pontos de escalação listados em §8 + string `AUTORIZADO GATE 2 — WAVE 3 v4.0 / C11` antes de prosseguir.**
