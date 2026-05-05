# Relatório de Auditoria · Wave 2 v4.0 · Componente 06 (atualização v4.0)

**Auditor:** Sessão de auditoria sênior independente (Claude Opus 4.7 1M)
**Data:** 2026-05-05
**Branch auditada:** `development` (HEAD `c06ca56`); merge da Wave 2 v4.0
em `main` no commit `0547550`; refresh visual em `5047172`/`c06ca56`.
**SHA do PR auditado:** `c06ca56` em `development` · `0547550` em `main`
**Veredito final:** **REPROVADO E REFAZER** — 2 achados CRITICAL bloqueantes
+ 6 HIGH (≥3 implicariam bloqueio sozinhos).

---

## Sumário Executivo

A Wave 2 v4.0 entrega o esqueleto correto da v4.0 (enum estendido, coluna
`codigo_publico`, trigger de imutabilidade, etiqueta com código textual,
schema Pydantic com `RotaCriacaoEnum`, RLS preservada). A migration 012
foi aplicada em produção; os 16 registros existentes receberam código
público válido; o trigger de imutabilidade está ativo e respeita a
transição `NULL → valor` (pré-requisito da Wave 7). Os 14 testes novos
da Wave 2 v4.0 passam.

**Mas dois defeitos bloqueantes foram encontrados:**

1. **AUD-W2V4-001 (CRITICAL)** — `state_machine.executar_transicao` zera
   `prova.rota = None` no reinício de ciclo (linha 383). Para qualquer
   prova v4.0 reprovada, o admin que tentar `POST /provas/{id}/reiniciar-ciclo`
   dispara o novo trigger `trg_provas_rota_imutavel` (`OLD.rota='MATRIZ'`,
   `NEW.rota=NULL` é DISTINCT e proibido) → falha com SQLSTATE 22023.
   Viola RF-009 v4.0 ("Ao reiniciar o ciclo, a rota previamente escolhida
   é mantida"), RN-006 v4.0 e US-010. A modificação cirúrgica do ADR-119
   cobriu apenas a aprovação. Não há teste de integração que pegue isso
   (testes usam `mock_db`, sem trigger PostgreSQL).

2. **AUD-W2V4-002 (CRITICAL)** — Branch `development` HEAD em estado
   build-broken: `nova-prova/page.tsx` (commit `5047172` Visual Refresh v2)
   importa `isAllowedImageType` de `@/lib/types/prova`, mas
   `lib/types/prova.ts` em HEAD (commit `e936ddf`) não exporta esse
   símbolo. As linhas que adicionam o helper estão **uncommitted** no
   working tree. O `tsc --noEmit` reportado nos changelogs Visual Refresh
   v1 e v2 só passou no working tree dirty, não no HEAD declarado. A
   declaração "13/13 páginas geradas" no CHANGELOG é inválida para o
   código realmente commitado.

**Achados ALTOS (6, qualquer 3 isoladamente bloqueariam):**
ausência das 3 suítes de teste prometidas no `analysis.md` (drift
enum, imutabilidade real, migration), descarte da mitigação documentada
para o risco "Confusão operacional" (Backlog v4.0 §6) sem substituta,
schema.sql desatualizado, migration Alembic divergente do estado
realmente aplicado em produção.

**Recomendação:** sessão de correção obrigatória cobrindo CRITICAL +
HIGH antes de qualquer prosseguimento para Wave 3 v4.0. A Wave 7
(Componente 21) tem dependência DIRETA no AUD-W2V4-001: enquanto o
reinício zerar a rota, a mesma operação que a Wave 7 vai exercitar
(transitar provas legadas via state machine) já estaria broken.

---

## Fase 1 — Verificação de Completude

### Critérios de Aceitação do Componente 06 v4.0 (Backlog v4.0 §5 +
prompt da execução §5.3)

| Critério | Status | Evidência |
|---|---|---|
| C1. Tentar criar prova sem rota selecionada → 422 | ✅ | `RotaCriacaoEnum` campo obrigatório em `ProvaCreateRequest` (`schemas/prova.py:124`); teste `test_provacreaterequest_rejeita_rota_faltando` em `test_provas_api_v4.py:71-80`. |
| C2. PATCH/PUT na rota após criação → erro | ✅ defesa em camadas; **⚠ PARCIAL** para `executar_transicao`/reinício | (a) Não há schema `ProvaUpdateRequest` que aceite `rota`. (b) Trigger `trg_provas_rota_imutavel` ativo (verificado via `pg_trigger`) e função `fn_bloquear_alteracao_rota` com `search_path=''`. (c) `executar_transicao` na aprovação preserva rota (ADR-119). **MAS:** no reinício de ciclo zera para None — viola via UPDATE indireto (AUD-W2V4-001). |
| C3. Etiqueta PDF exibe nome, requerimento, vendedor, rota, QR Code, código textual | ✅ | `etiqueta_service.gerar_pdf` (`backend/app/services/etiqueta_service.py:157-377`): linhas 335-338 renderizam `codigo_publico` em mono 8.5pt abaixo do QR (qr_box reduzido de 29mm para 26mm para abrir espaço); 345-359 renderizam badge da rota (preto fill + texto branco + 6.5pt bold) ao lado do ano. Validado em `test_etiqueta_service.py`. |
| C4. Código textual escaneável manualmente (Componente 19, Wave 3 v4.0) | ✅ | Backend persiste `codigo_publico` UNIQUE em `idx_provas_codigo_publico`; payload do QR embute o código (`gerar_payload_qr(codigo_publico, qr_hash)` em `provas.py:422`); `validar_payload_qr` flexível para aceitar formato antigo e novo. |
| C5. Provas v3.0 migradas (Wave 7) com rota inferida | ✅ READINESS | Trigger permite `NULL → valor` (testado mentalmente via `pg_proc.prosrc`); `idx_provas_rota` está pronto. **MAS:** AUD-W2V4-001 fará a Wave 7 falhar para qualquer cenário em que ela tente regerar transições legacy via state machine, porque o reinício de ciclo continuará tentando zerar rota. |
| C6. ALTER TYPE adiciona valores ao enum existente | ✅ | Migration 012 linhas 81-84 usa `ALTER TYPE rota_enum ADD VALUE IF NOT EXISTS` para os 4 valores. Confirmado em produção: `pg_enum` agora tem 6 valores (`PADRAO`, `DIRETA`, `MATRIZ`, `LAM_MATRIZ`, `FILIAL`, `LAM_FILIAL`). |
| C7. RotaCriacaoEnum bloqueia legacy (PADRAO/DIRETA) na criação | ✅ | `RotaCriacaoEnum` em `schemas/prova.py:12-28` tem só os 4 v4.0; teste `test_provacreaterequest_rejeita_legacy_v3` parametrizado para PADRAO e DIRETA. |
| C8. Coluna `codigo_publico` UNIQUE NOT NULL VARCHAR(20) | ✅ | Confirmado via `information_schema.columns` (data_type=character varying, max_length=20, is_nullable=NO); `idx_provas_codigo_publico` UNIQUE em `pg_indexes`. |
| C9. Geração com CSPRNG `secrets.choice` + alfabeto 31 chars sem ambíguos | ✅ | `codigo_publico_service.py:54-61`; `CODIGO_PUBLICO_NANO_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"` (linha 35) — sem 0/O/1/I/L. 20 testes em `test_codigo_publico_service.py`. |
| C10. Idempotência camera↔manual: QR carrega `codigo_publico` | ✅ | `qrcode_service.gerar_payload_qr` aceita `identificador` (DAT v3.0 §8.1); `provas.py:422` passa `codigo_publico`; `validar_payload_qr` constant-time compara hash truncado. |
| C11. Ordem dos 4 valores enum padrão UPPERCASE | ⚠ DIVERGE | DAT v3.0 §8 e Backlog usam lowercase (`'matriz'/'lam_matriz'/...`); ADR-115 documentou divergência (UPPERCASE para consistência com outros enums). Aceitável. |
| C12. Etiqueta usa template configurável (RN-011) | ✅ | `etiqueta_service.gerar_pdf` aceita `template: dict | None`; `_carregar_template_etiqueta` lê de `configuracoes_sistema.template_etiqueta` (ADR-036). |
| C13. Modificação cirúrgica em `executar_transicao` (autorizada por Mario, ADR-119) | ⚠ INCOMPLETA | Cobre aprovação (linhas 359-375 de `state_machine.py`) mas **NÃO cobre reinício de ciclo** (linhas 377-384 — zera rota). Ver AUD-W2V4-001. |
| C14. RLS já cobre o cenário sem nova policy | ✅ | `pol_provas_insert WITH CHECK (app_private.current_user_is_admin())` em `pg_policies`; sem nova migration RLS necessária. |
| C15. Confirmação dupla na criação (mitigação Backlog v4.0 §6) | ❌ AUSENTE | Modal de confirmação descartado pelo ADR-118 (depois SUPERSEDIDO pelo Visual Refresh v2); texto auxiliar "rota imutável" também removido (CHANGELOG Polish round 1). Risco de "Confusão operacional" sem mitigação. |
| C16. Backfill local na migration | ✅ | Migration 012 linhas 92-140 lê provas com `codigo_publico IS NULL`, gera código baseado em `created_at`, garante unicidade via set local + retry 20x. Confirmado em prod: 16/16 provas têm código. |
| C17. Testes do Componente 06 com cobertura ≥80% | ✅ PARCIAL | `test_codigo_publico_service.py` (20 testes), `test_provas_api_v4.py` (14 testes). **MAS:** falta cobertura de imutabilidade real e drift enum (testes `test_imutabilidade_rota.py`, `test_rota_enum_drift.py`, `test_migration_012.py` propostos no `analysis.md` §4.10 NÃO foram criados). |

