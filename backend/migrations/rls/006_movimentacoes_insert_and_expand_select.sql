-- =============================================================================
-- RLS 006: movimentacoes — INSERT policy (nova) + SELECT policy (expandida)
-- =============================================================================
-- IMPORTANTE: Este script e idempotente — DROP IF EXISTS antes de cada CREATE.
--
-- Contexto (Wave 3 Lote A, sub-bloco A.2 — ADR-082):
--
--   Entrega duas mudancas em `movimentacoes`:
--
--   (1) NOVA `pol_movimentacoes_insert` — admin-only, espelhando
--       `pol_provas_insert`. Defesa em profundidade: o backend roda com
--       service_role e bypassa RLS, mas a policy existe para proteger
--       eventuais acessos diretos via supabase-js client no futuro. Sem
--       essa policy, `INSERT INTO movimentacoes` via supabase-js cairia
--       na regra padrao "nenhum INSERT permitido" (RLS habilitada sem
--       policy INSERT bloqueia por padrao), o que tambem funcionaria —
--       mas a policy explicita e consistente com `pol_provas_insert` e
--       tornou-se convencao do projeto desde a Wave 1.
--
--   (2) EXPANSAO de `pol_movimentacoes_select` para resolver o debito
--       F03 da auditoria externa da Sessao 22. A versao atual (definida
--       em `005_initplan_optimization.sql` linhas 147-164) cobre apenas
--       admin + vendedor das proprias provas + autor da movimentacao.
--       Falta cobrir MOTORISTA e CLICHERIA — em desacordo com
--       `pol_provas_select` que ja cobre os 4 atores.
--
--       A regra operacional e: se um setor pode ver a prova, pode ver o
--       historico de movimentacoes daquela prova. Sem isso, MOTORISTA/
--       CLICHERIA conseguiriam listar uma prova (via provas_digitais mas
--       nao conseguiriam ver o historico via movimentacoes direto — gap
--       de defesa em profundidade se o frontend comecar a chamar o
--       supabase-js direto.
--
--       O backend FastAPI ja cobre o scoping corretamente via
--       `_carregar_prova_com_scoping` em `provas.py` (ADR-046, ADR-049),
--       entao funcionalmente o sistema ja funciona. Mas o RNF-005 exige
--       "log imutavel e auditavel" e essa policy e parte da defesa em
--       profundidade.
--
-- Por que nao foi feito na Wave 2: a Wave 2 nao inseria movimentacoes
--   (state machine stub). Tratar o gap agora, na Wave 3 Lote A sub-bloco
--   A.2, e o momento certo — e o primeiro sub-bloco que escreve linhas
--   reais em `movimentacoes`.
--
-- Ordem de execucao em relacao ao 005:
--   `apply_rls.py` aplica arquivos em ordem numerica via
--   `sorted(glob("*.sql"))`. O 006 roda DEPOIS do 005, entao o DROP +
--   CREATE do `pol_movimentacoes_select` abaixo sobrescreve a versao do
--   005 com a versao expandida. Idempotente — pode ser reaplicado.
--
-- UPDATE/DELETE continuam bloqueados pelo trigger `trg_movimentacoes_imutavel`
--   (migration Alembic 001, RNF-005). Nao ha necessidade de `pol_movimentacoes_update`
--   ou `pol_movimentacoes_delete`.
--
-- Validacao pos-aplicacao:
--   1. `SELECT COUNT(*) FROM pg_policies WHERE schemaname='public'`:
--      deve ser 12 (11 anteriores + 1 nova `pol_movimentacoes_insert`).
--   2. `SELECT policyname FROM pg_policies WHERE schemaname='public' AND
--      tablename='movimentacoes'`: deve retornar exatamente 2 policies,
--      `pol_movimentacoes_insert` e `pol_movimentacoes_select`.
--   3. Supabase advisor (security): zero novos lints.
-- =============================================================================


-- ─── MOVIMENTACOES — INSERT policy (nova) ─────────────────────────────────

-- Apenas admin pode inserir movimentacoes via supabase-js client. O backend
-- FastAPI usa service_role e bypassa RLS — todas as transicoes reais da
-- Wave 3 Lote A vao rodar via service_role. Esta policy e defesa em
-- profundidade para o caso de um acesso direto via supabase-js no futuro.
-- Consistente com `pol_provas_insert` (admin-only).
DROP POLICY IF EXISTS pol_movimentacoes_insert ON movimentacoes;
CREATE POLICY pol_movimentacoes_insert ON movimentacoes
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM usuarios u
            WHERE u.auth_uid = (SELECT auth.uid()) AND u.is_admin = true
        )
    );


