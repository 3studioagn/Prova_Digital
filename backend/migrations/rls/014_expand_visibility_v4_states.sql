-- =============================================================================
-- RLS 014 (Wave 3 v4.0 - Componente 11): expandir visibilidade de
--                                          motorista/clicheria para os 7
--                                          novos estados v4.0
-- =============================================================================
-- Wave 3 v4.0 / Componente 11 - Maquina de Estados Expandida.
--
-- Migration 013 (Alembic) adicionou 7 valores ao status_prova_enum:
--   COM_MOTORISTA_ENTREGA_FINAL    (v4.0 - motorista entrega final)
--   COM_MOTORISTA_IDA_LAMINACAO    (v4.0 - motorista ida laminacao)
--   COM_MOTORISTA_VOLTA_LAMINACAO  (v4.0 - motorista volta laminacao)
--   DE_VOLTA_3STUDIO_POS_LAMINACAO (v4.0 - 3Studio recebe pos-laminacao)
--   ENCAMINHADA_PARA_LAMINACAO     (v4.0 - rumo a clicheria para laminar)
--   ENCAMINHADA_PARA_O_VENDEDOR    (v4.0 - rotas Filial/Lam.Filial)
--   LAMINACAO_CONCLUIDA            (v4.0 - clicheria concluiu laminacao)
--
-- As policies RLS atuais (RLS 012) filtram por status v3.0 literais:
--   - MOTORISTA ve provas/movs/etiquetas quando status = 'COM_MOTORISTA'
--   - CLICHERIA ve quando status IN (ENVIADA, ENCAMINHADA, RECEBIDA)
--
-- Apos a migration 013, esses filtros NAO reconhecem os novos estados.
-- Motorista trabalhando em prova v4.0 (Lam. Matriz) com status
-- COM_MOTORISTA_IDA_LAMINACAO seria filtrado pela RLS — 0 rows visiveis.
--
-- Esta migration expande os 3 policies (provas_digitais, movimentacoes,
-- etiquetas) para reconhecer os 7 novos estados v4.0 onde motorista e
-- clicheria precisam de acesso:
--
--   MOTORISTA ve estados com motorista (4 estados):
--     - COM_MOTORISTA (legacy)
--     - COM_MOTORISTA_IDA_LAMINACAO
--     - COM_MOTORISTA_VOLTA_LAMINACAO
--     - COM_MOTORISTA_ENTREGA_FINAL
--
--   CLICHERIA ve estados onde clicheria atua (US-007 v4.0):
--     - ENVIADA_PARA_CLICHERIA (legacy)
--     - ENCAMINHADA_A_CLICHERIA (legacy)
--     - RECEBIDA_PELA_CLICHERIA (terminal)
--     - ENCAMINHADA_PARA_LAMINACAO (recebe para laminar)
--     - COM_MOTORISTA_IDA_LAMINACAO (motorista a caminho — visivel para
--       confirmar quando chegar)
--     - LAMINACAO_CONCLUIDA (clicheria preparou — continua visivel ate
--       motorista/vendedor pegar)
--
-- Backend usa service_role e BYPASSA RLS por design. O scoping real
-- continua sendo via `app.access.scopes.scope_filter_for` (Wave 1 v4.0).
-- RLS continua ativa como defesa em profundidade para acesso direto
-- via Supabase client do frontend.
--
-- IDEMPOTENTE: usa DROP POLICY IF EXISTS + CREATE.
--
-- Validacao pos-aplicacao:
--   1. SELECT polname FROM pg_policy
--      WHERE polrelid = 'public.provas_digitais'::regclass;
--      -> deve retornar pol_provas_select, pol_provas_insert, pol_provas_update.
--   2. get_advisors security: sem novos alertas.
-- =============================================================================


-- ─── provas_digitais ───────────────────────────────────────────────────────

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
                'LAMINACAO_CONCLUIDA'::public.status_prova_enum
            ])
        )
    );


-- ─── movimentacoes ─────────────────────────────────────────────────────────

DROP POLICY IF EXISTS pol_movimentacoes_select ON public.movimentacoes;
CREATE POLICY pol_movimentacoes_select ON public.movimentacoes
    FOR SELECT
    USING (
        app_private.current_user_is_admin()
        OR prova_id IN (
            SELECT pd.id FROM public.provas_digitais pd
            WHERE pd.vendedor_id = app_private.current_user_id()
        )
        OR usuario_id = app_private.current_user_id()
        OR (
            app_private.current_user_setor() = 'MOTORISTA'::public.setor_enum
            AND prova_id IN (
                SELECT pd.id FROM public.provas_digitais pd
                WHERE pd.status = ANY (ARRAY[
                    'COM_MOTORISTA'::public.status_prova_enum,
                    'COM_MOTORISTA_IDA_LAMINACAO'::public.status_prova_enum,
                    'COM_MOTORISTA_VOLTA_LAMINACAO'::public.status_prova_enum,
                    'COM_MOTORISTA_ENTREGA_FINAL'::public.status_prova_enum
                ])
            )
        )
        OR (
            app_private.current_user_setor() = 'CLICHERIA'::public.setor_enum
            AND prova_id IN (
                SELECT pd.id FROM public.provas_digitais pd
                WHERE pd.status = ANY (ARRAY[
                    'ENVIADA_PARA_CLICHERIA'::public.status_prova_enum,
                    'ENCAMINHADA_A_CLICHERIA'::public.status_prova_enum,
                    'RECEBIDA_PELA_CLICHERIA'::public.status_prova_enum,
                    'ENCAMINHADA_PARA_LAMINACAO'::public.status_prova_enum,
                    'COM_MOTORISTA_IDA_LAMINACAO'::public.status_prova_enum,
                    'LAMINACAO_CONCLUIDA'::public.status_prova_enum
                ])
            )
        )
    );


-- ─── etiquetas ─────────────────────────────────────────────────────────────

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
                          'LAMINACAO_CONCLUIDA'::public.status_prova_enum
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
--     identica a antes — todos os estados v3.0 (COM_MOTORISTA, ENVIADA,
--     ENCAMINHADA, RECEBIDA) continuam na lista.
-- =============================================================================