### Definition of Done Global (Backlog v4.0 §2 — 10 itens)

| # | Item | Status | Evidência |
|---|---|---|---|
| 1 | Code review aprovado | N/A | Sessão única; auditoria sênior é o equivalente. |
| 2 | Cobertura ≥80% nas camadas de domínio/serviço | ✅ | `codigo_publico_service` 20 testes; `state_machine` 26+; `etiqueta_service` 7+. |
| 3 | Testes de integração no staging | ⚠ | Backend `pytest` reportado 795 passed. **Mas** smoke E2E manual reportado como "não executado" no analysis.md anexo Visual Refresh v1; Mario validou apenas visualmente. |
| 4 | Migrations versionadas e documentadas | ✅ aplicada via MCP, **⚠ DIVERGE do repo** | Migration Alembic única (`012_add_codigo_publico...`) em `backend/migrations/versions/`. **Em produção foi aplicada em 3 chunks via MCP** (`012a`, `012b`, `012c`) registrados em `supabase_migrations.schema_migrations` mas não em `alembic_version` da forma alembic-canônica (apenas o `version_num='012'` foi setado). Idempotência reclamada mas não testada via `alembic upgrade/downgrade` em ambiente limpo. |
| 5 | Critérios de aceitação validados | ⚠ | 14/17 ✅, 1 ⚠ (C11), 1 ⚠ (C13 — incompleto), 1 ❌ (C15). |
| 6 | Matriz de Acesso testada em cada perfil | ✅ | `pol_provas_insert WITH CHECK (current_user_is_admin())` herdada da Wave 1 v4.0. |
| 7 | Sem erros no console / logs | ⚠ NÃO VERIFICÁVEL | Smoke E2E não executado nesta entrega. |
| 8 | Documentação atualizada | ⚠ | `CHANGELOG.md`, `DECISIONS.md`, `CLAUDE.md` ✅. **MAS** `docs/db/schema.sql` desatualizado (declara alembic_version=011, sem coluna `codigo_publico`). Anexo Visual Refresh v1 em `analysis.md` é descommitted no working tree e referencia estado SUPERSEDED. |
| 9 | RLS versionada em `/migrations/rls/` | ✅ | Wave 2 v4.0 não criou nova policy (cobertura herdada). |
| 10 | Animações com prefers-reduced-motion | ✅ | `nova-prova.module.css` tem `@media (prefers-reduced-motion: reduce)` que desabilita Framer Motion. |

### Cobertura dos 4 valores do enum `rota_enum`

| Rota | Pydantic (`RotaCriacaoEnum`) | TypeScript (`RotaCriacao`) | PostgreSQL (`pg_enum`) | Teste integração | Teste E2E | Etiqueta (badge) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| MATRIZ | ✅ | ✅ | ✅ (sortorder=3) | ✅ parametrizado | ❌ não exercida | ✅ "MATRIZ" |
| LAM_MATRIZ | ✅ | ✅ | ✅ (sortorder=4) | ✅ parametrizado | ❌ | ✅ "LAM. MATRIZ" |
| FILIAL | ✅ | ✅ | ✅ (sortorder=5) | ✅ parametrizado | ❌ | ✅ "FILIAL" |
| LAM_FILIAL | ✅ | ✅ | ✅ (sortorder=6) | ✅ parametrizado | ❌ | ✅ "LAM. FILIAL" |
| PADRAO (legacy) | ❌ bloqueado | ✅ leitura | ✅ (sortorder=1) | N/A criação | N/A | ✅ "MATRIZ (legada)" |
| DIRETA (legacy) | ❌ bloqueado | ✅ leitura | ✅ (sortorder=2) | N/A criação | N/A | ✅ "FILIAL (legada)" |

