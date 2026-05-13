-- =============================================================================
-- RLS 015 (Wave 3 v4.0 — Correcoes Pos-Auditoria do Componente 11):
--   (a) AUD-W3C11-002: adicionar COM_MOTORISTA_ENTREGA_FINAL a clausula
--       de CLICHERIA nas 3 policies (paridade primaria<->secundaria com
--       _CLICHERIA_STATUSES em backend/app/access/scopes.py).
--   (b) AUD-W3C11-008 + AUD-W3C11-016: uniformizar todas as 3 policies
--       para o padrao EXISTS (mais legivel + termina ao primeiro match;
--       performance equivalente apos otimizacao do planner mas semantica
--       mais clara para manutencao).
-- =============================================================================
-- Estado pre-correcao (RLS 014 aplicada):
--   - pol_provas_select: USING direto sobre `status` (sem subquery).
--   - pol_movimentacoes_select: usa `prova_id IN (SELECT pd.id ... WHERE ...)`
--     2 vezes (motorista + clicheria) — inconsistente com etiquetas.
--   - pol_etiquetas_select: usa EXISTS — preferivel.
--   - CLICHERIA cobre 6 estados (3 v3.0 + ENCAMINHADA_PARA_LAMINACAO,
--     COM_MOTORISTA_IDA_LAMINACAO, LAMINACAO_CONCLUIDA) — MAS NAO
--     COM_MOTORISTA_ENTREGA_FINAL, que e necessario para clicheria
--     concluir a ultima transicao das rotas Matriz e Lam.Matriz.
--
-- Estado pos-correcao (esta migration):
--   - pol_provas_select: USING direto preservado (sem subquery — ja era
--     o mais eficiente possivel sobre a propria tabela; nao se beneficia
--     de EXISTS). CLICHERIA inclui 7 estados (3 v3.0 + 4 v4.0).
--   - pol_movimentacoes_select: reescrita usando EXISTS em vez de IN.
--     Semantica preservada; estilo uniforme com pol_etiquetas_select.
--     CLICHERIA agora cobre 7 estados.
--   - pol_etiquetas_select: preservada com EXISTS; CLICHERIA cobre 7.
--
-- Backend continua usando service_role (bypassa RLS). A RLS e defesa
-- em profundidade. _CLICHERIA_STATUSES Python (AUD-W3C11-002) e a
-- defesa SUPERIOR — esta migration alinha a INFERIOR.
--
-- IDEMPOTENTE: DROP POLICY IF EXISTS + CREATE.
--
-- Validacao pos-aplicacao via MCP:
--   SELECT polname, qual FROM pg_policies
--   WHERE schemaname='public' AND tablename IN ('provas_digitais',
--   'movimentacoes','etiquetas') AND policyname LIKE 'pol_%select';
--   -> verificar que cada uma das 3 policies de clicheria contem
--      'COM_MOTORISTA_ENTREGA_FINAL'.
-- =============================================================================


-- ─── provas_digitais ───────────────────────────────────────────────────────
-- Sem subquery — filtro direto sobre a propria tabela. CLICHERIA recebe
-- COM_MOTORISTA_ENTREGA_FINAL como 7o estado.

DROP POLICY IF EXISTS pol_provas_select ON public.provas_digitais;
CREATE POLICY pol_provas_select ON public.provas_digitais
    FOR SELECT
    USING (
        app_private.current_user_is_admin()
        OR vendedor_id = app_private.current_user_id()
        OR (
            app_private.current_user_setor() = 'MOTORISTA'::public.setor_enum
            AND status = ANY (ARRAY[
                'COM_MOTORISTA'::public.status_prova_enum,
                'COM_MOTORISTA_IDA_LAMINACAO'::public.status_prova_enum,
                'COM_MOTORISTA_VOLTA_LAMINACAO'::public.status_prova_enum,
                'COM_MOTORISTA_ENTREGA_FINAL'::public.status_prova_enum
            ])
        )
        OR (
            app_private.current_user_setor() = 'CLICHERIA'::public.setor_enum
            AND status = ANY (ARRAY[
                'ENVIADA_PARA_CLICHERIA'::public.status_prova_enum,
                'ENCAMINHADA_A_CLICHERIA'::public.status_prova_enum,
                'RECEBIDA_PELA_CLICHERIA'::public.status_prova_enum,
                'ENCAMINHADA_PARA_LAMINACAO'::public.status_prova_enum,
                'COM_MOTORISTA_IDA_LAMINACAO'::public.status_prova_enum,
                'LAMINACAO_CONCLUIDA'::public.status_prova_enum,
                'COM_MOTORISTA_ENTREGA_FINAL'::public.status_prova_enum  -- AUD-002: paridade
            ])
        )
    );


-- ─── movimentacoes ─────────────────────────────────────────────────────────
-- Reescrita para EXISTS (AUD-008/016 — uniformizacao). Semantica
-- preservada. CLICHERIA recebe COM_MOTORISTA_ENTREGA_FINAL.