-- ─── MOVIMENTACOES — SELECT policy (expandida) ────────────────────────────

-- Resolve o debito F03 da Sessao 22: cobre MOTORISTA e CLICHERIA em adicao
-- aos 3 casos ja existentes (admin + vendedor das suas provas + autor).
--
-- Semantica alinhada com pol_provas_select (005_initplan_optimization.sql
-- linhas 75-99):
--   - MOTORISTA ve movimentacoes de provas atualmente em COM_MOTORISTA.
--   - CLICHERIA ve movimentacoes de provas em qualquer status de
--     clicheria (ENVIADA, ENCAMINHADA, RECEBIDA).
--
-- Nota: o JOIN com `provas_digitais` usa o status ATUAL da prova — nao
-- o `status_novo` ou `status_anterior` da movimentacao. A pergunta que a
-- policy responde e "este motorista pode ver movimentacoes da prova X?",
-- e a resposta e "sim, se a prova X esta no status COM_MOTORISTA agora".
-- Isso pode gerar o cenario onde um motorista transiciona `COM_MOTORISTA
-- -> ENVIADA` e imediatamente deixa de ver o historico (porque a prova
-- saiu do seu scope). Aceitavel — o historico fica visivel para o autor
-- (proprio motorista, via OR usuario_id) e para o admin.
--
-- Mantem o padrao `(SELECT auth.uid())` para initplan optimization (ADR-029).
DROP POLICY IF EXISTS pol_movimentacoes_select ON movimentacoes;
CREATE POLICY pol_movimentacoes_select ON movimentacoes
    FOR SELECT
    USING (
        -- 1. Admin ve tudo (consistente com as outras policies).
        EXISTS (
            SELECT 1 FROM usuarios u
            WHERE u.auth_uid = (SELECT auth.uid()) AND u.is_admin = true
        )
        -- 2. Vendedor ve movimentacoes das suas proprias provas.
        OR prova_id IN (
            SELECT pd.id FROM provas_digitais pd
            WHERE pd.vendedor_id = (
                SELECT u.id FROM usuarios u WHERE u.auth_uid = (SELECT auth.uid())
            )
        )
        -- 3. Autor sempre ve suas proprias movimentacoes (mesmo apos
        --    deixar de ser dono do scope — preserva rastreabilidade).
        OR usuario_id = (
            SELECT u.id FROM usuarios u WHERE u.auth_uid = (SELECT auth.uid())
        )
        -- 4. MOTORISTA ve movimentacoes de provas atualmente em
        --    COM_MOTORISTA (F03 fix — Wave 3 A.2, ADR-082).
        OR (
            EXISTS (
                SELECT 1 FROM usuarios u
                WHERE u.auth_uid = (SELECT auth.uid()) AND u.setor = 'MOTORISTA'
            )
            AND prova_id IN (
                SELECT pd.id FROM provas_digitais pd
                WHERE pd.status = 'COM_MOTORISTA'
            )
        )
        -- 5. CLICHERIA ve movimentacoes de provas em qualquer status de
        --    clicheria (F03 fix — Wave 3 A.2, ADR-082).
        OR (
            EXISTS (
                SELECT 1 FROM usuarios u
                WHERE u.auth_uid = (SELECT auth.uid()) AND u.setor = 'CLICHERIA'
            )
            AND prova_id IN (
                SELECT pd.id FROM provas_digitais pd
                WHERE pd.status IN (
                    'ENVIADA_PARA_CLICHERIA',
                    'ENCAMINHADA_A_CLICHERIA',
                    'RECEBIDA_PELA_CLICHERIA'
                )
            )
        )
    );