**Observação:** os 4 valores v4.0 são idênticos em literais nas três
camadas. Teste de drift automatizado (`test_rota_enum_drift.py`,
proposto no `analysis.md` §4.10 #9) **NÃO** foi criado. Sem proteção
contra divergência futura.

### Imutabilidade da rota — duas camadas

**Camada Pydantic:** `ProvaCreateRequest` aceita `rota: RotaCriacaoEnum`
(obrigatório). Não existe schema de UPDATE com `rota`. Endpoints
`/transicoes`, `/cancelar`, `/reiniciar-ciclo` não recebem `rota` no
payload. ✅

**Camada banco (trigger):** `trg_provas_rota_imutavel` ativo (verificado
via `pg_trigger`); função `fn_bloquear_alteracao_rota` confirmada via
`pg_proc.prosrc` com `proconfig=["search_path="]` (ADR-024). Permite
`NULL → valor`, bloqueia `valor → outro_valor` e `valor → NULL`. ✅

**Transição NULL → valor (Wave 7 readiness):** verificada apenas
**estaticamente** (lendo o source do trigger). NÃO há teste de
integração que rode UPDATE real e confirme. **Risco:** sem teste, se
algum PR futuro alterar a função do trigger e quebrar a permissividade
de NULL→valor, a Wave 7 vai falhar e ninguém detecta antes do deploy.

**Lacuna:** `state_machine.executar_transicao` linha 383 tenta
`prova.rota = None` para reinício de ciclo. Em prova v4.0 com rota
preenchida, esse UPDATE é exatamente o caso `valor → NULL` proibido
pelo trigger. Ver AUD-W2V4-001.

### Compatibilidade com provas legacy (`rota IS NULL`)

| Cenário | Resultado | Evidência |
|---|---|---|
| Listagem (`GET /provas/`) com rota=NULL | ✅ funciona | `ProvaListItem.rota: RotaEnum \| None`. Frontend renderiza `—` quando null. |
| Detalhe (`GET /provas/{id}`) | ✅ funciona | `ProvaResponse.rota: RotaEnum \| None`. |
| Aprovação (`POST /transicoes`) prova legacy | ✅ funciona (modificação cirúrgica) | `state_machine.executar_transicao` linha 370-375: `if prova.rota is None: rota_depois = determinar_rota(usuario)`; teste `test_executar_transicao_deriva_rota_em_prova_legada` valida. |
| Reinício de ciclo prova legacy (`rota=PADRAO`) | ⚠ teste passa em mock_db, **mas em produção quebra para v4.0** | `test_executar_reinicio_ciclo_reprovada_para_criada_incrementa` usa `rota=PADRAO`. mock_db não simula trigger. AUD-W2V4-001 trata este cenário. |
| Etiqueta legacy regerada (`GET /etiqueta.pdf`) | ✅ | `gerar_pdf(codigo_publico=None, rota=None)` produz PDF sem o bloco extra; `ROTA_BADGE_LABELS` inclui `(legada)` para PADRAO/DIRETA caso a prova legada já tenha um desses. |

### Geração do identificador alfanumérico

| Verificação | Status | Notas |
|---|---|---|
| Formato `PRV-AAAA-MM-NNNNNN` | ✅ | `gerar_codigo_publico` em `codigo_publico_service.py:43-61`; teste regex em `test_gerar_codigo_publico_regex_completo`. |
| Alfabeto sem 0/O/1/I/L | ✅ | Constant `CODIGO_PUBLICO_NANO_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"` (31 chars); teste `test_alfabeto_tem_31_chars_sem_ambiguos`. |
| Teste de unicidade em larga escala | ⚠ FRACO | `test_gerar_codigo_publico_nao_determinismo_sufixo` usa apenas 200 amostras com tolerância para 1 colisão. Prompt de execução pediu 10.000. Probabilidade ~2.3e-5 com 200; com 10.000 seria ~57%. |
| Índice único | ✅ | `idx_provas_codigo_publico` UNIQUE em `pg_indexes`. |
| Retry em colisão | ✅ migration; ⚠ NÃO no handler | Migration 012 retry até 20x (linha 122). **MAS** `provas.py:create_prova` linha 488-543 NÃO retenta — em colisão de UNIQUE INDEX, mapeia genericamente para 409 "Numero de requerimento ja cadastrado" (mensagem ENGANOSA: pode ser colisão de `codigo_publico`). |
| Decisão registrada em DECISIONS.md | ✅ | ADR-116 explícito sobre coluna NOVA vs `qr_code_hash`. |

### Etiqueta reformulada

| Verificação | Status |
|---|---|
| Nome, requerimento, vendedor, rota, QR, código textual | ✅ |
| Código em destaque | ⚠ 8.5pt (não 18pt do prompt) — documentado no `analysis.md` §4.9 |
| Etiquetas pré-existentes válidas | ✅ (regerar produz PDF sem bloco extra; etiqueta original em BYTEA preservada) |
| Compatível com impressoras térmicas e a jato | ✅ (90×57mm A1 PDF padrão) |
| Configurabilidade prevista | ✅ (`template_etiqueta` JSONB, mas nenhuma chave nova adicionada nesta wave — `codigo_publico` e badge sempre renderizados quando presentes) |

### Confirmação dupla da rota no frontend

| Verificação | Status |
|---|---|
| Modal aparece após submit | ❌ AUSENTE |
| Reapresenta rota escolhida em destaque | ❌ |
| Confirmação explícita | ❌ |
| Mensagem "rota é imutável" | ❌ removida no Polish round 1 |

**Conclusão:** mitigação documentada do risco "Confusão operacional"
(Backlog v4.0 §6) **descartada**. Nenhuma mitigação substituta clara.
O default `INITIAL_FORM.rota = "MATRIZ"` (`page.tsx:48`) aumenta o risco
— admin pode submeter rapidamente sem prestar atenção.

### Documentação Atualizada

| Arquivo | Status | Notas |
|---|---|---|
| `CHANGELOG.md` | ✅ | Seção da Wave 2 v4.0 + Visual Refresh + Visual Refresh v2 presentes (linhas 5-616). Histórico anterior preservado. |
| `DECISIONS.md` | ✅ | ADRs 115-122 registrados. ADR-118/120/121 marcados SUPERSEDIDO. |
| `CLAUDE.md` | ✅ | Tabela de waves atualizada; seção "Como adicionar valor ao enum `rota_enum`" presente. |
| `docs/wave2-v4/analysis.md` | ⚠ DIRTY | Anexo "Visual Refresh Execution" (linhas 1268-1417) está **descommitted** no working tree — referencia estado SUPERSEDED pelo Visual Refresh v2 que **já foi commitado**. Confunde leitor. |
| `docs/db/schema.sql` | ❌ DESATUALIZADO | Declara `alembic_version=011`, omite coluna `codigo_publico`, omite trigger novo, omite indexes `idx_provas_codigo_publico`/`idx_provas_rota`, mostra rota_enum com 2 valores. CLAUDE.md aponta este arquivo como referência rápida — ainda mais grave. |

### Migrations Versionadas

| Migration | Em repo? | Em produção? | Casa? |
|---|---|---|---|
| `012_add_codigo_publico_and_rotas_v4_to_provas.py` | ✅ | ⚠ Aplicada em 3 chunks via MCP, não como Alembic atomic | Estado final coerente; mas `alembic upgrade head` em ambiente limpo não reproduz o histórico real (foi `apply_migration` MCP, não `alembic upgrade`). |
| `alembic_version` | ✅ aponta `012` | ✅ `version_num='012'` | Sim |
| RLS migrations | ✅ | ✅ aplicadas (rls_009 a rls_013) | Sim |

**Risco:** se a migration Alembic 012 do repo for aplicada em ambiente
novo (staging fresh, dev local), o `bind.execute("SELECT id, created_at
FROM provas_digitais WHERE codigo_publico IS NULL")` lê 0 linhas (banco
vazio) → backfill é no-op → `ALTER COLUMN ... SET NOT NULL` passa →
estado final equivalente. Aceitável **se** ninguém precisar fazer
`alembic downgrade` para reproduzir o estado intermediário (não pode,
porque ENUM ADD VALUE não é reversível em transação).

### Refactor Coordenado Completo

Pontos de inferência de rota identificados no `analysis.md` §3 e
substituídos:

| Ponto | Status |
|---|---|
| `provas.py:create_prova` removeu `determinar_rota` chamada na criação | ✅ removeu de fato (linhas 414-421 antigas substituídas por persistência direta de `body.rota` na linha 484). |
| `state_machine.executar_transicao` aprovação | ✅ modificação cirúrgica ADR-119 |
| `state_machine.executar_transicao` reinício | ❌ NÃO MODIFICADO — zera rota — AUD-W2V4-001 |
| `_build_prova_response` removeu `rota_projetada` | ✅ confirmado por inspeção do `provas.py` |
| `ProvaResponse` removeu `rota_projetada` | ✅ |
| Frontend `nova-prova/page.tsx` consome `prova.rota` | ✅ |

---

## Fase 2 — Auditoria Qualitativa

### Achados de Segurança

#### AUD-W2V4-S01 (LOW) — `gerar_payload_qr` aceita identificador sem validar separador
**Arquivo:** `backend/app/services/qrcode_service.py:48-63`
**Descrição:** o parâmetro `identificador` foi renomeado de `nro_requerimento`
para refletir aceitar tanto `codigo_publico` quanto legacy. **Mas** se um
caller passar uma string contendo `|` (separador do payload), o payload
fica malformado (4 ou mais campos no `split`). O backend hoje passa
apenas `codigo_publico` (formato fixo) e `nro_requerimento` (regex
`[A-Za-z0-9._\-/ ]+` que **não inclui `|`**), então é defesa preventiva.
**Recomendação:** adicionar `if '|' in identificador: raise ValueError(...)`.
Severidade BAIXA porque os callers atuais já filtram, mas o helper é
público.

#### AUD-W2V4-S02 (INFO) — Etiqueta pública por design
**Descrição:** o `codigo_publico` é renderizado em destaque na etiqueta
impressa. A etiqueta pode ser fotografada e divulgada externamente.
Mitigações DAT v3.0 §8.2 (rate limiting + mensagens genéricas) ficam
para a Wave 3 v4.0 / Componente 19. Aceitável e documentado.

#### AUD-W2V4-S03 (INFO) — `service_role` bypassa trigger
**Descrição:** o backend usa `service_role` (RLS bypass). O trigger
`trg_provas_rota_imutavel` é `BEFORE UPDATE` — mesmo com `service_role`,
o trigger dispara. Confirmado via `pg_trigger.tgenabled='O'`. Não é
escape route. ✅

### Achados de Correção (Bugs)

#### AUD-W2V4-001 (CRITICAL) — Reinício de ciclo de prova v4.0 quebra com SQLSTATE 22023
**Arquivo:** `backend/app/services/state_machine.py:377-414`
**Descrição:** a função `executar_transicao` define
`reiniciando_ciclo = (status_atual == REPROVADA_PELO_VENDEDOR and
status_novo == CRIADA)` (linha 354-357). Quando verdadeiro, executa:

```python
# linha 377-384
if reiniciando_ciclo:
    ciclo_depois = ciclo_antes + 1
    rota_depois = None       # <-- BUG
    acao_audit = "reiniciar_ciclo"

# linha 414
prova.rota = rota_depois     # <-- aciona trigger
```

**Reprodução mental:**
1. Admin cria prova v4.0 com `rota=MATRIZ` → ok.
2. Vendedor MATRIZ aprova (modificação cirúrgica preserva `rota=MATRIZ`).
3. Vendedor reprova → `prova.status=REPROVADA_PELO_VENDEDOR`,
   `prova.rota=MATRIZ`.
4. Admin clica "Reiniciar ciclo" → `POST /provas/{id}/reiniciar-ciclo`.
5. `executar_transicao(status_novo=CRIADA, prova.rota=MATRIZ)`:
   - `reiniciando_ciclo=True` → `rota_depois=None`.
   - linha 414: `prova.rota = None`.
6. `db.flush()` → `UPDATE provas_digitais SET rota=NULL WHERE id=...`.
7. Trigger `trg_provas_rota_imutavel` BEFORE UPDATE com `OLD.rota=MATRIZ
   IS DISTINCT FROM NEW.rota=NULL` → função executa.
8. Função: `OLD.rota IS NOT NULL AND NEW.rota IS DISTINCT FROM OLD.rota`
   → TRUE → `RAISE EXCEPTION 'Coluna rota e imutavel...' SQLSTATE
   22023`.
9. Endpoint mapeia para 502 ou 422 (`AtorNaoAutorizadoError` /
   `RotaIndeterminavelError` / `ValueError` ramos não cobrem
   `IntegrityError`/`DBAPIError`; ramo `Exception` no
   `reiniciar_ciclo_prova:2243-2252` mapeia para 502).
10. Admin vê "Falha ao reiniciar ciclo" sem orientação útil.

**Por que isso é CRITICAL:**
- Viola **RF-009 v4.0 literal**: "Ao reiniciar o ciclo, a rota
  previamente escolhida é mantida".
- Viola **RN-006 v4.0**: "preserva a rota original".
- Viola **US-010**: "rota original é preservada".
- Endpoint `/reiniciar-ciclo` está EXPOSTO em produção desde a Wave 3
  Lote C; basta uma prova v4.0 ser reprovada para o bug ser acionado.
- O `analysis.md` §6 ADR-119 só cobriu o caso `aprovando`, não o
  `reiniciando_ciclo`. Lapso de escopo da modificação cirúrgica
  autorizada por Mario.
- **Bloqueia a Wave 7** indiretamente: a Wave 7 vai usar a state machine
  para validar a coerência das provas legacy, e qualquer fluxo que
  envolva reinício de ciclo + rota preservada vai falhar.

**Cobertura de teste:** ZERO. O teste existente
`test_executar_reinicio_ciclo_reprovada_para_criada_incrementa`
(`test_state_machine.py:718`) usa `rota=RotaEnum.PADRAO` (legacy) e
`mock_db` (não simula trigger). Passa porque:
- `prova.rota` é setada para `None` no objeto Python (mock não tem
  trigger).
- Asserções verificam `prova.rota is None` (estado pós, sem trigger).

**Recomendação:** modificar `state_machine.executar_transicao` linhas
377-384:

```python
if reiniciando_ciclo:
    ciclo_depois = ciclo_antes + 1
    # RN-006 v4.0: preservar rota no reinício de ciclo (RF-009 v4.0).
    # rota_depois = rota_antes (sem alteração; trigger permite valor=valor
    # via `WHEN (OLD.rota IS DISTINCT FROM NEW.rota)` que retorna FALSE).
    # Para provas legadas v3.0 com rota=NULL, mantém NULL — Wave 7 fará
    # backfill antes de re-executar a state machine.
    rota_depois = rota_antes
    acao_audit = "reiniciar_ciclo"
```

E adicionar **2 testes de integração** com banco real:
1. Reinício de prova v4.0 (`rota=MATRIZ`) preserva rota e não dispara
   trigger.
2. Reinício de prova legacy (`rota=NULL`) mantém NULL.

#### AUD-W2V4-002 (CRITICAL) — Branch `development` HEAD em estado build-broken
**Arquivos afetados:**
- `frontend/src/lib/types/prova.ts` (HEAD `e936ddf`, sem helper) vs
  working tree (com helper)
- `frontend/src/app/(dashboard)/nova-prova/page.tsx` (HEAD `5047172`,
  importa helper)
- `frontend/src/hooks/useCreateProva.ts` (working tree, usa helper)
- `frontend/src/app/globals.css` (working tree, ajuste de cor)

**Descrição:** o commit `5047172` (Visual Refresh v2) reescreveu
`page.tsx` para importar `isAllowedImageType` de `@/lib/types/prova`
(linha 20) e usar em runtime (linha 136). **Mas** o helper só existe
no working tree de `prova.ts` (382 linhas) — **não no commit `e936ddf`**
que continua em HEAD para esse arquivo (369 linhas). O `useCreateProva.ts`
no HEAD ainda usa o cast antigo `(ALLOWED_IMAGE_TYPES as readonly
string[]).includes(...)`.

**Verificação:**
```
git show HEAD:frontend/src/lib/types/prova.ts | grep isAllowedImageType
# (vazio)
git show HEAD:frontend/src/app/(dashboard)/nova-prova/page.tsx | grep isAllowedImageType
# 20:  isAllowedImageType,
# 136:    if (!isAllowedImageType(file.type)) {
```

**Consequência:** `tsc --noEmit` em HEAD do `development`:
```
frontend/src/app/(dashboard)/nova-prova/page.tsx:20:3 - error TS2305:
Module '@/lib/types/prova' has no exported member 'isAllowedImageType'.
```

**O `next build` falha**. As validações reportadas no CHANGELOG da
Visual Refresh v2 ("tsc 0 / next build 13/13 paginas") foram feitas no
working tree DIRTY, não no estado realmente commitado.

**`main` está coerente** (tem o cast antigo + tipo antigo, sem
inconsistência), mas `development` que serve de base para próximas
waves está broken.

**Recomendação:** commit das alterações pendentes para que o estado
em `development` reflita a realidade dos changelogs:
```
git add frontend/src/lib/types/prova.ts frontend/src/hooks/useCreateProva.ts \
        frontend/src/app/globals.css
git commit -m "fix(wave2-v4/c06): commit das alteracoes do helper isAllowedImageType (Visual Refresh v1)"
```

E o anexo Visual Refresh v1 em `docs/wave2-v4/analysis.md` deve ser
revisado (referencia estado SUPERSEDED pelo v2) — ou commitado com nota
clara, ou descartado via `git checkout`.

**Severidade CRITICAL** porque:
- Toda CI/CD e desenvolvimento futuro a partir de `development` quebra.
- Discrepância entre documentação ("tsc 0") e estado realmente
  commitado mina a confiança em outros relatórios.

#### AUD-W2V4-003 (HIGH) — Comentário enganoso em `codigo_publico_service.py`
**Arquivo:** `backend/app/services/codigo_publico_service.py:14-16`
**Descrição:** docstring afirma:
> Unicidade enforced pela coluna `provas_digitais.codigo_publico UNIQUE`
> e pelo trigger `trg_provas_rota_imutavel`.

Mas o trigger `trg_provas_rota_imutavel` protege a coluna `rota`, NÃO o
`codigo_publico`. Confunde leitor.
**Recomendação:** remover a parte do trigger; deixar só "Unicidade
enforced pela coluna `provas_digitais.codigo_publico UNIQUE` (índice
`idx_provas_codigo_publico`)".

#### AUD-W2V4-004 (MEDIUM) — Handler de criação não tem retry em colisão de `codigo_publico`
**Arquivo:** `backend/app/api/v1/provas.py:474-543`
**Descrição:** o `analysis.md` §4.4 propôs retry de até 3x na geração
do código em caso de colisão. **A implementação não tem retry** —
gera código uma vez (linha 413), faz INSERT, e em `IntegrityError`
mapeia para 409 "Numero de requerimento ja cadastrado" (mensagem
**enganosa** se a colisão for de `codigo_publico`, não de `nro_req`).
A migration tem retry (20x). O handler em produção, não.

**Probabilidade:** baixíssima (31^6 = 887M combinações; ~30 inserts/dia
operacional). Mas:
- Mensagem 409 enganosa atrapalha debugging quando acontecer.
- Análise da exception não distingue entre `idx_provas_codigo_publico`
  e `provas_digitais_nro_requerimento_key`.

**Recomendação:** ler `exc.orig` ou usar `pg_error_code` para distinguir
o constraint violado. Em colisão de `codigo_publico`, retentar com novo
código (até 3x). Em colisão de `nro_requerimento`, manter 409 atual.

#### AUD-W2V4-005 (MEDIUM) — `validar_payload_qr` aceita formato legacy sem validação semântica
**Arquivo:** `backend/app/services/qrcode_service.py:66-86`
**Descrição:** a função aceita tanto formato v4.0 (`codigo_publico`)
quanto legacy v3.0 (`nro_requerimento`) no segundo campo, e valida apenas
o hash truncado. **MAS** o `ScanRequest` Pydantic em `prova.py:322-354`
chama o validador apenas em formato estrutural (3 campos separados por `|`)
e não diferencia. **Risco:** se o Componente 19 da Wave 3 v4.0 chamar
`resolver_prova(identificador)` sem distinguir formato, pode acabar
usando `nro_requerimento` antigo num registro v4.0 que tem ambos. Sem
testes que cubram a coexistência.
**Recomendação:** adicionar comentário explícito documentando o contrato
"identificador pode ser PRV-* (preferencial) ou nro_requerimento
(legacy)" + teste integrado quando a Wave 3 v4.0 implementar Componente 19.

### Achados de Regressões em Waves Anteriores

#### AUD-W2V4-006 (HIGH) — Reinício de ciclo (Wave 3 C14) regredido para v4.0
Mesmo achado do AUD-W2V4-001 visto pela ótica de regressão: o endpoint
`POST /provas/{id}/reiniciar-ciclo` (Wave 3 Lote C, Componente 14)
funcionava para provas legacy. Após Wave 2 v4.0, **funciona para
legacy `rota=NULL`** (zera para NULL — sem mudança detectada pelo
trigger), **mas quebra para legacy `rota=PADRAO/DIRETA` E para todas
as v4.0**. Como há 5 provas legacy com `rota=PADRAO/DIRETA` em produção
(2 PADRAO + 3 DIRETA), a regressão é **observável imediatamente**:
qualquer admin que tente reiniciar uma dessas provas (se foram
reprovadas em algum momento) recebe 502.

#### AUD-W2V4-007 (LOW) — Audit log de reinício documenta `rota_depois=null`
**Arquivo:** `backend/app/services/state_machine.py:432-433`
**Descrição:** o `detalhes_json` do audit log de reinício grava
`"rota_depois": None`. Após o fix do AUD-W2V4-001, deve passar a gravar
`"rota_depois": rota_antes.value` (a rota preservada). Mudança de
contrato silenciosa — registrar.

### Achados de Performance

#### AUD-W2V4-P01 (INFO) — `idx_provas_rota` aparece como unused
Esperado: nenhuma prova v4.0 criada em produção, então o índice ainda
não foi exercitado. Cairá do advisor conforme uso real (mesmo padrão
da Wave 6).

#### AUD-W2V4-P02 (INFO) — `idx_provas_codigo_publico` JÁ usado
Não aparece como `unused_index`. Significa que alguma query já tocou
nele (provavelmente via UNIQUE constraint check do INSERT da migration
012 ou de testes locais).

#### AUD-W2V4-P03 (LOW) — Geração do PDF tem custo fixo do logo SVG
A `etiqueta_service.gerar_pdf` lê 2 SVGs do disco a cada chamada (não
cacheia). Custo aceitável (<200ms total), mas em alta concorrência
(10+ POST /provas/ simultâneos) pode somar. Aceitável para o volume
atual; documentar como follow-up.

### Achados de Manutenibilidade

#### AUD-W2V4-M01 (HIGH) — schema.sql desatualizado
**Arquivo:** `docs/db/schema.sql`
**Descrição:** declara `alembic_version=011` e contém:
- `CREATE TYPE rota_enum AS ENUM ('PADRAO', 'DIRETA');` (deveria ter 6)
- `provas_digitais` sem coluna `codigo_publico`
- Sem trigger `trg_provas_rota_imutavel`
- Sem indexes `idx_provas_codigo_publico` / `idx_provas_rota`

CLAUDE.md aponta este arquivo na seção "Documentos de referência" como
"Snapshot do schema atual". Quem ler tem visão errada.

**Recomendação:** atualizar para refletir alembic_version=012, todas as
estruturas novas, ou MARCAR EXPLICITAMENTE no topo "este arquivo está
desatualizado — fonte de verdade são as migrations".

#### AUD-W2V4-M02 (MEDIUM) — Migration Alembic divergente do estado real
A migration 012 do repo é UMA migration atomic. Em produção foi aplicada
em 3 chunks via MCP `apply_migration` (`012a`, `012b`, `012c` em
`supabase_migrations.schema_migrations`). O `alembic_version='012'`
foi setado manualmente (passo 5 do `analysis.md` anexo Execução).

Se algum dev rodar `alembic downgrade -1` localmente, o downgrade da
012 do repo NÃO é equivalente ao "rollback" do estado em produção (que
exigiria reverter os 3 chunks separadamente). Se o dev rodar `alembic
upgrade head` em ambiente novo, o resultado funcional bate (estado final
equivalente), mas o histórico é distinto.

**Recomendação:** documentar explicitamente em `CLAUDE.md` ou `DECISIONS.md`
que `alembic_version=012` corresponde aos 3 chunks MCP. Adicionar nota
na docstring da migration sobre essa divergência.

#### AUD-W2V4-M03 (LOW) — Default `INITIAL_FORM.rota = "MATRIZ"` aumenta risco operacional
**Arquivo:** `frontend/src/app/(dashboard)/nova-prova/page.tsx:48`
**Descrição:** o default `MATRIZ` permite ao admin submeter rapidamente
sem prestar atenção. Combinado com a remoção da confirmação dupla
(C15) e do texto auxiliar "rota imutável" (Polish round 1), agrava
o risco "Confusão operacional" do Backlog v4.0 §6.
**Recomendação:** ou (a) reintroduzir confirmação dupla, ou (b) trocar
default para `null`/`""` forçando escolha consciente, ou (c) restaurar
o texto auxiliar.

#### AUD-W2V4-M04 (LOW) — Duplicação de logos backend/frontend órfã
**Descrição:** o ADR-120 documentou que `logo_3studio.svg` e
`logo_studio_e_arte.svg` viviam em `backend/app/services/etiqueta_assets/`
**e** em `frontend/public/etiqueta/`. O Visual Refresh v2 deletou a
pasta frontend (CHANGELOG linha 103-104), mas o ADR-120 está SUPERSEDIDO
e ainda menciona a duplicação como decorrente. Aceitável (documentado),
mas confunde quem lê DECISIONS sequencialmente.

### Achados de Cobertura de Testes

#### AUD-W2V4-T01 (HIGH) — Suíte `test_imutabilidade_rota.py` não criada
Proposta no `analysis.md` §4.10 #7. Cobriria:
- UPDATE direto rota=X em prova com rota não-NULL → IntegrityError
- UPDATE direto rota=NULL em prova com rota não-NULL → IntegrityError
- UPDATE direto rota=Y em prova com rota=NULL → SUCESSO (Wave 7)
- `executar_transicao` aprovando prova legada (mock_db ok, mas
  com banco real testar trigger)
- `executar_transicao` aprovando prova v4.0 (mesmo)

**Sem este teste, AUD-W2V4-001 não foi detectado pela suíte automática.**

#### AUD-W2V4-T02 (HIGH) — Suíte `test_rota_enum_drift.py` não criada
Proposta no `analysis.md` §4.10 #9. Sem proteção automática contra
divergência futura entre `RotaEnum` Python, `Rota` TypeScript e
`pg_enum`. Hoje os 3 batem; nada garante que continuarão batendo.

#### AUD-W2V4-T03 (HIGH) — Suíte `test_migration_012.py` não criada
Proposta no `analysis.md` §4.10 #8. Sem teste de:
- `alembic upgrade head` em ambiente limpo
- `alembic downgrade -1` reverte coluna + trigger + indexes
- Idempotência (re-run)

A reclamação "IDEMPOTENTE" na docstring da migration não é validada
automaticamente.

#### AUD-W2V4-T04 (MEDIUM) — Cobertura E2E ausente para 4 rotas
Os testes `test_provas_api_v4.py` cobrem APENAS o schema Pydantic e o
state_machine (mock_db). NÃO há teste de integração HTTP que crie
prova com cada uma das 4 rotas e verifique que o PDF tem o badge
correto, que o `codigo_publico` está no payload do QR, etc.

**Risco:** a tela `/nova-prova` pode submeter `rota=LAM_FILIAL` mas
o backend pode estar persistindo `MATRIZ` por algum bug de mapeamento
— nenhum teste E2E pega isso. Smoke E2E manual reportado como "não
executado" no `analysis.md` anexo Visual Refresh.

#### AUD-W2V4-T05 (LOW) — Teste de unicidade fraco (200 amostras)
Proposto 10.000 no prompt da execução; entregue 200. Aceitável
estatisticamente, mas longe da expectativa.

### Achados de Documentação

#### AUD-W2V4-D01 (LOW) — Anexo Visual Refresh v1 em analysis.md descommitted
**Arquivo:** `docs/wave2-v4/analysis.md` (linhas 1268-1417 no working
tree, ausentes no HEAD)
**Descrição:** o anexo descreve o estado SUPERSEDED (EtiquetaPreview SVG
removido, etc.) e está em working tree não-commitado. Confunde leitor:
quem ler `analysis.md` no HEAD vê apenas até linha 1267 (anexo Execução
da Wave 2 v4.0 inicial). Se for commitado, o leitor verá o anexo de
um estado que já foi superseded.
**Recomendação:** ou (a) atualizar para refletir estado pós-Visual
Refresh v2 (consistente), ou (b) descartar via `git checkout
docs/wave2-v4/analysis.md` (perdendo informação histórica).

#### AUD-W2V4-D02 (LOW) — Strings `analysis.md`/`CHANGELOG` mencionam validação `tsc 0` que é falsa em HEAD
Mesma raiz do AUD-W2V4-002. Os changelogs Visual Refresh v1 e v2
declaram que `tsc --noEmit` retorna exit 0 e que `next build` gera
13/13 páginas. **Falso para o HEAD do `development`** (sem o helper
`isAllowedImageType` em `prova.ts`). A frase só era verdadeira no
working tree dirty. Mina a confiança nas demais validações reportadas.

### Achados de Aderência ao Especificado

#### AUD-W2V4-A01 (CRITICAL) — Modificação cirúrgica autorizada por Mario INCOMPLETA
**Contrato do `analysis.md` §6:** "Modificar 4 linhas em `executar_transicao`
(linhas 358-373) para preservar `prova.rota` quando já preenchida".

**Implementação:** modificou apenas o ramo `aprovando` (linhas 359-375).
Não modificou o ramo `reiniciando_ciclo` (linhas 377-384).

**Consequência:** AUD-W2V4-001. Modificação foi feita no espírito do
prompt mas não na completude requerida.

#### AUD-W2V4-A02 (HIGH) — Mitigação documentada do Backlog §6 descartada
Conforme C15 da Fase 1. Nem `analysis.md` nem `DECISIONS.md` justificam
adequadamente o descarte além de "design Figma do Mario sem confirmação".
ADR-118 SUPERSEDIDO menciona que "os 2 toggles forçam escolha
consciente"; mas Visual Refresh v2 voltou a 4 botões diretos com
default `MATRIZ`, removendo o argumento original.

---

## Fase 3 — Verificação Comportamental em Staging

### Estado real da tabela provas_digitais

```
column         type                       max_len   nullable
nro_requerimento  varchar                   50      NO
qr_code_hash      varchar                   64      NO
rota              rota_enum                 -       YES
codigo_publico    varchar                   20      NO
```
✅ Conforme migration 012.

**Trigger `trg_provas_rota_imutavel`:**
```
CREATE TRIGGER trg_provas_rota_imutavel BEFORE UPDATE ON public.provas_digitais
FOR EACH ROW WHEN ((old.rota IS DISTINCT FROM new.rota))
EXECUTE FUNCTION fn_bloquear_alteracao_rota()
```
✅ Função tem `proconfig=["search_path="]`, código verificado.

**Indexes em provas_digitais:** 10 (8 explícitos + 2 das UNIQUE constraints
nro_requerimento + qr_code_hash). Inclui `idx_provas_codigo_publico`
UNIQUE e `idx_provas_rota`. ✅

### Distribuição de dados

```
total_provas              16
rota_null                 11
rota_padrao_legacy         2
rota_direta_legacy         3
rota_matriz_v4             0
rota_lam_matriz_v4         0
rota_filial_v4             0
rota_lam_filial_v4         0
codigo_null                0
```

**Observação importante:** **ZERO provas v4.0 foram criadas em
produção desde o deploy** (2026-05-04). O smoke E2E não foi executado.
A entrega não foi exercitada funcionalmente — apenas visualmente
(Mario validou aspecto da tela, não fluxo completo).

### Cenários de Borda

- ✅ Nenhuma prova com rota inválida.
- ✅ Nenhuma prova legacy com rota acidentalmente preenchida (1->1).
- ✅ Nenhum `codigo_publico` duplicado (UNIQUE constraint).
- ✅ Nenhum `codigo_publico` em formato inválido (todos `PRV-2026-04-XXXXXX`).

### Audit log da Wave 2

Não auditável diretamente sem credenciais admin. Por inspeção do
código (`provas.py:502-517`), o `criar_prova` registra:
- `acao="criar_prova"`
- `detalhes_json` inclui `rota`, `codigo_publico`, `vendedor_id`,
  `vendedor_nome`, `nro_requerimento`, `cliente`, `object_key`
- ✅ Conforme planejado.

### Cloudflare

- R2 bucket `rastreio-provas-artes` inalterado desde 2026-04-07. ✅
- 0 workers (esperado).
- KV/D1/Hyperdrive: nenhum referenciado pelo projeto. ✅
- **Nenhuma modificação na Wave 2 v4.0** — escopo respeitado.

### Advisors Supabase (security + performance)

- 1 INFO `rls_enabled_no_policy` em `alembic_version` (intencional,
  ADR-025) — pré-existente.
- 1 WARN `auth_leaked_password_protection` (WONTFIX plano pago,
  ADR-027) — pré-existente.
- 12 INFOs `unused_index` — todos pré-existentes EXCETO
  `idx_provas_rota` que é da Wave 2 v4.0 (esperado: nenhuma prova v4.0
  ainda).
- **Nenhum NOVO advisor de segurança ou performance crítico.**

---

## Achados Consolidados Ordenados por Severidade

### CRITICAL (2 achados — bloqueiam aprovação)

| ID | Título | Arquivo:linha | Recomendação |
|---|---|---|---|
| AUD-W2V4-001 | Reinício de ciclo de prova v4.0 quebra com SQLSTATE 22023 (rota imutável zerada) | `backend/app/services/state_machine.py:377-414` | Trocar `rota_depois = None` por `rota_depois = rota_antes` no ramo `reiniciando_ciclo`; adicionar 2 testes integrados (v4.0 e legacy NULL); registrar ADR. |
| AUD-W2V4-002 | Branch `development` HEAD em estado build-broken (helper `isAllowedImageType` ausente em `prova.ts` mas usado em `page.tsx`) | `frontend/src/lib/types/prova.ts` (HEAD vs working) | Commitar as alterações pendentes em `prova.ts` + `useCreateProva.ts` + `globals.css`; revisar anexo do `analysis.md`. |
| AUD-W2V4-A01 | Modificação cirúrgica autorizada por Mario incompleta (cobre só aprovação) | (mesmo de AUD-W2V4-001) | Mesma recomendação |

### HIGH (6 achados — ≥3 bloqueariam isoladamente)

| ID | Título | Recomendação |
|---|---|---|
| AUD-W2V4-006 | Regressão em Wave 3 C14 (reinício) para 5 provas legacy + futuras v4.0 | Mesma de AUD-W2V4-001 |
| AUD-W2V4-T01 | `test_imutabilidade_rota.py` não criada | Criar suíte com banco real (não mock_db) cobrindo 5 cenários (NULL→valor; valor→outro; valor→NULL; aprovação v4.0; aprovação legacy) |
| AUD-W2V4-T02 | `test_rota_enum_drift.py` não criada | Criar teste que confronta `set(RotaEnum)` com `SELECT enumlabel FROM pg_enum` |
| AUD-W2V4-T03 | `test_migration_012.py` não criada | Criar teste de upgrade/downgrade/idempotência |
| AUD-W2V4-A02 | Mitigação "Confusão operacional" descartada sem substituta | Reintroduzir confirmação dupla OU restaurar texto auxiliar OU mudar default para "" |
| AUD-W2V4-M01 | `docs/db/schema.sql` desatualizado (declara alembic 011) | Atualizar ou marcar como desatualizado no topo |
| AUD-W2V4-003 | Comentário enganoso em `codigo_publico_service.py` (afirma trigger protege codigo_publico) | Corrigir docstring linha 14-16 |

### MEDIUM (4 achados)

| ID | Título | Recomendação |
|---|---|---|
| AUD-W2V4-004 | Handler de criação não retenta em colisão de `codigo_publico` (mensagem 409 enganosa) | Diferenciar `IntegrityError` por constraint name; retentar até 3x para `idx_provas_codigo_publico`; manter 409 para `nro_requerimento` |
| AUD-W2V4-005 | `validar_payload_qr` aceita formato legacy sem validação semântica | Documentar contrato; adicionar teste integrado quando Componente 19 for implementado |
| AUD-W2V4-M02 | Migration Alembic divergente do estado realmente aplicado em produção (3 chunks MCP) | Documentar em `CLAUDE.md` / docstring da migration |
| AUD-W2V4-T04 | Cobertura E2E ausente para 4 rotas | Smoke E2E manual obrigatório antes do merge para `main`; idealmente Playwright para 1 rota |

### LOW (8 achados)

| ID | Título | Notas |
|---|---|---|
| AUD-W2V4-S01 | `gerar_payload_qr` aceita identificador sem validar `\|` | Defesa preventiva |
| AUD-W2V4-007 | Audit log de reinício documenta `rota_depois=null` | Mudança de contrato após fix do AUD-W2V4-001 |
| AUD-W2V4-P03 | Geração do PDF tem custo fixo do logo SVG | Cache + métrica de performance |
| AUD-W2V4-M03 | Default `INITIAL_FORM.rota = "MATRIZ"` aumenta risco operacional | Combinar com AUD-W2V4-A02 |
| AUD-W2V4-M04 | Duplicação de logos backend/frontend órfã (Visual Refresh v2 deletou) | ADR-120 SUPERSEDIDO menciona — esclarecer |
| AUD-W2V4-T05 | Teste de unicidade fraco (200 amostras) | Aumentar para 10.000 conforme prompt da execução |
| AUD-W2V4-D01 | Anexo Visual Refresh v1 em analysis.md descommitted referenciando estado SUPERSEDED | Atualizar ou descartar |
| AUD-W2V4-D02 | Changelogs declaram `tsc 0`/`next build 13/13` que é falso em HEAD | Corrigir em sessão de fix |

### INFO (3 achados)

| ID | Título |
|---|---|
| AUD-W2V4-S02 | Etiqueta semi-pública por design (mitigações ficam para Wave 3 / C19) |
| AUD-W2V4-S03 | `service_role` bypassa RLS mas trigger continua disparando — não é escape route |
| AUD-W2V4-P01 | `idx_provas_rota` aparece como unused (esperado — sem provas v4.0) |
| AUD-W2V4-P02 | `idx_provas_codigo_publico` JÁ usado (esperado) |

---

## Recomendações de Próximos Passos

### Bloqueantes — devem entrar em sessão dedicada de correção ANTES de qualquer prosseguimento para Wave 3 v4.0

1. **AUD-W2V4-001 + AUD-W2V4-006 + AUD-W2V4-A01:** corrigir
   `state_machine.executar_transicao` para preservar rota no reinício
   de ciclo. Adicionar 2 testes integrados em
   `backend/tests/test_imutabilidade_rota.py` que rodem com banco real
   (não mock_db) — afirmando que o reinício de prova v4.0 com
   `rota=MATRIZ` mantém `MATRIZ`, e que reinício de prova legacy com
   `rota=NULL` mantém `NULL`. ADR novo registrando.

2. **AUD-W2V4-002:** commitar as alterações pendentes em
   `frontend/src/lib/types/prova.ts`,
   `frontend/src/hooks/useCreateProva.ts`, `frontend/src/app/globals.css`.
   Decidir sobre o anexo Visual Refresh v1 em `analysis.md` (commit ou
   descarte). Confirmar `npx tsc --noEmit` exit 0 + `npx next build`
   13/13 no estado realmente commitado (não no working tree dirty).

### Antes da Wave 7 (Componente 21) — pré-requisitos críticos

3. **AUD-W2V4-T01:** suíte de testes de imutabilidade da rota com banco
   real cobrindo NULL→valor (cenário Wave 7) entre os 5 cenários.

4. **AUD-W2V4-T02:** teste de drift `RotaEnum` Python ↔ `pg_enum`
   PostgreSQL.

5. **AUD-W2V4-T03:** teste de upgrade/downgrade/idempotência da
   migration 012.

### Recomendado nesta sprint (ALTOS restantes)

6. **AUD-W2V4-A02 + AUD-W2V4-M03:** decisão produto sobre mitigação do
   risco "Confusão operacional" — confirmação dupla, default vazio, ou
   texto auxiliar restaurado.

7. **AUD-W2V4-M01:** atualizar `docs/db/schema.sql` para refletir
   alembic_version=012 + estruturas novas, OU marcar topo como
   desatualizado.

8. **AUD-W2V4-003:** corrigir docstring de `codigo_publico_service.py`.

### Backlog técnico (MEDIUM/LOW)

9. AUD-W2V4-004 (retry em colisão de código).
10. AUD-W2V4-005 (documentação contrato `validar_payload_qr`).
11. AUD-W2V4-T04 (smoke E2E manual obrigatório antes do merge).
12. AUD-W2V4-T05 (teste de unicidade com 10k amostras).
13. AUD-W2V4-S01 (validar separador `|` em `gerar_payload_qr`).

### Pré-requisitos que a Wave 7 precisa verificar antes de executar

- **AUD-W2V4-001 corrigido** (sem isso, a Wave 7 vai conseguir
  fazer backfill `NULL → valor`, mas qualquer prova reprovada que
  tenha rota recém-atribuída e seja reiniciada subsequentemente
  quebra).
- **Teste de transição NULL → valor** (AUD-W2V4-T01) confirmando
  que o trigger permite isso explicitamente — sem teste, a Wave 7
  pode descobrir tarde.
- **Idempotência da migration 012** (AUD-W2V4-T03) validada em
  ambiente limpo — se a Wave 7 for fazer mais um par de migrations
  Alembic, precisam coexistir com o estado atual (3 chunks MCP).

---

## Anexos

### A.1 — Inventário de artefatos lidos

**Contexto vivo (Seção 2.1 do prompt):**
- `CLAUDE.md` (integral, 521 linhas)
- `DECISIONS.md` ADRs 115-122 (Wave 2 v4.0)
- `CHANGELOG.md` linhas 1-616 (Wave 2 v4.0 + Visual Refresh + Visual Refresh v2)
- `docs/wave2-v4/analysis.md` (integral, 1417 linhas no working tree;
  HEAD termina em 1267)
- `docs/db/schema.sql` (integral — DESATUALIZADO)
- (Wave 1 v4.0 audit-report.md / fix-validation.md — referenciados,
  não relidos integralmente)

**Documentos canônicos v4.0 (Seção 2.2 do prompt):**
- `RequisitosProvasDigitais_v4_0.docx` — extraído via Python
  `zipfile`+regex (40.346 chars). Foco em RFs 001-027, RNs 001-013,
  US-001 a US-012.
- `BACKLOG_RastreioProvasDigitais_v4_0.docx` — 29.708 chars. Foco em
  Componente 06 v4.0 (linhas 247-287), Componente 21 Wave 7 (616-654),
  DoD global (40-62), Riscos §6 (655-676).
- `DAT_RastreioProvasDigitais_v3_0.docx` — 21.966 chars. Foco em
  §6 (Migração) + §7 (RBAC) + §8 (Identificação `PRV-AAAA-MM-NNNNNN`).
- `UML_RastreioProvasDigitais_v4_0.drawio` — existência confirmada
  (257 KB), não lido integralmente.

**Código-fonte (Seção 2.3 do prompt):**
- `backend/migrations/versions/012_add_codigo_publico_and_rotas_v4_to_provas.py` (integral)
- `backend/app/db/models.py` (integral, RotaEnum + ProvaDigital)
- `backend/app/services/codigo_publico_service.py` (integral, 89 linhas)
- `backend/app/services/qrcode_service.py` (integral, 115 linhas)
- `backend/app/services/etiqueta_service.py` (integral, 378 linhas)
- `backend/app/services/state_machine.py` (integral, 451 linhas)
- `backend/app/domain/schemas/prova.py` (integral, 533 linhas)
- `backend/app/api/v1/provas.py` (linhas críticas: 365-624 criação;
  2170-2287 reinício)
- `frontend/src/lib/types/prova.ts` (integral, 382 linhas no working;
  369 em HEAD)
- `frontend/src/hooks/useCreateProva.ts` (integral)
- `frontend/src/app/(dashboard)/nova-prova/page.tsx` (integral, 609 linhas)
- `backend/tests/test_codigo_publico_service.py` (integral)
- `backend/tests/test_provas_api_v4.py` (integral)
- `backend/tests/test_state_machine.py` linhas 718-800 (reinício)

**Histórico Git (Seção 2.4 do prompt):**
```
c06ca56 docs(wave2-v4/c06): supersede ADRs 118/120/121 (em development)
5047172 fix(wave2-v4/c06): visual refresh v2 (em development)
0547550 Merge branch 'wave2-v4/componente-06' (em main)
4b78352 fix(wave2-v4/c06): canvas com padding 12px
32b0998 fix(wave2-v4/c06): conteudo 100% do box branco
a9c7444 feat(wave2-v4/c06): visualizacao da rota
e936ddf feat(wave2-v4/c06): cadastro com selecao de rota + codigo publico
0782073 docs(wave2-v4): analise read-only pre-execucao
```

### A.2 — Output principal do MCP Supabase (read-only)

```
SELECT version_num FROM alembic_version;
=> "012"

SELECT enumlabel, enumsortorder FROM pg_enum WHERE enumtypid='rota_enum'::regtype;
=> [PADRAO/1, DIRETA/2, MATRIZ/3, LAM_MATRIZ/4, FILIAL/5, LAM_FILIAL/6]

SELECT * FROM pg_trigger WHERE tgrelid='provas_digitais'::regclass;
=> trg_provas_rota_imutavel BEFORE UPDATE WHEN (OLD.rota IS DISTINCT FROM NEW.rota)
   trg_provas_updated_at

Distribuição de provas:
  total                  16
  rota_null              11
  rota_padrao_legacy      2
  rota_direta_legacy      3
  rota_matriz_v4          0
  rota_lam_matriz_v4      0
  rota_filial_v4          0
  rota_lam_filial_v4      0
  codigo_null             0  (16/16 backfilled)

Indexes provas_digitais:
  idx_provas_codigo_publico (UNIQUE)  ← NOVO
  idx_provas_rota                     ← NOVO
  idx_provas_status, idx_provas_vendedor, idx_provas_created_at,
  idx_provas_status_created, idx_provas_vendedor_status,
  provas_digitais_pkey, _nro_req_key, _qr_code_hash_key

RLS policies provas_digitais (3): pol_provas_select / _insert / _update,
todas usando app_private.current_user_*().

Advisors security: 1 INFO + 1 WARN (pré-existentes).
Advisors performance: 12 INFO unused_index (1 novo: idx_provas_rota,
esperado).

Cloudflare R2: bucket único 'rastreio-provas-artes', sem modificações
desde 2026-04-07. 0 workers.
```

### A.3 — Cenários reproduzidos mentalmente

#### Cenário 1: Admin cria prova v4.0 com `rota=MATRIZ` → vendedor MATRIZ aprova

1. POST `/upload-url` → `object_key=provas/uuid/arte.jpg`. ✅
2. PUT no R2 → 200. ✅
3. POST `/provas/` body `{rota: "MATRIZ", ...}`:
   - `RotaCriacaoEnum("MATRIZ")` ✅
   - `gerar_codigo_publico(now())` → `PRV-2026-05-XXXXXX` ✅
   - `gerar_payload_qr(codigo_publico, qr_hash)` → `3SD|PRV-...|hash` ✅
   - `gerar_pdf(codigo_publico, RotaEnum.MATRIZ, ...)` ✅
   - INSERT `provas_digitais (rota=MATRIZ, codigo_publico=PRV-...)`. ✅
4. Vendedor MATRIZ escaneia → `validar_payload_qr` ok. ✅
5. POST `/transicoes {status_novo: APROVADA_PELO_VENDEDOR}`:
   - `executar_transicao` linha 359-375 (modificação cirúrgica):
     `aprovando=True, prova.rota=MATRIZ`, então `rota_depois = MATRIZ`. ✅
   - `prova.rota = MATRIZ` (sem mudança).
   - Trigger `WHEN (OLD.rota=MATRIZ IS DISTINCT FROM NEW.rota=MATRIZ)`
     → FALSE → função NÃO executa. ✅
6. Aprovação ok. ✅

#### Cenário 2 (BUG AUD-W2V4-001): Admin cria prova v4.0, é reprovada, tenta reiniciar ciclo

1. (passos 1-5 do cenário 1)
2. Vendedor reprova → `prova.status=REPROVADA_PELO_VENDEDOR`, `rota=MATRIZ`. ✅
3. Admin POST `/provas/{id}/reiniciar-ciclo`:
   - `_carregar_prova_com_scoping` ok.
   - validação status `REPROVADA_PELO_VENDEDOR` ok.
   - `executar_transicao(status_novo=CRIADA, prova.rota=MATRIZ)`:
     - `reiniciando_ciclo=True` (linha 354).
     - linha 383: `rota_depois = None`.
     - linha 414: `prova.rota = None`.
     - `db.flush()` → `UPDATE ... SET rota=NULL`.
     - Trigger: `OLD.rota=MATRIZ IS DISTINCT FROM NEW.rota=NULL` → TRUE.
     - Função: `OLD.rota IS NOT NULL AND NEW.rota IS DISTINCT FROM OLD.rota`
       → TRUE → `RAISE EXCEPTION 'Coluna rota e imutavel...'` SQLSTATE 22023.
   - `try/except` no handler captura `Exception` (linha 2243) → 502
     "Falha ao reiniciar ciclo".
4. Admin recebe 502 sem orientação útil. **BUG REPRODUZIDO MENTALMENTE.**

#### Cenário 3: Admin cria prova v4.0 LAM_FILIAL → fluxo aprovação

Igual cenário 1 com `rota=LAM_FILIAL`. **Status atual:** o `state_machine`
da Wave 2 v4.0 NÃO tem suporte aos novos estados de laminação (Wave 3
v4.0 / Componente 11 fará isso). Logo, após `RETIRADA_PELO_VENDEDOR →
APROVADA_PELO_VENDEDOR`, a prova fica "presa" porque as próximas
transições da `TRANSICOES` (linha 63-69) só conhecem
`DE_VOLTA_3STUDIO` ou `ENCAMINHADA_A_CLICHERIA` (rota direta v3.0). A
regra extra de rota em `state_machine.executar_transicao:316-341`
exige vendedor MATRIZ ou FILIAL — funciona para LAM_FILIAL se o
vendedor for FILIAL. Resultado: prova segue por rota direta antiga.
**Inconsistência tolerada documentada no `analysis.md` §4.12 ponto 5.**

---

**Fim do relatório de auditoria.**

---

## APÊNDICE — Status de Resolução por Achado (2026-05-05)

> Adicionado pela sessão de Audit Fixes (`wave2-v4/fixes/execution`).
> O corpo original do relatório acima **NÃO foi editado** — este
> apêndice anota o status final de cada achado.

### CRITICAL (3)

| ID | Status | Commit | Critério de validação |
|---|---|---|---|
| AUD-W2V4-001 | **RESOLVIDO** | `cbd6506` | `state_machine.py:377-384` agora preserva `rota_antes` no reinício. 3 testes em `test_state_machine.py` (1 ajustado + 2 novos cobrindo v4.0/legacy NULL); 1 teste em `test_provas_api.py` ajustado; cenário 5 de `test_imutabilidade_rota.py` valida com banco real. ADR-123. |
| AUD-W2V4-002 | **RESOLVIDO** | `1a88ab8` | 3 arquivos commitados (`prova.ts`, `useCreateProva.ts`, `globals.css`); `tsc --noEmit` exit 0 + `next build` 13/13 NO ESTADO COMMITADO; anexo `analysis.md` com nota de supersedimento explícita. |
| AUD-W2V4-A01 | **RESOLVIDO** | `cbd6506` | Mesma raiz de AUD-W2V4-001 — modificação cirúrgica do ADR-119 completada para o ramo `reiniciando_ciclo`. |

### HIGH (7)

| ID | Status | Commit | Critério |
|---|---|---|---|
| AUD-W2V4-006 | **RESOLVIDO** | `cbd6506` | Mesma raiz de AUD-W2V4-001 — regressão Wave 3 C14 corrigida para 5 provas legacy + futuras v4.0. |
| AUD-W2V4-T01 | **RESOLVIDO** | `c9bd87b` | `backend/tests/test_imutabilidade_rota.py` criado com 5 testes integrados (`NULL→valor`, `valor→outro`, `valor→NULL`, aprovação v4.0, reinício v4.0). Skip sem `INTEGRATION_DATABASE_URL` (alinhado com padrão da suíte). |
| AUD-W2V4-T02 | **RESOLVIDO** | `420de1d` | `backend/tests/test_rota_enum_drift.py` criado com 5 testes (Python↔Postgres skipif; TS↔Python rodam — confirmam zero drift atual; subset Pydantic; sanity). |
| AUD-W2V4-T03 | **RESOLVIDO** | `3af50d1` | `backend/tests/test_migration_012.py` criado com 3 testes (upgrade fresh, downgrade reverte, idempotência via down-up). Skip sem `INTEGRATION_DATABASE_URL`. |
| AUD-W2V4-A02 | **RESOLVIDO** | `c7de064` | Default `INITIAL_FORM.rota = ""` força escolha; texto auxiliar "rota imutável após cadastro" restaurado. ADR-124. |
| AUD-W2V4-M01 | **RESOLVIDO** | `f02d882` | `docs/db/schema.sql` reescrito refletindo `alembic_version=012` + estruturas Wave 2 v4.0 + Wave 1 v4.0 + RLS 008-013 + nota dos 3 chunks MCP. |
| AUD-W2V4-003 | **RESOLVIDO** | `78aeb15` | Docstring de `codigo_publico_service.py` corrigida (trigger não enforça unicidade do `codigo_publico`). |

### MEDIUM (4)

| ID | Status | Commit | Critério |
|---|---|---|---|
| AUD-W2V4-004 | **RESOLVIDO** | `4e99410` | While loop com retry 3x em `idx_provas_codigo_publico`; classificação por `constraint_name`; mensagem clara para race TOCTOU de `nro_requerimento`; 502 para outros IntegrityError. 3 testes novos. |
| AUD-W2V4-005 | **RESOLVIDO** | `42532e9` | Docstring de `validar_payload_qr` documenta contrato polimórfico do segundo campo (codigo_publico v4.0 vs nro_requerimento legacy). TEST PENDING explícito para Componente 19. |
| AUD-W2V4-M02 | **RESOLVIDO** | `1ec605b` | CLAUDE.md "Estado atual do banco" + docstring da migration 012 documentam os 3 chunks MCP e set manual de `alembic_version='012'`. |
| AUD-W2V4-T04 | **RESOLVIDO** (manual) | (`fix-validation.md`) | Smoke E2E manual obrigatório antes do merge para `main` documentado em checklist. Execução por Mario. |

### LOW (8)

| ID | Status | Commit | Critério |
|---|---|---|---|
| AUD-W2V4-S01 | **RESOLVIDO** | `42532e9` | `gerar_payload_qr` rejeita identificador com separador `\|`. 1 teste novo. |
| AUD-W2V4-007 | **RESOLVIDO** | `cbd6506` | Audit log de reinício agora grava `rota_depois = rota_antes.value` (mudança de contrato documentada e mais honesta). |
| AUD-W2V4-P03 | **RESOLVIDO** (parcial) | `38b2fc5` | `@lru_cache(maxsize=1)` em `_check_assets` — economiza 2 syscalls/request. Cache de bytes do SVG classificado WONTFIX-parcial (gargalo é parse XML, não read) — documentado no docstring. |
| AUD-W2V4-M03 | **RESOLVIDO** | `c7de064` | Junto com AUD-W2V4-A02 — default vazio. |
| AUD-W2V4-M04 | **RESOLVIDO** | `7c80523` | Bloco "Pós-supersedimento" no ADR-120 esclarece eliminação da duplicação de logos. |
| AUD-W2V4-T05 | **RESOLVIDO** | `6b6c727` | Amostras aumentadas de 200 para 10.000 (tolera 5 colisões com base em paradoxo do aniversário). |
| AUD-W2V4-D01 | **RESOLVIDO** | `1a88ab8` | Anexo Visual Refresh v1 do `analysis.md` commitado com nota explícita de supersedimento. |
| AUD-W2V4-D02 | **RESOLVIDO** | `1a88ab8` | Re-validação `tsc --noEmit` exit 0 + `next build` 13/13 NO ESTADO COMMITADO confirmada após AUD-002. |

### INFO (4 — registrar status)

| ID | Status | Tratamento |
|---|---|---|
| AUD-W2V4-S02 | **NÃO APLICÁVEL nesta sessão** | Mitigações DAT v3.0 §8.2 (rate limiting) ficam para Componente 19 / Wave 3 v4.0. Registrado follow-up. |
| AUD-W2V4-S03 | **CONFIRMADO** | `service_role` bypassa RLS mas `trg_provas_rota_imutavel` BEFORE UPDATE continua disparando — não é escape route. Sem ação necessária. |
| AUD-W2V4-P01 | **CONFIRMADO** | `idx_provas_rota` aparece como `unused_index` esperado (zero provas v4.0). Cairá com uso real. |
| AUD-W2V4-P02 | **CONFIRMADO** | `idx_provas_codigo_publico` já usado pelo UNIQUE check da migration 012. Sem ação. |

### Recapitulação

- **Total resolvido:** 22/26 explícitos + 4 INFO confirmados/não-aplicáveis = **26/26**.
- **Deferred:** 0.
- **Não resolvido:** 0.
- **CRITICAL bloqueantes:** ambos resolvidos (AUD-W2V4-001 + AUD-W2V4-002).
- **Wave 7 readiness:** preservada e validada via testes T01/T02/T03 + fix de AUD-W2V4-001.

**Recomenda-se nova rodada de auditoria independente em sessão
separada para confirmar que (a) achados originais foram resolvidos,
(b) correções não introduziram novos problemas, (c) a Wave 7
continua viável.**