DROP POLICY IF EXISTS pol_movimentacoes_select ON public.movimentacoes;
CREATE POLICY pol_movimentacoes_select ON public.movimentacoes
    FOR SELECT
    USING (
        app_private.current_user_is_admin()
        OR usuario_id = app_private.current_user_id()
        OR EXISTS (
            SELECT 1 FROM public.provas_digitais pd
            WHERE pd.id = movimentacoes.prova_id
              AND (
                  pd.vendedor_id = app_private.current_user_id()
                  OR (
                      app_private.current_user_setor() = 'MOTORISTA'::public.setor_enum
                      AND pd.status = ANY (ARRAY[
                          'COM_MOTORISTA'::public.status_prova_enum,
                          'COM_MOTORISTA_IDA_LAMINACAO'::public.status_prova_enum,
                          'COM_MOTORISTA_VOLTA_LAMINACAO'::public.status_prova_enum,
                          'COM_MOTORISTA_ENTREGA_FINAL'::public.status_prova_enum
                      ])
                  )
                  OR (
                      app_private.current_user_setor() = 'CLICHERIA'::public.setor_enum
                      AND pd.status = ANY (ARRAY[
                          'ENVIADA_PARA_CLICHERIA'::public.status_prova_enum,
                          'ENCAMINHADA_A_CLICHERIA'::public.status_prova_enum,
                          'RECEBIDA_PELA_CLICHERIA'::public.status_prova_enum,
                          'ENCAMINHADA_PARA_LAMINACAO'::public.status_prova_enum,
                          'COM_MOTORISTA_IDA_LAMINACAO'::public.status_prova_enum,
                          'LAMINACAO_CONCLUIDA'::public.status_prova_enum,
                          'COM_MOTORISTA_ENTREGA_FINAL'::public.status_prova_enum  -- AUD-002
                      ])
                  )
              )
        )
    );


-- ─── etiquetas ─────────────────────────────────────────────────────────────
-- Padrao EXISTS preservado. CLICHERIA recebe COM_MOTORISTA_ENTREGA_FINAL.

DROP POLICY IF EXISTS pol_etiquetas_select ON public.etiquetas;
CREATE POLICY pol_etiquetas_select ON public.etiquetas
    FOR SELECT
    USING (
        app_private.current_user_is_admin()
        OR EXISTS (
            SELECT 1 FROM public.provas_digitais pd
            WHERE pd.id = etiquetas.prova_id
              AND (
                  pd.vendedor_id = app_private.current_user_id()
                  OR (
                      app_private.current_user_setor() = 'MOTORISTA'::public.setor_enum
                      AND pd.status = ANY (ARRAY[
                          'COM_MOTORISTA'::public.status_prova_enum,
                          'COM_MOTORISTA_IDA_LAMINACAO'::public.status_prova_enum,
                          'COM_MOTORISTA_VOLTA_LAMINACAO'::public.status_prova_enum,
                          'COM_MOTORISTA_ENTREGA_FINAL'::public.status_prova_enum
                      ])
                  )
                  OR (
                      app_private.current_user_setor() = 'CLICHERIA'::public.setor_enum
                      AND pd.status = ANY (ARRAY[
                          'ENVIADA_PARA_CLICHERIA'::public.status_prova_enum,
                          'ENCAMINHADA_A_CLICHERIA'::public.status_prova_enum,
                          'RECEBIDA_PELA_CLICHERIA'::public.status_prova_enum,
                          'ENCAMINHADA_PARA_LAMINACAO'::public.status_prova_enum,
                          'COM_MOTORISTA_IDA_LAMINACAO'::public.status_prova_enum,
                          'LAMINACAO_CONCLUIDA'::public.status_prova_enum,
                          'COM_MOTORISTA_ENTREGA_FINAL'::public.status_prova_enum  -- AUD-002
                      ])
                  )
              )
        )
    );


-- =============================================================================
-- Notas:
--   - INSERT/UPDATE/DELETE em movimentacoes, etiquetas, audit_logs continuam
--     bloqueados pelos triggers de imutabilidade (RNF-005) + REVOKE GRANT
--     (RLS 008 + 013).
--   - pol_provas_insert e pol_provas_update permanecem inalterados (admin-only).
--   - Schema `app_private` continua nao exposto via PostgREST.
--   - Provas v3.0 legacy (rota=NULL ou PADRAO/DIRETA) tem visibilidade
--     identica a antes — todos os estados v3.0 continuam na lista.
--   - MOTORISTA cobertura permanece em 4 estados (1 legacy + 3 v4.0 contextos)
--     — sem mudanca vs RLS 014.
--   - CLICHERIA cobertura sobe de 6 para 7 estados (adicionado
--     COM_MOTORISTA_ENTREGA_FINAL) — alinha com _CLICHERIA_STATUSES Python.
-- =============================================================================
